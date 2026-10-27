"""Bind validated CLI artifacts to successful native edits and published hashes."""
import hashlib
import json
from pathlib import Path
from setup_env import ROOT

NAMES={'vram-plan':'VRAM_PLAN.md','model-audit':'MODEL_AUDIT.json','operator-guide':'OPERATIONS.md'}

def publish(row, *, trace_directory=None, destination=None):
    path=ROOT/row['artifact']
    trace_directory=trace_directory or ROOT/'tmp/acceptance'
    destination=destination or ROOT/'evidence/tasks'
    events=[json.loads(s) for s in (trace_directory/f"{row['task']}.jsonl").read_text(encoding='utf-8').splitlines() if s.startswith('{')]
    successful=set()
    for event in events:
        if event.get('type')=='user':
            for block in event.get('message',{}).get('content',[]):
                if isinstance(block,dict) and block.get('type')=='tool_result' and not block.get('is_error') and '<tool_use_error>' not in str(block.get('content')):
                    successful.add(block['tool_use_id'])
    reconstructed='PENDING_LOCAL_ACCEPTANCE\n'
    edits=0
    first_edit_index=None
    for event_index,event in enumerate(events):
        if event.get('type')!='assistant': continue
        for block in event.get('message',{}).get('content',[]):
            if block.get('type')!='tool_use' or block.get('name')!='Edit' or block['id'] not in successful: continue
            args=block['input']
            assert Path(args['file_path']).resolve()==path.resolve(),'Native edit targeted a different file'
            old=args['old_string']
            assert old and old in reconstructed,'Native edit does not match prior artifact state'
            reconstructed=reconstructed.replace(old,args['new_string'],-1 if args.get('replace_all') else 1)
            if first_edit_index is None: first_edit_index=event_index
            edits+=1
    assert edits and reconstructed.rstrip('\r\n')==path.read_text(encoding='utf-8').rstrip('\r\n'),'Artifact differs from successful native edits'
    published=destination/NAMES[row['task']]
    published.parent.mkdir(parents=True,exist_ok=True)
    published.write_bytes(path.read_bytes())
    allowed={ROOT/p for p in ['README.md','compose.yaml','gateway.yaml','evidence/host-vram.json','evidence/runtime-vram.json','evidence/model-manifest.json']}
    sources=[]
    for event_index,event in enumerate(events):
        if event_index>=first_edit_index: break
        result=event.get('tool_use_result',{})
        if not isinstance(result,dict) or result.get('type')!='text': continue
        file=result.get('file',{})
        original=Path(file.get('filePath',''))
        if original not in allowed or file.get('startLine')!=1 or file.get('numLines')!=file.get('totalLines'): continue
        snapshot=destination/'sources'/row['task']/original.name
        snapshot.parent.mkdir(parents=True,exist_ok=True)
        snapshot.write_text(file['content'],encoding='utf-8')
        sources.append({'original':original.relative_to(ROOT).as_posix(),'snapshot':snapshot.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),'complete_native_read':True,'before_first_artifact_edit':True})
    required={'vram-plan':{'host-vram.json','runtime-vram.json','model-manifest.json'},'model-audit':{'model-manifest.json','compose.yaml'},'operator-guide':{'README.md','compose.yaml','gateway.yaml'}}
    assert required[row['task']]<={Path(s['original']).name for s in sources},'Missing required complete source reads before artifact edit'
    return dict(row,published_artifact=published.relative_to(ROOT).as_posix(),artifact_sha256=hashlib.sha256(published.read_bytes()).hexdigest(),native_edit_reconstruction_matches=True,source_snapshots=sources)

def main():
    path=ROOT/'evidence/claude-acceptance.json'
    rows=json.loads(path.read_text())
    assert {r['task'] for r in rows}==set(NAMES) and all(r['passed'] for r in rows)
    rows=[publish(row) for row in rows]
    path.write_text(json.dumps(rows,indent=2))
    print('Three accepted artifacts match native edits and published SHA256 hashes')

if __name__=='__main__': main()
