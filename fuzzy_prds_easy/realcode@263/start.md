## Product Requirement Document

# Dependency Container and Factory Adapter - Service Resolution Contracts

## Project Goal

Build a dependency container and factory toolkit that allows developers to register, locate, construct, decorate, and validate application objects without hand-writing repetitive object wiring and cache-management code.

---

## Background & Problem

Without this library, developers are forced to manually instantiate objects, thread dependencies through constructors, maintain alias maps, decide which objects should be shared, and duplicate lifecycle hook logic at each call site. This leads to repetitive code, inconsistent dependency resolution, fragile initialization order, and hard-to-debug object graph failures.

With this library, developers describe registrations, dependency maps, aliases, sharing rules, and lifecycle hooks once; callers can then request entries through a small container interface and receive consistently created objects or normalized errors.

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

### Feature 1: Container Registration and Resolution

**As a developer**, I want to register services, factories, aliases, sharing rules, and lifecycle hooks, so I can retrieve fully prepared objects from a single container without manual wiring.

**Expected Behavior / Usage:**

*1.1 Service Retrieval — Resolving configured entries*

The adapter input selects a retrieval scenario with `operation=service_retrieval`, a registration style, and a neutral service identifier. The output must state whether the entry is known, what neutral object kind was resolved, and whether a second retrieval returns the same cached object. Supported registration styles include prebuilt services, direct factories, closure factories, and fallback abstract factories.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_service_retrieval.json`

```json
{
    "description": "Resolves configured entries from direct instances, factories, closures, and abstract factories, and reports whether the same entry is cached between repeated lookups.",
    "cases": [
        {
            "input": {
                "operation": "service_retrieval",
                "registration": "factory",
                "service": "optioned_object"
            },
            "expected_output": "has_service=yes\nresolved=optioned_object\nsame_on_second_get=yes\n"
        }
    ]
}
```

*1.2 Sharing Rules — Controlling cache reuse*

The adapter input selects `operation=sharing_rules` and may provide a default sharing flag plus an entry-specific sharing flag. The output must report whether two ordinary retrievals of the same entry return the same object. Entry-specific sharing rules override the container default.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_sharing_rules.json`

```json
{
    "description": "Applies default and per-entry sharing rules when the same configured entry is requested more than once.",
    "cases": [
        {
            "input": {
                "operation": "sharing_rules",
                "shared_by_default": true
            },
            "expected_output": "same_on_second_get=yes\n"
        },
        {
            "input": {
                "operation": "sharing_rules",
                "shared_by_default": false
            },
            "expected_output": "same_on_second_get=no\n"
        }
    ]
}
```

*1.3 Explicit Build With Options — Creating uncached configured objects*

The adapter input selects `operation=build_with_options` and supplies an options object. The output must include the resolved object kind, the options passed into the constructed object, and confirmation that repeated explicit builds produce distinct objects even when a normal retrieval might be shared.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_build_with_options.json`

```json
{
    "description": "Creates a fresh object with caller-supplied options using the explicit build path instead of retrieving a cached shared entry.",
    "cases": [
        {
            "input": {
                "operation": "build_with_options",
                "options": {
                    "foo": "bar"
                }
            },
            "expected_output": "resolved=optioned_object\noptions={\"foo\":\"bar\"}\nsame_on_second_build=no\n"
        }
    ]
}
```

*1.4 Alias Resolution — Following chains to a target entry*

The adapter input selects `operation=alias_resolution`, supplies an alias map, and names the entry to retrieve. The output must show that the requested alias is recognized, resolves to the target object kind, and returns the same shared object as the target registration.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_alias_resolution.json`

```json
{
    "description": "Follows alias chains when checking and retrieving entries, returning the same shared target object through every alias.",
    "cases": [
        {
            "input": {
                "operation": "alias_resolution",
                "aliases": {
                    "foo": "optioned_object",
                    "bar": "foo"
                },
                "get": "bar"
            },
            "expected_output": "has_requested=yes\nresolved=optioned_object\nsame_as_target=yes\n"
        }
    ]
}
```

*1.5 Lifecycle Hooks — Decorating and initializing created objects*

