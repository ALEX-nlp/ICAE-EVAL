## Product Requirement Document

# Generative AI Client Adapter - Request, Response, and Resource Contract

## Project Goal

Build a developer-facing client adapter for a generative AI service that allows developers to prepare model requests, interpret model responses, validate conversation state, and manage remote file and cache resources without hand-crafting wire-format HTTP payloads and response helpers.

---

## Background & Problem

Without this library/tool, developers are forced to manually normalize prompt inputs, build service URLs and headers, format token-count and cache requests, parse generated response structures, detect blocked responses, and keep conversation histories valid. This leads to repetitive boilerplate, subtle protocol mistakes, inconsistent error handling, and fragile integrations.

With this library/tool, callers provide idiomatic prompt, response, history, and resource data while the adapter consistently translates them into service-ready requests and developer-readable outputs.

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

### Feature 1: Content request formatting

**As a developer**, I want plain text prompts and part arrays to be converted into a canonical single user-role content request, so I can integrate with the service using stable, predictable request payloads.

**Expected Behavior / Usage:**

Text prompts and part arrays are converted into a canonical single user content request while preserving extra request configuration. Inputs are JSON values matching the examples below, and outputs are deterministic stdout lines containing either normalized request/response data or language-neutral error categories. Error outputs never expose host-language exception class names or stack traces.

**Test Cases:** `rcb_tests/public_test_cases/feature1_content_request_formatting.json`

```json
{
    "description": "Text prompts and part arrays are converted into a canonical single user content request while preserving extra request configuration.",
    "cases": [
        {
            "input": "some text content",
            "expected_output": "request={\"contents\":[{\"parts\":[{\"text\":\"some text content\"}],\"role\":\"user\"}]}\n"
        },
        {
            "input": [
                "txt1",
                "txt2"
            ],
            "expected_output": "request={\"contents\":[{\"parts\":[{\"text\":\"txt1\"},{\"text\":\"txt2\"}],\"role\":\"user\"}]}\n"
        },
        {
            "input": [
                "txtA",
                {
                    "text": "txtB"
                }
            ],
            "expected_output": "request={\"contents\":[{\"parts\":[{\"text\":\"txtA\"},{\"text\":\"txtB\"}],\"role\":\"user\"}]}\n"
        },
        {
            "input": {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": "txtA"
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "topK": 100
                }
            },
            "expected_output": "request={\"contents\":[{\"parts\":[{\"text\":\"txtA\"}],\"role\":\"user\"}],\"generationConfig\":{\"topK\":100}}\n"
        }
    ]
}
```

---

### Feature 2: System instruction normalization

**As a developer**, I want a system instruction supplied as plain text, a text part, or role-less content to be normalized into a system-role content object, so I can set model behavior without worrying about its input shape.

**Expected Behavior / Usage:**

A caller-supplied system instruction is normalized into a system role content object, whether supplied as plain text, a text part, or role-less content. Inputs are JSON values matching the examples below, and outputs are deterministic stdout lines containing either normalized request/response data or language-neutral error categories. Error outputs never expose host-language exception class names or stack traces.

**Test Cases:** `rcb_tests/public_test_cases/feature2_system_instruction_formatting.json`

```json
{
    "description": "A caller-supplied system instruction is normalized into a system role content object, whether supplied as plain text, a text part, or role-less content.",
    "cases": [
        {
            "input": {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": "txtA"
                            }
                        ]
                    }
                ],
                "systemInstruction": "be excited"
            },
            "expected_output": "request={\"contents\":[{\"parts\":[{\"text\":\"txtA\"}],\"role\":\"user\"}],\"systemInstruction\":{\"parts\":[{\"text\":\"be excited\"}],\"role\":\"system\"}}\n"
        },
        {
            "input": {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": "txtA"
                            }
                        ]
                    }
                ],
                "systemInstruction": {
                    "text": "be excited"
                }
            },
            "expected_output": "request={\"contents\":[{\"parts\":[{\"text\":\"txtA\"}],\"role\":\"user\"}],\"systemInstruction\":{\"parts\":[{\"text\":\"be excited\"}],\"role\":\"system\"}}\n"
        },
        {
            "input": {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": "txtA"
                            }
                        ]
                    }
                ],
                "systemInstruction": {
                    "parts": [
                        {
                            "text": "be excited"
                        }
                    ]
                }
            },
            "expected_output": "request={\"contents\":[{\"parts\":[{\"text\":\"txtA\"}],\"role\":\"user\"}],\"systemInstruction\":{\"parts\":[{\"text\":\"be excited\"}],\"role\":\"system\"}}\n"
        }
    ]
}
```

