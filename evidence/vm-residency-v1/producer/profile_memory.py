"""Replay sampled whole-host GPU deltas; never claim isolated model residency."""
import argparse
from datetime import datetime
import json
from pathlib import Path

MIB=1024**2
DEFAULT_LIMIT_BYTES=14_000_000_000


def summarize_memory(samples,case_id,limit_bytes=DEFAULT_LIMIT_BYTES):
    if type(limit_bytes)is not int or limit_bytes<=0:
        raise ValueError('limit_bytes must be a positive integer')
    valid=[row for row in samples if type(row.get('used_mib'))is int and row['used_mib']>=0]
    baseline=[row['used_mib']for row in valid if row.get('stage')in ('baseline-start','baseline-end')]
    prefixes=('loading-'+str(case_id),'tests-'+str(case_id))
    case=[row for row in valid if any(row.get('stage')==prefix or row.get('stage','').startswith(prefix+'-')for prefix in prefixes)]
    if not baseline or len(case)<2:
        raise ValueError('Require stopped-baseline samples and at least two valid case samples')
    ordered=sorted(case,key=lambda row:datetime.fromisoformat(row['at']))
    gaps=[(datetime.fromisoformat(b['at'])-datetime.fromisoformat(a['at'])).total_seconds()for a,b in zip(ordered,ordered[1:])]
    minimum=min(baseline)
    peak=max(row['used_mib']for row in case)
    if peak<minimum:
        raise ValueError('Case occupancy below the entire stopped baseline; delta is inconclusive')
    delta=peak-minimum
    return {'case_id':str(case_id),'baseline_range_mib':[minimum,max(baseline)],'sampled_peak_host_used_mib':peak,
        'conservative_host_delta_mib':delta,'delta_bytes_derived_from_mib':delta*MIB,
        'limit_bytes':limit_bytes,'within_sampled_delta_limit':delta*MIB<=limit_bytes,
        'valid_case_samples':len(case),'largest_valid_case_sample_gap_seconds':max(gaps),
        'sampling_error_rows':sum('sampling_error'in row for row in samples),
        'scope':'Sampled whole-host occupancy minus the lower stopped baseline; desktop drift and unsampled transients remain confounds. Not isolated per-allocation residency.'}


def summarize_vm_memory(samples, case_id, limit_bytes=DEFAULT_LIMIT_BYTES,
                        minimum_load_bytes=10_000_000_000, maximum_gap_seconds=5):
    """Bound the containing VM's dedicated usage, including every counter alias."""
    if type(limit_bytes) is not int or limit_bytes <= 0:
        raise ValueError('limit_bytes must be a positive integer')
    if type(minimum_load_bytes) is not int or minimum_load_bytes < 0:
        raise ValueError('minimum_load_bytes must be a nonnegative integer')
    if isinstance(maximum_gap_seconds, bool) or not isinstance(maximum_gap_seconds, (int, float)) or not 0 < maximum_gap_seconds <= 60:
        raise ValueError('maximum_gap_seconds must be finite and in (0,60]')
    prefixes = ('loading-' + str(case_id), 'tests-' + str(case_id))
    baseline, case, baseline_stages = [], [], set()
    for row in samples:
        stage = row.get('stage', '')
        is_case = any(stage == prefix or stage.startswith(prefix + '-') for prefix in prefixes)
        if stage not in ('baseline-start', 'baseline-end') and not is_case:
            continue
        if not is_case:
            baseline_stages.add(stage)
        identities = row.get('vm_processes', [])
        counters = row.get('counters', [])
        if row.get('sampling_error') or not identities or not counters:
            raise ValueError('Missing or failed VM counter sample')
        if any(type(p.get('pid')) is not int or p['pid'] <= 0 or p.get('name') != 'vmwp' for p in identities):
            raise ValueError('Unverified VM process identity')
        ids = {p['pid'] for p in identities}
        names = set()
        for counter in counters:
            name = counter.get('instance', '')
            if type(counter.get('pid')) is not int or counter.get('pid') not in ids or not name.startswith('pid_' + str(counter['pid']) + '_') or name in names:
                raise ValueError('Unmatched or duplicate counter instance')
            names.add(name)
            if any(type(counter.get(key)) is not int or counter[key] < 0 for key in ('dedicated_bytes', 'shared_bytes', 'committed_bytes')):
                raise ValueError('Invalid GPU counter byte value')
        values = {'at': row['at'], 'dedicated': sum(c['dedicated_bytes'] for c in counters),
                  'shared': sum(c['shared_bytes'] for c in counters), 'instances': len(counters)}
        (case if is_case else baseline).append(values)
    if len(case) < 2 or baseline_stages != {'baseline-start', 'baseline-end'}:
        raise ValueError('Require VM baseline and at least two case samples')
    ordered = sorted(case, key=lambda r: datetime.fromisoformat(r['at']))
    gaps = [(datetime.fromisoformat(b['at']) - datetime.fromisoformat(a['at'])).total_seconds() for a, b in zip(ordered, ordered[1:])]
    gap = max(gaps)
    if gap > maximum_gap_seconds:
        raise ValueError('VM sampling gap exceeds the predeclared bound')
    peak = max(r['dedicated'] for r in case)
    baseline_min = min(r['dedicated'] for r in baseline)
    increase = peak - baseline_min
    if increase < minimum_load_bytes:
        raise ValueError('VM counter change does not cover the expected model allocation')
    return {'case_id': str(case_id), 'peak_all_vm_dedicated_bytes': peak,
            'peak_all_vm_dedicated_mib': peak / MIB, 'peak_all_vm_shared_bytes': max(r['shared'] for r in case),
            'stopped_vm_dedicated_range_bytes': [baseline_min, max(r['dedicated'] for r in baseline)],
            'observed_load_increase_bytes': increase, 'minimum_load_bytes': minimum_load_bytes,
            'limit_bytes': limit_bytes, 'sampled_vm_dedicated_under_limit': peak < limit_bytes,
            'valid_case_samples': len(case), 'largest_case_gap_seconds': gap,
            'maximum_instance_count': max(r['instances'] for r in case),
            'scope': 'Direct Windows dedicated GPU-memory counters summed across all VM processes/instances; may overcount shared allocations. No desktop subtraction. A containing-VM upper bound, not an exact isolated model value or continuous-time peak.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('samples',type=Path)
    parser.add_argument('--case',required=True)
    parser.add_argument('--limit-bytes',type=int,default=DEFAULT_LIMIT_BYTES)
    parser.add_argument('--scope', choices=('host', 'vm'), default='host')
    options=parser.parse_args()
    rows=[json.loads(line)for line in options.samples.read_text(encoding='utf-8').splitlines()if line.strip()]
    summarize = summarize_vm_memory if options.scope == 'vm' else summarize_memory
    print(json.dumps(summarize(rows,options.case,options.limit_bytes),indent=2))


if __name__=='__main__':main()
