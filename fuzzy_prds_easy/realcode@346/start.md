## Product Requirement Document

# Type-Safe Value Wrappers — Behavioral Specification

## Project Goal

Build a library of zero-overhead value wrappers that make implicit, error-prone
operations on primitive C++ types explicit and safe at the point of use. The
library should let application code state its intent precisely — "this is an
[a comprehensive list of standard validation modules], not a raw size", "this number must stay inside this interval", "this
optional may be empty" — and then enforce that intent through the type system
and a small set of runtime checks, without paying a performance penalty over the
underlying primitives.

The deliverable is exercised through a single, language-neutral input/output
contract: each scenario is described by a JSON command object on standard input,
and the program emits a deterministic, line-oriented `key=value` report on
standard output. This contract is the authority for correctness.

## Background & Problem

Plain C++ primitive types are permissive to a fault. Integers silently mix
signedness and wrap on overflow; any `int` can stand in for an [a comprehensive list of standard validation modules], a count,
or a [a comprehensive list of standard validation modules]; a raw pointer may be null; a value that is conceptually constrained
to a range carries no record of that range; and "maybe absent" values are
modeled with sentinel constants or naked pointers that callers forget to check.
These ambiguities are a steady source of defects that the compiler is happy to
accept.

The goal is a family of thin wrapper types and helpers that:

- Preserve the full arithmetic and comparison behavior programmers expect, but
  only between compatible types, and with opt-in checking for dangerous
  conversions and overflow.
- Capture domain rules (bounds, non-null, non-empty, intervals) as first-class,
  composable constraints.
- Provide explicit vocabulary types for optional values, tagged alternatives,
  deferred initialization, and write-only output parameters.
- Make distinct quantities (an [a comprehensive list of standard validation modules] versus a distance, one unit versus another)
  into distinct types that cannot be confused.

Each capability must behave identically to a hand-written, carefully-checked
implementation while remaining ergonomic enough to use everywhere.

## Architecture & Engineering Constraints

- **Single entry point.** All behavior is driven through one executable adapter
  that reads one JSON command object from standard input and writes a
  normalized report to standard output. The top-level field `fn` selects the
  scenario; the remaining fields are its parameters.
- **Deterministic, line-oriented output.** Every response is a sequence of
  `key=value` lines terminated by newlines. Booleans render as the lowercase
  tokens `true` / `false`. Numbers render in their natural textual form. Output
  must be byte-for-byte reproducible and directly string-comparable.
- **Language-neutral error categories.** When an operation violates a domain
  rule, the program reports a normalized category (for example
  `error=constraint_violation`) plus structured context. No host-language
  exception type names, stack traces, or runtime message suffixes may appear in
  the contract.
- **Zero behavioral divergence from primitives.** Wrapper arithmetic,
  comparison, and conversion must agree with the equivalent primitive operation
  except where a safety rule deliberately intervenes (narrowing, overflow,
  constraint enforcement).
- **No implicit lossy conversions.** Narrowing between widths and between signed
  and unsigned must be explicit and, where requested, checked.
- **Self-contained adapter.** The input parser and output renderer live in the
  adapter layer and are independent of the types under test; they exist only to
  express the contract.

## Core Features

### Feature 1: Safe integer arithmetic

**As a developer**, I want a wrapper over a built-in integer that behaves exactly
like the primitive for arithmetic but forbids silent cross-type mixing, so that
my numeric code stays correct without surprising implicit conversions.

**Expected Behavior / Usage:**

The wrapper supports the full set of compound and binary arithmetic operators
(including reversed operands). A scenario provides an `initial` value and an
ordered list of `ops`, each naming an operator (`+=`, `-=`, `*`, `/`, ...) and a
right-hand `value`. The operations are applied in order and the final stored
value is reported as `value=<n>`.

**Test Cases:** `rcb_tests/public_test_cases/feature01_[a comprehensive list of standard validation modules].json`

