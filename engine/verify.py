#!/usr/bin/env python3
"""Check the source package's behavioral contracts against a complete CLI artifact."""
import argparse
import json
import os
from pathlib import Path
import re
import tempfile
import sys

sys.dont_write_bytecode = True

from build_support import scanner_report, test_execution
from build_support.scanner_report import parse_report
from build_support.test_execution import TestCapacity, run_test_process

PACKAGE = Path(__file__).resolve().parent
ANNOTATION = re.compile(r"^\s*(?:#|//|;;|\(\*|/\*)\s*ruleid:\s*(.+?)(?:\s*(?:\*\)|\*/))?$")
UPSTREAM_PATTERN_ANNOTATION = re.compile(r"^\s*//\s*ERROR:")


def valid_trace(trace, source):
    if not isinstance(trace, dict):
        return False
    lines = source.read_bytes().split(b"\n")

    def position(value):
        if not isinstance(value, dict):
            return False
        line, column = value.get("line"), value.get("col")
        return type(line) is int and type(column) is int and 1 <= line <= len(lines) and 1 <= column <= len(lines[line - 1]) + 1

    def location(value):
        if not isinstance(value, dict) or not isinstance(value.get("path"), str):
            return False
        if Path(value["path"]).resolve() != source.resolve() or not position(value.get("start")) or not position(value.get("end")):
            return False
        return (value["start"]["line"], value["start"]["col"]) <= (value["end"]["line"], value["end"]["col"])

    def located_content(value):
        return isinstance(value, list) and len(value) == 2 and location(value[0]) and isinstance(value[1], str)

    def intermediate_vars(values):
        return values is None or (isinstance(values, list) and all(isinstance(value, dict) and location(value.get("location")) and isinstance(value.get("content"), str) for value in values))

    def call_trace(value, depth=0):
        if depth >= 64 or not isinstance(value, list) or len(value) != 2:
            return False
        tag, payload = value
        if tag == "CliLoc":
            return located_content(payload)
        if tag == "CliCall" and isinstance(payload, list) and len(payload) == 3:
            return located_content(payload[0]) and intermediate_vars(payload[1]) and call_trace(payload[2], depth + 1)
        return False

    return call_trace(trace.get("taint_source")) and call_trace(trace.get("taint_sink")) and intermediate_vars(trace.get("intermediate_vars"))


def terminal_trace_location(trace, depth=0):
    if depth >= 64 or not isinstance(trace, list) or len(trace) != 2:
        return None
    tag, value = trace
    if tag == "CliLoc" and isinstance(value, list) and len(value) == 2:
        return value[0]
    if tag == "CliCall" and isinstance(value, list) and len(value) == 3:
        return terminal_trace_location(value[2], depth + 1)
    return None


def expected_traces_match(report, source):
    path = source.with_suffix(source.suffix + ".traces.json")
    if not path.exists():
        return True
    def span(location):
        if (not isinstance(location, dict) or not scanner_report.position(location.get('start'))
                or not scanner_report.position(location.get('end'))):
            return None
        return {"line": location["start"]["line"], "column": location["start"]["col"],
                "end_line": location["end"]["line"], "end_column": location["end"]["col"]}
    for expected in json.loads(path.read_text()):
        findings = [finding for finding in report["results"] if finding["check_id"] == expected["rule"] and finding["start"]["line"] == expected["line"]]
        if len(findings) != 1:
            return False
        trace = findings[0].get("extra", {}).get("dataflow_trace") or {}
        for key in ("source", "sink"):
            if key in expected and span(terminal_trace_location(trace.get("taint_" + key))) != expected[key]:
                return False
    return True


def diagnostic_identity(error):
    type_ = error["type"]
    tag = type_[0] if isinstance(type_, list) else type_
    code = type_[1] if tag == "PartialSemantics" and isinstance(type_, list) else None
    spans = error.get("spans") or [{}]
    return {"type": tag, "construct": code, "line": spans[0].get("start", {}).get("line")}


def valid_diagnostic_positions(errors, source):
    lines = source.read_bytes().split(b"\n")
    offsets = [0]
    for line in lines[:-1]:
        offsets.append(offsets[-1] + len(line) + 1)
    for error in errors:
        kind = error.get("type")
        if not isinstance(kind, list) or kind[0] not in ("PartialParsing", "PartialSemantics"):
            continue
        for span in error.get("spans", []):
            if Path(span["file"]).resolve() != source.resolve():
                return False
            for point in (span["start"], span["end"]):
                line, column = point["line"], point["col"]
                if not (1 <= line <= len(lines) and 1 <= column <= len(lines[line - 1]) + 1):
                    return False
                if point["offset"] != offsets[line - 1] + column - 1:
                    return False
    return True


