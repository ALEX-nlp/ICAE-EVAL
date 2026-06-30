## Product Requirement Document

# Statistical Distributions and Tests Toolkit - A Pure-Computation Statistics Library

## Project Goal

Build a self-contained statistics library that lets developers compute descriptive statistics, evaluate the most common probability distributions, and run standard statistical hypothesis tests, so they can perform quantitative analysis without pulling in a heavyweight numerical stack or re-deriving the formulas by hand.

---

## Background & Problem

Without this library, developers who need a mean, a binomial probability, or a t-test must either re-implement well-known but error-prone formulas (incomplete gamma/beta functions, tie-aware ranking, variance decomposition) or depend on a large scientific computing framework. Both options are costly: hand-rolled formulas are easy to get subtly wrong at the edges (negative inputs, empty collections, undefined parameters), and a heavyweight dependency is overkill for routine work.

With this library, each statistical primitive is exposed as a small, well-defined operation with explicit, observable behavior at the boundaries, so developers get correct, predictable results for both typical and edge-case inputs.

---

## Program Interface (Wire Format)

The deliverable is a program that reads exactly one JSON command object from standard input and prints the result to standard output. A command has the shape `{"op": "<operation>", "args": { ... }, "round": <integer, optional>}`. The `op` string selects the operation; `args` carries its inputs; the optional `round` rounds any floating-point result to that many decimal places before printing.

Output rendering rules (every `expected_output` below is the exact stdout, including the trailing newline):

- A missing/undefined result is printed as `nil`.
- Boolean results are printed as `true` or `false`.
- Integer results are printed as their digits; floating-point results are printed as the shortest decimal string that round-trips to the same value; non-finite results are printed as `Infinity`, `-Infinity`, or `NaN`.
- A scalar result is printed on a single line. An array result is printed inline as `[a, b, c]`.
- A composite (key/value) result is printed as one `key=value` line per entry, in the fixed order documented for that operation.
- If an operation raises, the program prints a single line `error: <message>`.

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

### Feature 1: Descriptive Statistics over a Collection

**As a developer**, I want to summarise a numeric collection, so I can understand its center and spread without writing the formulas by hand.

**Expected Behavior / Usage:**

Operation `collection.mean` returns the arithmetic mean of the values. `collection.variance` returns the sample variance (sum of squared deviations from the mean divided by n-1). `collection.standard_deviation` returns the square root of the sample variance. Each takes `{"data": [numbers]}` and prints a single floating-point value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_descriptive_statistics.json`

```json
{
    "description": "Descriptive measures over a numeric collection: arithmetic mean, sample variance (divided by n-1) and sample standard deviation (square root of the sample variance).",
    "cases": [
        {"input": {"op": "collection.mean", "args": {"data": [1, 2, 3, 4, 5]}}, "expected_output": "3.0\n"},
        {"input": {"op": "collection.variance", "args": {"data": [1, 2, 3, 4, 5]}}, "expected_output": "2.5\n"},
        {"input": {"op": "collection.standard_deviation", "args": {"data": [1, 2, 3, 4, 5]}}, "expected_output": "1.5811388300841898\n"}
    ]
}
```

---

### Feature 2: Combinatorics: Factorial, Arrangements, Selections

**As a developer**, I want to compute factorials and counting quantities, so I can reuse correct combinatorial building blocks.

**Expected Behavior / Usage:**

Operation `math.factorial` with `{"n": <number>}` returns no value (printed as `nil`) for negative n, returns 1 for n equal to 0 or 1, and otherwise truncates any fractional part of n and returns the factorial of the resulting integer. `math.permutation` with `{"n", "k"}` returns the number of ordered arrangements of k items chosen from n. `math.combination` with `{"n", "r"}` returns the number of unordered selections of r items chosen from n. Permutation and combination results are emitted in floating-point form.

**Test Cases:** `rcb_tests/public_test_cases/feature2_combinatorics.json`

```json
{
    "description": "Integer combinatorial helpers: factorial (undefined for negatives, equal to 1 for 0 and 1, and computed for larger integers after truncating any fractional part of the input), the number of ordered arrangements of k items chosen from n, and the number of unordered selections of r items chosen from n.",
    "cases": [
        {"input": {"op": "math.factorial", "args": {"n": -7}}, "expected_output": "nil\n"},
        {"input": {"op": "math.permutation", "args": {"n": 15, "k": 4}}, "expected_output": "32760.0\n"},
        {"input": {"op": "math.combination", "args": {"n": 16, "r": 3}}, "expected_output": "560.0\n"}
    ]
}
```

---

### Feature 3: Numerical Integration and Special Functions

**As a developer**, I want to approximate integrals and evaluate special functions, so I can support downstream probability calculations.

**Expected Behavior / Usage:**

Operation `math.simpson_rule` with `{"a", "b", "intervals", "function"}` approximates the definite integral of the named integrand over [a, b] using a composite rule; the integrand `"square"` is x^2 and `"sine"` is sin(x). The number of sub-intervals MUST be even: when it is odd the routine prints the notice line `The composite simpson's rule needs even intervals!` and yields no value (`nil`). When a value is produced it is reported floored to the nearest lower integer. Operation `math.lower_incomplete_gamma` with `{"s", "x"}` returns the lower incomplete gamma function. Operation `math.beta` with `{"x", "y"}` returns the beta function and is exactly 1 when both parameters equal 1. Operation `math.incomplete_beta` with `{"x", "alpha", "beta"}` returns the regularized incomplete beta value. Optional `"round"` rounds the printed float to the given number of decimals.

**Test Cases:** `rcb_tests/public_test_cases/feature3_numerical_functions.json`

```json
{
    "description": "Numerical building blocks. A composite Simpson's rule approximates a definite integral over [a,b] using a number of sub-intervals that MUST be even; when the interval count is odd the routine emits the notice line \"The composite simpson's rule needs even intervals!\" and yields no value. The lower incomplete gamma function, the beta function (which is exactly 1 when both parameters are 1) and the regularized incomplete beta function are also exposed. For the named integrands, \"square\" integrates x^2 and \"sine\" integrates sin(x); the Simpson result is reported floored to the nearest lower integer.",
    "cases": [
        {"input": {"op": "math.simpson_rule", "args": {"a": 0, "b": 12, "intervals": 10000, "function": "square"}}, "expected_output": "576\n"},
        {"input": {"op": "math.simpson_rule", "args": {"a": 0, "b": 12, "intervals": 10000, "function": "sine"}}, "expected_output": "0\n"},
        {"input": {"op": "math.simpson_rule", "args": {"a": 1, "b": 2, "intervals": 3, "function": "identity"}}, "expected_output": "The composite simpson's rule needs even intervals!\nnil\n"},
        {"input": {"op": "math.lower_incomplete_gamma", "args": {"s": 1, "x": 1}, "round": 4}, "expected_output": "0.6322\n"},
        {"input": {"op": "math.beta", "args": {"x": 1, "y": 1}}, "expected_output": "1\n"},
        {"input": {"op": "math.incomplete_beta", "args": {"x": 0.1, "alpha": 1, "beta": 2}, "round": 4}, "expected_output": "0.19\n"}
    ]
}
```

