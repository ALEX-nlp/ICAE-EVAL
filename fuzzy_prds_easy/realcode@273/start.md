## Product Requirement Document

# Drawing-Interchange Toolkit - Read, Build, and Serialize 2D/3D CAD Drawings

## Project Goal

Build a library and a thin command surface that reads, constructs, and re-serializes vector CAD drawings expressed in the industry-standard drawing-interchange format. Developers should be able to inspect a drawing's strongly-typed contents (entities, layers, viewports, text styles, blocks, class registrations, header settings, thumbnails) and to author and emit new drawings — all without hand-parsing the verbose group-code wire format or tracking its many version-specific quirks.

---

## Background & Problem

The drawing-interchange format encodes a CAD document as a flat stream of "group-code / value" line pairs grouped into sections (header, classes, tables, blocks, entities, thumbnail). The same logical drawing can be written in several on-disk dialects keyed to a target product version, in a text encoding or one of two binary encodings, and with locale-sensitive number formatting. Numeric fields appear in assorted notations, some booleans are stored under the "wrong" group code, and a byte-order mark may precede the text stream.

Without a library, developers must reimplement all of this by hand for every project: tracking which group code maps to which property of which entity, emitting exactly the right subclass markers and freshly assigned handles, gating sections and properties by target version, and normalizing numeric/locale differences. This is repetitive, error-prone, and brittle.

With this toolkit, a developer loads a drawing from a stream (encoding auto-detected), reads strongly-typed entities/tables/header values, builds new drawings from typed objects, and serializes them back to a chosen target version — the library owns all of the group-code bookkeeping, version gating, and locale-independent formatting.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a substantial domain (many entity types, several sections and tables, two binary encodings, version gating). It MUST NOT be a single "god file". Provide a clear multi-file tree separating the core model (entities, tables, sections, header), the readers/writers (text + binary encodings), and the execution adapter. Do not over-engineer trivial helpers, but the core library must read like a production repository.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below form a **black-box contract for the execution adapter only**, not for the internal data model. The core library must expose idiomatic typed objects and must not know about JSON or stdout. The adapter alone translates a JSON command into core calls and renders the result text.

3. **Adherence to SOLID Design Principles:** Separate parsing, routing, validation, core execution, and output formatting. The reader/writer pipeline must be open for extension (new entity types, new target versions) but closed for modification of existing ones; entity types must be substitutable through a common entity abstraction; high-level serialization must depend on abstractions rather than concrete stream details.

4. **Robustness & Interface Design:** The public interface must be idiomatic to the implementation language and hide group-code bookkeeping. Edge cases (missing fields defaulting correctly, byte-order marks, locale-sensitive numbers, alternate boolean encodings, unsupported requests) must be handled gracefully and modeled with proper error types rather than generic faults.

---

## Execution Adapter Contract (How the cases are driven)

The execution adapter reads exactly one JSON value from stdin (the case `input`) and writes raw text to stdout (the case `expected_output`). A well-formed command is a JSON object carrying an `op` field naming the requested operation; the remaining fields are operation arguments.

Drawing payloads are supplied one of two ways:

- A `dxf` field holds drawing text as a string of group-code / value lines separated by `\n`. For operations that focus on one section/table, the value holds the records that go *inside* that section (the adapter wraps them); for whole-document operations the value is a complete document.
- A `data` field holds a complete stream as base64 (used for the binary encodings and the byte-order-mark case).

A target product version may be requested with a `version` field whose value is one of the symbolic version tags `R10`–`R2013`. An optional `locale` field installs a host regional setting before parsing, used to prove locale-independence.

Two output styles are used, chosen to make the relevant behavior observable:

- **Typed reads** parse the payload and emit one `key=value` line per parsed property, so parsing behavior is observable independently of re-serialization. Geometry is rendered as `x,y,z`; booleans as `true`/`false`; binary blobs as lowercase hex.
- **Wire-format writes** build a drawing in memory and emit the exact serialized section/table the library produces (group-code / value lines), which is the externally observable wire format. The serializer assigns fresh handles and emits canonical subclass markers and ordering for the target version.

All multi-line output uses `\n` line endings. Errors are rendered as a neutral category contract (see Feature 11) and never leak host-runtime fault text.

---

## Core Features

### Feature 1: Entity Geometry

Read and build the common drawing entities with correct default values, so geometry can be inspected or authored without memorizing per-entity group codes. Reading a single entity record (`op: "read_entity"`) reports the parsed typed properties; building one (`op: "write_entity"` with an `entity` object) emits the canonical ENTITIES section the serializer produces. Omitted fields take documented defaults.

*1.1 Line — two endpoints with optional thickness and extrusion*

A line is defined by a start point `p1`, an end point `p2`, an optional `thickness`, and an optional `extrusion` direction (default `[0,0,1]`). On read, missing coordinates default to the origin. On build, common properties (`handle`, `layer`, `color_index`, `thickness`, `extrusion`) are honored and the canonical line section is emitted.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_line.json`

```json
{
    "description": "Parse and emit a straight line segment. A line is defined by two endpoints (start P1, end P2), an optional thickness and an optional extrusion direction vector. Omitted coordinates default to the origin and the extrusion direction defaults to the +Z unit vector. Reading reports the parsed typed values; writing emits the canonical entities section the library produces.",
    "cases": [
        {
            "input": {
                "op": "read_entity",
                "dxf": "  0\nLINE\n"
            },
            "expected_output": "type=line\nlayer=0\nlinetype=BYLAYER\nlinetype_scale=1\nis_visible=true\nis_in_paper_space=false\ncolor=BYLAYER\np1=0,0,0\np2=0,0,0\nthickness=0\nextrusion=0,0,1\n"
        },
        {
            "input": {
                "op": "read_entity",
                "dxf": "  0\nLINE\n 10\n1.1\n 20\n2.2\n 30\n3.3\n 11\n4.4\n 21\n5.5\n 31\n6.6\n 39\n7.7\n210\n8.8\n220\n9.9\n230\n10.1\n"
            },
            "expected_output": "type=line\nlayer=0\nlinetype=BYLAYER\nlinetype_scale=1\nis_visible=true\nis_in_paper_space=false\ncolor=BYLAYER\np1=1.1,2.2,3.3\np2=4.4,5.5,6.6\nthickness=7.7\nextrusion=8.8,9.9,10.1\n"
        },
        {
            "input": {
                "op": "write_entity",
                "entity": {
                    "type": "line",
                    "p1": [
                        1,
                        2,
                        3
                    ],
                    "p2": [
                        4,
                        5,
                        6
                    ],
                    "color_index": 7,
                    "handle": 66,
                    "layer": "bar",
                    "thickness": 7,
                    "extrusion": [
                        8,
                        9,
                        10
                    ]
                }
            },
            "expected_output": "  0\nSECTION\n  2\nENTITIES\n  0\nLINE\n  5\n42\n100\nAcDbEntity\n  8\nbar\n 62\n7\n100\nAcDbLine\n 39\n7.0\n 10\n1.0\n 20\n2.0\n 30\n3.0\n 11\n4.0\n 21\n5.0\n 31\n6.0\n210\n8.0\n220\n9.0\n230\n10.0\n  0\nENDSEC\n"
        }
    ]
}
```

*1.2 Circle — center, radius, optional thickness and normal*

A circle is defined by a `center`, a `radius`, an optional `thickness`, and a normal/extrusion vector (default `[0,0,1]`). A bare record defaults all numbers to zero except the normal Z which is 1.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_circle.json`

```json
{
    "description": "Parse and emit a circle. A circle is defined by a center point, a radius, an optional thickness, and a normal (extrusion) vector that defaults to +Z. Omitted values default to zero except the normal.",
    "cases": [
        {
            "input": {
                "op": "read_entity",
                "dxf": "  0\nCIRCLE\n"
            },
            "expected_output": "type=circle\nlayer=0\nlinetype=BYLAYER\nlinetype_scale=1\nis_visible=true\nis_in_paper_space=false\ncolor=BYLAYER\ncenter=0,0,0\nradius=0\nnormal=0,0,1\nthickness=0\n"
        },
        {
            "input": {
                "op": "read_entity",
                "dxf": "  0\nCIRCLE\n 10\n11\n 20\n22\n 30\n33\n 40\n44\n 39\n35\n210\n55\n220\n66\n230\n77\n"
            },
            "expected_output": "type=circle\nlayer=0\nlinetype=BYLAYER\nlinetype_scale=1\nis_visible=true\nis_in_paper_space=false\ncolor=BYLAYER\ncenter=11,22,33\nradius=44\nnormal=55,66,77\nthickness=35\n"
        }
    ]
}
```

