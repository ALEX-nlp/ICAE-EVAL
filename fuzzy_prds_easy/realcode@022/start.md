## Product Requirement Document

# Resilient Request Wrapper — Automatic Retry Layer Around an HTTP Fetch Function

## Project Goal

Build a thin wrapper around an HTTP request function that adds automatic, configurable retry behavior, so developers can make requests that survive transient network failures (and optionally specific HTTP status codes) without hand-writing retry loops, timers, and back-off logic at every call site.

---

## Background & Problem

A bare HTTP request function either succeeds with a response or fails with a network error, and it does so exactly once. In the real world requests fail intermittently — a flaky connection, a momentarily overloaded server returning a 503, a gateway hiccup. Handling this everywhere means each call site re-implements the same boilerplate: try the request, decide whether the outcome is retryable, wait a while, try again, give up after N attempts, and finally surface either the good response or the last error.

This wrapper centralizes that logic behind a single call. It is used the same way as the underlying request function — you pass a target URL and an optional options object — but the options object additionally understands three retry controls: how many times to retry, how long to wait between attempts, and which outcomes count as retryable. The wrapper returns a promise that resolves with a response or rejects with an error, exactly mirroring the underlying function's contract, while transparently re-issuing the request according to the configured policy.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls to the core retry wrapper, and for driving the simulated request outcomes and clock described below.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, the retry policy, the request invocation, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The retry engine must be open for extension (new retry policies) but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** The wrapper must depend on an abstract request function, not a concrete networking implementation, so it can be driven by a controllable stub.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface must be elegant and idiomatic to the target programming language, returning a promise/future that resolves or rejects.
   - **Resilience:** The system must handle edge cases gracefully and reject invalid configuration up front, modeling errors properly rather than relying on generic faults.

---

## Core Features

The wrapper's public entry point takes a target URL and an optional options object. Recognized retry controls on the options object are: `retries` (an integer count, default 3), `retryDelay` (milliseconds to wait between attempts, default 1000, given either as a number or as a function that computes the delay), and `retryOn` (which outcomes are retryable, default: retry network errors only). The wrapper returns a promise that resolves with a response or rejects with an error. Any other fields on the options object are not interpreted by the wrapper.

Because retry behavior is inherently asynchronous and time-based, the execution adapter drives each scenario deterministically: it replaces the underlying request function with a controllable stub and uses a virtual clock. A scenario `input` carries the `url`, the optional `options`, and a `script` — an ordered timeline whose steps are: `{"resolve": <statusInt|null>}` settles the next issued request with a response of that status; `{"reject": <msgString|null>}` settles the next issued request with a network error carrying that message; `{"advance": <ms>}` advances the virtual clock by that many milliseconds (firing any retry whose delay has elapsed); `{"observe": "fetch_count"}` emits the number of requests issued so far; and `{"observe": "last_url"}` emits the URL of the most recently issued request. When `retryDelay` or `retryOn` is supplied as a function, the adapter expresses it as `{"fn": true, "returns": <value>}`, where `returns` is the value the function yields (a single value, or an array consumed by call index, clamping to the last element).

The adapter prints a deterministic, language-neutral trace: any inline `observe` and any function-callback records appear first, in chronological order, followed by a summary block — `fetch_count=<N>`, and (when at least one request was issued) `url=<first request URL>` and `options_passed=<true|false>` (false when no options object was supplied), and finally the outcome line: `outcome=resolved status=<s>`, `outcome=rejected [a specific absence-indicating token — ask the PM for the exact error field value when no message is present]`, or `[a specific pending-state sentinel — ask the PM for the exact output token]`. A function callback is recorded as `retryOn_call attempt=<n> [a specific absence-indicating token — ask the PM for the exact error field value when no message is present] status=<s|none>` (and likewise `retryDelay_call ...`), where `attempt` is the zero-based attempt index, `error` is the failed attempt's error message (or `none`), and `status` is the response status (or `none`).

### Feature 1: Forwarding The Request To The Underlying Function

**As a developer**, I want the wrapper to send my request to the exact target I gave it and keep targeting that same destination across retries, so the retry layer never silently changes what I asked for.

**Expected Behavior / Usage:**

The wrapper invokes the underlying request function with the caller-supplied URL. The first issued request records that URL, and every retried attempt reuses the identical URL. When no options object is supplied, that fact is observable (`options_passed=false`). The trace's `url=` line reflects the URL of the first request; using `observe: last_url` after a retry shows the most recent request used the same URL.

**Test Cases:** `rcb_tests/public_test_cases/feature1_request_forwarding.json`

