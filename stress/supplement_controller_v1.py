"""Run only the sealed prospective supplement; no retries or count promotion."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from setup_env import gateway_key

def utc():
    return datetime.now(timezone.utc).isoformat()

def dump(path, data):
    pending = path.with_suffix('.pending')
    pending.write_text(json.dumps(data, indent=2), encoding='utf-8')
    pending.replace(path)

def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()

def main():
    plan_path = ROOT / 'evidence/supplement-v1-plan.json'
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    committed = subprocess.check_output(['git', 'show', 'HEAD:evidence/supplement-v1-plan.json'], cwd=ROOT)
    assert json.loads(committed) == plan, 'Plan is not committed'
    assert plan['sealed'] and len(plan['cases']) == 2
    baseline = json.loads((ROOT / 'evidence/stress-campaign.json').read_text())
    assert baseline['qualifying_long_sessions'] == 19
    from stress.cli_campaign import source_hashes
    def verify():
        assert source_hashes() == baseline['source_sha256'], 'Frozen implementation changed'
        assert all(digest(p) == h for p, h in plan['new_source_sha256'].items()), 'Supplement source changed'
        image = subprocess.check_output(['docker', 'inspect', 'local-inference-gateway-1', '--format', '{{.Image}}'], text=True).strip()
        assert image == plan['gateway_image'], 'Gateway image changed'
    verify()
    output = ROOT / 'tmp/supplement-v1'
    output.mkdir(exist_ok=False)
    state_path = ROOT / 'evidence/supplement-v1-state.json'
    state = {'state': 'running', 'controller_pid': os.getpid(), 'started_at': utc(),
             'plan_sha256': digest('evidence/supplement-v1-plan.json'),
             'plan_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
             'original_qualifying_sessions': 19, 'supplement_qualifying_sessions': 0,
             'candidate_aggregate_sessions': 19, 'final_independent_acceptance': 'pending',
             'full_goal_complete': False, 'cases': []}
    dump(state_path, state)
    stop = threading.Event()
    def sample_gpu():
        with (output / 'gpu-samples.jsonl').open('w', encoding='utf-8') as stream:
            while not stop.is_set():
                try:
                    raw = subprocess.check_output(['nvidia-smi', '--query-gpu=memory.total,memory.used,memory.free', '--format=csv,noheader,nounits'], timeout=5, text=True).strip()
                    stream.write(json.dumps({'at': utc(), 'csv_total_used_free_mib': raw}) + '\n')
                    stream.flush()
                except Exception as error:
                    stream.write(json.dumps({'at': utc(), 'error': type(error).__name__}) + '\n')
                    stream.flush()
                stop.wait(5)
    monitor = threading.Thread(target=sample_gpu, daemon=True)
    monitor.start()
    try:
        for case in plan['cases']:
            verify()
            folder = output / case['id']
            args = [sys.executable, '-B', '-m', 'stress.supplement_campaign_v1', '--client', case['client'],
                    '--task', case['task'], '--seed', str(case['seed']), '--output-dir', str(folder),
                    '--minimum-seconds', '185', '--minimum-turns', '9', '--max-turns', '32', '--turn-timeout', '240']
            env = dict(os.environ)
            env['SIFT_ACCEPTANCE_API_KEY'] = gateway_key()
            item = {'id': case['id'], 'client': case['client'], 'task': case['task'], 'seed': case['seed'],
                    'started_at': utc(), 'receipt': str(folder / 'result.json'), 'status': 'running'}
            state['cases'].append(item)
            with (output / (case['id'] + '.stdout')).open('w', encoding='utf-8') as out, (output / (case['id'] + '.stderr')).open('w', encoding='utf-8') as err:
                child = subprocess.Popen(args, cwd=ROOT, env=env, stdout=out, stderr=err)
                item['runner_pid'] = child.pid
                dump(state_path, state)
                try:
                    code = child.wait(timeout=32 * 240 + 900)
                except subprocess.TimeoutExpired:
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'], capture_output=True)
                    else:
                        child.kill()
                    child.wait(timeout=20)
                    item.update(status='terminal_controller_timeout', exit_code=child.returncode, accepted=False)
                    raise RuntimeError('Bounded session controller deadline reached; child stopped')
            verify()
            receipt = json.loads((folder / 'result.json').read_text(encoding='utf-8')) if (folder / 'result.json').exists() else {}
            qualified = bool(receipt.get('accepted')) and code == 0
            item.update(status='terminal', finished_at=utc(), exit_code=code, accepted=qualified,
                        user_turns=len(receipt.get('turns', [])), active_seconds=receipt.get('active_client_seconds'), failure=receipt.get('failure'))
            state['supplement_qualifying_sessions'] += int(qualified)
            state['candidate_aggregate_sessions'] = 19 + state['supplement_qualifying_sessions']
            dump(state_path, state)
            print(json.dumps(item), flush=True)
        state['state'] = 'terminal_review_required'
    except Exception as error:
        state['state'] = 'terminal_controller_failure'
        state['error'] = type(error).__name__ + ': ' + str(error).replace(gateway_key(), '[REDACTED]')
    finally:
        stop.set()
        monitor.join(timeout=10)
        state['finished_at'] = utc()
        dump(state_path, state)
    print(str(state_path), flush=True)

if __name__ == '__main__':
    main()
