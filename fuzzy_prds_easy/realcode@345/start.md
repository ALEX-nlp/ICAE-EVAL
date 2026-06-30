## Product Requirement Document

# Zonal Raster Extraction Tool - Polygon-Based Raster Summaries

## Project Goal

Build a zonal raster extraction tool that allows developers to summarize numeric and categorical raster data over polygon features without manually clipping rasters, computing fractional cell overlaps, and assembling output tables.

---

## Background & Problem

Without this library/tool, developers are forced to combine geospatial file readers, polygon-cell intersection code, missing-data handling, summary-statistic calculators, and output writers by hand. This leads to repetitive code, inconsistent handling of edge cells and no-data values, and fragile table schemas for downstream analysis.

With this library/tool, a caller supplies polygon features, raster matrices, requested measurements, and output options, and receives deterministic tabular or spatial output that reflects exact fractional overlap between polygons and raster cells.

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

### Feature 1: Polygon Raster Summary Statistics

**As a developer**, I want to calculate named summary statistics for each input polygon, so I can obtain tabular measurements from raster cells covered by a polygon.

**Expected Behavior / Usage:**

The adapter input contains one or more polygon features, one or more rasters with numeric cell matrices, a list of requested statistics, and an identifier field. For each feature, the output is CSV. The first column is the identifier, followed by statistic columns named from the raster name and operation. Covered cells contribute according to fractional overlap. Quantile requests include the requested probability in the output column name.

**Test Cases:** `rcb_tests/public_test_cases/feature1_zonal_summary_statistics.json`

```json
{
    "description": "Compute multiple summary statistics for a polygon over a named raster and preserve the identifier column.",
    "cases": [
        {
            "input": {
                "features": [
                    {
                        "id": 1,
                        "geometry": "POLYGON (([a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent], 2.5 [a fractional area value relative to the raster extent], 2.5 2, [a fractional area value relative to the raster extent] 2, [a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent]))"
                    }
                ],
                "rasters": [
                    {
                        "data": [
                            [
                                1,
                                2,
                                3,
                                4
                            ],
                            [
                                1,
                                2,
                                2,
                                5
                            ],
                            [
                                3,
                                3,
                                3,
                                2
                            ]
                        ],
                        "dtype": "int16",
                        "name": "metric"
                    }
                ],
                "statistics": [
                    {
                        "operation": "mean",
                        "raster": "metric"
                    },
                    {
                        "operation": "variety",
                        "raster": "metric"
                    },
                    {
                        "operation": "quantile",
                        "raster": "metric",
                        "q": [a fractional area value relative to the raster extent]
                    }
                ],
                "options": {
                    "identifier": "id"
                }
            },
            "expected_output": "id,metric_mean,metric_variety,metric_quantile_25\n\"1\",2.16666674613953,\"3\",1.6\n"
        }
    ]
}
```

---

### Feature 2: Implicit Single-Raster Statistic Naming

**As a developer**, I want to request statistics without naming a raster when only one single-band raster is present, so I can keep simple one-raster requests concise.

**Expected Behavior / Usage:**

When the input has exactly one unnamed, single-band raster, statistics may omit a raster reference. The output CSV uses the operation names as column headers rather than inventing a raster prefix.

**Test Cases:** `rcb_tests/public_test_cases/feature2_implicit_single_raster_statistics.json`

```json
{
    "description": "Compute statistics with implicit operation names when exactly one single-band raster is supplied.",
    "cases": [
        {
            "input": {
                "features": [
                    {
                        "id": 1,
                        "geometry": "POLYGON (([a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent], 2.5 [a fractional area value relative to the raster extent], 2.5 2, [a fractional area value relative to the raster extent] 2, [a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent]))"
                    }
                ],
                "rasters": [
                    {
                        "data": [
                            [
                                1,
                                2,
                                3,
                                4
                            ],
                            [
                                1,
                                2,
                                2,
                                5
                            ],
                            [
                                3,
                                3,
                                3,
                                2
                            ]
                        ],
                        "dtype": "int16"
                    }
                ],
                "statistics": [
                    {
                        "operation": "mean"
                    },
                    {
                        "operation": "variety"
                    }
                ],
                "options": {
                    "identifier": "id"
                }
            },
            "expected_output": "id,mean,variety\n\"1\",2.16666674613953,\"3\"\n"
        }
    ]
}
```

---

### Feature 3: Category Fraction Outputs

**As a developer**, I want to summarize categorical rasters as per-category fractions, so I can see the proportion of each observed class inside each feature.

**Expected Behavior / Usage:**

