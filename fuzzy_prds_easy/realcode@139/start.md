## Product Requirement Document

# Code-Review Payload Parsing Library - Typed Model & Aggregation for Pull/Merge Request Automation

## Project Goal

Build a library that ingests the raw JSON metadata a continuous-integration bot receives for a code-review (the pull/merge request currently being evaluated) and exposes it as a strongly-typed, platform-agnostic object model. It allows automation authors to read pull-request facts (title, state, authors, commits, comments, milestones, changed files, changed line counts, …) directly as typed values, without hand-parsing deeply nested, platform-specific JSON or juggling shell commands.

---

## Background & Problem

Code-review automation runs against several different hosting systems: two cloud platforms (one organised around *pull requests*, one around *merge requests*) and one self-hosted server product. Each emits a large, differently-shaped JSON document describing the review under evaluation. Without this library, every automation script must re-implement brittle parsing of those documents — reaching into nested objects, coping with snake_case vs. camelCase keys, decoding ISO-8601 timestamps into epoch milliseconds, treating absent optional attributes as nulls, and shelling out to compute diff statistics. This produces repetitive, error-prone boilerplate that breaks whenever a payload shape changes.

With this library, the automation author receives one decoded model. Reading `the pull request title`, `the list of requested reviewer teams`, `the milestone due date`, `which platform produced this payload`, or `how many lines this PR changes` becomes a direct field/expression access. The library also detects which of the three supported platforms produced a given payload so a single script can run everywhere.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-domain parsing library (three source platforms, several record types each, plus derived aggregations). It MUST NOT be a single "god file". Output a clear, multi-file directory tree separating the per-platform model definitions, the shared value types (users, commits, timestamps, branch references), the derived aggregations (diff statistics), and the I/O utilities. The execution adapter MUST live separately from the core model.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract for the execution adapter**, NOT the internal data model. The core parsing/model layer MUST remain decoupled from stdin/stdout and from the specific command envelope used by the adapter. The adapter is solely responsible for translating a JSON command into idiomatic calls against the core model and rendering the result.

3. **Adherence to SOLID Design Principles (scaled to project size):**
   - **SRP:** Separate command parsing, routing, model decoding, derived computation, and output formatting.
   - **OCP:** Adding a new platform or record type must not require editing existing record types.
   - **LSP:** The per-platform user/commit/reference value types must be substitutable wherever a generic equivalent is expected.
   - **ISP:** Keep model interfaces small and cohesive (a milestone need not know about pipelines).
   - **DIP:** Diff-statistics computation must depend on an abstraction for "run a command and read its output", not on a concrete process launcher, so it is testable and injectable.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The decoded model must be elegant and idiomatic to the target language; timestamps are exposed as epoch milliseconds, optional attributes as nullable fields.
   - **Resilience:** Absent optional attributes must decode to a neutral null marker rather than failing. Unknown/extra keys in the wire payload must be ignored. Errors must be modelled as neutral categories, never leaking host-language runtime identity.

---

## Core Features

### Feature 1: Pull-Request Record Parsing

**As a developer**, I want to decode a cloud pull-request payload into a typed record, so I can read its scalar facts, timestamps, author/assignee accounts and branch references directly.

**Expected Behavior / Usage:**

