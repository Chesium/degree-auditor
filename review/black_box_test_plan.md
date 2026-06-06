# Black-Box Test Plan — NUS EE AY24 JC Degree Auditor CLI

Goal: validate the CLI's externally observable behaviour **without reading the source code**.
We treat the package as a binary that consumes config folders, transcript YAML, and optional
manual-allocation YAML, and emits text/JSON/YAML reports plus exit codes.

All assertions below are derived from the resource PDFs and `prompt.txt`. The 17 prior
ambiguities are now **resolved** (`ambiguous_human_review.md` + new resources), so most
`[ambiguous]` tags are removed; the few items still marked `[default]` adopted a recommended
default without an explicit "solved" stamp (A-02, A-04, A-10, A-15) and may be flipped to
`xfail` only if the implementation documents a different choice.

---

## 1. Interfaces under test (the black-box contract)

From PRM 549–586, the CLI exposes:

| command | observable outputs |
|---------|--------------------|
| `validate-config --config <dir>` | exit code; error text on bad/conflicting config |
| `list-requirements --config <dir>` | enumerated requirements w/ IDs + source refs |
| `list-specialisations --config <dir>` | enumerated specialisations |
| `expand-eligibility --config <dir> --transcript <f>` | per-course eligible requirements/pools |
| `plan-allocation --config <dir> --transcript <f> --out <f>` | written allocation YAML |
| `audit --config <dir> --transcript <f> [--allocation <f>] [--format text\|json\|yaml]` | report + exit code |

The three observable channels we assert on:
1. **Exit code** — `audit` returns `0` iff `result.pass == true`; `2` for a non-passing audit;
   `1` for invalid input/config (parse error, merge conflict, invalid manual allocation). See
   the Contract chapter in `prompt.txt`.
2. **Structured output** (`--format json`) — the machine-readable contract (schema below).
3. **Human report** (`--format text`, Rich) — checked via snapshot + substring assertions.

> **Alignment note (read first).** This plan no longer "discovers" whatever IDs the code emits.
> The authoritative interface is the **Contract & Assumptions** chapter appended to `prompt.txt`,
> and the registries/enums in `edge_cases.yaml › meta`. The maintainer aligns the CLI to that
> contract; the harness asserts against it verbatim. Any divergence is a code defect, not a
> mapping exercise.

---

## 2. Test harness design (no source access)

### 2.1 Driver
- Invoke the console script `degree-auditor …` (or `python -m degree_auditor …`) via
  `subprocess.run`, capturing `stdout`, `stderr`, `returncode`.
- Always request `--format json` for assertions; capture `text` separately for snapshots.

### 2.2 Fixture materialisation
For each case in `edge_cases.yaml`, apply `meta.defaults` to every `CourseAttempt`, then write:
- `tmp/<id>/transcript.yaml`  ← `transcript` (+ `student_flags`)
- `tmp/<id>/manual_allocation.yaml`  ← `manual_allocation` (only if present)
- `tmp/<id>/overlay/*.yaml`  ← `config_overlay` fragments (merge tests only)

### 2.3 Required JSON output schema (the oracle)
`audit --format json` MUST emit at least:

```json
{
  "pass": false,
  "cohort": "nus_ee_ay24_jc",
  "total_units": 160,
  "requirements": [
    {"id": "TC_MIN_3", "status": "FAIL", "units_done": 8, "units_required": 12,
     "satisfied_by": ["EE3408C","EE3331C"], "source_ref": {"document":"CHK","page":1}}
  ],
  "failed_requirements": ["TC_MIN_3"],
  "constraints": [
    {"id": "TC_NOT_TE", "status": "FAIL", "message": "EE3331C used for both TC and TE",
     "source_ref": {"document":"CHK","page":3}}
  ],
  "failed_constraints": ["TC_NOT_TE"],
  "warnings": ["EE3331C allocated to both TC and TE; mutual exclusion violated"],
  "specialisations": [
    {"id":"RBT","status":"PARTIAL","overlap_used":8,"overlap_budget":8,
     "distinct_units":12,"sep_mapped_units":0,"capstone_lock":true}
  ],
  "allocations": [
    {"course_code":"EE3331C","requirement_id":"TC_MIN_3","units":4,
     "allocation_role":"primary","manual":true}
  ]
}
```

