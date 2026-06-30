## Product Requirement Document

# Decision-Tree Ensemble Compiler & Predictor — Functional Requirements

## Project Goal

Build a toolkit that turns a *trained* decision-tree ensemble (a gradient-boosted forest exported by a training framework) into a fast, standalone native predictor, and that lets developers introspect, prune, serialize and run that ensemble through one consistent interface. Developers should be able to load a model, ask what it expects and produces, compile it into a runnable artifact, and score data — without re-implementing tree-traversal logic or hand-writing prediction code for each model.

---

## Background & Problem

Without this toolkit, developers who want to deploy a trained tree ensemble must either ship the original training framework into production (heavy, slow, dependency-laden) or hand-translate each model's split structure into bespoke scoring code (tedious, error-prone, and impossible to keep in sync as models change). They also lack a uniform way to inspect a model's shape, trim it to fewer trees, convert between on-disk formats, or guarantee that an optimized build produces the same numbers as a naive one.

With this toolkit, a trained ensemble becomes a black box with a small, predictable contract: load it, query its metadata, compile it once into a native predictor, and score either whole batches or single rows. Models from different training frameworks (gradient-boosted forests and ensembles using categorical splits) are normalized into one internal representation, can be round-tripped through a portable interchange buffer, and can be tuned for build size/speed without ever changing the predictions.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a non-trivial system spanning model loading, an internal model representation, a compiler that emits native code, a runtime predictor, and (de)serialization. It MUST be organized as a multi-module repository with clear separation between the model representation, the compiler, the runtime predictor, the (de)serializer, and the I/O adapter. Do not collapse these responsibilities into a single file.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases in "Core Features" are a **black-box contract for the execution adapter only**, not the core data model. The compiler, runtime and model representation MUST be fully decoupled from stdin/stdout and JSON. The adapter alone translates JSON commands into idiomatic calls on the core objects and renders results to stdout.

3. **Adherence to SOLID Design Principles:** Separate parsing, routing, validation, core execution, and output formatting into distinct units. The compiler must be open for extension (new output formats / tuning options) but closed for modification; substitutable model and predictor abstractions; small cohesive interfaces; high-level flows depend on abstractions, not on the concrete I/O layer.

4. **Robustness & Interface Design:** The public interface must be idiomatic and hide internal complexity. Edge cases — too-wide input, invalid prune limits, missing-value encodings — must be handled deterministically and modeled as explicit error categories rather than generic faults. Error reporting is a rendering concern of the adapter; the core may raise idiomatic errors, but the externally visible contract uses neutral, language-independent error categories.

---

## Core Features

The execution adapter reads one JSON object from stdin describing an action and its operands, performs it against the core system, and prints a small set of `key=value` lines to stdout (one per line, trailing newline). Numeric output is rendered with fixed 6-decimal precision. Errors are rendered as a neutral `error=<category>` line plus supporting fields — never as host-language exception text.

Three reference ensembles are referenced by neutral identifiers throughout:
- `binary_mushroom` — a small binary classifier (sigmoid output).
- `multiclass_dermatology` — a 6-class classifier (softmax output).
- `categorical_toy` — a single-output regressor whose trees use categorical (set-membership) splits.

---

### Feature 1: Ensemble Metadata

**As a developer**, I want to load a trained ensemble and read back its structural metadata, so I can verify I loaded the right model and know how many features it expects before feeding it data.

**Expected Behavior / Usage:**

Given a request naming a model, the system loads the serialized ensemble and reports three facts: the number of trees in the ensemble (`num_tree`), the number of input features the model expects (`num_feature`), and the number of output groups it produces (`num_output_group`, 1 for a binary classifier or single-output regressor, one-per-class for a multiclass classifier). Output is exactly three lines, `num_tree=<int>` then `num_feature=<int>` then `num_output_group=<int>`. Loading uses the format implied by the model identifier; the caller does not need to specify it.

**Test Cases:** `rcb_tests/public_test_cases/feature1_ensemble_metadata.json`

```json
{
    "description": "Load a serialized gradient-boosted tree ensemble and report its tree count, the number of input features it expects, and the number of output groups it produces.",
    "cases": [
        {
            "input": {"action": "model_metadata", "dataset": "binary_mushroom"},
            "expected_output": "num_tree=2\nnum_feature=127\nnum_output_group=1\n"
        },
        {
            "input": {"action": "model_metadata", "dataset": "multiclass_dermatology"},
            "expected_output": "num_tree=60\nnum_feature=33\nnum_output_group=6\n"
        }
    ]
}
```

---

### Feature 2: Tree-Limit Pruning

**As a developer**, I want to truncate an ensemble to only its first N trees, so I can trade a small amount of accuracy for faster scoring or study how many trees are actually needed.