```json
{
    "description": "The wrapper issues the request to the underlying fetch using exactly the caller-supplied target URL, and reuses that same URL for every retried attempt. The trace echoes the URL recorded on the first issued request; when a retry occurs after a transient failure, the URL of the most recently issued request is observed to be identical, confirming the wrapper does not alter the target between attempts.",
    "cases": [
        {
            "input": {
                "url": "http://some-url.com",
                "script": [
                    {"resolve": 200}
                ]
            },
            "expected_output": "fetch_count=1\nurl=http://some-url.com\noptions_passed=false\noutcome=resolved status=200\n"
        },
        {
            "input": {
                "url": "http://some-url.com",
                "script": [
                    {"reject": "network down"},
                    {"observe": "last_url"},
                    {"advance": 1000},
                    {"observe": "last_url"},
                    {"resolve": 200}
                ]
            },
            "expected_output": "last_url=http://some-url.com\nlast_url=http://some-url.com\nfetch_count=2\nurl=http://some-url.com\noptions_passed=false\noutcome=resolved status=200\n"
        }
    ]
}
```

---

### Feature 2: Retry On Network Failure With A Configurable Retry Budget

**As a developer**, I want a request that fails with a network error to be retried automatically a bounded number of times, so transient connectivity blips recover on their own without my code looping.

**Expected Behavior / Usage:**

When an attempt fails with a network error, the wrapper waits (the retry delay) and re-issues the request. It keeps doing so until an attempt succeeds (the wrapper resolves with that response) or the retry budget is exhausted (the wrapper rejects with the error of the final attempt). The budget is the `retries` option, defaulting to 3 — so by default up to 4 attempts are made. Lowering `retries` lowers the number of attempts (e.g. `retries: 1` allows at most 2 attempts). The trace reports the number of requests issued and whether the outcome was a resolved response or a rejected error.

**Test Cases:** `rcb_tests/public_test_cases/feature2_retry_on_network_error.json`

```json
{
    "description": "By default the wrapper treats a rejected request (a network-level failure) as retryable and re-issues it, waiting between attempts, until either an attempt succeeds or the configured number of retries is exhausted. The retry budget defaults to 3 (so up to 4 attempts total) and can be lowered via a retries option. When all attempts fail the wrapper settles by rejecting with the error of the final attempt; when an attempt succeeds it resolves with that response. The trace reports how many requests were issued and the final outcome.",
    "cases": [
        {
            "input": {
                "url": "http://someurl",
                "script": [
                    {"reject": "err1"},
                    {"advance": 1000},
                    {"resolve": 200}
                ]
            },
            "expected_output": "fetch_count=2\nurl=http://someurl\noptions_passed=false\noutcome=resolved status=200\n"
        },
        {
            "input": {
                "url": "http://someurl",
                "script": [
                    {"reject": "err1"},
                    {"advance": 1000},
                    {"reject": "err2"},
                    {"advance": 1000},
                    {"reject": "err3"},
                    {"advance": 1000},
                    {"reject": "err4"}
                ]
            },
            "expected_output": "fetch_count=4\nurl=http://someurl\noptions_passed=false\noutcome=rejected error=err4\n"
        }
    ]
}
```

---

### Feature 3: Successful Responses Are Returned Without Retrying By Default

**As a developer**, I want a request that actually returns a response to be handed back to me immediately by default, even if the status indicates a server error, so the retry layer never second-guesses a completed response unless I ask it to.

**Expected Behavior / Usage:**

With no `retryOn` configuration, the wrapper considers only network-level failures retryable. Any received response — regardless of its HTTP status, including `503` or `404` — resolves the wrapper on the first attempt, and no further request is issued. The trace shows exactly one request and the unchanged response status.

**Test Cases:** `rcb_tests/public_test_cases/feature3_no_retry_on_http_response.json`

```json
{
    "description": "With no retry-on configuration supplied, the wrapper retries ONLY on network-level failures, never on a received HTTP response. Any completed response — including server-error statuses such as 503 or 404 — is passed straight through and resolves the wrapper on the very first attempt without issuing any further requests. The trace shows a single request was made and the response status that was returned unchanged.",
    "cases": [
        {
            "input": {
                "url": "http://someurl",
                "script": [
                    {"resolve": 503}
                ]
            },
            "expected_output": "fetch_count=1\nurl=http://someurl\noptions_passed=false\noutcome=resolved status=503\n"
        }
    ]
}
```

---

### Feature 4: Fixed Delay Between Attempts

**As a developer**, I want a configurable fixed wait between a failed attempt and the next one, so I can avoid hammering a struggling endpoint immediately.

**Expected Behavior / Usage:**

After a retryable failure, the next request is issued only once the full `retryDelay` (in milliseconds) has elapsed; before that, no new request is made. Observing the request count while advancing the virtual clock demonstrates this: with a 5000 ms delay, the count remains at 1 after advancing 1000 ms, and becomes 2 only once the remaining time elapses and the retry fires.

**Test Cases:** `rcb_tests/public_test_cases/feature4_retry_delay_timing.json`

