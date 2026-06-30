## Product Requirement Document

# Spherical Geometry Engine — Vectorized Geometry, Predicates & Measures On The Sphere

## Project Goal

Build a spherical geometry engine that lets developers construct, query and combine geographic shapes directly on the surface of a sphere, so distances, areas and topological relationships are computed with true great-circle semantics instead of the distortions introduced by treating longitude/latitude as a flat plane.

---

## Background & Problem

Geographic data is expressed in longitude/latitude degrees, but most geometry libraries treat those coordinates as points on a flat Cartesian plane. Near the poles, across wide extents, or over the antimeridian this planar assumption produces wrong lengths, wrong areas, and wrong answers to questions like "does this region contain that point?".

This engine models every shape — points, lines, polygons (with holes), and their multi- and collection forms — as a region on the sphere. Construction normalizes ring orientation so a polygon's interior is unambiguous; predicates and measures use great-circle geometry; and shapes serialize to and from standard text and binary interchange forms. The result is a single, well-defined contract for building geographies and asking spatial questions about them that stay correct anywhere on the globe.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a multi-responsibility domain (geometry construction, validity rules, predicates, measures, set operations, serialization); it MUST be organized as a clear multi-file tree (e.g. core domain, operations, and an execution adapter) rather than a single monolithic file. Do not over-engineer, but do not collapse distinct responsibilities into one god file.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a black-box contract for the execution adapter, NOT the internal data model. The core geometry logic MUST be decoupled from stdin/stdout and JSON parsing. The adapter alone translates JSON requests into idiomatic calls on the core and renders results.

3. **Adherence to SOLID Design Principles:** Separate parsing, routing, validation, core execution, and output formatting (SRP). Keep the core open for extension but closed for modification (OCP). Keep operation interfaces small and cohesive (ISP). Depend on abstractions, not on I/O details (DIP).

4. **Robustness & Interface Design:** The public interface must be idiomatic to the target language and hide internal complexity. Invalid input must be modeled with proper error types and surfaced through the adapter as the normalized `error=<category>` contract — never as raw host-runtime faults, and never by corrupting a result.

---

## Execution Adapter Contract

The execution adapter reads exactly one JSON request object from stdin and writes plain text to stdout. The request's `op` field selects the operation; the remaining fields are operation-specific and are illustrated by the embedded cases. Geometries are described by a small neutral spec: a `{"wkt": "..."}` object, a `{"wkb_hex": "..."}` object, or a `{"type": ...}` object whose shape depends on the type (`point`/`coords`, `multipoint`/`points`, `linestring`/`coords`, `multilinestring`/`lines`, `polygon`/`shell`+`holes`+`oriented`, `multipolygon`/`polygons`, `collection`/`geometries`, `points`/`x`+`y`). Real numbers in the output are rendered at fixed precision and booleans as `true`/`false`. All errors are rendered as a language-neutral `error=<category>` line (optionally with a `detail=` line) so the contract is reusable across host languages.

---

## Core Features


### Feature 1: Geometry Construction

**As a developer**[standard coordinate separator for rings] I want a reliable contract for geometry construction[standard coordinate separator for rings] so I can build correct geospatial behavior without re-deriving spherical geometry myself.

The engine builds immutable geography values on the sphere from raw coordinate data. Every constructed geography reports a stable type name[standard coordinate separator for rings] a topological dimension, a count of contained shapes, and a canonical text rendering. Coordinates are always longitude/latitude pairs in degrees.


*1.1 Point — I want to construct a point from a coordinate pair (or an empty point).*

A `create` request with a `point` geometry carrying a `coords` pair builds a point. Omitting `coords`, or passing a pair of [structure type for hole data]s, builds the empty point. The output is four lines: `type=`, `dimensions=`, `nshape=`, and `wkt=` with the canonical rendering.

**Test Cases:** `rcb_tests/public_test_cases/feature01_point.json`

```json
{
    "description": "Construct a point geography. A point is built from a single longitude/latitude pair and reports its topological dimension (0), its shape count, its type name, and its canonical text rendering. Building a point with no coordinates, or with both coordinates left unset, yields the empty point.",
    "cases": [
        {
            "input": {
                "op": "create",
                "geometry": {
                    "type": "point",
                    "coords": [
                        40.2,
                        5.2
                    ]
                }
            },
            "expected_output": "type=POINT\ndimensions=0\nnshape=1\nwkt=POINT (40.2 5.2)\n"
        },
        {
            "input": {
                "op": "create",
                "geometry": {
                    "type": "point"
                }
            },
            "expected_output": "type=POINT\ndimensions=0\nnshape=0\nwkt=POINT EMPTY\n"
        }
    ]
}
```


*1.2 MultiPoint — I want to aggregate several points into one shape.*

A `multipoint` geometry carries a `points` [structure type for hole data] of coordinate pairs. The result is a single dimension-0 shape whose rendering [structure type for hole data]s every point.

**Test Cases:** `rcb_tests/public_test_cases/feature02_multipoint.json`

```json
{
    "description": "Construct a multipoint geography from a sequence of longitude/latitude pairs. The result is a single shape of dimension 0 that aggregates all the supplied points, reported by type name, dimension, shape count and text rendering.",
    "cases": [
        {
            "input": {
                "op": "create",
                "geometry": {
                    "type": "multipoint",
                    "points": [
                        [
                            5,
                            50
                        ],
                        [
                            6,
                            51
                        ]
                    ]
                }
            },
            "expected_output": "type=MULTIPOINT\ndimensions=0\nnshape=1\nwkt=MULTIPOINT ((5 50), (6 51))\n"
        }
    ]
}
```


*1.3 LineString — I want to construct a connected path through ordered vertices.*

A `linestring` geometry carries a `coords` [structure type for hole data] of vertices. A non-empty line has dimension 1 and one shape; an unset or empty vertex list yields the empty line.

**Test Cases:** `rcb_tests/public_test_cases/feature03_linestring.json`

```json
{
    "description": "Construct a linestring geography from an ordered sequence of longitude/latitude vertices. A non-empty linestring has dimension 1 and a single shape. Supplying no vertices (unset or an empty sequence) yields the empty linestring.",
    "cases": [
        {
            "input": {
                "op": "create",
                "geometry": {
                    "type": "linestring",
                    "coords": [
                        [
                            5,
                            50
                        ],
                        [
                            6,
                            51
                        ]
                    ]
                }
            },
            "expected_output": "type=LINESTRING\ndimensions=1\nnshape=1\nwkt=LINESTRING (5 50, 6 51)\n"
        },
        {
            "input": {
                "op": "create",
                "geometry": {
                    "type": "linestring"
                }
            },
            "expected_output": "type=LINESTRING\ndimensions=1\nnshape=0\nwkt=LINESTRING EMPTY\n"
        }
    ]
}
```


*1.4 MultiLineString — I want to aggregate several lines into one shape.*

A `multilinestring` geometry carries a `lines` list, each element being a vertex list. The shape count equals the number of lines.

**Test Cases:** `rcb_tests/public_test_cases/feature04_multilinestring.json`

```json
{
    "description": "Construct a multilinestring geography from several ordered vertex sequences, each describing one line. The result has dimension 1 and a shape count equal to the number of supplied lines.",
    "cases": [
        {
            "input": {
                "op": "create",
                "geometry": {
                    "type": "multilinestring",
                    "lines": [
                        [
                            [
                                5,
                                50
                            ],
                            [
                                6,
                                51
                            ]
                        ],
                        [
                            [
                                15,
                                60
                            ],
                            [
                                16,
                                61
                            ]
                        ]
                    ]
                }
            },
            "expected_output": "type=MULTILINESTRING\ndimensions=1\nnshape=2\nwkt=MULTILINESTRING ((5 50, 6 51), (15 60, 16 61))\n"
        }
    ]
}
```


*1.5 Polygon — I want to construct an areal region with an optional set of holes.*

A `polygon` geometry carries a `shell` vertex list and an optional `holes` list of rings. The shell is auto-closed when its last vertex does not repeat the first. Dimension is 2; an unset shell yields the empty polygon.

**Test Cases:** `rcb_tests/public_test_cases/feature05_polygon_basic.json`

