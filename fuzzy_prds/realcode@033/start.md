## Product Requirement Document

Hey team, we need to ship a small logging utility — think of it like the routing layer we built for the notification service, but for log output instead. The core idea is that app code should just call one thing and not care where logs end up. We want to support multiple 'destinations' at once, so if someone wants logs going to the console AND some remote tracker simultaneously, that just works without touching the call sites.

We also got feedback from the on-call team that when things go wrong at 2am, it's really hard to visually scan a terminal and spot the critical stuff. So the console destination should make scary stuff visually pop — warnings and crashes should look obviously different from normal info messages. The exact color scheme follows what the design team agreed on internally (check the last design sync notes).

One more thing from the security folks: sometimes you want to log something but specifically NOT send it to certain destinations — like you might not want to fire off a crash report to the external vendor for every little warning. That selective suppression needs to work per-call without permanently removing any destination from the list.

The whole thing needs a CLI test harness that can run JSON-driven scenarios against it. Keep infra concerns out of the business logic please — same pattern we used on the auth refactor.