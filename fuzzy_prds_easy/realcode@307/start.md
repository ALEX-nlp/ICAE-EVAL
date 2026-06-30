## Product Requirement Document

# Command-Line Argument Parser — Declarative Definition, Parsing, Validation, and Self-Documentation

## Project Goal

Build a reusable command-line argument parser that lets a program declare its options and operands once and then turn a raw token vector into a structured set of typed, validated name=value bindings, so developers can stop hand-writing fragile token-walking loops and get consistent parsing, validation, error reporting, and help text for free.

---

## Background & Problem

Programs receive their arguments as a flat vector of strings. Without a parser, every program re-implements the same tedious and error-prone logic: distinguishing options (tokens introduced by a prefix character) from positional operands, splitting concatenated short options, attaching values to options (either as the next token or embedded after an `=`), applying defaults, converting strings to richer types, validating against allowed sets or ranges, supporting subcommands, and producing readable usage/help text and error messages.

With this library, the developer declares each argument and its behavior up front (its name/flags, how many tokens it consumes, its type, its default, its allowed choices, whether it is required, which mutually-exclusive group it belongs to, etc.). The library then parses a token vector into a result object of bindings, raising a clear domain error when the input is invalid, and can render a one-line usage summary, a full help body, or a version string on demand.

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

## Execution Contract (shared by all features)

The execution adapter reads a single JSON request from stdin. The request describes a parser to construct and an action to perform; the adapter builds the parser using the core library, performs the action, and writes a neutral, value-rich result to stdout.

A request has these fields. Unless noted, every field is optional.

- `prog`: the program name used in usage/help/version text (defaults to `app`).
- `add_help`: whether an automatic help option (`-h`/`--help`) is added (defaults to true).
- `prefix_chars`: the set of characters that introduce options (defaults to `-`).
- `description`, `epilog`, `usage`, `version`: free text used by the self-documentation actions. In `usage` and `version`, the substring `${prog}` is replaced by the program name.
- `default_help`: when true, help text appends each argument's default value.
- `parser_defaults`: an object of extra name→value defaults injected into the result.
- `arguments`: a list of argument specifications (see below).
- `groups`: a list of groups, each `{ "kind": "group" | "mutex", "title": <string>, "required": <bool>, "description": <string>, "arguments": [ ... ] }`. A `group` only affects help layout; a `mutex` group additionally forbids supplying more than one of its members and, when `required`, forbids supplying none.
- `subparsers`: `{ "dest": <string>, "title": <string>, "description": <string>, "help": <string>, "metavar": <string>, "parsers": [ { "name": <string>, "aliases": [ ... ], "help": <string>, "defaults": { ... }, "arguments": [ ... ] }, ... ] }` declaring named subcommands.
- `action`: one of `parse` (default), `usage`, `help`, `version`.
- `argv`: the token vector to parse (used by the `parse` action).

An argument specification supports:

- `flags`: a list of option strings (e.g. `["-v", "--verbose"]`) for an optional argument; OR `name`: a single string for a positional argument.
- `nargs`: how many tokens to consume — an integer N, or one of `"?"` (a single optional value), `"*"` (zero or more), `"+"` (one or more).
- `const`: the constant value used by the optional-value (`"?"`) form and by the constant-storing actions.
- `default`: the value bound when the argument is absent; the special string `"::suppress::"` means "bind nothing" (the name is omitted from the result).
- `type`: a converter applied to each operand — `"int"` (integer), `"enum"` (a member of `{RED, GREEN, BLUE}` matched by name), `"enumstr"` (a member of `{SMALL, MEDIUM, LARGE}` matched by display string, where `LARGE` displays as `X-LARGE`), `"boolean"` (accepts `true`/`false`), `"booleanyn"` (accepts `yes`/`no`).
- `choices`: an allowed set as a list, OR a numeric range as `{ "range": [low, high] }`.
- `action`: `"store_true"`, `"store_false"`, `"store_const"`, `"append"`, `"append_const"`, `"count"`.
- `required`: whether an optional argument must be supplied.
- `dest`: overrides the result key for this argument.
- `metavar`: the placeholder name(s) shown in usage/help.
- `help`: help text, or `"::suppress::"` to hide the argument from help.

