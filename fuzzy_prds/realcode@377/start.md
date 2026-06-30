## Product Requirement Document

Hey team, we need to wrap up the scaffolding tool we've been building. The core idea is pretty straightforward — devs give it a template folder and some answers, and it spits out a fully populated project. But there are a bunch of edge cases we keep running into that need to be nailed down before we ship.

First, the file-naming thing — some files should get their contents filled in, others should just be copied as-is, and the folder/file names themselves can also have placeholders. We also need that 'safety valve' mode where you can preview what would happen without actually writing anything to disk.

There's also the question of what happens when you run it again over an existing project — we don't want people losing hand-edited files. The 'protect certain files' logic should work like we did with the login module's compatibility handling, but applied to file paths.

We need config file support too — the template should be able to ship its own defaults, and those settings need to feed into the engine options correctly. The validation layer for flags and template engine settings also needs to be tight — wrong types or conflicting options should surface clean errors, not stack traces.

Finally, there's the external template thing where a child template references a parent that lives somewhere else. If that parent can't be found, or the path doesn't exist at all, we need distinct, clear error messages. Can someone make sure all these pieces are wired up properly?