## Product Requirement Document

# Voice Recognition Session Coordinator - Driving Speech-to-Text Over a Platform Message Channel

## Project Goal

Build a reusable coordinator that lets an application turn spoken audio into text by managing a recognition session end-to-end, so developers can start and stop listening, receive transcriptions and status updates, and handle errors through a single clean interface without re-implementing the bookkeeping around a device's native speech service.

---

## Background & Problem

A device's native speech service is driven through an asynchronous message channel: the application sends commands (check permission, initialize, start listening, stop, cancel) and the service sends back notifications (partial and final transcriptions, status changes, sound-level updates, errors). Working with that raw channel directly is tedious and error-prone — every application would have to track whether it is initialized, whether it is currently listening, deserialize each notification payload, route results to the right callback, and decide when an error should end the session.

This coordinator provides one well-defined contract over that channel. It exposes a small set of value objects (a recognition candidate, a recognition result built from ranked candidates, a recognition error, an event envelope, and a named locale), parses the wire payloads the service emits, tracks session state, forwards notifications to registered callbacks, and normalizes platform failures into stable, language-neutral error categories. The behavior is fully deterministic when driven against a mocked platform channel: no real audio, device, timer, or randomness is involved.

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

### Feature 1: Recognition Candidate

**As a developer**, I want a value object that pairs a transcribed phrase with a confidence score and answers questions about that confidence, so I can decide how much to trust a candidate transcription.

**Expected Behavior / Usage:**

*1.1 Confidence Evaluation — does this candidate clear the confidence bar?*

A candidate is "confident" when its confidence score is at least an acceptance threshold, or when its confidence is the reserved missing sentinel value. The threshold defaults to a standard value (0.8) but a caller may supply a different one. The missing sentinel is the value -1, which means the platform did not report a confidence; a candidate with the missing sentinel is always treated as confident, and is the only case for which the candidate is reported to have no confidence rating. Output reports the phrase, the numeric confidence, whether a real rating is present, and the confident verdict.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_candidate_confidence.json`

```json
{
    "description": "A recognition candidate pairs a transcribed phrase with a confidence score. Evaluate whether the candidate should be treated as confident. A candidate is confident when its confidence score meets or exceeds an acceptance threshold (defaulting to a standard value when none is supplied), or when its confidence is the reserved 'missing' sentinel (meaning the platform did not provide a score, in which case the candidate is always treated as confident). The output reports the transcribed phrase, the numeric confidence, whether a real confidence rating is present (false only for the missing sentinel), and the confident verdict.",
    "cases": [
        {
            "input": {
                "op": "candidate_confidence",
                "words": "hello",
                "confidence": 0.85
            },
            "expected_output": "recognized=hello\nconfidence=0.85\nhas_rating=true\nconfident=true\n"
        },
        {
            "input": {
                "op": "candidate_confidence",
                "words": "hello",
                "confidence": -1
            },
            "expected_output": "recognized=hello\nconfidence=-1.0\nhas_rating=false\nconfident=true\n"
        }
    ]
}
```

*1.2 Wire (De)serialization — round-trip a candidate through its JSON payload*

A candidate is reconstructed from a JSON object carrying a `recognizedWords` string and a `confidence` number, and serializes back to the identical JSON shape. Output reports the parsed phrase and confidence and the re-serialized JSON object.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_candidate_serialization.json`

```json
{
    "description": "A recognition candidate is reconstructed from its wire payload, a JSON object carrying the transcribed phrase and confidence score, and can be serialized back to the same wire shape. The output reports the parsed phrase and confidence and the re-serialized JSON object, demonstrating a lossless round trip.",
    "cases": [
        {
            "input": {
                "op": "candidate_json",
                "json": "{\"recognizedWords\":\"hello\",\"confidence\":0.85}"
            },
            "expected_output": "recognized=hello\nconfidence=0.85\njson={\"recognizedWords\":\"hello\",\"confidence\":0.85}\n"
        }
    ]
}
```