*1.3 Arc — a circle plus start/end angles*

An arc adds a `start_angle` and an `end_angle` in degrees to the circle definition. When omitted the start angle defaults to 0 and the end angle defaults to 360.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_arc.json`

```json
{
    "description": "Parse and emit a circular arc. An arc extends a circle with a start angle and an end angle in degrees. When omitted, the start angle defaults to 0 and the end angle defaults to 360.",
    "cases": [
        {
            "input": {
                "op": "read_entity",
                "dxf": "  0\nARC\n"
            },
            "expected_output": "type=arc\nlayer=0\nlinetype=BYLAYER\nlinetype_scale=1\nis_visible=true\nis_in_paper_space=false\ncolor=BYLAYER\ncenter=0,0,0\nradius=0\nnormal=0,0,1\nthickness=0\n"
        },
        {
            "input": {
                "op": "read_entity",
                "dxf": "  0\nARC\n 10\n11\n 20\n22\n 30\n33\n 40\n44\n 50\n88\n 51\n99\n 39\n35\n"
            },
            "expected_output": "type=arc\nlayer=0\nlinetype=BYLAYER\nlinetype_scale=1\nis_visible=true\nis_in_paper_space=false\ncolor=BYLAYER\ncenter=11,22,33\nradius=44\nnormal=0,0,1\nthickness=35\n"
        }
    ]
}
```

*1.4 Ellipse — center, major axis, axis ratio, parameter sweep*

An ellipse is defined by a center, a major-axis endpoint (default +X), a minor-to-major axis ratio (default 1.0), and a start/end parameter sweep (default 0 to 2*pi). The full-sweep end parameter is the numeric value of two pi.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_ellipse.json`

```json
{
    "description": "Parse and emit an ellipse. An ellipse is defined by a center, a major-axis endpoint (default +X), a minor-to-major axis ratio (default 1.0), and a start/end parameter sweep (default 0 to 2*pi).",
    "cases": [
        {
            "input": {
                "op": "read_entity",
                "dxf": "  0\nELLIPSE\n"
            },
            "expected_output": "type=ellipse\nlayer=0\nlinetype=BYLAYER\nlinetype_scale=1\nis_visible=true\nis_in_paper_space=false\ncolor=BYLAYER\ncenter=0,0,0\nmajor_axis=1,0,0\nnormal=0,0,1\nminor_axis_ratio=1\nstart_parameter=0\nend_parameter=6.2831853071795862\n"
        },
        {
            "input": {
                "op": "write_entity",
                "entity": {
                    "type": "ellipse"
                }
            },
            "expected_output": "  0\nSECTION\n  2\nENTITIES\n  0\nELLIPSE\n  5\nA\n100\nAcDbEntity\n  8\n0\n100\nAcDbEllipse\n 10\n0.0\n 20\n0.0\n 30\n0.0\n 11\n1.0\n 21\n0.0\n 31\n0.0\n 40\n1.0\n 41\n0.0\n 42\n6.28318530717959\n  0\nENDSEC\n"
        }
    ]
}
```

*1.5 Text — string value with placement and justification*

