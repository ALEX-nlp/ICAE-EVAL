## Product Requirement Document

# Distributed Tracing Instrumentation for a Microservice Application Framework

## Project Goal

Build an auto-activating tracing instrumentation layer for a conventional
microservice application framework. When the host application performs common
runtime activities — serving inbound HTTP requests, calling other services,
routing traffic through an edge gateway, talking to a database, running work in
the background, scheduling jobs, executing circuit-breaker commands, or passing
messages through a publish/subscribe channel — the layer must automatically
produce tracing **spans** that describe each activity and correctly correlate
them into traces, without the application author writing any tracing code.

The layer binds to a pluggable tracer abstraction. For the purposes of this
contract, an in-memory tracer records every finished span so that the observable
result of an activity can be inspected: the span's operation name, its
component and kind, selected attributes (such as HTTP status, route host, or
database statement), whether it recorded an error, and which span is its parent.

## Background & Problem

In a distributed system a single logical action fans out across many technical
layers and threads. Operators need an end-to-end picture of where time is spent
and where failures originate, but manually adding tracing calls to every entry
point, client, executor and message handler is error-prone, repetitive and
quickly drifts out of date.

The problem this project solves is to make tracing **ambient**: by being present
on the application's classpath and detecting a configured tracer, the layer
transparently wraps the framework's extension points so that activities are
traced consistently. Two properties matter most:

1. **Faithful observation** — each activity yields a span with the right
   operation name, component label, kind, status/attributes and error flag.
2. **Correct correlation** — spans produced within one logical action share a
   single trace, and each span points at the correct parent, even across thread
   boundaries, asynchronous hand-offs and remote message carriers.

## Architecture & Engineering Constraints

- **Ambient activation.** The instrumentation activates only when a tracer is
  available, and otherwise stays inert. It must not require changes to business
  code beyond ordinary framework configuration.
- **Pluggable tracer.** All spans are created through a tracer abstraction.
  Instrumentation never depends on a concrete backend.
- **Context propagation.** The currently active span is treated as the parent of
  any span started while it is active. Context must survive executor hand-offs,
  asynchronous results and serialization into/out of message carriers.
- **Language-neutral observable contract.** The externally-checkable result of an
  activity is a deterministic textual rendering of the finished spans. It must
  not contain random identifiers, host-language exception types, or
  backend-specific formatting. Failures are surfaced as a neutral error flag and
  a neutral error event on the relevant span.
- **Determinism.** Renderings are stable across runs: span/trace identifiers are
  never printed; parent links are rendered by the parent's operation name; span
  lines are emitted in a stable, sorted order; the number of distinct traces is
  reported instead of raw trace identifiers.

### Observable rendering format

Most features render a finished-span set as:

```
spans=<total number of finished spans>
distinct_traces=<number of distinct traces; 0 when there are no spans>
<one sorted line per span>
```

Each per-span line has the shape:

```
op=<operation name> component=<component|-> span.kind=<kind|-> http.status=<status|-> attrs=[k=v;...sorted] error=<true|false> error_log=<event|-> parent=<parent operation|root|external>
```

where `component`, `span.kind`, `http.status` and the error flag are surfaced as
dedicated fields; all remaining tags appear in the sorted `attrs` list; `parent`
is `root` for a span with no parent and `external` for a parent that is not part
of the recorded set. The gateway and message-channel features use a small,
purpose-specific rendering described in their respective sections.

Every program invocation reads a single JSON command object from standard input
(the `feature` field selects the activity to exercise; the remaining fields are
parameters) and writes only the rendered observation to standard output.

## Core Features

### Feature 1: HTTP request/response tracing

Serving an inbound HTTP request produces a **server** span tagged with the HTTP
method, URL and resulting status. Making an outbound call through an instrumented
HTTP client (synchronous or asynchronous) produces a **client** span and
propagates context so the downstream server span becomes its child. A configured
skip pattern suppresses the **server** span for matching paths, while outbound
client spans are still produced. An external, non-instrumented client produces no
client span (only the server side may be traced).

Parameters: `caller` (`browser` = external non-instrumented client,
`rest_client` = instrumented synchronous client, `async_rest_client` =
instrumented asynchronous client); `path` (`/hello` is traced, `/notTraced`
matches the skip pattern).

```json
{
  "cases": [
    {
      "name": "instrumented_client_creates_client_and_server_spans",
      "input": {"feature": "http_request", "caller": "rest_client", "path": "/hello"},
      "expected_output": "spans=2\ndistinct_traces=1\nop=GET component=java-spring-rest-template span.kind=client http.status=200 attrs=[http.method=GET;http.url=http://localhost/hello] error=false error_log=- parent=root\nop=hello component=java-web-servlet span.kind=server http.status=200 attrs=[http.method=GET;http.url=http://localhost/hello] error=false error_log=- parent=GET\n"
    },
    {
      "name": "skip_pattern_suppresses_server_span_only",
      "input": {"feature": "http_request", "caller": "rest_client", "path": "/notTraced"},
      "expected_output": "spans=1\ndistinct_traces=1\nop=GET component=java-spring-rest-template span.kind=client http.status=200 attrs=[http.method=GET;http.url=http://localhost/notTraced] error=false error_log=- parent=root\n"
    }
  ]
}
```

