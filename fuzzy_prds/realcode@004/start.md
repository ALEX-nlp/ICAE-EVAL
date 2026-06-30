## Product Requirement Document

Hey team, we need to build that database pagination optimizer thing we discussed last sprint. The basic idea is that when devs do a bounded query to fetch a page of records, instead of pulling all the heavy row data upfront, we do a lightweight pass first to grab just the IDs, then fetch the full rows for only those IDs. Should work similarly to how we handled the deferred loading pattern in the billing module a while back — check how that was structured if you need a reference.

The tool needs to plug into our existing Rails/ActiveRecord stack (we're using SQLite for the in-memory test layer). It should handle the common pagination scenarios: plain limit, limit+offset, and also play nicely with that page-number helper we use on the backend (the one that also fires a COUNT query). Relationship preloading should still work but shouldn't bleed into the ID-selection step — that was a big complaint from the frontend team.

One thing that keeps biting us: devs sometimes forget to set any kind of page boundary, and then the optimizer just tries to run on the whole table. We need a clean, user-friendly error for that case — nothing gross with stack traces leaking out.

Also needs a test harness that can run the JSON-based test cases from a configurable directory and write outputs to per-case files. Make sure the structure is clean and not a giant single file — we've been burned by that before.