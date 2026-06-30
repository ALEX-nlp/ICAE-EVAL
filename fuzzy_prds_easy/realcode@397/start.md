## Product Requirement Document

# Spectroscopy Analysis Toolkit - 1D Spectrum Measurement & Region Manipulation

## Project Goal

Build a library for analysing one-dimensional spectra — sequences of flux measurements indexed by a physical spectral axis (wavelength, frequency, energy, or pixel) — that lets developers measure line properties, fit continua, and manipulate spectral regions without re-implementing unit-aware numerical analysis by hand.

---

## Background & Problem

Without this library, developers working with spectroscopic data are forced to hand-roll flux integration, moment calculations, signal-to-noise estimation, and region bookkeeping, while also manually tracking the physical units attached to every axis and flux array. This leads to repetitive, error-prone boilerplate and subtle unit mistakes.

With this library, a spectrum is a first-class object that pairs a flux array with a unit-carrying spectral axis (and optional per-sample uncertainty and mask). Analysis functions consume such an object and return unit-carrying scalar results; region objects describe intervals on the spectral axis and support set-like manipulation.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has multiple distinct responsibilities (spectrum model, unit handling, per-measurement analysis routines, continuum fitting, region algebra, masking). It MUST NOT be a single "god file"; output a clear, multi-file directory tree (`src/`, `tests/`, etc.) reflecting a production-grade repository. Do not over-engineer, but strictly avoid monolithic files.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below represent a **black-box testing contract** for the execution adapter, NOT the internal data model. The core analysis logic must remain decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls to the core domain and rendering results.

3. **Adherence to SOLID Design Principles:** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units; keep the core open for extension but closed for modification; keep interfaces small and cohesive; depend on abstractions rather than I/O details.

4. **Robustness & Interface Design:** The public interface must be elegant and idiomatic to the target language, hiding internal complexity. Edge cases must be handled gracefully and errors modelled with specific error types rather than generic faults.

---

## Core Features

### Feature 1: Integrated Line Flux

**As a developer**, I want to integrate a spectrum's flux density across its spectral axis, so I can obtain a single total line flux with the correct compound unit.

**Expected Behavior / Usage:**

The input is a spectrum: a spectral axis (an array of strictly monotonic positions with a unit) paired with a flux array (same length, with a unit), optionally with a per-sample standard-deviation uncertainty. The integrated flux is the area under the flux curve with respect to the spectral axis; its unit is the product of the flux unit and the spectral-axis unit. When a per-sample uncertainty is supplied, an uncertainty on the integrated value is propagated and reported alongside it. Output lines report the integrated value with its unit and, when present, the propagated uncertainty magnitude.

**Test Cases:** `rcb_tests/public_test_cases/feature1_integrated_flux.json`

```json
{
  "description": "Integrate the flux density of a spectrum across its spectral axis to obtain a total line flux, returning a quantity whose unit is the product of the flux unit and the spectral-axis unit. A second scenario attaches a per-sample standard-deviation uncertainty to the flux and verifies that an uncertainty on the integrated result is propagated and reported.",
  "cases": [
    {
      "input": {
        "op": "integrated_flux",
        "spectral_axis": {
          "values": [
            1.0,
            2.0,
            3.0,
            4.0,
            5.0
          ],
          "unit": "AA"
        },
        "flux": {
          "values": [
            0.0,
            1.0,
            2.0,
            1.0,
            0.0
          ],
          "unit": "Jy"
        }
      },
      "expected_output": "integrated_flux=4 unit=Angstrom Jy\n"
    }
  ]
}
```

---

### Feature 2: Equivalent Width

**As a developer**, I want to measure a line's equivalent width against a continuum, so I can quantify line strength independently of the continuum level.

**Expected Behavior / Usage:**

Given a spectrum and a continuum level (defaulting to one flux unit), the equivalent width is the width of a rectangle reaching from zero to the continuum that has the same area as the line relative to the continuum. With the default continuum, an emission line (flux rising above the continuum) yields a negative equivalent width and an absorption line (flux dipping below) yields a positive one, expressed in spectral-axis units. The continuum level may be given explicitly, and the measurement may be restricted to a spectral region specified by a lower/upper bound pair. Output reports the equivalent-width value and its unit.

**Test Cases:** `rcb_tests/public_test_cases/feature2_equivalent_width.json`

```json
{
  "description": "Measure the equivalent width of a spectral line relative to a continuum level. With a default continuum of one flux unit, an emission line yields a negative equivalent width and an absorption line yields a positive one. The continuum level may be supplied explicitly, and the measurement may be restricted to a spectral region given by a lower/upper bound pair.",
  "cases": [
    {
      "input": {
        "op": "equivalent_width",
        "spectral_axis": {
          "values": [
            0.0,
            0.2,
            0.4,
            0.6,
            0.8,
            1.0,
            1.2,
            1.4,
            1.6,
            1.8,
            2.0,
            2.2,
            2.4,
            2.6,
            2.8,
            3.0,
            3.2,
            3.4,
            3.6,
            3.8,
            4.0,
            4.2,
            4.4,
            4.6,
            4.8,
            5.0,
            5.2,
            5.4,
            5.6,
            5.8,
            6.0,
            6.2,
            6.4,
            6.6,
            6.8,
            7.0,
            7.2,
            7.4,
            7.6,
            7.8,
            8.0,
            8.2,
            8.4,
            8.6,
            8.8,
            9.0,
            9.2,
            9.4,
            9.6,
            9.8,
            10.0,
            10.2,
            10.4,
            10.6,
            10.8,
            11.0,
            11.2,
            11.4,
            11.6,
            11.8,
            12.0,
            12.2,
            12.4,
            12.6,
            12.8,
            13.0,
            13.2,
            13.4,
            13.6,
            13.8,
            14.0,
            14.2,
            14.4,
            14.6,
            14.8,
            15.0,
            15.2,
            15.4,
            15.6,
            15.8,
            16.0,
            16.2,
            16.4,
            16.6,
            16.8,
            17.0,
            17.2,
            17.4,
            17.6,
            17.8,
            18.0,
            18.2,
            18.4,
            18.6,
            18.8,
            19.0,
            19.2,
            19.4,
            19.6,
            19.8,
            20.0
          ],
          "unit": "GHz"
        },
        "flux": {
          "values": [
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.00000002,
            1.00000005,
            1.00000015,
            1.00000047,
            1.00000134,
            1.00000373,
            1.00000993,
            1.00002542,
            1.00006252,
            1.00014775,
            1.00033546,
            1.0007318,
            1.00153381,
            1.00308872,
            1.00597602,
            1.011109,
            1.01984109,
            1.03404745,
            1.05613476,
            1.08892162,
            1.13533528,
            1.1978987,
            1.2780373,
            1.3753111,
            1.48675226,
            1.60653066,
            1.72614904,
            1.83527021,
            1.92311635,
            1.98019867,
            2.0,
            1.98019867,
            1.92311635,
            1.83527021,
            1.72614904,
            1.60653066,
            1.48675226,
            1.3753111,
            1.2780373,
            1.1978987,
            1.13533528,
            1.08892162,
            1.05613476,
            1.03404745,
            1.01984109,
            1.011109,
            1.00597602,
            1.00308872,
            1.00153381,
            1.0007318,
            1.00033546,
            1.00014775,
            1.00006252,
            1.00002542,
            1.00000993,
            1.00000373,
            1.00000134,
            1.00000047,
            1.00000015,
            1.00000005,
            1.00000002,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0
          ],
          "unit": "Jy"
        }
      },
      "expected_output": "equivalent_[a derived width metric]-2.50663 unit=GHz\n"
    }
  ]
}
```

