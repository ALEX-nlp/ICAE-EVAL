## Product Requirement Document

# Clickstream Event Collection, Mapping & Sink Engine

## Project Goal

Build the server-side core of a clickstream data-collection platform. The system
receives raw browser/web events over HTTP, turns each event into a strongly typed
structured record according to a declarative mapping, and durably writes batches of
those records to a file-based sink for downstream analytics.

The engine must be deterministic, schema-driven, and configurable at runtime through
a hierarchical configuration document, without code changes. It is composed of four
cooperating capabilities:

1. A compact, self-verifying **identity token** codec used to label visitors,
   sessions, and page views.
2. A small **optional-configuration** access layer that reads typed values from a
   hierarchical configuration document and degrades gracefully when values are
   absent.
3. A **record mapper** that transforms an incoming HTTP event into a typed record
   using a declarative field-mapping configuration (flat copies, user-agent
   parsing, regular-expression extraction, query-string/path/cookie extraction,
   type casting, custom event parameters, and optional geo-IP enrichment).
4. A **file sink** that buffers records into files using pluggable rolling
   strategies (time-based rolling and session-window binning), publishing finished
   files atomically and keeping unfinished files in-flight.

## Background & Problem

A clickstream collector sits on the hot path of a website: every page view and
custom event becomes an HTTP request. To be useful for analytics, those requests
must be normalized into a uniform, typed schema and stored efficiently. Several
recurring problems must be solved together:

- **Stable identities.** Visitors and sessions need opaque identifiers that are
  globally unique, carry their creation time so windows can be derived, and survive
  a round trip (serialize → store in a cookie → read back) without loss.
- **Configuration that may be incomplete.** Operators describe mappings and runtime
  options in a configuration document. Lookups for optional settings must not crash
  the server; they must report presence/absence and support fallbacks, required
  semantics, filtering, and transformation.
- **Declarative, type-safe mapping.** The shape of the output record is fixed by a
  schema; the mapping from HTTP signals to record fields is data-driven. Values
  arrive as strings and must be coerced to the schema's types, falling back to
  schema defaults when coercion fails or a source value is missing. Invalid mapping
  configurations must be rejected early with clear diagnostics.
- **Durable, windowed output.** Records must be written to files that can be safely
  published only once complete. Two strategies are required: rolling files on a time
  interval, and binning events into per-session-window files (where an event sticks
  to the window in which its session began, as long as that window is still open).

## Architecture & Engineering Constraints

### Component boundaries

- **Identity token codec** — encodes a millisecond timestamp plus random bits into a
  fixed-width, opaque, hex-like string; decodes it back to recover the timestamp;
  defines value-based equality.
- **Optional configuration accessor** — wraps a typed read against a hierarchical
  configuration document; an unreadable/absent path yields an "absent" result
  instead of throwing; supports value, fallback (eager and lazy), required,
  predicate-filter, and transform operations.
- **Record mapper** — validated against the output schema at construction time;
  produces one typed record per HTTP event from a declarative mapping.
- **File sink** — accepts a stream of encoded records and routes them to files via a
  configurable strategy; finished files are published to an output area, unfinished
  files remain in a working area with a distinct in-flight suffix.

### Engineering constraints

- **Deterministic contract.** All observable behavior is exposed as plain
  `key=value` lines (one per line, in a fixed order). Collections render as
  `[a, b, c]`; absent values render as `null`.
- **Schema-driven typing.** Output field types come from the record schema; string
  inputs are cast to integer/long/double/boolean as required, and a failed cast or
  missing source falls back to the schema's declared default for that field.
- **Fail-fast validation.** A mapping configuration with an unsupported version, a
  mapped field that does not exist in the schema, or a cookie/event-parameter
  mapping that omits its required name is rejected when the mapper is built. Errors
  are surfaced as neutral, categorized codes (not host-language exceptions).
- **Atomic publication.** A file is only readable once finalized; an in-flight file
  is not yet a valid container and must not be treated as durable.
- **Window semantics for binning.** Session windows are fixed-width; an event is
  filed under the window in which its session started if that window's file is still
  open, otherwise it moves to the current window's file. On a clean shutdown,
  in-flight binning files are finalized in place but not published.

