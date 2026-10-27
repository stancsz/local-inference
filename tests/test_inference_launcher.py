"""Execute the real POSIX launcher with only the server replaced by argv capture."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


def launch(**settings):
    shell = shutil.which('sh')
    if not shell:
        candidate = Path('C:/Program Files/Git/bin/sh.exe')
        shell = str(candidate) if candidate.exists() else None
    if not shell:
        pytest.skip('POSIX shell required to execute the inference launcher')
    script = (ROOT / 'docker/start-inference.sh').read_text(encoding='utf-8')
    script = script.replace('set -- /app/llama-server', "set -- printf '%s\\n'")
    script = script.replace('exec "$@"', '"$@"')
    env = {key: value for key, value in os.environ.items() if key not in {
        'SPEC_TYPE', 'MTP_MODEL_PATH', 'DRAFT_TOKENS', 'DRAFT_GPU_LAYERS',
        'CONTEXT_SIZE', 'GPU_LAYERS', 'UBATCH_SIZE',
    }}
    env.update(settings)
    return subprocess.run([shell, '-s'], input=script, text=True,
                          encoding='utf-8', env=env, capture_output=True, timeout=10)


def test_default_mtp_shares_target_weights():
    result = launch()
    assert result.returncode == 0, result.stderr
    args = result.stdout.splitlines()
    assert args[args.index('--spec-type') + 1] == 'draft-mtp'
    assert '--model-draft' not in args
    assert '--gpu-layers-draft' not in args
    assert args[args.index('--spec-draft-n-max') + 1] == '4'


def test_explicit_separate_draft_path_is_a_single_argument():
    result = launch(MTP_MODEL_PATH='/models/custom draft.gguf', DRAFT_GPU_LAYERS='7', DRAFT_TOKENS='2')
    assert result.returncode == 0, result.stderr
    args = result.stdout.splitlines()
    assert args[args.index('--model-draft') + 1] == '/models/custom draft.gguf'
    assert args[args.index('--gpu-layers-draft') + 1] == '7'
    assert args[args.index('--spec-draft-n-max') + 1] == '2'


def test_none_omits_all_draft_settings():
    result = launch(SPEC_TYPE='none', MTP_MODEL_PATH='/models/ignored.gguf')
    assert result.returncode == 0, result.stderr
    args = result.stdout.splitlines()
    assert args[args.index('--spec-type') + 1] == 'none'
    assert not any('draft' in arg for arg in args)


def test_unknown_spec_type_fails_closed():
    result = launch(SPEC_TYPE='invalid')
    assert result.returncode == 2
    assert not result.stdout
    assert 'SPEC_TYPE must be' in result.stderr
