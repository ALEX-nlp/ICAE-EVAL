## Product Requirement Document

# Distributed Trace-Context & Adaptive Sampling Toolkit - PRD

## Project Goal

Build a client-side tracing toolkit that lets developers **propagate trace context across service boundaries** and **decide which traces to record** without hand-rolling wire formats, sampling math, or metric bookkeeping. The toolkit provides: a canonical trace-context serializer/parser, a family of sampling strategies (constant, probabilistic, rate-limited, and guaranteed-throughput), a deterministic token-bucket rate limiter, IPv4/baggage-key utilities, B3 and text-map header codecs, and an in-memory metrics backend wired into the span lifecycle.

---

## Background & Problem

Without such a toolkit, every service that wants distributed tracing must independently reinvent the same fragile pieces: how to pack a 64-bit trace id, span id, parent id and a flags byte into a header string and parse it back; how to turn a sampling probability into a deterministic keep/drop decision per trace id; how to throttle trace volume with a refillable budget; how to read and write the de-facto B3 propagation headers used by other tracing libraries; and how to count started/finished spans for observability. Each reimplementation drifts subtly, breaking interoperability between services and producing traces that cannot be stitched together.

With this toolkit, propagation and sampling become a small set of well-defined, deterministic operations with a stable wire contract. A service injects context into outgoing headers and extracts it from incoming ones; a sampler yields a reproducible decision plus self-describing tags; and span metrics are emitted automatically. The behavior is identical across processes, so traces line up end-to-end.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility domain (wire codecs, sampling strategies, a rate limiter, utilities, and a metrics backend). It MUST be organized as a multi-file repository with clear separation between propagation, sampling, utilities, and metrics — not a single monolithic file. Do not over-engineer the leaf utilities, but keep each responsibility in its own cohesive unit.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box contract for the execution adapter**, not the internal data model. The core domain types (context, samplers, limiter, metrics) MUST NOT know about JSON or stdin/stdout. A thin execution adapter translates each JSON command into idiomatic core calls and renders the result.

3. **Adherence to SOLID Design Principles:** Parsing, routing, the sampling decision engine, and output formatting must be distinct units. New sampler types or new propagation codecs must be addable without modifying existing ones (samplers and codecs are interface-driven). High-level flows depend on the `Sampler` / codec abstractions, not concrete implementations.

4. **Robustness & Interface Design:** The public surface must be idiomatic to the target language and hide internal complexity. Invalid inputs (out-of-range sampling rate, malformed context string, non-IPv4 address, empty inputs) must be modeled as explicit, typed error conditions and surfaced to the adapter as **normalized, language-neutral error categories** — never as host-runtime exception text.

---

## Core Features

### Feature 1: Trace-Context Wire String

**As a developer**, I want to serialize and parse a trace context as a compact header string, so I can carry it in a single header and reconstruct it on the receiving side.

**Expected Behavior / Usage:**

A trace context is four values: a 64-bit `trace_id`, a 64-bit `span_id`, a 64-bit `parent_id`, and an 8-bit `flags`.

*1.1 Encode — serialize a context to the canonical wire string*