---

### Feature 4: Rank Correlation

**As a developer**, I want to rank values and correlate two rankings, so I can measure monotonic association between two variables.

**Expected Behavior / Usage:**

Operation `rank_correlation.ranks` with `{"data": [numbers]}` returns the rank vector, assigning rank 1 to the largest value and resolving ties by averaging the positions they occupy (producing fractional ranks). Operation `rank_correlation.ranks_detail` returns, per distinct value, a record of how many times it occurred, the accumulated raw rank, and the resolved (possibly fractional) tie rank. Operation `rank_correlation.coefficient` with `{"set_one", "set_two"}` ranks each set and returns the rank-correlation coefficient. Operation `rank_correlation.coefficient_raw` computes the coefficient directly from two already-prepared equal-length rank vectors; it raises an error (printed as `error: <message>`) when the two inputs differ in length, and yields no value when both inputs are empty.

**Test Cases:** `rcb_tests/public_test_cases/feature4_rank_correlation.json`

```json
{
    "description": "Spearman-style rank correlation. Ranking assigns rank 1 to the largest value and resolves ties by averaging the positions they occupy (producing fractional ranks). A detailed ranking variant additionally reports, per distinct value, how many times it occurred, the accumulated raw rank and the resolved (possibly fractional) tie rank. The correlation coefficient is computed from two equally sized rank vectors; it raises when the two inputs differ in size and yields no value when both inputs are empty.",
    "cases": [
        {"input": {"op": "rank_correlation.ranks", "args": {"data": [10, 30, 12, 15, 3]}}, "expected_output": "[4, 1, 3, 2, 5]\n"},
        {"input": {"op": "rank_correlation.ranks", "args": {"data": [56, 75, 45, 71, 61, 64, 58, 80, 76, 61]}}, "expected_output": "[9, 3, 10, 4, 6.5, 5, 8, 1, 2, 6.5]\n"},
        {"input": {"op": "rank_correlation.ranks_detail", "args": {"data": [10, 30, 12, 15, 3]}}, "expected_output": "10={counter: 1, rank: 4, tie_rank: 4}\n30={counter: 1, rank: 1, tie_rank: 1}\n12={counter: 1, rank: 3, tie_rank: 3}\n15={counter: 1, rank: 2, tie_rank: 2}\n3={counter: 1, rank: 5, tie_rank: 5}\n"},
        {"input": {"op": "rank_correlation.coefficient", "args": {"set_one": [1760, 2040, 2440, 2550, 2730, 2740, 3010, 3080, 3370, 3740, 4910, 5090, 5090, 5380, 5850, 6730, 6990, 7960], "set_two": [529, 566, 473, 461, 465, 532, 484, 527, 488, 485, 478, 434, 468, 449, 425, 389, 421, 416]}, "round": 7}, "expected_output": "-0.7630357\n"},
        {"input": {"op": "rank_correlation.coefficient_raw", "args": {"set_one": [1, 2, 3], "set_two": [1, 2, 3, 4]}}, "expected_output": "error: Both group sets must have the same number of cases.\n"},
        {"input": {"op": "rank_correlation.coefficient_raw", "args": {"set_one": [], "set_two": []}}, "expected_output": "nil\n"}
    ]
}
```

---

### Feature 5: Bernoulli Distribution

**As a developer**, I want to evaluate a single-trial success/failure distribution, so I can model binary outcomes.

**Expected Behavior / Usage:**

For success probability p, operation `bernoulli.pmf` with `{"n", "p"}` returns the mass at outcome n: it yields no value for any n other than 0 or 1, equals 1-p at 0 and p at 1. Operation `bernoulli.cdf` returns the cumulative value: no value outside {0,1}, 1-p at 0, and 1 at 1. Operation `bernoulli.variance` with `{"p"}` returns p(1-p); `bernoulli.skewness` and `bernoulli.kurtosis` return the standard closed-form skewness and excess kurtosis.

**Test Cases:** `rcb_tests/public_test_cases/feature5_bernoulli_distribution.json`

```json
{
    "description": "Bernoulli distribution with success probability p. The mass and cumulative functions are only defined for the outcomes 0 and 1 (any other outcome yields no value): the mass at 0 is 1-p and at 1 is p, while the cumulative value at 0 is 1-p and at 1 is 1. Variance is p(1-p); skewness and excess-kurtosis follow the standard closed forms.",
    "cases": [
        {"input": {"op": "bernoulli.pmf", "args": {"n": 5, "p": 0.3}}, "expected_output": "nil\n"},
        {"input": {"op": "bernoulli.pmf", "args": {"n": 0, "p": 0.3}}, "expected_output": "0.7\n"},
        {"input": {"op": "bernoulli.cdf", "args": {"n": 5, "p": 0.3}}, "expected_output": "nil\n"},
        {"input": {"op": "bernoulli.variance", "args": {"p": 0.3}}, "expected_output": "0.21\n"},
        {"input": {"op": "bernoulli.skewness", "args": {"p": 0.3}}, "expected_output": "0.8728715609439696\n"},
        {"input": {"op": "bernoulli.kurtosis", "args": {"p": 0.3}}, "expected_output": "-1.238095238095237\n"}
    ]
}
```

---

### Feature 6: Binomial Distribution

**As a developer**, I want to evaluate the distribution of successes across n trials, so I can model repeated independent trials.

**Expected Behavior / Usage:**

Parameterised by trials n and success probability p. Operation `binomial.pmf` with `{"n", "p", "k"}` and `binomial.cdf` yield no value for k below 0 or above n. Operation `binomial.mean` returns n*p; `binomial.variance` returns n*p*(1-p). Operation `binomial.mode` returns the floor of (n+1)*p, except that when (n+1)*p is a whole number strictly between 1 and n the two adjacent integers are both returned (as a list), and when it equals n+1 the mode is n. Optional `"round"` controls printed precision.

**Test Cases:** `rcb_tests/public_test_cases/feature6_binomial_distribution.json`

