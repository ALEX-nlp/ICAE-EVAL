## Product Requirement Document

Hey team, we need to wrap up the admin panel permissions helper we discussed last sprint. The basic idea is that we want something that can automatically figure out the right 'name' for each admin screen/resource so we don't have to keep manually writing those strings every time someone adds a new screen. Last time we did something similar for the login module — same kind of naming convention applies here, just refer to how we handled that.

The tool also needs to be smart enough to skip certain screens we don't want to expose (like the main dashboard landing), and it should handle the three types of things we have in the panel: the data management screens, the standalone pages, and the little stat cards/charts at the top of the dashboard.

The big thing for the ops team is that whenever a new screen gets added, the super-admin account should automatically get access without anyone having to remember to go in and add it manually. We've had incidents where a new report page went live and the super-admin couldn't even open it for two days.

One more thing — there's been a complaint that some naming outputs are causing weird bugs downstream because of a specific character that conflicts with how our system parses permission strings internally. We need to make sure those are caught and rejected with a clear error. The code should be split into sensible modules, not one big file.