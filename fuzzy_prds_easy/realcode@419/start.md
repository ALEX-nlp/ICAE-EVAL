## Product Requirement Document

# Machine Learning Numerical Toolkit - Metrics, Models & Retrieval Primitives

## Project Goal

Build a machine learning numerical toolkit that gives developers a single, dependable library of the low-level building blocks behind supervised learning: evaluation metrics, probability link functions, distance-weighting kernels, optimizer cost/gradient computations, learning-rate schedules, cross-validation index planners, empirical distributions, decision-tree impurity measures, nearest-neighbour search, and tabular data shaping helpers. It lets developers assemble and evaluate models without re-deriving and re-testing this numerically delicate plumbing for every project.

---

## Background & Problem

Without this toolkit, developers building classifiers, regressors, decision trees and nearest-neighbour models are forced to hand-roll each numerical primitive: averaging per-class precision/recall, clipping probabilities so a log-loss stays finite, keeping a softmax from overflowing, enumerating leave-p-out subsets, weighting tree impurities by node size, and so on. This leads to repetitive, error-prone boilerplate where a single off-by-one in a fold split or a missing probability clip silently corrupts every downstream model, and where the same edge cases (empty matrices, out-of-range column indices, degenerate probabilities) are mishandled differently in each codebase.

With this toolkit, each primitive is exposed as a small, well-specified operation with a precise input shape, a precise output shape, and a defined behaviour for every boundary and error condition. Developers compose these vetted pieces instead of reinventing them, and they get consistent, language-neutral handling of malformed input across the whole surface.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility numerical library (metrics, link functions, kernels, optimization helpers, schedules, cross-validation, tree impurity, retrieval, data shaping). It MUST NOT be a single "god file". Output a clear, multi-file directory tree that groups each family of primitives into its own cohesive module, with a separate execution adapter. Do not over-engineer individual leaf functions, but strictly avoid a monolith.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core numerical logic must remain completely decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating each JSON command into idiomatic calls into the core library and rendering the result as the line-oriented text contract specified per feature.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Separate JSON parsing, command routing, core numerical computation, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** Adding a new metric, kernel, or schedule must be possible by extension, without modifying existing primitives.
   - **Liskov Substitution Principle (LSP):** All kernels (and likewise all schedules, all impurity measures) must be interchangeable behind a common abstraction.
   - **Interface Segregation Principle (ISP):** Keep each primitive's interface small and focused (a metric exposes a scoring call; a kernel exposes a weight-by-distance call).
   - **Dependency Inversion Principle (DIP):** High-level routing depends on primitive abstractions, not on concrete I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core library must be elegant and idiomatic to the target language.
   - **Resilience:** Edge cases (empty matrices, wrong column counts, out-of-range indices, degenerate probabilities, invalid fold/neighbour counts) must be modelled as well-defined error conditions, not generic faults. The adapter renders these as the neutral error categories specified below.

---

## Core Features

All numeric output is rendered in a stable, platform-independent textual form: integers print without a decimal point, fractional values print with trailing zeros trimmed, and each logical record ends with a newline. Matrices print one row per line with comma-separated cells. Errors are rendered as a single neutral `error=<category>` line and never expose host-language exception types or runtime traces.

---

### Feature 1: Classification Quality Metrics

**As a developer**, I want to score multiclass and binary classifier output against ground truth, so I can compare models on a consistent, well-defined scale.

**Expected Behavior / Usage:**

*1.1 Precision (macro-averaged) — mean per-class precision over one-hot label matrices*

The input is two equally shaped matrices of one-hot encoded labels (`predicted` and `actual`); each row is one observation with at most one positive column, and each column is a class. The output is a single line `score=<value>` where the value is the mean over classes of (true positives / predicted positives). A class for which nothing was predicted positive contributes 0 to the average. The score lies in [0, 1].

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_precision.json`

```json
{
    "description": "Per-class precision averaged over all classes for one-hot encoded multiclass label matrices. Each row is one observation with exactly one (or zero) positive class column. The score is the mean over classes of (true positives / predicted positives), treating a class with no predicted positives as contributing 0.",
    "cases": [
        {"input": {"op": "classification_precision", "predicted": [[0, 1, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 1, 0], [1, 0, 0], [0, 0, 1]], "actual": [[1, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 1, 0], [1, 0, 0], [0, 0, 1]]}, "expected_output": "score=0.888889\n"},
        {"input": {"op": "classification_precision", "predicted": [[0, 1, 0], [1, 0, 0], [0, 1, 0], [0, 1, 0], [0, 1, 0], [1, 0, 0], [1, 0, 0]], "actual": [[1, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 1, 0], [1, 0, 0], [0, 0, 1]]}, "expected_output": "score=0.388889\n"},
        {"input": {"op": "classification_precision", "predicted": [[0, 1, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 1, 0], [1, 0, 0], [0, 0, 1]], "actual": [[1, 0, 0], [1, 0, 0], [0, 1, 0], [1, 0, 0], [0, 1, 0], [1, 0, 0], [1, 0, 0]]}, "expected_output": "score=0.555556\n"}
    ]
}
```

*1.2 Recall (macro-averaged) — mean per-class recall over one-hot label matrices*

The input is two equally shaped one-hot label matrices. The output is `score=<value>` where the value is the mean over classes of (true positives / actual positives). A perfect prediction yields `score=1`. The score lies in [0, 1].

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_recall.json`

