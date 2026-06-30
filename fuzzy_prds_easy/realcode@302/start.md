## Product Requirement Document

# Runtime Value Type System — Type Classification & Coercion Contract

## Project Goal

Build a runtime value type-system library that lets developers inspect and convert dynamically-typed values through one small, uniform interface. Given any runtime value, a developer can ask "what type is this?" against a fixed catalogue of categories, and can convert that value into a boolean, a number, a string, or an object using well-defined coercion rules — without hand-writing the per-type branching, special cases, and edge-case handling every time.

---

## Background & Problem

Dynamically-typed values arrive at a boundary (an external call, a parsed payload, a host runtime) with no static guarantee of their shape. Without a shared type-system layer, developers are forced to re-implement ad-hoc `typeof`-style ladders, hand-roll "is this an array vs. a typed array vs. a plain object" checks, and re-derive coercion rules (truthiness, numeric parsing, string rendering, object boxing) at every call site. This produces repetitive, subtly-inconsistent boilerplate where one site treats an empty array as `0`, another forgets that a typed array is also an object, and a third mishandles `undefined` vs. `null`.

With this library, every value flows through one classifier that reports a complete, consistent type profile, and through one coercion surface whose rules are fixed and documented. Callers get the same answers everywhere, edge cases are handled once, and the behavior is specified as a black-box input/output contract rather than buried in scattered conditionals.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain is a focused type-system surface (a classifier plus a small set of coercions); a clean, logically separated module is acceptable, but the type-classification logic, the coercion logic, and the execution/output adapter MUST remain distinct logical units. Do not over-engineer, but do not collapse everything into one undifferentiated script.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box testing contract** for the execution adapter, NOT the internal data model of the core type system. The core classification/coercion logic must remain completely decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls to the core and for rendering the line-based output.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Separate value construction, type classification, value coercion, and output formatting.
   - **Open/Closed Principle (OCP):** Adding a new type category or coercion target must not require rewriting existing classifiers.
   - **Liskov Substitution Principle (LSP):** Any value handled by the classifier must be handled uniformly by the coercion surface where the contract defines a result.
   - **Interface Segregation Principle (ISP):** Keep the classifier interface and the coercion interface small and cohesive.
   - **Dependency Inversion Principle (DIP):** The core must not depend on the I/O adapter; the adapter depends on the core.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface must be elegant and idiomatic to the target language.
   - **Resilience:** Unsupported or malformed commands must be handled gracefully and rendered as a neutral error category, never as a host-language runtime fault leaking through stdout.

---

## Core Features

A single execution adapter reads one JSON command object from stdin and prints a line-based result to stdout. Every command has the shape:

```json
{ "op": "<operation>", "value": { "kind": "<value-kind>", ... } }
```

`op` selects the behavior (`classify`, `coerce_primitive`, or `box`). `value` describes the runtime value to construct, using a neutral, language-agnostic tag:

- `{"kind": "undefined"}` — the absent/undefined value
- `{"kind": "null"}` — the null value
- `{"kind": "boolean", "data": true|false}`
- `{"kind": "number", "data": <number>}`
- `{"kind": "string", "data": "<text>"}`
- `{"kind": "symbol", "data": "<text>"}` — a unique symbolic value
- `{"kind": "array"}` — an empty ordered list
- `{"kind": "arraybuffer", "byteLength": <n>}` — a raw binary buffer of `n` bytes
- `{"kind": "typedarray", "byteLength": <n>}` — a 32-bit signed integer view over an `n`-byte zero-filled buffer
- `{"kind": "object"}` — an empty plain key/value object
- `{"kind": "function"}` — a callable value with source `function () {}`
- `{"kind": "promise"}` — a pending asynchronous result
- `{"kind": "dataview", "byteLength": <n>}` — a byte-addressable view over an `n`-byte buffer

Each leaf feature below is fully specified by its prose plus its embedded cases.

---

### Feature 1: Runtime Value Type Classification

**As a developer**, I want to classify any runtime value against a complete catalogue of type categories in one call, so I can branch on a value's shape without writing my own type-detection ladder.

**Expected Behavior / Usage:**

For `op = "classify"`, the adapter constructs the described value and reports, for every category in this fixed order, whether the value belongs to that category. Output is one `<category>=<true|false>` line per category, in this exact order: `undefined`, `null`, `boolean`, `number`, `string`, `symbol`, `array`, `arraybuffer`, `typedarray`, `object`, `function`, `promise`, `dataview`.

