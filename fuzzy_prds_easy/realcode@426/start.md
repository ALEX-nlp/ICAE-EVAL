## Product Requirement Document

# Chain State and Transaction Indexing Toolkit - Black-Box Behavior Contract

## Project Goal

Build a Bitcoin chain-state and transaction-indexing toolkit that allows developers to maintain local checkpoint chains, track wallet-relevant transaction outputs, calculate fees, derive receiving scripts, and filter canonical transaction history without manually reconciling block reorganizations, duplicate outputs, or conflicting spends.

---

## Background & Problem

Without this library/tool, developers are forced to keep ad hoc maps of block checkpoints, transaction outputs, script usage, and spend relationships. This leads to repetitive reconciliation code, missed reorganization edge cases, incorrect balance buckets, and fragile conflict handling when multiple transactions spend the same output.

With this library/tool, applications can submit compact chain and transaction observations and receive deterministic, queryable results for chain updates, indexed outputs, fee calculations, derivation state, and canonical transaction visibility.

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

### Feature 1: Local Chain Updates

**As a developer**, I want to apply updates of ordered block checkpoints to a local chain record, so I can merge new tips, older checkpoints, reorganizations, and disconnected updates without manually rewriting chain state.

**Expected Behavior / Usage:**

The input is a single adapter command naming a checkpoint-update scenario. The output is either `result=applied` followed by a bracketed `changeset` and the resulting `chain`, or `error=cannot_connect` with the earliest height that must be included to connect the update. Hashes are wire-format block identifiers, and `<removed>` marks a checkpoint invalidated by a reorganization.

**Test Cases:** `rcb_tests/public_test_cases/feature1_local_chain_updates.json`

```json
{
    "description": "Apply checkpoint-chain updates to an existing chain, reporting either the exact applied checkpoint changes and final chain or a normalized connection error.",
    "cases": [
        {
            "input": "local_chain_update:add_first_tip",
            "expected_output": "result=applied\nchangeset=[0:425ea523fee4a4451246a49a08174424ee3fdc03d40926ad46ffe0e671efd61c]\nchain=[0:425ea523fee4a4451246a49a08174424ee3fdc03d40926ad46ffe0e671efd61c]\n"
        },
        {
            "input": "local_chain_update:two_points_of_agreement",
            "expected_output": "result=applied\nchangeset=[0:425ea523fee4a4451246a49a08174424ee3fdc03d40926ad46ffe0e671efd61c,3:2e52efc7b8cab2e0ca3f688ae090febff94be0eaa3ce666301985b287fc6e178]\nchain=[0:425ea523fee4a4451246a49a08174424ee3fdc03d40926ad46ffe0e671efd61c,1:01517aea572935ff9eb1455bc1147f98fb60957f4f9f868f06824ede3bb0550b,2:ea3f6455fc84430d6f2db40d708a046caab99ad8207d14e43b2f1ffd68894fca,3:2e52efc7b8cab2e0ca3f688ae090febff94be0eaa3ce666301985b287fc6e178]\n"
        },
        {
            "input": "local_chain_update:transitive_invalidation",
            "expected_output": "result=applied\nchangeset=[2:4a05b7aa85ed877a8f60fa1e7f3a3d914a9927f5f6502010bef0a769f9be6b7f,3:118102ef170982195e8fef18d5963365af29e6111f56434a4d860d09f9dedea9,4:2e52efc7b8cab2e0ca3f688ae090febff94be0eaa3ce666301985b287fc6e178,5:<removed>]\nchain=[0:425ea523fee4a4451246a49a08174424ee3fdc03d40926ad46ffe0e671efd61c,2:4a05b7aa85ed877a8f60fa1e7f3a3d914a9927f5f6502010bef0a769f9be6b7f,3:118102ef170982195e8fef18d5963365af29e6111f56434a4d860d09f9dedea9,4:2e52efc7b8cab2e0ca3f688ae090febff94be0eaa3ce666301985b287fc6e178]\n"
        },
        {
            "input": "local_chain_update:disjoint_short",
            "expected_output": "error=cannot_connect\ntry_include_height=0\n"
        }
    ]
}
```

---

### Feature 2: Local Chain Insertions

**As a developer**, I want to insert one checkpoint into an existing local chain, so I can accept new historical or tip checkpoints while rejecting same-height conflicts safely.

