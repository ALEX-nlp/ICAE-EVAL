## Product Requirement Document

# Geospatial Coordinate Operations Toolkit - Black-Box Coordinate Conversion, Geodesic Measurement, Registry Lookup, and Support-Data Synchronization

## Project Goal

Build a geospatial coordinate operations toolkit that allows developers to create coordinate transformations, measure ellipsoidal distances and geometry properties, inspect reference metadata, and manage transformation support-data records without manually implementing projection mathematics, geodesic algorithms, or support-file catalog filtering.

---

## Background & Problem

Without this library/tool, developers are forced to hand-code coordinate reference conversions, ellipsoidal distance calculations, area/perimeter algorithms, reference database lookups, and transformation-grid discovery logic. This leads to repetitive code, subtle axis-order mistakes, inconsistent numeric behavior, fragile error handling, and maintenance issues whenever geospatial data definitions change.

With this library/tool, applications can describe the desired spatial operation or catalog query in a compact input object and receive deterministic stdout fields that capture the observable geospatial result, metadata, or normalized error category.

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

### Feature 1: Projection Definitions and Projected Points

**As a developer**, I want to create projected coordinate operations from declarative geospatial parameters, so I can convert longitude-latitude or projected coordinate inputs with reproducible numeric output.

**Expected Behavior / Usage:**

Input is a JSON object describing either a coordinate operation parameter set or a named projection definition plus one coordinate pair. Output is newline-delimited fields: normalized operation parameters for definition inspection, or numeric x/y fields for coordinate conversion. Boolean parameter flags are included only when enabled; disabled flags do not appear.

**Test Cases:** `rcb_tests/public_test_cases/feature1_projection_parameters_and_points.json`

```json
{
    "description": "Create projected coordinate operations from geospatial parameter sets and apply them to input coordinates, including boolean flags in parameter dictionaries.",
    "cases": [
        {
            "input": {
                "action": "projection_definition",
                "projection": {
                    "parameters": {
                        "proj": "lcc",
                        "R": 6371200,
                        "lat_1": 50,
                        "lat_2": 50,
                        "lon_0": -107
                    },
                    "preserve_units": false
                }
            },
            "expected_output": "parameter=+R=6371200\nparameter=+[a specific geographic coordinate pair used in projection parameters — request exact floats from the PM]\nparameter=+[a specific geographic coordinate pair used in projection parameters — request exact floats from the PM]\nparameter=+[a specific geographic coordinate pair used in projection parameters — request exact floats from the PM]\nparameter=+proj=lcc\nparameter=+type=crs\n"
        }
    ]
}
```

---

### Feature 2: Coordinate Transformation

**As a developer**, I want to transform coordinates between coordinate reference systems, so I can move 2D, 3D, and time-tagged positions between spatial reference definitions.

**Expected Behavior / Usage:**

Input is a source reference, target reference, coordinate tuple, and optional mode flags for legacy single-call or streaming transformation. Output is one point line containing comma-separated numeric ordinates in the transformed coordinate space, preserving height or time values when the operation supports them.

**Test Cases:** `rcb_tests/public_test_cases/feature2_coordinate_transformation.json`

```json
{
    "description": "Transform 2D, 3D, and time-tagged coordinates between coordinate reference definitions, including legacy single-call and streaming modes.",
    "cases": [
        {
            "input": {
                "action": "coordinate_transform",
                "mode": "legacy_single",
                "source": "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs",
                "target": "+proj=geos +lon_0=0.000000 +lat_0=0 +h=35807.414063 +a=6378.169000 +b=6356.583984",
                "coordinate": [
                    3.23406,
                    51.04715
                ]
            },
            "expected_output": "point=212.623382,4604.975492\n"
        }
    ]
}
```

---

### Feature 3: Axis Order and Direction Controls

**As a developer**, I want to control coordinate axis order and transformation direction, so I can obtain predictable output when a reference system has native axis ordering or when I need inverse/identity behavior.

**Expected Behavior / Usage:**

Input includes source and target references, a coordinate tuple, and optional always-x-y or direction controls. Output is a point line showing the resulting coordinate tuple. Invalid direction text is normalized to an error category plus the raw direction value.

