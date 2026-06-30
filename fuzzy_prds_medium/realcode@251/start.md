## Product Requirement Document

Hey team, we need a URL cleaning utility — basically something that takes a blob of user-pasted text (could be a product link, a social share, a YouTube video, whatever) and spits back a cleaned version. The idea is we strip out all the junk tracking stuff that platforms tack on before we store or display the link. Think of it like what we did with the affiliate stripping logic in the referral module, but more general-purpose.

The tool needs to handle a bunch of different platforms — Amazon, eBay, YouTube, Facebook, Twitter, Wikipedia, Google redirects, etc. For some of these (like Google's /url wrapper or YouTube's redirect endpoint) we actually want to unwrap to the real destination, not just strip params. For others we just clean the params.

One tricky bit: there's a decode option the frontend team mentioned — when enabled, the final text output should be percent-decoded, but the individual URL entries in the output should still show the pre-decode cleaned URLs. The output format is very specific and the frontend is parsing it line by line, so it has to be exact.

We also need this to be testable — there are JSON test case files already sitting in the test folder that the CI pipeline will run against. The runner reads JSON from stdin and prints results to stdout. Please keep the core logic separate from the I/O plumbing.

One more pass on the output shape since the frontend is being pretty strict here: stdout needs to be line-oriented and exactly in this format. First line is `cleaned_text=<full cleaned text>`, second line is `url_count=<number>`, then one line per URL as `url[0]=<url>`, `url[1]=<url>`, etc., and every one of those lines ends with a newline. The whole thing should also end with a trailing newline after the last url line.

On the decode behavior, the split is intentional. When `decode_url` is true, the `cleaned_text` value in the output should be percent-decoded, so `%C3%A4` becomes `ä`. But the `url[i]=` lines should still show the cleaned URL before percent-decoding. So the URL list is the post-cleaning, pre-decode version, even if `cleaned_text` is decoded for display.

Also, if the input text has multiple URLs mixed into normal prose, clean each URL independently and replace it in place. Everything around the URLs stays exactly as-is. `url_count` is just the total number of URLs found, and the `url[i]` lines should be listed in encounter order from left to right.

For the runner side, the adapter reads one JSON object from stdin with a required `text` string field and an optional `decode_url` boolean field. It calls the core `clean_text` function and prints the formatted result to stdout. Please keep that adapter physically and logically separate from the core logic — no URL-cleaning rules should live in the adapter.

Small cleanup detail: if removing params leaves a URL with no query params at all, drop the trailing `?` too. So it should end up as `https://www.example.com`, not `https://www.example.com?`.

For Amazon, if it’s a product URL with the long title slug before `/dp/<ASIN>/`, the cleaned result should collapse to the short canonical form `https://<host>/dp/<ASIN>/`. Strip all query params there, including examples like `_encoding`, `pd_rd_w`, `pf_rd_p`, `ref_=`, etc. If it’s a non-product Amazon path like `/gp/css/...`, then just strip all query params and otherwise leave the path alone.

For redirect wrappers, there are a couple specific rules. For `google.com/url`, pull the destination from the `url` query parameter first, and if that’s missing, fall back to `q`. For `youtube.com/redirect`, pull from the `q` parameter and percent-decode it. In both of those redirect cases, that extracted destination becomes both the `cleaned_text` and `url[0]` output, and we do not do any further parameter stripping on the destination after that.

And just to make sure it’s carried through everywhere, the generic tracking param removal from feature6 applies globally across all URL cleaning, not only the social cases. That means the prefix-based stripping for `utm_`, `ga_`, `fb_`, `wt_`, plus exact-match removal for `gclid`, `fbclid`, `sfnsn`, `mibextid`.