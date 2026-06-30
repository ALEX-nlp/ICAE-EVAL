## Product Requirement Document

# Open Location Tracking Library - Fused Location, Mock Playback & Update Filtering

## Project Goal

Build a location-tracking library that lets mobile application developers obtain the device's best last-known position, subscribe to filtered streams of location updates, and replay recorded routes for testing — all behind one small, idiomatic client facade — without writing low-level, source-by-source plumbing for every satellite, network, and passive positioning source on the platform.

---

## Background & Problem

Without this library, developers must talk to each raw positioning source individually: query every source for its last fix, hand-roll the logic that decides which fix is "best" (newest vs. most accurate), wire up and tear down subscriptions per source, and re-implement throttling by time and distance. They also have no uniform way to feed synthetic positions or recorded routes into the app during testing, so location-dependent features are painful to exercise. This leads to repetitive boilerplate, subtle correctness bugs in the "which fix wins" logic, and brittle manual testing.

With this library, a developer connects a single client, asks for the last location or for ongoing updates with a chosen power/accuracy priority, and the library fuses the available sources, applies the requested time/distance filtering, and (in mock mode) replays injected fixes or a recorded track. The "best fix" rules and subscription lifecycle are handled for them.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has several distinct responsibilities (request configuration, fix-selection rules, source activation, update filtering/dispatch, mock playback, client lifecycle), so it MUST NOT be a single "god file": use a clear multi-file layout that separates these concerns. Do not over-engineer, but do not collapse the domain into one module either.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box contract for the execution adapter**, not the internal data model. The core location logic MUST be fully decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls on the core library and rendering results to stdout.

3. **Adherence to SOLID Design Principles:**
   - **SRP:** Keep request configuration, fix selection, source activation, update filtering, output formatting, and lifecycle in distinct units.
   - **OCP:** New positioning sources or playback strategies should be addable without modifying the fusion core.
   - **LSP:** All location-producing engines (real fusion vs. mock playback) must be interchangeable behind one engine abstraction.
   - **ISP:** Keep the client/listener interfaces small and cohesive.
   - **DIP:** High-level fusion logic depends on a source/clock abstraction, not on concrete platform I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public client facade must be elegant and idiomatic to the target language, hiding the per-source complexity.
   - **Resilience:** Invalid configuration (e.g. an unsupported priority) must be reported as a well-modeled error, not a generic crash. Missing fixes, stale fixes, and empty source sets must be handled gracefully.

---

## Core Features

### Feature 1: Location Update Request Configuration

**As a developer**, I want to describe how often and how precisely I want location updates, so I can trade off accuracy against power without managing source-specific knobs.

**Expected Behavior / Usage:**

A request is a mutable configuration object with four fields: `interval` (desired update period, milliseconds), `fastest_interval` (the fastest period the app can handle, milliseconds), `smallest_displacement` (minimum movement before an update, meters), and `priority` (power/accuracy preference). The input is an ordered list of `steps`, each setting one field; the output is the resulting configuration. A brand-new request reports its built-in defaults. Setting any field overrides its default. There is one coupling rule: whenever the interval is set to a value **below** the current fastest interval, the fastest interval is lowered to equal the new interval (setting the interval to a value at or above the fastest interval leaves the fastest interval unchanged). Priority accepts the named values `high`, `balanced`, `low_power`, and `no_power`; the default is `balanced`. Any priority value outside this set is rejected and reported as a normalized error carrying the offending raw value, instead of being applied.

**Test Cases:** `rcb_tests/public_test_cases/feature1_location_request.json`

```json
{
    "description": "Configuring a location update request: a fresh request exposes default interval/fastest-interval/displacement/priority; each field can be overridden; lowering the interval below the fastest interval also lowers the fastest interval to match; and an unsupported priority is rejected with a normalized error.",
    "cases": [
        {
            "input": { "command": "configure_request", "steps": [] },
            "expected_output": "[a specific millisecond interval — ask the team lead for the exact number]\n[the minimum allowed interval as defined in the system config]\n[zero or a value derived from the initial calibration step]\npriority=balanced\n"
        },
        {
            "input": { "command": "configure_request", "steps": [ { "interval": 5000 } ] },
            "expected_output": "interval=5000\nfastest_interval=5000\n[zero or a value derived from the initial calibration step]\npriority=balanced\n"
        },
        {
            "input": { "command": "configure_request", "steps": [ { "priority": "high" } ] },
            "expected_output": "[a specific millisecond interval — ask the team lead for the exact number]\n[the minimum allowed interval as defined in the system config]\n[zero or a value derived from the initial calibration step]\npriority=high\n"
        },
        {
            "input": { "command": "configure_request", "steps": [ { "priority": -1 } ] },
            "expected_output": "error=invalid_priority\npriority=-1\n"
        }
    ]
}
```