**Expected Behavior / Usage:**

The input names one single-checkpoint insertion scenario. The output reports `result=inserted`, the exact checkpoint change, and the final chain when insertion is accepted. If the inserted height already exists with a different block identifier, the output uses `error=conflicting_block` and includes the height, original hash, update hash, and unchanged chain.

**Test Cases:** `rcb_tests/public_test_cases/feature2_local_chain_insertions.json`

```json
{
    "description": "Insert one checkpoint into a local chain, preserving the chain on conflicts and reporting the exact accepted change or normalized conflict details.",
    "cases": [
        {
            "input": "local_chain_insert:empty_at_height_5",
            "expected_output": "result=inserted\nchangeset=[5:43a3981aeb4807c76222f6d84f5ba371f1b5158dd49d3f28a958bb1f270558e1]\nchain=[5:43a3981aeb4807c76222f6d84f5ba371f1b5158dd49d3f28a958bb1f270558e1]\n"
        },
        {
            "input": "local_chain_insert:conflicting_same_height",
            "expected_output": "error=conflicting_block\nheight=2\noriginal_hash=cf2bb50677d427c231a0b22bf60fceb3a2716b78c6abae0a1e948b8f1812c3ff\nupdate_hash=d6531d1c9bbc6d9d6771f1c2be3c7ed6341e731a6c1ebc1e9978198013fd3889\nchain=[2:cf2bb50677d427c231a0b22bf60fceb3a2716b78c6abae0a1e948b8f1812c3ff]\n"
        }
    ]
}
```

---

### Feature 3: Script Value Accounting

**As a developer**, I want to measure value flow for transactions involving tracked output scripts, so I can display wallet-relevant sent, received, and net amounts without hand-counting inputs and outputs.

**Expected Behavior / Usage:**

The input names a transaction-value scenario over a set of tracked locking scripts. The output always contains `sent`, `received`, and `net` satoshi amounts. Incoming transactions to tracked scripts count as received even before scanning, while later transactions spending a previously scanned tracked output count that previous value as sent and any tracked outputs as received.

**Test Cases:** `rcb_tests/public_test_cases/feature3_script_value_accounting.json`

```json
{
    "description": "Track registered locking scripts and report sent, received, and net value for transactions before and after scanning prior outputs.",
    "cases": [
        {
            "input": "script_value:incoming_before_scan",
            "expected_output": "[the specific output prefixes for script balance counters (e.g., 'sent=', '[the specific output prefixes for script balance counters (e.g., 'sent=', 'received=', '[the specific output prefixes for script balance counters (e.g., 'sent=', 'received=', 'net=') — ask the implementation team for the exact string format]') — ask the implementation team for the exact string format]', '[the specific output prefixes for script balance counters (e.g., 'sent=', 'received=', 'net=') — ask the implementation team for the exact string format]') — ask the implementation team for the exact string format]0\n[the specific output prefixes for script balance counters (e.g., 'sent=', 'received=', '[the specific output prefixes for script balance counters (e.g., 'sent=', 'received=', 'net=') — ask the implementation team for the exact string format]') — ask the implementation team for the exact string format]42000\n[the specific output prefixes for script balance counters (e.g., 'sent=', 'received=', 'net=') — ask the implementation team for the exact string format]42000\n"
        },
        {
            "input": "script_value:spend_after_scan",
            "expected_output": "[the specific output prefixes for script balance counters (e.g., 'sent=', '[the specific output prefixes for script balance counters (e.g., 'sent=', 'received=', '[the specific output prefixes for script balance counters (e.g., 'sent=', 'received=', 'net=') — ask the implementation team for the exact string format]') — ask the implementation team for the exact string format]', '[the specific output prefixes for script balance counters (e.g., 'sent=', 'received=', 'net=') — ask the implementation team for the exact string format]') — ask the implementation team for the exact string format]42000\n[the specific output prefixes for script balance counters (e.g., 'sent=', 'received=', '[the specific output prefixes for script balance counters (e.g., 'sent=', 'received=', 'net=') — ask the implementation team for the exact string format]') — ask the implementation team for the exact string format]50000\n[the specific output prefixes for script balance counters (e.g., 'sent=', 'received=', 'net=') — ask the implementation team for the exact string format]8000\n"
        }
    ]
}
```