For a categorical raster fraction request, the output schema expands dynamically to one column for each observed category that contributes to the processed feature set. Each row contains the feature identifier and the fraction of valid covered area belonging to each category. Missing categories in a feature are represented by an empty CSV field.

**Test Cases:** `rcb_tests/public_test_cases/feature3_category_fraction_columns.json`

```json
{
    "description": "Return one fraction column per observed raster category across all processed features.",
    "cases": [
        {
            "input": {
                "features": [
                    {
                        "id": 1,
                        "geometry": "POLYGON ((0 0, 3 0, 3 [a fractional area value relative to the raster extent], 0 [a fractional area value relative to the raster extent], 0 0))"
                    },
                    {
                        "id": 2,
                        "geometry": "POLYGON ((1.5 1.5, 2.5 1.5, 2.5 2.5, 1.5 2.5, 1.5 1.5))"
                    }
                ],
                "rasters": [
                    {
                        "data": [
                            [
                                1,
                                2,
                                3
                            ],
                            [
                                1,
                                2,
                                2
                            ],
                            [
                                3,
                                3,
                                3
                            ]
                        ],
                        "dtype": "int16",
                        "name": "class"
                    }
                ],
                "statistics": [
                    {
                        "operation": "frac",
                        "raster": "class"
                    }
                ],
                "options": {
                    "identifier": "id"
                }
            },
            "expected_output": "id,frac_2,frac_3\n\"1\",,1\n\"2\",0.75,[a fractional area value relative to the raster extent]\n"
        }
    ]
}
```

---

### Feature 4: Empty and Missing-Data Intersections

**As a developer**, I want to receive stable outputs when a feature has no valid raster observations, so I can handle features outside coverage or over missing data without special-case failures.

**Expected Behavior / Usage:**

If a feature does not intersect the raster, count is zero and aggregate statistics that require values are reported as `nan`. If the feature intersects only missing raster cells, count is also zero; mean is `nan`; mode is `nan` for floating missing values and the configured missing-data sentinel for integer rasters.

**Test Cases:** `rcb_tests/public_test_cases/feature4_empty_and_nodata_intersections.json`

```json
{
    "description": "Report neutral numeric results for features outside the raster or inside cells with no valid values.",
    "cases": [
        {
            "input": {
                "features": [
                    {
                        "id": 1,
                        "geometry": "POLYGON ((100 100, 200 100, 200 200, 100 100))"
                    }
                ],
                "rasters": [
                    {
                        "data": [
                            [
                                1,
                                2,
                                3
                            ],
                            [
                                1,
                                2,
                                2
                            ],
                            [
                                3,
                                3,
                                3
                            ]
                        ],
                        "dtype": "float32",
                        "name": "value"
                    }
                ],
                "statistics": [
                    {
                        "operation": "count",
                        "raster": "value"
                    },
                    {
                        "operation": "mean",
                        "raster": "value"
                    }
                ],
                "options": {
                    "identifier": "id"
                }
            },
            "expected_output": "id,value_count,value_mean\n\"1\",0,nan\n"
        },
        {
            "input": {
                "features": [
                    {
                        "id": 1,
                        "geometry": "POLYGON (([a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent], 2.5 [a fractional area value relative to the raster extent], 2.5 2, [a fractional area value relative to the raster extent] 2, [a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent]))"
                    }
                ],
                "rasters": [
                    {
                        "data": [
                            [
                                NaN,
                                NaN,
                                NaN
                            ],
                            [
                                NaN,
                                NaN,
                                NaN
                            ],
                            [
                                NaN,
                                NaN,
                                NaN
                            ],
                            [
                                NaN,
                                NaN,
                                NaN
                            ]
                        ],
                        "dtype": "float32",
                        "name": "metric"
                    }
                ],
                "statistics": [
                    {
                        "operation": "count",
                        "raster": "metric"
                    },
                    {
                        "operation": "mean",
                        "raster": "metric"
                    },
                    {
                        "operation": "mode",
                        "raster": "metric"
                    }
                ],
                "options": {
                    "identifier": "id"
                }
            },
            "expected_output": "id,metric_count,metric_mean,metric_mode\n\"1\",0,nan,nan\n"
        },
        {
            "input": {
                "features": [
                    {
                        "id": 1,
                        "geometry": "POLYGON (([a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent], 2.5 [a fractional area value relative to the raster extent], 2.5 2, [a fractional area value relative to the raster extent] 2, [a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent]))"
                    }
                ],
                "rasters": [
                    {
                        "data": [
                            [
                                -999,
                                -999,
                                -999
                            ],
                            [
                                -999,
                                -999,
                                -999
                            ],
                            [
                                -999,
                                -999,
                                -999
                            ],
                            [
                                -999,
                                -999,
                                -999
                            ]
                        ],
                        "dtype": "int32",
                        "name": "metric",
                        "nodata": -999
                    }
                ],
                "statistics": [
                    {
                        "operation": "count",
                        "raster": "metric"
                    },
                    {
                        "operation": "mean",
                        "raster": "metric"
                    },
                    {
                        "operation": "mode",
                        "raster": "metric"
                    }
                ],
                "options": {
                    "identifier": "id"
                }
            },
            "expected_output": "id,metric_count,metric_mean,metric_mode\n\"1\",0,nan,-999\n"
        }
    ]
}
```