```json
{
    "description": "Binomial distribution parameterised by a number of trials n and a per-trial success probability p. The mass and cumulative functions are undefined (no value) for k below 0 or above n. Mean is n*p and variance is n*p*(1-p). The mode is the floor of (n+1)*p, except that when (n+1)*p is a whole number between 1 and n the two adjacent integers are returned, and when it equals n+1 the mode is n.",
    "cases": [
        {"input": {"op": "binomial.pmf", "args": {"n": 0, "p": 0, "k": -5}}, "expected_output": "nil\n"},
        {"input": {"op": "binomial.pmf", "args": {"n": 10, "p": 0.5, "k": 1}}, "expected_output": "0.009765625\n"},
        {"input": {"op": "binomial.cdf", "args": {"n": 0, "p": 0, "k": -5}}, "expected_output": "nil\n"},
        {"input": {"op": "binomial.cdf", "args": {"n": 10, "p": 0.5, "k": 1}, "round": 8}, "expected_output": "0.01074219\n"},
        {"input": {"op": "binomial.mean", "args": {"n": 8, "p": 0.5}}, "expected_output": "4.0\n"},
        {"input": {"op": "binomial.variance", "args": {"n": 8, "p": 0.5}}, "expected_output": "2.0\n"},
        {"input": {"op": "binomial.mode", "args": {"n": 9, "p": 0.2702702702702703}}, "expected_output": "2\n"},
        {"input": {"op": "binomial.mode", "args": {"n": 11, "p": 0.5}}, "expected_output": "[6.0, 5.0]\n"},
        {"input": {"op": "binomial.mode", "args": {"n": 7, "p": 1.0}}, "expected_output": "7\n"}
    ]
}
```

---

### Feature 7: Negative Binomial Distribution

**As a developer**, I want to evaluate the distribution of trials until a number of failures, so I can model over-dispersed count data.

**Expected Behavior / Usage:**

Parameterised by a number of failures r and a per-trial probability p. Operation `negative_binomial.pmf` with `{"r", "p", "k"}` and `negative_binomial.cdf` yield no value for k below 0 or above r. Operation `negative_binomial.mean` returns p*r/(1-p); `negative_binomial.variance` returns p*r/(1-p)^2. Operation `negative_binomial.mode` returns 0 when r<=1 and otherwise the floor of p*(r-1)/(1-p). Operation `negative_binomial.skewness` returns the standard closed form. Optional `"round"` controls printed precision.

**Test Cases:** `rcb_tests/public_test_cases/feature7_negative_binomial_distribution.json`

```json
{
    "description": "Negative binomial distribution parameterised by a number of failures r and a per-trial probability p. The mass and cumulative functions are undefined (no value) for k below 0 or above r. Mean is p*r/(1-p); variance is p*r/(1-p)^2. The mode is 0 when r<=1, otherwise the floor of p*(r-1)/(1-p); skewness follows the standard closed form.",
    "cases": [
        {"input": {"op": "negative_binomial.pmf", "args": {"r": 0, "p": 0, "k": -5}}, "expected_output": "nil\n"},
        {"input": {"op": "negative_binomial.pmf", "args": {"r": 10, "p": 0.5, "k": 1}, "round": 8}, "expected_output": "0.00488281\n"},
        {"input": {"op": "negative_binomial.cdf", "args": {"r": 0, "p": 0, "k": -5}}, "expected_output": "nil\n"},
        {"input": {"op": "negative_binomial.cdf", "args": {"r": 10, "p": 0.5, "k": 1}, "round": 9}, "expected_output": "0.005859375\n"},
        {"input": {"op": "negative_binomial.mean", "args": {"r": 8, "p": 0.3}}, "expected_output": "3.428571428571429\n"},
        {"input": {"op": "negative_binomial.variance", "args": {"r": 8, "p": 0.3}}, "expected_output": "4.8979591836734695\n"},
        {"input": {"op": "negative_binomial.mode", "args": {"r": -3, "p": 0.3}}, "expected_output": "0.0\n"},
        {"input": {"op": "negative_binomial.mode", "args": {"r": 5, "p": 0.3}}, "expected_output": "1\n"},
        {"input": {"op": "negative_binomial.skewness", "args": {"r": 8, "p": 0.3}}, "expected_output": "0.8391463916782737\n"}
    ]
}
```

---

### Feature 8: Poisson Distribution

**As a developer**, I want to evaluate the distribution of event counts at a fixed rate, so I can model rare events over an interval.

**Expected Behavior / Usage:**

Parameterised by an expected rate lambda. Operation `poisson.pmf` with `{"lambda", "k"}` returns the probability of exactly k events; `poisson.cdf` returns the probability of at most k events. Operations `poisson.mean` and `poisson.variance` with `{"lambda"}` both return lambda. Optional `"round"` controls printed precision.

**Test Cases:** `rcb_tests/public_test_cases/feature8_poisson_distribution.json`

```json
{
    "description": "Poisson distribution parameterised by an expected rate lambda. The mass function gives the probability of exactly k events; the cumulative function gives the probability of at most k events. Both mean and variance equal lambda.",
    "cases": [
        {"input": {"op": "poisson.pmf", "args": {"lambda": 2, "k": 1}, "round": 3}, "expected_output": "0.271\n"},
        {"input": {"op": "poisson.cdf", "args": {"lambda": 2, "k": 1}, "round": 3}, "expected_output": "0.406\n"},
        {"input": {"op": "poisson.mean", "args": {"lambda": 5}}, "expected_output": "5\n"},
        {"input": {"op": "poisson.variance", "args": {"lambda": 5}}, "expected_output": "5\n"}
    ]
}
```

---

### Feature 9: Geometric Distribution

**As a developer**, I want to evaluate the distribution of trials until the first success, so I can model waiting times for a first success.

**Expected Behavior / Usage:**

For success probability p, a boolean flag `zero_inclusive` selects the support. When the flag is false (default), the variable counts the number of trials up to and including the first success, so the mass and cumulative functions yield no value for k<=0. When the flag is true, the variable counts the number of failures before the first success, so they yield no value only for k<0 and admit k=0. Operations `geometric.pmf`, `geometric.cdf`, `geometric.mean`, `geometric.median`, and `geometric.mode` all depend on the selected support; `geometric.variance`, `geometric.skewness`, and `geometric.kurtosis` depend only on p.

**Test Cases:** `rcb_tests/public_test_cases/feature9_geometric_distribution.json`

