## Product Requirement Document

We need a reusable payload sanitizer that can scrub sensitive data from API request and response payloads before they are forwarded to any monitoring or logging destination. The primary goal is to ensure no secrets such as passwords, card numbers, identity numbers, or access credentials are ever transmitted in plain text to third-party observability tools.

The sanitizer accepts a flat map of field names to their values. For each field whose name is recognized as sensitive, the value should be replaced with a masking character repeated as many times as the length of the original value — preserving the shape of the data while destroying the content. If a sensitive field holds no value (i.e., it is empty/absent), it should be passed through as-is without conversion. All non-sensitive fields must be returned completely unchanged, and the original ordering of all fields must be preserved in the output.

The set of field names considered sensitive should have sensible defaults built in, covering the most common cases teams typically encounter. That default set should be configurable so teams can extend or override it without modifying the core logic — handle the configuration loading the same way the service provider module handles its config merging.

The output of the sanitizer must be a compact, single-line JSON object written to standard output, followed by a newline. Error conditions such as invalid input or unrecognized actions should emit a short diagnostic line rather than crashing.

The masking logic must be physically and logically decoupled from the I/O adapter layer, so the core business rules can be tested in isolation. The whole system should be structured appropriately for its complexity — neither over-engineered nor bundled into a single monolithic file.

A couple extra specifics from the questions that came back: the built-in masked field list is exactly ['password', 'pwd', 'secret', 'password_confirmation', 'cc', 'card_number', 'ccv', 'ssn', 'credit_score', 'api_key']. That same list lives in config/treblle.php under 'masked_fields' and also exists as a hardcoded fallback inside the maskFields method itself, so we still have the expected defaults even if config is not giving us anything.

On matching, field names are checked with preg_match('/\b' . $field . '\b/mi', (string) $key). So this is case-insensitive, uses whole-word boundaries, and avoids partial substring matches. On the value side, if a sensitive field is null, it stays null and does not get turned into a string or masked. The check is $data[$key] = $value != null ? str_repeat('*', strlen($value)) : $value; so null just passes through unchanged. If it is a sensitive non-null string, we replace it with '*' repeated strlen($value) times, using the original byte-length. Example: 'hunter2' becomes '*******'.

Also, the dispatcher output is literally json_encode($masked) and then "\n" written to STDOUT, so the result is compact one-line JSON with no extra whitespace. Example output looks like {"cc":null,"otherValue":"something","password":"****"}\n