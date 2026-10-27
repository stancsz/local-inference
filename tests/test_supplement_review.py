"""Reject false qualification before trusting a published supplement receipt."""
import pytest
from stress.supplement_review_v1 import basic_failures


def record():
    return {'accepted': True, 'client': 'codex', 'model': 'qwen3.8-27b-codex', 'active_client_seconds': 189,
        'session_id': 'same-native-session', 'upstream': 'http://127.0.0.1:8090/v1', 'target': 32768,
        'source_sha256': {'source': 'frozen'},
        'turns': [dict(accepted=True, duration_seconds=21, timed_out=False, client_exit=0, hidden_tests_exit=0, historical_gold_passed=True) for _ in range(9)],
        'native_gateway_audits': [dict(native_input_tokens=32000, output_reserve=4096, decoder_headroom=256, context_window=40960)],
        'audits': [dict(compacted=True, tool_results=1, gold_retained=True, forwarded_tokens=32000, upstream_status=200)]}


def test_valid_threshold_record_has_no_basic_failures():
    assert basic_failures(record(), {'source': 'frozen'}) == []


@pytest.mark.parametrize('failure', ['rejected', 'short', 'few-turns', 'clock', 'session', 'upstream', 'model', 'source', 'timeout', 'hidden', 'gold', 'native-overflow', 'no-native-audit', 'not-compacted', 'lost-source', 'status'])
def test_rejects_each_false_qualification(failure):
    value = record()
    if failure == 'rejected': value['accepted'] = False
    if failure == 'short': value['active_client_seconds'] = 180
    if failure == 'few-turns': value['turns'].pop()
    if failure == 'clock': value['active_client_seconds'] += 1
    if failure == 'session': value['session_id'] = None
    if failure == 'upstream': value['upstream'] = 'http://127.0.0.1:4000/v1'
    if failure == 'model': value['model'] = 'default'
    if failure == 'source': value['source_sha256'] = {}
    if failure == 'timeout': value['turns'][0]['timed_out'] = True
    if failure == 'hidden': value['turns'][0]['hidden_tests_exit'] = 1
    if failure == 'gold': value['turns'][0]['historical_gold_passed'] = False
    if failure == 'native-overflow': value['native_gateway_audits'][0]['native_input_tokens'] = 40960
    if failure == 'no-native-audit': value['native_gateway_audits'] = []
    if failure == 'not-compacted': value['audits'][0]['compacted'] = False
    if failure == 'lost-source': value['audits'][0]['gold_retained'] = False
    if failure == 'status': value['audits'][0]['upstream_status'] = 500
    assert basic_failures(value, {'source': 'frozen'})
