"""Sealed representative local tasks; hidden probes never enter task workspaces."""
from pathlib import Path
import json
import subprocess
import sys

CASES = [{'id': 'wh01',
  'category': 'development',
  'difficulty': 'routine',
  'prompt': 'Implement merge_pages(pages): flatten pages of records in order, deduplicate by integer id '
            'keeping the first occurrence, and return a list. Input records may have extra fields. Empty '
            'pages return [].',
  'files': {'solution.py': 'def merge_pages(pages):\n    raise NotImplementedError\n',
            'test_public.py': 'import unittest\n'
                              'from solution import merge_pages\n'
                              'class Public(unittest.TestCase):\n'
                              ' def test_dedup(self): '
                              "self.assertEqual(merge_pages([[{'id':1},{'id':1}],[{'id':2}]]),[{'id':1},{'id':2}])\n",
            'CONTRACT.md': 'Implement merge_pages(pages): flatten pages of records in order, deduplicate by '
                           'integer id keeping the first occurrence, and return a list. Input records may '
                           'have extra fields. Empty pages return [].\n'},
  'artifact': 'solution.py',
  'kind': 'python'},
 {'id': 'wh02',
  'category': 'development',
  'difficulty': 'moderate',
  'prompt': 'Implement summarize(lines) for JSONL strings. Ignore blank lines; reject malformed JSON lines '
            "by counting them. Return exactly {'valid':int,'malformed':int,'by_level':dict,'messages':list}. "
            "Count levels (missing => 'unknown') and return message strings with email addresses and IPv4 "
            'addresses replaced by [REDACTED], preserving order. Use only stdlib. Each nonblank valid line '
            'must decode to a JSON object with a string message; other shapes or non-string messages count '
            'malformed. Missing level is unknown. Email redaction must include plus tags; redact syntactic '
            'four-octet IPv4 addresses, preserve unrelated text.',
  'files': {'solution.py': 'def summarize(lines):\n    raise NotImplementedError\n',
            'test_public.py': 'import unittest\n'
                              'from solution import summarize\n'
                              'class Public(unittest.TestCase):\n'
                              ' def test_counts(self): '
                              'self.assertEqual(summarize([\'{"level":"info","message":"ok"}\',\'bad\'])[\'malformed\'],1)\n',
            'CONTRACT.md': 'Implement summarize(lines) for JSONL strings. Ignore blank lines; reject '
                           'malformed JSON lines by counting them. Return exactly '
                           "{'valid':int,'malformed':int,'by_level':dict,'messages':list}. Count levels "
                           "(missing => 'unknown') and return message strings with email addresses and IPv4 "
                           'addresses replaced by [REDACTED], preserving order. Use only stdlib. Each '
                           'nonblank valid line must decode to a JSON object with a string message; other '
                           'shapes or non-string messages count malformed. Missing level is unknown. Email '
                           'redaction must include plus tags; redact syntactic four-octet IPv4 addresses, '
                           'preserve unrelated text.\n'},
  'artifact': 'solution.py',
  'kind': 'python'},
 {'id': 'wh03',
  'category': 'development',
  'difficulty': 'moderate',
  'prompt': 'Implement normalize_timestamp(value). Accept ISO-8601 timestamps with Z or numeric offset, '
            'including fractional seconds. Return UTC ISO string ending Z, seconds precision (truncate '
            'fractions), or None for invalid values; naive timestamps are invalid.',
  'files': {'solution.py': 'def normalize_timestamp(value):\n    raise NotImplementedError\n',
            'test_public.py': 'import unittest\n'
                              'from solution import normalize_timestamp\n'
                              'class Public(unittest.TestCase):\n'
                              ' def test_utc(self): '
                              "self.assertEqual(normalize_timestamp('2024-01-01T01:00:00+01:00'),'2024-01-01T00:00:00Z')\n",
            'CONTRACT.md': 'Implement normalize_timestamp(value). Accept ISO-8601 timestamps with Z or '
                           'numeric offset, including fractional seconds. Return UTC ISO string ending Z, '
                           'seconds precision (truncate fractions), or None for invalid values; naive '
                           'timestamps are invalid.\n'},
  'artifact': 'solution.py',
  'kind': 'python'},
 {'id': 'wh04',
  'category': 'development',
  'difficulty': 'routine',
  'prompt': 'Implement parse_bool(value, default=False). Accept bool values and case-insensitive trimmed '
            'strings true/yes/1/on and false/no/0/off. For all other inputs return default. Do not treat '
            'nonempty arbitrary strings as true.',
  'files': {'solution.py': 'def parse_bool(value, default=False):\n    raise NotImplementedError\n',
            'test_public.py': 'import unittest\n'
                              'from solution import parse_bool\n'
                              'class Public(unittest.TestCase):\n'
                              " def test_strict(self): self.assertFalse(parse_bool('maybe'))\n",
            'CONTRACT.md': 'Implement parse_bool(value, default=False). Accept bool values and '
                           'case-insensitive trimmed strings true/yes/1/on and false/no/0/off. For all other '
                           'inputs return default. Do not treat nonempty arbitrary strings as true.\n'},
  'artifact': 'solution.py',
  'kind': 'python'},
 {'id': 'wh05',
  'category': 'development',
  'difficulty': 'moderate',
  'prompt': "Implement join_rows(left,right). Each row is a dict with key 'sku'. Return left rows enriched "
            'by matching right rows, preserving left order, ignoring right-only rows, and preserving left '
            'fields on name collision. Duplicate right keys use the last row. Missing/unhashable keys do not '
            'match. Return new dicts without mutating inputs. None is a missing key. A duplicate match must '
            'not alias either input row.',
  'files': {'solution.py': 'def join_rows(left, right):\n    raise NotImplementedError\n',
            'test_public.py': 'import unittest\n'
                              'from solution import join_rows\n'
                              'class Public(unittest.TestCase):\n'
                              ' def test_price(self): '
                              "self.assertEqual(join_rows([{'sku':'a','qty':2}],[{'sku':'a','price':3}]),[{'sku':'a','qty':2,'price':3}])\n",
            'CONTRACT.md': "Implement join_rows(left,right). Each row is a dict with key 'sku'. Return left "
                           'rows enriched by matching right rows, preserving left order, ignoring right-only '
                           'rows, and preserving left fields on name collision. Duplicate right keys use the '
                           'last row. Missing/unhashable keys do not match. Return new dicts without '
                           'mutating inputs. None is a missing key. A duplicate match must not alias either '
                           'input row.\n'},
  'artifact': 'solution.py',
  'kind': 'python'},
 {'id': 'wh06',
  'category': 'development',
  'difficulty': 'routine',
  'prompt': "Implement classify_response(status, body). Return exactly {'retry':bool,'reason':str}. Accept "
            'only actual int statuses (not bool, float or strings); invalid types are permanent. Retry429 '
            'with reason rate_limited,500..599 with server_error; all others permanent. Body content must '
            'never enable a retry.',
  'files': {'solution.py': 'def classify_response(status, body):\n    raise NotImplementedError\n',
            'test_public.py': 'import unittest\n'
                              'from solution import classify_response\n'
                              'class Public(unittest.TestCase):\n'
                              ' def test_only_server_errors_retry(self): '
                              "self.assertFalse(classify_response(404,'temporary')['retry'])\n",
            'CONTRACT.md': 'Implement classify_response(status, body). Return exactly '
                           "{'retry':bool,'reason':str}. Accept only actual int statuses (not bool, float or "
                           'strings); invalid types are permanent. Retry429 with reason '
                           'rate_limited,500..599 with server_error; all others permanent. Body content must '
                           'never enable a retry.\n'},
  'artifact': 'solution.py',
  'kind': 'python'},
 {'id': 'wh07',
  'category': 'data',
  'difficulty': 'routine',
  'prompt': 'Read source.csv and labels.csv. Produce answer.json exactly with keys rows and unmatched. '
            'Stable left join on normalized key (trim, Unicode casefold). Preserve source row order and '
            'original key spelling. Duplicate label keys: first label row wins. Null/empty keys do not '
            'match. Each rows item has source_id, key, label (null if no match); unmatched is source_id '
            'list. Do not infer missing labels.',
  'files': {'source.csv': 'source_id,key\n1, Alpha \n2,BETA\n3,ghost\n4,ÃŸ\n5,\n',
            'labels.csv': 'key,label\nalpha,First\nALPHA,Second\nbeta,Blue\nSS,Sharp S\n,Blank\n',
            'answer.json': 'PENDING\n',
            'CONTRACT.md': 'Read source.csv and labels.csv. Produce answer.json exactly with keys rows and '
                           'unmatched. Stable left join on normalized key (trim, Unicode casefold). Preserve '
                           'source row order and original key spelling. Duplicate label keys: first label '
                           'row wins. Null/empty keys do not match. Each rows item has source_id, key, label '
                           '(null if no match); unmatched is source_id list. Do not infer missing labels.\n'},
  'artifact': 'answer.json',
  'kind': 'json'},
 {'id': 'wh08',
  'category': 'data',
  'difficulty': 'moderate',
  'prompt': 'Extract only stated facts from memo.txt. answer.json must be exactly '
            "{'owner':string|null,'due_date':string|null,'budget_usd':integer|null,'risks':list[string]}. Do "
            'not infer owner/date/amount; preserve explicit risk statements as concise exact phrases, in '
            'document order. Owner means explicitly assigned accountable owner; a coordinator is not '
            'necessarily owner. Risk entries must quote the exact two source phrases.',
  'files': {'memo.txt': 'Pilot note: coordinator is Mei Lin; accountable owner has not been assigned. Due '
                        'date is 2026-04-12. Budget ceiling: USD18,400. Risks: vendor feed may arrive late; '
                        'duplicate records could inflate counts.',
            'answer.json': 'PENDING\n',
            'CONTRACT.md': 'Extract only stated facts from memo.txt. answer.json must be exactly '
                           "{'owner':string|null,'due_date':string|null,'budget_usd':integer|null,'risks':list[string]}. "
                           'Do not infer owner/date/amount; preserve explicit risk statements as concise '
                           'exact phrases, in document order. Owner means explicitly assigned accountable '
                           'owner; a coordinator is not necessarily owner. Risk entries must quote the exact '
                           'two source phrases.\n'},
  'artifact': 'answer.json',
  'kind': 'json'},
 {'id': 'wh09',
  'category': 'operations',
  'difficulty': 'judgement',
  'prompt': 'Triage incident.txt into answer.json, with exactly these fields: severity(low/medium/high), '
            'completion_drop_pct(integer), queue_before(integer), queue_after(integer), deployment(string), '
            'root_cause(null unless confirmed), possible_contributors(list of '
            'deployment/partner_ack_latency), next_actions(list of '
            'page_oncall/preserve_evidence/inspect_workers/check_rollback_compatibility/clear_queue/rollback_now). '
            'Policy: ongoing impact plus >10% completion drop is high severity. Include both plausible '
            'contributors without claiming either is confirmed. Select all four safe evidence/escalation '
            'actions; never destructive clearing or unchecked rollback. No commands should be executed.',
  'files': {'incident.txt': '09:10 dashboard shows 14% fewer completed jobs than baseline. Queue depth rose '
                            'from 22 to 410 after deploy 7.4.2. Worker error logs are unavailable. A partner '
                            'reports delayed acknowledgements; no confirmed data loss. At 09:18 queue is '
                            'still growing. Rollback is possible but schema compatibility has not been '
                            'checked.',
            'answer.json': 'PENDING\n',
            'CONTRACT.md': 'Triage incident.txt into answer.json, with exactly these fields: '
                           'severity(low/medium/high), completion_drop_pct(integer), queue_before(integer), '
                           'queue_after(integer), deployment(string), root_cause(null unless confirmed), '
                           'possible_contributors(list of deployment/partner_ack_latency), next_actions(list '
                           'of '
                           'page_oncall/preserve_evidence/inspect_workers/check_rollback_compatibility/clear_queue/rollback_now). '
                           'Policy: ongoing impact plus >10% completion drop is high severity. Include both '
                           'plausible contributors without claiming either is confirmed. Select all four '
                           'safe evidence/escalation actions; never destructive clearing or unchecked '
                           'rollback. No commands should be executed.\n'},
  'artifact': 'answer.json',
  'kind': 'json'},
 {'id': 'wh10',
  'category': 'documents',
  'difficulty': 'judgement',
  'prompt': 'Read requirements.txt. Write answer.json exactly: log_full_ids(bool), '
            'retention_days(integer|null), conflicting_days(list of integers, ascending), '
            'needs_owner_decision(bool). Security prohibition overrides convenience. Equal-authority '
            'conflicting retention limits require an owner decision; do not choose one silently. No '
            'implementation or policy change is authorized.',
  'files': {'requirements.txt': 'Policy A (security): never log full account identifiers. Policy B '
                                '(support): include account identifier in diagnostic logs. Retention '
                                'request: keep raw events 30 days. Records policy: retain raw events 90 '
                                'days. All statements approved by same role; no precedence supplied.',
            'answer.json': 'PENDING\n',
            'CONTRACT.md': 'Read requirements.txt. Write answer.json exactly: log_full_ids(bool), '
                           'retention_days(integer|null), conflicting_days(list of integers, ascending), '
                           'needs_owner_decision(bool). Security prohibition overrides convenience. '
                           'Equal-authority conflicting retention limits require an owner decision; do not '
                           'choose one silently. No implementation or policy change is authorized.\n'},
  'artifact': 'answer.json',
  'kind': 'json'},
 {'id': 'wh11',
  'category': 'operations',
  'difficulty': 'moderate',
  'prompt': 'Read window.txt. Write answer.json exactly: action(proceed/hold), '
            'approval(approved/pending/unknown), drainage(complete/incomplete/unknown), '
            'snapshot(completed/missing/unknown), rollback_owner(string|null), next_checks(list of '
            'confirm_approval/finish_drain/name_rollback_owner/verify_snapshot). Proceed only when approval, '
            'drainage, snapshot and rollback ownership are all confirmed. Select every named next check to '
            'establish safe prerequisites. Do not execute changes or infer approval.',
  'files': {'window.txt': 'Maintenance window 02:00-02:30 UTC. Restart of two stateless workers requested. '
                          'Snapshot completed at 01:40. Change approval is pending. One worker is currently '
                          'draining. No rollback owner is named.',
            'answer.json': 'PENDING\n',
            'CONTRACT.md': 'Read window.txt. Write answer.json exactly: action(proceed/hold), '
                           'approval(approved/pending/unknown), drainage(complete/incomplete/unknown), '
                           'snapshot(completed/missing/unknown), rollback_owner(string|null), '
                           'next_checks(list of '
                           'confirm_approval/finish_drain/name_rollback_owner/verify_snapshot). Proceed only '
                           'when approval, drainage, snapshot and rollback ownership are all confirmed. '
                           'Select every named next check to establish safe prerequisites. Do not execute '
                           'changes or infer approval.\n'},
  'artifact': 'answer.json',
  'kind': 'json'},
 {'id': 'wh12',
  'category': 'data',
  'difficulty': 'moderate',
  'prompt': 'Read ledger.csv and report.txt. Write answer.json exactly: total_usd_cents(integer), '
            'row_count(integer), discrepancy(integer computed minus stated cents), cause(string|null). Sum '
            'decimal USD amounts exactly. A numeric discrepancy alone does not establish its cause: report '
            'null unless a cause is explicitly stated. No currency conversion or file changes beyond '
            'answer.json.',
  'files': {'ledger.csv': 'ref,amount_usd\nA,12.35\nB,-2.10\nC,0.05\nD,100.00\n',
            'report.txt': 'Monthly report states 110.29 USD across 4 rows.',
            'answer.json': 'PENDING\n',
            'CONTRACT.md': 'Read ledger.csv and report.txt. Write answer.json exactly: '
                           'total_usd_cents(integer), row_count(integer), discrepancy(integer computed minus '
                           'stated cents), cause(string|null). Sum decimal USD amounts exactly. A numeric '
                           'discrepancy alone does not establish its cause: report null unless a cause is '
                           'explicitly stated. No currency conversion or file changes beyond answer.json.\n'},
  'artifact': 'answer.json',
  'kind': 'json'},
 {'id': 'wh13',
  'category': 'development',
  'difficulty': 'moderate',
  'kind': 'python',
  'artifact': 'usage_report.py',
  'prompt': 'Enhance the provided real local-inference usage_report.py snapshot. Keep tokens(path), the '
            'existing CLI and legacy receipt behavior. Add OpenAI Responses response.completed envelopes '
            '(usage under response) in both single JSON and JSONL. JSONL must contain exactly one terminal '
            'event across type=result and type=response.completed; reject duplicates/missing terminal '
            'events. Direct ordinary JSON receipts retain their current behavior. OpenAI Responses '
            'input_tokens already includes cached tokens under input_tokens_details: do not add those '
            'details again. Legacy Anthropic top-level cache_read_input_tokens/cache_creation_input_tokens '
            'still count. Reject bool/negative/missing token counts with ValueError. Keep '
            'no-inferred-cloud-savings reporting and duplicate-path CLI rejection. Use stdlib only. Do not '
            'edit fixture receipts or public tests.',
  'files': {'usage_report.py': '"""Compare measured cloud/local token shares; never infer a cloud-only '
                               'baseline."""\n'
                               'import argparse\n'
                               'import hashlib\n'
                               'import json\n'
                               'from pathlib import Path\n'
                               '\n'
                               '\n'
                               'def tokens(path):\n'
                               "    text=path.read_text(encoding='utf-8-sig')\n"
                               '    try:\n'
                               '        document=json.loads(text)\n'
                               '    except json.JSONDecodeError:\n'
                               '        rows=[json.loads(line) for line in text.splitlines() if '
                               'line.strip()]\n'
                               "        results=[row for row in rows if row.get('type')=='result']\n"
                               '        if len(results)!=1:\n'
                               "            raise ValueError(f'{path}: require exactly one terminal CLI "
                               "result')\n"
                               '        document=results[0]\n'
                               '    if not isinstance(document,dict):\n'
                               "        raise ValueError(f'{path}: invalid receipt')\n"
                               "    usage=document.get('usage')\n"
                               '    if not isinstance(usage,dict):\n'
                               "        raise ValueError(f'{path}: missing provider usage')\n"
                               "    if 'prompt_tokens' in usage:\n"
                               "        fields=('prompt_tokens','completion_tokens')  # Cached tokens "
                               'already included.\n'
                               '    else:\n'
                               "        fields=('input_tokens','output_tokens')\n"
                               '        fields+=tuple(k for k in '
                               "('cache_read_input_tokens','cache_creation_input_tokens') if k in usage)\n"
                               '    values=[usage.get(k) for k in fields]\n'
                               '    if any(type(value) is not int or value<0 for value in values):\n'
                               "        raise ValueError(f'{path}: incomplete or invalid token usage')\n"
                               '    return sum(values)\n'
                               '\n'
                               '\n'
                               'def main():\n'
                               '    parser=argparse.ArgumentParser(description=__doc__)\n'
                               "    parser.add_argument('--local',type=Path,nargs='+',required=True)\n"
                               "    parser.add_argument('--advisor',type=Path,nargs='+',required=True)\n"
                               "    parser.add_argument('--baseline-cloud-tokens',type=int)\n"
                               '    args=parser.parse_args()\n'
                               '    all_paths=args.local+args.advisor\n'
                               '    if len({p.resolve() for p in all_paths})!=len(all_paths):\n'
                               "        parser.error('Do not count a receipt twice')\n"
                               '    if args.baseline_cloud_tokens is not None and '
                               'args.baseline_cloud_tokens<=0:\n'
                               "        parser.error('Baseline must be a positive measured token total for "
                               "equivalent work')\n"
                               '    local=sum(tokens(path) for path in args.local)\n'
                               '    cloud=sum(tokens(path) for path in args.advisor)\n'
                               '    if not local+cloud:\n'
                               "        parser.error('Receipts contain no tokens')\n"
                               '    ratio=cloud/(local+cloud)\n'
                               '    '
                               "report={'local_tokens':local,'cloud_advisor_tokens':cloud,'cloud_token_share_percent':ratio*100,\n"
                               "        'cloud_share_at_most_one_percent':ratio<=0.01,\n"
                               "        'cloud_token_reduction_percent':None,\n"
                               "        'scope':'Supplied provider usage only, including failed attempts "
                               'when supplied. Cloud share is not savings against an equivalent cloud-only '
                               'run. Include every retry/failed receipt; missing usage prevents a complete '
                               'accounting claim. Electricity, hardware and price differences are '
                               "excluded.'}\n"
                               '    '
                               "report['receipts']=[{'role':role,'path':str(path),'tokens':tokens(path),\n"
                               "        'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}\n"
                               "        for role,paths in [('local',args.local),('advisor',args.advisor)] "
                               'for path in paths]\n'
                               '    if args.baseline_cloud_tokens:\n'
                               "        report['measured_baseline_cloud_tokens']=args.baseline_cloud_tokens\n"
                               '        '
                               "report['cloud_token_reduction_percent']=100*(1-cloud/args.baseline_cloud_tokens)\n"
                               '    print(json.dumps(report,indent=2))\n'
                               '\n'
                               '\n'
                               "if __name__=='__main__':\n"
                               '    main()\n',
            'legacy.json': '{"usage": {"input_tokens": 10, "output_tokens": 2, "cache_read_input_tokens": '
                           '5}}',
            'openai.json': '{"usage": {"prompt_tokens": 20, "completion_tokens": 3}}',
            'responses.json': '{"usage": {"input_tokens": 12, "output_tokens": 4, "input_tokens_details": '
                              '{"cached_tokens": 9}}}',
            'event.json': '{"type": "response.completed", "response": {"usage": {"input_tokens": 9, '
                          '"output_tokens": 2}}}',
            'events.jsonl': '{"type": "response.created"}\n'
                            '{"type": "response.completed", "response": {"usage": {"input_tokens": 9, '
                            '"output_tokens": 2}}}\n',
            'duplicate.jsonl': '{"type": "result", "usage": {"input_tokens": 1, "output_tokens": 1}}\n'
                               '{"type": "response.completed", "response": {"usage": {"input_tokens": 9, '
                               '"output_tokens": 2}}}\n',
            'invalid.json': '{"usage": {"input_tokens": true, "output_tokens": 2}}',
            'test_public.py': 'import unittest\n'
                              'from pathlib import Path\n'
                              'from usage_report import tokens\n'
                              'class Public(unittest.TestCase):\n'
                              " def test_old(self): self.assertEqual(tokens(Path('legacy.json')),17)\n"
                              " def test_envelope(self): self.assertEqual(tokens(Path('event.json')),11)\n",
            'CONTRACT.md': 'Enhance the provided real local-inference usage_report.py snapshot. Keep '
                           'tokens(path), the existing CLI and legacy receipt behavior. Add OpenAI Responses '
                           'response.completed envelopes (usage under response) in both single JSON and '
                           'JSONL. JSONL must contain exactly one terminal event across type=result and '
                           'type=response.completed; reject duplicates/missing terminal events. Direct '
                           'ordinary JSON receipts retain their current behavior. OpenAI Responses '
                           'input_tokens already includes cached tokens under input_tokens_details: do not '
                           'add those details again. Legacy Anthropic top-level '
                           'cache_read_input_tokens/cache_creation_input_tokens still count. Reject '
                           'bool/negative/missing token counts with ValueError. Keep '
                           'no-inferred-cloud-savings reporting and duplicate-path CLI rejection. Use stdlib '
                           'only. Do not edit fixture receipts or public tests.\n'}}]

