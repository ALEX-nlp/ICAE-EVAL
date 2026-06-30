## Product Requirement Document

# Team Workspace Management Toolkit - Role, Team, Membership, and HTTP Contract Behavior

## Project Goal

Build a team workspace management library that allows developers to create and manage teams, roles, memberships, current-team selection, and team-aware account deletion without hand-writing repetitive authorization, validation, and relationship-management code.

---

## Background & Problem

Without this library/tool, developers are forced to manually maintain role permission registries, owner/member relationships, team validation rules, membership cleanup, and HTTP endpoints for switching teams or changing member roles. This leads to duplicated rules, inconsistent authorization responses, stale memberships, and fragile controller code.

With this library/tool, applications get a cohesive team-management layer whose externally visible behavior is defined by deterministic state outputs, normalized validation and authorization errors, and HTTP-observable status and redirect signals.

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

### Feature 1: Role and Permission Registry

**As a developer**, I want to register role definitions and aggregate their permissions, so I can validate that role setup exposes a deterministic permission contract.

**Expected Behavior / Usage:**

The input is a role registration command containing one or more role records, each with a stable role key, display name, and permission list. The output reports whether any permissions are present, the complete de-duplicated permission list sorted lexically as a comma-separated value, and the number of roles registered.

**Test Cases:** `rcb_tests/public_test_cases/feature1_role_permission_registry.json`

```json
{
    "description": "Registering multiple team roles exposes whether any permissions exist and returns the de-duplicated permission set in sorted order.",
    "cases": [
        {
            "input": {
                "scenario": "register_team_roles",
                "roles": [
                    {
                        "key": "admin",
                        "name": "Administrator",
                        "permissions": [
                            "read",
                            "create"
                        ]
                    },
                    {
                        "key": "editor",
                        "name": "Editor",
                        "permissions": [
                            "read",
                            "update",
                            "delete"
                        ]
                    }
                ]
            },
            "expected_output": "[a specific boolean value string — ask the PM for the exact format]\npermissions=create,delete,read,update\nrole_count=2\n"
        }
    ]
}
```

---

### Feature 2: Team Creation

**As a developer**, I want to create a team for an owner, so I can start collaborative workspaces with validated names.

**Expected Behavior / Usage:**

The input is either a team creation request containing owner account data and a team name, or the same request with a blank team name. On success, the output confirms creation, echoes the persisted team name and owner email, indicates that the new team is not personal, and reports the owner’s owned-team count. When the team name is blank, the output is a normalized validation error with the failing field and message.

**Test Cases:** `rcb_tests/public_test_cases/feature2_team_creation.json`

```json
{
    "description": "Creating a team for an owner either persists a non-personal team with the submitted name or returns a normalized validation error when the name is blank.",
    "cases": [
        {
            "input": {
                "scenario": "create_team",
                "owner": {
                    "name": "Primary Owner",
                    "email": "owner@example.com",
                    "password": "secret"
                },
                "team": {
                    "name": "Product Team"
                }
            },
            "expected_output": "team_created=yes\nteam_name=Product Team\nowner_email=owner@example.com\npersonal_team=no\nowned_team_count=1\n"
        },
        {
            "input": {
                "scenario": "create_team_validation",
                "owner": {
                    "name": "Primary Owner",
                    "email": "owner@example.com",
                    "password": "secret"
                },
                "team": {
                    "name": ""
                }
            },
            "expected_output": "error=validation_failed\nfield=name\nmessage=The name field is required.\n"
        }
    ]
}
```

---

### Feature 3: Team Name Updates

**As a developer**, I want to rename an existing team, so I can keep workspace names accurate while preserving validation behavior.

**Expected Behavior / Usage:**

The input identifies an owner, an existing team name, and a requested new team name. On success, the output confirms the update, reports the persisted team name, and reports the owner email. When the requested name is blank, the output is a normalized validation error for the name field.

