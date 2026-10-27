# Native CLI stress acceptance — in progress

This campaign tests a frozen, uncommitted Sift candidate from the owner's `codex/issue-59-error-code` checkout. Published main was still `e62ed81` when it was captured. [Provenance](../evidence/stress-candidate.json) and a [reconstructable patch](../evidence/stress-candidate.patch) identify the exact source; the original working tree is untouched. This is candidate acceptance, not a new Sift release announcement.

## Required matrix

21 sessions total: seven each for Claude Code, OpenCode and Codex. Each client runs evolving bounded-number utilities, configuration migration and daily CSV expense processing. Two full repetitions cover all nine client/task combinations, with a third engineering repetition for each client. Fixtures are synthetic; the CLI processes, model inference, file edits and tests are real.

An accepted session must have over 180 active client seconds (configured minimum 185), at least nine substantive user turns, one persisted native session ID, completed matching native tool events, an immutable public test file, independent hidden-test passes and the retained approved historical fact. Failed attempts remain failures. Client subprocess duration is measured; controller/monitor waits do not pad it. The controller stops for investigation if a failed session cannot meet the long-session criteria.

Captured fixtures under `evidence/stress-sessions/` preserve their original bytes through Git attributes, including Windows line endings. This keeps public-test and source hashes verifiable across checkout platforms. [Byte-integrity evidence](../evidence/stress-fixture-byte-integrity.json) compares indexed, published and original workspace bytes; refresh it for the complete campaign before final acceptance. Native streams and full receipts remain compressed without text conversion.

The first accepted Claude and OpenCode sessions completed nine turns each in **1,040.878 and 1,067.216 active seconds** respectively. This is a substantial long-context stress workload, not the short-prompt 103 tok/s decode benchmark. The remaining matrix is running; no 21-session acceptance claim is made yet. Live local state is `evidence/stress-campaign.json`; the published checkpoint is [stress-checkpoint.json](../evidence/stress-checkpoint.json). Completed traces are compressed and verified by `python -m stress.publish`, with hashes in [stress-published.json](../evidence/stress-published.json). In-progress receipts and native streams remain under ignored `tmp/stress/sessions/`.

After the Codex corrections below, a fresh engineering session passed all nine turns in **863.291 active seconds**. Parent review replayed all native turns and reran nine hidden-test stages with another seed against its final implementation; [acceptance receipt](../evidence/stress-codex-parent-acceptance.json). The corrected-epoch 21-session matrix has resumed and will reuse this matching Codex receipt. Earlier Claude/OpenCode samples retain their original source hashes and are historical, rather than corrected-epoch passes. Full matrix acceptance remains pending.

The corrected-epoch Claude session also passed all nine workflow turns in 980.493 active seconds; OpenCode has also completed nine turns in 1069.701 active seconds; all three clients now cover engineering and configuration migration is running next. Workflow acceptance is only the frozen harness result. Additional final-artifact probes found that the corrected-epoch Claude and OpenCode implementations, plus the historical OpenCode implementation, skip bound validation for empty bulk inputs, while the fresh Codex and historical Claude artifacts pass. See [additional contract probes](../evidence/stress-contract-probes.json). These observations remain separate from original workflow receipts and are required context for the final quality report. Run `python -m stress.contract_probe` to inspect completed artifacts without changing the running workload. Earlier stage checks are separately executed; seed-dependent unseen inputs occur at the final stage, so a different seed does not create different cases at every earlier stage.

## Route and versions

```text
Claude / OpenCode / Codex
  -> isolated loopback Sift test adapter (frozen candidate, LiteLLM 1.103.0)
  -> local-inference :8090 (native-counted mandatory Sift, LiteLLM 1.106.4)
  -> local llama.cpp :8091, Qwen3.8-27B IQ3_XXS + Q4 MTP
```

The test adapter injects an older 8,000-record archive and exercises Sift's CLI protocol handling. Its first-stage token counts are LiteLLM counts, not claims of exact Qwen native counts. The final gateway independently applies its native full-request counter and window/output/headroom limits. The campaign stores both audit layers. All campaign task inference is local Qwen; there is no cloud fallback. A separate, small council consultation informed the bridge design and is not a campaign sample.

