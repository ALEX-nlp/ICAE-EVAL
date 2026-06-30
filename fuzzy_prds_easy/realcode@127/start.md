## Product Requirement Document

# Nested API Serializer Extensions - Flexible Sparse Fields, Expansion, and External Identifiers

## Project Goal

Build a serializer extension toolkit for JSON API applications that allows developers to select fields, exclude fields, expand related resources, and expose opaque [a set of allowed field path patterns (consult the field mapping docs)]entifiers without hand-writing separate serializers for every response shape.

---

## Background & Problem

Without this library/tool, developers are forced to duplicate serializers, manually prune nested dictionaries, manually parse request parameters, and hand-code relation expansion for each endpoint. This leads to repetitive code, inconsistent payload shapes, fragile val[a set of allowed field path patterns (consult the field mapping docs)]ation, and acc[a set of allowed field path patterns (consult the field mapping docs)]ental exposure of internal [a set of allowed field path patterns (consult the field mapping docs)]entifiers.

With this library/tool, a single serializer configuration can produce compact default responses, sparse field responses, rich expanded responses, write-time relation resolution, external [a set of allowed field path patterns (consult the field mapping docs)]entifier rendering, and request-driven API output in a consistent way.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain. 
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, prov[a set of allowed field path patterns (consult the field mapping docs)]ed it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository. 
   Do not over-engineer simple problems, but strictly avo[a set of allowed field path patterns (consult the field mapping docs)] monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases prov[a set of allowed field path patterns (consult the field mapping docs)]ed in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into [a set of allowed field path patterns (consult the field mapping docs)]iomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, val[a set of allowed field path patterns (consult the field mapping docs)]ation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and [a set of allowed field path patterns (consult the field mapping docs)]iomatic to the target programming language, h[a set of allowed field path patterns (consult the field mapping docs)]ing internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Select Requested Fields

**As a developer**, I want to serialize nested records with only explicitly requested fields, so I can reduce payload size while preserving the requested object structure.

**Expected Behavior / Usage:**

The adapter input uses `operation: "select_fields"` and may include `fields`, an array of field paths. When `fields` is omitted or empty, the complete product representation is emitted. Field paths may target root fields such as `[a set of allowed field path patterns (consult the field mapping docs)]`, nested object fields such as `[a set of allowed field path patterns (consult the field mapping docs)]`, and fields ins[a set of allowed field path patterns (consult the field mapping docs)]e collections such as `[a set of allowed field path patterns (consult the field mapping docs)]`. The output is a single JSON object followed by a newline; only requested branches and leaves appear, collection order is stable, and nested containers are retained when any child field is requested.

**Test Cases:** `rcb_tests/public_test_cases/feature1_select_requested_fields.json`

```json
{
    "cases": [
        {
            "expected_output": "{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"manufacturer\":{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"Tesla\"},\"name\":\"Model S\",\"skus\":[{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"owners\":[{\"email\":\"t.wellick@e-corp.com\",\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"Tyrell\",\"organization\":{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"E Corp\"}}],\"variant\":\"P100D\"},{\"[a set of allowed field path patterns (consult the field mapping docs)]\":2,\"owners\":[],\"variant\":\"70\"}]}\n",
            "input": {
                "operation": "select_fields"
            }
        },
        {
            "expected_output": "{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1}\n",
            "input": {
                "fields": [
                    "[a set of allowed field path patterns (consult the field mapping docs)]"
                ],
                "operation": "select_fields"
            }
        },
        {
            "expected_output": "{\"skus\":[{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"variant\":\"P100D\"},{\"[a set of allowed field path patterns (consult the field mapping docs)]\":2,\"variant\":\"70\"}]}\n",
            "input": {
                "fields": [
                    "skus__[a set of allowed field path patterns (consult the field mapping docs)]",
                    "[a set of allowed field path patterns (consult the field mapping docs)]"
                ],
                "operation": "select_fields"
            }
        },
        {
            "expected_output": "{\"manufacturer\":{\"name\":\"Tesla\"},\"name\":\"Model S\",\"skus\":[{\"variant\":\"P100D\"},{\"variant\":\"70\"}]}\n",
            "input": {
                "fields": [
                    "name",
                    "[a set of allowed field path patterns (consult the field mapping docs)]",
                    "[a set of allowed field path patterns (consult the field mapping docs)]"
                ],
                "operation": "select_fields"
            }
        }
    ],
    "description": "Serialize a nested product record while keeping only the requested root or nested fields."
}
```

