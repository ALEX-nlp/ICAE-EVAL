## Product Requirement Document

Hey team, we need to get the BigQuery client adapter wrapper finished up. This is the thing that lets devs stop hand-rolling all those gross request bodies every time they talk to the warehouse. Right now people are copy-pasting endpoint strings and getting the slashes wrong, or they lose precision on big numbers (you know the JS number problem we always run into), and the typed value stuff for dates/times/geo is just a mess of strings everywhere.

Basically we want a clean API layer that handles all the boring formatting: endpoints, typed literals (dates, timestamps, geo points, big integers), query params with type inference, schema parsing from those short comma-separated strings, table metadata, job configs (query jobs, extract jobs, copy jobs), row inserts, and the IAM policy stuff.

For the integer thing, just follow the same safe-range pattern we used in that earlier numeric handling module. And for model exports, we should validate the format names — invalid ones should surface a clean error, not blow up.

The whole thing needs to run as a CLI-style adapter that reads JSON commands from stdin and writes results to stdout so our test harness can drive it. Output should be deterministic and pretty-printed. We'll hook it up to the existing test runner once it's ready. Should be multi-file, not a single blob. Roughly follows what we did on the resource-reference layer last quarter.

One quick follow-up from the questions that came in: for endpoint cleanup, if the string comes in without a protocol prefix we treat it as secure and prepend 'https://'. If it already has an explicit protocol like 'http://', we keep that exactly as provided. Then we strip all trailing slash characters from the final result, no matter how many there are.

On the typed date side, when it’s built from structured parts, the wire value is just 'year-month-day' with no zero-padding. So year=2019, month=1, day=2 becomes '2019-1-2', not '2019-01-02'. If it’s built from a raw string, we preserve that string verbatim.

For create-table, the request body needs a 'tableReference' object containing 'datasetId', 'projectId', and 'tableId'. The projectId there should come from the client' s configured project id ('project-id' in the test harness context). The method is 'POST' and the uri is '/tables'. Metadata formatting follows the same normal rules we already use for table metadata, including name→friendlyName and parsing string schema.

For query params, if the input is a plain object and not an array, parameterMode should be 'named' and each key turns into its own parameter entry with a 'name' field. If params comes in as an array, parameterMode is 'positional' and those entries do not get a 'name' field. Also, the 'types' field should pass straight through into the configuration as-is alongside the parameters.

On model extract jobs, we only accept the allowed destination format strings. Valid values include 'ml_tf_saved_model' and 'ml_tf_lite', case-insensitive on input, but normalized to uppercase in output, so 'ml_tf_saved_model' → 'ML_TF_SAVED_MODEL'. If the format value isn’t recognized, return exactly 'error=invalid_destination_format\n' and nothing else.

For table copy jobs, if sourceProjectId or destProjectId are missing, use the client' s default project id ('project-id'). If they’re explicitly provided, those should override the default. The location field belongs at the job level only when explicitly supplied. jobId should appear at the top level when provided, and jobPrefix should also appear at the top level.

For row inserts, default behavior is that every inserted row gets an auto-generated insertId. If options has 'createInsertId' explicitly false, then we do not add insertId. If 'raw' is true, pass the rows through as-is with no encoding. If options like 'skipInvalidRows' are true, include them in the JSON body. Also, if rows comes in as a single object, treat it as a single-row insert by wrapping it in an array internally.

For IAM, the 'get' action should output method 'POST', uri '/:getIamPolicy', and the json body should contain an 'options' object with 'requestedPolicyVersion'. For the 'set' action, use uri '/:setIamPolicy' and put the policy object in json along with any options like 'etag' at the top level of that json. If someone asks for an unsupported policy version, normalize it to exactly 'error=unsupported_policy_version\n'.

Also keeping the integer boundary behavior aligned with the earlier module: JavaScript's Number.MAX_SAFE_INTEGER boundary (9007199254740991); integers exceeding this produce error=integer_out_of_bounds with the original string value echoed back, as defined in Feature 2.2 integer literal construction.

And one last thing that came up from the reference layer parity check: Feature 6 resource references includes dataset_reference and table_reference factory operations that produce {id, location, parentProjectId} and {id, location, datasetId} shaped objects respectively, found in feature6_resource_references.json.