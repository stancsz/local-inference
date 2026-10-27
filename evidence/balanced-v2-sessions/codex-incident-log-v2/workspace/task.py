import json
import math
from pathlib import Path


def audit_events(jsonl_text):
    if not isinstance(jsonl_text, str):
        raise ValueError('jsonl_text must be a string')
    result = {
        'count': 0,
        'ok': 0,
        'errors': 0,
        'total_duration_ms': 0,
        'services': {},
    }
    for line in jsonl_text.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError('invalid JSON row') from exc
        if not isinstance(event, dict):
            raise ValueError('event must be a JSON object')
        for field in ('service', 'status', 'duration_ms'):
            if field not in event:
                raise ValueError('missing required field: ' + field)
        service = event['service']
        status = event['status']
        duration = event['duration_ms']
        if not isinstance(service, str) or not service.strip():
            raise ValueError('service must be a nonempty string')
        if status not in ('ok', 'error'):
            raise ValueError("status must be exactly 'ok' or 'error'")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration < 0:
            raise ValueError('duration_ms must be a finite nonnegative number')
        result['count'] += 1
        if status == 'ok':
            result['ok'] += 1
        else:
            result['errors'] += 1
        result['total_duration_ms'] += duration
        service = service.strip()
        entry = result['services'].get(service)
        if entry is None:
            entry = {'count': 0, 'errors': 0, 'duration_ms': 0}
            result['services'][service] = entry
        entry['count'] += 1
        if status == 'error':
            entry['errors'] += 1
        entry['duration_ms'] += duration
    return result


def audit_file(path):
    text = Path(path).read_text(encoding='utf-8')
    return audit_events(text)


def render_markdown(report):
    lines = [
        '# Incident summary',
        f"Count: {report['count']}",
        f"OK: {report['ok']}",
        f"Errors: {report['errors']}",
    ]
    for service, entry in report['services'].items():
        lines.append(f"- {service}: {entry['count']} events, {entry['errors']} errors, {entry['duration_ms']} ms")
    return '\n'.join(lines) + '\n'