Output contract:

- For a successful `parse`, the adapter prints one line per resulting binding, sorted by name, as `<name>=<value>`. A null binding renders as `null`; a boolean as `true`/`false`; a list as `[a, b]` (nested lists nest, an empty list is `[]`); an enumerated value as its display string.
- For a failed `parse`, the adapter prints a single line `error: <message>`, where `<message>` is the parser's domain diagnostic (e.g. a required argument, too few operands, an unrecognized token, an invalid choice, a conversion failure, a mutually-exclusive conflict, or an ambiguous abbreviation). The error contract is language-neutral: it never contains host-runtime type names.
- For `usage`, `help`, and `version`, the adapter prints the formatted text verbatim.

---

## Core Features


### Feature 1: Optional and Positional Argument Binding

**As a developer**, I want to declare optional and positional arguments and have a raw token vector resolved into a set of name=value bindings, so I can have predictable, structured access to what the user passed instead of walking the token vector by hand.

**Expected Behavior / Usage:**

An optional argument is introduced by a prefix character and may consume a value; a positional argument consumes operands by position. The parser resolves a token vector into one binding per declared argument. An optional declared with the `"?"` quantifier and a `const` binds that constant when present with no value. A positional with `"*"` greedily collects the remaining operands, but yields tokens back to later fixed-count and required positionals so they can be satisfied. A parser-wide default takes precedence over a per-argument default for the same name. A per-argument default of `"::suppress::"` removes the binding entirely, so that name does not appear in the result. An optional may appear between positionals without disturbing positional assignment.

**Test Cases:** `rcb_tests/public_test_cases/feature1_basic_store_parsing.json`

```json
{
    "description": "Resolve a token vector against a parser that mixes optional arguments (named with a leading prefix character) and positional arguments, producing a set of name=value bindings. Covers: an optional that consumes one value, an optional with an optional value that falls back to a fixed constant when given with no value, a positional that greedily collects the remaining tokens; precedence of a parser-wide default over a per-argument default; a default sentinel that removes the binding entirely so the name is absent from the result; redistribution of positionals so a greedy collector yields tokens to later fixed-count and required positionals; and an optional appearing between positionals.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "flags": [
                            "--foo"
                        ]
                    },
                    {
                        "flags": [
                            "--bar"
                        ],
                        "nargs": "?",
                        "const": "c"
                    },
                    {
                        "name": "suites",
                        "nargs": "*"
                    }
                ],
                "argv": [
                    "--bar",
                    "--foo",
                    "hello",
                    "cake",
                    "dango",
                    "mochi"
                ]
            },
            "expected_output": "bar=c\nfoo=hello\nsuites=[cake, dango, mochi]\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "flags": [
                            "-f"
                        ]
                    },
                    {
                        "flags": [
                            "-g"
                        ],
                        "default": "::suppress::"
                    }
                ],
                "argv": []
            },
            "expected_output": "f=null\n"
        }
    ]
}
```

---

### Feature 2: Argument Arity (nargs Quantifiers)

**As a developer**, I want to control how many tokens each argument consumes, so I can model required pairs, optional single values, and variable-length lists precisely.

**Expected Behavior / Usage:**

Each argument may declare an arity: a fixed integer count, `"?"` for a single optional value, `"*"` for zero-or-more, or `"+"` for one-or-more. With `"?"`, an optional binds its `const` when given as a bare flag and its `default` when absent. A fixed count that is not satisfied is an error. For `"*"` optionals, supplying the flag with no following values binds an explicit empty list that overrides any default; under an append action an empty list is appended as a nested element. For `"*"` positionals, absence yields an empty list unless a default is configured, in which case the configured default is preserved when no operands are given and replaced when operands are supplied.

**Test Cases:** `rcb_tests/public_test_cases/feature2_nargs_quantifiers.json`