*1.3 Equality & Hashing — value identity by phrase and confidence*

Two candidates are equal when both their phrase and confidence match, and equal candidates produce equal hashes. Output reports the equality verdict and whether the hashes agree.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_candidate_equality.json`

```json
{
    "description": "Recognition candidates compare equal when both their transcribed phrase and their confidence score match, and equal candidates hash alike. The output reports whether two candidates are equal and whether their hashes agree.",
    "cases": [
        {
            "input": {
                "op": "candidate_equality",
                "first": {
                    "words": "hello",
                    "confidence": 0.85
                },
                "second": {
                    "words": "hello",
                    "confidence": 0.85
                }
            },
            "expected_output": "equal=true\nhash_equal=true\n"
        }
    ]
}
```

---

### Feature 2: Recognition Result

**As a developer**, I want a value object that aggregates an ordered list of alternative candidates plus a final-or-interim flag and derives a single best transcription, so I can consume one result without ranking candidates myself.

**Expected Behavior / Usage:**

*2.1 Best-Transcription Derivation — summarize a result from its alternates*

A result holds the alternates in order plus a `final` flag. The best transcription and its confidence come from the first alternate; the confident verdict and rating presence also mirror the first alternate. When the alternates list is empty, the best transcription is the empty string, the confidence is zero, the result is not confident, and it has no rating. Output reports the best transcription, derived confidence, final flag, confident verdict, rating presence, the alternate count, and each alternate's phrase and confidence in order.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_result_summary.json`

```json
{
    "description": "A recognition result holds an ordered list of alternative candidate transcriptions plus a flag marking whether it is the final result for the utterance. The best transcription and its confidence are derived from the first alternate; when there are no alternates the best transcription is the empty string, the confidence is zero, the result is not considered confident, and it has no confidence rating. The output reports the best transcription, derived confidence, final flag, confident verdict, rating presence, the number of alternates, and each alternate's phrase and confidence in order.",
    "cases": [
        {
            "input": {
                "op": "result_summary",
                "alternates": [
                    {
                        "words": "hello",
                        "confidence": 0.85
                    },
                    {
                        "words": "hello there",
                        "confidence": 0.62
                    }
                ],
                "final": true
            },
            "expected_output": "recognized=hello\nconfidence=0.85\nfinal=true\nconfident=true\nhas_rating=true\nalternate_count=2\nalternate[0]=hello@0.85\nalternate[1]=hello there@0.62\n"
        }
    ]
}
```

*2.2 Wire (De)serialization — round-trip a result through its JSON payload*

A result is reconstructed from a JSON object carrying an ordered `alternates` array (each element the candidate wire shape) and a `finalResult` flag, and serializes back to the identical shape. Output reports the derived best transcription, its confidence, the final flag, and the re-serialized JSON object.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_result_serialization.json`

```json
{
    "description": "A recognition result is reconstructed from its wire payload, a JSON object carrying the ordered alternates array and the final flag, and can be serialized back to the same wire shape. The output reports the derived best transcription, its confidence, the final flag, and the re-serialized JSON object.",
    "cases": [
        {
            "input": {
                "op": "result_json",
                "json": "{\"alternates\":[{\"recognizedWords\":\"hello\",\"confidence\":0.85}],\"finalResult\":false}"
            },
            "expected_output": "recognized=hello\nconfidence=0.85\nfinal=false\njson={\"alternates\":[{\"recognizedWords\":\"hello\",\"confidence\":0.85}],\"finalResult\":false}\n"
        }
    ]
}
```

*2.3 Equality & Hashing — value identity by best transcription and final flag*

Two results are equal when their best transcription (the first alternate's phrase) and their final flag match; the remaining alternates do not affect equality, and equal results hash alike. Output reports the equality verdict and whether the hashes agree.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_result_equality.json`

