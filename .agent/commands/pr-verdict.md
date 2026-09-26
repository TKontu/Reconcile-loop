# pr-verdict

Follow [the shared contract](common.md).

Input: PR identifier, optional request to publish the verdict.

1. Pin base and head; load changed paths, assignment scope and canonical references. Existing verdicts
   only apply to their recorded head. Reuse one only when its scope/evidence remain current.
2. Choose lenses by risk: claims and conformance for instruction/docs changes; add correctness and
   scope for behavior changes; add production-path/scale scrutiny for data, identity, migrations,
   security, concurrency or other locally identified risky seams.
3. Apply [review-lens](review-lens.md). Use independent agents only if available and authorized;
   otherwise do explicit sequential passes and disclose that they were not independent. Do not claim
   consensus from a single review. A fresh lens gets pinned artifacts, not a desired conclusion.
4. Verify each material finding in source or by a safe reproduction; seek counterevidence before
   retaining interpretive concerns. Label confirmed versus plausible; dismiss refuted findings with
   rationale in the review record. Assign severity separately from certainty.
5. Return head SHA, chosen lenses, held/refuted claims, located findings, verification gaps and
   recommendation: ready, fix-first, or escalate. This recommendation does not authorize merge.

Default output is local/chat. Only publish a PR comment when explicitly requested or already authorized
by the project workflow. Include a head-specific marker such as `reconcile-verdict:<head-sha>` and
avoid duplicating an unchanged verdict. A stale comment is not evidence for a new head.
