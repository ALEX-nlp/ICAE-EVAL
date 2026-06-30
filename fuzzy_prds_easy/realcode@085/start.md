## Product Requirement Document

# Calendar API Adapter - Event, Calendar, Availability, and Error Contract

## Project Goal

Build a lightweight calendar API client adapter that allows developers to authenticate, manage calendar profiles, read and mutate events, inspect calendar lists, query availability, and handle service errors without manually composing calendar API URLs, request bodies, response parsing, and error mapping.

---

## Background & Problem

Without this library/tool, developers are forced to hand-build OAuth authorization links, token exchange flows, calendar and event endpoints, event JSON payloads, recurrence rules, reminder structures, free/busy requests, and service-error handling. This leads to repetitive code, inconsistent request formatting, fragile parsing, and application logic that is tightly coupled to raw service responses.

With this library/tool, developers work with a compact client-facing interface and receive predictable event, calendar, list, availability, serialization, and error outputs through a standard execution adapter.

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

### Feature 1: OAuth Connection Setup

**As a developer**, I want to obtain access to a user calendar through an OAuth-style flow, so I can make authenticated calendar requests without hand-writing token URLs.

**Expected Behavior / Usage:**

Connection setup covers authorization URL generation, token acquisition, and credential validation. Inputs are JSON commands consumed by the execution adapter; outputs are line-oriented stdout fields such as generated URLs, token values, or normalized error categories.

*1.1 Authorization URL Generation — The input provides a client identifier, client secret, redirect URL, and optionally a state value.*

The input provides a client identifier, client secret, redirect URL, and optionally a state value. The output contains one `authorization_url=` line whose URL requests offline calendar scope access and preserves the provided redirect and state parameters.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_oauth_consent_url.json`

```json
{
    "description": "Build the browser authorization URL for offline calendar access from client credentials, redirect URL, and optional state.",
    "cases": [
        {
            "input": {
                "task": "build_consent_link",
                "client_id": "671053090364-ntifn8rauvhib9h3vnsegi6dhfglk9ue.apps.googleusercontent.com",
                "client_secret": "roBgdbfEmJwPgrgi2mRbbO-f",
                "redirect_url": "urn:ietf:wg:oauth:2.0:oob"
            },
            "expected_output": "authorization_url=https://accounts.google.com/o/oauth2/auth?access_type=offline&client_id=671053090364-ntifn8rauvhib9h3vnsegi6dhfglk9ue.apps.googleusercontent.com&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&scope=https://www.googleapis.com/auth/calendar\n"
        }
    ]
}
```

*1.2 Token Exchange and Refresh — The input represents either a one-time code exchange or a refresh-token exchange.*

The input represents either a one-time code exchange or a refresh-token exchange. The output exposes the refresh token, access token, and whether any one-time code remains stored after exchange. A one-time code must not remain visible after it is used.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_oauth_token_exchange.json`

```json
{
    "description": "Exchange an authorization code or refresh token and expose the resulting tokens without retaining the one-time code.",
    "cases": [
        {
            "input": {
                "task": "exchange_one_time_code",
                "one_time_code": "4/QzBU-n6GXnHUkorG0fiu6AhoZtIjW53qKLOREiJWFpQ.wn0UfiyaDlEfEnp6UAPFm0EazsV1kwI",
                "access_token": "ya29.hYjPO0uHt63uWr5qmQtMEReZEvILcdGlPCOHDy6quKPyEQaQQvqaVAlLAVASaRm_O0a7vkZ91T8xyQ",
                "returned_refresh_token": "1/aJUy7pQzc4fUMX89BMMLeAfKcYteBKRMpQvf4fQFX0"
            },
            "expected_output": "refresh_token=1/aJUy7pQzc4fUMX89BMMLeAfKcYteBKRMpQvf4fQFX0\naccess_token=ya29.hYjPO0uHt63uWr5qmQtMEReZEvILcdGlPCOHDy6quKPyEQaQQvqaVAlLAVASaRm_O0a7vkZ91T8xyQ\nauth_code_after_exchange=4/QzBU-n6GXnHUkorG0fiu6AhoZtIjW53qKLOREiJWFpQ.wn0UfiyaDlEfEnp6UAPFm0EazsV1kwI\n"
        }
    ]
}
```

