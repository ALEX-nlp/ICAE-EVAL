## Product Requirement Document

Hey team, we need to build out that schema migration safety toolkit we've been talking about. Basically devs keep shooting themselves in the foot when they push db changes to prod — things like adding columns that cause full table rewrites, or foreign keys that grab locks at the wrong time. We had a similar pattern in the background job resolution module we built a while back, so maybe look at how that handles the 'is this a valid task' check for inspiration.

The tool needs to cover a few areas: checking whether a column addition is safe (this depends on the postgres version — there was a big change around version 11 that changed how defaults are stored), checking foreign key patterns, actually applying defaulted columns and reporting back what the db sees, managing check constraints (including the case where old bad rows exist), index operations (concurrent ones have that transaction restriction we always forget about), and background batch data repair jobs.

For the retry stuff, there's a meaningful difference between how transactional vs non-transactional migrations behave when they hit a lock — the retry count should reflect that correctly. We want 2 retries configured so total attempts for transactional should be 3.

Output should be plain key=value lines. Please look at how we handled the constraint-not-found and association-not-found error cases in similar modules — those need clean normalized error keys, not raw exception messages.