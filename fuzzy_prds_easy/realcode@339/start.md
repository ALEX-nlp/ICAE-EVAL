## Product Requirement Document

# In-Memory Archive & Compression Toolkit — Checksums, Byte Codecs, and Container Formats

## Project Goal

Build a self-contained library for reading and writing the common building blocks of file archives entirely in memory: integrity checksums, low-level byte cursors and writers, the general-purpose compression codecs, and the multi-file container formats layered on top of them. The library must let a program turn bytes into a compressed/archived blob and back again, and parse archives produced by external tools, without touching the filesystem or shelling out to native utilities.

---

## Background & Problem

Archive and compression handling is usually delegated to platform-specific native tools, which makes behavior non-portable and hard to test. This project instead implements the whole stack in one place:

- **Integrity checksums** — CRC-32 and Adler-32, exposed both as a one-shot function over a byte sequence and as an incremental streaming object that can be fed in chunks and then finalized.
- **Byte plumbing** — a positioned input cursor that reads bytes, fixed-width integers, blocks, NUL-terminated and fixed-length text, and supports peeking, skipping, rewinding, and non-copying windowed sub-views; and a growable output buffer that appends bytes and fixed-width little-endian integers.
- **Compression codecs** — DEFLATE/INFLATE (raw, with a one-shot and a chunk-streamed decode path), and the ZLIB, GZIP, BZIP2, and XZ container formats, each able to round-trip data and to decode streams produced by external tools.
- **Archive containers** — TAR (parsing several historical dialects, GNU long names, and symbolic links; plus encode/round-trip) and ZIP (round-trip with optional stored entries, parsing externally-produced archives including zip64 and non-ASCII names, and decrypting ZipCrypto password-protected archives), plus an ordered in-memory archive collection with replace-by-name and clear semantics.

Everything is deterministic and content-addressable: binary results are reported by their length and CRC-32 (or, for small blobs, by hexadecimal bytes), so outputs can be compared exactly without depending on byte-for-byte compressor internals.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain spans several distinct responsibilities (checksums, byte I/O, multiple compression codecs, multiple container formats); it MUST therefore be organized as a clear, multi-file directory tree (e.g. `src/`, `lib/`, `tests/`) rather than a single monolithic file. Do not over-engineer, but strictly avoid a god file.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box testing contract** for an execution adapter, NOT the internal data model of the core library. The core logic must remain decoupled from stdin/stdout and JSON parsing. A thin execution adapter is solely responsible for translating one JSON command into idiomatic calls on the core library and rendering the result.

3. **Adherence to SOLID Design Principles:** Separate parsing/routing, the checksum engines, the byte codecs, the compression codecs, and the container parsers into distinct cohesive units. The core engines must be open for extension (new check types, new formats) but closed for modification, and high-level code must depend on abstractions rather than I/O details.

4. **Robustness & Interface Design:** The public interface must be idiomatic to the target language and hide internal complexity. Malformed input (e.g. bytes that are not a valid archive) must be handled gracefully by raising a proper, distinguishable [a low-level fault or standard error message] rather than producing a bogus result or crashing with a low-level fault.

---

## Execution Adapter I/O Contract

The execution adapter reads exactly **one JSON object** from stdin and writes the rendered result to stdout. The object always carries a string field `op` selecting the operation; the remaining fields are operation-specific and described per feature below. Output is plain text: one `key=value` line per reported field, each terminated by a newline (`\n`). Hexadecimal is always lowercase.

**Byte-sequence encoding.** Wherever a field denotes a sequence of bytes, it may be given in any of three interchangeable forms:

- a JSON array of integers in `0..255` (e.g. `[1, 2, 3]`);
- an object `{"b64": "<base64>"}` whose value is the standard base64 encoding of the bytes;
- an object `{"pattern": "mod256", "length": N, "mod": M}` denoting the `N`-byte sequence whose i-th byte is `i % M` (`M` defaults to 256). This compact form lets large buffers be specified without inlining them.

**Error reporting.** When an operation cannot complete because its input is invalid (for example, parsing bytes that are not a valid archive), the adapter prints a single neutral line `[a low-level fault or standard error message]=<category>` followed by a newline, instead of any normal output. It must never leak a host-language stack trace or exception class name.

---

## Core Features

### Feature 1: CRC-32 Checksum

#### 1.1 One-Shot CRC-32 Value

**As a developer**, I want the CRC-32 of a byte sequence as a single value, so I can verify integrity in one call.

**Expected Behavior / Usage:**

For `op` = `crc32_value`, the adapter computes the CRC-32 checksum of the bytes in `data` and prints `crc32=<value>` where the value is the 32-bit checksum as a fixed eight-digit lowercase hexadecimal number. An optional integer `repeat` feeds the same `data` sequence that many times, accumulating the running checksum across repetitions (so the result equals the CRC-32 of `data` concatenated `repeat` times). The checksum of an empty sequence is zero.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_crc32_value.json`

```json
{
    "description": "Compute the CRC-32 checksum of a sequence of bytes and report it as a fixed eight-digit lowercase hexadecimal value. An optional repeat count feeds the same byte sequence that many times, accumulating the running checksum across repetitions so a large input can be expressed compactly.",
    "cases": [
        {
            "input": {
                "op": "crc32_value",
                "data": [
                    1
                ]
            },
            "expected_output": "crc32=a505df1b\n"
        },
        {
            "input": {
                "op": "crc32_value",
                "data": [
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    7,
                    8,
                    9,
                    0
                ]
            },
            "expected_output": "crc32=c5f5be65\n"
        }
    ]
}
```

#### 1.2 Streaming CRC-32 Digest

**As a developer**, I want to compute a CRC-32 incrementally by feeding chunks, then finalize, so I can checksum data I do not hold all at once.

**Expected Behavior / Usage:**

For `op` = `crc32_digest`, the adapter feeds the bytes in `data` (repeated `repeat` times if given) through a streaming checksum object and then finalizes it. The finalized digest is the four **big-endian** bytes of the resulting 32-bit checksum; it is printed as `digest=<value>`, an eight-digit lowercase hexadecimal number. For any given input this equals the one-shot CRC-32 value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_crc32_stream.json`

```json
{
    "description": "Compute a CRC-32 checksum incrementally by feeding one or more chunks of bytes through a streaming checksum object, then finalize it. The finalized digest is the four big-endian bytes of the 32-bit checksum, reported as a fixed eight-digit lowercase hexadecimal value. An optional repeat count adds the same chunk that many times before finalizing.",
    "cases": [
        {
            "input": {
                "op": "crc32_digest",
                "data": [
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    7,
                    8,
                    9,
                    0
                ]
            },
            "expected_output": "digest=c5f5be65\n"
        }
    ]
}
```

