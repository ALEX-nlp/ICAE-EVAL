## Product Requirement Document

# WebAssembly Module Loader & Runtime Bindings - Product Requirements

## Project Goal

Build a library that lets developers load a compiled WebAssembly (WASM) binary[a custom comma-separated string including null markers — ask the host interface spec] instantiate it[a custom comma-separated string including null markers — ask the host interface spec] and call into it from host code — wiring host-provided functions[a custom comma-separated string including null markers — ask the host interface spec] globals[a custom comma-separated string including null markers — ask the host interface spec] and memory into the module[a custom comma-separated string including null markers — ask the host interface spec] exchanging scalar values across the boundary[a custom comma-separated string including null markers — ask the host interface spec] and capturing the module's standard output — all without hand-writing low-level binary-interface glue or managing native runtime handles by hand.

---

## Background & Problem

Without this library[a custom comma-separated string including null markers — ask the host interface spec] a developer who wants to run a WASM module from a high-level language must manually drive a C-level WASM runtime: parse and validate the binary[a custom comma-separated string including null markers — ask the host interface spec] allocate stores and instances[a custom comma-separated string including null markers — ask the host interface spec] marshal each scalar argument into the runtime's tagged-value representation[a custom comma-separated string including null markers — ask the host interface spec] register host callbacks with the right signatures[a custom comma-separated string including null markers — ask the host interface spec] and free every native handle in the right order. This is verbose[a custom comma-separated string including null markers — ask the host interface spec] error-prone[a custom comma-separated string including null markers — ask the host interface spec] and leaks runtime details into application code; a single mismatched import or argument type produces an opaque native fault.

With this library[a custom comma-separated string including null markers — ask the host interface spec] the developer hands over a byte buffer[a custom comma-separated string including null markers — ask the host interface spec] declares the imports the module needs (functions[a custom comma-separated string including null markers — ask the host interface spec] globals[a custom comma-separated string including null markers — ask the host interface spec] memory) using ordinary host values and closures[a custom comma-separated string including null markers — ask the host interface spec] and then calls exported functions as if they were native — with value conversion[a custom comma-separated string including null markers — ask the host interface spec] import validation[a custom comma-separated string including null markers — ask the host interface spec] and error reporting handled for them. Misuse (a corrupted binary[a custom comma-separated string including null markers — ask the host interface spec] a missing or mistyped import[a custom comma-separated string including null markers — ask the host interface spec] an out-of-range memory grow[a custom comma-separated string including null markers — ask the host interface spec] a wrong-arity call) is surfaced as a well-defined error category rather than a crash.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact[a custom comma-separated string including null markers — ask the host interface spec] the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain spans several distinct responsibilities (binary compilation[a custom comma-separated string including null markers — ask the host interface spec] an import-building phase[a custom comma-separated string including null markers — ask the host interface spec] instantiation[a custom comma-separated string including null markers — ask the host interface spec] typed value marshaling[a custom comma-separated string including null markers — ask the host interface spec] memory management[a custom comma-separated string including null markers — ask the host interface spec] globals[a custom comma-separated string including null markers — ask the host interface spec] and a system-interface/stdout layer). It MUST therefore be organized into clear modules rather than a single "god file"[a custom comma-separated string including null markers — ask the host interface spec] with the public surface separated from the low-level runtime binding.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract for the execution adapter**[a custom comma-separated string including null markers — ask the host interface spec] NOT the internal data model. The core library must expose an idiomatic object API (a module[a custom comma-separated string including null markers — ask the host interface spec] an instance builder[a custom comma-separated string including null markers — ask the host interface spec] an instance[a custom comma-separated string including null markers — ask the host interface spec] functions[a custom comma-separated string including null markers — ask the host interface spec] globals[a custom comma-separated string including null markers — ask the host interface spec] memory) and must remain completely decoupled from stdin/stdout and JSON parsing. A separate execution adapter translates each JSON scenario into idiomatic calls and renders results.

3. **Adherence to SOLID Design Principles:**
   - **SRP:** Keep compilation[a custom comma-separated string including null markers — ask the host interface spec] import collection/validation[a custom comma-separated string including null markers — ask the host interface spec] instantiation[a custom comma-separated string including null markers — ask the host interface spec] value marshaling[a custom comma-separated string including null markers — ask the host interface spec] memory[a custom comma-separated string including null markers — ask the host interface spec] globals[a custom comma-separated string including null markers — ask the host interface spec] and output formatting in distinct units.
   - **OCP:** New value types or import kinds should extend the engine without rewriting the call path.
   - **LSP:** Exported and imported entities of the same category must be interchangeable through their abstractions.
   - **ISP:** Keep the module/builder/instance/function/global/memory interfaces small and cohesive.
   - **DIP:** High-level code depends on the typed API[a custom comma-separated string including null markers — ask the host interface spec] not on raw native handles.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** Exported functions should be callable like ordinary host functions; imports should be declared with ordinary host values and closures.
   - **Resilience:** Every misuse path (corrupt binary[a custom comma-separated string including null markers — ask the host interface spec] missing/duplicate/mis-kinded import[a custom comma-separated string including null markers — ask the host interface spec] wrong-arity or wrong-type call[a custom comma-separated string including null markers — ask the host interface spec] writing a constant global[a custom comma-separated string including null markers — ask the host interface spec] writing a wrong-typed value[a custom comma-separated string including null markers — ask the host interface spec] oversized memory create/grow[a custom comma-separated string including null markers — ask the host interface spec] system-interface misuse) must be modeled as a distinct[a custom comma-separated string including null markers — ask the host interface spec] well-defined error rather than a generic fault.

---

## Output Contract (applies to every feature)

The execution adapter reads ONE JSON scenario object on stdin and writes a line-oriented[a custom comma-separated string including null markers — ask the host interface spec] language-neutral result to stdout. The conventions used in `expected_output` across all features are:

- `result[<fn>]=[a specific high-precision decimal string — check the test harness config]` — the return value of calling exported function `<fn>`; a void return is rendered as `result[<fn>]=void`.
- `lookup[<name>]=present|missing` — whether an exported function exists.
- `global[<name>]=[a specific high-precision decimal string — check the test harness config]` — the current value of a global.
- `[a custom comma-separated string including null markers — ask the host interface spec][<ns>::<name>]=<v1>[a custom comma-separated string including null markers — ask the host interface spec]<v2>[a custom comma-separated string including null markers — ask the host interface spec]...` — the arguments a host import received during a call.
- `output=<text>` / `stdout=<text>` — captured text produced by the module.
- `instantiated=true` — a successful instantiation.
- memory: `pages=<n>`[a custom comma-separated string including null markers — ask the host interface spec] `bytes=<n>`[a custom comma-separated string including null markers — ask the host interface spec] `write[<i>]=<v>`[a custom comma-separated string including null markers — ask the host interface spec] `byte[<i>]=<v>`[a custom comma-separated string including null markers — ask the host interface spec] `grow[<n>]=ok`.
- Errors are normalized to `error=<category>` lines[a custom comma-separated string including null markers — ask the host interface spec] optionally followed by structured fields (`detail=`[a custom comma-separated string including null markers — ask the host interface spec] `type=`[a custom comma-separated string including null markers — ask the host interface spec] `import=`[a custom comma-separated string including null markers — ask the host interface spec] `expected=`[a custom comma-separated string including null markers — ask the host interface spec] `message=`) on their own lines. Error categories used: `compile_failed`[a custom comma-separated string including null markers — ask the host interface spec] `argument_count`[a custom comma-separated string including null markers — ask the host interface spec] `argument_type`[a custom comma-separated string including null markers — ask the host interface spec] `const_global_write`[a custom comma-separated string including null markers — ask the host interface spec] `bad_value_type`[a custom comma-separated string including null markers — ask the host interface spec] `import_not_found`[a custom comma-separated string including null markers — ask the host interface spec] `import_already_filled`[a custom comma-separated string including null markers — ask the host interface spec] `import_kind_mismatch`[a custom comma-separated string including null markers — ask the host interface spec] `missing_import`[a custom comma-separated string including null markers — ask the host interface spec] `memory_create_failed`[a custom comma-separated string including null markers — ask the host interface spec] `memory_grow_failed`[a custom comma-separated string including null markers — ask the host interface spec] `wasi_fill_failed`[a custom comma-separated string including null markers — ask the host interface spec] `wasi_already_enabled`[a custom comma-separated string including null markers — ask the host interface spec] `stdout_without_wasi`[a custom comma-separated string including null markers — ask the host interface spec] `stderr_without_wasi`[a custom comma-separated string including null markers — ask the host interface spec] `imported_function_threw`.