```json
{
    "description": "Construct a polygon geography from a shell of longitude/latitude vertices, optionally with interior holes. The shell is automatically closed if the first vertex is not repeated as the last. A polygon has dimension 2 and a single shape. Supplying no shell yields the empty polygon.",
    "cases": [
        {
            "input": {
                "op": "create",
                "geometry": {
                    "type": "polygon",
                    "shell": [
                        [
                            0,
                            0
                        ],
                        [
                            2,
                            0
                        ],
                        [
                            2,
                            2
                        ],
                        [
                            0,
                            2
                        ]
                    ]
                }
            },
            "expected_output": "type=POLYGON\ndimensions=2\nnshape=1\nwkt=POLYGON ((0 0, 2 0, 2 2, 0 2, 0 0))\n"
        },
        {
            "input": {
                "op": "create",
                "geometry": {
                    "type": "polygon",
                    "shell": [
                        [
                            0,
                            0
                        ],
                        [
                            2,
                            0
                        ],
                        [
                            2,
                            2
                        ],
                        [
                            0,
                            2
                        ]
                    ],
                    "holes": [
                        [
                            [
                                0.5,
                                0.5
                            ],
                            [
                                1.5,
                                0.5
                            ],
                            [
                                1.5,
                                1.5
                            ],
                            [
                                0.5,
                                1.5
                            ]
                        ]
                    ]
                }
            },
            "expected_output": "type=POLYGON\ndimensions=2\nnshape=1\nwkt=POLYGON ((0 0, 2 0, 2 2, 0 2, 0 0), (0.5 1.5, 1.5 1.5, 1.5 0.5, 0.5 0.5, 0.5 1.5))\n"
        }
    ]
}
```


*1.6 Polygon Orientation & Normalization — I want to rely on deterministic ring winding.*

By default a ring is normalized so its interior is the smaller of the two regions it bounds, and the rendered vertex order reflects that normalization. Setting `oriented` to true preserves the supplied winding and takes the interior as given. Hole rings are normalized to the opposite winding of the shell.

**Test Cases:** `rcb_tests/public_test_cases/feature06_polygon_orientation.json`

```json
{
    "description": "Polygon construction normalizes ring orientation. By default the engine interprets a ring so that the enclosed interior is the smaller of the two regions it divides the sphere into, reordering vertices as needed; the canonical text rendering reflects the normalized order. When orientation is declared as already meaningful, the supplied vertex order is preserved and the interior is taken as given. Interior hole rings are normalized to the opposite winding of the shell.",
    "cases": [
        {
            "input": {
                "op": "create",
                "geometry": {
                    "type": "polygon",
                    "shell": [
                        [
                            0,
                            0
                        ],
                        [
                            0,
                            2
                        ],
                        [
                            2,
                            2
                        ],
                        [
                            2,
                            0
                        ]
                    ]
                }
            },
            "expected_output": "type=POLYGON\ndimensions=2\nnshape=1\nwkt=POLYGON ((2 0, 2 2, 0 2, 0 0, 2 0))\n"
        },
        {
            "input": {
                "op": "create",
                "geometry": {
                    "type": "polygon",
                    "shell": [
                        [
                            0,
                            0
                        ],
                        [
                            0,
                            2
                        ],
                        [
                            2,
                            2
                        ],
                        [
                            2,
                            0
                        ]
                    ],
                    "oriented": true
                }
            },
            "expected_output": "type=POLYGON\ndimensions=2\nnshape=1\nwkt=POLYGON ((0 0, 0 2, 2 2, 2 0, 0 0))\n"
        }
    ]
}
```


*1.7 MultiPolygon — I want to aggregate several polygons into one shape.*

A `multipolygon` geometry carries a `polygons` list, each entry a polygon spec (optionally with holes).

**Test Cases:** `rcb_tests/public_test_cases/feature07_multipolygon.json`

```json
{
    "description": "Construct a multipolygon geography from several polygons (each possibly having holes). The result has dimension 2 and a single shape aggregating the component polygons.",
    "cases": [
        {
            "input": {
                "op": "create",
                "geometry": {
                    "type": "multipolygon",
                    "polygons": [
                        {
                            "type": "polygon",
                            "shell": [
                                [
                                    0,
                                    0
                                ],
                                [
                                    2,
                                    0
                                ],
                                [
                                    2,
                                    2
                                ],
                                [
                                    0,
                                    2
                                ]
                            ]
                        },
                        {
                            "type": "polygon",
                            "shell": [
                                [
                                    4,
                                    0
                                ],
                                [
                                    6,
                                    0
                                ],
                                [
                                    6,
                                    2
                                ],
                                [
                                    4,
                                    2
                                ]
                            ],
                            "holes": [
                                [
                                    [
                                        4.5,
                                        0.5
                                    ],
                                    [
                                        5.5,
                                        0.5
                                    ],
                                    [
                                        5.5,
                                        1.5
                                    ],
                                    [
                                        4.5,
                                        1.5
                                    ]
                                ]
                            ]
                        }
                    ]
                }
            },
            "expected_output": "type=MULTIPOLYGON\ndimensions=2\nnshape=1\nwkt=MULTIPOLYGON (((0 0, 2 0, 2 2, 0 2, 0 0)), ((4 0, 6 0, 6 2, 4 2, 4 0), (4.5 1.5, 5.5 1.5, 5.5 0.5, 4.5 0.5, 4.5 1.5)))\n"
        }
    ]
}
```


*1.8 GeometryCollection — I want to group geographies of mixed types.*

A `collection` geometry carries a `geometries` list of arbitrary geometry specs. It reports a mixed-dimension marker, a total shape count, and a rendering listing each member.

**Test Cases:** `rcb_tests/public_test_cases/feature08_collection.json`

```json
{
    "description": "Construct a heterogeneous geometry collection from a list of geographies of any types. The collection reports a mixed dimension marker and a shape count equal to the total number of contained shapes; its text rendering lists each member.",
    "cases": [
        {
            "input": {
                "op": "create",
                "geometry": {
                    "type": "collection",
                    "geometries": [
                        {
                            "type": "point",
                            "coords": [
                                0,
                                0
                            ]
                        },
                        {
                            "type": "linestring",
                            "coords": [
                                [
                                    0,
                                    0
                                ],
                                [
                                    1,
                                    1
                                ]
                            ]
                        },
                        {
                            "type": "polygon",
                            "shell": [
                                [
                                    0,
                                    0
                                ],
                                [
                                    1,
                                    0
                                ],
                                [
                                    1,
                                    1
                                ]
                            ]
                        }
                    ]
                }
            },
            "expected_output": "type=GEOMETRYCOLLECTION\ndimensions=[special dimension value for abortable collections]\nnshape=3\nwkt=GEOMETRYCOLLECTION (POINT (0 0), LINESTRING (0 0, 1 1), POLYGON ((0 0, 1 0, 1 1, 0 0)))\n"
        }
    ]
}
```


---

### Feature 2: Construction Validation

**As a developer**, I want a reliable contract for construction validation, so I can build correct geospatial behavior without re-deriving spherical geometry myself.

Construction is total: malformed requests never produce a wrong geography, they produce a normalized error contract instead. Errors are emitted as an `error=<category>` line, optionally followed by a `detail=` line carrying a domain-level explanation. Error output never reveals host-language runtime identity.


*2.1 Component Type Checking — I want to be told when a container is given the wrong element type.*

Homogeneous containers (multipoint, linestring, multilinestring, polygon ring, multipolygon) require all components to share the element type they expect. A mismatch yields `error=type_mismatch` and a detail naming the expected and the encountered type.

**Test Cases:** `rcb_tests/public_test_cases/feature09_type_validation.json`

```json
{
    "description": "Construction of a homogeneous container geography rejects component geographies whose type does not match the container's required element type, reporting a normalized type-mismatch error that names the expected and the encountered geometry type.",
    "cases": [
        {
            "input": {
                "op": "create",
                "geometry": {
                    "type": "multipoint",
                    "components": [
                        {
                            "type": "point",
                            "coords": [
                                5,
                                50
                            ]
                        },
                        {
                            "type": "linestring",
                            "coords": [
                                [
                                    5,
                                    50
                                ],
                                [
                                    6,
                                    61
                                ]
                            ]
                        }
                    ]
                }
            },
            "expected_output": "error=type_mismatch\ndetail=invalid Geography type (expected POINT, found LINESTRING)\n"
        },
        {
            "input": {
                "op": "create",
                "geometry": {
                    "type": "polygon",
                    "shell_geometries": [
                        {
                            "type": "point",
                            "coords": [
                                0,
                                0
                            ]
                        },
                        {
                            "type": "point",
                            "coords": [
                                2,
                                0
                            ]
                        },
                        {
                            "type": "point",
                            "coords": [
                                2,
                                2
                            ]
                        },
                        {
                            "type": "point",
                            "coords": [
                                0,
                                2
                            ]
                        },
                        {
                            "type": "linestring",
                            "coords": [
                                [
                                    5,
                                    50
                                ],
                                [
                                    6,
                                    61
                                ]
                            ]
                        }
                    ]
                }
            },
            "expected_output": "error=type_mismatch\ndetail=invalid Geography type (expected POINT, found LINESTRING)\n"
        }
    ]
}
```


*2.2 Geometric Validity Checking — I want to be told when coordinates do not form a valid geometry.*

Validity rules are enforced: lines need at least two vertices, polygon rings at least three, no empty components, no duplicate consecutive vertices, no self-crossing or mutually crossing rings, consistent ring orientation when orientation is declared meaningful, and no holes on an empty shell. Violations yield `error=invalid_geometry` with an explanatory detail.

**Test Cases:** `rcb_tests/public_test_cases/feature10_geometry_validation.json`

