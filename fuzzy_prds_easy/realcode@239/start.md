## Product Requirement Document

# Marketplace Service Request Toolkit - Request Construction and Response Parsing Contracts

## Project Goal

Build a marketplace service client toolkit that allows developers to construct service request parameters, normalize repeated protocol fields, validate payload integrity, and parse response payloads without hand-writing brittle query maps or XML transformations.

---

## Background & Problem

Without this library/tool, developers are forced to manually assemble action names, account credentials, region endpoints, date encodings, indexed list parameters, shipment address fields, and response parsing logic. This leads to repetitive code, subtle protocol mistakes, and hard-to-maintain integrations.

With this library/tool, developers provide ordinary input values and receive deterministic protocol-ready request data or parsed response structures that can be inspected and sent by a separate transport layer.

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

### Feature 1: Region Endpoint Resolution

**As a developer**, I want to use domain-level input values for this functional area, so I can obtain deterministic protocol-facing output without duplicating low-level formatting logic.

**Expected Behavior / Usage:**

The adapter accepts the JSON input object shown in each case and prints exactly one JSON line to stdout. Successful outputs expose observable protocol values such as endpoint, request path, API version, parameter names, encoded parameter values, parsed XML signals, hash values, or structured fulfillment fields. Dynamic timestamps are normalized to `<iso8601-url-encoded-utc-second>`. Error outputs use language-neutral categories and do not expose host-language exception names or stack traces. This leaf feature is completely defined by its description, inputs, and expected stdout examples below.

**Test Cases:** `rcb_tests/public_test_cases/feature1_region_endpoints.json`

```json
{
    "description": "Resolve marketplace region codes to service endpoints and reject unsupported region codes.",
    "cases": [
        {
            "input": {
                "feature": "region_endpoint",
                "region": "AE"
            },
            "expected_output": "{\"endpoint\":\"https://mws.amazonservices.ae\",\"region\":\"AE\"}\n"
        },
        {
            "input": {
                "feature": "region_endpoint",
                "region": "US"
            },
            "expected_output": "{\"endpoint\":\"https://mws.amazonservices.com\",\"region\":\"US\"}\n"
        },
        {
            "input": {
                "feature": "region_endpoint",
                "region": "UK"
            },
            "expected_output": "{\"endpoint\":\"https://mws-eu.amazonservices.com\",\"region\":\"UK\"}\n"
        },
        {
            "input": {
                "feature": "marketplace_entry",
                "region": "CA"
            },
            "expected_output": "{\"endpoint\":\"[a specific AWS region endpoint URL — verify with the architecture team]\",\"marketplace_id\":\"[a specific AWS region endpoint URL — verify with the architecture team]\",\"region\":\"CA\"}\n"
        }
    ]
}
```

---

### Feature 2: Request Parameter Expansion

**As a developer**, I want to use domain-level input values for this functional area, so I can obtain deterministic protocol-facing output without duplicating low-level formatting logic.

**Expected Behavior / Usage:**

The adapter accepts the JSON input object shown in each case and prints exactly one JSON line to stdout. Successful outputs expose observable protocol values such as endpoint, request path, API version, parameter names, encoded parameter values, parsed XML signals, hash values, or structured fulfillment fields. Dynamic timestamps are normalized to `<iso8601-url-encoded-utc-second>`. Error outputs use language-neutral categories and do not expose host-language exception names or stack traces. This leaf feature is completely defined by its description, inputs, and expected stdout examples below.

**Test Cases:** `rcb_tests/public_test_cases/feature2_parameter_expansion.json`

