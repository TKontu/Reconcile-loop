# test

Follow [the shared contract](common.md).

Input: optional test path/pattern or explicit tier. Use the current assignment for default scope.

Read exact test commands and service permissions from the project profile/assignment. Select the
smallest relevant set rather than automatically launching a full suite. If the command is unknown,
inspect existing configuration; do not guess a framework or add dependencies merely to run this skill.

Before integration/live execution verify the permitted disposable/persistent target, configured guard,
resource ownership and artifacts. Never print credentials. Run the selected command, capture the exit
status and counts/skips, and identify whether failures are environmental or behavioral. Do not turn a
fully skipped tier into a pass. Report unavailable gates with a named owner and environment requirement.
Do not alter code unless fixing it is separately within the current task's scope.
