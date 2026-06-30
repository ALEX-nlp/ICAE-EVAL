## Product Requirement Document

# Module Dependency Tree Resolver — Compute the Transitive Source-File Set of an Entry Module

## Project Goal

Build a library that, given an entry source file and the directory that contains a related set of source files, walks that file's declared dependencies and returns the flat set of every distinct local source file reachable from the entry. It lets developers obtain the complete on-disk footprint of a module — for bundling, impact analysis, or cache invalidation — without hand-tracing imports across files.

---

## Background & Problem

Without this library, developers must manually open each source file, read its import/require directives, follow every referenced sibling, and repeat the process transitively while remembering which files they have already seen and breaking import cycles by hand. This is tedious and error-prone, especially across the several different ways a file can declare its dependencies (array-and-callback module definitions, synchronous requires, static import declarations, stylesheet at-imports).

With this library, the developer supplies a single entry file plus the root directory of the file set and receives back the full, de-duplicated set of reachable source files. The traversal handles multiple dependency-declaration syntaxes, ignores runtime built-in modules, terminates safely on cyclic graphs, tolerates a missing entry file, and supports an optional precomputed cache so that already-known sub-trees are not recomputed.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a focused traversal utility; a small, cleanly separated core (dependency extraction, path resolution, recursive traversal with de-duplication) is appropriate. Do not inflate it into a sprawling framework, but keep the dependency-extraction, path-resolution, and traversal concerns logically distinct.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases in "Core Features" are a black-box contract for an execution adapter, NOT the core data model. The core traversal logic MUST operate purely on file paths and return an in-memory list of paths; it must know nothing about JSON, stdin, or stdout. A separate execution adapter translates JSON commands into core calls and renders the result.

3. **Adherence to SOLID Design Principles:** Separate the extraction of a single file's direct dependencies, the resolution of a raw dependency reference to an absolute file path, and the recursive cycle-safe traversal into distinct cohesive units. The traversal engine must be extensible to new dependency-declaration syntaxes without being rewritten.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public entry point should be a simple call taking an entry file, a root directory, and an optional cache, returning a list of file paths.
   - **Resilience:** A non-existent entry file must yield an empty result rather than an error. Cyclic dependency graphs must terminate. Missing required arguments must be rejected with a clear, modeled error.

---

## Core Features

### Feature 1: Resolve the dependency tree across module-declaration syntaxes

**As a developer**, I want to hand the resolver an entry file and its root directory and get back every local source file reachable from it, so I can see a module's full on-disk footprint regardless of how its dependencies are declared.

**Expected Behavior / Usage:**

The input names an entry file (a path relative to a fixed source-set base) and the root directory that contains the related files. The resolver reads the entry file, extracts its directly declared dependencies, resolves each to a concrete sibling file inside the root, and recurses. The output is the set of every distinct reachable source file **including the entry itself**, with one file path per line, **sorted lexicographically**. Paths are reported relative to the source-set base. Pure runtime built-in references and bare external package names that do not correspond to a local file contribute nothing on their own; only files that resolve to the local set appear. This feature point is exercised across four distinct dependency-declaration styles, each as its own leaf.

*1.1 Array-and-callback module definitions — entry declares its dependencies as a list passed to a definition call*

The entry lists two sibling references; one of those siblings in turn references the other. The resolved set is the entry plus both siblings (three files total), de-duplicated and sorted.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_amd.json`

```json
{
  "description": "Resolve the complete dependency tree for an entry module declared with the array-and-callback module-definition syntax, given the directory that holds the module set; the output is the sorted set of every distinct source file reachable through the entry's declared dependencies, including the entry itself.",
  "cases": [
    {"input": {"entry": "amd/a.js", "root": "amd"},
     "expected_output": "amd/a.js\namd/b.js\namd/c.js\n"}
  ]
}
```

*1.2 Synchronous require calls — entry pulls in siblings through inline require expressions*

The entry requires two siblings; the resolved set is the entry plus both siblings, sorted.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_commonjs.json`