```json
{
    "description": "Expand repeated scalar, keyed object, and nested dictionary values into indexed request parameter maps.",
    "cases": [
        {
            "input": {
                "feature": "parameter_expansion",
                "mode": "single",
                "name": "SomethingOrOther",
                "values": [
                    123,
                    765,
                    3512,
                    756437,
                    3125
                ]
            },
            "expected_output": "{\"result\":{\"SomethingOrOther.1\":123,\"SomethingOrOther.2\":765,\"SomethingOrOther.3\":3512,\"SomethingOrOther.4\":756437,\"SomethingOrOther.5\":3125}}\n"
        },
        {
            "input": {
                "feature": "parameter_expansion",
                "mode": "single",
                "name": "FooBar.",
                "values": "eleven"
            },
            "expected_output": "{\"result\":{\"FooBar.1\":\"eleven\"}}\n"
        },
        {
            "input": {
                "feature": "parameter_expansion",
                "mode": "multi",
                "params": {
                    "Summat.": [
                        "colorful",
                        "cheery",
                        "turkey"
                    ],
                    "FooBaz.what": "singular",
                    "hot_dog": [
                        "something",
                        "or",
                        "other"
                    ]
                }
            },
            "expected_output": "{\"result\":{\"FooBaz.what.1\":\"singular\",\"Summat.1\":\"colorful\",\"Summat.2\":\"cheery\",\"Summat.3\":\"turkey\",\"hot_dog.1\":\"something\",\"hot_dog.2\":\"or\",\"hot_dog.3\":\"other\"}}\n"
        },
        {
            "input": {
                "feature": "parameter_expansion",
                "mode": "keyed",
                "name": "AthingToKeyUp.member",
                "values": [
                    {
                        "thing": "stuff",
                        "foo": "baz"
                    },
                    {
                        "thing": 123,
                        "foo": 908,
                        "bar": "hello"
                    },
                    {
                        "stuff": "foobarbazmatazz",
                        "stuff2": "foobarbazmatazz5"
                    }
                ]
            },
            "expected_output": "{\"result\":{\"AthingToKeyUp.member.1.foo\":\"baz\",\"AthingToKeyUp.member.1.thing\":\"stuff\",\"AthingToKeyUp.member.2.bar\":\"hello\",\"AthingToKeyUp.member.2.foo\":908,\"AthingToKeyUp.member.2.thing\":123,\"AthingToKeyUp.member.3.stuff\":\"foobarbazmatazz\",\"AthingToKeyUp.member.3.stuff2\":\"foobarbazmatazz5\"}}\n"
        },
        {
            "input": {
                "feature": "parameter_expansion",
                "mode": "dict_keyed",
                "name": "ShipmentRequestDetails.PackageDimensions.",
                "values": {
                    "Length": 5,
                    "Width": 5,
                    "Height": 5,
                    "Unit": "inches"
                }
            },
            "expected_output": "{\"result\":{\"ShipmentRequestDetails.PackageDimensions.Height\":5,\"ShipmentRequestDetails.PackageDimensions.Length\":5,\"ShipmentRequestDetails.PackageDimensions.Unit\":\"inches\",\"ShipmentRequestDetails.PackageDimensions.Width\":5}}\n"
        }
    ]
}
```

---

### Feature 3: Request Description and Payload Integrity

**As a developer**, I want to use domain-level input values for this functional area, so I can obtain deterministic protocol-facing output without duplicating low-level formatting logic.

**Expected Behavior / Usage:**

The adapter accepts the JSON input object shown in each case and prints exactly one JSON line to stdout. Successful outputs expose observable protocol values such as endpoint, request path, API version, parameter names, encoded parameter values, parsed XML signals, hash values, or structured fulfillment fields. Dynamic timestamps are normalized to `<iso8601-url-encoded-utc-second>`. Error outputs use language-neutral categories and do not expose host-language exception names or stack traces. This leaf feature is completely defined by its description, inputs, and expected stdout examples below.

**Test Cases:** `rcb_tests/public_test_cases/feature3_request_description_and_hashes.json`

```json
{
    "description": "Create deterministic query descriptions and base64 MD5 digests for request and payload integrity checks.",
    "cases": [
        {
            "input": {
                "feature": "request_description",
                "params": {
                    "AWSAccessKeyId": "AAAAAAAAAAAAAAAAAAAA",
                    "Markets": "AAAAAAAAAAAAAA",
                    "SignatureVersion": "2",
                    "Timestamp": "2017-08-12T19%3A40%3A35Z",
                    "Version": "2017-01-01",
                    "SignatureMethod": "HmacSHA256"
                }
            },
            "expected_output": "{\"request_description\":\"AWSAccessKeyId=AAAAAAAAAAAAAAAAAAAA&Markets=AAAAAAAAAAAAAA&SignatureMethod=HmacSHA256&SignatureVersion=2&Timestamp=2017-08-12T19%3A40%3A35Z&Version=2017-01-01\"}\n"
        },
        {
            "input": {
                "feature": "content_md5",
                "text": "mws"
            },
            "expected_output": "{\"content_md5\":\"mA5nPbh1CSx9M3dbkr3Cyg==\"}\n"
        },
        {
            "input": {
                "feature": "data_wrapper",
                "text": "abc\tdef",
                "headers": {
                    "content-md5": "Zj+Bh1BJ8HzBb9ToK28qFQ=="
                }
            },
            "expected_output": "{\"content_md5_valid\":true,\"parsed_text\":\"abc\\tdef\"}\n"
        }
    ]
}
```

