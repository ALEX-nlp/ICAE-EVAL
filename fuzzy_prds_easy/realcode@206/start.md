## Product Requirement Document

# Geographic Feature Interchange Toolkit - A GeoJSON Object Model and Serializer

## Project Goal

Build a library and serialization layer for the GeoJSON geographic data interchange format that allows developers to [a specific list of operation identifiers defined in the protocol spec], validate, compare, and losslessly convert geographic geometries, features, and coordinate reference systems to and from their standard JSON text form, without hand-writing fragile parsing and formatting code for each shape.

---

## Background & Problem

Geographic data is exchanged as JSON documents in which each object is tagged by a `type` discriminator (a point, a path, an area, a collection, a feature, a feature collection) and carries coordinate arrays ordered horizontal-axis, vertical-axis, and optional elevation. Without a dedicated library, developers must repeatedly hand-roll position parsing, axis-order handling, ring-closure validation, coordinate-reference-system encoding, and structural equality. This is repetitive, easy to get subtly wrong (axis order, optional elevation, ring validity), and hard to keep consistent across producers and consumers.

With this library, developers work with a typed object model for each geometry and document kind, get strict [a specific list of operation identifiers defined in the protocol spec]ion-time validation with clear error semantics, get value equality and hashing, and get a [a specific list of operation identifiers defined in the protocol spec]r/de[a specific list of operation identifiers defined in the protocol spec]r that reproduces the exact wire shapes the format mandates.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility domain (an object model, a validation layer, several format converters, and an execution adapter). It MUST be organized as a clear, multi-file tree separating the domain types, the serialization converters, and the adapter — not a single monolithic file. Do not over-engineer, but do not collapse distinct responsibilities together.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box contract for the execution adapter**, NOT the internal data model. The core domain (geometries, features, coordinate reference systems, equality, validation, and the format converters) MUST be completely decoupled from stdin/stdout and from the adapter's command envelope. The adapter alone translates each JSON command into idiomatic calls on the core domain and renders the result.

3. **Adherence to SOLID Design Principles:** Separate parsing, command routing, validation, core [a specific list of operation identifiers defined in the protocol spec]ion, format conversion, and output rendering into distinct cohesive units; keep the converters open for extension to new geometry kinds; make derived geometry/CRS types substitutable for their abstractions; keep interfaces small; depend on abstractions rather than on the I/O layer.

4. **Robustness & Interface Design:** The public object model must be idiomatic and hide internal complexity. Invalid [a specific list of operation identifiers defined in the protocol spec]ion must be modeled as proper, typed failures (raise idiomatic errors); the adapter is responsible for normalizing those native failures into the neutral `error=...` contract defined below — the core domain must never write to stdout nor embed the host runtime's error identity into output.

---

## Execution Adapter Protocol

The execution adapter is a runnable program that reads **exactly one JSON object** from stdin, performs the operation it names, and writes a deterministic textual result to stdout. All numbers are formatted culture-invariantly (dot as decimal separator). Lines are separated by `\n`. Each operation appears in the cases below.

**Value shapes used inside commands**

- *Geometry value:* `{"type": "<Point|LineString|MultiPoint|MultiLineString|Polygon|MultiPolygon|GeometryCollection>", "coordinates": ...}` (a geometry collection instead carries `"geometries": [ ... ]`). A position is `[horizontal, vertical]` or `[horizontal, vertical, elevation]`. A `null` coordinates/geometries value is passed through to [a specific list of operation identifiers defined in the protocol spec]ion so its validation can be exercised. An optional `"crs"` member may be attached (see CRS value).
- *CRS value:* `{"kind": "named", "name": <string|null>}`, `{"kind": "linked", "href": <string|null>, "type": <string?>}`, or `{"kind": "unspecified"}`.
- *Object value (for `[a specific list of operation identifiers defined in the protocol spec]`/`[a specific list of operation identifiers defined in the protocol spec]`):* a geometry value, or `{"kind": "feature", "geometry": <geometry|null>, "properties": <object?>, "id": <string?>}`, or `{"kind": "feature_collection", "features": [<feature>...]|null, "crs": <CRS value?>}`.

**Operations**

- `[a specific list of operation identifiers defined in the protocol spec]` — fields `object` and `formatting` (`none` or `indented`). Builds the object value and prints its GeoJSON text followed by a newline. Property order is fixed by the format (e.g. a geometry renders `type` then `coordinates`, with any `crs` last; a CRS renders `properties` then `type`).
- `[a specific list of operation identifiers defined in the protocol spec]` — fields `target` and `wire`. Parses the `wire` string as the named target type and re-renders it compact, followed by a newline. Targets: `Point`, `LineString`, `MultiPoint`, `MultiLineString`, `Polygon`, `MultiPolygon`, `GeometryCollection`, `Feature`, `FeatureCollection`, `Geometry` (type-driven geometry), `GeoJSONObject` (type-driven any object), `FeaturePoint`/`FeatureLineString` (feature over a known geometry type), `FeatureTypedPoint` (feature with a typed property object), `FeatureCollectionGeneric` (collection with typed feature properties).
- `[a specific list of operation identifiers defined in the protocol spec]` — field `object`. Builds the value to exercise [a specific list of operation identifiers defined in the protocol spec]ion-time validation. On invalid input it prints the normalized error block (below). (Valid [a specific list of operation identifiers defined in the protocol spec]ion prints a single `[a specific list of operation identifiers defined in the protocol spec]ed=<type-discriminator>` line.)
- `[a specific list of operation identifiers defined in the protocol spec]` — field `geometry` (a line string). Prints `[a specific list of operation identifiers defined in the protocol spec]=<true|false>` then `is_linear_ring=<true|false>`.
- `[a specific list of operation identifiers defined in the protocol spec]` — fields `kind` (`geometry`, `crs`, `feature`, or `feature_collection`), `left`, and `right` (either may be `null`). Prints five lines: `[a specific list of operation identifiers defined in the protocol spec]`, `[a specific list of operation identifiers defined in the protocol spec]_reverse`, `op_[a specific list of operation identifiers defined in the protocol spec]`, `op_not_[a specific list of operation identifiers defined in the protocol spec]`, and `hash_equal` (each `true`/`false`, except `hash_equal` which is `na` when a hash cannot be computed).
- `[a specific list of operation identifiers defined in the protocol spec]` — field `crs`. Prints `type=<name|link|unspecified>` then, for property-bearing systems, `prop.<key>=<value>` lines sorted by key.
- `[a specific list of operation identifiers defined in the protocol spec]_equal` — fields `via` (`geometry` or `geojson`) and `geometry`. Serializes then de[a specific list of operation identifiers defined in the protocol spec]s through the named converter and prints `equal=<true|false>`.
- `wrapper_[a specific list of operation identifiers defined in the protocol spec]` — field `geometry`. Serializes a host object carrying the geometry as a property, de[a specific list of operation identifiers defined in the protocol spec]s it, and prints `equal=<…>` then `hash_equal=<…>`.
- `typed_feature_[a specific list of operation identifiers defined in the protocol spec]` — fields `geometry`, `name`, `value`, `id`. Serializes a feature whose properties are a typed object with `name` and `value` members.

