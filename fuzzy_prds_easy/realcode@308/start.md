## Product Requirement Document

# Code Coverage Toolkit — Instrumentation Support, Hit Aggregation & Reporting Configuration

## Project Goal

Build a code-coverage toolkit core that lets developers measure which lines of their compiled code actually run during a test suite, and configure how coverage is collected and reported, without hand-writing the bookkeeping that coverage measurement normally requires. The toolkit owns the supporting machinery around instrumentation: pruning a call graph to the code under test, aggregating per-line hit counts gathered at runtime, persisting and reloading coverage records, deriving the companion file names involved in rewriting binaries, discovering extra assembly lookup directories, and parsing the command-line options that drive the whole flow.

---

## Background & Problem

Without a toolkit like this, developers measuring coverage are forced to manually splice tracking instructions into their binaries, invent an ad-hoc on-disk format to record which lines were hit, merge the counts coming from many test methods by hand, and remember which backup/symbol files belong to which assembly. They must also reimplement the same option parsing (default file names, glob defaults, percentage thresholds, verbosity levels, working-directory switching) for every project. This is repetitive, error-prone boilerplate that is easy to get subtly wrong — a mis-merged count or a wrong default path silently corrupts a coverage report.

With this toolkit, the supporting behavior is provided as small, composable, well-specified operations: feed in raw data (a graph, a set of hit records, raw bytes, a config string, an option value) and get back a precise, deterministic result. The instrumentation engine and the report writers build on top of these primitives, and the command-line surface is reduced to declarative option definitions with predictable defaults and resolution rules.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility system (graph algorithms, runtime hit aggregation, binary serialization, file-name derivation, configuration document parsing, and a command-line option layer). It MUST NOT be a single "god file". Output a clear, multi-file directory tree separating the core measurement primitives, the configuration/option layer, and the execution adapter. Do not over-engineer the individual leaf operations, but keep each responsibility in its own cohesive module.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a black-box contract for an execution adapter, NOT the internal data model. The core logic must be decoupled from stdin/stdout and JSON. The adapter is solely responsible for translating JSON commands into idiomatic calls to the core and rendering results as the stdout contract.

3. **Adherence to SOLID Design Principles:**
   - **SRP:** Keep parsing, validation, core computation, and output formatting in distinct units.
   - **OCP:** New report-output options, glob options, or graph node types should extend the system without modifying the core engine.
   - **LSP:** All option kinds that share a category (file path, directory path, glob list) must be substitutable behind a common abstraction.
   - **ISP:** Keep option/abstraction interfaces small and focused (single-value vs. multi-value options, file vs. directory options).
   - **DIP:** The core must depend on a file-system abstraction, not directly on the physical disk, so behavior is deterministic and testable.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public surface must be elegant and idiomatic to the target language, hiding internal complexity.
   - **Resilience:** Edge cases (cycles in the graph, duplicate hit records, empty/blank config documents, missing files, unparseable option values) must be handled deterministically. Invalid input must be surfaced as a modeled validation error, not a generic crash, and the error rendered as a neutral, language-independent category.

---

## Core Features

### Feature 1: Call Graph Filtering

**As a developer**, I want to prune a directed call graph down to only the nodes I care about while preserving reachability through removed nodes, so I can focus a coverage view on the code under test without losing the structural links between kept nodes.

**Expected Behavior / Usage:**

The input is a directed graph described by an adjacency map (`children`: parent value -> list of child values, in declared order), a `root` value, and an `allowed` set of values. A node whose value is in the allowed set is kept. A node whose value is not allowed is removed, and each of its children is re-attached to the removed node's parent position, so paths through removed nodes are preserved. If the root itself is removed, its surviving descendants become the new top-level set. The result is rendered as a nested text form: `v` is a kept node, `v[...]` lists that node's retained children, and `*v` marks a back-reference to a node already shown earlier on the path (i.e. a cycle / shared node). Cycles and self-references must terminate (no infinite recursion). Children at each level are listed in ascending value order so the rendering is deterministic.

**Test Cases:** `rcb_tests/public_test_cases/feature1_call_graph_filtering.json`

