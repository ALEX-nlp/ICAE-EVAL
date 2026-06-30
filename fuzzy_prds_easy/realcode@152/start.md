## Product Requirement Document

# Structured Reference Processing Library - Parse, Transform, Normalize, and Render Resource References

## Project Goal

Build a structured reference processing library that allows developers to parse, inspect, transform, normalize, and render URI/IRI-style resource references without hand-writing fragile string manipulation.

---

## Background & Problem

Without this library, developers are forced to split resource references by delimiters, decode percent escapes manually, maintain authority and path rules themselves, and reassemble strings while preserving query ordering, empty values, default ports, and Unicode hostnames. This leads to repetitive code, broken edge cases, accidental password disclosure, and inconsistent behavior across URI and IRI inputs.

With this library, developers work with references as structured values: parsing exposes stable components, transformations return new references, Unicode and ASCII forms can be converted deliberately, malformed input is rejected predictably, and adapter output can be compared as a black-box contract.

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
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project size):
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
### Feature 1: Reference Parsing and Inspection

**As a developer**, I want to parse reference text into observable components, so I can validate and inspect resource locations without manually splitting strings.

**Expected Behavior / Usage:**

*1.1 Parse Encoded References — Preserve encoded text while exposing structural components*

Encoded parsing accepts a reference string and prints the exact rendered text, password-redacted text, scheme, authority usage, host, effective port, rooted-path flag, path segment array, ordered query pairs, fragment, and raw userinfo. Percent escapes remain part of the component text rather than being decoded.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_parse_encoded_references.json`

```json
{
    "cases": [
        {
            "expected_output": "[informational prefix string]http://www.foo.com/a/nice/path/?zot=23&zut\n[informational prefix string]http://www.foo.com/a/nice/path/?zot=23&zut\nscheme=http\nuses_authority=true\nhost=www.foo.com\nport=80\nrooted_path=true\npath=[\"a\",\"nice\",\"path\",\"\"]\nquery=[[\"zot\",\"23\"],[\"zut\",null]]\nfragment=\nuserinfo=\"\"\n",
            "input": {
                "feature": "inspect_encoded_url",
                "url": "http://www.foo.com/a/nice/path/?zot=23&zut"
            }
        },
        {
            "expected_output": "[informational prefix string]https://user:pass@example.com/path/to/here?k=v#nice\n[informational prefix string]https://user:@example.com/path/to/here?k=v#nice\nscheme=https\nuses_authority=true\nhost=example.com\nport=443\nrooted_path=true\npath=[\"path\",\"to\",\"here\"]\nquery=[[\"k\",\"v\"]]\nfragment=nice\nuserinfo=\"user:pass\"\n",
            "input": {
                "feature": "inspect_encoded_url",
                "url": "https://user:pass@example.com/path/to/here?k=v#nice"
            }
        }
    ],
    "description": "Parse an encoded reference and print its structural URL components without decoding percent escapes."
}
```

*1.2 Parse Decoded References — Decode percent escapes and internationalized hostnames into human-readable components*

Decoded parsing accepts a reference string and prints the same component lines as encoded parsing, but component values are decoded into Unicode where applicable. Percent-encoded query names that decode to the same key appear under the same decoded name while preserving their order.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_parse_decoded_references.json`

```json
{
    "cases": [
        {
            "expected_output": "[informational prefix string]https://%75%73%65%72:%00%00%00%00@xn--bcher-kva.ch:8080/a/nice%20nice/./path/?zot=23%25&zut#frég\n[informational prefix string]https://%75%73%65%72:@xn--bcher-kva.ch:8080/a/nice%20nice/./path/?zot=23%25&zut#frég\nscheme=https\nuses_authority=true\nhost=bücher.ch\nport=8080\nrooted_path=true\npath=[\"a\",\"nice nice\",\".\",\"path\",\"\"]\nquery=[[\"zot\",\"23%\"],[\"zut\",null]]\nfragment=frég\nuserinfo=[\"user\",\"\\u0000\\u0000\\u0000\\u0000\"]\n",
            "input": {
                "feature": "inspect_decoded_url",
                "url": "https://%75%73%65%72:%00%00%00%00@xn--bcher-kva.ch:8080/a/nice%20nice/./path/?zot=23%25&zut#frég"
            }
        },
        {
            "expected_output": "[informational prefix string]/?%61rg=b&arg=c\n[informational prefix string]/?%61rg=b&arg=c\nscheme=\nuses_authority=false\nhost=\nport=null\nrooted_path=true\npath=[\"\"]\nquery=[[\"arg\",\"b\"],[\"arg\",\"c\"]]\nfragment=\nuserinfo=[\"\"]\n",
            "input": {
                "feature": "inspect_decoded_url",
                "url": "/?%61rg=b&arg=c"
            }
        }
    ],
    "description": "Parse a reference into decoded Unicode components and print its human-readable structure."
}
```

