## Product Requirement Document

# Schema-to-Type Declarations - Generate Client Data Contracts from Server Model Metadata

## Project Goal

Build a schema-to-TypeScript declaration generator that allows developers to derive client-side data contracts from server-side data model metadata without manually duplicating database fields, computed attributes, relationships, and constant sets.

---

## Background & Problem

Without this library/tool, developers are forced to hand-write TypeScript interfaces and keep them synchronized with server-side models, database columns, relationship metadata, and enum-like constants. This leads to repetitive code, stale contracts, incorrect nullability, missing hidden-field rules, and inconsistent type mappings.

With this library/tool, developers can request definitions or structured metadata for discovered models and receive deterministic stdout that reflects the same fields, relationships, constants, and configuration choices exercised by the source project tests.

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

### Feature 1: Model Discovery and Inspection

**As a developer**, I want to locate data model definitions and confirm that each requested model has inspectable schema information, so I can generate definitions only for valid concrete models and safely skip non-generatable targets.

**Expected Behavior / Usage:**

This feature group is split into leaf behaviors so each contract can be tested independently from stdin JSON to exact stdout.

*1.1 Project model discovery — Given a request to discover models, the adapter prints a count line followed by one `model=<name>` line for each discovered concrete data model*

Given a request to discover models, the adapter prints a count line followed by one `model=<name>` line for each discovered concrete data model. When a subject is supplied, discovery narrows to that one model while preserving the same output shape.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_model_discovery.json`

```json
{
    "description": "Discovers all eligible sample data models in the project or narrows discovery to a requested model.",
    "cases": [
        {
            "input": {
                "request": "discover_models",
                "subject": "all"
            },
            "expected_output": "count=4\nmodel=Complex\nmodel=Pivot\nmodel=User\nmodel=Team\n"
        }
    ]
}
```

*1.2 Model inspection status — Given a request to inspect one subject, the adapter prints whether it was inspected or null*

Given a request to inspect one subject, the adapter prints whether it was inspected or null. Concrete inspected subjects include framework-observable schema signals: table name, attribute count, and relationship count. Abstract or missing subjects print `result=null`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_model_inspection.json`

```json
{
    "description": "Inspects a sample data model and reports whether schema attributes and relationships are available for generation.",
    "cases": [
        {
            "input": {
                "request": "inspect_model",
                "subject": "user"
            },
            "expected_output": "result=inspected\ntable=users\nattributes=12\nrelations=1\n"
        }
    ]
}
```

---

### Feature 2: Definition Generation Outputs

**As a developer**, I want to generate TypeScript-compatible definitions from database model metadata, so I can keep client-side data contracts synchronized with server-side schemas.

**Expected Behavior / Usage:**

This feature group is split into leaf behaviors so each contract can be tested independently from stdin JSON to exact stdout.

*2.1 Default interface output — Given a sample user-shaped model and no switches, the adapter prints a TypeScript interface containing persisted columns, computed attributes, relationships, and string-literal constant definitions*

Given a sample user-shaped model and no switches, the adapter prints a TypeScript interface containing persisted columns, computed attributes, relationships, and string-literal constant definitions. Optional fields use `?`, nullable fields include `| null`, and the output is the exact declaration text.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_default_interface_output.json`

```json
{
    "description": "Generates a TypeScript interface for a sample user-shaped data model, including columns, computed fields, relationships, and literal union constants.",
    "cases": [
        {
            "input": {
                "request": "generate_definitions",
                "subject": "user",
                "options": {}
            },
            "expected_output": "export interface User {\n  // columns\n  id: number\n  name: string\n  email: string\n  email_verified_at: string | null\n  password?: string\n  remember_token?: string | null\n  created_at: string | null\n  updated_at: string | null\n  // mutators\n  role_traditional: string\n  role_new: string\n  role_enum: Roles\n  role_enum_traditional: Roles\n  // relations\n  notifications: DatabaseNotification[]\n}\n\nconst Roles = {\n  /** Can do anything */\n  ADMIN: 'admin',\n  /** Standard readonly */\n  USER: 'user',\n  /** Value that needs string escaping */\n  USERCLASS: 'App\\\\Models\\\\User',\n} as const;\n\nexport type Roles = typeof Roles[keyof typeof Roles]\n"
        }
    ]
}
```

*2.2 Complex field type output — Given a model containing many database field categories, the adapter prints a TypeScript interface where each field is mapped to its TypeScript representation*

Given a model containing many database field categories, the adapter prints a TypeScript interface where each field is mapped to its TypeScript representation. Known numeric, string, boolean, object, date/time, identifier, and [a specific compound value based on DB type and whether it's a boolean flag — consult schema docs] categories must be visible in the output.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_complex_type_mapping_output.json`