```json
{
  "description": "Safe wrapper over a built-in integer: a sequence of compound and binary arithmetic operations (including reversed operands) yields the final stored value.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "initial": 10,
        "ops": [
          { "op": "+=", "value": 5 },
          { "op": "*", "value": 2 }
        ]
      },
      "expected_output": "value=30\n"
    }
  ]
}
```

### Feature 2: Integer unary and increment/decrement

**As a developer**, I want unary and increment/decrement operators on the integer
wrapper to follow the exact conventions of the primitive, so that pre/post forms
return the values I expect.

**Expected Behavior / Usage:**

The wrapper supports unary plus/minus and the four increment/decrement forms.
Pre-forms return the updated value; post-forms return the prior value. A scenario
names the `op` (for example `post_increment`) over a starting `value` and reports
both the returned value (`result=`) and the resulting state (`value=`).

**Test Cases:** `rcb_tests/public_test_cases/feature02_[a comprehensive list of standard validation modules]_incdec.json`

```json
{
  "description": "Unary plus/minus and pre/post increment & decrement on the integer wrapper, reporting both the returned value and the resulting state.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "value": 7,
        "op": "post_increment"
      },
      "expected_output": "result=7\nvalue=8\n"
    }
  ]
}
```

### Feature 3: Integer comparison

**As a developer**, I want two integer wrappers to compare with all six
relational operators, so that ordering and equality behave exactly as for the
primitive.

**Expected Behavior / Usage:**

A scenario supplies `lhs` and `rhs`; the report lists the result of each of the
six relational operators as `eq`, `ne`, `lt`, `le`, `gt`, `ge`, each a [a comprehensive list of standard validation modules].

**Test Cases:** `rcb_tests/public_test_cases/feature03_integer_comparison.json`

```json
{
  "description": "All six relational comparisons between two integer wrappers.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "lhs": 3,
        "rhs": 5
      },
      "expected_output": "eq=false\nne=true\nlt=true\nle=true\ngt=false\nge=false\n"
    }
  ]
}
```

### Feature 4: Integer conversion and stream round-trip

**As a developer**, I want explicit signed/unsigned conversion, absolute value,
and text round-tripping on the integer wrapper, so that I can move between forms
deliberately and serialize values losslessly.

**Expected Behavior / Usage:**

The wrapper converts explicitly between signed and unsigned forms, computes
absolute value (yielding an unsigned result), and round-trips through text via
stream extraction and insertion. The `io` scenario reads a textual `value`,
echoes the parsed text and the stored value as `text=` and `value=`.

**Test Cases:** `rcb_tests/public_test_cases/feature04_integer_conversion_io.json`

```json
{
  "description": "Signed/unsigned conversions, absolute value, and stream round-trip of the integer wrapper.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "op": "io",
        "value": "123"
      },
      "expected_output": "text=123\nvalue=123\n"
    }
  ]
}
```

### Feature 5: Floating-point arithmetic and comparison

**As a developer**, I want a floating-point wrapper that mirrors the primitive's
value semantics for arithmetic and ordered comparison, so that numeric float code
gains type clarity without behavioral change.

**Expected Behavior / Usage:**

A scenario provides an `initial` value and an ordered list of `ops`; operations
are applied in order and the final stored value is reported as `value=<n>`.
Ordered comparison mirrors the primitive.

**Test Cases:** `rcb_tests/public_test_cases/feature05_floating_point.json`

```json
{
  "description": "Floating-point wrapper arithmetic sequences and ordered comparison.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "initial": 1.5,
        "ops": [
          { "op": "+=", "value": 2.5 },
          { "op": "*", "value": 2.0 }
        ]
      },
      "expected_output": "value=8\n"
    }
  ]
}
```

### Feature 6: Boolean wrapper

**As a developer**, I want a dedicated [a comprehensive list of standard validation modules] type that disallows accidental
arithmetic use, so that [a comprehensive list of standard validation modules] intent is explicit while logical operations and
stream I/O still work.

**Expected Behavior / Usage:**

