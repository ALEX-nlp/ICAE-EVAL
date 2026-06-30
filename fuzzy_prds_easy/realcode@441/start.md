## Product Requirement Document

# Linked Data JSON Processor - JSON-LD Transformation and RDF Interchange

## Project Goal

Build a JSON-LD processing library that allows developers to expand, compact, flatten, frame, convert, and normalize linked data documents without hand-writing graph transformation and RDF serialization logic.

---

## Background & Problem

Without this library/tool, developers are forced to manually interpret JSON-LD contexts, resolve IRIs, preserve graph structure, convert RDF statements, and canonicalize blank nodes. This leads to repetitive code, subtle data-loss bugs, inconsistent serialization, and brittle interoperability with RDF systems.

With this library/tool, applications can submit JSON-LD or N-Quads data to well-defined processing operations and receive deterministic stdout representations that preserve graph semantics.

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

### Feature 1: JSON-LD Expansion

**As a developer**, I want to expand compact JSON-LD documents into full IRI-based node objects, so I can process data without relying on local aliases or abbreviated terms.

**Expected Behavior / Usage:**

The input is a JSON command whose operation is expansion, with a JSON-LD document and optional processing options such as a base IRI. The output is pretty-printed expanded JSON-LD on stdout. Expansion MUST apply context aliases, term mappings, type coercion, default language rules, and IRI expansion; properties that do not produce semantic graph data are omitted according to JSON-LD processing rules. Errors are not reported for valid expansion inputs in this feature.

**Test Cases:** `rcb_tests/public_test_cases/feature1_expand.json`

```json
{
    "description": "Expand compact JSON-LD documents into full IRI-based node objects while applying context aliases, type coercion, and default language rules.",
    "cases": [
        {
            "input": {
                "options": {},
                "document": {
                    "@context": {
                        "t1": "http://example.com/t1",
                        "t2": "http://example.com/t2",
                        "term1": "http://example.com/term1",
                        "term2": "http://example.com/term2",
                        "term3": "http://example.com/term3",
                        "term4": "http://example.com/term4",
                        "term5": "http://example.com/term5"
                    },
                    "@id": "http://example.com/id1",
                    "@type": "t1",
                    "term1": "v1",
                    "term2": {
                        "@value": "v2",
                        "@type": "t2"
                    },
                    "term3": {
                        "@value": "v3",
                        "@language": "en"
                    },
                    "term4": 4,
                    "term5": [
                        50,
                        51
                    ]
                },
                "algorithm": "expand",
                "base": "http://json-ld.org/test-suite/tests/expand-0002-in.jsonld"
            },
            "expected_output": "[ {\n  \"@id\" : \"http://example.com/id1\",\n  \"@type\" : [ \"http://example.com/t1\" ],\n  \"http://example.com/term1\" : [ {\n    \"@value\" : \"v1\"\n  } ],\n  \"http://example.com/term2\" : [ {\n    \"@type\" : \"http://example.com/t2\",\n    \"@value\" : \"v2\"\n  } ],\n  \"http://example.com/term3\" : [ {\n    \"@language\" : \"en\",\n    \"@value\" : \"v3\"\n  } ],\n  \"http://example.com/term4\" : [ {\n    \"@value\" : 4\n  } ],\n  \"http://example.com/term5\" : [ {\n    \"@value\" : 50\n  }, {\n    \"@value\" : 51\n  } ]\n} ]\n"
        },
        {
            "input": {
                "options": {},
                "document": {
                    "@context": {
                        "http://example.org/test#property1": {
                            "@type": "@id"
                        },
                        "http://example.org/test#property2": {
                            "@type": "@id"
                        },
                        "uri": "@id"
                    },
                    "http://example.org/test#property1": {
                        "http://example.org/test#property4": "foo",
                        "uri": "http://example.org/test#example2"
                    },
                    "http://example.org/test#property2": "http://example.org/test#example3",
                    "http://example.org/test#property3": {
                        "uri": "http://example.org/test#example4"
                    },
                    "uri": "http://example.org/test#example1"
                },
                "algorithm": "expand",
                "base": "http://json-ld.org/test-suite/tests/expand-0006-in.jsonld"
            },
            "expected_output": "[ {\n  \"http://example.org/test#property1\" : [ {\n    \"http://example.org/test#property4\" : [ {\n      \"@value\" : \"foo\"\n    } ],\n    \"@id\" : \"http://example.org/test#example2\"\n  } ],\n  \"http://example.org/test#property2\" : [ {\n    \"@id\" : \"http://example.org/test#example3\"\n  } ],\n  \"http://example.org/test#property3\" : [ {\n    \"@id\" : \"http://example.org/test#example4\"\n  } ],\n  \"@id\" : \"http://example.org/test#example1\"\n} ]\n"
        }
    ]
}
```

