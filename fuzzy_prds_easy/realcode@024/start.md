## Product Requirement Document

# XML Property-List Conversion Library - Parse and Emit Typed Property-List Data

## Project Goal

Build a property-list conversion library that allows developers to parse XML property-list documents into typed application values and serialize application values back to XML property-list output without manually traversing XML nodes or constructing tags.

---

## Background & Problem

Without this library/tool, developers are forced to hand-write XML parsing and XML generation logic for property-list files, including nested arrays, dictionaries, scalar types, dates, escaped text, and binary data. This leads to repetitive code, fragile formatting, inconsistent type handling, and hard-to-maintain adapters around configuration or metadata files.

With this library/tool, developers can provide XML property-list input or ordinary application values and receive deterministic parsed reports or XML property-list output through a small execution adapter, while the core conversion logic remains independent of standard input and output.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: XML Property-List Parsing

**As a developer**, I want to parse XML property-list input into typed observable values, so I can inspect configuration or metadata files without writing a custom XML walker.

**Expected Behavior / Usage:**

This feature area covers the externally observable behavior for xml property-list parsing. Each leaf sub-feature below is independently testable through one JSON case file and emits only raw stdout in the format shown.

*1.1 Structured XML Values — Parse a complete XML property-list document containing nested dictionaries, arrays, strings, integers, and booleans.*

