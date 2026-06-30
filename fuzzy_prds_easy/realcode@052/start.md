## Product Requirement Document

# Native Module Rebuild Planner — A Dependency-Aware Build Orchestrator for Prebuilt-Runtime Native Addons

## Project Goal

Build a library and command-line tool that, given a project's dependency manifest and its installed module tree, decides **which native (compiled) modules need to be rebuilt** so they are binary-compatible with a specific target runtime, and which can be safely skipped. It walks the dependency graph, classifies dependencies, detects already-up-to-date builds, and produces a deterministic rebuild plan — without the developer manually tracking ABI compatibility, dependency types, or transitive native children.

---

## Background & Problem

Native addons are compiled against a specific runtime ABI (Application Binary Interface). When an application embeds a runtime whose ABI differs from the one the addons were originally compiled for, every native module must be recompiled or it will fail to load. Doing this by hand is painful: a developer must crawl the whole `node_modules` tree, figure out which packages are production vs. optional vs. development dependencies, discover native children buried under non-native parents (including scoped packages), avoid rebuilding modules that are already up to date, and recompute the correct ABI number for the target runtime version. This leads to repetitive, error-prone scripting and slow, wasteful full rebuilds on every change.

With this tool, the developer hands over the manifest and the installed tree and receives a precise plan: the resolved target ABI, the exact set of modules selected for rebuild, and how many were skipped because they were already current. The same engine also answers the supporting questions the planner needs — where the project root is, and what a manifest contains.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility system (dependency-graph traversal, ABI resolution, build-stamp comparison, project-root discovery, manifest reading, and an I/O adapter). It MUST be organized as a multi-file repository with clear separation between the core planning engine and the execution adapter. Do not collapse it into a single "god file", and do not over-engineer the smaller helpers.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in "Core Features" are a **black-box contract for the execution adapter**, not the internal data model of the core engine. The core logic must not read stdin, write stdout, or parse the test JSON. The adapter is solely responsible for translating a JSON command into idiomatic calls on the core engine and for rendering results and errors into the line-based stdout contract.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Keep graph traversal, dependency classification, ABI resolution, build-stamp comparison, root discovery, manifest reading, and output formatting in distinct units.
   - **Open/Closed Principle (OCP):** Adding a new selection rule (e.g., a new dependency category) must not require rewriting the traversal core.
   - **Liskov Substitution Principle (LSP):** Any module-descriptor variant (plain, scoped, nested child) must be handled uniformly by the traversal.
   - **Interface Segregation Principle (ISP):** Keep the planner's public surface small — a planning entry point plus a few focused query helpers.
   - **Dependency Inversion Principle (DIP):** The planner depends on abstractions for filesystem access and progress reporting, not on concrete stdout writing.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The core's public interface should be elegant and hide traversal/ABI complexity behind a simple "plan a rebuild" call.
   - **Resilience:** Invalid inputs (e.g., a non-absolute build path, a target runtime version that is not a string) must surface as well-modeled, normalized error categories rather than leaking host-language runtime details.

---

## Core Features

### Feature 1: Dependency-Aware Module Selection

**As a developer**, I want the planner to automatically discover every native module that belongs to my application's production and optional dependency closure, so I don't have to hand-curate which addons need rebuilding.

**Expected Behavior / Usage:**

The input describes a project: its manifest dependency sets (`dependencies`, `optionalDependencies`, `devDependencies`) and a `modules` list describing the installed tree. Each module entry has a `name`; `native: true` marks it as a compiled addon that is a rebuild candidate; `dependencies` declares its own child dependencies; and `children` nests modules installed privately under that module (used for transitive native children and for scoped packages whose short-name lives under a scope segment). Optionally, `buildSubdir` places the build target in a sub-package of a multi-package workspace whose root is one [a specific list of production native modules] up.

The planner selects native modules reachable through the **production** and **optional** dependency closure, **including transitive native children** discovered by descending into each selected module's own declared dependencies (a native child nested under a non-native parent is still selected). Modules reachable **only** through development dependencies are **excluded**. In a workspace layout, selection is scoped to the target sub-package's closure.

Output is three lines: `runtime_abi=<resolved ABI for the target runtime>`, `selected=<comma-separated sorted short-names>` (scoped packages contribute their short-name after the scope segment), and `skipped=<count>` (0 on a fresh tree where nothing is pre-built).

**Test Cases:** `rcb_tests/public_test_cases/feature1_dependency_selection.json`

