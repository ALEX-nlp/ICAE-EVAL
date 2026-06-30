## Product Requirement Document

# UML-to-Entity Modeling Toolkit - Parse diagrams into entity definitions and generator-ready outputs

## Project Goal

Build a UML-to-entity modeling tool that allows developers to parse supported UML/XMI diagrams, inspect field-type rules, generate entity configuration JSON, export textual model definitions, and assemble downstream generator invocations without manually translating diagrams into boilerplate entity files.

---

## Background & Problem

Without this tool, developers are forced to read diagram XML by hand, infer entity names, table names, field types, validations, relationships, and generation options, then duplicate that information in multiple textual and JSON formats. This leads to repetitive work, mismatched relationships, incorrect validation rules, and fragile command invocations.

With this tool, diagram metadata is parsed into stable model data, validated against storage-specific type rules, converted into generator-ready JSON, and optionally exported as a concise textual model document.

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

### Feature 1: Model Data Records

**As a developer**, I want to create normalized records for entities, fields, associations, enumerations, primitive types, and validations, so I can rely on consistent defaults and predictable supplied-value mapping.

**Expected Behavior / Usage:**

The input selects a model record category and optionally supplies a value object. The output is a JSON rendering of the constructed record, including default values when no values are supplied. Reserved entity names are reported as a normalized error object rather than exposing runtime exception details.

**Test Cases:** `rcb_tests/public_test_cases/feature1_data_records.json`

```json
{
    "description": "Construct model data records from supplied values or defaults and surface reserved-name failures as normalized errors.",
    "cases": [
        {
            "input": {
                "action": "data-object",
                "kind": "entity",
                "values": null
            },
            "expected_output": "{\n  \"comment\": \"\",\n  \"dto\": \"no\",\n  \"fields\": [],\n  \"name\": \"\",\n  \"pagination\": \"no\",\n  \"service\": \"no\",\n  \"tableName\": \"\"\n}\n"
        },
        {
            "input": {
                "action": "data-object",
                "kind": "entity",
                "values": {
                    "name": "Abc",
                    "comment": "42",
                    "dto": "yes",
                    "pagination": "always",
                    "service": "never",
                    "fields": [
                        1,
                        2
                    ],
                    "tableName": "something"
                }
            },
            "expected_output": "{\n  \"comment\": \"42\",\n  \"dto\": \"yes\",\n  \"fields\": [\n    1,\n    2\n  ],\n  \"name\": \"Abc\",\n  \"pagination\": \"always\",\n  \"service\": \"never\",\n  \"tableName\": \"something\"\n}\n"
        }
    ]
}
```

---

### Feature 2: Storage Type Registries

**As a developer**, I want to inspect supported field types and validations for a storage profile, so I can validate model fields before generation.

**Expected Behavior / Usage:**

The input names a storage profile and a registry query. Type-list queries output the supported field type names. Validation queries output the validation names allowed for a field type. Membership and validation-support queries output JSON booleans. Invalid field types are reported as a normalized unsupported_type error.

**Test Cases:** `rcb_tests/public_test_cases/feature2_type_registries.json`

```json
{
    "description": "Query supported field types and validation rules for each storage profile, including invalid type handling.",
    "cases": [
        {
            "input": {
                "action": "type-registry",
                "database": "sql",
                "query": "types"
            },
            "expected_output": "[\n  \"String\",\n  \"Integer\",\n  \"Long\",\n  \"BigDecimal\",\n  \"LocalDate\",\n  \"ZonedDateTime\",\n  \"Boolean\",\n  \"Enum\",\n  \"Blob\",\n  \"AnyBlob\",\n  \"ImageBlob\",\n  \"TextBlob\",\n  \"Float\",\n  \"Double\"\n]\n"
        },
        {
            "input": {
                "action": "type-registry",
                "database": "sql",
                "query": "validations",
                "type": "String"
            },
            "expected_output": "[\n  \"required\",\n  \"minlength\",\n  \"maxlength\",\n  \"pattern\"\n]\n"
        }
    ]
}
```

---

### Feature 3: Diagram Parsing

**As a developer**, I want to parse supported UML/XMI diagrams into normalized model metadata, so I can turn visual models into deterministic entity definitions.