```json
{
    "description": "Filters a directed call graph down to a whitelist of allowed node values. Nodes whose value is allowed are kept; nodes whose value is not allowed are spliced out, with their children re-attached to the removed node's parent. The result is rendered as a nested text form where `v[..]` lists a node's retained children and `*v` marks a back-reference to an already-visited node (a cycle). Children at each level are listed in ascending value order.",
    "cases": [
        {"input": {"op": "filter_graph", "children": {"1": [2], "2": [3], "3": [2]}, "root": 1, "allowed": [1, 2, 3]}, "expected_output": "1[2[3[*2]]]\n"},
        {"input": {"op": "filter_graph", "children": {"1": [2], "2": [3], "3": [2]}, "root": 1, "allowed": [1]}, "expected_output": "1\n"},
        {"input": {"op": "filter_graph", "children": {"1": [2], "2": [2]}, "root": 1, "allowed": [1, 2]}, "expected_output": "1[2[*2]]\n"},
        {"input": {"op": "filter_graph", "children": {"1": [2], "2": [2]}, "root": 1, "allowed": [1]}, "expected_output": "1\n"},
        {"input": {"op": "filter_graph", "children": {"1": [2, 3]}, "root": 1, "allowed": [2, 3]}, "expected_output": "2,3\n"},
        {"input": {"op": "filter_graph", "children": {"1": [2, 3], "2": [1, 7, 8], "3": [4, 5, 6], "4": [5], "5": [4], "6": [7, 8, 6, 3]}, "root": 1, "allowed": [1, 2, 3, 8]}, "expected_output": "1[2[*1,8],3[*3,*8]]\n"},
        {"input": {"op": "filter_graph", "children": {"1": [2, 3], "2": [4], "3": [4], "4": [5]}, "root": 1, "allowed": [1, 5]}, "expected_output": "1[5]\n"},
        {"input": {"op": "filter_graph", "children": {"1": [2, 3], "2": [5], "3": [4], "4": [5], "5": [6]}, "root": 1, "allowed": [1, 2, 3, 6]}, "expected_output": "1[2[6],3[*6]]\n"}
    ]
}
```

---

### Feature 2: Hit Aggregation

**As a developer**, I want per-line hit counts gathered independently by many test executions to be merged into one coherent picture, so I can ask how many times a line ran in total and from how many distinct execution contexts.

**Expected Behavior / Usage:**

The input is a list of recording `contexts`, each identified by an `(assembly, class, method)` triple and carrying a `hits` map of line id -> count, plus a `query` list of line ids. Contexts that share the same identity triple are first merged into a single context whose per-line counts are the element-wise sums. For each queried line id the result reports, on one line, the total hit count summed across all contexts and the number of distinct contexts that recorded that line; then, one line per contributing context, that context's hit count for the queried id. Contexts are reported in stable first-seen order.

**Test Cases:** `rcb_tests/public_test_cases/feature2_hit_aggregation.json`

```json
{
    "description": "Aggregates per-line hit counts collected from many recording contexts. Each context is identified by an (assembly, class, method) triple and carries a map of line id -> hit count. Contexts that share the same triple are merged into one (their per-line counts summed). For each queried line id the aggregate reports the total hit count across all contexts and how many distinct contexts touched that line, followed by the per-context hit count for that line.",
    "cases": [
        {"input": {"op": "merge_hits", "contexts": [{"assembly": "A", "class": "C", "method": "XUnitTest2", "hits": {"17": 2500000}}, {"assembly": "A", "class": "C", "method": "NUnitTest2", "hits": {"17": 2500000}}], "query": [17]}, "expected_output": "id=17 total=5000000 contexts=2\ncontext[0] hits=2500000\ncontext[1] hits=2500000\n"},
        {"input": {"op": "merge_hits", "contexts": [{"assembly": "A", "class": "C", "method": "XUnitTest2", "hits": {"8": 1}}, {"assembly": "A", "class": "C", "method": "XUnitTest2", "hits": {"8": 1}}], "query": [8]}, "expected_output": "id=8 total=2 contexts=1\ncontext[0] hits=2\n"},
        {"input": {"op": "merge_hits", "contexts": [{"assembly": "A", "class": "C", "method": "M1", "hits": {"8": 1, "9": 1}}, {"assembly": "A", "class": "C", "method": "M2", "hits": {"8": 1}}], "query": [8, 9]}, "expected_output": "id=8 total=2 contexts=2\ncontext[0] hits=1\ncontext[1] hits=1\nid=9 total=1 contexts=1\ncontext[0] hits=1\n"}
    ]
}
```

---

### Feature 3: Coverage Record Serialization

**As a developer**, I want a coverage recording context to be written to a compact binary form and read back without loss, so collected coverage can be persisted to disk during a test run and reloaded later for reporting.

**Expected Behavior / Usage:**