**Error normalization contract**

Construction failures and unsupported requests are rendered as a neutral, language-independent block — never the host runtime's exception type or message. Categories:

- `error=argument_null` + `param=<name>` — a required argument was null.
- `error=[a specific error code constant for out-of-range validation]` + `param=<name>` — an argument was outside its allowed range.
- `error=argument_invalid` + `param=<name>` + `reason=<must_be_specified|[a specific validation rule describing acceptable URI formats]|not_a_linear_ring|invalid>` — an argument was otherwise invalid.
- `error=json` — the input text was not valid JSON for the requested target.
- `error=not_supported` — the requested conversion is not supported for that type.

---

## Core Features


### Feature 1: Point Geometry

**As a developer**, I want to represent a single geographic location and move it in and out of text losslessly.

**Expected Behavior / Usage:**

A point holds one position. A position is an ordered tuple of numbers in axis order: horizontal axis (e.g. longitude) first, vertical axis (e.g. latitude) second, and an optional elevation third. The `[a specific list of operation identifiers defined in the protocol spec]` op renders a point to a JSON object whose members are a `type` discriminator of `"Point"` and a `coordinates` array carrying the position; every supplied component is emitted, including components equal to zero, and the elevation appears only when it was supplied. The `[a specific list of operation identifiers defined in the protocol spec]` op (`target` of `Point`) parses such an object and re-renders it, reproducing the same coordinates and preserving the presence or absence of elevation. The `[a specific list of operation identifiers defined in the protocol spec]` op (`kind` of `geometry`) reports structural equality of two points across five lines (`[a specific list of operation identifiers defined in the protocol spec]`, `[a specific list of operation identifiers defined in the protocol spec]_reverse`, `op_[a specific list of operation identifiers defined in the protocol spec]`, `op_not_[a specific list of operation identifiers defined in the protocol spec]`, `hash_equal`): points with the same position are equal and share a hash; differing positions are unequal.

**Test Cases:** `rcb_tests/public_test_cases/feature01_point.json`

```json
{
  "description": "A point is the simplest geometry: a single coordinate. Serializing a point produces a JSON object carrying a type discriminator and a coordinate array given in axis order (horizontal first, then vertical, then an optional elevation as a third element). Every supplied coordinate component is always emitted, including components whose value is zero. Deserializing the same shape re[a specific list of operation identifiers defined in the protocol spec]s an equal point, preserving the optional elevation only when it was present. Two points built from the same coordinate compare equal and produce the same hash code; differing coordinates compare unequal.",
  "cases": [
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "object": {
          "type": "Point",
          "coordinates": [
            90.65464646,
            53.2455662
          ]
        },
        "formatting": "none"
      },
      "expected_output": "{\"type\":\"Point\",\"coordinates\":[90.65464646,53.2455662]}\n"
    },
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "object": {
          "type": "Point",
          "coordinates": [
            90.65464646,
            53.2455662,
            200.4567
          ]
        },
        "formatting": "none"
      },
      "expected_output": "{\"type\":\"Point\",\"coordinates\":[90.65464646,53.2455662,200.4567]}\n"
    },
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "kind": "geometry",
        "left": {
          "type": "Point",
          "coordinates": [
            90.65464646,
            53.2455662
          ]
        },
        "right": {
          "type": "Point",
          "coordinates": [
            90.65464646,
            53.2455662
          ]
        }
      },
      "expected_output": "[a specific list of operation identifiers defined in the protocol spec]=true\n[a specific list of operation identifiers defined in the protocol spec]_reverse=true\nop_[a specific list of operation identifiers defined in the protocol spec]=true\nop_not_[a specific list of operation identifiers defined in the protocol spec]=false\nhash_equal=true\n"
    }
  ]
}
```

---

### Feature 2: Line String Geometry

**As a developer**, I want to model a connected path of positions and query its shape.

**Expected Behavior / Usage:**

A line string is an ordered list of two or more positions, [a specific list of operation identifiers defined in the protocol spec]d as a `type` of `"LineString"` plus a `coordinates` array of position arrays, and recovered intact by `[a specific list of operation identifiers defined in the protocol spec]`. The `[a specific list of operation identifiers defined in the protocol spec]` op reports two booleans (`[a specific list of operation identifiers defined in the protocol spec]`, `is_linear_ring`): closed means the first and last positions coincide; a linear ring is a closed line string with at least four positions. The `[a specific list of operation identifiers defined in the protocol spec]` op validates inputs: a null coordinate list yields the normalized error `error=argument_null` with `param=coordinates`; a list of fewer than two positions yields `error=[a specific error code constant for out-of-range validation]` with `param=coordinates`. The `[a specific list of operation identifiers defined in the protocol spec]` op reports the usual five-line equality contract.

**Test Cases:** `rcb_tests/public_test_cases/feature02_linestring.json`

```json
{
  "description": "A line string is an ordered sequence of two or more coordinates. It [a specific list of operation identifiers defined in the protocol spec]s to a type discriminator plus an array of coordinate arrays, and round-trips back to an equal value. A line string can report whether it is closed (its first and last coordinates coincide) and whether it forms a linear ring (closed and having at least four coordinates). Construction validates its input: a null coordinate sequence is rejected as a missing required argument, and a sequence with fewer than two coordinates is rejected as out of range. Equal coordinate sequences yield equal line strings sharing a hash code.",
  "cases": [
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "object": {
          "type": "LineString",
          "coordinates": [
            [
              4.889259338378906,
              52.370725881211314
            ],
            [
              4.895267486572266,
              52.3711451105601
            ],
            [
              4.892091751098633,
              52.36931095278263
            ],
            [
              4.889259338378906,
              52.370725881211314
            ]
          ]
        },
        "formatting": "none"
      },
      "expected_output": "{\"type\":\"LineString\",\"coordinates\":[[4.889259338378906,52.370725881211314],[4.895267486572266,52.3711451105601],[4.892091751098633,52.36931095278263],[4.889259338378906,52.370725881211314]]}\n"
    },
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "geometry": {
          "type": "LineString",
          "coordinates": [
            [
              4.889259338378906,
              52.370725881211314
            ],
            [
              4.895267486572266,
              52.3711451105601
            ],
            [
              4.892091751098633,
              52.36931095278263
            ],
            [
              4.889259338378906,
              52.370725881211314
            ]
          ]
        }
      },
      "expected_output": "[a specific list of operation identifiers defined in the protocol spec]=true\nis_linear_ring=true\n"
    },
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "object": {
          "type": "LineString",
          "coordinates": null
        }
      },
      "expected_output": "error=argument_null\nparam=coordinates\n"
    }
  ]
}
```

