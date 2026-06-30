## Product Requirement Document

# Native Runtime Bridge Contract - JavaScript Value Interoperability Adapter

## Project Goal

Build a native runtime bridge that allows developers to create, inspect, transform, and exchange JavaScript-visible values from native code without hand-writing unsafe boundary glue for every primitive, object, function, buffer, error, or asynchronous result.

---

## Background & Problem

Without this library/tool, developers are forced to manually encode native values into JavaScript-compatible representations, manage object lifetimes, handle callback invocation, and translate failures at the boundary. This leads to repetitive boilerplate, inconsistent type handling, memory-safety risks, and hard-to-debug runtime failures.

With this library/tool, native modules can expose values and operations through a predictable adapter contract: JSON commands enter through stdin for testing, native behavior is invoked through the execution adapter, and stdout records only the externally observable result.

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

### Feature 1: Module Export Values

**As a developer**, I want module initialization to expose stable primitives, numbers, objects, and callable behavior, so I can rely on exported values immediately after loading the native bridge.

**Expected Behavior / Usage:**

The adapter accepts an object selecting the module-export scenario. It prints key-value lines for the exported greeting text, primitive sentinels, numeric constants, created object properties, or a one-argument increment call. Undefined and null are rendered as neutral literal values.

**Test Cases:** `rcb_tests/public_test_cases/feature1_module_exports.json`

```json
{
    "description": "Values exported at module initialization are visible with the expected primitive, number, object, and callable behavior.",
    "cases": [
        {
            "input": {
                "operation": "module_exports",
                "scenario": "greeting_text"
            },
            "expected_output": "greeting=Hello, World!\ncopy=Hello, World!\nsame=true\n"
        },
        {
            "input": {
                "operation": "module_exports",
                "scenario": "primitive_singletons"
            },
            "expected_output": "undefined=undefined\nhas_undefined_property=true\nnull=null\ntrue=true\nfalse=false\n"
        }
    ]
}
```

---

### Feature 2: Number Creation and Round Trip

**As a developer**, I want numeric values to cross the native boundary predictably, so I can preserve integers, large numbers, floating point values, and negative values.

**Expected Behavior / Usage:**

The adapter accepts a numeric scenario and optional numeric value. It prints the input and result for round trips, or prints the generated numeric constants. Values beyond the exactly representable integer range are reported as the runtime-observable number value.

**Test Cases:** `rcb_tests/public_test_cases/feature2_numbers.json`

```json
{
    "description": "Numeric values crossing the native boundary preserve integer, large integer, floating point, and negative-number behavior as observed by callers.",
    "cases": [
        {
            "input": {
                "operation": "numbers",
                "scenario": "created_numbers"
            },
            "expected_output": "integer=9000\nlarge_integer=4294967296\nnegative_integer=-9000\nfloat=1.4747\nnegative_float=-1.4747\n"
        },
        {
            "input": {
                "operation": "numbers",
                "scenario": "round_trip",
                "value": 1
            },
            "expected_output": "input=1\nresult=1\n"
        }
    ]
}
```

---

### Feature 3: String Values and Script Evaluation

**As a developer**, I want strings to be returned and evaluated as source text, so I can use the bridge for dynamic value creation while receiving normalized failures.

**Expected Behavior / Usage:**

The adapter accepts a string scenario and, for evaluation, source text. Successful evaluation prints the source and result. Runtime throws print `error=script_exception` with a message line; parse failures print `error=script_syntax` without leaking runtime exception class names.

**Test Cases:** `rcb_tests/public_test_cases/feature3_string_scripts.json`

```json
{
    "description": "String values can be returned, evaluated as source text, and reported with normalized script error categories when evaluation fails.",
    "cases": [
        {
            "input": {
                "operation": "strings",
                "scenario": "created_string"
            },
            "expected_output": "[a specific string literal — verify with the setter documentation]\n"
        },
        {
            "input": {
                "operation": "strings",
                "scenario": "evaluate_script",
                "source": "6 * 7"
            },
            "expected_output": "source=6 * 7\nresult=42\n"
        }
    ]
}
```

---

### Feature 4: Array Creation and Reading

**As a developer**, I want arrays created and read through the bridge, so indexed values and empty-array behavior are observable.

**Expected Behavior / Usage:**

The adapter accepts an array scenario and optional array data. Created arrays print length and JSON item content. Reading prints the input array and the first value, using `undefined` when index zero is not present.

**Test Cases:** `rcb_tests/public_test_cases/feature4_arrays.json`

```json
{
    "description": "Array outputs preserve length and indexed content, and reading the first element returns either that value or an undefined sentinel for an empty array.",
    "cases": [
        {
            "input": {
                "operation": "arrays",
                "scenario": "created_empty"
            },
            "expected_output": "length=0\nitems=[]\n"
        },
        {
            "input": {
                "operation": "arrays",
                "scenario": "created_number"
            },
            "expected_output": "length=1\nitems=[9000]\n"
        }
    ]
}
```

---

