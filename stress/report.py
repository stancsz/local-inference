"""Reconcile campaign outcomes without changing acceptance or task artifacts."""
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
from statistics import median

ROOT=Path(__file__).resolve().parents[1]


def distribution(values):
    return {'samples':len(values),'minimum':min(values),'median':median(values),'maximum':max(values)} if values else {'samples':0}


def memory_aggregate():
    manifest=json.loads((ROOT/'evidence/stress-gpu-samples-manifest.json').read_text())
    compressed=(ROOT/manifest['file']).read_bytes()
    raw=gzip.decompress(compressed)
    assert hashlib.sha256(raw).hexdigest()==manifest['raw_sha256']
    assert hashlib.sha256(compressed).hexdigest()==manifest['compressed_sha256']
    samples=[json.loads(line) for line in raw.splitlines() if line.strip()]
    assert len(samples)==manifest['samples']
    gaps=[(datetime.fromisoformat(b['at'])-datetime.fromisoformat(a['at'])).total_seconds() for a,b in zip(samples,samples[1:])]
    result={'source':manifest['file'],'raw_sha256':manifest['raw_sha256'],'raw_bytes':len(raw),
        'samples':len(samples),'first':samples[0],'last':samples[-1],
        'host_used_mib':distribution([s['used_mib'] for s in samples]),
        'host_free_mib':distribution([s['free_mib'] for s in samples]),
        'sampling_gap_seconds':distribution(gaps),'units':'MiB =1048576 bytes',
        'scope':'Available sampling intervals only, with gaps. Total host occupancy includes desktop drift and is not isolated model+MTP residency, uninterrupted per-session coverage or proof of under14GB.'}
    (ROOT/'evidence/stress-memory-aggregate.json').write_text(json.dumps(result,indent=2))
    return result