*1.3 Select Encoded or Decoded Parsing Through a Facade — Choose representation and surface lazy decoding failures*

The high-level parsing command accepts a reference string plus a representation selector. It prints `representation=decoded` or `representation=encoded`, followed by the same structural component lines. When requested, it also prints a selected query value list and fragment value. If malformed text is deferred until a component is read, the adapter prints a neutral error category rather than a runtime-specific exception.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_parse_facade_and_lazy_decoding.json`

```json
{
    "cases": [
        {
            "expected_output": "representation=decoded\n[informational prefix string]https://%75%73%65%72:%00%00%00%00@xn--bcher-kva.ch:8080/a/nice%20nice/./path/?zot=23%25&zut#frég\n[informational prefix string]https://%75%73%65%72:@xn--bcher-kva.ch:8080/a/nice%20nice/./path/?zot=23%25&zut#frég\nscheme=https\nuses_authority=true\nhost=bücher.ch\nport=8080\nrooted_path=true\npath=[\"a\",\"nice nice\",\".\",\"path\",\"\"]\nquery=[[\"zot\",\"23%\"],[\"zut\",null]]\nfragment=frég\nuserinfo=[\"user\",\"\\u0000\\u0000\\u0000\\u0000\"]\nfragment_value=frég\nquery_values=[\"23%\"]\n",
            "input": {
                "decoded": true,
                "feature": "parse_url",
                "query_key": "zot",
                "read_fragment": true,
                "url": "https://%75%73%65%72:%00%00%00%00@xn--bcher-kva.ch:8080/a/nice%20nice/./path/?zot=23%25&zut#frég"
            }
        },
        {
            "expected_output": "representation=encoded\n[informational prefix string]https://%75%73%65%72:%00%00%00%00@xn--bcher-kva.ch:8080/a/nice%20nice/./path/?zot=23%25&zut#frég\n[informational prefix string]https://%75%73%65%72:@xn--bcher-kva.ch:8080/a/nice%20nice/./path/?zot=23%25&zut#frég\nscheme=https\nuses_authority=true\nhost=xn--bcher-kva.ch\nport=8080\nrooted_path=true\npath=[\"a\",\"nice%20nice\",\".\",\"path\",\"\"]\nquery=[[\"zot\",\"23%25\"],[\"zut\",null]]\nfragment=frég\nuserinfo=\"%75%73%65%72:%00%00%00%00\"\nquery_values=[\"23%25\"]\n",
            "input": {
                "decoded": false,
                "feature": "parse_url",
                "query_key": "zot",
                "url": "https://%75%73%65%72:%00%00%00%00@xn--bcher-kva.ch:8080/a/nice%20nice/./path/?zot=23%25&zut#frég"
            }
        }
    ],
    "description": "Parse through the high-level parser, selecting decoded or encoded output and reporting deferred decoding failures as neutral errors."
}
```

*1.4 Reject Malformed References — Report neutral error categories for invalid input*

Malformed references must not leak host-language exception names or runtime messages. Invalid ports print `error=invalid_port`; malformed authority, host, or undecodable reference text prints `error=invalid_url` or `error=invalid_text_encoding` as appropriate, followed by the original `url=` line when the input contained a reference string.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_reject_malformed_references.json`