### Feature 5: Object Creation, Metadata, and Method Dispatch

**As a developer**, I want object properties, object metadata, immutability operations, and receiver-based method calls to behave consistently across the boundary.

**Expected Behavior / Usage:**

The adapter accepts an object scenario. It prints JSON object content, mutation/deletion outcomes after freeze or seal, own property names excluding inherited and symbolic keys, and method-call results that prove the receiver object is used.

**Test Cases:** `rcb_tests/public_test_cases/feature5_objects.json`

```json
{
    "description": "Object outputs preserve own properties, object immutability operations affect later mutation/deletion attempts, own-property enumeration excludes inherited and symbolic keys, and method invocation uses the receiver object.",
    "cases": [
        {
            "input": {
                "operation": "objects",
                "scenario": "created_objects"
            },
            "expected_output": "empty={}\nnumber={\"number\":9000}\nstring={\"string\":\"hello node\"}\nmixed={\"number\":9000,\"string\":\"hello node\"}\n"
        },
        {
            "input": {
                "operation": "objects",
                "scenario": "freeze_prevents_mutation"
            },
            "expected_output": "before=1\nafter_assignment=1\nmutation_prevented=true\n"
        }
    ]
}
```

---

### Feature 6: Value Stringification

**As a developer**, I want arbitrary values converted to strings using observable host conversion rules, so adapter output matches caller-facing semantics.

**Expected Behavior / Usage:**

The adapter accepts a stringification scenario and prints the input kind plus the resulting string. Arrays, map-like objects, and plain objects retain their distinct string forms.

**Test Cases:** `rcb_tests/public_test_cases/feature6_value_stringification.json`

```json
{
    "description": "Values are converted to strings using the host value conversion semantics observable at the boundary.",
    "cases": [
        {
            "input": {
                "operation": "coercion",
                "scenario": "stringify_array"
            },
            "expected_output": "input_kind=array\nresult=1,2,3\n"
        }
    ]
}
```

---

### Feature 7: Runtime Type Predicates and Identity

**As a developer**, I want runtime predicates and identity comparison to classify values precisely, so native code can distinguish primitives, boxed values, binary memory, errors, and object references.

**Expected Behavior / Usage:**

The adapter accepts a predicate scenario and prints one line per checked sample. Outputs must distinguish arrays from array-like objects, buffers from array buffers, primitive values from boxed objects, error objects from strings, and same-reference identity from lookalike objects.

**Test Cases:** `rcb_tests/public_test_cases/feature7_type_predicates.json`

```json
{
    "description": "Runtime predicates report the observable kind of values, and strict identity comparison distinguishes equal primitives from distinct object references.",
    "cases": [
        {
            "input": {
                "operation": "types",
                "scenario": "array_predicate"
            },
            "expected_output": "empty_array=true\nconstructed_array=true\nnull=false\nnumber=false\narray_like_object=false\n"
        },
        {
            "input": {
                "operation": "types",
                "scenario": "binary_predicates"
            },
            "expected_output": "array_buffer=true\ndata_view=false\nuint8_array_as_array_buffer=false\nbyte_buffer=true\nuint8_array_as_buffer=true\narray_buffer_as_buffer=false\nuint32_array=true\nuint16_array_as_uint32=false\n"
        }
    ]
}
```

---

### Feature 8: Function Calls, Construction, Arguments, and Exception Capture

**As a developer**, I want functions to cross the boundary as callable and constructible values, so callbacks, arguments, receiver binding, and thrown values can be handled as data.

**Expected Behavior / Usage:**

The adapter accepts a function scenario and optional value. It prints callback results for different arities, construction results, argument counts and presence flags, normalized type mismatch output when a string is required, captured thrown values, and call-vs-construction detection.

**Test Cases:** `rcb_tests/public_test_cases/feature8_function_calls.json`

```json
{
    "description": "Functions crossing the boundary remain callable, receive the expected arguments and receiver, support construction, expose argument counts/presence, and can capture thrown values as data.",
    "cases": [
        {
            "input": {
                "operation": "functions",
                "scenario": "returned_incrementer",
                "value": 41
            },
            "expected_output": "input=41\nresult=42\n"
        },
        {
            "input": {
                "operation": "functions",
                "scenario": "callback_invocation"
            },
            "expected_output": "direct_call=17\nidiomatic_call=17\nzero_args=-Infinity\none_arg=1\ntwo_args=2\nthree_args=3\nfour_args=4\nheterogeneous=[1,\"hello\",true]\n"
        }
    ]
}
```

---

### Feature 9: Date Creation and Validation

**As a developer**, I want timestamp-based date values to be created and inspected, so valid and invalid date states are visible at the boundary.

**Expected Behavior / Usage:**

The adapter accepts a date scenario and optional millisecond timestamp. It prints UTC string output for created dates, validity flags, fixed timestamp extraction, or `NaN` plus an invalid flag for invalid date values.

**Test Cases:** `rcb_tests/public_test_cases/feature9_dates.json`

