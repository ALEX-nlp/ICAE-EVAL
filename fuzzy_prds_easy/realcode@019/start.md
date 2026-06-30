## Product Requirement Document

# Deprecation Notice Manager — Side-Effect-Free Deprecation Reporting Layer

## Project Goal

Build a small, side-effect-free deprecation-reporting layer that lets library authors announce that a code path is deprecated without dictating how the surrounding application must react. Each deprecation is identified by a stable identifier (any URL-like string pointing at an explanation), and the layer can count occurrences, route notifications to a chosen backend, deduplicate noise, and selectively silence individual deprecations or whole packages — all opt-in, doing nothing at all until a host explicitly turns it on.

---

## Background & Problem

Without such a layer, a library that wants to warn about deprecated usage must reach directly for a global error-raising mechanism or a logger of its own choosing. That couples the library to an error-handling strategy it does not own, floods logs with duplicate warnings, gives consumers no way to silence a specific warning or an entire dependency, and offers no programmatic way to discover which deprecations actually fired during a run. The result is brittle, noisy, and hard to integrate into test suites.

With this layer, a producer simply declares a deprecation by identifier, package, and message; the application independently decides whether deprecations are ignored, merely counted, raised through the runtime's error channel, or sent to a structured logger. Consumers can deduplicate, suppress specific identifiers, silence whole packages, inspect counts, and reset state — without the producing library knowing or caring.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a focused utility with a single cohesive responsibility (managing deprecation state and routing), so a small, well-separated structure is appropriate — but the routing/backends, the counting/state, and the activation/configuration concerns must remain cleanly separated rather than entangled in one undifferentiated blob.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in "Core Features" are a **black-box contract for the execution adapter**, not the internal data model. The core deprecation engine must not know anything about stdin/stdout or JSON. A thin execution adapter translates JSON scenarios into idiomatic calls on the core and renders observable effects to stdout.

3. **Adherence to SOLID Design Principles:** Separate activation/configuration, counting/state, suppression rules, backend notification, and output formatting into distinct logical units. The set of notification backends must be open for extension (new backends) without modifying the core dispatch logic. Backends must be substitutable behind a common notification abstraction. High-level dispatch must depend on the backend abstraction, not on a concrete logger or error channel.

4. **Robustness & Interface Design:** The public interface must be elegant and idiomatic to the target language, hiding internal state. The default state must be a genuine no-op (zero side effects). Configuration must be resilient to being driven either programmatically or via an environment selector. Edge cases (unknown selector values, suppressed identifiers, repeated triggers) must be handled gracefully and predictably.

---

## Core Features

> **Shared output contract (applies to every feature).** The execution adapter reads one JSON scenario and prints two things in order:
> 1. Zero or more **notice blocks**, one per backend notification actually emitted, in emission order. Each block is exactly:
>    `[a specific event category constant — ask the PM for the exact string]` / `backend=<trigger_error|psr_logger>` / `message=<formatted message>` / `package=<package>` / `link=<identifier>`.
> 2. A **summary**: a line `unique_count=<sum of all per-identifier counters>`, followed by either one `count[<identifier>]=<n>` line per tracked identifier (in first-seen order) or a single `tracked=(none)` line when nothing is tracked.
>
> A scenario object may contain: `enable` (list of modes to activate: `track`, `trigger`, `psr`), `env` (environment selector value, an alternative activation channel), `deduplication` (boolean, default true), `ignore_packages` (list), `ignore_links` (list of identifiers to suppress), `triggers` (list of `{package, link, message, args}` operations), `from_outside` (caller-location scenario selector), and `disable_after` (boolean). Notice that no call-site file or line ever appears in the output: such host-runtime detail is deliberately excluded from the contract.

### Feature 1: Activation and counting

**As a developer**, I want the layer to do nothing until explicitly activated, and to count deprecations once activated, so I can drop it into a library safely and still discover what fired.

**Expected Behavior / Usage:**

*1.1 Default no-op — the layer is inert until a mode is selected*