A text entity carries a string value, an insertion location, a height, a style name, rotation, oblique angle, backward/upside-down flags, and horizontal/vertical justification codes. Caret-encoded control characters in the stored string are decoded on read and reported with explicit escapes.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_text.json`

```json
{
    "description": "Parse and emit a single-line text entity. Text carries a string value, an insertion point, a height, a style name, rotation, oblique angle, backward/upside-down flags, and horizontal/vertical justification codes. Caret-encoded control characters in the stored string are decoded on read and reported with explicit escapes.",
    "cases": [
        {
            "input": {
                "op": "read_entity",
                "dxf": "  0\nTEXT\n"
            },
            "expected_output": "type=text\nlayer=0\nlinetype=BYLAYER\nlinetype_scale=1\nis_visible=true\nis_in_paper_space=false\ncolor=BYLAYER\nvalue=null\ntext_style_name=STANDARD\nlocation=0,0,0\nthickness=0\ntext_height=1\nrelative_x_scale=1\nrotation=0\noblique_angle=0\nis_text_backward=false\nis_text_upside_down=false\nhorizontal_justification=Left\nvertical_justification=Baseline\nsecond_alignment_point=0,0,0\nnormal=0,0,1\n"
        },
        {
            "input": {
                "op": "read_entity",
                "dxf": "  0\nTEXT\n  1\nfoo bar\n  7\ntext style name\n 10\n11\n 20\n22\n 30\n33\n 40\n44\n 50\n55\n 71\n255\n 72\n3\n 73\n1\n"
            },
            "expected_output": "type=text\nlayer=0\nlinetype=BYLAYER\nlinetype_scale=1\nis_visible=true\nis_in_paper_space=false\ncolor=BYLAYER\nvalue=foo bar\ntext_style_name=text style name\nlocation=11,22,33\nthickness=0\ntext_height=44\nrelative_x_scale=1\nrotation=55\noblique_angle=0\nis_text_backward=true\nis_text_upside_down=true\nhorizontal_justification=Aligned\nvertical_justification=Bottom\nsecond_alignment_point=0,0,0\nnormal=0,0,1\n"
        },
        {
            "input": {
                "op": "read_entity",
                "dxf": "  0\nTEXT\n  1\na^G^ ^^ b\n"
            },
            "expected_output": "type=text\nlayer=0\nlinetype=BYLAYER\nlinetype_scale=1\nis_visible=true\nis_in_paper_space=false\ncolor=BYLAYER\nvalue=a\\x07^\\x1E b\ntext_style_name=STANDARD\nlocation=0,0,0\nthickness=0\ntext_height=1\nrelative_x_scale=1\nrotation=0\noblique_angle=0\nis_text_backward=false\nis_text_upside_down=false\nhorizontal_justification=Left\nvertical_justification=Baseline\nsecond_alignment_point=0,0,0\nnormal=0,0,1\n"
        }
    ]
}
```

*1.6 Polyline & Vertex — an ownership chain of vertices*

A polyline owns an ordered sequence of vertex sub-entities terminated by a sequence-end marker; each vertex carries its own location and reading the polyline reports its vertex list. A standalone vertex record carries location, widths, bulge, and flag/index fields. Building a polyline for a newer target emits the owned records with freshly assigned handles.

**Test Cases:** `rcb_tests/public_test_cases/feature1_6_polyline.json`

```json
{
    "description": "Parse and emit a polyline together with its vertex list. A polyline owns an ordered sequence of vertex sub-entities terminated by a sequence-end marker; each vertex carries its own location. A standalone vertex record carries location, widths, bulge, and flag/index fields.",
    "cases": [
        {
            "input": {
                "op": "read_entity",
                "dxf": "  0\nPOLYLINE\n 70\n0\n  0\nVERTEX\n 10\n12\n 20\n23\n 30\n34\n  0\nVERTEX\n 10\n45\n 20\n56\n 30\n67\n  0\nSEQEND\n"
            },
            "expected_output": "type=polyline\nlayer=0\nlinetype=BYLAYER\nlinetype_scale=1\nis_visible=true\nis_in_paper_space=false\ncolor=BYLAYER\nelevation=0\nnormal=0,0,1\nthickness=0\ndefault_starting_width=0\ndefault_ending_width=0\npolygon_mesh_m_count=0\npolygon_mesh_n_count=0\nsmooth_surface_m_density=0\nsmooth_surface_n_density=0\nsurface_type=None\nis_closed=false\ncurve_fit_added=false\nspline_fit_added=false\nis_3d_polyline=false\nis_3d_polygon_mesh=false\nis_polygon_mesh_closed_n=false\nis_polyface_mesh=false\nis_linetype_continuous=false\nvertex_count=2\nvertex.0.location=12,23,34\nvertex.1.location=45,56,67\n"
        },
        {
            "input": {
                "op": "read_entity",
                "dxf": "  0\nVERTEX\n 10\n11\n 20\n22\n 30\n33\n 40\n40\n 41\n41\n 42\n42\n 50\n50\n 70\n255\n 71\n71\n 72\n72\n 73\n73\n 74\n74\n"
            },
            "expected_output": "type=vertex\nlayer=0\nlinetype=BYLAYER\nlinetype_scale=1\nis_visible=true\nis_in_paper_space=false\ncolor=BYLAYER\nlocation=11,22,33\nstarting_width=40\nending_width=41\nbulge=42\nis_extra_created_by_curve_fit=true\nis_curve_fit_tangent_defined=true\nis_spline_vertex_created_by_spline_fitting=true\nis_spline_frame_control_point=true\nis_3d_polyline_vertex=true\nis_3d_polygon_mesh=true\nis_polyface_mesh_vertex=true\ncurve_fit_tangent_direction=50\npolyface_index_1=71\npolyface_index_2=72\npolyface_index_3=73\npolyface_index_4=74\n"
        },
        {
            "input": {
                "op": "write_entity",
                "version": "R2000",
                "entity": {
                    "type": "polyline",
                    "vertex_count": 2
                }
            },
            "expected_output": "  0\nSECTION\n  2\nENTITIES\n  0\nPOLYLINE\n  5\nA\n330\n0\n100\nAcDbEntity\n  8\n0\n370\n0\n100\nAcDb2dPolyline\n 10\n0.0\n 20\n0.0\n 30\n0.0\n  0\nVERTEX\n  5\nB\n330\nA\n100\nAcDbEntity\n  8\n0\n370\n0\n100\nAcDbVertex\n 10\n0.0\n 20\n0.0\n 30\n0.0\n 70\n0\n 50\n0.0\n  0\nVERTEX\n  5\nC\n330\nA\n100\nAcDbEntity\n  8\n0\n370\n0\n100\nAcDbVertex\n 10\n0.0\n 20\n0.0\n 30\n0.0\n 70\n0\n 50\n0.0\n  0\nSEQEND\n  5\nD\n330\nA\n100\nAcDbEntity\n  8\n0\n370\n0\n  0\nENDSEC\n"
        }
    ]
}
```

*1.7 Aligned Dimension — definition points plus override text*

An aligned linear dimension carries up to three definition points and an override text string. On build the canonical dimension record contains the primary definition point, the dimension type flag, the text, and the two extension-line definition points.

**Test Cases:** `rcb_tests/public_test_cases/feature1_7_dimension.json`

```json
{
    "description": "Parse and emit an aligned linear dimension. The dimension carries up to three definition points and an override text string. On output the canonical dimension record contains the primary definition point, the dimension type flag, the text, and the two extension-line definition points.",
    "cases": [
        {
            "input": {
                "op": "read_entity",
                "dxf": "  0\nDIMENSION\n  1\ntext\n 10\n330.25\n 20\n1310.0\n 13\n330.25\n 23\n1282.0\n 14\n319.75\n 24\n1282.0\n 70\n1\n"
            },
            "expected_output": "type=dimension\nlayer=0\nlinetype=BYLAYER\nlinetype_scale=1\nis_visible=true\nis_in_paper_space=false\ncolor=BYLAYER\ndefinition_point_1=330.25,1310,0\ndefinition_point_2=330.25,1282,0\ndefinition_point_3=319.75,1282,0\ntext=text\n"
        },
        {
            "input": {
                "op": "write_entity",
                "entity": {
                    "type": "aligned_dimension",
                    "color_index": 7,
                    "definition_point_1": [
                        330.25,
                        1310.0,
                        330.25
                    ],
                    "definition_point_2": [
                        330.25,
                        1282.0,
                        0.0
                    ],
                    "definition_point_3": [
                        319.75,
                        1282.0,
                        0.0
                    ],
                    "handle": 66,
                    "layer": "bar",
                    "text": "text"
                }
            },
            "expected_output": "  0\nSECTION\n  2\nENTITIES\n  0\nDIMENSION\n  5\n42\n100\nAcDbEntity\n  8\nbar\n 62\n7\n100\nAcDbDimension\n  2\n\n 10\n330.25\n 20\n1310.0\n 30\n330.25\n 11\n0.0\n 21\n0.0\n 31\n0.0\n 70\n0\n  1\ntext\n  3\n\n100\nAcDbAlignedDimension\n 12\n0.0\n 22\n0.0\n 32\n0.0\n 13\n330.25\n 23\n1282.0\n 33\n0.0\n 14\n319.75\n 24\n1282.0\n 34\n0.0\n  0\nENDSEC\n"
        }
    ]
}
```

*1.8 Solid — four corners with optional thickness and extrusion*

A filled solid is defined by four corner points, an optional thickness, and an extrusion direction (default +Z). When read from a bare record every corner defaults to the origin.

**Test Cases:** `rcb_tests/public_test_cases/feature1_8_solid.json`

```json
{
    "description": "Parse and emit a filled solid. A solid is defined by four corner points, an optional thickness, and an extrusion direction that defaults to +Z. When read from a bare record every corner defaults to the origin.",
    "cases": [
        {
            "input": {
                "op": "read_entity",
                "dxf": "  0\nSOLID\n"
            },
            "expected_output": "type=solid\nlayer=0\nlinetype=BYLAYER\nlinetype_scale=1\nis_visible=true\nis_in_paper_space=false\ncolor=BYLAYER\nfirst_corner=0,0,0\nsecond_corner=0,0,0\nthird_corner=0,0,0\nfourth_corner=0,0,0\nthickness=0\nextrusion=0,0,1\n"
        }
    ]
}
```

### Feature 2: Common Properties & Extension Data

Every entity shares a common preamble independent of its geometric type, and any entity may carry application-scoped extension data. These behaviors are exercised separately from the geometry.

*2.1 Shared entity preamble — handle, layer, linetype, scale, visibility, color*

Independent of type, every entity carries a handle, an owning layer name, a linetype name, a linetype scale, a visibility flag, a paper-space membership flag, and a color. These are parsed from the shared leading group codes and reported in the canonical entity preamble.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_common_properties.json`

```json
{
    "description": "Every entity shares a common set of properties independent of its geometric type: a handle, the owning layer name, a linetype name, a linetype scale, a visibility flag, a paper-space membership flag, and a color index. These are parsed from the shared leading group codes and reported in the canonical entity preamble.",
    "cases": [
        {
            "input": {
                "op": "read_entity",
                "dxf": "  0\nLINE\n  5\n42\n  6\n<linetype-name>\n  8\n<layer>\n 48\n3.14159\n 60\n1\n 62\n1\n 67\n1\n 10\n1.1\n 20\n2.2\n 30\n3.3\n"
            },
            "expected_output": "type=line\nlayer=<layer>\nlinetype=<linetype-name>\nlinetype_scale=3.14159\nis_visible=false\nis_in_paper_space=true\ncolor=1\np1=1.1,2.2,3.3\np2=0,0,0\nthickness=0\nextrusion=0,0,1\n"
        }
    ]
}
```

*2.2 Extension data groups — `{app … }` brace-delimited code/value lists*