---

### Feature 2: JSON-LD Compaction

**As a developer**, I want to compact expanded JSON-LD using a supplied context, so I can publish concise documents while preserving graph meaning.

**Expected Behavior / Usage:**

The input is a JSON command whose operation is compaction, with an expanded JSON-LD document, a target context, and optional compaction options. The output is pretty-printed compacted JSON-LD on stdout. Compaction MUST shorten IRIs using the provided context, compact types and identifiers where valid, preserve native scalar values, and render the context in the resulting document according to JSON-LD compaction rules.

**Test Cases:** `rcb_tests/public_test_cases/feature2_compact.json`

```json
{
    "description": "Compact expanded JSON-LD using a supplied context so IRIs, types, native values, and context declarations are rendered in their shortest valid JSON-LD form.",
    "cases": [
        {
            "input": {
                "options": {},
                "document": [
                    {
                        "@id": "http://example.com/id1",
                        "@type": [
                            "http://example.com/t1"
                        ],
                        "http://example.com/term1": [
                            "v1"
                        ],
                        "http://example.com/term2": [
                            {
                                "@value": "v2",
                                "@type": "http://example.com/t2"
                            }
                        ],
                        "http://example.com/term3": [
                            {
                                "@value": "v3",
                                "@language": "en"
                            }
                        ],
                        "http://example.com/term4": [
                            4
                        ],
                        "http://example.com/term5": [
                            50,
                            51
                        ]
                    }
                ],
                "algorithm": "compact",
                "context": {
                    "@context": {
                        "t1": "http://example.com/t1",
                        "t2": "http://example.com/t2",
                        "term1": "http://example.com/term1",
                        "term2": "http://example.com/term2",
                        "term3": "http://example.com/term3",
                        "term4": "http://example.com/term4",
                        "term5": "http://example.com/term5"
                    }
                },
                "base": "http://json-ld.org/test-suite/tests/compact-0002-in.jsonld"
            },
            "expected_output": "{\n  \"@id\" : \"http://example.com/id1\",\n  \"@type\" : \"t1\",\n  \"term1\" : \"v1\",\n  \"term2\" : {\n    \"@type\" : \"t2\",\n    \"@value\" : \"v2\"\n  },\n  \"term3\" : {\n    \"@language\" : \"en\",\n    \"@value\" : \"v3\"\n  },\n  \"term4\" : 4,\n  \"term5\" : [ 50, 51 ],\n  \"@context\" : {\n    \"t1\" : \"http://example.com/t1\",\n    \"t2\" : \"http://example.com/t2\",\n    \"term1\" : \"http://example.com/term1\",\n    \"term2\" : \"http://example.com/term2\",\n    \"term3\" : \"http://example.com/term3\",\n    \"term4\" : \"http://example.com/term4\",\n    \"term5\" : \"http://example.com/term5\"\n  }\n}\n"
        },
        {
            "input": {
                "options": {},
                "document": {
                    "@id": "http://example.org/id1",
                    "@type": [
                        "http://example.org/Type1",
                        "http://example.org/Type2"
                    ],
                    "http://example.org/term1": {
                        "@value": "v1",
                        "@type": "http://example.org/datatype"
                    },
                    "http://example.org/term2": {
                        "@id": "http://example.org/id2"
                    }
                },
                "algorithm": "compact",
                "context": {
                    "@context": {
                        "ex": "http://example.org/",
                        "term1": {
                            "@id": "ex:term1",
                            "@type": "ex:datatype"
                        },
                        "term2": {
                            "@id": "ex:term2",
                            "@type": "@id"
                        }
                    }
                },
                "base": "http://json-ld.org/test-suite/tests/compact-0005-in.jsonld"
            },
            "expected_output": "{\n  \"@id\" : \"ex:id1\",\n  \"@type\" : [ \"ex:Type1\", \"ex:Type2\" ],\n  \"term1\" : \"v1\",\n  \"term2\" : \"ex:id2\",\n  \"@context\" : {\n    \"ex\" : \"http://example.org/\",\n    \"term1\" : {\n      \"@id\" : \"ex:term1\",\n      \"@type\" : \"ex:datatype\"\n    },\n    \"term2\" : {\n      \"@id\" : \"ex:term2\",\n      \"@type\" : \"@id\"\n    }\n  }\n}\n"
        }
    ]
}
```

