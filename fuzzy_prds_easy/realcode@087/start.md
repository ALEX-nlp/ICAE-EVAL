## Product Requirement Document

# Object Storage REST Client — Request Signing, Addressing, and Response Parsing

## Project Goal

Build a client-side library for an object-storage REST API that lets developers authenticate requests, build bucket and object addresses, normalize request options into wire-format headers and query strings, and parse service XML/HTTP responses into structured domain data — all without hand-writing repetitive and error-prone protocol code.

---

## Background & Problem

Without this library, developers integrating with an object-storage REST service must manually canonicalize and sign every HTTP request, percent-encode object paths, choose between virtual-host and path-style bucket addressing, translate friendly option names into wire headers and query strings, and parse XML/HTTP responses by hand. This produces repetitive boilerplate, subtle authentication failures, inconsistent URL generation, and fragile, host-language-specific error handling.

With this library, a developer supplies ordinary request, bucket, object, and response data through a small idiomatic interface and receives deterministic wire-format outputs (authorization headers, signatures, URLs, normalized headers and query strings) and parsed domain fields (bucket lists, object listings, locations, copy results, object metadata) that conform to the storage protocol. Errors are surfaced as neutral, language-independent categories.

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

5. **Language-Neutral Error Reporting:** All error conditions surfaced through the contract MUST be reported as stable, language-independent category strings (e.g. `invalid_bucket_name`, `missing_credential`, `invalid_object_key`, `remote_error`). No host-language exception class names, stack traces, or runtime-specific suffixes may appear in stdout.

6. **Determinism:** Given identical input, the system MUST produce byte-for-byte identical stdout. Header and query outputs that require ordering MUST use the specified deterministic ordering (input order or name-sorted as noted per feature).

---

## Core Features

### Feature 1: Request Authorization Signature

**As a developer**, I want to produce a protocol-compatible authorization header for an HTTP request, so that my requests can be authenticated and accepted by the storage service.

**Expected Behavior / Usage:**

The input is an HTTP method, request path, host, headers, an access key id, and a secret access key. The output is a single `authorization` line containing the complete authorization header value for that request. Canonicalization must respect content headers (content-type, content-md5), date versus service-specific date headers, sub-resource query fields, virtual-host bucket addressing, repeated/custom metadata headers, and already percent-encoded paths.

**Test Cases:** `rcb_tests/public_test_cases/feature1_request_authorization_signatures.json`

```json
{
    "description": "Produce the protocol Authorization header value for a concrete HTTP request, given the request method, path, host, headers, and access credentials. The signing must respect content headers, date versus service-date headers, sub-resource query fields, virtual-host bucket addressing, repeated metadata headers, and already percent-encoded paths.",
    "cases": [
        {
            "input": {"feature": "request_signature", "method": "GET", "path": "/photos/puppy.jpg", "host": "johnsmith.s3.amazonaws.com", "headers": {"date": "Tue, 27 Mar 2007 19:36:42 +0000"}, "access_key_id": "0PN5J17HBGZHT7JJ3X82", "secret_access_key": "uV3F3YluFJax1cknvbcGwgjvx4QpvB+leU8dUj2o"},
            "expected_output": "authorization=AWS 0PN5J17HBGZHT7JJ3X82:xXjDGYUmKxnwqr5KXNPGldn5LbA=\n"
        },
        {
            "input": {"feature": "request_signature", "method": "PUT", "path": "/db-backup.dat.gz", "host": "static.johnsmith.net", "headers": {"user-agent": "curl/7.15.5", "date": "Tue, 27 Mar 2007 21:06:08 +0000", "x-amz-acl": "public-read", "content-type": "application/x-download", "content-md5": "4gJE4saaMU4BqNR0kLY+lw==", "x-amz-meta-reviewedby": "joe@johnsmith.net,jane@johnsmith.net", "x-amz-meta-filechecksum": "0x02661779", "x-amz-meta-checksumalgorithm": "crc32", "content-disposition": "attachment; filename=database.dat", "content-encoding": "gzip", "content-length": "5913339"}, "access_key_id": "0PN5J17HBGZHT7JJ3X82", "secret_access_key": "uV3F3YluFJax1cknvbcGwgjvx4QpvB+leU8dUj2o"},
            "expected_output": "authorization=AWS 0PN5J17HBGZHT7JJ3X82:C0FlOtU8Ylb9KDTpZqYkZPX91iI=\n"
        }
    ]
}
```

