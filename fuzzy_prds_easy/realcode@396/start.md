## Product Requirement Document

# Project Manifest & CLI Argument Toolkit - Build-Tooling Primitives Library

## Project Goal

Build a small, dependency-light utility library that supplies the reusable "plumbing" primitives a command-line build/deploy tool needs: environment-variable templating, key/value and command-line argument parsing, relative-path math, project-manifest inspection, SDK-version selection, and POSIX user resolution. The goal is to let a higher-level CLI focus on its workflow while delegating these fiddly, well-defined string/parsing tasks to a single, well-tested component.

---

## Background & Problem

Without this library, every command in a build/deploy CLI re-implements the same low-level chores: expanding `$(NAME)` placeholders against the environment, splitting `key=value;key2=value2` option strings (with quoting), turning raw `argv` tokens into typed options, computing relative paths between project and solution directories, reading a project manifest to learn its target framework / output type / AOT setting, picking the newest installed SDK from a version listing, and discovering the effective user/group id on Linux/macOS. Each re-implementation drifts subtly, producing inconsistent edge-case behavior and brittle, hard-to-test code.

With this library, those primitives live in one place behind small, idiomatic functions with precise, documented behavior on every edge case (missing variables, quoted values, empty values, malformed input, case-insensitive path comparison, override precedence, command-probe failures). The CLI calls them and gets predictable results, and the behavior is locked down by a black-box test contract.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain is a collection of mostly-independent primitives, so group related primitives into cohesive units (e.g. a string/option-parsing unit, a path/manifest unit, a process/user unit, an argument-parsing unit) rather than one monolithic file or one file per trivial function. Do not over-engineer, but do not produce a single "god file".

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract for the execution adapter**, NOT the internal data model. The core primitives must take and return ordinary native values (strings, maps, booleans, numeric versions, small structs) and must know nothing about stdin/stdout or JSON. A thin execution adapter is solely responsible for decoding a JSON payload, calling the right primitive, and formatting the result lines.

3. **Adherence to SOLID Design Principles (scaled to project size):**
   - **SRP:** Keep parsing, path math, manifest reading, process probing, and output formatting in distinct units.
   - **OCP:** Adding a new option value type or a new manifest property should not require rewriting existing primitives.
   - **LSP:** Any process-probe and logger abstractions must be substitutable by test doubles without changing behavior.
   - **ISP:** Keep the process-probe and logger interfaces tiny and focused.
   - **DIP:** The user-resolution primitive must depend on an injectable process-probe abstraction and an injectable logger abstraction, not on a concrete OS-process implementation, so it is testable with scripted results.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** Each primitive should read naturally in the target language and hide its internal parsing state.
   - **Resilience:** Malformed input must be modeled with explicit error categories, not generic crashes. In particular, a key/value pair with an empty key is a domain error and must surface as a normalized error category (never as a host-language exception identity).

---

## Core Features

### Feature 1: Environment Variable Substitution

**As a developer**, I want to expand `$(NAME)` placeholders in a string using the current environment, so I can templatize configuration values without writing my own scanner.

**Expected Behavior / Usage:**

The input is a string plus the set of environment entries that should be visible. Every `$(NAME)` token is replaced by the value of the environment entry named `NAME` (exact, case-sensitive name match). A token whose name has no matching environment entry is left exactly as written, including its surrounding `$(` and `)`. A string containing no tokens is returned unchanged. The same token may appear several times and every occurrence is replaced. The output is a single line `result=<expanded string>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_env_substitution.json`

```json
{
    "description": "Substitute $(NAME) tokens inside a string with values from the process environment. Tokens whose name has no matching environment entry are left untouched, and a string with no tokens passes through unchanged. The same token may appear multiple times and every occurrence is replaced.",
    "cases": [
        {
            "input": {"env": {}, "text": "some string"},
            "expected_output": "result=some string\n"
        },
        {
            "input": {"env": {}, "text": "some string=$(variable)"},
            "expected_output": "result=some string=$(variable)\n"
        },
        {
            "input": {"env": {"Key1": "replacement1"}, "text": "some string=$(Key1) other $(Key1)"},
            "expected_output": "result=some string=replacement1 other replacement1\n"
        }
    ]
}
```

---

### Feature 2: Key/Value Option Parsing

**As a developer**, I want to parse a `key1=value1;key2=value2` option string into a map, so users can pass structured parameters as a single argument.

**Expected Behavior / Usage:**

The input is one option string. It is split into pairs on `;` and each pair into key and value on `=`. Output is `count=<n>` followed by one `key=value` line per pair in the order parsed. Rules and edge cases:
- A null or empty option yields `count=0` with no further lines.
- A trailing `;` is tolerated (it does not produce an extra empty pair).
- Either side may be wrapped in double quotes; quoting lets a value contain literal `=` and `;` characters, and the surrounding quotes are stripped from the result.
- An empty value is allowed and renders as a `key=` line with nothing after the `=`.
- A pair whose key is empty (e.g. `=aaa`) is invalid and must be reported as the normalized error line `error=command_line_parse_error` (and nothing else).