Parse a complete XML property-list document containing nested dictionaries, arrays, strings, integers, and booleans. The adapter input supplies an XML document and requests an overview report; stdout lists the top-level keys, selected nested fields, and scalar values in deterministic key=value lines so callers can verify the parsed structure and values.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_parse_structured_xml_values.json`

```json
{
    "description": "Parse XML property-list documents into observable scalar, array, and object values while preserving nested field values and boolean values.",
    "cases": [
        {
            "input": {
                "operation": "parse_report",
                "report": "album_library_overview",
                "xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n<plist version=\"1.0\">\n<dict>\n\t<key>Application Version</key>\n\t<string>5.0.4 (263)</string>\n\t<key>Archive Path</key>\n\t<string>/Users/username/Pictures/iPhoto Library</string>\n\t<key>List of Albums</key>\n\t<array>\n\t\t<dict>\n\t\t\t<key>AlbumId</key>\n\t\t\t<integer>999000</integer>\n\t\t\t<key>AlbumName</key>\n\t\t\t<string>Library</string>\n\t\t\t<key>KeyList</key>\n\t\t\t<array>\n\t\t\t\t<string>7</string>\n\t\t\t</array>\n\t\t\t<key>Master</key>\n\t\t\t<true/>\n\t\t\t<key>PhotoCount</key>\n\t\t\t<integer>1</integer>\n\t\t\t<key>PlayMusic</key>\n\t\t\t<string>YES</string>\n\t\t\t<key>RepeatSlideShow</key>\n\t\t\t<string>YES</string>\n\t\t\t<key>SecondsPerSlide</key>\n\t\t\t<integer>3</integer>\n\t\t\t<key>SlideShowUseTitles</key>\n\t\t\t<false/>\n\t\t\t<key>SongPath</key>\n\t\t\t<string></string>\n\t\t\t<key>TransitionDirection</key>\n\t\t\t<integer>0</integer>\n\t\t\t<key>TransitionName</key>\n\t\t\t<string>Dissolve</string>\n\t\t\t<key>TransitionSpeed</key>\n\t\t\t<real>1</real>\n\t\t</dict>\n\t\t<dict>\n\t\t\t<key>Album Type</key>\n\t\t\t<string>Special Roll</string>\n\t\t\t<key>AlbumId</key>\n\t\t\t<integer>999001</integer>\n\t\t\t<key>AlbumName</key>\n\t\t\t<string>Last Roll</string>\n\t\t\t<key>Filter Mode</key>\n\t\t\t<string>All</string>\n\t\t\t<key>Filters</key>\n\t\t\t<array>\n\t\t\t\t<dict>\n\t\t\t\t\t<key>Count</key>\n\t\t\t\t\t<integer>1</integer>\n\t\t\t\t\t<key>Operation</key>\n\t\t\t\t\t<string>In Last</string>\n\t\t\t\t\t<key>Type</key>\n\t\t\t\t\t<string>Roll</string>\n\t\t\t\t</dict>\n\t\t\t</array>\n\t\t\t<key>KeyList</key>\n\t\t\t<array>\n\t\t\t\t<string>7</string>\n\t\t\t</array>\n\t\t\t<key>PhotoCount</key>\n\t\t\t<integer>1</integer>\n\t\t\t<key>PlayMusic</key>\n\t\t\t<string>YES</string>\n\t\t\t<key>RepeatSlideShow</key>\n\t\t\t<string>YES</string>\n\t\t\t<key>SecondsPerSlide</key>\n\t\t\t<integer>3</integer>\n\t\t\t<key>SlideShowUseTitles</key>\n\t\t\t<false/>\n\t\t\t<key>SongPath</key>\n\t\t\t<string></string>\n\t\t\t<key>TransitionDirection</key>\n\t\t\t<integer>0</integer>\n\t\t\t<key>TransitionName</key>\n\t\t\t<string>Dissolve</string>\n\t\t\t<key>TransitionSpeed</key>\n\t\t\t<real>1</real>\n\t\t</dict>\n\t\t<dict>\n\t\t\t<key>Album Type</key>\n\t\t\t<string>Special Month</string>\n\t\t\t<key>AlbumId</key>\n\t\t\t<integer>999002</integer>\n\t\t\t<key>AlbumName</key>\n\t\t\t<string>Last 12 Months</string>\n\t\t\t<key>Filter Mode</key>\n\t\t\t<string>All</string>\n\t\t\t<key>Filters</key>\n\t\t\t<array/>\n\t\t\t<key>KeyList</key>\n\t\t\t<array>\n\t\t\t\t<string>7</string>\n\t\t\t</array>\n\t\t\t<key>PhotoCount</key>\n\t\t\t<integer>1</integer>\n\t\t\t<key>PlayMusic</key>\n\t\t\t<string>YES</string>\n\t\t\t<key>RepeatSlideShow</key>\n\t\t\t<string>YES</string>\n\t\t\t<key>SecondsPerSlide</key>\n\t\t\t<integer>3</integer>\n\t\t\t<key>SlideShowUseTitles</key>\n\t\t\t<false/>\n\t\t\t<key>SongPath</key>\n\t\t\t<string></string>\n\t\t\t<key>TransitionDirection</key>\n\t\t\t<integer>0</integer>\n\t\t\t<key>TransitionName</key>\n\t\t\t<string>Dissolve</string>\n\t\t\t<key>TransitionSpeed</key>\n\t\t\t<real>1</real>\n\t\t</dict>\n\t\t<dict>\n\t\t\t<key>Album Type</key>\n\t\t\t<string>Regular</string>\n\t\t\t<key>AlbumId</key>\n\t\t\t<integer>9</integer>\n\t\t\t<key>AlbumName</key>\n\t\t\t<string>An Album</string>\n\t\t\t<key>KeyList</key>\n\t\t\t<array>\n\t\t\t\t<string>7</string>\n\t\t\t</array>\n\t\t\t<key>PhotoCount</key>\n\t\t\t<integer>1</integer>\n\t\t\t<key>PlayMusic</key>\n\t\t\t<string>YES</string>\n\t\t\t<key>RepeatSlideShow</key>\n\t\t\t<string>YES</string>\n\t\t\t<key>SecondsPerSlide</key>\n\t\t\t<integer>3</integer>\n\t\t\t<key>SlideShowUseTitles</key>\n\t\t\t<false/>\n\t\t\t<key>SongPath</key>\n\t\t\t<string></string>\n\t\t\t<key>TransitionDirection</key>\n\t\t\t<integer>0</integer>\n\t\t\t<key>TransitionName</key>\n\t\t\t<string>Dissolve</string>\n\t\t\t<key>TransitionSpeed</key>\n\t\t\t<real>1</real>\n\t\t</dict>\n\t</array>\n\t<key>List of Keywords</key>\n\t<dict/>\n\t<key>List of Rolls</key>\n\t<array>\n\t\t<dict>\n\t\t\t<key>Album Type</key>\n\t\t\t<string>Regular</string>\n\t\t\t<key>AlbumId</key>\n\t\t\t<integer>6</integer>\n\t\t\t<key>AlbumName</key>\n\t\t\t<string>Roll 1</string>\n\t\t\t<key>KeyList</key>\n\t\t\t<array>\n\t\t\t\t<string>7</string>\n\t\t\t</array>\n\t\t\t<key>Parent</key>\n\t\t\t<integer>999000</integer>\n\t\t\t<key>PhotoCount</key>\n\t\t\t<integer>1</integer>\n\t\t</dict>\n\t</array>\n\t<key>Major Version</key>\n\t<integer>2</integer>\n\t<key>Master Image List</key>\n\t<dict>\n\t\t<key>7</key>\n\t\t<dict>\n\t\t\t<key>Aspect Ratio</key>\n\t\t\t<real>1</real>\n\t\t\t<key>Caption</key>\n\t\t\t<string>fallow_keep.png.450x450.2005-12-04</string>\n\t\t\t<key>Comment</key>\n\t\t\t<string>a comment</string>\n\t\t\t<key>DateAsTimerInterval</key>\n\t\t\t<real>158341389</real>\n\t\t\t<key>ImagePath</key>\n\t\t\t<string>/Users/username/Pictures/iPhoto Library/2006/01/07/fallow_keep.png.450x450.2005-12-04.jpg</string>\n\t\t\t<key>MediaType</key>\n\t\t\t<string>Image</string>\n\t\t\t<key>MetaModDateAsTimerInterval</key>\n\t\t\t<real>158341439.728129</real>\n\t\t\t<key>ModDateAsTimerInterval</key>\n\t\t\t<real>158341389</real>\n\t\t\t<key>Rating</key>\n\t\t\t<integer>0</integer>\n\t\t\t<key>Roll</key>\n\t\t\t<integer>6</integer>\n\t\t\t<key>ThumbPath</key>\n\t\t\t<string>/Users/username/Pictures/iPhoto Library/2006/01/07/Thumbs/7.jpg</string>\n\t\t</dict>\n\t</dict>\n\t<key>Minor Version</key>\n\t<integer>0</integer>\n</dict>\n</plist>\n"
            },
            "expected_output": "type=object\nkeys=Application Version|Archive Path|List of Albums|List of Keywords|List of Rolls|Major Version|Master Image List|Minor Version\nlist_of_rolls_type=array\nfirst_roll_album_type=Regular\nfirst_roll_album_id=6\nfirst_roll_album_name=Roll 1\nfirst_roll_key_list=7\nfirst_roll_parent=999000\nfirst_roll_photo_count=1\napplication_version=5.0.4 (263)\nmajor_version=2\nfirst_album_master=true\nsecond_album_slideshow_use_titles=false\n"
        }
    ]
}
```

*1.2 Date Elements — Parse date elements from XML property-list input.*

Parse date elements from XML property-list input. The adapter input supplies an XML document and requests the first expiration timestamp; stdout reports the result as type=datetime followed by an ISO-like UTC timestamp line with second precision.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_parse_dates.json`

