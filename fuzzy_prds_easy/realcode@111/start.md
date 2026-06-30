## Product Requirement Document

# WebDAV Remote Resource Adapter - Protocol XML, Request, Configuration, and Error Contracts

## Project Goal

Build a WebDAV remote resource client library and execution adapter that allows developers to list resources, inspect metadata, manage custom properties, validate connection settings, issue protocol requests, and receive portable structured errors without manually composing XML, parsing multistatus responses, or decoding raw HTTP failure details.

---

## Background & Problem

Without this library/tool, developers are forced to handcraft WebDAV XML request bodies, traverse XML namespaces, normalize URL paths, choose HTTP methods and headers, validate endpoint credentials and certificate settings, and interpret server status codes themselves. This leads to repetitive protocol boilerplate, inconsistent error handling, brittle path matching, and difficult maintenance when different WebDAV servers expose slightly different response shapes.

With this library/tool, developers interact with higher-level resource, metadata, property, configuration, and request concepts while the adapter exposes deterministic input/output behavior for black-box testing.

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

### Feature 1: Directory Listing Parsing

**As a developer**, I want to parse WebDAV directory listing responses, so I can display remote resources and their metadata without manually traversing XML namespaces.

**Expected Behavior / Usage:**

This feature group covers WebDAV multistatus responses that contain one or more resource entries. Leaf features split compact resource entry extraction from detailed metadata extraction.

*1.1 Directory Listing Entries* — This leaf feature covers parse WebDAV collection responses into ordered paths.

**As a developer**, I want to parse WebDAV collection responses into ordered paths, so I can show users the resources returned by a remote directory listing.

**Expected Behavior / Usage:**

The adapter receives JSON containing only the externally supplied values needed for this behavior, such as WebDAV multistatus XML, server URL, requested path, property descriptors, connection options, status codes, or error data depending on the feature. It prints newline-delimited fields that expose the observable result: ordered resource rows, metadata fields, XML request bodies, byte counts, HTTP request details, validation status, or normalized error records. Errors are rendered as neutral `error=<category>` records with separate data fields rather than host-language exception names or runtime messages.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_list_resource_entries.json`

```json
{
    "description": "Parse a WebDAV multistatus directory listing into ordered resource entries with each entry path, directory flag, and display text.",
    "cases": [
        {
            "input": {
                "multistatus_xml": "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<D:multistatus xmlns:D=\"DAV:\">\n    <D:response xmlns:lp1=\"DAV:\" xmlns:lp2=\"http://apache.org/dav/props/\">\n        <D:href>/test_dir/</D:href>\n        <D:propstat>\n            <D:prop>\n                <lp1:resourcetype>\n                    <D:collection/>\n                </lp1:resourcetype>\n                <lp1:creationdate>2020-04-10T21:59:43Z</lp1:creationdate>\n                <lp1:getlastmodified>Fri, 10 Apr 2020 21:59:43 GMT</lp1:getlastmodified>\n                <lp1:getetag>\n                    \"1000-5a2f6d9cf8d39\"\n                </lp1:getetag>\n                <D:supportedlock>\n                    <D:lockentry>\n                        <D:lockscope>\n                            <D:exclusive/>\n                        </D:lockscope>\n\n                        <D:locktype>\n                            <D:write/>\n                        </D:locktype>\n\n                    </D:lockentry>\n\n                    <D:lockentry>\n                        <D:lockscope>\n                            <D:shared/>\n                        </D:lockscope>\n\n                        <D:locktype>\n                            <D:write/>\n                        </D:locktype>\n\n                    </D:lockentry>\n\n                </D:supportedlock>\n                <D:lockdiscovery/>\n                <D:getcontenttype>httpd/unix-directory</D:getcontenttype>\n            </D:prop>\n            <D:status>HTTP/1.1 200 OK</D:status>\n        </D:propstat>\n\n    </D:response>\n\n    <D:response xmlns:lp1=\"DAV:\" xmlns:lp2=\"http://apache.org/dav/props/\">\n        <D:href>/test_dir/test.txt</D:href>\n        <D:propstat>\n            <D:prop>\n                <lp1:resourcetype/>\n                <lp1:creationdate>2020-04-10T21:59:43Z</lp1:creationdate>\n                <lp1:getcontentlength>\n                    41\n                </lp1:getcontentlength>\n                <lp1:getlastmodified>Fri, 10 Apr 2020 21:59:43 GMT</lp1:getlastmodified>\n                <lp1:getetag>\"29-5a2f6d9cf8d39\"</lp1:getetag>\n                <lp2:executable>\n                    F\n                </lp2:executable>\n                <D:supportedlock>\n                    <D:lockentry>\n                        <D:lockscope>\n                            <D:exclusive/>\n                        </D:lockscope>\n\n                        <D:locktype>\n                            <D:write/>\n                        </D:locktype>\n\n                    </D:lockentry>\n\n                    <D:lockentry>\n                        <D:lockscope>\n                            <D:shared/>\n                        </D:lockscope>\n\n                        <D:locktype>\n                            <D:write/>\n                        </D:locktype>\n\n                    </D:lockentry>\n\n                </D:supportedlock>\n                <D:lockdiscovery/>\n                <D:getcontenttype>text/plain</D:getcontenttype>\n            </D:prop>\n            <D:status>HTTP/1.1 200 OK</D:status>\n        </D:propstat>\n\n    </D:response>\n\n</D:multistatus>"
            },
            "expected_output": "count=2\nitem[0].path=/test_dir/\nitem[0].is_directory=true\nitem[0].text=/test_dir/\nitem[1].path=/test_dir/test.txt\nitem[1].is_directory=false\nitem[1].text=/test_dir/test.txt\n"
        }
    ]
}
```

*1.2 Directory Listing Metadata* — This leaf feature covers parse WebDAV collection responses into detailed metadata rows.

**As a developer**, I want to parse WebDAV collection responses into detailed metadata rows, so I can display dates, sizes, content types, paths, and directory flags for each listed resource.

**Expected Behavior / Usage:**

The adapter receives JSON containing only the externally supplied values needed for this behavior, such as WebDAV multistatus XML, server URL, requested path, property descriptors, connection options, status codes, or error data depending on the feature. It prints newline-delimited fields that expose the observable result: ordered resource rows, metadata fields, XML request bodies, byte counts, HTTP request details, validation status, or normalized error records. Errors are rendered as neutral `error=<category>` records with separate data fields rather than host-language exception names or runtime messages.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_list_resource_metadata.json`

