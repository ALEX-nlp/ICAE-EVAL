## Product Requirement Document

# Configuration-Driven Webhook Command Server — Validation, Invocation, and Routing Core

## Project Goal

Build a small webhook server toolkit that lets developers expose shell commands over HTTP purely from a declarative configuration, so they can wire up "when this URL is hit, run that command" endpoints without writing any server code by hand.

---

## Background & Problem

Teams frequently need to trigger a script when an external system calls a URL: redeploy on a push, rotate a log on demand, kick off a backup. Without a reusable layer, each project re-implements the same plumbing — parsing a config of endpoints, validating it, mapping each entry onto one or more HTTP verbs, and shelling out to the right interpreter for the host platform.

This toolkit provides that shared core. It validates each webhook definition up front so misconfiguration fails fast, expands a definition that lists several HTTP methods into one route per method, normalizes a command string into the exact arguments needed to spawn a child process on the current operating system, and selects distinct colors in round-robin fashion so concurrent command logs can be told apart. The result is a contract-driven core that an HTTP layer can drive directly.

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

### Feature 1: Webhook Definition Validation

**As a developer**, I want each webhook definition checked before it is used, so misconfiguration is rejected up front instead of producing a broken or unsafe endpoint.

**Expected Behavior / Usage:**

A webhook definition is an object with three fields: a `method`, a `path`, and a `command`. A definition is accepted only when all three fields are individually valid; otherwise it is rejected. The outcome is reported on a single line as `valid=true` when accepted and `valid=false` when rejected (followed by a trailing newline). The rules for each field are independent and are described in the leaf sub-features below.

*1.1 Method Field — accepted HTTP verbs, single or list*

The `method` must be either a single HTTP verb or a non-empty list of HTTP verbs. The recognized verbs are `GET`, `POST`, `PUT`, and `DELETE`, matched case-insensitively (so `get` and `Post` are accepted). A single unrecognized verb, a list containing any unrecognized verb, an empty list, an empty string, a number, `null`, or a plain object all make the definition invalid.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_method_validation.json`

```json
{
    "description": "Validate the HTTP method field of a webhook definition. A webhook is an object carrying a method, a relative path, and a shell command. The method must be either a single HTTP verb (one of GET, POST, PUT, DELETE, compared case-insensitively) or a non-empty list whose every element is such a verb. Any other value (an unknown verb, a list containing an unknown verb, an empty string, a number, null, an empty list, or a plain object) makes the whole definition invalid. The output reports whether the definition is accepted.",
    "cases": [
        {"input": {"feature": "validate", "hook": {"method": ["get", "Post", "PUT", "DELETE"], "path": "/hello", "command": "echo hello world"}}, "expected_output": "valid=true\n"},
        {"input": {"feature": "validate", "hook": {"method": "[a specific forbidden token — ask the PM for the exact string]", "path": "/foo", "command": "echo bar"}}, "expected_output": "valid=false\n"}
    ]
}
```

*1.2 Path Field — relative URL shape*

The `path` must be a string that begins with a forward slash and otherwise contains only ASCII letters, digits, hyphens, and additional forward slashes; a trailing slash is allowed. Any string that does not start with a slash, or that contains any other character (for example a question mark, a dot, or a dollar sign), is rejected, as are the empty string and any non-string value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_path_validation.json`

```json
{
    "description": "Validate the path field of a webhook definition while the method and command are held at valid values. A path is accepted only when it is a string beginning with a forward slash and otherwise containing only letters, digits, hyphens, and additional forward slashes; a trailing slash is allowed. Any string that does not start with a slash, or that contains characters outside that set (such as a question mark, a dot, or a dollar sign), is rejected, as is any non-string value or the empty string. The output reports whether the definition is accepted.",
    "cases": [
        {"input": {"feature": "validate", "hook": {"method": "GET", "path": "/hello/world", "command": "echo bar"}}, "expected_output": "valid=true\n"},
        {"input": {"feature": "validate", "hook": {"method": "GET", "path": "/hello.php", "command": "echo bar"}}, "expected_output": "valid=false\n"}
    ]
}
```

*1.3 Command Field — non-empty string*

The `command` must be a non-empty string. The empty string and any non-string value (a number, `null`, an object, or a list) make the definition invalid.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_command_validation.json`

```json
{
    "description": "Validate the command field of a webhook definition while the method and path are held at valid values. The command must be a non-empty string; any non-string value (a number, null, an object, a list) or the empty string makes the definition invalid. The output reports whether the definition is accepted.",
    "cases": [
        {"input": {"feature": "validate", "hook": {"method": "GET", "path": "/foo", "command": "echo bar"}}, "expected_output": "valid=true\n"},
        {"input": {"feature": "validate", "hook": {"method": "GET", "path": "/foo", "command": null}}, "expected_output": "valid=false\n"}
    ]
}
```

---

### Feature 2: Shell Command Invocation Normalization

**As a developer**, I want a command string turned into the exact executable and argument list for the current operating system, so the same configuration runs correctly on both Windows-family and Unix-like hosts.

**Expected Behavior / Usage:**

The input supplies a `command` string, a `platform` identifier (as reported by the runtime, e.g. `win32`, `darwin`, `linux`), and optionally a `comspec` naming the OS command interpreter. The output is an invocation descriptor with three parts in this order: `file` (the executable to spawn), `args` (the ordered argument list), and `options` (a map of spawn options), rendered as a single compact JSON object on one line.

On a Windows-family platform (`platform` equal to `win32`), the descriptor runs the command through the command interpreter: `file` is the supplied `comspec` if present, otherwise the default `cmd.exe`; `args` is `["/s", "/c", "\"<command>\""]` where the command is wrapped verbatim in double quotes; and `options` is `{"windowsVerbatimArguments": true}`. On any other (Unix-like) platform, `file` is `/bin/sh`, `args` is `["-c", "<command>"]`, and `options` is an empty map `{}`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_command_normalization.json`

