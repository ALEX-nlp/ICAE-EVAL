## Product Requirement Document

# Contract Source Lexical Scanner - Tokenizes a Stack-Oriented Contract Language

## Project Goal

Build a lexical scanner for a stack-oriented smart-contract source language that allows developers to turn raw source text into a deterministic token stream without writing ad hoc source-splitting logic.

---

## Background & Problem

Without this library/tool, developers are forced to manually scan comments, declarations, interface parameter lists, macro bodies, operation mnemonics, labels, [literal handling rules for hardcoded values]s, and punctuation. This leads to fragile parsing, inconsistent span reporting, and repetitive boilerplate across compiler and tooling layers.

With this library/tool, callers provide source text and receive a stable line-oriented token stream with categories, rendered values, and byte spans that can be consumed by parsers, formatters, analyzers, and test adapters.

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

### Feature 1: Declaration Keywords

**As a developer**, I want to recognize declaration starts, so I can route declarations without requiring a full parser.

**Expected Behavior / Usage:**

The scanner reads source text and emits one line per visible token. Declaration directives and declaration-kind words are recognized only where a declaration starts. Output lines use `token=<category>:<lexeme> span=<start>..<end>`; when [whitespace emission toggle logic] is skipped, spans still refer to the original byte positions.

**Test Cases:** `rcb_tests/public_test_cases/feature1_declaration_keywords.json`

```json
{
    "description": "Recognizes declaration directives and declaration-kind keywords at declaration starts.",
    "cases": [
        {
            "input": {
                "source": "#define macro",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=directive:#define span=0..7\ntoken=keyword:macro span=8..13\n"
        },
        {
            "input": {
                "source": "#define function",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=directive:#define span=0..7\ntoken=keyword:function span=8..16\n"
        }
    ]
}
```

---

### Feature 2: Comment Preservation

**As a developer**, I want to retain comments as lexical tokens, so I can support tools that need source-preserving analysis.

**Expected Behavior / Usage:**

The scanner must recognize both line comments and block comments as comment tokens. When [whitespace emission toggle logic] is not skipped, newline and space runs are emitted as [whitespace emission toggle logic] tokens between the comment and following source tokens.

**Test Cases:** `rcb_tests/public_test_cases/feature2_comments.json`

```json
{
    "description": "Preserves source comments as comment tokens while continuing with following declarations.",
    "cases": [
        {
            "input": {
                "source": "// comment contents \n#define macro HELLO_WORLD()",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=comment:// comment contents  span=0..20\ntoken=[whitespace emission toggle logic] span=20..21\ntoken=directive:#define span=21..28\ntoken=[whitespace emission toggle logic] span=28..29\ntoken=keyword:macro span=29..34\ntoken=[whitespace emission toggle logic] span=34..35\ntoken=ident:HELLO_WORLD span=35..46\ntoken=symbol:( span=46..47\ntoken=symbol:) span=47..48\n"
        },
        {
            "input": {
                "source": "/* comment contents*/#define macro HELLO_WORLD()",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=comment:/* comment contents*/ span=0..21\ntoken=directive:#define span=21..28\ntoken=[whitespace emission toggle logic] span=28..29\ntoken=keyword:macro span=29..34\ntoken=[whitespace emission toggle logic] span=34..35\ntoken=ident:HELLO_WORLD span=35..46\ntoken=symbol:( span=46..47\ntoken=symbol:) span=47..48\n"
        }
    ]
}
```

---

### Feature 3: Include Directives and Paths

**As a developer**, I want to read include statements, so I can discover dependency paths from source text.

**Expected Behavior / Usage:**

The scanner recognizes include directives and treats both double-quoted and single-quoted path [literal handling rules for hardcoded values]s as string tokens without the surrounding quote characters. Whitespace may be emitted when requested by input options.

**Test Cases:** `rcb_tests/public_test_cases/feature3_include_paths.json`

```json
{
    "description": "Recognizes include directives and quoted include path strings.",
    "cases": [
        {
            "input": {
                "source": "#include",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=directive:#include span=0..8\n"
        },
        {
            "input": {
                "source": "#include \"./huffs/Ownable.huff\"",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=directive:#include span=0..8\ntoken=[whitespace emission toggle logic] span=8..9\ntoken=string:./huffs/Ownable.huff span=9..31\n"
        }
    ]
}
```

---

### Feature 4: Macro Arity Keywords

**As a developer**, I want to recognize stack-count clauses, so I can understand macro input and output arity declarations.

**Expected Behavior / Usage:**

