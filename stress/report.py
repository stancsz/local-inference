"""Reconcile campaign outcomes without changing acceptance or task artifacts."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import median

ROOT=Path(__file__).resolve().parents[1]


def distribution(values):
    return {'samples':len(values),'minimum':min(values),'median':median(values),'maximum':max(values)} if values else {'samples':0}


def main():
    campaign=json.loads((ROOT/'evidence/stress-campaign.json').read_text())
    probes=json.loads((ROOT/'evidence/stress-contract-probes.json').read_text())
    probe_map={row['receipt']:row for row in probes['sessions']}
    rows=[]
    for row in campaign['sessions']:
        path=ROOT/row['receipt']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
        record=json.loads(path.read_text())
        assert record['source_sha256']==campaign['source_sha256']
        assert record['upstream']=='http://127.0.0.1:8090/v1'
        assert record['accepted']==row['accepted']
        native=record.get('native_gateway_audits',[])
        bounds=bool(native) and all(a['native_input_tokens']+a['output_reserve']+a['decoder_headroom']<=a['context_window'] for a in native)
        turns=record['turns']
        strict_long=len(turns)>=9 and record['active_client_seconds']>180 and bool(record.get('session_id'))
        if record['accepted']:
            assert strict_long and bounds and all(t['accepted'] and t['hidden_tests_exit']==0 and t['historical_gold_passed'] for t in turns)
        probe=probe_map.get(row['receipt'])
        rows.append({**row,'nine_turn_long_session':strict_long,'native_budget_checks':len(native),
            'native_bounds_passed':bounds,'additional_contract_passed':probe['all_additional_checks_passed'] if probe else None})
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
    report={'captured_at':datetime.now(timezone.utc).isoformat(),'controller_state':campaign['state'],
        'planned_attempts':campaign['planned_sessions'],'terminal_attempts':len(rows),
        'harness_accepted':sum(r['accepted'] for r in rows),
        'nine_turn_long_sessions':sum(r['nine_turn_long_session'] for r in rows),
        'failed_attempts':sum(not r['accepted'] for r in rows),
        'native_budget_checks':sum(r['native_budget_checks'] for r in rows),
        'groups':groups,'sessions':rows,'all_retained_terminal_receipts':all_receipts,
        'historical_accepted_nine_turn_samples_with_same_sift':[
            row for row in all_receipts if not row['source_matches_current'] and row['sift_candidate_matches_current']
            and row['accepted'] and row['turns']>=9 and row['active_seconds']>180
            and row['upstream']=='http://127.0.0.1:8090/v1' and row['published_raw_evidence_verified']],
        'independent_final_acceptance':'pending',
        'limits':[
            'Three synthetic task families use real native CLIs, persisted sessions, local Qwen and filesystem edits; this is not a production repository trial.',
            'Harness acceptance and selected posthoc contract probes are separate. Extra edge cases are not exhaustive or preregistered; no universal quality percentage follows.',
            'Historical and setup receipts remain listed separately and are excluded from the current matrix denominator.',
            'Active seconds measure client execution without idle padding. They are not decode tokens/second.',
            'No paired no-Sift ablation establishes whether compaction caused any task defect.',
        ]}
    (ROOT/'evidence/stress-summary.json').write_text(json.dumps(report,indent=2))
    lines=['# Local CLI stress results','',f"Checkpoint: {report['captured_at']}. Controller: **{campaign['state']}**. Final independent acceptance: **pending**.",'',
        f"{report['harness_accepted']} harness passes and {report['failed_attempts']} failed attempts among {len(rows)} terminal matrix attempts; {report['nine_turn_long_sessions']} reached nine turns and over 180 active seconds. There are {campaign['planned_sessions']} planned attempts. Two short failures mean this plan can yield at most 20 corrected-epoch nine-turn sessions; the target of 21 remains unmet.",'',
        '| Client | Terminal attempts | Harness passes | Nine-turn long sessions | Median accepted active seconds | Added contract failures |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for group in groups:
        value=group['accepted_active_seconds'].get('median')
        timing=f'{value:.3f}' if value is not None else 'n/a'
        lines.append(f"| {group['client']} | {group['terminal_attempts']} | {group['harness_accepted']} | {group['nine_turn_long_sessions']} | {timing} | {group['additional_contract_failures']} |")
    lines+=['','The retained OpenCode expense timeout remains a failed one-turn attempt. The fixed extra sample uses repeat2/seed2951; no outcome-based re-roll or timeout extension is allowed.','',
        'The nine-turn harness checks native tool workflows, hidden tests, historical-fact retention and session continuity. Selected additional contract probes expose narrower validation defects in generated artifacts despite workflow passes. See [per-artifact probes](../evidence/stress-contract-probes.json) and [complete outcome summary](../evidence/stress-summary.json).','']
    lines.extend('- '+limit for limit in report['limits'])
    (ROOT/'docs/STRESS_RESULTS.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({key:report[key] for key in ('controller_state','terminal_attempts','harness_accepted','nine_turn_long_sessions','failed_attempts','native_budget_checks')}))


if __name__=='__main__':main()
