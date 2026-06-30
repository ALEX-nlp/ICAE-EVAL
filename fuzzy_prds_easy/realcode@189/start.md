## Product Requirement Document

# CI Pipeline Configuration Generator - Declarative Multi-Package Build Matrix

## Project Goal

Build a configuration generator that turns small, declarative per-package build definitions into a complete continuous-integration job matrix plus an executable runner script, so developers can describe *what* to test (SDK versions, ordered stages, tasks) in a few lines and have the verbose CI plumbing generated for them, kept consistent across every package in a repository.

---

## Background & Problem

A repository that hosts several related packages usually needs a CI pipeline that runs the same families of checks (format, analyze, unit tests) against several language-SDK versions, for every package, in a consistent stage order. Hand-writing this CI matrix is painful: the YAML is long and repetitive, the runner script must enumerate every task, identical work across packages should be de-duplicated, and the stage order must agree across packages. Doing this by hand is error-prone and drifts out of sync as packages are added.

With this tool, each package carries a short definition file listing its target SDKs and an ordered list of named stages, each holding one or more tasks. An optional repository-root file adds cross-cutting settings. The tool validates everything, computes a globally consistent stage order, de-duplicates shared work, and emits two artifacts: a CI matrix file (`.travis.yml`) describing one job per (stage, task-group, SDK, package-set) combination, and a runner shell script (`tool/travis.sh`) whose case-branches execute each distinct task command.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility domain (filesystem discovery, schema parsing/validation, stage-graph ordering, task de-duplication, and two distinct output renderers). It MUST NOT be a single "god file". Use a clear multi-file tree (core domain, validators, renderers, and a separate execution adapter). Do not over-engineer, but do not collapse the responsibilities into one module.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box contract for the execution adapter**, not the internal data model. The core engine must take structured configuration and produce structured artifacts with no knowledge of stdin/stdout or JSON. The execution adapter is solely responsible for translating a JSON command into core calls and rendering the result to stdout.

3. **Adherence to SOLID Design Principles:** Separate discovery, parsing, validation, ordering, and the two renderers into distinct units (SRP). The stage-ordering and task-extraction engine must be open for extension but closed for modification (OCP). Output renderers should be substitutable behind a common abstraction (LSP/ISP). High-level orchestration must depend on abstractions, not on concrete file I/O (DIP).

4. **Robustness & Interface Design:** The core API must be idiomatic to the target language and hide internal complexity. All user-facing failures (missing files, malformed schema, inconsistent stage order, dangling stage references) must be modeled as explicit error types, never generic faults.

---

## Execution Adapter Contract (I/O shape)

The execution adapter reads ONE JSON command from stdin:

- `files` (object, required) — a virtual repository: map of repository-relative file path → file content string. Package directories each hold a definition file named `mono_pkg.yaml` and a manifest named `pubspec.yaml`; the repository root may hold an aggregation file named `mono_repo.yaml`.
- `useGet` (boolean, optional, default `false`) — selects the dependency-resolution verb used by the generated runner script.

On success the adapter prints the generator's console log (one line per discovered package and per advisory warning, each generated-file write acknowledged) followed by a dump of every generated artifact, each introduced by a line `--- file: <path> ---`. Paths and the generator version stamp are normalized so output is reproducible.

On failure the adapter prints a normalized, language-neutral error block instead of artifacts:

- A validation failure renders as `error=user_exception`, then `message=<text>`, then `details=<text or empty>`.
- A schema/parse failure renders as `error=config_parse`, then `message=<location-and-reason, possibly multi-line source excerpt>`.

No host-language exception type names or runtime message fragments ever appear in stdout.

---

## Core Features

### Feature 1: Generate CI Job Matrix and Runner Script

**As a developer**, I want to describe a single package's SDK versions and ordered stages/tasks and get a full CI matrix plus a runner script, so I don't hand-write repetitive pipeline boilerplate.

**Expected Behavior / Usage:**

The package definition lists target SDK versions under a `dart` key and an ordered list of named stages under `stages`; each stage holds one or more tasks (e.g. an analyze command, a formatter command, or a test invocation). The generator emits one matrix job per (stage, task-group, SDK) combination. Job entries are sorted by stage order, then environment, then script, then SDK. A task may be a bare name (default command) or a name mapped to explicit arguments; a `group` bundles several tasks to run together in one job; a `description` overrides the human-readable task label. The companion runner script declares one `case` branch per distinct task command (auto-keyed `test_0`, `test_1`, … when one task name expands to multiple commands) plus a catch-all error branch, and is bracketed by a header comment, an environment guard, an argument guard, and a per-package dependency-resolution loop. The console log prints `package:<relative-path>`, acknowledges the two generated files, and reminds the developer to mark the runner script executable.

**Test Cases:** `rcb_tests/public_test_cases/feature1_generate_config_matrix.json`

