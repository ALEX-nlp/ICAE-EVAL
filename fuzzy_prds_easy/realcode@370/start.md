## Product Requirement Document

# Lie Group Algebra Kernel for Rotations and Rigid Motions — Composition, Exp/Log Maps, Group Actions, and Analytic Jacobians

## Project Goal

Build a numeric kernel for the algebra of rotations and rigid motions that lets developers compose transformations, move between a transformation and its minimal local coordinates, transform points, and obtain the analytic derivatives of every operation, without re-deriving the matrix/quaternion bookkeeping or the calculus on curved spaces by hand.

---

## Background & Problem

Rotations and rigid motions form smooth groups: composing two of them yields another, every one has an inverse, and there is an identity that does nothing. Each group has a flat tangent space of minimal coordinates around the identity (one number for a planar rotation, three for a spatial rotation, three for a planar rigid motion, six for a spatial rigid motion). Two maps connect the curved group and its flat tangent space: an exponential map turning tangent coordinates into a group element, and a logarithmic map doing the reverse. On top of these sit the right/left increment and difference operators (apply a tangent step to an element, or recover the tangent step between two elements), the action of an element on a point, the adjoint that transports tangent vectors across an element, geodesic interpolation, and the analytic Jacobians of all of the above expressed in the local tangent frames.

Without a dedicated kernel, developers re-implement quaternion and matrix products, small-angle series, and error-prone derivative formulas in every project, with subtle sign and ordering bugs. This kernel provides one consistent contract for four groups — planar rotation, spatial rotation, planar rigid motion, and spatial rigid motion — so that estimation, control and geometry code can rely on uniform, differentiable building blocks.

This document specifies the kernel purely in terms of inputs and outputs. Four groups are referenced by short tokens: `SO2` (rotation of the plane, 1 degree of freedom), `SO3` (rotation of space, 3 degrees of freedom), `SE2` (rigid motion of the plane, 3 degrees of freedom), and `SE3` (rigid motion of space, 6 degrees of freedom).

### Coordinate conventions (shared by all features)

A group element is supplied in a request through **natural construction parameters** under a field whose value is a list of numbers:
- `SO2`: one angle.
- `SO3`: three successive axis-rotation angles applied as a rotation about the first (X) axis, then the second (Y) axis, then the third (Z) axis (equivalently the rotation Rz(third)·Ry(second)·Rx(first)).
- `SE2`: a translation pair followed by one angle.
- `SE3`: a translation triple followed by three axis-rotation angles using the same convention as `SO3`.

A group element is **emitted** as its canonical coordinate vector:
- `SO2`: the pair (cosine, sine) of the angle.
- `SO3`: a unit quaternion ordered as the three vector components then the scalar.
- `SE2`: the translation pair followed by (cosine, sine).
- `SE3`: the translation triple followed by the unit quaternion (vector part then scalar).

A **tangent vector** (supplied or emitted) is a list whose length equals the group's degrees of freedom:
- `SO2`: one rotation rate.
- `SO3`: three rotation-rate components.
- `SE2`: two translation-rate components followed by one rotation rate.
- `SE3`: three translation-rate components followed by three rotation-rate components.

**Numeric output format.** Every number is rendered in fixed-point notation with six digits after the decimal point. Values whose magnitude is below one half of a millionth are rendered as a clean [a specific magnitude threshold for rendering positives] so that the sign of numerical noise never appears. Vectors are emitted on a single labelled line as `label: v0 v1 ...`. Matrices are emitted as a label line `label:` followed by one line per row, the row's entries separated by single spaces. A trailing newline terminates every emitted line.

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

### Feature 1: Exponential and Logarithmic Maps

**As a developer**, I want to convert between a transformation and its minimal local coordinates, so I can parametrize, optimize over, and reconstruct group elements without leaving the group.

**Expected Behavior / Usage:**

*1.1 Exponential map — tangent coordinates to a group element*