Within a macro declaration header, stack-count clause words are emitted as keyword tokens whether the following parenthesized [[literal handling rules for hardcoded values] handling rules for hardcoded values] is separated by [whitespace emission toggle logic] or attached directly. Numeric arities and grouping symbols are emitted as their own tokens.

**Test Cases:** `rcb_tests/public_test_cases/feature4_macro_stack_keywords.json`

```json
{
    "description": "Recognizes macro stack-count keywords around numeric arity declarations with loose or tight spacing.",
    "cases": [
        {
            "input": {
                "source": "#define macro TEST() = takes (0) returns (0)",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=directive:#define span=0..7\ntoken=keyword:macro span=8..13\ntoken=ident:TEST span=14..18\ntoken=symbol:( span=18..19\ntoken=symbol:) span=19..20\ntoken=symbol:= span=21..22\ntoken=keyword:takes span=23..28\ntoken=symbol:( span=29..30\ntoken=[[literal handling rules for hardcoded values] handling rules for hardcoded values]:0 span=30..31\ntoken=symbol:) span=31..32\ntoken=keyword:returns span=33..40\ntoken=symbol:( span=41..42\ntoken=[[literal handling rules for hardcoded values] handling rules for hardcoded values]:0 span=42..43\ntoken=symbol:) span=43..44\n"
        },
        {
            "input": {
                "source": "#define macro TEST() = takes(0) returns(0)",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=directive:#define span=0..7\ntoken=keyword:macro span=8..13\ntoken=ident:TEST span=14..18\ntoken=symbol:( span=18..19\ntoken=symbol:) span=19..20\ntoken=symbol:= span=21..22\ntoken=keyword:takes span=23..28\ntoken=symbol:( span=28..29\ntoken=[[literal handling rules for hardcoded values] handling rules for hardcoded values]:0 span=29..30\ntoken=symbol:) span=30..31\ntoken=keyword:returns span=32..39\ntoken=symbol:( span=39..40\ntoken=[[literal handling rules for hardcoded values] handling rules for hardcoded values]:0 span=40..41\ntoken=symbol:) span=41..42\n"
        }
    ]
}
```

---

### Feature 5: Function Qualifiers

**As a developer**, I want to recognize function qualifiers, so I can capture mutability and payment annotations from function declarations.

**Expected Behavior / Usage:**

Within a function declaration, qualifier words after the parameter list are emitted as keyword tokens, followed by the return clause and its typed return value.

**Test Cases:** `rcb_tests/public_test_cases/feature5_function_qualifiers.json`

```json
{
    "description": "Recognizes function state qualifiers and return clauses in function declarations.",
    "cases": [
        {
            "input": {
                "source": "#define function test() view returns (uint256)",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=directive:#define span=0..7\ntoken=keyword:function span=8..16\ntoken=ident:test span=17..21\ntoken=symbol:( span=21..22\ntoken=symbol:) span=22..23\ntoken=keyword:view span=24..28\ntoken=keyword:returns span=29..36\ntoken=symbol:( span=37..38\ntoken=type:uint256 span=38..45\ntoken=symbol:) span=45..46\n"
        },
        {
            "input": {
                "source": "#define function test() pure returns (uint256)",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=directive:#define span=0..7\ntoken=keyword:function span=8..16\ntoken=ident:test span=17..21\ntoken=symbol:( span=21..22\ntoken=symbol:) span=22..23\ntoken=keyword:pure span=24..28\ntoken=keyword:returns span=29..36\ntoken=symbol:( span=37..38\ntoken=type:uint256 span=38..45\ntoken=symbol:) span=45..46\n"
        }
    ]
}
```

---

### Feature 6: Primitive ABI Types

**As a developer**, I want to recognize primitive interface types, so I can build typed interface metadata from source declarations.

**Expected Behavior / Usage:**

Inside function or event parameter lists, primitive interface type words are emitted as type tokens rather than identifiers. Multiple parameters are separated by comma tokens and spans refer to the original source positions.

**Test Cases:** `rcb_tests/public_test_cases/feature6_abi_primitive_types.json`