---

### Feature 3: Token count request formatting

**As a developer**, I want token-count inputs to be wrapped as a generation-style request that inherits model-level context such as system instruction, tools, and cached content references, so I can estimate token usage with the same context the model would see.

**Expected Behavior / Usage:**

Token-count inputs are wrapped as a generation-style request and may inherit model-level context such as system instruction, tools, and cached content references. Inputs are JSON values matching the examples below, and outputs are deterministic stdout lines containing either normalized request/response data or language-neutral error categories. Error outputs never expose host-language exception class names or stack traces.

**Test Cases:** `rcb_tests/public_test_cases/feature3_token_count_request_formatting.json`

```json
{
    "description": "Token-count inputs are wrapped as a generation-style request and may inherit model-level context such as system instruction, tools, and cached content references.",
    "cases": [
        {
            "input": {
                "request": "some text content",
                "modelDefaults": {
                    "model": "gemini-1.5-flash"
                }
            },
            "expected_output": "request={\"generateContentRequest\":{\"contents\":[{\"parts\":[{\"text\":\"some text content\"}],\"role\":\"user\"}],\"model\":\"gemini-1.5-flash\"}}\n"
        },
        {
            "input": {
                "request": "some text content",
                "modelDefaults": {
                    "model": "gemini-1.5-flash",
                    "systemInstruction": "hello",
                    "tools": [
                        {
                            "codeExecution": {}
                        }
                    ],
                    "cachedContent": {
                        "name": "mycache",
                        "contents": []
                    }
                }
            },
            "expected_output": "request={\"generateContentRequest\":{\"cachedContent\":\"mycache\",\"contents\":[{\"parts\":[{\"text\":\"some text content\"}],\"role\":\"user\"}],\"model\":\"gemini-1.5-flash\",\"systemInstruction\":\"hello\",\"tools\":[{\"codeExecution\":{}}]}}\n"
        },
        {
            "input": {
                "request": {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {
                                    "text": "some text content"
                                }
                            ]
                        }
                    ]
                },
                "modelDefaults": {
                    "model": "gemini-1.5-flash",
                    "systemInstruction": "hello",
                    "tools": [
                        {
                            "codeExecution": {}
                        }
                    ],
                    "cachedContent": {
                        "name": "mycache",
                        "contents": []
                    }
                }
            },
            "expected_output": "request={\"generateContentRequest\":{\"cachedContent\":\"mycache\",\"contents\":[{\"parts\":[{\"text\":\"some text content\"}],\"role\":\"user\"}],\"model\":\"gemini-1.5-flash\",\"systemInstruction\":\"hello\",\"tools\":[{\"codeExecution\":{}}]}}\n"
        }
    ]
}
```

---

### Feature 4: Model API request construction

**As a developer**, I want model RPC requests to produce deterministic URLs, headers, methods, streaming markers, and normalized backend errors, so I can call the service reliably without hand-assembling HTTP details.

**Expected Behavior / Usage:**

Model RPC requests produce deterministic URLs, request headers, methods, streaming query markers, custom client labels, custom headers, timeout signals, and normalized backend errors. Inputs are JSON values matching the examples below, and outputs are deterministic stdout lines containing either normalized request/response data or language-neutral error categories. Error outputs never expose host-language exception class names or stack traces.

**Test Cases:** `rcb_tests/public_test_cases/feature4_model_request_construction.json`

