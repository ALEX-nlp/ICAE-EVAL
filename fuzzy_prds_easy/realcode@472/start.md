## Product Requirement Document

# Tokenized Research Project Registry — A GraphQL Service for IP-Backed Projects, Data Rooms & Announcements

## Project Goal

Build a GraphQL service that lets a research organization register tokenized (IP-NFT) research projects and, for each one, automatically provision an isolated workspace consisting of a dedicated account, a versioned **data room** of files, and an append-only **announcements** stream. Application developers interact with everything — provisioning, lifecycle control, file versioning and publishing — through a single typed GraphQL surface, without having to assemble accounts, content-addressed datasets, collections and activity feeds by hand.

---

## Background & Problem

Without this service, a team that wants to host data and updates for tokenized research assets has to manually wire together several moving parts: create an account namespace per project, stand up a content-addressed store for files, track every file version and its metadata, maintain a collection that maps human paths to file references, reserve project symbols so two projects never collide, and build an audit/activity log. Doing this by hand is repetitive, error-prone, and hard to keep consistent — for example, it is easy to accidentally let two projects share the same on-chain unique id, or to publish an announcement that points at an attachment that does not exist.

With this service, a developer issues one mutation to provision a project and receives a ready-to-use account, data room, and announcements stream. Files are uploaded with rich denormalized metadata and automatically versioned; projects can be disabled and re-enabled idempotently while keeping their symbols reserved; announcements validate their attachments before being accepted; and every change is surfaced newest-first in per-project and global activity feeds. All of this is reached through one coherent, strongly typed API.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a non-trivial, stateful, multi-entity domain (projects, accounts, versioned files, collections, announcements, activity feeds). It MUST NOT be implemented as a single "god file". Use a clear multi-file layout that separates the GraphQL/API surface, the core domain use-cases (provisioning, lifecycle, data-room, announcements), and the underlying versioned-storage abstractions, mirroring a production-grade repository.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract for an execution adapter**, not the internal data model. Each `input` is a sequence of GraphQL operations (with variables) executed against a freshly provisioned environment; each `expected_output` is the normalized, rendered response stream. The core domain MUST remain decoupled from stdin/stdout and JSON case parsing. The adapter is solely responsible for executing operations against the API and rendering responses to the contract below.

3. **Adherence to SOLID Design Principles:** Separate request parsing/routing, validation, core execution, and output formatting into distinct units (SRP). The core engine must be open for extension but closed for modification (OCP); derived types must be substitutable (LSP); interfaces must be small and cohesive (ISP); and high-level modules must depend on abstractions, not concrete I/O (DIP).

4. **Robustness & Interface Design:** The public GraphQL interface must be idiomatic and hide internal complexity. Errors must be modeled explicitly — both as typed result variants returned inside `data` (e.g. a conflict or invalid-attachment result type) and as top-level GraphQL errors for not-found / no-history conditions — rather than as generic faults. Volatile runtime identifiers (generated dataset ids of the form `did:odf:…` and random UUIDs) are part of the data model but are not stable across runs; the execution adapter normalizes them to stable, order-of-appearance placeholders (`[stable placeholders for volatile identifiers (e.g., '<did-X>'), ask for the specific string format]`, `[stable placeholders for volatile identifiers (e.g., '<did-X>'), ask for the specific string format]`, `[stable placeholders for volatile identifiers (e.g., '<did-X>'), ask for the specific string format]`, …) so the contract is deterministic while preserving identity relationships.

---

## Output Contract (how `expected_output` is rendered)

Every case `input` is an object with:

- an optional `"create_projects_dataset": true` flag that pre-creates the empty project catalog before any operation runs (when omitted, the first `createProject` auto-creates it);
- an `"operations"` array. Each operation has a GraphQL `"query"` string, optional `"variables"`, an optional `"emit"` boolean (default `true`; set `false` to run a setup step without printing it), and an optional `"capture"` map that records a runtime value (looked up by a JSON path) under a name so a later operation can reference it via a `"$name"` variable.