---

### Feature 4: XML Response Parsing

**As a developer**, I want to use domain-level input values for this functional area, so I can obtain deterministic protocol-facing output without duplicating low-level formatting logic.

**Expected Behavior / Usage:**

The adapter accepts the JSON input object shown in each case and prints exactly one JSON line to stdout. Successful outputs expose observable protocol values such as endpoint, request path, API version, parameter names, encoded parameter values, parsed XML signals, hash values, or structured fulfillment fields. Dynamic timestamps are normalized to `<iso8601-url-encoded-utc-second>`. Error outputs use language-neutral categories and do not expose host-language exception names or stack traces. This leaf feature is completely defined by its description, inputs, and expected stdout examples below.

**Test Cases:** `rcb_tests/public_test_cases/feature4_xml_response_parsing.json`

```json
{
    "description": "Parse XML response bytes after removing namespaces while preserving attributes, repeated elements, and non-UTF control characters.",
    "cases": [
        {
            "input": {
                "feature": "xml_response",
                "xml": "<?xml version=\"1.0\"?><ListMatchingProductsResponse xmlns=\"http://mws.amazonservices.com/schema/Products/2011-10-01\"><ListMatchingProductsResult><Products xmlns:ns2=\"http://mws.amazonservices.com/schema/Products/2011-10-01/default.xsd\"><Product><Identifiers><MarketplaceASIN><MarketplaceId>APJ6JRA9NG5V4</MarketplaceId><ASIN>8891808660</ASIN></MarketplaceASIN></Identifiers><AttributeSets><ns2:ItemAttributes xml:lang=\"it-IT\"><ns2:Creator Role=\"Autore\">Mizielinska, Aleksandra</ns2:Creator><ns2:Creator Role=\"Autore\">Mizielinski, Daniel</ns2:Creator><ns2:Title>Mappe. Un atlante per viaggiare tra terra, mari e culture del mondo</ns2:Title></ns2:ItemAttributes></AttributeSets><Relationships/></Product><Product><Identifiers><MarketplaceASIN><MarketplaceId>APJ6JRA9NG5V4</MarketplaceId><ASIN>8832706571</ASIN></MarketplaceASIN></Identifiers><AttributeSets><ns2:ItemAttributes xml:lang=\"it-IT\"><ns2:Creator Role=\"Autore\">aa.vv.</ns2:Creator><ns2:Title>Concorso Magistratura 2020: Mappe e schemi di Diritto civile-Diritto penale-Diritto amministrativo</ns2:Title></ns2:ItemAttributes></AttributeSets><SalesRankings><SalesRank><ProductCategoryId>book_display_on_website</ProductCategoryId><Rank>62044</Rank></SalesRank></SalesRankings></Product></Products></ListMatchingProductsResult><ResponseMetadata><RequestId>d384713e-7c79-4a6d-81cd-d0aa68c7b409</RequestId></ResponseMetadata></ListMatchingProductsResponse>",
                "encoding": "iso-8859-1",
                "signals": {
                    "first_asin": [
                        "ListMatchingProductsResult",
                        "Products",
                        "Product",
                        0,
                        "Identifiers",
                        "MarketplaceASIN",
                        "ASIN",
                        "value"
                    ],
                    "first_creator_role": [
                        "ListMatchingProductsResult",
                        "Products",
                        "Product",
                        0,
                        "AttributeSets",
                        "ItemAttributes",
                        "Creator",
                        0,
                        "Role",
                        "value"
                    ],
                    "second_rank": [
                        "ListMatchingProductsResult",
                        "Products",
                        "Product",
                        1,
                        "SalesRankings",
                        "SalesRank",
                        "Rank",
                        "value"
                    ],
                    "request_id": [
                        "ResponseMetadata",
                        "RequestId",
                        "value"
                    ]
                }
            },
            "expected_output": "{\"parsed_signals\":{\"first_asin\":\"8891808660\",\"first_creator_role\":\"Autore\",\"request_id\":\"d384713e-7c79-4a6d-81cd-d0aa68c7b409\",\"second_rank\":\"62044\"}}\n"
        }
    ]
}
```

---

### Feature 5: Catalog Request Construction

**As a developer**, I want to use domain-level input values for this functional area, so I can obtain deterministic protocol-facing output without duplicating low-level formatting logic.

**Expected Behavior / Usage:**