**Test Cases:** `rcb_tests/public_test_cases/feature3_axis_order_and_direction.json`

```json
{
    "description": "Respect requested axis order and transformation direction when converting coordinates between reference systems.",
    "cases": [
        {
            "input": {
                "action": "coordinate_transform",
                "source": 2193,
                "target": 4326,
                "coordinate": [
                    1625350,
                    5504853
                ],
                "always_xy": true
            },
            "expected_output": "point=173.299647,-40.606748\n"
        }
    ]
}
```

---

### Feature 4: Geodesic Calculations

**As a developer**, I want to compute ellipsoidal geodesic results, so I can measure distances, azimuths, destinations, intermediate points, and line lengths on an ellipsoid.

**Expected Behavior / Usage:**

Input names an ellipsoid and a geodesic calculation type with longitude-latitude coordinates. Output uses domain fields such as forward_azimuth, back_azimuth, distance_m, longitude, latitude, point, length_m, and segment_m, with meter values rounded for stable black-box comparison.

**Test Cases:** `rcb_tests/public_test_cases/feature4_geodesic_calculations.json`

```json
{
    "description": "Calculate ellipsoidal inverse and forward geodesics, intermediate points, and line distances for longitude-latitude inputs.",
    "cases": [
        {
            "input": {
                "action": "geodesic",
                "calculation": "inverse",
                "ellipsoid": {
                    "ellps": "clrk66"
                },
                "start": [
                    -71.11666666666666,
                    42.25
                ],
                "end": [
                    -123.68333333333334,
                    45.516666666666666
                ]
            },
            "expected_output": "forward_azimuth=-66.531\nback_azimuth=75.654\ndistance_m=4164192.708\n"
        }
    ]
}
```

---

### Feature 5: Geometry Measurements

**As a developer**, I want to measure geodesic properties of geometry-like coordinate arrays, so I can calculate length, area, and perimeter for point, line, ring, and polygon inputs.

**Expected Behavior / Usage:**

Input is a simple geometry object with a type and coordinate arrays, plus the requested measurement. Output is length_m for length requests, or area_m2 and perimeter_m for area/perimeter requests. Degenerate point geometry reports zero length.

**Test Cases:** `rcb_tests/public_test_cases/feature5_geometry_measurements.json`

```json
{
    "description": "Measure geodesic length, area, and perimeter for simple geometry objects supplied as coordinate arrays.",
    "cases": [
        {
            "input": {
                "action": "geometry_measurement",
                "measurement": "length",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        1,
                        2
                    ]
                }
            },
            "expected_output": "length_m=0.000\n"
        }
    ]
}
```

---

### Feature 6: Reference Registry Lookups

**As a developer**, I want to query geospatial reference metadata, so I can discover units, ellipsoids, meridians, operations, authorities, and available code sets.

**Expected Behavior / Usage:**

Input specifies a registry query and optional filters such as category, authority, type, or deprecation inclusion. Output reports stable metadata fields for the matched registry item or summary counts and representative codes. Invalid registry type values are normalized to error=invalid_registry_query.

**Test Cases:** `rcb_tests/public_test_cases/feature6_reference_registry.json`

```json
{
    "description": "Expose reference database metadata for units, ellipsoids, prime meridians, projection operations, authorities, and code sets.",
    "cases": [
        {
            "input": {
                "action": "registry",
                "query": "unit",
                "name": "metre"
            },
            "expected_output": "name=metre\nauthority=EPSG\ncode=9001\ncategory=linear\nfactor=1.000000\nshort_name=m\ndeprecated=false\n"
        }
    ]
}
```

---

### Feature 7: Transformation Grid Catalog Filters

**As a developer**, I want to filter a support-data catalog, so I can find transformation grid files by source, geographic area, file name, bounding box, and spatial predicate.

**Expected Behavior / Usage:**

Input is a catalog filter object containing optional bounding box, source identifier, file-name fragment, area text, spatial predicate, and world-coverage inclusion flag. Output reports the number of matched grids, the sorted source identifiers, and first/last matched file names so both filtering and result ordering are observable.

**Test Cases:** `rcb_tests/public_test_cases/feature7_grid_catalog_filters.json`

