## Product Requirement Document

Hey team, we need a small library/tool that helps developers fill out a 'create service' form and spits out a properly shaped deployment request for our container hosting platform. Right now people are hand-rolling these request payloads and keep getting it wrong — wrong fields, extra slashes in URLs, flags set when they shouldn't be, that sort of thing. The thing needs to handle a few different deployment flavors (private registry image, public registry image, deploying from a source repo), and each one has slightly different rules about what goes in the payload. Some fields just shouldn't exist at all in certain modes, not just be empty or zero.

Also there's some normalization stuff — like the URL cleanup logic we did for the login module a while back, same idea, trim it up and drop trailing separators. Start commands that are blank should be treated like they were never entered.

The code should NOT be one big file — split it up sensibly by responsibility. There should be a thin adapter layer that reads a JSON command and calls into the core logic, don't mix those two things together.

Also needs a test runner script at rcb_tests/test.sh that loops over the JSON case files and writes per-case output files so we can diff them. Make sure it supports pointing at a different cases subdirectory.