def main():
    campaign=json.loads((ROOT/'evidence/stress-campaign.json').read_text())
    probes=json.loads((ROOT/'evidence/stress-contract-probes.json').read_text())
    probe_map={row['receipt']:row for row in probes['sessions']}
    rows=[];native_inputs=[];native_targets=[];output_reserves=[];windows=set()
    for row in campaign['sessions']:
        path=ROOT/row['receipt']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
        record=json.loads(path.read_text())
        assert record['source_sha256']==campaign['source_sha256']
        assert record['upstream']=='http://127.0.0.1:8090/v1'
        assert record['accepted']==row['accepted']
        native=record.get('native_gateway_audits',[])
        native_inputs.extend(a['native_input_tokens'] for a in native)
        native_targets.extend(a['target_tokens'] for a in native)
        output_reserves.extend(a['output_reserve'] for a in native)
        windows.update(a['context_window'] for a in native)
        bounds=bool(native) and all(a['native_input_tokens']+a['output_reserve']+a['decoder_headroom']<=a['context_window'] for a in native)
        turns=record['turns']
        strict_long=len(turns)>=9 and record['active_client_seconds']>180 and bool(record.get('session_id'))
        if record['accepted']:
            assert strict_long and bounds and all(t['accepted'] and t['hidden_tests_exit']==0 and t['historical_gold_passed'] for t in turns)
        probe=probe_map.get(row['receipt'])
        rows.append({**row,'nine_turn_long_session':strict_long,'native_budget_checks':len(native),
            'native_bounds_passed':bounds,'additional_contract_passed':probe['all_additional_checks_passed'] if probe else None})
        if not record['accepted']:
            last=turns[-1] if turns else {}
            rows[-1]['final_turn']={'timed_out':last.get('timed_out'),'hidden_tests_exit':last.get('hidden_tests_exit'),
                'historical_gold_passed':last.get('historical_gold_passed'),'native':last.get('native')}
    all_receipts=[]
    paths={r['receipt'] for r in rows}
    sift_modules=('sift.core','sift.dynamic','sift.litellm_proxy','sift.litellm_responses')
    published=json.loads((ROOT/'evidence/stress-published.json').read_text())
    published_hashes={row['receipt_raw_sha256'] for row in published['sessions'] if row.get('verified')}
    for path in sorted((ROOT/'tmp/stress/sessions').glob('*/result.json')):
        record=json.loads(path.read_text())
        if not record.get('accepted') and not record.get('failure'):
            continue
        relative=path.relative_to(ROOT).as_posix()
        all_receipts.append({'receipt':relative,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'client':record['client'],'task':record['task'],'accepted':bool(record.get('accepted')),
            'upstream':record.get('upstream'),'published_raw_evidence_verified':hashlib.sha256(path.read_bytes()).hexdigest() in published_hashes,
            'turns':len(record.get('turns',[])),'active_seconds':record.get('active_client_seconds',0),
            'source_matches_current':record.get('source_sha256')==campaign['source_sha256'],
            'sift_candidate_matches_current':all(record.get('source_sha256',{}).get(k)==campaign['source_sha256'][k] for k in sift_modules),
            'in_controller_outcomes':relative in paths})
    groups=[]
    for client in ('claude','opencode','codex'):
        group=[r for r in rows if r['case']['client']==client]
        accepted=[r for r in group if r['accepted']]
        groups.append({'client':client,'terminal_attempts':len(group),'harness_accepted':len(accepted),
            'nine_turn_long_sessions':sum(r['nine_turn_long_session'] for r in group),
            'accepted_tasks':dict(Counter(r['case']['task'] for r in accepted)),
            'accepted_active_seconds':distribution([r['active_client_seconds'] for r in accepted]),
            'additional_contract_failures':sum(r['additional_contract_passed'] is False for r in accepted)})
    tasks=[]
    for task in ('engineering','migration','expenses'):
        group=[r for r in rows if r['case']['task']==task]
        accepted=[r for r in group if r['accepted']]
        tasks.append({'task':task,'terminal_attempts':len(group),'harness_accepted':len(accepted),
            'accepted_active_seconds':distribution([r['active_client_seconds'] for r in accepted]),
            'additional_contract_failures':sum(r['additional_contract_passed'] is False for r in accepted)})
    memory=memory_aggregate()
    review_path=ROOT/'evidence/stress-independent-review.json'
    review=json.loads(review_path.read_text()) if review_path.exists() else None
    report={'captured_at':datetime.now(timezone.utc).isoformat(),'controller_state':campaign['state'],
        'planned_attempts':campaign['planned_sessions'],'terminal_attempts':len(rows),
        'harness_accepted':sum(r['accepted'] for r in rows),
        'nine_turn_long_sessions':sum(r['nine_turn_long_session'] for r in rows),
        'failed_attempts':sum(not r['accepted'] for r in rows),
        'native_budget_checks':sum(r['native_budget_checks'] for r in rows),
        'required_qualifying_sessions':21,'qualifying_shortfall':max(0,21-sum(r['nine_turn_long_session'] for r in rows)),
        'accepted_active_seconds':distribution([r['active_client_seconds'] for r in rows if r['accepted']]),
        'total_accepted_active_seconds':round(sum(r['active_client_seconds'] for r in rows if r['accepted']),3),
        'native_context':{'input_tokens':distribution(native_inputs),'target_tokens':distribution(native_targets),
            'output_reserve_tokens':distribution(output_reserves),'window_tokens':sorted(windows),'decoder_guard_tokens':256,
            'scope':'Final gateway native full-request counts, after the separate fixed32768 LiteLLM-counted first-stage compaction.'},
        'memory':memory,'groups':groups,'task_groups':tasks,'sessions':rows,'all_retained_terminal_receipts':all_receipts,
        'historical_accepted_nine_turn_samples_with_same_sift':[
            row for row in all_receipts if not row['source_matches_current'] and row['sift_candidate_matches_current']
            and row['accepted'] and row['turns']>=9 and row['active_seconds']>180
            and row['upstream']=='http://127.0.0.1:8090/v1' and row['published_raw_evidence_verified']],
        'independent_final_acceptance':review.get('verdict','UNVERIFIED') if review else 'pending',
        'independent_review_scopes':review.get('scopes',{}) if review else {},
        'full_goal_complete':False,
        'limits':[
            'Three synthetic task families use real native CLIs, persisted sessions, local Qwen and filesystem edits; this is not a production repository trial.',
            'Harness acceptance and selected posthoc contract probes are separate. Extra edge cases are not exhaustive or preregistered; no universal quality percentage follows.',
            'Historical and setup receipts remain listed separately and are excluded from the current matrix denominator.',
            'Active seconds measure client execution without idle padding. They are not decode tokens/second.',
            'No paired no-Sift ablation establishes whether compaction caused any task defect.',
        ]}
    (ROOT/'evidence/stress-summary.json').write_text(json.dumps(report,indent=2))
    lines=['# Local CLI stress results','',f"Checkpoint: {report['captured_at']}. Controller: **{campaign['state']}**. Final independent acceptance: **{report['independent_final_acceptance']}**.",'',
        f"{report['harness_accepted']} harness passes and {report['failed_attempts']} failed attempts among {len(rows)} terminal matrix attempts; {report['nine_turn_long_sessions']} reached nine turns and over 180 active seconds. The required 21-session target remains unmet: shortfall **{report['qualifying_shortfall']}**. The fixed plan has {campaign['planned_sessions']} attempts; failed one-turn attempts and older epochs are not promoted into current passes.",'',
        '| Client | Terminal attempts | Harness passes | Nine-turn long sessions | Median accepted active seconds | Added contract failures |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for group in groups:
        value=group['accepted_active_seconds'].get('median')
        timing=f'{value:.3f}' if value is not None else 'n/a'
        lines.append(f"| {group['client']} | {group['terminal_attempts']} | {group['harness_accepted']} | {group['nine_turn_long_sessions']} | {timing} | {group['additional_contract_failures']} |")
    timing=report['accepted_active_seconds']
    lines+=['',f"Accepted session active seconds: minimum {timing['minimum']:.3f}, median {timing['median']:.3f}, maximum {timing['maximum']:.3f}; total {report['total_accepted_active_seconds']:.3f}. These are long-context task durations, not the short-prompt decode benchmark.",'',
        'All three rejected expense attempts remain one-turn failures. Two repeatedly wrote code still failing category grouping. The final OpenCode sample (repeat 2, seed 2951) passed public/hidden tests and retained history, but reached 240 seconds before a successful CLI terminal event. It remains rejected. No outcome-based re-roll or timeout extension is allowed.','',
        'The nine-turn harness checks native tool workflows, hidden tests, historical-fact retention and session continuity. Selected additional contract probes expose narrower validation defects in generated artifacts despite workflow passes. See [per-artifact probes](../evidence/stress-contract-probes.json) and [complete outcome summary](../evidence/stress-summary.json).','']
    lines+=['| Task | Terminal attempts | Workflow passes | Added contract failures |','| --- | ---: | ---: | ---: |']
    lines.extend(f"| {t['task']} | {t['terminal_attempts']} | {t['harness_accepted']} | {t['additional_contract_failures']} |" for t in tasks)
    lines+=['',f"Final native context checks: {report['native_budget_checks']} requests, windows {sorted(windows)}, output reserve up to {max(output_reserves)} and a 256-token decoder guard. Native input range {min(native_inputs)} to {max(native_inputs)}. Source-matched accepted traces and published fixture bytes are reconciled in [publication review](../evidence/stress-published-fixture-review.json).",'',
        f"Memory: {memory['samples']} available host-GPU samples, {memory['host_used_mib']['minimum']} to {memory['host_used_mib']['maximum']} MiB used and {memory['host_free_mib']['minimum']} to {memory['host_free_mib']['maximum']} MiB free. Largest observed sampling gap: {memory['sampling_gap_seconds']['maximum']:.3f} seconds. This is whole-host occupancy with gaps and desktop drift; isolated model+MTP under 14 GB is unproven. [Hashed raw samples](../evidence/stress-gpu-samples-manifest.json).",'',
        'Separate evidence: [256k/1M synthetic context checks](../evidence/context-acceptance.json), [short decode/MTP benchmarks](../evidence/benchmark-summary.json), and [rejected attempt archive](../evidence/stress-rejected.json). These do not establish arbitrary semantic retention, task-level decode speed, or simultaneous 64k input under 14 GB.','']
    lines.extend('- '+limit for limit in report['limits'])
    if review:
        lines+=['',f"Independent review scopes: {json.dumps(review.get('scopes',{}),sort_keys=True)}. [Preserved verdict](../evidence/stress-independent-review.json), [review provenance and limits](../evidence/stress-independent-review-provenance.json), and [parent factual clarifications](../evidence/stress-independent-review-parent-response.json). The review execution phase reached its tool limit; a text-only nonauthor handoff assessed its captured observations and actual raw excerpts. No full-goal completion or unattended-production acceptance follows."]
    (ROOT/'docs/STRESS_RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({key:report[key] for key in ('controller_state','terminal_attempts','harness_accepted','nine_turn_long_sessions','failed_attempts','native_budget_checks')}))


if __name__=='__main__':main()
