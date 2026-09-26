# decisions

Follow [the shared contract](common.md).

Input: list (default), add with affected item/question/options, or apply an explicit recorded answer.

Read the project's standing policy and canonical decision location. For list, report open decisions,
owners, recommendations and exact blocked work without modifying state. For add, first establish
whether this is a routine authorized choice or a genuinely reserved/missing decision. Record routine
choices in the PR; use [the decision template](../../templates/decision.md) for reserved questions.

Give a recommendation, alternatives, affected items, policy basis and independent work that may
continue. Use separate records or serialize writes. Link the queue from canonical item records;
do not create a competing backlog or infer approval from silence.

For apply, verify explicit approver and scope, preserve the original question/ruling, record the
answer and update only planner-owned affected records. Revise assignments before dependent execution
resumes. A rejected answer is not approval to proceed; a superseding answer links the prior record.
Do not perform the reserved action merely by recording the decision.
