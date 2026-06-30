## Product Requirement Document

# Realtime Channel Messaging Server — Pub/Sub Protocol, Presence Channels & Channel Inspection API

## Project Goal

Build the deterministic core of a realtime messaging server that lets clients subscribe to named channels over a long-lived connection and exchange events, so application developers can push live updates to many clients without hand-rolling connection bookkeeping, channel authorization, presence tracking, and a server-side inspection API.

---

## Background & Problem

Realtime features (live dashboards, chat, notifications) require a server that accepts many client connections, lets each client subscribe to named channels, fans events out to the right subscribers, and keeps an accurate picture of who is connected where. Doing this by hand is repetitive and error-prone: developers must invent their own subscribe/unsubscribe handshake, re-implement authorization for restricted channels, track presence membership, and expose an API for other services to query channel occupancy.

This project provides that core as reusable, deterministic logic. It speaks a small pub/sub control protocol over a connection abstraction: a client sends control frames (subscribe, unsubscribe, ping, and client-originated events) and the server replies with acknowledgement and data frames. Restricted channels are gated by an HMAC signature scheme; presence channels additionally track member rosters. A separate signed HTTP-style inspection API reports occupied channels, single-channel occupancy, and presence members. The connection transport itself (sockets, event loop) is out of scope — the logic operates on an injected connection abstraction, which is what makes it deterministic and testable.

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

## Domain Conventions (shared by all features)

An **application** is an identity record with a numeric `id`, a public `key`, a secret `secret`, a display `name`, and two boolean flags: whether client-originated messaging is enabled and whether statistics are enabled. Unless a case overrides it via an `app` block, the configured application is `{id: 1234, key: "TestKey", secret: "TestSecret", name: "Test App", client messaging disabled, statistics enabled}`.

A **connection** is an abstract client endpoint that the adapter can write frames to. The adapter assigns each connection a stable `socket_id` (the real transport id is random and out of scope). Frames written to a connection are JSON objects rendered as compact JSON strings.

**Channel kinds** are decided purely by the channel name prefix: a name starting with `private-` is a restricted channel, a name starting with `presence-` is a presence channel, and any other name is an open channel.

**Subscription signature.** Restricted and presence channels require an auth token of the form `<key>:<hmac>`, where `<hmac>` is the lowercase hex HMAC-SHA256, keyed by the application `secret`, of the string `<socket_id>:<channel>` for restricted channels, or `<socket_id>:<channel>:<channel_data>` for presence channels (`channel_data` being the exact member JSON string supplied on subscribe).

**Adapter request shape.** The adapter reads ONE JSON object from stdin and selects behavior by its `action` field. The session-oriented actions describe a list of named `connections` and a list of `events` to apply in order; a `report` block names which connections' received frames and which channels' occupancy to print. Output is line-oriented text. A connection report is a line `[<name>] received <N>` followed by `<N>` raw frame lines. A channel report is `[channel:<name>] occupied=<bool> subscription_count=<n>` (with ` user_count=<n>` appended for presence channels) or `[channel:<name>] absent` if the channel is no longer tracked. Errors are normalized to neutral lines such as `error=<category>` plus a `code=<n>` line (for protocol errors) or `status=<n>` and `message=<text>` lines (for inspection-API errors).

---

## Core Features

### Feature 1: Subscribe To An Open Channel

**As a developer**, I want a client to subscribe to an open channel and get a confirmation, so it can start receiving events on that channel.

**Expected Behavior / Usage:**

A client subscribes by sending a `pusher:subscribe` control frame whose data names a channel. For an open channel (a name without a restricted or presence prefix), the server registers the client and replies to that same client with exactly one frame: `{"event":"pusher_internal:subscription_succeeded","channel":"<name>"}`. No signature is required. The report prints, per client, the number of frames received followed by each raw frame.

**Test Cases:** `rcb_tests/public_test_cases/feature1_public_subscription.json`

```json
{
    "description": "A client opens a subscription to an open (non-restricted) channel by sending a subscribe control message naming the channel. The server registers the client on that channel and sends back exactly one acknowledgement event confirming the subscription for that channel name. The report lists, per client, how many frames it received followed by each raw frame.",
    "cases": [
        {
            "input": {
                "action": "session",
                "connections": [
                    {
                        "name": "a",
                        "socket_id": "100.1"
                    }
                ],
                "events": [
                    {
                        "type": "message",
                        "conn": "a",
                        "payload": {
                            "event": "pusher:subscribe",
                            "data": {
                                "channel": "basic-channel"
                            }
                        }
                    }
                ]
            },
            "expected_output": "[a] received 1\n{\"event\":\"pusher_internal:subscription_succeeded\",\"channel\":\"basic-channel\"}\n"
        }
    ]
}
```

