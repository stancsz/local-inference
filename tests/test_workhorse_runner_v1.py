from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from workhorse.run_v1 import inspect_native

def stream(path,old='PENDING\n',new='done\n'):
 return [
  {'type':'assistant','message':{'content':[{'type':'tool_use','id':'r','name':'Read','input':{'file_path':str(path)}}]}},
  {'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'r','content':'PENDING'}]}},
  {'type':'assistant','message':{'content':[{'type':'tool_use','id':'e','name':'Edit','input':{'file_path':str(path),'old_string':old,'new_string':new}}]}},
  {'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'e','content':'updated'}]}},
  {'type':'result','session_id':'fixed','is_error':False}]

def test_actual_edits_bind_to_artifact_and_required_reads(tmp_path):
 artifact=tmp_path/'answer.json';artifact.write_bytes(b'done\r\n')
 row=inspect_native(stream(artifact),tmp_path,artifact,'PENDING\n',{artifact})
 assert row['edit_reconstruction_matches'] and not row['missing_reads']and not row['scope_violations']

def test_claimed_success_without_native_edit_is_insufficient(tmp_path):
 artifact=tmp_path/'answer.json';artifact.write_text('done\n')
 row=inspect_native([{'type':'result','session_id':'fixed','is_error':False}],tmp_path,artifact,'PENDING\n',{artifact})
 assert row['terminal_success']and not row['edit_reconstruction_matches']and row['missing_reads']==['answer.json']

def test_outside_or_different_artifact_edit_is_rejected(tmp_path):
 artifact=tmp_path/'answer.json';artifact.write_text('done\n')
 row=inspect_native(stream(tmp_path.parent/'unexpected.json'),tmp_path,artifact,'PENDING\n',set())
 assert len(row['scope_violations'])==3 and not row['edit_reconstruction_matches']

def test_mismatched_edit_and_undeclared_shell_command_are_rejected(tmp_path):
 artifact=tmp_path/'answer.json';artifact.write_text('done\n');events=stream(artifact,old='wrong')
 events.insert(0,{'type':'assistant','message':{'content':[{'type':'tool_use','id':'b','name':'Bash','input':{'command':'python -c "print(1)"'}}]}})
 row=inspect_native(events,tmp_path,artifact,'PENDING\n',set())
 assert len(row['scope_violations'])==2 and not row['edit_reconstruction_matches']
