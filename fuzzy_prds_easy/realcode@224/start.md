## Product Requirement Document

# Named Bit-Flag Set Toolkit — Typed Flag Values Over a Fixed-Width Integer

## Project Goal

Build a reusable toolkit for working with **named bit-flag sets**: a value type that wraps a fixed-width unsigned integer and gives meaning to individual bits through named flags, so developers can combine, query, mutate, iterate, format, and parse option-style flags safely instead of juggling raw integers and hand-written bit masks.

---

## Background & Problem

Many programs encode a collection of independent on/off options as bits packed into a single integer (a "bitmask"). Done by hand, this is error-prone: callers must remember which bit means what, write `&`/`|`/`!` expressions correctly, decide what to do with bits that don't correspond to any known option, and reinvent text formatting and parsing every time. There is no shared vocabulary for "does this value contain that flag", "which named flags are set", or "render this value for a log line".

This toolkit provides one well-defined contract for a flag-set value built from a declared list of named flags over a fixed-width integer. It supports constructing values from raw integers under three policies (reject unknown bits, drop unknown bits, or keep them), querying membership and emptiness, the full set algebra (union, intersection, difference, symmetric difference, complement), in-place mutation, decomposition into the contained flags, equality/ordering, numeric and named formatting, a bar-separated text format with matching parsers, and an ordered pattern-classification helper. Throughout, a clear distinction is drawn between **known bits** (those belonging to some declared flag) and **unknown bits** (set bits that no declared flag covers).

All examples in this document operate on an **8-bit** flag set (the underlying integer ranges 0–255). A flag value is identified on the wire purely by its underlying integer (its "bits").

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

## Flag Set Catalog

Every request names a **flag set** via the `set` field. A flag set is a declaration: an ordered list of named flags, each mapping a textual name to a bit pattern within an 8-bit integer. Declaration order matters for listing and decomposition. The toolkit must support the following fixed catalog of 8-bit sets (the names below are display labels used only in formatted output):

- `abc` — three single-bit flags plus one combined flag: `A=1`, `B=2`, `C=4`, `ABC=7` (the union of the first three). Display label `Abc`.
- `abc_inverted` — the same four flags as `abc` but with the combined flag declared **first**: `ABC=7`, then `A=1`, `B=2`, `C=4`. Display label `AbcInverted`.
- `zero` — a single flag whose value is no bits at all: `ZERO=0`. Display label `Zero`.
- `zero_one` — `ZERO=0`, `ONE=1`. Display label `ZeroOne`.
- `unicode` — two single-bit flags with non-ASCII names: `一=1`, `二=2`. Display label `Unicode`.
- `empty` — a set that declares no flags at all. Display label `Empty`.
- `overlapping` — two multi-bit flags that share a bit: `AB=3`, `BC=6`. Display label `Overlapping`.
- `overlapping_full` — three flags that all map to the same single bit, plus one more: `A=1`, `B=1`, `C=1`, `D=2`. Display label `OverlappingFull`.
- `external` — `A=1`, `B=2`, `C=4`, `ABC=7`, plus a **catch-all** flag declared with an empty name covering every bit (`=255`). Because of the catch-all, every bit is a "known" bit in this set. Display label `External`.
- `external_full` — only the catch-all empty-named flag (`=255`). Display label `ExternalFull`.
- `abcd` — four single-bit flags: `A=1`, `B=2`, `C=4`, `D=8`. Display label `Abcd`.

"Known bits" of a set = the union of all its declared flag bit patterns. For `abc` that is `7`; for `zero`/`empty` it is `0`; for `external`/`external_full` it is `255`.

---

## Execution Adapter Contract

The execution adapter reads **one JSON object** from stdin and writes a plain-text result to stdout. The request always carries an `op` (the operation) and, for all operations except classification, a `set` (a catalog id from the list above). Operands are supplied as additional fields:

- `value` — a single flag value, given as its underlying integer (0–255).
- `lhs`, `rhs` — two flag values, each an underlying integer, for binary operations.
- `name` — a textual flag name (for name lookup).
- `text` — a textual flag expression (for parsing).
- `values` — an array of underlying integers (for folding a sequence).

Output rendering conventions, used consistently across features:

- A single flag value is rendered as one line: `bits=<decimal> hex=0x<two-lowercase-hex-digits> bin=<eight-binary-digits>` — e.g. the value `9` renders as `bits=9 hex=0x09 bin=00001001`.
- An optional result is prefixed by an `outcome=some` line (followed by the value line) when a value is produced, or the single line `outcome=none` when none is produced.
- A sequence result begins with a `count=<n>` line, followed by one line per element.
- Errors are rendered as a neutral category line `error=<category>` and never leak any host-language runtime detail.

---

## Core Features

### Feature 1: Constructing Flag Values & Reading Bits

**As a developer**, I want several well-defined ways to turn a raw integer into a typed flag value (and read its bits back), so I can choose how strictly unknown bits are handled.

**Expected Behavior / Usage:**

*1.1 Empty value — the value with no bits set.*

Building the canonical empty value of any set yields underlying bits `0`, regardless of the set's declared flags (including the no-flag set and a set whose catch-all flag would otherwise cover every bit).

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_empty.json`

```json
{
    "description": "Build the canonical empty flag value for a given flag set and read back its underlying bits. The empty value has no bits set, regardless of which flags the set defines, including sets that have no flags at all or a set whose catch-all flag would otherwise cover every bit.",
    "cases": [
        {"input": {"op": "empty", "set": "abc"}, "expected_output": "bits=0 hex=0x00 bin=00000000"}
    ]
}
```

*1.2 All value — every known bit set.*

Building the "all" value yields the union of every declared flag's bits: the ordinary set `abc` gives `7`, a set whose flags declare no bits gives `0`, and a set with a catch-all spanning every bit gives `255`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_all.json`

```json
{
    "description": "Build the value containing every bit that belongs to a defined flag in the set, then read its underlying bits. For an ordinary set this is the union of all declared flag bits; for a set whose only members declare no bits it is empty; for a set carrying a catch-all flag that spans every bit it is the all-ones value.",
    "cases": [
        {"input": {"op": "all", "set": "abc"}, "expected_output": "bits=7 hex=0x07 bin=00000111"},
        {"input": {"op": "all", "set": "external"}, "expected_output": "bits=255 hex=0xff bin=11111111"}
    ]
}
```

*1.3 Read underlying bits — round-tripping an integer.*

Constructing a value from a raw integer while retaining every bit, then reading its bits, returns exactly the input integer (including bits that match no declared flag).

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_bits.json`

```json
{
    "description": "Construct a flag value from a raw integer while retaining every bit (including bits that do not correspond to any defined flag) and read back the stored bits. The stored bits equal the input exactly.",
    "cases": [
        {"input": {"op": "raw_bits", "set": "abc", "value": 1}, "expected_output": "bits=1 hex=0x01 bin=00000001"}
    ]
}
```

*1.4 Checked construction — reject unknown bits.*

A raw integer is validated against the set's known bits: if every set bit belongs to some declared flag, a present value carrying those bits is produced; if any bit falls outside the known flags, no value is produced.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_from_bits.json`

```json
{
    "description": "Validate a raw integer against the set of known flag bits. The result is a present value carrying those bits when every set bit corresponds to a defined flag, or an absent result when any bit falls outside the known flags. A present result reports its bits; an absent result reports that no value was produced.",
    "cases": [
        {"input": {"op": "from_value_checked", "set": "abc", "value": 7}, "expected_output": "outcome=some\nbits=7 hex=0x07 bin=00000111"},
        {"input": {"op": "from_value_checked", "set": "abc", "value": 9}, "expected_output": "outcome=none"}
    ]
}
```

*1.5 Masking construction — drop unknown bits.*

A raw integer is masked down to the set's known bits; bits matching no declared flag are dropped. For `abc`, input `9` (binary `1001`) becomes `1`, and input `8` becomes `0`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_from_bits_truncate.json`

```json
{
    "description": "Construct a flag value from a raw integer, dropping any bits that do not correspond to a defined flag. The stored bits are the input masked down to the known-flag bits.",
    "cases": [
        {"input": {"op": "from_value_masked", "set": "abc", "value": 9}, "expected_output": "bits=1 hex=0x01 bin=00000001"},
        {"input": {"op": "from_value_masked", "set": "abc", "value": 8}, "expected_output": "bits=0 hex=0x00 bin=00000000"}
    ]
}
```