---

### Feature 3: JSON-LD Flattening

**As a developer**, I want to flatten JSON-LD into a deterministic node list, so I can compare and traverse graph data without nested embedding differences.

**Expected Behavior / Usage:**

The input is a JSON command whose operation is flattening, with a JSON-LD document and optional processing options. The output is pretty-printed flattened JSON-LD on stdout. Flattening MUST expand and collect graph nodes into a stable top-level node list while preserving identifiers, types, native values, graph membership, and embedded graph information.

**Test Cases:** `rcb_tests/public_test_cases/feature3_flatten.json`

```json
{
    "description": "Flatten JSON-LD into a deterministic node list that preserves graph membership, native values, and embedded graph data after expansion.",
    "cases": [
        {
            "input": {
                "options": {},
                "document": {
                    "@context": {
                        "t1": "http://example.com/t1",
                        "t2": "http://example.com/t2",
                        "term1": "http://example.com/term1",
                        "term2": "http://example.com/term2",
                        "term3": "http://example.com/term3",
                        "term4": "http://example.com/term4",
                        "term5": "http://example.com/term5"
                    },
                    "@id": "http://example.com/id1",
                    "@type": "t1",
                    "term1": "v1",
                    "term2": {
                        "@value": "v2",
                        "@type": "t2"
                    },
                    "term3": {
                        "@value": "v3",
                        "@language": "en"
                    },
                    "term4": 4,
                    "term5": [
                        50,
                        51
                    ]
                },
                "algorithm": "flatten",
                "base": "http://json-ld.org/test-suite/tests/flatten-0002-in.jsonld"
            },
            "expected_output": "[ {\n  \"@id\" : \"http://example.com/id1\",\n  \"@type\" : [ \"http://example.com/t1\" ],\n  \"http://example.com/term1\" : [ {\n    \"@value\" : \"v1\"\n  } ],\n  \"http://example.com/term2\" : [ {\n    \"@type\" : \"http://example.com/t2\",\n    \"@value\" : \"v2\"\n  } ],\n  \"http://example.com/term3\" : [ {\n    \"@language\" : \"en\",\n    \"@value\" : \"v3\"\n  } ],\n  \"http://example.com/term4\" : [ {\n    \"@value\" : 4\n  } ],\n  \"http://example.com/term5\" : [ {\n    \"@value\" : 50\n  }, {\n    \"@value\" : 51\n  } ]\n} ]\n"
        },
        {
            "input": {
                "options": {},
                "document": {
                    "@context": {
                        "d": "http://purl.org/dc/elements/1.1/",
                        "e": "http://example.org/vocab#",
                        "f": "http://xmlns.com/foaf/0.1/",
                        "xsd": "http://www.w3.org/2001/XMLSchema#"
                    },
                    "@id": "http://example.org/test",
                    "e:bool": true,
                    "e:int": 123
                },
                "algorithm": "flatten",
                "base": "http://json-ld.org/test-suite/tests/flatten-0010-in.jsonld"
            },
            "expected_output": "[ {\n  \"@id\" : \"http://example.org/test\",\n  \"http://example.org/vocab#bool\" : [ {\n    \"@value\" : true\n  } ],\n  \"http://example.org/vocab#int\" : [ {\n    \"@value\" : 123\n  } ]\n} ]\n"
        }
    ]
}
```

---

### Feature 4: JSON-LD Framing