Operations execute in order against one shared, freshly provisioned environment. For each **emitted** operation the adapter prints a block:

```
--- operation <N> ---
errors:
  - <normalized error message>      (only present when the response carries GraphQL errors)
data:
<pretty-printed JSON of the response data, object keys sorted, 2-space indent>
```

`<N>` counts only emitted operations starting at 1. When `data` is null it is printed as the literal `null`. All `did:odf:…` ids and UUIDs anywhere in the output (including inside error messages) are replaced with stable placeholders; the same raw id always maps to the same placeholder within a case.

---

## Core Features

### Feature 1: Project Provisioning & Catalog

**As a developer**, I want to register a tokenized research project from its IP-NFT identity and have a complete workspace provisioned automatically, so I can immediately start hosting its data without manually creating accounts, stores, and collections.

**Expected Behavior / Usage:**

Provisioning takes an IP-NFT symbol, a globally unique id (`ipnftUid`), a contract address, and an integer token id (token ids may be arbitrarily large integers carried as strings). On success the response is a success-typed result whose `project` exposes a freshly generated account (with id and an account name derived by lowercasing and namespacing the symbol, e.g. a symbol `VITAFAST` yields account name `molecule.vitafast`), plus a `dataRoom` and an `announcements` entity each with a generated id and an alias of the form `<accountName>/data-room` and `<accountName>/announcements`. The created project then appears in the catalog listing and can be read back by its `ipnftUid`, with its symbol normalized to lowercase. Attempting to provision a second project that reuses an already-registered `ipnftUid` (or an already-used symbol) is rejected with a conflict-typed result whose message names the existing project's symbol and uid; the catalog is left unchanged. Generated account/dataset ids are non-deterministic and appear as stable placeholders in the contract.

**Test Cases:** `rcb_tests/public_test_cases/feature1_project_provisioning.json`