```json
{
    "cases": [
        {
            "expected_output": "error=invalid_port\nurl=http://example.com:bad\n",
            "input": {
                "feature": "inspect_encoded_url",
                "url": "http://example.com:bad"
            }
        },
        {
            "expected_output": "error=invalid_url\nurl=http://[::1\n",
            "input": {
                "feature": "inspect_encoded_url",
                "url": "http://[::1"
            }
        }
    ],
    "description": "Reject malformed references and print a language-neutral error category plus the offending input."
}
```

---
### Feature 2: Path and Reference Transformation

**As a developer**, I want to create related references from existing ones, so I can navigate resource hierarchies while preserving the correct query, fragment, and authority semantics.

**Expected Behavior / Usage:**

*2.1 Append Path Segments — Add literal child segments safely*

The adapter accepts a base reference and a list of literal path segments. It appends each segment to the path, escapes embedded path separators inside a segment, preserves existing query and fragment data, and prints the rendered text plus final path, query, and fragment lines.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_append_path_segments.json`

```json
{
    "cases": [
        {
            "expected_output": "[informational prefix string]http://www.foo.com/a/nice/path/gong?zot=23&zut\npath=[\"a\",\"nice\",\"path\",\"gong\"]\nquery=[[\"zot\",\"23\"],[\"zut\",null]]\nfragment=\n",
            "input": {
                "feature": "path_append",
                "segments": [
                    "gong"
                ],
                "url": "http://www.foo.com/a/nice/path/?zot=23&zut"
            }
        },
        {
            "expected_output": "[informational prefix string]http://www.foo.com/a/nice/path/gong%2Fdouble%2F?zot=23&zut\npath=[\"a\",\"nice\",\"path\",\"gong%2Fdouble%2F\"]\nquery=[[\"zot\",\"23\"],[\"zut\",null]]\nfragment=\n",
            "input": {
                "feature": "path_append",
                "segments": [
                    "gong/double/"
                ],
                "url": "http://www.foo.com/a/nice/path/?zot=23&zut"
            }
        }
    ],
    "description": "Append one or more literal path segments while preserving the existing query and fragment and escaping embedded separators."
}
```

*2.2 Replace the Last Path Segment — Create a sibling reference*

The adapter accepts a base reference and a literal replacement segment. If the base ends with a trailing path marker, the replacement is appended after that directory; otherwise, the final existing segment is replaced. Query and fragment data are preserved, and output includes rendered text, final path, query, and fragment.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_replace_last_path_segment.json`

```json
{
    "cases": [
        {
            "expected_output": "[informational prefix string]http://www.foo.com/a/nice/path/sister?zot=23&zut\npath=[\"a\",\"nice\",\"path\",\"sister\"]\nquery=[[\"zot\",\"23\"],[\"zut\",null]]\nfragment=\n",
            "input": {
                "feature": "path_replace_last",
                "segment": "sister",
                "url": "http://www.foo.com/a/nice/path/?zot=23&zut"
            }
        },
        {
            "expected_output": "[informational prefix string]http://www.foo.com/a/nice/sister?zot=23&zut\npath=[\"a\",\"nice\",\"sister\"]\nquery=[[\"zot\",\"23\"],[\"zut\",null]]\nfragment=\n",
            "input": {
                "feature": "path_replace_last",
                "segment": "sister",
                "url": "http://www.foo.com/a/nice/path?zot=23&zut"
            }
        }
    ],
    "description": "Replace the final path segment with a literal sibling segment while preserving query and fragment data."
}
```

*2.3 Resolve Relative References — Apply standard relative-reference resolution*