The wire string is the four fields joined by colons. Each of the three ids is rendered as **unsigned lowercase hexadecimal** (so a negative signed id appears as its full 64-bit two's-complement hex, e.g. the signed value `-10` becomes `fffffffffffffff6`); the flags byte is rendered as its unsigned hex value (`0`–`ff`). Output is a single line `context=<trace[a specific delimiter character]<span[a specific delimiter character]<parent[a specific delimiter character]<flags>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_context_encode.json`

```json
{
    "description": "Serialize a trace context (trace id, span id, parent id, one-byte flags) into its canonical colon-separated lowercase-hex wire string. Each of the three 64-bit ids is printed as unsigned lowercase hex and the flags byte as its unsigned hex value.",
    "cases": [
        {"input": {"op": "context_encode", "trace_id": -10, "span_id": -10, "parent_id": -10, "flags": 129}, "expected_output": "context=fffffffffffffff6:fffffffffffffff6:fffffffffffffff6:81\n"},
        {"input": {"op": "context_encode", "trace_id": 255, "span_id": 221, "parent_id": 204, "flags": 4}, "expected_output": "context=ff:dd:cc:4\n"}
    ]
}
```

*1.2 Decode — parse a wire string back into numeric fields*

A valid string has exactly four colon-separated hex fields; each is parsed as a 64-bit signed value (so `fffffffffffffff6` round-trips back to `-10`, and the flags field is interpreted as a signed byte). Output is four lines `trace_id=`, `span_id=`, `parent_id=`, `flags=`. An **empty input** yields `error=empty_tracer_state_string`. A string whose field count is not four yields `error=malformed_tracer_state_string` followed by `value=<raw>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_context_decode.json`

```json
{
    "description": "Parse a colon-separated lowercase-hex trace-context wire string back into its four numeric components. The string must contain exactly four colon-separated hex fields; an empty string and a string with the wrong number of fields are reported as distinct normalized errors.",
    "cases": [
        {"input": {"op": "context_decode", "value": "ff:dd:cc:4"}, "expected_output": "trace_id=255\nspan_id=221\nparent_id=204\nflags=4\n"},
        {"input": {"op": "context_decode", "value": "fffffffffffffff6:fffffffffffffff6:fffffffffffffff6:81"}, "expected_output": "trace_id=-10\nspan_id=-10\nparent_id=-10\nflags=-127\n"},
        {"input": {"op": "context_decode", "value": "ff:ff:ff"}, "expected_output": "error=malformed_tracer_state_string\nvalue=ff:ff:ff\n"},
        {"input": {"op": "context_decode", "value": ""}, "expected_output": "error=empty_tracer_state_string\n"}
    ]
}
```

---

### Feature 2: Sampling Strategies

**As a developer**, I want pluggable sampling strategies that each return a keep/drop decision plus self-describing tags, so I can control trace volume and record how the decision was made.

**Expected Behavior / Usage:**

Every sampler answers a query with three lines: `sampled=<true|false>`, `sampler_type=<type>`, `sampler_param=<param>`. The `type`/`param` tags identify the strategy and its configuration.

*2.1 Constant sampler — always the same decision*

Returns its fixed boolean decision for any operation/trace id. Tags: type `const`, param equal to the boolean decision.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_sampler_const.json`

```json
{
    "description": "A constant sampler always returns the same fixed sampling decision regardless of operation name or trace id, and reports its decision via sampler tags (type 'const' and the boolean decision as the parameter).",
    "cases": [
        {"input": {"op": "sampler_const", "decision": true, "id": 218, "operation": "biryani"}, "expected_output": "sampled=true\nsampler_type=const\nsampler_param=true\n"},
        {"input": {"op": "sampler_const", "decision": false, "id": 0, "operation": "x"}, "expected_output": "sampled=false\nsampler_type=const\nsampler_param=false\n"}
    ]
}
```

*2.2 Probabilistic sampler — keep a fraction of traces by id*

Configured with a rate in `[0,1]`. The rate maps to a symmetric boundary over the signed 64-bit id space: a **positive** id is sampled when it is at or below the positive boundary `floor((2^63 - 1) * rate)`; a **negative** id is sampled when it is at or above the negative boundary `floor(-2^63 * rate)`. Tags: type `probabilistic`, param the rate. A rate `< 0` or `> 1` yields `error=sampling_rate_out_of_range` followed by `rate=<value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_sampler_probabilistic.json`

```json
{
    "description": "A probabilistic sampler samples a trace when its id falls within a boundary derived from the configured rate in [0,1]. Positive ids sample when id is at or below the positive boundary; negative ids sample when id is at or above the negative boundary. The reported tags carry type 'probabilistic' and the rate. A rate outside [0,1] is a normalized range error.",
    "cases": [
        {"input": {"op": "sampler_probabilistic", "rate": 0.5, "id": 4611686018427387903}, "expected_output": "sampled=true\nsampler_type=probabilistic\nsampler_param=0.5\n"},
        {"input": {"op": "sampler_probabilistic", "rate": 0.5, "id": 4611686018427387905}, "expected_output": "sampled=false\nsampler_type=probabilistic\nsampler_param=0.5\n"},
        {"input": {"op": "sampler_probabilistic", "rate": 0.5, "id": -4611686018427387904}, "expected_output": "sampled=true\nsampler_type=probabilistic\nsampler_param=0.5\n"},
        {"input": {"op": "sampler_probabilistic", "rate": 0.5, "id": -4611686018427387905}, "expected_output": "sampled=false\nsampler_type=probabilistic\nsampler_param=0.5\n"},
        {"input": {"op": "sampler_probabilistic", "rate": 0.1, "id": 20, "operation": "vadacurry"}, "expected_output": "sampled=true\nsampler_type=probabilistic\nsampler_param=0.1\n"}
    ]
}
```

*2.3 Rate-limiting sampler — cap traces per second*

Configured with a maximum traces-per-second. Tags: type `ratelimiting`, param the configured maximum (rendered as a decimal). With a fresh budget the first request is admitted.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_sampler_ratelimiting.json`

```json
{
    "description": "A rate-limiting sampler reports tags with type 'ratelimiting' and the configured maximum traces-per-second as the parameter. With a fresh bucket the first request is admitted.",
    "cases": [
        {"input": {"op": "sampler_ratelimiting", "max_traces_per_second": 123, "id": 11, "operation": "operate"}, "expected_output": "sampled=true\nsampler_type=ratelimiting\nsampler_param=123.0\n"}
    ]
}
```

*2.4 Guaranteed-throughput sampler — probabilistic with a lower bound*

Combines a probabilistic sampler with a lower-bound rate limiter so every operation is sampled at least once per interval. If the probabilistic component samples, its tags (type `probabilistic`, param the rate) are reported; otherwise the result reflects the lower-bound component and reports type `lowerbound` with the probabilistic rate as param. The sampler can be reconfigured at runtime by supplying `updates` (each `{rate, lower_bound}`); each update emits an `update=<true|false>` line indicating whether anything actually changed before the final sample is taken.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_sampler_guaranteed.json`

```json
{
    "description": "A guaranteed-throughput sampler combines a probabilistic sampler with a lower-bound rate limiter so that every operation is sampled at least once per interval. When the probabilistic sampler samples, its tags (type 'probabilistic') are reported; otherwise the lower-bound tags (type 'lowerbound') are reported. It can be reconfigured at runtime; an update returns whether anything actually changed.",
    "cases": [
        {"input": {"op": "sampler_guaranteed", "rate": 0.0001, "lower_bound": 1.0, "id": 9223372036854775807}, "expected_output": "sampled=true\nsampler_type=lowerbound\nsampler_param=0.00010\n"},
        {"input": {"op": "sampler_guaranteed", "rate": 0.999, "lower_bound": 1.0, "id": 0}, "expected_output": "sampled=true\nsampler_type=probabilistic\nsampler_param=0.999\n"},
        {"input": {"op": "sampler_guaranteed", "rate": 0.001, "lower_bound": 1, "id": 9223372036854775807, "updates": [{"rate": 0.001, "lower_bound": 1}, {"rate": 0.002, "lower_bound": 1}]}, "expected_output": "update=false\nupdate=true\nsampled=true\nsampler_type=lowerbound\nsampler_param=0.002\n"}
    ]
}
```

---

### Feature 3: Token-Bucket Rate Limiter

**As a developer**, I want a deterministic token-bucket limiter driven by an explicit clock, so I can admit work up to a refillable budget and test the behavior reproducibly.

**Expected Behavior / Usage:**

The bucket is configured with a refill rate (credits per second) and a maximum balance, and starts **full** (balance = max). Each step optionally advances a virtual clock (`advance_micros` and/or `advance_millis`) and then attempts to charge a `cost`. Before charging, the balance accrues `elapsed_seconds * credits_per_second`, capped at the maximum. The request is admitted (`allow=true`) only when the balance is at least the cost, in which case the cost is deducted; otherwise `allow=false` and the balance is unchanged. One `allow=` line is emitted per step.

**Test Cases:** `rcb_tests/public_test_cases/feature3_rate_limiter.json`

```json
{
    "description": "A token-bucket rate limiter starts full (balance = max). Each step may advance a virtual clock (microseconds and/or milliseconds) before charging a cost; the request is admitted only when the accumulated balance covers the cost. Credits refill at the configured rate but the balance is capped at the configured maximum.",
    "cases": [
        {"input": {"op": "rate_limiter", "credits_per_second": 2.0, "max_balance": 2.0, "steps": [{"advance_micros": 100, "cost": 1.0}, {"cost": 1.0}, {"cost": 1.0}, {"advance_millis": 250, "cost": 1.0}, {"advance_millis": 500, "cost": 1.0}, {"cost": 1.0}, {"advance_millis": 5000, "cost": 1.0}, {"cost": 1.0}, {"cost": 1.0}, {"cost": 1.0}, {"cost": 1.0}]}, "expected_output": "allow=true\nallow=true\nallow=false\nallow=false\nallow=true\nallow=false\nallow=true\nallow=true\nallow=false\nallow=false\nallow=false\n"},
        {"input": {"op": "rate_limiter", "credits_per_second": 0.5, "max_balance": 0.5, "steps": [{"advance_micros": 100, "cost": 0.25}, {"cost": 0.25}, {"cost": 0.25}, {"advance_millis": 250, "cost": 0.25}, {"advance_millis": 500, "cost": 0.25}, {"cost": 0.25}]}, "expected_output": "allow=true\nallow=true\nallow=false\nallow=false\nallow=true\nallow=false\n"}
    ]
}
```

---

### Feature 4: Address & Baggage-Key Utilities

**As a developer**, I want small normalization helpers for network addresses and metadata keys, so I can store them in compact, canonical forms.

**Expected Behavior / Usage:**

*4.1 IPv4 to signed 32-bit integer*

Convert a dotted-quad IPv4 address into its big-endian two's-complement 32-bit integer (`127.0.0.1` → `2130706433`, `255.255.255.255` → `-1`). Output: `ip_int=<value>`. An **empty** input yields `error=empty_ip`; a string that is not a valid dotted-quad yields `error=not_four_octets` followed by `ip=<raw>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_ip_to_int.json`

```json
{
    "description": "Convert a dotted-quad IPv4 address into its signed 32-bit integer value (big-endian, two's-complement). An empty string and a non-IPv4 string are reported as distinct normalized errors.",
    "cases": [
        {"input": {"op": "ip_to_int", "ip": "127.0.0.1"}, "expected_output": "ip_int=2130706433\n"},
        {"input": {"op": "ip_to_int", "ip": "10.137.1.2"}, "expected_output": "ip_int=176750850\n"},
        {"input": {"op": "ip_to_int", "ip": "0.0.0.0"}, "expected_output": "ip_int=0\n"},
        {"input": {"op": "ip_to_int", "ip": "255.255.255.255"}, "expected_output": "ip_int=-1\n"},
        {"input": {"op": "ip_to_int", "ip": ":19"}, "expected_output": "error=not_four_octets\nip=:19\n"},
        {"input": {"op": "ip_to_int", "ip": ""}, "expected_output": "error=empty_ip\n"}
    ]
}
```

*4.2 Baggage-key normalization*

Normalize a metadata key by replacing every underscore with a hyphen and lowercasing the result. Output: `key=<normalized>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_normalize_baggage_key.json`

```json
{
    "description": "Normalize a baggage key by replacing underscores with hyphens and lowercasing the result.",
    "cases": [
        {"input": {"op": "normalize_baggage_key", "key": "TEST_KEY"}, "expected_output": "key=test-key\n"},
        {"input": {"op": "normalize_baggage_key", "key": "Some_Mixed_KEY"}, "expected_output": "key=some-mixed-key\n"}
    ]
}
```

---

### Feature 5: B3 Multi-Header Propagation

**As a developer**, I want to read and write the widely-used B3 multi-header format, so my traces interoperate with other tracing libraries.

**Expected Behavior / Usage:**

*5.1 Inject a context into B3 headers*

Write `X-B3-TraceId`, `X-B3-SpanId` (and `X-B3-ParentSpanId` only when the parent id is non-zero) as **zero-padded 16-character lowercase hex**. Write `X-B3-Sampled` as `1` when sampled else `0`. When the debug flag is set, also write `X-B3-Flags=1`. Baggage items are written under a configurable prefix (default `baggage-`, so `foo` → `baggage-foo`). The adapter emits one `header=value` line per produced header, sorted by header name.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_b3_inject.json`

```json
{
    "description": "Inject a trace context into a B3 multi-header carrier. Each id is written as zero-padded 16-character lowercase hex; the parent header is emitted only when the parent id is non-zero; the sampled header is '1' when sampled, else '0'; debug flag emits a flags header. Baggage items are written under a configurable prefix (default 'baggage-'). Output lines are sorted by header name.",
    "cases": [
        {"input": {"op": "b3_inject", "trace_id": 1, "span_id": 2, "parent_id": 3, "flags": 0, "baggage": {"foo": "bar"}}, "expected_output": "X-B3-ParentSpanId=0000000000000003\nX-B3-Sampled=0\nX-B3-SpanId=0000000000000002\nX-B3-TraceId=0000000000000001\nbaggage-foo=bar\n"},
        {"input": {"op": "b3_inject", "trace_id": 1, "span_id": 1, "parent_id": 1, "flags": 1}, "expected_output": "X-B3-ParentSpanId=0000000000000001\nX-B3-Sampled=1\nX-B3-SpanId=0000000000000001\nX-B3-TraceId=0000000000000001\n"}
    ]
}
```

*5.2 Extract a context from B3 headers*

Read the id headers (case-insensitively); a **128-bit** trace id is downgraded to its lower 64 bits. `X-B3-Sampled` (`1`/`true`) sets the sampled flag and `X-B3-Flags=1` sets the debug flag, combined into the context flags. Baggage carried under the prefix is collected; unrelated headers are ignored. Output is `trace_id=`, `span_id=`, `parent_id=`, `flags=` and then one `baggage.<key>=<value>` line per baggage item (sorted by key). When the required id headers are absent, output is `context=none`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_b3_extract.json`

```json
{
    "description": "Extract a trace context from a B3 multi-header carrier. A 128-bit trace id is downgraded to its lower 64 bits. The sampled and flags headers combine into the context flags. Baggage carried under the prefix is collected and unrelated headers are ignored. When the required id headers are absent, no context is produced.",
    "cases": [
        {"input": {"op": "b3_extract", "headers": {"X-B3-TraceId": "463ac35c9f6413ad48485a3953bb6124", "X-B3-SpanId": "48485a3953bb6124", "X-B3-ParentSpanId": "0", "X-B3-Sampled": "1", "X-B3-Flags": "1", "baggage-foo": "bar", "random-foo": "bar"}}, "expected_output": "trace_id=5208512171318403364\nspan_id=5208512171318403364\nparent_id=0\nflags=3\nbaggage.foo=bar\n"},
        {"input": {"op": "b3_extract", "headers": {"X-B3-Sampled": "1", "random": "x"}}, "expected_output": "context=none\n"}
    ]
}
```

---

### Feature 6: Text-Map Codec Configuration

**As a developer**, I want a text-map propagation codec whose header key, baggage prefix, and URL-encoding can be configured, so I can adapt to differing header conventions.

**Expected Behavior / Usage:**

The codec exposes its effective configuration as three lines: `context_key=<key>`, `baggage_prefix=<prefix>`, `url_encoding=<true|false>`. The defaults are `uber-trace-id` and `uberctx-` with URL-encoding off; all three are overridable.

**Test Cases:** `rcb_tests/public_test_cases/feature6_textmap_config.json`

```json
{
    "description": "A text-map propagation codec exposes its effective configuration: the header key used for the serialized context, the prefix used for baggage headers, and whether values are URL-encoded. Defaults are 'uber-trace-id' and 'uberctx-'; all three are overridable.",
    "cases": [
        {"input": {"op": "textmap_config", "url_encoding": false}, "expected_output": "context_key=uber-trace-id\nbaggage_prefix=uberctx-\nurl_encoding=false\n"},
        {"input": {"op": "textmap_config", "url_encoding": true, "context_key": "jaeger-trace-id", "baggage_prefix": "jaeger-baggage-"}, "expected_output": "context_key=jaeger-trace-id\nbaggage_prefix=jaeger-baggage-\nurl_encoding=true\n"}
    ]
}
```

---

### Feature 7: In-Memory Metrics Backend

**As a developer**, I want an ephemeral metrics backend addressed by metric name plus tag set, so I can record and query counters, timers, and gauges in tests.

**Expected Behavior / Usage:**

Each metric is identified by its **name together with its tag set**. Querying a name/tag combination that was never created returns `-1`. A created metric starts at `0`. Each query emits one line `value=<n>`.

*7.1 Counter — monotonic accumulation*

A counter accumulates increments. A query against a tag set different from the one used at creation is treated as a different (non-existent) series and returns `-1`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_metrics_counter.json`

```json
{
    "description": "An in-memory counter is identified by its name plus its tag set. Querying a name/tag combination that was never created returns -1; a created counter starts at 0 and accumulates increments.",
    "cases": [
        {"input": {"op": "metrics", "kind": "counter", "name": "thecounter", "tags": {"foo": "bar"}, "steps": [{"action": "get", "tags": {}}, {"action": "get", "tags": {"foo": "bar"}}, {"action": "inc", "amount": 1}, {"action": "get", "tags": {"foo": "bar"}}]}, "expected_output": "value=-1\nvalue=0\nvalue=1\n"}
    ]
}
```

*7.2 Timer — accumulated durations*

A timer accumulates recorded durations the same way a counter accumulates increments.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_metrics_timer.json`

```json
{
    "description": "An in-memory timer is identified by its name plus its tag set. Querying an unknown name/tag combination returns -1; a created timer starts at 0 and accumulates recorded durations.",
    "cases": [
        {"input": {"op": "metrics", "kind": "timer", "name": "thetimer", "tags": {"foo": "bar"}, "steps": [{"action": "get", "tags": {}}, {"action": "get", "tags": {"foo": "bar"}}, {"action": "duration", "amount": 1}, {"action": "get", "tags": {"foo": "bar"}}]}, "expected_output": "value=-1\nvalue=0\nvalue=1\n"}
    ]
}
```

*7.3 Gauge — last value wins*

A gauge holds the most recently set value: each update replaces the current value rather than accumulating.

**Test Cases:** `rcb_tests/public_test_cases/feature7_3_metrics_gauge.json`

```json
{
    "description": "An in-memory gauge is identified by its name plus its tag set. Querying an unknown name/tag combination returns -1; a created gauge starts at 0 and each update replaces the current value with the new value.",
    "cases": [
        {"input": {"op": "metrics", "kind": "gauge", "name": "thegauge", "tags": {"foo": "bar"}, "steps": [{"action": "get", "tags": {}}, {"action": "get", "tags": {"foo": "bar"}}, {"action": "update", "amount": 1}, {"action": "get", "tags": {"foo": "bar"}}, {"action": "update", "amount": 2}, {"action": "get", "tags": {"foo": "bar"}}]}, "expected_output": "value=-1\nvalue=0\nvalue=1\nvalue=2\n"}
    ]
}
```

---

### Feature 8: Span-Lifecycle Metrics Integration

**As a developer**, I want span creation to automatically emit metrics into the backend, so I can observe trace volume without manual instrumentation.

**Expected Behavior / Usage:**

When a span is started through the tracing pipeline with a constant **sampled** decision, the backend's counters are updated: `jaeger:started_spans` with tag string `sampled=y` becomes `1` while `sampled=n` stays `0`, and `jaeger:traces` with `sampled=y,state=started` becomes `1` while `sampled=n,state=started` stays `0`. Counters are queried by metric name and an exact comma-separated tag string; a query whose tag string does not exactly match a created series returns `-1`. Each query emits one line `<name>|<tags>=<value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_tracer_span_metrics.json`

```json
{
    "description": "Starting a span through the tracer pipeline emits counters into the metrics backend. Counters are addressed by metric name and a comma-separated tag string. Starting one sampled span increments started_spans(sampled=y) and traces(sampled=y,state=started) to 1 while their not-sampled counterparts stay 0. Querying a counter whose tag string does not exactly match a created series returns -1.",
    "cases": [
        {"input": {"op": "tracer_metrics", "service": "metricsFactoryTest", "operation": "theoperation", "sampled": true, "queries": [{"name": "jaeger:started_spans", "tags": "sampled=y"}, {"name": "jaeger:started_spans", "tags": "sampled=n"}, {"name": "jaeger:traces", "tags": "sampled=y,state=started"}, {"name": "jaeger:traces", "tags": "sampled=n,state=started"}]}, "expected_output": "jaeger:started_spans|sampled=y=1\njaeger:started_spans|sampled=n=0\njaeger:traces|sampled=y,state=started=1\njaeger:traces|sampled=n,state=started=0\n"},
        {"input": {"op": "tracer_metrics", "service": "metricsFactoryTest", "operation": "theoperation", "sampled": true, "queries": [{"name": "jaeger:started_spans", "tags": "sampled"}, {"name": "jaeger:started_spans", "tags": ""}]}, "expected_output": "jaeger:started_spans|sampled=-1\njaeger:started_spans|=-1\n"}
    ]
}
```

---

### Feature 9: Default Baggage Restriction Policy

**As a developer**, I want a default policy describing whether a metadata key is permitted and how long its value may be, so I can enforce baggage limits uniformly.

**Expected Behavior / Usage:**

The default policy allows **every** key and caps each value length at **2048** characters, independent of the service or key queried. Output: `key_allowed=true` and `max_value_length=2048`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_baggage_restriction.json`

```json
{
    "description": "The default baggage restriction policy allows every key and caps each baggage value length at 2048 characters, independent of the service or key queried.",
    "cases": [
        {"input": {"op": "baggage_restriction", "service": "", "key": "key"}, "expected_output": "key_allowed=true\nmax_value_length=2048\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the features above — propagation codecs (trace-context string, B3 multi-header, configurable text-map), the sampling strategies, the token-bucket limiter, the address/key utilities, and the in-memory metrics backend with span-lifecycle integration — with the core domain fully decoupled from stdin/stdout and JSON.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON command from stdin, dispatches it to the appropriate core logic, and prints the language-neutral contract to stdout exactly as specified per leaf feature. All invalid-input conditions are rendered as normalized `error=<category>` lines (plus a separate field for the offending value where applicable); no host-language exception identity appears in stdout. This adapter is separate from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory (default `public_test_cases`). For each case it writes one file `rcb_tests/stdout/<cases-dir>/{stem}@{index:03d}.txt` containing **only** the raw stdout of the program under test (no PASS/FAIL or metadata), namespaced by `<cases-dir>` so different case directories never overwrite each other, directly comparable against `expected_output`.


---
**Implementation notes:**
- use the same flag encoding scheme as the authority module
