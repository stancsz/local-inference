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

if __name__=='__main__': unittest.main()
