## Product Requirement Document

# Compile-Time Checked Builder Generator - Declarative Record Construction Without Boilerplate

## Project Goal

Build a code-generation library that creates type-safe construction APIs for structured records, allowing developers to assemble records fluently while preventing missing required values, duplicate assignments, and invalid hidden-field usage before the program runs.

---

## Background & Problem

Without this library, developers must manually write construction objects, setter methods, default handling, validation, conversion hooks, and finalization logic for every record. This leads to repetitive boilerplate, inconsistent optional-field behavior, and maintenance risks whenever record fields change.

With this library, developers declare field-level and record-level construction behavior once, and the generated construction API enforces valid usage while producing the same record values as handwritten construction code.

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

### Feature 1: Required fields may be supplied in any order

**As a developer**, I want to generate a checked construction interface for this scenario, so I can create records with clear inputs and receive reliable results without handwritten boilerplate.

**Expected Behavior / Usage:**

A record with two required integer fields is constructed only from caller-supplied values; changing the order of supplied fields must not change which final field receives each value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_required_fields_any_order.json`

```json
{
    "description": "A record with two required integer fields is constructed only from caller-supplied values; changing the order of supplied fields must not change which final field receives each value.",
    "cases": [
        {
            "input": {
                "contract": "required_fields",
                "values": {
                    "left": 1,
                    "right": 2
                },
                "order": [
                    "left",
                    "right"
                ]
            },
            "expected_output": "record=Pair\nleft=1\nright=2\n"
        }
    ]
}
```

---

### Feature 2: Borrowed input values are preserved

**As a developer**, I want to generate a checked construction interface for this scenario, so I can create records with clear inputs and receive reliable results without handwritten boilerplate.

**Expected Behavior / Usage:**

A record may contain borrowed input values. Construction preserves the referenced values for fields that use independent or bounded lifetimes.

**Test Cases:** `rcb_tests/public_test_cases/feature2_borrowed_values.json`

```json
{
    "description": "A record may contain borrowed input values. Construction preserves the referenced values for fields that use independent or bounded lifetimes.",
    "cases": [
        {
            "input": {
                "contract": "borrowed_values",
                "values": {
                    "left": 1,
                    "right": 2
                },
                "bounded": false
            },
            "expected_output": "record=BorrowedPair\nleft=1\nright=2\nbounded=false\n"
        }
    ]
}
```

---

### Feature 3: Mutable borrowed fields can be used through the constructed record

**As a developer**, I want to generate a checked construction interface for this scenario, so I can create records with clear inputs and receive reliable results without handwritten boilerplate.

**Expected Behavior / Usage:**

When a record stores mutable borrowed values, mutating through the constructed record changes the original input locations.

**Test Cases:** `rcb_tests/public_test_cases/feature3_mutable_borrows.json`

```json
{
    "description": "When a record stores mutable borrowed values, mutating through the constructed record changes the original input locations.",
    "cases": [
        {
            "input": {
                "contract": "mutable_borrows",
                "initial": {
                    "left": 1,
                    "right": 2
                },
                "multiply": {
                    "left": 10,
                    "right": 100
                }
            },
            "expected_output": "left_after=10\nright_after=200\n"
        }
    ]
}
```

---

### Feature 4: Generic field values are preserved

**As a developer**, I want to generate a checked construction interface for this scenario, so I can create records with clear inputs and receive reliable results without handwritten boilerplate.

**Expected Behavior / Usage:**

A record whose field types are chosen by the caller can be constructed with concrete values and preserves those values in the final record.

**Test Cases:** `rcb_tests/public_test_cases/feature4_generic_fields.json`

```json
{
    "description": "A record whose field types are chosen by the caller can be constructed with concrete values and preserves those values in the final record.",
    "cases": [
        {
            "input": {
                "contract": "generic_fields",
                "values": {
                    "left": 1,
                    "right": 2
                }
            },
            "expected_output": "record=GenericPair\nleft=1\nright=2\n"
        }
    ]
}
```

---

### Feature 5: Inputs may be converted before assignment

**As a developer**, I want to generate a checked construction interface for this scenario, so I can create records with clear inputs and receive reliable results without handwritten boilerplate.

**Expected Behavior / Usage:**

A field can accept a value of a compatible input type and store it as the field type after conversion.

**Test Cases:** `rcb_tests/public_test_cases/feature5_converting_setters.json`

```json
{
    "description": "A field can accept a value of a compatible input type and store it as the field type after conversion.",
    "cases": [
        {
            "input": {
                "contract": "converting_setter",
                "input_value": 1,
                "input_type": "small_unsigned_integer"
            },
            "expected_output": "record=ConvertedValue\nvalue=1\n"
        }
    ]
}
```

---

### Feature 6: Optional fields can accept present values directly

**As a developer**, I want to generate a checked construction interface for this scenario, so I can create records with clear inputs and receive reliable results without handwritten boilerplate.

**Expected Behavior / Usage:**

A caller can provide the present value for an optional field without wrapping it. The constructed record stores the value as present.

**Test Cases:** `rcb_tests/public_test_cases/feature6_optional_value_shorthand.json`

```json
{
    "description": "A caller can provide the present value for an optional field without wrapping it. The constructed record stores the value as present.",
    "cases": [
        {
            "input": {
                "contract": "optional_shorthand",
                "input_value": 1,
                "input_type": "small_unsigned_integer",
                "option_order": "present_then_convert"
            },
            "expected_output": "record=OptionalValue\nvalue=present:1\n"
        }
    ]
}
```

---

### Feature 7: Boolean flags can be enabled without a value

**As a developer**, I want to generate a checked construction interface for this scenario, so I can create records with clear inputs and receive reliable results without handwritten boilerplate.

**Expected Behavior / Usage:**

A boolean field configured as a flag defaults to false and becomes true when the caller includes the flag action.

**Test Cases:** `rcb_tests/public_test_cases/feature7_boolean_flag_shorthand.json`

```json
{
    "description": "A boolean field configured as a flag defaults to false and becomes true when the caller includes the flag action.",
    "cases": [
        {
            "input": {
                "contract": "boolean_flag",
                "enabled": true
            },
            "expected_output": "record=BooleanFlag\nenabled=true\n"
        }
    ]
}
```

---

### Feature 8: Omitted fields can use constant defaults

**As a developer**, I want to generate a checked construction interface for this scenario, so I can create records with clear inputs and receive reliable results without handwritten boilerplate.

**Expected Behavior / Usage:**

Fields marked with defaults are optional during construction. When omitted, they use their configured default values; provided values override only the corresponding fields.

**Test Cases:** `rcb_tests/public_test_cases/feature8_constant_defaults.json`

```json
{
    "description": "Fields marked with defaults are optional during construction. When omitted, they use their configured default values; provided values override only the corresponding fields.",
    "cases": [
        {
            "input": {
                "contract": "constant_defaults",
                "provided": {}
            },
            "expected_output": "record=Defaults\nmaybe=absent\nnumber=10\nitems=[20, 30, 40]\n"
        }
    ]
}
```

---

### Feature 9: Default values may depend on earlier field values

**As a developer**, I want to generate a checked construction interface for this scenario, so I can create records with clear inputs and receive reliable results without handwritten boilerplate.

**Expected Behavior / Usage:**

A default expression for one field may read another field that has already been resolved. If the dependency is overridden, the dependent default reflects the override unless it too is overridden.

**Test Cases:** `rcb_tests/public_test_cases/feature9_dependent_defaults.json`

```json
{
    "description": "A default expression for one field may read another field that has already been resolved. If the dependency is overridden, the dependent default reflects the override unless it too is overridden.",
    "cases": [
        {
            "input": {
                "contract": "dependent_defaults",
                "provided": {}
            },
            "expected_output": "record=DependentDefaults\nmaybe=absent\nnumber=10\nitems=[10, 30, 40]\n"
        }
    ]
}
```

---

### Feature 10: Fields can be omitted from the construction interface

**As a developer**, I want to generate a checked construction interface for this scenario, so I can create records with clear inputs and receive reliable results without handwritten boilerplate.

**Expected Behavior / Usage:**

A field can be intentionally unavailable as a caller input when it has a default. Such fields are still present in the final record and may use defaults that depend on supplied fields.

**Test Cases:** `rcb_tests/public_test_cases/feature10_skipped_fields.json`

```json
{
    "description": "A field can be intentionally unavailable as a caller input when it has a default. Such fields are still present in the final record and may use defaults that depend on supplied fields.",
    "cases": [
        {
            "input": {
                "contract": "skipped_fields",
                "provided": {
                    "visible": 1
                }
            },
            "expected_output": "record=SkippedFields\nhidden_default=0\nvisible=1\ndependent_hidden=2\n"
        }
    ]
}
```

---

### Feature 11: Record-level field policies apply unless overridden

**As a developer**, I want to generate a checked construction interface for this scenario, so I can create records with clear inputs and receive reliable results without handwritten boilerplate.

**Expected Behavior / Usage:**

Default and input-shaping policies can be declared for all fields of a record, while individual fields may opt out or override those policies.

**Test Cases:** `rcb_tests/public_test_cases/feature11_field_default_policies.json`

```json
{
    "description": "Default and input-shaping policies can be declared for all fields of a record, while individual fields may opt out or override those policies.",
    "cases": [
        {
            "input": {
                "contract": "field_default_value_policy",
                "provided": {
                    "required_text": "bla"
                }
            },
            "expected_output": "record=FieldDefaultValues\nfirst=12\nrequired_text=bla\nthird=13\n"
        }
    ]
}
```

---

### Feature 12: Partially configured construction plans can be cloned

**As a developer**, I want to generate a checked construction interface for this scenario, so I can create records with clear inputs and receive reliable results without handwritten boilerplate.

**Expected Behavior / Usage:**

A partially configured construction plan can be copied and completed in different ways as long as the already supplied values support copying.

**Test Cases:** `rcb_tests/public_test_cases/feature12_clone_partial_builder.json`

```json
{
    "description": "A partially configured construction plan can be copied and completed in different ways as long as the already supplied values support copying.",
    "cases": [
        {
            "input": {
                "contract": "clone_partial_builder",
                "seed": 1,
                "branches": [
                    2,
                    3
                ]
            },
            "expected_output": "record=CloneBranch\nbranch=0\nx=1\ny=2\nz=default\nrecord=CloneBranch\nbranch=1\nx=1\ny=3\nz=default\n"
        }
    ]
}
```

---

### Feature 13: Fields whose names are reserved words remain constructible

**As a developer**, I want to generate a checked construction interface for this scenario, so I can create records with clear inputs and receive reliable results without handwritten boilerplate.

**Expected Behavior / Usage:**

A record can include fields whose textual names are reserved by the host language; the generated construction interface still assigns caller-provided and defaulted values correctly.

**Test Cases:** `rcb_tests/public_test_cases/feature13_reserved_words_as_fields.json`

```json
{
    "description": "A record can include fields whose textual names are reserved by the host language; the generated construction interface still assigns caller-provided and defaulted values correctly.",
    "cases": [
        {
            "input": {
                "contract": "reserved_word_fields",
                "provided": {
                    "function_value": 1,
                    "union_text": "two"
                }
            },
            "expected_output": "record=ReservedWords\nfunction_value=1\ntype_value=absent\nenum_value=present:unit\nunion_text=two\n"
        }
    ]
}
```

---

### Feature 14: Field setters can transform multiple inputs into one stored value

**As a developer**, I want to generate a checked construction interface for this scenario, so I can create records with clear inputs and receive reliable results without handwritten boilerplate.

**Expected Behavior / Usage:**

A field may be assigned by a transformation that accepts multiple caller values and stores one composite value in the constructed record.

**Test Cases:** `rcb_tests/public_test_cases/feature14_transformed_field_input.json`

```json
{
    "description": "A field may be assigned by a transformation that accepts multiple caller values and stores one composite value in the constructed record.",
    "cases": [
        {
            "input": {
                "contract": "transformed_field",
                "point": {
                    "x": 1,
                    "y": 2
                }
            },
            "expected_output": "record=TransformedField\npoint.x=1\npoint.y=2\n"
        }
    ]
}
```

---

### Feature 15: Construction entry points, finalization names, and output conversion can be customized

**As a developer**, I want to generate a checked construction interface for this scenario, so I can create records with clear inputs and receive reliable results without handwritten boilerplate.

**Expected Behavior / Usage:**

The generated construction API can expose custom names for starting construction, completing construction, or naming the construction-plan type. A completed inner record may also be converted into an enclosing output type.

**Test Cases:** `rcb_tests/public_test_cases/feature15_customized_entrypoints_and_outputs.json`

```json
{
    "description": "The generated construction API can expose custom names for starting construction, completing construction, or naming the construction-plan type. A completed inner record may also be converted into an enclosing output type.",
    "cases": [
        {
            "input": {
                "contract": "custom_finalize_name",
                "provided": {
                    "value": 1
                }
            },
            "expected_output": "record=CustomFinalize\nvalue=1\n"
        },
        {
            "input": {
                "contract": "custom_start_name",
                "provided": {
                    "value": 1
                }
            },
            "expected_output": "record=CustomStart\nvalue=1\n"
        }
    ]
}
```

---

### Feature 16: Invalid construction attempts are rejected before execution

**As a developer**, I want to generate a checked construction interface for this scenario, so I can create records with clear inputs and receive reliable results without handwritten boilerplate.

**Expected Behavior / Usage:**

The construction API rejects invalid programs such as supplying a hidden field, defining a hidden field without a default, or copying a partially configured plan that contains a non-copyable value. Errors are reported as normalized contract categories.

**Test Cases:** `rcb_tests/public_test_cases/feature16_compile_time_rejections.json`

```json
{
    "description": "The construction API rejects invalid programs such as supplying a hidden field, defining a hidden field without a default, or copying a partially configured plan that contains a non-copyable value. Errors are reported as normalized contract categories.",
    "cases": [
        {
            "input": {
                "contract": "compile_rejection",
                "invalid_action": "set_hidden_field"
            },
            "expected_output": "error=hidden_field_not_settable\nfield=hidden\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