```json
{
    "description": "Parse date elements from XML property-list input and expose the resulting instant in UTC timestamp form.",
    "cases": [
        {
            "input": {
                "operation": "parse_report",
                "report": "first_expiration",
                "xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n<plist version=\"1.0\">\n<array>\n\t<dict>\n\t\t<key>Created</key>\n\t\t<real>151936595.697543</real>\n\t\t<key>Domain</key>\n\t\t<string>.cleveland.com</string>\n\t\t<key>Expires</key>\n\t\t<date>2007-10-25T12:36:35Z</date>\n\t\t<key>Name</key>\n\t\t<string>CTC</string>\n\t\t<key>Path</key>\n\t\t<string>/</string>\n\t\t<key>Value</key>\n\t\t<string>:broadband:</string>\n\t</dict>\n\t<dict>\n\t\t<key>Created</key>\n\t\t<real>151778895.063041</real>\n\t\t<key>Domain</key>\n\t\t<string>.gamefaqs.com</string>\n\t\t<key>Expires</key>\n\t\t<date>2006-04-21T16:47:58Z</date>\n\t\t<key>Name</key>\n\t\t<string>ctk</string>\n\t\t<key>Path</key>\n\t\t<string>/</string>\n\t\t<key>Value</key>\n\t\t<string>NDM1YmJlYmU0NjZiOGYxZjc1NjgxODg0YmRkMA%3D%3D</string>\n\t</dict>\n\t<dict>\n\t\t<key>Created</key>\n\t\t<real>183530456</real>\n\t\t<key>Domain</key>\n\t\t<string>arstechnica.com</string>\n\t\t<key>Expires</key>\n\t\t<date>2006-10-26T13:56:36Z</date>\n\t\t<key>Name</key>\n\t\t<string>fontFace</string>\n\t\t<key>Path</key>\n\t\t<string>/</string>\n\t\t<key>Value</key>\n\t\t<string>1</string>\n\t</dict>\n\t<dict>\n\t\t<key>Created</key>\n\t\t<real>183004526</real>\n\t\t<key>Domain</key>\n\t\t<string>.sourceforge.net</string>\n\t\t<key>Expires</key>\n\t\t<date>2006-10-20T02:35:26Z</date>\n\t\t<key>Name</key>\n\t\t<string>FRQSTR</string>\n\t\t<key>Path</key>\n\t\t<string>/</string>\n\t\t<key>Value</key>\n\t\t<string>18829595x86799:1:1440x87033:1:1440x86799:1:1440x87248:1:1440|18829595|18829595|18829595|18829595</string>\n\t</dict>\n\t<dict>\n\t\t<key>Created</key>\n\t\t<real>151053128.640531</real>\n\t\t<key>Domain</key>\n\t\t<string>.tvguide.com</string>\n\t\t<key>Expires</key>\n\t\t<date>2025-10-10T07:12:17Z</date>\n\t\t<key>Name</key>\n\t\t<string>DMSEG</string>\n\t\t<key>Path</key>\n\t\t<string>/</string>\n\t\t<key>Value</key>\n\t\t<string>1BDF3D1CC07FC70F&amp;D04451&amp;434EC763&amp;4351FD51&amp;0&amp;</string>\n\t</dict>\n\t<dict>\n\t\t<key>Created</key>\n\t\t<real>151304125.760261</real>\n\t\t<key>Domain</key>\n\t\t<string>.code.blogspot.com</string>\n\t\t<key>Expires</key>\n\t\t<date>2038-01-18T00:00:00Z</date>\n\t\t<key>Name</key>\n\t\t<string>__utma</string>\n\t\t<key>Path</key>\n\t\t<string>/</string>\n\t\t<key>Value</key>\n\t\t<string>11680422.1172819419.1129611326.1129611326.1129611326.1</string>\n\t</dict>\n\t<dict>\n\t\t<key>Created</key>\n\t\t<real>599529600</real>\n\t\t<key>Domain</key>\n\t\t<string>.tvguide.com</string>\n\t\t<key>Expires</key>\n\t\t<date>2020-01-01T00:00:00Z</date>\n\t\t<key>Name</key>\n\t\t<string>gfm</string>\n\t\t<key>Path</key>\n\t\t<string>/</string>\n\t\t<key>Value</key>\n\t\t<string>0</string>\n\t</dict>\n</array>\n</plist>\n"
            },
            "expected_output": "type=datetime\nvalue=2007-10-25T12:36:35Z\n"
        }
    ]
}
```