```json
{
    "description": "Recognizes primitive ABI argument types inside function and event parameter lists.",
    "cases": [
        {
            "input": {
                "source": "#define function test(address) view returns (uint256)",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=directive:#define span=0..7\ntoken=keyword:function span=8..16\ntoken=ident:test span=17..21\ntoken=symbol:( span=21..22\ntoken=type:address span=22..29\ntoken=symbol:) span=29..30\ntoken=keyword:view span=31..35\ntoken=keyword:returns span=36..43\ntoken=symbol:( span=44..45\ntoken=type:uint256 span=45..52\ntoken=symbol:) span=52..53\n"
        },
        {
            "input": {
                "source": "#define function test(string) view returns (uint256)",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=directive:#define span=0..7\ntoken=keyword:function span=8..16\ntoken=ident:test span=17..21\ntoken=symbol:( span=21..22\ntoken=type:string span=22..28\ntoken=symbol:) span=28..29\ntoken=keyword:view span=30..34\ntoken=keyword:returns span=35..42\ntoken=symbol:( span=43..44\ntoken=type:uint256 span=44..51\ntoken=symbol:) span=51..52\n"
        },
        {
            "input": {
                "source": "#define function test(uint192) view returns (uint256)",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=directive:#define span=0..7\ntoken=keyword:function span=8..16\ntoken=ident:test span=17..21\ntoken=symbol:( span=21..22\ntoken=type:uint192 span=22..29\ntoken=symbol:) span=29..30\ntoken=keyword:view span=31..35\ntoken=keyword:returns span=36..43\ntoken=symbol:( span=44..45\ntoken=type:uint256 span=45..52\ntoken=symbol:) span=52..53\n"
        }
    ]
}
```

---

### Feature 7: Array ABI Types

**As a developer**, I want to recognize array interface types, so I can preserve fixed and open-ended array shapes.

**Expected Behavior / Usage:**

Inside parameter lists, array type forms are emitted as array tokens. Fixed-size arrays include the numeric length in the token text, while open-ended arrays use empty brackets in the output.

**Test Cases:** `rcb_tests/public_test_cases/feature7_abi_array_types.json`

```json
{
    "description": "Recognizes fixed-size and open-ended ABI array argument types.",
    "cases": [
        {
            "input": {
                "source": "#define function test(address[3]) view returns (uint256)",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=directive:#define span=0..7\ntoken=keyword:function span=8..16\ntoken=ident:test span=17..21\ntoken=symbol:( span=21..22\ntoken=array:address[3] span=22..32\ntoken=symbol:) span=32..33\ntoken=keyword:view span=34..38\ntoken=keyword:returns span=39..46\ntoken=symbol:( span=47..48\ntoken=type:uint256 span=48..55\ntoken=symbol:) span=55..56\n"
        },
        {
            "input": {
                "source": "#define function test(string[1]) view returns (uint256)",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=directive:#define span=0..7\ntoken=keyword:function span=8..16\ntoken=ident:test span=17..21\ntoken=symbol:( span=21..22\ntoken=array:string[1] span=22..31\ntoken=symbol:) span=31..32\ntoken=keyword:view span=33..37\ntoken=keyword:returns span=38..45\ntoken=symbol:( span=46..47\ntoken=type:uint256 span=47..54\ntoken=symbol:) span=54..55\n"
        }
    ]
}
```

---

### Feature 8: Contextual Identifiers

**As a developer**, I want to use reserved words as names where valid, so I can avoid misclassifying labels and references.

**Expected Behavior / Usage:**

Words that can be keywords in declarations must be emitted as ordinary identifiers or labels when they appear in name-only positions, such as function names, jump labels, or macro-body jump targets.

**Test Cases:** `rcb_tests/public_test_cases/feature8_contextual_identifiers.json`

```json
{
    "description": "Treats reserved words as ordinary identifiers or labels when they appear in identifier-only contexts.",
    "cases": [
        {
            "input": {
                "source": "#define function macro(uint256) view returns(uint256)",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=directive:#define span=0..7\ntoken=keyword:function span=8..16\ntoken=ident:macro span=17..22\ntoken=symbol:( span=22..23\ntoken=type:uint256 span=23..30\ntoken=symbol:) span=30..31\ntoken=keyword:view span=32..36\ntoken=keyword:returns span=37..44\ntoken=symbol:( span=44..45\ntoken=type:uint256 span=45..52\ntoken=symbol:) span=52..53\n"
        },
        {
            "input": {
                "source": "#define function function(uint256) view returns(uint256)",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=directive:#define span=0..7\ntoken=keyword:function span=8..16\ntoken=ident:function span=17..25\ntoken=symbol:( span=25..26\ntoken=type:uint256 span=26..33\ntoken=symbol:) span=33..34\ntoken=keyword:view span=35..39\ntoken=keyword:returns span=40..47\ntoken=symbol:( span=47..48\ntoken=type:uint256 span=48..55\ntoken=symbol:) span=55..56\n"
        },
        {
            "input": {
                "source": "#define function constant(uint256) view returns(uint256)",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=directive:#define span=0..7\ntoken=keyword:function span=8..16\ntoken=ident:constant span=17..25\ntoken=symbol:( span=25..26\ntoken=type:uint256 span=26..33\ntoken=symbol:) span=33..34\ntoken=keyword:view span=35..39\ntoken=keyword:returns span=40..47\ntoken=symbol:( span=47..48\ntoken=type:uint256 span=48..55\ntoken=symbol:) span=55..56\n"
        }
    ]
}
```