The adapter accepts the JSON input object shown in each case and prints exactly one JSON line to stdout. Successful outputs expose observable protocol values such as endpoint, request path, API version, parameter names, encoded parameter values, parsed XML signals, hash values, or structured fulfillment fields. Dynamic timestamps are normalized to `<iso8601-url-encoded-utc-second>`. Error outputs use language-neutral categories and do not expose host-language exception names or stack traces. This leaf feature is completely defined by its description, inputs, and expected stdout examples below.

**Test Cases:** `rcb_tests/public_test_cases/feature5_product_request_parameters.json`

```json
{
    "description": "Build catalog request parameters for product search, product lookup, pricing, offers, and category operations.",
    "cases": [
        {
            "input": {
                "feature": "request_params",
                "area": "products",
                "operation": "ListMatchingProducts",
                "arguments": {
                    "marketplace_id": "ALDERAAN",
                    "query": "hokey religions and ancient weapons",
                    "context_id": "ArtsAndCrafts"
                }
            },
            "expected_output": "{\"endpoint\":\"https://mws.amazonservices.com\",\"params\":{\"AWSAccessKeyId\":\"cred_access\",\"Action\":\"ListMatchingProducts\",\"MWSAuthToken\":\"cred_token\",\"MarketplaceId\":\"ALDERAAN\",\"Query\":\"hokey%20religions%20and%20ancient%20weapons\",\"QueryContextId\":\"ArtsAndCrafts\",\"SellerId\":\"cred_account\",\"SignatureMethod\":\"HmacSHA256\",\"SignatureVersion\":\"2\",\"Timestamp\":\"<iso8601-url-encoded-utc-second>\",\"Version\":\"2011-10-01\"},\"path\":\"/Products/2011-10-01\",\"version\":\"2011-10-01\"}\n"
        },
        {
            "input": {
                "feature": "request_params",
                "area": "products",
                "operation": "GetMatchingProduct",
                "arguments": {
                    "marketplace_id": "TATOOINE",
                    "asins": [
                        "pibMZnNRoS",
                        "nTuCCevqaZ"
                    ]
                }
            },
            "expected_output": "{\"endpoint\":\"https://mws.amazonservices.com\",\"params\":{\"ASINList.ASIN.1\":\"pibMZnNRoS\",\"ASINList.ASIN.2\":\"nTuCCevqaZ\",\"AWSAccessKeyId\":\"cred_access\",\"Action\":\"GetMatchingProduct\",\"MWSAuthToken\":\"cred_token\",\"MarketplaceId\":\"TATOOINE\",\"SellerId\":\"cred_account\",\"SignatureMethod\":\"HmacSHA256\",\"SignatureVersion\":\"2\",\"Timestamp\":\"<iso8601-url-encoded-utc-second>\",\"Version\":\"2011-10-01\"},\"path\":\"/Products/2011-10-01\",\"version\":\"2011-10-01\"}\n"
        },
        {
            "input": {
                "feature": "request_params",
                "area": "products",
                "operation": "GetLowestOfferListingsForSKU",
                "arguments": {
                    "marketplace_id": "ENDOR",
                    "skus": [
                        "XhPpwZTI3T",
                        "JcaTGvCr4f"
                    ],
                    "condition": "Beat up",
                    "exclude_me": true
                }
            },
            "expected_output": "{\"endpoint\":\"https://mws.amazonservices.com\",\"params\":{\"AWSAccessKeyId\":\"cred_access\",\"Action\":\"GetLowestOfferListingsForSKU\",\"ExcludeMe\":\"true\",\"ItemCondition\":\"Beat%20up\",\"MWSAuthToken\":\"cred_token\",\"MarketplaceId\":\"ENDOR\",\"SellerId\":\"cred_account\",\"SellerSKUList.SellerSKU.1\":\"XhPpwZTI3T\",\"SellerSKUList.SellerSKU.2\":\"JcaTGvCr4f\",\"SignatureMethod\":\"HmacSHA256\",\"SignatureVersion\":\"2\",\"Timestamp\":\"<iso8601-url-encoded-utc-second>\",\"Version\":\"2011-10-01\"},\"path\":\"/Products/2011-10-01\",\"version\":\"2011-10-01\"}\n"
        }
    ]
}
```

---

### Feature 6: Order Request Construction

**As a developer**, I want to use domain-level input values for this functional area, so I can obtain deterministic protocol-facing output without duplicating low-level formatting logic.

**Expected Behavior / Usage:**

