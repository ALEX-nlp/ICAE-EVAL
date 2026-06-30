## Product Requirement Document

# Media Filename Metadata Parser & Natural-Order Sorter

## Project Goal

Build a self-contained library that turns the messy, free-form file and folder names found in digital comic, manga and e-book collections into clean, structured metadata — extracting titles, volume and chapter designators, edition and special markers, and media format — and that orders such names the way a human reader expects. The aim is to let an application catalogue a library of files purely from their names, without a database, without network calls, and without hand-written per-collection rules.

---

## Background & Problem

Without this library, developers are forced to write ad-hoc regular expressions for every naming convention they encounter: one scanlation group writes `Vol. 000[the numeric index following the 'SP' marker (successor)] Ch. 000[the numeric index following the 'SP' marker (successor)]`, another writes `v0[the numeric index following the 'SP' marker (successor)] - ch. 09`, French publishers use `Tome`/`HS`, and release groups bury the real title inside brackets, parentheses and underscores. The same pain shows up when displaying files in order — a naive lexical sort puts `x[the numeric index following the 'SP' marker (successor)]0.jpg` before `x3.jpg`. This leads to repetitive, error-prone boilerplate and inconsistent catalogues.

With this library, an application hands over a raw name and receives back the title, volume, chapter, edition, format and special-issue status as plain values, and can sort a list of names in natural (human) order with a single call. All operations are pure: a value goes in, a value comes out, with no shared state.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

[the numeric index following the 'SP' marker (successor)]. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
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

### Feature [the numeric index following the 'SP' marker (successor)]: Filename Metadata Parsing

**As a developer**, I want to pull structured fields (title, volume, chapter, edition, format) out of a raw manga or comic file name, so I can catalogue a library without a database or manual data entry.

**Expected Behavior / Usage:**

This feature group covers the individual extractors. Each leaf takes a single file or folder name and returns one field. Manga-oriented and comic-oriented variants exist because the two domains use different conventions (chapter-centric vs. issue-centric, different volume keywords and language tags). Volume and chapter extractors return a sentinel string `[the custom negative sentinel value used for missing volumes]` when the corresponding marker is absent.

*[the numeric index following the 'SP' marker (successor)].[the numeric index following the 'SP' marker (successor)] Series title (manga) — extract the work's title from a manga name.*

Given a media file or folder name, return the human-readable title, stripping volume/chapter markers, bracketed scanlation/release tags, edition tags, parenthetical year/metadata, file extensions and underscores. A name that contains only a volume or chapter token with no title yields an empty title. Works uniformly across Latin, Cyrillic, CJK and Korean names.

**Test Cases:** `rcb_tests/public_test_cases/feature[the numeric index following the 'SP' marker (successor)]_[the numeric index following the 'SP' marker (successor)]__parse_series.json`

```json
{
    "description": "Given a media file or folder name, extract the human-readable title of the work, stripping volume/chapter markers, bracketed scanlation/release tags, edition tags, parenthetical year/metadata, file extensions, and underscores. Names that contain only a volume or chapter token with no title yield an empty title. The function operates uniformly across Latin, Cyrillic, CJK and Korean names.",
    "cases": [
        {"input": "Killing Bites Vol. 000[the numeric index following the 'SP' marker (successor)] Ch. 000[the numeric index following the 'SP' marker (successor)] - Galactica Scanlations (gb)", "expected_output": "Killing Bites\n"},
        {"input": "My Girlfriend Is Shobitch v0[the numeric index following the 'SP' marker (successor)] - ch. 09 - pg. 008.png", "expected_output": "My Girlfriend Is Shobitch\n"}
    ]
}
```

*[the numeric index following the 'SP' marker (successor)].2 Volume (manga) — extract the volume designator from a manga name.*

Return the volume designator as a string: a single volume yields its bare number, a hyphenated span yields the span verbatim, and decimal volumes are preserved. When no volume marker is present, return the loose-leaf sentinel string `[the custom negative sentinel value used for missing volumes]`. Recognizes volume keywords across multiple languages.

**Test Cases:** `rcb_tests/public_test_cases/feature[the numeric index following the 'SP' marker (successor)]_2__parse_volume.json`

