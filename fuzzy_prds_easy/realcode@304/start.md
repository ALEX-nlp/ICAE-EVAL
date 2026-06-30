## Product Requirement Document

# XML Toolkit — Parsing, Querying, Serializing, and Building XML Documents

## Project Goal

Build a lightweight XML toolkit that lets developers parse XML text into a navigable document tree, inspect and query that tree, escape and unescape character data, report precise errors on malformed input, and assemble new documents programmatically — all through one cohesive, idiomatic library, so applications never have to hand-roll fragile string manipulation to work with XML.

---

## Background & Problem

Applications routinely need to read configuration, exchange messages, or transform markup expressed as XML. Without a dedicated toolkit, developers resort to ad-hoc string slicing and regular expressions, which fail on nested structure, namespaces, character references, CDATA sections, comments, processing instructions, and document type declarations. Such code is brittle, hard to maintain, and silently produces wrong results on edge cases.

With this toolkit, a developer can: turn XML text into a fully-typed tree and serialize it back to a canonical string; produce indented, human-readable output; inspect any element's structural facts; query for elements by name and namespace, either among direct children or recursively; decode and encode character/entity references against selectable entity tables; receive structured, position-aware diagnostics for malformed input; and construct documents step by step in code. The library models the standard XML node kinds (elements, attributes, text, CDATA, comments, processing instructions, declarations, document type declarations, documents, and fragments) and preserves namespace prefixes and attribute quoting styles throughout.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains. This domain (tokenizing/parsing, a typed node model, navigation, querying, entity coding, serialization, and a builder) is non-trivial and warrants a multi-file structure.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, the node model, navigation/querying, entity coding, serialization, and building into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived node types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Parse and Serialize (Round-Trip)

**As a developer**, I want to parse XML text into a document tree and serialize it back to a canonical string, so I can normalize markup and be sure the structure round-trips losslessly.

**Expected Behavior / Usage:**

The input carries an XML document as text. The system parses it into a tree and emits the canonical serialization. Serialization preserves structure, node order, attribute quoting style (single vs. double), namespace prefixes, CDATA sections, comments, processing instructions, and document type declarations. It normalizes only insignificant in-tag whitespace — for instance, the optional space before a self-closing slash is removed, so `<root key="value" />` serializes as `<root key="value"/>`. A childless element that was written self-closing stays self-closing; an element written with a separate closing tag keeps both tags.

**Test Cases:** `rcb_tests/public_test_cases/feature1_round_trip.json`

```json
{
    "description": "Parse a complete XML document from its textual form and serialize it back to a canonical XML string. The serializer normalizes insignificant whitespace inside tags (for example the optional space before a self-closing slash is dropped) while preserving the document's structure, node order, attribute quoting style, character data sections, comments, processing instructions, document type declarations, and namespace prefixes. The output is the canonical textual representation of the parsed tree.",
    "cases": [
        {
            "input": {"action": "serialize", "xml": "<root key=\"value\" />"},
            "expected_output": "<root key=\"value\"/>\n"
        },
        {
            "input": {"action": "serialize", "xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><schema><!-- <foo></foo> --></schema>"},
            "expected_output": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><schema><!-- <foo></foo> --></schema>\n"
        }
    ]
}
```

---

### Feature 2: Pretty-Print

**As a developer**, I want to re-serialize a document with indentation, so I can produce human-readable output for logs and diffs.

**Expected Behavior / Usage:**

The input carries an XML document as text and an optional indent string. The system parses it and emits an indented serialization: each nested node sits on its own line, indented by its depth, and siblings appear on separate lines. The indent unit defaults to two spaces but can be overridden by supplying an explicit indent string (for example four spaces). Insignificant whitespace between nodes in the source is normalized away and replaced by the pretty-printer's own line breaks and indentation.

**Test Cases:** `rcb_tests/public_test_cases/feature2_pretty_print.json`

