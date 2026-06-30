## Product Requirement Document

# Typed Argument Parser - Declarative, Type-Safe Command-Line Argument Parsing

## Project Goal

Build a command-line argument parser that lets developers declare each argument as a typed field (a name, an optional type, and an optional default) and have parsing, type conversion, validation, defaulting, and required-checking derived automatically from those declarations, so command-line programs gain type safety without hand-written conversion and validation boilerplate.

---

## Background & Problem

Without this library, developers configure a general-purpose argument parser imperatively: every option is registered with a separate call that repeats its name, its conversion function, its default, and whether it is required. The declared shape of the program's inputs is scattered across procedural setup code, type information is lost (everything arrives as text unless manually converted), and there is no single object whose fields describe the whole input surface. This leads to repetitive, error-prone boilerplate and weak typing.

With this library, the set of arguments is declared once as typed fields. The parser infers the conversion type, the default, and whether the field is required directly from the declaration; it converts each command-line token to the right type (including collections, optionals, literals/choices, and paths); it validates choices, tuple arity, and required-ness; and it exposes the resolved arguments as a single mapping that can also be repopulated from a mapping. Subcommands, configuration files, dash-style flag names, accumulation actions, and a known-only mode round out the surface.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain. This is a non-trivial domain (type inference, conversion, validation, collections, subcommands, config files); it MUST be organized into clear modules (e.g. type-resolution, conversion/enforcement, the parser core, and the execution adapter) rather than a single monolithic file. Do not over-engineer, but strictly avoid a "god file".

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core parsing logic must remain completely decoupled from standard I/O and JSON parsing. The execution adapter alone translates a JSON request into idiomatic calls on the core parser and renders the result.

3. **Adherence to SOLID Design Principles:** Separate type resolution, conversion/validation, parsing/routing, and output formatting into distinct cohesive units; keep the core open for extension (new element types, new actions) but closed for modification; depend on abstractions rather than on I/O details.

4. **Robustness & Interface Design:** The public interface must be elegant and idiomatic to the target language. Errors must be modeled properly (a usage failure, a file-not-found failure, an invalid-type-configuration failure, an invalid-request failure) rather than as generic faults, and must be reported through the neutral error contract below.

---

## Execution Adapter Request & Output Contract

The execution adapter reads ONE JSON request object from stdin, drives the core parser, and writes the resolved arguments (or a neutral error line) to stdout.

**Request shape** (all keys optional unless noted):

- `arguments`: ordered list of field declarations, each `{"name": str, "type"?: <annotation string>, "default"?: <value>}`. Omitting `type` declares an untyped field; omitting `default` makes an annotated field required. Annotation strings use the conventional type-hint surface, e.g. `"int"`, `"float"`, `"str"`, `"bool"`, `"List"`, `"List[int]"`, `"Set[int]"`, `"Tuple[int, ...]"`, `"Tuple[int, str]"`, `"Optional[int]"`, `"Union[int, float]"`, `"Literal['a', 'b']"`, `"Path"`.
- `configure`: ordered list of additional registrations, each `{"flags": [str, ...], "kwargs": {...}}`, used for flag aliases, positionals (a flag with no leading dash), default/type overrides (`"type"` given as one of `"int"|"float"|"str"|"bool"`), and accumulation actions (`"action"`, `"const"`, `"nargs"`).
- `init`: parser construction options — `"underscores_to_dashes"` (bool), `"explicit_bool"` (bool), `"config_files"` (list of paths), `"config_files_content"` (list of file contents, each materialized into a temporary config file).
- `subparsers`: `{"settings": {...}, "items": [{"flag": str, "spec": <nested request>, "kwargs"?: {...}}, ...]}` to register subcommands.
- `argv`: the command-line tokens to parse.
- `parse`: parsing options — `{"known_only": bool}`.
- `from_dict`: a name-to-value mapping to populate the parser from, instead of parsing `argv`.
- `parse_twice` / `add_argument_post_init`: lifecycle-misuse probes.
- `show`: which sections to render, a list drawn from `"values"` (the resolved mapping) and `"extra"` (the collected unknown tokens). Default is `["values"]`.

Values that need a concrete non-JSON type use tagged objects: `{"__set__": [...]}` for a set, `{"__tuple__": [...]}` for a tuple, `{"__path__": "..."}` for a path.

**Output contract** (raw stdout, compared byte-for-byte):

- The resolved mapping renders one `name=<token>` line per field, sorted by field name, each line terminated by a newline. An empty mapping renders no output.
- A scalar token is type-tagged: `int:<n>`, `float:<repr>`, `str:<text>`, `bool:True`/`bool:False`, `none`, `path:<text>`.
- A list renders as `[t0, t1, ...]`, a tuple as `(t0, t1, ...)`, and a set as `{t0, t1, ...}` with element tokens sorted lexicographically for determinism.
- The unknown-token section renders as `[a placeholder for the bracketed array content]...]`.
- Errors are normalized to a single neutral line: `error=usage` (a parse/usage failure such as a missing required argument, an invalid choice, or a tuple arity/type violation), `error=file_not_found` (a missing config file), `error=invalid_type_configuration` (an un-parseable type declaration such as an ambiguous union or an empty tuple type), or `error=invalid_request` (a lifecycle misuse or a mapping missing a required field). Errors MUST NOT leak any host-language runtime details.

---

## Core Features

### Feature 1: Declaring Arguments and Inferring Types