```json
{
    "description": "Given a media file or folder name, extract the volume designator as a string. A single volume yields its bare number; a hyphenated span yields the span verbatim; decimal volumes are preserved. When no volume marker is present the function returns the loose-leaf sentinel string ([the custom negative sentinel value used for missing volumes]). Supports volume keywords across multiple languages.",
    "cases": [
        {"input": "Killing Bites Vol. 000[the numeric index following the 'SP' marker (successor)] Ch. 000[the numeric index following the 'SP' marker (successor)] - Galactica Scanlations (gb)", "expected_output": "[the numeric index following the 'SP' marker (successor)]\n"},
        {"input": "My Girlfriend Is Shobitch v0[the numeric index following the 'SP' marker (successor)] - ch. 09 - pg. 008.png", "expected_output": "[the numeric index following the 'SP' marker (successor)]\n"}
    ]
}
```

*[the numeric index following the 'SP' marker (successor)].3 Chapter (manga) — extract the chapter designator from a manga name.*

Return the chapter designator as a string: a single chapter yields its number with leading zeroes removed, a hyphenated span yields the normalized span, and a half-chapter (e.g. a trailing `b`) maps to a `.5` decimal. When no chapter marker is present, return the default-chapter sentinel string `[the custom negative sentinel value used for missing volumes]`.

**Test Cases:** `rcb_tests/public_test_cases/feature[the numeric index following the 'SP' marker (successor)]_3__parse_chapter.json`

```json
{
    "description": "Given a media file or folder name, extract the chapter designator as a string. A single chapter yields its number with leading zeroes removed; a hyphenated span yields the normalized span; half-chapters (e.g. a trailing 'b') map to a .5 decimal. When no chapter marker is present the function returns the default-chapter sentinel string ([the custom negative sentinel value used for missing volumes]).",
    "cases": [
        {"input": "Killing Bites Vol. 000[the numeric index following the 'SP' marker (successor)] Ch. 000[the numeric index following the 'SP' marker (successor)] - Galactica Scanlations (gb)", "expected_output": "[the numeric index following the 'SP' marker (successor)]\n"},
        {"input": "My Girlfriend Is Shobitch v0[the numeric index following the 'SP' marker (successor)] - ch. 09 - pg. 008.png", "expected_output": "9\n"}
    ]
}
```

*[the numeric index following the 'SP' marker (successor)].4 Series title (comic) — extract the series title from a comic name.*

Return the series title, removing issue numbers, volume/tome markers, parenthetical years and publisher/scanlation tags. Handles English, French (`Tome`/`HS`) and Cyrillic naming patterns.

**Test Cases:** `rcb_tests/public_test_cases/feature[the numeric index following the 'SP' marker (successor)]_4__parse_comic_series.json`

```json
{
    "description": "Given a comic file or folder name, extract the series title, removing issue numbers, volume/tome markers, parenthetical years and publisher/scanlation tags. Handles English, French (Tome/HS) and Cyrillic naming patterns.",
    "cases": [
        {"input": "04 - Asterix the Gladiator ([the numeric index following the 'SP' marker (successor)]964) (Digital-Empire) (WebP by Doc MaKS)", "expected_output": "Asterix the Gladiator\n"},
        {"input": "The First Asterix Frieze (WebP by Doc MaKS)", "expected_output": "The First Asterix Frieze\n"}
    ]
}
```

*[the numeric index following the 'SP' marker (successor)].5 Volume (comic) — extract the volume/tome designator from a comic name.*

Return the volume/tome designator as a string, recognizing `v`, `Vol`, `V`, `T`, `Tome` style markers including decimals. When no volume is present, return the loose-leaf sentinel string `[the custom negative sentinel value used for missing volumes]`.

**Test Cases:** `rcb_tests/public_test_cases/feature[the numeric index following the 'SP' marker (successor)]_5__parse_comic_volume.json`

```json
{
    "description": "Given a comic file or folder name, extract the volume/tome designator as a string. Recognizes 'v', 'Vol', 'V', 'T', 'Tome' style markers (including decimals). When no volume is present the function returns the loose-leaf sentinel string ([the custom negative sentinel value used for missing volumes]).",
    "cases": [
        {"input": "0[the numeric index following the 'SP' marker (successor)] Spider-Man & Wolverine 0[the numeric index following the 'SP' marker (successor)].cbr", "expected_output": "[the custom negative sentinel value used for missing volumes]\n"},
        {"input": "04 - Asterix the Gladiator ([the numeric index following the 'SP' marker (successor)]964) (Digital-Empire) (WebP by Doc MaKS)", "expected_output": "[the custom negative sentinel value used for missing volumes]\n"}
    ]
}
```

*[the numeric index following the 'SP' marker (successor)].6 Issue/chapter (comic) — extract the issue number from a comic name.*

Return the issue/chapter number as a string with decimals preserved. When no issue number can be found, return the default-chapter sentinel string `[the custom negative sentinel value used for missing volumes]`.