---

### Feature 3: Multi-Point Geometry

**As a developer**, I want to group several standalone positions as one geometry.

**Expected Behavior / Usage:**

A multi-point is a collection of points, [a specific list of operation identifiers defined in the protocol spec]d as a `type` of `"MultiPoint"` and a `coordinates` array of positions, and recovered by `[a specific list of operation identifiers defined in the protocol spec]`. The `[a specific list of operation identifiers defined in the protocol spec]` op gives the five-line equality contract; multi-points over the same positions are equal and share a hash.

**Test Cases:** `rcb_tests/public_test_cases/feature03_multipoint.json`

```json
{
  "description": "A multi-point is a collection of point geometries. It [a specific list of operation identifiers defined in the protocol spec]s to a type discriminator and an array of coordinate arrays, and round-trips back to an equal value. Two multi-points built from the same set of coordinates compare equal and share a hash code.",
  "cases": [
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "object": {
          "type": "MultiPoint",
          "coordinates": [
            [
              4.889259338378906,
              52.370725881211314
            ],
            [
              4.895267486572266,
              52.3711451105601
            ],
            [
              4.892091751098633,
              52.36931095278263
            ],
            [
              4.889259338378906,
              52.370725881211314
            ]
          ]
        },
        "formatting": "none"
      },
      "expected_output": "{\"type\":\"MultiPoint\",\"coordinates\":[[4.889259338378906,52.370725881211314],[4.895267486572266,52.3711451105601],[4.892091751098633,52.36931095278263],[4.889259338378906,52.370725881211314]]}\n"
    }
  ]
}
```

---

### Feature 4: Multi-Line-String Geometry

**As a developer**, I want to group several paths as one geometry.

**Expected Behavior / Usage:**

A multi-line-string is a collection of line strings, [a specific list of operation identifiers defined in the protocol spec]d as a `type` of `"MultiLineString"` and a nested `coordinates` array (one position-array per line), and recovered by `[a specific list of operation identifiers defined in the protocol spec]`. The `[a specific list of operation identifiers defined in the protocol spec]` op gives the five-line equality contract.

**Test Cases:** `rcb_tests/public_test_cases/feature04_multilinestring.json`

```json
{
  "description": "A multi-line-string is a collection of line strings. It [a specific list of operation identifiers defined in the protocol spec]s to a type discriminator and a nested array of coordinate arrays, and round-trips back to an equal value. Two multi-line-strings built from the same coordinates compare equal and share a hash code.",
  "cases": [
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "object": {
          "type": "MultiLineString",
          "coordinates": [
            [
              [
                5.3173828125,
                52.379790828551016
              ],
              [
                5.456085205078125,
                52.36721467920585
              ],
              [
                5.386047363281249,
                52.303440474272755,
                4.23
              ]
            ],
            [
              [
                5.3273828125,
                52.379790828551016
              ],
              [
                5.486085205078125,
                52.36721467920585
              ],
              [
                5.426047363281249,
                52.303440474272755,
                4.23
              ]
            ]
          ]
        },
        "formatting": "none"
      },
      "expected_output": "{\"type\":\"MultiLineString\",\"coordinates\":[[[5.3173828125,52.379790828551016],[5.456085205078125,52.36721467920585],[5.386047363281249,52.303440474272755,4.23]],[[5.3273828125,52.379790828551016],[5.486085205078125,52.36721467920585],[5.426047363281249,52.303440474272755,4.23]]]}\n"
    }
  ]
}
```

---

### Feature 5: Polygon Geometry

**As a developer**, I want to describe a filled area with an outer boundary and optional holes.

**Expected Behavior / Usage:**

A polygon is one or more linear rings: an exterior ring optionally followed by interior rings (holes). It [a specific list of operation identifiers defined in the protocol spec]s as a `type` of `"Polygon"` and a nested `coordinates` array of rings, and `[a specific list of operation identifiers defined in the protocol spec]` recovers it intact, including the multi-ring case. `[a specific list of operation identifiers defined in the protocol spec]` validates inputs: a null ring list yields `error=argument_null` with `param=coordinates`; any ring that is not a closed linear ring (at least four positions, first equal to last) yields `error=argument_invalid` with `param=coordinates` and `reason=not_a_linear_ring`. The `[a specific list of operation identifiers defined in the protocol spec]` op gives the five-line equality contract.

**Test Cases:** `rcb_tests/public_test_cases/feature05_polygon.json`

```json
{
  "description": "A polygon is described by one or more linear rings: an exterior ring optionally followed by interior rings. It [a specific list of operation identifiers defined in the protocol spec]s to a type discriminator and a nested array of coordinate arrays, and round-trips back to an equal value, including the multi-ring (exterior plus interior) case. Construction validates its input: a null ring sequence is rejected as a missing required argument, and any ring that is not a closed linear ring (at least four coordinates, first equal to last) is rejected as invalid. Polygons built from equal rings compare equal and share a hash code.",
  "cases": [
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "object": {
          "type": "Polygon",
          "coordinates": [
            [
              [
                5.3173828125,
                52.379790828551016
              ],
              [
                5.456085205078125,
                52.36721467920585
              ],
              [
                5.386047363281249,
                52.303440474272755,
                4.23
              ],
              [
                5.3173828125,
                52.379790828551016
              ]
            ]
          ]
        },
        "formatting": "none"
      },
      "expected_output": "{\"type\":\"Polygon\",\"coordinates\":[[[5.3173828125,52.379790828551016],[5.456085205078125,52.36721467920585],[5.386047363281249,52.303440474272755,4.23],[5.3173828125,52.379790828551016]]]}\n"
    },
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "object": {
          "type": "Polygon",
          "coordinates": null
        }
      },
      "expected_output": "error=argument_null\nparam=coordinates\n"
    }
  ]
}
```

---

### Feature 6: Multi-Polygon Geometry

