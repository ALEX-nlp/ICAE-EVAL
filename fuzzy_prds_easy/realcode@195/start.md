## Product Requirement Document

# Web Mapping Services Client - Request Construction and Response Handling

## Project Goal

Build a web mapping services client that allows developers to construct authenticated geocoding, routing, places, roads, elevation, time zone, geolocation, address validation, and static map requests without manually encoding URLs, signing requests, normalizing coordinates, or parsing common response envelopes.

---

## Background & Problem

Without this library/tool, developers are forced to hand-build query strings, normalize coordinates, join multi-value parameters, sign credentialed URLs, manage tracking headers, and interpret service error responses for each mapping endpoint separately. This leads to repetitive code, inconsistent escaping, fragile request authentication, and hard-to-maintain integrations.

With this library/tool, developers provide structured request data and receive predictable routed HTTP requests, response summaries, and language-neutral error output through a small execution adapter.

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

### Feature 1.1: Coordinate Text Serialization

**As a developer**, I want to format a single coordinate-like input into service-ready text, so I can pass addresses or coordinates consistently to request builders.

**Expected Behavior / Usage:**

The input is a JSON object with `action` set to `[a list of known text extraction feature constants]` and a `value` that is either a latitude/longitude object, a two-item numeric coordinate, or an already formatted coordinate string. The output is one line `value=<latitude>,<longitude>` when the input is valid. Invalid non-location inputs produce `error=invalid_type`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_[a list of known text extraction feature constants].json`

```json
{
    "description": "Coordinates supplied as structured latitude/longitude data or as already formatted text are rendered as comma-separated latitude and longitude text.",
    "cases": [
        {
            "input": {
                "action": "[a list of known text extraction feature constants]",
                "value": {
                    "lat": 1,
                    "lng": 2
                }
            },
            "expected_output": "value=1,2\n"
        }
    ]
}
```

---

### Feature 1.2: Location Sequence Serialization

**As a developer**, I want to format multiple locations into one route/search parameter, so I can send multi-point requests without manually joining values.

**Expected Behavior / Usage:**

The input is a JSON object with `action` set to `[a list of known text extraction feature constants]` and `locations` containing either a list of coordinate/address values or an already formatted sequence. The output is one line `value=<location>|<location>...`, where each structured coordinate is normalized before joining.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_[a list of known text extraction feature constants].json`

```json
{
    "description": "A sequence of locations is rendered as pipe-separated coordinate or address values, preserving each location value after coordinate normalization.",
    "cases": [
        {
            "input": {
                "action": "[a list of known text extraction feature constants]",
                "locations": [
                    {
                        "lat": 1,
                        "lng": 2
                    },
                    {
                        "lat": 1,
                        "lng": 2
                    }
                ]
            },
            "expected_output": "value=1,2|1,2\n"
        }
    ]
}
```

---

### Feature 1.3: Component Filter Serialization

**As a developer**, I want to format component filters into service-ready text, so I can express component restrictions without hand-building filter strings.

**Expected Behavior / Usage:**

The input is a JSON object with `action` set to `[a list of known text extraction feature constants]` and `components` as a key/value object. Scalar values render as `key:value`; list values expand into repeated `key:value` fragments. Fragments are pipe-separated in deterministic order. Non-object component input produces `error=invalid_type`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_[a list of known text extraction feature constants].json`

```json
{
    "description": "Component filters are rendered as key:value fragments joined by pipes, with multi-valued filters expanded into repeated key:value fragments.",
    "cases": [
        {
            "input": {
                "action": "[a list of known text extraction feature constants]",
                "components": {
                    "country": "US"
                }
            },
            "expected_output": "value=country:US\n"
        }
    ]
}
```

---

### Feature 1.4: Route Polyline Conversion

**As a developer**, I want to decode and re-encode compact route geometry, so I can store and transmit route paths in compact text form.

**Expected Behavior / Usage:**

The input is a JSON object with `action` set to `[a list of known text extraction feature constants]`, `mode` set to `decode` or `round_trip`, and a compact encoded `polyline`. Decode mode outputs the point count plus first and last coordinates. Round-trip mode decodes and re-encodes the route and outputs `polyline=<encoded text>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_[a list of known text extraction feature constants].json`

```json
{
    "description": "Encoded route polylines can be decoded to geographic points, and decoded points can be encoded back to the same compact route string.",
    "cases": [
        {
            "input": {
                "action": "[a list of known text extraction feature constants]",
                "mode": "decode",
                "polyline": "gcneIpgxzRcDnBoBlEHzKjBbHlG`@`IkDxIiKhKoMaLwTwHeIqHuAyGXeB~Ew@fFjAtIzExF"
            },
            "expected_output": "count=17\nfirst=53.48932,-104.16777\nlast=53.48935,-104.16773\n"
        }
    ]
}
```

---

### Feature 2.1: Request Authentication Parameters

**As a developer**, I want to attach API-key or signed client credentials to request paths, so I can authenticate outgoing service calls consistently.

**Expected Behavior / Usage:**

The input is a JSON object with `action` set to `[a list of known text extraction feature constants]`, a request `path`, query `params`, and credential fields. API-key authentication appends a `key` parameter. Client-credential authentication appends optional `channel`, `client`, and deterministic `signature` parameters. Invalid credential values produce `error=invalid_argument`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_request_authentication.json`