*1.3 Credential Requirement Handling — The input omits required credential fields.*

The input omits required credential fields. The output is a normalized `error=missing_credentials` line rather than a host-language exception name or stack trace.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_credentials_required.json`

```json
{
    "description": "Reject connection setup when the required client credential fields are absent or blank.",
    "cases": [
        {
            "input": {
                "task": "missing_credentials"
            },
            "expected_output": "error=missing_credentials\n"
        }
    ]
}
```

---

### Feature 2: Calendar Profile Management

**As a developer**, I want to read and write calendar-level metadata, so I can maintain calendars without manually composing profile HTTP requests.

**Expected Behavior / Usage:**

Calendar profile operations expose the routed calendar endpoint and the profile fields returned or sent. Inputs describe profile reads, profile updates, or profile creation; outputs include request method/path signals and resulting profile data.

*2.1 Calendar Profile Retrieval — The input provides a calendar id and an upstream calendar-profile response.*

The input provides a calendar id and an upstream calendar-profile response. The output includes the GET request path and profile fields including id, summary, description, location, and time zone.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_calendar_profile_retrieval.json`

```json
{
    "description": "Retrieve a calendar profile and render the request endpoint plus profile fields returned by the service.",
    "cases": [
        {
            "input": {
                "task": "read_calendar_profile",
                "calendar_id": "gqeb0i6v737kfu5md0f35htjlg@group.calendar.google.com",
                "upstream_response": "calendar_profile"
            },
            "expected_output": "request0.method=get\nrequest0.path=/calendars/gqeb0i6v737kfu5md0f35htjlg@group.calendar.google.com\nid=gqeb0i6v737kfu5md0f35htjlg@group.calendar.google.com\nsummary=Some Calendar\ndescription=Our work events\nlocation=Portland\ntime_zone=America/Los_Angeles\n"
        }
    ]
}
```

*2.2 Calendar Profile Creation and Update — The input supplies either a change set for an existing calendar or a profile for a new calendar.*

The input supplies either a change set for an existing calendar or a profile for a new calendar. The output includes the request method, routed path, serialized request body where applicable, and resulting id/summary/description fields.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_calendar_profile_write.json`

```json
{
    "description": "Create or update a calendar profile and render the service request made with the resulting profile fields.",
    "cases": [
        {
            "input": {
                "task": "change_calendar_profile",
                "calendar_id": "gqeb0i6v737kfu5md0f35htjlg@group.calendar.google.com",
                "changes": {
                    "summary": "Our Company",
                    "description": "Work event list"
                }
            },
            "expected_output": "request0.method=put\nrequest0.path=/calendars/gqeb0i6v737kfu5md0f35htjlg@group.calendar.google.com\nrequest0.body={\"description\":\"Work event list\",\"location\":null,\"summary\":\"Our Company\",\"timeZone\":null}\nid=gqeb0i6v737kfu5md0f35htjlg@group.calendar.google.com\nsummary=Our Company\ndescription=Work event list\n"
        }
    ]
}
```

---

### Feature 3: Event Discovery

**As a developer**, I want to retrieve and filter calendar events, so I can find relevant events without handling raw service feeds.

**Expected Behavior / Usage:**

Event discovery covers collection reads, text search, time-window filtering, custom-property filtering, and identifier lookup. Outputs include both routed request paths and event record fields so the behavior cannot be satisfied by returning only counts.

*3.1 Event Collection Retrieval — The input names the event feed shape returned by the upstream service.*

The input names the event feed shape returned by the upstream service. The output includes the events endpoint, calendar summary, collection count, and indexed event fields such as id, status, title, start, end, location, description, and color.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_event_collection_retrieval.json`

