## Product Requirement Document

# Command-Line Function Adapter - Declarative CLI Assembly and Dispatch

## Project Goal

Build a lightweight command-line assembly and dispatch library that allows developers to expose ordinary application callables as structured CLI commands without writing repetitive parser glue code.

---

## Background & Problem

Without this library/tool, developers are forced to manually define parser objects, wire command names, map positional and optional arguments, format command output, and handle user-facing command failures. This leads to repetitive code, inconsistent command behavior, and fragile error handling across small command-line applications.

With this library/tool, developers describe command behavior through callable signatures and small metadata declarations, then rely on a dispatcher to parse command-line input, invoke the selected command, and render predictable stdout-oriented results.

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

### Feature 1: Default command options

**As a developer**, I want to run a single callable as the default command with optional values, so I can invoke simple tools without writing parser boilerplate.

**Expected Behavior / Usage:**

The adapter input contains a neutral setup identifier and an `argv` command-line string. For this feature, an empty command line uses the configured numeric default and an explicit long option overrides it. The output is the command result followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_default_command_options.json`

```json
{
    "description": "A default command accepts an omitted optional value or an explicit option value.",
    "cases": [
        {
            "input": {
                "scenario": "default_optional_number",
                "argv": ""
            },
            "expected_output": "1[a context-dependent trailing newline literal]"
        }
    ]
}
```

---

### Feature 2: Required positional arguments

**As a developer**, I want to declare positional data that must be provided, so I can get clear invocation contracts for required inputs.

**Expected Behavior / Usage:**

The adapter input contains a setup identifier and an `argv` command-line string. The command requires one positional token; when present, that token is printed with a trailing newline. When omitted, stdout is a normalized usage error with `error=missing_required` and the missing argument name.

**Test Cases:** `rcb_tests/public_test_cases/feature2_required_positional_arguments.json`

```json
{
    "description": "A required positional argument is emitted when present and reports a neutral missing-argument error when absent.",
    "cases": [
        {
            "input": {
                "scenario": "positional_required",
                "argv": "foo"
            },
            "expected_output": "foo[a context-dependent trailing newline literal]"
        }
    ]
}
```

---

### Feature 3: Optional values with defaults

**As a developer**, I want to expose a parameter as an optional command-line value, so I can let callers rely on defaults or override them explicitly.

**Expected Behavior / Usage:**

The adapter input contains a setup identifier and an `argv` command-line string. With no argument, the configured text default is printed. With the named option, the supplied option value is printed. A stray positional token is rejected as `error=unrecognized_arguments` with the raw unrecognized text on a separate line.

**Test Cases:** `rcb_tests/public_test_cases/feature3_optional_defaults.json`

```json
{
    "description": "An optional parameter uses its default value when omitted, accepts a named override, and rejects unexpected positional text.",
    "cases": [
        {
            "input": {
                "scenario": "optional_default_text",
                "argv": ""
            },
            "expected_output": "foo[a context-dependent trailing newline literal]"
        },
        {
            "input": {
                "scenario": "optional_default_text",
                "argv": "--x bar"
            },
            "expected_output": "bar[a context-dependent trailing newline literal]"
        }
    ]
}
```

---

### Feature 4: Variable-length positional lists

**As a developer**, I want to accept any number of trailing positional tokens, so I can support commands that work on zero, one, or many items.

**Expected Behavior / Usage:**

The adapter input contains a setup identifier and an `argv` command-line string. All positional tokens are collected in order and rendered as a comma-and-space separated line. Supplying no tokens renders an empty line.

**Test Cases:** `rcb_tests/public_test_cases/feature4_variadic_positionals.json`

```json
{
    "description": "A variable-length positional list accepts zero, one, or several tokens and passes them to the command in order.",
    "cases": [
        {
            "input": {
                "scenario": "variadic_paths",
                "argv": ""
            },
            "expected_output": "[a context-dependent trailing newline literal]"
        },
        {
            "input": {
                "scenario": "variadic_paths",
                "argv": "foo"
            },
            "expected_output": "foo[a context-dependent trailing newline literal]"
        }
    ]
}
```

---

### Feature 5: Named argument capture

**As a developer**, I want to combine declared positional and optional values into named command inputs, so I can write commands that consume flexible named data.

**Expected Behavior / Usage:**

The adapter input contains a setup identifier and an `argv` command-line string. A required positional value and an optional named value are passed to command code as named entries. Output lists the captured entries in sorted key order, one `name: value` line per entry. If the positional value is absent, stdout is a normalized missing-required error.

**Test Cases:** `rcb_tests/public_test_cases/feature5_keyword_capture.json`

```json
{
    "description": "Explicit positional and optional arguments can be captured as named values and exposed to command code.",
    "cases": [
        {
            "input": {
                "scenario": "keyword_capture",
                "argv": "hello"
            },
            "expected_output": "bar: None[a context-dependent trailing newline literal]foo: hello[a context-dependent trailing newline literal]"
        },
        {
            "input": {
                "scenario": "keyword_capture",
                "argv": "hello --bar 123"
            },
            "expected_output": "bar: 123[a context-dependent trailing newline literal]foo: hello[a context-dependent trailing newline literal]"
        }
    ]
}
```

---

### Feature 6: Return-value rendering modes

**As a developer**, I want to render structured command results consistently, so I can control whether helper formatting is applied.

**Expected Behavior / Usage:**

The adapter input contains a setup identifier, an `argv` command-line string, and optionally `raw_output`. By default, a multi-item command result is printed one item per line with a final newline. When raw output is requested, returned items are written directly without inserted separators or trailing formatting.

**Test Cases:** `rcb_tests/public_test_cases/feature6_output_rendering_modes.json`

```json
{
    "description": "Structured return values are rendered one item per line by default, while raw rendering concatenates returned items without inserted separators.",
    "cases": [
        {
            "input": {
                "scenario": "ordered_positionals",
                "argv": "foo bar"
            },
            "expected_output": "foo[a context-dependent trailing newline literal]bar[a context-dependent trailing newline literal]"
        }
    ]
}
```

---

### Feature 7: Keyword-only options

**As a developer**, I want to support required and optional named options together with free positional tokens, so I can model modern command signatures accurately.

**Expected Behavior / Usage:**

The adapter input contains a setup identifier and an `argv` command-line string. Free positional tokens are preserved in order, optional named values use defaults when omitted, and a required named value must be present. Successful output lists the joined positional text and resolved option values on separate lines. Missing required named options are normalized as `error=missing_required`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_keyword_only_arguments.json`

