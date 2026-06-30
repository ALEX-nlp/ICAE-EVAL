## Product Requirement Document

# Cloud Script Project CLI - Command-Line Project and File Metadata Behavior

## Project Goal

Build a command-line library/tool for hosted script projects that allows developers to inspect command usage, translate project/file metadata, manage API subcommands, and clear local credentials without hand-coding project URL formats, file type conversions, or credential cleanup steps.

---

## Background & Problem

Without this library/tool, developers are forced to manually assemble script editor URLs, remember platform-specific file type labels, inspect command syntax by trial and error, and delete credential files from multiple locations themselves. This leads to repetitive command wrappers, inconsistent metadata conversion, and stale authentication state during local development.

With this library/tool, developers get predictable command-line help, stable metadata formatting, clear API-subcommand responses, and deterministic credential cleanup through a single executable interface.

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

### Feature 1: Command Help Rendering

**As a developer**, I want command help text to expose usage, purpose, and supported options, so I can understand how to invoke a command without reading source code.

**Expected Behavior / Usage:**

*1.1 Run-command help — Help for executing a remote script function*

Given the command-line argument sequence for requesting help on the run operation, the executable must exit successfully and print help content that includes the usage form, a human-readable purpose line saying it runs a function in the hosted script project, and the standard help option. The adapter renders these externally observable help fields as newline-delimited key/value lines.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_run_help.json`

```json
{
    "description": "Render command-line help for running a remote script function, including the usage form, purpose text, and help option.",
    "cases": [
        {
            "input": [
                "run",
                "--help"
            ],
            "expected_output": "exit_code=0\nusage=Usage: run [options] <functionName>\ndescription=Run a function in your Apps Scripts project\noption=-h, --help  output usage information\n"
        }
    ]
}
```

*1.2 Log-command help — Help for viewing remote execution logs*

Given the command-line argument sequence for requesting help on the logs operation, the executable must exit successfully and print help content that includes the usage form, a human-readable purpose line saying it shows StackDriver logs, the JSON-output option, the browser-opening option, and the standard help option. The adapter renders these externally observable help fields as newline-delimited key/value lines.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_logs_help.json`

```json
{
    "description": "Render command-line help for viewing remote execution logs, including usage, purpose text, log-format options, browser-opening option, and help option.",
    "cases": [
        {
            "input": [
                "logs",
                "--help"
            ],
            "expected_output": "exit_code=0\nusage=Usage: logs [options]\ndescription=Shows the StackDriver logs\noption=--json      Show logs in JSON form\noption=--open      Open the StackDriver logs in browser\noption=-h, --help  output usage information\n"
        }
    ]
}
```

---

### Feature 2: Script Editor URL Formatting

**As a developer**, I want a project identifier to be converted into the corresponding online editor URL, so I can open a project directly from stored metadata.

**Expected Behavior / Usage:**

The input is a script project identifier string. The output is a single `script_url` line containing the editor URL formed by placing that identifier in the `/d/{identifier}/edit` path of the script editor host. The identifier is preserved exactly in the URL path.

**Test Cases:** `rcb_tests/public_test_cases/feature2_editor_url.json`

```json
{
    "description": "Convert a script project identifier into the browser URL for editing that project.",
    "cases": [
        {
            "input": "abcdefghijklmnopqrstuvwxyz",
            "expected_output": "script_url=https://script.google.com/d/abcdefghijklmnopqrstuvwxyz/edit\n"
        }
    ]
}
```

---

### Feature 3: Local File Extension Mapping

**As a developer**, I want remote file type labels to become local file extensions, so downloaded files use expected local names.

**Expected Behavior / Usage:**

The input is a remote file type label string. The output is a single `local_type` line. The server-side script label maps to `js`; other tested labels are lowercased as local extensions.

**Test Cases:** `rcb_tests/public_test_cases/feature3_local_file_type.json`

```json
{
    "description": "Convert remote file type labels into local filename extensions, using JavaScript extension output for server-side script labels and lowercase output for other labels.",
    "cases": [
        {
            "input": "SERVER_JS",
            "expected_output": "local_type=js\n"
        },
        {
            "input": "GS",
            "expected_output": "local_type=gs\n"
        },
        {
            "input": "JS",
            "expected_output": "local_type=js\n"
        }
    ]
}
```

---

### Feature 4: Remote File Type Mapping

**As a developer**, I want local file paths to become platform file type labels, so uploads declare each file using the correct remote type.

**Expected Behavior / Usage:**

The input is a local file path string. The final filename extension determines the output. `.gs`, `.GS`, `.js`, and `.JS` map to `SERVER_JS`; other tested extensions are uppercased. For a compound name, only the final extension is used. The output is a single `remote_type` line.

**Test Cases:** `rcb_tests/public_test_cases/feature4_remote_file_type.json`