```json
{
    "description": "Parse a WebDAV multistatus directory listing into ordered resource metadata records.",
    "cases": [
        {
            "input": {
                "multistatus_xml": "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<d:multistatus xmlns:d=\"DAV:\">\n    <d:response>\n        <d:href>/test_dir/test.txt</d:href>\n        <d:propstat>\n            <d:status>HTTP/1.1 200 OK</d:status>\n            <d:prop>\n                <d:resourcetype/>\n                <d:getlastmodified>Wed, 18 Oct 2017 15:16:04 GMT</d:getlastmodified>\n                <d:getetag>ab0b4b7973803c03639b848682b5f38c</d:getetag>\n                <d:getcontenttype>text/plain</d:getcontenttype>\n                <d:getcontentlength>41</d:getcontentlength>\n                <d:displayname>test.txt</d:displayname>\n                <d:creationdate>[a sample ISO 8601 timestamp]</d:creationdate>\n            </d:prop>\n        </d:propstat>\n    </d:response>\n</d:multistatus>"
            },
            "expected_output": "count=1\nitem[0].created=[a sample ISO 8601 timestamp]\nitem[0].name=test.txt\nitem[0].modified=Wed, 18 Oct 2017 15:16:04 GMT\nitem[0].size=41\nitem[0].etag=ab0b4b7973803c03639b848682b5f38c\nitem[0].isdir=false\nitem[0].path=/test_dir/test.txt\nitem[0].content_type=text/plain\n"
        }
    ]
}
```

---

### Feature 2: Storage Quota Handling

**As a developer**, I want to request and parse WebDAV storage quota information, so I can show available remote storage and handle unsupported servers consistently.

**Expected Behavior / Usage:**

This feature group covers both directions of the quota interaction: producing the XML request body and parsing the server response into either available bytes or a normalized unsupported-operation error.

*2.1 Quota Query Request Body* — This leaf feature covers generate the XML body for a quota query.