**As a developer**, I want to group several polygons as one geometry.

**Expected Behavior / Usage:**

A multi-polygon is a collection of polygons, [a specific list of operation identifiers defined in the protocol spec]d as a `type` of `"MultiPolygon"` and a deeply nested `coordinates` array, recovered by `[a specific list of operation identifiers defined in the protocol spec]`. A null polygon list at `[a specific list of operation identifiers defined in the protocol spec]` yields `error=argument_null` with `param=polygons`. The `[a specific list of operation identifiers defined in the protocol spec]` op gives the five-line equality contract.

**Test Cases:** `rcb_tests/public_test_cases/feature06_multipolygon.json`

```json
{
  "description": "A multi-polygon is a collection of polygons. It [a specific list of operation identifiers defined in the protocol spec]s to a type discriminator and a deeply nested array of coordinate arrays, and round-trips back to an equal value. A null polygon sequence is rejected at [a specific list of operation identifiers defined in the protocol spec]ion as a missing required argument. Multi-polygons built from equal polygons compare equal and share a hash code.",
  "cases": [
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "object": {
          "type": "MultiPolygon",
          "coordinates": [
            [
              [
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
                ],
                [
                  0,
                  1
                ],
                [
                  0,
                  0
                ]
              ]
            ],
            [
              [
                [
                  60,
                  60
                ],
                [
                  61,
                  60
                ],
                [
                  61,
                  61
                ],
                [
                  60,
                  61
                ],
                [
                  60,
                  60
                ]
              ],
              [
                [
                  70,
                  70
                ],
                [
                  70,
                  71
                ],
                [
                  71,
                  71
                ],
                [
                  71,
                  70
                ],
                [
                  70,
                  70
                ]
              ]
            ]
          ]
        },
        "formatting": "none"
      },
      "expected_output": "{\"type\":\"MultiPolygon\",\"coordinates\":[[[[0.0,0.0],[1.0,0.0],[1.0,1.0],[0.0,1.0],[0.0,0.0]]],[[[60.0,60.0],[61.0,60.0],[61.0,61.0],[60.0,61.0],[60.0,60.0]],[[70.0,70.0],[70.0,71.0],[71.0,71.0],[71.0,70.0],[70.0,70.0]]]]}\n"
    },
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "object": {
          "type": "MultiPolygon",
          "coordinates": null
        }
      },
      "expected_output": "error=argument_null\nparam=polygons\n"
    }
  ]
}
```

---

### Feature 7: Geometry Collection

**As a developer**, I want to bundle heterogeneous geometries together.

**Expected Behavior / Usage:**

A geometry collection holds any number of geometries of any kind. It [a specific list of operation identifiers defined in the protocol spec]s as a `type` of `"GeometryCollection"` and a `geometries` array of nested geometry objects (note: it has `geometries`, not `coordinates`), and is recovered by `[a specific list of operation identifiers defined in the protocol spec]`. A null member list at `[a specific list of operation identifiers defined in the protocol spec]` yields `error=argument_null` with `param=geometries`. The `[a specific list of operation identifiers defined in the protocol spec]` op gives the five-line equality contract.

**Test Cases:** `rcb_tests/public_test_cases/feature07_geometrycollection.json`

```json
{
  "description": "A geometry collection groups several geometries of any kind. It [a specific list of operation identifiers defined in the protocol spec]s to a type discriminator and an array of nested geometry objects, and round-trips back to an equal value. A null geometry sequence is rejected at [a specific list of operation identifiers defined in the protocol spec]ion as a missing required argument. Collections built from equal member geometries compare equal and share a hash code.",
  "cases": [
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "object": {
          "type": "GeometryCollection",
          "geometries": [
            {
              "type": "Point",
              "coordinates": [
                1,
                2,
                3
              ]
            },
            {
              "type": "LineString",
              "coordinates": [
                [
                  1,
                  1
                ],
                [
                  2,
                  2
                ]
              ]
            }
          ]
        },
        "formatting": "none"
      },
      "expected_output": "{\"type\":\"GeometryCollection\",\"geometries\":[{\"type\":\"Point\",\"coordinates\":[1.0,2.0,3.0]},{\"type\":\"LineString\",\"coordinates\":[[1.0,1.0],[2.0,2.0]]}]}\n"
    },
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "object": {
          "type": "GeometryCollection",
          "geometries": null
        }
      },
      "expected_output": "error=argument_null\nparam=geometries\n"
    }
  ]
}
```

---

### Feature 8: Type-Driven Geometry Conversion

**As a developer**, I want to read back a geometry of unknown kind using only its type discriminator.

**Expected Behavior / Usage:**

The `[a specific list of operation identifiers defined in the protocol spec]_equal` op with `via` of `geometry` [a specific list of operation identifiers defined in the protocol spec]s a geometry and de[a specific list of operation identifiers defined in the protocol spec]s it back through a converter that picks the concrete geometry kind purely from the `type` discriminator, then reports `equal=<bool>`. For every geometry kind this round trip re[a specific list of operation identifiers defined in the protocol spec]s an equal value.

**Test Cases:** `rcb_tests/public_test_cases/feature08_geometry_converter.json`

```json
{
  "description": "Any geometry can be [a specific list of operation identifiers defined in the protocol spec]d and then read back through a converter that selects the concrete geometry kind from the type discriminator alone. For each geometry kind, serializing and then deserializing through this type-driven converter re[a specific list of operation identifiers defined in the protocol spec]s a value equal to the original.",
  "cases": [
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]_equal",
        "via": "geometry",
        "geometry": {
          "type": "Point",
          "coordinates": [
            1,
            2,
            3
          ]
        }
      },
      "expected_output": "equal=true\n"
    }
  ]
}
```

---

### Feature 9: General GeoJSON Object Conversion

**As a developer**, I want to [a specific list of operation identifiers defined in the protocol spec] and read back any top-level GeoJSON object without naming its type up front.

**Expected Behavior / Usage:**

The `[a specific list of operation identifiers defined in the protocol spec]_equal` op with `via` of `geojson` round-trips a geometry through a general converter that dispatches on the `type` discriminator and reports `equal=<bool>`. The `[a specific list of operation identifiers defined in the protocol spec]` op with `target` of `GeoJSONObject` performs the same general parse-and-re-render. Both re[a specific list of operation identifiers defined in the protocol spec] an equal value.

**Test Cases:** `rcb_tests/public_test_cases/feature09_geojson_converter.json`

