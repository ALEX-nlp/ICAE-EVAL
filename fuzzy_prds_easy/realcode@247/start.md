## Product Requirement Document

# Mobile Advertising Gateway Adapter - Black-Box Contract for Ad Loading and Events

## Project Goal

Build a mobile advertising gateway adapter that allows developers to initialize an advertising subsystem, configure request-wide targeting, load multiple ad formats, render in-line ad views, and react to platform ad events without hand-writing repetitive platform-channel plumbing.

---

## Background & Problem

Without this library/tool, developers are forced to manually maintain ad identifiers, serialize request payloads, send platform gateway calls, connect asynchronous platform events back to the correct in-app ad object, and guard invalid widget reuse themselves. This leads to repetitive code, fragile lifecycle handling, hard-to-debug mismatches between native and application state, and inconsistent error reporting.

With this library/tool, developers work with a clean advertising abstraction while the adapter owns gateway serialization, native call routing, loaded-ad registration, event dispatch, and normalized adapter output for tests.

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

### Feature 1: Request Configuration Forwarding

**As a developer**, I want to request configuration forwarding, so I can use mobile advertising behavior through a stable gateway contract.

**Expected Behavior / Usage:**

The adapter accepts a request-wide configuration object containing a maximum content rating string, child-directed treatment flag, under-age-of-consent flag, and a list of test device identifiers. It must forward these fields to the mobile ad gateway as a single configuration update and render the gateway-observable method and field values to stdout.

**Test Cases:** `rcb_tests/public_test_cases/feature1_request_configuration.json`

```json
{
    "description": "Request-wide targeting configuration is forwarded to the native advertising gateway with all configured privacy, rating, and test-device fields.",
    "cases": [
        {
            "input": {
                "platform": "ios",
                "max_content_rating": "MA",
                "child_directed": 1,
                "under_age": 1,
                "test_device_ids": [
                    "test-device-id"
                ]
            },
            "expected_output": "channel=mobile_ad_gateway\nmethod=MobileAds#updateRequestConfiguration\nmax_content_rating=MA\nchild_directed=1\nunder_age=1\ntest_device_ids=test-device-id\n"
        }
    ]
}
```

---
### Feature 2: Initialization Status Reporting

**As a developer**, I want to initialization status reporting, so I can use mobile advertising behavior through a stable gateway contract.

**Expected Behavior / Usage:**

The adapter accepts an initialization response shape from the platform gateway and invokes the subsystem initialization path exactly once. Stdout must include the gateway method signal and the returned adapter-status record count, adapter key, readiness state, human-readable description, and latency value, using `null` when no latency is reported.

**Test Cases:** `rcb_tests/public_test_cases/feature2_initialization_status.json`

```json
{
    "description": "Initialization invokes the native gateway once and returns each mediation adapter status with state, description, and latency fields.",
    "cases": [
        {
            "input": {
                "platform": "ios",
                "adapter_name": "aName",
                "state": "not_ready",
                "description": "desc",
                "latency": null
            },
            "expected_output": "channel=mobile_ad_gateway\nmethod=MobileAds#initialize\nadapter_count=1\nadapter=aName\nstate=not_ready\ndescription=desc\nlatency_seconds=null\n"
        }
    ]
}
```

---
### Feature 3: Gateway Codec Behavior

**As a developer**, I want to gateway codec behavior, so I can use mobile advertising behavior through a stable gateway contract.

**Expected Behavior / Usage:**

The adapter accepts an encoded adapter status containing readiness state, description, and latency. For Android gateway data, integer latency values represent milliseconds and must be rendered as seconds; for iOS gateway data, numeric latency values are already seconds and must be preserved. The output must include the normalized state, description, and latency seconds.

**Test Cases:** `rcb_tests/public_test_cases/feature3_adapter_status_codec.json`

```json
{
    "description": "Adapter status messages preserve state and description while normalizing Android millisecond latency to seconds and leaving iOS latency values in seconds.",
    "cases": [
        {
            "input": {
                "platform": "android",
                "state": "not_ready",
                "description": "describe",
                "latency": 23
            },
            "expected_output": "state=not_ready\ndescription=describe\nlatency_seconds=0.023\n"
        },
        {
            "input": {
                "platform": "ios",
                "state": "not_ready",
                "description": "describe",
                "latency": 23
            },
            "expected_output": "state=not_ready\ndescription=describe\nlatency_seconds=23.0\n"
        }
    ]
}
```

