## Product Requirement Document

# URL Cleaning Contract - Shareable Link Normalization

## Project Goal

Build a URL-cleaning library/tool that allows developers to normalize share links, remove tracking noise, and resolve supported redirect wrappers without manually maintaining one-off URL rewrite code.

---

## Background & Problem

Without this library/tool, developers are forced to inspect each incoming URL, recognize platform-specific query parameters or redirect formats, and hand-code fragile string manipulation for every site. This leads to repetitive code, privacy leaks through forgotten tracking fields, broken links from over-aggressive cleanup, and maintenance issues as URL formats vary across commerce, search, media, social, and reference sites.

With this library/tool, developers pass user-provided text containing URLs to a single cleaning workflow and receive deterministic stdout that includes the cleaned text plus the cleaned URLs discovered in order.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain. 
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository. 
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Plain Text URL Cleaning

**As a developer**, I want to clean one or more URLs embedded in user-provided text, so I can return the text with each URL cleaned and report the cleaned URLs found in order.

**Expected Behavior / Usage:**

The input is an object with a `text` string and an optional `decode_url` boolean. The output is line-oriented stdout: `cleaned_text=<full cleaned text>`, `url_count=<number of URLs found>`, then one `url[index]=<cleaned URL>` line for each URL in encounter order. Surrounding prose must remain unchanged. When URL decoding is explicitly enabled, the final `cleaned_text` is percent-decoded after URL cleaning, while the per-URL list continues to report the cleaned URL values detected before that final decode step.

**Test Cases:** `rcb_tests/public_test_cases/feature1_plain_text_url_cleaning.json`

```json
{
    "description": "Cleans one or more URLs found inside arbitrary text while preserving surrounding non-URL text.",
    "cases": [
        {
            "input": {
                "text": "https://www.some.site/?paramA=A&paramB=B"
            },
            "expected_output": "cleaned_text=https://www.some.site/?paramA=A&paramB=B\nurl_count=1\nurl[0]=https://www.some.site/?paramA=A&paramB=B\n"
        },
        {
            "input": {
                "text": "https://www.some.site/?paramA=A&paramB=B&page=1&q=query"
            },
            "expected_output": "cleaned_text=https://www.some.site/?paramA=A&paramB=B&page=1&q=query\nurl_count=1\nurl[0]=https://www.some.site/?paramA=A&paramB=B&page=1&q=query\n"
        },
        {
            "input": {
                "text": "[a specific tracking fragment pattern]?igsh=YmMyMTA2M2Y="
            },
            "expected_output": "cleaned_text=[a specific tracking fragment pattern]\nurl_count=1\nurl[0]=[a specific tracking fragment pattern]\n"
        }
    ]
}
```

---

### Feature 2: Commerce Product URL Normalization

**As a developer**, I want to share durable product links from commerce sites, so I can remove campaign and navigation noise while preserving the product identity.

**Expected Behavior / Usage:**

The input is an object with a `text` string containing a commerce product URL. The output must report the cleaned text and exactly one cleaned URL. For product pages, the stable product identifier path is retained; for tested site-specific navigation parameters, campaign/share/referral fields are removed. If the original product path has a canonical short form in the contract, stdout must use that canonical URL rather than the long marketing title path.

**Test Cases:** `rcb_tests/public_test_cases/feature2_commerce_product_urls.json`

```json
{
    "description": "Normalizes commerce product links by keeping the durable product path and removing campaign, navigation, and share parameters.",
    "cases": [
        {
            "input": {
                "text": "https://www.amazon.de/Xiaomi-Aktivit%C3%A4tstracker-Trainings-Puls%C3%BCberwachung-Akkulaufzeit/dp/B091G3FLL7/?_encoding=UTF8&pd_rd_w=xDcJP&pf_rd_p=bf172aca-3277-41f6-babb-6ce7fc34cf7f&pf_rd_r=ZC6FZ5G6W9K8DEZTPBYW&pd_rd_r=ee23359e-cb24-455b-a76a-5b80ea44704f&pd_rd_wg=q6rba&ref_=pd_gw_ci_mcx_mr_hp_atf_m"
            },
            "expected_output": "cleaned_text=https://www.amazon.de/dp/B091G3FLL7/\nurl_count=1\nurl[0]=https://www.amazon.de/dp/B091G3FLL7/\n"
        },
        {
            "input": {
                "text": "https://www.amazon.de/gp/css/homepage.html?ref_=nav_AccountFlyout_ya"
            },
            "expected_output": "cleaned_text=https://www.amazon.de/gp/css/homepage.html\nurl_count=1\nurl[0]=https://www.amazon.de/gp/css/homepage.html\n"
        },
        {
            "input": {
                "text": "https://www.ebay.de/itm/271784973135?mkcid=16&mkevt=1&mkrid=707-127654-2357-0&ssspo=rMbbkKXARCW&sssrc=2348624&ssuid=Bw-3_LUXSsm&widget_ver=artemis&media=MORE"
            },
            "expected_output": "cleaned_text=https://www.ebay.de/itm/271784973135\nurl_count=1\nurl[0]=https://www.ebay.de/itm/271784973135\n"
        }
    ]
}
```

