## Product Requirement Document

# Terminal Command Risk Guard - Black-Box Command Safety Contracts

## Project Goal

Build a terminal command risk-guard library/tool that allows developers to evaluate shell commands against configurable risky-command rules and manage those rules without manually reimplementing pattern matching, configuration parsing, and confirmation-policy updates.

---

## Background & Problem

Without this library/tool, developers who want a safety layer before dangerous terminal commands must write repeated ad hoc checks for literal text, prefixes, regular expressions, grouped rule sets, and challenge settings. This leads to fragile command filters, inconsistent configuration files, and risky behavior changes when rule lists evolve.

With this library/tool, developers can define risk checks, load and update a configuration, evaluate commands, and expose deterministic adapter output that reports exactly which externally visible risk rules matched.

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

### Feature 1: Command Risk Matching

**As a developer**, I want to evaluate command text against configured risk patterns, so I can identify dangerous terminal actions before they are executed.

**Expected Behavior / Usage:**

*1.1 Literal containment matching — Report a risk when an enabled rule's literal text appears anywhere inside the command.*

The input provides a list of enabled or disabled risk checks and one or more command strings. A containment check matches when its pattern appears as a substring of the command. For each command, stdout must include the command index and text, the number of matched checks, and, for every match, the rule group and warning description. Non-matching commands must report a zero match count.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_contains_matching.json`

```json
{
    "description": "A command is reported as risky when it contains an enabled literal pattern, and non-matching text reports no matched risk.",
    "cases": [
        {
            "input": {
                "feature": "match_commands",
                "checks": [
                    {
                        "group": "sample",
                        "pattern": "test",
                        "method": "contains",
                        "enabled": true,
                        "description": "contains matched"
                    }
                ],
                "commands": [
                    "test is valid",
                    "not-found"
                ]
            },
            "expected_output": "command[0]=test is valid\nmatch_count=1\nmatch_group=sample\nmatch_description=contains matched\n---\ncommand[1]=not-found\nmatch_count=0\n"
        }
    ]
}
```

*1.2 Prefix matching — Report a risk only when the command begins with an enabled prefix pattern.*

The input provides risk checks and command strings. A prefix check matches only when the command starts with the configured pattern. Commands that contain the pattern later but do not begin with it must report no matches. Output follows the same per-command match summary shape as other command matching contracts.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_prefix_matching.json`

```json
{
    "description": "A command is reported as risky only when it begins with an enabled prefix pattern.",
    "cases": [
        {
            "input": {
                "feature": "match_commands",
                "checks": [
                    {
                        "group": "sample",
                        "pattern": "test is",
                        "method": "starts_with",
                        "enabled": true,
                        "description": "prefix matched"
                    }
                ],
                "commands": [
                    "test is valid",
                    "is"
                ]
            },
            "expected_output": "command[0]=test is valid\nmatch_count=1\nmatch_group=sample\nmatch_description=prefix matched\n---\ncommand[1]=is\nmatch_count=0\n"
        }
    ]
}
```

*1.3 Regular-expression matching — Report a risk when an enabled expression matches command text.*

The input provides risk checks whose patterns are regular expressions and one or more commands. A regular-expression check matches when the expression matches the command text. Output must expose the original command string, the match count, and the matched rule group and description so that callers can distinguish a real rule-engine match from a hard-coded boolean response.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_regex_matching.json`

```json
{
    "description": "A command is reported as risky when an enabled regular-expression pattern matches the command text.",
    "cases": [
        {
            "input": {
                "feature": "match_commands",
                "checks": [
                    {
                        "group": "sample",
                        "pattern": "rm.+(-r|-f|-rf|-fr)*",
                        "method": "regex",
                        "enabled": true,
                        "description": "regex matched"
                    }
                ],
                "commands": [
                    "rm -rf",
                    "foo"
                ]
            },
            "expected_output": "command[0]=rm -rf\nmatch_count=1\nmatch_group=sample\nmatch_description=regex matched\n---\ncommand[1]=foo\nmatch_count=0\n"
        }
    ]
}
```

---

### Feature 2: Risk Configuration Management

**As a developer**, I want to load and transform risk-check configuration data, so I can keep command safety behavior consistent as rule groups and challenge settings change.

**Expected Behavior / Usage:**

*2.1 Load configuration — Parse a configuration document into its externally visible challenge setting, included groups, and check summaries.*

The input provides a YAML configuration document containing a default challenge, an ordered list of included risk groups, and zero or more checks. The output must summarize the loaded challenge, preserve include order, report the active check count, and render each check as group, match method, enabled flag, challenge override, and warning description.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_load_configuration.json`

```json
{
    "description": "A YAML configuration is loaded into challenge type, included risk groups, and enabled check summaries.",
    "cases": [
        {
            "input": {
                "feature": "load_config",
                "yaml": "---\nchallenge: Math\nincludes:\n  - default-check\nversion: 0.2.2\nchecks:\n- from: default-check\n  test: default-check\n  method: Regex\n  enable: true\n  description: \"\"\n"
            },
            "expected_output": "challenge=Math\nincludes=default-check\ncheck_count=1\ncheck=default-check|Regex|true|[a fallback string for empty descriptions — verify via test output]|\n"
        }
    ]
}
```

*2.2 Add and remove check groups — Update included groups and active checks from an available rule catalog.*