```json
{
    "description": "Per-class recall averaged over all classes for one-hot encoded multiclass label matrices. The score is the mean over classes of (true positives / actual positives); a perfect prediction yields 1.",
    "cases": [
        {"input": {"op": "classification_recall", "predicted": [[0, 1, 0], [0, 0, 0], [0, 1, 0], [0, 0, 1], [0, 1, 0], [1, 0, 0], [0, 0, 1]], "actual": [[1, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 1, 0], [1, 0, 0], [0, 0, 1]]}, "expected_output": "score=0.777778\n"},
        {"input": {"op": "classification_recall", "predicted": [[0, 1, 0], [1, 0, 0], [0, 1, 0], [0, 1, 0], [0, 1, 0], [1, 0, 0], [1, 0, 0]], "actual": [[1, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 1, 0], [1, 0, 0], [0, 0, 1]]}, "expected_output": "score=0.555556\n"},
        {"input": {"op": "classification_recall", "predicted": [[0, 1, 0], [0, 0, 0], [0, 1, 0], [0, 0, 1], [0, 1, 0], [1, 0, 0], [0, 0, 1]], "actual": [[1, 0, 0], [1, 0, 0], [0, 1, 0], [1, 0, 0], [0, 1, 0], [1, 0, 0], [1, 0, 0]]}, "expected_output": "score=0.4\n"}
    ]
}
```

*1.3 Binary log-loss — mean logarithmic loss with probability clipping*

The input is a single-column matrix of predicted probabilities (`predicted`) and a single-column matrix of binary truths (`actual`). The output is `score=<value>`, the mean binary cross-entropy. Probabilities are clipped away from exactly 0 and 1 so the loss stays finite even for degenerate predictions; a perfect prediction gives a score near 0, while a confidently wrong prediction gives a large but finite score.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_log_loss.json`

```json
{
    "description": "Mean binary logarithmic loss between predicted probabilities and binary truth columns. Probabilities are clipped away from 0 and 1 so the loss stays finite even for degenerate predictions. Perfect predictions give a loss near 0.",
    "cases": [
        {"input": {"op": "log_loss", "predicted": [[1], [0], [1], [0]], "actual": [[1], [0], [1], [0]]}, "expected_output": "score=0\n"},
        {"input": {"op": "log_loss", "predicted": [[0.9], [0.1]], "actual": [[1], [0]]}, "expected_output": "score=0.105361\n"},
        {"input": {"op": "log_loss", "predicted": [[0.0], [1.0]], "actual": [[1], [0]]}, "expected_output": "score=34.539176\n"}
    ]
}
```

---

### Feature 2: Regression Quality Metrics

**As a developer**, I want to score continuous predictions against continuous truths, so I can evaluate regressors with standard error measures and get consistent rejection of malformed input.

**Expected Behavior / Usage:**

*2.1 Mean absolute percentage error — column-vector inputs only*

The input is a single-column prediction matrix and a single-column truth matrix. The output is `score=<value>`, the mean of |truth − prediction| / |truth| over rows. Any input that is empty or has more than one column is rejected with `[a standard summation metric based on squared residuals]`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_mape.json`

```json
{
    "description": "Mean absolute percentage error between a single-column matrix of predictions and a single-column matrix of truths. Both inputs must be column vectors; any input that is empty or has more than one column is rejected with a neutral invalid-columns error.",
    "cases": [
        {"input": {"op": "mape", "predicted": [[12], [18], [12], [90], [78]], "actual": [[10], [20], [30], [60], [70]]}, "expected_output": "score=0.062857\n"},
        {"input": {"op": "mape", "predicted": [], "actual": [[10], [20], [30], [60], [70]]}, "expected_output": "[a standard summation metric based on squared residuals]\n"},
        {"input": {"op": "mape", "predicted": [[1, 2]], "actual": [[10], [20], [30], [60], [70]]}, "expected_output": "[a standard summation metric based on squared residuals]\n"}
    ]
}
```

*2.2 Residual sum of squares — column-vector inputs only*

The input is a single-column prediction matrix and a single-column truth matrix. The output is `score=<value>`, the sum over rows of (prediction − truth)². Empty or multi-column inputs are rejected with `[a standard summation metric based on squared residuals]`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_rss.json`

```json
{
    "description": "Residual sum of squares between a single-column matrix of predictions and a single-column matrix of truths. Both inputs must be column vectors; empty or multi-column inputs are rejected with a neutral invalid-columns error.",
    "cases": [
        {"input": {"op": "residual_sum_of_squares", "predicted": [[12], [18], [12], [90], [78]], "actual": [[10], [20], [30], [60], [70]]}, "expected_output": "score=1296\n"},
        {"input": {"op": "residual_sum_of_squares", "predicted": [], "actual": [[10], [20], [30], [60], [70]]}, "expected_output": "[a standard summation metric based on squared residuals]\n"},
        {"input": {"op": "residual_sum_of_squares", "predicted": [[1, 2]], "actual": [[10], [20], [30], [60], [70]]}, "expected_output": "[a standard summation metric based on squared residuals]\n"}
    ]
}
```

---

### Feature 3: Probability Link Functions

**As a developer**, I want to convert raw model scores into probabilities, so I can turn linear outputs into calibrated, numerically stable distributions.

**Expected Behavior / Usage:**

*3.1 Logistic (inverse-logit) — element-wise score-to-probability on a single column*

The input is a single-column matrix of real-valued scores. The output is one probability per line. The mapping is the logistic function: a score of 0 maps to 0.5, scores at or above +10 saturate to 1, and scores at or below −10 saturate to 0. Input with more than one column is rejected with `[a standard summation metric based on squared residuals]`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_sigmoid.json`