---

### Feature 2: Presigned Temporary Signature Component

**As a developer**, I want to compute the escaped signature token for a temporary, pre-authenticated object link, so that I can assemble shareable links safely.

**Expected Behavior / Usage:**

The input gives the bucket, the object resource path, the secret key, an absolute expiry timestamp, and optionally the HTTP method (defaulting to read), extra request headers, and whether the bucket is folded into the host. The output is a single `signature` line containing the URL-escaped HMAC signature token to embed into a temporary URL.

**Test Cases:** `rcb_tests/public_test_cases/feature2_presigned_url_signatures.json`

```json
{
    "description": "Produce the URL-escaped signature component used in a temporary, pre-authenticated link to an object. Input gives the bucket, the object resource path, the secret key, an absolute expiry timestamp, and optionally the HTTP method (default read), extra headers, and whether the bucket is folded into the host. Output is the single escaped signature token.",
    "cases": [
        {
            "input": {"feature": "temporary_signature", "bucket": "johnsmith", "resource": "photos/puppy.jpg", "secret_access_key": "uV3F3YluFJax1cknvbcGwgjvx4QpvB+leU8dUj2o", "expires_at": 1175046589},
            "expected_output": "signature=gs6xNznrLJ4Bd%2B1y9pcy2HOSVeg%3D\n"
        },
        {
            "input": {"feature": "temporary_signature", "bucket": "johnsmith", "resource": "photos/puppy.jpg", "secret_access_key": "uV3F3YluFJax1cknvbcGwgjvx4QpvB+leU8dUj2o", "expires_at": 1175046589, "method": "put", "headers": {"x-amz-acl": "public-read"}},
            "expected_output": "signature=SDMxjIkOKIVR47nWfJ57UNPXxFM%3D\n"
        }
    ]
}
```

---

### Feature 3: Complete Presigned URL

**As a developer**, I want to assemble a complete temporary object URL, so that clients can access a resource until a specified expiry without further credentials.

**Expected Behavior / Usage:**

The input is the bucket, object resource path, secret key, absolute expiry timestamp, and optionally the access key, HTTP method, headers, and a flag controlling whether the bucket appears in the hostname. The output is a single `url` line containing the full HTTP temporary URL with `AWSAccessKeyId`, `Expires`, and `Signature` query parameters. When the bucket is folded into the host it becomes a host prefix; otherwise it becomes a leading path segment.

**Test Cases:** `rcb_tests/public_test_cases/feature3_presigned_url_generation.json`

```json
{
    "description": "Assemble a complete temporary object URL combining the addressing style, the access key, the expiry timestamp, and the signature query fields. When the bucket is folded into the host the bucket becomes a host prefix; otherwise it becomes a leading path segment.",
    "cases": [
        {
            "input": {"feature": "temporary_url", "bucket": "johnsmith", "resource": "photos/puppy.jpg", "secret_access_key": "uV3F3YluFJax1cknvbcGwgjvx4QpvB+leU8dUj2o", "expires_at": 1175046589, "add_bucket_to_host": true},
            "expected_output": "url=http://johnsmith.s3.amazonaws.com/photos/puppy.jpg?AWSAccessKeyId=&Expires=1175046589&Signature=gs6xNznrLJ4Bd%2B1y9pcy2HOSVeg%3D\n"
        },
        {
            "input": {"feature": "temporary_url", "bucket": "johnsmith", "resource": "photos/puppy.jpg", "access_key": "0PN5J17HBGZHT7JJ3X82", "secret_access_key": "uV3F3YluFJax1cknvbcGwgjvx4QpvB+leU8dUj2o", "expires_at": 1175046589, "method": "put", "headers": {"x-amz-acl": "public-read"}},
            "expected_output": "url=http://s3.amazonaws.com/johnsmith/photos/puppy.jpg?AWSAccessKeyId=0PN5J17HBGZHT7JJ3X82&Expires=1175046589&Signature=SDMxjIkOKIVR47nWfJ57UNPXxFM%3D\n"
        }
    ]
}
```