```json
{
    "description": "Fetch a calendar event collection and always expose a count and indexed event records, including empty collections.",
    "cases": [
        {
            "input": {
                "task": "list_events",
                "upstream_response": "multiple_events"
            },
            "expected_output": "request0.method=get\nrequest0.path=/calendars/klei8jnelo09nflqehnvfzipgs%40group.calendar.google.com/events\ncalendar_summary=My Events Calendar\ncount=3\nevent0.id=fhru34kt6ikmr20knd2456l08n\nevent0.status=confirmed\nevent0.title=Staff Meeting\nevent0.start=2011-10-03T16:30:00Z\nevent0.end=2011-10-03T17:30:00Z\nevent0.location=\nevent0.description=\nevent0.color=\nevent1.id=fhru34kt6ikmr20knd2456l08n\nevent1.status=confirmed\nevent1.title=Skype Meeting\nevent1.start=2011-10-03T17:30:00Z\nevent1.end=2011-10-03T18:00:00Z\nevent1.location=\nevent1.description=\nevent1.color=\nevent2.id=_75342gho74p3aba4852j6b9k6l0j2ba16l23cba18p2j8h9p74o4adhh6k\nevent2.status=confirmed\nevent2.title=Sales Staff Meeting\nevent2.start=2012-01-09T17:15:00Z\nevent2.end=2012-01-09T18:15:00Z\nevent2.location=\nevent2.description=\nevent2.color=\n"
        }
    ]
}
```

*3.2 Text Search — The input supplies a text query.*

The input supplies a text query. The output includes the routed request path with the query parameter and the matching event records returned by the service.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_event_text_search.json`

```json
{
    "description": "Search events using a text query and return the matching event records together with the exact routed request path.",
    "cases": [
        {
            "input": {
                "task": "search_events",
                "query": "Test&gsessionid=12345"
            },
            "expected_output": "request0.method=get\nrequest0.path=/calendars/klei8jnelo09nflqehnvfzipgs%40group.calendar.google.com/events?q=Test&gsessionid=12345\ncount=1\nevent0.id=fhru34kt6ikmr20knd2456l08n\nevent0.status=confirmed\nevent0.title=Test Event\nevent0.start=2008-09-24T17:30:00Z\nevent0.end=2008-09-24T18:00:00Z\nevent0.location=\nevent0.description=My Test Event\nevent0.color=3\n"
        }
    ]
}
```

*3.3 Time-Window and Future Queries — The input provides start/end timestamps or a fixed current timestamp with optional result options.*

The input provides start/end timestamps or a fixed current timestamp with optional result options. The output includes encoded `timeMin`, `timeMax`, ordering, max-result, expansion, and query parameters in the request path plus the returned count.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_time_window_event_queries.json`

```json
{
    "description": "Query events by time windows and future-start filters, rendering the encoded request URL and count.",
    "cases": [
        {
            "input": {
                "task": "events_in_window",
                "start": "2015-03-06T00:00:00Z",
                "end": "2015-03-07T00:00:00Z"
            },
            "expected_output": "request0.method=get\nrequest0.path=/calendars/klei8jnelo09nflqehnvfzipgs%40group.calendar.google.com/events?timeMin=2015-03-06T00:00:00Z&timeMax=2015-03-07T00:00:00Z&orderBy=startTime&maxResults=25&singleEvents=true\ncount=0\n"
        }
    ]
}
```

*3.4 Custom Property Queries — The input supplies shared or private key/value properties and may also include a time range.*

The input supplies shared or private key/value properties and may also include a time range. The output includes the encoded extended-property parameters, default ordering options, optional time bounds, and the resulting count.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_custom_property_event_queries.json`

```json
{
    "description": "Query events by shared or private custom properties, optionally bounded by a time window, and expose the encoded request URL.",
    "cases": [
        {
            "input": {
                "task": "events_with_custom_properties",
                "properties": {
                    "shared": {
                        "p": "v",
                        "q": "w"
                    }
                }
            },
            "expected_output": "request0.method=get\nrequest0.path=/calendars/klei8jnelo09nflqehnvfzipgs%40group.calendar.google.com/events?sharedExtendedProperty=p%3Dv&sharedExtendedProperty=q%3Dw&orderBy=startTime&maxResults=25&singleEvents=true\ncount=0\n"
        }
    ]
}
```

*3.5 Identifier Lookup — The input supplies an event identifier and an upstream result category.*

The input supplies an event identifier and an upstream result category. The output includes the routed event URL and either an indexed event record with parsed fields or `count=0` when the service reports not found.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5_event_identifier_lookup.json`

