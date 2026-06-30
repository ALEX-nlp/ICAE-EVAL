## Product Requirement Document

Hey team, we need a traffic throttling library built in Rust that devs can drop into any service to control how fast work gets processed. The basic idea is you configure an allowance — like '50 requests per second' or '2 per minute' — and then ask the library 'can this go through?' and it says yes or no, and if no it tells you exactly how long to wait before retrying. We also need it to handle bulkier workloads where you want to admit like 5 or 10 units at once, not just one at a time.

One big thing: it needs to be fully testable without depending on the system clock — remember how we solved that in the auth middleware last quarter? Same kind of pattern, the clock needs to be injectable so tests are deterministic.

Also need per-key isolation, so different tenants or endpoints each get their own independent budget under one shared config. And there should be a way to clean up stale keys periodically so memory doesn't grow forever.

Finally, a 'state reporting' mode where admitted requests also reveal how much budget is left — useful for dashboards or client hints.

All durations should be in nanoseconds internally. The adapter layer should read a single JSON command from stdin and write plain text lines to stdout. Exact output format details are in the test cases but basically think 'check allow', 'check deny wait_ns=...', that kind of thing.