---

### Feature 4: Query Parameter Normalization

**As a developer**, I want to emit only supported listing query parameters, so that request URLs remain valid and deterministic.

**Expected Behavior / Usage:**

The input is a map of candidate request query parameters. Only a fixed allow-list of listing parameters is emitted; every other key is dropped. Underscores in accepted keys become hyphens, a null value emits the bare key with no equals sign, and order follows the input order joined by ampersands. The output is one `query` line containing the exact query string, which may be empty.

**Test Cases:** `rcb_tests/public_test_cases/feature4_query_parameter_normalization.json`

```json
{
    "description": "Convert a map of request parameters into a wire-format query string. Only a fixed allow-list of listing parameters is emitted; every other key is dropped. Underscores in accepted keys become hyphens, a null value emits the bare key with no equals sign, and order follows the input order joined by ampersands.",
    "cases": [
        {
            "input": {"feature": "query_parameters", "params": {"param1": "1", "maxkeys": "2"}},
            "expected_output": "query=\n"
        },
        {
            "input": {"feature": "query_parameters", "params": {"max_keys": 100}},
            "expected_output": "query=max-keys=100\n"
        },
        {
            "input": {"feature": "query_parameters", "params": {"max_keys": 100, "prefix": null}},
            "expected_output": "query=max-keys=100&prefix\n"
        }
    ]
}
```

---

### Feature 5: Request Header Normalization

**As a developer**, I want to emit only supported request headers in normalized form, so that wire requests contain the expected header names and values.

**Expected Behavior / Usage:**

The input is a map of candidate request header fields using adapter-level names. Only a fixed allow-list of content, conditional, ACL, storage-class and copy headers is kept; unrelated fields are dropped. Underscores become hyphens, null values are preserved as null, and a numeric range value is rendered as an HTTP byte range. The output lists each surviving header on its own line sorted by name, or a single empty marker line when nothing survives.

**Test Cases:** `rcb_tests/public_test_cases/feature5_request_header_normalization.json`

```json
{
    "description": "Convert a map of request header fields into normalized HTTP header names and values. Only a fixed allow-list of content, conditional, ACL, storage-class and copy headers is kept; unrelated fields are dropped. Underscores become hyphens, null values are preserved as null, and a numeric range value is rendered as an HTTP byte range. The output lists each surviving header on its own line sorted by name, or a single empty marker line when nothing survives.",
    "cases": [
        {
            "input": {"feature": "headers", "headers": {"accept": "text/*", "accept_charset": "iso-8859-2"}},
            "expected_output": "headers=\n"
        },
        {
            "input": {"feature": "headers", "headers": {"content_type": "text/html", "x_amz_acl": "public-read", "x_amz_storage_class": "STANDARD", "if_modified_since": "today", "if_unmodified_since": "tomorrow", "if_match": "1234", "if_none_match": "1243", "content_disposition": "inline", "content_encoding": "gzip"}},
            "expected_output": "content-disposition=inline\ncontent-encoding=gzip\ncontent-type=text/html\nif-match=1234\nif-modified-since=today\nif-none-match=1243\nif-unmodified-since=tomorrow\nx-amz-acl=public-read\nx-amz-storage-class=STANDARD\n"
        },
        {
            "input": {"feature": "headers", "headers": {"range": {"range": [0, 100]}}},
            "expected_output": "range=bytes=0-100\n"
        }
    ]
}
```

---

### Feature 6: Input Validation

This feature validates the two primary identifiers a caller supplies before any remote work is attempted: bucket names and service credentials. Each rejection is reported as a neutral, language-independent category.

#### Feature 6.1: Bucket Name Validation

**As a developer**, I want to reject unusable bucket names early, so that invalid remote requests are avoided.

**Expected Behavior / Usage:**

