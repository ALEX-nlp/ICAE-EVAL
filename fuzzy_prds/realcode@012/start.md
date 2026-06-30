## Product Requirement Document

We need a reusable payload sanitizer that can scrub sensitive data from API request and response payloads before they are forwarded to any monitoring or logging destination. The primary goal is to ensure no secrets such as passwords, card numbers, identity numbers, or access credentials are ever transmitted in plain text to third-party observability tools.

The sanitizer accepts a flat map of field names to their values. For each field whose name is recognized as sensitive, the value should be replaced with a masking character repeated as many times as the length of the original value — preserving the shape of the data while destroying the content. If a sensitive field holds no value (i.e., it is empty/absent), it should be passed through as-is without conversion. All non-sensitive fields must be returned completely unchanged, and the original ordering of all fields must be preserved in the output.

The set of field names considered sensitive should have sensible defaults built in, covering the most common cases teams typically encounter. That default set should be configurable so teams can extend or override it without modifying the core logic — handle the configuration loading the same way the service provider module handles its config merging.

The output of the sanitizer must be a compact, single-line JSON object written to standard output, followed by a newline. Error conditions such as invalid input or unrecognized actions should emit a short diagnostic line rather than crashing.

The masking logic must be physically and logically decoupled from the I/O adapter layer, so the core business rules can be tested in isolation. The whole system should be structured appropriately for its complexity — neither over-engineered nor bundled into a single monolithic file.