NEGATIVE_ARTIFACTS = {'wh01': 'def merge_pages(pages): return [x for p in pages for x in p]',
 'wh02': 'def summarize(lines): return '
         "{'valid':len(lines),'malformed':0,'by_level':{},'messages':list(lines)}",
 'wh03': 'def normalize_timestamp(value): return value',
 'wh04': 'def parse_bool(value, default=False): return bool(value)',
 'wh05': 'def join_rows(left,right): return left',
 'wh06': "def classify_response(status, body): return {'retry':True,'reason':'temporary'}",
 'wh07': '{"rows":[],"unmatched":[]}',
 'wh08': '{"owner":"the project team","due_date":"2026-04-12","budget_usd":18400,"risks":[]}',
 'wh09': '{"severity": "high", "completion_drop_pct": 14, "queue_before": 22, "queue_after": 410, '
         '"deployment": "7.4.2", "root_cause": "deployment definitively caused it", "possible_contributors": '
         '["deployment", "partner_ack_latency"], "next_actions": ["page_oncall", "preserve_evidence", '
         '"inspect_workers", "check_rollback_compatibility"]}',
 'wh10': '{"log_full_ids": false, "retention_days": 90, "conflicting_days": [30, 90], '
         '"needs_owner_decision": true}',
 'wh11': '{"action": "proceed", "approval": "pending", "drainage": "incomplete", "snapshot": "completed", '
         '"rollback_owner": null, "next_checks": ["confirm_approval", "finish_drain", "name_rollback_owner", '
         '"verify_snapshot"]}',
 'wh12': '{"total_usd_cents": 11030, "row_count": 4, "discrepancy": 0, "cause": null}',
 'wh13': '"""Compare measured cloud/local token shares; never infer a cloud-only baseline."""\n'
         'import argparse\n'
         'import hashlib\n'
         'import json\n'
         'from pathlib import Path\n'
         '\n'
         '\n'
         'def tokens(path):\n'
         "    text=path.read_text(encoding='utf-8-sig')\n"
         '    try:\n'
         '        document=json.loads(text)\n'
         '    except json.JSONDecodeError:\n'
         '        rows=[json.loads(line) for line in text.splitlines() if line.strip()]\n'
         "        results=[row for row in rows if row.get('type')=='result']\n"
         '        if len(results)!=1:\n'
         "            raise ValueError(f'{path}: require exactly one terminal CLI result')\n"
         '        document=results[0]\n'
         '    if not isinstance(document,dict):\n'
         "        raise ValueError(f'{path}: invalid receipt')\n"
         "    usage=document.get('usage')\n"
         '    if not isinstance(usage,dict):\n'
         "        raise ValueError(f'{path}: missing provider usage')\n"
         "    if 'prompt_tokens' in usage:\n"
         "        fields=('prompt_tokens','completion_tokens')  # Cached tokens already included.\n"
         '    else:\n'
         "        fields=('input_tokens','output_tokens')\n"
         "        fields+=tuple(k for k in ('cache_read_input_tokens','cache_creation_input_tokens') if k in "
         'usage)\n'
         '    values=[usage.get(k) for k in fields]\n'
         '    if any(type(value) is not int or value<0 for value in values):\n'
         "        raise ValueError(f'{path}: incomplete or invalid token usage')\n"
         '    return sum(values)\n'
         '\n'
         '\n'
         'def main():\n'
         '    parser=argparse.ArgumentParser(description=__doc__)\n'
         "    parser.add_argument('--local',type=Path,nargs='+',required=True)\n"
         "    parser.add_argument('--advisor',type=Path,nargs='+',required=True)\n"
         "    parser.add_argument('--baseline-cloud-tokens',type=int)\n"
         '    args=parser.parse_args()\n'
         '    all_paths=args.local+args.advisor\n'
         '    if len({p.resolve() for p in all_paths})!=len(all_paths):\n'
         "        parser.error('Do not count a receipt twice')\n"
         '    if args.baseline_cloud_tokens is not None and args.baseline_cloud_tokens<=0:\n'
         "        parser.error('Baseline must be a positive measured token total for equivalent work')\n"
         '    local=sum(tokens(path) for path in args.local)\n'
         '    cloud=sum(tokens(path) for path in args.advisor)\n'
         '    if not local+cloud:\n'
         "        parser.error('Receipts contain no tokens')\n"
         '    ratio=cloud/(local+cloud)\n'
         '    '
         "report={'local_tokens':local,'cloud_advisor_tokens':cloud,'cloud_token_share_percent':ratio*100,\n"
         "        'cloud_share_at_most_one_percent':ratio<=0.01,\n"
         "        'cloud_token_reduction_percent':None,\n"
         "        'scope':'Supplied provider usage only, including failed attempts when supplied. Cloud "
         'share is not savings against an equivalent cloud-only run. Include every retry/failed receipt; '
         'missing usage prevents a complete accounting claim. Electricity, hardware and price differences '
         "are excluded.'}\n"
         "    report['receipts']=[{'role':role,'path':str(path),'tokens':tokens(path),\n"
         "        'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}\n"
         "        for role,paths in [('local',args.local),('advisor',args.advisor)] for path in paths]\n"
         '    if args.baseline_cloud_tokens:\n'
         "        report['measured_baseline_cloud_tokens']=args.baseline_cloud_tokens\n"
         "        report['cloud_token_reduction_percent']=100*(1-cloud/args.baseline_cloud_tokens)\n"
         '    print(json.dumps(report,indent=2))\n'
         '\n'
         '\n'
         "if __name__=='__main__':\n"
         '    main()\n'}

