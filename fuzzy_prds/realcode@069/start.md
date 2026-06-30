## Product Requirement Document

hey team, we need to wrap up that repo discovery + publishing assistant we've been talking about. the basic idea is: given some config, find interesting repos on github, check if we've already featured them before, build some content out of the metadata, and push it out to a readme doc and a tweet. pretty straightforward but there are a bunch of small details that keep tripping people up.

the cache logic should work similarly to how we handled session tracking in the notifications module — you know, that thing where we check before we write and bail early if it's already there. same vibe here.

for the content summary, the hashtag priority ordering is a bit nuanced — configured tags should win, but if there are none, fall back through topic then language. also there's a language line that only shows up conditionally based on config.

the tweet formatter needs to handle posts that are too long by cutting the subtitle and adding dots, not the whole message. and safe mode should skip actual publishing but still report success.

the readme publisher needs to decode existing file content before checking for duplicates — if the base64 decode fails it should NOT proceed. also if the content is already plain text it should just work.

for orchestration, if the provider fails we stop early and report that, don't even call publishers.

expiration window is cache_size times periodicity, but clamp negatives to zero. there are a few edge cases like this scattered around — please don't guess, just check the test files.