Entities may carry application-scoped extension data groups, delimited by an opening `{<app-name>` marker and a matching `}` marker. The group preserves an ordered list of raw code/value pairs. Groups present in the input are reported on read, and groups supplied programmatically are emitted before the entity body on build.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_extension_data.json`

```json
{
    "description": "Entities may carry application-scoped extension data groups, delimited by an opening '{<app-name>' marker (group code 102) and a matching '}' marker. The group preserves an ordered list of raw code/value pairs. Both directions are supported: extension groups present in the input are reported, and groups supplied programmatically are emitted before the entity body.",
    "cases": [
        {
            "input": {
                "op": "read_entity",
                "dxf": "  0\nLINE\n102\n{APP_NAME\n360\nAAAA\n360\nBBBB\n102\n}\n"
            },
            "expected_output": "type=line\nlayer=0\nlinetype=BYLAYER\nlinetype_scale=1\nis_visible=true\nis_in_paper_space=false\ncolor=BYLAYER\nextension.group_name=APP_NAME\nextension.group_item_count=2\nextension.item.0=360:AAAA\nextension.item.1=360:BBBB\np1=0,0,0\np2=0,0,0\nthickness=0\nextrusion=0,0,1\n"
        },
        {
            "input": {
                "op": "write_entity",
                "entity": {
                    "type": "line",
                    "extension_groups": [
                        {
                            "name": "APP_NAME",
                            "pairs": [
                                {
                                    "code": 1,
                                    "value": "foo"
                                },
                                {
                                    "code": 2,
                                    "value": "bar"
                                }
                            ]
                        }
                    ]
                }
            },
            "expected_output": "  0\nSECTION\n  2\nENTITIES\n  0\nLINE\n  5\nA\n102\n{APP_NAME\n  1\nfoo\n  2\nbar\n102\n}\n100\nAcDbEntity\n  8\n0\n100\nAcDbLine\n 10\n0.0\n 20\n0.0\n 30\n0.0\n 11\n0.0\n 21\n0.0\n 31\n0.0\n  0\nENDSEC\n"
        }
    ]
}
```

### Feature 3: Header Variables

The drawing header holds named global variables of several types. The toolkit parses them into typed values, writes them with the correct formatting, converts date/time variables, parses numbers independently of locale, and tolerates alternate boolean encodings.

*3.1 Reading typed header values*

Reading the header parses each variable's typed value — integers, reals, angles, enumerations, and layer-name strings — and reports the requested fields in canonical form.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_header_read.json`

```json
{
    "description": "The drawing header holds named global variables. Reading the header parses each variable's typed value (integers, reals, angles, enumerations, layer-name strings) and reports the requested fields in canonical form.",
    "cases": [
        {
            "input": {
                "op": "read_header",
                "dxf": "  9\n$ACADMAINTVER\n 70\n16\n  9\n$ACADVER\n  1\nAC1012\n  9\n$ANGBASE\n 50\n55.0\n  9\n$ANGDIR\n 70\n1\n  9\n$ATTMODE\n 70\n1\n  9\n$AUNITS\n 70\n3\n  9\n$AUPREC\n 70\n7\n  9\n$CLAYER\n  8\n<current layer>\n  9\n$LUNITS\n 70\n6\n  9\n$LUPREC\n 70\n7\n",
                "fields": [
                    "maintenance_version",
                    "version",
                    "angle_zero_direction",
                    "angle_direction",
                    "attribute_visibility",
                    "angle_unit_format",
                    "angle_unit_precision",
                    "current_layer",
                    "unit_format",
                    "unit_precision"
                ]
            },
            "expected_output": "maintenance_version=16\nversion=R13\nangle_zero_direction=55\nangle_direction=Clockwise\nattribute_visibility=Normal\nangle_unit_format=Radians\nangle_unit_precision=7\ncurrent_layer=<current layer>\nunit_format=Architectural\nunit_precision=7\n"
        }
    ]
}
```

*3.2 Writing header values with defaults*

Header variables can be set programmatically and are serialized with the correct group code and formatting. A variable left at its default is still emitted with its default value; the query reports the requested variable from the produced header.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_header_write.json`

```json
{
    "description": "Header variables can be set programmatically and are serialized with the correct group code and formatting. A variable left at its default is still emitted with its default value. The query reports the requested variable from the produced header.",
    "cases": [
        {
            "input": {
                "op": "write_header_var",
                "vars": [
                    "$DIMGAP"
                ]
            },
            "expected_output": "  9\n$DIMGAP\n 40\n0.0\n"
        },
        {
            "input": {
                "op": "write_header_var",
                "dimension_line_gap": 11.0,
                "vars": [
                    "$DIMGAP"
                ]
            },
            "expected_output": "  9\n$DIMGAP\n 40\n11.0\n"
        }
    ]
}
```

*3.3 Date/time variables as Julian day numbers*

Date/time header variables are stored as Julian day numbers with a fractional day. Reading such a variable converts it to a calendar date/time (for example the reference value for 1999-12-31 21:58:35).

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_header_date.json`

```json
{
    "description": "Date/time header variables are stored as Julian day numbers with a fractional day. Reading such a variable converts it to a calendar date/time (for example the reference value for 1999-12-31 21:58:35).",
    "cases": [
        {
            "input": {
                "op": "read_creation_date",
                "dxf": "  9\n$TDCREATE\n 40\n2451544.91568287\n"
            },
            "expected_output": "creation_date=1999-12-31T21:58:35.000\n"
        }
    ]
}
```

*3.4 Locale-independent numeric parsing*

Numeric parsing must be independent of the host machine's regional formatting. The same drawing parsed under a comma-decimal locale must produce exactly the same numeric output as under a period-decimal locale; the query carries the locale to install before parsing.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_header_locale.json`

```json
{
    "description": "Numeric parsing must be independent of the host machine's regional formatting. The same drawing parsed under a locale that uses a comma decimal separator must produce exactly the same numeric output as one parsed under a period-decimal locale. The query carries the locale to install before parsing.",
    "cases": [
        {
            "input": {
                "op": "read_creation_date",
                "locale": "de-DE",
                "dxf": "  9\n$TDCREATE\n 40\n2456478.590142998\n"
            },
            "expected_output": "creation_date=2013-07-04T14:09:48.355\n"
        },
        {
            "input": {
                "op": "read_creation_date",
                "locale": "en-US",
                "dxf": "  9\n$TDCREATE\n 40\n2456478.590142998\n"
            },
            "expected_output": "creation_date=2013-07-04T14:09:48.355\n"
        }
    ]
}
```

*3.5 Tolerant boolean decoding*

Some boolean header variables are specified to use a boolean group code, but files in the wild encode them with a short-integer group code instead. The reader must accept either encoding and produce the same canonical boolean output.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5_header_bool_code.json`

```json
{
    "description": "Some boolean header variables are specified to use a boolean group code, but files in the wild encode them with a short-integer group code instead. The reader must accept either encoding and produce the same canonical boolean output.",
    "cases": [
        {
            "input": {
                "op": "read_header",
                "dxf": "  9\n$ACADVER\n  1\nAC1018\n  9\n$HIDETEXT\n290\n1\n",
                "fields": [
                    "hide_text_objects"
                ]
            },
            "expected_output": "hide_text_objects=true\n"
        },
        {
            "input": {
                "op": "read_header",
                "dxf": "  9\n$ACADVER\n  1\nAC1018\n  9\n$HIDETEXT\n280\n1\n",
                "fields": [
                    "hide_text_objects"
                ]
            },
            "expected_output": "hide_text_objects=true\n"
        }
    ]
}
```

### Feature 4: Symbol Tables

Named symbol tables hold reusable definitions. The toolkit reads existing tables into typed records and builds default records for serialization.

*4.1 Layer table — name, color, optional extension data*

Each layer record carries a name and a color index, and may carry application extension-data groups. Reading the table parses every layer; layers can also be created programmatically and serialized as the canonical LAYER table.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_layers.json`

```json
{
    "description": "Layers are stored in a named symbol table. Each layer record carries a name and a color index, and may carry application extension-data groups. Reading the table parses every layer; layers can also be created programmatically and serialized as the canonical LAYER table.",
    "cases": [
        {
            "input": {
                "op": "read_layers",
                "dxf": "  0\nTABLE\n  2\nLAYER\n  0\nLAYER\n  2\na\n 62\n12\n  0\nLAYER\n  2\nb\n 62\n13\n  0\nENDTAB\n"
            },
            "expected_output": "layer_count=2\nlayer.0.name=a\nlayer.0.color=12\nlayer.1.name=b\nlayer.1.color=13\n"
        },
        {
            "input": {
                "op": "read_layers",
                "dxf": "  0\nTABLE\n  2\nLAYER\n  0\nLAYER\n  2\nb\n 62\n13\n102\n{APP_NAME\n  1\nfoo\n  2\nbar\n102\n}\n  0\nENDTAB\n"
            },
            "expected_output": "layer_count=1\nlayer.0.name=b\nlayer.0.color=13\nlayer.0.group_name=APP_NAME\nlayer.0.group_item_count=2\nlayer.0.item.0=1:foo\nlayer.0.item.1=2:bar\n"
        },
        {
            "input": {
                "op": "write_layer",
                "name": "default"
            },
            "expected_output": "  0\nTABLE\n  2\nLAYER\n  5\n5\n100\nAcDbSymbolTable\n 70\n0\n  0\nLAYER\n  5\nA\n100\nAcDbSymbolTableRecord\n100\nAcDbLayerTableRecord\n  2\ndefault\n 70\n0\n 62\n1\n  6\n\n  0\nENDTAB\n"
        }
    ]
}
```