**As a developer**, I want to declare typed, untyped, and forward-referenced arguments without boilerplate.

**Expected Behavior / Usage:**

*1.1 Typed scalar arguments*

A field is declared by a name, an optional type annotation, and an optional default. When the corresponding flag is absent from the command line the resolved value is the declared default; when the flag is supplied the trailing token is converted to the annotated type. The resolved arguments are rendered as one `name=token` line per field, where `token` is a typed token (see Output Contract).

**Test Cases:** `rcb_tests/public_test_cases/feature01_typed_scalar.json`

```json
{
    "description": "Declare a single argument annotated with a scalar type and an inline default value. When the command line does not supply the flag, the parsed value equals the declared default. When the flag is supplied, the parsed value is the string token taken from the command line. The rendered output lists the field name and its typed value.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "greeting",
                        "type": "str",
                        "default": "sup"
                    }
                ],
                "argv": []
            },
            "expected_output": "greeting=str:sup\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "greeting",
                        "type": "str",
                        "default": "sup"
                    }
                ],
                "argv": [
                    "--greeting",
                    "yo"
                ]
            },
            "expected_output": "greeting=str:yo\n"
        }
    ]
}
```

*1.2 Untyped arguments*

An argument declared with a default but no type keeps its default when absent and, when supplied, takes the command-line text verbatim with no numeric conversion. A flag registered at configuration time with no backing default simply captures the supplied text.

**Test Cases:** `rcb_tests/public_test_cases/feature02_untyped_argument.json`

```json
{
    "description": "Arguments may be declared with only a default value and no type annotation, or added at configuration time with no annotation at all. An untyped argument keeps its default when the flag is absent; when supplied on the command line its value is taken verbatim as text (no numeric conversion is inferred). A configuration-time flag with no backing default simply captures the supplied text.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "hi",
                        "default": 3
                    }
                ],
                "argv": []
            },
            "expected_output": "[e.g., 'name=value:50']\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "hi",
                        "default": 3
                    }
                ],
                "argv": [
                    "--hi",
                    "yo"
                ]
            },
            "expected_output": "hi=str:yo\n"
        }
    ]
}
```

*1.3 String (forward-reference) annotations*

A string annotation is resolved to the equivalent type and drives the same conversion: a scalar numeric string annotation converts the token to a number, and a parameterized collection string annotation converts each whitespace-separated token element-wise. Defaults apply when the flag is absent.

**Test Cases:** `rcb_tests/public_test_cases/feature03_string_annotation.json`

```json
{
    "description": "Type annotations may be provided as strings (forward references) rather than as live type objects; they are resolved to the same behavior. A scalar string annotation drives numeric conversion and a parameterized collection string annotation drives element-wise conversion of a whitespace-separated list. Defaults apply when flags are absent.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "a_number",
                        "type": "int",
                        "default": 3
                    },
                    {
                        "name": "a_list",
                        "type": "List[float]",
                        "default": [
                            3.7,
                            0.3
                        ]
                    }
                ],
                "argv": []
            },
            "expected_output": "a_list=[float:3.7, float:0.3]\na_number=int:3\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "a_number",
                        "type": "int",
                        "default": 3
                    },
                    {
                        "name": "a_list",
                        "type": "List[float]",
                        "default": [
                            3.7,
                            0.3
                        ]
                    }
                ],
                "argv": [
                    "--a_number",
                    "42",
                    "--a_list",
                    "3",
                    "4",
                    "0.7"
                ]
            },
            "expected_output": "a_list=[float:3.0, float:4.0, float:0.7]\na_number=int:42\n"
        }
    ]
}
```

---

### Feature 2: Required and Optional Arguments

**As a developer**, I want to distinguish mandatory inputs from optional ones that may be absent.

**Expected Behavior / Usage:**

*2.1 Required arguments*

An annotated field with no default is required. If any required field is missing the parse fails with a usage error (rendered as the neutral line `error=usage`). When all required fields are supplied the parse succeeds and converts each value by its annotation.

**Test Cases:** `rcb_tests/public_test_cases/feature04_required_arguments.json`

```json
{
    "description": "An annotated argument with no default value is required. If any required argument is missing from the command line the parse fails with a usage error. When every required argument is supplied the parse succeeds and the values are converted according to their annotations.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "arg_str_required",
                        "type": "str"
                    },
                    {
                        "name": "arg_list_str_required",
                        "type": "List[str]"
                    }
                ],
                "argv": [
                    "--arg_str_required",
                    "tappy"
                ]
            },
            "expected_output": "error=usage\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "arg_str_required",
                        "type": "str"
                    },
                    {
                        "name": "arg_list_str_required",
                        "type": "List[str]"
                    }
                ],
                "argv": [
                    "--arg_str_required",
                    "tappy",
                    "--arg_list_str_required",
                    "hi",
                    "there"
                ]
            },
            "expected_output": "arg_list_str_required=[str:hi, str:there]\narg_str_required=str:tappy\n"
        }
    ]
}
```

*2.2 Optional-typed arguments*

An optional field (an inner type combined with the absence of a value) defaults to a none token and, when supplied, converts the token to the inner type. Multiple optional fields of different inner types are converted independently.

**Test Cases:** `rcb_tests/public_test_cases/feature08_optional_types.json`

