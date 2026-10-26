"""Compare measured cloud/local token shares; never infer a cloud-only baseline."""
import argparse
import hashlib
import json
from pathlib import Path


def tokens(path):
    text=path.read_text(encoding='utf-8-sig')
    try:
        document=json.loads(text)
    except json.JSONDecodeError:
        rows=[json.loads(line) for line in text.splitlines() if line.strip()]
        results=[row for row in rows if row.get('type')=='result']
        if len(results)!=1:
            raise ValueError(f'{path}: require exactly one terminal CLI result')
        document=results[0]
    if not isinstance(document,dict):
        raise ValueError(f'{path}: invalid receipt')
    usage=document.get('usage')
    if not isinstance(usage,dict):
        raise ValueError(f'{path}: missing provider usage')
    if 'prompt_tokens' in usage:
        fields=('prompt_tokens','completion_tokens')  # Cached tokens already included.
    else:
        fields=('input_tokens','output_tokens')
        fields+=tuple(k for k in ('cache_read_input_tokens','cache_creation_input_tokens') if k in usage)
    values=[usage.get(k) for k in fields]
    if any(type(value) is not int or value<0 for value in values):
        raise ValueError(f'{path}: incomplete or invalid token usage')
    return sum(values)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local',type=Path,nargs='+',required=True)
    parser.add_argument('--advisor',type=Path,nargs='+',required=True)
    parser.add_argument('--baseline-cloud-tokens',type=int)
    args=parser.parse_args()
    all_paths=args.local+args.advisor
    if len({p.resolve() for p in all_paths})!=len(all_paths):
        parser.error('Do not count a receipt twice')
    if args.baseline_cloud_tokens is not None and args.baseline_cloud_tokens<=0:
        parser.error('Baseline must be a positive measured token total for equivalent work')
    local=sum(tokens(path) for path in args.local)
    cloud=sum(tokens(path) for path in args.advisor)
    if not local+cloud:
        parser.error('Receipts contain no tokens')
    ratio=cloud/(local+cloud)
    report={'local_tokens':local,'cloud_advisor_tokens':cloud,'cloud_token_share_percent':ratio*100,
        'cloud_share_at_most_one_percent':ratio<=0.01,
        'cloud_token_reduction_percent':None,
        'scope':'Supplied provider usage only, including failed attempts when supplied. Cloud share is not savings against an equivalent cloud-only run. Include every retry/failed receipt; missing usage prevents a complete accounting claim. Electricity, hardware and price differences are excluded.'}
    report['receipts']=[{'role':role,'path':str(path),'tokens':tokens(path),
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        for role,paths in [('local',args.local),('advisor',args.advisor)] for path in paths]
    if args.baseline_cloud_tokens:
        report['measured_baseline_cloud_tokens']=args.baseline_cloud_tokens
        report['cloud_token_reduction_percent']=100*(1-cloud/args.baseline_cloud_tokens)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