---
### Feature 4: Structured Gateway Value Round-Trip

**As a developer**, I want to structured gateway value round-trip, so I can use mobile advertising behavior through a stable gateway contract.

**Expected Behavior / Usage:**

The adapter accepts a structured payload such as a standard ad request, publisher request, ad size, load error, or reward credit, sends it through the gateway value codec, decodes it, and prints the decoded public fields. Lists and maps must retain their entries, booleans must remain booleans, and event payloads must expose their numeric and string fields directly.

**Test Cases:** `rcb_tests/public_test_cases/feature4_gateway_value_codec.json`

```json
{
    "description": "Structured values sent through the platform gateway retain their public fields after encoding and decoding, including request metadata, ad sizes, load errors, and reward credits.",
    "cases": [
        {
            "input": {
                "payload": "ad_request",
                "keywords": [
                    "1",
                    "2",
                    "3"
                ],
                "content_url": "contentUrl",
                "birthday_year": 2020,
                "gender": "unknown",
                "designed_for_families": true,
                "child_directed": true,
                "test_devices": [
                    "Android",
                    "iOS"
                ],
                "non_personalized_ads": false
            },
            "expected_output": "payload=ad_request\nkeywords=1,2,3\ncontent_url=contentUrl\nbirthday_year=2020\ngender=unknown\ndesigned_for_families=true\nchild_directed=true\ntest_devices=Android,iOS\nnon_personalized_ads=false\n"
        },
        {
            "input": {
                "payload": "publisher_request",
                "keywords": [
                    "who"
                ],
                "content_url": "dat",
                "custom_targeting": {
                    "boy": "who"
                },
                "custom_targeting_lists": {
                    "him": [
                        "is"
                    ]
                },
                "non_personalized_ads": true
            },
            "expected_output": "payload=publisher_request\nkeywords=who\ncontent_url=dat\ncustom_targeting=[oscillating format – consult helper class for serialization prefix]\ncustom_targeting_lists=[oscillating format – consult helper class for serialization prefix]\nnon_personalized_ads=true\n"
        }
    ]
}
```

---
### Feature 5: Ad Load Request Routing

**As a developer**, I want to ad load request routing, so I can use mobile advertising behavior through a stable gateway contract.

**Expected Behavior / Usage:**

The adapter accepts an ad format, ad unit identifier, and the request metadata required for that format. Loading must allocate ad id `0` for the first loaded ad in a fresh session, call the matching gateway load method, pass format-specific fields such as size, factory id, custom options, standard request, or publisher request, and register the loaded ad so it can be looked up by id.

**Test Cases:** `rcb_tests/public_test_cases/feature5_load_ad_requests.json`

```json
{
    "description": "Loading each supported ad format allocates a stable ad id, forwards a format-specific gateway method with the supplied request data, and makes the ad retrievable by id.",
    "cases": [
        {
            "input": {
                "format": "banner",
                "ad_unit_id": "ca-app-pub-3940256099942544/2934735716",
                "size": {
                    "width": 320,
                    "height": 50
                },
                "request": {}
            },
            "expected_output": "method=loadBannerAd\nad_id=0\nad_unit_id=ca-app-pub-3940256099942544/2934735716\nrequest=standard\nsize=320x50\nregistry_ad_id=0\nregistry_has_ad=true\n"
        },
        {
            "input": {
                "format": "native",
                "ad_unit_id": "ca-app-pub-3940256099942544/3986624511",
                "factory_id": "0",
                "custom_options": {
                    "a": 1,
                    "b": 2
                },
                "request": {}
            },
            "expected_output": "method=loadNativeAd\nad_id=0\nad_unit_id=ca-app-pub-3940256099942544/3986624511\nrequest=standard\npublisher_request=null\nfactory_id=0\ncustom_options=a:1,b:2\nregistry_ad_id=0\nregistry_has_ad=true\n"
        },
        {
            "input": {
                "format": "native",
                "ad_unit_id": "test-id",
                "factory_id": "0",
                "custom_options": {
                    "a": 1,
                    "b": 2
                },
                "publisher_request": {}
            },
            "expected_output": "method=loadNativeAd\nad_id=0\nad_unit_id=test-id\nrequest=null\npublisher_request=publisher\nfactory_id=0\ncustom_options=a:1,b:2\nregistry_ad_id=0\nregistry_has_ad=true\n"
        }
    ]
}
```

