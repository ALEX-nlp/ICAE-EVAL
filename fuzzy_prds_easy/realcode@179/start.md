## Product Requirement Document

# Reactive Connection-Pool Configuration & Driver-Resolution Library - Product Requirements

## Project Goal

Build a connection-pooling layer for reactive database drivers that allows developers to wrap any underlying database driver in a pool purely through declarative configuration — either a single connection URL or a programmatic builder — without writing pool-management or driver-lookup code by hand. The library resolves which underlying driver to use, parses and normalizes every pool setting, validates the resulting configuration, and presents the wrapped driver while preserving the underlying driver's identity.

---

## Background & Problem

Without this library, developers wiring a reactive database driver into a connection pool must: hand-parse a connection URL into individual settings; convert each raw value (text, numbers, durations, enums) into the correct type; reconcile partially-specified pool sizes; locate the correct underlying driver from a registry; and re-validate every combination of options. This is repetitive, error-prone boilerplate that is easy to get subtly wrong (e.g. a max size smaller than the initial size, or a timeout value silently dropped).

With this library, a developer supplies a pooling connection URL such as `r2dbc:pool:<delegate>://host?initialSize=2&maxSize=12` (or the equivalent programmatic settings) and receives a fully-resolved, validated pool configuration plus a pooled connection factory that transparently delegates to the discovered underlying driver. Type coercion, default application, size reconciliation, constraint validation, and driver discovery all happen for them.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The domain has several distinct responsibilities (driver identification, URL parsing/resolution, a configuration builder, value coercion, conditional option binding, and delegate discovery). It MUST NOT be a single "god file"; organize it into cohesive units (e.g. a value-coercion/option-mapping unit, a configuration-builder unit, a URL-resolution/driver-provider unit, and a discovery/wrapping unit). Do not over-engineer — a small number of focused units is sufficient.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box contract for the execution adapter**, not the internal data model. The core configuration/resolution logic MUST remain decoupled from stdin/stdout and JSON. A thin execution adapter is solely responsible for translating JSON commands into idiomatic core calls and rendering results.

3. **Adherence to SOLID Design Principles:** Separate parsing, type coercion, builder validation, driver resolution, and output formatting into distinct logical units. The coercion/binding mechanism must be open for extension (new value types) without modifying existing call sites. Abstractions (option source, provider interface) must be small and substitutable.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public builder and URL-resolution entry points must read fluently in the target language and hide internal pool wiring.
   - **Resilience:** Invalid configurations and unparseable values must surface as well-modeled, specific error conditions (not generic faults). The execution adapter normalizes these into language-neutral category lines.

---

## Core Features

### Feature 1: Driver Identification & Registration

**As a developer**, I want the pooling layer to advertise a stable driver identifier and to reliably decide whether it should handle a given driver selector, so I can register it in a driver registry and have the right factory chosen for pooling requests.

**Expected Behavior / Usage:**

The pooling layer exposes a fixed driver identifier (the string `pool`). Given a set of connection options, it reports whether it handles them: it handles a request only when the driver selector equals its own identifier. A request with a missing driver selector, or with a selector naming a different (delegate) driver, is not handled. The command echoes back the supplied selector (`[a specific sentinel value indicating the pool state — confirm with the PM]` when absent), whether the pooling layer handles it, and the pooling layer's own advertised identifier.

**Test Cases:** `rcb_tests/public_test_cases/feature1_driver_identification.json`

```json
{
    "description": "Driver identification: the pooling provider advertises a stable driver identifier and decides whether it handles a given driver selector. It handles only its own pooling selector and declines requests with a missing or foreign driver selector.",
    "cases": [
        {
            "input": {"op": "driver", "driver": "pool"},
            "expected_output": "driver=pool\nhandled=true\npoolingDriver=pool\n"
        },
        {
            "input": {"op": "driver"},
            "expected_output": "driver=[a specific sentinel value indicating the pool state — confirm with the PM]\nhandled=false\npoolingDriver=pool\n"
        },
        {
            "input": {"op": "driver", "driver": "mock"},
            "expected_output": "driver=mock\nhandled=false\npoolingDriver=pool\n"
        }
    ]
}
```

---

### Feature 2: Connection-URL → Resolved Configuration

