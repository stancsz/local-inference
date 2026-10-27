import json
import math

def audit_events(jsonl_text):
    if not isinstance(jsonl_text, str):
        raise ValueError("Input must be a string")
    count = 0
    ok = 0
    errors = 0
    total_duration_ms = 0
    services = {}
    for line in jsonl_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
        if not isinstance(obj, dict):
            raise ValueError("Row is not a JSON object")
        for field in ('service', 'status', 'duration_ms'):
            if field not in obj:
                raise ValueError(f"Missing required field: {field}")
        if not isinstance(obj['service'], str) or not obj['service'].strip():
            raise ValueError("service must be a nonempty string")
        if obj['status'] not in ('ok', 'error'):
            raise ValueError("status must be 'ok' or 'error'")
        duration = obj['duration_ms']
        if isinstance(duration, bool) or not isinstance(duration, (int, float)):
            raise ValueError("duration_ms must be a number")
        if not math.isfinite(duration) or duration < 0:
            raise ValueError("duration_ms must be finite and nonnegative")
        count += 1
        status = obj['status']
        service = obj['service']
        if status == 'ok':
            ok += 1
        elif status == 'error':
            errors += 1
        total_duration_ms += duration
        service = service.strip()
        if service not in services:
            services[service] = {'count': 0, 'errors': 0, 'duration_ms': 0}
        services[service]['count'] += 1
        if status == 'error':
            services[service]['errors'] += 1
        services[service]['duration_ms'] += duration
    return {
        'count': count,
        'ok': ok,
        'errors': errors,
        'total_duration_ms': total_duration_ms,
        'services': services
    }

def audit_file(path):
    from pathlib import Path
    text = Path(path).read_text(encoding='utf-8')
    return audit_events(text)

def render_markdown(report):
    lines = ['# Incident summary', f"Count: {report['count']}", f"OK: {report['ok']}", f"Errors: {report['errors']}"]
    for name, stats in report['services'].items():
        lines.append(f"- {name}: {stats['count']} events, {stats['errors']} errors, {stats['duration_ms']} ms")
    return '\n'.join(lines)
