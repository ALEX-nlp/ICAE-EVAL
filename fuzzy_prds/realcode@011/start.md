## Product Requirement Document

Hey team, we need to build out this HTML assertion utility we've been talking about. Basically it's a tool that lets devs write checks against rendered markup output without having to do all the messy DOM traversal stuff manually every time. The core idea is you feed it some HTML and tell it what you expect to find, and it either confirms the match or tells you what failed in a consistent, readable way.

We need it to handle the usual stuff — checking that certain text shows up, that specific element types exist, that links point to the right places, that CSS classes are on the right elements, that attribute values are exactly right. There's also a scoping thing — like the validation flow we used in that last auth module — where you can narrow down to a specific part of the document before running your checks. And we should support picking a specific element from a list by position, not just "find any match."

There's also that reusable charset check that keeps coming up in onboarding issues — we should make that a first-class thing so people stop reinventing it.

The output format needs to be totally deterministic and machine-parseable so CI pipelines can consume it without custom parsing logic. When something matches, say so cleanly. When it fails, tell us what condition failed without leaking internal error details.

Input should come in via stdin as structured data, one check per invocation.