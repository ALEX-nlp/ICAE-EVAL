## Product Requirement Document

# Blockchain Chain-Event Predicate Matching Engine — Selecting Transactions From Block Streams By Declarative Rules

## Project Goal

Build a stateless engine that, given a declarative predicate and a stream of blocks, decides which blocks contain transactions that satisfy the predicate, so applications can subscribe to exactly the on-chain activity they care about without re-scanning and re-parsing entire blocks themselves.

---

## Background & Problem

Applications that react to blockchain activity need to answer a recurring question: "out of this batch of new blocks, which transactions are interesting to me?" Each block carries a list of transactions; each transaction has an identifier hash, a kind (it may call a smart-contract method, deploy a contract, or transfer the native token), and a receipt holding the events it emitted (token mints/transfers/burns/locks and smart-contract print events).

Without a shared engine, every application re-implements ad-hoc scanning and asset-matching logic, which is repetitive and error-prone. This engine centralizes that logic behind a single contract: callers describe what they want with a typed predicate, hand over a sequence of blocks, and receive back a precise report of which blocks were selected and which transactions matched. The matching rules are fixed and deterministic, covering fungible-token events, non-fungible-token events, native-token events, smart-contract print events, contract deployments, contract calls, and exact transaction-id lookups.

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

The execution adapter reads ONE JSON request from stdin. A request has two fields: `predicate` (a declarative rule whose `scope` field selects its variant; the remaining fields are variant-specific) and `blocks` (an ordered array of blocks). Each block has a `transactions` array; each transaction has a `txid` (its identifier hash), an optional `kind` (one of `{"type":"contract_call","contract_identifier":...,"method":...}`, `{"type":"contract_deployment","contract_identifier":...}`, or `{"type":"native_token_transfer"}`; defaults to a native token transfer when omitted), and an optional `events` array of receipt events. Each event is `{"type":<event-type-tag>,"data":{...}}`.

The adapter evaluates the predicate against the blocks and prints exactly three lines to stdout:
`triggered=<true|false>` — whether at least one block was selected;
`apply_block_count=<n>` — how many blocks were selected (a block is selected if at least one of its transactions matches);
`matched_transactions=<csv>` — the identifier hashes of every matched transaction, in block order then in-block order, comma-separated (empty after the `=` when nothing matched).

A block is selected when one or more of its transactions match the predicate; matching is evaluated independently per transaction. The same three-line report shape applies to every feature below.

### Feature 1: Fungible-Token Event Predicate

**As a developer**, I want to select blocks whose transactions emitted a fungible-token event for a specific asset and action, so I can track movements of a particular token.

**Expected Behavior / Usage:**

The predicate (`scope` = `ft_event`) names an `asset_identifier` and a list of accepted `actions` drawn from `mint`, `transfer`, `burn`. A transaction matches when any of its receipt events is a fungible-token event whose action is among the accepted set AND whose asset identifier equals the predicate's `asset_identifier`. A non-matching asset identifier disqualifies the event even when the action matches. When several single-event blocks each match, each is counted and its transaction reported; a predicate whose accepted action is absent from the blocks selects nothing. Relevant event tags are `FTMintEvent`, `FTTransferEvent`, `FTBurnEvent`, each carrying an `asset_identifier` (plus `recipient`/`sender`/`amount` strings).

**Test Cases:** `rcb_tests/public_test_cases/feature1_ft_event.json`

```json
{
    "description": "Evaluate a fungible-token event predicate against a sequence of blocks. The predicate names a token asset identifier and a set of accepted actions (mint, transfer, burn). A block is selected when it holds a transaction that emitted a fungible-token event whose action is among the accepted set AND whose asset identifier equals the one named by the predicate. The report states whether any block was selected, how many blocks were selected, and the identifiers of the matched transactions.",
    "cases": [
        {
            "input": {
                "predicate": {"scope": "ft_event", "asset_identifier": "asset-id", "actions": ["mint"]},
                "blocks": [
                    {"transactions": [{"txid": "0x01", "events": [{"type": "FTMintEvent", "data": {"asset_identifier": "asset-id", "recipient": "", "amount": ""}}]}]}
                ]
            },
            "expected_output": "triggered=true\napply_block_count=1\nmatched_transactions=0x01\n"
        },
        {
            "input": {
                "predicate": {"scope": "ft_event", "asset_identifier": "wrong-id", "actions": ["mint"]},
                "blocks": [
                    {"transactions": [{"txid": "0x01", "events": [{"type": "FTMintEvent", "data": {"asset_identifier": "asset-id", "recipient": "", "amount": ""}}]}]}
                ]
            },
            "expected_output": "triggered=false\napply_block_count=0\nmatched_transactions=\n"
        }
    ]
}
```

