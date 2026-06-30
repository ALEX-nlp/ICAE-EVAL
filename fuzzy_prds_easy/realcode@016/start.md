## Product Requirement Document

# PNG Visual Comparison and Diffing - Black-Box Image Equivalence Contracts

## Project Goal

Build a PNG visual comparison and diff-generation tool that allows developers to compare rendered images and produce highlighted difference artifacts without hand-writing pixel traversal, tolerance handling, or image-output plumbing.

---

## Background & Problem

Without this library/tool, developers are forced to manually decode PNG files, compare image dimensions, compare RGB channels, account for barely visible color differences, and construct diff images pixel by pixel. This leads to repetitive code, brittle screenshot tests, and hard-to-debug visual regressions.

With this library/tool, developers can provide two PNG images, choose a comparison mode, and receive either a concise equivalence result or a generated diff image that exposes visible changes.

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

### Feature 1: Image Visual Equivalence

**As a developer**, I want to compare two PNG images in a way that reflects visible output rather than only file identity, so I can detect regressions in rendered screenshots and generated images.

**Expected Behavior / Usage:**

The input is a JSON object with `reference_image`, `candidate_image`, and `input_transport`. The image names identify PNG fixtures available to the adapter; `input_transport` is either `file` for file-backed input or `buffer` for in-memory bytes. Optional `comparison_options` may request `color_tolerance` for a perceptual threshold, `strict_pixel_match` for exact RGB comparison, or `ignore_single_vertical_caret` to ignore one continuous vertical changed column such as a text caret. The output reports the two image identifiers, transport, decoded dimensions, final comparison value (`look_same` or `different`), and `error=none`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_image_comparison.json`

```json
{
    "description": "Compares two PNG images supplied either as file-backed images or in-memory image bytes and reports whether the rendered pixels look the same under the requested comparison options.",
    "cases": [
        {
            "input": {
                "reference_image": "ref.png",
                "candidate_image": "same.png",
                "input_transport": "file"
            },
            "expected_output": "reference=ref.png\ncandidate=same.png\ninput_transport=file\nreference_size=50x50\ncandidate_size=50x50\ncomparison=look_same\nerror=none\n"
        },
        {
            "input": {
                "reference_image": "ref.png",
                "candidate_image": "different.png",
                "input_transport": "file"
            },
            "expected_output": "reference=ref.png\ncandidate=different.png\ninput_transport=file\nreference_size=50x50\ncandidate_size=50x50\ncomparison=different\nerror=none\n"
        },
        {
            "input": {
                "reference_image": "ref.png",
                "candidate_image": "different.png",
                "input_transport": "file",
                "comparison_options": {
                    "color_tolerance": 50
                }
            },
            "expected_output": "reference=ref.png\ncandidate=different.png\ninput_transport=file\nreference_size=50x50\ncandidate_size=50x50\ncomparison=look_same\nerror=none\n"
        },
        {
            "input": {
                "reference_image": "ref.png",
                "candidate_image": "different-unnoticable.png",
                "input_transport": "file"
            },
            "expected_output": "reference=ref.png\ncandidate=different-unnoticable.png\ninput_transport=file\nreference_size=50x50\ncandidate_size=50x50\ncomparison=look_same\nerror=none\n"
        },
        {
            "input": {
                "reference_image": "ref.png",
                "candidate_image": "different-unnoticable.png",
                "input_transport": "file",
                "comparison_options": {
                    "strict_pixel_match": true
                }
            },
            "expected_output": "reference=ref.png\ncandidate=different-unnoticable.png\ninput_transport=file\nreference_size=50x50\ncandidate_size=50x50\ncomparison=different\nerror=none\n"
        },
        {
            "input": {
                "reference_image": "ref.png",
                "candidate_image": "wide.png",
                "input_transport": "file"
            },
            "expected_output": "reference=ref.png\ncandidate=wide.png\ninput_transport=file\nreference_size=50x50\ncandidate_size=80x50\ncomparison=different\nerror=none\n"
        },
        {
            "input": {
                "reference_image": "no-caret.png",
                "candidate_image": "caret.png",
                "input_transport": "file"
            },
            "expected_output": "reference=no-caret.png\ncandidate=caret.png\ninput_transport=file\nreference_size=176x26\ncandidate_size=176x26\ncomparison=different\nerror=none\n"
        },
        {
            "input": {
                "reference_image": "no-caret.png",
                "candidate_image": "caret.png",
                "input_transport": "file",
                "comparison_options": {
                    "ignore_single_vertical_caret": true
                }
            },
            "expected_output": "reference=no-caret.png\ncandidate=caret.png\ninput_transport=file\nreference_size=176x26\ncandidate_size=176x26\ncomparison=look_same\nerror=none\n"
        },
        {
            "input": {
                "reference_image": "no-caret.png",
                "candidate_image": "not-only-caret.png",
                "input_transport": "file",
                "comparison_options": {
                    "ignore_single_vertical_caret": true
                }
            },
            "expected_output": "reference=no-caret.png\ncandidate=not-only-caret.png\ninput_transport=file\nreference_size=176x26\ncandidate_size=176x26\ncomparison=different\nerror=none\n"
        },
        {
            "input": {
                "reference_image": "no-caret.png",
                "candidate_image": "two-caret.png",
                "input_transport": "file",
                "comparison_options": {
                    "ignore_single_vertical_caret": true
                }
            },
            "expected_output": "reference=no-caret.png\ncandidate=two-caret.png\ninput_transport=file\nreference_size=176x26\ncandidate_size=176x26\ncomparison=different\nerror=none\n"
        },
        {
            "input": {
                "reference_image": "no-caret.png",
                "candidate_image": "broken-caret.png",
                "input_transport": "file",
                "comparison_options": {
                    "ignore_single_vertical_caret": true
                }
            },
            "expected_output": "reference=no-caret.png\ncandidate=broken-caret.png\ninput_transport=file\nreference_size=176x26\ncandidate_size=176x26\ncomparison=different\nerror=none\n"
        }
    ]
}
```

---

### Feature 2: Comparison Mode Conflict

**As a developer**, I want to receive a clear validation result when mutually exclusive comparison modes are requested, so I can avoid ambiguous image-comparison behavior.

**Expected Behavior / Usage:**

The input is a comparison request that simultaneously enables exact pixel matching and a perceptual color tolerance. These options are mutually exclusive because exact matching cannot also apply a tolerance. The output is a normalized, language-neutral error with the conflicting option names on a separate line.

**Test Cases:** `rcb_tests/public_test_cases/feature2_comparison_option_conflict.json`

```json
{
    "description": "Rejects a comparison request that asks for strict pixel matching and perceptual tolerance at the same time, because those modes are mutually exclusive.",
    "cases": [
        {
            "input": {
                "reference_image": "ref.png",
                "candidate_image": "same.png",
                "input_transport": "file",
                "comparison_options": {
                    "strict_pixel_match": true,
                    "color_tolerance": 9000
                }
            },
            "expected_output": "error=conflicting_comparison_options\noptions=strict_pixel_match,color_tolerance\n"
        }
    ]
}
```

---

### Feature 3: Diff Image Generation

**As a developer**, I want to generate an inspectable PNG diff image from two rendered images, so I can see where images differ without manually comparing pixels.

**Expected Behavior / Usage:**

The input is a JSON object with `reference_image`, `current_image`, `highlight_color`, and `output_delivery`. Matching pixels are copied from the reference image, pixels that differ under the selected comparison mode are painted with the requested highlight color, and areas outside the smaller image are also highlighted when dimensions differ. Optional `diff_options` supports `color_tolerance` and `strict_pixel_match` using the same semantics as comparison. `output_delivery` is `file` for a written PNG or `buffer` for an in-memory PNG. The output reports source identifiers, delivery mode, PNG signature when returned as a buffer, decoded diff dimensions, a deterministic RGB color-count summary of the generated image, and `error=none`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_diff_image_generation.json`