`failed_requirements` / `failed_constraints` are flat ID arrays derived from the detailed
objects; the harness asserts on those arrays. IDs MUST be drawn from `rule_inventory.md`
(reported `requirement_id`) and the `constraint_ids` registry.

### 2.4 Assertion contract (exact, from `edge_cases.yaml › meta.assertion_semantics`)
For each case:
- `result.pass == expected_pass`
- `set(expected_failed_requirements) ⊆ set(result.failed_requirements)`
- `set(expected_failed_constraints) ⊆ set(result.failed_constraints)`
- `∀ w ∈ expected_warnings: ∃ m ∈ result.warnings with w ⊆ m` (substring)
- `assert_focus`, `source_refs`, `why_this_matters` are **documentation only** (never asserted).

Subset (not equality) lets minimal fixtures omit incidental failures. A case with empty
`expected_failed_*` asserts only `expected_pass` + warnings.

### 2.5 Snapshotting
For `text` format, store a normalised snapshot (strip ANSI, trailing whitespace, volatile
timestamps) per case; diff on re-run (supports MP-15 determinism).

### 2.6 Pre-flight contract check (run before any layer)
A guard test asserts the CLI's emitted vocabulary matches the contract, failing loudly on drift:
- every `requirement_id` in `meta.slot_to_requirement` values appears in `list-requirements`;
- every id in `meta.constraint_ids_used` is a known constraint (`validate-config --explain` or
  a `list-constraints` command);
- the JSON keys in §2.3 are present on a trivial audit.

---

## 3. Test layers

### Layer A — Config validity (no transcript)
- A1. `validate-config` on the shipped `configs/nus_ee_ay24_jc` → exit 0, no errors.
- A2. `list-requirements` includes the structural requirements from `rule_inventory.md`
  (DEG_TOTAL_160, CC_CDE_60, UE_40, MAJOR_60, TC_MIN_3, TE_MIN_2). Each line carries a
  `source_ref` (assert `document`/`page` present).
- A3. `list-specialisations` lists exactly the 7 modelled specs (AE, Indust4, IoT, Rbt, SPT,
  SET, MQM).
- A4. **Merge conflict:** point `--config` at base + an overlay that redefines an ID with a
  different value (fixture from `config_merge_conflict_fail`) → non-zero exit, error text
  naming the conflicting ID and mentioning `override`.
- A5. **Idempotent merge:** pass the same `--config` twice → identical `list-requirements`
  output as passing once (MP-2).
- A6. **Source-ref completeness:** every requirement/constraint emitted by `list-*` has a
  non-empty `source_ref.document` (PRM 216).

### Layer B — Eligibility expansion
- B1. `expand-eligibility` for a transcript containing EE3331C must list EE3331C as eligible
  for **all** of: TC, TE, Industry 4.0 core, SPT elective (PRM 112 names this exact example).
- B2. EE2027 must be eligible for both Major core and MQM core.
- B3. EE3033 must be eligible for TC but **not** TE (and not as an Extended Core).
- B4. EE3031 must be eligible for UE but **not** TE.
- B5. Eligibility must be order-independent and not yet make allocation decisions
  (eligibility ≠ allocation, PRM 109).
- B6. **Closed TC pool:** a course outside the closed set (e.g. EE3801) must NOT be TC-eligible
  (A-01). Only {unused EE2026/EE2028, EE3033, EE3131C, EE3408C, EE3331C, EE3431C, EE3731C,
  EE3104C} are TC-eligible.