```json
{
    "description": "Outgoing service requests include either an API key query parameter or client credentials with a deterministic URL signature and optional tracking channel.",
    "cases": [
        {
            "input": {
                "action": "[a list of known text extraction feature constants]",
                "api_key": "AIzaasdf",
                "path": "/test",
                "params": {
                    "param": "param"
                },
                "accepts_client_credentials": false
            },
            "expected_output": "path_query=/test?param=param&key=AIzaasdf\n"
        }
    ]
}
```

---

### Feature 2.2: Experience Header State

**As a developer**, I want to set, read, and clear a request experience identifier, so I can control the experience tracking header for future requests.

**Expected Behavior / Usage:**

The input is a JSON object with `action` set to `[a list of known text extraction feature constants]`, optional initial `experience_id`, and ordered `actions`. Set actions accept one or more values and store them as a comma-separated header value. Clear actions remove the value. The output is `experience_id=<value>` with an empty value when no identifier is set.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_[a list of known text extraction feature constants]_value.json`

```json
{
    "description": "A request experience identifier can be initialized, replaced with one or more values, read back as a comma-separated header value, and cleared.",
    "cases": [
        {
            "input": {
                "action": "[a list of known text extraction feature constants]",
                "api_key": "AIzaasdf",
                "experience_id": "Exp1",
                "actions": []
            },
            "expected_output": "experience_id=Exp1\n"
        }
    ]
}
```

---

### Feature 2.3: HTTP Failure Normalization

**As a developer**, I want to surface transport status failures as stable contract output, so I can handle service failures without depending on runtime exception formatting.

**Expected Behavior / Usage:**

The input is a JSON object with `action` set to `[a list of known text extraction feature constants]`, a target URL, path, parameters, and mocked HTTP status. A non-200 response outputs `error=http_error` and `status_code=<code>`; no host-language exception type or runtime message is exposed.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_http_failure_normalization.json`

```json
{
    "description": "Non-success HTTP responses from a service request are surfaced as a language-neutral HTTP error category with the response status code.",
    "cases": [
        {
            "input": {
                "action": "[a list of known text extraction feature constants]",
                "api_key": "AIzaasdf",
                "base_url": "[base domain paths for routing services]/geocode/json",
                "path": "/maps/api/geocode/json",
                "params": {
                    "address": "Foo"
                },
                "status": 404
            },
            "expected_output": "error=transport_error\n"
        }
    ]
}
```

---

### Feature 3.1: Forward Geocoding Request Construction

**As a developer**, I want to turn address-like search inputs into a geocoding HTTP request, so I can verify the exact request sent to the remote service.

**Expected Behavior / Usage:**

The input is a JSON object with `action` set to `[a list of known text extraction feature constants]` and a `request` object containing an address, bounds, region, component filters, place identifier, or a combination allowed by the service. The output includes `method=GET`, `status=200`, the canonical routed URL with encoded query parameters, and `result_count=0` for the parsed response.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_forward_geocoding_requests.json`

```json
{
    "description": "Forward geocoding converts addresses, region hints, component filters, bounds, and place identifiers into a GET request and returns the parsed result count.",
    "cases": [
        {
            "input": {
                "action": "[a list of known text extraction feature constants]",
                "request": {
                    "address": "Sydney"
                }
            },
            "expected_output": "method=GET\nstatus=200\nurl=[base domain paths for routing services]/geocode/json?address=Sydney&key=AIzaasdf\nresult_count=0\n"
        }
    ]
}
```

---

### Feature 3.2: Reverse Geocoding Request Construction

**As a developer**, I want to turn coordinates and optional filters into a reverse-geocoding HTTP request, so I can verify both request routing and response extraction.

**Expected Behavior / Usage:**

The input is a JSON object with `action` set to `[a list of known text extraction feature constants]` and a `request` object containing `latlng` plus optional location type filters, result type filters, or an address descriptor flag. The output includes the GET method, HTTP status, canonical routed URL, and either `result_count=0` or an address descriptor summary when descriptors are requested.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_reverse_geocoding_requests.json`