```json
{
    "description": "An optional-typed argument defaults to an empty (none) value and, when supplied, converts the command-line text to the inner type. Several optional arguments of different inner types can coexist; each is converted independently.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "opt_str",
                        "type": "Optional[str]",
                        "default": null
                    },
                    {
                        "name": "opt_int",
                        "type": "Optional[int]",
                        "default": null
                    },
                    {
                        "name": "opt_float",
                        "type": "Optional[float]",
                        "default": null
                    }
                ],
                "argv": []
            },
            "expected_output": "opt_float=none\nopt_int=none\nopt_str=none\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "opt_str",
                        "type": "Optional[str]",
                        "default": null
                    },
                    {
                        "name": "opt_int",
                        "type": "Optional[int]",
                        "default": null
                    },
                    {
                        "name": "opt_float",
                        "type": "Optional[float]",
                        "default": null
                    }
                ],
                "argv": [
                    "--opt_str",
                    "hello",
                    "--opt_int",
                    "77",
                    "--opt_float",
                    "7.7"
                ]
            },
            "expected_output": "opt_float=float:7.7\nopt_int=int:77\nopt_str=str:hello\n"
        }
    ]
}
```

---

### Feature 3: Boolean Arguments

**As a developer**, I want to express on/off options either as bare flags or as explicit truth values.

**Expected Behavior / Usage:**

*3.1 Implicit boolean flags*

A boolean field with a default becomes a no-argument flag. Supplying the flag yields the opposite of the default (a true-default reads false when present; a false-default reads true when present). Absent flags keep their defaults.

**Test Cases:** `rcb_tests/public_test_cases/feature05_implicit_bool.json`

```json
{
    "description": "A boolean argument with a default value becomes a no-argument flag whose presence flips it to the opposite of its default: a field defaulting to true reads as false when the flag is given, and a field defaulting to false reads as true when the flag is given. When neither flag is present both keep their declared defaults.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "arg_true",
                        "type": "bool",
                        "default": true
                    },
                    {
                        "name": "arg_false",
                        "type": "bool",
                        "default": false
                    }
                ],
                "argv": []
            },
            "expected_output": "arg_false=bool:False\narg_true=bool:True\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "arg_true",
                        "type": "bool",
                        "default": true
                    },
                    {
                        "name": "arg_false",
                        "type": "bool",
                        "default": false
                    }
                ],
                "argv": [
                    "--arg_true",
                    "--arg_false"
                ]
            },
            "expected_output": "arg_false=bool:True\narg_true=bool:False\n"
        }
    ]
}
```

*3.2 Explicit boolean values*

In explicit-boolean mode a boolean flag requires a truth-value argument. Truthy spellings (full word, single letter, or `1`) parse to true and falsy spellings (full word, single letter, or `0`) parse to false, in any capitalization. Omitting the value after the flag, or omitting a required boolean entirely, is a usage error.

**Test Cases:** `rcb_tests/public_test_cases/feature06_explicit_bool.json`

```json
{
    "description": "In explicit-boolean mode a boolean argument expects a literal truth value as its argument. Truthy spellings (full word, single letter, or one) parse to true and falsy spellings (full word, single letter, or zero) parse to false, in any capitalization. Omitting the value after the flag, or omitting a required boolean entirely, is a usage error.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "is_gpu",
                        "type": "bool"
                    }
                ],
                "init": {
                    "explicit_bool": true
                },
                "argv": [
                    "--is_gpu",
                    "True"
                ]
            },
            "expected_output": "is_gpu=bool:True\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "is_gpu",
                        "type": "bool"
                    }
                ],
                "init": {
                    "explicit_bool": true
                },
                "argv": [
                    "--is_gpu",
                    "False"
                ]
            },
            "expected_output": "is_gpu=bool:False\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "is_gpu",
                        "type": "bool"
                    }
                ],
                "init": {
                    "explicit_bool": true
                },
                "argv": [
                    "--is_gpu"
                ]
            },
            "expected_output": "error=usage\n"
        }
    ]
}
```

---

### Feature 4: Literal (Choice-Restricted) Arguments

**As a developer**, I want to restrict an argument to a fixed set of typed options.

**Expected Behavior / Usage:**

A literal-typed field accepts only the enumerated options and converts the chosen value to the type of the matching option (string option stays text, numeric option becomes a number, boolean option becomes a boolean). A value outside the allowed set is a usage error; the default is used when the flag is absent.

**Test Cases:** `rcb_tests/public_test_cases/feature07_literal_choices.json`

```json
{
    "description": "A literal-typed argument restricts the accepted values to a fixed set of allowed options and converts the chosen value to the type of the matching option (so a string option stays text, a numeric option becomes a number, and a boolean option becomes a boolean). Supplying a value outside the allowed set is a usage error. The default is used when the flag is absent.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "arg_literal",
                        "type": "Literal['english', 'A', True, 88.9, 100]",
                        "default": "A"
                    }
                ],
                "argv": [
                    "--arg_literal",
                    "88.9"
                ]
            },
            "expected_output": "arg_literal=float:88.9\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "arg_lit",
                        "type": "Literal['125', 'no, 3 sir']"
                    }
                ],
                "argv": [
                    "--arg_lit",
                    "[any integer not in the allowed set, e.g., '123']"
                ]
            },
            "expected_output": "error=usage\n"
        }
    ]
}
```

---

### Feature 5: Collection Arguments

**As a developer**, I want to gather multiple command-line tokens into typed lists, sets, and tuples.

**Expected Behavior / Usage:**

*5.1 List arguments*

A list field consumes all whitespace-separated tokens after its flag and converts each element to the declared element type (a bare list keeps strings; typed lists convert to integers, floats, or booleans). Element order is preserved and rendered inside `[ ... ]`.