- B7. **Non-EE not TE:** ME3243/ME3163/ME3142/ME4245/RB4301 and CSxxxxDE are eligible for
  Specialisation/UE but **not** the EE TE rule (TE26 Note 2).
- B8. **Intake carve-out:** for the AY2024 config, CG3207/EE3105/EE3305/EE3306/EE3703/EE3801
  ARE TE-eligible (TE26 Note 3 / GRB p.9).

### Layer C — Greedy audit (no manual allocation)
Run `audit --format json` on transcript-only fixtures and assert pass/fail + IDs:
- C1. `major_core_pass_basic` → pass.
- C2. `tc_only_2_courses_fail` → fail `TC_MIN_3`.
- C3. `robotics_coursework_only_pass` → Robotics satisfied via Path 2.
- C4. `robotics_capstone_untagged_fail` → Robotics fails (tag missing).
- C5. `spt_idp_path_inactive_without_flag_fail` → SPT core fails without IDP flag.
- C6. `order_independence_check` == `major_core_pass_basic` (MP-1).

### Layer D — Manual-allocation audit
Run `audit --allocation <f>`:
- D1. `tc_te_mutual_exclusion_fail` → fail `TC_NOT_TE`.
- D2. `ae_core_tc_te_conflict` → fail `TC_NOT_TE` even though overlap budget is fine.
- D3. `ee3031_not_te_fail`, `ee3033_not_te_fail` → respective exclusion failures.
- D4. `manual_override_changes_greedy_choice` → pass, with a warning that greedy was overridden.
- D5. `manual_alloc_unknown_course_error`, `manual_alloc_units_exceed_attempt_error`,
  `manual_alloc_ineligible_requirement_fail` → non-pass + clear error (MP-7).
- D6. `robotics_capstone_overlap_lock_fail` → fail `CAP_LOCK`.
- D7. `mqm_ee2027_overlap_budget` → pass, report shows "MQM overlap 4/8".
- D8. `mqm_overlap_exceeds_budget_fail` → fail overlap and/or capstone lock.

### Layer E — SEP rules
- E1. `sep_te_one_nus_one_sep_pass` → pass.
- E2. `sep_te_all_sep_fail` → fail (no NUS TE / >1 SEP TE).
- E3. `sep_specialisation_max_8_units_pass` (==8) → pass; boundary inclusive (MP-10).
- E4. `sep_specialisation_over_8_units_fail` (12) → fail.
- E5. `sep_same_course_two_specialisations_fail` → fail cross-spec reuse (MP-11).
- E6. `spt_capstone_sep_forbidden_fail` → fail (capstone ⇒ no SEP for that spec).

### Layer F — Aliases & topic tags
- F1. `alias_ee3305_me3243_robotics_basket` → pass for the Robotics basket (ME3243 resolved to
  EE3305 for Specialisation eligibility **only**).
- F2. `alias_ee3306_me3163_double_count_fail` → fail (no double-credit).
- F3. `robotics_capstone_path_pass` → satellite/robotics topic tag honoured.
- F4. `iot_electives_units_equivalent_pass` → 8-unit single project satisfies electives (A-08).
- F5. `non_ee_course_not_te_fail` → ME3243 as TE fails (`TE_EXCLUDE_NON_EE`); asymmetric alias.
- F6. `ee3305_te_ay24_pass` vs F5 → EE3305 passes as TE for AY2024 but its non-EE twin does not.

### Layer H — New corrections (closed TC list, SEP→TC, CDE4301, residency, emerging tech)
- H1. `tc_closed_list_reject_fail` → EE3801 cannot satisfy TC.
- H2. `cg3207_te_ay24_pass` → CG3207 valid TE for AY2024.
- H3. `sep_mapped_to_tc_pass` → SEP course mapped to TC accepted (AY23/AY24).
- H4. `cde4301_spec_idp_conflict_fail` → CDE4301 cannot fulfil a Spec when used for IDP 2nd Major.
- H5. `sep_residency_below_50_fail` → residency <50% fails.
- H6. `emerging_tech_not_set_elective_fail` → EE4032 is NOT a SET elective (A-09 ignore entirely).
- H7. **Level-1000 cap** (`level1000_cap_exceeded_warn`) and internship-combo are now enforced
  (A-13), not advisory; S/U is out of scope.
