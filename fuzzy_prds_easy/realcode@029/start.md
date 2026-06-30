## Product Requirement Document

# Financial Statement Parser — Structured Extraction from OFX Bank/Card Statement Documents

## Project Goal

Build a library that ingests an OFX (Open Financial Exchange) statement document — in any of the serialization dialects banks emit in the wild — and turns it into a clean, navigable object model of accounts, transactions, balances and institution metadata, so developers can work with strongly-typed statement data instead of hand-parsing a quirky, half-XML markup format.

---

## Background & Problem

OFX is the format most banks export account statements in, but real-world OFX files are notoriously irregular: some are well-formed XML, some are legacy SGML with unclosed value tags (`<ACCTID>12345` with no closing tag), some collapse the entire document onto a single line, and amounts and dates appear in a grab-bag of locale conventions. Without a parser, developers are forced to write fragile, file-specific string surgery and regular expressions, re-deriving the same normalization rules for every dialect and silently breaking when a new bank's export differs.

With this library, a caller hands over a document (by file path or raw string) and receives a uniform structure: a list of accounts, each carrying its identifiers, statement window, ledger balance, and an ordered list of transactions with normalized type labels, signed decimal amounts, and parsed timestamps — regardless of which dialect the source used.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility domain (document normalization, markup parsing, value coercion, object-model construction). It MUST NOT be a single god file. Separate the dialect-normalization stage, the structured-document reader, the value coercion helpers (amount/date), and the typed entity model into distinct units with a clear directory tree.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a black-box contract for an execution adapter, NOT the internal data model. The core parser must know nothing about stdin/stdout or the JSON command shape. A thin adapter translates each command into ordinary calls on the parser and renders the resulting object model to text.

3. **Adherence to SOLID Design Principles:** Keep normalization, parsing, value coercion, model construction, and output rendering as separate cohesive units. The entity model should be extendable without modifying the parser; the parser should depend on abstractions, not on a concrete I/O channel.

4. **Robustness & Interface Design:** The public interface should accept either a file path or an in-memory string. Failures (unreadable/absent source, content that cannot be normalized into a valid document) must be modeled as explicit, distinguishable error conditions rather than generic faults or warnings leaking to output.

---

## Core Features

### Feature 1: Parse a single-account bank statement

**As a developer**, I want to load a bank statement document and read its account, balance and transactions as structured fields, so I can process statement data without touching the raw markup.

**Expected Behavior / Usage:**

Given a document describing one bank account, the parser exposes: the account number, account type, routing identifier, branch/agency identifier, the statement-level transaction-set id, the ledger balance (preserved as written), and the balance-as-of timestamp. The statement carries a currency code and a start/end date window. Each transaction exposes a type code and a human-readable type description derived from it (e.g. a credit code → "Generic credit", a cheque code → "Cheque"), a signed decimal amount, a unique id, a name and memo (empty string when absent), a category/sic and cheque-number field (empty when absent), a posting date, and a user-initiated date (the literal `none` when the source omits it). Amounts render with any purely-integral value stripped of trailing zeros (`200.00` → `200`, `-100.00` → `-100`). All timestamps render as wall-clock `Y-m-d H:i:s`, and a bracketed timezone-offset suffix in the source does NOT shift those wall-clock fields. A `singleAccountHelper=set` line signals that exactly one account was present. Collections render in source order.

**Test Cases:** `rcb_tests/public_test_cases/feature1_bank_statement.json`