When no activation mode is selected, triggering a deprecation has no effect whatsoever: nothing is counted and no backend is notified. The summary reports a unique total of zero and no tracked identifiers.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_default_noop.json`

```json
{
    "description": "When no activation mode has been selected, the manager is a complete no-op: triggering a deprecation neither records a counter nor notifies any backend. The unique total stays zero and no identifiers are tracked.",
    "cases": [
        {
            "input": {"triggers": [{"package": "acme/orm", "link": "https://dep.example.com/orm/1234", "message": "a deprecated call"}]},
            "expected_output": "[a specific sentinel value — ask the PM for the exact string]\ntracked=(none)\n"
        }
    ]
}
```

*1.2 Tracking and counting — per-identifier counters and the unique total*

When tracking is activated, each trigger increments a counter keyed by the deprecation's identifier. The unique total equals the sum of every counter. Repeated triggers of the same identifier grow its counter; distinct identifiers are counted independently and listed in first-seen order.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_tracking_count.json`

```json
{
    "description": "With tracking activated, every trigger increments a per-identifier counter. The unique total equals the sum of all counters. Repeated triggers of the same identifier grow its counter; distinct identifiers are counted independently in first-seen order.",
    "cases": [
        {
            "input": {"enable": ["track"], "triggers": [{"package": "acme/orm", "link": "https://dep.example.com/orm/1234", "message": "this is deprecated %s %d", "args": ["foo", 1234]}]},
            "expected_output": "unique_count=1\ncount[https://dep.example.com/orm/1234]=1\n"
        },
        {
            "input": {"enable": ["track"], "triggers": [{"package": "acme/orm", "link": "https://dep.example.com/orm/1234", "message": "m"}, {"package": "acme/orm", "link": "https://dep.example.com/orm/1234", "message": "m"}, {"package": "acme/orm", "link": "https://dep.example.com/orm/1234", "message": "m"}]},
            "expected_output": "unique_count=3\ncount[https://dep.example.com/orm/1234]=3\n"
        }
    ]
}
```

---

### Feature 2: Deduplication of backend notifications

**As a developer**, I want repeated occurrences of the same deprecation to notify the backend only once by default (while still being counted), with an option to disable that, so I can avoid log spam yet still measure true frequency.

**Expected Behavior / Usage:**

*2.1 Default deduplication — notify once per identifier, keep counting*

With deduplication on (the default), the backend is notified only on the first occurrence of each identifier during a run; subsequent occurrences are still counted but produce no further notification. Two triggers of the same identifier therefore yield exactly one notice block and a counter of two.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_deduplication.json`

```json
{
    "description": "By default deduplication is on: the backend (here the error-trigger notifier) is invoked only on the first occurrence of each identifier within a run, even though the per-identifier counter keeps incrementing on every occurrence.",
    "cases": [
        {
            "input": {"enable": ["trigger"], "triggers": [{"package": "acme/orm", "link": "https://dep.example.com/orm/1234", "message": "this is deprecated %s %d", "args": ["foo", 1234]}, {"package": "acme/orm", "link": "https://dep.example.com/orm/1234", "message": "this is deprecated %s %d", "args": ["foo", 1234]}]},
            "expected_output": "[a specific event category constant — ask the PM for the exact string]\nbackend=trigger_error\nmessage=this is deprecated foo 1234\npackage=acme/orm\nlink=https://dep.example.com/orm/1234\nunique_count=2\ncount[https://dep.example.com/orm/1234]=2\n"
        }
    ]
}
```

*2.2 Deduplication disabled — notify on every occurrence*

When deduplication is turned off, the backend is notified on every occurrence rather than just the first. Two triggers of the same identifier then yield two notice blocks and a counter of two.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_without_deduplication.json`

```json
{
    "description": "When deduplication is turned off, the backend is notified on every occurrence of an identifier, not just the first. Two triggers of the same identifier produce two notifications and a counter of two.",
    "cases": [
        {
            "input": {"enable": ["trigger"], "deduplication": false, "triggers": [{"package": "acme/orm", "link": "https://dep.example.com/orm/2222", "message": "this is deprecated %s %d", "args": ["foo", 2222]}, {"package": "acme/orm", "link": "https://dep.example.com/orm/2222", "message": "this is deprecated %s %d", "args": ["foo", 2222]}]},
            "expected_output": "[a specific event category constant — ask the PM for the exact string]\nbackend=trigger_error\nmessage=this is deprecated foo 2222\npackage=acme/orm\nlink=https://dep.example.com/orm/2222\n[a specific event category constant — ask the PM for the exact string]\nbackend=trigger_error\nmessage=this is deprecated foo 2222\npackage=acme/orm\nlink=https://dep.example.com/orm/2222\nunique_count=2\ncount[https://dep.example.com/orm/2222]=2\n"
        }
    ]
}
```