**As a developer**, I want to express the entire pool setup in one connection URL, so I can configure pooling declaratively. A pooling URL has the shape `r2dbc:pool:<delegate>://host?<params>`, where `<delegate>` names the underlying driver to pool and `<params>` are pool settings. Resolving a URL parses every recognized parameter into the correct type and produces a complete configuration; any parameter not present falls back to its default. The rendered configuration always lists the same fields in the same order: `initialSize`, `maxSize`, `acquireRetry`, `maxIdleTime`, `maxCreateConnectionTime`, `maxAcquireTime`, `maxLifeTime`, `backgroundEvictionInterval`, `validationDepth`, `validationQuery`, `name`, `registerJmx`. Timeouts that are not configured render as the sentinel `PT-0.001S`, meaning "no timeout".

**Expected Behavior / Usage:**

*2.1 Defaults — A URL with no parameters yields the default configuration*

When the URL carries only the delegate protocol and no query parameters, all settings take their defaults: both sizes are 10, acquire retry is 1, idle time is 30 minutes (`PT30M`), every other timeout is the no-timeout sentinel `PT-0.001S`, validation depth is `LOCAL`, and there is no validation query, name, or JMX registration.

**Test Cases:** `rcb_tests/public_test_cases/feature2_url_defaults.json`

```json
{
    "description": "Connection-URL to resolved configuration: parse a pooling connection URL whose nested protocol names a delegate driver, then resolve the full effective pool configuration. With no query parameters all pool settings fall back to their defaults. Timeouts that are not configured render as the sentinel negative duration meaning 'no timeout'.",
    "cases": [
        {
            "input": {"op": "url-config", "url": "r2dbc:pool:mock://host"},
            "expected_output": "initialSize=10\nmaxSize=10\nacquireRetry=1\nmaxIdleTime=PT30M\nmaxCreateConnectionTime=PT-0.001S\nmaxAcquireTime=PT-0.001S\nmaxLifeTime=PT-0.001S\nbackgroundEvictionInterval=PT-0.001S\nvalidationDepth=LOCAL\nvalidationQuery=[a specific sentinel value indicating the pool state — confirm with the PM]\nname=[a specific sentinel value indicating the pool state — confirm with the PM]\nregisterJmx=false\n"
        }
    ]
}
```

*2.2 Sizing & retry parameters — Integer parameters override their defaults*

The `initialSize`, `maxSize`, and `acquireRetry` parameters are parsed as integers and applied to the matching fields, overriding the defaults; unmentioned fields keep their defaults.

**Test Cases:** `rcb_tests/public_test_cases/feature2_url_sizing.json`

```json
{
    "description": "Sizing parameters from the connection URL: initialSize and maxSize query parameters are parsed to integers and applied to the resolved configuration, overriding the defaults. acquireRetry is likewise parsed to an integer.",
    "cases": [
        {
            "input": {"op": "url-config", "url": "r2dbc:pool:mock://host?initialSize=2&maxSize=12"},
            "expected_output": "initialSize=2\nmaxSize=12\nacquireRetry=1\nmaxIdleTime=PT30M\nmaxCreateConnectionTime=PT-0.001S\nmaxAcquireTime=PT-0.001S\nmaxLifeTime=PT-0.001S\nbackgroundEvictionInterval=PT-0.001S\nvalidationDepth=LOCAL\nvalidationQuery=[a specific sentinel value indicating the pool state — confirm with the PM]\nname=[a specific sentinel value indicating the pool state — confirm with the PM]\nregisterJmx=false\n"
        }
    ]
}
```

*2.3 Duration parameters — ISO-8601 timeouts apply independently*

Each timeout parameter (`maxLifeTime`, `maxAcquireTime`, `maxIdleTime`, `maxCreateConnectionTime`, `backgroundEvictionInterval`) is parsed from ISO-8601 duration text (e.g. `PT30M`) and applied only to its own field, leaving the other timeouts at their sentinel defaults.

**Test Cases:** `rcb_tests/public_test_cases/feature2_url_durations.json`

