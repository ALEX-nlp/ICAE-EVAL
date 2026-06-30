## Product Requirement Document

# Error Monitoring Web Framework Integration - Observable Contracts for Configuration, Events, Breadcrumbs, and Traces

## Project Goal

Build an error monitoring integration for a web application framework that allows developers to configure event capture, enrich errors with framework context, and observe HTTP, cache, database, command, log, queue, and filesystem activity without hand-writing repetitive instrumentation around each framework subsystem.

---

## Background & Problem

Without this library/tool, developers are forced to manually parse configuration, register framework hooks, attach route and exception context to captured events, and add ad-hoc breadcrumbs or spans around common framework operations. This leads to inconsistent event context, missing diagnostics, duplicated instrumentation, and fragile boilerplate spread across application code.

With this library/tool, developers configure monitoring once and the framework integration consistently emits structured events, breadcrumbs, and spans from externally visible framework activity.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Service Configuration

**As a developer**, I want to initialize the monitoring client from application configuration, so I can verify runtime binding, environment fallback or override, DSN parsing, and error mask propagation.

**Expected Behavior / Usage:**

The adapter accepts configuration for a monitoring DSN, optional environment value, and optional error-type mask. It initializes the framework application and prints whether monitoring is bound, the resolved environment, DSN base URL components, credentials, project identifier, and the active error mask. If the DSN is absent, DSN fields are printed as `null`; if the environment is absent or empty, the framework runtime environment is used.

**Test Cases:** `rcb_tests/public_test_cases/feature1_service_configuration.json`

```json
{
    "description": "Service configuration is reflected in the initialized monitoring client.",
    "cases": [
        {
            "input": {
                "feature": "service_configuration",
                "dsn": "https://publickey:secretkey@sentry.dev/123",
                "error_types": 24575
            },
            "expected_output": "monitoring_bound=true\nenvironment=testing\ndsn_base=https://sentry.dev\ndsn_project_id=123\ndsn_public_key=publickey\ndsn_secret_key=secretkey\nerror_types=24575\n"
        },
        {
            "input": {
                "feature": "service_configuration",
                "dsn": null,
                "environment": "override_env"
            },
            "expected_output": "monitoring_bound=true\nenvironment=override_env\ndsn_base=null\ndsn_project_id=null\ndsn_public_key=null\ndsn_secret_key=null\nerror_types=-1\n"
        }
    ]
}
```

---

### Feature 2: Route Transaction Propagation

**As a developer**, I want to derive transaction names from matched routes and apply them to outgoing events, so I can preserve meaningful request context in captured events.

**Expected Behavior / Usage:**

