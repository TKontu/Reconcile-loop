# Project workflow profile

Use this checklist to write the policy file referenced by `.agent/config.toml`. Keep path and command
routing in that config; link it here instead of duplicating values. Paths are relative to the adopting repository
unless explicitly stated. Replace every required placeholder; use N/A with a reason for absent tiers.
Do not store secrets or duplicate architecture/backlog content here.

## Authority and paths
- Project README: <actual filename and orientation sections>
- Approved architecture: <path and approval authority>
- Sole status/dependency registry: <path and allowed status semantics>
- Item details: <path convention and acceptance ownership>
- Canonical decisions and pending questions: <locations and serialized-write owner>
- Evidence / reconciliation ledger: <locations>
- Standing decision policy: <path, revision and approver>
- Handoff: <ignored path; default HANDOFF.md>

## Git and ownership
- Default branch / remote: <names>
- Planner workspace / isolated executor convention: <locations or creation rule>
- Local round records: <default .agent-runs/; compatible custom tooling if present>
- Planner / executor / reviewer / merge authority: <roles and boundaries>
- Independent review and merge method: <policy>
- Publication authorization: <who may commit, push, create PRs or post comments and within what scope>

## Verification
| Tier | Exact command or check | Environment / resource | Owner and when required | Skip policy |
| --- | --- | --- | --- | --- |
| Targeted tests | <command syntax> | <environment> | <owner> | <policy> |
| Lint / format / types / build | <configured checks or N/A> | <environment> | <owner> | <policy> |
| Broad local gate | <command> | <environment> | <before PR> | <policy> |
| Integration / live | <commands or N/A> | <safe target and guard> | <owner> | <policy> |
| Merge-ready CI | <required checks and triggering procedure> | <exact head> | <owner> | <policy> |
| Combined-state gate | <command/check or explicit N/A> | <final main> | <planner> | <policy> |
| Docs / metadata / secrets | <tools or documented inspection procedure> | <diff scope> | <owner> | <policy> |

## Resources and operations
- Disposable vs persistent resources / runbook: <names, target guards, reset policy or N/A>
- Exclusive reservation/enforcement: <mechanism and release owner or N/A>
- Required ignored artifact/configuration provisioning: <secure delivery convention or none>
- Representative scale and connection-proof policy: <references>
- Runner / manual delivery: <available interfaces; do not assume a CLI exists>
- Supervisor configuration: <path to completed contract, or manual-only>
- Time/round/cost limits and recovery owner: <values or manual phase limits>

## Bootstrap result
<Ready for manual first round, or exact unresolved required settings. Automation readiness is separate.>