---

### Feature 2: Reject Inval[a set of allowed field path patterns (consult the field mapping docs)] Selection Paths

**As a developer**, I want to receive a clear neutral error for inval[a set of allowed field path patterns (consult the field mapping docs)] field selections, so I can distinguish bad client instructions from val[a set of allowed field path patterns (consult the field mapping docs)] sparse serialization.

**Expected Behavior / Usage:**

The adapter input uses `operation: "select_fields"` with `fields`. If a field path does not exist at the addressed level, stdout is the normalized JSON error `{"error":"unknown_field"}` followed by a newline. If the input asks for both an entire object and one of that object’s descendants in the same selection set, stdout is the normalized JSON error `{"error":"inval[a set of allowed field path patterns (consult the field mapping docs)]_field_selection"}` followed by a newline. Error output must not expose host-language exception names.

**Test Cases:** `rcb_tests/public_test_cases/feature2_reject_inval[a set of allowed field path patterns (consult the field mapping docs)]_field_selection.json`

```json
{
    "cases": [
        {
            "expected_output": "{\"error\":\"unknown_field\"}\n",
            "input": {
                "fields": [
                    "not_found"
                ],
                "operation": "select_fields"
            }
        },
        {
            "expected_output": "{\"error\":\"inval[a set of allowed field path patterns (consult the field mapping docs)]_field_selection\"}\n",
            "input": {
                "fields": [
                    "manufacturer",
                    "[a set of allowed field path patterns (consult the field mapping docs)]"
                ],
                "operation": "select_fields"
            }
        }
    ],
    "description": "Reject requested field paths that do not correspond to fields in the nested representation or that ambiguously request both a whole object and one of its children."
}
```

---

### Feature 3: Exclude Requested Fields

**As a developer**, I want to remove explicitly named fields from nested records, so I can h[a set of allowed field path patterns (consult the field mapping docs)]e unwanted data without redefining the whole representation.

**Expected Behavior / Usage:**

The adapter input uses `operation: "exclude_fields"` and may include `fields`, an array of field paths to remove. When `fields` is omitted or empty, the complete product representation is emitted. Root, nested object, and collection-child fields can be excluded. The output is a single JSON object followed by a newline; unspecified fields remain in their original nested structure and collection order remains stable.

**Test Cases:** `rcb_tests/public_test_cases/feature3_exclude_requested_fields.json`

```json
{
    "cases": [
        {
            "expected_output": "{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"manufacturer\":{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"Tesla\"},\"name\":\"Model S\",\"skus\":[{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"owners\":[{\"email\":\"t.wellick@e-corp.com\",\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"Tyrell\",\"organization\":{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"E Corp\"}}],\"variant\":\"P100D\"},{\"[a set of allowed field path patterns (consult the field mapping docs)]\":2,\"owners\":[],\"variant\":\"70\"}]}\n",
            "input": {
                "operation": "exclude_fields"
            }
        },
        {
            "expected_output": "{\"manufacturer\":{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"Tesla\"},\"name\":\"Model S\",\"skus\":[{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"owners\":[{\"email\":\"t.wellick@e-corp.com\",\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"Tyrell\",\"organization\":{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"E Corp\"}}],\"variant\":\"P100D\"},{\"[a set of allowed field path patterns (consult the field mapping docs)]\":2,\"owners\":[],\"variant\":\"70\"}]}\n",
            "input": {
                "fields": [
                    "[a set of allowed field path patterns (consult the field mapping docs)]"
                ],
                "operation": "exclude_fields"
            }
        },
        {
            "expected_output": "{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"manufacturer\":{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"Tesla\"},\"name\":\"Model S\",\"skus\":[{\"owners\":[{\"email\":\"t.wellick@e-corp.com\",\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"Tyrell\",\"organization\":{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"E Corp\"}}]},{\"owners\":[]}]}\n",
            "input": {
                "fields": [
                    "skus__[a set of allowed field path patterns (consult the field mapping docs)]",
                    "[a set of allowed field path patterns (consult the field mapping docs)]"
                ],
                "operation": "exclude_fields"
            }
        },
        {
            "expected_output": "{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"manufacturer\":{\"name\":\"Tesla\"},\"skus\":[{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"owners\":[{\"email\":\"t.wellick@e-corp.com\",\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"Tyrell\",\"organization\":{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"E Corp\"}}]},{\"[a set of allowed field path patterns (consult the field mapping docs)]\":2,\"owners\":[]}]}\n",
            "input": {
                "fields": [
                    "name",
                    "manufacturer__[a set of allowed field path patterns (consult the field mapping docs)]",
                    "[a set of allowed field path patterns (consult the field mapping docs)]"
                ],
                "operation": "exclude_fields"
            }
        }
    ],
    "description": "Serialize a nested product record while removing the requested root or nested fields."
}
```

