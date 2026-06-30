## Product Requirement Document

Hey team, we need to build out that slug automation library we've been talking about. Basically, devs are constantly rewriting the same boilerplate every time they add a new model — normalizing text, handling duplicates, keeping URLs from breaking when someone edits a title. It's a mess and we keep getting bug reports about broken links and weird characters showing up in URLs.

The core idea: you declare how a record generates its identifier, and the system handles the rest automatically during normal save/update/delete operations. Think of it like that profile-driven approach we used in the auth module last time — same kind of declarative config pattern.

A few things we know we need: it should handle accented characters gracefully, support combining fields together for the identifier, let us cap the length without cutting words in weird places, and make sure two records with the same name don't stomp on each other. Also some teams scope their content by owner/author so duplicates should be fine across different owners.

We also need a way to look records up by their identifier, generate one without actually saving anything, and control what happens to the identifier when someone edits the title. Oh, and soft-deleted records — we need to decide whether those still "own" their identifier or not.

Refer to the test scaffolding in the rcb_tests folder for the expected wire format. Should be a proper multi-file library, not a single script.