```json
{
    "description": "Generate a CI job-matrix YAML and a runner shell script from a single package's CI definition. The definition lists target SDK versions and a sequence of named stages, each containing tasks. The generator emits one job per (stage, task-group, SDK) combination plus a shell script whose case-branches run each distinct task command.",
    "cases": [
        {
            "input": {
                "files": {
                    "sub_pkg/mono_pkg.yaml": "dart:\n - dev\n - stable\n\nstages:\n  - analyze:\n    - dartanalyzer\n  - unit_test:\n    - test\n",
                    "sub_pkg/pubspec.yaml": "name: pkg_name\n"
                }
            },
            "expected_output": "package:sub_pkg\nWrote `.travis.yml`.\nMake sure to mark `./tool/travis.sh` as executable.\n  chmod +x ./tool/travis.sh\nWrote `./tool/travis.sh`.\n--- file: .travis.yml ---\n# Generated by ci-config-generator\nlanguage: dart\n\njobs:\n  include:\n    - stage: analyze\n      name: \"SDK: dev; PKG: sub_pkg; TASKS: `dartanalyzer .`\"\n      dart: dev\n      env: PKGS=\"sub_pkg\"\n      script: ./tool/travis.sh dartanalyzer\n    - stage: analyze\n      name: \"SDK: stable; PKG: sub_pkg; TASKS: `dartanalyzer .`\"\n      dart: stable\n      env: PKGS=\"sub_pkg\"\n      script: ./tool/travis.sh dartanalyzer\n    - stage: unit_test\n      name: \"SDK: dev; PKG: sub_pkg; TASKS: `pub run test`\"\n      dart: dev\n      env: PKGS=\"sub_pkg\"\n      script: ./tool/travis.sh test\n    - stage: unit_test\n      name: \"SDK: stable; PKG: sub_pkg; TASKS: `pub run test`\"\n      dart: stable\n      env: PKGS=\"sub_pkg\"\n      script: ./tool/travis.sh test\n\nstages:\n  - analyze\n  - unit_test\n\n# Only building master means that we don't run two builds for each pull request.\nbranches:\n  only:\n    - master\n\ncache:\n  directories:\n    - \"[standard paths examples for namespaced cache directories]\"\n--- file: tool/travis.sh ---\n#!/bin/bash\n# Generated by ci-config-generator\n\nif [[ -z ${PKGS} ]]; then\n  echo -e '\\033[31mPKGS environment variable must be set!\\033[0m'\n  exit 1\nfi\n\nif [[ \"$#\" == \"0\" ]]; then\n  echo -e '\\033[31mAt least one task argument must be provided!\\033[0m'\n  exit 1\nfi\n\nEXIT_CODE=0\n\nfor PKG in ${PKGS}; do\n  echo -e \"\\033[1mPKG: ${PKG}\\033[22m\"\n  pushd \"${PKG}\" || exit $?\n\n  PUB_EXIT_CODE=0\n  pub upgrade --no-precompile || PUB_EXIT_CODE=$?\n\n  if [[ ${PUB_EXIT_CODE} -ne 0 ]]; then\n    EXIT_CODE=1\n    echo -e '\\033[31mpub upgrade failed\\033[0m'\n    popd\n    continue\n  fi\n\n  for TASK in \"$@\"; do\n    echo\n    echo -e \"\\033[1mPKG: ${PKG}; TASK: ${TASK}\\033[22m\"\n    case ${TASK} in\n    dartanalyzer)\n      echo 'dartanalyzer .'\n      dartanalyzer . || EXIT_CODE=$?\n      ;;\n    test)\n      echo 'pub run test'\n      pub run test || EXIT_CODE=$?\n      ;;\n    *)\n      echo -e \"\\033[31mNot expecting TASK '${TASK}'. Error!\\033[0m\"\n      EXIT_CODE=1\n      ;;\n    esac\n  done\n\n  popd\ndone\n\nexit ${EXIT_CODE}\n"
        }
    ]
}
```


---

### Feature 2: Multi-Package Aggregation and Stage Ordering

**As a developer**, I want definitions from several packages combined into one matrix with consistent stage order and de-duplicated work, so the repository's CI stays coherent and minimal.

**Expected Behavior / Usage:**

*2.1 Merge Shared Tasks Across Packages — identical work runs once over a combined package set*

When two or more packages declare the same stage with the **same** concrete task command at the same SDK, the corresponding jobs are merged into a single job whose package-set environment lists every participating package (space-separated), and whose label switches to the plural form. Cache directories declared by each package are collected, de-duplicated, the shared dependency cache is always included, and each package-declared directory is namespaced under that package's path; the resulting list is sorted.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_merge_shared_tasks.json`

```json
{
    "description": "When multiple packages define the same stage with an identical task command, jobs that share (stage, SDK, task) are merged into a single job whose package-set environment lists all participating packages. Cache directories declared by each package are aggregated and namespaced under each package path.",
    "cases": [
        {
            "input": {
                "files": {
                    "pkg_a/mono_pkg.yaml": "dart:\n - stable\n - dev\n\nstages:\n  - format:\n    - dartfmt\n\ncache:\n  directories:\n    - .dart_tool\n    - /some_repo_root_dir\n",
                    "pkg_a/pubspec.yaml": "name: pkg_a\n",
                    "pkg_b/mono_pkg.yaml": "dart:\n - dev\n\nstages:\n  - format:\n    - dartfmt: sdk\n\ncache:\n  directories:\n    - .dart_tool\n    - /some_repo_root_dir\n",
                    "pkg_b/pubspec.yaml": "name: pkg_b\n"
                }
            },
            "expected_output": "package:pkg_a\npackage:pkg_b\nWrote `.travis.yml`.\nMake sure to mark `./tool/travis.sh` as executable.\n  chmod +x ./tool/travis.sh\nWrote `./tool/travis.sh`.\n--- file: .travis.yml ---\n# Generated by ci-config-generator\nlanguage: dart\n\njobs:\n  include:\n    - stage: format\n      name: \"SDK: dev; PKG: pkg_a; TASKS: `dartfmt -n --set-exit-if-changed .`\"\n      dart: dev\n      env: PKGS=\"pkg_a\"\n      script: ./tool/travis.sh dartfmt\n    - stage: format\n      name: \"SDK: stable; PKG: pkg_a; TASKS: `dartfmt -n --set-exit-if-changed .`\"\n      dart: stable\n      env: PKGS=\"pkg_a\"\n      script: ./tool/travis.sh dartfmt\n    - stage: format\n      name: \"SDK: dev; PKG: pkg_b; TASKS: `dartfmt -n --set-exit-if-changed .`\"\n      dart: dev\n      env: PKGS=\"pkg_b\"\n      script: ./tool/travis.sh dartfmt\n\nstages:\n  - format\n\n# Only building master means that we don't run two builds for each pull request.\nbranches:\n  only:\n    - master\n\ncache:\n  directories:\n    - \"[standard paths examples for namespaced cache directories]\"\n    - /some_repo_root_dir\n    - pkg_a/.dart_tool\n    - pkg_b/.dart_tool\n--- file: tool/travis.sh ---\n#!/bin/bash\n# Generated by ci-config-generator\n\nif [[ -z ${PKGS} ]]; then\n  echo -e '\\033[31mPKGS environment variable must be set!\\033[0m'\n  exit 1\nfi\n\nif [[ \"$#\" == \"0\" ]]; then\n  echo -e '\\033[31mAt least one task argument must be provided!\\033[0m'\n  exit 1\nfi\n\nEXIT_CODE=0\n\nfor PKG in ${PKGS}; do\n  echo -e \"\\033[1mPKG: ${PKG}\\033[22m\"\n  pushd \"${PKG}\" || exit $?\n\n  PUB_EXIT_CODE=0\n  pub upgrade --no-precompile || PUB_EXIT_CODE=$?\n\n  if [[ ${PUB_EXIT_CODE} -ne 0 ]]; then\n    EXIT_CODE=1\n    echo -e '\\033[31mpub upgrade failed\\033[0m'\n    popd\n    continue\n  fi\n\n  for TASK in \"$@\"; do\n    echo\n    echo -e \"\\033[1mPKG: ${PKG}; TASK: ${TASK}\\033[22m\"\n    case ${TASK} in\n    dartfmt)\n      echo 'dartfmt -n --set-exit-if-changed .'\n      dartfmt -n --set-exit-if-changed . || EXIT_CODE=$?\n      ;;\n    *)\n      echo -e \"\\033[31mNot expecting TASK '${TASK}'. Error!\\033[0m\"\n      EXIT_CODE=1\n      ;;\n    esac\n  done\n\n  popd\ndone\n\nexit ${EXIT_CODE}\n"
        }
    ]
}
```


