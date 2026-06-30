## Product Requirement Document

# Session Shopping Cart - A Per-Session Line-Item Cart with Exact Money Totals

## Project Goal

Build a session-scoped shopping cart that lets developers track a customer's selected products — each as a line item holding a quantity and a unit price — and derive accurate per-item and whole-cart money totals, without hand-rolling session storage, line-item deduplication, or floating-point-safe price arithmetic.

---

## Background & Problem

Without this component, developers building a storefront must repeatedly wire the same plumbing: stash a cart in the caller's session, look up whether a chosen product is already in the cart before inserting a duplicate, keep quantities and prices in sync, and sum money amounts in a way that does not drift due to binary floating point. This leads to repetitive, error-prone boilerplate scattered across request handlers, and to subtle bugs such as duplicate line items for the same product or rounding errors in totals.

With this component, a developer attaches a cart to the current session, adds/updates/removes products by identity, and reads back exact totals and counts through a small, idiomatic interface.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a small domain (one cart aggregate and its line items); a clean, well-separated small module set is appropriate. Do not inflate it into an over-engineered framework, but keep the cart/session/line-item responsibilities logically distinct.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box contract for the execution adapter**, NOT the internal data model. The core cart logic must be completely decoupled from stdin/stdout and JSON parsing. The adapter alone translates JSON command sequences into idiomatic calls on the cart.

3. **Adherence to SOLID Design Principles:** Separate session binding, line-item storage, total/count computation, and output formatting into distinct cohesive units. The core must be open for extension but closed for modification, with high-level logic depending on abstractions rather than I/O details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface must read naturally in the target language and hide storage details.
   - **Resilience:** Operations on absent line items must be modeled as explicit, catchable error conditions rather than silent no-ops or generic faults.

---

## Core Features

### Feature 1: Session-Scoped Cart Persistence

**As a developer**, I want a cart to attach to the current session and survive across separate request cycles, so a customer's selections are not lost between page loads.

**Expected Behavior / Usage:**

A cart is bound to a caller-supplied session on first use. The first time a cart is established for a session it is created fresh and empty; once established, re-establishing a cart against that same session resolves to the **same** open cart, so its line items persist. The contract exposes whether re-establishing resolved to the same cart, followed by a dump of the cart state. A state dump lists every line item on its own line as `item product=<product-id> quantity=<n> unit_price=<price> subtotal=<price>`, with line items ordered by ascending product id, then a `total=<price>` line (sum of all subtotals) and a `count=<n>` line (sum of all quantities). All money amounts are rendered with exactly two decimal places.

**Test Cases:** `rcb_tests/public_test_cases/feature1_session_persistence.json`

```json
{
    "description": "A cart is bound to a caller session on first use and persists for the lifetime of that session. Re-establishing a cart against the same session must resolve to the same underlying open cart rather than starting a new one, so its contents survive across separate request cycles.",
    "cases": [
        {
            "input": {"products": [1], "operations": [{"op": "add", "product": 1, "unit_price": "100", "quantity": 1}, {"op": "reopen"}, {"op": "dump"}]},
            "expected_output": "same_cart=yes\nitem product=1 quantity=1 unit_price=100.00 subtotal=100.00\ntotal=100.00\ncount=1\n"
        }
    ]
}
```

---

### Feature 2: Adding a Product as a Line Item

**As a developer**, I want to add a product to the cart with a quantity and unit price, so the cart records what the customer wants to buy.

**Expected Behavior / Usage:**

Adding a product creates a line item that references that product and stores the supplied quantity and unit price. The line item is then retrievable from the cart with exactly the quantity and unit price supplied, and its subtotal equals quantity times unit price. A subsequent state dump (see Feature 1 for the dump format) reflects the new line item, the running cart total, and the cart's item count (sum of quantities).

**Test Cases:** `rcb_tests/public_test_cases/feature2_add_item.json`

```json
{
    "description": "Adding a product places a line item in the cart that references the product and records its quantity and unit price. A freshly added line item is retrievable from the cart with the exact quantity and unit price supplied, and its subtotal equals quantity times unit price.",
    "cases": [
        {
            "input": {"products": [1], "operations": [{"op": "add", "product": 1, "unit_price": "100", "quantity": 1}, {"op": "dump"}]},
            "expected_output": "item product=1 quantity=1 unit_price=100.00 subtotal=100.00\ntotal=100.00\ncount=1\n"
        }
    ]
}
```

---

### Feature 3: Exact Money Subtotals and Totals

