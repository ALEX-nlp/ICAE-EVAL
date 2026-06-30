## Product Requirement Document

# Deployment Parameter-Set Generator — Deriving Template Parameter Maps from Declarative Sources

## Project Goal

Build a reusable parameter-set generator that turns declarative descriptions of *where* deployments should come from into a concrete, ordered list of parameter maps, so a templating engine can stamp out one deployment per map without each tool re-implementing source discovery and parameter extraction.

---

## Background & Problem

A fleet-management tool needs to instantiate many near-identical deployments from a single template, varying only a handful of parameters per instance (which cluster, which path, which config values). The hard part is deciding the *set* of parameter maps: sometimes they are listed inline, sometimes they are discovered by scanning the directories of a source tree, and sometimes they are read out of structured config files committed alongside the code.

Without a shared generator, every tool hand-rolls its own discovery and flattening logic, leading to inconsistent key naming, non-deterministic ordering, and silent divergence between "what the source says" and "what got deployed". This component defines one contract: given a declarative source, produce an ordered list of string-to-string parameter maps with stable, well-defined keys. It covers a static inline list, a directory scan filtered by glob patterns, and a config-file scan that flattens nested JSON into dotted keys. Failures in the underlying source-of-record (the thing that lists or reads source content) propagate as a clean failure rather than a partial or empty success.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain. In particular, the source-of-record that lists directories, lists files, and reads file content MUST be an injectable abstraction, so the generators run as pure functions over in-memory inputs.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification — adding a new kind of source must not require editing existing generators.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults. When the source-of-record reports a failure, the generator must surface that failure rather than swallow it.

---

## Core Features

Every feature shares one shaped result. A generator produces an **ordered list of parameter maps**; each map is a set of string keys to string values. The execution adapter renders that result to stdout as follows: a first line `params=<N>` where `N` is the number of maps; then, for each map in order, a line `#<i>` (its zero-based position) followed by one `key=value` line per entry, the entries sorted by key. When the underlying source-of-record fails, the adapter instead prints exactly one line, `error=source_unavailable`, and no maps. Every emitted line is terminated by a newline.

### Feature 1: Inline List Parameter Generation

**As a developer**, I want to declare a fixed list of targets inline and get one parameter map per entry, so I can drive a template from a small, hand-maintained set without any source scanning.

**Expected Behavior / Usage:**

The input has an action of `list` and an `elements` array. Each element supplies a `cluster` (an identifier string), a `url` (a server address string), and an optional `values` object of extra string-to-string pairs. The generator emits one parameter map per element, in the order the elements were given. Each map always contains the cluster identifier under the fixed key `cluster` and the url under the fixed key `url`; in addition, every entry of that element's `values` object contributes a key formed by prefixing its own name with `values.` (the literal text `values` then a dot), mapped to its value. An element with an empty `values` object yields a map with just the two fixed keys. The set of keys in a map does not depend on the order pairs were supplied — the adapter renders each map's keys sorted.

**Test Cases:** `rcb_tests/public_test_cases/feature1_list_params.json`

```json
{
    "description": "Generate one parameter map per element of a static input list. Each element supplies a cluster identifier, a server url, and an optional map of extra key/value pairs. The generator emits, in input order, one parameter map per element: the cluster identifier under a fixed cluster key, the url under a fixed url key, and each extra pair under a key formed by prefixing its name with values. and a dot. The element order is preserved and the set of keys within each map does not depend on insertion order.",
    "cases": [
        {
            "input": {"action": "list", "elements": [{"cluster": "cluster", "url": "url", "values": {}}]},
            "expected_output": "params=1\n#0\ncluster=cluster\nurl=url\n"
        },
        {
            "input": {"action": "list", "elements": [{"cluster": "cluster", "url": "url", "values": {"foo": "bar"}}]},
            "expected_output": "params=1\n#0\ncluster=cluster\nurl=url\nvalues.foo=bar\n"
        }
    ]
}
```

---

### Feature 2: Directory-Scan Parameter Generation

**As a developer**, I want to point at a source tree and select target directories by glob pattern, so each matching directory becomes a deployment without me listing them by hand.

**Expected Behavior / Usage:**

The input has an action of `git_directories`, a `directories` array of glob patterns, and an `apps` array that stands in for the flat listing of candidate directory paths the source-of-record would return. The generator retains a candidate path when it matches at least one pattern under shell-style globbing where a single `*` matches any run of characters *within one path segment* and does NOT cross the path separator `/` (so `*` matches `app1` but not `p1/app3`; `p1/*/*` matches `p1/p2/app3` but not `p1/p2/p3/app4`). Matching is considered pattern-by-pattern, then candidate-by-candidate, preserving that order in the output. For each retained path the generator emits a map with the full path under key `path` and the final path segment (the base name after the last `/`) under key `path.basename`. An empty candidate listing yields zero maps (`params=0`). If the candidate listing cannot be obtained from the source-of-record, the whole operation fails and the neutral error line is produced.