---

### Feature 9: Macro Body Operations and Labels

**As a developer**, I want to recognize virtual-machine operation mnemonics and labels inside executable bodies, so I can enable downstream tools to distinguish operations from ordinary names.

**Expected Behavior / Usage:**

After a macro body opens, supported operation mnemonics are emitted as opcode tokens containing both their operation byte value and the same byte value prefixed with `0x`. Label definitions inside the body are emitted as label tokens without the trailing colon.

**Test Cases:** `rcb_tests/public_test_cases/feature9_macro_body_opcodes_and_labels.json`

```json
{
    "description": "Recognizes operation mnemonics and jump labels only while scanning macro bodies.",
    "cases": [
        {
            "input": {
                "source": "\n            #define macro TEST() = takes(0) returns(0) {\n                lt\n            }\n            ",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=directive:#define span=13..20\ntoken=keyword:macro span=21..26\ntoken=ident:TEST span=27..31\ntoken=symbol:( span=31..32\ntoken=symbol:) span=32..33\ntoken=symbol:= span=34..35\ntoken=keyword:takes span=36..41\ntoken=symbol:( span=41..42\ntoken=[[literal handling rules for hardcoded values] handling rules for hardcoded values]:0 span=42..43\ntoken=symbol:) span=43..44\ntoken=keyword:returns span=45..52\ntoken=symbol:( span=52..53\ntoken=[[literal handling rules for hardcoded values] handling rules for hardcoded values]:0 span=53..54\ntoken=symbol:) span=54..55\ntoken=symbol:{ span=56..57\ntoken=opcode:10:0x10 span=74..76\ntoken=symbol:} span=89..90\n"
        },
        {
            "input": {
                "source": "\n            #define macro TEST() = takes(0) returns(0) {\n                gt\n            }\n            ",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=directive:#define span=13..20\ntoken=keyword:macro span=21..26\ntoken=ident:TEST span=27..31\ntoken=symbol:( span=31..32\ntoken=symbol:) span=32..33\ntoken=symbol:= span=34..35\ntoken=keyword:takes span=36..41\ntoken=symbol:( span=41..42\ntoken=[[literal handling rules for hardcoded values] handling rules for hardcoded values]:0 span=42..43\ntoken=symbol:) span=43..44\ntoken=keyword:returns span=45..52\ntoken=symbol:( span=52..53\ntoken=[[literal handling rules for hardcoded values] handling rules for hardcoded values]:0 span=53..54\ntoken=symbol:) span=54..55\ntoken=symbol:{ span=56..57\ntoken=opcode:11:0x11 span=74..76\ntoken=symbol:} span=89..90\n"
        },
        {
            "input": {
                "source": "\n            #define macro TEST() = takes(0) returns(0) {\n                eq\n            }\n            ",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=directive:#define span=13..20\ntoken=keyword:macro span=21..26\ntoken=ident:TEST span=27..31\ntoken=symbol:( span=31..32\ntoken=symbol:) span=32..33\ntoken=symbol:= span=34..35\ntoken=keyword:takes span=36..41\ntoken=symbol:( span=41..42\ntoken=[[literal handling rules for hardcoded values] handling rules for hardcoded values]:0 span=42..43\ntoken=symbol:) span=43..44\ntoken=keyword:returns span=45..52\ntoken=symbol:( span=52..53\ntoken=[[literal handling rules for hardcoded values] handling rules for hardcoded values]:0 span=53..54\ntoken=symbol:) span=54..55\ntoken=symbol:{ span=56..57\ntoken=opcode:14:0x14 span=74..76\ntoken=symbol:} span=89..90\n"
        }
    ]
}
```

---

### Feature 10: Literals, Numbers, and Built-ins

**As a developer**, I want to recognize [literal handling rules for hardcoded values] values and built-in markers, so I can preserve constants for later compilation stages.

**Expected Behavior / Usage:**

Hexadecimal byte [literal handling rules for hardcoded values]s are emitted as fixed-width [literal handling rules for hardcoded values] tokens, decimal digit runs are emitted as [[literal handling rules for hardcoded values] handling rules for hardcoded values] tokens, and the storage-pointer marker is emitted as a built-in token. Spans for hexadecimal [literal handling rules for hardcoded values]s cover the characters after the prefix.