In the JSON scenarios[a custom comma-separated string including null markers — ask the host interface spec] a WASM binary is supplied as a lowercase hex string in the `module` field. Hex strings are the actual module bytes under test and are reproduced verbatim.

---

## Core Features

### Feature 1: Module Compilation

**As a developer**[a custom comma-separated string including null markers — ask the host interface spec] I want to compile a byte buffer into a runnable module[a custom comma-separated string including null markers — ask the host interface spec] so I can reject malformed binaries up front with a clear[a custom comma-separated string including null markers — ask the host interface spec] structured reason.

**Expected Behavior / Usage:**

The input scenario carries a `module` hex string and nothing else (no `build`). The adapter attempts to compile the bytes into a module. A buffer whose contents are not a valid WASM binary (e.g. the leading 4-byte signature is missing) must fail compilation: emit `error=compile_failed` followed by a `detail=<...>` line carrying the runtime's validation message. A buffer that compiles cleanly produces no output for this step (compilation is exercised implicitly by every later feature).

**Test Cases:** `rcb_tests/public_test_cases/feature1_module_compilation.json`

```json
{
  "description": "Compiling a byte buffer into a module: a buffer whose leading bytes are not the WASM binary signature is rejected with a normalized compile-failure category and the underlying validation detail."[a custom comma-separated string including null markers — ask the host interface spec]
  "cases": [
    {
      "input": {
        "module": "0100000001060160017e017e071302066d656d6f727902000673717561726500000020007e0b"
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "error=compile_failed\ndetail=Validation error: Bad magic number (at offset 0)\u0000\n"
    }
  ]
}
```

---

### Feature 2: Exported Function Lookup & Invocation

**As a developer**[a custom comma-separated string including null markers — ask the host interface spec] I want to look up an exported function by name and call it with host values[a custom comma-separated string including null markers — ask the host interface spec] so I can invoke module logic as if it were native code and get clear errors on misuse.

**Expected Behavior / Usage:**