**Expected Behavior / Usage:**

The input names a diagram file and storage profile. The output is JSON containing the parsed class names, per-class table names and field counts, parsed fields with types and validations, associations with cardinality/end names/required flags/comments, and discovered field type names. Output must preserve comments and normalize lower-cased field types where the original tests expect that behavior.

**Test Cases:** `rcb_tests/public_test_cases/feature3_diagram_parsing.json`

```json
{
    "description": "Parse XMI/UML diagrams into normalized classes, fields, associations, comments, required flags, and type names.",
    "cases": [
        {
            "input": {
                "action": "parse-diagram",
                "file": "./test/xmi/modelio.xmi",
                "database": "sql"
            },
            "expected_output": "Parser detected: MODELIO.\n\n{\n  \"parsed\": {\n    \"associations\": [\n      {\n        \"commentInFrom\": \"\",\n        \"commentInTo\": \"\",\n        \"from\": \"Country\",\n        \"injectedFieldInFrom\": \"region\",\n        \"requiredInFrom\": true,\n        \"requiredInTo\": true,\n        \"to\": \"Region\",\n        \"type\": \"one-to-one\"\n      },\n      {\n        \"commentInFrom\": \"\",\n        \"commentInTo\": \"\",\n        \"from\": \"Department\",\n        \"injectedFieldInFrom\": \"employee\",\n        \"requiredInFrom\": false,\n        \"requiredInTo\": false,\n        \"to\": \"Employee\",\n        \"type\": \"one-to-many\"\n      },\n      {\n        \"commentInFrom\": \"\",\n        \"commentInTo\": \"\",\n        \"from\": \"Department\",\n        \"injectedFieldInFrom\": \"location\",\n        \"requiredInFrom\": true,\n        \"requiredInTo\": true,\n        \"to\": \"Location\",\n        \"type\": \"one-to-one\"\n      },\n      {\n        \"commentInFrom\": \"\",\n        \"commentInTo\": \"\",\n        \"from\": \"Employee\",\n        \"injectedFieldInFrom\": \"manager\",\n        \"injectedFieldInTo\": \"\",\n        \"requiredInFrom\": false,\n        \"requiredInTo\": false,\n        \"to\": \"Employee\",\n        \"type\": \"many-to-one\"\n      },\n      {\n        \"commentInFrom\": \"\",\n        \"commentInTo\": \"\",\n        \"from\": \"Employee\",\n        \"injectedFieldInFrom\": \"job\",\n        \"requiredInFrom\": false,\n        \"requiredInTo\": false,\n        \"to\": \"Job\",\n        \"type\": \"one-to-many\"\n      },\n      {\n        \"commentInFrom\": \"\",\n        \"commentInTo\": \"\",\n        \"from\": \"JobHistory\",\n        \"injectedFieldInFrom\": \"department\",\n        \"requiredInFrom\": true,\n        \"requiredInTo\": true,\n        \"to\": \"Department\",\n        \"type\": \"one-to-one\"\n      },\n      {\n        \"commentInFrom\": \"\",\n        \"commentInTo\": \"\",\n        \"from\": \"JobHistory\",\n        \"injectedFieldInFrom\": \"employee\",\n        \"requiredInFrom\": true,\n        \"requiredInTo\": true,\n        \"to\": \"Employee\",\n        \"type\": \"one-to-one\"\n      },\n      {\n        \"commentInFrom\": \"\",\n        \"commentInTo\": \"\",\n        \"from\": \"JobHistory\",\n        \"injectedFieldInFrom\": \"job\",\n        \"requiredInFrom\": true,\n        \"requiredInTo\": true,\n        \"to\": \"Job\",\n        \"type\": \"one-to-one\"\n      },\n      {\n        \"commentInFrom\": \"\",\n        \"commentInTo\": \"\",\n        \"from\": \"Job\",\n        \"injectedFieldInFrom\": \"task\",\n        \"injectedFieldInTo\": \"job\",\n        \"requiredInFrom\": false,\n        \"requiredInTo\": false,\n        \"to\": \"Task\",\n        \"type\": \"many-to-many\"\n      },\n      {\n        \"commentInFrom\": \"\",\n        \"commentInTo\": \"\",\n        \"from\": \"Location\",\n        \"injectedFieldInFrom\": \"country\",\n        \"requiredInFrom\": true,\n        \"requiredInTo\": true,\n        \"to\": \"Country\",\n        \"type\": \"one-to-one\"\n      }\n    ],\n    \"classNames\": [\n      \"JobHistory\",\n      \"Job\",\n      \"Department\",\n      \"Employee\",\n      \"Location\",\n      \"Country\",\n      \"Region\",\n      \"Task\"\n    ],\n    \"classes\": {\n      \"Country\": {\n        \"comment\": \"\",\n        \"dto\": \"no\",\n        \"fieldCount\": 2,\n        \"pagination\": \"no\",\n        \"service\": \"no\",\n        \"tableName\": \"country\"\n      },\n      \"Department\": {\n        \"comment\": \"\",\n        \"dto\": \"no\",\n        \"fieldCount\": 2,\n        \"pagination\": \"no\",\n        \"service\": \"no\",\n        \"tableName\": \"department\"\n      },\n      \"Employee\": {\n        \"comment\": \"\",\n        \"dto\": \"no\",\n        \"fieldCount\": 8,\n        \"pagination\": \"no\",\n        \"service\": \"no\",\n        \"tableName\": \"employee\"\n      },\n      \"Job\": {\n        \"comment\": \"\",\n        \"dto\": \"no\",\n        \"fieldCount\": 4,\n        \"pagination\": \"no\",\n        \"service\": \"no\",\n        \"tableName\": \"job\"\n      },\n      \"JobHistory\": {\n        \"comment\": \"\",\n        \"dto\": \"no\",\n        \"fieldCount\": 2,\n        \"pagination\": \"no\",\n        \"service\": \"no\",\n        \"tableName\": \"job_history\"\n      },\n      \"Location\": {\n        \"comment\": \"\",\n        \"dto\": \"no\",\n        \"fieldCount\": 5,\n        \"pagination\": \"no\",\n        \"service\": \"no\",\n        \"tableName\": \"location\"\n      },\n      \"Region\": {\n        \"comment\": \"\",\n        \"dto\": \"no\",\n        \"fieldCount\": 2,\n        \"pagination\": \"no\",\n        \"service\": \"no\",\n        \"tableName\": \"region\"\n      },\n      \"Task\": {\n        \"comment\": \"\",\n        \"dto\": \"no\",\n        \"fieldCount\": 3,\n        \"pagination\": \"no\",\n        \"service\": \"no\",\n        \"tableName\": \"task\"\n      }\n    },\n    \"fields\": {\n      \"city\": {\n        \"comment\": \"\",\n        \"type\": \"String\",\n        \"validations\": []\n      },\n      \"commissionPct\": {\n        \"comment\": \"\",\n        \"type\": \"_0iCzKrieEeW4ip1mZlCqPg\",\n        \"validations\": []\n      },\n      \"countryId\": {\n        \"comment\": \"\",\n        \"type\": \"_0iCzKrieEeW4ip1mZlCqPg\",\n        \"validations\": []\n      },\n      \"countryName\": {\n        \"comment\": \"\",\n        \"type\": \"String\",\n        \"validations\": []\n      },\n      \"departmentId\": {\n        \"comment\": \"\",\n        \"type\": \"_0iCzKrieEeW4ip1mZlCqPg\",\n        \"validations\": []\n      },\n      \"departmentName\": {\n        \"comment\": \"\",\n        \"type\": \"String\",\n        \"validations\": []\n      },\n      \"description\": {\n        \"comment\": \"\",\n        \"type\": \"String\",\n        \"validations\": []\n      },\n      \"email\": {\n        \"comment\": \"\",\n        \"type\": \"String\",\n        \"validations\": []\n      },\n      \"employeeId\": {\n        \"comment\": \"\",\n        \"type\": \"_0iCzKrieEeW4ip1mZlCqPg\",\n        \"validations\": []\n      },\n      \"endDate\": {\n        \"comment\": \"\",\n        \"type\": \"_0iCzKbieEeW4ip1mZlCqPg\",\n        \"validations\": []\n      },\n      \"firstName\": {\n        \"comment\": \"\",\n        \"type\": \"String\",\n        \"validations\": []\n      },\n      \"hireDate\": {\n        \"comment\": \"\",\n        \"type\": \"_0iCzKbieEeW4ip1mZlCqPg\",\n        \"validations\": []\n      },\n      \"jobId\": {\n        \"comment\": \"\",\n        \"type\": \"_0iCzKrieEeW4ip1mZlCqPg\",\n        \"validations\": []\n      },\n      \"jobTitle\": {\n        \"comment\": \"\",\n        \"type\": \"String\",\n        \"validations\": []\n      },\n      \"lastName\": {\n        \"comment\": \"\",\n        \"type\": \"String\",\n        \"validations\": []\n      },\n      \"locationId\": {\n        \"comment\": \"\",\n        \"type\": \"_0iCzKrieEeW4ip1mZlCqPg\",\n        \"validations\": []\n      },\n      \"maxSalary\": {\n        \"comment\": \"\",\n        \"type\": \"_0iCzKrieEeW4ip1mZlCqPg\",\n        \"validations\": []\n      },\n      \"minSalary\": {\n        \"comment\": \"\",\n        \"type\": \"_0iCzKrieEeW4ip1mZlCqPg\",\n        \"validations\": []\n      },\n      \"phoneNumber\": {\n        \"comment\": \"\",\n        \"type\": \"String\",\n        \"validations\": []\n      },\n      \"postalCode\": {\n        \"comment\": \"\",\n        \"type\": \"String\",\n        \"validations\": []\n      },\n      \"regionId\": {\n        \"comment\": \"\",\n        \"type\": \"_0iCzKrieEeW4ip1mZlCqPg\",\n        \"validations\": []\n      },\n      \"regionName\": {\n        \"comment\": \"\",\n        \"type\": \"String\",\n        \"validations\": []\n      },\n      \"salary\": {\n        \"comment\": \"\",\n        \"type\": \"_0iCzKrieEeW4ip1mZlCqPg\",\n        \"validations\": []\n      },\n      \"startDate\": {\n        \"comment\": \"\",\n        \"type\": \"_0iCzKbieEeW4ip1mZlCqPg\",\n        \"validations\": [\n          \"_0iCy1LieEeW4ip1mZlCqPg\"\n        ]\n      },\n      \"stateProvince\": {\n        \"comment\": \"\",\n        \"type\": \"String\",\n        \"validations\": []\n      },\n      \"streetAddress\": {\n        \"comment\": \"\",\n        \"type\": \"String\",\n        \"validations\": []\n      },\n      \"taskId\": {\n        \"comment\": \"\",\n        \"type\": \"_0iCzKrieEeW4ip1mZlCqPg\",\n        \"validations\": []\n      },\n      \"title\": {\n        \"comment\": \"\",\n        \"type\": \"String\",\n        \"validations\": []\n      }\n    },\n    \"types\": [\n      \"Long\",\n      \"String\",\n      \"ZonedDateTime\"\n    ]\n  }\n}\n"
        }
    ]
}
```

