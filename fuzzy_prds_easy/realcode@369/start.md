## Product Requirement Document

# Recurring Billing Adapter - Subscription Payment and Webhook Behavior

## Project Goal

Build a recurring billing support library that allows developers to convert payment amounts, prepare subscription checkout payments, track billable line items, synchronize gateway payments, and process payment webhooks without hand-writing repetitive billing infrastructure.

---

## Background & Problem

Without this library/tool, developers are forced to manually convert money formats, calculate taxed order totals, persist payment state, attach subscription actions to checkout payments, and coordinate webhook side effects across orders, credits, mandates, and subscriptions. This leads to duplicated billing code, fragile rounding behavior, inconsistent gateway payloads, and error-prone webhook handling.

With this library/tool, the application can express billing operations through a clean domain interface while an execution adapter exposes deterministic JSON input and stdout output for black-box validation.

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

### Feature 1: Initial-Payment Coupon Discount Action

**As a developer**, I want to rely on initial-payment coupon discount action, so I can integrate recurring billing flows without rewriting gateway and billing-state glue code.

**Expected Behavior / Usage:**

The adapter accepts an initial payment amount and applies a fixed subscription discount action. It prints the negative discount total, zero tax, absence of follow-up payload, and empty execution result.

**Test Cases:** `rcb_tests/public_test_cases/feature10_coupon_first_payment_discount.json`

```json
{
    "description": "Applies a fixed subscription coupon to an initial payment action as a negative line item with zero tax and no follow-up payload.",
    "cases": [
        {
            "input": {
                "feature": "coupon.first_payment_discount",
                "unit_price_minor_units": 10000
            },
            "expected_output": "total_minor_units=-500\ntax_percentage=0\ntax_minor_units=0\npayload=null\nexecute_count=0\n"
        }
    ]
}
```

---
### Feature 2: First Subscription Payment Checkout Payload

**As a developer**, I want to rely on first subscription payment checkout payload, so I can integrate recurring billing flows without rewriting gateway and billing-state glue code.

**Expected Behavior / Usage:**

The adapter accepts subscription checkout options such as trial days, quantity, or trial skipping. It builds a first-payment checkout through the framework flow and prints the HTTP redirect URL, gateway payload fields, amount, and stored action metadata.

**Test Cases:** `rcb_tests/public_test_cases/feature11_subscription_first_payment.json`

```json
{
    "description": "Builds the gateway payload for a first subscription payment, including redirect URL, sequence type, locale, customer identifier, amount, and stored follow-up action metadata.",
    "cases": [
        {
            "input": {
                "feature": "subscription.first_payment_payload",
                "trial_days": 5
            },
            "expected_output": "http_redirect_url=https://foo-redirect-bar.com\ngateway_amount_value=0.05\ngateway_amount_currency=EUR\nsequence_type=first\nmethod=[\"ideal\"]\ncustomer_id=cst_unique_customer_id\nlocale=nl_NL\naction_count=2\nfirst_action_quantity=1\nfirst_action_tax_percentage=20\n"
        }
    ]
}
```

---
### Feature 3: Webhook Payment Lookup

**As a developer**, I want to rely on webhook payment lookup, so I can integrate recurring billing flows without rewriting gateway and billing-state glue code.

**Expected Behavior / Usage:**

The adapter accepts a webhook payment identifier, debug flag, and optional simulated gateway lookup failure. It prints whether a payment resource is available; in debug mode lookup failures are normalized as gateway_lookup_failed.

**Test Cases:** `rcb_tests/public_test_cases/feature12_webhook_lookup.json`

```json
{
    "description": "Retrieves a payment resource for a webhook identifier and normalizes gateway lookup failures differently for debug and non-debug modes.",
    "cases": [
        {
            "input": {
                "feature": "webhook.lookup",
                "id": "tr_123xyz"
            },
            "expected_output": "debug=false\npayment_found=true\n"
        },
        {
            "input": {
                "feature": "webhook.lookup",
                "id": "sub_xxxxxxxxxxx",
                "api_error": true,
                "debug": false
            },
            "expected_output": "debug=false\npayment_found=false\n"
        }
    ]
}
```