---

### Feature 5: Attribute Pass-Through

**As a developer**, I want to copy selected feature attributes into computed output rows, so I can join existing feature metadata with raster-derived statistics.

**Expected Behavior / Usage:**

The input may request named non-geometric feature attributes to be copied into the output. The output CSV preserves the identifier first, then the requested attributes in request order, then computed statistic columns. Attribute values are repeated on the corresponding feature output rows.

**Test Cases:** `rcb_tests/public_test_cases/feature5_attribute_passthrough.json`

```json
{
    "description": "Copy selected non-geometric feature attributes into every output row alongside computed statistics.",
    "cases": [
        {
            "input": {
                "features": [
                    {
                        "id": 1,
                        "name": "A",
                        "class": 1,
                        "geometry": "POLYGON (([a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent], 2.5 [a fractional area value relative to the raster extent], 2.5 2, [a fractional area value relative to the raster extent] 2, [a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent]))"
                    },
                    {
                        "id": 2,
                        "name": "B",
                        "class": 2,
                        "geometry": "POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))"
                    }
                ],
                "rasters": [
                    {
                        "data": [
                            [
                                1,
                                2,
                                3,
                                4
                            ],
                            [
                                1,
                                2,
                                2,
                                5
                            ],
                            [
                                3,
                                3,
                                3,
                                2
                            ]
                        ],
                        "dtype": "int16",
                        "name": "metric"
                    }
                ],
                "statistics": [
                    {
                        "operation": "variety",
                        "raster": "metric"
                    }
                ],
                "options": {
                    "identifier": "id",
                    "copy_attributes": [
                        "name",
                        "class"
                    ]
                }
            },
            "expected_output": "id,name,class,metric_variety\n\"1\",A,\"1\",\"3\"\n\"2\",B,\"2\",\"1\"\n"
        }
    ]
}
```

---

### Feature 6: Cell-Level Intersection Rows

**As a developer**, I want to emit per-cell details for each polygon-raster intersection, so I can inspect coverage fractions, cell positions, and raw cell values.

**Expected Behavior / Usage:**

When cell-level operations are requested, the output contains one row per intersecting raster cell rather than one row per feature. Coverage gives the polygon fraction of each cell. Cell identifiers are zero-based in row-major order, center coordinates are reported in raster coordinates, and copied feature attributes repeat on each cell row.

**Test Cases:** `rcb_tests/public_test_cases/feature6_cell_level_outputs.json`