```json
{
    "description": "Keyword-only options can be required or optional while extra positional tokens remain available to the command.",
    "cases": [
        {
            "input": {
                "scenario": "keyword_only",
                "argv": "--baz=done test this --bar=do"
            },
            "expected_output": "test this[a context-dependent trailing newline literal]1[a context-dependent trailing newline literal]do[a context-dependent trailing newline literal]done[a context-dependent trailing newline literal]0[a context-dependent trailing newline literal]"
        }
    ]
}
```

---

### Feature 8: Subcommand routing

**As a developer**, I want to select a command by the first command-line token, so I can build multi-action command-line programs.

**Expected Behavior / Usage:**

The adapter input contains a setup identifier and an `argv` command-line string. The first token selects the command, and remaining tokens are parsed according to that selected command. A successful command prints its result. If the selected command lacks a required argument, stdout reports a normalized missing-required error.

**Test Cases:** `rcb_tests/public_test_cases/feature8_subcommand_routing.json`

```json
{
    "description": "A named subcommand is selected from the first command token and receives its remaining command-line arguments.",
    "cases": [
        {
            "input": {
                "scenario": "simple_subcommand",
                "argv": "echo foo"
            },
            "expected_output": "you said foo[a context-dependent trailing newline literal]"
        }
    ]
}
```

---

### Feature 9: Boolean flags

**As a developer**, I want to infer flag behavior for false-by-default boolean options, so I can let callers toggle behavior with presence-only flags.

**Expected Behavior / Usage:**

The adapter input contains a setup identifier and an `argv` command-line string. Without the boolean flag, the command receives the false default and prints the default-result text. With the flag present, the command receives true and prints the alternate-result text.

