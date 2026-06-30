## Product Requirement Document

# Coupon Redemption Engine - Polymorphic Coupon Storage and Redemption Contracts

## Project Goal

Build a coupon redemption library that allows developers to create, verify, redeem, restrict, and generate coupons for application records without writing repetitive persistence, validation, and redemption-tracking code.

---

## Background & Problem

Without this library, developers are forced to manually create coupon tables, check expiration and stock, attach coupons to customers, enforce per-customer limits, normalize coupon errors, and maintain command-line seeding logic. This leads to repetitive code, fragile edge-case handling, and inconsistent redemption records across the application.

With this library, coupon creation, validation, redemption, metadata access, fallback handling, and generation are exposed through a cohesive domain interface while storage and event behavior remain observable through stable black-box outputs.

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

### Feature 1: Coupon Record Creation

**As a developer**, I want to create coupon records with public codes and business fields, so I can store and retrieve coupon offers without hand-writing persistence glue.

**Expected Behavior / Usage:**

The input is a JSON command describing a coupon to create, including at minimum a public coupon code and optionally visible business fields such as type, value, usage limit, quantity, expiration, restrictions, and metadata. The output prints the stored coupon code and storage confirmation; when visible fields are requested, it prints those field values as individual lines.

**Test Cases:** `rcb_tests/public_test_cases/feature1_coupon_creation.json`

```json
{
    "description": "Creating a coupon record persists its public code and visible fields in storage.",
    "cases": [
        {
            "input": {
                "action": "create_coupon",
                "code": "test-code"
            },
            "expected_output": "coupon_code=test-code\ndatabase_has_coupon_code=true\n"
        }
    ]
}
```

---

### Feature 2: Expiration Status

**As a developer**, I want to check whether a coupon is expired, so I can block stale offers before redemption.

**Expected Behavior / Usage:**

The input is a coupon code plus an optional relative expiration condition. If no expiration is supplied, the coupon is active. If the expiration is in the past, the coupon is expired. The output includes the coupon code and complementary boolean status lines for expired and not-expired states.

**Test Cases:** `rcb_tests/public_test_cases/feature2_expiration_status.json`

```json
{
    "description": "A coupon reports whether it is expired based on its expiration timestamp relative to the current time.",
    "cases": [
        {
            "input": {
                "action": "check_expiration",
                "code": "not-expired-coupon"
            },
            "expected_output": "coupon_code=not-expired-coupon\nis_expired=false\nis_not_expired=true\n"
        }
    ]
}
```

---

### Feature 3: Coupon Redemption

**As a developer**, I want to redeem valid coupons for customers and target items, so I can track usage through durable redemption records.

**Expected Behavior / Usage:**

This feature groups related coupon behaviors. The leaf sub-features below define the complete input and output contracts.

---

### Feature 3.1: Customer Redemption

**As a developer**, I want to redeem a coupon for the acting customer, so I can record that the customer consumed the offer.

**Expected Behavior / Usage:**

The input supplies a coupon code to redeem for the current customer. A successful redemption verifies the coupon, attaches it to the customer, and prints the coupon fields, redemption count, redeemer alias, and emitted domain signals. No HTTP layer is involved; the observable integration signals are database redemptions and domain events.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_redeem_coupon_for_customer.json`

```json
{
    "description": "Redeeming an available coupon for a customer creates a redemption record and emits verification and redemption signals.",
    "cases": [
        {
            "input": {
                "action": "redeem_coupon",
                "code": "test-code"
            },
            "expected_output": "coupon_code=test-code\ncoupon_type=null\ncoupon_value=null\ncoupon_limit=null\ncoupon_quantity=null\nredemption_count=1\nredeemer_alias=customer\nevents=[\"coupon_verified\",\"coupon_redeemed\"]\n"
        }
    ]
}
```

---

### Feature 3.2: Targeted Redemption

**As a developer**, I want to redeem a coupon by one customer for another target item, so I can represent purchases or enrollments where the redeemer and redeemed item differ.

**Expected Behavior / Usage:**

The input supplies a coupon code and target item identifier. A successful redemption records both the customer that used the coupon and the target item that received the benefit. The output includes coupon fields, redemption count, redeemer alias and id, target alias and id, and emitted domain signals.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_redeem_coupon_for_target.json`