The type supports logical negation, equality/inequality against a plain [a comprehensive list of standard validation modules],
and stream output/input — rendering as `1` / `0` on a stream while reporting its
logical state as `true` / `false`. The `io` scenario writes the current `value`
(reported as `written=`) and reads back from `text` (reported as `read=`).

**Test Cases:** `rcb_tests/public_test_cases/feature06_[a comprehensive list of standard validation modules].json`

```json
{
  "description": "Boolean wrapper: logical negation, equality/inequality against a plain bool, and stream output/input round-trip (rendered as 1/0).",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "op": "io",
        "value": true,
        "text": "0"
      },
      "expected_output": "written=1\nread=false\n"
    }
  ]
}
```

### Feature 7: Explicit narrowing conversion

**As a developer**, I want an explicit narrowing conversion between integer widths
or between floating-point widths, so that lossy conversions are visible at the
call site rather than implicit.

**Expected Behavior / Usage:**

A scenario names the `kind` (`integer` or `float`) and a `value`; the value is
narrowed and the resulting stored value is reported as `value=<n>`.

**Test Cases:** `rcb_tests/public_test_cases/feature07_[a comprehensive list of standard validation modules].json`

```json
{
  "description": "Explicit narrowing conversion between integer widths and between floating-point widths.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "kind": "integer",
        "value": 100
      },
      "expected_output": "value=100\n"
    }
  ]
}
```

### Feature 8: Overflow and underflow detection

**As a developer**, I want to know in advance whether an arithmetic operation
would overflow, underflow, or be undefined, so that I can guard against it before
it happens.

**Expected Behavior / Usage:**

Before performing an operation, a predicate reports whether that operation on the
given `signed`/`unsigned` operands would overflow, underflow, or otherwise be
undefined (including division/modulo by zero). The scenario names `sign`, `op`,
`lhs`, `rhs` and reports `will_error=<bool>`.

**Test Cases:** `rcb_tests/public_test_cases/feature08_overflow_detection.json`

```json
{
  "description": "Predicate detection of whether a signed/unsigned arithmetic operation would overflow or underflow before it is performed.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "sign": "signed",
        "op": "addition",
        "lhs": 2147483647,
        "rhs": 1
      },
      "expected_output": "will_error=true\n"
    }
  ]
}
```

### Feature 9: Two-state [a comprehensive list of standard validation modules]

**As a developer**, I want a [a comprehensive list of standard validation modules] that holds a single [a comprehensive list of standard validation modules] state with explicit
transition operations, so that toggles and conditional sets are unambiguous and
report what changed.

**Expected Behavior / Usage:**

A [a comprehensive list of standard validation modules] supports toggle (returning the prior state), unconditional
change/set/reset, and conditional try-set/try-reset that report whether they
actually changed the state. The scenario names an `initial` state and an `op`,
reporting the returned value (`returned=`) and the resulting `state=`.

**Test Cases:** `rcb_tests/public_test_cases/feature09_[a comprehensive list of standard validation modules].json`

```json
{
  "description": "Two-state [a comprehensive list of standard validation modules] with deliberate transitions: toggle, change, set/reset and the conditional try_set/try_reset that report whether they changed the state.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "initial": false,
        "op": "toggle"
      },
      "expected_output": "returned=false\nstate=true\n"
    }
  ]
}
```

### Feature 10: Named [a comprehensive list of standard validation modules] set

**As a developer**, I want a fixed-width set of named [a comprehensive list of standard validation modules]s with set/reset/toggle
and bitwise composition, so that I can manage a group of related options and
query them in aggregate.

**Expected Behavior / Usage:**

The set supports setting, resetting, and toggling individual [a comprehensive list of standard validation modules]s or all [a comprehensive list of standard validation modules]s
at once, plus bitwise composition. The scenario applies an ordered list of `ops`
naming an operation and a `[a comprehensive list of standard validation modules]`, then reports membership of each [a comprehensive list of standard validation modules] and the
aggregate `any`/`none`/`all` queries.