```json
{
    "description": "Construction rejects geographies that violate geometric validity rules, reporting a normalized invalid-geometry error whose detail explains the violation. Rules include the minimum vertex counts for lines and polygon rings, the prohibition of empty components, of duplicate consecutive vertices, of self-crossing or mutually crossing rings, of inconsistent ring orientations when orientation is declared meaningful, and of holes attached to an empty shell.",
    "cases": [
        {
            "input": {
                "op": "create",
                "geometry": {
                    "type": "linestring",
                    "coords": [
                        [
                            5,
                            50
                        ]
                    ]
                }
            },
            "expected_output": "error=invalid_geometry\ndetail=linestring is not valid: it must have at least 2 vertices\n"
        },
        {
            "input": {
                "op": "create",
                "geometry": {
                    "type": "polygon",
                    "shell": [
                        [
                            0,
                            0
                        ],
                        [
                            0,
                            2
                        ],
                        [
                            0,
                            2
                        ],
                        [
                            2,
                            0
                        ]
                    ]
                }
            },
            "expected_output": "error=invalid_geometry\ndetail=polygon is not valid: Loop 0: Edge 1 is degenerate (duplicate vertex)\n"
        }
    ]
}
```


---

### Feature 3: Geometry Properties & Identity

**As a developer**, I want a reliable contract for geometry properties & identity, so I can build correct geospatial behavior without re-deriving spherical geometry myself.

Beyond construction, geographies can be inspected in bulk and compared. Bulk inspections operate over a sequence of values and report one result per element.


*3.1 Type Classification — I want to classify each geography in a batch by its type.*

A `properties` request named `get_type_id` over a `values` list emits one `i=TYPENAME` line per element.

**Test Cases:** `rcb_tests/public_test_cases/feature11_get_type_id.json`

```json
{
    "description": "Report the geometry type of each geography in a sequence as a stable type name. Both single-shape and multi-shape geographies, including collections and polygons with holes, are classified by their top-level type.",
    "cases": [
        {
            "input": {
                "op": "properties",
                "name": "get_type_id",
                "values": [
                    {
                        "type": "point",
                        "coords": [
                            45,
                            50
                        ]
                    },
                    {
                        "type": "multipoint",
                        "points": [
                            [
                                5,
                                50
                            ],
                            [
                                6,
                                51
                            ]
                        ]
                    },
                    {
                        "type": "linestring",
                        "coords": [
                            [
                                5,
                                50
                            ],
                            [
                                6,
                                51
                            ]
                        ]
                    },
                    {
                        "type": "multilinestring",
                        "lines": [
                            [
                                [
                                    5,
                                    50
                                ],
                                [
                                    6,
                                    51
                                ]
                            ],
                            [
                                [
                                    15,
                                    60
                                ],
                                [
                                    16,
                                    61
                                ]
                            ]
                        ]
                    },
                    {
                        "type": "polygon",
                        "shell": [
                            [
                                5,
                                50
                            ],
                            [
                                5,
                                60
                            ],
                            [
                                6,
                                60
                            ],
                            [
                                6,
                                51
                            ]
                        ]
                    },
                    {
                        "type": "polygon",
                        "shell": [
                            [
                                5,
                                60
                            ],
                            [
                                6,
                                60
                            ],
                            [
                                6,
                                50
                            ],
                            [
                                5,
                                50
                            ]
                        ],
                        "holes": [
                            [
                                [
                                    5.1,
                                    59
                                ],
                                [
                                    5.9,
                                    59
                                ],
                                [
                                    5.9,
                                    51
                                ],
                                [
                                    5.1,
                                    51
                                ]
                            ]
                        ]
                    },
                    {
                        "type": "multipolygon",
                        "polygons": [
                            {
                                "type": "polygon",
                                "shell": [
                                    [
                                        5,
                                        50
                                    ],
                                    [
                                        5,
                                        60
                                    ],
                                    [
                                        6,
                                        60
                                    ],
                                    [
                                        6,
                                        51
                                    ]
                                ]
                            },
                            {
                                "type": "polygon",
                                "shell": [
                                    [
                                        10,
                                        100
                                    ],
                                    [
                                        10,
                                        160
                                    ],
                                    [
                                        11,
                                        160
                                    ],
                                    [
                                        11,
                                        100
                                    ]
                                ]
                            }
                        ]
                    },
                    {
                        "type": "collection",
                        "geometries": [
                            {
                                "type": "point",
                                "coords": [
                                    40,
                                    50
                                ]
                            }
                        ]
                    }
                ]
            },
            "expected_output": "0=POINT\n1=MULTIPOINT\n2=LINESTRING\n3=MULTILINESTRING\n4=POLYGON\n5=POLYGON\n6=MULTIPOLYGON\n7=GEOMETRYCOLLECTION\n"
        }
    ]
}
```


*3.2 Dimension Reporting — I want to read the topological dimension of each geography in a batch.*

A `properties` request named `get_dimensions` emits one `i=<dim>` line per element (0 for points, 1 for lines, 2 for areal).

**Test Cases:** `rcb_tests/public_test_cases/feature12_get_dimensions.json`

```json
{
    "description": "Report the topological dimension of each geography in a sequence: points are dimension 0, lines are dimension 1, areal geographies are dimension 2.",
    "cases": [
        {
            "input": {
                "op": "properties",
                "name": "get_dimensions",
                "values": [
                    {
                        "type": "point",
                        "coords": [
                            5,
                            40
                        ]
                    },
                    {
                        "type": "point",
                        "coords": [
                            6,
                            30
                        ]
                    },
                    {
                        "type": "linestring",
                        "coords": [
                            [
                                5,
                                50
                            ],
                            [
                                6,
                                51
                            ]
                        ]
                    },
                    {
                        "type": "point",
                        "coords": [
                            4,
                            20
                        ]
                    }
                ]
            },
            "expected_output": "0=0\n1=0\n2=1\n3=0\n"
        }
    ]
}
```


*3.3 Geography Predicate — I want to distinguish geography objects from plain values in a mixed batch.*

A `properties` request named `is_geography` over a `values` list (entries are geometry specs or `{"number": x}` scalars) emits one `i=true|false` line per element.

**Test Cases:** `rcb_tests/public_test_cases/feature13_is_geography.json`

```json
{
    "description": "Classify each element of a heterogeneous sequence, reporting whether it is a geography object as opposed to a plain numeric value.",
    "cases": [
        {
            "input": {
                "op": "properties",
                "name": "is_geography",
                "values": [
                    {
                        "number": 1
                    },
                    {
                        "number": 2.33
                    },
                    {
                        "type": "point",
                        "coords": [
                            30,
                            6
                        ]
                    }
                ]
            },
            "expected_output": "0=false\n1=false\n2=true\n"
        }
    ]
}
```


*3.4 Structural Equality — I want to compare geographies for shape equality regardless of vertex order.*

A `properties` request named `equality` over a `pairs` list emits one `i=true|false` line per pair. Equality ignores the starting vertex and direction of rings and closed lines; differing types or shapes compare unequal.

**Test Cases:** `rcb_tests/public_test_cases/feature14_equality.json`

```json
{
    "description": "Compare two geographies for structural equality. Equality is independent of the starting vertex and direction of a ring or closed line, so geographies that describe the same shape compare equal even when their vertex sequences differ; geographies of different types or shapes compare unequal.",
    "cases": [
        {
            "input": {
                "op": "properties",
                "name": "equality",
                "pairs": [
                    {
                        "a": {
                            "type": "point",
                            "coords": [
                                1,
                                1
                            ]
                        },
                        "b": {
                            "type": "point",
                            "coords": [
                                1,
                                1
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "point",
                            "coords": [
                                1,
                                1
                            ]
                        },
                        "b": {
                            "type": "point",
                            "coords": [
                                1,
                                1
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "point",
                            "coords": [
                                1,
                                1
                            ]
                        },
                        "b": {
                            "type": "point",
                            "coords": [
                                2,
                                2
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "linestring",
                            "coords": [
                                [
                                    1,
                                    1
                                ],
                                [
                                    2,
                                    2
                                ],
                                [
                                    3,
                                    3
                                ]
                            ]
                        },
                        "b": {
                            "type": "linestring",
                            "coords": [
                                [
                                    3,
                                    3
                                ],
                                [
                                    2,
                                    2
                                ],
                                [
                                    1,
                                    1
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "polygon",
                            "shell": [
                                [
                                    1,
                                    1
                                ],
                                [
                                    3,
                                    1
                                ],
                                [
                                    2,
                                    3
                                ]
                            ]
                        },
                        "b": {
                            "type": "polygon",
                            "shell": [
                                [
                                    2,
                                    3
                                ],
                                [
                                    1,
                                    1
                                ],
                                [
                                    3,
                                    1
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "polygon",
                            "shell": [
                                [
                                    2,
                                    3
                                ],
                                [
                                    1,
                                    1
                                ],
                                [
                                    3,
                                    1
                                ]
                            ]
                        },
                        "b": {
                            "type": "polygon",
                            "shell": [
                                [
                                    2,
                                    3
                                ],
                                [
                                    3,
                                    1
                                ],
                                [
                                    1,
                                    1
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "polygon",
                            "shell": [
                                [
                                    1,
                                    1
                                ],
                                [
                                    3,
                                    1
                                ],
                                [
                                    2,
                                    3
                                ]
                            ]
                        },
                        "b": {
                            "type": "polygon",
                            "shell": [
                                [
                                    2,
                                    3
                                ],
                                [
                                    3,
                                    1
                                ],
                                [
                                    1,
                                    1
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "point",
                            "coords": [
                                1,
                                1
                            ]
                        },
                        "b": {
                            "type": "polygon",
                            "shell": [
                                [
                                    1,
                                    1
                                ],
                                [
                                    3,
                                    1
                                ],
                                [
                                    2,
                                    3
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "linestring",
                            "coords": [
                                [
                                    1,
                                    1
                                ],
                                [
                                    2,
                                    2
                                ],
                                [
                                    3,
                                    3
                                ]
                            ]
                        },
                        "b": {
                            "type": "polygon",
                            "shell": [
                                [
                                    1,
                                    1
                                ],
                                [
                                    3,
                                    1
                                ],
                                [
                                    2,
                                    3
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "collection",
                            "geometries": [
                                {
                                    "type": "point",
                                    "coords": [
                                        40,
                                        50
                                    ]
                                }
                            ]
                        },
                        "b": {
                            "type": "collection",
                            "geometries": [
                                {
                                    "type": "point",
                                    "coords": [
                                        40,
                                        50
                                    ]
                                }
                            ]
                        }
                    }
                ]
            },
            "expected_output": "0=true\n1=true\n2=false\n3=true\n4=true\n5=true\n6=true\n7=false\n8=false\n9=true\n"
        }
    ]
}
```