```json
{
    "description": "Convert a local file path into the remote file type label by reading the final filename extension; JavaScript and server-script extensions map to the server-side script label, while other extensions become uppercase labels.",
    "cases": [
        {
            "input": "file.GS",
            "expected_output": "remote_type=SERVER_JS\n"
        },
        {
            "input": "file.JS",
            "expected_output": "remote_type=SERVER_JS\n"
        },
        {
            "input": "file.js",
            "expected_output": "remote_type=SERVER_JS\n"
        },
        {
            "input": "file.jsx",
            "expected_output": "remote_type=JSX\n"
        },
        {
            "input": "file.js.html",
            "expected_output": "remote_type=HTML\n"
        }
    ]
}
```

---

### Feature 5: Project Identifier Persistence

**As a developer**, I want a script project identifier to be saved in the local project settings file, so subsequent commands can find the project without asking again.

**Expected Behavior / Usage:**

The input is a script project identifier string. The system writes a compact JSON project settings document containing that identifier under the `scriptId` key. The adapter reports the exact saved JSON on a `saved_json` line.

**Test Cases:** `rcb_tests/public_test_cases/feature5_project_id_persistence.json`

```json
{
    "description": "Persist a script project identifier in the project settings file as a compact JSON object containing that identifier.",
    "cases": [
        {
            "input": "12345",
            "expected_output": "saved_json={\"scriptId\":\"12345\"}\n"
        }
    ]
}
```

---

### Feature 6: API Catalog Listing

**As a developer**, I want to list available platform APIs in a stable row format, so I can inspect service names and versioned identifiers from the command line.

**Expected Behavior / Usage:**

The input is the command-line argument sequence for listing APIs. The executable must exit successfully. Each returned API row contains a short API name, aligned spacing, a hyphen separator, and a versioned API identifier. The adapter emits the exit code and one `api` line per observed row.

**Test Cases:** `rcb_tests/public_test_cases/feature6_api_catalog_listing.json`

```json
{
    "description": "List available platform APIs as aligned rows containing the short API name, a separator, and the versioned API identifier.",
    "cases": [
        {
            "input": [
                "apis",
                "list"
            ],
            "expected_output": "exit_code=0\n[two specific API rows with exact separator and spacing]\n[two specific API rows with exact separator and spacing]\n"
        }
    ]
}
```

---

### Feature 7: API Enable/Disable Placeholder Responses

**As a developer**, I want not-yet-implemented API mutation commands to return a clear placeholder response, so scripts can distinguish recognized commands from unsupported ones.

**Expected Behavior / Usage:**

The input is a command-line argument sequence for either enabling or disabling APIs. For the tested recognized mutation subcommands, the executable exits successfully and prints the development-placeholder message. The adapter emits the exit code, the requested subcommand, and the message.

**Test Cases:** `rcb_tests/public_test_cases/feature7_api_mutation_placeholders.json`

```json
{
    "description": "For API enablement and disablement requests that are not implemented yet, report a successful command result with the development-placeholder message.",
    "cases": [
        {
            "input": [
                "apis",
                "enable"
            ],
            "expected_output": "exit_code=0\nsubcommand=enable\nmessage=In development...\n"
        },
        {
            "input": [
                "apis",
                "disable"
            ],
            "expected_output": "exit_code=0\nsubcommand=disable\nmessage=In development...\n"
        }
    ]
}
```

---

### Feature 8: Unknown API Subcommand Handling

**As a developer**, I want unsupported API-management subcommands to fail with a clear command error, so invalid automation is not mistaken for a successful no-op.

**Expected Behavior / Usage:**

The input is a command-line argument sequence for an unsupported API-management subcommand. The executable must return a nonzero exit code. The adapter normalizes the error to language-neutral stdout lines containing `error=unknown_command`, the rejected command path, and the command users can run for help; it must not expose host-language exception class names or runtime stack formatting.

**Test Cases:** `rcb_tests/public_test_cases/feature8_unknown_api_subcommand.json`

```json
{
    "description": "Reject an unsupported API-management subcommand with a nonzero exit code, the normalized unknown-command category, the rejected command path, and the command users can run for help.",
    "cases": [
        {
            "input": [
                "apis",
                "unknown"
            ],
            "expected_output": "exit_code=1\nerror=unknown_command\ncommand=apis unknown\nhelp_command=clasp --help\n"
        }
    ]
}
```

---

### Feature 9: Credential Cleanup on Logout

**As a developer**, I want logout to remove stored credential files from both local and home locations, so future commands do not accidentally reuse stale credentials.

**Expected Behavior / Usage:**

The input supplies credential-file contents to place in both the project-local credential location and the user-home credential location before logout. After logout runs, neither credential location should exist. The adapter reports the post-logout existence of both locations as boolean text fields; these fields describe filesystem state, not a pass/fail status.

**Test Cases:** `rcb_tests/public_test_cases/feature9_logout_credentials_cleanup.json`

```json
{
    "description": "Remove both project-local and user-home credential files during logout, leaving neither credential location present afterward.",
    "cases": [
        {
            "input": {
                "local_credentials": "{\"timeZone\": \"America/New_York\"}",
                "home_credentials": "{\"timeZone\": \"America/New_York\"}"
            },
            "expected_output": "[post-logout existence state of credential paths]\n[post-logout existence state of credential paths]\n"
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
- uses the URL generation logic consistent with the Slot Editor component codebase
- adheres to the same column spacing convention used in the `report_list` printed API array
