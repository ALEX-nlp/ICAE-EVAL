## Product Requirement Document

# Mobile UI Automation Driver — Capability, Gesture, Network, Device, and Context Engine

## Project Goal

Build a mobile UI automation driver that lets test engineers drive a physical or virtual handset (validate a session request, decode touch gestures, change radio state, prepare the right device, manage localized strings, and switch between native and in-app web automation contexts) through one coherent, idiomatic interface, without hand-writing the brittle device-shell command sequences and platform-version branching that each of these operations normally requires.

---

## Background & Problem

Without this driver, anyone automating a mobile handset must reimplement a large amount of fiddly glue: deciding whether a requested session is even runnable, translating high-level gestures into low-level coordinate math, encoding/decoding the radio state into a bitmask, branching on the platform API level for nearly every settings operation, choosing the correct device out of several attached ones, staging and de-duplicating application archives by content hash, and bookkeeping which automation context is active. This logic is repetitive, easy to get subtly wrong (off-by-one durations, wrong key-navigation sequences, forgetting to reboot after a locale change), and tends to leak host-specific runtime details into callers.

With this driver, all of that is expressed as a small set of well-defined behaviors with clear inputs and outputs. Callers describe *what* they want (a gesture, a target network state, a locale) and the driver performs the minimum correct device operations, normalizes every failure into a stable, language-neutral category, and keeps the platform-version branching internal.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility domain (capability validation, gesture math, network bitmask coding, device/locale provisioning, application-archive staging, string localization, context switching, session teardown). It MUST NOT be a single "god file". Organize the codebase into clear modules grouped by responsibility, with a directory tree that reflects a production-grade repository. Do not over-engineer the genuinely small helpers (e.g. a pure path builder), but do not collapse the whole surface into one file either.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box contract for the execution adapter**, not the internal data model. The core logic must not parse JSON or write to stdout. A thin execution adapter is solely responsible for translating each JSON command into idiomatic calls on the core, and for rendering results and errors as the line-oriented contract shown here. Device interactions (shell, settings, archive transfer, reboot) MUST be expressed against an abstraction so the core can run against a real device or a recording test double without changing.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Separate request validation, gesture parsing, network coding, device provisioning, archive staging, string handling, context management, and output formatting into distinct units.
   - **Open/Closed Principle (OCP):** Adding a new gesture or a new settings-toggle platform branch must not require editing unrelated behaviors.
   - **Liskov Substitution Principle (LSP):** Any device-collaborator implementation must be substitutable for the abstraction the core depends on.
   - **Interface Segregation Principle (ISP):** Keep the device-collaborator interface cohesive; a behavior should depend only on the operations it actually uses.
   - **Dependency Inversion Principle (DIP):** Core behaviors depend on the device abstraction, never on a concrete shell/transport.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface must be elegant and idiomatic to the target language, hiding the platform-version branching and bitmask arithmetic.
   - **Resilience:** Edge cases (already-running emulator, already-unlocked screen, missing archive, unknown context) must be handled deterministically. Errors must be modeled as distinct, catchable categories rather than generic faults.
   - **Language-Neutral Errors:** Every failure rendered to the contract MUST be a neutral category line (e.g. `error=app_not_found`) with offending values placed in their own fields. No host-language exception class names, runtime message suffixes, or object reprs may appear in stdout.

---

## Core Features

### Feature 1: Session Capability Validation

**As a developer**, I want the driver to validate a requested session configuration up front, so I can fail fast with a clear reason instead of starting an unrunnable session.

**Expected Behavior / Usage:**

The input is a capability set. A configuration is valid when it names at least one launch target — an application file path, an installed package identifier, or a supported browser — and the platform name is matched case-insensitively. The configuration is rejected when: it names no launch target (`error=missing_required_capability`, with `required=app_or_package_or_browser`); it names an unsupported browser (`error=unsupported_browser`, with the offending `browser` value echoed); or it names both an application file and a browser at once (`error=conflicting_capabilities`, with `conflict=app_and_browser`). A valid configuration outputs `valid=true`. Errors are neutral categories; the offending value is a separate field, never embedded in a host-language sentence.

**Test Cases:** `rcb_tests/public_test_cases/feature1_capability_validation.json`

