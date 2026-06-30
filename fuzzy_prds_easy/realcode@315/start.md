## Product Requirement Document

# Binary Collaboration Protocol Toolkit - File, Chat, User, News, and Transfer Wire Contracts

## Project Goal

Build a protocol toolkit that allows developers to parse, render, and route binary collaboration-server messages without hand-writing brittle byte manipulation, path sanitation, permission checks, and transfer framing.

---

## Background & Problem

Without this library/tool, developers are forced to manually assemble binary frames, split network streams, normalize client-supplied paths, enforce chat and file permissions, and serialize metadata records. This leads to repetitive code, security mistakes, incompatible wire payloads, and hard-to-maintain server behavior.

With this library/tool, developers can express protocol operations through clear domain inputs while the system produces deterministic wire-format outputs and protocol-visible replies.

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

### Feature 1: Protocol Path Encoding

**As a developer, I want to encode human-readable file paths into the wire path format**, so I can send file and folder locations over the protocol.

**Expected Behavior / Usage:**

The input is an object with `operation` set to `path_encoding` and a slash-separated relative `path`. The output reports the number of path components and the complete encoded byte sequence as lowercase hexadecimal. Each path component is length-prefixed in the encoded payload, and multi-segment paths preserve segment order.

**Test Cases:** `rcb_tests/public_test_cases/feature1_path_encoding.json`

```json
{
    "description": "Encodes one or more slash-separated path segments into the protocol path byte format.",
    "cases": [
        {
            "input": {
                "operation": "path_encoding",
                "path": "kitten1.jpg"
            },
            "expected_output": "item_count=1\nencoded_hex=000100000b6b697474656e312e6a7067\n"
        },
        {
            "input": {
                "operation": "path_encoding",
                "path": "foo/kitten1.jpg"
            },
            "expected_output": "item_count=2\nencoded_hex=000200[uses entry-specific padding logic requiring test case inspection]666f6f00000b6b697474656e312e6a7067\n"
        }
    ]
}
```

---

### Feature 2: Safe File Path Resolution

**As a developer, I want to combine a configured file root with protocol path bytes and a file name**, so I can locate files without allowing traversal outside the root.

**Expected Behavior / Usage:**

