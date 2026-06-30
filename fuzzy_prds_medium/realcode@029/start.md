## Product Requirement Document

hey team, we need a library that can read those bank export files (the ones banks give you when you download your statement) and turn them into something developers can actually work with programmatically. right now every dev on the team is writing their own string hacking to get account numbers and transaction lists out of these files and it keeps breaking whenever a new bank formats things slightly differently. we need one unified thing that handles all the weird formats banks use — some banks put everything on one line, some leave tags unclosed, etc.

the library should expose account info, transactions with proper types and amounts, and also the sign-on/institution block. amounts need to be normalized properly regardless of whether the bank uses commas or dots as separators. dates too — banks include varying levels of precision and sometimes timezone stuff that should NOT change the actual displayed time.

should be structured like we did with the payment processor adapter — separate concerns, not one giant file. the error handling should be clean categories, not raw exceptions bubbling up.

also need a test runner script that loops through case files and dumps outputs for comparison. fixture files will be in a known location. check how the login module handled the dialect normalization step for reference on how to structure that part.

one thing to clarify on amounts: for transaction amounts, purely integral values should lose the trailing decimal zeros, so 200.00 should come out as 200, -100.00 as -100, and 150.00 as 150. but that cleanup is only for transaction amounts. ledger balances should not get that treatment, so values like -500.00 and 5250.00 stay exactly as -500.00 and 5250.00.

also on amount coercion, we do need to treat both period and comma as possible decimal marks and also handle thousands separators. so 1000.00, 1000,00, 1,000.00, and 1.000,00 should all normalize to 1000. there’s also that documented quirk where a bare integer of three or more digits whose last two digits look like a fractional part is treated as having an implied two-decimal fraction, so bare '100' is interpreted as 1 because the trailing 00 gets consumed as cents. and again, purely integral results drop trailing zeros.

for timestamps, the bracketed timezone offset suffix like [-5:EST] and any fractional seconds are not supposed to shift the wall-clock time at all. we treat the timestamp as a wall-clock value and render it as-is in Y-m-d H:i:s format. so 20081005132200.124[-5:EST] should render as 2008-10-05 13:22:00, with no UTC adjustment.

on transaction typing, every transaction object should include both the raw type code and the derived human-readable description. the mappings we need are CREDIT → 'Generic credit', CHECK → 'Cheque', and POS → 'Point of sale debit or credit'.

one more edge case on dates: if the source leaves out DTUSER, then userInitiatedDate should be the literal string 'none'. not an empty string, not null, and not copied from the posting date. only if DTUSER actually exists in the source should userInitiatedDate render as a wall-clock datetime.

for errors, we only want two clean categories in output: 'parse_failed' when the content can’t be normalized into a valid document, and 'file_not_found' when the path doesn’t exist. those should render exactly as 'error=parse_failed' and 'error=file_not_found'. nothing else should leak through there — no raw exceptions, stack traces, or warning text.

and just to make the structure expectation explicit, the dialect normalization step from the PRD should be its own dedicated pre-processing unit that converts SGML unclosed-tag format, single-line format, and whitespace variants into well-formed markup before the structured-document reader runs. that should live as a separate module/file, not be inlined into the parser.