## Product Requirement Document

# In-Memory Document Store Engine — JSON Document Matching, Modification, and Ordering

## Project Goal

Build the core engine of an in-memory document store that operates on schemaless JSON-like documents, so developers can match documents against rich query specifications, apply declarative update modifiers, and order heterogeneous values exactly the way a real document database would — entirely in memory, without standing up an external database server.

---

## Background & Problem

Applications that talk to a document database need their data-access logic exercised somewhere fast and deterministic. Spinning up a real database server for every test is slow, stateful, and awkward to isolate. The alternative — hand-mocking each query — quickly drifts from the database's real semantics (how comparisons treat arrays, how `null` versus "missing" differ, how update modifiers mutate nested arrays, how values of different kinds sort relative to each other).

This project provides the behavioral heart of such a store as a pure, in-memory engine over JSON-like documents. A document is an ordered map of string keys to values; values may be scalars (numbers — integer/long/double, strings, booleans), `null`, dates, object identifiers, regular expressions, the special smallest-key and largest-key sentinels, nested documents, or arrays of any of these. The engine offers three capabilities: a **matcher** that decides which documents satisfy a query specification, an **update engine** that applies a modifier specification to a document and returns the new document, and an **ordering** facility that sorts a list of values by a sort specification. All three follow the well-known semantics of document-database query and update languages and use a JSON wire format that carries typed values via reserved keys (an object identifier as `{"$oid": "<hex>"}`, a date as `{"$date": <ms-since-epoch>}` and rendered back as an ISO-8601 instant, a long via `{"$numberLong": "<n>"}`, a regular expression as `{"$regex": "<pat>", "$options": "<flags>"}`, and the sentinels as `{"$minKey": 1}` / `{"$maxKey": 1}`).

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository. This domain (query matching, update modifiers, value ordering, typed-value (de)serialization) is non-trivial; prefer a multi-module layout that separates the matcher, the update engine, the ordering comparator, and the JSON adapter.
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

### Feature 1: Document Matching

**As a developer**, I want to evaluate a query specification against a stream of documents and keep only the ones that satisfy it, so I can implement find/filter behavior with the same semantics a document database uses.

**Expected Behavior / Usage:**

A `find` request carries a `query` object and a `documents` array. The engine returns, on its own line, the matching documents in their original input order (each rendered as a JSON document in the wire format). A query maps fields to conditions; an operator-free value is an equality condition, while an object of `$`-prefixed keys expresses operators. Across all operators, when the stored field holds an array, a scalar condition matches if **any** element satisfies it; an absent field never satisfies a positive condition. The sub-features below each cover one independent family of conditions.

*1.1 Comparison conditions — range, equality, inequality, and temporal comparisons on a single field.*

Supports `$gt`, `$gte`, `$lt`, `$lte` (strict/inclusive bounds, combinable to form a range), `$eq` (equality), and `$ne` (inequality, which also keeps documents where the field is absent). Comparisons work across numeric kinds and over ordered typed values such as dates.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_comparison.json`

```json
{
    "description": "A document matcher evaluates a query specification against a stream of documents and returns, in their original order, only the documents that satisfy it. This scenario covers range and equality comparison conditions on a single field: a value strictly or inclusively greater-than or less-than a bound, an explicit equality condition, an inequality (not-equal) condition, ranges combining two bounds, and comparisons against temporal values. When the stored field holds an array, the condition matches if any element satisfies it. A field that is absent or holds the empty/null value does not satisfy a positive comparison.",
    "cases": [
        {"input": {"op": "find", "query": {"a": {"$gte": 4}}, "documents": [{"a": null}, {"n": "neil", "a": 1}, {"n": "fred", "a": 2}, {"n": "ted", "a": 3}, {"n": "stu", "a": 4}, {"n": "tim", "a": 5}, {"a": [3, 4]}]}, "expected_output": "{ \"n\" : \"stu\" , \"a\" : 4}\n{ \"n\" : \"tim\" , \"a\" : 5}\n{ \"a\" : [ 3 , 4]}\n"},
        {"input": {"op": "find", "query": {"a": {"$ne": 3}}, "documents": [{"a": [1, 3]}, {"a": 1}, {"a": 3}, {"b": 3}, {"a": [1, 2]}]}, "expected_output": "{ \"a\" : 1}\n{ \"b\" : 3}\n{ \"a\" : [ 1 , 2]}\n"}
    ]
}
```

*1.2 Set-membership conditions — relate a field to a collection of values.*

Supports `$in` (field equals one of the listed values, or for an array field has any element among them; a `null` entry also matches absent fields), `$nin` (the complement, also keeping documents with the field absent), and `$all` (array field contains every listed value, where list entries may themselves be patterns).

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_membership.json`