The input is an object with `operation` set to `safe_path_resolution`, a `root`, optional `file_path` bytes, and optional `file_name` bytes. The output is the resolved absolute path. Traversal fragments in either the encoded folder path or file name are normalized away so the final path remains under the configured root; malformed encoded path bytes produce `error=invalid_path_bytes`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_safe_path_resolution.json`

```json
{
    "description": "Combines a configured file root, an encoded optional folder path, and an optional file name while stripping traversal segments.",
    "cases": [
        {
            "input": {
                "operation": "safe_path_resolution",
                "root": "/srv/files",
                "file_path": [],
                "file_name": [
                    102,
                    111,
                    111
                ]
            },
            "expected_output": "resolved_path=/srv/files/foo\n"
        },
        {
            "input": {
                "operation": "safe_path_resolution",
                "root": "/srv/files",
                "file_path": [],
                "file_name": [
                    46,
                    46,
                    47,
                    46,
                    46,
                    47,
                    46,
                    46,
                    47,
                    102,
                    111,
                    111
                ]
            },
            "expected_output": "resolved_path=/srv/files/foo\n"
        },
        {
            "input": {
                "operation": "safe_path_resolution",
                "root": "/srv/files",
                "file_path": [
                    0,
                    2,
                    0,
                    0,
                    3,
                    46,
                    46,
                    47,
                    0,
                    0,
                    8,
                    65,
                    32,
                    83,
                    117,
                    98,
                    68,
                    105,
                    114
                ],
                "file_name": [
                    102,
                    111,
                    111
                ]
            },
            "expected_output": "resolved_path=/srv/files/A SubDir/foo\n"
        },
        {
            "input": {
                "operation": "safe_path_resolution",
                "root": "/srv/files",
                "file_path": [],
                "file_name": []
            },
            "expected_output": "resolved_path=/srv/files\n"
        }
    ]
}
```

---

### Feature 3: File List Header Rendering

**As a developer, I want to render file and directory list entries as protocol header payloads**, so clients can distinguish item type and location.

**Expected Behavior / Usage:**

The input is an object with `operation` set to `file_header_payload`, an item `name`, and an `is_dir` flag. The output reports the item kind, the two-byte payload size as hexadecimal, and the complete header payload as lowercase hexadecimal. Regular files and directories share the same encoded path format but use different type bytes.

**Test Cases:** `rcb_tests/public_test_cases/feature3_file_header_payload.json`

```json
{
    "description": "Builds a file-list item header that distinguishes regular files from directories and embeds the encoded path payload.",
    "cases": [
        {
            "input": {
                "operation": "file_header_payload",
                "name": "foo",
                "is_dir": false
            },
            "expected_output": "kind=file\nsize_hex=000a\npayload_hex=000a0000000100[uses entry-specific padding logic requiring test case inspection]666f6f\n"
        },
        {
            "input": {
                "operation": "file_header_payload",
                "name": "foo",
                "is_dir": true
            },
            "expected_output": "kind=directory\nsize_hex=000a\npayload_hex=000a0001000100[uses entry-specific padding logic requiring test case inspection]666f6f\n"
        }
    ]
}
```

---

### Feature 4: Transaction Field List Decoding

**As a developer, I want to decode transaction field lists**, so I can inspect typed protocol parameters safely.

**Expected Behavior / Usage:**

The input is an object with `operation` set to `field_list_decoding`, a two-byte `param_count`, and raw field-list `bytes`. The output reports each decoded field ID, declared size, and data bytes as lowercase hexadecimal. Empty field lists decode to zero fields. Truncated fields or trailing undeclared bytes produce `error=malformed_field_list`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_field_list_decoding.json`

```json
{
    "description": "Decodes transaction field lists according to the declared parameter count and rejects malformed trailing or truncated data.",
    "cases": [
        {
            "input": {
                "operation": "field_list_decoding",
                "param_count": [
                    0,
                    2
                ],
                "bytes": [
                    0,
                    101,
                    0,
                    4,
                    1,
                    2,
                    3,
                    4,
                    0,
                    102,
                    0,
                    2,
                    0,
                    1
                ]
            },
            "expected_output": "field_count=2\nfield_0_id=101\nfield_0_size=4\nfield_0_data_hex=01020304\nfield_1_id=102\nfield_1_size=2\nfield_1_data_hex=0001\n"
        },
        {
            "input": {
                "operation": "field_list_decoding",
                "param_count": [
                    0,
                    0
                ],
                "bytes": []
            },
            "expected_output": "field_count=0\n"
        },
        {
            "input": {
                "operation": "field_list_decoding",
                "param_count": [
                    0,
                    1
                ],
                "bytes": [
                    0,
                    101,
                    0,
                    4,
                    1,
                    2,
                    3
                ]
            },
            "expected_output": "error=malformed_field_list\n"
        },
        {
            "input": {
                "operation": "field_list_decoding",
                "param_count": [
                    0,
                    1
                ],
                "bytes": [
                    0,
                    101,
                    0,
                    2,
                    1,
                    2,
                    3
                ]
            },
            "expected_output": "error=malformed_field_list\n"
        }
    ]
}
```

---

### Feature 5: Transaction Frame Scanning

**As a developer, I want to split a byte stream into complete transaction frames**, so partial network reads do not produce premature messages.

**Expected Behavior / Usage:**

The input is an object with `operation` set to `transaction_frame_scan`, raw stream `bytes`, and an `at_eof` flag. The output reports how many bytes are consumed and the emitted token bytes as lowercase hexadecimal. If there are too few bytes to determine or complete a frame, no bytes are consumed and the token is empty; extra bytes after a complete frame remain unconsumed.