*1.3 String Text and Empty Keys — Parse string and key text exactly.*

Parse string and key text exactly. XML entities in string content are decoded, and dictionary keys with empty text remain addressable; stdout reports the decoded string or the observed dictionary values in deterministic lines.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_parse_strings_and_empty_keys.json`

```json
{
    "description": "Parse string and key text exactly, including XML entity decoding and empty key names inside dictionaries.",
    "cases": [
        {
            "input": {
                "operation": "parse_report",
                "report": "decoded_string",
                "xml": "<string>Fish &amp; Chips</string>"
            },
            "expected_output": "type=string\nvalue=Fish & Chips\n"
        },
        {
            "input": {
                "operation": "parse_report",
                "report": "empty_key_lookup",
                "xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n<plist version=\"1.0\">\n  <dict>\n    <key>key</key>\n    <dict>\n      <key></key>\n      <string>1</string>\n      <key>subkey</key>\n      <string>2</string>\n    </dict>\n  </dict>\n</plist>\n"
            },
            "expected_output": "type=object\n[a set of formatted key-value lines derived from the nested structure]\nempty_key_value=1\n[a set of formatted key-value lines derived from the nested structure]\n"
        }
    ]
}
```

*1.4 Comments, Empty Sources, and Encoded Text — Accept XML text or a readable stream as input.*

Accept XML text or a readable stream as input. Comments, XML declarations, and document declarations must not create spurious values; an input with no property-list value reports type=null. Declared character encoding must be honored when producing parsed text.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_parse_empty_and_encoded_sources.json`