---

### Feature 3: Message formatting

**As a developer**, I want the message to be a printf-style template with trailing arguments substituted in, so I can embed dynamic values without pre-building strings.

**Expected Behavior / Usage:**

The message is a printf-style template. Any trailing arguments are substituted into the template before it reaches a backend: `%s` consumes a string, `%d` consumes an integer, multiple placeholders consume multiple arguments in order, and a template with no placeholders is emitted verbatim. The substituted result is what appears in the notice block's `message` field.

**Test Cases:** `rcb_tests/public_test_cases/feature3_message_formatting.json`

```json
{
    "description": "The message is a printf-style template; any trailing arguments are substituted into it before it reaches a backend. Supports string and integer placeholders, multiple placeholders, and templates with no placeholders (emitted verbatim).",
    "cases": [
        {
            "input": {"enable": ["trigger"], "triggers": [{"package": "acme/orm", "link": "https://dep.example.com/orm/1234", "message": "this is deprecated %s %d", "args": ["foo", 1234]}]},
            "expected_output": "[a specific event category constant — ask the PM for the exact string]\nbackend=trigger_error\nmessage=this is deprecated foo 1234\npackage=acme/orm\nlink=https://dep.example.com/orm/1234\nunique_count=1\ncount[https://dep.example.com/orm/1234]=1\n"
        },
        {
            "input": {"enable": ["trigger"], "triggers": [{"package": "acme/orm", "link": "https://dep.example.com/orm/1234", "message": "use %s instead", "args": ["newApi"]}]},
            "expected_output": "[a specific event category constant — ask the PM for the exact string]\nbackend=trigger_error\nmessage=use newApi instead\npackage=acme/orm\nlink=https://dep.example.com/orm/1234\nunique_count=1\ncount[https://dep.example.com/orm/1234]=1\n"
        }
    ]
}
```

---

### Feature 4: Notification backends

**As a developer**, I want to choose where deprecation notices go, so I can either route them through the runtime's error channel or capture them as structured log entries.

**Expected Behavior / Usage:**

*4.1 Error-trigger backend — carries package and identifier alongside the message*

The error-trigger backend emits a notice carrying the formatted message together with the originating package and the deprecation identifier. (The underlying mechanism may append call-site location detail, but such host-runtime detail is not part of the observable contract and is excluded.)

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_trigger_error_backend.json`

```json
{
    "description": "The error-trigger backend emits a deprecation notice carrying the formatted message together with the originating package and the deprecation identifier. Host-specific call-site location details are not part of the observable contract.",
    "cases": [
        {
            "input": {"enable": ["trigger"], "triggers": [{"package": "acme/orm", "link": "https://dep.example.com/orm/1234", "message": "this is deprecated %s %d", "args": ["foo", 1234]}]},
            "expected_output": "[a specific event category constant — ask the PM for the exact string]\nbackend=trigger_error\nmessage=this is deprecated foo 1234\npackage=acme/orm\nlink=https://dep.example.com/orm/1234\nunique_count=1\ncount[https://dep.example.com/orm/1234]=1\n"
        }
    ]
}
```

*4.2 Structured-logger backend — message clean, package and identifier as metadata*

The structured-logger backend emits the formatted message as a clean log entry, carrying the originating package and the deprecation identifier as structured metadata rather than appending them to the message text. The observable fields are the same (`message`, `package`, `link`), but the backend label distinguishes it.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_psr_logger_backend.json`