---

### Feature 3: Search, Advertising, and Affiliate Redirect Resolution

**As a developer**, I want to open the real destination behind supported redirect links, so I can avoid sharing search-result, ad, or affiliate wrapper URLs.

**Expected Behavior / Usage:**

The input is an object with a `text` string containing a supported redirect URL. The output must report the destination URL as both `cleaned_text` and `url[0]`. Destination values may come from tested query fields or encoded redirect segments, and they must be decoded into their normal URL form. If a search query page is itself the resource, only the meaningful query field is retained.

**Test Cases:** `rcb_tests/public_test_cases/feature3_search_and_ad_redirects.json`

```json
{
    "description": "Extracts the destination URL from search, advertising, and affiliate redirect links when the original tests expose a destination field or encoded path.",
    "cases": [
        {
            "input": {
                "text": "https://www.google.com/url?sa=t&source=web&rct=j&url=https://www.regextester.com/&ved=2ahUKEwiTpvflqP34AhXOgv0HHSNQCOIQFnoECAcQAQ&usg=AOvVaw1wBmEA7TD90QkZPu7zcsOa"
            },
            "expected_output": "cleaned_text=https://www.regextester.com/\nurl_count=1\nurl[0]=https://www.regextester.com/\n"
        },
        {
            "input": {
                "text": "https://www.google.com/url?sa=t&source=web&rct=j&q=https://www.regextester.com/&ved=2ahUKEwiTpvflqP34AhXOgv0HHSNQCOIQFnoECAcQAQ&usg=AOvVaw1wBmEA7TD90QkZPu7zcsOa"
            },
            "expected_output": "cleaned_text=https://www.regextester.com/\nurl_count=1\nurl[0]=https://www.regextester.com/\n"
        },
        {
            "input": {
                "text": "https://www.youtube.com/redirect?event=channel_description&redir_token=QUFFLUhqa1JoZzZUczlhMWJCaTBoc1lqa3ZtX2Rpd0ZPUXxBQ3Jtc0tsYVhpenF1czV5VjlwZm5pemZGdm4zNHVXSldEUlR6dHNhZzI0UjRucGFpS3dNNktqU0lpczhybHdHX1JCUVdUOFVRRzVIbHRkdFJfeERrTjhRVDVsOUFuTHdyeS1yOA&q=http%3A%2F%2Fwww.google.com%2Fabout%2F"
            },
            "expected_output": "cleaned_text=http://www.google.com/about/\nurl_count=1\nurl[0]=http://www.google.com/about/\n"
        }
    ]
}
```

---

### Feature 4: Video and Music URL Cleanup

**As a developer**, I want to share media links without transient recommendation or share metadata, so I can preserve the video, playlist, timestamp, album, or title identity.

**Expected Behavior / Usage:**

The input is an object with a `text` string containing a media URL. The output reports one cleaned URL. Video watch URLs keep the video identifier and, when present in the tested contract, the timestamp. Playlist URLs keep the playlist identifier. Short video URLs are expanded to the tested full watch URL form. Music and streaming title links keep the stable album, track, playlist, or title path and drop transient share parameters.

**Test Cases:** `rcb_tests/public_test_cases/feature4_video_and_music_urls.json`

```json
{
    "description": "Keeps the essential media identifier parameters for video, playlist, music, and short links while removing share metadata.",
    "cases": [
        {
            "input": {
                "text": "https://m.youtube.com/watch?v=CvFH_6DNRCY&pp=ygUHZGVidXNzeQ%3D%3D"
            },
            "expected_output": "cleaned_text=https://m.youtube.com/watch?v=CvFH_6DNRCY\nurl_count=1\nurl[0]=https://m.youtube.com/watch?v=CvFH_6DNRCY\n"
        },
        {
            "input": {
                "text": "https://m.youtube.com/watch?v=CvFH_6DNRCY&t=125"
            },
            "expected_output": "cleaned_text=https://m.youtube.com/watch?v=CvFH_6DNRCY&t=125\nurl_count=1\nurl[0]=https://m.youtube.com/watch?v=CvFH_6DNRCY&t=125\n"
        },
        {
            "input": {
                "text": "https://youtube.com/playlist?list=PLkqz3S84Tw-QYEdfTLBzxJ1FAprtqeEpJ&si=2tDDmSKejG2GTtj5"
            },
            "expected_output": "cleaned_text=https://youtube.com/playlist?list=PLkqz3S84Tw-QYEdfTLBzxJ1FAprtqeEpJ\nurl_count=1\nurl[0]=https://youtube.com/playlist?list=PLkqz3S84Tw-QYEdfTLBzxJ1FAprtqeEpJ\n"
        }
    ]
}
```

---

### Feature 5: Social Content URL Cleanup

**As a developer**, I want to share social posts and short-form content links, so I can remove share tracking while preserving the addressed post or profile content.

**Expected Behavior / Usage:**

