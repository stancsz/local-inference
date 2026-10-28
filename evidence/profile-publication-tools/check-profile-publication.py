"""Verify immutable Git artifact blobs against the recorded raw/compressed hashes."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]
REPORTS=['evidence/long-profile-'+epoch+'/parent-review.json'for epoch in ('v1','v2','v3','v4','v5')]+[
    'evidence/codex-shared-mtp-v1-publication.json','evidence/shared-mtp-pair-v1-parent-review.json','evidence/shared-mtp-launcher-v1/parent-review.json','evidence/shared-mtp-review-v2.json','evidence/daily-review-v5.json','evidence/gpu-verification-v1/receipt.json',
    'evidence/test-discovery-v1/receipt.json','evidence/mtp-quantization-dryrun-v1/receipt.json']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit',default='HEAD')
    parser.add_argument('--output',type=Path)
    options=parser.parse_args()
    if options.commit.startswith('-'):parser.error('Commit must be a Git ref or object ID')
    commit=subprocess.check_output(['git','rev-parse','--verify',options.commit+'^{commit}'],cwd=ROOT,text=True).strip()
    assert re.fullmatch(r'[a-f0-9]{40,64}',commit)
    expected={}
    for report in REPORTS:
        content=subprocess.check_output(['git','show',commit+':'+report],cwd=ROOT)
        for row in json.loads(content)['artifacts']:
            path=row['path']
            assert path.startswith('evidence/')and '\n'not in path and '\r'not in path and '..'not in Path(path).parts
            value={'sha256':row.get('compressed_sha256',row.get('sha256',row.get('raw_sha256')))}
            if 'compressed_sha256'in row:value['decompressed_sha256']=row['raw_sha256']
            assert value['sha256']
            if path in expected:assert expected[path]==value
            expected[path]=value
    result=subprocess.run(['git','cat-file','--batch'],cwd=ROOT,
        input=''.join(commit+':'+path+'\n'for path in expected).encode(),capture_output=True,check=True)
    stream=io.BytesIO(result.stdout)
    for path,digests in expected.items():
        header=stream.readline().decode().strip().split()
        assert len(header)==3 and header[1]=='blob',(path,header)
        data=stream.read(int(header[2]));assert stream.read(1)==b'\n'
        assert hashlib.sha256(data).hexdigest()==digests['sha256'],path
        if 'decompressed_sha256'in digests:
            assert hashlib.sha256(gzip.decompress(data)).hexdigest()==digests['decompressed_sha256'],path
    assert not stream.read()
    proof={'artifact_commit':commit,'manifest_reports':REPORTS,'files_verified':len(expected),
        'mismatches':0,'qualification_increment':0,'full_goal':'NOT_READY'}
    if options.output:
        with options.output.open('x',encoding='utf-8')as target:json.dump(proof,target,indent=2)
    print(json.dumps(proof))


if __name__=='__main__':main()