**Test Cases:** `rcb_tests/public_test_cases/feature09_list_arguments.json`

```json
{
    "description": "A list-typed argument consumes all whitespace-separated tokens following its flag and converts each element to the declared element type (bare list keeps strings, and typed lists convert to integers, floats, or booleans). Element order is preserved.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "list_",
                        "type": "List"
                    },
                    {
                        "name": "list_int",
                        "type": "List[int]"
                    },
                    {
                        "name": "list_str",
                        "type": "List[str]"
                    },
                    {
                        "name": "list_bool",
                        "type": "List[bool]"
                    }
                ],
                "argv": [
                    "--list_",
                    "I",
                    "was",
                    "wondering",
                    "--list_int",
                    "0",
                    "1",
                    "2",
                    "--list_str",
                    "a",
                    "bee",
                    "cd",
                    "ee",
                    "--list_bool",
                    "True",
                    "False"
                ]
            },
            "expected_output": "list_=[str:I, str:was, str:wondering]\nlist_bool=[bool:True, bool:False]\nlist_int=[int:0, int:1, int:2]\nlist_str=[str:a, str:bee, str:cd, str:ee]\n"
        }
    ]
}
```

*5.2 Set arguments*

A set field consumes the whitespace-separated tokens after its flag, converts each to the declared element type, and keeps only unique values. Membership (not order) is significant; the rendered form lists elements inside `{ ... }` sorted by their token text for determinism.

**Test Cases:** `rcb_tests/public_test_cases/feature10_set_arguments.json`

```json
{
    "description": "A set-typed argument consumes the whitespace-separated tokens after its flag, converts each to the declared element type, and collapses duplicate values into a unique collection (membership only, order not significant).",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "set_int",
                        "type": "Set[int]"
                    },
                    {
                        "name": "set_str",
                        "type": "Set[str]"
                    }
                ],
                "argv": [
                    "--set_int",
                    "1",
                    "2",
                    "2",
                    "3",
                    "--set_str",
                    "a",
                    "bee",
                    "cd"
                ]
            },
            "expected_output": "set_int={int:1, int:2, int:3}\nset_str={str:a, str:bee, str:cd}\n"
        }
    ]
}
```

*5.3 Tuple arguments*

A tuple field fixes its element count and per-position types. A bare tuple keeps an arbitrary number of string elements; a single-element typed tuple yields one converted element; a homogeneous ellipsis tuple converts an arbitrary number of elements to one type; and a fully enumerated tuple converts each position to its own type. Order is preserved and rendered inside `( ... )`.

**Test Cases:** `rcb_tests/public_test_cases/feature11_tuple_arguments.json`

```json
{
    "description": "A tuple-typed argument fixes the number and per-position types of its elements. A bare tuple keeps an arbitrary number of string elements; a single-element typed tuple yields one converted element; a homogeneous ellipsis tuple converts an arbitrary number of elements to one type; and a fully enumerated tuple converts each position to its own declared type.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "tup_str",
                        "type": "Tuple[str]"
                    },
                    {
                        "name": "tup_int",
                        "type": "Tuple[int]"
                    },
                    {
                        "name": "tup_float",
                        "type": "Tuple[float]"
                    },
                    {
                        "name": "tup_bool",
                        "type": "Tuple[bool]"
                    }
                ],
                "argv": [
                    "--tup_str",
                    "hello",
                    "--tup_int",
                    "445",
                    "--tup_float",
                    "7.9",
                    "--tup_bool",
                    "tru"
                ]
            },
            "expected_output": "tup_bool=(bool:True)\ntup_float=(float:7.9)\ntup_int=(int:445)\ntup_str=(str:hello)\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "tup_int",
                        "type": "Tuple[int, ...]"
                    },
                    {
                        "name": "tup_bool",
                        "type": "Tuple[bool, ...]"
                    }
                ],
                "argv": [
                    "--tup_int",
                    "2",
                    "3",
                    "4",
                    "--tup_bool",
                    "false",
                    "true",
                    "0",
                    "1",
                    "tru"
                ]
            },
            "expected_output": "tup_bool=(bool:False, bool:True, bool:False, bool:True, bool:True)\ntup_int=(int:2, int:3, int:4)\n"
        }
    ]
}
```

*5.4 Tuple validation errors*

A typed tuple enforces element count and per-position types: a non-convertible element, the wrong number of elements, or elements that violate the position types all fail with a usage error. Declaring an empty tuple type is rejected up front (`error=invalid_type_configuration`).

**Test Cases:** `rcb_tests/public_test_cases/feature12_tuple_errors.json`

```json
{
    "description": "A typed tuple enforces both the count and the per-position types of its elements. Supplying an element that cannot be converted to its declared type, supplying the wrong number of elements, or supplying elements in an order that violates the position types, all fail with a usage error. Declaring an empty tuple type is rejected up front as an invalid type configuration.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "tup",
                        "type": "Tuple[int]"
                    }
                ],
                "argv": [
                    "--tup",
                    "tomato"
                ]
            },
            "expected_output": "error=usage\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "tup",
                        "type": "Tuple[()]"
                    }
                ],
                "argv": []
            },
            "expected_output": "error=invalid_type_configuration\n"
        }
    ]
}
```

*5.5 Non-collection defaults on collection fields*

When a collection-typed field is given a default that is not a collection (such as an empty/none value or a bare scalar) and the flag is not supplied, the declared default is returned unchanged with no collection conversion applied.