- H8. **Internship model:** `internship_ia_full_pass`, `internship_via_plus_vip_pass` (combo=10),
  `internship_short_combo_fail` (8<10), `internship_urop_cap_fail` (UROP>4 to major),
  `internship_overflow_to_ue_pass` (>10 spills to UE), `internship_poly_apc_pass` (EG3611P),
  `internship_eg2605_alias_pass` (EG2605→CDE2605), `internship_ceg_only_course_fail` (CP* CEG-only).

### Layer G — Output-format & reporting contract
- G1. `--format json` is valid JSON and contains: overall status, per-section status (Major,
  TC, TE, each selected Spec), overlap budget per spec, capstone lock status, manual-allocation
  warnings, missing courses/units, failed constraints, and source refs (PRM 588–604).
- G2. `--format text` (Rich) snapshot matches stored snapshot; contains the section headers
  from the PRM 607 example (e.g. "Technical Courses:", "Overlap: X / 8 units used").
- G3. `--format yaml` (if implemented) round-trips to the same structure as JSON.
- G4. Same input → identical JSON across two runs (MP-15, determinism).
- G5. `plan-allocation --out` produces a YAML file that, when fed back via `--allocation`
  with no edits, yields the SAME audit result as the greedy run (round-trip stability).

---

## 4. Mapping of priority areas → black-box tests

| priority area (from task) | black-box tests |
|---------------------------|-----------------|
| TC/TE mutual exclusion | D1, D2, MP-13 |
| EE2026/EE2028 choice | ee2026_ee2028_choice_tc_success, ee2026_both_to_major_and_tc_fail |
| EE3031 / EE3033 special | C2-adjacent, D3, ee3033 effective-date cases |
| Specialisation overlap budget | D7, D8, ae_core_overlap_with_tc_within_budget |
| UE residual not consuming overlap | ue_residual_does_not_consume_overlap (MP-5) |
| Capstone double-count lock | D6, capstone_double_count_two_specs_fail (MP-9) |
| SEP mapping limits | E1–E4 |
| SEP uniqueness across specs | E5 (MP-11) |
| Topic-tagged capstones | F3, robotics_capstone_untagged_fail |
| Aliases EE3305/ME3243, EE3306/ME3163 | F1, F2 (MP-8) |
| Manual overriding greedy | D4 (MP-6) |
| Invalid manual allocations | D5 (MP-7) |
| Config merge conflicts | A4, A5, config_merge_* (MP-12) |
| Source reference preservation | A6, source_ref_preserved_on_failure (MP-4) |
| Closed TC pool (A-01) | B6, H1 (MP-18) |
| Non-EE not TE / asym alias (TE26 Note 2) | B7, F5, F6 (MP-8c) |
| Intake TE carve-outs (TE26 Note 3) | B8, H2, ee3305_te_ay24_pass (MP-20) |
| SEP→TC mapping (AY23/24) | H3 |
| CDE4301 vs IDP 2nd Major (A-16) | H4 |
| SEP residency 50%/60% | H5 (MP-19) |
| Emerging Tech ignored (A-09) | H6 |
| Level-1000 cap + internship enforced (A-13) | H7 |
| Internship model (combos, UROP cap, UE overflow, poly APC) | H8 (MP-23) |

---

## 5. Negative / robustness inputs (fuzz the black box)

- N1. Empty transcript (`courses: []`) → audit runs, reports everything unsatisfied, exit
  non-zero; must not crash.
- N2. Malformed transcript YAML → clear parse error, non-zero exit, no traceback dump.
- N3. Unknown course code with no alias → treated as ineligible everywhere, surfaced as
  unallocated; no crash.
