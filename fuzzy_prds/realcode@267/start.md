## Product Requirement Document

We need a small shared utility library for programs that manage workloads on individual cluster nodes, addressing two recurring pain points.

First, a standardized way to tag errors with a semantic category so calling code can ask 'did this fail because the thing was not there?' or 'was the input invalid?' without fragile string matching. The tagging must be nil-safe — attaching a category to a missing error should produce nothing. Category checks must work even when the tagged error has been wrapped by other errors up the call stack, provided those wrappers expose their underlying cause. Third-party error types that self-report category membership via a boolean method should also be recognized.

Second, a simple in-memory lookup layer for the four core object types that node agents need: compute units, networking endpoints, credential stores, and configuration bundles. A caller pre-fills the store with current node objects, then either counts all records of a type or fetches one by its two-part identifier. Fetch failures on data-bearing types should handle it the same way as the error categorization module does for not-found conditions, and the failure message must name the object type and the missing identifier.

Data from a successful fetch must be returned with entries in a consistent, deterministic order so results are reproducible across environments.