```json
{
    "description": "Maps a single-column matrix of real-valued scores to probabilities with the logistic (inverse-logit) function, one probability per row. Scores at or above +10 saturate to 1, scores at or below -10 saturate to 0, and a score of 0 maps to 0.5. Input with more than one column is rejected with a neutral invalid-columns error.",
    "cases": [
        {"input": {"op": "sigmoid", "scores": [[1.0], [2.0], [3.0], [4.0]]}, "expected_output": "0.731059\n0.880797\n0.952574\n0.982014\n"},
        {"input": {"op": "sigmoid", "scores": [[-1.0], [-2.0], [-3.0], [-4.0]]}, "expected_output": "0.268941\n0.119203\n0.047426\n0.017986\n"},
        {"input": {"op": "sigmoid", "scores": [[50000.0], [100000.0], [200.0], [1000.0], [10.0]]}, "expected_output": "1\n1\n1\n1\n1\n"},
        {"input": {"op": "sigmoid", "scores": [[-10.0], [-11.0], [-12.0], [-13.0]]}, "expected_output": "0\n0\n0\n0\n"}
    ]
}
```

*3.2 Softmax — row-wise normalization into a probability distribution*

The input is a score matrix. Each row is independently converted into a probability distribution that sums to 1, using a numerically stable shift by the row maximum before exponentiation. The output has the same shape as the input, one row per line.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_softmax.json`

```json
{
    "description": "Row-wise softmax of a score matrix: each row of scores is converted to a probability distribution that sums to 1, using a numerically stable shift by the row maximum. The output has the same shape as the input.",
    "cases": [
        {"input": {"op": "softmax", "scores": [[2, 1, -3], [7, 11, 0], [-7, 4, -9], [6, 1, 3], [-1, -3, -2]]}, "expected_output": "0.727475,0.267623,0.004902\n0.017986,0.981998,0.000016\n0.000017,0.999981,0.000002\n0.946499,0.006377,0.047123\n0.665241,0.090031,0.244728\n"}
    ]
}
```

---

### Feature 4: Distance-Weighting Kernels

**As a developer**, I want to convert a non-negative distance into a similarity weight, so I can build distance-weighted nearest-neighbour and kernel-smoothing models.

**Expected Behavior / Usage:**

The input names a kernel and a non-negative `distance`. The output is a single line `weight=<value>`. Four kernels are supported. Three are compactly supported on the unit bandwidth (weight is 0 once the distance exceeds 1): `uniform` returns 1/2 inside the bandwidth and 0 outside; `epanechnikov` returns 0.75·(1−d²) inside and 0 outside; `cosine` returns (π/4)·cos((π/2)·d) inside and 0 outside. The `gaussian` kernel has unbounded support and returns the standard normal density at the distance.

**Test Cases:** `rcb_tests/public_test_cases/feature4_distance_kernels.json`

```json
{
    "description": "Distance-weighting kernels used to convert a non-negative distance into a similarity weight. Supported kernels: 'uniform' (1/2 inside the unit bandwidth, else 0), 'epanechnikov' (0.75*(1-d^2) inside, else 0), 'cosine' (pi/4*cos(pi/2*d) inside, else 0) and 'gaussian' (standard normal density, unbounded support).",
    "cases": [
        {"input": {"op": "kernel_weight", "kernel": "uniform", "distance": 0}, "expected_output": "weight=0.5\n"},
        {"input": {"op": "kernel_weight", "kernel": "uniform", "distance": 0.5}, "expected_output": "weight=0.5\n"},
        {"input": {"op": "kernel_weight", "kernel": "uniform", "distance": 1}, "expected_output": "weight=0.5\n"},
        {"input": {"op": "kernel_weight", "kernel": "uniform", "distance": 1.01}, "expected_output": "weight=0\n"},
        {"input": {"op": "kernel_weight", "kernel": "uniform", "distance": 10}, "expected_output": "weight=0\n"},
        {"input": {"op": "kernel_weight", "kernel": "epanechnikov", "distance": 0}, "expected_output": "weight=0.75\n"},
        {"input": {"op": "kernel_weight", "kernel": "epanechnikov", "distance": 1}, "expected_output": "weight=0\n"},
        {"input": {"op": "kernel_weight", "kernel": "epanechnikov", "distance": 1.01}, "expected_output": "weight=0\n"}
    ]
}
```

---

### Feature 5: Least-Squares Cost & Gradient

**As a developer**, I want to compute the least-squares objective and its gradient for a linear model, so I can drive gradient-based optimizers.

**Expected Behavior / Usage:**

*5.1 Cost — residual sum of squares of a linear model*

The input is a feature matrix `x`, a coefficient column vector `w`, and a target column vector `y`. The output is `cost=<value>`, the residual sum of squares of (x·w − y).

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_least_squares_cost.json`

```json
{
    "description": "Least-squares cost of a linear model: given a feature matrix x, a coefficient column vector w and a target column vector y, returns the residual sum of squares of (x*w - y).",
    "cases": [
        {"input": {"op": "least_squares_cost", "x": [[21.5, -0.04, 27.0], [15.0, 0.0, 33.9], [-10.0, -1.0, 22.0], [-10.0, -1.0, 17.0]], "w": [[0.1], [0.2], [-0.9]], "y": [[11.0], [17.0], [-25.0], [5.0]]}, "expected_output": "cost=3694.623169\n"}
    ]
}
```