*1.6 Raw construction — keep all bits.*

A raw integer is stored verbatim, retaining bits that match no declared flag. The stored bits equal the input.

**Test Cases:** `rcb_tests/public_test_cases/feature1_6_from_bits_retain.json`

```json
{
    "description": "Construct a flag value from a raw integer, retaining every bit exactly as supplied even when some bits do not correspond to any defined flag. The stored bits equal the input.",
    "cases": [
        {"input": {"op": "from_value_raw", "set": "abc", "value": 8}, "expected_output": "bits=8 hex=0x08 bin=00001000"}
    ]
}
```

*1.7 Lookup by name — single declared flag.*

A textual name is matched, case-sensitively, against the set's declared flag names. A match returns that flag's value; the empty string, an unrecognized name, a hex literal, a multi-flag expression, or a flag declared with an empty name all return no value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_7_from_name.json`

```json
{
    "description": "Look up a single defined flag by its exact textual name. A match returns the value of that flag; lookup is case-sensitive and does not accept expressions, hex literals, the empty string, or names not declared in the set. A flag declared with an empty name is never returned by name lookup.",
    "cases": [
        {"input": {"op": "lookup_name", "set": "abc", "name": "A"}, "expected_output": "outcome=some\nbits=1 hex=0x01 bin=00000001"},
        {"input": {"op": "lookup_name", "set": "abc", "name": "0x1"}, "expected_output": "outcome=none"}
    ]
}
```

---

### Feature 2: Querying Flag Values

**As a developer**, I want to ask boolean questions about a value (emptiness, fullness, membership, overlap, presence of unknown bits), so I can make decisions without manual bit math.

**Expected Behavior / Usage:**

*2.1 Is empty — no bits set.*

Reports whether the value has no bits set at all. Any non-zero value, including one whose only set bits are unknown, is not empty.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_is_empty.json`

```json
{
    "description": "Report whether a flag value has no bits set at all. Any non-zero value, including bits that do not correspond to a defined flag, is not empty.",
    "cases": [
        {"input": {"op": "is_empty", "set": "abc", "value": 0}, "expected_output": "bits=0 is_empty=true"},
        {"input": {"op": "is_empty", "set": "abc", "value": 1}, "expected_output": "bits=1 is_empty=false"}
    ]
}
```

*2.2 Is all — contains every known bit.*

Reports whether the value contains every bit that belongs to a declared flag. Extra unknown bits do not affect the answer; for a set whose known bits are `0`, the empty value contains all flags.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_is_all.json`

```json
{
    "description": "Report whether a flag value contains every bit that belongs to a defined flag. Extra bits outside the known flags do not affect the answer; a set with no flags (or whose flags declare no bits) considers the empty value to contain all flags.",
    "cases": [
        {"input": {"op": "is_all", "set": "abc", "value": 7}, "expected_output": "bits=7 is_all=true"},
        {"input": {"op": "is_all", "set": "abc", "value": 1}, "expected_output": "bits=1 is_all=false"}
    ]
}
```

*2.3 Contains — superset test.*

Reports whether the first value contains all bits of the second. The empty value is contained by everything; a value contains itself; a value does not contain another whose bits are not all present (including unknown bits).

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_contains.json`

```json
{
    "description": "Report whether the first flag value contains all bits of the second. The empty value is contained by everything; a value contains itself; a value does not contain a flag whose bits are not all present, including bits outside the known flags.",
    "cases": [
        {"input": {"op": "contains", "set": "abc", "lhs": 1, "rhs": 0}, "expected_output": "lhs=1 rhs=0 contains=true"},
        {"input": {"op": "contains", "set": "abc", "lhs": 1, "rhs": 1}, "expected_output": "lhs=1 rhs=1 contains=true"}
    ]
}
```

*2.4 Intersects — shared-bit test.*

