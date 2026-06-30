## Product Requirement Document

# Tabular Random Forest Modeling Engine — Product Requirements

## Project Goal

Build a random forest modeling engine that lets a developer describe a learning problem over an in-memory table — *which column is the response and which columns are predictors* — and obtain a trained ensemble plus predictions, without manually slicing columns, one-hot encoding labels, choosing a task family by hand, or wiring up cross-validated error estimation. From a single problem specification the engine infers the task (classification, regression, probability estimation, or right-censored survival), trains an ensemble of decision trees, and exposes predictions, out-of-bag error structures, variable importance, and per-tree detail through one uniform interface.

---

## Background & Problem

Without this engine, a developer who wants to fit a forest must, by hand: pick the response column out of a table; enumerate every remaining column as a predictor; drop the columns to exclude; decide whether the problem is classification, regression, probability estimation, or survival based on the response's type; encode categorical responses as integers and decode predictions back to labels; re-implement out-of-bag error and a confusion matrix; and re-seed the random generator carefully to make experiments reproducible. This is repetitive, error-prone boilerplate, rewritten for every dataset, and easy to get subtly wrong (off-by-one predictor sets, label/integer mismatches, non-reproducible runs).

With this engine, the developer supplies one specification — either a compact formula (`response ~ .` to use all other columns, or a survival form pairing a time column with a status column) or a named response column — together with a data source. The engine resolves the predictor set, infers the task, trains the ensemble deterministically from a seed, and returns predictions and diagnostics in stable shapes. The same specification works whether the data is a column-typed table or an all-numeric matrix encoding of that table. Invalid specifications produce explicit, typed error categories instead of crashes.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a non-trivial domain (specification resolution, task inference, ensemble training, prediction in four task families, diagnostics, and input validation). The codebase MUST be organized into clear, separately-reasoned units — at minimum: specification/predictor resolution, task inference, the ensemble trainer, the prediction renderer per task family, the diagnostics (error/importance/confusion), and an input-validation layer. It MUST NOT be a single monolithic file. Do not over-engineer beyond what these responsibilities require.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases in "Core Features" are a **black-box contract for an execution adapter**, not the internal data model. The core engine must accept an in-memory data source plus a problem specification and return structured objects (a trained model, a prediction object, importance scores, an error outcome); it must know nothing about stdin/stdout or JSON. A thin adapter translates a JSON command into a core call and renders the structured result to stdout in the contract format below.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Separate specification parsing, predictor-set resolution, task inference, ensemble training, prediction rendering, diagnostics, and output formatting.
   - **Open/Closed Principle (OCP):** Adding a new task family or a new splitting rule should extend the engine, not require rewriting existing branches.
   - **Liskov Substitution Principle (LSP):** A matrix-backed data source and a column-typed table source must be interchangeable wherever a data source is expected.
   - **Interface Segregation Principle (ISP):** The data-source abstraction should expose only what the engine needs (column names, column kinds, values).
   - **Dependency Inversion Principle (DIP):** The engine depends on a data-source abstraction, not on a concrete table or matrix implementation.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public entry points (train a model; predict; query a diagnostic) should be small and idiomatic to the target language.
   - **Resilience:** Invalid specifications (bad sampling fractions, task/splitting-rule mismatches, missing values, unsupported response shapes) must be modeled as explicit, typed error outcomes — never generic crashes — and surfaced as the neutral error categories defined below.

---

## Reference Data & Output Conventions

The contract is exercised against two standard reference tables that the adapter exposes by name:

- **`iris`** — 150 rows, columns in order `Sepal.Length, Sepal.Width, Petal.Length, Petal.Width, Species`. The first four are numeric; `Species` is a categorical column with three classes `setosa, versicolor, virginica` (50 rows each).
- **`veteran`** — 137 rows, columns in order `trt, celltype, time, status, karno, diagtime, age, prior`. Here `time` is a positive survival time, `status` is the event indicator (1 = event, 0 = censored), and the rest are covariates.

A name suffixed with `_matrix` (e.g. `iris_matrix`) denotes the all-numeric matrix encoding of the same table (categorical columns mapped to integer codes), used to demonstrate data-source substitutability.

Every command is a JSON object read from stdin; the program writes a small block of `key=value` lines to stdout (the contract). Shapes are rendered as `DxE` (or `DxExF` for 3-D), counts as integers. Errors and warnings are rendered as neutral category lines (`error=<category>` / `warning=<category>`) with any parameters on their own `key=value` lines — never as host-language exception text.

---

## Core Features

### Feature 1: Problem Specification via Formula

