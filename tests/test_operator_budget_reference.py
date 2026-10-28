"""Equivalent explicit anchor references must not fail the runbook grader."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from claude_acceptance import input_budget_invariant

def test_explicit_setting_then_pronoun_is_equivalent():
 text=('`sift_target=32768` is the adaptive policy anchor, not a fixed forwarded budget; '
       'it is part of the input budget and never added to it.')
 assert input_budget_invariant(text)

def test_reference_never_accepts_additive_or_unrelated_anchor():
 assert not input_budget_invariant('sift_target=32768 is the adaptive policy anchor, not a fixed forwarded budget; it is added to the input budget.')
 assert not input_budget_invariant('The output reserve is the adaptive policy anchor, not a fixed forwarded budget; it is part of the input budget and never added to it.')
 assert not input_budget_invariant('sift_target=32768 is outside the input budget; it is part of the input budget and never added to it.')

def test_negated_invariant_is_rejected():
 assert not input_budget_invariant('sift_target=32768 is the adaptive policy anchor, not a fixed forwarded budget; it is not part of the input budget and never added to it.')