---

### Feature 4: Script Usage State

**As a developer**, I want to track whether registered output scripts are unused or used, so I can avoid reusing scripts once they have been manually reserved or observed on-chain.

**Expected Behavior / Usage:**

The input names a script-usage state transition. The output reports booleans for whether manual marking changed state, whether the script is currently used, and whether a scanned output prevents an attempted unmark. Unknown script identifiers cannot be marked back to unused and must not create invalid unused entries.

**Test Cases:** `rcb_tests/public_test_cases/feature4_script_usage_state.json`

```json
{
    "description": "Maintain whether tracked locking scripts are unused, manually used, or made permanently used by scanned outputs.",
    "cases": [
        {
            "input": "script_usage:manual_marking",
            "expected_output": "[a specific binary flag indicating the script usage state (e.g., 'initial_used=false' or '[a specific binary flag indicating the script usage state (e.g., 'initial_used=false' or 'mark_changed=true') — refer to the script_usage module test output for the exact string]') — refer to the script_usage module test output for the exact string]\n[a specific binary flag indicating the script usage state (e.g., 'initial_used=false' or 'mark_changed=true') — refer to the script_usage module test output for the exact string]\n[a specific binary flag indicating the script usage state (e.g., 'initial_used=false' or 'mark_changed=true') — refer to the script_usage module test output for the exact string]\nun[a specific binary flag indicating the script usage state (e.g., 'initial_used=false' or 'mark_changed=true') — refer to the script_usage module test output for the exact string]\n[a specific binary flag indicating the script usage state (e.g., 'initial_used=false' or 'mark_changed=true') — refer to the script_usage module test output for the exact string]\n"
        },
        {
            "input": "script_usage:scanned_output_stays_used",
            "expected_output": "[a specific binary flag indicating the script usage state (e.g., 'initial_used=false' or 'mark_changed=true') — refer to the script_usage module test output for the exact string]\n[a specific binary flag indicating the script usage state (e.g., 'initial_used=false' or 'mark_changed=true') — refer to the script_usage module test output for the exact string]\n[a specific binary flag indicating the script usage state (e.g., 'initial_used=false' or 'mark_changed=true') — refer to the script_usage module test output for the exact string]\n"
        }
    ]
}
```

---

### Feature 5: Transaction Fee Calculation

**As a developer**, I want to calculate transaction fees from known previous outputs, so I can separate valid fee results from missing-input and negative-fee conditions.

**Expected Behavior / Usage:**

The input names a fee-calculation scenario. A valid transaction outputs `fee=<satoshis>`. A transaction whose known inputs sum to less than outputs outputs `error=negative_fee` and the signed amount. A transaction that spends an unknown previous output outputs `error=missing_previous_output` and a missing count. Coinbase-like transactions have fee zero.

**Test Cases:** `rcb_tests/public_test_cases/feature5_transaction_fee_calculation.json`

```json
{
    "description": "Calculate transaction fee from known previous outputs and normalize negative-fee or missing-input conditions.",
    "cases": [
        {
            "input": "fee:positive_fee",
            "expected_output": "fee=100\n"
        },
        {
            "input": "fee:negative_fee",
            "expected_output": "error=negative_fee\namount=-200\n"
        },
        {
            "input": "fee:missing_input",
            "expected_output": "error=missing_previous_output\nmissing_count=1\n"
        }
    ]
}
```

---

### Feature 6: Output Precedence

**As a developer**, I want to resolve duplicate knowledge about the same transaction output, so I can prefer authoritative full-transaction outputs over floating output records.

**Expected Behavior / Usage:**

The input names an ordering scenario where a floating output record and a full transaction describe the same outpoint. The output reports the selected value for output zero and whether output one exists. Regardless of whether floating records arrive before or after the full transaction, the full transaction output remains authoritative and nonexistent outputs stay absent.

**Test Cases:** `rcb_tests/public_test_cases/feature6_output_precedence.json`

