# OpenSSF Best Practices Badge -- Criteria Reference

All criterion slugs, N/A eligibility, and automation URL field names for all three badge levels.
Source: https://www.bestpractices.dev/en/criteria

Each entry lists:
- `slug`: the form field ID used in automation URLs (`{slug}_status=Met`)
- `na`: whether N/A is a valid selection
- `section`: logical grouping within the level

The automation URL for a level only includes criteria **first introduced at that level**.
Passing criteria are NOT repeated in silver or gold URL params -- the form carries them over.

---

## Passing Level (`/passing/edit?`)

### Basics

| slug | N/A |
|------|-----|
| description_good | no |
| interact | no |
| contribution | no |
| contribution_requirements | no |
| floss_license | no |
| floss_license_osi | no |
| license_location | no |
| documentation_basics | no |
| documentation_interface | yes |
| sites_https | no |
| discussion | no |
| english | no |
| maintained | no |

### Change Control

| slug | N/A |
|------|-----|
| repo_public | no |
| repo_track | no |
| repo_interim | no |
| repo_distributed | no |
| version_unique | no |
| version_semver | no |
| version_tags | no |
| release_notes | no |
| release_notes_vulns | yes |

### Reporting

| slug | N/A |
|------|-----|
| report_process | no |
| report_tracker | yes |
| report_responses | no |
| enhancement_responses | no |
| report_archive | no |
| vulnerability_report_process | no |
| vulnerability_report_private | no |
| vulnerability_report_response | no |

### Quality

| slug | N/A |
|------|-----|
| build | yes |
| build_common_tools | yes |
| build_floss_tools | yes |
| test | no |
| test_invocation | yes |
| test_most | yes |
| test_continuous_integration | yes |
| test_policy | no |
| tests_are_added | no |
| tests_documented_added | yes |
| warnings | yes |
| warnings_fixed | yes |
| warnings_strict | yes |

### Security

| slug | N/A |
|------|-----|
| know_secure_design | no |
| know_common_errors | no |
| crypto_published | yes |
| crypto_call | yes |
| crypto_floss | yes |
| crypto_keylength | yes |
| crypto_working | yes |
| crypto_weaknesses | yes |
| crypto_pfs | yes |
| crypto_password_storage | yes |
| crypto_random | yes |
| crypto_used_network | yes |
| crypto_tls12 | yes |
| delivery_mitm | no |
| delivery_unsigned | no |
| vulnerabilities_fixed_60_days | no |
| vulnerabilities_critical_fixed | yes |
| no_leaked_credentials | no |
| static_analysis | no |
| static_analysis_common_vulnerabilities | yes |
| static_analysis_fixed | no |
| static_analysis_often | no |

### Analysis

| slug | N/A |
|------|-----|
| dynamic_analysis | yes |
| dynamic_analysis_unsafe | yes |
| dynamic_analysis_enable_assertions | yes |
| dynamic_analysis_fixed | yes |

---

## Silver Level (`/silver/edit?`)

Only criteria **first introduced at silver**. Do not repeat passing slugs.

### Basics

| slug | N/A |
|------|-----|
| achieve_passing | no |
| dco | no |
| governance | no |
| code_of_conduct | no |
| roles_responsibilities | no |
| access_continuity | no |
| bus_factor | no |
| documentation_roadmap | no |
| documentation_architecture | yes |
| documentation_security | yes |
| documentation_quick_start | yes |
| documentation_current | yes |
| documentation_achievements | no |
| accessibility_best_practices | yes |
| internationalization | yes |
| sites_password_security | yes |

### Change Control

| slug | N/A |
|------|-----|
| maintenance_or_update | yes |

### Reporting

| slug | N/A |
|------|-----|
| vulnerability_report_credit | yes |
| vulnerability_response_process | no |

### Quality

| slug | N/A |
|------|-----|
| coding_standards | yes |
| coding_standards_enforced | yes |
| build_standard_variables | yes |
| build_preserve_debug | yes |
| build_non_recursive | yes |
| build_repeatable | yes |
| installation_common | yes |
| installation_standard_variables | yes |
| installation_development_quick | yes |
| external_dependencies | yes |
| dependency_monitoring | yes |
| updateable_reused_components | yes |
| interfaces_current | yes |
| automated_integration_testing | no |
| regression_tests_added50 | yes |
| test_statement_coverage80 | yes |
| test_policy_mandated | yes |

### Security

| slug | N/A |
|------|-----|
| implement_secure_design | yes |
| crypto_algorithm_agility | yes |
| crypto_credential_agility | yes |
| crypto_certificate_verification | yes |
| crypto_verification_private | yes |
| signed_releases | yes |
| version_tags_signed | yes |
| input_validation | yes |
| hardening | yes |
| assurance_case | no |

---

## Gold Level (`/gold/edit?`)

Only criteria **first introduced at gold**. Do not repeat passing or silver slugs.

### Prerequisites

| slug | N/A |
|------|-----|
| achieve_silver | no |
| contributors_unassociated | no |

### Basics

| slug | N/A |
|------|-----|
| copyright_per_file | no |
| license_per_file | no |

### Change Control

| slug | N/A |
|------|-----|
| small_tasks | no |
| require_2FA | no |
| secure_2FA | no |

### Quality

Note: `test_invocation` and `test_continuous_integration` are intentionally re-listed here. At passing level both allow N/A (`yes`); at gold level N/A is removed (`no`), making them mandatory. Include in the gold URL only when they are Met.

| slug | N/A |
|------|-----|
| code_review_standards | yes |
| two_person_review | no |
| build_reproducible | yes |
| test_invocation | no |
| test_continuous_integration | no |
| test_statement_coverage90 | yes |
| test_branch_coverage80 | yes |

### Security

| slug | N/A |
|------|-----|
| hardened_site | no |
| security_review | no |

---

## URL Construction Rules

1. A criterion param looks like: `{slug}_status=Met` or `{slug}_status=N%2FA`
2. Include justification only when it meaningfully aids a reviewer -- justification text is URL-encoded
3. Each level's URL contains only slugs from that level's table above
4. Omit criteria marked HUMAN or Unmet from the URL (they must be set manually in the form)
5. Only include criteria where CONFIDENCE is High or Medium
6. Default: pre-fills blank fields only. Append `&overrides=*` to force-override existing values

## Form Visual Indicators (after loading URL)

| Color | Meaning |
|-------|---------|
| Yellow + robot icon | Proposal fills a previously blank field (normal) |
| Orange + warning icon | Forced override of existing value (`overrides=*` mode) |
| Blue + not-equal icon | Divergent proposal not applied (no matching override pattern) |

## Resource Constraints

This agent operates under Claude Code's default session limits. Callers should set
an explicit `timeout` in the Agent tool call for any invocation expected to run
longer than 5 minutes. No unbounded loops or recursive agent calls.
