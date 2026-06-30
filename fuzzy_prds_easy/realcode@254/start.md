## Product Requirement Document

# Compile-Time Sequence Toolkit - Type and Value Metaprogramming Contracts

## Project Goal

Build a compile-time sequence toolkit that allows developers to describe, inspect, transform, search, reduce, sort, and associate types or integral constants at compile time without writing repetitive template boilerplate by hand.

---

## Background & Problem

Without this library, developers are forced to encode type lists, integral-constant lists, type-to-type associations, and sequence algorithms manually. This leads to duplicated template code, fragile special cases for empty or single-element sequences, and hard-to-maintain compile-time logic.

With this library, developers can express common compile-time data-structure and algorithm operations through a compact, declarative interface and receive deterministic type or value results that can be checked at compile time.

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

### Feature 1: Type Sequence Access

**As a developer**, I want to inspect and combine ordered sequences of types, so I can build compile-time type pipelines without manually unpacking each position.

**Expected Behavior / Usage:**

Given an ordered sequence of type identifiers, the system reports its length, first type, last type, or the type at a zero-based index. It can also remove the first or last type and concatenate another ordered type sequence. The output is one line per requested observation, using stable textual type identifiers and ordered bracket notation for sequence results.

**Test Cases:** `rcb_tests/public_test_cases/feature1_type_sequence_access.json`

```json
{
    "description": "Observes the size and boundary elements of a sequence of types without constructing runtime objects.",
    "cases": [
        {
            "input": {"task":"type_sequence_observe","items":["int","bool"],"observe":["size","front","back"]},
            "expected_output": "size=2\nfront=int\nback=bool\n"
        }
    ]
}
```

---

### Feature 2: Integral Value Sequence Access

**As a developer**, I want to inspect and combine ordered sequences of integral constants, so I can express compile-time numeric data without runtime arrays.

**Expected Behavior / Usage:**

Given an ordered sequence of integral constants, the system reports its length, first value, last value, or the value at a zero-based index. It can remove either end of the sequence and concatenate another integral sequence while preserving order. The output uses decimal values and ordered bracket notation.

**Test Cases:** `rcb_tests/public_test_cases/feature2_value_sequence_access.json`

```json
{
    "description": "Observes the size, boundary values, indexed values, and concatenation behavior of a sequence of integral constants.",
    "cases": [
        {
            "input": {"task":"value_sequence_observe","value_type":"uint32","values":[42,69],"observe":["size","front","back"]},
            "expected_output": "size=2\nfront=42\nback=69\n"
        }
    ]
}
```

---

### Feature 3: Integer Range Generation

**As a developer**, I want to generate integer sequences from bounds, so I can derive compile-time value lists from compact numeric intervals.

**Expected Behavior / Usage:**

Given a start bound, stop bound, and direction, the system returns the generated sequence. Forward generation is half-open and includes `start` while excluding `stop`. Reverse generation counts down from `start` while excluding `stop`. Equal bounds produce an empty sequence.

**Test Cases:** `rcb_tests/public_test_cases/feature3_range_generation.json`

```json
{
    "description": "Generates forward half-open integer ranges and reverse countdown ranges as value sequences.",
    "cases": [
        {
            "input": {"task":"range_values","direction":"forward","start":0,"stop":3},
            "expected_output": "sequence=[0,1,2]\n"
        }
    ]
}
```

---

### Feature 4: Iterative Sequence Generation

**As a developer**, I want to generate a fixed-length sequence by repeatedly stepping from a starting value, so I can model compile-time counters and countdowns.

**Expected Behavior / Usage:**

Given a starting value, a count, and a one-step operation, the system emits exactly `count` values. The first output value is the start value; each subsequent value is produced by applying the step operation once to the previous value. Supported observed steps are increment and decrement.

**Test Cases:** `rcb_tests/public_test_cases/feature4_iterative_sequence_generation.json`

```json
{
    "description": "Generates a fixed number of values by repeatedly applying a one-step increment or decrement operation from a starting value.",
    "cases": [
        {
            "input": {"task":"iterative_values","start":0,"count":3,"step":"next"},
            "expected_output": "sequence=[0,1,2]\n"
        }
    ]
}
```

---

### Feature 5: Sequence Transformation

**As a developer**, I want to transform every item in a sequence, so I can derive new compile-time sequences from existing type or value data.

**Expected Behavior / Usage:**

Given a sequence and a supported transformation, the system returns a sequence of the same length with each item transformed in order. Observed transformations include adding a pointer layer to each type, pairing each type with the type at the same position in another sequence, adding a constant to each integer value, and subtracting each integer value from a constant.

**Test Cases:** `rcb_tests/public_test_cases/feature5_transform_sequences.json`