**Test Cases:** `rcb_tests/public_test_cases/feature3_team_name_updates.json`

```json
{
    "description": "Updating a team name as its owner either persists the new name or returns a normalized validation error when the new name is blank.",
    "cases": [
        {
            "input": {
                "scenario": "update_team_name",
                "owner": {
                    "name": "Primary Owner",
                    "email": "owner@example.com",
                    "password": "secret"
                },
                "initial_team_name": "Product Team",
                "new_team_name": "Product Team Updated"
            },
            "expected_output": "updated=yes\nteam_name=Product Team Updated\nowner_email=owner@example.com\n"
        },
        {
            "input": {
                "scenario": "update_team_name_validation",
                "owner": {
                    "name": "Primary Owner",
                    "email": "owner@example.com",
                    "password": "secret"
                },
                "initial_team_name": "Product Team",
                "new_team_name": ""
            },
            "expected_output": "error=validation_failed\nfield=name\nmessage=The name field is required.\n"
        }
    ]
}
```

---

### Feature 4: Team Member Addition

**As a developer**, I want to add registered users to a team with a role, so I can grant team access without duplicating members or accepting unknown users.

**Expected Behavior / Usage:**

The input contains role definitions, an owner, a team, and a member email or member account to add. On success, the output reports the number of attached non-owner members, the attached member email, the assigned role, and permission checks derived from that role. If the email does not belong to a registered user, or if the user is already on the team, the output is a normalized validation error.

**Test Cases:** `rcb_tests/public_test_cases/feature4_team_member_addition.json`

```json
{
    "description": "Adding a user to a team by email attaches the member with the selected role, while missing users and duplicate members return normalized validation errors.",
    "cases": [
        {
            "input": {
                "scenario": "add_team_member",
                "roles": [
                    {
                        "key": "admin",
                        "name": "Administrator",
                        "permissions": [
                            "foo"
                        ]
                    }
                ],
                "owner": {
                    "name": "Primary Owner",
                    "email": "owner@example.com",
                    "password": "secret"
                },
                "team_name": "Product Team",
                "member": {
                    "name": "Invited Member",
                    "email": "member@example.com",
                    "password": "secret"
                },
                "role": "admin",
                "check_permissions": [
                    "foo",
                    "bar"
                ]
            },
            "expected_output": "member_count=1\nmember_email=member@example.com\nrole=admin\ncan_foo=yes\ncan_bar=no\n"
        },
        {
            "input": {
                "scenario": "add_team_member_missing",
                "roles": [
                    {
                        "key": "admin",
                        "name": "Administrator",
                        "permissions": [
                            "foo"
                        ]
                    }
                ],
                "owner": {
                    "name": "Primary Owner",
                    "email": "owner@example.com",
                    "password": "secret"
                },
                "team_name": "Product Team",
                "email": "missing@example.com",
                "role": "admin"
            },
            "expected_output": "error=validation_failed\nfield=email\nmessage=We were unable to find a registered user with this email address.\n"
        },
        {
            "input": {
                "scenario": "add_team_member_duplicate",
                "roles": [
                    {
                        "key": "admin",
                        "name": "Administrator",
                        "permissions": [
                            "foo"
                        ]
                    }
                ],
                "owner": {
                    "name": "Primary Owner",
                    "email": "owner@example.com",
                    "password": "secret"
                },
                "team_name": "Product Team",
                "member": {
                    "name": "Invited Member",
                    "email": "member@example.com",
                    "password": "secret"
                },
                "role": "admin"
            },
            "expected_output": "error=validation_failed\nfield=email\nmessage=This user already belongs to the team.\n"
        }
    ]
}
```

---

### Feature 5: Team Membership and Permission Resolution

**As a developer**, I want to query ownership, membership, current-team, role, and token-scope access, so I can make authorization decisions from persisted team relationships.

**Expected Behavior / Usage:**