```json
{
  "description": "Provision an IP-NFT-identified project and list it in the catalog; a second project reusing the same unique id is rejected as a conflict.",
  "cases": [
    {
      "input": {
        "create_projects_dataset": true,
        "operations": [
          {
            "query": "\nquery {\n  molecule {\n    v2 {\n      projects(page: 0, perPage: 100) {\n        nodes { ipnftSymbol ipnftUid }\n      }\n    }\n  }\n}\n"
          },
          {
            "query": "\nmutation ($ipnftSymbol: String!, $ipnftUid: String!, $ipnftAddress: String!, $ipnftTokenId: Int!) {\n  molecule {\n    v2 {\n      createProject(ipnftSymbol: $ipnftSymbol, ipnftUid: $ipnftUid, ipnftAddress: $ipnftAddress, ipnftTokenId: $ipnftTokenId) {\n        isSuccess\n        message\n        __typename\n        ... on CreateProjectSuccess {\n          project {\n            account { id accountName }\n            ipnftUid\n            dataRoom { id alias }\n            announcements { id alias }\n          }\n        }\n      }\n    }\n  }\n}\n",
            "variables": {
              "ipnftSymbol": "VITAFAST",
              "ipnftUid": "0xcaD88677CA87a7815728C72D74B4ff4982d54Fc1_9",
              "ipnftAddress": "0xcaD88677CA87a7815728C72D74B4ff4982d54Fc1",
              "ipnftTokenId": "9"
            }
          },
          {
            "query": "\nquery ($ipnftUid: String!) {\n  molecule {\n    v2 {\n      project(ipnftUid: $ipnftUid) {\n        account { id accountName }\n        ipnftSymbol\n        ipnftUid\n        ipnftAddress\n        ipnftTokenId\n      }\n    }\n  }\n}\n",
            "variables": {
              "ipnftUid": "0xcaD88677CA87a7815728C72D74B4ff4982d54Fc1_9"
            }
          },
          {
            "query": "\nmutation ($ipnftSymbol: String!, $ipnftUid: String!, $ipnftAddress: String!, $ipnftTokenId: Int!) {\n  molecule {\n    v2 {\n      createProject(ipnftSymbol: $ipnftSymbol, ipnftUid: $ipnftUid, ipnftAddress: $ipnftAddress, ipnftTokenId: $ipnftTokenId) {\n        isSuccess\n        message\n        __typename\n        ... on CreateProjectSuccess {\n          project {\n            account { id accountName }\n            ipnftUid\n            dataRoom { id alias }\n            announcements { id alias }\n          }\n        }\n      }\n    }\n  }\n}\n",
            "variables": {
              "ipnftSymbol": "vitaslow",
              "ipnftUid": "0xcaD88677CA87a7815728C72D74B4ff4982d54Fc1_9",
              "ipnftAddress": "0xcaD88677CA87a7815728C72D74B4ff4982d54Fc1",
              "ipnftTokenId": "9"
            }
          },
          {
            "query": "\nquery {\n  molecule {\n    v2 {\n      projects(page: 0, perPage: 100) {\n        nodes { ipnftSymbol ipnftUid }\n      }\n    }\n  }\n}\n"
          }
        ]
      },
      "expected_output": "--- operation 1 ---\ndata:\n{\n  \"molecule\": {\n    \"v2\": {\n      \"projects\": {\n        \"nodes\": []\n      }\n    }\n  }\n}\n--- operation 2 ---\ndata:\n{\n  \"molecule\": {\n    \"v2\": {\n      \"createProject\": {\n        \"__typename\": \"CreateProjectSuccess\",\n        \"isSuccess\": true,\n        \"message\": \"\",\n        \"project\": {\n          \"account\": {\n            \"accountName\": \"molecule.vitafast\",\n            \"id\": \"[stable placeholders for volatile identifiers (e.g., '<did-X>'), ask for the specific string format]\"\n          },\n          \"announcements\": {\n            \"alias\": \"molecule.vitafast/announcements\",\n            \"id\": \"[stable placeholders for volatile identifiers (e.g., '<did-X>'), ask for the specific string format]\"\n          },\n          \"dataRoom\": {\n            \"alias\": \"molecule.vitafast/data-room\",\n            \"id\": \"<did-2>\"\n          },\n          \"ipnftUid\": \"0xcaD88677CA87a7815728C72D74B4ff4982d54Fc1_9\"\n        }\n      }\n    }\n  }\n}\n--- operation 3 ---\ndata:\n{\n  \"molecule\": {\n    \"v2\": {\n      \"project\": {\n        \"account\": {\n          \"accountName\": \"molecule.vitafast\",\n          \"id\": \"[stable placeholders for volatile identifiers (e.g., '<did-X>'), ask for the specific string format]\"\n        },\n        \"ipnftAddress\": \"0xcaD88677CA87a7815728C72D74B4ff4982d54Fc1\",\n        \"ipnftSymbol\": \"vitafast\",\n        \"ipnftTokenId\": \"9\",\n        \"ipnftUid\": \"0xcaD88677CA87a7815728C72D74B4ff4982d54Fc1_9\"\n      }\n    }\n  }\n}\n--- operation 4 ---\ndata:\n{\n  \"molecule\": {\n    \"v2\": {\n      \"createProject\": {\n        \"__typename\": \"CreateProjectErrorConflict\",\n        \"isSuccess\": false,\n        \"message\": \"Conflict with existing project vitafast (0xcaD88677CA87a7815728C72D74B4ff4982d54Fc1_9)\"\n      }\n    }\n  }\n}\n--- operation 5 ---\ndata:\n{\n  \"molecule\": {\n    \"v2\": {\n      \"projects\": {\n        \"nodes\": [\n          {\n            \"ipnftSymbol\": \"vitafast\",\n            \"ipnftUid\": \"0xcaD88677CA87a7815728C72D74B4ff4982d54Fc1_9\"\n          }\n        ]\n      }\n    }\n  }\n}\n"
    }
  ]
}
```