*5.2 Gradient — derivative of the least-squares cost w.r.t. coefficients*

The input is the same `x`, `w`, `y`. The output is the gradient vector, computed as −2·xᵀ·(y − x·w), printed one component per line (one entry per feature).

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_least_squares_gradient.json`

```json
{
    "description": "Gradient of the least-squares cost with respect to the coefficient vector, computed as -2 * x^T * (y - x*w). Output is one component per line (a column vector with one entry per feature).",
    "cases": [
        {"input": {"op": "least_squares_gradient", "x": [[21.5, -0.04, 27.0], [15.0, 0.0, 33.9], [-10.0, -1.0, 22.0], [-10.0, -1.0, 17.0]], "w": [[0.1], [0.2], [-0.9]], "y": [[11.0], [17.0], [-25.0], [5.0]]}, "expected_output": "-2456.09375\n37.652641\n-5465.010254\n"}
    ]
}
```

---

### Feature 6: Learning-Rate Schedules

**As a developer**, I want a family of learning-rate schedules that emit a deterministic sequence of step sizes, so I can control optimizer convergence over a fixed number of iterations.

**Expected Behavior / Usage:**

Every schedule takes a `limit` (number of values to emit) and prints one value per line; a `limit` of 0 yields empty output. Each schedule defines how the value evolves with the iteration index.

*6.1 Constant — emits the same value `limit` times*

The value never changes; the schedule emits `initialValue` exactly `limit` times.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_constant.json`

```json
{
    "description": "Constant learning-rate schedule: emits the same value 'limit' times. A limit of 0 yields an empty sequence.",
    "cases": [
        {"input": {"op": "learning_rate_constant", "initialValue": 1.3, "limit": 5}, "expected_output": "1.3\n1.3\n1.3\n1.3\n1.3\n"},
        {"input": {"op": "learning_rate_constant", "initialValue": 3.5, "limit": 1}, "expected_output": "3.5\n"},
        {"input": {"op": "learning_rate_constant", "initialValue": 1.3, "limit": 0}, "expected_output": ""}
    ]
}
```

*6.2 Exponential — geometric decay by iteration*

Starting from `initialValue`, the value shrinks geometrically with the iteration index at rate `decay`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_exponential.json`

```json
{
    "description": "Exponential learning-rate decay schedule producing 'limit' values that shrink geometrically according to initialValue and decay. A limit of 0 yields an empty sequence.",
    "cases": [
        {"input": {"op": "learning_rate_exponential", "initialValue": 1.3, "decay": 2, "limit": 4}, "expected_output": "0.175936\n0.02381\n0.003222\n0.000436\n"},
        {"input": {"op": "learning_rate_exponential", "initialValue": 1.3, "decay": 2, "limit": 2}, "expected_output": "0.175936\n0.02381\n"},
        {"input": {"op": "learning_rate_exponential", "initialValue": 1.3, "decay": 2, "limit": 0}, "expected_output": ""}
    ]
}
```

*6.3 Step-based — piecewise-constant steps controlled by a drop rate*

The value changes in discrete steps: it is recomputed from `initialValue`, `decay` and the step index, where the step index advances every `dropRate` iterations. `decay` may be fractional or negative (a negative decay produces alternating signs).

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_step_based.json`

```json
{
    "description": "Step-based learning-rate schedule: the rate changes in discrete steps controlled by decay and dropRate over 'limit' iterations. Decay may be fractional or negative.",
    "cases": [
        {"input": {"op": "learning_rate_step_based", "initialValue": 1.3, "decay": 2, "dropRate": 2, "limit": 4}, "expected_output": "2.6\n2.6\n5.2\n5.2\n"},
        {"input": {"op": "learning_rate_step_based", "initialValue": 1.3, "decay": 2, "dropRate": 1, "limit": 4}, "expected_output": "5.2\n10.4\n20.8\n41.6\n"},
        {"input": {"op": "learning_rate_step_based", "initialValue": 1.3, "decay": -2, "dropRate": 1, "limit": 4}, "expected_output": "5.2\n-10.4\n20.8\n-41.6\n"},
        {"input": {"op": "learning_rate_step_based", "initialValue": 1.3, "decay": 0.2, "dropRate": 1, "limit": 4}, "expected_output": "0.052\n0.0104\n0.00208\n0.000416\n"}
    ]
}
```

*6.4 Time-based — decay as a function of the iteration index*

Starting from `initialValue`, the value decreases as a function of the iteration index and `decay` (the rate falls more slowly than exponential decay).

**Test Cases:** `rcb_tests/public_test_cases/feature6_4_time_based.json`

```json
{
    "description": "Time-based learning-rate decay schedule producing 'limit' values that decrease as a function of the iteration index, initialValue and decay. A limit of 0 yields an empty sequence.",
    "cases": [
        {"input": {"op": "learning_rate_time_based", "initialValue": 1.3, "decay": 2, "limit": 4}, "expected_output": "0.433333\n0.086667\n0.012381\n0.001376\n"},
        {"input": {"op": "learning_rate_time_based", "initialValue": 1.3, "decay": 2, "limit": 2}, "expected_output": "0.433333\n0.086667\n"},
        {"input": {"op": "learning_rate_time_based", "initialValue": 1.3, "decay": 2, "limit": 0}, "expected_output": ""}
    ]
}
```

---

### Feature 7: Cross-Validation Index Planners