```json
{
    "description": "Model RPC requests produce deterministic URLs, request headers, methods, streaming query markers, custom client labels, custom headers, timeout signals, and normalized backend errors.",
    "cases": [
        {
            "input": {
                "mode": "url",
                "model": "models/model-name",
                "task": "GENERATE_CONTENT",
                "apiKey": "key",
                "stream": true,
                "options": {}
            },
            "expected_output": "url=https://generativelanguage.googleapis.com/v1beta/models/model-name:generateContent?alt=sse\ncontains_api_key=false\n"
        },
        {
            "input": {
                "mode": "url",
                "model": "tunedModels/model-name",
                "task": "GENERATE_CONTENT",
                "apiKey": "key",
                "stream": false,
                "options": {
                    "apiVersion": "v2beta",
                    "baseUrl": "http://my.staging.website"
                }
            },
            "expected_output": "url=http://my.staging.website/v2beta/tunedModels/model-name:generateContent\ncontains_api_key=false\n"
        },
        {
            "input": {
                "mode": "construct",
                "model": "model-name",
                "task": "GENERATE_CONTENT",
                "apiKey": "key",
                "stream": true,
                "body": "",
                "options": {
                    "apiClient": "client/version",
                    "timeout": 5000
                },
                "customHeaders": {
                    "customerHeader": "customerHeaderValue"
                }
            },
            "expected_output": "url=https://generativelanguage.googleapis.com/v1beta/model-name:generateContent?alt=sse\nmethod=POST\ncontent_type=application/json\napi_key_header=key\nclient_header=client/version genai-js/__PACKAGE_VERSION__\ncustomer_header=customerHeaderValue\nhas_abort_signal=true\n"
        },
        {
            "input": {
                "mode": "construct",
                "model": "model-name",
                "task": "GENERATE_CONTENT",
                "apiKey": "key",
                "stream": true,
                "body": "",
                "options": {},
                "customHeaders": {
                    "x-goog-api-client": "client/version"
                }
            },
            "expected_output": "error=reserved_header\nheader=x-goog-api-client\n"
        },
        {
            "input": {
                "mode": "fetch_error",
                "model": "model-name",
                "task": "GENERATE_CONTENT",
                "apiKey": "key",
                "stream": true,
                "body": "",
                "status": 500,
                "statusText": "Server Error",
                "errorMessage": "extra info"
            },
            "expected_output": "error=http_error\nmessage=extra info\nstatus=500\nstatus_text=Server Error\n"
        }
    ]
}
```

---

### Feature 5: Generated response rendering

**As a developer**, I want a completed response to expose concatenated text, ordered tool-call payloads, mixed text/tool-call content, and executable-code output as developer-readable text, so I can consume model output without traversing raw candidate structures.

**Expected Behavior / Usage:**

A completed response exposes concatenated text, ordered tool-call payloads, mixed text/tool-call content, and executable-code output as developer-readable text. Inputs are JSON values matching the examples below, and outputs are deterministic stdout lines containing either normalized request/response data or language-neutral error categories. Error outputs never expose host-language exception class names or stack traces.

**Test Cases:** `rcb_tests/public_test_cases/feature5_response_rendering.json`

