# plan-round

Read project AGENTS.md and `.agent/config.toml`; follow [the protocol](../../SPEC.md).

Input: maximum assignment count, default one, or named ready items.

Read each selected item's entire detail and necessary architecture sections. Use only executable,
unclaimed work with satisfied dependencies. Check shared files, interfaces and mutable resources;
plan fewer assignments if they cannot safely overlap. This selection is a planner decision.

Refresh a clean default branch with fetch and fast-forward only, then create the round:

```sh
python3 scripts/round.py init ROUND --base main
```

Substitute the configured default branch. The CLI resolves the full commit and refuses a prior open
round. It does not fetch, choose tasks, or detect all ownership/resource conflicts for you.

Write each spec using [the assignment template](../../templates/assignment.md), then:

```sh
python3 scripts/round.py assign ROUND A1 --item TASK-1 --branch task/short-name --spec /path/to/spec.md
```

The generated packet includes identity/base and is bound by one stored SHA-256. Inspect its scope,
resource access and complete acceptance. Provision required ignored artifacts securely. The packet
must work in an isolated checkout without the planner's local files. Deliver the packet unchanged,
with its digest, to an authorized executor or provide it for manual delivery.

Planning stops at packets and the assignment table; execution starts only when authorized. Do not
change a packet after delivery. Cancel and reassign if its scope/base must change.