**As a developer**, I want to plan train/validation splits as groups of observation indices, so I can run k-fold and leave-p-out cross-validation deterministically.

**Expected Behavior / Usage:**

*7.1 K-fold — contiguous index partitioning*

The input is a number of `folds` and a number of `observations` n. The output partitions the indices 0..n−1 into `folds` contiguous groups, one group per line, comma-separated. When n is not divisible by `folds`, the later folds absorb the remainder. The number of folds must be at least 2 and at most n; otherwise `error=out_of_range` is returned.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_kfold.json`

```json
{
    "description": "Contiguous k-fold index partitioning: splits observation indices 0..n-1 into 'folds' contiguous groups; when n is not divisible by folds the later folds absorb the remainder. Number of folds must be at least 2 and at most n, otherwise a neutral out-of-range error is returned.",
    "cases": [
        {"input": {"op": "kfold_indices", "folds": 5, "observations": 12}, "expected_output": "0,1\n2,3\n4,5\n6,7,8\n9,10,11\n"},
        {"input": {"op": "kfold_indices", "folds": 4, "observations": 12}, "expected_output": "0,1,2\n3,4,5\n6,7,8\n9,10,11\n"},
        {"input": {"op": "kfold_indices", "folds": 3, "observations": 12}, "expected_output": "0,1,2,3\n4,5,6,7\n8,9,10,11\n"},
        {"input": {"op": "kfold_indices", "folds": 12, "observations": 12}, "expected_output": "0\n1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n"}
    ]
}
```

*7.2 Leave-p-out — enumerate every size-p subset*

The input is a subset size `p` and a number of `observations` n. The output enumerates every size-p subset of the indices 0..n−1, each subset emitted on its own line as an ascending, comma-separated group.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_leave_p_out.json`

```json
{
    "description": "Leave-p-out index combinations: enumerates every size-p subset of observation indices 0..n-1, each subset emitted as an ascending group of indices.",
    "cases": [
        {"input": {"op": "leave_p_out_indices", "p": 2, "observations": 4}, "expected_output": "0,1\n0,2\n1,2\n0,3\n1,3\n2,3\n"},
        {"input": {"op": "leave_p_out_indices", "p": 2, "observations": 5}, "expected_output": "0,1\n0,2\n1,2\n0,3\n1,3\n2,3\n0,4\n1,4\n2,4\n3,4\n"},
        {"input": {"op": "leave_p_out_indices", "p": 1, "observations": 5}, "expected_output": "0\n1\n2\n3\n4\n"}
    ]
}
```

---

### Feature 8: Empirical Value Distribution

**As a developer**, I want the empirical probability distribution of a sequence of values, so I can compute class priors and feed downstream impurity measures.

**Expected Behavior / Usage:**

The input is a sequence of values plus a `value_type` of `number`, `string`, or `vector` (fixed-length numeric tuples). The output lists each distinct value with its relative frequency, one `key=probability` line per distinct value, sorted by key (numeric keys ascending; vector keys printed as `c0|c1|...`). An optional `length` normalizes the frequencies against a larger universe instead of the sequence length. An empty sequence, or a zero `length`, is rejected with `error=invalid_argument`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_value_distribution.json`

```json
{
    "description": "Empirical probability distribution of a sequence of values: returns each distinct value with its relative frequency. An optional total length can be supplied to normalize against a larger universe. Values may be numbers, strings, or fixed-length numeric vectors. An empty sequence or a zero length is rejected with a neutral invalid-argument error.",
    "cases": [
        {"input": {"op": "value_distribution", "value_type": "number", "values": [1, 1, 1, 2, 3]}, "expected_output": "1=0.6\n2=0.2\n3=0.2\n"},
        {"input": {"op": "value_distribution", "value_type": "number", "values": [1, 1, 1, 1, 1]}, "expected_output": "1=1\n"},
        {"input": {"op": "value_distribution", "value_type": "number", "values": [10, 20, 30, 40, 60]}, "expected_output": "10=0.2\n20=0.2\n30=0.2\n40=0.2\n60=0.2\n"},
        {"input": {"op": "value_distribution", "value_type": "vector", "values": [[1, 0, 0], [0, 0, 1], [0, 0, 1], [0, 1, 0], [1, 0, 0]]}, "expected_output": "0|0|1=0.4\n0|1|0=0.2\n1|0|0=0.4\n"},
        {"input": {"op": "value_distribution", "value_type": "string", "values": ["class 1", "class 2", "class 3"], "length": 10}, "expected_output": "class 1=0.1\nclass 2=0.1\nclass 3=0.1\n"}
    ]
}
```

---

### Feature 9: Decision-Tree Impurity Measures

**As a developer**, I want to measure how mixed the class labels are within a tree node (or across a split), so I can choose the best split when growing a decision tree.

**Expected Behavior / Usage:**

Each measure takes a `targetId` naming the class-label column. A single node is given as a `node` matrix (each row is an observation, one column is the target). A split is given as `nodes`, a list of child-node matrices; the split error is the row-count weighted aggregate over children, and empty children are ignored. The output is `error_value=<value>`. A `targetId` outside the node's column range is rejected with `error=out_of_range`.

*9.1 Gini impurity — sum of p·(1−p) over class probabilities*

For a single node the error is the sum over class probabilities p of p·(1−p) within the target column. For a split it is the row-count weighted average of the per-child Gini impurities.

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_gini.json`

