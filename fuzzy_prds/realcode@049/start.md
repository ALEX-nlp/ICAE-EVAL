## Product Requirement Document

Hey team, we need to build out that stylesheet module processing tool we've been talking about. The basic idea is that devs are constantly having to hand-maintain type declaration files and class name mappings whenever they touch a CSS module file — it's a huge pain and things go stale constantly. We need something that can take a stylesheet file and spit out the right class export map and declaration text automatically.

The tool needs to handle all the usual stylesheet flavors people use (you know, the ones we support in the main app build pipeline). It also needs to do the smart naming thing — like when someone has a dash-separated class name and they want to use it as a JS property, we should be able to expose both versions or just one depending on how they've configured things. Similar to how we handled identifiers in that config parser module a while back, but for class names specifically.

For path handling, it should recognize which imports are actually stylesheet modules vs regular stylesheets, and also tell us if they're local relative imports or coming from somewhere else. Custom pattern overrides should be supported too, with a graceful fallback if someone gives us a bad regex.

Declaration output needs to be flexible — support for custom templates, and also that line-aligned mode for source maps. The scoped class name generation should be deterministic and consistent. Please check what the existing test fixtures expect for the exact output formats before assuming anything.