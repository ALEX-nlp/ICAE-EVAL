## Product Requirement Document

Hey team, we need to build out the team workspace management piece for the platform. Basically users should be able to create teams, add/remove people, switch between teams, and handle all the role/permission stuff. Think of it like that membership layer we built for the org module a while back, but more fleshed out.

A few things I know we need: when someone tries to do something they shouldn't, we need consistent error responses (not just random 500s or whatever). There's also some HTTP redirect behavior for the team-switching and role-update flows that needs to be wired up properly — the product team is getting complaints that the current prototype just hangs or throws a generic error page.

Also important: when a user deletes their account, we can't leave orphaned teams floating around — their owned teams should go away but teams owned by others should stay intact. Oh and permissions work in two layers — the role itself plus whatever the token was issued with — both have to line up for access to go through.

One more thing: duplicate members, missing users, owners trying to leave their own team — all of these need to surface a specific, normalized message, not just a boolean or a generic failure. The format needs to match what the frontend expects. Ask me if you're unsure about the exact shape of those error payloads.