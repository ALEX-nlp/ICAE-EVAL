## Product Requirement Document

hey team, we need to get the annotation placement engine shipped. basically we have this chart widget where callouts keep flying outside the drawing area or stomping on each other and users are complaining the labels cover the exact data point they're supposed to describe. super embarrassing in demos.

the core ask: build the layout logic that figures out where each annotation box goes and where its little connector line anchors. there are two flavors of these boxes — the ones that stick to an axis edge (horizontal or vertical) and the ones that float next to a data point. the axis ones should hug their respective edges and basically carve out space so the floating ones route around them. the floating ones prefer one side but should flip if something's in the way.

coordinate stuff should work the same way we did it in the crosshair/cursor module — top-left origin, x right, y down. the output needs to be deterministic so automated snapshot tests don't flake.

one thing i keep forgetting to mention: there's a rule about how many of a given axis type you can show at once — just follow whatever we settled on in that earlier axis-dedup discussion. also the cursor avoidance behavior is NOT the same for all box types so be careful there.

numbers in output should be rounded, placement order matters for the output lines. viewport is 500x500 for all our test cases right now.

quick follow-up since a couple details came up in questions. for the axis-dedup piece, the rule is strict: at most one x_axis callout and at most one y_axis callout may be active at the same time. if a scene includes more than one of the same axis kind, we only place the first one in input order and silently discard the rest. the placed count should only reflect the survivors. that’s the same dedup behavior from Feature 1.3 in start.md, just calling it out here so nobody overthinks it.

also, on cursor behavior, the avoidance logic is only for side callouts. it is NOT applied to x_axis or y_axis at all. those axis callouts stay anchored at their computed position regardless of where the cursor is.

for the connector details, the stem anchor is the point where the line from the box meets the target object. for side callouts, put it on the edge of the object circle: stem_x = coord_x - objectRadius for left placement or stem_x = coord_x + objectRadius for right placement, and stem_y = coord_y. for axis callouts, the stem anchor is always exactly the callout’s coord, because objectRadius is 0 and stem length is 0. related to that, there are two stem lengths in play: side callouts use 12 units, and both x_axis and y_axis use 0. the box offset from the target is stem_length + objectRadius along the attachment axis.

one more placement detail for the axis flavors. for x_axis callouts, the axis line is at y=470 and the viewport bottom is y=500, so there’s a 30 unit gap there. if the callout height fits in that 30 units, set the top at y=470. if the height is bigger than 30, pin it so the bottom sits exactly at y=500, which means top = 500 - height. either way, the stem anchor stays at the original coord point. for y_axis callouts, the left viewport border is x=0 and the axis line is x=30, so again the gap is 30 units. if the width fits, left-align it so the right edge touches x=30, meaning left = 30 - width. if the width is bigger than 30, pin the left edge at x=0. in both cases it stays vertically centered on the target y coord, and again the stem anchor stays at the original coord point.

and just to make sure there’s no ambiguity, coordinates are the same as the crosshair/cursor work: origin at the top-left corner of the viewport, x increases to the right and y increases downward. that’s defined in the Domain Model section of start.md and should be applied consistently everywhere in placement math.