**Test Cases:** `rcb_tests/public_test_cases/feature9_boolean_flags.json`

```json
{
    "description": "Boolean options inferred from false defaults are disabled by default and become enabled when their flag is present.",
    "cases": [
        {
            "input": {
                "scenario": "boolean_subcommand",
                "argv": "parrot"
            },
            "expected_output": "beautiful plumage[a context-dependent trailing newline literal]"
        }
    ]
}
```

---

### Feature 10: Namespaced command groups

**As a developer**, I want to group related subcommands under a namespace token, so I can organize larger command-line surfaces without losing per-command parsing.

**Expected Behavior / Usage:**

The adapter input contains a setup identifier and an `argv` command-line string. The first token selects a namespace, the next token selects a command inside that namespace, and remaining tokens are parsed by that leaf command. Outputs must reflect the selected leaf command. Invalid leftover tokens are reported as normalized unrecognized arguments.

**Test Cases:** `rcb_tests/public_test_cases/feature10_namespaced_commands.json`

```json
{
    "description": "A namespace token can group multiple subcommands, with each leaf command keeping its own argument contract.",
    "cases": [
        {
            "input": {
                "scenario": "namespaced_greeting",
                "argv": "greet hello"
            },
            "expected_output": "Hello world![a context-dependent trailing newline literal]"
        },
        {
            "input": {
                "scenario": "namespaced_greeting",
                "argv": "greet hello --name=John"
            },
            "expected_output": "Hello John![a context-dependent trailing newline literal]"
        }
    ]
}
```

---

### Feature 11: Custom public command names

**As a developer**, I want to publish a command under an explicit public name, so I can decouple external command names from implementation names.

**Expected Behavior / Usage:**

The adapter input contains a setup identifier and an `argv` command-line string. The configured public command name invokes the command and prints its result. The non-public inferred name is not accepted and produces `error=invalid_choice` with the rejected command token.

**Test Cases:** `rcb_tests/public_test_cases/feature11_custom_command_names.json`

```json
{
    "description": "A command may expose an explicit public command name instead of the name inferred from the underlying callable.",
    "cases": [
        {
            "input": {
                "scenario": "explicit_command_name",
                "argv": "new-name"
            },
            "expected_output": "ok[a context-dependent trailing newline literal]"
        }
    ]
}
```

---

### Feature 12: Command aliases

**As a developer**, I want to make one command reachable through multiple public tokens, so I can support backward-compatible or convenient command names.

**Expected Behavior / Usage:**

The adapter input contains a setup identifier and an `argv` command-line string. The primary command token and each configured alias route to the same command and therefore produce identical command output.

**Test Cases:** `rcb_tests/public_test_cases/feature12_command_aliases.json`

```json
{
    "description": "A command may be reachable through its primary public name and additional aliases.",
    "cases": [
        {
            "input": {
                "scenario": "aliased_command",
                "argv": "alias1"
            },
            "expected_output": "ok[a context-dependent trailing newline literal]"
        },
        {
            "input": {
                "scenario": "aliased_command",
                "argv": "alias2"
            },
            "expected_output": "ok[a context-dependent trailing newline literal]"
        }
    ]
}
```

---

### Feature 13: Generated command output

**As a developer**, I want to render values produced incrementally by a command, so I can stream command results in a predictable line-oriented form.

**Expected Behavior / Usage:**

The adapter input contains a setup identifier and an `argv` command-line string. Each value produced by the command is rendered to stdout as its own line in production order.

**Test Cases:** `rcb_tests/public_test_cases/feature13_generated_output.json`

```json
{
    "description": "Commands that yield values produce each yielded value as a separate output line.",
    "cases": [
        {
            "input": {
                "scenario": "generated_output",
                "argv": ""
            },
            "expected_output": "1[a context-dependent trailing newline literal]"
        }
    ]
}
```

---

### Feature 14: Domain command errors

**As a developer**, I want to render application-level command failures as structured neutral output, so I can report failures without leaking runtime-specific exception classes.

**Expected Behavior / Usage:**