```json
{
    "description": "Parse an XML document and re-serialize it in a human-readable, indented form. Each nested node is placed on its own line and indented according to its depth; sibling nodes appear on separate lines. The indentation unit defaults to two spaces but can be overridden by supplying an explicit indent string. Insignificant whitespace between nodes is normalized away and replaced by the pretty-printer's own line breaks and indentation.",
    "cases": [
        {
            "input": {"action": "pretty", "xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?> <!-- before -->\n<element/>\t<!-- after -->"},
            "expected_output": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<!-- before -->\n<element/>\n<!-- after -->\n"
        },
        {
            "input": {"action": "pretty", "xml": "<bookstore><book><title>XML</title></book></bookstore>"},
            "expected_output": "<bookstore>\n  <book>\n    <title>XML</title>\n  </book>\n</bookstore>\n"
        }
    ]
}
```

---

### Feature 3: Element Inspection

**As a developer**, I want to read the structural facts of an element, so I can drive logic from the parsed tree rather than re-scanning text.

**Expected Behavior / Usage:**

The input carries an XML document as text. The system parses it and reports, for the root element: its node kind; its qualified tag name (including any namespace prefix); the number of attributes; the number of direct child nodes; the total number of descendant nodes (children, their attributes, and deeper descendants); the combined text content (the concatenation of all descendant character data); whether it was written in self-closing form; and its canonical serialized form. An element written as an empty open/close pair is reported as not self-closing; one written as a single self-closing tag is reported as self-closing. Each reported fact is emitted on its own `key=value` line in the order above.

**Test Cases:** `rcb_tests/public_test_cases/feature3_element_inspection.json`

```json
{
    "description": "Parse an XML document and report the structural facts of its root element: the element's qualified tag name (including any namespace prefix), the number of attributes it carries, the number of direct child nodes, the total number of descendant nodes (children, their attributes, and deeper descendants), its combined text content (the concatenation of all descendant character data), whether it was written in self-closing form, and its canonical serialized form. An element written as an empty pair of open/close tags is reported as not self-closing, whereas an element written with a single self-closing tag is reported as self-closing.",
    "cases": [
        {
            "input": {"action": "inspect_element", "xml": "<ns:data key=\"value\">Am I or are the other crazy?</ns:data>"},
            "expected_output": "kind=element\nname=ns:data\nattributes=1\nchildren=1\ndescendants=2\ntext=Am I or are the other crazy?\n[a likely detection condition for self-closing attributes]\nserialized=<ns:data key=\"value\">Am I or are the other crazy?</ns:data>\n"
        },
        {
            "input": {"action": "inspect_element", "xml": "<data></data>"},
            "expected_output": "kind=element\nname=data\nattributes=0\nchildren=0\ndescendants=0\ntext=\nself_closing=false\nserialized=<data></data>\n"
        }
    ]
}
```

---

### Feature 4: Attribute Parsing

**As a developer**, I want to read an element's attributes with their decoded values and quoting style, so I can consume configuration faithfully and re-emit it correctly.

**Expected Behavior / Usage:**

The input carries an XML element as text. The system parses it and reports the attribute count, then, for each attribute in document order, its qualified name, its decoded value (with all character and entity references resolved to literal characters), the quote style used in the source (single or double), and its canonical serialized form (in which the value is re-escaped as required for the chosen quote style). An attribute written with an empty value is reported with an empty value string.

**Test Cases:** `rcb_tests/public_test_cases/feature4_attributes.json`

```json
{
    "description": "Parse an XML element and report, for each of its attributes in document order, the attribute's qualified name, its decoded value (with all character and entity references resolved to their literal characters), the quote style used in the source (single or double), and its canonical serialized form (in which the value is re-escaped as required for the chosen quote style). The count of attributes is reported first. An attribute written with an empty value is reported with an empty value string.",
    "cases": [
        {
            "input": {"action": "attributes", "xml": "<data ns:attr=\"Am I or are the other crazy?\" />"},
            "expected_output": "count=1\nname=ns:attr\nvalue=Am I or are the other crazy?\nquote=double\nserialized=ns:attr=\"Am I or are the other crazy?\"\n"
        },
        {
            "input": {"action": "attributes", "xml": "<data ns:attr='Am I or are the other crazy?' />"},
            "expected_output": "count=1\nname=ns:attr\nvalue=Am I or are the other crazy?\nquote=single\nserialized=ns:attr='Am I or are the other crazy?'\n"
        }
    ]
}
```

---

### Feature 5: Character/Entity Coding

**As a developer**, I want to decode and encode character/entity references against selectable tables, so I can safely move text in and out of XML.