```json
{
    "description": "Reverse geocoding converts coordinates plus optional result filters and address descriptor flags into a GET request and returns the parsed response summary.",
    "cases": [
        {
            "input": {
                "action": "[a list of known text extraction feature constants]",
                "request": {
                    "latlng": [
                        -33.8674869,
                        151.2069902
                    ]
                }
            },
            "expected_output": "method=GET\nstatus=200\nurl=[base domain paths for routing services]/geocode/json?key=AIzaasdf&latlng=-33.8674869%2C151.2069902\nresult_count=0\n"
        }
    ]
}
```

---

### Feature 4: Directions Request Construction

**As a developer**, I want to turn route parameters into a directions HTTP request, so I can request routes with travel options without manually assembling URLs.

**Expected Behavior / Usage:**

The input is a JSON object with `action` set to `[a list of known text extraction feature constants]` and a `request` object containing origin, destination, and optional mode, avoid list, units, region, language, waypoints, waypoint optimization, and alternatives. Valid inputs output the GET method, status, canonical routed URL, and `route_count=0`. Unsupported travel modes output `error=invalid_argument`. A zero-results service response still returns a successful route count of zero.

**Test Cases:** `rcb_tests/public_test_cases/feature4_[a list of known text extraction feature constants]s.json`

```json
{
    "description": "Directions requests convert origins, destinations, route options, waypoints, transit times, and region/language options into a GET request and return the route count.",
    "cases": [
        {
            "input": {
                "action": "[a list of known text extraction feature constants]",
                "request": {
                    "origin": "Sydney",
                    "destination": "Melbourne"
                }
            },
            "expected_output": "method=GET\nstatus=200\nurl=[base domain paths for routing services]/directions/json?destination=Melbourne&key=AIzaasdf&origin=Sydney\nroute_count=0\n"
        }
    ]
}
```

---

### Feature 5: Distance Matrix Request Construction

**As a developer**, I want to turn origin/destination collections into a matrix HTTP request, so I can calculate many origin-destination combinations through one routed request.

**Expected Behavior / Usage:**

The input is a JSON object with `action` set to `[a list of known text extraction feature constants]` and a `request` object containing origin and destination lists plus optional language, mode, and travel options. Addresses, coordinates, and place identifiers are normalized and pipe-joined. The output includes the GET method, status, canonical routed URL, and `row_count=0`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_[a list of known text extraction feature constants]s.json`

```json
{
    "description": "Distance matrix requests convert origin and destination lists, mixed coordinate/address inputs, place identifiers, and travel options into a GET request and return the row count.",
    "cases": [
        {
            "input": {
                "action": "[a list of known text extraction feature constants]",
                "request": {
                    "origins": [
                        "Vancouver BC",
                        "Seattle"
                    ],
                    "destinations": [
                        "San Francisco",
                        "Victoria BC"
                    ],
                    "language": "fr-FR",
                    "mode": "bicycling"
                }
            },
            "expected_output": "method=GET\nstatus=200\nurl=[base domain paths for routing services]/distancematrix/json?destinations=San+Francisco%7CVictoria+BC&key=AIzaasdf&language=fr-FR&mode=bicycling&origins=Vancouver+BC%7CSeattle\nrow_count=0\n"
        }
    ]
}
```

---

### Feature 6: Elevation Request Construction

**As a developer**, I want to turn locations or sampled paths into elevation HTTP requests, so I can retrieve elevation data for points or path samples.

**Expected Behavior / Usage:**

The input is a JSON object with `action` set to `[a list of known text extraction feature constants]`. Point mode provides `locations`; sampled-path mode sets `along_path` to true and provides `path` plus `samples`. Valid inputs output the GET method, status, canonical routed URL, and `result_count=0`. A sampled path with too few points outputs `error=api_error` with the domain status.

**Test Cases:** `rcb_tests/public_test_cases/feature6_[a list of known text extraction feature constants]s.json`

```json
{
    "description": "Elevation requests encode one or more locations, or a sampled path, into a GET request and return the result count; too-short sampled paths are rejected.",
    "cases": [
        {
            "input": {
                "action": "[a list of known text extraction feature constants]",
                "request": {
                    "locations": [
                        40.714728,
                        -73.998672
                    ]
                }
            },
            "expected_output": "error=invalid_type\n"
        }
    ]
}
```

---

### Feature 7.1: Place Lookup and Detail Requests

**As a developer**, I want to construct place lookup and detail requests with field controls, so I can fetch candidate or detail records with explicit response fields.

**Expected Behavior / Usage:**

The input is a JSON object with `action` set to `[a list of known text extraction feature constants]` or `place_detail_request` and a `request` object containing the lookup text or place identifier plus field lists and optional language, bias, and review options. Valid inputs output the GET method, status, canonical routed URL, and a parsed response summary. Invalid input types or unsupported fields output `error=invalid_argument`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_place_find_and_detail_requests.json`

