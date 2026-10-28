# Run locally. Consult the cloud selectively.

Use local Qwen for reading files, tool loops, drafts and routine changes. Give a strong cloud model a short evidence packet when a consequential decision needs better judgment. Return its recommendation to the local worker, then verify the result. The cloud advisor is optional; inference continues without it.

This is a tested Windows/RTX 5070 Ti setup, not a universal hardware installer. It runs two containers and one CPU Sift callback. There is no automatic cloud fallback, routing database or background advisor.

## What you need

| Component | Tested or required |
| --- | --- |
| GPU | RTX 5070 Ti, 16 GB; substantial free VRAM before loading |
| Memory | About 48 GiB host RAM in the measured environment |
| Disk | Approximately 50 GB free for weights, staging, resumable chunks and images |
| Runtime | Docker Desktop in Linux-container mode with NVIDIA GPU access |
| Host tools | Git, Python 3.11+, PowerShell 7 (`pwsh`), Claude Code CLI on PATH |
| Network | Initial model/image downloads; optional advisor calls |

Different NVIDIA GPUs may work, but throughput and memory fit need new measurements. An 8 GB GPU cannot use this measured full-GPU 27B profile. Smaller models and CPU offload require separate tuning and acceptance. The launcher currently invokes Windows `claude.cmd`; Linux/macOS launcher support is not established.

## Install and verify