The categories are mostly mutually exclusive: a primitive matches exactly one of `undefined`/`null`/`boolean`/`number`/`string`/`symbol` and nothing else. The `object` category is the general structural test and is intentionally broad: it reports `true` for any value that is structurally an object — arrays, raw buffers, typed arrays, plain objects, functions, promises, and byte views all report `object=true` in addition to their specific category. A function therefore reports both `function=true` and `object=true`; an array reports both `array=true` and `object=true`. The `null` value is NOT an object (`object=false`). A typed array and a byte view are distinct categories: a typed array reports `typedarray=true` but `dataview=false`, while a byte view reports `dataview=true` but `typedarray=false`; neither reports `arraybuffer=true` even though both are backed by a buffer.

**Test Cases:** `rcb_tests/public_test_cases/feature1_type_classification.json`

```json
{
  "description": "Classify a runtime value against every primitive and object type predicate; for each input exactly the matching category (plus the generic object category for non-null objects, arrays, typed arrays, functions, promises, etc.) reports true and all others report false.",
  "cases": [
    {
      "input": {
        "op": "classify",
        "value": {
          "kind": "undefined"
        }
      },
      "expected_output": "undefined=true\nnull=false\nboolean=false\nnumber=false\nstring=false\nsymbol=false\narray=false\narraybuffer=false\ntypedarray=false\nobject=false\nfunction=false\npromise=false\ndataview=false\n"
    },
    {
      "input": {
        "op": "classify",
        "value": {
          "kind": "boolean",
          "data": true
        }
      },
      "expected_output": "undefined=false\nnull=false\nboolean=true\nnumber=false\nstring=false\nsymbol=false\narray=false\narraybuffer=false\ntypedarray=false\nobject=false\nfunction=false\npromise=false\ndataview=false\n"
    },
    {
      "input": {
        "op": "classify",
        "value": {
          "kind": "array"
        }
      },
      "expected_output": "undefined=false\nnull=false\nboolean=false\nnumber=false\nstring=false\nsymbol=false\narray=true\narraybuffer=false\ntypedarray=false\nobject=true\nfunction=false\npromise=false\ndataview=false\n"
    },
    {
      "input": {
        "op": "classify",
        "value": {
          "kind": "function"
        }
      },
      "expected_output": "undefined=false\nnull=false\nboolean=false\nnumber=false\nstring=false\nsymbol=false\narray=false\narraybuffer=false\ntypedarray=false\nobject=true\nfunction=true\npromise=false\ndataview=false\n"
    },
    {
      "input": {
        "op": "classify",
        "value": {
          "kind": "dataview",
          "byteLength": 12
        }
      },
      "expected_output": "undefined=false\nnull=false\nboolean=false\nnumber=false\nstring=false\nsymbol=false\narray=false\narraybuffer=false\ntypedarray=false\nobject=true\nfunction=false\npromise=false\ndataview=true\n"
    }
  ]
}
```

---

### Feature 2: Primitive Coercion (boolean / number / string)

**As a developer**, I want to coerce any runtime value into a boolean, a number, and a string with one call, so I can normalize untrusted values without memorizing each coercion's edge cases.

**Expected Behavior / Usage:**

For `op = "coerce_primitive"`, the adapter constructs the described value and emits exactly three lines: `boolean=<r>`, `number=<r>`, `string=<r>`.

Boolean coercion follows truthiness: `undefined`, `null`, `false`, the number `0`, and the empty string are falsey; every non-empty container, function, promise, buffer, and any non-zero number is truthy.

Number coercion: `undefined` becomes the not-a-number sentinel rendered as `NaN`; `null` becomes `0`; `false`/`0` become `0`; `true` becomes `1`; a numeric string parses to its value while a non-numeric string becomes `NaN`; an empty list becomes `0`; objects, functions, promises, raw buffers, and typed views that have no numeric representation become `NaN`.

String coercion renders the value's textual form: `undefined` → `undefined`, `null` → `null`, booleans → `true`/`false`, numbers → their decimal text, a string → itself, an empty list → the empty string, a typed integer view over a 12-byte zero buffer → `0,0,0`, a raw buffer → `[object ArrayBuffer]`, a plain object → `[object Object]`, a pending async result → `[object Promise]`, and a function → its source text `function () {}`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_primitive_coercion.json`