```json
{
    "description": "Place lookup requests convert text search parameters or place detail parameters, including field lists, language, location bias, review options, and identifiers into GET requests.",
    "cases": [
        {
            "input": {
                "action": "[a list of known text extraction feature constants]",
                "request": {
                    "input": "restaurant",
                    "input_type": "textquery",
                    "fields": [
                        "business_status",
                        "geometry/location",
                        "place_id"
                    ],
                    "location_bias": "point:90,90",
                    "language": "en-AU"
                }
            },
            "expected_output": "method=GET\nstatus=200\nurl=[base domain paths for routing services]/place/findplacefromtext/json?fields=business_status%2Cgeometry%2Flocation%2Cplace_id&input=restaurant&inputtype=textquery&key=AIzaasdf&language=en-AU&locationbias=point%3A90%2C90\ncandidate_count=0\n"
        }
    ]
}
```

---

### Feature 7.2: Place Search Requests

**As a developer**, I want to construct text and nearby place search requests, so I can search places with geographic and price constraints.

**Expected Behavior / Usage:**

The input is a JSON object with `action` set to `[a list of known text extraction feature constants]` or `nearby_search_request` and a `request` object containing search text or nearby-search constraints. Valid inputs output the GET method, status, canonical routed URL, and `result_count=0`. Nearby searches missing required location/radius/rank combinations output `error=invalid_argument`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_place_search_requests.json`

```json
{
    "description": "Text and nearby place search requests convert search text, coordinates, radius, price range, language, region, type, rank, keyword, and open-now flags into GET requests.",
    "cases": [
        {
            "input": {
                "action": "[a list of known text extraction feature constants]",
                "request": {
                    "query": "restaurant",
                    "location": [
                        -33.86746,
                        151.20709
                    ],
                    "radius": 100,
                    "region": "AU",
                    "language": "en-AU",
                    "min_price": 1,
                    "max_price": 4,
                    "open_now": true,
                    "type": "liquor_store"
                }
            },
            "expected_output": "method=GET\nstatus=200\nurl=[base domain paths for routing services]/place/textsearch/json?key=AIzaasdf&language=en-AU&location=-33.86746%2C151.20709&maxprice=4&minprice=1&opennow=true&query=restaurant&radius=100&region=AU&type=liquor_store\nresult_count=0\n"
        }
    ]
}
```

---

### Feature 7.3: Place Autocomplete Requests

**As a developer**, I want to construct place autocomplete prediction requests, so I can fetch predictions for partial user input.

**Expected Behavior / Usage:**

The input is a JSON object with `action` set to `[a list of known text extraction feature constants]` or `query_[a list of known text extraction feature constants]` and a `request` object containing partial input plus optional session token, offsets, origin, location bias, radius, language, type, components, and strict bounds. The output includes the GET method, status, canonical routed URL, and `prediction_count=0`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_3_place_[a list of known text extraction feature constants]s.json`

