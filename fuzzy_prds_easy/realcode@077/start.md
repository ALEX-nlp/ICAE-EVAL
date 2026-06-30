## Product Requirement Document

# Resource and Tool Catalog Runtime - Dynamic Content and Callable Operation Contracts

## Project Goal

Build a resource and tool catalog runtime that allows developers to register static content, dynamic URI-template content, and callable operations with machine-readable schemas without hand-writing repetitive catalog, pagination, lookup, and validation plumbing.

---

## Background & Problem

Without this library/tool, developers are forced to manually maintain resource lists, match templated URIs, implement cursor pagination, describe tool inputs, validate nested arguments, and normalize invocation failures. This leads to repetitive code, inconsistent error handling, and clients that cannot reliably discover or call available capabilities.

With this library/tool, developers provide resource and tool definitions once, and clients can list, page, read, and call them through predictable JSON-shaped envelopes and language-neutral error outputs.

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

### Feature 1: Static Resource Listing

**As a developer**, I want to register static content entries with metadata, so I can discover available entries without reading each one.

**Expected Behavior / Usage:**

A request contains setup data with one or more static resource entries, followed by a list request for the resource catalog. The output is formatted JSON containing a resources array in registration order. Each entry includes the resource URI, display name, description, and MIME type; if no MIME type is supplied, the default text MIME type is returned. No pagination cursor is included when the complete set is returned.

**Test Cases:** `rcb_tests/public_test_cases/feature1_static_resource_listing.json`

```json
{
    "description": "Registered static resources are listed with their URI, display name, description, and default MIME type.",
    "cases": [
        {
            "input": {
                "setup": {
                    "resources": [
                        {
                            "[a generic error code and attribute key]": "/test",
                            "name": "test_resource",
                            "description": "A test resource",
                            "text": "test content"
                        }
                    ]
                },
                "request": {
                    "target": "resources",
                    "action": "list"
                }
            },
            "expected_output": "{\n  \"resources\": [\n    {\n      \"[a generic error code and attribute key]\": \"/test\",\n      \"name\": \"test_resource\",\n      \"description\": \"A test resource\",\n      \"mimeType\": \"text/plain\"\n    }\n  ]\n}\n"
        }
    ]
}
```

---

### Feature 2: Static Resource Pagination

**As a developer**, I want to page through static content entries, so I can present large catalogs incrementally.

**Expected Behavior / Usage:**

A request contains multiple static resource entries and asks for the resource catalog, optionally with page_size and cursor. The cursor is a decimal string offset into the registration-ordered catalog. Without page_size, all resources from the cursor are returned and no nextCursor appears. With page_size, at most that many resources are returned; nextCursor is emitted only when another page exists.

**Test Cases:** `rcb_tests/public_test_cases/feature2_static_resource_pagination.json`

```json
{
    "description": "Static resources preserve registration order and support cursor-based pagination.",
    "cases": [
        {
            "input": {
                "setup": {
                    "resources": [
                        {
                            "[a generic error code and attribute key]": "/test0",
                            "name": "resource0",
                            "description": "",
                            "text": "content0"
                        },
                        {
                            "[a generic error code and attribute key]": "/test1",
                            "name": "resource1",
                            "description": "",
                            "text": "content1"
                        },
                        {
                            "[a generic error code and attribute key]": "/test2",
                            "name": "resource2",
                            "description": "",
                            "text": "content2"
                        },
                        {
                            "[a generic error code and attribute key]": "/test3",
                            "name": "resource3",
                            "description": "",
                            "text": "content3"
                        },
                        {
                            "[a generic error code and attribute key]": "/test4",
                            "name": "resource4",
                            "description": "",
                            "text": "content4"
                        },
                        {
                            "[a generic error code and attribute key]": "/test5",
                            "name": "resource5",
                            "description": "",
                            "text": "content5"
                        },
                        {
                            "[a generic error code and attribute key]": "/test6",
                            "name": "resource6",
                            "description": "",
                            "text": "content6"
                        },
                        {
                            "[a generic error code and attribute key]": "/test7",
                            "name": "resource7",
                            "description": "",
                            "text": "content7"
                        },
                        {
                            "[a generic error code and attribute key]": "/test8",
                            "name": "resource8",
                            "description": "",
                            "text": "content8"
                        },
                        {
                            "[a generic error code and attribute key]": "/test9",
                            "name": "resource9",
                            "description": "",
                            "text": "content9"
                        }
                    ]
                },
                "request": {
                    "target": "resources",
                    "action": "list"
                }
            },
            "expected_output": "{\n  \"resources\": [\n    {\n      \"[a generic error code and attribute key]\": \"/test0\",\n      \"name\": \"resource0\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]\": \"/test1\",\n      \"name\": \"resource1\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]\": \"/test2\",\n      \"name\": \"resource2\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]\": \"/test3\",\n      \"name\": \"resource3\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]\": \"/test4\",\n      \"name\": \"resource4\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]\": \"/test5\",\n      \"name\": \"resource5\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]\": \"/test6\",\n      \"name\": \"resource6\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]\": \"/test7\",\n      \"name\": \"resource7\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]\": \"/test8\",\n      \"name\": \"resource8\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]\": \"/test9\",\n      \"name\": \"resource9\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "setup": {
                    "resources": [
                        {
                            "[a generic error code and attribute key]": "/test0",
                            "name": "resource0",
                            "description": "",
                            "text": "content0"
                        },
                        {
                            "[a generic error code and attribute key]": "/test1",
                            "name": "resource1",
                            "description": "",
                            "text": "content1"
                        },
                        {
                            "[a generic error code and attribute key]": "/test2",
                            "name": "resource2",
                            "description": "",
                            "text": "content2"
                        },
                        {
                            "[a generic error code and attribute key]": "/test3",
                            "name": "resource3",
                            "description": "",
                            "text": "content3"
                        },
                        {
                            "[a generic error code and attribute key]": "/test4",
                            "name": "resource4",
                            "description": "",
                            "text": "content4"
                        },
                        {
                            "[a generic error code and attribute key]": "/test5",
                            "name": "resource5",
                            "description": "",
                            "text": "content5"
                        },
                        {
                            "[a generic error code and attribute key]": "/test6",
                            "name": "resource6",
                            "description": "",
                            "text": "content6"
                        },
                        {
                            "[a generic error code and attribute key]": "/test7",
                            "name": "resource7",
                            "description": "",
                            "text": "content7"
                        },
                        {
                            "[a generic error code and attribute key]": "/test8",
                            "name": "resource8",
                            "description": "",
                            "text": "content8"
                        },
                        {
                            "[a generic error code and attribute key]": "/test9",
                            "name": "resource9",
                            "description": "",
                            "text": "content9"
                        }
                    ]
                },
                "request": {
                    "target": "resources",
                    "action": "list",
                    "page_size": 5
                }
            },
            "expected_output": "{\n  \"resources\": [\n    {\n      \"[a generic error code and attribute key]\": \"/test0\",\n      \"name\": \"resource0\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]\": \"/test1\",\n      \"name\": \"resource1\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]\": \"/test2\",\n      \"name\": \"resource2\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]\": \"/test3\",\n      \"name\": \"resource3\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]\": \"/test4\",\n      \"name\": \"resource4\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    }\n  ],\n  \"nextCursor\": \"5\"\n}\n"
        },
        {
            "input": {
                "setup": {
                    "resources": [
                        {
                            "[a generic error code and attribute key]": "/test0",
                            "name": "resource0",
                            "description": "",
                            "text": "content0"
                        },
                        {
                            "[a generic error code and attribute key]": "/test1",
                            "name": "resource1",
                            "description": "",
                            "text": "content1"
                        },
                        {
                            "[a generic error code and attribute key]": "/test2",
                            "name": "resource2",
                            "description": "",
                            "text": "content2"
                        },
                        {
                            "[a generic error code and attribute key]": "/test3",
                            "name": "resource3",
                            "description": "",
                            "text": "content3"
                        },
                        {
                            "[a generic error code and attribute key]": "/test4",
                            "name": "resource4",
                            "description": "",
                            "text": "content4"
                        },
                        {
                            "[a generic error code and attribute key]": "/test5",
                            "name": "resource5",
                            "description": "",
                            "text": "content5"
                        },
                        {
                            "[a generic error code and attribute key]": "/test6",
                            "name": "resource6",
                            "description": "",
                            "text": "content6"
                        },
                        {
                            "[a generic error code and attribute key]": "/test7",
                            "name": "resource7",
                            "description": "",
                            "text": "content7"
                        },
                        {
                            "[a generic error code and attribute key]": "/test8",
                            "name": "resource8",
                            "description": "",
                            "text": "content8"
                        },
                        {
                            "[a generic error code and attribute key]": "/test9",
                            "name": "resource9",
                            "description": "",
                            "text": "content9"
                        }
                    ]
                },
                "request": {
                    "target": "resources",
                    "action": "list",
                    "page_size": 5,
                    "cursor": "5"
                }
            },
            "expected_output": "{\n  \"resources\": [\n    {\n      \"[a generic error code and attribute key]\": \"/test5\",\n      \"name\": \"resource5\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]\": \"/test6\",\n      \"name\": \"resource6\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]\": \"/test7\",\n      \"name\": \"resource7\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]\": \"/test8\",\n      \"name\": \"resource8\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]\": \"/test9\",\n      \"name\": \"resource9\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    }\n  ]\n}\n"
        }
    ]
}
```