```json
{
    "description": "Resolve conflicts between floating output records and full transaction records by giving the full transaction output authoritative value.",
    "cases": [
        {
            "input": "txout_precedence:full_replaces_floating",
            "expected_output": "vout0_value=42000\nvout1_pre[the specific output prefixes for script balance counters (e.g., 'sent=', '[the specific output prefixes for script balance counters (e.g., 'sent=', 'received=', '[the specific output prefixes for script balance counters (e.g., 'sent=', 'received=', 'net=') — ask the implementation team for the exact string format]') — ask the implementation team for the exact string format]', '[the specific output prefixes for script balance counters (e.g., 'sent=', 'received=', 'net=') — ask the implementation team for the exact string format]') — ask the implementation team for the exact string format]false\n"
        },
        {
            "input": "txout_precedence:floating_does_not_replace_full",
            "expected_output": "vout0_value=42000\nvout1_pre[the specific output prefixes for script balance counters (e.g., 'sent=', '[the specific output prefixes for script balance counters (e.g., 'sent=', 'received=', '[the specific output prefixes for script balance counters (e.g., 'sent=', 'received=', 'net=') — ask the implementation team for the exact string format]') — ask the implementation team for the exact string format]', '[the specific output prefixes for script balance counters (e.g., 'sent=', 'received=', 'net=') — ask the implementation team for the exact string format]') — ask the implementation team for the exact string format]false\n"
        }
    ]
}
```

---

### Feature 7: Spend Tracking

**As a developer**, I want to track spend edges between transactions, so I can query spenders consistently regardless of insertion order while ignoring null coinbase inputs.

**Expected Behavior / Usage:**

The input names a spend-tracking scenario. The output reports counts of spenders or whether two insertion orders produce identical spender sets. Coinbase/null previous-output inputs must not create ordinary spend edges, while ordinary inputs must register exactly one spender whether the spending transaction arrives before or after the funding transaction.

**Test Cases:** `rcb_tests/public_test_cases/feature7_spend_tracking.json`

```json
{
    "description": "Track transaction spends independently from insertion order while ignoring coinbase null inputs as spend edges.",
    "cases": [
        {
            "input": "spend_tracking:coinbase_not_spent",
            "expected_output": "null_outpoint_spenders=0\nzero_tx_spends=0\n"
        },
        {
            "input": "spend_tracking:insertion_order_independent",
            "expected_output": "graph1_spenders=1\ngraph2_spenders=1\nsame_spenders=true\n"
        }
    ]
}
```

---

### Feature 8: Script Derivation

**As a developer**, I want to derive and scan deterministic script sequences, so I can manage lookahead windows, used gaps, and fixed single-script templates predictably.

**Expected Behavior / Usage:**

The input names a deterministic script-derivation scenario. The output reports last revealed indices, change counts, lookahead scan effects, next unused indices, and total script counts. Target revelation is idempotent, lookahead scanning extends only when the matched index is within range, unused selection fills gaps before deriving new scripts, and fixed single-script templates never create additional derived scripts.

**Test Cases:** `rcb_tests/public_test_cases/feature8_script_derivation.json`

```json
{
    "description": "Reveal and scan deterministic script derivations with target indices, lookahead windows, unused-script selection, and non-wildcard descriptors.",
    "cases": [
        {
            "input": "derivation:set_targets",
            "expected_output": "external_last=12\ninternal_last=24\nfirst_changes=2\nsecond_changes_empty=true\n"
        },
        {
            "input": "derivation:lookahead_scan_limit",
            "expected_output": "scan_0_changed=1\nscan_0_last_revealed=0\nscan_0_last_used=0\nscan_10_changed=1\nscan_10_last_revealed=10\nscan_10_last_used=10\nscan_20_changed=1\nscan_20_last_revealed=20\nscan_20_last_used=20\nscan_30_changed=1\nscan_30_last_revealed=30\nscan_30_last_used=30\nscan_41_changed=0\nlast_revealed=30\nlast_used=30\n"
        },
        {
            "input": "derivation:wildcard_unused",
            "expected_output": "initial_next_index=0\ninitial_next_is_new=true\ninitial_reveal_changes=1\ninitial_unused_changes=0\nnext_after_reveal_to_25=26\nnext_after_reveal_to_25_is_new=true\nreveal_26_changes=1\nnext_unused_after_gaps=16\nnext_unused_after_gaps_changes=0\nnext_unused_after_all_used=27\nnext_unused_after_all_used_changes=1\n"
        },
        {
            "input": "derivation:non_wildcard",
            "expected_output": "initial_next_index=0\ninitial_next_is_new=true\nfirst_reveal_changes=1\nfirst_unused_changes=0\nnext_after_reveal_index=0\nnext_after_reveal_is_new=false\nsecond_reveal_changes=0\nsecond_unused_changes=0\nreveal_to_200_count=0\nreveal_to_200_changes_empty=true\ntotal_scripts=1\n"
        }
    ]
}
```

