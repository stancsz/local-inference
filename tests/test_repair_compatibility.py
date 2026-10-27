"""Resource guards and permission metadata must survive local compaction."""
from copy import deepcopy
import json
from unittest.mock import patch
import pytest
from app import budget
from sift import CompactionError
from sift.litellm_proxy import compact_proxy_request


class Counter:
    def _count_pre_call_check_tokens(self, messages, input, request_kwargs):
        return (len(json.dumps(messages)) + len(json.dumps(request_kwargs.get('tools', [])))) // 4


def test_large_tool_schema_is_rejected_before_tokenizer_io():
    payload={'messages':[{'role':'user','content':'hello'}], 'tools':[{'description':'x'*500}], 'max_tokens':4096}
    with patch.object(budget, 'DEFAULT_MAX_INPUT_CHARACTERS', 256), patch.object(budget, 'count') as counter:
        with pytest.raises(CompactionError) as error: budget.compact(payload)
        assert error.value.code=='input_size_limit'
        counter.assert_not_called()


@pytest.mark.parametrize('raw', [32768,32769,34000,36608])
def test_fitting_protected_request_is_not_compressed_below_its_native_size(raw):
    payload={'messages':[{'role':'user','content':'Protected active task'}], 'max_tokens':4096}
    with patch.object(budget,'count',return_value=raw):
        forwarded,audit=budget.compact(payload)
    assert forwarded['messages']==payload['messages']
    assert audit['fitting_request_preserved']
    assert audit['target_tokens']>=raw
    assert audit['native_input_tokens']+4096+256<=40960


def test_request_exceeding_window_still_fails_closed():
    payload={'messages':[{'role':'user','content':'Protected active task'}], 'max_tokens':4096}
    with patch.object(budget,'count',return_value=36609):
        with pytest.raises(CompactionError):budget.compact(payload)


@pytest.mark.parametrize('client_policy', ['never','on-request','untrusted'])
def test_sift_keeps_permission_fields_and_instruction_catalog_exact(client_policy):
    policy={'approval_policy':client_policy,'sandbox_mode':'workspace-write','permissions':{'outside_workspace':'deny'}}
    catalog={'type':'additional_tools','role':'developer','tools':[{'type':'function','name':'safe_read',
        'parameters':{'type':'object','properties':{'path':{'type':'string'}}},'require_approval':'always'}]}
    instruction={'role':'developer','content':json.dumps(policy)}
    data={'model':'test','input':[instruction,catalog,
        {'role':'user','content':'Completed source archive. '*1800},
        {'role':'assistant','content':'Recorded.'}, {'role':'user','content':'Read only the allowed file.'}],
        'tools':[{'type':'function','name':'read','parameters':{'type':'object'},'require_approval':'always'}],
        'tool_choice':'auto','metadata':deepcopy(policy),'approval_policy':client_policy,'sandbox_mode':'workspace-write'}
    original=deepcopy(data)
    forwarded=compact_proxy_request(Counter(),data,call_type='aresponses',target=1600)
    assert data==original
    assert forwarded['approval_policy']==client_policy and forwarded['sandbox_mode']=='workspace-write'
    assert forwarded['tools']==original['tools'] and forwarded['tool_choice']==original['tool_choice']
    assert all(forwarded['metadata'][key]==value for key,value in policy.items())
    assert catalog in forwarded['input'] and instruction in forwarded['input']


def test_codex_bridge_does_not_mistake_tool_catalog_for_instruction_text():
    from app.gateway import protect_codex_instructions
    catalog={'type':'additional_tools','role':'developer','tools':[{'type':'function','name':'read','require_approval':'always'}]}
    data={'instructions':'Keep approval_policy=on-request and sandbox_mode=workspace-write.',
          'input':[deepcopy(catalog),{'role':'user','content':'Do the task.'}],
          'approval_policy':'on-request','sandbox_mode':'workspace-write'}
    original=deepcopy(data)
    protect_codex_instructions(data)
    assert data==original