```json
{
    "description": "Generates a TypeScript interface for a model containing many database field categories and maps each field to the corresponding TypeScript type.",
    "cases": [
        {
            "input": {
                "request": "generate_definitions",
                "subject": "complex",
                "options": {}
            },
            "expected_output": "export interface Complex {\n  // columns\n  id: number\n  [a specific compound value based on DB type and whether it's a boolean flag — consult schema docs]: number\n  [a specific compound value based on DB type and whether it's a boolean flag — consult schema docs]: [a specific compound value based on DB type and whether it's a boolean flag — consult schema docs]\n  boolean: boolean\n  char: string\n  date_time: string\n  immutable_date_time: string\n  immutable_custom_date_time: string\n  date: string\n  immutable_date: string\n  decimal: number\n  double: number\n  enum: string\n  float: number\n  integer: number\n  ip_address: string\n  json: Record<string, [a specific compound value based on DB type and whether it's a boolean flag — consult schema docs]>\n  jsonb: Record<string, [a specific compound value based on DB type and whether it's a boolean flag — consult schema docs]>\n  long_text: string\n  mac_address: string\n  medium_integer: number\n  medium_text: string\n  small_integer: number\n  string: string\n  casted_uppercase_string: [a specific compound value based on DB type and whether it's a boolean flag — consult schema docs]\n  text: string\n  time: string\n  timestamp: string\n  year: number\n  uuid: string\n  ulid: string\n  created_at: string | null\n  updated_at: string | null\n  deleted_at: string | null\n}\n"
        }
    ]
}
```

*2.3 Global namespace output — Given a request for namespace-wrapped output, the adapter prints TypeScript declarations inside the configured global namespace while preserving the same model fields and enum definitions.*

Given a request for namespace-wrapped output, the adapter prints TypeScript declarations inside the configured global namespace while preserving the same model fields and enum definitions.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_global_namespace_output.json`

```json
{
    "description": "Wraps generated interfaces in a configured global namespace when namespace output is requested.",
    "cases": [
        {
            "input": {
                "request": "generate_definitions",
                "subject": "user",
                "options": {
                    "global": true
                },
                "config": {
                    "global_namespace": "App.Models"
                }
            },
            "expected_output": "export {}\ndeclare global {\n  export namespace App.Models {\n\n    export interface User {\n      // columns\n      id: number\n      name: string\n      email: string\n      email_verified_at: string | null\n      password?: string\n      remember_token?: string | null\n      created_at: string | null\n      updated_at: string | null\n      // mutators\n      role_traditional: string\n      role_new: string\n      role_enum: Roles\n      role_enum_traditional: Roles\n      // relations\n      notifications: DatabaseNotification[]\n    }\n\n    const Roles = {\n      /** Can do anything */\n      ADMIN: 'admin',\n      /** Standard readonly */\n      USER: 'user',\n      /** Value that needs string escaping */\n      USERCLASS: 'App\\\\Models\\\\User',\n    } as const;\n\n    export type Roles = typeof Roles[keyof typeof Roles]\n\n  }\n}\n"
        }
    ]
}
```

*2.4 JSON metadata output — Given a request for structured metadata, the adapter prints JSON with `interfaces`, `relations`, and `enums` sections*

Given a request for structured metadata, the adapter prints JSON with `interfaces`, `relations`, and `enums` sections. Interface entries list field names and types, relationship entries preserve related type metadata, and enum entries preserve generated enum declaration text.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_json_metadata_output.json`

```json
{
    "description": "Generates structured JSON metadata for a sample model when JSON output is requested, including interface fields, relations, and enum metadata.",
    "cases": [
        {
            "input": {
                "request": "generate_definitions",
                "subject": "user",
                "options": {
                    "json": true,
                    "use_enums": true
                }
            },
            "expected_output": "{\n    \"interfaces\": {\n        \"User\": [\n            {\n                \"name\": \"id\",\n                \"type\": \"number\"\n            },\n            {\n                \"name\": \"name\",\n                \"type\": \"string\"\n            },\n            {\n                \"name\": \"email\",\n                \"type\": \"string\"\n            },\n            {\n                \"name\": \"email_verified_at\",\n                \"type\": \"string | null\"\n            },\n            {\n                \"name\": \"password?\",\n                \"type\": \"string\"\n            },\n            {\n                \"name\": \"remember_token?\",\n                \"type\": \"string | null\"\n            },\n            {\n                \"name\": \"created_at\",\n                \"type\": \"string | null\"\n            },\n            {\n                \"name\": \"updated_at\",\n                \"type\": \"string | null\"\n            },\n            {\n                \"name\": \"role_traditional\",\n                \"type\": \"string\"\n            },\n            {\n                \"name\": \"role_new\",\n                \"type\": \"string\"\n            },\n            {\n                \"name\": \"role_enum\",\n                \"type\": \"RolesEnum\"\n            },\n            {\n                \"name\": \"role_enum_traditional\",\n                \"type\": \"RolesEnum\"\n            }\n        ]\n    },\n    \"relations\": [\n        {\n            \"DatabaseNotification[]\": {\n                \"name\": \"notifications\",\n                \"type\": \"export type DatabaseNotification[] = Array<User>\"\n            }\n        }\n    ],\n    \"enums\": [\n        {\n            \"Roles\": {\n                \"name\": \"Roles\",\n                \"type\": \"export const enum Roles {\\n  \\/** Can do anything *\\/\\n  ADMIN = 'admin',\\n  \\/** Standard readonly *\\/\\n  USER = 'user',\\n  \\/** Value that needs string escaping *\\/\\n  USERCLASS = 'App\\\\\\\\Models\\\\\\\\User',\\n}\\n\\nexport type RolesEnum = `${Roles}`\\n\\n\"\n            }\n        },\n        {\n            \"Roles\": {\n                \"name\": \"Roles\",\n                \"type\": \"export const enum Roles {\\n  \\/** Can do anything *\\/\\n  ADMIN = 'admin',\\n  \\/** Standard readonly *\\/\\n  USER = 'user',\\n  \\/** Value that needs string escaping *\\/\\n  USERCLASS = 'App\\\\\\\\Models\\\\\\\\User',\\n}\\n\\nexport type RolesEnum = `${Roles}`\\n\\n\"\n            }\n        }\n    ]\n}\n"
        }
    ]
}
```

