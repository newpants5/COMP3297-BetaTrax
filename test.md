# BetaTrax Test Suite — 40 Tests

All tests live in `Betrax/tests.py` and use PostgreSQL with a dedicated tenant schema (`test`).

---

## AuthenticationEndpointTests (2 tests)

| #   | Test                             | Endpoint            | What it checks                                     |
| --- | -------------------------------- | ------------------- | -------------------------------------------------- |
| 1   | `test_login_returns_auth_token`  | `POST /api/login/`  | Valid credentials → HTTP 200 + `token` in response |
| 2   | `test_logout_deletes_auth_token` | `POST /api/logout/` | Valid token → HTTP 200, token deleted from DB      |

---

## ProductEndpointTests (2 tests)

| #   | Test                                            | Endpoint              | What it checks                                               |
| --- | ----------------------------------------------- | --------------------- | ------------------------------------------------------------ |
| 3   | `test_product_list_returns_registered_products` | `GET /api/products/`  | Returns all products in the DB (correct count and ID)        |
| 4   | `test_product_create_allows_product_owner`      | `POST /api/products/` | Product Owner can create a product → HTTP 201, product saved |

---

## DefectEndpointTests (14 tests)

Covers the full defect lifecycle state machine.

| #   | Test                                                       | Endpoint                                    | What it checks                                                        |
| --- | ---------------------------------------------------------- | ------------------------------------------- | --------------------------------------------------------------------- |
| 5   | `test_defect_list_returns_filtered_results`                | `GET /api/defects/?status=&product=`        | Query-string filters return only matching defects                     |
| 6   | `test_defect_create_allows_beta_tester`                    | `POST /api/defects/`                        | Beta Tester can submit a defect; initial status is `NEW`              |
| 7   | `test_defect_detail_returns_single_report`                 | `GET /api/defects/<id>/`                    | Returns correct defect with `product_name` field                      |
| 8   | `test_accept_defect_updates_status_and_fields`             | `PATCH /api/defects/<id>/accept/`           | Status → `OPEN`; severity and priority saved                          |
| 9   | `test_assign_defect_sets_responsible_developer`            | `PATCH /api/defects/<id>/assign/`           | Product Owner assigns a developer; status → `ASSIGNED`                |
| 10  | `test_developer_can_self_assign_open_defect`               | `PATCH /api/defects/<id>/assign/`           | Developer self-assigns an `OPEN` defect → status `ASSIGNED`           |
| 11  | `test_developer_cannot_assign_defect_to_another_developer` | `PATCH /api/defects/<id>/assign/`           | Developer attempting to assign to another developer → `403 Forbidden` |
| 12  | `test_fix_defect_marks_assigned_defect_as_fixed`           | `PATCH /api/defects/<id>/fix/`              | Developer marks assigned defect → status `FIXED`                      |
| 13  | `test_resolve_defect_marks_fixed_defect_as_resolved`       | `PATCH /api/defects/<id>/resolve/`          | Product Owner marks fixed defect → status `RESOLVED`                  |
| 14  | `test_reject_defect_marks_new_defect_as_rejected`          | `PATCH /api/defects/<id>/reject/`           | Product Owner rejects a new defect → status `REJECTED`                |
| 15  | `test_reopen_defect_marks_fixed_defect_as_reopened`        | `PATCH /api/defects/<id>/reopen/`           | Product Owner reopens a fixed defect → status `REOPENED`              |
| 16  | `test_reassign_defect_updates_assigned_developer`          | `PATCH /api/defects/<id>/reassign/`         | Swaps the assigned developer; status stays `ASSIGNED`                 |
| 17  | `test_mark_duplicate_links_duplicate_to_parent`            | `PATCH /api/defects/<id>/mark-duplicate/`   | Status → `DUPLICATE`; `duplicate_of` FK set to parent                 |
| 18  | `test_cannot_reproduce_marks_assigned_defect`              | `PATCH /api/defects/<id>/cannot-reproduce/` | Developer marks assigned defect → status `CANNOT_REPRODUCE`           |

---

## CommentEndpointTests (6 tests)