**Test Cases:** `rcb_tests/public_test_cases/feature13_noncollection_default.json`

```json
{
    "description": "If a collection-typed argument is given a default that is not itself a collection (for example an empty/none value or a bare scalar), and the flag is not supplied on the command line, the declared default value is returned unchanged without any collection conversion.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "set_1",
                        "type": "Set[str]",
                        "default": null
                    },
                    {
                        "name": "set_2",
                        "type": "Set[int]",
                        "default": 3.7
                    }
                ],
                "argv": []
            },
            "expected_output": "set_1=none\nset_2=float:3.7\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "tup_1",
                        "type": "Tuple[int, str]",
                        "default": null
                    },
                    {
                        "name": "tup_2",
                        "type": "Tuple[str, int]",
                        "default": 3
                    }
                ],
                "argv": []
            },
            "expected_output": "tup_1=none\ntup_2=int:3\n"
        }
    ]
}
```

---

### Feature 6: Path-Typed Arguments

**As a developer**, I want to wrap inputs into filesystem-path values, alone or inside containers.

**Expected Behavior / Usage:**

A path type is supported as a scalar element and inside optional, list, set, and tuple containers. Each token is wrapped into a path value; path collections keep their respective semantics (list ordered, set unique, tuple fixed-length). A path token renders as `path:<text>`.

**Test Cases:** `rcb_tests/public_test_cases/feature14_path_types.json`

```json
{
    "description": "A filesystem-path type is supported as a scalar element type and inside optional, list, set, and tuple containers. Each supplied token is wrapped into a path value; collections of paths preserve their respective semantics (list ordered, set unique, tuple fixed-length).",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "path",
                        "type": "Path"
                    },
                    {
                        "name": "optional_path",
                        "type": "Optional[Path]"
                    },
                    {
                        "name": "list_path",
                        "type": "List[Path]"
                    },
                    {
                        "name": "tuple_path",
                        "type": "Tuple[Path, Path]"
                    }
                ],
                "argv": [
                    "--path",
                    "/path/to/file.txt",
                    "--optional_path",
                    "/path/to/optional/file.txt",
                    "--list_path",
                    "/path/to/list/file1.txt",
                    "/path/to/list/file2.txt",
                    "--tuple_path",
                    "/path/to/tuple/file1.txt",
                    "/path/to/tuple/file2.txt"
                ]
            },
            "expected_output": "list_path=[path:/path/to/list/file1.txt, path:/path/to/list/file2.txt]\noptional_path=path:/path/to/optional/file.txt\npath=path:/path/to/file.txt\ntuple_path=(path:/path/to/tuple/file1.txt, path:/path/to/tuple/file2.txt)\n"
        }
    ]
}
```

---

### Feature 7: Ambiguous Unions Require an Explicit Converter

**As a developer**, I want to be forced to disambiguate multi-type unions instead of guessing.

**Expected Behavior / Usage:**

A general union of two or more concrete types (anything other than an optional, i.e. a type combined with the absence of a value) cannot be parsed automatically. Declaring such a union without an explicit conversion function is rejected as an invalid type configuration (`error=invalid_type_configuration`).

**Test Cases:** `rcb_tests/public_test_cases/feature15_union_requires_converter.json`

```json
{
    "description": "A general union of two or more concrete types (other than an optional, i.e. a type combined with none) cannot be parsed automatically because the parser cannot know which member type to convert to. Declaring such a union without supplying an explicit conversion function is rejected as an invalid type configuration.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "arg",
                        "type": "Union[int, float]"
                    }
                ],
                "argv": []
            },
            "expected_output": "error=invalid_type_configuration\n"
        }
    ]
}
```

---

### Feature 8: Retrieving and Populating Argument Values

**As a developer**, I want to read all resolved arguments as a mapping and restore them from one.

**Expected Behavior / Usage:**

*8.1 Retrieve as a mapping*

After a successful parse the complete set of resolved arguments is available as a mapping. It includes typed fields, untyped fields, optional fields (with their none defaults), collection fields, and any field introduced under a renamed destination at configuration time. This is the default rendered view.

**Test Cases:** `rcb_tests/public_test_cases/feature16_as_dict.json`

```json
{
    "description": "After parsing, the full set of resolved arguments can be retrieved as a name-to-value mapping. The mapping includes typed fields, untyped fields, optional fields (with their none defaults), and collection fields, as well as arguments introduced under a renamed destination at configuration time.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "a",
                        "type": "str"
                    },
                    {
                        "name": "b",
                        "default": 1
                    },
                    {
                        "name": "c",
                        "type": "bool",
                        "default": true
                    },
                    {
                        "name": "d",
                        "type": "Tuple[str, ...]",
                        "default": {
                            "__tuple__": [
                                "hi",
                                "bob"
                            ]
                        }
                    },
                    {
                        "name": "e",
                        "type": "Optional[int]",
                        "default": null
                    },
                    {
                        "name": "f",
                        "type": "Set[int]",
                        "default": {
                            "__set__": [
                                1
                            ]
                        }
                    }
                ],
                "argv": [
                    "--a",
                    "hi"
                ]
            },
            "expected_output": "a=str:hi\nb=int:1\nc=bool:True\nd=(str:hi, str:bob)\ne=none\nf={int:1}\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "a",
                        "type": "str"
                    },
                    {
                        "name": "b",
                        "default": 1
                    }
                ],
                "configure": [
                    {
                        "flags": [
                            "-arg_name",
                            "--long_arg_name"
                        ]
                    }
                ],
                "argv": [
                    "--a",
                    "hi",
                    "--long_arg_name",
                    "arg"
                ]
            },
            "expected_output": "a=str:hi\nb=int:1\nlong_arg_name=str:arg\n"
        }
    ]
}
```

