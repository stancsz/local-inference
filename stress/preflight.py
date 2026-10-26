"""Native client/tool preflight through frozen Sift and local Qwen only."""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time

from stress.cli_acceptance import child_command,executable,make_app,native_evidence
from stress.cli_campaign import parse_events
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from setup_env import gateway_key,ROOT


def main():
    import uvicorn
    parser=argparse.ArgumentParser()
    parser.add_argument('--client',choices=['claude','opencode','codex'],required=True)
    parser.add_argument('--label',default='first')
    args=parser.parse_args()
    dest=ROOT/'tmp/stress'/f'preflight-{args.client}-{args.label}'
    dest.mkdir(exist_ok=False)
    workspace=dest/'workspace';workspace.mkdir()
    marker='LOCAL_QWEN_'+args.client.upper()+'_TOOLS_OK'
    (workspace/'probe.txt').write_text(marker)
    model='qwen3.8-27b-codex' if args.client=='codex' else 'qwen3.8-27b'
    audits=[]
    sock=socket.socket();sock.bind(('127.0.0.1',0))
    server=uvicorn.Server(uvicorn.Config(make_app('http://127.0.0.1:8090/v1',gateway_key(),model,32768,audits),access_log=False,log_level='critical'))
    thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
    while not server.started:time.sleep(.02)
    prompt='Use one native file-read tool (or shell read) to read probe.txt in the current directory. Reply with its exact marker and the APPROVED acceptance_delay_seconds from archived conversation evidence. Do not guess, write files, delegate, use network, or explore other files.'
    command,env=child_command(args.client,executable(args.client),dest/'home',f'http://127.0.0.1:{sock.getsockname()[1]}/v1',model,prompt)
    try:
        with (dest/'native.jsonl').open('w',encoding='utf-8') as out,(dest/'stderr.log').open('w',encoding='utf-8') as err:
            done=subprocess.run(command,cwd=workspace,env=env,stdout=out,stderr=err,timeout=180)
        events=parse_events((dest/'native.jsonl').read_text(encoding='utf-8'))
        native=native_evidence(args.client,events)
        text=json.dumps(events)
        passed=done.returncode==0 and native['terminal_success'] and native['calls']>0 and native['completed']==native['calls'] and marker in text and '37' in text and audits and all(a.get('upstream_status')==200 for a in audits) and any(a.get('compacted') for a in audits)
        receipt={'client':args.client,'model':model,'upstream':'http://127.0.0.1:8090/v1','exit':done.returncode,'native':native,'audits':audits,'passed':bool(passed)}
        (dest/'receipt.json').write_text(json.dumps(receipt,indent=2))
        print(json.dumps({'client':args.client,'passed':bool(passed),'native':native,'requests':len(audits)}),flush=True)
        return 0 if passed else 1
    finally:
        server.should_exit=True;thread.join(timeout=10);sock.close()


if __name__=='__main__':raise SystemExit(main())