*2.2 Disambiguate Task Keys — same task name, different commands get unique keys*

When the same task name resolves to **different** concrete commands across packages (for example two formatter invocations with different arguments), each distinct command is assigned a unique key formed from the task name plus a zero-padded numeric suffix. Job scripts reference the suffixed keys, and the runner script gets one `case` branch per distinct command. This keeps otherwise-colliding tasks individually dispatchable.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_disambiguate_task_keys.json`

```json
{
    "description": "When the same task name resolves to different concrete commands across packages, each distinct command is assigned a unique, numerically-suffixed task key so the runner script can dispatch them unambiguously. Job entries reference the suffixed keys.",
    "cases": [
        {
            "input": {
                "files": {
                    "pkg_a/mono_pkg.yaml": "dart:\n - stable\n - dev\n\nstages:\n  - format:\n    - dartfmt: sdk\n\ncache:\n  directories:\n    - .dart_tool\n    - /some_repo_root_dir\n",
                    "pkg_a/pubspec.yaml": "name: pkg_a\n",
                    "pkg_b/mono_pkg.yaml": "dart:\n - dev\n\nstages:\n  - format:\n    - dartfmt: --dry-run --fix --set-exit-if-changed .\n\ncache:\n  directories:\n    - .dart_tool\n    - /some_repo_root_dir\n",
                    "pkg_b/pubspec.yaml": "name: pkg_b\n"
                }
            },
            "expected_output": "package:pkg_a\npackage:pkg_b\nWrote `.travis.yml`.\nMake sure to mark `./tool/travis.sh` as executable.\n  chmod +x ./tool/travis.sh\nWrote `./tool/travis.sh`.\n--- file: .travis.yml ---\n# Generated by ci-config-generator\nlanguage: dart\n\njobs:\n  include:\n    - stage: format\n      name: \"SDK: dev; PKG: pkg_a; TASKS: `dartfmt -n --set-exit-if-changed .`\"\n      dart: dev\n      env: PKGS=\"pkg_a\"\n      script: ./tool/travis.sh [a pattern showing suffixed task keys generated for conflicting commands]\n    - stage: format\n      name: \"SDK: stable; PKG: pkg_a; TASKS: `dartfmt -n --set-exit-if-changed .`\"\n      dart: stable\n      env: PKGS=\"pkg_a\"\n      script: ./tool/travis.sh [a pattern showing suffixed task keys generated for conflicting commands]\n    - stage: format\n      name: \"SDK: dev; PKG: pkg_b; TASKS: `dartfmt --dry-run --fix --set-exit-if-changed .`\"\n      dart: dev\n      env: PKGS=\"pkg_b\"\n      script: ./tool/travis.sh [a pattern showing suffixed task keys generated for conflicting commands]\n\nstages:\n  - format\n\n# Only building master means that we don't run two builds for each pull request.\nbranches:\n  only:\n    - master\n\ncache:\n  directories:\n    - \"[standard paths examples for namespaced cache directories]\"\n    - /some_repo_root_dir\n    - pkg_a/.dart_tool\n    - pkg_b/.dart_tool\n--- file: tool/travis.sh ---\n#!/bin/bash\n# Generated by ci-config-generator\n\nif [[ -z ${PKGS} ]]; then\n  echo -e '\\033[31mPKGS environment variable must be set!\\033[0m'\n  exit 1\nfi\n\nif [[ \"$#\" == \"0\" ]]; then\n  echo -e '\\033[31mAt least one task argument must be provided!\\033[0m'\n  exit 1\nfi\n\nEXIT_CODE=0\n\nfor PKG in ${PKGS}; do\n  echo -e \"\\033[1mPKG: ${PKG}\\033[22m\"\n  pushd \"${PKG}\" || exit $?\n\n  PUB_EXIT_CODE=0\n  pub upgrade --no-precompile || PUB_EXIT_CODE=$?\n\n  if [[ ${PUB_EXIT_CODE} -ne 0 ]]; then\n    EXIT_CODE=1\n    echo -e '\\033[31mpub upgrade failed\\033[0m'\n    popd\n    continue\n  fi\n\n  for TASK in \"$@\"; do\n    echo\n    echo -e \"\\033[1mPKG: ${PKG}; TASK: ${TASK}\\033[22m\"\n    case ${TASK} in\n    [a pattern showing suffixed task keys generated for conflicting commands])\n      echo 'dartfmt -n --set-exit-if-changed .'\n      dartfmt -n --set-exit-if-changed . || EXIT_CODE=$?\n      ;;\n    [a pattern showing suffixed task keys generated for conflicting commands])\n      echo 'dartfmt --dry-run --fix --set-exit-if-changed .'\n      dartfmt --dry-run --fix --set-exit-if-changed . || EXIT_CODE=$?\n      ;;\n    *)\n      echo -e \"\\033[31mNot expecting TASK '${TASK}'. Error!\\033[0m\"\n      EXIT_CODE=1\n      ;;\n    esac\n  done\n\n  popd\ndone\n\nexit ${EXIT_CODE}\n"
        }
    ]
}
```


*2.3 Detect Inconsistent Stage Order — reject unorderable stage graphs*

Stage order is derived from the union of every package's ordered stage list and must admit a single global ordering. If one package orders stage X before Y while another orders Y before X, the stages form a cycle and no total order exists. The generator reports a validation error that names the cyclic stage set and produces no output.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_detect_stage_cycle.json`

