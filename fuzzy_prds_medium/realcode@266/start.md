## Product Requirement Document

Hey team, we need a codec utility library for our Lambda event pipeline. Basically our consumers are drowning in boilerplate every time they try to read a DynamoDB stream record or process a CloudWatch Logs subscription — everyone's hand-rolling the same conversions differently and we keep getting weird silent bugs when someone assumes a number field is already an int or forgets to gunzip the logs payload before parsing it. 

The library should handle the three main pain points we keep hitting: (1) those typed attribute wrapper objects from the document store — you know the ones with the single-key envelope format we discussed in the infra sync — (2) the timestamp fields that sometimes come in as seconds and sometimes as millis depending on which service is sending, and (3) the compressed log batch field in CloudWatch delivery events. 

For the timestamp stuff, refer to how we handled the precision-sensitive round-trip in the billing module — same idea here but we need both directions. Wrong-type access should blow up loudly, not silently coerce. 

Also need a test runner script that can point at different case directories so QA can swap in their own fixtures without touching the harness itself. Output files should be namespaced so parallel runs don't stomp each other. Single stdin-to-stdout adapter for the test interface, core logic fully separated.

One extra pass on the details the team asked about: for map entries, type M needs to come back with keys sorted in ascending lexicographic order every time. So if a map has keys 'Name' and 'Age', the output should put the 'Age' entry before the 'Name' entry. Same rule applies not just in the top-level full decode output, but also when a map shows up inside a list or nested under another map.

On the number conversion edge case, for the 'dynamodb_number' action when the 'as' field is 'integer', if the decimal string has a fractional part then parse it as a floating-point number first and truncate toward zero, not floor it. So -123.9 becomes -123, not -124.

Also, for wrong-type access, this should be very strict and very plain. A type-mismatch error must produce exactly three lines: 'error=incompatible_type', then 'requested=<RequestedTypeName>', then 'actual=<ActualTypeName>'. The names there should be the logical type names, so String, Number, Binary, Boolean, Null, StringSet, NumberSet, BinarySet, List, Map, and not host-language class names. The action that triggers this is 'dynamodb_access' with a mismatched 'as' field.

For the epoch encoders, when doing 'epoch_seconds_encode' the output line is 'epoch=<value>' and it should keep only the fractional digits actually needed for sub-second precision. Example: 476 milliseconds should come out as 'epoch=1480641523.476'. If there is no sub-second part, then it should just be a plain integer representation. For 'epoch_millis_encode', the output line is also 'epoch=<value>' but in that case it needs to be a whole integer count of milliseconds with no decimal point. Example: '2016-12-02T01:18:43.476Z' yields 'epoch=1480641523476'.

And just to make the DynamoDB side fully explicit, the attribute value wire format here is a JSON object with exactly one key that names the logical type (S, N, BOOL, B, NULL, SS, NS, BS, L, M) and whose value is the encoded payload, as specified in Feature 1 of start.md and tested in feature1_1_decode_attribute_value.json.