Reports whether two values share at least one set bit. The empty value intersects nothing; any shared bit (including unknown bits) counts.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_intersects.json`

```json
{
    "description": "Report whether two flag values share at least one set bit. The empty value intersects nothing; values sharing any bit (including bits outside the known flags) intersect.",
    "cases": [
        {"input": {"op": "intersects", "set": "abc", "lhs": 1, "rhs": 1}, "expected_output": "lhs=1 rhs=1 intersects=true"},
        {"input": {"op": "intersects", "set": "abc", "lhs": 1, "rhs": 2}, "expected_output": "lhs=1 rhs=2 intersects=false"}
    ]
}
```

*2.5 Has unknown bits — stray-bit detection.*

Reports whether the value carries any bit that no declared flag covers. Values fully accounted for by known flags report `false`; values with stray bits report `true`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_unknown_bits.json`

```json
{
    "description": "Report whether a flag value carries any bit that does not correspond to a defined flag. Values whose bits are all accounted for by known flags report false; values containing stray bits report true.",
    "cases": [
        {"input": {"op": "has_unknown_bits", "set": "abc", "value": 15}, "expected_output": "bits=15 unknown=true"},
        {"input": {"op": "has_unknown_bits", "set": "abc", "value": 7}, "expected_output": "bits=7 unknown=false"}
    ]
}
```

---

### Feature 3: Set Algebra

**As a developer**, I want the standard set operations on flag values, so I can combine and subtract options declaratively.

**Expected Behavior / Usage:**

*3.1 Union — bits in either operand.*

Produces a value with every bit set in either operand; unknown bits are preserved.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_union.json`

```json
{
    "description": "Combine two flag values, producing a value that has every bit set in either operand. Bits outside the known flags are preserved.",
    "cases": [
        {"input": {"op": "union", "set": "abc", "lhs": 0, "rhs": 7}, "expected_output": "bits=7 hex=0x07 bin=00000111"},
        {"input": {"op": "union", "set": "abc", "lhs": 5, "rhs": 3}, "expected_output": "bits=7 hex=0x07 bin=00000111"}
    ]
}
```

*3.2 Intersection — bits in both operands.*

Produces a value with only the bits set in both operands.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_intersection.json`

```json
{
    "description": "Combine two flag values, producing a value that has only the bits set in both operands.",
    "cases": [
        {"input": {"op": "intersection", "set": "abc", "lhs": 7, "rhs": 1}, "expected_output": "bits=1 hex=0x01 bin=00000001"},
        {"input": {"op": "intersection", "set": "overlapping", "lhs": 3, "rhs": 6}, "expected_output": "bits=2 hex=0x02 bin=00000010"}
    ]
}
```

*3.3 Difference — first minus second.*

Removes from the first value every bit set in the second, keeping the remaining bits of the first (including unknown bits of the first).

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_difference.json`

```json
{
    "description": "Remove from the first flag value every bit that is set in the second, keeping the remaining bits of the first (including bits outside the known flags).",
    "cases": [
        {"input": {"op": "difference", "set": "abc", "lhs": 3, "rhs": 1}, "expected_output": "bits=2 hex=0x02 bin=00000010"},
        {"input": {"op": "difference", "set": "abc", "lhs": 9, "rhs": 1}, "expected_output": "bits=8 hex=0x08 bin=00001000"}
    ]
}
```

*3.4 Symmetric difference — bits in exactly one operand.*

Produces a value with exactly the bits set in one operand but not the other.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_symmetric_difference.json`

```json
{
    "description": "Combine two flag values, producing a value that has exactly the bits set in one operand but not the other.",
    "cases": [
        {"input": {"op": "symmetric_difference", "set": "abc", "lhs": 0, "rhs": 7}, "expected_output": "bits=7 hex=0x07 bin=00000111"},
        {"input": {"op": "symmetric_difference", "set": "abc", "lhs": 11, "rhs": 7}, "expected_output": "bits=12 hex=0x0c bin=00001100"}
    ]
}
```

*3.5 Complement — known bits the value lacks.*

