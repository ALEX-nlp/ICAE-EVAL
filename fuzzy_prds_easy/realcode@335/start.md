## Product Requirement Document

# Plugin Dependency & Version Resolution Toolkit — Semantic Versioning, Dependency Ordering, and Metadata Parsing

## Project Goal

Build a reusable toolkit for managing modular software components ("plugins"), so developers can declare each component's version and the other components it depends on, and have the system decide—deterministically and up front—whether the set is consistent and in what order the components must be loaded. The toolkit covers semantic-version reasoning, dependency-coordinate parsing, dependency-graph resolution, generic directed-graph ordering, and parsing component metadata into a normalized descriptor.

---

## Background & Problem

A modular application is assembled from independent components. Each component declares its own version and a list of other components it requires, where each requirement may pin an acceptable version range. Without a shared toolkit, every application re-implements version comparison, range checking, requirement parsing, cycle detection, and load ordering by hand—logic that is subtle (semantic-version precedence, compound ranges), easy to get wrong (silent cyclic dependencies, missing requirements discovered only at runtime), and duplicated across projects.

This toolkit centralizes that logic behind a small set of well-defined, deterministic operations: check whether a version satisfies a constraint, compare two versions, parse a dependency coordinate, resolve a whole component set into a load order while reporting cycles / missing / version-mismatched requirements, perform generic topological ordering on a directed graph, and parse a component's key/value metadata into a normalized descriptor.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:*[a specific wildcard string representing any-version support]The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:*[a specific wildcard string representing any-version support]A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:*[a specific wildcard string representing any-version support]If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract*[a specific wildcard string representing any-version support]for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):*[a specific wildcard string representing any-version support]Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):*[a specific wildcard string representing any-version support]The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):*[a specific wildcard string representing any-version support]Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):*[a specific wildcard string representing any-version support]Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):*[a specific wildcard string representing any-version support]High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:*[a specific wildcard string representing any-version support]The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:*[a specific wildcard string representing any-version support]The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Version Constraint Satisfaction

**As a developer**, I want to check whether a given version satisfies a version constraint, so I can decide whether a component is acceptable before using it.

**Expected Behavior / Usage:**

The input supplies a `version` string and a `constraint` string. The constraint follows semantic-version expression syntax: a single comparator such as `>2.0.0`, a compound range that joins comparators with `&` such as `>=1.4.0 & <1.6.0`, or the wildcard `*` which accepts any version (including non-semantic strings). The output reports three lines: `version=<the version under test>`, `constraint=<the constraint>`, and `satisfied=<true|false>` indicating whether the version satisfies the constraint. The wildcard constraint is satisfied without parsing the version at all. Two error conditions are normalized to a neutral category line in place of the `satisfied` line: if the version is missing/empty, the output ends with `error=version_required`; if the version is present but is not a well-formed semantic version (e.g. it lacks a required component), the output ends with `error=invalid_version`.

**Test Cases:*[a specific wildcard string representing any-version support]`rcb_tests/public_test_cases/feature1_version_constraint.json`

```json
{
    "description": "Evaluate whether a concrete version string satisfies a version constraint expression. The constraint may be a simple comparator, a compound range joining several comparators, or a wildcard that accepts any version. The result reports the version under test, the constraint, and whether the version satisfies it. When the version string is missing or empty the evaluation reports a neutral error indicating a version is required; when the version string is present but is not a well-formed version it reports a neutral invalid-version error.",
    "cases": [
        {
            "input": {"action": "version_constraint", "version": "1.4.3", "constraint": ">2.0.0"},
            "expected_output": "version=1.4.3\nconstraint=>2.0.0\nsatisfied=false\n"
        },
        {
            "input": {"action": "version_constraint", "version": "1.4.3", "constraint": ">=1.4.0 & <1.6.0"},
            "expected_output": "version=1.4.3\nconstraint=>=1.4.0 & <1.6.0\nsatisfied=true\n"
        },
        {
            "input": {"action": "version_constraint", "version": null, "constraint": ">2.0.0"},
            "expected_output": "version=\nconstraint=>2.0.0\nerror=version_required\n"
        }
    ]
}
```