**Test Cases:** `rcb_tests/public_test_cases/feature10_[a comprehensive list of standard validation modules]_set.json`

```json
{
  "description": "Fixed-width set of named [a comprehensive list of standard validation modules]s supporting set/reset/toggle of individual and all [a comprehensive list of standard validation modules]s plus bitwise composition, reporting membership and aggregate any/none/all queries.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]_set",
        "ops": [
          { "op": "set", "[a comprehensive list of standard validation modules]": "a" },
          { "op": "toggle", "[a comprehensive list of standard validation modules]": "c" }
        ]
      },
      "expected_output": "a=true\nb=false\nc=true\nany=true\nnone=false\nall=false\n"
    }
  ]
}
```

### Feature 11: Index arithmetic

**As a developer**, I want an [a comprehensive list of standard validation modules] type that can only be advanced by a separate
signed distance type, so that indices cannot be accidentally mixed with arbitrary
integers.

**Expected Behavior / Usage:**

An [a comprehensive list of standard validation modules] is advanced via compound and binary +/- operators and the
next/prev/advance helpers. The scenario provides an `initial` [a comprehensive list of standard validation modules] and an ordered
list of `ops` (each a distance), reporting the final `[a comprehensive list of standard validation modules]=<n>`.

**Test Cases:** `rcb_tests/public_test_cases/feature11_[a comprehensive list of standard validation modules]_arithmetic.json`

```json
{
  "description": "Index type advanced by a separate signed distance type via +=, -=, binary +/-, and the next/prev/advance helpers.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "initial": 5,
        "ops": [
          { "op": "+=", "value": 3 },
          { "op": "prev", "value": 2 }
        ]
      },
      "expected_output": "[a comprehensive list of standard validation modules]=6\n"
    }
  ]
}
```

### Feature 12: Index distance and element access

**As a developer**, I want the signed distance between two indices as a distinct
distance value and type-safe element access by [a comprehensive list of standard validation modules], so that pointer-style
offsets are explicit and checked.

**Expected Behavior / Usage:**

The distance between `from` and `to` is computed as a signed distance value and
reported as `distance=<n>`; a related access scenario reaches a container element
by a typed [a comprehensive list of standard validation modules].

**Test Cases:** `rcb_tests/public_test_cases/feature12_[a comprehensive list of standard validation modules]_distance_at.json`

```json
{
  "description": "Signed distance between two indices and type-safe element access into a container by [a comprehensive list of standard validation modules].",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]_distance",
        "from": 2,
        "to": 9
      },
      "expected_output": "distance=7\n"
    }
  ]
}
```

### Feature 13: Relational constraints

**As a developer**, I want single-bound constraint predicates as first-class
objects, so that I can validate batches of values against a rule like "less than
five".

**Expected Behavior / Usage:**

Constraint predicates — less, less-or-equal, greater, greater-or-equal — are
evaluated against a batch of `queries` relative to a `bound`. Each query is
reported as `<query>=<bool>`.

**Test Cases:** `rcb_tests/public_test_cases/feature13_relational_constraints.json`

```json
{
  "description": "Single-bound relational constraint predicates (less, less-or-equal, greater, greater-or-equal) evaluated against a batch of queries.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "constraint": "less",
        "bound": 5,
        "queries": [3, 5, 7]
      },
      "expected_output": "3=true\n5=false\n7=false\n"
    }
  ]
}
```

### Feature 14: Interval constraints

**As a developer**, I want an interval-membership constraint where each bound is
independently open or closed, so that I can express ranges precisely.

**Expected Behavior / Usage:**

The constraint treats `lower_closed` and `upper_closed` independently against
`lower`/`upper` bounds, and reports membership for each value in `queries` as
`<query>=<bool>`.

**Test Cases:** `rcb_tests/public_test_cases/feature14_interval_constraints.json`

