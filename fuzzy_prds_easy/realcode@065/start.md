## Product Requirement Document

# Runtime Coverage Collection Subsystem - Recording, Merging, and Reporting Per-File Line Execution

## Project Goal

Build a runtime code-coverage subsystem that allows developers to record which lines of which source files were executed, accumulate that data across many separate runs or hosts, persist it through interchangeable storage backends, and produce a clean, normalized coverage report — without forcing them to hand-roll bespoke aggregation, path-reconciliation, or storage logic for every project.

---

## Background & Problem

Without this subsystem, developers tracking real-world execution coverage are forced to stitch together raw per-file line counters by hand: summing hit counts from repeated runs, reconciling file paths that differ between machines or rotating deploy directories, filtering out [the complete list of built-in exclusion patterns]ed/internal files, and serializing everything to some datastore. This leads to repetitive, error-prone boilerplate and reports that disagree across environments.

With this subsystem, a caller simply submits per-file line-execution counts; the system accumulates them, keeps them under a pluggable store, filters out files that should not be measured, and emits a normalized coverage map keyed by canonical file paths.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility domain (storage adapters, data accumulation, path/report normalization, configuration of filtering rules). It MUST NOT be a single "god file". Provide a clear multi-file directory tree that separates storage backends, the accumulation/merge core, report normalization/filtering, and the execution adapter.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract** for an execution adapter, NOT the internal data model. Core logic must be decoupled from stdin/stdout and JSON parsing; the adapter alone translates JSON commands into idiomatic core calls and renders results.

3. **Adherence to SOLID Design Principles:** Separate parsing, routing, validation, core execution, and output formatting. The storage layer must be an abstraction with interchangeable implementations (an in-process/file-backed store and a networked key-value store) that are perfectly substitutable. High-level accumulation and reporting logic must depend on the storage abstraction, not a concrete backend.

4. **Robustness & Interface Design:** The public interface must be idiomatic and hide internal complexity. Edge cases (unknown files, empty stores, mismatched array lengths, positions with no execution data) must be handled gracefully and modeled explicitly rather than via generic faults.

---

## Core Features

### Feature 1: Pluggable Coverage Store

**As a developer**, I want to persist and retrieve per-file line-execution data through interchangeable storage backends, so I can keep coverage between runs without coupling my code to a specific datastore.

**Expected Behavior / Usage:**

A coverage snapshot is a map from a file path to an array of per-line execution counts. Index `i` of the array corresponds to line `i` of the file; a non-negative integer is the number of times that line executed, and a no-data position (a line that is not executable / never instrumented) is represented as a null entry. The store accepts a snapshot, persists it, and can return the full coverage map, the counts for a single file, the list of tracked files, or be cleared. All retrieval returns only the line-count data (no internal bookkeeping such as timestamps or content hashes).

*1.1 Save and read back a coverage map — round-trip identity across backends*

Submitting one snapshot to a fresh store and then reading the entire coverage map returns exactly the per-file arrays that were submitted. The same observable result holds whether the snapshot is kept in a file-backed store or a networked key-value store. Output lists, for each file (sorted by path), the file key and its comma-separated line counts (null for no-data positions), preceded by the number of files.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_store_save_retrieve.json`

```json
{
    "description": "Persisting a single coverage snapshot (a map of file path to per-line execution counts) through a pluggable store and then reading the full coverage map back returns exactly the same per-file line-hit arrays that were written. The same contract holds regardless of which storage backend is used.",
    "cases": [
        {
            "input": {"op": "store_and_read", "backend": "redis", "snapshot": {"app_path/dog.rb": [0, 1, 2]}},
            "expected_output": "count=1\nfile=app_path/dog.rb\nlines=0,1,2"
        },
        {
            "input": {"op": "store_and_read", "backend": "file", "snapshot": {"cat.rb": [0, 1]}},
            "expected_output": "count=1\nfile=cat.rb\nlines=0,1"
        }
    ]
}
```

*1.2 Read the line counts for one file — unknown files return empty*

Given a populated store, requesting the counts for a specific file returns that file's array; requesting a file the store has never recorded returns an empty array. Output reports the queried file, the length of the returned array, and its comma-separated values.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_covered_lines.json`

```json
{
    "description": "Querying the recorded line-hit array for one specific file returns that file's per-line execution counts, while querying a file the store has never recorded returns an empty array. The contract is identical across storage backends.",
    "cases": [
        {
            "input": {"op": "read_file_lines", "backend": "redis", "snapshot": {"app_path/dog.rb": [0, 1, 2]}, "file": "app_path/dog.rb"},
            "expected_output": "file=app_path/dog.rb\nlength=3\nlines=0,1,2"
        },
        {
            "input": {"op": "read_file_lines", "backend": "redis", "snapshot": {"app_path/dog.rb": [0, 1, 2]}, "file": "app_path/other.rb"},
            "expected_output": "file=app_path/other.rb\nlength=0\nlines="
        }
    ]
}
```

