## Product Requirement Document

Hey team, we need to tighten up our request wrapper logic to handle flaky networks better. The core requirement is that if a call fails, we retry it, but we must always hit the exact same URL as the original request—no changing endpoints mid-stream. 

For the default behavior, if someone doesn't specify a retry count, we should try a total of 4 times (the initial shot plus 3 retries). If they do pass a custom count, say N, we should do N+1 attempts total. By default, only actual network drops (rejections) should trigger a retry; if the server responds with an HTTP error like 503 or 404, we should just bubble that up immediately without retrying.

However, we need to support custom logic. If a user provides a list of status codes, we should treat those as failures and retry them. We also need to support a custom function to decide whether to retry based on the response. When calculating the wait time between retries, if a custom delay function is provided, pass the same context arguments to the delay function as we do for the retry predicate so the logic stays consistent. If no delay is specified, just wait 1 second.

Finally, the summary report needs to show the URL of the very first attempt and the total number of requests made. Please ensure the logs follow the standard trace output format used by the logging module so our monitoring tools parse them correctly.

One extra bit the team asked about on the trace side: the summary needs to be able to show both options_passed=false and options_passed=true, depending on what actually happened for that run, and the outcome line should stay exact. For a successful response, use 'outcome=resolved status=<int>', and for a rejected call, use 'outcome=rejected error=<message>'. The per-attempt log line also needs to stay in the standard shape: '<name>_call attempt=<n> error=<msg|none> status=<s|none>'. If the attempt got a response, then the 'error' field in the log must be 'none' and 'status' must be the response status.

Also clarifying the immediate output behavior: as requests are issued, emit 'fetch_count=<N>' right away, where N is the number of requests issued so far, and emit 'last_url=<url>' right away too. Then in the summary block, include 'fetch_count=<N>' again, this time reflecting total requests issued.

And on retry timing, when retryDelay is provided, the retryDelay function is invoked with (attempt_index, error, response) before scheduling the retry; the return value is the delay. That should line up with the same context we’re already passing around for the retry decision so custom logic stays predictable.