The adapter accepts the JSON input object shown in each case and prints exactly one JSON line to stdout. Successful outputs expose observable protocol values such as endpoint, request path, API version, parameter names, encoded parameter values, parsed XML signals, hash values, or structured fulfillment fields. Dynamic timestamps are normalized to `<iso8601-url-encoded-utc-second>`. Error outputs use language-neutral categories and do not expose host-language exception names or stack traces. This leaf feature is completely defined by its description, inputs, and expected stdout examples below.

**Test Cases:** `rcb_tests/public_test_cases/feature6_order_request_parameters.json`

```json
{
    "description": "Build order request parameters for order searches, order lookup, order item lookup, and next-token pagination.",
    "cases": [
        {
            "input": {
                "feature": "request_params",
                "area": "orders",
                "operation": "ListOrders",
                "arguments": {
                    "marketplace_ids": [
                        "ATVPDKIKX0DER",
                        "[a specific AWS region endpoint URL — verify with the architecture team]"
                    ],
                    "created_after": "2018-04-30T22:59:59",
                    "created_before": "2018-04-30T23:59:59",
                    "order_statuses": [
                        "Pending",
                        "Shipped"
                    ],
                    "fulfillment_channels": [
                        "AFN",
                        "MFN"
                    ],
                    "payment_methods": [
                        "COD",
                        "Other"
                    ],
                    "buyer_email": "buyer@example.com",
                    "seller_order_id": "seller-123",
                    "max_results": 99,
                    "tfm_shipment_statuses": [
                        "PendingPickUp",
                        "Delivered"
                    ],
                    "easyship_statuses": [
                        "PendingSchedule",
                        "DroppedOff"
                    ]
                }
            },
            "expected_output": "{\"endpoint\":\"https://mws.amazonservices.com\",\"params\":{\"AWSAccessKeyId\":\"cred_access\",\"Action\":\"ListOrders\",\"BuyerEmail\":\"buyer%40example.com\",\"CreatedAfter\":\"2018-04-30T22%3A59%3A59\",\"CreatedBefore\":\"2018-04-30T23%3A59%3A59\",\"EasyShipShipmentStatus.Status.1\":\"PendingSchedule\",\"EasyShipShipmentStatus.Status.2\":\"DroppedOff\",\"FulfillmentChannel.Channel.1\":\"AFN\",\"FulfillmentChannel.Channel.2\":\"MFN\",\"MWSAuthToken\":\"cred_token\",\"MarketplaceId.Id.1\":\"ATVPDKIKX0DER\",\"MarketplaceId.Id.2\":\"[a specific AWS region endpoint URL — verify with the architecture team]\",\"MaxResultsPerPage\":\"99\",\"OrderStatus.Status.1\":\"Pending\",\"OrderStatus.Status.2\":\"Shipped\",\"PaymentMethod.Method.1\":\"COD\",\"PaymentMethod.Method.2\":\"Other\",\"SellerId\":\"cred_account\",\"SellerOrderId\":\"seller-123\",\"SignatureMethod\":\"HmacSHA256\",\"SignatureVersion\":\"2\",\"TFMShipmentStatus.Status.1\":\"PendingPickUp\",\"TFMShipmentStatus.Status.2\":\"Delivered\",\"Timestamp\":\"<iso8601-url-encoded-utc-second>\",\"Version\":\"2013-09-01\"},\"path\":\"/Orders/2013-09-01\",\"version\":\"2013-09-01\"}\n"
        },
        {
            "input": {
                "feature": "request_params",
                "area": "orders",
                "operation": "ListOrdersByNextToken",
                "arguments": {
                    "next_token": "RXmLZ2bEgE"
                }
            },
            "expected_output": "{\"endpoint\":\"https://mws.amazonservices.com\",\"params\":{\"AWSAccessKeyId\":\"cred_access\",\"Action\":\"ListOrdersByNextToken\",\"MWSAuthToken\":\"cred_token\",\"NextToken\":\"RXmLZ2bEgE\",\"SellerId\":\"cred_account\",\"SignatureMethod\":\"HmacSHA256\",\"SignatureVersion\":\"2\",\"Timestamp\":\"<iso8601-url-encoded-utc-second>\",\"Version\":\"2013-09-01\"},\"path\":\"/Orders/2013-09-01\",\"version\":\"2013-09-01\"}\n"
        },
        {
            "input": {
                "feature": "request_params",
                "area": "orders",
                "operation": "GetOrder",
                "arguments": {
                    "amazon_order_ids": [
                        "902-3159896-1390916",
                        "483-3488972-0896720"
                    ]
                }
            },
            "expected_output": "{\"endpoint\":\"https://mws.amazonservices.com\",\"params\":{\"AWSAccessKeyId\":\"cred_access\",\"Action\":\"GetOrder\",\"AmazonOrderId.Id.1\":\"902-3159896-1390916\",\"AmazonOrderId.Id.2\":\"483-3488972-0896720\",\"MWSAuthToken\":\"cred_token\",\"SellerId\":\"cred_account\",\"SignatureMethod\":\"HmacSHA256\",\"SignatureVersion\":\"2\",\"Timestamp\":\"<iso8601-url-encoded-utc-second>\",\"Version\":\"2013-09-01\"},\"path\":\"/Orders/2013-09-01\",\"version\":\"2013-09-01\"}\n"
        }
    ]
}
```