```json
{
  "description": "A general converter can [a specific list of operation identifiers defined in the protocol spec] and de[a specific list of operation identifiers defined in the protocol spec] any top-level GeoJSON object purely from its type discriminator, without the caller naming the concrete type in advance. Round-tripping a geometry through this general converter re[a specific list of operation identifiers defined in the protocol spec]s an equal value, whether the static reference type used is the common base type or the common interface.",
  "cases": [
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]_equal",
        "via": "geojson",
        "geometry": {
          "type": "Point",
          "coordinates": [
            20,
            10
          ]
        }
      },
      "expected_output": "equal=true\n"
    }
  ]
}
```

---

### Feature 10: Serialization Formatting

**As a developer**, I want to control whether [a specific list of operation identifiers defined in the protocol spec]d output is indented or compact.

**Expected Behavior / Usage:**

The `[a specific list of operation identifiers defined in the protocol spec]` op honors a `formatting` field. With `indented`, the output is pretty-printed and contains line breaks and spacing; with `none`, the output is compact and contains no line breaks and no separating whitespace. The underlying content is identical either way.

**Test Cases:** `rcb_tests/public_test_cases/feature10_serialization_formatting.json`

```json
{
  "description": "Serialization honors the formatting setting of the [a specific list of operation identifiers defined in the protocol spec]r. With indented formatting the output contains line breaks; with compact formatting the output contains neither line breaks nor whitespace separators. The same geometry content is represented either way.",
  "cases": [
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "object": {
          "type": "Point",
          "coordinates": [
            1,
            2
          ]
        },
        "formatting": "indented"
      },
      "expected_output": "{\n  \"type\": \"Point\",\n  \"coordinates\": [\n    1.0,\n    2.0\n  ]\n}\n"
    },
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "object": {
          "type": "Point",
          "coordinates": [
            1,
            2
          ]
        },
        "formatting": "none"
      },
      "expected_output": "{\"type\":\"Point\",\"coordinates\":[1.0,2.0]}\n"
    }
  ]
}
```

---

### Feature 11: Geometry as an Object Property

**As a developer**, I want to embed a geometry inside another object and restore its concrete kind on read.

**Expected Behavior / Usage:**

The `wrapper_[a specific list of operation identifiers defined in the protocol spec]` op [a specific list of operation identifiers defined in the protocol spec]s a host object that carries a geometry as a typed property and de[a specific list of operation identifiers defined in the protocol spec]s it back through a type-driven converter, reporting `equal=<bool>` and `hash_equal=<bool>`. For every geometry kind the restored host object is equal to the original and shares its hash.

**Test Cases:** `rcb_tests/public_test_cases/feature11_geometry_as_property.json`

```json
{
  "description": "A geometry can be embedded as a typed property of an arbitrary host object and [a specific list of operation identifiers defined in the protocol spec]d as part of that object, using a converter that restores the correct geometry kind on read. For each geometry kind, serializing a host object that carries the geometry and then deserializing it yields a host object that compares equal to the original and shares its hash code.",
  "cases": [
    {
      "input": {
        "op": "wrapper_[a specific list of operation identifiers defined in the protocol spec]",
        "geometry": {
          "type": "Point",
          "coordinates": [
            1,
            2,
            3
          ]
        }
      },
      "expected_output": "equal=true\nhash_equal=true\n"
    }
  ]
}
```

---

### Feature 12: Named Coordinate Reference System

**As a developer**, I want to identify a coordinate reference system by name.

**Expected Behavior / Usage:**

A named CRS identifies a system by name. The `[a specific list of operation identifiers defined in the protocol spec]` op (`kind` of `named`) emits `type=name` followed by sorted `prop.<key>=<value>` lines, here `prop.name=<name>`. When attached to a [a specific list of operation identifiers defined in the protocol spec]d object it renders as a nested object `{"properties":{"name":...},"type":"name"}`. Construction rejects a null name with `error=argument_null` (`param=name`) and an empty name with `error=argument_invalid` (`param=name`, `reason=must_be_specified`). The `[a specific list of operation identifiers defined in the protocol spec]` op (`kind` of `crs`) reports the five-line equality contract: same name equal, different name unequal.

**Test Cases:** `rcb_tests/public_test_cases/feature12_named_crs.json`

```json
{
  "description": "A named coordinate reference system identifies a CRS by name. It exposes a type marker indicating a named system and carries the name under a dedicated property key. When attached to a GeoJSON object it [a specific list of operation identifiers defined in the protocol spec]s as a nested object containing that property and the named-system type marker. Construction rejects a null name as a missing required argument and an empty name as invalid. Two named systems with the same name compare equal and share a hash code; different names compare unequal with differing hash codes.",
  "cases": [
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "crs": {
          "kind": "named",
          "name": "EPSG:31370"
        }
      },
      "expected_output": "type=name\nprop.name=EPSG:31370\n"
    },
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "object": {
          "kind": "feature_collection",
          "features": [],
          "crs": {
            "kind": "named",
            "name": "EPSG:31370"
          }
        },
        "formatting": "none"
      },
      "expected_output": "{\"type\":\"FeatureCollection\",\"features\":[],\"crs\":{\"properties\":{\"name\":\"EPSG:31370\"},\"type\":\"name\"}}\n"
    }
  ]
}
```

---

### Feature 13: Linked Coordinate Reference System

**As a developer**, I want to reference a coordinate reference system by dereferenceable URI.

**Expected Behavior / Usage:**

A linked CRS references a system by href, optionally with a link type. The `[a specific list of operation identifiers defined in the protocol spec]` op (`kind` of `linked`) emits `type=link` then sorted `prop.<key>=<value>` lines (`prop.href`, and `prop.type` when supplied). When attached to a [a specific list of operation identifiers defined in the protocol spec]d object it renders as `{"properties":{"href":...},"type":"link"}` and is recovered by `[a specific list of operation identifiers defined in the protocol spec]`. Construction rejects a null href with `error=argument_null` (`param=href`); an empty href, or an href that is not a dereferenceable URI, with `error=argument_invalid` (`param=href`, `reason=[a specific validation rule describing acceptable URI formats]`); a relative reference is accepted. The `[a specific list of operation identifiers defined in the protocol spec]` op gives the five-line contract: same href equal, different href unequal.

**Test Cases:** `rcb_tests/public_test_cases/feature13_linked_crs.json`