```json
{
    "description": "Stage ordering must be globally consistent across all packages. If one package orders stage X before Y while another orders Y before X, no total order exists; the generator reports a configuration error naming the conflicting stages instead of emitting output.",
    "cases": [
        {
            "input": {
                "files": {
                    "pkg_a/mono_pkg.yaml": "dart:\n - dev\n\nstages:\n  - format:\n    - dartfmt\n  - analyze:\n    - dartanalyzer\n",
                    "pkg_a/pubspec.yaml": "name: pkg_a\n",
                    "pkg_b/mono_pkg.yaml": "dart:\n - dev\n\nstages:\n  - analyze:\n    - dartanalyzer\n  - format:\n    - dartfmt: sdk\n",
                    "pkg_b/pubspec.yaml": "name: pkg_b\n"
                }
            },
            "expected_output": "error=user_exception\nmessage=Not all packages agree on `stages` ordering, found a cycle between the following stages: [analyze, format]\ndetails=\n"
        }
    ]
}
```


---

### Feature 3: Matrix Group Overrides

**As a developer**, I want a stage entry to bundle tasks with its own SDK list overriding the top-level one, so I can run different task groups on different SDKs without duplicating the whole definition.

**Expected Behavior / Usage:**

A stage entry may be a `group` that lists several tasks together with its own SDK list. Each group yields one job per group-SDK that runs all the group's tasks in sequence, and the job label lists every task command. When a group provides its own SDK list, it overrides the top-level SDK list for that group. If a top-level SDK list is present but every stage entry overrides it, those top-level SDK values are unused; the console log emits an advisory warning that they can be removed, listing the unused values.

**Test Cases:** `rcb_tests/public_test_cases/feature3_matrix_group_overrides.json`

```json
{
    "description": "A stage entry may bundle several tasks into a group with its own per-group SDK list, overriding the top-level SDK list. Each group produces one job per group-SDK running all the group's tasks together. When a top-level SDK list is present but every stage entry overrides it, the unused top-level SDK values are reported as a removable warning.",
    "cases": [
        {
            "input": {
                "files": {
                    "pkg_a/mono_pkg.yaml": "dart:\n- unneeded\n\nstages:\n- analyzer_and_format:\n  - group:\n    - dartfmt\n    - dartanalyzer: --fatal-warnings --fatal-infos .\n    dart: [dev]\n  - group:\n    - dartfmt\n    - dartanalyzer: --fatal-warnings .\n    dart: [2.1.1]\n",
                    "pkg_a/pubspec.yaml": "name: pkg_a\n"
                }
            },
            "expected_output": "package:pkg_a\n  `dart` values (unneeded) are not used and can be removed.\nWrote `.travis.yml`.\nMake sure to mark `./tool/travis.sh` as executable.\n  chmod +x ./tool/travis.sh\nWrote `./tool/travis.sh`.\n--- file: .travis.yml ---\n# Generated by ci-config-generator\nlanguage: dart\n\njobs:\n  include:\n    - stage: analyzer_and_format\n      name: \"SDK: dev; PKG: pkg_a; TASKS: [`dartfmt -n --set-exit-if-changed .`, `dartanalyzer --fatal-warnings --fatal-infos .`]\"\n      dart: dev\n      env: PKGS=\"pkg_a\"\n      script: ./tool/travis.sh dartfmt dartanalyzer_0\n    - stage: analyzer_and_format\n      name: \"SDK: 2.1.1; PKG: pkg_a; TASKS: [`dartfmt -n --set-exit-if-changed .`, `dartanalyzer --fatal-warnings .`]\"\n      dart: \"2.1.1\"\n      env: PKGS=\"pkg_a\"\n      script: ./tool/travis.sh dartfmt dartanalyzer_1\n\nstages:\n  - analyzer_and_format\n\n# Only building master means that we don't run two builds for each pull request.\nbranches:\n  only:\n    - master\n\ncache:\n  directories:\n    - \"[standard paths examples for namespaced cache directories]\"\n--- file: tool/travis.sh ---\n#!/bin/bash\n# Generated by ci-config-generator\n\nif [[ -z ${PKGS} ]]; then\n  echo -e '\\033[31mPKGS environment variable must be set!\\033[0m'\n  exit 1\nfi\n\nif [[ \"$#\" == \"0\" ]]; then\n  echo -e '\\033[31mAt least one task argument must be provided!\\033[0m'\n  exit 1\nfi\n\nEXIT_CODE=0\n\nfor PKG in ${PKGS}; do\n  echo -e \"\\033[1mPKG: ${PKG}\\033[22m\"\n  pushd \"${PKG}\" || exit $?\n\n  PUB_EXIT_CODE=0\n  pub upgrade --no-precompile || PUB_EXIT_CODE=$?\n\n  if [[ ${PUB_EXIT_CODE} -ne 0 ]]; then\n    EXIT_CODE=1\n    echo -e '\\033[31mpub upgrade failed\\033[0m'\n    popd\n    continue\n  fi\n\n  for TASK in \"$@\"; do\n    echo\n    echo -e \"\\033[1mPKG: ${PKG}; TASK: ${TASK}\\033[22m\"\n    case ${TASK} in\n    dartanalyzer_0)\n      echo 'dartanalyzer --fatal-warnings --fatal-infos .'\n      dartanalyzer --fatal-warnings --fatal-infos . || EXIT_CODE=$?\n      ;;\n    dartanalyzer_1)\n      echo 'dartanalyzer --fatal-warnings .'\n      dartanalyzer --fatal-warnings . || EXIT_CODE=$?\n      ;;\n    dartfmt)\n      echo 'dartfmt -n --set-exit-if-changed .'\n      dartfmt -n --set-exit-if-changed . || EXIT_CODE=$?\n      ;;\n    *)\n      echo -e \"\\033[31mNot expecting TASK '${TASK}'. Error!\\033[0m\"\n      EXIT_CODE=1\n      ;;\n    esac\n  done\n\n  popd\ndone\n\nexit ${EXIT_CODE}\n"
        }
    ]
}
```


---

### Feature 4: SDK Constraint Compatibility Warnings

**As a developer**, I want to be warned when a job targets an SDK version outside the package's declared support range, so I catch misconfigured matrices early without blocking generation.

**Expected Behavior / Usage:**

If a package manifest declares an SDK version constraint, the generator compares every explicitly-pinned job SDK against it. Versions that fall outside the constraint are **not** removed (the jobs are still generated), but the console log emits a warning that lists the incompatible pinned versions alongside the declared constraint range. Versions inside the range, and non-pinned channel names, produce no warning.

**Test Cases:** `rcb_tests/public_test_cases/feature4_sdk_constraint_warning.json`

