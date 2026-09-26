# quick-fix

Follow [the shared contract](common.md).

Input: exact branch/head, bounded correction, ownership and permitted checks/publication.

Inspect the named branch in an isolated workspace and verify the expected head. Apply only the
specified mechanical change: formatting, wording, generated artifact refresh or similarly bounded
repair. If it requires design, migration or behavioral judgment, return it to the executor/planner.
Preserve unrelated edits and do not use persistent services.

Run relevant configured checks, inspect the diff and report the resulting revision/evidence. Commit
or push only when authorized; never force-push or merge. Any new commit requires affected head-specific
review/verification to refresh. Keep the result concise and tied to the original correction request.