The adapter receives a command `{"view": "github_pull_request", "data": <pull-request object>}`. It decodes the object and emits one `key=value` line per exposed field. Timestamps (`created_at`, `updated_at`, `closed_at`, `merged_at`) are rendered as epoch-millisecond integers; absent optional timestamps render as `null`. The enumerated `state` is rendered as an upper-case symbolic name (e.g. `CLOSED`). Nested accounts are flattened with dotted keys (`user.login`, `assignee.login`), list sizes are exposed as `*.count`, and the head/base branch references expose their `label`, `ref`, `sha` and owning repository full-name. An absent milestone renders as `milestone=null`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_github_pull_request.json`

```json
{
    "description": "Parse a hosted Git platform pull-request payload and expose its scalar fields, timestamps as epoch milliseconds, nested author/assignee accounts, and head/base branch references.",
    "cases": [
        {
            "input": {
                "view": "github_pull_request",
                "data": {
                    "number": 609, "title": "Xcode updates", "body": "Keep tooling up to date.",
                    "user": {"id": 498212, "login": "alice", "type": "User", "avatar_url": "https://img.example/alice.png"},
                    "assignee": {"id": 49038, "login": "bob", "type": "User", "avatar_url": "https://img.example/bob.png"},
                    "assignees": [{"id": 49038, "login": "bob", "type": "User", "avatar_url": "https://img.example/bob.png"}],
                    "created_at": "2016-07-26T19:57:30Z", "updated_at": "2016-08-17T16:46:15Z",
                    "closed_at": "2016-08-17T16:46:14Z", "merged_at": "2016-08-17T16:46:14Z",
                    "head": {"label": "acme:feature", "ref": "feature", "sha": "d769f27",
                        "user": {"id": 546231, "login": "acme", "type": "Organization", "avatar_url": "https://img.example/acme.png"},
                        "repo": {"id": 22613546, "name": "widget", "full_name": "acme/widget", "private": false, "description": "The widget app", "fork": false, "html_url": "https://example.com/acme/widget"}},
                    "base": {"label": "acme:main", "ref": "main", "sha": "68c8db8",
                        "user": {"id": 546231, "login": "acme", "type": "Organization", "avatar_url": "https://img.example/acme.png"},
                        "repo": {"id": 22613546, "name": "widget", "full_name": "acme/widget", "private": false, "description": "The widget app", "fork": false, "html_url": "https://example.com/acme/widget"}},
                    "state": "closed", "locked": false, "merged": true,
                    "commits": 15, "comments": 8, "review_comments": 11,
                    "additions": 205, "deletions": 111, "changed_files": 56,
                    "milestone": null, "html_url": "https://example.com/acme/widget/pull/609"
                }
            },
            "expected_output": "number=609\ntitle=Xcode updates\nstate=CLOSED\nbody=Keep tooling up to date.\ncreated_at=1469563050000\nupdated_at=1471452375000\nclosed_at=1471452374000\nmerged_at=1471452374000\nlocked=false\nmerged=true\ncommit_count=15\ncomment_count=8\nreview_comment_count=11\nadditions=205\ndeletions=111\nchanged_files=56\nhtml_url=https://example.com/acme/widget/pull/609\nmilestone=null\nuser.id=498212\nuser.login=alice\nuser.type=USER\nuser.avatar_url=https://img.example/alice.png\nassignee.login=bob\nassignees.count=1\nassignees.0.login=bob\nhead.label=acme:feature\nhead.ref=feature\nhead.sha=d769f27\nhead.repo.full_name=acme/widget\nbase.label=acme:main\nbase.ref=main\nbase.sha=68c8db8\nbase.repo.full_name=acme/widget\n"
        }
    ]
}
```

---

### Feature 2: Pull-Request Commit List Parsing

**As a developer**, I want to decode the commits attached to a pull request, so I can inspect each commit's identity and its embedded raw git authorship.

**Expected Behavior / Usage:**

Command `{"view": "github_commits", "data": [<commit objects>]}`. The adapter emits `count=<n>` followed, per commit index `i`, by the platform-level `i.sha`, `i.url`, `i.author.login`, `i.committer.login`, and the embedded raw git commit (`i.commit.message`, `i.commit.sha` — `null` when omitted — `i.commit.author.name/email/date`, `i.commit.committer.name/date`, `i.commit.url`). Dates inside the raw git commit are passed through verbatim as their original ISO strings.

**Test Cases:** `rcb_tests/public_test_cases/feature2_github_commits.json`

```json
{
    "description": "Parse the list of commits attached to a pull request, exposing each commit's SHA, web URL, platform author/committer handles, and the embedded raw git-commit (message, author/committer name+email+date, url).",
    "cases": [
        {
            "input": {
                "view": "github_commits",
                "data": [
                    {"sha": "93ae30c", "url": "https://api.example/commits/93ae30c",
                     "author": {"id": 498212, "login": "alice", "type": "User", "avatar_url": "https://img.example/alice.png"},
                     "commit": {"author": {"name": "Ash Furrow", "email": "ash@example.com", "date": "2016-07-26T19:54:16Z"},
                                "committer": {"name": "Ash Furrow", "email": "ash@example.com", "date": "2016-07-26T19:55:00Z"},
                                "message": "[Xcode] Updates for compatibility.", "parents": [], "url": "https://api.example/commits/93ae30c"},
                     "committer": {"id": 498212, "login": "alice", "type": "User", "avatar_url": "https://img.example/alice.png"}},
                    {"sha": "a1b2c3d", "url": "https://api.example/commits/a1b2c3d",
                     "author": {"id": 49038, "login": "bob", "type": "User", "avatar_url": "https://img.example/bob.png"},
                     "commit": {"sha": "a1b2c3d", "author": {"name": "Ash Furrow", "email": "ash@example.com", "date": "2016-07-26T19:54:16Z"},
                                "committer": {"name": "Ash Furrow", "email": "ash@example.com", "date": "2016-07-26T19:55:00Z"},
                                "message": "Follow-up fix.", "parents": ["93ae30c"], "url": "https://api.example/commits/a1b2c3d"},
                     "committer": {"id": 49038, "login": "bob", "type": "User", "avatar_url": "https://img.example/bob.png"}}
                ]
            },
            "expected_output": "count=2\n0.sha=93ae30c\n0.url=https://api.example/commits/93ae30c\n0.author.login=alice\n0.committer.login=alice\n0.commit.message=[Xcode] Updates for compatibility.\n0.commit.sha=null\n0.commit.author.name=Ash Furrow\n0.commit.author.email=ash@example.com\n0.commit.author.date=2016-07-26T19:54:16Z\n0.commit.committer.name=Ash Furrow\n0.commit.committer.date=2016-07-26T19:55:00Z\n0.commit.url=https://api.example/commits/93ae30c\n1.sha=a1b2c3d\n1.url=https://api.example/commits/a1b2c3d\n1.author.login=bob\n1.committer.login=bob\n1.commit.message=Follow-up fix.\n1.commit.sha=a1b2c3d\n1.commit.author.name=Ash Furrow\n1.commit.author.email=ash@example.com\n1.commit.author.date=2016-07-26T19:54:16Z\n1.commit.committer.name=Ash Furrow\n1.commit.committer.date=2016-07-26T19:55:00Z\n1.commit.url=https://api.example/commits/a1b2c3d\n"
        }
    ]
}
```

---

### Feature 3: Issue Record Parsing

**As a developer**, I want to decode the issue that backs a pull request, so I can read its state, comment count, timestamps, labels and attached milestone.

**Expected Behavior / Usage:**

Command `{"view": "github_issue", "data": <issue object>}`. The adapter emits `id`, `number`, `title`, `body`, symbolic `state`, `locked`, `comment_count`, epoch-millisecond `created_at`/`updated_at`/`closed_at` (`null` when absent), `labels.count`, and — when a milestone is present — the milestone fields under the `milestone.*` prefix (including its creator handle and all four epoch-millisecond timestamps). A missing milestone renders as `milestone=null`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_github_issue.json`