```json
{
  "description": "Interval membership constraint with each bound independently open or closed.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "lower_closed": true,
        "upper_closed": true,
        "lower": 0,
        "upper": 10,
        "queries": [0, 10, 5, -1]
      },
      "expected_output": "0=true\n10=true\n5=true\n-1=false\n"
    }
  ]
}
```

### Feature 15: Clamping and bounded construction

**As a developer**, I want a [a comprehensive list of standard validation modules]ing policy that forces a value into a closed
interval and constructors that record their bounds, so that out-of-range inputs
are coerced rather than rejected.

**Expected Behavior / Usage:**

A [a comprehensive list of standard validation modules]ing policy forces a value into the closed interval `[lower, upper]`. The
scenario reports, for each value in `queries`, the [a comprehensive list of standard validation modules]ed result as
`<query>=<[a comprehensive list of standard validation modules]ed>`.

**Test Cases:** `rcb_tests/public_test_cases/feature15_[a comprehensive list of standard validation modules]ing.json`

```json
{
  "description": "Clamping verifier that forces a value into a closed interval, and the make_[a comprehensive list of standard validation modules]ed / make_bounded constructors that report the stored value and the recorded bounds.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "lower": 0,
        "upper": 10,
        "queries": [-5, 5, 15]
      },
      "expected_output": "-5=0\n5=5\n15=10\n"
    }
  ]
}
```

### Feature 16: Constraint enforcement and predicates

**As a developer**, I want a constrained value that enforces its invariant at
assignment time, so that an illegal assignment is rejected with a normalized
error instead of corrupting state.

**Expected Behavior / Usage:**

Assigning a value that violates the constraint raises a normalized constraint
violation (`error=constraint_violation`) plus the violated `constraint=` context,
rather than corrupting state. Predefined predicates (non-null, non-empty,
non-default) report satisfaction directly.

**Test Cases:** `rcb_tests/public_test_cases/feature16_constraint_enforcement.json`

```json
{
  "description": "Enforcing a constraint at assignment time: a non-null constrained value rejects a null assignment by raising a normalized constraint violation, while predefined predicates (non-null, non-empty, non-default) report satisfaction.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "assign_null": true
      },
      "expected_output": "error=constraint_violation\nconstraint=non_null\n"
    }
  ]
}
```

### Feature 17: Compile-time literal parsing

**As a developer**, I want a numeric literal parser that handles all common bases
and digit separators, so that tokens are interpreted exactly as the language
would interpret a literal.

**Expected Behavior / Usage:**

The parser interprets digit sequences across decimal, hexadecimal, octal, and
binary bases, honoring digit-group separators, and yields the parsed integer as
`value=<n>` for the given `token`.

**Test Cases:** `rcb_tests/public_test_cases/feature17_literal_parser.json`

```json
{
  "description": "Compile-time numeric literal parser exposed for a catalogue of tokens covering decimal, hexadecimal, octal, binary bases and digit separators.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "token": "23'900"
      },
      "expected_output": "value=23900\n"
    }
  ]
}
```

### Feature 18: Identity-preserving [a comprehensive list of standard validation modules]

**As a developer**, I want a checked [a comprehensive list of standard validation modules] from a base reference to a derived
reference, so that I can recover the derived type while preserving object
identity.

**Expected Behavior / Usage:**

The [a comprehensive list of standard validation modules] converts a base reference to a derived reference while preserving the
identity of the underlying object. The scenario tags the object and reports
`same_object=<bool>` and the recovered `tag=<n>`.

**Test Cases:** `rcb_tests/public_test_cases/feature18_[a comprehensive list of standard validation modules].json`

```json
{
  "description": "Safe [a comprehensive list of standard validation modules] from a base reference to a derived reference that preserves object identity.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "tag": 42
      },
      "expected_output": "same_object=true\ntag=42\n"
    }
  ]
}
```

### Feature 19: Strong type aliases

**As a developer**, I want a strong alias over a primitive that opts into selected
operator sets while remaining a distinct type, so that distinct quantities cannot
be implicitly confused.

**Expected Behavior / Usage:**