```json
{
    "description": "If a package declares an SDK version constraint, the generator checks every explicitly-pinned job SDK against it. SDK versions that fall outside the declared constraint still produce jobs, but a warning lists the incompatible versions alongside the constraint.",
    "cases": [
        {
            "input": {
                "files": {
                    "sub_pkg/mono_pkg.yaml": "dart:\n - 1.23.0\n - dev\n\nstages:\n  - analyze:\n    - dartanalyzer\n",
                    "sub_pkg/pubspec.yaml": "name: pkg_name\nenvironment:\n  sdk: '>=2.1.0 <3.0.0'\n"
                }
            },
            "expected_output": "package:sub_pkg\n  There are jobs defined that are not compatible with the package SDK constraint (>=2.1.0 <3.0.0): `1.23.0`.\nWrote `.travis.yml`.\nMake sure to mark `./tool/travis.sh` as executable.\n  chmod +x ./tool/travis.sh\nWrote `./tool/travis.sh`.\n--- file: .travis.yml ---\n# Generated by ci-config-generator\nlanguage: dart\n\njobs:\n  include:\n    - stage: analyze\n      name: \"SDK: 1.23.0; PKG: sub_pkg; TASKS: `dartanalyzer .`\"\n      dart: \"1.23.0\"\n      env: PKGS=\"sub_pkg\"\n      script: ./tool/travis.sh dartanalyzer\n    - stage: analyze\n      name: \"SDK: dev; PKG: sub_pkg; TASKS: `dartanalyzer .`\"\n      dart: dev\n      env: PKGS=\"sub_pkg\"\n      script: ./tool/travis.sh dartanalyzer\n\nstages:\n  - analyze\n\n# Only building master means that we don't run two builds for each pull request.\nbranches:\n  only:\n    - master\n\ncache:\n  directories:\n    - \"[standard paths examples for namespaced cache directories]\"\n--- file: tool/travis.sh ---\n#!/bin/bash\n# Generated by ci-config-generator\n\nif [[ -z ${PKGS} ]]; then\n  echo -e '\\033[31mPKGS environment variable must be set!\\033[0m'\n  exit 1\nfi\n\nif [[ \"$#\" == \"0\" ]]; then\n  echo -e '\\033[31mAt least one task argument must be provided!\\033[0m'\n  exit 1\nfi\n\nEXIT_CODE=0\n\nfor PKG in ${PKGS}; do\n  echo -e \"\\033[1mPKG: ${PKG}\\033[22m\"\n  pushd \"${PKG}\" || exit $?\n\n  PUB_EXIT_CODE=0\n  pub upgrade --no-precompile || PUB_EXIT_CODE=$?\n\n  if [[ ${PUB_EXIT_CODE} -ne 0 ]]; then\n    EXIT_CODE=1\n    echo -e '\\033[31mpub upgrade failed\\033[0m'\n    popd\n    continue\n  fi\n\n  for TASK in \"$@\"; do\n    echo\n    echo -e \"\\033[1mPKG: ${PKG}; TASK: ${TASK}\\033[22m\"\n    case ${TASK} in\n    dartanalyzer)\n      echo 'dartanalyzer .'\n      dartanalyzer . || EXIT_CODE=$?\n      ;;\n    *)\n      echo -e \"\\033[31mNot expecting TASK '${TASK}'. Error!\\033[0m\"\n      EXIT_CODE=1\n      ;;\n    esac\n  done\n\n  popd\ndone\n\nexit ${EXIT_CODE}\n"
        }
    ]
}
```


---

### Feature 5: Dependency Resolution Command Option

**As a developer**, I want to choose whether the generated runner resolves dependencies by "upgrading" or by "getting", so the pipeline matches my reproducibility policy.

**Expected Behavior / Usage:**

The runner script fetches each package's dependencies before running its tasks. The `useGet` option selects the verb: the default (`false`) emits the "upgrade" verb; `true` emits the "get" verb. The chosen verb appears in both the dependency-resolution invocation and in the message printed if resolution fails. Everything else in the output is identical between the two modes.

**Test Cases:** `rcb_tests/public_test_cases/feature5_dependency_command_option.json`