The adapter accepts a base reference and a relative or authority-relative reference. It resolves dot segments, handles empty references, replaces or preserves query and fragment according to the reference form, supports authority replacement, and prints rendered text, path, query, fragment, and host.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_resolve_relative_references.json`

```json
{
    "cases": [
        {
            "expected_output": "[informational prefix string]http://www.foo.com/a/nice/path/click\npath=[\"a\",\"nice\",\"path\",\"click\"]\nquery=[]\nfragment=\nhost=www.foo.com\n",
            "input": {
                "base": "http://www.foo.com/a/nice/path/?zot=23&zut",
                "feature": "resolve_reference",
                "reference": "click"
            }
        },
        {
            "expected_output": "[informational prefix string]http://a/b/g\npath=[\"b\",\"g\"]\nquery=[]\nfragment=\nhost=a\n",
            "input": {
                "base": "http://a/b/c/d;p?q",
                "feature": "resolve_reference",
                "reference": "../g"
            }
        },
        {
            "expected_output": "[informational prefix string]http://g\npath=[]\nquery=[]\nfragment=\nhost=g\n",
            "input": {
                "base": "http://a/b/c/d;p?q",
                "feature": "resolve_reference",
                "reference": "//g"
            }
        }
    ],
    "description": "Resolve a relative reference against a base reference using standard dot-segment, query, fragment, and authority rules."
}
```

---
### Feature 3: Query Parameter Manipulation

**As a developer**, I want to add, replace, remove, and inspect ordered query parameters, so I can update references without losing duplicate keys or valueless flags.

**Expected Behavior / Usage:**

*3.1 Encoded Query Updates — Manipulate raw query pairs while preserving order*

The adapter accepts a reference and a sequence of query changes. Adding appends a new ordered pair, setting replaces all pairs with the same name using one new pair, and removing deletes all matching names. Valueless parameters are represented as JSON null in the printed `query=` array. When a `get` key is provided, output also prints its value list.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_encoded_query_updates.json`

```json
{
    "cases": [
        {
            "expected_output": "[informational prefix string]http://www.foo.com/a/nice/path/?zot=23&zut&foo=bar\nquery=[[\"zot\",\"23\"],[\"zut\",null],[\"foo\",\"bar\"]]\nvalues=[\"bar\"]\n",
            "input": {
                "feature": "query_update",
                "get": "foo",
                "steps": [
                    {
                        "change": "add",
                        "name": "foo",
                        "value": "bar"
                    }
                ],
                "url": "http://www.foo.com/a/nice/path/?zot=23&zut"
            }
        },
        {
            "expected_output": "[informational prefix string]http://www.foo.com/a/nice/path/?zot=99&zut\nquery=[[\"zot\",\"99\"],[\"zut\",null]]\nvalues=[\"99\"]\n",
            "input": {
                "feature": "query_update",
                "get": "zot",
                "steps": [
                    {
                        "change": "set",
                        "name": "zot",
                        "value": "99"
                    }
                ],
                "url": "http://www.foo.com/a/nice/path/?zot=23&zut"
            }
        },
        {
            "expected_output": "[informational prefix string]http://www.foo.com/a/nice/path/?zut\nquery=[[\"zut\",null]]\n",
            "input": {
                "feature": "query_update",
                "steps": [
                    {
                        "change": "remove",
                        "name": "zot"
                    }
                ],
                "url": "http://www.foo.com/a/nice/path/?zot=23&zut"
            }
        }
    ],
    "description": "Add, set, and remove encoded query parameters while preserving ordering and valueless parameters."
}
```

*3.2 Decoded Query Updates — Manipulate query pairs through decoded Unicode names and values*

Decoded query updates accept decoded Unicode names and values, apply the same add/set/remove semantics, and render the final reference with necessary escaping. Output prints the final rendered reference, decoded ordered query pairs, and an optional decoded value list for the requested key.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_decoded_query_updates.json`

```json
{
    "cases": [
        {
            "expected_output": "[informational prefix string]https://%75%73%65%72:%00%00%00%00@xn--bcher-kva.ch:8080/a/nice%20nice/./path/?zot=23%25&zut&%20=space#frég\nquery=[[\"zot\",\"23%\"],[\"zut\",null],[\" \",\"space\"]]\nvalues=[\"space\"]\n",
            "input": {
                "feature": "decoded_query_update",
                "get": " ",
                "steps": [
                    {
                        "change": "add",
                        "name": " ",
                        "value": "space"
                    }
                ],
                "url": "https://%75%73%65%72:%00%00%00%00@xn--bcher-kva.ch:8080/a/nice%20nice/./path/?zot=23%25&zut#frég"
            }
        },
        {
            "expected_output": "[informational prefix string]/?arg=d\nquery=[[\"arg\",\"d\"]]\nvalues=[\"d\"]\n",
            "input": {
                "feature": "decoded_query_update",
                "get": "arg",
                "steps": [
                    {
                        "change": "set",
                        "name": "arg",
                        "value": "d"
                    }
                ],
                "url": "/?%61rg=b&arg=c"
            }
        }
    ],
    "description": "Manipulate query parameters through decoded Unicode names and values while serializing them back to escaped text."
}
```

---
### Feature 4: Conversion and Normalization

**As a developer**, I want to convert and canonicalize reference text, so I can produce stable URI/IRI output while preserving reference meaning.

**Expected Behavior / Usage:**

*4.1 URI and IRI Conversion — Convert between ASCII-safe and Unicode-readable forms*

The adapter accepts a reference and a conversion target. URI conversion emits an ASCII-safe representation using percent escapes and punycode hostnames where needed. IRI conversion emits Unicode-readable host, path, query, and fragment text where valid. Output includes rendered text, host, path, query, and fragment lines.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_uri_iri_conversion.json`

