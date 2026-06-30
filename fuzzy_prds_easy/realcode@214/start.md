## Product Requirement Document

# Environment-Driven Access-Log Configuration Engine - XML Configuration Resolution & Typed Settings Binding

## Project Goal

Build a configuration engine for an HTTP access-logging subsystem that allows developers to externalize logging behavior into XML documents whose variables, conditional sections, and modular includes are resolved against a runtime property environment and a set of active deployment profiles, plus a typed settings layer that maps flat configuration keys onto an immutable settings object. This lets operators tune logging output per environment without editing or recompiling the application.

---

## Background & Problem

Without this engine, developers must hard-code logging layouts, branch on the deployment environment inside application code, and duplicate shared logging fragments across every configuration file. This leads to brittle, copy-pasted configuration, environment drift between staging and production, and silent misconfiguration when a value is mistyped.

With this engine, a configuration document declares named variables sourced from the surrounding property environment (with literal fallbacks), gates whole sections behind profile expressions, and pulls in shared fragments by reference — all resolved deterministically at configuration time. A parallel typed-binding layer turns a flat map of dotted keys into a validated, immutable settings object with documented defaults, so the rest of the system consumes strongly-typed configuration rather than loose strings.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This project spans two distinct responsibilities — (a) an XML configuration interpreter that resolves variables, evaluates conditional sections, and follows includes, and (b) a typed settings binder. These MUST be cleanly separated into distinct logical units; do not collapse them into a single monolithic file.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core engine. The core configuration logic must remain completely decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls to the core engine and rendering the result.

3. **Adherence to SOLID Design Principles:** Separate document parsing, variable resolution, profile evaluation, include resolution, settings binding, and output formatting into distinct cohesive units. The engine must be open for extension (new element kinds, new settings fields) but closed for modification, and high-level modules must depend on abstractions rather than concrete I/O.

4. **Robustness & Interface Design:** The public interface must be idiomatic to the target language and hide internal complexity. Edge cases — malformed declarations, unresolvable references, empty conditions — must be handled gracefully and modeled as recoverable outcomes (tallied errors or normalized error categories) rather than uncaught faults.

---

## Core Features

### Feature 1: Environment-Sourced Variable Resolution

**As a developer**, I want my configuration document to declare named variables that draw their values from the runtime property environment, with literal fallbacks, so I can externalize logging layout per environment without editing the document.

**Expected Behavior / Usage:**

A configuration document declares named variables. Each declaration binds a *name* to a value looked up from a *source* key in a supplied property environment; an optional literal *fallback* is used when that key is absent. A declaration is **rejected** (and tallied as one error) when its name or its source key is empty or omitted — such declarations contribute no variable. Resolved variables are interpolated (by `${name}` reference) into a console output pattern. The engine drives a `[a specific string accepted by the dispatch logic]` request carrying the document set, the entry document name, and a flat `properties` map; it emits one `appender=<name> pattern=<resolved-pattern>` line for each active output target (in attachment order), followed by an `errors=<count>` line giving the number of rejected declarations. When a sourced key is present its environment value wins; when absent the fallback (if any) is used; a variable with neither a present key nor a fallback resolves to empty.

**Test Cases:** `rcb_tests/public_test_cases/feature1_spring_property_resolution.json`

```json
{
  "description": "A configuration document declares named variables that are each sourced from a key in a supplied property environment, with an optional literal fallback used when the key is absent from the environment. A declaration whose name or source key is empty or omitted is rejected and tallied. The resolved variables are interpolated into a console output pattern; the engine reports every active output target with its fully resolved pattern, followed by the number of rejected declarations.",
  "cases": [
    {
      "input": {
        "mode": "[a specific string accepted by the dispatch logic]",
        "entry": "main.xml",
        "documents": {
          "main.xml": "<configuration> ...springProperty declarations (3 valid + 4 rejected) and a console appender whose pattern is ${console_pattern_prefix}${console_pattern_body}${console_pattern_suffix}... </configuration>"
        },
        "properties": {
          "logback.access.test.console.pattern.prefix": ">>>",
          "logback.access.test.console.pattern.suffix": "<<<"
        }
      },
      "expected_output": "appender=console pattern=>>>%h %l %u [%t] \"%r\" %s %b<<<\nerrors=4"
    },
    {
      "input": {
        "mode": "[a specific string accepted by the dispatch logic]",
        "entry": "main.xml",
        "documents": { "main.xml": "<configuration> ...same declarations... </configuration>" },
        "properties": {}
      },
      "expected_output": "appender=console pattern=%h %l %u [%t] \"%r\" %s %b;\nerrors=4"
    }
  ]
}
```