---

### Feature 3: Flux-Weighted Centroid

**As a developer**, I want the flux-weighted centroid of a spectrum, so I can locate a line's center of mass on the spectral axis.

**Expected Behavior / Usage:**

The centroid is the flux-weighted mean position along the spectral axis (sum of position times flux divided by sum of flux), returned in spectral-axis units. When a per-sample uncertainty is attached, an uncertainty on the centroid is also reported. The centroid is invariant under a global sign flip of the flux, so a continuum-subtracted absorption line produces the same centroid as the corresponding emission line. Output reports the centroid value with its unit and, when uncertainty is present, the centroid uncertainty magnitude.

**Test Cases:** `rcb_tests/public_test_cases/feature3_centroid.json`

```json
{
  "description": "Compute the flux-weighted centroid (first-moment location) of a spectrum along its spectral axis. When a per-sample uncertainty is attached, an uncertainty on the centroid is also reported. The centroid is invariant under inversion of the flux sign, so a continuum-subtracted absorption line yields the same centroid as the corresponding emission line.",
  "cases": [
    {
      "input": {
        "op": "centroid",
        "spectral_axis": {
          "values": [
            0.0,
            0.2,
            0.4,
            0.6,
            0.8,
            1.0,
            1.2,
            1.4,
            1.6,
            1.8,
            2.0,
            2.2,
            2.4,
            2.6,
            2.8,
            3.0,
            3.2,
            3.4,
            3.6,
            3.8,
            4.0,
            4.2,
            4.4,
            4.6,
            4.8,
            5.0,
            5.2,
            5.4,
            5.6,
            5.8,
            6.0,
            6.2,
            6.4,
            6.6,
            6.8,
            7.0,
            7.2,
            7.4,
            7.6,
            7.8,
            8.0,
            8.2,
            8.4,
            8.6,
            8.8,
            9.0,
            9.2,
            9.4,
            9.6,
            9.8,
            10.0,
            10.2,
            10.4,
            10.6,
            10.8,
            11.0,
            11.2,
            11.4,
            11.6,
            11.8,
            12.0,
            12.2,
            12.4,
            12.6,
            12.8,
            13.0,
            13.2,
            13.4,
            13.6,
            13.8,
            14.0,
            14.2,
            14.4,
            14.6,
            14.8,
            15.0,
            15.2,
            15.4,
            15.6,
            15.8,
            16.0,
            16.2,
            16.4,
            16.6,
            16.8,
            17.0,
            17.2,
            17.4,
            17.6,
            17.8,
            18.0,
            18.2,
            18.4,
            18.6,
            18.8,
            19.0,
            19.2,
            19.4,
            19.6,
            19.8,
            20.0
          ],
          "unit": "GHz"
        },
        "flux": {
          "values": [
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.00000001,
            1.00000002,
            1.00000003,
            1.00000007,
            1.00000015,
            1.00000032,
            1.00000067,
            1.00000134,
            1.00000266,
            1.00000519,
            1.00000993,
            1.00001866,
            1.00003447,
            1.00006252,
            1.00011142,
            1.00019506,
            1.00033546,
            1.00056677,
            1.0009407,
            1.00153381,
            1.00245682,
            1.00386592,
            1.00597602,
            1.00907509,
            1.01353844,
            1.01984109,
            1.0285655,
            1.04040148,
            1.05613476,
            1.07662063,
            1.10273981,
            1.13533528,
            1.17513079,
            1.22263487,
            1.2780373,
            1.3411082,
            1.41111229,
            1.48675226,
            1.56615415,
            1.64690518,
            1.72614904,
            1.8007374,
            1.86742847,
            1.92311635,
            1.96506912,
            1.9911505,
            2.0,
            1.9911505,
            1.96506912,
            1.92311635,
            1.86742847,
            1.8007374,
            1.72614904,
            1.64690518,
            1.56615415,
            1.48675226,
            1.41111229,
            1.3411082,
            1.2780373,
            1.22263487,
            1.17513079,
            1.13533528,
            1.10273981,
            1.07662063,
            1.05613476,
            1.04040148,
            1.0285655,
            1.01984109,
            1.01353844,
            1.00907509,
            1.00597602,
            1.00386592,
            1.00245682,
            1.00153381,
            1.0009407,
            1.00056677,
            1.00033546,
            1.00019506,
            1.00011142,
            1.00006252,
            1.00003447,
            1.00001866,
            1.00000993,
            1.00000519,
            1.00000266,
            1.00000134,
            1.00000067
          ],
          "unit": "Jy"
        },
        "uncertainty": {
          "values": [
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01
          ],
          "unit": "Jy"
        }
      },
      "expected_output": "centroid=10.3139 unit=GHz\n[a secondary value derived from the primary metric]0.00489861\n"
    }
  ]
}
```

---

### Feature 4: Signal-to-Noise Ratio

**As a developer**, I want to compute a spectrum's signal-to-noise ratio, so I can judge data quality both from explicit uncertainties and directly from the flux.

**Expected Behavior / Usage:**

*4.1 Uncertainty-based signal-to-noise — ratio from an explicit uncertainty array*

The signal-to-noise ratio is the mean over samples of flux divided by its standard-deviation uncertainty (a dimensionless number). The computation may be restricted to a spectral region given by a lower/upper bound pair. If the spectrum carries no uncertainty the operation is rejected with a neutral error category. Output reports the ratio value (or, for restricted regions, the value computed over the selected samples).

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_signal_to_noise.json`

```json
{
  "description": "Compute the signal-to-noise ratio of a spectrum as the mean of flux divided by its standard-deviation uncertainty. The calculation may be limited to a spectral region. If no uncertainty is attached to the spectrum the operation is rejected with a neutral error category.",
  "cases": [
    {
      "input": {
        "op": "signal_to_noise",
        "spectral_axis": {
          "values": [
            0.0,
            1.0,
            2.0,
            3.0,
            4.0,
            5.0,
            6.0,
            7.0,
            8.0,
            9.0
          ],
          "unit": "AA"
        },
        "flux": {
          "values": [
            0.5,
            0.6,
            0.7,
            0.8,
            0.9,
            1.0,
            0.9,
            0.8,
            0.7,
            0.6
          ],
          "unit": "Jy"
        },
        "uncertainty": {
          "values": [
            0.1,
            0.1,
            0.1,
            0.1,
            0.1,
            0.1,
            0.1,
            0.1,
            0.1,
            0.1
          ],
          "unit": "Jy"
        }
      },
      "expected_output": "snr=7.5\n"
    }
  ]
}
```

*4.2 Derivative-based signal-to-noise — estimate from flux alone*

This estimator derives a signal-to-noise ratio purely from the flux values using a robust derivative-based formula, requiring no separate uncertainty array. It may be computed over the whole spectrum or restricted to a spectral region. Output reports the dimensionless estimate.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_signal_to_noise_derived.json`