---
### Feature 4: Order Payment Webhook Processing

**As a developer**, I want to rely on order payment webhook processing, so I can integrate recurring billing flows without rewriting gateway and billing-state glue code.

**Expected Behavior / Usage:**

The adapter accepts an order-payment webhook scenario with initial and gateway payment statuses. It invokes the HTTP controller path and prints HTTP status plus persisted order, subscription, stored-payment, and credit state.

**Test Cases:** `rcb_tests/public_test_cases/feature13_order_webhook.json`

```json
{
    "description": "Processes order-payment webhooks through the framework controller, returning HTTP status and updated order, subscription, stored-payment, and credit state.",
    "cases": [
        {
            "input": {
                "feature": "webhook.order_payment",
                "payment_id": "tr_payment_paid_id",
                "initial_status": "open",
                "gateway_status": "paid"
            },
            "expected_output": "http_status=200\norder_status=paid\nsubscription_active=true\nsubscription_cancelled=false\nstored_payment_status=paid\ncredit_minor_units=0\n"
        }
    ]
}
```

---
### Feature 5: Paid First-Payment Webhook Processing

**As a developer**, I want to rely on paid first-payment webhook processing, so I can integrate recurring billing flows without rewriting gateway and billing-state glue code.

**Expected Behavior / Usage:**

The adapter accepts a paid first-payment webhook scenario. It invokes the registered HTTP route and prints the HTTP status, subscription state, trial state, mandate identifier, and subscription plan.

**Test Cases:** `rcb_tests/public_test_cases/feature14_first_payment_webhook.json`

```json
{
    "description": "Processes a paid first-payment webhook through the HTTP route and starts the subscription, trial state, and mandate linkage.",
    "cases": [
        {
            "input": {
                "feature": "first_payment.webhook_paid"
            },
            "expected_output": "http_status=200\nsubscribed=true\non_trial=true\nmandate_id=mdt_unique_mandate_id\nsubscription_plan=monthly-10-1\n"
        }
    ]
}
```

---
### Feature 6: Money Amount Conversion

**As a developer**, I want to rely on money amount conversion, so I can integrate recurring billing flows without rewriting gateway and billing-state glue code.

**Expected Behavior / Usage:**

The adapter accepts a money conversion command with either minor units, a decimal string, or a gateway amount object. It prints currency and minor units for money objects, or currency and a two-decimal value for gateway payloads. Currency codes are preserved exactly.

**Test Cases:** `rcb_tests/public_test_cases/feature1_money_conversion.json`

```json
{
    "description": "Converts between minor-unit money, decimal amount strings, and gateway amount payloads while preserving currency and two-decimal formatting.",
    "cases": [
        {
            "input": {
                "feature": "money.convert",
                "operation": "minor_to_money",
                "minor_units": 1234,
                "currency": "EUR"
            },
            "expected_output": "currency=EUR\nminor_units=1234\n"
        },
        {
            "input": {
                "feature": "money.convert",
                "operation": "decimal_to_money",
                "decimal": "12.34",
                "currency": "EUR"
            },
            "expected_output": "currency=EUR\nminor_units=1234\n"
        }
    ]
}
```

---
### Feature 7: Billable Line Item Amounts

**As a developer**, I want to rely on billable line item amounts, so I can integrate recurring billing flows without rewriting gateway and billing-state glue code.

**Expected Behavior / Usage:**

The adapter accepts a line item containing currency, quantity, unit price in minor units, and tax percentage. It prints subtotal, rounded tax, total, and money-view signals so rounding and currency preservation are observable.

**Test Cases:** `rcb_tests/public_test_cases/feature2_order_item_amounts.json`

```json
{
    "description": "Computes subtotal, rounded tax, total, and money views for a billable line item from unit price, quantity, tax percentage, and currency.",
    "cases": [
        {
            "input": {
                "feature": "order_item.amounts",
                "item": {
                    "currency": "EUR",
                    "quantity": 4,
                    "unit_price": 110,
                    "tax_percentage": 21.5
                }
            },
            "expected_output": "[a specific rounding logic resulting in a precise minor-unit total]\n[a specific rounding logic resulting in a precise minor-unit total]\n[a specific rounding logic resulting in a precise minor-unit total]\nunit_price_currency=EUR\nunit_price_minor_units=110\ntotal_currency=EUR\n"
        }
    ]
}
```