```json
{
    "description": "Given a project manifest plus its installed module tree, the planner selects which native modules to (re)build. It walks production and optional dependencies, descends into their transitive native children (including scoped packages nested under a parent), and excludes development-only dependencies. The output reports the resolved target ABI for the requested runtime version and the sorted set of module short-names chosen for rebuild.",
    "cases": [
        {
            "input": {
                "command": "plan_rebuild",
                "runtimeVersion": "10.4.7",
                "dependencies": {"[a specific list of production native modules]": "1", "[a specific list of production native modules]": "1", "[a specific list of production native modules]": "1", "@newrelic/native-metrics": "1"},
                "optionalDependencies": {"bcrypt": "1"},
                "devDependencies": {"ffi-napi": "1"},
                "modules": [
                    {"name": "[a specific list of production native modules]", "native": true},
                    {"name": "[a specific list of production native modules]", "native": true},
                    {"name": "bcrypt", "native": true},
                    {"name": "ffi-napi", "native": true},
                    {"name": "@newrelic/native-metrics", "native": true},
                    {"name": "[a specific list of production native modules]", "dependencies": {"[a specific list of production native modules]down": "1"}, "children": [{"name": "[a specific list of production native modules]down", "native": true}]}
                ]
            },
            "expected_output": "runtime_abi=82\nselected=bcrypt,[a specific list of production native modules],[a specific list of production native modules]down,native-metrics,[a specific list of production native modules]\nskipped=0\n"
        },
        {
            "input": {
                "command": "plan_rebuild",
                "runtimeVersion": "10.4.7",
                "buildSubdir": "child-workspace",
                "dependencies": {"snappy": "1"},
                "devDependencies": {"sleep": "1"},
                "modules": [
                    {"name": "snappy", "native": true},
                    {"name": "sleep", "native": true}
                ]
            },
            "expected_output": "runtime_abi=82\nselected=snappy\nskipped=0\n"
        }
    ]
}
```

---

### Feature 2: Incremental Skip on ABI Match

**As a developer**, I want modules that are already compiled for the exact target runtime to be skipped, so repeated runs are fast and only stale binaries get rebuilt.

**Expected Behavior / Usage:**

Each previously built native module carries a build-stamp recording the architecture and the ABI it was compiled against; the input expresses this via `builtForRuntimeVersion` (the runtime version the existing binaries were built for). When the target runtime's resolved ABI equals the stamped ABI and rebuilding is not forced, every matching module is **skipped** rather than rebuilt. When the target runtime's ABI differs from the stamped ABI — for example after a runtime upgrade that changes the ABI number — the stamps no longer match and **every** module is selected for rebuild.

Output reports `runtime_abi`, the `selected` set (which modules were found as rebuild candidates), and `skipped` (how many of those were short-circuited because their stamp already matched the target ABI).

**Test Cases:** `rcb_tests/public_test_cases/feature2_incremental_skip.json`

```json
{
    "description": "The planner avoids redundant work by skipping native modules already built for the exact target runtime. Each previously built module carries a build-stamp recording the architecture and ABI it was compiled for. When every module's stamp matches the requested runtime's ABI and rebuilding is not forced, all modules are skipped. If the target runtime's ABI differs from the stamped ABI (a runtime upgrade), the stamps no longer match and every module is selected for rebuild. The output reports how many modules were skipped versus selected.",
    "cases": [
        {
            "input": {
                "command": "plan_rebuild",
                "runtimeVersion": "10.4.7",
                "builtForRuntimeVersion": "10.4.7",
                "dependencies": {"[a specific list of production native modules]": "1", "[a specific list of production native modules]": "1", "[a specific list of production native modules]": "1", "@newrelic/native-metrics": "1"},
                "optionalDependencies": {"bcrypt": "1"},
                "devDependencies": {"ffi-napi": "1"},
                "modules": [
                    {"name": "[a specific list of production native modules]", "native": true},
                    {"name": "[a specific list of production native modules]", "native": true},
                    {"name": "bcrypt", "native": true},
                    {"name": "ffi-napi", "native": true},
                    {"name": "@newrelic/native-metrics", "native": true},
                    {"name": "[a specific list of production native modules]", "dependencies": {"[a specific list of production native modules]down": "1"}, "children": [{"name": "[a specific list of production native modules]down", "native": true}]}
                ]
            },
            "expected_output": "runtime_abi=82\nselected=bcrypt,[a specific list of production native modules],[a specific list of production native modules]down,native-metrics,[a specific list of production native modules]\nskipped=5\n"
        },
        {
            "input": {
                "command": "plan_rebuild",
                "runtimeVersion": "10.4.7",
                "builtForRuntimeVersion": "3.0.0",
                "dependencies": {"[a specific list of production native modules]": "1", "[a specific list of production native modules]": "1", "[a specific list of production native modules]": "1", "@newrelic/native-metrics": "1"},
                "optionalDependencies": {"bcrypt": "1"},
                "devDependencies": {"ffi-napi": "1"},
                "modules": [
                    {"name": "[a specific list of production native modules]", "native": true},
                    {"name": "[a specific list of production native modules]", "native": true},
                    {"name": "bcrypt", "native": true},
                    {"name": "ffi-napi", "native": true},
                    {"name": "@newrelic/native-metrics", "native": true},
                    {"name": "[a specific list of production native modules]", "dependencies": {"[a specific list of production native modules]down": "1"}, "children": [{"name": "[a specific list of production native modules]down", "native": true}]}
                ]
            },
            "expected_output": "runtime_abi=82\nselected=bcrypt,[a specific list of production native modules],[a specific list of production native modules]down,native-metrics,[a specific list of production native modules]\nskipped=0\n"
        }
    ]
}
```