---

### Feature 3: Static Resource Reading

**As a developer**, I want to read a static content entry by URI, so I can retrieve the stored text payload and framework-visible envelope.

**Expected Behavior / Usage:**

A request contains registered static resources and a read request with a concrete URI. On success, the output is formatted JSON with a contents array whose first item includes the URI, MIME type, and text content. If no registered static resource or matching template exists for the URI, the output is a normalized error object with error=[a generic error code and attribute key] and the requested URI.

**Test Cases:** `rcb_tests/public_test_cases/feature3_static_resource_reading.json`

```json
{
    "description": "Reading a registered static resource returns the requested URI, MIME type, and text content; unknown URIs are reported neutrally.",
    "cases": [
        {
            "input": {
                "setup": {
                    "resources": [
                        {
                            "[a generic error code and attribute key]": "/test",
                            "name": "test_resource",
                            "description": "",
                            "text": "test content"
                        }
                    ]
                },
                "request": {
                    "target": "resources",
                    "action": "read",
                    "[a generic error code and attribute key]": "/test"
                }
            },
            "expected_output": "{\n  \"contents\": [\n    {\n      \"[a generic error code and attribute key]\": \"/test\",\n      \"mimeType\": \"text/plain\",\n      \"text\": \"test content\"\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "setup": {
                    "resources": [
                        {
                            "[a generic error code and attribute key]": "/test",
                            "name": "test_resource",
                            "description": "",
                            "text": "test content"
                        }
                    ]
                },
                "request": {
                    "target": "resources",
                    "action": "read",
                    "[a generic error code and attribute key]": "/non_existent"
                }
            },
            "expected_output": "{\n  \"error\": \"[a generic error code and attribute key]\",\n  \"[a generic error code and attribute key]\": \"/non_existent\"\n}\n"
        }
    ]
}
```

---

### Feature 4: Static Resource Definition Validation

**As a developer**, I want to receive clear errors for invalid static resource definitions, so I can reject unusable catalogs before serving requests.

**Expected Behavior / Usage:**

A request may attempt to build a catalog with malformed static resource definitions. Empty or null URIs are rejected as invalid_resource_[a generic error code and attribute key]. Hidden validation also covers resource definitions that cannot provide content or a display name. Errors are normalized JSON objects and do not expose host-language exception class names.

**Test Cases:** `rcb_tests/public_test_cases/feature4_static_resource_definition_validation.json`

```json
{
    "description": "Invalid static resource definitions are rejected with normalized error categories.",
    "cases": [
        {
            "input": {
                "setup": {
                    "resources": [
                        {
                            "[a generic error code and attribute key]": null,
                            "name": "bad",
                            "text": "x"
                        }
                    ]
                },
                "request": {
                    "target": "catalog",
                    "action": "build"
                }
            },
            "expected_output": "{\n  \"error\": \"invalid_resource_[a generic error code and attribute key]\"\n}\n"
        },
        {
            "input": {
                "setup": {
                    "resources": [
                        {
                            "[a generic error code and attribute key]": "",
                            "name": "bad",
                            "text": "x"
                        }
                    ]
                },
                "request": {
                    "target": "catalog",
                    "action": "build"
                }
            },
            "expected_output": "{\n  \"error\": \"invalid_resource_[a generic error code and attribute key]\"\n}\n"
        }
    ]
}
```

---

### Feature 5: Template Resource Reading

**As a developer**, I want to define URI-shaped resource templates, so I can serve dynamic content from concrete resource URIs.

**Expected Behavior / Usage:**

A request contains one or more resource templates. Template placeholders are path-segment variables enclosed in braces; each placeholder matches a non-slash segment in a concrete URI. Reading a concrete URI that matches a template returns a contents array with the concrete URI, MIME type, and rendered text based on extracted variable values. Non-matching URIs produce a normalized [a generic error code and attribute key] error.

**Test Cases:** `rcb_tests/public_test_cases/feature5_template_resource_reading.json`

```json
{
    "description": "Template resources match concrete URIs, extract path variables, and render content from those variables.",
    "cases": [
        {
            "input": {
                "setup": {
                    "resource_templates": [
                        {
                            "[a generic error code and attribute key]_template": "/test/{param_1}",
                            "name": "test_resource",
                            "description": "",
                            "text_format": "test content {param_1}",
                            "behavior": "render_template_values"
                        }
                    ]
                },
                "request": {
                    "target": "resources",
                    "action": "read",
                    "[a generic error code and attribute key]": "/test/value1"
                }
            },
            "expected_output": "{\n  \"contents\": [\n    {\n      \"[a generic error code and attribute key]\": \"/test/value1\",\n      \"mimeType\": \"text/plain\",\n      \"text\": \"test content value1\"\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "setup": {
                    "resource_templates": [
                        {
                            "[a generic error code and attribute key]_template": "/test/{param1}/{param2}",
                            "name": "test_template",
                            "description": "",
                            "text_format": "{param1}, {param2}",
                            "behavior": "render_template_values"
                        }
                    ]
                },
                "request": {
                    "target": "resources",
                    "action": "read",
                    "[a generic error code and attribute key]": "/test/value1/value2"
                }
            },
            "expected_output": "{\n  \"contents\": [\n    {\n      \"[a generic error code and attribute key]\": \"/test/value1/value2\",\n      \"mimeType\": \"text/plain\",\n      \"text\": \"value1, value2\"\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "setup": {
                    "resource_templates": [
                        {
                            "[a generic error code and attribute key]_template": "/test/{param_1}",
                            "name": "test_resource",
                            "description": "",
                            "text_format": "test content {param_1}",
                            "behavior": "render_template_values"
                        }
                    ]
                },
                "request": {
                    "target": "resources",
                    "action": "read",
                    "[a generic error code and attribute key]": "/non_existent"
                }
            },
            "expected_output": "{\n  \"error\": \"[a generic error code and attribute key]\",\n  \"[a generic error code and attribute key]\": \"/non_existent\"\n}\n"
        }
    ]
}
```