---

### Feature 3: Reusable Declaration Fragment Rendering

**As a developer**, I want to render reusable declaration fragments independently, so I can compose full definition output from predictable field and enum fragments.

**Expected Behavior / Usage:**

This feature group is split into leaf behaviors so each contract can be tested independently from stdin JSON to exact stdout.

*3.1 Enum declaration rendering — Given a backed string constant set, the adapter prints either TypeScript declaration text or structured metadata*

Given a backed string constant set, the adapter prints either TypeScript declaration text or structured metadata. Text output preserves comments, constant names, escaped string values, and the exported union type. Metadata output includes the enum name and declaration body.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_enum_rendering.json`

```json
{
    "description": "Renders backed string constants as TypeScript declarations while preserving descriptions and escaped string values.",
    "cases": [
        {
            "input": {
                "request": "enum_definition",
                "json": false
            },
            "expected_output": "const Roles = {\n  /** Can do anything */\n  ADMIN: 'admin',\n  /** Standard readonly */\n  USER: 'user',\n  /** Value that needs string escaping */\n  USERCLASS: 'App\\\\Models\\\\User',\n} as const;\n\nexport type Roles = typeof Roles[keyof typeof Roles]\n\n"
        }
    ]
}
```

*3.2 Relationship field rendering — Given relationship metadata, the adapter prints a TypeScript property or structured field metadata*

Given relationship metadata, the adapter prints a TypeScript property or structured field metadata. The output reflects the relationship name, related resource type, array cardinality, optional marker when requested, pluralized resource name when requested, and custom indentation when requested.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_relationship_rendering.json`

```json
{
    "description": "Renders relationship fields as TypeScript properties or structured field metadata, with optionality and plural resource-name variants.",
    "cases": [
        {
            "input": {
                "request": "relationship_field",
                "name": "notifications",
                "related_resource": "DatabaseNotification",
                "json": false
            },
            "expected_output": "  notifications: DatabaseNotification[]\n"
        },
        {
            "input": {
                "request": "relationship_field",
                "name": "notifications",
                "related_resource": "DatabaseNotification",
                "json": true
            },
            "expected_output": "[the exact field key and type combo used in the namespace output]notifications\n[the exact field key and type combo used in the namespace output]DatabaseNotification[]\n"
        }
    ]
}
```

---

### Feature 4: Generation and Mapping Configuration

**As a developer**, I want to apply caller-selected generation and mapping choices, so I can produce definitions that match project-specific serialization conventions.

**Expected Behavior / Usage:**

This feature group is split into leaf behaviors so each contract can be tested independently from stdin JSON to exact stdout.

*4.1 Generation switches — Given generation switches, the adapter prints the resulting TypeScript declaration text*

