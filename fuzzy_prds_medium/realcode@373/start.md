## Product Requirement Document

Hey team, we need to build out this geospatial coordinate toolkit we've been talking about. Basically devs are spending way too much time re-implementing the same projection math and distance calculations over and over, and we keep getting bug reports about coordinate axis mixups and inconsistent rounding in distance outputs. The idea is a clean CLI tool that reads a JSON command from stdin and writes results to stdout — similar in spirit to the approach we used in that data pipeline adapter project last quarter (you know the one).

The tool needs to handle stuff like: converting coordinates between different spatial reference systems, measuring distances along the earth's surface, looking up metadata about map projections and units, filtering some kind of grid file catalog, and also doing file checksum verification. Error cases should come back as plain text error categories, not raw Python exceptions — our downstream consumers really can't parse stack traces.

The codebase should be properly split up, not one giant file — we've had enough of those. Core logic should be totally separate from the stdin/stdout wiring. Think production-quality repo layout.

One thing I keep hearing from the team: the output formatting for things like azimuth and distance numbers needs to be stable and predictable for comparison purposes. Also make sure the bounding box comparison logic handles both the 'fits inside' and 'overlaps' cases. Let me know if you have questions, I'll dig up the old spec doc if needed.

One extra pass on details the team asked about: for projection metadata/parameter output, each projection parameter should come back on its own line as `parameter=+KEY=VALUE`, sorted alphabetically by key, and there’s always an automatically appended `+type=crs` entry as the final parameter line. Also, boolean flags like `preserve_units` only show up in that parameter output when they’re enabled (true); if they’re off, leave them out completely.

For coordinate transforms, the output format should be `point=X,Y` with exactly 6 decimal places for each ordinate, for example `point=212.623382,4604.975492`. If it’s 3D or time-tagged, keep everything on that same point line, just comma-separated in order. Also, if `always_xy=true` is present, we need to force longitude-first / x-first axis ordering no matter what the CRS says natively. That especially matters for EPSG codes like 2193 (NZTM2000) and 4326 where the native axis order is latitude-first, and the output coordinate order needs to reflect that enforced XY behavior. There’s also a `mode` field on transform input: it can be `legacy_single` or streaming mode. When `mode=legacy_single`, use pyproj's `transform` or equivalent single-call API. If `mode` is absent, use the default transformer pipeline. Either way, the output stays the same as `point=X,Y`.

On invalid transform definitions, please keep the failure response very strict. If the definition is bad, like a non-transform pipeline string such as `epsg:4326` being passed as a pipeline, or the options don’t work together, the output must be exactly `error=invalid_transformation_definition
`. No extra text added around it.

For geodesic inverse output, `forward_azimuth`, `back_azimuth`, and `distance_m` all need to be rounded to 3 decimal places. The example to match is `forward_azimuth=-66.531
back_azimuth=75.654
distance_m=4164192.708
`.

And just to restate the repo shape since this came up again: this needs to stay multi-file, like `src/` with separate modules for core domain logic, I/O adapter, routing/dispatch, formatters, and individual feature handlers. The stdin/stdout JSON adapter has to stay strictly separated from the core business logic, and a single monolithic file is not okay here. The execution flow should follow the adapter pattern from the PRD: CLI entry point reads a JSON command dict from stdin, dispatches to core domain methods, and writes newline-delimited key=value fields to stdout, specifically through `run(command: dict) -> str` so the JSON I/O stays decoupled from the actual logic.