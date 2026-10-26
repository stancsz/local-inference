"""Reconstruct the frozen candidate without editing either owner's Sift tree."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile
from setup_env import ROOT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-repo',type=Path,default=ROOT.parent/'sift')
    parser.add_argument('--destination',type=Path,default=ROOT/'tmp/stress/sift-candidate')
    args=parser.parse_args()
    record=json.loads((ROOT/'evidence/stress-candidate.json').read_text())
    patch=ROOT/'evidence/stress-candidate.patch'
    if hashlib.sha256(patch.read_bytes()).hexdigest()!=record['reproducible_patch_sha256']:
        raise ValueError('Candidate patch digest mismatch')
    destination=args.destination.resolve()
    destination.mkdir(parents=True,exist_ok=False)
    archive=subprocess.check_output(['git','-C',str(args.source_repo.resolve()),'archive','--format=zip',record['base']])
    with zipfile.ZipFile(io.BytesIO(archive)) as source:
        source.extractall(destination)
    subprocess.run(['git','-C',str(destination),'init','--initial-branch=stress-snapshot'],check=True,capture_output=True)
    subprocess.run(['git','-C',str(destination),'fetch','--no-tags',str(args.source_repo.resolve()),record['base']],check=True,capture_output=True)
    subprocess.run(['git','-C',str(destination),'update-ref','refs/heads/stress-snapshot','FETCH_HEAD'],check=True)
    subprocess.run(['git','-C',str(destination),'read-tree','HEAD'],check=True)
    subprocess.run(['git','-C',str(destination),'apply','--whitespace=nowarn',str(patch)],check=True)
    for name,expected in record['canonical_files'].items():
        actual=hashlib.sha256((destination/name).read_text(encoding='utf-8').encode()).hexdigest()
        if actual!=expected: raise ValueError(f'Candidate source mismatch: {name}')
    print(f'Frozen candidate reconstructed and verified in {destination}')


if __name__=='__main__':main()
