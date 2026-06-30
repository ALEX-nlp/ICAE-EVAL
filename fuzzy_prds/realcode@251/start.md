## Product Requirement Document

Hey team, we need a URL cleaning utility — basically something that takes a blob of user-pasted text (could be a product link, a social share, a YouTube video, whatever) and spits back a cleaned version. The idea is we strip out all the junk tracking stuff that platforms tack on before we store or display the link. Think of it like what we did with the affiliate stripping logic in the referral module, but more general-purpose.

The tool needs to handle a bunch of different platforms — Amazon, eBay, YouTube, Facebook, Twitter, Wikipedia, Google redirects, etc. For some of these (like Google's /url wrapper or YouTube's redirect endpoint) we actually want to unwrap to the real destination, not just strip params. For others we just clean the params.

One tricky bit: there's a decode option the frontend team mentioned — when enabled, the final text output should be percent-decoded, but the individual URL entries in the output should still show the pre-decode cleaned URLs. The output format is very specific and the frontend is parsing it line by line, so it has to be exact.

We also need this to be testable — there are JSON test case files already sitting in the test folder that the CI pipeline will run against. The runner reads JSON from stdin and prints results to stdout. Please keep the core logic separate from the I/O plumbing.