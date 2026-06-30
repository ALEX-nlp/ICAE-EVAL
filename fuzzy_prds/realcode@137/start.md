## Product Requirement Document

Hey team, we need to build out this notification delivery library we've been talking about. The idea is that devs should be able to define a notification once and have it go out through multiple channels without re-writing all the plumbing every time. Think of it like that messaging abstraction we did for the billing service, but more generalized.

At a high level we need: payloads that carry arbitrary data, some kind of validation so we catch bad inputs early, immediate and deferred sending, the ability to skip channels based on conditions, lifecycle hooks so other parts of the system can observe what's happening, and durable storage so we can show users their notification history with read/unread tracking. We also want email, websocket broadcast, HTTP integrations (like Slack), and mobile push support.

One thing that keeps biting us is that when a user deletes something in the app, their related notifications linger in the DB and cause confusion — we need a way to tie notifications to application records and clean them up properly.

Also the ops team mentioned something about needing to store notification payloads in different column formats depending on the database setup, so make sure serialization is flexible.

Finally, it would be great if there was a generator so teams can bootstrap the storage model quickly instead of writing migrations by hand. Localization support would also be a nice-to-have so copy lives in translation files.