The request names a group and supplies a tangent vector of matching degrees of freedom under `tau`. The output is the group element produced by the exponential map, rendered as its canonical coordinate vector. A zero tangent maps to the identity element.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_exp.json`

```json
{
    "description": "Map a tangent-space coordinate vector to a group element through the exponential map. The request names a group and supplies a tangent vector whose length equals the group's degrees of freedom (a single rotation rate for planar rotation; three rotation-rate components for spatial rotation; for the planar and spatial rigid-motion groups the translation-rate components come first followed by the rotation-rate components). The output is the resulting element's canonical coordinate vector: for planar rotation the pair (cosine, sine) of the angle; for spatial rotation a unit quaternion ordered as the three vector components then the scalar; for planar rigid motion the translation pair followed by (cosine, sine); for spatial rigid motion the translation triple followed by the unit quaternion.",
    "cases": [
        {"input": {"group": "SO2", "op": "exp", "tau": [0.5]}, "expected_output": "element: 0.877583 0.479426\n"},
        {"input": {"group": "SO3", "op": "exp", "tau": [0.2, -0.1, 0.4]}, "expected_output": "element: 0.099127 -0.049564 0.198255 0.973865\n"}
    ]
}
```

*1.2 Logarithmic map — group element to tangent coordinates*

The request names a group and supplies an element through its natural construction parameters under `x`. The output is the tangent vector returned by the logarithmic map, the inverse of the exponential map. The identity element maps to the zero tangent.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_log.json`

```json
{
    "description": "Map a group element to its tangent-space coordinate vector through the logarithmic map (the inverse of the exponential map). The request names a group and supplies the element through natural construction parameters: a single angle for planar rotation; three successive axis-rotation angles for spatial rotation applied as a rotation about the first axis, then the second, then the third; a translation pair plus an angle for planar rigid motion; a translation triple plus three axis-rotation angles for spatial rigid motion. The output is the tangent coordinate vector whose length equals the group's degrees of freedom.",
    "cases": [
        {"input": {"group": "SO2", "op": "log", "x": [0.7]}, "expected_output": "tangent: 0.700000\n"}
    ]
}
```

---

### Feature 2: Composition, Inversion, and Relative Transformation

**As a developer**, I want to combine transformations, undo them, and express one relative to another, so I can chain frames and reason about relative geometry.

**Expected Behavior / Usage:**

*2.1 Inverse — the undoing element*

The request names a group and supplies one element under `x`. The output is the inverse element (the one that composes with the original on either side to give the identity), as its canonical coordinate vector.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_inverse.json`

```json
{
    "description": "Compute the group inverse of an element, i.e. the element that composes with the original on either side to yield the identity. The request names a group and supplies the element through its natural construction parameters. The output is the inverse element's canonical coordinate vector.",
    "cases": [
        {"input": {"group": "SO2", "op": "inverse", "x": [0.7]}, "expected_output": "element: 0.764842 -0.644218\n"}
    ]
}
```

*2.2 Composition — the group product*

The request names a group and supplies two elements under `x` and `y`. The output is their composite (the second applied after the first), as its canonical coordinate vector.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_compose.json`

```json
{
    "description": "Compose two group elements with the group product (apply the second after the first) and return the composite element. The request names a group and supplies two elements through their natural construction parameters. The output is the composite element's canonical coordinate vector.",
    "cases": [
        {"input": {"group": "SO2", "op": "compose", "x": [0.7], "y": [2]}, "expected_output": "element: -0.904072 0.427380\n"}
    ]
}
```

*2.3 Relative transformation (between) — from one element to another*

The request names a group and supplies two elements under `x` and `y`. The output is the relative element defined as the inverse of the first composed with the second, as its canonical coordinate vector. The relative transformation of an element with itself is the identity.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_between.json`

```json
{
    "description": "Compute the relative transformation from a first element to a second element, defined as the inverse of the first composed with the second. The request names a group and supplies two elements through their natural construction parameters. The output is the relative element's canonical coordinate vector.",
    "cases": [
        {"input": {"group": "SO2", "op": "between", "x": [0.7], "y": [2]}, "expected_output": "element: 0.267499 0.963558\n"}
    ]
}
```

---

### Feature 3: Tangent Increments (Right and Left Plus)

**As a developer**, I want to nudge a transformation by a tangent step on either side, so I can apply local corrections in the frame of the element or in the global frame.

**Expected Behavior / Usage:**

*3.1 Right plus — increment on the right*

The request names a group, an element under `x`, and a tangent vector under `tau`. The result exponentiates the tangent and composes it after the element (element first). The output is the resulting element's canonical coordinate vector. Adding a zero tangent returns the element unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_rplus.json`

```json
{
    "description": "Apply a tangent-space increment to a group element on the right: exponentiate the increment to an element and compose it after the original (original first). The request names a group and supplies the base element through its natural construction parameters together with a tangent vector of matching degrees of freedom. The output is the resulting element's canonical coordinate vector.",
    "cases": [
        {"input": {"group": "SO2", "op": "rplus", "x": [0.7], "tau": [0.5]}, "expected_output": "element: 0.362358 0.932039\n"}
    ]
}
```

*3.2 Left plus — increment on the left*

The request names a group, an element under `x`, and a tangent vector under `tau`. The result exponentiates the tangent and composes it before the element (increment first). The output is the resulting element's canonical coordinate vector.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_lplus.json`