```json
{
    "description": "Emit one output row per intersecting cell when cell-level statistics are requested.",
    "cases": [
        {
            "input": {
                "features": [
                    {
                        "id": 1,
                        "geometry": "POLYGON (([a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent], 2.5 [a fractional area value relative to the raster extent], 2.5 2.5, [a fractional area value relative to the raster extent] 2.5, [a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent]))"
                    }
                ],
                "rasters": [
                    {
                        "data": [
                            [
                                0,
                                1,
                                2
                            ],
                            [
                                3,
                                4,
                                5
                            ],
                            [
                                6,
                                7,
                                8
                            ]
                        ],
                        "dtype": "int32",
                        "name": "rast"
                    }
                ],
                "statistics": [
                    {
                        "operation": "coverage",
                        "raster": "rast"
                    },
                    {
                        "operation": "values",
                        "raster": "rast"
                    }
                ],
                "options": {
                    "identifier": "id"
                }
            },
            "expected_output": "id,rast_coverage,rast_values\n\"1\",[a fractional area value relative to the raster extent],0\n\"1\",[a fractional area value relative to the raster extent],1\n\"1\",[a fractional area value relative to the raster extent],2\n\"1\",[a fractional area value relative to the raster extent],3\n\"1\",1,4\n\"1\",[a fractional area value relative to the raster extent],5\n\"1\",[a fractional area value relative to the raster extent],6\n\"1\",[a fractional area value relative to the raster extent],7\n\"1\",[a fractional area value relative to the raster extent],8\n"
        },
        {
            "input": {
                "features": [
                    {
                        "id": 1,
                        "class": 3,
                        "type": "B",
                        "geometry": "POLYGON (([a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent], 2.5 [a fractional area value relative to the raster extent], 2.5 2.5, [a fractional area value relative to the raster extent] 2.5, [a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent]))"
                    }
                ],
                "rasters": [
                    {
                        "data": [
                            [
                                0,
                                1,
                                2
                            ],
                            [
                                3,
                                4,
                                5
                            ],
                            [
                                6,
                                7,
                                8
                            ]
                        ],
                        "dtype": "int32",
                        "name": "rast"
                    }
                ],
                "statistics": [
                    {
                        "operation": "coverage",
                        "raster": "rast"
                    },
                    {
                        "operation": "cell_id",
                        "raster": "rast"
                    },
                    {
                        "operation": "center_x",
                        "raster": "rast"
                    },
                    {
                        "operation": "center_y",
                        "raster": "rast"
                    },
                    {
                        "operation": "values",
                        "raster": "rast"
                    }
                ],
                "options": {
                    "identifier": "id",
                    "copy_attributes": [
                        "class",
                        "type"
                    ]
                }
            },
            "expected_output": "id,class,type,rast_coverage,rast_cell_id,rast_center_x,rast_center_y,rast_values\n\"1\",\"3\",B,[a fractional area value relative to the raster extent],\"0\",[a fractional area value relative to the raster extent],2.5,0\n\"1\",\"3\",B,[a fractional area value relative to the raster extent],\"1\",1.5,2.5,1\n\"1\",\"3\",B,[a fractional area value relative to the raster extent],\"2\",2.5,2.5,2\n\"1\",\"3\",B,[a fractional area value relative to the raster extent],\"3\",[a fractional area value relative to the raster extent],1.5,3\n\"1\",\"3\",B,1,\"4\",1.5,1.5,4\n\"1\",\"3\",B,[a fractional area value relative to the raster extent],\"5\",2.5,1.5,5\n\"1\",\"3\",B,[a fractional area value relative to the raster extent],\"6\",[a fractional area value relative to the raster extent],[a fractional area value relative to the raster extent],6\n\"1\",\"3\",B,[a fractional area value relative to the raster extent],\"7\",1.5,[a fractional area value relative to the raster extent],7\n\"1\",\"3\",B,[a fractional area value relative to the raster extent],\"8\",2.5,[a fractional area value relative to the raster extent],8\n"
        }
    ]
}
```

---

### Feature 7: Scaled Raster Cell Values

**As a developer**, I want to apply raster scale and offset metadata to returned cell values, so I can work with physical values rather than stored encoded integers.

**Expected Behavior / Usage:**

For cell value output, if the raster band defines scale and offset metadata, the returned value is `stored_value * scale + offset`. The output still includes the source feature identifier and the intersecting cell identifier.

**Test Cases:** `rcb_tests/public_test_cases/feature7_scaled_raster_cells.json`

```json
{
    "description": "Apply stored scale and offset metadata before returning raster cell values.",
    "cases": [
        {
            "input": {
                "features": [
                    {
                        "id": 1,
                        "geometry": "POLYGON (([a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent], 2.5 [a fractional area value relative to the raster extent], 2.5 2, [a fractional area value relative to the raster extent] 2, [a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent]))"
                    }
                ],
                "rasters": [
                    {
                        "data": [
                            [
                                17650,
                                18085
                            ],
                            [
                                19127,
                                19428
                            ]
                        ],
                        "dtype": "int16",
                        "name": "d2m",
                        "scale": [a fractional area value relative to the raster extent]01571273180860454,
                        "offset": 250.47270984680802
                    }
                ],
                "statistics": [
                    {
                        "operation": "cell_id",
                        "raster": "d2m"
                    },
                    {
                        "operation": "values",
                        "raster": "d2m"
                    }
                ],
                "options": {
                    "identifier": "id"
                }
            },
            "expected_output": "id,d2m_cell_id,d2m_values\n\"1\",\"0\",[a scale and offset pair]\n\"1\",\"1\",278.889185322669\n\"1\",\"2\",28[a fractional area value relative to the raster extent]26451977126\n\"1\",\"3\",280.999405204565\n"
        }
    ]
}
```

---