**As a developer**, I want to generate the XML body for a quota query, so I can ask a WebDAV server for used and available storage in the protocol format.

**Expected Behavior / Usage:**

The adapter receives JSON containing only the externally supplied values needed for this behavior, such as WebDAV multistatus XML, server URL, requested path, property descriptors, connection options, status codes, or error data depending on the feature. It prints newline-delimited fields that expose the observable result: ordered resource rows, metadata fields, XML request bodies, byte counts, HTTP request details, validation status, or normalized error records. Errors are rendered as neutral `error=<category>` records with separate data fields rather than host-language exception names or runtime messages.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_free_space_request_xml.json`

```json
{
    "description": "Build the WebDAV XML body used to request available and used quota bytes.",
    "cases": [
        {
            "input": {},
            "expected_output": "<?xml version='1.0' encoding='UTF-8'?>\n<propfind xmlns=\"DAV:\"><prop><quota-available-bytes/><quota-used-bytes/></prop></propfind>\n"
        }
    ]
}
```

*2.2 Quota Query Response* — This leaf feature covers parse a quota response into available bytes or a normalized unsupported-operation error.

**As a developer**, I want to parse a quota response into available bytes or a normalized unsupported-operation error, so I can handle servers that either report or omit quota properties.

**Expected Behavior / Usage:**

The adapter receives JSON containing only the externally supplied values needed for this behavior, such as WebDAV multistatus XML, server URL, requested path, property descriptors, connection options, status codes, or error data depending on the feature. It prints newline-delimited fields that expose the observable result: ordered resource rows, metadata fields, XML request bodies, byte counts, HTTP request details, validation status, or normalized error records. Errors are rendered as neutral `error=<category>` records with separate data fields rather than host-language exception names or runtime messages.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_free_space_response.json`

```json
{
    "description": "Parse a WebDAV quota response into available byte count or a normalized error when quota is unsupported.",
    "cases": [
        {
            "input": {
                "server": "localhost",
                "multistatus_xml": "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<d:multistatus xmlns:d=\"DAV:\">\n    <d:response>\n        <d:href>/</d:href>\n        <d:propstat>\n            <d:status>HTTP/1.1 200 OK</d:status>\n            <d:prop>\n                <d:quota-used-bytes>697</d:quota-used-bytes>\n                <d:quota-available-bytes>10737417543</d:quota-available-bytes>\n            </d:prop>\n        </d:propstat>\n    </d:response>\n</d:multistatus>"
            },
            "expected_output": "available_bytes=10737417543\n"
        }
    ]
}
```

---

### Feature 3: Resource Metadata and Path Matching

**As a developer**, I want to locate a resource in WebDAV multistatus XML and interpret its metadata, so I can inspect files and directories reliably even when server URL prefixes are present.

**Expected Behavior / Usage:**

This feature group covers metadata extraction, directory classification, and path-specific response selection. Each leaf receives XML plus the externally requested server/path values and prints the matching observable fields or a normalized error.

*3.1 Single Resource Metadata* — This leaf feature covers extract metadata for one requested resource path.

**As a developer**, I want to extract metadata for one requested resource path, so I can inspect one remote file or directory without manually searching XML.

**Expected Behavior / Usage:**