The input is a single recording context: the `(assembly, class, method)` identity and a `hits` map of line id -> count. The operation serializes the context to a binary stream and immediately deserializes it back. The recovered data must equal the original in every field. The result reports the number of records recovered (one), the three identity strings, and the recovered line/hit pairs in ascending line-id order.

**Test Cases:** `rcb_tests/public_test_cases/feature3_coverage_record_serialization.json`

```json
{
    "description": "Serializes a coverage recording context (assembly, class and method identity plus a map of line id -> hit count) into a compact binary stream and reads it back. The round trip must preserve every field exactly: the number of recovered records, the three identity strings, and all line/hit pairs. Recovered hit pairs are reported in ascending line-id order.",
    "cases": [
        {"input": {"op": "roundtrip_hit_context", "assembly": "Asm", "class": "Ns.Type", "method": "DoWork", "hits": {"1": 15}}, "expected_output": "count=1\nassembly=Asm\nclass=Ns.Type\nmethod=DoWork\nhits=1:15\n"},
        {"input": {"op": "roundtrip_hit_context", "assembly": "Sample.UnitTests", "class": "Sample.UnitTests.UnitTest1", "method": "Test", "hits": {"8": 1, "19": 50, "23": 2500050}}, "expected_output": "count=1\nassembly=Sample.UnitTests\nclass=Sample.UnitTests.UnitTest1\nmethod=Test\nhits=8:1,19:50,23:2500050\n"}
    ]
}
```

---

### Feature 4: Artifact File Utilities

**As a developer**, I want small, reliable helpers for fingerprinting binaries and deriving the companion file names involved in rewriting them, so the instrumentation flow can detect changes and manage backups/symbols safely.

**Expected Behavior / Usage:**

*4.1 Content Hash — fingerprint raw bytes*

Given the raw bytes of an artifact, produce a stable content fingerprint: the MD5 digest rendered as an uppercase hexadecimal string with no separators.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_content_hash.json`

```json
{
    "description": "Computes a stable content fingerprint for a binary artifact, given its raw bytes. The fingerprint is the MD5 digest rendered as an uppercase hexadecimal string with no separators.",
    "cases": [
        {"input": {"op": "file_hash", "bytes": [1, 2, 3, 4, 5]}, "expected_output": "7CFDD07889B3295D6A550914AB35E068\n"}
    ]
}
```

*4.2 Debug-Symbol Path — derive the symbols file path*

Given a compiled assembly path, derive its companion debug-symbols path by replacing the assembly extension with the debug-symbols extension (`pdb`), keeping the directory and base name unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_debug_symbol_path.json`

```json
{
    "description": "Derives the companion debug-symbols file path for a compiled assembly path by replacing the assembly's extension with the debug-symbols extension (`pdb`), keeping the directory and base name unchanged.",
    "cases": [
        {"input": {"op": "pdb_path", "path": "/test/ACME.Something.dll"}, "expected_output": "path=/test/ACME.Something.pdb\n"}
    ]
}
```

*4.3 Backup Path — derive the backup file path*

Given an assembly path, derive the backup path used to preserve the original (unmodified) copy before rewriting. The backup name inserts an `uninstrumented` marker before the original extension, keeping the directory and base name unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_backup_path.json`

```json
{
    "description": "Derives the backup file path used to preserve the original, unmodified copy of an assembly before it is rewritten. The backup name inserts an `uninstrumented` marker before the original extension, keeping the directory and base name unchanged.",
    "cases": [
        {"input": {"op": "backup_path", "path": "/test/ACME.Something.dll"}, "expected_output": "path=/test/ACME.Something.uninstrumented.dll\n"}
    ]
}
```

*4.4 Backup Detection — recognize a backup file*

Given a file path, decide whether it refers to a backup (original, unmodified) artifact by detecting the `uninstrumented` marker in the file name. Report the bare file name and the boolean verdict.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_backup_detection.json`

```json
{
    "description": "Decides whether a given file path refers to a backup (original, unmodified) artifact by detecting the `uninstrumented` marker in the file name. Reports the bare file name and the boolean verdict.",
    "cases": [
        {"input": {"op": "is_backup", "path": "/test/ACME.Something.dll"}, "expected_output": "name=ACME.Something.dll\nbackup=false\n"},
        {"input": {"op": "is_backup", "path": "/test/ACME.Something.uninstrumented.dll"}, "expected_output": "name=ACME.Something.uninstrumented.dll\nbackup=true\n"}
    ]
}
```

