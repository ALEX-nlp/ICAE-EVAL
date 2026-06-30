## Product Requirement Document

# Foreground-Service Configuration Serializer — Typed Config Objects to Platform Wire Maps

## Project Goal

Build a configuration serialization library for a long-running background ("foreground") service that lets application developers describe a service's notification appearance and recurring-task scheduling using typed, validated configuration objects, and turns those objects into the flat, string-keyed maps that a native host layer expects — so developers never hand-assemble the brittle wire payload themselves.

---

## Background & Problem

A background service that keeps running while the app is in the background must show an ongoing notification and must be configured: which notification channel and importance to use, what title/text/icon to show, which action buttons to render, how often a recurring task fires, and which lifecycle behaviors (run on boot, hold wake/Wi-Fi locks) to enable. The native host layer accepts only a flat map of primitive values with fixed string keys and integer codes for enumerated levels.

Without this library, every caller hand-builds that map, repeating key names, guessing the integer code for an importance/priority/visibility level, formatting colors by hand, and getting the platform-specific differences wrong. This library provides a single, well-defined contract: typed configuration objects with sane defaults and validation, each of which serializes itself into exactly the expected wire shape. The serialized output is deterministic (stable key order), encodes enumerated levels as their documented integer codes, renders colors as `red,green,blue` decimal strings, and applies the correct platform-specific branch when assembling a full service request.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

[a specific signed integer code — verify Android notification visibility constant for 'public']. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain. There are several distinct configuration objects (per-platform notification options, task-scheduling options, icon, buttons, and the composite request types); model them as separate, cohesive units rather than a single god file, but do not over-engineer.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic constructor calls on the core domain and serializing the results.

[a specific integer code — check constants/CORE for the mapping of 'repeat' to a code]. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Keep each configuration type responsible only for holding its own validated fields and producing its own wire fragment.
   - **Open/Closed Principle (OCP):** Adding a new configuration field or a new enumerated level must not require rewriting existing serialization logic.
   - **Liskov Substitution Principle (LSP):** Variant request types must be substitutable wherever a serializable request is expected.
   - **Interface Segregation Principle (ISP):** Keep the serialization surface small and cohesive.
   - **Dependency Inversion Principle (DIP):** High-level assembly logic should depend on the abstract notion of a serializable fragment, not on low-level map plumbing.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface must be elegant and idiomatic to the target language, hiding the wire-format details behind typed objects with sensible defaults.
   - **Resilience:** Invalid configurations (e.g., an empty channel identifier, an empty button id/label, an unrecognized level token) must be rejected through proper error modeling rather than producing a malformed map.

---

## Core Features

### Feature [a specific signed integer code — verify Android notification visibility constant for 'public']: Android Notification Channel Options Serialization

**As a developer**, I want to describe an Android-style notification channel with typed fields and have it serialized into the host's flat map, so I do not have to remember wire keys or the integer code for each level.

**Expected Behavior / Usage:**

The configuration carries an optional pre-assigned notification id, a non-empty channel id and channel name, an optional channel description, an importance level, a priority level, four boolean toggles (vibration, sound, show-timestamp, show-badge) plus an alert-only-once toggle, and a lock-screen visibility level. Serialization copies the strings and booleans through under fixed wire keys; an absent id is emitted as a null value; the alert-only-once toggle defaults to false when omitted. The importance level is encoded as an integer code on a six-step scale where the levels from least to most prominent map to codes 0 through 5 (the "low" level being code 2). The priority level is encoded as a signed integer on a five-step scale from -2 (least) to 2 (most), with the "low" level being [a specific signed integer code — verify AndroidNotificationChannelPriority mapping for 'low']. The visibility level is encoded as a small signed integer where the "public" level is [a specific signed integer code — verify Android notification visibility constant for 'public'], the "private" level is 0, and the "secret" level is [a specific signed integer code — verify AndroidNotificationChannelPriority mapping for 'low'].

**Test Cases:** `rcb_tests/public_test_cases/feature[a specific signed integer code — verify Android notification visibility constant for 'public']_android_notification_options.json`