---
### Feature 2: Unsubscribe From A Channel

**As a developer**, I want a client to leave a channel it joined, so the channel stops counting it as a subscriber.

**Expected Behavior / Usage:**

After subscribing to an open channel, a client sends a `pusher:unsubscribe` control frame naming that channel. The server removes the client from the channel's subscriber set. The channel record still exists but now reports `occupied=false` and `subscription_count=0`. The report shows the client's received frames (its earlier acknowledgement) and the channel's post-operation occupancy.

**Test Cases:** `rcb_tests/public_test_cases/feature2_unsubscribe.json`

```json
{
    "description": "A client first subscribes to an open channel and then sends an unsubscribe control message for the same channel. After unsubscribing, the channel still exists but no longer counts that client: its occupancy flag is false and its subscriber count is zero. The report shows the client's received frames and the post-operation channel occupancy/subscription count.",
    "cases": [
        {
            "input": {
                "action": "session",
                "connections": [
                    {
                        "name": "a",
                        "socket_id": "100.1"
                    }
                ],
                "events": [
                    {
                        "type": "message",
                        "conn": "a",
                        "payload": {
                            "event": "pusher:subscribe",
                            "data": {
                                "channel": "test-channel"
                            }
                        }
                    },
                    {
                        "type": "message",
                        "conn": "a",
                        "payload": {
                            "event": "pusher:unsubscribe",
                            "data": {
                                "channel": "test-channel"
                            }
                        }
                    }
                ],
                "report": {
                    "connections": [
                        "a"
                    ],
                    "channels": [
                        "test-channel"
                    ]
                }
            },
            "expected_output": "[a] received 1\n{\"event\":\"pusher_internal:subscription_succeeded\",\"channel\":\"test-channel\"}\n[channel:test-channel] occupied=false subscription_count=0\n"
        }
    ]
}
```

---
### Feature 3: Keep-Alive Ping/Pong

**As a developer**, I want a connected client to verify the link is alive, so it can detect a dead connection.

**Expected Behavior / Usage:**

A client sends a `pusher:ping` control frame. The server replies to that client with exactly one frame `{"event":"pusher:pong"}` and nothing else.

**Test Cases:** `rcb_tests/public_test_cases/feature3_ping_pong.json`

```json
{
    "description": "A connected client sends a protocol-level ping control message. The server replies to that same client with a single pong event and nothing else. This is the keep-alive handshake of the protocol.",
    "cases": [
        {
            "input": {
                "action": "session",
                "connections": [
                    {
                        "name": "a",
                        "socket_id": "5.5"
                    }
                ],
                "events": [
                    {
                        "type": "message",
                        "conn": "a",
                        "payload": {
                            "event": "pusher:ping"
                        }
                    }
                ]
            },
            "expected_output": "[a] received 1\n{\"event\":\"pusher:pong\"}\n"
        }
    ]
}
```

---
### Feature 4: Broadcast To All Subscribers

**As a developer**, I want to push a payload to every subscriber of a channel, so all connected clients receive the same event.

**Expected Behavior / Usage:**

Given several clients subscribed to the same channel, broadcasting a payload on that channel delivers that exact payload frame to every current subscriber. Each subscriber therefore ends up with its earlier subscription acknowledgement plus the broadcast frame. The report shows each client's full received frame list.

**Test Cases:** `rcb_tests/public_test_cases/feature4_broadcast_all.json`

