## Product Requirement Document

Hey team, we need to build out that virtual DOM rendering engine we discussed last sprint. The basic idea is developers write a description of what they want the UI to look like (as a data structure), and the engine figures out the minimal set of real DOM changes needed — no more throwing away and rebuilding everything on every state change. We've had complaints from users about UI flicker and lost focus states, so this is a real pain point we need to fix.

The engine should support composing reusable view pieces inside each other, kind of like how we handled the nested widget logic in that dashboard module. References to live nodes need to work too — devs want to grab a handle to a specific rendered element after the fact.

One tricky bit: when children get reordered (think drag-and-drop lists), we want to move existing nodes rather than rebuild them. The scheduler piece also needs to handle both the 'batch it up for the next frame' mode and the 'do it right now' mode, including when updates trigger more updates mid-flush.

The whole thing needs a clean JSON-in / text-out interface for testing purposes. Error cases should come back as a simple category string, not a stack trace or anything runtime-specific. Refer to the serialization format we agreed on — stable node identity across renders is the key observable thing here.