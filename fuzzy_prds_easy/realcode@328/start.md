## Product Requirement Document

# Nonlinear State Estimation Toolkit — Recursive Filters, State History and Geodetic Conversion

## Project Goal

Build a numerical state-estimation toolkit that lets developers fuse noisy, time-stamped sensor measurements into a single continuously-maintained estimate of a moving body's pose and motion, look that estimate up at any past or future instant, and convert between geographic and projected planar coordinates — all as pure numeric-in / numeric-out routines, without any dependency on a running middleware, message bus, or wall clock.

---

## Background & Problem

A body moving through space has a fifteen-element state: position (x, y, z), orientation as roll/pitch/yaw, the corresponding linear and angular velocities, and linear accelerations. Sensors report partial, noisy, time-stamped observations of this state. Turning a stream of such observations into one coherent, drift-bounded estimate requires a recursive predict/correct filter, careful bookkeeping of measurement priority and timing, a bounded history so earlier estimates can be recalled or interpolated, and — for outdoor navigation — a way to move between latitude/longitude and a flat metric grid.

Without a shared toolkit, every project re-derives the Kalman update equations, re-invents measurement queues, and hand-rolls geodetic math, producing subtly inconsistent and hard-to-test results. This toolkit specifies one well-defined numeric contract for each of those pieces: two recursive filters (an extended and an unscented variant) that share a common base, the base's measurement-record and parameter bookkeeping, a fixed-capacity state-history buffer with interpolation and extrapolation, and a latitude/longitude ↔ projected-grid converter. Every behavior is expressed purely as input values mapping to output values.

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
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types. The two filter variants MUST be interchangeable behind the shared filter abstraction.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

### Domain Conventions (shared by all features)

- **State vector.** A state is fifteen real numbers in this fixed order: `x, y, z, roll, pitch, yaw, vx, vy, vz, vroll, vpitch, vyaw, ax, ay, az`. Positions are meters, angles are radians, velocities and accelerations follow accordingly.
- **Covariance.** A fifteen-by-fifteen real matrix. In test inputs a covariance may be supplied compactly as `{"identity_scale": s}` (the identity scaled by `s`), `{"diagonal": [...15...]}` (a diagonal matrix), or `{"matrix": [[...], ...]}` (the full matrix).
- **Numeric output formatting.** State-vector and parameter values are printed with six digits after the decimal point. Covariance-diagonal values are printed in scientific notation with six digits after the decimal point. Negative zero is normalized to zero. Values are space-separated on a single line following their label.

---

## Core Features

### Feature 1: Extended Recursive Filter — Predict/Correct Fusion

**As a developer**, I want to fuse a time-ordered series of full-state measurements through an extended recursive filter, so I can maintain a single best estimate of a moving body's state.

**Expected Behavior / Usage:**

The request supplies an ordered list of `steps`. A `set_covariance` step overrides the current estimate-error covariance. A `process` step fuses a measurement consisting of a fifteen-element `measurement` vector, a measurement `covariance`, a per-element `update` mask (1 = the corresponding state element is observed by this measurement), and a `time`. The very first processed measurement *initializes* the estimate: each observed element of the state is set directly to the measured value, and the corresponding block of the estimate-error covariance is set to the measurement covariance. Every later measurement first advances (predicts) the estimate forward over the elapsed time from the previous measurement, then corrects it toward the new measurement weighted by the relative covariances; a measurement that is not strictly later in time skips the prediction. When the measurement covariance is extremely small, the corrected estimate is pulled almost exactly onto the measured values. The result reports the final state vector (`state:`) and the diagonal of the final estimate-error covariance (`covariance_diagonal:`).

**Test Cases:** `rcb_tests/public_test_cases/feature1_ekf_fusion.json`