---

### Feature 4: Reject Inval[a set of allowed field path patterns (consult the field mapping docs)] Exclusion Paths

**As a developer**, I want to receive a clear neutral error for inval[a set of allowed field path patterns (consult the field mapping docs)] exclusions, so I can avo[a set of allowed field path patterns (consult the field mapping docs)] silently accepting misspelled or impossible output paths.

**Expected Behavior / Usage:**

The adapter input uses `operation: "exclude_fields"` with `fields`. If any excluded field path does not exist at the addressed level, stdout is the normalized JSON error `{"error":"unknown_field"}` followed by a newline. Error output must be language-neutral and must not include runtime exception names or stack details.

**Test Cases:** `rcb_tests/public_test_cases/feature4_reject_inval[a set of allowed field path patterns (consult the field mapping docs)]_exclusion_paths.json`

```json
{
    "cases": [
        {
            "expected_output": "{\"error\":\"unknown_field\"}\n",
            "input": {
                "fields": [
                    "not_found"
                ],
                "operation": "exclude_fields"
            }
        },
        {
            "expected_output": "{\"error\":\"unknown_field\"}\n",
            "input": {
                "fields": [
                    "manufacturer__not_found"
                ],
                "operation": "exclude_fields"
            }
        }
    ],
    "description": "Reject excluded field paths that do not correspond to fields in the nested representation."
}
```

---

### Feature 5: Expand Related Resources

**As a developer**, I want to request related data only when it is needed, so I can balance compact default payloads with rich nested responses.

**Expected Behavior / Usage:**

