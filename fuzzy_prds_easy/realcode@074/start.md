## Product Requirement Document

# Places Builder Toolkit — Fluent Construction of Place Data Models and Service Requests

## Project Goal

Build a fluent construction toolkit that lets developers assemble immutable place-domain value objects (photo metadata, plus codes, address components, places, opening periods, opening-hours schedules, autocomplete predictions) and immutable service-request objects (fetch-a-place, fetch-a-photo, find-current-place, autocomplete-predictions, text-search) through small, idiomatic builder entry points, without hand-writing verbose builder chains or repeating boilerplate at every call site.

---

## Background & Problem

Without this toolkit, developers constructing place-domain objects must call a multi-step builder for each object — obtain a builder, set each field, remember which arguments are mandatory versus optional, and call a terminal build step — and repeat that ceremony every time. This produces repetitive, error-prone boilerplate, makes optional configuration awkward (you either branch on every optional value or chain conditionally), and scatters knowledge of which fields are required across the codebase.

With this toolkit, each object has a single concise construction entry point: required values are passed positionally, and any number of optional fields are configured inside one trailing configuration block. The same pattern extends to service-request objects, including those that carry a cancellation handle whose lifetime is owned by the request. The result is compact, readable construction code with the required/optional contract expressed once, in one place.

---

## Background terminology (shared by all features)

- **Cancellation token**: a request may carry a cancellation handle drawn from a cancellation source. The handle exposes a boolean "cancellation requested" state. Cancelling the source must flip the handle attached to the request from not-requested to requested — this proves the request holds the live handle rather than a detached copy.
- **Place field**: an enumerated name of a piece of place data to request (e.g. `NAME`, `ADDRESS`). A request records the ordered list of requested field names.
- **Coordinate**: a latitude/longitude pair given as decimal degrees.
- **Location bias**: a geographic area used to bias results, supplied either as a *rectangular* area (southwest + northeast corner coordinates) or a *circular* area (center coordinate + radius in meters).

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has two clear responsibility groups (data-model construction and service-request construction) plus an execution adapter. Keep the core construction helpers logically grouped and the execution adapter physically separate from them. Do not collapse everything into one file if the domain warrants separation, and do not over-engineer trivial helpers.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases in "Core Features" are a **black-box contract for the execution adapter**, not the internal shape of the core construction helpers. The core construction logic MUST NOT know about JSON or stdout. The execution adapter alone translates a JSON command into idiomatic construction calls and formats the resulting object's observable state to stdout.

3. **Adherence to SOLID Design Principles:** Separate JSON parsing, command routing, construction, and output formatting into distinct units. The set of constructible kinds must be open for extension (adding a new kind must not require rewriting existing ones). Keep each construction entry point small and cohesive. High-level routing should depend on an abstraction over "construct and render", not on concrete formatting details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** Each construction entry point should take mandatory values up front and accept optional configuration through one trailing block, hiding the underlying multi-step builder.
   - **Resilience:** Invalid input (e.g. an unrecognized enumerated value) must surface as a normalized, language-neutral error category rather than leaking host-runtime fault details.

---

## Core Features

### Feature 1: Place Data-Model Construction

**As a developer**, I want single-call construction entry points for the place value objects, so I can assemble immutable domain data with required fields up front and optional fields configured in one block, without repeating builder ceremony.

**Expected Behavior / Usage:**

Each leaf below constructs one value-object kind. Required values are mandatory inputs; optional values, when omitted, fall back to the object's documented defaults. The adapter renders the constructed object's observable getters as `key=value` lines.

*1.1 Photo metadata — reference plus optional attribution and dimensions*

Construct photo metadata from a required photo reference string. Optionally set an attribution text, a width, and a height (pixels). When attribution is omitted it defaults to an empty string; when width or height are omitted they default to `0`. Output reports `attributions`, `width`, `height`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_photo_metadata.json`

```json
{
    "description": "Build photo metadata from a required photo reference, optionally setting attribution text and pixel dimensions. With no optional fields the dimensions default to zero and the attribution text defaults to empty. Output reports the resulting attribution text, width and height.",
    "cases": [
        {
            "input": {"kind": "photo_metadata", "photo_reference": "reference"},
            "expected_output": "attributions=\nwidth=0\nheight=0\n"
        },
        {
            "input": {"kind": "photo_metadata", "photo_reference": "reference", "attributions": "attributions", "width": 100, "height": 100},
            "expected_output": "attributions=attributions\nwidth=100\nheight=100\n"
        }
    ]
}
```

*1.2 Plus code — compound and global codes*

Construct a plus code by assigning its compound code and global code strings. Output reports `compound_code` and `global_code`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_plus_code.json`