```json
{
    "description": "Validate a requested capability set before a session starts. The validator accepts a configuration that names at least one launch target (an application file path, an installed package identifier, or a supported browser) and is case-insensitive about the platform name. It rejects a configuration that names no launch target, names an unsupported browser, or names both an application file and a browser at the same time. A valid configuration outputs valid=true; a rejected one outputs a neutral error category plus any offending value.",
    "cases": [
        {"input": {"op": "validate_capabilities", "caps": {"platformName": "Android", "deviceName": "device", "app": "/path/to/some.apk"}}, "expected_output": "valid=true\n"},
        {"input": {"op": "validate_capabilities", "caps": {"platformName": "Android", "deviceName": "device"}}, "expected_output": "error=missing_required_capability\nrequired=app_or_package_or_browser\n"},
        {"input": {"op": "validate_capabilities", "caps": {"platformName": "Android", "deviceName": "device", "browserName": "Netscape Navigator"}}, "expected_output": "error=unsupported_browser\nbrowser=Netscape Navigator\n"},
        {"input": {"op": "validate_capabilities", "caps": {"platformName": "Android", "deviceName": "device", "app": "/path/to/some.apk", "browserName": "Chrome"}}, "expected_output": "error=conflicting_capabilities\nconflict=app_and_browser\n"}
    ]
}
```

---

### Feature 2: Request Proxying Configuration

**As a developer**, I want to query how the driver proxies requests to an external in-app web engine, so I can correctly route commands between native automation and web automation.

**Expected Behavior / Usage:**

*2.1 Proxy-Active Query — whether proxying is currently on*

Until an external web engine is attached to the session, request proxying is inactive. Querying the proxy-active state returns `proxy_active=false`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_proxy_active.json`

```json
{
    "description": "Report whether request proxying to an external in-app web engine is currently active. Until such an engine is attached, proxying is inactive, so this query returns proxy_active=false.",
    "cases": [
        {"input": {"op": "proxy_config", "query": "proxy_active"}, "expected_output": "proxy_active=false\n"}
    ]
}
```

*2.2 Proxy-Avoid List — routes always handled locally*

The driver exposes the list of HTTP method + URL-pattern pairs that must never be proxied to an external web engine and are always handled by the driver itself. Each entry names a method and a route regular expression. The list covers context-switching endpoints, vendor extension endpoints, touch-performance endpoints, and orientation endpoints. The output lists each pair as `avoid_route method=<METHOD> pattern=<REGEX>` in order. The patterns are wire-format strings and are reproduced verbatim.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_proxy_avoid_list.json`

```json
{
    "description": "Expose the list of HTTP method + URL-pattern pairs that must never be proxied to an external web engine and are always handled locally. Each pair names a method and a route regular expression. The list covers context switching, vendor-specific extension endpoints, touch performance endpoints, and orientation endpoints.",
    "cases": [
        {"input": {"op": "proxy_config", "query": "avoid_list"}, "expected_output": "avoid_route method=POST pattern=^\\/session\\/[^/]+\\/context\navoid_route method=GET pattern=^\\/session\\/[^/]+\\/context\navoid_route method=POST pattern=^\\/session\\/[^/]+\\/appium\navoid_route method=GET pattern=^\\/session\\/[^/]+\\/appium\navoid_route method=POST pattern=^\\/session\\/[^/]+\\/touch\\/perform\navoid_route method=POST pattern=^\\/session\\/[^/]+\\/touch\\/multi\\/perform\navoid_route method=POST pattern=^\\/session\\/[^/]+\\/orientation\navoid_route method=GET pattern=^\\/session\\/[^/]+\\/orientation\n"}
    ]
}
```

---

### Feature 3: Touch Gesture Engine

**As a developer**, I want to express touch interactions at a high level and have them resolved into concrete device commands, so I do not have to compute coordinates, durations, and command routing by hand.

**Expected Behavior / Usage:**

*3.1 Absolute-Coordinate Gesture Resolution — normalize a sequence into ordered touch states*

