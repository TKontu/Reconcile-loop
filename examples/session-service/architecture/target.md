# Session-service target

An expired session must be rejected with HTTP 401 before protected resource lookup. A valid session
continues to resource lookup and receives that resource's normal response. A malformed credential
also receives 401. The contract does not reveal whether an inaccessible protected resource exists.

Implementation, token format, database choice and deployment are outside this example round.
The operator approves target changes; a docs task cannot redefine behavior.