The scenario compiles and builds (`build: true`) a module[a custom comma-separated string including null markers — ask the host interface spec] then runs `steps`. An `invoke` step names an exported function and supplies an argument list; the adapter emits `result[<fn>]=[a specific high-precision decimal string — check the test harness config]`. A `lookup` step reports `lookup[<name>]=present` or `missing` — looking up a name that the module does not export is `missing` (not an error). Calling a function with the wrong number of arguments yields `error=argument_count`; calling it with an argument of the wrong scalar type yields `error=argument_type`. The sample module exports `square(int64)->int64`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_function_invocation.json`

```json
{
  "description": "Looking up an exported function by name and calling it; looking up a name that is not exported reports it as missing; calling with the wrong number or wrong type of arguments yields normalized argument errors."[a custom comma-separated string including null markers — ask the host interface spec]
  "cases": [
    {
      "input": {
        "module": "0061736d0100000001060160017e017e030201000405017001010105030100020608017f01418088040b071302066d656d6f727902000673717561726500000a09010700200020007e0b"[a custom comma-separated string including null markers — ask the host interface spec]
        "build": true[a custom comma-separated string including null markers — ask the host interface spec]
        "steps": [
          {
            "op": "invoke"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "square"[a custom comma-separated string including null markers — ask the host interface spec]
            "args": [
              1234
            ]
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "op": "lookup"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "not_a_function"
          }
        ]
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "result[square]=1522756\nlookup[not_a_function]=missing\n"
    }[a custom comma-separated string including null markers — ask the host interface spec]
    {
      "input": {
        "module": "0061736d0100000001060160017e017e030201000405017001010105030100020608017f01418088040b071302066d656d6f727902000673717561726500000a09010700200020007e0b"[a custom comma-separated string including null markers — ask the host interface spec]
        "build": true[a custom comma-separated string including null markers — ask the host interface spec]
        "steps": [
          {
            "op": "invoke"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "square"[a custom comma-separated string including null markers — ask the host interface spec]
            "args": []
          }
        ]
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "error=argument_count\n"
    }[a custom comma-separated string including null markers — ask the host interface spec]
    {
      "input": {
        "module": "0061736d0100000001060160017e017e030201000405017001010105030100020608017f01418088040b071302066d656d6f727902000673717561726500000a09010700200020007e0b"[a custom comma-separated string including null markers — ask the host interface spec]
        "build": true[a custom comma-separated string including null markers — ask the host interface spec]
        "steps": [
          {
            "op": "invoke"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "square"[a custom comma-separated string including null markers — ask the host interface spec]
            "args": [
              1.23
            ]
          }
        ]
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "error=argument_type\n"
    }
  ]
}
```

---

### Feature 3: Numeric Value Types

**As a developer**[a custom comma-separated string including null markers — ask the host interface spec] I want to pass and receive all four scalar value types across the boundary[a custom comma-separated string including null markers — ask the host interface spec] so I can call numeric routines without manually marshaling tagged values.

**Expected Behavior / Usage:**

The module exports four addition functions over the four scalar types: 64-bit integer[a custom comma-separated string including null markers — ask the host interface spec] 32-bit integer[a custom comma-separated string including null markers — ask the host interface spec] 64-bit float[a custom comma-separated string including null markers — ask the host interface spec] and 32-bit float. Each `invoke` returns the sum as `result[<fn>]=[a specific high-precision decimal string — check the test harness config]`. Integer results are exact. Float results are rendered in the host's natural decimal form for the corresponding IEEE-754 precision — note that a 32-bit-float sum is reported at single-precision (so it carries the rounding of that precision)[a custom comma-separated string including null markers — ask the host interface spec] distinct from the 64-bit-float result of the same inputs.

**Test Cases:** `rcb_tests/public_test_cases/feature3_numeric_types.json`

```json
{
  "description": "Calling functions that add the four scalar value types (32/64-bit integers and 32/64-bit floats) and returning the wire result for each."[a custom comma-separated string including null markers — ask the host interface spec]
  "cases": [
    {
      "input": {
        "module": "0061736d0100000001190460027e7e017e60027f7f017f60027c7c017c60027d7d017d030504000102030405017001010105030100020608017f01418088040b072e05066d656d6f727902000661646449363400000661646449333200010661646446363400020661646446333200030a21040700200120007c0b0700200120006a0b070020002001a00b070020002001920b"[a custom comma-separated string including null markers — ask the host interface spec]
        "build": true[a custom comma-separated string including null markers — ask the host interface spec]
        "steps": [
          {
            "op": "invoke"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "addI64"[a custom comma-separated string including null markers — ask the host interface spec]
            "args": [
              81985529216486895[a custom comma-separated string including null markers — ask the host interface spec]
              1147797409030816545
            ]
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "op": "invoke"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "addI32"[a custom comma-separated string including null markers — ask the host interface spec]
            "args": [
              11259375[a custom comma-separated string including null markers — ask the host interface spec]
              16702650
            ]
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "op": "invoke"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "addF64"[a custom comma-separated string including null markers — ask the host interface spec]
            "args": [
              1234.5678[a custom comma-separated string including null markers — ask the host interface spec]
              8765.4321
            ]
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "op": "invoke"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "addF32"[a custom comma-separated string including null markers — ask the host interface spec]
            "args": [
              1234.5678[a custom comma-separated string including null markers — ask the host interface spec]
              8765.4321
            ]
          }
        ]
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "result[addI64]=1229782938247303440\nresult[addI32]=27962025\nresult[addF64]=9999.9999\nresult[addF32]=9999.9990234375\n"
    }
  ]
}
```

---

### Feature 4: Void Returns & Parameterless Functions

**As a developer**[a custom comma-separated string including null markers — ask the host interface spec] I want to call functions that return nothing and functions that take no arguments[a custom comma-separated string including null markers — ask the host interface spec] so I can drive side-effecting and accessor-style exports.

**Expected Behavior / Usage:**

The module holds internal state. A `set(int64[a custom comma-separated string including null markers — ask the host interface spec]int64)` function with a void return mutates that state and reports `result[set]=void`. A subsequent parameterless `get()` returns the stored value as `result[get]=[a specific high-precision decimal string — check the test harness config]`. This confirms that void returns are represented explicitly (not as a numeric zero) and that no-argument calls work.

**Test Cases:** `rcb_tests/public_test_cases/feature4_void_and_noarg.json`

```json
{
  "description": "Calling a function with a void return type (which reports no value) followed by a parameterless function that returns the state mutated by the first call."[a custom comma-separated string including null markers — ask the host interface spec]
  "cases": [
    {
      "input": {
        "module": "0061736d01000000010a0260027e7e006000017e03030200010405017001010105030100020608017f01419088040b071603066d656d6f727902000373657400000367657400010a1e0210004100200120007c370380888080000b0b004100290380888080000b0b0f01004180080b080000000000000000"[a custom comma-separated string including null markers — ask the host interface spec]
        "build": true[a custom comma-separated string including null markers — ask the host interface spec]
        "steps": [
          {
            "op": "invoke"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "set"[a custom comma-separated string including null markers — ask the host interface spec]
            "args": [
              123[a custom comma-separated string including null markers — ask the host interface spec]
              456
            ]
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "op": "invoke"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "get"[a custom comma-separated string including null markers — ask the host interface spec]
            "args": []
          }
        ]
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "result[set]=void\nresult[get]=579\n"
    }
  ]
}
```

---

### Feature 5: Host Function Imports

**As a developer**[a custom comma-separated string including null markers — ask the host interface spec] I want module code to call back into host-provided functions[a custom comma-separated string including null markers — ask the host interface spec] so the module can delegate behavior to my code and so host errors surface cleanly.

**Expected Behavior / Usage:**

*5.1 Argument Passing into Host Imports — values flow from module code into a host callback.*

The scenario declares a function import (`kind: "function"`) under a namespace and name with an `echo_args` behavior; module code calls it during an `invoke`. After the call[a custom comma-separated string including null markers — ask the host interface spec] an `[a custom comma-separated string including null markers — ask the host interface spec]` step reports the arguments the host import received as `[a custom comma-separated string including null markers — ask the host interface spec][<ns>::<name>]=<v1>[a custom comma-separated string including null markers — ask the host interface spec]<v2>`. The sample module's exported `reportStuff` calls the imported `env::report(int64[a custom comma-separated string including null markers — ask the host interface spec]int64)` with fixed values.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_host_function_args.json`

```json
{
  "description": "A module function that calls back into a host-provided function; the host import records the arguments it receives[a custom comma-separated string including null markers — ask the host interface spec] demonstrating values flow from module code into the host callback."[a custom comma-separated string including null markers — ask the host interface spec]
  "cases": [
    {
      "input": {
        "module": "0061736d0100000001090260027e7e00600000020e0103656e76067265706f72740000030201010405017001010105030100020608017f01418088040b071802066d656d6f727902000b7265706f7274537475666600010a10010e0042fb0042c8031080808080000b"[a custom comma-separated string including null markers — ask the host interface spec]
        "imports": [
          {
            "kind": "function"[a custom comma-separated string including null markers — ask the host interface spec]
            "module": "env"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "report"[a custom comma-separated string including null markers — ask the host interface spec]
            "behavior": "echo_args"[a custom comma-separated string including null markers — ask the host interface spec]
            "arity": 2
          }
        ][a custom comma-separated string including null markers — ask the host interface spec]
        "build": true[a custom comma-separated string including null markers — ask the host interface spec]
        "steps": [
          {
            "op": "invoke"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "reportStuff"[a custom comma-separated string including null markers — ask the host interface spec]
            "args": []
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "op": "[a custom comma-separated string including null markers — ask the host interface spec]"[a custom comma-separated string including null markers — ask the host interface spec]
            "ref": "env::report"
          }
        ]
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "result[reportStuff]=void\n[a custom comma-separated string including null markers — ask the host interface spec][env::report]=123[a custom comma-separated string including null markers — ask the host interface spec]456\n"
    }
  ]
}
```

*5.2 Exception Propagation from Host Imports — an error thrown by a host import unwinds the module call.*

When a host import is declared with a `throw` behavior and module code calls it[a custom comma-separated string including null markers — ask the host interface spec] the raised error must propagate out of the in-progress `invoke` and be reported as `error=imported_function_threw` followed by `message=<text>` carrying the host error's message. A second never-reached import confirms control did not continue past the throw.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_host_function_exception.json`

```json
{
  "description": "When a host-provided import raises an error during a module call[a custom comma-separated string including null markers — ask the host interface spec] the error propagates out of the call and is reported with a normalized category plus the error message."[a custom comma-separated string including null markers — ask the host interface spec]
  "cases": [
    {
      "input": {
        "module": "0061736d0100000001040160000002110203656e760161000003656e7601620000030201000405017001010105030100020608017f01418088040b070f02066d656d6f7279020002666e00020a10010e001080808080001081808080000b"[a custom comma-separated string including null markers — ask the host interface spec]
        "imports": [
          {
            "kind": "function"[a custom comma-separated string including null markers — ask the host interface spec]
            "module": "env"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "a"[a custom comma-separated string including null markers — ask the host interface spec]
            "behavior": "throw"[a custom comma-separated string including null markers — ask the host interface spec]
            "message": "Hello exception!"[a custom comma-separated string including null markers — ask the host interface spec]
            "arity": 0
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "kind": "function"[a custom comma-separated string including null markers — ask the host interface spec]
            "module": "env"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "b"[a custom comma-separated string including null markers — ask the host interface spec]
            "behavior": "return"[a custom comma-separated string including null markers — ask the host interface spec]
            "arity": 0[a custom comma-separated string including null markers — ask the host interface spec]
            "value": null
          }
        ][a custom comma-separated string including null markers — ask the host interface spec]
        "build": true[a custom comma-separated string including null markers — ask the host interface spec]
        "steps": [
          {
            "op": "invoke"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "fn"[a custom comma-separated string including null markers — ask the host interface spec]
            "args": []
          }
        ]
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "error=imported_function_threw\nmessage=Hello exception!\n"
    }
  ]
}
```

---

### Feature 6: Global Variables

**As a developer**[a custom comma-separated string including null markers — ask the host interface spec] I want to read and write module globals (both exported and imported)[a custom comma-separated string including null markers — ask the host interface spec] so I can share mutable and constant state across the boundary safely.

**Expected Behavior / Usage:**

The scenario imports a constant global `env::bar` with an initial value and builds a module that exports a mutable global `foo` and a function `baz()` computing `foo * bar`. Steps can read an exported global (`read_global`)[a custom comma-separated string including null markers — ask the host interface spec] read an imported global (`read_import_global`)[a custom comma-separated string including null markers — ask the host interface spec] write a mutable exported global (`write_global`[a custom comma-separated string including null markers — ask the host interface spec] which re-reports the new value)[a custom comma-separated string including null markers — ask the host interface spec] and invoke the dependent function to observe the change. Two error paths are required: writing to a constant (imported) global yields `error=const_global_write`; writing a value whose type does not match the global's declared scalar type yields `error=bad_value_type` followed by `type=<declared type>`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_globals.json`

```json
{
  "description": "Reading exported and imported globals[a custom comma-separated string including null markers — ask the host interface spec] calling a function that depends on them[a custom comma-separated string including null markers — ask the host interface spec] writing a mutable global and observing the dependent function change[a custom comma-separated string including null markers — ask the host interface spec] then the errors raised by writing a constant global and by writing a value of the wrong type."[a custom comma-separated string including null markers — ask the host interface spec]
  "cases": [
    {
      "input": {
        "module": "0061736d010000000105016000017f020c0103656e7603626172037f000302010004040170000005030100010606017f0141250b071603066d656d6f727902000362617a000003666f6f03010a09010700230123006c0b0b0a0100410c0b0425000000"[a custom comma-separated string including null markers — ask the host interface spec]
        "imports": [
          {
            "kind": "global"[a custom comma-separated string including null markers — ask the host interface spec]
            "module": "env"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "bar"[a custom comma-separated string including null markers — ask the host interface spec]
            "value": 10
          }
        ][a custom comma-separated string including null markers — ask the host interface spec]
        "build": true[a custom comma-separated string including null markers — ask the host interface spec]
        "steps": [
          {
            "op": "read_global"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "foo"
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "op": "read_import_global"[a custom comma-separated string including null markers — ask the host interface spec]
            "ref": "env::bar"
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "op": "invoke"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "baz"[a custom comma-separated string including null markers — ask the host interface spec]
            "args": []
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "op": "write_global"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "foo"[a custom comma-separated string including null markers — ask the host interface spec]
            "value": 99
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "op": "invoke"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "baz"[a custom comma-separated string including null markers — ask the host interface spec]
            "args": []
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "op": "write_import_global"[a custom comma-separated string including null markers — ask the host interface spec]
            "ref": "env::bar"[a custom comma-separated string including null markers — ask the host interface spec]
            "value": 100
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "op": "write_global"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "foo"[a custom comma-separated string including null markers — ask the host interface spec]
            "value": 3.14159
          }
        ]
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "global[foo]=37\nglobal[env::bar]=10\nresult[baz]=370\nglobal[foo]=99\nresult[baz]=990\nerror=const_global_write\nerror=bad_value_type\ntype=int32\n"
    }
  ]
}
```

---

### Feature 7: Linear Memory

**As a developer**[a custom comma-separated string including null markers — ask the host interface spec] I want to create[a custom comma-separated string including null markers — ask the host interface spec] inspect[a custom comma-separated string including null markers — ask the host interface spec] edit[a custom comma-separated string including null markers — ask the host interface spec] and grow linear memory[a custom comma-separated string including null markers — ask the host interface spec] with limit violations reported clearly.

**Expected Behavior / Usage:**

*7.1 Create[a custom comma-separated string including null markers — ask the host interface spec] Inspect[a custom comma-separated string including null markers — ask the host interface spec] Edit[a custom comma-separated string including null markers — ask the host interface spec] Grow — the happy path of standalone memory.*

The scenario uses `standalone_memory: {pages: N}` to create a memory directly from a module[a custom comma-separated string including null markers — ask the host interface spec] then runs `memory_ops`. `info` reports `pages=<n>` and `bytes=<n>` (bytes = pages times 64 KiB). `write` sets a byte and echoes `write[<i>]=<v>`; `read` reports `byte[<i>]=<v>`. `grow` adds pages and reports `grow[<n>]=ok`. After growing[a custom comma-separated string including null markers — ask the host interface spec] size reflects the new page count and previously-written bytes are preserved.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_memory_ops.json`

```json
{
  "description": "Creating a standalone linear memory[a custom comma-separated string including null markers — ask the host interface spec] reporting its size in pages and bytes[a custom comma-separated string including null markers — ask the host interface spec] writing and reading a byte[a custom comma-separated string including null markers — ask the host interface spec] growing it by some pages[a custom comma-separated string including null markers — ask the host interface spec] and confirming size grew and the written byte survived the grow."[a custom comma-separated string including null markers — ask the host interface spec]
  "cases": [
    {
      "input": {
        "module": "0061736d0100000006810000"[a custom comma-separated string including null markers — ask the host interface spec]
        "standalone_memory": {
          "pages": 100
        }[a custom comma-separated string including null markers — ask the host interface spec]
        "memory_ops": [
          {
            "op": "info"
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "op": "write"[a custom comma-separated string including null markers — ask the host interface spec]
            "index": 123[a custom comma-separated string including null markers — ask the host interface spec]
            "value": 45
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "op": "read"[a custom comma-separated string including null markers — ask the host interface spec]
            "index": 123
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "op": "grow"[a custom comma-separated string including null markers — ask the host interface spec]
            "pages": 10
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "op": "info"
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "op": "read"[a custom comma-separated string including null markers — ask the host interface spec]
            "index": 123
          }
        ]
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "pages=100\nbytes=6553600\nwrite[123]=45\nbyte[123]=45\ngrow[10]=ok\npages=110\nbytes=7208960\nbyte[123]=45\n"
    }
  ]
}
```

*7.2 Memory Limit Errors — out-of-range create and grow.*

Requesting an impossibly large initial page count fails creation with `error=memory_create_failed`. Growing a memory beyond what the runtime can satisfy[a custom comma-separated string including null markers — ask the host interface spec] or beyond a declared maximum page count (`standalone_memory: {pages: N[a custom comma-separated string including null markers — ask the host interface spec] max: M}`)[a custom comma-separated string including null markers — ask the host interface spec] fails with `error=memory_grow_failed`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_memory_errors.json`

```json
{
  "description": "Memory operations that exceed limits: requesting an impossibly large initial size fails creation; growing past the implementation limit fails; growing past a declared maximum fails. Each yields a normalized category."[a custom comma-separated string including null markers — ask the host interface spec]
  "cases": [
    {
      "input": {
        "module": "0061736d0100000006810000"[a custom comma-separated string including null markers — ask the host interface spec]
        "standalone_memory": {
          "pages": 1000000000
        }
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "error=memory_create_failed\n"
    }[a custom comma-separated string including null markers — ask the host interface spec]
    {
      "input": {
        "module": "0061736d0100000006810000"[a custom comma-separated string including null markers — ask the host interface spec]
        "standalone_memory": {
          "pages": 100[a custom comma-separated string including null markers — ask the host interface spec]
          "max": 200
        }[a custom comma-separated string including null markers — ask the host interface spec]
        "memory_ops": [
          {
            "op": "grow"[a custom comma-separated string including null markers — ask the host interface spec]
            "pages": 300
          }
        ]
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "error=memory_grow_failed\n"
    }
  ]
}
```

---

### Feature 8: Import Validation at Instantiation

**As a developer**[a custom comma-separated string including null markers — ask the host interface spec] I want the builder to validate the imports I supply before producing an instance[a custom comma-separated string including null markers — ask the host interface spec] so mistakes are caught with precise[a custom comma-separated string including null markers — ask the host interface spec] structured errors instead of native crashes.

**Expected Behavior / Usage:**

The module requires a single function import `env::someFn(int32[a custom comma-separated string including null markers — ask the host interface spec]int64[a custom comma-separated string including null markers — ask the host interface spec]float32[a custom comma-separated string including null markers — ask the host interface spec]float64)->int64`. Supplying it correctly and building yields `instantiated=true`. The required error paths are: building with the import unfilled gives `error=missing_import`; supplying an import of the wrong kind where a function is required (a memory[a custom comma-separated string including null markers — ask the host interface spec] or a global) gives `error=import_kind_mismatch` followed by `expected=<memory|global>`; declaring an import under a namespace or name the module does not list gives `error=import_not_found` followed by `import=<ns>::<name>`; filling the same import twice gives `error=import_already_filled` followed by `import=<ns>::<name>`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_import_validation.json`

```json
{
  "description": "Instantiation-time import checking: a fully and correctly supplied set of imports instantiates successfully; leaving an import unfilled[a custom comma-separated string including null markers — ask the host interface spec] supplying an import of the wrong kind (memory/global where a function is expected)[a custom comma-separated string including null markers — ask the host interface spec] naming an import that does not exist[a custom comma-separated string including null markers — ask the host interface spec] or filling the same import twice each yields a normalized category (with the offending import name where relevant)."[a custom comma-separated string including null markers — ask the host interface spec]
  "cases": [
    {
      "input": {
        "module": "0061736d01000000010c0260047f7e7d7c017e600000020e0103656e7606736f6d65466e0000030201010405017001010105030100020608017f01418088040b071102066d656d6f7279020004626c616800010a1d011b004101420243000040404400000000000010401080808080001a0b"[a custom comma-separated string including null markers — ask the host interface spec]
        "imports": [
          {
            "kind": "function"[a custom comma-separated string including null markers — ask the host interface spec]
            "module": "env"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "someFn"[a custom comma-separated string including null markers — ask the host interface spec]
            "behavior": "return"[a custom comma-separated string including null markers — ask the host interface spec]
            "arity": 4[a custom comma-separated string including null markers — ask the host interface spec]
            "value": 123
          }
        ][a custom comma-separated string including null markers — ask the host interface spec]
        "build": true[a custom comma-separated string including null markers — ask the host interface spec]
        "report_build": true
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "instantiated=true\n"
    }[a custom comma-separated string including null markers — ask the host interface spec]
    {
      "input": {
        "module": "0061736d01000000010c0260047f7e7d7c017e600000020e0103656e7606736f6d65466e0000030201010405017001010105030100020608017f01418088040b071102066d656d6f7279020004626c616800010a1d011b004101420243000040404400000000000010401080808080001a0b"[a custom comma-separated string including null markers — ask the host interface spec]
        "build": true
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "error=missing_import\n"
    }[a custom comma-separated string including null markers — ask the host interface spec]
    {
      "input": {
        "module": "0061736d01000000010c0260047f7e7d7c017e600000020e0103656e7606736f6d65466e0000030201010405017001010105030100020608017f01418088040b071102066d656d6f7279020004626c616800010a1d011b004101420243000040404400000000000010401080808080001a0b"[a custom comma-separated string including null markers — ask the host interface spec]
        "imports": [
          {
            "kind": "global"[a custom comma-separated string including null markers — ask the host interface spec]
            "module": "env"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "someFn"[a custom comma-separated string including null markers — ask the host interface spec]
            "value": 123
          }
        ]
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "error=import_kind_mismatch\nexpected=global\n"
    }[a custom comma-separated string including null markers — ask the host interface spec]
    {
      "input": {
        "module": "0061736d01000000010c0260047f7e7d7c017e600000020e0103656e7606736f6d65466e0000030201010405017001010105030100020608017f01418088040b071102066d656d6f7279020004626c616800010a1d011b004101420243000040404400000000000010401080808080001a0b"[a custom comma-separated string including null markers — ask the host interface spec]
        "imports": [
          {
            "kind": "function"[a custom comma-separated string including null markers — ask the host interface spec]
            "module": "foo"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "someFn"[a custom comma-separated string including null markers — ask the host interface spec]
            "behavior": "return"[a custom comma-separated string including null markers — ask the host interface spec]
            "arity": 4[a custom comma-separated string including null markers — ask the host interface spec]
            "value": 123
          }
        ][a custom comma-separated string including null markers — ask the host interface spec]
        "build": true
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "error=import_not_found\nimport=foo::someFn\n"
    }[a custom comma-separated string including null markers — ask the host interface spec]
    {
      "input": {
        "module": "0061736d01000000010c0260047f7e7d7c017e600000020e0103656e7606736f6d65466e0000030201010405017001010105030100020608017f01418088040b071102066d656d6f7279020004626c616800010a1d011b004101420243000040404400000000000010401080808080001a0b"[a custom comma-separated string including null markers — ask the host interface spec]
        "imports": [
          {
            "kind": "function"[a custom comma-separated string including null markers — ask the host interface spec]
            "module": "env"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "someFn"[a custom comma-separated string including null markers — ask the host interface spec]
            "behavior": "return"[a custom comma-separated string including null markers — ask the host interface spec]
            "arity": 4[a custom comma-separated string including null markers — ask the host interface spec]
            "value": 123
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "kind": "function"[a custom comma-separated string including null markers — ask the host interface spec]
            "module": "env"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "someFn"[a custom comma-separated string including null markers — ask the host interface spec]
            "behavior": "return"[a custom comma-separated string including null markers — ask the host interface spec]
            "arity": 4[a custom comma-separated string including null markers — ask the host interface spec]
            "value": 456
          }
        ]
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "error=import_already_filled\nimport=env::someFn\n"
    }
  ]
}
```

---

### Feature 9: System Interface & Standard Output

**As a developer**[a custom comma-separated string including null markers — ask the host interface spec] I want to run modules that use the standard system interface and capture what they print[a custom comma-separated string including null markers — ask the host interface spec] or wire the system calls myself[a custom comma-separated string including null markers — ask the host interface spec] with misuse reported clearly.

**Expected Behavior / Usage:**

*9.1 Enable System Interface and Capture stdout — run an entry point and read its output.*

With `wasi: {capture_stdout: true}` and `build: true`[a custom comma-separated string including null markers — ask the host interface spec] the adapter enables the system interface with stdout capture[a custom comma-separated string including null markers — ask the host interface spec] invokes the module entry point (`_start`)[a custom comma-separated string including null markers — ask the host interface spec] then a `read_stdout` step reports the captured text as `stdout=<text>`. The sample module prints a greeting followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_wasi_capture_stdout.json`

```json
{
  "description": "Enabling the system interface with stdout capture[a custom comma-separated string including null markers — ask the host interface spec] running the module entry point[a custom comma-separated string including null markers — ask the host interface spec] and reading back the captured standard output text."[a custom comma-separated string including null markers — ask the host interface spec]
  "cases": [
    {
      "input": {
        "module": "0061736d0100000001330960037f7f7f017f60047f7f7f7f017f60000060027f7f017f60017f017f60037f7e7f017e6000017f60017f0060037f7f7f00021a010d776173695f756e737461626c650866645f77726974650001030f0e03040003020705040306020208000405017001040405060101800280020609017f0141c095c0020b072e04066d656d6f72790200115f5f7761736d5f63616c6c5f63746f72730005046d61696e0004065f7374617274000b0909010041010b03080e070aae0c0ebf0101057f4180082104024020012802102202047f200205200110020d0120012802100b200128021422056b20004904402001418008200020012802241100000f0b024020012c004b4100480d0020002103034020032202450d012002417f6a22034180086a2d0000410a470d000b20014180082002200128022411000022032002490d01200020026b210020024180086a210420012802142105200221060b20052004200010031a2001200128021420006a360214200020066a21030b20030b5901017f200020002d004a2201417f6a2001723a004a20002802002201410871044020002001412072360200417f0f0b200042003702042000200028022c220136021c200020013602142000200120002802306a36021041000b820401037f20024180c0004f0440200020012002100d20000f0b200020026a210302402000200173410371450440024020024101480440200021020c010b2000410371450440200021020c010b200021020340200220012d00003a0000200141016a2101200241016a220220034f0d0120024103710d000b0b02402003417c71220441c000490d002002200441406a22054b0d0003402002200128020036020020022001280204360204200220012802083602082002200128020c36020c2002200128021036021020022001280214360214200220012802183602182002200128021c36021c2002200128022036022020022001280224360224200220012802283602282002200128022c36022c2002200128023036023020022001280234360234200220012802383602382002200128023c36023c200141406b2101200241406b220220054d0d000b0b200220044f0d01034020022001280200360200200141046a2101200241046a22022004490d000b0c010b20034104490440200021020c010b2003417c6a22042000490440200021020c010b200021020340200220012d00003a0000200220012d00013a0001200220012d00023a0002200220012d00033a0003200141046a2101200241046a220220044d0d000b0b200220034904400340200220012d00003a0000200141016a2101200241016a22022003470d000b0b20000b0600100c41000b0300010b7e01037f230041106b220124002001410a3a000f024020002802102202450440200010020d01200028021021020b02402000280214220320024f0d0020002c004b410a460d002000200341016a3602142003410a3a00000c010b20002001410f6a410120002802241100004101470d0020012d000f1a0b200141106a24000b040042000b040041000b3101017f200021022002027f200128024c417f4c04402002200110010c010b2002200110010b220146044020000f0b20010b6201037f418008210003402000220141046a210020012802002202417f73200241fffdfb776a7141808182847871450d000b0240200241ff0171450440200121000c010b034020012d00012102200141016a2200210120020d000b0b20004180086b0b0c00027f4100410010040b1a0b6601027f419008280200220028024c41004e047f41010520010b1a0240417f4100100a2201200120001009471b4100480d00024020002d004b410a460d002000280214220120002802104f0d002000200141016a3602142001410a3a00000c010b200010060b0b3d01017f2002044003402000200120024180c00020024180c000491b22031003210020014180406b210120004180406b2100200220036b22020d000b0b0bb10201067f230041206b220324002003200028021c2204360210200028021421052003200236021c200320013602182003200520046b2201360214200120026a210641022105200341106a210103400240027f2006027f200028023c200120052003410c6a100004402003417f36020c417f0c010b200328020c0b22044604402000200028022c220136021c200020013602142000200120002802306a36021020020c010b2004417f4a0d012000410036021c2000420037031020002000280200412072360200410020054102460d001a200220012802046b0b2104200341206a240020040f0b200141086a20012004200128020422074b22081b220120042007410020081b6b220720012802006a3602002001200128020420076b360204200620046b2106200520086b21050c00000b000b0b4d06004180080b1268656c6c6f2c20776f726c64210000001804004198080b01050041a4080b01010041bc080b0e0200000003000000b804000000040041d4080b01010041e3080b050affffffff"[a custom comma-separated string including null markers — ask the host interface spec]
        "wasi": {
          "capture_stdout": true
        }[a custom comma-separated string including null markers — ask the host interface spec]
        "build": true[a custom comma-separated string including null markers — ask the host interface spec]
        "steps": [
          {
            "op": "invoke"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "_start"[a custom comma-separated string including null markers — ask the host interface spec]
            "args": []
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "op": "read_stdout"
          }
        ]
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "result[_start]=void\nstdout=hello[a custom comma-separated string including null markers — ask the host interface spec] world!\n\n"
    }
  ]
}
```

*9.2 Manually Provided System Call — supply the write function by hand.*

Instead of enabling the system interface[a custom comma-separated string including null markers — ask the host interface spec] the scenario supplies the required write function as an ordinary host import (`fd_write_capture` behavior). When the entry point runs[a custom comma-separated string including null markers — ask the host interface spec] the host function reads the strings from the instance's exported memory and accumulates them; a `captured_output` step reports them as `output=<text>`. This demonstrates a host import reading typed arguments and the instance's memory together.

**Test Cases:** `rcb_tests/public_test_cases/feature9_2_manual_fd_write.json`

```json
{
  "description": "Supplying a host write function manually (instead of enabling the system interface): the module entry point calls it[a custom comma-separated string including null markers — ask the host interface spec] the host reads the strings from the instance memory and accumulates them[a custom comma-separated string including null markers — ask the host interface spec] and the accumulated output is reported."[a custom comma-separated string including null markers — ask the host interface spec]
  "cases": [
    {
      "input": {
        "module": "0061736d0100000001330960037f7f7f017f60047f7f7f7f017f60000060027f7f017f60017f017f60037f7e7f017e6000017f60017f0060037f7f7f00021a010d776173695f756e737461626c650866645f77726974650001030f0e03040003020705040306020208000405017001040405060101800280020609017f0141c095c0020b072e04066d656d6f72790200115f5f7761736d5f63616c6c5f63746f72730005046d61696e0004065f7374617274000b0909010041010b03080e070aae0c0ebf0101057f4180082104024020012802102202047f200205200110020d0120012802100b200128021422056b20004904402001418008200020012802241100000f0b024020012c004b4100480d0020002103034020032202450d012002417f6a22034180086a2d0000410a470d000b20014180082002200128022411000022032002490d01200020026b210020024180086a210420012802142105200221060b20052004200010031a2001200128021420006a360214200020066a21030b20030b5901017f200020002d004a2201417f6a2001723a004a20002802002201410871044020002001412072360200417f0f0b200042003702042000200028022c220136021c200020013602142000200120002802306a36021041000b820401037f20024180c0004f0440200020012002100d20000f0b200020026a210302402000200173410371450440024020024101480440200021020c010b2000410371450440200021020c010b200021020340200220012d00003a0000200141016a2101200241016a220220034f0d0120024103710d000b0b02402003417c71220441c000490d002002200441406a22054b0d0003402002200128020036020020022001280204360204200220012802083602082002200128020c36020c2002200128021036021020022001280214360214200220012802183602182002200128021c36021c2002200128022036022020022001280224360224200220012802283602282002200128022c36022c2002200128023036023020022001280234360234200220012802383602382002200128023c36023c200141406b2101200241406b220220054d0d000b0b200220044f0d01034020022001280200360200200141046a2101200241046a22022004490d000b0c010b20034104490440200021020c010b2003417c6a22042000490440200021020c010b200021020340200220012d00003a0000200220012d00013a0001200220012d00023a0002200220012d00033a0003200141046a2101200241046a220220044d0d000b0b200220034904400340200220012d00003a0000200141016a2101200241016a22022003470d000b0b20000b0600100c41000b0300010b7e01037f230041106b220124002001410a3a000f024020002802102202450440200010020d01200028021021020b02402000280214220320024f0d0020002c004b410a460d002000200341016a3602142003410a3a00000c010b20002001410f6a410120002802241100004101470d0020012d000f1a0b200141106a24000b040042000b040041000b3101017f200021022002027f200128024c417f4c04402002200110010c010b2002200110010b220146044020000f0b20010b6201037f418008210003402000220141046a210020012802002202417f73200241fffdfb776a7141808182847871450d000b0240200241ff0171450440200121000c010b034020012d00012102200141016a2200210120020d000b0b20004180086b0b0c00027f4100410010040b1a0b6601027f419008280200220028024c41004e047f41010520010b1a0240417f4100100a2201200120001009471b4100480d00024020002d004b410a460d002000280214220120002802104f0d002000200141016a3602142001410a3a00000c010b200010060b0b3d01017f2002044003402000200120024180c00020024180c000491b22031003210020014180406b210120004180406b2100200220036b22020d000b0b0bb10201067f230041206b220324002003200028021c2204360210200028021421052003200236021c200320013602182003200520046b2201360214200120026a210641022105200341106a210103400240027f2006027f200028023c200120052003410c6a100004402003417f36020c417f0c010b200328020c0b22044604402000200028022c220136021c200020013602142000200120002802306a36021020020c010b2004417f4a0d012000410036021c2000420037031020002000280200412072360200410020054102460d001a200220012802046b0b2104200341206a240020040f0b200141086a20012004200128020422074b22081b220120042007410020081b6b220720012802006a3602002001200128020420076b360204200620046b2106200520086b21050c00000b000b0b4d06004180080b1268656c6c6f2c20776f726c64210000001804004198080b01050041a4080b01010041bc080b0e0200000003000000b804000000040041d4080b01010041e3080b050affffffff"[a custom comma-separated string including null markers — ask the host interface spec]
        "imports": [
          {
            "kind": "function"[a custom comma-separated string including null markers — ask the host interface spec]
            "module": "wasi_unstable"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "fd_write"[a custom comma-separated string including null markers — ask the host interface spec]
            "behavior": "fd_write_capture"[a custom comma-separated string including null markers — ask the host interface spec]
            "arity": 4
          }
        ][a custom comma-separated string including null markers — ask the host interface spec]
        "build": true[a custom comma-separated string including null markers — ask the host interface spec]
        "steps": [
          {
            "op": "invoke"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "_start"[a custom comma-separated string including null markers — ask the host interface spec]
            "args": []
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "op": "captured_output"
          }
        ]
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "result[_start]=void\noutput=hello[a custom comma-separated string including null markers — ask the host interface spec] world!\n\n"
    }
  ]
}
```

*9.3 System Interface Error Conditions — misuse is reported[a custom comma-separated string including null markers — ask the host interface spec] not crashed.*

Enabling the system interface for a module that lacks the imports it expects yields `error=wasi_fill_failed`. Enabling it twice yields `error=wasi_already_enabled`. Building a module that needs the interface without supplying its imports yields `error=missing_import`. Requesting captured stdout or stderr when capture was not enabled yields `error=stdout_without_wasi` / `error=stderr_without_wasi` respectively.

**Test Cases:** `rcb_tests/public_test_cases/feature9_3_wasi_errors.json`

```json
{
  "description": "System-interface error conditions: enabling it for a module that lacks the required imports fails; enabling it twice fails; building a module that needs the interface without enabling it reports a missing import; and requesting captured stdout/stderr when capture was not enabled fails. Each yields a normalized category."[a custom comma-separated string including null markers — ask the host interface spec]
  "cases": [
    {
      "input": {
        "module": "0061736d0100000006810000"[a custom comma-separated string including null markers — ask the host interface spec]
        "wasi": {}
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "error=wasi_fill_failed\n"
    }[a custom comma-separated string including null markers — ask the host interface spec]
    {
      "input": {
        "module": "0061736d0100000001330960037f7f7f017f60047f7f7f7f017f60000060027f7f017f60017f017f60037f7e7f017e6000017f60017f0060037f7f7f00021a010d776173695f756e737461626c650866645f77726974650001030f0e03040003020705040306020208000405017001040405060101800280020609017f0141c095c0020b072e04066d656d6f72790200115f5f7761736d5f63616c6c5f63746f72730005046d61696e0004065f7374617274000b0909010041010b03080e070aae0c0ebf0101057f4180082104024020012802102202047f200205200110020d0120012802100b200128021422056b20004904402001418008200020012802241100000f0b024020012c004b4100480d0020002103034020032202450d012002417f6a22034180086a2d0000410a470d000b20014180082002200128022411000022032002490d01200020026b210020024180086a210420012802142105200221060b20052004200010031a2001200128021420006a360214200020066a21030b20030b5901017f200020002d004a2201417f6a2001723a004a20002802002201410871044020002001412072360200417f0f0b200042003702042000200028022c220136021c200020013602142000200120002802306a36021041000b820401037f20024180c0004f0440200020012002100d20000f0b200020026a210302402000200173410371450440024020024101480440200021020c010b2000410371450440200021020c010b200021020340200220012d00003a0000200141016a2101200241016a220220034f0d0120024103710d000b0b02402003417c71220441c000490d002002200441406a22054b0d0003402002200128020036020020022001280204360204200220012802083602082002200128020c36020c2002200128021036021020022001280214360214200220012802183602182002200128021c36021c2002200128022036022020022001280224360224200220012802283602282002200128022c36022c2002200128023036023020022001280234360234200220012802383602382002200128023c36023c200141406b2101200241406b220220054d0d000b0b200220044f0d01034020022001280200360200200141046a2101200241046a22022004490d000b0c010b20034104490440200021020c010b2003417c6a22042000490440200021020c010b200021020340200220012d00003a0000200220012d00013a0001200220012d00023a0002200220012d00033a0003200141046a2101200241046a220220044d0d000b0b200220034904400340200220012d00003a0000200141016a2101200241016a22022003470d000b0b20000b0600100c41000b0300010b7e01037f230041106b220124002001410a3a000f024020002802102202450440200010020d01200028021021020b02402000280214220320024f0d0020002c004b410a460d002000200341016a3602142003410a3a00000c010b20002001410f6a410120002802241100004101470d0020012d000f1a0b200141106a24000b040042000b040041000b3101017f200021022002027f200128024c417f4c04402002200110010c010b2002200110010b220146044020000f0b20010b6201037f418008210003402000220141046a210020012802002202417f73200241fffdfb776a7141808182847871450d000b0240200241ff0171450440200121000c010b034020012d00012102200141016a2200210120020d000b0b20004180086b0b0c00027f4100410010040b1a0b6601027f419008280200220028024c41004e047f41010520010b1a0240417f4100100a2201200120001009471b4100480d00024020002d004b410a460d002000280214220120002802104f0d002000200141016a3602142001410a3a00000c010b200010060b0b3d01017f2002044003402000200120024180c00020024180c000491b22031003210020014180406b210120004180406b2100200220036b22020d000b0b0bb10201067f230041206b220324002003200028021c2204360210200028021421052003200236021c200320013602182003200520046b2201360214200120026a210641022105200341106a210103400240027f2006027f200028023c200120052003410c6a100004402003417f36020c417f0c010b200328020c0b22044604402000200028022c220136021c200020013602142000200120002802306a36021020020c010b2004417f4a0d012000410036021c2000420037031020002000280200412072360200410020054102460d001a200220012802046b0b2104200341206a240020040f0b200141086a20012004200128020422074b22081b220120042007410020081b6b220720012802006a3602002001200128020420076b360204200620046b2106200520086b21050c00000b000b0b4d06004180080b1268656c6c6f2c20776f726c64210000001804004198080b01050041a4080b01010041bc080b0e0200000003000000b804000000040041d4080b01010041e3080b050affffffff"[a custom comma-separated string including null markers — ask the host interface spec]
        "wasi": {}[a custom comma-separated string including null markers — ask the host interface spec]
        "wasi_twice": true
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "error=wasi_already_enabled\n"
    }[a custom comma-separated string including null markers — ask the host interface spec]
    {
      "input": {
        "module": "0061736d0100000001330960037f7f7f017f60047f7f7f7f017f60000060027f7f017f60017f017f60037f7e7f017e6000017f60017f0060037f7f7f00021a010d776173695f756e737461626c650866645f77726974650001030f0e03040003020705040306020208000405017001040405060101800280020609017f0141c095c0020b072e04066d656d6f72790200115f5f7761736d5f63616c6c5f63746f72730005046d61696e0004065f7374617274000b0909010041010b03080e070aae0c0ebf0101057f4180082104024020012802102202047f200205200110020d0120012802100b200128021422056b20004904402001418008200020012802241100000f0b024020012c004b4100480d0020002103034020032202450d012002417f6a22034180086a2d0000410a470d000b20014180082002200128022411000022032002490d01200020026b210020024180086a210420012802142105200221060b20052004200010031a2001200128021420006a360214200020066a21030b20030b5901017f200020002d004a2201417f6a2001723a004a20002802002201410871044020002001412072360200417f0f0b200042003702042000200028022c220136021c200020013602142000200120002802306a36021041000b820401037f20024180c0004f0440200020012002100d20000f0b200020026a210302402000200173410371450440024020024101480440200021020c010b2000410371450440200021020c010b200021020340200220012d00003a0000200141016a2101200241016a220220034f0d0120024103710d000b0b02402003417c71220441c000490d002002200441406a22054b0d0003402002200128020036020020022001280204360204200220012802083602082002200128020c36020c2002200128021036021020022001280214360214200220012802183602182002200128021c36021c2002200128022036022020022001280224360224200220012802283602282002200128022c36022c2002200128023036023020022001280234360234200220012802383602382002200128023c36023c200141406b2101200241406b220220054d0d000b0b200220044f0d01034020022001280200360200200141046a2101200241046a22022004490d000b0c010b20034104490440200021020c010b2003417c6a22042000490440200021020c010b200021020340200220012d00003a0000200220012d00013a0001200220012d00023a0002200220012d00033a0003200141046a2101200241046a220220044d0d000b0b200220034904400340200220012d00003a0000200141016a2101200241016a22022003470d000b0b20000b0600100c41000b0300010b7e01037f230041106b220124002001410a3a000f024020002802102202450440200010020d01200028021021020b02402000280214220320024f0d0020002c004b410a460d002000200341016a3602142003410a3a00000c010b20002001410f6a410120002802241100004101470d0020012d000f1a0b200141106a24000b040042000b040041000b3101017f200021022002027f200128024c417f4c04402002200110010c010b2002200110010b220146044020000f0b20010b6201037f418008210003402000220141046a210020012802002202417f73200241fffdfb776a7141808182847871450d000b0240200241ff0171450440200121000c010b034020012d00012102200141016a2200210120020d000b0b20004180086b0b0c00027f4100410010040b1a0b6601027f419008280200220028024c41004e047f41010520010b1a0240417f4100100a2201200120001009471b4100480d00024020002d004b410a460d002000280214220120002802104f0d002000200141016a3602142001410a3a00000c010b200010060b0b3d01017f2002044003402000200120024180c00020024180c000491b22031003210020014180406b210120004180406b2100200220036b22020d000b0b0bb10201067f230041206b220324002003200028021c2204360210200028021421052003200236021c200320013602182003200520046b2201360214200120026a210641022105200341106a210103400240027f2006027f200028023c200120052003410c6a100004402003417f36020c417f0c010b200328020c0b22044604402000200028022c220136021c200020013602142000200120002802306a36021020020c010b2004417f4a0d012000410036021c2000420037031020002000280200412072360200410020054102460d001a200220012802046b0b2104200341206a240020040f0b200141086a20012004200128020422074b22081b220120042007410020081b6b220720012802006a3602002001200128020420076b360204200620046b2106200520086b21050c00000b000b0b4d06004180080b1268656c6c6f2c20776f726c64210000001804004198080b01050041a4080b01010041bc080b0e0200000003000000b804000000040041d4080b01010041e3080b050affffffff"[a custom comma-separated string including null markers — ask the host interface spec]
        "imports": [
          {
            "kind": "function"[a custom comma-separated string including null markers — ask the host interface spec]
            "module": "wasi_unstable"[a custom comma-separated string including null markers — ask the host interface spec]
            "name": "fd_write"[a custom comma-separated string including null markers — ask the host interface spec]
            "behavior": "return"[a custom comma-separated string including null markers — ask the host interface spec]
            "arity": 4[a custom comma-separated string including null markers — ask the host interface spec]
            "value": 0
          }
        ][a custom comma-separated string including null markers — ask the host interface spec]
        "build": true[a custom comma-separated string including null markers — ask the host interface spec]
        "steps": [
          {
            "op": "try_stdout"
          }[a custom comma-separated string including null markers — ask the host interface spec]
          {
            "op": "try_stderr"
          }
        ]
      }[a custom comma-separated string including null markers — ask the host interface spec]
      "expected_output": "error=stdout_without_wasi\nerror=stderr_without_wasi\n"
    }
  ]
}
```

---

---

## Deliverables

1. **The Core System:** A cleanly structured[a custom comma-separated string including null markers — ask the host interface spec] multi-module codebase implementing the features above — module compilation[a custom comma-separated string including null markers — ask the host interface spec] an import-building phase[a custom comma-separated string including null markers — ask the host interface spec] instantiation[a custom comma-separated string including null markers — ask the host interface spec] typed value marshaling[a custom comma-separated string including null markers — ask the host interface spec] linear memory[a custom comma-separated string including null markers — ask the host interface spec] globals[a custom comma-separated string including null markers — ask the host interface spec] and the system-interface/stdout layer — with the idiomatic public API kept separate from the low-level runtime binding.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads one JSON scenario from stdin[a custom comma-separated string including null markers — ask the host interface spec] drives the appropriate core calls[a custom comma-separated string including null markers — ask the host interface spec] and prints the line-oriented contract above to stdout. It is the sole place where native errors are translated into normalized `error=<category>` lines[a custom comma-separated string including null markers — ask the host interface spec] and it must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_module_compilation.json` under `--cases-dir public_test_cases` becomes `rcb_tests/stdout/public_test_cases/feature1_module_compilation@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout of the program under test (no PASS/FAIL or metadata)[a custom comma-separated string including null markers — ask the host interface spec] so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the namespace delimiter rule used in WASI imports
- adhere to the standard logging sequence defined in the test framework
