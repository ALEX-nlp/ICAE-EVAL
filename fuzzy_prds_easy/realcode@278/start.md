## Product Requirement Document

# Load Rate Engine — Deterministic Traffic Shaping for Load Tests

## Project Goal

Build a load rate engine that lets developers describe *how much traffic to generate over time* — as constant rates, ramps, multi-stage schedules, or bell-curve (Gaussian) volume profiles — and turns those descriptions into a precise, deterministic, per-tick count of how many iterations to start at each moment. This lets a load-testing tool drive a target throughput shape without anyone hand-writing scheduling loops, fractional-rate accounting, or smoothing logic.

---

## Background & Problem

Without this engine, developers writing load tests are forced to manually translate human intentions ("ramp from 0 to 10 requests per second over 10 seconds", "peak at 1400 requests/second around 2pm", "hold 6/s for 5 seconds then stop") into imperative timer loops. This leads to repetitive, error-prone boilerplate: integer rates do not divide evenly across sub-intervals, so naive loops either overshoot or undershoot the requested volume; ramps and bell curves require interpolation math; and a config-file format for non-programmers has to be parsed and validated by hand.

With this engine, a developer supplies a compact specification (a rate string, a stage list, or a YAML config) and receives a *rate function*: given any point in time it returns an exact non-negative integer count of iterations to launch, such that the totals over each interval match the requested shape. The engine guarantees that fractional remainders are carried forward so that, over a full interval, the emitted counts sum exactly to the requested rate, and it smooths bursts across fixed 100ms sub-ticks so load is spread evenly (or pseudo-randomly) rather than fired all at once.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility domain (rate-string parsing, schedule interpolation, sub-tick smoothing, statistical volume calculation, config-file parsing/validation). It MUST NOT be a single "god file". Provide a clear, multi-file directory tree separating the core domain from the execution adapter and the tests. Do not over-engineer, but do reflect the real feature surface.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract for the execution adapter**, NOT the internal data model. The core engine must be expressed in idiomatic in-language types (durations, rate functions, value objects) and must remain completely decoupled from stdin/stdout and JSON parsing. A thin adapter is solely responsible for translating JSON commands into core calls and rendering results.

3. **Adherence to SOLID Design Principles:**
   - **SRP:** Separate rate-string parsing, stage interpolation, distribution smoothing, volume calculation, config parsing/validation, and output formatting into distinct units.
   - **OCP:** New distribution strategies and new stage modes must be addable without modifying existing strategies.
   - **LSP:** All stage modes must be substitutable behind a common "produces a rate function" abstraction.
   - **ISP:** Keep the rate-function abstraction minimal (time → integer count).
   - **DIP:** High-level scheduling depends on the rate-function abstraction, not on concrete parsers or I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public core API must be elegant and hide internal accounting (remainders, sub-tick counters).
   - **Resilience:** Invalid inputs (bad rate strings, malformed schedules, incomplete configs) must be modeled as explicit, typed error outcomes rather than crashes, and surfaced through the adapter as the normalized error contract shown below.

---

## Core Features

### Feature 1: Stage Schedule Parsing

**As a developer**, I want to write a load schedule as a short comma-separated string of `<stage_duration>:<target>` segments, so I can express a multi-step concurrency plan without building objects by hand.

**Expected Behavior / Usage:**