The adapter receives JSON containing only the externally supplied values needed for this behavior, such as WebDAV multistatus XML, server URL, requested path, property descriptors, connection options, status codes, or error data depending on the feature. It prints newline-delimited fields that expose the observable result: ordered resource rows, metadata fields, XML request bodies, byte counts, HTTP request details, validation status, or normalized error records. Errors are rendered as neutral `error=<category>` records with separate data fields rather than host-language exception names or runtime messages.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_single_resource_metadata.json`

```json
{
    "description": "Extract metadata for one requested resource path from a WebDAV multistatus response.",
    "cases": [
        {
            "input": {
                "server": "localhost",
                "path": "/test_dir/test.txt",
                "multistatus_xml": "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<d:multistatus xmlns:d=\"DAV:\">\n    <d:response>\n        <d:href>/test_dir/test.txt</d:href>\n        <d:propstat>\n            <d:status>HTTP/1.1 200 OK</d:status>\n            <d:prop>\n                <d:resourcetype/>\n                <d:getlastmodified>Wed, 18 Oct 2017 15:16:04 GMT</d:getlastmodified>\n                <d:getetag>ab0b4b7973803c03639b848682b5f38c</d:getetag>\n                <d:getcontenttype>text/plain</d:getcontenttype>\n                <d:getcontentlength>41</d:getcontentlength>\n                <d:displayname>test.txt</d:displayname>\n                <d:creationdate>[a sample ISO 8601 timestamp]</d:creationdate>\n            </d:prop>\n        </d:propstat>\n    </d:response>\n</d:multistatus>"
            },
            "expected_output": "created=[a sample ISO 8601 timestamp]\nname=test.txt\nmodified=Wed, 18 Oct 2017 15:16:04 GMT\nsize=41\netag=ab0b4b7973803c03639b848682b5f38c\ncontent_type=text/plain\n"
        }
    ]
}
```

*3.2 Resource Type Detection* — This leaf feature covers detect whether a requested resource is a collection.

**As a developer**, I want to detect whether a requested resource is a collection, so I can branch between file and directory handling using protocol metadata.

**Expected Behavior / Usage:**

The adapter receives JSON containing only the externally supplied values needed for this behavior, such as WebDAV multistatus XML, server URL, requested path, property descriptors, connection options, status codes, or error data depending on the feature. It prints newline-delimited fields that expose the observable result: ordered resource rows, metadata fields, XML request bodies, byte counts, HTTP request details, validation status, or normalized error records. Errors are rendered as neutral `error=<category>` records with separate data fields rather than host-language exception names or runtime messages.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_directory_classification.json`