```json
{
    "description": "A retried request is delayed by a fixed amount of time (the retryDelay option, in milliseconds) before being re-issued. After the first attempt fails, no new request is made until at least the full delay has elapsed: observing the request count while advancing a virtual clock shows the count stays at 1 until the delay is reached, then becomes 2 when the next attempt fires. Here the delay is 5000 ms, so advancing only 1000 ms triggers no new request while advancing the remaining time does.",
    "cases": [
        {
            "input": {
                "url": "http://someUrl",
                "options": {"retryDelay": 5000},
                "script": [
                    {"reject": "err1"},
                    {"observe": "fetch_count"},
                    {"advance": 1000},
                    {"observe": "fetch_count"},
                    {"advance": 4000},
                    {"observe": "fetch_count"},
                    {"resolve": 200}
                ]
            },
            "expected_output": "fetch_count=1\nfetch_count=1\nfetch_count=2\nfetch_count=2\nurl=http://someUrl\noptions_passed=true\noutcome=resolved status=200\n"
        }
    ]
}
```

---

### Feature 5: Computed Delay Via A Delay Function

**As a developer**, I want to compute each wait dynamically (e.g. exponential back-off), so I can space retries more intelligently than a single fixed interval.

**Expected Behavior / Usage:**

When `retryDelay` is a function, the wrapper invokes it before scheduling each retry, supplying the zero-based attempt index, the failed attempt's network error (when the failure was an error), and the response (when applicable). The number it returns is used as the delay for that retry. Across successive retries the function is invoked again with the incremented attempt index and the corresponding failure. The trace records each invocation and its arguments, in order.

**Test Cases:** `rcb_tests/public_test_cases/feature5_retry_delay_function.json`

```json
{
    "description": "The retry delay may be supplied as a function instead of a fixed number, allowing the caller to compute each wait (for example, exponential backoff). Before scheduling each retry the wrapper invokes this function, supplying the zero-based attempt index, the network error of the failed attempt (when the failure was an error), and the response (when applicable); the function's returned number is used as the delay. The trace records each invocation with the arguments the wrapper supplied, in order, across successive retries.",
    "cases": [
        {
            "input": {
                "url": "http://someUrl",
                "options": {"retryDelay": {"fn": true, "returns": 5000}},
                "script": [
                    {"reject": "first error"},
                    {"advance": 5000},
                    {"resolve": 200}
                ]
            },
            "expected_output": "retryDelay_call attempt=0 error=first error status=none\nfetch_count=2\nurl=http://someUrl\noptions_passed=true\noutcome=resolved status=200\n"
        },
        {
            "input": {
                "url": "http://someUrl",
                "options": {"retryDelay": {"fn": true, "returns": 5000}},
                "script": [
                    {"reject": "first error"},
                    {"advance": 5000},
                    {"reject": "second error"},
                    {"advance": 5000},
                    {"resolve": 200}
                ]
            },
            "expected_output": "retryDelay_call attempt=0 error=first error status=none\nretryDelay_call attempt=1 error=second error status=none\nfetch_count=3\nurl=http://someUrl\noptions_passed=true\noutcome=resolved status=200\n"
        }
    ]
}
```

---

### Feature 6: Retry On A List Of HTTP Status Codes

**As a developer**, I want to opt specific HTTP status codes into the retry policy, so that responses like 503 are retried while other responses are returned immediately.

**Expected Behavior / Usage:**

When `retryOn` is a list of status codes, a received response whose status is in the list is treated as retryable (subject to the retry budget), while a response whose status is not in the list resolves the wrapper immediately. If the response status stays within the list for every attempt until the retry budget is exhausted, the wrapper resolves with the last received response (it does not reject). The trace reports the number of requests issued and the status the wrapper ultimately resolved with.

**Test Cases:** `rcb_tests/public_test_cases/feature6_retry_on_status_list.json`

```json
{
    "description": "The retryOn option may be a list of HTTP status codes that should be treated as retryable. When a response arrives whose status is in the list, the wrapper retries (subject to the retry budget); when the status is NOT in the list, the wrapper resolves immediately with that response. If every attempt keeps returning a listed status until the retry budget is exhausted, the wrapper resolves with the last received response rather than rejecting. The trace shows the number of requests issued and the status of the response the wrapper finally resolved with.",
    "cases": [
        {
            "input": {
                "url": "http://someurl",
                "options": {"retryOn": [503]},
                "script": [
                    {"resolve": 503},
                    {"advance": 1000},
                    {"resolve": 503},
                    {"advance": 1000},
                    {"resolve": 503},
                    {"advance": 1000},
                    {"resolve": 503}
                ]
            },
            "expected_output": "fetch_count=4\nurl=http://someurl\noptions_passed=true\noutcome=resolved status=503\n"
        },
        {
            "input": {
                "url": "http://someurl",
                "options": {"retryOn": [503]},
                "script": [
                    {"resolve": 503},
                    {"advance": 1000},
                    {"resolve": 200}
                ]
            },
            "expected_output": "fetch_count=2\nurl=http://someurl\noptions_passed=true\noutcome=resolved status=200\n"
        }
    ]
}
```