*1.3 List the tracked files*

Requesting the set of tracked files returns the file keys present in the stored coverage map. Output reports the count followed by each file key (sorted).

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_covered_files.json`

```json
{
    "description": "Listing the files tracked by the store returns the set of file keys present in the stored coverage map.",
    "cases": [
        {
            "input": {"op": "list_files", "backend": "file", "snapshot": {"dog.rb": [1, 2, null]}},
            "expected_output": "count=1\nfile=dog.rb"
        }
    ]
}
```

*1.4 Clear the store*

Clearing the store discards all stored coverage, so a subsequent read of the full map yields zero files. Output reports a file count of zero.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_clear.json`

```json
{
    "description": "Clearing the store removes all stored coverage data, so a subsequent read of the full coverage map returns an empty result. The contract is identical across storage backends.",
    "cases": [
        {
            "input": {"op": "reset_store", "backend": "redis", "snapshot": {"app_path/dog.rb": [0, 1, 2]}},
            "expected_output": "count=0"
        }
    ]
}
```

---

### Feature 2: Coverage Accumulation on Persist

**As a developer**, I want successive coverage snapshots to be merged into the stored data rather than overwriting it, so the persisted map reflects the total execution observed across all runs.

**Expected Behavior / Usage:**

When a snapshot is persisted into a store that already holds data, the two are merged. For a file present in both, the line-count arrays are summed position-by-position. A position is summed only when both sides have a count; a position that is no-data (null) on either side stays null in the result unless the other side has a count to carry. Files present in only one of the two are kept as-is. Summing of a file's counts only applies while the underlying source content is unchanged between snapshots.

*2.1 Repeated identical snapshots accumulate*

Persisting the same snapshot twice doubles each line's count (no-data positions stay no-data). Output is the resulting coverage map.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_incremental_merge.json`

```json
{
    "description": "Persisting the same coverage snapshot twice accumulates line-hit counts by summing them element-wise for each file, so repeated reporting of identical execution data increases the recorded hit totals while preserving array positions that have no data.",
    "cases": [
        {
            "input": {"op": "accumulate", "backend": "redis", "snapshots": [{"app_path/dog.rb": [0, 1, 2]}, {"app_path/dog.rb": [0, 1, 2]}]},
            "expected_output": "count=1\nfile=app_path/dog.rb\nlines=0,2,4"
        }
    ]
}
```

*2.2 Merge across overlapping file sets — sum shared, retain old, add new*

Merging two snapshots whose file sets overlap sums the shared files, retains files seen only in the earlier snapshot, and adds files seen only in the later one. The resulting map is the union of both file sets, sorted by path.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_merge_file_sets.json`

```json
{
    "description": "Merging two coverage snapshots that share some files and differ in others sums the line hits for shared files (whose underlying source content is unchanged), retains files present only in the earlier snapshot, and adds files present only in the later snapshot. The resulting coverage map is the union of both file sets with shared files accumulated.",
    "cases": [
        {
            "input": {"op": "accumulate", "backend": "redis", "snapshots": [{"config/settings.rb": [5, 7, null], "config/assets.rb": [5, 7, null], "config/cookies.rb": [5, 7, null]}, {"config/settings.rb": [5, 7, null], "config/logging.rb": [5, 7, null], "config/params.rb": [5, 7, null], "app/controllers/main_controller.rb": [5, 7, null]}]},
            "expected_output": "count=6\nfile=app/controllers/main_controller.rb\nlines=5,7,null\nfile=config/assets.rb\nlines=5,7,null\nfile=config/cookies.rb\nlines=5,7,null\nfile=config/logging.rb\nlines=5,7,null\nfile=config/params.rb\nlines=5,7,null\nfile=config/settings.rb\nlines=10,14,null"
        }
    ]
}
```

---

### Feature 3: Report Normalization and Filtering

**As a developer**, I want coverage data reconciled to canonical paths, mergeable across hosts, and filtered by ignore rules when reporting, so my final report is consistent regardless of where the data was collected.

**Expected Behavior / Usage:**

*3.1 Canonical path remapping*

A recorded file key is normalized against an ordered list of root-path prefixes. Each prefix is treated as a leading pattern; any matching prefix is rewritten to the configured local root (the last entry in the list). Prefixes may be plain strings or regular expressions, which lets rotating release directories (e.g. a numeric release id) collapse to one stable path. A key already under the local root is returned effectively unchanged. Output reports the resulting path.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_path_normalization.json`

