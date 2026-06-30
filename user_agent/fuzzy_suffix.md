---

## Clarification

This PRD is intentionally incomplete. A requirements oracle can answer questions about hidden implementation details — including exact feature specs, interface contracts, and test cases.

**Oracle** — POST `http://{host}:{query_port}/`
```
{{"append_id":"{append_id}","task_id":"{task_id}","question":"..."}}
```
Answer is in `data`. Budget shown in `status.remaining`.

Features and test cases have been prepared. Ask before you code. Unasked questions become bugs.