```json
{
    "description": "ISO-8601 duration parameters from the connection URL: each timeout query parameter (maxLifeTime, maxAcquireTime, maxIdleTime, maxCreateConnectionTime, backgroundEvictionInterval) is parsed from its ISO-8601 text and applied independently to the matching configuration field, leaving the other timeouts at their default sentinels.",
    "cases": [
        {
            "input": {"op": "url-config", "url": "r2dbc:pool:mock://host?maxLifeTime=PT30M"},
            "expected_output": "initialSize=10\nmaxSize=10\nacquireRetry=1\nmaxIdleTime=PT30M\nmaxCreateConnectionTime=PT-0.001S\nmaxAcquireTime=PT-0.001S\nmaxLifeTime=PT30M\nbackgroundEvictionInterval=PT-0.001S\nvalidationDepth=LOCAL\nvalidationQuery=[a specific sentinel value indicating the pool state — confirm with the PM]\nname=[a specific sentinel value indicating the pool state — confirm with the PM]\nregisterJmx=false\n"
        }
    ]
}
```

*2.4 Validation, naming & JMX parameters — Enum, string and boolean parameters apply*

The `validationDepth` parameter is parsed case-insensitively into a validation-depth category (`LOCAL` or `REMOTE`); `poolName` sets the pool's name; `registerJmx` enables JMX registration as a boolean.

**Test Cases:** `rcb_tests/public_test_cases/feature2_url_validation_jmx.json`

```json
{
    "description": "Validation, naming and JMX parameters from the connection URL: validationDepth is parsed case-insensitively into a validation-depth category; poolName sets the pool name; registerJmx enables JMX registration. These string/enum/boolean parameters apply to the resolved configuration.",
    "cases": [
        {
            "input": {"op": "url-config", "url": "r2dbc:pool:mock://host?validationDepth=remote"},
            "expected_output": "initialSize=10\nmaxSize=10\nacquireRetry=1\nmaxIdleTime=PT30M\nmaxCreateConnectionTime=PT-0.001S\nmaxAcquireTime=PT-0.001S\nmaxLifeTime=PT-0.001S\nbackgroundEvictionInterval=PT-0.001S\nvalidationDepth=REMOTE\nvalidationQuery=[a specific sentinel value indicating the pool state — confirm with the PM]\nname=[a specific sentinel value indicating the pool state — confirm with the PM]\nregisterJmx=false\n"
        },
        {
            "input": {"op": "url-config", "url": "r2dbc:pool:mock://host?registerJmx=true&poolName=requiredHere"},
            "expected_output": "initialSize=10\nmaxSize=10\nacquireRetry=1\nmaxIdleTime=PT30M\nmaxCreateConnectionTime=PT-0.001S\nmaxAcquireTime=PT-0.001S\nmaxLifeTime=PT-0.001S\nbackgroundEvictionInterval=PT-0.001S\nvalidationDepth=LOCAL\nvalidationQuery=[a specific sentinel value indicating the pool state — confirm with the PM]\nname=requiredHere\nregisterJmx=true\n"
        }
    ]
}
```

---

### Feature 3: Programmatic Configuration Builder

**As a developer**, I want to assemble a pool configuration step by step in code against a concrete underlying connection factory, so I can configure pooling without a URL. The builder accepts individual settings, applies defaults, reconciles partially-specified sizes, validates constraints, and produces the same field set rendered in the same fixed order as Feature 2.

**Expected Behavior / Usage:**

*3.1 Explicit settings — Provided settings appear verbatim; unset settings keep defaults*

When a mix of settings is supplied (validation query, idle timeout, initial and max size, name, JMX flag), each appears exactly as given while every unmentioned field keeps its default (e.g. acquire retry 1, the no-timeout sentinel for unset timeouts, `LOCAL` validation depth).

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_builder_explicit.json`

```json
{
    "description": "Programmatic configuration builder with explicit settings: starting from a valid delegate connection factory, the builder accepts an explicit mix of settings (validation query, idle timeout, initial and max size, pool name, JMX flag) and produces a configuration whose fields reflect exactly those settings while unset fields keep their defaults.",
    "cases": [
        {
            "input": {"op": "build-config", "settings": {"validationQuery": "foo", "maxIdleTime": "PT1S", "initialSize": 2, "maxSize": 20, "name": "bar", "registerJmx": true}},
            "expected_output": "initialSize=2\nmaxSize=20\nacquireRetry=1\nmaxIdleTime=PT1S\nmaxCreateConnectionTime=PT-0.001S\nmaxAcquireTime=PT-0.001S\nmaxLifeTime=PT-0.001S\nbackgroundEvictionInterval=PT-0.001S\nvalidationDepth=LOCAL\nvalidationQuery=foo\nname=bar\nregisterJmx=true\n"
        }
    ]
}
```

*3.2 Size reconciliation — Deriving the missing size from the one provided*

The defaults for both sizes are 10. When only max size is given, initial size stays at 10 if max ≥ 10, otherwise initial size is lowered to equal max. When only initial size is given, max size is raised to equal initial size if initial > 10 (otherwise max stays 10).

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_builder_sizing_defaults.json`