```json
{
    "description": "A document matcher selects documents whose field relates to a given set of values. The set-membership condition keeps documents whose field equals one of the listed values (or, for an array field, has any element among them); a null entry in the listed values additionally matches documents where the field is absent. The not-in condition is the complement: it keeps documents whose field matches none of the listed values, including documents where the field is absent. The contains-all condition keeps documents whose array field contains every listed value (list entries may themselves be patterns). Matching returns documents in their original order.",
    "cases": [
        {"input": {"op": "find", "query": {"a": {"$in": [2, 3]}}, "documents": [{"a": [1, 3]}, {"a": 1}, {"a": 3}]}, "expected_output": "{ \"a\" : [ 1 , 3]}\n{ \"a\" : 3}\n"},
        {"input": {"op": "find", "query": {"a": {"$all": [2, 3]}}, "documents": [{"a": [2, 3]}, {"a": null}, {"a": [1, 3, 4]}, {"a": [1, 2, 3]}, {"a": [1, 3, 4]}]}, "expected_output": "{ \"a\" : [ 2 , 3]}\n{ \"a\" : [ 1 , 2 , 3]}\n"}
    ]
}
```

*1.3 Element conditions — match on structural properties rather than value.*

Supports `$exists` (field present, even when its value is `null`), `$size` (array field has exactly the given length), and `$mod` (numeric field has a given remainder for a given divisor).

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_element.json`

```json
{
    "description": "A document matcher selects documents based on structural properties of a field rather than its concrete value. The existence condition keeps documents in which the field is present (even when its value is null). The array-size condition keeps documents whose array field has exactly the given number of elements. The modulo condition keeps documents whose numeric field, divided by a given divisor, leaves a given remainder. Documents are returned in their original order; an absent field does not satisfy these positive conditions.",
    "cases": [
        {"input": {"op": "find", "query": {"a": {"$exists": true}}, "documents": [{"a": null}, {"b": null}, {"a": "hi"}, {"b": "hi"}]}, "expected_output": "{ \"a\" :  null }\n{ \"a\" : \"hi\"}\n"},
        {"input": {"op": "find", "query": {"a": {"$size": 3}}, "documents": [{"a": null}, {"a": [1, 2, 3]}, {"a": [1, 2, 3, 4]}]}, "expected_output": "{ \"a\" : [ 1 , 2 , 3]}\n"}
    ]
}
```

*1.4 Logical connectives — combine conditions.*

Supports implicit conjunction (several field conditions in one query object), explicit `$and`, `$or` (satisfied when at least one sub-query holds; nestable), and `$not` (inverts an inner condition).

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_logical.json`

```json
{
    "description": "A document matcher combines conditions with logical connectives. A query object listing several field conditions is an implicit conjunction: every condition must hold. An explicit conjunction connective requires all of its sub-queries to hold. A disjunction connective keeps a document when at least one of its sub-queries holds, and disjunctions may be nested. A negation connective inverts a condition, keeping the documents the inner condition would reject. Matching preserves the original document order.",
    "cases": [
        {"input": {"op": "find", "query": {"$and": [{"a": 3}, {"b": 4}]}, "documents": [{"a": 3, "b": 4}, {"a": 3, "b": 5}, {"b": 4}, {"a": 3}, {"a": 5, "b": 4}]}, "expected_output": "{ \"a\" : 3 , \"b\" : 4}\n"},
        {"input": {"op": "find", "query": {"$or": [{"a": 3}, {"b": {"$ne": 3}}]}, "documents": [{"a": 3, "b": 1}, {"a": 1, "b": 3}, {"a": 1, "b": 1}, {"a": 3}, {"b": 1}, {"a": 5}, {"b": 3}]}, "expected_output": "{ \"a\" : 3 , \"b\" : 1}\n{ \"a\" : 1 , \"b\" : 1}\n{ \"a\" : 3}\n{ \"b\" : 1}\n{ \"a\" : 5}\n"}
    ]
}
```