```json
{
    "description": "Gini-impurity error of decision-tree nodes. For a single node it returns sum over class probabilities p of p*(1-p) using the target column. For a 'stump' (a list of child nodes) it returns the row-count weighted average of per-node Gini impurities. Empty child nodes are ignored; a target column index outside the node is rejected with a neutral out-of-range error.",
    "cases": [
        {"input": {"op": "gini_impurity", "node": [[10, 30, 40, 0], [20, 30, 10, 1], [30, 20, 30, 1], [40, 10, 20, 2]], "targetId": 3}, "expected_output": "error_value=0.625\n"},
        {"input": {"op": "gini_impurity", "node": [[10, 30, 0], [14, 20, 0]], "targetId": 2}, "expected_output": "error_value=0\n"},
        {"input": {"op": "gini_impurity", "nodes": [[[10, 30, 0], [10, 30, 1], [10, 30, 1], [10, 30, 2]], [[10, 30, 2], [10, 30, 2], [10, 30, 2], [10, 30, 1]], [[10, 30, 0], [10, 30, 0], [10, 30, 1], [10, 30, 2]]], "targetId": 2}, "expected_output": "error_value=0.541667\n"}
    ]
}
```

*9.2 Majority error — fraction not in the most frequent class*

For a single node the error is the fraction of observations that do not belong to the most frequent class in the target column. For a split it is the total misclassified count divided by the total number of observations.

**Test Cases:** `rcb_tests/public_test_cases/feature9_2_majority.json`

```json
{
    "description": "Majority-class error of decision-tree nodes. For a single node it returns the fraction of observations that do not belong to the most frequent class in the target column. For a 'stump' (a list of child nodes) it returns the total misclassified count divided by the total number of observations. Empty child nodes are ignored; a target column index outside the node is rejected with a neutral out-of-range error.",
    "cases": [
        {"input": {"op": "majority_error", "node": [[10, 30, 40, 0], [20, 30, 10, 1], [30, 20, 30, 1], [40, 10, 20, 2]], "targetId": 3}, "expected_output": "error_value=0.5\n"},
        {"input": {"op": "majority_error", "node": [[10, 30, 0], [14, 20, 0]], "targetId": 2}, "expected_output": "error_value=0\n"},
        {"input": {"op": "majority_error", "nodes": [[[10, 30, 0], [10, 30, 1], [10, 30, 1], [10, 30, 2]], [[10, 30, 2], [10, 30, 2], [10, 30, 2], [10, 30, 1]], [[10, 30, 0], [10, 30, 0], [10, 30, 1], [10, 30, 2]]], "targetId": 2}, "expected_output": "error_value=0.416667\n"}
    ]
}
```

---

### Feature 10: K-Nearest-Neighbour Search (brute force)

**As a developer**, I want to find the k closest training rows to each query and read off their outcome labels, so I can build neighbour-based classifiers and regressors.

**Expected Behavior / Usage:**

The input is a training feature matrix `trainFeatures`, a column of training outcome labels `trainOutcomes` (one per training row), a neighbour count `k`, a distance metric (`euclidean`, `manhattan`, `cosine`, `hamming`), a `standardize` flag, and a query feature matrix `testFeatures`. For each query row the output is one line listing the outcome labels of its k nearest training rows, ordered nearest-first, comma-separated. When `standardize` is true, features are z-scored before distances are measured. Construction is rejected with a neutral error when matrices are empty, shapes are inconsistent, or k is outside 1..number-of-training-rows.

**Test Cases:** `rcb_tests/public_test_cases/feature10_knn_neighbours.json`

```json
{
    "description": "K nearest neighbours search: given a training feature matrix, a column of training outcome labels, a neighbour count k, a distance metric and a standardize flag, returns for each test observation the labels of its k closest training rows ordered nearest-first. Construction is rejected with a neutral error when matrices are empty, shapes are inconsistent, or k is outside 1..number-of-training-rows.",
    "cases": [
        {"input": {"op": "knn_neighbours", "trainFeatures": [[15, 15, 15, 15, 15], [14, 14, 14, 14, 14], [16, 16, 16, 16, 16], [18, 18, 18, 18, 18], [17, 17, 17, 17, 17], [13, 13, 13, 13, 13], [12, 12, 12, 12, 12], [5, 5, 5, 5, 5]], "trainOutcomes": [[100], [200], [300], [400], [500], [600], [700], [800]], "k": 3, "distance": "euclidean", "standardize": true, "testFeatures": [[10, 10, 10, 10, 10], [3, 3, 3, 3, 3]]}, "expected_output": "700,600,200\n800,700,600\n"},
        {"input": {"op": "knn_neighbours", "trainFeatures": [[15, 15, 15, 15, 15], [14, 14, 14, 14, 14], [2, 2, 2, 2, 2], [18, 18, 18, 18, 18], [1, 1, 1, 1, 1]], "trainOutcomes": [[100], [200], [300], [400], [500]], "k": 5, "distance": "euclidean", "standardize": true, "testFeatures": [[10, 10, 10, 10, 10], [3, 3, 3, 3, 3]]}, "expected_output": "200,100,300,400,500\n300,500,200,100,400\n"}
    ]
}
```

---

### Feature 11: Tabular Data Shaping Helpers

**As a developer**, I want to reshape feature matrices and tabular datasets before fitting, so I can add an intercept term and separate features from targets cleanly.

**Expected Behavior / Usage:**

*11.1 Intercept column — optionally prepend a constant first column*

