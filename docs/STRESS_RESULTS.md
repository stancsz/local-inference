# Local CLI stress results

Frozen original matrix checkpoint: 2026-10-27T05:47:46.651886+00:00. Its controller is terminal. Current prospective-batch state is in [balanced-v2-state](../evidence/balanced-v2-state.json); final independent acceptance remains **NOT_READY**.

19 harness passes and 3 failed attempts among 22 terminal matrix attempts; 19 reached nine turns and over 180 active seconds. At this original-matrix checkpoint, the21-session shortfall was **2**; see the separate later epochs below for current candidate totals. The fixed plan has 22 attempts; failed one-turn attempts and older epochs are not promoted into current passes.

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

Independent review scopes: {"full_goal": "NOT_READY", "report_and_publication": "READY", "unattended_production": "NOT_READY"}. [Preserved verdict](../evidence/stress-independent-review.json), [review provenance and limits](../evidence/stress-independent-review-provenance.json), and [parent factual clarifications](../evidence/stress-independent-review-parent-response.json). The review execution phase reached its tool limit; a text-only nonauthor handoff assessed its captured observations and actual raw excerpts. No full-goal completion or unattended-production acceptance follows.


Prospective supplement v1 (separate workload epoch): OpenCode incident-log analysis passed nine turns/1014.592 active seconds; Codex release-manifest auditing was rejected after seven turns/850.846 seconds, including a240-second terminal timeout. Parent replay yields a candidate aggregate of20/21 (Claude7/OpenCode7/Codex6), pending final nonauthor acceptance. The original19/22 matrix and12/19 posthoc quality failures above remain frozen. See [parent review](../evidence/supplement-v1-parent-review.json).

The rejected Codex case also produced12 archived-source retention audit failures. Its stored historical value was correct; forwarded excerpts were not captured, so actual compaction loss versus checker mismatch is unresolved. Separate Windows fixture diagnostics passed the unchanged tests with workspace-inherited temporary directories while outside-workspace writes stayed denied. Neither diagnostic promotes the failed attempt.

Expense feedback v3 is a separate short generated repair, not a qualifying session: one native Claude turn against local Qwen :8090 repaired blank-currency handling and empty-CSV ValueError behavior. Parent replay reproduced0/6 baseline probe passes and6/6 final passes, alongside13 regressions,9 original behavior stages and12 existing probes. Raw revisions/native events and byte hashes are [published](../evidence/expense-feedback-v3.json); [parent acceptance](../evidence/expense-feedback-v3-parent-review.json) is separate from final full-goal acceptance. The supporting4000/default writer reached its18-turn cap; parent completed acceptance and publication guards. Original failures were not rewritten.


Balanced v2 remains in progress: Claude incident-log and OpenCode manifest cases each passed9 turns with parent replay (993.867s/988.9s). Codex expense auditing was rejected after240.312s: real grouping failure and a native patch-path error, with the fixture preflight passing and all11 original-source captures retained. Candidate aggregate22 = original19 + prior supplement1 + balanced2; clientsClaude8/OpenCode8/Codex6. All9 declared cases must finish and full-goal nonauthor acceptance is pending.

A parent diagnostic also found that frozen native success recognition hardcodes `Ran 2 tests`, whereas the new portable expense fixtures run3/4 tests. Successful three/four-test output can be falsely rejected. This does not affect the original two-test matrix comparison, and the failed Codex expense output independently fails semantic tests. Preserve all outcomes, qualify this confound in future expense results and use a separately versioned harness for any correction; do not retrofit passing counts. See [offline controls](../evidence/balanced-v2-native-test-count-diagnostic.json) and [failed-case review](../evidence/balanced-v2-case3-failure-review.json).


Case4 of balanced v2 exposes a confirmed first-stage historical-source omission: all9 Claude manifest task turns and independent new-seed behavior checks pass, but requests42..46 omit the approved historical fact from their captured excerpts. All47 HTTP requests return200 and native context limits hold. The setting remains correct in the saved artifact; no downstream task damage or full provider-wire absence is inferred. The session remains rejected and the candidate aggregate stays22. See [retention failure](../evidence/balanced-v2-case4-retention-failure.json); raw native traces, generated artifact, public/hidden-test receipts and all47 excerpt captures are preserved under evidence/balanced-v2-progress/case4-retention-rejected. This is separate from the earlier Codex warning whose actual excerpts were unavailable. All9 cases and final independent full-goal acceptance remain unfinished.