**As a developer**, I want to state my learning problem as a compact formula over a named table, so I can train a forest without hand-listing predictor columns or choosing a task family myself.

**Expected Behavior / Usage:**

A formula has a left-hand side (the response) and a right-hand side describing predictors. The dot term on the right means "use every other column". The engine resolves the formula against the data source into a model design and reports: the inferred `task`, the `num_trees` actually grown, the `num_predictors`, and the ordered `predictors` list. The task is inferred from the response: a categorical response gives `classification` (or `probability` when probability estimation is requested); a continuous numeric response gives `regression`; a right-censored time/event response gives `survival`.

*1.1 Categorical response → classification — every other column becomes a predictor.*

A formula whose response is a categorical column yields a classification design; the predictor list is every other column in table order, and the reported tree count equals the requested count.
**Test Cases:** `rcb_tests/public_test_cases/feature1_1_formula_classification.json`

```json
{
    "description": "Resolve a formula whose response is a categorical column into a model design: the inferred learning task, the tree count actually used, and the ordered list of predictor columns (every other column).",
    "cases": [
        {
            "input": {
                "op": "fit",
                "dataset": "iris",
                "formula": "Species ~ .",
                "num_trees": 5,
                "seed": 1
            },
            "expected_output": "task=classification\nnum_trees=5\nnum_predictors=4\npredictors=Sepal.Length,Sepal.Width,Petal.Length,Petal.Width\n"
        }
    ]
}
```

---

*1.2 Continuous response → regression.*

A formula whose response is a continuous numeric column yields a regression design over the remaining columns.
**Test Cases:** `rcb_tests/public_test_cases/feature1_2_formula_regression.json`

```json
{
    "description": "Resolve a formula whose response is a continuous numeric column into a regression model design with the remaining columns as predictors.",
    "cases": [
        {
            "input": {
                "op": "fit",
                "dataset": "iris",
                "formula": "Sepal.Length ~ .",
                "num_trees": 5,
                "seed": 1
            },
            "expected_output": "task=regression\nnum_trees=5\nnum_predictors=4\npredictors=Sepal.Width,Petal.Length,Petal.Width,Species\n"
        }
    ]
}
```

---

*1.3 Time/event response → survival.*

A formula whose response pairs a time column with a status (event) column yields a survival design. Both response columns are consumed and excluded from the predictor list.
**Test Cases:** `rcb_tests/public_test_cases/feature1_3_formula_survival.json`

```json
{
    "description": "Resolve a formula whose response is a right-censored time/event pair into a survival model design; the time and status columns are consumed by the response and excluded from predictors.",
    "cases": [
        {
            "input": {
                "op": "fit",
                "dataset": "veteran",
                "formula": "Surv(time, status) ~ .",
                "num_trees": 10,
                "seed": 1
            },
            "expected_output": "task=survival\nnum_trees=10\nnum_predictors=6\npredictors=trt,celltype,karno,diagtime,age,prior\n"
        }
    ]
}
```

---

*1.4 Probability estimation request → probability task.*

When probability estimation is requested for a categorical response, the inferred task becomes probability estimation over the response classes (rather than hard classification), while the predictor resolution is unchanged.
**Test Cases:** `rcb_tests/public_test_cases/feature1_4_formula_probability.json`

```json
{
    "description": "Resolve a formula with a categorical response while requesting class-probability estimation; the task becomes probability estimation over the response classes.",
    "cases": [
        {
            "input": {
                "op": "fit",
                "dataset": "iris",
                "formula": "Species ~ .",
                "num_trees": 5,
                "seed": 1,
                "probability": true
            },
            "expected_output": "task=probability\nnum_trees=5\nnum_predictors=4\npredictors=Sepal.Length,Sepal.Width,Petal.Length,Petal.Width\n"
        }
    ]
}
```

---

*1.5 Transformed response on the left-hand side.*

The response on the left-hand side may be wrapped in a user-supplied function. The design must still resolve and infer the task from the underlying response column.
**Test Cases:** `rcb_tests/public_test_cases/feature1_5_lhs_function_response.json`

```json
{
    "description": "Accept a formula whose left-hand side wraps the response column in a user function; the design must still resolve and infer the task from the underlying response.",
    "cases": [
        {
            "input": {
                "op": "fit",
                "dataset": "iris",
                "formula": "transform(Species) ~ .",
                "num_trees": 5,
                "seed": 1
            },
            "expected_output": "task=classification\nnum_trees=5\nnum_predictors=4\npredictors=Sepal.Length,Sepal.Width,Petal.Length,Petal.Width\n"
        }
    ]
}
```

---

### Feature 2: Problem Specification via Named Response Column