### Execution adapter contract (for the test harness)

A thin adapter reads exactly **one JSON command object** from standard input,
performs the requested operation against the engine, and writes the rendered
`key=value` contract to standard output. The command's `op` field selects the
operation; remaining fields are operation-specific inputs. This is the interface the
hidden and public test cases drive.

## Core Features

### Feature 1: Identity token codec

Opaque, time-bearing, unique identifiers with value equality.

#### Feature 1.1: Encode/decode round-trip

A timestamp encoded into a token is recovered exactly on decode, and the token has a
fixed width regardless of the timestamp.

```json
{
  "description": "Identity token codec: a timestamp encoded into an opaque fixed-width token is recovered intact on decode.",
  "cases": [
    {
      "input": { "op": "token_encode_decode", "timestamp": 42 },
      "expected_output": "timestamp=42\nlength=32\n"
    }
  ]
}
```

#### Feature 1.2: Value equality and hashing

A decoded token equals the original it was parsed from (and shares its hash); an
independently generated token for the same timestamp is not equal (random bits
differ).

```json
{
  "description": "Token value equality: a decoded token equals its original (same value and hash); an independently generated token for the same timestamp does not.",
  "cases": [
    {
      "input": { "op": "token_identity", "timestamp": 42 },
      "expected_output": "reparsed_equals=true\nhashcode_equals=true\nindependent_equals=false\n"
    }
  ]
}
```

#### Feature 1.3: Uniqueness at scale

A large batch of freshly generated tokens contains no collisions.

```json
{
  "description": "Token uniqueness: a large batch of freshly generated tokens are all distinct.",
  "cases": [
    {
      "input": { "op": "token_unique", "count": 100000 },
      "expected_output": "generated=100000\ndistinct=100000\n"
    }
  ]
}
```

### Feature 2: Optional configuration access

Typed, null-safe access to a hierarchical configuration document.

#### Feature 2.1: Presence lookup

A present typed value reports `present` with its rendered value; an absent path
reports `absent` instead of raising.

```json
{
  "description": "Optional config lookup: present typed values report present with their value; an absent path reports absent rather than raising.",
  "cases": [
    {
      "input": { "op": "config_presence", "config": { "some": { "existing": { "str": "Existing", "int": 42, "bool": true, "arr": ["val1", "val2"] } } }, "type": "string", "path": "some.existing.str" },
      "expected_output": "state=present\nvalue=Existing\n"
    },
    {
      "input": { "op": "config_presence", "config": { "some": { "existing": { "str": "Existing", "int": 42, "bool": true, "arr": ["val1", "val2"] } } }, "type": "string", "path": "some.nonexisting.str" },
      "expected_output": "state=absent\n"
    }
  ]
}
```

#### Feature 2.2: Fallback values

A present value is returned as-is; an absent path yields the supplied fallback,
whether resolved eagerly or lazily.

```json
{
  "description": "Optional config with fallback: a present value is returned; an absent path yields the supplied fallback, whether resolved eagerly or lazily.",
  "cases": [
    {
      "input": { "op": "config_fallback", "config": { "some": { "existing": { "str": "Existing", "int": 42, "bool": true, "arr": ["val1", "val2"] } } }, "type": "string", "path": "some.existing.str", "fallback": "theOtherOne" },
      "expected_output": "value=Existing\n"
    },
    {
      "input": { "op": "config_fallback", "config": { "some": { "existing": { "str": "Existing", "int": 42, "bool": true, "arr": ["val1", "val2"] } } }, "type": "string", "path": "some.nonexisting.str", "fallback": "theOtherOne" },
      "expected_output": "value=theOtherOne\n"
    }
  ]
}
```

#### Feature 2.3: Required values

A present value is returned; an absent path surfaces a neutral missing-value error.

```json
{
  "description": "Optional config required: a present value is returned; an absent path surfaces a neutral missing-value error.",
  "cases": [
    {
      "input": { "op": "config_required", "config": { "some": { "existing": { "str": "Existing", "int": 42, "bool": true, "arr": ["val1", "val2"] } } }, "type": "string", "path": "some.existing.str" },
      "expected_output": "value=Existing\n"
    },
    {
      "input": { "op": "config_required", "config": { "some": { "existing": { "str": "Existing", "int": 42, "bool": true, "arr": ["val1", "val2"] } } }, "type": "string", "path": "some.nonexisting.str" },
      "expected_output": "error=absent_value\n"
    }
  ]
}
```