```json
{
    "description": "Accept readable XML input as well as text input, ignore comments and document declarations, and preserve declared character encoding for parsed text.",
    "cases": [
        {
            "input": {
                "operation": "parse_report",
                "report": "empty_document_result",
                "xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n<plist version=\"1.0\">\n<!-- I am a comment! -->\n<!--\n  I am a multi-line comment!\n  hooray!\n-->\n</plist>\n"
            },
            "expected_output": "type=null\n"
        },
        {
            "input": {
                "operation": "parse_report",
                "report": "empty_document_result",
                "xml": "",
                "as_readable_stream": true
            },
            "expected_output": "type=null\n"
        }
    ]
}
```

*1.5 Data Elements — Parse base64 data elements into readable byte streams.*

Parse base64 data elements into readable byte streams. Stdout reports byte counts and SHA-256 digests for parsed data so the byte content is externally verifiable without relying on host-language object rendering.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_parse_data_elements.json`

```json
{
    "description": "Parse base64 data elements from XML property-list input into byte streams whose content can be read back without alteration.",
    "cases": [
        {
            "input": {
                "operation": "parse_report",
                "report": "data_elements",
                "xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n<plist version=\"1.0\">\n  <dict>\n    <key>stringio</key>\n    <data>dGhpcyBpcyBhIHN0cmluZ2lvIG9iamVjdA==\n    </data>\n    <key>file</key>\n    <data>AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n    AAAAAAAAAAAAAA==\n    </data>\n    <key>io</key>\n    <data>AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n    AAAAAAAAAAAAAA==\n    </data>\n    <key>nodata</key>\n    <data/>\n  </dict>\n</plist>\n"
            },
            "expected_output": "type=object\nio_type=data\nio_bytes=100\nio_sha256=cd00e292c5970d3c5e2f0ffa5171e555bc46bfc4faddfb4a418b6840b86e79a3\nfile_type=data\nfile_bytes=100\nfile_sha256=cd00e292c5970d3c5e2f0ffa5171e555bc46bfc4faddfb4a418b6840b86e79a3\nstringio_type=data\nstringio_bytes=25\nstringio_sha256=dd7f7d430b6345ae1785903935e360bd5b2c9851c6ccd222e665d3eea941e966\nnodata_type=data\nnodata_bytes=0\nnodata_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n"
        }
    ]
}
```

---

### Feature 2: Scalar Value Serialization

**As a developer**, I want to serialize scalar values into XML property-list fragments, so I can write interoperable XML property-list data without manual tag construction.

**Expected Behavior / Usage:**

This feature area covers the externally observable behavior for scalar value serialization. Each leaf sub-feature below is independently testable through one JSON case file and emits only raw stdout in the format shown.

*2.1 Text Values — Serialize text-like values as string elements.*

Serialize text-like values as string elements. Plain text is emitted as element content, while XML-sensitive characters are escaped in the output wire format.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_serialize_text_values.json`