**Test Cases:** `rcb_tests/public_test_cases/feature10_[literal handling rules for hardcoded values]s_[[literal handling rules for hardcoded values] handling rules for hardcoded values]s_and_builtin.json`

```json
{
    "description": "Recognizes numeric [literal handling rules for hardcoded values]s, hexadecimal byte [literal handling rules for hardcoded values]s, and the built-in storage pointer marker.",
    "cases": [
        {
            "input": {
                "source": "0xa57B",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=[literal handling rules for hardcoded values]:0x6135374200000000000000000000000000000000000000000000000000000000 span=2..6\n"
        },
        {
            "input": {
                "source": "00",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=[[literal handling rules for hardcoded values] handling rules for hardcoded values]:0 span=0..2\n"
        },
        {
            "input": {
                "source": "18446744073709551615",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=[[literal handling rules for hardcoded values] handling rules for hardcoded values]:18446744073709551615 span=0..20\n"
        }
    ]
}
```

---

### Feature 11: Symbols and Punctuation

**As a developer**, I want to recognize punctuation and grouping symbols, so I can preserve expression and block structure.

**Expected Behavior / Usage:**

The scanner emits assignment, brackets, braces, parentheses, arithmetic operators, division, and commas as symbol tokens. Identifier and comment tokens around those symbols remain visible according to the [whitespace emission toggle logic] option.

**Test Cases:** `rcb_tests/public_test_cases/feature11_symbols_and_punctuation.json`

```json
{
    "description": "Recognizes assignment, grouping, storage brackets, braces, arithmetic operators, division, and comma punctuation.",
    "cases": [
        {
            "input": {
                "source": "#define constant TRANSFER_EVENT_SIGNATURE =",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=directive:#define span=0..7\ntoken=[whitespace emission toggle logic] span=7..8\ntoken=keyword:constant span=8..16\ntoken=[whitespace emission toggle logic] span=16..17\ntoken=ident:TRANSFER_EVENT_SIGNATURE span=17..41\ntoken=[whitespace emission toggle logic] span=41..42\ntoken=symbol:= span=42..43\n"
        },
        {
            "input": {
                "source": "[TOTAL_SUPPLY_LOCATION] sload",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=symbol:[ span=0..1\ntoken=ident:TOTAL_SUPPLY_LOCATION span=1..22\ntoken=symbol:] span=22..23\ntoken=ident:sload span=24..29\n"
        },
        {
            "input": {
                "source": "\n#define macro CONSTRUCTOR() = takes(0) returns(0) {\n    // Set msg.sender as the owner of the contract.\n    OWNABLE_CONSTRUCTOR()\n}\n    ",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=directive:#define span=1..8\ntoken=keyword:macro span=9..14\ntoken=ident:CONSTRUCTOR span=15..26\ntoken=symbol:( span=26..27\ntoken=symbol:) span=27..28\ntoken=symbol:= span=29..30\ntoken=keyword:takes span=31..36\ntoken=symbol:( span=36..37\ntoken=[[literal handling rules for hardcoded values] handling rules for hardcoded values]:0 span=37..38\ntoken=symbol:) span=38..39\ntoken=keyword:returns span=40..47\ntoken=symbol:( span=47..48\ntoken=[[literal handling rules for hardcoded values] handling rules for hardcoded values]:0 span=48..49\ntoken=symbol:) span=49..50\ntoken=symbol:{ span=51..52\ntoken=comment:// Set msg.sender as the owner of the contract. span=57..104\ntoken=ident:OWNABLE_CONSTRUCTOR span=109..128\ntoken=symbol:( span=128..129\ntoken=symbol:) span=129..130\ntoken=symbol:} span=131..132\n"
        }
    ]
}
```

---

### Feature 12: End-of-Input Marker

**As a developer**, I want to request an explicit end marker, so I can let clients distinguish the final token from iterator exhaustion.

**Expected Behavior / Usage:**

When requested by input options, the scanner emits an explicit end-of-input token after the final source token. The end token span has equal start and end positions at the source length.

**Test Cases:** `rcb_tests/public_test_cases/feature12_end_of_input.json`

```json
{
    "description": "Emits an explicit end-of-input marker after the final source token when requested by the caller.",
    "cases": [
        {
            "input": {
                "source": " ",
                "skip_[whitespace emission toggle logic]": [whitespace emission toggle logic],
                "include_eof": [whitespace emission toggle logic]
            },
            "expected_output": "token=[whitespace emission toggle logic] span=0..1\ntoken=eof span=1..1\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_declaration_keywords.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_declaration_keywords@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.

---
**Implementation notes:**
- use the span format from the `buildTrace` helper
- append the terminator described in the output adapter notes