#### Feature 2.4: Predicate filtering

A present list that satisfies the predicate stays present; one that fails the
predicate, or an absent path, becomes absent.

```json
{
  "description": "Optional config filtering: a present list that satisfies the predicate stays present; one that fails the predicate or is absent becomes absent.",
  "cases": [
    {
      "input": { "op": "config_filter", "config": { "some": { "existing": { "str": "Existing", "int": 42, "bool": true, "arr": ["val1", "val2"] } } }, "path": "some.existing.arr", "contains": "val1" },
      "expected_output": "state=present\nsize=2\nitems=val1,val2\n"
    },
    {
      "input": { "op": "config_filter", "config": { "some": { "existing": { "str": "Existing", "int": 42, "bool": true, "arr": ["val1", "val2"] } } }, "path": "some.existing.arr", "contains": "missing" },
      "expected_output": "state=absent\n"
    }
  ]
}
```

#### Feature 2.5: Value transformation

A present value is mapped through a function (here, string length); an absent path
stays absent without applying the function.

```json
{
  "description": "Optional config transformation: a present value is mapped through a function (here string length); an absent path stays absent without applying the function.",
  "cases": [
    {
      "input": { "op": "config_map", "config": { "some": { "existing": { "str": "Existing", "int": 42, "bool": true, "arr": ["val1", "val2"] } } }, "path": "some.existing.str" },
      "expected_output": "state=present\nvalue=8\n"
    },
    {
      "input": { "op": "config_map", "config": { "some": { "existing": { "str": "Existing", "int": 42, "bool": true, "arr": ["val1", "val2"] } } }, "path": "some.nonexisting.str" },
      "expected_output": "state=absent\n"
    }
  ]
}
```

### Feature 3: HTTP event → typed record mapping

A declarative mapper that builds one typed record per HTTP event. For every mapping
case the request carries a default cookie header
(`[the default session cookie payload used by the mapper when no headers are found]`) and
fixed identity tokens, so derived fields are deterministic.

#### Feature 3.1: Standard field copies

Simple request signals (location, referer, user agent, viewport, event type) and the
request's identity tokens are copied into the record, together with the derived
session-start flag and the event timestamp.

```json
{
  "description": "Event mapping of standard fields: simple request signals (location, referer, user agent, viewport, event type) and the request's identity tokens are copied into the record, with the derived session-start flag and event timestamp.",
  "cases": [
    {
      "input": { "op": "map_event", "scenario": "flat_fields", "page_view_id": "the_page_view_id", "location": "https://example.com/", "referer": "http://example.com/", "screen_width": "1024", "screen_height": "768", "viewport_width": "640", "viewport_height": "480", "event_type": "pageView", "fields": ["sessionStart", "ts", "location", "referer", "userAgentString", "eventType", "viewportWidth", "viewportHeight", "client", "session", "pageview"] },
      "expected_output": "sessionStart=true\nts=42\nlocation=https://example.com/\nreferer=http://example.com/\nuserAgentString=Divolte/Test\neventType=pageView\nviewportWidth=640\nviewportHeight=480\n[explicit hardcoded hex strings generated from the input identity tokens]\n[explicit hardcoded hex strings generated from the input identity tokens]\n[explicit hardcoded hex strings generated from the input identity tokens]\n"
    }
  ]
}
```

#### Feature 3.2: User-agent parsing

The raw user-agent header is decomposed into browser, vendor, type, version, device
category, and operating-system attributes.

```json
{
  "description": "User-agent parsing: the raw user-agent header is decomposed into browser, vendor, type, version, device category and operating-system attributes.",
  "cases": [
    {
      "input": { "op": "map_event", "scenario": "user_agent", "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36", "fields": ["userAgentName", "userAgentFamily", "userAgentVendor", "userAgentType", "userAgentVersion", "userAgentDeviceCategory", "userAgentOsFamily", "userAgentOsVersion", "userAgentOsVendor"] },
      "expected_output": "[direct mappings from the parsed Chrome User Agent string]\nuserAgentFamily=Chrome\n[direct mappings from the parsed Chrome User Agent string]\nuserAgentType=Browser\nuserAgentVersion=36.0.1985.125\nuserAgentDeviceCategory=Personal computer\n[direct mappings from the parsed Chrome User Agent string]\nuserAgentOsVersion=10.9.4\nuserAgentOsVendor=Apple Computer, Inc.\n"
    }
  ]
}
```