### Feature 2: Adler-32 Checksum

#### 2.1 One-Shot Adler-32 Value

**As a developer**, I want the Adler-32 of a byte sequence as a single value, so I can use the lighter-weight checksum that backs zlib.

**Expected Behavior / Usage:**

For `op` = `adler32_value`, the adapter computes the Adler-32 checksum of `data` and prints `adler32=<value>` as a fixed eight-digit lowercase hexadecimal number. The checksum of an empty sequence is the initial seed value `1`. An optional integer `repeat` feeds `data` that many times, accumulating the running checksum.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_adler32_value.json`

```json
{
    "description": "Compute the Adler-32 checksum of a sequence of bytes and report it as a fixed eight-digit lowercase hexadecimal value. The checksum of an empty input is the initial seed value. An optional repeat count feeds the same byte sequence that many times, accumulating the running checksum.",
    "cases": [
        {
            "input": {
                "op": "adler32_value",
                "data": []
            },
            "expected_output": "adler32=[a hard-coded initial seed value for Adler-32]\n"
        },
        {
            "input": {
                "op": "adler32_value",
                "data": [
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    7,
                    8,
                    9,
                    0
                ]
            },
            "expected_output": "adler32=00dc002e\n"
        }
    ]
}
```

#### 2.2 Streaming Adler-32 Digest

**As a developer**, I want to compute an Adler-32 incrementally and finalize it, mirroring the streaming CRC-32 object.

**Expected Behavior / Usage:**

For `op` = `adler32_digest`, the adapter feeds `data` (repeated `repeat` times if given) through a streaming Adler-32 object and finalizes it. The finalized digest is the four big-endian bytes of the 32-bit checksum, printed as `digest=<value>` in eight-digit lowercase hexadecimal.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_adler32_stream.json`

```json
{
    "description": "Compute an Adler-32 checksum incrementally by feeding one or more chunks of bytes through a streaming checksum object, then finalize it. The finalized digest is the four big-endian bytes of the 32-bit checksum, reported as a fixed eight-digit lowercase hexadecimal value. An optional repeat count adds the same chunk that many times before finalizing.",
    "cases": [
        {
            "input": {
                "op": "adler32_digest",
                "data": [
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    7,
                    8,
                    9,
                    0
                ]
            },
            "expected_output": "digest=00dc002e\n"
        }
    ]
}
```

### Feature 3: Byte Input Cursor

#### 3.1 Positioned Byte Reader

**As a developer**, I want a cursor over an in-memory buffer that advances as I consume data and supports look-ahead, skipping, and rewind, so I can parse binary layouts.

**Expected Behavior / Usage:**

For `op` = `read`, the adapter builds a cursor over the bytes in `data` and executes the command list in `program` in order against it. Each command either advances the cursor and/or emits one labelled line:

- `"len"` — emit `len=<remaining>`, the number of bytes not yet consumed (does not advance).
- `"byte"` — read one byte; emit `byte=<hh>` as two lowercase hex digits.
- `{"peek": N}` — look ahead at the next `N` bytes without advancing; emit `peek=<hex>` (the bytes concatenated as hex).
- `{"skip": N}` — advance the cursor by `N` bytes, emitting nothing.
- `{"block": N}` — read `N` bytes; emit `block=<hex>`.
- `"string"` — read a NUL-terminated text run (consuming the terminator); emit `str=<text>` verbatim.
- `{"string": N}` — read exactly `N` bytes as text; emit `str=<text>`.
- `"reset"` — rewind the cursor to the start, emitting nothing.
- `"eos"` — emit `eos=<true|false>`, whether the cursor is at end of stream.

Lines appear in command order.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_byte_reader.json`

```json
{
    "description": "Read from an in-memory byte buffer using a positioned cursor that advances as data is consumed. A program of read commands is executed in order against one buffer. Commands include: report the number of bytes remaining; read a single byte; look ahead at the next N bytes without advancing the cursor; advance the cursor by N bytes without reading; read a block of N bytes; read a NUL-terminated text run; read a fixed number of bytes as text; rewind the cursor to the start; and report whether the cursor is at end of stream. Each command that yields a value emits one labelled line; single bytes and byte blocks are reported in lowercase hexadecimal, text is reported verbatim.",
    "cases": [
        {
            "input": {
                "op": "read",
                "data": [
                    170,
                    187,
                    204
                ],
                "program": [
                    "len",
                    "byte",
                    "byte",
                    "byte",
                    "eos"
                ]
            },
            "expected_output": "len=3\nbyte=aa\nbyte=bb\nbyte=cc\neos=true\n"
        },
        {
            "input": {
                "op": "read",
                "data": [
                    84,
                    101,
                    115,
                    116,
                    0
                ],
                "program": [
                    "string",
                    "eos",
                    "reset",
                    {
                        "string": 4
                    },
                    "byte",
                    "eos"
                ]
            },
            "expected_output": "str=Test\neos=true\nstr=Test\nbyte=00\neos=true\n"
        }
    ]
}
```

#### 3.2 Fixed-Width Integer Decode

**As a developer**, I want to decode a fixed-width unsigned integer from the front of a buffer under either byte order, so I can read binary headers.

**Expected Behavior / Usage:**

For `op` = `read_int`, the adapter takes the integer `width` in bytes (one of 2, 3, 4, 8) and decodes the first `width` bytes of `data` as an unsigned integer under both byte orders. It prints two lines: `le=<hex>` for the little-endian interpretation and `be=<hex>` for the big-endian interpretation, each padded to the integer's full byte width (`2*width` hex digits).

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_fixed_integers.json`

```json
{
    "description": "Decode a fixed-width unsigned integer from the front of a byte buffer under both little-endian and big-endian byte orders, given the width in bytes (2, 3, 4, or 8). The same buffer is interpreted under each byte order and the two decoded values are reported as hexadecimal, each padded to the integer's full byte width.",
    "cases": [
        {
            "input": {
                "op": "read_int",
                "data": [
                    170,
                    187,
                    204,
                    221,
                    238
                ],
                "width": 2
            },
            "expected_output": "le=bbaa\nbe=aabb\n"
        },
        {
            "input": {
                "op": "read_int",
                "data": [
                    170,
                    187,
                    204,
                    221,
                    238,
                    255,
                    238,
                    221
                ],
                "width": 8
            },
            "expected_output": "le=ddeeffeeddccbbaa\nbe=aabbccddeeffeedd\n"
        }
    ]
}
```

#### 3.3 Non-Copying Windowed Sub-Views

**As a developer**, I want independent windowed views over a shared buffer that each track their own position without copying, so I can hand a bounded slice to a sub-parser.

**Expected Behavior / Usage:**

