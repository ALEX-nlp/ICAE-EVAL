## Product Requirement Document

We need a small, self-contained library of text-parsing utilities for our virtual machine management platform. The platform inspects the internal state of guest operating systems and their tooling without reaching out to any network or running processes — every parser is a pure function taking raw text and returning clean structured data.

Six capabilities are needed:

1. Decode the kernel's open-socket table into readable records showing address family, IP, port, and whether the socket is listening or actively connected. Addresses are stored in a quirky little-endian-per-group byte order — handle it the same way as the network parsing module already does for address byte-order.

2. Scan the firewall's NAT rule dump and extract only rules that actually forward host ports into containers. When no specific host IP is pinned in the rule, report an unspecified binding address.

3. Look up a flag's value inside an already-split command-line token list. Report presence and value; a standalone flag with no following value token should still be reported as present.

4. Normalize the SSH client's self-reported version banner, stripping vendor noise and producing a clean three-component version number; use zero for any missing component.

5. Validate SSH public-key lines by checking the key type is recognized and the key body length is within expected bounds. Use the same approach as the SSH utility module for reading the embedded signature identifier.

6. Extract the platform's unique hardware identifier from the device registry's property-list XML format, navigating its nested dictionary-and-array structure.

A couple extra specifics from the questions that came back: for the socket parser, the TCP LISTEN state is 0x0A (decimal 10) and that should come out as 'listen', and the established state is 0x01 (decimal 1) and that should come out as 'established'. Anything else should just be rendered as '0x<hex>' literally. The output format for each parsed socket should be exactly 'kind=<tcp|tcp6> ip=<dotted-decimal or IPv6> port=<decimal> state=<listen|established|0x<hex>>\n', with space-separated fields, no trailing spaces, and one socket per line.

On the address decoding piece, this follows the same behavior as the existing ParseAddress function in pkg/guestagent/procnettcp/procnettcp.go: each 8-character (4-byte) hex group is decoded little-endian independently for both IPv4 (one group) and IPv6 (four groups). So for IPv4, the full 8-char token gets reversed byte-by-byte to make the IP. For IPv6, the 32-char token is split into four 8-char groups and each group is reversed independently. The port after the colon is big-endian hex. Example: '0100007F:0050' decodes to ip=127.0.0.1 port=80.

For the NAT rules, only rules matching '-A CNI-DN-<alphanum>*' chains that contain '--dport <port> -j DNAT' should be treated as forwarding entries. Rules in PREROUTING, OUTPUT, POSTROUTING, CNI-HOSTPORT-*, CNI-<hex>* (non-DN) chains, and any chain not matching the CNI-DN- prefix are ignored. Also, if a DNAT forwarding rule in a CNI-DN-* chain does not include a '-d <ip>/32' clause, the bound IP should be reported as '0.0.0.0'. The rule still needs both '--dport <port>' and '-j DNAT' to count.