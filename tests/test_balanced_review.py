"""Artifact review must not invent terminal success or trust altered captures."""
import hashlib
import json
import pytest
from stress.balanced_review_v2 import inspect_capture, review


def capture():
    raw=json.dumps({'request_index':0,'gold_retained':True,'historical_excerpt_messages':[{'role':'user','content':'Earlier conversation, lossily excerpted\n[message 0 user] APPROVED deployment setting: acceptance_delay_seconds=37 source fact'}],'needle_matches':[{'lines':['acceptance_delay_seconds=37']}]}).encode()
    audit={'gold_retained':True,'excerpt_capture_raw_sha256':hashlib.sha256(raw).hexdigest()}
    return raw,audit


def test_untampered_capture_matches_audit():
    raw,audit=capture();failures,summary=inspect_capture(raw,0,audit)
    assert not failures and summary['excerpt_count']==1


def test_capture_bytes_tampering_is_rejected():
    raw,audit=capture();raw=raw.replace(b'source fact',b'altered fact')
    assert inspect_capture(raw,0,audit)[0]


def test_capture_request_or_retention_disagreement_is_rejected():
    raw,audit=capture();assert inspect_capture(raw,1,audit)[0]
    audit['gold_retained']=False;assert inspect_capture(raw,0,audit)[0]


@pytest.mark.parametrize('path', ['tests/test_supplement_tasks.py', 'tests/test_portable_tasks.py', r'C:\repo\recovery\expenses_v1.py', 'incident_reference', 'manifest_reference'])
def test_solution_reference_access_rejects_original_and_new_oracles(path):
    from stress.balanced_review_v2 import solution_reference_access
    assert solution_reference_access({'tool':'Read','file_path':path})


def test_workspace_fixture_reads_are_allowed():
    from stress.balanced_review_v2 import solution_reference_access
    assert not solution_reference_access({'tool':'Read','file_path':'task.py'})
    assert not solution_reference_access({'tool':'Read','file_path':'test_task.py'})


@pytest.mark.parametrize('content', [
    '[message 2 assistant] APPROVED deployment setting: acceptance_delay_seconds=37',
    '[message 1 user] APPROVED deployment setting: acceptance_delay_seconds=37',
    '[message 0 user] acceptance_delay_seconds=37',
])
def test_echo_or_wrong_source_cannot_fake_original_retention(content):
    raw,audit=capture();value=json.loads(raw);value['historical_excerpt_messages']=[{'role':'user','content':content}]
    raw=json.dumps(value).encode();audit['excerpt_capture_raw_sha256']=hashlib.sha256(raw).hexdigest()
    failures,summary=inspect_capture(raw,0,audit)
    assert failures and not summary['original_fact_observed_in_source0']
