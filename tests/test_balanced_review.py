"""Artifact review must not invent terminal success or trust altered captures."""
import hashlib
import json
import pytest
from stress.balanced_review_v2 import inspect_capture, review


def capture():
    raw=json.dumps({'request_index':0,'gold_retained':True,'historical_excerpt_messages':[{'content':'source fact'}],'needle_matches':[{'lines':['acceptance_delay_seconds=37']}]}).encode()
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