```json
{
    "description": "Parse the issue backing a pull request, exposing identifiers, state, lock flag, comment count, timestamps, label count and the attached milestone fields.",
    "cases": [
        {
            "input": {
                "view": "github_issue",
                "data": {
                    "id": 2190001234, "number": 609, "title": "Xcode updates",
                    "user": {"id": 498212, "login": "alice", "type": "User", "avatar_url": "https://img.example/alice.png"},
                    "state": "closed", "locked": false, "body": "Keep tooling up to date.", "comments": 8,
                    "assignee": null, "assignees": [],
                    "milestone": {"id": 1002604, "number": 1, "state": "open", "title": "v1.0",
                        "description": "Tracking milestone for version 1.0",
                        "creator": {"id": 1, "login": "octocat", "type": "User", "avatar_url": "https://img.example/octocat.gif"},
                        "open_issues": 4, "closed_issues": 8,
                        "created_at": "2011-04-10T20:09:31Z", "updated_at": "2014-03-03T18:58:10Z",
                        "closed_at": "2013-02-12T13:22:01Z", "due_on": "2012-10-09T23:39:01Z"},
                    "created_at": "2016-07-26T19:57:30Z", "updated_at": "2016-08-17T16:46:14Z",
                    "closed_at": null, "labels": []
                }
            },
            "expected_output": "id=2190001234\nnumber=609\ntitle=Xcode updates\nbody=Keep tooling up to date.\nstate=CLOSED\nlocked=false\ncomment_count=8\ncreated_at=1469563050000\nupdated_at=1471452374000\nclosed_at=null\nlabels.count=0\nmilestone.id=1002604\nmilestone.number=1\nmilestone.state=OPEN\nmilestone.title=v1.0\nmilestone.description=Tracking milestone for version 1.0\nmilestone.creator.login=octocat\nmilestone.open_issues=4\nmilestone.closed_issues=8\nmilestone.created_at=1302466171000\nmilestone.updated_at=1393873090000\nmilestone.closed_at=1360675321000\nmilestone.due_on=1349825941000\n"
        }
    ]
}
```

---

### Feature 4: Requested-Reviewers Parsing

**As a developer**, I want to decode the requested-reviewers block, so I can list the individual accounts and teams whose review was requested.

**Expected Behavior / Usage:**

Command `{"view": "github_requested_reviewers", "data": <requested-reviewers object>}`. The adapter emits `users.count` plus the first user's `id`/`login`, and `teams.count` plus the first team's `id`/`name`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_github_requested_reviewers.json`

```json
{
    "description": "Parse the requested-reviewers payload into the list of requested user accounts and the list of requested teams.",
    "cases": [
        {
            "input": {
                "view": "github_requested_reviewers",
                "data": {
                    "users": [{"id": 1, "login": "octocat", "type": "User", "avatar_url": "https://img.example/octocat.gif"}],
                    "teams": [{"id": 1, "name": "Justice League"}]
                }
            },
            "expected_output": "users.count=1\nusers.0.id=1\nusers.0.login=octocat\nteams.count=1\nteams.0.id=1\nteams.0.name=Justice League\n"
        }
    ]
}
```

---

### Feature 5: Milestone Parsing

**As a developer**, I want to decode a milestone record robustly, so I can read its state and dates whether or not the optional attributes are present.

**Expected Behavior / Usage:**

Command `{"view": "github_milestone", "data": <milestone object>}`. The adapter emits `id`, `number`, symbolic `state`, `title`, `description` (`null` when absent), creator handle, open/closed issue counts, and the four timestamps `created_at`, `updated_at`, `closed_at`, `due_on` (each rendered as epoch milliseconds, or `null` when absent). This feature has two leaf scenarios distinguished only by their input data: one where optional attributes are absent, and one where the milestone is closed with every optional attribute populated.

*5.1 Optional Attributes Absent — a milestone missing description, closed and due timestamps*

When `description`, `closed_at` and `due_on` are omitted from the payload, they decode to the neutral `null` marker; the populated `created_at`/`updated_at` still render as epoch milliseconds.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_milestone_optional_nulls.json`

```json
{
    "description": "Parse a milestone whose optional attributes (description, closed timestamp, due timestamp) are absent, rendering them as the neutral null marker.",
    "cases": [
        {
            "input": {
                "view": "github_milestone",
                "data": {
                    "id": 5, "number": 2, "state": "open", "title": "v2.0",
                    "creator": {"id": 1, "login": "octocat", "type": "User", "avatar_url": "https://img.example/octocat.gif"},
                    "open_issues": 1, "closed_issues": 0,
                    "created_at": "2011-04-10T20:09:31Z", "updated_at": "2014-03-03T18:58:10Z"
                }
            },
            "expected_output": "id=5\nnumber=2\nstate=OPEN\ntitle=v2.0\ndescription=null\ncreator.login=octocat\nopen_issues=1\nclosed_issues=0\ncreated_at=1302466171000\nupdated_at=1393873090000\nclosed_at=null\ndue_on=null\n"
        }
    ]
}
```

*5.2 Closed Milestone — a milestone whose state is closed and whose optional attributes are all present*