*1.5 Dotted-path resolution — reach into nested documents and arrays.*

A field key may be a dotted path whose components are sub-document keys or numeric array indexes. Traversing an array of sub-documents without an explicit index matches if any element along the way satisfies the condition; comparison operators apply through paths too.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_dotted_path.json`

```json
{
    "description": "A document matcher resolves dotted field paths to reach into nested documents and arrays. A path component may be a sub-document key or a numeric array index. When a path traverses an array of sub-documents without an explicit index, the condition matches if any element along the way satisfies it. Comparison conditions also apply through dotted paths. Documents are returned in their original order; a path that cannot be resolved does not match.",
    "cases": [
        {"input": {"op": "find", "query": {"a.b": 1}, "documents": [{"a": 1}, {"b": 1}, {"a": {"b": 1}}]}, "expected_output": "{ \"a\" : { \"b\" : 1}}\n"},
        {"input": {"op": "find", "query": {"a.b": {"$gt": 2}}, "documents": [{"a": [{"b": 1}, {"b": 2}]}, {"a": [{"b": 2}, {"b": 3}]}]}, "expected_output": "{ \"a\" : [ { \"b\" : 2} , { \"b\" : 3}]}\n"}
    ]
}
```

*1.6 Regular-expression conditions — pattern matching on strings.*

A field condition given as a pattern (directly, or as a pattern together with option flags such as dot-matches-newline) keeps documents whose string value matches; for an array of strings it matches if any element matches; it also applies through dotted paths. Non-string and absent values never match.

**Test Cases:** `rcb_tests/public_test_cases/feature1_6_regex.json`

```json
{
    "description": "A document matcher supports regular-expression conditions on string fields. A field condition given as a pattern keeps documents whose string value matches the pattern (anchored as the pattern dictates); when the field is an array of strings, it matches if any element matches. The pattern may be supplied directly or together with option flags (for example, enabling dot-to-match-newline behavior). Regex conditions also apply through dotted paths into nested documents. Non-string and absent values do not match. Documents are returned in their original order.",
    "cases": [
        {"input": {"op": "find", "query": {"a": {"$regex": "^foo"}}, "documents": [{"a": 1}, {"a": null}, {"a": "fooSter"}, {"a": "funky foo"}, {"a": ["foomania", "notfoo"]}]}, "expected_output": "{ \"a\" : \"fooSter\"}\n{ \"a\" : [ \"foomania\" , \"notfoo\"]}\n"},
        {"input": {"op": "find", "query": {"a": {"$regex": "foo.*Ster", "$options": "s"}}, "documents": [{"a": "foo\nSter"}]}, "expected_output": "{ \"a\" : \"foo\\nSter\"}\n"}
    ]
}
```

*1.7 Implicit equality — a plain value as an equality condition.*

For a scalar, direct value equality. For an array value, the field must be an equal array element-by-element, or a non-array field must equal one of the array's elements. For an embedded-document value, the field must equal that document. Equality respects value identity for typed values such as object identifiers.

**Test Cases:** `rcb_tests/public_test_cases/feature1_7_implicit_equality.json`

```json
{
    "description": "A document matcher treats a plain (non-operator) value as an equality condition. For a scalar this is direct value equality. For an array value, a document matches when its field is an array equal element-by-element to the query array, or when a non-array field equals one of the array's elements. For an embedded-document value, the stored field must equal that document. Equality respects value identity for typed values such as object identifiers. Documents are returned in their original order.",
    "cases": [
        {"input": {"op": "find", "query": {"a": [1, 2, 3]}, "documents": [{"a": []}, {"b": []}, {"a": [1, 2, 3]}, {"a": [1, 2, 3]}, {"a": []}]}, "expected_output": "{ \"a\" : [ 1 , 2 , 3]}\n{ \"a\" : [ 1 , 2 , 3]}\n"},
        {"input": {"op": "find", "query": {"a": {"b": {"$oid": "4f39d78d4b90b2f2f1530841"}}}, "documents": [{"a": null}, {"a": {"b": {"$oid": "4f39d78d4b90b2f2f1530841"}}}]}, "expected_output": "{ \"a\" : { \"b\" : { \"$oid\" : \"4f39d78d4b90b2f2f1530841\"}}}\n"}
    ]
}
```

---

### Feature 2: Document Update Modifiers

**As a developer**, I want to apply a declarative modifier specification to a document and get the resulting document back, so I can implement in-place document updates with database-accurate semantics.

**Expected Behavior / Usage:**

An `update` request carries a `document`, an `update` specification, and optionally a `query` (needed only by the positional placeholder). The engine returns the resulting document as a single JSON line. An update specification is either a set of `$`-prefixed modifier operators or, when it contains none, a whole-document replacement. The sub-features below cover the independent modifier families.

*2.1 Field modifiers — set, unset, rename, increment, and whole-document replacement.*

A modifier-free specification replaces the whole document (the identifier is preserved). `$set` assigns at a (possibly nested, dotted) path, creating intermediate documents; `$unset` removes a field; `$rename` moves values between paths; `$inc` adds a numeric delta (absent field treated as zero, numeric kind preserved). Numeric path components address array positions or create numbered sub-keys.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_field_modifiers.json`