---
### Feature 8: Line Item Processing State

**As a developer**, I want to rely on line item processing state, so I can integrate recurring billing flows without rewriting gateway and billing-state glue code.

**Expected Behavior / Usage:**

The adapter accepts a line item order identifier. A missing order identifier means the item is unprocessed; a present order identifier means it is processed. The output reports both positive and inverse processed checks.

**Test Cases:** `rcb_tests/public_test_cases/feature3_order_item_processing.json`

```json
{
    "description": "Reports whether a line item is considered processed or unprocessed based on the presence of an associated order identifier.",
    "cases": [
        {
            "input": {
                "feature": "order_item.processed_state",
                "order_id": null
            },
            "expected_output": "processed_when_true=false\nprocessed_when_false=true\n"
        },
        {
            "input": {
                "feature": "order_item.processed_state",
                "order_id": 1
            },
            "expected_output": "processed_when_true=true\nprocessed_when_false=false\n"
        }
    ]
}
```

---
### Feature 9: Persisted Line Item Query Filters

**As a developer**, I want to rely on persisted line item query filters, so I can integrate recurring billing flows without rewriting gateway and billing-state glue code.

**Expected Behavior / Usage:**

The adapter accepts persisted line item records with order identifiers and processing timestamps. It runs framework-backed query filters and prints counts for processed, unprocessed, ready-to-process, and due items.

**Test Cases:** `rcb_tests/public_test_cases/feature4_order_item_queries.json`

```json
{
    "description": "Filters persisted line items by processed state and due processing time, returning framework query counts for each scope.",
    "cases": [
        {
            "input": {
                "feature": "order_item.query_scopes",
                "items": [
                    {
                        "order_id": null,
                        "process_at": "2019-01-01 00:00:00"
                    },
                    {
                        "order_id": null,
                        "process_at": "2099-01-01 00:00:00"
                    },
                    {
                        "order_id": 1,
                        "process_at": "2019-01-01 00:00:00"
                    }
                ]
            },
            "expected_output": "processed_count=1\nunprocessed_count=2\nshould_process_count=1\ndue_count=2\n"
        }
    ]
}
```

---
### Feature 10: Collection Currency Summary

**As a developer**, I want to rely on collection currency summary, so I can integrate recurring billing flows without rewriting gateway and billing-state glue code.

**Expected Behavior / Usage:**

The adapter accepts a collection of line items with currencies. It prints the unique currencies in collection order, or the single currency when every item uses the same currency.

**Test Cases:** `rcb_tests/public_test_cases/feature5_collection_currency.json`

```json
{
    "description": "Summarizes currencies used by a collection of billable line items and returns the single currency only when all items share it.",
    "cases": [
        {
            "input": {
                "feature": "collection.currency",
                "operation": "list_currencies",
                "items": [
                    {
                        "description": "a",
                        "currency": "USD"
                    },
                    {
                        "description": "b",
                        "currency": "USD"
                    },
                    {
                        "description": "c",
                        "currency": "EUR"
                    }
                ]
            },
            "expected_output": "currencies=[\"USD\",\"EUR\"]\n"
        },
        {
            "input": {
                "feature": "collection.currency",
                "operation": "single_currency",
                "items": [
                    {
                        "description": "a",
                        "currency": "USD"
                    },
                    {
                        "description": "b",
                        "currency": "USD"
                    }
                ]
            },
            "expected_output": "currency=USD\n"
        }
    ]
}
```

---
### Feature 11: Multiple-Currency Error Normalization

**As a developer**, I want to rely on multiple-currency error normalization, so I can integrate recurring billing flows without rewriting gateway and billing-state glue code.

**Expected Behavior / Usage:**

The adapter accepts a collection containing more than one currency and a request for a single currency. Instead of exposing a runtime exception, it prints a neutral multiple-currency error and the currencies that caused it.

**Test Cases:** `rcb_tests/public_test_cases/feature6_collection_currency_error.json`

