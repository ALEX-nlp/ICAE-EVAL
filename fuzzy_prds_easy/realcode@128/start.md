## Product Requirement Document

# Managed-to-Script Library Publisher - Build-Time Interop Packaging and Call Bridging

## Project Goal

Build a managed-code-to-script interop toolkit that allows developers to expose compiled application functions through a browser-friendly script package and call global script functions from managed code without manually writing repetitive bridge, boot, and type declaration glue.

---

## Background & Problem

Without this library/tool, developers are forced to hand-maintain runtime boot wrappers, script-call forwarding functions, generated source stubs, and declaration files that mirror compiled application assemblies. This leads to duplicated boilerplate, fragile naming conventions, incorrect async bindings, and mismatched type information between managed code and script consumers.

With this library/tool, a developer can mark which managed functions participate in script interop, publish a single browser library with boot data and bindings, and optionally emit declaration files that describe the generated script surface.

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

### Feature 1: Runtime Script Calls

**As a developer**, I want to configure and replace the runtime used for script calls, so I can control serialization and route invocations through the host environment.

**Expected Behavior / Usage:**

*1.1 Runtime JSON Configuration — Apply serializer options consistently to both outbound and inbound runtime processing.*

The input describes a runtime JSON number-output mode. When numbers are requested as strings, the runtime must apply that setting to both outbound calls and inbound calls. The output reports the effective outbound and inbound number-output settings as separate lines.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_runtime_configuration.json`

```json
{
    "description": "Configuring number serialization applies the same option to outbound and inbound JSON processing.",
    "cases": [
        {
            "input": {
                "json_number_output": "numbers_as_strings"
            },
            "expected_output": "[the specific valid string literal for the number format writer — verify against the schema registry]\n[the specific valid string literal for the number format writer — verify against the schema registry]\n"
        }
    ]
}
```

*1.2 Runtime Invocation Routing — Forward all call forms through the configured runtime.*

The input names a global script function and lists call forms to execute. Each synchronous or asynchronous call must be delegated to the configured runtime with the same identifier. If the runtime reports that the operation is unavailable, stdout must normalize the failure as `error=runtime_call_not_implemented` while still showing the requested call form, forwarded identifier, and runtime call channel.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_runtime_routing.json`

```json
{
    "description": "Synchronous and asynchronous global calls are forwarded through the configured runtime with the requested identifier and normalized errors.",
    "cases": [
        {
            "input": {
                "function_name": "demo.echo",
                "calls": [
                    "sync_without_result",
                    "sync_with_result",
                    "async_with_result",
                    "async_without_result"
                ]
            },
            "expected_output": "call=sync_without_result\nruntime_identifier=demo.echo\nruntime_call=sync\nerror=runtime_call_not_implemented\ncall=sync_with_result\nruntime_identifier=demo.echo\nruntime_call=sync\nerror=runtime_call_not_implemented\ncall=async_with_result\nruntime_identifier=demo.echo\nruntime_call=async\nerror=runtime_call_not_implemented\ncall=async_without_result\nruntime_identifier=demo.echo\nruntime_call=async\nerror=runtime_call_not_implemented\n"
        }
    ]
}
```

---

### Feature 2: Source Stub Generation

**As a developer**, I want marked partial declarations to be completed automatically, so I can call global script functions without writing repetitive forwarding bodies.

**Expected Behavior / Usage:**

*2.1 Partial Function Generation — Generate forwarding bodies for marked partial declarations.*