```json
{
    "description": "Geometric distribution with success probability p. A flag selects the support. By default (the flag off) the variable counts the number of trials up to and including the first success, so it is undefined (no value) for k<=0. When the zero-inclusive variant is selected (flag on) the variable counts the number of failures before the first success, so it is undefined only for k<0 and admits k=0. The mass, cumulative, mean, median and mode all depend on which support is selected; variance, skewness and kurtosis depend only on p.",
    "cases": [
        {"input": {"op": "geometric.pmf", "args": {"p": 0.5, "k": 1, "zero_inclusive": true}}, "expected_output": "0.25\n"},
        {"input": {"op": "geometric.pmf", "args": {"p": 0.5, "k": 1, "zero_inclusive": false}}, "expected_output": "0.5\n"},
        {"input": {"op": "geometric.cdf", "args": {"p": 0.5, "k": 1, "zero_inclusive": true}}, "expected_output": "0.75\n"},
        {"input": {"op": "geometric.cdf", "args": {"p": 0.5, "k": 1, "zero_inclusive": false}}, "expected_output": "0.5\n"},
        {"input": {"op": "geometric.mean", "args": {"p": 0.5, "zero_inclusive": true}}, "expected_output": "1.0\n"},
        {"input": {"op": "geometric.mean", "args": {"p": 0.5, "zero_inclusive": false}}, "expected_output": "2.0\n"},
        {"input": {"op": "geometric.median", "args": {"p": 0.5, "zero_inclusive": true}}, "expected_output": "0.0\n"},
        {"input": {"op": "geometric.mode", "args": {"p": 0.5, "zero_inclusive": true}}, "expected_output": "0.0\n"},
        {"input": {"op": "geometric.variance", "args": {"p": 0.5}}, "expected_output": "2.0\n"},
        {"input": {"op": "geometric.skewness", "args": {"p": 0.5}}, "expected_output": "2.1213203435596424\n"},
        {"input": {"op": "geometric.kurtosis", "args": {"p": 0.5}}, "expected_output": "6.5\n"}
    ]
}
```

---

### Feature 10: Logarithmic Series Distribution

**As a developer**, I want to evaluate a logarithmic-series count distribution, so I can model heavily skewed count data.

**Expected Behavior / Usage:**

Parameterised by p. Operation `log_series.pmf` with `{"k", "p"}` and `log_series.cdf` yield no value for k<=0. Operation `log_series.mode` always returns 1. Operations `log_series.mean` and `log_series.variance` with `{"p"}` depend only on p. Optional `"round"` controls printed precision.

**Test Cases:** `rcb_tests/public_test_cases/feature10_log_series_distribution.json`

```json
{
    "description": "Logarithmic-series distribution with parameter p. The mass and cumulative functions are undefined (no value) for k<=0. The mode is always 1; mean and variance depend only on p.",
    "cases": [
        {"input": {"op": "log_series.pmf", "args": {"k": -3, "p": 0.5}}, "expected_output": "nil\n"},
        {"input": {"op": "log_series.pmf", "args": {"k": 1, "p": 0.5}, "round": 6}, "expected_output": "0.721348\n"},
        {"input": {"op": "log_series.cdf", "args": {"k": -3, "p": 0.5}}, "expected_output": "nil\n"},
        {"input": {"op": "log_series.cdf", "args": {"k": 1, "p": 0.5}, "round": 6}, "expected_output": "0.721348\n"},
        {"input": {"op": "log_series.mode", "args": {}}, "expected_output": "1.0\n"},
        {"input": {"op": "log_series.mean", "args": {"p": 0.5}}, "expected_output": "1.4426950408889634\n"},
        {"input": {"op": "log_series.variance", "args": {"p": 0.5}}, "expected_output": "0.804021100772319\n"}
    ]
}
```

---

### Feature 11: Continuous Uniform Distribution

**As a developer**, I want to evaluate a flat distribution over an interval, so I can model equally likely outcomes in a range.

**Expected Behavior / Usage:**

Over the closed interval [left, right], operation `uniform.pdf` with `{"left", "right", "value"}` returns the constant density 1/(right-left) inside the interval and 0 outside it. Operation `uniform.cdf` returns 0 below the interval, a value rising linearly inside it, and 1 above it. Operation `uniform.mean` with `{"left", "right"}` returns the midpoint; `uniform.variance` returns (right-left)^2/12.

**Test Cases:** `rcb_tests/public_test_cases/feature11_uniform_distribution.json`

```json
{
    "description": "Continuous uniform distribution over the closed interval [left, right]. The density is constant 1/(right-left) inside the interval and 0 outside it. The cumulative value is 0 below the interval, rises linearly inside it and is 1 above it. Mean (and median) is the midpoint; variance is (right-left)^2/12.",
    "cases": [
        {"input": {"op": "uniform.pdf", "args": {"left": 3.0, "right": 4.0, "value": 3.5}}, "expected_output": "1\n"},
        {"input": {"op": "uniform.pdf", "args": {"left": 2, "right": 5, "value": 1}}, "expected_output": "0\n"},
        {"input": {"op": "uniform.cdf", "args": {"left": 2, "right": 4, "value": 1}}, "expected_output": "0\n"},
        {"input": {"op": "uniform.cdf", "args": {"left": 2, "right": 4, "value": 3}}, "expected_output": "0.5\n"},
        {"input": {"op": "uniform.mean", "args": {"left": 2, "right": 4}}, "expected_output": "3.0\n"},
        {"input": {"op": "uniform.variance", "args": {"left": 2, "right": 4}}, "expected_output": "0.3333333333333333\n"}
    ]
}
```

---

### Feature 12: Beta Distribution

**As a developer**, I want to evaluate a distribution over the unit interval, so I can model probabilities and proportions.

**Expected Behavior / Usage:**

With shape parameters alpha and beta, operation `beta.pdf` with `{"alpha", "beta", "value"}` returns 0 outside [0,1]. Operation `beta.cdf` returns the regularized incomplete beta value, returning 1 for inputs above 1 and no value for inputs below 0. Operation `beta.mode` with `{"alpha", "beta"}` is defined only when both shapes exceed 1 and equals (alpha-1)/(alpha+beta-2). Operation `beta.mean` returns alpha/(alpha+beta) and yields no value when alpha+beta is 0. Optional `"round"` controls printed precision.

**Test Cases:** `rcb_tests/public_test_cases/feature12_beta_distribution.json`

```json
{
    "description": "Beta distribution with shape parameters alpha and beta. The density is 0 outside the [0,1] interval. The cumulative function reports the regularized incomplete beta value, returning 1 for inputs above 1 and no value for inputs below 0. The mode is defined only when both shapes exceed 1 and equals (alpha-1)/(alpha+beta-2); the mean is alpha/(alpha+beta) and is undefined (no value) when alpha+beta is 0.",
    "cases": [
        {"input": {"op": "beta.cdf", "args": {"alpha": 2, "beta": 3, "value": 5}}, "expected_output": "1.0\n"},
        {"input": {"op": "beta.cdf", "args": {"alpha": 2, "beta": 3, "value": -1}}, "expected_output": "nil\n"},
        {"input": {"op": "beta.cdf", "args": {"alpha": 2, "beta": 3, "value": 0.1}, "round": 4}, "expected_output": "0.0523\n"},
        {"input": {"op": "beta.pdf", "args": {"alpha": 1, "beta": 1, "value": 2}}, "expected_output": "0\n"},
        {"input": {"op": "beta.pdf", "args": {"alpha": 3, "beta": 2, "value": 0.1}, "round": 4}, "expected_output": "0.108\n"},
        {"input": {"op": "beta.mode", "args": {"alpha": 4, "beta": 6}}, "expected_output": "0.375\n"},
        {"input": {"op": "beta.mode", "args": {"alpha": 1, "beta": 1}}, "expected_output": "nil\n"},
        {"input": {"op": "beta.mean", "args": {"alpha": 0, "beta": 0}}, "expected_output": "nil\n"},
        {"input": {"op": "beta.mean", "args": {"alpha": 2, "beta": 3}}, "expected_output": "0.4\n"}
    ]
}
```