```json
{
    "description": "Serialize text-like values as XML string elements and escape XML-sensitive characters in element content.",
    "cases": [
        {
            "input": {
                "operation": "serialize_fragment",
                "value": {
                    "kind": "string",
                    "value": "testdata"
                }
            },
            "expected_output": "<string>testdata</string>\n"
        },
        {
            "input": {
                "operation": "serialize_fragment",
                "value": {
                    "kind": "symbol_text",
                    "value": "testdata"
                }
            },
            "expected_output": "<string>testdata</string>\n"
        },
        {
            "input": {
                "operation": "serialize_fragment",
                "value": {
                    "kind": "string",
                    "value": "<Fish & Chips>"
                }
            },
            "expected_output": "<string>&lt;Fish &amp; Chips&gt;</string>\n"
        }
    ]
}
```

*2.2 Numeric and Boolean Values — Serialize integer, real-number, and boolean values to their corresponding XML property-list scalar elements.*

Serialize integer, real-number, and boolean values to their corresponding XML property-list scalar elements. Booleans are emitted as self-closing true or false tags.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_serialize_numeric_and_boolean_values.json`

```json
{
    "description": "Serialize integer, real-number, and boolean values to the corresponding XML property-list scalar elements.",
    "cases": [
        {
            "input": {
                "operation": "serialize_fragment",
                "value": {
                    "kind": "integer",
                    "value": 42
                }
            },
            "expected_output": "<integer>42</integer>\n"
        },
        {
            "input": {
                "operation": "serialize_fragment",
                "value": {
                    "kind": "integer",
                    "value": 2376239847623987623
                }
            },
            "expected_output": "<integer>2376239847623987623</integer>\n"
        },
        {
            "input": {
                "operation": "serialize_fragment",
                "value": {
                    "kind": "integer",
                    "value": -8192
                }
            },
            "expected_output": "<integer>-8192</integer>\n"
        },
        {
            "input": {
                "operation": "serialize_fragment",
                "value": {
                    "kind": "real",
                    "value": 3.14159
                }
            },
            "expected_output": "<real>3.14159</real>\n"
        }
    ]
}
```

*2.3 Temporal Values — Serialize calendar dates, date-times, and timestamps to XML date elements.*

Serialize calendar dates, date-times, and timestamps to XML date elements. The emitted value uses a UTC-style timestamp with second precision and a trailing Z marker.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_serialize_temporal_values.json`

```json
{
    "description": "Serialize calendar dates, date-times, and timestamps into UTC-style XML date elements using second precision.",
    "cases": [
        {
            "input": {
                "operation": "serialize_fragment",
                "value": {
                    "kind": "date",
                    "value": "2020-01-02"
                }
            },
            "expected_output": "<date>2020-01-02T00:00:00Z</date>\n"
        },
        {
            "input": {
                "operation": "serialize_fragment",
                "value": {
                    "kind": "datetime",
                    "value": "2020-01-02T03:04:05Z"
                }
            },
            "expected_output": "<date>2020-01-02T03:04:05Z</date>\n"
        },
        {
            "input": {
                "operation": "serialize_fragment",
                "value": {
                    "kind": "timestamp",
                    "value": "2020-01-02T03:04:05Z"
                }
            },
            "expected_output": "<date>2020-01-02T03:04:05Z</date>\n"
        }
    ]
}
```

