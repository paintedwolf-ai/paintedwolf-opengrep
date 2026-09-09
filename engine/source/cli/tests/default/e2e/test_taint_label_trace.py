import json

from tests.fixtures import RunSemgrep
from semgrep.constants import OutputFormat


def test_sink_labels_select_supporting_trace(run_semgrep_in_tmp: RunSemgrep):
    result = run_semgrep_in_tmp(
        "rules/taint_label_trace.yaml",
        target_name="taint/taint_label_trace.py",
        output_format=OutputFormat.JSON,
        options=["--dataflow-traces"],
    )
    report = json.loads(result.stdout)
    assert report["errors"] == []
    observed = {}
    for finding in report["results"]:
        rule = finding["check_id"].rsplit(".", 1)[-1]
        trace = finding["extra"]["dataflow_trace"]
        kind, (source, content) = trace["taint_source"]
        assert kind == "CliLoc"
        observed[rule] = (
            finding["start"]["line"],
            source["start"]["line"],
            source["start"]["col"],
            source["end"]["col"],
            content,
        )
    assert len(report["results"]) == 4
    assert observed == {
        "conjunction": (4, 2, 9, 26, "source_a(context)"),
        "disjunction": (6, 2, 9, 26, "source_a(context)"),
        "negative": (8, 1, 11, 21, "source_b()"),
        "nested": (10, 2, 9, 26, "source_a(context)"),
    }