*3.5 Prepared-State Lifecycle — I want to toggle and observe a geography's prepared (indexed) state.*

A `prepare` request over a `values` list reports the per-element prepared state across the lifecycle as three lines: `initial=[...]`, `prepared=[...]`, `destroyed=[...]`.

**Test Cases:** `rcb_tests/public_test_cases/feature15_prepare.json`

```json
{
    "description": "Manage the prepared (spatial-index) state of a sequence of geographies. Geographies start unprepared; preparing them flips the state on; destroying the prepared state flips it back off. The state is observable per element across the lifecycle.",
    "cases": [
        {
            "input": {
                "op": "prepare",
                "values": [
                    {
                        "type": "point",
                        "coords": [
                            50,
                            45
                        ]
                    },
                    {
                        "type": "linestring",
                        "coords": [
                            [
                                5,
                                50
                            ],
                            [
                                6,
                                51
                            ]
                        ]
                    }
                ]
            },
            "expected_output": "initial=[false, false]\nprepared=[true, true]\ndestroyed=[false, false]\n"
        }
    ]
}
```


---

### Feature 4: Spatial Predicates

**As a developer**, I want a reliable contract for spatial predicates, so I can build correct geospatial behavior without re-deriving spherical geometry myself.

Topological predicates evaluate a boolean relationship for each ordered pair of geographies. A `predicate` request names the relation and supplies a `pairs` list; the output is a header line `predicate=<name>` followed by one `i=true|false` line per pair.


*4.1 Intersects — I want to test whether two geographies share any point.*

True when the operands have at least one point in common.

**Test Cases:** `rcb_tests/public_test_cases/feature16_intersects.json`

```json
{
    "description": "Evaluate, for each ordered pair of geographies, whether they share at least one point in common.",
    "cases": [
        {
            "input": {
                "op": "predicate",
                "name": "intersects",
                "pairs": [
                    {
                        "a": {
                            "type": "linestring",
                            "coords": [
                                [
                                    40,
                                    8
                                ],
                                [
                                    60,
                                    8
                                ]
                            ]
                        },
                        "b": {
                            "type": "linestring",
                            "coords": [
                                [
                                    50,
                                    5
                                ],
                                [
                                    50,
                                    10
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "linestring",
                            "coords": [
                                [
                                    20,
                                    0
                                ],
                                [
                                    30,
                                    0
                                ]
                            ]
                        },
                        "b": {
                            "type": "linestring",
                            "coords": [
                                [
                                    50,
                                    5
                                ],
                                [
                                    50,
                                    10
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "point",
                            "coords": [
                                50,
                                8
                            ]
                        },
                        "b": {
                            "type": "point",
                            "coords": [
                                20,
                                5
                            ]
                        }
                    }
                ]
            },
            "expected_output": "predicate=intersects\n0=true\n1=false\n2=false\n"
        }
    ]
}
```


*4.2 Equals — I want to test whether two geographies are the same point set.*

True when both operands cover exactly the same points.

**Test Cases:** `rcb_tests/public_test_cases/feature17_equals.json`

```json
{
    "description": "Evaluate, for each ordered pair of geographies, whether they represent the same point set.",
    "cases": [
        {
            "input": {
                "op": "predicate",
                "name": "equals",
                "pairs": [
                    {
                        "a": {
                            "type": "linestring",
                            "coords": [
                                [
                                    40,
                                    8
                                ],
                                [
                                    60,
                                    8
                                ]
                            ]
                        },
                        "b": {
                            "type": "point",
                            "coords": [
                                50,
                                8
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "linestring",
                            "coords": [
                                [
                                    20,
                                    0
                                ],
                                [
                                    30,
                                    0
                                ]
                            ]
                        },
                        "b": {
                            "type": "point",
                            "coords": [
                                50,
                                8
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "point",
                            "coords": [
                                50,
                                8
                            ]
                        },
                        "b": {
                            "type": "point",
                            "coords": [
                                50,
                                8
                            ]
                        }
                    }
                ]
            },
            "expected_output": "predicate=equals\n0=false\n1=false\n2=true\n"
        }
    ]
}
```


*4.3 Contains — I want to test whether one geography contains another.*

True when every point of the second operand lies in the first. A polygon does not contain a point inside one of its holes.

**Test Cases:** `rcb_tests/public_test_cases/feature18_contains.json`

```json
{
    "description": "Evaluate, for each ordered pair, whether the first geography contains the second. A polygon with an interior hole does not contain a point lying inside that hole.",
    "cases": [
        {
            "input": {
                "op": "predicate",
                "name": "contains",
                "pairs": [
                    {
                        "a": {
                            "type": "linestring",
                            "coords": [
                                [
                                    40,
                                    8
                                ],
                                [
                                    60,
                                    8
                                ]
                            ]
                        },
                        "b": {
                            "type": "point",
                            "coords": [
                                40,
                                8
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "linestring",
                            "coords": [
                                [
                                    20,
                                    0
                                ],
                                [
                                    30,
                                    0
                                ]
                            ]
                        },
                        "b": {
                            "type": "point",
                            "coords": [
                                40,
                                8
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "linestring",
                            "coords": [
                                [
                                    50,
                                    8
                                ],
                                [
                                    60,
                                    8
                                ]
                            ]
                        },
                        "b": {
                            "type": "point",
                            "coords": [
                                50,
                                8
                            ]
                        }
                    }
                ]
            },
            "expected_output": "predicate=contains\n0=true\n1=false\n2=true\n"
        }
    ]
}
```


*4.4 Within — I want to test whether one geography lies within another.*

True when every point of the first operand lies in the second. A point inside a polygon hole is not within the polygon.

**Test Cases:** `rcb_tests/public_test_cases/feature19_within.json`

```json
{
    "description": "Evaluate, for each ordered pair, whether the first geography lies within the second. A point inside a polygon's hole is not within that polygon.",
    "cases": [
        {
            "input": {
                "op": "predicate",
                "name": "within",
                "pairs": [
                    {
                        "a": {
                            "type": "point",
                            "coords": [
                                40,
                                8
                            ]
                        },
                        "b": {
                            "type": "linestring",
                            "coords": [
                                [
                                    40,
                                    8
                                ],
                                [
                                    60,
                                    8
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "point",
                            "coords": [
                                40,
                                8
                            ]
                        },
                        "b": {
                            "type": "linestring",
                            "coords": [
                                [
                                    20,
                                    0
                                ],
                                [
                                    30,
                                    0
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "point",
                            "coords": [
                                50,
                                8
                            ]
                        },
                        "b": {
                            "type": "linestring",
                            "coords": [
                                [
                                    50,
                                    8
                                ],
                                [
                                    60,
                                    8
                                ]
                            ]
                        }
                    }
                ]
            },
            "expected_output": "predicate=within\n0=true\n1=false\n2=true\n"
        }
    ]
}
```


*4.5 Disjoint — I want to test whether two geographies share no point.*

True when the operands have no point in common.

**Test Cases:** `rcb_tests/public_test_cases/feature20_disjoint.json`

