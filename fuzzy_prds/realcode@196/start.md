## Product Requirement Document

Hey team, we need to build that CLI adapter library we've been talking about. The idea is devs should be able to take a regular Python function and expose it as a command-line command without writing all the argparse boilerplate themselves. Think of it like the decorator pattern we used in that routing module a while back — similar philosophy here.

The library needs to handle the usual stuff: positional args, optional args with defaults, variadic inputs, subcommands, namespacing, aliases, boolean toggles, counting flags, and so on. There's also some output rendering logic we need — by default results print line by line, but there should be a way to get raw output too. Errors need to come out in a normalized neutral format, not as Python tracebacks — users keep complaining about seeing raw exception dumps in the terminal and it looks terrible.

Also important: when parameter names have underscores, the CLI-facing name should use dashes instead (again, refer to how we handled that naming convention last time). We also want help text to surface default values automatically.

There's a confirmation prompt feature that needs to handle three states based on the default — when no default is set, when it's yes by default, and when it's no by default — and the prompt formatting and result mapping should reflect which state we're in.

Please check the existing test scenarios folder to understand the full scope, some edge cases aren't obvious from this description alone.