```json
{
    "description": "Two clients are subscribed to the same channel. A payload is then broadcast on that channel to every subscriber. Both clients receive the broadcast frame (in addition to their earlier subscription acknowledgement). The report shows each client's full received frame list.",
    "cases": [
        {
            "input": {
                "action": "session",
                "connections": [
                    {
                        "name": "a",
                        "socket_id": "1.1"
                    },
                    {
                        "name": "b",
                        "socket_id": "2.2"
                    }
                ],
                "events": [
                    {
                        "type": "message",
                        "conn": "a",
                        "payload": {
                            "event": "pusher:subscribe",
                            "data": {
                                "channel": "test-channel"
                            }
                        }
                    },
                    {
                        "type": "message",
                        "conn": "b",
                        "payload": {
                            "event": "pusher:subscribe",
                            "data": {
                                "channel": "test-channel"
                            }
                        }
                    },
                    {
                        "type": "broadcast",
                        "channel": "test-channel",
                        "payload": {
                            "event": "broadcasted-event",
                            "channel": "test-channel"
                        }
                    }
                ]
            },
            "expected_output": "[a] received 2\n{\"event\":\"pusher_internal:subscription_succeeded\",\"channel\":\"test-channel\"}\n{\"event\":\"broadcasted-event\",\"channel\":\"test-channel\"}\n[b] received 2\n{\"event\":\"pusher_internal:subscription_succeeded\",\"channel\":\"test-channel\"}\n{\"event\":\"broadcasted-event\",\"channel\":\"test-channel\"}\n"
        }
    ]
}
```

---
### Feature 5: Broadcast To Everyone Except One

**As a developer**, I want to push a payload to all subscribers except a specific one, so the originator of an action does not receive its own echo.

**Expected Behavior / Usage:**

Given several clients subscribed to the same channel, broadcasting a payload to everyone except one named client delivers the frame to all subscribers other than the excluded one. The excluded client's received list does not contain the broadcast frame; every other subscriber's does. The report shows each client's received frames so the exclusion is observable.

**Test Cases:** `rcb_tests/public_test_cases/feature5_broadcast_to_others.json`

```json
{
    "description": "Two clients are subscribed to the same channel. A payload is broadcast on that channel to everyone EXCEPT one named client. That excluded client does NOT receive the broadcast frame, while every other subscriber does. The report shows each client's received frame list so the exclusion is visible.",
    "cases": [
        {
            "input": {
                "action": "session",
                "connections": [
                    {
                        "name": "a",
                        "socket_id": "1.1"
                    },
                    {
                        "name": "b",
                        "socket_id": "2.2"
                    }
                ],
                "events": [
                    {
                        "type": "message",
                        "conn": "a",
                        "payload": {
                            "event": "pusher:subscribe",
                            "data": {
                                "channel": "test-channel"
                            }
                        }
                    },
                    {
                        "type": "message",
                        "conn": "b",
                        "payload": {
                            "event": "pusher:subscribe",
                            "data": {
                                "channel": "test-channel"
                            }
                        }
                    },
                    {
                        "type": "broadcast_to_others",
                        "channel": "test-channel",
                        "conn": "a",
                        "payload": {
                            "event": "broadcasted-event",
                            "channel": "test-channel"
                        }
                    }
                ]
            },
            "expected_output": "[a] received 1\n{\"event\":\"pusher_internal:subscription_succeeded\",\"channel\":\"test-channel\"}\n[b] received 2\n{\"event\":\"pusher_internal:subscription_succeeded\",\"channel\":\"test-channel\"}\n{\"event\":\"broadcasted-event\",\"channel\":\"test-channel\"}\n"
        }
    ]
}
```

---
### Feature 6: Disconnect Cleanup

**As a developer**, I want a disconnecting client to be removed from every channel it joined, so stale subscribers never linger.

**Expected Behavior / Usage:**