---

### Feature 3: Collection Serialization

**As a developer**, I want to serialize arrays and dictionaries into nested XML property-list structures, so I can represent structured data without hand-writing recursive XML formatting.

**Expected Behavior / Usage:**

This feature area covers the externally observable behavior for collection serialization. Each leaf sub-feature below is independently testable through one JSON case file and emits only raw stdout in the format shown.

*3.1 Arrays — Serialize arrays as XML array elements.*

Serialize arrays as XML array elements. Non-empty arrays preserve item order and serialize each item recursively; empty arrays use a compact self-closing array element.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_serialize_arrays.json`

```json
{
    "description": "Serialize arrays as XML array elements, preserving element order and using a compact self-closing element for an empty array.",
    "cases": [
        {
            "input": {
                "operation": "serialize_fragment",
                "value": {
                    "kind": "array",
                    "items": [
                        {
                            "kind": "integer",
                            "value": 1
                        },
                        {
                            "kind": "integer",
                            "value": 2
                        },
                        {
                            "kind": "integer",
                            "value": 3
                        }
                    ]
                }
            },
            "expected_output": "<array>\n\t<integer>1</integer>\n\t<integer>2</integer>\n\t<integer>3</integer>\n</array>\n"
        },
        {
            "input": {
                "operation": "serialize_fragment",
                "value": {
                    "kind": "array",
                    "items": []
                }
            },
            "expected_output": "<array/>\n"
        }
    ]
}
```

*3.2 Dictionaries — Serialize dictionaries as XML dict elements.*

Serialize dictionaries as XML dict elements. Keys are emitted as key elements sorted by their textual form; empty dictionaries use a compact self-closing dict element.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_serialize_dictionaries.json`

```json
{
    "description": "Serialize dictionaries as XML dict elements, sorting keys by their textual form and using a compact self-closing element for an empty dictionary.",
    "cases": [
        {
            "input": {
                "operation": "serialize_fragment",
                "value": {
                    "kind": "object",
                    "entries": [
                        {
                            "key": {
                                "kind": "symbol_text",
                                "value": "[a dynamic set of keys sorted alphabetically, including those with special characters]"
                            },
                            "value": {
                                "kind": "symbol_text",
                                "value": "bar"
                            }
                        },
                        {
                            "key": {
                                "kind": "symbol_text",
                                "value": "[a dynamic set of keys sorted alphabetically, including those with special characters]"
                            },
                            "value": {
                                "kind": "integer",
                                "value": 123
                            }
                        }
                    ]
                }
            },
            "expected_output": "<dict>\n\t<key>[a dynamic set of keys sorted alphabetically, including those with special characters]</key>\n\t<integer>123</integer>\n\t<key>[a dynamic set of keys sorted alphabetically, including those with special characters]</key>\n\t<string>bar</string>\n</dict>\n"
        },
        {
            "input": {
                "operation": "serialize_fragment",
                "value": {
                    "kind": "object",
                    "entries": []
                }
            },
            "expected_output": "<dict/>\n"
        }
    ]
}
```

*3.3 Nested Collections — Serialize arrays and dictionaries recursively.*