*4.2 Viewport table — full view geometry with defaults*

Each viewport record carries a name plus a large set of view-geometry values (corners, view center, snap and grid spacing, view direction, target point, height, aspect ratio, lens length, clipping planes, and rotation angles). A defaulted viewport emits the canonical zero/identity values; the view-direction Z defaults to 1.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_viewports.json`

```json
{
    "description": "Viewports are stored in a named symbol table. Each viewport record carries a name plus a large set of view-geometry values (corners, view center, snap and grid spacing, view direction, target point, height, aspect ratio, lens length, clipping planes, and rotation angles). A defaulted viewport emits the canonical zero/identity values; the view-direction Z defaults to 1.",
    "cases": [
        {
            "input": {
                "op": "read_viewports",
                "dxf": "  0\nTABLE\n  2\nVPORT\n  0\nVPORT\n  2\n*ACTIVE\n  0\nENDTAB\n",
                "index": 0
            },
            "expected_output": "viewport_count=1\nname=*ACTIVE\nlower_left=0,0,0\nupper_right=0,0,0\nview_center=0,0,0\nsnap_base_point=0,0,0\nsnap_spacing=0,0,0\ngrid_spacing=0,0,0\nview_direction=0,0,1\ntarget_view_point=0,0,0\nview_height=0\naspect_ratio=0\nlens_length=0\nfront_clipping_plane=0\nback_clipping_plane=0\nsnap_rotation_angle=0\nview_twist_angle=0\n"
        },
        {
            "input": {
                "op": "write_viewport"
            },
            "expected_output": "  0\nTABLE\n  2\nVPORT\n  5\n9\n100\nAcDbSymbolTable\n 70\n0\n  0\nVPORT\n  5\nA\n100\nAcDbSymbolTableRecord\n100\nAcDbViewportTableRecord\n  2\n\n 70\n0\n 10\n0.0\n 20\n0.0\n 11\n0.0\n 21\n0.0\n 12\n0.0\n 22\n0.0\n 13\n0.0\n 23\n0.0\n 14\n0.0\n 24\n0.0\n 15\n0.0\n 25\n0.0\n 16\n0.0\n 26\n0.0\n 36\n1.0\n 17\n0.0\n 27\n0.0\n 37\n0.0\n 40\n0.0\n 41\n0.0\n 42\n0.0\n 43\n0.0\n 44\n0.0\n 50\n0.0\n 51\n0.0\n 71\n0\n 72\n0\n 73\n1\n 74\n0\n 75\n0\n 76\n0\n 77\n0\n 78\n0\n  0\nENDTAB\n"
        }
    ]
}
```

*4.3 Text-style table — font and shape parameters*

Each text-style record carries a name, standard flags, a fixed text height, a width factor, an oblique angle, generation flags, a last-height-used value, and a primary font file name. Both reading an existing table and creating a default style are supported.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_styles.json`

```json
{
    "description": "Text styles are stored in a named symbol table. Each style record carries a name, standard flags, a fixed text height, a width factor, an oblique angle, generation flags, a last-height-used value, and a primary font file name. Both reading an existing table and creating a default style are supported.",
    "cases": [
        {
            "input": {
                "op": "read_styles",
                "dxf": "  0\nSECTION\n  2\nTABLES\n  0\nTABLE\n  2\nSTYLE\n  0\nSTYLE\n  2\nENTRY_1\n 70\n64\n 40\n0.4\n 41\n1.0\n 50\n0.0\n 71\n0\n 42\n0.4\n  3\nBUFONTS.TXT\n  0\nENDTAB\n  0\nENDSEC\n  0\nEOF"
            },
            "expected_output": "style_count=1\nstyle.0.handle=A\nstyle.0.name=ENTRY_1\nstyle.0.standard_flags=64\nstyle.0.text_height=0.4\nstyle.0.width_factor=1\nstyle.0.oblique_angle=0\nstyle.0.text_generation_flags=0\nstyle.0.last_height_used=0.4\nstyle.0.primary_font=BUFONTS.TXT\n"
        },
        {
            "input": {
                "op": "write_style_table"
            },
            "expected_output": "  0\nSECTION\n  2\nTABLES\n  0\nTABLE\n  2\nSTYLE\n  5\n6\n100\nAcDbSymbolTable\n 70\n0\n  0\nSTYLE\n  5\nA\n100\nAcDbSymbolTableRecord\n100\nAcDbTextStyleTableRecord\n  2\n\n 70\n0\n 40\n0.0\n 41\n1.0\n 50\n0.0\n 71\n0\n 42\n0.0\n  3\n\n  4\n\n  0\nENDTAB\n  0\nENDSEC\n"
        }
    ]
}
```

### Feature 5: Blocks

A block groups a named collection of entities around a base point. Reading parses every block and its contents; building serializes a block for the target version with the correct begin/end markers.

*5.1 Reading blocks and their contents*

Reading the blocks section parses every block, its base point, and its contained entities in order.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_blocks_read.json`

```json
{
    "description": "A block groups a named collection of entities around a base point. Reading the blocks section parses every block, its base point, and its contained entities in order.",
    "cases": [
        {
            "input": {
                "op": "read_blocks",
                "dxf": "  0\nSECTION\n  2\nBLOCKS\n  0\nBLOCK\n  2\nblock #1\n 10\n1\n 20\n2\n 30\n3\n  0\nLINE\n 10\n10\n 20\n20\n 30\n30\n 11\n11\n 21\n21\n 31\n31\n  0\nENDBLK\n  0\nBLOCK\n  2\nblock #2\n  0\nCIRCLE\n 40\n40\n  0\nARC\n 40\n41\n  0\nENDBLK\n  0\nENDSEC\n  0\nEOF"
            },
            "expected_output": "block_count=2\nblock.0.name=block #1\nblock.0.handle=A\nblock.0.layer=null\nblock.0.base_point=1,2,3\nblock.0.entity_count=1\nblock.0.entity.0.type=line\nblock.0.entity.0.p1=10,20,30\nblock.0.entity.0.p2=11,21,31\nblock.1.name=block #2\nblock.1.handle=B\nblock.1.layer=null\nblock.1.base_point=0,0,0\nblock.1.entity_count=2\nblock.1.entity.0.type=circle\nblock.1.entity.0.radius=40\nblock.1.entity.1.type=arc\nblock.1.entity.1.radius=41\n"
        }
    ]
}
```

*5.2 Version-sensitive block serialization*

A block carries a name, a handle, an owning layer, an external-reference path, a base point, and contained entities. For an R13-class target the block-begin and block-end records both include the entity subclass markers and the owning layer; reading the equivalent form recovers the block contents.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_blocks_version.json`