---

### Feature 6: Template Resource Listing

**As a developer**, I want to list registered URI templates with metadata, so I can advertise dynamic resource shapes to clients.

**Expected Behavior / Usage:**

A request contains registered resource templates and asks for the template catalog, optionally with page_size and cursor. The output is formatted JSON containing resourceTemplates in registration order. Each template entry includes the template URI string, display name, description, and MIME type. Pagination follows the same string-offset cursor behavior as static resources.

**Test Cases:** `rcb_tests/public_test_cases/feature6_template_resource_listing.json`

```json
{
    "description": "Registered resource templates are listed with template URI, display name, description, and MIME type, and support pagination.",
    "cases": [
        {
            "input": {
                "setup": {
                    "resource_templates": [
                        {
                            "[a generic error code and attribute key]_template": "/test/{param_1}",
                            "name": "test_resource template",
                            "description": "A test resource template",
                            "text_format": "test content {param_1}",
                            "behavior": "render_template_values"
                        }
                    ]
                },
                "request": {
                    "target": "resource_templates",
                    "action": "list"
                }
            },
            "expected_output": "{\n  \"resourceTemplates\": [\n    {\n      \"[a generic error code and attribute key]Template\": \"/test/{param_1}\",\n      \"name\": \"test_resource template\",\n      \"description\": \"A test resource template\",\n      \"mimeType\": \"text/plain\"\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "setup": {
                    "resource_templates": [
                        {
                            "[a generic error code and attribute key]_template": "/test0/{param_1}",
                            "name": "resource0",
                            "description": "",
                            "text_format": "content0 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test1/{param_1}",
                            "name": "resource1",
                            "description": "",
                            "text_format": "content1 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test2/{param_1}",
                            "name": "resource2",
                            "description": "",
                            "text_format": "content2 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test3/{param_1}",
                            "name": "resource3",
                            "description": "",
                            "text_format": "content3 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test4/{param_1}",
                            "name": "resource4",
                            "description": "",
                            "text_format": "content4 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test5/{param_1}",
                            "name": "resource5",
                            "description": "",
                            "text_format": "content5 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test6/{param_1}",
                            "name": "resource6",
                            "description": "",
                            "text_format": "content6 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test7/{param_1}",
                            "name": "resource7",
                            "description": "",
                            "text_format": "content7 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test8/{param_1}",
                            "name": "resource8",
                            "description": "",
                            "text_format": "content8 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test9/{param_1}",
                            "name": "resource9",
                            "description": "",
                            "text_format": "content9 {param_1}",
                            "behavior": "render_template_values"
                        }
                    ]
                },
                "request": {
                    "target": "resource_templates",
                    "action": "list"
                }
            },
            "expected_output": "{\n  \"resourceTemplates\": [\n    {\n      \"[a generic error code and attribute key]Template\": \"/test0/{param_1}\",\n      \"name\": \"resource0\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]Template\": \"/test1/{param_1}\",\n      \"name\": \"resource1\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]Template\": \"/test2/{param_1}\",\n      \"name\": \"resource2\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]Template\": \"/test3/{param_1}\",\n      \"name\": \"resource3\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]Template\": \"/test4/{param_1}\",\n      \"name\": \"resource4\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]Template\": \"/test5/{param_1}\",\n      \"name\": \"resource5\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]Template\": \"/test6/{param_1}\",\n      \"name\": \"resource6\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]Template\": \"/test7/{param_1}\",\n      \"name\": \"resource7\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]Template\": \"/test8/{param_1}\",\n      \"name\": \"resource8\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]Template\": \"/test9/{param_1}\",\n      \"name\": \"resource9\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "setup": {
                    "resource_templates": [
                        {
                            "[a generic error code and attribute key]_template": "/test0/{param_1}",
                            "name": "resource0",
                            "description": "",
                            "text_format": "content0 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test1/{param_1}",
                            "name": "resource1",
                            "description": "",
                            "text_format": "content1 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test2/{param_1}",
                            "name": "resource2",
                            "description": "",
                            "text_format": "content2 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test3/{param_1}",
                            "name": "resource3",
                            "description": "",
                            "text_format": "content3 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test4/{param_1}",
                            "name": "resource4",
                            "description": "",
                            "text_format": "content4 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test5/{param_1}",
                            "name": "resource5",
                            "description": "",
                            "text_format": "content5 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test6/{param_1}",
                            "name": "resource6",
                            "description": "",
                            "text_format": "content6 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test7/{param_1}",
                            "name": "resource7",
                            "description": "",
                            "text_format": "content7 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test8/{param_1}",
                            "name": "resource8",
                            "description": "",
                            "text_format": "content8 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test9/{param_1}",
                            "name": "resource9",
                            "description": "",
                            "text_format": "content9 {param_1}",
                            "behavior": "render_template_values"
                        }
                    ]
                },
                "request": {
                    "target": "resource_templates",
                    "action": "list",
                    "page_size": 5
                }
            },
            "expected_output": "{\n  \"resourceTemplates\": [\n    {\n      \"[a generic error code and attribute key]Template\": \"/test0/{param_1}\",\n      \"name\": \"resource0\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]Template\": \"/test1/{param_1}\",\n      \"name\": \"resource1\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]Template\": \"/test2/{param_1}\",\n      \"name\": \"resource2\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]Template\": \"/test3/{param_1}\",\n      \"name\": \"resource3\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]Template\": \"/test4/{param_1}\",\n      \"name\": \"resource4\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    }\n  ],\n  \"nextCursor\": \"5\"\n}\n"
        },
        {
            "input": {
                "setup": {
                    "resource_templates": [
                        {
                            "[a generic error code and attribute key]_template": "/test0/{param_1}",
                            "name": "resource0",
                            "description": "",
                            "text_format": "content0 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test1/{param_1}",
                            "name": "resource1",
                            "description": "",
                            "text_format": "content1 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test2/{param_1}",
                            "name": "resource2",
                            "description": "",
                            "text_format": "content2 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test3/{param_1}",
                            "name": "resource3",
                            "description": "",
                            "text_format": "content3 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test4/{param_1}",
                            "name": "resource4",
                            "description": "",
                            "text_format": "content4 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test5/{param_1}",
                            "name": "resource5",
                            "description": "",
                            "text_format": "content5 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test6/{param_1}",
                            "name": "resource6",
                            "description": "",
                            "text_format": "content6 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test7/{param_1}",
                            "name": "resource7",
                            "description": "",
                            "text_format": "content7 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test8/{param_1}",
                            "name": "resource8",
                            "description": "",
                            "text_format": "content8 {param_1}",
                            "behavior": "render_template_values"
                        },
                        {
                            "[a generic error code and attribute key]_template": "/test9/{param_1}",
                            "name": "resource9",
                            "description": "",
                            "text_format": "content9 {param_1}",
                            "behavior": "render_template_values"
                        }
                    ]
                },
                "request": {
                    "target": "resource_templates",
                    "action": "list",
                    "page_size": 5,
                    "cursor": "5"
                }
            },
            "expected_output": "{\n  \"resourceTemplates\": [\n    {\n      \"[a generic error code and attribute key]Template\": \"/test5/{param_1}\",\n      \"name\": \"resource5\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]Template\": \"/test6/{param_1}\",\n      \"name\": \"resource6\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]Template\": \"/test7/{param_1}\",\n      \"name\": \"resource7\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]Template\": \"/test8/{param_1}\",\n      \"name\": \"resource8\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    },\n    {\n      \"[a generic error code and attribute key]Template\": \"/test9/{param_1}\",\n      \"name\": \"resource9\",\n      \"description\": \"\",\n      \"mimeType\": \"text/plain\"\n    }\n  ]\n}\n"
        }
    ]
}
```