---

### Feature 2: Non-Fungible-Token Event Predicate

**As a developer**, I want to select blocks whose transactions emitted a non-fungible-token event for a specific asset class and action, so I can track activity of a particular collectible.

**Expected Behavior / Usage:**

The predicate (`scope` = `nft_event`) names an `asset_identifier` and a list of accepted `actions` drawn from `mint`, `transfer`, `burn`. A transaction matches when any of its receipt events is a non-fungible-token event whose action is among the accepted set AND whose asset identifier equals the predicate's `asset_identifier`. A non-matching asset identifier disqualifies the event even when the action matches. Several matching blocks are each counted and reported; an accepted action absent from the blocks selects nothing. Relevant event tags are `NFTMintEvent`, `NFTTransferEvent`, `NFTBurnEvent`, each carrying an `asset_identifier` and a `raw_value` (plus `recipient`/`sender`).

**Test Cases:** `rcb_tests/public_test_cases/feature2_nft_event.json`

```json
{
    "description": "Evaluate a non-fungible-token event predicate against a sequence of blocks. The predicate names a token asset identifier and a set of accepted actions (mint, transfer, burn). A block is selected when it holds a transaction that emitted a non-fungible-token event whose action is among the accepted set AND whose asset identifier equals the one named by the predicate. The report states whether any block was selected, how many blocks were selected, and the identifiers of the matched transactions.",
    "cases": [
        {
            "input": {
                "predicate": {"scope": "nft_event", "asset_identifier": "asset-id", "actions": ["mint"]},
                "blocks": [
                    {"transactions": [{"txid": "0x01", "events": [{"type": "NFTMintEvent", "data": {"asset_identifier": "asset-id", "raw_value": "asset-id", "recipient": ""}}]}]}
                ]
            },
            "expected_output": "triggered=true\napply_block_count=1\nmatched_transactions=0x01\n"
        },
        {
            "input": {
                "predicate": {"scope": "nft_event", "asset_identifier": "wrong-id", "actions": ["mint"]},
                "blocks": [
                    {"transactions": [{"txid": "0x01", "events": [{"type": "NFTMintEvent", "data": {"asset_identifier": "asset-id", "raw_value": "asset-id", "recipient": ""}}]}]}
                ]
            },
            "expected_output": "triggered=false\napply_block_count=0\nmatched_transactions=\n"
        }
    ]
}
```

---

### Feature 3: Native-Token Event Predicate

**As a developer**, I want to select blocks whose transactions emitted a native-token event of a given action, so I can track the base currency's movements without specifying an asset.

**Expected Behavior / Usage:**

The predicate (`scope` = `stx_event`) names only a list of accepted `actions` drawn from `mint`, `transfer`, `lock`, `burn`; there is no asset identifier because the native token is implicit. A transaction matches when any of its receipt events is a native-token event whose action is among the accepted set. Several matching blocks are each counted and reported; an accepted action absent from the blocks selects nothing. Relevant event tags are `STXMintEvent`, `STXTransferEvent`, `STXLockEvent`, `STXBurnEvent`, carrying string fields appropriate to each action.

**Test Cases:** `rcb_tests/public_test_cases/feature3_stx_event.json`

```json
{
    "description": "Evaluate a native-token event predicate against a sequence of blocks. The predicate names a set of accepted actions (mint, transfer, lock, burn) and does not constrain any asset identifier. A block is selected when it holds a transaction that emitted a native-token event whose action is among the accepted set. The report states whether any block was selected, how many blocks were selected, and the identifiers of the matched transactions.",
    "cases": [
        {
            "input": {
                "predicate": {"scope": "stx_event", "actions": ["mint"]},
                "blocks": [
                    {"transactions": [{"txid": "0x01", "events": [{"type": "STXMintEvent", "data": {"recipient": "", "amount": ""}}]}]}
                ]
            },
            "expected_output": "triggered=true\napply_block_count=1\nmatched_transactions=0x01\n"
        },
        {
            "input": {
                "predicate": {"scope": "stx_event", "actions": ["mint"]},
                "blocks": [
                    {"transactions": [{"txid": "0x01", "events": [{"type": "STXTransferEvent", "data": {"sender": "", "recipient": "", "amount": ""}}]}]},
                    {"transactions": [{"txid": "0x02", "events": [{"type": "STXLockEvent", "data": {"locked_amount": "", "unlock_height": "", "locked_address": ""}}]}]}
                ]
            },
            "expected_output": "triggered=false\napply_block_count=0\nmatched_transactions=\n"
        }
    ]
}
```