The input is an ordered gesture sequence given in absolute screen coordinates. Each press/moveTo/tap/longPress state resolves to an absolute x/y. A `moveTo` whose coordinates are relative to the previous position accumulates onto the running position. A `wait` state inherits the current running position. A `release` state carries no coordinates. The output lists each resolved state in order: `action=<name> x=<x> y=<y>` for positioned states, and `action=release` for the release.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_parse_touch_absolute.json`

```json
{
    "description": "Normalize a touch gesture sequence given in absolute screen coordinates into a list of resolved touch states. Each press/moveTo/tap/longPress state carries an absolute x/y; a moveTo expressed relative to the previous position is accumulated onto the running position; a wait state inherits the current position; and a release state carries no coordinates. The output lists each state in order with its resolved coordinates.",
    "cases": [
        {"input": {"op": "parse_touch", "actions": [{"action": "press", "options": {"x": 100, "y": 101}}, {"action": "moveTo", "options": {"x": 50, "y": 51}}, {"action": "wait", "options": {"ms": 5000}}, {"action": "moveTo", "options": {"x": -40, "y": -41}}, {"action": "release", "options": {}}]}, "expected_output": "action=press x=100 y=101\naction=moveTo x=150 y=152\naction=wait x=150 y=152\naction=moveTo x=110 y=111\naction=release\n"}
    ]
}
```

*3.2 Drag Duration Computation — long-press/move/release becomes a drag with a derived duration*

A long-press, move, release triple is translated into a drag. The start coordinates come from the long-press and the end coordinates from the move. The duration in seconds defaults to a platform-dependent minimum: 2 seconds on platforms at API level 5 and above, and 1 second on platforms below API level 5. If the long-press carries an explicit hold duration in milliseconds, that value (converted to seconds) is used only when it exceeds the platform minimum; otherwise the minimum wins. The output reports `start_x`, `start_y`, `end_x`, `end_y`, and `duration`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_touch_drag_duration.json`

```json
{
    "description": "Translate a long-press / move / release gesture into a drag operation with a computed duration in seconds. The start coordinates come from the long-press, the end coordinates from the move. The duration defaults to a platform-dependent minimum (2 seconds on newer platforms with API level 5 and above, 1 second on older platforms below API level 5). If the long-press specifies an explicit hold duration in milliseconds, it is used (converted to seconds) only when it exceeds that minimum; otherwise the minimum wins.",
    "cases": [
        {"input": {"op": "touch_drag", "apiLevel": 5, "longPress": {"x": 100, "y": 101}, "moveTo": {"x": 50, "y": 51}}, "expected_output": "start_x=100\nstart_y=101\nend_x=50\nend_y=51\nduration=2\n"},
        {"input": {"op": "touch_drag", "apiLevel": 5, "longPress": {"x": 100, "y": 101, "duration": 4000}, "moveTo": {"x": 50, "y": 51}}, "expected_output": "start_x=100\nstart_y=101\nend_x=50\nend_y=51\nduration=4\n"},
        {"input": {"op": "touch_drag", "apiLevel": 4.4, "longPress": {"x": 100, "y": 101}, "moveTo": {"x": 50, "y": 51}}, "expected_output": "start_x=100\nstart_y=101\nend_x=50\nend_y=51\nduration=1\n"}
    ]
}
```

*3.3 Gesture Command Routing — element-scoped vs screen-level routing*