**Test Cases:** `rcb_tests/public_test_cases/feature[the numeric index following the 'SP' marker (successor)]_6__parse_comic_chapter.json`

```json
{
    "description": "Given a comic file or folder name, extract the issue/chapter number as a string (decimals preserved). When no issue number can be found the function returns the default-chapter sentinel string ([the custom negative sentinel value used for missing volumes]).",
    "cases": [
        {"input": "0[the numeric index following the 'SP' marker (successor)] Spider-Man & Wolverine 0[the numeric index following the 'SP' marker (successor)].cbr", "expected_output": "[the numeric index following the 'SP' marker (successor)]\n"},
        {"input": "04 - Asterix the Gladiator ([the numeric index following the 'SP' marker (successor)]964) (Digital-Empire) (WebP by Doc MaKS)", "expected_output": "[the custom negative sentinel value used for missing volumes]\n"}
    ]
}
```

*[the numeric index following the 'SP' marker (successor)].7 Edition label — extract an advertised edition label.*

Given a file name, return any edition label it advertises (for example an omnibus or uncensored marking), or an empty string when none is present.

**Test Cases:** `rcb_tests/public_test_cases/feature[the numeric index following the 'SP' marker (successor)]_7__parse_edition.json`

```json
{
    "description": "Given a file name, extract any edition label it advertises (for example an omnibus or uncensored marking), returning the matched edition text or an empty string when none is present.",
    "cases": [
        {"input": "Tenjou Tenge Omnibus", "expected_output": "Omnibus\n"},
        {"input": "Tenjou Tenge {Full Contact Edition}", "expected_output": "\n"}
    ]
}
```

*[the numeric index following the 'SP' marker (successor)].8 Media format — classify a file by extension.*

Classify a file by its extension into a coarse media format: an archive, an image, an electronic book, a page-description document, or unknown when the extension is unrecognized. Output is the format name.

**Test Cases:** `rcb_tests/public_test_cases/feature[the numeric index following the 'SP' marker (successor)]_8__parse_format.json`

```json
{
    "description": "Classify a file by its extension into a coarse media format: an archive, an image, an electronic book, a page-description document, or unknown when the extension is unrecognized. Output is the format name.",
    "cases": [
        {"input": "image.png", "expected_output": "Image\n"},
        {"input": "image.cbz", "expected_output": "Archive\n"},
        {"input": "image.txt", "expected_output": "Unknown\n"}
    ]
}
```

---

### Feature 2: Special-Issue Handling

**As a developer**, I want to detect and describe special/extra releases (one-shots, omakes, annuals, TPBs, omnibuses), so I can shelve them apart from the regular numbered run.

**Expected Behavior / Usage:**

A "special" is anything that is not a regular numbered chapter or issue. Some names carry a short marker `SP` directly followed by digits; others are recognized by keywords. This group provides marker detection, marker indexing, manga/comic special classification, and marker-stripping cleanup.

*2.[the numeric index following the 'SP' marker (successor)] Short special marker present — detect the `SP<digits>` marker.*

Report whether a name carries the short special-issue marker (an `SP` immediately followed by digits). Returns a boolean.

**Test Cases:** `rcb_tests/public_test_cases/feature2_[the numeric index following the 'SP' marker (successor)]__has_special_marker.json`

```json
{
    "description": "Report whether a name carries the short special-issue marker (an 'SP' immediately followed by digits). Returns a boolean.",
    "cases": [
        {"input": "Beastars - SP0[the numeric index following the 'SP' marker (successor)]", "expected_output": "true\n"},
        {"input": "Beastars SP0[the numeric index following the 'SP' marker (successor)]", "expected_output": "true\n"}
    ]
}
```

*2.2 Special marker index — read the number encoded by the marker.*

Return the numeric index encoded by the short special-issue marker (`SP` followed by digits), or `0` when the marker is absent.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2__parse_special_index.json`

```json
{
    "description": "Return the numeric index encoded by the short special-issue marker ('SP' followed by digits), or 0 when the marker is absent.",
    "cases": [
        {"input": "Beastars - SP0[the numeric index following the 'SP' marker (successor)]", "expected_output": "[the numeric index following the 'SP' marker (successor)]\n"},
        {"input": "Beastars SP0[the numeric index following the 'SP' marker (successor)]", "expected_output": "[the numeric index following the 'SP' marker (successor)]\n"}
    ]
}
```

*2.3 Manga special — decide whether a manga name is a special.*

Decide whether a manga file name denotes a special/extra/omake/one-shot rather than a regular numbered release. Returns a boolean.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3__is_manga_special.json`