Produces the complement relative to the known bits: the result contains exactly the known-flag bits absent from the input and never contains unknown bits. For a set whose catch-all spans every bit, the complement of empty is the all-ones value.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5_complement.json`

```json
{
    "description": "Produce the complement of a flag value with respect to the known flags: the result contains exactly the known-flag bits that the input lacks, and never contains bits outside the known flags. For a set whose catch-all flag spans every bit, the complement of empty is the all-ones value.",
    "cases": [
        {"input": {"op": "complement", "set": "abc", "value": 4}, "expected_output": "bits=3 hex=0x03 bin=00000011"},
        {"input": {"op": "complement", "set": "external", "value": 0}, "expected_output": "bits=255 hex=0xff bin=11111111"}
    ]
}
```

---

### Feature 4: In-Place Mutation

**As a developer**, I want to add, clear, grow, and clean up bits on a value, returning the updated bits.

**Expected Behavior / Usage:**

*4.1 Insert — add bits.*

Adds the second value's bits into the first; idempotent and preserves unknown bits.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_insert.json`

```json
{
    "description": "Add the bits of the second value into the first, returning the updated bits. Inserting is idempotent and preserves bits outside the known flags.",
    "cases": [
        {"input": {"op": "insert", "set": "abc", "lhs": 0, "rhs": 1}, "expected_output": "bits=1 hex=0x01 bin=00000001"},
        {"input": {"op": "insert", "set": "abc", "lhs": 0, "rhs": 3}, "expected_output": "bits=3 hex=0x03 bin=00000011"}
    ]
}
```

*4.2 Remove — clear bits.*

Clears from the first value every bit present in the second; removing an absent flag leaves the value unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_remove.json`

```json
{
    "description": "Clear from the first value every bit present in the second, returning the updated bits. Removing a flag that is absent leaves the value unchanged.",
    "cases": [
        {"input": {"op": "remove", "set": "abc", "lhs": 7, "rhs": 1}, "expected_output": "bits=6 hex=0x06 bin=00000110"},
        {"input": {"op": "remove", "set": "abc", "lhs": 7, "rhs": 5}, "expected_output": "bits=2 hex=0x02 bin=00000010"}
    ]
}
```

*4.3 Extend — accumulate bits from another value.*

Grows a value by adding all bits of another value into it; accumulates bits and preserves unknown bits.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_extend.json`

```json
{
    "description": "Grow a flag value by adding all bits of another value into it, returning the updated bits. Extending accumulates bits and preserves bits outside the known flags.",
    "cases": [
        {"input": {"op": "extend", "set": "abc", "lhs": 7, "rhs": 32}, "expected_output": "bits=39 hex=0x27 bin=00100111"}
    ]
}
```

*4.4 Clear unknown bits — keep only known bits.*

Drops every bit that no declared flag covers, returning the remaining known-flag bits.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_truncate.json`

```json
{
    "description": "Drop from a flag value every bit that does not correspond to a defined flag, returning the remaining known-flag bits.",
    "cases": [
        {"input": {"op": "clear_unknown", "set": "abc", "value": 15}, "expected_output": "bits=7 hex=0x07 bin=00000111"}
    ]
}
```

---

### Feature 5: Decomposition & Folding

**As a developer**, I want to break a value into its contained flags (with or without names) and to fold a sequence of values into one.

**Expected Behavior / Usage:**

*5.1 Decompose — contained flags as sub-values.*

Yields the contained flags as a sequence of sub-values: each declared flag whose bits are all present is yielded once in declaration order, and any leftover unknown bits are yielded together as a single final element. A combined flag is yielded as one element only when no finer decomposition applies.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_iter.json`

```json
{
    "description": "Enumerate the contained flags of a value as a sequence of sub-values. Each defined flag whose bits are all present is yielded once in declaration order; any leftover bits that do not correspond to a defined flag are yielded together as a final element. A flag whose value is a combination of finer flags is yielded as a single element only when no finer decomposition applies.",
    "cases": [
        {"input": {"op": "decompose", "set": "abc", "value": 11}, "expected_output": "count=3\nbits=1 hex=0x01 bin=00000001\nbits=2 hex=0x02 bin=00000010\nbits=8 hex=0x08 bin=00001000"},
        {"input": {"op": "decompose", "set": "external", "value": 255}, "expected_output": "count=4\nbits=1 hex=0x01 bin=00000001\nbits=2 hex=0x02 bin=00000010\nbits=4 hex=0x04 bin=00000100\nbits=248 hex=0xf8 bin=11111000"}
    ]
}
```

*5.2 Decompose named — contained named flags.*

