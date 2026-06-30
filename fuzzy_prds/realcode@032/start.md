## Product Requirement Document

Hey team, we've been getting complaints from devs that writing tests for async streams is a total nightmare — people keep shipping bugs because they forget to check the last value, or tests pass even when the stream throws an error nobody read. We talked about this in the Q3 planning thing and agreed we need a small testing helper library for this.

Basically devs should be able to 'open a session' over a stream, pull out events one at a time, and have the library yell at them if they missed something. Similar to how we handled the observable wrapper in the notification service refactor — that same idea of a scoped block that auto-validates at the end.

A few things I know we need: some way to just grab whatever event comes next without caring what type it is, a way to say 'I'm done, throw away the rest', and a way to verify the stream hasn't produced anything yet. We also need it to not hang forever if the stream is slow — there was a whole incident last sprint where CI was blocked for 40 minutes because of that.

One thing I'm not sure about: how exactly the clock/timing enforcement works when someone passes zero as the wait window — does that disable it or error immediately? And what happens with leftover events vs explicitly draining them — are those treated the same? Please make sure the end-of-block cleanup behavior is clearly defined for all the exit paths (exception, explicit stop, etc.).