```json
{
    "description": "The runner script fetches each package's dependencies before running tasks. A boolean option selects whether the generated script resolves dependencies via the 'upgrade' command (default) or the 'get' command; the chosen verb appears in both the resolution call and its failure message.",
    "cases": [
        {
            "input": {
                "files": {
                    "sub_pkg/mono_pkg.yaml": "dart:\n - dev\n - stable\n\nstages:\n  - analyze:\n    - dartanalyzer\n  - unit_test:\n    - test\n",
                    "sub_pkg/pubspec.yaml": "name: pkg_name\n"
                },
                "useGet": false
            },
            "expected_output": "package:sub_pkg\nWrote `.travis.yml`.\nMake sure to mark `./tool/travis.sh` as executable.\n  chmod +x ./tool/travis.sh\nWrote `./tool/travis.sh`.\n--- file: .travis.yml ---\n# Generated by ci-config-generator\nlanguage: dart\n\njobs:\n  include:\n    - stage: analyze\n      name: \"SDK: dev; PKG: sub_pkg; TASKS: `dartanalyzer .`\"\n      dart: dev\n      env: PKGS=\"sub_pkg\"\n      script: ./tool/travis.sh dartanalyzer\n    - stage: analyze\n      name: \"SDK: stable; PKG: sub_pkg; TASKS: `dartanalyzer .`\"\n      dart: stable\n      env: PKGS=\"sub_pkg\"\n      script: ./tool/travis.sh dartanalyzer\n    - stage: unit_test\n      name: \"SDK: dev; PKG: sub_pkg; TASKS: `pub run test`\"\n      dart: dev\n      env: PKGS=\"sub_pkg\"\n      script: ./tool/travis.sh test\n    - stage: unit_test\n      name: \"SDK: stable; PKG: sub_pkg; TASKS: `pub run test`\"\n      dart: stable\n      env: PKGS=\"sub_pkg\"\n      script: ./tool/travis.sh test\n\nstages:\n  - analyze\n  - unit_test\n\n# Only building master means that we don't run two builds for each pull request.\nbranches:\n  only:\n    - master\n\ncache:\n  directories:\n    - \"[standard paths examples for namespaced cache directories]\"\n--- file: tool/travis.sh ---\n#!/bin/bash\n# Generated by ci-config-generator\n\nif [[ -z ${PKGS} ]]; then\n  echo -e '\\033[31mPKGS environment variable must be set!\\033[0m'\n  exit 1\nfi\n\nif [[ \"$#\" == \"0\" ]]; then\n  echo -e '\\033[31mAt least one task argument must be provided!\\033[0m'\n  exit 1\nfi\n\nEXIT_CODE=0\n\nfor PKG in ${PKGS}; do\n  echo -e \"\\033[1mPKG: ${PKG}\\033[22m\"\n  pushd \"${PKG}\" || exit $?\n\n  PUB_EXIT_CODE=0\n  pub upgrade --no-precompile || PUB_EXIT_CODE=$?\n\n  if [[ ${PUB_EXIT_CODE} -ne 0 ]]; then\n    EXIT_CODE=1\n    echo -e '\\033[31mpub upgrade failed\\033[0m'\n    popd\n    continue\n  fi\n\n  for TASK in \"$@\"; do\n    echo\n    echo -e \"\\033[1mPKG: ${PKG}; TASK: ${TASK}\\033[22m\"\n    case ${TASK} in\n    dartanalyzer)\n      echo 'dartanalyzer .'\n      dartanalyzer . || EXIT_CODE=$?\n      ;;\n    test)\n      echo 'pub run test'\n      pub run test || EXIT_CODE=$?\n      ;;\n    *)\n      echo -e \"\\033[31mNot expecting TASK '${TASK}'. Error!\\033[0m\"\n      EXIT_CODE=1\n      ;;\n    esac\n  done\n\n  popd\ndone\n\nexit ${EXIT_CODE}\n"
        },
        {
            "input": {
                "files": {
                    "sub_pkg/mono_pkg.yaml": "dart:\n - dev\n - stable\n\nstages:\n  - analyze:\n    - dartanalyzer\n  - unit_test:\n    - test\n",
                    "sub_pkg/pubspec.yaml": "name: pkg_name\n"
                },
                "useGet": true
            },
            "expected_output": "package:sub_pkg\nWrote `.travis.yml`.\nMake sure to mark `./tool/travis.sh` as executable.\n  chmod +x ./tool/travis.sh\nWrote `./tool/travis.sh`.\n--- file: .travis.yml ---\n# Generated by ci-config-generator\nlanguage: dart\n\njobs:\n  include:\n    - stage: analyze\n      name: \"SDK: dev; PKG: sub_pkg; TASKS: `dartanalyzer .`\"\n      dart: dev\n      env: PKGS=\"sub_pkg\"\n      script: ./tool/travis.sh dartanalyzer\n    - stage: analyze\n      name: \"SDK: stable; PKG: sub_pkg; TASKS: `dartanalyzer .`\"\n      dart: stable\n      env: PKGS=\"sub_pkg\"\n      script: ./tool/travis.sh dartanalyzer\n    - stage: unit_test\n      name: \"SDK: dev; PKG: sub_pkg; TASKS: `pub run test`\"\n      dart: dev\n      env: PKGS=\"sub_pkg\"\n      script: ./tool/travis.sh test\n    - stage: unit_test\n      name: \"SDK: stable; PKG: sub_pkg; TASKS: `pub run test`\"\n      dart: stable\n      env: PKGS=\"sub_pkg\"\n      script: ./tool/travis.sh test\n\nstages:\n  - analyze\n  - unit_test\n\n# Only building master means that we don't run two builds for each pull request.\nbranches:\n  only:\n    - master\n\ncache:\n  directories:\n    - \"[standard paths examples for namespaced cache directories]\"\n--- file: tool/travis.sh ---\n#!/bin/bash\n# Generated by ci-config-generator\n\nif [[ -z ${PKGS} ]]; then\n  echo -e '\\033[31mPKGS environment variable must be set!\\033[0m'\n  exit 1\nfi\n\nif [[ \"$#\" == \"0\" ]]; then\n  echo -e '\\033[31mAt least one task argument must be provided!\\033[0m'\n  exit 1\nfi\n\nEXIT_CODE=0\n\nfor PKG in ${PKGS}; do\n  echo -e \"\\033[1mPKG: ${PKG}\\033[22m\"\n  pushd \"${PKG}\" || exit $?\n\n  PUB_EXIT_CODE=0\n  pub get --no-precompile || PUB_EXIT_CODE=$?\n\n  if [[ ${PUB_EXIT_CODE} -ne 0 ]]; then\n    EXIT_CODE=1\n    echo -e '\\033[31mpub get failed\\033[0m'\n    popd\n    continue\n  fi\n\n  for TASK in \"$@\"; do\n    echo\n    echo -e \"\\033[1mPKG: ${PKG}; TASK: ${TASK}\\033[22m\"\n    case ${TASK} in\n    dartanalyzer)\n      echo 'dartanalyzer .'\n      dartanalyzer . || EXIT_CODE=$?\n      ;;\n    test)\n      echo 'pub run test'\n      pub run test || EXIT_CODE=$?\n      ;;\n    *)\n      echo -e \"\\033[31mNot expecting TASK '${TASK}'. Error!\\033[0m\"\n      EXIT_CODE=1\n      ;;\n    esac\n  done\n\n  popd\ndone\n\nexit ${EXIT_CODE}\n"
        }
    ]
}
```


---

### Feature 6: Root Aggregation Configuration

**As a developer**, I want an optional repository-root file to inject cross-cutting CI settings and reference stages by name, so I can customize the pipeline without editing every package.

**Expected Behavior / Usage:**

*6.1 Custom Settings Passthrough — inject a verbatim top-level block*