```json
{
    "description": "Translate a single shell command string into the concrete arguments needed to spawn a child process, given the host operating-system family. The request supplies the command, the platform identifier, and optionally the name of the OS command interpreter. On Windows-family platforms the command must be run through the command interpreter (taken from the supplied interpreter name, or a default of cmd.exe when none is given) with the switches that pass the verbatim command, and verbatim-argument handling must be enabled. On any other (Unix-like) platform the command must be run through the POSIX shell with its command switch and no special options. The output is the resulting invocation descriptor: the executable file, the ordered argument list, and the options map.",
    "cases": [
        {"input": {"feature": "normalize", "command": "echo Hello world", "platform": "win32"}, "expected_output": "{\"file\":\"cmd.exe\",\"args\":[\"/s\",\"/c\",\"\\\"echo Hello world\\\"\"],\"options\":{\"windowsVerbatimArguments\":true}}\n"},
        {"input": {"feature": "normalize", "command": "echo Hello from the other side", "platform": "darwin"}, "expected_output": "{\"file\":\"/bin/sh\",\"args\":[\"-c\",\"echo Hello from the other side\"],\"options\":{}}\n"}
    ]
}
```

---

### Feature 3: Route Registration with Method Expansion

**As a developer**, I want a list of webhook definitions turned into concrete routes, with multi-method entries expanded into one route per verb, so I can declare several verbs for one endpoint in a single line of configuration.

**Expected Behavior / Usage:**

The input supplies a `hooks` list of webhook definitions. Every definition is validated first (per Feature 1). A definition whose `method` is a single verb yields exactly one route; a definition whose `method` is a list of verbs yields one route per listed verb. Routes are produced in the order the definitions appear, and within a multi-verb definition in the order the verbs are listed. The output lists each registered route on its own line as the HTTP verb (upper-case) followed by a single space and the path.

An empty `hooks` list registers nothing and produces no output. Error conditions are reported as a single neutral `error=<category>` line: when no `hooks` list is supplied at all, the category is `no_hooks`; when a supplied definition fails validation, the category is `invalid_hook`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_route_registration.json`

```json
{
    "description": "Register a list of webhook definitions as routes, expanding any definition whose method is a list into one route per method. Each definition supplies a method (a single HTTP verb or a list of verbs), a relative path, and a command. Registration validates every definition first; a definition with a single method produces one route, while a definition whose method is a list produces one route for each listed method, preserving the order of definitions and of the methods within each definition. If no list of definitions is supplied at all the operation fails; if a supplied definition is not valid the operation fails. The output is the ordered list of registered routes, each shown as the HTTP verb and the path, one route per line; an empty list of definitions registers nothing.",
    "cases": [
        {"input": {"feature": "register", "hooks": [{"method": "GET", "path": "/foo", "command": "echo bar"}, {"method": ["GET", "POST"], "path": "/hello", "command": "echo hello world"}]}, "expected_output": "GET /foo\nGET /hello\nPOST /hello\n"},
        {"input": {"feature": "register"}, "expected_output": "error=no_hooks\n"}
    ]
}
```

---

### Feature 4: Round-Robin Color Selection

**As a developer**, I want successive log streams assigned distinct colors that cycle through a fixed palette, so output from concurrently running commands can be visually told apart.

**Expected Behavior / Usage:**

The input supplies an ordered `colors` palette (a list of color labels) and a `count` of selections to make. Selections walk through the palette in order; once the last entry is used, the next selection wraps back to the first entry, repeating indefinitely. The output is the resulting sequence of selected labels, one per line, in the order drawn.

**Test Cases:** `rcb_tests/public_test_cases/feature4_color_cycle.json`

```json
{
    "description": "Draw a sequence of colors from a fixed, ordered palette using round-robin selection. The request supplies the palette (an ordered list of color labels) and the number of selections to make. Successive selections walk through the palette in order and wrap back to the first entry once the end is reached, repeating indefinitely. The output is the resulting sequence of selected labels, one per line, in the order drawn.",
    "cases": [
        {"input": {"feature": "cycle", "colors": ["blue", "red", "green"], "count": 5}, "expected_output": "blue\nred\ngreen\nblue\nred\n"},
        {"input": {"feature": "cycle", "colors": ["only"], "count": 3}, "expected_output": "only\nonly\nonly\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result to stdout, matching the per-feature contracts above. The request's `feature` field selects behavior: `validate` checks one webhook definition; `normalize` turns a command plus platform into a spawn descriptor; `register` expands a list of definitions into routes; `cycle` draws a round-robin color sequence. Native errors must be rendered as neutral `error=<category>` lines, never as host-language runtime traces.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the HTTP method naming convention used in `routes.py`
- use the quoting strategy from the test case `test_shell_escapes`