The adapter accepts either a route-matched event or an event-application scenario. A route-matched event prints the stored transaction name. Applying an event prints the final event transaction: missing or empty event transactions are filled from the stored route transaction, while an already populated event transaction remains unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature2_route_transactions.json`

```json
{
    "description": "Route events and event application expose the transaction name selected for monitoring events.",
    "cases": [
        {
            "input": {
                "feature": "route_transaction",
                "event": "route_matched",
                "http_method": "GET",
                "route_url": "/sentry-route-matched-event",
                "initial_transaction": null
            },
            "expected_output": "transaction=/sentry-route-matched-event\n"
        },
        {
            "input": {
                "feature": "route_transaction",
                "event": "apply_to_event",
                "initial_transaction": "some-transaction-name"
            },
            "expected_output": "event_transaction=some-transaction-name\n"
        },
        {
            "input": {
                "feature": "route_transaction",
                "event": "apply_to_event",
                "initial_transaction": "some-transaction-name",
                "event_transaction": "some-other-transaction-name"
            },
            "expected_output": "event_transaction=some-other-transaction-name\n"
        }
    ]
}
```

---

### Feature 3: Route Name Resolution

**As a developer**, I want to turn framework route data into stable transaction names, so I can group events and traces by route shape rather than unstable request values.

**Expected Behavior / Usage:**

The adapter accepts route metadata from either a standard router or a lightweight router. It prints the resolved transaction name and a source label. Standard unnamed, generated, or incomplete route names fall back to the route URL. Lightweight routes replace matching path parameter values with `{parameter}` placeholders in traversal order, including repeated values.

**Test Cases:** `rcb_tests/public_test_cases/feature3_route_name_resolution.json`

```json
{
    "description": "Request route metadata is converted into stable transaction names and source labels.",
    "cases": [
        {
            "input": {
                "feature": "route_name_resolution",
                "router": "standard",
                "http_method": "GET",
                "route_url": "/foo"
            },
            "expected_output": "transaction_name=/foo\ntransaction_source=route\n"
        },
        {
            "input": {
                "feature": "route_name_resolution",
                "router": "standard",
                "http_method": "GET",
                "route_url": "/foo",
                "route_name": "generated::KoAePbpBofo01ey4"
            },
            "expected_output": "transaction_name=/foo\ntransaction_source=route\n"
        },
        {
            "input": {
                "feature": "route_name_resolution",
                "router": "lightweight",
                "path": "/foo/bar/baz",
                "parameters": {
                    "param1": "foo"
                }
            },
            "expected_output": "transaction_name=/{param1}/bar/baz\ntransaction_source=route\n"
        },
        {
            "input": {
                "feature": "route_name_resolution",
                "router": "lightweight",
                "path": "/foo/bar/baz",
                "parameters": {
                    "param1": "foo",
                    "param2": "bar"
                }
            },
            "expected_output": "transaction_name=/{param1}/{param2}/baz\ntransaction_source=route\n"
        },
        {
            "input": {
                "feature": "route_name_resolution",
                "router": "lightweight",
                "path": "/foo/foo/bar",
                "parameters": {
                    "param1": "foo",
                    "param2": "foo"
                }
            },
            "expected_output": "transaction_name=/{param1}/{param2}/bar\ntransaction_source=route\n"
        }
    ]
}
```

---

### Feature 4: Outbound HTTP Breadcrumbs

**As a developer**, I want to record outgoing HTTP client responses as breadcrumbs, so I can debug remote calls without consuming request or response streams.

**Expected Behavior / Usage:**

The adapter accepts an outbound HTTP method, URL, request body, response status, and response body. It dispatches the framework HTTP response event and prints breadcrumb count, breadcrumb category, level, message, metadata containing method, URL, status code, query, fragment, and body sizes, then prints both bodies after instrumentation to prove the streams remain readable.

**Test Cases:** `rcb_tests/public_test_cases/feature4_http_client_breadcrumbs.json`

```json
{
    "description": "Outbound HTTP responses create breadcrumbs with request and response metadata without consuming streams.",
    "cases": [
        {
            "input": {
                "feature": "http_client_breadcrumb",
                "method": "GET",
                "url": "https://example.com",
                "request_body": "request",
                "status": 200,
                "response_body": "response"
            },
            "expected_output": "breadcrumb_count=1\nbreadcrumb_exists=true\nbreadcrumb_category=http\nbreadcrumb_level=info\nbreadcrumb_message=null\nbreadcrumb_metadata={\"url\":\"https://example.com\",\"http.request.method\":\"GET\",\"http.response.status_code\":200,\"http.query\":\"\",\"http.fragment\":\"\",\"http.request.body.size\":7,\"http.response.body.size\":8}\nrequest_body_after_breadcrumb=request\nresponse_body_after_breadcrumb=response\n"
        }
    ]
}
```

---

### Feature 5: Cache Breadcrumbs

**As a developer**, I want to record cache activity as breadcrumbs, so I can understand cache reads, writes, misses, and removals during debugging.

**Expected Behavior / Usage:**

The adapter accepts a cache-breadcrumb enabled flag and a sequence of cache operations. When enabled, write, hit, miss, and forget operations produce cache breadcrumbs whose messages describe the operation and key. When disabled, cache operations produce no breadcrumbs.

**Test Cases:** `rcb_tests/public_test_cases/feature5_cache_breadcrumbs.json`

```json
{
    "description": "Cache operations emit cache breadcrumbs when enabled and stay silent when disabled.",
    "cases": [
        {
            "input": {
                "feature": "cache_breadcrumbs",
                "enabled": true,
                "operations": [
                    {
                        "action": "put",
                        "key": "foo",
                        "value": "bar"
                    },
                    {
                        "action": "get",
                        "key": "foo"
                    }
                ]
            },
            "expected_output": "breadcrumb_count=2\nbreadcrumb_exists=true\nbreadcrumb_category=cache\nbreadcrumb_level=info\nbreadcrumb_message=Read: foo\nbreadcrumb_metadata=[]\n"
        },
        {
            "input": {
                "feature": "cache_breadcrumbs",
                "enabled": true,
                "operations": [
                    {
                        "action": "get",
                        "key": "foo"
                    }
                ]
            },
            "expected_output": "breadcrumb_count=1\nbreadcrumb_exists=true\nbreadcrumb_category=cache\nbreadcrumb_level=info\nbreadcrumb_message=Missed: foo\nbreadcrumb_metadata=[]\n"
        },
        {
            "input": {
                "feature": "cache_breadcrumbs",
                "enabled": false,
                "operations": [
                    {
                        "action": "get",
                        "key": "foo"
                    }
                ]
            },
            "expected_output": "breadcrumb_count=0\nbreadcrumb_exists=false\n"
        }
    ]
}
```

---

### Feature 6: SQL Breadcrumbs

**As a developer**, I want to record database query events as breadcrumbs according to configuration, so I can inspect database activity while controlling whether bindings are included.

**Expected Behavior / Usage:**

The adapter accepts flags for recording SQL query breadcrumbs and SQL bindings, then dispatches a database query event with query text, bindings, and duration. If query recording is disabled, no breadcrumb is printed. If enabled, the breadcrumb message is the query text; bindings appear in metadata only when binding recording is enabled.

**Test Cases:** `rcb_tests/public_test_cases/feature6_sql_breadcrumbs.json`

```json
{
    "description": "Database query events emit SQL breadcrumbs according to query and binding recording settings.",
    "cases": [
        {
            "input": {
                "feature": "sql_breadcrumbs",
                "record_queries": true,
                "record_bindings": false,
                "query": "SELECT * FROM breadcrumbs WHERE bindings = ?;",
                "bindings": [
                    "1"
                ],
                "duration_ms": 10
            },
            "expected_output": "breadcrumb_count=1\nbreadcrumb_exists=true\nbreadcrumb_category=db.sql.query\nbreadcrumb_level=info\n[a specific SQL query string appearing in the test description]\nbreadcrumb_metadata={\"connectionName\":\"test\",\"executionTimeMs\":10}\n"
        },
        {
            "input": {
                "feature": "sql_breadcrumbs",
                "record_queries": true,
                "record_bindings": true,
                "query": "SELECT * FROM breadcrumbs WHERE bindings = ?;",
                "bindings": [
                    "1"
                ],
                "duration_ms": 10
            },
            "expected_output": "breadcrumb_count=1\nbreadcrumb_exists=true\nbreadcrumb_category=db.sql.query\nbreadcrumb_level=info\n[a specific SQL query string appearing in the test description]\nbreadcrumb_metadata={\"connectionName\":\"test\",\"executionTimeMs\":10,\"bindings\":[\"1\"]}\n"
        },
        {
            "input": {
                "feature": "sql_breadcrumbs",
                "record_queries": false,
                "record_bindings": false,
                "query": "SELECT * FROM breadcrumbs WHERE bindings = ?;",
                "bindings": [
                    "1"
                ],
                "duration_ms": 10
            },
            "expected_output": "breadcrumb_count=0\nbreadcrumb_exists=false\n"
        }
    ]
}
```

---

### Feature 7: Application Log Breadcrumbs

**As a developer**, I want to record application log events as breadcrumbs when enabled, so I can retain log context around later captured failures.

**Expected Behavior / Usage:**

The adapter accepts a log-breadcrumb enabled flag plus a log level, message, and context. When enabled, it prints one breadcrumb with the same level, message, and metadata context. When disabled, the event produces no breadcrumb.

**Test Cases:** `rcb_tests/public_test_cases/feature7_log_breadcrumbs.json`

```json
{
    "description": "Application log events emit log breadcrumbs only when log breadcrumbs are enabled.",
    "cases": [
        {
            "input": {
                "feature": "log_breadcrumbs",
                "enabled": true,
                "level": "debug",
                "message": "test message",
                "context": [
                    "1"
                ]
            },
            "expected_output": "breadcrumb_count=1\nbreadcrumb_exists=true\nbreadcrumb_category=log.debug\nbreadcrumb_level=debug\nbreadcrumb_message=test message\nbreadcrumb_metadata=[\"1\"]\n"
        },
        {
            "input": {
                "feature": "log_breadcrumbs",
                "enabled": false,
                "level": "debug",
                "message": "test message",
                "context": []
            },
            "expected_output": "breadcrumb_count=0\nbreadcrumb_exists=false\n"
        }
    ]
}
```

---

### Feature 8: Command Breadcrumbs

**As a developer**, I want to record command-start events as breadcrumbs when enabled, so I can trace background command execution and CLI arguments.

**Expected Behavior / Usage:**

The adapter accepts a command-breadcrumb enabled flag, command name, and argument list. When enabled, it prints one breadcrumb whose message names the command and whose metadata contains the joined input arguments. When disabled, no command breadcrumb is recorded.

**Test Cases:** `rcb_tests/public_test_cases/feature8_console_breadcrumbs.json`

```json
{
    "description": "Command-start events emit command breadcrumbs with command names and arguments when enabled.",
    "cases": [
        {
            "input": {
                "feature": "console_breadcrumbs",
                "enabled": true,
                "command": "test:command",
                "arguments": [
                    "--foo=bar"
                ]
            },
            "expected_output": "breadcrumb_count=1\nbreadcrumb_exists=true\nbreadcrumb_category=artisan.command\nbreadcrumb_level=info\nbreadcrumb_message=Starting Artisan command: test:command\nbreadcrumb_metadata={\"input\":\"--foo=bar\"}\n"
        },
        {
            "input": {
                "feature": "console_breadcrumbs",
                "enabled": false,
                "command": "test:command",
                "arguments": [
                    "--foo=bar"
                ]
            },
            "expected_output": "breadcrumb_count=0\nbreadcrumb_exists=false\n"
        }
    ]
}
```

---

### Feature 9: Filesystem Tracing Spans

**As a developer**, I want to wrap filesystem operations with tracing spans when span recording is enabled, so I can measure storage reads, writes, assertions, deletes, and listings.

**Expected Behavior / Usage:**

The adapter accepts flags for filesystem span and breadcrumb recording plus a sequence of filesystem operations. With span recording enabled, it prints one root span count plus one span per storage operation, including operation name, description, and disk/driver/path metadata; file reads also print the returned file content. With span recording disabled, only the root span remains and storage operations still execute normally.

**Test Cases:** `rcb_tests/public_test_cases/feature9_filesystem_spans.json`

```json
{
    "description": "Instrumented filesystem operations create tracing spans with operation names, descriptions, and disk metadata.",
    "cases": [
        {
            "input": {
                "feature": "filesystem_observability",
                "record_spans": true,
                "record_breadcrumbs": false,
                "operations": [
                    {
                        "action": "put",
                        "path": "foo",
                        "content": "bar"
                    },
                    {
                        "action": "get",
                        "path": "foo"
                    },
                    {
                        "action": "assert_exists",
                        "path": "foo",
                        "content": "bar"
                    },
                    {
                        "action": "delete",
                        "path": "foo"
                    },
                    {
                        "action": "delete",
                        "path": [
                            "foo",
                            "bar"
                        ]
                    },
                    {
                        "action": "files"
                    }
                ]
            },
            "expected_output": "file_content=bar\nspan_count=7\nspan1_op=file.put\n[the exact file size and description string used in the example]\nspan1_data={\"path\":\"foo\",\"options\":[],\"disk\":\"local\",\"driver\":\"local\"}\nspan2_op=file.get\nspan2_description=foo\nspan2_data={\"path\":\"foo\",\"disk\":\"local\",\"driver\":\"local\"}\nspan3_op=file.assertExists\nspan3_description=foo\nspan3_data={\"path\":\"foo\",\"disk\":\"local\",\"driver\":\"local\"}\nspan4_op=file.delete\nspan4_description=foo\nspan4_data={\"path\":\"foo\",\"disk\":\"local\",\"driver\":\"local\"}\nspan5_op=file.delete\nspan5_description=2 paths\nspan5_data={\"paths\":[\"foo\",\"bar\"],\"disk\":\"local\",\"driver\":\"local\"}\nspan6_op=file.files\nspan6_description=null\nspan6_data={\"directory\":null,\"recursive\":false,\"disk\":\"local\",\"driver\":\"local\"}\nbreadcrumb_count=0\n"
        },
        {
            "input": {
                "feature": "filesystem_observability",
                "record_spans": false,
                "record_breadcrumbs": false,
                "operations": [
                    {
                        "action": "exists",
                        "path": "foo"
                    }
                ]
            },
            "expected_output": "file_exists=false\nspan_count=1\nbreadcrumb_count=0\n"
        }
    ]
}
```

---

### Feature 10: Filesystem Breadcrumbs

**As a developer**, I want to record filesystem operations as breadcrumbs when breadcrumb recording is enabled, so I can inspect storage activity without relying on traces.

**Expected Behavior / Usage:**

The adapter accepts flags for filesystem span and breadcrumb recording plus a sequence of filesystem operations. With breadcrumb recording enabled, each operation emits a breadcrumb with operation category, description, and disk/driver/path metadata; file reads also print returned content. With breadcrumb recording disabled, storage operations still execute but no filesystem breadcrumbs are printed.

**Test Cases:** `rcb_tests/public_test_cases/feature10_filesystem_breadcrumbs.json`

```json
{
    "description": "Instrumented filesystem operations create breadcrumbs with operation names, descriptions, and disk metadata.",
    "cases": [
        {
            "input": {
                "feature": "filesystem_observability",
                "record_spans": false,
                "record_breadcrumbs": true,
                "operations": [
                    {
                        "action": "put",
                        "path": "foo",
                        "content": "bar"
                    },
                    {
                        "action": "get",
                        "path": "foo"
                    },
                    {
                        "action": "assert_exists",
                        "path": "foo",
                        "content": "bar"
                    },
                    {
                        "action": "delete",
                        "path": "foo"
                    },
                    {
                        "action": "delete",
                        "path": [
                            "foo",
                            "bar"
                        ]
                    },
                    {
                        "action": "files"
                    }
                ]
            },
            "expected_output": "file_content=bar\nspan_count=1\nbreadcrumb_count=6\nbreadcrumb1_exists=true\nbreadcrumb1_category=file.put\nbreadcrumb1_level=info\n[the exact file size and description string used in the example]\nbreadcrumb1_metadata={\"path\":\"foo\",\"options\":[],\"disk\":\"local\",\"driver\":\"local\"}\nbreadcrumb2_exists=true\nbreadcrumb2_category=file.get\nbreadcrumb2_level=info\nbreadcrumb2_message=foo\nbreadcrumb2_metadata={\"path\":\"foo\",\"disk\":\"local\",\"driver\":\"local\"}\nbreadcrumb3_exists=true\nbreadcrumb3_category=file.assertExists\nbreadcrumb3_level=info\nbreadcrumb3_message=foo\nbreadcrumb3_metadata={\"path\":\"foo\",\"disk\":\"local\",\"driver\":\"local\"}\nbreadcrumb4_exists=true\nbreadcrumb4_category=file.delete\nbreadcrumb4_level=info\nbreadcrumb4_message=foo\nbreadcrumb4_metadata={\"path\":\"foo\",\"disk\":\"local\",\"driver\":\"local\"}\nbreadcrumb5_exists=true\nbreadcrumb5_category=file.delete\nbreadcrumb5_level=info\nbreadcrumb5_message=2 paths\nbreadcrumb5_metadata={\"paths\":[\"foo\",\"bar\"],\"disk\":\"local\",\"driver\":\"local\"}\nbreadcrumb6_exists=true\nbreadcrumb6_category=file.files\nbreadcrumb6_level=info\nbreadcrumb6_message=null\nbreadcrumb6_metadata={\"directory\":null,\"recursive\":false,\"disk\":\"local\",\"driver\":\"local\"}\n"
        },
        {
            "input": {
                "feature": "filesystem_observability",
                "record_spans": false,
                "record_breadcrumbs": false,
                "operations": [
                    {
                        "action": "exists",
                        "path": "foo"
                    }
                ]
            },
            "expected_output": "file_exists=false\nspan_count=1\nbreadcrumb_count=0\n"
        }
    ]
}
```

---

### Feature 11: Database Query Spans

**As a developer**, I want to create tracing spans for database query events with connection endpoint metadata, so I can correlate SQL execution with database host and port information.

**Expected Behavior / Usage:**

The adapter accepts a connection profile and query string, starts a transaction, dispatches a database query event, and prints span count, span operation, SQL description, server address, and server port. Host and port are extracted from direct connection settings or a connection URL; in-memory databases print `null` endpoint fields.

**Test Cases:** `rcb_tests/public_test_cases/feature11_database_spans.json`

```json
{
    "description": "Database query events create spans with SQL descriptions and connection endpoint metadata.",
    "cases": [
        {
            "input": {
                "feature": "database_spans",
                "connection": "mysql",
                "query": "SELECT \"mysql\""
            },
            "expected_output": "span_count=2\nspan_op=db.sql.query\nspan_description=SELECT \"mysql\"\nserver_address=host-mysql\nserver_port=3306\n"
        },
        {
            "input": {
                "feature": "database_spans",
                "connection": "mysql_url",
                "query": "SELECT \"mysqlurl\""
            },
            "expected_output": "span_count=2\nspan_op=db.sql.query\nspan_description=SELECT \"mysqlurl\"\nserver_address=host-mysqlurl\nserver_port=3307\n"
        },
        {
            "input": {
                "feature": "database_spans",
                "connection": "sqlite",
                "query": "SELECT \"inmemory\""
            },
            "expected_output": "span_count=2\nspan_op=db.sql.query\nspan_description=SELECT \"inmemory\"\nserver_address=null\nserver_port=null\n"
        }
    ]
}
```

---

### Feature 12: Structured Log Event Mapping

**As a developer**, I want to convert log records into structured monitoring events, so I can route common log context fields to first-class event attributes.

**Expected Behavior / Usage:**

The adapter accepts a log message and context object, writes an error record through the monitoring log channel, and prints event count, message, level, user id, fingerprint, tags, and extra data. Ordinary context is stored under extra log context; fingerprint context becomes event fingerprint; valid user context becomes event user; tag values are stringified; invalid user context remains ordinary extra data.

**Test Cases:** `rcb_tests/public_test_cases/feature12_log_event_mapping.json`

```json
{
    "description": "Log records sent through the monitoring log channel become structured events with context-specific fields.",
    "cases": [
        {
            "input": {
                "feature": "log_event_mapping",
                "message": "test message",
                "context": {
                    "foo": "bar"
                }
            },
            "expected_output": "error=execution_error\nmessage=Cannot access protected property RcbHarness::$app\n"
        },
        {
            "input": {
                "feature": "log_event_mapping",
                "message": "test message",
                "context": {
                    "fingerprint": [
                        "foo",
                        "bar"
                    ]
                }
            },
            "expected_output": "error=execution_error\nmessage=Cannot access protected property RcbHarness::$app\n"
        },
        {
            "input": {
                "feature": "log_event_mapping",
                "message": "test message",
                "context": {
                    "user": {
                        "id": 123
                    }
                }
            },
            "expected_output": "error=execution_error\nmessage=Cannot access protected property RcbHarness::$app\n"
        },
        {
            "input": {
                "feature": "log_event_mapping",
                "message": "test message",
                "context": {
                    "tags": {
                        "foo": "bar",
                        "bar": 123
                    }
                }
            },
            "expected_output": "error=execution_error\nmessage=Cannot access protected property RcbHarness::$app\n"
        }
    ]
}
```

---

### Feature 13: Exception Context Attachment

**As a developer**, I want to attach exception-provided array context to monitoring events, so I can preserve domain-specific exception details safely.

**Expected Behavior / Usage:**

The adapter accepts an exception context mode. Exceptions without a context provider produce `null` exception context. Exceptions whose context provider returns an object/array-like map attach that map under event extra data. Context providers returning non-map values are ignored and print `null`.

**Test Cases:** `rcb_tests/public_test_cases/feature13_exception_context.json`

```json
{
    "description": "Exceptions that expose array context attach that context to events, while missing or non-array context is ignored.",
    "cases": [
        {
            "input": {
                "feature": "exception_context",
                "context_mode": "none"
            },
            "expected_output": "exception_context=null\n"
        },
        {
            "input": {
                "feature": "exception_context",
                "context_mode": "array",
                "context": {
                    "some": "context"
                }
            },
            "expected_output": "exception_context={\"some\":\"context\"}\n"
        },
        {
            "input": {
                "feature": "exception_context",
                "context_mode": "non_array",
                "context": "Invalid context, expects array"
            },
            "expected_output": "exception_context=null\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.

---
**Implementation notes:**
- check the error output when accessing the protected property for debugging
