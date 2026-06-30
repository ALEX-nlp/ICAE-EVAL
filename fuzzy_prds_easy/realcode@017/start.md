## Product Requirement Document

# DOM Ripple Effect Adapter - Standardized Input/Output Contract

## Project Goal

Build a DOM ripple-effect library that allows developers to add configurable material-style pointer feedback to UI elements without manually calculating geometry, generating effect DOM, or handling host-runtime lifecycle differences.

---

## Background & Problem

Without this library/tool, developers are forced to attach pointer listeners, compute element-relative origins, calculate the radius needed to cover a target rectangle, create and style temporary DOM nodes, and integrate those nodes with multiple host runtime lifecycle conventions. This leads to repetitive code, inconsistent visual feedback, brittle browser-specific style handling, and maintenance issues when projects need both modern and legacy runtime support.

With this library/tool, developers configure a reusable ripple behavior once and receive predictable DOM output, activation semantics, geometry calculations, and runtime-compatible lifecycle registration.

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

### Feature 1: Built-In Effect Defaults

**As a developer**, I want to use a complete default effect configuration when I do not provide overrides, so I can apply a predictable ripple experience with no setup.

**Expected Behavior / Usage:**

The adapter accepts an empty input object and reports the full default configuration as newline-delimited key/value stdout. The output includes the directive label, visual color, starting and ending opacity, movement and dissolve [a specific CSS transition duration in milliseconds — verify with the Design System]s, [a specific enumeration for animation timing functions] curve, cancellation delay, activation mode, generated container tag, disabled handling, disabled-attribute handling, and event propagation behavior.

**Test Cases:** `rcb_tests/public_test_cases/feature1_default_configuration.json`

```json
{
  "description": "Reports the complete built-in configuration used when no caller overrides are supplied.",
  "cases": [
    {
      "input": {},
      "expected_output": "directive=wave\ncolor=currentColor\ninitialOpacity=0.2\nfinalOpacity=0.1\n[a specific CSS transition duration in milliseconds — verify with the Design System]=[a specific CSS transition duration in milliseconds — verify with the Design System]\n[a specific list of animation time intervals]=[a specific list of animation time intervals]\n[a specific enumeration for animation timing functions]=[a specific enumeration for animation timing functions]\ncancellationPeriod=75\ntrigger=auto\ntagName=div\ndisabled=false\nrespectDisabledAttribute=true\nstopPropagation=false\n"
    }
  ]
}
```

---

### Feature 2: Activation Trigger Mode Classification

**As a developer**, I want to know how an activation setting will be interpreted, so I can wire ordinary, automatic, disabled, and named activators correctly.

**Expected Behavior / Usage:**

The adapter accepts an object containing a single activation setting. The stdout classifies the setting as automatic behavior, boolean behavior, or a named identifier. Only a string value other than the automatic sentinel is classified as an identifier and marked as requiring a matching named activator; boolean values and automatic behavior do not require a matching named activator.

**Test Cases:** `rcb_tests/public_test_cases/feature2_trigger_modes.json`

```json
{
  "description": "Classifies activation trigger settings as automatic behavior, boolean behavior, or a named identifier that requires a matching activator.",
  "cases": [
    {
      "input": {
        "trigger": "auto"
      },
      "expected_output": "trigger=auto\nkind=automatic\nrequiresMatchingNamedActivator=false\n"
    },
    {
      "input": {
        "trigger": true
      },
      "expected_output": "trigger=true\nkind=boolean\nrequiresMatchingNamedActivator=false\n"
    },
    {
      "input": {
        "trigger": false
      },
      "expected_output": "trigger=false\nkind=boolean\nrequiresMatchingNamedActivator=false\n"
    },
    {
      "input": {
        "trigger": "stringId"
      },
      "expected_output": "trigger=stringId\nkind=identifier\nrequiresMatchingNamedActivator=true\n"
    }
  ]
}
```

---