---

### Feature 13: Chi-squared Distribution

**As a developer**, I want to evaluate a chi-squared distribution, so I can support goodness-of-fit reasoning.

**Expected Behavior / Usage:**

With k degrees of freedom, operation `chi_squared.pdf` with `{"k", "value"}` returns 0 for inputs below 0. Operation `chi_squared.cdf` returns the regularized lower incomplete gamma probability. Operation `chi_squared.mode` with `{"k"}` returns max(k-2, 0); `chi_squared.variance` returns 2k. Optional `"round"` controls printed precision.

**Test Cases:** `rcb_tests/public_test_cases/feature13_chi_squared_distribution.json`

```json
{
    "description": "Chi-squared distribution with k degrees of freedom. The density is 0 for inputs below 0. The cumulative function reports the regularized lower incomplete gamma probability. The mode is max(k-2, 0) and the variance is 2k.",
    "cases": [
        {"input": {"op": "chi_squared.cdf", "args": {"k": 5, "value": 1}, "round": 4}, "expected_output": "0.0374\n"},
        {"input": {"op": "chi_squared.pdf", "args": {"k": 3, "value": -2}}, "expected_output": "0\n"},
        {"input": {"op": "chi_squared.pdf", "args": {"k": 1, "value": 1}, "round": 4}, "expected_output": "0.242\n"},
        {"input": {"op": "chi_squared.mode", "args": {"k": 1}}, "expected_output": "0\n"},
        {"input": {"op": "chi_squared.mode", "args": {"k": 3}}, "expected_output": "1\n"},
        {"input": {"op": "chi_squared.variance", "args": {"k": 1}}, "expected_output": "2\n"}
    ]
}
```

---

### Feature 14: F Distribution

**As a developer**, I want to evaluate an F distribution, so I can support variance-ratio reasoning.

**Expected Behavior / Usage:**

With numerator and denominator degrees of freedom d1 and d2, operation `f.pdf` with `{"d1", "d2", "value"}` yields no value when either degree of freedom is negative. Operation `f.cdf` returns a regularized incomplete beta probability. Operation `f.mean` with `{"d1", "d2"}` returns d2/(d2-2) and yields no value for d2<=2. Operation `f.mode` returns ((d1-2)/d1)*(d2/(d2+2)) and yields no value for d1<=2. Optional `"round"` controls printed precision.

**Test Cases:** `rcb_tests/public_test_cases/feature14_f_distribution.json`

```json
{
    "description": "F distribution with numerator and denominator degrees of freedom d1 and d2. The density is undefined (no value) when either degree of freedom is negative. The cumulative function reports a regularized incomplete beta probability. The mean is d2/(d2-2) and is undefined for d2<=2; the mode is ((d1-2)/d1)*(d2/(d2+2)) and is undefined for d1<=2.",
    "cases": [
        {"input": {"op": "f.cdf", "args": {"d1": 3, "d2": 4, "value": 1}, "round": 7}, "expected_output": "0.5210509\n"},
        {"input": {"op": "f.pdf", "args": {"d1": 1, "d2": 2, "value": 1}, "round": 8}, "expected_output": "0.19245009\n"},
        {"input": {"op": "f.mean", "args": {"d1": 1, "d2": 5}}, "expected_output": "1.6666666666666667\n"},
        {"input": {"op": "f.mean", "args": {"d1": 3, "d2": 2}}, "expected_output": "nil\n"},
        {"input": {"op": "f.mode", "args": {"d1": 4, "d2": 6}}, "expected_output": "0.375\n"},
        {"input": {"op": "f.mode", "args": {"d1": 2, "d2": 5}}, "expected_output": "nil\n"}
    ]
}
```

---

### Feature 15: Student's t Distribution

**As a developer**, I want to evaluate a t distribution, so I can support small-sample inference.

**Expected Behavior / Usage:**

With df degrees of freedom, operation `t.pdf` with `{"df", "value"}` yields no value for df<=0. Operation `t.cdf` returns a regularized incomplete beta probability. Operation `t.mean` with `{"df"}` returns 0 for df>1 and yields no value otherwise. Operation `t.variance` returns df/(df-2) for df>2, positive infinity for 1<df<=2 (printed as `Infinity`), and yields no value otherwise. Optional `"round"` controls printed precision.

**Test Cases:** `rcb_tests/public_test_cases/feature15_t_distribution.json`

```json
{
    "description": "Student's t distribution with df degrees of freedom. The density is undefined (no value) for df<=0. The cumulative function reports a regularized incomplete beta probability. The mean is 0 for df>1 and undefined otherwise; the variance is df/(df-2) for df>2, positive infinity for 1<df<=2, and undefined otherwise.",
    "cases": [
        {"input": {"op": "t.cdf", "args": {"df": 2, "value": 1}, "round": 7}, "expected_output": "0.7886751\n"},
        {"input": {"op": "t.pdf", "args": {"df": 0, "value": 3}}, "expected_output": "nil\n"},
        {"input": {"op": "t.pdf", "args": {"df": 5, "value": 1}, "round": 8}, "expected_output": "0.2196798\n"},
        {"input": {"op": "t.mean", "args": {"df": 5}}, "expected_output": "0\n"},
        {"input": {"op": "t.mean", "args": {"df": 1}}, "expected_output": "nil\n"},
        {"input": {"op": "t.variance", "args": {"df": 5}}, "expected_output": "1.6666666666666667\n"},
        {"input": {"op": "t.variance", "args": {"df": 1.5}}, "expected_output": "Infinity\n"},
        {"input": {"op": "t.variance", "args": {"df": -3}}, "expected_output": "nil\n"}
    ]
}
```

---

### Feature 16: Weibull Distribution

**As a developer**, I want to evaluate a Weibull distribution, so I can model lifetimes and failure rates.

**Expected Behavior / Usage:**

With shape and scale parameters, operation `weibull.pdf` with `{"shape", "scale", "value"}` yields no value when either parameter is <=0 and returns 0 for inputs below 0. Operation `weibull.cdf` returns 0 for inputs <=0. Operations `weibull.mean`, `weibull.mode` (which is 0 when shape<=1), and `weibull.variance` with `{"shape", "scale"}` follow the standard gamma-function closed forms. Optional `"round"` controls printed precision.

**Test Cases:** `rcb_tests/public_test_cases/feature16_weibull_distribution.json`

