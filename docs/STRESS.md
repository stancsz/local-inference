# Native CLI stress acceptance — in progress

This campaign tests a frozen, uncommitted Sift candidate from the owner's `codex/issue-59-error-code` checkout. Published main was still `e62ed81` when it was captured. [Provenance](../evidence/stress-candidate.json) and a [reconstructable patch](../evidence/stress-candidate.patch) identify the exact source; the original working tree is untouched. This is candidate acceptance, not a new Sift release announcement.

## Required matrix

21 sessions total: seven each for Claude Code, OpenCode and Codex. Each client runs evolving bounded-number utilities, configuration migration and daily CSV expense processing. Two full repetitions cover all nine client/task combinations, with a third engineering repetition for each client. Fixtures are synthetic; the CLI processes, model inference, file edits and tests are real.

An accepted session must have over 180 active client seconds (configured minimum 185), at least nine substantive user turns, one persisted native session ID, completed matching native tool events, an immutable public test file, independent hidden-test passes and the retained approved historical fact. Failed attempts remain failures. Client subprocess duration is measured; controller/monitor waits do not pad it. The controller stops for investigation if a failed session cannot meet the long-session criteria.

The first accepted Claude and OpenCode sessions completed nine turns each in **1,040.878 and 1,067.216 active seconds** respectively. This is a substantial long-context stress workload, not the short-prompt 103 tok/s decode benchmark. The remaining matrix is running; no 21-session acceptance claim is made yet. Live local state is `evidence/stress-campaign.json`; the published checkpoint is [stress-checkpoint.json](../evidence/stress-checkpoint.json). Completed traces are compressed and verified by `python -m stress.publish`, with hashes in [stress-published.json](../evidence/stress-published.json). In-progress receipts and native streams remain under ignored `tmp/stress/sessions/`.

## Route and versions

```text
Claude / OpenCode / Codex
  -> isolated loopback Sift test adapter (frozen candidate, LiteLLM 1.103.0)
  -> local-inference :8090 (native-counted mandatory Sift, LiteLLM 1.106.4)
  -> local llama.cpp :8091, Qwen3.8-27B IQ3_XXS + Q4 MTP
```

The test adapter injects an older 8,000-record archive and exercises Sift's CLI protocol handling. Its first-stage token counts are LiteLLM counts, not claims of exact Qwen native counts. The final gateway independently applies its native full-request counter and window/output/headroom limits. The campaign stores both audit layers. All campaign task inference is local Qwen; there is no cloud fallback. A separate, small council consultation informed the bridge design and is not a campaign sample.

Codex uses a dedicated `qwen3.8-27b-codex` Responses alias. LiteLLM converts it to Chat Completions and re-enters the guarded local Qwen route. Native function/custom-tool streaming continuation and final token-count parity passed preflight. Opaque server-held Responses histories are rejected. Codex uses a conventional tool profile copied from its own installed catalog; code-mode-only behavior is not claimed. Web search is disabled for this local model. Claude/OpenCode profiles are also isolated; global settings and credentials are not changed.

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
- Claude's background title request exposed immediate `429 Sift busy` rejection. Nonessential traffic is disabled, and the gateway now waits up to 15 seconds for its single Sift slot before returning 429. Concurrency remains bounded at one.
- Candidate offline suite: 575 passed and one skipped initially; two Git-fixture checks failed because an archive resolved the parent repository. Adding the correct base-commit Git metadata inside the isolated snapshot made both affected checks pass. The candidate source bytes did not change.
- Refreshed text/tool, OpenAI, Responses and 256k/1M retention checks passed. The legacy productivity validator initially rejected a correct explicit artifact mapping; acceptance now permits that optional field only with exact manifest filenames. Wrong arithmetic and swapped mappings remain rejected.

Final acceptance rates, latency distributions, memory observations and independent trace review remain pending. Short preflight/setup failures do not count as completed long sessions. No universal model-quality, retention-equivalence, cloud-savings or simultaneous 64k-under-14-GB claim follows from this campaign.