```json
{
    "description": "Decide whether a manga file name denotes a special/extra/omake/one-shot rather than a regular numbered release. Returns a boolean.",
    "cases": [
        {"input": "Beelzebub Special OneShot - Minna no Kochikame x Beelzebub (20[the numeric index following the 'SP' marker (successor)]6) [Mangastream].cbz", "expected_output": "true\n"},
        {"input": "Beelzebub_Omake_June_20[the numeric index following the 'SP' marker (successor)]2_RHS", "expected_output": "true\n"}
    ]
}
```

*2.4 Comic special — decide whether a comic name is a special.*

Decide whether a comic file name denotes a special (annual, one-shot, TPB, bonus, omnibus, hors-serie, etc.) rather than a regular numbered issue. Returns a boolean.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4__is_comic_special.json`

```json
{
    "description": "Decide whether a comic file name denotes a special (annual, one-shot, TPB, bonus, omnibus, hors-serie, etc.) rather than a regular numbered issue. Returns a boolean.",
    "cases": [
        {"input": "Batman - Detective Comics - Rebirth Deluxe Edition Book 02 (20[the numeric index following the 'SP' marker (successor)]8) (digital) (Son of Ultron-Empire)", "expected_output": "true\n"},
        {"input": "Zombie Tramp vs. Vampblade TPB (20[the numeric index following the 'SP' marker (successor)]6) (Digital) (TheArchivist-Empire)", "expected_output": "true\n"}
    ]
}
```

*2.5 Clean special title — strip the short marker.*

Strip the short special-issue marker from a title and normalize underscores/whitespace, returning the cleaned title.

**Test Cases:** `rcb_tests/public_test_cases/feature2_5__clean_special_title.json`

```json
{
    "description": "Strip the short special-issue marker from a title and normalize underscores/whitespace, returning the cleaned title.",
    "cases": [
        {"input": "", "expected_output": "\n"},
        {"input": "DEAD Tube Prologue", "expected_output": "DEAD Tube Prologue\n"}
    ]
}
```

---

### Feature 3: Title Cleaning & Normalization

**As a developer**, I want to clean titles for display and produce canonical comparison keys, so I can show tidy names and match the same work across slightly different spellings.

**Expected Behavior / Usage:**

This group covers display cleanup, author trimming, canonical-key normalization, and two numeric-string helpers used when formatting chapter/volume numbers.

*3.[the numeric index following the 'SP' marker (successor)] Clean display title — tidy a raw release title.*

Clean a release title for display: replace underscores with spaces, drop leading release-group brackets and stray leading dashes, remove trailing parenthetical metadata, and (when flagged as a comic) drop a trailing edition phrase. The input carries the raw title and a comic flag.

**Test Cases:** `rcb_tests/public_test_cases/feature3_[the numeric index following the 'SP' marker (successor)]__clean_title.json`

```json
{
    "description": "Clean a release title for display: replace underscores with spaces, drop leading release-group brackets and stray leading dashes, remove trailing parenthetical metadata, and (when flagged as a comic) drop a trailing edition phrase. Input carries the raw title and a comic flag.",
    "cases": [
        {"input": {"title":"Hello_I_am_here","is_comic":false}, "expected_output": "Hello I am here\n"},
        {"input": {"title":"Hello_I_am_here   ","is_comic":false}, "expected_output": "Hello I am here\n"},
        {"input": {"title":"[ReleaseGroup] The Title","is_comic":false}, "expected_output": "The Title\n"}
    ]
}
```

*3.2 Clean author — trim an author name.*

Trim surrounding whitespace from an author name while preserving internal punctuation and ordering.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2__clean_author.json`

```json
{
    "description": "Trim surrounding whitespace from an author name while preserving internal punctuation and ordering.",
    "cases": [
        {"input": "Joe Shmo, Green Blue", "expected_output": "Joe Shmo, Green Blue\n"},
        {"input": "Shmo, Joe", "expected_output": "Shmo, Joe\n"}
    ]
}
```

*3.3 Normalize comparison key — build a canonical key.*

