## Product Requirement Document

Hey team, we need to wrap up the gitbeaker API adapter work. The core idea is that devs should be able to describe what they want to do (list stuff, create things, delete, etc.) and the system figures out the right HTTP verb, route, and where the payload goes — no manual URL building. We've been getting complaints that people keep mixing up where to put params (query string vs body) and it's causing bugs in prod.

The adapter needs to handle reading data back (including cases where there's a lot of it and you have to keep fetching more pages), writing/mutating resources, and that streaming thing we talked about — remember how we handled the unsupported transport case in the earlier auth module? Same pattern should apply here.

Also there's the key naming thing — sometimes consumers want the JavaScript-style naming, sometimes they don't, and we need to respect that without it leaking into the core logic.

Routing coverage should include the usual suspects: projects, groups, branches, commits, issues, merge stuff, repo files, and pipelines. Each area has its own quirks around which field goes in the body vs the query.

The whole thing needs to be testable via stdin/stdout JSON so QA can black-box it. Make sure the mock transport layer is completely swappable — no hardcoded network calls anywhere. Outputs need to be deterministic and line-oriented.

One extra pass on a few details the team asked about. For the key naming behavior, this only kicks in when the input contains `"key_style": "camelCase"`. In that case, all keys in the returned objects must be converted from snake_case to camelCase before rendering, so `gravatar_enable` becomes `gravatarEnable`. If that flag is not explicitly set, we leave keys exactly as they come back from the mock transport.

On the read/pagination side, when `"page_links": true` is set, the adapter should follow link-based next-page hops automatically and keep accumulating records across pages until the server reports no further page. A `"limit_pages"` value caps how many pages are fetched. Without a limit, the mock returns 10 pages of 2 items each (20 total). With `limit_pages: 3`, only 3 pages (6 items) are fetched. The output here should include count, first/last records, request count, and the final fetched URL.

Also, `sudo` and `isForm` are reserved transport options, so they need to be pulled out before anything is placed into the body. The body should contain only the remaining keys after `sudo` (and other reserved keys like `isForm`) are stripped out. The extracted `sudo` value is printed separately as `sudo=<value>`. And if the payload contains `"isForm": true`, then instead of rendering the body as a JSON object in stdout, render it as `body="[multipart_form]"`. The `isForm` key itself must not appear in the rendered body payload.

For the stream request behavior, same idea as what we discussed earlier: when `"available": false` is passed for a stream request, the adapter must output `error=unsupported_stream` followed by `operation=stream_resource`. When `"available": true`, it outputs `operation=stream_resource`, `url=test`, and `query={"ref":"main"}`. Important part is that the error category string is the language-neutral token `unsupported_stream`, and this should be modeled as a specific error type rather than a generic exception.