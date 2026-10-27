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


def test_compressible_history_still_gets_productive_ratio_budget_when_it_fits_window():
    payload={'messages':[{'role':'user','content':'completed record '*8200},
        {'role':'assistant','content':'recorded'},{'role':'user','content':'Continue the task.'}], 'max_tokens':4096}
    with patch.object(budget,'count',side_effect=lambda p,protocol:len(json.dumps(p))//4):
        _,audit=budget.compact(payload)
    assert 32768<audit['raw_native_tokens']<=36608
    assert audit['compacted'] and audit['target_tokens']==24576
    assert not audit['fitting_request_preserved']


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
    assert data['input']==original['input']
    assert data['approval_policy']==original['approval_policy']
    assert data['sandbox_mode']==original['sandbox_mode']
    assert data['instructions'].startswith(original['instructions'])
    assert json.loads(data['instructions'].split('host permissions still apply):\n',1)[1])==catalog
    once=deepcopy(data)
    protect_codex_instructions(data)
    assert data==once


def test_full_responses_converter_retains_catalog_approval_metadata_in_protected_path():
    from app.gateway import protect_codex_instructions
    from litellm.responses.litellm_completion_transformation.transformation import LiteLLMCompletionResponsesConfig as Converter
    catalog={'type':'additional_tools','role':'developer','tools':[{'type':'function','name':'Read','require_approval':'always','allowed_paths':['workspace']} ]}
    data={'model':'qwen3.8-27b-codex','instructions':'Keep approval_policy=on-request; sandbox_mode=workspace-write.',
          'input':[deepcopy(catalog),{'role':'user','content':'Read the approved file.'}]}
    protect_codex_instructions(data)
    converted=Converter.transform_responses_api_request_to_chat_completion_request(
        model='qwen3.8-27b',input=data['input'],responses_api_request={'instructions':data['instructions']},custom_llm_provider='openai')
    protected='\n'.join(m['content'] for m in converted['messages'] if m['role'] in ('system','developer'))
    assert 'approval_policy=on-request; sandbox_mode=workspace-write.' in protected
    assert json.loads(protected.split('host permissions still apply):\n',1)[1])==catalog


def test_parallel_native_call_ids_and_approval_metadata_survive_compaction():
    active=[{'role':'user','content':'Read both approved files.'},
        {'type':'function_call','call_id':'call-one','name':'read','arguments':'{"path":"one"}','approval_id':'approved-one'},
        {'type':'function_call','call_id':'call-two','name':'read','arguments':'{"path":"two"}','approval_id':'approved-two'},
        {'type':'function_call_output','call_id':'call-one','output':'first result'},
        {'type':'function_call_output','call_id':'call-two','output':'second result'}]
    payload={'model':'test','instructions':'Approval policy is on-request. Outside workspace writes denied.',
        'input':[{'role':'user','content':'completed ordinary source archive '*2000},{'role':'assistant','content':'recorded'}]+deepcopy(active)}
    original=deepcopy(payload)
    forwarded=compact_proxy_request(Counter(),payload,call_type='aresponses',target=1600)
    assert payload==original and forwarded['instructions']==original['instructions']
    assert forwarded['input'][-len(active):]==active


@pytest.mark.parametrize('item',[
    {'type':'mcp_approval_response','approval_request_id':'approval-1','approve':True},
    {'type':'mcp_approval_request','id':'approval-1','name':'external-tool'},
    {'type':'reasoning','summary':[],'encrypted_content':'opaque-provider-state'},
    {'type':'unknown_future_approval','approve':True},
])
def test_local_bridge_fails_closed_instead_of_dropping_unsupported_approval_state(item):
    import asyncio
    from app.gateway import LocalSift
    from fastapi import HTTPException
    data={'model':'qwen3.8-27b-codex','input':[item,{'role':'user','content':'Continue.'}]}
    with pytest.raises(HTTPException) as error:
        asyncio.run(LocalSift().async_pre_call_hook(None,None,data,'aresponses'))
    assert error.value.status_code==422
    assert data['input'][0]==item