---

### Feature 2: Project Lifecycle (Disable / Enable & Symbol Reservation)

**As a developer**, I want to hide a project from the catalog and later restore it, with safe idempotent semantics and clear errors, so I can take projects offline without losing their identity or accidentally freeing their reserved symbol.

**Expected Behavior / Usage:**

Disabling a project by `ipnftUid` returns a mutation handle and removes the project from both the catalog listing and lookup-by-id. Disabling is single-shot: once a project is disabled, a second disable of the same id surfaces a top-level `Project <uid> not found` error and produces null data. Enabling a previously-disabled project restores it to the catalog and to lookup-by-id, and is idempotent (enabling an already-enabled project succeeds and returns the same handle). Disabling or enabling a completely unknown id yields top-level errors with null data: disable reports `Project <uid> not found`, while enable reports `No historical entries for project <uid>`. A symbol stays reserved while its project is disabled: creating a new project that reuses the disabled project's symbol is rejected with a conflict-typed result naming the original project.

**Test Cases:** `rcb_tests/public_test_cases/feature2_project_lifecycle.json`

```json
{
  "description": "Disabling or enabling an unknown project surfaces a not-found / no-history error.",
  "cases": [
    {
      "input": {
        "create_projects_dataset": true,
        "operations": [
          {
            "query": "\nmutation ($ipnftUid: String!) {\n  molecule { v2 { disableProject(ipnftUid: $ipnftUid) { project { __typename } } } }\n}\n",
            "variables": {
              "ipnftUid": "foo"
            }
          },
          {
            "query": "\nmutation ($ipnftUid: String!) {\n  molecule { v2 { enableProject(ipnftUid: $ipnftUid) { project { __typename } } } }\n}\n",
            "variables": {
              "ipnftUid": "foo"
            }
          }
        ]
      },
      "expected_output": "--- operation 1 ---\nerrors:\n  - Project foo not found\ndata:\nnull\n--- operation 2 ---\nerrors:\n  - No historical entries for project foo\ndata:\nnull\n"
    }
  ]
}
```

---

### Feature 3: Data Room — Versioned File Management

**As a developer**, I want to upload files into a project's data room with rich metadata and automatic versioning, then list and read them back, so I can manage a project's documents without hand-rolling content hashing, version tracking, or path bookkeeping.

**Expected Behavior / Usage:**

Uploading a file into a project's data room takes a path, Base64-encoded content, a content type, a `changeBy` author identity, an access level, and optional denormalized metadata (description, categories, tags, plain-text preview, and an encryption-metadata block whose fields are stored and echoed verbatim). On success the response returns the data-room entry: its path, a generated file reference id (`ref`), its owning project's account name, and the file's latest version — version number (starting at 1), a deterministic content hash computed from the bytes, content type, author, access level, description, categories, tags, and encryption metadata. The same file then appears in the data room's entry listing with a total count, each node carrying its path, ref, author, and the denormalized latest-version metadata. Generated reference ids are non-deterministic and rendered as stable placeholders.

**Test Cases:** `rcb_tests/public_test_cases/feature3_data_room.json`

