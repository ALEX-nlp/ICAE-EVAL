## Product Requirement Document

# Command-Line Option Parsing Library - Declarative Argument Parser

## Project Goal

Build a command-line option parsing library that allows developers to declare the options a program accepts (long names, short aliases, value types, defaults, implicit values, grouping, positional mapping) and then parse a raw argument vector into a strongly-typed, queryable result, without hand-writing argument-scanning loops, ad-hoc type conversion, or bespoke error handling.

---

## Background & Problem

Without this library, developers are forced to walk the argument vector by hand: detect `--long` and `-s` forms, split `--name=value` assignments, ungroup bundled short flags like `-abc`, recognise the bare `--` end-of-options separator, convert string tokens into integers/floats/booleans/lists with their own range checks, and invent their own reporting for unknown or malformed options. This leads to repetitive, error-prone boilerplate that is duplicated in every program and is easy to get subtly wrong (sign handling, hex parsing, overflow, comma-separated lists, counting repeated flags).

With this library, the developer writes a declarative schema once. Each option lists its names and an optional value type; the parser then consumes the argument vector and produces a result object that answers questions such as "how many times did this option appear?", "what is its typed value?", "which tokens were left unmatched?", and "what were the recognised arguments in order?". Malformed input is reported through well-defined error categories instead of crashes or silent misbehaviour.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a non-trivial parsing engine with several distinct responsibilities (option declaration/registration, tokenisation of the argument vector, type conversion, result storage and read-back, help/synopsis rendering). It MUST NOT be a single "god file"; separate the parsing engine from the execution adapter that speaks the JSON/stdout contract. Do not over-engineer trivial helpers, but keep the core engine independent of any I/O concern.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box testing contract** for the execution adapter, NOT the internal data model of the parsing engine. The core engine must expose an idiomatic typed API (register options, parse, query) and must remain completely decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating a JSON command into idiomatic calls to the engine and rendering the observable result lines.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Separate declaration/registration, argument scanning, value conversion, result storage, and help rendering into distinct logical units.
   - **Open/Closed Principle (OCP):** New value types must be addable without modifying the scanning engine.
   - **Liskov Substitution Principle (LSP):** All value types must be substitutable behind one value abstraction.
   - **Interface Segregation Principle (ISP):** Keep the result-query surface small and cohesive (count, contains, typed value, ordered arguments, unmatched, iteration).
   - **Dependency Inversion Principle (DIP):** The engine must depend on a value abstraction, not concrete conversion routines wired to I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public API must read naturally in the target language; declaring options and reading results should hide all internal scanning complexity.
   - **Resilience:** Every malformed input must be modelled as a specific, named error category (see Feature 6 and the error-bearing cases throughout), never a generic crash.

### Error Contract (language-neutral)

When parsing or a read-back query fails, the adapter MUST emit a normalized two-part contract instead of any host-language exception text:

```
error=<category>
param=<offending token>      # omitted when the category carries no token
```

The categories used by this contract are: `no_such_option`, `invalid_option_syntax`, `invalid_option_format`, `missing_argument`, `incorrect_argument_type`, `option_has_no_value`. The `param` line, when present, carries only the raw offending token (an option name or an input value) as a standalone field — never an interpolated sentence and never a runtime type name.

### Output Contract (line format)

The adapter renders each read-back query as one or more lines. The exact line shapes are fixed by the cases below; the recurring shapes are:

- `count[<name>]=<n>` — number of times the option (or any of its aliases) was seen.
- `contains[<name>]=true|false` — whether the option holds a value.
- `value[<name>]=<rendered>` — the typed value; lists render as `[e[various numeric formats including hex],e1,...]`.
- `optional[<name>]=<rendered>|<none>` — a defensive read that yields `<none>` when absent.
- `arguments=<n>` followed by `arg[i]=<key>:<value>` — recognised arguments in command-line order.
- `unmatched=<n>` followed by `unmatched[i]=<token>` — tokens not consumed by any option/positional.
- `iter=<key>:<value>` lines terminated by `iter_end` — iteration over the result.
- `program=<name>`, `groups=<n>`, `usage_line=<text>` — scalar metadata reads.