```json
{
    "description": "Pool sizing defaults and reconciliation in the programmatic builder: when only one of initial size / max size is specified, the other is derived. Specifying only max size keeps initial size at the default of 10 when max is at least 10, otherwise lowers initial size to match max. Specifying only initial size raises max size to equal initial size when it exceeds the default of 10.",
    "cases": [
        {
            "input": {"op": "build-config", "settings": {"maxSize": 20}},
            "expected_output": "initialSize=10\nmaxSize=20\nacquireRetry=1\nmaxIdleTime=PT30M\nmaxCreateConnectionTime=PT-0.001S\nmaxAcquireTime=PT-0.001S\nmaxLifeTime=PT-0.001S\nbackgroundEvictionInterval=PT-0.001S\nvalidationDepth=LOCAL\nvalidationQuery=[a specific sentinel value indicating the pool state — confirm with the PM]\nname=[a specific sentinel value indicating the pool state — confirm with the PM]\nregisterJmx=false\n"
        },
        {
            "input": {"op": "build-config", "settings": {"maxSize": 5}},
            "expected_output": "initialSize=5\nmaxSize=5\nacquireRetry=1\nmaxIdleTime=PT30M\nmaxCreateConnectionTime=PT-0.001S\nmaxAcquireTime=PT-0.001S\nmaxLifeTime=PT-0.001S\nbackgroundEvictionInterval=PT-0.001S\nvalidationDepth=LOCAL\nvalidationQuery=[a specific sentinel value indicating the pool state — confirm with the PM]\nname=[a specific sentinel value indicating the pool state — confirm with the PM]\nregisterJmx=false\n"
        }
    ]
}
```

*3.3 Constraint validation — Invalid configurations fail with a normalized category*

Building fails (and emits a single normalized `error=<category>` line) when: no underlying connection factory is supplied (`connection_factory_required`); JMX registration is enabled but no pool name is set (`jmx_name_required`); or the requested max size is below the requested initial size (`max_size_below_initial_size`).

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_builder_validation_errors.json`

```json
{
    "description": "Validation of configuration constraints in the programmatic builder. Building fails with a neutral error category when: no delegate connection factory is supplied; JMX registration is enabled without a pool name; or the requested max size is below the requested initial size. Each failure is reported as a single normalized error line.",
    "cases": [
        {
            "input": {"op": "build-config", "connectionFactory": false, "settings": {}},
            "expected_output": "error=connection_factory_required\n"
        },
        {
            "input": {"op": "build-config", "settings": {"registerJmx": true}},
            "expected_output": "error=jmx_name_required\n"
        },
        {
            "input": {"op": "build-config", "settings": {"initialSize": 2, "maxSize": 1}},
            "expected_output": "error=max_size_below_initial_size\n"
        }
    ]
}
```

---

### Feature 4: Value Coercion & Conditional Option Binding

**As a developer**, I want raw option values (which may arrive as numbers, strings, durations, or enum text) to be coerced into the correct type, and I want options applied only when actually present, so I can drive configuration from heterogeneous untyped sources without manual type handling.

**Expected Behavior / Usage:**

*4.1 Integer coercion — Numbers and numeric strings collapse to one integer*

A value is coerced to an integer. Any numeric input — integral or fractional in representation — and any numeric string all yield the same integer (fractional representations are truncated, strings are parsed).

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_coerce_integer.json`

```json
{
    "description": "Integer coercion: a configuration value is coerced to an integer. Numeric inputs (whether integral or fractional in representation) and numeric strings all coerce to the same integer value by truncation/parsing.",
    "cases": [
        {
            "input": {"op": "coerce", "kind": "integer", "value": 100},
            "expected_output": "value=100\n"
        },
        {
            "input": {"op": "coerce", "kind": "integer", "value": "100"},
            "expected_output": "value=100\n"
        }
    ]
}
```

*4.2 Enum coercion — Case-insensitive match to a validation-depth category*