The input is a candidate bucket name. A name is rejected when it is empty, looks like a raw IPv4 address, is shorter than three characters, is longer than 255 characters, or begins with a dot, hyphen, or underscore. Otherwise the name is accepted as-is. Rejections report the `invalid_bucket_name` category and echo the offending name; accepted names report `valid=true` and the accepted name.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_bucket_name_validation.json`

```json
{
    "description": "Validate a storage bucket name against the naming rules before a bucket handle may be created. A name is rejected when it is empty, looks like a raw IPv4 address, is shorter than three characters, is longer than 255 characters, or begins with a dot, hyphen, or underscore. Otherwise the name is accepted as-is. Rejections are reported as a neutral validation-error category that echoes the offending name in a separate field.",
    "cases": [
        {"input": {"feature": "bucket_validation", "bucket_name": ""}, "expected_output": "error=invalid_bucket_name\nname=\n"},
        {"input": {"feature": "bucket_validation", "bucket_name": "10.0.0.1"}, "expected_output": "error=invalid_bucket_name\nname=10.0.0.1\n"},
        {"input": {"feature": "bucket_validation", "bucket_name": "_asdf"}, "expected_output": "error=invalid_bucket_name\nname=_asdf\n"},
        {"input": {"feature": "bucket_validation", "bucket_name": "a_a_"}, "expected_output": "valid=true\nname=a_a_\n"}
    ]
}
```

#### Feature 6.2: Service Credential Validation

**As a developer**, I want to require both credential parts when constructing a client, so that misconfigured clients fail fast with a clear reason.

**Expected Behavior / Usage:**

The input is an access key id and a secret access key. Both are mandatory; if either is missing the construction is rejected with the `missing_credential` category naming the absent field. When both are present the client is accepted and the access key id is echoed.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_service_credential_validation.json`

```json
{
    "description": "Validate the credentials supplied when constructing a service client. Both an access key id and a secret access key are mandatory; if either is missing the construction is rejected with a neutral missing-credential category naming the absent field. When both are present the client is accepted.",
    "cases": [
        {"input": {"feature": "credential_validation", "access_key_id": null, "secret_access_key": "qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDF"}, "expected_output": "error=missing_credential\nfield=access_key_id\n"},
        {"input": {"feature": "credential_validation", "access_key_id": "12345678901234567890", "secret_access_key": null}, "expected_output": "error=missing_credential\nfield=secret_access_key\n"},
        {"input": {"feature": "credential_validation", "access_key_id": "12345678901234567890", "secret_access_key": "qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDF"}, "expected_output": "valid=true\naccess_key_id=12345678901234567890\n"}
    ]
}
```

---

### Feature 7: Bucket Addressing Resolution

**As a developer**, I want to resolve how a bucket is addressed on the wire, so that requests are routed to the intended bucket through the correct host and path.

**Expected Behavior / Usage:**

The input is a bucket name plus flags for virtual-host addressing and secure transport. The output reports the resolved request host, the path prefix, and whether virtual-host addressing is in effect. Virtual-host addressing applies only when the name forms a valid host label and secure transport is off; otherwise the bucket is addressed through a path prefix on the shared service host.

**Test Cases:** `rcb_tests/public_test_cases/feature7_bucket_addressing.json`

```json
{
    "description": "Resolve how a bucket is addressed on the wire from its name and the transport options. Output reports the request host, the path prefix, and whether virtual-host addressing is in effect. Virtual-host addressing applies only when the name forms a valid host label and secure transport is off; otherwise the bucket is addressed through a path prefix on the shared service host.",
    "cases": [
        {"input": {"feature": "bucket_addressing", "bucket_name": "Data-Bucket", "use_virtual_host": true, "use_ssl": false}, "expected_output": "host=Data-Bucket.s3.amazonaws.com\npath_prefix=\nvirtual_host=true\n"},
        {"input": {"feature": "bucket_addressing", "bucket_name": "Data_Bucket", "use_virtual_host": false, "use_ssl": false}, "expected_output": "host=s3.amazonaws.com\npath_prefix=Data_Bucket/\nvirtual_host=false\n"},
        {"input": {"feature": "bucket_addressing", "bucket_name": "Data-Secured", "use_virtual_host": true, "use_ssl": true}, "expected_output": "host=s3.amazonaws.com\npath_prefix=Data-Secured/\nvirtual_host=false\n"}
    ]
}
```

---

### Feature 8: Object Addressing and URLs

**As a developer**, I want to produce stable object identifiers and URLs, so that objects can be referenced safely in URLs.

**Expected Behavior / Usage:**