For `op` = `read_subset`, the adapter reads one byte from the base cursor over `data`, then takes a sub-view of a fixed length at the current position, and a further sub-view at an offset within that sub-view. Reading through each view advances only that view's own cursor. The adapter emits, in order, the bytes yielded by the first sub-view as `sub1=<hh>` lines, then `eos=<true|false>` for that first sub-view, then the bytes yielded by the second sub-view as `sub2=<hh>` lines.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_subset_views.json`

```json
{
    "description": "Create independent windowed views over a shared byte buffer without copying. After reading one byte from the base buffer, a sub-view of a given length is taken at the current position, and a further sub-view is taken at an offset within that sub-view. Reading through each view advances only that view's own cursor; the bytes yielded by each view and the end-of-stream state of the first view are reported.",
    "cases": [
        {
            "input": {
                "op": "read_subset",
                "data": [
                    170,
                    187,
                    204,
                    221,
                    238
                ]
            },
            "expected_output": "sub1=bb\nsub1=cc\nsub1=dd\neos=true\nsub2=cc\nsub2=dd\n"
        }
    ]
}
```

### Feature 4: Byte Output Buffer

#### 4.1 Growable Byte Writer

**As a developer**, I want to append bytes one at a time to a growable buffer and read back its size and checksum, so I can assemble binary output.

**Expected Behavior / Usage:**

For `op` = `write_bytes_ramp`, the adapter appends `count` bytes to a growable output buffer, where the i-th byte written (0-based) is `i % mod`. It then prints `length=<n>` (the total bytes written) and `crc32=<value>` (the CRC-32 of the buffer contents as eight-digit lowercase hex).

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_byte_writer.json`

```json
{
    "description": "Append bytes one at a time to a growable in-memory output buffer, then report the total number of bytes written and the CRC-32 checksum of the resulting buffer as eight-digit hexadecimal. The input specifies how many bytes to write; each byte's value is its index taken modulo a given base.",
    "cases": [
        {
            "input": {
                "op": "write_bytes_ramp",
                "count": 10000,
                "mod": 256
            },
            "expected_output": "length=10000\ncrc32=d1ffc4fc\n"
        }
    ]
}
```

#### 4.2 Fixed-Width Integer Writer

**As a developer**, I want to append fixed-width little-endian integers to the output buffer, so I can serialize numeric fields.

**Expected Behavior / Usage:**

For `op` = `write_ints`, the adapter appends `count` unsigned integers of `width` bytes each in little-endian order to a growable buffer; the i-th integer written (0-based) is `base + i`. It then prints `length=<n>` (total bytes = `count*width`) and `crc32=<value>` of the buffer as eight-digit lowercase hex.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_integer_writer.json`

```json
{
    "description": "Append fixed-width unsigned integers in little-endian byte order to a growable output buffer, then report the total byte length and the CRC-32 checksum of the buffer as eight-digit hexadecimal. The input specifies the integer width in bytes, how many integers to write, and a base value; the i-th integer written is the base plus i.",
    "cases": [
        {
            "input": {
                "op": "write_ints",
                "width": 2,
                "count": 65535,
                "base": 0
            },
            "expected_output": "length=131070\ncrc32=c7624fe6\n"
        }
    ]
}
```

### Feature 5: DEFLATE / INFLATE

#### 5.1 DEFLATE Round-Trip

**As a developer**, I want to compress a buffer with raw DEFLATE at a chosen level and decompress it back, so I get lossless compression independent of level.

**Expected Behavior / Usage:**

For `op` = `deflate_roundtrip`, the adapter compresses the bytes in `data` with DEFLATE at the given integer `level`, then decompresses the result. The recovered bytes must equal the original regardless of level. It prints `length=<n>` and `crc32=<value>` of the recovered bytes (the compressed size, which is implementation-dependent, is intentionally not reported).

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_deflate_roundtrip.json`

```json
{
    "description": "Compress a byte buffer with the DEFLATE algorithm at a given compression level, then decompress the result. The recovered bytes must equal the original input regardless of level. The output reports the length and CRC-32 of the recovered bytes.",
    "cases": [
        {
            "input": {
                "op": "deflate_roundtrip",
                "data": {
                    "pattern": "mod256",
                    "length": 1048575
                },
                "level": 9
            },
            "expected_output": "length=1048575\ncrc32=04a8505f\n"
        }
    ]
}
```

#### 5.2 Chunk-Streamed INFLATE

**As a developer**, I want to decompress DEFLATE data incrementally, feeding the compressed stream in fixed-size chunks and pulling out decoded blocks, so I can decode without buffering the whole stream.

**Expected Behavior / Usage:**

For `op` = `inflate_stream`, the adapter first produces a DEFLATE stream of `data` at the given `level`, then decodes it incrementally by feeding the compressed bytes in fixed-size chunks of `chunk` bytes and concatenating the decoded output as it becomes available. The recovered bytes must equal the original. It prints `length=<n>` and `crc32=<value>` of the recovered bytes.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_streamed_inflate.json`

```json
{
    "description": "Decompress DEFLATE data incrementally: the compressed stream is fed in fixed-size chunks and decoded blocks are pulled out as they become available, then concatenated. The recovered bytes must equal the original uncompressed input. The output reports the length and CRC-32 of the recovered bytes. The input gives the original data, the compression level used to produce the stream, and the streaming chunk size.",
    "cases": [
        {
            "input": {
                "op": "inflate_stream",
                "data": {
                    "pattern": "mod256",
                    "length": 1048575
                },
                "level": 0,
                "chunk": 1049
            },
            "expected_output": "length=1048575\ncrc32=04a8505f\n"
        }
    ]
}
```

#### 5.3 ZLIB Block Decode

**As a developer**, I want to decode a single zlib-wrapped DEFLATE block produced by an external tool, so I can read data others compressed.

**Expected Behavior / Usage:**