---

### Feature 7: Simple Tool Schema and Call

**As a developer**, I want to publish a callable operation with one required text input, so I can let clients inspect and invoke the operation consistently.

**Expected Behavior / Usage:**

A request can register a callable tool with a display description and a required string input. Listing tools returns a formatted JSON schema object with type=object, properties for the input, and required field names. Calling the tool with valid arguments returns a content array containing one text item and isError=false.

**Test Cases:** `rcb_tests/public_test_cases/feature7_simple_tool_schema_and_call.json`

```json
{
    "description": "A tool with one required text input exposes a JSON-compatible input schema and returns text content when called.",
    "cases": [
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": "greet",
                            "description": "Greet someone by name",
                            "arguments": [
                                {
                                    "name": "name",
                                    "required": true,
                                    "description": "Name to greet",
                                    "type": "string"
                                }
                            ],
                            "behavior": "greet_by_name"
                        }
                    ]
                },
                "request": {
                    "target": "tools",
                    "action": "list"
                }
            },
            "expected_output": "{\n  \"tools\": [\n    {\n      \"name\": \"greet\",\n      \"description\": \"Greet someone by name\",\n      \"inputSchema\": {\n        \"type\": \"object\",\n        \"properties\": {\n          \"name\": {\n            \"type\": \"string\",\n            \"description\": \"Name to greet\"\n          }\n        },\n        \"required\": [\n          \"name\"\n        ]\n      }\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": "greet",
                            "description": "Greet someone by name",
                            "arguments": [
                                {
                                    "name": "name",
                                    "required": true,
                                    "description": "Name to greet",
                                    "type": "string"
                                }
                            ],
                            "behavior": "greet_by_name"
                        }
                    ]
                },
                "request": {
                    "target": "tools",
                    "action": "call",
                    "name": "greet",
                    "arguments": {
                        "name": "World"
                    }
                }
            },
            "expected_output": "{\n  \"content\": [\n    {\n      \"type\": \"text\",\n      \"text\": \"Hello, World!\"\n    }\n  ],\n  \"isError\": false\n}\n"
        }
    ]
}
```

---

### Feature 8: Tool Pagination

**As a developer**, I want to page through registered callable operations, so I can present large tool catalogs incrementally.

**Expected Behavior / Usage:**

A request contains multiple registered tools and asks for a page of the tool catalog. Tool listing preserves registration order. The output includes at most page_size tools and emits nextCursor as a decimal string offset only when more tools remain; the next request can pass that cursor to continue listing.

**Test Cases:** `rcb_tests/public_test_cases/feature8_tool_pagination.json`