**Expected Behavior / Usage:**

*5.1 Decode references — resolve references in a raw string against a selectable entity table.*

The input carries a raw string and a table selector. Numeric references are always recognized: a hexadecimal form (a hash, the letter `x` in either case, then hex digits) and a decimal form (a hash then decimal digits) both resolve to the character at that code point. Named references resolve through the selected table: a minimal table (`xml`) recognizes only the five core XML names; richer tables (`html`, `html5`) additionally recognize HTML named references. A reference that is unknown, has no closing delimiter, or is empty is left untouched. A pass-through table (`none`) performs no resolution and returns the input verbatim. The decoded string is the output.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_decode.json`

```json
{
    "description": "Resolve character and entity references in a raw string using a selectable entity table. The numeric forms are always recognized: a hexadecimal form (a hash, the letter x in either case, hexadecimal digits) and a decimal form (a hash followed by decimal digits) both resolve to the character at that code point. Named references resolve through the selected table: the minimal table recognizes only the five core XML names; richer tables additionally recognize HTML named references. A reference that is unknown, has no closing delimiter, or is empty is left untouched in the output. The pass-through table performs no resolution at all and returns the input verbatim.",
    "cases": [
        {"input": {"action": "decode", "mapping": "xml", "input": "&#X41;"}, "expected_output": "A\n"},
        {"input": {"action": "decode", "mapping": "xml", "input": "&lt;&gt;&amp;&apos;&quot;"}, "expected_output": "<>&'\"\n"},
        {"input": {"action": "decode", "mapping": "xml", "input": "&invalid;"}, "expected_output": "&invalid;\n"},
        {"input": {"action": "decode", "mapping": "html", "input": "&eacute;&Eacute;"}, "expected_output": "éÉ\n"}
    ]
}
```

*5.2 Encode text — escape a raw string for use as element text.*

The input carries a raw string and a table selector. With the standard table (`xml`), the less-than character and the ampersand are replaced by their named references, while every other character — including quotes and already-escaped sequences — is emitted verbatim (so an existing `&` inside `&amp;` is itself escaped again). The pass-through table (`none`) returns the input unchanged. The escaped string is the output.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_encode_text.json`

```json
{
    "description": "Escape a raw string so that it is safe to embed as XML element text using a selectable entity table. With the standard table the less-than character and the ampersand are replaced by their named references while all other characters, including already-escaped sequences and quotes, are emitted verbatim. The pass-through table performs no escaping and returns the input unchanged.",
    "cases": [
        {"input": {"action": "encode_text", "mapping": "xml", "input": "<"}, "expected_output": "&lt;\n"},
        {"input": {"action": "encode_text", "mapping": "xml", "input": "<foo &amp;>"}, "expected_output": "&lt;foo &amp;amp;>\n"}
    ]
}
```

*5.3 Encode attribute value — escape a raw string for use as an attribute value under a given quote style.*

The input carries a raw string, a table selector, and a quote style (single or double). Only the quote character matching the chosen style is escaped to its named reference; the opposite quote is left verbatim. The ampersand and the less-than character are always escaped, and the tab, newline, and carriage-return characters are escaped to their numeric references. The pass-through table (`none`) returns the input unchanged for either quote style. The escaped string is the output.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_encode_attribute.json`

```json
{
    "description": "Escape a raw string so that it is safe to embed as an XML attribute value, given the surrounding quote style (single or double). Only the quote character matching the chosen style is escaped to its named reference; the opposite quote character is left verbatim. The ampersand and the less-than character are always escaped, and the tab, newline, and carriage-return characters are escaped to their numeric references. The pass-through table performs no escaping and returns the input unchanged for either quote style.",
    "cases": [
        {"input": {"action": "encode_attribute", "mapping": "xml", "quote": "single", "input": "'"}, "expected_output": "&apos;\n"},
        {"input": {"action": "encode_attribute", "mapping": "xml", "quote": "double", "input": "\""}, "expected_output": "&quot;\n"}
    ]
}
```

---

### Feature 6: Element Queries

**As a developer**, I want to find elements by name and namespace, so I can extract data from a document without manual traversal.

**Expected Behavior / Usage:**

*6.1 Direct children — search only the immediate children of a context element.*

The input carries an XML document, a name filter, and an optional namespace filter; the search context is the root element. The result reports the match count followed by each matched element's qualified name, in document order. The name filter is either a specific name or a wildcard (`*`) matching any name. With no namespace filter, the requested name is compared against the element's fully qualified name (prefix included). With a namespace filter, only the local name is compared and the element's namespace URI must match the filter; a wildcard namespace filter (`*`) matches any namespace. Only immediate children are considered.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_find_elements.json`