For `op` = `zlib_decode`, the adapter decodes the zlib-wrapped (DEFLATE inside a zlib header/checksum envelope) bytes in `data`, recovering the original. It prints `length=<n>` and `crc32=<value>` of the decoded bytes.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_zlib_block_decode.json`

```json
{
    "description": "Decode a single zlib-wrapped (DEFLATE inside a zlib header/checksum envelope) block produced by an external tool, recovering the original bytes. The output reports the length and CRC-32 of the decoded bytes.",
    "cases": [
        {
            "input": {
                "op": "zlib_decode",
                "data": {
                    "b64": "eJydy1EKAiEQANB/T+EFitHRVIgo+ugc42i7C5kxuNv1i47Q/3tDatXRJ8SYLBdjHGUGtuRyyEjWcynsguECqagXSX0OHQNm97W1Bm9TZiSuhLWAyxByZntIFvjOitYxd9E3WoU2fZlI3vTQx0m2M8/S27K2fZfppA1GjB6SdXoHEUBxb20Zo/6V1fW3tVcf4dVEDJ8NeJydy0sKAjEMANB9T9ELKG2TNhFEFBeeI7aZDzhWSme8vuIRXD9eb6o2oCcpRQ+ZCsngxAEA+TQIpEgQUyHFLGJe0vTZLSMhJ8XCUQIoJUbm4IFiCGlILtwzfxGNrH2qzd5kbbLZyyjtLQ97HNt2zlOry7wu+9rGk/XAwNHxwdudY+dMrssy965/ZXP9bYvmA7jKQgufDXicnctLCsIwEADQfU6RCyiTz9QZEFFceI5JmrQFa2RI6/UFj+Dbv66lWBmQ0eUxZ1ewOhkpevQBcSB0IWGKAJEJzVu0vLrlREF84ixAhYnrAN5XBo+uVM+1nhJzdNHI1uem9iGbym5vk+hHnvY86X7Ns7Z12dZj0+liXaBACBTQHoAATG7ruvRe/srm/ts2mC+f3UIHnw14nJ3LQQ7CIBAAwDuv2A9oYOkCTYzRePAdCwttEyuG0Pp9jU/wOIfpLWfgbAnRFE2CI0WywQ8+DhJHE4oN2kouhpjUi1t+dojWJ4kkTqMhh2SMFP+FGDcwspY0csYSFG99rg3uvDXe4Tpxe/MDTlPbL2ludV229VjbdAZjgw2kvUM46KC1SnVdl97zX1ndfhtQfQDx9UKZnwp4nJ3LSwrCMBAA0H1OMRdQZkzzKUhRuvAcYyamBUNgSOr1BY/g27+uOUMg8YHohXMUsdY7TpmEbeTnRE6QZ2F0QQyPvjWFBw/lA+6F9cNvuBY9bmnTVvdRz03LAmSjjQ7DxcMJI6JJrda99/xXNutvA5kvsWI1ia4CeJwzNDAwMzFRKEhMzo5Py8xJjS9JLS7RK6koYbi96uS30L2FGfySYbf8HHvSO4/VNAIAiukS8LcFeJwLycgsVgCikoxUhZLU4hKFtPwihYLE5GyFtMyc1GI9rhCogrLUouLM/DwFI4X8NLAcppQJQgoALC0dW60FeJwzNDAwMzFRKEhMzo5Py8xJjc/MS0mt0CupKGHguaYe1lDXsWrLhY4lG/8bVHRXhLw2RFdeklpcAlZ9e9XJb6F7CzP4JcNu+Tn2pHceq2kEAKpMJru4A3icC8nILFYAokSFktTiEoW0/CKFgsTkbIXMvJTUCoW0zJzUYj2uEKiistSi4sz8PAUjPS4ALGoTA60FeJwzNDAwMzFRKEhMzo5Py8xJjc/MS0mt0CupKGE4U3H9TsgdveQJsWtfs63dw+H2+6SyIbryktTiErDq2slHFz19d4xD24mt6cO/O5/unnfZAADEPyjXtQJ4nAvJyCxWAKJEhZLU4hKFtPwihYLE5GyFzLyU1AqFtMyc1GI9LgD1vAy/ZIFYeJwLt5lgAwADcAFgrgJ4nDM0MDAzMVEoSEzOjk/LzEmNL0ktLtErqShhqJ18dNHTd8c4tJ3Ymj78u/Pp7nmXDQCUfBUErgJ4nDM0MDAzMVEoSEzOjk/LzEmNL0ktLtE="
                }
            },
            "expected_output": "length=223\ncrc32=6be8ada0\n"
        }
    ]
}
```

### Feature 6: ZLIB Container

#### 6.1 ZLIB Round-Trip

**As a developer**, I want to wrap data in the zlib container and decode it back with checksum verification, so I can interoperate with zlib streams.

**Expected Behavior / Usage:**

For `op` = `zlib_roundtrip`, the adapter compresses `data` into the zlib container format and decompresses it again (verifying the embedded Adler-32). It prints `length=<n>` and `crc32=<value>` of the recovered bytes, which must equal the original.

**Test Cases:** `rcb_tests/public_test_cases/feature6_zlib_roundtrip.json`

```json
{
    "description": "Compress a byte buffer into the zlib container format, then decompress it with checksum verification. The recovered bytes must equal the original. The output reports the length and CRC-32 of the recovered bytes.",
    "cases": [
        {
            "input": {
                "op": "zlib_roundtrip",
                "data": {
                    "pattern": "mod256",
                    "length": 10000
                }
            },
            "expected_output": "length=10000\ncrc32=d1ffc4fc\n"
        }
    ]
}
```

### Feature 7: GZIP Container

#### 7.1 GZIP Round-Trip

**As a developer**, I want to compress data into the gzip container and decode it back with trailer verification.

**Expected Behavior / Usage:**

For `op` = `gzip_roundtrip`, the adapter compresses `data` into the gzip container format and decompresses it again (verifying the embedded CRC-32 and length trailer). It prints `length=<n>` and `crc32=<value>` of the recovered bytes, which must equal the original.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_gzip_roundtrip.json`

```json
{
    "description": "Compress a byte buffer into the gzip container format, then decompress it with checksum verification. The recovered bytes must equal the original. The output reports the length and CRC-32 of the recovered bytes.",
    "cases": [
        {
            "input": {
                "op": "gzip_roundtrip",
                "data": {
                    "pattern": "mod256",
                    "length": 10000
                }
            },
            "expected_output": "length=10000\ncrc32=d1ffc4fc\n"
        }
    ]
}
```

#### 7.2 GZIP Decode

**As a developer**, I want to decode a gzip stream produced by an external tool, validating its trailer.

**Expected Behavior / Usage:**

For `op` = `gzip_decode`, the adapter decodes the gzip stream in `data`, validating the embedded CRC-32 and length trailer, and prints `length=<n>` and `crc32=<value>` of the decoded bytes.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_gzip_decode.json`

```json
{
    "description": "Decompress a gzip stream produced by an external tool, validating the embedded CRC-32 and length trailer. The output reports the length and CRC-32 of the decoded bytes.",
    "cases": [
        {
            "input": {
                "op": "gzip_decode",
                "data": {
                    "b64": "H4sICKX6wVIAA2MudHh0ACvJyCxWAKJEhZLU4hKu/DSFkoxUrqrMAoXEouSMzLJUrrT8otzEEj2uEhqoBADyvDukfgAAAA=="
                }
            },
            "expected_output": "length=126\ncrc32=a43bbcf2\n"
        }
    ]
}
```

### Feature 8: BZIP2 Container

#### 8.1 BZIP2 Round-Trip

**As a developer**, I want to compress data with bzip2 and decode it back with checksum verification.

**Expected Behavior / Usage:**

For `op` = `bzip2_roundtrip`, the adapter compresses `data` with the bzip2 algorithm and decompresses it again (verifying the per-block checksums). It prints `length=<n>` and `crc32=<value>` of the recovered bytes, which must equal the original.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_bzip2_roundtrip.json`