def valid_finding_positions(findings, source):
    raw = source.read_bytes()
    for finding in findings:
        if Path(finding["path"]).resolve() != source.resolve():
            return False
        start, end = finding["start"], finding["end"]
        if not 0 <= start["offset"] <= end["offset"] <= len(raw):
            return False
        for point in (start, end):
            offset = point["offset"]
            prefix = raw[:offset]
            line = prefix.count(b"\n") + 1
            column = offset - prefix.rfind(b"\n")
            if (point["line"], point["col"]) != (line, column):
                return False
    return True


def unique_findings(findings):
    identities = [(finding['check_id'], str(Path(finding['path']).resolve()),
                   finding['start']['offset'], finding['end']['offset']) for finding in findings]
    return len(identities) == len(set(identities))


def scan_contract(binary, config, source, directory, capacity, *, traces=False, output_file=True):
    env = dict(os.environ, SEMGREP_SEND_METRICS="off",
               SEMGREP_SETTINGS_FILE=str(directory / "settings.yaml"),
               SEMGREP_LOG_FILE=str(directory / "scan.log"))
    report_path = directory / "report.json"
    report_path.unlink(missing_ok=True)
    command = [str(binary), "scan", "--quiet", "--json", "--disable-version-check",
               "--no-rewrite-rule-ids", "--jobs", "1", "--timeout", "0"]
    if traces:
        command.append("--dataflow-traces")
    if output_file:
        command.extend(["--output", str(report_path)])
    command.extend(["--config", str(config), "--", str(source)])
    execution = {"capacity": capacity.record()}
    raw_report = None
    try:
        result = run_test_process(command, env=env, timeout=capacity.deadline(120))
        execution.update(result.record())
        if result.timed_out:
            raise ValueError("scanner exceeded the scaled test deadline")
        raw_report = report_path.read_text() if output_file else result.stdout
        report = parse_report(raw_report)
    except (OSError, ValueError) as error:
        if raw_report is not None:
            execution['report_output'] = raw_report
        return None, {"passed": False, "status": "execution-incomplete",
                      "failure": str(error), "execution": execution}
    return report, {"execution": execution, "exit_code": result.returncode}


def verify_file_selection(binary, directory, capacity=None):
    capacity = capacity or TestCapacity.detect()
    contracts = json.loads((PACKAGE / "source/tests/native-file-selection.json").read_text())
    rows = []
    for contract in contracts:
        root = directory / contract["language"]
        source = root / "source"
        source.mkdir(parents=True)
        for filename in contract["filenames"] + contract["excluded"]:
            (source / filename).write_text(contract["source"])
        config = root / "rule.yaml"
        config.write_text(json.dumps({"rules": [{"id": "selection", "languages": [contract["language"]], "message": "selection", "severity": "ERROR", "mode": "taint", "pattern-sources": [{"pattern": contract["source_pattern"], "exact": True}], "pattern-sinks": [{"pattern": contract["sink_pattern"]}]}]}))
        report, outcome = scan_contract(binary, config, source, root, capacity, traces=True)
        if report is None:
            rows.append({"case": "file-selection/" + contract["language"], **outcome})
            continue
        actual = sorted(Path(finding["path"]).name for finding in report["results"])
        expected = sorted(contract["filenames"])
        scanned = sorted(Path(path).name for path in report.get("paths", {}).get("scanned", []))
        traces = all(valid_trace(finding.get("extra", {}).get("dataflow_trace"), Path(finding["path"])) for finding in report["results"])
        rows.append({"case": "file-selection/" + contract["language"], **outcome, "passed": outcome["exit_code"] == 0 and not report["errors"] and actual == expected and scanned == expected and traces, "expected": expected, "actual": actual, "scanned": scanned, "diagnostics": report["errors"]})
    return rows


def rule_validation_cases():
    cases = json.loads((PACKAGE / "source/tests/callback-rule-validation.json").read_text())
    for case in cases:
        propagator = {"pattern": "register($FROM, $TO)", "from": "$FROM", "to": "$TO",
                      "to-parameter": case["target"]}
        if "by-side-effect" in case:
            propagator["by-side-effect"] = case["by-side-effect"]
        rule = {"id": "callback", "languages": ["javascript"], "severity": "ERROR",
                "message": "Callback model validation", "mode": "taint",
                "pattern-sources": [{"pattern": "source()"}],
                "pattern-sinks": [{"pattern": "sink(...)"}], "pattern-propagators": [propagator]}
        yield case, rule
    for case in json.loads((PACKAGE / "source/tests/model-rule-validation.json").read_text()):
        mode = case.get("mode", "taint")
        if mode not in ("taint", "search"):
            raise ValueError(f"Unknown validation rule mode: {mode}")
        rule = {"id": "model", "languages": ["javascript"], "severity": "ERROR",
                "message": "Framework model validation"}
        if mode == "taint":
            rule.update({"mode": "taint", "pattern-sources": [{"pattern": "source()"}],
                         "pattern-sinks": [{"pattern": "sink(...)"}]})
        rule.update(case["rule"])
        yield case, rule

    for case in json.loads((PACKAGE / "source/tests/native-pattern-validation.json").read_text()):
        rule = {"id": "native-pattern", "languages": [case["language"]], "severity": "ERROR",
                "message": "Native pattern validation", "pattern": case["pattern"]}
        yield case, rule