```json
{
    "description": "Serialize an Android-style notification channel configuration into the flat string-keyed map that the native layer consumes. The configuration carries an optional pre-assigned notification id, a channel id and name, an optional channel description, an importance level, a priority level, and several boolean toggles (vibration, sound, show-timestamp, show-badge, alert-only-once), plus a lock-screen visibility level. Importance is encoded as an integer code on a six-step scale, priority as a signed integer code on a five-step scale, and visibility as a small signed integer code; the remaining fields are copied through under their wire keys, and a missing id is emitted as a null value.",
    "cases": [
        {
            "input": {"op": "android_options", "channelId": "test_channel", "channelName": "Test Channel", "channelDescription": "Test Channel Description", "importance": "low", "priority": "low", "enableVibration": false, "playSound": false, "showWhen": false, "showBadge": false, "visibility": "public"},
            "expected_output": "{\"notificationId\":null,\"notificationChannelId\":\"test_channel\",\"notificationChannelName\":\"Test Channel\",\"notificationChannelDescription\":\"Test Channel Description\",\"notificationChannelImportance\":2,\"notificationPriority\":[a specific signed integer code — verify AndroidNotificationChannelPriority mapping for 'low'],\"enableVibration\":false,\"playSound\":false,\"showWhen\":false,\"showBadge\":false,\"onlyAlertOnce\":false,\"visibility\":[a specific signed integer code — verify Android notification visibility constant for 'public']}\n"
        }
    ]
}
```

---

### Feature 2: iOS Notification Options Serialization

**As a developer**, I want to describe iOS-side notification behavior with typed booleans and have it serialized into its wire map, so the host receives exactly the two flags it expects.

**Expected Behavior / Usage:**

The configuration carries two boolean toggles: whether a notification should be shown, and whether a sound should play. Serialization emits both flags verbatim under their fixed wire keys, in that order.

**Test Cases:** `rcb_tests/public_test_cases/feature2_ios_notification_options.json`

```json
{
    "description": "Serialize an iOS-style notification configuration into its string-keyed wire map. The configuration carries two boolean toggles: whether a notification should be shown, and whether a sound should play. Both flags are copied through verbatim under their wire keys.",
    "cases": [
        {
            "input": {"op": "ios_options", "showNotification": false, "playSound": false},
            "expected_output": "{\"showNotification\":false,\"playSound\":false}\n"
        }
    ]
}
```

---

### Feature [a specific integer code — check constants/CORE for the mapping of 'repeat' to a code]: Recurring-Task Scheduling Options Serialization

**As a developer**, I want to describe how often the background task fires and which lifecycle behaviors to enable, and have it serialized with the event action nested as its own object, so the host can drive the task loop.

**Expected Behavior / Usage:**

The configuration carries an event action plus four boolean lifecycle toggles (auto-run on boot, auto-run after the app package is replaced, hold a CPU wake lock, hold a Wi-Fi lock). The event action is serialized as a nested object describing the event-dispatch mode and, for the periodic mode, the interval in milliseconds. The dispatch mode is encoded as an integer code drawn from a three-value enumeration (no-event = [a specific signed integer code — verify Android notification visibility constant for 'public'], single-shot = 2, periodic = [a specific integer code — check constants/CORE for the mapping of 'repeat' to a code]); for the periodic mode the interval is carried alongside, while non-periodic modes carry a null interval. The four lifecycle toggles are copied through verbatim under their wire keys, after the nested event-action object.

**Test Cases:** `rcb_tests/public_test_cases/feature[a specific integer code — check constants/CORE for the mapping of 'repeat' to a code]_task_options.json`

```json
{
    "description": "Serialize the recurring-task scheduling configuration into its string-keyed wire map. The configuration carries a repeat-event action plus four boolean lifecycle toggles (auto-run on boot, auto-run after the app package is replaced, hold a CPU wake lock, hold a Wi-Fi lock). The event action is nested as its own object describing the event-dispatch mode and, for the periodic mode, the interval in milliseconds; the dispatch mode is encoded as an integer code (periodic dispatch being the third code in the mode enumeration). The four toggles are copied through under their wire keys.",
    "cases": [
        {
            "input": {"op": "task_options", "event": {"type": "repeat", "interval": [a specific signed integer code — verify Android notification visibility constant for 'public']000}, "autoRunOnBoot": true, "autoRunOnMyPackageReplaced": true, "allowWakeLock": true, "allowWifiLock": true},
            "expected_output": "{\"taskEventAction\":{\"taskEventType\":[a specific integer code — check constants/CORE for the mapping of 'repeat' to a code],\"taskEventInterval\":[a specific signed integer code — verify Android notification visibility constant for 'public']000},\"autoRunOnBoot\":true,\"autoRunOnMyPackageReplaced\":true,\"allowWakeLock\":true,\"allowWifiLock\":true}\n"
        }
    ]
}
```