The input is a single string containing one or more comma-separated segments. Each segment has the form `<duration>:<target>`, where `<duration>` is a time span (e.g. `0s`, `10s`, `1m`, `1h`) and `<target>` is a non-negative integer target. Surrounding whitespace within a segment is ignored. The output is the ordered list of parsed stages; for each stage the engine emits its index, the normalized duration (rendered as a compact span such as `10s`, `1m0s`, `1h0m0s`), and its target. The parser does not assign start targets at this layer — every parsed stage reports only its own duration and end target. Malformed input is rejected with a normalized error category and the offending stage string echoed back: a segment that does not split into exactly two colon-separated parts yields `invalid_stage_format`; an unparseable duration yields `invalid_duration`; an unparseable target yields `invalid_target`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_schedule_parsing.json`

```json
{
    "description": "Parse a comma-separated load schedule string of <stage_duration>:<target> segments into an ordered list of stages, each carrying its normalized duration and target concurrency; malformed segments are rejected with a normalized error category.",
    "cases": [
        {
            "input": {
                "op": "parse_schedule",
                "stages": "0s:1,10s:1,20s:20,1m:50,1h:200"
            },
            "expected_output": "stage=0 duration=0s target=1\nstage=1 duration=10s target=1\nstage=2 duration=20s target=20\nstage=3 duration=1m0s target=50\nstage=4 duration=1h0m0s target=200\n"
        },
        {
            "input": {
                "op": "parse_schedule",
                "stages": "1s:BB"
            },
            "expected_output": "error=invalid_target\nstages=1s:BB\n"
        }
    ]
}
```

---

### Feature 2: Staged Rate Interpolation

**As a developer**, I want the engine to compute the instantaneous target rate at any elapsed time across a multi-stage schedule, so the running load smoothly transitions between stages.

**Expected Behavior / Usage:**

The input is an ordered schedule (each entry a target `end` value and a `duration`) plus an optional `start_offset` expressing how long ago the schedule began (e.g. `-2m` means the schedule started two minutes ago). The engine treats each stage as a linear ramp from the previous stage's end target (the very first stage starts at 0) to its own end target over its duration, and returns the single interpolated integer rate for the current moment. Behavior at the boundaries: when no start offset is supplied the schedule is considered to begin now, so the rate is `0` (the start of the first ramp); when the elapsed time lands inside a stage, the rate is the linear interpolation for that position; when the elapsed time is past the total duration of all stages, the rate is `0`. The output is a single `rate=<n>` line.

**Test Cases:** `rcb_tests/public_test_cases/feature2_staged_rate.json`

```json
{
    "description": "Compute the instantaneous target rate for a multi-stage schedule given an elapsed-time offset, linearly interpolating within the active stage; before the schedule starts the rate is zero, and past the final stage the rate is zero.",
    "cases": [
        {
            "input": {
                "op": "staged_rate",
                "schedule": [
                    {"end": 10, "duration": "1m"},
                    {"end": 10, "duration": "10m"}
                ],
                "start_offset": "-2m"
            },
            "expected_output": "rate=10\n"
        },
        {
            "input": {
                "op": "staged_rate",
                "schedule": [
                    {"end": 1, "duration": "1m"},
                    {"end": 10, "duration": "10m"}
                ]
            },
            "expected_output": "rate=0\n"
        }
    ]
}
```

---

### Feature 3: Load Distribution Smoothing

**As a developer**, I want a per-interval target rate to be spread across fixed 100ms sub-ticks instead of fired in a single burst, so generated traffic is evenly (or randomly) distributed within each interval while still summing exactly to the requested rate.

**Expected Behavior / Usage:**

Each request supplies an interval length (`iteration_duration`), a number of sub-ticks to observe (`ticks`), and a per-interval target rate — either a single `rate` (held constant) or a `rates` sequence consumed one value per full interval. The engine returns the effective sub-tick interval and the integer count emitted at each observed sub-tick. The effective sub-tick interval is `100ms` whenever the requested interval is larger than `100ms`; if the interval is at or below `100ms`, smoothing is bypassed and the full rate is returned on a single tick at the original interval. Output is two lines: `iteration_duration=<effective interval>` followed by `rates=<space-separated counts>`.

*3.1 Regular (even) distribution — spreads the rate as uniformly as possible across sub-ticks*

For an interval split into N sub-ticks (N = interval / 100ms), the per-interval rate is accumulated at `rate/N` per sub-tick; whenever the running accumulator reaches at least 1, that whole part is emitted and carried-down, so low rates produce occasional `1`s spaced out across the interval and high rates produce a balanced pattern. The emitted counts over each full interval sum exactly to that interval's rate. When a `rates` sequence is supplied, each successive interval pulls the next value from the sequence.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_regular_distribution.json`

