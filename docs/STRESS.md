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
