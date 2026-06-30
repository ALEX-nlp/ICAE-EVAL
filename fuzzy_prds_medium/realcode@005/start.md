## Product Requirement Document

Hey team, we need a shopping cart feature for the storefront project. Basically customers keep losing their cart contents between page loads which is super frustrating and we're getting complaints. The cart needs to stick around for the whole browsing session — similar to how we handled persistence in that user login flow we did before.

Each item in the cart should track how many the customer wants and what price they're paying, and we need the math to be solid — accounting had some issues last quarter with totals being slightly off on invoices so that's a hard requirement this time. Products should be identifiable and if someone picks the same product twice it shouldn't create a duplicate entry, just update it.

We also want a nice readable description for each cart line so customer service can read it out without looking at raw IDs.

On the technical side, keep the cart logic separate from whatever reads/writes to the outside world — we've had issues before where business logic got tangled up with I/O stuff and it made testing a nightmare. We need a test runner script too that can just be pointed at a folder of test cases and runs everything automatically, writing outputs somewhere we can diff them.

Basically model it after the architecture approach we used in the inventory module — small, clean, no over-engineering. Let me know if anything is unclear.

One small follow-up from the questions that came in: when a cart gets re-established against the same session through the 'reopen' operation, that should resolve to the same existing cart, not make a fresh one. In that case the output needs to start with the line 'same_cart=yes' before the cart state dump so it’s obvious we found the existing cart. This is the same session-scoped binding idea from before: the cart attaches to the caller-supplied session object on first use, and coming back with that same session should give you that same cart again.

Also, for the cart state dump, please make it deterministic and easy to diff. Each line item should be printed on its own line as 'item product=<product-id> quantity=<n> unit_price=<price> subtotal=<price>', and those item lines should be ordered by ascending product id. After the items, print 'total=<price>' and then 'count=<n>'. Money formatting needs to be exactly two decimal places every time, so things like 100.00, 3.20, 12.80. And for the math itself, this needs to use exact fixed-point decimal arithmetic, not binary floating-point (float/double). So if it’s 4 units at 3.20, the subtotal must be exactly 12.80. Please use a Decimal or equivalent exact-arithmetic type in the implementation.

One other behavior point: updating a line item replaces its quantity and unit price completely, it does not stack onto what was already there. So if something was quantity-3 and then gets updated to quantity-2 at a new price, the cart should now show exactly 2 units at the new price, count=2.

For the readable description piece, the label operation should output a single line formatted as 'label=<quantity> units of <product-type-name>', where the product-type-name is the class/type name of the product object. Example: 'label=3 units of User', and for a Django User product fixture with id=1 the type name there is 'User'.