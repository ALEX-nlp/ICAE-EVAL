## Product Requirement Document

# YAML Serialization Engine

## Project Goal

Build a YAML 1.2 serialization engine that converts between structured, typed
values and YAML text in both directions, driven by a schema/type description.
The engine must:

- **Decode** a YAML document into a typed value according to a requested target
  shape (primitives, enumerations, collections, structured objects, and
  polymorphic hierarchies).
- **Encode** a typed value back into a YAML document, honoring configurable
  formatting (string quoting style, sequence style, indentation, key naming
  convention, default-value emission, and polymorphic type-writing style).
- **Parse** an arbitrary document into a generic structural node tree (scalars,
  sequences, mappings, nulls, tagged nodes) without a target type.
- Report every failure through a **stable, language-neutral error contract**
  that names a category and carries structured fields (offending value, property
  name, human-readable reason, and 1-based line/column location).

The engine is exercised through a thin command interface: each test feeds one
JSON command on standard input and the program writes a single textual result
to standard output.

## Background & Problem

Configuration files, deployment manifests, and data-interchange payloads are
frequently authored in YAML because it is concise and human-friendly. Programs
that consume these files need to turn the text into strongly typed in-memory
values and, just as often, to emit typed values back out as YAML for round-trips
and code-generation.

A naive reader is not enough. Real documents rely on YAML's full scalar grammar
(hexadecimal and octal integers, scientific-notation and special floating-point
tokens, multiple boolean spellings), on optional structure (defaulted and
nullable fields, keys in any order), on anchors/aliases and document-local
extension blocks, and on several conventions for expressing *which* concrete
type a value represents (a type tag versus a discriminator property). On the
writing side, downstream tooling demands precise control over quoting,
block-versus-flow layout, indentation, and key casing.

The problem is to implement a single engine that covers this surface area
predictably, and—critically—fails *informatively*. When a document is malformed
or does not satisfy the requested shape, the engine must not crash with an opaque
message; it must classify the failure and point at the exact location, so the
calling program can surface a precise diagnostic to the user.

## Architecture & Engineering Constraints

**Command interface.** The program reads exactly one JSON object from standard
input and prints exactly one result to standard output, terminated by a single
newline. The command object has these fields:

- `op` — one of `"decode"`, `"encode"`, `"parse"`.
- `shape` — (decode/encode) a neutral selector naming the target data shape
  (e.g. `"int"`, `"string-list"`, `"named"`, `"complex"`, `"shape"`). A trailing
  `?` marks a nullable target (e.g. `"string?"`).
- `document` — (decode/parse) the YAML text to read.
- `value` — (encode) the structured value to write, expressed as JSON.
- `config` — (optional) a map of formatting/behavior options (see below).

**Output contract.**

- A successful **decode** prints the decoded value rendered as compact JSON
  (objects as `{"k":v}`, lists as `[a,b]`, strings quoted, booleans as
  `true`/`false`, null as `null`). Floating-point infinities and not-a-number
  render as `Infinity`, `-Infinity`, `NaN`.
- A successful **encode** prints the raw YAML document exactly as produced.
- A successful **parse** prints an indented textual rendering of the node tree:
  `scalar '<content>'`, `null`, `list (size: N)` with `- [i]` element headers,
  `map (size: N)` with `key '<content>'` entries (entries ordered by source
  location), and `tagged !<tag>` wrappers.

**Error contract.** Any failure prints a block whose first line is
`error=<category>` followed by `field=value` lines. Categories include:
`[standard error categories for schema violations]`, `[standard error categories for schema violations]`, `[standard error categories for schema violations]`, `[standard error categories for schema violations]`,
`[standard error categories for schema violations]`, `[standard error categories for schema violations]`, `[standard error categories for schema violations]`, `[standard error categories for schema violations]`,
`[standard error categories for schema violations]`, `[standard error categories for schema violations]`, `[standard error categories for schema violations]`, `[standard error categories for schema violations]`.
Location fields (`line`, `column`) are **1-based**. Error text must be free of
any host-language type names or runtime-specific message suffixes.