```json
{
    "description": "An update engine applies a modifier specification to a document and returns the resulting document. A specification with no modifier operators replaces the whole document (the identifier is preserved). The set operator assigns a value at a (possibly nested, dotted) path, creating intermediate documents as needed. The unset operator removes a field at a path. The rename operator moves values from one path to another. The increment operator adds a numeric delta to a field, treating an absent field as zero and preserving the field's numeric kind. Numeric path components address array positions or create numbered sub-keys.",
    "cases": [
        {"input": {"op": "update", "document": {"_id": 1, "a": 1, "b": 1}, "update": {"$set": {"a": 5}}}, "expected_output": "{ \"_id\" : 1 , \"a\" : 5 , \"b\" : 1}\n"},
        {"input": {"op": "update", "document": {"a": 1}, "update": {"$inc": {"a": 5}}}, "expected_output": "{ \"a\" : 6}\n"}
    ]
}
```

*2.2 Array append — push, push-all, add-to-set, with each/slice/position/sort modifiers.*

`$push` appends one element (creating the array when absent); with `$each` it appends several, `$slice` trims to a maximum length (first N for non-negative N, last N for negative, empty for zero), `$position` inserts at an index, and `$sort` reorders (by a sub-field ascending/descending, or whole elements). `$pushAll` appends a list. `$addToSet` appends only values not already present (optionally each of several). Modifiers compose with each other and with other operators in one specification.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_array_append.json`

```json
{
    "description": "An update engine appends to array fields. The push operator adds one element to the end of an array, creating the array when absent. With an each-modifier it appends several elements at once; a slice-modifier then trims the array to a maximum length (keeping the first N for a non-negative N, the last N for a negative N, or empty for zero); a position-modifier inserts the new elements at a given index instead of the end; a sort-modifier reorders the array (by a sub-field ascending/descending, or the whole elements). The push-all operator appends a list of elements. The add-to-set operator appends only values not already present (optionally each of several). Push and increment may be combined in one specification.",
    "cases": [
        {"input": {"op": "update", "document": {"a": [1]}, "update": {"$push": {"a": 2}}}, "expected_output": "{ \"a\" : [ 1 , 2]}\n"},
        {"input": {"op": "update", "document": {"a": [1]}, "update": {"$push": {"a": {"$each": [2, 3]}}}}, "expected_output": "{ \"a\" : [ 1 , 2 , 3]}\n"}
    ]
}
```

*2.3 Array removal — pop, pull, pull-all.*

`$pop` drops one element from the end (positive argument) or front (negative argument), leaving a missing/empty array unchanged. `$pull` removes every element matching a condition (a scalar removes equal elements; a sub-condition removes matching embedded documents or set/pattern members). `$pullAll` removes every occurrence of any value in a list.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_array_remove.json`