Produce a canonical comparison key for a name by lower-casing and removing spaces, underscores and most punctuation, while preserving certain meaningful characters and non-Latin scripts.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3__normalize.json`

```json
{
    "description": "Produce a canonical comparison key for a name by lower-casing, removing spaces, underscores and most punctuation while preserving certain meaningful characters and non-Latin scripts.",
    "cases": [
        {"input": "Darker Than Black", "expected_output": "darkerthanblack\n"},
        {"input": "Darker Than Black - Something", "expected_output": "darkerthanblacksomething\n"}
    ]
}
```

*3.4 Remove leading zeroes — normalize a numeric string.*

Remove leading zeroes from a numeric string, leaving the significant digits (and at least a single digit).

**Test Cases:** `rcb_tests/public_test_cases/feature3_4__remove_leading_zeroes.json`

```json
{
    "description": "Remove leading zeroes from a numeric string, leaving the significant digits (and at least a single digit).",
    "cases": [
        {"input": "000[the numeric index following the 'SP' marker (successor)]", "expected_output": "[the numeric index following the 'SP' marker (successor)]\n"},
        {"input": "[the numeric index following the 'SP' marker (successor)]", "expected_output": "[the numeric index following the 'SP' marker (successor)]\n"}
    ]
}
```

*3.5 Pad zeros — left-pad a numeric string.*

Left-pad a numeric string with zeroes to a minimum width of three characters; strings already that wide are unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5__pad_zeros.json`

```json
{
    "description": "Left-pad a numeric string with zeroes to a minimum width of three characters; strings already that wide are unchanged.",
    "cases": [
        {"input": "[the numeric index following the 'SP' marker (successor)]", "expected_output": "00[the numeric index following the 'SP' marker (successor)]\n"},
        {"input": "[the numeric index following the 'SP' marker (successor)]0", "expected_output": "0[the numeric index following the 'SP' marker (successor)]0\n"}
    ]
}
```

---

### Feature 4: File-Type Classification

**As a developer**, I want boolean predicates that tell me what kind of file a name is, so I can decide how to open or skip it.

**Expected Behavior / Usage:**

Each leaf inspects the file extension (or, for cover detection, the whole file name) and returns a boolean.

*4.[the numeric index following the 'SP' marker (successor)] Is archive — detect archive extensions.*

Report whether a file name has an archive extension (e.g. cbz/zip/rar/cbr/7z/cbt). Returns a boolean.

**Test Cases:** `rcb_tests/public_test_cases/feature4_[the numeric index following the 'SP' marker (successor)]__is_archive.json`

```json
{
    "description": "Report whether a file name has an archive extension (e.g. cbz/zip/rar/cbr/7z/cbt). Returns a boolean.",
    "cases": [
        {"input": "test.cbz", "expected_output": "true\n"},
        {"input": "test.cbr", "expected_output": "true\n"}
    ]
}
```

*4.2 Is book — detect book extensions.*

Report whether a file name has a book extension (epub or pdf). Returns a boolean.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2__is_book.json`

```json
{
    "description": "Report whether a file name has a book extension (epub or pdf). Returns a boolean.",
    "cases": [
        {"input": "test.epub", "expected_output": "true\n"},
        {"input": "test.pdf", "expected_output": "true\n"}
    ]
}
```

*4.3 Is epub — detect the epub extension.*

Report whether a file name has the epub extension (case-insensitive). Returns a boolean.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3__is_epub.json`

```json
{
    "description": "Report whether a file name has the epub extension (case-insensitive). Returns a boolean.",
    "cases": [
        {"input": "test.epub", "expected_output": "true\n"},
        {"input": "test.EPUB", "expected_output": "true\n"}
    ]
}
```

*4.4 Is image — detect supported raster images.*

