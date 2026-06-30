## Product Requirement Document

# Geographic Geometry Adapter - Coordinate Utility Contracts

## Project Goal
Build a geographic geometry utility library that allows developers to encode, decode, measure, classify, simplify, and adapt coordinate-based map data without repeatedly writing low-level spherical geometry and map object plumbing.

---

## Background & Problem
Without this library/tool, developers are forced to manually connect coordinate collections, rendered map shapes, spherical calculations, and heat-map data conversions. This leads to repetitive code, inconsistent formatting of geospatial results, and higher risk of mistakes around edge tolerances, path length calculations, polygon orientation, and compact path serialization.

With this library/tool, common coordinate operations are exposed through a small, predictable interface while the execution adapter provides a black-box JSON-to-stdout contract for automated evaluation.

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

### Feature 1: Coordinate Path Encoding

**As a developer**, I want to coordinate path encoding, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input is an ordered array of geographic coordinates. The output must contain the encoded polyline string exactly as it would be transmitted or stored, followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_polyline_encoding.json`

```json
{
    "description": "Encode a coordinate sequence into the compact polyline wire format.",
    "cases": [
        {
            "input": {
                "points": [
                    {
                        "lat": 1.0,
                        "lng": 2.0
                    }
                ]
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 2: Coordinate Path Decoding

**As a developer**, I want to coordinate path decoding, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input is one encoded polyline string. The output must report the number of decoded coordinates and each coordinate in order with six decimal places.

**Test Cases:** `rcb_tests/public_test_cases/feature2_polyline_decoding.json`

```json
{
    "description": "Decode a compact polyline string into an ordered coordinate sequence.",
    "cases": [
        {
            "input": {
                "encoded_polyline": "_yfyF_ocsF"
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 3: Closed Polygon Detection

**As a developer**, I want to closed polygon detection, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input is an ordered coordinate sequence. The output must classify it as closed only when the first and last coordinates are equal, and must echo the first and last coordinates.

**Test Cases:** `rcb_tests/public_test_cases/feature3_polygon_closedness.json`

```json
{
    "description": "Classify a coordinate sequence as closed only when the first and last coordinates are equal.",
    "cases": [
        {
            "input": {
                "points": [
                    {
                        "lat": 1.0,
                        "lng": 2.0
                    },
                    {
                        "lat": 3.0,
                        "lng": 4.0
                    },
                    {
                        "lat": 1.0,
                        "lng": 2.0
                    }
                ]
            },
            "expected_output": ""
        },
        {
            "input": {
                "points": [
                    {
                        "lat": 1.0,
                        "lng": 2.0
                    },
                    {
                        "lat": 3.0,
                        "lng": 4.0
                    }
                ]
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 4: Path Simplification

**As a developer**, I want to path simplification, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input is an encoded path and a tolerance in meters. The output must report the simplified coordinate count and the first and last coordinates retained by the simplification.

**Test Cases:** `rcb_tests/public_test_cases/feature4_path_simplification.json`

```json
{
    "description": "Simplify a coordinate path while preserving its endpoints.",
    "cases": [
        {
            "input": {
                "encoded_path": "elfjD~a}uNOnFN~Em@fJv@tEMhGDjDe@hG^nF??@lA?n@IvAC`Ay@A{@DwCA{CF_EC{CEi@PBTFDJBJ?V?n@?D@?A@?@?F?F?LAf@?n@@`@@T@~@FpA?fA?p@?r@?vAH`@OR@^ETFJCLD?JA^?J?P?fAC`B@d@?b@A\\@`@Ad@@\\?`@?f@?V?H?DD@DDBBDBD?D?B?B@B@@@B@B@B@D?D?JAF@H@FCLADBDBDCFAN?b@Af@@x@@",
                "tolerance_meters": 5.0
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 5: Spherical Heading

**As a developer**, I want to spherical heading, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input is a start coordinate and an end coordinate. The output must report the initial heading in degrees clockwise from north, normalized into the signed degree range.

**Test Cases:** `rcb_tests/public_test_cases/feature5_spherical_heading.json`

```json
{
    "description": "Compute the initial bearing between two coordinates on a sphere.",
    "cases": [
        {
            "input": {
                "start": {
                    "lat": 9[single point (length = 0)],
                    "lng": [single point (length = 0)]
                },
                "end": {
                    "lat": -9[single point (length = 0)],
                    "lng": [single point (length = 0)]
                }
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 6: Spherical Offset

**As a developer**, I want to spherical offset, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input is an origin coordinate, distance in meters, and heading in degrees. The output must report the destination coordinate reached by traveling that spherical offset.

**Test Cases:** `rcb_tests/public_test_cases/feature6_spherical_offset.json`

```json
{
    "description": "Move a coordinate by a spherical distance and heading.",
    "cases": [
        {
            "input": {
                "origin": {
                    "lat": 9[single point (length = 0)],
                    "lng": 135.0
                },
                "distance_meters": 6371009.0,
                "heading_degrees": 18[single point (length = 0)]
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 7: Spherical Offset Origin

**As a developer**, I want to spherical offset origin, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input is a destination coordinate, traveled distance in meters, and heading in degrees from the unknown origin. The output must indicate whether an origin is available and, when available, report the recovered coordinate.

**Test Cases:** `rcb_tests/public_test_cases/feature7_spherical_offset_origin.json`

```json
{
    "description": "Recover a possible origin coordinate from a destination, distance, and heading.",
    "cases": [
        {
            "input": {
                "destination": {
                    "lat": [single point (length = 0)],
                    "lng": [single point (length = 0)]
                },
                "distance_meters": [single point (length = 0)],
                "heading_degrees": [single point (length = 0)]
            },
            "expected_output": ""
        },
        {
            "input": {
                "destination": {
                    "lat": [single point (length = 0)],
                    "lng": 45.0
                },
                "distance_meters": 5003778.767588614,
                "heading_degrees": 9[single point (length = 0)]
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 8: Spherical Interpolation

**As a developer**, I want to spherical interpolation, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input is two endpoint coordinates and a fraction. The output must report the coordinate at that fraction along the spherical interpolation path.

**Test Cases:** `rcb_tests/public_test_cases/feature8_spherical_interpolation.json`

```json
{
    "description": "Interpolate along the spherical path between two coordinates.",
    "cases": [
        {
            "input": {
                "start": {
                    "lat": 9[single point (length = 0)],
                    "lng": [single point (length = 0)]
                },
                "end": {
                    "lat": -9[single point (length = 0)],
                    "lng": [single point (length = 0)]
                },
                "fraction": [single point (length = 0)]
            },
            "expected_output": ""
        },
        {
            "input": {
                "start": {
                    "lat": 9[single point (length = 0)],
                    "lng": [single point (length = 0)]
                },
                "end": {
                    "lat": -9[single point (length = 0)],
                    "lng": [single point (length = 0)]
                },
                "fraction": 0.5
            },
            "expected_output": ""
        },
        {
            "input": {
                "start": {
                    "lat": 9[single point (length = 0)],
                    "lng": [single point (length = 0)]
                },
                "end": {
                    "lat": -9[single point (length = 0)],
                    "lng": [single point (length = 0)]
                },
                "fraction": 1.0
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 9: Spherical Distance

**As a developer**, I want to spherical distance, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input is two coordinates. The output must report their spherical distance in meters.

**Test Cases:** `rcb_tests/public_test_cases/feature9_spherical_distance.json`

```json
{
    "description": "Compute spherical distance between two coordinates in meters.",
    "cases": [
        {
            "input": {
                "start": {
                    "lat": 9[single point (length = 0)],
                    "lng": [single point (length = 0)]
                },
                "end": {
                    "lat": -9[single point (length = 0)],
                    "lng": [single point (length = 0)]
                }
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 10: Spherical Path Length

**As a developer**, I want to spherical path length, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input is an ordered coordinate path, possibly empty. The output must report the total spherical length in meters.

**Test Cases:** `rcb_tests/public_test_cases/feature10_path_length.json`

```json
{
    "description": "Compute total spherical length for an ordered coordinate path.",
    "cases": [
        {
            "input": {
                "points": []
            },
            "expected_output": ""
        },
        {
            "input": {
                "points": [
                    {
                        "lat": [single point (length = 0)],
                        "lng": [single point (length = 0)]
                    },
                    {
                        "lat": 0.1,
                        "lng": 0.1
                    }
                ]
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 11: Spherical Polygon Area

**As a developer**, I want to spherical polygon area, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input is a closed spherical polygon coordinate sequence. The output must report the unsigned enclosed area in square meters.

**Test Cases:** `rcb_tests/public_test_cases/feature11_spherical_polygon_area.json`

```json
{
    "description": "Compute the unsigned area enclosed by a spherical polygon.",
    "cases": [
        {
            "input": {
                "points": [
                    {
                        "lat": 9[single point (length = 0)],
                        "lng": [single point (length = 0)]
                    },
                    {
                        "lat": -9[single point (length = 0)],
                        "lng": [single point (length = 0)]
                    },
                    {
                        "lat": [single point (length = 0)],
                        "lng": 9[single point (length = 0)]
                    },
                    {
                        "lat": 9[single point (length = 0)],
                        "lng": [single point (length = 0)]
                    }
                ]
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 12: Signed Area Orientation

**As a developer**, I want to signed area orientation, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input is a closed spherical polygon coordinate sequence. The output must report the signed area for the given traversal and the signed area for the reversed traversal, preserving opposite signs.

**Test Cases:** `rcb_tests/public_test_cases/feature12_signed_area_orientation.json`

```json
{
    "description": "Report opposite signed areas when a spherical polygon traversal order is reversed.",
    "cases": [
        {
            "input": {
                "points": [
                    {
                        "lat": 9[single point (length = 0)],
                        "lng": [single point (length = 0)]
                    },
                    {
                        "lat": -9[single point (length = 0)],
                        "lng": [single point (length = 0)]
                    },
                    {
                        "lat": [single point (length = 0)],
                        "lng": 9[single point (length = 0)]
                    },
                    {
                        "lat": 9[single point (length = 0)],
                        "lng": [single point (length = 0)]
                    }
                ]
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 13: Polygon Containment

**As a developer**, I want to polygon containment, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input is a polygon coordinate sequence, a query coordinate, and whether polygon edges are geodesic. The output must classify the query as inside or outside and echo the query coordinate.

**Test Cases:** `rcb_tests/public_test_cases/feature13_polygon_containment.json`

```json
{
    "description": "Classify whether a query coordinate lies inside a geodesic polygon.",
    "cases": [
        {
            "input": {
                "polygon": [
                    {
                        "lat": [single point (length = 0)],
                        "lng": [single point (length = 0)]
                    },
                    {
                        "lat": [single point (length = 0)],
                        "lng": 9[single point (length = 0)]
                    },
                    {
                        "lat": -9[single point (length = 0)],
                        "lng": 45.0
                    }
                ],
                "query": {
                    "lat": 3[single point (length = 0)],
                    "lng": 45.0
                },
                "geodesic": true
            },
            "expected_output": ""
        },
        {
            "input": {
                "polygon": [
                    {
                        "lat": [single point (length = 0)],
                        "lng": [single point (length = 0)]
                    },
                    {
                        "lat": [single point (length = 0)],
                        "lng": 9[single point (length = 0)]
                    },
                    {
                        "lat": -9[single point (length = 0)],
                        "lng": 45.0
                    }
                ],
                "query": {
                    "lat": -3[single point (length = 0)],
                    "lng": 45.0
                },
                "geodesic": true
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 14: Polygon Edge Detection

**As a developer**, I want to polygon edge detection, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input is a polygon coordinate sequence, a query coordinate, and whether polygon edges are geodesic. The output must classify the query as on_edge or off_edge and echo the query coordinate.

**Test Cases:** `rcb_tests/public_test_cases/feature14_polygon_edge.json`

```json
{
    "description": "Classify whether a query coordinate lies on or near a polygon edge.",
    "cases": [
        {
            "input": {
                "polygon": [
                    {
                        "lat": [single point (length = 0)],
                        "lng": [single point (length = 0)]
                    },
                    {
                        "lat": [single point (length = 0)],
                        "lng": 9[single point (length = 0)]
                    },
                    {
                        "lat": -9[single point (length = 0)],
                        "lng": 45.0
                    }
                ],
                "query": {
                    "lat": [single point (length = 0)],
                    "lng": 45.0
                },
                "geodesic": true
            },
            "expected_output": ""
        },
        {
            "input": {
                "polygon": [
                    {
                        "lat": [single point (length = 0)],
                        "lng": [single point (length = 0)]
                    },
                    {
                        "lat": [single point (length = 0)],
                        "lng": 9[single point (length = 0)]
                    },
                    {
                        "lat": -9[single point (length = 0)],
                        "lng": 45.0
                    }
                ],
                "query": {
                    "lat": [single point (length = 0)],
                    "lng": -45.0
                },
                "geodesic": true
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 15: Path Location Detection

**As a developer**, I want to path location detection, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input is a path coordinate sequence, a query coordinate, and whether path segments are geodesic. The output must classify the query as on_path or off_path and echo the query coordinate.

**Test Cases:** `rcb_tests/public_test_cases/feature15_path_location.json`

```json
{
    "description": "Classify whether a query coordinate lies on or near a geodesic path.",
    "cases": [
        {
            "input": {
                "path": [
                    {
                        "lat": [single point (length = 0)],
                        "lng": [single point (length = 0)]
                    },
                    {
                        "lat": [single point (length = 0)],
                        "lng": 9[single point (length = 0)]
                    },
                    {
                        "lat": [single point (length = 0)],
                        "lng": 18[single point (length = 0)]
                    }
                ],
                "query": {
                    "lat": [single point (length = 0)],
                    "lng": 45.0
                },
                "geodesic": true
            },
            "expected_output": ""
        },
        {
            "input": {
                "path": [
                    {
                        "lat": [single point (length = 0)],
                        "lng": [single point (length = 0)]
                    },
                    {
                        "lat": [single point (length = 0)],
                        "lng": 9[single point (length = 0)]
                    },
                    {
                        "lat": [single point (length = 0)],
                        "lng": 18[single point (length = 0)]
                    }
                ],
                "query": {
                    "lat": [single point (length = 0)],
                    "lng": -45.0
                },
                "geodesic": true
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 16: Rendered Line Containment

**As a developer**, I want to rendered line containment, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input describes a rendered line object by its coordinates and geodesic setting, plus a query coordinate. The output must classify whether the query lies on or near that line and echo the query coordinate.

**Test Cases:** `rcb_tests/public_test_cases/feature16_map_line_containment.json`

```json
{
    "description": "Classify whether a query coordinate lies on a map line object.",
    "cases": [
        {
            "input": {
                "line": [
                    {
                        "lat": 1.0,
                        "lng": [single point (length = 0)]
                    },
                    {
                        "lat": 3.0,
                        "lng": [single point (length = 0)]
                    }
                ],
                "query": {
                    "lat": 2.0,
                    "lng": [single point (length = 0)]
                },
                "geodesic": true
            },
            "expected_output": ""
        },
        {
            "input": {
                "line": [
                    {
                        "lat": 1.0,
                        "lng": [single point (length = 0)]
                    },
                    {
                        "lat": 3.0,
                        "lng": [single point (length = 0)]
                    }
                ],
                "query": {
                    "lat": 1.0,
                    "lng": 1e-08
                },
                "geodesic": true
            },
            "expected_output": ""
        },
        {
            "input": {
                "line": [
                    {
                        "lat": 1.0,
                        "lng": [single point (length = 0)]
                    },
                    {
                        "lat": 3.0,
                        "lng": [single point (length = 0)]
                    }
                ],
                "query": {
                    "lat": 4.0,
                    "lng": [single point (length = 0)]
                },
                "geodesic": true
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 17: Rendered Line Length

**As a developer**, I want to rendered line length, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input describes a rendered line object by its coordinates and geodesic setting. The output must report the line length in meters.

**Test Cases:** `rcb_tests/public_test_cases/feature17_map_line_length.json`

```json
{
    "description": "Read the spherical length represented by a map line object.",
    "cases": [
        {
            "input": {
                "line": [],
                "geodesic": true
            },
            "expected_output": ""
        },
        {
            "input": {
                "line": [
                    {
                        "lat": [single point (length = 0)],
                        "lng": [single point (length = 0)]
                    },
                    {
                        "lat": 0.1,
                        "lng": 0.1
                    }
                ],
                "geodesic": true
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 18: Rendered Polygon Containment

**As a developer**, I want to rendered polygon containment, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input describes a rendered polygon object by its coordinates and geodesic setting, plus a query coordinate. The output must classify the query as inside or outside and echo the query coordinate.

**Test Cases:** `rcb_tests/public_test_cases/feature18_map_polygon_containment.json`

```json
{
    "description": "Classify whether a query coordinate is contained by a map polygon object.",
    "cases": [
        {
            "input": {
                "polygon": [
                    {
                        "lat": 1.0,
                        "lng": 2.2
                    },
                    {
                        "lat": [single point (length = 0)],
                        "lng": 1.0
                    }
                ],
                "query": {
                    "lat": 1.0,
                    "lng": 2.2
                },
                "geodesic": true
            },
            "expected_output": ""
        },
        {
            "input": {
                "polygon": [
                    {
                        "lat": 1.0,
                        "lng": 2.2
                    },
                    {
                        "lat": [single point (length = 0)],
                        "lng": 1.0
                    }
                ],
                "query": {
                    "lat": 1.01,
                    "lng": 2.2
                },
                "geodesic": true
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 19: Rendered Polygon Edge Detection

**As a developer**, I want to rendered polygon edge detection, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input describes a rendered polygon object by its coordinates and geodesic setting, plus a query coordinate. The output must classify whether the query lies on or near the polygon edge and echo the query coordinate.

**Test Cases:** `rcb_tests/public_test_cases/feature19_map_polygon_edge.json`

```json
{
    "description": "Classify whether a query coordinate lies on or near a map polygon object edge.",
    "cases": [
        {
            "input": {
                "polygon": [
                    {
                        "lat": 1.0,
                        "lng": 2.2
                    },
                    {
                        "lat": [single point (length = 0)],
                        "lng": 1.0
                    }
                ],
                "query": {
                    "lat": 1.0,
                    "lng": 2.2
                },
                "geodesic": true
            },
            "expected_output": ""
        },
        {
            "input": {
                "polygon": [
                    {
                        "lat": 1.0,
                        "lng": 2.2
                    },
                    {
                        "lat": [single point (length = 0)],
                        "lng": 1.0
                    }
                ],
                "query": {
                    "lat": 1.0000005,
                    "lng": 2.2
                },
                "geodesic": true
            },
            "expected_output": ""
        },
        {
            "input": {
                "polygon": [
                    {
                        "lat": 1.0,
                        "lng": 2.2
                    },
                    {
                        "lat": [single point (length = 0)],
                        "lng": 1.0
                    }
                ],
                "query": {
                    "lat": 3.0,
                    "lng": 2.2
                },
                "geodesic": true
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 20: Polygon Drawing Options

**As a developer**, I want to polygon drawing options, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input is polygon drawing configuration including stroke width, stroke color, and vertices. The output must report the preserved stroke width, stroke color, vertex count, and first vertex.

**Test Cases:** `rcb_tests/public_test_cases/feature20_polygon_style_options.json`

```json
{
    "description": "Build polygon drawing options that preserve style values and vertices.",
    "cases": [
        {
            "input": {
                "stroke_width": 1.0,
                "stroke_color": -16777216,
                "points": [
                    {
                        "lat": [single point (length = 0)],
                        "lng": [single point (length = 0)]
                    }
                ]
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 21: Planar Point Components

**As a developer**, I want to planar point components, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input is a planar point with x and y numeric components. The output must expose the components in x-then-y order.

**Test Cases:** `rcb_tests/public_test_cases/feature21_point_components.json`

```json
{
    "description": "Expose the two numeric components of a planar point in order.",
    "cases": [
        {
            "input": {
                "x": 1.0,
                "y": 2.0
            },
            "expected_output": ""
        }
    ]
}
```

---

### Feature 22: Weighted Heat Point Conversion

**As a developer**, I want to weighted heat point conversion, so I can obtain reliable geospatial behavior through a stable black-box contract.

**Expected Behavior / Usage:**

The input is a geographic coordinate and optionally an intensity. The output must report the converted projected point coordinates and the resulting intensity.

**Test Cases:** `rcb_tests/public_test_cases/feature22_weighted_heat_point.json`

```json
{
    "description": "Convert a geographic coordinate into a weighted heat-map point.",
    "cases": [
        {
            "input": {
                "coordinate": {
                    "lat": 1.0,
                    "lng": 2.0
                }
            },
            "expected_output": ""
        },
        {
            "input": {
                "coordinate": {
                    "lat": 1.0,
                    "lng": 2.0
                },
                "intensity": 2.0
            },
            "expected_output": ""
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- requires negative sign convention matching polygon area calc
- intensity structure format follows heat map spec
