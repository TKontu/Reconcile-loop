# secrets-check

Follow [the shared contract](common.md).

Input: staged changes by default, or an explicit publication diff/artifact set.

Inventory staged paths, including additions, binary/generated artifacts and documents. Inspect actual
staged content rather than assuming the working copy matches. Use the project's configured scanner
when available, then review suspicious additions for credentials, tokens, private keys, connection
strings, infrastructure details and identifiable private source references. Distinguish placeholders
from actual sensitive material; keyword matches alone are not proof.

Report path/line and category with values redacted. Do not echo discovered secrets or private document
titles into logs. Hold affected publication and help remove/exclude material within scope; rerun the
check after the change. If data was already published, flag that separately without rewriting history
or rotating credentials without authority. A clean scan means no findings in the inspected set, not
an absolute guarantee. Do not broaden into unrelated ignored data or credential stores.