---

### Feature 2: Version Comparison

**As a developer**, I want to compare two versions, so I can tell which one is newer when selecting among candidates.

**Expected Behavior / Usage:**

The input supplies a `left` version string and a `right` version string, both well-formed semantic versions. The output echoes `left=<left>` and `right=<right>`, then `order=<greater|[a specific boolean outcome indicating version A is less than version B]|equal>`: `greater` when the left version has higher precedence than the right, `[a specific boolean outcome indicating version A is less than version B]` when it is lower, and `equal` when the two versions have the same precedence.

**Test Cases:*[a specific wildcard string representing any-version support]`rcb_tests/public_test_cases/feature2_version_compare.json`

```json
{
    "description": "Compare two version strings and report their relative order. The output echoes both operands and a single word describing whether the left version is greater than, [a specific boolean outcome indicating version A is less than version B] than, or equal to the right version according to semantic-version precedence.",
    "cases": [
        {
            "input": {"action": "version_compare", "left": "1.1.0", "right": "1.0.0"},
            "expected_output": "left=1.1.0\nright=1.0.0\norder=greater\n"
        },
        {
            "input": {"action": "version_compare", "left": "1.0.0", "right": "2.3.1"},
            "expected_output": "left=1.0.0\nright=2.3.1\norder=[a specific boolean outcome indicating version A is less than version B]\n"
        }
    ]
}
```

---

### Feature 3: Dependency Coordinate Parsing

**As a developer**, I want to parse a single dependency coordinate into its parts, so I know which component is required, which versions are acceptable, and whether the requirement is optional.

**Expected Behavior / Usage:**

The input supplies a `coordinate` string: an identifier, optionally followed by a `?` to mark the requirement optional, optionally followed by `@` and a version-support expression. The output reports `pluginId=<identifier>`, `versionSupport=<expression>`, and `optional=<true|false>`. Rules: a `?` immediately after the identifier (before any `@`) marks the dependency optional and is stripped from the identifier; an `@` with nothing after it, or no `@` at all, yields the any-version wildcard `*` as the version support; otherwise the text after the `@` is the version-support expression verbatim.

**Test Cases:*[a specific wildcard string representing any-version support]`rcb_tests/public_test_cases/feature3_parse_dependency.json`

```json
{
    "description": "Parse a dependency coordinate string into its three components: the dependency identifier, the required version-support expression, and whether the dependency is optional. The coordinate is a single token of the form identifier, optionally followed by a question mark to mark it optional, optionally followed by an at-sign and a version-support expression. A missing or empty version-support expression defaults to the any-version wildcard; the trailing question mark (if present) marks the dependency optional and is not part of the identifier.",
    "cases": [
        {
            "input": {"action": "parse_dependency", "coordinate": "test"},
            "expected_output": "pluginId=test\nversionSupport=*\noptional=false\n"
        },
        {
            "input": {"action": "parse_dependency", "coordinate": "test?@1.0"},
            "expected_output": "pluginId=test\nversionSupport=1.0\noptional=true\n"
        }
    ]
}
```

---

### Feature 4: Dependency Resolution

**As a developer**, I want to resolve a whole set of components into a safe load order while surfacing any problems, so the application either knows exactly how to start up or fails fast with a precise diagnosis.

**Expected Behavior / Usage:**

The input supplies a `plugins` array. Each element has an `id`, an optional `version` (its own version), and an optional `dependencies` string (a comma-separated list of dependency coordinates, each in the Feature-3 format). The resolver builds the dependency graph and reports four lines:

- `cyclic=<true|false>` — whether the dependencies form a cycle.
- `sorted=<comma-separated ids>` — a load order in which every dependency precedes the component that needs it; empty when a cycle prevents any valid order.
- `notFound=<comma-separated ids>` — required dependency ids that are not present among the supplied components.
- `wrongVersion=<entries>` — one entry per dependency whose present version does not satisfy a dependent's required version-support expression; each entry has the form `dependency=<id> dependent=<id> existing=<present version> required=<required expression>`, and multiple entries are joined with ` | `.