```json
{
    "description": "Evaluate, for each ordered pair of geographies, whether they share no point in common.",
    "cases": [
        {
            "input": {
                "op": "predicate",
                "name": "disjoint",
                "pairs": [
                    {
                        "a": {
                            "type": "point",
                            "coords": [
                                40,
                                9
                            ]
                        },
                        "b": {
                            "type": "linestring",
                            "coords": [
                                [
                                    40,
                                    8
                                ],
                                [
                                    60,
                                    8
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "point",
                            "coords": [
                                40,
                                9
                            ]
                        },
                        "b": {
                            "type": "linestring",
                            "coords": [
                                [
                                    20,
                                    0
                                ],
                                [
                                    30,
                                    0
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "point",
                            "coords": [
                                50,
                                9
                            ]
                        },
                        "b": {
                            "type": "linestring",
                            "coords": [
                                [
                                    50,
                                    8
                                ],
                                [
                                    60,
                                    8
                                ]
                            ]
                        }
                    }
                ]
            },
            "expected_output": "predicate=disjoint\n0=true\n1=true\n2=true\n"
        }
    ]
}
```


*4.6 Touches — I want to test whether two geographies meet only on their boundaries.*

True when the operands share a boundary point but their interiors do not meet. Points have no boundary, so two points never touch, yet a point can touch a line endpoint.

**Test Cases:** `rcb_tests/public_test_cases/feature21_touches.json`

```json
{
    "description": "Evaluate, for each ordered pair, whether the geographies touch: they have at least one boundary point in common but their interiors do not intersect. Points have no boundary, so two points never touch, but a point can touch a line at its endpoint.",
    "cases": [
        {
            "input": {
                "op": "predicate",
                "name": "touches",
                "pairs": [
                    {
                        "a": {
                            "type": "polygon",
                            "shell": [
                                [
                                    0.0,
                                    0.0
                                ],
                                [
                                    0.0,
                                    1.0
                                ],
                                [
                                    1.0,
                                    1.0
                                ],
                                [
                                    1.0,
                                    0.0
                                ]
                            ]
                        },
                        "b": {
                            "type": "polygon",
                            "shell": [
                                [
                                    1.0,
                                    1.0
                                ],
                                [
                                    1.0,
                                    2.0
                                ],
                                [
                                    2.0,
                                    2.0
                                ],
                                [
                                    2.0,
                                    1.0
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "polygon",
                            "shell": [
                                [
                                    0.0,
                                    0.0
                                ],
                                [
                                    0.0,
                                    1.0
                                ],
                                [
                                    1.0,
                                    1.0
                                ],
                                [
                                    1.0,
                                    0.0
                                ]
                            ]
                        },
                        "b": {
                            "type": "polygon",
                            "shell": [
                                [
                                    0.5,
                                    0.5
                                ],
                                [
                                    0.5,
                                    1.5
                                ],
                                [
                                    1.5,
                                    1.5
                                ],
                                [
                                    1.5,
                                    0.5
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "point",
                            "coords": [
                                1.0,
                                1.0
                            ]
                        },
                        "b": {
                            "type": "point",
                            "coords": [
                                1.0,
                                1.0
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "point",
                            "coords": [
                                1.0,
                                1.0
                            ]
                        },
                        "b": {
                            "type": "linestring",
                            "coords": [
                                [
                                    1.0,
                                    1.0
                                ],
                                [
                                    1.0,
                                    2.0
                                ]
                            ]
                        }
                    }
                ]
            },
            "expected_output": "predicate=touches\n0=true\n1=false\n2=false\n3=true\n"
        }
    ]
}
```


*4.7 Covers — I want to test whether one geography covers another.*

True when every point of the second operand lies in the first, boundary included.

**Test Cases:** `rcb_tests/public_test_cases/feature22_covers.json`

```json
{
    "description": "Evaluate, for each ordered pair, whether the first geography covers the second, i.e. every point of the second lies in the first (including its boundary). A reference areal region is tested against points, lines and polygons that fall outside it, cross it, lie on its boundary, or lie in its interior.",
    "cases": [
        {
            "input": {
                "op": "predicate",
                "name": "covers",
                "pairs": [
                    {
                        "a": {
                            "type": "polygon",
                            "shell": [
                                [
                                    [special dimension value for abortable collections]18,
                                    60
                                ],
                                [
                                    [special dimension value for abortable collections]18,
                                    40
                                ],
                                [
                                    -118,
                                    23
                                ],
                                [
                                    34,
                                    23
                                ],
                                [
                                    34,
                                    40
                                ],
                                [
                                    34,
                                    60
                                ]
                            ]
                        },
                        "b": {
                            "type": "point",
                            "coords": [
                                -120.0,
                                70.0
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -118,
                                    60
                                ],
                                [
                                    -118,
                                    40
                                ],
                                [
                                    -118,
                                    23
                                ],
                                [
                                    34,
                                    23
                                ],
                                [
                                    34,
                                    40
                                ],
                                [
                                    34,
                                    60
                                ]
                            ]
                        },
                        "b": {
                            "type": "point",
                            "coords": [
                                -118.0,
                                41.0
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -118,
                                    60
                                ],
                                [
                                    -118,
                                    40
                                ],
                                [
                                    -118,
                                    23
                                ],
                                [
                                    34,
                                    23
                                ],
                                [
                                    34,
                                    40
                                ],
                                [
                                    34,
                                    60
                                ]
                            ]
                        },
                        "b": {
                            "type": "point",
                            "coords": [
                                -116.0,
                                37.0
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -118,
                                    60
                                ],
                                [
                                    -118,
                                    40
                                ],
                                [
                                    -118,
                                    23
                                ],
                                [
                                    34,
                                    23
                                ],
                                [
                                    34,
                                    40
                                ],
                                [
                                    34,
                                    60
                                ]
                            ]
                        },
                        "b": {
                            "type": "linestring",
                            "coords": [
                                [
                                    -120.0,
                                    70.0
                                ],
                                [
                                    -116.0,
                                    37.0
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -118,
                                    60
                                ],
                                [
                                    -118,
                                    40
                                ],
                                [
                                    -118,
                                    23
                                ],
                                [
                                    34,
                                    23
                                ],
                                [
                                    34,
                                    40
                                ],
                                [
                                    34,
                                    60
                                ]
                            ]
                        },
                        "b": {
                            "type": "linestring",
                            "coords": [
                                [
                                    -118.0,
                                    41.0
                                ],
                                [
                                    -118.0,
                                    23.0
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -118,
                                    60
                                ],
                                [
                                    -118,
                                    40
                                ],
                                [
                                    -118,
                                    23
                                ],
                                [
                                    34,
                                    23
                                ],
                                [
                                    34,
                                    40
                                ],
                                [
                                    34,
                                    60
                                ]
                            ]
                        },
                        "b": {
                            "type": "linestring",
                            "coords": [
                                [
                                    -117.0,
                                    39.0
                                ],
                                [
                                    -115.0,
                                    37.0
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -118,
                                    60
                                ],
                                [
                                    -118,
                                    40
                                ],
                                [
                                    -118,
                                    23
                                ],
                                [
                                    34,
                                    23
                                ],
                                [
                                    34,
                                    40
                                ],
                                [
                                    34,
                                    60
                                ]
                            ]
                        },
                        "b": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -120.0,
                                    41.0
                                ],
                                [
                                    -120.0,
                                    35.0
                                ],
                                [
                                    -115.0,
                                    35.0
                                ],
                                [
                                    -115.0,
                                    41.0
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -118,
                                    60
                                ],
                                [
                                    -118,
                                    40
                                ],
                                [
                                    -118,
                                    23
                                ],
                                [
                                    34,
                                    23
                                ],
                                [
                                    34,
                                    40
                                ],
                                [
                                    34,
                                    60
                                ]
                            ]
                        },
                        "b": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -118.0,
                                    40.0
                                ],
                                [
                                    -118.0,
                                    23.0
                                ],
                                [
                                    34.0,
                                    23.0
                                ],
                                [
                                    34.0,
                                    40.0
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -118,
                                    60
                                ],
                                [
                                    -118,
                                    40
                                ],
                                [
                                    -118,
                                    23
                                ],
                                [
                                    34,
                                    23
                                ],
                                [
                                    34,
                                    40
                                ],
                                [
                                    34,
                                    60
                                ]
                            ]
                        },
                        "b": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -117.0,
                                    40.0
                                ],
                                [
                                    -117.0,
                                    35.0
                                ],
                                [
                                    -115.0,
                                    35.0
                                ],
                                [
                                    -115.0,
                                    40.0
                                ]
                            ]
                        }
                    }
                ]
            },
            "expected_output": "predicate=covers\n0=false\n1=true\n2=true\n3=false\n4=true\n5=true\n6=false\n7=true\n8=true\n"
        }
    ]
}
```


*4.8 Covered By — I want to test whether one geography is covered by another.*

True when every point of the first operand lies in the second, boundary included.

**Test Cases:** `rcb_tests/public_test_cases/feature23_covered_by.json`