Report whether a file name is a supported raster image (png/jpg/jpeg/webp/gif/avif), excluding dot-prefixed hidden files. Returns a boolean.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4__is_image.json`

```json
{
    "description": "Report whether a file name is a supported raster image (png/jpg/jpeg/webp/gif/avif), excluding dot-prefixed hidden files. Returns a boolean.",
    "cases": [
        {"input": "test.jpg", "expected_output": "true\n"},
        {"input": "test.jpeg", "expected_output": "true\n"}
    ]
}
```

*4.5 Is cover image — detect a front cover.*

Report whether a path's file name denotes a front cover image (e.g. cover/folder/!cover or a volume cover), but not a back cover. Returns a boolean.

**Test Cases:** `rcb_tests/public_test_cases/feature4_5__is_cover_image.json`

```json
{
    "description": "Report whether a path's file name denotes a front cover image (e.g. cover/folder/!cover or a volume cover), but not a back cover. Returns a boolean.",
    "cases": [
        {"input": "Love Hina - Special.jpg", "expected_output": "false\n"},
        {"input": "folder.jpg", "expected_output": "true\n"}
    ]
}
```

---

### Feature 5: Path Handling

**As a developer**, I want to normalize filesystem paths and skip junk folders, so my scanner behaves the same across operating systems and ignores system metadata.

**Expected Behavior / Usage:**

These leaves operate on path strings, returning either a normalized path or a boolean verdict.

*5.[the numeric index following the 'SP' marker (successor)] Normalize path — canonicalize separators.*

Normalize a filesystem path by converting backslashes to forward slashes and collapsing duplicate separators.

**Test Cases:** `rcb_tests/public_test_cases/feature5_[the numeric index following the 'SP' marker (successor)]__normalize_path.json`

```json
{
    "description": "Normalize a filesystem path by converting backslashes to forward slashes and collapsing duplicate separators.",
    "cases": [
        {"input": "/manga/[the numeric index following the 'SP' marker (successor)]/[the numeric index following the 'SP' marker (successor)]/[the numeric index following the 'SP' marker (successor)]", "expected_output": "/manga/[the numeric index following the 'SP' marker (successor)]/[the numeric index following the 'SP' marker (successor)]/[the numeric index following the 'SP' marker (successor)]\n"},
        {"input": "/manga/[the numeric index following the 'SP' marker (successor)]/[the numeric index following the 'SP' marker (successor)]/[the numeric index following the 'SP' marker (successor)].jpg", "expected_output": "/manga/[the numeric index following the 'SP' marker (successor)]/[the numeric index following the 'SP' marker (successor)]/[the numeric index following the 'SP' marker (successor)].jpg\n"}
    ]
}
```

*5.2 Blacklisted folder — detect system/junk folders.*

Report whether any path segment is a system/junk folder that should be skipped (e.g. macOS metadata, recycle/snapshot/trash folders). Returns a boolean.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2__has_blacklisted_folder.json`

```json
{
    "description": "Report whether any path segment is a system/junk folder that should be skipped (e.g. macOS metadata, recycle/snapshot/trash folders). Returns a boolean.",
    "cases": [
        {"input": "__MACOSX/Love Hina - Special.jpg", "expected_output": "true\n"},
        {"input": "TEST/Love Hina - Special.jpg", "expected_output": "false\n"}
    ]
}
```

---

### Feature 6: Numeric Range Extraction

**As a developer**, I want to read the low and high ends of a number or a hyphenated range, so I can compute the span a chapter/volume token covers.

**Expected Behavior / Usage:**

Each leaf accepts either a bare number or a hyphenated range and returns a number. A pure number returns itself; an unparseable input returns `0`.

*6.[the numeric index following the 'SP' marker (successor)] Minimum of range — return the lower bound.*

Given a number or a hyphenated range, return the minimum value as a number. Pure numbers return themselves; ranges return the lower bound; unparseable inputs return `0`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_[the numeric index following the 'SP' marker (successor)]__min_from_range.json`

```json
{
    "description": "Given a number or a hyphenated range, return the minimum value as a number. Pure numbers return themselves; ranges return the lower bound; unparseable inputs return 0.",
    "cases": [
        {"input": "[the numeric index following the 'SP' marker (successor)]2-[the numeric index following the 'SP' marker (successor)]4", "expected_output": "[the numeric index following the 'SP' marker (successor)]2\n"},
        {"input": "24", "expected_output": "24\n"}
    ]
}
```

*6.2 Maximum of range — return the upper bound.*

Given a number or a hyphenated range, return the maximum value as a number. Pure numbers return themselves; ranges return the upper bound; unparseable inputs return `0`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2__max_from_range.json`

```json
{
    "description": "Given a number or a hyphenated range, return the maximum value as a number. Pure numbers return themselves; ranges return the upper bound; unparseable inputs return 0.",
    "cases": [
        {"input": "[the numeric index following the 'SP' marker (successor)]2-[the numeric index following the 'SP' marker (successor)]4", "expected_output": "[the numeric index following the 'SP' marker (successor)]4\n"},
        {"input": "24", "expected_output": "24\n"}
    ]
}
```

---

### Feature 7: Balanced Delimiter Matching

**As a developer**, I want to verify that a string's brackets are balanced, so I can validate tags before stripping them.

**Expected Behavior / Usage:**

Each leaf reports whether the relevant delimiter type is correctly balanced and properly nested across the entire string. Returns a boolean.

*7.[the numeric index following the 'SP' marker (successor)] Balanced parentheses — validate round brackets.*

Report whether a string's parentheses are correctly balanced and properly nested across the entire string. Returns a boolean.

**Test Cases:** `rcb_tests/public_test_cases/feature7_[the numeric index following the 'SP' marker (successor)]__balanced_paren.json`