- N4. Duplicate course attempts (same code twice) → de-duplicated or flagged; must not
  double-count units.
- N5. Course with `units: 0` or negative → rejected with a validation error.
- N6. `--allocation` referencing requirement IDs absent from config → clear error.
- N7. Non-4-unit courses (e.g. MA1511 = 2u) → unit-based requirements count units, not
  courses, where applicable (probes ambiguity A-02).
- N8. `--format` with an unsupported value → usage error, non-zero exit.
- N9. Missing `--config` or `--transcript` → CLI usage/help error.

---

## 6. Cross-checks that need no oracle (metamorphic in the CLI)

These run two CLI invocations and compare outputs (see `metamorphic_properties.md`):
- X1. Shuffle transcript order → identical audit (MP-1).
- X2. Duplicate `--config` → identical config listing (MP-2).
- X3. Swap order of two non-conflicting `--config` overlays → identical audit (MP-3).
- X4. Append a UE-only course → unchanged requirement/constraint outcomes (MP-17).
- X5. Replace a course with its alias → unchanged audit (MP-8a).
- X6. plan-allocation → audit round-trip equals greedy audit (G5).

---

## 7. Open questions to confirm with maintainer (do not assume)

Curriculum ambiguities are resolved (see `ambiguous_rules.md` resolution table). Remaining
open items are about the **CLI contract**, not the rules:

1. **Exit-code semantics.** Does `audit` return non-zero when the degree does not pass, or
   always 0 with status in the payload? Tests in §3 assume non-zero on fail; mark `[confirm]`.
2. **Scope of a single audit.** Confirm the JSON exposes per-section status so section-scoped
   assertions are possible on minimal fixtures (it should per PRM 588–604).
3. **Specialisation selection.** Is the audited specialisation chosen automatically, declared
   in the transcript, or passed as a CLI flag?
4. **Cohort parameterisation.** Confirm the AY2024 carve-outs (CG3207/EE3105/EE3305/EE3306/
   EE3703/EE3801 TE-eligible; AY2025+ UE-only) are driven by a cohort key in config, so MP-20
   can be tested by swapping configs.
5. **ID stability.** Confirm the public requirement/constraint IDs so the adapter in §2 is
   stable across versions (e.g. `TE_EXCLUDE_NON_EE`, `TC_SEP_MAPPABLE`, `CDE4301_NO_SPEC_IF_IDP`,
   `SEP_RESIDENCY_50`).
6. **Residency data.** Confirm transcripts carry enough `source` info (NUS vs SEP) for the
   50%/60% residency computation, and whether residency is a hard fail or a warning.

Items still on a recommended default (not explicitly "solved"): A-02 (count+units), A-04
(EE3033 term gate), A-10 (ME3142 review), A-15 (MQM host MSE). Keep these as `[default]` tests.

---

## 8. Suggested pytest organisation (black-box only)

```text
tests_blackbox/
  conftest.py              # builds tmp fixtures from review/edge_cases.yaml; cli() helper
  test_config_validity.py  # Layer A
  test_eligibility_cli.py  # Layer B
  test_greedy_audit.py     # Layer C
  test_manual_alloc.py     # Layer D
  test_sep_rules.py        # Layer E
  test_alias_topic.py      # Layer F
  test_corrections.py      # Layer H (closed TC list, SEP->TC, CDE4301, residency, emerging tech)
  test_output_formats.py   # Layer G + snapshots
  test_robustness.py       # Section 5 negatives
  test_metamorphic.py      # Section 6 cross-checks
```

Each `edge_cases.yaml` entry becomes a parametrised case; the harness asserts that
`expected_failed_requirements` / `expected_failed_constraints` are subsets of the emitted
sets and that each `expected_warnings` substring is present. `[default]`-tagged cases (A-02,
A-04, A-10, A-15) are collected separately so they can be flipped to `xfail` if the
implementation documents a different choice, without masking real regressions.
