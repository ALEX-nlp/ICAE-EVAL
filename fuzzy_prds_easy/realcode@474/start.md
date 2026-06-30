## Product Requirement Document

# Dependency-Injected HTTP Resource Service - Behavioral Specification

## Project Goal

Build an HTTP web service whose endpoint handlers are plain objects assembled by a dependency-injection container, so developers can declare resource classes, their collaborators, and their lifecycles declaratively and have the request-handling framework wire everything together. The service must expose request data (path, query, matrix, header parameters), pluggable collaborator services selected by qualifier, container-managed lifecycles (per-request and application-scoped), producer-supplied values, container extensions, exception translation, and response filters — all observable purely over HTTP.

---

## Background & Problem

Without a dependency-injection-aware request framework, developers wiring an HTTP service by hand must manually construct each handler, thread request data into it, look up shared services, manage object lifetimes (a fresh object per request versus one shared for the whole application), and hand-roll error-to-response translation. This produces repetitive, error-prone boilerplate and tightly couples handlers to the machinery that feeds them.

With this service, a handler simply declares what it needs — a path segment, a query value, a qualified collaborator, a produced value, a shared counter — and the container supplies it. The same managed collaborator can be injected into handlers belonging to two independent applications running side by side without their contexts leaking into one another. Lifecycle, qualifier-based selection, producer values, extensions, exception mapping, and response filtering are all configuration concerns the developer declares rather than codes.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has many distinct responsibilities (request-data binding, scoped lifecycles, qualifier-based service selection, producers, extensions, exception translation, response filtering, multi-application hosting), so it MUST be organized as a multi-file, production-grade tree (resource handlers, collaborator services, container configuration, and a separate execution adapter), not a single "god file".

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases in "Core Features" are a **black-box contract for the execution adapter only**, not the internal data model of the service. The core request-handling logic and domain objects MUST be completely decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating a JSON request specification into real HTTP requests against the running service and rendering the observed responses to stdout.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Keep request-data binding, lifecycle management, service selection, exception translation, response filtering, and output formatting in distinct units.
   - **Open/Closed Principle (OCP):** New resource handlers, collaborator implementations, or response filters must be addable without modifying the container core.
   - **Liskov Substitution Principle (LSP):** Every implementation of the echo collaborator interface must be substitutable wherever that interface is injected.
   - **Interface Segregation Principle (ISP):** Collaborator interfaces must be small and cohesive (e.g. a single-method echo service).
   - **Dependency Inversion Principle (DIP):** Handlers depend on collaborator abstractions selected by qualifier, not on concrete implementations or on I/O details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** Handlers and collaborators must read as ordinary classes annotated with their injection and routing intent; the wiring machinery stays hidden.
   - **Resilience:** Domain failures must be modeled as typed exceptions and translated into well-formed HTTP error responses by registered mappers, never surfaced as raw runtime faults.

---

## Core Features

### Feature 1: Constructor Parameter Binding from the Request

**As a developer**, I want a handler to receive request data and a container-produced value through its constructor, so I can build immutable, fully-wired handlers without per-field plumbing.

**Expected Behavior / Usage:**

