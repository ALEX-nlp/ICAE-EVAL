## Product Requirement Document

Hey team, we need a shopping cart feature for the storefront project. Basically customers keep losing their cart contents between page loads which is super frustrating and we're getting complaints. The cart needs to stick around for the whole browsing session — similar to how we handled persistence in that user login flow we did before.

Each item in the cart should track how many the customer wants and what price they're paying, and we need the math to be solid — accounting had some issues last quarter with totals being slightly off on invoices so that's a hard requirement this time. Products should be identifiable and if someone picks the same product twice it shouldn't create a duplicate entry, just update it.

We also want a nice readable description for each cart line so customer service can read it out without looking at raw IDs.

On the technical side, keep the cart logic separate from whatever reads/writes to the outside world — we've had issues before where business logic got tangled up with I/O stuff and it made testing a nightmare. We need a test runner script too that can just be pointed at a folder of test cases and runs everything automatically, writing outputs somewhere we can diff them.

Basically model it after the architecture approach we used in the inventory module — small, clean, no over-engineering. Let me know if anything is unclear.