```json
{
  "description": "Upload a versioned file into a project's data room and read it back from the entry listing.",
  "cases": [
    {
      "input": {
        "operations": [
          {
            "query": "\nmutation ($ipnftSymbol: String!, $ipnftUid: String!, $ipnftAddress: String!, $ipnftTokenId: Int!) {\n  molecule {\n    v2 {\n      createProject(ipnftSymbol: $ipnftSymbol, ipnftUid: $ipnftUid, ipnftAddress: $ipnftAddress, ipnftTokenId: $ipnftTokenId) {\n        isSuccess\n        message\n        __typename\n        ... on CreateProjectSuccess {\n          project {\n            account { id accountName }\n            ipnftUid\n            dataRoom { id alias }\n            announcements { id alias }\n          }\n        }\n      }\n    }\n  }\n}\n",
            "variables": {
              "ipnftSymbol": "vitafast",
              "ipnftUid": "0xcaD88677CA87a7815728C72D74B4ff4982d54Fc1_9",
              "ipnftAddress": "0xcaD88677CA87a7815728C72D74B4ff4982d54Fc1",
              "ipnftTokenId": "9"
            },
            "emit": false
          },
          {
            "query": "\nmutation ($ipnftUid: String!, $path: CollectionPath!, $content: Base64Usnp!, $contentType: String!, $changeBy: String!, $accessLevel: String!, $description: String, $categories: [String!], $tags: [String!], $contentText: String, $encryptionMetadata: MoleculeEncryptionMetadataInput) {\n  molecule { v2 { project(ipnftUid: $ipnftUid) { dataRoom {\n    uploadFile(path: $path, content: $content, contentType: $contentType, changeBy: $changeBy, accessLevel: $accessLevel, description: $description, categories: $categories, tags: $tags, contentText: $contentText, encryptionMetadata: $encryptionMetadata) {\n      isSuccess\n      message\n      ... on MoleculeDataRoomFinishUploadFileResultSuccess {\n        entry {\n          project { account { accountName } }\n          path\n          ref\n          asVersionedFile { latest {\n            version contentHash contentType changeBy accessLevel description categories tags\n            encryptionMetadata { dataToEncryptHash accessControlConditions encryptedBy encryptedAt chain litSdkVersion litNetwork templateName contractVersion }\n          } }\n        }\n      }\n    }\n  } } } }\n}\n",
            "variables": {
              "ipnftUid": "0xcaD88677CA87a7815728C72D74B4ff4982d54Fc1_9",
              "path": "/foo.txt",
              "content": "aGVsbG8",
              "contentType": "text/plain",
              "changeBy": "did:ethr:0x43f3F090af7fF638ad0EfD64c5354B6945fE75BC",
              "accessLevel": "public",
              "description": "Plain text file",
              "categories": [
                "test-category"
              ],
              "tags": [
                "test-tag1",
                "test-tag2"
              ],
              "contentText": "hello",
              "encryptionMetadata": {
                "dataToEncryptHash": "EM1",
                "accessControlConditions": "EM2",
                "encryptedBy": "EM3",
                "encryptedAt": "EM4",
                "chain": "EM5",
                "litSdkVersion": "EM6",
                "litNetwork": "EM7",
                "templateName": "EM8",
                "contractVersion": "EM9"
              }
            }
          },
          {
            "query": "\nquery ($ipnftUid: String!) {\n  molecule { v2 { project(ipnftUid: $ipnftUid) { dataRoom { latest { entries {\n    totalCount\n    nodes {\n      path\n      ref\n      changeBy\n      asVersionedFile { latest { contentType categories tags accessLevel version description } }\n    }\n  } } } } } }\n}\n",
            "variables": {
              "ipnftUid": "0xcaD88677CA87a7815728C72D74B4ff4982d54Fc1_9"
            }
          }
        ]
      },
      "expected_output": "--- operation 1 ---\ndata:\n{\n  \"molecule\": {\n    \"v2\": {\n      \"project\": {\n        \"dataRoom\": {\n          \"uploadFile\": {\n            \"entry\": {\n              \"asVersionedFile\": {\n                \"latest\": {\n                  \"accessLevel\": \"public\",\n                  \"categories\": [\n                    \"test-category\"\n                  ],\n                  \"changeBy\": \"did:ethr:0x43f3F090af7fF638ad0EfD64c5354B6945fE75BC\",\n                  \"contentHash\": \"f16203338be694f50c5f338814986cdf0686453a888b84f424d792af4b9202398f392\",\n                  \"contentType\": \"text/plain\",\n                  \"description\": \"Plain text file\",\n                  \"encryptionMetadata\": {\n                    \"accessControlConditions\": \"EM2\",\n                    \"chain\": \"EM5\",\n                    \"contractVersion\": \"EM9\",\n                    \"dataToEncryptHash\": \"EM1\",\n                    \"encryptedAt\": \"EM4\",\n                    \"encryptedBy\": \"EM3\",\n                    \"litNetwork\": \"EM7\",\n                    \"litSdkVersion\": \"EM6\",\n                    \"templateName\": \"EM8\"\n                  },\n                  \"tags\": [\n                    \"test-tag1\",\n                    \"test-tag2\"\n                  ],\n                  \"version\": 1\n                }\n              },\n              \"path\": \"/foo.txt\",\n              \"project\": {\n                \"account\": {\n                  \"accountName\": \"molecule.vitafast\"\n                }\n              },\n              \"ref\": \"<did-3>\"\n            },\n            \"isSuccess\": true,\n            \"message\": \"\"\n          }\n        }\n      }\n    }\n  }\n}\n--- operation 2 ---\ndata:\n{\n  \"molecule\": {\n    \"v2\": {\n      \"project\": {\n        \"dataRoom\": {\n          \"latest\": {\n            \"entries\": {\n              \"nodes\": [\n                {\n                  \"asVersionedFile\": {\n                    \"latest\": {\n                      \"accessLevel\": \"public\",\n                      \"categories\": [\n                        \"test-category\"\n                      ],\n                      \"contentType\": \"text/plain\",\n                      \"description\": \"Plain text file\",\n                      \"tags\": [\n                        \"test-tag1\",\n                        \"test-tag2\"\n                      ],\n                      \"version\": 1\n                    }\n                  },\n                  \"changeBy\": \"did:ethr:0x43f3F090af7fF638ad0EfD64c5354B6945fE75BC\",\n                  \"path\": \"/foo.txt\",\n                  \"ref\": \"<did-3>\"\n                }\n              ],\n              \"totalCount\": 1\n            }\n          }\n        }\n      }\n    }\n  }\n}\n"
    }
  ]
}
```