**As a developer**, I want per-item subtotals and the cart total computed with exact decimal money arithmetic, so monetary amounts never drift due to floating-point rounding.

**Expected Behavior / Usage:**

A line item's subtotal is its quantity multiplied by its unit price, computed in exact fixed-point decimal arithmetic and rendered with two decimal places. Unit prices may be whole numbers (e.g. an integer amount) or fractional money amounts (e.g. a two-decimal price); in both cases the subtotal preserves exact monetary precision (for instance, four units at a fractional unit price yields the exact product, not a binary-float approximation). The whole-cart total is the sum of all line-item subtotals, and the item count is the sum of all quantities.

**Test Cases:** `rcb_tests/public_test_cases/feature3_subtotal_decimal.json`

```json
{
    "description": "A line item's subtotal is its quantity multiplied by its unit price, computed with exact fixed-point decimal arithmetic. Unit prices may be whole numbers or fractional money amounts, and the subtotal preserves two-decimal monetary precision without floating-point rounding error.",
    "cases": [
        {"input": {"products": [1], "operations": [{"op": "add", "product": 1, "unit_price": "100", "quantity": 3}, {"op": "dump"}]}, "expected_output": "item product=1 quantity=3 unit_price=100.00 subtotal=300.00\ntotal=300.00\ncount=3\n"},
        {"input": {"products": [1], "operations": [{"op": "add", "product": 1, "unit_price": "3.20", "quantity": 4}, {"op": "dump"}]}, "expected_output": "item product=1 quantity=4 unit_price=3.20 subtotal=12.80\ntotal=12.80\ncount=4\n"}
    ]
}
```

---

### Feature 4: Updating an Existing Line Item

**As a developer**, I want to update an existing line item's quantity and unit price, so I can change how much of a product the customer is buying and at what price.

**Expected Behavior / Usage:**

Updating an existing line item **replaces** its quantity and unit price with the supplied values; it does not accumulate onto the prior quantity. After an update, the line item's subtotal, the whole-cart total, and the cart's item count all reflect the new unit price and new quantity (e.g. updating a quantity-3 line to quantity 2 at a new unit price yields a total of two units at the new price, and an item count of 2).

**Test Cases:** `rcb_tests/public_test_cases/feature4_update_item.json`

```json
{
    "description": "Updating an existing line item replaces its quantity and unit price with the supplied values (it does not accumulate onto the prior quantity). After an update, the cart total reflects the new unit price times the new quantity, and the cart's reported item count equals the new quantity.",
    "cases": [
        {
            "input": {"products": [1], "operations": [{"op": "add", "product": 1, "unit_price": "100", "quantity": 3}, {"op": "update", "product": 1, "unit_price": "200", "quantity": 2}, {"op": "dump"}]},
            "expected_output": "item product=1 quantity=2 unit_price=200.00 subtotal=400.00\ntotal=400.00\ncount=2\n"
        }
    ]
}
```

---

### Feature 5: Human-Readable Line-Item Label

**As a developer**, I want each line item to expose a readable label combining its quantity and the kind of product it references, so a cart listing can be rendered without digging into raw fields.

**Expected Behavior / Usage:**

A line item carries a human-readable label of the form `<quantity> units of <product-type-name>`, where the product-type name is the name of the kind/type of product the line item references. Requesting the label yields a `label=<text>` line.

**Test Cases:** `rcb_tests/public_test_cases/feature5_item_label.json`

```json
{
    "description": "A line item carries a human-readable label that combines its quantity with the name of the product type it references, so a cart listing can be rendered without inspecting raw fields.",
    "cases": [
        {
            "input": {"products": [1], "operations": [{"op": "add", "product": 1, "unit_price": "100", "quantity": 3}, {"op": "label", "product": 1}]},
            "expected_output": "label=3 units of User\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured cart implementation: a session-bound cart aggregate holding line items (each referencing a product and storing quantity and unit price), with exact decimal money totals and counts. Its physical structure must match this small domain without over-engineering.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON command object from stdin (product fixtures plus an ordered sequence of cart operations), drives the core cart, and prints the result to stdout, strictly matching the per-feature contracts above. This adapter is separated from the core domain.

3. **Automated test harness:** A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a cases directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file `rcb_tests/stdout/<cases-dir>/{stem}@{index:03}.txt` containing **only** the raw stdout from the program under test, comparable directly against `expected_output`.


---
**Implementation notes:**
- follow the sorting logic used in the headers module