The adapter input contains a setup identifier and an `argv` command-line string. When command code raises a domain command failure, stdout contains `error=command_error` and a separate `message` line. If the command produced output before the failure, that already-produced output remains before the normalized error record.

**Test Cases:** `rcb_tests/public_test_cases/feature14_command_error_output.json`

```json
{
    "description": "Domain command failures are reported as neutral error records while preserving any output emitted before the failure.",
    "cases": [
        {
            "input": {
                "scenario": "command_error",
                "argv": "whiner-plain"
            },
            "expected_output": "error=command_error[a context-dependent trailing newline literal]message=I feel depressed.[a context-dependent trailing newline literal]"
        }
    ]
}
```

---

### Feature 15: Wrapped application failures

**As a developer**, I want to convert configured application failures into neutral command errors, so I can hide host-language exception names from black-box output.

**Expected Behavior / Usage:**

The adapter input contains a setup identifier and an `argv` command-line string. A successful invocation prints the normal command result. A configured application failure is caught by the adapter layer and rendered as `error=wrapped_command_error` plus the domain message, with no host-language exception class name in stdout.

**Test Cases:** `rcb_tests/public_test_cases/feature15_wrapped_failures.json`

```json
{
    "description": "Configured application exceptions are caught and rendered as neutral wrapped-error records instead of propagating runtime-specific exception names.",
    "cases": [
        {
            "input": {
                "scenario": "wrapped_failure",
                "argv": ""
            },
            "expected_output": "beautiful plumage[a context-dependent trailing newline literal]"
        }
    ]
}
```

---

### Feature 16: Inferred option behavior

**As a developer**, I want to infer option conversion and flag behavior from defaults, so I can avoid redundant option declarations for common cases.

**Expected Behavior / Usage:**

The adapter input contains a setup identifier and an `argv` command-line string. Numeric defaults cause supplied option text to be converted before command execution, so the command can compare numbers. Boolean false defaults create presence-only flags that switch the value to true.

**Test Cases:** `rcb_tests/public_test_cases/feature16_inferred_argument_types.json`

```json
{
    "description": "Defaults infer command-line conversion for numeric options and flag behavior for boolean options.",
    "cases": [
        {
            "input": {
                "scenario": "inferred_numeric_and_bool",
                "argv": "grenade"
            },
            "expected_output": "Three shall be the number thou shalt count[a context-dependent trailing newline literal]"
        },
        {
            "input": {
                "scenario": "inferred_numeric_and_bool",
                "argv": "grenade --count 5"
            },
            "expected_output": "5 is right out[a context-dependent trailing newline literal]"
        }
    ]
}
```

---

### Feature 17: Distinct similar option names

**As a developer**, I want to expose similar parameter names as separate long options, so I can avoid ambiguous short-option inference.

**Expected Behavior / Usage:**

The adapter input contains a setup identifier and an `argv` command-line string. Similar option names remain distinct long options; each updates only its corresponding value. A shared short option is not accepted and is rendered as a normalized unrecognized-arguments error.

**Test Cases:** `rcb_tests/public_test_cases/feature17_distinct_long_options.json`

```json
{
    "description": "Similar argument names are exposed as distinct long options rather than an ambiguous shared short option.",
    "cases": [
        {
            "input": {
                "scenario": "distinct_long_options",
                "argv": ""
            },
            "expected_output": "foo 1, fox 2[a context-dependent trailing newline literal]"
        },
        {
            "input": {
                "scenario": "distinct_long_options",
                "argv": "--foo 3"
            },
            "expected_output": "foo 3, fox 2[a context-dependent trailing newline literal]"
        }
    ]
}
```

---

### Feature 18: Counting options

**As a developer**, I want to count repeated flag occurrences, so I can support verbosity-style command-line controls.

**Expected Behavior / Usage:**

The adapter input contains a setup identifier and an `argv` command-line string. The counting option starts at its configured default and increments once for each occurrence, including compact repeated flag syntax.

**Test Cases:** `rcb_tests/public_test_cases/feature18_counting_options.json`