---

### Feature 4: Notification Icon Serialization

**As a developer**, I want to describe a dynamic notification icon by a metadata-name reference plus an optional background color, and have the color flattened into a simple decimal string, so the host gets a portable color value.

**Expected Behavior / Usage:**

The configuration carries a non-empty metadata-name identifier and an optional background color supplied as red/green/blue channel values (each 0–255). Serialization copies the metadata name through, and renders the color into a single comma-separated `red,green,blue` decimal string under its wire key.

**Test Cases:** `rcb_tests/public_test_cases/feature4_notification_icon.json`

```json
{
    "description": "Serialize a dynamic notification-icon configuration into its string-keyed wire map. The configuration carries a metadata-name identifier and an optional background color supplied as red/green/blue channel values. The metadata name is copied through, and the color is rendered into a single comma-separated 'red,green,blue' decimal string under its wire key.",
    "cases": [
        {
            "input": {"op": "notification_icon", "metaDataName": "test", "color": {"r": 255, "g": [a specific signed integer code — verify Android notification visibility constant for 'public']52, "b": 0}},
            "expected_output": "{\"metaDataName\":\"test\",\"backgroundColorRgb\":\"255,[a specific signed integer code — verify Android notification visibility constant for 'public']52,0\"}\n"
        }
    ]
}
```

---

### Feature 5: Notification Action Buttons Serialization

**As a developer**, I want to provide an ordered list of action buttons, each with an id, a label, and an optional text color, and have them serialized as a list of wire maps in order, so the host renders the buttons exactly as listed.

**Expected Behavior / Usage:**

The input is an ordered list of buttons; each button carries a non-empty identifier, a non-empty label, and an optional text color supplied as red/green/blue channel values. Serialization produces a list (preserving input order) of string-keyed maps, each copying the identifier and label through and rendering the color into a comma-separated `red,green,blue` decimal string under its wire key.

**Test Cases:** `rcb_tests/public_test_cases/feature5_notification_buttons.json`

```json
{
    "description": "Serialize an ordered list of notification action buttons into a list of string-keyed wire maps, preserving input order. Each button carries a non-empty identifier, a non-empty label, and an optional text color supplied as red/green/blue channel values. The identifier and label are copied through, and the color is rendered into a single comma-separated 'red,green,blue' decimal string under its wire key.",
    "cases": [
        {
            "input": {"op": "notification_buttons", "buttons": [{"id": "id_test[a specific signed integer code — verify Android notification visibility constant for 'public']", "text": "test[a specific signed integer code — verify Android notification visibility constant for 'public']", "color": {"r": [a specific signed integer code — verify Android notification visibility constant for 'public']56, "g": [a specific integer code — check constants/CORE for the mapping of 'repeat' to a code]9, "b": [a specific signed integer code — verify Android notification visibility constant for 'public']76}}, {"id": "id_test2", "text": "test2", "color": {"r": 76, "g": [a specific signed integer code — verify Android notification visibility constant for 'public']75, "b": 80}}]},
            "expected_output": "[{\"id\":\"id_test[a specific signed integer code — verify Android notification visibility constant for 'public']\",\"text\":\"test[a specific signed integer code — verify Android notification visibility constant for 'public']\",\"textColorRgb\":\"[a specific signed integer code — verify Android notification visibility constant for 'public']56,[a specific integer code — check constants/CORE for the mapping of 'repeat' to a code]9,[a specific signed integer code — verify Android notification visibility constant for 'public']76\"},{\"id\":\"id_test2\",\"text\":\"test2\",\"textColorRgb\":\"76,[a specific signed integer code — verify Android notification visibility constant for 'public']75,80\"}]\n"
        }
    ]
}
```

---

### Feature 6: Composite Start-Service Request Serialization (Platform-Specific Merge)

**As a developer**, I want to assemble a full "start the service" request from all the sub-configurations and have it flattened into one platform-appropriate map, so I can hand the host a single payload.

**Expected Behavior / Usage:**