---

### Feature 2: Best Last-Known Location Selection

**As a developer**, I want a single "best last-known location" answer fused from every available source, so I don't have to compare fixes myself.

**Expected Behavior / Usage:**

The input gives the current time (`now`, milliseconds) and a list of `fixes`, each with a source `provider` (`gps`, `network`, or `passive`), an optional `accuracy` (radius in meters; smaller is better), and a `time` (milliseconds). The library returns the selected source and its accuracy, or `selected=none` when there are no fixes. A fix is "fresh" if its time is within the recent-update threshold of `now` (the threshold is 60000 ms); otherwise it is "stale". Selection rules: among fresh fixes, the one with the smallest accuracy radius wins. Stale fixes are ignored as long as at least one fresh fix exists. If every fix is stale, the most recent stale fix is returned (accuracy is not used as a tiebreaker in that case).

**Test Cases:** `rcb_tests/public_test_cases/feature2_last_known_location.json`

```json
{
    "description": "Selecting the best last-known location across the available sources. With no fixes nothing is returned. With a single source that fix is returned. Among fresh fixes the most accurate (smallest accuracy radius) wins. Stale fixes (older than the recent-update threshold) are skipped while a fresh fix exists; if every fix is stale the most recent one is returned.",
    "cases": [
        {
            "input": { "command": "last_known_location", "now": 100000000, "fixes": [] },
            "expected_output": "selected=none\n"
        },
        {
            "input": { "command": "last_known_location", "now": 100000000, "fixes": [ { "provider": "gps", "time": 100000000 } ] },
            "expected_output": "selected=gps\naccuracy=0.0\n"
        },
        {
            "input": { "command": "last_known_location", "now": 100000000, "fixes": [ { "provider": "gps", "accuracy": 1000.0, "time": 100000000 }, { "provider": "network", "accuracy": 100.0, "time": 100000000 }, { "provider": "passive", "accuracy": 10.0, "time": 100000000 } ] },
            "expected_output": "selected=passive\naccuracy=10.0\n"
        },
        {
            "input": { "command": "last_known_location", "now": 100000000, "fixes": [ { "provider": "gps", "accuracy": 100.0, "time": 100000000 }, { "provider": "network", "accuracy": 100.0, "time": 99880000 } ] },
            "expected_output": "selected=gps\naccuracy=100.0\n"
        }
    ]
}
```

---

### Feature 3: Location Source Activation by Power Priority

**As a developer**, I want the chosen power priority to decide which positioning sources are actually turned on, so I get the accuracy/power profile I asked for.

**Expected Behavior / Usage:**

Given a request with a `priority`, the library subscribes to a specific set of positioning sources and reports the activated source names (sorted, comma-separated). `high` activates both the satellite (`gps`) and `network` sources. `balanced` and `low_power` activate the `network` source only. `no_power` activates the `passive` source only. When the request is subsequently cleared (`disable: true`), all sources are deactivated and the activated set becomes empty.

**Test Cases:** `rcb_tests/public_test_cases/feature3_provider_activation.json`

```json
{
    "description": "Activating location sources from a request's power priority. High accuracy activates both the satellite (gps) and network sources; balanced and low-power activate the network source only; no-power activates the passive source only; and clearing the request deactivates every source.",
    "cases": [
        {
            "input": { "command": "activate_sources", "priority": "high" },
            "expected_output": "providers=gps,network\n"
        },
        {
            "input": { "command": "activate_sources", "priority": "balanced" },
            "expected_output": "providers=network\n"
        },
        {
            "input": { "command": "activate_sources", "priority": "no_power" },
            "expected_output": "providers=passive\n"
        },
        {
            "input": { "command": "activate_sources", "priority": "high", "disable": true },
            "expected_output": "providers=\n"
        }
    ]
}
```

---

### Feature 4: Filtered Streaming Location Updates

