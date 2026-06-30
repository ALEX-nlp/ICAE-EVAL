## Product Requirement Document

Hey team, we need to tighten up our request wrapper logic to handle flaky networks better. The core requirement is that if a call fails, we retry it, but we must always hit the exact same URL as the original request—no changing endpoints mid-stream. 

For the default behavior, if someone doesn't specify a retry count, we should try a total of 4 times (the initial shot plus 3 retries). If they do pass a custom count, say N, we should do N+1 attempts total. By default, only actual network drops (rejections) should trigger a retry; if the server responds with an HTTP error like 503 or 404, we should just bubble that up immediately without retrying.

However, we need to support custom logic. If a user provides a list of status codes, we should treat those as failures and retry them. We also need to support a custom function to decide whether to retry based on the response. When calculating the wait time between retries, if a custom delay function is provided, pass the same context arguments to the delay function as we do for the retry predicate so the logic stays consistent. If no delay is specified, just wait 1 second.

Finally, the summary report needs to show the URL of the very first attempt and the total number of requests made. Please ensure the logs follow the standard trace output format used by the logging module so our monitoring tools parse them correctly.