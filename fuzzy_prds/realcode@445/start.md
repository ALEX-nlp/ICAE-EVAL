## Product Requirement Document

We need a small support library for the administrative dashboard of our map tile server. The dashboard repeats the same error-prone transformations on every screen, producing inconsistent size labels, broken URLs, and subtly wrong charts. We want to centralize three categories of functionality.

First, display storage sizes in a human-friendly format. Raw byte counts must be converted to readable labels using a decimal scale. Edge cases — zero, a single byte, missing or invalid inputs, and extremely large values — must produce distinct, well-defined labels.

Second, the dashboard calls backend API endpoints but the server can be hosted at different paths or domains. We need a way to derive the correct API root from either an explicit configuration setting or the current browser location, ensuring that query strings and hash fragments never corrupt the constructed address. Given this base and a relative path, the library must assemble a properly joined absolute URL.

Third, the dashboard needs to visualize request performance. It reads a metrics exposition format emitted by the server — look for the relevant metric family name already used in the codebase — and extracts per-endpoint duration totals, request counts, and latency distribution buckets. Those must also be aggregated into logical endpoint groupings whose definitions already live somewhere in the source tree. Bucket data must be sorted correctly and the redundant catch-all upper bound dropped.

All logic should be pure functions decoupled from I/O, with a thin command-dispatch adapter on top.