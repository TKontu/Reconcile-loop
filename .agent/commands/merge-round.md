# merge-round

Read project AGENTS.md and `.agent/config.toml`; follow [the protocol](../../SPEC.md).

Confirm current head, review, required checks, mergeability and existing merge authorization for
each candidate. Ask only for a missing approval on a concrete reviewed change. Do not infer authority
from a ready verdict. Resolve conflicts deliberately and renew affected checks; never force-push.

Merge serially using the project's approved Git/PR method. Verify each actual merge and refresh the
local default branch between merges. Reassess remaining work if shared assumptions changed. Then:

```sh
python3 scripts/round.py resolve ROUND A1 --outcome merged --head FULL_REVIEWED_HEAD --merge FULL_MERGE_SHA --evidence "PR review and merge references"
```

The CLI checks the result head and supplied check statuses; it does not call the PR host or independently
prove review/merge correctness. That verification belongs to this phase. If work is abandoned, confirm
its worker has stopped and resource access ended, then record cancellation with an explanation:

```sh
python3 scripts/round.py resolve ROUND A1 --outcome cancelled --evidence "Stopped; remaining work recorded in TASK-1"
```

Do not start another round yet. All merged and cancelled outcomes still require reconciliation.
