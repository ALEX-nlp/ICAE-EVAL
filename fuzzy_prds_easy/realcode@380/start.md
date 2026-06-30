## Product Requirement Document

# 2D Physics Constraint and Collision Toolkit - Black-Box Behavior Contract

## Project Goal

Build a 2D rigid-body physics toolkit that allows developers to model collision primitives, bodies, contacts, simulation gravity, and constraints without hand-writing low-level geometry, solver, and debug-rendering behavior.

---

## Background & Problem

Without this library/tool, developers are forced to implement collision geometry, body state transitions, contact toggles, constraint bookkeeping, and debug drawing manually. This leads to repetitive math code, fragile edge-case handling, and simulations that are difficult to inspect or maintain.

With this library/tool, developers can create common 2D collision primitives, run gravity steps, manage contacts and constraints, and observe debug-rendering signals through stable behavior-oriented interfaces.

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

### Feature 1: Round Collision Primitive Properties

**As a developer**, I want to inspect a round collision primitive after creation and copying, so I can confirm that both the original and copy preserve the requested radius and center.

**Expected Behavior / Usage:**

The input supplies a radius and center for a round collision primitive. The output prints the original radius and center, followed by the copied primitive radius and center, using two-decimal numeric formatting.

**Test Cases:** `rcb_tests/public_test_cases/feature1_round_shape_properties.json`

```json
{
    "description": "A circular collision primitive reports its configured radius and center, and a copied primitive preserves those same externally visible values.",
    "cases": [
        {
            "input": {
                "scenario": "circle_properties",
                "radius": 5.0,
                "center": [
                    1.0,
                    2.0
                ]
            },
            "expected_output": "radius=5.00\ncenter=1.00,2.00\ncopy_radius=5.00\ncopy_center=1.00,2.00\n"
        }
    ]
}
```

---

### Feature 2: Round Collision Distance Query

**As a developer**, I want to query separation from a round collision boundary to a point, so I can use distance and normal values for collision diagnostics.

**Expected Behavior / Usage:**

The input supplies a round primitive radius, local center, query point, and transform containing translation and rotation. The output prints the signed distance from the transformed boundary to the point and the outward unit normal, rounded to two decimals.

**Test Cases:** `rcb_tests/public_test_cases/feature2_round_shape_distance.json`

```json
{
    "description": "A circular collision primitive computes the signed separation distance and outward unit normal from its transformed boundary to a query point.",
    "cases": [
        {
            "input": {
                "scenario": "circle_distance",
                "radius": 3.0,
                "center": [
                    1.0,
                    2.0
                ],
                "point": [
                    10.0,
                    7.0
                ],
                "transform": {
                    "translation": [
                        0.0,
                        0.0
                    ],
                    "angle": 0.0
                }
            },
            "expected_output": "distance=7.30\nnormal=0.87,0.49\n"
        },
        {
            "input": {
                "scenario": "circle_distance",
                "radius": 3.0,
                "center": [
                    1.0,
                    2.0
                ],
                "point": [
                    1.0,
                    -5.0
                ],
                "transform": {
                    "translation": [
                        0.0,
                        0.0
                    ],
                    "angle": 0.0
                }
            },
            "expected_output": "distance=4.00\nnormal=-0.00,-1.00\n"
        },
        {
            "input": {
                "scenario": "circle_distance",
                "radius": 3.0,
                "center": [
                    1.0,
                    2.0
                ],
                "point": [
                    10.0,
                    7.0
                ],
                "transform": {
                    "translation": [
                        10.0,
                        10.0
                    ],
                    "angle": 0.2
                }
            },
            "expected_output": "distance=7.59\nnormal=0.89,0.46\n"
        },
        {
            "input": {
                "scenario": "circle_distance",
                "radius": 3.0,
                "center": [
                    1.0,
                    2.0
                ],
                "point": [
                    1.0,
                    -5.0
                ],
                "transform": {
                    "translation": [
                        10.0,
                        10.0
                    ],
                    "angle": 0.2
                }
            },
            "expected_output": "distance=4.17\nnormal=0.06,-1.00\n"
        }
    ]
}
```