A client subscribes to multiple channels and then disconnects (a `close` event). On disconnect the server removes the client from all of its channels; any channel left with zero subscribers is discarded entirely and is no longer tracked. The report queries those channels afterwards and shows each as `absent`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_disconnect_cleanup.json`

```json
{
    "description": "A client subscribes to several channels and then disconnects. On disconnect the server removes that client from every channel it had joined; channels left with no remaining subscribers are discarded entirely. The report queries those channels afterwards and shows each as absent (no longer tracked).",
    "cases": [
        {
            "input": {
                "action": "session",
                "connections": [
                    {
                        "name": "a",
                        "socket_id": "1.1"
                    }
                ],
                "events": [
                    {
                        "type": "message",
                        "conn": "a",
                        "payload": {
                            "event": "pusher:subscribe",
                            "data": {
                                "channel": "test-channel-1"
                            }
                        }
                    },
                    {
                        "type": "message",
                        "conn": "a",
                        "payload": {
                            "event": "pusher:subscribe",
                            "data": {
                                "channel": "test-channel-2"
                            }
                        }
                    },
                    {
                        "type": "close",
                        "conn": "a"
                    }
                ],
                "report": {
                    "connections": [],
                    "channels": [
                        "test-channel-1",
                        "test-channel-2"
                    ]
                }
            },
            "expected_output": "[channel:test-channel-1] absent\n[channel:test-channel-2] absent\n"
        }
    ]
}
```

---
### Feature 7: Client-Originated Event Relay

**As a developer**, I want client-sent events to reach the other subscribers only when the application explicitly allows it, so untrusted client traffic is gated.

**Expected Behavior / Usage:**

An event whose name begins with the `client-` prefix, sent by a subscriber of a channel, is relayed to the *other* subscribers of that channel only when the application has client messaging enabled; when disabled it is silently dropped. In all cases the sender never receives its own client event back. The first case (client messaging disabled) shows a peer subscriber receiving only its subscription acknowledgement; the second case (enabled via an `app` override) shows the peer additionally receiving the relayed client event, re-serialized with its original `event`, `channel` and `data`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_client_messages.json`

```json
{
    "description": "Client-originated events (events whose name begins with the client- prefix) are only relayed to other subscribers of the channel when the application has client messaging enabled; otherwise they are silently dropped. In both cases the sender never receives its own client event back. The report shows a peer subscriber's received frames: with messaging disabled it only has its subscription acknowledgement; with messaging enabled it additionally receives the relayed client event carrying the original payload.",
    "cases": [
        {
            "input": {
                "action": "session",
                "connections": [
                    {
                        "name": "a",
                        "socket_id": "1.1"
                    },
                    {
                        "name": "b",
                        "socket_id": "2.2"
                    }
                ],
                "events": [
                    {
                        "type": "message",
                        "conn": "a",
                        "payload": {
                            "event": "pusher:subscribe",
                            "data": {
                                "channel": "test-channel"
                            }
                        }
                    },
                    {
                        "type": "message",
                        "conn": "b",
                        "payload": {
                            "event": "pusher:subscribe",
                            "data": {
                                "channel": "test-channel"
                            }
                        }
                    },
                    {
                        "type": "message",
                        "conn": "a",
                        "payload": {
                            "event": "client-test",
                            "channel": "test-channel",
                            "data": {
                                "client-event": "test"
                            }
                        }
                    }
                ],
                "report": {
                    "connections": [
                        "b"
                    ]
                }
            },
            "expected_output": "[b] received 1\n{\"event\":\"pusher_internal:subscription_succeeded\",\"channel\":\"test-channel\"}\n"
        },
        {
            "input": {
                "action": "session",
                "app": {
                    "client_messages_enabled": true
                },
                "connections": [
                    {
                        "name": "a",
                        "socket_id": "1.1"
                    },
                    {
                        "name": "b",
                        "socket_id": "2.2"
                    }
                ],
                "events": [
                    {
                        "type": "message",
                        "conn": "a",
                        "payload": {
                            "event": "pusher:subscribe",
                            "data": {
                                "channel": "test-channel"
                            }
                        }
                    },
                    {
                        "type": "message",
                        "conn": "b",
                        "payload": {
                            "event": "pusher:subscribe",
                            "data": {
                                "channel": "test-channel"
                            }
                        }
                    },
                    {
                        "type": "message",
                        "conn": "a",
                        "payload": {
                            "event": "client-test",
                            "channel": "test-channel",
                            "data": {
                                "client-event": "test"
                            }
                        }
                    }
                ],
                "report": {
                    "connections": [
                        "b"
                    ]
                }
            },
            "expected_output": "[b] received 2\n{\"event\":\"pusher_internal:subscription_succeeded\",\"channel\":\"test-channel\"}\n{\"event\":\"client-test\",\"channel\":\"test-channel\",\"data\":{\"client-event\":\"test\"}}\n"
        }
    ]
}
```

---
### Feature 8: Restricted Channel Authorization

**As a developer**, I want restricted channels to require a valid signature, so only authorized clients can subscribe.

**Expected Behavior / Usage:**