---

### Feature 5: Runtime Probing Path Extraction

**As a developer**, I want to discover the extra directories where dependencies may be located, declared in a runtime configuration document, so the instrumentation engine can resolve assemblies that are not next to the main binary.

**Expected Behavior / Usage:**

The input is a runtime configuration document as a JSON string. Read the `runtimeOptions.additionalProbingPaths` array and return every concrete path, skipping any entry that contains a templated placeholder (a `|...|` macro such as an architecture/framework token). The result reports the count of returned paths followed by each path in order. An empty string, the literal `null`, or a document lacking the relevant section yields zero paths.

**Test Cases:** `rcb_tests/public_test_cases/feature5_probing_paths.json`

```json
{
    "description": "Extracts extra assembly probing directories from a runtime configuration document (JSON). It reads `runtimeOptions.additionalProbingPaths` and returns every concrete path, skipping any entry that contains a templated placeholder (a `|...|` token such as an architecture/framework macro). Reports the number of returned paths followed by each path. Empty input, the literal `null`, or a document without the relevant section yield zero paths.",
    "cases": [
        {"input": {"op": "probing_paths", "runtime_config": "{\"runtimeOptions\":{\"additionalProbingPaths\":[\"/root/.dotnet/store/|arch|/|tfm|\",\"/api/.nuget/packages\",\"/usr/share/dotnet/sdk/NuGetFallbackFolder\"]}}"}, "expected_output": "count=2\n/api/.nuget/packages\n/usr/share/dotnet/sdk/NuGetFallbackFolder\n"},
        {"input": {"op": "probing_paths", "runtime_config": ""}, "expected_output": "count=0\n"},
        {"input": {"op": "probing_paths", "runtime_config": "null"}, "expected_output": "count=0\n"},
        {"input": {"op": "probing_paths", "runtime_config": "{}"}, "expected_output": "count=0\n"}
    ]
}
```

---

### Feature 6: Command-Line Option Parsing

**As a developer**, I want the toolkit's command-line options to resolve to predictable values with sensible defaults, so the coverage flow behaves consistently and surfaces bad input clearly.

**Expected Behavior / Usage:**

*6.1 Output File Path — default fallback and resolution*

An output-file option resolves a path. With no value it falls back to a per-report default file name placed in the working directory; with a (possibly relative) value it resolves to an absolute path against the working directory. The `role` selects the default: `coverage`->`[standard format expressions for the specified roles — reference the role list]`, `clover`->`[standard format expressions for the specified roles — reference the role list]`, `cobertura`->`[standard format expressions for the specified roles — reference the role list]`, `ncover`->`[standard format expressions for the specified roles — reference the role list]`, `opencover`->`opencover[standard format expressions for the specified roles — reference the role list]`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_output_file_path.json`

```json
{
    "description": "Resolves the output file path for a report. When no value is supplied the option falls back to a per-report default file name placed in the working directory. When a (possibly relative) value is supplied it is resolved to an absolute path against the working directory. The `role` selects which report's default name applies: coverage->[standard format expressions for the specified roles — reference the role list], clover->[standard format expressions for the specified roles — reference the role list], cobertura->[standard format expressions for the specified roles — reference the role list], ncover->[standard format expressions for the specified roles — reference the role list], opencover->opencover[standard format expressions for the specified roles — reference the role list].",
    "cases": [
        {"input": {"op": "resolve_file_path", "role": "coverage", "workdir": "/current-directory", "value": null}, "expected_output": "path=/current-directory/[standard format expressions for the specified roles — reference the role list]\n"},
        {"input": {"op": "resolve_file_path", "role": "clover", "workdir": "/current-directory", "value": null}, "expected_output": "path=/current-directory/[standard format expressions for the specified roles — reference the role list]\n"},
        {"input": {"op": "resolve_file_path", "role": "cobertura", "workdir": "/current-directory", "value": null}, "expected_output": "path=/current-directory/[standard format expressions for the specified roles — reference the role list]\n"},
        {"input": {"op": "resolve_file_path", "role": "ncover", "workdir": "/current-directory", "value": null}, "expected_output": "path=/current-directory/[standard format expressions for the specified roles — reference the role list]\n"},
        {"input": {"op": "resolve_file_path", "role": "opencover", "workdir": "/current-directory", "value": null}, "expected_output": "path=/current-directory/opencover[standard format expressions for the specified roles — reference the role list]\n"},
        {"input": {"op": "resolve_file_path", "role": "clover", "workdir": "/current-directory", "value": "folder/file.xml"}, "expected_output": "path=/current-directory/folder/file.xml\n"}
    ]
}
```

*6.2 Output Directory Path — default fallback and resolution*

A directory option resolves a path. With no value it falls back to a per-role default folder in the working directory; with a value it resolves to an absolute path against the working directory. Defaults: `hits`->`coverage-hits`, `html`->`coverage-html`, `parent`->the working directory itself.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_output_directory_path.json`