The alias opts into arithmetic, comparison, and bitwise operator sets while
staying distinct from the underlying primitive and other aliases. The arithmetic
scenario applies an ordered list of `ops` to an `initial` value and reports the
final `value=<n>`.

**Test Cases:** `rcb_tests/public_test_cases/feature19_strong_typedef.json`

```json
{
  "description": "Strong typedef over a primitive that opts into arithmetic, comparison and bitwise operator sets while remaining a distinct type.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "initial": 10,
        "ops": [
          { "op": "+=", "value": 5 },
          { "op": "%", "value": 4 }
        ]
      },
      "expected_output": "value=3\n"
    }
  ]
}
```

### Feature 20: Deferred construction

**As a developer**, I want a storage slot that starts empty and is filled exactly
once, so that I can separate declaration from initialization without a default
value.

**Expected Behavior / Usage:**

The slot starts empty and is later filled by assignment or in-place construction.
The scenario reports the initial engaged state (`initial_has_value=`), the engaged
state after filling (`has_value=`), and the stored `value=`.

**Test Cases:** `rcb_tests/public_test_cases/feature20_[a comprehensive list of standard validation modules].json`

```json
{
  "description": "A storage slot that starts empty and is later filled exactly once via assignment or in-place construction.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "type": "int",
        "assign": 99
      },
      "expected_output": "initial_has_value=false\nhas_value=true\nvalue=99\n"
    }
  ]
}
```

### Feature 21: Output parameter

**As a developer**, I want an output parameter that writes through to caller-owned
storage, so that a function can produce a result without returning it and without
exposing the storage details.

**Expected Behavior / Usage:**

The parameter writes through to backing storage via direct assignment,
repeated-fill assignment, or successive writes. The scenario names an `op` and a
`value`, and reports the final `backing=<value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature21_[a comprehensive list of standard validation modules].json`

```json
{
  "description": "An output parameter that writes through to backing storage via assignment, repeated-fill assignment, or repeated writes.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "op": "assign_value",
        "value": "hello"
      },
      "expected_output": "backing=hello\n"
    }
  ]
}
```

### Feature 22: Optional value

**As a developer**, I want an optional value that makes absence explicit and
supports safe access patterns, so that "maybe empty" is impossible to ignore.

**Expected Behavior / Usage:**

The optional reports presence, converts to [a comprehensive list of standard validation modules], supplies a fallback via
value-or, applies a transform only when engaged, and compares against another
optional that may itself be empty. The scenario reports `has_value=`, `as_bool=`,
and `value_or=`.

**Test Cases:** `rcb_tests/public_test_cases/feature22_optional.json`

```json
{
  "description": "Optional value: presence test, bool conversion, value_or fallback, the map transform applied only when engaged, and full comparison against another optional that may be empty.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "present": true,
        "value": 7,
        "fallback": -1
      },
      "expected_output": "has_value=true\nas_bool=true\nvalue_or=7\n"
    }
  ]
}
```

### Feature 23: Optional reference

**As a developer**, I want an optional reference that either refers to an existing
object or to nothing, so that I can express a nullable reference without raw
pointers.

**Expected Behavior / Usage:**

The reference either binds to an existing object or to nothing, and supplies a
usable fallback via value-or. The scenario reports `has_value=`, the referenced
`value=`, and `value_or=`.

**Test Cases:** `rcb_tests/public_test_cases/feature23_[a comprehensive list of standard validation modules].json`

```json
{
  "description": "Optional reference that either refers to an existing object or to nothing, with a value_or fallback.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "value": 5,
        "fallback": -1,
        "present": true
      },
      "expected_output": "has_value=true\nvalue=5\nvalue_or=5\n"
    }
  ]
}
```

### Feature 24: Tagged variant

**As a developer**, I want a tagged variant over several alternatives with safe
queries and well-defined behavior under throwing assignments, so that I can hold
one of several types without manual bookkeeping.

**Expected Behavior / Usage:**

