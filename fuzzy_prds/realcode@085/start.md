## Product Requirement Document

Hey team, we need to build out a Google Calendar integration library for our platform. Basically developers are spending way too much time hand-rolling all the plumbing to talk to Google Calendar — auth flows, fetching events, creating/updating them, checking availability, etc. It's a mess and every developer is doing it slightly differently which causes bugs.

The library should handle the full lifecycle: getting users connected (similar to how we did the login flow on the old CRM project, you know the one), reading and writing calendar data, searching events, and checking when people are free or busy. It also needs to handle errors gracefully — no one wants raw stack traces bubbling up to the UI.

There's also some nuance around how events are structured — all-day events behave differently, there are reminder configurations, recurrence rules, custom properties you can attach, guest permission flags, that kind of thing. The serialization to wire format needs to be exact or the Google API will reject it.

The adapter should be drivable from structured JSON commands so we can test it in isolation. Errors should come back as normalized category strings, not raw HTTP codes or exception class names. We also need calendar list enumeration and free/busy querying for the scheduling feature. Please make sure the URL encoding and query parameter ordering matches what we agreed on — the QA team flagged that last time as a blocker.