**As a developer**, I want to frame JSON-LD data with a graph-shaped template, so I can receive documents organized around the nodes and relationships my application needs.

**Expected Behavior / Usage:**

The input is a JSON command whose operation is framing, with a JSON-LD document, a frame document, and optional framing options. The output is pretty-printed framed JSON-LD on stdout. Framing MUST select nodes that match the frame, embed or reference related nodes according to the frame, preserve declared contexts, and honor processing options that affect array compaction or embedding behavior.

**Test Cases:** `rcb_tests/public_test_cases/feature4_frame.json`

```json
{
    "description": "Frame JSON-LD by selecting graph nodes that match a frame and embedding or referencing related nodes according to the frame and processing options.",
    "cases": [
        {
            "input": {
                "options": {},
                "document": {
                    "@context": {
                        "dc": "http://purl.org/dc/elements/1.1/",
                        "ex": "http://example.org/vocab#",
                        "ex:contains": {
                            "@type": "@id"
                        }
                    },
                    "@graph": [
                        {
                            "@id": "http://example.org/test/#library",
                            "@type": "ex:Library",
                            "ex:contains": "http://example.org/test#book"
                        },
                        {
                            "@id": "http://example.org/test#book",
                            "@type": "ex:Book",
                            "dc:contributor": "Writer",
                            "dc:title": "My Book",
                            "ex:contains": "http://example.org/test#chapter"
                        },
                        {
                            "@id": "http://example.org/test#chapter",
                            "@type": "ex:Chapter",
                            "dc:description": "Fun",
                            "dc:title": "Chapter One"
                        }
                    ]
                },
                "algorithm": "frame",
                "frame": {
                    "@context": {
                        "dc": "http://purl.org/dc/elements/1.1/",
                        "ex": "http://example.org/vocab#"
                    },
                    "@type": "ex:Library",
                    "ex:contains": {
                        "@type": "ex:Book",
                        "ex:contains": {
                            "@type": "ex:Chapter"
                        }
                    }
                },
                "base": "http://json-ld.org/test-suite/tests/frame-0001-in.jsonld"
            },
            "expected_output": "{\n  \"@context\" : {\n    \"dc\" : \"http://purl.org/dc/elements/1.1/\",\n    \"ex\" : \"http://example.org/vocab#\"\n  },\n  \"@graph\" : [ {\n    \"@id\" : \"http://example.org/test/#library\",\n    \"@type\" : \"ex:Library\",\n    \"ex:contains\" : {\n      \"@id\" : \"http://example.org/test#book\",\n      \"@type\" : \"ex:Book\",\n      \"ex:contains\" : {\n        \"@id\" : \"http://example.org/test#chapter\",\n        \"@type\" : \"ex:Chapter\",\n        \"dc:description\" : \"Fun\",\n        \"dc:title\" : \"Chapter One\"\n      },\n      \"dc:contributor\" : \"Writer\",\n      \"dc:title\" : \"My Book\"\n    }\n  } ]\n}\n"
        },
        {
            "input": {
                "options": {},
                "document": {
                    "@context": {
                        "dc": "http://purl.org/dc/elements/1.1/",
                        "ex": "http://example.org/vocab#",
                        "ex:contains": {
                            "@type": "@id"
                        }
                    },
                    "@graph": [
                        {
                            "@id": "http://example.org/test/#library",
                            "@type": "ex:Library",
                            "ex:contains": "http://example.org/test#book"
                        },
                        {
                            "@id": "http://example.org/test#book",
                            "@type": "ex:Book",
                            "dc:contributor": "Writer",
                            "dc:title": "My Book",
                            "ex:contains": "http://example.org/test#chapter"
                        },
                        {
                            "@id": "http://example.org/test#chapter",
                            "@type": "ex:Chapter",
                            "dc:description": "Fun",
                            "dc:title": "Chapter One",
                            "ex:act": "ex:ActOne"
                        }
                    ]
                },
                "algorithm": "frame",
                "frame": {
                    "@context": {
                        "dc": "http://purl.org/dc/elements/1.1/",
                        "ex": "http://example.org/vocab#"
                    },
                    "@type": "ex:Library",
                    "ex:contains": {
                        "@type": "ex:Book",
                        "ex:contains": {
                            "@type": "ex:Chapter"
                        }
                    }
                },
                "base": "http://json-ld.org/test-suite/tests/frame-0002-in.jsonld"
            },
            "expected_output": "{\n  \"@context\" : {\n    \"dc\" : \"http://purl.org/dc/elements/1.1/\",\n    \"ex\" : \"http://example.org/vocab#\"\n  },\n  \"@graph\" : [ {\n    \"@id\" : \"http://example.org/test/#library\",\n    \"@type\" : \"ex:Library\",\n    \"ex:contains\" : {\n      \"@id\" : \"http://example.org/test#book\",\n      \"@type\" : \"ex:Book\",\n      \"ex:contains\" : {\n        \"@id\" : \"http://example.org/test#chapter\",\n        \"@type\" : \"ex:Chapter\",\n        \"ex:act\" : \"ex:ActOne\",\n        \"dc:description\" : \"Fun\",\n        \"dc:title\" : \"Chapter One\"\n      },\n      \"dc:contributor\" : \"Writer\",\n      \"dc:title\" : \"My Book\"\n    }\n  } ]\n}\n"
        }
    ]
}
```

