## Product Requirement Document

Hey team, we need to build out the team workspace management piece for the platform. Basically users should be able to create teams, add/remove people, switch between teams, and handle all the role/permission stuff. Think of it like that membership layer we built for the org module a while back, but more fleshed out.

A few things I know we need: when someone tries to do something they shouldn't, we need consistent error responses (not just random 500s or whatever). There's also some HTTP redirect behavior for the team-switching and role-update flows that needs to be wired up properly — the product team is getting complaints that the current prototype just hangs or throws a generic error page.

Also important: when a user deletes their account, we can't leave orphaned teams floating around — their owned teams should go away but teams owned by others should stay intact. Oh and permissions work in two layers — the role itself plus whatever the token was issued with — both have to line up for access to go through.

One more thing: duplicate members, missing users, owners trying to leave their own team — all of these need to surface a specific, normalized message, not just a boolean or a generic failure. The format needs to match what the frontend expects. Ask me if you're unsure about the exact shape of those error payloads.

One quick follow-up from the questions that came in: for the permission summary piece, we need to de-duplicate permissions across all registered roles and return them as one comma-separated string sorted lexicographically (A-Z). That output also needs the extra flags around it, specifically has_permissions=yes and the total role_count. The example should come back exactly like this: has_permissions=yes
permissions=create,delete,read,update
role_count=2

On the validation side, let’s keep this really locked down and consistent. All validation failures should come back in the normalized three-line format exactly as error=validation_failed
field=<field_name>
message=<human readable message>
. So for a blank team name, that means field is 'name' and the message is exactly 'The name field is required.' Same idea for member add when the email doesn’t match any registered user: error=validation_failed
field=email
message=We were unable to find a registered user with this email address. And for auth failures, the format stays newline-delimited too, just error=authorization_denied
with no extra fields.

A couple lifecycle details too: a team created through the normal team creation flow is NOT a personal team, so the output needs personal_team=no. Personal team status is its own flag and should be false by default for user-created teams. After the team is created and the owner is set up, we should be able to observe personal_team_id_matches=yes and current_team_id_matches=yes, and also owner_belongs_to_team=yes and owner_owns_team=yes, so we know all those references landed on the created team context correctly.

For account deletion, the expected behavior is that all teams the deleted user owns are also deleted, and all of that user’s team memberships on teams owned by others are removed. Teams owned by other users should remain intact. The expected output here tracks teams_before, memberships_before, user_deleted=yes, teams_after, and memberships_after. And on the team member removal path, when removal succeeds we also need to dispatch the removal event signal, so include removed_event_dispatched=yes along with member_count_before and member_count_after.

Last thing, confirming two authorization rules that came up: only the team owner is authorized to delete a team, so if a non-owner actor tries deletion validation the response must be exactly error=authorization_denied
and nothing else, same shape as unauthorized member removal. And on the permissions model, the two-layer check still applies in the token_limited_team_permission scenario: both the team role’s permissions AND the token’s active permission scopes have to include the requested permission or access should be denied.