```json
{
    "description": "Look up a single event by identifier, returning an event array when found and an empty collection when the service reports not found.",
    "cases": [
        {
            "input": {
                "task": "event_by_identifier",
                "identifier": "fhru34kt6ikmr20knd2456l08n",
                "upstream_response": "found_event"
            },
            "expected_output": "request0.method=get\nrequest0.path=/calendars/klei8jnelo09nflqehnvfzipgs%40group.calendar.google.com/events/fhru34kt6ikmr20knd2456l08n\ncount=1\nevent0.id=fhru34kt6ikmr20knd2456l08n\nevent0.status=confirmed\nevent0.title=This is a test event\nevent0.start=2008-09-24T17:30:00Z\nevent0.end=2008-09-24T18:00:00Z\nevent0.location=\nevent0.description=Test Event\nevent0.color=\nevent0.creator=Some Person\nevent0.shared_key=value\n"
        }
    ]
}
```

---

### Feature 4: Event Mutation

**As a developer**, I want to create, update, or delete events, so I can change calendar contents through a high-level event interface.

**Expected Behavior / Usage:**

Event mutation commands expose both the high-level result and the underlying event route used. Inputs describe detailed event creation, quick text creation, update-or-create behavior, and deletion.

*4.1 Event Creation — The input provides event fields or quick text.*

The input provides event fields or quick text. The output includes POST request details, serialized event JSON or quick-add path, and saved event result fields including id and title.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_event_creation.json`

```json
{
    "description": "Create events from detailed fields or quick natural-language text and render request details plus the saved event identity.",
    "cases": [
        {
            "input": {
                "task": "create_detailed_event",
                "event": {
                    "title": "New Event",
                    "start_time": "2014-11-16T20:17:31-08:00",
                    "end_time": "2014-11-16T21:17:31-08:00",
                    "description": "A new event",
                    "location": "Joe's House",
                    "extended_properties": {
                        "shared": {
                            "key": "value"
                        }
                    }
                }
            },
            "expected_output": "request0.method=post\nrequest0.path=/calendars/klei8jnelo09nflqehnvfzipgs%40group.calendar.google.com/events?sendNotifications=false\nrequest0.body={\"description\":\"A new event\",\"end\":{\"dateTime\":\"2014-11-16T21:17:31-08:00\"},\"extendedProperties\":{\"shared\":{\"key\":\"value\"}},\"guestsCanInviteOthers\":null,\"guestsCanSeeOtherGuests\":null,\"location\":\"Joe's House\",\"reminders\":{\"useDefault\":true},\"start\":{\"dateTime\":\"2014-11-16T20:17:31-08:00\"},\"summary\":\"New Event\",\"transparency\":\"opaque\",\"visibility\":\"default\"}\nresult.id=fhru34kt6ikmr20knd2456l08n\nresult.title=New Event\nresult.description=A new event\nresult.location=Joe's House\n"
        }
    ]
}
```

*4.2 Update or Create by Identifier — The input provides an optional identifier and a replacement title.*

The input provides an optional identifier and a replacement title. The output includes lookup and save request signals plus the resulting event id and title.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_event_update_or_create.json`

```json
{
    "description": "Find an event by identifier, update it when found, or create it when no identifier is supplied.",
    "cases": [
        {
            "input": {
                "task": "update_or_create_event",
                "identifier": "t00jnpqc08rcabi6pa549ttjlk",
                "new_title": "New Event Update",
                "now": "2015-03-06T10:11:12Z"
            },
            "expected_output": "request0.method=get\nrequest0.path=/calendars/klei8jnelo09nflqehnvfzipgs%40group.calendar.google.com/events/t00jnpqc08rcabi6pa549ttjlk\nrequest1.method=put\nrequest1.path=/calendars/klei8jnelo09nflqehnvfzipgs%40group.calendar.google.com/events/fhru34kt6ikmr20knd2456l08n?sendNotifications=false\nrequest1.body={\"description\":\"Test Event\",\"end\":{\"dateTime\":\"2008-09-24T18:00:00Z\"},\"extendedProperties\":{\"shared\":{\"key\":\"value\"}},\"guestsCanInviteOthers\":null,\"guestsCanSeeOtherGuests\":null,\"id\":\"fhru34kt6ikmr20knd2456l08n\",\"location\":null,\"reminders\":{\"useDefault\":true},\"start\":{\"dateTime\":\"2008-09-24T17:30:00Z\"},\"summary\":\"New Event Update\",\"transparency\":\"opaque\",\"visibility\":\"default\"}\nresult.id=fhru34kt6ikmr20knd2456l08n\nresult.title=New Event Update\n"
        }
    ]
}
```