```json
{
    "description": "Builds a PNG diff image that preserves matching pixels and paints differing or out-of-bounds pixels with the requested highlight color, returning either a written image or an in-memory PNG.",
    "cases": [
        {
            "input": {
                "reference_image": "ref.png",
                "current_image": "same.png",
                "highlight_color": "#ff00ff",
                "output_delivery": "file"
            },
            "expected_output": "reference=ref.png\ncurrent=same.png\noutput_delivery=file\ndiff_size=50x50\ncolors=0,0,0:1300;255,255,255:1200\nerror=none\n"
        },
        {
            "input": {
                "reference_image": "ref.png",
                "current_image": "different.png",
                "highlight_color": "#ff00ff",
                "output_delivery": "file"
            },
            "expected_output": "reference=ref.png\ncurrent=different.png\noutput_delivery=file\ndiff_size=50x50\ncolors=0,0,0:1299;255,0,255:301;255,255,255:900\nerror=none\n"
        },
        {
            "input": {
                "reference_image": "ref.png",
                "current_image": "different.png",
                "highlight_color": "#ff00ff",
                "output_delivery": "file",
                "diff_options": {
                    "color_tolerance": 50
                }
            },
            "expected_output": "reference=ref.png\ncurrent=different.png\noutput_delivery=file\ndiff_size=50x50\ncolors=0,0,0:1300;255,255,255:1200\nerror=none\n"
        },
        {
            "input": {
                "reference_image": "ref.png",
                "current_image": "different.png",
                "highlight_color": "#00FF00",
                "output_delivery": "file"
            },
            "expected_output": "reference=ref.png\ncurrent=different.png\noutput_delivery=file\ndiff_size=50x50\ncolors=0,0,0:1299;0,255,0:301;255,255,255:900\nerror=none\n"
        },
        {
            "input": {
                "reference_image": "ref.png",
                "current_image": "tall-different.png",
                "highlight_color": "#FF00FF",
                "output_delivery": "file"
            },
            "expected_output": "reference=ref.png\ncurrent=tall-different.png\noutput_delivery=file\ndiff_size=50x80\ncolors=0,0,0:1299;255,0,255:1601;255,255,255:1100\nerror=none\n"
        },
        {
            "input": {
                "reference_image": "ref.png",
                "current_image": "different.png",
                "highlight_color": "#ff00ff",
                "output_delivery": "buffer"
            },
            "expected_output": "reference=ref.png\ncurrent=different.png\noutput_delivery=buffer\n[PNG binary header signature]\ndiff_size=50x50\ncolors=0,0,0:1299;255,0,255:301;255,255,255:900\nerror=none\n"
        }
    ]
}
```

---

### Feature 4: Diff Generation Mode Conflict

**As a developer**, I want to receive a clear validation result when diff generation is requested with mutually exclusive modes, so I can avoid producing ambiguous diff images.

**Expected Behavior / Usage:**

The input is a diff-generation request that simultaneously enables exact pixel matching and perceptual color tolerance. These options are mutually exclusive for diff generation. The output is a normalized, language-neutral error with the conflicting option names on a separate line.

**Test Cases:** `rcb_tests/public_test_cases/feature4_diff_option_conflict.json`

```json
{
    "description": "Rejects a diff-generation request that asks for strict pixel matching and perceptual tolerance at the same time, because those modes are mutually exclusive.",
    "cases": [
        {
            "input": {
                "reference_image": "ref.png",
                "current_image": "different.png",
                "highlight_color": "#ff00ff",
                "output_delivery": "file",
                "diff_options": {
                    "strict_pixel_match": true,
                    "color_tolerance": 9000
                }
            },
            "expected_output": "error=conflicting_comparison_options\noptions=strict_pixel_match,color_tolerance\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_image_comparison.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_image_comparison@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- reference the diff_size parsing logic from the graphics_auditor.py decorators
- consult the legacy diff_engine module for the exact key used