```json
{
    "description": "Block serialization is version-sensitive. A block carries a name, a handle, an owning layer, an external-reference path, a base point, and contained entities. For an R13-class target the block-begin and block-end records both include the entity subclass markers and the owning layer. Reading the equivalent R13 form recovers the block contents.",
    "cases": [
        {
            "input": {
                "op": "write_block",
                "version": "R13",
                "name": "<block name>",
                "handle": 66,
                "layer": "<layer>",
                "xref_name": "<xref>",
                "base_point": [
                    11,
                    22,
                    33
                ],
                "entities": [
                    {
                        "type": "point",
                        "location": [
                            111,
                            222,
                            333
                        ]
                    }
                ]
            },
            "expected_output": "  0\nSECTION\n  2\nBLOCKS\n  0\nBLOCK\n  5\n42\n330\n0\n100\nAcDbEntity\n  8\n<layer>\n100\nAcDbBlockBegin\n  2\n<block name>\n 70\n0\n 10\n11.0\n 20\n22.0\n 30\n33.0\n  3\n<block name>\n  1\n<xref>\n  0\nPOINT\n100\nAcDbEntity\n  8\n0\n100\nAcDbPoint\n 10\n111.0\n 20\n222.0\n 30\n333.0\n  0\nENDBLK\n  5\n42\n100\nAcDbEntity\n  8\n<layer>\n100\nAcDbBlockEnd\n  0\nENDSEC\n"
        },
        {
            "input": {
                "op": "read_blocks",
                "dxf": "  0\nSECTION\n  2\nHEADER\n  9\n$ACADVER\n  1\nAC1012\n  0\nENDSEC\n  0\nSECTION\n  2\nBLOCKS\n  0\nBLOCK\n  5\n42\n100\nAcDbEntity\n  8\n<layer>\n100\nAcDbBlockBegin\n  2\n<block name>\n 70\n0\n 10\n11\n 20\n22\n 30\n33\n  3\n<block name>\n  1\n<xref path>\n  0\nPOINT\n 10\n1.1\n 20\n2.2\n 30\n3.3\n  0\nENDBLK\n  5\n42\n100\nAcDbEntity\n  8\n<layer>\n100\nAcDbBlockEnd\n  0\nENDSEC\n  0\nEOF"
            },
            "expected_output": "block_count=1\nblock.0.name=<block name>\nblock.0.handle=42\nblock.0.layer=<layer>\nblock.0.xref_name=<xref path>\nblock.0.base_point=11,22,33\nblock.0.entity_count=1\nblock.0.entity.0.type=point\nblock.0.entity.0.location=1.1,2.2,3.3\n"
        }
    ]
}
```

### Feature 6: Class Registrations

The classes section registers custom object class definitions. Two on-disk forms exist and both parse into the same registration; building emits the canonical form for the target version.

*6.1 Reading both class dialects*

An older form uses the record-name as the class marker; a newer form introduces each record with a `CLASS` marker. Both parse into the same class registration: record name, C++ class name, application name, and a version/proxy-capability value.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_classes_read.json`

```json
{
    "description": "The classes section registers custom object class definitions. Two on-disk forms exist: an older form where the record-name is the class marker and a newer form introduced by a 'CLASS' marker. Both are parsed into the same class registration (record name, C++ class name, application name, and a version/proxy-capability value).",
    "cases": [
        {
            "input": {
                "op": "read_classes",
                "dxf": "  0\nSECTION\n  2\nHEADER\n  9\n$ACADVER\n  1\nAC1012\n  0\nENDSEC\n  0\nSECTION\n  2\nCLASSES\n  0\n<class dxf name>\n  1\nCPP_CLASS_NAME\n  2\n<application name>\n 90\n42\n  0\nENDSEC\n  0\nEOF"
            },
            "expected_output": "class_count=1\nclass.0.record_name=<class dxf name>\nclass.0.cpp_class_name=CPP_CLASS_NAME\nclass.0.application_name=<application name>\nclass.0.class_version=42\n"
        },
        {
            "input": {
                "op": "read_classes",
                "dxf": "  0\nSECTION\n  2\nHEADER\n  9\n$ACADVER\n  1\nAC1014\n  0\nENDSEC\n  0\nSECTION\n  2\nCLASSES\n  0\nCLASS\n  1\n<class dxf name>\n  2\nCPP_CLASS_NAME\n  3\n<application name>\n 90\n42\n  0\nENDSEC\n  0\nEOF"
            },
            "expected_output": "class_count=1\nclass.0.record_name=<class dxf name>\nclass.0.cpp_class_name=CPP_CLASS_NAME\nclass.0.application_name=<application name>\nclass.0.class_version=0\n"
        }
    ]
}
```

*6.2 Building class registrations per target version*

Class definitions can be created programmatically with a record name, a C++ class name, an application name, and either a class-version number or a proxy-capability flag value, then serialized into the canonical classes section for the target version.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_classes_write.json`

```json
{
    "description": "Class definitions can be created programmatically with a record name, a C++ class name, an application name, and either a class-version number or a proxy-capability flag value, then serialized into the canonical classes section for the target.",
    "cases": [
        {
            "input": {
                "op": "write_class",
                "version": "R13",
                "record_name": "<class dxf name>",
                "cpp_class_name": "CPP_CLASS_NAME",
                "application_name": "<application name>",
                "class_version": 42
            },
            "expected_output": "  0\nSECTION\n  2\nCLASSES\n  0\n<class dxf name>\n  1\nCPP_CLASS_NAME\n  2\n<application name>\n 90\n42\n280\n1\n281\n0\n  0\nENDSEC\n"
        },
        {
            "input": {
                "op": "write_class",
                "version": "R14",
                "record_name": "<class dxf name>",
                "cpp_class_name": "CPP_CLASS_NAME",
                "application_name": "<application name>",
                "proxy_capabilities": 42
            },
            "expected_output": "  0\nSECTION\n  2\nCLASSES\n  0\nCLASS\n  1\n<class dxf name>\n  2\nCPP_CLASS_NAME\n  3\n<application name>\n 90\n42\n280\n1\n281\n0\n  0\nENDSEC\n"
        }
    ]
}
```

### Feature 7: Block Records with Extended Data

Block records are table entries that may carry extended application data (XData) and raw bitmap preview bytes. XData preserves an application name and an ordered list of typed items (strings, integers, and nested brace-delimited control groups). Bitmap bytes are rendered as a hex string. Both reading and programmatic creation are supported.

*7.1 Reading and building block-record extended data*

Reading a block-record table parses the record name, layout handle, bitmap bytes, and the structured XData tree. Building a block record from a typed XData spec plus bitmap bytes emits the canonical block-record table for a newer target version.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_block_record.json`

```json
{
    "description": "Block records are table entries that may carry extended application data (XData) and raw bitmap preview bytes. XData preserves an application name and an ordered list of typed items (strings, integers, and nested brace-delimited control groups). Bitmap bytes are emitted as a hex string. Both reading and programmatic creation are supported.",
    "cases": [
        {
            "input": {
                "op": "read_block_records",
                "dxf": "  0\nTABLE\n  2\nBLOCK_RECORD\n  0\nBLOCK_RECORD\n  2\n<name>\n1001\nACAD\n1000\nDesignCenter Data\n1002\n{\n1070\n0\n1070\n1\n1070\n2\n1002\n}\n  0\nENDTAB\n"
            },
            "expected_output": "block_record_count=1\nname=<name>\nlayout_handle=0\nbitmap_data=\nxdata.application=ACAD\nxdata.item_count=2\nxdata.item.0.type=String\nxdata.item.0.value=DesignCenter Data\nxdata.item.1.type=ControlString\nxdata.item.1.item_count=3\nxdata.item.1.item.0.type=Integer\nxdata.item.1.item.0.value=0\nxdata.item.1.item.1.type=Integer\nxdata.item.1.item.1.value=1\nxdata.item.1.item.2.type=Integer\nxdata.item.1.item.2.value=2\n"
        },
        {
            "input": {
                "op": "write_block_record",
                "version": "R2000",
                "name": "<name>",
                "xdata": {
                    "application": "ACAD",
                    "items": [
                        {
                            "type": "string",
                            "value": "DesignCenter Data"
                        },
                        {
                            "type": "control_group",
                            "items": [
                                {
                                    "type": "integer",
                                    "value": 0
                                },
                                {
                                    "type": "integer",
                                    "value": 1
                                },
                                {
                                    "type": "integer",
                                    "value": 2
                                }
                            ]
                        }
                    ]
                },
                "bitmap_data": [
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    7,
                    8,
                    9,
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    7,
                    8,
                    9
                ]
            },
            "expected_output": "  0\nTABLE\n  2\nBLOCK_RECORD\n  5\n2\n330\n0\n100\nAcDbSymbolTable\n 70\n0\n  0\nBLOCK_RECORD\n  5\nA\n330\n0\n100\nAcDbSymbolTableRecord\n100\nAcDbBlockTableRecord\n  2\n<name>\n340\n0\n310\n010203040506070809010203040506070809\n1001\nACAD\n1000\nDesignCenter Data\n1002\n{\n1070\n0\n1070\n1\n1070\n2\n1002\n}\n  0\nENDTAB\n"
        }
    ]
}
```

### Feature 8: Thumbnail Previews

A drawing may embed a thumbnail preview image. The payload can be read raw or wrapped as a complete bitmap, and writing the section is version-gated.

*8.1 Reading the raw preview payload*

Reading the raw thumbnail returns the stored preview payload bytes exactly, rendered as a lowercase hex string.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_thumbnail_raw.json`