```json
{
  "description": "Resolve the complete dependency tree for an entry module that pulls in siblings through synchronous require calls, given its containing directory; the output is the sorted set of every distinct local source file transitively reachable from the entry, including the entry itself.",
  "cases": [
    {"input": {"entry": "commonjs/a.js", "root": "commonjs"},
     "expected_output": "commonjs/a.js\ncommonjs/b.js\ncommonjs/c.js\n"}
  ]
}
```

*1.3 Static import declarations — entry pulls in siblings through static import statements*

The entry imports two siblings; the resolved set is the entry plus both siblings, sorted.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_es6.json`

```json
{
  "description": "Resolve the complete dependency tree for an entry module that pulls in siblings through static import declarations, given its containing directory; the output is the sorted set of every distinct local source file transitively reachable from the entry, including the entry itself.",
  "cases": [
    {"input": {"entry": "es6/a.js", "root": "es6"},
     "expected_output": "es6/a.js\nes6/b.js\nes6/c.js\n"}
  ]
}
```

*1.4 Stylesheet at-import directives — entry pulls in partials, with or without an explicit extension*

The stylesheet entry imports two partials, one referenced without a file extension and one with it; both resolve to concrete partial files. The resolved set is the entry plus both partials, sorted.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_sass.json`

```json
{
  "description": "Resolve the complete dependency tree for a stylesheet entry that pulls in partials through at-import directives, given its containing directory; partials referenced with or without a file extension both resolve, and the output is the sorted set of every distinct stylesheet file transitively reachable from the entry, including the entry itself.",
  "cases": [
    {"input": {"entry": "sass/a.scss", "root": "sass"},
     "expected_output": "sass/_b.scss\nsass/_c.scss\nsass/a.scss\n"}
  ]
}
```

---

### Feature 2: Terminate safely on cyclic dependency graphs

**As a developer**, I want traversal to terminate even when two files import each other, so I can analyze real codebases that contain dependency cycles without the tool hanging or looping.

**Expected Behavior / Usage:**

The input is an entry whose file references a sibling that, in turn, references the entry back, forming a cycle. The resolver must mark files as visited eagerly so the cycle is broken; each participating file appears exactly once in the result. The output is the sorted set of the two mutually-dependent files.

**Test Cases:** `rcb_tests/public_test_cases/feature2_cyclic.json`

```json
{
  "description": "Resolve the dependency tree for a module set in which two files depend on each other, forming a cycle; traversal must terminate and each participating file must appear exactly once in the sorted output rather than looping indefinitely.",
  "cases": [
    {"input": {"entry": "cyclic/a.js", "root": "cyclic"},
     "expected_output": "cyclic/a.js\ncyclic/b.js\n"}
  ]
}
```

---

### Feature 3: Exclude runtime built-in modules

**As a developer**, I want references to runtime built-in (standard-library) modules to be excluded from the resolved set, so the tree contains only the project's own source files.

**Expected Behavior / Usage:**

The input is an entry whose only declared dependency is a runtime built-in module rather than a local file. Built-in references resolve to nothing on disk and are excluded, so the output contains only the entry file itself.

**Test Cases:** `rcb_tests/public_test_cases/feature3_core_exclusion.json`

```json
{
  "description": "Resolve the dependency tree for an entry module whose only dependency is a runtime built-in (standard-library) module; built-in modules are excluded from the resolved set, so the output contains only the entry file itself.",
  "cases": [
    {"input": {"entry": "commonjs/b.js", "root": "commonjs"},
     "expected_output": "commonjs/b.js\n"}
  ]
}
```

---

### Feature 4: Tolerate a non-existent entry file

**As a developer**, I want a request for a file that is not on disk to return an empty result instead of raising, so I can call the resolver opportunistically without guarding every path.

**Expected Behavior / Usage:**

The input names an entry path that does not exist under the source-set base. The resolver completes normally and yields an empty set; the output is empty (no lines).

**Test Cases:** `rcb_tests/public_test_cases/feature4_nonexistent_entry.json`

```json
{
  "description": "Request the dependency tree for an entry path that does not exist on disk; resolution must complete without raising an error and yield an empty set, so the output is empty.",
  "cases": [
    {"input": {"entry": "missing-file", "root": "amd"},
     "expected_output": ""}
  ]
}
```