Subscribing to a restricted channel (name prefixed `private-`) requires an auth token `<key>:<hmac>` where `<hmac>` is HMAC-SHA256 of `<socket_id>:<channel>` keyed by the application secret. A matching signature yields the normal `pusher_internal:subscription_succeeded` acknowledgement. A non-matching token is rejected: no acknowledgement is sent and a signature error is reported as `error=invalid_signature` with protocol `code=4009`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_private_channel_auth.json`

```json
{
    "description": "A restricted (private) channel requires an authentication token on subscribe. The token is the application key, a colon, and the hex HMAC-SHA256 of the string '<socket_id>:<channel>' keyed by the application secret. When the token's signature matches, the subscription is acknowledged. When it does not match, the subscription is rejected with a signature error (carrying the protocol error code) and the client receives no acknowledgement.",
    "cases": [
        {
            "input": {
                "action": "session",
                "connections": [
                    {
                        "name": "a",
                        "socket_id": "200.2"
                    }
                ],
                "events": [
                    {
                        "type": "message",
                        "conn": "a",
                        "payload": {
                            "event": "pusher:subscribe",
                            "data": {
                                "channel": "private-channel",
                                "auth": "TestKey:d08ef786d54c1fee10dd22741270f8134bd375acd67667a90f0501f0765a8ab2"
                            }
                        }
                    }
                ]
            },
            "expected_output": "[a] received 1\n{\"event\":\"pusher_internal:subscription_succeeded\",\"channel\":\"private-channel\"}\n"
        },
        {
            "input": {
                "action": "session",
                "connections": [
                    {
                        "name": "a",
                        "socket_id": "200.2"
                    }
                ],
                "events": [
                    {
                        "type": "message",
                        "conn": "a",
                        "payload": {
                            "event": "pusher:subscribe",
                            "data": {
                                "channel": "private-channel",
                                "auth": "invalid"
                            }
                        }
                    }
                ]
            },
            "expected_output": "error=invalid_signature\ncode=4009\n[a] received 0\n"
        }
    ]
}
```

---
### Feature 9: Presence Channel Authorization & Roster

**As a developer**, I want presence channels to authorize members and expose who is present, so clients can render member lists.

**Expected Behavior / Usage:**

Subscribing to a presence channel (name prefixed `presence-`) requires both an auth token and a `channel_data` JSON string describing the member (`user_id` and `user_info`). The signed string is `<socket_id>:<channel>:<channel_data>` HMAC-SHA256 keyed by the application secret, prefixed with `<key>:`. On success the acknowledgement frame's `data` field is a JSON string carrying a presence roster: the array of member ids (as strings), a hash mapping each member id to its info, and the member count. On an invalid token the subscription is rejected with `error=invalid_signature` and `code=4009`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_presence_channel_auth.json`

```json
{
    "description": "A presence channel requires an authentication token plus a channel_data JSON describing the joining member. The signed string is '<socket_id>:<channel>:<channel_data>' HMAC-SHA256 keyed by the application secret, prefixed with the application key and a colon. On a valid token the subscription acknowledgement also carries a presence roster in its data field: the list of member ids, a hash mapping each member id to its info, and the member count. On an invalid token the subscription is rejected with a signature error and protocol code.",
    "cases": [
        {
            "input": {
                "action": "session",
                "connections": [
                    {
                        "name": "a",
                        "socket_id": "300.3"
                    }
                ],
                "events": [
                    {
                        "type": "message",
                        "conn": "a",
                        "payload": {
                            "event": "pusher:subscribe",
                            "data": {
                                "channel": "presence-channel",
                                "auth": "TestKey:4bda51fe69c2da03c4873e227ad9ca7a7f7f78adde3b9551cbc43f89c4f36f87",
                                "channel_data": "{\"user_id\":1,\"user_info\":{\"name\":\"Marcel\"}}"
                            }
                        }
                    }
                ]
            },
            "expected_output": "[a] received 1\n{\"event\":\"pusher_internal:subscription_succeeded\",\"channel\":\"presence-channel\",\"data\":\"{\\\"presence\\\":{\\\"ids\\\":[\\\"1\\\"],\\\"hash\\\":{\\\"1\\\":{\\\"name\\\":\\\"Marcel\\\"}},\\\"count\\\":1}}\"}\n"
        },
        {
            "input": {
                "action": "session",
                "connections": [
                    {
                        "name": "a",
                        "socket_id": "300.3"
                    }
                ],
                "events": [
                    {
                        "type": "message",
                        "conn": "a",
                        "payload": {
                            "event": "pusher:subscribe",
                            "data": {
                                "channel": "presence-channel",
                                "auth": "invalid"
                            }
                        }
                    }
                ]
            },
            "expected_output": "error=invalid_signature\ncode=4009\n[a] received 0\n"
        }
    ]
}
```