When the milestone is closed, the symbolic `state` is `CLOSED` and the optional `description`, `closed_at`, `due_on` are all rendered with their decoded values.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_milestone_closed_state.json`

```json
{
    "description": "Parse a milestone that has been closed, exposing its closed state plus all populated optional timestamps.",
    "cases": [
        {
            "input": {
                "view": "github_milestone",
                "data": {
                    "id": 6, "number": 3, "state": "closed", "title": "v3.0", "description": "shipped",
                    "creator": {"id": 1, "login": "octocat", "type": "User", "avatar_url": "https://img.example/octocat.gif"},
                    "open_issues": 0, "closed_issues": 5,
                    "created_at": "2011-04-10T20:09:31Z", "updated_at": "2014-03-03T18:58:10Z",
                    "closed_at": "2013-02-12T13:22:01Z", "due_on": "2012-10-09T23:39:01Z"
                }
            },
            "expected_output": "id=6\nnumber=3\nstate=CLOSED\ntitle=v3.0\ndescription=shipped\ncreator.login=octocat\nopen_issues=0\nclosed_issues=5\ncreated_at=1302466171000\nupdated_at=1393873090000\nclosed_at=1360675321000\ndue_on=1349825941000\n"
        }
    ]
}
```

---

### Feature 6: Source-Platform Detection

**As a developer**, I want the decoded payload to tell me which hosting platform produced it, so a single automation script can run unchanged across all supported platforms.

**Expected Behavior / Usage:**

Command `{"view": "platform_detection", "data": <complete review payload>}`. The complete payload always carries a `git` block and exactly one platform-specific block keyed by `github`, `gitlab` or `bitbucket_server`. The adapter emits the detected `platform` name plus three mutually-exclusive boolean flags `on_github`, `on_gitlab`, `on_bitbucket_server` — exactly one of which is `true`, matching whichever platform block is present. (The hidden suite covers all three platforms; the embedded example shows the merge-request platform.)

**Test Cases:** `rcb_tests/public_test_cases/feature6_platform_detection.json`

```json
{
    "description": "Given a complete review payload, detect which hosting platform produced it and expose the three mutually-exclusive platform flags.",
    "cases": [
        {
            "input": {
                "view": "platform_detection",
                "data": {
                    "danger": {
                        "git": {"modified_files": [".travis.yml", "Podfile"], "created_files": [".ruby-version"], "deleted_files": ["Obsolete.swift"], "commits": []},
                        "gitlab": {
                            "mr": {
                                "allow_collaboration": false, "allow_maintainer_to_push": false, "approvals_before_merge": 1,
                                "assignee": {"avatar_url": "https://grav.example/orta", "id": 377669, "name": "Orta", "state": "active", "username": "orta", "web_url": "https://gitlab.example/orta"},
                                "author": {"avatar_url": "https://grav.example/fm", "id": 3331525, "name": "Franco Meloni", "state": "active", "username": "f-meloni", "web_url": "https://gitlab.example/f-meloni"},
                                "changes_count": "1", "closed_at": null, "closed_by": null, "description": "Updating it to avoid problems",
                                "diff_refs": {"base_sha": "ef28580", "head_sha": "621bc33", "start_sha": "ef28580"}, "downvotes": 0,
                                "first_deployed_to_production_at": "2019-04-11T01:50:22Z", "force_remove_source_branch": true,
                                "id": 27469633, "iid": 182, "latest_build_finished_at": "2019-04-11T01:53:22Z", "latest_build_started_at": "2019-04-11T01:40:22Z",
                                "labels": [], "merge_commit_sha": "377a24f", "merged_at": "2019-04-11T01:57:22Z",
                                "merged_by": {"avatar_url": "https://grav.example/orta", "id": 377669, "name": "Orta", "state": "active", "username": "orta", "web_url": "https://gitlab.example/orta"},
                                "merge_when_pipeline_succeeds": false,
                                "milestone": {"created_at": "2019-04-10T20:37:45Z", "description": "Test Description", "due_date": "2019-06-10T00:00:00Z", "id": 1, "iid": 2, "project_id": 1000, "start_date": "2019-04-10T20:37:45Z", "state": "closed", "title": "Test Milestone", "updated_at": "2019-04-10T20:37:45Z", "web_url": "https://gitlab.example/milestone"},
                                "pipeline": {"id": 50, "ref": "ef28580", "sha": "621bc33", "status": "success", "web_url": "https://gitlab.example/pipeline/621"},
                                "project_id": "1620437", "sha": "621bc33", "should_remove_source_branch": null, "source_branch": "patch-2", "source_project_id": "10132593",
                                "state": "merged", "subscribed": false, "target_branch": "master", "target_project_id": "1620437", "timeStats": null,
                                "title": "Update getting_started.html.slim", "upvotes": 0, "user": {"can_merge": false}, "user_notes_count": 0,
                                "web_url": "https://gitlab.example/merge_requests/182", "work_in_progress": false
                            },
                            "metadata": {"pullRequestID": "182", "repoSlug": "acme/widget-systems"}
                        }
                    }
                }
            },
            "expected_output": "platform=gitlab\non_github=false\non_gitlab=true\non_bitbucket_server=false\n"
        }
    ]
}
```

---

### Feature 7: Merge-Request Record Parsing

**As a developer**, I want to decode the second cloud platform's merge-request payload, so I can read its scalar facts, the derived can-merge flag, diff refs, pipeline, milestone and participant accounts.

**Expected Behavior / Usage:**

Command `{"view": "gitlab_merge_request", "data": <merge-request object>}`. The adapter emits the merge-request scalar fields (`id`, `iid`, `title`, `description`, symbolic `state`, the various booleans/counts, branch names, project ids, web URL). It also exposes `can_merge`, a **derived** boolean lifted out of a nested user-permission object (it is NOT a top-level field). Epoch-millisecond timestamps are rendered for `closed_at`/`merged_at` (`null` when absent). Nested author/assignee/merged-by accounts are flattened by username, and the `diff_refs.*`, `pipeline.*` and `milestone.*` sub-objects are flattened with dotted keys; an absent milestone renders as `milestone=null`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_gitlab_merge_request.json`

