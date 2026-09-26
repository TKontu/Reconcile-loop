# debug

Follow [the shared contract](common.md).

Input: observed error, failing check or unexpected behavior.

Read the full relevant diagnostic and trace its data/control path in source. Reproduce with the
smallest safe case and inspect recent changes and a comparable working path. Distinguish setup faults
from product defects. State a falsifiable hypothesis and run a focused check; avoid stacking guesses.

Once the cause is supported, use [tdd](tdd.md) for an executable regression case and the smallest
in-scope fix. Rerun affected checks and record remaining uncertainty. Preserve diagnostics without
exposing secrets. If evidence points to a target/scope conflict, return it to planning; repeated failed
hypotheses call for revisiting the model, not arbitrary rewrites or unbounded retries.