**As a developer**, I want to name the response column directly instead of writing a formula, so I can build a design programmatically from column names.

**Expected Behavior / Usage:**

Instead of a formula, the developer names the response column; every other column becomes a predictor. For survival, a time column and a separate status column are named, and both are excluded from predictors. The reported design has the same shape as the formula interface (`task`, `num_trees`, `num_predictors`, `predictors`).

*2.1 Named categorical response → classification.*

Naming a categorical response column yields a classification design with all other columns as predictors in table order.
**Test Cases:** `rcb_tests/public_test_cases/feature2_1_named_response_classification.json`

```json
{
    "description": "Build a model design by naming the response column directly (instead of a formula); a categorical response yields a classification design with all other columns as predictors.",
    "cases": [
        {
            "input": {
                "op": "fit",
                "dataset": "iris",
                "dependent": "Species",
                "num_trees": 5,
                "seed": 1
            },
            "expected_output": "task=classification\nnum_trees=5\nnum_predictors=4\npredictors=Sepal.Length,Sepal.Width,Petal.Length,Petal.Width\n"
        }
    ]
}
```

---

*2.2 Named numeric response → regression.*

Naming a numeric response column yields a regression design.
**Test Cases:** `rcb_tests/public_test_cases/feature2_2_named_response_regression.json`

```json
{
    "description": "Name a numeric response column directly to obtain a regression design.",
    "cases": [
        {
            "input": {
                "op": "fit",
                "dataset": "iris",
                "dependent": "Sepal.Length",
                "num_trees": 5,
                "seed": 1
            },
            "expected_output": "task=regression\nnum_trees=5\nnum_predictors=4\npredictors=Sepal.Width,Petal.Length,Petal.Width,Species\n"
        }
    ]
}
```

---

*2.3 Named time + status columns → survival.*

Naming a time column and a separate status column yields a survival design; both named columns are excluded from the predictor list.
**Test Cases:** `rcb_tests/public_test_cases/feature2_3_named_response_survival.json`

```json
{
    "description": "Name a time column and a separate status column to obtain a survival design; both named columns are excluded from predictors.",
    "cases": [
        {
            "input": {
                "op": "fit",
                "dataset": "veteran",
                "dependent": "time",
                "status": "status",
                "num_trees": 10,
                "seed": 1
            },
            "expected_output": "task=survival\nnum_trees=10\nnum_predictors=6\npredictors=trt,celltype,karno,diagtime,age,prior\n"
        }
    ]
}
```

---

### Feature 3: Data-Source Substitutability (Typed Table vs. Numeric Matrix)

**As a developer**, I want the same specification to work on either a column-typed table or its all-numeric matrix encoding, so I can feed data from either representation and get equivalent models.

**Expected Behavior / Usage:**

A column-typed table and the all-numeric matrix encoding of the same data (categorical columns mapped to integer codes) must be interchangeable. Trained with the same seed and settings, the two representations must produce the same externally-observable outputs. Predictor resolution on a matrix source selects every non-response column in order, just like a typed table.

*3.1 Classification equivalence across representations.*

Training the same classification problem from the same seed on a typed table and on the matrix encoding (declared as a classification task) yields identical label assignments; the count of disagreeing observations is zero.
**Test Cases:** `rcb_tests/public_test_cases/feature3_1_matrix_classification_equivalence.json`

```json
{
    "description": "Train two models with the same seed: one on a column-typed table, one on the all-numeric matrix encoding of the same data (declared as a classification task). The externally-observable label assignments must agree on every observation.",
    "cases": [
        {
            "input": {
                "op": "equivalence",
                "dataset": "iris",
                "dataset_matrix": "iris_matrix",
                "formula": "Species ~ .",
                "num_trees": 5,
                "seed": 10,
                "classification_matrix": true,
                "compare": "predictions"
            },
            "expected_output": "task=classification\nobservations=150\ndisagreements=0\n"
        }
    ]
}
```

---

*3.2 Survival equivalence across representations.*

Training the same survival problem from the same seed on a typed table and on the matrix encoding yields identical cumulative-hazard estimates; the number of disagreeing cells is zero.
**Test Cases:** `rcb_tests/public_test_cases/feature3_2_matrix_survival_equivalence.json`

```json
{
    "description": "Train a survival model with the same seed on a typed table and on its all-numeric matrix encoding; the cumulative-hazard estimates must agree cell-for-cell.",
    "cases": [
        {
            "input": {
                "op": "equivalence",
                "dataset": "veteran",
                "dataset_matrix": "veteran_matrix",
                "formula": "Surv(time, status) ~ .",
                "num_trees": 5,
                "seed": 10,
                "compare": "chf"
            },
            "expected_output": "task=survival\ncells=13837\ndisagreements=0\n"
        }
    ]
}
```