```json
{
    "description": "Tool listings preserve registration order and expose next cursors when a page has more entries.",
    "cases": [
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": "tool0",
                            "description": "Tool 0",
                            "arguments": [
                                {
                                    "name": "value",
                                    "required": true,
                                    "description": "Value for tool 0",
                                    "type": "string"
                                }
                            ],
                            "behavior": "indexed_echo",
                            "index": 0
                        },
                        {
                            "name": "tool1",
                            "description": "Tool 1",
                            "arguments": [
                                {
                                    "name": "value",
                                    "required": true,
                                    "description": "Value for tool 1",
                                    "type": "string"
                                }
                            ],
                            "behavior": "indexed_echo",
                            "index": 1
                        },
                        {
                            "name": "tool2",
                            "description": "Tool 2",
                            "arguments": [
                                {
                                    "name": "value",
                                    "required": true,
                                    "description": "Value for tool 2",
                                    "type": "string"
                                }
                            ],
                            "behavior": "indexed_echo",
                            "index": 2
                        },
                        {
                            "name": "tool3",
                            "description": "Tool 3",
                            "arguments": [
                                {
                                    "name": "value",
                                    "required": true,
                                    "description": "Value for tool 3",
                                    "type": "string"
                                }
                            ],
                            "behavior": "indexed_echo",
                            "index": 3
                        },
                        {
                            "name": "tool4",
                            "description": "Tool 4",
                            "arguments": [
                                {
                                    "name": "value",
                                    "required": true,
                                    "description": "Value for tool 4",
                                    "type": "string"
                                }
                            ],
                            "behavior": "indexed_echo",
                            "index": 4
                        },
                        {
                            "name": "tool5",
                            "description": "Tool 5",
                            "arguments": [
                                {
                                    "name": "value",
                                    "required": true,
                                    "description": "Value for tool 5",
                                    "type": "string"
                                }
                            ],
                            "behavior": "indexed_echo",
                            "index": 5
                        },
                        {
                            "name": "tool6",
                            "description": "Tool 6",
                            "arguments": [
                                {
                                    "name": "value",
                                    "required": true,
                                    "description": "Value for tool 6",
                                    "type": "string"
                                }
                            ],
                            "behavior": "indexed_echo",
                            "index": 6
                        },
                        {
                            "name": "tool7",
                            "description": "Tool 7",
                            "arguments": [
                                {
                                    "name": "value",
                                    "required": true,
                                    "description": "Value for tool 7",
                                    "type": "string"
                                }
                            ],
                            "behavior": "indexed_echo",
                            "index": 7
                        },
                        {
                            "name": "tool8",
                            "description": "Tool 8",
                            "arguments": [
                                {
                                    "name": "value",
                                    "required": true,
                                    "description": "Value for tool 8",
                                    "type": "string"
                                }
                            ],
                            "behavior": "indexed_echo",
                            "index": 8
                        },
                        {
                            "name": "tool9",
                            "description": "Tool 9",
                            "arguments": [
                                {
                                    "name": "value",
                                    "required": true,
                                    "description": "Value for tool 9",
                                    "type": "string"
                                }
                            ],
                            "behavior": "indexed_echo",
                            "index": 9
                        }
                    ]
                },
                "request": {
                    "target": "tools",
                    "action": "list",
                    "page_size": 5
                }
            },
            "expected_output": "{\n  \"tools\": [\n    {\n      \"name\": \"tool0\",\n      \"description\": \"Tool 0\",\n      \"inputSchema\": {\n        \"type\": \"object\",\n        \"properties\": {\n          \"value\": {\n            \"type\": \"string\",\n            \"description\": \"Value for tool 0\"\n          }\n        },\n        \"required\": [\n          \"value\"\n        ]\n      }\n    },\n    {\n      \"name\": \"tool1\",\n      \"description\": \"Tool 1\",\n      \"inputSchema\": {\n        \"type\": \"object\",\n        \"properties\": {\n          \"value\": {\n            \"type\": \"string\",\n            \"description\": \"Value for tool 1\"\n          }\n        },\n        \"required\": [\n          \"value\"\n        ]\n      }\n    },\n    {\n      \"name\": \"tool2\",\n      \"description\": \"Tool 2\",\n      \"inputSchema\": {\n        \"type\": \"object\",\n        \"properties\": {\n          \"value\": {\n            \"type\": \"string\",\n            \"description\": \"Value for tool 2\"\n          }\n        },\n        \"required\": [\n          \"value\"\n        ]\n      }\n    },\n    {\n      \"name\": \"tool3\",\n      \"description\": \"Tool 3\",\n      \"inputSchema\": {\n        \"type\": \"object\",\n        \"properties\": {\n          \"value\": {\n            \"type\": \"string\",\n            \"description\": \"Value for tool 3\"\n          }\n        },\n        \"required\": [\n          \"value\"\n        ]\n      }\n    },\n    {\n      \"name\": \"tool4\",\n      \"description\": \"Tool 4\",\n      \"inputSchema\": {\n        \"type\": \"object\",\n        \"properties\": {\n          \"value\": {\n            \"type\": \"string\",\n            \"description\": \"Value for tool 4\"\n          }\n        },\n        \"required\": [\n          \"value\"\n        ]\n      }\n    }\n  ],\n  \"nextCursor\": \"5\"\n}\n"
        },
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": "tool0",
                            "description": "Tool 0",
                            "arguments": [
                                {
                                    "name": "value",
                                    "required": true,
                                    "description": "Value for tool 0",
                                    "type": "string"
                                }
                            ],
                            "behavior": "indexed_echo",
                            "index": 0
                        },
                        {
                            "name": "tool1",
                            "description": "Tool 1",
                            "arguments": [
                                {
                                    "name": "value",
                                    "required": true,
                                    "description": "Value for tool 1",
                                    "type": "string"
                                }
                            ],
                            "behavior": "indexed_echo",
                            "index": 1
                        },
                        {
                            "name": "tool2",
                            "description": "Tool 2",
                            "arguments": [
                                {
                                    "name": "value",
                                    "required": true,
                                    "description": "Value for tool 2",
                                    "type": "string"
                                }
                            ],
                            "behavior": "indexed_echo",
                            "index": 2
                        },
                        {
                            "name": "tool3",
                            "description": "Tool 3",
                            "arguments": [
                                {
                                    "name": "value",
                                    "required": true,
                                    "description": "Value for tool 3",
                                    "type": "string"
                                }
                            ],
                            "behavior": "indexed_echo",
                            "index": 3
                        },
                        {
                            "name": "tool4",
                            "description": "Tool 4",
                            "arguments": [
                                {
                                    "name": "value",
                                    "required": true,
                                    "description": "Value for tool 4",
                                    "type": "string"
                                }
                            ],
                            "behavior": "indexed_echo",
                            "index": 4
                        },
                        {
                            "name": "tool5",
                            "description": "Tool 5",
                            "arguments": [
                                {
                                    "name": "value",
                                    "required": true,
                                    "description": "Value for tool 5",
                                    "type": "string"
                                }
                            ],
                            "behavior": "indexed_echo",
                            "index": 5
                        },
                        {
                            "name": "tool6",
                            "description": "Tool 6",
                            "arguments": [
                                {
                                    "name": "value",
                                    "required": true,
                                    "description": "Value for tool 6",
                                    "type": "string"
                                }
                            ],
                            "behavior": "indexed_echo",
                            "index": 6
                        },
                        {
                            "name": "tool7",
                            "description": "Tool 7",
                            "arguments": [
                                {
                                    "name": "value",
                                    "required": true,
                                    "description": "Value for tool 7",
                                    "type": "string"
                                }
                            ],
                            "behavior": "indexed_echo",
                            "index": 7
                        },
                        {
                            "name": "tool8",
                            "description": "Tool 8",
                            "arguments": [
                                {
                                    "name": "value",
                                    "required": true,
                                    "description": "Value for tool 8",
                                    "type": "string"
                                }
                            ],
                            "behavior": "indexed_echo",
                            "index": 8
                        },
                        {
                            "name": "tool9",
                            "description": "Tool 9",
                            "arguments": [
                                {
                                    "name": "value",
                                    "required": true,
                                    "description": "Value for tool 9",
                                    "type": "string"
                                }
                            ],
                            "behavior": "indexed_echo",
                            "index": 9
                        }
                    ]
                },
                "request": {
                    "target": "tools",
                    "action": "list",
                    "page_size": 5,
                    "cursor": "5"
                }
            },
            "expected_output": "{\n  \"tools\": [\n    {\n      \"name\": \"tool5\",\n      \"description\": \"Tool 5\",\n      \"inputSchema\": {\n        \"type\": \"object\",\n        \"properties\": {\n          \"value\": {\n            \"type\": \"string\",\n            \"description\": \"Value for tool 5\"\n          }\n        },\n        \"required\": [\n          \"value\"\n        ]\n      }\n    },\n    {\n      \"name\": \"tool6\",\n      \"description\": \"Tool 6\",\n      \"inputSchema\": {\n        \"type\": \"object\",\n        \"properties\": {\n          \"value\": {\n            \"type\": \"string\",\n            \"description\": \"Value for tool 6\"\n          }\n        },\n        \"required\": [\n          \"value\"\n        ]\n      }\n    },\n    {\n      \"name\": \"tool7\",\n      \"description\": \"Tool 7\",\n      \"inputSchema\": {\n        \"type\": \"object\",\n        \"properties\": {\n          \"value\": {\n            \"type\": \"string\",\n            \"description\": \"Value for tool 7\"\n          }\n        },\n        \"required\": [\n          \"value\"\n        ]\n      }\n    },\n    {\n      \"name\": \"tool8\",\n      \"description\": \"Tool 8\",\n      \"inputSchema\": {\n        \"type\": \"object\",\n        \"properties\": {\n          \"value\": {\n            \"type\": \"string\",\n            \"description\": \"Value for tool 8\"\n          }\n        },\n        \"required\": [\n          \"value\"\n        ]\n      }\n    },\n    {\n      \"name\": \"tool9\",\n      \"description\": \"Tool 9\",\n      \"inputSchema\": {\n        \"type\": \"object\",\n        \"properties\": {\n          \"value\": {\n            \"type\": \"string\",\n            \"description\": \"Value for tool 9\"\n          }\n        },\n        \"required\": [\n          \"value\"\n        ]\n      }\n    }\n  ]\n}\n"
        }
    ]
}
```

---

### Feature 9: Multi-Argument Tool Calls

**As a developer**, I want to declare tools with required and optional arguments, so I can validate invocation input while supporting optional data.

**Expected Behavior / Usage:**

A tool may define several string arguments. Required arguments appear in the schema required list; optional arguments appear in properties but not in required. Calls with all required fields return text content. Calls that omit a required argument return a normalized validation error with error=missing_required_parameter and a path field identifying the missing input.

**Test Cases:** `rcb_tests/public_test_cases/feature9_multi_argument_tool_calls.json`