**Configuration options** (keys in `config`): `encodeDefaults`, `strictMode`,
`extensionDefinitionPrefix`, `polymorphismStyle` (`"tag"`/`"property"`/`"none"`),
`polymorphismPropertyName`, `encodingIndentationSize`, `sequenceStyle`
(`"block"`/`"flow"`), `singleLineStringStyle`
(`"double"`/`"single"`/`"plain"`/`"plain-except-ambiguous"`),
`ambiguousQuoteStyle`, `anchorsAndAliases` (`"forbidden"`/`"permitted"`),
`maxAliasCount`, `namingStrategy` (`"snake"`/`"kebab"`/`"pascal"`/`"camel"`),
`decodeEnumCaseInsensitive`.

**Engineering constraints.**

- The engine must conform to YAML 1.2 scalar and structure grammar.
- Decoding is type-directed: the same textual scalar may decode to different
  widths/types depending on the requested shape, and the result must be
  consistent across widths.
- Errors must be deterministic and carry exact source locations.
- The output must be byte-stable for identical inputs (used for golden
  comparison); no incidental ordering, whitespace, or platform variance.

## Core Features

### Feature 1: Scalar decoding

#### Feature 1.1: Integer bases and signs

Decode a scalar into an integer-like value, supporting decimal, hexadecimal
(`0x`), octal (`0o`), and negative-sign prefixes. The same textual form decodes
identically regardless of the requested integer width.

```json
{
    "description": "Decode a scalar document into an integer-like value, supporting decimal, hexadecimal (0x), octal (0o) and negative sign prefixes; the same textual forms decode identically regardless of the integer width requested.",
    "cases": [
        {
            "input": {
                "op": "decode",
                "shape": "int",
                "document": "123"
            },
            "expected_output": "123"
        }
    ]
}
```

#### Feature 1.2: Floating-point and special tokens

Decode a scalar into a floating-point value, including scientific notation and
the special tokens for positive/negative infinity and not-a-number.

```json
{
    "description": "Decode a scalar document into a floating point value, including scientific notation and the special tokens for positive/negative infinity and not-a-number.",
    "cases": [
        {
            "input": {
                "op": "decode",
                "shape": "double",
                "document": ".5"
            },
            "expected_output": "0.5"
        }
    ]
}
```

#### Feature 1.3: Booleans

Decode a scalar into a boolean. Only the lower/title/upper-case spellings of
true and false are accepted.

```json
{
    "description": "Decode a scalar document into a boolean value; only the lower/title/upper case spellings of true and false are accepted.",
    "cases": [
        {
            "input": {
                "op": "decode",
                "shape": "boolean",
                "document": "true"
            },
            "expected_output": "true"
        }
    ]
}
```

#### Feature 1.4: Strings and characters

Decode a scalar into a single string or single character value.

```json
{
    "description": "Decode a scalar document into a single string or single character value.",
    "cases": [
        {
            "input": {
                "op": "decode",
                "shape": "string",
                "document": "hello"
            },
            "expected_output": "\"hello\""
        }
    ]
}
```

#### Feature 1.5: Enumerations

Decode a scalar into an enumeration value. Members may carry explicit external
names (including names containing spaces). Matching is case-sensitive by
default; an option enables case-insensitive matching.

```json
{
    "description": "Decode a scalar document into an enumeration value. Members may carry explicit external names (including names containing spaces). By default matching is case-sensitive; an option enables case-insensitive matching.",
    "cases": [
        {
            "input": {
                "op": "decode",
                "shape": "enum",
                "document": "Value1"
            },
            "expected_output": "\"Value1\""
        }
    ]
}
```

#### Feature 1.6: Invalid scalar reporting

When a scalar cannot be interpreted as the requested type, decoding fails with a
normalized invalid-scalar error carrying the offending raw value, a human
description, and the 1-based line/column.

```json
{
    "description": "When a scalar cannot be interpreted as the requested type, decoding fails with a normalized invalid-scalar error carrying the offending raw value, a human description, and the 1-based line/column where it occurred.",
    "cases": [
        {
            "input": {
                "op": "decode",
                "shape": "enum",
                "document": "nonsense"
            },
            "expected_output": "error=[standard error categories for schema violations]\nvalue=nonsense\ndetail=Value 'nonsense' is not a valid option, permitted choices are: Value1, Value2\nline=1\ncolumn=1"
        }
    ]
}
```

