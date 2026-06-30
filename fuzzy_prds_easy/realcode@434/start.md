## Product Requirement Document

# Particle-System Analysis Toolkit - Geometry, Neighborhood, Density, and Order Metrics

## Project Goal

Build a particle-system analysis toolkit that allows developers to generate reference structures and compute periodic geometry, neighbor, density, clustering, orientational-order, and trajectory metrics without rewriting low-level spatial algorithms for every simulation workflow.

---

## Background & Problem

Without this library/tool, developers are forced to manually implement periodic boundary handling, neighbor searches, histogram normalization, connected-component analysis, orientation algebra, and time-correlation calculations. This leads to repetitive numerical code, inconsistent boundary conventions, subtle off-by-one neighbor errors, and difficult-to-maintain analysis scripts.

With this library/tool, developers can express common particle-analysis tasks in terms of domains, points, orientations, and trajectories, and receive deterministic numerical outputs in a consistent machine-readable format.

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
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project size):
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

### Feature 1: Lattice Generation

**As a developer**, I want to generate canonical periodic point sets, so I can start simulations from known structures.

**Expected Behavior / Usage:**

The input names a lattice family and may include scale or replication controls. The output is a single line beginning with `result=` followed by compact JSON containing the generated domain lengths, dimensionality, tilt factors, and ordered point coordinates. Square cells are two-dimensional with z coordinates present as zero; cubic cells are three-dimensional. Invalid replication inputs are outside this contract because the retained behavior focuses on successfully generated structures.

**Test Cases:** `rcb_tests/public_test_cases/feature1_lattice_generation.json`

```json
{
    "description": "Generate standard periodic unit-cell point sets with the requested lattice family and optional scaling or replication.",
    "cases": [
        {
            "input": {
                "lattice": "square"
            },
            "expected_output": "result={\"box\":{\"Lx\":1.0,\"Ly\":1.0,\"Lz\":0.0,\"dimensions\":2,\"xy\":0.0,\"xz\":0.0,\"yz\":0.0},\"dimensions\":2,\"points\":[[-0.5,-0.5,0.0]]}\n"
        }
    ]
}
```

---

### Feature 2: Box Coordinate Geometry

**As a developer**, I want to inspect domain geometry and transform coordinates, so I can move safely between fractional and absolute coordinate systems.

**Expected Behavior / Usage:**

The input provides a periodic domain and optional coordinate arrays. The output reports domain dimensionality, lengths, volume, and any requested vectors, matrices, absolute coordinates, fractional coordinates, center of mass, and centered positions. Fractional coordinates use the centered periodic convention where fractional zero maps to the negative half-domain corner and one half maps to the box center.

**Test Cases:** `rcb_tests/public_test_cases/feature2_box_coordinate_geometry.json`

```json
{
    "description": "Report box geometry and convert between fractional and centered absolute coordinates for two- and three-dimensional periodic domains.",
    "cases": [
        {
            "input": {
                "box": {
                    "kind": "cube",
                    "length": 2
                },
                "absolute_from_fractional": [
                    [
                        0.5,
                        0.25,
                        0.75
                    ],
                    [
                        0,
                        0,
                        0
                    ],
                    [
                        0.5,
                        0.5,
                        0.5
                    ]
                ],
                "fractional_from_absolute": [
                    [
                        0,
                        -0.5,
                        0.5
                    ],
                    [
                        -1,
                        -1,
                        -1
                    ],
                    [
                        0,
                        0,
                        0
                    ]
                ]
            },
            "expected_output": "result={\"absolute\":[[0.0,-0.5,0.5],[-1.0,-1.0,-1.0],[0.0,0.0,0.0]],\"dimensions\":3,\"fractional\":[[0.5,0.25,0.75],[0.0,0.0,0.0],[0.5,0.5,0.5]],\"lengths\":[2.0,2.0,2.0],\"volume\":8.0}\n"
        }
    ]
}
```

---

### Feature 3: Periodic Coordinate Mapping

**As a developer**, I want to apply periodic boundary operations, so I can normalize, reconstruct, and compare positions across image boundaries.

**Expected Behavior / Usage:**

