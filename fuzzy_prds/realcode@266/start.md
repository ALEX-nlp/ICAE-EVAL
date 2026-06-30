## Product Requirement Document

Hey team, we need a codec utility library for our Lambda event pipeline. Basically our consumers are drowning in boilerplate every time they try to read a DynamoDB stream record or process a CloudWatch Logs subscription — everyone's hand-rolling the same conversions differently and we keep getting weird silent bugs when someone assumes a number field is already an int or forgets to gunzip the logs payload before parsing it. 

The library should handle the three main pain points we keep hitting: (1) those typed attribute wrapper objects from the document store — you know the ones with the single-key envelope format we discussed in the infra sync — (2) the timestamp fields that sometimes come in as seconds and sometimes as millis depending on which service is sending, and (3) the compressed log batch field in CloudWatch delivery events. 

For the timestamp stuff, refer to how we handled the precision-sensitive round-trip in the billing module — same idea here but we need both directions. Wrong-type access should blow up loudly, not silently coerce. 

Also need a test runner script that can point at different case directories so QA can swap in their own fixtures without touching the harness itself. Output files should be namespaced so parallel runs don't stomp each other. Single stdin-to-stdout adapter for the test interface, core logic fully separated.