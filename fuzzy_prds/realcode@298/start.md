## Product Requirement Document

Hey team, we need to wrap up the auth toolkit we've been building. The core pieces are mostly specced out but there are a few gaps I want to flag before we hand this off to the dev team.

First, the password hashing — we need to support multiple strategies and one of them is that silly 'reverse' trick we used in the demo last quarter to prove pluggability works. Make sure the verification output format is consistent across all strategies.

For the permission system, there's a nuance around how denials behave depending on which 'mode' you're in — the strict vs the other one. We had a whole discussion about this in the Figma meeting but basically: one mode lets the person's own settings win, the other lets any denial from anywhere kill the access. Also there's that thing with the star-based key matching and the grouped class keys (you know, the @ syntax thing) — make sure exact keys beat the pattern ones.

The login protection stuff needs three separate sources checked in a specific order, and the delay math has two flavors — a simple cutoff and a tiered one. The entity permission mutations need to respect insertion order when printing.

One thing I'm unclear on is how many sources the throttle gate actually checks and what order it checks them — can someone confirm the priority chain? Also need to nail down the 'create on update' behavior for permission mutations.