A swipe, flick, or drag is routed to a device command whose name depends on whether the gesture is scoped to a specific element. A scoped gesture emits an element-prefixed command (e.g. `element:swipe`); the same gesture without an element emits the bare command (e.g. `swipe`). The output reports the resolved `command`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_gesture_routing.json`

```json
{
    "description": "Route a gesture to the correct underlying device command name depending on whether it is scoped to a specific element or applied at screen level. A swipe, flick, or drag scoped to an element emits an element-prefixed command; the same gesture without an element emits the bare command. The output is the resolved command name.",
    "cases": [
        {"input": {"op": "gesture_route", "gesture": "swipe", "scoped": true}, "expected_output": "command=element:swipe\n"},
        {"input": {"op": "gesture_route", "gesture": "swipe", "scoped": false}, "expected_output": "command=swipe\n"},
        {"input": {"op": "gesture_route", "gesture": "flick", "scoped": true}, "expected_output": "command=element:flick\n"},
        {"input": {"op": "gesture_route", "gesture": "flick", "scoped": false}, "expected_output": "command=flick\n"},
        {"input": {"op": "gesture_route", "gesture": "drag", "scoped": true}, "expected_output": "command=element:drag\n"},
        {"input": {"op": "gesture_route", "gesture": "drag", "scoped": false}, "expected_output": "command=drag\n"}
    ]
}
```

---

### Feature 4: Network State Management

**As a developer**, I want to read and set the device's radio state through a single integer bitmask, so I can control connectivity without juggling three independent settings.

**Expected Behavior / Usage:**

*4.1 Read Connection Bitmask — combine three radio signals into one integer*

The current connection state is computed from three independent signals: airplane mode (bit value 1), WiFi (bit value 2), and mobile data (bit value 4). When airplane mode is on, the result is 1 and the WiFi/data bits are not added. Otherwise the result is the sum of whichever of the WiFi and data bits are on. The output reports `connection=<int>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_get_network_connection.json`

```json
{
    "description": "Compute the current network connection state as a bitmask from three independent device signals: airplane mode (bit value 1), WiFi (bit value 2), and mobile data (bit value 4). When airplane mode is on the result is 1 and the WiFi and data bits are not added. Otherwise the result is the sum of the WiFi and data bits that are on. The output is the integer connection value.",
    "cases": [
        {"input": {"op": "get_network", "airplane": false, "wifi": false, "data": false}, "expected_output": "connection=0\n"},
        {"input": {"op": "get_network", "airplane": true, "wifi": false, "data": false}, "expected_output": "connection=1\n"},
        {"input": {"op": "get_network", "airplane": false, "wifi": true, "data": false}, "expected_output": "connection=2\n"},
        {"input": {"op": "get_network", "airplane": false, "wifi": false, "data": true}, "expected_output": "connection=4\n"},
        {"input": {"op": "get_network", "airplane": false, "wifi": true, "data": true}, "expected_output": "connection=6\n"}
    ]
}
```

*4.2 Apply Connection Bitmask — decode the mask into ordered device operations*

A requested bitmask is decoded: the lowest bit selects airplane mode, the next WiFi, the next data. Airplane mode is always set and broadcast first. When airplane mode is requested on, the operation stops there and does not touch WiFi/data. When airplane mode is off, the WiFi and data flags are then applied together. The output lists each device operation in order as `device_op=...` with its arguments.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_set_network_connection.json`

```json
{
    "description": "Apply a requested network connection state given as a bitmask, decoding it into ordered device operations. The lowest bit selects airplane mode, the next bit WiFi, the next bit data. The system always sets and broadcasts airplane mode first. When airplane mode is requested on, it stops there and does not touch WiFi/data. When airplane mode is off, it then applies the WiFi and data flags together. The output lists each device operation in order with its arguments.",
    "cases": [
        {"input": {"op": "set_network", "type": 0}, "expected_output": "device_op=set_airplane_mode value=0\ndevice_op=broadcast_airplane_mode value=0\ndevice_op=set_wifi_and_data wifi=0 data=0\n"},
        {"input": {"op": "set_network", "type": 1}, "expected_output": "device_op=set_airplane_mode value=1\ndevice_op=broadcast_airplane_mode value=1\n"},
        {"input": {"op": "set_network", "type": 2}, "expected_output": "device_op=set_airplane_mode value=0\ndevice_op=broadcast_airplane_mode value=0\ndevice_op=set_wifi_and_data wifi=1 data=0\n"},
        {"input": {"op": "set_network", "type": 6}, "expected_output": "device_op=set_airplane_mode value=0\ndevice_op=broadcast_airplane_mode value=0\ndevice_op=set_wifi_and_data wifi=1 data=1\n"}
    ]
}
```

*4.3 Toggle Location Services — platform-aware key-navigation sequence*