Yields the contained named flags as `(name, bits)` pairs in declaration order; unknown bits are not reported. When a value matches a combined flag declared before its components, that combined name is reported instead of the components.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_iter_names.json`

```json
{
    "description": "Enumerate the contained, named flags of a value as a sequence of (name, bits) pairs in declaration order. Bits that do not correspond to a defined flag are not reported. When a value matches a combined flag declared before its components, that combined name is reported instead of the components.",
    "cases": [
        {"input": {"op": "decompose_named", "set": "abc", "value": 11}, "expected_output": "count=2\nname=A bits=1\nname=B bits=2"},
        {"input": {"op": "decompose_named", "set": "abc_inverted", "value": 7}, "expected_output": "count=1\nname=ABC bits=7"}
    ]
}
```

*5.3 Union-all — fold a sequence.*

Folds a sequence of values into one by taking their union; an empty sequence yields the empty value and unknown bits are preserved.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_collect.json`

```json
{
    "description": "Fold a sequence of flag values into a single value by taking the union of all of them, returning the combined bits. An empty sequence yields the empty value; bits outside the known flags are preserved.",
    "cases": [
        {"input": {"op": "union_all", "set": "abc", "values": [1, 6]}, "expected_output": "bits=7 hex=0x07 bin=00000111"},
        {"input": {"op": "union_all", "set": "external", "values": [0, 32, 128]}, "expected_output": "bits=160 hex=0xa0 bin=10100000"}
    ]
}
```

---

### Feature 6: Flag Catalog Introspection

**As a developer**, I want to list the flags a set declares, so I can build menus, docs, or validation tables.

**Expected Behavior / Usage:**

Lists the declared flags as `(name, bits)` pairs in declaration order. Combined flags and a catch-all flag declared with an empty name are included; a set with no declared flags lists nothing.

**Test Cases:** `rcb_tests/public_test_cases/feature6_flags_metadata.json`

```json
{
    "description": "List the flags declared by a set as (name, bits) pairs in declaration order. Combined flags and a catch-all flag declared with an empty name are included; a set with no declared flags lists nothing.",
    "cases": [
        {"input": {"op": "catalog", "set": "abc"}, "expected_output": "count=4\nname=A bits=1\nname=B bits=2\nname=C bits=4\nname=ABC bits=7"},
        {"input": {"op": "catalog", "set": "external"}, "expected_output": "count=5\nname=A bits=1\nname=B bits=2\nname=C bits=4\nname=ABC bits=7\nname= bits=255"}
    ]
}
```

---

### Feature 7: Equality & Ordering

**As a developer**, I want to compare two values for equality and order, so I can sort and deduplicate them.

**Expected Behavior / Usage:**

Compares two values: equality holds when both carry the same bits; ordering compares the underlying integer magnitude of the bits.

**Test Cases:** `rcb_tests/public_test_cases/feature7_compare.json`

```json
{
    "description": "Compare two flag values for equality and ordering. Equality holds when both carry the same bits; ordering compares the underlying integer magnitude of the bits.",
    "cases": [
        {"input": {"op": "compare", "set": "abc", "lhs": 1, "rhs": 2}, "expected_output": "eq=false lt=true gt=false"},
        {"input": {"op": "compare", "set": "abc", "lhs": 2, "rhs": 1}, "expected_output": "eq=false lt=false gt=true"}
    ]
}
```

---

### Feature 8: Numeric & Named Formatting

**As a developer**, I want to render a value both as a readable debug string and in common numeric bases.

**Expected Behavior / Usage:**

Renders a value in several forms: a debug form that prefixes the set's display label and lists the contained flag names joined by ` | ` (with any leftover unknown bits shown as a single `0x`-prefixed hex literal, and the empty value shown as `0x0`); and the bare numeric forms of the underlying bits in upper-hex, lower-hex, octal, and binary (no leading zeros, no base prefix). When a value mixes known flags and unknown bits, the debug form lists the names then the hex remainder, e.g. `External(A | B | 0x8)`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_format.json`