**Expected Behavior / Usage:**

Given a model and an integer `limit`, the system keeps only the first `limit` trees and reports the resulting active tree count as `num_tree=<int>`. A `limit` is valid when it is at least 1 and does not exceed the model's current tree count. An invalid limit (zero, negative, or larger than the available trees) is rejected: the ensemble is left unchanged and the output is the neutral category `error=invalid_tree_limit`, followed by the requested limit and the model's actual tree count. The error path never leaks any host-language exception type.

**Test Cases:** `rcb_tests/public_test_cases/feature2_tree_limit.json`

```json
{
    "description": "Truncate an ensemble to keep only its first N trees. Valid limits in the range 1..tree_count update the active tree count; a limit of zero or a limit exceeding the available trees is rejected as invalid.",
    "cases": [
        {
            "input": {"action": "set_tree_limit", "dataset": "multiclass_dermatology", "limit": 30},
            "expected_output": "num_tree=30\n"
        },
        {
            "input": {"action": "set_tree_limit", "dataset": "binary_mushroom", "limit": 1},
            "expected_output": "num_tree=1\n"
        },
        {
            "input": {"action": "set_tree_limit", "dataset": "binary_mushroom", "limit": 0},
            "expected_output": "error=invalid_tree_limit\nrequested=0\nmodel_tree_count=2\n"
        },
        {
            "input": {"action": "set_tree_limit", "dataset": "binary_mushroom", "limit": 3},
            "expected_output": "error=invalid_tree_limit\nrequested=3\nmodel_tree_count=2\n"
        }
    ]
}
```

---

### Feature 3: Compiled Predictor Metadata

**As a developer**, I want to compile a loaded ensemble into a runnable predictor and inspect the predictor's runtime properties, so I can confirm its input width, output shape, and the post-processing transform that turns raw scores into final outputs.

**Expected Behavior / Usage:**

The system compiles the ensemble into a native predictor and reports five properties: the feature count (`num_feature`), the number of output groups / classes (`num_output_group`, 1 for binary or single-output regression), the name of the post-processing transform applied to raw margins (`pred_transform`, e.g. `sigmoid` for a binary classifier, `softmax` for a multiclass one), the global bias added to every margin (`global_bias`), and the sigmoid steepness parameter (`sigmoid_alpha`). Numeric properties are rendered with 6-decimal precision; `-0` is normalized to `0`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_predictor_metadata.json`

```json
{
    "description": "After compiling an ensemble into a runnable predictor, expose the predictor's feature count, output-group count, post-processing transform name, global bias and sigmoid alpha.",
    "cases": [
        {
            "input": {"action": "predictor_metadata", "dataset": "binary_mushroom"},
            "expected_output": "num_feature=127\nnum_output_group=1\npred_transform=sigmoid\nglobal_bias=0.000000\nsigmoid_alpha=1.000000\n"
        },
        {
            "input": {"action": "predictor_metadata", "dataset": "multiclass_dermatology"},
            "expected_output": "num_feature=33\nnum_output_group=6\npred_transform=softmax\nglobal_bias=0.500000\nsigmoid_alpha=1.000000\n"
        }
    ]
}
```

---

### Feature 4: Batch Prediction

**As a developer**, I want to score a whole sparse data matrix at once and get a compact, verifiable summary of the output, so I can validate predictions in bulk without dumping thousands of rows.

**Expected Behavior / Usage:**

A batch request compiles the predictor and scores the model's companion test matrix. Two output modes are available: the default **probability** mode applies the model's post-processing transform; **margin** mode (`pred_margin: true`) returns the raw additive scores before any transform. Each run reports four lines: `num_row` (rows scored), `num_col` (values per row — 1 for binary/regression, one per class for multiclass), `row0` (the comma-separated 6-decimal values of the first row), and `mean` (the mean of all output values). For multiclass, `num_col` equals the class count and `row0` is the full per-class vector for the first row.

*4.1 Binary classifier batch — single value per row, sigmoid-transformed probabilities vs. raw margins.*

A binary classifier yields one value per row. In probability mode the values are sigmoid-squashed into (0,1); in margin mode they are the raw log-odds-style scores.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_binary_batch.json`

```json
{
    "description": "Run batch prediction over a sparse test matrix for a binary classifier, returning either the post-processed probability output or the raw margin output; report the row count, the per-row width, the first row's values and the mean over all outputs.",
    "cases": [
        {
            "input": {"action": "predict_batch", "dataset": "binary_mushroom"},
            "expected_output": "num_row=1583\nnum_col=1\nrow0=0.110274\nmean=0.488999\n"
        },
        {
            "input": {"action": "predict_batch", "dataset": "binary_mushroom", "pred_margin": true},
            "expected_output": "num_row=1583\nnum_col=1\nrow0=-2.087944\nmean=-0.106025\n"
        }
    ]
}
```

