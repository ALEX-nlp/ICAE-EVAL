## Product Requirement Document

We need a small utility library that lets our system persist and reload deployment configuration records in two standard text-based interchange formats. Each configuration record describes a single deployable component: a short identifier, the name of its backing implementation, and an ordered list of named startup settings. Groups of records can be packaged into a collection for bulk deployment operations.

The library must convert a single record or an entire collection into either format, and read those formats back into in-memory objects. When reading a collection document it should gracefully ignore extra descriptive fields not part of the core model — such as human-readable labels or localization hints — rather than failing.

After a parse operation, reported state must be fully deterministic: collection size first, then each record in document order, and within each record the startup settings listed with keys sorted alphabetically. Every output line must end with a newline.

The internal business logic must stay completely separate from the command-routing layer. The routing adapter reads a structured request from standard input and delegates to the core library. A specific internal component — findable by searching the portal package — acts as the central serialization helper wiring together both format encoders. A dedicated entry point class in that same package handles request dispatching. The full suite of format round-trip checks lives under a test script that accepts a directory of case files.