---

### Feature 9: Chain Conflict Filtering

**As a developer**, I want to select canonical transaction history from conflicting spends, so I can list chain-visible transactions, outputs, unspents, and balances across confirmed and unconfirmed conflicts.

**Expected Behavior / Usage:**

The input names a transaction-conflict scenario. The output includes canonical `chain_txs`, visible `chain_txouts`, currently spendable `unspents`, and categorized balance lines. Confirmed transactions on the active chain override conflicting unconfirmed transactions; among unconfirmed conflicts, recency and descendants determine the canonical branch; outputs or descendants from non-canonical branches are excluded.

**Test Cases:** `rcb_tests/public_test_cases/feature9_chain_conflict_filtering.json`

```json
{
    "description": "Filter transaction histories to canonical chain-visible transactions, outputs, unspents, and balances across confirmed and unconfirmed conflicts.",
    "cases": [
        {
            "input": "conflict:coinbase_and_confirmed_conflict",
            "expected_output": "chain_txs=[confirmed_conflict,confirmed_genesis]\nchain_txouts=[confirmed_conflict:0,confirmed_genesis:0]\nunspents=[confirmed_conflict:0]\nbalance_immature=0\nbalance_trusted_pending=0\nbalance_untrusted_pending=0\nbalance_confirmed=20000\nexpected_chain_txs=[confirmed_conflict,confirmed_genesis]\nexpected_chain_txouts=[confirmed_conflict:0,confirmed_genesis:0]\nexpected_unspents=[confirmed_conflict:0]\nbalance_immature=0\nbalance_trusted_pending=0\nbalance_untrusted_pending=0\nbalance_confirmed=20000\n"
        },
        {
            "input": "conflict:newer_unconfirmed_wins",
            "expected_output": "chain_txs=[tx1,tx_conflict_2]\nchain_txouts=[tx1:0,tx1:1,tx_conflict_2:0]\nunspents=[tx_conflict_2:0]\nbalance_immature=0\nbalance_trusted_pending=30000\nbalance_untrusted_pending=0\nbalance_confirmed=0\nexpected_chain_txs=[tx1,tx_conflict_2]\nexpected_chain_txouts=[tx1:0,tx1:1,tx_conflict_2:0]\nexpected_unspents=[tx_conflict_2:0]\nbalance_immature=0\nbalance_trusted_pending=30000\nbalance_untrusted_pending=0\nbalance_confirmed=0\n"
        },
        {
            "input": "conflict:confirmed_wins_over_mempool",
            "expected_output": "chain_txs=[tx1,tx_confirmed_conflict]\nchain_txouts=[tx1:0,tx_confirmed_conflict:0]\nunspents=[tx_confirmed_conflict:0]\nbalance_immature=0\nbalance_trusted_pending=0\nbalance_untrusted_pending=0\nbalance_confirmed=50000\nexpected_chain_txs=[tx1,tx_confirmed_conflict]\nexpected_chain_txouts=[tx1:0,tx_confirmed_conflict:0]\nexpected_unspents=[tx_confirmed_conflict:0]\nbalance_immature=0\nbalance_trusted_pending=0\nbalance_untrusted_pending=0\nbalance_confirmed=50000\n"
        },
        {
            "input": "conflict:descendant_can_make_older_branch_canonical",
            "expected_output": "chain_txs=[A,B,C]\nchain_txouts=[A:0,B:0,C:0]\nunspents=[C:0]\nbalance_immature=0\nbalance_trusted_pending=30000\nbalance_untrusted_pending=0\nbalance_confirmed=0\nexpected_chain_txs=[A,B,C]\nexpected_chain_txouts=[A:0,B:0,C:0]\nexpected_unspents=[C:0]\nbalance_immature=0\nbalance_trusted_pending=30000\nbalance_untrusted_pending=0\nbalance_confirmed=0\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin or an equivalent harness-provided command argument, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_local_chain_updates.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_local_chain_updates@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- full_replaces_floating
- same_spenders=true
