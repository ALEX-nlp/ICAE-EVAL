## Product Requirement Document

hey team, we need to wrap up that deployment config toolkit we've been talking about. basically the idea is that devs are spending way too much time hand-rolling the same conversion logic every time someone touches a service definition — things like translating human-readable sizes into what the provider actually wants, figuring out if tags changed between deploys, that kind of stuff. it's causing subtle drift between environments and people only find out something's wrong when the deploy actually fails, which is way too late.

we want a single entrypoint that accepts a JSON blob describing what operation to run and spits out a predictable text result, so it can be wired up to our test harness easily. the core logic should stay cleanly separated from that IO layer though — last time we mixed those together (remember the auth service refactor?) it was a nightmare to test.

some specifics i know we need: the duration stuff should handle both directions (format and parse), the tag diffing needs to show adds/updates/deletes cleanly, resource identifiers from the cloud provider need to be classified, and version constraint checking should fail early with a clear signal. there's also the scheduling strategy edge case that tripped us up before — daemon mode should behave differently than replica. config and definition files need template resolution against env vars too.

check the existing tests folder for the file shapes we're already using, there's a bunch of fixture files in there that show what the loader expects.