---

*3.3 Predictor resolution on a matrix source.*

When the data source is an all-numeric matrix and the response is named, the predictor set is every other matrix column in order — for both numeric and (integer-coded) categorical responses.
**Test Cases:** `rcb_tests/public_test_cases/feature3_3_matrix_predictor_selection.json`

```json
{
    "description": "When the data source is an all-numeric matrix and the response is named, the predictor set is every other column of the matrix, preserving order.",
    "cases": [
        {
            "input": {
                "op": "fit",
                "dataset": "iris_matrix",
                "dependent": "Sepal.Length",
                "num_trees": 5,
                "seed": 1
            },
            "expected_output": "task=regression\nnum_trees=5\nnum_predictors=4\npredictors=Sepal.Width,Petal.Length,Petal.Width,Species\n"
        }
    ]
}
```

---

### Feature 4: Deterministic, Reproducible Training

**As a developer**, I want training to be fully determined by a seed, so repeated runs and shared experiments are reproducible.

**Expected Behavior / Usage:**

Two trainings with the same seed and identical settings must produce identical predictions for the same inputs. The contract reports the prediction count and the number of observations on which the two runs disagree, which must be zero.

*Reproducibility from a fixed seed.*

Training twice from the same seed and predicting on the same data yields zero disagreements between the two runs.
**Test Cases:** `rcb_tests/public_test_cases/feature4_reproducibility.json`

```json
{
    "description": "Training twice from the same seed with identical settings produces identical predictions; the number of disagreeing observations between the two runs must be zero.",
    "cases": [
        {
            "input": {
                "op": "determinism",
                "dataset": "iris",
                "formula": "Species ~ .",
                "num_trees": 50,
                "seed": 2
            },
            "expected_output": "task=classification\npredictions=150\ndisagreements=0\n"
        }
    ]
}
```

---

### Feature 5: Prediction Output Shapes

**As a developer**, I want predictions delivered in well-defined shapes per task family — both the aggregated forest prediction and the per-tree detail — so I can post-process them reliably.

**Expected Behavior / Usage:**

Beyond the aggregated forest prediction, the engine can return per-tree predictions ("predict-all") and terminal-node identifiers. The shapes depend on the task family: classification/regression per-tree predictions are an observations-by-trees matrix; probability per-tree predictions are observations-by-classes-by-trees; survival per-tree output yields survival and cumulative-hazard arrays of observations-by-event-times-by-trees. Per-tree prediction can be restricted to the first K trees, in which case the tree dimension equals K. Terminal-node output is an observations-by-trees matrix of node indices.

*5.1 Per-tree classification predictions.*

Per-tree prediction for a classification design returns an observations-by-trees matrix.
**Test Cases:** `rcb_tests/public_test_cases/feature5_1_predict_all_classification.json`

```json
{
    "description": "Per-tree prediction for a classification design returns one column per tree: an observations-by-trees matrix.",
    "cases": [
        {
            "input": {
                "op": "predict",
                "dataset": "iris",
                "formula": "Species ~ .",
                "num_trees": 5,
                "seed": 1,
                "predict": "all"
            },
            "expected_output": "task=classification\npredictions_shape=150x5\n"
        }
    ]
}
```

---

*5.2 Per-tree regression predictions.*

Per-tree prediction for a regression design returns an observations-by-trees matrix.
**Test Cases:** `rcb_tests/public_test_cases/feature5_2_predict_all_regression.json`

```json
{
    "description": "Per-tree prediction for a regression design returns an observations-by-trees matrix.",
    "cases": [
        {
            "input": {
                "op": "predict",
                "dataset": "iris",
                "formula": "Sepal.Length ~ .",
                "num_trees": 5,
                "seed": 1,
                "predict": "all"
            },
            "expected_output": "task=regression\npredictions_shape=150x5\n"
        }
    ]
}
```

---

*5.3 Per-tree probability predictions.*

Per-tree prediction for a probability design returns a three-dimensional observations-by-classes-by-trees array.
**Test Cases:** `rcb_tests/public_test_cases/feature5_3_predict_all_probability.json`

```json
{
    "description": "Per-tree prediction for a probability design returns a three-dimensional array of observations by classes by trees.",
    "cases": [
        {
            "input": {
                "op": "predict",
                "dataset": "iris",
                "formula": "Species ~ .",
                "num_trees": 5,
                "seed": 1,
                "probability": true,
                "predict": "all"
            },
            "expected_output": "task=probability\npredictions_shape=150x3x5\n"
        }
    ]
}
```