```json
{
    "description": "Render a flag value in several textual forms: a debug form that prefixes the set name and lists the contained flag names (with any leftover bits shown as a hex literal, and the empty value shown as a zero hex literal), and the bare numeric forms in upper-hex, lower-hex, octal, and binary of the underlying bits.",
    "cases": [
        {"input": {"op": "format", "set": "abc", "value": 7}, "expected_output": "debug=Abc(A | B | C)\nupper_hex=7\nlower_hex=7\noctal=7\nbinary=111"},
        {"input": {"op": "format", "set": "external", "value": 11}, "expected_output": "debug=External(A | B | 0x8)\nupper_hex=B\nlower_hex=b\noctal=13\nbinary=1011"}
    ]
}
```

---

### Feature 9: Text Serialization

**As a developer**, I want a bar-separated text format for flag values with matching serializers and parsers under three unknown-bit policies, so values survive round-tripping through config files, command lines, and logs.

**Expected Behavior / Usage:**

The text grammar is a sequence of tokens separated by `|`, where each token is either a declared flag name or a `0x`-prefixed hexadecimal literal of the underlying integer; surrounding whitespace around tokens is ignored, and the empty (or all-whitespace) string denotes the empty value. The three policies differ only in how unknown bits are handled: the **retaining** form keeps unknown bits and emits/accepts them as a trailing hex literal; the **masked** form silently drops unknown bits; the **named-only** ("strict") form refuses to emit or accept any hex literal at all.

*9.1 Serialize (retaining).*

Writes contained named flags in declaration order joined by ` | `, then appends any leftover unknown bits as a single `0x`-prefixed hex literal; the empty value serializes to an empty string.

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_to_text.json`

```json
{
    "description": "Serialize a flag value to a bar-separated text form. Contained named flags are written in declaration order joined by ' | '; any leftover bits that do not correspond to a flag are appended as a single '0x'-prefixed hex literal. The empty value serializes to an empty string.",
    "cases": [
        {"input": {"op": "to_text", "set": "abc", "value": 7}, "expected_output": "text=A | B | C"},
        {"input": {"op": "to_text", "set": "abc", "value": 9}, "expected_output": "text=A | 0x8"}
    ]
}
```

*9.2 Parse (retaining).*

Parses the grammar, keeping unknown bits supplied as hex. An unrecognized name yields `error=unrecognized_named_flag`; an unparsable or oversized hex token yields `error=invalid_hex_flag`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_2_from_text.json`

```json
{
    "description": "Parse a flag value from bar-separated text. Tokens are flag names or '0x'-prefixed hex literals separated by '|', surrounding whitespace is ignored, and the empty string parses to the empty value. Unknown bits supplied as hex are retained. An unrecognized name yields an unrecognized-named-flag error and an unparsable or oversized hex token yields an invalid-hex-flag error.",
    "cases": [
        {"input": {"op": "parse", "set": "abc", "text": "0x1 | 0x8 | B"}, "expected_output": "bits=11 hex=0x0b bin=00001011"},
        {"input": {"op": "parse", "set": "unicode", "text": "一 | 二"}, "expected_output": "bits=3 hex=0x03 bin=00000011"}
    ]
}
```

*9.3 Serialize (masked).*

Drops unknown bits first, then writes only known flag names; there is never a trailing hex literal, and an all-unknown value serializes to an empty string.

**Test Cases:** `rcb_tests/public_test_cases/feature9_3_to_text_truncate.json`

```json
{
    "description": "Serialize a flag value to bar-separated text after first dropping any bits that do not correspond to a flag. Only known flag names appear; there is never a trailing hex literal. The empty result is an empty string.",
    "cases": [
        {"input": {"op": "to_text_masked", "set": "abc", "value": 8}, "expected_output": "text="},
        {"input": {"op": "to_text_masked", "set": "abc", "value": 9}, "expected_output": "text=A"}
    ]
}
```

*9.4 Parse (masked).*

Parses the grammar but drops unknown bits supplied via hex literals; names and whitespace behave as in the retaining parse.

**Test Cases:** `rcb_tests/public_test_cases/feature9_4_from_text_truncate.json`

```json
{
    "description": "Parse a flag value from bar-separated text, but drop any bits supplied via hex literals that do not correspond to a flag. Names and whitespace are handled as in the retaining parse; the empty string parses to the empty value.",
    "cases": [
        {"input": {"op": "parse_masked", "set": "abc", "text": "0x8"}, "expected_output": "bits=0 hex=0x00 bin=00000000"},
        {"input": {"op": "parse_masked", "set": "abc", "text": "0x1 | 0x8 | B"}, "expected_output": "bits=3 hex=0x03 bin=00000011"}
    ]
}
```