```json
{
    "description": "Filter a transformation support-data catalog by file name, source, area text, bounding box, and spatial relationship.",
    "cases": [
        {
            "input": {
                "action": "grid_catalog",
                "bbox": [
                    170,
                    -90,
                    -170,
                    90
                ],
                "include_already_downloaded": true
            },
            "expected_output": "count=68\nsource_ids=au_ga,nc_dittt,nz_linz,us_nga,us_noaa\nfirst_file=au_ga_AGQG_20191107.tif\nlast_file=us_noaa_nadcon5_nad83_2007_nad83_2011_alaska.tif\n"
        }
    ]
}
```

---

### Feature 8: Bounding Box Predicates

**As a developer**, I want to compare geographic bounding boxes, so I can know whether one extent contains or intersects another extent.

**Expected Behavior / Usage:**

Input contains two bounding boxes encoded as west, south, east, north numeric arrays. Output contains contains and intersects boolean fields as lowercase text, allowing overlap, containment, and disjoint cases to be distinguished.

**Test Cases:** `rcb_tests/public_test_cases/feature8_bounding_box_predicates.json`

```json
{
    "description": "Evaluate whether one geographic bounding box contains or intersects another bounding box.",
    "cases": [
        {
            "input": {
                "action": "bbox_relation",
                "left": [
                    1,
                    1,
                    4,
                    4
                ],
                "right": [
                    2,
                    2,
                    3,
                    3
                ]
            },
            "expected_output": "contains=true\nintersects=true\n"
        }
    ]
}
```

---

### Feature 9: Transformation Metadata and Candidate Groups

**As a developer**, I want to inspect transformation metadata and candidate operations, so I can understand operation names, summaries, export shape, and available transformation alternatives.

**Expected Behavior / Usage:**

Input requests either metadata for one transformation or a candidate group for a source-target pair, optionally constrained by an area. Output includes operation names, summary fields, JSON-export signals, or group availability/count fields and first candidate details.

**Test Cases:** `rcb_tests/public_test_cases/feature9_transformer_metadata_and_groups.json`

```json
{
    "description": "Report selected metadata and candidate-operation groups for coordinate transformations.",
    "cases": [
        {
            "input": {
                "action": "transformer_metadata",
                "source": 4326,
                "target": 3857,
                "detail": "summary"
            },
            "expected_output": "name=pipeline\ndescription=Popular Visualisation Pseudo-Mercator\nhas_inverse=true\naccuracy=0.000\n"
        }
    ]
}
```

---

### Feature 10: Support File Integrity and Download Simulation

**As a developer**, I want to compute checksums and validate simulated downloads, so I can verify support-data file integrity and observe download progress behavior without relying on a live network.

**Expected Behavior / Usage:**

Input is either file content for checksum calculation or a simulated download request with URL, target file name, verbosity, downloaded content, and optional checksum. Output reports the checksum, captured progress text, file existence, and final checksum, or a normalized download_failed error for validation failure.

**Test Cases:** `rcb_tests/public_test_cases/feature10_file_integrity_and_downloads.json`

```json
{
    "description": "Compute support-file checksums and simulate resource downloads with optional checksum validation and verbose progress output.",
    "cases": [
        {
            "input": {
                "action": "checksum",
                "content": "TEST"
            },
            "expected_output": "sha256=94ee059335e587e501cc4bf90613e0814f00a7b08bc7c648fd865a2af6a22cc2\n"
        }
    ]
}
```

---

### Feature 11: Normalized Transformation Errors

**As a developer**, I want to receive language-neutral error categories for invalid transformation requests, so I can handle transformation-domain failures without depending on runtime exception class names.

**Expected Behavior / Usage:**

Input is an invalid transformation request such as a non-transform pipeline definition or an incompatible time-coordinate option. Output is a language-neutral error category line only, avoiding host-language exception names and runtime-specific message text.

**Test Cases:** `rcb_tests/public_test_cases/feature11_error_contracts.json`

```json
{
    "description": "Normalize domain errors from invalid transformation definitions, coordinate failures, and invalid option combinations.",
    "cases": [
        {
            "input": {
                "action": "coordinate_transform",
                "pipeline": "epsg:4326",
                "coordinate": [
                    1,
                    2
                ]
            },
            "expected_output": "error=invalid_transformation_definition\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