Serialize arrays and dictionaries recursively. Nested output must preserve the XML tree shape and indentation shown in stdout so consumers receive a stable property-list fragment.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_serialize_nested_collections.json`

```json
{
    "description": "Serialize nested arrays and dictionaries recursively while preserving the expected XML tree shape and indentation.",
    "cases": [
        {
            "input": {
                "operation": "serialize_fragment",
                "value": {
                    "kind": "object",
                    "entries": [
                        {
                            "key": {
                                "kind": "symbol_text",
                                "value": "ary"
                            },
                            "value": {
                                "kind": "array",
                                "items": [
                                    {
                                        "kind": "integer",
                                        "value": 1
                                    },
                                    {
                                        "kind": "symbol_text",
                                        "value": "b"
                                    },
                                    {
                                        "kind": "string",
                                        "value": "3"
                                    }
                                ]
                            }
                        }
                    ]
                }
            },
            "expected_output": "<dict>\n\t<key>ary</key>\n\t<array>\n\t\t<integer>1</integer>\n\t\t<string>b</string>\n\t\t<string>3</string>\n\t</array>\n</dict>\n"
        },
        {
            "input": {
                "operation": "serialize_fragment",
                "value": {
                    "kind": "array",
                    "items": [
                        {
                            "kind": "object",
                            "entries": [
                                {
                                    "key": {
                                        "kind": "symbol_text",
                                        "value": "[a dynamic set of keys sorted alphabetically, including those with special characters]"
                                    },
                                    "value": {
                                        "kind": "string",
                                        "value": "bar"
                                    }
                                }
                            ]
                        },
                        {
                            "kind": "symbol_text",
                            "value": "b"
                        },
                        {
                            "kind": "integer",
                            "value": 3
                        }
                    ]
                }
            },
            "expected_output": "<array>\n\t<dict>\n\t\t<key>[a dynamic set of keys sorted alphabetically, including those with special characters]</key>\n\t\t<string>bar</string>\n\t</dict>\n\t<string>b</string>\n\t<integer>3</integer>\n</array>\n"
        }
    ]
}
```

---

### Feature 4: Binary Data and Full Document Serialization

**As a developer**, I want to serialize byte streams and complete XML property-list documents, so I can emit both reusable fragments and complete documents suitable for property-list consumers.

**Expected Behavior / Usage:**

This feature area covers the externally observable behavior for binary data and full document serialization. Each leaf sub-feature below is independently testable through one JSON case file and emits only raw stdout in the format shown.

*4.1 Binary Data — Serialize byte-stream input as a base64 XML data element.*

Serialize byte-stream input as a base64 XML data element. The emitted base64 content is line-wrapped inside data tags, preserving the original bytes through the wire format.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_serialize_binary_data.json`

```json
{
    "description": "Serialize byte-stream input as base64 XML data elements with line wrapping suitable for property-list output.",
    "cases": [
        {
            "input": {
                "operation": "serialize_fragment",
                "value": {
                    "kind": "binary",
                    "base64": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="
                }
            },
            "expected_output": "<data>\nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==\n</data>\n"
        },
        {
            "input": {
                "operation": "serialize_fragment",
                "value": {
                    "kind": "binary",
                    "base64": "dGhpcyBpcyBhIHN0cmluZ2lvIG9iamVjdA=="
                }
            },
            "expected_output": "<data>\ndGhpcyBpcyBhIHN0cmluZ2lvIG9iamVjdA==\n</data>\n"
        }
    ]
}
```

*4.2 Complete XML Document Envelope — Wrap a serialized value in a complete XML property-list document when requested.*

Wrap a serialized value in a complete XML property-list document when requested. Stdout includes the XML declaration, document type declaration, root element, serialized body, and closing root tag.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_serialize_complete_document.json`

```json
{
    "description": "Optionally wrap a serialized value in a complete XML property-list document with XML declaration, document type, root element, and closing root tag.",
    "cases": [
        {
            "input": {
                "operation": "serialize_document",
                "value": {
                    "kind": "array",
                    "items": [
                        {
                            "kind": "integer",
                            "value": 1
                        },
                        {
                            "kind": "symbol_text",
                            "value": "b"
                        },
                        {
                            "kind": "boolean",
                            "value": true
                        }
                    ]
                }
            },
            "expected_output": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n<plist version=\"1.0\">\n<array>\n\t<integer>1</integer>\n\t<string>b</string>\n\t<true/>\n</array>\n</plist>\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_parse_structured_xml_values.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_parse_structured_xml_values@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the standard base64 wrapping convention
- deterministic ordering based on logical unit
