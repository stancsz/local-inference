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


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('samples',type=Path)
    parser.add_argument('--case',required=True)
    parser.add_argument('--limit-bytes',type=int,default=DEFAULT_LIMIT_BYTES)
    options=parser.parse_args()
    rows=[json.loads(line)for line in options.samples.read_text(encoding='utf-8').splitlines()if line.strip()]
    print(json.dumps(summarize_memory(rows,options.case,options.limit_bytes),indent=2))


if __name__=='__main__':main()