The adapter input uses `operation: "expand_resources"`. Without expansion instructions, the owner representation includes its own fields and a relation [a set of allowed field path patterns (consult the field mapping docs)]entifier for its organization. `expand` fully embeds named related resources; nested paths such as `cars__model__manufacturer` expand each intermediate resource until the leaf. `expand_[a set of allowed field path patterns (consult the field mapping docs)]_only` emits only [a set of allowed field path patterns (consult the field mapping docs)]entifiers for collection leaves while fully expanding intermediate parents when needed. Some expanded fields can represent additional information about the current record or calculated relation data. The output is a single JSON object followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature5_expand_related_resources.json`

```json
{
    "cases": [
        {
            "expected_output": "{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"Tyrell\",\"organization_[a set of allowed field path patterns (consult the field mapping docs)]\":1}\n",
            "input": {
                "operation": "expand_resources"
            }
        },
        {
            "expected_output": "{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"Tyrell\",\"organization\":{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"E Corp\"},\"organization_[a set of allowed field path patterns (consult the field mapping docs)]\":1}\n",
            "input": {
                "expand": [
                    "organization"
                ],
                "operation": "expand_resources"
            }
        },
        {
            "expected_output": "{\"cars\":[1],\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"Tyrell\",\"organization_[a set of allowed field path patterns (consult the field mapping docs)]\":1}\n",
            "input": {
                "expand_[a set of allowed field path patterns (consult the field mapping docs)]_only": [
                    "cars"
                ],
                "operation": "expand_resources"
            }
        },
        {
            "expected_output": "{\"cars\":[{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"model\":{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"manufacturer\":{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"Tesla\"},\"manufacturer_[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"Model S\"},\"model_[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"variant\":\"P100D\"}],\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"Tyrell\",\"organization_[a set of allowed field path patterns (consult the field mapping docs)]\":1}\n",
            "input": {
                "expand": [
                    "cars__model__manufacturer"
                ],
                "operation": "expand_resources"
            }
        },
        {
            "expected_output": "{\"cars\":[{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"model\":{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"manufacturer_[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"Model S\",\"skus\":[1,2]},\"model_[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"variant\":\"P100D\"}],\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"Tyrell\",\"organization_[a set of allowed field path patterns (consult the field mapping docs)]\":1}\n",
            "input": {
                "expand_[a set of allowed field path patterns (consult the field mapping docs)]_only": [
                    "cars__model__skus"
                ],
                "operation": "expand_resources"
            }
        },
        {
            "expected_output": "{\"is_model\":false,\"sku\":{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"model_[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"variant\":\"P100D\"}}\n",
            "input": {
                "expand": [
                    "sku"
                ],
                "operation": "expand_resources",
                "profile": "plain_object"
            }
        }
    ],
    "description": "Serialize a base owner record while expanding requested related resources fully, as [a set of allowed field path patterns (consult the field mapping docs)]entifiers only for collection leaves, or as additional same-record information."
}
```

---

### Feature 6: Val[a set of allowed field path patterns (consult the field mapping docs)]ate Expansion Instructions

**As a developer**, I want to val[a set of allowed field path patterns (consult the field mapping docs)]ate expansion paths before producing a response, so I can catch impossible or unsafe expansion requests deterministically.

**Expected Behavior / Usage:**

The adapter input uses `operation: "expand_resources"`. Expansion paths are val[a set of allowed field path patterns (consult the field mapping docs)]ated by default. Too-deep paths produce `{"error":"expand_depth_exceeded"}`. Unknown expansion paths produce `{"error":"unknown_field"}`. Identifier-only expansion is val[a set of allowed field path patterns (consult the field mapping docs)] only for supported collection leaves; unsupported targets produce `{"error":"inval[a set of allowed field path patterns (consult the field mapping docs)]_field_selection"}`. If `val[a set of allowed field path patterns (consult the field mapping docs)]ate_expand_instructions` is false, unknown instructions are ignored while val[a set of allowed field path patterns (consult the field mapping docs)] instructions still apply. All errors are normalized JSON objects followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature6_val[a set of allowed field path patterns (consult the field mapping docs)]ate_expansion_instructions.json`

```json
{
    "cases": [
        {
            "expected_output": "{\"error\":\"expand_depth_exceeded\"}\n",
            "input": {
                "expand": [
                    "cars__model__manufacturer__models"
                ],
                "operation": "expand_resources"
            }
        },
        {
            "expected_output": "{\"error\":\"inval[a set of allowed field path patterns (consult the field mapping docs)]_field_selection\"}\n",
            "input": {
                "expand_[a set of allowed field path patterns (consult the field mapping docs)]_only": [
                    "organization"
                ],
                "operation": "expand_resources"
            }
        },
        {
            "expected_output": "{\"error\":\"unknown_field\"}\n",
            "input": {
                "expand": [
                    "not_found"
                ],
                "operation": "expand_resources"
            }
        },
        {
            "expected_output": "{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"Tyrell\",\"organization\":{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"E Corp\"},\"organization_[a set of allowed field path patterns (consult the field mapping docs)]\":1}\n",
            "input": {
                "expand": [
                    "organization",
                    "not_found"
                ],
                "operation": "expand_resources",
                "val[a set of allowed field path patterns (consult the field mapping docs)]ate_expand_instructions": false
            }
        }
    ],
    "description": "Val[a set of allowed field path patterns (consult the field mapping docs)]ate expansion paths and expansion depth unless val[a set of allowed field path patterns (consult the field mapping docs)]ation is explicitly disabled."
}
```

---

### Feature 7: Deserialize Expandable Relations

**As a developer**, I want to val[a set of allowed field path patterns (consult the field mapping docs)]ate write payloads containing relation [a set of allowed field path patterns (consult the field mapping docs)]entifiers, so I can control whether relation [a set of allowed field path patterns (consult the field mapping docs)]entifiers are ignored or resolved during input val[a set of allowed field path patterns (consult the field mapping docs)]ation.

**Expected Behavior / Usage:**

The adapter input uses `operation: "val[a set of allowed field path patterns (consult the field mapping docs)]ate_write"`, a `profile` mode, and a `data` object. For read-only relation handling, relation [a set of allowed field path patterns (consult the field mapping docs)]entifier inputs are ignored and only writable scalar data is returned as `val[a set of allowed field path patterns (consult the field mapping docs)]ated_data`. For writable relation handling, the relation [a set of allowed field path patterns (consult the field mapping docs)]entifier is retained and resolved to a target record summary with `record_type`, `[a set of allowed field path patterns (consult the field mapping docs)]`, and `name`. Missing required writable relation [a set of allowed field path patterns (consult the field mapping docs)]entifiers produce a val[a set of allowed field path patterns (consult the field mapping docs)]ation error object. The output is a single JSON object followed by a newline and includes `is_val[a set of allowed field path patterns (consult the field mapping docs)]`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_deserialize_expandable_relations.json`

```json
{
    "cases": [
        {
            "expected_output": "{\"is_val[a set of allowed field path patterns (consult the field mapping docs)]\":true,\"val[a set of allowed field path patterns (consult the field mapping docs)]ated_data\":{\"name\":\"Ka\"}}\n",
            "input": {
                "data": {
                    "manufacturer_[a set of allowed field path patterns (consult the field mapping docs)]": 1,
                    "name": "Ka"
                },
                "operation": "val[a set of allowed field path patterns (consult the field mapping docs)]ate_write",
                "profile": "read_only_relation"
            }
        },
        {
            "expected_output": "{\"is_val[a set of allowed field path patterns (consult the field mapping docs)]\":true,\"val[a set of allowed field path patterns (consult the field mapping docs)]ated_data\":{\"manufacturer_[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"manufacturer_[a set of allowed field path patterns (consult the field mapping docs)]_resolved\":{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"Tesla\",\"record_type\":\"manufacturer\"},\"name\":\"Ka\"}}\n",
            "input": {
                "data": {
                    "manufacturer_[a set of allowed field path patterns (consult the field mapping docs)]": 1,
                    "name": "Ka"
                },
                "operation": "val[a set of allowed field path patterns (consult the field mapping docs)]ate_write",
                "profile": "writable_relation"
            }
        },
        {
            "expected_output": "{\"errors\":{\"manufacturer_[a set of allowed field path patterns (consult the field mapping docs)]\":[\"This field is required.\"]},\"is_val[a set of allowed field path patterns (consult the field mapping docs)]\":false}\n",
            "input": {
                "data": {
                    "name": "Ka"
                },
                "operation": "val[a set of allowed field path patterns (consult the field mapping docs)]ate_write",
                "profile": "writable_relation"
            }
        }
    ],
    "description": "Val[a set of allowed field path patterns (consult the field mapping docs)]ate write input for expandable relations, leaving read-only relation [a set of allowed field path patterns (consult the field mapping docs)]entifiers out of val[a set of allowed field path patterns (consult the field mapping docs)]ated data and resolving writable relation [a set of allowed field path patterns (consult the field mapping docs)]entifiers to their target records."
}
```

---

### Feature 8: External Identifier Fields

**As a developer**, I want to convert internal numeric [a set of allowed field path patterns (consult the field mapping docs)]entifiers to opaque external [a set of allowed field path patterns (consult the field mapping docs)]entifiers and back, so I can avo[a set of allowed field path patterns (consult the field mapping docs)] exposing raw database [a set of allowed field path patterns (consult the field mapping docs)]entifiers in API payloads.

**Expected Behavior / Usage:**

The adapter input uses `operation: "external_[a set of allowed field path patterns (consult the field mapping docs)]entifier"`. Encode modes return an opaque `external_[a set of allowed field path patterns (consult the field mapping docs)]` or a serialized object whose `[a set of allowed field path patterns (consult the field mapping docs)]` is opaque. Decode modes accept `external_[a set of allowed field path patterns (consult the field mapping docs)]` and return the matching numeric `internal_[a set of allowed field path patterns (consult the field mapping docs)]`. If the external [a set of allowed field path patterns (consult the field mapping docs)]entifier is malformed or does not match the expected record category, stdout is the normalized JSON error `{"error":"inval[a set of allowed field path patterns (consult the field mapping docs)]_external_[a set of allowed field path patterns (consult the field mapping docs)]"}` followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature8_external_[a set of allowed field path patterns (consult the field mapping docs)]entifier_fields.json`

```json
{
    "cases": [
        {
            "expected_output": "{\"external_[a set of allowed field path patterns (consult the field mapping docs)]\":\"4Nt1\"}\n",
            "input": {
                "mode": "encode_field",
                "operation": "external_[a set of allowed field path patterns (consult the field mapping docs)]entifier"
            }
        },
        {
            "expected_output": "{\"[a set of allowed field path patterns (consult the field mapping docs)]\":\"4Nt1\",\"name\":\"Model S\"}\n",
            "input": {
                "mode": "encode_record",
                "operation": "external_[a set of allowed field path patterns (consult the field mapping docs)]entifier"
            }
        },
        {
            "expected_output": "{\"internal_[a set of allowed field path patterns (consult the field mapping docs)]\":1}\n",
            "input": {
                "external_[a set of allowed field path patterns (consult the field mapping docs)]": "4Nt1",
                "mode": "decode_field",
                "operation": "external_[a set of allowed field path patterns (consult the field mapping docs)]entifier"
            }
        },
        {
            "expected_output": "{\"error\":\"inval[a set of allowed field path patterns (consult the field mapping docs)]_external_[a set of allowed field path patterns (consult the field mapping docs)]\"}\n",
            "input": {
                "external_[a set of allowed field path patterns (consult the field mapping docs)]": "abc123",
                "mode": "decode_field",
                "operation": "external_[a set of allowed field path patterns (consult the field mapping docs)]entifier"
            }
        }
    ],
    "description": "Convert internal numeric [a set of allowed field path patterns (consult the field mapping docs)]entifiers to opaque external [a set of allowed field path patterns (consult the field mapping docs)]entifiers and convert matching external [a set of allowed field path patterns (consult the field mapping docs)]entifiers back to internal [a set of allowed field path patterns (consult the field mapping docs)]entifiers."
}
```

---

### Feature 9: External Identifier Hyperlinks

**As a developer**, I want to build relation URLs using opaque external [a set of allowed field path patterns (consult the field mapping docs)]entifiers, so I can keep hyperlinked API output consistent with external ID fields.

**Expected Behavior / Usage:**

The adapter input uses `operation: "external_link"` and a record `state`. For a saved record, stdout contains a fully routed URL whose path includes the opaque external [a set of allowed field path patterns (consult the field mapping docs)]entifier. For an unsaved record without a persistent [a set of allowed field path patterns (consult the field mapping docs)]entifier, stdout contains `null` for the URL. The output is a single JSON object followed by a newline and includes framework-observable URL text.

**Test Cases:** `rcb_tests/public_test_cases/feature9_external_[a set of allowed field path patterns (consult the field mapping docs)]entifier_hyperlinks.json`

```json
{
    "cases": [
        {
            "expected_output": "{\"manufacturer_url\":\"http://testserver/models/AMTw/\"}\n",
            "input": {
                "operation": "external_link",
                "state": "saved"
            }
        },
        {
            "expected_output": "{\"manufacturer_url\":null}\n",
            "input": {
                "operation": "external_link",
                "state": "unsaved"
            }
        }
    ],
    "description": "Render relation hyperlinks with the external [a set of allowed field path patterns (consult the field mapping docs)]entifier in the routed URL and return a null link for unsaved records."
}
```

---

### Feature 10: Child Serializer Context

**As a developer**, I want to track nested path names and pass parent context into calculated child serialization, so I can make nested field filtering and custom child rendering behave consistently.

**Expected Behavior / Usage:**

The adapter input uses `operation: "child_path"` with a `selector` to inspect the path of a serializer node, or `operation: "calculated_child"` with a child [a set of allowed field path patterns (consult the field mapping docs)]entifier and context label. Hierarchy output is the delimiter-joined path from the root, with the root represented by an empty string. Calculated child output preserves the child instance data, reports the child hierarchy, and includes the label inherited from the parent context.

**Test Cases:** `rcb_tests/public_test_cases/feature10_child_serializer_context.json`

```json
{
    "cases": [
        {
            "expected_output": "{\"hierarchy\":\"\"}\n",
            "input": {
                "operation": "child_path",
                "selector": "root"
            }
        },
        {
            "expected_output": "{\"hierarchy\":\"skus__owners__organization\"}\n",
            "input": {
                "operation": "child_path",
                "selector": "skus__owners__organization"
            }
        },
        {
            "expected_output": "{\"child\":{\"context_label\":\"Label\",\"hierarchy\":\"child\",\"[a set of allowed field path patterns (consult the field mapping docs)]\":1}}\n",
            "input": {
                "child_[a set of allowed field path patterns (consult the field mapping docs)]": 1,
                "label": "Label",
                "operation": "calculated_child"
            }
        }
    ],
    "description": "Track nested serializer path names and preserve parent context when rendering a calculated child serializer."
}
```

---

### Feature 11: Build Serializer Context From Requests

**As a developer**, I want to derive serializer instructions from API view defaults and HTTP query parameters, so I can let endpoint configuration and request parameters share one execution context.

**Expected Behavior / Usage:**

The adapter input uses `operation: "request_context"`. View-level defaults may prov[a set of allowed field path patterns (consult the field mapping docs)]e expansion, [a set of allowed field path patterns (consult the field mapping docs)]entifier-only expansion, exclusion, and selection lists. HTTP query parameters may prov[a set of allowed field path patterns (consult the field mapping docs)]e the same instructions either as repeated list values or comma-delimited strings. Query parameters overr[a set of allowed field path patterns (consult the field mapping docs)]e view defaults unless query parsing is disabled, in which case defaults are preserved. The output includes framework-observable context signals: request path, format, view class name, and sorted instruction arrays.

**Test Cases:** `rcb_tests/public_test_cases/feature11_build_serializer_context_from_request.json`

```json
{
    "cases": [
        {
            "expected_output": "{\"exclude\":[],\"expand\":[],\"expand_[a set of allowed field path patterns (consult the field mapping docs)]_only\":[],\"format\":\"json\",\"only\":[],\"request_path\":\"/\",\"view_class\":\"View\"}\n",
            "input": {
                "operation": "request_context"
            }
        },
        {
            "expected_output": "{\"exclude\":[\"c\"],\"expand\":[\"a\",\"a1\"],\"expand_[a set of allowed field path patterns (consult the field mapping docs)]_only\":[\"b\"],\"format\":\"json\",\"only\":[\"d\",\"d1\",\"d2\"],\"request_path\":\"/\",\"view_class\":\"View\"}\n",
            "input": {
                "operation": "request_context",
                "query": {
                    "exclude": [
                        "c"
                    ],
                    "expand": [
                        "a",
                        "a1"
                    ],
                    "expand_[a set of allowed field path patterns (consult the field mapping docs)]_only": [
                        "b"
                    ],
                    "only": [
                        "d",
                        "d1",
                        "d2"
                    ]
                }
            }
        },
        {
            "expected_output": "{\"exclude\":[\"c\"],\"expand\":[\"a\",\"a1\"],\"expand_[a set of allowed field path patterns (consult the field mapping docs)]_only\":[\"b\"],\"format\":\"json\",\"only\":[\"d\",\"d1\",\"d2\"],\"request_path\":\"/\",\"view_class\":\"View\"}\n",
            "input": {
                "operation": "request_context",
                "query": {
                    "exclude": "c",
                    "expand": "a,a1",
                    "expand_[a set of allowed field path patterns (consult the field mapping docs)]_only": "b",
                    "only": "d,d1,d2"
                }
            }
        },
        {
            "expected_output": "{\"exclude\":[\"overr[a set of allowed field path patterns (consult the field mapping docs)]e_c\"],\"expand\":[\"overr[a set of allowed field path patterns (consult the field mapping docs)]e_a\"],\"expand_[a set of allowed field path patterns (consult the field mapping docs)]_only\":[\"overr[a set of allowed field path patterns (consult the field mapping docs)]e_b\"],\"format\":\"json\",\"only\":[\"overr[a set of allowed field path patterns (consult the field mapping docs)]e_d\"],\"request_path\":\"/\",\"view_class\":\"View\"}\n",
            "input": {
                "attribute_exclude": [
                    "c"
                ],
                "attribute_expand": [
                    "a",
                    "a1"
                ],
                "attribute_expand_[a set of allowed field path patterns (consult the field mapping docs)]_only": [
                    "b"
                ],
                "attribute_only": [
                    "d",
                    "d1",
                    "d2"
                ],
                "operation": "request_context",
                "query": {
                    "exclude": "overr[a set of allowed field path patterns (consult the field mapping docs)]e_c",
                    "expand": "overr[a set of allowed field path patterns (consult the field mapping docs)]e_a",
                    "expand_[a set of allowed field path patterns (consult the field mapping docs)]_only": "overr[a set of allowed field path patterns (consult the field mapping docs)]e_b",
                    "only": "overr[a set of allowed field path patterns (consult the field mapping docs)]e_d"
                }
            }
        },
        {
            "expected_output": "{\"exclude\":[\"c\"],\"expand\":[\"a\",\"a1\"],\"expand_[a set of allowed field path patterns (consult the field mapping docs)]_only\":[\"b\"],\"format\":\"json\",\"only\":[\"d\",\"d1\",\"d2\"],\"request_path\":\"/\",\"view_class\":\"View\"}\n",
            "input": {
                "attribute_exclude": [
                    "c"
                ],
                "attribute_expand": [
                    "a",
                    "a1"
                ],
                "attribute_expand_[a set of allowed field path patterns (consult the field mapping docs)]_only": [
                    "b"
                ],
                "attribute_only": [
                    "d",
                    "d1",
                    "d2"
                ],
                "operation": "request_context",
                "query": {
                    "exclude": "overr[a set of allowed field path patterns (consult the field mapping docs)]e_c",
                    "expand": "overr[a set of allowed field path patterns (consult the field mapping docs)]e_a",
                    "expand_[a set of allowed field path patterns (consult the field mapping docs)]_only": "overr[a set of allowed field path patterns (consult the field mapping docs)]e_b",
                    "only": "overr[a set of allowed field path patterns (consult the field mapping docs)]e_d"
                },
                "query_params_enabled": false
            }
        }
    ],
    "description": "Build serializer context from view defaults and HTTP query parameters, including comma-delimited parameters and overr[a set of allowed field path patterns (consult the field mapping docs)]e behavior."
}
```

---

### Feature 12: Apply Extensions In API Responses

**As a developer**, I want to apply request instructions through a real API view response, so I can verify that serialization extensions work through the web framework boundary.

**Expected Behavior / Usage:**

The adapter input uses `operation: "api_response"` with optional query parameters, or `operation: "external_lookup"` with a lookup mode. API response output includes `status_code` and response `data`, proving the behavior was exercised through the view layer. Query-supplied expand, select, and exclude instructions shape the returned data. External [a set of allowed field path patterns (consult the field mapping docs)]entifier lookup returns status 200 and the target data when the lookup matches the expected record category; a lookup for another category returns status 404 with a not-found payload.

**Test Cases:** `rcb_tests/public_test_cases/feature12_apply_extensions_in_api_responses.json`

```json
{
    "cases": [
        {
            "expected_output": "{\"data\":{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"Tyrell\",\"organization_[a set of allowed field path patterns (consult the field mapping docs)]\":1},\"status_code\":200}\n",
            "input": {
                "operation": "api_response"
            }
        },
        {
            "expected_output": "{\"data\":{\"cars\":[{\"variant\":\"P100D\"}]},\"status_code\":200}\n",
            "input": {
                "operation": "api_response",
                "query": {
                    "exclude": "cars__[a set of allowed field path patterns (consult the field mapping docs)]",
                    "expand": "cars",
                    "only": "cars"
                }
            }
        },
        {
            "expected_output": "{\"data\":{\"[a set of allowed field path patterns (consult the field mapping docs)]\":1,\"name\":\"Tyrell\",\"organization_[a set of allowed field path patterns (consult the field mapping docs)]\":\"mbcN\"},\"lookup\":\"94Fp\",\"status_code\":200}\n",
            "input": {
                "lookup": "owner_external_[a set of allowed field path patterns (consult the field mapping docs)]",
                "operation": "external_lookup"
            }
        },
        {
            "expected_output": "{\"data\":{\"detail\":\"Not found.\"},\"lookup\":\"XPh7\",\"status_code\":404}\n",
            "input": {
                "lookup": "other_model_external_[a set of allowed field path patterns (consult the field mapping docs)]",
                "operation": "external_lookup"
            }
        }
    ],
    "description": "Apply request-supplied extension instructions through an API view response and preserve framework-visible response signals."
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and [a set of allowed field path patterns (consult the field mapping docs)]eally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- check input.media-type attribute overrides in context builder
- refer to the owner lookup result in integration tests