---

### Feature 5: Reuse a precomputed cache (memoization)

**As a developer**, I want to pass in already-known sub-results so the resolver skips recomputing them, so I can amortize repeated analyses across an evolving file set.

**Expected Behavior / Usage:**

The optional third input is a cache mapping an absolute-equivalent file path to its previously resolved list of files. When traversal reaches a cached file it reuses the stored list instead of re-reading and re-walking that file.

*5.1 Cached intermediate sub-tree — a non-entry file is pre-seeded with its own resolved list*

The cache pre-seeds one intermediate file with its resolved sub-list. That file's sub-tree is taken from the cache rather than recomputed, yet the final sorted set is identical to resolving everything from scratch.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_cache_subtree.json`

```json
{
  "description": "Resolve the dependency tree while supplying a precomputed cache that already maps one intermediate file to its own resolved sub-list; the cached sub-tree is reused instead of being recomputed, yet the final sorted set is identical to resolving from scratch.",
  "cases": [
    {"input": {"entry": "amd/a.js", "root": "amd",
               "cache": {"amd/b.js": ["amd/b.js", "amd/c.js"]}},
     "expected_output": "amd/a.js\namd/b.js\namd/c.js\n"}
  ]
}
```

*5.2 Cached entry point — the entry file itself is pre-seeded with an empty list*

When the cache already maps the entry file to a list (here, an empty one), that precomputed list is returned directly and no traversal occurs. With an empty cached list, the output is empty.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_cache_entry.json`

```json
{
  "description": "Resolve the dependency tree while supplying a precomputed cache that already maps the entry file itself to an empty resolved list; the cached entry short-circuits all traversal, so the output is empty.",
  "cases": [
    {"input": {"entry": "amd/a.js", "root": "amd",
               "cache": {"amd/a.js": []}},
     "expected_output": ""}
  ]
}
```

---

### Feature 6: Reject missing required arguments

**As a developer**, I want the resolver to reject calls that omit a required argument with a clear, neutral error category, so misuse fails fast instead of producing misleading empty results.

**Expected Behavior / Usage:**

Both the entry file and the root directory are required. When one is omitted (provided as null/absent), the call is rejected and the adapter emits a single neutral error-category line — `error=missing_filename` when the entry is absent, `error=missing_root` when the root is absent — with no other output.

*6.1 Missing entry file*

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_missing_filename.json`

```json
{
  "description": "Request a dependency tree without providing the required entry file argument; the operation rejects the call and the adapter reports the neutral missing-entry error category.",
  "cases": [
    {"input": {"entry": null, "root": "amd"},
     "expected_output": "[a specific neutral error format string defined in error_constants]"}
  ]
}
```

*6.2 Missing root directory*

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_missing_root.json`

```json
{
  "description": "Request a dependency tree with an entry file but without the required root-directory argument; the operation rejects the call and the adapter reports the neutral missing-root error category.",
  "cases": [
    {"input": {"entry": "amd/a.js", "root": null},
     "expected_output": "[a specific neutral error format string defined in error_constants]"}
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured library implementing the traversal described above — dependency extraction, dependency-reference-to-path resolution, and cycle-safe recursive traversal with de-duplication and optional caching — decoupled from all I/O.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON command from stdin (`entry`, `root`, optional `cache`, with paths relative to a shipped source-set base), invokes the core resolver, and prints the result to stdout per the per-feature contracts: a sorted, newline-terminated list of base-relative file paths on success, an empty output for an empty set, and a neutral `error=<category>` line for rejected calls. The adapter — not the core — is responsible for path normalization and for translating any native error into the neutral category line.

3. **Automated test harness:** A single entry point `bash rcb_tests/test.sh` that reads every `*.json` case file from a case directory and runs the full suite, accepting `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{stem}@{index:03}.txt` containing only the raw stdout of the program under test, directly comparable to `expected_output`.


---
**Implementation notes:**
- follow the same resolution strategy as the legacy AMD loader
- decode paths exactly like the common-jobs pipeline does