---

### Feature 3: Axis-Aligned Box Geometry

**As a developer**, I want to construct a rectangular collision primitive from half extents, so I can use predictable vertices and normals for collision calculations.

**Expected Behavior / Usage:**

The input supplies the half width and half height of an axis-aligned rectangular collision primitive. The output lists the four vertices in counter-clockwise boundary order, the four outward edge normals in matching order, and the same copied values with the shape skin radius.

**Test Cases:** `rcb_tests/public_test_cases/feature3_axis_aligned_box_geometry.json`

```json
{
    "description": "An axis-aligned rectangular collision primitive built from half extents exposes the expected corner ordering, outward normals, and copy values.",
    "cases": [
        {
            "input": {
                "scenario": "box_geometry",
                "half_size": [
                    3.0,
                    4.0
                ]
            },
            "expected_output": "vertices=-3.00,-4.00;3.00,-4.00;3.00,4.00;-3.00,4.00\nnormals=0.00,-1.00;1.00,0.00;0.00,1.00;-1.00,0.00\ncopy_radius=0.01\ncopy_vertices=-3.00,-4.00;3.00,-4.00;3.00,4.00;-3.00,4.00\ncopy_normals=0.00,-1.00;1.00,0.00;0.00,1.00;-1.00,0.00\n"
        }
    ]
}
```

---

### Feature 4: Box Distance Query

**As a developer**, I want to query separation from a rectangular collision boundary to a point, so I can use distance and normal values for collision diagnostics.

**Expected Behavior / Usage:**

The input supplies rectangular half extents, a query point, and a transform containing translation and rotation. The output prints the signed distance from the transformed boundary to the point and the outward unit normal, rounded to two decimals.

**Test Cases:** `rcb_tests/public_test_cases/feature4_box_distance.json`

```json
{
    "description": "An axis-aligned rectangular collision primitive computes the signed separation distance and outward unit normal from its transformed boundary to a query point.",
    "cases": [
        {
            "input": {
                "scenario": "box_distance",
                "half_size": [
                    3.0,
                    4.0
                ],
                "point": [
                    10.0,
                    7.0
                ],
                "transform": {
                    "translation": [
                        0.0,
                        0.0
                    ],
                    "angle": 0.0
                }
            },
            "expected_output": "distance=7.00\nnormal=1.00,0.00\n"
        },
        {
            "input": {
                "scenario": "box_distance",
                "half_size": [
                    3.0,
                    4.0
                ],
                "point": [
                    1.0,
                    -5.0
                ],
                "transform": {
                    "translation": [
                        0.0,
                        0.0
                    ],
                    "angle": 0.0
                }
            },
            "expected_output": "distance=1.00\nnormal=0.00,-1.00\n"
        },
        {
            "input": {
                "scenario": "box_distance",
                "half_size": [
                    3.0,
                    4.0
                ],
                "point": [
                    10.0,
                    7.0
                ],
                "transform": {
                    "translation": [
                        10.0,
                        10.0
                    ],
                    "angle": 0.2
                }
            },
            "expected_output": "distance=8.19\nnormal=0.98,0.20\n"
        },
        {
            "input": {
                "scenario": "box_distance",
                "half_size": [
                    3.0,
                    4.0
                ],
                "point": [
                    1.0,
                    -5.0
                ],
                "transform": {
                    "translation": [
                        10.0,
                        10.0
                    ],
                    "angle": 0.2
                }
            },
            "expected_output": "distance=1.10\nnormal=0.20,-0.98\n"
        }
    ]
}
```

---

### Feature 5: Fast Moving Body Flag

**As a developer**, I want to mark whether a rigid body needs continuous collision handling, so I can prevent tunneling behavior for fast objects when requested.

**Expected Behavior / Usage:**

The input creates a rigid body and may include a fast-body flag update. The output always prints the initial flag state and, when an update is provided, prints the updated state.

**Test Cases:** `rcb_tests/public_test_cases/feature5_fast_body_flag.json`