```json
{
    "description": "Parse a single-account bank statement and report account identity, balances, the statement window, and each transaction's normalized type label, signed amount, identifiers, descriptions and dates. Integral amounts drop trailing zeros; timestamps render as timezone-independent wall-clock; a missing user-initiated date renders as 'none'.",
    "cases": [
        {
            "input": {"op": "accounts", "fixture": "ofxdata-xml.ofx"},
            "expected_output": "accountCount=1\nsingleAccountHelper=set\naccount[0].accountNumber=098-121\naccount[0].accountType=SAVINGS\naccount[0].routingNumber=987654321\naccount[0].agencyNumber=\naccount[0].transactionUid=23382938\naccount[0].balance=5250.00\naccount[0].balanceDate=2007-10-15 02:15:29\naccount[0].currency=USD\naccount[0].startDate=2007-01-01 00:00:00\naccount[0].endDate=2007-10-15 00:00:00\naccount[0].transactionCount=3\ntransaction[0].type=CREDIT\ntransaction[0].typeDesc=Generic credit\ntransaction[0].amount=200\ntransaction[0].uniqueId=980315001\ntransaction[0].name=DEPOSIT\ntransaction[0].memo=automatic deposit\ntransaction[0].sic=\ntransaction[0].checkNumber=\ntransaction[0].date=2007-03-15 00:00:00\ntransaction[0].userInitiatedDate=2007-03-15 00:00:00\ntransaction[1].type=CREDIT\ntransaction[1].typeDesc=Generic credit\ntransaction[1].amount=150\ntransaction[1].uniqueId=980310001\ntransaction[1].name=TRANSFER\ntransaction[1].memo=Transfer from checking\ntransaction[1].sic=\ntransaction[1].checkNumber=\ntransaction[1].date=2007-03-29 00:00:00\ntransaction[1].userInitiatedDate=2007-03-29 00:00:00\ntransaction[2].type=CHECK\ntransaction[2].typeDesc=Cheque\ntransaction[2].amount=-100\ntransaction[2].uniqueId=980309001\ntransaction[2].name=Cheque\ntransaction[2].memo=\ntransaction[2].sic=\ntransaction[2].checkNumber=1025\ntransaction[2].date=2007-07-09 00:00:00\ntransaction[2].userInitiatedDate=2007-07-09 00:00:00\n"
        }
    ]
}
```

---

### Feature 2: Read the sign-on / institution block

**As a developer**, I want to read the session sign-on response, so I can confirm the request succeeded and identify the responding institution.

**Expected Behavior / Usage:**

The document opens with a sign-on response. The parser exposes its status as a numeric code, a severity label, and a message string (empty when the source omits it), plus a human-readable description that the code maps to — code `0` maps to `Success`. It also exposes the session language, the institution's display name and id, and the server timestamp rendered as wall-clock `Y-m-d H:i:s`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_signon.json`

```json
{
    "description": "From the sign-on block, report response status (code, severity, message, and the description the code maps to), session language, institution name/id, and the server timestamp as wall-clock time. Code 0 maps to 'Success'; an absent message is empty.",
    "cases": [
        {
            "input": {"op": "signon", "fixture": "ofxdata-xml.ofx"},
            "expected_output": "statusCode=0\nstatusSeverity=INFO\nstatusMessage=\nstatusCodeDesc=Success\nlanguage=ENG\ninstituteName=MYBANK\ninstituteId=01234\ndate=2007-10-15 02:15:29\n"
        }
    ]
}
```

---

### Feature 3: Handle documents with multiple accounts

**As a developer**, I want a document carrying several accounts to expose all of them, so I can iterate over every account in one statement export.

**Expected Behavior / Usage:**

When a document carries more than one account, the parser collects all of them; a summary reports the total account count, the total number of transactions across all accounts, and the sorted set of distinct statement currencies. The convenience single-account helper is `unset` whenever there is more than one account, and `set` when there is exactly one. The illustrative case below shows a three-account document.

**Test Cases:** `rcb_tests/public_test_cases/feature3_multiple_accounts.json`

```json
{
    "description": "Summarize a document by total account count, total transaction count across accounts, and sorted distinct currencies. With more than one account the single-account helper is unset; with one account it is set.",
    "cases": [
        {
            "input": {"op": "summary", "fixture": "ofx-multiple-accounts-xml.ofx"},
            "expected_output": "accountCount=3\nsingleAccountHelper=unset\ntransactionCount=3\ncurrencies=GBP\n"
        }
    ]
}
```

---

### Feature 4: Parse a credit-card statement

**As a developer**, I want a credit-card statement — whose account-identity block uses a card-account source rather than a bank-account source — to parse into the same shape as a bank statement, so my downstream code is source-agnostic.