---

*5.4 Per-tree survival predictions.*

Per-tree prediction for a survival design returns survival and cumulative-hazard arrays, each observations-by-event-times-by-trees.
**Test Cases:** `rcb_tests/public_test_cases/feature5_4_predict_all_survival.json`

```json
{
    "description": "Per-tree prediction for a survival design returns survival and cumulative-hazard arrays, each observations by event-times by trees.",
    "cases": [
        {
            "input": {
                "op": "predict",
                "dataset": "veteran",
                "formula": "Surv(time, status) ~ .",
                "num_trees": 5,
                "seed": 1,
                "predict": "all"
            },
            "expected_output": "task=survival\nsurvival_shape=137x101x5\nchf_shape=137x101x5\n"
        }
    ]
}
```

---

*5.5 Restricting per-tree prediction to the first K trees.*

Per-tree prediction restricted to the first K trees returns a matrix whose tree dimension equals K.
**Test Cases:** `rcb_tests/public_test_cases/feature5_5_predict_subset_trees.json`

```json
{
    "description": "Per-tree prediction restricted to the first K trees returns a matrix whose tree dimension equals K.",
    "cases": [
        {
            "input": {
                "op": "predict",
                "dataset": "iris",
                "formula": "Species ~ .",
                "num_trees": 5,
                "seed": 1,
                "predict": "all",
                "num_trees_predict": 3
            },
            "expected_output": "task=classification\npredictions_shape=150x3\n"
        }
    ]
}
```

---

*5.6 Terminal-node identifiers.*

Requesting terminal-node identifiers returns an observations-by-trees matrix of node indices.
**Test Cases:** `rcb_tests/public_test_cases/feature5_6_terminal_nodes.json`

```json
{
    "description": "Requesting terminal-node identifiers returns an observations-by-trees matrix of node indices.",
    "cases": [
        {
            "input": {
                "op": "predict",
                "dataset": "iris",
                "formula": "Species ~ .",
                "num_trees": 5,
                "seed": 1,
                "predict": "terminalNodes"
            },
            "expected_output": "task=classification\npredictions_shape=150x5\n"
        }
    ]
}
```

---

### Feature 6: Out-of-Bag Confusion Matrix (Classification)

**As a developer**, I want a confusion matrix from out-of-bag predictions, so I can read per-class performance without a separate holdout.

**Expected Behavior / Usage:**

A classification design exposes a square confusion matrix. Its rows are the true classes and its columns the predicted classes (same class ordering on both axes). Each row total equals the number of training observations of that true class.

*Square confusion matrix with true-class row totals.*

A classification design yields a square confusion matrix whose row and column labels are the response classes and whose row totals equal the per-class training counts.
**Test Cases:** `rcb_tests/public_test_cases/feature6_confusion_matrix.json`

```json
{
    "description": "A classification design exposes a square confusion matrix whose rows are the true classes and whose columns are the predicted classes; each row total equals the number of training observations of that true class.",
    "cases": [
        {
            "input": {
                "op": "confusion",
                "dataset": "iris",
                "formula": "Species ~ .",
                "num_trees": 500,
                "seed": 1
            },
            "expected_output": "dims=3x3\ntrue_classes=setosa,versicolor,virginica\npredicted_classes=setosa,versicolor,virginica\nrow_totals=50,50,50\n"
        }
    ]
}
```

---

### Feature 7: Calibrated Class Probabilities

**As a developer**, I want class-probability predictions that form a valid distribution per observation, so I can use them as probabilities directly.

**Expected Behavior / Usage:**

A probability design predicts an observations-by-classes matrix. Every row sums to one and every entry lies in the unit interval. The contract reports the matrix dimensions and the counts of rows that fail to sum to one and entries that fall outside the unit interval (both must be zero).

*Per-row probability distributions sum to one within the unit interval.*

Probability predictions form an observations-by-classes matrix with every row summing to one and all entries within the unit interval.
**Test Cases:** `rcb_tests/public_test_cases/feature7_probability_outputs.json`

```json
{
    "description": "Class-probability predictions form an observations-by-classes matrix whose every row sums to one with all entries in the unit interval.",
    "cases": [
        {
            "input": {
                "op": "probabilities",
                "dataset": "iris",
                "formula": "Species ~ .",
                "num_trees": 5,
                "seed": 1,
                "probability": true
            },
            "expected_output": "classes=3\nrows=150\nrows_not_summing_to_one=0\nvalues_out_of_unit_range=0\n"
        }
    ]
}
```

---

