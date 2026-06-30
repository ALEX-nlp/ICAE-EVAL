## Product Requirement Document

# In-Process Data Interchange & Tabular Compute Toolkit

## Project Goal

Build a self-contained library that provides the low-level building blocks
needed to move structured data across a process boundary and to evaluate
user-supplied transformations over that data in-process. The toolkit must
offer, behind a single line-oriented command interface:

- value and collection equality and conversion primitives,
- a binary wire protocol for primitive values and length-prefixed byte blocks,
- a typeless object serializer that preserves concrete type identity across a
  round trip,
- a schema description parser for atomic and nested data types,
- a microsecond-precision timestamp value type,
- positional and by-name access into typed tabular rows,
- composable user-defined functions (UDFs) that can be applied to a row and
  chained together,
- serialization of a transformation so that it can be reconstructed and
  re-executed elsewhere,
- value-comparable dependency-metadata records with file round-trip and
  sortable name generation.

Every capability is exercised through one stable contract: a single JSON
command object arrives on standard input, and a deterministic, line-oriented
text result is written to standard output.

## Background & Problem

Systems that distribute computation to remote workers need a small, dependable
core that does three things well: describe data, serialize it, and run
user-provided logic over it. These pieces are normally buried inside a larger
runtime and are difficult to test in isolation because they assume a live
backend connection.

The problem this toolkit solves is to expose those primitives directly and
deterministically, so each one can be driven in isolation with a fixed input
and verified against a fixed output. There is no network, no external service,
and no interactive state: each invocation reads exactly one command, performs
exactly one unit of work, and prints a stable result. This makes the behavior
fully reproducible and independently checkable.

A second concern is failure reporting. Because the same primitives may be hosted
in different language runtimes, error results must be reported as a small set of
neutral, stable categories rather than as runtime-specific exception identities
or messages.

## Architecture & Engineering Constraints

- **Single command interface.** The program reads one complete JSON object from
  standard input. The object always contains a string field `op` selecting the
  operation; the remaining fields are operation-specific arguments. The program
  writes only the result contract to standard output.
- **Line-oriented output contract.** Output is zero or more `key=value` lines in
  a fixed, documented order. Multi-line results are joined with a single `\n`
  and carry no trailing blank line. No decorative text, banners, or diagnostic
  logging may appear on standard output.
- **One unit of work per invocation.** The process is stateless across runs; all
  required input is provided in the single command object.
- **Neutral error contract.** Any rejected operation produces exactly one line
  of the form `error=<category>`. The category vocabulary is fixed and
  language-neutral:
  - `error=type_mismatch` — a typed read or reconstruction was requested for a
    target that is incompatible with the stored value.
  - `[the exact error category constant returned for numeric out of range failures]` — a numeric argument fell outside its permitted
    range.
  - `error=invalid_format` — a value could not be interpreted in the requested
    form.
  - `error=invalid_argument` — an argument was structurally unacceptable.
  - `error=invalid_operation` — the operation is not valid in the given state.
  - `error=serialization_rejected` — an object was not permitted to be
    reconstructed by the serializer.
  - `error=failure` — any other rejection.
  Error results never contain runtime exception class names, stack traces, or
  localized messages.
- **Deterministic rendering.** Booleans render as `true` / `false`. Whole numbers
  render without a decimal point or thousands separators. Collections render in
  input order; dictionaries render with keys in ascending order. These rules are
  fixed so output is byte-stable across runs and hosts.
- **No host leakage.** The contract exposes no host language, runtime, package,
  or file-layout details.

## Core Features

### Feature 1: Integer-array equality

Compare two integer sequences for element-by-element equality. Two sequences are
equal only when both are absent (null) or when they have identical length and
identical elements in order. A present sequence is never equal to an absent one,
and sequences of different length are never equal.

- **Input:** `{ "op":"array_equals", "left":<int[]|null>, "right":<int[]|null> }`
- **Output:** `equal=true` or `equal=false`

Examples:

```json
{
  "cases": [
    {
      "input": { "op": "array_equals", "left": [1, 2, 3], "right": [1, 2, 3] },
      "expected_output": "equal=true"
    },
    {
      "input": { "op": "array_equals", "left": null, "right": null },
      "expected_output": "equal=true"
    },
    {
      "input": { "op": "array_equals", "left": [1, 2, 3], "right": [1, 2, 4] },
      "expected_output": "equal=false"
    },
    {
      "input": { "op": "array_equals", "left": [1], "right": [1, 2] },
      "expected_output": "equal=false"
    },
    {
      "input": { "op": "array_equals", "left": [1], "right": null },
      "expected_output": "equal=false"
    }
  ]
}
```

### Feature 2: Value and collection conversion

Convert a dynamically-typed value into a requested target shape. Scalars convert
to the named numeric, boolean, or string target. Untyped ordered collections
convert into nested fixed-element arrays of the requested nesting depth, and
untyped keyed collections convert into nested dictionaries of the requested
depth. Converted collections render in a compact, canonical form: arrays in
input order, dictionaries with keys sorted ascending.

- **Input (scalar):** `{ "op":"convert_scalar", "target":"int|long|double|string|bool", "value":<scalar> }`
- **Input (array):** `{ "op":"convert_array", "depth":<n>, "values":<nested array> }`
- **Input (dictionary):** `{ "op":"convert_dictionary", "depth":<n>, "entries":<object> }`
- **Output:** `value=<scalar>`, `array=<canonical array>`, or `map=<canonical map>`

Examples:

```json
{
  "cases": [
    {
      "input": { "op": "convert_scalar", "target": "long", "value": 1 },
      "expected_output": "value=1"
    },
    {
      "input": { "op": "convert_scalar", "target": "string", "value": "test" },
      "expected_output": "value=test"
    },
    {
      "input": { "op": "convert_array", "depth": 1, "values": [0, 1, 2, 3] },
      "expected_output": "array=[0,1,2,3]"
    },
    {
      "input": { "op": "convert_array", "depth": 2, "values": [[0, 1], [2, 3]] },
      "expected_output": "array=[[0,1],[2,3]]"
    },
    {
      "input": { "op": "convert_dictionary", "depth": 1, "entries": { "1": 1, "2": 4, "3": 9 } },
      "expected_output": "map={1:1,2:4,3:9}"
    }
  ]
}
```

### Feature 3: Primitive wire serialization

Serialize a primitive value to a binary stream and read it back, proving the
wire encoding is lossless. The supported primitive types are boolean, 32-bit
integer, 64-bit integer, double, and string. A separate length-prefixed byte
read recognizes a reserved sentinel length that denotes an absent block
(reported as `[the specific sentinel value used to indicate a null read back length]`), and rejects a negative length as out of range.

- **Input (primitive):** `{ "op":"stream_primitives", "type":"bool|int|long|double|string", "value":<v> }`
- **Input (byte block):** `{ "op":"read_bytes", "length":<n> }`
- **Output (primitive):** `type=<t>` then `value=<readback>`
- **Output (byte block):** `length=<n|null>` or the neutral error contract

Examples:

```json
{
  "cases": [
    {
      "input": { "op": "stream_primitives", "type": "int", "value": 12345 },
      "expected_output": "type=int\nvalue=12345"
    },
    {
      "input": { "op": "stream_primitives", "type": "double", "value": 3.14 },
      "expected_output": "type=double\nvalue=3.14"
    },
    {
      "input": { "op": "stream_primitives", "type": "string", "value": "hello world!" },
      "expected_output": "type=string\nvalue=hello world!"
    },
    {
      "input": { "op": "read_bytes", "length": -5 },
      "expected_output": "[the specific sentinel value used to indicate a null read back length]"
    },
    {
      "input": { "op": "read_bytes", "length": -1 },
      "expected_output": "[the exact error category constant returned for numeric out of range failures]"
    }
  ]
}
```

### Feature 4: Typeless object round-trip

Serialize an object graph in a typeless format that embeds concrete type
identity, then reconstruct it. A simple record round-trips its field values. A
derived instance referenced through its base type restores to its derived type
and exposes the derived-only field. Requesting reconstruction as an unrelated
type is rejected as a type mismatch, and an object whose type is not permitted
to be reconstructed is rejected as a serialization rejection.