---

### Feature 5: JSON-LD to RDF Conversion

**As a developer**, I want to convert JSON-LD into RDF statements, so I can interoperate with RDF tooling and graph stores.

**Expected Behavior / Usage:**

The input is a JSON command whose operation is conversion to RDF, with a JSON-LD document and optional processing options. The output is either canonical N-Quads text or a small line-oriented report for specialized RDF dataset observations. The conversion MUST produce RDF statements for IRIs, literals, language-tagged strings, RDF type relationships, RDF lists, typed literals, and decimal values while preserving the lexical value required by the input.

**Test Cases:** `rcb_tests/public_test_cases/feature5_to_rdf.json`

```json
{
    "description": "Convert JSON-LD documents into RDF statements, including literal language tags, RDF type triples, RDF lists, typed literals, and decimal lexical values.",
    "cases": [
        {
            "input": {
                "options": {},
                "document": {
                    "@id": "http://greggkellogg.net/foaf#me",
                    "http://xmlns.com/foaf/0.1/name": "Gregg Kellogg"
                },
                "algorithm": "to_rdf",
                "base": "http://json-ld.org/test-suite/tests/toRdf-0001-in.jsonld"
            },
            "expected_output": "<http://greggkellogg.net/foaf#me> <http://xmlns.com/foaf/0.1/name> \"Gregg Kellogg\" .\n"
        },
        {
            "input": {
                "options": {},
                "document": {
                    "http://www.w3.org/2000/01/rdf-schema#label": {
                        "@value": "A plain literal with a lang tag.",
                        "@language": "en-us"
                    }
                },
                "algorithm": "to_rdf",
                "base": "http://json-ld.org/test-suite/tests/toRdf-0004-in.jsonld"
            },
            "expected_output": "_:b0 <http://www.w3.org/2000/01/rdf-schema#label> \"A plain literal with a lang tag.\"@en-us .\n"
        }
    ]
}
```

---

### Feature 6: RDF to JSON-LD Conversion

**As a developer**, I want to convert N-Quads RDF into JSON-LD, so I can consume RDF datasets through JSON-oriented APIs.

**Expected Behavior / Usage:**

The input is a JSON command whose operation is conversion from RDF, with N-Quads text and optional conversion options. The output is pretty-printed expanded JSON-LD on stdout. The conversion MUST group triples by subject, preserve named graph data, reconstruct RDF lists where possible, represent blank nodes and IRI references correctly, and honor options that map native typed values or RDF type predicates.

**Test Cases:** `rcb_tests/public_test_cases/feature6_from_rdf.json`