```json
{
    "description": "A newly created rigid body starts with continuous-collision fast-body behavior disabled, and the flag can be enabled later.",
    "cases": [
        {
            "input": {
                "scenario": "fast_body_flag"
            },
            "expected_output": "initial_fast_body=false\n"
        },
        {
            "input": {
                "scenario": "fast_body_flag",
                "fast_body": true
            },
            "expected_output": "initial_fast_body=false\nupdated_fast_body=true\n"
        }
    ]
}
```

---

### Feature 6: Per-Body Gravity Participation

**As a developer**, I want to step a world while controlling how a dynamic body receives gravity, so I can support objects that ignore, scale, or follow world gravity.

**Expected Behavior / Usage:**

The input supplies a world gravity vector, one-second simulation duration, and optionally either a body-specific gravity override or gravity scale. The output prints initial and final positions plus whether each displacement component is zero or nonzero after the step.

**Test Cases:** `rcb_tests/public_test_cases/feature6_gravity_step.json`

```json
{
    "description": "A dynamic rigid body either remains stationary when gravity is neutralized for that body, or moves after a simulation step when world gravity applies.",
    "cases": [
        {
            "input": {
                "scenario": "gravity_step",
                "gravity": [
                    10.0,
                    10.0
                ],
                "gravity_override": [
                    0.0,
                    0.0
                ],
                "seconds": 1.0
            },
            "expected_output": "initial_position=0.00,0.00\nfinal_position=0.00,0.00\ndisplacement_x=zero\ndisplacement_y=zero\n"
        },
        {
            "input": {
                "scenario": "gravity_step",
                "gravity": [
                    10.0,
                    10.0
                ],
                "gravity_scale": [
                    0.0,
                    0.0
                ],
                "seconds": 1.0
            },
            "expected_output": "initial_position=0.00,0.00\nfinal_position=0.00,0.00\ndisplacement_x=zero\ndisplacement_y=zero\n"
        },
        {
            "input": {
                "scenario": "gravity_step",
                "gravity": [
                    10.0,
                    10.0
                ],
                "seconds": 1.0
            },
            "expected_output": "initial_position=0.00,0.00\nfinal_position=1.41,1.41\ndisplacement_x=nonzero\ndisplacement_y=nonzero\n"
        }
    ]
}
```

---

### Feature 7: Contact Enablement

**As a developer**, I want to toggle whether a fixture contact participates in collision processing, so I can temporarily disable or re-enable contacts without destroying them.

**Expected Behavior / Usage:**

The input creates a contact between two fixtures and may include a desired enabled state. The output prints the initial enabled state and, when an update is provided, prints the updated state.

**Test Cases:** `rcb_tests/public_test_cases/feature7_contact_enablement.json`

```json
{
    "description": "A newly created contact between two fixtures starts enabled, and its enablement can be changed for later collision processing.",
    "cases": [
        {
            "input": {
                "scenario": "contact_enablement"
            },
            "expected_output": "initial_enabled=true\n"
        },
        {
            "input": {
                "scenario": "contact_enablement",
                "enabled": false
            },
            "expected_output": "initial_enabled=true\nupdated_enabled=false\n"
        }
    ]
}
```

---

### Feature 8: World Gravity Assignment

**As a developer**, I want to set and read the gravity vector of a simulation world, so I can verify the vector that future dynamic-body steps will use.

**Expected Behavior / Usage:**

The input supplies a gravity vector for a simulation world. The output prints the assigned gravity vector using two-decimal numeric formatting.

**Test Cases:** `rcb_tests/public_test_cases/feature8_world_gravity.json`

```json
{
    "description": "A simulation world exposes the gravity vector assigned to it so later steps can use that vector for dynamic bodies.",
    "cases": [
        {
            "input": {
                "scenario": "world_gravity",
                "gravity": [
                    1.0,
                    0.0
                ]
            },
            "expected_output": "gravity=1.00,0.00\n"
        }
    ]
}
```

---

### Feature 9: Constraint Lifecycle Cleanup

