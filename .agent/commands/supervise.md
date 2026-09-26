# supervise

Follow [the shared contract](common.md).

Input: monitor or drive mode, adapter/configuration, scope, limits and recovery owner.

Read [supervision](../../docs/supervision.md) and the completed project supervisor contract. Without an
implemented adapter, report the missing interfaces and offer the manual one-round path through
[orchestrate](orchestrate.md); do not invent an unattended shell loop or claim one was installed.

For monitor mode, inspect structured runner/round/check state and report only. For authorized drive
mode, verify fresh session identities per round, safe resume within a round, explicit dispatch mapping,
resource enforcement, merge policy, time/turn/cost/round limits and halt persistence before launch.

Observe phase exit status, semantic errors and required artifacts together. Detect unknown APIs,
partial dispatch, worker timeouts, missing/closed-unmerged PRs, invalid handoff and no-progress limits.
Halt with durable reason and active-worker/resource inventory rather than blindly retrying. Queue
reserved decisions while independent work remains executable. Notify only authorized destinations.

Do not override engineering judgment or approval gates. At cancellation stop new launches, inspect
surviving workers and record recovery state. A fresh planner session must reconstruct state from
records, not reuse the previous round's conversational context.