```json
{
    "description": "Control how many tokens an argument consumes via a quantifier: a fixed count N, an optional single value '?', zero-or-more '*', and one-or-more '+'. Demonstrates an optional-value argument falling back to its constant when present without a value and to its default when absent; a wrong fixed count being rejected; the empty-list semantics of '*' for optionals (an explicit empty list overrides any default, and under an append action an empty list is appended); and the '*' semantics for positionals (absent positionals yield an empty list unless a default is configured, and a configured default is preserved when no tokens are supplied).",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "flags": [
                            "--foo"
                        ],
                        "nargs": "?",
                        "const": "c",
                        "default": "d"
                    },
                    {
                        "name": "bar",
                        "nargs": "?",
                        "default": "d"
                    }
                ],
                "argv": [
                    "XX",
                    "--foo",
                    "YY"
                ]
            },
            "expected_output": "bar=XX\nfoo=YY\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "flags": [
                            "--foo"
                        ],
                        "nargs": "?",
                        "const": "c",
                        "default": "d"
                    },
                    {
                        "name": "bar",
                        "nargs": "?",
                        "default": "d"
                    }
                ],
                "argv": [
                    "XX",
                    "--foo"
                ]
            },
            "expected_output": "bar=XX\nfoo=c\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "flags": [
                            "--foo"
                        ],
                        "nargs": "?",
                        "const": "c",
                        "default": "d"
                    },
                    {
                        "name": "bar",
                        "nargs": "?",
                        "default": "d"
                    }
                ],
                "argv": []
            },
            "expected_output": "bar=d\nfoo=d\n"
        }
    ]
}
```

---

### Feature 3: Action-Driven Binding

**As a developer**, I want to bind values by action rather than by consuming operands, so I can express flags, counters, and accumulators declaratively.

**Expected Behavior / Usage:**

An argument's action decides how its presence updates the result. Boolean flag actions store true or false. A constant-storing action binds a fixed `const` when the flag appears. A counting action binds the number of occurrences of a flag (including repeated and concatenated occurrences). An append action accumulates each occurrence's value into a list, while an append-constant action appends a fixed `const` per occurrence.

**Test Cases:** `rcb_tests/public_test_cases/feature3_store_const_actions.json`

```json
{
    "description": "Bind values by action rather than by consuming operands: flag actions that store a true or false boolean, an action that stores a fixed constant when the flag appears, a counting action that yields how many times a (possibly repeated/concatenated) flag occurred, an append action that accumulates each occurrence's value into a list, and an append-constant action that appends a fixed constant per occurrence.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "flags": [
                            "--foo"
                        ],
                        "action": "store_true"
                    },
                    {
                        "flags": [
                            "--bar"
                        ],
                        "action": "store_false"
                    },
                    {
                        "flags": [
                            "--baz"
                        ],
                        "action": "store_false"
                    },
                    {
                        "flags": [
                            "--sid"
                        ],
                        "action": "store_true"
                    }
                ],
                "argv": [
                    "--foo",
                    "--bar"
                ]
            },
            "expected_output": "bar=false\nbaz=true\nfoo=true\nsid=false\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "flags": [
                            "-v",
                            "--verbose"
                        ],
                        "action": "count"
                    },
                    {
                        "flags": [
                            "--foo"
                        ]
                    }
                ],
                "argv": [
                    "-v",
                    "-vv",
                    "-vvvv"
                ]
            },
            "expected_output": "foo=null\nverbose=7\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "flags": [
                            "--foo"
                        ],
                        "action": "append",
                        "nargs": "*"
                    },
                    {
                        "flags": [
                            "--bar"
                        ],
                        "action": "append"
                    }
                ],
                "argv": [
                    "--foo",
                    "a",
                    "--foo",
                    "b",
                    "--bar",
                    "c",
                    "--bar",
                    "d"
                ]
            },
            "expected_output": "bar=[c, d]\nfoo=[[a], [b]]\n"
        }
    ]
}
```

---

### Feature 4: Short-Option Lexing

**As a developer**, I want to use compact short-option syntax, so I can type terse command lines the way established CLI tools allow.

**Expected Behavior / Usage:**

Several short options may be concatenated into a single token; a trailing short option that needs a value takes the remainder of the token as an embedded value, or the next token if the remainder is empty. A unique prefix (abbreviation) of a longer option name is accepted, while a prefix that could match more than one option is rejected as ambiguous, listing the candidates. The set of prefix characters is configurable, and concatenation works with the configured prefix. A token that looks like a negative number is treated as a value rather than an option unless a matching numeric option is defined; an undefined numeric-looking option is unrecognized, and a numeric option still requires its own value.