The input is a bucket name, object key, and requested address form (`full_key`, `url`, or `cname_url`). The output is either the combined bucket/key identifier, a service URL, or a CNAME-style URL. Object keys are percent-encoded in URLs (spaces, non-ASCII, and reserved characters). Buckets that cannot use virtual-host addressing produce an empty CNAME URL. Empty object keys are rejected with the `invalid_object_key` category.

**Test Cases:** `rcb_tests/public_test_cases/feature8_object_addressing.json`

```json
{
    "description": "Build object identifiers and links from a bucket name and an object key. The full key joins bucket and key with a slash. The standard URL uses the bucket addressing rules and percent-encodes the key (spaces, non-ASCII, and reserved characters). The CNAME URL omits the service host and is only available when the bucket is virtual-host eligible, otherwise it is empty. An empty key is rejected with a neutral invalid-key category. The address_kind field selects which form to produce.",
    "cases": [
        {"input": {"feature": "object_addressing", "bucket_name": "images", "key": "Lena.png", "address_kind": "full_key"}, "expected_output": "full_key=images/Lena.png\n"},
        {"input": {"feature": "object_addressing", "bucket_name": "images", "key": "Lena Söderberg [1].png", "address_kind": "url"}, "expected_output": "url=http://images.s3.amazonaws.com/Lena%20S%C3%B6derberg%20%5B1%5D.png\n"},
        {"input": {"feature": "object_addressing", "bucket_name": "images_new", "key": "Lena.png", "address_kind": "cname_url"}, "expected_output": "cname_url=\n"},
        {"input": {"feature": "object_addressing", "bucket_name": "images", "key": "", "address_kind": "url"}, "expected_output": "error=invalid_object_key\nkey=\n"}
    ]
}
```

---

### Feature 9: Object Policy Attribute Normalization

**As a developer**, I want to configure object policy attributes consistently, so that upload and copy operations use predictable policy values.

**Expected Behavior / Usage:**

The input identifies one policy-like attribute to set on an object handle. An access-policy symbol is canonicalized by replacing underscores with hyphens; a storage-tier symbol is canonicalized to upper case; a cache-control value is stored verbatim. The selected attribute is echoed back in its normalized form on a dedicated line.

**Test Cases:** `rcb_tests/public_test_cases/feature9_object_policy_attributes.json`

```json
{
    "description": "Normalize the access-policy, storage-tier, and cache-control attributes assigned to an object handle. An access policy symbol is canonicalized by replacing underscores with hyphens; a storage tier symbol is canonicalized to upper case; a cache-control value is stored verbatim. The selected attribute is echoed back in its normalized form.",
    "cases": [
        {"input": {"feature": "object_attributes", "acl": "public_read"}, "expected_output": "acl=public-read\n"},
        {"input": {"feature": "object_attributes", "storage_class": "reduced_redundancy"}, "expected_output": "storage_class=REDUCED_REDUNDANCY\n"},
        {"input": {"feature": "object_attributes", "initial_cache_control": "max-age=315360000"}, "expected_output": "cache_control=max-age=315360000\n"}
    ]
}
```

---

### Feature 10: XML Response Parsing

This feature consumes raw service XML response bodies and returns structured domain data — never raw XML. It covers the four document shapes the client must understand: the service bucket listing, a bucket's object listing, a bucket location constraint, and a copy-object result.

#### Feature 10.1: Bucket Listing Parsing

**As a developer**, I want to parse a service bucket-listing document into owned bucket names, so that callers can enumerate their buckets as structured data.

**Expected Behavior / Usage:**

The input is the raw XML body of a service bucket listing. The output reports the number of buckets and their names in document order. An empty bucket set yields a count of zero and no names.

**Test Cases:** `rcb_tests/public_test_cases/feature10_1_bucket_listing_parsing.json`