```json
{
    "description": "Smooth a per-interval target rate evenly across fixed 100ms sub-ticks so the integer counts emitted over each interval sum to the requested rate; when the interval is at or below the sub-tick size the rate passes through unchanged. A sequence of per-interval rates is consumed one value per full interval.",
    "cases": [
        {
            "input": {"op": "distribute_load", "distribution": "regular", "iteration_duration": "1s", "rate": 7, "ticks": 10},
            "expected_output": "iteration_duration=100ms\nrates=0 1 1 0 1 1 0 1 1 1\n"
        },
        {
            "input": {"op": "distribute_load", "distribution": "regular", "iteration_duration": "1s", "rate": 15, "ticks": 10},
            "expected_output": "iteration_duration=100ms\nrates=1 2 1 2 1 2 1 2 1 2\n"
        },
        {
            "input": {"op": "distribute_load", "distribution": "regular", "iteration_duration": "10ms", "rate": 10000, "ticks": 1},
            "expected_output": "iteration_duration=10ms\nrates=10000\n"
        }
    ]
}
```

*3.2 Random distribution — spreads the rate with a pseudo-random draw per sub-tick*

The interval is split into N sub-ticks. On each sub-tick (except the last) the engine draws how many of the remaining budget to emit using an externally supplied draw sequence, clamping a draw to whatever budget remains; the final sub-tick emits whatever budget is left, so the counts over each full interval still sum exactly to the requested rate. The `random_values` array provides the deterministic draw sequence (each value is the result of a draw against the current remaining budget), making outputs reproducible.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_random_distribution.json`

```json
{
    "description": "Smooth a per-interval target rate across fixed 100ms sub-ticks by randomly drawing how many to emit on each sub-tick from the remaining budget, with the final sub-tick receiving whatever remains so the interval total is exactly the requested rate. The draw sequence is supplied deterministically.",
    "cases": [
        {
            "input": {"op": "distribute_load", "distribution": "random", "iteration_duration": "1s", "rate": 28, "random_values": [0, 1, 0, 0, 1, 0, 0, 0, 7], "ticks": 10},
            "expected_output": "iteration_duration=100ms\nrates=0 1 0 0 1 0 0 0 7 19\n"
        },
        {
            "input": {"op": "distribute_load", "distribution": "random", "iteration_duration": "1s", "rate": 1, "random_values": [1], "ticks": 10},
            "expected_output": "iteration_duration=100ms\nrates=1 0 0 0 0 0 0 0 0 0\n"
        }
    ]
}
```

---

### Feature 4: Peak Rate to Volume Conversion

**As a developer**, I want to specify a desired *peak rate* for a bell-curve load profile and have the engine compute the total volume that profile implies over a day, so I can think in terms of "what peak throughput do I want" instead of "what total count".

**Expected Behavior / Usage:**

The input is a peak rate string (`<count>/<unit>`, e.g. `1400/s`, `100/10s`, `1/h`; a bare number means per second), a `peak_time` offset (where the bell curve peaks), and a `stddev` (standard deviation of the bell curve). The engine interprets the rate as the desired peak amplitude in requests-per-second, integrates a normal distribution with the given peak offset and standard deviation across a 24-hour window, and returns the implied total volume as a single rounded integer: `volume=<n>`. Invalid rate strings are rejected with `invalid_rate`, and negative rates with `negative_rate`, echoing the offending rate string.

**Test Cases:** `rcb_tests/public_test_cases/feature4_peak_volume.json`

```json
{
    "description": "Convert a desired peak rate (requests per time unit) at a given peak offset, together with a standard deviation, into the total volume of a Gaussian load profile over a 24h window; unparseable or negative rates are rejected with a normalized error category.",
    "cases": [
        {"input": {"op": "peak_to_volume", "peak_rate": "1400/s", "peak_time": "14h", "stddev": "4h"}, "expected_output": "volume=50208044\n"},
        {"input": {"op": "peak_to_volume", "peak_rate": "100/10s", "peak_time": "14h", "stddev": "4h"}, "expected_output": "volume=358629\n"},
        {"input": {"op": "peak_to_volume", "peak_rate": "1/h", "peak_time": "14h", "stddev": "4h"}, "expected_output": "volume=10\n"},
        {"input": {"op": "peak_to_volume", "peak_rate": "ms", "peak_time": "14h", "stddev": "4h"}, "expected_output": "error=invalid_rate\nrate=ms\n"},
        {"input": {"op": "peak_to_volume", "peak_rate": "-10/s", "peak_time": "14h", "stddev": "4h"}, "expected_output": "error=negative_rate\nrate=-10/s\n"}
    ]
}
```

---

### Feature 5: Config-File Load Schedule

**As a developer**, I want to describe a complete load test in a YAML config file — global limits plus an ordered list of stages, each in one of several modes — and have the engine produce a runnable schedule with a per-interval rate series, so non-programmers can define and tweak load shapes without code.

**Expected Behavior / Usage:**

The input is the raw YAML `content` plus a reference timestamp `now` (used to skip already-elapsed scheduled stages) and a `samples` count (how many successive intervals of the first stage's rate series to emit; `0` means emit none). The engine parses and validates the config, then exposes the global limits and the resolved first stage.

*5.1 Single-stage modes — resolve and run each supported stage mode*

A config has a `limits` block (`max-duration`, `concurrency`, `max-iterations`, `ignore-dropped`, all required) and a `stages` list (at least one). A `default` block may supply values inherited by stages that omit them. Each stage declares a `duration`, a `mode`, optional `parameters`, and mode-specific fields:
- `constant` — a fixed `rate` (e.g. `6/s`); the rate series is that rate every interval.
- `ramp` — `start-rate` and `end-rate`; the rate series linearly interpolates between them across the stage.
- `staged` — an embedded `stages` schedule string and `iteration-frequency`; the rate series follows the interpolated multi-stage shape.
- `gaussian` — `volume`, `repeat`, `iteration-frequency`, `peak`, `weights`, `standard-deviation`; the rate series follows a repeating bell curve achieving the requested volume per repeat window.
- `users` — a fixed user `concurrency` with no rate series.

When a `schedule.stage-start` timestamp is given, stages that would have completely finished before `now` are skipped, so only the still-active tail of the schedule is returned. The output reports `scenario`, `max_duration`, `concurrency`, `max_iterations`, `ignore_dropped`, the number of resolved stages, and for the first stage its `duration`, effective per-interval `iteration_duration`, `users_concurrency`, sorted `params`, and (when `samples > 0`) the sampled `rates` series. Durations are rendered as compact spans (e.g. `1m0s`, `5s`, `0s`).

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_config_modes.json`

