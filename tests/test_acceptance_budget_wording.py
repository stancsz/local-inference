import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))

@pytest.mark.parametrize('suffix',['part of the input budget, never added to it','part of the input budget and never added to it','part of the input budget and is never added to it'])
def test_budget_relationship_accepts_equivalent_wording(suffix):
    from claude_acceptance import input_budget_invariant
    assert input_budget_invariant('The Sift target is '+suffix)

@pytest.mark.parametrize('suffix',['not part of the input budget, never added to it','part of the input budget and is added to it','added to the input budget'])
def test_wrong_budget_relationship_is_rejected(suffix):
    from claude_acceptance import input_budget_invariant
    assert not input_budget_invariant('The Sift target is '+suffix)

@pytest.mark.parametrize('target', ['`sift_target`', '`SIFT_TARGET`', '`Sift target`'])
def test_markdown_configuration_name_keeps_the_same_budget_meaning(target):
    from claude_acceptance import input_budget_invariant
    assert input_budget_invariant('The '+target+' is part of the input budget, never added to it')
    assert not input_budget_invariant('The '+target+' is part of the input budget and is added to it')

def test_anchor_inside_input_budget_has_the_same_non_additive_meaning():
    from claude_acceptance import input_budget_invariant
    phrase='The Sift target is an adaptive policy anchor inside the input budget, never added to it'
    assert input_budget_invariant(phrase)
    assert not input_budget_invariant(phrase.replace('inside', 'outside'))
    assert not input_budget_invariant(phrase.replace('never added', 'added'))


def guide():
    return '''The adaptive anchor range is 24576..36608. The Sift target is part of the input budget and is never added to it. Reserve 256 tokens of decoder headroom.
```text
context_window=40960
sift_target=32768
output_reserve=4096
draft_tokens=4
```
```powershell
docker compose up -d --build
curl.exe http://127.0.0.1:8090/health/readiness
curl.exe http://127.0.0.1:8091/health
python scripts/claude_acceptance.py
docker compose logs --no-color gateway > tmp/sift-runtime.log
docker compose down
```
'''


def test_configuration_is_not_required_to_be_an_executable_command():
    from claude_acceptance import validate_operator_guide
    assert validate_operator_guide(guide())


def test_extra_or_missing_commands_are_rejected():
    from claude_acceptance import validate_operator_guide
    assert not validate_operator_guide(guide()+'\n```powershell\nRemove-Item *\n```')
    assert not validate_operator_guide(guide().replace('docker compose down',''))


def test_numeric_thousands_separators_do_not_change_budget_meaning():
    from claude_acceptance import validate_operator_guide
    assert validate_operator_guide(guide().replace('24576..36608','24,576 to 36,608'))