The input is a `matrix`, a boolean `fitIntercept` flag, and a `scale` value. When the flag is false the matrix is returned unchanged. When the flag is true a new first column filled with `scale` is inserted before the existing columns. Output is one matrix row per line.

**Test Cases:** `rcb_tests/public_test_cases/feature11_1_intercept.json`

```json
{
    "description": "Optionally prepends a constant (intercept) column to a feature matrix. When the flag is false the matrix is returned unchanged. When the flag is true a new first column filled with the given scale value is inserted before the existing columns.",
    "cases": [
        {"input": {"op": "prepend_constant_column", "fitIntercept": false, "matrix": [[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0]], "scale": 1.0}, "expected_output": "1,2,3,4\n5,6,7,8\n"},
        {"input": {"op": "prepend_constant_column", "fitIntercept": true, "matrix": [[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0]], "scale": 2.0}, "expected_output": "2,1,2,3,4\n2,5,6,7,8\n"},
        {"input": {"op": "prepend_constant_column", "fitIntercept": true, "matrix": [[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0]], "scale": 0.0}, "expected_output": "0,1,2,3,4\n0,5,6,7,8\n"}
    ]
}
```

*11.2 Features/target split — separate columns into a features table and a target table*

The input is a `dataset` (rows of cells) and a list of `targetIndices`. The output prints a `features:` section (the rows restricted to the non-target columns) followed by a `target:` section (the rows restricted to the target columns), one row per line. Duplicate target indices are de-duplicated. A target index outside the column range is rejected with `error=out_of_range`.

**Test Cases:** `rcb_tests/public_test_cases/feature11_2_features_target_split.json`

```json
{
    "description": "Splits a tabular dataset by column into a features table and a target table, given the target column indices. Output lists the features rows then the target rows. Duplicate target indices are de-duplicated. A target index outside the column range is rejected with a neutral out-of-range error.",
    "cases": [
        {"input": {"op": "split_features_target", "dataset": [[0, 1, 2, 4, 5], [10, 20, 30, 40, 50], [66, 77, 88, 99, 11], [11, 22, 33, 44, 55]], "targetIndices": [3]}, "expected_output": "features:\n0,1,2,5\n10,20,30,50\n66,77,88,11\n11,22,33,55\ntarget:\n4\n40\n99\n44\n"},
        {"input": {"op": "split_features_target", "dataset": [[0, 1, 2, 4, 5], [10, 20, 30, 40, 50], [66, 77, 88, 99, 11], [11, 22, 33, 44, 55]], "targetIndices": [0, 3]}, "expected_output": "features:\n1,2,5\n20,30,50\n77,88,11\n22,33,55\ntarget:\n0,4\n10,40\n66,99\n11,44\n"},
        {"input": {"op": "split_features_target", "dataset": [[0, 1, 2, 4, 5], [10, 20, 30, 40, 50], [66, 77, 88, 99, 11], [11, 22, 33, 44, 55]], "targetIndices": [0, 3, 0, 0, 3]}, "expected_output": "features:\n1,2,5\n20,30,50\n77,88,11\n22,33,55\ntarget:\n0,4\n10,40\n66,99\n11,44\n"}
    ]
}
```

---

### Feature 12: KD-Tree Nearest-Neighbour Retrieval

**As a developer**, I want to index a set of points in a KD-tree and query the k nearest to an arbitrary point, so I can accelerate nearest-neighbour retrieval over a fixed dataset.

**Expected Behavior / Usage:**

The input is a `data` matrix (rows are points), a `point` to query, a neighbour count `k`, a `leafSize`, a split strategy (`inOrder` or `largestVariance`), and a distance metric. The output is a single line of the zero-based indices of the k nearest points, ordered nearest-first, comma-separated. The result is independent of `leafSize` and split strategy (these only affect internal tree shape, not the answer). A query point whose length does not match the data dimensionality is rejected with `error=invalid_query_length`.

**Test Cases:** `rcb_tests/public_test_cases/feature12_kdtree_query.json`