---

### Feature 7: Report and Feed Request Construction

**As a developer**, I want to use domain-level input values for this functional area, so I can obtain deterministic protocol-facing output without duplicating low-level formatting logic.

**Expected Behavior / Usage:**

The adapter accepts the JSON input object shown in each case and prints exactly one JSON line to stdout. Successful outputs expose observable protocol values such as endpoint, request path, API version, parameter names, encoded parameter values, parsed XML signals, hash values, or structured fulfillment fields. Dynamic timestamps are normalized to `<iso8601-url-encoded-utc-second>`. Error outputs use language-neutral categories and do not expose host-language exception names or stack traces. This leaf feature is completely defined by its description, inputs, and expected stdout examples below.

**Test Cases:** `rcb_tests/public_test_cases/feature7_report_and_feed_request_parameters.json`

```json
{
    "description": "Build report and feed request parameters including date windows, list filters, booleans, and result retrieval identifiers.",
    "cases": [
        {
            "input": {
                "feature": "request_params",
                "area": "reports",
                "operation": "RequestReport",
                "arguments": {
                    "report_type": "_GET_FLAT_FILE_OPEN_LISTINGS_DATA_",
                    "start_date": "2018-04-30T22:59:59",
                    "end_date": "2018-04-30T23:59:59",
                    "marketplace_ids": [
                        "iQzBCmf1y3",
                        "wH9q0CiEMp"
                    ]
                }
            },
            "expected_output": "{\"endpoint\":\"https://mws.amazonservices.com\",\"params\":{\"AWSAccessKeyId\":\"cred_access\",\"Action\":\"RequestReport\",\"EndDate\":\"2018-04-30T23%3A59%3A59\",\"MWSAuthToken\":\"cred_token\",\"MarketplaceIdList.Id.1\":\"iQzBCmf1y3\",\"MarketplaceIdList.Id.2\":\"wH9q0CiEMp\",\"Merchant\":\"cred_account\",\"ReportType\":\"_GET_FLAT_FILE_OPEN_LISTINGS_DATA_\",\"SignatureMethod\":\"HmacSHA256\",\"SignatureVersion\":\"2\",\"StartDate\":\"2018-04-30T22%3A59%3A59\",\"Timestamp\":\"<iso8601-url-encoded-utc-second>\",\"Version\":\"2009-01-01\"},\"path\":\"/\",\"version\":\"2009-01-01\"}\n"
        },
        {
            "input": {
                "feature": "request_params",
                "area": "reports",
                "operation": "GetReportList",
                "arguments": {
                    "request_ids": [
                        "c4eik8sxXC",
                        "NIVgnbHXe0"
                    ],
                    "report_types": [
                        "_GET_V1_SELLER_PERFORMANCE_REPORT_",
                        "_GET_SELLER_FEEDBACK_DATA_"
                    ],
                    "max_count": 564,
                    "acknowledged": true,
                    "from_date": "2018-05-01T01:02:03",
                    "to_date": "2018-05-01T02:02:03"
                }
            },
            "expected_output": "{\"endpoint\":\"https://mws.amazonservices.com\",\"params\":{\"AWSAccessKeyId\":\"cred_access\",\"Acknowledged\":\"true\",\"Action\":\"GetReportList\",\"AvailableFromDate\":\"2018-05-01T01%3A02%3A03\",\"AvailableToDate\":\"2018-05-01T02%3A02%3A03\",\"MWSAuthToken\":\"cred_token\",\"MaxCount\":\"564\",\"Merchant\":\"cred_account\",\"ReportRequestIdList.Id.1\":\"c4eik8sxXC\",\"ReportRequestIdList.Id.2\":\"NIVgnbHXe0\",\"ReportTypeList.Type.1\":\"_GET_V1_SELLER_PERFORMANCE_REPORT_\",\"ReportTypeList.Type.2\":\"_GET_SELLER_FEEDBACK_DATA_\",\"SignatureMethod\":\"HmacSHA256\",\"SignatureVersion\":\"2\",\"Timestamp\":\"<iso8601-url-encoded-utc-second>\",\"Version\":\"2009-01-01\"},\"path\":\"/\",\"version\":\"2009-01-01\"}\n"
        },
        {
            "input": {
                "feature": "request_params",
                "area": "reports",
                "operation": "GetReportScheduleListByNextToken",
                "arguments": {
                    "next_token": "SAlt4JwJGv"
                }
            },
            "expected_output": "{\"endpoint\":\"https://mws.amazonservices.com\",\"params\":{\"AWSAccessKeyId\":\"cred_access\",\"Action\":\"GetReportScheduleListByNextToken\",\"MWSAuthToken\":\"cred_token\",\"Merchant\":\"cred_account\",\"NextToken\":\"SAlt4JwJGv\",\"SignatureMethod\":\"HmacSHA256\",\"SignatureVersion\":\"2\",\"Timestamp\":\"<iso8601-url-encoded-utc-second>\",\"Version\":\"2009-01-01\"},\"path\":\"/\",\"version\":\"2009-01-01\"}\n"
        }
    ]
}
```