The input provides a periodic domain and one or more requested operations: wrapping raw coordinates into the primary image, unwrapping wrapped positions with integer image counters, computing integer image counters for raw positions, or measuring minimum-image distances. The output contains only the requested arrays under descriptive keys.

**Test Cases:** `rcb_tests/public_test_cases/feature3_box_periodic_mapping.json`

```json
{
    "description": "Map coordinates through periodic boundaries by wrapping, unwrapping image coordinates, computing image counters, and measuring minimum-image distances.",
    "cases": [
        {
            "input": {
                "box": {
                    "kind": "general",
                    "Lx": 2,
                    "Ly": 2,
                    "Lz": 2,
                    "xy": 1,
                    "xz": 0,
                    "yz": 0
                },
                "wrap_points": [
                    [
                        10,
                        -5,
                        -5
                    ],
                    [
                        0,
                        0.5,
                        0
                    ]
                ]
            },
            "expected_output": "result={\"wrapped\":[[-2.0,-1.0,-1.0],[0.0,0.5,0.0]]}\n"
        }
    ]
}
```

---

### Feature 4: Neighbor Search

**As a developer**, I want to query neighboring particles, so I can build connectivity from radius or nearest-neighbor rules.

**Expected Behavior / Usage:**

The input supplies a periodic domain, stored points, query points, and a search rule. Radius searches include all pairs within the cutoff and may exclude identical-index self pairs. Nearest searches return the requested number of closest stored points subject to any cutoff. The output includes total bond count, per-query counts, sorted neighbor indices grouped by query point, and sorted query-target index pairs.

**Test Cases:** `rcb_tests/public_test_cases/feature4_neighbor_query.json`

```json
{
    "description": "Find neighboring point pairs in a periodic domain using either radius cutoff searches or a requested nearest-neighbor count, including optional self-pair exclusion.",
    "cases": [
        {
            "input": {
                "box": {
                    "kind": "cube",
                    "length": 10
                },
                "points": [
                    [
                        0,
                        0,
                        0
                    ],
                    [
                        1,
                        0,
                        0
                    ],
                    [
                        3,
                        0,
                        0
                    ],
                    [
                        2,
                        0,
                        0
                    ]
                ],
                "query_points": [
                    [
                        0,
                        0,
                        0
                    ],
                    [
                        1,
                        0,
                        0
                    ],
                    [
                        3,
                        0,
                        0
                    ],
                    [
                        2,
                        0,
                        0
                    ]
                ],
                "query": {
                    "mode": "ball",
                    "r_max": 2.01,
                    "exclude_ii": true
                }
            },
            "expected_output": "result={\"neighbor_counts\":[2,3,2,3],\"neighbors_by_query\":{\"0\":[1,3],\"1\":[0,2,3],\"2\":[1,3],\"3\":[0,1,2]},\"num_bonds\":10,\"pairs\":[[0,1],[0,3],[1,0],[1,2],[1,3],[2,1],[2,3],[3,0],[3,1],[3,2]]}\n"
        },
        {
            "input": {
                "box": {
                    "kind": "cube",
                    "length": 10
                },
                "points": [
                    [
                        0,
                        0,
                        0
                    ],
                    [
                        1,
                        0,
                        0
                    ],
                    [
                        3,
                        0,
                        0
                    ],
                    [
                        2,
                        0,
                        0
                    ]
                ],
                "query_points": [
                    [
                        0,
                        0,
                        0
                    ],
                    [
                        1,
                        0,
                        0
                    ],
                    [
                        3,
                        0,
                        0
                    ],
                    [
                        2,
                        0,
                        0
                    ]
                ],
                "query": {
                    "mode": "nearest",
                    "num_neighbors": 3,
                    "r_max": 1.9,
                    "exclude_ii": true
                }
            },
            "expected_output": "result={\"neighbor_counts\":[1,2,1,2],\"neighbors_by_query\":{\"0\":[1],\"1\":[0,3],\"2\":[3],\"3\":[1,2]},\"num_bonds\":6,\"pairs\":[[0,1],[1,0],[1,3],[2,3],[3,1],[3,2]]}\n"
        }
    ]
}
```

---

### Feature 5: Explicit Neighbor List Tables