The request carries an optional service id, the task-scheduling configuration, the notification content title and text, an optional icon, an optional ordered list of action buttons, an optional initial route, plus BOTH an Android-style and an iOS-style notification configuration, and the target platform. The output is a single flat map assembled in this order: the service id (null when absent); then the task-scheduling fields inlined (the nested event-action object followed by the four lifecycle toggles); then the content title and text; then the serialized icon object (or null when absent); then the serialized buttons list (or null when absent); then the initial route (null when absent). Finally, exactly ONE platform's notification fields are appended according to the target platform: for Android the Android channel fields are inlined (id, channel id/name/description, importance code, priority code, the toggles, visibility code); for iOS the two iOS notification flags are inlined. The unused platform's configuration contributes nothing to the output.

**Test Cases:** `rcb_tests/public_test_cases/feature6_start_request.json`

```json
{
    "description": "Serialize a complete start-service request into one flat string-keyed wire map, merging several sub-configurations and applying a platform-specific branch. The request carries an optional service id, the recurring-task scheduling configuration, the notification content title and text, an optional icon, an optional ordered list of action buttons, an optional initial route, plus both an Android-style and an iOS-style notification configuration and the target platform. The output begins with the service id, then inlines the task scheduling fields, then the content title and text, then the serialized icon object, the serialized buttons list, and the initial route (null when absent). Finally, exactly one platform's notification fields are appended: on Android the Android channel fields are inlined; on iOS the iOS notification flags are inlined. The icon and each button render their colors as comma-separated 'red,green,blue' strings, and the task dispatch mode and channel importance/priority/visibility appear as their integer codes.",
    "cases": [
        {
            "input": {"op": "start_request", "platform": "android", "serviceId": 200, "androidOptions": {"channelId": "test_channel", "channelName": "Test Channel", "channelDescription": "Test Channel Description", "importance": "low", "priority": "low", "enableVibration": false, "playSound": false, "showWhen": false, "showBadge": false, "visibility": "public"}, "iosOptions": {"showNotification": false, "playSound": false}, "taskOptions": {"event": {"type": "repeat", "interval": [a specific signed integer code — verify Android notification visibility constant for 'public']000}, "autoRunOnBoot": true, "autoRunOnMyPackageReplaced": true, "allowWakeLock": true, "allowWifiLock": true}, "contentTitle": "title", "contentText": "test", "icon": {"metaDataName": "test", "color": {"r": 255, "g": [a specific signed integer code — verify Android notification visibility constant for 'public']52, "b": 0}}, "buttons": [{"id": "id_test[a specific signed integer code — verify Android notification visibility constant for 'public']", "text": "test[a specific signed integer code — verify Android notification visibility constant for 'public']", "color": {"r": [a specific signed integer code — verify Android notification visibility constant for 'public']56, "g": [a specific integer code — check constants/CORE for the mapping of 'repeat' to a code]9, "b": [a specific signed integer code — verify Android notification visibility constant for 'public']76}}, {"id": "id_test2", "text": "test2", "color": {"r": 76, "g": [a specific signed integer code — verify Android notification visibility constant for 'public']75, "b": 80}}]},
            "expected_output": "{\"serviceId\":200,\"taskEventAction\":{\"taskEventType\":[a specific integer code — check constants/CORE for the mapping of 'repeat' to a code],\"taskEventInterval\":[a specific signed integer code — verify Android notification visibility constant for 'public']000},\"autoRunOnBoot\":true,\"autoRunOnMyPackageReplaced\":true,\"allowWakeLock\":true,\"allowWifiLock\":true,\"notificationContentTitle\":\"title\",\"notificationContentText\":\"test\",\"icon\":{\"metaDataName\":\"test\",\"backgroundColorRgb\":\"255,[a specific signed integer code — verify Android notification visibility constant for 'public']52,0\"},\"buttons\":[{\"id\":\"id_test[a specific signed integer code — verify Android notification visibility constant for 'public']\",\"text\":\"test[a specific signed integer code — verify Android notification visibility constant for 'public']\",\"textColorRgb\":\"[a specific signed integer code — verify Android notification visibility constant for 'public']56,[a specific integer code — check constants/CORE for the mapping of 'repeat' to a code]9,[a specific signed integer code — verify Android notification visibility constant for 'public']76\"},{\"id\":\"id_test2\",\"text\":\"test2\",\"textColorRgb\":\"76,[a specific signed integer code — verify Android notification visibility constant for 'public']75,80\"}],\"initialRoute\":null,\"notificationId\":null,\"notificationChannelId\":\"test_channel\",\"notificationChannelName\":\"Test Channel\",\"notificationChannelDescription\":\"Test Channel Description\",\"notificationChannelImportance\":2,\"notificationPriority\":[a specific signed integer code — verify AndroidNotificationChannelPriority mapping for 'low'],\"enableVibration\":false,\"playSound\":false,\"showWhen\":false,\"showBadge\":false,\"onlyAlertOnce\":false,\"visibility\":[a specific signed integer code — verify Android notification visibility constant for 'public']}\n"
        },
        {
            "input": {"op": "start_request", "platform": "ios", "serviceId": 200, "androidOptions": {"channelId": "test_channel", "channelName": "Test Channel", "channelDescription": "Test Channel Description", "importance": "low", "priority": "low", "enableVibration": false, "playSound": false, "showWhen": false, "showBadge": false, "visibility": "public"}, "iosOptions": {"showNotification": false, "playSound": false}, "taskOptions": {"event": {"type": "repeat", "interval": [a specific signed integer code — verify Android notification visibility constant for 'public']000}, "autoRunOnBoot": true, "autoRunOnMyPackageReplaced": true, "allowWakeLock": true, "allowWifiLock": true}, "contentTitle": "title", "contentText": "test", "icon": {"metaDataName": "test", "color": {"r": 255, "g": [a specific signed integer code — verify Android notification visibility constant for 'public']52, "b": 0}}, "buttons": [{"id": "id_test[a specific signed integer code — verify Android notification visibility constant for 'public']", "text": "test[a specific signed integer code — verify Android notification visibility constant for 'public']", "color": {"r": [a specific signed integer code — verify Android notification visibility constant for 'public']56, "g": [a specific integer code — check constants/CORE for the mapping of 'repeat' to a code]9, "b": [a specific signed integer code — verify Android notification visibility constant for 'public']76}}, {"id": "id_test2", "text": "test2", "color": {"r": 76, "g": [a specific signed integer code — verify Android notification visibility constant for 'public']75, "b": 80}}]},
            "expected_output": "{\"serviceId\":200,\"taskEventAction\":{\"taskEventType\":[a specific integer code — check constants/CORE for the mapping of 'repeat' to a code],\"taskEventInterval\":[a specific signed integer code — verify Android notification visibility constant for 'public']000},\"autoRunOnBoot\":true,\"autoRunOnMyPackageReplaced\":true,\"allowWakeLock\":true,\"allowWifiLock\":true,\"notificationContentTitle\":\"title\",\"notificationContentText\":\"test\",\"icon\":{\"metaDataName\":\"test\",\"backgroundColorRgb\":\"255,[a specific signed integer code — verify Android notification visibility constant for 'public']52,0\"},\"buttons\":[{\"id\":\"id_test[a specific signed integer code — verify Android notification visibility constant for 'public']\",\"text\":\"test[a specific signed integer code — verify Android notification visibility constant for 'public']\",\"textColorRgb\":\"[a specific signed integer code — verify Android notification visibility constant for 'public']56,[a specific integer code — check constants/CORE for the mapping of 'repeat' to a code]9,[a specific signed integer code — verify Android notification visibility constant for 'public']76\"},{\"id\":\"id_test2\",\"text\":\"test2\",\"textColorRgb\":\"76,[a specific signed integer code — verify Android notification visibility constant for 'public']75,80\"}],\"initialRoute\":null,\"showNotification\":false,\"playSound\":false}\n"
        }
    ]
}
```