**Test Cases:** `rcb_tests/public_test_cases/feature2_key_value_parsing.json`

```json
{
    "description": "Parse a semicolon-delimited list of key=value pairs into a map, reporting how many pairs were found followed by each key=value. Values may be quoted so they can themselves contain '=' and ';' characters; a trailing ';' is tolerated; an empty value is allowed. A pair with an empty key is rejected as a command-line parse error.",
    "cases": [
        {
            "input": {"option": ""},
            "expected_output": "count=0\n"
        },
        {
            "input": {"option": "Table=Blog"},
            "expected_output": "count=1\nTable=Blog\n"
        },
        {
            "input": {"option": "Table=Blog;Bucket=MyBucket"},
            "expected_output": "count=2\nTable=Blog\nBucket=MyBucket\n"
        },
        {
            "input": {"option": "\"ConnectionString\"=\"User=foo;Password=test\""},
            "expected_output": "count=1\nConnectionString=User=foo;Password=test\n"
        },
        {
            "input": {"option": "ShouldCreateTable=true;BlogTableName="},
            "expected_output": "count=2\nShouldCreateTable=true\nBlogTableName=\n"
        },
        {
            "input": {"option": "=aaa"},
            "expected_output": "error=command_line_parse_error\n"
        }
    ]
}
```

---

### Feature 3: Relative Path Computation

**As a developer**, I want to compute the relative path from one location to another, so I can emit portable project references instead of absolute paths.

**Expected Behavior / Usage:**

The input is a `start` path and a `relative_to` (target) path. Both are normalized first: backslashes are treated as path separators and equal forward slashes, and segment comparison is case-insensitive. Walking from the deepest shared ancestor, each remaining segment on the `start` side contributes one `../`, then the remaining segments on the target side are appended joined by `/`. If `start` is itself an ancestor of the target, the result is just the descending segments (no `../`). A trailing separator on the target path is preserved in the output. The result is emitted as `relative_path=<path>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_relative_path.json`

```json
{
    "description": "Compute the relative path from a start location to a target location. Both inputs are normalized (backslashes treated as separators, comparison is case-insensitive); each directory left behind on the start side becomes a '../' segment and the remaining target segments are appended with '/'. When the start path is an ancestor of the target the result is just the descending segments; a trailing separator on the target is preserved.",
    "cases": [
        {
            "input": {"start": "/home/user/Solution/Project", "relative_to": "/home/user/Solution"},
            "expected_output": "relative_path=../\n"
        },
        {
            "input": {"start": "/home/user/Solution", "relative_to": "/home/user/Solution/Project"},
            "expected_output": "relative_path=Project\n"
        },
        {
            "input": {"start": "C:\\Code\\Solution\\ProjectA", "relative_to": "C:\\Code\\Solution\\ProjectB\\file.csproj"},
            "expected_output": "relative_path=../ProjectB/file.csproj\n"
        },
        {
            "input": {"start": "user/Solution/", "relative_to": "user/Solution/Project/"},
            "expected_output": "relative_path=Project/\n"
        }
    ]
}
```

---

### Feature 4: Typed Command-Line Argument Parsing

**As a developer**, I want to map raw `argv` tokens onto declared options with typed values, so commands receive validated, typed inputs instead of raw strings.

**Expected Behavior / Usage:**

The input declares a list of options and a list of argument tokens. Each option has a `name`, a `short` switch (single dash), a `switch` (long, double dash), and a `type` of `string`, `int`, or `bool`. The parser scans tokens; when a token equals an option's short or long switch (case-insensitive, the two forms interchangeable), the immediately following token is consumed and coerced to the declared type. The output reports `count=<number of matched options>` followed, for each matched option, by `name=<name>`, `type=<string|int|bool>`, and `value=<parsed value>` (booleans render lowercase `true`/`false`; integers render in decimal). Both `-c Release` and `--configuration Release` must produce identical output.

**Test Cases:** `rcb_tests/public_test_cases/feature4_argument_parsing.json`