```json
{
    "description": "Apply a tangent-space increment to a group element on the left: exponentiate the increment to an element and compose it before the original (increment first). The request names a group and supplies the base element through its natural construction parameters together with a tangent vector of matching degrees of freedom. The output is the resulting element's canonical coordinate vector.",
    "cases": [
        {"input": {"group": "SO2", "op": "lplus", "x": [0.7], "tau": [0.5]}, "expected_output": "element: 0.362358 0.932039\n"}
    ]
}
```

---

### Feature 4: Tangent Differences (Right and Left Minus)

**As a developer**, I want to recover the tangent step between two transformations, so I can measure residuals and errors as minimal local coordinates.

**Expected Behavior / Usage:**

*4.1 Right minus — right difference*

The request names a group and supplies two elements under `x` and `y`. The output is the tangent vector whose right increment carries the second element onto the first, equivalently the logarithm of the inverse of the second composed with the first. The difference of an element with itself is the zero tangent.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_rminus.json`

```json
{
    "description": "Compute the right difference between two elements: the tangent vector whose right-side increment carries the second element onto the first, equivalently the logarithm of the inverse of the second composed with the first. The request names a group and supplies two elements through their natural construction parameters. The output is the tangent coordinate vector of matching degrees of freedom.",
    "cases": [
        {"input": {"group": "SO2", "op": "rminus", "x": [0.7], "y": [2]}, "expected_output": "tangent: -1.300000\n"}
    ]
}
```

*4.2 Left minus — left difference*

The request names a group and supplies two elements under `x` and `y`. The output is the tangent vector equal to the logarithm of the first composed with the inverse of the second.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_lminus.json`

```json
{
    "description": "Compute the left difference between two elements, equivalently the logarithm of the first composed with the inverse of the second. The request names a group and supplies two elements through their natural construction parameters. The output is the tangent coordinate vector of matching degrees of freedom.",
    "cases": [
        {"input": {"group": "SO2", "op": "lminus", "x": [0.7], "y": [2]}, "expected_output": "tangent: -1.300000\n"}
    ]
}
```

---

### Feature 5: Group Action on a Point

**As a developer**, I want to transform a coordinate point by a group element, so I can move geometry between frames.

**Expected Behavior / Usage:**

The request names a group, supplies an element under `x`, and a point under `p` whose dimension is two for the planar groups and three for the spatial groups. A rotation group rotates the point about the origin; a rigid-motion group rotates and then translates it. The output is the transformed point's coordinates.

**Test Cases:** `rcb_tests/public_test_cases/feature5_act.json`

```json
{
    "description": "Apply a group element to a point as a rigid transformation: rotation groups rotate the point about the origin, rigid-motion groups rotate and then translate it. The request names a group, supplies the element through its natural construction parameters, and supplies a point whose dimension is two for the planar groups and three for the spatial groups. The output is the transformed point's coordinates.",
    "cases": [
        {"input": {"group": "SO2", "op": "act", "x": [0.7], "p": [1.0, 2.0]}, "expected_output": "point: -0.523593 2.173902\n"},
        {"input": {"group": "SO3", "op": "act", "x": [0.3, -0.5, 0.8], "p": [1.0, -2.0, 0.5]}, "expected_output": "point: 2.125916 -0.765594 0.379932\n"}
    ]
}
```

---

### Feature 6: Adjoint

**As a developer**, I want the linear map that transports a tangent vector across an element, so I can convert between the right and left tangent representations of the same motion.

**Expected Behavior / Usage:**

The request names a group and supplies one element under `x`. The output is the square adjoint matrix of the element, emitted one row per line, whose dimension equals the group's degrees of freedom. The adjoint of the identity is the identity matrix.

**Test Cases:** `rcb_tests/public_test_cases/feature6_adjoint.json`

```json
{
    "description": "Compute the adjoint matrix of a group element, the linear map that transports tangent vectors from the right tangent space to the left tangent space of the element. The request names a group and supplies the element through its natural construction parameters. The output is the square adjoint matrix, one row per line, whose dimension equals the group's degrees of freedom.",
    "cases": [
        {"input": {"group": "SO2", "op": "adjoint", "x": [0.7]}, "expected_output": "adjoint:\n1.000000\n"}
    ]
}
```

---

### Feature 7: Geodesic Interpolation

**As a developer**, I want to blend between two transformations along the shortest path, so I can produce smooth intermediate poses.

**Expected Behavior / Usage:**

