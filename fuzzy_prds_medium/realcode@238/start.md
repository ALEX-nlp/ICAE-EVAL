## Product Requirement Document

Hey team, we need a small utility library for handling geo coordinates. Basically we keep running into issues where coordinate values get mangled when we pass them into external map services — stuff like weird number formatting that the downstream APIs just reject outright. It's been causing support tickets and manual workarounds from the devs every time they integrate a new region or edge-case location.

The library should take a lat/lng pair and spit out a clean, consistent text representation we can drop straight into a URL or query param. Make sure it follows the same kind of separation pattern we used in that address-formatter module — you know, keep the actual formatting logic away from any I/O or transport layer. SOLID principles, etc.

Should be runnable/testable via a JSON-in, text-out adapter on stdin/stdout so our test harness can drive it automatically. The test runner lives under rcb_tests/ and should be invokable with a single bash command, writing each case output to its own file.

The tricky edge cases are the ones that have been biting us in production — particularly around certain coastal or near-equator regions with coordinates that end up looking totally garbled in logs. Make sure those are handled gracefully. Nothing fancy needed, just solid and dependable.

One extra bit the team asked about: for the ugly tiny values, we need to be very literal about how they come out. If a coordinate component is something like 0.000009 or 0.0000009, render it in full plain fixed-point decimal form and never let it flip into scientific/exponent notation like 9E-06. The fractional digits should expand as needed so the value is represented exactly and not rounded away.

Also, when a component is exactly zero (0.0), keep it as the literal token '0.0'. Not '0', not blank, and not omitted. Treat lat and lng independently here, so if both are zero then the final string should be '0.0,0.0'.

On the actual output shape, keep it super strict: a single line with latitude and longitude joined by exactly one comma, no surrounding whitespace, and then a trailing newline character. For example: '-33.8688,151.2093\n'. No extra spaces, no brackets, no labels. Also the decimal separator must always be a period (.) no matter what locale or regional settings the host machine is using, so this needs to be explicitly locale-independent rather than whatever the system default number-to-string conversion happens to do.

And on the design side, yes, this should line up with the SOLID notes in start.md and the architecture section of the PRD: SRP with separate parsing, value type, formatting rule, output rendering; OCP so the formatting rule can be extended without modifying coordinate type; and DIP so output rendering depends on an abstraction not a concrete I/O implementation.