The adapter input selects `operation=delegator_initializer`. The output must show the object kind and the properties contributed by creation wrappers and post-creation initializers, plus whether the final object is cached on repeated retrieval.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_lifecycle_hooks.json`

```json
{
    "description": "Runs delegators around object creation and initializers after creation so the resolved object contains all externally visible contributions.",
    "cases": [
        {
            "input": {
                "operation": "delegator_initializer"
            },
            "expected_output": "resolved=generic_object\noption=OPTIONED\nfoo=bar\nbar=baz\nsame_on_second_get=yes\n"
        }
    ]
}
```

*1.6 Configuration and Runtime Mutation — Adding registrations after construction*

The adapter input selects either a configuration merge or a sequence of runtime mutation actions. The output must demonstrate externally visible effects: previously unknown entries become known, configuration returns the same container instance, aliases resolve, decorators and initializers affect objects, and sharing rules can be changed.

**Test Cases:** `rcb_tests/public_test_cases/feature1_6_configuration_and_mutation.json`

```json
{
    "description": "Adds and changes registrations after construction through configuration and mutation APIs, including factories, aliases, delegators, initializers, and sharing rules.",
    "cases": [
        {
            "input": {
                "operation": "configure_container"
            },
            "expected_output": "has_date_before=yes\nhas_generic_before=no\nreturned_same_container=yes\nhas_date_after=yes\nhas_generic_after=yes\n"
        }
    ]
}
```

*1.7 Override Protection — Blocking changes to configured entries*

The adapter input selects `operation=override_protection`, a mutation action, and optionally enables override permission. If override permission is not enabled, attempts to replace an already configured entry must print a normalized `modification_not_allowed` error. If override permission is enabled, the mutation must apply and the output must show the newly resolved object kind.

**Test Cases:** `rcb_tests/public_test_cases/feature1_7_override_protection.json`

```json
{
    "description": "Rejects mutation of an already configured entry unless override permission has been explicitly enabled.",
    "cases": [
        {
            "input": {
                "operation": "override_protection",
                "action": "set_service"
            },
            "expected_output": "error=modification_not_allowed\ndetail=unspecified\n"
        },
        {
            "input": {
                "operation": "override_protection",
                "allow_override": true,
                "action": "set_service"
            },
            "expected_output": "allow_override=yes\nmutation_applied=yes\nresolved=date_time_object\n"
        }
    ]
}
```

*1.8 Cyclic Alias Detection — Rejecting recursive alias maps*

The adapter input selects `operation=cyclic_alias` and provides an alias map. If aliases form a cycle, the output must be a normalized alias-cycle error and must not include language runtime exception names or stack details.

**Test Cases:** `rcb_tests/public_test_cases/feature1_8_cyclic_alias_detection.json`

```json
{
    "description": "Detects cycles in alias definitions during configuration and reports a normalized alias-cycle error instead of looping.",
    "cases": [
        {
            "input": {
                "operation": "cyclic_alias",
                "aliases": {
                    "a": "a"
                }
            },
            "expected_output": "error=cyclic_alias\ndetail=alias_cycle_detected\n"
        }
    ]
}
```

---

### Feature 2: Explicit Dependency Map Factory

**As a developer**, I want to create objects from a declarative dependency map, so I can describe constructor wiring without embedding creation logic in application code.

**Expected Behavior / Usage:**

*2.1 Mapped Dependency Creation — Checking and constructing mapped objects*

The adapter input selects either `operation=config_abstract_factory_can_create` or `operation=config_abstract_factory_create`, supplies a `dependency_map`, and names the requested neutral object kind. Capability checks must print `can_create=yes` or `can_create=no`. Creation must instantiate the requested object and recursively resolve the dependencies named in the map.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_configured_dependency_factory.json`

```json
{
    "description": "Uses an explicit dependency map to decide whether an object can be created and to assemble objects with zero, simple, or nested dependencies.",
    "cases": [
        {
            "input": {
                "operation": "config_abstract_factory_can_create",
                "dependency_map": {
                    "optioned_object": []
                },
                "requested": "optioned_object"
            },
            "expected_output": "can_create=yes\n"
        }
    ]
}
```

*2.2 Dependency Map Shape Errors — Normalizing invalid configuration*

The adapter input selects `operation=config_abstract_factory_error` and names a malformed configuration shape. Missing container config, missing dependency map, non-map config, unavailable dependency maps, non-list dependency declarations, and non-string dependency entries must produce normalized error and detail lines.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_configured_dependency_errors.json`

```json
{
    "description": "Reports normalized errors when the explicit dependency map is missing or has a shape that cannot describe dependencies.",
    "cases": [
        {
            "input": {
                "operation": "config_abstract_factory_error",
                "config_shape": "missing_config_service"
            },
            "expected_output": "error=service_not_created\ndetail=missing_config_service\n"
        }
    ]
}
```

---

### Feature 3: Constructor Inspection Factory

**As a developer**, I want a factory that can inspect constructors and resolve dependencies from a container, so I can reduce boilerplate factories for straightforward object graphs.

**Expected Behavior / Usage:**

*3.1 Constructibility Checks — Determining whether inspection can create an entry*

The adapter input selects `operation=reflection_factory_can_create` and a requested constructibility scenario. The output must state whether automatic construction is possible. Non-class identifiers and classes with inaccessible constructors are not constructible; classes with no constructor are constructible.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_reflection_factory_capability.json`