### Feature 8: Identifier Field Formatting

**As a developer**, I want to control the output identifier column name and numeric type, so I can produce downstream-friendly feature identifiers.

**Expected Behavior / Usage:**

The input may rename the identifier column and request that identifier values be emitted as a numeric type. If no source identifier field is explicitly selected, the generated feature identifier can still be renamed and typed. CSV output uses the configured identifier column as the first column.

**Test Cases:** `rcb_tests/public_test_cases/feature8_identifier_field_formatting.json`

```json
{
    "description": "Rename or type-convert the output identifier field while preserving the feature identity value.",
    "cases": [
        {
            "input": {
                "features": [
                    {
                        "id": "3.14",
                        "geometry": "POLYGON (([a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent], 2.5 [a fractional area value relative to the raster extent], 2.5 2, [a fractional area value relative to the raster extent] 2, [a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent]))"
                    }
                ],
                "rasters": [
                    {
                        "data": [
                            [
                                1,
                                2,
                                3,
                                4
                            ],
                            [
                                1,
                                2,
                                2,
                                5
                            ],
                            [
                                3,
                                3,
                                3,
                                2
                            ]
                        ],
                        "dtype": "int16",
                        "name": "metric"
                    }
                ],
                "statistics": [
                    {
                        "operation": "mean",
                        "raster": "metric"
                    }
                ],
                "options": {
                    "identifier": "id",
                    "identifier_output_name": "orig_id",
                    "identifier_output_type": "float"
                }
            },
            "expected_output": "orig_id,metric_mean\n3.14,2.16666674613953\n"
        },
        {
            "input": {
                "features": [
                    {
                        "id": "3.14",
                        "geometry": "POLYGON (([a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent], 2.5 [a fractional area value relative to the raster extent], 2.5 2, [a fractional area value relative to the raster extent] 2, [a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent]))"
                    }
                ],
                "rasters": [
                    {
                        "data": [
                            [
                                1,
                                2,
                                3,
                                4
                            ],
                            [
                                1,
                                2,
                                2,
                                5
                            ],
                            [
                                3,
                                3,
                                3,
                                2
                            ]
                        ],
                        "dtype": "int16",
                        "name": "metric"
                    }
                ],
                "statistics": [
                    {
                        "operation": "mean",
                        "raster": "metric"
                    }
                ],
                "options": {
                    "identifier_output_name": "id",
                    "identifier_output_type": "float"
                }
            },
            "expected_output": "id,metric_mean\n3.14,2.16666674613953\n"
        }
    ]
}
```

---

### Feature 9: Geometry and Spatial Reference Preservation

**As a developer**, I want to include source geometry in geometry-capable outputs, so I can produce spatial outputs that retain feature shape and coordinate reference metadata.

**Expected Behavior / Usage:**

When geometry output is requested with a geometry-capable format, the output record preserves the source polygon geometry and spatial reference. The adapter renders this contract as field values plus normalized geometry and spatial-reference signals: geometry type and whether the coordinate reference metadata identifies the expected projected region.

**Test Cases:** `rcb_tests/public_test_cases/feature9_geometry_and_spatial_reference_output.json`

```json
{
    "description": "Preserve input geometry and spatial reference when geometry output is requested for a geometry-capable output format.",
    "cases": [
        {
            "input": {
                "features": [
                    {
                        "id": "3.14",
                        "geometry": "POLYGON (([a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent], 2.5 [a fractional area value relative to the raster extent], 2.5 2, [a fractional area value relative to the raster extent] 2, [a fractional area value relative to the raster extent] [a fractional area value relative to the raster extent]))"
                    }
                ],
                "rasters": [
                    {
                        "data": [
                            [
                                1,
                                2,
                                3,
                                4
                            ],
                            [
                                1,
                                2,
                                2,
                                5
                            ],
                            [
                                3,
                                3,
                                3,
                                2
                            ]
                        ],
                        "dtype": "int16",
                        "name": "metric"
                    }
                ],
                "statistics": [
                    {
                        "operation": "mean",
                        "raster": "metric",
                        "output": "y"
                    }
                ],
                "options": {
                    "identifier": "id",
                    "identifier_output_name": "orig_id",
                    "identifier_output_type": "float",
                    "include_geometry": true
                },
                "output_format": "shp",
                "feature_srs": 32145
            },
            "expected_output": "fields=orig_id=3.14;y=2.166666746139526\ngeometry_type=POLYGON\nsrs_contains_vermont=true\n"
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
- implements the 'shp' strict domain format
- uses the attribute exclusion logic from the schema module
