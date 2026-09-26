# tdd

Follow [the shared contract](common.md).

Input: assigned behavior or reproduced bug and its acceptance.

Choose the project's actual test harness and smallest test crossing the relevant behavior boundary.
Run it before changing production code. Confirm RED is the intended missing/broken behavior, not an
import, typo, missing dependency or inaccessible service. Implement the smallest sufficient change;
run the same test to GREEN, then relevant neighboring checks. Refactor only within scope while keeping
those checks green. Record commands, revision/environment and observed outcomes for PR evidence.

Use representative boundary data for producer/consumer contracts and scale-sensitive code. Avoid tests
that merely mirror implementation. Docs-only or similarly low-impact nonbehavior edits use meaningful
structural checks instead; record why RED/GREEN is not applicable. Never fabricate a prior failure.