Given generation switches, the adapter prints the resulting TypeScript declaration text. Supported behaviors include editable subset aliases, enum style changes, plural resource names, relationship exclusion, optional relationship fields, hidden-field inclusion control, date-object timestamp types, nullable fields marked optional, and API resource wrapping.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_generation_options.json`

```json
{
    "description": "Applies generation switches that alter the emitted interface, including editable subsets, enum style, plural names, relation inclusion, hidden fields, date object timestamps, nullable optionality, and API resource wrapping.",
    "cases": [
        {
            "input": {
                "request": "generate_definitions",
                "subject": "user",
                "options": {
                    "fillable_subset": true,
                    "fillable_suffix": "Editable"
                }
            },
            "expected_output": "export interface User {\n  // columns\n  id: number\n  name: string\n  email: string\n  email_verified_at: string | null\n  password?: string\n  remember_token?: string | null\n  created_at: string | null\n  updated_at: string | null\n  // mutators\n  role_traditional: string\n  role_new: string\n  role_enum: Roles\n  role_enum_traditional: Roles\n  // relations\n  notifications: DatabaseNotification[]\n}\nexport type UserEditable = Pick<User, 'name' | 'email' | 'password' | 'role_traditional' | 'role_new'>\n\nconst Roles = {\n  /** Can do anything */\n  ADMIN: 'admin',\n  /** Standard readonly */\n  USER: 'user',\n  /** Value that needs string escaping */\n  USERCLASS: 'App\\\\Models\\\\User',\n} as const;\n\nexport type Roles = typeof Roles[keyof typeof Roles]\n"
        },
        {
            "input": {
                "request": "generate_definitions",
                "subject": "user",
                "options": {
                    "use_enums": true
                }
            },
            "expected_output": "export interface User {\n  // columns\n  id: number\n  name: string\n  email: string\n  email_verified_at: string | null\n  password?: string\n  remember_token?: string | null\n  created_at: string | null\n  updated_at: string | null\n  // mutators\n  role_traditional: string\n  role_new: string\n  role_enum: RolesEnum\n  role_enum_traditional: RolesEnum\n  // relations\n  notifications: DatabaseNotification[]\n}\n\nexport const enum Roles {\n  /** Can do anything */\n  ADMIN = 'admin',\n  /** Standard readonly */\n  USER = 'user',\n  /** Value that needs string escaping */\n  USERCLASS = 'App\\\\Models\\\\User',\n}\n\nexport type RolesEnum = `${Roles}`\n"
        }
    ]
}
```

*4.2 Type mapping configuration — Given raw type tokens and mapping configuration, the adapter prints the resolved TypeScript type or selected mapping lines*

Given raw type tokens and mapping configuration, the adapter prints the resolved TypeScript type or selected mapping lines. Nullable tokens append `| null`, [a specific compound value based on DB type and whether it's a boolean flag — consult schema docs] tokens become `[a specific compound value based on DB type and whether it's a boolean flag — consult schema docs]`, timestamp categories can become `Date`, and custom mappings can add or override entries.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_type_mapping_configuration.json`

```json
{
    "description": "Maps raw type tokens using default and user-provided mappings, including nullable tokens, [a specific compound value based on DB type and whether it's a boolean flag — consult schema docs] tokens, timestamp date-object mapping, and custom overrides.",
    "cases": [
        {
            "input": {
                "request": "map_type_token",
                "type_token": "B",
                "mappings": {
                    "a": "1",
                    "b": "2"
                }
            },
            "expected_output": "[the exact field key and type combo used in the namespace output]2\n"
        }
    ]
}
```

---

### Feature 5: Normalized Errors and Accessor Recognition

**As a developer**, I want to return stable adapter output for errors and computed attributes, so I can make black-box tests portable across implementation languages.

**Expected Behavior / Usage:**

This feature group is split into leaf behaviors so each contract can be tested independently from stdin JSON to exact stdout.

*5.1 Language-neutral error output — Given an invalid generation target, empty type token, or unresolved computed-attribute selector, the adapter prints a normalized `error=<category>` line*

Given an invalid generation target, empty type token, or unresolved computed-attribute selector, the adapter prints a normalized `error=<category>` line. It must not print host-language exception class names, stack traces, or runtime-generated message suffixes.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_error_normalization.json`

```json
{
    "description": "Reports language-neutral error categories when generation cannot find models, a type token is empty, or an accessor selector cannot be resolved.",
    "cases": [
        {
            "input": {
                "request": "generate_definitions",
                "subject": "missing_sample",
                "options": {}
            },
            "expected_output": "error=no_models_found\n"
        },
        {
            "input": {
                "request": "generate_definitions",
                "subject": "abstract_sample",
                "options": {}
            },
            "expected_output": "error=no_models_found\n"
        }
    ]
}
```

*5.2 Computed attribute selector recognition — Given a selector for a supported computed attribute style, the adapter prints the raw selector and `result=found`*

Given a selector for a supported computed attribute style, the adapter prints the raw selector and `result=found`. Both modern value-object style and legacy getter-style selectors are recognized through the same stdout contract.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_accessor_resolution.json`

```json
{
    "description": "Recognizes both modern and legacy computed attribute selectors on a sample model.",
    "cases": [
        {
            "input": {
                "request": "accessor_probe",
                "selector": "new_role_value"
            },
            "expected_output": "accessor=new_role_value\nresult=found\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- check how global enums are constructed in the namespace container
- refer to the global wrapper pattern used for all type definitions