```json
{
    "description": "Tools may declare multiple required and optional inputs; missing required inputs return normalized validation errors.",
    "cases": [
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": "format_greeting",
                            "description": "Format a greeting with title and name",
                            "arguments": [
                                {
                                    "name": "title",
                                    "required": true,
                                    "description": "Title (Mr./Ms./Dr. etc.)",
                                    "type": "string"
                                },
                                {
                                    "name": "first_name",
                                    "required": true,
                                    "description": "First name",
                                    "type": "string"
                                },
                                {
                                    "name": "last_name",
                                    "required": true,
                                    "description": "Last name",
                                    "type": "string"
                                },
                                {
                                    "name": "suffix",
                                    "required": false,
                                    "description": "Name suffix (Jr./Sr./III etc.)",
                                    "type": "string"
                                }
                            ],
                            "behavior": "format_person_name"
                        }
                    ]
                },
                "request": {
                    "target": "tools",
                    "action": "list"
                }
            },
            "expected_output": "{\n  \"tools\": [\n    {\n      \"name\": \"format_greeting\",\n      \"description\": \"Format a greeting with title and name\",\n      \"inputSchema\": {\n        \"type\": \"object\",\n        \"properties\": {\n          \"title\": {\n            \"type\": \"string\",\n            \"description\": \"Title (Mr./Ms./Dr. etc.)\"\n          },\n          \"first_name\": {\n            \"type\": \"string\",\n            \"description\": \"First name\"\n          },\n          \"last_name\": {\n            \"type\": \"string\",\n            \"description\": \"Last name\"\n          },\n          \"suffix\": {\n            \"type\": \"string\",\n            \"description\": \"Name suffix (Jr./Sr./III etc.)\"\n          }\n        },\n        \"required\": [\n          \"title\",\n          \"first_name\",\n          \"last_name\"\n        ]\n      }\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": "format_greeting",
                            "description": "Format a greeting with title and name",
                            "arguments": [
                                {
                                    "name": "title",
                                    "required": true,
                                    "description": "Title (Mr./Ms./Dr. etc.)",
                                    "type": "string"
                                },
                                {
                                    "name": "first_name",
                                    "required": true,
                                    "description": "First name",
                                    "type": "string"
                                },
                                {
                                    "name": "last_name",
                                    "required": true,
                                    "description": "Last name",
                                    "type": "string"
                                },
                                {
                                    "name": "suffix",
                                    "required": false,
                                    "description": "Name suffix (Jr./Sr./III etc.)",
                                    "type": "string"
                                }
                            ],
                            "behavior": "format_person_name"
                        }
                    ]
                },
                "request": {
                    "target": "tools",
                    "action": "call",
                    "name": "format_greeting",
                    "arguments": {
                        "title": "Dr.",
                        "first_name": "John",
                        "last_name": "Smith"
                    }
                }
            },
            "expected_output": "{\n  \"content\": [\n    {\n      \"type\": \"text\",\n      \"text\": \"Dr. John Smith\"\n    }\n  ],\n  \"isError\": false\n}\n"
        },
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": "format_greeting",
                            "description": "Format a greeting with title and name",
                            "arguments": [
                                {
                                    "name": "title",
                                    "required": true,
                                    "description": "Title (Mr./Ms./Dr. etc.)",
                                    "type": "string"
                                },
                                {
                                    "name": "first_name",
                                    "required": true,
                                    "description": "First name",
                                    "type": "string"
                                },
                                {
                                    "name": "last_name",
                                    "required": true,
                                    "description": "Last name",
                                    "type": "string"
                                },
                                {
                                    "name": "suffix",
                                    "required": false,
                                    "description": "Name suffix (Jr./Sr./III etc.)",
                                    "type": "string"
                                }
                            ],
                            "behavior": "format_person_name"
                        }
                    ]
                },
                "request": {
                    "target": "tools",
                    "action": "call",
                    "name": "format_greeting",
                    "arguments": {
                        "title": "Mr.",
                        "first_name": "John",
                        "last_name": "Smith",
                        "suffix": "Jr."
                    }
                }
            },
            "expected_output": "{\n  \"content\": [\n    {\n      \"type\": \"text\",\n      \"text\": \"Mr. John Smith Jr.\"\n    }\n  ],\n  \"isError\": false\n}\n"
        },
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": "format_greeting",
                            "description": "Format a greeting with title and name",
                            "arguments": [
                                {
                                    "name": "title",
                                    "required": true,
                                    "description": "Title (Mr./Ms./Dr. etc.)",
                                    "type": "string"
                                },
                                {
                                    "name": "first_name",
                                    "required": true,
                                    "description": "First name",
                                    "type": "string"
                                },
                                {
                                    "name": "last_name",
                                    "required": true,
                                    "description": "Last name",
                                    "type": "string"
                                },
                                {
                                    "name": "suffix",
                                    "required": false,
                                    "description": "Name suffix (Jr./Sr./III etc.)",
                                    "type": "string"
                                }
                            ],
                            "behavior": "format_person_name"
                        }
                    ]
                },
                "request": {
                    "target": "tools",
                    "action": "call",
                    "name": "format_greeting",
                    "arguments": {
                        "first_name": "John",
                        "last_name": "Smith"
                    }
                }
            },
            "expected_output": "{\n  \"error\": \"missing_required_parameter\",\n  \"path\": \"title\"\n}\n"
        }
    ]
}
```

---

### Feature 10: Nested Object Tool Inputs

**As a developer**, I want to accept structured object arguments, so I can validate nested required fields and optional nested fields.

**Expected Behavior / Usage:**

A tool argument may be an object with its own properties and required fields. Listing the tool returns a nested object schema. Calls with complete nested data return text content. Calls that omit the whole object or a required nested property return normalized missing_required_parameter errors whose path identifies the missing object or nested field.

**Test Cases:** `rcb_tests/public_test_cases/feature10_nested_object_tool_inputs.json`

