## Product Requirement Document

hey team, we need to wrap up that repo discovery + publishing assistant we've been talking about. the basic idea is: given some config, find interesting repos on github, check if we've already featured them before, build some content out of the metadata, and push it out to a readme doc and a tweet. pretty straightforward but there are a bunch of small details that keep tripping people up.

the cache logic should work similarly to how we handled session tracking in the notifications module — you know, that thing where we check before we write and bail early if it's already there. same vibe here.

for the content summary, the hashtag priority ordering is a bit nuanced — configured tags should win, but if there are none, fall back through topic then language. also there's a language line that only shows up conditionally based on config.

the tweet formatter needs to handle posts that are too long by cutting the subtitle and adding dots, not the whole message. and safe mode should skip actual publishing but still report success.

the readme publisher needs to decode existing file content before checking for duplicates — if the base64 decode fails it should NOT proceed. also if the content is already plain text it should just work.

for orchestration, if the provider fails we stop early and report that, don't even call publishers.

expiration window is cache_size times periodicity, but clamp negatives to zero. there are a few edge cases like this scattered around — please don't guess, just check the test files.

one quick follow-up since a few folks asked the same things: for the summary hashtag fallback, explicit configured hashtags in the config object always take highest priority. If none are configured, fall back to the configured topic, then the configured language, then the repository's own language field — in that exact order. Only one source is used per summary. also on the comma-separated tag input, each tag is trimmed of surrounding whitespace and prefixed with '#'. Empty input (or all-whitespace input) produces an empty hashtag string and a count of 0. Non-empty items after trimming are all prefixed; the count equals the number of such items.

on tweets, the maximum supported post length is 280 characters. When the formatted tweet exceeds this, only the subtitle is truncated and suffixed with ' ...' (space, three dots) so that the full tweet fits exactly within 280 characters. The title, auxiliary lines, and URL are never truncated. also worth spelling out that twitter_username is empty when: there is no owner, the owner has no login name, the profile lookup fails, or the profile exists but has no twitter/social username set. It is only populated when the owner exists, has a login, and the profile lookup returns a non-empty username.

for cache behavior, operations are processed in order. The output format per operation is 'action:key=result'. For set operations the result is 'stored'. For get on an existing key the result is the stored value. For get on a missing key the result is 'missing'. For delete on an existing key the result is 'deleted'. and for admission, this is the same rule a couple different tests are checking: cache_get must return 'missing' AND the subsequent cache set must succeed; either condition failing returns admitted=false. Put another way, cache admission requires two things: first the identifier must be absent from cache (a 'missing' read result), AND the subsequent write must succeed. If the cache read returns 'present', or if the cache read itself errors, or if the write fails after a missing read, admitted=false is returned. Only both conditions passing yields admitted=true.

last small thing on timing and readme handling: the expiration window in minutes is computed as cache_size multiplied by periodicity. If the result is negative (e.g., negative cache_size), the value is clamped to zero — it cannot go below 0 minutes. and for the plain-text readme edge case, existing_file_content='sometext' is not valid base64 but is treated as readable plain text, duplicate check proceeds, and since title is not found, published=true is returned.