```json
{
    "description": "A counting option starts at its default count and increments once for each repeated flag occurrence.",
    "cases": [
        {
            "input": {
                "scenario": "count_option",
                "argv": ""
            },
            "expected_output": "0[a context-dependent trailing newline literal]"
        },
        {
            "input": {
                "scenario": "count_option",
                "argv": "-v"
            },
            "expected_output": "1[a context-dependent trailing newline literal]"
        }
    ]
}
```

---

### Feature 19: Dashed option names

**As a developer**, I want to map underscored internal parameter names to dashed command-line names, so I can provide conventional command-line spelling while preserving named values.

**Expected Behavior / Usage:**

The adapter input contains a setup identifier and an `argv` command-line string. Required positional values are accepted in order, and dashed option names are mapped back to their corresponding named inputs before command execution. The output lists the resolved values and any extra captured named values.

**Test Cases:** `rcb_tests/public_test_cases/feature19_dashed_option_names.json`

```json
{
    "description": "Underscored parameter names are exposed as dashed command-line names and mapped back before command execution.",
    "cases": [
        {
            "input": {
                "scenario": "underscore_names",
                "argv": "abc def --baz-baz 8"
            },
            "expected_output": "abc[a context-dependent trailing newline literal]def[a context-dependent trailing newline literal]8[a context-dependent trailing newline literal]9[a context-dependent trailing newline literal]{}[a context-dependent trailing newline literal]"
        }
    ]
}
```

---

### Feature 20: Generated help text

**As a developer**, I want to include defaults and explicit help snippets in generated usage text, so I can make command help informative without hand-written duplication.

**Expected Behavior / Usage:**

The adapter input contains a setup identifier. Generated help text must include default values from positional and optional arguments, default values inferred from the command signature, and explicit help text. The adapter renders each verified visible snippet as `help_snippet=<text>`.

**Test Cases:** `rcb_tests/public_test_cases/feature20_help_default_text.json`

```json
{
    "description": "Generated help includes default values and explicit help snippets for positional and optional arguments.",
    "cases": [
        {
            "input": {
                "scenario": "help_defaults",
                "argv": ""
            },
            "expected_output": "help_snippet=Basil[a context-dependent trailing newline literal]help_snippet=Moose[a context-dependent trailing newline literal]help_snippet=creatures[a context-dependent trailing newline literal]help_snippet=remarkable animal[a context-dependent trailing newline literal]help_snippet=it can speak[a context-dependent trailing newline literal]"
        }
    ]
}
```

---

### Feature 21: Confirmation prompts

**As a developer**, I want to ask a yes/no question with default-aware prompt text, so I can collect simple interactive decisions consistently.

**Expected Behavior / Usage:**

The adapter input contains a prompt string, a reply string, and a default value or an omitted-default marker. Prompt text ends with choice hints: `(y/n)` with no default, `(Y/n)` for a yes default, and `(y/N)` for a no default. Empty replies use the default when present; `y` maps to `result=yes`, `n` maps to `result=no`, and other replies map to `result=unknown`.

**Test Cases:** `rcb_tests/public_test_cases/feature21_confirmation_prompts.json`

```json
{
    "description": "A confirmation prompt formats the available choices from the default value and maps replies to yes, no, or unknown.",
    "cases": [
        {
            "input": {
                "scenario": "confirmation",
                "prompt": "do smth",
                "reply": "",
                "default": "omitted"
            },
            "expected_output": "prompt=do smth? (y/n)[a context-dependent trailing newline literal]result=unknown[a context-dependent trailing newline literal]"
        },
        {
            "input": {
                "scenario": "confirmation",
                "prompt": "do smth",
                "reply": "",
                "default": true
            },
            "expected_output": "prompt=do smth? (Y/n)[a context-dependent trailing newline literal]result=yes[a context-dependent trailing newline literal]"
        },
        {
            "input": {
                "scenario": "confirmation",
                "prompt": "do smth",
                "reply": "",
                "default": false
            },
            "expected_output": "prompt=do smth? (y/N)[a context-dependent trailing newline literal]result=no[a context-dependent trailing newline literal]"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_default_command_options.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_default_command_options@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- output the error domain format as defined in the previous step
- apply standard interactive prompt formatting rules