### Feature 8: Survival Evaluation Timepoints

**As a developer**, I want to know the timepoints at which survival curves are evaluated, so I can align predicted curves to observed event times.

**Expected Behavior / Usage:**

A survival design reports its evaluation timepoints. These equal the sorted distinct event times observed in the training data. The contract reports the timepoint count and whether they equal the sorted distinct event times.

*Timepoints equal sorted distinct training event times.*

A survival design's evaluation timepoints equal the sorted distinct event times observed in training.
**Test Cases:** `rcb_tests/public_test_cases/feature8_survival_timepoints.json`

```json
{
    "description": "A survival design reports its evaluation timepoints; these equal the sorted distinct event times observed in training.",
    "cases": [
        {
            "input": {
                "op": "death_times",
                "dataset": "veteran",
                "formula": "Surv(time, status) ~ .",
                "num_trees": 5,
                "seed": 1,
                "time_col": "time"
            },
            "expected_output": "count=101\nequals_sorted_unique_event_times=yes\n"
        }
    ]
}
```

---

### Feature 9: Variable Importance

**As a developer**, I want a numeric importance score per predictor, so I can rank features.

**Expected Behavior / Usage:**

When importance scoring is enabled at training time, the model exposes one numeric importance value per predictor, keyed by predictor name. The contract reports the value kind, the count (which equals the number of predictors), and the predictor names in order.

*One numeric importance value per predictor.*

With importance scoring enabled, the model exposes one numeric importance value per predictor, named and ordered like the predictor set; the count matches the number of predictors.
**Test Cases:** `rcb_tests/public_test_cases/feature9_variable_importance.json`

```json
{
    "description": "When importance scoring is enabled, the design exposes one numeric importance value per predictor, keyed by predictor name.",
    "cases": [
        {
            "input": {
                "op": "importance",
                "dataset": "iris",
                "formula": "Species ~ .",
                "num_trees": 5,
                "seed": 1,
                "importance": "impurity"
            },
            "expected_output": "kind=numeric\ncount=4\nnames=Sepal.Length,Sepal.Width,Petal.Length,Petal.Width\n"
        }
    ]
}
```

---

### Feature 10: Input Validation as Neutral Error Categories

**As a developer**, I want invalid specifications rejected with explicit, typed categories, so my calling code can branch on them without parsing free text.

**Expected Behavior / Usage:**

Invalid inputs produce a neutral `error=<category>` line, with any parameters (class names, column lists, counts, the offending splitting rule) on their own `key=value` lines. No host-language exception text appears. The categories below cover sampling-fraction validation, task/splitting-rule mismatches, missing-data detection in training and prediction, unsupported prediction types and response shapes, diagnostics requested but unavailable, and a failing predictor-count selection function.

*10.1 Scalar sampling fraction out of range.*

A scalar sampling fraction outside the half-open interval (0,1] is rejected as out-of-range.
**Test Cases:** `rcb_tests/public_test_cases/feature10_1_sample_fraction_scalar_range.json`

```json
{
    "description": "A scalar sampling fraction outside the half-open interval (0,1] is rejected with an out-of-range error category.",
    "cases": [
        {
            "input": {
                "op": "error",
                "dataset": "iris",
                "formula": "Species ~ .",
                "num_trees": 5,
                "sample_fraction": 0
            },
            "expected_output": "error=sample_fraction_out_of_range\n"
        }
    ]
}
```

---

*10.2 Per-class sampling vector only valid for classification.*

Supplying a per-class vector of sampling fractions for a non-classification (e.g. regression) response is rejected.
**Test Cases:** `rcb_tests/public_test_cases/feature10_2_sample_fraction_vector_task.json`

```json
{
    "description": "A per-class vector of sampling fractions is only valid for classification; supplying one for a regression response is rejected.",
    "cases": [
        {
            "input": {
                "op": "error",
                "dataset": "iris",
                "formula": "Sepal.Length ~ .",
                "num_trees": 5,
                "sample_fraction": [
                    0.1,
                    0.2
                ]
            },
            "expected_output": "error=sample_fraction_vector_requires_classification\n"
        }
    ]
}
```

---

*10.3 Per-class sampling vector wrong length.*

A per-class sampling vector must supply exactly one value per response class; a wrong-length vector is rejected, reporting the expected and provided counts.
**Test Cases:** `rcb_tests/public_test_cases/feature10_3_sample_fraction_vector_size.json`