*8.2 Populate from a mapping*

Populating from a mapping reproduces the same retrievable arguments as command-line parsing. If the mapping omits a required field that has no default, population fails with an invalid-request error (`error=invalid_request`).

**Test Cases:** `rcb_tests/public_test_cases/feature17_from_dict.json`

```json
{
    "description": "A parser can be populated directly from a name-to-value mapping instead of from the command line, reproducing the same retrievable arguments. If the mapping omits a required argument that has no default, population fails with an invalid-request error.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "a",
                        "type": "str"
                    },
                    {
                        "name": "d",
                        "type": "Tuple[str, ...]"
                    },
                    {
                        "name": "b",
                        "default": 1
                    },
                    {
                        "name": "c",
                        "type": "bool",
                        "default": true
                    },
                    {
                        "name": "e",
                        "type": "Optional[int]",
                        "default": null
                    },
                    {
                        "name": "f",
                        "type": "Set[int]",
                        "default": {
                            "__set__": [
                                1
                            ]
                        }
                    }
                ],
                "from_dict": {
                    "a": "hi",
                    "d": {
                        "__tuple__": [
                            "a",
                            "b"
                        ]
                    },
                    "b": 1,
                    "c": true,
                    "e": 7,
                    "f": {
                        "__set__": [
                            1
                        ]
                    }
                }
            },
            "expected_output": "a=str:hi\nb=int:1\nc=bool:True\nd=(str:a, str:b)\ne=int:7\nf={int:1}\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "a",
                        "type": "str"
                    },
                    {
                        "name": "b",
                        "default": 1
                    }
                ],
                "from_dict": {
                    "b": 1
                }
            },
            "expected_output": "error=invalid_request\n"
        }
    ]
}
```

---

### Feature 9: Ignoring Unknown Arguments

**As a developer**, I want to consume known flags and collect the rest for downstream tools.

**Expected Behavior / Usage:**

In known-only mode the parser consumes recognized arguments (converting them normally) and gathers every unrecognized token, in order, into a separate extra-arguments list instead of failing. The extra list is rendered as an additional `[a placeholder for the bracketed array content] ... ]` line.

**Test Cases:** `rcb_tests/public_test_cases/feature18_known_only.json`

```json
{
    "description": "In known-only mode the parser consumes the arguments it recognizes and collects every unrecognized command-line token, in order, into a separate extra-arguments list rather than failing. Recognized arguments are still converted normally.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "arg_int",
                        "type": "int",
                        "default": 2
                    }
                ],
                "argv": [
                    "--arg_int",
                    "3"
                ],
                "parse": {
                    "known_only": true
                },
                "show": [
                    "values",
                    "extra"
                ]
            },
            "expected_output": "arg_int=int:3\n[a placeholder for the bracketed array content]]\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "arg_int",
                        "type": "int",
                        "default": 2
                    }
                ],
                "argv": [
                    "--arg_int",
                    "3",
                    "--arg_float",
                    "3.3"
                ],
                "parse": {
                    "known_only": true
                },
                "show": [
                    "values",
                    "extra"
                ]
            },
            "expected_output": "arg_int=int:3\n[a placeholder for the bracketed array content]str:--arg_float, str:3.3]\n"
        }
    ]
}
```

---

### Feature 10: Dash-Style Flag Naming

**As a developer**, I want to spell multi-word flags with dashes while keeping underscore attributes.

**Expected Behavior / Usage:**

With underscore-to-dash conversion enabled, multi-word flags are spelled with dashes on the command line while resolved attribute names keep underscores. This applies both to annotated fields and to flags registered at configuration time.

**Test Cases:** `rcb_tests/public_test_cases/feature19_underscores_to_dashes.json`

```json
{
    "description": "When underscore-to-dash conversion is enabled, multi-word flag names are spelled with dashes on the command line instead of underscores, while the resolved attribute names keep their underscore form. This applies to annotated fields and to flags registered at configuration time.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "arg",
                        "type": "int",
                        "default": 10
                    },
                    {
                        "name": "arg_u_ment",
                        "type": "int",
                        "default": 10
                    },
                    {
                        "name": "arg_you_mean_",
                        "type": "int",
                        "default": 10
                    }
                ],
                "init": {
                    "underscores_to_dashes": true
                },
                "argv": [
                    "--arg",
                    "11",
                    "--arg-u-ment",
                    "12",
                    "--arg-you-mean-",
                    "13"
                ]
            },
            "expected_output": "arg=int:11\narg_u_ment=int:12\narg_you_mean_=int:13\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "foo_arg",
                        "type": "str",
                        "default": "foo_arg"
                    },
                    {
                        "name": "foo_arg_2",
                        "type": "Optional[int]",
                        "default": null
                    }
                ],
                "configure": [
                    {
                        "flags": [
                            "-f",
                            "--foo-arg"
                        ]
                    },
                    {
                        "flags": [
                            "-f2",
                            "--foo-arg-2"
                        ]
                    }
                ],
                "init": {
                    "underscores_to_dashes": true
                },
                "argv": [
                    "-f2",
                    "2"
                ]
            },
            "expected_output": "foo_arg=str:foo_arg\nfoo_arg_2=int:2\n"
        }
    ]
}
```

