## Product Requirement Document

# Error Categorization and In-Memory Resource Cache - A Support Library for Cluster Node Agents

## Project Goal

Build a small support library for programs that manage cluster workloads on a single node, providing two independent capabilities: a way to tag and recognize errors by semantic category (so callers can branch on *why* an operation failed rather than on a brittle string match), and a read-only in-memory cache that serves cluster objects (pods, services, secrets, config-maps) by name and namespace, so developers get uniform error semantics and fast local lookups without reinventing either mechanism.

---

## Background & Problem

Programs that reconcile workloads on a node constantly ask two kinds of questions: "what kind of failure was this?" and "where is the object with this name?". Without a shared convention, the first question is answered by fragile substring checks on error text, and the second by ad-hoc maps scattered across the codebase.

This library solves both. For errors, it lets any operation produce a value that belongs to a named category (for example *not-found* or *invalid-input*) while still carrying a human-readable message, and it lets a caller test membership in a category even when the categorized error has been wrapped inside other errors that merely expose their underlying cause. For lookups, it offers a passthrough cache: callers preload it with the objects currently assigned to the node and then list or fetch them by coordinates, getting a clear not-found signal when nothing matches.

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

### Feature 1: Error Categorization

**As a developer**, I want to attach a semantic category to an error and later test whether any error (possibly wrapped) belongs to that category, so I can branch on the meaning of a failure instead of matching its text.

**Expected Behavior / Usage:**