**As a developer**, I want to construct a neighbor table from arrays, so I can reuse explicit connectivity with counts, weights, and range filtering.

**Expected Behavior / Usage:**

The input supplies query indices, target indices, distances, optional weights, and the number of query and target points. The output returns the normalized table, weight values, neighbor counts per query point, and segment-start offsets. If a filter is supplied, only rows with distances in the requested half-open range are retained.

**Test Cases:** `rcb_tests/public_test_cases/feature5_neighbor_list_arrays.json`

```json
{
    "description": "Build an explicit neighbor-pair table from arrays, derive counts and segment starts, preserve weights, and filter rows by distance range.",
    "cases": [
        {
            "input": {
                "num_query_points": 4,
                "num_points": 4,
                "query_point_indices": [
                    0,
                    0,
                    1,
                    2,
                    3
                ],
                "point_indices": [
                    1,
                    2,
                    3,
                    0,
                    0
                ],
                "distances": [
                    1,
                    1,
                    1,
                    1,
                    1
                ]
            },
            "expected_output": "result={\"distances\":[1.0,1.0,1.0,1.0,1.0],\"neighbor_counts\":[2,1,1,1],\"num_bonds\":5,\"point_indices\":[1,2,3,0,0],\"query_point_indices\":[0,0,1,2,3],\"segments\":[0,2,3,4],\"weights\":[1.0,1.0,1.0,1.0,1.0]}\n"
        }
    ]
}
```

---

### Feature 6: Radial Distribution Histograms

**As a developer**, I want to compute radial bin geometry and pair statistics, so I can analyze how particle density varies with distance.

**Expected Behavior / Usage:**

The input supplies bin count, maximum radius, optional minimum radius, and optionally a point system. Without a system, the output contains bin centers and edges. With a system, the output also contains the radial distribution values and cumulative coordination counts. Empty histograms return zero arrays rather than unavailable results.

**Test Cases:** `rcb_tests/public_test_cases/feature6_radial_distribution.json`

```json
{
    "description": "Create radial histogram bins and compute radial distribution and cumulative neighbor counts for supplied point systems.",
    "cases": [
        {
            "input": {
                "bins": 5,
                "r_max": 5,
                "r_min": 0
            },
            "expected_output": "result={\"bin_centers\":[0.5,1.5,2.5,3.5,4.5],\"bin_edges\":[0.0,1.0,2.0,3.0,4.0,5.0]}\n"
        },
        {
            "input": {
                "bins": 10,
                "r_max": 0.5,
                "system": {
                    "box": {
                        "kind": "cube",
                        "length": 5
                    },
                    "points": [
                        [
                            0,
                            0,
                            0
                        ],
                        [
                            2,
                            2,
                            2
                        ]
                    ]
                }
            },
            "expected_output": "result={\"bin_centers\":[0.025,0.075,0.125,0.175,0.225,0.275,0.325,0.375,0.425,0.475],\"bin_edges\":[0.0,0.05,0.1,0.15,0.2,0.25,0.3,0.35,0.4,0.45,0.5],\"cumulative_counts\":[0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0],\"rdf\":[0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0]}\n"
        }
    ]
}
```

---

### Feature 7: Local Density Estimation

**As a developer**, I want to estimate density around query locations, so I can measure local crowding in a particle system.

**Expected Behavior / Usage:**

The input supplies a periodic domain, particle coordinates, sampling radius, particle diameter, and optional query coordinates. The output contains one density and one effective neighbor count per query point. Boundary contributions from particles near the sampling shell are handled by the density estimator rather than by a simple integer count.

**Test Cases:** `rcb_tests/public_test_cases/feature7_local_density.json`

```json
{
    "description": "Estimate local number density and neighbor count around each query point from particles inside a spherical sampling volume.",
    "cases": [
        {
            "input": {
                "box": {
                    "kind": "cube",
                    "length": 10
                },
                "r_max": 3,
                "diameter": 1,
                "points": [
                    [
                        0,
                        0,
                        0
                    ],
                    [
                        1,
                        0,
                        0
                    ],
                    [
                        0,
                        1,
                        0
                    ],
                    [
                        0,
                        0,
                        1
                    ],
                    [
                        4,
                        4,
                        4
                    ]
                ],
                "query_points": [
                    [
                        0,
                        0,
                        0
                    ],
                    [
                        4,
                        4,
                        4
                    ]
                ]
            },
            "expected_output": "result={\"density\":[0.035368,0.008842],\"num_neighbors\":[4.0,1.0]}\n"
        }
    ]
}
```