---

### Feature 4: Entity Configuration Generation

**As a developer**, I want to convert a parsed diagram into entity configuration JSON, so I can feed downstream code generation without hand-writing repetitive entity files.

**Expected Behavior / Usage:**

The input names a diagram file, storage profile, and optional generation settings. The output is JSON keyed by entity name, with fields, relationships, table name, fluent-method setting, and generation options such as DTO, pagination, service, microservice, and search settings. Changelog timestamps are intentionally omitted from the stdout contract because they are time-dependent. Relationship models that are incompatible with the chosen storage profile are reported as normalized unsupported_model errors.

**Test Cases:** `rcb_tests/public_test_cases/feature4_entity_json_generation.json`

```json
{
    "description": "Convert parsed diagrams into entity configuration JSON with fields, relationships, generation options, and modeling errors.",
    "cases": [
        {
            "input": {
                "action": "build-entities",
                "file": "./test/xmi/modelio.xmi",
                "database": "sql"
            },
            "expected_output": "Parser detected: MODELIO.\n\n{\n  \"Country\": {\n    \"dto\": \"no\",\n    \"entityTableName\": \"country\",\n    \"fields\": [\n      {\n        \"fieldName\": \"countryId\",\n        \"fieldType\": \"Long\"\n      },\n      {\n        \"fieldName\": \"countryName\",\n        \"fieldType\": \"String\"\n      }\n    ],\n    \"fluentMethods\": true,\n    \"pagination\": \"no\",\n    \"relationships\": [\n      {\n        \"otherEntityField\": \"id\",\n        \"otherEntityName\": \"region\",\n        \"otherEntityRelationshipName\": \"country\",\n        \"ownerSide\": true,\n        \"relationshipName\": \"region\",\n        \"relationshipType\": \"one-to-one\",\n        \"relationshipValidateRules\": \"required\"\n      }\n    ],\n    \"service\": \"no\"\n  },\n  \"Department\": {\n    \"dto\": \"no\",\n    \"entityTableName\": \"department\",\n    \"fields\": [\n      {\n        \"fieldName\": \"departmentId\",\n        \"fieldType\": \"Long\"\n      },\n      {\n        \"fieldName\": \"departmentName\",\n        \"fieldType\": \"String\"\n      }\n    ],\n    \"fluentMethods\": true,\n    \"pagination\": \"no\",\n    \"relationships\": [\n      {\n        \"otherEntityField\": \"id\",\n        \"otherEntityName\": \"location\",\n        \"otherEntityRelationshipName\": \"department\",\n        \"ownerSide\": true,\n        \"relationshipName\": \"location\",\n        \"relationshipType\": \"one-to-one\",\n        \"relationshipValidateRules\": \"required\"\n      },\n      {\n        \"otherEntityName\": \"employee\",\n        \"otherEntityRelationshipName\": \"department\",\n        \"relationshipName\": \"employee\",\n        \"relationshipType\": \"one-to-many\"\n      }\n    ],\n    \"service\": \"no\"\n  },\n  \"Employee\": {\n    \"dto\": \"no\",\n    \"entityTableName\": \"employee\",\n    \"fields\": [\n      {\n        \"fieldName\": \"employeeId\",\n        \"fieldType\": \"Long\"\n      },\n      {\n        \"fieldName\": \"firstName\",\n        \"fieldType\": \"String\"\n      },\n      {\n        \"fieldName\": \"lastName\",\n        \"fieldType\": \"String\"\n      },\n      {\n        \"fieldName\": \"email\",\n        \"fieldType\": \"String\"\n      },\n      {\n        \"fieldName\": \"phoneNumber\",\n        \"fieldType\": \"String\"\n      },\n      {\n        \"fieldName\": \"hireDate\",\n        \"fieldType\": \"ZonedDateTime\"\n      },\n      {\n        \"fieldName\": \"salary\",\n        \"fieldType\": \"Long\"\n      },\n      {\n        \"fieldName\": \"commissionPct\",\n        \"fieldType\": \"Long\"\n      }\n    ],\n    \"fluentMethods\": true,\n    \"pagination\": \"no\",\n    \"relationships\": [\n      {\n        \"otherEntityField\": \"id\",\n        \"otherEntityName\": \"department\",\n        \"relationshipName\": \"department\",\n        \"relationshipType\": \"many-to-one\"\n      },\n      {\n        \"otherEntityName\": \"job\",\n        \"otherEntityRelationshipName\": \"employee\",\n        \"relationshipName\": \"job\",\n        \"relationshipType\": \"one-to-many\"\n      },\n      {\n        \"otherEntityField\": \"id\",\n        \"otherEntityName\": \"employee\",\n        \"relationshipName\": \"manager\",\n        \"relationshipType\": \"many-to-one\"\n      }\n    ],\n    \"service\": \"no\"\n  },\n  \"Job\": {\n    \"dto\": \"no\",\n    \"entityTableName\": \"job\",\n    \"fields\": [\n      {\n        \"fieldName\": \"jobId\",\n        \"fieldType\": \"Long\"\n      },\n      {\n        \"fieldName\": \"jobTitle\",\n        \"fieldType\": \"String\"\n      },\n      {\n        \"fieldName\": \"minSalary\",\n        \"fieldType\": \"Long\"\n      },\n      {\n        \"fieldName\": \"maxSalary\",\n        \"fieldType\": \"Long\"\n      }\n    ],\n    \"fluentMethods\": true,\n    \"pagination\": \"no\",\n    \"relationships\": [\n      {\n        \"otherEntityField\": \"id\",\n        \"otherEntityName\": \"task\",\n        \"otherEntityRelationshipName\": \"job\",\n        \"ownerSide\": true,\n        \"relationshipName\": \"task\",\n        \"relationshipType\": \"many-to-many\"\n      },\n      {\n        \"otherEntityField\": \"id\",\n        \"otherEntityName\": \"employee\",\n        \"relationshipName\": \"employee\",\n        \"relationshipType\": \"many-to-one\"\n      }\n    ],\n    \"service\": \"no\"\n  },\n  \"JobHistory\": {\n    \"dto\": \"no\",\n    \"entityTableName\": \"job_history\",\n    \"fields\": [\n      {\n        \"fieldName\": \"startDate\",\n        \"fieldType\": \"ZonedDateTime\",\n        \"fieldValidateRules\": [\n          \"required\"\n        ]\n      },\n      {\n        \"fieldName\": \"endDate\",\n        \"fieldType\": \"ZonedDateTime\"\n      }\n    ],\n    \"fluentMethods\": true,\n    \"pagination\": \"no\",\n    \"relationships\": [\n      {\n        \"otherEntityField\": \"id\",\n        \"otherEntityName\": \"job\",\n        \"otherEntityRelationshipName\": \"jobHistory\",\n        \"ownerSide\": true,\n        \"relationshipName\": \"job\",\n        \"relationshipType\": \"one-to-one\",\n        \"relationshipValidateRules\": \"required\"\n      },\n      {\n        \"otherEntityField\": \"id\",\n        \"otherEntityName\": \"department\",\n        \"otherEntityRelationshipName\": \"jobHistory\",\n        \"ownerSide\": true,\n        \"relationshipName\": \"department\",\n        \"relationshipType\": \"one-to-one\",\n        \"relationshipValidateRules\": \"required\"\n      },\n      {\n        \"otherEntityField\": \"id\",\n        \"otherEntityName\": \"employee\",\n        \"otherEntityRelationshipName\": \"jobHistory\",\n        \"ownerSide\": true,\n        \"relationshipName\": \"employee\",\n        \"relationshipType\": \"one-to-one\",\n        \"relationshipValidateRules\": \"required\"\n      }\n    ],\n    \"service\": \"no\"\n  },\n  \"Location\": {\n    \"dto\": \"no\",\n    \"entityTableName\": \"location\",\n    \"fields\": [\n      {\n        \"fieldName\": \"locationId\",\n        \"fieldType\": \"Long\"\n      },\n      {\n        \"fieldName\": \"streetAddress\",\n        \"fieldType\": \"String\"\n      },\n      {\n        \"fieldName\": \"postalCode\",\n        \"fieldType\": \"String\"\n      },\n      {\n        \"fieldName\": \"city\",\n        \"fieldType\": \"String\"\n      },\n      {\n        \"fieldName\": \"stateProvince\",\n        \"fieldType\": \"String\"\n      }\n    ],\n    \"fluentMethods\": true,\n    \"pagination\": \"no\",\n    \"relationships\": [\n      {\n        \"otherEntityField\": \"id\",\n        \"otherEntityName\": \"country\",\n        \"otherEntityRelationshipName\": \"location\",\n        \"ownerSide\": true,\n        \"relationshipName\": \"country\",\n        \"relationshipType\": \"one-to-one\",\n        \"relationshipValidateRules\": \"required\"\n      }\n    ],\n    \"service\": \"no\"\n  },\n  \"Region\": {\n    \"dto\": \"no\",\n    \"entityTableName\": \"region\",\n    \"fields\": [\n      {\n        \"fieldName\": \"regionId\",\n        \"fieldType\": \"Long\"\n      },\n      {\n        \"fieldName\": \"regionName\",\n        \"fieldType\": \"String\"\n      }\n    ],\n    \"fluentMethods\": true,\n    \"pagination\": \"no\",\n    \"relationships\": [],\n    \"service\": \"no\"\n  },\n  \"Task\": {\n    \"dto\": \"no\",\n    \"entityTableName\": \"task\",\n    \"fields\": [\n      {\n        \"fieldName\": \"taskId\",\n        \"fieldType\": \"Long\"\n      },\n      {\n        \"fieldName\": \"title\",\n        \"fieldType\": \"String\"\n      },\n      {\n        \"fieldName\": \"description\",\n        \"fieldType\": \"String\"\n      }\n    ],\n    \"fluentMethods\": true,\n    \"pagination\": \"no\",\n    \"relationships\": [\n      {\n        \"otherEntityName\": \"job\",\n        \"otherEntityRelationshipName\": \"task\",\n        \"ownerSide\": false,\n        \"relationshipName\": \"job\",\n        \"relationshipType\": \"many-to-many\"\n      }\n    ],\n    \"service\": \"no\"\n  }\n}\n"
        }
    ]
}
```