The input sets up an owner, a team, an optional personal-team marker, a member role, and permission checks, or sets up role permissions together with token permission scopes. The output reports observable relationship facts such as whether users belong to or own the team, owned/all team counts, whether personal/current team references match, and whether requested permissions are granted. Token-scoped checks must require both the team role permission and the active token permission.

**Test Cases:** `rcb_tests/public_test_cases/feature5_team_membership_permissions.json`

```json
{
    "description": "Team ownership, membership, personal-team selection, role permissions, and token scopes combine to determine visible team access results.",
    "cases": [
        {
            "input": {
                "scenario": "team_relationships",
                "owner": {
                    "name": "Primary Owner",
                    "email": "owner@example.com",
                    "password": "secret"
                },
                "team_name": "Product Team",
                "member": {
                    "name": "Invited Member",
                    "email": "member@example.com",
                    "password": "secret"
                },
                "role": {
                    "key": "editor",
                    "name": "Editor",
                    "permissions": [
                        "foo"
                    ]
                },
                "permission_checks": [
                    "foo",
                    "bar"
                ]
            },
            "expected_output": "owner_belongs_to_team=yes\nowner_owns_team=yes\nowned_team_count=1\nall_team_count=1\npersonal_team_id_matches=yes\ncurrent_team_id_matches=yes\noutsider_belongs_to_team=no\noutsider_owns_team=no\nmember_belongs_to_team=yes\nmember_owns_team=no\nmember_can_foo=yes\nmember_can_bar=no\n"
        },
        {
            "input": {
                "scenario": "token_limited_team_permission",
                "owner": {
                    "name": "Primary Owner",
                    "email": "owner@example.com",
                    "password": "secret"
                },
                "team_name": "Product Team",
                "role": {
                    "key": "admin",
                    "name": "Administrator",
                    "permissions": [
                        "foo"
                    ]
                },
                "blocked_member": {
                    "name": "Blocked Member",
                    "email": "blocked@example.com",
                    "password": "secret"
                },
                "allowed_member": {
                    "name": "Allowed Member",
                    "email": "allowed@example.com",
                    "password": "secret"
                },
                "blocked_token_permissions": [
                    "bar"
                ],
                "allowed_token_permissions": [
                    "foo"
                ],
                "permission": "foo"
            },
            "expected_output": "blocked_member_can_foo=no\nallowed_member_can_foo=yes\n"
        }
    ]
}
```

---

### Feature 6: Team Member Removal

**As a developer**, I want to remove members from teams, so I can keep memberships accurate and reject invalid removal attempts.

**Expected Behavior / Usage:**

The input describes an owner, team, and member removal operation. On success, the output reports the member count before and after removal and whether a removal event signal was dispatched. If the owner tries to remove themselves from a team they created, the output is a normalized validation error. If an unauthorized member tries to remove another member, the output is a normalized authorization error.

**Test Cases:** `rcb_tests/public_test_cases/feature6_team_member_removal.json`

```json
{
    "description": "Removing team members updates team membership and emits a removal signal; attempts by an owner to remove themselves or by an unauthorized member to remove another member return normalized errors.",
    "cases": [
        {
            "input": {
                "scenario": "remove_team_member",
                "owner": {
                    "name": "Primary Owner",
                    "email": "owner@example.com",
                    "password": "secret"
                },
                "team_name": "Product Team",
                "member": {
                    "name": "Invited Member",
                    "email": "member@example.com",
                    "password": "secret"
                }
            },
            "expected_output": "member_count_before=1\nmember_count_after=0\nremoved_event_dispatched=yes\n"
        },
        {
            "input": {
                "scenario": "remove_team_member_self_owner",
                "owner": {
                    "name": "Primary Owner",
                    "email": "owner@example.com",
                    "password": "secret"
                },
                "team_name": "Product Team"
            },
            "expected_output": "error=validation_failed\nfield=team\nmessage=You may not leave a team that you created.\n"
        },
        {
            "input": {
                "scenario": "remove_team_member_unauthorized",
                "owner": {
                    "name": "Primary Owner",
                    "email": "owner@example.com",
                    "password": "secret"
                },
                "team_name": "Product Team",
                "actor": {
                    "name": "Limited Actor",
                    "email": "actor@example.com",
                    "password": "secret"
                },
                "target": {
                    "name": "Target Member",
                    "email": "target@example.com",
                    "password": "secret"
                }
            },
            "expected_output": "error=authorization_denied\n"
        }
    ]
}
```