Toggling the device location-services setting opens the relevant settings screen and emits a platform-dependent key-navigation sequence to move focus onto the toggle. Platforms at API level 16 use the sequence `19,19,20`. Platforms at API level 19 and above use `22,22,19` and additionally send one preparatory key event `19` before opening the screen. Platforms at API level 15 and below have no global toggle and report `error=not_implemented`. The output reports the optional `pre_keyevent`, the `setting` opened, and the `key_sequence`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_toggle_location_services.json`

```json
{
    "description": "Toggle the device location-services setting by opening the relevant settings screen and emitting a platform-dependent key navigation sequence to move focus onto the toggle. Platforms at API level 16 use the sequence 19,19,20 (up, up, down). Platforms at API level 19 and above use 22,22,19 (right, right, up) and additionally send one preparatory up keyevent (19) before opening the screen. Platforms at API level 15 and below have no global toggle and report a not_implemented error.",
    "cases": [
        {"input": {"op": "toggle_location", "apiLevel": 15}, "expected_output": "error=not_implemented\n"},
        {"input": {"op": "toggle_location", "apiLevel": 16}, "expected_output": "setting=LOCATION_SOURCE_SETTINGS\nkey_sequence=19,19,20\n"},
        {"input": {"op": "toggle_location", "apiLevel": 19}, "expected_output": "pre_keyevent=19\nsetting=LOCATION_SOURCE_SETTINGS\nkey_sequence=22,22,19\n"}
    ]
}
```

---

### Feature 5: Device Provisioning

**As a developer**, I want the driver to prepare the right device, locale, and launch metadata for me, so my session starts on a correctly configured target.

**Expected Behavior / Usage:**

*5.1 Ensure Device Locale — minimal changes plus reboot only on change*

Given a requested target language and/or country, the driver makes the minimum device changes and reboots only if something changed. When neither language nor country is requested, nothing happens (`no_change=true`). Below API level 23, language and country are independent: only the differing ones are written, and a reboot follows any change. At API level 23 and above the value is a single combined locale formed as lowercase-language, a dash, then uppercase-country; it is rewritten only if it differs, followed by a reboot. The output lists each `device_op=...` in order, or `no_change=true`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_ensure_device_locale.json`

```json
{
    "description": "Ensure the device language and country match a requested target, performing the minimum device operations needed and rebooting only when something changed. When neither language nor country is requested, nothing happens. On platforms below API level 23, language and country are independent settings: only the ones that differ from the current value are written, and a reboot follows any change. On platforms at API level 23 and above the value is a single combined locale (lowercase-language + dash + uppercase-country): it is rewritten only if it differs, followed by a reboot. The output lists each device operation in order, or no_change when nothing was needed.",
    "cases": [
        {"input": {"op": "ensure_locale", "current": {"apiLevel": 18}}, "expected_output": "no_change=true\n"},
        {"input": {"op": "ensure_locale", "language": "en", "country": "us", "current": {"apiLevel": 18, "language": "en", "country": "us"}}, "expected_output": "no_change=true\n"},
        {"input": {"op": "ensure_locale", "language": "en", "country": "us", "current": {"apiLevel": 18, "language": "fr", "country": "FR"}}, "expected_output": "device_op=set_language value=en\ndevice_op=set_country value=us\ndevice_op=reboot\n"},
        {"input": {"op": "ensure_locale", "language": "en", "country": "us", "current": {"apiLevel": 23, "locale": "en-US"}}, "expected_output": "no_change=true\n"},
        {"input": {"op": "ensure_locale", "language": "en", "country": "us", "current": {"apiLevel": 23, "locale": "fr-FR"}}, "expected_output": "device_op=set_locale value=en-US\ndevice_op=reboot\n"}
    ]
}
```

*5.2 Device Selection — pick the right attached device and report its identity*

Given the connected device list, the driver resolves which device to use. A requested device identifier must appear in the list, otherwise `error=device_not_found` is reported with the requested `udid`. When no identifier is requested, the first connected device is chosen. When a virtual device name is requested, the running emulator's identifier and port are used. The output reports the resolved `udid` and `emulator_port`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_device_info_from_caps.json`

```json
{
    "description": "Resolve which connected device to use and report its identifier and emulator port. When a specific device identifier is requested it must appear in the connected device list, otherwise a device_not_found error is reported along with the requested identifier. When no identifier is requested, the first connected device is chosen. When a virtual device name is requested, the running emulator's identifier and port are used. The output gives the resolved udid and emulator_port.",
    "cases": [
        {"input": {"op": "device_info", "caps": {"udid": "emulator-1234"}, "devices": [{"udid": "emulator-1234"}, {"udid": "rotalume-1337"}], "emulatorPort": 1234}, "expected_output": "udid=emulator-1234\nemulator_port=1234\n"},
        {"input": {"op": "device_info", "caps": {}, "devices": [{"udid": "emulator-1234"}, {"udid": "rotalume-1337"}], "emulatorPort": 1234}, "expected_output": "udid=emulator-1234\nemulator_port=1234\n"},
        {"input": {"op": "device_info", "caps": {"avd": "AVD_NAME"}, "devices": [{"udid": "emulator-1234"}, {"udid": "rotalume-1337"}], "emulatorPort": 1234}, "expected_output": "udid=emulator-1234\nemulator_port=1234\n"},
        {"input": {"op": "device_info", "caps": {"udid": "foomulator"}, "devices": [{"udid": "emulator-1234"}, {"udid": "rotalume-1337"}], "emulatorPort": 1234}, "expected_output": "error=device_not_found\nudid=foomulator\n"}
    ]
}
```

