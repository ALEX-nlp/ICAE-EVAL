## Product Requirement Document

Hey team, we need to build out a Google Calendar integration library for our platform. Basically developers are spending way too much time hand-rolling all the plumbing to talk to Google Calendar — auth flows, fetching events, creating/updating them, checking availability, etc. It's a mess and every developer is doing it slightly differently which causes bugs.

The library should handle the full lifecycle: getting users connected (similar to how we did the login flow on the old CRM project, you know the one), reading and writing calendar data, searching events, and checking when people are free or busy. It also needs to handle errors gracefully — no one wants raw stack traces bubbling up to the UI.

There's also some nuance around how events are structured — all-day events behave differently, there are reminder configurations, recurrence rules, custom properties you can attach, guest permission flags, that kind of thing. The serialization to wire format needs to be exact or the Google API will reject it.

The adapter should be drivable from structured JSON commands so we can test it in isolation. Errors should come back as normalized category strings, not raw HTTP codes or exception class names. We also need calendar list enumeration and free/busy querying for the scheduling feature. Please make sure the URL encoding and query parameter ordering matches what we agreed on — the QA team flagged that last time as a blocker.

One more pass on the specifics the team asked about. For the consent link, the authorization URL needs to be exactly https://accounts.google.com/o/oauth2/auth and the query params have to stay in this exact order: access_type=offline, client_id=<value>, redirect_uri=<value>, response_type=code, scope=https://www.googleapis.com/auth/calendar. That scope needs to be exactly https://www.googleapis.com/auth/calendar, not calendar.readonly and not any other variant. Same story on the build_consent_link behavior we talked about before: the fixed ordering is access_type, client_id, redirect_uri, response_type, scope, and we need to keep that stable.

Also, after the one-time code exchange, we should not keep that one-time authorization code around as reusable client state. The one exception is that the black-box adapter still echoes it back in stdout as auth_code_after_exchange=<original one_time_code>, but that’s only there for deterministic reporting, not because we’re storing it as active state.

On availability/transparency, if the input is null or just not provided, we default to 'opaque'. In that case the output needs to include exactly these three lines: transparency=opaque, opaque=true, transparent=false. If the mode is 'transparent', then it should be transparency=transparent, opaque=false, transparent=true.

For the reminder payload task, the reminder JSON gets printed twice on two separate lines, and both lines are identical. The JSON key order matters: overrides first, then useDefault. Inside overrides, each object also needs alphabetical key order as {method, minutes}. The example to follow is exactly {"overrides":[{"method":"popup","minutes":6}],"useDefault":false}\n{"overrides":[{"method":"popup","minutes":6}],"useDefault":false}\n

For calendar list enumeration, the endpoint is GET /users/me/calendarList. Each returned entry needs to expose id, summary, time_zone, access_role, primary, and calendar_id, where calendar_id equals the entry id. The primary value should be true/false as a boolean, with false for non-primary calendars and true for the primary one.

For free/busy, the request is a POST to /freeBusy with body: {"items": [{"id": "<cal_id>"}, ...], "timeMax": "<end>", "timeMin": "<start>"}. Keep the keys in alphabetical order. The output should include the request details, then calendar_ids=<comma-separated list>, then for each calendar <cal_id>.busy_count=<n>, and for each busy block <cal_id>.busy<i>.start=<value> and <cal_id>.busy<i>.end=<value>. If a calendar has no busy windows, it should only show busy_count=0.

On error handling, HTTP failures need to come back as http_status=<code>, error=<normalized_category>, and details=<raw upstream response body as-is multiline string>. The details part is literally the raw upstream body printed verbatim, not re-serialized into something nicer. And error should always be a snake_case category like bad_request for 400 or not_found for 404, never just the numeric code and never an exception class name.

A couple request-flow details too: deleting an event is a two-step sequence. First we do a POST to create it, then a DELETE to /calendars/<encoded_cal_id>/events/<event_id>?sendNotifications=false. The output needs created.id=<id> before the POST request details, and after the DELETE succeeds we show after_delete.id= with the value left empty to reflect that the local identifier was cleared.

For update-or-create, there are two numbered requests: request0 is a GET to fetch the existing event by identifier, and request1 is a PUT to update it. The PUT has to target the event’s real id from the fetched record, not the lookup identifier, and the PUT JSON body also includes the id field. That PUT path ends with ?sendNotifications=false.

Last thing, a couple encoding and ordering details that QA was rightly picky about: @ needs to become %40 in calendar ID path segments, = needs to become %3D in extended property values, and for time-window queries the parameter order stays fixed as timeMin, timeMax, orderBy, maxResults, singleEvents.