#### Feature 3.3: Regular-expression named mapping

A field is populated by the named capture of a regular expression applied to a
request signal (here, the URL protocol of the location and referer).

```json
{
  "description": "Regex named-mapping: a field is populated by the named capture of a regular expression applied to a request signal (here the URL protocol of location and referer).",
  "cases": [
    {
      "input": { "op": "map_event", "scenario": "regex_match", "location": "http://example.com/", "referer": "https://www.example.com/bla/", "fields": ["locationProtocol", "refererProtocol"] },
      "expected_output": "locationProtocol=http\nrefererProtocol=https\n"
    }
  ]
}
```

#### Feature 3.4: Regular-expression capture groups

Multiple fields are populated from positional capture groups of regular expressions
applied to the location and referer.

```json
{
  "description": "Regex capture-group mapping: multiple fields are populated from positional capture groups of regular expressions applied to the location and referer.",
  "cases": [
    {
      "input": { "op": "map_event", "scenario": "regex_capture", "location": "http://example.com/part1/part2/part3/ABA_C12_X3B", "referer": "https://www.example.com/about.html", "fields": ["toplevelCategory", "subCategory", "contentPage"] },
      "expected_output": "toplevelCategory=ABA\nsubCategory=C12\ncontentPage=about\n"
    }
  ]
}
```

#### Feature 3.5: Query-string parameter mapping

A field is set from a named parameter of the location URL; when the parameter is
absent the schema default is used.

```json
{
  "description": "Query-string parameter mapping: a field is set from a named parameter of the location URL; when the parameter is absent the schema default is used.",
  "cases": [
    {
      "input": { "op": "map_event", "scenario": "query_param", "location": "http://ci-website-elb-1121474138.eu-west-1.elb.amazonaws.com/search?q=fiets+lamp+rood", "referer": "https://www.example.com/about.html", "fields": ["queryparam"] },
      "expected_output": "queryparam=fiets lamp rood\n"
    },
    {
      "input": { "op": "map_event", "scenario": "query_param", "location": "http://ci-website-elb-1121474138.eu-west-1.elb.amazonaws.com/search?other=wrong+param+name", "referer": "https://www.example.com/about.html", "fields": ["queryparam"] },
      "expected_output": "queryparam=not set\n"
    }
  ]
}
```

#### Feature 3.6: Type casting with default fallback

String signals from query, URL path, and cookie are cast to the schema's integer,
boolean, double, and long types; a value that cannot be parsed falls back to the
schema default.

```json
{
  "description": "Type casting of mapped values: string-typed signals from query, URL path and cookie are cast to the schema's integer, boolean, double and long types; a value that cannot be parsed falls back to the schema default.",
  "cases": [
    {
      "input": { "op": "map_event", "scenario": "type_cast", "location": "http://example.com/42/false/3.14159265359/34359738368/whatever?i=-42&b=true&d=3.14159265359&l=34359738368", "referer": "https://www.example.com/about.html", "fields": ["queryparamInteger", "queryparamBoolean", "queryparamDouble", "queryparamLong", "pathInteger", "pathBoolean", "pathDouble", "pathLong", "cookieInteger", "cookieBoolean"] },
      "expected_output": "queryparamInteger=-42\nqueryparamBoolean=true\nqueryparamDouble=3.14159265359\nqueryparamLong=34359738368\npathInteger=42\npathBoolean=false\npathDouble=3.14159265359\npathLong=34359738368\ncookieInteger=42\ncookieBoolean=true\n"
    },
    {
      "input": { "op": "map_event", "scenario": "type_cast", "location": "http://example.com/NotAnInt/false/3.14159265359/34359738368/whatever?i=-42&b=true&d=3.14159265359&l=34359738368", "referer": "https://www.example.com/about.html", "fields": ["pathInteger"] },
      "expected_output": "pathInteger=-1\n"
    }
  ]
}
```