```json
{
    "description": "A coupon can be redeemed by one customer while being assigned to a separate target item in the redemption record.",
    "cases": [
        {
            "input": {
                "action": "redeem_coupon_for_target",
                "code": "test-code",
                "target_id": 1
            },
            "expected_output": "coupon_code=test-code\ncoupon_type=null\ncoupon_value=null\ncoupon_limit=null\ncoupon_quantity=null\nredemption_count=1\nredeemer_alias=customer\nredeemer_id=1\ntarget_alias=target_item\ntarget_id=1\nevents=[\"coupon_verified\",\"coupon_redeemed\"]\n"
        }
    ]
}
```

---

### Feature 3.3: Usage Lookup

**As a developer**, I want to query whether a customer has already used a coupon code, so I can prevent duplicate application decisions from relying on manual joins.

**Expected Behavior / Usage:**

The input supplies available coupon codes, one code to redeem, and a code to query afterward. The output identifies the redeemed coupon, the number of redemption records, the queried code, and whether that exact code was previously used by the customer.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_coupon_usage_checks.json`

```json
{
    "description": "After redemption, checking a customer against a coupon code reports whether that exact code has already been used.",
    "cases": [
        {
            "input": {
                "action": "check_coupon_usage",
                "available_codes": [
                    "test-code",
                    "applied-code"
                ],
                "redeem_code": "applied-code",
                "query_code": "applied-code"
            },
            "expected_output": "coupon_code=applied-code\ncoupon_type=null\ncoupon_value=null\ncoupon_limit=null\ncoupon_quantity=null\nredemption_count=1\nquery_code=applied-code\nalready_used=true\n"
        }
    ]
}
```

---

### Feature 4: Validity and Eligibility

**As a developer**, I want to reject coupons that are invalid, expired, or restricted to another redeemer, so I can surface domain-safe errors instead of runtime-specific failures.

**Expected Behavior / Usage:**

This feature groups related coupon behaviors. The leaf sub-features below define the complete input and output contracts.

---

### Feature 4.1: Redeemer Restrictions

**As a developer**, I want to limit coupons to a specific customer or customer type, so I can offer customer-specific promotions safely.

**Expected Behavior / Usage:**

The input may restrict a coupon to the current customer, another customer, the current customer type, or another type. Matching restrictions redeem successfully and print redemption details. Non-matching restrictions print a normalized error category, emitted not-allowed signal, and zero redemption count.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_redeemer_restrictions.json`

```json
{
    "description": "Coupons restricted to a specific customer or customer type can be redeemed only by matching redeemers; mismatches produce a normalized not-allowed error.",
    "cases": [
        {
            "input": {
                "action": "redeem_coupon",
                "code": "redeemer-coupon",
                "restriction": "this_customer"
            },
            "expected_output": "coupon_code=redeemer-coupon\ncoupon_type=null\ncoupon_value=null\ncoupon_limit=null\ncoupon_quantity=null\nredemption_count=1\nredeemer_alias=customer\nevents=[\"coupon_verified\",\"coupon_redeemed\"]\n"
        }
    ]
}
```

---

### Feature 4.2: Validity Errors

**As a developer**, I want to normalize invalid and expired coupon failures, so I can let callers handle failures consistently across implementations.

**Expected Behavior / Usage:**

The input attempts to verify or redeem a code that is missing or expired. The output never exposes host-language exception names; it prints a neutral error category plus observable domain signals and redemption count.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_coupon_validity_errors.json`

```json
{
    "description": "Invalid and expired coupon attempts return normalized errors and include observable redemption counts and emitted domain signals.",
    "cases": [
        {
            "input": {
                "action": "verify_coupon",
                "code": "correct-coupon",
                "verify_code": "wrong-coupon"
            },
            "expected_output": "error=invalid_coupon\nevents=[]\nredemption_count=0\n"
        }
    ]
}
```

---

### Feature 5: Usage Limits

**As a developer**, I want to enforce per-customer and global quantity limits, so I can control how many times offers can be consumed.

**Expected Behavior / Usage:**

This feature groups related coupon behaviors. The leaf sub-features below define the complete input and output contracts.

---

### Feature 5.1: Per-Customer Usage Limit

**As a developer**, I want to enforce a maximum number of redemptions for each customer, so I can stop repeat use after the configured threshold.

**Expected Behavior / Usage:**

The input supplies a coupon code, a per-customer limit, and one or more redemption attempts. Attempts up to the limit create redemption records. Attempts beyond the limit print a normalized over-limit error, emitted over-limit signal, current redemption count, and remaining quantity if present. A separate status query reports whether the customer has reached the configured limit.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_usage_limit.json`