```json
{
    "description": "An update engine removes elements from array fields. The pop operator drops one element from the array's end (for a positive argument) or its front (for a negative argument), leaving a missing or empty array unchanged. The pull operator removes every element matching a condition: a scalar removes equal elements, and a sub-condition removes matching embedded documents or elements matching a set membership (including pattern membership). The pull-all operator removes every occurrence of any value in a given list.",
    "cases": [
        {"input": {"op": "update", "document": {"a": [1, 2]}, "update": {"$pop": {"a": 1}}}, "expected_output": "{ \"a\" : [ 1]}\n"},
        {"input": {"op": "update", "document": {"a": [1, 2, 1, 3, 1]}, "update": {"$pull": {"a": 1}}}, "expected_output": "{ \"a\" : [ 2 , 3]}\n"}
    ]
}
```

*2.4 Bitwise modifier — bitwise AND/OR on an integer field.*

`$bit` performs a bitwise AND with a mask, a bitwise OR with a mask, or both in sequence (AND then OR), replacing the field with the integer result.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_bitwise.json`

```json
{
    "description": "An update engine applies bitwise modifiers to an integer field. The bit operator can perform a bitwise AND with a given mask, a bitwise OR with a given mask, or both in sequence (AND then OR), replacing the field with the computed integer result.",
    "cases": [
        {"input": {"op": "update", "document": {"a": 11}, "update": {"$bit": {"a": {"and": 5}}}}, "expected_output": "{ \"a\" : 1}\n"},
        {"input": {"op": "update", "document": {"a": 11}, "update": {"$bit": {"a": {"or": 5}}}}, "expected_output": "{ \"a\" : 15}\n"}
    ]
}
```

*2.5 Positional placeholder — target the first array element matched by the query.*

The positional placeholder `$` in an update path resolves to the first array element matched by the accompanying `query` (including via an element-match condition). It may stand for a field inside the matched element, the matched scalar element itself, or replacing the whole matched element; other elements are untouched.

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_positional.json`

```json
{
    "description": "An update engine supports the positional placeholder, which targets the first array element matched by the accompanying query. The placeholder may stand for a field inside the matched element, for the matched scalar element itself, or for replacing the whole matched element. The query that located the document (including via an element-match condition) determines which array position the placeholder resolves to; other elements are left untouched.",
    "cases": [
        {"input": {"op": "update", "document": {"b": [{"c": 1, "n": "jon"}]}, "update": {"$inc": {"b.$.c": 1}}, "query": {"b.n": "jon"}}, "expected_output": "{ \"b\" : [ { \"c\" : 2 , \"n\" : \"jon\"}]}\n"},
        {"input": {"op": "update", "document": {"b": [1, 2, 3]}, "update": {"$inc": {"b.$": 1}}, "query": {"b": 2}}, "expected_output": "{ \"b\" : [ 1 , 3 , 3]}\n"}
    ]
}
```

*2.6 Invalid specifications — normalized error reporting.*