Codex uses a dedicated `qwen3.8-27b-codex` Responses alias. LiteLLM converts it to Chat Completions and re-enters the guarded local Qwen route. Native function/custom-tool streaming continuation and final token-count parity passed preflight. Opaque server-held Responses histories are rejected. Codex uses a conventional tool profile copied from its own installed catalog; code-mode-only behavior is not claimed. Web search is disabled for this local model. Claude/OpenCode profiles are also isolated; global settings and credentials are not changed.

Native Codex resume can append developer instructions after completed conversation turns. Qwen's template rejects that position. The dedicated bridge preserves their text in input order alongside existing leading instructions, before the inner Sift/native counter; it leaves user/tool history in its original order. Unsupported instruction content fails closed. This is an explicit local-model compatibility adaptation, not a claim that instruction timing is unchanged for every model. The new gateway image and harness source hashes define another campaign epoch; previous rejected resume receipts stay rejected.

With user configuration ignored, Codex resume also requires an explicit process-only `sandbox_mode="workspace-write"`; the initial exec's `--sandbox` flag alone did not retain write access here. The harness sets both paths explicitly. No sandbox bypass or global configuration change is used. A native denied-write/hidden-test failure is preserved in [the permission receipt](../evidence/stress-resume-permissions.json); 44 local tests include the initial/resume command regression.

Observed CLI versions: Claude Code 2.1.251, OpenCode 1.15.10 and Codex CLI 0.154.0. The host test dependencies are pinned in [requirements-stress.txt](../requirements-stress.txt). The normal GPU model profile is unchanged: 40,960 total context, up to 4,096 output tokens and 256 decoder-headroom tokens, one slot and four MTP draft tokens.

## Reproduce

First complete the normal [setup](SETUP.md). Use a fresh Python environment for optional stress dependencies; do not replace a working global environment just for this campaign.

```powershell
python -m pip install -r requirements-stress.txt
python scripts/prepare_stress_snapshot.py
docker compose build gateway
docker compose -f compose.yaml -f compose.stress.yaml build gateway
docker compose -f compose.yaml -f compose.stress.yaml up -d --no-deps gateway
$env:PYTHONPATH = "$PWD/tmp/stress/sift-candidate/src;$PWD"
python scripts/runtime_receipt.py --sift-source tmp/stress/sift-candidate
python -m stress.preflight --client claude
python -m stress.preflight --client opencode
python -m stress.preflight --client codex
python -m stress.campaign --prechecks
```

Snapshot creation refuses to overwrite an existing directory. Existing preflight directories also require a new `--label`; preserve failures. The campaign reuses matching terminal long-session receipts, verifies frozen source and the gateway image between sessions, and writes atomic checkpoints. Run one controller at a time. It is sequential because this GPU profile has one slot. On Windows the controller requests system wakefulness only for its own lifetime and restores that request on exit; it does not change the saved power plan or require the display to stay on.

Optional GPU sampling, from a second terminal after reading the controller's actual PID:

```powershell
python -m stress.monitor --pid YOUR_CONTROLLER_PID
```

The monitor verifies a live process handle and samples total host occupancy. These values include desktop activity; they are not isolated per-model allocation measurements or proof of a strict 14 GB cap. The stress image changes only the gateway; inference weights, GPU profile and other Docker projects remain untouched. After the campaign is stopped, `docker compose up -d --no-deps gateway` restores the normal gateway image.

## Findings so far