```json
{
    "description": "Convert N-Quads RDF input into expanded JSON-LD while reconstructing lists, blank-node structures, named graphs, native values, and RDF type handling.",
    "cases": [
        {
            "input": {
                "options": {},
                "nquads": "<http://example.com/Subj1> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://example.com/Type> .\n<http://example.com/Subj1> <http://example.com/prop1> <http://example.com/Obj1> .\n<http://example.com/Subj1> <http://example.com/prop2> \"Plain\" .\n<http://example.com/Subj1> <http://example.com/prop2> \"2012-05-12\"^^<http://www.w3.org/2001/XMLSchema#date> .\n<http://example.com/Subj1> <http://example.com/prop2> \"English\"@en .",
                "algorithm": "from_rdf"
            },
            "expected_output": "[ {\n  \"@id\" : \"http://example.com/Subj1\",\n  \"@type\" : [ \"http://example.com/Type\" ],\n  \"http://example.com/prop1\" : [ {\n    \"@id\" : \"http://example.com/Obj1\"\n  } ],\n  \"http://example.com/prop2\" : [ {\n    \"@value\" : \"Plain\"\n  }, {\n    \"@value\" : \"2012-05-12\",\n    \"@type\" : \"http://www.w3.org/2001/XMLSchema#date\"\n  }, {\n    \"@value\" : \"English\",\n    \"@language\" : \"en\"\n  } ]\n} ]\n"
        },
        {
            "input": {
                "options": {},
                "nquads": "<http://example.com/Subj1> <http://example.com/prop> \"true\"^^<http://www.w3.org/2001/XMLSchema#boolean> .\n<http://example.com/Subj1> <http://example.com/prop> \"false\"^^<http://www.w3.org/2001/XMLSchema#boolean> .\n<http://example.com/Subj1> <http://example.com/prop> \"1\"^^<http://www.w3.org/2001/XMLSchema#integer> .\n<http://example.com/Subj1> <http://example.com/prop> \"1.1\"^^<http://www.w3.org/2001/XMLSchema#decimal> .\n<http://example.com/Subj1> <http://example.com/prop> \"1.1E-1\"^^<http://www.w3.org/2001/XMLSchema#double> .",
                "algorithm": "from_rdf"
            },
            "expected_output": "[ {\n  \"@id\" : \"http://example.com/Subj1\",\n  \"http://example.com/prop\" : [ {\n    \"@value\" : \"true\",\n    \"@type\" : \"http://www.w3.org/2001/XMLSchema#boolean\"\n  }, {\n    \"@value\" : \"false\",\n    \"@type\" : \"http://www.w3.org/2001/XMLSchema#boolean\"\n  }, {\n    \"@value\" : \"1\",\n    \"@type\" : \"http://www.w3.org/2001/XMLSchema#integer\"\n  }, {\n    \"@value\" : \"1.1\",\n    \"@type\" : \"http://www.w3.org/2001/XMLSchema#decimal\"\n  }, {\n    \"@value\" : \"1.1E-1\",\n    \"@type\" : \"http://www.w3.org/2001/XMLSchema#double\"\n  } ]\n} ]\n"
        }
    ]
}
```

---

### Feature 7: RDF Dataset Normalization

**As a developer**, I want to normalize JSON-LD into canonical N-Quads, so I can compare equivalent RDF datasets reliably.

**Expected Behavior / Usage:**

The input is a JSON command whose operation is normalization, with a JSON-LD document and optional processing options. The output is canonical N-Quads text on stdout. Normalization MUST produce stable blank node identifiers and deterministic statement ordering for equivalent graph data; documents that contain no RDF statements produce an empty N-Quads payload followed by the adapter newline.

**Test Cases:** `rcb_tests/public_test_cases/feature7_normalize.json`

```json
{
    "description": "Normalize JSON-LD into canonical N-Quads so blank node identifiers and statement ordering are stable for equivalent RDF datasets.",
    "cases": [
        {
            "input": {
                "options": {},
                "document": {
                    "@id": "http://example.org/test#example"
                },
                "algorithm": "normalize",
                "base": "http://json-ld.org/test-suite/tests/normalize-0001-in.jsonld"
            },
            "expected_output": "\n"
        },
        {
            "input": {
                "options": {},
                "document": {
                    "@context": {
                        "ex": "http://example.org/vocab#"
                    },
                    "@type": "ex:Foo"
                },
                "algorithm": "normalize",
                "base": "http://json-ld.org/test-suite/tests/normalize-0003-in.jsonld"
            },
            "expected_output": "_:c14n0 <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://example.org/vocab#Foo> .\n"
        }
    ]
}
```