The input provides an initial configuration, a catalog of available checks, a list of groups to add, and a list of groups to remove. Added groups must appear in the include list only once and their catalog checks must be inserted into the active check list. Removed groups must be absent from the include list and their checks must be removed from the active check list. Existing checks outside the changed groups must remain in order.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_update_check_groups.json`

```json
{
    "description": "Adding risk groups inserts their default checks without duplicating existing includes, while removing groups deletes their checks from the active configuration.",
    "cases": [
        {
            "input": {
                "feature": "update_groups",
                "initial_yaml": "---\nchallenge: Math\nincludes:\n  - default-check\nversion: 0.2.2\nchecks:\n- from: default-check\n  test: default-check\n  method: Regex\n  enable: true\n  description: \"\"\n",
                "available_checks": [
                    {
                        "group": "test-1",
                        "pattern": "test-1",
                        "method": "regex",
                        "enabled": true,
                        "description": ""
                    },
                    {
                        "group": "test-2",
                        "pattern": "test-2",
                        "method": "regex",
                        "enabled": true,
                        "description": ""
                    },
                    {
                        "group": "test-disabled",
                        "pattern": "test-disabled",
                        "method": "regex",
                        "enabled": true,
                        "description": ""
                    }
                ],
                "add": [
                    "test-1",
                    "test-2"
                ],
                "remove": []
            },
            "expected_output": "challenge=Math\nincludes=default-check,test-1,test-2\ncheck_count=3\ncheck=default-check|Regex|true|[a fallback string for empty descriptions — verify via test output]|\ncheck=test-1|Regex|true|[a fallback string for empty descriptions — verify via test output]|\ncheck=test-2|Regex|true|[a fallback string for empty descriptions — verify via test output]|\n"
        },
        {
            "input": {
                "feature": "update_groups",
                "initial_yaml": "---\nchallenge: Math\nincludes:\n  - default-check\nversion: 0.2.2\nchecks:\n- from: default-check\n  test: default-check\n  method: Regex\n  enable: true\n  description: \"\"\n",
                "available_checks": [
                    {
                        "group": "test-1",
                        "pattern": "test-1",
                        "method": "regex",
                        "enabled": true,
                        "description": ""
                    },
                    {
                        "group": "test-2",
                        "pattern": "test-2",
                        "method": "regex",
                        "enabled": true,
                        "description": ""
                    },
                    {
                        "group": "test-disabled",
                        "pattern": "test-disabled",
                        "method": "regex",
                        "enabled": true,
                        "description": ""
                    }
                ],
                "add": [
                    "test-1",
                    "test-2"
                ],
                "remove": [
                    "test-1"
                ]
            },
            "expected_output": "challenge=Math\nincludes=default-check,test-2\ncheck_count=2\ncheck=default-check|Regex|true|[a fallback string for empty descriptions — verify via test output]|\ncheck=test-2|Regex|true|[a fallback string for empty descriptions — verify via test output]|\n"
        }
    ]
}
```

*2.3 Reset configuration — Replace the current configuration with the default challenge and default group list.*

The input provides an existing configuration, an available rule catalog, and whether a backup should be created before replacement. Reset output must report the backup decision, set the default challenge to the math challenge, restore the default include groups in order, and summarize the active checks selected from the provided catalog.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_reset_configuration.json`

```json
{
    "description": "Resetting configuration replaces the current settings with the default challenge and default included groups, and reports whether a backup was requested.",
    "cases": [
        {
            "input": {
                "feature": "reset_config",
                "initial_yaml": "---\nchallenge: Math\nincludes:\n  - default-check\nversion: 0.2.2\nchecks:\n- from: default-check\n  test: default-check\n  method: Regex\n  enable: true\n  description: \"\"\n",
                "available_checks": [
                    {
                        "group": "test-1",
                        "pattern": "test-1",
                        "method": "regex",
                        "enabled": true,
                        "description": ""
                    },
                    {
                        "group": "test-2",
                        "pattern": "test-2",
                        "method": "regex",
                        "enabled": true,
                        "description": ""
                    },
                    {
                        "group": "test-disabled",
                        "pattern": "test-disabled",
                        "method": "regex",
                        "enabled": true,
                        "description": ""
                    }
                ],
                "backup_existing": true
            },
            "expected_output": "backup_created=yes\nchallenge=Math\nincludes=base,fs,git\ncheck_count=0\n"
        }
    ]
}
```

*2.4 Update challenge policy — Change the default confirmation challenge while preserving existing includes and checks.*

The input provides an initial configuration and a new challenge value. The output must show the new challenge value while preserving the existing include list and active checks. Check-level challenge values remain unchanged unless explicitly represented in the check data.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_update_challenge.json`

```json
{
    "description": "Changing the default confirmation challenge preserves the configured checks and includes while replacing the challenge type.",
    "cases": [
        {
            "input": {
                "feature": "update_challenge",
                "initial_yaml": "---\nchallenge: Math\nincludes:\n  - default-check\nversion: 0.2.2\nchecks:\n- from: default-check\n  test: default-check\n  method: Regex\n  enable: true\n  description: \"\"\n",
                "challenge": "Yes"
            },
            "expected_output": "challenge=Yes\nincludes=default-check\ncheck_count=1\ncheck=default-check|Regex|true|[a fallback string for empty descriptions — verify via test output]|\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- maintain the ordering strategy used in the groups utility
- follow the canonical summary format defined in the helper module
