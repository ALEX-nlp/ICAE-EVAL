## Product Requirement Document

We need a small library for managing the contents of signed authentication tokens used across our platform. The library should handle four main concerns: checking whether a compact token string is structurally well formed, providing an immutable container for the named data fields carried inside a token, validating that a set of data fields is complete and temporally fresh, and assembling a complete set of data fields from whatever partial information the caller provides.

For the structural check, the library should accept a compact string only when it contains the exact right number of dot-separated sections — anything fewer or greater should be rejected immediately.

For the immutable container, developers should be able to read data by field name, retrieve multiple field values at once, check whether certain fields exist or contain specific values, and fetch a field by its well-known semantic role (such as subject, issuer, or token identity). Any attempt to modify or remove entries from the container must be blocked, consistent with how we handle immutability in the permissions module.

For validation, the library must verify that all required standard fields are present and that the relevant timestamps are within the valid window — expiration cannot have passed, and future-dated fields are not accepted.

For assembly, the library should auto-populate any standard fields the caller leaves out, using a configurable lifetime in minutes that defaults to sixty. The token identity field must be derived deterministically from the subject and the not-before values when not explicitly supplied. Caller-supplied fields must appear first in the output, maintaining their original order, with auto-generated fields appended after.