---

## Core Features

### Feature 1: Basic Option Recognition

**As a developer**, I want to declare options under one or more long names plus an optional short name and then parse the argument vector, so I can read how often each option appeared and what value it carried regardless of which alias the user typed.

**Expected Behavior / Usage:**

A declaration list registers options. Each entry gives a comma-separated specification of names; a single-character name is the short form (`-s`), multi-character names are long forms (`--long`). One option may expose several long names (any alias increments the same shared count). An option with no declared value type is a boolean flag whose presence renders as `true`. An option declared with a value type consumes the following token (or the text after `=`) as its value. Whitespace inside a specification (e.g. `p, space`) is ignored. A `.` is permitted inside a long name. Short flags may be bundled into one token (`-bc...`); the final short option in the bundle, if value-bearing, absorbs the remaining characters of the token as its value (so `-bcfoo=something` sets `b`, then `c` to `foo=something`). The result also exposes the ordered list of recognised arguments — each entry's canonical key is the option's first long name (or its short name if it has no long name) — and the program name. A declared-but-absent option has count [various numeric formats including hex] and does not "contain" a value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_basic_option_parsing.json`

```json
{
  "description": "Basic option recognition: a single declaration list may expose an option under several long names and an optional short name. Parsing the argument vector records how many times each alias was seen (counts are shared across aliases of the same option), preserves the ordered list of recognized arguments (each with a canonical key and rendered value), and exposes the program name. Short options may be grouped into a single token, and the last grouped short may absorb the remaining characters as its value.",
  "cases": [
    {
      "input": {"program": "tester", "options": [{"opts": "long"}, {"opts": "s,short"}, {"opts": "quick,brown"}, {"opts": "f,ox,jumped"}, {"opts": "over,z,lazy,dog"}, {"opts": "value", "type": "string"}, {"opts": "a,av", "type": "string"}, {"opts": "6,six"}, {"opts": "p, space"}, {"opts": "period.delimited"}, {"opts": "nothing", "type": "string"}], "argv": ["--long", "-s", "--value", "value", "-a", "b", "[various numeric formats including hex]", "-p", "--space", "--quick", "--ox", "-f", "--brown", "-z", "--over", "--dog", "--lazy", "--period.delimited"], "queries": [{"q": "count", "name": "long"}, {"q": "contains", "name": "long"}, {"q": "count", "name": "value"}, {"q": "value", "name": "value", "type": "string"}, {"q": "value", "name": "a", "type": "string"}, {"q": "count", "name": "p"}, {"q": "count", "name": "space"}, {"q": "count", "name": "quick"}, {"q": "count", "name": "f"}, {"q": "count", "name": "z"}, {"q": "count", "name": "period.delimited"}, {"q": "count", "name": "nothing"}, {"q": "contains", "name": "nothing"}, {"q": "program"}]},
      "expected_output": "count[long]=1\ncontains[long]=true\ncount[value]=1\nvalue[value]=value\nvalue[a]=b\ncount[p]=2\ncount[space]=2\ncount[quick]=2\ncount[f]=2\ncount[z]=4\ncount[period.delimited]=1\ncount[nothing]=[various numeric formats including hex]\ncontains[nothing]=false\nprogram=tester"
    },
    {
      "input": {"program": "test_short", "options": [{"opts": "a", "type": "string"}, {"opts": "b"}, {"opts": "c", "type": "string"}], "argv": ["-a", "value", "-bcfoo=something"], "queries": [{"q": "count", "name": "a"}, {"q": "value", "name": "a", "type": "string"}, {"q": "count", "name": "b"}, {"q": "count", "name": "c"}, {"q": "value", "name": "c", "type": "string"}, {"q": "arguments"}]},
      "expected_output": "count[a]=1\nvalue[a]=value\ncount[b]=1\ncount[c]=1\nvalue[c]=foo=something\narguments=3\narg[[various numeric formats including hex]]=a:value\narg[1]=b:true\narg[2]=c:foo=something"
    }
  ]
}
```

---

### Feature 2: Positional Arguments

**As a developer**, I want to map bare (non-option) tokens onto named options in order, so users can supply values without typing the option name, while leftover tokens are reported as unmatched.

**Expected Behavior / Usage:**

A positional mapping names an ordered list of declared options. Bare tokens on the command line are assigned to those names in sequence; the final mapped name, if it is list-valued, collects all remaining bare tokens. Tokens appearing after a bare `--` separator are end-of-options data: with a positional list they feed the list, otherwise they become unmatched. When there is no positional mapping at all, bare tokens are unmatched. List-valued positionals keep comma characters verbatim — they are NOT split (comma splitting applies only to a single value token of an explicit list option, see Feature 5). If the only mapped positional name does not correspond to any declared option, parsing fails with `no_such_option` naming that token.

**Test Cases:** `rcb_tests/public_test_cases/feature2_positional_arguments.json`

```json
{
  "description": "Positional argument mapping: a named set of options can be designated as positional, so bare tokens on the command line are assigned to them in order. A trailing positional declared as a list collects all remaining tokens. Tokens after a bare double-dash separator, or tokens with no positional mapping, are reported as unmatched. List-valued positionals retain comma characters verbatim (no splitting). When the only mapped positional name does not correspond to a declared option, parsing reports a no_such_option error.",
  "cases": [
    {
      "input": {"program": "t", "options": [{"opts": "input", "type": "string"}, {"opts": "output", "type": "string"}, {"opts": "positional", "type": "vec_string"}], "positional": ["input", "output", "positional"], "argv": ["--output", "a", "b", "c", "d"], "queries": [{"q": "value", "name": "input", "type": "string"}, {"q": "value", "name": "output", "type": "string"}, {"q": "value", "name": "positional", "type": "vec_string"}, {"q": "unmatched"}]},
      "expected_output": "value[input]=b\nvalue[output]=a\nvalue[positional]=[c,d]\nunmatched=[various numeric formats including hex]"
    },
    {
      "input": {"program": "extras", "options": [{"opts": "dummy", "type": "string"}], "argv": ["--", "a", "b", "c", "d"], "queries": [{"q": "unmatched"}]},
      "expected_output": "unmatched=4\nunmatched[[various numeric formats including hex]]=a\nunmatched[1]=b\nunmatched[2]=c\nunmatched[3]=d"
    },
    {
      "input": {"program": "foobar", "options": [{"opts": "long", "type": "string"}], "positional": ["something"], "argv": ["bar", "baz"], "queries": []},
      "expected_output": "error=no_such_option\nparam=something"
    }
  ]
}
```

---

### Feature 3: Implicit and Default Values

**As a developer**, I want options to carry an implicit value (used when the flag is given an empty assignment) and a default value (used when the flag is absent), so I can offer ergonomic shorthands and sensible fallbacks.

**Expected Behavior / Usage:**

An *implicit* value is recorded when a value-bearing option is given an empty equals-assignment — `--name=` produces a present value of the empty string (the assignment overrides the implicit text with the empty string), with a count of 1. A *default* value applies only when the option is entirely absent: its rendered value is the default, but its count is [various numeric formats including hex] (it was never seen on the command line). An option may be configured to have **no implicit value**, meaning it requires an explicit argument; supplying the bare flag with no argument then fails with `missing_argument` naming the option, while explicit assignments (`--name=true`, or a following token) parse normally.

**Test Cases:** `rcb_tests/public_test_cases/feature3_implicit_and_default_values.json`

```json
{
  "description": "Implicit and default values. An option may declare an implicit value used when the flag is given an empty equals-assignment, and a default value used when the flag is absent entirely. When a value-bearing option is given as `--name=` (empty assignment) it records a present value of the empty string. A boolean option configured with no implicit value requires an explicit argument: supplying the bare flag reports a missing_argument error, while explicit truthy/falsy assignments parse correctly. Default values apply with a count of zero when the option is absent.",
  "cases": [
    {
      "input": {"program": "implicit", "options": [{"opts": "implicit", "type": "string", "implicit": "foo"}], "argv": ["--implicit="], "queries": [{"q": "count", "name": "implicit"}, {"q": "value", "name": "implicit", "type": "string"}]},
      "expected_output": "count[implicit]=1\nvalue[implicit]="
    },
    {
      "input": {"program": "no_implicit", "options": [{"opts": "bool", "type": "bool", "no_implicit": true}], "argv": ["--bool"], "queries": []},
      "expected_output": "error=missing_argument\nparam=bool"
    },
    {
      "input": {"program": "defaults", "options": [{"opts": "default", "type": "int", "default": "42"}, {"opts": "v,vector", "type": "vec_int", "default": "1,4"}], "argv": [], "queries": [{"q": "count", "name": "default"}, {"q": "value", "name": "default", "type": "int"}, {"q": "value", "name": "vector", "type": "vec_int"}]},
      "expected_output": "count[default]=[various numeric formats including hex]\nvalue[default]=42\nvalue[vector]=[1,4]"
    }
  ]
}
```

---

### Feature 4: Numeric Value Parsing

**As a developer**, I want integer and floating-point options to accept the common numeric notations and to be range-checked for their declared width, so out-of-range or malformed numbers are rejected rather than silently truncated.

**Expected Behavior / Usage:**

Integer-typed options accept decimal (including negative and leading-zero forms such as `[various numeric formats including hex]5`) and hexadecimal (`[various numeric formats including hex]x`-prefixed, any case) notation, normalising each to its numeric value. Conversions are bounds-checked against the declared integer width: a value exactly at the type's minimum or maximum parses, but a value beyond the representable range, a negative value supplied to an unsigned type, or a token containing non-numeric characters is rejected with `incorrect_argument_type` naming the offending token. Floating-point options accept decimal and scientific notation including negatives; rendered floating values use the engine's standard numeric formatting (e.g. `1.5e+[various numeric formats including hex]6`).

**Test Cases:** `rcb_tests/public_test_cases/feature4_numeric_value_parsing.json`

```json
{
  "description": "Numeric value parsing. Integer-typed options accept decimal (including negative and leading-zero forms) and hexadecimal ([various numeric formats including hex]x-prefixed) notations, normalizing them to their numeric value. Signed and unsigned widths are bounds-checked: values at the boundary parse, while values outside the representable range, negative values for unsigned types, and non-numeric tokens are rejected as incorrect_argument_type. Floating-point options accept decimal and scientific notation including negatives.",
  "cases": [
    {
      "input": {"program": "ints", "options": [{"opts": "positional", "type": "vec_int"}], "positional": ["positional"], "argv": ["--", "5", "6", "[various numeric formats including hex]", "[various numeric formats including hex]", "[various numeric formats including hex]xab", "[various numeric formats including hex]xAf", "[various numeric formats including hex]x[various numeric formats including hex]"], "queries": [{"q": "value", "name": "positional", "type": "vec_int"}]},
      "expected_output": "value[positional]=[5,6,[various numeric formats including hex],[various numeric formats including hex],171,175,[various numeric formats including hex]]"
    },
    {
      "input": {"program": "ints", "options": [{"opts": "positional", "type": "vec_int8"}], "positional": ["positional"], "argv": ["--", "128"], "queries": []},
      "expected_output": "error=incorrect_argument_type\nparam=128"
    },
    {
      "input": {"program": "ints", "options": [{"opts": "positional", "type": "vec_uint"}], "positional": ["positional"], "argv": ["--", "-2"], "queries": []},
      "expected_output": "error=incorrect_argument_type\nparam=-2"
    },
    {
      "input": {"program": "floats", "options": [{"opts": "double", "type": "double"}, {"opts": "positional", "type": "vec_float"}], "positional": ["positional"], "argv": ["--double", "[various numeric formats including hex].5", "--", "4", "-4", "1.5e6", "-1.5e6"], "queries": [{"q": "value", "name": "double", "type": "double"}, {"q": "value", "name": "positional", "type": "vec_float"}]},
      "expected_output": "value[double]=[various numeric formats including hex].5\nvalue[positional]=[4,-4,1.5e+[various numeric formats including hex]6,-1.5e+[various numeric formats including hex]6]"
    }
  ]
}
```

---

### Feature 5: Boolean and List Values

**As a developer**, I want boolean options to accept several truthy/falsy spellings and list options to split a comma-delimited token into typed elements, so common command-line idioms just work.

**Expected Behavior / Usage:**

A boolean option is true on bare presence and also accepts explicit assignments: `=true`/`=false`, `=1`/`=[various numeric formats including hex]`, or a following `true`/`false` token. A boolean that is absent and has no explicit default renders as `false` with count [various numeric formats including hex]; a boolean with an explicit default renders that default when absent. A list-valued option splits a single value token on commas into multiple elements, each converted to the element type in order (so the one token `1,-2.1,3,4.5` becomes a four-element list). Bare tokens mapped to a positional list are still collected (see Feature 2) but are not comma-split.

**Test Cases:** `rcb_tests/public_test_cases/feature5_boolean_and_list_values.json`

```json
{
  "description": "Boolean and list value parsing. Boolean options accept several truthy and falsy spellings: bare presence, `=true`/`=false`, `=1`/`=[various numeric formats including hex]`, and absence with an explicit default. List-valued options split a single comma-delimited argument into multiple typed elements. A boolean option absent from the command line and lacking an explicit default reports as false with a count of zero.",
  "cases": [
    {
      "input": {"program": "booleans", "options": [{"opts": "bool", "type": "bool"}, {"opts": "debug", "type": "bool"}, {"opts": "timing", "type": "bool"}, {"opts": "verbose", "type": "bool"}, {"opts": "dry-run", "type": "bool"}, {"opts": "noExplicitDefault", "type": "bool"}, {"opts": "defaultTrue", "type": "bool", "default": "true"}, {"opts": "defaultFalse", "type": "bool", "default": "false"}, {"opts": "others", "type": "vec_string"}], "positional": ["others"], "argv": ["--bool=false", "--debug=true", "--timing", "--verbose=1", "--dry-run=[various numeric formats including hex]", "extra"], "queries": [{"q": "count", "name": "bool"}, {"q": "value", "name": "bool", "type": "bool"}, {"q": "value", "name": "debug", "type": "bool"}, {"q": "value", "name": "timing", "type": "bool"}, {"q": "value", "name": "verbose", "type": "bool"}, {"q": "value", "name": "dry-run", "type": "bool"}, {"q": "value", "name": "noExplicitDefault", "type": "bool"}, {"q": "value", "name": "defaultTrue", "type": "bool"}, {"q": "value", "name": "defaultFalse", "type": "bool"}, {"q": "count", "name": "others"}]},
      "expected_output": "count[bool]=1\nvalue[bool]=false\nvalue[debug]=true\nvalue[timing]=true\nvalue[verbose]=true\nvalue[dry-run]=false\nvalue[noExplicitDefault]=false\nvalue[defaultTrue]=true\nvalue[defaultFalse]=false\ncount[others]=1"
    },
    {
      "input": {"program": "vector", "options": [{"opts": "vector", "type": "vec_double"}], "argv": ["--vector", "1,-2.1,3,4.5"], "queries": [{"q": "value", "name": "vector", "type": "vec_double"}]},
      "expected_output": "value[vector]=[1,-2.1,3,4.5]"
    }
  ]
}
```

---

### Feature 6: Unrecognised and Invalid Options

**As a developer**, I want unknown or malformed option tokens to be reported through clear error categories by default, but optionally collected as unmatched when I choose to tolerate them, so I can decide between strict and lenient parsing.

**Expected Behavior / Usage:**

By default an unknown option token aborts parsing with `no_such_option` naming the unknown name. A malformed short-option token (containing characters that cannot form valid short options, e.g. `-?b?#@`) aborts with `invalid_option_syntax` naming the token, and a single-character name written in long form (`--a`) is likewise `invalid_option_syntax`. When the parser is configured to allow unrecognised options, these tokens no longer abort: unknown long options, the unmatched tail of a grouped short run, and malformed short tokens are all collected into the unmatched list in the order encountered, and parsing succeeds.