---

### Feature 8: Namespace Prefix Preservation

**As a developer**, I want namespace prefixes to be preserved and applied during RDF conversion, so compact names remain useful when moving between JSON-LD and RDF forms.

**Expected Behavior / Usage:**

The input is a JSON command that either converts JSON-LD to RDF with namespace reporting enabled or performs an RDF round trip with declared namespace prefixes. The output is line-oriented stdout where each namespace line has the form `namespace.<prefix>=<iri>` and marker checks have the form `contains.<text>=<true-or-false>`. The system MUST keep valid prefixes, keep longer nested namespace prefixes when they are meaningful, and choose compact names that shorten IRIs without dropping the namespace map.

**Test Cases:** `rcb_tests/public_test_cases/feature8_namespaces.json`

```json
{
    "description": "Preserve valid namespace prefixes during RDF conversion and choose compact names that shorten IRIs without losing prefix mappings.",
    "cases": [
        {
            "input": {
                "algorithm": "to_rdf",
                "document": {
                    "@context": {
                        "aat": "http://vocab.getty.edu/aat/",
                        "aat_rev": "http://vocab.getty.edu/aat/rev/"
                    },
                    "@id": "aat_rev:5001065997",
                    "@type": "aat_rev:datatype",
                    "used": "aat:300016954"
                },
                "namespaces": true,
                "options": {
                    "useNamespaces": true
                }
            },
            "expected_output": "namespace.aat=http://vocab.getty.edu/aat/\nnamespace.aat_rev=http://vocab.getty.edu/aat/rev/\n"
        },
        {
            "input": {
                "algorithm": "roundtrip_namespaces",
                "namespaces": {
                    "aat": "http://vocab.getty.edu/aat/",
                    "aat_rev": "http://vocab.getty.edu/aat/rev/"
                },
                "triples": [
                    {
                        "subject": "http://vocab.getty.edu/aat/rev/5001065997",
                        "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                        "object": "http://vocab.getty.edu/aat/datatype",
                        "objectKind": "iri"
                    }
                ],
                "contains": [
                    "aat:rev/"
                ],
                "options": {
                    "useNamespaces": true
                }
            },
            "expected_output": "namespace.aat=http://vocab.getty.edu/aat/\nnamespace.aat_rev=http://vocab.getty.edu/aat/rev/\ncontains.aat:rev/=true\n"
        }
    ]
}
```

---

### Feature 9: Normalized Error Reporting

**As a developer**, I want invalid JSON-LD inputs to produce stable language-neutral error categories, so tests and clients do not depend on runtime exception names or host-language messages.

**Expected Behavior / Usage:**

The input is a JSON command whose requested JSON-LD operation receives an invalid context or invalid IRI-valued data. The output is line-oriented stdout with `error=<normalized_category>`. The adapter MUST translate implementation exceptions into domain categories such as keyword redefinition, loading remote context failure, invalid vocabulary mapping, invalid type mapping, or invalid IRI value, and MUST NOT print language runtime exception class names, stack traces, or automatically generated parameter-message suffixes.

**Test Cases:** `rcb_tests/public_test_cases/feature9_errors.json`

```json
{
    "description": "Report invalid JSON-LD contexts and invalid IRI values as normalized language-neutral error categories instead of runtime exception details.",
    "cases": [
        {
            "input": {
                "options": {},
                "document": {
                    "@context": {
                        "@type": "@id"
                    },
                    "@type": "http://example.org/type"
                },
                "algorithm": "flatten",
                "base": "http://json-ld.org/test-suite/tests/error-0001-in.jsonld"
            },
            "expected_output": "[error category codes from validation schema]\n"
        },
        {
            "input": {
                "options": {},
                "document": {
                    "@context": "tag:non-dereferencable-iri",
                    "@id": "http://example/test#example"
                },
                "algorithm": "flatten",
                "base": "http://json-ld.org/test-suite/tests/error-0004-in.jsonld"
            },
            "expected_output": "[error category codes from validation schema]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_expand.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_expand@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the dotted triple format defined in the text conversion module
