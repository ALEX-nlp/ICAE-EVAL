## Product Requirement Document

# Cross-Platform Image Resource Metadata Toolkit - Naming, Color, Size & Platform Lookups

## Project Goal

Build a small utility library that resolves the metadata needed when packaging image assets for multiple application platforms, so developers can validate resource names, interpret color and size annotations, classify images, and look up per-platform output locations without re-implementing these fiddly rules for every project.

---

## Background & Problem

When the same image is shipped to several application platforms, a build tool must answer a handful of small but error-prone questions: Is this file name a legal resource identifier on the target platform? What color does this textual annotation represent? What pixel size does this annotation request? Is this image a scalable vector or a raster bitmap? Where should the unscaled "original" of this image be written for each platform?

Without a shared library, every project re-codes these rules slightly differently, producing inconsistent validation, subtle color/size parsing bugs, and platform output mistakes. This toolkit centralizes the rules behind a single command interface: each request is a JSON object naming an operation plus its arguments, and each response is a short, plain-text result printed to standard output.

The program reads exactly one JSON object from standard input and writes the result for that one operation to standard output. Each operation is described below as an independent functional point.

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

### Feature 1: Resource Name Validation

**As a developer**, I want to check whether a file's base name is a legal resource identifier, so I can reject bad asset names early in the build.

**Expected Behavior / Usage:**

The operation `validate_filename` takes a `filename` argument. Only the final path component is considered, and its extension is removed before validation (any leading directory and the extension are ignored). The remaining base name is legal only if **all** of these hold: it begins with a lowercase ASCII letter (`a`–`z`); every other character is a lowercase letter, a digit (`0`–`9`), or an underscore (`_`); it is at least two characters long; and it does not end with an underscore. Any uppercase letter, leading digit, leading underscore, trailing underscore, space, hyphen, or other punctuation makes it illegal. Output is a single line `valid=True` or `valid=False`.

*1.1 Legal identifiers — names that satisfy every rule*

A base name that starts with a lowercase letter and uses only lowercase letters, digits, and interior underscores (not at the end) is accepted.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_valid_names.json`

```json
{
    "description": "Validate that a resource identifier (derived from the file name, ignoring any directory part and extension) conforms to the naming rules: it starts with a lowercase letter, contains only lowercase letters, digits and underscores, is at least two characters long, and does not end with an underscore. These inputs all satisfy the rules.",
    "cases": [
        {"input": {"op": "validate_filename", "filename": "one.png"}, "expected_output": "valid=True"},
        {"input": {"op": "validate_filename", "filename": "o1.png"}, "expected_output": "valid=True"}
    ]
}
```

*1.2 Illegal identifiers — names that break at least one rule*

A base name that begins with a digit or uppercase letter, contains a space/hyphen, starts with an underscore, or ends with an underscore is rejected.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_invalid_names.json`

```json
{
    "description": "Validate that identifiers breaking the naming rules are rejected: starting with a digit, containing an uppercase letter, containing a hyphen or space, starting with an underscore, or ending with an underscore. Each of these inputs violates at least one rule.",
    "cases": [
        {"input": {"op": "validate_filename", "filename": "1one.png"}, "expected_output": "valid=False"},
        {"input": {"op": "validate_filename", "filename": "O1.png"}, "expected_output": "valid=False"}
    ]
}
```

---

### Feature 2: Color Annotation Parsing

**As a developer**, I want to turn a textual color annotation into a concrete color value, so I can tint or fill images consistently.

**Expected Behavior / Usage:**

The operation `parse_color` takes a `value` argument and resolves it to an 8-digit alpha-red-green-blue (ARGB) color. Output is a single line `argb=AARRGGBB`, where `AARRGGBB` is the uppercase 8-character hexadecimal color (alpha, red, green, blue, two hex digits each). If the value cannot be resolved to a color, output `[a specific output string for null values]`.

*2.1 Hexadecimal colors — direct hex notation*

A hex string (optionally prefixed with `#`) is parsed. A 6-hex-digit form specifies red, green, blue and is treated as fully opaque, so the alpha byte becomes `FF`. An 8-hex-digit form specifies alpha, red, green, blue explicitly and keeps that alpha.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_hex_colors.json`

```json
{
    "description": "Parse a color given as a hexadecimal string into its 8-digit alpha-red-green-blue representation. A 6-digit form is treated as fully opaque (alpha forced to FF), and an 8-digit form (with or without a leading '#') keeps its explicit alpha. Output is the uppercase 8-character ARGB hex.",
    "cases": [
        {"input": {"op": "parse_color", "value": "#abcdef"}, "expected_output": "argb=FFABCDEF"},
        {"input": {"op": "parse_color", "value": "#12345678"}, "expected_output": "argb=12345678"}
    ]
}
```

*2.2 Named colors — well-known English color names*

A recognized English color name resolves to its standard opaque value. Name matching is case-insensitive, and both the `-gray` and `-grey` spellings of the affected names are accepted and resolve to the same value.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_named_colors.json`

```json
{
    "description": "Parse a color given by a well-known English color name (case-insensitive) into its opaque 8-digit alpha-red-green-blue hex value. Both the '-gray' and '-grey' spellings of the relevant names are accepted and resolve to the same value.",
    "cases": [
        {"input": {"op": "parse_color", "value": "Red"}, "expected_output": "argb=FFFF0000"},
        {"input": {"op": "parse_color", "value": "Green"}, "expected_output": "argb=FF008000"}
    ]
}
```