```json
{
    "description": "Recognition results compare equal when their best transcription (the first alternate's phrase) and their final flag match; the remaining alternates do not affect equality, and equal results hash alike. The output reports whether two results are equal and whether their hashes agree.",
    "cases": [
        {
            "input": {
                "op": "result_equality",
                "first": {
                    "alternates": [
                        {
                            "words": "hello",
                            "confidence": 0.85
                        }
                    ],
                    "final": true
                },
                "second": {
                    "alternates": [
                        {
                            "words": "hello",
                            "confidence": 0.85
                        }
                    ],
                    "final": true
                }
            },
            "expected_output": "equal=true\nhash_equal=true\n"
        }
    ]
}
```

---

### Feature 3: Recognition Error

**As a developer**, I want a value object describing a recognition failure with a permanence flag, so I can tell whether the session can continue or is blocked until the condition is fixed.

**Expected Behavior / Usage:**

*3.1 Wire (De)serialization — round-trip an error through its JSON payload*

An error carries an `errorMsg` identifier and a `permanent` flag. It is reconstructed from a JSON object with those two fields and serializes back to the identical shape. The permanence flag distinguishes a transient failure (recognition may retry) from a permanent one (blocked until resolved). Output reports the identifier, the permanence flag, and the re-serialized JSON object.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_error_serialization.json`

```json
{
    "description": "A recognition error carries a short error identifier and a permanence flag that states whether recognition can continue (transient) or is blocked until the condition is resolved (permanent). It is reconstructed from its wire payload, a JSON object with the identifier and permanence flag, and serialized back to the same shape. The output reports the identifier, the permanence flag, and the re-serialized JSON object.",
    "cases": [
        {
            "input": {
                "op": "error_json",
                "json": "{\"errorMsg\":\"network\",\"permanent\":true}"
            },
            "expected_output": "error_msg=network\npermanent=true\njson={\"errorMsg\":\"network\",\"permanent\":true}\n"
        }
    ]
}
```

*3.2 Equality & Hashing — value identity by identifier and permanence*

Two errors are equal when both their identifier and permanence flag match, and equal errors hash alike. Output reports the equality verdict and whether the hashes agree.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_error_equality.json`

```json
{
    "description": "Recognition errors compare equal when both their error identifier and permanence flag match, and equal errors hash alike. The output reports whether two errors are equal and whether their hashes agree.",
    "cases": [
        {
            "input": {
                "op": "error_equality",
                "first": {
                    "msg": "msg1",
                    "permanent": false
                },
                "second": {
                    "msg": "msg1",
                    "permanent": false
                }
            },
            "expected_output": "equal=true\nhash_equal=true\n"
        }
    ]
}
```

---

### Feature 4: Recognition Event Envelope

**As a developer**, I want a single tagged envelope type carried on the recognition event stream, so a stream consumer can switch on the event kind and read only the payload relevant to that kind.

**Expected Behavior / Usage:**

An event has a kind that selects which payload is meaningful: a status event exposes the listening flag, a final-result event exposes the recognition result, an error event exposes the recognition error, and a sound-level event exposes the input loudness level. The other payload slots are unused for a given kind. Output reports the event kind and the accessor relevant to that kind.

**Test Cases:** `rcb_tests/public_test_cases/feature4_recognition_event.json`

```json
{
    "description": "A recognition event is a tagged envelope delivered on the event stream. Its kind selects which payload is meaningful: a status event exposes the listening flag, a final-result event exposes the recognition result, an error event exposes the recognition error, and a sound-level event exposes the input loudness level. The output reports the event kind and the accessor relevant to that kind.",
    "cases": [
        {
            "input": {
                "op": "event",
                "type": "status",
                "listening": true
            },
            "expected_output": "type=status\nlistening=true\n"
        },
        {
            "input": {
                "op": "event",
                "type": "sound",
                "level": 0.5
            },
            "expected_output": "type=sound_level\nlevel=0.5\n"
        }
    ]
}
```

---

### Feature 5: Locale Catalog