```json
{
    "description": "Resolves an output directory path. When no value is supplied the option falls back to a per-role default folder placed in the working directory. When a (possibly relative) value is supplied it is resolved to an absolute path against the working directory. The `role` selects the default: hits->coverage-hits, html->coverage-html, parent->the working directory itself.",
    "cases": [
        {"input": {"op": "resolve_directory_path", "role": "hits", "workdir": "/current-directory", "value": null}, "expected_output": "path=/current-directory/coverage-hits\n"},
        {"input": {"op": "resolve_directory_path", "role": "html", "workdir": "/current-directory", "value": null}, "expected_output": "path=/current-directory/coverage-html\n"},
        {"input": {"op": "resolve_directory_path", "role": "parent", "workdir": "/current-directory", "value": null}, "expected_output": "path=/current-directory\n"},
        {"input": {"op": "resolve_directory_path", "role": "parent", "workdir": "/current-directory", "value": "folder"}, "expected_output": "path=/current-directory/folder\n"}
    ]
}
```

*6.3 Working Directory Switch — resolve and change*

The working-directory option resolves the supplied value (or the default `./`) against the current working directory. If the resolved directory differs from the current one it is created and becomes the new working directory; if it equals the current one nothing changes. Reports the resolved directory and the resulting current working directory.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_working_directory.json`

```json
{
    "description": "Switches the process working directory. The supplied value (or the default `./`) is resolved against the current working directory. If the resolved directory differs from the current one it is created and becomes the new working directory; if it equals the current one nothing changes. Reports the resolved directory and the resulting current working directory.",
    "cases": [
        {"input": {"op": "working_directory", "workdir": "/current-directory", "value": null}, "expected_output": "path=/current-directory\ncwd=/current-directory\n"},
        {"input": {"op": "working_directory", "workdir": "/current-directory", "value": "folder"}, "expected_output": "path=/current-directory/folder\ncwd=/current-directory/folder\n"}
    ]
}
```

*6.4 Glob Patterns — defaults and overrides*

A multi-valued glob option yields its role's default glob list when given a null or empty value, and takes a non-empty value as-is (dropping empty entries). Reports the count of patterns followed by each pattern. Defaults per role: `include-sources`->`[src/**/*.cs]`, `exclude-sources`->`[**/bin/**/*.cs, **/obj/**/*.cs]`, `include-tests`->`[tests/**/*.cs, test/**/*.cs]`, `exclude-tests`->`[**/bin/**/*.cs, **/obj/**/*.cs]`, `include-assemblies`->`[**/*.dll]`, `exclude-assemblies`->`[**/obj/**/*.dll]`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_4_glob_patterns.json`

```json
{
    "description": "Resolves a multi-valued glob option. A null or empty value yields the role's default glob list; a non-empty value is taken as-is (with empty entries dropped). Reports the number of patterns followed by each pattern. Defaults per role: include-sources->[src/**/*.cs], exclude-sources->[**/bin/**/*.cs, **/obj/**/*.cs], include-tests->[tests/**/*.cs, test/**/*.cs], exclude-tests->[**/bin/**/*.cs, **/obj/**/*.cs], include-assemblies->[**/*.dll], exclude-assemblies->[**/obj/**/*.dll].",
    "cases": [
        {"input": {"op": "resolve_globs", "role": "include-sources", "value": null}, "expected_output": "count=1\nsrc/**/*.cs\n"},
        {"input": {"op": "resolve_globs", "role": "include-tests", "value": null}, "expected_output": "count=2\ntests/**/*.cs\ntest/**/*.cs\n"},
        {"input": {"op": "resolve_globs", "role": "exclude-sources", "value": null}, "expected_output": "count=2\n**/bin/**/*.cs\n**/obj/**/*.cs\n"},
        {"input": {"op": "resolve_globs", "role": "include-assemblies", "value": null}, "expected_output": "count=1\n**/*.dll\n"},
        {"input": {"op": "resolve_globs", "role": "exclude-assemblies", "value": null}, "expected_output": "count=1\n**/obj/**/*.dll\n"},
        {"input": {"op": "resolve_globs", "role": "include-tests", "value": []}, "expected_output": "count=2\ntests/**/*.cs\ntest/**/*.cs\n"},
        {"input": {"op": "resolve_globs", "role": "include-sources", "value": ["a.cs", "**/a.cs"]}, "expected_output": "count=2\na.cs\n**/a.cs\n"}
    ]
}
```

