from datetime import datetime,timedelta,timezone
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from profile_memory import MIB,summarize_memory


def row(second,stage,used):
    return {'at':(datetime(2026,10,27,tzinfo=timezone.utc)+timedelta(seconds=second)).isoformat(),
            'stage':stage,'used_mib':used}


def test_lower_final_baseline_can_reverse_an_initial_apparent_pass():
    samples=[row(0,'baseline-start',2040),row(1,'loading-16',15120),row(2,'tests-16-capacity',15210),row(3,'baseline-end',1674)]
    assert 15210-2040 < 14_000_000_000/MIB
    result=summarize_memory(samples,16)
    assert result['conservative_host_delta_mib']==13536
    assert not result['within_sampled_delta_limit']


def test_case_labels_have_boundaries_and_do_not_include_case_40():
    samples=[row(0,'baseline-start',1800),row(1,'tests-4',14000),row(2,'tests-4-local',14020),row(3,'tests-40',16000)]
    result=summarize_memory(samples,4)
    assert result['sampled_peak_host_used_mib']==14020
    assert result['valid_case_samples']==2


def test_limit_is_decimal_bytes_not_gibibytes():
    samples=[row(0,'baseline-start',1000),row(1,'tests-4',14400),row(2,'tests-4',14400)]
    result=summarize_memory(samples,4)
    assert result['delta_bytes_derived_from_mib']==13400*MIB
    assert not result['within_sampled_delta_limit']
    assert summarize_memory(samples,4,14*1024**3)['within_sampled_delta_limit']


def test_failed_samples_do_not_hide_valid_sampling_gaps():
    samples=[row(0,'baseline-start',1800),row(1,'tests-4',14000),
             {'at':row(2,'','')['at'],'stage':'tests-4','sampling_error':'nvidia-smi timeout'},row(11,'tests-4',14010)]
    result=summarize_memory(samples,4)
    assert result['largest_valid_case_sample_gap_seconds']==10
    assert result['sampling_error_rows']==1


@pytest.mark.parametrize('samples',[
    [],[row(1,'tests-4',14000),row(2,'tests-4',14000)],
    [row(0,'baseline-start',1800),row(1,'tests-4',14000)],
    [row(0,'baseline-start',15000),row(1,'tests-4',14000),row(2,'tests-4',14000)],
])
def test_missing_or_inconclusive_measurement_fails_closed(samples):
    with pytest.raises(ValueError):summarize_memory(samples,4)