```json
{
    "description": "A coupon with a per-customer usage limit allows redemptions up to the limit and then reports an over-limit error or status.",
    "cases": [
        {
            "input": {
                "action": "redeem_coupon",
                "code": "disposable-coupon",
                "limit": 1,
                "attempts": 2
            },
            "expected_output": "error=coupon_over_limit\nevents=[\"coupon_verified\",\"coupon_redeemed\",\"coupon_over_limit\"]\nredemption_count=1\nremaining_quantity=null\n"
        }
    ]
}
```

---

### Feature 5.2: Overall Quantity Limit

**As a developer**, I want to decrement remaining coupon stock on redemption, so I can exhaust a finite pool of coupon uses.

**Expected Behavior / Usage:**

The input supplies a coupon code with an overall quantity and multiple redemption attempts. Each successful redemption decrements remaining quantity. Once quantity reaches zero, a later attempt prints a normalized over-quantity error, emitted over-quantity signal, redemption count, and remaining quantity.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_quantity_limit.json`

```json
{
    "description": "A coupon with an overall quantity decrements when redeemed and reports an over-quantity error after stock is exhausted.",
    "cases": [
        {
            "input": {
                "action": "redeem_coupon",
                "code": "quantity-coupon",
                "quantity": 1,
                "attempts": 2
            },
            "expected_output": "error=coupon_over_quantity\nevents=[\"coupon_verified\",\"coupon_redeemed\",\"coupon_over_quantity\"]\nredemption_count=1\nremaining_quantity=0\n"
        }
    ]
}
```

---

### Feature 6: Coupon Metadata Payload

**As a developer**, I want to attach nested metadata to coupons, so I can drive application-specific actions after verification or redemption.

**Expected Behavior / Usage:**

The input supplies nested key-value metadata and a path to inspect. The output confirms the metadata behaves as a readable key-value collection, prints the selected nested value, and prints the stored JSON representation.

**Test Cases:** `rcb_tests/public_test_cases/feature6_coupon_data_payload.json`

```json
{
    "description": "Coupon metadata supplied as nested key-value data remains readable after redemption and is stored as JSON.",
    "cases": [
        {
            "input": {
                "action": "coupon_data_payload",
                "code": "business-coupon",
                "data": {
                    "run-actions": {
                        "queue-job": true
                    }
                },
                "data_path": [
                    "run-actions",
                    "queue-job"
                ]
            },
            "expected_output": "coupon_code=business-coupon\ndata_is_key_value_collection=true\ndata_path_value=true\nstored_data_json={\"run-actions\":{\"queue-job\":true}}\n"
        }
    ]
}
```

---

### Feature 7: Optional Operations

**As a developer**, I want to return fallback values for missing coupons when requested, so I can avoid exception control flow in optional form paths.

**Expected Behavior / Usage:**

This feature groups related coupon behaviors. The leaf sub-features below define the complete input and output contracts.

---

### Feature 7.1: Optional Redemption Fallback

**As a developer**, I want to attempt redemption while returning fallback values on failure, so I can keep optional coupon fields nullable without crashing checkout.

**Expected Behavior / Usage:**

The input supplies a nullable, missing, or existing coupon code and optionally a fallback value. Null or missing codes return the fallback/null result and create no redemption record. Existing codes redeem normally and print coupon fields plus the redemption count.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_optional_redeem_fallback.json`

```json
{
    "description": "Optional redemption returns a fallback value instead of raising for null or missing codes, while existing codes still redeem normally.",
    "cases": [
        {
            "input": {
                "action": "redeem_coupon_or_fallback",
                "code": null
            },
            "expected_output": "result=null\nredemption_count=0\n"
        }
    ]
}
```

---

### Feature 7.2: Optional Verification Fallback

**As a developer**, I want to attempt verification while returning fallback values on failure, so I can validate optional coupon fields without creating redemptions.

**Expected Behavior / Usage:**

The input supplies a nullable, missing, or existing coupon code and optionally a fallback value. Null or missing codes return the fallback/null result and create no redemption record. Existing codes verify successfully and also create no redemption record.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_optional_verify_fallback.json`

```json
{
    "description": "Optional verification returns a fallback value instead of raising for null or missing codes, while existing codes verify without creating a redemption.",
    "cases": [
        {
            "input": {
                "action": "verify_coupon_or_fallback",
                "code": null
            },
            "expected_output": "result=null\nredemption_count=0\n"
        }
    ]
}
```

---

### Feature 8: Coupon Generation

**As a developer**, I want to generate coupons programmatically, so I can seed promotions without manually creating every record.

**Expected Behavior / Usage:**

This feature groups related coupon behaviors. The leaf sub-features below define the complete input and output contracts.

---

### Feature 8.1: Bulk Generation

**As a developer**, I want to generate many coupons at once, so I can quickly create a requested number of usable coupon records.

**Expected Behavior / Usage:**

The input specifies a count. The output prints how many coupon objects were generated, how many coupon records exist in storage, and whether every generated code is non-empty.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_bulk_generation.json`

