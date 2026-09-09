import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(PACKAGE))
from build_support.test_execution import TestCapacity, TestProcessResult

spec = importlib.util.spec_from_file_location('opengrep_verify', PACKAGE / 'verify.py')
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


class ContractFailures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.capacity = TestCapacity(8, 16, 3, 'environment')

    def test_upstream_annotations_preserve_required_and_quiet_lines(self):
        source = self.root / 'upstream.c'
        source.write_text('/* ruleid: first, second */\nsink(value);\n'
                          '//ERROR: exact upstream pattern expectation\nmatch(value);\n'
                          '/* ok: first */\nsink(safe);\n'
                          '// OK: a quiet alternative\nother(value);\n')
        self.assertEqual(verify.expected_findings(source, [{'id': 'pattern'}]),
                         {('first', 2), ('second', 2), ('pattern', 4)})

    def test_upstream_pattern_annotation_rejects_ambiguous_rule_identity(self):
        source = self.root / 'upstream.php'
        source.write_text('//ERROR:\ncall();\n')
        for rules in ([], [{'id': 'first'}, {'id': 'second'}]):
            with self.subTest(rules=rules), self.assertRaisesRegex(ValueError, 'exactly one rule'):
                verify.expected_findings(source, rules)

    def test_existing_annotation_formats_remain_exact(self):
        source = self.root / 'annotations.txt'
        source.write_text('# ruleid: python\ncall()\n// ruleid: javascript\ncall()\n'
                          ';; ruleid: scheme\n(call)\n(* ruleid: ocaml *)\ncall()\n'
                          'plain prose ERROR: ignore\ncall()\n')
        self.assertEqual(verify.expected_findings(source, [{'id': 'unused'}]),
                         {('python', 2), ('javascript', 4), ('scheme', 6), ('ocaml', 8)})

    def test_timeout_is_structured_and_remaining_cases_run(self):
        cases = [({'name': 'slow', 'valid': True}, {}), ({'name': 'next', 'valid': True}, {})]
        results = [TestProcessResult([], -9, 'partial', 'diagnostic', True, 360, 360),
                   TestProcessResult([], 0, '{"results":[],"errors":[]}', '', False, 1, 360)]
        with patch.object(verify, 'rule_validation_cases', return_value=iter(cases)), \
                patch.object(verify, 'run_test_process', side_effect=results) as run:
            rows = list(verify.verify_rule_validation(Path('/scanner'), self.root / 'cases', self.capacity))
        self.assertEqual([row['passed'] for row in rows], [False, True])
        self.assertEqual(rows[0]['status'], 'execution-incomplete')
        self.assertEqual(rows[0]['execution']['stderr'], 'diagnostic')
        self.assertEqual(rows[0]['execution']['capacity']['timeout_scale'], 3)
        self.assertEqual(run.call_args.kwargs['timeout'], 360)
        command = run.call_args.args[0]
        self.assertEqual(command[command.index('--timeout') + 1], '0')
        self.assertEqual(command[command.index('--jobs') + 1], '1')

    def test_missing_or_malformed_report_cannot_pass(self):
        for output in ('', 'truncated{', '{}', '[]'):
            with self.subTest(output=output), patch.object(verify, 'run_test_process', return_value=
                    TestProcessResult([], 0, output, 'stderr', False, 1, 360)):
                report, outcome = verify.scan_contract(Path('/scanner'), self.root / 'rule', self.root / 'source',
                                                        self.root, self.capacity, output_file=False)
                self.assertIsNone(report)
                self.assertFalse(outcome['passed'])
                self.assertEqual(outcome['execution']['stderr'], 'stderr')

    def test_missing_executable_is_an_incomplete_case(self):
        with patch.object(verify, 'run_test_process', side_effect=FileNotFoundError('scanner missing')):
            report, outcome = verify.scan_contract(Path('/scanner'), self.root / 'rule', self.root / 'source',
                                                    self.root, self.capacity)
        self.assertIsNone(report)
        self.assertEqual(outcome['status'], 'execution-incomplete')

    def test_malformed_output_file_survives_scratch_directory_cleanup(self):
        raw = '{"results":[null],"errors":[]}'
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            def scan(*_args, **_kwargs):
                (directory / 'report.json').write_text(raw)
                return TestProcessResult([], 0, '', 'diagnostic', False, 1, 360)
            with patch.object(verify, 'run_test_process', side_effect=scan):
                report, outcome = verify.scan_contract(Path('/scanner'), directory / 'rule', directory / 'source',
                                                        directory, self.capacity)
        self.assertIsNone(report)
        self.assertEqual(outcome['status'], 'execution-incomplete')
        self.assertEqual(outcome['execution']['report_output'], raw)
        self.assertEqual(outcome['execution']['stderr'], 'diagnostic')

    def test_nested_invalid_output_records_failure_and_continues(self):
        invalid = [
            {'results': [None], 'errors': []},
            {'results': [{'path': 'source'}], 'errors': []},
            {'results': [], 'errors': [None]},
            {'results': [], 'errors': [{'type': []}]},
            {'results': [], 'errors': [{'type': ['PartialSemantics', 'x'], 'spans': [{}]}]},
            {'results': [], 'errors': [], 'paths': {'scanned': [None]}},
        ]
        for index, report in enumerate(invalid):
            with self.subTest(report=report):
                cases = [({'name': 'invalid', 'valid': True}, {}), ({'name': 'next', 'valid': True}, {})]
                results = [TestProcessResult([], 0, json.dumps(report), 'diagnostic', False, 1, 360),
                           TestProcessResult([], 0, '{"results":[],"errors":[]}', '', False, 1, 360)]
                with patch.object(verify, 'rule_validation_cases', return_value=iter(cases)), \
                        patch.object(verify, 'run_test_process', side_effect=results):
                    rows = list(verify.verify_rule_validation(Path('/scanner'), self.root / str(index), self.capacity))
                self.assertEqual([row['passed'] for row in rows], [False, True])
                self.assertEqual(rows[0]['status'], 'execution-incomplete')
                self.assertEqual(rows[0]['execution']['stderr'], 'diagnostic')

    def test_same_line_matches_are_distinct_but_duplicate_ranges_fail(self):
        finding = {'check_id': 'rule', 'path': '/source', 'start': {'offset': 1}, 'end': {'offset': 3}}
        other = {**finding, 'start': {'offset': 5}, 'end': {'offset': 7}}
        self.assertTrue(verify.unique_findings([finding, other]))
        self.assertFalse(verify.unique_findings([finding, other, dict(finding)]))

    def test_schema_error_snippets_have_unknown_offsets_but_source_spans_do_not(self):
        error = {'type': 'InvalidRuleSchemaError', 'spans': [
            {'file': '<No file>', 'start': {'line': 1, 'col': 1, 'offset': -1},
             'end': {'line': 1, 'col': 4, 'offset': -1}}]}
        report = {'results': [], 'errors': [error]}
        self.assertEqual(verify.parse_report(json.dumps(report)), report)
        for kind in (['PartialSemantics', 'construct'], ['PartialParsing', []]):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                verify.parse_report(json.dumps({'results': [], 'errors': [{**error, 'type': kind}]}))

    def test_newline_and_utf8_finding_endpoints_identify_original_bytes(self):
        source = self.root / 'source.txt'
        source.write_bytes('é\r\n'.encode())
        finding = {'path': str(source), 'start': {'line': 1, 'col': 1, 'offset': 0},
                   'end': {'line': 2, 'col': 1, 'offset': 4}}
        self.assertTrue(verify.valid_finding_positions([finding], source))
        for invalid_end in ({'line': 1, 'col': 1, 'offset': 4},
                            {'line': 1, 'col': 5, 'offset': 4},
                            {'line': 2, 'col': 1, 'offset': 3},
                            {'line': 2, 'col': 2, 'offset': 5}):
            with self.subTest(end=invalid_end):
                self.assertFalse(verify.valid_finding_positions([{**finding, 'end': invalid_end}], source))


if __name__ == '__main__':
    unittest.main()