**Test Cases:** `rcb_tests/public_test_cases/feature4_short_option_lexing.json`

```json
{
    "description": "Lexing of single-prefix short options: several boolean/short options may be concatenated into one token, and a trailing option that needs a value takes the rest of the token as its embedded value (or, if empty, the next token); a unique prefix of a longer option name is accepted while an ambiguous prefix that could match several options is rejected; an alternative prefix character can be configured and still supports concatenation; and tokens that look like negative numbers are treated as values rather than options unless a matching numeric option is defined.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "flags": [
                            "-1"
                        ],
                        "action": "store_true"
                    },
                    {
                        "flags": [
                            "-2"
                        ]
                    },
                    {
                        "flags": [
                            "-3"
                        ]
                    },
                    {
                        "flags": [
                            "-ff"
                        ]
                    },
                    {
                        "flags": [
                            "-f"
                        ]
                    },
                    {
                        "flags": [
                            "-c"
                        ],
                        "action": "append_const",
                        "const": true
                    }
                ],
                "argv": [
                    "-123=x",
                    "-ff=a",
                    "-fx",
                    "-cccc"
                ]
            },
            "expected_output": "1=true\n2=3=x\n3=null\nc=[true, true, true, true]\nf=x\nff=a\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "flags": [
                            "-a"
                        ],
                        "action": "store_true"
                    },
                    {
                        "flags": [
                            "-b"
                        ]
                    },
                    {
                        "flags": [
                            "-aaa"
                        ],
                        "action": "store_true"
                    },
                    {
                        "flags": [
                            "-bbb"
                        ],
                        "action": "store_true"
                    }
                ],
                "argv": [
                    "-aaa"
                ]
            },
            "expected_output": "a=false\naaa=true\nb=null\nbbb=false\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "flags": [
                            "-x"
                        ]
                    },
                    {
                        "name": "foo",
                        "nargs": "?"
                    }
                ],
                "argv": [
                    "-x",
                    "-1"
                ]
            },
            "expected_output": "foo=null\nx=-1\n"
        }
    ]
}
```

---

### Feature 5: Type Conversion

**As a developer**, I want to convert raw operands into typed values, so I can work with integers, enumerated values, and booleans instead of bare strings.

**Expected Behavior / Usage:**

Each argument may declare a converter applied to every operand before binding. Integer conversion yields numbers (including across a list-valued positional). Enumerated conversion by name matches a member's symbolic name; enumerated conversion by display string matches a member's display text, which may differ from its name. Boolean conversion accepts a configurable pair of literals. A value that does not convert is rejected with a diagnostic that names the offending input and lists the acceptable values in a brace-enclosed set.

**Test Cases:** `rcb_tests/public_test_cases/feature5_type_conversion.json`

```json
{
    "description": "Convert raw string operands into typed values before binding them. Covers integer conversion (including across a list-valued positional), conversion to an enumerated value matched by its symbolic member name, conversion to an enumerated value matched by its display string (which may differ from the member name), and conversion to a boolean restricted to a configurable pair of accepted literals. A value that does not convert is rejected with a diagnostic naming the offending input and the set of acceptable values.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "foo",
                        "nargs": "*",
                        "type": "int"
                    }
                ],
                "argv": [
                    "1",
                    "2",
                    "3"
                ]
            },
            "expected_output": "foo=[1, 2, 3]\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "flags": [
                            "--c"
                        ],
                        "type": "enum"
                    }
                ],
                "argv": [
                    "--c",
                    "GREEN"
                ]
            },
            "expected_output": "c=GREEN\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "flags": [
                            "--c"
                        ],
                        "type": "enum"
                    }
                ],
                "argv": [
                    "--c",
                    "PURPLE"
                ]
            },
            "expected_output": "error: argument --c: could not convert 'PURPLE' (choose from {RED,GREEN,BLUE})\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "flags": [
                            "--s"
                        ],
                        "type": "enumstr"
                    }
                ],
                "argv": [
                    "--s",
                    "X-LARGE"
                ]
            },
            "expected_output": "s=X-LARGE\n"
        }
    ]
}
```