*4.2 Multiclass classifier batch — one value per class per row, softmax probabilities vs. raw margins.*

A multiclass classifier yields one value per class for each row. `num_col` equals the number of classes and `row0` is the first row's full class vector.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_multiclass_batch.json`

```json
{
    "description": "Run batch prediction for a multiclass classifier, producing one value per class for each row; report the per-row width and the first row's vector for both the probability and the raw margin output.",
    "cases": [
        {
            "input": {"action": "predict_batch", "dataset": "multiclass_dermatology"},
            "expected_output": "num_row=110\nnum_col=6\nrow0=0.083662,0.088542,0.083608,0.577178,0.083545,0.083466\nmean=0.166667\n"
        },
        {
            "input": {"action": "predict_batch", "dataset": "multiclass_dermatology", "pred_margin": true},
            "expected_output": "num_row=110\nnum_col=6\nrow0=-0.059313,-0.002621,-0.059962,1.872051,-0.060716,-0.061665\nmean=0.317861\n"
        }
    ]
}
```

*4.3 Categorical-split regressor batch — single regression value per row.*

An ensemble whose trees branch on categorical (set-membership) conditions scores a single regression value per row in margin mode.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_categorical_margin.json`

```json
{
    "description": "Run batch margin prediction for an ensemble trained with categorical splits, returning a single regression value per row.",
    "cases": [
        {
            "input": {"action": "predict_batch", "dataset": "categorical_toy", "pred_margin": true},
            "expected_output": "num_row=180\nnum_col=1\nrow0=-20.738508\nmean=-10.065133\n"
        }
    ]
}
```

---

### Feature 5: Single-Instance Prediction & Missing-Value Encodings

**As a developer**, I want to score one row at a time and supply it in whichever encoding my data pipeline produces, so I can serve low-latency single predictions and trust that equivalent inputs give identical results.

**Expected Behavior / Usage:**

A single-instance request scores one selected row of the model's test matrix and reports `num_output_group` followed by `values` (the comma-separated 6-decimal output vector — one value for binary/regression, one per class for multiclass). The same row may be supplied in three equivalent encodings, all of which MUST produce identical output: `sparse` (only the present entries), `dense_zero_missing` (a full dense vector where 0 marks an absent feature), and `dense_nan_missing` (a full dense vector where NaN marks an absent feature). Both probability (default) and `pred_margin: true` outputs are supported. This guarantees that the choice of input representation is purely a convenience and never changes the prediction.

**Test Cases:** `rcb_tests/public_test_cases/feature5_single_instance.json`

```json
{
    "description": "Predict for a single row supplied in several equivalent encodings: a sparse row, a dense row treating 0 as the missing-value marker, and a dense row treating NaN as the missing-value marker. All encodings of the same row must yield identical output, and both probability and margin outputs are supported.",
    "cases": [
        {
            "input": {"action": "predict_instance", "dataset": "binary_mushroom", "row_index": 0, "encoding": "sparse"},
            "expected_output": "num_output_group=1\nvalues=0.110274\n"
        },
        {
            "input": {"action": "predict_instance", "dataset": "binary_mushroom", "row_index": 0, "encoding": "dense_zero_missing"},
            "expected_output": "num_output_group=1\nvalues=0.110274\n"
        },
        {
            "input": {"action": "predict_instance", "dataset": "binary_mushroom", "row_index": 0, "encoding": "dense_nan_missing"},
            "expected_output": "num_output_group=1\nvalues=0.110274\n"
        },
        {
            "input": {"action": "predict_instance", "dataset": "binary_mushroom", "row_index": 4, "encoding": "sparse", "pred_margin": true},
            "expected_output": "num_output_group=1\nvalues=1.792405\n"
        },
        {
            "input": {"action": "predict_instance", "dataset": "multiclass_dermatology", "row_index": 0, "encoding": "sparse"},
            "expected_output": "num_output_group=6\nvalues=0.083662,0.088542,0.083608,0.577178,0.083545,0.083466\n"
        }
    ]
}
```

---

### Feature 6: Input Column-Count Adaptation

**As a developer**, I want the predictor to behave predictably when the input matrix's column count doesn't exactly match the model's feature count, so narrower inputs still score and over-wide inputs fail loudly instead of silently corrupting results.

**Expected Behavior / Usage:**

*6.1 Narrower input is zero-padded.*

When an input matrix declares fewer columns than the model expects, the missing trailing columns are treated as absent (zero) features and prediction proceeds normally. The output reports `num_row` and the comma-separated 6-decimal `values` (one per row). A fully empty narrow matrix therefore scores every row to the model's all-features-missing prediction.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_padded_matrix.json`