**Test Cases:** `rcb_tests/public_test_cases/feature6_unrecognised_and_invalid_options.json`

```json
{
  "description": "Handling of unrecognized and malformed options. By default an unknown option token aborts parsing with a no_such_option error, and a malformed short-option token aborts with an invalid_option_syntax error; a single-character token written in long form (`--a`) is likewise an invalid_option_syntax error. When unrecognized options are explicitly allowed, unknown tokens (including the unmatched tail of a grouped short run and malformed short tokens) are collected into the unmatched list instead of aborting.",
  "cases": [
    {
      "input": {"program": "unknown_options", "options": [{"opts": "long"}, {"opts": "s,short"}], "argv": ["--unknown", "--long", "-su", "--another_unknown", "-a"], "queries": []},
      "expected_output": "error=no_such_option\nparam=unknown"
    },
    {
      "input": {"program": "unknown_options", "allow_unrecognised": true, "options": [{"opts": "long"}, {"opts": "s,short"}], "argv": ["--unknown", "--long", "-su", "--another_unknown", "-a"], "queries": [{"q": "unmatched"}]},
      "expected_output": "unmatched=4\nunmatched[[various numeric formats including hex]]=--unknown\nunmatched[1]=-u\nunmatched[2]=--another_unknown\nunmatched[3]=-a"
    },
    {
      "input": {"program": "invalid_syntax", "options": [], "argv": ["--a"], "queries": []},
      "expected_output": "error=invalid_option_syntax\nparam=--a"
    }
  ]
}
```