```json
{
  "description": "Coerce a runtime value simultaneously to a truthiness boolean, to a number (NaN when not numerically representable), and to its string form, returning all three coercions for one input.",
  "cases": [
    {
      "input": {
        "op": "coerce_primitive",
        "value": {
          "kind": "undefined"
        }
      },
      "expected_output": "boolean=false\nnumber=NaN\nstring=undefined\n"
    },
    {
      "input": {
        "op": "coerce_primitive",
        "value": {
          "kind": "null"
        }
      },
      "expected_output": "boolean=false\nnumber=0\nstring=null\n"
    },
    {
      "input": {
        "op": "coerce_primitive",
        "value": {
          "kind": "boolean",
          "data": true
        }
      },
      "expected_output": "boolean=true\nnumber=1\nstring=true\n"
    },
    {
      "input": {
        "op": "coerce_primitive",
        "value": {
          "kind": "number",
          "data": 10
        }
      },
      "expected_output": "boolean=true\nnumber=10\nstring=10\n"
    },
    {
      "input": {
        "op": "coerce_primitive",
        "value": {
          "kind": "array"
        }
      },
      "expected_output": "boolean=true\nnumber=0\nstring=\n"
    },
    {
      "input": {
        "op": "coerce_primitive",
        "value": {
          "kind": "function"
        }
      },
      "expected_output": "boolean=true\nnumber=NaN\nstring=function () {}\n"
    }
  ]
}
```

---

### Feature 3: Object Boxing

**As a developer**, I want to convert any value into an object form, so I can treat primitives and objects uniformly while still preserving the identity of values that are already objects.

**Expected Behavior / Usage:**

For `op = "box"`, the adapter constructs the described value, converts it to its object form, and emits `same_reference=<true|false>` followed by `result_typeof=<object|function>`; for primitive inputs it additionally emits `unwrapped=<value>`.

A primitive input (boolean, number, string) is wrapped into a fresh object: the result is therefore NOT the same reference as the input (`same_reference=false`), its structural type is `object` (`result_typeof=object`), and the `unwrapped` line shows that the wrapper still carries the original primitive value (e.g. boxing the number `10` yields `unwrapped=10`; boxing the string `string` yields `unwrapped=string`).

A value that is already an object is returned as the very same reference (`same_reference=true`) and no `unwrapped` line is emitted. Plain objects, arrays, buffers, typed views, and promises report `result_typeof=object`; a callable value preserves its callable nature and reports `result_typeof=function` while still being the same reference.

**Test Cases:** `rcb_tests/public_test_cases/feature3_object_boxing.json`

```json
{
  "description": "Convert a runtime value to an object: primitives are boxed into a fresh wrapper object whose unwrapped value equals the original primitive, while values that are already objects (including functions) are returned as the very same reference.",
  "cases": [
    {
      "input": {
        "op": "box",
        "value": {
          "kind": "number",
          "data": 10
        }
      },
      "expected_output": "same_reference=false\nresult_typeof=object\nunwrapped=10\n"
    },
    {
      "input": {
        "op": "box",
        "value": {
          "kind": "string",
          "data": "string"
        }
      },
      "expected_output": "same_reference=false\nresult_typeof=object\nunwrapped=string\n"
    },
    {
      "input": {
        "op": "box",
        "value": {
          "kind": "object"
        }
      },
      "expected_output": "same_reference=true\nresult_typeof=object\n"
    },
    {
      "input": {
        "op": "box",
        "value": {
          "kind": "function"
        }
      },
      "expected_output": "same_reference=true\nresult_typeof=function\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the type classifier and the coercion surface described above, with the classification logic, coercion logic, and output formatting kept as distinct logical units. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint — focused and maintainable, not a monolithic god-file and not over-engineered.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads one JSON command from stdin, constructs the described value, invokes the appropriate core logic (`classify`, `coerce_primitive`, or `box`), and prints the line-based result to stdout, strictly matching the per-feature contracts above. Any malformed or unsupported command is rendered as a neutral `error=<category>` line; no host-language exception type, stack trace, or runtime message suffix may appear in stdout. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_type_classification.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_type_classification@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- adopt the unpacking strategy seen in the stream abstract class