---

### Feature 11: Configuration Files

**As a developer**, I want to load arguments from files with clear precedence and error handling.

**Expected Behavior / Usage:**

*11.1 Loading and precedence*

Arguments can be loaded from configuration files containing command-line-style flag tokens. Command-line arguments override config values, and among multiple config files later files override earlier ones. Config content supports shell-style comments and quoted multi-word values.

**Test Cases:** `rcb_tests/public_test_cases/feature20_config_files.json`

```json
{
    "description": "Arguments can be loaded from one or more configuration files, each containing command-line-style flag tokens. Command-line arguments override config values; among multiple config files, later files override earlier ones. Config content supports shell-style comments and quoted multi-word values.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "a",
                        "type": "int"
                    },
                    {
                        "name": "b",
                        "type": "str",
                        "default": "b"
                    }
                ],
                "init": {
                    "config_files_content": [
                        "--a 1"
                    ]
                },
                "argv": []
            },
            "expected_output": "a=int:1\nb=str:b\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "a",
                        "type": "int"
                    },
                    {
                        "name": "b",
                        "type": "str",
                        "default": "b"
                    }
                ],
                "init": {
                    "config_files_content": [
                        "--a 1 --b two"
                    ]
                },
                "argv": [
                    "--a",
                    "2"
                ]
            },
            "expected_output": "a=int:2\nb=str:two\n"
        }
    ]
}
```

*11.2 Configuration errors*

Pointing at a nonexistent config path fails with a file-not-found error (`error=file_not_found`); content that cannot be tokenized into valid flags fails with a usage error; and a required field still unprovided after applying all config files and the command line fails with a usage error.

**Test Cases:** `rcb_tests/public_test_cases/feature21_config_errors.json`

```json
{
    "description": "Configuration-file handling fails cleanly: pointing at a path that does not exist raises a file-not-found error; content that cannot be parsed as valid flag tokens raises a usage error; and a required argument that is still not provided by any config file or the command line raises a usage error.",
    "cases": [
        {
            "input": {
                "arguments": [],
                "init": {
                    "config_files": [
                        "nope"
                    ]
                },
                "argv": []
            },
            "expected_output": "error=file_not_found\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "a",
                        "type": "int"
                    },
                    {
                        "name": "b",
                        "type": "str",
                        "default": "b"
                    }
                ],
                "init": {
                    "config_files_content": [
                        "--b fore"
                    ]
                },
                "argv": []
            },
            "expected_output": "error=usage\n"
        }
    ]
}
```

---

### Feature 12: Accumulating Actions

**As a developer**, I want to build up values from repeated flags via append, count, and extend.

**Expected Behavior / Usage:**

Configuration-time fields can opt into accumulation: an append action adds one converted value per occurrence onto the list default; an append-constant action appends a fixed constant per occurrence; a count action tallies occurrences onto a numeric default; and an extend action flattens multiple multi-valued occurrences into the default list.

**Test Cases:** `rcb_tests/public_test_cases/feature22_actions.json`

```json
{
    "description": "Configuration-time arguments can opt into accumulation behaviors: an append action collects one converted value per occurrence onto the list default; an append-constant action appends a fixed constant per occurrence; a count action tallies the number of occurrences onto a numeric default; and an extend action flattens multiple multi-valued occurrences into the default list.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "arg",
                        "type": "List[int]",
                        "default": [
                            1,
                            2
                        ]
                    }
                ],
                "configure": [
                    {
                        "flags": [
                            "--arg"
                        ],
                        "kwargs": {
                            "action": "append"
                        }
                    }
                ],
                "argv": [
                    "--arg",
                    "3",
                    "--arg",
                    "4"
                ]
            },
            "expected_output": "arg=[int:1, int:2, int:3, int:4]\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "arg",
                        "type": "int",
                        "default": 7
                    }
                ],
                "configure": [
                    {
                        "flags": [
                            "--arg",
                            "-a"
                        ],
                        "kwargs": {
                            "action": "count"
                        }
                    }
                ],
                "argv": [
                    "-aaa",
                    "--arg"
                ]
            },
            "expected_output": "arg=int:11\n"
        }
    ]
}
```

---

### Feature 13: Subcommands

**As a developer**, I want to expose distinct command modes each with their own arguments.

**Expected Behavior / Usage:**

A parser can register named subcommands. Selecting a subcommand activates only that subcommand's arguments; top-level arguments remain available before the subcommand token. With no subcommand selected, only top-level arguments are present, and a subcommand's own arguments are absent unless that subcommand is chosen.

**Test Cases:** `rcb_tests/public_test_cases/feature23_subparsers.json`