The request names a group, supplies two elements under `x` and `y`, and a blending factor under `t`. A factor of zero returns the first element, a factor of one returns the second element, and intermediate factors return the element a corresponding fraction of the way along the geodesic. A factor strictly outside the closed interval from zero to one is rejected and the kernel reports a neutral error line `error: factor_out_of_range` followed by a newline. A successful result is the interpolated element's canonical coordinate vector.

**Test Cases:** `rcb_tests/public_test_cases/feature7_interpolate.json`

```json
{
    "description": "Interpolate along the shortest path between two group elements by a factor between zero and one inclusive: a factor of zero returns the first element, a factor of one returns the second element, and intermediate factors return the element a corresponding fraction of the way along the geodesic. The request names a group, supplies two elements through their natural construction parameters, and supplies the factor. A factor outside the closed unit interval is rejected with a neutral error line. The successful output is the interpolated element's canonical coordinate vector.",
    "cases": [
        {"input": {"group": "SO3", "op": "interpolate", "x": [0.3, -0.5, 0.8], "y": [1.2, 0.4, -0.7], "t": 0}, "expected_output": "element: 0.228624 -0.168931 0.407129 0.868009\n"},
        {"input": {"group": "SO3", "op": "interpolate", "x": [0.3, -0.5, 0.8], "y": [1.2, 0.4, -0.7], "t": 0.5}, "expected_output": "element: 0.448702 -0.114120 0.013599 0.886261\n"}
    ]
}
```

---

### Feature 8: Analytic Jacobians

**As a developer**, I want the analytic derivative of each operation in the local tangent frames, so I can build optimizers and filters without numerical differentiation.

**Expected Behavior / Usage:**

Each leaf below performs one operation and additionally returns its analytic Jacobian(s). Every Jacobian is a matrix emitted one row per line. A Jacobian with respect to a group element or a tangent vector is square with dimension equal to the group's degrees of freedom; for the point action the Jacobian with respect to the element has one row per point coordinate and one column per degree of freedom, and the Jacobian with respect to the point is square with dimension equal to the point dimension. The operation result is emitted first (a canonical coordinate vector for element-valued results, a tangent vector for tangent-valued results, or a point for the action), followed by the Jacobian(s) in the order stated for each leaf.

*8.1 Inverse Jacobian*

Returns the inverse element followed by the Jacobian of the inverse with respect to the input element.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_jac_inverse.json`

```json
{
    "description": "Compute the group inverse together with the analytic Jacobian of the inverse operation with respect to the input element, expressed in the local tangent frames. The request names a group and supplies the element through its natural construction parameters. The output is the inverse element's canonical coordinate vector followed by the square Jacobian matrix (one row per line) whose dimension equals the group's degrees of freedom.",
    "cases": [
        {"input": {"group": "SO2", "op": "jac_inverse", "x": [0.7]}, "expected_output": "element: 0.764842 -0.644218\n[various jacobian label prefixes]\n-1.000000\n"}
    ]
}
```

*8.2 Logarithm Jacobian*

Returns the logarithm tangent followed by the Jacobian of the logarithm with respect to the element.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_jac_log.json`

```json
{
    "description": "Compute the logarithm of a group element together with the analytic Jacobian of the logarithm with respect to the element, expressed in the local tangent frame. The request names a group and supplies the element through its natural construction parameters. The output is the tangent coordinate vector followed by the square Jacobian matrix whose dimension equals the group's degrees of freedom.",
    "cases": [
        {"input": {"group": "SO2", "op": "jac_log", "x": [0.7]}, "expected_output": "tangent: 0.700000\n[various jacobian label prefixes]\n1.000000\n"}
    ]
}
```

*8.3 Composition Jacobians*

Returns the composite element followed by the Jacobian with respect to the first element and then the Jacobian with respect to the second element.

**Test Cases:** `rcb_tests/public_test_cases/feature8_3_jac_compose.json`

```json
{
    "description": "Compose two group elements together with the two analytic Jacobians of the product with respect to the first and second elements, expressed in the local tangent frames. The request names a group and supplies two elements through their natural construction parameters. The output is the composite element's canonical coordinate vector followed by the Jacobian with respect to the first element and then the Jacobian with respect to the second element, each a square matrix whose dimension equals the group's degrees of freedom.",
    "cases": [
        {"input": {"group": "SO2", "op": "jac_compose", "x": [0.7], "y": [2]}, "expected_output": "element: -0.904072 0.427380\n[various jacobian label prefixes]\n1.000000\n[various jacobian label prefixes]\n1.000000\n"}
    ]
}
```

*8.4 Relative-transformation Jacobians*