```json
{
    "description": "Bulk coupon generation creates the requested number of stored coupons with non-empty codes.",
    "cases": [
        {
            "input": {
                "action": "generate_coupons",
                "count": 10
            },
            "expected_output": "[a deterministic count based on the input batch size]\n[a deterministic count based on the input batch size]\ncodes_are_non_empty=true\n"
        }
    ]
}
```

---

### Feature 8.2: Customer-Specific Generation

**As a developer**, I want to generate one coupon assigned to a customer, so I can create targeted promotions with stored attributes.

**Expected Behavior / Usage:**

The input supplies a coupon code and attributes for a coupon assigned to the current customer. The output prints the stored coupon fields and the customer restriction alias and id.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_generate_for_customer.json`

```json
{
    "description": "Generating one coupon for a specific customer stores the code, supplied attributes, and customer restriction.",
    "cases": [
        {
            "input": {
                "action": "generate_coupon_for_customer",
                "code": "test-code",
                "attributes": {
                    "value": 100
                }
            },
            "expected_output": "coupon_code=test-code\ncoupon_type=null\ncoupon_value=100\ncoupon_limit=null\ncoupon_quantity=null\nredeemer_alias=customer\nredeemer_id=1\n"
        }
    ]
}
```

---

### Feature 9: Command-Line Coupon Creation

**As a developer**, I want to create a coupon from a CLI-style command input, so I can seed promotions from automation scripts.

**Expected Behavior / Usage:**

The input contains a command-style coupon code, current time, and option map for value, type, limits, quantity, expiration, redeemer alias, redeemer id, and metadata. The output includes the success message and all persisted coupon fields, including expiration, redeemer, and stored metadata JSON.

**Test Cases:** `rcb_tests/public_test_cases/feature9_console_coupon_creation.json`

```json
{
    "description": "The command-line creation interface writes a coupon with supplied options and returns a success message.",
    "cases": [
        {
            "input": {
                "action": "make_coupon_command",
                "now": "2022-06-25 10:00:00",
                "code": "my-test-coupon",
                "options": {
                    "value": 50,
                    "type": "percentage",
                    "limit": 3,
                    "quantity": 10,
                    "expires_at": "2022-06-25 10:00:00",
                    "redeemer_type_alias": "customer",
                    "redeemer_id": 1,
                    "data": "json"
                }
            },
            "expected_output": "console_output=The coupon was added to the database successfully!\ncoupon_code=my-test-coupon\ncoupon_type=percentage\ncoupon_value=50\ncoupon_limit=3\ncoupon_quantity=10\nexpires_at=2022-06-25 10:00:00\nredeemer_alias=customer\nredeemer_id=1\nstored_data_json=\"json\"\n"
        }
    ]
}
```

---

### Feature 10: Configurable Storage

**As a developer**, I want to use alternate coupon and redemption storage names, so I can adapt the system to applications with customized database schemas.

**Expected Behavior / Usage:**

The input selects an alternate coupon record scenario or alternate redemption record scenario. The output confirms the configured storage alias, coupon data behavior, database presence, or redemption timestamp matching without exposing implementation class names.

**Test Cases:** `rcb_tests/public_test_cases/feature10_configurable_storage.json`

```json
{
    "description": "Alternative configured coupon and redemption storage locations preserve the same externally visible coupon data and redemption timestamp behavior.",
    "cases": [
        {
            "input": {
                "action": "configured_coupon_model",
                "code": "fake-coupon",
                "data": {
                    "run-actions": {
                        "queue-job": true
                    }
                },
                "data_path": [
                    "run-actions",
                    "queue-job"
                ]
            },
            "expected_output": "[a configurable table name derived from the model setup]\ncoupon_code=fake-coupon\ndata_is_key_value_collection=true\ndata_path_value=true\ndatabase_has_coupon_code=true\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_coupon_creation.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_coupon_creation@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- check the config file referenced in the feature name
