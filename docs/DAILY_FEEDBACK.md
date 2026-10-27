# Daily task feedback acceptance

Run the three existing local productivity tasks with bounded native feedback:

```powershell
python scripts/daily_artifacts.py --output-dir tmp/my-daily-check
```

The directory must be new. Each task gets one generation and at most two repairs, with a 240-second deadline per phase. Repairs resume the original Claude session and require complete native source reads before editing. The harness preserves prompts, native events, stderr, revisions, hashes and failures. It never writes a correction itself. Task inference uses local Qwen at `:8090`, with no cloud fallback. The isolated test-client permissions match the existing acceptance harness; normal interactive approval/configuration remains inherited through `scripts/claude_local.py`.

## Observed results

The v2 run used producer commit `2b6eb2e` and took 104.16 seconds end to end:

| Task | Initial generation | Feedback repairs | Final artifact |
| --- | --- | --- | --- |
| VRAM plan | Passed | 0 | Passed source-derived checks |
| Model audit | Passed | 0 | Passed exact arithmetic, revision and basename checks |
| Operator guide | Rejected by wording checker | 1 | Passed; native session continuity verified |

Parent replay reconstructs all nine phases across v1/v2 from successful native Edit events and verifies the archived revision hashes and session identities. Both accepted and rejected outcomes are published in [the artifact archive](../evidence/daily-feedback-v2-artifacts); [parent evidence](../evidence/daily-feedback-v2-parent-review.json) distinguishes original outcomes from later validator replay.

Two harness defects were exposed and repaired:

- v1 feedback referred to source files “named above,” but command-only errors named none. The model corrected its artifact without repeating all required reads, and the harness rejected both affected tasks. Feedback now explicitly lists every required source. The original rejection remains unchanged.
- The wording checker rejected the semantically correct Markdown name `` `sift_target` ``. It now accepts that formatting while still rejecting claims that the target is added to the input budget. The original v2 phase receipt and producer bytes remain unchanged.

v1 has complete native streams and revisions but did not save producer hashes before execution. v2 saves its source/harness plan before inference; its original producer snapshots are archived. Neither experiment increments long-session qualification or replaces frozen failures. These short checks do not establish nine-turn reliability, arbitrary semantic retention, universal model correctness, or simultaneous 64k input/4k output under 14 decimal GB of VRAM. The long-campaign candidate totals remain Claude 8 / OpenCode 9 / Codex 6, and full-goal acceptance remains NOT_READY.

Current verification: 405 project tests, 38 focused feedback/wording checks, local text/tool continuation smoke and OpenAI schema/output-limit smoke pass. Independent review is recorded separately when available; parent publication is not independent acceptance. Windows timeout tree termination is implemented but was not exercised by these successful short live phases.

Fresh legacy-entry-point check: `python scripts/claude_acceptance.py --output-dir tmp/daily-one-shot-v3` produced two passes and one rejected runbook. Parent reconstructed all three native artifacts. The runbook genuinely omitted `--build`; its equivalent adaptive-anchor budget wording also exposed a checker false negative, which is now covered without accepting opposite budget claims. It remains rejected for the missing build flag. See [one-shot evidence](../evidence/daily-feedback-v3-one-shot.json); no rerun or promotion was used.

The original independent attempts remained **UNVERIFIED**. The first attempt hit an artificial two-request cap on its scoped key. Removing that cap allowed partial inspection, but the second attempt exhausted its turn limit after tool/schema and command-scope errors. A focused third attempt returned UNVERIFIED because the supplied brief ambiguously included an extra dot argument outside its exact allowlist. The policy correctly rejected that command. All three failures, native receipts and credential revocations are preserved in [review provenance](../evidence/daily-feedback-v2-independent-attempt.json). This is a review-setup defect, not a reason to broaden caller approvals or waive independent acceptance. No review attempt supplied a READY verdict.

The subsequent [paged nonauthor review](../evidence/daily-review-v5.json) returns **READY for the original daily harness increment only**, with full_goal NOT_READY. Its actual three native Bash inspection pages verified127 archive files, replayed9 native phases, ran37 focused tests and displayed the relevant sources plus all three generated v2 artifacts. Earlier failures and the fourth, truncated-output inspection remain preserved. The verdict retains its limits: checks used the supplied deterministic helper, rather than a separately implemented verifier. A low presentation finding concerned tool-display replacement characters; parent inspection confirms the original generated UTF-8 file contains zero replacement characters and two em dashes.

A later parent regression reproduced a separate Windows transport defect: the harness sent CP1252 prompt bytes instead of UTF-8. `invoke_cli` now explicitly uses UTF-8, with a real child-process regression covering accented and Chinese text (failed before, passed after). This one-line follow-up is covered by the405-test suite and lies outside the preceding nonauthor verdict. Caller approval/configuration is untouched.