---

### Feature 6: Choice and Range Validation

**As a developer**, I want to restrict an argument to a fixed set or numeric range, so I can reject invalid input early with a helpful message.

**Expected Behavior / Usage:**

An argument may constrain its accepted values to an explicit set or a numeric range, validated after type conversion. A value inside the set/range is accepted and bound; a value outside it is rejected with a diagnostic naming the offending value and listing the allowed choices — a brace-enclosed enumeration for a set, or a brace-enclosed `low..high` span for a range. The same validation applies to a value embedded in a multi-value argument.

**Test Cases:** `rcb_tests/public_test_cases/feature6_choices_validation.json`

```json
{
    "description": "Restrict an argument's accepted values to a fixed set or a numeric range, validating each operand after type conversion. A value within the allowed set/range is accepted and bound; a value outside it is rejected with a diagnostic that names the offending value and lists the allowed choices (a brace-enclosed enumeration for a set, or a brace-enclosed 'low..high' span for a range). The same validation applies to embedded values of a multi-value argument.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "flags": [
                            "--foo"
                        ],
                        "choices": [
                            "chocolate",
                            "icecream",
                            "froyo"
                        ]
                    }
                ],
                "argv": [
                    "--foo",
                    "icecream"
                ]
            },
            "expected_output": "foo=icecream\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "flags": [
                            "--foo"
                        ],
                        "choices": [
                            "chocolate",
                            "icecream",
                            "froyo"
                        ]
                    }
                ],
                "argv": [
                    "--foo",
                    "pudding"
                ]
            },
            "expected_output": "error: argument --foo: invalid choice: 'pudding' (choose from {chocolate,icecream,froyo})\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "flags": [
                            "--port"
                        ],
                        "type": "int",
                        "choices": {
                            "range": [
                                1025,
                                65535
                            ]
                        }
                    }
                ],
                "argv": [
                    "--port",
                    "3000"
                ]
            },
            "expected_output": "port=3000\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "flags": [
                            "--port"
                        ],
                        "type": "int",
                        "choices": {
                            "range": [
                                1025,
                                65535
                            ]
                        }
                    }
                ],
                "argv": [
                    "--port",
                    "80"
                ]
            },
            "expected_output": "error: argument --port: invalid choice: '80' (choose from {1025..65535})\n"
        }
    ]
}
```

---

### Feature 7: End-of-Options Separator

**As a developer**, I want to force the parser to stop interpreting options, so I can pass operands that look like options or values.

**Expected Behavior / Usage:**

A bare double-prefix token (`--`) marks the end of options: every subsequent token is treated as a positional operand even if it begins with a prefix character or otherwise looks like an option. Tokens after the separator fill the remaining positionals in order.

**Test Cases:** `rcb_tests/public_test_cases/feature7_argument_separator.json`

```json
{
    "description": "A bare double-prefix token ('--') marks the end of options: every token after it is treated as a positional operand even if it looks like an option or a value. Tokens following the separator are assigned to the remaining positionals in order.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "flags": [
                            "--foo"
                        ]
                    },
                    {
                        "flags": [
                            "-2"
                        ]
                    },
                    {
                        "name": "bar"
                    },
                    {
                        "name": "car"
                    }
                ],
                "argv": [
                    "--",
                    "-2",
                    "--"
                ]
            },
            "expected_output": "2=null\nbar=-2\ncar=--\nfoo=null\n"
        }
    ]
}
```

---

### Feature 8: Parse Error Reporting

**As a developer**, I want to receive clear errors when the input is invalid, so I can tell the user exactly what went wrong.

**Expected Behavior / Usage:**

Invalid input produces a single neutral diagnostic line. Covered conditions: a required optional that was not supplied; too few operands for required positionals (including fixed-count and one-or-more quantifiers); leftover tokens that match no declared argument, reported as unrecognized; and, when the automatic help option is disabled, the help flag itself reported as unrecognized.

**Test Cases:** `rcb_tests/public_test_cases/feature8_error_conditions.json`