```json
{
    "description": "Autocomplete requests convert partial user input, session token, offsets, geographic biasing, component filters, language, and type restrictions into prediction GET requests.",
    "cases": [
        {
            "input": {
                "action": "[a list of known text extraction feature constants]",
                "request": {
                    "input_text": "Google",
                    "session_token": "test-session-token",
                    "offset": 3,
                    "origin": [
                        -33.86746,
                        151.20709
                    ],
                    "location": [
                        -33.86746,
                        151.20709
                    ],
                    "radius": 100,
                    "language": "en-AU",
                    "types": "geocode",
                    "components": {
                        "country": "au"
                    },
                    "strict_bounds": true
                }
            },
            "expected_output": "method=GET\nstatus=200\nurl=[base domain paths for routing services]/place/autocomplete/json?components=country%3Aau&input=Google&key=AIzaasdf&language=en-AU&location=-33.86746%2C151.20709&offset=3&origin=-33.86746%2C151.20709&radius=100&sessiontoken=test-session-token&strictbounds=true&types=geocode\nprediction_count=0\n"
        }
    ]
}
```

---

### Feature 8: Roads Request Construction

**As a developer**, I want to construct road snapping and speed-limit requests, so I can map coordinates to roads and query speed limits.

**Expected Behavior / Usage:**