| #   | Test                                                    | Endpoint                           | What it checks                                                  |
| --- | ------------------------------------------------------- | ---------------------------------- | --------------------------------------------------------------- |
| 19  | `test_comment_list_returns_comments_for_defect`         | `GET /api/defects/<id>/comments/`  | Returns all comments for a defect in insertion order            |
| 20  | `test_comment_create_allows_product_owner_or_developer` | `POST /api/defects/<id>/comments/` | Developer can add a comment → HTTP 201, saved to correct defect |
| 21  | `test_comment_detail_returns_single_comment`            | `GET /api/comments/<id>/`          | Returns the correct single comment                              |
| 22  | `test_comment_put_replaces_comment_text`                | `PUT /api/comments/<id>/`          | Full replace of comment content → text updated                  |
| 23  | `test_comment_patch_updates_comment_text`               | `PATCH /api/comments/<id>/`        | Partial update of text field only → text updated                |
| 24  | `test_comment_delete_removes_comment`                   | `DELETE /api/comments/<id>/`       | HTTP 204 returned; comment no longer exists in DB               |

---

## NotificationAndValidationTests (5 tests)

| #   | Test                                                               | What it checks                                                                                  |
| --- | ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| 25  | `test_send_status_notification_sends_email_when_address_exists`    | `send_status_notification()` sends one email to `tester_email`; subject contains the new status |
| 26  | `test_send_status_notification_skips_when_no_email`                | No email sent when `tester_email` is blank                                                      |
| 27  | `test_defect_clean_requires_duplicate_parent_for_duplicate_status` | `full_clean()` raises `ValidationError` if status is `DUPLICATE` but `duplicate_of` is `None`   |
| 28  | `test_defect_clean_rejects_self_duplicate`                         | `full_clean()` raises `ValidationError` if `duplicate_of` points to the defect itself           |
| 29  | `test_assign_serializer_rejects_unknown_developer`                 | `DefectAssignSerializer` is invalid when `developer_id` does not exist in DB                    |

---

## PermissionTests (5 tests)

| #   | Test                                                        | Permission class            | What it checks                                             |
| --- | ----------------------------------------------------------- | --------------------------- | ---------------------------------------------------------- |
| 30  | `test_is_product_owner_recognizes_product_owner_group`      | `IsProductOwner`            | Grants access to users in the "Product Owner" Django group |
| 31  | `test_is_developer_recognizes_developer_group`              | `IsDeveloper`               | Grants access to users in the "Developer" group            |
| 32  | `test_is_beta_tester_recognizes_beta_tester_group`          | `IsBetaTester`              | Grants access to users in the "Beta Tester" group          |
| 33  | `test_is_product_owner_or_developer_rejects_anonymous_user` | `IsProductOwnerOrDeveloper` | Denies unauthenticated (`AnonymousUser`) requests          |
| 34  | `test_is_product_owner_or_developer_accepts_developer`      | `IsProductOwnerOrDeveloper` | Grants access to users in the "Developer" group            |

---

## DeveloperEffectivenessClassificationTests (6 tests)

Tests every branch of `Developer.effectiveness_summary()`.  
Classification is based on the ratio `reopened_count / fixed_count`.

| #   | Test                                                  | Condition                                 | Expected classification / What it checks                              |
| --- | ----------------------------------------------------- | ----------------------------------------- | --------------------------------------------------------------------- |
| 35  | `test_insufficient_data_when_fixed_count_below_20`    | `fixed_count < 20`                        | `INSUFFICIENT_DATA`, `ratio = None`                                   |
| 36  | `test_good_when_ratio_below_1_over_32`                | ratio `< 1/32` (e.g. 0/20)                | `GOOD`                                                                |
| 37  | `test_fair_when_ratio_between_1_over_32_and_1_over_8` | `1/32 ≤ ratio < 1/8` (e.g. 1/32)          | `FAIR`                                                                |
| 38  | `test_poor_when_ratio_at_or_above_1_over_8`           | ratio `≥ 1/8` (e.g. 3/24)                 | `POOR`                                                                |
| 39  | `test_developer_list_returns_all_developers`          | `GET /api/developers/`                    | HTTP 200; returns all developer records with correct IDs              |
| 40  | `test_effectiveness_endpoint_returns_classification`  | `GET /api/developers/<id>/effectiveness/` | HTTP 200; response contains `classification` and `fixed_count` fields |

---

## Defect Lifecycle Summary

```
NEW ──accept──► OPEN ──assign──► ASSIGNED ──fix──► FIXED ──resolve──► RESOLVED ──reopen──► REOPENED
 │                                  │                                                           │
reject                       cannot-reproduce                                                 assign
 │                                  │                                                           │
REJECTED                  CANNOT_REPRODUCE                                                  ASSIGNED
```

Any defect can also be marked `DUPLICATE` (linked to a parent defect).