```json
{
    "description": "Parse a YAML load-test config into a runnable schedule, exposing global limits (scenario, max-duration, concurrency, max-iterations, ignore-dropped), the resolved per-stage duration/iteration window/user concurrency/parameters, and the sampled per-interval rate series for each supported stage mode (constant, ramp, staged, gaussian, users), including default-value inheritance and skipping of already-elapsed scheduled stages.",
    "cases": [
        {
            "input": {
                "op": "config_schedule",
                "now": "2020-12-10T10:00:00+00:00",
                "samples": 6,
                "content": "\nscenario: template\nlimits:\n  max-duration: 1m\n  concurrency: 50\n  max-iterations: 100\n  ignore-dropped: true\nstages:\n- duration: 5s\n  mode: constant\n  rate: 6/s\n  jitter: 0\n  distribution: none\n  parameters:\n    FOO: bar\n"
            },
            "expected_output": "scenario=template\nmax_duration=1m0s\nconcurrency=50\nmax_iterations=100\nignore_dropped=true\nstages=1\nstage=0 duration=5s iteration_duration=1s users_concurrency=0\nparams=FOO=bar\nrates=6 6 6 6 6 6\n"
        },
        {
            "input": {
                "op": "config_schedule",
                "now": "2020-12-10T10:00:00+00:00",
                "samples": 10,
                "content": "\nscenario: template\nlimits:\n  max-duration: 1m\n  concurrency: 50\n  max-iterations: 100\n  ignore-dropped: true\nstages:\n- duration: 10s\n  mode: ramp\n  start-rate: 0/s\n  end-rate: 10/s\n  jitter: 0\n  distribution: none\n  parameters:\n    FOO: bar\n"
            },
            "expected_output": "scenario=template\nmax_duration=1m0s\nconcurrency=50\nmax_iterations=100\nignore_dropped=true\nstages=1\nstage=0 duration=10s iteration_duration=1s users_concurrency=0\nparams=FOO=bar\nrates=0 1 2 3 4 5 6 7 8 9\n"
        },
        {
            "input": {
                "op": "config_schedule",
                "now": "2020-12-10T10:00:00+00:00",
                "samples": 60,
                "content": "\nscenario: template\nlimits:\n  max-duration: 1m\n  concurrency: 50\n  max-iterations: 100\n  ignore-dropped: true\nstages:\n- duration: 10s\n  mode: gaussian\n  volume: 100\n  repeat: 20s\n  iteration-frequency: 1s\n  peak: 10s\n  weights: \"1.0,1.0\"\n  standard-deviation: 3s\n  jitter: 0\n  distribution: none\n  parameters:\n    FOO: bar\n"
            },
            "expected_output": "scenario=template\nmax_duration=1m0s\nconcurrency=50\nmax_iterations=100\nignore_dropped=true\nstages=1\nstage=0 duration=10s iteration_duration=1s users_concurrency=0\nparams=FOO=bar\nrates=0 0 1 2 3 6 8 10 13 13 13 10 9 5 3 2 1 0 1 0 0 0 1 2 3 6 8 10 13 13 13 11 8 5 3 2 1 0 1 0 0 0 1 2 3 6 8 10 13 13 13 11 8 5 3 2 1 1 0 0\n"
        },
        {
            "input": {
                "op": "config_schedule",
                "now": "2020-12-10T10:00:00+00:00",
                "samples": 0,
                "content": "\nscenario: template\nlimits:\n  max-duration: 1m\n  concurrency: 50\n  max-iterations: 100\n  ignore-dropped: true\nstages:\n- duration: 10s\n  mode: users\n  concurrency: 100\n  parameters:\n    FOO: bar\n"
            },
            "expected_output": "scenario=template\nmax_duration=1m0s\nconcurrency=50\nmax_iterations=100\nignore_dropped=true\nstages=1\nstage=0 duration=10s iteration_duration=0s users_concurrency=100\nparams=FOO=bar\n"
        }
    ]
}
```