**As a developer**, I want the platform's list of supported recognition locales parsed into named locale objects with a designated system default, so I can present choices and know which one is used when none is specified.

**Expected Behavior / Usage:**

*5.1 Catalog Parsing — parse, filter, order, and pick the system default*

The platform supplies the catalog as a list of `identifier:display name` strings. Each well-formed entry (exactly one identifier and one name separated by a single colon) becomes a locale; malformed entries are dropped. The returned list is ordered by display name. The system (default) locale is the first well-formed entry in the ORIGINAL platform order — that is, before the display-name sort — or none when there are no well-formed entries. Output reports the parsed count, each parsed locale's identifier and display name in returned order, and the system locale's identifier.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_locale_parsing.json`

```json
{
    "description": "The set of supported recognition locales is supplied by the platform as a list of colon-separated 'identifier:display name' strings. Each well-formed entry becomes a locale with an identifier and a display name; entries that are not exactly one identifier and one name are dropped. The returned list is ordered by display name. The system (default) locale is the first well-formed entry in the ORIGINAL platform order (before the display-name sort). The output reports the count of parsed locales, each parsed locale's identifier and display name in returned order, and the system locale's identifier.",
    "cases": [
        {
            "input": {
                "op": "locales",
                "raw": [
                    "en_US:English US",
                    "fr_CA:French Canada"
                ]
            },
            "expected_output": "count=2\nlocale[0]=en_US|English US\nlocale[1]=fr_CA|French Canada\nsystem=en_US\n"
        },
        {
            "input": {
                "op": "locales",
                "raw": [
                    "fr_CA:Zebra",
                    "en_US:Apple"
                ]
            },
            "expected_output": "count=2\nlocale[0]=en_US|Apple\nlocale[1]=fr_CA|Zebra\nsystem=fr_CA\n"
        }
    ]
}
```

*5.2 Initialization Guard — locale catalog requires initialization*

Requesting the catalog before the coordinator has been initialized is rejected with a normalized not-initialized error and never reaches the platform.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_locale_requires_init.json`

```json
{
    "description": "Querying the supported locales before the coordinator has been initialized is rejected: the operation reports a normalized not-initialized error rather than reaching the platform.",
    "cases": [
        {
            "input": {
                "op": "locales_uninitialized"
            },
            "expected_output": "[normalized error for missing initialization]\n"
        }
    ]
}
```

---

### Feature 6: Recognition Session Lifecycle

**As a developer**, I want the coordinator to manage a recognition session over the platform channel — permission, initialization, listening, result/status/sound notifications, stop/cancel, and error policy — while tracking observable state, so I can run a full session through one interface.

The session is driven by a sequence of steps against a mocked platform channel. Each step that touches the platform reports whether the corresponding platform operation was invoked (so that bypassing the channel is observable), callbacks report their payloads as they fire, and a state snapshot reports `listening`, `recognized`, `available`, `has_error`, the last recognized phrase, the last status, and the last sound level. When the platform accepts a listen request it immediately reports a `listening` status back, which is why an active session is listening after a successful listen.

**Expected Behavior / Usage:**

*6.1 Permission Query — has microphone access already been granted?*

The coordinator asks the platform whether permission has already been granted, without prompting the user, and reports the verdict.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_permission.json`

```json
{
    "description": "The coordinator can report whether microphone permission has already been granted by querying the platform, without prompting the user. The output reports the permission verdict returned by the platform.",
    "cases": [
        {
            "input": {
                "op": "session",
                "config": {
                    "has_permission": true
                },
                "steps": [
                    {
                        "do": "permission"
                    }
                ]
            },
            "expected_output": "has_permission=true\n"
        }
    ]
}
```

*6.2 Initialization — idempotent setup with success/failure reporting*

Initialization prepares the coordinator and returns whether it succeeded. It is idempotent: after a success, calling it again returns success WITHOUT re-invoking the platform initialize operation. When the platform reports failure, initialization returns failure and the coordinator stays unavailable. Output reports, per initialize call, the result and whether the platform was invoked, then an availability snapshot.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_initialization.json`