A value is coerced to a validation-depth category. A string is matched case-insensitively to a category name, so `remote` and `REMOTE` both resolve to the canonical `REMOTE`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_coerce_enum.json`

```json
{
    "description": "Validation-depth enum coercion: a configuration value is coerced to a validation-depth category. A string is matched case-insensitively to the category name, so both lower-case and upper-case text resolve to the same canonical category.",
    "cases": [
        {
            "input": {"op": "coerce", "kind": "validationDepth", "value": "remote"},
            "expected_output": "value=REMOTE\n"
        },
        {
            "input": {"op": "coerce", "kind": "validationDepth", "value": "REMOTE"},
            "expected_output": "value=REMOTE\n"
        }
    ]
}
```

*4.3 Duration coercion — ISO-8601 text becomes a duration*

A value is coerced to a duration by parsing ISO-8601 text and re-rendering it in canonical ISO-8601 form.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_coerce_duration.json`

```json
{
    "description": "Duration coercion: a configuration value is coerced to a duration. An ISO-8601 duration string is parsed into the equivalent duration value, rendered back in canonical ISO-8601 form.",
    "cases": [
        {
            "input": {"op": "coerce", "kind": "duration", "value": "PT30M"},
            "expected_output": "value=PT30M\n"
        }
    ]
}
```

*4.4 Conditional binding — Apply only when present; surface conversion failures*

An option source binds a coerced value to a consumer only when the named option is present. When present, the coerced value is delivered (`bound=true` plus the value). When absent, nothing is applied (`bound=false`). When present but uncoercible, binding fails with a neutral `error=option_conversion_failed` line that names the offending option.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_option_binding.json`

```json
{
    "description": "Conditional option binding: an option source binds a value to a consumer only when the option is present, applying a coercion in between. When the named option is present its coerced value is delivered (bound=true). When the option is absent the consumer is never invoked (bound=false). When the option is present but its value cannot be coerced, binding fails with a neutral conversion-failure category naming the option.",
    "cases": [
        {
            "input": {"op": "bind", "kind": "integer", "key": "value", "options": {"value": "123"}},
            "expected_output": "bound=true\nvalue=123\n"
        },
        {
            "input": {"op": "bind", "kind": "integer", "key": "value", "options": {}},
            "expected_output": "bound=false\n"
        },
        {
            "input": {"op": "bind", "kind": "integer", "key": "value", "options": {"value": "abc"}},
            "expected_output": "error=option_conversion_failed\noption=value\n"
        }
    ]
}
```

---

### Feature 5: Delegate Discovery & Identity Preservation

**As a developer**, I want resolving a pooling URL to automatically discover the underlying driver named by the nested protocol, wrap it in a pool, and keep the underlying driver's identity intact, so the pool is a transparent stand-in for the real driver.

**Expected Behavior / Usage:**

Given a pooling URL `r2dbc:pool:<delegate>://host`, the library discovers the delegate driver registered under `<delegate>` and returns a pooling factory wrapping it. The wrapper exposes the delegate's identity faithfully: unwrapping the pooling factory yields the exact delegate factory instance, and the pooling factory reports the delegate's metadata unchanged. The command reports the delegate's driver name, whether unwrapping returns the delegate, and whether the wrapper's metadata matches the delegate's.

**Test Cases:** `rcb_tests/public_test_cases/feature5_delegate_discovery.json`

```json
{
    "description": "Delegate discovery and identity preservation: resolving a pooling connection URL discovers the delegate driver named by the nested protocol, wraps it in a pooling factory, and preserves the delegate's identity. The wrapper unwraps back to the exact delegate factory and reports the delegate's metadata unchanged.",
    "cases": [
        {
            "input": {"op": "discover", "url": "r2dbc:pool:mock://host"},
            "expected_output": "delegateDriver=mock\nunwrapsToDelegate=true\nmetadataMatchesDelegate=true\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing Features 1–5 — driver identification, connection-URL resolution, the programmatic configuration builder (with defaults, size reconciliation, and constraint validation), value coercion and conditional option binding, and delegate discovery with identity preservation. Organize it into cohesive units reflecting these responsibilities; do not collapse everything into one file and do not over-engineer.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON command from stdin, invokes the appropriate core logic, and prints the language-neutral, line-oriented result to stdout, matching the per-leaf-feature contracts above. The adapter is the only component aware of stdin/stdout and JSON, and it normalizes any core error into a neutral `error=<category>` line. It must be logically (ideally physically) separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_driver_identification.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_driver_identification@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