---

### Feature 4: Smart-Contract Print-Event Predicate

**As a developer**, I want to select blocks whose transactions published a smart-contract print event from a given contract and whose decoded payload contains a substring, so I can watch domain-specific log messages.

**Expected Behavior / Usage:**

The predicate (`scope` = `print_event`) names a `contract_identifier` and a `contains` substring. Only events under the `print` topic are considered (a `SmartContractEvent` whose `topic` is not `print` is ignored). A print event matches when its `contract_identifier` equals the predicate's `contract_identifier`, OR the predicate's `contract_identifier` is the wildcard `*`; AND the decoded, human-readable form of the event payload (`raw_value`, a hex-encoded value) contains the predicate's `contains` substring, OR the predicate's `contains` is the wildcard `*` (which accepts any payload). A wrong contract identifier or a substring not present in the decoded payload disqualifies the event. When both fields are wildcards, every print event matches and each carrying block is counted.

**Test Cases:** `rcb_tests/public_test_cases/feature4_print_event.json`

```json
{
    "description": "Evaluate a smart-contract print-event predicate against a sequence of blocks. The predicate names a target contract identifier and a substring constraint. Only events published under the print topic are considered. A print event matches when its publishing contract identifier equals the predicate's contract identifier (or the predicate uses the wildcard '*' for the contract identifier) AND the human-readable decoding of the event's payload contains the predicate's substring (or the predicate uses the wildcard '*' for the substring, which matches any payload). A block is selected when it holds a transaction emitting at least one matching print event. The report states whether any block was selected, how many blocks were selected, and the identifiers of the matched transactions.",
    "cases": [
        {
            "input": {
                "predicate": {"scope": "print_event", "contract_identifier": "ST3AXH4EBHD63FCFPTZ8GR29TNTVWDYPGY0KDY5E5.loan-data", "contains": "some-value"},
                "blocks": [
                    {"transactions": [{"txid": "0x01", "events": [{"type": "SmartContractEvent", "data": {"contract_identifier": "ST3AXH4EBHD63FCFPTZ8GR29TNTVWDYPGY0KDY5E5.loan-data", "topic": "print", "raw_value": "0x0d00000010616263736f6d652d76616c7565616263"}}]}]}
                ]
            },
            "expected_output": "triggered=true\napply_block_count=1\nmatched_transactions=0x01\n"
        },
        {
            "input": {
                "predicate": {"scope": "print_event", "contract_identifier": "*", "contains": "*"},
                "blocks": [
                    {"transactions": [{"txid": "0x01", "events": [{"type": "SmartContractEvent", "data": {"contract_identifier": "ST3AXH4EBHD63FCFPTZ8GR29TNTVWDYPGY0KDY5E5.loan-data", "topic": "print", "raw_value": "0x0d00000010616263736f6d652d76616c7565616263"}}]}]},
                    {"transactions": [{"txid": "0x02", "events": [{"type": "SmartContractEvent", "data": {"contract_identifier": "some-id", "topic": "print", "raw_value": "0x0d00000000"}}]}]}
                ]
            },
            "expected_output": "triggered=true\napply_block_count=2\nmatched_transactions=0x01,0x02\n"
        }
    ]
}
```

---

### Feature 5: Contract-Deployment Predicate

**As a developer**, I want to select contract-deployment transactions by their deployer (or by a standard token trait), so I can react to new contracts published by a given account.

**Expected Behavior / Usage:**

The predicate (`scope` = `contract_deployment`) has two mutually exclusive forms. The **deployer** form supplies a `deployer` string: a contract-deployment transaction matches when its deployed `contract_identifier` starts with that deployer prefix; the wildcard `*` matches every deployment. The **implemented-trait** form supplies `implement_trait` (one of `sip09`, `sip10`, or the wildcard `*`); this form never selects any transaction, because detection of which standard trait a deployment implements is not performed. In both forms, only transactions whose kind is a contract deployment can match — contract-call and native-transfer transactions are never selected by this predicate, so a block stream mixing deployments and calls yields only the matching deployments.

**Test Cases:** `rcb_tests/public_test_cases/feature5_contract_deployment.json`

