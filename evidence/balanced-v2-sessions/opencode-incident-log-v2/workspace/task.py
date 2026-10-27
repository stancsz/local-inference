import json
import math

def audit_events(jsonl_text):
    if not isinstance(jsonl_text, str):
        raise ValueError('expected str')
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
            raise ValueError(f'invalid JSON: {e}')
        if not isinstance(obj, dict):
            raise ValueError('expected JSON object')
        for field in ('service', 'status', 'duration_ms'):
            if field not in obj:
                raise ValueError(f'missing field: {field}')
        service = obj['service']
        if not isinstance(service, str) or not service.strip():
            raise ValueError('service must be nonempty string')
        status = obj['status']
        if not isinstance(status, str) or status not in ('ok', 'error'):
            raise ValueError('status must be ok or error')
        duration = obj['duration_ms']
        if isinstance(duration, bool) or not isinstance(duration, (int, float)):
            raise ValueError('duration_ms must be finite nonnegative number')
        if not math.isfinite(duration) or duration < 0:
            raise ValueError('duration_ms must be finite nonnegative number')
        count += 1
        if status == 'ok':
            ok += 1
        else:
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
        'services': services,
    }

def audit_file(path):
    with open(path, encoding='utf-8') as f:
        return audit_events(f.read())

def render_markdown(report):
    lines = ['# Incident summary\n', f"Count: {report['count']}", f"OK: {report['ok']}", f"Errors: {report['errors']}"]
    for service, stats in report['services'].items():
        lines.append(f"{service}: count={stats['count']}, errors={stats['errors']}, duration_ms={stats['duration_ms']}")
    return '\n'.join(lines)