```json
{
  "description": "A linked coordinate reference system references a CRS by dereferenceable URI, optionally with a link type. It exposes a type marker indicating a linked system and carries the href, and the optional type, under dedicated property keys. When attached to a GeoJSON object it [a specific list of operation identifiers defined in the protocol spec]s as a nested object and is read back from that same shape. Construction rejects a null href as a missing required argument, an empty href as invalid, and an href that is not a dereferenceable URI as invalid; a relative reference is accepted. Two linked systems with the same href compare equal and share a hash code; different hrefs compare unequal.",
  "cases": [
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "crs": {
          "kind": "linked",
          "href": "http://localhost"
        }
      },
      "expected_output": "type=link\nprop.href=http://localhost\n"
    },
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "crs": {
          "kind": "linked",
          "href": "http://localhost",
          "type": "ogcwkt"
        }
      },
      "expected_output": "type=link\nprop.href=http://localhost\nprop.type=ogcwkt\n"
    },
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "crs": {
          "kind": "linked",
          "href": "http://not-a-valid-<>-url"
        }
      },
      "expected_output": "error=argument_invalid\nparam=href\nreason=[a specific validation rule describing acceptable URI formats]\n"
    }
  ]
}
```

---

### Feature 14: Unspecified Coordinate Reference System

**As a developer**, I want to represent the explicit absence of a coordinate reference system.

**Expected Behavior / Usage:**

An unspecified CRS marks the deliberate absence of a system. When attached to a collection and [a specific list of operation identifiers defined in the protocol spec]d, its CRS member renders as JSON `null`; reading a collection whose CRS member is `null` yields an unspecified CRS. Two unspecified CRS values always compare equal and share a hash (`[a specific list of operation identifiers defined in the protocol spec]` op, `kind` of `crs`).

**Test Cases:** `rcb_tests/public_test_cases/feature14_unspecified_crs.json`

```json
{
  "description": "An unspecified coordinate reference system represents the explicit absence of a CRS. It exposes a type marker indicating an unspecified system. When attached to a collection it [a specific list of operation identifiers defined in the protocol spec]s as a null CRS member, and reading a collection whose CRS member is null produces an unspecified system. Two unspecified systems always compare equal and share a hash code.",
  "cases": [
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "object": {
          "kind": "feature_collection",
          "features": [],
          "crs": {
            "kind": "unspecified"
          }
        },
        "formatting": "none"
      },
      "expected_output": "{\"type\":\"FeatureCollection\",\"features\":[],\"crs\":null}\n"
    },
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "kind": "crs",
        "left": {
          "kind": "unspecified"
        },
        "right": {
          "kind": "unspecified"
        }
      },
      "expected_output": "[a specific list of operation identifiers defined in the protocol spec]=true\n[a specific list of operation identifiers defined in the protocol spec]_reverse=true\nop_[a specific list of operation identifiers defined in the protocol spec]=true\nop_not_[a specific list of operation identifiers defined in the protocol spec]=false\nhash_equal=true\n"
    }
  ]
}
```

---

### Feature 15: Default CRS Handling

**As a developer**, I want to omit the CRS when none is set and faithfully carry one when present.

**Expected Behavior / Usage:**

When no CRS is supplied, a [a specific list of operation identifiers defined in the protocol spec]d object omits the CRS member entirely, and an object parsed from text without a CRS member carries no CRS (its `[a specific list of operation identifiers defined in the protocol spec]` output likewise has no CRS member). When a named CRS is present on a geometry it is [a specific list of operation identifiers defined in the protocol spec]d after the coordinates as a nested named-system object and restored on read. The well-known default geographic CRS is simply a named CRS carrying its canonical name string.

**Test Cases:** `rcb_tests/public_test_cases/feature15_default_crs.json`

```json
{
  "description": "When no CRS is supplied, a GeoJSON object omits the CRS member entirely on serialization, and an object read from text that has no CRS member carries no CRS. When a named CRS is present on a geometry, it is [a specific list of operation identifiers defined in the protocol spec]d after the coordinates as a nested named-system object and is restored on read. The well-known default geographic CRS is just a named system carrying its canonical name.",
  "cases": [
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "object": {
          "kind": "feature_collection",
          "features": []
        },
        "formatting": "none"
      },
      "expected_output": "{\"type\":\"FeatureCollection\",\"features\":[]}\n"
    },
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "object": {
          "type": "Point",
          "coordinates": [
            34.56,
            12.34
          ],
          "crs": {
            "kind": "named",
            "name": "TEST NAME"
          }
        },
        "formatting": "none"
      },
      "expected_output": "{\"type\":\"Point\",\"coordinates\":[34.56,12.34],\"crs\":{\"properties\":{\"name\":\"TEST NAME\"},\"type\":\"name\"}}\n"
    }
  ]
}
```

---

### Feature 16: Feature Serialization

**As a developer**, I want to [a specific list of operation identifiers defined in the protocol spec] a geometry together with its identity and attributes.

**Expected Behavior / Usage:**

A feature wraps one geometry with an optional identifier and a property bag. The `[a specific list of operation identifiers defined in the protocol spec]` op (`kind` of `feature`) renders a `type` of `"Feature"`, the optional `id`, the nested `geometry`, and a `properties` object. Each geometry kind [a specific list of operation identifiers defined in the protocol spec]s to its corresponding nested shape; a feature given no properties [a specific list of operation identifiers defined in the protocol spec]s with an empty `properties` object.

**Test Cases:** `rcb_tests/public_test_cases/feature16_feature_[a specific list of operation identifiers defined in the protocol spec].json`

```json
{
  "description": "A feature wraps a single geometry together with an optional identifier and a property bag. Serializing a feature produces a type discriminator, the optional identifier, the nested geometry, and the properties object. Features carrying each kind of geometry [a specific list of operation identifiers defined in the protocol spec] to the corresponding nested geometry shape; a feature with no supplied properties [a specific list of operation identifiers defined in the protocol spec]s with an empty properties object.",
  "cases": [
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "object": {
          "kind": "feature",
          "geometry": {
            "type": "Point",
            "coordinates": [
              2,
              1
            ]
          }
        },
        "formatting": "none"
      },
      "expected_output": "{\"type\":\"Feature\",\"geometry\":{\"type\":\"Point\",\"coordinates\":[2.0,1.0]},\"properties\":{}}\n"
    }
  ]
}
```

---

### Feature 17: Feature Deserialization

**As a developer**, I want to re[a specific list of operation identifiers defined in the protocol spec] a feature's geometry, identity, and attributes from text.

**Expected Behavior / Usage:**

The `[a specific list of operation identifiers defined in the protocol spec]` op (`target` of `Feature`) parses a feature and re-renders it canonically. A feature with properties keeps them; a feature without properties yields an empty property bag; a feature whose `geometry` member is `null`, or absent entirely, yields a feature with no geometry.