```json
{
    "description": "Surface user-facing parse errors as a neutral diagnostic line. Covers: a required optional that was not supplied; too few operands for required positionals (including fixed-count and one-or-more quantifiers); leftover tokens that match no argument reported as unrecognized; and, when automatic help is disabled, the help flag itself being reported as unrecognized.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "flags": [
                            "--foo"
                        ],
                        "required": true
                    }
                ],
                "argv": []
            },
            "expected_output": "error: argument --foo is required\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "foo"
                    }
                ],
                "argv": []
            },
            "expected_output": "error: too few arguments\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "foo"
                    }
                ],
                "argv": [
                    "alpha",
                    "bravo",
                    "charlie"
                ]
            },
            "expected_output": "error: unrecognized arguments: 'bravo charlie'\n"
        }
    ]
}
```

---

### Feature 9: Mutually Exclusive Groups

**As a developer**, I want to declare that at most one of several arguments may be used, so I can model alternatives that cannot be combined.

**Expected Behavior / Usage:**

Arguments may be grouped so that at most one member is allowed. A single member is accepted and bound. Supplying two members of the same group is rejected, naming the conflicting pair. A group may be marked required, so supplying none of its members is rejected, listing the group's members. Conflict detection also applies when members are concatenated into one short-option token.

**Test Cases:** `rcb_tests/public_test_cases/feature9_mutex_groups.json`

```json
{
    "description": "Group arguments so at most one may be supplied. A single member is accepted and bound; supplying two members of the same group is rejected naming the conflicting pair; a group may be marked required so omitting all of its members is rejected listing the group's members; and the conflict detection applies even when members are concatenated into one short-option token.",
    "cases": [
        {
            "input": {
                "groups": [
                    {
                        "kind": "mutex",
                        "title": "mutex",
                        "arguments": [
                            {
                                "flags": [
                                    "--foo"
                                ]
                            },
                            {
                                "flags": [
                                    "--bar"
                                ]
                            }
                        ]
                    }
                ],
                "argv": [
                    "--foo",
                    "bar"
                ]
            },
            "expected_output": "bar=null\nfoo=bar\n"
        },
        {
            "input": {
                "groups": [
                    {
                        "kind": "mutex",
                        "title": "mutex",
                        "arguments": [
                            {
                                "flags": [
                                    "--foo"
                                ]
                            },
                            {
                                "flags": [
                                    "--bar"
                                ]
                            }
                        ]
                    }
                ],
                "argv": [
                    "--foo",
                    "bar",
                    "--bar",
                    "baz"
                ]
            },
            "expected_output": "error: argument --bar: not allowed with argument --foo\n"
        },
        {
            "input": {
                "groups": [
                    {
                        "kind": "mutex",
                        "title": "mutex",
                        "required": true,
                        "arguments": [
                            {
                                "flags": [
                                    "--foo"
                                ]
                            },
                            {
                                "flags": [
                                    "--bar"
                                ]
                            }
                        ]
                    }
                ],
                "argv": []
            },
            "expected_output": "error: one of the arguments --foo --bar is required\n"
        }
    ]
}
```

---

### Feature 10: Subcommands

**As a developer**, I want to dispatch to named subcommands each with their own arguments, so I can build multi-command tools where each command has its own interface.

**Expected Behavior / Usage:**

A parser may declare named subcommands, each with its own arguments and its own defaults. Selecting a subcommand merges that subcommand's operands and defaults into the result. Subcommands may declare aliases. A unique prefix of a subcommand name is accepted, while an ambiguous prefix is rejected listing the candidates. The chosen command name may be recorded under a configured destination. Omitting the subcommand entirely, or placing it after the end-of-options separator, is reported as an error.

**Test Cases:** `rcb_tests/public_test_cases/feature10_subcommands.json`