```json
{
    "description": "Find the direct child elements of a context element whose tag matches a requested name and namespace filter, and report the number of matches followed by each matched element's qualified name in document order. The name filter may be a specific local/qualified name or a wildcard that matches any name. When no namespace filter is supplied, the requested name is compared against the element's fully qualified name (prefix included). When a namespace filter is supplied, only the local name is compared and the element's namespace URI must match the filter; a wildcard namespace filter matches elements in any namespace. Only immediate children are considered, never deeper descendants.",
    "cases": [
        {
            "input": {"action": "find_elements", "from_root": true, "name": "a", "xml": "<root xmlns:x=\"http://example.com/x\"><a/><a/><x:a/><b/></root>"},
            "expected_output": "count=2\nname=a\nname=a\n"
        },
        {
            "input": {"action": "find_elements", "from_root": true, "name": "a", "namespace": "*", "xml": "<root xmlns:x=\"http://example.com/x\"><a/><a/><x:a/><b/></root>"},
            "expected_output": "count=3\nname=a\nname=a\nname=x:a\n"
        }
    ]
}
```

*6.2 Recursive descendants — search the whole tree.*

The input carries an XML document, a name filter, and an optional namespace filter; the search starts at the document and visits the root element and every descendant in document order. The name and namespace filtering rules are identical to the direct-children search, but the search is recursive over the entire tree. A wildcard name with no namespace filter therefore enumerates every element in the document. The result reports the match count followed by each matched element's qualified name.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_find_all_elements.json`

```json
{
    "description": "Find all elements anywhere in the document tree (the root element and every descendant, in document order) whose tag matches a requested name and namespace filter, and report the number of matches followed by each matched element's qualified name. The name and namespace filtering rules are identical to the direct-children search, but here the search is recursive over the whole tree rather than limited to immediate children. A wildcard name combined with no namespace filter therefore enumerates every element in the document.",
    "cases": [
        {
            "input": {"action": "find_all_elements", "name": "a", "xml": "<root xmlns:x=\"http://example.com/x\"><group><a/><x:a/></group><a/></root>"},
            "expected_output": "count=2\nname=a\nname=a\n"
        },
        {
            "input": {"action": "find_all_elements", "name": "*", "xml": "<root xmlns:x=\"http://example.com/x\"><group><a/><x:a/></group><a/></root>"},
            "expected_output": "count=5\nname=root\nname=group\nname=a\nname=x:a\nname=a\n"
        }
    ]
}
```

---

### Feature 7: Parse Error Reporting

**As a developer**, I want malformed input to fail with a precise, structured diagnostic, so I can pinpoint and fix the problem.

**Expected Behavior / Usage:**

The input carries XML text that may be malformed. On a parse failure the system reports a neutral, structured error rather than a tree: a line `error=parse`, a line `message=<diagnostic>` describing what the parser expected at the point of failure, and a line `position=<offset>` giving the zero-based character offset into the input where the failure occurred. Conditions include: input that does not begin with a tag (the parser expects an opening `<` at the first non-tag position), trailing content after the root element (the parser expects end of input), a start tag closed by a non-matching end tag (the diagnostic names the expected and found end tags), an unterminated tag (the parser expects a closing `>`), and a tag with a missing name (the parser expects a name). The diagnostic text and offset are domain signals of the parsing contract; no host-language runtime details appear.

**Test Cases:** `rcb_tests/public_test_cases/feature7_parse_errors.json`

```json
{
    "description": "Attempt to parse malformed XML and report the failure as a neutral, structured error rather than a successful tree. The report carries a human-readable diagnostic describing what the parser expected at the point of failure and the zero-based character offset into the input where the failure occurred. Conditions covered include: input that does not begin with a tag, trailing content after the root element, a start tag closed by a non-matching end tag, an unterminated tag, and a tag with a missing name.",
    "cases": [
        {"input": {"action": "parse_error", "xml": ""}, "expected_output": "error=parse\nmessage=\"<\" expected\nposition=0\n"},
        {"input": {"action": "parse_error", "xml": "<foo></bar>"}, "expected_output": "error=parse\nmessage=Expected </foo>, but found </bar>\nposition=5\n"}
    ]
}
```

