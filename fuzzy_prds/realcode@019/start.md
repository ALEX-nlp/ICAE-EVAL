## Product Requirement Document

Hey team, we need a small utility layer for our PHP libraries so they can announce deprecated code paths without stepping on the host application's toes. The core idea is that a library just declares 'this thing is deprecated' with a stable URL and a message, and the host app decides what to do with it — or nothing at all if it hasn't opted in. Right now our libraries are either throwing errors directly or spamming logs in ways consumers can't control, and we keep getting complaints about noise in test suites and production logs.

The layer should support a few different modes of operation — counting only, routing to the runtime error channel, or sending to a structured logger — and the host should be able to flip between these either in code or via some kind of environment config (think the same pattern we used in that deployment-selector mechanism from the auth service refactor).

There should also be a way to silence specific deprecations or whole vendor packages without affecting whether they get counted. And we need the repeated-trigger noise problem handled by default, with an escape hatch to turn that off.

One tricky bit: some deprecations should only fire when a consumer outside the owning package calls into it — internal calls within the same package should stay quiet. Also need a reset/disable capability so test suites can clean up state between runs. Please keep the internals cleanly separated — routing, counting, and suppression logic should not be tangled together.