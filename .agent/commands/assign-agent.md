# assign-agent

Follow [the shared contract](common.md).

Input: executable item, round/base, executor and isolated workspace; obtain missing planning decisions
before dispatch. Routine implementation choices remain within the executor's standing authority.

Read the item's complete detail and named authoritative sections. Fill [the assignment
contract](../../templates/assignment.md): one outcome; scope/non-goals; base/branch; source links;
expected symbols; editable records; caller/data connections; service access; resource reservation;
provisioned artifacts; scale envelope; RED/GREEN and exact required gates; verification owner.

Write task-specific content to `specs/<assignment>.md`; hash its exact bytes with a SHA-256 tool,
then create `prompts/<assignment>.md` containing that content plus identity/dispatch instructions.
The digest covers the spec, not the rendered packet. Do not hand-invent digests or require the
executor to read an ignored planner ledger. All source references must resolve in its checkout;
ignored artifacts must be provisioned separately without disclosing secrets.

Record the packet in the round ledger and compare scope/ownership with siblings. Preserve canonical
specifications as references rather than replacing them with paraphrases. Output the packet path,
identity, base and digest. Do not launch an agent, edit unrelated records, or create architecture policy.

Store both spec and final packet SHA-256 in the manifest as specified by [SPEC.md](../../SPEC.md).