```json
{
    "description": "KD-tree nearest-neighbour retrieval: builds a KD-tree from a set of points and returns the zero-based indices of the k nearest points to a query point, ordered nearest-first. Supports a configurable leaf size, a split strategy ('inOrder' or 'largestVariance') and a distance metric ('euclidean', 'manhattan', 'cosine').",
    "cases": [
        {"input": {"op": "kdtree_query", "data": [[3.43, 10.91, 11.62, -12.93, -11.66], [19.41, -4.96, 3.99, 16.35, 10.57], [11.3, 8.89, -17.66, -5.17, 16.2], [-8.13, -5.23, 18.01, 1.97, 9.08], [13.98, -8.21, 17.01, -5.14, 14.49], [-17.65, 13.1, 5.82, 8.61, 14.41], [4.16, -4.72, -3.71, -2.32, -13.7], [7.29, 11.16, -9.51, -1.89, -18.94], [19.81, 3.17, 14.27, 0.05, -17.93], [-9.63, 18.82, -14.4, -1.91, -6.58], [-10.95, -19.58, 9.05, 17.39, 3.3], [4.08, -13.19, -5.71, 18.56, -0.13], [2.79, -9.15, 6.56, -18.59, 13.53], [-7.56, 11.97, 6.55, -7.54, 15.9], [-15.97, -15.95, 7.71, 9.7, 16.94], [-15.01, 16.12, -10.42, -17.61, 6.27], [7.63, -10.7, 15.09, 10.25, -18.16], [0.05, 9.74, 7.08, 15.49, -17.99], [-6.48, 1.1, 9.28, 0.9, 6.09], [-9.88, -5.66, -16.15, 4.46, 2.34]], "leafSize": 3, "point": [2.79, -9.15, 6.56, -18.59, 13.53], "k": 3}, "expected_output": "12,4,18\n"},
        {"input": {"op": "kdtree_query", "data": [[3.43, 10.91, 11.62, -12.93, -11.66], [19.41, -4.96, 3.99, 16.35, 10.57], [11.3, 8.89, -17.66, -5.17, 16.2], [-8.13, -5.23, 18.01, 1.97, 9.08], [13.98, -8.21, 17.01, -5.14, 14.49], [-17.65, 13.1, 5.82, 8.61, 14.41], [4.16, -4.72, -3.71, -2.32, -13.7], [7.29, 11.16, -9.51, -1.89, -18.94], [19.81, 3.17, 14.27, 0.05, -17.93], [-9.63, 18.82, -14.4, -1.91, -6.58], [-10.95, -19.58, 9.05, 17.39, 3.3], [4.08, -13.19, -5.71, 18.56, -0.13], [2.79, -9.15, 6.56, -18.59, 13.53], [-7.56, 11.97, 6.55, -7.54, 15.9], [-15.97, -15.95, 7.71, 9.7, 16.94], [-15.01, 16.12, -10.42, -17.61, 6.27], [7.63, -10.7, 15.09, 10.25, -18.16], [0.05, 9.74, 7.08, 15.49, -17.99], [-6.48, 1.1, 9.28, 0.9, 6.09], [-9.88, -5.66, -16.15, 4.46, 2.34]], "leafSize": 1, "point": [2.79, -9.15, 6.56, -18.59, 13.53], "k": 3}, "expected_output": "12,4,18\n"},
        {"input": {"op": "kdtree_query", "data": [[3.43, 10.91, 11.62, -12.93, -11.66], [19.41, -4.96, 3.99, 16.35, 10.57], [11.3, 8.89, -17.66, -5.17, 16.2], [-8.13, -5.23, 18.01, 1.97, 9.08], [13.98, -8.21, 17.01, -5.14, 14.49], [-17.65, 13.1, 5.82, 8.61, 14.41], [4.16, -4.72, -3.71, -2.32, -13.7], [7.29, 11.16, -9.51, -1.89, -18.94], [19.81, 3.17, 14.27, 0.05, -17.93], [-9.63, 18.82, -14.4, -1.91, -6.58], [-10.95, -19.58, 9.05, 17.39, 3.3], [4.08, -13.19, -5.71, 18.56, -0.13], [2.79, -9.15, 6.56, -18.59, 13.53], [-7.56, 11.97, 6.55, -7.54, 15.9], [-15.97, -15.95, 7.71, 9.7, 16.94], [-15.01, 16.12, -10.42, -17.61, 6.27], [7.63, -10.7, 15.09, 10.25, -18.16], [0.05, 9.74, 7.08, 15.49, -17.99], [-6.48, 1.1, 9.28, 0.9, 6.09], [-9.88, -5.66, -16.15, 4.46, 2.34]], "leafSize": 3, "point": [13.98, -8.21, 17.01, -5.14, 14.49], "k": 4}, "expected_output": "4,12,3,18\n"},
        {"input": {"op": "kdtree_query", "data": [[3.43, 10.91, 11.62, -12.93, -11.66], [19.41, -4.96, 3.99, 16.35, 10.57], [11.3, 8.89, -17.66, -5.17, 16.2], [-8.13, -5.23, 18.01, 1.97, 9.08], [13.98, -8.21, 17.01, -5.14, 14.49], [-17.65, 13.1, 5.82, 8.61, 14.41], [4.16, -4.72, -3.71, -2.32, -13.7], [7.29, 11.16, -9.51, -1.89, -18.94], [19.81, 3.17, 14.27, 0.05, -17.93], [-9.63, 18.82, -14.4, -1.91, -6.58], [-10.95, -19.58, 9.05, 17.39, 3.3], [4.08, -13.19, -5.71, 18.56, -0.13], [2.79, -9.15, 6.56, -18.59, 13.53], [-7.56, 11.97, 6.55, -7.54, 15.9], [-15.97, -15.95, 7.71, 9.7, 16.94], [-15.01, 16.12, -10.42, -17.61, 6.27], [7.63, -10.7, 15.09, 10.25, -18.16], [0.05, 9.74, 7.08, 15.49, -17.99], [-6.48, 1.1, 9.28, 0.9, 6.09], [-9.88, -5.66, -16.15, 4.46, 2.34]], "leafSize": 3, "point": [-9.88, -5.66, -16.15, 4.46, 2.34], "k": 20}, "expected_output": "19,11,6,9,18,2,14,10,15,5,7,13,3,12,17,1,0,16,4,8\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the metrics, link functions, kernels, optimizer cost/gradient, learning-rate schedules, cross-validation index planners, empirical distribution, tree impurity measures, nearest-neighbour and KD-tree retrieval, and data-shaping helpers described above. Group each family into its own cohesive module; do not place everything in one file.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to your core system. It reads one JSON command object from stdin, routes it (by its `op` field) to the appropriate core logic, and prints the result to stdout, strictly matching the per-feature line contracts above — including rendering every error as a single neutral `error=<category>` line. This adapter must be logically and physically separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_precision.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_precision@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- output the negative two times the transpose of x times the residual vector (y minus xw)