```json
{
    "description": "Determine whether a requested resource path is a directory from its WebDAV resource type.",
    "cases": [
        {
            "input": {
                "server": "https://webdav.yandex.ru",
                "path": "/test_dir",
                "multistatus_xml": "<?xml version='1.0' encoding='UTF-8'?>\n<d:multistatus xmlns:d=\"DAV:\">\n    <d:response>\n        <d:href>/</d:href>\n        <d:propstat>\n            <d:status>HTTP/1.1 200 OK</d:status>\n            <d:prop>\n                <d:creationdate>2012-04-04T20:00:00Z</d:creationdate>\n                <d:displayname>disk</d:displayname>\n                <d:getlastmodified>Wed, 04 Apr 2012 20:00:00 GMT</d:getlastmodified>\n                <d:resourcetype>\n                    <d:collection/>\n                </d:resourcetype>\n            </d:prop>\n        </d:propstat>\n    </d:response>\n    <d:response>\n        <d:href>/test_dir/</d:href>\n        <d:propstat>\n            <d:status>HTTP/1.1 200 OK</d:status>\n            <d:prop>\n                <d:creationdate>2018-05-10T07:31:13Z</d:creationdate>\n                <d:displayname>test_dir</d:displayname>\n                <d:getlastmodified>Thu, 10 May 2018 07:31:13 GMT</d:getlastmodified>\n                <d:resourcetype>\n                    <d:collection/>\n                </d:resourcetype>\n            </d:prop>\n        </d:propstat>\n    </d:response>\n    <d:response>\n        <d:href>/%D0%93%D0%BE%D1%80%D1%8B.jpg</d:href>\n        <d:propstat>\n            <d:status>HTTP/1.1 200 OK</d:status>\n            <d:prop>\n                <d:getetag>1392851f0668017168ee4b5a59d66e7b</d:getetag>\n                <d:creationdate>2018-05-09T14:44:28Z</d:creationdate>\n                <d:displayname>Горы.jpg</d:displayname>\n                <d:getlastmodified>Wed, 09 May 2018 14:44:28 GMT</d:getlastmodified>\n                <d:getcontenttype>image/jpeg</d:getcontenttype>\n                <d:getcontentlength>1762478</d:getcontentlength>\n                <d:resourcetype/>\n            </d:prop>\n        </d:propstat>\n    </d:response>\n    <d:response>\n        <d:href>/%D0%97%D0%B8%D0%BC%D0%B0.jpg</d:href>\n        <d:propstat>\n            <d:status>HTTP/1.1 200 OK</d:status>\n            <d:prop>\n                <d:getetag>a64146fee5e15b3b94c204e544426d43</d:getetag>\n                <d:creationdate>2018-05-09T14:44:28Z</d:creationdate>\n                <d:displayname>Зима.jpg</d:displayname>\n                <d:getlastmodified>Wed, 09 May 2018 14:44:28 GMT</d:getlastmodified>\n                <d:getcontenttype>image/jpeg</d:getcontenttype>\n                <d:getcontentlength>1394575</d:getcontentlength>\n                <d:resourcetype/>\n            </d:prop>\n        </d:propstat>\n    </d:response>\n    <d:response>\n        <d:href>/%D0%9C%D0%B8%D1%88%D0%BA%D0%B8.jpg</d:href>\n        <d:propstat>\n            <d:status>HTTP/1.1 200 OK</d:status>\n            <d:prop>\n                <d:getetag>569a1c98696050439b5b2a1ecfa52d19</d:getetag>\n                <d:creationdate>2018-05-09T14:44:27Z</d:creationdate>\n                <d:displayname>Мишки.jpg</d:displayname>\n                <d:getlastmodified>Wed, 09 May 2018 14:44:27 GMT</d:getlastmodified>\n                <d:getcontenttype>image/jpeg</d:getcontenttype>\n                <d:getcontentlength>1555830</d:getcontentlength>\n                <d:resourcetype/>\n            </d:prop>\n        </d:propstat>\n    </d:response>\n    <d:response>\n        <d:href>/%D0%9C%D0%BE%D1%80%D0%B5.jpg</d:href>\n        <d:propstat>\n            <d:status>HTTP/1.1 200 OK</d:status>\n            <d:prop>\n                <d:getetag>ab903d9cab031eca2a8f12f37bbc9d37</d:getetag>\n                <d:creationdate>2018-05-09T14:44:27Z</d:creationdate>\n                <d:displayname>Море.jpg</d:displayname>\n                <d:getlastmodified>Wed, 09 May 2018 14:44:27 GMT</d:getlastmodified>\n                <d:getcontenttype>image/jpeg</d:getcontenttype>\n                <d:getcontentlength>1080301</d:getcontentlength>\n                <d:resourcetype/>\n            </d:prop>\n        </d:propstat>\n    </d:response>\n    <d:response>\n        <d:href>/%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0.jpg</d:href>\n        <d:propstat>\n            <d:status>HTTP/1.1 200 OK</d:status>\n            <d:prop>\n                <d:getetag>d27d72a3059ad5ebed7a5470459d2670</d:getetag>\n                <d:creationdate>2018-05-09T14:44:27Z</d:creationdate>\n                <d:displayname>Москва.jpg</d:displayname>\n                <d:getlastmodified>Wed, 09 May 2018 14:44:27 GMT</d:getlastmodified>\n                <d:getcontenttype>image/jpeg</d:getcontenttype>\n                <d:getcontentlength>1454228</d:getcontentlength>\n                <d:resourcetype/>\n            </d:prop>\n        </d:propstat>\n    </d:response>\n    <d:response>\n        <d:href>/%D0%A1%D0%B0%D0%BD%D0%BA%D1%82-%D0%9F%D0%B5%D1%82%D0%B5%D1%80%D0%B1%D1%83%D1%80%D0%B3.jpg</d:href>\n        <d:propstat>\n            <d:status>HTTP/1.1 200 OK</d:status>\n            <d:prop>\n                <d:getetag>f1abe3b27b410128623fd1ca00a45c29</d:getetag>\n                <d:creationdate>2018-05-09T14:44:27Z</d:creationdate>\n                <d:displayname>Санкт-Петербург.jpg</d:displayname>\n                <d:getlastmodified>Wed, 09 May 2018 14:44:27 GMT</d:getlastmodified>\n                <d:getcontenttype>image/jpeg</d:getcontenttype>\n                <d:getcontentlength>2573704</d:getcontentlength>\n                <d:resourcetype/>\n            </d:prop>\n        </d:propstat>\n    </d:response>\n    <d:response>\n        <d:href>/%D0%A5%D0%BB%D0%B5%D0%B1%D0%BD%D1%8B%D0%B5%20%D0%BA%D1%80%D0%BE%D1%88%D0%BA%D0%B8.mp4</d:href>\n        <d:propstat>\n            <d:status>HTTP/1.1 200 OK</d:status>\n            <d:prop>\n                <d:getetag>ea977f513074d5524bee3638798183b9</d:getetag>\n                <d:creationdate>2018-05-09T14:44:28Z</d:creationdate>\n                <d:displayname>Хлебные крошки.mp4</d:displayname>\n                <d:getlastmodified>Wed, 09 May 2018 14:44:28 GMT</d:getlastmodified>\n                <d:getcontenttype>video/mp4</d:getcontenttype>\n                <d:getcontentlength>31000079</d:getcontentlength>\n                <d:resourcetype/>\n            </d:prop>\n        </d:propstat>\n    </d:response>\n</d:multistatus>"
            },
            "expected_output": "is_directory=true\n"
        }
    ]
}
```

