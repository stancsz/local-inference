import gzip
from pathlib import Path
import re
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import daily_acceptance as validator


def valid_plan():
    path=Path(__file__).resolve().parents[1]/'evidence/daily-feedback-v2-artifacts/v2/vram-plan/vram-plan.md.gz'
    return gzip.decompress(path.read_bytes()).decode('utf-8')


def test_nonexistent_process_gpu_property_is_rejected_even_with_nvidia_in_prose():
    text=re.sub(r'```powershell\s*\n.*?```',
        '```powershell\nGet-Process | Select-Object @{n="DedicatedMiB";e={$_.DedicatedMemory/1MB}}\n```',
        valid_plan(),flags=re.S)+'\nMeasurement reference: nvidia-smi.\n'
    errors=validator.validate_task_artifact('vram-plan',text,validator.load_sources())
    assert any('DedicatedMemory' in error for error in errors),errors


def test_real_gpu_verification_stays_accepted():
    assert validator.validate_task_artifact('vram-plan',valid_plan(),validator.load_sources())==[]


def test_warning_about_bad_process_property_does_not_reject_valid_command():
    text=valid_plan()+'\nDo not use Get-Process.DedicatedMemory; that property does not exist.\n'
    assert validator.validate_task_artifact('vram-plan',text,validator.load_sources())==[]
