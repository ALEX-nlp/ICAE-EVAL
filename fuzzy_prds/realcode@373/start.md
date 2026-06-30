## Product Requirement Document

Hey team, we need to build out this geospatial coordinate toolkit we've been talking about. Basically devs are spending way too much time re-implementing the same projection math and distance calculations over and over, and we keep getting bug reports about coordinate axis mixups and inconsistent rounding in distance outputs. The idea is a clean CLI tool that reads a JSON command from stdin and writes results to stdout — similar in spirit to the approach we used in that data pipeline adapter project last quarter (you know the one).

The tool needs to handle stuff like: converting coordinates between different spatial reference systems, measuring distances along the earth's surface, looking up metadata about map projections and units, filtering some kind of grid file catalog, and also doing file checksum verification. Error cases should come back as plain text error categories, not raw Python exceptions — our downstream consumers really can't parse stack traces.

The codebase should be properly split up, not one giant file — we've had enough of those. Core logic should be totally separate from the stdin/stdout wiring. Think production-quality repo layout.

One thing I keep hearing from the team: the output formatting for things like azimuth and distance numbers needs to be stable and predictable for comparison purposes. Also make sure the bounding box comparison logic handles both the 'fits inside' and 'overlaps' cases. Let me know if you have questions, I'll dig up the old spec doc if needed.