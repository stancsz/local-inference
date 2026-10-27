# Local CLI stress results

Checkpoint: 2026-10-27T04:43:19.767579+00:00. Controller: **running**. Final independent acceptance: **pending**.

17 harness passes and 2 failed attempts among 19 terminal matrix attempts; 17 reached nine turns and over 180 active seconds. There are 22 planned attempts. Two short failures mean this plan can yield at most 20 corrected-epoch nine-turn sessions; the target of 21 remains unmet.

| Client | Terminal attempts | Harness passes | Nine-turn long sessions | Median accepted active seconds | Added contract failures |
| --- | ---: | ---: | ---: | ---: | ---: |
| claude | 7 | 7 | 7 | 980.493 | 4 |
| opencode | 6 | 5 | 5 | 1060.940 | 4 |
| codex | 6 | 5 | 5 | 849.925 | 3 |

The retained OpenCode expense timeout remains a failed one-turn attempt. The fixed extra sample uses repeat2/seed2951; no outcome-based re-roll or timeout extension is allowed.

The nine-turn harness checks native tool workflows, hidden tests, historical-fact retention and session continuity. Selected additional contract probes expose narrower validation defects in generated artifacts despite workflow passes. See [per-artifact probes](../evidence/stress-contract-probes.json) and [complete outcome summary](../evidence/stress-summary.json).

- Three synthetic task families use real native CLIs, persisted sessions, local Qwen and filesystem edits; this is not a production repository trial.
- Harness acceptance and selected posthoc contract probes are separate. Extra edge cases are not exhaustive or preregistered; no universal quality percentage follows.
- Historical and setup receipts remain listed separately and are excluded from the current matrix denominator.
- Active seconds measure client execution without idle padding. They are not decode tokens/second.
- No paired no-Sift ablation establishes whether compaction caused any task defect.
