# verify

Follow [the shared contract](common.md).

Input: assignment/PR and candidate revision, or documentation-only scope.

Read acceptance, configured commands, tier/environment requirements and ownership. Run surgical
checks during development and the broad local gate once before PR creation. After later changes or
failures rerun affected required checks; evidence must describe the actual candidate, not an old head.
Use [test](test.md) for safe service selection. Run lint/types/build only when configured or required.

For docs/skills, validate relative references, entry-point metadata, instructions/templates and
whitespace. Do not invent tests or claim structural checks prove runtime behavior. Record commands,
revision/environment, outcomes, counts and skips. Missing required checks block the completion claim;
name their owner and reason. Distinguish unit, integration, live and representative-scale evidence.

Return satisfied and outstanding acceptance explicitly. A successful exit alone does not prove the
expected tests ran. Do not broaden or repeatedly rerun successful checks without a changed condition.