```json
{
    "description": "A drawing may embed a thumbnail preview image. Reading the raw thumbnail returns the stored preview payload bytes exactly, rendered as a lowercase hex string.",
    "cases": [
        {
            "input": {
                "op": "read_thumbnail_raw",
                "dxf": " 90\n3\n310\n012345\n"
            },
            "expected_output": "thumbnail_raw=012345\n"
        }
    ]
}
```

*8.2 Returning the payload as a full bitmap*

The payload can be returned as a complete bitmap by prefixing it with a fixed bitmap file header (the 'BM' magic, the payload length, reserved fields, and a fixed bit-offset). The result is rendered as a lowercase hex string.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_thumbnail_bmp.json`

```json
{
    "description": "The embedded thumbnail payload can be returned as a complete bitmap by prefixing it with a fixed bitmap file header (the 'BM' magic, the payload length, reserved fields, and a fixed bit-offset). The result is rendered as a lowercase hex string.",
    "cases": [
        {
            "input": {
                "op": "read_thumbnail_bitmap",
                "dxf": " 90\n3\n310\n012345\n"
            },
            "expected_output": "thumbnail_bitmap=424d030000000000000036040000012345\n"
        }
    ]
}
```

*8.3 Version-gated thumbnail writing*

Whether a thumbnail section is written depends on the target version: pre-R2000 targets omit it, while R2000-class targets emit it. The payload may be supplied as raw preview bytes or as a full bitmap (whose fixed header is stripped before storing). When the section is omitted the result reports its absence.

**Test Cases:** `rcb_tests/public_test_cases/feature8_3_thumbnail_write.json`

```json
{
    "description": "Whether a thumbnail section is written depends on the target version: pre-R2000 targets omit the section entirely, while R2000-class targets emit it. The payload may be supplied either as raw preview bytes or as a full bitmap (in which case the fixed bitmap header is stripped before storing). When the section is omitted the result reports its absence.",
    "cases": [
        {
            "input": {
                "op": "write_thumbnail",
                "version": "R14",
                "raw_thumbnail": [
                    1,
                    35,
                    69
                ]
            },
            "expected_output": "thumbnail_section=absent\n"
        },
        {
            "input": {
                "op": "write_thumbnail",
                "version": "R2000",
                "raw_thumbnail": [
                    1,
                    35,
                    69
                ]
            },
            "expected_output": "  0\nSECTION\n  2\nTHUMBNAILIMAGE\n 90\n3\n310\n012345\n  0\nENDSEC\n"
        },
        {
            "input": {
                "op": "write_thumbnail",
                "version": "R2000",
                "set_bitmap": [
                    66,
                    77,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    54,
                    4,
                    0,
                    0,
                    1,
                    35,
                    69
                ]
            },
            "expected_output": "  0\nSECTION\n  2\nTHUMBNAILIMAGE\n 90\n3\n310\n012345\n  0\nENDSEC\n"
        }
    ]
}
```

### Feature 9: Alternate Encodings

Besides the text encoding, drawings may be stored in two binary encodings, and a text stream may begin with a byte-order mark. The reader auto-detects the encoding and skips a leading mark transparently.

*9.1 Binary-encoded drawing auto-detection*

A binary-encoded drawing is distinguished by a sentinel header; the reader auto-detects it and recovers the document. The query reports document statistics: total entity count, a per-entity-type breakdown, and the layer count. The input is the base64 of a binary-encoded drawing.

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_binary_read.json`

```json
{
    "description": "Besides the text encoding, drawings may be stored in a binary encoding distinguished by a sentinel header. The reader auto-detects the encoding from the stream and recovers the document. The query reports document statistics: total entity count, a per-entity-type breakdown, and the layer count. The input is the base64 of a binary-encoded drawing.",
    "cases": [
        {
            "input": {
                "op": "load_binary",
                "data": "QXV0b0NBRCBCaW5hcnkgRFhGDQoaAABTRUNUSU9OAAJFTlRJVElFUwAATElORQAIMAAKAAAAAACARkAUAAAAAACARkAeAAAAAAAAAAALAAAAAACARkAVAAAAAACARsAfAAAAAAAAAAAATElORQAIMAAKAAAAAACARkAUAAAAAACARsAeAAAAAAAAAAALAAAAAAAAAAAVAAAAAAAAAAAfAAAAAAAAAAAATElORQAIMAAKAAAAAAAAAAAUAAAAAAAAAAAeAAAAAAAAAAALAAAAAACARsAVAAAAAACARkAfAAAAAAAAAAAATElORQAIMAAKAAAAAACARsAUAAAAAACARkAeAAAAAAAAAAALAAAAAACARkAVAAAAAACARkAfAAAAAAAAAAAATElORQAIMAAKAAAAAACARkAUAAAAAACARkAeAAAAAAAAAAALAAAAAAAAAAAVAAAAAAAAAAAfAAAAAACAU8AATElORQAIMAAKAAAAAAAAAAAUAAAAAAAAAAAeAAAAAACAU8ALAAAAAAAAAAAVAAAAAAAAAAAfAAAAAAAAAAAATElORQAIMAAKAAAAAAAAAAAUAAAAAAAAAAAeAAAAAAAAAAALAAAAAACARsAVAAAAAACARsAfAAAAAAAAAAAATElORQAIMAAKAAAAAACARsAUAAAAAACARsAeAAAAAAAAAAALAAAAAACARkAVAAAAAACARkAfAAAAAAAAAAAATElORQAIMAAKAAAAAACARkAUAAAAAACARsAeAAAAAAAAAAALAAAAAACARsAVAAAAAACARsAfAAAAAAAAAAAATElORQAIMAAKAAAAAACARsAUAAAAAACARsAeAAAAAAAAAAALAAAAAACARsAVAAAAAACARkAfAAAAAAAAAAAATElORQAIMAAKAAAAAACARsAUAAAAAACARkAeAAAAAAAAAAALAAAAAAAAAAAVAAAAAAAAAAAfAAAAAACAU8AATElORQAIMAAKAAAAAAAAAAAUAAAAAAAAAAAeAAAAAACAU8ALAAAAAACARkAVAAAAAACARsAfAAAAAAAAAAAARU5EU0VDAABFT0YA"
            },
            "expected_output": "entity_count=12\nentity_type.line=12\nlayer_count=0\n"
        }
    ]
}
```

*9.2 Compact binary drawing format*

A separate compact binary format begins with its own sentinel header, encodes a current color followed by geometry primitives, and is terminated by a null record. The reader auto-detects it and recovers the entities; the writer can produce it from a drawing and read it back.

**Test Cases:** `rcb_tests/public_test_cases/feature9_2_dxb.json`

```json
{
    "description": "A separate compact binary drawing format is also supported. It begins with its own sentinel header, encodes a current color followed by geometry primitives, and is terminated by a null record. The reader auto-detects it and recovers the entities; the writer can produce it from a drawing and read it back.",
    "cases": [
        {
            "input": {
                "op": "load_dxb",
                "data": "QXV0b0NBRCBEWEIgMS4wDQoaAIgBAAEBAAIAAwAEAAUABgAA"
            },
            "expected_output": "entity_count=1\ntype=line\nlayer=0\nlinetype=BYLAYER\nlinetype_scale=1\nis_visible=true\nis_in_paper_space=false\ncolor=1\np1=1,2,3\np2=4,5,6\nthickness=0\nextrusion=0,0,1\n"
        },
        {
            "input": {
                "op": "dxb_roundtrip",
                "entity": {
                    "type": "line",
                    "p1": [
                        1,
                        2,
                        3
                    ],
                    "p2": [
                        4,
                        5,
                        6
                    ]
                }
            },
            "expected_output": "entity_count=1\ntype=line\nlayer=0\nlinetype=BYLAYER\nlinetype_scale=1\nis_visible=true\nis_in_paper_space=false\ncolor=BYLAYER\np1=1,2,3\np2=4,5,6\nthickness=0\nextrusion=0,0,1\n"
        }
    ]
}
```