---

### Feature 5: Textual Model Export

**As a developer**, I want to export a parsed diagram to a textual entity-definition document, so I can review or reuse the model in a compact text format.

**Expected Behavior / Usage:**

The input names a diagram file, storage profile, and optional generation directives. The output is the exact textual entity and relationship document, including entity blocks, relationship blocks, blank lines, and option directives when requested.

**Test Cases:** `rcb_tests/public_test_cases/feature5_jdl_export.json`

```json
{
    "description": "Export parsed diagrams as textual entity and relationship definitions, optionally appending generation directives.",
    "cases": [
        {
            "input": {
                "action": "export-jdl",
                "file": "./test/xmi/modelio.xmi",
                "database": "sql"
            },
            "expected_output": "Parser detected: MODELIO.\n\nentity JobHistory (job_history) {\n  startDate ZonedDateTime required,\n  endDate ZonedDateTime\n}\nentity Job (job) {\n  jobId Long,\n  jobTitle String,\n  minSalary Long,\n  maxSalary Long\n}\nentity Department (department) {\n  departmentId Long,\n  departmentName String\n}\nentity Employee (employee) {\n  employeeId Long,\n  firstName String,\n  lastName String,\n  email String,\n  phoneNumber String,\n  hireDate ZonedDateTime,\n  salary Long,\n  commissionPct Long\n}\nentity Location (location) {\n  locationId Long,\n  streetAddress String,\n  postalCode String,\n  city String,\n  stateProvince String\n}\nentity Country (country) {\n  countryId Long,\n  countryName String\n}\nentity Region (region) {\n  regionId Long,\n  regionName String\n}\nentity Task (task) {\n  taskId Long,\n  title String,\n  description String\n}\n\nrelationship OneToOne {\n  JobHistory{job} to Job,\n  JobHistory{department} to Department,\n  JobHistory{employee} to Employee,\n  Department{location} to Location,\n  Location{country} to Country,\n  Country{region} to Region\n}\nrelationship OneToMany {\n  Department{employee} to Employee,\n  Employee{job} to Job\n}\nrelationship ManyToOne {\n  Employee{manager} to Employee\n}\nrelationship ManyToMany {\n  [[Exact syntax pattern for composite relationships in JDL]]\n}\n\n"
        }
    ]
}
```