An error value is built and then queried for membership in a named category. The supported categories are *not-found* and *invalid-input*, and each is independent: a value tagged with one category is not a member of the other. There are four ways to obtain the value under test: build a fresh categorized error from a message; tag an already-existing plain error with the category (a nil-safe operation — tagging "no error" produces no error at all, and therefore no category membership); supply no error at all; or supply a foreign error that reports its own category membership through a boolean self-assessment (such a value's message is the lowercase spelling of that boolean). Membership testing follows the chain of wrapped causes: when a categorized error is later wrapped inside an unrelated error that exposes its underlying cause, the value is still recognized as a member of the original category, and its message is the composed message of the wrapper. The result reports the queried category name, whether the value is a member, and the value's textual message (empty when there is no error).

*1.1 Not-Found Category — recognizing errors that mean "the requested thing does not exist"*

Build or supply an error and ask whether it belongs to the *not-found* category. A freshly built categorized error and a foreign error whose self-assessment is true are both members; tagging a missing error, supplying no error, and a foreign error whose self-assessment is false are all non-members. A not-found error wrapped by a cause-bearing wrapper is still a member.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_not_found.json`

```json
{
    "description": "An error value is constructed in one of several ways and then queried for membership in the not-found category. Construction variants are: building a categorized error directly from a message; tagging an existing plain error with the category, which is a nil-safe operation that yields no error when there is no underlying error; supplying no error at all; or providing a foreign error that advertises its own category membership through a boolean self-report. The query walks the chain of wrapped causes, so a categorized error stays recognizable even after being wrapped by an unrelated cause-bearing error. The output reports the queried category name, whether the value is recognized as a member of that category, and the value's textual message (empty when there is no error).",
    "cases": [
        {
            "input": {"action": "classify", "category": "not_found", "error": {"build": "new", "message": "foo not found"}},
            "expected_output": "category=not_found\nclassified=true\n[specific failure message format for uncategorizable tagged errors]foo not found\n"
        },
        {
            "input": {"action": "classify", "category": "not_found", "error": null},
            "expected_output": "category=not_found\n[specific failure message format for uncategorizable tagged errors]\n[specific failure message format for uncategorizable tagged errors]\n"
        }
    ]
}
```

*1.2 Invalid-Input Category — recognizing errors that mean "the supplied input was not acceptable"*

Build or supply an error and ask whether it belongs to the *invalid-input* category, with exactly the same construction variants and cause-chain behavior as the not-found category, but reported under the invalid-input name.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_invalid_input.json`

```json
{
    "description": "An error value is constructed in one of several ways and then queried for membership in the invalid-input category. Construction variants are: building a categorized error directly from a message; tagging an existing plain error with the category, which is a nil-safe operation that yields no error when there is no underlying error; supplying no error at all; or providing a foreign error that advertises its own category membership through a boolean self-report. The query walks the chain of wrapped causes, so a categorized error stays recognizable even after being wrapped by an unrelated cause-bearing error. The output reports the queried category name, whether the value is recognized as a member of that category, and the value's textual message (empty when there is no error).",
    "cases": [
        {
            "input": {"action": "classify", "category": "invalid_input", "error": {"build": "new", "message": "foo not found"}},
            "expected_output": "category=invalid_input\nclassified=true\n[specific failure message format for uncategorizable tagged errors]foo not found\n"
        },
        {
            "input": {"action": "classify", "category": "invalid_input", "error": null},
            "expected_output": "category=invalid_input\n[specific failure message format for uncategorizable tagged errors]\n[specific failure message format for uncategorizable tagged errors]\n"
        }
    ]
}
```

---

### Feature 2: In-Memory Resource Cache

**As a developer**, I want to preload a cache with the cluster objects assigned to a node and then list or fetch them by coordinates, so I can serve workload lookups locally with a clear not-found signal.

**Expected Behavior / Usage:**

The cache is a read-only passthrough over an in-memory store. For each request, a fresh cache is populated with the supplied records and then a single operation is performed against it. Every record is identified by a `namespace` and a `name`; data-bearing kinds also carry a `data` map of string keys to string values. The cache distinguishes four object kinds — `pod`, `service`, `secret`, and `config-map` — and supports two operation shapes: listing all records of a kind (reporting how many were returned), and fetching one data-bearing record by name and namespace. A successful fetch returns the record's data, rendered as comma-joined `key=value` pairs with keys in sorted order. A fetch whose name/namespace pair matches no stored record fails with a not-found outcome; the failure is reported as a neutral `error=not_found` line followed by a `message` line carrying the domain message, which names the requested resource kind and the missing name in the form `<kind> "<name>" not found`.

*2.1 List Pods — count the pod records held by the cache*

Preload zero or more pod records (each a namespace/name pair) and list them. The output is `pods=<count>` where the count equals the number of records that were loaded.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_pods.json`

```json
{
    "description": "A set of pod records is loaded into the resource cache, each identified by a namespace and a name. The cache acts as a passthrough to the underlying store, and listing all pods returns every record that was loaded. The output reports the number of pods the cache returns.",
    "cases": [
        {
            "input": {"action": "resource", "resource": "pod", "items": [{"namespace": "namespace-0", "name": "name-0"}, {"namespace": "namespace-1", "name": "name-1"}]},
            "expected_output": "pods=2\n"
        }
    ]
}
```

*2.2 List Services — count the service records held by the cache*

Preload zero or more service records and list them. The output is `services=<count>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_services.json`

```json
{
    "description": "A set of service records is loaded into the resource cache, each identified by a namespace and a name. The cache acts as a passthrough to the underlying store, and listing all services returns every record that was loaded. The output reports the number of services the cache returns.",
    "cases": [
        {
            "input": {"action": "resource", "resource": "service", "items": [{"namespace": "namespace-0", "name": "service-0"}, {"namespace": "namespace-1", "name": "service-1"}]},
            "expected_output": "services=2\n"
        }
    ]
}
```

*2.3 Fetch Secret — retrieve one secret's data, or report not-found*

Preload secret records (namespace, name, and a `data` map) and fetch one by name and namespace. A match returns `data=<sorted key=value pairs>`. A miss returns a not-found outcome whose message names the secret kind and the requested name.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_secret.json`

```json
{
    "description": "Secret records are loaded into the resource cache, each identified by a namespace and a name and carrying a map of key/value data. A retrieval is then performed by name and namespace. When a matching record exists, its data is returned and the output lists the key/value pairs (keys sorted). When no record matches the requested name and namespace, the retrieval fails with a not-found outcome whose message names the requested resource kind and name.",
    "cases": [
        {
            "input": {"action": "resource", "resource": "secret", "items": [{"namespace": "namespace-0", "name": "name-0", "data": {"key-0": "val-0"}}, {"namespace": "namespace-1", "name": "name-1", "data": {"key-1": "val-1"}}], "get": {"name": "name-0", "namespace": "namespace-0"}},
            "expected_output": "data=key-0=val-0\n"
        },
        {
            "input": {"action": "resource", "resource": "secret", "items": [{"namespace": "namespace-0", "name": "name-0", "data": {"key-0": "val-0"}}, {"namespace": "namespace-1", "name": "name-1", "data": {"key-1": "val-1"}}], "get": {"name": "name-X", "namespace": "namespace-X"}},
            "expected_output": "error=not_found\n[specific failure message format for uncategorizable tagged errors]secret \"name-X\" not found\n"
        }
    ]
}
```

*2.4 Fetch Config-Map — retrieve one config-map's data, or report not-found*

Preload config-map records (namespace, name, and a `data` map) and fetch one by name and namespace, with the same success and not-found contract as the secret fetch, but reported for the config-map kind.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_configmap.json`

```json
{
    "description": "Config-map records are loaded into the resource cache, each identified by a namespace and a name and carrying a map of key/value data. A retrieval is then performed by name and namespace. When a matching record exists, its data is returned and the output lists the key/value pairs (keys sorted). When no record matches the requested name and namespace, the retrieval fails with a not-found outcome whose message names the requested resource kind and name.",
    "cases": [
        {
            "input": {"action": "resource", "resource": "configmap", "items": [{"namespace": "namespace-0", "name": "name-0", "data": {"key-0": "val-0"}}, {"namespace": "namespace-1", "name": "name-1", "data": {"key-1": "val-1"}}], "get": {"name": "name-0", "namespace": "namespace-0"}},
            "expected_output": "data=key-0=val-0\n"
        },
        {
            "input": {"action": "resource", "resource": "configmap", "items": [{"namespace": "namespace-0", "name": "name-0", "data": {"key-0": "val-0"}}, {"namespace": "namespace-1", "name": "name-1", "data": {"key-1": "val-1"}}], "get": {"name": "name-X", "namespace": "namespace-X"}},
            "expected_output": "error=not_found\n[specific failure message format for uncategorizable tagged errors]configmap \"name-X\" not found\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result to stdout, matching the per-leaf-feature contracts above. The request's `action` selects behavior: `classify` builds an error per the `category` and `error` spec (optionally wrapping it in a cause-bearing wrapper via `wrap_in_cause`) and reports the category, membership, and message; `resource` populates a fresh cache of the given `resource` kind with `items` and either lists them or, when a `get` block is present, fetches one record by name and namespace. Errors must be rendered as language-neutral lines (a `category`/`error` label plus a domain `message`), never leaking host-language runtime type names.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the 'composed message' logic defined in the error composition module
- adhere to the standard block termination rule in the execution engine module