```json
{
    "description": "Parse a GitLab-style merge-request payload, exposing scalar fields, the derived can-merge flag, diff refs, pipeline, milestone and participant accounts.",
    "cases": [
        {
            "input": {
                "view": "gitlab_merge_request",
                "data": {
                    "allow_collaboration": false, "allow_maintainer_to_push": false, "approvals_before_merge": 1,
                    "assignee": {"avatar_url": "https://grav.example/orta", "id": 377669, "name": "Orta", "state": "active", "username": "orta", "web_url": "https://gitlab.example/orta"},
                    "author": {"avatar_url": "https://grav.example/fm", "id": 3331525, "name": "Franco Meloni", "state": "active", "username": "f-meloni", "web_url": "https://gitlab.example/f-meloni"},
                    "changes_count": "1", "closed_at": null, "closed_by": null, "description": "Updating it to avoid problems",
                    "diff_refs": {"base_sha": "ef28580", "head_sha": "621bc33", "start_sha": "ef28580"}, "downvotes": 0,
                    "first_deployed_to_production_at": "2019-04-11T01:50:22Z", "force_remove_source_branch": true,
                    "id": 27469633, "iid": 182, "latest_build_finished_at": "2019-04-11T01:53:22Z", "latest_build_started_at": "2019-04-11T01:40:22Z",
                    "labels": [], "merge_commit_sha": "377a24f", "merged_at": "2019-04-11T01:57:22Z",
                    "merged_by": {"avatar_url": "https://grav.example/orta", "id": 377669, "name": "Orta", "state": "active", "username": "orta", "web_url": "https://gitlab.example/orta"},
                    "merge_when_pipeline_succeeds": false,
                    "milestone": {"created_at": "2019-04-10T20:37:45Z", "description": "Test Description", "due_date": "2019-06-10T00:00:00Z", "id": 1, "iid": 2, "project_id": 1000, "start_date": "2019-04-10T20:37:45Z", "state": "closed", "title": "Test Milestone", "updated_at": "2019-04-10T20:37:45Z", "web_url": "https://gitlab.example/milestone"},
                    "pipeline": {"id": 50, "ref": "ef28580", "sha": "621bc33", "status": "success", "web_url": "https://gitlab.example/pipeline/621"},
                    "project_id": "1620437", "sha": "621bc33", "should_remove_source_branch": null, "source_branch": "patch-2", "source_project_id": "10132593",
                    "state": "merged", "subscribed": false, "target_branch": "master", "target_project_id": "1620437", "timeStats": null,
                    "title": "Update getting_started.html.slim", "upvotes": 0, "user": {"can_merge": false}, "user_notes_count": 0,
                    "web_url": "https://gitlab.example/merge_requests/182", "work_in_progress": false
                }
            },
            "expected_output": "id=27469633\niid=182\ntitle=Update getting_started.html.slim\ndescription=Updating it to avoid problems\nstate=MERGED\nallow_collaboration=false\nallow_maintainer_to_push=false\napprovals_before_merge=1\nchanges_count=1\nclosed_at=null\ncan_merge=false\ndownvotes=0\nupvotes=0\nforce_remove_source_branch=true\nmerge_commit_sha=377a24f\nmerged_at=1554947842000\nmerge_on_pipeline_success=false\nsource_branch=patch-2\ntarget_branch=master\nproject_id=1620437\nsha=621bc33\nsubscribed=false\nuser_notes_count=0\nweb_url=https://gitlab.example/merge_requests/182\nwork_in_progress=false\nlabels.count=0\nauthor.username=f-meloni\nauthor.state=ACTIVE\nassignee.username=orta\nmerged_by.username=orta\ndiff_refs.base_sha=ef28580\ndiff_refs.head_sha=621bc33\ndiff_refs.start_sha=ef28580\npipeline.id=50\npipeline.status=SUCCESS\npipeline.web_url=https://gitlab.example/pipeline/621\nmilestone.title=Test Milestone\nmilestone.state=CLOSED\nmilestone.due_date=1560124800000\n"
        }
    ]
}
```

---

### Feature 8: Merge-Request Metadata Parsing

**As a developer**, I want to decode the merge-request metadata block, so I can read the pull-request id and repository slug regardless of platform.

**Expected Behavior / Usage:**

