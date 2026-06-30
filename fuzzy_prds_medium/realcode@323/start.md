## Product Requirement Document

Hey team, we need to wrap up that mobile starter kit thing we've been talking about. The idea is basically that every new app project ends up with the same copy-paste mess — devs are manually wiring up network lists, handling startup screens, dealing with error messages that expose internal exception names, and so on. It's a nightmare and every project does it slightly differently.

What we want is a clean foundation that handles the "boring glue" automatically. Think about how we did the preference fallback stuff for the onboarding flow in the login module last time — something like that pattern but more formalized across the board.

Specifically we care about: loading a remote list and getting back clean model rows, translating network failures into something user-friendly (no raw exception class names in the output please), reading/writing that first-launch flag with safe defaults when things go wrong, a use-case layer that sits between the UI and data, and a home screen coordinator that ties all of this together with loading states and navigation.

The whole thing needs a test runner that a CI pipeline can just call with a single bash command. Results should be written as separate files per test case so they're easy to diff. We also need to make sure different test suites don't stomp on each other's output files.

Keep it clean, layered, no god files. Reach out if anything is unclear.

One quick follow-up since a few details came up in chat. On the network side, connectivity failures and interrupted timeouts should both come out as `error=no_connectivity`. For HTTP failures, the output should be `error=api_error` and also include `operation=request`, `http_status`, `http_message`, and `body_message`. If it’s some other unhandled request I/O failure, that should be `error=unhandled_request_error` with the supplied message. In all of these request cases, make sure `operation=request` is included, and we still do not want host-language exception class names showing up anywhere in the output.

On the launch flag behavior, if there’s a recoverable preference read I/O failure, just fall back quietly to `first_time_launch=true`. If the preference read fails in an unexpected non-I/O way, normalize it as an upstream failure with `operation=preference_read`. And when a value is successfully stored/read through that path, emit it as `first_time_launch=<value>`. Same storage contract as discussed before: on recoverable IO read failure fall back to first_time_launch=true; on unexpected failure emit a normalized upstream error with operation=preference_read; see rcb_tests/public_test_cases/feature3_launch_preference_storage.json

Also wanted to lock the successful model output format since it’s shared in two places. A successful model result should output `result=models` on the first line, then `count=<n>`, then one `item[<index>].id=<id>` line per row, keeping the exact same order as the payload. This same format is used by both the feed mapping (Feature 1) and the domain model query (Feature 4).

For the home flow, a loaded home scenario should output `screen_title=Home`, `loading_sequence=false,true,false`, `visible_model_ids=<comma-separated ids in feed order>`, `first_time_launch=<bool>`, and `toast=none`. If it’s the navigate-from-model scenario, the output should be `navigation_route=second/<first_model_id>`.

And for running this in CI, the command is `bash rcb_tests/test.sh` with optional `--cases-dir <subdir>` flag. If nothing is passed, the default cases-dir is `test_cases`, and results should be written to `rcb_tests/stdout/<cases-dir>/`. This is the pathing we should stick to so suites stay separated and don’t step on each other.