### Feature 2: Collections

#### Feature 2.1: Lists

Decode a block sequence into a list whose elements are decoded with the
requested element type (numbers, booleans, characters, nullable elements, nested
lists, or objects).

```json
{
    "description": "Decode a block sequence document into a list whose elements are decoded with the requested element type (numbers, booleans, characters, nullable elements, nested lists, or objects).",
    "cases": [
        {
            "input": {
                "op": "decode",
                "shape": "string-list",
                "document": "- thing1\n- thing2\n- thing3"
            },
            "expected_output": "[\"thing1\",\"thing2\",\"thing3\"]"
        }
    ]
}
```

#### Feature 2.2: Maps

Decode a block mapping into a key/value map with the requested key and value
types.

```json
{
    "description": "Decode a block mapping document into a key/value map with the requested key and value types.",
    "cases": [
        {
            "input": {
                "op": "decode",
                "shape": "string-map",
                "document": "SOME_ENV_VAR: somevalue\nSOME_OTHER_ENV_VAR: someothervalue"
            },
            "expected_output": "{\"SOME_ENV_VAR\":\"somevalue\",\"SOME_OTHER_ENV_VAR\":\"someothervalue\"}"
        }
    ]
}
```

### Feature 3: Structured objects

#### Feature 3.1: Simple and nested objects

Decode a mapping into a structured object; nested objects and embedded lists
are decoded recursively, and mapping keys may appear in any order.

```json
{
    "description": "Decode a mapping document into a structured object; nested objects and embedded lists are decoded recursively, and mapping keys may appear in any order.",
    "cases": [
        {
            "input": {
                "op": "decode",
                "shape": "named",
                "document": "name: Alex"
            },
            "expected_output": "{\"name\":\"Alex\"}"
        }
    ]
}
```

#### Feature 3.2: Optional and defaulted fields

A field with a default value may be omitted or supplied explicitly; when omitted
the default is used.

```json
{
    "description": "A field with a default value may be omitted from the document or supplied explicitly; when omitted the default is used.",
    "cases": [
        {
            "input": {
                "op": "decode",
                "shape": "complex",
                "document": "string: Alex\nbyte: 12\nshort: 1234\nint: 123456\nlong: 1234567\nfloat: 1.2\ndouble: 2.4\nenum: Value1\nboolean: true\nchar: A\nnullable: present"
            },
            "expected_output": "{\"string\":\"Alex\",\"byte\":12,\"short\":1234,\"int\":123456,\"long\":1234567,\"float\":1.2,\"double\":2.4,\"enum\":\"Value1\",\"boolean\":true,\"char\":\"A\",\"nullable\":\"present\"}"
        }
    ]
}
```

#### Feature 3.3: Nullable fields

A nullable field accepts an explicit null and yields a null value; a
non-nullable field given null fails with a normalized invalid-property-value
error.

```json
{
    "description": "A nullable field accepts an explicit null and yields a null value; a non-nullable field given null fails with a normalized invalid-property-value error reporting the null.",
    "cases": [
        {
            "input": {
                "op": "decode",
                "shape": "nullable-first",
                "document": "firstPerson: null"
            },
            "expected_output": "{\"firstPerson\":null}"
        }
    ]
}
```

#### Feature 3.4: Missing required property

Omitting a required (non-default) property fails with a normalized
missing-property error naming the property and the location.

```json
{
    "description": "Decoding an object that omits a required (non-default) property fails with a normalized missing-property error naming the property and the location.",
    "cases": [
        {
            "input": {
                "op": "decode",
                "shape": "complex",
                "document": "byte: 12\nshort: 1234\nint: 123456\nlong: 1234567\nfloat: 1.2\ndouble: 2.4\nenum: Value1\nboolean: true\nchar: A"
            },
            "expected_output": "error=[standard error categories for schema violations]\nproperty=string\nline=1\ncolumn=1\npath=<root>"
        }
    ]
}
```

#### Feature 3.5: Unknown property and strict mode

By default an unknown property fails with a normalized unknown-property error
listing the known property names sorted alphabetically; disabling strict mode
silently ignores unknown properties.