Command `{"view": "gitlab_metadata", "data": <metadata object>}`. The adapter emits `pull_request_id` and `repo_slug`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_gitlab_metadata.json`

```json
{
    "description": "Parse the merge-request metadata block into pull-request id and repository slug.",
    "cases": [
        {
            "input": {"view": "gitlab_metadata", "data": {"pullRequestID": "182", "repoSlug": "acme/widget-systems"}},
            "expected_output": "pull_request_id=182\nrepo_slug=acme/widget-systems\n"
        }
    ]
}
```

---

### Feature 9: Self-Hosted Server Pull-Request Parsing

**As a developer**, I want to decode a self-hosted server pull-request payload, so I can read its state flags, author, source/target branch references and reviewers/participants.

**Expected Behavior / Usage:**

Command `{"view": "bitbucket_pull_request", "data": <pull-request object>}`. This platform supplies its creation date as an epoch-millisecond integer directly (rendered through as `created_at`). The adapter emits `id`, `title`, symbolic `state`, the `open`/`closed`/`locked` booleans, the author account name/email, the source (`from_ref.*`) and target (`to_ref.*`) branch references each with branch id, display id, latest commit and (for the source) repository slug and project key, and the reviewer/participant lists with `*.count` plus the first entry's account name (and, for reviewers, approval flag and last-reviewed commit).

**Test Cases:** `rcb_tests/public_test_cases/feature9_bitbucket_pull_request.json`

```json
{
    "description": "Parse a self-hosted server pull-request payload, exposing state flags, epoch timestamp, author account, source/target branch refs with repository info, and reviewer/participant accounts.",
    "cases": [
        {
            "input": {
                "view": "bitbucket_pull_request",
                "data": {
                    "id": 1, "version": 1, "title": "Pull request title", "state": "OPEN", "open": true, "closed": false,
                    "createdDate": 1518863923273, "updatedDate": 1518863923273,
                    "fromRef": {"id": "refs/heads/master", "displayId": "master", "latestCommit": "8942a1f",
                        "repository": {"name": "Repo", "slug": "repo", "scmId": "git", "public": false, "forkable": true, "project": {"id": 1, "key": "PROJ", "name": "Project", "public": false, "type": "NORMAL"}}},
                    "toRef": {"id": "refs/heads/foo", "displayId": "foo", "latestCommit": "d6725486",
                        "repository": {"name": "Repo", "slug": "repo", "scmId": "git", "public": false, "forkable": true, "project": {"id": 1, "key": "PROJ", "name": "Project", "public": false, "type": "NORMAL"}}},
                    "locked": false,
                    "author": {"user": {"name": "test", "emailAddress": "user@email.com", "active": true, "type": "NORMAL"}},
                    "reviewers": [{"user": {"id": 2, "name": "danger", "displayName": "DangerCI", "emailAddress": "foo@bar.com", "active": true, "slug": "danger", "type": "NORMAL"}, "approved": true, "lastReviewedCommit": "8942a1f"}],
                    "participants": [{"user": {"id": 2, "name": "danger", "displayName": "DangerCI", "emailAddress": "user@email.com", "active": true, "slug": "danger", "type": "NORMAL"}}]
                }
            },
            "expected_output": "id=1\ntitle=Pull request title\nstate=OPEN\nopen=true\nclosed=false\nlocked=false\ncreated_at=1518863923273\nauthor.user.name=test\nauthor.user.email=user@email.com\nfrom_ref.id=refs/heads/master\nfrom_ref.display_id=master\nfrom_ref.latest_commit=8942a1f\nfrom_ref.repo.slug=repo\nfrom_ref.repo.project.key=PROJ\nto_ref.id=refs/heads/foo\nto_ref.display_id=foo\nto_ref.latest_commit=d6725486\nparticipants.count=1\nparticipants.0.user.name=danger\nreviewers.count=1\nreviewers.0.user.name=danger\nreviewers.0.approved=true\nreviewers.0.last_reviewed_commit=8942a1f\n"
        }
    ]
}
```

---

### Feature 10: Self-Hosted Server Commit List Parsing

**As a developer**, I want to decode the server commit list, so I can inspect each commit's identity, authorship timestamps, message and parents.

**Expected Behavior / Usage:**

Command `{"view": "bitbucket_commits", "data": [<commit objects>]}`. The adapter emits `count` and, per commit index `i`, the full `i.id`, short `i.display_id`, `i.author.name`, the epoch-millisecond `i.author_timestamp`/`i.committer_timestamp`, the `i.message`, and the parent list as `i.parents.count` plus the first parent's full/short id.

**Test Cases:** `rcb_tests/public_test_cases/feature10_bitbucket_commits.json`

```json
{
    "description": "Parse the server commit list, exposing each commit's full and short SHA, author, author/committer epoch timestamps, message and parent SHAs.",
    "cases": [
        {
            "input": {
                "view": "bitbucket_commits",
                "data": [
                    {"id": "d6725486", "displayId": "d6725486c38",
                     "author": {"id": 2, "name": "danger", "displayName": "DangerCI", "emailAddress": "foo@bar.com", "active": true, "slug": "danger", "type": "NORMAL"},
                     "authorTimestamp": 1519442341000,
                     "committer": {"id": 2, "name": "danger", "displayName": "DangerCI", "emailAddress": "foo@bar.com", "active": true, "slug": "danger", "type": "NORMAL"},
                     "committerTimestamp": 1519442341000, "message": "Modify and remove files",
                     "parents": [{"id": "c62ada7", "displayId": "c62ada76533"}]},
                    {"id": "e7836597", "displayId": "e7836597d49",
                     "author": {"id": 2, "name": "danger", "displayName": "DangerCI", "emailAddress": "foo@bar.com", "active": true, "slug": "danger", "type": "NORMAL"},
                     "authorTimestamp": 1519442342000,
                     "committer": {"id": 2, "name": "danger", "displayName": "DangerCI", "emailAddress": "foo@bar.com", "active": true, "slug": "danger", "type": "NORMAL"},
                     "committerTimestamp": 1519442342000, "message": "Add tests",
                     "parents": [{"id": "d6725486", "displayId": "d6725486c38"}]}
                ]
            },
            "expected_output": "count=2\n0.id=d6725486\n0.display_id=d6725486c38\n0.author.name=danger\n0.author_timestamp=1519442341000\n0.committer_timestamp=1519442341000\n0.message=Modify and remove files\n0.parents.count=1\n0.parents.0.id=c62ada7\n0.parents.0.display_id=c62ada76533\n1.id=e7836597\n1.display_id=e7836597d49\n1.author.name=danger\n1.author_timestamp=1519442342000\n1.committer_timestamp=1519442342000\n1.message=Add tests\n1.parents.count=1\n1.parents.0.id=d6725486\n1.parents.0.display_id=d6725486c38\n"
        }
    ]
}
```

---

### Feature 11: Self-Hosted Server Comment Stream Parsing

**As a developer**, I want to decode the server comment stream, so I can read each entry's action and, where present, the nested comment detail.

**Expected Behavior / Usage:**

Command `{"view": "bitbucket_comments", "data": [<comment objects>]}`. The adapter emits `count` and, per entry index `i`, `i.id`, epoch-millisecond `i.created_at`, `i.user.name`, `i.action`, and `i.comment_action` (`null` when absent). When an entry carries a nested comment detail, the adapter additionally emits `i.comment.id`, `i.comment.version`, `i.comment.text`, `i.comment.author.name`, and `i.comment.properties.repository_id`.

**Test Cases:** `rcb_tests/public_test_cases/feature11_bitbucket_comments.json`

```json
{
    "description": "Parse the server comment activity stream, exposing each entry's id, epoch timestamp, author, action and (when present) the nested comment detail with its repository id.",
    "cases": [
        {
            "input": {
                "view": "bitbucket_comments",
                "data": [
                    {"id": 51, "createdDate": 1518939353000,
                     "user": {"id": 2, "name": "danger", "displayName": "DangerCI", "emailAddress": "foo@bar.com", "active": true, "slug": "danger", "type": "NORMAL"},
                     "action": "OPENED"},
                    {"id": 52, "createdDate": 1518939353345,
                     "user": {"id": 2, "name": "danger", "displayName": "DangerCI", "emailAddress": "foo@bar.com", "active": true, "slug": "danger", "type": "NORMAL"},
                     "action": "COMMENTED", "commentAction": "ADDED",
                     "comment": {"id": 10, "version": 23, "text": "test",
                        "author": {"id": 2, "name": "danger", "displayName": "DangerCI", "emailAddress": "foo@bar.com", "active": true, "slug": "danger", "type": "NORMAL"},
                        "createdDate": 1518939353345, "updatedDate": 1519449132488, "comments": [],
                        "properties": {"repositoryId": 1, "issues": []}, "tasks": []}}
                ]
            },
            "expected_output": "count=2\n0.id=51\n0.created_at=1518939353000\n0.user.name=danger\n0.action=OPENED\n0.comment_action=null\n1.id=52\n1.created_at=1518939353345\n1.user.name=danger\n1.action=COMMENTED\n1.comment_action=ADDED\n1.comment.id=10\n1.comment.version=23\n1.comment.text=test\n1.comment.author.name=danger\n1.comment.properties.repository_id=1\n"
        }
    ]
}
```

---

### Feature 12: Self-Hosted Server Metadata Parsing

**As a developer**, I want to decode the server pull-request metadata, so I can read the repository slug and pull-request id.

**Expected Behavior / Usage:**

Command `{"view": "bitbucket_metadata", "data": <metadata object>}`. The adapter emits `pull_request_id` and `repo_slug`.

**Test Cases:** `rcb_tests/public_test_cases/feature12_bitbucket_metadata.json`

```json
{
    "description": "Parse the server pull-request metadata into repository slug and pull-request id.",
    "cases": [
        {
            "input": {"view": "bitbucket_metadata", "data": {"pullRequestID": "327", "repoSlug": "artsy/emission"}},
            "expected_output": "pull_request_id=327\nrepo_slug=artsy/emission\n"
        }
    ]
}
```

---

### Feature 13: Self-Hosted Server Activity Stream Parsing

**As a developer**, I want to decode the server activity stream, so I can read who performed each lifecycle action (opening, rescoping, commenting, …) and when.

**Expected Behavior / Usage:**

Command `{"view": "bitbucket_activities", "data": [<activity objects>]}`. The adapter emits `count` and, per activity index `i`, `i.id`, epoch-millisecond `i.created_at`, `i.user.name`, `i.action`, and `i.comment_action` (`null` when the activity is not a comment).

**Test Cases:** `rcb_tests/public_test_cases/feature13_bitbucket_activities.json`

```json
{
    "description": "Parse the server activity stream (OPENING/RESCOPING/etc), exposing each activity's id, epoch timestamp, actor account and action.",
    "cases": [
        {
            "input": {
                "view": "bitbucket_activities",
                "data": [
                    {"id": 61, "createdDate": 1519442356495, "user": {"id": 1, "name": "test", "displayName": "test", "emailAddress": "foo@bar.com", "active": true, "slug": "test", "type": "NORMAL"}, "action": "RESCOPED"},
                    {"id": 62, "createdDate": 1519442357000, "user": {"id": 1, "name": "test", "displayName": "test", "emailAddress": "foo@bar.com", "active": true, "slug": "test", "type": "NORMAL"}, "action": "COMMENTED", "commentAction": "CREATED"}
                ]
            },
            "expected_output": "count=2\n0.id=61\n0.created_at=1519442356495\n0.user.name=test\n0.action=RESCOPED\n0.comment_action=null\n1.id=62\n1.created_at=1519442357000\n1.user.name=test\n1.action=COMMENTED\n1.comment_action=CREATED\n"
        }
    ]
}
```

---

### Feature 14: Changed-Files Listing

**As a developer**, I want the decoded git block to expose the modified, created and deleted file paths, so I can drive file-scoped review rules.

**Expected Behavior / Usage:**

Command `{"view": "changed_files", "data": <git object>}`. The adapter emits `modified.count` and each modified path as `modified.<i>`, then likewise for `created.*` and `deleted.*`.

**Test Cases:** `rcb_tests/public_test_cases/feature14_changed_files.json`

```json
{
    "description": "Expose the modified, created and deleted file path lists from the git metadata block.",
    "cases": [
        {
            "input": {
                "view": "changed_files",
                "data": {"modified_files": [".travis.yml", "Podfile", "Kiosk/App/Logger.swift"], "created_files": [".ruby-version"], "deleted_files": ["Obsolete.swift"], "commits": []}
            },
            "expected_output": "modified.count=3\nmodified.0=.travis.yml\nmodified.1=Podfile\nmodified.2=Kiosk/App/Logger.swift\ncreated.count=1\ncreated.0=.ruby-version\ndeleted.count=1\ndeleted.0=Obsolete.swift\n"
        }
    ]
}
```

---

### Feature 15: Changed-Line Aggregation from a Diff

**As a developer**, I want the library to total additions and deletions for the review under evaluation, so I can gate on PR size without writing diff-parsing code.

**Expected Behavior / Usage:**

Command `{"view": "changed_lines", "data": {"diff": <numstat text>, "commit_count": <n>}}`. The diff is the tab-separated numstat output where each non-empty line is `<col1>\t<col2>\t<path>`. The library sums the second column into **additions** and the first column into **deletions**, and reports **lines_of_code** as their sum. A diff range only exists when the review has at least one commit; with zero commits the library short-circuits to all zeros and never consults the diff. This is the externally-observable contract; how the diff text is obtained (a command runner) is an injectable detail.

*15.1 With Commits — aggregate a non-empty numstat diff*

When `commit_count` is at least 1, the adapter parses the numstat and reports the summed additions, deletions and combined total.

**Test Cases:** `rcb_tests/public_test_cases/feature15_1_changed_lines.json`

```json
{
    "description": "Aggregate a unified numstat diff into total additions, deletions and combined lines of code for a pull request that has at least one commit.",
    "cases": [
        {
            "input": {
                "view": "changed_lines",
                "data": {"diff": "0\t1\tfeatures/search/build.gradle\n3\t10\tfeatures/search/RepositoryModule.kt\n2\t4\tfeatures/search/ApiInteractor.kt\n2\t4\tfeatures/search/RecommendedPublishersRepository.kt\n1\t3\tfeatures/search/RecommendedTopicsRepository.kt", "commit_count": 1}
            },
            "expected_output": "additions=22\ndeletions=8\nlines_of_code=30\n"
        }
    ]
}
```

*15.2 No Commits — empty diff range*

When `commit_count` is 0 there is no diff range, so additions, deletions and lines of code are all zero, independent of any diff text supplied.

**Test Cases:** `rcb_tests/public_test_cases/feature15_2_changed_lines_no_commits.json`

```json
{
    "description": "When the pull request has no commits there is no diff range, so additions, deletions and lines of code are all zero regardless of any diff content.",
    "cases": [
        {
            "input": {
                "view": "changed_lines",
                "data": {"diff": "0\t1\tfeatures/search/build.gradle\n3\t10\tfeatures/search/RepositoryModule.kt\n2\t4\tfeatures/search/ApiInteractor.kt\n2\t4\tfeatures/search/RecommendedPublishersRepository.kt\n1\t3\tfeatures/search/RecommendedTopicsRepository.kt", "commit_count": 0}
            },
            "expected_output": "additions=0\ndeletions=0\nlines_of_code=0\n"
        }
    ]
}
```

---

### Feature 16: File-Contents Reader

**As a developer**, I want a one-call helper that returns the textual contents of a file referenced by a changed-file path, so I can inspect file content during a review rule without boilerplate.

**Expected Behavior / Usage:**

Command `{"view": "file_contents", "data": {"content": <text>}}`. The adapter persists the given text to a file, reads it back through the library helper, and prints the contents verbatim (no added trailing newline).

**Test Cases:** `rcb_tests/public_test_cases/feature16_file_contents.json`

```json
{
    "description": "Read the textual contents of a file referenced by path and return it verbatim.",
    "cases": [
        {"input": {"view": "file_contents", "data": {"content": "Test"}}, "expected_output": "Test"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file library implementing the typed per-platform models, shared value types, platform detection, diff aggregation and the file-reading helper described above. Parsing must ignore unknown wire keys, decode timestamps to epoch milliseconds, and model optional attributes as nullable fields. Diff aggregation must depend on an injectable command-runner abstraction.

2. **The Execution/Test Adapter:** A runnable program that reads a single JSON command `{"view": ..., "data": ...}` from stdin, invokes the appropriate core logic, and prints the flat `key=value` contract to stdout exactly as specified per feature above. The adapter is the only component that touches stdin/stdout and the command envelope; it must translate any native parsing failure into a neutral `error=<category>` line rather than leaking host-language runtime identity.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to select the directory (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_github_pull_request.json` under `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_github_pull_request@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other, and each `.txt` contains **only** the raw stdout of the program under test so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- do not render the field for nullable attributes
- sequential ordering of scalar and nested outputs