---

### Feature 6: Diagram Metadata Helpers

**As a developer**, I want to detect supported diagram metadata and normalize model names, so I can route diagrams and derive stable identifiers before parsing.

**Expected Behavior / Usage:**

The input either supplies diagram root metadata for editor detection or a name/identifier normalization request. Editor detection outputs the normalized editor family name. Null metadata is reported as normalized null_input. Identifier checks and entity/table-name extraction output JSON fields describing the normalized result.

**Test Cases:** `rcb_tests/public_test_cases/feature6_diagram_metadata_helpers.json`

```json
{
    "description": "Recognize editor metadata and normalize diagram names or identifiers used while interpreting model elements.",
    "cases": [
        {
            "input": {
                "action": "detect-editor",
                "root": {
                    "eAnnotations": [
                        {
                            "$": {
                                "source": "Objing"
                            }
                        }
                    ]
                }
            },
            "expected_output": "Parser detected: MODELIO.\n\n{\n  \"editor\": \"modelio\"\n}\n"
        },
        {
            "input": {
                "action": "detect-editor",
                "root": null
            },
            "expected_output": "{\n  \"detail\": null,\n  \"error\": \"null_input\",\n  \"input\": \"detect-editor\"\n}\n"
        }
    ]
}
```

---

### Feature 7: Association Validation