The input is a JSON object with `action` set to `[a list of known text extraction feature constants]`, a `kind` selecting snap-to-road, nearest-road, snapped speed limits, or place-ID speed limits, and a `request` object containing points, paths, or place identifiers. Valid inputs output the GET method, status, canonical routed URL, and the parsed snapped-point or speed-limit summary. Credential modes not accepted by a selected endpoint output `error=invalid_argument`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_[a list of known text extraction feature constants]s.json`

```json
{
    "description": "Roads requests convert points, paths, and place identifiers into the proper roads endpoint and return the relevant snapped point or speed-limit summary.",
    "cases": [
        {
            "input": {
                "action": "[a list of known text extraction feature constants]",
                "kind": "snap",
                "request": {
                    "path": [
                        40.714728,
                        -73.998672
                    ]
                }
            },
            "expected_output": "error=invalid_type\n"
        }
    ]
}
```

---

### Feature 9: Time Zone and Browser Geolocation Requests

**As a developer**, I want to construct time zone and browser geolocation requests, so I can retrieve temporal or device-position metadata through routed service calls.

**Expected Behavior / Usage:**

The input is a JSON object with `action` set to `[a list of known text extraction feature constants]` or `browser_geolocation_request`. Time-zone requests contain a coordinate and timestamp; browser geolocation requests may use an empty body. The output includes the HTTP method, status, canonical routed URL, POST JSON body when applicable, and parsed response fields.

**Test Cases:** `rcb_tests/public_test_cases/feature9_time_and_position_requests.json`

```json
{
    "description": "Timezone and browser geolocation requests convert coordinates, timestamps, and empty geolocation bodies into service calls and return parsed response summaries.",
    "cases": [
        {
            "input": {
                "action": "[a list of known text extraction feature constants]",
                "request": {
                    "location": [
                        39.603481,
                        -119.682251
                    ],
                    "timestamp": 1331766000
                }
            },
            "expected_output": "method=GET\nstatus=200\nurl=[base domain paths for routing services]/timezone/json?key=AIzaasdf&location=39.603481%2C-119.682251&timestamp=1331766000\ntimezone_status=OK\n"
        }
    ]
}
```

---

### Feature 10: Address Validation Request

**As a developer**, I want to send postal address validation input as a POST request, so I can validate address components through a remote service contract.

**Expected Behavior / Usage:**

The input is a JSON object with `action` set to `[a list of known text extraction feature constants]`, credentials, and a `request` object containing address lines, region, locality, and validation flags. The output includes `method=POST`, `status=200`, the canonical routed URL, the JSON body sent to the service, and a parsed address summary.

**Test Cases:** `rcb_tests/public_test_cases/feature10_[a list of known text extraction feature constants].json`

```json
{
    "description": "Address validation sends a POST request containing address lines, region, locality, and validation flags, then returns a summary of the parsed validation response.",
    "cases": [
        {
            "input": {
                "action": "[a list of known text extraction feature constants]",
                "api_key": "AIzaSyD_sJl0qMA65CYHMBokVfMNA7AKyt5ERYs",
                "request": {
                    "addressLines": "1600 Amphitheatre Pk",
                    "regionCode": "US",
                    "locality": "Mountain View",
                    "enableUspsCass": true
                }
            },
            "expected_output": "method=POST\nstatus=200\nurl=[base domain paths for routing services]/v1:validateAddress?key=AIzaSyD_sJl0qMA65CYHMBokVfMNA7AKyt5ERYs\njson={\"address\":{\"addressLines\":\"1600 Amphitheatre Pk\",\"locality\":\"Mountain View\",\"regionCode\":\"US\"},\"enableUspsCass\":true}\nresponse_address_lines=1600 Amphitheatre Pkwy\n"
        }
    ]
}
```

---

### Feature 11.1: Static Map Overlay Rendering

**As a developer**, I want to render marker and path overlay descriptors, so I can compose map image overlays without manual pipe-separated formatting.

**Expected Behavior / Usage:**

The input is a JSON object with `action` set to `[a list of known text extraction feature constants]` or `map_path_overlay` and overlay fields such as locations, size, color, label, weight, fill color, and geodesic flag. Valid marker input outputs `marker=<wire format>`; valid path input outputs `path=<wire format>`. Invalid marker labels output `error=invalid_argument`.

**Test Cases:** `rcb_tests/public_test_cases/feature11_1_static_map_overlays.json`

```json
{
    "description": "Static map marker and path overlays render style attributes followed by normalized locations in the pipe-separated wire format expected by map image requests.",
    "cases": [
        {
            "input": {
                "action": "[a list of known text extraction feature constants]",
                "locations": [
                    {
                        "lat": -33.867486,
                        "lng": 151.20699
                    },
                    "Sydney"
                ],
                "size": "small",
                "color": "blue",
                "label": "S"
            },
            "expected_output": "marker=size:small|color:blue|label:S|-33.867486,151.20699|Sydney\n"
        }
    ]
}
```

---

### Feature 11.2: Static Map Image Request

**As a developer**, I want to construct streamed static map image requests, so I can download a map image with center, zoom, overlays, and display options.

**Expected Behavior / Usage:**

The input is a JSON object with `action` set to `[a list of known text extraction feature constants]` and a `request` object containing image size plus center/zoom or markers, display options, visible locations, path overlays, and marker overlays. Valid inputs output the GET method, status, canonical routed URL, and `response_stream=true`. Missing required viewport data or unsupported image/map types output `error=invalid_argument`.

**Test Cases:** `rcb_tests/public_test_cases/feature11_2_static_map_image_request.json`

```json
{
    "description": "Static map image requests convert size, center, zoom, map type, format, scale, visibility, markers, and path overlays into a streamed image GET request.",
    "cases": [
        {
            "input": {
                "action": "[a list of known text extraction feature constants]",
                "request": {
                    "size": [
                        400,
                        400
                    ],
                    "zoom": 6,
                    "center": [
                        63.259591,
                        -144.667969
                    ],
                    "maptype": "hybrid",
                    "format": "png",
                    "scale": 2,
                    "visible": [
                        "Tok,AK"
                    ],
                    "path": {
                        "points": [
                            [
                                62.107733,
                                -145.541936
                            ],
                            "Delta+Junction,AK"
                        ],
                        "weight": 5,
                        "color": "red"
                    },
                    "markers": [
                        {
                            "locations": [
                                [
                                    62.107733,
                                    -145.541936
                                ]
                            ],
                            "color": "blue",
                            "label": "S"
                        },
                        {
                            "locations": [
                                "Delta+Junction,AK"
                            ],
                            "size": "tiny",
                            "color": "green"
                        },
                        {
                            "locations": [
                                "Tok,AK"
                            ],
                            "size": "mid",
                            "color": "0xFFFF00",
                            "label": "C"
                        }
                    ]
                }
            },
            "expected_output": "method=GET\nstatus=200\nurl=[base domain paths for routing services]/staticmap?center=63.259591%2C-144.667969&format=png&key=AIzaasdf&maptype=hybrid&markers=color%3Ablue%7Clabel%3AS%7C62.107733%2C-145.541936&markers=size%3Amid%7Ccolor%3A0xFFFF00%7Clabel%3AC%7CTok%2CAK&markers=size%3Atiny%7Ccolor%3Agreen%7CDelta%2BJunction%2CAK&path=weight%3A5%7Ccolor%3Ared%7C62.107733%2C-145.541936%7CDelta%2BJunction%2CAK&scale=2&size=400x400&visible=Tok%2CAK&zoom=6\nresponse_stream=true\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_[a list of known text extraction feature constants].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_[a list of known text extraction feature constants]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.

---
**Implementation notes:**
- consult the fields and input type schema for find_place requests