*The literal document text and the full case list are authoritative in the JSON file; the snippet above is abbreviated for readability.*

---

### Feature 2: Variable Resolution Across a Referenced Document

**As a developer**, I want to factor shared variable declarations into a separate document that my main document pulls in by reference, so I can reuse common logging fragments across configurations.

**Expected Behavior / Usage:**

The same kind of environment-sourced variable declarations from Feature 1 are placed in a **separate document** that the entry document incorporates by reference. The referenced document participates fully in resolution: variable lookup, literal fallback, and rejection of malformed declarations all behave identically to the inline form. The engine resolves the reference using its own resource loader (the referenced document must be discoverable by name among the supplied document set), then reports each active output target with its resolved pattern and the count of rejected declarations, exactly as in the inline case. This demonstrates that modular includes are transparent to variable resolution.

**Test Cases:** `rcb_tests/public_test_cases/feature2_spring_property_via_include.json`

```json
{
  "description": "The same environment-sourced variable declarations are placed in a separate document that the main document pulls in by reference. Resolution, fallback, and rejection behave identically to the inline form, demonstrating that referenced documents participate fully in variable resolution. The engine reports each active output target with its resolved pattern and the number of rejected declarations.",
  "cases": [
    {
      "input": {
        "mode": "[a specific string accepted by the dispatch logic]",
        "entry": "main.xml",
        "documents": {
          "main.xml": "<configuration> <include resource=\"...included.xml\"/> </configuration>",
          "...included.xml": "<included> ...same 3 valid + 4 rejected declarations and console appender... </included>"
        },
        "properties": {
          "logback.access.test.console.pattern.prefix": ">>>",
          "logback.access.test.console.pattern.suffix": "<<<"
        }
      },
      "expected_output": "appender=console pattern=>>>%h %l %u [%t] \"%r\" %s %b<<<\nerrors=4"
    }
  ]
}
```

---

### Feature 3: Profile-Gated Configuration Sections

**As a developer**, I want to gate whole configuration sections behind deployment-profile expressions, so the same document produces different logging behavior across environments without code changes.

**Expected Behavior / Usage:**

A configuration document wraps sections in profile-gated blocks. A block is **kept** only when its profile expression matches the set of active profiles supplied with the request. A leading negation marker (`!`) inverts the match, so a negated expression is kept precisely when the named profile is *not* active. Blocks may **nest**: an inner block is evaluated only if its enclosing block was kept; if the outer block is dropped, all of its descendants are dropped regardless of their own expressions. An **empty** profile expression is never kept. The engine processes a `[a specific string accepted by the dispatch logic]` request carrying the document set, the entry name, and a `profiles` array of active profile names; it emits, in declaration order, one `appender=<name> pattern=<pattern>` line for each output target that belongs to a kept block, followed by an `errors=<count>` line. Output targets inside dropped or empty blocks never appear.

**Test Cases:** `rcb_tests/public_test_cases/feature3_spring_profile_selection.json`

