## Product Requirement Document

Hey team, we need to build a small lookup service for stdlib backport packages — basically a catalog that devs can query to figure out whether a given module has a backport they can install on older Python versions. Think of it like that compatibility table we maintain manually in the packaging tool, but this time it should be a proper service with a query interface so we stop duplicating that knowledge everywhere.

The service needs to handle a handful of operations: listing what's in the catalog, checking membership, rendering a nice human-readable output (with alignment, similar to how we did the indented listing in the dependency reporter), stripping version pins off identifiers, collapsing a bunch of identifiers down to their bare names, and expanding a bare name into all its versioned variants.

For the availability info, there's a special display convention for cases where a module never became native on a given Python line — just refer to the marker format we agreed on in the version formatting spec, you'll know it when you see it. The render output needs to be padded so all the separators line up nicely.

The expand operation should show the unversioned entry first, then pins newest-to-oldest. The adapter reads JSON from stdin and writes plain-text results to stdout. Any bad input should surface as a neutral error line, never a stack trace. One test runner script should exercise all the case files.