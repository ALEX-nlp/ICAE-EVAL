## Product Requirement Document

Hey team, we need to put together a security logging utility library (Python is fine) for the platform. The core idea is that we want to be able to tag log events with sensitivity levels and then do smart things based on those tags — like blanking out sensitive data before it hits the log file, or sending certain events to a separate destination. Think of it kind of like what we did with the classification layer in the payments module, but more generalised.

A few pain points we're trying to solve: devs keep accidentally printing passwords and tokens in plain text logs, security-relevant events (logins, access checks, etc.) are getting buried in general debug noise, and we've had at least one incident where user-supplied input messed up our log formatting. That last one is a real concern for compliance.

The library should support combining multiple classification tags together and being able to ask 'does this event have tag X?'. It should also handle different levels of partial hiding for things like usernames, order numbers, and emails — not just a simple blanket redact. Routing decisions (allow / block / pass-through) should be configurable per filter type.

We'll need this to work as a clean API that can be driven from a JSON-based test harness. Please make sure the code is well-structured — not a single giant file. Refer to the existing field-pattern logic we scoped out for the data pipeline if you need a model for how masking rules should be composed.