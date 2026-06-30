## Product Requirement Document

Hey team, we need to get the auto-lock timing feature sorted out for the Android app. Users have been complaining that the app either locks too aggressively or never seems to lock at all depending on which option they pick in settings. The lock screen choices aren't mapping to the right wait times on the backend, which is causing confusing behavior. Can we make sure all the duration options are properly wired up?

Also while we're in there — remember how we handled the 'never lock' edge case in that settings screen we did a while back? We should follow the same pattern here. The 'Never' option needs special treatment since it's not really a time value.

The output should just expose each named choice paired with its numeric value so the rest of the system can consume it cleanly. The full list of options should be supported: the short ones like one minute and five minutes, the medium ones, and the longer overnight-style ones. Make sure the never-lock option doesn't accidentally get a real millisecond value assigned to it — that's been a source of bugs before.

This is blocking the QA team from signing off on the lock screen settings flow, so please prioritize. Should be straightforward if we follow the existing conventions.