The root aggregation file may carry a `travis` block of custom top-level CI settings. When present, that block is injected verbatim into the generated matrix file under a clearly-marked custom section placed before the jobs list. If the custom block declares its own branch settings, the generator suppresses the default branch block it would otherwise add. An empty (or absent) root file produces the default output with the default branch block.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_custom_ci_passthrough.json`

```json
{
    "description": "An optional root aggregation file may carry a verbatim block of custom top-level CI settings. When present, that block is injected into the generated YAML under a clearly-marked custom section. When the file declares its own branch settings, the generator suppresses its default branch block. An empty root file produces the default output.",
    "cases": [
        {
            "input": {
                "files": {
                    "mono_repo.yaml": "travis:\n  sudo: required\n  addons:\n    chrome: stable\n  branches:\n    only:\n      - master\n      - not_master\n  after_failure:\n  - tool/report_failure.sh\n",
                    "sub_pkg/mono_pkg.yaml": "dart:\n - dev\n\nstages:\n  - analyze:\n    - dartanalyzer\n",
                    "sub_pkg/pubspec.yaml": "name: pkg_name\n"
                }
            },
            "expected_output": "package:sub_pkg\nWrote `.travis.yml`.\nMake sure to mark `./tool/travis.sh` as executable.\n  chmod +x ./tool/travis.sh\nWrote `./tool/travis.sh`.\n--- file: .travis.yml ---\n# Generated by ci-config-generator\nlanguage: dart\n\n# Custom configuration\nsudo: required\naddons:\n  chrome: stable\nbranches:\n  only:\n    - master\n    - not_master\nafter_failure:\n  - tool/report_failure.sh\n\njobs:\n  include:\n    - stage: analyze\n      name: \"SDK: dev; PKG: sub_pkg; TASKS: `dartanalyzer .`\"\n      dart: dev\n      env: PKGS=\"sub_pkg\"\n      script: ./tool/travis.sh dartanalyzer\n\nstages:\n  - analyze\n\ncache:\n  directories:\n    - \"[standard paths examples for namespaced cache directories]\"\n--- file: tool/travis.sh ---\n#!/bin/bash\n# Generated by ci-config-generator\n\nif [[ -z ${PKGS} ]]; then\n  echo -e '\\033[31mPKGS environment variable must be set!\\033[0m'\n  exit 1\nfi\n\nif [[ \"$#\" == \"0\" ]]; then\n  echo -e '\\033[31mAt least one task argument must be provided!\\033[0m'\n  exit 1\nfi\n\nEXIT_CODE=0\n\nfor PKG in ${PKGS}; do\n  echo -e \"\\033[1mPKG: ${PKG}\\033[22m\"\n  pushd \"${PKG}\" || exit $?\n\n  PUB_EXIT_CODE=0\n  pub upgrade --no-precompile || PUB_EXIT_CODE=$?\n\n  if [[ ${PUB_EXIT_CODE} -ne 0 ]]; then\n    EXIT_CODE=1\n    echo -e '\\033[31mpub upgrade failed\\033[0m'\n    popd\n    continue\n  fi\n\n  for TASK in \"$@\"; do\n    echo\n    echo -e \"\\033[1mPKG: ${PKG}; TASK: ${TASK}\\033[22m\"\n    case ${TASK} in\n    dartanalyzer)\n      echo 'dartanalyzer .'\n      dartanalyzer . || EXIT_CODE=$?\n      ;;\n    *)\n      echo -e \"\\033[31mNot expecting TASK '${TASK}'. Error!\\033[0m\"\n      EXIT_CODE=1\n      ;;\n    esac\n  done\n\n  popd\ndone\n\nexit ${EXIT_CODE}\n"
        },
        {
            "input": {
                "files": {
                    "mono_repo.yaml": "",
                    "sub_pkg/mono_pkg.yaml": "dart:\n - dev\n\nstages:\n  - analyze:\n    - dartanalyzer\n",
                    "sub_pkg/pubspec.yaml": "name: pkg_name\n"
                }
            },
            "expected_output": "package:sub_pkg\nWrote `.travis.yml`.\nMake sure to mark `./tool/travis.sh` as executable.\n  chmod +x ./tool/travis.sh\nWrote `./tool/travis.sh`.\n--- file: .travis.yml ---\n# Generated by ci-config-generator\nlanguage: dart\n\njobs:\n  include:\n    - stage: analyze\n      name: \"SDK: dev; PKG: sub_pkg; TASKS: `dartanalyzer .`\"\n      dart: dev\n      env: PKGS=\"sub_pkg\"\n      script: ./tool/travis.sh dartanalyzer\n\nstages:\n  - analyze\n\n# Only building master means that we don't run two builds for each pull request.\nbranches:\n  only:\n    - master\n\ncache:\n  directories:\n    - \"[standard paths examples for namespaced cache directories]\"\n--- file: tool/travis.sh ---\n#!/bin/bash\n# Generated by ci-config-generator\n\nif [[ -z ${PKGS} ]]; then\n  echo -e '\\033[31mPKGS environment variable must be set!\\033[0m'\n  exit 1\nfi\n\nif [[ \"$#\" == \"0\" ]]; then\n  echo -e '\\033[31mAt least one task argument must be provided!\\033[0m'\n  exit 1\nfi\n\nEXIT_CODE=0\n\nfor PKG in ${PKGS}; do\n  echo -e \"\\033[1mPKG: ${PKG}\\033[22m\"\n  pushd \"${PKG}\" || exit $?\n\n  PUB_EXIT_CODE=0\n  pub upgrade --no-precompile || PUB_EXIT_CODE=$?\n\n  if [[ ${PUB_EXIT_CODE} -ne 0 ]]; then\n    EXIT_CODE=1\n    echo -e '\\033[31mpub upgrade failed\\033[0m'\n    popd\n    continue\n  fi\n\n  for TASK in \"$@\"; do\n    echo\n    echo -e \"\\033[1mPKG: ${PKG}; TASK: ${TASK}\\033[22m\"\n    case ${TASK} in\n    dartanalyzer)\n      echo 'dartanalyzer .'\n      dartanalyzer . || EXIT_CODE=$?\n      ;;\n    *)\n      echo -e \"\\033[31mNot expecting TASK '${TASK}'. Error!\\033[0m\"\n      EXIT_CODE=1\n      ;;\n    esac\n  done\n\n  popd\ndone\n\nexit ${EXIT_CODE}\n"
        }
    ]
}
```


*6.2 Stage Reference Validation — referenced stages must exist*

The root file may reference stages by name, either to attach a condition (`travis.stages`, each entry a map of `name` + `if`) or to request merging (`merge_stages`). Every referenced stage name must exist in at least one package's definition. Referencing a name that no package declares is reported as a validation error that names the offending stage.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_unknown_stage_reference.json`