*6.5 Coverage Threshold — percentage parsing*

The threshold option parses a percentage string into a 0..1 fraction by dividing by 100. A missing or unparseable value falls back to a default of 90 percent.

**Test Cases:** `rcb_tests/public_test_cases/feature6_5_threshold.json`

```json
{
    "description": "Parses the coverage threshold option, supplied as a percentage string, into a 0..1 fraction. A missing or unparseable value falls back to the default of 90 percent. The value is divided by 100.",
    "cases": [
        {"input": {"op": "parse_threshold", "value": null}, "expected_output": "threshold=0.9\n"},
        {"input": {"op": "parse_threshold", "value": "80.51"}, "expected_output": "threshold=0.8051\n"}
    ]
}
```

*6.6 Verbosity Level — parsing and validation*

The verbosity option changes the minimum log level. A null value leaves the current level unchanged. A recognized level name (case-insensitive, e.g. `debug` or `Debug`) sets that level. An unrecognized name is rejected with a normalized validation error that echoes the offending value. Recognized names: `Trace`, `Debug`, `Information`, `Warning`, `Error`, `Critical`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_6_verbosity.json`

```json
{
    "description": "Parses the verbosity option, which changes the minimum log level. A null value leaves the current level unchanged. A recognized level name (case-insensitive, e.g. `debug` or `Debug`) sets that level. An unrecognized name is rejected with a normalized validation error that echoes the offending value. Recognized names: Trace, Debug, Information, Warning, Error, Critical.",
    "cases": [
        {"input": {"op": "parse_verbosity", "value": null, "current": "Information"}, "expected_output": "level=Information\n"},
        {"input": {"op": "parse_verbosity", "value": "debug", "current": "Information"}, "expected_output": "level=Debug\n"},
        {"input": {"op": "parse_verbosity", "value": "Debug", "current": "Information"}, "expected_output": "level=Debug\n"},
        {"input": {"op": "parse_verbosity", "value": "InvalidLevel", "current": "Information"}, "expected_output": "error=invalid_verbosity\nvalue=InvalidLevel\n"}
    ]
}
```

*6.7 Coverage Manifest Loading — read back and validate*

The coverage-manifest option resolves a file path against the working directory (defaulting to `[standard format expressions for the specified roles — reference the role list]`). When the file exists its JSON content is parsed and the embedded source path is read back. When the file does not exist the operation fails with a normalized error reporting the resolved path that was expected.

**Test Cases:** `rcb_tests/public_test_cases/feature6_7_coverage_manifest.json`

```json
{
    "description": "Loads a previously written coverage manifest file (JSON). The path is resolved against the working directory (defaulting to [standard format expressions for the specified roles — reference the role list] when no value is given). When the file exists its content is parsed and the embedded source path is read back. When the file does not exist the operation fails with a normalized error that reports the resolved path that was expected.",
    "cases": [
        {"input": {"op": "load_coverage_manifest", "workdir": "/current-directory", "value": null, "exists": true, "content": "{\"SourcePath\": \"/source-path\"}"}, "expected_output": "path=/current-directory/[standard format expressions for the specified roles — reference the role list]\nsource_path=/source-path\n"},
        {"input": {"op": "load_coverage_manifest", "workdir": "/current-directory", "value": "folder/file.json", "exists": false}, "expected_output": "error=coverage_file_not_found\npath=/current-directory/folder/file.json\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the features above — the graph-filtering primitive, the hit-aggregation engine, the coverage-record serializer, the artifact file utilities, the runtime-config probing-path extractor, and the command-line option layer — each in its own cohesive module, decoupled from I/O behind a file-system abstraction.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core. It reads a single JSON command from stdin, dispatches on the `op` field, invokes the appropriate core logic, and prints the result to stdout exactly matching the per-leaf-feature contracts above. Native exceptions raised by the core are translated by this adapter into the neutral error categories shown in the contracts; the core itself is never coupled to stdout or JSON.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_call_graph_filtering.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_call_graph_filtering@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the output schema of the raw module