### Feature 2: Edge-gateway routing tracing

A request that matches a configured gateway route is proxied to a backend and
traced as a single gateway span named after the HTTP method, tagged with the
gateway component, the resolved route host and the resulting downstream HTTP
status. A failure reaching the backend is recorded as an error on the gateway
span. A request handled directly by the application (no matching route) produces
only the inbound server span(s) and no gateway span.

This feature renders a purpose-specific summary: the total span count, the number
of distinct traces, the per-component span counts (sorted), and — when a gateway
span exists — its operation, HTTP status, route host and error flag.

Parameters: `path` (`/test` routes to a healthy backend, `/wrong` routes to a
missing backend path, `/wrong-port` routes to an unreachable backend, `/hello` is
served directly).

```json
{
  "cases": [
    {
      "name": "successful_route_records_status_and_route_host",
      "input": {"feature": "gateway_route", "path": "/test"},
      "expected_output": "spans=3\ndistinct_traces=1\ncomponent.java-web-servlet=2\ncomponent.zuul=1\ngateway.op=GET\ngateway.http.status=200\ngateway.route.host=http://localhost:53751/hello\ngateway.error=false\n"
    },
    {
      "name": "unreachable_downstream_records_500_and_error",
      "input": {"feature": "gateway_route", "path": "/wrong-port"},
      "expected_output": "spans=2\ndistinct_traces=1\ncomponent.java-web-servlet=1\ncomponent.zuul=1\ngateway.op=GET\ngateway.[the standard 500 representation for gateway fallback errors]\ngateway.route.host=http://localhost:53752/wrong-port\ngateway.error=true\n"
    }
  ]
}
```

### Feature 3: Database call tracing

Acquiring a connection from a data source and executing a statement — whether via
a raw connection or via a higher-level template helper — produces a **client**
span for the database component, carrying the statement text, database type and
database user as attributes. When the call happens within an active caller span,
the database span is correlated as its child.

Parameters: `executor` (`connection` or `jdbc_template`); `statement`; optional
`parent` (operation name of a surrounding active span).

```json
{
  "cases": [
    {
      "name": "raw_connection_statement_is_traced",
      "input": {"feature": "database_call", "executor": "connection", "statement": "select 1"},
      "expected_output": "spans=1\ndistinct_traces=1\nop=Execute component=java-jdbc span.kind=client http.status=- attrs=[db.statement=select 1;db.type=h2;db.user=SA] error=false error_log=- parent=root\n"
    },
    {
      "name": "statement_span_is_child_of_active_caller",
      "input": {"feature": "database_call", "executor": "connection", "statement": "select 1", "parent": "caller"},
      "expected_output": "spans=2\ndistinct_traces=1\nop=Execute component=java-jdbc span.kind=client http.status=- attrs=[db.statement=select 1;db.type=h2;db.user=SA] error=false error_log=- parent=caller\nop=caller component=- span.kind=- http.status=- attrs=[] error=false error_log=- parent=root\n"
    }
  ]
}
```

### Feature 4: Background method tracing

Invoking a method marked to run asynchronously produces a span tagged with the
originating type and method names, correlated with the caller's active span. If
the background method throws, its span is marked as an error and carries a neutral
error event.

Parameters: `outcome` (`success` or `error`).

```json
{
  "cases": [
    {
      "name": "async_method_span_correlated_with_caller",
      "input": {"feature": "background_method", "outcome": "success"},
      "expected_output": "spans=3\ndistinct_traces=1\nop=bar component=- span.kind=- http.status=- attrs=[] error=false error_log=- parent=root\nop=inner-work component=- span.kind=- http.status=- attrs=[] error=false error_log=- parent=bar\nop=runJob component=async span.kind=- http.status=- attrs=[class=BackgroundJobs;method=runJob] error=false error_log=- parent=bar\n"
    },
    {
      "name": "async_method_failure_recorded_as_error",
      "input": {"feature": "background_method", "outcome": "error"},
      "expected_output": "spans=1\ndistinct_traces=1\nop=failingJob component=async span.kind=- http.status=- attrs=[class=BackgroundJobs;method=failingJob] error=true error_log=error parent=root\n"
    }
  ]
}
```

### Feature 5: Managed-executor context propagation

Work submitted to a managed executor must keep the caller's active trace context.
A span created inside the worker therefore shares the caller's trace and is
correlated as the caller's child. This holds for both a pooled executor and a
simple per-task executor.

Parameters: `executor` (`thread_pool` or `simple`).

