## Product Requirement Document

Hey team, we need to get the BigQuery client adapter wrapper finished up. This is the thing that lets devs stop hand-rolling all those gross request bodies every time they talk to the warehouse. Right now people are copy-pasting endpoint strings and getting the slashes wrong, or they lose precision on big numbers (you know the JS number problem we always run into), and the typed value stuff for dates/times/geo is just a mess of strings everywhere.

Basically we want a clean API layer that handles all the boring formatting: endpoints, typed literals (dates, timestamps, geo points, big integers), query params with type inference, schema parsing from those short comma-separated strings, table metadata, job configs (query jobs, extract jobs, copy jobs), row inserts, and the IAM policy stuff.

For the integer thing, just follow the same safe-range pattern we used in that earlier numeric handling module. And for model exports, we should validate the format names — invalid ones should surface a clean error, not blow up.

The whole thing needs to run as a CLI-style adapter that reads JSON commands from stdin and writes results to stdout so our test harness can drive it. Output should be deterministic and pretty-printed. We'll hook it up to the existing test runner once it's ready. Should be multi-file, not a single blob. Roughly follows what we did on the resource-reference layer last quarter.