A required version-support expression of the wildcard or a simple pin is checked against the dependency's own declared version. Optional dependencies do not participate in ordering. When a cycle is detected, `cyclic=true` and `sorted` is empty; the not-found and wrong-version reports are independent of ordering.

**Test Cases:*[a specific wildcard string representing any-version support]`rcb_tests/public_test_cases/feature4_resolve_dependencies.json`

```json
{
    "description": "Resolve a set of plugin descriptors into a dependency-ordered load plan. Each plugin supplies an identifier, an optional own version, and a comma-separated list of dependency coordinates (identifier with optional version-support expression). The resolver reports: whether the dependency graph contains a cycle; the plugins listed in an order where every dependency precedes the plugin that needs it; any required dependency identifiers that are not present among the supplied plugins; and any dependencies whose present version does not satisfy the version-support expression required by a dependent. When a cycle is present no order can be produced. Each wrong-version entry names the dependency, the dependent that required it, the version actually present, and the required version-support expression.",
    "cases": [
        {
            "input": {"action": "resolve_dependencies", "plugins": [
                {"id": "p1", "dependencies": "p2"},
                {"id": "p2", "version": "0.0.0"}
            ]},
            "expected_output": "cyclic=false\nsorted=p2,p1\nnotFound=\nwrongVersion=\n"
        },
        {
            "input": {"action": "resolve_dependencies", "plugins": [
                {"id": "p1", "version": "0.0.0", "dependencies": "p2"},
                {"id": "p2", "version": "0.0.0", "dependencies": "p3"},
                {"id": "p3", "version": "0.0.0", "dependencies": "p1"}
            ]},
            "expected_output": "cyclic=true\nsorted=\nnotFound=\nwrongVersion=\n"
        },
        {
            "input": {"action": "resolve_dependencies", "plugins": [
                {"id": "p1", "dependencies": "p2@>=1.5.0 & <1.6.0"},
                {"id": "p2", "version": "1.4.0"}
            ]},
            "expected_output": "cyclic=false\nsorted=p2,p1\nnotFound=\nwrongVersion=dependency=p2 dependent=p1 existing=1.4.0 required=>=1.5.0 & <1.6.0\n"
        }
    ]
}
```

---

### Feature 5: Directed Graph Ordering & Degrees

**As a developer**, I want a generic directed-graph utility that can topologically order vertices and report their degrees, so the dependency engine (and other callers) can reuse a single correct graph implementation.

**Expected Behavior / Usage:**

The input supplies a `vertices` array and an `edges` array, where each edge is a two-element `[from, to]` pair. The utility reports four lines:

- `topological=<comma-separated vertices>` — a topological ordering where every vertex appears before the vertices it points to.
- `reverseTopological=<comma-separated vertices>` — the reverse of that ordering.
- `inDegree=<vertex:count,...>` — the number of incoming edges for each vertex, one `vertex:count` entry per vertex listed in ascending vertex order.
- `outDegree=<vertex:count,...>` — the number of outgoing edges for each vertex, in the same listing format.

**Test Cases:*[a specific wildcard string representing any-version support]`rcb_tests/public_test_cases/feature5_directed_graph.json`

```json
{
    "description": "Given a directed graph described by a set of vertices and a set of directed edges (each edge a from/to pair), report four derived results: a topological ordering of the vertices (every vertex appears before the vertices it points to), the reverse of that topological ordering, the in-degree of every vertex (number of incoming edges), and the out-degree of every vertex (number of outgoing edges). Degree maps are listed with one vertex:count entry per vertex in ascending vertex order.",
    "cases": [
        {
            "input": {"action": "graph", "vertices": ["A", "B", "C", "D", "E", "F", "G"], "edges": [["A", "B"], ["B", "C"], ["B", "F"], ["D", "E"], ["F", "G"]]},
            "expected_output": "topological=D,E,A,B,F,G,C\nreverseTopological=C,G,F,B,A,E,D\ninDegree=A:0,B:1,C:1,D:0,E:1,F:1,G:1\noutDegree=A:1,B:2,C:0,D:1,E:0,F:1,G:0\n"
        }
    ]
}
```