*4.3 Event Deletion — The input supplies a title for an event that is first saved and then deleted.*

The input supplies a title for an event that is first saved and then deleted. The output includes creation and deletion request paths and shows that the local id is empty after deletion.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_event_deletion.json`

```json
{
    "description": "Delete a saved event through the event endpoint and clear the local event identifier after successful deletion.",
    "cases": [
        {
            "input": {
                "task": "delete_created_event",
                "title": "Delete Me",
                "now": "2015-03-06T10:11:12Z"
            },
            "expected_output": "created.id=fhru34kt6ikmr20knd2456l08n\nrequest0.method=post\nrequest0.path=/calendars/klei8jnelo09nflqehnvfzipgs%40group.calendar.google.com/events?sendNotifications=false\nrequest0.body={\"description\":null,\"end\":{\"dateTime\":\"2015-03-06T11:11:12Z\"},\"guestsCanInviteOthers\":null,\"guestsCanSeeOtherGuests\":null,\"location\":null,\"reminders\":{\"useDefault\":true},\"start\":{\"dateTime\":\"2015-03-06T10:11:12Z\"},\"summary\":\"Delete Me\",\"transparency\":\"opaque\",\"visibility\":\"default\"}\nrequest1.method=delete\nrequest1.path=/calendars/klei8jnelo09nflqehnvfzipgs%40group.calendar.google.com/events/fhru34kt6ikmr20knd2456l08n?sendNotifications=false\nafter_delete.id=\n"
        }
    ]
}
```

---

### Feature 5: Event Data Modeling and Serialization

**As a developer**, I want to work with event fields as structured domain data, so I can produce calendar-compatible event payloads without hand-building JSON.

**Expected Behavior / Usage:**

Event data behavior covers identifier validation, all-day dates, availability, creator names, JSON payload rendering, reminder data, and recurrence parsing. Outputs include concrete field values or normalized error categories.

*5.1 Identifier Validation — The input supplies an event identifier value.*

The input supplies an event identifier value. The output echoes valid identifiers, prints an empty id for nil input, or emits `error=invalid_event_id` with the raw identifier for invalid input.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_event_identifier_validation.json`

```json
{
    "description": "Accept valid event identifiers and normalize invalid identifier errors without leaking runtime exception names.",
    "cases": [
        {
            "input": {
                "task": "event_identifier_value",
                "identifier": "8os94knodtv84h0jh4pqq4ut35"
            },
            "expected_output": "id=8os94knodtv84h0jh4pqq4ut35\n"
        }
    ]
}
```

*5.2 All-Day Event Handling — The input supplies date-only or timestamp boundaries, or a date to assign as an all-day event.*

The input supplies date-only or timestamp boundaries, or a date to assign as an all-day event. The output shows the all-day boolean, duration, start/end dates, or serialized date-only event payload.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_all_day_events.json`

```json
{
    "description": "Determine and assign all-day events using date-only boundaries and render date-only payload fields for all-day events.",
    "cases": [
        {
            "input": {
                "task": "event_all_day_status",
                "start": "2012-03-31",
                "end": "2012-04-01"
            },
            "expected_output": "all_day=true\nduration_seconds=86400\n"
        }
    ]
}
```

*5.3 Availability and Creator Fields — The input provides an availability mode or creator object.*

The input provides an availability mode or creator object. The output shows normalized transparency, opaque/transparent booleans, or creator display name.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_availability_and_creator_fields.json`

```json
{
    "description": "Normalize event transparency inputs into availability modes and expose creator display names from service records.",
    "cases": [
        {
            "input": {
                "task": "event_availability_mode",
                "mode": null
            },
            "expected_output": "transparency=opaque\nopaque=true\ntransparent=false\n"
        }
    ]
}
```