```json
{
    "description": "Compress a byte buffer with the bzip2 algorithm, then decompress it with checksum verification. The recovered bytes must equal the original. The output reports the length and CRC-32 of the recovered bytes.",
    "cases": [
        {
            "input": {
                "op": "bzip2_roundtrip",
                "data": {
                    "pattern": "mod256",
                    "length": 10000
                }
            },
            "expected_output": "length=10000\ncrc32=d1ffc4fc\n"
        }
    ]
}
```

#### 8.2 BZIP2 Decode

**As a developer**, I want to decode a bzip2 stream produced by an external tool, verifying its block checksums.

**Expected Behavior / Usage:**

For `op` = `bzip2_decode`, the adapter decodes the bzip2 stream in `data`, verifying the per-block checksums, and prints `length=<n>` and `crc32=<value>` of the decoded bytes.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_bzip2_decode.json`

```json
{
    "description": "Decompress a bzip2 stream produced by an external tool, verifying the per-block checksums. The output reports the length and CRC-32 of the decoded bytes.",
    "cases": [
        {
            "input": {
                "op": "bzip2_decode",
                "data": {
                    "b64": "QlpoOTFBWSZTWeBLR58AANVfgFQSaO/AHzelnJr/79/6UAM6yvapyaaVhJJJkehPUBpPUYNJ6Q0A0BkbSAGinip6p+go09EaMAAAAADQBIkIkYg9TxQAaDQ0AAADQ4AYAAAAAAAAABKaIUegieIjJpG1HqDENAAB5TKCSogS1cOWD6jrseG5ZxmJZ3SomxpTY6VFZKp4ktrhJRMCSiElj4nAsPVockNG49I+L3NE6KuorI/iVKChwakygfBMz9xn1h7SyvFx1tHGHyi9+LHDfpUWIeVTmomlJVkY3mchrUYTo4CiqST42COiIMZhW6432r9DnsSj4olJrHFS+KlSZ72TJqg3YzTGSMswSBGzkS6LMDKT0AfdmgDntYBqs4IErwlXXtRAE8RTBjgoDcDUT2CYmuaRjzsLuY6SlxwKFxIwVohCqSmnSewvG5ImQVs5YCFAaZzQ0Fcc2G0OzvdsFqcRlveoD+jwrK+eiU7iYoGtTH1Ew/xcNYa6WHRPGMmWG0TGbmlN7cOikYrnRYXWGZhwsulyqcfm6VYNQ90EkdoZC0Y3mknyLJqTXj6TFh0SWhmDueqEkIXAoOkmckPBK9M+acJFPV2Z+RbuZoolANYzwMd71Bxenc4HaQmTgalFzoqUpmnIbrmi+HIkrBw02dOArmQfmwvHaqG1IySIrVhaoarW5zSisSM6YowhdOhhazjaBcdDnUZhztQLsE8B5dxfJBvTCW5mCwcke+DDiIObK/d3n0mGTIGsL+Ypn3q900jZUYre0D+bQqE+Nc5rSCrG3ZqDdv9qBjfa0beozmLtPRPYxUmM6dwlAVb7MUJxxQk4ftyhVjkWNfEoBNN00bbwx4UqJjeskVmS0smlOiJDkprGss+q4goNJg5ZqtLj5a4YwIMsk4OJIguZ21JkCAroN5hQwvY9dlf/wNHNl1j4CJGYFnJEMhEodNDLZK4uMVUpmnsoqL1KiULclMloRaOswQQprEiu53U7KBYyMzeRmfbjUYoSoQ2J4FYJNfTrMXHIPCZzmm3EoOJnNBCH9zbIC97ZQVkhqbEiowsykurtJ/8XckU4UJDgS0ef"
                },
                "verify": true
            },
            "expected_output": "length=1773\ncrc32=82e415c7\n"
        }
    ]
}
```

### Feature 9: XZ Decode

#### 9.1 XZ Stream Decode

**As a developer**, I want to decode an xz stream produced by an external tool, regardless of which integrity-check type its container declares.

**Expected Behavior / Usage:**

For `op` = `xz_decode`, the adapter decodes the xz stream in `data` and prints `length=<n>` and `crc32=<value>` of the decoded bytes. The xz container may declare no integrity check or one of several check types (CRC-32, CRC-64, or SHA-256); when the container carries a check, it must validate. An empty xz stream decodes to zero bytes (`length=0`, `crc32=00000000`).

**Test Cases:** `rcb_tests/public_test_cases/feature9_xz_decode.json`

```json
{
    "description": "Decompress an xz stream produced by an external tool. The xz container may carry no integrity check or one of several check types (CRC-32, CRC-64, or SHA-256); when checksum verification is requested the embedded check must validate. An empty xz stream decodes to no bytes. The output reports the length and CRC-32 of the decoded bytes.",
    "cases": [
        {
            "input": {
                "op": "xz_decode",
                "data": {
                    "b64": "/Td6WFoAAATm1rRGAAAAABzfRCEftvN9AQAAAAAEWVo="
                }
            },
            "expected_output": "length=0\ncrc32=00000000\n"
        },
        {
            "input": {
                "op": "xz_decode",
                "data": {
                    "b64": "/Td6WFoAAATm1rRGAgAhARYAAAB0L+WjAQAFaGVsbG8KAAAApWCX8ZT2/eAAAR4GwS+kHR+2830BAAAAAARZWg=="
                }
            },
            "expected_output": "length=6\ncrc32=363a3020\n"
        }
    ]
}
```

### Feature 10: TAR Container

#### 10.1 TAR Header Parsing (Multiple Dialects)

**As a developer**, I want to parse a tar archive and read normalized header metadata for every entry, across the historical tar dialects.

**Expected Behavior / Usage:**

For `op` = `tar_decode`, the adapter parses the tar archive in `data` and prints `files=<count>` followed, for each entry in order, by a block of header fields: `name`, `mode` (numeric permission bits as a decimal integer), `uid`, `gid`, `size`, `modtime` (modification time as a Unix timestamp), `type` (the single-character type flag), `uname`, `gname`, and `link` (the linked-file name, empty when none). Old GNU, star, and classic V7 dialects must all parse into the same normalized fields.

**Test Cases:** `rcb_tests/public_test_cases/feature10_1_tar_headers.json`

```json
{
    "description": "Parse a tar archive and report, for every entry in order, its header metadata: the entry name, the numeric permission mode, owner and group numeric ids, the byte size, the modification time as a Unix timestamp, the single-character type flag, the owner and group names, and the linked-file name. Several historical tar dialects (old GNU, star, classic V7) must all be parsed into the same normalized header fields.",
    "cases": [
        {
            "input": {
                "op": "tar_decode",
                "data": {
                    "b64": "UDEwNTAyMzguSlBHLmxvZwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADAwMDA2NjQAAAAAAAAAAAAAAAAAAAAAADAwMDAwMDAwMDE2ADEyMTMwNjI3NzY2ADAxMjc3NwAgMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB1c3RhciAgAGV5ZWZpAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAZXllZmkAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAxMjEzMDQwNDIwMAAxMjEzMDYyNzc2NgAAAAAAAAAAAAAAAAA0NCw0NCxQT1dFUk9OAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="
                },
                "verify": true
            },
            "expected_output": "files=1\nname=P1050238.JPG.log\nmode=436\nuid=0\ngid=0\nsize=14\nmodtime=1365454838\ntype=0\nuname=eyefi\ngname=eyefi\nlink=\n"
        }
    ]
}
```

#### 10.2 TAR GNU Long Name

**As a developer**, I want a tar entry whose name exceeds the fixed header field to be reconstructed in full via the GNU long-name extension.

**Expected Behavior / Usage:**

For `op` = `tar_decode`, when the archive in `data` stores a file name longer than the fixed header name field using the GNU long-name extension, the reported `name` must be the fully reconstructed long name. All other header fields are reported as in feature 10.1.

**Test Cases:** `rcb_tests/public_test_cases/feature10_2_tar_long_name.json`

```json
{
    "description": "Parse a tar archive that stores a file name longer than the fixed header name field using the GNU long-name extension, and report the reconstructed full entry name and header metadata.",
    "cases": [
        {
            "input": {
                "op": "tar_decode",
                "data": {
                    "b64": "Li8uL0BMb25nTGluawAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADAwMDA2NDQAMDAwMDAwMAAwMDAwMDAwADAwMDAwMDAwMjMzADAwMDAwMDAwMDAwADAxMTYwMQAgTAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB1c3RhciAgAHJvb3QAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcm9vdAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHgudHh0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHgwMDAwNzc3ADAwMDE3NTAAMDAwMTc1MAAwMDAwMDAwMDAwNAAxMzQyMDUyNjIzNwAwNDAyMzEAIDAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAdXN0YXIgIABicmVuZGFuAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGJyZW5kYW4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAdGVzdAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="
                },
                "verify": true
            },
            "expected_output": "files=1\nname=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.txt\nmode=511\nuid=1000\ngid=1000\nsize=4\nmodtime=1547873439\ntype=0\nuname=brendan\ngname=brendan\nlink=\n"
        }
    ]
}
```

#### 10.3 TAR Symbolic Link

**As a developer**, I want a symbolic-link entry's type and link target reported, so I can distinguish links from regular files and directories.

**Expected Behavior / Usage:**

For `op` = `tar_decode`, an entry that is a symbolic link is reported with the type flag identifying a symbolic link and a `link` field naming the file it points to. Directory and regular-file entries in the same archive are reported with their own type flags and an empty `link`.

**Test Cases:** `rcb_tests/public_test_cases/feature10_3_tar_symlink.json`

```json
{
    "description": "Parse a tar archive containing a symbolic-link entry and report each entry's header metadata, including the type flag identifying the symbolic link and the name of the file it links to.",
    "cases": [
        {
            "input": {
                "op": "tar_decode",
                "data": {
                    "b64": "c3ltbGlua190YXIvAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADAwMDA3NzcAMDAwMTc1MAAwMDAxNzUwADAwMDAwMDAwMDAwADEzNDY1NzE2NDExADAxMzIzMgAgNQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB1c3RhciAgAGJyZW5kYW4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAYnJlbmRhbgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABzeW1saW5rX3Rhci9hAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMDAwMDc3NwAwMDAxNzUwADAwMDE3NTAAMDAwMDAwMDAwMDAAMTM0NjU3MTY0MTEAMDE0NTcxACAyYi9iLnR4dAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHVzdGFyICAAYnJlbmRhbgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABicmVuZGFuAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHN5bWxpbmtfdGFyL2IvAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAwMDAwNzc3ADAwMDE3NTAAMDAwMTc1MAAwMDAwMDAwMDAwMAAxMzQ2NTcxNjQwMAAwMTM0NTEAIDUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAdXN0YXIgIABicmVuZGFuAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGJyZW5kYW4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAc3ltbGlua190YXIvYi9iLnR4dAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADAwMDA2NjYAMDAwMTc1MAAwMDAxNzUwADAwMDAwMDAwMDE2ADEzNDY1NzE2NDAwADAxNDQzMAAgMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB1c3RhciAgAGJyZW5kYW4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAYnJlbmRhbgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB0ZXN0aW5nIDEgMiAzCgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="
                },
                "verify": true
            },
            "expected_output": "files=4\nname=symlink_tar/\nmode=511\nuid=1000\ngid=1000\nsize=0\nmodtime=1557634313\ntype=5\nuname=brendan\ngname=brendan\nlink=\nname=symlink_tar/a\nmode=511\nuid=1000\ngid=1000\nsize=0\nmodtime=1557634313\ntype=2\nuname=brendan\ngname=brendan\nlink=b/b.txt\nname=symlink_tar/b/\nmode=511\nuid=1000\ngid=1000\nsize=0\nmodtime=1557634304\ntype=5\nuname=brendan\ngname=brendan\nlink=\nname=symlink_tar/b/b.txt\nmode=438\nuid=1000\ngid=1000\nsize=14\nmodtime=1557634304\ntype=0\nuname=brendan\ngname=brendan\nlink=\n"
        }
    ]
}
```

#### 10.4 TAR Encode Round-Trip

**As a developer**, I want to build an archive from named byte entries, encode it to tar, and decode it back, recovering names and content.

**Expected Behavior / Usage:**

For `op` = `tar_roundtrip`, the adapter builds an in-memory archive from the `files` list (each `{name, content}`, where `content` is a byte sequence), encodes it to the tar format, then decodes the encoded bytes. It prints `files=<count>` followed by one `name=<name> content=<hex>` line per decoded entry, where `<hex>` is the entry content in lowercase hexadecimal. (Encoded tar bytes embed the current time, so only the recovered names and content are reported.)

**Test Cases:** `rcb_tests/public_test_cases/feature10_4_tar_roundtrip.json`

```json
{
    "description": "Build an archive in memory from named entries with byte content, encode it to the tar format, then decode the encoded bytes back into entries. The decoded entry names and content must match what was put in. The output reports the entry count and each decoded entry's name and content in hexadecimal.",
    "cases": [
        {
            "input": {
                "op": "tar_roundtrip",
                "files": [
                    {
                        "name": "file.txt",
                        "content": [
                            100
                        ]
                    }
                ]
            },
            "expected_output": "files=1\nname=file.txt content=64\n"
        }
    ]
}
```

#### 10.5 Invalid Archive Rejection

**As a developer**, I want parsing of bytes that are not a valid archive to fail cleanly with a neutral [a low-level fault or standard error message], not a bogus result.

**Expected Behavior / Usage:**

For `op` = `tar_invalid`, the adapter attempts to parse the bytes in `data` as a tar archive. Because the bytes are not a valid archive, parsing must fail and the adapter prints the single neutral line `[a low-level fault or standard error message]=invalid_archive`.

**Test Cases:** `rcb_tests/public_test_cases/feature10_5_tar_invalid.json`

```json
{
    "description": "Attempt to parse bytes that are not a valid tar archive. Parsing must fail rather than producing a bogus result; the failure is reported as a neutral [a low-level fault or standard error message] category line.",
    "cases": [
        {
            "input": {
                "op": "tar_invalid",
                "data": [
                    1,
                    2,
                    3
                ]
            },
            "expected_output": "[a low-level fault or standard error message]=invalid_archive\n"
        }
    ]
}
```

### Feature 11: ZIP Container

#### 11.1 ZIP Encode Round-Trip

**As a developer**, I want to build named byte entries, encode them to zip, and decode them back with checksum verification, including stored entries and non-ASCII names.

**Expected Behavior / Usage:**

For `op` = `zip_roundtrip`, the adapter builds an in-memory archive from the `files` list (each `{name, content}`, optionally with `"stored": true` to opt out of compression), encodes it to the zip format, then decodes the result verifying each entry's CRC-32. It prints `files=<count>` followed, per decoded entry in order, by `name=<name> size=<uncompressed-size> crc32=<value>`, where the CRC-32 is the eight-digit lowercase hex checksum of the entry content. Content of any byte shape and non-ASCII entry names round-trip correctly.

**Test Cases:** `rcb_tests/public_test_cases/feature11_1_zip_roundtrip.json`

```json
{
    "description": "Build an archive in memory from named entries with byte content, encode it to the zip format, then decode the encoded bytes back with checksum verification. Entries may opt out of compression (stored). Content of any byte shape is preserved, and non-ASCII entry names round-trip correctly. The output reports the decoded entry count and, per entry, the name, the uncompressed size, and the CRC-32 of the content.",
    "cases": [
        {
            "input": {
                "op": "zip_roundtrip",
                "files": [
                    {
                        "name": "abc.txt",
                        "content": [
                            104,
                            101,
                            108,
                            108,
                            111,
                            32,
                            119,
                            111,
                            114,
                            108,
                            100
                        ],
                        "compress": false
                    }
                ]
            },
            "expected_output": "files=1\nname=abc.txt size=11 crc32=0d4a1185\n"
        },
        {
            "input": {
                "op": "zip_roundtrip",
                "files": [
                    {
                        "name": "fileöäüÖÄÜß.txt",
                        "content": [
                            116,
                            101,
                            115,
                            116
                        ]
                    }
                ]
            },
            "expected_output": "files=1\nname=fileöäüÖÄÜß.txt size=4 crc32=d87f7e0c\n"
        }
    ]
}
```

#### 11.2 ZIP Decode (External Archives)

**As a developer**, I want to parse a zip archive produced by an external tool, reading its comment, entries, sizes, file/dir flags, and content checksums, including zip64 and non-ASCII names.

**Expected Behavior / Usage:**

For `op` = `zip_decode`, the adapter parses the zip archive in `data`. If the archive carries a comment, it first prints `comment=<text>`. It then prints `files=<count>` followed, per entry in order, by `name=<name> size=<uncompressed-size> isfile=<true|false> crc32=<value>`, where `isfile` is false for directory entries and the CRC-32 is the eight-digit lowercase hex checksum of the decompressed content. Stored and deflated entries, directory entries, non-ASCII names, and the zip64 size extension must all parse.

**Test Cases:** `rcb_tests/public_test_cases/feature11_2_zip_decode.json`

```json
{
    "description": "Parse a zip archive produced by an external tool and report the archive comment when present, the number of entries, and for each entry the name, the uncompressed size, whether it is a file (as opposed to a directory entry), and the CRC-32 of its decompressed content. Archives using stored and deflated entries, directory entries, non-ASCII names, and the zip64 size extension must all be parsed.",
    "cases": [
        {
            "input": {
                "op": "zip_decode",
                "data": {
                    "b64": "UEsDBBQAAAAIAIFhJT3A1+3DGQAAABoAAAAIABwAdGVzdC50eHRVVAkAA3H8gkx2/IJMdXgLAAEE9QEAAAQUAAAAC8nILFYAokSFktTiEiBRUaKQlpmTqscFAFBLAwQKAAAAAACdfiU9/jHVVBEDAAARAwAAFAAcAGdvcGhlcmNvbG9yMTZ4MTYucG5nVVQJAAM6MINMOzCDTHV4CwABBPUBAAAEFAAAAIlQTkcNChoKAAAADUlIRFIAAAAQAAAADwgGAAAA7XNPLwAAAARnQU1BAADW2NRPWDIAAAAZdEVYdFNvZnR3YXJlAEFkb2JlIEltYWdlUmVhZHlxyWU8AAACo0lEQVR42nSTX0hTURjAv3vP7sZ1W1baKiVtbAZRVvRfI7ciIrB6iEEPSwwKo4ICH2IaRS+hg3pJKoYVNf9kmJCikS4QnC9TksIH6baGKNpdtu1edQ7Zn9M5m42t8oPvnnu/P7/zfd85l8EYQ6bY7Xaw2WyXz506eiOv0FgUlORl38SXZSWHFJxWV+F2u72Z8YrMj5aWVvS6vc3haKi9ZDQa4LjlGtxvsENpkRakkATzbP4mEpYFYGgFNTU1EF6KwPDgQGfzC6fF6xVA/DoC5rNVoOIQxH+Og4LBcPtRV91Ww7bGWCxKNmtJESiAZZljBbp1HXdvVmFZCmHP6Cd85NBefKJsJ37TVI8nXM+wb8iJL1pOCuvzNrBmszmZRzXZgiaHLyvRbzHtMBbByIdWAKSEyordEIyqQaPVQjyRgHBkGc5XVpQIM/PXNxcUNGW1wDAMR95Lr14403/riiV/YXEJGBbBtF8G3docUKk4YEiASsmBo3MQHG09jfNSqI4C2BVQlOjY2/dDHUE5TLCk73gCijfmJpMCUjgJo5KnUcKCLPX9qYDNnOhcUL7zxNkzyauUKSqBkPmAd0oEYUaCaCwGuvxc6gr8F0BEetXlsvmmRUAo5YrG4rBvezGYdhUmw1fg6tUAEIvHXe7R8SVaenpQLEsfaSANWxVARBbnggss+69LoUDwwx+gBH/WTTQYDCkaSfrumwREVuavZGpjAUMwgpFas+Y0MTWnAR6PJxmkJWduq6tXewZ7ebobRxQhsnIKoEf7uLXv18dR4eXBA/tnsyooLy9PVyCKYkKSpNqn7f0PTYf35M7OTMO4MBV4NzDcixF/r7q6etJqtWb/TIIgZFa7SPS5yzNhHfvmj/A8/6C7u/szsYX0ej29dFmt/RZgAKgIDYsD52LqAAAAAElFTkSuQmCCUEsBAh4DFAAAAAgAgWElPcDX7cMZAAAAGgAAAAgAGAAAAAAAAQAAAKSBAAAAAHRlc3QudHh0VVQFAANx/IJMdXgLAAEE9QEAAAQUAAAAUEsBAh4DCgAAAAAAnX4lPf4x1VQRAwAAEQMAABQAGAAAAAAAAAAAAKSBWwAAAGdvcGhlcmNvbG9yMTZ4MTYucG5nVVQFAAM6MINMdXgLAAEE9QEAAAQUAAAAUEsFBgAAAAACAAIAqAAAALoDAAAaAFRoaXMgaXMgYSB6aXBmaWxlIGNvbW1lbnQu"
                },
                "verify": true
            },
            "expected_output": "comment=This is a zipfile comment.\nfiles=2\nname=test.txt size=26 isfile=true crc32=c3edd7c0\nname=gophercolor16x16.png size=785 isfile=true crc32=54d531fe\n"
        }
    ]
}
```

#### 11.3 ZIP Password Decrypt (ZipCrypto)

**As a developer**, I want to decrypt a ZipCrypto password-protected zip archive given the correct password.

**Expected Behavior / Usage:**

For `op` = `zip_decode` with a `password` field supplying the correct password, the adapter decrypts and verifies the contained entry. It prints `files=<count>` followed by `name=<name> size=<size> isfile=<true|false> crc32=<value>` for the entry, exactly as in feature 11.2.

**Test Cases:** `rcb_tests/public_test_cases/feature11_3_zip_password.json`

```json
{
    "description": "Parse a password-protected (ZipCrypto) zip archive given the correct password, decrypting and verifying the single contained entry. The output reports the entry count and the entry's name, size, file flag, and content CRC-32.",
    "cases": [
        {
            "input": {
                "op": "zip_decode",
                "data": {
                    "b64": "UEsDBBQAAQAAAHeyfk2FEUoNFwAAAAsAAAAJAAAAaGVsbG8udHh0xCjjneaUicGoX6Vr7B5B8DEP0U4wKx1QSwECPwAUAAEAAAB3sn5NhRFKDRcAAAALAAAACQAkAAAAAAAAACAAAAAAAAAAaGVsbG8udHh0CgAgAAAAAAABABgANSXf2j2J1AEOysLSPYnUAQ7KwtI9idQBUEsFBgAAAAABAAEAWwAAAD4AAAAAAA=="
                },
                "verify": true,
                "password": "test1234"
            },
            "expected_output": "files=1\nname=hello.txt size=11 isfile=true crc32=0d4a1185\n"
        }
    ]
}
```

### Feature 12: In-Memory Archive Collection

#### 12.1 Replace Entry By Name

**As a developer**, I want adding an entry whose name already exists to replace that entry in place, preserving order and count.

**Expected Behavior / Usage:**

For `op` = `archive_build`, the adapter adds each `{name, content}` from `files` in order to an ordered archive collection. When an added name already exists, the existing entry's content is replaced in place, without changing its position or the total count. It prints `length=<count>` followed by one `entry=<name> b0=<hh>` line per entry in order, where `<hh>` is the first content byte in two-digit lowercase hex.

**Test Cases:** `rcb_tests/public_test_cases/feature12_1_replace_file.json`

```json
{
    "description": "Maintain an ordered collection of named archive entries. Adding an entry whose name already exists replaces the existing entry's content in place without changing the order or count. The output reports the entry count and, in order, each entry's name and first content byte.",
    "cases": [
        {
            "input": {
                "op": "archive_build",
                "files": [
                    {
                        "name": "a",
                        "content": [
                            0
                        ]
                    },
                    {
                        "name": "b",
                        "content": [
                            1
                        ]
                    },
                    {
                        "name": "c",
                        "content": [
                            2
                        ]
                    },
                    {
                        "name": "b",
                        "content": [
                            3
                        ]
                    }
                ]
            },
            "expected_output": "length=3\nentry=a b0=00\nentry=b b0=03\nentry=c b0=02\n"
        }
    ]
}
```

#### 12.2 Clear Collection

**As a developer**, I want clearing the collection to remove all entries.

**Expected Behavior / Usage:**

For `op` = `archive_build` with `"clear": true`, the adapter adds the `files` entries and then clears the collection. It prints `length=<count>` (which is zero after clearing) and lists no entries.

**Test Cases:** `rcb_tests/public_test_cases/feature12_2_clear.json`

```json
{
    "description": "Clearing the collection removes all entries. The output reports the resulting entry count and lists no entries.",
    "cases": [
        {
            "input": {
                "op": "archive_build",
                "files": [
                    {
                        "name": "a",
                        "content": [
                            0
                        ]
                    },
                    {
                        "name": "b",
                        "content": [
                            1
                        ]
                    },
                    {
                        "name": "c",
                        "content": [
                            2
                        ]
                    }
                ],
                "clear": true
            },
            "expected_output": "length=0\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core Library:** A cleanly structured, multi-file codebase implementing the checksums, byte cursor/writer, compression codecs, and container formats above. The core logic must be decoupled from stdin/stdout and JSON parsing.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON object from stdin, dispatches on its `op` field to the core library, and prints the result to stdout following the per-feature contracts. Byte-sequence fields accept the array / `{"b64":...}` / `{"pattern":"mod256",...}` forms described in the I/O contract. Invalid input is rendered as a single neutral `[a low-level fault or standard error message]=<category>` line; native exceptions must never reach stdout.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `test_cases`) to choose the directory. For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` containing **only** the raw stdout of the program under test (no PASS/FAIL or metadata), so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- stream repeated data until end
- apply modulo streaming architecture