**As a developer**, I want a stream of location updates that already respects my interval, displacement, and accuracy preferences, so my listener only sees the updates worth handling.

**Expected Behavior / Usage:**

The input is a `request` (priority plus optional `fastest_interval` in ms and `smallest_displacement` in meters) and an ordered list of incoming `fixes` (each with a source `provider`, `lat`, `lng`, optional `time` in ms, and optional `accuracy`). The output lists, in order, the fixes that were actually delivered to the listener: a `reported=<count>` line followed by one `<n> provider=<p> lat=<lat> lng=<lng>` line per delivered fix. Rules: a single incoming fix is delivered. A later fix from the same source that arrives sooner than `fastest_interval` after the previous delivered fix is dropped; likewise a later fix that has moved less than `smallest_displacement` from the previous delivered fix is dropped. When the satellite and network sources stream nearly simultaneously, only the more accurate fix (smaller accuracy radius) is delivered; the less accurate one is suppressed.

**Test Cases:** `rcb_tests/public_test_cases/feature4_location_updates.json`

```json
{
    "description": "Streaming location updates to a listener while honoring the request. A single incoming fix is delivered. Updates arriving sooner than the fastest interval, or closer than the smallest displacement, are dropped. When both sources stream simultaneously only the more accurate fix is delivered.",
    "cases": [
        {
            "input": { "command": "stream_updates", "request": { "priority": "high" }, "fixes": [ { "provider": "gps", "lat": 0.0, "lng": 0.0 } ] },
            "expected_output": "reported=1\n1 provider=gps lat=0.0 lng=0.0\n"
        },
        {
            "input": { "command": "stream_updates", "request": { "priority": "high", "fastest_interval": 5000 }, "fixes": [ { "provider": "gps", "lat": 0.0, "lng": 0.0, "time": 1000 }, { "provider": "gps", "lat": 1.0, "lng": 1.0, "time": 2000 } ] },
            "expected_output": "reported=1\n1 provider=gps lat=0.0 lng=0.0\n"
        },
        {
            "input": { "command": "stream_updates", "request": { "priority": "high", "fastest_interval": 0, "smallest_displacement": 0.0 }, "fixes": [ { "provider": "gps", "lat": 0.0, "lng": 0.0, "time": 1000, "accuracy": 10.0 }, { "provider": "network", "lat": 0.0, "lng": 0.0, "time": 1001, "accuracy": 20.0 } ] },
            "expected_output": "reported=1\n1 provider=gps lat=0.0 lng=0.0\n"
        }
    ]
}
```

---

### Feature 5: Stopping Location Updates

**As a developer**, I want to cancel an active subscription, so the app stops receiving updates and releases the sources.

**Expected Behavior / Usage:**

The input is a `stop_updates` command with an optional `priority`. The adapter registers a request (subscribing to the sources its priority implies — two sources for `high`, one for the default `balanced`), then removes updates. The output reports the number of active source subscriptions immediately after registering and again after removal. Removing updates must unsubscribe from **every** source, so the post-removal count is always zero.

**Test Cases:** `rcb_tests/public_test_cases/feature5_remove_updates.json`

```json
{
    "description": "Stopping location updates. Registering a high-accuracy request subscribes to two sources and a default request subscribes to one; removing updates unsubscribes from every source.",
    "cases": [
        {
            "input": { "command": "stop_updates", "priority": "high" },
            "expected_output": "after_request=2\nafter_remove=0\n"
        },
        {
            "input": { "command": "stop_updates" },
            "expected_output": "after_request=1\nafter_remove=0\n"
        }
    ]
}
```

---

### Feature 6: Mock Mode

**As a developer**, I want to feed synthetic positions through the same pipeline real positions use, so I can test location-dependent behavior deterministically.

**Expected Behavior / Usage:**

*6.1 Single Mock Location — inject one synthetic fix while in mock mode*