#### Feature 3.7: Custom cookie mapping

A field is populated from the value of a named request cookie.

```json
{
  "description": "Custom cookie mapping: a field is populated from the value of a named request cookie.",
  "cases": [
    {
      "input": { "op": "map_event", "scenario": "custom_cookie", "fields": ["customCookie"] },
      "expected_output": "customCookie=custom_cookie_value\n"
    }
  ]
}
```

#### Feature 3.8: Custom event-parameter mapping

A field is populated from a named custom event parameter carried on the request,
preserving punctuation in the value.

```json
{
  "description": "Custom event-parameter mapping: a field is populated from a named custom event parameter carried on the request, preserving punctuation in the value.",
  "cases": [
    {
      "input": { "op": "map_event", "scenario": "custom_event_param", "event_params": { "abba": "Honey, Honey" }, "fields": ["customEventParameter"] },
      "expected_output": "customEventParameter=Honey, Honey\n"
    }
  ]
}
```

#### Feature 3.9: Geo-IP enrichment

When a geo lookup yields a full result every geo field is populated; an empty lookup
result yields neutral defaults (false booleans, empty lists, null scalars); no lookup
result leaves every geo field null.

```json
{
  "description": "Geo-IP enrichment: when a geo lookup yields a full result every geo field is populated; an empty result yields neutral defaults (false booleans, empty lists, null scalars); no lookup result leaves every geo field null.",
  "cases": [
    {
      "input": { "op": "map_event", "scenario": "geo", "geo": "with-everything", "user_agent": "Arbitrary User Agent", "fields": ["geoCityId", "geoCityName", "geoContinentCode", "geoContinentId", "geoContinentName", "geoCountryCode", "geoCountryId", "geoCountryName", "geoLatitude", "geoLongitude", "geoMetroCode", "geoTimeZone", "geoMostSpecificSubdivisionCode", "geoMostSpecificSubdivisionId", "geoMostSpecificSubdivisionName", "geoPostalCode", "geoRegisteredCountryCode", "geoRegisteredCountryId", "geoRegisteredCountryName", "geoRepresentedCountryCode", "geoRepresentedCountryId", "geoRepresentedCountryName", "geoAutonomousSystemNumber", "geoAutonomousSystemOrganization", "geoDomain", "geoIsp", "geoOrganisation", "geoAnonymousProxy", "geoSatelliteProvider", "geoSubdivisionCodes", "geoSubdivisionIds", "geoSubdivisionNames"] },
      "expected_output": "geoCityId=2758064\ngeoCityName=Bussum\ngeoContinentCode=EU\ngeoContinentId=6255148\ngeoContinentName=Europe\ngeoCountryCode=NL\ngeoCountryId=2750405\ngeoCountryName=Netherlands\ngeoLatitude=52.27333\ngeoLongitude=5.16111\ngeoMetroCode=37331\ngeoTimeZone=Europe/Amsterdam\ngeoMostSpecificSubdivisionCode=YC\ngeoMostSpecificSubdivisionId=2333\ngeoMostSpecificSubdivisionName=Subdivision2\ngeoPostalCode=1403RM\ngeoRegisteredCountryCode=AB\ngeoRegisteredCountryId=12\ngeoRegisteredCountryName=Name1\ngeoRepresentedCountryCode=CD\ngeoRepresentedCountryId=14\ngeoRepresentedCountryName=Name2\ngeoAutonomousSystemNumber=42\ngeoAutonomousSystemOrganization=Level Communications\ngeoDomain=divolte.io\ngeoIsp=An ISP\ngeoOrganisation=The Organization\ngeoAnonymousProxy=true\ngeoSatelliteProvider=false\ngeoSubdivisionCodes=[WN, YC]\ngeoSubdivisionIds=[2331, 2333]\ngeoSubdivisionNames=[Subdivision1, Subdivision2]\n"
    },
    {
      "input": { "op": "map_event", "scenario": "geo", "geo": "none", "user_agent": "Arbitrary User Agent", "fields": ["geoCityId", "geoCityName", "geoContinentCode", "geoContinentId", "geoContinentName", "geoCountryCode", "geoCountryId", "geoCountryName", "geoLatitude", "geoLongitude", "geoMetroCode", "geoTimeZone", "geoMostSpecificSubdivisionCode", "geoMostSpecificSubdivisionId", "geoMostSpecificSubdivisionName", "geoPostalCode", "geoRegisteredCountryCode", "geoRegisteredCountryId", "geoRegisteredCountryName", "geoRepresentedCountryCode", "geoRepresentedCountryId", "geoRepresentedCountryName", "geoAutonomousSystemNumber", "geoAutonomousSystemOrganization", "geoDomain", "geoIsp", "geoOrganisation", "geoAnonymousProxy", "geoSatelliteProvider", "geoSubdivisionCodes", "geoSubdivisionIds", "geoSubdivisionNames"] },
      "expected_output": "geoCityId=null\ngeoCityName=null\ngeoContinentCode=null\ngeoContinentId=null\ngeoContinentName=null\ngeoCountryCode=null\ngeoCountryId=null\ngeoCountryName=null\ngeoLatitude=null\ngeoLongitude=null\ngeoMetroCode=null\ngeoTimeZone=null\ngeoMostSpecificSubdivisionCode=null\ngeoMostSpecificSubdivisionId=null\ngeoMostSpecificSubdivisionName=null\ngeoPostalCode=null\ngeoRegisteredCountryCode=null\ngeoRegisteredCountryId=null\ngeoRegisteredCountryName=null\ngeoRepresentedCountryCode=null\ngeoRepresentedCountryId=null\ngeoRepresentedCountryName=null\ngeoAutonomousSystemNumber=null\ngeoAutonomousSystemOrganization=null\ngeoDomain=null\ngeoIsp=null\ngeoOrganisation=null\ngeoAnonymousProxy=null\ngeoSatelliteProvider=null\ngeoSubdivisionCodes=null\ngeoSubdivisionIds=null\ngeoSubdivisionNames=null\n"
    }
  ]
}
```

