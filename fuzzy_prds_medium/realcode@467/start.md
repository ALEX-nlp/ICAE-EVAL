## Product Requirement Document

Hey team, we need a small config reader tool for our tracing/observability setup. Basically devs are complaining that every time they wire up a new service they have to manually dig through a dozen env vars to figure out what the tracer is actually going to do at runtime — it's causing a lot of 'works on my machine' issues and support tickets. We want a single pass that takes whatever env vars are set and spits out the effective tracing config in a predictable, readable format.

The output should cover things like whether tracing is on, what exporter is being used, the protocol stuff, any instrumentation lists, activity sources, and that HTTP/2 thing we discussed in the infra thread last week. If someone passes in a bad exporter value it should give back a clean normalized error, not some raw exception dump.

The protocol handling is a bit nuanced — refer to how we handled the 'delegate vs default' pattern in that SDK compatibility layer we shipped a while back, it's the same idea here. Empty or missing protocol means we pin a concrete default, anything else just defers downstream.

Should be runnable as a CLI that takes JSON on stdin and outputs key=value lines. Needs a test harness under rcb_tests/ as well. Keep it clean, separated concerns, no big god files please.

One follow-up from the questions that came in: when no environment variables are provided, we do want the tool to print the full effective config every time, not a partial view. The defaults are trace_enabled=true, load_at_startup=true, traces_exporter=otlp, otlp_protocol=http/protobuf, console_exporter_enabled=true, enabled_instrumentations=(empty), tracer_plugins=(empty), activity_sources=default_activity_source, legacy_sources=(empty), integrations_available=true, http2_unencrypted_support=false, and all eleven fields must appear in that exact order.

Also clarifying the exporter behavior a bit more. OTEL_TRACES_EXPORTER only supports none, jaeger, otlp, and zipkin. Anything else should come back as a normalized error response with exactly two fields and nothing extra: error=unsupported_traces_exporter and value=<the rejected string>. Put differently, the output must be exactly two newline-terminated lines: 'error=unsupported_traces_exporter' and 'value=<rejected_value>'. No stack traces, no exception class names, no additional fields are permitted.

For the protocol piece, OTEL_EXPORTER_OTLP_PROTOCOL is the switch for otlp_protocol. If that variable is absent, null, or an empty string, use otlp_protocol=http/protobuf. If any non-empty string is present, even something like 'grpc' or 'http/json', then the output should be otlp_protocol=sdk_default, since at that point we’re deferring interpretation to the exporter layer instead of deciding it here.

And on the HTTP/2 flag, the environment variable is OTEL_DOTNET_AUTO_HTTP2UNENCRYPTEDSUPPORT_ENABLED, and that is what controls the http2_unencrypted_support boolean field in the effective configuration output. Only the exact string 'true' should set http2_unencrypted_support=true. The string 'false', a null value, or an absent key all result in http2_unencrypted_support=false.