```json
{
    "description": "Parse a service bucket-listing document into the list of owned bucket names. Input is the raw XML body; output reports the number of buckets and their names in document order. An empty bucket set yields a count of zero and no names.",
    "cases": [
        {
            "input": {"feature": "parse_bucket_listing", "xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><ListAllMyBucketsResult xmlns=\"http://s3.amazonaws.com/doc/2006-03-01/\"><Owner><ID>123u1odhkhfoadf</ID><DisplayName>JohnDoe</DisplayName></Owner><Buckets></Buckets></ListAllMyBucketsResult>"},
            "expected_output": "bucket_count=0\nbuckets=\n"
        },
        {
            "input": {"feature": "parse_bucket_listing", "xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><ListAllMyBucketsResult xmlns=\"http://s3.amazonaws.com/doc/2006-03-01/\"><Owner><ID>123u1odhkhfoadf</ID><DisplayName>JohnDoe</DisplayName></Owner><Buckets><Bucket><Name>data.example.com</Name><CreationDate>2009-07-02T11:56:58.000Z</CreationDate></Bucket><Bucket><Name>images</Name><CreationDate>2009-06-05T12:26:33.000Z</CreationDate></Bucket></Buckets></ListAllMyBucketsResult>"},
            "expected_output": "bucket_count=2\nbuckets=data.example.com,images\n"
        }
    ]
}
```

#### Feature 10.2: Object Listing Parsing

**As a developer**, I want to parse a bucket object-listing document into per-object attributes, so that callers can work with object keys and sizes as structured data.

**Expected Behavior / Usage:**

The input is the raw XML body of a bucket object listing. The output reports the number of objects and their keys and byte sizes in document order. An empty listing yields a count of zero.

**Test Cases:** `rcb_tests/public_test_cases/feature10_2_object_listing_parsing.json`

```json
{
    "description": "Parse a bucket object-listing document into per-object attributes. Input is the raw XML body; output reports the number of objects and their keys and byte sizes in document order. An empty listing yields a count of zero; a prefixed listing yields only the matching subset.",
    "cases": [
        {
            "input": {"feature": "parse_object_listing", "xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><ListBucketResult xmlns=\"http://s3.amazonaws.com/doc/2006-03-01/\"><Name>bucket</Name><Prefix></Prefix><Marker></Marker><MaxKeys>1000</MaxKeys><IsTruncated>false</IsTruncated></ListBucketResult>"},
            "expected_output": "object_count=0\nkeys=\nsizes=\n"
        },
        {
            "input": {"feature": "parse_object_listing", "xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><ListBucketResult xmlns=\"http://s3.amazonaws.com/doc/2006-03-01/\"><Name>bucket</Name><Prefix></Prefix><Marker></Marker><MaxKeys>1000</MaxKeys><IsTruncated>false</IsTruncated><Contents><Key>obj1</Key><LastModified>2009-07-03T10:17:33.000Z</LastModified><ETag>&quot;99519cdf14c255e580e1b7bca85a458c&quot;</ETag><Size>1729</Size><Owner><ID>id</ID><DisplayName>owner</DisplayName></Owner><StorageClass>STANDARD</StorageClass></Contents><Contents><Key>obj2</Key><LastModified>2009-07-03T11:17:33.000Z</LastModified><ETag>&quot;99519cdf14c255e586e1b12bca85a458c&quot;</ETag><Size>179</Size><Owner><ID>id2</ID><DisplayName>owner</DisplayName></Owner><StorageClass>STANDARD</StorageClass></Contents><Contents><Key>prefix/</Key><LastModified>2009-07-03T10:17:33.000Z</LastModified><ETag>&quot;99519cdf14c255e580e1b7bca85a458c&quot;</ETag><Size>1729</Size><Owner><ID>id</ID><DisplayName>owner</DisplayName></Owner><StorageClass>STANDARD</StorageClass></Contents><Contents><Key>prefix/obj3</Key><LastModified>2009-07-03T10:17:33.000Z</LastModified><ETag>&quot;99519cdf14c255e580e1b7bca85a458c&quot;</ETag><Size>1729</Size><Owner><ID>id</ID><DisplayName>owner</DisplayName></Owner><StorageClass>STANDARD</StorageClass></Contents></ListBucketResult>"},
            "expected_output": "object_count=4\nkeys=obj1,obj2,prefix/,prefix/obj3\nsizes=1729,179,1729,1729\n"
        }
    ]
}
```

#### Feature 10.3: Location Constraint Parsing

**As a developer**, I want to parse a bucket location-constraint document into its region value, so that callers can learn where a bucket resides.

**Expected Behavior / Usage:**

The input is the raw XML body of a location-constraint document. The output reports the location code it carries.

**Test Cases:** `rcb_tests/public_test_cases/feature10_3_location_constraint_parsing.json`