---

### Feature 7: Team Deletion and Deletion Validation

**As a developer**, I want to delete teams only when deletion rules allow it, so I can protect personal teams and owner-only deletion boundaries.

**Expected Behavior / Usage:**

The input either requests direct deletion of a team, or validation of whether an actor may delete a team with a personal-team flag. Direct deletion reports whether the team record is gone and the remaining team count. Validation by the owner of a non-personal team reports that deletion is allowed and echoes the team name. Personal teams fail with a normalized validation error, while non-owner actors fail with a normalized authorization error.

**Test Cases:** `rcb_tests/public_test_cases/feature7_team_deletion.json`

```json
{
    "description": "Team deletion removes the team record; deletion validation permits an owner to delete a non-personal team and rejects personal teams or non-owner actors.",
    "cases": [
        {
            "input": {
                "scenario": "delete_team",
                "owner": {
                    "name": "Primary Owner",
                    "email": "owner@example.com",
                    "password": "secret"
                },
                "team_name": "Product Team"
            },
            "expected_output": "team_deleted=yes\nremaining_team_count=0\n"
        },
        {
            "input": {
                "scenario": "validate_team_deletion",
                "owner": {
                    "name": "Primary Owner",
                    "email": "owner@example.com",
                    "password": "secret"
                },
                "team_name": "Product Team",
                "personal_team": false,
                "actor": "owner"
            },
            "expected_output": "deletion_allowed=yes\nteam_name=Product Team\n"
        },
        {
            "input": {
                "scenario": "validate_team_deletion",
                "owner": {
                    "name": "Primary Owner",
                    "email": "owner@example.com",
                    "password": "secret"
                },
                "team_name": "Product Team",
                "personal_team": true,
                "actor": "owner"
            },
            "expected_output": "error=validation_failed\nfield=team\nmessage=You may not delete your personal team.\n"
        },
        {
            "input": {
                "scenario": "validate_team_deletion",
                "owner": {
                    "name": "Primary Owner",
                    "email": "owner@example.com",
                    "password": "secret"
                },
                "team_name": "Product Team",
                "personal_team": false,
                "actor": "non_owner",
                "non_owner": {
                    "name": "Outside User",
                    "email": "outsider@example.com",
                    "password": "secret"
                }
            },
            "expected_output": "error=authorization_denied\n"
        }
    ]
}
```

---

### Feature 8: Current Team HTTP Switching

**As a developer**, I want to switch an authenticated user’s current team through the HTTP layer, so I can verify routing, redirection, and authorization behavior rather than only state mutation.

**Expected Behavior / Usage:**

The input is an authenticated HTTP-style request to switch the current team, with either a team owner or an outsider as actor. When the actor belongs to the team, the output includes HTTP status 303, the home redirect URL, and state checks proving the selected current team changed. When the actor does not belong to the team, the output includes HTTP status 403 and no redirect URL.

**Test Cases:** `rcb_tests/public_test_cases/feature8_current_team_http_switching.json`