---

### Feature 3: Forced Full Rebuild

**As a developer**, I want a way to force every native module to rebuild regardless of existing build-stamps, so I can recover from a corrupted or untrusted build cache.

**Expected Behavior / Usage:**

When the `force` flag is set, the planner bypasses the build-stamp comparison entirely. Even if a module's stamp already matches the target ABI (the situation that would normally skip it), it is selected for rebuild and `skipped` is `0`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_force_rebuild.json`

```json
{
    "description": "When the force flag is set, the planner ignores existing build-stamps and rebuilds every native module even if it was already built for the exact target runtime. No module is reported as skipped.",
    "cases": [
        {
            "input": {
                "command": "plan_rebuild",
                "runtimeVersion": "10.4.7",
                "builtForRuntimeVersion": "10.4.7",
                "force": true,
                "dependencies": {"[a specific list of production native modules]": "1", "[a specific list of production native modules]": "1", "[a specific list of production native modules]": "1", "@newrelic/native-metrics": "1"},
                "optionalDependencies": {"bcrypt": "1"},
                "devDependencies": {"ffi-napi": "1"},
                "modules": [
                    {"name": "[a specific list of production native modules]", "native": true},
                    {"name": "[a specific list of production native modules]", "native": true},
                    {"name": "bcrypt", "native": true},
                    {"name": "ffi-napi", "native": true},
                    {"name": "@newrelic/native-metrics", "native": true},
                    {"name": "[a specific list of production native modules]", "dependencies": {"[a specific list of production native modules]down": "1"}, "children": [{"name": "[a specific list of production native modules]down", "native": true}]}
                ]
            },
            "expected_output": "runtime_abi=82\nselected=bcrypt,[a specific list of production native modules],[a specific list of production native modules]down,native-metrics,[a specific list of production native modules]\nskipped=0\n"
        }
    ]
}
```

---

### Feature 4: Allow-List Scoping

**As a developer**, I want to restrict a rebuild to an explicit list of module names, so I can rebuild just the one or two addons I'm iterating on instead of the whole tree.

**Expected Behavior / Usage:**

When an `only` list is provided, the selected set is restricted to exactly the modules whose short-name appears in the list. All other native modules in the closure are ignored, regardless of their dependency category. A single-element list selects exactly one module; a multi-element list selects exactly those modules.

**Test Cases:** `rcb_tests/public_test_cases/feature4_only_filter.json`

```json
{
    "description": "An allow-list narrows the rebuild to only the named modules. Even when the project declares many native dependencies, supplying an explicit list restricts the selected set to exactly those names (matched by module short-name), ignoring all others regardless of their dependency type.",
    "cases": [
        {
            "input": {
                "command": "plan_rebuild",
                "runtimeVersion": "10.4.7",
                "only": ["[a specific list of production native modules]"],
                "dependencies": {"[a specific list of production native modules]": "1", "[a specific list of production native modules]": "1", "[a specific list of production native modules]": "1", "@newrelic/native-metrics": "1"},
                "optionalDependencies": {"bcrypt": "1"},
                "devDependencies": {"ffi-napi": "1"},
                "modules": [
                    {"name": "[a specific list of production native modules]", "native": true},
                    {"name": "[a specific list of production native modules]", "native": true},
                    {"name": "bcrypt", "native": true},
                    {"name": "ffi-napi", "native": true},
                    {"name": "@newrelic/native-metrics", "native": true},
                    {"name": "[a specific list of production native modules]", "dependencies": {"[a specific list of production native modules]down": "1"}, "children": [{"name": "[a specific list of production native modules]down", "native": true}]}
                ]
            },
            "expected_output": "runtime_abi=82\n[a dynamic string array of allowed module names]\nskipped=0\n"
        },
        {
            "input": {
                "command": "plan_rebuild",
                "runtimeVersion": "10.4.7",
                "only": ["ffi-napi", "[a specific list of production native modules]"],
                "dependencies": {"[a specific list of production native modules]": "1", "[a specific list of production native modules]": "1", "[a specific list of production native modules]": "1", "@newrelic/native-metrics": "1"},
                "optionalDependencies": {"bcrypt": "1"},
                "devDependencies": {"ffi-napi": "1"},
                "modules": [
                    {"name": "[a specific list of production native modules]", "native": true},
                    {"name": "[a specific list of production native modules]", "native": true},
                    {"name": "bcrypt", "native": true},
                    {"name": "ffi-napi", "native": true},
                    {"name": "@newrelic/native-metrics", "native": true},
                    {"name": "[a specific list of production native modules]", "dependencies": {"[a specific list of production native modules]down": "1"}, "children": [{"name": "[a specific list of production native modules]down", "native": true}]}
                ]
            },
            "expected_output": "runtime_abi=82\n[a dynamic string array of allowed module names]\nskipped=0\n"
        }
    ]
}
```

