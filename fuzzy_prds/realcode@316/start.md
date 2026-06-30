## Product Requirement Document

Hey team, we need to wrap up the gitbeaker API adapter work. The core idea is that devs should be able to describe what they want to do (list stuff, create things, delete, etc.) and the system figures out the right HTTP verb, route, and where the payload goes — no manual URL building. We've been getting complaints that people keep mixing up where to put params (query string vs body) and it's causing bugs in prod.

The adapter needs to handle reading data back (including cases where there's a lot of it and you have to keep fetching more pages), writing/mutating resources, and that streaming thing we talked about — remember how we handled the unsupported transport case in the earlier auth module? Same pattern should apply here.

Also there's the key naming thing — sometimes consumers want the JavaScript-style naming, sometimes they don't, and we need to respect that without it leaking into the core logic.

Routing coverage should include the usual suspects: projects, groups, branches, commits, issues, merge stuff, repo files, and pipelines. Each area has its own quirks around which field goes in the body vs the query.

The whole thing needs to be testable via stdin/stdout JSON so QA can black-box it. Make sure the mock transport layer is completely swappable — no hardcoded network calls anywhere. Outputs need to be deterministic and line-oriented.