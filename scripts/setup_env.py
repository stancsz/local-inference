"""Create only this gateway's local authentication key; never print its value."""
import os
from pathlib import Path
import secrets

ROOT=Path(__file__).resolve().parents[1]

def gateway_key():
    key=os.environ.get('LOCAL_GATEWAY_KEY')
    if key: return key
    path=ROOT/'.env'
    if path.exists():
        for line in path.read_text().splitlines():
            if line.startswith('LOCAL_GATEWAY_KEY='): return line.split('=',1)[1].strip()
    raise RuntimeError('Run python scripts/setup_env.py first')

def main():
    path=ROOT/'.env'
    previous=path.read_text() if path.exists() else ''
    if 'LOCAL_GATEWAY_KEY=' not in previous:
        with path.open('a') as stream:
            stream.write(('\n' if previous and not previous.endswith('\n') else '')+'LOCAL_GATEWAY_KEY=sk-'+secrets.token_hex(32)+'\n')
    print('Local gateway key configured in ignored .env; value hidden.')

if __name__=='__main__': main()
