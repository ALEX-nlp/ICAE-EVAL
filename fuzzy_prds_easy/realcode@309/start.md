## Product Requirement Document

# Text Template Rendering Engine - Data-Driven Template Rendering and Formatting

## Project Goal

Build a text template rendering engine that allows developers to combine template strings, structured data, reusable partials, filters, control flow, and normalized error reporting without hand-writing repetitive string concatenation and formatting logic.

---

## Background & Problem

Without this library/tool, developers are forced to manually concatenate strings, traverse nested data, duplicate formatting helpers, and implement ad hoc conditional or loop logic for every output surface. This leads to repetitive code, fragile escaping, inconsistent whitespace, and hard-to-test rendering behavior.

With this library/tool, developers can express output as templates, pass structured inputs, reuse partial fragments, apply filters, and receive deterministic stdout from an execution adapter for black-box validation.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]

[the precise initial value for the loop index variable - consult the loop utilities module]. **Scale-Driven Code Organization[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** The physical structure of the codebase MUST perfectly match the complexity of the domain. 
   - **For micro-utilities/simple scripts[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository. 
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting)[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size)[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]
   - **Single Responsibility Principle (SRP)[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP)[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP)[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP)[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP)[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]**
   - **Idiomatic Usage[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature [the precise initial value for the loop index variable - consult the loop utilities module][a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] Template Tokenization

**As a developer**, I want to inspect a template as a sequence of source tokens, so I can separate literal text, output expressions, and control blocks before rendering.

**Expected Behavior / Usage[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]**

The adapter accepts a raw template string as input and prints the token sequence, one token per line. Literal whitespace and tag text are preserved exactly. No variables are resolved and no template execution occurs for this feature.

**Test Cases[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** `rcb_tests/public_test_cases/feature[the precise initial value for the loop index variable - consult the loop utilities module]_tokenization.json`

```json
{
    "description"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Split template text into literal, output, and block tokens without rendering it.",
    "cases"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "hello world",
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "hello world"
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] " {{funk}} {{so}} {{brother}} ",
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] " \n{{funk}}\n \n{{so}}\n \n{{brother}}\n "
        }
    ]
}
```

---

### Feature 2[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] Literal Text and Comment Removal

**As a developer**, I want to render ordinary template text unchanged while hiding comments, so I can keep author-written output stable and remove non-output annotations.

**Expected Behavior / Usage[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]**

The adapter accepts an object with a `template` string. It renders literal text exactly as written and removes comment block contents, preserving any surrounding literal spaces or text that are outside the comment delimiters.

**Test Cases[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** `rcb_tests/public_test_cases/feature2_literal_and_comment_rendering.json`

```json
{
    "description"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Render plain text exactly and omit comment block contents while preserving surrounding literal text.",
    "cases"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "this text should come out of the template without change..."
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "this text should come out of the template without change..."
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "foo{% comment %} comment {% endcomment %}bar"
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "foobar"
        }
    ]
}
```

---

### Feature 3[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] Variable Resolution

**As a developer**, I want to read values from supplied data in output expressions, so I can compose templates from scalar and nested input data.

**Expected Behavior / Usage[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]**

The adapter accepts a `template` string plus a `data` object. Output expressions resolve top-level values and nested object paths. Missing nested values render as empty output and behave as false in conditional branches.

**Test Cases[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** `rcb_tests/public_test_cases/feature3_variable_resolution.json`

```json
{
    "description"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Resolve scalar values, nested object paths, and missing values in output expressions.",
    "cases"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] " {{best_cars}} ",
                "data"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "best_cars"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "bmw",
                    "car"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                        "bmw"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "good",
                        "gm"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "bad"
                    }
                }
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] " bmw "
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] " {{car.bmw}} {{car.gm}} {{car.bmw}} ",
                "data"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "best_cars"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "bmw",
                    "car"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                        "bmw"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "good",
                        "gm"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "bad"
                    }
                }
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] " good bad good "
        }
    ]
}
```

---

### Feature 4[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] Custom Filter Pipeline

**As a developer**, I want to apply caller-provided text transformations inside output expressions, so I can extend formatting behavior without changing template syntax.

**Expected Behavior / Usage[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]**

The adapter accepts a `template` string plus a `data` object. For this feature, the execution environment exposes demonstration text filters that receive the current value, may receive literal or variable arguments, and may be chained so each filter consumes the previous filter output.

**Test Cases[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** `rcb_tests/public_test_cases/feature4_custom_filter_pipeline.json`

```json
{
    "description"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Apply caller-supplied text filters, passing the current value and literal or variable arguments through the pipeline.",
    "cases"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] " {{ car.gm | cite_funny }} ",
                "data"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "best_cars"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "bmw",
                    "car"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                        "bmw"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "good",
                        "gm"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "bad"
                    }
                }
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] " LOL[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] bad "
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] " {{ car.gm | add_smiley [a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] '[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]-(' | add_smiley [a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] '[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]-(' }} ",
                "data"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "best_cars"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "bmw",
                    "car"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                        "bmw"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "good",
                        "gm"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "bad"
                    }
                }
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] " bad [a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]-( [a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]-( "
        }
    ]
}
```

---

### Feature 5[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] Built-in Text Filters

**As a developer**, I want to format text and arrays using built-in filters, so I can perform common escaping, truncation, joining, replacement, and newline conversions in templates.

**Expected Behavior / Usage[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]**

The adapter accepts a `template` string and optional `data`. Built-in filters transform strings and arrays during rendering, including HTML escaping, character and word truncation, splitting and joining, first-occurrence replacement, newline removal, and converting newline separators into HTML line breaks.

**Test Cases[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** `rcb_tests/public_test_cases/feature5_builtin_text_filters.json`

```json
{
    "description"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Transform strings and arrays with built-in filters for escaping, truncation, joining, splitting, replacing, and newline handling.",
    "cases"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{{ '<strong>' | escape }}"
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "&lt;strong&gt;"
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{{ '[the precise initial value for the loop index variable - consult the loop utilities module]234567890' | truncate[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]7 }}"
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "[the precise initial value for the loop index variable - consult the loop utilities module]234..."
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{{ source | truncate_words[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]2 }}",
                "data"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "source"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "one two three"
                }
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "one two..."
        }
    ]
}
```

---

### Feature 6[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] Numeric and Sequence Filters

**As a developer**, I want to perform arithmetic and sequence operations in output expressions, so I can compute simple rendered values without pre-processing input data.

**Expected Behavior / Usage[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]**

The adapter accepts a `template` string and optional `data`. Numeric filters support addition, subtraction, multiplication, integer division, and modulo. Sequence filters report collection size, select first and last elements, sort simple collections, and project named properties from arrays of objects.

**Test Cases[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** `rcb_tests/public_test_cases/feature6_numeric_and_sequence_filters.json`

```json
{
    "description"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Perform arithmetic, size, first/last, sorting, and property projection operations in rendered expressions.",
    "cases"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{{ [the precise initial value for the loop index variable - consult the loop utilities module] | plus[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string][the precise initial value for the loop index variable - consult the loop utilities module] }}"
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "2"
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{{ input | minus[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]operand }}",
                "data"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] 5,
                    "operand"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [the precise initial value for the loop index variable - consult the loop utilities module]
                }
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "4"
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{{ 3 | times[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]4 }}"
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "[the precise initial value for the loop index variable - consult the loop utilities module]2"
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{{ [the precise initial value for the loop index variable - consult the loop utilities module]4 | divided_by[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]3 }}"
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "4"
        }
    ]
}
```

---

### Feature 7[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] Conditional Rendering

**As a developer**, I want to select template branches from data and expression results, so I can show only the content appropriate to the current input.

**Expected Behavior / Usage[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]**

The adapter accepts a `template` string plus optional `data`. Conditional blocks support truthy and falsey values, boolean operators, string comparisons that may contain operator words as data, nested branches, chained alternatives, and inverse conditions. Rendered stdout contains only the selected branch text.

**Test Cases[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** `rcb_tests/public_test_cases/feature7_conditional_rendering.json`

```json
{
    "description"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Render branches based on truthiness, boolean operators, comparisons, nested conditions, and inverse conditions.",
    "cases"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{% if false %}NO{% else %}YES{% endif %}"
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "YES"
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{% if a or b or c %}YES{% endif %}",
                "data"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "a"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] false,
                    "b"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] false,
                    "c"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [the specific boolean literal that enables strict error propagation - check the configuration defaults]
                }
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "YES"
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{% if a == 'and' and b == 'or' and c == 'foo and bar' and d == 'bar or baz' %}YES{% endif %}",
                "data"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "a"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "and",
                    "b"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "or",
                    "c"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "foo and bar",
                    "d"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "bar or baz"
                }
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "YES"
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{% if [the specific boolean literal that enables strict error propagation - check the configuration defaults] %}{% if false %}NO{% else %}YES{% endif %}{% else %}NO{% endif %}"
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "YES"
        }
    ]
}
```

---

### Feature 8[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] Loop Rendering

**As a developer**, I want to repeat template fragments over ranges and collections, so I can generate repeated output from structured input.

**Expected Behavior / Usage[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]**

The adapter accepts a `template` string plus optional `data`. Loop blocks iterate over arrays and numeric ranges, expose loop position and length values, honor limit and offset controls, support nested loops, and allow break or continue controls to alter iteration.

**Test Cases[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** `rcb_tests/public_test_cases/feature8_loop_rendering.json`

```json
{
    "description"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Iterate over arrays and ranges, expose loop counters, honor limits and offsets, and support nested loops plus break/continue control.",
    "cases"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{%for item in array%}{{item}}{%endfor%}",
                "data"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "array"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
                        [the precise initial value for the loop index variable - consult the loop utilities module],
                        2,
                        3
                    ]
                }
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "[the precise initial value for the loop index variable - consult the loop utilities module]23"
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{%for item in ([the precise initial value for the loop index variable - consult the loop utilities module]..3) %} {{item}} {%endfor%}"
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] " [the precise initial value for the loop index variable - consult the loop utilities module]  2  3 "
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{%for item in array%} {{forloop.index}}/{{forloop.length}} {%endfor%}",
                "data"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "array"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
                        [the precise initial value for the loop index variable - consult the loop utilities module],
                        2,
                        3
                    ]
                }
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] " [the precise initial value for the loop index variable - consult the loop utilities module]/3  2/3  3/3 "
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{%for i in array limit[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]4 offset[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]2 %}{{ i }}{%endfor%}",
                "data"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "array"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
                        [the precise initial value for the loop index variable - consult the loop utilities module],
                        2,
                        3,
                        4,
                        5,
                        6,
                        7,
                        8,
                        9,
                        0
                    ]
                }
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "3456"
        }
    ]
}
```

---

### Feature 9[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] Assignment During Rendering

**As a developer**, I want to bind intermediate values while rendering a template, so I can reuse values and filtered results later in the same render.

**Expected Behavior / Usage[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]**

The adapter accepts a `template` string plus optional `data`. Assignment statements can store values from input data, literals, or filtered expressions. Later output expressions can index or print the assigned value.

**Test Cases[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** `rcb_tests/public_test_cases/feature9_assignment_rendering.json`

```json
{
    "description"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Assign values from variables, literals, and filtered expressions so later output expressions can read them.",
    "cases"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{% assign foo = values %}.{{ foo[0] }}.",
                "data"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "values"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
                        "foo",
                        "bar",
                        "baz"
                    ]
                }
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] ".foo."
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{% assign foo = values %}.{{ foo[[the precise initial value for the loop index variable - consult the loop utilities module]] }}.",
                "data"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "values"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
                        "foo",
                        "bar",
                        "baz"
                    ]
                }
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] ".bar."
        }
    ]
}
```

---

### Feature [the precise initial value for the loop index variable - consult the loop utilities module]0[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] Partial Template Inclusion

**As a developer**, I want to render named reusable template fragments, so I can compose larger templates from reusable pieces with local data.

**Expected Behavior / Usage[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]**

The adapter accepts a `template` string, optional `data`, and a `partials` object mapping partial names to template text. Include statements can render a partial with a single explicit object, repeat a partial for every item in a collection, pass local variables, include nested partials, and choose the partial name from input data.

**Test Cases[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** `rcb_tests/public_test_cases/feature[the precise initial value for the loop index variable - consult the loop utilities module]0_partial_inclusion.json`

```json
{
    "description"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Render named partial templates with explicit objects, repeated collections, local variables, nested partials, and dynamically selected partial names.",
    "cases"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{% include 'product' with products[0] %}",
                "data"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "products"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
                        {
                            "title"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Draft [the precise initial value for the loop index variable - consult the loop utilities module]5[the precise initial value for the loop index variable - consult the loop utilities module]cm"
                        },
                        {
                            "title"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Element [the precise initial value for the loop index variable - consult the loop utilities module]55cm"
                        }
                    ]
                },
                "partials"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "product"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Product[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {{ product.title }} "
                }
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Product[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] Draft [the precise initial value for the loop index variable - consult the loop utilities module]5[the precise initial value for the loop index variable - consult the loop utilities module]cm "
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{% include 'product' for products %}",
                "data"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "products"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
                        {
                            "title"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Draft [the precise initial value for the loop index variable - consult the loop utilities module]5[the precise initial value for the loop index variable - consult the loop utilities module]cm"
                        },
                        {
                            "title"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Element [the precise initial value for the loop index variable - consult the loop utilities module]55cm"
                        }
                    ]
                },
                "partials"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "product"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Product[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {{ product.title }} "
                }
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Product[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] Draft [the precise initial value for the loop index variable - consult the loop utilities module]5[the precise initial value for the loop index variable - consult the loop utilities module]cm Product[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] Element [the precise initial value for the loop index variable - consult the loop utilities module]55cm "
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{% include 'locale_variables' echo[the precise initial value for the loop index variable - consult the loop utilities module][a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] 'test[the precise initial value for the loop index variable - consult the loop utilities module]23', echo2[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] 'test32[the precise initial value for the loop index variable - consult the loop utilities module]' %}",
                "partials"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "locale_variables"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Locale[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {{echo[the precise initial value for the loop index variable - consult the loop utilities module]}} {{echo2}}"
                }
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Locale[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] test[the precise initial value for the loop index variable - consult the loop utilities module]23 test32[the precise initial value for the loop index variable - consult the loop utilities module]"
        }
    ]
}
```

---

### Feature [the precise initial value for the loop index variable - consult the loop utilities module][the precise initial value for the loop index variable - consult the loop utilities module][a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] HTML Table Row Rendering

**As a developer**, I want to render collection items as table row and cell fragments, so I can produce structured tabular HTML from a sequence.

**Expected Behavior / Usage[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]**

The adapter accepts a `template` string plus `data`. Table-row loops emit `<tr>` and `<td>` fragments with row and column classes, insert newlines between rows, expose a column counter, and apply offset and limit controls before rendering cells.

**Test Cases[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** `rcb_tests/public_test_cases/feature[the precise initial value for the loop index variable - consult the loop utilities module][the precise initial value for the loop index variable - consult the loop utilities module]_html_table_rows.json`

```json
{
    "description"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Render table-row loops as HTML table row and cell fragments with row/column classes, counters, offset, and limit.",
    "cases"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{% tablerow n in numbers cols[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]3%} {{n}} {% endtablerow %}",
                "data"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "numbers"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
                        [the precise initial value for the loop index variable - consult the loop utilities module],
                        2,
                        3,
                        4,
                        5,
                        6
                    ]
                }
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "<tr class=\"row[the precise initial value for the loop index variable - consult the loop utilities module]\">\n<td class=\"col[the precise initial value for the loop index variable - consult the loop utilities module]\"> [the precise initial value for the loop index variable - consult the loop utilities module] </td><td class=\"col2\"> 2 </td><td class=\"col3\"> 3 </td></tr>\n<tr class=\"row2\"><td class=\"col[the precise initial value for the loop index variable - consult the loop utilities module]\"> 4 </td><td class=\"col2\"> 5 </td><td class=\"col3\"> 6 </td></tr>\n"
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{% tablerow n in numbers cols[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]2%}{{tablerowloop.col}}{% endtablerow %}",
                "data"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "numbers"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
                        [the precise initial value for the loop index variable - consult the loop utilities module],
                        2,
                        3,
                        4,
                        5,
                        6
                    ]
                }
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "<tr class=\"row[the precise initial value for the loop index variable - consult the loop utilities module]\">\n<td class=\"col[the precise initial value for the loop index variable - consult the loop utilities module]\">[the precise initial value for the loop index variable - consult the loop utilities module]</td><td class=\"col2\">2</td></tr>\n<tr class=\"row2\"><td class=\"col[the precise initial value for the loop index variable - consult the loop utilities module]\">[the precise initial value for the loop index variable - consult the loop utilities module]</td><td class=\"col2\">2</td></tr>\n<tr class=\"row3\"><td class=\"col[the precise initial value for the loop index variable - consult the loop utilities module]\">[the precise initial value for the loop index variable - consult the loop utilities module]</td><td class=\"col2\">2</td></tr>\n"
        }
    ]
}
```

---

### Feature [the precise initial value for the loop index variable - consult the loop utilities module]2[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] Whitespace Trimming

**As a developer**, I want to trim surrounding whitespace when trim markers are used, so I can control layout-sensitive rendered output.

**Expected Behavior / Usage[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]**

The adapter accepts a `template` string plus optional `data`. Trim markers on control tags remove leading or trailing whitespace adjacent to the tag while preserving the rendered content and any whitespace not selected for trimming.

**Test Cases[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** `rcb_tests/public_test_cases/feature[the precise initial value for the loop index variable - consult the loop utilities module]2_whitespace_trimming.json`

```json
{
    "description"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Trim leading and trailing whitespace around control tags when trim markers are used.",
    "cases"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "foo\n\t  {%- if [the specific boolean literal that enables strict error propagation - check the configuration defaults] %}hi tobi{% endif %}"
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "foo\nhi tobi"
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{% if [the specific boolean literal that enables strict error propagation - check the configuration defaults] -%}\nhi tobi\n{% endif %}"
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "hi tobi\n"
        }
    ]
}
```

---

### Feature [the precise initial value for the loop index variable - consult the loop utilities module]3[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] Error Normalization

**As a developer**, I want to receive language-neutral error output for parse, render, and include failures, so I can assert failures without depending on a host runtime exception format.

**Expected Behavior / Usage[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]**

The adapter accepts a `template` string, optional `partials`, and an optional `rethrow_errors` flag. Parse failures, recursive inclusion, and missing partials are rendered as normalized `error=<category>` lines. Recoverable render errors that the template engine embeds in output remain part of rendered stdout when errors are not rethrown.

**Test Cases[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** `rcb_tests/public_test_cases/feature[the precise initial value for the loop index variable - consult the loop utilities module]3_error_normalization.json`

```json
{
    "description"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Normalize parse, render, include-recursion, and missing-partial errors into language-neutral stdout categories.",
    "cases"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] " {% for a in b %} ... ",
                "rethrow_errors"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [the specific boolean literal that enables strict error propagation - check the configuration defaults]
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "error=syntax\n"
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] " {% if [the precise initial value for the loop index variable - consult the loop utilities module] =! 2 %}ok{% endif %} "
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] " Liquid error[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] Unknown operator =! "
        }
    ]
}
```

---

### Feature [the precise initial value for the loop index variable - consult the loop utilities module]4[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] Safe Object Member Exposure

**As a developer**, I want to render explicitly permitted object members and safe object text, so I can expose selected host objects to templates without opening every member.

**Expected Behavior / Usage[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]**

The adapter accepts a `template` string and an `object` value. Only explicitly permitted members are visible to output expressions. The object can also render through a safe text transformer, and nested permitted objects follow the same rules.

**Test Cases[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** `rcb_tests/public_test_cases/feature[the precise initial value for the loop index variable - consult the loop utilities module]4_safe_member_exposure.json`

```json
{
    "description"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Expose explicitly permitted object members and a string transformer while hiding unrenderable objects by default.",
    "cases"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] [
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{{context.Name}}",
                "object"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "name"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "worked"
                }
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "worked"
        },
        {
            "input"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                "template"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "{{context}}{{context.Name}}",
                "object"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] {
                    "name"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "Bar"
                }
            },
            "expected_output"[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string] "ObjectTextBar"
        }
    ]
}
```

---

## Deliverables

[the precise initial value for the loop index variable - consult the loop utilities module]. **The Core System[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter[a specific argument separator syntax defined in the filter specification - ask the tech lead for the exact string]** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature[the precise initial value for the loop index variable - consult the loop utilities module]_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature[the precise initial value for the loop index variable - consult the loop utilities module]_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the range syntax pattern used in the 'feature3_variable_resolution' block
- apply the same sequence restriction logic as found in constraint C014