```json
{
    "description": "Drive an extended-Kalman state estimator over an ordered sequence of steps. Each step either overrides the current estimate-error covariance or fuses a full state measurement carrying a measurement vector, a measurement covariance, a per-element update mask and a timestamp. The very first measurement initializes the estimate directly; later measurements advance the estimate forward to the measurement time and then correct it. The result is the final fifteen-element state vector and the diagonal of the final estimate-error covariance.",
    "cases": [
        {
            "input": {"action": "ekf_fusion", "args": [0.001, 0.0, 2.0], "steps": [{"action": "set_covariance", "covariance": {"identity_scale": 0.5}}, {"action": "process", "measurement": [0.0, 0.15, 0.3, 0.44999999999999996, 0.6, 0.75, 0.8999999999999999, 1.05, 1.2, 1.3499999999999999, 1.5, 1.65, 1.7999999999999998, 1.95, 2.1], "covariance": {"diagonal": [[a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value]]}, "update": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], "time": 1000.0}]},
            "expected_output": "state: 0.000000 0.150000 0.300000 0.450000 0.600000 0.750000 0.900000 1.050000 1.200000 1.350000 1.500000 1.650000 1.800000 1.950000 2.100000\ncovariance_diagonal: 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09\n"
        },
        {
            "input": {"action": "ekf_fusion", "args": [0.001, 0.0, 2.0], "steps": [{"action": "set_covariance", "covariance": {"identity_scale": 0.5}}, {"action": "process", "measurement": [0.0, 0.15, 0.3, 0.44999999999999996, 0.6, 0.75, 0.8999999999999999, 1.05, 1.2, 1.3499999999999999, 1.5, 1.65, 1.7999999999999998, 1.95, 2.1], "covariance": {"diagonal": [[a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value]]}, "update": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], "time": 1000.0}, {"action": "set_covariance", "covariance": {"identity_scale": 0.5}}, {"action": "process", "measurement": [0.0, 0.3, 0.6, 0.8999999999999999, 1.2, 1.5, 1.7999999999999998, 2.1, 2.4, 2.6999999999999997, 3.0, 3.3, 3.5999999999999996, 3.9, 4.2], "covariance": {"diagonal": [[a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value]]}, "update": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], "time": 1002.0}]},
            "expected_output": "state: 0.000000 0.300000 0.600000 0.900000 1.200000 1.500000 1.800000 2.100000 2.400000 2.700000 3.000000 3.300000 3.600000 3.900000 4.200000\ncovariance_diagonal: 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09\n"
        }
    ]
}
```

---

### Feature 2: Unscented Recursive Filter — Predict/Correct Fusion

**As a developer**, I want an alternative recursive filter that propagates uncertainty through a set of sampled points rather than a linearization, so I can fuse the same measurement streams with a filter better suited to strong nonlinearities while keeping an identical external contract.

**Expected Behavior / Usage:**