```json
{
    "cases": [
        {
            "expected_output": "[informational prefix string]http://xn--xample-9ua.com/%C3%A9%20path?x=%C3%A9#%C3%A9\nhost=xn--xample-9ua.com\npath=[\"%C3%A9%20path\"]\nquery=[[\"x\",\"%C3%A9\"]]\nfragment=%C3%A9\n",
            "input": {
                "feature": "convert_reference_text",
                "target": "uri",
                "url": "http://éxample.com/é path?x=é#é"
            }
        },
        {
            "expected_output": "[informational prefix string]http://bücher.ch/a b?x=é#frég\nhost=bücher.ch\npath=[\"a b\"]\nquery=[[\"x\",\"é\"]]\nfragment=frég\n",
            "input": {
                "feature": "convert_reference_text",
                "target": "iri",
                "url": "http://xn--bcher-kva.ch/a%20b?x=%C3%A9#fr%C3%A9g"
            }
        }
    ],
    "description": "Convert reference text between URI-safe ASCII form and IRI Unicode form while preserving component meaning."
}
```

*4.2 Reference Normalization — Canonicalize case, default ports, dot segments, and safe escapes*

Normalization accepts a reference string and prints the canonical rendered text plus scheme, host, path, and query. It lowercases scheme and host where applicable, removes default ports, resolves `.` and `..` path segments, and decodes safe percent escapes without changing component meaning.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_normalize_references.json`

```json
{
    "cases": [
        {
            "expected_output": "[informational prefix string]http://example.com/a/c\nscheme=http\nhost=example.com\npath=[\"a\",\"c\"]\nquery=[]\n",
            "input": {
                "feature": "normalize_reference",
                "url": "HTTP://EXAMPLE.COM:80/a/./b/../c"
            }
        },
        {
            "expected_output": "[informational prefix string]https://example.com/~user?q=A\nscheme=https\nhost=example.com\npath=[\"~user\"]\nquery=[[\"q\",\"A\"]]\n",
            "input": {
                "feature": "normalize_reference",
                "url": "https://EXAMPLE.COM:443/%7Euser?q=%41"
            }
        }
    ],
    "description": "Normalize references by canonicalizing scheme and host case, removing default ports, resolving dot segments, and normalizing safe escapes."
}
```

---
### Feature 5: Scheme Registration

**As a developer**, I want to define scheme metadata, so custom schemes render with the correct authority and default-port behavior.

**Expected Behavior / Usage:**

*5.1 Register Authority-Based Schemes — Configure schemes that use host authority and default ports*

The adapter accepts a scheme name, authority usage flag, optional default port, and a reference or replacement host. Authority-based schemes render with `//` when a host is present. If the reference explicitly contains the configured default port, the rendered text omits that port while the printed `port=` line reports the effective default.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_register_authority_schemes.json`