```json
{
    "description": "Determines whether automatic constructor inspection can create a requested entry based on whether it is a constructible class.",
    "cases": [
        {
            "input": {
                "operation": "reflection_factory_can_create",
                "requested": "non_class"
            },
            "expected_output": "can_create=no\n"
        }
    ]
}
```

*3.2 Constructor Dependency Resolution — Supplying services, config, aliases, and defaults*

The adapter input selects `operation=reflection_factory_create` and a requested constructor scenario. The output must identify the resolved scenario and include observable injected values: configuration maps, option defaults, scalar defaults, typed-service injections, and well-known service injections when present.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_reflection_factory_creation.json`

```json
{
    "description": "Creates objects by inspecting constructor requirements, injecting container services, config maps, well-known service aliases, and default values where appropriate.",
    "cases": [
        {
            "input": {
                "operation": "reflection_factory_create",
                "requested": "no_constructor"
            },
            "expected_output": "resolved=no_constructor\n"
        },
        {
            "input": {
                "operation": "reflection_factory_create",
                "requested": "empty_constructor"
            },
            "expected_output": "resolved=empty_constructor\n"
        }
    ]
}
```

*3.3 Constructor Dependency Errors — Reporting unresolved requirements*

The adapter input selects `operation=reflection_factory_error` and a failing constructor scenario. Required typed dependencies missing from the container and required scalar parameters without defaults must produce normalized dependency-resolution error lines.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_reflection_factory_errors.json`

```json
{
    "description": "Reports normalized dependency-resolution errors when automatic constructor inspection encounters required parameters that cannot be supplied.",
    "cases": [
        {
            "input": {
                "operation": "reflection_factory_error",
                "requested": "missing_typed_service"
            },
            "expected_output": "error=service_not_found\ndetail=unresolvable_typed_dependency\n"
        }
    ]
}
```

---

### Feature 4: Constrained Child Containers

**As a developer**, I want a child container that validates retrieved plugin objects while still supporting normal container behavior, so I can expose a type-safe extension registry.

**Expected Behavior / Usage:**

*4.1 Plugin Validation and Caching — Validating result type and optioned lookups*

The adapter input selects `operation=plugin_manager` and a plugin-manager scenario. Normal lookups of valid plugins must resolve and be cached. Lookups with options must pass those options to construction and return fresh objects. Invalid plugin instances must be rejected with a normalized `invalid_service` error in hidden cases.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_plugin_manager_validation_and_caching.json`

```json
{
    "description": "A constrained child container retrieves valid plugin objects, caches normal lookups, bypasses the cache when options are supplied, and rejects invalid plugin instances.",
    "cases": [
        {
            "input": {
                "operation": "plugin_manager",
                "scenario": "cached_lookup"
            },
            "expected_output": "resolved=optioned_object\nsame_on_second_get=yes\n"
        },
        {
            "input": {
                "operation": "plugin_manager",
                "scenario": "options_disable_cache",
                "share_by_default": true
            },
            "expected_output": "resolved=optioned_object\noptions={\"foo\":\"bar\"}\nsame_on_second_get=no\n"
        }
    ]
}
```

---

### Feature 5: Container Decoration

**As a developer**, I want to wrap an existing standards-compatible container, so I can adapt it for consumers that expect the toolkit's container shape without changing the wrapped container.

**Expected Behavior / Usage:**

*5.1 Forwarded Container Operations — Proxying lookup and exposing the wrapped container*

The adapter input selects `operation=psr_decorator` and an entry identifier. The output must show that existence checks and retrieval are forwarded to the wrapped container and that the decorator can return the exact wrapped container object.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_container_decorator.json`

```json
{
    "description": "Wraps a standards-compatible container so existence checks, retrieval, and access to the wrapped container are forwarded transparently.",
    "cases": [
        {
            "input": {
                "operation": "psr_decorator",
                "id": "known"
            },
            "expected_output": "has=yes\nget_id=known\nsame_wrapped_container=yes\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_service_retrieval.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_service_retrieval@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same distinctness guarantee as provided by the build_with_options module
- use the same operation token mapping as defined in the Action/Operation Mapping table
