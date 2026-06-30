## Product Requirement Document

We need a small, self-contained library of text-parsing utilities for our virtual machine management platform. The platform inspects the internal state of guest operating systems and their tooling without reaching out to any network or running processes — every parser is a pure function taking raw text and returning clean structured data.

Six capabilities are needed:

1. Decode the kernel's open-socket table into readable records showing address family, IP, port, and whether the socket is listening or actively connected. Addresses are stored in a quirky little-endian-per-group byte order — handle it the same way as the network parsing module already does for address byte-order.

2. Scan the firewall's NAT rule dump and extract only rules that actually forward host ports into containers. When no specific host IP is pinned in the rule, report an unspecified binding address.

3. Look up a flag's value inside an already-split command-line token list. Report presence and value; a standalone flag with no following value token should still be reported as present.

4. Normalize the SSH client's self-reported version banner, stripping vendor noise and producing a clean three-component version number; use zero for any missing component.

5. Validate SSH public-key lines by checking the key type is recognized and the key body length is within expected bounds. Use the same approach as the SSH utility module for reading the embedded signature identifier.

6. Extract the platform's unique hardware identifier from the device registry's property-list XML format, navigating its nested dictionary-and-array structure.