```json
{
    "description": "A per-class vector of sampling fractions must provide exactly one value per response class; a wrong-length vector is rejected with the expected and provided counts.",
    "cases": [
        {
            "input": {
                "op": "error",
                "dataset": "iris",
                "formula": "Species ~ .",
                "num_trees": 5,
                "sample_fraction": [
                    0.1,
                    0.2
                ]
            },
            "expected_output": "error=sample_fraction_size_mismatch\nexpected=3\nprovided=2\n"
        }
    ]
}
```

---

*10.4 Per-class sampling vector sums to zero.*

A per-class sampling vector whose values sum to zero is rejected.
**Test Cases:** `rcb_tests/public_test_cases/feature10_4_sample_fraction_vector_sum.json`

```json
{
    "description": "A per-class vector of sampling fractions whose values sum to zero is rejected.",
    "cases": [
        {
            "input": {
                "op": "error",
                "dataset": "iris",
                "formula": "Species ~ .",
                "num_trees": 5,
                "sample_fraction": [
                    0,
                    0,
                    0
                ]
            },
            "expected_output": "error=sample_fraction_sum_zero\n"
        }
    ]
}
```

---

*10.5 Insufficient samples when sampling without replacement.*

Sampling without replacement that requests more observations of a class than exist is rejected, reporting the class, the available count, and the requested count.
**Test Cases:** `rcb_tests/public_test_cases/feature10_5_insufficient_samples.json`

```json
{
    "description": "Sampling without replacement that requests more observations of a class than exist is rejected, reporting the class, the available count, and the requested count.",
    "cases": [
        {
            "input": {
                "op": "error",
                "dataset": "iris",
                "formula": "Species ~ .",
                "num_trees": 5,
                "sample_fraction": [
                    0.2,
                    0.3,
                    0.4
                ],
                "replace": false,
                "keep_inbag": true
            },
            "expected_output": "error=insufficient_samples_in_class\nclass=virginica\navailable=50\nrequested=60\n"
        }
    ]
}
```

---

*10.6 Splitting-rule / task-family mismatch.*

A splitting rule specific to one task family is rejected on data of another family; the contract names the offending rule and the required family.
**Test Cases:** `rcb_tests/public_test_cases/feature10_6_splitrule_task_mismatch.json`

```json
{
    "description": "A splitting rule that is specific to one task family is rejected when used on data of a different family (e.g. a regression-only rule on categorical data, or survival-only rules on categorical data).",
    "cases": [
        {
            "input": {
                "op": "error",
                "dataset": "iris",
                "formula": "Species ~ .",
                "num_trees": 5,
                "splitrule": "variance"
            },
            "expected_output": "error=splitrule_requires_regression\nsplitrule=variance\n"
        }
    ]
}
```

---

*10.7 Missing data detected during training.*

A missing value in a training predictor column is rejected, naming the column(s); a missing value in the response is rejected as a distinct response category.
**Test Cases:** `rcb_tests/public_test_cases/feature10_7_missing_data_training.json`

```json
{
    "description": "Missing values in a predictor column used for training are rejected, naming the offending column(s); a missing value in the response is rejected with a distinct response category.",
    "cases": [
        {
            "input": {
                "op": "error",
                "dataset": "iris",
                "formula": "Species ~ .",
                "num_trees": 5,
                "na_cell": [
                    [
                        25,
                        "Sepal.Length"
                    ]
                ]
            },
            "expected_output": "error=[a distinct missing data error category covering response validation]\ncolumns=Sepal.Length\n"
        }
    ]
}
```

---

*10.8 Missing data detected during prediction.*

Missing values in predictor columns of the data supplied at prediction time are rejected, naming the offending columns in column order.
**Test Cases:** `rcb_tests/public_test_cases/feature10_8_missing_data_prediction.json`

```json
{
    "description": "Missing values in predictor columns of the data passed at prediction time are rejected, naming the offending columns in column order.",
    "cases": [
        {
            "input": {
                "op": "error",
                "dataset": "iris",
                "formula": "Species ~ .",
                "predict_after": true,
                "num_trees": 5,
                "na_cell_predict": [
                    [
                        25,
                        "Sepal.Length"
                    ],
                    [
                        4,
                        "Petal.Width"
                    ]
                ]
            },
            "expected_output": "error=[a distinct missing data error category covering response validation]\ncolumns=Sepal.Length, Petal.Width\n"
        }
    ]
}
```

---

*10.9 Unknown prediction output type.*

Requesting an unsupported prediction output type is rejected.
**Test Cases:** `rcb_tests/public_test_cases/feature10_9_invalid_prediction_type.json`

```json
{
    "description": "Requesting an unknown prediction output type is rejected.",
    "cases": [
        {
            "input": {
                "op": "error",
                "dataset": "iris",
                "formula": "Species ~ .",
                "predict_after": true,
                "num_trees": 5,
                "predict_type": "class"
            },
            "expected_output": "error=invalid_prediction_type\n"
        }
    ]
}
```