---
### Feature 6: Ad Lifecycle Commands

**As a developer**, I want to ad lifecycle commands, so I can use mobile advertising behavior through a stable gateway contract.

**Expected Behavior / Usage:**

The adapter accepts a lifecycle action. Disposing a loaded in-line ad must forward a dispose gateway call with the loaded ad id and remove the ad from the registry. Showing a loaded full-screen ad must forward a show gateway call with the loaded ad id. Showing a full-screen ad before it has been loaded must not leak host-language exception details; stdout must render `error=ad_not_loaded` and the affected ad unit identifier.

**Test Cases:** `rcb_tests/public_test_cases/feature6_ad_lifecycle_commands.json`

```json
{
    "description": "A loaded ad can be disposed or shown through the gateway by id; attempting to show a full-screen ad before it has been loaded is reported as a neutral ad-not-loaded error.",
    "cases": [
        {
            "input": {
                "action": "dispose_loaded_banner",
                "ad_unit_id": "ca-app-pub-3940256099942544/2934735716"
            },
            "expected_output": "load_method=loadBannerAd\ndispose_method=disposeAd\ndisposed_ad_id=0\nregistry_has_ad=false\nregistry_ad_id=null\n"
        },
        {
            "input": {
                "action": "show_loaded_fullscreen",
                "ad_unit_id": "testId"
            },
            "expected_output": "load_method=loadInterstitialAd\nshow_method=showAdWithoutView\nshown_ad_id=0\n"
        }
    ]
}
```

---
### Feature 7: Platform Event Dispatch

**As a developer**, I want to platform event dispatch, so I can use mobile advertising behavior through a stable gateway contract.

**Expected Behavior / Usage:**

The adapter accepts an event name, loads a matching ad into the registry, injects a platform event addressed to that ad id, and prints the invoked callback plus any payload fields. Failure events must expose code, domain, and message; reward events must expose amount and type; loaded-state checks must transition from false before the load event to true after it and back to false after disposal.

**Test Cases:** `rcb_tests/public_test_cases/feature7_ad_event_callbacks.json`

```json
{
    "description": "Platform events addressed by ad id invoke the matching lifecycle callback and expose event payloads such as load errors, reward credits, and load-state transitions.",
    "cases": [
        {
            "input": {
                "event": "loaded",
                "format": "banner",
                "ad_unit_id": "ca-app-pub-3940256099942544/2934735716"
            },
            "expected_output": "callback=loaded\nad_id=0\nad_unit_id=ca-app-pub-3940256099942544/2934735716\n"
        },
        {
            "input": {
                "event": "failed_to_load",
                "format": "banner",
                "ad_unit_id": "ca-app-pub-3940256099942544/2934735716",
                "error": {
                    "code": 1,
                    "domain": "domain",
                    "message": "message"
                }
            },
            "expected_output": "callback=failed_to_load\nad_id=0\ncode=1\ndomain=domain\nmessage=message\n"
        },
        {
            "input": {
                "event": "native_clicked",
                "format": "native",
                "ad_unit_id": "ca-app-pub-3940256099942544/3986624511",
                "factory_id": "testId"
            },
            "expected_output": "callback=native_clicked\nad_id=0\nad_unit_id=ca-app-pub-3940256099942544/3986624511\n"
        }
    ]
}
```

---
### Feature 8: In-Line Ad Widget Mounting

**As a developer**, I want to in-line ad widget mounting, so I can use mobile advertising behavior through a stable gateway contract.

**Expected Behavior / Usage:**

The adapter accepts a widget scenario for an in-line ad. Rendering on Android must produce a platform-view link and the gateway view type. Attempting to mount the same ad object or the same widget in two active locations must report a neutral `ad_widget_already_mounted` error with the user-facing summary, without leaking host runtime exception class names.

**Test Cases:** `rcb_tests/public_test_cases/feature8_ad_widget_mounting.json`

```json
{
    "description": "An in-line ad widget renders as a platform view for the active mobile platform, and the same ad object cannot be mounted in two widget locations at the same time.",
    "cases": [
        {
            "input": {
                "scenario": "render_android_view",
                "ad_unit_id": "ca-app-pub-3940256099942544/3986624511",
                "factory_id": "0"
            },
            "expected_output": "widget_result=platform_view_link\n[Flutter view type string from Google Mobile Ads plugin]\n"
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
- refer to the payload object mapped to 'FailedToLoad', check ExternalServicesError class
