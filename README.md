# local-inference

**Do the token-heavy work locally. Bring in a strong cloud advisor for the decisions that need it.**

Run a quantized 27B model with MTP at **103.45 tok/s average decode** on a 16 GB RTX 5070 Ti. Keep file reads, drafts and tool loops on your GPU; send a small evidence packet to an optional cloud advisor. Two containers, explicit limits, reproducible receipts.

[Get started](#setup) · [Practical setup and advisor workflow](docs/SETUP.md) · [Measured speed](#measured-speed-on-rtx-5070-ti) · [Evidence and limits](VERIFICATION.md)

An independent, minimal LiteLLM gateway serving Dockerized Qwen3.8-27B IQ3_XXS + Q4 MTP on a Windows RTX 5070 Ti (16 GB). Claude Code uses LiteLLM at `http://127.0.0.1:8090`; mandatory Sift runs in its pre-call callback. llama.cpp runs on `8091` for diagnostics. Neither endpoint is exposed beyond loopback. There is no Subroute runtime dependency, cloud fallback, database, Redis, or separate compaction service.

**Status: the recommended local workflow is running and verified on this host.** Live text/tool continuation, three Claude productivity tasks, 256k/1M compaction and exact 64k+4k capacity have receipts. See [verification and limits](VERIFICATION.md), [GOAL.md](GOAL.md), and [evidence](evidence). These bounded tests do not establish general task quality or information-retention parity.

## Lower cloud usage, explicit tradeoffs

- **Local execution:** OpenAI-compatible Chat Completions and Anthropic Messages for the local Qwen model; Claude Code launcher included.
- **Adaptive context:** Sift selects useful history within a request-dependent budget, preserving protected work and failing closed on overflow.
- **Optional cloud judgment:** a bounded, text-only [advisor command](docs/SETUP.md#add-a-strong-cloud-advisor), with your chosen model and no automatic fallback.
- **Maintainable operation:** pinned weights/runtime, persistent Docker model volume, one inference slot and inspectable usage receipts.

**99%+ lower cloud-token usage is a target to measure, not a benchmark we have achieved.** Use the [comparison workflow](docs/SETUP.md#measure-the-99-target) to account for advisor calls, retries and equivalent cloud-only work. Hardware, electricity, cache pricing and model quality affect the actual cost tradeoff. The local gateway needs no cloud credential; the optional advisor stays outside its runtime.

## Measured speed on RTX 5070 Ti

**103.45 tok/s average decode, peaking at 104.09 tok/s**, with Qwen3.8-27B IQ3_XXS + Q4 MTP, four draft tokens and the recommended 40,960-token context window.

| Context profile | MTP draft tokens | Average decode | Raw receipts |
| --- | --- | --- | --- |
| 40k daily | 4 (recommended) | **103.45 tok/s** | [Two samples](evidence/benchmark-mtp4-40k.json) |
| 40k daily | 2 | 91.60 tok/s | [Two samples](evidence/benchmark-mtp2-40k.json) |
| 64k-input | 2 | 91.18 tok/s | [Two samples](evidence/benchmark-mtp-64k-ubatch64.json) |
| 64k-input | Disabled | 49.92 tok/s | [Two samples](evidence/benchmark-no-mtp-64k-ubatch64.json) |

The matched larger-window comparison measured **1.83× faster decode with MTP** ([summary](evidence/benchmark-summary.json)). Each row contains two sequential short-prompt runs generating 256 tokens each, one cold and one cached. The context profiles describe capacity; these runs did not fill that window. Rates measure backend token generation, excluding Sift compaction and prompt processing; they do not measure end-to-end Claude task throughput or establish equal output quality. See [verification](VERIFICATION.md) for the separate long-context and real-task results.

## Setup

Requirements: Docker Desktop with Linux GPU support, NVIDIA driver, Python 3.11+, PowerShell, Claude Code CLI, and approximately 50 GB free disk for images, staged weights and resumable chunks. Keep the two repositories beside each other:

```powershell
git clone https://github.com/stancsz/local-inference.git
git clone https://github.com/stancsz/sift.git
cd sift
git checkout e62ed81d8fbf07b076a2cf5c8a9f94f61f509105
cd ../local-inference
python scripts/setup_env.py
python scripts/download_ranges.py
pwsh -NoProfile -File scripts/stage_models.ps1
docker compose up -d --build
curl.exe http://127.0.0.1:8090/health/readiness
```

The model downloader pins the Hugging Face revision in its receipt, verifies each range, then checks SHA-256 against the repository's LFS metadata. Partial chunks remain under ignored `tmp/chunks` for resumption. Model files stay ignored. Stage verified weights into the persistent Linux `local-inference-models` Docker volume to avoid Windows bind-mount loading overhead. The runtime image is pinned by digest in Compose.

## Working profiles

The recommended default is one slot, 40,960 total context tokens, a 32,768-token Sift anchor, up to 4,096 output tokens, four draft tokens, q4 target/draft KV, and full GPU target/MTP layers. Sift uses the backend's native full-request tokenizer, including tool/system/template overhead, for selection and final validation. The host was reduced from roughly 4 GB to roughly 1.5 GB desktop occupancy before this experiment. This profile leaves more desktop VRAM headroom than the optional 64k-input profile.

For the tested 64k-input capacity profile, set `CONTEXT_SIZE=69888`, `SIFT_TARGET=65536`, and `DRAFT_TOKENS=2` in `.env`, then recreate both services. The extra 256 context tokens accommodate speculative decoder headroom: 69,632 total tokens stopped two generated tokens short in the initial test. The corrected profile processed exactly 65,536 input tokens and generated all 4,096 tokens without truncation. This synthetic backend capacity test is separate from real task quality. Its observed runtime delta including caches/buffers was slightly above 14 decimal GB, although it fits this freed 16 GB host. Prefer the default for a stricter memory budget.

After enabling that optional profile, reproduce capacity with `python scripts/capacity_acceptance.py`; it refuses to run the 64k test against the smaller daily profile. Stop inference before restaging weights into the Docker volume.

Sift chooses its budget per request. Requests within the configured `SIFT_TARGET` anchor pass unchanged when they also fit the loaded window. Larger histories use `ceil(native_raw_tokens / 8)`, bounded to 24,576–65,536 and to `CONTEXT_SIZE - requested_output - 256`. At the daily defaults with all 4,096 output tokens reserved, the adaptive range is **24,576–36,608**. The larger profile can reach **65,536**. The ratio is a deterministic size-based policy, not an estimate of task difficulty or a guarantee of retention. System, tools and template overhead count toward the native input budget. Mandatory content that cannot fit fails closed. Total context must be at least 28,928; context shifting is disabled so overflow cannot silently discard source history.

Tune `GPU_LAYERS`, `DRAFT_GPU_LAYERS`, `DRAFT_TOKENS`, `UBATCH_SIZE`, and `SPEC_TYPE` via `.env`. Use `SPEC_TYPE=none` for the no-MTP baseline; the launcher omits the MTP model entirely in that mode. Recreate the inference container between comparisons. Four draft tokens measured about 103 tokens/s versus 92 for two on the short 40k-profile microbenchmark. The paired 64k-window benchmark measured 91 with MTP versus 50 without it (two samples per arm). These are decode rates, not end-to-end task throughput or exhaustive hardware optimization.

## Reproducible acceptance

```powershell
pwsh -NoProfile -File scripts/host_vram.ps1
python scripts/claude_local.py
python scripts/runtime_receipt.py
python scripts/benchmark.py --label mtp
python scripts/claude_acceptance.py
$env:PYTHONPATH = '../sift/src'
python scripts/context_acceptance.py
docker compose logs --no-color gateway > tmp/sift-runtime.log
docker compose logs --no-color inference > tmp/inference-runtime.log
docker compose down
```

Use `python scripts/claude_local.py` for normal interactive work, or append CLI flags such as `-p "your task"`. The wrapper isolates local configuration and credentials and preserves the invoking working directory. Tests use temporary isolated configuration and process-local environment variables; they do not modify the user's saved model or API configuration. Outputs, native event streams, and stderr are under `tmp/acceptance`; the durable summary is `evidence/claude-acceptance.json`. Accepted files and the source snapshots actually read are published under `evidence/tasks`, with SHA256s and successful native-edit reconstruction. This installed Claude CLI exposes a unified `Edit` tool. The parent inspects report quality separately; validators do not promise universal semantic grading.

The adaptive context test established 257,539 and 1,001,638 native raw input tokens. It chose different budgets of 32,193 and 40,576 and forwarded 32,053 and 33,300 tokens, respectively, with the required evidence retained and answered correctly. These probes requested 128 output tokens; reserving all 4,096 lowers the daily ceiling to 36,608. Live gateway audits are correlated by SHA-256 and matched against independent compaction counts and provider usage. This is a synthetic retention probe, separate from the three real CLI productivity tasks; it does not prove general semantic equivalence. A mandatory latest request too large to fit fails closed. The raw ceiling is 1,050,000 native tokens; Sift retains its pre-count character/node bounds.

## Host VRAM

Run `scripts/host_vram.ps1` to inventory total GPU usage and WDDM per-process allocations. The initial host baseline was about 4 GB; DWM was its largest identified consumer. WDDM allocations may overlap, so do not sum them as physical GPU usage. Save work before closing unused GPU-accelerated apps. Reducing active display resolution/count or browser acceleration may free memory; do not terminate the desktop compositor. CPU weight offload avoids application disruption but can reduce throughput.

Report model/MTP weights, KV cache, compute buffers and total host occupancy separately. GGUF file sizes are not GPU allocation measurements. The requested inference memory ceiling is 14 GB; the host's 16 GB also serves the desktop.

The supported local profile disables thinking. OpenAI `max_completion_tokens` is intentionally normalized to this backend's `max_tokens` output limit; this is verified by an exact 16-token/length-stop receipt. This gateway does not claim generic reasoning-token accounting across arbitrary providers. Compaction audit digests identify the Sift count/selection inputs, not full provider requests or generation outputs.

## Sources

- [Qwen3.8 guide and sampling settings](https://unsloth.ai/docs/models/qwen3.8)
- [GGUF weights and MTP artifacts](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/tree/main)
- [MTP guide](https://unsloth.ai/docs/models/mtp)
- [llama.cpp native Messages and token-count endpoints](https://github.com/ggml-org/llama.cpp/tree/master/tools/server)
- [Sift request-adaptive budgets](https://github.com/stancsz/sift/pull/58)