- **Input (round-trip):** `{ "op":"object_roundtrip", "id":<int>, "name":<string> }`
- **Input (polymorphic):** `{ "op":"object_polymorphic", "id":<int>, "name":<string>, "role":<string> }`
- **Input (mismatch):** `{ "op":"object_type_mismatch", "id":<int>, "name":<string> }`
- **Input (disallowed):** `{ "op":"object_disallowed", "value":<int> }`
- **Output:** field lines on success, or the neutral error contract

Examples:

```json
{
  "cases": [
    {
      "input": { "op": "object_roundtrip", "id": 101, "name": "John Doe" },
      "expected_output": "id=101\nname=John Doe"
    },
    {
      "input": { "op": "object_polymorphic", "id": 1, "name": "Alice", "role": "Account manager" },
      "expected_output": "concrete=derived\nname=Alice\nrole=Account manager"
    },
    {
      "input": { "op": "object_type_mismatch", "id": 101, "name": "John Doe" },
      "expected_output": "error=type_mismatch"
    },
    {
      "input": { "op": "object_disallowed", "value": 123 },
      "expected_output": "error=serialization_rejected"
    }
  ]
}
```

### Feature 5: Data-type schema parsing

Parse a JSON schema description into a data-type model and report its observable
shape. Atomic types report a type name and a compact signature. An array type
additionally reports its element type and whether it allows absent elements. A
map type reports key type, value type, and whether values may be absent. A
struct type reports its field count followed by each field's name, type, and
nullability, in declared order.

- **Input:** `{ "op":"parse_type", "schema":<schema-json-string> }`
- **Output:** `type_name=...`, `simple_string=...`, plus type-specific child lines

Examples:

```json
{
  "cases": [
    {
      "input": { "op": "parse_type", "schema": "\"integer\"" },
      "expected_output": "type_name=integer\nsimple_string=integer"
    },
    {
      "input": { "op": "parse_type", "schema": "{\"type\":\"array\",\"elementType\":\"integer\",\"containsNull\":false}" },
      "expected_output": "type_name=array\nsimple_string=array<integer>\nelement_type=integer\ncontains_null=false"
    },
    {
      "input": { "op": "parse_type", "schema": "{\"type\":\"map\",\"keyType\":\"integer\",\"valueType\":\"double\",\"valueContainsNull\":false}" },
      "expected_output": "type_name=map\nsimple_string=map<integer,double>\nkey_type=integer\nvalue_type=double\nvalue_contains_null=false"
    },
    {
      "input": { "op": "parse_type", "schema": "{\"type\":\"struct\",\"fields\":[{\"name\":\"age\",\"type\":\"long\",\"nullable\":true,\"metadata\":{}},{\"name\":\"name\",\"type\":\"string\",\"nullable\":false,\"metadata\":{}}]}" },
      "expected_output": "type_name=struct\nsimple_string=struct<age:long,name:string>\nfield_count=2\nfield_name=age\nfield_type=long\nfield_nullable=true\nfield_name=name\nfield_type=string\nfield_nullable=false"
    }
  ]
}
```

### Feature 6: Microsecond timestamp value

Construct a timestamp from explicit calendar and time-of-day components with
microsecond precision and report each component back, plus a canonical UTC
string of the form `YYYY-MM-DD HH:MM:SS.ffffffZ`. The microsecond component is
range-checked: a value of one million or more is rejected as out of range.

- **Input:** `{ "op":"timestamp", "year":..., "month":..., "day":..., "hour":..., "minute":..., "second":..., "microsecond":... }`
- **Output:** component lines and `iso=<canonical string>`, or the neutral error contract

Examples:

```json
{
  "cases": [
    {
      "input": { "op": "timestamp", "year": 2020, "month": 1, "day": 2, "hour": 15, "minute": 30, "second": 30, "microsecond": 123456 },
      "expected_output": "year=2020\nmonth=1\nday=2\nhour=15\nminute=30\nsecond=30\nmicrosecond=123456\niso=2020-01-02 15:30:30.123456Z"
    },
    {
      "input": { "op": "timestamp", "year": 2020, "month": 1, "day": 1, "hour": 8, "minute": 30, "second": 30, "microsecond": 123 },
      "expected_output": "year=2020\nmonth=1\nday=1\nhour=8\nminute=30\nsecond=30\nmicrosecond=123\niso=2020-01-01 08:30:30.000123Z"
    },
    {
      "input": { "op": "timestamp", "year": 2020, "month": 1, "day": 2, "hour": 15, "minute": 30, "second": 30, "microsecond": 1234567 },
      "expected_output": "[the exact error category constant returned for numeric out of range failures]"
    }
  ]
}
```

### Feature 7: Typed row access

Build a tabular row from a named, typed schema and a set of values, then read
its cells positionally and by column name. The row reports its size. A typed
read that matches the column's declared type returns the value; a typed read
whose target is incompatible with the column is rejected. Reading an integer
column as a string is rejected as a type mismatch, while reading a string column
as an integer is rejected as an invalid format.

- **Input:** `{ "op":"row", "columns":[{"name":...,"type":"int|string"},...], "values":[...], "access":[{"by":"index|name", ...,"as":"int|string"},...] }`
- **Output:** `size=<n>` then one `get=<value>` per successful access, or the neutral error contract

Examples:

```json
{
  "cases": [
    {
      "input": {
        "op": "row",
        "columns": [{ "name": "col1", "type": "int" }, { "name": "col2", "type": "string" }],
        "values": [1, "abc"],
        "access": [
          { "by": "index", "index": 0, "as": "int" },
          { "by": "name", "name": "col2", "as": "string" }
        ]
      },
      "expected_output": "size=2\nget=1\nget=abc"
    },
    {
      "input": {
        "op": "row",
        "columns": [{ "name": "col1", "type": "int" }, { "name": "col2", "type": "string" }],
        "values": [1, "abc"],
        "access": [{ "by": "index", "index": 0, "as": "string" }]
      },
      "expected_output": "error=type_mismatch"
    },
    {
      "input": {
        "op": "row",
        "columns": [{ "name": "col1", "type": "int" }, { "name": "col2", "type": "string" }],
        "values": [1, "abc"],
        "access": [{ "by": "index", "index": 1, "as": "int" }]
      },
      "expected_output": "error=invalid_format"
    }
  ]
}
```

### Feature 8: User-defined function application and chaining

Apply a user-defined function to selected arguments of an input row and compose
functions into a pipeline. A concatenating function of fixed arity selects its
arguments from a wider input row using an offset list, so leading columns may be
ignored. Functions can be chained so the output of one feeds the next; a valid
two-stage chain reports both intermediate results, while a chain whose argument
shapes do not line up is rejected.

- **Input (apply):** `{ "op":"udf_apply", "arity":<n>, "inputs":[...], "offsets":[...] }`
- **Input (chain):** `{ "op":"udf_chain", "inputs":[...], "offsets":[...], "order":"valid|invalid" }`
- **Output:** `result=<value>`, or `level1=...` / `level2=...` for a valid chain, or the neutral error contract

Examples:

```json
{
  "cases": [
    {
      "input": { "op": "udf_apply", "arity": 1, "inputs": ["arg1"], "offsets": [0] },
      "expected_output": "result=arg1"
    },
    {
      "input": { "op": "udf_apply", "arity": 3, "inputs": ["arg0", "arg1", "arg2", "arg3"], "offsets": [0, 1, 2] },
      "expected_output": "result=arg0arg1arg2"
    },
    {
      "input": { "op": "udf_chain", "inputs": [100, "name"], "offsets": [0, 1], "order": "valid" },
      "expected_output": "level1=outer1:name:100\nlevel2=outer2:outer1:name:100"
    },
    {
      "input": { "op": "udf_chain", "inputs": [100, "name"], "offsets": [0, 1], "order": "invalid" },
      "expected_output": "error=type_mismatch"
    }
  ]
}
```