- All three CLIs passed large-context native-tool preflight through local Qwen. The first Codex attempt advertised unsupported web search; the corrected isolated local profile disables it.
- The first full Codex session launch exposed a missing sandbox helper import before inference. The small local helper now exercises an actual workspace write and rejection of an outside write before the model starts. The zero-turn failed launch is excluded from long-session counts.
- A subsequent Codex attempt passed its hidden tests and historical fact but failed native workflow recognition after one 148-second turn. The trace contains native shell writes rather than separate file-change events. That receipt stays rejected. One bounded :4000/default implementation worker produced an incomplete patch; parent review replaced its broad recognizer, completed quoted-wrapper and exact absolute-workspace handling, and passed 40 local tests covering negative paths, failed writes and ordering. Both stored rejected traces now replay correctly without rewriting their original outcomes. One further setup trial was stopped by the parent before changing frozen source and is explicitly excluded. A fresh nine-turn local-Qwen Codex session is running; the matrix remains paused pending its acceptance. Changed harness hashes begin a new matrix epoch; earlier accepted sessions retain their original provenance. [Parent review](../evidence/stress-native-fix-review.json), [bounded worker](../evidence/stress-repair-worker.json), and [recovery status](../evidence/stress-recovery-status.json) preserve this distinction.
- Claude's background title request exposed immediate `429 Sift busy` rejection. Nonessential traffic is disabled, and the gateway now waits up to 15 seconds for its single Sift slot before returning 429. Concurrency remains bounded at one.
- Candidate offline suite: 575 passed and one skipped initially; two Git-fixture checks failed because an archive resolved the parent repository. Adding the correct base-commit Git metadata inside the isolated snapshot made both affected checks pass. The candidate source bytes did not change.
- Refreshed text/tool, OpenAI, Responses and 256k/1M retention checks passed. The legacy productivity validator initially rejected a correct explicit artifact mapping; acceptance now permits that optional field only with exact manifest filenames. Wrong arithmetic and swapped mappings remain rejected.

Final acceptance rates, latency distributions, memory observations and independent trace review remain pending. Short preflight/setup failures do not count as completed long sessions. No universal model-quality, retention-equivalence, cloud-savings or simultaneous 64k-under-14-GB claim follows from this campaign.

## Reviewed interruption and fixed continuation

The second OpenCode expense sample (seed 1951) stopped after one 240-second turn with repeated identical writes, incomplete workflow evidence and failed hidden tests. It remains rejected and cannot count toward long-session coverage. Its exact receipt and native trace are preserved in `evidence/stress-failures/opencode-expenses-r1`; `stress-failure-recovery.json` records their hashes and the continuation plan.

The controller accepts an explicit receipt path and SHA256 acknowledgment for this reviewed short failure. This only permits continuing past it; acceptance, frozen source checks, local routing, nine-turn requirements and timeouts are unchanged. The original remaining four cases run unchanged, followed by one predeclared OpenCode expense sample (repeat 2, seed 2951). Thus there are 22 planned attempts targeting 21 qualifying long sessions, seven per client. The extra sample has no further retry or timeout extension if it fails. All outcomes remain in the report denominator; final independent review is still required.

Recovery verification: eight acknowledgment/provenance regression checks and the full 52-test project suite passed with the frozen candidate on `PYTHONPATH`. An unscoped pytest invocation collected archived/snapshot fixtures and failed collection; a subsequent invocation without the candidate path could not import `sift.dynamic`. Neither was a product test result. The documented candidate environment plus `pytest tests` is the applicable suite.

The next Codex expense case (seed 2051) also failed after one 240-second turn. It retained the history fact but repeatedly wrote code still failing category grouping. This second original case is preserved separately in [failure evidence](../evidence/stress-codex-expense-failure.json); acknowledging its exact hash permits running remaining independent cases without rerunning it. The fixed plan now has a maximum of 20 corrected-epoch nine-turn long sessions. Its target of 21 remains unmet; no further replacement seed or timeout increase is planned.

The commander's representative offline probe retained all 15 actual completed command outputs, including four failed-test outputs, through Chat and Responses hook fixtures and a native OpenAI final-stage budget check. This demonstrates no retention defect for those fixtures, while original campaign wire payloads remain unavailable. The supporting Claude worker missed its three-minute artifact checkpoint and was stopped without a verdict; its partial trace and key revocation are retained. See [diagnostic evidence](../evidence/stress-feedback-review.json) and run `python -m stress.feedback_probe` to reproduce the representative checks without inference calls. Current outcomes and limits are reconciled in [stress results](STRESS_RESULTS.md).