**As a developer**, I want to track body-to-body constraints and remove them during body destruction, so I can avoid stale connections after one constrained body is deleted.

**Expected Behavior / Usage:**

The input creates two bodies, attaches a constraint between them, then destroys one endpoint body. The output prints the world constraint count before and after creation, each body constraint count after creation, and each endpoint count after destruction.

**Test Cases:** `rcb_tests/public_test_cases/feature9_constraint_lifecycle.json`

```json
{
    "description": "When two bodies are connected by a constraint, each body records that connection; destroying one connected body removes the connection from both endpoints.",
    "cases": [
        {
            "input": {
                "scenario": "constraint_lifecycle"
            },
            "expected_output": "world_constraints_before=0\nworld_constraints_after_create=1\nbody_a_constraints_after_create=1\nbody_b_constraints_after_create=1\nbody_a_constraints_after_destroy=0\nbody_b_constraints_after_destroy=0\n"
        }
    ]
}
```

---

### Feature 10: Adjustable Motor Constraint Settings

**As a developer**, I want to change motor settings on supported constraints, so I can control motorized physics relationships and wake affected bodies.

**Expected Behavior / Usage:**

The input identifies a motorized constraint family, a numeric setting, and a value. The output prints the setting value after assignment and confirms both attached bodies are awake.

**Test Cases:** `rcb_tests/public_test_cases/feature10_adjustable_constraint_settings.json`

```json
{
    "description": "Motorized constraints expose adjustable numeric motor settings and wake both attached bodies when those settings are changed.",
    "cases": [
        {
            "input": {
                "scenario": "adjustable_constraint",
                "family": "hinge",
                "setting": "motor_speed",
                "value": 1.0
            },
            "expected_output": "motor_speed=1.00\nbody_a_awake=true\nbody_b_awake=true\n"
        },
        {
            "input": {
                "scenario": "adjustable_constraint",
                "family": "slider",
                "setting": "motor_speed",
                "value": 1.0
            },
            "expected_output": "motor_speed=1.00\nbody_a_awake=true\nbody_b_awake=true\n"
        },
        {
            "input": {
                "scenario": "adjustable_constraint",
                "family": "slider",
                "setting": "max_motor_force",
                "value": 1.0
            },
            "expected_output": "max_motor_force=1.00\nbody_a_awake=true\nbody_b_awake=true\n"
        },
        {
            "input": {
                "scenario": "adjustable_constraint",
                "family": "wheel",
                "setting": "motor_speed",
                "value": 1.0
            },
            "expected_output": "motor_speed=1.00\nbody_a_awake=true\nbody_b_awake=true\n"
        }
    ]
}
```

---

### Feature 11: Constraint Debug Rendering Signals

**As a developer**, I want to render constraint connection geometry into debug draw calls, so I can inspect which connection segments a constraint exposes to visualization tools.

**Expected Behavior / Usage:**

The input identifies a constraint family and requests debug rendering. The output prints how many line segments, points, and circles were sent to the debug renderer, making the rendering behavior externally observable.

**Test Cases:** `rcb_tests/public_test_cases/feature11_constraint_debug_rendering.json`