**As a developer**, I want to validate relationship endpoint rules for each cardinality, so I can reject malformed relationships before entity generation.

**Expected Behavior / Usage:**

The input supplies a relationship cardinality and its available endpoint names. Valid relationships output a JSON valid flag. Missing or excessive endpoint names, null associations, and unsupported cardinalities output normalized error categories such as malformed_association, null_input, or unsupported_association.

**Test Cases:** `rcb_tests/public_test_cases/feature7_association_validation.json`

```json
{
    "description": "Validate relationship cardinality endpoint rules and report malformed or unsupported associations.",
    "cases": [
        {
            "input": {
                "action": "check-association",
                "association": {
                    "type": "one-to-one",
                    "injectedFieldInFrom": "notnull"
                }
            },
            "expected_output": "{\n  \"valid\": true\n}\n"
        },
        {
            "input": {
                "action": "check-association",
                "association": {
                    "type": "one-to-one"
                }
            },
            "expected_output": "{\n  \"detail\": null,\n  \"error\": \"malformed_association\",\n  \"input\": \"check-association\"\n}\n"
        }
    ]
}
```

---

### Feature 8: Entity Generator Command Assembly

**As a developer**, I want to assemble an external entity-generator command from an entity name and flags, so I can invoke downstream generation consistently across platforms.

