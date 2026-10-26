import asyncio
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from fastapi import HTTPException

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from gateway import LocalSift


class GatewayAdmissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_responses_bridge_is_pinned_and_does_not_hold_inner_slot(self):
        hook=LocalSift()
        data={'model':'qwen3.8-27b-codex','input':'test'}
        with patch.dict(os.environ,{'LITELLM_MASTER_KEY':'test-only'}):
            result=await hook.async_pre_call_hook(None,None,data,'aresponses')
        self.assertTrue(result['use_chat_completions_api'])
        self.assertEqual(result['api_base'],'http://127.0.0.1:8090/v1')
        self.assertTrue(hook.slot.acquire(False))
        hook.slot.release()
        for changes in ({'model':'qwen3.8-27b'},{'previous_response_id':'hidden'},
                        {'use_chat_completions_api':False},{'max_output_tokens':8192}):
            with self.subTest(changes=changes),self.assertRaises(HTTPException):
                await hook.async_pre_call_hook(None,None,dict(data,**changes),'aresponses')

    async def test_short_admission_wait_keeps_single_worker(self):
        hook=LocalSift(wait_seconds=.5)
        hook.slot.acquire()
        asyncio.get_running_loop().call_later(.08,hook.slot.release)
        payload={'model':'qwen3.8-27b','messages':[{'role':'user','content':'x'}]}
        with patch('gateway.compact',return_value=(dict(payload,max_tokens=128),{'compaction_input_sha256':'test'})),patch.dict(os.environ,{'SIFT_AUDIT_PATH':os.devnull}):
            result=await hook.async_pre_call_hook(None,None,payload,'acompletion')
        self.assertEqual(result['max_tokens'],128)
        self.assertTrue(hook.slot.acquire(False))
        hook.slot.release()

    async def test_exhausted_wait_fails_closed(self):
        hook=LocalSift(wait_seconds=0)
        hook.slot.acquire()
        with self.assertRaises(HTTPException) as error:
            await hook.async_pre_call_hook(None,None,{},'acompletion')
        self.assertEqual(error.exception.status_code,429)
        hook.slot.release()
