## Product Requirement Document

Hey team, we need to ship the browser entropy toolkit we've been talking about. The idea is to give devs a single layer that handles all the messy browser readings — you know, the ones that come back as strings instead of numbers, or just go missing entirely, or randomly collapse to zero in fullscreen. We had a similar defensive-parsing pattern in the old login module, so just follow that spirit but make it a proper standalone thing this time.

The toolkit needs to handle number coercion (both integer and float flavors), some kind of fingerprint-ready hash (the exact algo was agreed on in the architecture call — make sure the output is always the same fixed width), a way to gather multiple signals at once without one bad reading killing the whole batch, and the screen geometry thing where the available area sometimes drops to zero temporarily and we need to remember the last good value.

Please keep the code organized — don't dump everything in one file, we've had complaints about that before. Separate the concerns cleanly. The execution layer that reads commands and writes results should be totally isolated from the actual logic.

One thing I'm not 100% sure was written down anywhere: what exactly happens when availLeft or availTop are missing vs zero — there's a difference there that caused a bug in QA last sprint. Make sure that's handled correctly. Also confirm the rounding behavior for fractional bases, that one always trips people up.