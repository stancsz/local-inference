# Local inference with mandatory Sift compaction

An independent, minimal LiteLLM gateway serving Dockerized Qwen3.8-27B IQ3_XXS + Q4 MTP on a Windows RTX 5070 Ti (16 GB). Claude Code uses LiteLLM at `http://127.0.0.1:8090`; mandatory Sift runs in its pre-call callback. llama.cpp runs on `8091` for diagnostics. Neither endpoint is exposed beyond loopback. There is no Subroute runtime dependency, cloud fallback, database, Redis, or separate compaction service.

**Status: live text/tool continuation, three Claude productivity tasks, 256k/1M compaction and exact 64k+4k capacity have runtime receipts.** Final validation of the recommended profile is ongoing. See [GOAL.md](GOAL.md) for the acceptance contract and [evidence](evidence) for actual receipts. These bounded tests do not establish general task quality or information-retention parity.

## Setup

Requirements: Docker Desktop with Linux GPU support, NVIDIA driver, Python 3.11+, PowerShell, Claude Code CLI, and approximately 40 GB free disk for weights plus resumable chunks. Keep the two repositories beside each other:

```powershell
git clone https://github.com/stancsz/local-inference.git
git clone https://github.com/stancsz/sift.git
cd sift
git pull --ff-only
cd ../local-inference
python scripts/setup_env.py
python scripts/download_ranges.py
pwsh -NoProfile -File scripts/stage_models.ps1
docker compose up -d --build
curl.exe http://127.0.0.1:8090/health/readiness
```

The model downloader pins the Hugging Face revision in its receipt, verifies each range, then checks SHA-256 against the repository's LFS metadata. Partial chunks remain under ignored `tmp/chunks` for resumption. Model files stay ignored. Stage verified weights into the persistent Linux `local-inference-models` Docker volume to avoid Windows bind-mount loading overhead. The runtime image is pinned by digest in Compose.

## Working profiles

The recommended default is one slot, 40,960 total context tokens, a 32,768-token Sift budget, up to 4,096 output tokens, four draft tokens, q4 target/draft KV, and full GPU target/MTP layers. Sift uses the backend's native full-request tokenizer, including tool/system/template overhead, for selection and final validation. The host was reduced from roughly 4 GB to roughly 1.5 GB desktop occupancy before this experiment. This profile leaves more desktop VRAM headroom than the optional 64k-input profile.

For the tested 64k-input capacity profile, set `CONTEXT_SIZE=69888`, `SIFT_TARGET=65536`, and `DRAFT_TOKENS=2` in `.env`, then recreate both services. The extra 256 context tokens accommodate speculative decoder headroom: 69,632 total tokens stopped two generated tokens short in the initial test. The corrected profile processed exactly 65,536 input tokens and generated all 4,096 tokens without truncation. This synthetic backend capacity test is separate from real task quality. Its observed runtime delta including caches/buffers was slightly above 14 decimal GB, although it fits this freed 16 GB host. Prefer the default for a stricter memory budget.

The default 32k Sift budget keeps prefill and retrieval costs lower. System, tools and template overhead count toward the native input budget. Sift also reserves 256 decoder headroom tokens beyond the requested output. Supported targets are 24,576–65,536; total context must be at least 28,928. Context shifting is disabled so overflow cannot silently discard source history.

Tune `GPU_LAYERS`, `DRAFT_GPU_LAYERS`, `DRAFT_TOKENS`, `UBATCH_SIZE`, and `SPEC_TYPE` via `.env`. Use `SPEC_TYPE=none` for the no-MTP baseline; the launcher omits the MTP model entirely in that mode. Recreate the inference container between comparisons. Four draft tokens measured about 103 tokens/s versus 92 for two on the short 40k-profile microbenchmark. The paired 64k-window benchmark measured 91 with MTP versus 50 without it (two samples per arm). These are decode rates, not end-to-end task throughput or exhaustive hardware optimization.

## Reproducible acceptance

```powershell
pwsh -NoProfile -File scripts/host_vram.ps1
python scripts/claude_local.py
python scripts/benchmark.py --label mtp
python scripts/claude_acceptance.py
$env:PYTHONPATH = '../sift/src'
python scripts/context_acceptance.py
docker compose logs --no-color gateway > tmp/sift-runtime.log
docker compose logs --no-color inference > tmp/inference-runtime.log
docker compose down
```

Use `python scripts/claude_local.py` for normal interactive work, or append CLI flags such as `-p "your task"`. The wrapper isolates local configuration and credentials and preserves the invoking working directory. Tests use temporary isolated configuration and process-local environment variables; they do not modify the user's saved model or API configuration. Outputs, native event streams, and stderr are under `tmp/acceptance`; the durable summary is `evidence/claude-acceptance.json`. This installed Claude CLI exposes a unified `Edit` tool: acceptance requires native reads and edits to pending artifacts, successful terminal results, expected artifacts and exact byte arithmetic. The parent inspects report quality separately.

The context test established 257,539 and 1,001,638 native raw input tokens, reduced to 32,689 and 32,648 native forwarded tokens, with the required evidence retained and answered correctly. Selection took about 1.2 and 2.6 seconds in the initial runtime receipts. Live gateway audits are correlated by SHA-256 and matched against independent compaction counts and provider usage. This is a synthetic retention probe, separate from the three real CLI productivity tasks; it does not prove general semantic equivalence. A mandatory latest request too large to fit fails closed. The raw ceiling is 1,050,000 native tokens; Sift retains its pre-count character/node bounds.

## Host VRAM

Run `scripts/host_vram.ps1` to inventory total GPU usage and WDDM per-process allocations. The initial host baseline was about 4 GB; DWM was its largest identified consumer. WDDM allocations may overlap, so do not sum them as physical GPU usage. Save work before closing unused GPU-accelerated apps. Reducing active display resolution/count or browser acceleration may free memory; do not terminate the desktop compositor. CPU weight offload avoids application disruption but can reduce throughput.

Report model/MTP weights, KV cache, compute buffers and total host occupancy separately. GGUF file sizes are not GPU allocation measurements. The requested inference memory ceiling is 14 GB; the host's 16 GB also serves the desktop.

## Sources

- [Qwen3.8 guide and sampling settings](https://unsloth.ai/docs/models/qwen3.8)
- [GGUF weights and MTP artifacts](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/tree/main)
- [MTP guide](https://unsloth.ai/docs/models/mtp)
- [llama.cpp native Messages and token-count endpoints](https://github.com/ggml-org/llama.cpp/tree/master/tools/server)
- [Sift dynamic API](https://github.com/stancsz/sift/pull/57)
