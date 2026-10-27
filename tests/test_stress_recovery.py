"""Review acknowledgments preserve failed outcomes and require exact provenance."""
import hashlib
import json

import pytest

from stress.campaign import cases, reviewed_short_failure


def receipt(tmp_path, **updates):
    value={'accepted':False,'failure':'timeout','source_sha256':{'test':'frozen'},
           'upstream':'http://127.0.0.1:8090/v1','active_client_seconds':240,
           'turns':[{}],'session_id':'real-session'}
    value.update(updates)
    path=tmp_path/'result.json'
    path.write_text(json.dumps(value))
    return path,hashlib.sha256(path.read_bytes()).hexdigest()


def test_acknowledgment_keeps_failure(tmp_path):
    path,sha=receipt(tmp_path)
    value=reviewed_short_failure(path,sha,{'test':'frozen'})
    assert value['accepted'] is False
    assert len(value['turns'])==1
    assert hashlib.sha256(path.read_bytes()).hexdigest()==sha


@pytest.mark.parametrize('updates',[
    {'accepted':True}, {'source_sha256':{'test':'different'}},
    {'upstream':'http://127.0.0.1:4000/v1'}, {'failure':None},
    {'turns':[{},{}]},
])
def test_rejects_wrong_acknowledgment(tmp_path,updates):
    path,sha=receipt(tmp_path,**updates)
    with pytest.raises(ValueError):
        reviewed_short_failure(path,sha,{'test':'frozen'})


def test_rejects_modified_receipt(tmp_path):
    path,sha=receipt(tmp_path)
    path.write_text(path.read_text()+' ')
    with pytest.raises(ValueError,match='changed'):
        reviewed_short_failure(path,sha,{'test':'frozen'})


def test_original_plan_unchanged():
    plan=list(cases())
    assert len(plan)==21
    assert plan[16]=={'client':'opencode','task':'expenses','seed':1951,'repeat':1}
    assert {client:sum(row['client']==client for row in plan) for client in ('claude','opencode','codex')}=={
        'claude':7,'opencode':7,'codex':7}