```json
{
  "description": "A configuration document gates sections behind profile expressions. A section is kept only when its expression matches the set of active profiles; a leading negation marker inverts the match, sections may nest (an inner section is evaluated only if its enclosing section is kept), and an empty expression is never kept. The engine reports, in declaration order, the output targets belonging to the kept sections together with their patterns, followed by an error count.",
  "cases": [
    {
      "input": {
        "mode": "[a specific string accepted by the dispatch logic]",
        "entry": "main.xml",
        "documents": { "main.xml": "<configuration> ...nested springProfile blocks: default (negated), additional (positive), each with a nested child; plus an empty-name block and a blank-name block... </configuration>" },
        "profiles": [
          "logback-access-test-disable-default-console",
          "logback-access-test-enable-additional-console",
          "logback-access-test-enable-additional-nested-console"
        ]
      },
      "expected_output": "appender=additional_console pattern=additional_console: %h %l %u [%t] \"%r\" %s %b\nappender=additional_nested_console pattern=additional_nested_console: %h %l %u [%t] \"%r\" %s %b\nerrors=0"
    },
    {
      "input": {
        "mode": "[a specific string accepted by the dispatch logic]",
        "entry": "main.xml",
        "documents": { "main.xml": "<configuration> ...same blocks... </configuration>" },
        "profiles": []
      },
      "expected_output": "appender=default_console pattern=default_console: %h %l %u [%t] \"%r\" %s %b\nappender=default_nested_console pattern=default_nested_console: %h %l %u [%t] \"%r\" %s %b\nerrors=0"
    }
  ]
}
```

---

### Feature 4: Typed Settings Binding

**As a developer**, I want a flat map of dotted configuration keys to bind onto an immutable, strongly-typed settings object with documented defaults, so the rest of the system consumes validated configuration rather than loose strings.

**Expected Behavior / Usage:**

The engine binds a flat map of dotted keys, all under a fixed prefix, onto a typed settings object composed of a top level plus nested groups. Keys that are absent take **documented defaults**; supplied keys **override** them. The settings include a boolean master switch (default on), an optional config-document locator (default absent), an enumerated local-port strategy (default the server-derived strategy), a nested group with an optional tri-state boolean (default absent), a second nested group with a boolean (default on), and a third nested group with a boolean switch (default off) plus two optional string filters (default absent). The engine processes a `bind` request carrying a `properties` map and emits the effective value of every field in a **stable order**, one `field=value` per line. The enumerated strategy is rendered in lowercase. Absent optional fields are rendered as the neutral marker `[a specific error marker string used for optional missing values]`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_configuration_property_binding.json`

```json
{
  "description": "Binds a flat map of dotted configuration keys under a fixed prefix onto a typed, immutable settings object with nested groups. Absent keys take documented defaults; supplied keys override them, including an enumerated strategy value and nested boolean/string groups. The effective value of every field is reported in a stable order, with absent optional fields rendered as a neutral null marker.",
  "cases": [
    {
      "input": { "mode": "bind", "properties": {} },
      "expected_output": "enabled=true\nconfig=[a specific error marker string used for optional missing values]\nlocal_port_strategy=server\ntomcat.request_attributes_enabled=[a specific error marker string used for optional missing values]\nundertow.record_request_start_time=true\ntee_filter.enabled=false\ntee_filter.includes=[a specific error marker string used for optional missing values]\ntee_filter.excludes=[a specific error marker string used for optional missing values]"
    },
    {
      "input": {
        "mode": "bind",
        "properties": {
          "logback.access.enabled": "false",
          "logback.access.config": "classpath:logback-access-test.xml",
          "logback.access.tomcat.request-attributes-enabled": "true",
          "logback.access.undertow.record-request-start-time": "false",
          "logback.access.tee-filter.includes": "example.com",
          "logback.access.tee-filter.excludes": "localhost"
        }
      },
      "expected_output": "enabled=false\nconfig=classpath:logback-access-test.xml\nlocal_port_strategy=server\ntomcat.request_attributes_enabled=true\nundertow.record_request_start_time=false\ntee_filter.enabled=false\ntee_filter.includes=example.com\ntee_filter.excludes=localhost"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the four features above — an XML configuration interpreter (variable resolution, profile gating, modular includes) and a typed settings binder — organized into distinct logical units, not a single god file.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads one JSON command from stdin, dispatches on a `mode` field (`[a specific string accepted by the dispatch logic]` or `bind`), invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-feature contracts above. Failures must be rendered as normalized `error=<category>` lines (e.g. `invalid_request`, `entry_not_found`, `config_failed`, `bind_failed`, `unknown_mode`, `empty_input`) and never leak host-runtime exception identities. This adapter must be logically and physically separated from the core domain.

3. **Automated test harness:** A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`, namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- process in the manner defined for profile inclusion resolution
- order the keys according to the scope hierarchy established in the schema parser