*5.4 Event JSON Serialization — The input supplies event fields such as title, times, description, location, attendees, reminders, recurrence, custom properties, and guest permissions.*

The input supplies event fields such as title, times, description, location, attendees, reminders, recurrence, custom properties, and guest permissions. The output is a canonical JSON string containing the wire-format fields.

**Test Cases:** `rcb_tests/public_test_cases/feature5_4_event_json_serialization.json`

```json
{
    "description": "Serialize event fields to the calendar event JSON wire format, preserving attendees, reminders, recurrence, and custom properties.",
    "cases": [
        {
            "input": {
                "task": "event_json_payload",
                "event": {
                    "start_time": "2014-11-16T20:17:31-08:00",
                    "end_time": "2014-11-16T21:17:31-08:00",
                    "title": "Go Swimming",
                    "description": "The polar bear plunge",
                    "location": "In the arctic ocean",
                    "transparency": "opaque",
                    "reminders": {
                        "useDefault": false,
                        "overrides": [
                            {
                                "minutes": 10,
                                "method": "popup"
                            }
                        ]
                    },
                    "attendees": [
                        {
                            "email": "some.a.one@gmail.com",
                            "displayName": "Some A One",
                            "responseStatus": "tentative"
                        },
                        {
                            "email": "some.b.one@gmail.com",
                            "displayName": "Some B One",
                            "responseStatus": "tentative"
                        }
                    ],
                    "extended_properties": {
                        "shared": {
                            "key": "value"
                        }
                    },
                    "guests_can_invite_others": false,
                    "guests_can_see_other_guests": false
                }
            },
            "expected_output": "{\"attendees\":[{\"displayName\":\"Some A One\",\"email\":\"some.a.one@gmail.com\",\"responseStatus\":\"tentative\"},{\"displayName\":\"Some B One\",\"email\":\"some.b.one@gmail.com\",\"responseStatus\":\"tentative\"}],\"description\":\"The polar bear plunge\",\"end\":{\"dateTime\":\"2014-11-16T21:17:31-08:00\"},\"extendedProperties\":{\"shared\":{\"key\":\"value\"}},\"guestsCanInviteOthers\":false,\"guestsCanSeeOtherGuests\":false,\"location\":\"In the arctic ocean\",\"reminders\":{\"overrides\":[{\"method\":\"popup\",\"minutes\":10}],\"useDefault\":false},\"start\":{\"dateTime\":\"2014-11-16T20:17:31-08:00\"},\"summary\":\"Go Swimming\",\"transparency\":\"opaque\",\"visibility\":\"default\"}\n"
        }
    ]
}
```

*5.5 Reminder and Recurrence Helpers — The input supplies reminder override data or recurrence rule strings.*

The input supplies reminder override data or recurrence rule strings. The output renders normalized reminder JSON and reminder attributes, or a normalized lower-case recurrence object.

**Test Cases:** `rcb_tests/public_test_cases/feature5_5_reminders_and_recurrence_helpers.json`

```json
{
    "description": "Expose reminder override data and parse recurrence rule strings into normalized lower-case recurrence fields.",
    "cases": [
        {
            "input": {
                "task": "event_reminder_payload",
                "reminders": {
                    "useDefault": false,
                    "overrides": [
                        {
                            "minutes": 6,
                            "method": "popup"
                        }
                    ]
                }
            },
            "expected_output": "{\"overrides\":[{\"method\":\"popup\",\"minutes\":6}],\"useDefault\":false}\n{\"overrides\":[{\"method\":\"popup\",\"minutes\":6}],\"useDefault\":false}\n"
        }
    ]
}
```

---

### Feature 6: Calendar List and Availability Queries

**As a developer**, I want to inspect accessible calendars and busy windows, so I can support calendar selection and scheduling decisions.

**Expected Behavior / Usage:**

These commands expose calendar-list entries and free/busy results with request paths and per-calendar result data.

*6.1 Calendar List Entries — The input requests the calendar list.*