*3.3 Path-Matched Response Selection* — This leaf feature covers select the response element that corresponds to a requested path.

**As a developer**, I want to select the response element that corresponds to a requested path, so I can support lookups even when server URLs include a mounted prefix.

**Expected Behavior / Usage:**

The adapter receives JSON containing only the externally supplied values needed for this behavior, such as WebDAV multistatus XML, server URL, requested path, property descriptors, connection options, status codes, or error data depending on the feature. It prints newline-delimited fields that expose the observable result: ordered resource rows, metadata fields, XML request bodies, byte counts, HTTP request details, validation status, or normalized error records. Errors are rendered as neutral `error=<category>` records with separate data fields rather than host-language exception names or runtime messages.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_extract_resource_response.json`

```json
{
    "description": "Select the WebDAV response element matching a requested path, including paths beneath a server URL prefix.",
    "cases": [
        {
            "input": {
                "server": "localhost",
                "path": "/test_dir/test.txt",
                "multistatus_xml": "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<d:multistatus xmlns:d=\"DAV:\">\n    <d:response>\n        <d:href>/test_dir/test.txt</d:href>\n        <d:propstat>\n            <d:status>HTTP/1.1 200 OK</d:status>\n            <d:prop>\n                <d:resourcetype/>\n                <d:getlastmodified>Wed, 18 Oct 2017 15:16:04 GMT</d:getlastmodified>\n                <d:getetag>ab0b4b7973803c03639b848682b5f38c</d:getetag>\n                <d:getcontenttype>text/plain</d:getcontenttype>\n                <d:getcontentlength>41</d:getcontentlength>\n                <d:displayname>test.txt</d:displayname>\n                <d:creationdate>[a sample ISO 8601 timestamp]</d:creationdate>\n            </d:prop>\n        </d:propstat>\n    </d:response>\n</d:multistatus>"
            },
            "expected_output": "href=/test_dir/test.txt\ncreated=[a sample ISO 8601 timestamp]\nname=test.txt\nmodified=Wed, 18 Oct 2017 15:16:04 GMT\nsize=41\netag=ab0b4b7973803c03639b848682b5f38c\ncontent_type=text/plain\n"
        }
    ]
}
```

---

### Feature 4: Custom Property XML and Values

**As a developer**, I want to create and parse WebDAV custom property messages, so I can query and update resource metadata without handcrafting XML.

**Expected Behavior / Usage:**

This feature group covers XML generation for property lookup, property value extraction, and XML generation for property updates. Property descriptors include a required name plus optional namespace and value fields.

*4.1 Property Lookup Request Body* — This leaf feature covers generate XML for requesting a named metadata property.

**As a developer**, I want to generate XML for requesting a named metadata property, so I can query custom WebDAV properties consistently.

**Expected Behavior / Usage:**

The adapter receives JSON containing only the externally supplied values needed for this behavior, such as WebDAV multistatus XML, server URL, requested path, property descriptors, connection options, status codes, or error data depending on the feature. It prints newline-delimited fields that expose the observable result: ordered resource rows, metadata fields, XML request bodies, byte counts, HTTP request details, validation status, or normalized error records. Errors are rendered as neutral `error=<category>` records with separate data fields rather than host-language exception names or runtime messages.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_property_request_xml.json`

```json
{
    "description": "Build a WebDAV property lookup XML body for a named property with an optional namespace.",
    "cases": [
        {
            "input": {
                "property": {
                    "namespace": "test",
                    "name": "aProperty"
                }
            },
            "expected_output": "<?xml version='1.0' encoding='UTF-8'?>\n<propfind xmlns=\"DAV:\"><prop><aProperty xmlns=\"test\"/></prop></propfind>\n"
        }
    ]
}
```