```json
{
    "description": "Build a plus code object by assigning its compound code and global code. Output echoes both codes back.",
    "cases": [
        {
            "input": {"kind": "plus_code", "compound_code": "ABC", "global_code": "DEF"},
            "expected_output": "compound_code=ABC\nglobal_code=DEF\n"
        }
    ]
}
```

*1.3 Address component — name, type tags, optional short name*

Construct an address component from a required name and a required non-empty list of type tags. Optionally set a short name; when omitted it is reported as `none`. Output reports `name`, `short_name`, and the `types` list.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_address_component.json`

```json
{
    "description": "Build an address component from a required name and a required list of type tags, with an optional short name. When the short name is omitted it is reported as absent. Output reports the name, short name, and types.",
    "cases": [
        {
            "input": {"kind": "address_component", "name": "Main Street", "types": ["street_address"]},
            "expected_output": "name=Main Street\n[use the provided default for when short_name is omitted]\ntypes=[street_address]\n"
        },
        {
            "input": {"kind": "address_component", "name": "Main Street", "types": ["street_address"], "short_name": "Main St."},
            "expected_output": "name=Main Street\nshort_name=Main St.\ntypes=[street_address]\n"
        }
    ]
}
```

*1.4 Place — address plus structured address components*

Construct a place by assigning a free-form address line and a list of structured address components, where each component is itself built from a name, a list of type tags, and an optional short name. Output reports `address`, the `address_component_count`, and for each component its indexed `name`, `short_name`, and `types`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_place.json`

```json
{
    "description": "Build a place by assigning a free-form address line and a list of structured address components (each itself built from name, types and optional short name). Output reports the address, the number of attached components, and each component's name, short name and types.",
    "cases": [
        {
            "input": {"kind": "place", "address": "address", "address_components": [{"name": "Main Street", "types": ["street_address"], "short_name": "Main St."}]},
            "expected_output": "address=address\naddress_component_count=1\naddress_component[0].name=Main Street\naddress_component[0].short_name=Main St.\naddress_component[0].types=[street_address]\n"
        }
    ]
}
```

*1.5 Opening period — open and close moments*

Construct a single opening-period by assigning its opening moment and its closing moment. A moment is a day-of-week (e.g. `MONDAY`) plus a time-of-day given as hour and minute. Output reports each boundary's `day` and zero-padded `HH:MM` time.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_period.json`

```json
{
    "description": "Build an opening-period by assigning its opening and closing moments. Each moment is a day-of-week plus a time-of-day (hour and minute). Output reports the day and the zero-padded hour:minute of each boundary.",
    "cases": [
        {
            "input": {"kind": "period", "open": {"day": "TUESDAY", "hour": 0, "minute": 0}, "close": {"day": "MONDAY", "hour": 0, "minute": 0}},
            "expected_output": "open.day=TUESDAY\nopen.time=00:00\nclose.day=MONDAY\nclose.time=00:00\n"
        }
    ]
}
```

*1.6 Opening hours — periods and weekday text*

Construct an opening-hours schedule by assigning a list of opening-periods plus a list of human-readable weekday text lines. A period within the list may set only a closing boundary, leaving its opening boundary absent (reported as `none`). Output reports `period_count`, each period's indexed boundaries, and the `weekday_text` list.

**Test Cases:** `rcb_tests/public_test_cases/feature1_6_opening_hours.json`

```json
{
    "description": "Build an opening-hours object by assigning a list of opening-periods plus a list of human-readable weekday text lines. A period may set only a closing boundary, leaving the opening boundary absent. Output reports the period count, each period's boundaries, and the weekday text list.",
    "cases": [
        {
            "input": {"kind": "opening_hours", "periods": [{"close": {"day": "MONDAY", "hour": 0, "minute": 0}}], "weekday_text": ["Monday"]},
            "expected_output": "period_count=1\nperiod[0].open=none\nperiod[0].close.day=MONDAY\nperiod[0].close.time=00:00\nweekday_text=[Monday]\n"
        }
    ]
}
```

*1.7 Autocomplete prediction — place id plus optional place types*

Construct an autocomplete prediction from a required place identifier, optionally assigning a list of place-type tags. Output reports `place_id` and the `place_types` list.

**Test Cases:** `rcb_tests/public_test_cases/feature1_7_autocomplete_prediction.json`

```json
{
    "description": "Build an autocomplete prediction from a required place identifier and an optional list of place-type tags. Output reports the place identifier and the assigned place types.",
    "cases": [
        {
            "input": {"kind": "autocomplete_prediction", "place_id": "placeId", "place_types": ["AQUARIUM"]},
            "expected_output": "place_id=placeId\nplace_types=[AQUARIUM]\n"
        }
    ]
}
```

---

### Feature 2: Service-Request Construction

**As a developer**, I want single-call construction entry points for the service-request objects, so I can build immutable request descriptors with their mandatory parameters up front and any optional knobs (cancellation token, session token, filters, location bias, ranking) in one trailing block.