**Expected Behavior / Usage:**

A card statement nests its account identity under a card-account block instead of a bank-account block; the parser detects this and still produces the uniform account/statement/transaction structure. The card number is exposed as the account identifier; fields absent for cards (account type, routing) render empty. Negative ledger balances and signed transaction amounts are preserved.

**Test Cases:** `rcb_tests/public_test_cases/feature4_credit_card.json`

```json
{
    "description": "Parse a credit-card statement whose account identity lives in a card-account source block, producing the same structure as a bank statement: the card number as account id, empty routing/type, preserved signed balance and amount.",
    "cases": [
        {
            "input": {"op": "accounts", "fixture": "ofxdata-credit-card.ofx"},
            "expected_output": "accountCount=1\nsingleAccountHelper=set\naccount[0].accountNumber=1234567891234567\naccount[0].accountType=\naccount[0].routingNumber=\naccount[0].agencyNumber=\naccount[0].transactionUid=20160823000000\naccount[0].balance=-500.00\naccount[0].balanceDate=2016-08-23 00:00:00\naccount[0].currency=GBP\naccount[0].startDate=2016-08-23 00:00:00\naccount[0].endDate=2016-08-23 00:00:00\naccount[0].transactionCount=1\ntransaction[0].type=POS\ntransaction[0].typeDesc=Point of sale debit or credit\ntransaction[0].amount=-100\ntransaction[0].uniqueId=ABCDEFGHIJ\ntransaction[0].name=VENDOR\ntransaction[0].memo=\ntransaction[0].sic=\ntransaction[0].checkNumber=\ntransaction[0].date=2016-08-23 00:00:00\ntransaction[0].userInitiatedDate=2016-08-23 00:00:00\n"
        }
    ]
}
```

---

### Feature 5: Tolerate real-world serialization dialects

**As a developer**, I want documents in the many irregular OFX dialects to all parse identically, so I don't need per-bank special-casing.

**Expected Behavior / Usage:**

The loader first normalizes the input into well-formed markup before reading it. It must accept: a multi-line form with one tag per line where value tags are left unclosed (`<BALAMT>5250.00` with no closing tag), a fully single-line form with the entire document on one physical line, indentation/whitespace variations, and trailing marketing/info text. After normalization every dialect yields the same structured result; the summary reports account count, the single-account helper flag, total transaction count, and sorted distinct currencies. The two illustrative cases show an unclosed-tag multi-line document and a single-line document.

**Test Cases:** `rcb_tests/public_test_cases/feature5_dialect_tolerance.json`

```json
{
    "description": "Load statement documents in several serialization dialects (multi-line with unclosed value tags, fully single-line, whitespace variants, trailing info text) and confirm each normalizes to the same structured result, reported as account count, single-account helper flag, total transaction count, and sorted distinct currencies.",
    "cases": [
        {
            "input": {"op": "summary", "fixture": "ofxdata.ofx"},
            "expected_output": "accountCount=1\nsingleAccountHelper=set\ntransactionCount=3\ncurrencies=USD\n"
        },
        {
            "input": {"op": "summary", "fixture": "ofxdata-oneline.ofx"},
            "expected_output": "accountCount=1\nsingleAccountHelper=set\ntransactionCount=8\ncurrencies=EUR\n"
        }
    ]
}
```

---

### Feature 6: Normalize locale-varied money amounts

**As a developer**, I want money strings in any locale convention coerced into one numeric value, so amounts compare and arithmetic correctly regardless of source formatting.

**Expected Behavior / Usage:**

A money string may use a period or a comma as the decimal mark, may or may not include thousands separators, and may carry a leading minus. All of `1000.00`, `1000,00`, `1,000.00` and `1.000,00` denote the same magnitude. The result is a single numeric value; purely-integral results drop trailing zeros (so `1000.00` → `1000`). A bare integer is taken at face value (`1` → `1`, `10` → `10`) EXCEPT that a bare three-digit-or-more run whose last two digits look like a fractional part is treated as having an implied two-decimal fraction — e.g. `100` is interpreted as `1` (the trailing `00` consumed as cents). This last rule is an intentional, documented quirk of the coercion contract.

