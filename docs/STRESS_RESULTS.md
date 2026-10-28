# Local CLI stress results

## Current repaired-source checkpoint

The separately sealed shared-MTP Codex incident-log session passed all nine native turns in 843.730 active seconds. Parent replay verified 18 immutable snapshots, 54 public/hidden/additional-parent behavior checks, the same native session, zero native errors and 42 exact original-source excerpt captures. All 42 recorded gateway requests returned 200 and their 24,339–24,576 native input tokens plus output reserve/headroom fit the 40,960-token window. Native sandbox and portable-fixture preflights verified outside-workspace write denial. The original inputs, seeds, 240-second turn deadlines and all historical failures remain unchanged.

Parent-qualified candidate totals are now **24: Claude 8 / OpenCode 9 / Codex 7**, across separately identified source/workload epochs: original 19 + prior supplement 1 + balanced 3 + repaired-source Codex 1. The seven-per-client gate is reached. The original 12/19 added contract failures remain historical failures; no old artifact or rejected session is promoted. These counts are bounded workflow/retention qualifications, not a claim of universal generated-code correctness.

See the [sealed plan](../evidence/codex-shared-mtp-v1-plan.json), [parent replay](../evidence/codex-shared-mtp-v1-parent-review.json) and [complete publication](../evidence/codex-shared-mtp-v1-publication.json). Exact captures concern first-stage historical excerpts, not the full downstream wire payload. Separate 256k/1M native-count/provider-answer tests establish their own bounded retention results. The Windows capture proxy emitted a connection-close callback traceback; it is preserved, with no corresponding recorded failed HTTP response or native error. The [final nonauthor full-goal review](../evidence/final-daily-driver-acceptance-v1.json) is **READY** within these explicit bounds; the historical verdicts below are unchanged.

## Historical matrices and reviews


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


Balanced case5 OpenCode expenses is also genuinely rejected: one240.362s turn, failing category grouping, and no successful terminal CLI completion. Parent reproduces the defect on the saved output; all10 historical-source captures retain the approved setting. This remains separate from the recognizer's potential false-negative issue. See [failed-case review](../evidence/balanced-v2-case5-failure-review.json). Candidate aggregate22 remains provisional; cases6..9 and full independent acceptance are still pending.


Balanced case6 confirms the same first-stage source omission through Codex Responses:9 accepted task turns/805.99s, all9 parent-seed/native/public checks passing,43 HTTP200 requests and valid native bounds, but requests41..42 omit the required historical fact from their captured excerpts. Live file-stage tests and the portable fixture preflight pass. The case remains rejected and no setting/output damage is inferred. See [case6 evidence](../evidence/balanced-v2-case6-retention-failure.json). Candidate aggregate remains22, with Codex6; the per-client gate and final independent full-goal verdict remain unmet. Cases7..9 are still pending.


Balanced case7 Claude expenses differs from cases3/5: its first-stage artifact passes hidden and new-seed parent checks, but the native CLI times out at240.257s without a successful terminal event after one turn. Actual native three-test success is visible in the raw tool output but not recognized by the frozen two-test matcher. Both the independent deadline/multi-turn failure and the grading defect remain explicit; no count is promoted and full expense-contract correctness was not tested. All12 original-source captures retain the fact. See [case7 review](../evidence/balanced-v2-case7-failure-review.json). Candidate22 and the Codex per-client shortfall remain; the final2 declared cases are pending.


Balanced v2 terminal parent review (2026-10-27): all nine sealed cases finished without restarts, replacements or deadline changes. Three qualify: Claude incident-log, OpenCode release-manifest and OpenCode incident-log. Six remain rejected. The final Codex manifest case reached nine turns/1075.401 active seconds but its last turn timed out at240.338 seconds without a successful native terminal event; hidden tests and the saved historical answer passed. Its captured original-source fact is absent in requests32..59, independently of the deadline failure. Earlier Claude manifest and Codex incident cases likewise retain their source-omission rejections. OpenCode expense also has a final audit without a recorded upstream status at its deadline; its forwarded32747 tokens are within the32768-token target. Correct source retention alone does not make it pass. No failed receipt is promoted.

Parent replay reconciles original19 + prior supplement1 + balanced3 =23 candidate qualifying sessions, with Claude8/OpenCode9/Codex6. The aggregate21 threshold is reached, but the required seven per client is UNMET for Codex. Original22 attempts/19 passes and12/19 selected contract failures remain unchanged and separately labeled. All57 native turn streams,310 captured excerpts and310 downstream native context checks are replayed; the final implementations are checked against each completed stage's immutable public seed, hidden seed and an additional parent seed. Raw final artifacts are unchanged by replay. Complete positive and negative evidence is published in518 manifest files, including all failed turns and original excerpt captures. See evidence/balanced-v2-parent-review.json and evidence/balanced-v2-sessions/.

Whole-host memory:1342 samples,15136..15171 MiB used, largest sampling gap5.118166 seconds. This is not isolated model+MTP residency or proof of under14 decimal GB. Native context checks enforce40960 total tokens with4096 output reserve and256 guard. The runtime image remains the sealed sha256:0441d3d28a6cb1411f4e390eb95cb2786e87fb9dab03b7f3cffba60d632e3189. No claim of simultaneous64k input and under14GB is established.

Verification:301 project tests pass with `python -m pytest tests -q`;29 review guards pass. An initial unscoped `pytest -q` collected archived experimental fixtures under tmp and failed collection (170 errors); that command/log is preserved and is not presented as a project-suite pass. Review/publication code is outside the frozen inference source epoch. The two-test native recognizer defect is preserved; it does not waive independent one-turn/deadline or semantic failures. Full-goal acceptance remains NOT_READY pending fresh nonauthor review, Codex coverage and unresolved retention/generated-contract correctness. No campaign inference process remains live.


Fresh nonauthor review of c5415ad is terminal: publication READY, full_goal NOT_READY. The reviewer personally inspected archived native traces, final code, hidden outputs and all310 excerpt captures; independently reconciled23 candidates (Claude8/OpenCode9/Codex6), reran29 review guards and301 project tests, and verified518 published files with zero mismatches. Exact verdict and native provenance are preserved in evidence/balanced-v2-independent-review.json and evidence/balanced-v2-independent-review-provenance.json. The initial24-turn inspection was incomplete; its artifacts remain preserved. A focused fresh read-only review completed with scoped credentials revoked. Its CLI reports45 turns despite configured40; this is explicitly recorded, with no change to any sealed task limit.

Remaining full-goal criteria: Codex seven-per-client coverage, repaired first-stage original-source omission, broad generated-contract correctness and isolated/simultaneous memory-context claims remain unmet or unverified. Parent clarification: final-code replay does not reconstruct intermediate task.py; the frozen runner DID run hidden checks on every recorded turn, and any failure rejects the session. No claim of reconstructed intermediate source follows. The review's suggested exactly-one future Codex run is advice, not a newly sealed campaign or an authorized outcome-selected promotion. Future work needs a separate versioned source/workload plan preserving all failures. All9 sealed cases, terminal parent publication and the fresh nonauthor verdict are now recorded; the batch-monitor heartbeat can pause while the overall goal remains active and NOT_READY.
