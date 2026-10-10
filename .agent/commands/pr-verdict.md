# pr-verdict

Read project AGENTS.md and `.agent/config.toml`; follow [the protocol](../../SPEC.md).

Input: PR identifier, optional request to publish the verdict. Optional helper for review-round;
advisory only. Never merge, push fixes or treat the recommendation as merge authority.

1. Pin the PR's base and head SHAs. Reuse an existing verdict only when its recorded head equals the
   current head. For a changed head, review the delta from the previously reviewed SHA plus affected
   seams, at the tier the delta warrants; record which prior evidence still applies and which checks
   must rerun. If the prior review or its head cannot be verified, review the full candidate.
2. Gather without judging: changed paths, the owning assignment/item and the canonical references it
   cites. Do not read the PR body yet; only the claims lens receives it.
3. Choose lenses by risk and state why. Documentation, instructions and CI only: claims and
   conformance. Other behavior changes: add correctness and scope. Data, identity, migrations,
   persisted shapes, security, concurrency or configurable pipeline paths: all five. When unsure,
   take the larger set.
4. Run each lens with only pinned artifacts: PR, base/head, changed paths and reference paths. Never
   include the desired outcome, author rationale or another lens's brief. Use independent
   fresh-context agents when available and authorized; otherwise run explicit sequential passes and
   disclose that they were not independent.
   - **claims**: extract each factual PR-body claim (behavior, callers, coverage, checks run);
     verify each at source or by running the named command; return held/refuted with evidence.
   - **conformance**: compare rule, gate or decision text restated in the diff with its canonical
     original; drift in either direction is a finding. Run the project's record validators if any.
   - **correctness**: concrete defects with `file:line` and a failure scenario. For moves, compare
     relocated bodies token by token.
   - **scope**: compare actual edits with the assignment's boundaries and approved decisions.
   - **production path**: trace entry points, defaults and producer/consumer seams; check that cited
     tests exercise the production configuration rather than a test-only branch.
5. Verify findings. One reported by two lenses, or reproduced by you at source, is confirmed. Give
   other medium-or-higher findings a fresh refutation attempt at source; drop refuted ones. Label
   confirmed or plausible before assigning severity.
6. Return head SHA, lenses and why, the claims table, located findings (certainty, severity, one line
   each), verification gaps and a recommendation: ready, fix-first or escalate. Report counts so
   reconcile can record review calibration.

Default output is local. Publish a PR comment only when requested or already authorized by project
policy. Re-fetch the head first; if it moved, review that delta before publishing. Keep one comment
starting `<!-- pr-verdict -->` then `Reviewed-SHA: FULL_SHA`, editing it rather than adding another.
A verdict for an older head is not evidence for a new one.