```json
{
    "description": "A tool input may be a required object with its own required fields and optional fields.",
    "cases": [
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": "create_user",
                            "description": "Create a user with details",
                            "arguments": [
                                {
                                    "name": "user",
                                    "required": true,
                                    "description": "",
                                    "type": "object",
                                    "properties": [
                                        {
                                            "name": "username",
                                            "required": true,
                                            "description": "Username",
                                            "type": "string"
                                        },
                                        {
                                            "name": "email",
                                            "required": true,
                                            "description": "Email address",
                                            "type": "string"
                                        },
                                        {
                                            "name": "age",
                                            "required": false,
                                            "description": "Age",
                                            "type": "integer"
                                        }
                                    ]
                                }
                            ],
                            "behavior": "create_user_summary"
                        }
                    ]
                },
                "request": {
                    "target": "tools",
                    "action": "list"
                }
            },
            "expected_output": "{\n  \"tools\": [\n    {\n      \"name\": \"create_user\",\n      \"description\": \"Create a user with details\",\n      \"inputSchema\": {\n        \"type\": \"object\",\n        \"properties\": {\n          \"user\": {\n            \"type\": \"object\",\n            \"properties\": {\n              \"username\": {\n                \"type\": \"string\",\n                \"description\": \"Username\"\n              },\n              \"email\": {\n                \"type\": \"string\",\n                \"description\": \"Email address\"\n              },\n              \"age\": {\n                \"type\": \"integer\",\n                \"description\": \"Age\"\n              }\n            },\n            \"required\": [\n              \"username\",\n              \"email\"\n            ],\n            \"description\": \"\"\n          }\n        },\n        \"required\": [\n          \"user\"\n        ]\n      }\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": "create_user",
                            "description": "Create a user with details",
                            "arguments": [
                                {
                                    "name": "user",
                                    "required": true,
                                    "description": "",
                                    "type": "object",
                                    "properties": [
                                        {
                                            "name": "username",
                                            "required": true,
                                            "description": "Username",
                                            "type": "string"
                                        },
                                        {
                                            "name": "email",
                                            "required": true,
                                            "description": "Email address",
                                            "type": "string"
                                        },
                                        {
                                            "name": "age",
                                            "required": false,
                                            "description": "Age",
                                            "type": "integer"
                                        }
                                    ]
                                }
                            ],
                            "behavior": "create_user_summary"
                        }
                    ]
                },
                "request": {
                    "target": "tools",
                    "action": "call",
                    "name": "create_user",
                    "arguments": {
                        "user": {
                            "username": "john",
                            "email": "john@example.com",
                            "age": 30
                        }
                    }
                }
            },
            "expected_output": "{\n  \"content\": [\n    {\n      \"type\": \"text\",\n      \"text\": \"User created: john, john@example.com, 30\"\n    }\n  ],\n  \"isError\": false\n}\n"
        },
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": "create_user",
                            "description": "Create a user with details",
                            "arguments": [
                                {
                                    "name": "user",
                                    "required": true,
                                    "description": "",
                                    "type": "object",
                                    "properties": [
                                        {
                                            "name": "username",
                                            "required": true,
                                            "description": "Username",
                                            "type": "string"
                                        },
                                        {
                                            "name": "email",
                                            "required": true,
                                            "description": "Email address",
                                            "type": "string"
                                        },
                                        {
                                            "name": "age",
                                            "required": false,
                                            "description": "Age",
                                            "type": "integer"
                                        }
                                    ]
                                }
                            ],
                            "behavior": "create_user_summary"
                        }
                    ]
                },
                "request": {
                    "target": "tools",
                    "action": "call",
                    "name": "create_user",
                    "arguments": {
                        "user": {
                            "username": "jane",
                            "email": "jane@example.com"
                        }
                    }
                }
            },
            "expected_output": "{\n  \"content\": [\n    {\n      \"type\": \"text\",\n      \"text\": \"User created: jane, jane@example.com, N/A\"\n    }\n  ],\n  \"isError\": false\n}\n"
        },
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": "create_user",
                            "description": "Create a user with details",
                            "arguments": [
                                {
                                    "name": "user",
                                    "required": true,
                                    "description": "",
                                    "type": "object",
                                    "properties": [
                                        {
                                            "name": "username",
                                            "required": true,
                                            "description": "Username",
                                            "type": "string"
                                        },
                                        {
                                            "name": "email",
                                            "required": true,
                                            "description": "Email address",
                                            "type": "string"
                                        },
                                        {
                                            "name": "age",
                                            "required": false,
                                            "description": "Age",
                                            "type": "integer"
                                        }
                                    ]
                                }
                            ],
                            "behavior": "create_user_summary"
                        }
                    ]
                },
                "request": {
                    "target": "tools",
                    "action": "call",
                    "name": "create_user",
                    "arguments": {}
                }
            },
            "expected_output": "{\n  \"error\": \"missing_required_parameter\",\n  \"path\": \"user\"\n}\n"
        },
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": "create_user",
                            "description": "Create a user with details",
                            "arguments": [
                                {
                                    "name": "user",
                                    "required": true,
                                    "description": "",
                                    "type": "object",
                                    "properties": [
                                        {
                                            "name": "username",
                                            "required": true,
                                            "description": "Username",
                                            "type": "string"
                                        },
                                        {
                                            "name": "email",
                                            "required": true,
                                            "description": "Email address",
                                            "type": "string"
                                        },
                                        {
                                            "name": "age",
                                            "required": false,
                                            "description": "Age",
                                            "type": "integer"
                                        }
                                    ]
                                }
                            ],
                            "behavior": "create_user_summary"
                        }
                    ]
                },
                "request": {
                    "target": "tools",
                    "action": "call",
                    "name": "create_user",
                    "arguments": {
                        "user": {
                            "email": "john@example.com"
                        }
                    }
                }
            },
            "expected_output": "{\n  \"error\": \"missing_required_parameter\",\n  \"path\": \"user.username\"\n}\n"
        }
    ]
}
```

---

### Feature 11: Array Tool Inputs

**As a developer**, I want to accept arrays of primitive values, so I can validate each array element before execution.

**Expected Behavior / Usage:**

A tool argument may be an array whose items are primitive values of a declared type. Listing the tool returns an array schema with an items schema. Calls with arrays of the correct element type return text content. Empty arrays are valid. If an element has the wrong type, the output is a normalized invalid_type error with a path containing the element index, the expected type, and the observed neutral type category.

**Test Cases:** `rcb_tests/public_test_cases/feature11_array_tool_inputs.json`

```json
{
    "description": "A tool input may be an array of primitive values and validates each element by index.",
    "cases": [
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": "sum_numbers",
                            "description": "Sum an array of numbers",
                            "arguments": [
                                {
                                    "name": "numbers",
                                    "required": false,
                                    "description": "Array of numbers to sum",
                                    "type": "array",
                                    "items": "integer"
                                }
                            ],
                            "behavior": "sum_numbers"
                        }
                    ]
                },
                "request": {
                    "target": "tools",
                    "action": "list"
                }
            },
            "expected_output": "{\n  \"tools\": [\n    {\n      \"name\": \"sum_numbers\",\n      \"description\": \"Sum an array of numbers\",\n      \"inputSchema\": {\n        \"type\": \"object\",\n        \"properties\": {\n          \"numbers\": {\n            \"type\": \"array\",\n            \"description\": \"Array of numbers to sum\",\n            \"items\": {\n              \"type\": \"integer\"\n            }\n          }\n        },\n        \"required\": []\n      }\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": "sum_numbers",
                            "description": "Sum an array of numbers",
                            "arguments": [
                                {
                                    "name": "numbers",
                                    "required": false,
                                    "description": "Array of numbers to sum",
                                    "type": "array",
                                    "items": "integer"
                                }
                            ],
                            "behavior": "sum_numbers"
                        }
                    ]
                },
                "request": {
                    "target": "tools",
                    "action": "call",
                    "name": "sum_numbers",
                    "arguments": {
                        "numbers": [
                            1,
                            2,
                            3
                        ]
                    }
                }
            },
            "expected_output": "{\n  \"content\": [\n    {\n      \"type\": \"text\",\n      \"text\": \"6\"\n    }\n  ],\n  \"isError\": false\n}\n"
        },
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": "sum_numbers",
                            "description": "Sum an array of numbers",
                            "arguments": [
                                {
                                    "name": "numbers",
                                    "required": false,
                                    "description": "Array of numbers to sum",
                                    "type": "array",
                                    "items": "integer"
                                }
                            ],
                            "behavior": "sum_numbers"
                        }
                    ]
                },
                "request": {
                    "target": "tools",
                    "action": "call",
                    "name": "sum_numbers",
                    "arguments": {
                        "numbers": []
                    }
                }
            },
            "expected_output": "{\n  \"content\": [\n    {\n      \"type\": \"text\",\n      \"text\": \"0\"\n    }\n  ],\n  \"isError\": false\n}\n"
        },
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": "sum_numbers",
                            "description": "Sum an array of numbers",
                            "arguments": [
                                {
                                    "name": "numbers",
                                    "required": false,
                                    "description": "Array of numbers to sum",
                                    "type": "array",
                                    "items": "integer"
                                }
                            ],
                            "behavior": "sum_numbers"
                        }
                    ]
                },
                "request": {
                    "target": "tools",
                    "action": "call",
                    "name": "sum_numbers",
                    "arguments": {
                        "numbers": [
                            1,
                            "two",
                            3
                        ]
                    }
                }
            },
            "expected_output": "{\n  \"error\": \"invalid_type\",\n  \"path\": \"numbers[1]\",\n  \"expected\": \"integer\",\n  \"actual\": \"string\"\n}\n"
        }
    ]
}
```

