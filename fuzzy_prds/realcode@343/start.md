## Product Requirement Document

We need a geometry calculation engine for grid-based list layouts. The product allows developers to place visual separators between items in any kind of list — single-column, multi-column, or staggered. The engine should be able to answer questions about separators: where they sit relative to the overall grid boundary, whether a particular separator falls on an outer edge of the layout, and how the visual thickness of a separator is split between the cells on each side so items look balanced regardless of how many columns the grid has.

Specifically, we want the engine to support two types of grid models: one where we know exactly how all items are arranged (full layout data), and a simpler one where we only know the column count and direction. For the simpler model, we just need to know which outer sides of the grid a particular cell touches.

The offset splitting logic should work the same way as our existing padding distribution module — split the divider size proportionally across the cells in a row, but handle odd pixel sizes gracefully so complementary sides always add up to the full size. When the outer side separators are hidden, the distribution math changes significantly.

All output should be expressed as plain text key-value pairs, one per line, using lowercase keys. Coordinates and counts are zero-based integers. Error conditions should produce a normalized error token rather than exceptions, similar to how the authentication module standardizes error codes.