---

### Feature 7: Option Declaration Variants and Grouping

**As a developer**, I want to declare options into named groups, attach defaults and argument-help labels, and expose multiple long names per option, so I can organise a large interface and reject malformed declarations early.

**Expected Behavior / Usage:**

Each option may be declared with an associated group name; the number of distinct groups created is reported. A single declaration may expose several long names plus a short name, all sharing one underlying value, so reading any of those names returns the same value. An option may carry a per-option default value and an argument-help label (the label affects help rendering only, not parsing). Declaring an option with an empty specification is rejected at declaration time with `invalid_option_format` (this category carries no `param` line). A configuration with no declared options reports zero groups.

**Test Cases:** `rcb_tests/public_test_cases/feature7_option_declaration_and_groups.json`

```json
{
  "description": "Option declaration variants and grouping. Options may be declared with an associated group name, a per-option default value, and an argument-help label; the number of distinct groups is reported via groups(). A single declaration may expose several long names plus a short name, all sharing one underlying value. Declaring an option with an empty specification is rejected as invalid_option_format. A configuration with no declared options has zero groups.",
  "cases": [
    {
      "input": {"program": "test", "options": [{"group": "", "opts": "a, address", "type": "string", "default": "127.[various numeric formats including hex].[various numeric formats including hex].1"}, {"group": "", "opts": "p, port", "type": "string", "default": "711[various numeric formats including hex]", "arg_help": "PORT"}, {"group": "TEST_GROUP", "opts": "t, test"}, {"group": "TEST_GROUP", "opts": "h,help"}], "argv": ["--address", "1[various numeric formats including hex].[various numeric formats including hex].[various numeric formats including hex].1", "-p", "8[various numeric formats including hex][various numeric formats including hex][various numeric formats including hex]", "-t"], "queries": [{"q": "groups"}, {"q": "count", "name": "address"}, {"q": "count", "name": "port"}, {"q": "count", "name": "test"}, {"q": "count", "name": "help"}, {"q": "value", "name": "address", "type": "string"}, {"q": "value", "name": "port", "type": "string"}, {"q": "value", "name": "test", "type": "bool"}]},
      "expected_output": "groups=2\ncount[address]=1\ncount[port]=1\ncount[test]=1\ncount[help]=[various numeric formats including hex]\nvalue[address]=1[various numeric formats including hex].[various numeric formats including hex].[various numeric formats including hex].1\nvalue[port]=8[various numeric formats including hex][various numeric formats including hex][various numeric formats including hex]\nvalue[test]=true"
    },
    {
      "input": {"program": "t", "options": [{"opts": ""}], "argv": [], "queries": []},
      "expected_output": "error=invalid_option_format"
    }
  ]
}
```