```json
{
    "description": "Normalizes the error produced when a collection-level single-currency operation is requested for items containing multiple currencies.",
    "cases": [
        {
            "input": {
                "feature": "collection.currency_error",
                "items": [
                    {
                        "description": "a",
                        "currency": "USD"
                    },
                    {
                        "description": "b",
                        "currency": "EUR"
                    }
                ]
            },
            "expected_output": "error=multiple_currencies\ncurrencies=[\"USD\",\"EUR\"]\n"
        }
    ]
}
```

---
### Feature 12: Collection Filtering and Grouping

**As a developer**, I want to rely on collection filtering and grouping, so I can integrate recurring billing flows without rewriting gateway and billing-state glue code.

**Expected Behavior / Usage:**

The adapter accepts a collection of line items and either filters by currency, groups by currency, or extracts unique tax percentages. Outputs include item counts, matching descriptions, grouped counts, or sorted unique tax percentages.

**Test Cases:** `rcb_tests/public_test_cases/feature7_collection_grouping.json`

```json
{
    "description": "Filters and groups billable line item collections by currency, and lists unique tax percentages in sorted order.",
    "cases": [
        {
            "input": {
                "feature": "collection.grouping",
                "operation": "where_currency",
                "currency": "USD",
                "items": [
                    {
                        "description": "eur item",
                        "currency": "EUR"
                    },
                    {
                        "description": "usd one",
                        "currency": "USD"
                    },
                    {
                        "description": "usd two",
                        "currency": "USD"
                    }
                ]
            },
            "expected_output": "count=2\ndescriptions=[\"usd one\",\"usd two\"]\n"
        }
    ]
}
```

---
### Feature 13: Collection Total Calculation

**As a developer**, I want to rely on collection total calculation, so I can integrate recurring billing flows without rewriting gateway and billing-state glue code.

**Expected Behavior / Usage:**

The adapter accepts same-currency line items with unit price, quantity, and tax percentage. It prints the total money amount in the collection currency after applying tax and rounding per line-item behavior.

**Test Cases:** `rcb_tests/public_test_cases/feature8_collection_total.json`

```json
{
    "description": "Computes the total money amount for a same-currency collection of billable line items, including rounded tax.",
    "cases": [
        {
            "input": {
                "feature": "collection.total",
                "items": [
                    {
                        "currency": "EUR",
                        "unit_price": 12150,
                        "quantity": 1,
                        "tax_percentage": 10.0
                    },
                    {
                        "currency": "EUR",
                        "unit_price": 12150,
                        "quantity": 2,
                        "tax_percentage": 10.0
                    }
                ]
            },
            "expected_output": "currency=EUR\nminor_units=40095\n"
        }
    ]
}
```

---
### Feature 14: Gateway Payment Synchronization

**As a developer**, I want to rely on gateway payment synchronization, so I can integrate recurring billing flows without rewriting gateway and billing-state glue code.

**Expected Behavior / Usage:**

The adapter accepts a gateway payment payload plus optional refunded and charged-back amounts. It persists a local payment through the framework model layer and prints identifiers, status, mandate, owner linkage, and monetary totals.

**Test Cases:** `rcb_tests/public_test_cases/feature9_payment_sync.json`

```json
{
    "description": "Creates a local payment record from a gateway payment payload, preserving identifiers, status, mandate, owner link, and monetary refund/chargeback totals.",
    "cases": [
        {
            "input": {
                "feature": "payment.create_from_gateway",
                "payment": {
                    "id": "tr_dummy_payment_id",
                    "status": "dummy_status",
                    "amount": {
                        "currency": "EUR",
                        "value": "12.34"
                    },
                    "mandate_id": "mdt_dummy_mandate_id"
                }
            },
            "expected_output": "payment_id=tr_dummy_payment_id\nstatus=dummy_status\ncurrency=EUR\nmandate_id=mdt_dummy_mandate_id\namount_minor_units=1234\nrefunded_minor_units=0\ncharged_back_minor_units=0\nowner_linked=true\n"
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
- follow the redirect pattern used in the legacy invoice module for EU customers