```json
{
    "description": "Report whether a string's parentheses are correctly balanced and properly nested across the entire string. Returns a boolean.",
    "cases": [
        {"input": "The quick brown fox jumps over the lazy dog", "expected_output": "true\n"},
        {"input": "(The quick brown fox jumps over the lazy dog)", "expected_output": "true\n"}
    ]
}
```

*7.2 Balanced brackets — validate square brackets.*

Report whether a string's square brackets are correctly balanced and properly nested across the entire string. Returns a boolean.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2__balanced_bracket.json`

```json
{
    "description": "Report whether a string's square brackets are correctly balanced and properly nested across the entire string. Returns a boolean.",
    "cases": [
        {"input": "The quick brown fox jumps over the lazy dog", "expected_output": "true\n"},
        {"input": "[The quick brown fox jumps over the lazy dog]", "expected_output": "true\n"}
    ]
}
```

---

### Feature 8: CSS Font Source Parsing

**As a developer**, I want to find and split the font reference inside a CSS `@font-face` source declaration, so I can rewrite or relocate embedded fonts in e-book stylesheets.

**Expected Behavior / Usage:**

These leaves operate on a single CSS font-source string. One reports presence; the other splits the declaration into its parts. Inline `data:` URIs are explicitly excluded.

*8.[the numeric index following the 'SP' marker (successor)] Font source present — detect an external font reference.*

Report whether a CSS font source declaration references an external font file via `url(...)` or `local(...)`, excluding inline `data:` URIs. Returns a boolean.

**Test Cases:** `rcb_tests/public_test_cases/feature8_[the numeric index following the 'SP' marker (successor)]__font_src_match.json`

```json
{
    "description": "Report whether a CSS font source declaration references an external font file via url(...) or local(...), excluding inline data: URIs. Returns a boolean.",
    "cases": [
        {"input": "src: url(fonts/AvenirNext-UltraLight.ttf)", "expected_output": "true\n"},
        {"input": "src: url(ideal-sans-serif.woff)", "expected_output": "true\n"}
    ]
}
```

*8.2 Font source split — separate directive, path and closer.*

