# What this local workhorse actually did

This stack is useful for **bounded, testable drafts and small code changes**. This trial does **not** support treating it as an unattended engineering agent. Correct output, reliable tool execution and obedience to a workflow are separate results.

The sealed native Claude/local-Qwen batch ran all13 cases once, with at most one same-session feedback phase. One CSV case has an invalid fixture/rubric and is excluded from the usefulness denominator, while its original rejected receipts remain published. Of the12 valid cases, **8 artifacts passed first attempt and10 passed at the end**. The original strict workflow result is **0/13 first attempt,2/13 final**. No failed session is promoted by reporting a correct artifact.

[Sealed task plan](../evidence/workhorse-v2-plan.json) · [Every artifact, native trace and parent replay](../evidence/workhorse-v2-parent-review.json) · [Invalid-case diagnostic](../evidence/workhorse-wh07-diagnostic-v2.json)

| Task | First artifact | Final artifact | Native phase time, total | Practical interpretation |
| --- | --- | --- | --- | --- |
| Page merge/deduplication | Pass | Pass |25.85s| Useful small utility; extra shell commands violate the strict contract. |
| JSONL counting and sample redaction | Pass | Pass |77.90s| Tested input cases work; CLI turn limit reached. Not proof of complete or security-grade PII removal. |
| UTC timestamp normalization | Pass | Pass |139.59s| Useful code, but substantial tool-loop overhead for a small change. |
| Strict boolean configuration parsing | Pass | Pass |81.00s| Correct tested implementation; CLI turn limit reached. |
| Stable row join with duplicate/collision handling | Pass | Pass |44.72s| Useful bounded transformation, with tests. |
| HTTP retry policy | Fail | Fail |47.43s| Returns `invalid_status` instead of the required `permanent` for invalid input types; terminal turn limit also reached. |
| Unicode CSV/label join | Invalid case | Invalid case |49.69s| Frozen source contains mojibake; hidden string-ID requirement was unstated. Not a clean model score. |
| Grounded memo extraction | Pass | Pass |19.91s| Correctly leaves unassigned accountable owner null. An extra phase adds no useful artifact correction. |
| Structured incident triage | Pass | Pass |23.28s| Correct facts and explicit safe-action policy; root cause remains null. Not an open-ended incident investigation. |
| Conflicting retention requirements | Fail | Pass after feedback |20.32s| Initially selects30days despite unresolved30/90 conflict; feedback corrects it to null. |
| Maintenance prerequisite checklist | Fail | Pass after feedback |18.16s| Initially omits snapshot verification; hold decision was already correct. |
| Ledger/report reconciliation | Fail | Fail |24.41s| Computes the right JSON inside attempted edits, but repeats a wrong `old_string` and never writes the file. |
| Existing repository usage-reporter enhancement | Pass | Pass |62.02s| Actual module snapshot gains Responses envelope/JSONL support and passes legacy/cache/CLI checks; terminal turn limit reached. Not applied to production source. |

The native phases total **634.27seconds (10m34s)**, including failed and redundant phases. This excludes fixture development, preflight fixes, tests, parent replay and review. These are task wall times, not decode benchmarks. There were18 native invocations, including5 feedback phases; only2 feedback phases changed a valid failing artifact into a passing artifact.

## Where to use local first

- Small stdlib utilities, configuration parsers and existing-module changes when an executable test can decide correctness. Six of seven development artifacts passed their hidden checks; strict native workflows still failed.
- Source-grounded structured extraction with an explicit schema, including missing-value handling. Inspect actual files, not only the final chat message.
- Draft triage summaries and checklists governed by explicit rules. Keep uncertain causes and unresolved ownership null; a drafted checklist is not authority to perform an operation.
- Repetitive work where a deterministic script can take over after its generated implementation is tested. For repeated arithmetic or CSV processing, run the script rather than asking the model to recalculate every time.

The existing shared-MTP decode benchmark and long-context Sift evidence explain capacity/speed, but do not establish these task success rates. This new pack mostly has short inputs; it is not a Sift-on/off ablation or a fresh1M semantic-retention test. No failure here is proven to have been caused by compaction.