```json
{
  "description": "Estimate the signal-to-noise ratio of a spectrum directly from the flux values using a derivative-based estimator that requires no separate uncertainty array. The estimate may be computed over the whole spectrum or restricted to a spectral region.",
  "cases": [
    {
      "input": {
        "op": "signal_to_noise_derived",
        "spectral_axis": {
          "values": [
            1.0,
            2.0,
            3.0,
            4.0,
            5.0,
            6.0,
            7.0,
            8.0,
            9.0,
            10.0,
            11.0,
            12.0,
            13.0,
            14.0,
            15.0,
            16.0,
            17.0,
            18.0,
            19.0,
            20.0,
            21.0,
            22.0,
            23.0,
            24.0,
            25.0,
            26.0,
            27.0,
            28.0,
            29.0,
            30.0,
            31.0,
            32.0,
            33.0,
            34.0,
            35.0,
            36.0,
            37.0,
            38.0,
            39.0,
            40.0,
            41.0,
            42.0,
            43.0,
            44.0,
            45.0,
            46.0,
            47.0,
            48.0,
            49.0,
            50.0
          ],
          "unit": "um"
        },
        "flux": {
          "values": [
            1.06543894,
            1.12367396,
            1.1682942,
            1.19438758,
            1.19908159,
            1.18185949,
            1.14461718,
            1.09145453,
            1.028224,
            0.96188641,
            0.89974459,
            0.8486395,
            0.8141971,
            0.80020902,
            0.80821515,
            0.83733412,
            0.88436035,
            0.9441169,
            1.0100254,
            1.07483025,
            1.13139732,
            1.17349937,
            1.19650156,
            1.19787165,
            1.17745882,
            1.13751024,
            1.0824237,
            1.01826345,
            0.95209265,
            0.89119578,
            0.84227674,
            0.81072085,
            0.80000196,
            0.81130007,
            0.84337143,
            0.89268542,
            0.95381325,
            1.0200256,
            1.08403341,
            1.13879031,
            1.17826832,
            1.19812147,
            1.1961642,
            1.17261197,
            1.13005757,
            1.07318563,
            1.00825697,
            0.94241934,
            0.88292053,
            0.83631055
          ],
          "unit": "Jy"
        }
      },
      "expected_output": "snr=27.8837\n"
    }
  ]
}
```

---

### Feature 5: Line Width Measurements

**As a developer**, I want several complementary measures of line width, so I can characterise line profiles in different ways.

**Expected Behavior / Usage:**

*5.1 Gaussian sigma width — second-moment standard deviation*

Measures the standard-deviation width of a profile from its second moment. For a Gaussian-shaped line, the result recovers the underlying sigma in spectral-axis units. Output reports the width value and unit.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_gaussian_sigma_width.json`

```json
{
  "description": "Measure the second-moment-based Gaussian sigma (standard deviation) width of a line profile. For a Gaussian profile the returned width recovers the underlying standard deviation in spectral-axis units.",
  "cases": [
    {
      "input": {
        "op": "gaussian_sigma_width",
        "spectral_axis": {
          "values": [
            0.1,
            0.2,
            0.3,
            0.4,
            0.5,
            0.6,
            0.7,
            0.8,
            0.9,
            1.0,
            1.1,
            1.2,
            1.3,
            1.4,
            1.5,
            1.6,
            1.7,
            1.8,
            1.9,
            2.0,
            2.1,
            2.2,
            2.3,
            2.4,
            2.5,
            2.6,
            2.7,
            2.8,
            2.9,
            3.0,
            3.1,
            3.2,
            3.3,
            3.4,
            3.5,
            3.6,
            3.7,
            3.8,
            3.9,
            4.0,
            4.1,
            4.2,
            4.3,
            4.4,
            4.5,
            4.6,
            4.7,
            4.8,
            4.9,
            5.0,
            5.1,
            5.2,
            5.3,
            5.4,
            5.5,
            5.6,
            5.7,
            5.8,
            5.9,
            6.0,
            6.1,
            6.2,
            6.3,
            6.4,
            6.5,
            6.6,
            6.7,
            6.8,
            6.9,
            7.0,
            7.1,
            7.2,
            7.3,
            7.4,
            7.5,
            7.6,
            7.7,
            7.8,
            7.9,
            8.0,
            8.1,
            8.2,
            8.3,
            8.4,
            8.5,
            8.6,
            8.7,
            8.8,
            8.9,
            9.0,
            9.1,
            9.2,
            9.3,
            9.4,
            9.5,
            9.6,
            9.7,
            9.8,
            9.9,
            10.0
          ],
          "unit": "GHz"
        },
        "flux": {
          "values": [
            4e-08,
            8e-08,
            1.6e-07,
            3.3e-07,
            6.7e-07,
            1.35e-06,
            2.66e-06,
            5.17e-06,
            9.9e-06,
            1.863e-05,
            3.454e-05,
            6.304e-05,
            0.00011325,
            0.00020033,
            0.00034885,
            0.00059806,
            0.00100942,
            0.00167731,
            0.0027439,
            0.00441913,
            0.0070068,
            0.01093746,
            0.01680843,
            0.02543035,
            0.03787839,
            0.05554498,
            0.08018855,
            0.1139709,
            0.15947397,
            0.21968467,
            0.29793659,
            0.39779754,
            0.52289501,
            0.67667642,
            0.86210812,
            1.08132583,
            1.33525918,
            1.62326234,
            1.94279064,
            2.28916681,
            2.65547996,
            3.0326533,
            3.40970376,
            3.77419801,
            4.11288781,
            4.41248451,
            4.66051246,
            4.84616617,
            4.96108969,
            5.0,
            4.96108969,
            4.84616617,
            4.66051246,
            4.41248451,
            4.11288781,
            3.77419801,
            3.40970376,
            3.0326533,
            2.65547996,
            2.28916681,
            1.94279064,
            1.62326234,
            1.33525918,
            1.08132583,
            0.86210812,
            0.67667642,
            0.52289501,
            0.39779754,
            0.29793659,
            0.21968467,
            0.15947397,
            0.1139709,
            0.08018855,
            0.05554498,
            0.03787839,
            0.02543035,
            0.01680843,
            0.01093746,
            0.0070068,
            0.00441913,
            0.0027439,
            0.00167731,
            0.00100942,
            0.00059806,
            0.00034885,
            0.00020033,
            0.00011325,
            6.304e-05,
            3.454e-05,
            1.863e-05,
            9.9e-06,
            5.17e-06,
            2.66e-06,
            1.35e-06,
            6.7e-07,
            3.3e-07,
            1.6e-07,
            8e-08,
            4e-08,
            2e-08
          ],
          "unit": "Jy"
        }
      },
      "expected_output": "sigma_[a derived width metric]0.8 unit=GHz\n"
    }
  ]
}
```

*5.2 Gaussian full width at half maximum — sigma scaled to FWHM*

Measures the full width at half maximum assuming a Gaussian profile, obtained by scaling the sigma width by the standard Gaussian sigma-to-FWHM factor. Output reports the width value and unit.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_gaussian_fwhm.json`

