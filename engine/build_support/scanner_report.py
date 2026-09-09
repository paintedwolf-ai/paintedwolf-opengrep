"""Validate the scanner fields consumed by behavioral and frontend checks."""
import json


def position(value, *, unknown_offset=False):
    return (isinstance(value, dict)
            and all(type(value.get(key)) is int for key in ('line', 'col', 'offset'))
            and value['line'] >= 1 and value['col'] >= 1
            and value['offset'] >= (-1 if unknown_offset else 0))


def location(value, path_key, *, unknown_offset=False):
    return (isinstance(value, dict) and isinstance(value.get(path_key), str)
            and bool(value[path_key]) and position(value.get('start'), unknown_offset=unknown_offset)
            and position(value.get('end'), unknown_offset=unknown_offset)
            and (value['start']['offset'] == -1) == (value['end']['offset'] == -1)
            and value['start']['offset'] <= value['end']['offset'])


def diagnostic(value):
    if not isinstance(value, dict):
        return False
    kind = value.get('type')
    if isinstance(kind, list):
        if len(kind) != 2 or not isinstance(kind[0], str):
            return False
        if kind[0] == 'PartialSemantics' and not isinstance(kind[1], str):
            return False
        kind = kind[0]
    if not isinstance(kind, str) or not kind:
        return False
    if value.get('path') is not None and not isinstance(value['path'], str):
        return False
    spans = value.get('spans', [])
    # CLI schema errors use -1 for offsets into synthetic YAML snippets.
    if not isinstance(spans, list) or not all(
            location(span, 'file', unknown_offset=kind == 'InvalidRuleSchemaError') for span in spans):
        return False
    return kind not in ('PartialParsing', 'PartialSemantics') or bool(spans)


def parse_report(raw):
    report = json.loads(raw)
    if (not isinstance(report, dict) or not isinstance(report.get('results'), list)
            or not isinstance(report.get('errors'), list)):
        raise ValueError('scanner report is missing results or errors')
    for finding in report['results']:
        if (not location(finding, 'path') or not isinstance(finding.get('check_id'), str)
                or not isinstance(finding.get('extra', {}), dict)):
            raise ValueError('scanner report contains a malformed finding')
    if not all(diagnostic(error) for error in report['errors']):
        raise ValueError('scanner report contains a malformed diagnostic')
    paths = report.get('paths', {})
    if (not isinstance(paths, dict) or not isinstance(paths.get('scanned', []), list)
            or not all(isinstance(path, str) and path for path in paths.get('scanned', []))):
        raise ValueError('scanner report contains malformed scanned paths')
    return report