def verify_rule_validation(binary, directory, capacity=None):
    capacity = capacity or TestCapacity.detect()
    directory.mkdir()
    for case, rule in rule_validation_cases():
        source = directory / ("flow" + case.get("extension", ".js"))
        source.write_text(case.get("source", "const safe = 1;\n"))
        config = directory / "rule.yaml"
        config.write_text(json.dumps({"rules": [rule]}))
        report, outcome = scan_contract(binary, config, source, directory, capacity, output_file=False)
        if report is None:
            yield {"case": "rule-validation/" + case["name"], **outcome}
            continue
        error_types = [error["type"] for error in report.get("errors", [])]
        if case["valid"]:
            passed = outcome["exit_code"] == 0 and not error_types
        else:
            passed = ((outcome["exit_code"] == 2 and error_types == ["Rule parse error"])
                      or (outcome["exit_code"] == 7 and error_types == ["InvalidRuleSchemaError", "SemgrepError"]))
        yield {"case": "rule-validation/" + case["name"],
               "passed": passed and report.get("results") == [],
               **outcome, "error_types": error_types}


def expected_findings(source, rules):
    expected = set()
    for line, text in enumerate(source.read_text().splitlines(), 1):
        match = ANNOTATION.match(text)
        if match:
            expected.update((rule.strip(), line + 1) for rule in match[1].split(","))
        elif UPSTREAM_PATTERN_ANNOTATION.match(text):
            if len(rules) != 1:
                raise ValueError("Upstream pattern annotations require exactly one rule")
            expected.add((rules[0]["id"], line + 1))
    return expected


def verify(binary, config, source, settings, capacity=None):
    capacity = capacity or TestCapacity.detect()
    from ruamel.yaml import YAML

    rules = YAML(typ="safe").load(config.read_text())["rules"]
    taint_rules = {rule["id"] for rule in rules if rule.get("mode") == "taint" or "taint" in rule}
    expected = expected_findings(source, rules)
    report, outcome = scan_contract(binary, config, source, settings, capacity, traces=True)
    if report is None:
        return {"case": str(source.relative_to(PACKAGE)), **outcome}
    actual = {(finding["check_id"], finding["start"]["line"]) for finding in report["results"]}
    diagnostics_path = source.with_suffix(source.suffix + ".diagnostics.json")
    expected_diagnostics = json.loads(diagnostics_path.read_text()) if diagnostics_path.exists() else []
    diagnostics = [diagnostic_identity(error) for error in report["errors"]]
    diagnostic_key = lambda value: json.dumps(value, sort_keys=True)
    diagnostics.sort(key=diagnostic_key)
    expected_diagnostics.sort(key=diagnostic_key)
    traces_valid = all(valid_trace(finding.get("extra", {}).get("dataflow_trace"), source)
                       for finding in report["results"] if finding["check_id"] in taint_rules)
    passed = outcome["exit_code"] == 0 and actual == expected and diagnostics == expected_diagnostics
    if expected_diagnostics:
        passed = outcome["exit_code"] in (0, 2, 3) and actual == expected and diagnostics == expected_diagnostics
    evidence_valid = expected_traces_match(report, source)
    diagnostic_paths_valid = all(not isinstance(error["type"], list) or error["type"][0] != "PartialSemantics"
                                 or (isinstance(error.get("path"), str) and Path(error["path"]).resolve() == source.resolve())
                                 for error in report["errors"])
    diagnostic_positions_valid = valid_diagnostic_positions(report["errors"], source)
    finding_positions_valid = valid_finding_positions(report["results"], source)
    findings_unique = unique_findings(report['results'])
    passed = passed and traces_valid and evidence_valid and diagnostic_paths_valid and diagnostic_positions_valid and finding_positions_valid and findings_unique
    return {"traces_valid": traces_valid, "evidence_valid": evidence_valid, "diagnostic_paths_valid": diagnostic_paths_valid, "diagnostic_positions_valid": diagnostic_positions_valid, "finding_positions_valid": finding_positions_valid, "findings_unique": findings_unique, "case": str(source.relative_to(PACKAGE)), "passed": passed,
            "expected": sorted(expected), "actual": sorted(actual),
            "diagnostics": diagnostics, **outcome}