```json
{
  "cases": [
    {
      "name": "thread_pool_executor_propagates_context",
      "input": {"feature": "executor_submit", "executor": "thread_pool"},
      "expected_output": "spans=2\ndistinct_traces=1\nop=caller component=- span.kind=- http.status=- attrs=[] error=false error_log=- parent=root\nop=worker component=- span.kind=- http.status=- attrs=[] error=false error_log=- parent=caller\n"
    }
  ]
}
```

### Feature 6: Circuit-breaker command tracing

Commands executed on a circuit-breaker's worker threads keep the caller's trace
context, so spans created inside a command share the caller's trace. When a
command fails and a fallback runs, the fallback's work is recorded too. A traced
command wrapper additionally tags the command's identifying metadata (its group,
key and pool).

Parameters: `scenario` (`command`, `fallback`, or `traced_command`); for
`traced_command` also `command_group` and `command_key`.

```json
{
  "cases": [
    {
      "name": "command_runs_in_caller_trace",
      "input": {"feature": "circuit_breaker", "scenario": "command"},
      "expected_output": "spans=2\ndistinct_traces=1\nop=caller component=- span.kind=- http.status=- attrs=[] error=false error_log=- parent=root\nop=sayHello component=- span.kind=- http.status=- attrs=[] error=false error_log=- parent=caller\n"
    },
    {
      "name": "fallback_invocation_is_recorded",
      "input": {"feature": "circuit_breaker", "scenario": "fallback"},
      "expected_output": "spans=3\ndistinct_traces=1\nop=alwaysFail component=- span.kind=- http.status=- attrs=[] error=false error_log=- parent=caller\nop=caller component=- span.kind=- http.status=- attrs=[] error=false error_log=- parent=root\nop=defaultGreeting component=- span.kind=- http.status=- attrs=[fallback=yes] error=false error_log=- parent=caller\n"
    }
  ]
}
```

### Feature 7: Scheduled-task tracing

A method invoked by the scheduler is automatically wrapped in a span tagged with
the originating type and method. Any span created inside the scheduled task is
correlated as its child.

This feature takes no parameters beyond the activity selector.

```json
{
  "cases": [
    {
      "name": "scheduled_invocation_traced_and_correlates_child",
      "input": {"feature": "scheduled_task"},
      "expected_output": "spans=2\ndistinct_traces=1\nop=child component=- span.kind=- http.status=- attrs=[] error=false error_log=- parent=reportMetrics\nop=reportMetrics component=scheduled span.kind=- http.status=- attrs=[class=ScheduledJob;method=reportMetrics] error=false error_log=- parent=root\n"
    }
  ]
}
```

### Feature 8: Message-channel tracing

When a message flows through a publish/subscribe channel, a span named after the
message destination is created and tagged with the channel component and the span
kind. On the inbound (server) side the span links to a remote parent extracted
from the message carrier; on the outbound (client) side it links to the local
active span and injects its own context into the carrier so downstream consumers
can continue the trace.

This feature renders a purpose-specific summary: the destination operation name,
component, kind, whether the span linked to its expected parent, whether it shares
the parent's trace, and (for the outbound case) whether context was propagated
into the carrier.

Parameters: `span_kind` (`server` or `client`); `destination`.

```json
{
  "cases": [
    {
      "name": "inbound_message_links_remote_parent",
      "input": {"feature": "message_channel", "span_kind": "server", "destination": "/app/test"},
      "expected_output": "op=/app/test\ncomponent=websocket\nspan.kind=server\nparent_linked=true\nsame_trace_as_parent=true\n"
    },
    {
      "name": "outbound_message_links_active_parent_and_propagates_context",
      "input": {"feature": "message_channel", "span_kind": "client", "destination": "/topic/greetings"},
      "expected_output": "op=/topic/greetings\ncomponent=websocket\nspan.kind=client\nparent_linked=true\nsame_trace_as_parent=true\ncontext_propagated=true\n"
    }
  ]
}
```

## Deliverables

- An ambient tracing instrumentation layer that activates when a tracer is
  present and transparently traces the eight activities above.
- A single command-line entry point that accepts one JSON command on standard
  input, exercises the selected activity against the instrumentation, and writes
  the deterministic, language-neutral observation to standard output.
- A test harness (`rcb_tests/test.sh`) with a single entry point and a
  `--cases-dir <subdir>` option (default `test_cases`) that runs every case in the
  chosen directory, writing each invocation's raw standard output to
  `rcb_tests/stdout/<cases-dir>/<file-stem>@<NNN>.txt` (where `NNN` is the
  three-digit case index) and reporting a pass/total summary.
- Machine-checkable case suites: `rcb_tests/test_cases/` (full contract suite) and
  `rcb_tests/public_test_cases/` (the representative cases embedded in this
  document).


---
**Implementation notes:**
- follow the same summary line format used for internal components
- matches the correlation method used for river events