```json
{
    "cases": [
        {
            "expected_output": "[informational prefix string]deltron://example.com\nscheme=deltron\nuses_authority=true\nport=3030\nhost=example.com\npath=[]\n",
            "input": {
                "default_port": 3030,
                "feature": "register_scheme_and_render",
                "scheme": "deltron",
                "url": "deltron://example.com",
                "uses_authority": true
            }
        },
        {
            "expected_output": "[informational prefix string]deltron://example.com\nscheme=deltron\nuses_authority=true\nport=3030\nhost=example.com\npath=[]\n",
            "input": {
                "default_port": 3030,
                "feature": "register_scheme_and_render",
                "scheme": "deltron",
                "url": "deltron://example.com:3030",
                "uses_authority": true
            }
        }
    ],
    "description": "Register an authority-based scheme with a default port and render URLs using its authority and default-port rules."
}
```

*5.2 Register Path-Only Schemes — Configure schemes that do not use authority separators*

Path-only scheme registration accepts a scheme name with authority usage disabled and a replacement path. The rendered reference uses `scheme:path` form without `//`, and output prints the scheme, authority flag, null port, empty host, and path segment array.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_register_path_only_schemes.json`

```json
{
    "cases": [
        {
            "expected_output": "[informational prefix string]noloctron:example/path\nscheme=noloctron\nuses_authority=false\nport=null\nhost=\npath=[\"example\",\"path\"]\n",
            "input": {
                "feature": "register_scheme_and_render",
                "replace_path": [
                    "example",
                    "path"
                ],
                "scheme": "noloctron",
                "url": "noloctron:",
                "uses_authority": false
            }
        }
    ],
    "description": "Register a path-only scheme and render paths without an authority separator."
}
```

*5.3 Reject Invalid Scheme Registration — Validate inconsistent scheme metadata*

Invalid scheme metadata is rejected at the adapter boundary with language-neutral output. A path-only scheme cannot also define a default port, authority usage must be a valid boolean when provided, and default ports must be valid integers. Output includes `error=invalid_scheme_registration` and the attempted scheme name.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_reject_invalid_scheme_registration.json`

```json
{
    "cases": [
        {
            "expected_output": "error=invalid_scheme_registration\nscheme=badnetlocless\n",
            "input": {
                "default_port": 7,
                "feature": "register_scheme_and_render",
                "scheme": "badnetlocless",
                "uses_authority": false
            }
        },
        {
            "expected_output": "error=invalid_scheme_registration\nscheme=badnetloc\n",
            "input": {
                "feature": "register_scheme_and_render",
                "scheme": "badnetloc",
                "uses_authority": null
            }
        }
    ],
    "description": "Reject inconsistent scheme registration metadata using language-neutral error output."
}
```

---
### Feature 6: Reference Identity

**As a developer**, I want to compare parsed references by structural identity, so I can use references as stable values in sets and maps.

**Expected Behavior / Usage:**

*6.1 Compare Reference Identity — Report equality and distinct hash-set membership*

The adapter accepts two reference strings, parses them, compares their structured identity, and places them in a distinct-value set. It prints whether the two references are equal, the number of distinct parsed values, and each rendered text so equality cannot be faked by a single boolean alone.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_compare_reference_identity.json`

```json
{
    "cases": [
        {
            "expected_output": "equal=true\ndistinct_hash_count=1\nfirst_[informational prefix string]http://www.foo.com/a/nice/path/?zot=23&zut\nsecond_[informational prefix string]http://www.foo.com/a/nice/path/?zot=23&zut\n",
            "input": {
                "feature": "compare_urls",
                "urls": [
                    "http://www.foo.com/a/nice/path/?zot=23&zut",
                    "http://www.foo.com/a/nice/path/?zot=23&zut"
                ]
            }
        },
        {
            "expected_output": "equal=false\ndistinct_hash_count=2\nfirst_[informational prefix string]http://www.foo.com/a/nice/path/?zot=23&zut\nsecond_[informational prefix string]http://www.foo.com/a/nice/path/?zot=23\n",
            "input": {
                "feature": "compare_urls",
                "urls": [
                    "http://www.foo.com/a/nice/path/?zot=23&zut",
                    "http://www.foo.com/a/nice/path/?zot=23"
                ]
            }
        }
    ],
    "description": "Compare parsed references by normalized structural identity and report hash-set distinctness with their rendered text."
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_parse_encoded_references.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_parse_encoded_references@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- check the reserved escape handling section