---

*10.10 Survival specification with no covariates.*

A survival specification that leaves no predictor columns after consuming the time and status columns is rejected.
**Test Cases:** `rcb_tests/public_test_cases/feature10_10_survival_no_covariates.json`

```json
{
    "description": "A survival formula that leaves no predictor columns after consuming the time and status columns is rejected.",
    "cases": [
        {
            "input": {
                "op": "error",
                "dataset": "veteran",
                "formula": "Surv(time, status) ~ .",
                "num_trees": 5,
                "keep_columns": [
                    "time",
                    "status"
                ]
            },
            "expected_output": "error=no_covariates\n"
        }
    ]
}
```

---

*10.11 Importance queried but not computed.*

Querying variable importance on a model trained without importance scoring is rejected.
**Test Cases:** `rcb_tests/public_test_cases/feature10_11_importance_not_requested.json`

```json
{
    "description": "Querying variable importance on a model trained without importance scoring is rejected.",
    "cases": [
        {
            "input": {
                "op": "error",
                "dataset": "iris",
                "formula": "Species ~ .",
                "num_trees": 5,
                "importance_query": true
            },
            "expected_output": "error=importance_not_available\n"
        }
    ]
}
```

---

*10.12 Timepoints queried on a non-survival model.*

Querying survival timepoints on a non-survival model is rejected.
**Test Cases:** `rcb_tests/public_test_cases/feature10_12_timepoints_non_survival.json`

```json
{
    "description": "Querying survival timepoints on a non-survival model is rejected.",
    "cases": [
        {
            "input": {
                "op": "error",
                "dataset": "iris",
                "formula": "Species ~ .",
                "num_trees": 5,
                "timepoints_on": true
            },
            "expected_output": "error=not_a_survival_forest\n"
        }
    ]
}
```

---

*10.13 Predictor-count selection function fails.*

When the function used to choose the number of candidate predictors per split raises during evaluation, training is aborted with a predictor-count-function error category.
**Test Cases:** `rcb_tests/public_test_cases/feature10_13_mtry_function_error.json`

```json
{
    "description": "When the predictor-count selection function raises during evaluation, training is aborted with an mtry-function error category.",
    "cases": [
        {
            "input": {
                "op": "error",
                "dataset": "veteran",
                "formula": "Surv(time, status) ~ .",
                "num_trees": 5,
                "mtry_error": true
            },
            "expected_output": "error=mtry_function_error\n"
        }
    ]
}
```

---

### Feature 11: Dropped-Unused-Level Warning

**As a developer**, I want a warning when my training subset omits some response classes, so I'm aware the model only saw a subset — while predictions still span the full class set.

**Expected Behavior / Usage:**

Training on a subset that omits some response classes emits a neutral warning naming the dropped response levels. Predictions still report the full set of original classes (for classification) or the count of surviving classes (for probability estimation). The contract renders `warning=dropped_unused_response_levels` with a `levels=` field plus the prediction-level information.

*Warn on dropped response levels; predictions retain full class span.*

Training on a subset missing some response classes warns and names the dropped levels; classification predictions still span all original classes and probability predictions report the surviving class count.
**Test Cases:** `rcb_tests/public_test_cases/feature11_dropped_unused_levels.json`

```json
{
    "description": "Training on a subset that omits some response classes warns that unused response levels were dropped, naming them; predictions still span the full set of original classes (or, for probability, the surviving class count).",
    "cases": [
        {
            "input": {
                "op": "warning",
                "dataset": "iris",
                "formula": "Species ~ .",
                "num_trees": 5,
                "row_range": [
                    1,
                    100
                ],
                "report_pred_levels": true
            },
            "expected_output": "warning=dropped_unused_response_levels\nlevels=virginica\nprediction_levels=setosa,versicolor,virginica\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above — specification/predictor resolution, task inference, ensemble training, the four prediction families, diagnostics, and input validation — organized into separate logical units (not a single god-file), with the public model/predict/diagnostic interface decoupled from any I/O or JSON concern.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON command from stdin, invokes the appropriate core logic, and prints the `key=value` contract block to stdout, matching the per-leaf-feature contracts above. It is solely responsible for JSON parsing and for normalizing any native error into the neutral `error=`/`warning=` categories; it adds no domain logic.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_1_formula_classification.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_formula_classification@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout from the program under test, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- respect the standard epsilon bound defined in the core validation module
- fail if the scalar falls into the forbidden zero region