```json
{
    "description": "An authenticated HTTP request can switch to a team the actor belongs to and redirects home; switching to a team the actor does not belong to returns an authorization status.",
    "cases": [
        {
            "input": {
                "scenario": "switch_current_team_http",
                "actor": "owner",
                "owner": {
                    "name": "Primary Owner",
                    "email": "owner@example.com",
                    "password": "secret"
                },
                "team_name": "Product Team"
            },
            "expected_output": "http_status=303\nredirect_url=http://localhost/home\ncurrent_team_id_matches=yes\nis_current_team=yes\n"
        },
        {
            "input": {
                "scenario": "switch_current_team_http",
                "actor": "outsider",
                "owner": {
                    "name": "Primary Owner",
                    "email": "owner@example.com",
                    "password": "secret"
                },
                "outsider": {
                    "name": "Outside User",
                    "email": "outsider@example.com",
                    "password": "secret"
                },
                "team_name": "Product Team"
            },
            "expected_output": "http_status=403\nredirect_url=null\n"
        }
    ]
}
```

---

### Feature 9: Team Member Role HTTP Updates

**As a developer**, I want to change a member role through the HTTP layer, so I can verify routed authorization and permission effects for role changes.

**Expected Behavior / Usage:**

The input is an authenticated HTTP-style request to update a team member’s role, with either the owner or the member as actor. An authorized owner receives HTTP status 303, a redirect URL, the persisted new role, and permission checks for the new role. An unauthorized member receives HTTP status 403 and no redirect URL.

**Test Cases:** `rcb_tests/public_test_cases/feature9_team_member_role_http_updates.json`

```json
{
    "description": "An authorized HTTP request can change a member role and updates permissions; an unauthorized member updating their own role receives an authorization status.",
    "cases": [
        {
            "input": {
                "scenario": "update_member_role_http",
                "actor": "owner",
                "owner": {
                    "name": "Primary Owner",
                    "email": "owner@example.com",
                    "password": "secret"
                },
                "team_name": "Product Team",
                "member": {
                    "name": "Invited Member",
                    "email": "member@example.com",
                    "password": "secret"
                },
                "initial_role": "admin",
                "new_role": "editor",
                "check_permissions": [
                    "baz",
                    "qux"
                ]
            },
            "expected_output": "http_status=303\nredirect_url=http://localhost\nrole=editor\ncan_baz=yes\ncan_qux=yes\n"
        },
        {
            "input": {
                "scenario": "update_member_role_http",
                "actor": "member",
                "owner": {
                    "name": "Primary Owner",
                    "email": "owner@example.com",
                    "password": "secret"
                },
                "team_name": "Product Team",
                "member": {
                    "name": "Invited Member",
                    "email": "member@example.com",
                    "password": "secret"
                },
                "initial_role": "admin",
                "new_role": "admin",
                "check_permissions": [
                    "foo"
                ]
            },
            "expected_output": "http_status=403\nredirect_url=null\n"
        }
    ]
}
```

---

### Feature 10: User Deletion With Team Cleanup

**As a developer**, I want to delete a user and clean up owned teams and memberships, so I can avoid orphaned team ownership and stale membership rows.

**Expected Behavior / Usage:**

The input creates one user who owns a team and also belongs to a second user’s team, then requests deletion of the first user. The output reports team and membership counts before deletion, confirms the user is deleted, confirms the owned team is removed, and confirms the membership association is cleared while the other user’s team remains.

**Test Cases:** `rcb_tests/public_test_cases/feature10_user_deletion_with_teams.json`

```json
{
    "description": "Deleting a user who owns teams and also belongs to another team removes the user, removes their owned teams, and clears their team membership associations without deleting teams owned by others.",
    "cases": [
        {
            "input": {
                "scenario": "delete_user_with_teams",
                "first_owner": {
                    "name": "First Owner",
                    "email": "first-owner@example.com",
                    "password": "secret"
                },
                "first_team_name": "Owned Team",
                "second_owner": {
                    "name": "Second Owner",
                    "email": "second-owner@example.com",
                    "password": "secret"
                },
                "second_team_name": "External Team"
            },
            "expected_output": "teams_before=2\nmemberships_before=1\nuser_deleted=yes\nteams_after=1\nmemberships_after=0\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_role_permission_registry.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_role_permission_registry@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.