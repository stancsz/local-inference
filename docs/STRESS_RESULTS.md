# Local CLI stress results

Checkpoint: 2026-10-27T05:28:20.852476+00:00. Controller: **attention_required**. Final independent acceptance: **pending**.

19 harness passes and 3 failed attempts among 22 terminal matrix attempts; 19 reached nine turns and over 180 active seconds. The required 21-session target remains unmet: shortfall **2**. The fixed plan has 22 attempts; failed one-turn attempts and older epochs are not promoted into current passes.

| Client | Terminal attempts | Harness passes | Nine-turn long sessions | Median accepted active seconds | Added contract failures |
| --- | ---: | ---: | ---: | ---: | ---: |
| claude | 7 | 7 | 7 | 980.493 | 4 |
| opencode | 8 | 6 | 6 | 1060.481 | 5 |
| codex | 7 | 6 | 6 | 819.683 | 3 |

Accepted session active seconds: minimum 766.871, median 967.795, maximum 1086.017; total 18247.656. These are long-context task durations, not the short-prompt decode benchmark.

All three rejected expense attempts remain one-turn failures. Two repeatedly wrote code still failing category grouping. The final OpenCode sample (repeat 2, seed 2951) passed public/hidden tests and retained history, but reached 240 seconds before a successful CLI terminal event. It remains rejected. No outcome-based re-roll or timeout extension is allowed.

The nine-turn harness checks native tool workflows, hidden tests, historical-fact retention and session continuity. Selected additional contract probes expose narrower validation defects in generated artifacts despite workflow passes. See [per-artifact probes](../evidence/stress-contract-probes.json) and [complete outcome summary](../evidence/stress-summary.json).

| Task | Terminal attempts | Workflow passes | Added contract failures |
| --- | ---: | ---: | ---: |
| engineering | 9 | 9 | 5 |
| migration | 6 | 6 | 3 |
| expenses | 7 | 4 | 4 |

Final native context checks: 880 requests, windows [40960], output reserve up to 4096 and a 256-token decoder guard. Native input range 24183 to 32716. Source-matched accepted traces and published fixture bytes are reconciled in [publication review](../evidence/stress-published-fixture-review.json).

Memory: 4139 available host-GPU samples, 15179 to 15638 MiB used and 358 to 817 MiB free. Largest observed sampling gap: 918.582 seconds. This is whole-host occupancy with gaps and desktop drift; isolated model+MTP under 14 GB is unproven. [Hashed raw samples](../evidence/stress-gpu-samples-manifest.json).

Separate evidence: [256k/1M synthetic context checks](../evidence/context-acceptance.json), [short decode/MTP benchmarks](../evidence/benchmark-summary.json), and [rejected attempt archive](../evidence/stress-rejected.json). These do not establish arbitrary semantic retention, task-level decode speed, or simultaneous 64k input under 14 GB.

- Three synthetic task families use real native CLIs, persisted sessions, local Qwen and filesystem edits; this is not a production repository trial.
- Harness acceptance and selected posthoc contract probes are separate. Extra edge cases are not exhaustive or preregistered; no universal quality percentage follows.
- Historical and setup receipts remain listed separately and are excluded from the current matrix denominator.
- Active seconds measure client execution without idle padding. They are not decode tokens/second.
- No paired no-Sift ablation establishes whether compaction caused any task defect.