**Expected Behavior / Usage:**

The input supplies an entity name plus optional generation flags and suffix values. The output is JSON with the normalized command executable and argument list. Missing or blank entity names are reported as normalized invalid_state or invalid_argument errors.

**Test Cases:** `rcb_tests/public_test_cases/feature8_generator_command_assembly.json`

```json
{
    "description": "Build an external entity-generator command from an entity name and selected flags.",
    "cases": [
        {
            "input": {
                "action": "build-command",
                "entity": "abc"
            },
            "expected_output": "{\n  \"args\": [\n    \"jhipster:entity\",\n    \"abc\",\n    \"--regenerate\"\n  ],\n  \"command\": \"yo\"\n}\n"
        },
        {
            "input": {
                "action": "build-command",
                "entity": "abc",
                "flags": [
                    "force",
                    "skip-client",
                    "skip-server",
                    "skip-install",
                    "skip-user-management"
                ],
                "angular_suffix": "suffix"
            },
            "expected_output": "{\n  \"args\": [\n    \"jhipster:entity\",\n    \"abc\",\n    \"--force\",\n    \"--skip-client\",\n    \"--skip-server\",\n    \"--skip-install\",\n    \"--skip-user-management\",\n    \"--angular-suffix\",\n    \"suffix\",\n    \"--regenerate\"\n  ],\n  \"command\": \"yo\"\n}\n"
        }
    ]
}
```