---

### Feature 4: Announcements with Validated Attachments

**As a developer**, I want to publish project announcements that may attach existing data-room files, with attachment validation and a newest-first feed, so I can broadcast project updates while guaranteeing every linked file actually exists.

**Expected Behavior / Usage:**

Creating an announcement takes a headline, body, access level, author (`moleculeChangeBy`), categories, tags, and an optional list of attachment references (file ids). When every attachment references an existing data-room file, the announcement is accepted and a success-typed result returns a generated `announcementId`. When any attachment references a non-existent file id, the announcement is rejected with an invalid-attachment-typed result whose message lists the missing id(s); no announcement is recorded. The per-project announcements tail lists accepted announcements with a total count, each node exposing its id, headline, body, attachments, access level, author, categories, and tags. Generated announcement ids appear as stable UUID placeholders and file ids as stable `did` placeholders, with the same raw value always mapping to the same placeholder.

**Test Cases:** `rcb_tests/public_test_cases/feature4_announcements.json`

```json
{
  "description": "Publish an announcement with a valid attachment and list it; an announcement referencing a non-existent attachment is rejected.",
  "cases": [
    {
      "input": {
        "operations": [
          {
            "query": "\nmutation ($ipnftSymbol: String!, $ipnftUid: String!, $ipnftAddress: String!, $ipnftTokenId: Int!) {\n  molecule {\n    v2 {\n      createProject(ipnftSymbol: $ipnftSymbol, ipnftUid: $ipnftUid, ipnftAddress: $ipnftAddress, ipnftTokenId: $ipnftTokenId) {\n        isSuccess\n        message\n        __typename\n        ... on CreateProjectSuccess {\n          project {\n            account { id accountName }\n            ipnftUid\n            dataRoom { id alias }\n            announcements { id alias }\n          }\n        }\n      }\n    }\n  }\n}\n",
            "variables": {
              "ipnftSymbol": "vitafast",
              "ipnftUid": "0xcaD88677CA87a7815728C72D74B4ff4982d54Fc1_9",
              "ipnftAddress": "0xcaD88677CA87a7815728C72D74B4ff4982d54Fc1",
              "ipnftTokenId": "9"
            },
            "emit": false
          },
          {
            "query": "\nmutation ($ipnftUid: String!, $path: CollectionPath!, $content: Base64Usnp!, $contentType: String!, $changeBy: String!, $accessLevel: String!, $description: String, $categories: [String!], $tags: [String!], $contentText: String, $encryptionMetadata: MoleculeEncryptionMetadataInput) {\n  molecule { v2 { project(ipnftUid: $ipnftUid) { dataRoom {\n    uploadFile(path: $path, content: $content, contentType: $contentType, changeBy: $changeBy, accessLevel: $accessLevel, description: $description, categories: $categories, tags: $tags, contentText: $contentText, encryptionMetadata: $encryptionMetadata) {\n      isSuccess\n      message\n      ... on MoleculeDataRoomFinishUploadFileResultSuccess { entry { ref } }\n    }\n  } } } }\n}\n",
            "variables": {
              "ipnftUid": "0xcaD88677CA87a7815728C72D74B4ff4982d54Fc1_9",
              "path": "/foo.txt",
              "content": "aGVsbG8gZm9v",
              "contentType": "text/plain",
              "changeBy": "did:ethr:0x43f3F090af7fF638ad0EfD64c5354B6945fE75BC",
              "accessLevel": "public",
              "description": "Plain text file (foo)",
              "categories": [
                "test-category"
              ],
              "tags": [
                "test-tag1",
                "test-tag2"
              ],
              "contentText": "hello foo",
              "encryptionMetadata": {
                "dataToEncryptHash": "EM1",
                "accessControlConditions": "EM2",
                "encryptedBy": "EM3",
                "encryptedAt": "EM4",
                "chain": "EM5",
                "litSdkVersion": "EM6",
                "litNetwork": "EM7",
                "templateName": "EM8",
                "contractVersion": "EM9"
              }
            },
            "emit": false,
            "capture": {
              "file1": [
                "molecule",
                "v2",
                "project",
                "dataRoom",
                "uploadFile",
                "entry",
                "ref"
              ]
            }
          },
          {
            "query": "\nmutation ($ipnftUid: String!, $headline: String!, $body: String!, $attachments: [DatasetID!], $moleculeAccessLevel: String!, $moleculeChangeBy: String!, $categories: [String!]!, $tags: [String!]!) {\n  molecule { v2 { project(ipnftUid: $ipnftUid) { announcements {\n    create(headline: $headline, body: $body, attachments: $attachments, moleculeAccessLevel: $moleculeAccessLevel, moleculeChangeBy: $moleculeChangeBy, categories: $categories, tags: $tags) {\n      isSuccess\n      message\n      __typename\n      ... on CreateAnnouncementSuccess { announcementId }\n    }\n  } } } }\n}\n",
            "variables": {
              "ipnftUid": "0xcaD88677CA87a7815728C72D74B4ff4982d54Fc1_9",
              "headline": "Test announcement 1",
              "body": "Blah blah 1",
              "attachments": [
                "$file1"
              ],
              "moleculeAccessLevel": "holders",
              "moleculeChangeBy": "did:ethr:0x43f3F090af7fF638ad0EfD64c5354B6945fE75BC",
              "categories": [
                "test-category-1"
              ],
              "tags": [
                "test-tag1",
                "test-tag2"
              ]
            }
          },
          {
            "query": "\nmutation ($ipnftUid: String!, $headline: String!, $body: String!, $attachments: [DatasetID!], $moleculeAccessLevel: String!, $moleculeChangeBy: String!, $categories: [String!]!, $tags: [String!]!) {\n  molecule { v2 { project(ipnftUid: $ipnftUid) { announcements {\n    create(headline: $headline, body: $body, attachments: $attachments, moleculeAccessLevel: $moleculeAccessLevel, moleculeChangeBy: $moleculeChangeBy, categories: $categories, tags: $tags) {\n      isSuccess\n      message\n      __typename\n      ... on CreateAnnouncementSuccess { announcementId }\n    }\n  } } } }\n}\n",
            "variables": {
              "ipnftUid": "0xcaD88677CA87a7815728C72D74B4ff4982d54Fc1_9",
              "headline": "Test announcement 2",
              "body": "Blah blah 2",
              "attachments": [
                "$file1",
                "did:odf:fed011ba79f25e520298ba6945dd6197083a366364bef178d5899b100c434748d88e5"
              ],
              "moleculeAccessLevel": "holders",
              "moleculeChangeBy": "did:ethr:0x43f3F090af7fF638ad0EfD64c5354B6945fE75BC",
              "categories": [],
              "tags": [
                "test-tag1"
              ]
            }
          },
          {
            "query": "\nquery ($ipnftUid: String!) {\n  molecule { v2 { project(ipnftUid: $ipnftUid) { announcements { tail {\n    totalCount\n    nodes { id headline body attachments accessLevel changeBy categories tags }\n  } } } } }\n}\n",
            "variables": {
              "ipnftUid": "0xcaD88677CA87a7815728C72D74B4ff4982d54Fc1_9"
            }
          }
        ]
      },
      "expected_output": "--- operation 1 ---\ndata:\n{\n  \"molecule\": {\n    \"v2\": {\n      \"project\": {\n        \"announcements\": {\n          \"create\": {\n            \"__typename\": \"CreateAnnouncementSuccess\",\n            \"announcementId\": \"[stable placeholders for volatile identifiers (e.g., '<did-X>'), ask for the specific string format]\",\n            \"isSuccess\": true,\n            \"message\": \"\"\n          }\n        }\n      }\n    }\n  }\n}\n--- operation 2 ---\ndata:\n{\n  \"molecule\": {\n    \"v2\": {\n      \"project\": {\n        \"announcements\": {\n          \"create\": {\n            \"__typename\": \"CreateAnnouncementErrorInvalidAttachment\",\n            \"isSuccess\": false,\n            \"message\": \"Not found attachment(s): [<did-4>]\"\n          }\n        }\n      }\n    }\n  }\n}\n--- operation 3 ---\ndata:\n{\n  \"molecule\": {\n    \"v2\": {\n      \"project\": {\n        \"announcements\": {\n          \"tail\": {\n            \"nodes\": [\n              {\n                \"accessLevel\": \"holders\",\n                \"attachments\": [\n                  \"<did-3>\"\n                ],\n                \"body\": \"Blah blah 1\",\n                \"categories\": [\n                  \"test-category-1\"\n                ],\n                \"changeBy\": \"did:ethr:0x43f3F090af7fF638ad0EfD64c5354B6945fE75BC\",\n                \"headline\": \"Test announcement 1\",\n                \"id\": \"[stable placeholders for volatile identifiers (e.g., '<did-X>'), ask for the specific string format]\",\n                \"tags\": [\n                  \"test-tag1\",\n                  \"test-tag2\"\n                ]\n              }\n            ],\n            \"totalCount\": 1\n          }\n        }\n      }\n    }\n  }\n}\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing project provisioning, lifecycle control, the versioned data room, and announcements over a content-addressed versioned-storage layer, with the GraphQL API surface separated from the core domain use-cases.

2. **The Execution/Test Adapter:** A runnable adapter that acts as a client to the core system. It reads a JSON scenario (the `create_projects_dataset` flag plus an ordered `operations` list), executes each GraphQL operation against a freshly provisioned environment, threads captured runtime values between operations, normalizes volatile ids to stable placeholders, and prints the rendered response stream to stdout exactly per the per-feature contracts above. This adapter is logically and physically separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_project_provisioning.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_project_provisioning@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- validation logic for attachment existence in announcements
- echoing encryption metadata to the result
