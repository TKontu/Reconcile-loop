# new-endpoint

Follow [the shared contract](common.md).

Input: approved endpoint behavior, request/response contract, authorization and acceptance.

Read the assignment and analogous existing routes, validation models, business/data boundaries and
test harness. If this project has no HTTP/API surface, this helper is not applicable; do not introduce
one solely because the command exists. Resolve missing public contract/security decisions before
implementation and keep routine implementation choices within standing authority.

Use [tdd](tdd.md) to demonstrate the intended endpoint behavior and relevant validation/auth/error
cases. Implement the smallest route and required schemas/service calls, register it in production,
and verify the response contract and source-level connection. Run targeted unit/integration checks
with the configured safe environment. Generate API artifacts only if the project requires them.
No framework-specific libraries, migrations, defaults or wider API redesign are implied by this skill.