---

### Feature 8: Cluster Properties

**As a developer**, I want to identify connected particle clusters and summarize them, so I can measure sizes and geometry of connected components.

**Expected Behavior / Usage:**

The input supplies a periodic domain, points, and either a neighbor rule or explicit cluster labels. The output reports the number of clusters, per-particle cluster labels, cluster membership keys when produced by connectivity, cluster sizes, periodic centers, and radii of gyration. Periodic centers must respect wrapped clusters that span a boundary.

**Test Cases:** `rcb_tests/public_test_cases/feature8_cluster_properties.json`

```json
{
    "description": "Group points connected by neighbor edges and report cluster labels, cluster sizes, centers, keys, and radii of gyration.",
    "cases": [
        {
            "input": {
                "box": {
                    "kind": "square",
                    "length": 5
                },
                "points": [
                    [
                        0,
                        -2,
                        0
                    ],
                    [
                        0,
                        -2,
                        0
                    ],
                    [
                        0,
                        2,
                        0
                    ],
                    [
                        -0.1,
                        1.9,
                        0
                    ]
                ],
                "neighbors": {
                    "r_max": 0.5
                }
            },
            "expected_output": "result={\"centers\":[[0.0,-2.0,0.0],[-0.05,1.95,0.0]],\"cluster_idx\":[0,0,1,1],\"cluster_keys\":[[0,1],[2,3]],\"num_clusters\":2,\"radii_of_gyration\":[0.0,0.070711],\"sizes\":[2,2]}\n"
        }
    ]
}
```

---

### Feature 9: Nematic Orientational Order

**As a developer**, I want to measure alignment of particle orientations, so I can quantify orientational ordering relative to a molecular axis.

**Expected Behavior / Usage:**

The input supplies an orientation set and a molecular axis. The output contains the scalar nematic order, the director, and the nematic tensor. Perfectly aligned identity orientations produce unit order along the requested molecular axis and a traceless tensor with one positive principal component and two negative half components.

**Test Cases:** `rcb_tests/public_test_cases/feature9_nematic_order.json`

```json
{
    "description": "Compute the orientational nematic scalar order, director, and tensor for particles relative to a chosen molecular axis.",
    "cases": [
        {
            "input": {
                "orientation_set": "identity",
                "count": 10,
                "molecular_axis": [
                    1,
                    0,
                    0
                ]
            },
            "expected_output": "result={\"director\":[1.0,0.0,0.0],\"nematic_tensor\":[[1.0,0.0,0.0],[0.0,-0.5,0.0],[0.0,0.0,-0.5]],\"order\":1.0}\n"
        }
    ]
}
```

---

### Feature 10: Planar Bond-Orientational Order

**As a developer**, I want to measure k-fold in-plane bond order, so I can distinguish square and hexagonal local symmetry.

**Expected Behavior / Usage:**

The input names a two-dimensional lattice, replication count, integer symmetry order, whether weighted evaluation is requested, and the neighbor source. The output reports aggregate absolute order values and a sample of per-particle absolute order. Weighted tessellation neighbors give unit fourfold order and zero sixfold order for square lattices, and unit sixfold order for hexagonal lattices.

**Test Cases:** `rcb_tests/public_test_cases/feature10_hexatic_order.json`

```json
{
    "description": "Measure weighted k-fold in-plane bond-orientational order for square or hexagonal lattices using tessellation-derived neighbor weights.",
    "cases": [
        {
            "input": {
                "lattice": "square",
                "num_replicas": 4,
                "k": 4,
                "weighted": true,
                "neighbor_source": "voronoi"
            },
            "expected_output": "result={\"max_abs_order\":1.0,\"mean_abs_order\":1.0,\"min_abs_order\":1.0,\"sample_abs_order\":[1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0]}\n"
        },
        {
            "input": {
                "lattice": "square",
                "num_replicas": 4,
                "k": 6,
                "weighted": true,
                "neighbor_source": "voronoi"
            },
            "expected_output": "result={\"max_abs_order\":0.0,\"mean_abs_order\":0.0,\"min_abs_order\":0.0,\"sample_abs_order\":[0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0]}\n"
        }
    ]
}
```