```json
{
    "description": "Weibull distribution with shape and scale parameters. The density is undefined (no value) when either parameter is <=0 and is 0 for inputs below 0. The cumulative function is 0 for inputs <=0. Mean, mode (0 when shape<=1) and variance follow the standard gamma-function closed forms.",
    "cases": [
        {"input": {"op": "weibull.pdf", "args": {"shape": 3, "scale": 4, "value": 1}, "round": 8}, "expected_output": "0.04614827\n"},
        {"input": {"op": "weibull.pdf", "args": {"shape": 3, "scale": 4, "value": -2}}, "expected_output": "0\n"},
        {"input": {"op": "weibull.pdf", "args": {"shape": -2, "scale": -2, "value": 3}}, "expected_output": "nil\n"},
        {"input": {"op": "weibull.cdf", "args": {"shape": 2, "scale": 3, "value": 1}, "round": 7}, "expected_output": "0.1051607\n"},
        {"input": {"op": "weibull.cdf", "args": {"shape": 2, "scale": 3, "value": -2}}, "expected_output": "0\n"},
        {"input": {"op": "weibull.mean", "args": {"shape": 3, "scale": 4}, "round": 8}, "expected_output": "3.57191805\n"},
        {"input": {"op": "weibull.mode", "args": {"shape": 1, "scale": 5}}, "expected_output": "0\n"},
        {"input": {"op": "weibull.mode", "args": {"shape": 3, "scale": 4}, "round": 8}, "expected_output": "3.49432186\n"},
        {"input": {"op": "weibull.variance", "args": {"shape": 3, "scale": 4}, "round": 8}, "expected_output": "1.68532616\n"}
    ]
}
```

---

### Feature 17: Normal Distribution

**As a developer**, I want to evaluate a normal distribution with arbitrary parameters, so I can model bell-shaped data.

**Expected Behavior / Usage:**

With a mean and a standard deviation, operation `normal.cdf` with `{"mean", "std", "value"}` returns the probability of being at most the queried value; `normal.pdf` returns the bell-curve height at the queried value. Optional `"round"` controls printed precision.

**Test Cases:** `rcb_tests/public_test_cases/feature17_normal_distribution.json`

```json
{
    "description": "Normal (Gaussian) distribution with a mean and a standard deviation. The cumulative function reports the probability of being at most the queried value; the density reports the bell-curve height at the queried value.",
    "cases": [
        {"input": {"op": "normal.cdf", "args": {"mean": 3, "std": 5, "value": 1}, "round": 7}, "expected_output": "0.3445783\n"},
        {"input": {"op": "normal.pdf", "args": {"mean": 3, "std": 5, "value": 1}, "round": 4}, "expected_output": "0.0737\n"}
    ]
}
```

---

### Feature 18: Standard Normal Distribution

**As a developer**, I want to evaluate the standard normal distribution, so I can compute z-score probabilities.

**Expected Behavior / Usage:**

For the distribution with mean 0 and standard deviation 1, operation `standard_normal.cdf` with `{"value"}` returns the probability of being at most the queried value; `standard_normal.pdf` returns the standard bell-curve height. Optional `"round"` controls printed precision.

**Test Cases:** `rcb_tests/public_test_cases/feature18_standard_normal_distribution.json`

```json
{
    "description": "Standard normal distribution (mean 0, standard deviation 1). The cumulative function reports the probability of being at most the queried value; the density reports the standard bell-curve height.",
    "cases": [
        {"input": {"op": "standard_normal.cdf", "args": {"value": 1}, "round": 7}, "expected_output": "0.8413447\n"},
        {"input": {"op": "standard_normal.pdf", "args": {"value": 1}, "round": 5}, "expected_output": "0.24197\n"}
    ]
}
```

---

### Feature 19: Inverse Standard Normal (Quantile)

**As a developer**, I want to invert the standard normal cumulative function, so I can convert probabilities back into z-scores.

**Expected Behavior / Usage:**

Operation `inverse_standard_normal.cdf` with `{"value"}` takes a probability and returns the value whose standard-normal cumulative probability equals it. Inputs outside [0,1] yield no value; an input of 0 maps to negative infinity (printed as `-Infinity`) and an input of 1 maps to positive infinity (printed as `Infinity`).

**Test Cases:** `rcb_tests/public_test_cases/feature19_inverse_standard_normal.json`

```json
{
    "description": "Inverse standard normal (quantile) function: given a probability in [0,1] it returns the value whose standard-normal cumulative probability equals that input. Inputs outside [0,1] yield no value; an input of 0 maps to negative infinity and an input of 1 maps to positive infinity.",
    "cases": [
        {"input": {"op": "inverse_standard_normal.cdf", "args": {"value": -1e-07}}, "expected_output": "nil\n"},
        {"input": {"op": "inverse_standard_normal.cdf", "args": {"value": 0}}, "expected_output": "-Infinity\n"},
        {"input": {"op": "inverse_standard_normal.cdf", "args": {"value": 0.25}}, "expected_output": "-0.6744897502234195\n"},
        {"input": {"op": "inverse_standard_normal.cdf", "args": {"value": 1}}, "expected_output": "Infinity\n"},
        {"input": {"op": "inverse_standard_normal.cdf", "args": {"value": 1.0000001}}, "expected_output": "nil\n"}
    ]
}
```

---

### Feature 20: Empirical Cumulative Distribution

**As a developer**, I want to build a cumulative distribution from observed samples, so I can estimate probabilities directly from data.

**Expected Behavior / Usage:**

Operation `empirical.cdf` with `{"samples": [numbers], "value": <number>}` returns the fraction of samples that are less than or equal to the queried value.

**Test Cases:** `rcb_tests/public_test_cases/feature20_empirical_distribution.json`

```json
{
    "description": "Empirical cumulative distribution built from a set of observed samples: it reports the fraction of samples that are less than or equal to the queried value.",
    "cases": [
        {"input": {"op": "empirical.cdf", "args": {"samples": [1, 2, 3, 4, 5, 6, 7, 8, 9, 0], "value": 7}}, "expected_output": "0.8\n"}
    ]
}
```

---

### Feature 21: Chi-squared Goodness-of-fit Test

**As a developer**, I want to test whether observed counts match expected counts, so I can decide if a categorical model fits.

**Expected Behavior / Usage:**

Operation `chi_squared_test.statistic` with `{"expected", "observed"}` returns the pair `[chi-squared statistic, degrees of freedom]`; `expected` may be a single number (applied to every observed bucket) or a per-bucket list, and the degrees of freedom is the number of observed buckets minus one. Operation `chi_squared_test.goodness_of_fit` with `{"alpha", "expected", "observed"}` returns the test report as `key=value` lines: probability, p_value, alpha, the null/alternative decision flags (the null is retained when alpha < p_value), and the confidence level 1-alpha. Optional `"round"` controls printed precision.