After mock mode is enabled and a listener is subscribed, injecting a single mock location (`lat`, `lng`) immediately delivers exactly one update to the listener and makes that location the value returned as the last-known location. The output reports the last-known coordinates and the number of times the listener was notified.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_mock_location.json`

```json
{
    "description": "Injecting a single mock location while in mock mode: the injected fix is immediately delivered to the registered listener exactly once and is also returned as the last-known location.",
    "cases": [
        {
            "input": { "command": "mock_location", "lat": 40.7484, "lng": -73.9857 },
            "expected_output": "last_lat=40.7484\nlast_lng=-73.9857\nnotifications=1\n"
        }
    ]
}
```

*6.2 Mock Mode Listener Bookkeeping — subscriptions while toggling mock mode*

The input is an ordered list of `actions`: `{"mock": true|false}` toggles mock mode, and `{"request": "high"|"default"}` registers a subscription. The output reports the final number of active **real-source** subscriptions. Rules: enabling mock mode tears down any existing real-source subscriptions (count becomes 0). While mock mode is on, registering a request does not create any real-source subscription (count stays 0). Toggling mock mode off and re-registering re-establishes real subscriptions without leaving stale duplicates behind (e.g. registering under `high`, then toggling mock on then off and registering `high` again, yields exactly the two subscriptions of one `high` request).

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_mock_mode.json`

```json
{
    "description": "Listener bookkeeping when toggling mock mode. Enabling mock mode unsubscribes any real source listeners; while mock mode is on, requests do not subscribe to real sources; toggling mock mode off and re-requesting does not leave duplicate subscriptions.",
    "cases": [
        {
            "input": { "command": "mock_listener_state", "actions": [ { "request": "high" }, { "mock": true } ] },
            "expected_output": "listeners=0\n"
        },
        {
            "input": { "command": "mock_listener_state", "actions": [ { "mock": true }, { "request": "default" } ] },
            "expected_output": "listeners=0\n"
        },
        {
            "input": { "command": "mock_listener_state", "actions": [ { "mock": true }, { "request": "high" }, { "mock": false }, { "request": "high" } ] },
            "expected_output": "listeners=2\n"
        }
    ]
}
```

---

### Feature 7: GPX Trace Replay

**As a developer**, I want to replay a recorded route as a sequence of mock locations, so I can test movement-driven features against a realistic path.

**Expected Behavior / Usage:**

