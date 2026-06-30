## Product Requirement Document

Hey team, we need to build out the spreadsheet export engine for the next release. Basically we want something that can take a bunch of in-memory spreadsheet data and spit out the right XML chunks that get assembled into a real .xlsx file. There are a bunch of little conversion helpers we need too — like turning grid coordinates into the letter-number cell names people are used to seeing, figuring out what type a value is when nobody tells us explicitly, and converting calendar dates into the weird number format spreadsheets use internally.

We also need serialization for all the layout-y stuff — margins, print settings, column widths, row heights, merged cells, filters, that kind of thing. Oh and protection settings with the password thing — similar to how we handled it in the auth module a while back, just a short hash, not storing it in plain text obviously.

The whole thing should be broken up into sensible files, not just one giant blob. Each operation should get called via a JSON command on stdin and print the result to stdout with no extra junk. Errors should come back as a clean normalized token, not raw exceptions.

Range references need to handle both relative and absolute forms, and the absolute ones need the sheet name quoted properly with special characters escaped. Date handling needs to support two different epoch modes. Basically just make sure all the edge cases are solid — invalid inputs, out-of-range numbers, unrecognized enum values, etc.