```json
{
    "description": "Each constraint family emits a predictable number of debug line segments when asked to render its connection geometry.",
    "cases": [
        {
            "input": {
                "scenario": "render_constraint",
                "family": "distance_link"
            },
            "expected_output": "segments=1\npoints=0\ncircles=0\n"
        },
        {
            "input": {
                "scenario": "render_constraint",
                "family": "surface_friction"
            },
            "expected_output": "segments=1\npoints=0\ncircles=0\n"
        },
        {
            "input": {
                "scenario": "render_constraint",
                "family": "linear_motor"
            },
            "expected_output": "segments=3\npoints=0\ncircles=0\n"
        },
        {
            "input": {
                "scenario": "render_constraint",
                "family": "pointer_target"
            },
            "expected_output": "segments=0\npoints=0\ncircles=0\n"
        },
        {
            "input": {
                "scenario": "render_constraint",
                "family": "slider"
            },
            "expected_output": "segments=3\npoints=0\ncircles=0\n"
        },
        {
            "input": {
                "scenario": "render_constraint",
                "family": "pulley"
            },
            "expected_output": "segments=3\npoints=0\ncircles=0\n"
        },
        {
            "input": {
                "scenario": "render_constraint",
                "family": "hinge"
            },
            "expected_output": "segments=3\npoints=0\ncircles=0\n"
        },
        {
            "input": {
                "scenario": "render_constraint",
                "family": "rope_limit"
            },
            "expected_output": "segments=3\npoints=0\ncircles=0\n"
        },
        {
            "input": {
                "scenario": "render_constraint",
                "family": "weld"
            },
            "expected_output": "segments=3\npoints=0\ncircles=0\n"
        },
        {
            "input": {
                "scenario": "render_constraint",
                "family": "wheel"
            },
            "expected_output": "segments=3\npoints=0\ncircles=0\n"
        },
        {
            "input": {
                "scenario": "render_constraint",
                "family": "constant_area"
            },
            "expected_output": "segments=0\npoints=0\ncircles=0\n"
        }
    ]
}
```

---

### Feature 12: Rope-Style Anchor Defaults

**As a developer**, I want to create a rope-style distance limiter with default local anchors, so I can start from neutral endpoint anchors before customization.

**Expected Behavior / Usage:**

The input creates a rope-style limiter definition without custom anchors. The output prints both local endpoint anchors, each formatted as an x,y pair.

**Test Cases:** `rcb_tests/public_test_cases/feature12_rope_anchor_defaults.json`

```json
{
    "description": "A rope-style distance limiter starts with both local endpoint anchors at the origin before a caller customizes them.",
    "cases": [
        {
            "input": {
                "scenario": "rope_defaults"
            },
            "expected_output": "anchor_a=0.00,0.00\nanchor_b=0.00,0.00\n"
        }
    ]
}
```

---

### Feature 13: Coupled Constraint Combinations

**As a developer**, I want to combine two source constraints into a coupled relation, so I can support hinge and slider combinations while rejecting unsupported pairs predictably.

**Expected Behavior / Usage:**

The input supplies the first and second source constraint families and asks either for rendering or solver setup. Supported hinge and slider combinations report successful creation and either rendered segment count or completed solver setup; unsupported source pairs return a normalized error with the raw family labels.

**Test Cases:** `rcb_tests/public_test_cases/feature13_coupled_constraint_combinations.json`

```json
{
    "description": "A coupled constraint can be built from hinge and slider constraints in either order, supports solver setup for those combinations, renders its links, and rejects unsupported source constraint pairs with a normalized error.",
    "cases": [
        {
            "input": {
                "scenario": "coupled_constraint",
                "first": "hinge",
                "second": "hinge",
                "check": "render"
            },
            "expected_output": "created=yes\nsegments=3\n"
        },
        {
            "input": {
                "scenario": "coupled_constraint",
                "first": "hinge",
                "second": "slider",
                "check": "solve_setup"
            },
            "expected_output": "created=yes\nvelocity_setup=completed\nposition_solution=true\n"
        },
        {
            "input": {
                "scenario": "coupled_constraint",
                "first": "slider",
                "second": "hinge",
                "check": "solve_setup"
            },
            "expected_output": "created=yes\nvelocity_setup=completed\nposition_solution=true\n"
        },
        {
            "input": {
                "scenario": "coupled_constraint",
                "first": "slider",
                "second": "slider",
                "check": "solve_setup"
            },
            "expected_output": "created=yes\nvelocity_setup=completed\nposition_solution=true\n"
        },
        {
            "input": {
                "scenario": "coupled_constraint",
                "first": "unsupported",
                "second": "unsupported",
                "check": "render"
            },
            "expected_output": "error=unsupported_constraint_pair\nfirst=unsupported\nsecond=unsupported\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the strict CCW vertex pattern used in box_geometry tests
- check the successful coupled constraint setup path logic