The input is a source snippet. If the snippet has no marked partial function declarations, the output is empty. For each marked partial declaration, the generated source must preserve the surrounding type and namespace shape, preserve the original declaration signature, build a global script identifier from the assembly name and function name, choose the proper synchronous or asynchronous invocation form from the return type, and pass declared parameters in order. The output is the generated source text exactly as produced by the generator.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_partial_function_generation.json`

```json
{
    "description": "Marked partial declarations are completed by generated forwarding bodies that call the corresponding global script identifier and pass declared parameters in order.",
    "cases": [
        {
            "input": {
                "source": ""
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 3: Publishing Script Packages

**As a developer**, I want a publishing task that inspects compiled assemblies and writes browser assets, so I can distribute a single script package with runtime boot data, callable bindings, and optional declarations.

**Expected Behavior / Usage:**

*3.1 Publish Artifacts — Write the main script library and honor optional outputs and cleaning behavior.*

The input describes whether to emit a source map, emit type declarations, clean the base directory, and whether a preexisting base file is present. Publishing must always write the main script library, omit source maps and declarations unless requested, remove preexisting base files when cleaning is enabled, preserve them when cleaning is disabled, and report publication results as boolean lines.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_publish_artifacts.json`

```json
{
    "description": "Publishing writes the boot library, optionally writes source maps and type definitions, controls base-directory cleaning, and reports inspection warnings without aborting.",
    "cases": [
        {
            "input": {
                "assemblies": []
            },
            "expected_output": "library_published=true\nmap_published=false\ntypes_published=false\npreexisting_base_file_exists=false\nwarnings=0\n"
        },
        {
            "input": {
                "emit_map": true,
                "assemblies": []
            },
            "expected_output": "library_published=true\nmap_published=true\ntypes_published=false\npreexisting_base_file_exists=false\nwarnings=0\n"
        },
        {
            "input": {
                "clean": false,
                "preexisting_base_file": true,
                "assemblies": []
            },
            "expected_output": "library_published=true\nmap_published=false\ntypes_published=false\npreexisting_base_file_exists=true\nwarnings=0\n"
        }
    ]
}
```

*3.2 Library Bindings — Generate nested assembly objects and script bindings.*

The input supplies compiled assembly names, exported member declarations, and probe strings. Publishing must include runtime script content, create one exported object hierarchy per dot-separated assembly name, avoid redeclaring a shared root object more than once, expose host-callable methods as functions that call the runtime invocation entry point, expose script-supplied functions as undefined slots to be assigned later, rename script-reserved parameter names where needed, and use the asynchronous invocation entry point for awaitable methods. The output reports whether each probe string is present in the generated library.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_library_bindings.json`

```json
{
    "description": "The emitted browser library declares nested assembly objects and exposes method bindings according to imported and exported script directions.",
    "cases": [
        {
            "input": {
                "assemblies": [
                    {
                        "name": "foo.bar.nya.dll",
                        "members": [
                            "[JSInvokable] public static void Bar () { }"
                        ]
                    }
                ],
                "probes": [
                    "exports.foo = {};",
                    "exports.foo.bar = {};",
                    "exports.foo.bar.nya = {};",
                    "exports.foo.bar.nya.Bar = () => exports.invoke('foo.bar.nya', 'Bar');"
                ]
            },
            "expected_output": "contains=exports.foo = {};\nvalue=true\ncontains=exports.foo.bar = {};\nvalue=true\ncontains=exports.foo.bar.nya = {};\nvalue=true\ncontains=exports.foo.bar.nya.Bar = () => exports.invoke('foo.bar.nya', 'Bar');\nvalue=true\n"
        },
        {
            "input": {
                "assemblies": [
                    {
                        "name": "foo.dll",
                        "members": [
                            "[JSInvokable] public static void Foo () { }"
                        ]
                    },
                    {
                        "name": "bar.nya.dll",
                        "members": [
                            "[JSFunction] public static void Fun () { }"
                        ]
                    }
                ],
                "probes": [
                    "exports.foo.Foo = () => exports.invoke('foo', 'Foo');",
                    "exports.bar.nya.Fun = undefined;"
                ]
            },
            "expected_output": "contains=exports.foo.Foo = () => exports.invoke('foo', 'Foo');\nvalue=true\ncontains=exports.bar.nya.Fun = undefined;\nvalue=true\n"
        }
    ]
}
```

*3.3 Type Definitions — Generate declaration bundles for runtime APIs and exported bindings.*

The input describes declaration resources, compiled assemblies, and probe strings. Publishing with declarations enabled must include only supported runtime declaration resources, inline supported imports, exclude unrelated declaration files, declare nested assembly-shaped APIs, map numeric types to `number`, booleans to `boolean`, characters and strings to `string`, date-time values to `Date`, awaitable results to `Promise<...>`, and unknown object types to `any`. If a required supported declaration import cannot be resolved, stdout must normalize the failure as `error=type_import_missing`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_type_definitions.json`

```json
{
    "description": "The emitted type declaration bundle includes only allowed runtime definitions, declares assembly-shaped APIs, maps host types to script types, and reports missing imports with a neutral error.",
    "cases": [
        {
            "input": {
                "assemblies": [],
                "probes": [
                    "export interface Interop {}",
                    "export interface Boot {}",
                    "import from",
                    "other"
                ]
            },
            "expected_output": "contains=export interface Interop {}\nvalue=true\ncontains=export interface Boot {}\nvalue=true\ncontains=import from\nvalue=false\ncontains=other\nvalue=false\n"
        },
        {
            "input": {
                "assemblies": [
                    {
                        "name": "bar.nya.dll",
                        "members": [
                            "[JSFunction] public static void Fun () { }"
                        ]
                    },
                    {
                        "name": "foo.dll",
                        "members": [
                            "[JSInvokable] public static void Foo () { }"
                        ]
                    }
                ],
                "probes": [
                    "export declare const bar: { nya: {\n    Fun: () => void,\n}};",
                    "export declare const foo: {\n    Foo: () => void,\n};"
                ]
            },
            "expected_output": "contains=export declare const bar: { nya: {\n    Fun: () => void,\n}};\nvalue=true\ncontains=export declare const foo: {\n    Foo: () => void,\n};\nvalue=true\n"
        },
        {
            "input": {
                "assemblies": [
                    {
                        "name": "test.dll",
                        "members": [
                            "[JSInvokable] public static Task<bool> AsyBool () => default;",
                            "[JSInvokable] public static ValueTask AsyVoid () => default;"
                        ]
                    }
                ],
                "probes": [
                    "AsyBool: () => Promise<boolean>",
                    "AsyVoid: () => Promise<void>"
                ]
            },
            "expected_output": "contains=AsyBool: () => Promise<boolean>\nvalue=true\ncontains=AsyVoid: () => Promise<void>\nvalue=true\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_runtime_configuration.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_runtime_configuration@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same semantic grouping as the network layer configuration