```json
{
    "description": "By default an unknown property fails with a normalized unknown-property error listing the known property names sorted alphabetically; disabling strict mode silently ignores unknown properties.",
    "cases": [
        {
            "input": {
                "op": "decode",
                "shape": "named",
                "document": "name: Blah Blahson\nextra-field: Hello"
            },
            "expected_output": "error=[standard error categories for schema violations]\nproperty=extra-field\nknown=name\nline=2\ncolumn=1\npath=extra-field"
        }
    ]
}
```

#### Feature 3.6: Invalid property value

When a property's value cannot be decoded as its declared type, decoding fails
with a normalized invalid-property-value error naming the property, the reason,
and the location.

```json
{
    "description": "When a property's value cannot be decoded as its declared type, decoding fails with a normalized invalid-property-value error naming the property, the reason, and the location.",
    "cases": [
        {
            "input": {
                "op": "decode",
                "shape": "complex",
                "document": "string: Alex\nbyte: xxx\nshort: 1234\nint: 123456\nlong: 1234567\nfloat: 1.2\ndouble: 2.4\nenum: Value1\nboolean: true\nchar: A"
            },
            "expected_output": "error=[standard error categories for schema violations]\nproperty=byte\nreason=Value 'xxx' is not a valid byte value.\nline=2\ncolumn=7"
        }
    ]
}
```

### Feature 4: Type-mismatch reporting

Decoding a document whose shape does not match the requested type (a sequence
where a scalar is expected, a mapping where a list is expected, etc.) fails with
a normalized incorrect-type error describing what was expected versus found.

```json
{
    "description": "Decoding a document whose shape does not match the requested type (a sequence where a scalar is expected, a mapping where a list is expected, etc.) fails with a normalized incorrect-type error describing what was expected versus what was found.",
    "cases": [
        {
            "input": {
                "op": "decode",
                "shape": "string",
                "document": "- thing"
            },
            "expected_output": "error=[standard error categories for schema violations]\ndetail=Expected a string, but got a list\nline=1\ncolumn=1"
        }
    ]
}
```

### Feature 5: Naming strategies (decode)

An optional naming strategy maps a field's program name to the key spelled in
the document (snake_case, kebab-case, PascalCase or camelCase); unknown keys are
reported using the strategy-mapped known names.

```json
{
    "description": "An optional naming strategy maps a field's program name to the key spelled in the document (snake_case, kebab-case, PascalCase or camelCase); unknown keys are reported using the strategy-mapped known names.",
    "cases": [
        {
            "input": {
                "op": "decode",
                "shape": "naming",
                "document": "serial_name: value",
                "config": {
                    "namingStrategy": "snake"
                }
            },
            "expected_output": "{\"serialName\":\"value\"}"
        }
    ]
}
```

### Feature 6: Anchors, aliases, and extensions

Anchors (`&name`) and aliases (`*name`) are forbidden by default and rejected
with a normalized error; when permitted they are resolved, and an optional
maximum alias count guards against alias-expansion attacks by failing once the
budget is exceeded. An extension-definition prefix marks anchor-defining keys at
the document root.

```json
{
    "description": "Anchors (&name) and aliases (*name) are forbidden by default and rejected with a normalized error; when permitted they are resolved, and an optional maximum alias count guards against alias-expansion attacks by failing once the budget is exceeded. An extension-definition prefix marks anchor-defining keys at the document root.",
    "cases": [
        {
            "input": {
                "op": "decode",
                "shape": "named",
                "document": ".some-extension: &name Jamie\n\nname: *name",
                "config": {
                    "extensionDefinitionPrefix": "."
                }
            },
            "expected_output": "error=[standard error categories for schema violations]\ndetail=Parsing anchors and aliases is disabled.\nline=1\ncolumn=18"
        }
    ]
}
```

### Feature 7: Polymorphism (decode)

#### Feature 7.1: Tag-based polymorphism

The concrete type of a value is selected from a YAML type tag (`!<typeName>`);
the matching subtype is decoded, an untagged value fails with a normalized
missing-type-tag signal, and an unrecognized tag fails with a normalized
unknown-type error listing known types.

