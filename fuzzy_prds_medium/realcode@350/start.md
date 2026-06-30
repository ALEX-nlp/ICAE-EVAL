## Product Requirement Document

Hey team, we need to get the auto-lock timing feature sorted out for the Android app. Users have been complaining that the app either locks too aggressively or never seems to lock at all depending on which option they pick in settings. The lock screen choices aren't mapping to the right wait times on the backend, which is causing confusing behavior. Can we make sure all the duration options are properly wired up?

Also while we're in there — remember how we handled the 'never lock' edge case in that settings screen we did a while back? We should follow the same pattern here. The 'Never' option needs special treatment since it's not really a time value.

The output should just expose each named choice paired with its numeric value so the rest of the system can consume it cleanly. The full list of options should be supported: the short ones like one minute and five minutes, the medium ones, and the longer overnight-style ones. Make sure the never-lock option doesn't accidentally get a real millisecond value assigned to it — that's been a source of bugs before.

This is blocking the QA team from signing off on the lock screen settings flow, so please prioritize. Should be straightforward if we follow the existing conventions.

One quick follow-up from the questions that came in: for this mapping, the complete set needs to be exactly OneMinute, FiveMinutes, FifteenMinutes, ThirtyMinutes, OneHour, TwelveHours, TwentyFourHours, and Never. All eight should be supported and all eight should produce output entries so nothing gets skipped depending on which option the user picked.

On the values, we should wire them exactly as follows, all in milliseconds: OneMinute=60000, FiveMinutes=300000, FifteenMinutes=900000, ThirtyMinutes=1800000, OneHour=3600000, TwelveHours=43200000, TwentyFourHours=86400000. And just to be extra clear on the special case, Never must be represented as exactly zero (0 milliseconds), not a sentinel like -1 or Long.MAX_VALUE. Any non-zero value for Never would be treated as a real timeout by the consuming system, which is the bug we want to avoid.

This should line up with the auto_lock_durations feature contract in rcb_tests/public_test_cases/feature8_auto_lock_durations.json, specifically the rule that Never must map to 0 milliseconds rather than any non-zero or sentinel value.