**Test Cases:** `rcb_tests/public_test_cases/feature5_transaction_frame_scanning.json`

```json
{
    "description": "Scans a byte stream and emits exactly one complete transaction frame when enough bytes are available.",
    "cases": [
        {
            "input": {
                "operation": "transaction_frame_scan",
                "bytes": [],
                "at_eof": false
            },
            "expected_output": "advance=0\ntoken_hex=\n"
        },
        {
            "input": {
                "operation": "transaction_frame_scan",
                "bytes": [
                    0,
                    1,
                    0,
                    0,
                    0,
                    0,
                    0,
                    4,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    16,
                    0,
                    0,
                    0,
                    16
                ],
                "at_eof": false
            },
            "expected_output": "advance=0\ntoken_hex=\n"
        },
        {
            "input": {
                "operation": "transaction_frame_scan",
                "bytes": [
                    0,
                    1,
                    0,
                    0,
                    0,
                    0,
                    0,
                    4,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    16,
                    0,
                    0,
                    0,
                    16,
                    0,
                    2,
                    0,
                    108,
                    0,
                    2,
                    99,
                    59,
                    0,
                    107,
                    0,
                    4,
                    0,
                    2,
                    147,
                    71,
                    1,
                    1,
                    1
                ],
                "at_eof": false
            },
            "expected_output": "advance=36\ntoken_hex=00010000000000040000000000000010000000100002006c0002633b006b000400029347\n"
        }
    ]
}
```

---

### Feature 6: File Transfer Header Decoding

**As a developer, I want to parse file-transfer handshakes**, so transfer connections can be accepted only when the wire header is valid.

**Expected Behavior / Usage:**

The input is an object with `operation` set to `transfer_header_decoding` and raw header `bytes`. The output reports bytes read, the four-character protocol marker, transfer reference bytes, and declared data size. Headers with an invalid protocol marker or fewer than the required header bytes produce `error=invalid_transfer_header`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_transfer_header_decoding.json`

```json
{
    "description": "Parses file-transfer handshake headers and rejects invalid protocol markers or truncated headers.",
    "cases": [
        {
            "input": {
                "operation": "transfer_header_decoding",
                "bytes": [
                    72,
                    84,
                    88,
                    70,
                    0,
                    0,
                    0,
                    1,
                    0,
                    0,
                    0,
                    2,
                    0,
                    0,
                    0,
                    0
                ]
            },
            "expected_output": "bytes_read=16\nprotocol=HTXF\nreference_hex=00000001\ndata_size=2\n"
        },
        {
            "input": {
                "operation": "transfer_header_decoding",
                "bytes": [
                    17,
                    17,
                    17,
                    17,
                    0,
                    0,
                    0,
                    1,
                    0,
                    0,
                    0,
                    2,
                    0,
                    0,
                    0,
                    0
                ]
            },
            "expected_output": "error=invalid_transfer_header\n"
        },
        {
            "input": {
                "operation": "transfer_header_decoding",
                "bytes": [
                    72,
                    84,
                    88,
                    70,
                    0,
                    0,
                    0,
                    1,
                    0,
                    0,
                    0,
                    2,
                    0,
                    0,
                    0
                ]
            },
            "expected_output": "error=invalid_transfer_header\n"
        }
    ]
}
```

---

### Feature 7: User Identity Records and Credential Obfuscation

**As a developer**, I want to decode user identity bytes and transform credential text, so I can interoperate with protocol clients that use compact user records and reversible credential obfuscation.

**Expected Behavior / Usage:**

*7.1 User Record Decoding — Decodes fixed and variable user identity fields from a compact record.*

The input is an object with `operation` set to `user_record_decoding` and raw record `bytes`. The output reports user ID, icon, flags, and display name. The fixed-width binary fields are rendered as lowercase hexadecimal and the display name is rendered as text.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_user_record_decoding.json`