---

### Feature 5: Project Root Discovery

**As a developer**, I want the tool to locate my project's root by finding the nearest dependency lock file while walking up from a starting directory, so traversal and workspace scoping anchor to the right boundary.

**Expected Behavior / Usage:**

Given a starting directory, the resolver walks upward through ancestor directories looking for a dependency lock file. The root is the directory that contains the lock file. Either of two common lock-file names is recognized. If no lock file is found anywhere in the ancestry, the starting directory itself is returned as the root.

The input declares the directories to create (`dirs`), which lock files to place and where (`lockfiles`, created at the temporary base), and the `startDir` to resolve from (relative to that base). Output is `project_root=<path of the root relative to startDir>`; `..` segments indicate how many [a specific list of production native modules]s up the root sits, and `.` means the start directory is itself the root.

**Test Cases:** `rcb_tests/public_test_cases/feature5_project_root.json`

```json
{
    "description": "Determines a project's root directory by walking upward from a starting directory until a dependency lock file is found. The root is the directory containing the lock file. Either of two common lock-file names is recognized. When no lock file exists anywhere in the ancestry, the starting directory itself is returned as the root. Output is the root expressed as a path relative to the starting directory ('.' means the start directory is the root).",
    "cases": [
        {
            "input": {"command": "resolve_project_root", "dirs": ["packages/bar"], "lockfiles": ["yarn.lock"], "startDir": "packages/bar"},
            "expected_output": "project_root=../..\n"
        },
        {
            "input": {"command": "resolve_project_root", "dirs": ["packages/bar"], "lockfiles": ["package-lock.json"], "startDir": "packages/bar"},
            "expected_output": "project_root=../..\n"
        },
        {
            "input": {"command": "resolve_project_root", "dirs": [], "lockfiles": [], "startDir": "."},
            "expected_output": "project_root=.\n"
        }
    ]
}
```

---

### Feature 6: Manifest Reading

**As a developer**, I want to read and parse a project's manifest descriptor from a directory, so the planner can inspect declared dependencies and metadata.

**Expected Behavior / Usage:**

Given a directory containing a JSON manifest, the reader parses it and returns the structured object. The output enumerates the manifest's top-[a specific list of production native modules] field names in sorted order on a `fields=` line, followed by one `key=value` line per field where the value is the JSON-encoded representation of that field. This lets the parsed structure be verified field-by-field.

**Test Cases:** `rcb_tests/public_test_cases/feature6_read_manifest.json`

```json
{
    "description": "Reads and parses a project manifest (a JSON descriptor file) from a directory and returns the parsed object. The output lists the manifest's top-[a specific list of production native modules] field names (sorted) followed by each field's JSON-encoded value, so the parsed structure can be verified field-by-field.",
    "cases": [
        {
            "input": {"command": "read_manifest", "manifest": {"name": "native-app", "version": "1.0.0", "dependencies": {"[a specific list of production native modules]": "1.4.2"}}},
            "expected_output": "fields=dependencies,name,version\ndependencies={\"[a specific list of production native modules]\":\"1.4.2\"}\nname=\"native-app\"\nversion=\"1.0.0\"\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the planning engine described above — dependency-graph traversal, dependency-type classification, ABI resolution for a target runtime version, build-stamp comparison (with force override and allow-list scoping), project-root discovery, and manifest reading — kept decoupled from any standard I/O.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON command from stdin, dispatches on its `command` field, invokes the appropriate core logic, and prints the line-based result to stdout exactly matching the per-feature contracts above. Errors must be normalized to language-neutral category lines (e.g. `error=build_path_not_absolute`, `error=invalid_runtime_version` with a separate `got=<type>` field) and must never leak host-language exception class names, runtime message suffixes, or object-repr formatting. The adapter must be logically and physically separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_dependency_selection.json` under `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_dependency_selection@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` contains **only** the raw stdout of the program under test (no PASS/FAIL or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- skip if version matches built version unless force flag is active
- mark all as selected on non-match when force is inactive