#### Feature 3.10: Mapping configuration validation

An unsupported mapping version, a mapped field missing from the schema, a cookie
mapping without a name, and an event-parameter mapping without a name are each
rejected at construction with a descriptive, categorized error.

```json
{
  "description": "Mapping configuration validation: an unsupported mapping version, a mapped field missing from the schema, a cookie mapping without a name, and an event-parameter mapping without a name are each rejected at construction with a descriptive, categorized error.",
  "cases": [
    {
      "input": { "op": "map_event", "scenario": "unsupported_version", "fields": [] },
      "expected_output": "error=unsupported_mapping_version\nversion=42\n"
    },
    {
      "input": { "op": "map_event", "scenario": "missing_field", "fields": [] },
      "expected_output": "error=missing_schema_field\nfield=fieldThatIsMissingFromSchema\n"
    }
  ]
}
```

### Feature 4: File sink strategies

Buffer records into files; publish completed files, keep unfinished files in-flight.
Output reports the number of published and in-flight files and, per file, the event
timestamps it contains (in file order). A `.avro` suffix denotes a published file;
a `.avro.partial` suffix denotes an in-flight file. An in-flight file that has not
been finalized is reported as `<unreadable>` because it is not yet a valid container.

#### Feature 4.1: Time-based rolling

Records accumulate in a single in-flight file that is published on clean shutdown;
an in-flight file left unfinalized is not yet readable; forcing rolls between
batches publishes one file per interval.