```json
{
    "description": "Evaluate, for each ordered pair, whether the first geography is covered by the second, i.e. every point of the first lies in the second (including its boundary). Points, lines and polygons are tested against a reference areal region that they fall outside of, cross, lie on the boundary of, or lie in the interior of.",
    "cases": [
        {
            "input": {
                "op": "predicate",
                "name": "covered_by",
                "pairs": [
                    {
                        "a": {
                            "type": "point",
                            "coords": [
                                -120.0,
                                70.0
                            ]
                        },
                        "b": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -118,
                                    60
                                ],
                                [
                                    -118,
                                    40
                                ],
                                [
                                    -118,
                                    23
                                ],
                                [
                                    34,
                                    23
                                ],
                                [
                                    34,
                                    40
                                ],
                                [
                                    34,
                                    60
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "point",
                            "coords": [
                                -118.0,
                                41.0
                            ]
                        },
                        "b": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -118,
                                    60
                                ],
                                [
                                    -118,
                                    40
                                ],
                                [
                                    -118,
                                    23
                                ],
                                [
                                    34,
                                    23
                                ],
                                [
                                    34,
                                    40
                                ],
                                [
                                    34,
                                    60
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "point",
                            "coords": [
                                -116.0,
                                37.0
                            ]
                        },
                        "b": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -118,
                                    60
                                ],
                                [
                                    -118,
                                    40
                                ],
                                [
                                    -118,
                                    23
                                ],
                                [
                                    34,
                                    23
                                ],
                                [
                                    34,
                                    40
                                ],
                                [
                                    34,
                                    60
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "linestring",
                            "coords": [
                                [
                                    -120.0,
                                    70.0
                                ],
                                [
                                    -116.0,
                                    37.0
                                ]
                            ]
                        },
                        "b": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -118,
                                    60
                                ],
                                [
                                    -118,
                                    40
                                ],
                                [
                                    -118,
                                    23
                                ],
                                [
                                    34,
                                    23
                                ],
                                [
                                    34,
                                    40
                                ],
                                [
                                    34,
                                    60
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "linestring",
                            "coords": [
                                [
                                    -118.0,
                                    41.0
                                ],
                                [
                                    -118.0,
                                    23.0
                                ]
                            ]
                        },
                        "b": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -118,
                                    60
                                ],
                                [
                                    -118,
                                    40
                                ],
                                [
                                    -118,
                                    23
                                ],
                                [
                                    34,
                                    23
                                ],
                                [
                                    34,
                                    40
                                ],
                                [
                                    34,
                                    60
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "linestring",
                            "coords": [
                                [
                                    -117.0,
                                    39.0
                                ],
                                [
                                    -115.0,
                                    37.0
                                ]
                            ]
                        },
                        "b": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -118,
                                    60
                                ],
                                [
                                    -118,
                                    40
                                ],
                                [
                                    -118,
                                    23
                                ],
                                [
                                    34,
                                    23
                                ],
                                [
                                    34,
                                    40
                                ],
                                [
                                    34,
                                    60
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -120.0,
                                    41.0
                                ],
                                [
                                    -120.0,
                                    35.0
                                ],
                                [
                                    -115.0,
                                    35.0
                                ],
                                [
                                    -115.0,
                                    41.0
                                ]
                            ]
                        },
                        "b": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -118,
                                    60
                                ],
                                [
                                    -118,
                                    40
                                ],
                                [
                                    -118,
                                    23
                                ],
                                [
                                    34,
                                    23
                                ],
                                [
                                    34,
                                    40
                                ],
                                [
                                    34,
                                    60
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -118.0,
                                    40.0
                                ],
                                [
                                    -118.0,
                                    23.0
                                ],
                                [
                                    34.0,
                                    23.0
                                ],
                                [
                                    34.0,
                                    40.0
                                ]
                            ]
                        },
                        "b": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -118,
                                    60
                                ],
                                [
                                    -118,
                                    40
                                ],
                                [
                                    -118,
                                    23
                                ],
                                [
                                    34,
                                    23
                                ],
                                [
                                    34,
                                    40
                                ],
                                [
                                    34,
                                    60
                                ]
                            ]
                        }
                    },
                    {
                        "a": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -117.0,
                                    40.0
                                ],
                                [
                                    -117.0,
                                    35.0
                                ],
                                [
                                    -115.0,
                                    35.0
                                ],
                                [
                                    -115.0,
                                    40.0
                                ]
                            ]
                        },
                        "b": {
                            "type": "polygon",
                            "shell": [
                                [
                                    -118,
                                    60
                                ],
                                [
                                    -118,
                                    40
                                ],
                                [
                                    -118,
                                    23
                                ],
                                [
                                    34,
                                    23
                                ],
                                [
                                    34,
                                    40
                                ],
                                [
                                    34,
                                    60
                                ]
                            ]
                        }
                    }
                ]
            },
            "expected_output": "predicate=covered_by\n0=false\n1=true\n2=true\n3=false\n4=true\n5=true\n6=false\n7=true\n8=true\n"
        }
    ]
}
```


---

### Feature 5: Measures

**As a developer**, I want a reliable contract for measures, so I can build correct geospatial behavior without re-deriving spherical geometry myself.

Scalar measures return a single real number rendered at fixed precision. Each accepts an optional `radius`; a unit radius yields the angular measure, while the default radius yields a metric measure on a mean-Earth sphere.


*5.1 Distance — I want to measure the shortest separation between two geographies.*

A `measure` request named `distance` with operands `a` and `b` returns the shortest great-circle distance as `distance=<value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature24_distance.json`

```json
{
    "description": "Compute the shortest great-circle distance between two geographies, in meters by default. An optional sphere radius rescales the result; supplying a unit radius yields the distance as an angle in radians.",
    "cases": [
        {
            "input": {
                "op": "measure",
                "name": "distance",
                "a": {
                    "type": "point",
                    "coords": [
                        0,
                        0
                    ]
                },
                "b": {
                    "type": "point",
                    "coords": [
                        0,
                        90
                    ]
                }
            },
            "expected_output": "distance=10007559.105974\n"
        },
        {
            "input": {
                "op": "measure",
                "name": "distance",
                "a": {
                    "type": "point",
                    "coords": [
                        0,
                        90
                    ]
                },
                "b": {
                    "type": "point",
                    "coords": [
                        0,
                        0
                    ]
                },
                "radius": 1
            },
            "expected_output": "distance=1.570796\n"
        }
    ]
}
```


*5.2 Area — I want to measure the enclosed area of an areal geography.*

A `measure` request named `area` returns the enclosed spherical area. Geographies with no enclosed area return zero.

**Test Cases:** `rcb_tests/public_test_cases/feature25_area.json`

```json
{
    "description": "Compute the spherical area enclosed by an areal geography. An optional sphere radius rescales the result; a unit radius yields the area in steradians. Geographies with no enclosed area (points, lines, empties) have area zero.",
    "cases": [
        {
            "input": {
                "op": "measure",
                "name": "area",
                "a": {
                    "type": "polygon",
                    "shell": [
                        [
                            0,
                            0
                        ],
                        [
                            90,
                            0
                        ],
                        [
                            0,
                            90
                        ],
                        [
                            0,
                            0
                        ]
                    ]
                },
                "radius": 1
            },
            "expected_output": "area=1.570796\n"
        },
        {
            "input": {
                "op": "measure",
                "name": "area",
                "a": {
                    "wkt": "POINT (-64 45)"
                }
            },
            "expected_output": "area=0.000000\n"
        }
    ]
}
```


*5.3 Length — I want to measure the total length of a linear geography.*

A `measure` request named `length` returns the total spherical length. Non-linear geographies return zero.

**Test Cases:** `rcb_tests/public_test_cases/feature26_length.json`

```json
{
    "description": "Compute the total spherical length of a linear geography. An optional sphere radius rescales the result; a unit radius yields the length as an angle in radians. Non-linear geographies (points, polygons, empties) have length zero.",
    "cases": [
        {
            "input": {
                "op": "measure",
                "name": "length",
                "a": {
                    "type": "linestring",
                    "coords": [
                        [
                            0,
                            0
                        ],
                        [
                            1,
                            0
                        ]
                    ]
                },
                "radius": 1
            },
            "expected_output": "length=0.017453\n"
        },
        {
            "input": {
                "op": "measure",
                "name": "length",
                "a": {
                    "wkt": "POLYGON ((0 0, 0 1, 1 0, 0 0))"
                }
            },
            "expected_output": "length=0.000000\n"
        }
    ]
}
```


*5.4 Perimeter — I want to measure the boundary length of an areal geography.*

A `measure` request named `perimeter` returns the boundary length. Non-areal geographies return zero.

**Test Cases:** `rcb_tests/public_test_cases/feature27_perimeter.json`

