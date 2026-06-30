## Product Requirement Document

Hey team, we need a small config reader tool for our tracing/observability setup. Basically devs are complaining that every time they wire up a new service they have to manually dig through a dozen env vars to figure out what the tracer is actually going to do at runtime — it's causing a lot of 'works on my machine' issues and support tickets. We want a single pass that takes whatever env vars are set and spits out the effective tracing config in a predictable, readable format.

The output should cover things like whether tracing is on, what exporter is being used, the protocol stuff, any instrumentation lists, activity sources, and that HTTP/2 thing we discussed in the infra thread last week. If someone passes in a bad exporter value it should give back a clean normalized error, not some raw exception dump.

The protocol handling is a bit nuanced — refer to how we handled the 'delegate vs default' pattern in that SDK compatibility layer we shipped a while back, it's the same idea here. Empty or missing protocol means we pin a concrete default, anything else just defers downstream.

Should be runnable as a CLI that takes JSON on stdin and outputs key=value lines. Needs a test harness under rcb_tests/ as well. Keep it clean, separated concerns, no big god files please.