*9.3 Byte-order-mark tolerance*

A leading byte-order mark on a text drawing stream must be skipped transparently so that an otherwise empty document parses successfully with no entities or tables. The input is the base64 of a BOM-prefixed minimal stream.

**Test Cases:** `rcb_tests/public_test_cases/feature9_3_bom.json`

```json
{
    "description": "A leading byte-order mark on a text drawing stream must be skipped transparently so that an otherwise empty document parses successfully with no entities or tables. The input is the base64 of a BOM-prefixed minimal stream.",
    "cases": [
        {
            "input": {
                "op": "load_binary",
                "data": "77u/MA0KRU9G"
            },
            "expected_output": "entity_count=0\nlayer_count=0\n"
        }
    ]
}
```

### Feature 10: Version Gating

Which sections, tables, entities, and properties appear in the output depends on the requested target version. The toolkit gates them consistently.

*10.1 Section presence by version*

A legacy target (R12-class) omits the classes section, whereas a newer target (R13-class) includes it. The result reports whether the requested section is present in the serialized drawing.

**Test Cases:** `rcb_tests/public_test_cases/feature10_1_sections_version.json`

```json
{
    "description": "Which top-level sections appear in the output depends on the target version. A legacy target (R12-class) omits the classes section, whereas a newer target (R13-class) includes it. The result reports whether each requested section is present in the serialized drawing.",
    "cases": [
        {
            "input": {
                "op": "section_presence",
                "version": "R12",
                "add_class": true,
                "targets": [
                    "section:CLASSES"
                ]
            },
            "expected_output": "section.CLASSES=absent\n"
        },
        {
            "input": {
                "op": "section_presence",
                "version": "R13",
                "add_class": true,
                "targets": [
                    "section:CLASSES"
                ]
            },
            "expected_output": "section.CLASSES=present\n"
        }
    ]
}
```

*10.2 Block-record table presence by version*

A legacy target (R12-class) does not emit a block-record table even when a block record exists, while a newer target (R13-class) does. The result reports whether the block-record table is present.

**Test Cases:** `rcb_tests/public_test_cases/feature10_2_blockrecord_table_version.json`

```json
{
    "description": "The block-record table is version-gated. A legacy target (R12-class) does not emit a block-record table even when a block record exists, while a newer target (R13-class) does. The result reports whether the block-record table is present in the serialized drawing.",
    "cases": [
        {
            "input": {
                "op": "section_presence",
                "version": "R12",
                "add_block_record": true,
                "targets": [
                    "table:BLOCK_RECORD"
                ]
            },
            "expected_output": "table.BLOCK_RECORD=absent\n"
        },
        {
            "input": {
                "op": "section_presence",
                "version": "R13",
                "add_block_record": true,
                "targets": [
                    "table:BLOCK_RECORD"
                ]
            },
            "expected_output": "table.BLOCK_RECORD=present\n"
        }
    ]
}
```

*10.3 Entity & property gating by version*

A proxy entity is only serialized for R14-class and later targets and disappears on older targets. A leader's annotation-offset property (group 213) is only written for R14-class and later targets.

**Test Cases:** `rcb_tests/public_test_cases/feature10_3_version_entities.json`

```json
{
    "description": "Individual entities and entity properties are gated by target version. A proxy entity is only serialized for R14-class and later targets and disappears on older targets. A leader's annotation-offset property (group 213) is only written for R14-class and later targets.",
    "cases": [
        {
            "input": {
                "op": "write_entity",
                "version": "R14",
                "entity": {
                    "type": "proxy"
                }
            },
            "expected_output": "  0\nSECTION\n  2\nENTITIES\n  0\nACAD_PROXY_ENTITY\n  5\nA\n100\nAcDbEntity\n  8\n0\n100\nAcDbProxyEntity\n 90\n498\n 91\n500\n 92\n0\n 93\n0\n 94\n0\n  0\nENDSEC\n"
        },
        {
            "input": {
                "op": "write_entity",
                "version": "R13",
                "entity": {
                    "type": "proxy"
                }
            },
            "expected_output": "  0\nSECTION\n  2\nENTITIES\n  0\nENDSEC\n"
        },
        {
            "input": {
                "op": "entity_marker",
                "version": "R14",
                "entity": {
                    "type": "leader"
                },
                "markers": [
                    "213"
                ]
            },
            "expected_output": "marker.213=present\n"
        },
        {
            "input": {
                "op": "entity_marker",
                "version": "R13",
                "entity": {
                    "type": "leader"
                },
                "markers": [
                    "213"
                ]
            },
            "expected_output": "marker.213=absent\n"
        }
    ]
}
```

### Feature 11: Error Contract

Malformed or unsupported requests are reported with a stable, language-neutral error contract instead of leaking host-runtime fault details. Each error is a category line, optionally followed by a field line naming the offending value: unparseable input, an unknown operation, an unsupported target version, and an unknown entity type.

*11.1 Neutral error categories*

The adapter never emits a host-language exception type, message, or stack trace. Instead it emits `error=<category>` and, when applicable, a second line naming the offending field and value.

**Test Cases:** `rcb_tests/public_test_cases/feature11_1_errors.json`

```json
{
    "description": "The system reports malformed or unsupported requests with a stable, language-neutral error contract instead of leaking host-runtime fault details. Each error is a category line, optionally followed by a field line naming the offending value: unparseable input, an unknown operation, an unsupported target version, and an unknown entity type.",
    "cases": [
        {
            "input": "this is not json",
            "expected_output": "error=invalid_input\n"
        },
        {
            "input": {
                "op": "frobnicate"
            },
            "expected_output": "error=unknown_operation\nop=frobnicate\n"
        },
        {
            "input": {
                "op": "write_layer",
                "name": "x",
                "version": "R99"
            },
            "expected_output": "error=unknown_version\nversion=R99\n"
        },
        {
            "input": {
                "op": "write_entity",
                "entity": {
                    "type": "banana"
                }
            },
            "expected_output": "error=unknown_entity_type\ntype=banana\n"
        }
    ]
}
```

---

## Deliverables

1. **Core drawing library** — a multi-file, idiomatic implementation of the drawing model and its read/write pipeline:
   - A typed object model for the document, its sections, the symbol tables (layers, viewports, text styles, block records), blocks, class registrations, the header variable set, and a common entity abstraction with concrete entity types (line, circle, arc, ellipse, text, vertex, polyline, solid, aligned dimension, model point, proxy, leader, …).
   - A reader that auto-detects the stream encoding (text, full binary, compact binary), skips a leading byte-order mark, parses every section, decodes group codes into typed properties with correct defaults, tolerates alternate boolean encodings, and parses numbers locale-independently.
   - A writer that serializes a document to a requested target version, assigning handles and emitting the correct subclass markers, section/table presence, and entity/property gating for that version, plus the compact binary writer.

2. **Execution adapter** — a thin command surface (`rcb_tests/dispatcher/`) that reads one JSON command from stdin, invokes the core library through its public interface only, and renders the language-neutral textual contract described above. It must not contain business logic of its own and must normalize all failures to the neutral error contract.

3. **Test harness** — `rcb_tests/test.sh`, a single entry point that accepts `--cases-dir <subdir>` (default `public_test_cases`), feeds each case's `input` to the adapter, and writes the raw program stdout to `rcb_tests/stdout/<cases-dir>/<file-stem>@<NNN>.txt` for comparison against each case's `expected_output`.

4. **Public test cases** — `rcb_tests/public_test_cases/featureN_*.json`, the JSON files embedded above, each a `{"description", "cases":[{"input","expected_output"}]}` document.