```json
{
  "description": "Rolling file sink: records written under a time-based rolling strategy accumulate in a single in-flight file, published on clean shutdown; an in-flight file that has not been finalized is not yet a readable container; forcing rolls between batches publishes one file per interval.",
  "cases": [
    {
      "input": { "op": "sink", "strategy": "simple", "roll_every": "1 day", "records": [{ "ts": 0 }, { "ts": 1 }, { "ts": 2 }, { "ts": 3 }, { "ts": 4 }, { "ts": 5 }, { "ts": 6 }, { "ts": 7 }, { "ts": 8 }, { "ts": 9 }] },
      "expected_output": "published_files=1\ninflight_files=0\npublished[0]=.avro|0,1,2,3,4,5,6,7,8,9\n"
    },
    {
      "input": { "op": "sink", "strategy": "simple", "roll_every": "1 day", "cleanup": false, "records": [{ "ts": 0 }, { "ts": 1 }, { "ts": 2 }] },
      "expected_output": "published_files=0\ninflight_files=1\ninflight[0]=.avro.partial|<unreadable>\n"
    },
    {
      "input": { "op": "sink", "strategy": "simple", "roll_every": "1 second", "records": [{ "ts": 0 }, { "ts": 1 }], "rolls": 2, "records2": [{ "ts": 2 }, { "ts": 3 }] },
      "expected_output": "published_files=2\ninflight_files=0\npublished[0]=.avro|0,1\npublished[1]=.avro|2,3\n"
    }
  ]
}
```

#### Feature 4.2: Session-window binning

Events are routed to per-session-window files. Events from distinct windows land in
separate files; an event whose session opened in an earlier window sticks to that
window's file while it is still open; once a window is no longer current a later
event opens the next window's file; a lone event yields a single in-flight file.

```json
{
  "description": "Session-binning file sink: events are routed to per-session-window files. Events from distinct windows land in separate files; an event whose session opened in an earlier window sticks to that window's file; once a window is no longer current a later event opens the next window's file; a lone event yields a single in-flight file.",
  "cases": [
    {
      "input": { "op": "sink", "strategy": "binning", "records": [{ "ts": 100 }, { "ts": 1100 }, { "ts": 2100 }, { "ts": 3100 }, { "ts": 4100 }] },
      "expected_output": "published_files=2\ninflight_files=3\npublished[0]=.avro|100\npublished[1]=.avro|1100\ninflight[0]=.avro.partial|2100\ninflight[1]=.avro.partial|3100\ninflight[2]=.avro.partial|4100\n"
    },
    {
      "input": { "op": "sink", "strategy": "binning", "records": [{ "ts": 100, "session_start": 100 }, { "ts": 1100, "session_start": 1100 }, { "ts": 2100, "session_start": 2100 }, { "ts": 3100, "session_start": 3100 }, { "ts": 3150, "session_start": 100 }, { "ts": 3160, "session_start": 1100 }, { "ts": 3170, "session_start": 2100 }, { "ts": 3180, "session_start": 3100 }] },
      "expected_output": "published_files=1\ninflight_files=3\npublished[0]=.avro|100\ninflight[0]=.avro.partial|1100,3150,3160\ninflight[1]=.avro.partial|2100,3170\ninflight[2]=.avro.partial|3100,3180\n"
    }
  ]
}
```

## Deliverables

- An **identity token codec** providing encode/decode round-trip, value equality and
  hashing, and uniqueness at scale (Feature 1).
- An **optional configuration accessor** over a hierarchical configuration document,
  supporting presence, fallback (eager and lazy), required, predicate-filter, and
  transform operations (Feature 2).
- A **declarative record mapper** that turns an HTTP event into a typed record:
  standard field copies, user-agent parsing, regex named/group extraction,
  query/path/cookie extraction with type casting and schema defaults, custom event
  parameters, geo-IP enrichment, and fail-fast mapping-configuration validation
  (Feature 3).
- A **file sink** with pluggable strategies — time-based rolling and session-window
  binning — that publishes completed files atomically and keeps unfinished files
  in-flight (Feature 4).
- A **single test entry point** (`rcb_tests/test.sh`) that builds the engine, runs
  every JSON case in a chosen directory through the execution adapter, captures raw
  program stdout, and compares it to each case's expected output. It supports
  `--cases-dir <subdir>` (default `test_cases`) and writes captured stdout to
  `rcb_tests/stdout/<subdir>/<stem>@<NNN>.txt`.
- A hidden evaluation set under `rcb_tests/test_cases/` and a public mirror under
  `rcb_tests/public_test_cases/`, one JSON file per leaf feature.

### Acceptance

Running `bash rcb_tests/test.sh --cases-dir test_cases` must report `0` failures
against the engine, and likewise for `--cases-dir public_test_cases`.


---
**Implementation notes:**
- verify the provider supports this specific mapping version
- inspect the partial file name and timestamp
