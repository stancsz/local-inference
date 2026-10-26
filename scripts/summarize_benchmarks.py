"""Summarize only observed timings; never treat throughput as task-quality proof."""
import json
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parents[1]
def main():
    pairs=[('mtp-64k-ubatch64','no-mtp-64k-ubatch64')]
    rows=[]
    for accelerated,baseline in pairs:
        fast=json.loads((ROOT/'evidence'/f'benchmark-{accelerated}.json').read_text())
        slow=json.loads((ROOT/'evidence'/f'benchmark-{baseline}.json').read_text())
        assert all(x['timings'].get('draft_n',0)>0 for x in fast)
        assert all(x['timings'].get('draft_n',0)==0 for x in slow)
        a=statistics.mean(x['timings']['predicted_per_second'] for x in fast)
        b=statistics.mean(x['timings']['predicted_per_second'] for x in slow)
        rows.append({'mtp_label':accelerated,'baseline_label':baseline,'samples_per_arm':len(fast),'mtp_decode_tps':a,'baseline_decode_tps':b,'decode_speedup':a/b,'mtp_mean_wall_seconds':statistics.mean(x['seconds'] for x in fast),'baseline_mean_wall_seconds':statistics.mean(x['seconds'] for x in slow),'output_tokens_per_sample':256,'scope':'Sequential short-prompt microbenchmark, one cold/one cached sample per arm. Outputs are not identical; this is not correctness-parity or general productivity evidence.'})
    (ROOT/'evidence/benchmark-summary.json').write_text(json.dumps(rows,indent=2))
    print(json.dumps(rows,indent=2))

if __name__=='__main__': main()
