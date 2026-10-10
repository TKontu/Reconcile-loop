# Task spec

- Item and complete detail: <canonical references>
- Architecture sections / approved decisions: <references>
- Objective: <one observable outcome>
- In scope / non-goals: <boundaries>
- Expected files and editable records: <ownership; name shared seams>
- Resources / artifacts: <permitted services, exclusive ownership, provisioned data or none>
- Acceptance: <observable behavior and expected results>
- Connections / scale: <production callers, data boundaries and relevant limits, or N/A>
- Publication authority and PR evidence: <scope, required reports and residuals>

List only applicable gates (local, integration, live or final combined state). An unavailable required
gate remains pending; name its recovery owner and next action in the existing result/PR evidence.

| Gate | Command / environment | Owner | Required evidence |
| --- | --- | --- | --- |
| <applicable gate> | <exact invocation and safe environment> | <executor or coordinator> | <revision, results including skips, and durable reference> |

The round CLI adds identity, base and branch to the final packet. The packet must be sufficient in
an isolated checkout without access to planner-local records. No target changes or self-merging.
