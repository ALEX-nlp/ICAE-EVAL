## Product Requirement Document

# Torrent Client Metrics Exporter - Prometheus-Oriented Monitoring Adapter

## Project Goal

Build a metrics exporter for a torrent client web API that allows developers to publish service health, transfer counters, and torrent inventory metrics to Prometheus without manually querying the remote API and formatting metric families.

---

## Background & Problem

Without this library/tool, developers are forced to assemble web UI endpoints, call multiple remote API surfaces, tolerate transient API failures, filter torrents by state and category, and hand-format Prometheus metric families. This leads to repetitive monitoring code, inconsistent labels, fragile error handling, and dashboards that are hard to maintain.

With this library/tool, deployment configuration and remote API snapshots are transformed into stable, labeled metrics that can be scraped and tested through a single execution adapter.

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

### Feature 1: Monitored Endpoint Resolution

**As a developer**, I want to derive the monitored service address from deployment settings, so I can connect the exporter to different web UI deployments without hand-building URLs.

**Expected Behavior / Usage:**

The adapter accepts an `endpoint` command with a configuration object containing host, port, secure-transport flag, optional URL base path, credentials, certificate verification flag, and metric prefix. It outputs the normalized server label and full endpoint URL. The server label is `host:port` plus the URL base path when one is supplied. The endpoint uses `https` when secure transport is requested or when the port is `443`; otherwise it uses `http`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_endpoint_resolution.json`

```json
{
    "description": "Build the monitored service endpoint from host, port, secure-transport flag, and optional URL base path.",
    "cases": [
        {
            "input": {
                "operation": "endpoint",
                "config": {
                    "host": "localhost",
                    "port": "[a specific sentinel value — ask the PM for the exact string]0[a specific sentinel value — ask the PM for the exact string]0",
                    "ssl": false,
                    "url_base": "qbt/",
                    "username": "user",
                    "password": "pass",
                    "verify_webui_certificate": false,
                    "metrics_prefix": "qbittorrent"
                }
            },
            "expected_output": "server=localhost:[a specific sentinel value — ask the PM for the exact string]0[a specific sentinel value — ask the PM for the exact string]0/qbt/\nendpoint=http://localhost:[a specific sentinel value — ask the PM for the exact string]0[a specific sentinel value — ask the PM for the exact string]0/qbt/\n"
        },
        {
            "input": {
                "operation": "endpoint",
                "config": {
                    "host": "qbittorrent.example.com",
                    "port": "[a specific sentinel value — ask the PM for the exact string]0[a specific sentinel value — ask the PM for the exact string]1",
                    "ssl": false,
                    "url_base": "qbittorrent/",
                    "username": "user",
                    "password": "pass",
                    "verify_webui_certificate": false,
                    "metrics_prefix": "qbittorrent"
                }
            },
            "expected_output": "server=qbittorrent.example.com:[a specific sentinel value — ask the PM for the exact string]0[a specific sentinel value — ask the PM for the exact string]1/qbittorrent/\nendpoint=http://qbittorrent.example.com:[a specific sentinel value — ask the PM for the exact string]0[a specific sentinel value — ask the PM for the exact string]1/qbittorrent/\n"
        }
    ]
}
```

---

### Feature 2: Metric Record Defaults

**As a developer**, I want a compact metric record representation with sensible defaults, so I can describe measured values without repeating empty metadata.

**Expected Behavior / Usage:**

The adapter accepts a `metric_record` command with a metric name and value. Optional labels, help text, and metric type may be omitted. When omitted, labels are an empty object, help text is an empty string, and the metric type is `gauge`. The output lists the metric name, type, value, serialized labels, and help text on separate lines.

**Test Cases:** `rcb_tests/public_test_cases/feature2_metric_record_defaults.json`

```json
{
    "description": "Represent a single metric record with its name and value while applying default labels, help text, and gauge type when optional metadata is omitted.",
    "cases": [
        {
            "input": {
                "operation": "metric_record",
                "name": "test_metric",
                "value": 10
            },
            "expected_output": "metric_name=test_metric\nmetric_type=gauge\nvalue=10\nlabels=[a specific sentinel value — ask the PM for the exact string]\nhelp=\n"
        }
    ]
}
```

---

### Feature 3: Prometheus Metric Family Rendering

**As a developer**, I want metric records rendered as Prometheus-compatible gauge or counter families, so metric metadata and sample data can be scraped consistently.

**Expected Behavior / Usage:**

The adapter accepts a `metric_family` command containing a metric object with name, metric type, help text, labels, and value. Gauge metrics produce a gauge family whose sample name equals the metric name. Counter metrics produce a counter family and expose the counter sample name with the conventional `_total` suffix. The output includes the family type, family name, documentation string, sample name, JSON labels, and sample value.

**Test Cases:** `rcb_tests/public_test_cases/feature3_prometheus_family_rendering.json`

```json
{
    "description": "Convert a metric record into the corresponding Prometheus gauge or counter family with documentation, labels, sample name, and sample value preserved.",
    "cases": [
        {
            "input": {
                "operation": "metric_family",
                "metric": {
                    "name": "test_gauge",
                    "metric_type": "gauge",
                    "help": "Test Gauge",
                    "labels": {
                        "label1": "value1",
                        "server": "localhost:[a specific sentinel value — ask the PM for the exact string]0[a specific sentinel value — ask the PM for the exact string]0"
                    },
                    "value": 10
                }
            },
            "expected_output": "family_type=gauge\nfamily_name=test_gauge\ndocumentation=Test Gauge\nsample_name=test_gauge\nsample_labels={\"label1\":\"value1\",\"server\":\"localhost:[a specific sentinel value — ask the PM for the exact string]0[a specific sentinel value — ask the PM for the exact string]0\"}\nsample_value=10\n"
        }
    ]
}
```

---

### Feature 4: Category Catalog Fetching

**As a developer**, I want the exporter to read the remote category catalog safely, so category-based metrics can be built from ordinary structured data.

**Expected Behavior / Usage:**

The adapter accepts a `category_catalog` command with either a category map or a source-error flag. When category data is available, the output is a single `categories=` line containing a stable JSON object of category entries. When the category source cannot be read, the output is an empty JSON object rather than an exception or partial runtime trace.

**Test Cases:** `rcb_tests/public_test_cases/feature4_category_catalog_fetch.json`

```json
{
    "description": "Return the category catalog from the remote service as ordinary JSON objects, and return an empty catalog when the category source cannot be read.",
    "cases": [
        {
            "input": {
                "operation": "category_catalog",
                "categories": {
                    "category1": {
                        "name": "Category 1"
                    },
                    "category2": {
                        "name": "Category 2"
                    },
                    "category3": {
                        "name": "Category 3"
                    }
                }
            },
            "expected_output": "categories={\"category1\":{\"name\":\"Category 1\"},\"category2\":{\"name\":\"Category 2\"},\"category3\":{\"name\":\"Category 3\"}}\n"
        }
    ]
}
```

---

### Feature 5: Torrent List Fetching

**As a developer**, I want the exporter to read torrent rows safely, so downstream filters and counters operate on a predictable list.

**Expected Behavior / Usage:**

The adapter accepts a `torrent_list` command with either a list of torrent objects or a source-error flag. When torrent data is available, the output is a single `torrents=` line containing the list as stable JSON. When the torrent source cannot be read, the output is an empty list rather than an exception or partial runtime trace.

**Test Cases:** `rcb_tests/public_test_cases/feature5_torrent_list_fetch.json`

```json
{
    "description": "Return the torrent list from the remote service as ordinary JSON objects, and return an empty list when the torrent source cannot be read.",
    "cases": [
        {
            "input": {
                "operation": "torrent_list",
                "torrents": [
                    {
                        "name": "Torrent 1",
                        "size": 100
                    },
                    {
                        "name": "Torrent 2",
                        "size": 200
                    },
                    {
                        "name": "Torrent 3",
                        "size": 300
                    }
                ]
            },
            "expected_output": "torrents=[{\"name\":\"Torrent 1\",\"size\":100},{\"name\":\"Torrent 2\",\"size\":200},{\"name\":\"Torrent 3\",\"size\":300}]\n"
        }
    ]
}
```

---

### Feature 6: Torrent State Filtering

**As a developer**, I want to select torrents by lifecycle state, so per-state metrics count exactly the torrents in that state.

**Expected Behavior / Usage:**

The adapter accepts a `select_by_state` command with a requested state and a list of torrent objects containing state fields. It returns only torrents whose state exactly equals the requested state, preserving the original order and object content. If no torrent matches, the output list is empty.

**Test Cases:** `rcb_tests/public_test_cases/feature6_state_filtering.json`

```json
{
    "description": "Select only torrents whose state exactly matches the requested torrent state; unmatched states produce an empty list.",
    "cases": [
        {
            "input": {
                "operation": "select_by_state",
                "state": "downloading",
                "torrents": [
                    {
                        "name": "Torrent DOWNLOADING 1",
                        "state": "downloading"
                    },
                    {
                        "name": "Torrent UPLOADING 1",
                        "state": "uploading"
                    },
                    {
                        "name": "Torrent DOWNLOADING 2",
                        "state": "downloading"
                    },
                    {
                        "name": "Torrent UPLOADING 2",
                        "state": "uploading"
                    }
                ]
            },
            "expected_output": "torrents=[{\"name\":\"Torrent DOWNLOADING 1\",\"state\":\"downloading\"},{\"name\":\"Torrent DOWNLOADING 2\",\"state\":\"downloading\"}]\n"
        }
    ]
}
```

---

### Feature 7: Torrent Category Filtering

**As a developer**, I want to select torrents by category, so per-category metrics reflect both named categories and uncategorized torrents.

**Expected Behavior / Usage:**

The adapter accepts a `select_by_category` command with a requested category and a list of torrent objects containing category fields. It returns torrents whose category exactly equals the requested category. When the requested category is `Uncategorized`, torrents with a blank category are included together with torrents explicitly labeled `Uncategorized`. If no torrent matches, the output list is empty.

**Test Cases:** `rcb_tests/public_test_cases/feature7_category_filtering.json`

```json
{
    "description": "Select only torrents whose category matches the requested category, treating a blank torrent category as Uncategorized when that category is requested.",
    "cases": [
        {
            "input": {
                "operation": "select_by_category",
                "category": "Movies",
                "torrents": [
                    {
                        "name": "Torrent Movies 1",
                        "category": "Movies"
                    },
                    {
                        "name": "Torrent Music 1",
                        "category": "Music"
                    },
                    {
                        "name": "Torrent Movies 2",
                        "category": "Movies"
                    },
                    {
                        "name": "Torrent unknown",
                        "category": ""
                    },
                    {
                        "name": "Torrent Music 2",
                        "category": "Music"
                    },
                    {
                        "name": "Torrent Uncategorized 1",
                        "category": "Uncategorized"
                    }
                ]
            },
            "expected_output": "torrents=[{\"category\":\"Movies\",\"name\":\"Torrent Movies 1\"},{\"category\":\"Movies\",\"name\":\"Torrent Movies 2\"}]\n"
        }
    ]
}
```

---

### Feature [a specific sentinel value — ask the PM for the exact string]: Torrent Count Metric Construction

**As a developer**, I want to turn a state/category count into a labeled metric, so the exporter can publish torrent inventory counts by dimension.

**Expected Behavior / Usage:**

The adapter accepts a `torrent_count_metric` command with a state string, category string, count, and optional configuration. It outputs a gauge metric named with the configured prefix and `_torrents_count` suffix. The metric value is the supplied count. Labels include the state as `status`, the category as `category`, and the normalized server label. The help text states that the metric is the number of torrents in the supplied status under the supplied category, including empty strings when supplied.

**Test Cases:** `rcb_tests/public_test_cases/feature[a specific sentinel value — ask the PM for the exact string]_torrent_count_metric.json`

```json
{
    "description": "Create a gauge metric that reports the number of torrents for a specific state and category, preserving both values as labels along with the monitored server label.",
    "cases": [
        {
            "input": {
                "operation": "torrent_count_metric",
                "state": "downloading",
                "category": "movies",
                "count": 10,
                "config": {
                    "metrics_prefix": "qbittorrent"
                }
            },
            "expected_output": "metric_name=qbittorrent_torrents_count\nmetric_type=gauge\nvalue=10\nlabels={\"category\":\"movies\",\"server\":\"localhost:[a specific sentinel value — ask the PM for the exact string]0[a specific sentinel value — ask the PM for the exact string]0/qbt/\",\"status\":\"downloading\"}\nhelp=Number of torrents in status downloading under category movies\n"
        }
    ]
}
```

---

### Feature 9: Server Status Metrics

**As a developer**, I want remote service status converted into a fixed set of health and transfer metrics, so monitoring can distinguish availability, connectivity, firewall state, peer discovery, and byte counters.

**Expected Behavior / Usage:**

The adapter accepts a `status_metrics` command with a server version and synchronized server-state object. It outputs eight metrics in order: service up, connected, firewalled, DHT nodes, session download bytes, session upload bytes, all-time download bytes, and all-time upload bytes. The up metric is true when server-state data is present and carries both version and server labels. Connected and firewalled are booleans derived from the connection status. Missing numeric fields default to zero. Transfer byte metrics are counters; the others are gauges.

**Test Cases:** `rcb_tests/public_test_cases/feature9_server_status_metrics.json`

```json
{
    "description": "Produce service health and transfer metrics from synchronized server state, including connectivity booleans, DHT node count, transfer counters, version, and server labels.",
    "cases": [
        {
            "input": {
                "operation": "status_metrics",
                "version": "1.2.3",
                "server_state": {
                    "connection_status": "connected"
                }
            },
            "expected_output": "metric_count=[a specific sentinel value — ask the PM for the exact string]\nmetric[0].name=qbittorrent_up\nmetric[0].type=gauge\nmetric[0].value=True\nmetric[0].labels={\"server\":\"localhost:[a specific sentinel value — ask the PM for the exact string]0[a specific sentinel value — ask the PM for the exact string]0/qbt/\",\"version\":\"1.2.3\"}\nmetric[0].help=Whether the qBittorrent server is answering requests from this exporter. A `version` label with the server version is added.\nmetric[1].name=qbittorrent_connected\nmetric[1].type=gauge\nmetric[1].value=True\nmetric[1].labels={\"server\":\"localhost:[a specific sentinel value — ask the PM for the exact string]0[a specific sentinel value — ask the PM for the exact string]0/qbt/\"}\nmetric[1].help=Whether the qBittorrent server is connected to the Bittorrent network.\nmetric[2].name=qbittorrent_firewalled\nmetric[2].type=gauge\nmetric[2].value=False\nmetric[2].labels={\"server\":\"localhost:[a specific sentinel value — ask the PM for the exact string]0[a specific sentinel value — ask the PM for the exact string]0/qbt/\"}\nmetric[2].help=Whether the qBittorrent server is connected to the Bittorrent network but is behind a firewall.\nmetric[3].name=qbittorrent_dht_nodes\nmetric[3].type=gauge\nmetric[3].value=0\nmetric[3].labels={\"server\":\"localhost:[a specific sentinel value — ask the PM for the exact string]0[a specific sentinel value — ask the PM for the exact string]0/qbt/\"}\nmetric[3].help=Number of DHT nodes connected to.\nmetric[4].name=qbittorrent_dl_info_data\nmetric[4].type=counter\nmetric[4].value=0\nmetric[4].labels={\"server\":\"localhost:[a specific sentinel value — ask the PM for the exact string]0[a specific sentinel value — ask the PM for the exact string]0/qbt/\"}\nmetric[4].help=Data downloaded since the server started, in bytes.\nmetric[5].name=qbittorrent_up_info_data\nmetric[5].type=counter\nmetric[5].value=0\nmetric[5].labels={\"server\":\"localhost:[a specific sentinel value — ask the PM for the exact string]0[a specific sentinel value — ask the PM for the exact string]0/qbt/\"}\nmetric[5].help=Data uploaded since the server started, in bytes.\nmetric[6].name=qbittorrent_alltime_dl\nmetric[6].type=counter\nmetric[6].value=0\nmetric[6].labels={\"server\":\"localhost:[a specific sentinel value — ask the PM for the exact string]0[a specific sentinel value — ask the PM for the exact string]0/qbt/\"}\nmetric[6].help=Total historical data downloaded, in bytes.\nmetric[7].name=qbittorrent_alltime_ul\nmetric[7].type=counter\nmetric[7].value=0\nmetric[7].labels={\"server\":\"localhost:[a specific sentinel value — ask the PM for the exact string]0[a specific sentinel value — ask the PM for the exact string]0/qbt/\"}\nmetric[7].help=Total historical data uploaded, in bytes.\n"
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
- fill in the state and category placeholders from the current selection context
- match the version derivation pattern used in the first line of output