```json
{
    "description": "The structured-logger backend emits the formatted message as a clean log entry, carrying the originating package and deprecation identifier as structured metadata rather than appending them to the message text.",
    "cases": [
        {
            "input": {"enable": ["psr"], "triggers": [{"package": "acme/orm", "link": "https://dep.example.com/orm/2222", "message": "this is deprecated %s %d", "args": ["foo", 1234]}]},
            "expected_output": "[a specific event category constant — ask the PM for the exact string]\nbackend=psr_logger\nmessage=this is deprecated foo 1234\npackage=acme/orm\nlink=https://dep.example.com/orm/2222\nunique_count=1\ncount[https://dep.example.com/orm/2222]=1\n"
        }
    ]
}
```

---

### Feature 5: Selective suppression

**As a developer**, I want to silence either a specific deprecation identifier or an entire package, so I can manage noise from code I cannot change yet.

**Expected Behavior / Usage:**

*5.1 Suppress by identifier — skipped entirely, not even counted*

A suppressed identifier is skipped before any counting takes place: it is neither counted nor sent to any backend, exactly as if it had never been triggered. The summary shows a unique total of zero and no tracked identifiers.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_ignore_identifier.json`

```json
{
    "description": "An identifier can be suppressed entirely. A suppressed identifier is skipped before any counting takes place: it is neither counted nor sent to any backend, as if it had never been triggered.",
    "cases": [
        {
            "input": {"enable": ["trigger"], "ignore_links": ["https://dep.example.com/orm/1234"], "triggers": [{"package": "acme/orm", "link": "https://dep.example.com/orm/1234", "message": "this is deprecated %s %d", "args": ["foo", 1234]}]},
            "expected_output": "[a specific sentinel value — ask the PM for the exact string]\ntracked=(none)\n"
        }
    ]
}
```

*5.2 Silence a package — still counted, but no backend notification*

Silencing a package suppresses only backend notifications for deprecations originating from that package; counting is unaffected. Such a deprecation is still counted (its counter increments and it appears in the summary) but no notice block is emitted.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_ignore_package.json`

```json
{
    "description": "A whole package can be silenced from backend notifications. Deprecations from a silenced package are still counted (tracking is unaffected), but no backend notification is emitted for them.",
    "cases": [
        {
            "input": {"enable": ["trigger"], "ignore_packages": ["acme/orm"], "triggers": [{"package": "acme/orm", "link": "https://dep.example.com/orm/1234", "message": "this is deprecated %s %d", "args": ["foo", 1234]}]},
            "expected_output": "unique_count=1\ncount[https://dep.example.com/orm/1234]=1\n"
        }
    ]
}
```

---

### Feature 6: Environment-driven activation

**As a developer**, I want to choose the activation mode through an environment selector instead of code, so I can flip behavior per deployment without recompiling.

**Expected Behavior / Usage:**

Activation can be driven by an environment selector as an alternative to explicit activation calls. The selector value `track` enables counting only (no backend); the value `trigger` enables the error-trigger backend (and counting); any other or absent value leaves the layer a no-op. The observable result is identical to activating the corresponding mode programmatically.

**Test Cases:** `rcb_tests/public_test_cases/feature6_env_activation.json`

```json
{
    "description": "Activation can be driven by an environment selector instead of explicit calls. The selector value 'track' enables counting only; 'trigger' enables the error-trigger backend; any other/absent value leaves the manager a no-op.",
    "cases": [
        {
            "input": {"env": "track", "triggers": [{"package": "acme/foo", "link": "https://dep.example.com/foo/1", "message": "message"}]},
            "expected_output": "unique_count=1\ncount[https://dep.example.com/foo/1]=1\n"
        },
        {
            "input": {"env": "trigger", "triggers": [{"package": "acme/foo", "link": "https://dep.example.com/foo/1", "message": "message"}]},
            "expected_output": "[a specific event category constant — ask the PM for the exact string]\nbackend=trigger_error\nmessage=message\npackage=acme/foo\nlink=https://dep.example.com/foo/1\nunique_count=1\ncount[https://dep.example.com/foo/1]=1\n"
        }
    ]
}
```

---

### Feature 7: Trigger only when called from outside the owning package

**As a developer**, I want a deprecation that fires only when the deprecated path is reached from outside the package that owns it, so a library can warn its consumers without warning itself during its own internal use.

