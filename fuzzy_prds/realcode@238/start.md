## Product Requirement Document

Hey team, we need a small utility library for handling geo coordinates. Basically we keep running into issues where coordinate values get mangled when we pass them into external map services — stuff like weird number formatting that the downstream APIs just reject outright. It's been causing support tickets and manual workarounds from the devs every time they integrate a new region or edge-case location.

The library should take a lat/lng pair and spit out a clean, consistent text representation we can drop straight into a URL or query param. Make sure it follows the same kind of separation pattern we used in that address-formatter module — you know, keep the actual formatting logic away from any I/O or transport layer. SOLID principles, etc.

Should be runnable/testable via a JSON-in, text-out adapter on stdin/stdout so our test harness can drive it automatically. The test runner lives under rcb_tests/ and should be invokable with a single bash command, writing each case output to its own file.

The tricky edge cases are the ones that have been biting us in production — particularly around certain coastal or near-equator regions with coordinates that end up looking totally garbled in logs. Make sure those are handled gracefully. Nothing fancy needed, just solid and dependable.