A handler is registered at a base route that carries a single path segment. The container constructs it for each request, supplying five values: the path segment, the query parameter named `q`, the matrix parameter named `m`, the request header named `Custom-Header`, and a fixed string supplied by a container producer. The path segment also names which of these five values the handler returns as the response body. A request whose path segment is `pathParam`/`queryParam`/`matrixParam`/`headerParam` echoes the correspondingly-bound request value; a path segment of `cdiParam` returns the producer-supplied constant `cdi-produced`. Every successful call returns HTTP 200. The output reports the response status, the fully routed request URL (with matrix and query syntax as sent), and the echoed value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_constructor_param_binding.json`

```json
{
    "description": "A resource is constructed with parameters bound from different parts of the HTTP request (path segment, query string, matrix parameter, request header) plus one value supplied by the container's value provider. The path segment names which bound value the resource should echo back as the response body. Input is a request specification with a path that ends in the name of the value to echo; output reports the response status, the fully routed request URL, and the echoed value.",
    "cases": [
        {
            "input": {"requests": [{"app": "main", "path": "ctor-injected/pathParam"}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/ctor-injected/pathParam\nbody=pathParam"
        },
        {
            "input": {"requests": [{"app": "main", "path": "ctor-injected/queryParam", "query": {"q": "123"}}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/ctor-injected/queryParam?q=123\nbody=123"
        },
        {
            "input": {"requests": [{"app": "main", "path": "ctor-injected/matrixParam", "matrix": {"m": "456"}}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/ctor-injected/matrixParam;m=456\nbody=456"
        },
        {
            "input": {"requests": [{"app": "main", "path": "ctor-injected/headerParam", "headers": {"Custom-Header": "789"}}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/ctor-injected/headerParam\nbody=789"
        },
        {
            "input": {"requests": [{"app": "main", "path": "ctor-injected/cdiParam"}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/ctor-injected/cdiParam\nbody=cdi-produced"
        }
    ]
}
```

---

### Feature 2: Qualifier-Selected Reversing Collaborator

**As a developer**, I want a handler to be injected with a specific implementation of a shared interface chosen by qualifier, so I can swap behavior without changing the handler.

**Expected Behavior / Usage:**

Two implementations of a single-method echo interface exist. A handler at route `reverse` is injected with the implementation qualified as the reversing one and forwards the `s` query parameter to it. The response body is the input string reversed character-by-character. Every call returns HTTP 200. The output reports status, routed URL, and the reversed body.

**Test Cases:** `rcb_tests/public_test_cases/feature2_reverse_echo.json`

```json
{
    "description": "A qualified echo service reverses its input string. The service is selected by a qualifier among multiple implementations of the same echo interface. Input supplies the string to reverse via the `s` query parameter; output reports status, routed URL, and the reversed string as the response body.",
    "cases": [
        {
            "input": {"requests": [{"app": "main", "path": "reverse", "query": {"s": "alpha"}}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/reverse?s=alpha\nbody=ahpla"
        },
        {
            "input": {"requests": [{"app": "main", "path": "reverse", "query": {"s": "gogol"}}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/reverse?s=gogol\nbody=logog"
        },
        {
            "input": {"requests": [{"app": "main", "path": "reverse", "query": {"s": "elcaro"}}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/reverse?s=elcaro\nbody=oracle"
        }
    ]
}
```

---

### Feature 3: Qualifier-Selected Repeating Collaborator (Default Factor)

**As a developer**, I want a different qualified implementation of the same echo interface that repeats its input, so I can demonstrate that qualifier selection yields distinct behavior at the same injection point.

**Expected Behavior / Usage:**

A handler at route `stutter` is injected with the implementation qualified as the repeating one and forwards the `s` query parameter. With the default repeat factor of 2, the response body is the input string concatenated to itself once (doubled). Every call returns HTTP 200. The output reports status, routed URL, and the doubled body.

**Test Cases:** `rcb_tests/public_test_cases/feature3_stutter_echo_default.json`

```json
{
    "description": "A qualified echo service repeats its input string a fixed number of times (default repeat factor is 2). Input supplies the string via the `s` query parameter; output reports status, routed URL, and the doubled string as the response body.",
    "cases": [
        {
            "input": {"requests": [{"app": "main", "path": "stutter", "query": {"s": "alpha"}}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/stutter?s=alpha\nbody=alphaalpha"
        },
        {
            "input": {"requests": [{"app": "main", "path": "stutter", "query": {"s": "gogol"}}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/stutter?s=gogol\nbody=gogolgogol"
        },
        {
            "input": {"requests": [{"app": "main", "path": "stutter", "query": {"s": "elcaro"}}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/stutter?s=elcaro\nbody=elcaroelcaro"
        }
    ]
}
```

---

### Feature 4: Reconfiguring a Shared Collaborator at Runtime

**As a developer**, I want to change a shared collaborator's configuration through its own endpoint and have every handler that depends on it observe the change, so I can prove the collaborator is a single application-scoped instance.

**Expected Behavior / Usage:**

The repeating collaborator exposes its own route `stutter-service-factor`: a PUT whose request body is an integer sets the repeat factor and returns HTTP 204 with an empty body; the separate `stutter` echo route then repeats its input that many times because both routes share one application-scoped collaborator instance. Input is an ordered sequence of requests; the output concatenates each request's status, routed URL, and body, with a blank line between consecutive request renderings.

**Test Cases:** `rcb_tests/public_test_cases/feature4_stutter_factor_set_get.json`

```json
{
    "description": "The repeat factor of the stutter echo service can be reconfigured at runtime through its own HTTP endpoint, and the change is observed by the separate echo endpoint that shares the same application-scoped service instance. Input is a sequence of requests: a PUT that sets the factor (request body is the integer factor, response carries no content), followed by a GET on the echo endpoint. The output concatenates each request's status, routed URL, and body, separated by a blank line. A successful factor update returns status 204 with an empty body; the subsequent echo repeats the `s` query value `factor` times.",
    "cases": [
        {
            "input": {"requests": [
                {"app": "main", "path": "stutter-service-factor", "method": "PUT", "body": "3"},
                {"app": "main", "path": "stutter", "query": {"s": "lincoln"}},
                {"app": "main", "path": "stutter-service-factor", "method": "PUT", "body": "2"},
                {"app": "main", "path": "stutter", "query": {"s": "lincoln"}}
            ]},
            "expected_output": "status=204\nurl=http://localhost:9998/main/stutter-service-factor\nbody=\n\nstatus=200\nurl=http://localhost:9998/main/stutter?s=lincoln\nbody=lincolnlincolnlincoln\n\nstatus=204\nurl=http://localhost:9998/main/stutter-service-factor\nbody=\n\nstatus=200\nurl=http://localhost:9998/main/stutter?s=lincoln\nbody=lincolnlincoln"
        }
    ]
}
```

---

### Feature 5: Per-Request Lifecycle Handlers

**As a developer**, I want handlers that are created fresh for every request, so request-scoped state never bleeds between requests.

**Expected Behavior / Usage:**

*5.1 Per-Request Echo Handler — handler recreated for each request*

A request-scoped handler at route `jcdibean/per-request` is injected with the current request context. Its response body has the form `<request-uri>: queryParam=<x> <n>`, where `<request-uri>` is the full request URL it observed, `<x>` is the `x` query parameter (shown decoded in the body), and `<n>` is a per-instance counter. Because a new instance serves every request, `<n>` is always `0`. Special characters in `x` appear percent-encoded in the routed URL but decoded in the body; a space encodes as `+` in the URL and stays a space in the body. Every call returns HTTP 200. The output reports status, routed URL, and that body.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_per_request_echo.json`

```json
{
    "description": "A request-scoped resource echoes the request context it was injected with: the full request URI, the `x` query parameter, and a per-instance counter that starts at 0. Because the resource is recreated for every request, the counter never advances beyond 0 across separate requests. Input supplies the `x` query parameter; the response body has the form `<request-uri>: queryParam=<x> 0`. Special characters in `x` appear decoded in the body but percent-encoded in the routed URL. Output reports status, routed URL, and that body.",
    "cases": [
        {
            "input": {"requests": [{"app": "main", "path": "jcdibean/per-request", "query": {"x": "alpha"}}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/jcdibean/per-request?x=alpha\nbody=http://localhost:9998/main/jcdibean/per-request?x=alpha: queryParam=alpha 0"
        },
        {
            "input": {"requests": [{"app": "main", "path": "jcdibean/per-request", "query": {"x": "AAA"}}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/jcdibean/per-request?x=AAA\nbody=http://localhost:9998/main/jcdibean/per-request?x=AAA: queryParam=AAA 0"
        },
        {
            "input": {"requests": [{"app": "main", "path": "jcdibean/per-request", "query": {"x": "$%^"}}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/jcdibean/per-request?x=%24%25%5E\nbody=http://localhost:9998/main/jcdibean/per-request?x=%24%25%5E: queryParam=$%^ 0"
        },
        {
            "input": {"requests": [{"app": "main", "path": "jcdibean/per-request", "query": {"x": "a b"}}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/jcdibean/per-request?x=a+b\nbody=http://localhost:9998/main/jcdibean/per-request?x=a+b: queryParam=a b 0"
        }
    ]
}
```

*5.2 Fully-Managed Per-Request Echo Handler — same lifecycle via full container management*

A second request-scoped handler at route `jcdibean/dependent/per-request` behaves identically to 5.1 but is additionally a fully container-managed bean. The response body has the same `<request-uri>: queryParam=<x> 0` form with the same per-request counter reset and the same encoding rules. Every call returns HTTP 200. The output reports status, routed URL, and that body.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_dependent_per_request_echo.json`

```json
{
    "description": "A request-scoped resource that is also a fully container-managed bean echoes the request context it was injected with: the full request URI, the `x` query parameter, and a per-instance counter that starts at 0 and never advances across separate requests. Input supplies the `x` query parameter; the response body has the form `<request-uri>: queryParam=<x> 0`. Output reports status, routed URL, and that body.",
    "cases": [
        {
            "input": {"requests": [{"app": "main", "path": "jcdibean/dependent/per-request", "query": {"x": "alpha"}}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/jcdibean/dependent/per-request?x=alpha\nbody=http://localhost:9998/main/jcdibean/dependent/per-request?x=alpha: queryParam=alpha 0"
        },
        {
            "input": {"requests": [{"app": "main", "path": "jcdibean/dependent/per-request", "query": {"x": "AAA"}}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/jcdibean/dependent/per-request?x=AAA\nbody=http://localhost:9998/main/jcdibean/dependent/per-request?x=AAA: queryParam=AAA 0"
        },
        {
            "input": {"requests": [{"app": "main", "path": "jcdibean/dependent/per-request", "query": {"x": "$%^"}}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/jcdibean/dependent/per-request?x=%24%25%5E\nbody=http://localhost:9998/main/jcdibean/dependent/per-request?x=%24%25%5E: queryParam=$%^ 0"
        },
        {
            "input": {"requests": [{"app": "main", "path": "jcdibean/dependent/per-request", "query": {"x": "a b"}}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/jcdibean/dependent/per-request?x=a+b\nbody=http://localhost:9998/main/jcdibean/dependent/per-request?x=a+b: queryParam=a b 0"
        }
    ]
}
```

---

### Feature 6: Application-Scoped Handler

**As a developer**, I want a single handler instance shared for the whole application, so shared state and a registered exception mapper can be exercised across requests.

**Expected Behavior / Usage:**

*6.1 Application-Scoped Echo — single shared instance echoing request context*

An application-scoped handler at route `jcdibean/singleton/{p}` echoes its injected request context. Its body has the form `<request-uri>: p=<p>, queryParam=<x>`, where `<p>` is the path segment and `<x>` is the `x` query parameter. Every call returns HTTP 200. The output reports status, routed URL, and that body.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_singleton_echo.json`

```json
{
    "description": "An application-scoped resource echoes its injected request context: the full request URI, the `p` path segment, and the `x` query parameter. Input supplies the `p` path segment and `x` query parameter; the response body has the form `<request-uri>: p=<p>, queryParam=<x>`. Output reports status, routed URL, and that body.",
    "cases": [
        {
            "input": {"requests": [{"app": "main", "path": "jcdibean/singleton/alpha", "query": {"x": "beta"}}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/jcdibean/singleton/alpha?x=beta\nbody=http://localhost:9998/main/jcdibean/singleton/alpha?x=beta: p=alpha, queryParam=beta"
        },
        {
            "input": {"requests": [{"app": "main", "path": "jcdibean/singleton/1", "query": {"x": "2"}}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/jcdibean/singleton/1?x=2\nbody=http://localhost:9998/main/jcdibean/singleton/1?x=2: p=1, queryParam=2"
        }
    ]
}
```

*6.2 Application-Scoped Shared Counter — state that persists across requests*

The same application-scoped handler exposes a `counter` sub-route holding an integer. A PUT whose body is an integer sets it and returns HTTP 204 with an empty body; a GET returns the current value (HTTP 200) and then post-increments it. Because one instance serves the whole application, the value persists between requests: after setting 10, successive GETs read 10 then 11; after setting 32, a GET reads 32. The output concatenates each request's status, routed URL, and body, with a blank line between renderings.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_singleton_counter.json`

```json
{
    "description": "An application-scoped resource exposes a shared integer counter via a sub-path that can be read (GET, returns the current value then post-increments) and set (PUT, body is the new integer value, response carries no content). Because the resource lives for the whole application lifetime, the counter persists across requests. Input is a sequence of requests: set to 10, read (returns 10), read again (returns 11), set to 32, read (returns 32). Output concatenates each request's status, routed URL, and body separated by a blank line; a successful set returns status 204 with an empty body.",
    "cases": [
        {
            "input": {"requests": [
                {"app": "main", "path": "jcdibean/singleton/alpha/counter", "query": {"x": "beta"}, "method": "PUT", "body": "10"},
                {"app": "main", "path": "jcdibean/singleton/alpha/counter", "query": {"x": "beta"}},
                {"app": "main", "path": "jcdibean/singleton/alpha/counter", "query": {"x": "beta"}},
                {"app": "main", "path": "jcdibean/singleton/alpha/counter", "query": {"x": "beta"}, "method": "PUT", "body": "32"},
                {"app": "main", "path": "jcdibean/singleton/alpha/counter", "query": {"x": "beta"}}
            ]},
            "expected_output": "status=204\nurl=http://localhost:9998/main/jcdibean/singleton/alpha/counter?x=beta\nbody=\n\nstatus=200\nurl=http://localhost:9998/main/jcdibean/singleton/alpha/counter?x=beta\n[an increasing sequence of integer values — check the expected output log]\n\nstatus=200\nurl=http://localhost:9998/main/jcdibean/singleton/alpha/counter?x=beta\n[an increasing sequence of integer values — check the expected output log]\n\nstatus=204\nurl=http://localhost:9998/main/jcdibean/singleton/alpha/counter?x=beta\nbody=\n\nstatus=200\nurl=http://localhost:9998/main/jcdibean/singleton/alpha/counter?x=beta\n[an increasing sequence of integer values — check the expected output log]"
        }
    ]
}
```

*6.3 Exception Translation — typed failure mapped to an error response*

Requesting the `exception` sub-route of the application-scoped handler raises a domain-specific failure. A registered mapper translates it into an HTTP 500 response whose body is the neutral failure category `JDCIBeanException`. The output reports status 500, the routed URL, and that body.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_singleton_exception.json`

```json
{
    "description": "When the application-scoped resource's exception sub-path is requested, the resource raises a domain-specific exception that is translated by a registered exception mapper into a server-error response whose body names the exception category. Input requests the exception sub-path; output reports status 500, the routed URL, and the body `JDCIBeanException`.",
    "cases": [
        {
            "input": {"requests": [{"app": "main", "path": "jcdibean/singleton/alpha/exception", "query": {"x": "beta"}}]},
            "expected_output": "status=500\nurl=http://localhost:9998/main/jcdibean/singleton/alpha/exception?x=beta\nbody=JDCIBeanException"
        },
        {
            "input": {"requests": [{"app": "main", "path": "jcdibean/singleton/1/exception", "query": {"x": "2"}}]},
            "expected_output": "status=500\nurl=http://localhost:9998/main/jcdibean/singleton/1/exception?x=2\nbody=JDCIBeanException"
        }
    ]
}
```

---

### Feature 7: Fully-Managed Application-Scoped Handler

**As a developer**, I want a second application-scoped handler that is also a fully container-managed bean with its own distinct exception type and mapper, so I can confirm the scoped lifecycle and exception translation also hold under full container management.

**Expected Behavior / Usage:**

*7.1 Managed Application-Scoped Echo — single shared, fully-managed instance*

An application-scoped, fully container-managed handler at route `jcdibean/dependent/singleton/{p}` echoes its request context with the same `<request-uri>: p=<p>, queryParam=<x>` body form. Every call returns HTTP 200. The output reports status, routed URL, and that body.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_dependent_singleton_echo.json`

```json
{
    "description": "An application-scoped resource that is also a fully container-managed bean echoes its injected request context: the full request URI, the `p` path segment, and the `x` query parameter. Input supplies the `p` path segment and `x` query parameter; the response body has the form `<request-uri>: p=<p>, queryParam=<x>`. Output reports status, routed URL, and that body.",
    "cases": [
        {
            "input": {"requests": [{"app": "main", "path": "jcdibean/dependent/singleton/alpha", "query": {"x": "beta"}}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/jcdibean/dependent/singleton/alpha?x=beta\nbody=http://localhost:9998/main/jcdibean/dependent/singleton/alpha?x=beta: p=alpha, queryParam=beta"
        },
        {
            "input": {"requests": [{"app": "main", "path": "jcdibean/dependent/singleton/1", "query": {"x": "2"}}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/jcdibean/dependent/singleton/1?x=2\nbody=http://localhost:9998/main/jcdibean/dependent/singleton/1?x=2: p=1, queryParam=2"
        }
    ]
}
```

*7.2 Managed Application-Scoped Shared Counter — persisting state under full management*

The fully-managed application-scoped handler exposes the same `counter` sub-route semantics: PUT sets (HTTP 204, empty body), GET reads-then-increments (HTTP 200), and the value persists across requests. The output concatenates each request's status, routed URL, and body separated by a blank line.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_dependent_singleton_counter.json`

```json
{
    "description": "An application-scoped managed-bean resource exposes a shared integer counter via a sub-path that can be read (GET, returns the current value then post-increments) and set (PUT, body is the new integer value, response carries no content). The counter persists across requests for the lifetime of the application. Input is a sequence of requests: set to 10, read (10), read (11), set to 32, read (32). Output concatenates each request's status, routed URL, and body separated by a blank line; a successful set returns status 204 with an empty body.",
    "cases": [
        {
            "input": {"requests": [
                {"app": "main", "path": "jcdibean/dependent/singleton/alpha/counter", "query": {"x": "beta"}, "method": "PUT", "body": "10"},
                {"app": "main", "path": "jcdibean/dependent/singleton/alpha/counter", "query": {"x": "beta"}},
                {"app": "main", "path": "jcdibean/dependent/singleton/alpha/counter", "query": {"x": "beta"}},
                {"app": "main", "path": "jcdibean/dependent/singleton/alpha/counter", "query": {"x": "beta"}, "method": "PUT", "body": "32"},
                {"app": "main", "path": "jcdibean/dependent/singleton/alpha/counter", "query": {"x": "beta"}}
            ]},
            "expected_output": "status=204\nurl=http://localhost:9998/main/jcdibean/dependent/singleton/alpha/counter?x=beta\nbody=\n\nstatus=200\nurl=http://localhost:9998/main/jcdibean/dependent/singleton/alpha/counter?x=beta\n[an increasing sequence of integer values — check the expected output log]\n\nstatus=200\nurl=http://localhost:9998/main/jcdibean/dependent/singleton/alpha/counter?x=beta\n[an increasing sequence of integer values — check the expected output log]\n\nstatus=204\nurl=http://localhost:9998/main/jcdibean/dependent/singleton/alpha/counter?x=beta\nbody=\n\nstatus=200\nurl=http://localhost:9998/main/jcdibean/dependent/singleton/alpha/counter?x=beta\n[an increasing sequence of integer values — check the expected output log]"
        }
    ]
}
```

*7.3 Distinct Exception Translation — second typed failure and mapper*

Requesting the `exception` sub-route of the fully-managed application-scoped handler raises a different domain-specific failure, translated by its own registered mapper into an HTTP 500 response whose body is the neutral category `JDCIBeanDependentException`. The output reports status 500, the routed URL, and that body.

**Test Cases:** `rcb_tests/public_test_cases/feature7_3_dependent_singleton_exception.json`

```json
{
    "description": "When the application-scoped managed-bean resource's exception sub-path is requested, the resource raises a distinct domain-specific exception that is translated by its own registered exception mapper into a server-error response whose body names the exception category. Input requests the exception sub-path; output reports status 500, the routed URL, and the body `JDCIBeanDependentException`.",
    "cases": [
        {
            "input": {"requests": [{"app": "main", "path": "jcdibean/dependent/singleton/alpha/exception", "query": {"x": "beta"}}]},
            "expected_output": "status=500\nurl=http://localhost:9998/main/jcdibean/dependent/singleton/alpha/exception?x=beta\nbody=JDCIBeanDependentException"
        },
        {
            "input": {"requests": [{"app": "main", "path": "jcdibean/dependent/singleton/1/exception", "query": {"x": "2"}}]},
            "expected_output": "status=500\nurl=http://localhost:9998/main/jcdibean/dependent/singleton/1/exception?x=2\nbody=JDCIBeanDependentException"
        }
    ]
}
```

---

### Feature 8: Container Extension Injection

**As a developer**, I want a handler injected with a container extension that holds shared state, so I can confirm extensions participate in injection without disrupting routing.

**Expected Behavior / Usage:**

A handler at route `counter` is injected with a shared container extension exposing a monotonically increasing counter. Each GET returns the next integer starting at 1 (1, 2, 3, ...) as the body, with HTTP 200. The output concatenates each request's status, routed URL, and body separated by a blank line, with the second value strictly greater than the first.

**Test Cases:** `rcb_tests/public_test_cases/feature8_extension_counter.json`

```json
{
    "description": "A resource is injected with a shared container extension that exposes a monotonically increasing counter; each GET returns the next integer (1, 2, 3, ...). Input is a sequence of two GET requests; output concatenates each request's status, routed URL, and body separated by a blank line, with the second body strictly greater than the first.",
    "cases": [
        {
            "input": {"requests": [
                {"app": "main", "path": "counter"},
                {"app": "main", "path": "counter"}
            ]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/counter\nbody=1\n\nstatus=200\nurl=http://localhost:9998/main/counter\nbody=2"
        }
    ]
}
```

---

### Feature 9: Producer-Supplied Beans

**As a developer**, I want a handler injected with values supplied by producers (one declared as a field, one as a method), so I can confirm producer-provided objects are injectable alongside routing.

**Expected Behavior / Usage:**

A handler at route `producer` is injected with two producer-supplied beans. Sub-route `f` returns the field-producer's value `field`; sub-route `m` returns the method-producer's value `method`. Each call returns HTTP 200. The output concatenates each request's status, routed URL, and body separated by a blank line.

**Test Cases:** `rcb_tests/public_test_cases/feature9_producer_beans.json`

```json
{
    "description": "A resource is injected with two beans supplied by producers: one produced from a producer field and one from a producer method. Each is exposed on its own sub-path and returns the value the producer assigned. Input requests sub-path `f` (field-produced, value `field`) and sub-path `m` (method-produced, value `method`); output concatenates each request's status, routed URL, and body separated by a blank line.",
    "cases": [
        {
            "input": {"requests": [
                {"app": "main", "path": "producer/f"},
                {"app": "main", "path": "producer/m"}
            ]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/producer/f\nbody=field\n\nstatus=200\nurl=http://localhost:9998/main/producer/m\nbody=method"
        }
    ]
}
```

---

### Feature 10: Two Applications Hosted Side by Side

**As a developer**, I want two independent applications, each under its own base path, to share the same managed-bean type without their request contexts leaking, so I can confirm injection isolation across concurrently-hosted applications.

**Expected Behavior / Usage:**

A request-scoped, container-managed bean carrying request-context injection points is injected into a resource in each of two applications hosted under base paths `/main` and `/secondary`. Each resource exposes a path endpoint that returns the matched relative path and a header endpoint that returns the value of request header `x-test`. The two applications use distinct sub-paths (`.../1` for the first, `.../2` for the second) and must report values from their own request context only.

*10.1 First Application Injection — endpoints under base path `/main`*

Input requests `non-jaxrs-bean-injected/path/1` (returns the relative path) and `non-jaxrs-bean-injected/header/1` with header `x-test` (returns its value). Each returns HTTP 200. The output concatenates each request's status, routed URL, and body separated by a blank line.

**Test Cases:** `rcb_tests/public_test_cases/feature10_1_main_app_injection.json`

```json
{
    "description": "Two independent applications are deployed simultaneously under different base paths (`/main` and `/secondary`). A request-scoped, container-managed bean carrying request-context injection points is injected into a resource in each application; the two applications' injection contexts must remain isolated. This covers the first (main) application: its resource exposes a path endpoint returning the matched relative path, and a header endpoint returning a custom request header value. Input requests `non-jaxrs-bean-injected/path/1` and `non-jaxrs-bean-injected/header/1` (with header `x-test`); output concatenates each request's status, routed URL, and body separated by a blank line.",
    "cases": [
        {
            "input": {"requests": [
                {"app": "main", "path": "non-jaxrs-bean-injected/path/1"},
                {"app": "main", "path": "non-jaxrs-bean-injected/header/1", "headers": {"x-test": "bummer"}}
            ]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/non-jaxrs-bean-injected/path/1\nbody=non-jaxrs-bean-injected/path/1\n\nstatus=200\nurl=http://localhost:9998/main/non-jaxrs-bean-injected/header/1\nbody=bummer"
        }
    ]
}
```

*10.2 Second Application Injection — endpoints under base path `/secondary`*

Input requests `non-jaxrs-bean-injected/path/2` (returns the relative path) and `non-jaxrs-bean-injected/header/2` with header `x-test` (returns its value), proving the second application resolves its own injected context independently of the first. Each returns HTTP 200. The output concatenates each request's status, routed URL, and body separated by a blank line.

**Test Cases:** `rcb_tests/public_test_cases/feature10_2_secondary_app_injection.json`

```json
{
    "description": "The second application deployed under base path `/secondary` proves the two coexisting applications keep isolated injection contexts. Its resource exposes a path endpoint returning the matched relative path, and a header endpoint returning a custom request header value, both under distinct sub-paths from the first application. Input requests `non-jaxrs-bean-injected/path/2` and `non-jaxrs-bean-injected/header/2` (with header `x-test`); output concatenates each request's status, routed URL, and body separated by a blank line.",
    "cases": [
        {
            "input": {"requests": [
                {"app": "secondary", "path": "non-jaxrs-bean-injected/path/2"},
                {"app": "secondary", "path": "non-jaxrs-bean-injected/header/2", "headers": {"x-test": "bummer2"}}
            ]},
            "expected_output": "status=200\nurl=http://localhost:9998/secondary/non-jaxrs-bean-injected/path/2\nbody=non-jaxrs-bean-injected/path/2\n\nstatus=200\nurl=http://localhost:9998/secondary/non-jaxrs-bean-injected/header/2\nbody=bummer2"
        }
    ]
}
```

---

### Feature 11: Response Filter Invoked Exactly Once

**As a developer**, I want a managed response filter that adds a single header to every reply, so I can confirm the filter participates in the pipeline exactly once per response.

**Expected Behavior / Usage:**

A registered response filter adds exactly one response header to every reply. A request may ask the harness to report how many times that header appears; for any single response the count is exactly 1. Input requests an endpoint and sets the report flag; output reports status, routed URL, body, and a final `filter_invoked_count=1` line.

**Test Cases:** `rcb_tests/public_test_cases/feature11_response_filter_once.json`

```json
{
    "description": "A response filter adds exactly one response header to every reply. Input requests the per-request echo endpoint and asks the harness to report how many times that header appears on the response; output reports status, routed URL, body, and `filter_invoked_count=1`, proving the filter runs exactly once per response.",
    "cases": [
        {
            "input": {"requests": [{"app": "main", "path": "jcdibean/per-request", "query": {"x": "alpha"}, "report_filter": true}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/jcdibean/per-request?x=alpha\nbody=http://localhost:9998/main/jcdibean/per-request?x=alpha: queryParam=alpha 0\nfilter_invoked_count=1"
        },
        {
            "input": {"requests": [{"app": "main", "path": "jcdibean/per-request", "query": {"x": "a b"}, "report_filter": true}]},
            "expected_output": "status=200\nurl=http://localhost:9998/main/jcdibean/per-request?x=a+b\nbody=http://localhost:9998/main/jcdibean/per-request?x=a+b: queryParam=a b 0\nfilter_invoked_count=1"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the dependency-injected HTTP resource service described above — resource handlers, qualifier-selected collaborator services, per-request and application-scoped lifecycles, producers, a container extension, typed exceptions with registered mappers, a response filter, and two side-by-side hosted applications. The physical structure MUST follow the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable program that acts as a client to the core service. It reads a JSON request specification from stdin (an object with a `requests` array; each request carries `app`, `method`, `path`, and optional `query`, `matrix`, `headers`, `body`, `report_filter`), drives the running service over real HTTP, and prints the observed responses to stdout strictly matching the per-leaf-feature contracts above (`status=`, `url=`, `body=`, and optionally `filter_invoked_count=` lines, with a blank line between consecutive request renderings). Any failure in the underlying stack is rendered as a neutral `error=<category>` line; no host-language exception identity ever appears in stdout. This adapter MUST be logically and physically separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_constructor_param_binding.json` under `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_constructor_param_binding@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same newline delimiters as in the app_isolation module