---
### Feature 10: Connection Handshake & App Key Verification

**As a developer**, I want an opening connection to be bound to a registered application by its key, so unknown clients are refused up front.

**Expected Behavior / Usage:**

When a connection opens it carries an application `key` as a query parameter. If the key matches a registered application, the connection is established: an `event=pusher:connection_established` line is reported together with the `activity_timeout` and the matched application's `id`, `key` and `name`. If the key is unknown, the handshake is rejected and reported as `error=unknown_app_key` with protocol `code=4001` and the offending `app_key`.

**Test Cases:** `rcb_tests/public_test_cases/feature10_connection_handshake.json`

```json
{
    "description": "When a connection opens it carries an application key as a query parameter. If the key matches a registered application, the connection is established: a connection_established event is reported (with the activity timeout) and the matched application's id, key and name are attached to the connection. If the key is unknown, the handshake is rejected with an unknown-app-key error carrying the protocol error code and the offending key.",
    "cases": [
        {
            "input": {
                "action": "connect",
                "app_key": "TestKey"
            },
            "expected_output": "event=pusher:connection_established\nactivity_timeout=30\napp_id=1234\napp_key=TestKey\napp_name=Test App\n"
        },
        {
            "input": {
                "action": "connect",
                "app_key": "test"
            },
            "expected_output": "error=unknown_app_key\ncode=4001\napp_key=test\n"
        }
    ]
}
```

---
### Feature 11: Application Registry Lookups

**As a developer**, I want to list and look up configured applications, so other components can resolve an application by id, key, or secret.

**Expected Behavior / Usage:**

