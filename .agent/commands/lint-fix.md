# lint-fix

Follow [the shared contract](common.md).

Input: assigned paths or the current scoped diff.

Read project-configured lint/format commands and excludes. Inspect working-tree state and preserve
unrelated edits. Restrict auto-fixes/formatting to assigned files where supported; do not sweep the
repository or change tool configuration to silence findings. Run safe fixes, inspect every changed
file, then rerun the configured check. Behavioral changes require their own review and targeted tests.

Report remaining findings and verification. Escalate scope conflicts rather than modifying unrelated
code. If the project has no configured tool, report that explicitly; do not assume Ruff or another stack.