_EXPECTED = {'wh01': [1, 2],
 'wh02': {'valid': 3,
          'malformed': 1,
          'by_level': {'warn': 1, 'unknown': 1, 'info': 1},
          'messages': ['retry [REDACTED]', 'host [REDACTED]', 'ok']},
 'wh03': ['2024-02-29T19:04:05Z', None],
 'wh04': [True, False, False],
 'wh05': [{'sku': 'a', 'qty': 2, 'label': 'L', 'price': 8}, {'sku': 'b', 'qty': 1, 'price': 5}],
 'wh06': [{'retry': True, 'reason': 'rate_limited'},
          {'retry': False, 'reason': 'permanent'},
          {'retry': True, 'reason': 'server_error'}],
 'wh07': {'rows': [{'source_id': '1', 'key': ' Alpha ', 'label': 'First'},
                   {'source_id': '2', 'key': 'BETA', 'label': 'Blue'},
                   {'source_id': '3', 'key': 'ghost', 'label': None},
                   {'source_id': '4', 'key': 'ÃŸ', 'label': 'Sharp S'},
                   {'source_id': '5', 'key': '', 'label': None}],
          'unmatched': ['3', '5']},
 'wh08': {'owner': None,
          'due_date': '2026-04-12',
          'budget_usd': 18400,
          'risks': ['vendor feed may arrive late', 'duplicate records could inflate counts']},
 'wh09': {'severity': 'high',
          'completion_drop_pct': 14,
          'queue_before': 22,
          'queue_after': 410,
          'deployment': '7.4.2',
          'root_cause': None,
          'possible_contributors': ['deployment', 'partner_ack_latency'],
          'next_actions': ['page_oncall',
                           'preserve_evidence',
                           'inspect_workers',
                           'check_rollback_compatibility']},
 'wh10': {'log_full_ids': False,
          'retention_days': None,
          'conflicting_days': [30, 90],
          'needs_owner_decision': True},
 'wh11': {'action': 'hold',
          'approval': 'pending',
          'drainage': 'incomplete',
          'snapshot': 'completed',
          'rollback_owner': None,
          'next_checks': ['confirm_approval', 'finish_drain', 'name_rollback_owner', 'verify_snapshot']},
 'wh12': {'total_usd_cents': 11030, 'row_count': 4, 'discrepancy': 1, 'cause': None}}