---

### Feature 3: Size Annotation Parsing

**As a developer**, I want to interpret a textual size annotation as width and height, so I can set base dimensions for an asset.

**Expected Behavior / Usage:**

The operation `parse_size` takes a `value` argument. The value holds one or two integers separated by a comma `,` or a semicolon `;`. When two integers are present, the first is the width and the second is the height. When only one integer is present, it is used for both width and height. Output is two lines, `width=<w>` then `height=<h>`. If the value is absent or empty, no size is produced and output is the single line `size=null`.

*3.1 Two-component sizes — width and height from a separated pair*

A `W,H` or `W;H` string yields the width and the height as written.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_dimensions.json`

```json
{
    "description": "Parse a size string of the form 'W,H' or 'W;H' (comma or semicolon separated) into its width and height components. Output reports the two numeric dimensions.",
    "cases": [
        {"input": {"op": "parse_size", "value": "1,2"}, "expected_output": "width=1\nheight=2"},
        {"input": {"op": "parse_size", "value": "1;2"}, "expected_output": "width=1\nheight=2"}
    ]
}
```

*3.2 Empty or absent size — no value to parse*

An empty string or a missing value yields no size.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_empty.json`

```json
{
    "description": "Parsing a size from an empty or absent string yields no size. Output indicates the absence of a parsed value.",
    "cases": [
        {"input": {"op": "parse_size", "value": null}, "expected_output": "size=null"},
        {"input": {"op": "parse_size", "value": ""}, "expected_output": "size=null"}
    ]
}
```

---

### Feature 4: Platform Original-Resource Lookup

**As a developer**, I want to look up where a platform expects the unscaled "original" copy of an image and what scale it corresponds to, so I can place assets in the right output folder.

**Expected Behavior / Usage:**

The operation `platform_original` takes a `platform` argument (a short platform key, matched case-insensitively). For a recognized platform it returns the destination folder and the scale factor of the original resource, printed as two lines: `path=<folder>` then `scale=<factor>`. The folder may be empty for platforms that write to the package root (the line is then `path=` with nothing after the equals sign). Scale factors are printed with one decimal place (for example `[the specific decimal format for scale factors]` or `4.0`); most platforms use `[the specific decimal format for scale factors]`, while one uses a higher fixed scale of `4.0`. Recognized keys include `android` (folder `drawable`, scale `[the specific decimal format for scale factors]`), `ios` (folder `Resources`, scale `[the specific decimal format for scale factors]`), `uwp` (empty folder, scale `[the specific decimal format for scale factors]`), and `wpf` (empty folder, scale `4.0`). For an unrecognized key, output the single line `result=null`.

*4.1 Recognized platforms — folder and scale of the original*

A known platform key returns its destination folder and scale. Matching is case-insensitive, so the same key in any letter casing resolves identically.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_folder.json`

```json
{
    "description": "Look up the default output location for a target platform's original (unscaled) resource. Output reports the destination folder and the associated scale factor for the recognized platform key.",
    "cases": [
        {"input": {"op": "platform_original", "platform": "android"}, "expected_output": "path=drawable\nscale=[the specific decimal format for scale factors]"},
        {"input": {"op": "platform_original", "platform": "ios"}, "expected_output": "path=Resources\nscale=[the specific decimal format for scale factors]"},
        {"input": {"op": "platform_original", "platform": "uwp"}, "expected_output": "path=\nscale=[the specific decimal format for scale factors]"},
        {"input": {"op": "platform_original", "platform": "wpf"}, "expected_output": "path=\nscale=4.0"}
    ]
}
```

*4.2 Unrecognized platforms — no location*

A platform key that does not match any known platform yields no result.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_unknown_platform.json`

```json
{
    "description": "An unrecognized platform key yields no result. Output indicates the absence of a resolved location.",
    "cases": [
        {"input": {"op": "platform_original", "platform": "ANDROID123"}, "expected_output": "result=null"},
        {"input": {"op": "platform_original", "platform": "Cars"}, "expected_output": "result=null"}
    ]
}
```

---

### Feature 5: Vector Image Classification

**As a developer**, I want to know whether an image is a scalable vector or a raster bitmap, so I can choose the right processing path.

**Expected Behavior / Usage:**

The operation `is_vector` takes a `filename` argument and reports whether the file is a vector image, judged solely by its extension. Only the `.svg` extension counts as a vector, matched case-insensitively; every other extension, a name with no extension, and an empty or absent name are all non-vector. The operation never fails on empty or missing input. Output is a single line `vector=True` or `vector=False`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_by_extension.json`

```json
{
    "description": "Determine whether an image file is a vector image based purely on its file-name extension. Only the '.svg' extension (matched case-insensitively) counts as a vector; raster extensions do not. Output reports the boolean determination.",
    "cases": [
        {"input": {"op": "is_vector", "filename": "image.svg"}, "expected_output": "vector=True"},
        {"input": {"op": "is_vector", "filename": "image.png"}, "expected_output": "vector=False"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON command object from standard input (`{"op": <operation>, ...arguments}`) and prints the result for that one operation to standard output, matching the per-feature contracts above.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same key resolution logic as used in the global_config module
- use the same output ordering convention as the path_resolution helper