---

### Feature 6: Plugin Metadata Parsing

**As a developer**, I want to parse a component's key/value metadata into a normalized descriptor, so the rest of the system can consume a consistent record regard[a specific boolean outcome indicating version A is less than version B] of how the metadata was authored.

**Expected Behavior / Usage:**

The input supplies a `properties` map of metadata keys to string values. Recognized keys are `plugin.id`, `plugin.description`, `plugin.class`, `plugin.version`, `plugin.provider`, `plugin.dependencies`, `plugin.requires`, and `plugin.license`. The output reports one line per descriptor field: `id`, `description`, `class`, `version`, `provider`, `requires`, `license`, and `dependencies`. Normalization rules: a missing/empty `plugin.description` yields an empty `description`; a missing/empty `plugin.requires` yields the any-version wildcard `*`; the `plugin.dependencies` value is split on commas and each non-empty token is parsed into a normalized coordinate rendered as `<id>@<versionSupport>` with a trailing `?` appended when optional (empty when there are no dependencies). Other absent fields render as empty.

**Test Cases:*[a specific wildcard string representing any-version support]`rcb_tests/public_test_cases/feature6_parse_metadata.json`

```json
{
    "description": "Parse a plugin's metadata key/value map into a normalized descriptor. The recognized keys are the plugin id, description, implementation class, version, provider, a comma-separated dependencies list, a version-requires expression, and a license. The descriptor echoes each field; an absent description normalizes to the empty string, an absent requires expression normalizes to the any-version wildcard, and the dependencies list is parsed into normalized coordinate tokens (identifier, an at-sign, the version-support expression which defaults to the wildcard, and a trailing question mark when optional).",
    "cases": [
        {
            "input": {"action": "parse_metadata", "properties": {
                "plugin.id": "alpha-plugin",
                "plugin.class": "com.example.plugins.SamplePlugin",
                "plugin.version": "0.0.1",
                "plugin.description": "Sample plugin one",
                "plugin.provider": "Acme Corp",
                "plugin.dependencies": "beta-plugin,gamma-plugin@~1.0",
                "plugin.requires": ">=1",
                "plugin.license": "Apache-2.0"
            }},
            "expected_output": "id=alpha-plugin\ndescription=Sample plugin one\nclass=com.example.plugins.SamplePlugin\nversion=0.0.1\nprovider=Acme Corp\nrequires=>=1\nlicense=Apache-2.0\ndependencies=beta-plugin@*,gamma-plugin@~1.0\n"
        },
        {
            "input": {"action": "parse_metadata", "properties": {
                "plugin.id": "beta-plugin",
                "plugin.class": "com.example.plugins.SamplePlugin",
                "plugin.version": "0.0.1",
                "plugin.provider": "Acme Corp",
                "plugin.dependencies": ""
            }},
            "expected_output": "id=beta-plugin\ndescription=\nclass=com.example.plugins.SamplePlugin\nversion=0.0.1\nprovider=Acme Corp\nrequires=*\nlicense=\ndependencies=\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:*[a specific wildcard string representing any-version support]A cleanly structured codebase implementing the features above (semantic-version reasoning, dependency-coordinate parsing, a generic directed graph, a dependency resolver, and a metadata parser). Its physical structure MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:*[a specific wildcard string representing any-version support]A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, dispatches on the `action` field (`version_constraint`, `version_compare`, `parse_dependency`, `resolve_dependencies`, `graph`, `parse_metadata`), invokes the appropriate core logic, and prints the result to stdout, matching the per-feature contracts above. Native errors raised by the core (e.g. an invalid or missing version) MUST be translated by the adapter into the neutral `error=<category>` lines specified above; the host language's runtime exception identity must never leak into stdout.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only*[a specific wildcard string representing any-version support]the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same ordering convention as the headers module
- use the wildcard used in C008 if no @ symbol exists
