## Product Requirement Document

hey team, filing this based on some feedback we got from a few backend devs who are trying to wire up our log shipping pipeline. basically the complaint is that every team is rolling their own version of the same plumbing — someone manually builds the JSON body, someone else wrote their own retry loop, another person has their own timestamp hack to avoid duplicate entries. it's a mess and nothing is consistent.

we need a library/adapter thing that handles all of this in one place. it should be able to take log events and pack them into the right wire format for the ingest endpoint (we use that same push API as before, similar to what the metrics team did with their protobuf stuff a few months back). it also needs to group events by their label identity — some events come in with extra labels attached at emit time that should affect grouping. timestamps need to be deduplicated somehow within the same millisecond bucket.

on the delivery side, when something fails it should retry automatically — but there's a special case for rate-limit responses that the PM from infra mentioned should be configurable. also there's a buffering layer that should respect a byte ceiling, and reuse allocated buffers when possible.

label text can come in different formats with different separators — including regex-based ones — and bad label data should surface as a clean error, not a stack trace. there's also some string utility stuff we apparently need for encoding correctness. let's get this scoped and built.