*5.3 Java Runtime Detection — parse the version banner*

Given the raw banner text a Java toolchain prints, the driver detects the installed runtime version. It scans for a line containing a Java or OpenJDK version banner and extracts the version token. When recognized, it reports `java_version=<token>`; when unrecognizable, it reports `error=java_version_unavailable`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_5_java_version.json`

```json
{
    "description": "Detect the installed Java runtime version from the raw banner text a Java toolchain prints. The parser scans for a line containing a Java or OpenJDK version banner and extracts the version token. When the banner is recognized, the version is reported; when it cannot be recognized, the operation reports a neutral java_version_unavailable error.",
    "cases": [
        {"input": {"op": "java_version", "raw": "java version \"1.8.0_40\""}, "expected_output": "java_version=1.8.0_40\n"},
        {"input": {"op": "java_version", "raw": "foo bar"}, "expected_output": "error=java_version_unavailable\n"}
    ]
}
```

---

### Feature 6: Application Archive Staging

**As a developer**, I want application archives staged and de-duplicated on the device by content hash, so reinstalls are cheap and the device temp area stays clean.

**Expected Behavior / Usage:**

*6.1 Staging Path — canonical on-device path from a content hash*

Given an archive's content hash, the driver computes the canonical on-device staging path: the device temporary directory, then the hash, then an `.apk` suffix. The output reports `remote_path=<path>`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_remote_apk_path.json`

```json
{
    "description": "Compute the canonical on-device staging path for a cached application archive from its content hash. The path is the device temporary directory followed by the hash and an .apk suffix.",
    "cases": [
        {"input": {"op": "remote_apk_path", "md5": "foo"}, "expected_output": "remote_path=/data/local/tmp/foo.apk\n"}
    ]
}
```

---

### Feature 7: Localized Strings, Screen, and Utility Operations

**As a developer**, I want the driver to manage localized application strings and other small but exacting utilities, so callers get deterministic behavior on the happy path and on the edges.

**Expected Behavior / Usage:**

*7.1 Localized Strings Retrieval — cache-aware lookup by language*

Return the localized application strings for a requested language. When the requested language is already cached, the cached map is returned without re-extracting. When no language is requested, the device's current language selects the cached map. When the language is not cached, the strings are freshly extracted and returned. The output lists each string entry as `key=value`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_get_strings.json`

```json
{
    "description": "Return the localized application strings for a requested language. When the requested language is already cached, the cached map is returned without extracting again. When no language is requested, the device's current language is used to select the cached map. When the language is not cached, the strings are freshly extracted and returned. The output lists each string key=value pair.",
    "cases": [
        {"input": {"op": "get_strings", "scenario": "fresh", "language": "en", "strings": {"test": "en_value"}}, "expected_output": "test=en_value\n"},
        {"input": {"op": "get_strings", "scenario": "cached", "language": "fr", "deviceLanguage": "en", "cache": {"en": {"test": "en_value"}, "fr": {"test": "fr_value"}}}, "expected_output": "test=fr_value\n"},
        {"input": {"op": "get_strings", "scenario": "cached", "deviceLanguage": "en", "cache": {"en": {"test": "en_value"}, "fr": {"test": "fr_value"}}}, "expected_output": "test=en_value\n"}
    ]
}
```

*7.2 Null-Property Pruning — drop null/undefined but keep falsy-defined*

Remove properties whose value is null or undefined from an object, while keeping properties whose value is defined-but-falsy such as `false` or `0`. The output lists the remaining keys in order and their count.

**Test Cases:** `rcb_tests/public_test_cases/feature7_3_remove_null_properties.json`