```json
{
    "description": "Transforms each element of one or two input sequences while preserving order and sequence length.",
    "cases": [
        {
            "input": {"task":"transform_items","transformation":"add_pointer","items":["[a specific substring keyword — ask the PM for the exact substring requirement]","double","int","char","void*"]},
            "expected_output": "sequence=[[a specific substring keyword — ask the PM for the exact substring requirement]*,double*,int*,char*,void**]\n"
        }
    ]
}
```

---

### Feature 6: Sequence Search

**As a developer**, I want to locate matching items in type or value sequences, so I can split compile-time data at the first or last meaningful position.

**Expected Behavior / Usage:**

For type sequences, the observed predicate matches [a specific substring keyword — ask the PM for the exact substring requirement]ing-point types. A forward scan returns whether a match exists and the suffix beginning at the first match. A reverse scan returns whether a match exists and the prefix ending at the last match. For value sequences, zero is treated as non-matching and any non-zero value is treated as matching. If no match exists, the returned sequence is empty and `found=no`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_search_sequences.json`

```json
{
    "description": "Searches type and value sequences and returns the suffix or prefix located at the first or last matching element.",
    "cases": [
        {
            "input": {"task":"find_match","items":["int","int","int","[a specific substring keyword — ask the PM for the exact substring requirement]","char"],"scan":"forward"},
            "expected_output": "found=yes\nmatched_suffix=[[a specific substring keyword — ask the PM for the exact substring requirement],char]\n"
        }
    ]
}
```

---

### Feature 7: Sequence Reduction

**As a developer**, I want to fold a sequence from left to right with an initial state, so I can compute compile-time aggregate values.

**Expected Behavior / Usage:**

Given an initial value and a reduction rule, the system processes the sequence in order and prints the final state. Observed reductions include counting [a specific substring keyword — ask the PM for the exact substring requirement]ing-point types, summing integer constants, and an order-sensitive rule that adds odd elements and multiplies by even elements.

**Test Cases:** `rcb_tests/public_test_cases/feature7_reduce_sequences.json`

```json
{
    "description": "Reduces a sequence from left to right using a supplied initial value and operation.",
    "cases": [
        {
            "input": {"task":"reduce_items","reduction":"count_[a specific substring keyword — ask the PM for the exact substring requirement]ing","items":["int","[a specific substring keyword — ask the PM for the exact substring requirement]","double","long","char","[a specific substring keyword — ask the PM for the exact substring requirement]"],"initial":0},
            "expected_output": "result=3\n"
        }
    ]
}
```

---

### Feature 8: Sequence Ordering

**As a developer**, I want to order value and type sequences, so I can canonicalize compile-time data before further processing.

**Expected Behavior / Usage:**

Given a numeric value sequence, the system returns the same values ordered ascending or descending while preserving duplicates. Given a type sequence with a type-size ordering rule, the system returns the types ordered from smallest to largest size according to the target platform's ordinary scalar type sizes used by the test adapter.

**Test Cases:** `rcb_tests/public_test_cases/feature8_sort_sequences.json`

```json
{
    "description": "Orders value sequences by numeric comparison and type sequences by a caller-provided type-size ordering.",
    "cases": [
        {
            "input": {"task":"order_items","values":[3,7,5,2,1,1,4],"order":"ascending"},
            "expected_output": "sequence=[1,1,2,3,4,5,7]\n"
        }
    ]
}
```

---

### Feature 9: Keyed Type Association

**As a developer**, I want to associate key types with value types, so I can perform compile-time lookups and build type-indexed tables.

**Expected Behavior / Usage:**

Given a list of key/value type pairs, the system reports the number of stored pairs and can look up a key. A present key prints `lookup=<key>:<value>`; a missing key prints `lookup=<key>:missing`. Inserting a new key appends it to the association set, while inserting an already-present key leaves the key set unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature9_keyed_type_association.json`

```json
{
    "description": "Stores compile-time associations from key types to value types and supports lookup plus idempotent insertion.",
    "cases": [
        {
            "input": {"task":"keyed_lookup","pairs":[["int","bool"],["char","int"]],"lookup":"int"},
            "expected_output": "size=2\nlookup=int:bool\n"
        }
    ]
}
```

---

### Feature 10: Unique Type Membership

**As a developer**, I want to represent a unique set of types, so I can test membership and update compile-time sets without duplicates.

**Expected Behavior / Usage:**

Given a set of type identifiers, the system reports its size and can test whether a queried type is present. Inserting an absent type adds it at the end of the rendered set; inserting a present type leaves the rendered set unchanged. Erasing a present type removes it, while erasing an absent type leaves the set unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature10_unique_type_membership.json`

```json
{
    "description": "Represents a compile-time set of unique types and supports membership queries, insertion, and removal.",
    "cases": [
        {
            "input": {"task":"unique_membership","items":["int","char"],"contains":"int"},
            "expected_output": "size=2\ncontains=int:yes\n"
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
- apply the inverse logic of the sum reduction rule
- follow the same marker convention as the add_const transformation