### Feature 9: Transformation serialization round-trip

Serialize a user-defined transformation together with its serialization modes to
bytes, reconstruct it, and re-execute it to prove behavior survives the round
trip. The reconstructed transformation reports its serializer mode, deserializer
mode, and run mode, and produces the same result it would have produced before
serialization.

- **Input:** `{ "op":"command_roundtrip", "arg":<string> }`
- **Output:** `serializer_mode=...`, `deserializer_mode=...`, `run_mode=...`, `result=...`

Examples:

```json
{
  "cases": [
    {
      "input": { "op": "command_roundtrip", "arg": "spark" },
      "expected_output": "serializer_mode=Row\ndeserializer_mode=Row\nrun_mode=N\nresult=hello spark"
    }
  ]
}
```

### Feature 10: Dependency-metadata records

Model a dependency-metadata record describing assembly probe paths, native probe
paths, and package coordinates. Records support value equality (a present record
is never equal to an absent one, and any differing path or coordinate makes them
unequal), a file round-trip (serialize to a file, reload, and compare for
equality), and generation of fixed-width, zero-padded, sortable file names from
numbers.

- **Input (equals):** `{ "op":"metadata_equals", "left":<metadata>, "right":<metadata|null> }`
- **Input (round-trip):** `{ "op":"metadata_roundtrip", "metadata":<metadata> }`
- **Input (file name):** `{ "op":"metadata_filename", "numbers":[...] }`
- **Output:** `equal=true|false`, or one `filename=<name>` line per number in input order

Examples:

```json
{
  "cases": [
    {
      "input": {
        "op": "metadata_equals",
        "left": { "assembly_paths": ["/assembly/probe/path"], "native_paths": ["/native/probe/path"], "nugets": [{ "file_name": "package.name.1.0.0.nupkg", "package_name": "package.name", "package_version": "1.0.0" }] },
        "right": { "assembly_paths": ["/assembly/probe/path"], "native_paths": ["/native/probe/path"], "nugets": [{ "file_name": "package.name.1.0.0.nupkg", "package_name": "package.name", "package_version": "1.0.0" }] }
      },
      "expected_output": "equal=true"
    },
    {
      "input": {
        "op": "metadata_equals",
        "left": { "assembly_paths": ["/assembly/probe/path"], "native_paths": ["/native/probe/path"], "nugets": [{ "file_name": "package.name.1.0.0.nupkg", "package_name": "package.name", "package_version": "1.0.0" }] },
        "right": null
      },
      "expected_output": "equal=false"
    },
    {
      "input": {
        "op": "metadata_roundtrip",
        "metadata": { "assembly_paths": ["/assembly/probe/path"], "native_paths": ["/native/probe/path"], "nugets": [{ "file_name": "package.name.1.0.0.nupkg", "package_name": "package.name", "package_version": "1.0.0" }] }
      },
      "expected_output": "equal=true"
    },
    {
      "input": { "op": "metadata_filename", "numbers": [1, 10, 100] },
      "expected_output": "filename=dependencyProviderMetadata_0000000000000000001\nfilename=dependencyProviderMetadata_0000000000000000010\nfilename=dependencyProviderMetadata_0000000000000000100"
    }
  ]
}
```

## Deliverables

- A library implementing all ten features behind the single JSON-on-stdin,
  lines-on-stdout command interface described above.
- An execution adapter that reads one command object, performs the selected
  operation, and renders the line-oriented result, including the neutral error
  contract for every rejected operation.
- A test harness (`rcb_tests/test.sh`) that, for a chosen case directory, feeds
  each case's `input` to the adapter and captures only the raw program standard
  output, then compares it to each case's `expected_output` and prints a
  pass/fail summary.
- A hidden evaluation set (`rcb_tests/test_cases/`) and a public mirror
  (`rcb_tests/public_test_cases/`) whose cases match the examples embedded in
  this document.


---
**Implementation notes:**
- follow the same parenthetical expansion pattern used for scalar types in the parse_type output
- apply the same nesting depth logic seen in C049 but include an outer level with two title parameters