```json
{
    "description": "Parse a list of command-line tokens against a set of declared options. Each option declares a name, a short switch (single dash) and a long switch (double dash), and a value type (string, int, or bool). When a switch is matched, the following token is consumed and coerced to the declared type. The result reports how many options were matched and, for each matched option, its name, value type, and parsed value. Both the short and long switch forms are accepted interchangeably.",
    "cases": [
        {
            "input": {"options": [{"name": "Configuration", "short": "-c", "switch": "--configuration", "type": "string"}], "args": ["-c", "Release"]},
            "expected_output": "count=1\nname=Configuration\ntype=string\nvalue=Release\n"
        },
        {
            "input": {"options": [{"name": "MyInt", "short": "-i", "switch": "--integer", "type": "int"}], "args": ["--integer", "100"]},
            "expected_output": "count=1\nname=MyInt\ntype=int\nvalue=100\n"
        },
        {
            "input": {"options": [{"name": "MyBool", "short": "-b", "switch": "--bool", "type": "bool"}], "args": ["-b", "true"]},
            "expected_output": "count=1\nname=MyBool\ntype=bool\nvalue=true\n"
        }
    ]
}
```

---

### Feature 5: Project Manifest Inspection

**As a developer**, I want to read selected properties out of an XML project manifest, so the tool can adapt its behavior to how a project is configured without me parsing XML by hand.

**Expected Behavior / Usage:**

Each leaf below takes the text of an XML project manifest (a `<Project>` root containing one or more `<PropertyGroup>` blocks) and extracts one property. The manifest's SDK attribute and surrounding properties may vary; extraction must locate the requested property regardless of the rest of the document.

*5.1 Target Framework — read the target framework property*

The input is the manifest text. Return the text of the project's target framework property as `target_framework=<value>`. Extraction is independent of the project's SDK style or which other properties are present.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_target_framework.json`

```json
{
    "description": "Given the text of an XML project manifest, return the value of the project's target framework property. The manifest's SDK style and other properties vary, but the target framework is read regardless of the surrounding structure.",
    "cases": [
        {
            "input": {"project_file": "<Project Sdk=\"Microsoft.NET.Sdk\">\n  <PropertyGroup>\n    <TargetFramework>netcoreapp3.1</TargetFramework>\n    <OutputType>Library</OutputType>\n  </PropertyGroup>\n</Project>\n"},
            "expected_output": "target_framework=netcoreapp3.1\n"
        },
        {
            "input": {"project_file": "<Project Sdk=\"Microsoft.NET.Sdk.Web\">\n  <PropertyGroup>\n    <TargetFramework>netcoreapp3.1</TargetFramework>\n  </PropertyGroup>\n</Project>\n"},
            "expected_output": "target_framework=netcoreapp3.1\n"
        }
    ]
}
```

*5.2 Output Type — read the output type property*

The input is the manifest text. Return the text of the project's output type property as `output_type=<value>` (e.g. a library versus an executable).

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_output_type.json`

```json
{
    "description": "Given the text of an XML project manifest, return the value of the project's output type property (for example a library versus an executable).",
    "cases": [
        {
            "input": {"project_file": "<Project Sdk=\"Microsoft.NET.Sdk\">\n  <PropertyGroup>\n    <TargetFramework>netcoreapp3.1</TargetFramework>\n    <OutputType>Library</OutputType>\n  </PropertyGroup>\n</Project>\n"},
            "expected_output": "output_type=Library\n"
        },
        {
            "input": {"project_file": "<Project Sdk=\"Microsoft.NET.Sdk\">\n  <PropertyGroup>\n    <OutputType>Exe</OutputType>\n    <TargetFramework>net7.0</TargetFramework>\n    <PublishAot>true</PublishAot>\n  </PropertyGroup>\n</Project>\n"},
            "expected_output": "output_type=Exe\n"
        }
    ]
}
```

*5.3 Ahead-of-Time Publish Flag — resolve the AOT publish setting with override precedence*

The input is the manifest text plus an optional build-parameter string. Resolution order: if the build-parameter string contains the publish-AOT flag (matched case-insensitively, with whitespace ignored) set to `true` or `false`, that value wins and the manifest is not consulted. Otherwise the manifest's publish-AOT property is read; if it is present and a valid boolean its value is used, and if it is absent or not a valid boolean the result defaults to `false`. Output is `publish_aot=<true|false>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_publish_aot.json`