*4.2 Property Value Parsing* — This leaf feature covers extract a named metadata property value from a response.

**As a developer**, I want to extract a named metadata property value from a response, so I can consume custom property values returned by the server.

**Expected Behavior / Usage:**

The adapter receives JSON containing only the externally supplied values needed for this behavior, such as WebDAV multistatus XML, server URL, requested path, property descriptors, connection options, status codes, or error data depending on the feature. It prints newline-delimited fields that expose the observable result: ordered resource rows, metadata fields, XML request bodies, byte counts, HTTP request details, validation status, or normalized error records. Errors are rendered as neutral `error=<category>` records with separate data fields rather than host-language exception names or runtime messages.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_property_value_response.json`

```json
{
    "description": "Extract a named metadata property value from a WebDAV property response.",
    "cases": [
        {
            "input": {
                "property_name": "aProperty",
                "multistatus_xml": "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<d:multistatus xmlns:d=\"DAV:\">\n    <d:response>\n        <d:href>/test_dir/test.txt</d:href>\n        <d:propstat>\n            <d:status>HTTP/1.1 200 OK</d:status>\n            <d:prop>\n                <aProperty xmlns=\"test\">aValue</aProperty>\n            </d:prop>\n        </d:propstat>\n    </d:response>\n</d:multistatus>"
            },
            "expected_output": "value=aValue\n"
        }
    ]
}
```

*4.3 Property Update Request Body* — This leaf feature covers generate XML for updating one or more metadata properties.

**As a developer**, I want to generate XML for updating one or more metadata properties, so I can send custom property changes in one protocol-compliant request.

**Expected Behavior / Usage:**

The adapter receives JSON containing only the externally supplied values needed for this behavior, such as WebDAV multistatus XML, server URL, requested path, property descriptors, connection options, status codes, or error data depending on the feature. It prints newline-delimited fields that expose the observable result: ordered resource rows, metadata fields, XML request bodies, byte counts, HTTP request details, validation status, or normalized error records. Errors are rendered as neutral `error=<category>` records with separate data fields rather than host-language exception names or runtime messages.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_set_properties_request_xml.json`

```json
{
    "description": "Build a WebDAV property update XML body for one or more named properties with optional namespaces and values.",
    "cases": [
        {
            "input": {
                "properties": [
                    {
                        "namespace": "test",
                        "name": "aProperty",
                        "value": "aValue"
                    }
                ]
            },
            "expected_output": "<?xml version='1.0' encoding='UTF-8'?>\n<propertyupdate xmlns=\"DAV:\"><set><prop><aProperty xmlns=\"test\">aValue</aProperty></prop></set></propertyupdate>\n"
        },
        {
            "input": {
                "properties": [
                    {
                        "name": "aProperty"
                    }
                ]
            },
            "expected_output": "<?xml version='1.0' encoding='UTF-8'?>\n<propertyupdate xmlns=\"DAV:\"><set><prop><aProperty xmlns=\"\"></aProperty></prop></set></propertyupdate>\n"
        }
    ]
}
```

---

### Feature 5: Connection Configuration Validation

**As a developer**, I want to normalize connection options, defaults, and validation outcomes, so I can fail fast on invalid endpoint, credential, certificate, and timeout configuration.

**Expected Behavior / Usage:**

