# Session response contract

| Credential | Response |
| --- | --- |
| Expired | 401 before protected resource lookup |
| Malformed | 401 |
| Valid | Continue to resource lookup and its normal response |

Authentication failures must not reveal whether an inaccessible protected resource exists.