---

### Feature 8: Inventory, Finance, Recommendation, and Seller Request Construction

**As a developer**, I want to use domain-level input values for this functional area, so I can obtain deterministic protocol-facing output without duplicating low-level formatting logic.

**Expected Behavior / Usage:**

The adapter accepts the JSON input object shown in each case and prints exactly one JSON line to stdout. Successful outputs expose observable protocol values such as endpoint, request path, API version, parameter names, encoded parameter values, parsed XML signals, hash values, or structured fulfillment fields. Dynamic timestamps are normalized to `<iso8601-url-encoded-utc-second>`. Error outputs use language-neutral categories and do not expose host-language exception names or stack traces. This leaf feature is completely defined by its description, inputs, and expected stdout examples below.

**Test Cases:** `rcb_tests/public_test_cases/feature8_inventory_finance_seller_request_parameters.json`

```json
{
    "description": "Build inventory, finance, recommendation, and seller request parameters, including next-token alternatives.",
    "cases": [
        {
            "input": {
                "feature": "request_params",
                "area": "inventory",
                "operation": "ListInventorySupply",
                "arguments": {
                    "skus": [
                        "sku-one",
                        "sku-two"
                    ],
                    "datetime_": "2018-04-30T22:59:59",
                    "response_group": "Basic"
                }
            },
            "expected_output": "{\"endpoint\":\"https://mws.amazonservices.com\",\"params\":{\"AWSAccessKeyId\":\"cred_access\",\"Action\":\"ListInventorySupply\",\"MWSAuthToken\":\"cred_token\",\"QueryStartDateTime\":\"2018-04-30T22%3A59%3A59\",\"ResponseGroup\":\"Basic\",\"SellerId\":\"cred_account\",\"SellerSkus.member.1\":\"sku-one\",\"SellerSkus.member.2\":\"sku-two\",\"SignatureMethod\":\"HmacSHA256\",\"SignatureVersion\":\"2\",\"Timestamp\":\"<iso8601-url-encoded-utc-second>\",\"Version\":\"2010-10-01\"},\"path\":\"/FulfillmentInventory/2010-10-01\",\"version\":\"2010-10-01\"}\n"
        },
        {
            "input": {
                "feature": "request_params",
                "area": "inventory",
                "operation": "ListInventorySupplyByNextToken",
                "arguments": {
                    "next_token": "0Ys0j83sOL"
                }
            },
            "expected_output": "{\"endpoint\":\"https://mws.amazonservices.com\",\"params\":{\"AWSAccessKeyId\":\"cred_access\",\"Action\":\"ListInventorySupplyByNextToken\",\"MWSAuthToken\":\"cred_token\",\"NextToken\":\"0Ys0j83sOL\",\"SellerId\":\"cred_account\",\"SignatureMethod\":\"HmacSHA256\",\"SignatureVersion\":\"2\",\"Timestamp\":\"<iso8601-url-encoded-utc-second>\",\"Version\":\"2010-10-01\"},\"path\":\"/FulfillmentInventory/2010-10-01\",\"version\":\"2010-10-01\"}\n"
        },
        {
            "input": {
                "feature": "request_params",
                "area": "finances",
                "operation": "ListFinancialEventGroups",
                "arguments": {
                    "max_results": 99,
                    "created_after": "2018-04-30T22:59:59",
                    "created_before": "2018-04-30T23:59:59"
                }
            },
            "expected_output": "{\"endpoint\":\"https://mws.amazonservices.com\",\"params\":{\"AWSAccessKeyId\":\"cred_access\",\"Action\":\"ListFinancialEventGroups\",\"FinancialEventGroupStartedAfter\":\"2018-04-30T22%3A59%3A59\",\"FinancialEventGroupStartedBefore\":\"2018-04-30T23%3A59%3A59\",\"MWSAuthToken\":\"cred_token\",\"MaxResultsPerPage\":\"99\",\"SellerId\":\"cred_account\",\"SignatureMethod\":\"HmacSHA256\",\"SignatureVersion\":\"2\",\"Timestamp\":\"<iso8601-url-encoded-utc-second>\",\"Version\":\"2015-05-01\"},\"path\":\"/Finances/2015-05-01\",\"version\":\"2015-05-01\"}\n"
        }
    ]
}
```

