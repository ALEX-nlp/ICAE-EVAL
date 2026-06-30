## Product Requirement Document

Hey team, we need to build out that gateway routing support library we've been talking about. Basically devs keep complaining they have to rewrite the same boilerplate every time they wire up a new service — stuff like figuring out whether to use secure connections, handling those weird international characters in URLs that break things downstream, and making sure monitoring dashboards can actually group metrics together properly. It's a mess right now and every team is doing it differently.

The library should handle the full lifecycle of a proxied request — from taking a discovered service name and turning it into a clean route path, all the way through to how headers get copied and filtered. There's some existing compatibility logic we used in the header filtering piece from that security hardening sprint a while back — make sure the new implementation stays consistent with whatever defaults we landed on there.

Also the metrics naming has been a recurring complaint from the SRE team — they can't aggregate anything reliably because the tag formatting is inconsistent across services. Fix that too.

The adapter layer that wires up the JSON test harness should stay totally separate from the actual business logic — we got burned last time when someone mixed those together and it made the core untestable. The test runner should output files per case so we can diff them individually. Ping me if anything's unclear.