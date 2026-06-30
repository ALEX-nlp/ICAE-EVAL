## Product Requirement Document

# Network Traffic Text Monitor - Format and Summarize Live Connection Usage

## Project Goal

Build a command-line network traffic monitor that allows developers and operators to inspect current bandwidth usage by process, connection, and remote endpoint without manually correlating packet captures, socket tables, byte counts, and display formatting.

---

## Background & Problem

Without this tool, developers are forced to combine low-level packet inspection with separate process lookup and manual byte-rate calculations. This leads to repetitive analysis, easy mistakes when grouping traffic by endpoint, and inconsistent reporting across terminal and raw-text workflows.

With this tool, captured network frames can be translated into readable bandwidth summaries that show which process, connection, or remote endpoint is responsible for upload and download activity, with predictable units and machine-comparable raw output.

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

### Feature 1: Bandwidth Unit Formatting

**As a developer**, I want to format byte-per-second rates in multiple unit families, so I can present network throughput consistently for small and large values.

**Expected Behavior / Usage:**

The execution adapter accepts a text command with `action=format_bandwidth`, a numeric `bytes_per_second` value, and a `unit_family` of `bin_bytes`, `bin_bits`, `si_bytes`, or `si_bits`. It prints exactly one formatted throughput line. Binary byte units use B, KiB, MiB, GiB, TiB, and PiB based on powers of 1024. Binary bit units convert bytes to bits and use b, Kib, Mib, Gib, Tib, and Pib. SI byte units use B, kB, MB, GB, TB, and PB based on powers of 1000. SI bit units convert bytes to bits and use b, kb, Mb, Gb, Tb, and Pb. The numeric component is always rounded to two decimal places.

**Test Cases:** `rcb_tests/public_test_cases/feature1_bandwidth_units.json`

```json
{
    "description": "Formats a numeric byte-per-second rate using the requested unit family and two decimal places, selecting the appropriate scale for small and large values.",
    "cases": [
        {
            "input": "action=format_bandwidth\nbytes_per_second=0.015625\nunit_family=bin_bytes\n",
            "expected_output": "0.02B\n"
        },
        {
            "input": "action=format_bandwidth\nbytes_per_second=1024\nunit_family=bin_bytes\n",
            "expected_output": "1.00KiB\n"
        },
        {
            "input": "action=format_bandwidth\nbytes_per_second=1024\nunit_family=bin_bits\n",
            "expected_output": "8.00Kib\n"
        },
        {
            "input": "action=format_bandwidth\nbytes_per_second=1024\nunit_family=si_bytes\n",
            "expected_output": "1.02kB\n"
        },
        {
            "input": "action=format_bandwidth\nbytes_per_second=1024\nunit_family=si_bits\n",
            "expected_output": "8.19kb\n"
        }
    ]
}
```

---

### Feature 2: Raw Traffic Reporting

**As a developer**, I want captured packet activity to be rendered as raw text, so I can compare traffic summaries in automated environments without a terminal UI.

**Expected Behavior / Usage:**

Raw reporting emits one or more `Refreshing:` sections. A section with no visible packet activity prints `[a specific sentinel string (consult spec doc)]`. Sections with traffic print process rows, connection rows, and remote address rows. Each row includes normalized timestamp text, upload and download byte-per-second values, and the relevant grouping signal: process name and connection count for process rows, interface, local port, remote endpoint, protocol, and process for connection rows, and endpoint plus connection count for remote address rows.

*2.1 Single Packet Capture Summary — A single TCP packet is summarized into process, connection, and remote endpoint rows.*

The execution adapter accepts `action=raw_snapshot` with a `scenario` value representing a captured single-packet sample. The output must include an initial no-traffic refresh followed by a refresh that reports the packet's direction-specific rate, the local interface marker, local and remote ports, protocol, process identity, and remote address aggregate.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_packet_capture_summary.json`

```json
{
    "description": "Summarizes a single captured TCP packet as raw text, including refresh markers, process totals, connection details, remote address totals, direction-specific rates, ports, protocol, and the interface name.",
    "cases": [
        {
            "input": "action=raw_snapshot\nscenario=one_ethernet_packet\n",
            "expected_output": "Refreshing:\n[a specific sentinel string (consult spec doc)]\n\nRefreshing:\nprocess: [a specific placeholder literal] \"1\" up/down Bps: 21/0 connections: 1\nconnection: [a specific placeholder literal] <interface_name>:443 => 1.1.1.1:12345 (tcp) up/down Bps: 21/0 process: \"1\"\nremote_address: [a specific placeholder literal] 1.1.1.1 up/down Bps: 21/0 connections: 1\n\n"
        }
    ]
}
```