```json
{
    "description": "Remove properties whose value is null or undefined from an object, while keeping properties whose value is falsy-but-defined such as false or 0. The output lists the remaining keys in order and their count.",
    "cases": [
        {"input": {"op": "remove_null_properties", "object": {"foo": null, "bar": true}}, "expected_output": "remaining_keys=bar\nkey_count=1\n"},
        {"input": {"op": "remove_null_properties", "object": {"foo": false, "bar": true, "zero": 0}}, "expected_output": "remaining_keys=foo,bar,zero\nkey_count=3\n"}
    ]
}
```

---

### Feature 8: Automation Context Management

**As a developer**, I want to enumerate and switch between native and in-app web automation contexts, so I can automate both native UI and embedded web content in one session.

**Expected Behavior / Usage:**

*8.1 Enumerate Contexts — native plus any web contexts*

Enumerate the available automation contexts. The native context is always present and listed first. When the session targets an in-app web engine browser, the web engine context is also listed. Otherwise the available web views discovered from the device are appended. The output reports `contexts=` as a comma-separated set.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_get_contexts.json`

```json
{
    "description": "Enumerate the automation contexts currently available. The native context is always present and listed first. When the session targets an in-app web engine browser, the web engine context is also listed. Otherwise the available web views are discovered from the device and appended. The output lists the contexts as a comma-separated set.",
    "cases": [
        {"input": {"op": "get_contexts", "browser": "Chrome"}, "expected_output": "contexts=NATIVE_APP,CHROMIUM\n"},
        {"input": {"op": "get_contexts", "webviews": []}, "expected_output": "contexts=NATIVE_APP\n"}
    ]
}
```

---

### Feature 9: Session Teardown

**As a developer**, I want session teardown to perform exactly the device operations its options call for, in a fixed order, so cleanup is deterministic and never does more than needed.

**Expected Behavior / Usage:**

Tear down a session, performing only the device operations appropriate to its options and in a fixed order. If the session was never started (already shut down), nothing is done beyond noting `already_shut_down=true`. Otherwise: when the unicode keyboard was enabled with keyboard reset and a default input method was recorded, the input method is restored first; a non-web session is force-stopped; the device is sent to its home screen; and when full reset is requested, the application is additionally uninstalled. The output lists each `device_op=...` in order.

**Test Cases:** `rcb_tests/public_test_cases/feature9_session_teardown.json`

```json
{
    "description": "Tear down a session, performing only the device operations appropriate to its options and in a fixed order. If the session was never started (already shut down), nothing is done beyond noting that. Otherwise, when the unicode keyboard was enabled with keyboard reset and a default input method was recorded, the input method is restored first. A non-web session is force-stopped, then the device is sent to its home screen. When full reset is requested, the application is additionally uninstalled. The output lists each device operation in order.",
    "cases": [
        {"input": {"op": "session_teardown", "alreadyShutDown": true}, "expected_output": "already_shut_down=true\n"},
        {"input": {"op": "session_teardown", "opts": {}}, "expected_output": "device_op=force_stop\ndevice_op=go_to_home\n"},
        {"input": {"op": "session_teardown", "opts": {"fullReset": true}}, "expected_output": "device_op=force_stop\ndevice_op=go_to_home\ndevice_op=uninstall_apk\n"},
        {"input": {"op": "session_teardown", "opts": {"unicodeKeyboard": true, "resetKeyboard": true}, "defaultIME": "someDefaultIME"}, "expected_output": "device_op=set_ime value=someDefaultIME\ndevice_op=force_stop\ndevice_op=go_to_home\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above, organized into modules by responsibility (capability validation, gesture engine, network coding, device provisioning, archive staging, string/utility helpers, context management, session lifecycle). Device interactions go through an abstraction so the core runs unchanged against a real device or a recording test double. Physical structure must follow the Scale-Driven Code Organization constraint.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core. It reads one JSON command from stdin, invokes the appropriate core logic, and prints the line-oriented contract to stdout, matching the per-leaf-feature contracts above. It is the only layer that touches stdin/stdout/JSON, and it is solely responsible for normalizing every failure into a neutral `error=<category>` line with offending values in their own fields — no host-language exception identity may reach stdout.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_capability_validation.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_capability_validation@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same gesture naming convention used in the core gesture controller module
- refer to the historical key event sequence documented in the legacy Android driver setup guide