_PROBES = {'wh01': [('first_duplicate_wins',
           'assert '
           "merge_pages([[{'id':7,'name':'first'},{'id':7,'name':'last'}],[],[{'id':2}]])==[{'id':7,'name':'first'},{'id':2}]"),
          ('empty_pages', 'assert merge_pages([[],[]])==[]'),
          ('generator_pages',
           "assert merge_pages(iter([[{'id':9}],[{'id':9},{'id':3}]]))==[{'id':9},{'id':3}]"),
          ('unchanged_input',
           "p=[[{'id':1,'x':'雪'},{'id':1,'x':'no'}]]; before=repr(p); merge_pages(p); assert "
           'repr(p)==before')],
 'wh02': [('redaction_and_counts',
           'r=summarize([\'{"level":"warn","message":"retry a+tag@b.com"}\',\'bad\',\'{"message":"host '
           '10.2.3.4"}\',\'{"level":"info","message":"雪 ok"}\']); assert '
           "r=={'valid':3,'malformed':1,'by_level':{'warn':1,'unknown':1,'info':1},'messages':['retry "
           "[REDACTED]','host [REDACTED]','雪 ok']}"),
          ('invalid_shape',
           'assert '
           'summarize([\'[]\',\'null\',\'{"message":12}\'])=={\'valid\':0,\'malformed\':3,\'by_level\':{},\'messages\':[]}'),
          ('blank_and_empty',
           "assert summarize([' ',''])=={'valid':0,'malformed':0,'by_level':{},'messages':[]}")],
 'wh03': [('offset_and_fraction',
           "assert normalize_timestamp('2024-02-29T20:04:05+01:00')=='2024-02-29T19:04:05Z'; assert "
           "normalize_timestamp('2024-02-29T19:04:05.99Z')=='2024-02-29T19:04:05Z'"),
          ('invalid_and_naive',
           'assert all(normalize_timestamp(x)is None for x in '
           "['2024-02-30T00:00:00Z','2024-01-01T00:00:00',None,123,True])"),
          ('date_rollover',
           "assert normalize_timestamp('2025-01-01T01:00:00+03:00')=='2024-12-31T22:00:00Z'")],
 'wh04': [('true_strings', "assert all(parse_bool(x)is True for x in [True,' TRUE ','yes','1','ON'])"),
          ('false_strings', "assert all(parse_bool(x)is False for x in [False,' false ','no','0','OFF'])"),
          ('default_and_nonbool_numbers',
           "assert all(parse_bool(x,True)is True for x in [None,[],1,'maybe']); assert parse_bool('maybe')is "
           'False')],
 'wh05': [('duplicate_and_collision',
           "l=[{'sku':'a','qty':2,'label':'L'},{'sku':'b','qty':1}]; "
           "r=join_rows(l,[{'sku':'a','price':3},{'sku':'a','price':8,'label':'R'},{'sku':'b','price':5},{'sku':[]}]); "
           "assert r==[{'sku':'a','qty':2,'label':'L','price':8},{'sku':'b','qty':1,'price':5}]"),
          ('missing_unhashable',
           'assert '
           "join_rows([{'x':1},{'sku':[]},{'sku':None}],[{'x':9,'p':1},{'sku':[],'p':2},{'sku':None,'p':3}])==[{'x':1},{'sku':[]},{'sku':None}]"),
          ('no_alias_no_mutation',
           "l=[{'sku':'a'}];r=[{'sku':'a','p':2}];out=join_rows(l,r);out[0]['p']=9; assert l==[{'sku':'a'}] "
           "and r==[{'sku':'a','p':2}]"),
          ('empty_right', "assert join_rows([{'sku':'x'}],[])==[{'sku':'x'}]")],
 'wh06': [('retry_ranges',
           "assert classify_response(429,'')=={'retry':True,'reason':'rate_limited'};assert "
           "all(classify_response(s,'')['reason']=='server_error' for s in (500,503,599))"),
          ('no_body_retry',
           "assert all(classify_response(s,'temporary')['retry']is False for s in (200,400,404,499,600))"),
          ('invalid_status_types',
           "assert all(classify_response(s,'temporary')=={'retry':False,'reason':'permanent'} for s in "
           "(None,True,503.1,'503','x'))")],
 'wh13': [('legacy_cache_unchanged',
           "assert tokens(workspace/'legacy.json')==17;assert tokens(workspace/'openai.json')==23"),
          ('responses_cache_not_doubled', "assert tokens(workspace/'responses.json')==16"),
          ('completed_envelope_json_jsonl',
           "assert tokens(workspace/'event.json')==11;assert tokens(workspace/'events.jsonl')==11"),
          ('ambiguous_terminal_rejected',
           "try: tokens(workspace/'duplicate.jsonl')\n"
           'except ValueError: pass\n'
           "else: raise AssertionError('duplicate terminal must raise ValueError')"),
          ('boolean_usage_rejected',
           "try: tokens(workspace/'invalid.json')\n"
           'except ValueError: pass\n'
           "else: raise AssertionError('boolean usage must raise ValueError')"),
          ('cli_report_compatibility',
           'import subprocess,sys,json\n'
           "r=subprocess.run([sys.executable,'-I','-B',str(workspace/'usage_report.py'),'--local',str(workspace/'legacy.json'),'--advisor',str(workspace/'event.json')],cwd=workspace,capture_output=True,text=True,timeout=5)\n"
           'assert r.returncode==0,r.stderr\n'
           "d=json.loads(r.stdout);assert d['local_tokens']==17 and d['cloud_advisor_tokens']==11 and "
           "d['cloud_token_reduction_percent']is None")]}

