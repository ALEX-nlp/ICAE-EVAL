## Product Requirement Document

Hey team, we need to wrap up that mobile starter kit thing we've been talking about. The idea is basically that every new app project ends up with the same copy-paste mess — devs are manually wiring up network lists, handling startup screens, dealing with error messages that expose internal exception names, and so on. It's a nightmare and every project does it slightly differently.

What we want is a clean foundation that handles the "boring glue" automatically. Think about how we did the preference fallback stuff for the onboarding flow in the login module last time — something like that pattern but more formalized across the board.

Specifically we care about: loading a remote list and getting back clean model rows, translating network failures into something user-friendly (no raw exception class names in the output please), reading/writing that first-launch flag with safe defaults when things go wrong, a use-case layer that sits between the UI and data, and a home screen coordinator that ties all of this together with loading states and navigation.

The whole thing needs a test runner that a CI pipeline can just call with a single bash command. Results should be written as separate files per test case so they're easy to diff. We also need to make sure different test suites don't stomp on each other's output files.

Keep it clean, layered, no god files. Reach out if anything is unclear.