## When to stop local and escalate

| Observed situation | Next action |
| --- | --- |
| Concrete failed assertion, otherwise progressing | Give local one precise failure and a bounded repair. Inspect the changed artifact and rerun the same tests. The retention/checklist cases demonstrate this working. |
| Repeated identical tool error, wrong edit target/context, or turn/time budget exhausted | Stop the loop. Re-read the actual target and reduce the task; use a cloud advisor for diagnosis or a new implementation attempt if the local repair still cannot finish. The ledger case repeated the same failed edit six times. |
| Broad architecture, repository-wide reasoning, uncertain debugging without a good oracle | Consider a stronger cloud model plus independent tests/review. These workloads are outside this small pack; cloud superiority on them was **not measured here**. |
| Missing owner, approval, source fact or conflicting authority | Ask the responsible person or retrieve the missing evidence. A cloud model cannot supply real approval or legitimately choose an unresolved policy. |
| Security-sensitive transformation or irreversible operation | Use audited deterministic controls and human authorization; seek cloud assistance only within the permitted data boundary. Neither a local nor a cloud answer is authorization or a security guarantee. |
| Invalid input data or a contradictory checker | Fix the harness/data in a separate epoch. Do not buy a stronger model to satisfy an impossible or unstated requirement. |

Cloud escalation here is a **workflow recommendation**, not a measured local-versus-cloud ranking. There is no paired cloud task baseline, cloud latency comparison or demonstrated savings. The supporting4000/default fixture worker itself produced a flawed draft and an unsupported test-pass claim; its raw failed work is preserved. A stronger route still needs verification.

For an optional advisor, send the smallest source excerpt, exact failure, attempted fix and acceptance check using the explicit [advisor setup](SETUP.md). Product inference stays local; there is no automatic cloud fallback. Keep caller approval/sandbox settings intact. **Do not loosen permissions to improve a benchmark score.**

## What went wrong in the evaluation itself

The initial v1 batch made13 requests rejected before generation, all with zero returned input/output tokens. The runner's credential filter accidentally removed numeric Claude output/context-limit variables. V2 fixes that environment filter, with regressions, preserving the original failed epoch and identical tasks/deadlines. This is a harness failure, not13 model-quality failures.

The CSV case's source contains codepointsU+00C3/U+0178 instead of the intended U+00DF. Its expected label assumes the intended character and its checker demands string IDs although the prompt never specified that type. Both original sealed attempts remain rejected. A separate posthoc diagnostic permits either stated-compatible ID representation and derives labels from the actual CSV: the first artifact is wrong, the repaired artifact matches. It is **not** promoted or counted as a successful primary case.

The strict workflow contract also requires every supplied file to be explicitly read, including `CONTRACT.md` which duplicates the task prompt, and permits only two exact shell-command forms. Safe redundant `cd` prefixes or listings still fail that declared contract. Some correct artifacts therefore have low practical-risk workflow misses; others have genuine repeated tool errors and turn-limit failures. Treating all of them as wrong code would mislead. Feedback on artifact checks alone also fails to tell the model about a missing read; those redundant phases are a harness limitation, not evidence that local repair is impossible.

The parent separately replayed every phase's artifact checks, source hashes, session continuity and successful native edit reconstruction.480 project tests pass, including48 focused pack/runner/config checks. Positive/negative controls are useful checks, but did not detect the CSV source-versus-oracle inconsistency; automated controls are not proof that a benchmark is valid.

The next useful comparative experiment would freeze representative real repository issues and run the same contracts on local and selected cloud models, with repeated seeds and calibrated human grading. That is unperformed follow-up, not an implicit claim of this result.

Method references: [Anthropic's verification and enforcement guidance](https://code.claude.com/docs/en/best-practices) distinguishes prompts from enforced rules; [OpenAI's evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices) recommends task-specific evaluation instead of judging by apparent success. These support the evaluation method, not the local model's measured results.