*2.2 Traffic Aggregation — Multiple packets are grouped by process, connection, and remote endpoint.*

The execution adapter accepts `action=raw_snapshot` with a `scenario` value representing packets across one or more connections. The output must aggregate byte-per-second values separately for upload and download, combine packets that belong to the same connection, count distinct connections per process and remote endpoint, and emit enough row detail to distinguish process totals from connection totals and remote-address totals.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_traffic_aggregation.json`

```json
{
    "description": "Aggregates packet traffic into raw text rows by process, connection, and remote address, preserving separate upload and download byte-per-second totals and connection counts.",
    "cases": [
        {
            "input": "action=raw_snapshot\nscenario=bidirectional_single_connection\n",
            "expected_output": "Refreshing:\n[a specific sentinel string (consult spec doc)]\n\nRefreshing:\nprocess: [a specific placeholder literal] \"1\" up/down Bps: 24/25 connections: 1\nconnection: [a specific placeholder literal] <interface_name>:443 => 1.1.1.1:12345 (tcp) up/down Bps: 24/25 process: \"1\"\nremote_address: [a specific placeholder literal] 1.1.1.1 up/down Bps: 24/25 connections: 1\n\n"
        },
        {
            "input": "action=raw_snapshot\nscenario=multiple_processes\n",
            "expected_output": "Refreshing:\n[a specific sentinel string (consult spec doc)]\n\nRefreshing:\nprocess: [a specific placeholder literal] \"5\" up/down Bps: 0/28 connections: 1\nprocess: [a specific placeholder literal] \"4\" up/down Bps: 0/26 connections: 1\nprocess: [a specific placeholder literal] \"1\" up/down Bps: 0/22 connections: 1\nprocess: [a specific placeholder literal] \"2\" up/down Bps: 0/21 connections: 1\nconnection: [a specific placeholder literal] <interface_name>:4435 => 3.3.3.3:1337 (tcp) up/down Bps: 0/28 process: \"5\"\nconnection: [a specific placeholder literal] <interface_name>:4434 => 2.2.2.2:54321 (tcp) up/down Bps: 0/26 process: \"4\"\nconnection: [a specific placeholder literal] <interface_name>:443 => 1.1.1.1:12345 (tcp) up/down Bps: 0/22 process: \"1\"\nconnection: [a specific placeholder literal] <interface_name>:4432 => 4.4.4.4:1337 (tcp) up/down Bps: 0/21 process: \"2\"\nremote_address: [a specific placeholder literal] 3.3.3.3 up/down Bps: 0/28 connections: 1\nremote_address: [a specific placeholder literal] 2.2.2.2 up/down Bps: 0/26 connections: 1\nremote_address: [a specific placeholder literal] 1.1.1.1 up/down Bps: 0/22 connections: 1\nremote_address: [a specific placeholder literal] 4.4.4.4 up/down Bps: 0/21 connections: 1\n\n"
        }
    ]
}
```

*2.3 Refresh Windows — Sustained captures are emitted as separate refresh snapshots.*

The execution adapter accepts `action=raw_snapshot` with a `scenario` value representing traffic separated by a refresh interval. The output must include a no-traffic startup section and then one text snapshot per refresh window. Byte-per-second values are reported for the packets observed in each window, while row structure remains stable across windows for the same process, connection, and remote endpoint.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_refresh_windows.json`

```json
{
    "description": "Emits a raw text snapshot for each refresh window, resetting per-window rates while retaining the same row structure for later packets in a sustained capture.",
    "cases": [
        {
            "input": "action=raw_snapshot\nscenario=sustained_one_process\n",
            "expected_output": "Refreshing:\n[a specific sentinel string (consult spec doc)]\n\nRefreshing:\nprocess: [a specific placeholder literal] \"1\" up/down Bps: 0/22 connections: 1\nconnection: [a specific placeholder literal] <interface_name>:443 => 1.1.1.1:12345 (tcp) up/down Bps: 0/22 process: \"1\"\nremote_address: [a specific placeholder literal] 1.1.1.1 up/down Bps: 0/22 connections: 1\n\nRefreshing:\nprocess: [a specific placeholder literal] \"1\" up/down Bps: 0/31 connections: 1\nconnection: [a specific placeholder literal] <interface_name>:443 => 1.1.1.1:12345 (tcp) up/down Bps: 0/31 process: \"1\"\nremote_address: [a specific placeholder literal] 1.1.1.1 up/down Bps: 0/31 connections: 1\n\n"
        }
    ]
}
```

