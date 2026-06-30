## Product Requirement Document

Hey team, we need to get this retry control utility shipped. The basic idea is that we want developers to stop copy-pasting retry loops everywhere and instead use a clean policy-based approach. Think of it like that circuit-breaker pattern we discussed last quarter but simpler — just configurable retries with timing.

Some things I know we need: different wait strategies (the usual suspects — flat wait, growing wait, the math sequence one), a way to say 'retry on any error except these specific ones' with proper parent/child error awareness, and lifecycle hooks so callers can observe what's happening. We also need async support — the team mentioned needing both a default thread pool and the ability to bring your own.

One thing that came up in the last sprint review: users were frustrated that certain return values weren't being treated as failures — like when the downstream service returns a 'not ready yet' signal instead of throwing. We need to handle that.

Also, validation should be strict — people were shipping bad configs silently and only finding out at runtime. Should catch things like missing timing config, contradictory retry rules, etc.

Refer to how we handled the exception hierarchy in the exclusion matching work — same inheritance-aware logic should apply here. Custom predicate support would be a bonus if it's not too much lift.

Target language is Java. Keep it clean and testable.

A couple follow-ups from the questions that came in. On the timing side, exponential backoff computes the wait as base_delay_ms * 2^(failed_tries - 1). So for failed_tries=5 and base_delay_ms=100, the result is 100 * 2^4 = 1600ms. The multiplier is based on the number of already-failed tries, not the attempt index. Fibonacci is the same idea in terms of using failed tries, and the formula is fib(failed_tries) * base_delay_ms. The Fibonacci sequence starts 1,1,2,3,5... so for failed_tries=4, fib(4)=3, and with base_delay_ms=5000 the wait is 15000ms. That Fibonacci backoff strategy is fib(failed_tries) * base_delay_ms.

Also worth calling out that delay amounts specified with unit='seconds' are stored internally as milliseconds (amount * 1000). So delay amount=5, unit=seconds results in delay_ms=5000. The policy stores and reports the converted millisecond value. On the validation front, policies using the no_wait backoff strategy do NOT require a delay to be configured. Validation should accept a policy with max_tries and no_wait alone as config_valid=true, without requiring a delay setting.

For termination, a policy can be configured with retry_indefinitely=true as a substitute for max_tries. When validation is enabled, a policy with retry_indefinitely=true satisfies the termination condition requirement so max_tries is not required. These two options are mutually exclusive from a semantic standpoint.

For the simulation behavior, the outcomes list is consumed in order. Once all outcomes have been used, the final outcome in the list repeats indefinitely for all subsequent attempts. This allows a single outcome to represent a persistent failure across all max_tries attempts.

On custom retry logic, two custom exception predicates are supported in the test harness: message_contains_retry (retryable if the exception message contains the substring 'retry') and custom_value_positive (retryable if the exception carries a numeric value field greater than zero). If the predicate returns false, the exception is treated as unexpected and not retried.

And for the exception include/exclude behavior, same inheritance-aware matching we already talked about still applies here: excluding a parent type (e.g., io_error) also excludes child types (e.g., file_not_found), implemented in the exception taxonomy/hierarchy module.