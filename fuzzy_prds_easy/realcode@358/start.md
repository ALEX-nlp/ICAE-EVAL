## Product Requirement Document

# Location Services Platform Contract — Coordinate Geodesy, Reading Serialization, Permission Modeling & Domain Errors

## Project Goal

Build the shared, platform-agnostic contract layer that sits between an application and whatever underlying operating-system location provider it runs on. It defines a single value type for a location reading, a small set of pure geodesy calculations over geographic coordinates, a canonical model of permission states and accuracy levels, and a consistent family of domain error conditions — so every concrete platform backend can plug in behind one stable, well-defined interface instead of each application re-implementing coordinate math, data parsing and error handling.

---

## Background & Problem

Applications that need a device's location must deal with several cross-cutting concerns that are independent of any specific operating system: turning the raw key/value data the platform hands back into a typed reading, computing distances and bearings between coordinates, expressing permission state as a stable set of tokens (often transported as small integers), and surfacing failures (denied permission, disabled location service, missing configuration, etc.) as well-typed conditions with clear messages.

Without a shared contract layer, every backend hand-rolls its own coordinate math, its own parsing rules, its own integer-to-permission mapping and its own ad-hoc error strings — producing inconsistent behavior and duplicated, error-prone code. This library fixes the contract once: pure great-circle geodesy, a strict reading deserializer with sensible defaults, a canonical permission/accuracy catalog with a fixed ordinal protocol, and a uniform set of domain errors whose human-readable descriptions are defined precisely.

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

### Feature 1: Great-Circle Distance Between Coordinates

**As a developer**, I want to compute the distance between two geographic points, so I can measure how far apart two locations are without depending on a platform service.

**Expected Behavior / Usage:**

The input supplies a start coordinate and an end coordinate, each as a latitude and longitude in decimal degrees. The system returns the great-circle (shortest surface) distance between them in meters, computed on a spherical Earth model. The result is always non-negative, is exactly zero when the two coordinates are identical, and is symmetric: swapping start and end yields the same distance. The single output line is the distance in meters.

**Test Cases:** `rcb_tests/public_test_cases/feature1_distance.json`

```json
{
    "description": "Compute the great-circle distance in meters between two geographic coordinates, each given as a latitude/longitude pair in decimal degrees. The result is the shortest surface distance between the two points and is always non-negative; it is zero when both points are identical and is symmetric with respect to swapping the start and end points. The single output line is the distance in meters.",
    "cases": [
        {
            "input": {"op": "distance", "startLatitude": 52.56127[a specific numeric comparison operator and threshold — ask the PM for the exact string], "startLongitude": 5.639382, "endLatitude": 52.56127[a specific numeric comparison operator and threshold — ask the PM for the exact string], "endLongitude": 5.639382},
            "expected_output": "[a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string]\n"
        },
        {
            "input": {"op": "distance", "startLatitude": 52.1[a specific numeric comparison operator and threshold — ask the PM for the exact string]58731, "startLongitude": 5.9[a specific numeric comparison operator and threshold — ask the PM for the exact string]76873, "endLatitude": 52.157296, "endLongitude": 5.3851278},
            "expected_output": "36164.1515[a specific numeric comparison operator and threshold — ask the PM for the exact string]48[a specific numeric comparison operator and threshold — ask the PM for the exact string]236\n"
        }
    ]
}
```

---

### Feature 2: Initial Bearing Between Coordinates

**As a developer**, I want to compute the initial heading from one coordinate toward another, so I can determine which direction to travel along the shortest path.

**Expected Behavior / Usage:**

The input supplies a start coordinate and an end coordinate, each as a latitude and longitude in decimal degrees. The system returns the initial bearing (forward azimuth) in degrees that one must head from the start point to follow the great-circle path toward the end point. The bearing is zero when the two coordinates coincide. The value is signed: headings east of due north are positive and headings west of due north are negative (so a due-west heading is reported as a negative quarter turn). The single output line is the bearing in degrees.

**Test Cases:** `rcb_tests/public_test_cases/feature2_bearing.json`