*2.4 Name Resolution Control — Remote endpoints can be displayed as host names or numeric addresses.*

The execution adapter accepts `action=raw_snapshot` with a `scenario` value that either enables available name resolution or disables it. When a name is available and resolution is enabled, later connection and remote endpoint rows use the resolved host name. When resolution is disabled, rows keep numeric IP addresses even if names are available. Process totals, connection rates, remote endpoint counts, ports, and protocol remain unchanged by the display-name choice.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_name_resolution.json`

```json
{
    "description": "Controls whether remote endpoint rows use resolved host names or numeric addresses while keeping process, connection, rate, and count data intact.",
    "cases": [
        {
            "input": "action=raw_snapshot\nscenario=hostnames\n",
            "expected_output": "Refreshing:\n[a specific sentinel string (consult spec doc)]\n\nRefreshing:\nprocess: [a specific placeholder literal] \"1\" up/down Bps: 28/30 connections: 1\nprocess: [a specific placeholder literal] \"5\" up/down Bps: 17/18 connections: 1\nconnection: [a specific placeholder literal] <interface_name>:443 => 1.1.1.1:12345 (tcp) up/down Bps: 28/30 process: \"1\"\nconnection: [a specific placeholder literal] <interface_name>:4435 => 3.3.3.3:1337 (tcp) up/down Bps: 17/18 process: \"5\"\nremote_address: [a specific placeholder literal] 1.1.1.1 up/down Bps: 28/30 connections: 1\nremote_address: [a specific placeholder literal] 3.3.3.3 up/down Bps: 17/18 connections: 1\n\nRefreshing:\nprocess: [a specific placeholder literal] \"1\" up/down Bps: 31/32 connections: 1\nprocess: [a specific placeholder literal] \"5\" up/down Bps: 22/27 connections: 1\nconnection: [a specific placeholder literal] <interface_name>:443 => one.one.one.one:12345 (tcp) up/down Bps: 31/32 process: \"1\"\nconnection: [a specific placeholder literal] <interface_name>:4435 => three.three.three.three:1337 (tcp) up/down Bps: 22/27 process: \"5\"\nremote_address: [a specific placeholder literal] one.one.one.one up/down Bps: 31/32 connections: 1\nremote_address: [a specific placeholder literal] three.three.three.three up/down Bps: 22/27 connections: 1\n\n"
        },
        {
            "input": "action=raw_snapshot\nscenario=no_resolve\n",
            "expected_output": "Refreshing:\n[a specific sentinel string (consult spec doc)]\n\nRefreshing:\nprocess: [a specific placeholder literal] \"1\" up/down Bps: 28/30 connections: 1\nprocess: [a specific placeholder literal] \"5\" up/down Bps: 17/18 connections: 1\nconnection: [a specific placeholder literal] <interface_name>:443 => 1.1.1.1:12345 (tcp) up/down Bps: 28/30 process: \"1\"\nconnection: [a specific placeholder literal] <interface_name>:4435 => 3.3.3.3:1337 (tcp) up/down Bps: 17/18 process: \"5\"\nremote_address: [a specific placeholder literal] 1.1.1.1 up/down Bps: 28/30 connections: 1\nremote_address: [a specific placeholder literal] 3.3.3.3 up/down Bps: 17/18 connections: 1\n\nRefreshing:\nprocess: [a specific placeholder literal] \"1\" up/down Bps: 31/32 connections: 1\nprocess: [a specific placeholder literal] \"5\" up/down Bps: 22/27 connections: 1\nconnection: [a specific placeholder literal] <interface_name>:443 => 1.1.1.1:12345 (tcp) up/down Bps: 31/32 process: \"1\"\nconnection: [a specific placeholder literal] <interface_name>:4435 => 3.3.3.3:1337 (tcp) up/down Bps: 22/27 process: \"5\"\nremote_address: [a specific placeholder literal] 1.1.1.1 up/down Bps: 31/32 connections: 1\nremote_address: [a specific placeholder literal] 3.3.3.3 up/down Bps: 22/27 connections: 1\n\n"
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
- Adhere to the single-line output pattern used in the main formatting pipeline
- Follow the standard snapshot output structure with two header blocks
