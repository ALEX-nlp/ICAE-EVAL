## Product Requirement Document

Hey team, we need to build that routing rule engine thing we discussed last sprint. Basically services are tired of copy-pasting the same header-inspection and traffic-splitting logic everywhere — every team is rolling their own version and they keep getting the weights wrong or forgetting edge cases when configs change live. We want a clean library that takes in some declarative rules and a request context and just tells you where to send the traffic.

The engine needs to support the usual stuff: picking a provider (like that CSE integration we wired up in the old gateway project), validating that nobody accidentally over-allocates traffic weights, matching headers with the operators the platform team already standardized, doing weighted picks in a stable/deterministic way, translating those dark-launch rollout objects the config service spits out, and reloading rules automatically when the config store fires an event.

One thing that keeps biting us is the weight fallback behavior — refer to how we handled the 'remainder goes to latest' pattern in the distribution module, same idea here. Also the config key prefixes are the ones already in use by the ServiceComb config namespace, so keep those consistent.

Output format for the CLI adapter needs to match what the test harness expects exactly. Tests live under rcb_tests/ and there's a test.sh entry point. Please make sure the code is properly split up — last time someone dumped everything in one file and it was a nightmare to review.