def verify_rule_translation(binary, config, source, directory, capacity=None):
    from ruamel.yaml.error import YAMLError
    capacity = capacity or TestCapacity.detect()
    case = "rule-translation/" + str(source.relative_to(PACKAGE / "source/tests"))
    execution = {"capacity": capacity.record()}
    env = dict(os.environ, SEMGREP_SEND_METRICS="off",
               SEMGREP_SETTINGS_FILE=str(directory / "settings.yaml"),
               SEMGREP_LOG_FILE=str(directory / "translation.log"))
    try:
        discovery = run_test_process([str(binary), "scan", "--dump-engine-path", "--disable-version-check"],
                                     env=env, timeout=capacity.deadline(120))
        execution["discovery"] = discovery.record()
        if discovery.timed_out or discovery.returncode != 0:
            raise ValueError("engine discovery did not complete successfully")
        core = Path(discovery.stdout.strip()).resolve(strict=True)
        if not core.is_file():
            raise ValueError("engine discovery did not identify a file")
        translation = run_test_process([str(core), "-translate_rules", str(config)],
                                       env=env, timeout=capacity.deadline(120))
        execution["translation"] = translation.record()
        if translation.timed_out or translation.returncode != 0 or not translation.stdout.strip():
            raise ValueError("rule translation did not complete successfully")
        from ruamel.yaml import YAML
        parsed = YAML(typ="safe").load(translation.stdout)
        if not isinstance(parsed, dict) or not isinstance(parsed.get("rules"), list) or not parsed["rules"]:
            raise ValueError("rule translation did not produce a rules document")
        translated = directory / "translated-rule.yaml"
        translated.write_text(translation.stdout)
        row = verify(binary, translated, source, directory, capacity)
        return {**row, "case": case, "translation_execution": execution}
    except (OSError, ValueError, YAMLError) as error:
        return {"case": case, "passed": False, "status": "translation-incomplete",
                "failure": str(error), "translation_execution": execution}


@test_execution.test_run_signals()
def main():
    from ruamel.yaml import YAML

    global PACKAGE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("--case", help="Run a source contract directory or subtree relative to source/tests")
    parser.add_argument("--package", type=Path, default=PACKAGE, help="Frozen contract input package (harness remains this version)")
    args = parser.parse_args()
    PACKAGE = args.package.resolve(strict=True)
    capacity = TestCapacity.detect()
    translation_manifest = PACKAGE / "source/tests/rule-translation.json"
    translations = set(json.loads(translation_manifest.read_text())) if translation_manifest.exists() else set()
    binary = args.binary.resolve(strict=True)
    failed, total = 0, 0
    yaml = YAML(typ="safe")
    with tempfile.TemporaryDirectory(prefix="opengrep-contracts-") as directory:
        configs = sorted((PACKAGE / "source/tests/tainting").rglob("*.yaml"))
        if args.case:
            configs = [config for config in configs if config.parent.relative_to(PACKAGE / "source/tests").is_relative_to(args.case)]
            if not configs:
                parser.error("case does not name a source contract directory")
        if not configs:
            parser.error("source package contains no discoverable taint contracts")
        for config in configs:
            # Reject malformed test rules before invoking the scanner.
            rules = yaml.load(config.read_text())
            if not rules.get("rules"):
                raise ValueError(f"No rules in {config}")
            sources = [path for path in config.parent.glob(config.stem + ".*") if path.suffix not in (".yaml", ".json")]
            if not sources:
                raise ValueError(f"No source contract for {config}")
            for source in sorted(sources):
                row = verify(binary, config, source, Path(directory), capacity)
                total += 1
                failed += not row["passed"]
                print(json.dumps(row), flush=True)
                if str(config.relative_to(PACKAGE / "source/tests")) in translations:
                    row = verify_rule_translation(binary, config, source, Path(directory), capacity)
                    total += 1
                    failed += not row["passed"]
                    print(json.dumps(row), flush=True)
        for row in ([] if args.case else verify_file_selection(binary, Path(directory) / "selection", capacity)):
            total += 1
            failed += not row["passed"]
            print(json.dumps(row), flush=True)
        for row in ([] if args.case else verify_rule_validation(binary, Path(directory) / "validation", capacity)):
            total += 1
            failed += not row["passed"]
            print(json.dumps(row), flush=True)
    print(json.dumps({"contracts": total, "failed": failed, "capacity": capacity.record(),
                      "identity": test_execution.harness_identity(
                          Path(__file__).resolve(), Path(test_execution.__file__).resolve(),
                          Path(scanner_report.__file__).resolve(),
                          PACKAGE / "source-lock.json", binary)}))
    raise SystemExit(int(failed > 0))


if __name__ == "__main__":
    main()
