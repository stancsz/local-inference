from copy import deepcopy
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from profile_memory import summarize_vm_memory


def row(stage, seconds, values):
    return {'stage': stage, 'at': (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)).isoformat(),
            'vm_processes': [{'pid': 7, 'name': 'vmwp'}],
            'counters': [{'pid': 7, 'instance': 'pid_7_luid_gpu_phys_0' + ('#' + str(i) if i else ''),
                          'dedicated_bytes': value, 'shared_bytes': 1, 'committed_bytes': value + 1}
                         for i, value in enumerate(values)]}


def samples():
    return [row('baseline-start', 0, [2]), row('loading-32', 1, [11, 1]),
            row('tests-32-capacity', 2, [12, 3]), row('baseline-end', 3, [4])]


def test_uses_direct_vm_total_without_subtracting_baseline_or_deduplicating_aliases():
    result = summarize_vm_memory(samples(), 32, limit_bytes=16, minimum_load_bytes=10)
    assert result['peak_all_vm_dedicated_bytes'] == 15
    assert result['observed_load_increase_bytes'] == 13
    assert result['maximum_instance_count'] == 2
    assert result['sampled_vm_dedicated_under_limit'] is True
    assert summarize_vm_memory(samples(), 32, limit_bytes=15, minimum_load_bytes=10)['sampled_vm_dedicated_under_limit'] is False


def test_case_labels_do_not_match_other_profiles():
    data = samples() + [row('tests-320-capacity', 4, [1000])]
    assert summarize_vm_memory(data, 32, limit_bytes=16, minimum_load_bytes=10)['peak_all_vm_dedicated_bytes'] == 15


@pytest.mark.parametrize('change', ['missing', 'error', 'wrong_pid', 'wrong_name', 'negative', 'duplicate'])
def test_bad_or_missing_counter_samples_fail_closed(change):
    data = deepcopy(samples())
    target = data[2]
    if change == 'missing': target['counters'] = []
    if change == 'error': target['sampling_error'] = 'provider failed'
    if change == 'wrong_pid': target['counters'][0]['pid'] = 8
    if change == 'wrong_name': target['vm_processes'][0]['name'] = 'unrelated'
    if change == 'negative': target['counters'][0]['dedicated_bytes'] = -1
    if change == 'duplicate': target['counters'].append(deepcopy(target['counters'][0]))
    with pytest.raises(ValueError): summarize_vm_memory(data, 32, minimum_load_bytes=10)


def test_missing_baseline_or_unrelated_load_is_not_mapping_proof():
    with pytest.raises(ValueError): summarize_vm_memory(samples()[1:3], 32, minimum_load_bytes=10)
    with pytest.raises(ValueError): summarize_vm_memory(samples()[:-1], 32, minimum_load_bytes=10)
    with pytest.raises(ValueError): summarize_vm_memory(samples(), 32, minimum_load_bytes=100)


def test_large_sampling_gap_fails_closed():
    data = samples()
    data[2]['at'] = row('unused', 10, [1])['at']
    with pytest.raises(ValueError): summarize_vm_memory(data, 32, minimum_load_bytes=10)