```json
{
    "description": "The root aggregation file may reference stages by name (to attach conditions or to request merging). Every referenced stage must exist in at least one package's definition; referencing a stage that no package declares is reported as a configuration error naming the offending stage.",
    "cases": [
        {
            "input": {
                "files": {
                    "mono_repo.yaml": "travis:\n  stages:\n    - name: bob\n      if: branch = master\n",
                    "sub_pkg/mono_pkg.yaml": "dart:\n - dev\n\nstages:\n  - analyze:\n    - dartanalyzer\n",
                    "sub_pkg/pubspec.yaml": "name: pkg_name\n"
                }
            },
            "expected_output": "error=user_exception\nmessage=Error parsing mono_repo.yaml\ndetails=Stage `bob` was referenced in `mono_repo.yaml`, but it does not exist in any `mono_pkg.yaml` files.\n"
        },
        {
            "input": {
                "files": {
                    "mono_repo.yaml": "merge_stages:\n  - bob\n",
                    "sub_pkg/mono_pkg.yaml": "dart:\n - dev\n\nstages:\n  - analyze:\n    - dartanalyzer\n",
                    "sub_pkg/pubspec.yaml": "name: pkg_name\n"
                }
            },
            "expected_output": "error=user_exception\nmessage=Error parsing mono_repo.yaml\ndetails=Stage `bob` was referenced in `mono_repo.yaml`, but it does not exist in any `mono_pkg.yaml` files.\n"
        }
    ]
}
```


*6.3 Root Schema Validation — strict shape for the aggregation file*

The root file accepts only the top-level keys `travis` and `merge_stages`. Each section has a strict shape: stage collections and merge collections must be arrays; stage entries must be maps; a conditional-stage map must contain exactly the keys `name` and `if` (missing `if` and any extra key are both rejected); stage names must be unique; merge entries must be strings; the custom block must be a map; and reserved keys are forbidden inside the custom block. Each rejection reports the location (line/column with a source excerpt) and the reason.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_root_config_schema.json`

```json
{
    "description": "The root aggregation file accepts only a fixed set of top-level keys, and each section has a strict shape. The generator rejects unknown top-level keys, non-array stage/merge collections, stage entries that are not maps, stage maps missing the required condition key or carrying unrecognized keys, duplicate stage names, non-string merge entries, a non-map custom block, and reserved keys inside the custom block. Each rejection reports the location and reason.",
    "cases": [
        {
            "input": {
                "files": {
                    "mono_repo.yaml": "other:\n  stages: 5\n",
                    "sub_pkg/mono_pkg.yaml": "dart:\n - dev\n\nstages:\n  - analyze:\n    - dartanalyzer\n",
                    "sub_pkg/pubspec.yaml": "name: pkg_name\n"
                }
            },
            "expected_output": "error=config_parse\nmessage=line 2, column 3 of mono_repo.yaml: Unsupported value for \"other\". Only `travis`, `merge_stages` keys are supported.\n  ╷\n2 │   stages: 5\n  │   ^^^^^^^^^\n  ╵\n"
        },
        {
            "input": {
                "files": {
                    "mono_repo.yaml": "travis:\n  stages: 5\n",
                    "sub_pkg/mono_pkg.yaml": "dart:\n - dev\n\nstages:\n  - analyze:\n    - dartanalyzer\n",
                    "sub_pkg/pubspec.yaml": "name: pkg_name\n"
                }
            },
            "expected_output": "error=config_parse\nmessage=line 2, column 11 of mono_repo.yaml: Unsupported value for \"stages\". `stages` must be an array.\n  ╷\n2 │   stages: 5\n  │           ^\n  ╵\n"
        },
        {
            "input": {
                "files": {
                    "mono_repo.yaml": "travis:\n  stages:\n    - name: bob\n",
                    "sub_pkg/mono_pkg.yaml": "dart:\n - dev\n\nstages:\n  - analyze:\n    - dartanalyzer\n",
                    "sub_pkg/pubspec.yaml": "name: pkg_name\n"
                }
            },
            "expected_output": "error=config_parse\nmessage=line 3, column 7 of mono_repo.yaml: Required keys are missing: if.\n  ╷\n3 │     - name: bob\n  │       ^^^^^^^^^\n  ╵\n"
        }
    ]
}
```


---

### Feature 7: Package Definition Validation

**As a developer**, I want clear, specific errors when a package definition is missing, malformed, empty, legacy-named, or incomplete, so I can fix configuration mistakes quickly.

**Expected Behavior / Usage:**

Before any output is produced, every discovered package definition is validated. The generator reports, with a distinct message for each: no package directory containing a definition file was found; a definition whose top-level content is not a map; a definition that produces no runnable tasks; a definition stored under the legacy file name that must be renamed; a definition missing the required SDK list; and a task carrying unsupported extra options. Structural-schema errors include a location and source excerpt; semantic validation errors carry a message and optional details.

**Test Cases:** `rcb_tests/public_test_cases/feature7_package_config_validation.json`

```json
{
    "description": "Package-level definitions are validated before any output is produced. The generator reports: no package directory containing a definition file; a definition whose top-level content is not a map; a definition that yields no runnable tasks; a legacy-named definition file that must be renamed; a definition missing the required SDK list; and a task carrying unsupported extra options. Each report states the reason and, for schema errors, the location.",
    "cases": [
        {
            "input": {
                "files": {
                    "sub_pkg/.keep": ""
                }
            },
            "expected_output": "error=user_exception\n[a message indicating the absence of package definitions]\ndetails=Each target package directory must contain a `mono_pkg.yaml` file.\n"
        },
        {
            "input": {
                "files": {
                    "sub_pkg/mono_pkg.yaml": "bob",
                    "sub_pkg/pubspec.yaml": "name: pkg_name\n"
                }
            },
            "expected_output": "error=user_exception\nmessage=The contents of `sub_pkg/mono_pkg.yaml` must be a Map.\ndetails=\n"
        },
        {
            "input": {
                "files": {
                    "sub_pkg/mono_pkg.yaml": "# just a comment!\n",
                    "sub_pkg/pubspec.yaml": "name: pkg_name\n"
                }
            },
            "expected_output": "error=user_exception\nmessage=No entries created. Check your nested `mono_pkg.yaml` files.\ndetails=\n"
        }
    ]
}
```


---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the features above — filesystem discovery, schema parsing/validation, stage-graph ordering, task de-duplication, and the matrix + runner renderers — kept decoupled from stdin/stdout and JSON.

2. **The Execution/Test Adapter:** A runnable entry point that reads a JSON command from stdin, materializes the virtual repository, invokes the core engine, and prints either the console log plus generated artifacts or a normalized language-neutral error block, exactly matching the per-feature contracts above. It must be logically and physically separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{stem}@{index:03d}.txt` containing only the raw program stdout, namespaced by `<cases-dir>` so different case directories never overwrite each other.


---
**Implementation notes:**
- follow the same formatting as the existing cycle detection error output
- use the default dependency resolution command for get-enabled modes