**Test Cases:** `rcb_tests/public_test_cases/feature2_directory_scan.json`

```json
{
    "description": "Scan a flat listing of candidate directory paths and keep only those matching a set of shell-style glob patterns, where a single star matches within one path segment and does not cross the path separator. For every retained path, emit a parameter map holding the full path under a path key and its final path segment under a path.basename key, considering the patterns and paths in their given order. If the directory listing cannot be obtained, the whole operation fails with a neutral error and no maps are produced. An empty listing yields zero maps.",
    "cases": [
        {
            "input": {"action": "git_directories", "directories": ["*"], "apps": ["app1", "app2", "p1/app3"]},
            "expected_output": "params=2\n#0\npath=app1\npath.basename=app1\n#1\npath=app2\npath.basename=app2\n"
        },
        {
            "input": {"action": "git_directories", "directories": ["*"], "apps": [], "apps_error": true},
            "expected_output": "error=source_unavailable\n"
        }
    ]
}
```

---

### Feature 3: Config-File-Scan Parameter Generation

**As a developer**, I want to read structured config files committed in the source and turn each into a parameter map, so the deployment parameters live next to the code they configure.

**Expected Behavior / Usage:**

The input has an action of `git_files`, a `files` array of file-path patterns, a `paths` array standing in for the matching file paths the source-of-record would return, a `file_contents` object mapping each path to its raw JSON text, and an optional `file_errors` array naming paths whose content cannot be read. The generator collects all matching paths, removes duplicates, and sorts them; it then processes them in that sorted order, producing exactly one parameter map per file in that order. Each map is built by parsing the file's JSON object and flattening it into single-level keys: a nested value's key is the dot-joined chain of property names leading to it (e.g. a value at `cluster` → `owner` becomes key `cluster.owner`), and only leaf string values are emitted. If the path listing cannot be obtained (a listing failure), or any file's content cannot be read (a read failure), the whole operation fails and the neutral error line is produced, with no partial maps.

**Test Cases:** `rcb_tests/public_test_cases/feature3_file_scan.json`

```json
{
    "description": "Scan a set of matching configuration file paths, deduplicate and sort them, then read each file's JSON content and flatten its nested object into a single-level parameter map whose keys are the dot-joined paths to each leaf string value. Files are processed in sorted path order, producing one parameter map per file in that order. If the path listing or any file's content cannot be obtained, the whole operation fails with a neutral error and no maps are produced.",
    "cases": [
        {
            "input": {
                "action": "git_files",
                "files": ["**/config.json"],
                "paths": ["cluster-config/production/config.json", "cluster-config/staging/config.json"],
                "file_contents": {
                    "cluster-config/production/config.json": "{\"cluster\":{\"owner\":\"john.doe@example.com\",\"name\":\"production\",\"address\":\"https://kubernetes.default.svc\"},\"key1\":\"val1\",\"key2\":{\"key2_1\":\"val2_1\",\"key2_2\":{\"key2_2_1\":\"val2_2_1\"}}}",
                    "cluster-config/staging/config.json": "{\"cluster\":{\"owner\":\"foo.bar@example.com\",\"name\":\"staging\",\"address\":\"https://kubernetes.default.svc\"}}"
                }
            },
            "expected_output": "params=2\n#0\ncluster.address=https://kubernetes.default.svc\ncluster.name=production\ncluster.owner=john.doe@example.com\nkey1=val1\nkey2.key2_1=val2_1\nkey2.key2_2.key2_2_1=val2_2_1\n#1\ncluster.address=https://kubernetes.default.svc\ncluster.name=staging\ncluster.owner=foo.bar@example.com\n"
        },
        {
            "input": {
                "action": "git_files",
                "files": ["**/config.json"],
                "paths": ["cluster-config/production/config.json", "cluster-config/staging/config.json"],
                "file_contents": {
                    "cluster-config/production/config.json": "{\"cluster\":{\"owner\":\"john.doe@example.com\",\"name\":\"production\",\"address\":\"https://kubernetes.default.svc\"}}"
                },
                "file_errors": ["cluster-config/staging/config.json"]
            },
            "expected_output": "error=source_unavailable\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the three generators above behind a common abstraction that returns an ordered list of string-to-string parameter maps. The source-of-record (listing directories, listing files, reading file content) MUST be an injectable dependency so the generators stay pure and testable without any network, repository, or cluster access. The core business logic must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, selects a generator by the request's `action` (`list`, `git_directories`, or `git_files`), supplies an in-memory source-of-record built from the request fields, invokes the generator, and prints the result to stdout using the shared contract: `params=<N>`, then per map a `#<i>` line followed by sorted `key=value` lines; or the single line `error=source_unavailable` when the source-of-record reports a failure. The adapter is solely responsible for translating any host-language failure raised by the core into that neutral error line.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same dot-flattening logic as imports found in main
