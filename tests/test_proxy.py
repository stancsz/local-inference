import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import budget as proxy
from sift import CompactionError

class ProxyBudgetTests(unittest.TestCase):
    def payload(self):
        return {'model':'caller-alias','system':'Keep exact instructions.','messages':[{'role':'user','content':'Inspect the current deployment.'}],'max_tokens':4096}

    def test_preserves_current_work_and_reserves_output(self):
        original=self.payload()
        with patch.object(proxy,'count',return_value=80):
            forwarded,audit=proxy.compact(original)
        self.assertEqual(forwarded['messages'],original['messages'])
        self.assertEqual(forwarded['system'],original['system'])
        self.assertEqual(forwarded['max_tokens'],4096)
        self.assertEqual(original['model'],'caller-alias')
        self.assertEqual(audit['native_input_tokens'],80)

    def test_rejects_native_template_overflow_after_selection(self):
        with patch.object(proxy,'count',side_effect=[80,proxy.WINDOW]):
            with self.assertRaises(CompactionError): proxy.compact(self.payload())

    def test_reserves_speculative_decoder_headroom(self):
        # Fits input+output, but leaves only 128 tokens for a 256-token guard.
        with patch.object(proxy,'count',side_effect=[80,proxy.WINDOW-4096-128]):
            with self.assertRaises(CompactionError): proxy.compact(self.payload())

    def test_schema_overhead_can_exhaust_minimum_budget(self):
        with patch.object(proxy,'count',return_value=proxy.WINDOW):
            with self.assertRaises(CompactionError): proxy.compact(self.payload())

    def test_oversized_immutable_current_task_fails_closed(self):
        payload=self.payload()
        payload['messages'][0]['content']='current-task '*12000
        with patch.object(proxy,'count',side_effect=lambda p,protocol:len(json.dumps(p))//2):
            with self.assertRaises(CompactionError): proxy.compact(payload)

    def test_cap_output_and_keep_tool_definitions(self):
        payload=self.payload()
        payload['tools']=[{'name':'Read','description':'Read a file','input_schema':{'type':'object'}}]
        with patch.object(proxy,'count',return_value=80):
            forwarded,audit=proxy.compact(payload)
        self.assertEqual(forwarded['max_tokens'],4096)
        self.assertEqual(forwarded['tools'],payload['tools'])

    def test_rejects_invalid_output_budget(self):
        for value in (0,-1,True,'4096',64000):
            payload=self.payload()
            payload['max_tokens']=value
            with self.subTest(value=value), self.assertRaises((ValueError,TypeError)):
                proxy.compact(payload)

    def test_openai_completion_budget_is_normalized(self):
        payload=self.payload()
        payload.pop('max_tokens')
        payload.pop('system')
        payload['max_completion_tokens']=128
        with patch.object(proxy,'count',return_value=80):
            forwarded,_=proxy.compact(payload,'openai')
        self.assertEqual(forwarded['max_tokens'],128)
        self.assertNotIn('max_completion_tokens',forwarded)

    def test_audit_identity_separates_tool_choice_and_schema(self):
        original=self.payload()
        other=dict(original,tool_choice={'type':'tool','name':'Read'})
        self.assertNotEqual(proxy.compaction_digest(original),proxy.compaction_digest(other))
        other=dict(original,response_format={'type':'json_object'})
        self.assertNotEqual(proxy.compaction_digest(original),proxy.compaction_digest(other))

    def test_audit_identity_separates_output_limit_aliases(self):
        original=self.payload()
        original.pop('max_tokens')
        self.assertNotEqual(proxy.compaction_digest(dict(original,max_completion_tokens=128)),proxy.compaction_digest(dict(original,max_completion_tokens=256)))

    def test_openai_top_level_system_is_rejected(self):
        with self.assertRaises(ValueError): proxy.compact(self.payload(),'openai')

    def test_adaptive_budgets_and_downstream_limits_in_both_protocols(self):
        def native(payload, protocol):
            return (len(json.dumps(payload)) + 3)//4
        for protocol in ('anthropic','openai'):
            targets=[]
            for repeats in (1000,4000):
                payload=self.payload()
                payload['tools']=[{'name':'Read','description':'read facts','input_schema':{'type':'object'}}]
                history=[]
                for index in range(20):
                    history.extend([{'role':'user','content':f'Record {index}: '+'Historical fact. '*repeats},
                                    {'role':'assistant','content':'Recorded.'}])
                payload['messages']=history+payload['messages']
                if protocol=='openai':
                    payload['messages'].insert(0,{'role':'system','content':payload.pop('system')})
                with patch.object(proxy,'count',side_effect=native):
                    forwarded,audit=proxy.compact(payload,protocol)
                self.assertEqual(forwarded['messages'][-1],payload['messages'][-1])
                self.assertEqual(forwarded['tools'],payload['tools'])
                self.assertLessEqual(audit['native_input_tokens'],audit['target_tokens'])
                self.assertLessEqual(audit['native_input_tokens']+forwarded['max_tokens']+256,proxy.WINDOW)
                if protocol=='anthropic': self.assertEqual(forwarded['system'],payload['system'])
                else: self.assertEqual(forwarded['messages'][0],payload['messages'][0])
                targets.append(audit['target_tokens'])
            self.assertEqual(targets,[24576,proxy.WINDOW-4096-256])

if __name__=='__main__': unittest.main()