This filter accepts the same `steps`/`set_covariance`/`process` protocol and produces the same `state:` / `covariance_diagonal:` output shape as Feature 1; it is fully substitutable for the extended variant. It additionally takes three real tuning coefficients via `args` (the spread, secondary, and distribution parameters) that govern how the sampled points are placed and weighted. As with the extended variant, the first measurement initializes the estimate, later measurements predict-then-correct, and a near-zero measurement covariance pulls the estimate onto the measured values (to within the filter's numerical tolerance). The diagonal of the resulting estimate-error covariance reflects the prediction's added process uncertainty combined with the correction.

**Test Cases:** `rcb_tests/public_test_cases/feature2_ukf_fusion.json`

```json
{
    "description": "Drive an unscented-Kalman state estimator (parameterized by its spread, secondary and distribution coefficients) over an ordered sequence of steps. Each step either overrides the current estimate-error covariance or fuses a full state measurement carrying a measurement vector, a measurement covariance, a per-element update mask and a timestamp. The first measurement initializes the estimate; later measurements advance and correct it. The result is the final fifteen-element state vector and the diagonal of the final estimate-error covariance.",
    "cases": [
        {
            "input": {"action": "ukf_fusion", "args": [0.001, 0.0, 2.0], "steps": [{"action": "set_covariance", "covariance": {"identity_scale": 0.5}}, {"action": "process", "measurement": [0.0, 0.15, 0.3, 0.44999999999999996, 0.6, 0.75, 0.8999999999999999, 1.05, 1.2, 1.3499999999999999, 1.5, 1.65, 1.7999999999999998, 1.95, 2.1], "covariance": {"diagonal": [[a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value]]}, "update": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], "time": 1000.0}]},
            "expected_output": "state: 0.000000 0.150000 0.300000 0.450000 0.600000 0.750000 0.900000 1.050000 1.200000 1.350000 1.500000 1.650000 1.800000 1.950000 2.100000\ncovariance_diagonal: 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09 1.000000e-09\n"
        },
        {
            "input": {"action": "ukf_fusion", "args": [0.001, 0.0, 2.0], "steps": [{"action": "set_covariance", "covariance": {"identity_scale": 0.5}}, {"action": "process", "measurement": [0.0, 0.15, 0.3, 0.44999999999999996, 0.6, 0.75, 0.8999999999999999, 1.05, 1.2, 1.3499999999999999, 1.5, 1.65, 1.7999999999999998, 1.95, 2.1], "covariance": {"diagonal": [[a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value]]}, "update": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], "time": 1000.0}, {"action": "set_covariance", "covariance": {"identity_scale": 0.5}}, {"action": "process", "measurement": [0.0, 0.3, 0.6, 0.8999999999999999, 1.2, 1.5, 1.7999999999999998, 2.1, 2.4, 2.6999999999999997, 3.0, 3.3, 3.5999999999999996, 3.9, 4.2], "covariance": {"diagonal": [[a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value], [a specific covariance threshold value]]}, "update": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], "time": 1002.0}]},
            "expected_output": "state: 0.000000 0.300000 0.600000 0.899997 1.200000 1.499997 1.800000 2.100000 2.400000 2.700000 3.000000 3.300000 3.600000 3.900000 4.200000\ncovariance_diagonal: 1.000000e-01 1.000000e-01 1.200000e-01 6.000010e-02 6.000000e-02 1.200001e-01 5.000000e-02 5.000000e-02 8.000000e-02 2.000000e-02 2.000000e-02 4.000000e-02 2.000000e-02 2.000000e-02 3.000000e-02\n"
        }
    ]
}
```

---

### Feature 3: Shared Filter Base — Records, Parameters, and Initialization

**As a developer**, I want the bookkeeping that both filters share — measurement records and their ordering, parameter get/set round-trips, and first-measurement initialization — to be specified independently of any particular prediction math, so I can rely on consistent behavior across filter variants.

**Expected Behavior / Usage:**

*3.1 Measurement Record Defaults and Time Ordering — a value type plus a strict priority predicate*

A freshly constructed measurement record has an empty source name and a zero timestamp. The shared priority predicate compares two records by time: applied to an ordered pair `(a, b)` it reports whether `a` is *strictly newer* than `b` (i.e. `a.time > b.time`). For two records with equal time the predicate is negative in both directions. The request supplies `first_time` and `second_time`; the result reports the default source name, the default time, and the predicate evaluated as `(first, second)` and as `(second, first)`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_measurement_ordering.json`

```json
{
    "description": "Inspect the default field values of a freshly constructed measurement record and the strict ordering predicate used to prioritize measurements by time. A default record has an empty source name and a zero timestamp. The predicate, applied to an ordered pair, reports whether the first argument is strictly newer (later timestamp) than the second; equal timestamps yield a negative result in both directions.",
    "cases": [
        {
            "input": {"action": "measurement_ordering", "first_time": 100.0, "second_time": 200.0},
            "expected_output": "default_topic_name=\ndefault_time=0.000000\n[specific encoding for equidistant timestamps]\n[specific encoding for equidistant timestamps]\n"
        }
    ]
}
```

*3.2 Filter Parameter Get/Set Round-Trips — accessors common to every filter*

A newly constructed filter exposes get/set accessors that must round-trip the supplied values. A debug toggle only engages when a valid output stream is provided: requesting debug mode without a stream leaves it disabled, while requesting it with a valid stream enables it. The request supplies a `sensor_timeout`, a `last_measurement_time`, a `process_noise` covariance and a `state` vector. The result echoes both debug outcomes, the timeout, the last-measurement time, the diagonal of the process-noise covariance, the state vector, and the initialization status (a freshly constructed filter is not yet initialized).

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_filter_parameters.json`

```json
{
    "description": "Exercise the generic parameter accessors shared by every filter: a debug toggle that only engages when a valid output stream is supplied (and stays disabled otherwise), a sensor-timeout value, a last-measurement-time value, a process-noise covariance matrix and the state vector. After applying the requested values, each is read back. A newly constructed filter reports that it has not yet been initialized.",
    "cases": [
        {
            "input": {"action": "filter_parameters", "sensor_timeout": 7.4, "last_measurement_time": 3.83, "state": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "process_noise": {"matrix": [[0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0],[0.0,1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0,10.0,11.0,12.0,13.0,14.0],[0.0,2.0,4.0,6.0,8.0,10.0,12.0,14.0,16.0,18.0,20.0,22.0,24.0,26.0,28.0],[0.0,3.0,6.0,9.0,12.0,15.0,18.0,21.0,24.0,27.0,30.0,33.0,36.0,39.0,42.0],[0.0,4.0,8.0,12.0,16.0,20.0,24.0,28.0,32.0,36.0,40.0,44.0,48.0,52.0,56.0],[0.0,5.0,10.0,15.0,20.0,25.0,30.0,35.0,40.0,45.0,50.0,55.0,60.0,65.0,70.0],[0.0,6.0,12.0,18.0,24.0,30.0,36.0,42.0,48.0,54.0,60.0,66.0,72.0,78.0,84.0],[0.0,7.0,14.0,21.0,28.0,35.0,42.0,49.0,56.0,63.0,70.0,77.0,84.0,91.0,98.0],[0.0,8.0,16.0,24.0,32.0,40.0,48.0,56.0,64.0,72.0,80.0,88.0,96.0,104.0,112.0],[0.0,9.0,18.0,27.0,36.0,45.0,54.0,63.0,72.0,81.0,90.0,99.0,108.0,117.0,126.0],[0.0,10.0,20.0,30.0,40.0,50.0,60.0,70.0,80.0,90.0,100.0,110.0,120.0,130.0,140.0],[0.0,11.0,22.0,33.0,44.0,55.0,66.0,77.0,88.0,99.0,110.0,121.0,132.0,143.0,154.0],[0.0,12.0,24.0,36.0,48.0,60.0,72.0,84.0,96.0,108.0,120.0,132.0,144.0,156.0,168.0],[0.0,13.0,26.0,39.0,52.0,65.0,78.0,91.0,104.0,117.0,130.0,143.0,156.0,169.0,182.0],[0.0,14.0,28.0,42.0,56.0,70.0,84.0,98.0,112.0,126.0,140.0,154.0,168.0,182.0,196.0]]}},
            "expected_output": "debug_null_stream=false\ndebug_valid_stream=true\nsensor_timeout=7.400000\nlast_measurement_time=3.830000\nprocess_noise_diagonal: 0.000000 1.000000 4.000000 9.000000 16.000000 25.000000 36.000000 49.000000 64.000000 81.000000 100.000000 121.000000 144.000000 169.000000 196.000000\nstate: 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000\ninitialized=false\n"
        }
    ]
}
```

*3.3 First-Measurement Initialization and Time Tracking — the generic measurement-processing routine*

The shared measurement-processing routine, exercised with a filter whose prediction and correction do nothing, demonstrates the initialization behavior in isolation. Before any measurement the filter is uninitialized. Processing the first measurement initializes the state from the measured values that the update mask selects and marks the filter initialized. Processing further measurements (with this do-nothing filter, the state is unchanged) advances the recorded last-measurement time to the latest measurement's time. The result reports the initialization status before and after, the resulting state vector, and the last-measurement time.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_filter_initialization.json`

```json
{
    "description": "Feed an ordered sequence of full state measurements into the generic measurement-processing routine of a filter that performs no prediction or correction of its own. Before any measurement the filter is uninitialized. The first measurement initializes the state from the measured values that the update mask selects; subsequent measurements advance the last-measurement time. The result reports the initialization status before and after, the resulting state vector and the most recent measurement time.",
    "cases": [
        {
            "input": {"action": "filter_initialization", "steps": [{"measurement": [0.0, 0.1, 0.2, 0.30000000000000004, 0.4, 0.5, 0.6000000000000001, 0.7000000000000001, 0.8, 0.9, 1.0, 1.1, 1.2000000000000002, 1.3, 1.4000000000000001], "covariance": {"matrix": [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], [0.0, 0.1, 0.2, 0.30000000000000004, 0.4, 0.5, 0.6000000000000001, 0.7000000000000001, 0.8, 0.9, 1.0, 1.1, 1.2000000000000002, 1.3, 1.4000000000000001], [0.0, 0.2, 0.4, 0.6000000000000001, 0.8, 1.0, 1.2000000000000002, 1.4000000000000001, 1.6, 1.8, 2.0, 2.2, 2.4000000000000004, 2.6, 2.8000000000000003], [0.0, 0.30000000000000004, 0.6000000000000001, 0.9000000000000001, 1.2000000000000002, 1.5000000000000002, 1.8000000000000003, 2.1000000000000005, 2.4000000000000004, 2.7, 3.0000000000000004, 3.3000000000000007, 3.6000000000000005, 3.9000000000000004, 4.200000000000001], [0.0, 0.4, 0.8, 1.2000000000000002, 1.6, 2.0, 2.4000000000000004, 2.8000000000000003, 3.2, 3.6, 4.0, 4.4, 4.800000000000001, 5.2, 5.6000000000000005], [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0], [0.0, 0.6000000000000001, 1.2000000000000002, 1.8000000000000003, 2.4000000000000004, 3.0000000000000004, 3.6000000000000005, 4.200000000000001, 4.800000000000001, 5.4, 6.000000000000001, 6.600000000000001, 7.200000000000001, 7.800000000000001, 8.400000000000002], [0.0, 0.7000000000000001, 1.4000000000000001, 2.1, 2.8000000000000003, 3.5000000000000004, 4.2, 4.9, 5.6000000000000005, 6.300000000000001, 7.000000000000001, 7.700000000000001, 8.4, 9.100000000000001, 9.8], [0.0, 0.8, 1.6, 2.4000000000000004, 3.2, 4.0, 4.800000000000001, 5.6000000000000005, 6.4, 7.2, 8.0, 8.8, 9.600000000000001, 10.4, 11.200000000000001], [0.0, 0.9, 1.8, 2.7, 3.6, 4.5, 5.4, 6.3, 7.2, 8.1, 9.0, 9.9, 10.8, 11.700000000000001, 12.6], [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0], [0.0, 1.1, 2.2, 3.3000000000000003, 4.4, 5.5, 6.6000000000000005, 7.700000000000001, 8.8, 9.9, 11.0, 12.100000000000001, 13.200000000000001, 14.3, 15.400000000000002], [0.0, 1.2000000000000002, 2.4000000000000004, 3.6000000000000005, 4.800000000000001, 6.000000000000001, 7.200000000000001, 8.400000000000002, 9.600000000000001, 10.8, 12.000000000000002, 13.200000000000003, 14.400000000000002, 15.600000000000001, 16.800000000000004], [0.0, 1.3, 2.6, 3.9000000000000004, 5.2, 6.5, 7.800000000000001, 9.1, 10.4, 11.700000000000001, 13.0, 14.3, 15.600000000000001, 16.900000000000002, 18.2], [0.0, 1.4000000000000001, 2.8000000000000003, 4.2, 5.6000000000000005, 7.000000000000001, 8.4, 9.8, 11.200000000000001, 12.600000000000001, 14.000000000000002, 15.400000000000002, 16.8, 18.200000000000003, 19.6]]}, "update": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], "time": 1000.0}, {"measurement": [0.0, 0.1, 0.2, 0.30000000000000004, 0.4, 0.5, 0.6000000000000001, 0.7000000000000001, 0.8, 0.9, 1.0, 1.1, 1.2000000000000002, 1.3, 1.4000000000000001], "covariance": {"matrix": [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], [0.0, 0.1, 0.2, 0.30000000000000004, 0.4, 0.5, 0.6000000000000001, 0.7000000000000001, 0.8, 0.9, 1.0, 1.1, 1.2000000000000002, 1.3, 1.4000000000000001], [0.0, 0.2, 0.4, 0.6000000000000001, 0.8, 1.0, 1.2000000000000002, 1.4000000000000001, 1.6, 1.8, 2.0, 2.2, 2.4000000000000004, 2.6, 2.8000000000000003], [0.0, 0.30000000000000004, 0.6000000000000001, 0.9000000000000001, 1.2000000000000002, 1.5000000000000002, 1.8000000000000003, 2.1000000000000005, 2.4000000000000004, 2.7, 3.0000000000000004, 3.3000000000000007, 3.6000000000000005, 3.9000000000000004, 4.200000000000001], [0.0, 0.4, 0.8, 1.2000000000000002, 1.6, 2.0, 2.4000000000000004, 2.8000000000000003, 3.2, 3.6, 4.0, 4.4, 4.800000000000001, 5.2, 5.6000000000000005], [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0], [0.0, 0.6000000000000001, 1.2000000000000002, 1.8000000000000003, 2.4000000000000004, 3.0000000000000004, 3.6000000000000005, 4.200000000000001, 4.800000000000001, 5.4, 6.000000000000001, 6.600000000000001, 7.200000000000001, 7.800000000000001, 8.400000000000002], [0.0, 0.7000000000000001, 1.4000000000000001, 2.1, 2.8000000000000003, 3.5000000000000004, 4.2, 4.9, 5.6000000000000005, 6.300000000000001, 7.000000000000001, 7.700000000000001, 8.4, 9.100000000000001, 9.8], [0.0, 0.8, 1.6, 2.4000000000000004, 3.2, 4.0, 4.800000000000001, 5.6000000000000005, 6.4, 7.2, 8.0, 8.8, 9.600000000000001, 10.4, 11.200000000000001], [0.0, 0.9, 1.8, 2.7, 3.6, 4.5, 5.4, 6.3, 7.2, 8.1, 9.0, 9.9, 10.8, 11.700000000000001, 12.6], [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0], [0.0, 1.1, 2.2, 3.3000000000000003, 4.4, 5.5, 6.6000000000000005, 7.700000000000001, 8.8, 9.9, 11.0, 12.100000000000001, 13.200000000000001, 14.3, 15.400000000000002], [0.0, 1.2000000000000002, 2.4000000000000004, 3.6000000000000005, 4.800000000000001, 6.000000000000001, 7.200000000000001, 8.400000000000002, 9.600000000000001, 10.8, 12.000000000000002, 13.200000000000003, 14.400000000000002, 15.600000000000001, 16.800000000000004], [0.0, 1.3, 2.6, 3.9000000000000004, 5.2, 6.5, 7.800000000000001, 9.1, 10.4, 11.700000000000001, 13.0, 14.3, 15.600000000000001, 16.900000000000002, 18.2], [0.0, 1.4000000000000001, 2.8000000000000003, 4.2, 5.6000000000000005, 7.000000000000001, 8.4, 9.8, 11.200000000000001, 12.600000000000001, 14.000000000000002, 15.400000000000002, 16.8, 18.200000000000003, 19.6]]}, "update": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], "time": 1002.0}]},
            "expected_output": "initialized_before=false\ninitialized_after=true\nstate: 0.000000 0.100000 0.200000 0.300000 0.400000 0.500000 0.600000 0.700000 0.800000 0.900000 1.000000 1.100000 1.200000 1.300000 1.400000\nlast_measurement_time=1002.000000\n"
        }
    ]
}
```

---

### Feature 4: Geographic ↔ Projected-Grid Conversion

**As a developer**, I want to convert a latitude/longitude coordinate to a planar metric grid coordinate and back, so I can fuse satellite-positioning fixes into the same Cartesian state the filters estimate.

**Expected Behavior / Usage:**

The request supplies a geographic coordinate as `lat` and `lon` in fractional degrees (north and east positive). The coordinate is projected to a transverse-Mercator grid yielding a `northing`, an `easting`, and a grid-zone designator (a zone number followed by a latitude-band letter). That projected coordinate is then converted back to latitude and longitude, recovering the input. The result reports the northing and easting (two decimal places, meters), the grid-zone designator, and the round-tripped latitude and longitude (five decimal places, degrees).

**Test Cases:** `rcb_tests/public_test_cases/feature4_geo_utm.json`

```json
{
    "description": "Convert a geographic coordinate given as latitude and longitude in fractional degrees into its projected grid coordinate (northing, easting and grid-zone designator), then convert that projected coordinate back to latitude and longitude. North latitudes and east longitudes are positive. The result reports the projected northing and easting, the grid-zone designator and the round-tripped latitude and longitude.",
    "cases": [
        {
            "input": {"action": "geo_utm", "lat": 51.423964, "lon": 5.494271},
            "expected_output": "[standard UTM coordinate extraction fields]5699924.71\n[standard UTM coordinate extraction fields]673409.99\n[standard UTM coordinate extraction fields]31U\n[standard UTM coordinate extraction fields]51.42396\n[standard UTM coordinate extraction fields]5.49427\n"
        }
    ]
}
```

---

### Feature 5: Fixed-Capacity State History Buffer

**As a developer**, I want to keep a bounded, time-ordered history of estimator states and recall the state at any requested instant — exactly when stored, or by interpolation/extrapolation otherwise — so I can answer queries about where the body was or will be.

**Expected Behavior / Usage:**

The buffer is created with a `buffer_capacity`, an underlying filter kind (`ekf` or `ukf`) used as the motion model for extrapolation, and a process-noise scale. A `set_state` operation inserts a state (a timestamp plus a fifteen-element vector) or overwrites the entry already at that timestamp; once more than `capacity` distinct timestamps are present, the oldest is dropped. `clear` empties the buffer; `size` reports how many entries it currently holds. A `get_state` operation at a requested time returns a result category and a state vector:
- `exact` — the requested time matches a stored entry; the stored vector is returned.
- `interpolation` — the requested time lies between two stored entries; the vector is interpolated.
- `extrapolation_past` — the requested time is older than the earliest stored entry; the earliest entry is projected backward via the motion model.
- `extrapolation_future` — the requested time is newer than the latest stored entry; the latest entry is projected forward via the motion model.

Each `size` prints `size=<n>`; each `get_state` prints a `result=<category>` line followed by a `state:` line. For a body moving at constant unit velocity along one axis, interpolation and forward/backward extrapolation reproduce the designed position at the requested time.

**Test Cases:** `rcb_tests/public_test_cases/feature5_state_buffer.json`

```json
{
    "description": "Maintain a fixed-capacity, time-ordered history buffer of estimator states and query it at arbitrary times. Setting a state inserts or overwrites the entry at its timestamp; once capacity is exceeded the oldest entry is dropped. The buffer can be cleared and its current size reported. A query returns a result category — an exact hit, an interpolation between two stored states, or an extrapolation into the past or the future relative to the stored range — together with the resulting state vector at the requested time.",
    "cases": [
        {
            "input": {"action": "state_buffer", "buffer_capacity": 5, "filter": "ekf", "process_noise_identity": 1.0, "operations": [{"op": "set_state", "time": 0.0, "state": [0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}, {"op": "set_state", "time": 1.0, "state": [1, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}, {"op": "set_state", "time": 2.0, "state": [2, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}, {"op": "set_state", "time": 3.0, "state": [3, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}, {"op": "set_state", "time": 4.0, "state": [4, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}, {"op": "set_state", "time": 5.0, "state": [5, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}, {"op": "size"}, {"op": "clear"}, {"op": "size"}, {"op": "set_state", "time": 1.0, "state": [1, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}, {"op": "set_state", "time": 2.0, "state": [2, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}, {"op": "set_state", "time": 3.0, "state": [3, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}, {"op": "set_state", "time": 0.0, "state": [0.0, 12.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}, {"op": "get_state", "time": 0.0}, {"op": "set_state", "time": 5.0, "state": [5, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}, {"op": "set_state", "time": 6.0, "state": [6, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}, {"op": "set_state", "time": 7.0, "state": [7, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}, {"op": "get_state", "time": 0.0}, {"op": "get_state", "time": 4.0}, {"op": "get_state", "time": 8.0}]},
            "expected_output": "size=5\nsize=0\nresult=exact\nstate: 0.000000 12.000000 0.000000 0.000000 0.000000 0.000000 1.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000\nresult=extrapolation_past\nstate: 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 1.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000\nresult=interpolation\nstate: 4.000000 0.000000 0.000000 0.000000 0.000000 0.000000 1.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000\nresult=extrapolation_future\nstate: 8.000000 0.000000 0.000000 0.000000 0.000000 0.000000 1.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above — two interchangeable recursive filters over a shared base, the base's measurement-record/parameter bookkeeping and initialization, a fixed-capacity state-history buffer, and a geographic/projected-grid converter. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint, and the core math MUST be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resulting values to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `ekf_fusion` / `ukf_fusion` drive the respective filters over `steps`; `measurement_ordering`, `filter_parameters`, and `filter_initialization` exercise the shared base; `geo_utm` performs the coordinate round-trip; `state_buffer` replays a list of buffer `operations`. Numbers are rendered at the fixed precision described under "Domain Conventions" and per-feature.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow 'update' mask semantics defined in the utility module
- adhere to the 'exact' retrieval protocol in state_manager.py