```json
{
    "description": "Compute the spherical perimeter (boundary length) of an areal geography. An optional sphere radius rescales the result; a unit radius yields the perimeter as an angle in radians. Non-areal geographies (points, lines, empties) have perimeter zero.",
    "cases": [
        {
            "input": {
                "op": "measure",
                "name": "perimeter",
                "a": {
                    "type": "polygon",
                    "shell": [
                        [
                            0,
                            0
                        ],
                        [
                            0,
                            90
                        ],
                        [
                            90,
                            90
                        ],
                        [
                            90,
                            0
                        ],
                        [
                            0,
                            0
                        ]
                    ]
                },
                "radius": 1
            },
            "expected_output": "perimeter=4.712389\n"
        },
        {
            "input": {
                "op": "measure",
                "name": "perimeter",
                "a": {
                    "wkt": "LINESTRING (0 0, 1 0)"
                }
            },
            "expected_output": "perimeter=0.000000\n"
        }
    ]
}
```


---

### Feature 6: Accessors & Derived Geometry

**As a developer**, I want a reliable contract for accessors & derived geometry, so I can build correct geospatial behavior without re-deriving spherical geometry myself.

Accessors derive a value or a new geography from a single input geography.


*6.1 Centroid — I want to derive the centroid point of a geography.*

An `accessor` request named `centroid` returns a point geography as `type=` and `wkt=` lines.

**Test Cases:** `rcb_tests/public_test_cases/feature28_centroid.json`

```json
{
    "description": "Compute the centroid of a geography, returning it as a point geography given by its type name and text rendering.",
    "cases": [
        {
            "input": {
                "op": "accessor",
                "name": "centroid",
                "a": {
                    "type": "point",
                    "coords": [
                        0,
                        0
                    ]
                }
            },
            "expected_output": "type=POINT\nwkt=POINT (0 0)\n"
        },
        {
            "input": {
                "op": "accessor",
                "name": "centroid",
                "a": {
                    "type": "linestring",
                    "coords": [
                        [
                            0,
                            0
                        ],
                        [
                            2,
                            0
                        ]
                    ]
                }
            },
            "expected_output": "type=POINT\nwkt=POINT (1 0)\n"
        }
    ]
}
```


*6.2 Boundary — I want to derive the boundary of a geography.*

An `accessor` request named `boundary` returns the boundary geography as a `wkt=` line: the empty collection for a point, the endpoint multipoint for an open line, the ring linework for a polygon.

**Test Cases:** `rcb_tests/public_test_cases/feature29_boundary.json`

```json
{
    "description": "Compute the boundary of a geography. The boundary of a point is the empty collection; the boundary of an open line is the multipoint of its endpoints; the boundary of a polygon is the linear ring(s) of its rings.",
    "cases": [
        {
            "input": {
                "op": "accessor",
                "name": "boundary",
                "a": {
                    "type": "linestring",
                    "coords": [
                        [
                            0,
                            0
                        ],
                        [
                            2,
                            0
                        ],
                        [
                            2,
                            2
                        ]
                    ]
                }
            },
            "expected_output": "wkt=MULTIPOINT ((0 0), (2 2))\n"
        },
        {
            "input": {
                "op": "accessor",
                "name": "boundary",
                "a": {
                    "type": "polygon",
                    "shell": [
                        [
                            0,
                            0
                        ],
                        [
                            0,
                            2
                        ],
                        [
                            2,
                            2
                        ],
                        [
                            0.5,
                            1.5
                        ]
                    ]
                }
            },
            "expected_output": "wkt=LINESTRING (0.5 1.5, 2 2, 0 2, 0 0, 0.5 1.5)\n"
        }
    ]
}
```


*6.3 Convex Hull — I want to derive the convex hull of a geography.*

An `accessor` request named `convex_hull` returns a polygon geography as `type=` and `wkt=` lines.

**Test Cases:** `rcb_tests/public_test_cases/feature30_convex_hull.json`

```json
{
    "description": "Compute the convex hull of a geography, returning it as a polygon geography given by its type name and text rendering.",
    "cases": [
        {
            "input": {
                "op": "accessor",
                "name": "convex_hull",
                "a": {
                    "type": "linestring",
                    "coords": [
                        [
                            0,
                            0
                        ],
                        [
                            2,
                            0
                        ],
                        [
                            2,
                            2
                        ]
                    ]
                }
            },
            "expected_output": "type=POLYGON\nwkt=POLYGON ((0 0, 2 0, 2 2, 0 0))\n"
        },
        {
            "input": {
                "op": "accessor",
                "name": "convex_hull",
                "a": {
                    "type": "polygon",
                    "shell": [
                        [
                            0,
                            0
                        ],
                        [
                            0,
                            2
                        ],
                        [
                            2,
                            2
                        ],
                        [
                            0.5,
                            1.5
                        ]
                    ]
                }
            },
            "expected_output": "type=POLYGON\nwkt=POLYGON ((0 0, 2 2, 0 2, 0 0))\n"
        }
    ]
}
```


*6.4 Coordinate Access — I want to read the longitude and latitude of a point.*

An `accessor` request named `get_x` or `get_y` returns the coordinate as `get_x=<value>` / `get_y=<value>`. Requesting a coordinate of a non-point yields `error=unsupported_geometry`.

**Test Cases:** `rcb_tests/public_test_cases/feature31_get_xy.json`

```json
{
    "description": "Read the longitude (x) and latitude (y) of a point geography. Requesting a coordinate of a non-point geography is rejected with a normalized unsupported-geometry error.",
    "cases": [
        {
            "input": {
                "op": "accessor",
                "name": "get_x",
                "a": {
                    "type": "point",
                    "coords": [
                        1.5,
                        2.6
                    ]
                }
            },
            "expected_output": "get_x=1.500000\n"
        },
        {
            "input": {
                "op": "accessor",
                "name": "get_x",
                "a": {
                    "type": "linestring",
                    "coords": [
                        [
                            0,
                            1
                        ],
                        [
                            1,
                            2
                        ]
                    ]
                }
            },
            "expected_output": "error=unsupported_geometry\ndetail=Only Point geometries supported\n"
        }
    ]
}
```


---

### Feature 7: Boolean Set Operations

**As a developer**, I want a reliable contract for boolean set operations, so I can build correct geospatial behavior without re-deriving spherical geometry myself.

Binary set operations combine two geographies into a result geography, returned as a single `result=<wkt>` line. Operands and results are exchanged in canonical text form.


*7.1 Union — I want to combine the points of two geographies.*

A `boolean_op` request named `union` returns every point belonging to either operand. Unioning with an empty geography returns the other operand; collinear lines sharing an endpoint merge.

**Test Cases:** `rcb_tests/public_test_cases/feature32_union.json`

```json
{
    "description": "Compute the union of two geographies: the geography covering every point that belongs to either operand. Unioning with an empty geography returns the other operand; two collinear lines sharing an endpoint merge into one line.",
    "cases": [
        {
            "input": {
                "op": "boolean_op",
                "name": "union",
                "a": {
                    "wkt": "POINT (30 10)"
                },
                "b": {
                    "wkt": "POINT EMPTY"
                }
            },
            "expected_output": "result=POINT (30 10)\n"
        },
        {
            "input": {
                "op": "boolean_op",
                "name": "union",
                "a": {
                    "wkt": "LINESTRING (-45 0, 0 0)"
                },
                "b": {
                    "wkt": "LINESTRING (0 0, 0 10)"
                }
            },
            "expected_output": "result=LINESTRING (-45 0, 0 0, 0 10)\n"
        }
    ]
}
```


*7.2 Intersection — I want to keep only the points common to two geographies.*

A `boolean_op` request named `intersection` returns the shared points. The result may have lower dimension than the operands; disjoint operands yield the empty collection.

**Test Cases:** `rcb_tests/public_test_cases/feature33_intersection.json`

```json
{
    "description": "Compute the intersection of two geographies: the geography covering every point belonging to both operands. The intersection may be of lower dimension than the operands (e.g. a polygon meeting a line yields the line segment inside it; two crossing lines yield a point). Disjoint operands yield the empty collection.",
    "cases": [
        {
            "input": {
                "op": "boolean_op",
                "name": "intersection",
                "a": {
                    "wkt": "POINT (30 10)"
                },
                "b": {
                    "wkt": "POINT (30 10)"
                }
            },
            "expected_output": "result=POINT (30 10)\n"
        },
        {
            "input": {
                "op": "boolean_op",
                "name": "intersection",
                "a": {
                    "wkt": "POLYGON ((0 0, 10 0, 10 10, 0 10, 0 0))"
                },
                "b": {
                    "wkt": "LINESTRING (0 5, 10 5)"
                }
            },
            "expected_output": "result=LINESTRING (0 5, 10 5)\n"
        }
    ]
}
```


*7.3 Difference — I want to subtract one geography from another.*

A `boolean_op` request named `difference` returns the points of the first operand not in the second. Subtracting an empty geography returns the first operand.

**Test Cases:** `rcb_tests/public_test_cases/feature34_difference.json`