```json
{
    "description": "Dispatch to one of several named subcommands, each with its own arguments and its own defaults. The chosen subcommand's operands and defaults are merged into the result; subcommands may declare aliases; a unique prefix of a subcommand name is accepted while an ambiguous prefix is rejected listing the candidates; the chosen command name can be recorded under a configured destination; and omitting the subcommand, or placing it after the end-of-options separator, is reported as an error.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "flags": [
                            "-f"
                        ]
                    }
                ],
                "subparsers": {
                    "parsers": [
                        {
                            "name": "install",
                            "arguments": [
                                {
                                    "name": "pkg1"
                                }
                            ],
                            "defaults": {
                                "func": "install"
                            }
                        },
                        {
                            "name": "search",
                            "arguments": [
                                {
                                    "name": "pkg2"
                                }
                            ],
                            "defaults": {
                                "func": "search"
                            }
                        }
                    ]
                },
                "argv": [
                    "install",
                    "aria2"
                ]
            },
            "expected_output": "f=null\nfunc=install\npkg1=aria2\n"
        },
        {
            "input": {
                "subparsers": {
                    "parsers": [
                        {
                            "name": "checkout",
                            "aliases": [
                                "co"
                            ],
                            "defaults": {
                                "func": "checkout"
                            }
                        }
                    ]
                },
                "argv": [
                    "co"
                ]
            },
            "expected_output": "func=checkout\n"
        },
        {
            "input": {
                "subparsers": {
                    "parsers": [
                        {
                            "name": "clone",
                            "defaults": {
                                "func": "clone"
                            }
                        },
                        {
                            "name": "clean",
                            "defaults": {
                                "func": "clean"
                            }
                        }
                    ]
                },
                "argv": [
                    "cl"
                ]
            },
            "expected_output": "error: ambiguous command: cl could match clean, clone\n"
        }
    ]
}
```

---

### Feature 11: Usage, Help, and Version Text

**As a developer**, I want to render the parser's self-documentation, so I can give users discoverable, well-formatted guidance.

**Expected Behavior / Usage:**

The parser can render three kinds of text. The one-line usage summary is auto-generated from the declared optionals, required optionals, mutually-exclusive groups, and positionals, and may be overridden by a usage template in which `${prog}` is substituted. The full help body lays out the usage line, an optional description, an optional-arguments section (including the auto-added help entry), named argument groups and mutually-exclusive groups, an optional rendering of each argument's default value, a subcommand listing with aliases, and an optional epilog. The version string substitutes `${prog}` and is rendered verbatim.

**Test Cases:** `rcb_tests/public_test_cases/feature11_usage_help_version.json`

```json
{
    "description": "Render the parser's self-documentation as text. Covers the one-line usage summary (auto-generated from the declared optionals, required optionals, mutually-exclusive groups and positionals, and an overridable usage template with program-name substitution), the full help body (program usage, description, an optional-arguments section including the auto-added help entry, named argument groups and mutually-exclusive groups, optional rendering of each argument's default value, and a subcommand listing with aliases), and the version string with program-name substitution.",
    "cases": [
        {
            "input": {
                "action": "usage",
                "arguments": [
                    {
                        "flags": [
                            "-a"
                        ]
                    },
                    {
                        "flags": [
                            "-b"
                        ],
                        "required": true
                    },
                    {
                        "name": "file"
                    }
                ],
                "groups": [
                    {
                        "kind": "mutex",
                        "title": "mutex",
                        "required": true,
                        "arguments": [
                            {
                                "flags": [
                                    "-c"
                                ],
                                "required": true
                            },
                            {
                                "flags": [
                                    "-d"
                                ],
                                "required": true
                            }
                        ]
                    }
                ]
            },
            "expected_output": "usage: app [-h] [-a A] -b B (-c C | -d D) file\n"
        },
        {
            "input": {
                "action": "help",
                "description": "This is a parser.",
                "epilog": "This is epilog."
            },
            "expected_output": "usage: app [-h]\n\nThis is a parser.\n\noptional arguments:\n  -h, --help             show this help message and exit\n\nThis is epilog.\n"
        },
        {
            "input": {
                "action": "version",
                "version": "${prog} version 7.8.7 (Dreamliner)"
            },
            "expected_output": "app version 7.8.7 (Dreamliner)\n"
        }
    ]
}
```

---

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, builds the described parser, performs the requested action (`parse`/`usage`/`help`/`version`), and prints the result to stdout exactly matching the per-feature contracts above.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- consult C038 and C039 for default behavior variations
- reference the short_lex_concatenation rule in the legacy argument parser