```json
{
  "description": "Measure the full width at half maximum of a line under the assumption of a Gaussian profile, derived from the sigma width scaled by the standard Gaussian sigma-to-FWHM factor.",
  "cases": [
    {
      "input": {
        "op": "gaussian_fwhm",
        "spectral_axis": {
          "values": [
            0.1,
            0.2,
            0.3,
            0.4,
            0.5,
            0.6,
            0.7,
            0.8,
            0.9,
            1.0,
            1.1,
            1.2,
            1.3,
            1.4,
            1.5,
            1.6,
            1.7,
            1.8,
            1.9,
            2.0,
            2.1,
            2.2,
            2.3,
            2.4,
            2.5,
            2.6,
            2.7,
            2.8,
            2.9,
            3.0,
            3.1,
            3.2,
            3.3,
            3.4,
            3.5,
            3.6,
            3.7,
            3.8,
            3.9,
            4.0,
            4.1,
            4.2,
            4.3,
            4.4,
            4.5,
            4.6,
            4.7,
            4.8,
            4.9,
            5.0,
            5.1,
            5.2,
            5.3,
            5.4,
            5.5,
            5.6,
            5.7,
            5.8,
            5.9,
            6.0,
            6.1,
            6.2,
            6.3,
            6.4,
            6.5,
            6.6,
            6.7,
            6.8,
            6.9,
            7.0,
            7.1,
            7.2,
            7.3,
            7.4,
            7.5,
            7.6,
            7.7,
            7.8,
            7.9,
            8.0,
            8.1,
            8.2,
            8.3,
            8.4,
            8.5,
            8.6,
            8.7,
            8.8,
            8.9,
            9.0,
            9.1,
            9.2,
            9.3,
            9.4,
            9.5,
            9.6,
            9.7,
            9.8,
            9.9,
            10.0
          ],
          "unit": "GHz"
        },
        "flux": {
          "values": [
            4e-08,
            8e-08,
            1.6e-07,
            3.3e-07,
            6.7e-07,
            1.35e-06,
            2.66e-06,
            5.17e-06,
            9.9e-06,
            1.863e-05,
            3.454e-05,
            6.304e-05,
            0.00011325,
            0.00020033,
            0.00034885,
            0.00059806,
            0.00100942,
            0.00167731,
            0.0027439,
            0.00441913,
            0.0070068,
            0.01093746,
            0.01680843,
            0.02543035,
            0.03787839,
            0.05554498,
            0.08018855,
            0.1139709,
            0.15947397,
            0.21968467,
            0.29793659,
            0.39779754,
            0.52289501,
            0.67667642,
            0.86210812,
            1.08132583,
            1.33525918,
            1.62326234,
            1.94279064,
            2.28916681,
            2.65547996,
            3.0326533,
            3.40970376,
            3.77419801,
            4.11288781,
            4.41248451,
            4.66051246,
            4.84616617,
            4.96108969,
            5.0,
            4.96108969,
            4.84616617,
            4.66051246,
            4.41248451,
            4.11288781,
            3.77419801,
            3.40970376,
            3.0326533,
            2.65547996,
            2.28916681,
            1.94279064,
            1.62326234,
            1.33525918,
            1.08132583,
            0.86210812,
            0.67667642,
            0.52289501,
            0.39779754,
            0.29793659,
            0.21968467,
            0.15947397,
            0.1139709,
            0.08018855,
            0.05554498,
            0.03787839,
            0.02543035,
            0.01680843,
            0.01093746,
            0.0070068,
            0.00441913,
            0.0027439,
            0.00167731,
            0.00100942,
            0.00059806,
            0.00034885,
            0.00020033,
            0.00011325,
            6.304e-05,
            3.454e-05,
            1.863e-05,
            9.9e-06,
            5.17e-06,
            2.66e-06,
            1.35e-06,
            6.7e-07,
            3.3e-07,
            1.6e-07,
            8e-08,
            4e-08,
            2e-08
          ],
          "unit": "Jy"
        }
      },
      "expected_output": "gaussian_fwhm=1.88386 unit=GHz\n"
    }
  ]
}
```

*5.3 Empirical full width at half maximum — measured directly from data*