**Test Cases:** `rcb_tests/public_test_cases/feature17_feature_de[a specific list of operation identifiers defined in the protocol spec].json`

```json
{
  "description": "Reading a feature re[a specific list of operation identifiers defined in the protocol spec]s its geometry, identifier, and properties from text and re-emits them in canonical form. A feature with properties keeps them; a feature without properties yields an empty property bag; a feature whose geometry member is null, or absent entirely, yields a feature with no geometry.",
  "cases": [
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "target": "Feature",
        "wire": "{\"type\":\"Feature\",\"id\":\"test-id\",\"geometry\":{\"type\":\"Point\",\"coordinates\":[125.6,10.1]},\"properties\":{\"name\":\"Dinagat Islands\"}}"
      },
      "expected_output": "{\"type\":\"Feature\",\"id\":\"test-id\",\"geometry\":{\"type\":\"Point\",\"coordinates\":[125.6,10.1]},\"properties\":{\"name\":\"Dinagat Islands\"}}\n"
    }
  ]
}
```

---

### Feature 18: Feature Properties

**As a developer**, I want to attach arbitrary key/value attributes to a feature.

**Expected Behavior / Usage:**

A feature's property bag carries arbitrary key/value pairs through to serialization. When no property object is supplied the feature still exposes an empty property bag rather than a missing one (its [a specific list of operation identifiers defined in the protocol spec]d `properties` is `{}`).

**Test Cases:** `rcb_tests/public_test_cases/feature18_feature_properties.json`

```json
{
  "description": "A feature's property bag can be supplied as a set of key/value pairs, which are carried through to serialization. When no property object is supplied, the feature still exposes an empty property bag rather than a missing one.",
  "cases": [
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "object": {
          "kind": "feature",
          "geometry": {
            "type": "Point",
            "coordinates": [
              10,
              10
            ]
          },
          "properties": {
            "StringProperty": "Hello, GeoJSON !",
            "IntProperty": -1,
            "BooleanProperty": true
          }
        },
        "formatting": "none"
      },
      "expected_output": "{\"type\":\"Feature\",\"geometry\":{\"type\":\"Point\",\"coordinates\":[10.0,10.0]},\"properties\":{\"StringProperty\":\"Hello, GeoJSON !\",\"IntProperty\":-1,\"BooleanProperty\":true}}\n"
    }
  ]
}
```

---

### Feature 19: Feature Equality

**As a developer**, I want to compare features by the geometry they carry, safely against null.

**Expected Behavior / Usage:**

Feature equality is determined solely by the wrapped geometry: features with equal geometries are equal even when their identifiers or properties differ, and features with differing geometries are unequal (`[a specific list of operation identifiers defined in the protocol spec]` op, `kind` of `feature`, five-line contract). Comparing a feature to a null operand (a `null` left/right value) never throws and reports not-equal; two features that both have no geometry are equal; a feature with a geometry versus one without are unequal. When a hash code cannot be computed (a feature with no geometry), the `hash_equal` line reports `na`.

**Test Cases:** `rcb_tests/public_test_cases/feature19_feature_equality.json`

```json
{
  "description": "Feature equality is determined solely by the wrapped geometry: features with equal geometries are equal even when their identifiers or properties differ, and features with differing geometries are unequal. Comparing a feature to a null reference is well-defined and never throws, returning not-equal; two features that both have no geometry are equal; a feature with a geometry and one without are unequal.",
  "cases": [
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "kind": "feature",
        "left": {
          "geometry": {
            "type": "Point",
            "coordinates": [
              10,
              10
            ]
          },
          "id": "abc",
          "properties": {
            "a": 1
          }
        },
        "right": {
          "geometry": {
            "type": "Point",
            "coordinates": [
              10,
              10
            ]
          },
          "id": "xyz",
          "properties": {
            "b": 2
          }
        }
      },
      "expected_output": "[a specific list of operation identifiers defined in the protocol spec]=true\n[a specific list of operation identifiers defined in the protocol spec]_reverse=true\nop_[a specific list of operation identifiers defined in the protocol spec]=true\nop_not_[a specific list of operation identifiers defined in the protocol spec]=false\nhash_equal=true\n"
    },
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "kind": "feature",
        "left": {
          "geometry": {
            "type": "Point",
            "coordinates": [
              123,
              12
            ]
          }
        },
        "right": null
      },
      "expected_output": "[a specific list of operation identifiers defined in the protocol spec]=false\n[a specific list of operation identifiers defined in the protocol spec]_reverse=false\nop_[a specific list of operation identifiers defined in the protocol spec]=false\nop_not_[a specific list of operation identifiers defined in the protocol spec]=true\nhash_equal=na\n"
    }
  ]
}
```

---

### Feature 20: Typed and Generic Features

**As a developer**, I want to read or write a feature against a known geometry type or a strongly typed attribute shape.

**Expected Behavior / Usage:**

A feature can be parsed against a specific geometry type or a strongly typed property object instead of the open property bag. The `[a specific list of operation identifiers defined in the protocol spec]` op with `target` of `FeaturePoint`, `FeatureLineString`, or `FeatureTypedPoint` parses accordingly and re-renders canonically; the `typed_feature_[a specific list of operation identifiers defined in the protocol spec]` op [a specific list of operation identifiers defined in the protocol spec]s a feature whose properties are a typed object exposing a `name` and a `value` member. Comparing such a feature to a null operand reports not-equal without throwing.

**Test Cases:** `rcb_tests/public_test_cases/feature20_generic_feature.json`

```json
{
  "description": "A feature can be read against a known geometry type or a known strongly typed property shape, instead of the open property bag. Reading against a specific geometry type or a typed property object re[a specific list of operation identifiers defined in the protocol spec]s the feature and re-emits it canonically; serializing a feature with a typed property object emits those named properties. Comparing such a typed feature to a null reference is well-defined and returns not-equal.",
  "cases": [
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "target": "FeaturePoint",
        "wire": "{\"type\":\"Feature\",\"id\":\"test-id\",\"geometry\":{\"type\":\"Point\",\"coordinates\":[125.6,10.1,456]},\"properties\":{\"name\":\"Dinagat Islands\"}}"
      },
      "expected_output": "{\"type\":\"Feature\",\"id\":\"test-id\",\"geometry\":{\"type\":\"Point\",\"coordinates\":[125.6,10.1,456.0]},\"properties\":{\"name\":\"Dinagat Islands\"}}\n"
    },
    {
      "input": {
        "op": "typed_feature_[a specific list of operation identifiers defined in the protocol spec]",
        "geometry": {
          "type": "Point",
          "coordinates": [
            2,
            1
          ]
        },
        "name": "no name here",
        "value": 1.337,
        "id": "no id there"
      },
      "expected_output": "{\"type\":\"Feature\",\"id\":\"no id there\",\"geometry\":{\"type\":\"Point\",\"coordinates\":[2.0,1.0]},\"properties\":{\"name\":\"no name here\",\"value\":1.337}}\n"
    }
  ]
}
```