```json
{
    "description": "Decide whether ahead-of-time (AOT) publishing is requested. An optional build-parameter string is consulted first: if it contains the publish-AOT flag set to true or false (case-insensitive, whitespace ignored) that value wins. Otherwise the project manifest's publish-AOT property is read; if it is absent or not a boolean the result defaults to false.",
    "cases": [
        {
            "input": {"project_file": "<Project Sdk=\"Microsoft.NET.Sdk\">\n  <PropertyGroup>\n    <TargetFramework>netcoreapp3.1</TargetFramework>\n    <OutputType>Library</OutputType>\n  </PropertyGroup>\n</Project>\n", "msbuild_parameters": null},
            "expected_output": "publish_aot=false\n"
        },
        {
            "input": {"project_file": "<Project Sdk=\"Microsoft.NET.Sdk\">\n  <PropertyGroup>\n    <TargetFramework>netcoreapp3.1</TargetFramework>\n    <OutputType>Library</OutputType>\n  </PropertyGroup>\n</Project>\n", "msbuild_parameters": "publishaot=true"},
            "expected_output": "publish_aot=true\n"
        },
        {
            "input": {"project_file": "<Project Sdk=\"Microsoft.NET.Sdk\">\n  <PropertyGroup>\n    <OutputType>Exe</OutputType>\n    <TargetFramework>net7.0</TargetFramework>\n    <PublishAot>true</PublishAot>\n  </PropertyGroup>\n</Project>\n", "msbuild_parameters": null},
            "expected_output": "publish_aot=true\n"
        },
        {
            "input": {"project_file": "<Project Sdk=\"Microsoft.NET.Sdk\">\n  <PropertyGroup>\n    <OutputType>Exe</OutputType>\n    <TargetFramework>net7.0</TargetFramework>\n    <PublishAot>true</PublishAot>\n  </PropertyGroup>\n</Project>\n", "msbuild_parameters": "publishAOT=False"},
            "expected_output": "publish_aot=false\n"
        }
    ]
}
```

---

### Feature 6: SDK Version Selection

**As a developer**, I want to pick the newest installed SDK version from a version listing, so the tool can target the latest available toolchain.

**Expected Behavior / Usage:**

The input is the multi-line text emitted by an SDK-list command. Each meaningful line starts with a dotted version number followed by whitespace and an install path in brackets; lines are scanned and the highest valid version is selected. The result is emitted as `sdk_version=<version>`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_sdk_version.json`

```json
{
    "description": "Parse the multi-line listing produced by an SDK-list command. Each line begins with a version number followed by an install path in brackets. Return the highest valid version found by scanning the listing.",
    "cases": [
        {
            "input": {"sdk_list_output": "1.1.11 [/usr/local/share/dotnet/sdk]\n2.1.302 [/usr/local/share/dotnet/sdk]\n2.1.403 [/usr/local/share/dotnet/sdk]\n2.1.503 [/usr/local/share/dotnet/sdk]\n2.2.100 [/usr/local/share/dotnet/sdk]\n"},
            "expected_output": "sdk_version=2.2.100\n"
        }
    ]
}
```

---

### Feature 7: POSIX Effective User Resolution

**As a developer**, I want to resolve the effective user id and group id by running two probe commands, so the tool can set correct file ownership on Linux/macOS while staying fully testable with scripted probe results.

**Expected Behavior / Usage:**

The input is an ordered list of probe results, one per command run (first the user-id probe, then the group-id probe). Each probe result reports `executed`, an `exit_code`, captured `output`, and captured `error`. When both probes execute, exit successfully, and emit numeric output, the resolution succeeds and emits `user_id=<n>` then `group_id=<n>`. When a probe fails (non-zero exit code), the resolver records a diagnostic line `Error executing "id <flag>" - exit code <code> <error text>` describing the failed probe, then a warning line noting which value could not be obtained (`Warning: Unable to get effective group from "id -g"` for the group probe), and finally `user_resolved=false`. The diagnostic and warning lines are emitted in that order before the `user_resolved=false` line.

**Test Cases:** `rcb_tests/public_test_cases/feature7_posix_user.json`

```json
{
    "description": "Resolve the effective user id and group id by running two probe commands in sequence (one for the user id, one for the group id). Each probe reports whether it executed, an exit code, captured output, and captured error. When both probes succeed and emit numeric output, the resolved user id and group id are returned. When a probe fails (non-zero exit), a diagnostic line describing the failed probe is recorded, a warning notes which value could not be obtained, and the user is reported as unresolved.",
    "cases": [
        {
            "input": {"id_results": [{"executed": true, "exit_code": 0, "output": "998", "error": ""}, {"executed": true, "exit_code": 0, "output": "999", "error": ""}]},
            "expected_output": "user_id=998\ngroup_id=999\n"
        },
        {
            "input": {"id_results": [{"executed": true, "exit_code": 0, "output": "998", "error": ""}, {"executed": true, "exit_code": -1, "output": "", "error": "Sad trombones"}]},
            "expected_output": "Error executing \"id -g\" - exit code -1 Sad trombones\nWarning: Unable to get effective group from \"id -g\"\nuser_resolved=false\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the seven feature areas above as cohesive, decoupled primitives. The physical structure (grouped units, not a single god file and not one file per trivial function) MUST align with the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core primitives. It reads a JSON command from stdin (the operation is selected externally, e.g. by the harness), invokes the appropriate primitive, and prints the result lines to stdout, strictly matching the per-leaf-feature contracts above. It must translate any native exception from the core into a normalized `error=<category>` line and must never leak host-language exception identities into stdout. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_env_substitution.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_env_substitution@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- normalize backslashes