---

### Feature 9: Command-Line Option Parsing

**As a developer**, I want to parse command-line flags and optional local configuration, so I can combine project defaults with user-supplied overrides.

**Expected Behavior / Usage:**

The input contains an argument vector and may include a local configuration object. The output is the parsed option object. Command-line values override local configuration values, boolean negation flags are preserved, and absent options fall back to parser defaults where applicable.

**Test Cases:** `rcb_tests/public_test_cases/feature9_cli_options.json`

```json
{
    "description": "Parse command-line flags and optional local configuration, with command-line values taking precedence.",
    "cases": [
        {
            "input": {
                "action": "parse-cli",
                "args": [
                    "--db",
                    "sql"
                ]
            },
            "expected_output": "{\n  \"db\": \"sql\",\n  \"fluent-methods\": true,\n  \"fluentMethods\": true,\n  \"h\": false,\n  \"help\": false,\n  \"v\": false,\n  \"version\": false\n}\n"
        },
        {
            "input": {
                "action": "parse-cli",
                "args": [
                    "--dto",
                    "mapstruct"
                ]
            },
            "expected_output": "{\n  \"dto\": \"mapstruct\",\n  \"fluent-methods\": true,\n  \"fluentMethods\": true,\n  \"h\": false,\n  \"help\": false,\n  \"v\": false,\n  \"version\": false\n}\n"
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
- See standard sorting rules for multi-flag entities
- Refer to 'diagram' module for association comment handling