Rejected terminal runner attempts, including historical setup/compatibility failures, are compressed with byte hashes in [the rejection manifest](../evidence/stress-rejected.json). Run `python -m stress.publish_failures` to reproduce this archive; it excludes in-progress receipts, retains `accepted=false`, and refuses to overwrite changed archived bytes. These heterogeneous attempts remain separate from the fixed current-matrix denominator.

## Terminal fixed-plan outcome

All 22 planned attempts have terminal receipts:19 accepted nine-turn sessions and 3 rejected one-turn expense attempts. Required 21 qualifying current-source sessions remain unmet (shortfall 2); no reroll or timeout increase follows. The final extra OpenCode expense sample passed its public/hidden tests and history checks but hit240 seconds without a successful CLI terminal event. Controller/supervisor processes are terminal. The earlier running descriptions above are historical milestones; current totals and constraints are in [the reconciled outcome report](STRESS_RESULTS.md).

The supporting reporting worker was stopped after its five-minute artifact checkpoint was missed, with no report/code changes or handoff. Its trace and revoked task key are preserved. Commander reconciliation independently reparsed 189 published native streams and compared 63 published fixture bytes against original workspaces, Git index, recorded hashes and public-test/contract-probe digests. These 21 published samples include two older gateway/harness epochs, so they are not 21 current-source sessions. Reproduce the no-inference verification with `python -B -m stress.verify_publication`; all 57 project tests passed. Final nonauthor acceptance remains pending.

Independent nonauthor review of revision8989c9b accepted report/publication reconciliation and rejected full-goal and unattended-production readiness. Its execution phase hit a tool cap; the final text-only handoff reviewed captured actual observations and raw representative excerpts. The original verdict is preserved, with parent corrections to a historical/current engineering count and rejected-archive schema details recorded separately. Required21 current sessions remain unmet by2. See [verdict](../evidence/stress-independent-review.json), [provenance](../evidence/stress-independent-review-provenance.json) and [parent clarifications](../evidence/stress-independent-review-parent-response.json).

## Separate expense-validation recovery fixture

[expenses_v1.py](../recovery/expenses_v1.py) repairs the recorded category-grouping, missing-amount and extra-cell examples as a deterministic stdlib fixture. Regression tests compile the original model artifacts read-only and demonstrate that the same contract checks reject those baselines and accept the repair. Parent review additionally caught delimited empty rows being skipped, then fixed that behavior with red/green tests. Run `python -B -m pytest -q tests/test_expense_recovery.py` (13 passed); the complete project suite passed 70 tests. [Evidence and scope](../evidence/expense-recovery-v1.json) preserves the worker's initial candidate, receipt, parent correction and test logs.

All nine frozen expense **behavior** checks and 12 additional expense probes passed against this fixture. Historical-evidence/model-retrieval assertions are outside this pure code check and were not simulated. No frozen campaign task, input seed, timeout or rejection was rewritten; the campaign remains 19/21 qualifying sessions with a two-session shortfall. This repair does not show that local Qwen generated corrected code or resolve final full-goal/production acceptance.

## Separate engineering recovery fixture

[clamp_v1.py](../recovery/clamp_v1.py) validates lower/upper types, booleans, finite floats and reversed bounds before processing empty inputs. Valid empty results, ordering, single-use iterators and normal clamp/report behavior are retained. Parent review completed an interrupted worker's test artifact and fixed large-finite-integer overflow. [Evidence](../evidence/engineering-recovery-v1.json) preserves red/green outputs and the initial worker artifacts: the final 44-test suite fails 26 checks on frozen bad code and passes on the repair. The full project suite passed 114 tests.

Reproduce the separate code checks with `python -B -m pytest -q tests/test_engineering_recovery.py` and `python -B -m recovery.check_fixture --task engineering --candidate recovery/clamp_v1.py`. The latter runs nine original behavior stages plus nine existing probes, excludes model-history assertions, writes no evidence/campaign files and makes no inference calls. It also supports the expense fixture via `--task expenses --candidate recovery/expenses_v1.py`. These deterministic repairs leave all recorded model results and the 19/21 campaign count unchanged; migration and final goal/production acceptance remain unresolved.
