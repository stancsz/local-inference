# Local inference

Keep the runtime independent of Subroute: only the local LiteLLM gateway and llama.cpp inference containers. Sift is a CPU callback inside the gateway. No cloud fallback, shared routing database, or global client configuration changes.

Use `GOAL.md` for Ask / Acceptance / Remaining. Preserve unrelated host-VRAM scripts and receipts. Stage explicit task-owned paths.

Verify changes with budget tests, `scripts/local_smoke.py`, `scripts/openai_smoke.py`, `scripts/claude_acceptance.py`, and the context/capacity harness relevant to the changed profile. Separate synthetic capacity, compaction retention, decode benchmarks and real Claude task evidence. Report memory in explicit units and distinguish host delta from per-allocation measurements.