**Test Cases:** `rcb_tests/public_test_cases/feature21_chi_squared_test.json`

```json
{
    "description": "Chi-squared goodness-of-fit test. The statistic step returns a pair [chi-squared statistic, degrees of freedom]; the expected argument may be a single number (the same expectation applies to every observed bucket) or a per-bucket list, and the degrees of freedom is the number of observed buckets minus one. The full test takes a significance level alpha plus the expected and observed counts and returns the test report: probability, p_value, alpha, the null/alternative decision flags (the null is retained when alpha < p_value) and the confidence level 1-alpha.",
    "cases": [
        {"input": {"op": "chi_squared_test.statistic", "args": {"expected": 100, "observed": [212, 147, 103, 50, 46, 42]}, "round": 3}, "expected_output": "[235.42, 5]\n"},
        {"input": {"op": "chi_squared_test.statistic", "args": {"expected": [232, 116, 116, 58, 58], "observed": [224, 119, 130, 48, 59]}, "round": 3}, "expected_output": "[3.784, 4]\n"},
        {"input": {"op": "chi_squared_test.goodness_of_fit", "args": {"alpha": 0.05, "expected": 100, "observed": [212, 147, 103, 50, 46, 42]}, "round": 4}, "expected_output": "probability=1.0\np_value=0.0\nalpha=0.05\nnull=false\nalternative=true\nconfidence_level=0.95\n"},
        {"input": {"op": "chi_squared_test.goodness_of_fit", "args": {"alpha": 0.05, "expected": [232, 116, 116, 58, 58], "observed": [224, 119, 130, 48, 59]}, "round": 4}, "expected_output": "probability=0.5641\np_value=0.4359\nalpha=0.05\nnull=true\nalternative=false\nconfidence_level=0.95\n"},
        {"input": {"op": "chi_squared_test.goodness_of_fit", "args": {"alpha": 0.01, "expected": 477, "observed": [481, 483, 482, 488, 478, 471, 477, 479, 475, 462]}, "round": 4}, "expected_output": "probability=0.0005\np_value=0.9995\nalpha=0.01\nnull=true\nalternative=false\nconfidence_level=0.99\n"}
    ]
}
```

---

### Feature 22: One-way ANOVA F-test

**As a developer**, I want to compare the means of two or more groups, so I can detect a difference among group means.

**Expected Behavior / Usage:**

Operation `f_test.anova_score` with `{"groups": [[...], ...]}` returns `[F statistic, numerator degrees of freedom, denominator degrees of freedom]`: with exactly two groups it is the ratio of the larger to the smaller sample variance with numerator df 1 and denominator df N-2; with more than two groups it uses the between/within variance decomposition with numerator df (groups-1) and denominator df (total-groups). Operation `f_test.one_way_anova` with `{"alpha", "groups"}` returns the test report as `key=value` lines (probability, p_value, alpha, null/alternative decision, confidence level). Optional `"round"` controls printed precision.

**Test Cases:** `rcb_tests/public_test_cases/feature22_anova_f_test.json`

```json
{
    "description": "One-way analysis of variance via the F-test. The score step returns [F statistic, numerator degrees of freedom, denominator degrees of freedom]: with exactly two groups it is the ratio of the larger to the smaller sample variance with numerator df 1 and denominator df N-2; with more than two groups it uses the between/within group variance decomposition with numerator df (groups-1) and denominator df (total-groups). The full test takes a significance level alpha and the groups and returns the report (probability, p_value, alpha, null/alternative decision, confidence level).",
    "cases": [
        {"input": {"op": "f_test.anova_score", "args": {"groups": [[1, 2, 3, 4, 5], [2, 4, 6, 8, 10]]}, "round": 6}, "expected_output": "[4.0, 1, 8]\n"},
        {"input": {"op": "f_test.anova_score", "args": {"groups": [[2.17, 1.85, 2.83, 1.69, 3.33], [2.63, 1.77, 3.25, 1.86, 2.21], [2.63, 3.78, 4.0, 2.55, 2.45], [3.79, 3.45, 3.08, 2.26, 3.18]]}, "round": 2}, "expected_output": "[2.23, 3, 16]\n"},
        {"input": {"op": "f_test.one_way_anova", "args": {"alpha": 0.1, "groups": [[2.17, 1.85, 2.83, 1.69, 3.33], [2.63, 1.77, 3.25, 1.86, 2.21], [2.63, 3.78, 4.0, 2.55, 2.45], [3.79, 3.45, 3.08, 2.26, 3.18]]}, "round": 4}, "expected_output": "probability=0.8759\np_value=0.1241\nalpha=0.1\nnull=true\nalternative=false\nconfidence_level=0.9\n"},
        {"input": {"op": "f_test.one_way_anova", "args": {"alpha": 0.05, "groups": [[7, 4, 6, 8, 6, 6, 2, 9], [5, 5, 3, 4, 4, 7, 2, 2], [2, 4, 7, 1, 2, 1, 5, 5]]}, "round": 4}, "expected_output": "probability=0.9546\np_value=0.0454\nalpha=0.05\nnull=false\nalternative=true\nconfidence_level=0.95\n"}
    ]
}
```

---

### Feature 23: Kolmogorov-Smirnov Two-sample Test

**As a developer**, I want to compare two samples without assuming a distribution, so I can decide if two samples come from the same distribution.

**Expected Behavior / Usage:**

Operation `ks_test.two_samples` with `{"group_one", "group_two"}` (and optional `"alpha"`) compares the two empirical cumulative distributions and returns a report as `key=value` lines: d_max (the largest absolute gap between the two distributions), d_critical (a critical threshold), total_samples, alpha, the null/alternative decision (the null is retained when d_max <= d_critical), and the confidence level 1-alpha. Optional `"round"` controls printed precision.

**Test Cases:** `rcb_tests/public_test_cases/feature23_kolmogorov_smirnov_test.json`

```json
{
    "description": "Two-sided Kolmogorov-Smirnov test for two samples. It compares the two empirical cumulative distributions and reports d_max (the largest absolute gap between them), a critical threshold, the total number of samples, alpha, the null/alternative decision (the null is retained when d_max <= the critical threshold) and the confidence level 1-alpha.",
    "cases": [
        {"input": {"op": "ks_test.two_samples", "args": {"group_one": [1.2, 1.4, 1.9, 3.7, 4.4, 4.8, 9.7, 17.3, 21.1, 28.4], "group_two": [5.6, 6.5, 6.6, 6.9, 9.2, 10.4, 10.6, 19.3]}, "round": 4}, "expected_output": "d_max=0.6\nd_critical=0.5805\ntotal_samples=18\nalpha=0.05\nnull=false\nalternative=true\nconfidence_level=0.95\n"}
    ]
}
```

---