```json
{
    "description": "With tag-based polymorphism, the concrete type of a value is selected from a YAML type tag (!<typeName>); the matching subtype is decoded, an untagged value fails with a normalized missing-type-tag signal, and an unrecognized tag fails with a normalized unknown-type error listing known types.",
    "cases": [
        {
            "input": {
                "op": "decode",
                "shape": "shape",
                "document": "!<sealedString>\nvalue: \"asdfg\"",
                "config": {
                    "polymorphismStyle": "tag"
                }
            },
            "expected_output": "{\"kind\":\"sealedString\",\"value\":\"asdfg\"}"
        }
    ]
}
```

#### Feature 7.2: Property-based polymorphism

The concrete type is selected from a discriminator property (default name
`type`, configurable); a missing discriminator fails with a normalized
missing-property error and an unknown value fails with a normalized unknown-type
error.

```json
{
    "description": "With property-based polymorphism, the concrete type is selected from a discriminator property (default name 'type', configurable); a missing discriminator fails with a normalized missing-property error and an unknown value fails with a normalized unknown-type error.",
    "cases": [
        {
            "input": {
                "op": "decode",
                "shape": "shape",
                "document": "type: sealedString\nvalue: \"asdfg\"",
                "config": {
                    "polymorphismStyle": "property"
                }
            },
            "expected_output": "{\"kind\":\"sealedString\",\"value\":\"asdfg\"}"
        }
    ]
}
```

#### Feature 7.3: Polymorphism disabled

When polymorphism is disabled, a document that still carries a type tag or a
discriminator-style mapping for a polymorphic target fails with a normalized
incorrect-type error.

```json
{
    "description": "When polymorphism is disabled, a document that still carries a type tag or a discriminator-style mapping for a polymorphic target fails with a normalized incorrect-type error.",
    "cases": [
        {
            "input": {
                "op": "decode",
                "shape": "shape",
                "document": "!<sealedString>\nvalue: \"asdfg\"",
                "config": {
                    "polymorphismStyle": "none"
                }
            },
            "expected_output": "error=[standard error categories for schema violations]\ndetail=Encountered a tagged polymorphic descriptor but PolymorphismStyle is 'None'\nline=1\ncolumn=1"
        }
    ]
}
```

### Feature 8: Scalar and string encoding

#### Feature 8.1: Encode primitives

Encode a primitive value to a YAML scalar. Numbers and booleans are emitted
plain; null is emitted as the plain token null.

```json
{
    "description": "Encode a primitive value to a YAML scalar document. Numbers and booleans are emitted plain; null is emitted as the plain token null.",
    "cases": [
        {
            "input": {
                "op": "encode",
                "shape": "int",
                "value": 12
            },
            "expected_output": "12"
        }
    ]
}
```

#### Feature 8.2: Encode string styles

Encode a string choosing the quoting style: double-quoted by default;
single-quoted and plain styles are selectable; the plain-except-ambiguous style
leaves unambiguous strings unquoted but quotes strings that could be misread as
another type.

```json
{
    "description": "Encode a string value choosing the quoting style: by default strings are double-quoted; single-quoted and plain styles are selectable; the plain-except-ambiguous style leaves unambiguous strings unquoted but quotes strings that could be misread as another type.",
    "cases": [
        {
            "input": {
                "op": "encode",
                "shape": "string",
                "value": "hello world"
            },
            "expected_output": "\"hello world\""
        }
    ]
}
```

### Feature 9: Collection encoding

Encode a list either as a block sequence (default) or as an inline flow
sequence; nested lists, maps and lists of objects follow the same chosen style.

```json
{
    "description": "Encode a list either as a block sequence (default) or as an inline flow sequence; nested lists, maps and lists of objects follow the same chosen style.",
    "cases": [
        {
            "input": {
                "op": "encode",
                "shape": "int-list",
                "value": [
                    1,
                    2,
                    3
                ]
            },
            "expected_output": "- 1\n- 2\n- 3"
        }
    ]
}
```

### Feature 10: Object encoding

#### Feature 10.1: Encode objects with indentation

Encode a structured object to a block mapping; nested objects are indented by
the configured indentation size, and embedded lists and maps are nested under
their key.