The input is a recorded route as a GPX document (`gpx`), containing ordered track points each with a latitude, longitude, and speed. In mock mode the library parses the document and delivers each track point in order as a location update carrying its latitude, longitude, and speed. The first delivered point has no computed bearing (`has_bearing=false`, `bearing=0.0`); every subsequent point carries the compass bearing from the previous point to the current point (`has_bearing=true`). The output is a `locations=<count>` line followed by one line per delivered point: `<n> lat=<lat> lng=<lng> speed=<speed> bearing=<bearing> has_bearing=<bool>`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_trace_replay.json`

```json
{
    "description": "Replaying a recorded GPX track as mock locations. Each track point is delivered in order carrying its latitude, longitude and speed. The first point has no bearing; each subsequent point carries the bearing from the previous point to the current one.",
    "cases": [
        {
            "input": { "command": "replay_trace", "gpx": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<gpx xmlns=\"http://www.topografix.com/GPX/1/0\" version=\"1.0\" creator=\"trace\">\n  <trk><trkseg>\n    <trkpt lat=\"0.0\" lon=\"0.1\"><speed>10.0</speed></trkpt>\n    <trkpt lat=\"1.0\" lon=\"1.1\"><speed>20.0</speed></trkpt>\n    <trkpt lat=\"2.0\" lon=\"2.1\"><speed>30.0</speed></trkpt>\n  </trkseg></trk>\n</gpx>\n" },
            "expected_output": "locations=3\n1 lat=0.0 lng=0.1 speed=10.0 bearing=0.0 has_bearing=false\n2 lat=1.0 lng=1.1 speed=20.0 bearing=45.188038 has_bearing=true\n3 lat=2.0 lng=2.1 speed=30.0 bearing=45.170467 has_bearing=true\n"
        }
    ]
}
```

---

### Feature 8: Location Freshness & Accuracy Comparison

**As a developer**, I want a single predicate that decides whether one candidate fix is better than another, so update dispatch can keep only improvements.

**Expected Behavior / Usage:**

The input is two candidate fixes `a` and `b`; each may be `null`, may carry an `accuracy` (meters), and/or an `elapsed_nanos` monotonic timestamp (nanoseconds). The output is `a_better_than_b=<bool>`. Rules, evaluated in order: a `null` `a` is never better (`false`). A non-null `a` against a `null` `b` is better (`true`). If `a` is newer than `b` by more than the recent-update threshold (60000 ms expressed in nanoseconds), `a` is better regardless of accuracy (`true`). Otherwise, a fix that lacks accuracy loses to a fix that has it: if `a` has no accuracy it is not better (`false`); if `b` has no accuracy (and `a` does) then `a` is better (`true`). When both have accuracy, `a` is better only if its accuracy radius is strictly smaller than `b`'s.

**Test Cases:** `rcb_tests/public_test_cases/feature8_is_better_than.json`

```json
{
    "description": "Deciding whether candidate fix A should be preferred over fix B. A missing A is never preferred; A is always preferred over a missing B; an A that is newer than B by more than the recent-update threshold is preferred regardless of accuracy; otherwise a fix lacking accuracy loses to one that has it, and between two fixes with accuracy the smaller accuracy radius wins.",
    "cases": [
        {
            "input": { "command": "compare_fixes", "a": null, "b": {} },
            "expected_output": "a_better_than_b=false\n"
        },
        {
            "input": { "command": "compare_fixes", "a": { "elapsed_nanos": 100000000000 }, "b": { "elapsed_nanos": 39999999999 } },
            "expected_output": "a_better_than_b=true\n"
        },
        {
            "input": { "command": "compare_fixes", "a": { "accuracy": 30.0 }, "b": { "accuracy": 40.0 } },
            "expected_output": "a_better_than_b=true\n"
        },
        {
            "input": { "command": "compare_fixes", "a": { "accuracy": 40.0 }, "b": { "accuracy": 30.0 } },
            "expected_output": "a_better_than_b=false\n"
        }
    ]
}
```

---

### Feature 9: Client Connection Lifecycle

**As a developer**, I want a single client I connect and disconnect, so the location and geofencing facades are available only while connected and cleaned up afterward.

**Expected Behavior / Usage:**

The input is an ordered list of `actions`: `connect`, `request` (subscribe a listener via the location facade), and `disconnect`. The output reports four fields: whether the client is `connected`, whether the `location_api` facade is `available`/`absent`, whether the `geofencing_api` facade is `available`/`absent`, and the number of active update `listeners`. Before connecting, both facades are absent and the client is not connected. Connecting makes both facades available and the client connected. Disconnecting makes both facades absent, marks the client not connected, and unsubscribes any active update listeners (so the listener count returns to zero even if a request had been made while connected).

**Test Cases:** `rcb_tests/public_test_cases/feature9_client_lifecycle.json`

```json
{
    "description": "Client connection lifecycle. Before connecting, the location and geofencing facades are unavailable. Connecting makes both available and reports connected. Disconnecting makes both unavailable, reports disconnected, and unsubscribes any active update listeners.",
    "cases": [
        {
            "input": { "command": "client_lifecycle", "actions": [] },
            "expected_output": "connected=false\nlocation_api=absent\ngeofencing_api=absent\nlisteners=0\n"
        },
        {
            "input": { "command": "client_lifecycle", "actions": [ "connect" ] },
            "expected_output": "connected=true\nlocation_api=available\ngeofencing_api=available\nlisteners=0\n"
        },
        {
            "input": { "command": "client_lifecycle", "actions": [ "connect", "disconnect" ] },
            "expected_output": "connected=false\nlocation_api=absent\ngeofencing_api=absent\nlisteners=0\n"
        },
        {
            "input": { "command": "client_lifecycle", "actions": [ "connect", "request", "disconnect" ] },
            "expected_output": "connected=false\nlocation_api=absent\ngeofencing_api=absent\nlisteners=0\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file location-tracking library implementing the features above (request configuration, fix selection, source activation, update filtering/dispatch, mock playback, freshness comparison, and client lifecycle), with the platform/I-O details kept behind abstractions.

2. **The Execution/Test Adapter:** A runnable adapter that acts as a client to the core library. It reads a JSON command (with a `command` discriminator) describing the scenario, invokes the appropriate core logic, normalizes any errors into the language-neutral contract shown above (no host-language exception identifiers), and prints the result to stdout exactly matching the per-feature contracts. The adapter is logically and physically separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{stem}@{index:03d}.txt` (e.g. the first case of `feature1_location_request.json` under `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_location_request@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` contains **only** the raw stdout of the program under test (no PASS/FAIL or metadata), so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- adjust priority using the same logic flow as the level-based scheduler