```json
{
    "description": "Date values can be created from millisecond timestamps, converted back to timestamps, and classified as valid or invalid with invalid values represented as NaN.",
    "cases": [
        {
            "input": {
                "operation": "dates",
                "scenario": "create_from_millis",
                "millis": 31415
            },
            "expected_output": "millis=31415\nutc=Thu, 01 Jan 1970 00:00:31 GMT\n"
        }
    ]
}
```

---

### Feature 10: Error Object Creation and Throwing

**As a developer**, I want domain errors to preserve categories and messages without leaking implementation exception names, so callers receive stable failure contracts.

**Expected Behavior / Usage:**

The adapter accepts an error scenario and optional message. It prints normalized categories for generic, type, and range errors, confirms base error behavior as a boolean signal, reports thrown messages through `error=thrown_error`, and renders failed conversion text as data.

**Test Cases:** `rcb_tests/public_test_cases/feature10_errors.json`

```json
{
    "description": "Error objects preserve their domain category and message, thrown messages are reported through a normalized error contract, and failed conversions can be rendered as domain text.",
    "cases": [
        {
            "input": {
                "operation": "errors",
                "scenario": "create_generic",
                "message": "Oh, no!"
            },
            "expected_output": "category=generic_error\nmessage=Oh, no!\n"
        },
        {
            "input": {
                "operation": "errors",
                "scenario": "create_type",
                "message": "Type error? From Rust?!"
            },
            "expected_output": "[a predefined type error category]\nmessage=Type error? From Rust?!\nbase_error=true\n"
        }
    ]
}
```

---

### Feature 11: Binary Buffers and Typed Array Views

**As a developer**, I want binary memory and typed array views to preserve byte content, lengths, offsets, and copy behavior, so memory shared across the boundary remains verifiable.

**Expected Behavior / Usage:**

The adapter accepts a binary-memory scenario. It prints byte lengths, byte sequences, typed-array lengths, little-endian byte evidence, view metadata, region content, copied values, and normalized error categories for invalid regions or overlapping mutable borrows.

**Test Cases:** `rcb_tests/public_test_cases/feature11_binary_memory.json`

```json
{
    "description": "Binary memory operations expose byte lengths, byte contents, view metadata, copy behavior, and normalized failures for invalid or overlapping regions.",
    "cases": [
        {
            "input": {
                "operation": "binary",
                "scenario": "zeroed_array_buffer"
            },
            "expected_output": "[the standard buffer length for these zero operations]\nuint32_values=0,0,0,0\n"
        },
        {
            "input": {
                "operation": "binary",
                "scenario": "array_buffer_read_write"
            },
            "expected_output": "read_values=47,133,9,88888888\nwritten_bytes=3,42,127,255\nborrow_read_values=49,135,11,237\nborrow_written_bytes=43,100,22,243\n"
        },
        {
            "input": {
                "operation": "binary",
                "scenario": "buffer_read_write"
            },
            "expected_output": "lock_read=147,113,109,189\nborrow_read=149,224,70,229\nlock_written=6,61,45,216\nborrow_written=16,100,232,55\n"
        }
    ]
}
```

---

### Feature 12: Boxed Stateful Values

**As a developer**, I want opaque stateful values to be created, greeted, mutated, and type checked, so native-owned state can be safely exposed to callers.

**Expected Behavior / Usage:**

The adapter accepts a boxed-state scenario and optional names. It prints greetings for immutable and mutable state, mutation results after renaming, and neutral error categories for borrow conflicts and external type mismatches.

**Test Cases:** `rcb_tests/public_test_cases/feature12_boxed_state.json`

```json
{
    "description": "Opaque stateful values can be created, greeted, mutated, and protected by dynamic borrow/type checks reported with neutral error categories.",
    "cases": [
        {
            "input": {
                "operation": "boxed",
                "scenario": "greet",
                "name": "World"
            },
            "expected_output": "name=World\ngreeting=Hello, World!\n"
        },
        {
            "input": {
                "operation": "boxed",
                "scenario": "ref_greet",
                "name": "World"
            },
            "expected_output": "name=World\ngreeting=Hello, World!\n"
        }
    ]
}
```

---

### Feature 13: Asynchronous Results and Rejections

**As a developer**, I want asynchronous callbacks, promises, and background computations to resolve predictably, so async native work can integrate with caller workflows.

**Expected Behavior / Usage:**

The adapter accepts an asynchronous scenario and optional numeric values. It prints resolved sums for callback, promise, and background computations without exposing host runtime classes.

**Test Cases:** `rcb_tests/public_test_cases/feature13_async_results.json`

```json
{
    "description": "Asynchronous callbacks, promises, and worker-backed computations resolve to numeric results or reject with normalized exception categories.",
    "cases": [
        {
            "input": {
                "operation": "async",
                "scenario": "lazy_add"
            },
            "expected_output": "result=3\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_module_exports.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_module_exports@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- matches the mutation flag behavior described in the Data Structure Integrity section
- applicable to the function invocation tests in the Core Functions test suite