```json
{
    "description": "Compute the difference of two geographies: the geography covering every point of the first operand that does not belong to the second. Subtracting an empty geography returns the first operand; subtracting a geography from an equal one yields the empty collection.",
    "cases": [
        {
            "input": {
                "op": "boolean_op",
                "name": "difference",
                "a": {
                    "wkt": "POINT (30 10)"
                },
                "b": {
                    "wkt": "POINT EMPTY"
                }
            },
            "expected_output": "result=POINT (30 10)\n"
        },
        {
            "input": {
                "op": "boolean_op",
                "name": "difference",
                "a": {
                    "wkt": "LINESTRING (0 0, 45 0)"
                },
                "b": {
                    "wkt": "LINESTRING (0 0, 45 0)"
                }
            },
            "expected_output": "result=GEOMETRYCOLLECTION EMPTY\n"
        }
    ]
}
```


*7.4 Symmetric Difference — I want to keep points in exactly one of two geographies.*

A `boolean_op` request named `symmetric_difference` returns the points belonging to exactly one operand. Equal operands yield the empty collection.

**Test Cases:** `rcb_tests/public_test_cases/feature35_symmetric_difference.json`

```json
{
    "description": "Compute the symmetric difference of two geographies: the geography covering every point belonging to exactly one of the operands. Equal operands yield the empty collection; two distinct points yield the multipoint of both.",
    "cases": [
        {
            "input": {
                "op": "boolean_op",
                "name": "symmetric_difference",
                "a": {
                    "wkt": "POINT (30 10)"
                },
                "b": {
                    "wkt": "POINT EMPTY"
                }
            },
            "expected_output": "result=POINT (30 10)\n"
        },
        {
            "input": {
                "op": "boolean_op",
                "name": "symmetric_difference",
                "a": {
                    "wkt": "POINT (30 10)"
                },
                "b": {
                    "wkt": "POINT (30 20)"
                }
            },
            "expected_output": "result=MULTIPOINT ((30 20), (30 10))\n"
        }
    ]
}
```


---

### Feature 8: Serialization

**As a developer**, I want a reliable contract for serialization, so I can build correct geospatial behavior without re-deriving spherical geometry myself.

Geographies convert to and from two interchange forms: a human-readable text form and a compact binary form. Parsing supports orientation handling and an optional planar tessellation mode.


*8.1 Render To Text — I want to render geographies to canonical text.*

A `to_wkt` request renders a `geometry` (here a `points` batch given by parallel `x`/`y` arrays) to text, one rendering per element. An optional `precision` caps the coordinate decimal digits.

**Test Cases:** `rcb_tests/public_test_cases/feature36_to_wkt.json`

```json
{
    "description": "Render geographies to their canonical text form. An optional precision controls the number of significant decimal digits used for coordinates.",
    "cases": [
        {
            "input": {
                "op": "to_wkt",
                "geometry": {
                    "type": "points",
                    "x": [
                        1.1,
                        2,
                        3
                    ],
                    "y": [
                        1.1,
                        2,
                        3
                    ]
                }
            },
            "expected_output": "POINT (1.1 1.1)\nPOINT (2 2)\nPOINT (3 3)\n"
        },
        {
            "input": {
                "op": "to_wkt",
                "geometry": {
                    "type": "points",
                    "x": [
                        0.12345
                    ],
                    "y": [
                        0.56789
                    ]
                },
                "precision": 2
            },
            "expected_output": "POINT (0.12 0.57)\n"
        }
    ]
}
```


*8.2 Parse From Text — I want to parse geographies from text with orientation and planar options.*

A `from_wkt` request parses one text or a list of texts. An inconsistently wound interior ring is re-oriented by default; declaring `oriented` true rejects it with a normalized error. A `planar` flag (with optional `tessellate_tolerance`) tessellates straight planar edges onto the sphere, observable via a `probe` distance from an off-geodesic midpoint.

**Test Cases:** `rcb_tests/public_test_cases/feature37_from_wkt.json`

```json
{
    "description": "Parse geographies from their text form. Several texts may be parsed at once. By default an interior ring with inconsistent winding is re-oriented to a valid hole; declaring the orientation as already meaningful rejects such input with a normalized error. By default the edges of a parsed line follow geodesics; a planar option instead tessellates straight planar edges onto the sphere within an optional tolerance, observable as a much smaller distance from a midpoint that lies off the geodesic.",
    "cases": [
        {
            "input": {
                "op": "from_wkt",
                "wkt": [
                    "POINT (1 1)",
                    "POINT(2 2)",
                    "POINT(3 3)"
                ]
            },
            "expected_output": "POINT (1 1)\nPOINT (2 2)\nPOINT (3 3)\n"
        },
        {
            "input": {
                "op": "from_wkt",
                "wkt": "POLYGON ((20 35, 10 30, 10 10, 30 5, 45 20, 20 35),(30 20, 20 25, 20 15, 30 20))"
            },
            "expected_output": "POLYGON ((20 35, 10 30, 10 10, 30 5, 45 20, 20 35), (20 15, 20 25, 30 20, 20 15))\n"
        }
    ]
}
```


*8.3 Binary Round Trip — I want to serialize to binary and parse back without loss of type or shape.*

A `wkb_roundtrip` request serializes a `geometry` to binary and parses it back, returning the restored geography as `wkt=`.

**Test Cases:** `rcb_tests/public_test_cases/feature38_wkb_roundtrip.json`

```json
{
    "description": "Serialize a geography to binary and parse it back, preserving its type and shape across the round trip for points, multipoints, lines, multilines, polygons (with and without holes), multipolygons and collections.",
    "cases": [
        {
            "input": {
                "op": "wkb_roundtrip",
                "geometry": {
                    "type": "point",
                    "coords": [
                        45,
                        50
                    ]
                }
            },
            "expected_output": "wkt=POINT (45 50)\n"
        },
        {
            "input": {
                "op": "wkb_roundtrip",
                "geometry": {
                    "type": "linestring",
                    "coords": [
                        [
                            5,
                            50
                        ],
                        [
                            6,
                            51
                        ]
                    ]
                }
            },
            "expected_output": "wkt=LINESTRING (5 50, 6 51)\n"
        }
    ]
}
```


*8.4 Parse From Binary — I want to parse geographies from binary with empty and orientation handling.*

A `from_wkb` request parses a hex-encoded buffer. Empty point/multipoint encodings normalize to the empty point; a non-minimal ring is re-oriented by default (observable through an optional `within` probe) unless `oriented` is declared true.

**Test Cases:** `rcb_tests/public_test_cases/feature39_from_wkb.json`

```json
{
    "description": "Parse geographies from binary form. Empty point and empty multipoint encodings normalize to the empty point; a collection of an empty point is preserved. By default a non-minimal areal ring is re-oriented to enclose the smaller region, observable through a point that then lies within it; declaring the orientation as meaningful preserves the supplied winding.",
    "cases": [
        {
            "input": {
                "op": "from_wkb",
                "wkb_hex": "0101000000000000000000f03f000000000000f03f"
            },
            "expected_output": "wkt=POINT (1 1)\n"
        },
        {
            "input": {
                "op": "from_wkb",
                "wkb_hex": "0107000000010000000101000000000000000000f87f000000000000f87f"
            },
            "expected_output": "wkt=GEOMETRYCOLLECTION (POINT EMPTY)\n"
        }
    ]
}
```


*8.5 Serialization Input Validation — I want to reject malformed or wrongly-typed serialization input.*

Text parsing rejects numeric/[structure type for hole data] entries with `error=invalid_input_type` and malformed text with `error=parse_error`; binary parsing rejects non-binary input and truncated buffers similarly; reading the dimension of a non-geography value yields `error=not_geography`.

**Test Cases:** `rcb_tests/public_test_cases/feature40_io_validation.json`

```json
{
    "description": "Serialization input is validated. Text parsing requires text values: numeric or [structure type for hole data] entries are rejected with a normalized input-type error, and malformed text is rejected with a normalized parse error. Binary parsing likewise rejects non-binary input and truncated buffers. Reading the dimension of a non-geography value is rejected with a normalized not-a-geography error.",
    "cases": [
        {
            "input": {
                "op": "from_wkt",
                "wkt": [
                    1
                ]
            },
            "expected_output": "error=invalid_input_type\n"
        },
        {
            "input": {
                "op": "properties",
                "name": "get_dimensions",
                "values": [
                    {
                        "number": 1
                    },
                    {
                        "number": 2.33
                    },
                    {
                        "type": "point",
                        "coords": [
                            30,
                            6
                        ]
                    }
                ]
            },
            "expected_output": "error=not_geography\n"
        }
    ]
}
```


---

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing spherical construction, validation, properties, predicates, measures, set operations, accessors and serialization as described above, decoupled from all I/O and JSON concerns.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON request from stdin, dispatches on `op`, invokes the core, and prints the result (or a normalized `error=<category>` contract) to stdout exactly as the per-feature cases specify.

3. **Automated test harness.** The cases embedded above live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` containing only the raw stdout of the program under test, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- identify consecutive duplicates
- invert winding for holes