```json
{
    "description": "Evaluate a contract-deployment predicate against a sequence of blocks that may contain both contract-deployment and contract-call transactions. Two predicate forms exist. In the deployer form, a deployment transaction is selected when its deployed contract identifier begins with the named deployer prefix, and the wildcard '*' selects every deployment transaction. In the implemented-trait form (selecting deployments that implement a standard token trait), no transaction is selected because trait detection is not performed. Only deployment transactions can ever be selected by this predicate. The report states whether any block was selected, how many blocks were selected, and the identifiers of the matched transactions.",
    "cases": [
        {
            "input": {
                "predicate": {"scope": "contract_deployment", "deployer": "ST13F481SBR0R7Z6NMMH8YV2FJJYXA5JPA0AD3HP9"},
                "blocks": [
                    {"transactions": [{"txid": "0x93c89ffdac77ed2ba52611563bd491f56f5d558e23d311a105663ae32bdf18e5", "kind": {"type": "contract_deployment", "contract_identifier": "ST13F481SBR0R7Z6NMMH8YV2FJJYXA5JPA0AD3HP9.subnet-v1"}}]},
                    {"transactions": [{"txid": "0xb92c2ade84a8b85f4c72170680ae42e65438aea4db72ba4b2d6a6960f4141ce8", "kind": {"type": "contract_call", "contract_identifier": "ST13F481SBR0R7Z6NMMH8YV2FJJYXA5JPA0AD3HP9.subnet-v1", "method": "commit-block"}}]}
                ]
            },
            "expected_output": "triggered=true\napply_block_count=1\nmatched_transactions=0x93c89ffdac77ed2ba52611563bd491f56f5d558e23d311a105663ae32bdf18e5\n"
        },
        {
            "input": {
                "predicate": {"scope": "contract_deployment", "implement_trait": "sip09"},
                "blocks": [
                    {"transactions": [{"txid": "0x93c89ffdac77ed2ba52611563bd491f56f5d558e23d311a105663ae32bdf18e5", "kind": {"type": "contract_deployment", "contract_identifier": "ST13F481SBR0R7Z6NMMH8YV2FJJYXA5JPA0AD3HP9.subnet-v1"}}]},
                    {"transactions": [{"txid": "0xb92c2ade84a8b85f4c72170680ae42e65438aea4db72ba4b2d6a6960f4141ce8", "kind": {"type": "contract_call", "contract_identifier": "ST13F481SBR0R7Z6NMMH8YV2FJJYXA5JPA0AD3HP9.subnet-v1", "method": "commit-block"}}]}
                ]
            },
            "expected_output": "triggered=false\napply_block_count=0\nmatched_transactions=\n"
        }
    ]
}
```

---

### Feature 6: Contract-Call Predicate

**As a developer**, I want to select contract-call transactions by their target contract and method, so I can react to a specific function being invoked.

**Expected Behavior / Usage:**

The predicate (`scope` = `contract_call`) names a `contract_identifier` and a `method`. A contract-call transaction matches when BOTH its called `contract_identifier` equals the predicate's value AND its invoked `method` equals the predicate's value. A wrong method or a wrong contract identifier disqualifies the transaction. Only transactions whose kind is a contract call can match; deployments and native transfers are never selected, so a mixed block stream yields only the matching calls.

**Test Cases:** `rcb_tests/public_test_cases/feature6_contract_call.json`

```json
{
    "description": "Evaluate a contract-call predicate against a sequence of blocks that may contain both contract-call and contract-deployment transactions. The predicate names a target contract identifier and a target method name. A contract-call transaction is selected when both its called contract identifier and its invoked method name equal the values named by the predicate. Only contract-call transactions can be selected. The report states whether any block was selected, how many blocks were selected, and the identifiers of the matched transactions.",
    "cases": [
        {
            "input": {
                "predicate": {"scope": "contract_call", "contract_identifier": "ST13F481SBR0R7Z6NMMH8YV2FJJYXA5JPA0AD3HP9.subnet-v1", "method": "commit-block"},
                "blocks": [
                    {"transactions": [{"txid": "0xb92c2ade84a8b85f4c72170680ae42e65438aea4db72ba4b2d6a6960f4141ce8", "kind": {"type": "contract_call", "contract_identifier": "ST13F481SBR0R7Z6NMMH8YV2FJJYXA5JPA0AD3HP9.subnet-v1", "method": "commit-block"}}]},
                    {"transactions": [{"txid": "0x93c89ffdac77ed2ba52611563bd491f56f5d558e23d311a105663ae32bdf18e5", "kind": {"type": "contract_deployment", "contract_identifier": "ST13F481SBR0R7Z6NMMH8YV2FJJYXA5JPA0AD3HP9.subnet-v1"}}]}
                ]
            },
            "expected_output": "triggered=true\napply_block_count=1\nmatched_transactions=0xb92c2ade84a8b85f4c72170680ae42e65438aea4db72ba4b2d6a6960f4141ce8\n"
        },
        {
            "input": {
                "predicate": {"scope": "contract_call", "contract_identifier": "ST13F481SBR0R7Z6NMMH8YV2FJJYXA5JPA0AD3HP9.subnet-v1", "method": "wrong-method"},
                "blocks": [
                    {"transactions": [{"txid": "0xb92c2ade84a8b85f4c72170680ae42e65438aea4db72ba4b2d6a6960f4141ce8", "kind": {"type": "contract_call", "contract_identifier": "ST13F481SBR0R7Z6NMMH8YV2FJJYXA5JPA0AD3HP9.subnet-v1", "method": "commit-block"}}]},
                    {"transactions": [{"txid": "0x93c89ffdac77ed2ba52611563bd491f56f5d558e23d311a105663ae32bdf18e5", "kind": {"type": "contract_deployment", "contract_identifier": "ST13F481SBR0R7Z6NMMH8YV2FJJYXA5JPA0AD3HP9.subnet-v1"}}]}
                ]
            },
            "expected_output": "triggered=false\napply_block_count=0\nmatched_transactions=\n"
        }
    ]
}
```

