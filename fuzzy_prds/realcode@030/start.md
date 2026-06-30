## Product Requirement Document

Hey team, we need to build out that auth strategy wrapper we've been talking about. Basically, devs are tired of hand-rolling all the boilerplate every time they wire up a new identity provider — they keep getting the URLs wrong, forgetting to validate tokens properly, and the user profile shapes coming back are inconsistent depending on which flow they used. It's causing a bunch of support tickets.

The library should be configurable once with the provider details and then just handle everything: figuring out the right endpoints automatically (but still letting you override them if needed), building the login redirect params based on what hints are available, doing the full token checking sequence, and spitting out a consistent user object regardless of whether it came from the legacy format or the newer OIDC style.

For the token checks, refer to the same claim-by-claim validation ordering we settled on during that login module refactor — same priority sequence, same error categories. The profile normalization should handle the 'pipe-delimited ID' edge cases the same way we discussed.

One thing that burned us before: the config setup must not touch the caller's original options object. That caused a really subtle bug last time in staging.

Please separate concerns properly — don't dump everything in one file. Each major responsibility should live in its own module. The adapter layer that handles the JSON in/out should be totally decoupled from the core logic.