---

### Feature 7: Retry Decided By A Predicate Function

**As a developer**, I want full control over the retry decision through a predicate, so I can retry on arbitrary combinations of errors and responses (e.g. any network error or any 4xx/5xx).

**Expected Behavior / Usage:**

When `retryOn` is a function, it is invoked after every attempt with the zero-based attempt index, the network error (when the attempt failed with an error, otherwise absent), and the response (when the attempt produced one, otherwise absent). A truthy return triggers another attempt; a falsy return settles the wrapper — resolving with the response if the last attempt produced one, or rejecting with the error if it failed. While the predicate is in control it alone governs retries; the numeric retry budget is not consulted. The trace records each invocation with its arguments, followed by the final outcome.

**Test Cases:** `rcb_tests/public_test_cases/feature7_retry_on_function.json`

```json
{
    "description": "The retryOn option may instead be a predicate function that fully governs whether to retry. After every attempt the wrapper invokes it with the zero-based attempt index, the network error (when the attempt failed with an error, otherwise absent), and the response (when the attempt produced one, otherwise absent). A truthy return triggers another attempt; a falsy return settles the wrapper — resolving with the response if the last attempt produced one, or rejecting with the error if it failed. When this predicate is used it alone decides retries (the numeric retry budget is not consulted). The trace records each invocation with the arguments supplied, then the final outcome.",
    "cases": [
        {
            "input": {
                "url": "http://someUrl",
                "options": {"retryOn": {"fn": true, "returns": false}},
                "script": [
                    {"reject": "first error"}
                ]
            },
            "expected_output": "retryOn_call attempt=0 error=first error status=none\nfetch_count=1\nurl=http://someUrl\noptions_passed=true\noutcome=rejected error=first error\n"
        },
        {
            "input": {
                "url": "http://someUrl",
                "options": {"retryOn": {"fn": true, "returns": [true, false]}},
                "script": [
                    {"resolve": 502},
                    {"advance": 1000},
                    {"resolve": 200}
                ]
            },
            "expected_output": "retryOn_call attempt=0 error=none status=502\nretryOn_call attempt=1 error=none status=200\nfetch_count=2\nurl=http://someUrl\noptions_passed=true\noutcome=resolved status=200\n"
        }
    ]
}
```

---

### Feature 8: Reject Invalid Retry Configuration Up Front

**As a developer**, I want a misconfigured retry policy rejected immediately, so I get a clear error instead of silently wrong behavior.

**Expected Behavior / Usage:**

The `retryOn` option must be either a list of status codes or a predicate function. If it is supplied as any other type (such as a bare number or a string), the wrapper rejects the configuration before issuing any request, surfacing a neutral error category and a descriptive message stating that `retryOn` expects an array or a function. No request is made.

**Test Cases:** `rcb_tests/public_test_cases/feature8_invalid_retry_on.json`

```json
{
    "description": "The retryOn option must be either a list of status codes or a predicate function. When it is supplied as any other type (for example a bare number or a string), the wrapper rejects the configuration up front, before issuing any request, reporting a neutral error category together with a descriptive message explaining that retryOn expects an array or a function. No request is made in this case.",
    "cases": [
        {
            "input": {
                "url": "http://someUrl",
                "options": {"retryOn": 503},
                "script": []
            },
            "expected_output": "[a specific neutral error category string — ask the PM for the exact identifier]\nmessage=[a specific neutral error category string — ask the PM for the exact identifier]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the retry wrapper described above. Its physical structure (single-file vs. multi-file) MUST align with the "Scale-Driven Code Organization" constraint. The wrapper must depend on an abstract request function (so it can be driven by a stub) and must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to the core wrapper — logically (and ideally physically) separated from it. It reads a single JSON request from stdin, installs a controllable stub request function and a virtual clock, drives the supplied `script` timeline (settling requests, advancing the clock, emitting `observe` lines), and prints the resulting trace to stdout, matching the per-feature contracts above. It renders `retryDelay`/`retryOn` functions (given as `{"fn": true, "returns": ...}`) as recording callbacks, normalizes any native configuration error thrown by the wrapper into the neutral `[a specific neutral error category string — ask the PM for the exact identifier]` / `message=...` lines, and never leaks host-language runtime artifacts into stdout.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- The callback trace format for retryDelay follows the same argument-logging pattern as the retryOn callback trace.
- The total attempt count follows the standard off-by-one convention documented in the retry-budget section.