```json
{
    "description": "Initialization prepares the coordinator and returns whether it succeeded. It is idempotent: once it has succeeded, calling it again returns success WITHOUT re-invoking the platform initialize operation. When the platform reports failure, initialization returns failure and the coordinator remains unavailable. The output reports, per initialize call, the returned result and whether the platform initialize was invoked, followed by an availability snapshot.",
    "cases": [
        {
            "input": {
                "op": "session",
                "config": {
                    "init_result": true
                },
                "steps": [
                    {
                        "do": "initialize"
                    },
                    {
                        "do": "initialize"
                    },
                    {
                        "do": "state"
                    }
                ]
            },
            "expected_output": "init result=true invoked=true\ninit result=true invoked=false\nlistening=false recognized=false available=true has_error=false last_recognized= last_status= last_level=0.0\n"
        }
    ]
}
```

*6.3 Listening — guard, platform invocation, locale forwarding, failure translation*

Starting a listening session requires a prior successful initialization; otherwise it is rejected with a normalized not-initialized error and the platform listen is never invoked. After successful initialization, listening invokes the platform listen operation; an optional locale identifier is forwarded when provided and absent otherwise. If the platform raises a listen failure, it is translated into a normalized listen-failed error that carries the platform-supplied failure detail. Output reports the initialize result and the listen outcome (invoked flag and forwarded locale, or the normalized error).

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_listen.json`

```json
{
    "description": "Starting a listening session requires a prior successful initialization; otherwise it is rejected with a normalized not-initialized error and the platform listen is never invoked. After successful initialization, listening invokes the platform listen operation; an optional locale identifier is forwarded to the platform when provided, and is absent otherwise. If the platform raises a listen failure, it is translated into a normalized listen-failed error that carries the platform-supplied failure detail. The output reports, per step, the initialize result and the listen outcome (invoked flag and forwarded locale, or the normalized error).",
    "cases": [
        {
            "input": {
                "op": "session",
                "config": {},
                "steps": [
                    {
                        "do": "initialize"
                    },
                    {
                        "do": "listen"
                    }
                ]
            },
            "expected_output": "init result=true invoked=true\nlisten invoked=true locale=none\n"
        },
        {
            "input": {
                "op": "session",
                "config": {
                    "listen_throws": true
                },
                "steps": [
                    {
                        "do": "initialize"
                    },
                    {
                        "do": "listen"
                    }
                ]
            },
            "expected_output": "init result=true invoked=true\nlisten error=listen_failed details=Device Listen Failure\n"
        }
    ]
}
```

*6.4 Recognition Notifications — parse payloads, invoke callback, remember last phrase*

While listening, each recognition payload delivered by the platform is parsed into a result and handed to the registered result callback, and the coordinator remembers the most recently recognized phrase. Multiple deliveries invoke the callback once each in order, and the remembered phrase tracks the latest delivery. Output reports each callback invocation (phrase and final flag) followed by a state snapshot whose remembered phrase reflects the last delivery.

**Test Cases:** `rcb_tests/public_test_cases/feature6_4_recognition_callback.json`

```json
{
    "description": "While listening, each recognition payload delivered by the platform is parsed into a recognition result and handed to the registered result callback, and the coordinator remembers the most recently recognized phrase. Multiple deliveries invoke the callback once each in order, and the remembered phrase tracks the latest delivery. The output reports each callback invocation (recognized phrase and final flag) followed by a state snapshot whose remembered phrase reflects the last delivery.",
    "cases": [
        {
            "input": {
                "op": "session",
                "config": {},
                "steps": [
                    {
                        "do": "initialize"
                    },
                    {
                        "do": "listen",
                        "onResult": true
                    },
                    {
                        "do": "deliver",
                        "method": "recognition",
                        "payload": "{\"alternates\":[{\"recognizedWords\":\"hello\",\"confidence\":0.85}],\"finalResult\":false}"
                    },
                    {
                        "do": "state"
                    }
                ]
            },
            "expected_output": "init result=true invoked=true\nlisten invoked=true locale=none\nresult recognized=hello final=false\nlistening=true recognized=true available=true has_error=false last_recognized=hello last_status=listening last_level=0.0\n"
        }
    ]
}
```

*6.5 Status Notifications — forward status changes*

A status update delivered by the platform is forwarded to the registered status callback with the new status string. Output reports the forwarded status.

**Test Cases:** `rcb_tests/public_test_cases/feature6_5_status_callback.json`

```json
{
    "description": "A status update delivered by the platform is forwarded to the registered status callback with the new status string. The output reports the forwarded status.",
    "cases": [
        {
            "input": {
                "op": "session",
                "config": {},
                "steps": [
                    {
                        "do": "initialize",
                        "onStatus": true
                    },
                    {
                        "do": "deliver",
                        "method": "status",
                        "payload": "listening"
                    }
                ]
            },
            "expected_output": "init result=true invoked=true\nstatus listening\n"
        }
    ]
}
```

*6.6 Sound-Level Notifications — forward and record loudness*

While a session is active, a sound-level update delivered by the platform is forwarded to the registered sound-level callback and recorded as the last sound level. Output reports the forwarded level followed by a state snapshot whose last sound level reflects the delivery.

**Test Cases:** `rcb_tests/public_test_cases/feature6_6_sound_level_callback.json`

```json
{
    "description": "While a listening session is active, a sound-level update delivered by the platform is forwarded to the registered sound-level callback and recorded as the last sound level. The output reports the forwarded level followed by a state snapshot whose last sound level reflects the delivery.",
    "cases": [
        {
            "input": {
                "op": "session",
                "config": {},
                "steps": [
                    {
                        "do": "initialize"
                    },
                    {
                        "do": "listen",
                        "onSound": true
                    },
                    {
                        "do": "deliver",
                        "method": "sound",
                        "payload": 0.5
                    },
                    {
                        "do": "state"
                    }
                ]
            },
            "expected_output": "init result=true invoked=true\nlisten invoked=true locale=none\nsound_level 0.5\nlistening=true recognized=false available=true has_error=false last_recognized= last_status=listening last_level=0.5\n"
        }
    ]
}
```

*6.7 Stop & Cancel — terminate a session*

Stopping or cancelling does nothing when the coordinator was never initialized: the corresponding platform operation is not invoked. After a successful initialization and an active session, stopping invokes the platform stop operation, and cancelling invokes the platform cancel operation and leaves the session no longer listening. Output reports whether the platform operation was invoked, plus a state snapshot where relevant.

**Test Cases:** `rcb_tests/public_test_cases/feature6_7_stop_cancel.json`

```json
{
    "description": "Stopping or cancelling does nothing when the coordinator was never initialized: the corresponding platform operation is not invoked. After a successful initialization and an active listening session, stopping invokes the platform stop operation, and cancelling invokes the platform cancel operation and leaves the session no longer listening. The output reports whether the platform operation was invoked, and a state snapshot where relevant.",
    "cases": [
        {
            "input": {
                "op": "session",
                "config": {},
                "steps": [
                    {
                        "do": "initialize"
                    },
                    {
                        "do": "listen"
                    },
                    {
                        "do": "cancel"
                    },
                    {
                        "do": "state"
                    }
                ]
            },
            "expected_output": "init result=true invoked=true\nlisten invoked=true locale=none\ncancel invoked=true\nlistening=false recognized=false available=true has_error=false last_recognized= last_status=listening last_level=0.0\n"
        },
        {
            "input": {
                "op": "session",
                "config": {},
                "steps": [
                    {
                        "do": "initialize"
                    },
                    {
                        "do": "listen"
                    },
                    {
                        "do": "stop"
                    }
                ]
            },
            "expected_output": "init result=true invoked=true\nlisten invoked=true locale=none\nstop invoked=true\n"
        }
    ]
}
```

*6.8 Error Policy — forward, continue-or-stop, and post-cancel suppression*

An error delivered during an active session is forwarded to the registered error callback. A transient error does not stop the session. A permanent error stops the session ONLY when the session was started with cancel-on-error enabled; otherwise it keeps listening. After the user has explicitly cancelled, a subsequently delivered error is suppressed. When cancel-on-error triggers an implicit cancel, a further delivered error is still forwarded. Output reports each forwarded error (identifier and permanence) interleaved with state snapshots as the steps specify.

**Test Cases:** `rcb_tests/public_test_cases/feature6_8_error_handling.json`

```json
{
    "description": "An error delivered by the platform during an active session is forwarded to the registered error callback. A transient error does not stop the session. A permanent error stops the session ONLY when the session was started with cancel-on-error enabled; otherwise the session keeps listening. Once the session has been explicitly cancelled by the user, a subsequently delivered error is suppressed (not forwarded). When cancel-on-error triggers an implicit cancel, a further delivered error is still forwarded. The output reports each forwarded error (identifier and permanence) interleaved with state snapshots as specified by the steps.",
    "cases": [
        {
            "input": {
                "op": "session",
                "config": {},
                "steps": [
                    {
                        "do": "initialize",
                        "onError": true
                    },
                    {
                        "do": "listen"
                    },
                    {
                        "do": "deliver",
                        "method": "error",
                        "payload": "{\"errorMsg\":\"network\",\"permanent\":true}"
                    },
                    {
                        "do": "state"
                    }
                ]
            },
            "expected_output": "init result=true invoked=true\nlisten invoked=true locale=none\nerror msg=network permanent=true\nlistening=true recognized=false available=true has_error=true last_recognized= last_status=listening last_level=0.0\n"
        },
        {
            "input": {
                "op": "session",
                "config": {},
                "steps": [
                    {
                        "do": "initialize",
                        "onError": true
                    },
                    {
                        "do": "listen"
                    },
                    {
                        "do": "cancel"
                    },
                    {
                        "do": "deliver",
                        "method": "error",
                        "payload": "{\"errorMsg\":\"network\",\"permanent\":true}"
                    },
                    {
                        "do": "state"
                    }
                ]
            },
            "expected_output": "init result=true invoked=true\nlisten invoked=true locale=none\ncancel invoked=true\nlistening=false recognized=false available=true has_error=false last_recognized= last_status=listening last_level=0.0\n"
        }
    ]
}
```

*6.9 Initial State — the starting snapshot*

Before any initialization or listening, the coordinator exposes a well-defined starting snapshot: not listening, nothing recognized, unavailable, no error, an empty remembered phrase, an empty last status, and a zero last sound level.

**Test Cases:** `rcb_tests/public_test_cases/feature6_9_initial_state.json`

```json
{
    "description": "Before any initialization or listening, the coordinator exposes a well-defined starting snapshot: it is not listening, has recognized nothing, is unavailable, has no error, has an empty remembered phrase, an empty last status, and a zero last sound level.",
    "cases": [
        {
            "input": {
                "op": "session",
                "config": {},
                "steps": [
                    {
                        "do": "state"
                    }
                ]
            },
            "expected_output": "listening=false recognized=false available=false has_error=false last_recognized= last_status= last_level=0.0\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the value objects (recognition candidate, recognition result, recognition error, recognition event envelope, named locale) and the session coordinator described above. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, selects behavior from the request's `op` field, drives the core logic (for session operations, against a mocked platform channel using the provided `config` and `steps`), and prints the resulting plain-text contract to stdout, matching the per-feature contracts above. Native exceptions raised by the core must be translated in this adapter layer into the normalized `error=<category>` / `... error=<category>` lines shown above; they must never leak host-language runtime identifiers.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- validate error forwarding logic against cancellation flag