---

### Feature 12: Array of Object Tool Inputs

**As a developer**, I want to accept arrays of structured objects, so I can validate required fields inside every element.

**Expected Behavior / Usage:**

A tool argument may be an array of objects. Listing the tool returns an array schema whose items are object schemas with properties and required fields. Calls with complete objects return text content. Empty arrays are valid. If an object element omits a required field, the output is a normalized missing_required_parameter error whose path includes the array index and field name.

**Test Cases:** `rcb_tests/public_test_cases/feature12_array_of_object_tool_inputs.json`

```json
{
    "description": "A tool input may be an array of objects whose elements validate nested required fields.",
    "cases": [
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": "list_users",
                            "description": "List users with their details",
                            "arguments": [
                                {
                                    "name": "users",
                                    "required": false,
                                    "description": "",
                                    "type": "array",
                                    "items": "object",
                                    "properties": [
                                        {
                                            "name": "name",
                                            "required": true,
                                            "description": "User's name",
                                            "type": "string"
                                        },
                                        {
                                            "name": "age",
                                            "required": true,
                                            "description": "User's age",
                                            "type": "integer"
                                        }
                                    ]
                                }
                            ],
                            "behavior": "list_user_summaries"
                        }
                    ]
                },
                "request": {
                    "target": "tools",
                    "action": "list"
                }
            },
            "expected_output": "{\n  \"tools\": [\n    {\n      \"name\": \"list_users\",\n      \"description\": \"List users with their details\",\n      \"inputSchema\": {\n        \"type\": \"object\",\n        \"properties\": {\n          \"users\": {\n            \"type\": \"array\",\n            \"description\": \"\",\n            \"items\": {\n              \"type\": \"object\",\n              \"properties\": {\n                \"name\": {\n                  \"type\": \"string\",\n                  \"description\": \"User's name\"\n                },\n                \"age\": {\n                  \"type\": \"integer\",\n                  \"description\": \"User's age\"\n                }\n              },\n              \"required\": [\n                \"name\",\n                \"age\"\n              ]\n            }\n          }\n        },\n        \"required\": []\n      }\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": "list_users",
                            "description": "List users with their details",
                            "arguments": [
                                {
                                    "name": "users",
                                    "required": false,
                                    "description": "",
                                    "type": "array",
                                    "items": "object",
                                    "properties": [
                                        {
                                            "name": "name",
                                            "required": true,
                                            "description": "User's name",
                                            "type": "string"
                                        },
                                        {
                                            "name": "age",
                                            "required": true,
                                            "description": "User's age",
                                            "type": "integer"
                                        }
                                    ]
                                }
                            ],
                            "behavior": "list_user_summaries"
                        }
                    ]
                },
                "request": {
                    "target": "tools",
                    "action": "call",
                    "name": "list_users",
                    "arguments": {
                        "users": [
                            {
                                "name": "Alice",
                                "age": 30
                            },
                            {
                                "name": "Bob",
                                "age": 25
                            }
                        ]
                    }
                }
            },
            "expected_output": "{\n  \"content\": [\n    {\n      \"type\": \"text\",\n      \"text\": \"Alice (30), Bob (25)\"\n    }\n  ],\n  \"isError\": false\n}\n"
        },
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": "list_users",
                            "description": "List users with their details",
                            "arguments": [
                                {
                                    "name": "users",
                                    "required": false,
                                    "description": "",
                                    "type": "array",
                                    "items": "object",
                                    "properties": [
                                        {
                                            "name": "name",
                                            "required": true,
                                            "description": "User's name",
                                            "type": "string"
                                        },
                                        {
                                            "name": "age",
                                            "required": true,
                                            "description": "User's age",
                                            "type": "integer"
                                        }
                                    ]
                                }
                            ],
                            "behavior": "list_user_summaries"
                        }
                    ]
                },
                "request": {
                    "target": "tools",
                    "action": "call",
                    "name": "list_users",
                    "arguments": {
                        "users": []
                    }
                }
            },
            "expected_output": "{\n  \"content\": [\n    {\n      \"type\": \"text\",\n      \"text\": \"\"\n    }\n  ],\n  \"isError\": false\n}\n"
        },
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": "list_users",
                            "description": "List users with their details",
                            "arguments": [
                                {
                                    "name": "users",
                                    "required": false,
                                    "description": "",
                                    "type": "array",
                                    "items": "object",
                                    "properties": [
                                        {
                                            "name": "name",
                                            "required": true,
                                            "description": "User's name",
                                            "type": "string"
                                        },
                                        {
                                            "name": "age",
                                            "required": true,
                                            "description": "User's age",
                                            "type": "integer"
                                        }
                                    ]
                                }
                            ],
                            "behavior": "list_user_summaries"
                        }
                    ]
                },
                "request": {
                    "target": "tools",
                    "action": "call",
                    "name": "list_users",
                    "arguments": {
                        "users": [
                            {
                                "name": "Alice"
                            },
                            {
                                "name": "Bob",
                                "age": 25
                            }
                        ]
                    }
                }
            },
            "expected_output": "{\n  \"error\": \"missing_required_parameter\",\n  \"path\": \"users[0].age\"\n}\n"
        }
    ]
}
```

---

### Feature 13: Tool Definition Validation

**As a developer**, I want to reject malformed tool definitions, so I can avoid exposing unusable callable operations.

**Expected Behavior / Usage:**

A request may attempt to build a catalog with malformed tool definitions. A null or empty tool name is rejected as invalid_tool_name. Hidden validation also covers tools without executable behavior. Errors are normalized JSON objects and do not expose host-language exception class names or runtime-specific message decorations.

**Test Cases:** `rcb_tests/public_test_cases/feature13_tool_definition_validation.json`

```json
{
    "description": "Invalid tool definitions are rejected with normalized error categories.",
    "cases": [
        {
            "input": {
                "setup": {
                    "tools": [
                        {
                            "name": null,
                            "description": "Invalid tool",
                            "arguments": [],
                            "behavior": "constant_text",
                            "text": "test"
                        }
                    ]
                },
                "request": {
                    "target": "catalog",
                    "action": "build"
                }
            },
            "expected_output": "{\n  \"error\": \"invalid_tool_name\"\n}\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ens[a generic error code and attribute key]ng high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_static_resource_listing.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_static_resource_listing@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- include schema descriptors as nested objects
- return text payload within envelope