---

### Feature 9: Inbound Fulfillment Request Construction

**As a developer**, I want to use domain-level input values for this functional area, so I can obtain deterministic protocol-facing output without duplicating low-level formatting logic.

**Expected Behavior / Usage:**

The adapter accepts the JSON input object shown in each case and prints exactly one JSON line to stdout. Successful outputs expose observable protocol values such as endpoint, request path, API version, parameter names, encoded parameter values, parsed XML signals, hash values, or structured fulfillment fields. Dynamic timestamps are normalized to `<iso8601-url-encoded-utc-second>`. Error outputs use language-neutral categories and do not expose host-language exception names or stack traces. This leaf feature is completely defined by its description, inputs, and expected stdout examples below.

**Test Cases:** `rcb_tests/public_test_cases/feature9_inbound_fulfillment_request_parameters.json`

```json
{
    "description": "Build inbound fulfillment shipment request parameters for item lists, ship-from addresses, shipment creation, labels, and transport operations.",
    "cases": [
        {
            "input": {
                "feature": "inbound_items",
                "operation": "CreateInboundShipmentPlan",
                "items": [
                    {
                        "sku": "somethingelse",
                        "quantity": 56,
                        "quantity_in_case": 12,
                        "asin": "ANYTHING",
                        "condition": "Used"
                    },
                    {
                        "sku": "something",
                        "quantity": 34
                    }
                ]
            },
            "expected_output": "{\"items\":[{\"ASIN\":\"ANYTHING\",\"Condition\":\"Used\",\"Quantity\":56,\"QuantityInCase\":12,\"SellerSKU\":\"somethingelse\"},{\"ASIN\":null,\"Condition\":null,\"Quantity\":34,\"QuantityInCase\":null,\"SellerSKU\":\"something\"}]}\n"
        },
        {
            "input": {
                "feature": "inbound_address",
                "address": {
                    "name": "Roland Deschain",
                    "address_1": "500 Summat Cully Lane",
                    "address_2": "Apartment 19",
                    "city": "Gilead",
                    "district_or_county": "West-Town",
                    "state_or_province": "New Canaan",
                    "postal_code": "13019",
                    "country": "Mid-World"
                }
            },
            "expected_output": "{\"ship_from_address\":{\"ShipFromAddress.AddressLine1\":\"500 Summat Cully Lane\",\"ShipFromAddress.AddressLine2\":\"Apartment 19\",\"ShipFromAddress.City\":\"Gilead\",\"ShipFromAddress.CountryCode\":\"Mid-World\",\"ShipFromAddress.DistrictOrCounty\":\"West-Town\",\"ShipFromAddress.Name\":\"Roland Deschain\",\"ShipFromAddress.PostalCode\":\"13019\",\"ShipFromAddress.StateOrProvinceCode\":\"New Canaan\"}}\n"
        },
        {
            "input": {
                "feature": "inbound_address",
                "address": {
                    "name": "Roland Deschain",
                    "address_1": "500 Summat Cully Lane",
                    "city": "Gilead"
                }
            },
            "expected_output": "{\"ship_from_address\":{\"ShipFromAddress.AddressLine1\":\"500 Summat Cully Lane\",\"ShipFromAddress.AddressLine2\":null,\"ShipFromAddress.City\":\"Gilead\",\"ShipFromAddress.CountryCode\":\"US\",\"ShipFromAddress.DistrictOrCounty\":null,\"ShipFromAddress.Name\":\"Roland Deschain\",\"ShipFromAddress.PostalCode\":null,\"ShipFromAddress.StateOrProvinceCode\":null}}\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_region_endpoints.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_region_endpoints@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