The variant reports its active alternative, supplies a typed value-or fallback,
compares against a value, and preserves a well-defined state under throwing
assignments according to its empty-state policy. The state scenario names the
active `kind` and `value`, reporting `has_value=`, `holds_int=`, `holds_double=`,
and `value_or_int=`.

**Test Cases:** `rcb_tests/public_test_cases/feature24_variant.json`

```json
{
  "description": "Tagged variant over several alternatives: active-alternative queries, value_or, comparison against a value, and exception safety under different empty-state policies.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "kind": "int",
        "value": 8
      },
      "expected_output": "has_value=true\nholds_int=true\nholds_double=false\nvalue_or_int=8\n"
    }
  ]
}
```

### Feature 25: Tagged union

**As a developer**, I want a low-level tagged union that tracks its active member,
so that I can build higher-level variants with explicit emplace/destroy control.

**Expected Behavior / Usage:**

The union emplaces a chosen alternative, reports the active type [a comprehensive list of standard validation modules] and value,
then destroys the active member and confirms it is empty. The scenario names the
active `kind` and `value`, reporting `initial_has_value=`, `type_[a comprehensive list of standard validation modules]=`,
`value=`, and `after_destroy_has_value=`.

**Test Cases:** `rcb_tests/public_test_cases/feature25_[a comprehensive list of standard validation modules].json`

```json
{
  "description": "Low-level tagged union: emplace an alternative, report the active type [a comprehensive list of standard validation modules] and value, then destroy and confirm it is empty.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "kind": "int",
        "value": 11
      },
      "expected_output": "initial_has_value=false\ntype_[a comprehensive list of standard validation modules]=1\nvalue=11\nafter_destroy_has_value=false\n"
    }
  ]
}
```

### Feature 26: Compact optional

**As a developer**, I want a space-optimized optional that encodes its empty state
inside the value domain itself, so that I avoid the storage cost of a separate
[a comprehensive list of standard validation modules].

**Expected Behavior / Usage:**

The empty state is encoded in the value domain (a [a comprehensive list of standard validation modules], a sentinel integer, or
NaN for floating point) rather than a separate [a comprehensive list of standard validation modules], and the same create/destroy
lifecycle is supported. The scenario names a `policy` and `value`, reporting
`initial_has_value=`, `has_value=`, `value=`, and `after_destroy_has_value=`.

**Test Cases:** `rcb_tests/public_test_cases/feature26_[a comprehensive list of standard validation modules].json`

```json
{
  "description": "Space-optimized optional storage whose empty state is encoded in the value domain itself ([a comprehensive list of standard validation modules], sentinel integer, NaN float): lifecycle of create/destroy.",
  "cases": [
    {
      "input": {
        "fn": "[a comprehensive list of standard validation modules]",
        "policy": "bool",
        "value": true
      },
      "expected_output": "initial_has_value=false\nhas_value=true\nvalue=true\nafter_destroy_has_value=false\n"
    }
  ]
}
```

## Deliverables

- **Adapter program** — a single executable that reads one JSON command object
  from standard input, dispatches on the `fn` field to the corresponding
  scenario, and writes the normalized `key=value` report to standard output,
  translating any domain-rule violation into a language-neutral error category.
- **Test harness** (`rcb_tests/test.sh`) — a single entry point that builds the
  adapter and runs every JSON case under a chosen cases directory
  (`--cases-dir <subdir>`, default `test_cases`), writing each case's raw
  standard output to `rcb_tests/stdout/<cases-dir>/<stem>@<NNN>.txt` and
  reporting a pass/fail tally.
- **Public case set** (`rcb_tests/public_test_cases/`) — the representative case
  for each feature above, mirroring exactly the `{description, cases}` blocks
  embedded in this document.
- **Hidden case set** (`rcb_tests/test_cases/`) — a broader battery of cases per
  feature covering the documented behaviors.
- **Acceptance criterion** — running the harness against the reference
  implementation must report zero failures for both case sets.
