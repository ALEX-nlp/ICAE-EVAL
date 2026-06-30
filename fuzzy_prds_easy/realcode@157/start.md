## Product Requirement Document

# Assembly Discovery Mode Selector — A Two-Mode Resolver for Component Scanning Strategy

## Project Goal

Build a small library that defines how a configuration-driven framework decides **where to look for plug-in components** (the assemblies/libraries that contribute extensions such as sinks, enrichers, or formatters). Application authors choose a discovery strategy by selecting one of a fixed set of named modes, so they can control component scanning behaviour declaratively without writing custom discovery code.

---

## Background & Problem

A framework that loads optional components by reflection must first decide which compiled libraries are even candidates for scanning. There are two reasonable strategies: trust the libraries already loaded into the running process, or always walk the library files sitting in the working directory. Hard-coding one strategy makes the framework brittle — some host environments expose an entry assembly and some do not.

This library solves that by publishing a **closed enumeration of discovery modes**. Each mode is a stable, named option with a fixed ordinal position. Callers pass the chosen mode into the framework; downstream code branches on it. The enumeration is the public contract: its member identifiers, their ordinal values, and which member is the default must remain stable, because configuration files and host code refer to the modes by name and by position.

With this enumeration, a developer can ask "what does mode X mean, what is its ordinal, and is it the default?" and get a deterministic answer that does not depend on any runtime, reflection, or I/O.

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

The behavioural surface is a single closed enumeration with exactly two members, in this declared order:

1. The **default** mode (ordinal `0`) — discover candidate libraries from those already loaded in the running process.
2. The **explicit on-disk scanning** mode (ordinal `1`) — always discover candidate libraries by scanning library files in the working directory.

The program is a resolver. It reads one JSON command from standard input and prints a deterministic, multi-line description of the resolved mode to standard output.

**Command shape.** The input is a JSON object with two fields: `op` (the operation, always `"describe"`) and `selector` (the mode to resolve). The `selector` may be given either as the mode's canonical identifier (a string such as the names introduced in the example cases below) or as the mode's ordinal rendered as a decimal string (`"0"`, `"1"`).

**Output shape.** Three lines, each `key=value`, terminated by a trailing newline:

```
name=<canonical mode identifier>
value=<ordinal as a decimal integer>
default=<true if this is the default mode, otherwise false>
```

The `name` is always the canonical identifier of the resolved mode, even when the caller selected it by ordinal. The `default` line is `true` only for the mode at ordinal `0`.

---

### Feature 1: Default in-process discovery mode

**As a developer**, I want to select the default discovery mode and confirm its identity, so I can rely on the framework using already-loaded libraries when I do not opt into anything else.

**Expected Behavior / Usage:**

Resolving the default mode returns its canonical identifier, the ordinal `0`, and `default=true`. Because this mode occupies ordinal `0`, selecting it by the identifier and selecting it by the string `"0"` yield identical output. This is the mode a caller gets implicitly when no explicit choice is made.

**Test Cases:** `rcb_tests/public_test_cases/feature1_default_loaded_assemblies_mode.json`

```json
{
    "description": "Resolving the default assembly-discovery mode of the two-mode selector. This mode instructs the configuration reader to discover candidate assemblies from those already present in the running process rather than scanning files on disk. It is the first-declared member of the selector, so it owns ordinal 0 and is the value chosen when no mode is supplied. The resolver echoes the canonical mode identifier, its ordinal, and whether it is the default. The selector may be given as the mode identifier or as its ordinal.",
    "cases": [
        {
            "input": {"op": "describe", "selector": "UseLoadedAssemblies"},
            "expected_output": "name=UseLoadedAssemblies\nvalue=0\ndefault=true\n"
        }
    ]
}
```

---

### Feature 2: Explicit on-disk scanning mode

**As a developer**, I want to select the explicit file-scanning discovery mode and confirm its identity, so I can force the framework to scan library files on disk in hosts that do not expose an entry assembly.

**Expected Behavior / Usage:**

Resolving the explicit scanning mode returns its canonical identifier, the ordinal `1`, and `default=false`. Selecting it by identifier and selecting it by the string `"1"` yield identical output. This is the non-default alternative to the in-process discovery strategy.

**Test Cases:** `rcb_tests/public_test_cases/feature2_explicit_dll_scanning_mode.json`

```json
{
    "description": "Resolving the explicit on-disk scanning mode of the two-mode selector. This mode instructs the configuration reader to always discover candidate assemblies by scanning library files in the working directory instead of relying on assemblies already loaded in the process. It is the second-declared member of the selector, so it owns ordinal 1 and is not the default. The resolver echoes the canonical mode identifier, its ordinal, and whether it is the default. The selector may be given as the mode identifier or as its ordinal.",
    "cases": [
        {
            "input": {"op": "describe", "selector": "AlwaysScanDllFiles"},
            "expected_output": "name=AlwaysScanDllFiles\nvalue=1\ndefault=false\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON command (`op` + `selector`) from stdin and prints the resolved mode's `name`, `value`, and `default` to stdout, matching the per-feature contracts above.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- Implementation consistent with the resolver module's default state logic
- Output follows the standard response envelope format defined in the protocol spec
