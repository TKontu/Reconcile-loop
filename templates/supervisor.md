# Supervisor adoption contract

This is configuration design, not an executable configuration file.

- Repository / default branch: <location and branch>
- Workflow / decision policy: <paths and policy revision>
- Runner adapter: <start-new-session, resume, status, dispatch, wait, cancel interfaces>
- Assignment-to-runner mapping: <explicit identities and isolated workspaces>
- Round artifacts and logs: <locations, access, retention, structured schema>
- Limits: <phase timeout, executor timeout, turn/cost budget, max rounds, no-progress limit>
- Exclusive resources: <identities, enforcement/locking and release procedure>
- Dispatch authorization: <scope and owner>
- Merge authorization: <policy; automation mode does not grant it>
- Required phase artifacts: <manifest, acknowledged packets, PR evidence, reviews, merged SHAs>
- Final combined-state checks: <commands/checks and required exact revision>
- Handoff validation: <schema, size, timestamp, SHA and link checks>
- Halt location and schema: <time, phase, reason, active workers, logs, recovery action>
- Recovery owner: <who checks state and authorizes safe resume>
- Cancellation behavior: <stop dispatch, inspect/stop workers, verify resource release>
- Decision queue: <durable location and serialized update mechanism>
- Notifications: <authorized destination or disabled>

Before unattended use, demonstrate a single supervised round and exercise timeout, partial dispatch,
API failure, closed-unmerged PR, active worker after interruption, and invalid-handoff cases. Verify
none can be mistaken for a successful completed round. This library supplies no tested adapter.