**Test Cases:** `rcb_tests/public_test_cases/feature6_amount_normalization.json`

```json
{
    "description": "Coerce a money string in any locale convention (period/comma decimal mark, optional thousands separators, optional leading minus) into one numeric value; integral results drop trailing zeros.",
    "cases": [
        {"input": {"op": "amount", "value": "1000.00"}, "expected_output": "amount=1000\n"},
        {"input": {"op": "amount", "value": "1000,00"}, "expected_output": "amount=1000\n"}
    ]
}
```

---

### Feature 7: Parse financial timestamps at any precision

**As a developer**, I want statement timestamps parsed regardless of how much precision the source includes, so dates are usable as real datetime values.

**Expected Behavior / Usage:**

A timestamp string may be date-only (`YYYYMMDD`), date plus time (`YYYYMMDDHHMMSS`), date-time with fractional seconds (`…​.XXX`), or date-time with fractional seconds and a bracketed timezone offset (`…​[-5:EST]`). All forms parse to a wall-clock `Y-m-d H:i:s` value. The fractional-second and bracketed timezone-offset components do NOT shift the rendered wall-clock fields — the same date and time-of-day appear whether or not an offset suffix is present.

**Test Cases:** `rcb_tests/public_test_cases/feature7_date_parsing.json`

```json
{
    "description": "Parse a timestamp at any supported precision (date only, date-time, date-time with fractional seconds, date-time with fractional seconds plus bracketed timezone offset) into a wall-clock 'Y-m-d H:i:s' value; the offset and fractional components do not shift the wall-clock fields.",
    "cases": [
        {"input": {"op": "datetime", "value": "20081005132200.124[-5:EST]"}, "expected_output": "datetime=2008-10-05 13:22:00\n"},
        {"input": {"op": "datetime", "value": "20081005"}, "expected_output": "datetime=2008-10-05 00:00:00\n"}
    ]
}
```

---

### Feature 8: Distinguishable error conditions

**As a developer**, I want load and parse failures surfaced as distinct, neutral categories, so I can branch on the failure kind instead of scraping error text.

**Expected Behavior / Usage:**

Two failure modes are modeled distinctly. Content that cannot be normalized into a valid document yields a parse-failure category. Requesting a document from a path that does not exist yields a file-not-found category. Errors are reported as a neutral `error=<category>` line, never as a raw runtime fault or warning text.

**Test Cases:** `rcb_tests/public_test_cases/feature8_error_handling.json`

```json
{
    "description": "Surface failures as neutral categories: content that cannot be normalized into a valid document yields a parse-failure category; a path that does not exist yields a file-not-found category.",
    "cases": [
        {"input": {"op": "parse", "content": "<invalid xml>"}, "expected_output": "error=parse_failed\n"},
        {"input": {"op": "load_path", "path": "a non-existent file"}, "expected_output": "error=file_not_found\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file library implementing the features above — dialect normalization, structured-document reading, amount/date coercion, and a typed entity model (accounts, transactions, balances, statement, sign-on/institution) — with the parser fully decoupled from standard I/O.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON command from stdin (`op` plus its arguments: a `fixture` name, raw `content`, a `path`, or a `value`), invokes the core parser, and prints the normalized text contract to stdout exactly as specified per feature. The adapter is solely responsible for JSON handling, deterministic ordering/rendering, and translating native failures into the neutral `error=<category>` lines.

3. **Automated test harness:** A single entry point `bash rcb_tests/test.sh` that reads every `*.json` case file from a case directory (default `test_cases`, switchable via `--cases-dir <subdir>`, e.g. `public_test_cases`), feeds each case's `input` to the adapter, and writes the raw program stdout to `rcb_tests/stdout/<cases-dir>/{stem}@{idx:03d}.txt` — one file per case, containing only the program output so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same ordering convention as the headers module
- apply only if the transaction type is a standard deposit