The registry can list all configured applications (reporting `count` followed by each application's full attributes) and can look one up by `id`, by `key`, or by `secret`. A match reports `found=true` followed by the application's `id`, `key`, `secret`, `name`, `client_messages_enabled` and `statistics_enabled`. A non-match reports `found=false`. The two illustrative cases show a full listing and a key lookup that misses.

**Test Cases:** `rcb_tests/public_test_cases/feature11_app_registry.json`

```json
{
    "description": "The application registry exposes the configured applications and lookups by id, by key and by secret. Listing returns the count followed by each application's full attribute set (id, key, secret, name, whether client messaging is enabled, whether statistics are enabled). A lookup that matches returns found=true with that attribute set; a lookup that does not match returns found=false.",
    "cases": [
        {
            "input": {
                "action": "find_app",
                "by": "all"
            },
            "expected_output": "count=1\napp.id=1234\napp.key=TestKey\napp.secret=TestSecret\napp.name=Test App\napp.client_messages_enabled=false\napp.statistics_enabled=true\n"
        },
        {
            "input": {
                "action": "find_app",
                "by": "key",
                "value": "InvalidKey"
            },
            "expected_output": "found=false\n"
        }
    ]
}
```

---
### Feature 12: Application Construction Validation

**As a developer**, I want application construction to reject empty credentials, so misconfiguration fails fast.

**Expected Behavior / Usage:**

Constructing an application requires a non-empty `key` and a non-empty `secret`. A valid construction reports `created=true` and echoes the `id`, `key` and `secret`. An empty key (or empty secret) is rejected and reported as `created=false`, `error=invalid_app`, and a `field=<name>` line naming the offending credential field.

**Test Cases:** `rcb_tests/public_test_cases/feature12_app_validation.json`

```json
{
    "description": "Constructing an application requires a non-empty key and a non-empty secret. A valid construction succeeds and echoes the stored id, key and secret. An empty key is rejected with an invalid-app error naming the offending field; likewise an empty secret is rejected naming that field.",
    "cases": [
        {
            "input": {
                "action": "create_app",
                "id": 1,
                "key": "appKey",
                "secret": "appSecret"
            },
            "expected_output": "created=true\nid=1\nkey=appKey\nsecret=appSecret\n"
        },
        {
            "input": {
                "action": "create_app",
                "id": 1,
                "key": "",
                "secret": "appSecret"
            },
            "expected_output": "created=false\nerror=invalid_app\nfield=appKey\n"
        }
    ]
}
```

---
### Feature 13: Application-Id Validation Rule

**As a developer**, I want a reusable rule that checks whether a value is a registered application id, so request validation can reject unknown ids.

**Expected Behavior / Usage:**

The rule takes a candidate value and reports whether it is the id of a registered application. It echoes the checked value as `app_id=<value>` and reports `registered=true` when an application with that id exists, or `registered=false` otherwise.

**Test Cases:** `rcb_tests/public_test_cases/feature13_app_id_rule.json`

```json
{
    "description": "The app-id validation rule reports whether a given value is the id of a registered application. It echoes the checked value and reports registered=true when an application with that id exists, or registered=false otherwise.",
    "cases": [
        {
            "input": {
                "action": "validate_app_id",
                "value": 1234
            },
            "expected_output": "app_id=1234\nregistered=true\n"
        },
        {
            "input": {
                "action": "validate_app_id",
                "value": "invalid-app-id"
            },
            "expected_output": "app_id=invalid-app-id\nregistered=false\n"
        }
    ]
}
```

---
### Feature 14: Inspection API — List Occupied Channels

**As a developer**, I want a signed API that lists occupied channels, so external services can inspect server state.

**Expected Behavior / Usage:**

A signed GET request returns a JSON document `{"channels": {...}}` of currently occupied channels. The request is authorized by a signature over the canonical request string keyed by the application secret; an invalid signature fails with `status=401` and message `Invalid auth signature provided.`. With a valid signature: with no filter, every occupied channel maps to an empty object; a `filter_by_prefix` query limits results to channel names starting with that prefix; an `info=user_count` query annotates each presence channel with its `user_count`, but is only allowed when the request is restricted to presence channels via a presence prefix (otherwise `status=400` with message `Request must be limited to presence channels in order to fetch user_count`); when nothing is occupied the document is `{"channels":{}}`. Success cases report `status=200` then the raw JSON body. The two illustrative cases show a basic occupied listing and an invalid-signature rejection. The hidden set additionally exercises prefix filtering, the user_count annotation, the non-presence user_count rejection, and the empty result.

**Test Cases:** `rcb_tests/public_test_cases/feature14_fetch_channels.json`

```json
{
    "description": "The channel-listing API returns a JSON document of currently occupied channels for an application. The request must be signed (HMAC of the canonical request string keyed by the application secret); an invalid signature yields a 401 error. With a valid signature: with no filter it lists every occupied channel mapped to an empty info object; a prefix filter limits the result to channel names starting with that prefix; requesting the user_count info field annotates each (presence) channel with its member count, but is only permitted when the request is restricted to presence channels (otherwise 400); when no channels are occupied the document is an empty channels object. The report prints the HTTP status code then the raw JSON body, or a normalized error with its status and message.",
    "cases": [
        {
            "input": {
                "action": "fetch_channels",
                "setup": [
                    {
                        "socket_id": "1.1",
                        "channel": "presence-channel",
                        "user_id": 1
                    }
                ],
                "request": {
                    "path": "/apps/1234/channels",
                    "route_params": {
                        "appId": "1234"
                    },
                    "sign_secret": "TestSecret"
                }
            },
            "expected_output": "status=200\n{\"channels\":{\"presence-channel\":{}}}\n"
        },
        {
            "input": {
                "action": "fetch_channels",
                "setup": [],
                "request": {
                    "path": "/apps/1234/channels",
                    "route_params": {
                        "appId": "1234"
                    },
                    "sign_secret": "InvalidSecret"
                }
            },
            "expected_output": "error=http_exception\nstatus=401\nmessage=Invalid auth signature provided.\n"
        }
    ]
}
```

---
### Feature 15: Inspection API — Single Channel Occupancy

**As a developer**, I want a signed API that reports one channel's occupancy, so a service can check a specific channel.

**Expected Behavior / Usage:**

A signed GET request for a named channel returns `{"occupied": <bool>, "subscription_count": <n>}` when that channel is currently occupied (`status=200`). An invalid signature fails with `status=401` and message `Invalid auth signature provided.`. A request for a channel that is not currently occupied fails with `status=404` and a message reading 'Unknown channel' followed by the channel name in backticks and a period. The illustrative cases show a successful occupancy report and a 404 for an unknown channel.

**Test Cases:** `rcb_tests/public_test_cases/feature15_fetch_channel.json`

```json
{
    "description": "The single-channel API returns occupancy information for one named channel of an application. The request must be signed; an invalid signature yields a 401 error. With a valid signature and an existing channel it returns the occupancy flag and the subscription (connection) count. Requesting a channel that is not currently occupied yields a 404 error naming the channel. The report prints the HTTP status then the raw JSON body, or a normalized error with its status and message.",
    "cases": [
        {
            "input": {
                "action": "fetch_channel",
                "setup": [
                    {
                        "socket_id": "1.1",
                        "channel": "my-channel"
                    },
                    {
                        "socket_id": "2.2",
                        "channel": "my-channel"
                    }
                ],
                "request": {
                    "path": "/apps/1234/channel/my-channel",
                    "route_params": {
                        "appId": "1234",
                        "channelName": "my-channel"
                    },
                    "sign_secret": "TestSecret"
                }
            },
            "expected_output": "status=200\n{\"occupied\":true,\"subscription_count\":2}\n"
        },
        {
            "input": {
                "action": "fetch_channel",
                "setup": [
                    {
                        "socket_id": "1.1",
                        "channel": "my-channel"
                    }
                ],
                "request": {
                    "path": "/apps/1234/channel/invalid-channel",
                    "route_params": {
                        "appId": "1234",
                        "channelName": "invalid-channel"
                    },
                    "sign_secret": "TestSecret"
                }
            },
            "expected_output": "error=http_exception\nstatus=404\nmessage=Unknown channel `invalid-channel`.\n"
        }
    ]
}
```

---
### Feature 16: Inspection API — Presence Channel Members

**As a developer**, I want a signed API that lists a presence channel's members, so a service can retrieve who is present.

**Expected Behavior / Usage:**

A signed GET request for a presence channel's users returns `{"users": [{"id": <member_id>}, ...]}` (`status=200`). An invalid signature fails with `status=401` and message `Invalid auth signature provided.`. The target channel must exist (otherwise `status=404` with a message reading 'Unknown channel' followed by the channel name in double quotes) and must be a presence channel (otherwise `status=400` with a message reading 'Invalid presence channel' followed by the channel name in double quotes). The illustrative cases show a successful member listing and the rejection of a non-presence channel.

**Test Cases:** `rcb_tests/public_test_cases/feature16_fetch_users.json`

```json
{
    "description": "The channel-users API returns the members of a presence channel. The request must be signed; an invalid signature yields a 401 error. The target channel must exist (else 404 naming the channel) and must be a presence channel (else 400). For a valid presence channel it returns the list of members, each rendered as its member id. The report prints the HTTP status then the raw JSON body, or a normalized error with its status and message.",
    "cases": [
        {
            "input": {
                "action": "fetch_users",
                "setup": [
                    {
                        "socket_id": "1.1",
                        "channel": "presence-channel",
                        "user_id": 1
                    }
                ],
                "request": {
                    "path": "/apps/1234/channel/presence-channel/users",
                    "route_params": {
                        "appId": "1234",
                        "channelName": "presence-channel"
                    },
                    "sign_secret": "TestSecret"
                }
            },
            "expected_output": "status=200\n{\"users\":[{\"id\":1}]}\n"
        },
        {
            "input": {
                "action": "fetch_users",
                "setup": [
                    {
                        "socket_id": "1.1",
                        "channel": "my-channel"
                    }
                ],
                "request": {
                    "path": "/apps/1234/channel/my-channel/users",
                    "route_params": {
                        "appId": "1234",
                        "channelName": "my-channel"
                    },
                    "sign_secret": "TestSecret"
                }
            },
            "expected_output": "error=http_exception\nstatus=400\nmessage=Invalid presence channel \"my-channel\"\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the pub/sub protocol handling, channel/presence bookkeeping, application registry, and inspection-API payload formatting described above. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing, and from the underlying connection transport (it operates on an injected connection abstraction).

2. **The Execution/Test Adapter:** A runnable program (entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, selects behavior by its `action`, drives the core logic, and prints the line-oriented report (or normalized error) to stdout, matching the per-feature contracts above. Native domain exceptions are translated by the adapter into neutral `error=<category>` / `code=<n>` / `status=<n>` lines; the host language identity of exceptions must never appear in stdout.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- refer to the 'connection_state' module implementation