The input requests the calendar list. The output includes the routed list endpoint, entry count, per-entry id/summary/time-zone/access-role/primary flag, and the calendar id produced from each list entry.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_calendar_list_entries.json`

```json
{
    "description": "Fetch the authenticated calendar list and expose each entry field plus the calendar identity created from that entry.",
    "cases": [
        {
            "input": {
                "task": "calendar_list_entries"
            },
            "expected_output": "request0.method=get\nrequest0.path=/users/me/calendarList\ncount=3\nentry0.id=initech.com_ed493d0a9b46ea46c3a0d48611ce@resource.calendar.google.com\nentry0.summary=Small cubicle\nentry0.time_zone=America/Los_Angeles\nentry0.access_role=owner\nentry0.primary=false\nentry0.calendar_id=initech.com_ed493d0a9b46ea46c3a0d48611ce@resource.calendar.google.com\nentry1.id=initech.com_db18a4e59c230a5cc5d2b069a30f@resource.calendar.google.com\nentry1.summary=Large cubicle\nentry1.time_zone=America/Los_Angeles\nentry1.access_role=reader\nentry1.primary=false\nentry1.calendar_id=initech.com_db18a4e59c230a5cc5d2b069a30f@resource.calendar.google.com\nentry2.id=bob@initech.com\nentry2.summary=Bob's Calendar\nentry2.time_zone=Europe/London\nentry2.access_role=owner\nentry2.primary=true\nentry2.calendar_id=bob@initech.com\n"
        }
    ]
}
```

*6.2 Free/Busy Query — The input supplies calendar ids and a start/end interval.*

The input supplies calendar ids and a start/end interval. The output includes the POST request path/body and, for each requested calendar id, the busy-slot count and slot start/end values.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_free_busy_query.json`

```json
{
    "description": "Query busy windows for multiple calendars and return a mapping for every requested calendar id.",
    "cases": [
        {
            "input": {
                "task": "free_busy_query",
                "calendar_ids": [
                    "busy-calendar-id",
                    "not-busy-calendar-id"
                ],
                "start": "2015-03-06T00:00:00Z",
                "end": "2015-03-06T23:59:59Z"
            },
            "expected_output": "request0.method=post\nrequest0.path=/freeBusy\nrequest0.body={\"items\":[{\"id\":\"busy-calendar-id\"},{\"id\":\"not-busy-calendar-id\"}],\"timeMax\":\"2015-03-06T23:59:59Z\",\"timeMin\":\"2015-03-06T00:00:00Z\"}\ncalendar_ids=busy-calendar-id,not-busy-calendar-id\nbusy-calendar-id.busy_count=2\nbusy-calendar-id.busy0.start=2015-03-06T10:00:00Z\nbusy-calendar-id.busy0.end=2015-03-06T11:00:00Z\nbusy-calendar-id.busy1.start=2015-03-06T11:30:00Z\nbusy-calendar-id.busy1.end=2015-03-06T11:30:00Z\nnot-busy-calendar-id.busy_count=0\n"
        }
    ]
}
```

---

### Feature 7: Upstream Error Normalization

**As a developer**, I want to map calendar service failures into stable categories, so I can handle failures without depending on language-specific exceptions.

**Expected Behavior / Usage:**

Error handling preserves protocol status and domain message signals while hiding host-language exception class names.

*7.1 HTTP Error Mapping — The input supplies an HTTP status and upstream response category.*

The input supplies an HTTP status and upstream response category. The output includes `http_status=...`, `error=...`, and a domain detail line when the upstream body contains a useful calendar-service message.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_http_error_mapping.json`

```json
{
    "description": "Map upstream HTTP error responses to language-neutral error categories while preserving status and domain message signals.",
    "cases": [
        {
            "input": {
                "task": "http_error_response",
                "status": 400,
                "upstream_response": "bad_request"
            },
            "expected_output": "http_status=400\nerror=bad_request\ndetails={\n \"error\": {\n  \"errors\": [\n   {\n    \"domain\": \"calendar\",\n    \"reason\": \"timeRangeEmpty\",\n    \"message\": \"The specified time range is empty.\",\n    \"locationType\": \"parameter\",\n    \"location\": \"timeMax\",\n   }\n  ],\n  \"code\": 400,\n  \"message\": \"The specified time range is empty.\"\n }\n}\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the exact q= encoding style used in the event search query builder module
- use the same error message format for empty time ranges as the freeBusy query validation logic