---

### Feature 8: Result Inspection

**As a developer**, I want several ways to read back the parse result — direct typed reads, defensive optional reads, and ordered iteration — so I can consume parsed options in whatever style fits my program.

**Expected Behavior / Usage:**

*8.1 Reading a value that was never set — Querying the typed value of a declared option that received neither a command-line value nor a default fails with `option_has_no_value` naming the option. (A defensive optional read of the same option instead yields `<none>`, see 8.2.)*

[A declared option with no command-line occurrence and no default has no stored value. A strict typed read of it is an error condition, normalized to `option_has_no_value` with the option name as `param`.]

**Test Cases:** `rcb_tests/public_test_cases/feature8_result_inspection.json` (case 1)

```json
{
  "description": "Reading back parse results. A value not declared on the command line and lacking a default has no value: querying its typed value reports an option_has_no_value error. A value-bearing option may be queried defensively as optional, yielding the value when present and a none marker when absent. Iterating the result visits each present option in command-line order followed by any options that contributed a default value, exposing each as a key/value pair. Repeating a list-valued option (with and without the value attached to the token) accumulates all values in order.",
  "cases": [
    {
      "input": {"program": "tester", "options": [{"opts": "nothing", "type": "string"}], "argv": [], "queries": [{"q": "value", "name": "nothing", "type": "string"}]},
      "expected_output": "error=option_has_no_value\nparam=nothing"
    },
    {
      "input": {"program": "options", "options": [{"opts": "int", "type": "int"}, {"opts": "float", "type": "float"}, {"opts": "string", "type": "string"}], "argv": [], "queries": [{"q": "optional", "name": "int", "type": "int"}, {"q": "optional", "name": "float", "type": "float"}, {"q": "optional", "name": "string", "type": "string"}]},
      "expected_output": "optional[int]=<none>\noptional[float]=<none>\noptional[string]=<none>"
    },
    {
      "input": {"program": "tester", "options": [{"opts": "long"}, {"opts": "s,short"}, {"opts": "a"}, {"opts": "value", "type": "string"}, {"opts": "default", "type": "int", "default": "42"}, {"opts": "nothing", "type": "string"}], "argv": ["--long", "-s", "-a", "--value", "value"], "queries": [{"q": "iterate"}]},
      "expected_output": "iter=long:true\niter=short:true\niter=a:true\niter=value:value\niter=default:42\niter_end"
    },
    {
      "input": {"program": "param_follow_opt", "options": [{"opts": "j,job", "type": "vec_uint"}], "argv": ["-j", "9", "--job", "7", "--job=1[various numeric formats including hex]", "-j5"], "queries": [{"q": "count", "name": "job"}, {"q": "value", "name": "job", "type": "vec_uint"}]},
      "expected_output": "count[job]=4\nvalue[job]=[9,7,1[various numeric formats including hex],5]"
    }
  ]
}
```