```json
{
    "description": "Parse a bucket location-constraint document into the region value it carries. Input is the raw XML body; output reports the location code.",
    "cases": [
        {
            "input": {"feature": "parse_location", "xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><LocationConstraint xmlns=\"http://s3.amazonaws.com/doc/2006-03-01/\">EU</LocationConstraint>"},
            "expected_output": "location=EU\n"
        }
    ]
}
```

#### Feature 10.4: Copy Result Parsing

**As a developer**, I want to parse a copy-object result document into the new entity tag and last-modified timestamp, so that callers can confirm a server-side copy.

**Expected Behavior / Usage:**

The input is the raw XML body of a copy-object result. The output reports the entity tag exactly as carried and the last-modified value.

**Test Cases:** `rcb_tests/public_test_cases/feature10_4_copy_result_parsing.json`

```json
{
    "description": "Parse a copy-object result document into the new entity tag and last-modified timestamp of the copied object. Input is the raw XML body; output reports the entity tag exactly as carried and the last-modified value.",
    "cases": [
        {
            "input": {"feature": "parse_copy_result", "xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><CopyObjectResult><LastModified>Tue, 27 Mar 2007 21:15:45 GMT</LastModified><ETag>\"etag\"</ETag></CopyObjectResult>"},
            "expected_output": "etag=\"etag\"\nlast_modified=Tue, 27 Mar 2007 21:15:45 GMT\n"
        }
    ]
}
```

---

### Feature 11: Object Response Header Application

**As a developer**, I want to apply an object response's headers and body onto the observable fields of an object handle, so that download and metadata requests update object state.

**Expected Behavior / Usage:**

The input is an object response body plus HTTP response headers. Content type, disposition, encoding and entity tag are taken from headers (the entity tag has its surrounding quotes stripped); custom metadata headers are collected as a name-to-values map. When a partial content-range header is present the size is taken from the range total and the body is not stored as content; otherwise the size comes from the content length and the body becomes the object content.

**Test Cases:** `rcb_tests/public_test_cases/feature11_object_response_headers.json`

```json
{
    "description": "Apply the headers and body of an object response onto the observable fields of an object handle. Content type, disposition, encoding and entity tag are taken from headers (the entity tag has its surrounding quotes stripped); custom metadata headers are collected as a name-to-values map. When a partial content-range header is present the size is taken from the range total and the body is not stored as content; otherwise the size comes from the content length and the body becomes the object content.",
    "cases": [
        {
            "input": {"feature": "object_response_headers", "body": "test", "headers": {"etag": "", "content-type": "image/png", "content-disposition": "inline", "content-encoding": null, "last-modified": "Tue, 27 Mar 2007 21:15:45 GMT", "content-length": "20", "x-amz-meta-test": "metadata"}},
            "expected_output": "content=test\ncontent_type=image/png\ncontent_disposition=inline\ncontent_encoding=\nsize=20\netag=\nmetadata=x-amz-meta-test:metadata\n"
        },
        {
            "input": {"feature": "object_response_headers", "body": null, "headers": {"content-range": "bytes 0-9/20", "content-type": "image/png"}},
            "expected_output": "content=\ncontent_type=image/png\ncontent_disposition=\ncontent_encoding=\nsize=20\netag=\nmetadata=\n"
        }
    ]
}
```

---

### Feature 12: HTTP Response Handling

**As a developer**, I want to interpret an HTTP response by status class, so that callers receive either a success result or language-neutral error information.

**Expected Behavior / Usage:**

The input is an HTTP status, reason phrase, and optional response body. A success status passes through and reports its status code and reason phrase. A non-success status carrying an error document is mapped to a neutral `remote_error` result whose category is the protocol error code from the body and whose status is echoed. A non-success status with an empty or absent body maps to a generic `remote_error` category (`response_error`) with the status echoed. No runtime-specific exception text appears.

**Test Cases:** `rcb_tests/public_test_cases/feature12_http_response_handling.json`