When an update is invalid the engine emits a normalized error line `error=<category>` instead of a result document. Two conflicting modifier operators on the same field yield `error=conflicting_modifiers`; a positional placeholder against a path that cannot be resolved to an array element of the required shape yields `error=invalid_positional_path`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_6_errors.json`

```json
{
    "description": "An update engine rejects invalid modifier specifications with a normalized error signal instead of a result document. Supplying two conflicting modifier operators that target the same field is reported as a conflicting-modifiers error. Using the positional placeholder against a path that cannot be resolved to an array element of the required shape is reported as an invalid-positional-path error.",
    "cases": [
        {"input": {"op": "update", "document": {}, "update": {"$set": {"a": 5}, "$inc": {"a": 3}}}, "expected_output": "error=conflicting_modifiers\n"},
        {"input": {"op": "update", "document": {"b": [1, 2, 3]}, "update": {"$inc": {"b.$.c": 1}}, "query": {"b": 2}}, "expected_output": "error=invalid_positional_path\n"}
    ]
}
```

---

### Feature 3: Heterogeneous Value Ordering

**As a developer**, I want to sort a list of mixed-kind values by a sort specification, so I can order query results the way a document database does, including the cross-type ordering rules.

**Expected Behavior / Usage:**

A `sort` request carries a `values` array and a `sort` specification (a field with direction `1` ascending or `-1` descending). The engine returns the sorted list as a single JSON array line. Values of different kinds follow a fixed inter-type ranking: smallest-key sentinel, `null`, numbers (integers, longs and doubles compared by numeric value), strings, embedded documents, arrays, object identifiers, booleans (false before true), dates, regular expressions, then largest-key sentinel. Embedded documents that contain the sort field are ordered by that field's value and placed after the other kinds; reversing the direction reverses the whole resulting order.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_type_ordering.json`

```json
{
    "description": "An ordering engine sorts a heterogeneous list of values according to a sort specification (a field with an ascending or descending direction). Values of different BSON kinds are ordered by a fixed inter-type ranking (for example smallest-key, null, numbers, strings, embedded documents, arrays, object identifiers, booleans, dates, regular expressions, largest-key), with numeric values compared across integer/long/double kinds. Embedded documents that contain the sort field are ordered by that field's value. Reversing the direction reverses the resulting order.",
    "cases": [
        {"input": {"op": "sort", "values": [{"a": 0}, {"a": 2}, {"b": 0}, {"a": 1, "b": 2}, 0.5, 0, null, {"$minKey": 1}, {"$maxKey": 1}, {"$numberLong": "1"}, false, true, {"$date": 1000}, {"$regex": "\\s*"}, {"$oid": "4f39d78d4b90b2f2f1530841"}, [], ""], "sort": {"a": 1}}, "expected_output": "[ { \"$minKey\" : 1} ,  null  , 0 , 0.5 , 1 , \"\" , { \"b\" : 0} , [ ] , { \"$oid\" : \"4f39d78d4b90b2f2f1530841\"} , false , true , { \"$date\" : \"1970-01-01T00:00:01.000Z\"} , { \"$regex\" : \"\\\\s*\"} , { \"$maxKey\" : 1} , { \"a\" : 0} , { \"a\" : 1 , \"b\" : 2} , { \"a\" : 2}]\n"},
        {"input": {"op": "sort", "values": [{"a": 0}, {"a": 2}, {"b": 0}, {"a": 1, "b": 2}, 0.5, 0, null, {"$minKey": 1}, {"$maxKey": 1}, {"$numberLong": "1"}, false, true, {"$date": 1000}, {"$regex": "\\s*"}, {"$oid": "4f39d78d4b90b2f2f1530841"}, [], ""], "sort": {"a": -1}}, "expected_output": "[ { \"a\" : 2} , { \"a\" : 1 , \"b\" : 2} , { \"a\" : 0} , { \"$minKey\" : 1} ,  null  , 0 , 0.5 , 1 , \"\" , { \"b\" : 0} , [ ] , { \"$oid\" : \"4f39d78d4b90b2f2f1530841\"} , false , true , { \"$date\" : \"1970-01-01T00:00:01.000Z\"} , { \"$regex\" : \"\\\\s*\"} , { \"$maxKey\" : 1}]\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the matcher, the update engine, and the value-ordering comparator described above, plus a typed-value (de)serialization layer for the JSON wire format. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result to stdout, matching the per-feature contracts above. The request's `op` selects behavior: `find` returns each matching document of `documents` (in input order, one per line) under `query`; `update` applies the `update` specification to `document` (using `query` for the positional placeholder) and prints the resulting document, or a normalized `error=<category>` line for invalid specifications; `sort` orders `values` by the `sort` specification and prints the resulting array. Typed values use the wire format described in "Background & Problem" (`$oid`, `$date`, `$numberLong`, `$regex`/`$options`, `$minKey`, `$maxKey`).

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same relative ordering rule as C004
