## Product Requirement Document

hey team, we need to get the annotation placement engine shipped. basically we have this chart widget where callouts keep flying outside the drawing area or stomping on each other and users are complaining the labels cover the exact data point they're supposed to describe. super embarrassing in demos.

the core ask: build the layout logic that figures out where each annotation box goes and where its little connector line anchors. there are two flavors of these boxes — the ones that stick to an axis edge (horizontal or vertical) and the ones that float next to a data point. the axis ones should hug their respective edges and basically carve out space so the floating ones route around them. the floating ones prefer one side but should flip if something's in the way.

coordinate stuff should work the same way we did it in the crosshair/cursor module — top-left origin, x right, y down. the output needs to be deterministic so automated snapshot tests don't flake.

one thing i keep forgetting to mention: there's a rule about how many of a given axis type you can show at once — just follow whatever we settled on in that earlier axis-dedup discussion. also the cursor avoidance behavior is NOT the same for all box types so be careful there.

numbers in output should be rounded, placement order matters for the output lines. viewport is 500x500 for all our test cases right now.