**Expected Behavior / Usage:**

Each leaf constructs one request kind. Required parameters are mandatory; optional knobs default away when omitted. Where a cancellation token is requested, the adapter proves the request holds the live handle by reporting the handle's "cancellation requested" state before and after the owning source is cancelled (`false` then `true`). When a token is not requested, the output reports it as `absent`.

*2.1 Fetch-a-place request — id, fields, optional cancellation and session tokens*

Construct a request to fetch one place by its identifier and a list of requested fields. Optionally attach a cancellation token and/or a session token. Output always reports `place_id` and `place_fields`. When the session token is requested, output reports `[default session token handling behavior]` (the attached token is the same instance supplied); otherwise `[default session token handling behavior]`. When the cancellation token is requested, output reports the before/after cancellation state; otherwise `cancellation_token=absent`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_fetch_place_request.json`

```json
{
    "description": "Build a request to fetch a single place by its identifier and a list of requested fields. Optional extras: a cancellation token and a session token. When the cancellation token is requested, output shows the cancellation state flips from not-requested to requested after the source is cancelled, proving the same token instance is wired into the request. When the session token is requested, output confirms the same token instance is attached. When either extra is omitted it is reported as absent.",
    "cases": [
        {
            "input": {"kind": "fetch_place_request", "place_id": "placeId", "place_fields": ["NAME"]},
            "expected_output": "place_id=placeId\nplace_fields=[NAME]\n[default session token handling behavior]\ncancellation_token=absent\n"
        },
        {
            "input": {"kind": "fetch_place_request", "place_id": "placeId", "place_fields": ["NAME"], "cancellation_token": true, "session_token": true},
            "expected_output": "place_id=placeId\nplace_fields=[NAME]\n[default session token handling behavior]\ncancellation_requested_before_cancel=false\ncancellation_requested_after_cancel=true\n"
        }
    ]
}
```

*2.2 Fetch-a-photo request — photo metadata, optional max size and cancellation token*

Construct a request to fetch a photo binary from its photo metadata, optionally bounding the result with a maximum width and height, and optionally attaching a cancellation token. Output reports the carried photo metadata (`attributions`, `width`, `height`), the `max_width` / `max_height` (each `none` when omitted), and the cancellation token (before/after state when requested, else `absent`).

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_fetch_photo_request.json`

```json
{
    "description": "Build a request to fetch a photo binary from its photo metadata, optionally bounding the returned image with a maximum width and height, and optionally attaching a cancellation token. The request echoes back the supplied photo metadata (attribution text, width, height). When the max-size bounds are omitted they are reported as absent. When the cancellation token is requested, output shows its state flips to requested after the source is cancelled.",
    "cases": [
        {
            "input": {"kind": "fetch_photo_request", "photo_metadata": {"photo_reference": "reference"}},
            "expected_output": "photo_metadata.attributions=\nphoto_metadata.width=0\nphoto_metadata.height=0\nmax_width=none\nmax_height=none\ncancellation_token=absent\n"
        },
        {
            "input": {"kind": "fetch_photo_request", "photo_metadata": {"photo_reference": "reference"}, "max_width": 100, "max_height": 100, "cancellation_token": true},
            "expected_output": "photo_metadata.attributions=\nphoto_metadata.width=0\nphoto_metadata.height=0\nmax_width=100\nmax_height=100\ncancellation_requested_before_cancel=false\ncancellation_requested_after_cancel=true\n"
        }
    ]
}
```

*2.3 Find-current-place request — fields and optional cancellation token*

Construct a request to find the device's approximate current place from a list of requested fields, optionally attaching a cancellation token. Output reports `place_fields` and the cancellation token (before/after state when requested, else `absent`).

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_find_current_place_request.json`

```json
{
    "description": "Build a request to find the device's approximate current place, given a list of requested fields and an optional cancellation token. Output reports the requested fields; when the cancellation token is requested it shows the cancellation state flips from not-requested to requested after the source is cancelled, otherwise it is reported as absent.",
    "cases": [
        {
            "input": {"kind": "find_current_place_request", "place_fields": ["NAME"]},
            "expected_output": "place_fields=[NAME]\ncancellation_token=absent\n"
        },
        {
            "input": {"kind": "find_current_place_request", "place_fields": ["NAME"], "cancellation_token": true},
            "expected_output": "place_fields=[NAME]\ncancellation_requested_before_cancel=false\ncancellation_requested_after_cancel=true\n"
        }
    ]
}
```

*2.4 Autocomplete-predictions request — query, filters, rectangular bias, cancellation token*

Construct a request for autocomplete predictions, configuring a free-text query, a list of country filters, a list of place-type filters, a rectangular location bias (southwest + northeast corners), and a cancellation token. Output reports `query`, `countries`, `types_filter`, the rectangular bias (`type`, `southwest`, `northeast` as `lat,lng`), and the before/after cancellation state.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_autocomplete_predictions_request.json`