*5.2 Config validation errors — reject incomplete or malformed configs*

If a required global field (`scenario`, `max-duration`, `concurrency`, `max-iterations`, `ignore-dropped`) is missing, or the `stages` list is empty, or a stage omits a field required by its mode (e.g. a `constant` stage without `rate`, a `ramp` stage without `start-rate`/`end-rate`, a `staged` stage without `stages`/`iteration-frequency`, a `gaussian` stage without `volume`/`repeat`/`iteration-frequency`), or a stage omits its `mode`, the config is rejected. Structurally malformed YAML is also rejected. Every rejection is reported as `error=invalid_config` followed by a `reason=` line: a normalized `malformed_yaml` for unparseable YAML, otherwise the domain reason for the missing field (e.g. `missing scenario`, `missing rate at stage 0`, `missing stage mode at stage 0`).

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_config_errors.json`

```json
{
    "description": "Reject invalid YAML load-test configs with a normalized error category and a domain reason: missing required global fields, missing mode-specific fields per stage, missing stage mode, and structurally malformed YAML.",
    "cases": [
        {
            "input": {"op": "config_schedule", "now": "2020-12-10T10:00:00+00:00", "content": "limits:\n  max-duration: 1m\n  concurrency: 50\n  max-iterations: 100\n  ignore-dropped: true\n"},
            "expected_output": "error=invalid_config\nreason=missing scenario\n"
        },
        {
            "input": {"op": "config_schedule", "now": "2020-12-10T10:00:00+00:00", "content": "scenario: template\nlimits:\n  max-duration: 1m\n  concurrency: 50\n  max-iterations: 100\n  ignore-dropped: true\nstages:\n- duration: 1h\n  mode: constant\n"},
            "expected_output": "error=invalid_config\nreason=missing rate at stage 0\n"
        },
        {
            "input": {"op": "config_schedule", "now": "2020-12-10T10:00:00+00:00", "content": "scenario: template\nlimits:\n  max-duration: 1m\n  concurrency: 50\n  max-iterations: 100\n  ignore-dropped: true\nstages:\n- duration: 10s\n"},
            "expected_output": "error=invalid_config\nreason=missing stage mode at stage 0\n"
        },
        {
            "input": {"op": "config_schedule", "now": "2020-12-10T10:00:00+00:00", "content": "\ninvalid file content\n"},
            "expected_output": "error=invalid_config\nreason=malformed_yaml\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the rate-string parsing, staged interpolation, distribution smoothing, peak-to-volume calculation, and config parsing/validation features described above, with the core domain fully decoupled from I/O.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above (including the normalized error categories). This adapter must be logically and physically separate from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_schedule_parsing.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_schedule_parsing@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- include stage indices starting from the standard zero-based convention seen elsewhere