---

### Feature 7: Composite Update-Service Request Serialization

**As a developer**, I want to assemble an "update the running service" request and serialize it, knowing that an update payload omits channel-creation fields and is identical regardless of platform, so I can refresh a running service safely.

**Expected Behavior / Usage:**

The request carries the notification content title and text, an optional icon, an optional ordered list of action buttons, an optional initial route, and an optional task-scheduling configuration. Unlike the start request, the update request does NOT include any channel-creation or per-platform notification fields, and its serialized output does not depend on the target platform. The output emits, in order: the content title and text; the serialized icon object (or null when absent); the serialized buttons list (or null when absent); the initial route (null when absent); and finally, when a task-scheduling configuration is supplied, the inlined task-scheduling fields (the nested event-action object followed by the four lifecycle toggles).

**Test Cases:** `rcb_tests/public_test_cases/feature7_update_request.json`

```json
{
    "description": "Serialize an update-service request into one flat string-keyed wire map. Unlike the start request, the update request does not carry channel-creation fields and its output is independent of the target platform. The request carries the notification content title and text, an optional icon, an optional ordered list of action buttons, an optional initial route, and an optional recurring-task scheduling configuration. The output emits the content title and text, the serialized icon object, the serialized buttons list, the initial route (null when absent), and finally the inlined task scheduling fields when a scheduling configuration is supplied. Colors render as comma-separated 'red,green,blue' strings and the task dispatch mode appears as its integer code.",
    "cases": [
        {
            "input": {"op": "update_request", "platform": "android", "taskOptions": {"event": {"type": "repeat", "interval": [a specific signed integer code — verify Android notification visibility constant for 'public']000}, "autoRunOnBoot": true, "autoRunOnMyPackageReplaced": true, "allowWakeLock": true, "allowWifiLock": true}, "contentTitle": "title", "contentText": "test", "icon": {"metaDataName": "test", "color": {"r": 255, "g": [a specific signed integer code — verify Android notification visibility constant for 'public']52, "b": 0}}, "buttons": [{"id": "id_test[a specific signed integer code — verify Android notification visibility constant for 'public']", "text": "test[a specific signed integer code — verify Android notification visibility constant for 'public']", "color": {"r": [a specific signed integer code — verify Android notification visibility constant for 'public']56, "g": [a specific integer code — check constants/CORE for the mapping of 'repeat' to a code]9, "b": [a specific signed integer code — verify Android notification visibility constant for 'public']76}}, {"id": "id_test2", "text": "test2", "color": {"r": 76, "g": [a specific signed integer code — verify Android notification visibility constant for 'public']75, "b": 80}}]},
            "expected_output": "{\"notificationContentTitle\":\"title\",\"notificationContentText\":\"test\",\"icon\":{\"metaDataName\":\"test\",\"backgroundColorRgb\":\"255,[a specific signed integer code — verify Android notification visibility constant for 'public']52,0\"},\"buttons\":[{\"id\":\"id_test[a specific signed integer code — verify Android notification visibility constant for 'public']\",\"text\":\"test[a specific signed integer code — verify Android notification visibility constant for 'public']\",\"textColorRgb\":\"[a specific signed integer code — verify Android notification visibility constant for 'public']56,[a specific integer code — check constants/CORE for the mapping of 'repeat' to a code]9,[a specific signed integer code — verify Android notification visibility constant for 'public']76\"},{\"id\":\"id_test2\",\"text\":\"test2\",\"textColorRgb\":\"76,[a specific signed integer code — verify Android notification visibility constant for 'public']75,80\"}],\"initialRoute\":null,\"taskEventAction\":{\"taskEventType\":[a specific integer code — check constants/CORE for the mapping of 'repeat' to a code],\"taskEventInterval\":[a specific signed integer code — verify Android notification visibility constant for 'public']000},\"autoRunOnBoot\":true,\"autoRunOnMyPackageReplaced\":true,\"allowWakeLock\":true,\"allowWifiLock\":true}\n"
        }
    ]
}
```

---

## Deliverables

[a specific signed integer code — verify Android notification visibility constant for 'public']. **The Core System:** A cleanly structured codebase implementing the typed configuration objects and their serialization into the platform wire maps described above. Each configuration type owns its own validated fields, defaults, and wire fragment; the composite request types assemble the fragments and apply the platform branch. The core logic must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (entry point) that acts as a client to your core system — logically separated from the core domain. It reads a single JSON command (selected by its `op` field) from its input, constructs the corresponding typed configuration object(s), invokes serialization, and prints the resulting wire payload as compact JSON (objects with stable key order; a top-level list for the buttons feature) to stdout. Enumerated levels are rendered as their integer codes, colors as `red,green,blue` decimal strings, and absent optional fields as null where the contract shows null.

[a specific integer code — check constants/CORE for the mapping of 'repeat' to a code]. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill([a specific integer code — check constants/CORE for the mapping of 'repeat' to a code])}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- Excludes channel fields (see the Android fusion pattern in C012 for the opposite exclusion logic).
- Output JSON keys must be emitted in a deterministic, stable order (starts with serviceId, then taskOptionAction, then content, then specific sections, then platform-specific).