```json
{
    "description": "Interpret an HTTP response by status class. A success status passes through and reports its status code and reason phrase. A non-success status carrying an error document is mapped to a neutral remote-error result whose category is the protocol error code from the body and whose status is echoed. A non-success status with an empty or absent body maps to a generic remote-error category with the status echoed.",
    "cases": [
        {
            "input": {"feature": "http_response_handling", "status": 200, "reason": "OK", "body": "anything"},
            "expected_output": "status=200\nreason=OK\n"
        },
        {
            "input": {"feature": "http_response_handling", "status": 404, "reason": "Not Found", "body": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Error><Code>NoSuchBucket</Code><Message>The specified bucket does not exist</Message></Error>"},
            "expected_output": "error=remote_error\ncategory=NoSuchBucket\nstatus=404\n"
        },
        {
            "input": {"feature": "http_response_handling", "status": 500, "reason": "Internal Server Error", "body": ""},
            "expected_output": "error=remote_error\ncategory=response_error\nstatus=500\n"
        }
    ]
}
```

---

### Feature 13: Upload & Copy Request Header Construction

This feature builds the request headers sent for the two write operations: uploading an object and server-side copying an object to a new key. Both apply protocol defaults and emit headers in normalized hyphenated form, sorted by name.

#### Feature 13.1: Upload Request Headers

**As a developer**, I want to construct the headers sent when uploading an object, so that uploads carry the correct policy, storage tier, and content metadata.

**Expected Behavior / Usage:**

Defaults are applied for the access policy (`private`), the storage tier (`STANDARD`), and the content type (`application/octet-stream`). Optional content encoding, content disposition, and cache control are included only when provided. The output lists each header in normalized hyphenated form, sorted by name.

**Test Cases:** `rcb_tests/public_test_cases/feature13_1_upload_request_headers.json`

```json
{
    "description": "Construct the set of request headers sent when uploading an object. Defaults are applied for the access policy (private), the storage tier (STANDARD), and the content type (application/octet-stream). Optional content encoding, content disposition, and cache control are included only when provided. Output lists each header in normalized hyphenated form, sorted by name.",
    "cases": [
        {
            "input": {"feature": "upload_headers"},
            "expected_output": "content-type=application/octet-stream\nx-amz-acl=private\nx-amz-storage-class=STANDARD\n"
        },
        {
            "input": {"feature": "upload_headers", "cache_control": "max-age=315360000"},
            "expected_output": "cache-control=max-age=315360000\ncontent-type=application/octet-stream\nx-amz-acl=private\nx-amz-storage-class=STANDARD\n"
        }
    ]
}
```

#### Feature 13.2: Copy Request Headers

**As a developer**, I want to construct the headers sent when server-side copying an object, so that copies reference the right source and metadata directive.

**Expected Behavior / Usage:**

The copy-source header is the source bucket and key joined by a slash. The metadata directive is `REPLACE` by default and `COPY` when replacement is explicitly disabled. Access policy defaults to `private` and content type to `application/octet-stream`. The output lists the copy headers in normalized hyphenated form sorted by name, followed by the destination key and the resulting object key.

**Test Cases:** `rcb_tests/public_test_cases/feature13_2_copy_request_headers.json`

```json
{
    "description": "Construct the request headers sent when server-side copying an object to a new key. The copy source header is the source bucket and key joined by a slash. The metadata directive is REPLACE by default and COPY when replacement is explicitly disabled. Access policy defaults to private and content type to application/octet-stream. Output lists the copy headers in normalized hyphenated form sorted by name, followed by the destination key and the resulting object key.",
    "cases": [
        {
            "input": {"feature": "copy_headers", "source_bucket": "images", "source_key": "Lena.png", "target_key": "Lena-copy.png"},
            "expected_output": "content-type=application/octet-stream\nx-amz-acl=private\nx-amz-copy-source=images/Lena.png\nx-amz-metadata-directive=REPLACE\ntarget_key=Lena-copy.png\nresult_key=Lena-copy.png\n"
        },
        {
            "input": {"feature": "copy_headers", "source_bucket": "images", "source_key": "Lena.png", "target_key": "Lena-copy.png", "replace": false},
            "expected_output": "content-type=application/octet-stream\nx-amz-acl=private\nx-amz-copy-source=images/Lena.png\nx-amz-metadata-directive=COPY\ntarget_key=Lena-copy.png\nresult_key=Lena-copy.png\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_request_authorization_signatures.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_request_authorization_signatures@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