Returns the relative element followed by the Jacobian with respect to the first element and then the Jacobian with respect to the second element.

**Test Cases:** `rcb_tests/public_test_cases/feature8_4_jac_between.json`

```json
{
    "description": "Compute the relative transformation from a first element to a second element together with the two analytic Jacobians of the result with respect to the first and second elements, expressed in the local tangent frames. The request names a group and supplies two elements through their natural construction parameters. The output is the relative element's canonical coordinate vector followed by the Jacobian with respect to the first element and then the Jacobian with respect to the second element.",
    "cases": [
        {"input": {"group": "SO2", "op": "jac_between", "x": [0.7], "y": [2]}, "expected_output": "element: 0.267499 0.963558\n[various jacobian label prefixes]\n-1.000000\n[various jacobian label prefixes]\n1.000000\n"}
    ]
}
```

*8.5 Right-plus Jacobians*

Returns the incremented element followed by the Jacobian with respect to the base element and then the Jacobian with respect to the increment.

**Test Cases:** `rcb_tests/public_test_cases/feature8_5_jac_rplus.json`

```json
{
    "description": "Apply a right tangent-space increment to a group element together with the two analytic Jacobians of the result with respect to the base element and with respect to the increment, expressed in the local tangent frames. The request names a group and supplies the base element through its natural construction parameters together with a tangent vector of matching degrees of freedom. The output is the resulting element's canonical coordinate vector followed by the Jacobian with respect to the element and then the Jacobian with respect to the increment.",
    "cases": [
        {"input": {"group": "SO2", "op": "jac_rplus", "x": [0.7], "tau": [0.5]}, "expected_output": "element: 0.362358 0.932039\n[various jacobian label prefixes]\n1.000000\n[various jacobian label prefixes]\n1.000000\n"}
    ]
}
```

*8.6 Right-minus Jacobians*

Returns the difference tangent followed by the Jacobian with respect to the first element and then the Jacobian with respect to the second element.

**Test Cases:** `rcb_tests/public_test_cases/feature8_6_jac_rminus.json`

```json
{
    "description": "Compute the right difference between two elements together with the two analytic Jacobians of the difference with respect to the first and second elements, expressed in the local tangent frames. The request names a group and supplies two elements through their natural construction parameters. The output is the tangent coordinate vector followed by the Jacobian with respect to the first element and then the Jacobian with respect to the second element.",
    "cases": [
        {"input": {"group": "SO2", "op": "jac_rminus", "x": [0.7], "y": [2]}, "expected_output": "tangent: -1.300000\n[various jacobian label prefixes]\n1.000000\n[various jacobian label prefixes]\n-1.000000\n"}
    ]
}
```

*8.7 Point-action Jacobians*

Returns the transformed point followed by the Jacobian with respect to the element (point-dimension rows by degrees-of-freedom columns) and then the Jacobian with respect to the point (a square matrix of point dimension).

**Test Cases:** `rcb_tests/public_test_cases/feature8_7_jac_act.json`

```json
{
    "description": "Apply a group element to a point together with the two analytic Jacobians of the transformed point: one with respect to the element expressed in the local tangent frame, and one with respect to the input point. The request names a group, supplies the element through its natural construction parameters, and supplies a point of dimension two for the planar groups and three for the spatial groups. The output is the transformed point followed by the Jacobian with respect to the element (point dimension rows by degrees-of-freedom columns) and then the Jacobian with respect to the point (a square matrix of point dimension).",
    "cases": [
        {"input": {"group": "SO2", "op": "jac_act", "x": [0.7], "p": [1, 2]}, "expected_output": "point: -0.523593 2.173902\n[various jacobian label prefixes]\n-2.173902\n-0.523593\n[various jacobian label prefixes]\n0.764842 -0.644218\n0.644218 0.764842\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the four groups and the operations above (exponential/logarithmic maps, inversion, composition, relative transformation, right/left increment and difference, point action, adjoint, geodesic interpolation, and the analytic Jacobians), with the core domain decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program that reads a single JSON request object from stdin, selects the group via the `group` field and the operation via the `op` field, invokes the core logic, and prints the result to stdout exactly matching the per-feature contracts above. The request carries operands under the documented fields: group elements under `x` and `y` as natural construction parameters, a tangent vector under `tau`, a point under `p`, and an interpolation factor under `t`. The adapter owns numeric formatting (fixed six-decimal rendering with near-zero values cleaned to [a specific magnitude threshold for rendering positives]) and the translation of domain failures into neutral error lines (e.g. an out-of-range interpolation factor becomes `error: factor_out_of_range`). The adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the Jacobian ordering as defined in C012 for state derivatives
