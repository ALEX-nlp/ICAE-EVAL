## Product Requirement Document

Hey team, we need to ship that expression reconstruction library we've been talking about. The idea is pretty straightforward — devs are sick of maintaining two copies of the same business logic, one for running and one for query stuff. We want a single place where you write the logic once and it just 'knows' how to represent itself symbolically too.

We need it to handle the usual suspects: basic value stuff, nullable/fallback cases, collection building, and then the more interesting case where computed properties on records get 'unfolded' into what they're actually doing under the hood so query providers don't choke on them. Also the method body reconstruction thing — similar to what we did with the output-slot pattern in the auth module, where it parses and falls back cleanly.

There's also a config piece — the engine should have a sensible startup story, like a default kicks in if nobody sets one up, but if you try to reconfigure it after the fact it should fail in a clean, framework-neutral way (no raw exception names leaking out). And we need it to stay fast even when predicates get really large — someone mentioned 27 items as the benchmark case.

The test harness needs to write per-case output files into a namespaced folder so different test runs don't stomp each other. Keep the adapter layer totally separate from the core logic please, last time things got messy.