```json
{
    "description": "A parser can register named subcommands, each with its own arguments. Selecting a subcommand on the command line activates only that subcommand's arguments; the top-level arguments remain available before the subcommand token. When no subcommand is selected, only the top-level arguments are present. A subcommand's own arguments are unavailable unless that subcommand is chosen.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "foo",
                        "type": "bool",
                        "default": false
                    }
                ],
                "subparsers": {
                    "items": [
                        {
                            "flag": "a",
                            "spec": {
                                "arguments": [
                                    {
                                        "name": "bar",
                                        "type": "int"
                                    }
                                ]
                            }
                        },
                        {
                            "flag": "b",
                            "spec": {
                                "arguments": [
                                    {
                                        "name": "baz",
                                        "type": "Literal['X', 'Y', 'Z']"
                                    }
                                ]
                            }
                        }
                    ]
                },
                "argv": [
                    "a",
                    "--bar",
                    "1"
                ]
            },
            "expected_output": "bar=int:1\nfoo=bool:False\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "foo",
                        "type": "bool",
                        "default": false
                    }
                ],
                "subparsers": {
                    "items": [
                        {
                            "flag": "a",
                            "spec": {
                                "arguments": [
                                    {
                                        "name": "bar",
                                        "type": "int"
                                    }
                                ]
                            }
                        },
                        {
                            "flag": "b",
                            "spec": {
                                "arguments": [
                                    {
                                        "name": "baz",
                                        "type": "Literal['X', 'Y', 'Z']"
                                    }
                                ]
                            }
                        }
                    ]
                },
                "argv": [
                    "--foo",
                    "b",
                    "--baz",
                    "X"
                ]
            },
            "expected_output": "baz=str:X\nfoo=bool:True\n"
        }
    ]
}
```

---

### Feature 14: Overriding Inferred Settings

**As a developer**, I want to fine-tune a field's inferred default, type, and flag aliases.

**Expected Behavior / Usage:**

Re-declaring an annotated field at configuration time overrides inferred settings: a supplied default replaces the inferred one, and a supplied conversion type replaces the inferred type (a numeric field can be forced to stay text). A flag may expose single-dash and double-dash aliases.

**Test Cases:** `rcb_tests/public_test_cases/feature24_override_inferred.json`

```json
{
    "description": "Re-declaring an annotated field at configuration time lets the developer override the inferred settings: a supplied default replaces the inferred one, and a supplied conversion type replaces the inferred type (so a field annotated as numeric can be forced to stay text). Flags may use a single dash, double dash, or both as aliases.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "arg_str",
                        "type": "str",
                        "default": "hello there"
                    }
                ],
                "configure": [
                    {
                        "flags": [
                            "--arg_str"
                        ],
                        "kwargs": {
                            "default": "yo dude"
                        }
                    }
                ],
                "argv": []
            },
            "expected_output": "arg_str=str:yo dude\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "arg_int",
                        "type": "int",
                        "default": -100
                    }
                ],
                "configure": [
                    {
                        "flags": [
                            "--arg_int"
                        ],
                        "kwargs": {
                            "type": "str"
                        }
                    }
                ],
                "argv": [
                    "--arg_int",
                    "yo dude"
                ]
            },
            "expected_output": "arg_int=str:yo dude\n"
        }
    ]
}
```

---

### Feature 15: Lifecycle Errors

**As a developer**, I want to have parser misuse reported rather than silently mishandled.

**Expected Behavior / Usage:**

Parsing the command line more than once on the same parser instance is an invalid request, and adding a new argument after the parser has finished initializing is likewise an invalid request (`error=invalid_request`).

**Test Cases:** `rcb_tests/public_test_cases/feature25_lifecycle_errors.json`

```json
{
    "description": "The parser enforces its usage lifecycle. Parsing the command line more than once on the same parser instance is an invalid request, and adding a new argument after the parser has finished initializing is likewise an invalid request.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "a",
                        "type": "int",
                        "default": 5
                    }
                ],
                "argv": [
                    "--a",
                    "6"
                ],
                "parse_twice": true
            },
            "expected_output": "error=invalid_request\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "a",
                        "type": "int",
                        "default": 5
                    }
                ],
                "argv": [],
                "add_argument_post_init": {
                    "flags": [
                        "--arg"
                    ]
                }
            },
            "expected_output": "error=invalid_request\n"
        }
    ]
}
```

---

### Feature 16: Positional Arguments

**As a developer**, I want to accept order-based inputs that are still typed by their annotation.

**Expected Behavior / Usage:**

A field registered as a positional (no leading dash) at configuration time still draws its conversion type from the matching annotated field, so the positional token is converted to the declared type. Positional names are never rewritten by underscore-to-dash conversion.

**Test Cases:** `rcb_tests/public_test_cases/feature26_positional.json`

```json
{
    "description": "An argument can be registered as a positional (no leading dash) at configuration time while still drawing its type from the matching annotated field, so the positional token is converted to the declared type. Positional names are never rewritten by underscore-to-dash conversion.",
    "cases": [
        {
            "input": {
                "arguments": [
                    {
                        "name": "a",
                        "type": "int"
                    }
                ],
                "configure": [
                    {
                        "flags": [
                            "a"
                        ]
                    }
                ],
                "argv": [
                    "1"
                ]
            },
            "expected_output": "a=int:1\n"
        },
        {
            "input": {
                "arguments": [
                    {
                        "name": "under_score",
                        "type": "int"
                    }
                ],
                "configure": [
                    {
                        "flags": [
                            "under_score"
                        ]
                    }
                ],
                "init": {
                    "underscores_to_dashes": true
                },
                "argv": [
                    "1"
                ]
            },
            "expected_output": "under_score=int:1\n"
        }
    ]
}
```

---

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-module codebase implementing the features above (type resolution, conversion/validation, the parser core), decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON request from stdin, drives the core parser per the Request & Output Contract above, and prints the resolved mapping (or a neutral error line) to stdout. It must be logically (and ideally physically) separate from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{stem}@{index:03d}.txt` containing **only** the raw stdout from the program under test, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- check the 'configure' section for the 'long_arg_name' mapping
- refer to the usage_error_categories enum definition