### Feature 3: Effect Boundary Marking

**As a developer**, I want to mark an element as a ripple boundary, so I can route pointer activations to the correct decorated element.

**Expected Behavior / Usage:**

The adapter accepts an element tag and activation setting, creates a boundary element, applies the boundary marker, and prints the resulting tag and boundary value. Automatic activation produces a generic true boundary marker. A named activation setting stores that same identifier as the boundary value, allowing matching activators to target the correct boundary.

**Test Cases:** `rcb_tests/public_test_cases/feature3_boundary_marker.json`

```json
{
  "description": "Marks an effect boundary so ordinary activation uses a generic marker and named activation stores the requested identifier.",
  "cases": [
    {
      "input": {
        "elementTag": "div",
        "trigger": "auto"
      },
      "expected_output": "tag=div\nboundary=true\n"
    },
    {
      "input": {
        "elementTag": "div",
        "trigger": "stringId"
      },
      "expected_output": "tag=div\nboundary=stringId\n"
    }
  ]
}
```

---

### Feature 4: Pointer Origin Coordinates

**As a developer**, I want to convert page pointer coordinates into element-relative coordinates, so I can start the visual effect at the point the user interacted with.

**Expected Behavior / Usage:**

The adapter accepts a pointer position and the target element box offset. It subtracts the element top-left position from the pointer position and prints the relative x and y coordinates. Coordinates are not clamped: a pointer outside the element may produce negative relative coordinates.

**Test Cases:** `rcb_tests/public_test_cases/feature4_relative_pointer.json`

```json
{
  "description": "Converts a page pointer position into coordinates relative to the decorated element's top-left corner, preserving negative coordinates outside the element.",
  "cases": [
    {
      "input": {
        "pointer": {
          "x": 125,
          "y": 150
        },
        "elementBox": {
          "top": 50,
          "left": 100
        }
      },
      "expected_output": "relativeX=25\nrelativeY=100\n"
    },
    {
      "input": {
        "pointer": {
          "x": 25,
          "y": 25
        },
        "elementBox": {
          "top": 30,
          "left": 30
        }
      },
      "expected_output": "relativeX=-5\nrelativeY=-5\n"
    }
  ]
}
```

---

### Feature 5: Ripple Coverage Radius

**As a developer**, I want to calculate how large the ripple must grow from its origin, so I can ensure the effect reaches every corner of the element.

**Expected Behavior / Usage:**

The adapter accepts an origin point and an element size. It computes the Euclidean distance from the origin to each of the four element corners, selects the largest distance as the required radius, and prints both radius and diameter. Floating-point results are printed as raw numeric strings.

**Test Cases:** `rcb_tests/public_test_cases/feature5_coverage_radius.json`

```json
{
  "description": "Calculates the ripple radius needed for an origin point to reach the farthest corner of an element rectangle.",
  "cases": [
    {
      "input": {
        "origin": {
          "x": 25,
          "y": 25
        },
        "elementSize": {
          "width": 100,
          "height": 100
        }
      },
      "expected_output": "radius=106.06601717798213\ndiameter=212.13203435596427\n"
    },
    {
      "input": {
        "origin": {
          "x": 25,
          "y": 25
        },
        "elementSize": {
          "width": 30,
          "height": 30
        }
      },
      "expected_output": "radius=35.35533905932738\ndiameter=70.71067811865476\n"
    }
  ]
}
```

---

### Feature 6: Generated Clipping Container

**As a developer**, I want to create the DOM container that clips and positions the ripple, so I can render the effect without intercepting pointer input or overflowing its boundary.

**Expected Behavior / Usage:**

The adapter accepts a requested element tag and creates the clipping container with that tag. Stdout prints the generated tag, attributes, and inline style. The container fills its boundary, is absolutely positioned, hides overflow, ignores pointer events, and includes a radial mask style used for browser-compatible clipping.