```json
{
    "description": "Encode a structured object to a block mapping; nested objects are indented by the configured indentation size, and embedded lists and maps are nested under their key.",
    "cases": [
        {
            "input": {
                "op": "encode",
                "shape": "named",
                "value": {
                    "name": "The name"
                }
            },
            "expected_output": "name: \"The name\""
        }
    ]
}
```

#### Feature 10.2: Encode defaults toggle

Encoding default-valued properties is on by default; turning it off omits any
property whose value equals its default, yielding an empty mapping when every
property is defaulted.

```json
{
    "description": "Encoding default-valued properties is on by default; turning it off omits any property whose value equals its default, yielding an empty mapping when every property is defaulted.",
    "cases": [
        {
            "input": {
                "op": "encode",
                "shape": "with-default",
                "value": {
                    "name": "default"
                },
                "config": {
                    "encodeDefaults": false
                }
            },
            "expected_output": "{}"
        }
    ]
}
```

#### Feature 10.3: Encode naming strategy

When encoding, a naming strategy rewrites each property's program name to the
chosen casing convention for the emitted keys.

```json
{
    "description": "When encoding, a naming strategy rewrites each property's program name to the chosen casing convention for the emitted keys.",
    "cases": [
        {
            "input": {
                "op": "encode",
                "shape": "naming",
                "value": {
                    "serialName": "value"
                },
                "config": {
                    "namingStrategy": "snake"
                }
            },
            "expected_output": "serial_name: \"value\""
        }
    ]
}
```

### Feature 11: Polymorphism encoding

Encode a polymorphic value, writing its concrete type either as a YAML tag or as
a discriminator property (default or custom name) according to the selected
style.

```json
{
    "description": "Encode a polymorphic value, writing its concrete type either as a YAML tag or as a discriminator property (default or custom name) according to the selected style.",
    "cases": [
        {
            "input": {
                "op": "encode",
                "shape": "shape",
                "value": {
                    "kind": "sealedInt",
                    "value": 5
                },
                "config": {
                    "polymorphismStyle": "tag"
                }
            },
            "expected_output": "!<sealedInt>\nvalue: 5"
        }
    ]
}
```

### Feature 12: Parse to node tree

Parse a document into a generic node tree without a target type, exposing the
structural shape (scalars, sequences, mappings, nulls and tagged nodes) and
scalar contents.

```json
{
    "description": "Parse a document into a generic node tree without a target type, exposing the structural shape (scalars, sequences, mappings, nulls and tagged nodes) and scalar contents.",
    "cases": [
        {
            "input": {
                "op": "parse",
                "document": "123"
            },
            "expected_output": "scalar '123'"
        }
    ]
}
```

### Feature 13: Null-document handling

Decoding the literal null document yields null for a nullable target and fails
with a normalized unexpected-null error for a non-nullable target, across
primitive, collection and object targets.

```json
{
    "description": "Decoding the literal null document yields null for a nullable target and fails with a normalized unexpected-null error for a non-nullable target, across primitive, collection and object targets.",
    "cases": [
        {
            "input": {
                "op": "decode",
                "shape": "string?",
                "document": "null"
            },
            "expected_output": "null"
        }
    ]
}
```

## Deliverables

- A YAML serialization engine implementing decode, encode, and parse operations
  over the command interface defined in **Architecture & Engineering
  Constraints**.
- Full coverage of the scalar grammar (integer bases/signs, floating-point and
  special tokens, boolean spellings, strings, characters, enumerations with
  external names and case-insensitive matching).
- Collection and structured-object decoding with optional/defaulted/nullable
  fields, order-independent keys, strict-mode unknown-property handling, and
  configurable naming strategies.
- Anchor/alias support gated behind an explicit permission with a maximum
  alias-count safeguard and a document-root extension-definition prefix.
- Polymorphic decode/encode via type tags and discriminator properties,
  including a disabled mode.
- An encoder with configurable string quoting, block/flow sequence style,
  indentation size, default-value emission toggle, and key naming strategy.
- A generic parse operation that materializes the structural node tree.
- A stable, language-neutral error contract emitting `error=<category>` blocks
  with structured fields and 1-based line/column locations for every failure
  mode listed above.
- A runnable test harness (`rcb_tests/test.sh`) that drives each JSON case
  through the engine and compares captured stdout against the expected output.


---
**Implementation notes:**
- handle hex/octal literal normalization