Split a CSS font source declaration into its three parts: the opening directive up to the opening quote/paren, the referenced file path, and the closing quote/paren. Output is the three parts, one per line, in order.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2__font_src_separate.json`

```json
{
    "description": "Split a CSS font source declaration into its three parts: the opening directive up to the opening quote/paren, the referenced file path, and the closing quote/paren. Output is the three parts, one per line, in order.",
    "cases": [
        {"input": "src: url(fonts/AvenirNext-UltraLight.ttf)", "expected_output": "src: url(\nfonts/AvenirNext-UltraLight.ttf\n)\n"},
        {"input": "src: url(ideal-sans-serif.woff)", "expected_output": "src: url(\nideal-sans-serif.woff\n)\n"}
    ]
}
```

---

### Feature 9: Natural-Order Sorting

**As a developer**, I want to sort names and chapter numbers the way a human reader expects, so pages and chapters display in the right order.

**Expected Behavior / Usage:**

Two leaves sort lists of strings in natural order (numeric runs compared numerically). Two more sort lists of chapter numbers ascending while pinning a special default/unnumbered sentinel value either last or first. Each output is the sorted sequence, one entry per line.

*9.[the numeric index following the 'SP' marker (successor)] String natural sort — order strings the human way.*

Sort a list of strings in natural (human) order: embedded digit runs compare numerically rather than lexically, letters compare case-insensitively, and non-alphanumeric-leading entries sort ahead of alphanumeric ones. Output is the sorted list, one entry per line.

**Test Cases:** `rcb_tests/public_test_cases/feature9_[the numeric index following the 'SP' marker (successor)]__string_logical_sort.json`

```json
{
    "description": "Sort a list of strings in natural (human) order: embedded digit runs compare numerically rather than lexically, letters compare case-insensitively, and non-alphanumeric-leading entries sort ahead of alphanumeric ones. Output is the sorted list, one entry per line.",
    "cases": [
        {"input": ["x[the numeric index following the 'SP' marker (successor)].jpg","x[the numeric index following the 'SP' marker (successor)]0.jpg","x3.jpg","x4.jpg","x[the numeric index following the 'SP' marker (successor)][the numeric index following the 'SP' marker (successor)].jpg"], "expected_output": "x[the numeric index following the 'SP' marker (successor)].jpg\nx3.jpg\nx4.jpg\nx[the numeric index following the 'SP' marker (successor)]0.jpg\nx[the numeric index following the 'SP' marker (successor)][the numeric index following the 'SP' marker (successor)].jpg\n"},
        {"input": ["a.jpg","aaa.jpg","[the numeric index following the 'SP' marker (successor)].jpg"], "expected_output": "[the numeric index following the 'SP' marker (successor)].jpg\na.jpg\naaa.jpg\n"}
    ]
}
```

*9.2 Filename natural sort — order file names the human way.*

Sort a list of file names using the same natural-order rule, so numeric segments order numerically. Output is the sorted list, one entry per line.

**Test Cases:** `rcb_tests/public_test_cases/feature9_2__numeric_sort.json`

```json
{
    "description": "Sort a list of file names using the same natural-order rule, so numeric segments order numerically. Output is the sorted list, one entry per line.",
    "cases": [
        {"input": ["x[the numeric index following the 'SP' marker (successor)].jpg","x[the numeric index following the 'SP' marker (successor)]0.jpg","x3.jpg","x4.jpg","x[the numeric index following the 'SP' marker (successor)][the numeric index following the 'SP' marker (successor)].jpg"], "expected_output": "x[the numeric index following the 'SP' marker (successor)].jpg\nx3.jpg\nx4.jpg\nx[the numeric index following the 'SP' marker (successor)]0.jpg\nx[the numeric index following the 'SP' marker (successor)][the numeric index following the 'SP' marker (successor)].jpg\n"},
        {"input": ["x[the numeric index following the 'SP' marker (successor)].0.jpg","0.5.jpg","0.3.jpg"], "expected_output": "0.3.jpg\n0.5.jpg\nx[the numeric index following the 'SP' marker (successor)].0.jpg\n"}
    ]
}
```

*9.3 Chapter sort, default last — pin the sentinel to the end.*

Sort a list of chapter numbers ascending, but always place the default/unnumbered sentinel value (`[the custom negative sentinel value used for missing volumes]`) at the end. Output is the sorted sequence, one number per line.

**Test Cases:** `rcb_tests/public_test_cases/feature9_3__chapter_sort_default_last.json`

```json
{
    "description": "Sort a list of chapter numbers ascending, but always place the default/unnumbered sentinel value ([the custom negative sentinel value used for missing volumes]) at the end. Output is the sorted sequence, one number per line.",
    "cases": [
        {"input": [[the numeric index following the 'SP' marker (successor)],2,[the custom negative sentinel value used for missing volumes]], "expected_output": "[the numeric index following the 'SP' marker (successor)]\n2\n[the custom negative sentinel value used for missing volumes]\n"},
        {"input": [3,[the numeric index following the 'SP' marker (successor)],2], "expected_output": "[the numeric index following the 'SP' marker (successor)]\n2\n3\n"}
    ]
}
```

*9.4 Chapter sort, default first — pin the sentinel to the front.*

Sort a list of chapter numbers in ascending order; a special default/unnumbered sentinel value, when present, is ordered before all real numbers. Output is the sorted sequence, one number per line.

**Test Cases:** `rcb_tests/public_test_cases/feature9_4__chapter_sort_default_first.json`

```json
{
    "description": "Sort a list of chapter numbers in ascending order; a special default/unnumbered sentinel value, when present, is ordered before all real numbers. Output is the sorted sequence, one number per line.",
    "cases": [
        {"input": [[the numeric index following the 'SP' marker (successor)],2,0], "expected_output": "0\n[the numeric index following the 'SP' marker (successor)]\n2\n"},
        {"input": [3,[the numeric index following the 'SP' marker (successor)],2], "expected_output": "[the numeric index following the 'SP' marker (successor)]\n2\n3\n"}
    ]
}
```

---

## Deliverables

- A core library implementing the 35 leaf functional points above (filename metadata parsing, special-issue handling, title cleaning/normalization, file-type classification, path handling, numeric range extraction, balanced-delimiter matching, CSS font-source parsing, and natural-order sorting), with business logic decoupled from I/O.
- An execution adapter that reads one JSON `input` per case from the harness, invokes the corresponding core operation, and writes the exact `expected_output` wire format (values rendered as shown; booleans as `true`/`false`; arrays one element per line; each output terminated by a trailing newline).
- A single test entry point `rcb_tests/test.sh` that runs every JSON case under the selected cases directory and writes one raw-stdout `.txt` per case to `rcb_tests/stdout/<cases-dir>/`, supporting `--cases-dir <subdir>` to switch between `test_cases` and `public_test_cases`.


---
**Implementation notes:**
- follow the normalization pattern used for other numeric segments in previous parse functions
- apply the same string ordering logic found in the file_sorter utility