The adapter receives JSON containing only the externally supplied values needed for this behavior, such as WebDAV multistatus XML, server URL, requested path, property descriptors, connection options, status codes, or error data depending on the feature. It prints newline-delimited fields that expose the observable result: ordered resource rows, metadata fields, XML request bodies, byte counts, HTTP request details, validation status, or normalized error records. Errors are rendered as neutral `error=<category>` records with separate data fields rather than host-language exception names or runtime messages.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_connection_settings.json`

```json
{
    "description": "Normalize connection configuration, apply defaults, and report validation results or normalized validation errors.",
    "cases": [
        {
            "input": {
                "options": {
                    "server": "http://localhost:8585",
                    "login": "alice",
                    "password": "secret1234"
                }
            },
            "expected_output": "timeout=30\nroot=\nis_valid=true\nvalid=true\n"
        },
        {
            "input": {
                "options": {
                    "server": "http://localhost:8585",
                    "login": "alice",
                    "password": "secret1234",
                    "timeout": 60
                }
            },
            "expected_output": "timeout=60\nroot=\nis_valid=true\nvalid=true\n"
        }
    ]
}
```

---

### Feature 6: HTTP Request Execution

**As a developer**, I want to translate a remote operation into concrete HTTP request details and status handling, so I can observe the wire-level method, URL, headers, timeout, and normalized status errors.

**Expected Behavior / Usage:**

The adapter receives JSON containing only the externally supplied values needed for this behavior, such as WebDAV multistatus XML, server URL, requested path, property descriptors, connection options, status codes, or error data depending on the feature. It prints newline-delimited fields that expose the observable result: ordered resource rows, metadata fields, XML request bodies, byte counts, HTTP request details, validation status, or normalized error records. Errors are rendered as neutral `error=<category>` records with separate data fields rather than host-language exception names or runtime messages.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_http_request_execution.json`

```json
{
    "description": "Execute one WebDAV HTTP action against a session and render the resulting request details or normalized HTTP error.",
    "cases": [
        {
            "input": {
                "options": {
                    "server": "http://localhost:8585",
                    "login": "alice",
                    "password": "secret1234"
                },
                "action": "list",
                "path": "",
                "response_status": 200,
                "session_has_auth": true
            },
            "expected_output": "result=response_returned\nrequest_count=2\nrequest[0].method=GET\nrequest[0].url=http://localhost:8585\nrequest[1].method=PROPFIND\nrequest[1].url=http://localhost:8585\nrequest[1].header.Accept=*/*\nrequest[1].header.Depth=1\nrequest[1].timeout=30\nrequest[1].verify=true\n"
        }
    ]
}
```

---

### Feature 7: Domain Error Output

**As a developer**, I want to render domain errors as language-neutral structured fields, so I can make failures portable across implementations and test runners.

**Expected Behavior / Usage:**

The adapter receives JSON containing only the externally supplied values needed for this behavior, such as WebDAV multistatus XML, server URL, requested path, property descriptors, connection options, status codes, or error data depending on the feature. It prints newline-delimited fields that expose the observable result: ordered resource rows, metadata fields, XML request bodies, byte counts, HTTP request details, validation status, or normalized error records. Errors are rendered as neutral `error=<category>` records with separate data fields rather than host-language exception names or runtime messages.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_exception_rendering.json`

```json
{
    "description": "Render domain error objects into language-neutral stdout categories with structured fields.",
    "cases": [
        {
            "input": {
                "error_kind": "invalid_option",
                "namespace": "Namespace/",
                "name": "Name",
                "value": "Value"
            },
            "expected_output": "error=invalid_option\nnamespace=Namespace/\nname=Name\nvalue=Value\n"
        },
        {
            "input": {
                "error_kind": "local_resource_not_found",
                "path": "Path"
            },
            "expected_output": "error=local_resource_not_found\npath=Path\n"
        },
        {
            "input": {
                "error_kind": "remote_resource_not_found",
                "path": "Path"
            },
            "expected_output": "error=remote_resource_not_found\npath=Path\n"
        }
    ]
}
```

---

### Feature 8: XML Serialization

**As a developer**, I want to serialize an XML tree with a UTF-8 declaration, so I can produce stable XML wire-format bodies.

**Expected Behavior / Usage:**

The adapter receives JSON containing only the externally supplied values needed for this behavior, such as WebDAV multistatus XML, server URL, requested path, property descriptors, connection options, status codes, or error data depending on the feature. It prints newline-delimited fields that expose the observable result: ordered resource rows, metadata fields, XML request bodies, byte counts, HTTP request details, validation status, or normalized error records. Errors are rendered as neutral `error=<category>` records with separate data fields rather than host-language exception names or runtime messages.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_xml_serialization.json`

```json
{
    "description": "Serialize an XML element tree with a UTF-8 XML declaration.",
    "cases": [
        {
            "input": {
                "root_name": "test"
            },
            "expected_output": "<?xml version='1.0' encoding='UTF-8'?>\n<test/>\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the standard WebDAF structure used in the list action examples
- use the default DAV quota response format for propfind