```json
{
    "description": "A completed response exposes concatenated text, ordered tool-call payloads, mixed text/tool-call content, and executable-code output as developer-readable text.",
    "cases": [
        {
            "input": {
                "candidates": [
                    {
                        "index": 0,
                        "content": {
                            "role": "model",
                            "parts": [
                                {
                                    "text": "Some text"
                                },
                                {
                                    "text": " and some more text"
                                }
                            ]
                        }
                    }
                ]
            },
            "expected_output": "text=Some text and some more text\nfunction_calls=[]\n"
        },
        {
            "input": {
                "candidates": [
                    {
                        "index": 0,
                        "content": {
                            "role": "model",
                            "parts": [
                                {
                                    "functionCall": {
                                        "name": "find_theaters",
                                        "args": {
                                            "location": "Mountain View, CA",
                                            "movie": "Barbie"
                                        }
                                    }
                                },
                                {
                                    "functionCall": {
                                        "name": "find_times",
                                        "args": {
                                            "location": "Mountain View, CA",
                                            "movie": "Barbie",
                                            "time": "20:00"
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ]
            },
            "expected_output": "text=\nfunction_calls=[{\"args\":{\"location\":\"Mountain View, CA\",\"movie\":\"Barbie\"},\"name\":\"find_theaters\"},{\"args\":{\"location\":\"Mountain View, CA\",\"movie\":\"Barbie\",\"time\":\"20:00\"},\"name\":\"find_times\"}]\n"
        },
        {
            "input": {
                "candidates": [
                    {
                        "index": 0,
                        "content": {
                            "role": "model",
                            "parts": [
                                {
                                    "text": "some text"
                                },
                                {
                                    "functionCall": {
                                        "name": "find_times",
                                        "args": {
                                            "location": "Mountain View, CA",
                                            "movie": "Barbie",
                                            "time": "20:00"
                                        }
                                    }
                                },
                                {
                                    "text": " and more text"
                                }
                            ]
                        }
                    }
                ]
            },
            "expected_output": "text=some text and more text\nfunction_calls=[{\"args\":{\"location\":\"Mountain View, CA\",\"movie\":\"Barbie\",\"time\":\"20:00\"},\"name\":\"find_times\"}]\n"
        },
        {
            "input": {
                "candidates": [
                    {
                        "index": 0,
                        "content": {
                            "role": "model",
                            "parts": [
                                {
                                    "text": "here's how to print hello world"
                                },
                                {
                                    "executableCode": {
                                        "language": "PYTHON",
                                        "code": "print(\"hello world\")"
                                    }
                                },
                                {
                                    "codeExecutionResult": {
                                        "outcome": "OUTCOME_OK",
                                        "output": "hello world"
                                    }
                                }
                            ]
                        }
                    }
                ]
            },
            "expected_output": "text=here's how to print hello world\n```PYTHON\nprint(\"hello world\")\n```\n\n```\nhello world\n```\n\nfunction_calls=[]\n"
        }
    ]
}
```

---

### Feature 6: Blocked response signals

**As a developer**, I want a response blocked by safety feedback or unsafe finish reasons to report the block scope and reason instead of returning normal content, so I can detect and handle moderation outcomes explicitly.

**Expected Behavior / Usage:**

A response blocked by safety feedback or unsafe finish reasons reports the block scope and reason instead of returning normal generated content. Inputs are JSON values matching the examples below, and outputs are deterministic stdout lines containing either normalized request/response data or language-neutral error categories. Error outputs never expose host-language exception class names or stack traces.

**Test Cases:** `rcb_tests/public_test_cases/feature6_blocked_response_signals.json`

```json
{
    "description": "A response blocked by safety feedback or unsafe finish reasons reports the block scope and reason instead of returning normal generated content.",
    "cases": [
        {
            "input": {
                "mode": "text",
                "response": {
                    "promptFeedback": {
                        "blockReason": "SAFETY",
                        "safetyRatings": []
                    }
                }
            },
            "expected_output": "error=blocked_response\nreason=SAFETY\n"
        },
        {
            "input": {
                "mode": "message",
                "response": {
                    "promptFeedback": {
                        "blockReason": "SAFETY",
                        "blockReasonMessage": "safety reasons",
                        "safetyRatings": []
                    }
                }
            },
            "expected_output": "blocked=true\nreason=SAFETY\nscope=response\nmessage=safety reasons\n"
        },
        {
            "input": {
                "mode": "message",
                "response": {
                    "candidates": [
                        {
                            "index": 0,
                            "finishReason": "SAFETY",
                            "finishMessage": "unsafe candidate",
                            "content": {}
                        }
                    ]
                }
            },
            "expected_output": "blocked=true\nreason=SAFETY\nscope=candidate\nmessage=unsafe candidate\n"
        }
    ]
}
```

---

### Feature 7: Conversation history validation

**As a developer**, I want conversation history to be accepted only when it begins with user content and every turn has non-empty parts compatible with its role, so I can catch malformed histories before sending them to the service.

**Expected Behavior / Usage:**

Conversation history is accepted only when it begins with user content and every turn contains non-empty parts compatible with that role. Inputs are JSON values matching the examples below, and outputs are deterministic stdout lines containing either normalized request/response data or language-neutral error categories. Error outputs never expose host-language exception class names or stack traces.

**Test Cases:** `rcb_tests/public_test_cases/feature7_chat_history_validation.json`

```json
{
    "description": "Conversation history is accepted only when it begins with user content and every turn contains non-empty parts compatible with that role.",
    "cases": [
        {
            "input": {
                "history": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": "hi"
                            }
                        ]
                    }
                ]
            },
            "expected_output": "history_valid=true\nturns=1\n"
        },
        {
            "input": {
                "history": [
                    {
                        "role": "model",
                        "parts": [
                            {
                                "text": "hi"
                            }
                        ]
                    }
                ]
            },
            "expected_output": "error=invalid_chat_history_first_role\nrole=model\n"
        },
        {
            "input": {
                "history": [
                    {
                        "role": "user",
                        "parts": []
                    }
                ]
            },
            "expected_output": "error=empty_content_parts\n"
        },
        {
            "input": {
                "history": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": "hi"
                            }
                        ]
                    },
                    {
                        "role": "model",
                        "parts": [
                            {
                                "functionCall": {
                                    "name": "greet",
                                    "args": {
                                        "name": "user"
                                    }
                                }
                            }
                        ]
                    },
                    {
                        "role": "function",
                        "parts": [
                            {
                                "functionResponse": {
                                    "name": "greet",
                                    "response": {
                                        "name": "user"
                                    }
                                }
                            }
                        ]
                    }
                ]
            },
            "expected_output": "history_valid=true\nturns=3\n"
        }
    ]
}
```

---

### Feature 8: Conversation response validity

**As a developer**, I want a model reply to be treated as valid for conversation state only when it contains at least one meaningful text, tool-call, or tool-response part, so I can avoid appending empty replies to history.

**Expected Behavior / Usage:**

A model reply is valid for conversation state only when it contains at least one meaningful text, tool-call, or tool-response part. Inputs are JSON values matching the examples below, and outputs are deterministic stdout lines containing either normalized request/response data or language-neutral error categories. Error outputs never expose host-language exception class names or stack traces.

**Test Cases:** `rcb_tests/public_test_cases/feature8_model_response_validity.json`

```json
{
    "description": "A model reply is valid for conversation state only when it contains at least one meaningful text, tool-call, or tool-response part.",
    "cases": [
        {
            "input": {
                "response": {}
            },
            "expected_output": "response_valid=false\ncandidate_count=0\n"
        },
        {
            "input": {
                "response": {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": "hello"
                                    }
                                ]
                            }
                        }
                    ]
                }
            },
            "expected_output": "response_valid=true\ncandidate_count=1\n"
        },
        {
            "input": {
                "response": {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "functionCall": {
                                            "name": "foo",
                                            "args": {
                                                "input": "bar"
                                            }
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            },
            "expected_output": "response_valid=true\ncandidate_count=1\n"
        },
        {
            "input": {
                "response": {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": ""
                                    }
                                ]
                            }
                        }
                    ]
                }
            },
            "expected_output": "response_valid=false\ncandidate_count=1\n"
        }
    ]
}
```

---

### Feature 9: File resource request handling

**As a developer**, I want file resource operations to normalize file identifiers and upload metadata, build the correct HTTP method and URL, and reject invalid identifiers or missing MIME types, so I can manage remote files without crafting upload protocols by hand.

**Expected Behavior / Usage:**

File resource operations normalize file identifiers and upload metadata, construct the correct HTTP method and URL, include upload protocol headers for multipart uploads, and reject invalid identifiers or missing MIME types. Inputs are JSON values matching the examples below, and outputs are deterministic stdout lines containing either normalized request/response data or language-neutral error categories. Error outputs never expose host-language exception class names or stack traces.

**Test Cases:** `rcb_tests/public_test_cases/feature9_file_resource_requests.json`

```json
{
    "description": "File resource operations normalize file identifiers and upload metadata, construct the correct HTTP method and URL, include upload protocol headers for multipart uploads, and reject invalid identifiers or missing MIME types.",
    "cases": [
        {
            "input": {
                "operation": "metadata",
                "metadata": {
                    "mimeType": "image/jpeg",
                    "displayName": "display name",
                    "name": "filename"
                }
            },
            "expected_output": "metadata={\"displayName\":\"display name\",\"mimeType\":\"image/jpeg\",\"name\":\"files/filename\"}\n"
        },
        {
            "input": {
                "operation": "metadata",
                "metadata": {}
            },
            "expected_output": "error=missing_mime_type\n"
        },
        {
            "input": {
                "operation": "list",
                "params": {
                    "pageSize": 3,
                    "pageToken": "abc"
                }
            },
            "expected_output": "task=list\nmethod=GET\nurl=https://generativelanguage.googleapis.com/v1beta/files?pageSize=3&pageToken=abc\nresult={\"files\":[{\"uri\":\"https://yourfile.here/filename\"}]}\n"
        },
        {
            "input": {
                "operation": "get",
                "name": "files/nameoffile"
            },
            "expected_output": "task=get\nmethod=GET\nurl=https://generativelanguage.googleapis.com/v1beta/files/nameoffile\nresult={\"uri\":\"https://yourfile.here/filename\"}\n"
        },
        {
            "input": {
                "operation": "delete",
                "name": ""
            },
            "expected_output": "error=invalid_file_id\n"
        },
        {
            "input": {
                "operation": "upload",
                "filePath": "./test-utils/cat.png",
                "metadata": {
                    "mimeType": "image/png",
                    "name": "customname",
                    "displayName": "mydisplayname"
                }
            },
            "expected_output": "task=upload\nmethod=POST\nurl=https://generativelanguage.googleapis.com/upload/v1beta/files\nupload_protocol=multipart\nbody_has_mime=true\nbody_has_name=true\nbody_has_display_name=true\nresult={\"file\":{\"uri\":\"https://yourfile.here/filename\"}}\n"
        }
    ]
}
```

---

### Feature 10: Cached content request handling

**As a developer**, I want cached content operations to normalize resource names, build create/list/get/update/delete requests with pagination and expiration fields, and reject missing or conflicting expiration inputs, so I can manage server-side caches safely.

**Expected Behavior / Usage:**

Cached content operations normalize resource names, construct create/list/get/update/delete requests with pagination and expiration fields, and reject missing or conflicting expiration inputs. Inputs are JSON values matching the examples below, and outputs are deterministic stdout lines containing either normalized request/response data or language-neutral error categories. Error outputs never expose host-language exception class names or stack traces.

**Test Cases:** `rcb_tests/public_test_cases/feature10_cache_resource_requests.json`

```json
{
    "description": "Cached content operations normalize resource names, construct create/list/get/update/delete requests with pagination and expiration fields, and reject missing or conflicting expiration inputs.",
    "cases": [
        {
            "input": {
                "operation": "create",
                "content": {
                    "model": "models/gemini-1.5-pro-001",
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {
                                    "text": "some text"
                                }
                            ]
                        }
                    ],
                    "ttlSeconds": 30,
                    "systemInstruction": "talk like a cat",
                    "tools": [
                        {
                            "functionDeclarations": [
                                {
                                    "name": "myFn"
                                }
                            ]
                        }
                    ],
                    "toolConfig": {
                        "functionCallingConfig": {}
                    },
                    "displayName": "a display name."
                }
            },
            "expected_output": "task=create\nmethod=POST\nurl=https://generativelanguage.googleapis.com/v1beta/cachedContents\nbody={\"contents\":[{\"parts\":[{\"text\":\"some text\"}],\"role\":\"user\"}],\"displayName\":\"a display name.\",\"model\":\"models/gemini-1.5-pro-001\",\"systemInstruction\":{\"parts\":[{\"text\":\"talk like a cat\"}],\"role\":\"system\"},\"toolConfig\":{\"functionCallingConfig\":{}},\"tools\":[{\"functionDeclarations\":[{\"name\":\"myFn\"}]}],\"ttl\":\"30s\"}\nresult={\"name\":\"cachedContents/hash1234\"}\n"
        },
        {
            "input": {
                "operation": "create",
                "content": {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {
                                    "text": "some text"
                                }
                            ]
                        }
                    ]
                }
            },
            "expected_output": "error=missing_model\n"
        },
        {
            "input": {
                "operation": "create",
                "content": {
                    "model": "models/gemini-1.5-pro-001",
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {
                                    "text": "some text"
                                }
                            ]
                        }
                    ],
                    "ttlSeconds": 40,
                    "expireTime": "2030-01-01T00:00:00.000Z"
                }
            },
            "expected_output": "error=exclusive_expiration_fields\n"
        },
        {
            "input": {
                "operation": "list",
                "params": {
                    "pageSize": 3,
                    "pageToken": "abc"
                }
            },
            "expected_output": "task=list\nmethod=GET\nurl=https://generativelanguage.googleapis.com/v1beta/cachedContents?pageSize=3&pageToken=abc\nresult={\"cachedContents\":[{\"name\":\"cachedContents/hash1234\"}]}\n"
        },
        {
            "input": {
                "operation": "get",
                "name": "hash1234"
            },
            "expected_output": "task=get\nmethod=GET\nurl=https://generativelanguage.googleapis.com/v1beta/cachedContents/hash1234\nresult={\"name\":\"cachedContents/hash1234\"}\n"
        },
        {
            "input": {
                "operation": "update",
                "name": "cachedContents/hash1234",
                "update": {
                    "cachedContent": {
                        "ttlSeconds": 30
                    }
                }
            },
            "expected_output": "task=update\nmethod=PATCH\nurl=https://generativelanguage.googleapis.com/v1beta/cachedContents/hash1234\nbody={\"ttl\":\"30s\"}\nresult={\"name\":\"cachedContents/hash1234\"}\n"
        },
        {
            "input": {
                "operation": "delete",
                "name": ""
            },
            "expected_output": "error=invalid_cache_name\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- the path structure defined in the API routing config
- the logic used in the text formatter unit tests