Run these commands in PowerShell from a directory where both repositories can live beside each other. Use the Sift revision pinned in the root [README](../README.md#setup).

```powershell
git clone https://github.com/stancsz/local-inference.git
git clone https://github.com/stancsz/sift.git
cd local-inference
git -C ../sift checkout 2f0ef2786345fe0868b282903712fd1ac92d43fe
python scripts/setup_env.py
python scripts/download_ranges.py
pwsh -NoProfile -File scripts/stage_models.ps1
docker compose up -d --build
python scripts/local_smoke.py
python scripts/openai_smoke.py
```

The gateway builds Sift from that pinned sibling source. `setup_env.py` creates a local ignored `.env` key. It does not install Python dependencies or configure your cloud credentials. The downloader verifies pinned weight SHA256s; keep `models/` and `tmp/chunks/` for reproducible download/resume. Weights are staged into the persistent Docker volume `local-inference-models` because Windows bind mounts loaded much more slowly in this experiment.

Start with the default profile: 40,960 context, at most 4,096 generated tokens, four MTP draft tokens and one inference slot. Keep requests sequential. Sift adapts the input budget to request size; its daily range with full output reservation is 24,576–36,608. Short inputs pass unchanged. Large raw histories may contain up to 1,050,000 native tokens, subject to character/node limits. That is raw history capacity, not a 1M native model context or a guarantee that every historical detail survives.

The optional shared-weight64k-input profile passed exact65,536 input+4,096 output and the sampled containing-VM upper bound below14decimalGB on this host. Earlier separate-draft profiles exceeded that limit; preserve that distinction. Start the tested long profile with `docker compose -f compose.yaml -f compose.long.yaml up -d --force-recreate`; restore the faster daily profile with `docker compose up -d --force-recreate`. Read [the measured profiles and limits](PROFILE_RESULTS.md) first. Free unused app VRAM after saving work; never kill DWM. Inspect with `pwsh -NoProfile -File scripts/host_vram.ps1`.

## Do useful work locally

From the repository you want to work on, invoke the launcher by absolute path. It preserves your current working directory and isolates the local endpoint/key from your saved cloud CLI settings.

```powershell
python C:/path/to/local-inference/scripts/claude_local.py
```

For a bounded task with a usage receipt:

```powershell
New-Item -ItemType Directory -Force tmp | Out-Null
python C:/path/to/local-inference/scripts/claude_local.py -p "Inspect the failing test, make the smallest scoped repair, run the relevant test, and report changed files and remaining risks. Stop if requirements are ambiguous." --permission-mode acceptEdits --max-turns 8 --output-format json > tmp/local-task.json
```

`acceptEdits` authorizes file edits; inspect the diff before committing. Keep shell permissions scoped through the CLI's normal permission controls. The model is quantized and thinking is disabled; validate factual reports and generated code. Readiness is insufficient acceptance: run `python scripts/claude_acceptance.py` from this project for its three real-task probes. The tested CLI version is recorded in [verification](../VERIFICATION.md); newer releases need fresh acceptance. This non-Claude backend integration is project-tested, not vendor-certified ([Claude gateway compatibility guidance](https://code.claude.com/docs/en/llm-gateway)).

## Add a strong cloud advisor

Choose a strong model you already have access to, ideally one that reliably improves decisions on your own evaluation tasks. Configure its exact model ID and an OpenAI-compatible HTTPS endpoint. The model is explicit: this project does not silently choose a provider or downgrade a failed call. For an Anthropic-only endpoint, supply an OpenAI-compatible adapter outside this stack or use your existing cloud client; this script does not translate native Anthropic requests.

In the calling PowerShell process, set `ADVISOR_BASE_URL` including `/v1`, `ADVISOR_MODEL`, and `ADVISOR_API_KEY`. Read the key without placing it in shell history:

```powershell
$env:ADVISOR_BASE_URL = 'https://YOUR-PROVIDER/v1'
$env:ADVISOR_MODEL = 'YOUR-STRONG-MODEL-ID'
$advisorSecret = Read-Host 'Advisor API key' -AsSecureString
$advisorCredential = [System.Net.NetworkCredential]::new('', $advisorSecret)
$env:ADVISOR_API_KEY = $advisorCredential.Password
```

The placeholder endpoint/model must be replaced with your provider's actual values. Use a dedicated restricted inference key; do not reuse the local gateway key or give a remote provider a gateway master key. An existing owner-configured LiteLLM `http://127.0.0.1:4000/v1` route can also be used with its authorized inference key and model alias. It is optional tooling, not a runtime dependency of this project. The local `:8090` gateway serves only Qwen and cannot itself serve as the strong cloud advisor.

Create `tmp/advisor-packet.txt` with at most 6,000 characters:

```text
Decision: which of these two repairs should the local worker implement?
Observed failure: <exact minimal error>
Relevant code/diff: <small excerpt>
Already tried: <one or two outcomes>
Constraints: <scope, latency, correctness requirements>
Question: recommend the smallest repair, a discriminating test and a stop condition.
```

Strip secrets and include only data you authorize sending to that provider. Ask about one decision; omit entire conversations and raw tool logs. Invoke it once:

```powershell
python scripts/advisor.py --packet tmp/advisor-packet.txt > tmp/advisor.json
```

The helper makes one text-only call, with no tools, retries, fallback or credential-bearing redirects. It bounds the packet, requests at most 1,024 output tokens and sets a 90-second HTTP timeout. Those bounds are not a provider-enforced dollar budget or an exact total wall-clock guarantee. Use your provider's spending controls and inspect usage. If the model requires a different API or rejects the output-limit parameter, the helper fails visibly; configure a compatible endpoint rather than guessing a fallback. A truncated answer exits unsuccessfully.

Pass the advice back to the local worker as context, with the original task constraints and verification command. Advice is not evidence that a test passed. Escalate on a consequential unclear choice or a repeated failed repair; avoid sending every local tool turn to the advisor. Remove the process credential afterward:

```powershell
Remove-Item Env:ADVISOR_API_KEY
Remove-Variable advisorCredential, advisorSecret
```

## Measure the 99% target

**99%+ reduction in cloud-token usage is a goal, not a result established by this repository.** Local delegation can keep most file/tool traffic off cloud inference, but advisor overhead, retries and harder tasks can erase the benefit. Sift reduces forwarded context; it does not by itself prove cloud-token savings or equivalent model quality.

Save complete `--output-format json` or terminal `stream-json` receipts for every local run, advisor call and failed attempt. Compare usage:

```powershell
python scripts/usage_report.py --local tmp/local-task.json --advisor tmp/advisor.json
```

The report counts Claude's separate cache/input/output fields and OpenAI-compatible prompt/completion fields without double-counting cached tokens. Supply multiple receipt paths after each flag for a whole workload. The output is a **cloud-token share**: `advisor_tokens / (local_tokens + advisor_tokens)`. A share at or below 1% is not a proven 99% saving against a cloud-only workflow; local and cloud models can take different numbers of turns and achieve different results. Do not pad local work to improve the ratio.

To measure an actual reduction, replay equivalent tasks on the chosen cloud-only setup, require the same acceptance checks, include all failed attempts/retries in both totals, and record that baseline's cloud-token total. Then run:

```powershell
python scripts/usage_report.py --local tmp/local-task.json --advisor tmp/advisor.json --baseline-cloud-tokens 100000
```

`100000` is an illustrative placeholder to replace with your measured baseline. The calculation is `100 × (1 - measured_advisor_cloud_tokens / baseline_cloud_tokens)`. Missing usage means the accounting is incomplete. This does not calculate money saved: provider prices, cache discounts, electricity, GPU purchase and your time require separate accounting. There is no measured 99%+ savings receipt yet.

The included [accounting example](../evidence/usage-example.json) combines six local acceptance attempts (including rejected outputs) with one explicit advisory review. It reports 103,441 local tokens and 1,710 cloud-advisor tokens: 1.63% cloud share. Those were different tasks/review scopes, with no cloud-only baseline; this is a working accounting example, not proof of savings or a tuned advisor-assisted workflow.

## Keep it predictable

| Symptom | First action |
| --- | --- |
| Model fails to load / CUDA out of memory | Save work, inspect `nvidia-smi` and inference logs, free unused app VRAM, restore the daily profile. Do not repeatedly increase the window. |
| Port 8090 ready but tasks fail | Run the text/tool smoke and real Claude tasks; inspect `docker compose logs --no-color gateway`. |
| HTTP 422 from Sift | Mandatory content or schema may exceed the budget, or input/config may be invalid. Split the current task or reduce oversized tool results. Do not bypass compaction. |
| HTTP 429 / Sift busy | One-slot workflow: wait for the active request and retry deliberately; do not fan out workers. |
| Slow startup | Verify Linux volume staging; do not restage while inference uses the volume. |
| Advisor fails | Keep the local result/evidence and inspect the explicit endpoint/model configuration. No automatic cloud retry or fallback occurs. |

```powershell
docker compose stop
docker compose start
docker compose logs --no-color inference
docker compose down
```

`stop/start` retains containers; `down` removes this project's containers/network. The external model volume and ignored host weights persist. The default restart policy is `no`, so after a host reboot start Docker Desktop, then `docker compose up -d`. This is a persistent, manually started setup, not an installed unattended startup service. Keep `.env` private and backed up; a new key requires recreating the gateway and updating any external clients. Services bind to loopback; do not expose this personal stack as a multi-user public gateway.

For CLI flags and usage output, consult the [Claude CLI reference](https://code.claude.com/docs/en/cli-reference). For every model/runtime upgrade, rerun the local checks before relying on earlier receipts.