---

### Feature 21: Feature Collection

**As a developer**, I want to group any number of features as one document.

**Expected Behavior / Usage:**

A feature collection holds any number of features. The `[a specific list of operation identifiers defined in the protocol spec]` op (`target` of `FeatureCollection`) parses it and re-renders each feature, including each member geometry's kind; with `target` of `FeatureCollectionGeneric` each feature's properties are parsed against a strongly typed object. A null feature list at `[a specific list of operation identifiers defined in the protocol spec]` yields `error=argument_null` with `param=features`. The `[a specific list of operation identifiers defined in the protocol spec]` op (`kind` of `feature_collection`) gives the five-line contract.

**Test Cases:** `rcb_tests/public_test_cases/feature21_feature_collection.json`

```json
{
  "description": "A feature collection groups any number of features. It [a specific list of operation identifiers defined in the protocol spec]s to a type discriminator and an array of features, and reading a collection re[a specific list of operation identifiers defined in the protocol spec]s every feature, including the kind of each member geometry; a collection may also be read against a strongly typed property shape applied to each feature. A null feature list is rejected at [a specific list of operation identifiers defined in the protocol spec]ion as a missing required argument. Collections built from equal features compare equal and share a hash code.",
  "cases": [
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "target": "FeatureCollection",
        "wire": "{\"type\":\"FeatureCollection\",\"features\":[{\"type\":\"Feature\",\"geometry\":{\"type\":\"Point\",\"coordinates\":[102.0,0.5]},\"properties\":{\"prop0\":\"value0\"}},{\"type\":\"Feature\",\"properties\":{\"name\":\"DD\"},\"geometry\":{\"type\":\"MultiPolygon\",\"coordinates\":[[[[-3.124469107867639,56.43179349026641],[-3.181864056758185,56.50435867827879],[-3.080807472497396,56.58041883184697],[-3.204635351704243,56.66878970099241],[-3.153385207792676,56.750141153246226],[-3.300369428804113,56.8589226202768],[-3.20971234483721,56.947300739465064],[-3.064462793503021,56.91976858406769],[-2.972112587880359,56.97746168167823],[-2.854882511931398,56.98360267279684],[-2.680251743133697,56.945352112881636],[-2.615357138064907,56.78566372854147],[-2.493780338741513,56.76540172907848],[-2.315459650038894,56.87577071411662],[-2.224180437247053,56.88745481725907],[-2.309193985939006,56.80497206404891],[-2.410860986028102,56.768333064132314],[-2.551721986204847,56.560417064546556],[-2.719166986355991,56.49336106469278],[-3.124469107867639,56.43179349026641]]],[[[-2.818223720652239,56.423668560365314],[-2.975782222542367,56.380750980197035],[-3.063948244048636,56.392897691447075],[-2.921693986527472,56.452056064793695],[-2.818223720652239,56.423668560365314]]]]}},{\"type\":\"Feature\",\"geometry\":{\"type\":\"Polygon\",\"coordinates\":[[[100.0,0.0],[101.0,0.0],[101.0,1.0],[100.0,1.0],[100.0,0.0]]]},\"properties\":{\"prop0\":\"value0\",\"prop1\":{\"this\":\"that\"}}}]}"
      },
      "expected_output": "{\"type\":\"FeatureCollection\",\"features\":[{\"type\":\"Feature\",\"geometry\":{\"type\":\"Point\",\"coordinates\":[102.0,0.5]},\"properties\":{\"prop0\":\"value0\"}},{\"type\":\"Feature\",\"geometry\":{\"type\":\"MultiPolygon\",\"coordinates\":[[[[-3.124469107867639,56.43179349026641],[-3.181864056758185,56.50435867827879],[-3.080807472497396,56.58041883184697],[-3.204635351704243,56.66878970099241],[-3.153385207792676,56.750141153246226],[-3.300369428804113,56.8589226202768],[-3.20971234483721,56.947300739465064],[-3.064462793503021,56.91976858406769],[-2.972112587880359,56.97746168167823],[-2.854882511931398,56.98360267279684],[-2.680251743133697,56.945352112881636],[-2.615357138064907,56.78566372854147],[-2.493780338741513,56.76540172907848],[-2.315459650038894,56.87577071411662],[-2.224180437247053,56.88745481725907],[-2.309193985939006,56.80497206404891],[-2.410860986028102,56.768333064132314],[-2.551721986204847,56.560417064546556],[-2.719166986355991,56.49336106469278],[-3.124469107867639,56.43179349026641]]],[[[-2.818223720652239,56.423668560365314],[-2.975782222542367,56.380750980197035],[-3.063948244048636,56.392897691447075],[-2.921693986527472,56.452056064793695],[-2.818223720652239,56.423668560365314]]]]},\"properties\":{\"name\":\"DD\"}},{\"type\":\"Feature\",\"geometry\":{\"type\":\"Polygon\",\"coordinates\":[[[100.0,0.0],[101.0,0.0],[101.0,1.0],[100.0,1.0],[100.0,0.0]]]},\"properties\":{\"prop0\":\"value0\",\"prop1\":{\"this\":\"that\"}}}]}\n"
    },
    {
      "input": {
        "op": "[a specific list of operation identifiers defined in the protocol spec]",
        "object": {
          "kind": "feature_collection",
          "features": null
        }
      },
      "expected_output": "error=argument_null\nparam=features\n"
    }
  ]
}
```

---


## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the geometry/feature/CRS object model, [a specific list of operation identifiers defined in the protocol spec]ion-time validation, value equality and hashing, and the format converters described above.

2. **The Execution/Test Adapter:** A runnable program that reads one JSON command from stdin, invokes the core domain, and prints the result to stdout exactly matching the per-feature contracts. It must be separated from the core domain and must perform the error-normalization rendering.

3. **Automated test harness:** A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `test_cases`, with the PRD-embedded examples under `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{stem}@{index:03}.txt` containing only the raw stdout of the program under test, so it can be byte-compared against `expected_output`.


---
**Implementation notes:**
- match the comparison logic used for content-addressed files
- implement the same transparent link resolution as the HTTP client's redirect handler
