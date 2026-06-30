## Product Requirement Document

Hey team, we need to build that database pagination optimizer thing we discussed last sprint. The basic idea is that when devs do a bounded query to fetch a page of records, instead of pulling all the heavy row data upfront, we do a lightweight pass first to grab just the IDs, then fetch the full rows for only those IDs. Should work similarly to how we handled the deferred loading pattern in the billing module a while back — check how that was structured if you need a reference.

The tool needs to plug into our existing Rails/ActiveRecord stack (we're using SQLite for the in-memory test layer). It should handle the common pagination scenarios: plain limit, limit+offset, and also play nicely with that page-number helper we use on the backend (the one that also fires a COUNT query). Relationship preloading should still work but shouldn't bleed into the ID-selection step — that was a big complaint from the frontend team.

One thing that keeps biting us: devs sometimes forget to set any kind of page boundary, and then the optimizer just tries to run on the whole table. We need a clean, user-friendly error for that case — nothing gross with stack traces leaking out.

Also needs a test harness that can run the JSON-based test cases from a configurable directory and write outputs to per-case files. Make sure the structure is clean and not a giant single file — we've been burned by that before.

Quick follow-up from the questions that came in: the core behavior is still the same two-step DeferredPaginationOptimizer / fast_page flow we talked about in Feature 1. For a normal bounded query that only has a limit, we should see exactly 2 SQL statements total: first a SELECT that pulls only the primary key IDs with the LIMIT applied, then a SELECT of the full rows WHERE id IN (the collected IDs). No extra statements should show up around that.

On the preload question, if something like preload_organization is requested, that still needs to stay out of the ID-selection pass completely. The order there should be: first SELECT ids with LIMIT, then SELECT full rows WHERE id IN (...), then SELECT from the related table. So total SQL count is 3 in that case, and the first ID query needs to stay clean with no JOINs or includes.

Also, for the missing boundary case, if there is no limit and no offset in the page request, this needs to raise the domain-specific error and not some generic runtime blow-up. The output needs to be exactly error=missing_page_boundary\nrequired=limit_or_offset\n with no stack traces, no host-language exception class names, and no extra fields.

For parity checks, the optimized path needs to return records in the same order and with identical IDs and login values as the standard non-optimized bounded query for the same limit/offset/order combo. That’s what compare_standard is there to verify side-by-side. And in the page-number adapter mode, when we use page + items, we also need to preserve the pagination metadata. So for page=2 with items=1, the result should carry current_page=2, next_page=3, prev_page=1 along with the right record.

Last bit: in backend_adapter mode from Feature 6, the pagination helper does a COUNT(*) first, and then we still do the same two-step ID+record fetch after that. So the full optimized flow there should produce exactly 3 observable SQL statements total.