```json
{
    "description": "Normalizing a stored file key against an ordered list of root-path prefixes rewrites deploy-specific or remote roots to the configured local root, so coverage recorded on different machines or release directories maps to a single canonical path. Keys already under the local root are left effectively unchanged. Root prefixes may be plain strings or regular expressions that match rotating release directories.",
    "cases": [
        {
            "input": {"op": "remap_path", "key": "/app/is/a/path.rb", "roots": ["/app/", "/full/remote_app/path/"]},
            "expected_output": "path=/full/remote_app/path/is/a/path.rb"
        },
        {
            "input": {"op": "remap_path", "key": "/box/apps/app_name/releases/20140725203539/app/models/user.rb", "roots": ["/box/apps/app_name/releases/\\d+/", "/full/remote_app/path/"]},
            "expected_output": "path=/full/remote_app/path/app/models/user.rb"
        }
    ]
}
```

*3.2 Merge two line-count arrays*

Two line-count arrays for the same file (e.g. from two hosts) are combined into an array as long as the longer input, summing position-by-position. A position uncovered on one side but executed on the other counts as zero on the missing side; a position unexecuted on both sides is preserved as no-data. Output reports the merged length and comma-separated values.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_merge_line_arrays.json`

```json
{
    "description": "Combining two line-hit arrays (for instance coverage for the same file gathered from two hosts) produces an array as long as the longer input, summing counts position-by-position. A position that is uncovered on one side but executed on the other is treated as zero on the missing side; a position that is unexecuted on both sides is preserved as no-data.",
    "cases": [
        {
            "input": {"op": "combine_counts", "first": [0, 0, 1, 0, 1], "second": [null, 0, 1, 0, 0]},
            "expected_output": "length=5\ncounts=0,0,2,0,1"
        },
        {
            "input": {"op": "combine_counts", "first": [0, 1, 2, null, null, null], "second": [0, 1, 2, null, 0, 1, 2]},
            "expected_output": "length=7\ncounts=0,2,4,null,0,1,2"
        }
    ]
}
```

*3.3 Ignore-rule filtering when reporting*

Building a report drops file keys that match the configured ignore rules. Each rule is a regular expression: an anchored extension pattern only excludes files whose key actually ends with that extension (a file that merely contains those letters mid-path is kept), while a plain substring rule excludes any key containing it. Files matching no rule are retained with their counts. Output is the filtered coverage map, sorted by path.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_ignore_filter.json`

```json
{
    "description": "Generating a report applies the configured ignore rules to drop matching file keys from the coverage map. Each rule is treated as a regular expression: an anchored extension pattern only excludes files whose key actually ends with that extension (a file that merely contains those letters mid-path is kept), while a plain substring rule excludes any key that contains it. Files that match no rule are retained with their line-hit arrays.",
    "cases": [
        {
            "input": {"op": "build_report", "snapshot": {"a_path/that_has_erb_in/thepath.rb": [1, 3, 6], "[the complete list of built-in exclusion patterns]/gem.rb": [2, 2], "app/view.erb": [9], "app/view.slim": [4], "app/models/user.rb": [1, 1, 1]}, "ignore": ["[the complete list of built-in exclusion patterns]", "[specific file extensions to exclude from reports]", "[specific file extensions to exclude from reports]"], "root": "/full/remote_app/path", "root_paths": []},
            "expected_output": "count=2\nfile=a_path/that_has_erb_in/thepath.rb\nlines=1,3,6\nfile=app/models/user.rb\nlines=1,1,1"
        }
    ]
}
```

---

### Feature 4: Built-in Exclusion Rules

**As a developer**, I want the collector to always skip framework-internal and schema files on top of my own ignore list, so generated/irrelevant files never pollute coverage.

**Expected Behavior / Usage:**

When the collector is initialized, its effective set of exclusion rules is the user-configured ignore list followed, in order, by two built-in internal exclusions (one for the language's internal prelude pseudo-file and one for the schema definition file). Output reports the number of effective rules and each rule in order.

**Test Cases:** `rcb_tests/public_test_cases/feature4_default_filter_rules.json`

```json
{
    "description": "Initializing the coverage collector derives its effective set of file-exclusion rules by appending two built-in internal exclusions to the user-configured ignore list, preserving order. This ensures framework-internal and schema files are always skipped on top of any user rules.",
    "cases": [
        {
            "input": {"op": "default_exclusions", "ignore": ["[the complete list of built-in exclusion patterns]"]},
            "expected_output": "count=3\nrule=[the complete list of built-in exclusion patterns]\nrule=[the complete list of built-in exclusion patterns]\nrule=[the complete list of built-in exclusion patterns]"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the storage abstraction (with interchangeable file-backed and networked key-value backends), the accumulation/merge core, and the report normalization/filtering logic, aligned with the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically and physically separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `[the exact filesystem path format for compressed stdout logs]/<cases-dir>/{filename.stem}@{case_index.[the exact filesystem path format for compressed stdout logs]}.txt` containing **only** the raw stdout from the program under test, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- apply the same scalar addition logic used in C004's unknown file handling
- use the same regex pattern style applied to file extensions in C024