Measures the full width at half maximum empirically by locating, with linear interpolation between samples, where the flux falls to half of its peak value. Edge cases include a profile peaking at the first sample, a monotonically increasing profile peaking at the last sample, and a perfectly flat profile. Output reports the width value and unit.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_fwhm.json`

```json
{
  "description": "Measure the full width at half maximum of a line empirically from the data, by locating where the flux falls to half of its peak value (with linear interpolation between samples). Edge cases include a profile whose peak is at the first sample, a monotonically increasing profile whose peak is at the last sample, and a flat profile.",
  "cases": [
    {
      "input": {
        "op": "fwhm",
        "spectral_axis": {
          "values": [
            0.1,
            0.2,
            0.3,
            0.4,
            0.5,
            0.6,
            0.7,
            0.8,
            0.9,
            1.0,
            1.1,
            1.2,
            1.3,
            1.4,
            1.5,
            1.6,
            1.7,
            1.8,
            1.9,
            2.0,
            2.1,
            2.2,
            2.3,
            2.4,
            2.5,
            2.6,
            2.7,
            2.8,
            2.9,
            3.0,
            3.1,
            3.2,
            3.3,
            3.4,
            3.5,
            3.6,
            3.7,
            3.8,
            3.9,
            4.0,
            4.1,
            4.2,
            4.3,
            4.4,
            4.5,
            4.6,
            4.7,
            4.8,
            4.9,
            5.0,
            5.1,
            5.2,
            5.3,
            5.4,
            5.5,
            5.6,
            5.7,
            5.8,
            5.9,
            6.0,
            6.1,
            6.2,
            6.3,
            6.4,
            6.5,
            6.6,
            6.7,
            6.8,
            6.9,
            7.0,
            7.1,
            7.2,
            7.3,
            7.4,
            7.5,
            7.6,
            7.7,
            7.8,
            7.9,
            8.0,
            8.1,
            8.2,
            8.3,
            8.4,
            8.5,
            8.6,
            8.7,
            8.8,
            8.9,
            9.0,
            9.1,
            9.2,
            9.3,
            9.4,
            9.5,
            9.6,
            9.7,
            9.8,
            9.9,
            10.0
          ],
          "unit": "GHz"
        },
        "flux": {
          "values": [
            4e-08,
            8e-08,
            1.6e-07,
            3.3e-07,
            6.7e-07,
            1.35e-06,
            2.66e-06,
            5.17e-06,
            9.9e-06,
            1.863e-05,
            3.454e-05,
            6.304e-05,
            0.00011325,
            0.00020033,
            0.00034885,
            0.00059806,
            0.00100942,
            0.00167731,
            0.0027439,
            0.00441913,
            0.0070068,
            0.01093746,
            0.01680843,
            0.02543035,
            0.03787839,
            0.05554498,
            0.08018855,
            0.1139709,
            0.15947397,
            0.21968467,
            0.29793659,
            0.39779754,
            0.52289501,
            0.67667642,
            0.86210812,
            1.08132583,
            1.33525918,
            1.62326234,
            1.94279064,
            2.28916681,
            2.65547996,
            3.0326533,
            3.40970376,
            3.77419801,
            4.11288781,
            4.41248451,
            4.66051246,
            4.84616617,
            4.96108969,
            5.0,
            4.96108969,
            4.84616617,
            4.66051246,
            4.41248451,
            4.11288781,
            3.77419801,
            3.40970376,
            3.0326533,
            2.65547996,
            2.28916681,
            1.94279064,
            1.62326234,
            1.33525918,
            1.08132583,
            0.86210812,
            0.67667642,
            0.52289501,
            0.39779754,
            0.29793659,
            0.21968467,
            0.15947397,
            0.1139709,
            0.08018855,
            0.05554498,
            0.03787839,
            0.02543035,
            0.01680843,
            0.01093746,
            0.0070068,
            0.00441913,
            0.0027439,
            0.00167731,
            0.00100942,
            0.00059806,
            0.00034885,
            0.00020033,
            0.00011325,
            6.304e-05,
            3.454e-05,
            1.863e-05,
            9.9e-06,
            5.17e-06,
            2.66e-06,
            1.35e-06,
            6.7e-07,
            3.3e-07,
            1.6e-07,
            8e-08,
            4e-08,
            2e-08
          ],
          "unit": "Jy"
        }
      },
      "expected_output": "fwhm=1.88489 unit=GHz\n"
    }
  ]
}
```

*5.4 Full width at zero intensity — total non-zero extent*

Measures the total extent over which an emission line profile remains non-zero above the baseline. Output reports the width value and unit.

**Test Cases:** `rcb_tests/public_test_cases/feature5_4_fwzi.json`

```json
{
  "description": "Measure the full width of an emission line at zero intensity, i.e. the total extent over which the line profile is non-zero above the baseline.",
  "cases": [
    {
      "input": {
        "op": "fwzi",
        "spectral_axis": {
          "values": [
            0.0,
            0.50251256,
            1.00502513,
            1.50753769,
            2.01005025,
            2.51256281,
            3.01507538,
            3.51758794,
            4.0201005,
            4.52261307,
            5.02512563,
            5.52763819,
            6.03015075,
            6.53266332,
            7.03517588,
            7.53768844,
            8.04020101,
            8.54271357,
            9.04522613,
            9.54773869,
            10.05025126,
            10.55276382,
            11.05527638,
            11.55778894,
            12.06030151,
            12.56281407,
            13.06532663,
            13.5678392,
            14.07035176,
            14.57286432,
            15.07537688,
            15.57788945,
            16.08040201,
            16.58291457,
            17.08542714,
            17.5879397,
            18.09045226,
            18.59296482,
            19.09547739,
            19.59798995,
            20.10050251,
            20.60301508,
            21.10552764,
            21.6080402,
            22.11055276,
            22.61306533,
            23.11557789,
            23.61809045,
            24.12060302,
            24.62311558,
            25.12562814,
            25.6281407,
            26.13065327,
            26.63316583,
            27.13567839,
            27.63819095,
            28.14070352,
            28.64321608,
            29.14572864,
            29.64824121,
            30.15075377,
            30.65326633,
            31.15577889,
            31.65829146,
            32.16080402,
            32.66331658,
            33.16582915,
            33.66834171,
            34.17085427,
            34.67336683,
            35.1758794,
            35.67839196,
            36.18090452,
            36.68341709,
            37.18592965,
            37.68844221,
            38.19095477,
            38.69346734,
            39.1959799,
            39.69849246,
            40.20100503,
            40.70351759,
            41.20603015,
            41.70854271,
            42.21105528,
            42.71356784,
            43.2160804,
            43.71859296,
            44.22110553,
            44.72361809,
            45.22613065,
            45.72864322,
            46.23115578,
            46.73366834,
            47.2361809,
            47.73869347,
            48.24120603,
            48.74371859,
            49.24623116,
            49.74874372,
            50.25125628,
            50.75376884,
            51.25628141,
            51.75879397,
            52.26130653,
            52.7638191,
            53.26633166,
            53.76884422,
            54.27135678,
            54.77386935,
            55.27638191,
            55.77889447,
            56.28140704,
            56.7839196,
            57.28643216,
            57.78894472,
            58.29145729,
            58.79396985,
            59.29648241,
            59.79899497,
            60.30150754,
            60.8040201,
            61.30653266,
            61.80904523,
            62.31155779,
            62.81407035,
            63.31658291,
            63.81909548,
            64.32160804,
            64.8241206,
            65.32663317,
            65.82914573,
            66.33165829,
            66.83417085,
            67.33668342,
            67.83919598,
            68.34170854,
            68.84422111,
            69.34673367,
            69.84924623,
            70.35175879,
            70.85427136,
            71.35678392,
            71.85929648,
            72.36180905,
            72.86432161,
            73.36683417,
            73.86934673,
            74.3718593,
            74.87437186,
            75.37688442,
            75.87939698,
            76.38190955,
            76.88442211,
            77.38693467,
            77.88944724,
            78.3919598,
            78.89447236,
            79.39698492,
            79.89949749,
            80.40201005,
            80.90452261,
            81.40703518,
            81.90954774,
            82.4120603,
            82.91457286,
            83.41708543,
            83.91959799,
            84.42211055,
            84.92462312,
            85.42713568,
            85.92964824,
            86.4321608,
            86.93467337,
            87.43718593,
            87.93969849,
            88.44221106,
            88.94472362,
            89.44723618,
            89.94974874,
            90.45226131,
            90.95477387,
            91.45728643,
            91.95979899,
            92.46231156,
            92.96482412,
            93.46733668,
            93.96984925,
            94.47236181,
            94.97487437,
            95.47738693,
            95.9798995,
            96.48241206,
            96.98492462,
            97.48743719,
            97.98994975,
            98.49246231,
            98.99497487,
            99.49748744,
            100.0
          ],
          "unit": "AA"
        },
        "flux": {
          "values": [
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1e-08,
            1e-08,
            2e-08,
            3e-08,
            6e-08,
            1e-07,
            1.8e-07,
            3.1e-07,
            5.3e-07,
            9e-07,
            1.52e-06,
            2.55e-06,
            4.22e-06,
            6.93e-06,
            1.125e-05,
            1.809e-05,
            2.879e-05,
            4.535e-05,
            7.073e-05,
            0.00010921,
            0.00016692,
            0.00025255,
            0.00037829,
            0.00056093,
            0.00082338,
            0.00119649,
            0.00172119,
            0.00245112,
            0.00345551,
            0.00482251,
            0.00666266,
            0.00911245,
            0.01233776,
            0.01653677,
            0.0219421,
            0.02882167,
            0.03747775,
            0.04824374,
            0.0614783,
            0.07755611,
            0.09685532,
            0.11974137,
            0.14654744,
            0.17755201,
            0.21295421,
            0.25284837,
            0.29719904,
            0.34581827,
            0.3983472,
            0.45424368,
            0.51277792,
            0.5730375,
            0.63394279,
            0.69427317,
            0.75270361,
            0.80785035,
            0.85832375,
            0.90278564,
            0.94000778,
            0.96892811,
            0.98870097,
            0.9987382,
            0.9987382,
            0.98870097,
            0.96892811,
            0.94000778,
            0.90278564,
            0.85832375,
            0.80785035,
            0.75270361,
            0.69427317,
            0.63394279,
            0.5730375,
            0.51277792,
            0.45424368,
            0.3983472,
            0.34581827,
            0.29719904,
            0.25284837,
            0.21295421,
            0.17755201,
            0.14654744,
            0.11974137,
            0.09685532,
            0.07755611,
            0.0614783,
            0.04824374,
            0.03747775,
            0.02882167,
            0.0219421,
            0.01653677,
            0.01233776,
            0.00911245,
            0.00666266,
            0.00482251,
            0.00345551,
            0.00245112,
            0.00172119,
            0.00119649,
            0.00082338,
            0.00056093,
            0.00037829,
            0.00025255,
            0.00016692,
            0.00010921,
            7.073e-05,
            4.535e-05,
            2.879e-05,
            1.809e-05,
            1.125e-05,
            6.93e-06,
            4.22e-06,
            2.55e-06,
            1.52e-06,
            9e-07,
            5.3e-07,
            3.1e-07,
            1.8e-07,
            1e-07,
            6e-08,
            3e-08,
            2e-08,
            1e-08,
            1e-08,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0
          ],
          "unit": "Jy"
        }
      },
      "expected_output": "fwzi=113.006 unit=Angstrom\n"
    }
  ]
}
```

---

### Feature 6: Statistical Moments

**As a developer**, I want statistical moments of a spectrum, so I can summarise its flux distribution along the spectral axis.

**Expected Behavior / Usage:**

Computes moments of a spectrum about the spectral axis at a requested order. Order 0 is the integrated flux (flux unit). Order 1 is the flux-weighted mean position (spectral-axis unit). Order 2 is a variance-like spread (spectral-axis unit squared). In general the unit is the flux unit for order 0 and the spectral-axis unit raised to the moment order otherwise. Output reports the moment value and unit.

**Test Cases:** `rcb_tests/public_test_cases/feature6_moment.json`

```json
{
  "description": "Compute statistical moments of a spectrum about its spectral axis. Order 0 is the integrated flux, order 1 is the flux-weighted mean position, and order 2 is the variance-like spread. The returned unit is the flux unit for order 0 and the spectral-axis unit raised to the moment order otherwise.",
  "cases": [
    {
      "input": {
        "op": "moment",
        "spectral_axis": {
          "values": [
            0.0,
            0.2,
            0.4,
            0.6,
            0.8,
            1.0,
            1.2,
            1.4,
            1.6,
            1.8,
            2.0,
            2.2,
            2.4,
            2.6,
            2.8,
            3.0,
            3.2,
            3.4,
            3.6,
            3.8,
            4.0,
            4.2,
            4.4,
            4.6,
            4.8,
            5.0,
            5.2,
            5.4,
            5.6,
            5.8,
            6.0,
            6.2,
            6.4,
            6.6,
            6.8,
            7.0,
            7.2,
            7.4,
            7.6,
            7.8,
            8.0,
            8.2,
            8.4,
            8.6,
            8.8,
            9.0,
            9.2,
            9.4,
            9.6,
            9.8,
            10.0,
            10.2,
            10.4,
            10.6,
            10.8,
            11.0,
            11.2,
            11.4,
            11.6,
            11.8,
            12.0,
            12.2,
            12.4,
            12.6,
            12.8,
            13.0,
            13.2,
            13.4,
            13.6,
            13.8,
            14.0,
            14.2,
            14.4,
            14.6,
            14.8,
            15.0,
            15.2,
            15.4,
            15.6,
            15.8,
            16.0,
            16.2,
            16.4,
            16.6,
            16.8,
            17.0,
            17.2,
            17.4,
            17.6,
            17.8,
            18.0,
            18.2,
            18.4,
            18.6,
            18.8,
            19.0,
            19.2,
            19.4,
            19.6,
            19.8,
            20.0
          ],
          "unit": "GHz"
        },
        "flux": {
          "values": [
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            2e-08,
            5e-08,
            1.5e-07,
            4.7e-07,
            1.34e-06,
            3.73e-06,
            9.93e-06,
            2.542e-05,
            6.252e-05,
            0.00014775,
            0.00033546,
            0.0007318,
            0.00153381,
            0.00308872,
            0.00597602,
            0.011109,
            0.01984109,
            0.03404745,
            0.05613476,
            0.08892162,
            0.13533528,
            0.1978987,
            0.2780373,
            0.3753111,
            0.48675226,
            0.60653066,
            0.72614904,
            0.83527021,
            0.92311635,
            0.98019867,
            1.0,
            0.98019867,
            0.92311635,
            0.83527021,
            0.72614904,
            0.60653066,
            0.48675226,
            0.3753111,
            0.2780373,
            0.1978987,
            0.13533528,
            0.08892162,
            0.05613476,
            0.03404745,
            0.01984109,
            0.011109,
            0.00597602,
            0.00308872,
            0.00153381,
            0.0007318,
            0.00033546,
            0.00014775,
            6.252e-05,
            2.542e-05,
            9.93e-06,
            3.73e-06,
            1.34e-06,
            4.7e-07,
            1.5e-07,
            5e-08,
            2e-08,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0
          ],
          "unit": "Jy"
        },
        "params": {
          "order": 0
        }
      },
      "expected_output": "moment=12.5331 unit=Jy\n"
    }
  ]
}
```

---

### Feature 7: Continuum Fitting

**As a developer**, I want to fit a smooth continuum to a spectrum, so I can model and remove the baseline beneath spectral features.

**Expected Behavior / Usage:**

Fits a smooth continuum model to a spectrum and evaluates the fitted continuum at requested sample indices. The input here is a noise-free spectrum consisting of a broad smooth continuum plus a narrow emission feature; the fit recovers the broad continuum shape while remaining insensitive to the narrow line. Output reports the fitted continuum value at each requested sample index.

**Test Cases:** `rcb_tests/public_test_cases/feature7_fit_continuum.json`

```json
{
  "description": "Fit a smooth continuum model to a spectrum and evaluate the fitted continuum at selected sample positions. The input is a noise-free spectrum consisting of a broad smooth continuum plus a narrow emission feature; the fitted continuum recovers the broad shape while ignoring the narrow line.",
  "cases": [
    {
      "input": {
        "op": "fit_continuum",
        "spectral_axis": {
          "values": [
            0.0,
            0.16949153,
            0.33898305,
            0.50847458,
            0.6779661,
            0.84745763,
            1.01694915,
            1.18644068,
            1.3559322,
            1.52542373,
            1.69491525,
            1.86440678,
            2.03389831,
            2.20338983,
            2.37288136,
            2.54237288,
            2.71186441,
            2.88135593,
            3.05084746,
            3.22033898,
            3.38983051,
            3.55932203,
            3.72881356,
            3.89830508,
            4.06779661,
            4.23728814,
            4.40677966,
            4.57627119,
            4.74576271,
            4.91525424,
            5.08474576,
            5.25423729,
            5.42372881,
            5.59322034,
            5.76271186,
            5.93220339,
            6.10169492,
            6.27118644,
            6.44067797,
            6.61016949,
            6.77966102,
            6.94915254,
            7.11864407,
            7.28813559,
            7.45762712,
            7.62711864,
            7.79661017,
            7.96610169,
            8.13559322,
            8.30508475,
            8.47457627,
            8.6440678,
            8.81355932,
            8.98305085,
            9.15254237,
            9.3220339,
            9.49152542,
            9.66101695,
            9.83050847,
            10.0
          ],
          "unit": "um"
        },
        "flux": {
          "values": [
            1.62027397,
            1.68736423,
            1.75504285,
            1.82316137,
            1.89156381,
            1.96008715,
            2.02856193,
            2.0968128,
            2.16465928,
            2.23191648,
            2.29839585,
            2.3639061,
            2.42825401,
            2.49124539,
            2.55268603,
            2.61238268,
            2.67014406,
            2.72578181,
            2.7791116,
            2.82995406,
            2.87813581,
            2.92349048,
            2.96585957,
            3.00509348,
            3.04105229,
            3.07360668,
            3.10263863,
            3.12804217,
            3.14972404,
            3.16760421,
            3.18161642,
            3.19170855,
            3.19784298,
            3.19999681,
            3.19816359,
            3.19581013,
            3.602513,
            6.04688449,
            4.26656672,
            3.15435216,
            3.10483603,
            3.07606034,
            3.04378356,
            3.00809249,
            2.96911558,
            2.92699192,
            2.88187038,
            2.83390876,
            2.78327286,
            2.73013554,
            2.6746757,
            2.61707733,
            2.55752849,
            2.49622027,
            2.43334581,
            2.36909928,
            2.30367489,
            2.23726597,
            2.17006402,
            2.10225782
          ],
          "unit": "Jy"
        },
        "params": {
          "sample_indices": [
            0,
            10,
            20,
            30,
            40,
            50
          ]
        }
      },
      "expected_output": "continuum[0]=1.5782\ncontinuum[10]=2.313\ncontinuum[20]=2.8994\ncontinuum[30]=3.2393\ncontinuum[40]=3.2347\ncontinuum[50]=2.7874\n"
    }
  ]
}
```

---

### Feature 8: Spectral Region Algebra

**As a developer**, I want to describe and manipulate intervals on a spectral axis, so I can select and reason about portions of a spectrum.

**Expected Behavior / Usage:**

*8.1 Region bounds and ordering — overall extent and canonical order*

A spectral region is a collection of one or more sub-intervals on a spectral axis. Independent of the order in which sub-intervals are supplied, the region exposes an overall lower bound (the minimum) and upper bound (the maximum), and canonicalises its sub-intervals into ascending order. Output reports the lower and upper bounds with their unit, followed by each sub-interval in ascending order.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_region_bounds.json`