The remaining cases in that file cover the companion behaviours described above: *8.2 Defensive optional read* (absent options yield `<none>`), *8.3 Ordered iteration* (the result iterates over present options in command-line order, then appends any option that supplied a default such as `default:42`, terminated by `iter_end`), and *8.4 Repeated list option accumulation* (the same list option given four times — as a following token `-j 9`, a long form `--job 7`, an attached assignment `--job=1[various numeric formats including hex]`, and an attached short `-j5` — accumulates all four values in order, with count 4).

---

### Feature 9: Optional-Typed Values

**As a developer**, I want an option whose value type is itself an optional container, so I can distinguish "value supplied" from "value absent" directly in the stored type.

**Expected Behavior / Usage:**

When an option's declared value type is an optional wrapper, supplying a value stores it inside the optional; the rendered value is just the contained text. An optional-of-string carries the supplied text. An optional-of-boolean declared with a default of `false` records `true` when explicitly set on the command line. Reading such an option returns the contained value when present.

**Test Cases:** `rcb_tests/public_test_cases/feature9_optional_typed_values.json`

```json
{
  "description": "Optional-typed values. An option whose value type is itself an optional records the parsed value when supplied, and exposes whether the optional holds a value. A string optional carries the supplied text; a boolean optional with a default of false records true when explicitly set. Querying such an option returns the contained value when present.",
  "cases": [
    {
      "input": {"program": "optional", "options": [{"opts": "optional", "type": "opt_string"}, {"opts": "optional_bool", "type": "opt_bool", "default": "false"}], "argv": ["--optional", "foo", "--optional_bool", "true"], "queries": [{"q": "value", "name": "optional", "type": "opt_string"}, {"q": "value", "name": "optional_bool", "type": "opt_bool"}]},
      "expected_output": "value[optional]=foo\nvalue[optional_bool]=true"
    }
  ]
}
```