```json
{
    "description": "Build a request for autocomplete predictions, configuring a free-text query, a list of country filters, a list of place-type filters, a rectangular location bias (defined by southwest and northeast corner coordinates), and a cancellation token. Output reports the query, country list, type filters, the rectangular bias corners, and the cancellation state flipping to requested after the source is cancelled.",
    "cases": [
        {
            "input": {"kind": "autocomplete_predictions_request", "query": "query", "countries": ["USA"], "types_filter": ["ESTABLISHMENT"], "location_bias": {"southwest": {"lat": 1.0, "lng": 1.0}, "northeast": {"lat": 2.0, "lng": 2.0}}, "cancellation_token": true},
            "expected_output": "query=query\ncountries=[USA]\ntypes_filter=[establishment]\nlocation_bias.type=rectangular\nlocation_bias.southwest=1.0,1.0\nlocation_bias.northeast=2.0,2.0\ncancellation_requested_before_cancel=false\ncancellation_requested_after_cancel=true\n"
        }
    ]
}
```

*2.5 Text-search request (basic) — query and fields only*

Construct a text-search request from a query string and a list of requested fields, with no optional knobs. Output reports `text_query` and `place_fields`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_search_by_text_request_basic.json`

```json
{
    "description": "Build a text-search request from a query string and a list of requested fields, with no extra options. Output reports the query and the requested fields.",
    "cases": [
        {
            "input": {"kind": "search_by_text_request", "text_query": "test query", "place_fields": ["NAME"]},
            "expected_output": "text_query=test query\nplace_fields=[NAME]\n"
        }
    ]
}
```

*2.6 Text-search request (full) — included type, open-now, min rating, price levels, ranking, region, circular bias*

Construct a fully-configured text-search request: query string, requested fields, an included place-type string, an open-now boolean, a minimum rating, a set of named price levels, a ranking preference, a region code, and a circular location bias (center coordinate + radius in meters). The named price levels `FREE`, `INEXPENSIVE`, `MODERATE`, `EXPENSIVE`, `VERY_EXPENSIVE` map to integer wire values `0`, `1`, `2`, `3`, `4` respectively, and the request stores those integer wire values. Output reports each configured option, the price levels as their integer wire values, and the circular bias (`type`, `center` as `lat,lng`, `radius`).

**Test Cases:** `rcb_tests/public_test_cases/feature2_6_search_by_text_request_full.json`

```json
{
    "description": "Build a fully-configured text-search request: query string, requested fields, an included place-type, an open-now flag, a minimum rating, a set of named price levels, a ranking preference, a region code, and a circular location bias (center coordinate plus radius in meters). The named price levels FREE/INEXPENSIVE/MODERATE/EXPENSIVE/VERY_EXPENSIVE map to integer wire values 0..4 respectively. Output reports each configured option, the price levels as their integer wire values, and the circular bias center and radius.",
    "cases": [
        {
            "input": {"kind": "search_by_text_request", "text_query": "test query", "place_fields": ["NAME", "ADDRESS"], "included_type": "national_park", "is_open_now": true, "min_rating": 4.0, "price_levels": ["MODERATE", "EXPENSIVE"], "rank_preference": "RELEVANCE", "region_code": "US", "location_bias": {"center": {"lat": 42.193893370553916, "lng": -122.7088890892941}, "radius": 1500.0}},
            "expected_output": "text_query=test query\nplace_fields=[NAME, ADDRESS]\nincluded_type=national_park\nis_open_now=true\nmin_rating=4.0\nprice_levels=[2, 3]\nrank_preference=RELEVANCE\nregion_code=US\nlocation_bias.type=circular\nlocation_bias.center=42.193893370553916,-122.7088890892941\nlocation_bias.radius=1500.0\n"
        },
        {
            "input": {"kind": "search_by_text_request", "text_query": "shops", "place_fields": ["NAME"], "price_levels": ["INEXPENSIVE", "VERY_EXPENSIVE"]},
            "expected_output": "text_query=shops\nplace_fields=[NAME]\n[the predefined mapping for these price categories]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured set of fluent construction entry points for the place data-model objects (Feature 1) and service-request objects (Feature 2), grouped by responsibility, each taking mandatory values up front and optional configuration through one trailing block, returning immutable objects. The named price-level enumeration maps to its integer wire values. The core knows nothing about JSON or stdout.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON command object from stdin, routes on its `kind`, invokes the matching construction entry point, and prints the constructed object's observable state to stdout as `key=value` lines matching the per-leaf contracts above. Invalid enumerated values surface as a normalized, language-neutral `error=<category>` line. This adapter is separate from the core construction logic.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_photo_metadata.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_photo_metadata@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- conforms to the same list structure convention as the autocomplete module documentation