```json
{
  "description": "A spectral region is a collection of one or more sub-intervals on a spectral axis. Regardless of the order in which the sub-intervals are supplied, the region exposes an overall lower bound (minimum) and upper bound (maximum), and its sub-intervals are canonicalised into ascending order.",
  "cases": [
    {
      "input": {
        "op": "region_bounds",
        "unit": "um",
        "subregions": [
          [
            0.3,
            1.0
          ],
          [
            0.45,
            0.6
          ],
          [
            0.04,
            0.05
          ],
          [
            0.8,
            0.9
          ]
        ]
      },
      "expected_output": "lower=0.04 unit=um\nupper=1 unit=um\nsubregion[0]=0.04 0.05 unit=um\nsubregion[1]=0.3 1 unit=um\nsubregion[2]=0.45 0.6 unit=um\nsubregion[3]=0.8 0.9 unit=um\n"
    }
  ]
}
```

*8.2 Region from center and width — symmetric construction*

Constructs a region from a center position and a width, spanning from center minus half-width to center plus half-width. A zero or negative width is rejected with a neutral error category. Output reports the lower and upper bounds with their unit.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_region_from_center.json`

```json
{
  "description": "Construct a spectral region from a center position and a width: the region spans from center minus half-width to center plus half-width. A zero or negative width is rejected with a neutral error category.",
  "cases": [
    {
      "input": {
        "op": "region_from_center",
        "unit": "AA",
        "center": 6563.0,
        "width": 10.0
      },
      "expected_output": "lower=6558 unit=Angstrom\nupper=6568 unit=Angstrom\n"
    }
  ]
}
```

*8.3 Region combination — union of sub-intervals*

Combines multiple regions into one whose sub-intervals are the union of the inputs, reported in ascending order. Output reports each resulting sub-interval with its unit.

**Test Cases:** `rcb_tests/public_test_cases/feature8_3_region_combine.json`

```json
{
  "description": "Combine multiple spectral regions into a single region whose sub-intervals are the union of the inputs, reported in ascending order.",
  "cases": [
    {
      "input": {
        "op": "region_combine",
        "unit": "um",
        "regions": [
          [
            [
              0.45,
              0.6
            ]
          ],
          [
            [
              0.8,
              0.9
            ]
          ]
        ]
      },
      "expected_output": "subregion[0]=0.45 0.6 unit=um\nsubregion[1]=0.8 0.9 unit=um\n"
    }
  ]
}
```

*8.4 Region inversion — complementary gaps within a range*

Inverts a region within an enclosing lower/upper range, producing the gaps between the original sub-intervals, including the segment from the enclosing lower bound to the first interval and from the last interval to the enclosing upper bound. Output reports each resulting gap sub-interval with its unit.

**Test Cases:** `rcb_tests/public_test_cases/feature8_4_region_invert.json`

```json
{
  "description": "Invert a spectral region within an enclosing lower/upper range: the result is the set of gaps between the original sub-intervals, including the segments from the enclosing lower bound to the first interval and from the last interval to the enclosing upper bound.",
  "cases": [
    {
      "input": {
        "op": "region_invert",
        "unit": "um",
        "subregions": [
          [
            0.15,
            0.2
          ],
          [
            0.3,
            0.4
          ],
          [
            0.45,
            0.6
          ],
          [
            0.8,
            0.9
          ]
        ],
        "params": {
          "lower": 0.05,
          "upper": 1.0
        }
      },
      "expected_output": "subregion[0]=0.05 0.15 unit=um\nsubregion[1]=0.2 0.3 unit=um\nsubregion[2]=0.4 0.45 unit=um\nsubregion[3]=0.6 0.8 unit=um\nsubregion[4]=0.9 1 unit=um\n"
    }
  ]
}
```

---

### Feature 9: Region Excision

**As a developer**, I want to delete the samples inside chosen intervals from a spectrum, so I can remove contaminated or unwanted regions.

**Expected Behavior / Usage:**

Removes the samples whose spectral-axis positions fall inside one or more sub-intervals, returning a spectrum with those samples deleted. The reported length decreases by the number of removed samples, and the remaining flux sum reflects only the surviving samples. Output reports the resulting length and the surviving flux sum with its unit.

**Test Cases:** `rcb_tests/public_test_cases/feature9_excise_regions.json`

```json
{
  "description": "Remove the samples that fall inside one or more spectral sub-intervals from a spectrum, returning a spectrum with those samples deleted. The reported length decreases by the number of removed samples and the remaining flux sum reflects only the surviving samples.",
  "cases": [
    {
      "input": {
        "op": "excise_regions",
        "spectral_axis": {
          "values": [
            5000.0,
            5001.0,
            5002.0,
            5003.0,
            5004.0,
            5005.0,
            5006.0,
            5007.0,
            5008.0,
            5009.0
          ],
          "unit": "AA"
        },
        "flux": {
          "values": [
            3.1,
            2.8,
            3.4,
            2.9,
            3.2,
            3.0,
            2.7,
            3.3,
            3.1,
            2.9
          ],
          "unit": "Jy"
        },
        "params": {
          "regions": [
            [
              5002,
              5004
            ]
          ]
        }
      },
      "expected_output": "length=8\nflux_sum=24.1 unit=Jy\n"
    }
  ]
}
```

---

### Feature 10: Signal-to-Noise Threshold Masking

**As a developer**, I want to mask samples by a signal-to-noise threshold, so I can flag low-quality or high-quality samples programmatically.

**Expected Behavior / Usage:**

Builds a boolean mask over a spectrum by comparing each sample's signal-to-noise ratio (flux divided by uncertainty) against a threshold using a chosen comparison operator (for example, less-than, greater-than). Samples satisfying the comparison relative to the threshold are masked. The default operator masks samples below the threshold. Output reports the mask as a sequence of per-sample boolean flags.

**Test Cases:** `rcb_tests/public_test_cases/feature10_snr_mask.json`

```json
{
  "description": "Build a boolean mask over a spectrum by comparing each sample's signal-to-noise ratio (flux divided by uncertainty) against a threshold. Samples whose ratio satisfies the chosen comparison operator relative to the threshold are masked. The default operator masks samples below the threshold.",
  "cases": [
    {
      "input": {
        "op": "snr_mask",
        "spectral_axis": {
          "values": [
            0.0,
            1.0,
            2.0,
            3.0,
            4.0,
            5.0,
            6.0,
            7.0,
            8.0,
            9.0
          ],
          "unit": "um"
        },
        "flux": {
          "values": [
            10.0,
            80.0,
            5.0,
            12.0,
            95.0,
            70.0,
            8.0,
            6.0,
            4.0,
            90.0
          ],
          "unit": "Jy"
        },
        "uncertainty": {
          "values": [
            2.0,
            1.0,
            3.0,
            4.0,
            1.0,
            1.0,
            5.0,
            6.0,
            7.0,
            1.0
          ],
          "unit": "Jy"
        },
        "params": {
          "threshold": 50,
          "operator": "<"
        }
      },
      "expected_output": "mask=0100110001\n"
    }
  ]
}
```

---

### Feature 11: Spectral Axis Construction

**As a developer**, I want flexible spectral-axis construction, so I can build axes from bin edges and rely on ordering guarantees.

**Expected Behavior / Usage:**

*11.1 Bin edges to centers — derive centers from edges*

A spectral axis may be specified by its bin edges rather than bin centers. When supplied as edges, the resulting axis exposes the bin centers (midpoints of consecutive edges) while retaining the original edges; this holds for irregular spacing. Output reports the derived centers and the retained edges.

**Test Cases:** `rcb_tests/public_test_cases/feature11_1_spectral_axis_bins.json`

```json
{
  "description": "A spectral axis can be specified by its bin edges instead of its bin centers. When supplied as edges, the resulting axis exposes the bin centers (midpoints of consecutive edges) while retaining the original edges. This works for irregular spacing.",
  "cases": [
    {
      "input": {
        "op": "spectral_axis_bins",
        "spectral_axis": {
          "values": [
            500.0,
            510.0,
            550.0,
            560.0,
            590.0
          ],
          "unit": "AA"
        },
        "params": {
          "bin_specification": "edges"
        }
      },
      "expected_output": "centers=505 530 555 575\nbin_edges=500 510 550 560 590\n"
    }
  ]
}
```

*11.2 Pixel axis ordering — ascending requirement*

A spectral axis expressed in pixel units must be strictly ascending; supplying a descending pixel axis is rejected with a neutral error category. Output reports the neutral error category.

**Test Cases:** `rcb_tests/public_test_cases/feature11_2_pixel_axis_order.json`

```json
{
  "description": "A spectral axis expressed in pixel units must be strictly ascending. Supplying a descending pixel axis is rejected with a neutral error category.",
  "cases": [
    {
      "input": {
        "op": "spectral_axis_bins",
        "spectral_axis": {
          "values": [
            5109.0,
            5108.0,
            5107.0,
            5106.0,
            5105.0,
            5104.0,
            5103.0,
            5102.0,
            5101.0,
            5100.0
          ],
          "unit": "pix"
        },
        "params": {
          "bin_specification": "centers"
        }
      },
      "expected_output": "error=pixel_axis_not_ascending\n"
    }
  ]
}
```

---

### Feature 12: Spectrum Arithmetic

**As a developer**, I want to combine spectra element-wise, so I can add, subtract, multiply, and divide flux arrays that share a spectral axis.

**Expected Behavior / Usage:**

Combines two spectra sharing the same spectral axis element-wise using addition, subtraction, multiplication, or division of their flux arrays, preserving the resulting flux unit. When an operand contains undefined (NaN) flux samples, the corresponding samples of the result are flagged in the output mask. Output reports the resulting flux array, its unit, and (when any sample is undefined) the per-sample mask.

**Test Cases:** `rcb_tests/public_test_cases/feature12_arithmetic.json`

```json
{
  "description": "Combine two spectra sharing the same spectral axis element-wise using addition, subtraction, multiplication, or division of their flux arrays. When one operand contains undefined (NaN) flux samples, the corresponding samples of the result are flagged in the output mask.",
  "cases": [
    {
      "input": {
        "op": "arithmetic",
        "spectral_axis": {
          "values": [
            1.0,
            2.0,
            3.0,
            4.0,
            5.0
          ],
          "unit": "nm"
        },
        "flux": {
          "values": [
            10.0,
            20.0,
            30.0,
            40.0,
            50.0
          ],
          "unit": "Jy"
        },
        "params": {
          "operation": "add",
          "other": {
            "values": [
              1.0,
              2.0,
              3.0,
              4.0,
              5.0
            ],
            "unit": "Jy"
          }
        }
      },
      "expected_output": "flux=11 22 33 44 55\nunit=Jy\n"
    },
    {
      "input": {
        "op": "arithmetic",
        "spectral_axis": {
          "values": [
            1.0,
            2.0,
            3.0,
            4.0,
            5.0
          ],
          "unit": "nm"
        },
        "flux": {
          "values": [
            10.0,
            20.0,
            30.0,
            40.0,
            50.0
          ],
          "unit": "Jy"
        },
        "params": {
          "operation": "subtract",
          "other": {
            "values": [
              1.0,
              2.0,
              3.0,
              4.0,
              5.0
            ],
            "unit": "Jy"
          }
        }
      },
      "expected_output": "flux=9 18 27 36 45\nunit=Jy\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the features above (spectrum model, unit-aware analysis routines, continuum fitting, region algebra, masking), with high maintainability and no monolithic files.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically and physically separated from the core domain. Native faults must be normalised to neutral `error=<category>` lines; the stdout contract must never leak host-language runtime artifacts.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{stem}@{index:03}.txt` containing **only** the raw stdout from the program under test (no PASS/FAIL or metadata), directly comparable against `expected_output`.


---
**Implementation notes:**
- calculate the width parameter using the gaussian derivation logic
- apply the standard FWHM normalization to the input values