*9.5 Serialize (named-only).*

Writes only known flag names, dropping unknown bits and never emitting a hex literal; a value whose only set bits are unknown serializes to an empty string.

**Test Cases:** `rcb_tests/public_test_cases/feature9_5_to_text_strict.json`

```json
{
    "description": "Serialize a flag value to bar-separated text using only known flag names, dropping any bits that do not correspond to a flag and never emitting a hex literal. Values whose only set bits are unknown serialize to an empty string.",
    "cases": [
        {"input": {"op": "to_text_named", "set": "abc", "value": 8}, "expected_output": "text="},
        {"input": {"op": "to_text_named", "set": "overlapping", "value": 1}, "expected_output": "text="}
    ]
}
```

*9.6 Parse (named-only).*

Accepts only flag names (and whitespace); any hex literal is rejected. Valid input combines the named flags; an unrecognized name yields `error=unrecognized_named_flag` and any hex token yields `error=invalid_hex_flag`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_6_from_text_strict.json`

```json
{
    "description": "Parse a flag value from bar-separated text accepting only flag names (and whitespace) — hex literals are rejected outright. Valid input combines the named flags; the empty string parses to the empty value. An unrecognized name yields an unrecognized-named-flag error and any hex token yields an invalid-hex-flag error.",
    "cases": [
        {"input": {"op": "parse_named", "set": "abc", "text": "A | B | C"}, "expected_output": "bits=7 hex=0x07 bin=00000111"},
        {"input": {"op": "parse_named", "set": "abc", "text": "0x1"}, "expected_output": "error=invalid_hex_flag"}
    ]
}
```

---

### Feature 10: Ordered Pattern Classification

**As a developer**, I want to classify a value by matching it against an ordered list of flag-combination patterns, returning the label of the first matching pattern, so I can drive branchy logic from a flag value.

**Expected Behavior / Usage:**

The classifier operates over the four single-bit flags `A=1`, `B=2`, `C=4`, `D=8` and evaluates this fixed, ordered list of pattern→label arms, returning the label of the **first** arm whose pattern value equals the input value (equality is by underlying bits); if none match, it returns `Unknown combination`. The arm patterns and labels, in order, are: `A`→`A`; `B`→`B`; `C`→`C`; `D`→`D`; `A | B`→`A or B`; `A & B`→`A and B | empty`; `A ^ B`→`A xor B`; `A | B | C`→`A or B or C`; `A & B & C`→`A and B and C`; `A ^ B ^ C`→`A xor B xor C`; `A | B | C | D`→`All flags`. Because intersection patterns such as `A & B` evaluate to the empty value and appear early in the list, **any** value equal to the empty value (bits `0`) is classified as `A and B | empty`. Similarly, since `A ^ B` (bits `3`) equals `A | B`, a value of `3` matches the earlier `A or B` arm. The result is rendered as `label=<text>`.

**Test Cases:** `rcb_tests/public_test_cases/feature10_match.json`

```json
{
    "description": "Dispatch a flag value through an ordered list of pattern arms, returning the label of the first arm whose pattern equals the value. Patterns are built from flag combinations using union, intersection, and symmetric-difference; because empty-producing patterns appear early, every value that reduces to empty maps to that early arm. A value matching none of the arms maps to a default label.",
    "cases": [
        {"input": {"op": "classify", "value": 8}, "expected_output": "label=D"},
        {"input": {"op": "classify", "value": 0}, "expected_output": "label=A and B | empty"},
        {"input": {"op": "classify", "value": 15}, "expected_output": "label=All flags"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing a named bit-flag set value type over a fixed-width integer, supporting the construction policies, queries, set algebra, mutation, decomposition, comparison, formatting, text serialization, and classification described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O and JSON parsing, and must distinguish known bits from unknown bits consistently.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, selects the named flag set (and operation), drives the appropriate core logic, and prints the plain-text result to stdout, matching the per-leaf-feature contracts above. The adapter is solely responsible for translating native errors into the neutral `error=<category>` lines; the core keeps raising its own idiomatic errors.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follows the formatting style used in the display module
- uses the same default_registry as the router