---

### Feature 7: Transaction-Id Predicate

**As a developer**, I want to select a transaction by its exact identifier hash, so I can locate one specific transaction regardless of its kind.

**Expected Behavior / Usage:**

The predicate (`scope` = `txid`) names an exact identifier hash under `equals`. A transaction matches when its `txid` equals that value exactly. The transaction's kind is irrelevant — a call, a deployment, or a transfer all qualify if the hash matches. A hash that is not present in any block selects nothing.

**Test Cases:** `rcb_tests/public_test_cases/feature7_txid.json`

```json
{
    "description": "Evaluate a transaction-identifier predicate against a sequence of blocks. The predicate names an exact transaction identifier hash. A transaction is selected when its identifier hash equals the named value, regardless of the transaction's kind. The report states whether any block was selected, how many blocks were selected, and the identifiers of the matched transactions.",
    "cases": [
        {
            "input": {
                "predicate": {"scope": "txid", "equals": "0xb92c2ade84a8b85f4c72170680ae42e65438aea4db72ba4b2d6a6960f4141ce8"},
                "blocks": [
                    {"transactions": [{"txid": "0xb92c2ade84a8b85f4c72170680ae42e65438aea4db72ba4b2d6a6960f4141ce8", "kind": {"type": "contract_call", "contract_identifier": "ST13F481SBR0R7Z6NMMH8YV2FJJYXA5JPA0AD3HP9.subnet-v1", "method": "commit-block"}}]},
                    {"transactions": [{"txid": "0x93c89ffdac77ed2ba52611563bd491f56f5d558e23d311a105663ae32bdf18e5", "kind": {"type": "contract_deployment", "contract_identifier": "ST13F481SBR0R7Z6NMMH8YV2FJJYXA5JPA0AD3HP9.subnet-v1"}}]}
                ]
            },
            "expected_output": "triggered=true\napply_block_count=1\nmatched_transactions=0xb92c2ade84a8b85f4c72170680ae42e65438aea4db72ba4b2d6a6960f4141ce8\n"
        },
        {
            "input": {
                "predicate": {"scope": "txid", "equals": "wrong-id"},
                "blocks": [
                    {"transactions": [{"txid": "0xb92c2ade84a8b85f4c72170680ae42e65438aea4db72ba4b2d6a6960f4141ce8", "kind": {"type": "contract_call", "contract_identifier": "ST13F481SBR0R7Z6NMMH8YV2FJJYXA5JPA0AD3HP9.subnet-v1", "method": "commit-block"}}]},
                    {"transactions": [{"txid": "0x93c89ffdac77ed2ba52611563bd491f56f5d558e23d311a105663ae32bdf18e5", "kind": {"type": "contract_deployment", "contract_identifier": "ST13F481SBR0R7Z6NMMH8YV2FJJYXA5JPA0AD3HP9.subnet-v1"}}]}
                ]
            },
            "expected_output": "triggered=false\napply_block_count=0\nmatched_transactions=\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the predicate-matching engine described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core matching logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin (`{"predicate": ..., "blocks": [...]}`), evaluates the predicate against the blocks via the core engine, and prints the three-line report described above (`triggered=...`, `apply_block_count=...`, `matched_transactions=...`).

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- utilize the default sorting key from Block.java
- handle the catch-all config for contract lookup