---

### Feature 11: Spherical Bond-Order Parameters

**As a developer**, I want to compute spherical-harmonic local order, so I can characterize three-dimensional neighbor environments.

**Expected Behavior / Usage:**

The input supplies a periodic domain, points, harmonic degree, and neighbor rule. The output contains the global average order and per-particle order. For three collinear points with two neighbors each, odd degrees give zero order for the middle particle and unit order for the end particles, while even degrees give unit order for all three.

**Test Cases:** `rcb_tests/public_test_cases/feature11_steinhardt_order.json`

```json
{
    "description": "Compute spherical-harmonic bond-order values for a point environment, including parity behavior for collinear neighbors.",
    "cases": [
        {
            "input": {
                "box": {
                    "kind": "cube",
                    "length": 10
                },
                "points": [
                    [
                        0,
                        0,
                        -1
                    ],
                    [
                        0,
                        0,
                        0
                    ],
                    [
                        0,
                        0,
                        1
                    ]
                ],
                "l": 1,
                "neighbors": {
                    "num_neighbors": 2
                }
            },
            "expected_output": "result={\"order\":0.0,\"particle_order\":[1.0,0.0,1.0]}\n"
        },
        {
            "input": {
                "box": {
                    "kind": "cube",
                    "length": 10
                },
                "points": [
                    [
                        0,
                        0,
                        -1
                    ],
                    [
                        0,
                        0,
                        0
                    ],
                    [
                        0,
                        0,
                        1
                    ]
                ],
                "l": 2,
                "neighbors": {
                    "num_neighbors": 2
                }
            },
            "expected_output": "result={\"order\":1.0,\"particle_order\":[1.0,1.0,1.0]}\n"
        }
    ]
}
```

---

### Feature 12: Mean Squared Displacement

**As a developer**, I want to compute displacement growth over time, so I can analyze trajectories of one or more particles.

**Expected Behavior / Usage:**

The input is a time-major array of particle positions and may select the direct or windowed calculation mode. The output contains the mean squared displacement for each lag time. Static particles contribute zero displacement, so mixed moving and static trajectories average their squared displacements across particles.

**Test Cases:** `rcb_tests/public_test_cases/feature12_mean_squared_displacement.json`

```json
{
    "description": "Compute windowed or direct mean squared displacement over time for one or more trajectories.",
    "cases": [
        {
            "input": {
                "positions": [
                    [
                        [
                            0,
                            0,
                            0
                        ]
                    ],
                    [
                        [
                            1,
                            0,
                            0
                        ]
                    ],
                    [
                        [
                            2,
                            0,
                            0
                        ]
                    ],
                    [
                        [
                            3,
                            0,
                            0
                        ]
                    ]
                ]
            },
            "expected_output": "result={\"msd\":[0.0,1.0,4.0,[the final MSD value with a tiny floating point epsilon]]}\n"
        },
        {
            "input": {
                "positions": [
                    [
                        [
                            0,
                            0,
                            0
                        ],
                        [
                            0,
                            0,
                            0
                        ]
                    ],
                    [
                        [
                            1,
                            0,
                            0
                        ],
                        [
                            0,
                            0,
                            0
                        ]
                    ],
                    [
                        [
                            2,
                            0,
                            0
                        ],
                        [
                            0,
                            0,
                            0
                        ]
                    ],
                    [
                        [
                            3,
                            0,
                            0
                        ],
                        [
                            0,
                            0,
                            0
                        ]
                    ]
                ],
                "mode": "direct"
            },
            "expected_output": "result={\"msd\":[0.0,0.5,2.0,4.5]}\n"
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
- use the lattice dictionary shape from the box geometry handler
- apply Steinhardt order to neighbors using the neighbor connectivity system