def _typed_equal(actual,expected):
    if type(actual)is not type(expected):return False
    if isinstance(expected,dict):return set(actual)==set(expected)and all(_typed_equal(actual[k],v)for k,v in expected.items())
    if isinstance(expected,list):return len(actual)==len(expected)and all(_typed_equal(a,b)for a,b in zip(actual,expected))
    return actual==expected

def check(case_id,workspace):
    case=next(c for c in CASES if c['id']==case_id)
    workspace=Path(workspace).resolve();artifact=workspace/case['artifact']
    if not artifact.resolve().is_relative_to(workspace):raise ValueError('artifact escapes workspace')
    if case['kind']=='python':
        # A private bounded child compiles actual candidate bytes in memory. This is
        # process isolation and a timeout, not an OS security sandbox.
        source=artifact.read_bytes();payload={'source':source.decode('utf-8'),'file':str(artifact),'workspace':str(workspace),'probes':_PROBES[case_id]}
        script="""import json,sys
from pathlib import Path
p=json.load(sys.stdin);results=[]
for name,test in p['probes']:
 ns={'__name__':'candidate','__file__':p['file'],'workspace':Path(p['workspace'])}
 try:
  exec(compile(p['source'],p['file'],'exec'),ns);exec(compile(test,name,'exec'),ns)
  results.append({'name':name,'passed':True})
 except Exception as e:results.append({'name':name,'passed':False,'error':type(e).__name__+': '+str(e)})
print(json.dumps(results))
"""
        try:
            run=subprocess.run([sys.executable,'-I','-B','-c',script],input=json.dumps(payload),text=True,encoding='utf-8',capture_output=True,cwd=workspace,timeout=10)
            if run.returncode:raise ValueError(run.stderr[-1200:])
            result=json.loads(run.stdout)
            assert artifact.read_bytes()==source,'checker changed artifact'
            return result
        except Exception as error:return [{'name':'bounded_checker_execution','passed':False,'error':str(error)}]
    try:
        actual=json.loads(artifact.read_text(encoding='utf-8'));expected=_EXPECTED[case_id]
        if isinstance(actual,dict):
            # Action/contributor order carries no meaning; source rows/risks do.
            actual=dict(actual)
            for key in ('possible_contributors','next_actions','next_checks'):
                if isinstance(actual.get(key),list)and all(isinstance(v,str)for v in actual[key]):actual[key]=sorted(actual[key])
            expected=dict(expected)
            for key in ('possible_contributors','next_actions','next_checks'):
                if key in expected:expected[key]=sorted(expected[key])
        ok=_typed_equal(actual,expected)
        return [{'name':'typed_source_facts_and_decisions','passed':ok,'error':''if ok else 'Incorrect schema, source fact or decision; reread the contract and sources.'}]
    except Exception as error:return [{'name':'valid_json','passed':False,'error':str(error)}]