**Test Cases:** `rcb_tests/public_test_cases/feature6_container_element.json`

```json
{
  "description": "Creates the clipping container for the visual effect using the requested tag and fixed positioning and masking styles.",
  "cases": [
    {
      "input": {
        "tag": "div"
      },
      "expected_output": "tag=div\nattributes=style=top: 0px; left: 0px; width: 100%; height: 100%; display: block; position: absolute; border-radius: undefined undefined undefined undefined; overflow: hidden; pointer-events: none; webkit-mask-image: -webkit-radial-gradient(white, black);\nstyle=top: 0px; left: 0px; width: 100%; height: 100%; display: block; position: absolute; border-radius: undefined undefined undefined undefined; overflow: hidden; pointer-events: none; webkit-mask-image: -webkit-radial-gradient(white, black);\n"
    },
    {
      "input": {
        "tag": "span"
      },
      "expected_output": "tag=span\nattributes=style=top: 0px; left: 0px; width: 100%; height: 100%; display: block; position: absolute; border-radius: undefined undefined undefined undefined; overflow: hidden; pointer-events: none; webkit-mask-image: -webkit-radial-gradient(white, black);\nstyle=top: 0px; left: 0px; width: 100%; height: 100%; display: block; position: absolute; border-radius: undefined undefined undefined undefined; overflow: hidden; pointer-events: none; webkit-mask-image: -webkit-radial-gradient(white, black);\n"
    }
  ]
}
```

---

### Feature 7: Generated Ripple Element

**As a developer**, I want to create the animated circular element from geometry and visual options, so I can render the expanding visual effect at the correct place.

**Expected Behavior / Usage:**

The adapter accepts an origin, size, and visual option object, then prints the generated element tag, attributes, and inline style. The element is a circle positioned at the supplied origin with the supplied size, starts scaled to zero, and uses inline transition styles derived from the visual timing options supplied in the input.

**Test Cases:** `rcb_tests/public_test_cases/feature7_wave_element.json`

```json
{
  "description": "Creates the animated circular visual element at the requested origin and size, applying the supplied visual timing options as inline styles.",
  "cases": [
    {
      "input": {
        "origin": {
          "x": 0,
          "y": 0
        },
        "size": 0,
        "options": {}
      },
      "expected_output": "tag=div\nattributes=style=position: absolute; width: 0px; height: 0px; top: 0px; left: 0px; border-radius: 50%; transform: translate(-50%,-50%) scale(0); transition: transform undefineds undefined, opacity undefineds undefined;\nstyle=position: absolute; width: 0px; height: 0px; top: 0px; left: 0px; border-radius: 50%; transform: translate(-50%,-50%) scale(0); transition: transform undefineds undefined, opacity undefineds undefined;\n"
    }
  ]
}
```

---

### Feature 8: Host Runtime Lifecycle Compatibility

**As a developer**, I want to detect the host UI runtime family, so I can register mount and update behavior using names the runtime understands.

**Expected Behavior / Usage:**

The adapter accepts a neutral runtime family label and prints the detected family plus the lifecycle phase names used for mount and update behavior. A modern application shape maps to modern phase names, while a legacy shape maps to legacy phase names, allowing the same effect behavior to attach in either host environment.

**Test Cases:** `rcb_tests/public_test_cases/feature8_runtime_family.json`

```json
{
  "description": "Detects whether the host UI runtime uses the modern or legacy plugin shape and reports the lifecycle phase names required by that runtime.",
  "cases": [
    {
      "input": {
        "runtime": "modern"
      },
      "expected_output": "runtime=modern\nfamily=modern\nmountPhase=mounted\nupdatePhase=updated\n"
    },
    {
      "input": {
        "runtime": "legacy"
      },
      "expected_output": "runtime=legacy\nfamily=legacy\nmountPhase=inserted\nupdatePhase=componentUpdated\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_default_configuration.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_default_configuration@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same naming convention as the legacy event listeners