```json
{
    "description": "Compute the initial bearing (forward azimuth) in degrees for travel from a start coordinate to an end coordinate, each given as a latitude/longitude pair in decimal degrees. The bearing is the direction one must initially head along the great-circle path. It is zero when the two points coincide, and the result may be negative (east-of-north is positive, west-of-north is negative). The single output line is the bearing in degrees.",
    "cases": [
        {
            "input": {"op": "bearing", "startLatitude": 9[a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "startLongitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "endLatitude": -9[a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "endLongitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string]},
            "expected_output": "18[a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string]\n"
        },
        {
            "input": {"op": "bearing", "startLatitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "startLongitude": 18[a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "endLatitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "endLongitude": -18[a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string]},
            "expected_output": "9[a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string]\n"
        }
    ]
}
```

---

### Feature 3: Location Reading Deserialization

**As a developer**, I want to turn the raw key/value data a platform returns into a typed location reading, so the rest of my code works with structured values instead of loose maps.

**Expected Behavior / Usage:**

*3.1 Mandatory-field validation — rejecting incomplete input*

A location reading is deserialized from a map. The `latitude` and `longitude` entries are mandatory. If either is absent, deserialization fails immediately rather than producing a partial reading; the failure is reported as a neutral error line that names the missing field. (When both are absent the latitude is reported first.)

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_parse_errors.json`

```json
{
    "description": "Deserialize a location reading from a key/value map. Latitude and longitude are mandatory. When either mandatory key is absent, deserialization fails fast; the failure is reported as a neutral error line naming the missing field rather than producing a partial reading.",
    "cases": [
        {
            "input": {"op": "parse_position", "map": {"longitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string]}},
            "expected_output": "error=missing_required_field\nfield=latitude\n"
        },
        {
            "input": {"op": "parse_position", "map": {"latitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string]}},
            "expected_output": "error=missing_required_field\nfield=longitude\n"
        }
    ]
}
```

*3.2 Field parsing with defaults*

When the mandatory fields are present, the reading is built. The timestamp, if supplied, is an integer count of milliseconds since the Unix epoch (UTC). Every other numeric field — accuracy, altitude, vertical (altitude) accuracy, heading, heading accuracy, speed and speed accuracy — is optional and defaults to `[a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string]` when absent. The building floor is optional and is left unset (rendered as null) when absent. The mocked-provider flag defaults to false. The output lists every resolved field of the reading, one per line, with the timestamp expressed as epoch milliseconds.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_parse_defaults.json`

```json
{
    "description": "Deserialize a complete or partial location reading from a key/value map. Latitude and longitude are required; the timestamp is supplied as an integer count of milliseconds since the Unix epoch (UTC). All remaining numeric fields (accuracy, altitude, vertical accuracy, heading, heading accuracy, speed, speed accuracy) are optional and default to [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string] when absent; the building floor is optional and is left unset (null) when absent; the mocked-provider flag defaults to false. The output lists every resolved field of the reading, one per line, including the timestamp re-expressed as epoch milliseconds.",
    "cases": [
        {
            "input": {"op": "parse_position", "map": {"latitude": 52.1, "longitude": 5.4, "timestamp": 1[a specific numeric comparison operator and threshold — ask the PM for the exact string][a specific numeric comparison operator and threshold — ask the PM for the exact string][a specific numeric comparison operator and threshold — ask the PM for the exact string], "accuracy": 1[a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "altitude": 5.[a specific numeric comparison operator and threshold — ask the PM for the exact string], "altitude_accuracy": 2.[a specific numeric comparison operator and threshold — ask the PM for the exact string], "heading": 3.[a specific numeric comparison operator and threshold — ask the PM for the exact string], "heading_accuracy": 1.[a specific numeric comparison operator and threshold — ask the PM for the exact string], "floor": 2, "speed": 4.[a specific numeric comparison operator and threshold — ask the PM for the exact string], "speed_accuracy": 1.5, "is_mocked": true}},
            "expected_output": "latitude=52.1\nlongitude=5.4\ntimestamp_ms=1[a specific numeric comparison operator and threshold — ask the PM for the exact string][a specific numeric comparison operator and threshold — ask the PM for the exact string][a specific numeric comparison operator and threshold — ask the PM for the exact string]\naccuracy=1[a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string]\naltitude=5.[a specific numeric comparison operator and threshold — ask the PM for the exact string]\naltitude_accuracy=2.[a specific numeric comparison operator and threshold — ask the PM for the exact string]\nheading=3.[a specific numeric comparison operator and threshold — ask the PM for the exact string]\nheading_accuracy=1.[a specific numeric comparison operator and threshold — ask the PM for the exact string]\nfloor=2\nspeed=4.[a specific numeric comparison operator and threshold — ask the PM for the exact string]\nspeed_accuracy=1.5\nmocked=true\n"
        },
        {
            "input": {"op": "parse_position", "map": {"latitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "longitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "timestamp": [a specific numeric comparison operator and threshold — ask the PM for the exact string]}},
            "expected_output": "latitude=[a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string]\nlongitude=[a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string]\ntimestamp_ms=[a specific numeric comparison operator and threshold — ask the PM for the exact string]\naccuracy=[a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string]\naltitude=[a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string]\naltitude_accuracy=[a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string]\nheading=[a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string]\nheading_accuracy=[a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string]\nfloor=null\nspeed=[a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string]\nspeed_accuracy=[a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string]\nmocked=false\n"
        }
    ]
}
```

---

### Feature 4: Location Reading Value Equality

**As a developer**, I want two location readings to compare equal exactly when all their fields match, so I can use readings as values (deduplicate, compare, key) reliably.

**Expected Behavior / Usage:**

Two location readings are equal only when every field is equal: latitude, longitude, timestamp, accuracy, altitude, vertical (altitude) accuracy, heading, heading accuracy, building floor, speed, speed accuracy and the mocked-provider flag. A difference in any single one of these fields makes the two readings unequal. Equality is consistent with hashing: equal readings always produce the same hash, and readings that differ in any field produce different hashes. The output reports the equality verdict and whether the two hashes coincide.

**Test Cases:** `rcb_tests/public_test_cases/feature4_position_equality.json`

```json
{
    "description": "Compare two location readings for value equality. Two readings are equal only when every field matches: latitude, longitude, timestamp, accuracy, altitude, vertical accuracy, heading, heading accuracy, building floor, speed, speed accuracy and the mocked-provider flag. A difference in any single field makes the readings unequal, and equal readings always share the same hash while readings that differ in any field do not. The output reports both the equality verdict and whether the two hashes coincide.",
    "cases": [
        {
            "input": {"op": "position_equality",
                "first": {"latitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "longitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "timestamp": [a specific numeric comparison operator and threshold — ask the PM for the exact string], "accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "altitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "altitude_accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "heading": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "heading_accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "floor": [a specific numeric comparison operator and threshold — ask the PM for the exact string], "speed": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "speed_accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "is_mocked": false},
                "second": {"latitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "longitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "timestamp": [a specific numeric comparison operator and threshold — ask the PM for the exact string], "accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "altitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "altitude_accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "heading": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "heading_accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "floor": [a specific numeric comparison operator and threshold — ask the PM for the exact string], "speed": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "speed_accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "is_mocked": false}},
            "expected_output": "equal=true\nhash_equal=true\n"
        },
        {
            "input": {"op": "position_equality",
                "first": {"latitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "longitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "timestamp": [a specific numeric comparison operator and threshold — ask the PM for the exact string], "accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "altitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "altitude_accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "heading": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "heading_accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "floor": [a specific numeric comparison operator and threshold — ask the PM for the exact string], "speed": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "speed_accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "is_mocked": false},
                "second": {"latitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "longitude": 1.[a specific numeric comparison operator and threshold — ask the PM for the exact string], "timestamp": [a specific numeric comparison operator and threshold — ask the PM for the exact string], "accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "altitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "altitude_accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "heading": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "heading_accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "floor": [a specific numeric comparison operator and threshold — ask the PM for the exact string], "speed": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "speed_accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "is_mocked": false}},
            "expected_output": "equal=false\nhash_equal=false\n"
        },
        {
            "input": {"op": "position_equality",
                "first": {"latitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "longitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "timestamp": [a specific numeric comparison operator and threshold — ask the PM for the exact string], "accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "altitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "altitude_accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "heading": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "heading_accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "floor": [a specific numeric comparison operator and threshold — ask the PM for the exact string], "speed": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "speed_accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "is_mocked": false},
                "second": {"latitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "longitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "timestamp": [a specific numeric comparison operator and threshold — ask the PM for the exact string], "accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "altitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "altitude_accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "heading": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "heading_accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "floor": 1, "speed": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "speed_accuracy": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "is_mocked": false}},
            "expected_output": "equal=false\nhash_equal=false\n"
        }
    ]
}
```

---

### Feature 5: Location Reading Summary String

**As a developer**, I want a concise textual summary of a reading, so I can log or display where a device is at a glance.

**Expected Behavior / Usage:**

A location reading renders to a single human-readable line that states its latitude and longitude and deliberately omits all other fields. The output is exactly that summary line.

**Test Cases:** `rcb_tests/public_test_cases/feature5_position_summary.json`

```json
{
    "description": "Produce a short human-readable summary of a location reading. The summary states the reading's latitude and longitude in a single line and intentionally omits the other fields. The output is exactly that summary line.",
    "cases": [
        {
            "input": {"op": "position_summary", "map": {"latitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "longitude": [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], "timestamp": [a specific numeric comparison operator and threshold — ask the PM for the exact string]}},
            "expected_output": "Latitude: [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string], Longitude: [a specific numeric comparison operator and threshold — ask the PM for the exact string].[a specific numeric comparison operator and threshold — ask the PM for the exact string]\n"
        }
    ]
}
```

---

### Feature 6: Permission Code Mapping

**As a developer**, I want to convert the small integer permission code a platform returns into a canonical status token, so my code branches on meaningful states instead of magic numbers.

**Expected Behavior / Usage:**

The input is a single integer code. Codes `[a specific numeric comparison operator and threshold — ask the PM for the exact string]`, `1`, `2` and `3` map, in that order, to the permission statuses `denied`, `deniedForever`, `whileInUse` and `always`. Any other integer is invalid and must not be guessed: the conversion fails and is reported as a neutral error line that echoes the offending value back, so the caller knows exactly which value could not be converted.

**Test Cases:** `rcb_tests/public_test_cases/feature6_permission_from_code.json`

```json
{
    "description": "Map an integer permission code coming from the platform into the canonical permission status token. Codes [a specific numeric comparison operator and threshold — ask the PM for the exact string] through 3 map, in order, to the statuses denied, deniedForever, whileInUse and always. Any other integer is invalid: instead of guessing, the conversion fails and is reported as a neutral error line that echoes back the offending value.",
    "cases": [
        {"input": {"op": "permission_from_code", "value": [a specific numeric comparison operator and threshold — ask the PM for the exact string]}, "expected_output": "permission=denied\n"},
        {"input": {"op": "permission_from_code", "value": 3}, "expected_output": "permission=always\n"},
        {"input": {"op": "permission_from_code", "value": 4}, "expected_output": "error=invalid_permission\nvalue=4\n"}
    ]
}
```

---

### Feature 7: Canonical Status & Accuracy Catalogs

**As a developer**, I want a fixed, ordered catalog of the permission statuses and accuracy levels the system recognizes, so the ordinal protocol used to exchange them as integers is stable and well-defined.

**Expected Behavior / Usage:**

*7.1 Permission status catalog*

The system recognizes a fixed, ordered set of permission statuses. The output first states how many statuses exist, then lists each status token together with its zero-based ordinal position. The ordinal is the contract used whenever a permission value is exchanged as an integer. The full ordered set is: `denied`, `deniedForever`, `whileInUse`, `always`, `unableToDetermine`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_permission_catalog.json`

```json
{
    "description": "Report the catalog of permission statuses recognized by the system, in their canonical order. The output first states how many statuses exist, then lists each status token paired with its zero-based ordinal position; that ordinal is the contract used when permission values are exchanged as integers.",
    "cases": [
        {"input": {"op": "permission_catalog"}, "expected_output": "count=5\n[a specific numeric comparison operator and threshold — ask the PM for the exact string]=denied\n1=deniedForever\n2=whileInUse\n3=always\n4=unableToDetermine\n"}
    ]
}
```

*7.2 Accuracy level catalog*

The system recognizes a fixed, ordered set of desired-accuracy levels, ranging from coarsest to finest and ending with a reduced level. The output first states how many levels exist, then lists each level token together with its zero-based ordinal position. The full ordered set is: `lowest`, `low`, `medium`, `high`, `best`, `bestForNavigation`, `reduced`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_accuracy_catalog.json`

```json
{
    "description": "Report the catalog of location-accuracy levels recognized by the system, in their canonical order from coarsest to finest plus the reduced level. The output first states how many levels exist, then lists each level token paired with its zero-based ordinal position.",
    "cases": [
        {"input": {"op": "accuracy_catalog"}, "expected_output": "count=7\n[a specific numeric comparison operator and threshold — ask the PM for the exact string]=lowest\n1=low\n2=medium\n3=high\n4=best\n5=bestForNavigation\n6=reduced\n"}
    ]
}
```

---

### Feature 8: Domain Error Descriptions

**As a developer**, I want each domain failure to carry a clear, well-defined human-readable description, so users and logs get consistent, meaningful messages.

**Expected Behavior / Usage:**

*8.1 Error categories with an overridable default description*

Several error categories carry an optional caller-supplied message. When a non-empty message is supplied, the description is exactly that message; when the message is null or empty, a category-specific default description is returned instead. The categories with overridable defaults are: `activity_missing`, `permission_definitions_missing`, `permission_denied`, `permission_request_in_progress` and `position_update_failed`. Each has its own fixed default text (see the cases). The input names the category and optionally carries a message; the output is the resulting description line.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_error_messages.json`

```json
{
    "description": "Render the human-readable description of a domain error condition. Several error categories accept an optional custom message: when a non-empty message is supplied it is used verbatim, and when the message is null or empty a category-specific default description is returned instead. The input names the error category and optionally carries a message; the output is the resulting description line.",
    "cases": [
        {"input": {"op": "error_message", "type": "permission_denied", "message": null}, "expected_output": "Access to the location of the device is denied by the user.\n"},
        {"input": {"op": "error_message", "type": "permission_denied", "message": "Location permission denied."}, "expected_output": "Location permission denied.\n"},
        {"input": {"op": "error_message", "type": "activity_missing", "message": null}, "expected_output": "Activity is missing. This might happen when running a certain function from the background that requires a UI element (e.g. requesting permissions or enabling the location services).\n"}
    ]
}
```

*8.2 Error categories with a fixed description*

Two error categories carry no message and always render a single constant description: `already_subscribed` (raised when starting a second concurrent stream of position updates) and `location_service_disabled` (raised when the device's location service is turned off). The input names the category; the output is its constant description line.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_fixed_messages.json`

```json
{
    "description": "Render the human-readable description of a domain error condition that has a single fixed description and accepts no custom message. The input names the error category; the output is its constant description line.",
    "cases": [
        {"input": {"op": "error_message", "type": "already_subscribed"}, "expected_output": "The App is already listening to a stream of position updates. It is not possible to listen to more then one stream at the same time.\n"},
        {"input": {"op": "error_message", "type": "location_service_disabled"}, "expected_output": "The location service on the device is disabled.\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above (coordinate geodesy, location-reading value type and deserializer, permission/accuracy catalogs, and the domain error family). Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result to stdout, matching the per-feature contracts above. The request's `op` field selects behavior: `distance` and `bearing` perform the geodesy calculations; `parse_position` deserializes a reading from its `map`; `position_equality` compares two readings (`first`, `second`); `position_summary` renders a reading's summary line; `permission_from_code` maps an integer `value`; `permission_catalog` and `accuracy_catalog` report the ordered catalogs; `error_message` renders a domain error description from a `type` and optional `message`. Native exceptions thrown by the core (e.g. on invalid permission code or missing mandatory field) MUST be translated by the adapter into the neutral `error=[a specific numeric comparison operator and threshold — ask the PM for the exact string]category>` lines shown above rather than leaking host-language runtime details.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir [a specific numeric comparison operator and threshold — ask the PM for the exact string]subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/[a specific numeric comparison operator and threshold — ask the PM for the exact string]cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `[a specific numeric comparison operator and threshold — ask the PM for the exact string]cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- apply defaults consistent with the mockBD object construction in utils/create_mock_position.js