### Feature 24: Student's t-test

**As a developer**, I want to compare a sample mean to a reference or to another sample, so I can decide if a difference in means is significant.

**Expected Behavior / Usage:**

Operation `t_test.perform` with `{"alpha", "tails", ...}` runs a one- or two-sample test. The tail mode `"tails"` is either `"one_tail"` or `"two_tail"`. Provide either `"population_mean"` plus `"sample"` for a one-sample test, or `"group_one"` plus `"group_two"` for a two-sample test. It returns a report as `key=value` lines: t_score, probability, p_value, alpha, the null/alternative decision, and the confidence level; a two-tailed p_value doubles the upper-tail probability. The test raises an error (printed as `error: <message>`) when the relevant standard deviation is zero. Operation `t_test.paired` with `{"alpha", "tails", "group_one", "group_two"}` compares two equal-length groups element-wise and additionally raises an error when the two groups are identical. Optional `"round"` controls printed precision.

**Test Cases:** `rcb_tests/public_test_cases/feature24_t_test.json`

```json
{
    "description": "Student's t-test. The one/two-sample test takes a significance level alpha, a tail mode (one_tail or two_tail) and either a comparison mean plus one sample, or two samples; it reports t_score, probability, p_value, alpha, the null/alternative decision and the confidence level. A two-tailed p_value doubles the upper-tail probability. The test refuses to run (raising an error) when the relevant standard deviation is zero. A paired variant compares two equally sized groups element-wise and additionally refuses to run when both groups are identical.",
    "cases": [
        {"input": {"op": "t_test.perform", "args": {"alpha": 0.05, "tails": "one_tail", "population_mean": 1.0, "sample": [1.0, 1.0, 1.0]}}, "expected_output": "error: Standard deviation for the difference or group is zero. Please, reconsider sample contents\n"},
        {"input": {"op": "t_test.perform", "args": {"alpha": 0.05, "tails": "one_tail", "population_mean": 4.7, "sample": [5, 5.5, 4.5, 5, 5, 6, 5, 5, 4.5, 5, 5, 4.5, 4.5, 5.5, 4, 5, 5, 5.5, 4.5, 5.5, 5, 5.5]}, "round": 6}, "expected_output": "t_score=3.039737\nprobability=0.996886\np_value=0.003114\nalpha=0.05\nnull=false\nalternative=true\nconfidence_level=0.95\n"},
        {"input": {"op": "t_test.perform", "args": {"alpha": 0.05, "tails": "two_tail", "group_one": [45, 38, 52, 48, 25, 39, 51, 46, 55, 46], "group_two": [34, 22, 15, 27, 37, 41, 24, 19, 26, 36]}, "round": 4}, "expected_output": "t_score=4.2575\nprobability=0.9998\np_value=0.0005\nalpha=0.05\nnull=false\nalternative=true\nconfidence_level=0.95\n"},
        {"input": {"op": "t_test.paired", "args": {"alpha": 0.05, "tails": "one_tail", "group_one": [1.0, 2.0], "group_two": [1.0, 2.0]}}, "expected_output": "error: both samples are the same\n"},
        {"input": {"op": "t_test.paired", "args": {"alpha": 0.05, "tails": "one_tail", "group_one": [1.0, 2.0, 3.0], "group_two": [2.0, 3.0, 4.0]}}, "expected_output": "error: Standard deviation for the difference or group is zero. Please, reconsider sample contents\n"},
        {"input": {"op": "t_test.paired", "args": {"alpha": 0.05, "tails": "one_tail", "group_one": [0.43, 0.266, 0.567, 0.531, 0.707, 0.716, 0.651, 0.589, 0.469, 0.723], "group_two": [0.415, 0.238, 0.39, 0.41, 0.605, 0.609, 0.632, 0.523, 0.411, 0.612]}, "round": 4}, "expected_output": "t_score=4.8638\nprobability=0.9996\np_value=0.0004\nalpha=0.05\nnull=false\nalternative=true\nconfidence_level=0.95\n"}
    ]
}
```

---

### Feature 25: Rank-sum (Mann-Whitney U) Test

**As a developer**, I want to compare two samples by rank, so I can decide if two groups differ without assuming normality.

**Expected Behavior / Usage:**

Operation `rank_sum.rank` with `{"data": [numbers]}` ranks a combined collection, returning per distinct value the occurrence count and the accumulated raw rank. Operation `rank_sum.test` with `{"alpha", "tails", "group_one", "group_two"}` (tail mode `"one_tail"` or `"two_tail"`) approximates the U statistic using the standard normal distribution and returns a report as `key=value` lines: probability, the U statistic, the z score, p_value, alpha, the null/alternative decision, and the confidence level. Optional `"round"` controls printed precision.

**Test Cases:** `rcb_tests/public_test_cases/feature25_rank_sum_test.json`

```json
{
    "description": "Rank-sum (Mann-Whitney U) test. The ranking step ranks a combined collection, returning per distinct value the occurrence count and the accumulated raw rank (tie ranks are resolved during the test by dividing the accumulated rank by the count). The test step takes a significance level alpha, a tail mode and two groups, approximating the U statistic with the standard normal distribution; it reports probability, the U statistic, the z score, p_value, alpha, the null/alternative decision and the confidence level.",
    "cases": [
        {"input": {"op": "rank_sum.rank", "args": {"data": [75, 32, 50, 38, 19, 44, 33, 102, 28, 70, 49, 70, 69, 99, 135, 115, 33, 92, 118, 115, 92, 89, 101]}}, "expected_output": "19={counter: 1, rank: 1}\n28={counter: 1, rank: 2}\n32={counter: 1, rank: 3}\n33={counter: 2, rank: 9}\n38={counter: 1, rank: 6}\n44={counter: 1, rank: 7}\n49={counter: 1, rank: 8}\n50={counter: 1, rank: 9}\n69={counter: 1, rank: 10}\n70={counter: 2, rank: 23}\n75={counter: 1, rank: 13}\n89={counter: 1, rank: 14}\n92={counter: 2, rank: 31}\n99={counter: 1, rank: 17}\n101={counter: 1, rank: 18}\n102={counter: 1, rank: 19}\n115={counter: 2, rank: 41}\n118={counter: 1, rank: 22}\n135={counter: 1, rank: 23}\n"},
        {"input": {"op": "rank_sum.test", "args": {"alpha": 0.05, "tails": "two_tail", "group_one": [3, 4, 2, 6, 2, 5], "group_two": [9, 7, 5, 10, 6, 8]}, "round": 4}, "expected_output": "probability=0.995\nu=2.0\nz=-2.5756\np_value=0.01\nalpha=0.05\nnull=false\nalternative=true\nconfidence_level=0.95\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON command from stdin and prints the result to stdout, matching the per-feature contracts above.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the string format of the 'format' key in the output_rule