**Expected Behavior / Usage:**

This variant guards a deprecation by the location of the immediate caller relative to the package that owns it (the package being treated as an installed, vendored dependency). The trigger call site lives inside the owning package. When the deprecated path is reached from **outside** the package boundary (ordinary consumer code), the deprecation fires and is counted. When it is reached from **inside** the package itself — including from a different class within the same package using the deprecated path internally — it is treated as an internal call and stays completely silent (not even counted). Calls originating from a test location are always treated as outside and therefore fire. In this scenario the guarded deprecation's owning package, identifier, and message are fixed as: package `acme/widgets`, identifier `https://deprecations.example.com/widgets/42`, message `oldWidget() is deprecated, use newWidget() instead.`. The `from_outside` selector chooses the caller's location: `outside` (consumer code → fires), `inside` (the package's own internal use → silent), `inside_other` (a different class inside the package → silent), or `tests` (a test location → fires).

**Test Cases:** `rcb_tests/public_test_cases/feature7_called_from_outside.json`

```json
{
    "description": "A deprecation can be declared so that it fires only when invoked from OUTSIDE the package that owns it (where the package is installed as a vendored dependency). The trigger call site lives inside the owning package; the decision depends on the immediate caller's location. When the caller is outside the package boundary the deprecation fires; when the caller is itself inside the package it is treated as an internal call and stays silent. The owning package, identifier and message of the guarded deprecation are fixed by the scenario: package 'acme/widgets', identifier 'https://deprecations.example.com/widgets/42', message 'oldWidget() is deprecated, use newWidget() instead.'. The 'location' field selects where the caller sits relative to the package: 'outside' (consumer code) or 'inside' (the package calling its own deprecated path).",
    "cases": [
        {
            "input": {"enable": ["trigger"], "from_outside": "outside"},
            "expected_output": "[a specific event category constant — ask the PM for the exact string]\nbackend=trigger_error\nmessage=oldWidget() is deprecated, use newWidget() instead.\npackage=acme/widgets\nlink=https://deprecations.example.com/widgets/42\nunique_count=1\ncount[https://deprecations.example.com/widgets/42]=1\n"
        },
        {
            "input": {"enable": ["trigger"], "from_outside": "inside"},
            "expected_output": "[a specific sentinel value — ask the PM for the exact string]\ntracked=(none)\n"
        }
    ]
}
```

---

### Feature 8: Disable and reset

**As a developer**, I want to disable the layer and reset its counters, so I can return to a clean baseline (for example between test runs).

**Expected Behavior / Usage:**

Disabling turns activation off and resets every per-identifier counter to zero. Identifiers that were already seen remain listed but with a zero count, and the unique total drops back to zero.

**Test Cases:** `rcb_tests/public_test_cases/feature8_disable_reset.json`

```json
{
    "description": "Disabling the manager turns tracking off and resets the per-identifier counters to zero. Identifiers that were already seen remain listed but with a zero count, and the unique total drops back to zero.",
    "cases": [
        {
            "input": {"enable": ["track"], "triggers": [{"package": "acme/orm", "link": "https://dep.example.com/orm/1234", "message": "this is deprecated %s %d", "args": ["foo", 1234]}], "disable_after": true},
            "expected_output": "[a specific sentinel value — ask the PM for the exact string]\ncount[https://dep.example.com/orm/1234]=0\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured deprecation-management engine implementing the activation, counting, deduplication, suppression, backend-routing, environment-driven activation, caller-location gating, and reset behaviors described above. Its physical structure must align with the "Scale-Driven Code Organization" constraint — small but with clearly separated state, routing, and configuration concerns, and no coupling to stdin/stdout or JSON.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads one JSON scenario from stdin, drives the core via idiomatic calls, and prints the resulting observable effects (notice blocks plus summary) to stdout, strictly matching the per-feature contracts above. This adapter must be logically (and ideally physically) separate from the core domain and is solely responsible for normalizing effects into the language-neutral stdout contract (no file paths, line numbers, or host-language exception identities ever leak into stdout).

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_1_default_noop.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_default_noop@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout of the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the signature style of the link metric