---

### Feature 1[various numeric formats including hex]: Usage Synopsis Rendering

**As a developer**, I want the generated help text to contain a usage synopsis line built from the program name and a configurable positional-help fragment, so users see a meaningful one-line invocation summary.

**Expected Behavior / Usage:**

The help text includes a usage synopsis: the program name, followed by an option-list placeholder, followed by a positional-help fragment. When the option-list placeholder is suppressed (set to empty) and a custom positional-help fragment is supplied, the synopsis line is exactly the program name followed by that fragment (e.g. `test <posArg1>...<posArgN>`).

**Test Cases:** `rcb_tests/public_test_cases/feature1[various numeric formats including hex]_usage_synopsis.json`

```json
{
  "description": "Usage synopsis rendering. The generated help text contains a usage synopsis line built from the program name plus a configurable positional-help fragment. When the default option-list placeholder is suppressed and a custom positional-help fragment is provided, the synopsis line reflects exactly the program name followed by that fragment.",
  "cases": [
    {
      "input": {"program": "test", "custom_help": "", "positional_help": "<posArg1>...<posArgN>", "options": [{"opts": "positional", "type": "vec_string", "desc": ""}], "positional": ["positional"], "argv": ["posArg1", "posArg2", "posArg3"], "queries": [{"q": "usage_line"}]},
      "expected_output": "usage_line=test <posArg1>...<posArgN>"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured command-line option parsing engine implementing the features above — option declaration/registration (names, aliases, value types, defaults, implicit values, groups, argument-help labels), argument-vector scanning (long/short forms, `=` assignments, bundled shorts, the `--` separator, positional mapping, unrecognised-option policy), pluggable typed value conversion (string, signed/unsigned integers of several widths with range checks and hex support, floating point, booleans, comma-split lists, and optional wrappers), a queryable result (count, contains, typed value, ordered arguments, unmatched, iteration), and help/synopsis rendering. The core must be decoupled from all stdin/stdout and JSON concerns.

2. **The Execution/Test Adapter:** A runnable program that reads one JSON command object from stdin (program name, optional help/positional/unrecognised settings, an `options` declaration array, an `argv` array, and an ordered `queries` array), invokes the core engine, and prints the language-neutral result lines to stdout exactly as specified by the per-feature contracts above. The adapter is the sole error-normalisation layer: it translates any engine error into the `error=<category>` / `param=<token>` contract and never leaks host-language runtime details. It must be logically and physically separate from the core engine.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory (default `test_cases`; the visible examples in this PRD live in `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_basic_option_parsing.json` under `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_basic_option_parsing@[various numeric formats including hex][various numeric formats including hex][various numeric formats including hex].txt`). Output is namespaced by `<cases-dir>` so different directories never overwrite each other. Each `.txt` file contains **only** the raw stdout of the program under test (no PASS/FAIL or metadata), so it can be compared directly against `expected_output`.