```json
{
    "description": "Predict over a sparse matrix that declares fewer columns than the model expects; the missing trailing columns are padded with zeros and prediction proceeds normally.",
    "cases": [
        {
            "input": {"action": "predict_padded", "dataset": "binary_mushroom", "nrow": 3, "ncol": 3},
            "expected_output": "num_row=3\nvalues=0.954569,0.954569,0.954569\n"
        }
    ]
}
```

*6.2 Wider input is rejected.*

When an input matrix declares more columns than the model expects, the request is rejected with the neutral category `error=too_many_features`, followed by the offending input width and the model's feature count. No prediction is produced and no host-language exception identity appears.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_too_wide_matrix.json`

```json
{
    "description": "Predict over a sparse matrix that declares more columns than the model expects; this is rejected as a feature-count mismatch.",
    "cases": [
        {
            "input": {"action": "predict_padded", "dataset": "binary_mushroom", "nrow": 3, "ncol": 1000},
            "expected_output": "error=too_many_features\ninput_features=1000\nmodel_features=127\n"
        }
    ]
}
```

---

### Feature 7: Serialization Round-Trip

**As a developer**, I want to serialize a loaded ensemble to a portable interchange buffer and reload it, so I can store, transmit, or convert models between formats while preserving their behavior exactly.

**Expected Behavior / Usage:**

The system serializes a loaded ensemble to a portable binary interchange buffer, reloads it from that buffer into a fresh model, compiles the reloaded model and scores its test matrix. The reported batch summary (`num_row`, `num_col`, `row0`, `mean`) MUST match what the original (un-serialized) model produces, confirming the round-trip is lossless. Both probability and margin modes are supported.

**Test Cases:** `rcb_tests/public_test_cases/feature7_serialization_roundtrip.json`

```json
{
    "description": "Serialize an ensemble to the interchange buffer format, reload it from that buffer, compile the reloaded model, and confirm predictions are preserved across the round-trip.",
    "cases": [
        {
            "input": {"action": "protobuf_roundtrip", "dataset": "binary_mushroom"},
            "expected_output": "num_row=1583\nnum_col=1\nrow0=0.110274\nmean=0.488999\n"
        },
        {
            "input": {"action": "protobuf_roundtrip", "dataset": "multiclass_dermatology", "pred_margin": true},
            "expected_output": "num_row=110\nnum_col=6\nrow0=-0.059313,-0.002621,-0.059962,1.872051,-0.060716,-0.061665\nmean=0.317861\n"
        }
    ]
}
```

---

### Feature 8: Compilation-Option Invariance

**As a developer**, I want optional build-time tuning knobs (threshold quantization, code folding, splitting the generated code into parallel compilation units) to change only how the predictor is built — never what it predicts — so I can optimize build size and compile time with zero risk to correctness.

**Expected Behavior / Usage:**

The compiler accepts tuning options: `quantize` (bucket continuous thresholds into integer codes), `code_folding` (collapse repeated subtrees up to a given depth ratio), and `parallel_comp` (split generated code across N translation units). Each option is purely a build-time optimization. A batch run with any single option enabled MUST produce the same prediction summary (`num_row`, `num_col`, `row0`, `mean`) as the plain compilation of the same model. The cases below all reproduce the binary classifier's margin output from Feature 4.1.

**Test Cases:** `rcb_tests/public_test_cases/feature8_compile_option_invariance.json`

```json
{
    "description": "Compilation tuning options (threshold quantization, code folding, and splitting generated code into parallel compilation units) change only how the predictor is built, never its numeric output. Predictions under each option match the plain compilation of the same model.",
    "cases": [
        {
            "input": {"action": "predict_batch", "dataset": "binary_mushroom", "pred_margin": true, "quantize": true},
            "expected_output": "num_row=1583\nnum_col=1\nrow0=-2.087944\nmean=-0.106025\n"
        },
        {
            "input": {"action": "predict_batch", "dataset": "binary_mushroom", "pred_margin": true, "code_folding": 2.0},
            "expected_output": "num_row=1583\nnum_col=1\nrow0=-2.087944\nmean=-0.106025\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-module codebase implementing model loading, an internal ensemble representation, a compiler that emits a native predictor, a runtime that scores batches and single instances, and a (de)serializer for the portable interchange buffer. The modules MUST be decoupled from stdin/stdout and JSON.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON command from stdin, invokes the appropriate core logic, and prints the `key=value` contract lines to stdout, exactly matching the per-feature contracts above. It normalizes every error into a neutral `error=<category>` line with supporting fields and never emits host-language exception identities. This adapter is logically and physically separate from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_ensemble_metadata.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_ensemble_metadata@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- format values the same way as the single_instance_predictions module uses for multiclass results