---

### Feature 8: Programmatic Document Building

**As a developer**, I want to assemble a document step by step in code, so I can generate XML without concatenating strings.

**Expected Behavior / Usage:**

The input carries an ordered list of build operations. Supported operations: add an XML declaration (with version, optional encoding, and extra attributes); add a processing instruction (a target plus raw content); add a comment; add a character-data (CDATA) section; add literal text; add an element (a tag name, an attribute map, an explicit self-closing preference, and a nested list of child operations or a single text payload); and add an attribute (name, value, and optional quote style) to the element currently being built. An element that has children or text renders with explicit open/close tags; a childless element renders self-closing unless self-closing is explicitly disabled. Consecutive text additions within one element are merged into a single text node. The output is the canonical serialization of the assembled document.

**Test Cases:** `rcb_tests/public_test_cases/feature8_build.json`

```json
{
    "description": "Build an XML document programmatically from a sequence of build operations and serialize the result. Supported operations include adding an XML declaration (with version, optional encoding, and extra attributes), a processing instruction (target plus raw content), comments, character-data (CDATA) sections, literal text, elements (with a tag name, an attribute map, an explicit self-closing preference, and nested child operations), and attributes (name, value, and optional quote style). Elements opened with children or text render with explicit open/close tags; childless elements render self-closing unless self-closing is explicitly disabled. Consecutive text additions within one element are merged. The output is the canonical serialization of the assembled document.",
    "cases": [
        {
            "input": {"action": "build", "ops": [
                {"op": "declaration", "encoding": "UTF-8"},
                {"op": "processing", "target": "xml-stylesheet", "text": "href=\"/style.css\" type=\"text/css\" title=\"default stylesheet\""},
                {"op": "element", "name": "bookstore", "children": [
                    {"op": "comment", "text": "Only one book?"},
                    {"op": "element", "name": "book", "children": [
                        {"op": "element", "name": "title", "children": [
                            {"op": "attribute", "name": "lang", "value": "en"},
                            {"op": "text", "text": "Harry "},
                            {"op": "cdata", "text": "Potter"}
                        ]},
                        {"op": "element", "name": "price", "text": "29.99"}
                    ]}
                ]}
            ]},
            "expected_output": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><?xml-stylesheet href=\"/style.css\" type=\"text/css\" title=\"default stylesheet\"?><bookstore><!--Only one book?--><book><title lang=\"en\">Harry <![CDATA[Potter]]></title><price>29.99</price></book></bookstore>\n"
        },
        {
            "input": {"action": "build", "ops": [
                {"op": "element", "name": "element", "children": [
                    {"op": "element", "name": "self-closing-default"},
                    {"op": "element", "name": "self-closing-true", "is_self_closing": true},
                    {"op": "element", "name": "self-closing-true-with-children", "is_self_closing": true, "text": "!"},
                    {"op": "element", "name": "self-closing-false", "is_self_closing": false}
                ]}
            ]},
            "expected_output": "<element><self-closing-default/><self-closing-true/><self-closing-true-with-children>!</self-closing-true-with-children><self-closing-false></self-closing-false></element>\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above — a tokenizer/parser, a typed node model (elements, attributes, text, CDATA, comments, processing instructions, declarations, document type declarations, documents, and fragments), navigation/query operations, selectable entity coding, serialization (canonical and pretty), and a programmatic builder. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, selects behavior by the request's `action`, invokes the appropriate core logic, and prints the raw result (or a neutral structured error) to stdout, matching the per-feature contracts above. Recognized actions: `serialize`, `pretty`, `inspect_element`, `attributes`, `decode`, `encode_text`, `encode_attribute`, `find_elements`, `find_all_elements`, `parse_error`, and `build`. Errors arising from malformed input must be rendered as neutral, domain-level signals (a category line plus structured fields) and must never leak host-language runtime exception identities.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- encode any entity references according to the entity resolution utility
- apply the same list formatting used in the iterator module
