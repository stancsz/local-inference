import json
import math

def audit_events(jsonl_text):
    if not isinstance(jsonl_text, str):
        raise ValueError('jsonl_text must be a string')
    count=0
    ok=0
    errors=0
    total_duration_ms=0
    services={}
    for line in jsonl_text.splitlines():
        line=line.strip()
        if not line:
            continue
        try:
            event=json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError('invalid JSON row') from exc
        if not isinstance(event, dict):
            raise ValueError('row must be a JSON object')
        if 'service' not in event or 'status' not in event or 'duration_ms' not in event:
            raise ValueError('missing required field')
        service=event['service']
        status=event['status']
        duration_ms=event['duration_ms']
        if not isinstance(service, str) or not service.strip():
            raise ValueError('service must be a nonempty string')
        if status not in ('ok', 'error'):
            raise ValueError('status must be exactly ok or error')
        if isinstance(duration_ms, bool) or not isinstance(duration_ms, (int, float)) or not math.isfinite(duration_ms) or duration_ms < 0:
            raise ValueError('duration_ms must be a finite nonnegative int/float')
        count+=1
        if status=='ok':
            ok+=1
        elif status=='error':
            errors+=1
        total_duration_ms+=duration_ms
        service=service.strip()
        if service not in services:
            services[service]={'count':0,'errors':0,'duration_ms':0}
        services[service]['count']+=1
        services[service]['errors']+=1 if status=='error' else 0
        services[service]['duration_ms']+=duration_ms
    return {'count':count,'ok':ok,'errors':errors,'total_duration_ms':total_duration_ms,'services':services}

def audit_file(path):
    with open(path,'r',encoding='utf-8') as f:
        return audit_events(f.read())

def render_markdown(report):
    lines=['# Incident summary','']
    lines.append(f"Count: {report['count']}")
    lines.append(f"OK: {report['ok']}")
    lines.append(f"Errors: {report['errors']}")
    lines.append(f"Total duration ms: {report['total_duration_ms']}")
    lines.append('')
    lines.append('## Services')
    for name, stats in report['services'].items():
        lines.append(f"- {name}: count={stats['count']}, errors={stats['errors']}, duration_ms={stats['duration_ms']}")
    return '\n'.join(lines) + '\n'