The input is an object with a `text` string containing a supported social-content URL. The output reports one cleaned URL. Reels, posts, threads, short videos, and status URLs drop share metadata. Story URLs preserve the tested content identifier fields while removing social sharing fields. URLs on domains represented by the contract keep their original host form unless the expected stdout specifies a canonicalized host.

**Test Cases:** `rcb_tests/public_test_cases/feature5_social_content_urls.json`

```json
{
    "description": "Removes social-network share metadata while preserving the stable content identifier or allowed story fields.",
    "cases": [
        {
            "input": {
                "text": "https://www.facebook.com/reel/1242384407160280?sfnsn=scwspmo"
            },
            "expected_output": "cleaned_text=https://www.facebook.com/reel/1242384407160280\nurl_count=1\nurl[0]=https://www.facebook.com/reel/1242384407160280\n"
        },
        {
            "input": {
                "text": "https://m.facebook.com/story.php?story_fbid=pfbid0HqS6zLZvNrQt6ACvjv3hKq6khpVse437nWSq2jBifKRD5sVH2XRLC3zz8aA7TKkWl&id=4&sfnsn=wiwspmo&mibextid=XzsMCV"
            },
            "expected_output": "cleaned_text=https://m.facebook.com/story.php?story_fbid=pfbid0HqS6zLZvNrQt6ACvjv3hKq6khpVse437nWSq2jBifKRD5sVH2XRLC3zz8aA7TKkWl&id=4\nurl_count=1\nurl[0]=https://m.facebook.com/story.php?story_fbid=pfbid0HqS6zLZvNrQt6ACvjv3hKq6khpVse437nWSq2jBifKRD5sVH2XRLC3zz8aA7TKkWl&id=4\n"
        },
        {
            "input": {
                "text": "https://twitter.com/AndroidDev/status/1453763770334027781?t=QEv2BUR2LOumjgK18S72bA&s=09"
            },
            "expected_output": "cleaned_text=https://twitter.com/AndroidDev/status/1453763770334027781\nurl_count=1\nurl[0]=https://twitter.com/AndroidDev/status/1453763770334027781\n"
        }
    ]
}
```

---

### Feature 6: Generic Tracking Parameter Removal

**As a developer**, I want to strip common tracking and empty parameters from otherwise ordinary URLs, so I can share cleaner URLs without losing unrelated business parameters.

**Expected Behavior / Usage:**

The input is an object with a `text` string containing a URL with generic tracking, session, or empty-value query parameters. The output reports the cleaned URL. Analytics prefixes, campaign identifiers, tested social click identifiers, empty query fields, and tested session identifiers are removed. Query fields not identified by the contract as removable must remain, and the output must keep a valid query separator before the first remaining field.

**Test Cases:** `rcb_tests/public_test_cases/feature6_generic_tracking_parameters.json`

```json
{
    "description": "Removes cross-site analytics, campaign, empty-value, and session identifier parameters from URLs while leaving unrelated fields intact.",
    "cases": [
        {
            "input": {
                "text": "https://www.example.com?ga_abc=123&utm_def=456&gclid=789"
            },
            "expected_output": "cleaned_text=https://www.example.com\nurl_count=1\nurl[0]=https://www.example.com\n"
        },
        {
            "input": {
                "text": "https://www.example.com?fb_abc=123&fbclid=12345&sfnsn=scwspmo"
            },
            "expected_output": "cleaned_text=https://www.example.com\nurl_count=1\nurl[0]=https://www.example.com\n"
        },
        {
            "input": {
                "text": "https://www.example.com?wt_abc=123&wt_efg=456"
            },
            "expected_output": "cleaned_text=https://www.example.com\nurl_count=1\nurl[0]=https://www.example.com\n"
        }
    ]
}
```

---

### Feature 7: Reference and Knowledge URL Cleanup

**As a developer**, I want to share reference, search, and help URLs in their stable form, so I can remove app-source and navigation metadata from informational resources.

**Expected Behavior / Usage:**

The input is an object with a `text` string containing a reference, search, or help URL. The output reports the stable informational URL. Tested encyclopedia share parameters are removed. Tested regional search URLs keep the search text parameter and remove navigation/source fields. Tested help-center URLs remove application source parameters and keep the article request path.

**Test Cases:** `rcb_tests/public_test_cases/feature7_reference_and_knowledge_urls.json`

```json
{
    "description": "Cleans reference, knowledge-base, and regional site URLs by removing tested share or navigation parameters while preserving the article path or query that identifies content.",
    "cases": [
        {
            "input": {
                "text": "https://en.wikipedia.org/wiki/Kerosene?wprov=sfla1"
            },
            "expected_output": "cleaned_text=https://en.wikipedia.org/wiki/Kerosene\nurl_count=1\nurl[0]=https://en.wikipedia.org/wiki/Kerosene\n"
        },
        {
            "input": {
                "text": "https://yandex.com/search/?text=test&lr=213&clid=123"
            },
            "expected_output": "cleaned_text=https://yandex.com/search/?text=test\nurl_count=1\nurl[0]=https://yandex.com/search/?text=test\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- quote format: 'https://www.google.com/about/' instead of 'https://www.google.comABOUT/'