```json
{
    "description": "Decodes a compact protocol user record into its observable identifier, icon, flags, and display name fields.",
    "cases": [
        {
            "input": {
                "operation": "user_record_decoding",
                "bytes": [
                    0,
                    1,
                    7,
                    208,
                    0,
                    1,
                    0,
                    3,
                    97,
                    97,
                    97
                ]
            },
            "expected_output": "id_hex=0001\nicon_hex=07d0\nflags_hex=0001\nname=aaa\n"
        }
    ]
}
```

*7.2 Credential Obfuscation — Converts between readable credentials and protocol obfuscation bytes.*

The input is an object with `operation` set to `credential_obfuscation`. When `bytes` are supplied, the output is `decoded=<text>`; when `text` is supplied, the output is `encoded_hex=<hex>`. The transformation is reversible and byte-wise.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_credential_obfuscation.json`

```json
{
    "description": "Converts between clear-text credential strings and the protocol byte-wise obfuscation format.",
    "cases": [
        {
            "input": {
                "operation": "credential_obfuscation",
                "bytes": [
                    152,
                    138,
                    154,
                    140,
                    139
                ]
            },
            "expected_output": "decoded=guest\n"
        },
        {
            "input": {
                "operation": "credential_obfuscation",
                "text": "guest"
            },
            "expected_output": "encoded_hex=988a9a8c8b\n"
        },
        {
            "input": {
                "operation": "credential_obfuscation",
                "text": "foo1"
            },
            "expected_output": "encoded_hex=999090ce\n"
        }
    ]
}
```

---

### Feature 8: File Metadata Record Encoding

**As a developer, I want to serialize and parse file metadata records**, so file name listings carry type, creator, size, and name information.

**Expected Behavior / Usage:**

The input is an object with `operation` set to `file_name_info_encoding`. Supplying metadata fields renders the complete record as `encoded_hex`; supplying record `bytes` renders the parsed type, creator, file-size bytes, and name. The record preserves the four-byte type and creator identifiers and the declared file size bytes.

**Test Cases:** `rcb_tests/public_test_cases/feature8_file_name_info_encoding.json`

```json
{
    "description": "Serializes and parses file metadata records containing type, creator, byte size, and name.",
    "cases": [
        {
            "input": {
                "operation": "file_name_info_encoding",
                "file_type": [
                    84,
                    69,
                    88,
                    84
                ],
                "creator": [
                    84,
                    84,
                    88,
                    84
                ],
                "file_size": [
                    0,
                    67,
                    22,
                    211
                ],
                "name": "foo"
            },
            "expected_output": "encoded_hex=5445585454545854004316d3000000000000[uses entry-specific padding logic requiring test case inspection]666f6f\n"
        },
        {
            "input": {
                "operation": "file_name_info_encoding",
                "bytes": [
                    84,
                    69,
                    88,
                    84,
                    84,
                    84,
                    88,
                    84,
                    0,
                    67,
                    22,
                    211,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    14,
                    65,
                    117,
                    100,
                    105,
                    111,
                    110,
                    46,
                    97,
                    112,
                    112,
                    46,
                    122,
                    105,
                    112
                ]
            },
            "expected_output": "type=TEXT\ncreator=TTXT\nfile_size_hex=004316d3\nname=Audion.app.zip\n"
        }
    ]
}
```

---

### Feature 9: News Category Entry Encoding

**As a developer, I want to render news category-list entries**, so clients can display bundles and categories consistently.

**Expected Behavior / Usage:**

The input is an object with `operation` set to `news_category_encoding`, `category_type` bytes, `name`, and `article_count`. The output is the serialized entry as lowercase hexadecimal. Bundle entries contain type, count, and name; category entries additionally include stable observable serial-number fields and a generated identifier whose bytes are normalized in the contract.

**Test Cases:** `rcb_tests/public_test_cases/feature9_news_category_encoding.json`

```json
{
    "description": "Serializes news category-list entries for bundle and category entry types with deterministic observable bytes.",
    "cases": [
        {
            "input": {
                "operation": "news_category_encoding",
                "category_type": [
                    0,
                    2
                ],
                "name": "foo",
                "article_count": 1
            },
            "expected_output": "encoded_hex=0002000103666f6f\n"
        },
        {
            "input": {
                "operation": "news_category_encoding",
                "category_type": [
                    0,
                    3
                ],
                "name": "foo",
                "article_count": 1
            },
            "expected_output": "encoded_hex=[uses entry-specific padding logic requiring test case inspection]000100000000000000000000000000000000000000010000000203666f6f\n"
        }
    ]
}
```

---

### Feature 10: Tracker Registration Payload

**As a developer, I want to build tracker registration messages**, so a server can advertise itself with connection and descriptive metadata.

**Expected Behavior / Usage:**

The input is an object with `operation` set to `tracker_registration_payload`, port bytes, user count, pass identifier, name, and description. The output is the complete registration payload as lowercase hexadecimal, including the protocol version marker, port, user count, pass identifier, and length-prefixed text fields.

**Test Cases:** `rcb_tests/public_test_cases/feature10_tracker_registration_payload.json`

```json
{
    "description": "Builds a tracker-registration payload advertising a server port, user count, pass identifier, name, and description.",
    "cases": [
        {
            "input": {
                "operation": "tracker_registration_payload",
                "port": [
                    0,
                    16
                ],
                "user_count": 2,
                "pass_id": [
                    0,
                    0,
                    0,
                    1
                ],
                "name": "Test Serv",
                "description": "Fooz"
            },
            "expected_output": "payload_hex=0001001000020000000000010954657374205365727604466f6f7a\n"
        }
    ]
}
```

---

### Feature 11: Chat Message Delivery

**As a developer, I want chat messages to be routed according to permissions and chat scope**, so only eligible clients receive the correct protocol notifications.

**Expected Behavior / Usage:**

The input is an object with `operation` set to `chat_delivery`, sender permission state, sender name bytes, message text, optional chat mode, optional chat ID, and recipient read-access flags. The output lists generated transactions with recipients, reply flags, transaction types, error codes, and field payloads. Public messages go to recipients with chat-read access, emote messages use the emote text format, private messages go only to members of the private chat, and a sender without send permission receives a protocol error reply.

**Test Cases:** `rcb_tests/public_test_cases/feature11_chat_delivery.json`

```json
{
    "description": "Routes public and private chat messages to eligible recipients and renders denied sends as protocol error replies.",
    "cases": [
        {
            "input": {
                "operation": "chat_delivery",
                "has_permission": true,
                "user_name": [
                    0,
                    1
                ],
                "text": "hai",
                "client_read_access": [
                    true,
                    true
                ]
            },
            "expected_output": "transaction_count=2\ntransaction_0_recipient=0001\ntransaction_0_reply=0\ntransaction_0_type=106\ntransaction_0_error_code=00000000\ntransaction_0_field_count=1\ntransaction_0_field_0_id=101\ntransaction_0_field_0_data_hex=0d202020202020202020202000013a2020686169\ntransaction_1_recipient=0002\ntransaction_1_reply=0\ntransaction_1_type=106\ntransaction_1_error_code=00000000\ntransaction_1_field_count=1\ntransaction_1_field_0_id=101\ntransaction_1_field_0_data_hex=0d202020202020202020202000013a2020686169\n"
        },
        {
            "input": {
                "operation": "chat_delivery",
                "has_permission": false,
                "user_name": [
                    0,
                    1
                ],
                "text": "hai"
            },
            "expected_output": "transaction_count=1\ntransaction_0_recipient=\ntransaction_0_reply=1\ntransaction_0_type=0\ntransaction_0_error_code=00000001\ntransaction_0_field_count=1\ntransaction_0_field_0_id=100\ntransaction_0_field_0_data_hex=596f7520617265206e6f7420616c6c6f77656420746f20706172746963697061746520696e20636861742e\n"
        },
        {
            "input": {
                "operation": "chat_delivery",
                "has_permission": true,
                "user_name": [
                    84,
                    101,
                    115,
                    116,
                    121,
                    32,
                    77,
                    99,
                    84,
                    101,
                    115,
                    116
                ],
                "text": "performed action",
                "mode": "emote",
                "client_read_access": [
                    true,
                    true
                ]
            },
            "expected_output": "transaction_count=2\ntransaction_0_recipient=0001\ntransaction_0_reply=0\ntransaction_0_type=106\ntransaction_0_error_code=00000000\ntransaction_0_field_count=1\ntransaction_0_field_0_id=101\ntransaction_0_field_0_data_hex=0d2a2a2a205465737479204d635465737420706572666f726d656420616374696f6e\ntransaction_1_recipient=0002\ntransaction_1_reply=0\ntransaction_1_type=106\ntransaction_1_error_code=00000000\ntransaction_1_field_count=1\ntransaction_1_field_0_id=101\ntransaction_1_field_0_data_hex=0d2a2a2a205465737479204d635465737420706572666f726d656420616374696f6e\n"
        },
        {
            "input": {
                "operation": "chat_delivery",
                "has_permission": true,
                "user_name": [
                    0,
                    1
                ],
                "text": "hai",
                "client_read_access": [
                    true,
                    false
                ]
            },
            "expected_output": "transaction_count=1\ntransaction_0_recipient=0001\ntransaction_0_reply=0\ntransaction_0_type=106\ntransaction_0_error_code=00000000\ntransaction_0_field_count=1\ntransaction_0_field_0_id=101\ntransaction_0_field_0_data_hex=0d202020202020202020202000013a2020686169\n"
        },
        {
            "input": {
                "operation": "chat_delivery",
                "has_permission": true,
                "user_name": [
                    0,
                    1
                ],
                "text": "hai",
                "chat_id": [
                    0,
                    0,
                    0,
                    1
                ],
                "client_read_access": [
                    true,
                    false,
                    false
                ]
            },
            "expected_output": "transaction_count=2\ntransaction_0_recipient=0001\ntransaction_0_reply=0\ntransaction_0_type=106\ntransaction_0_error_code=00000000\ntransaction_0_field_count=2\ntransaction_0_field_0_id=114\ntransaction_0_field_0_data_hex=00000001\ntransaction_0_field_1_id=101\ntransaction_0_field_1_data_hex=0d202020202020202020202000013a2020686169\ntransaction_1_recipient=0002\ntransaction_1_reply=0\ntransaction_1_type=106\ntransaction_1_error_code=00000000\ntransaction_1_field_count=2\ntransaction_1_field_0_id=114\ntransaction_1_field_0_data_hex=00000001\ntransaction_1_field_1_id=101\ntransaction_1_field_1_data_hex=0d202020202020202020202000013a2020686169\n"
        }
    ]
}
```

---

### Feature 12: Folder Creation Requests

**As a developer, I want folder creation requests to honor permissions and root-safe paths**, so clients can create folders without escaping the configured file area.

**Expected Behavior / Usage:**

The input is an object with `operation` set to `folder_creation`, permission state, root, file name bytes, and optional encoded folder path bytes. The output lists the protocol reply transaction. Without permission, the reply is an error transaction; with permission, the reply is a successful folder-creation transaction. Traversal fragments in names or encoded path components are normalized before creating the folder.

**Test Cases:** `rcb_tests/public_test_cases/feature12_folder_creation.json`

```json
{
    "description": "Creates folders under the configured file root, sanitizes traversal in path inputs, and returns either a success reply or a permission error reply.",
    "cases": [
        {
            "input": {
                "operation": "folder_creation",
                "has_permission": false,
                "root": "/Files",
                "file_name": [
                    116,
                    101,
                    115,
                    116,
                    70,
                    111,
                    108,
                    100,
                    101,
                    114
                ]
            },
            "expected_output": "transaction_count=1\ntransaction_0_recipient=0001\ntransaction_0_reply=1\ntransaction_0_type=0\ntransaction_0_error_code=00000001\ntransaction_0_field_count=1\ntransaction_0_field_0_id=100\ntransaction_0_field_0_data_hex=596f7520617265206e6f7420616c6c6f77656420746f2063726561746520666f6c646572732e\n"
        },
        {
            "input": {
                "operation": "folder_creation",
                "has_permission": true,
                "root": "/Files",
                "file_name": [
                    116,
                    101,
                    115,
                    116,
                    70,
                    111,
                    108,
                    100,
                    101,
                    114
                ]
            },
            "expected_output": "transaction_count=1\ntransaction_0_recipient=0001\ntransaction_0_reply=1\ntransaction_0_type=205\ntransaction_0_error_code=00000000\ntransaction_0_field_count=0\n"
        },
        {
            "input": {
                "operation": "folder_creation",
                "has_permission": true,
                "root": "/Files",
                "file_path": [
                    0,
                    1,
                    0,
                    0,
                    3,
                    97,
                    97,
                    97
                ],
                "file_name": [
                    116,
                    101,
                    115,
                    116,
                    70,
                    111,
                    108,
                    100,
                    101,
                    114
                ]
            },
            "expected_output": "transaction_count=1\ntransaction_0_recipient=0001\ntransaction_0_reply=1\ntransaction_0_type=205\ntransaction_0_error_code=00000000\ntransaction_0_field_count=0\n"
        },
        {
            "input": {
                "operation": "folder_creation",
                "has_permission": true,
                "root": "/Files",
                "file_name": [
                    46,
                    46,
                    47,
                    46,
                    46,
                    47,
                    116,
                    101,
                    115,
                    116,
                    70,
                    111,
                    108,
                    100,
                    101,
                    114
                ]
            },
            "expected_output": "transaction_count=1\ntransaction_0_recipient=0001\ntransaction_0_reply=1\ntransaction_0_type=205\ntransaction_0_error_code=00000000\ntransaction_0_field_count=0\n"
        },
        {
            "input": {
                "operation": "folder_creation",
                "has_permission": true,
                "root": "/Files",
                "file_path": [
                    0,
                    2,
                    0,
                    0,
                    3,
                    46,
                    46,
                    47,
                    0,
                    0,
                    3,
                    102,
                    111,
                    111
                ],
                "file_name": [
                    116,
                    101,
                    115,
                    116,
                    70,
                    111,
                    108,
                    100,
                    101,
                    114
                ]
            },
            "expected_output": "transaction_count=1\ntransaction_0_recipient=0001\ntransaction_0_reply=1\ntransaction_0_type=205\ntransaction_0_error_code=00000000\ntransaction_0_field_count=0\n"
        }
    ]
}
```

---

### Feature 13: File Download Transfer

**As a developer, I want a queued file download transfer to write a flattened file payload**, so file contents and metadata can be streamed over the transfer channel.

**Expected Behavior / Usage:**

The input is an object with `operation` set to `file_download_transfer`. The output reports that no error occurred, the number of bytes written, the flattened-file format marker, and boolean signals confirming that the payload contains the requested file name and a data-fork marker. These signals verify that the transfer path produces a real protocol payload rather than bypassing transfer framing.

**Test Cases:** `rcb_tests/public_test_cases/feature13_file_download_transfer.json`

```json
{
    "description": "Serves a valid queued file download through the file-transfer channel and writes a flattened file payload.",
    "cases": [
        {
            "input": {
                "operation": "file_download_transfer"
            },
            "expected_output": "error=none\nbytes_written=165\nformat=FILP\ncontains_name=true\ncontains_data_fork=true\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_path_encoding.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_path_encoding@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- apply the emote marker pattern used in the games module
- trigger if the incoming packet can't fulfill the header expectations
