# Metamorphic Properties & Invariants

Metamorphic tests assert relationships between the outputs of *related* inputs, without
needing a hand-computed oracle for each. They are ideal for an implementation-blind
review: we cannot easily assert the exact audit for every transcript, but we can assert
that certain transformations of a transcript/config must (or must not) change the result.

Notation: `audit(T, C, A)` = audit result for transcript `T`, config `C`, optional manual
allocation `A`. `==` on results means equal pass/fail, equal failed-requirement set,
equal failed-constraint set, and equal warning set (modulo ordering).

---

## MP-1. Transcript order independence
**Property.** For any permutation `π` of a transcript's course list,
`audit(π(T), C) == audit(T, C)`.

**Rationale.** The greedy allocator is deterministic by *priority*, not by input order
(PRM 514–524). Order sensitivity would make audits irreproducible.

**Test sketch.** Run `order_independence_check` vs `major_core_pass_basic`; assert equal.
Also fuzz: shuffle any passing transcript 20× and assert identical results.

**Likely break.** Greedy "first eligible course wins" without a stable sort → a different
course gets consumed by TC vs TE depending on order.

---

## MP-2. Config load idempotence
**Property.** Loading the same config folder twice, or merging a config with itself,
yields a rule set equal to loading it once: `merge(C, C) == C`.

**Rationale.** PRM 212 — identical same-id objects must be accepted, not duplicated or
errored.

**Test sketch.** `validate-config` on `C` and on `[C, C]`; compare requirement/constraint/
pool/spec ID sets and field values. Confirm no duplicate IDs and no conflict error.

**Likely break.** Merge appends instead of unioning by ID → duplicated requirements,
inflated counts.

---

## MP-3. Config merge commutativity (for non-conflicting overlays)
**Property.** For overlays `C1`, `C2` with no conflicting IDs,
`merge(C1, C2) == merge(C2, C1)`.

**Rationale.** Merge is union-by-ID (PRM 208–216); order of non-conflicting sources must
not matter. (Conflicting overlays are expected to fail either way — see MP-12.)

**Test sketch.** Load base + robotics then base + iot; compare to base + iot then base +
robotics. Resulting rule sets must be equal.

---

## MP-4. Source-ref preservation
**Property.** For every rule/constraint present in the loaded config, the audit output for
any transcript preserves a non-empty `source_ref` (at least `document`; `page` where the
PDF provides one). Allocation and reporting must not strip it.

**Rationale.** PRM 216, 603 — every loaded object retains `source_ref`; failed/important
rules show source references.

**Test sketch.** For each failing case (e.g. `source_ref_preserved_on_failure`), assert the
failed requirement/constraint in JSON output carries the same `source_ref` as in config.
Property form: `for r in audit.failed: r.source_ref == config[r.id].source_ref`.

**Likely break.** Reporting layer reconstructs rules from IDs and loses provenance.

---

## MP-5. UE residual neutrality (does not consume overlap)
**Property.** Let `T` be any transcript and `A` an allocation. Adding a `residual_ue`
allocation for a course that is otherwise only allocated to one Specialisation does NOT
change that Specialisation's overlap usage:
`overlap(audit(T, C, A ∪ {(course → UE, residual_ue)})) == overlap(audit(T, C, A))`.

**Rationale.** PRM 348, 362 — UE residual is not an "other explicit requirement".

**Test sketch.** `ue_residual_does_not_consume_overlap` vs the same transcript without the
UE allocation; overlap budget must be identical (0 used) in both.

**Likely break.** Overlap computed as "course appears in ≥2 allocations" regardless of role.

---

## MP-6. Manual allocation dominance & constraint persistence
**Property (a) dominance.** If a manual allocation `A` is provided, no greedy decision may
contradict it: every allocation in `A` appears verbatim in the final allocation.
**Property (b) persistence.** Constraints are still evaluated under `A`; a manual allocation
cannot make a violated constraint disappear.

**Rationale.** PRM 547 — manual overrides greedy, but constraints still evaluated; invalid
manual allocations produce errors/failed constraints.

**Test sketch.** `manual_override_changes_greedy_choice` (dominance) and
`tc_te_mutual_exclusion_fail` (a manual allocation that *creates* a violation still fails).

**Likely break.** Manual allocation path skips the constraint evaluation stage.

---

## MP-7. Manual allocation validity is a superset gate
**Property.** Any manual allocation that (i) references a non-existent course, (ii) assigns
more units than the attempt has, or (iii) targets an ineligible requirement must yield a
non-pass with a clear error/failed constraint — never a silent pass.

**Rationale.** PRM 547; eligibility ≠ allocation (PRM 109–112).

**Test sketch.** `manual_alloc_unknown_course_error`, `manual_alloc_units_exceed_attempt_error`,
`manual_alloc_ineligible_requirement_fail`.

**Likely break.** Unknown/oversized allocations silently dropped, leaving requirements
"unsatisfied" rather than flagged as invalid input.

---

## MP-8. Alias canonicalisation idempotence & no double-credit
**Property (a).** Replacing any course code in a transcript with its alias (EE3305↔ME3243,
EE3306↔ME3163, EE4002D↔EE4002R for capstone-type, EE4436↔MLE4207, EE4802↔IE4213) does not
change the audit result **for Specialisation/UE eligibility**.
**Property (b).** Presenting *both* sides of an alias pair must not yield double credit;
the second is ignored or flagged.
**Property (c) — asymmetric TE eligibility.** Alias equivalence is NOT symmetric for the TE
rule: the non-EE side (ME3243/ME3163/ME3142/etc.) is never TE-eligible even though its EE twin
may be. So replacing EE3305 with ME3243 must *not* preserve TE-satisfaction (`TE_EXCLUDE_NON_EE`),
only Specialisation/UE satisfaction.

**Rationale.** SPC p.6, p.8, p.11; aliases are equivalences for content, but TE26 Note 2 makes
non-EE courses UE-only for the TE rule.

**Test sketch.** `alias_ee3305_me3243_robotics_basket` (a), `alias_ee3306_me3163_double_count_fail`
(b), and `non_ee_course_not_te_fail` vs `ee3305_te_ay24_pass` (c).

**Likely break.** Alias map applied symmetrically so a non-EE twin "becomes" TE-eligible; or
alias applied for eligibility but not for de-duplication of units.

---

## MP-9. Capstone lock monotonicity
**Property.** Starting from any audit where a Specialisation passes *without* a CC↔spec
capstone double-count, introducing a CC↔spec capstone double-count must only *tighten*
results: remaining overlap budget goes to 0/8 and any additional spec double-count or SEP
mapping that was previously allowed becomes a failure. It can never *loosen* the audit.

**Rationale.** SPC p.1; PRM 366–379.

**Test sketch.** Compare `robotics_capstone_path_pass` (no CC double-count) against
`robotics_capstone_overlap_lock_fail` (adds CC double-count + extra overlap). The latter
must fail with `CAP_LOCK`.

**Likely break.** Capstone lock implemented as a simple `overlap <= 8` numeric check, which
misses the "no *further* double-count even within budget" semantics.

---

## MP-10. SEP cap monotonicity (per Specialisation)
**Property.** Increasing SEP-mapped units for one Specialisation is monotone w.r.t. the
8-unit cap: results are pass for ≤8 and fail for >8, with the transition exactly at 8
(inclusive pass). Adding a SEP mapping never *reduces* failures elsewhere.

**Rationale.** SPC p.1 — up to 8 units of unique SEP courses per Specialisation.

**Test sketch.** `sep_specialisation_max_8_units_pass` (==8) vs
`sep_specialisation_over_8_units_fail` (12). Boundary must be inclusive at 8.

**Likely break.** Off-by-one (`< 8` instead of `<= 8`) or counting non-unique SEP units.

---

## MP-11. SEP cross-Specialisation exclusivity
**Property.** A single SEP course instance approved/used for Specialisation X cannot also
count for Specialisation Y. Mapping it to a second Specialisation always fails, regardless
of unit budgets.

**Rationale.** SPC p.1 — "should not be mapped again to another Specialisation/Minor".

**Test sketch.** `sep_same_course_two_specialisations_fail`.

**Likely break.** Per-spec SEP cap enforced but global uniqueness across specs not tracked.

---

## MP-12. Config conflict determinism
**Property.** Merging two configs that define the same ID with differing fields (no
`override: true`) always fails fast with a clear error, deterministically and regardless of
merge order. With `override: true`, the overriding value wins deterministically.

**Rationale.** PRM 213.

**Test sketch.** `config_merge_conflict_fail` (fails both orders) and `config_merge_identical_ok`
(identical → accept). Add an `override: true` variant: assert the override value wins.

**Likely break.** "Last writer wins" silent resolution, hiding genuine config conflicts.

---

## MP-13. TC/TE mutual-exclusion symmetry
**Property.** For any course `x`, allocating `x` to both TC and TE fails identically whether
TC or TE is listed first: the violation is symmetric (CHK p.3 "and v.v.").

**Test sketch.** `tc_te_mutual_exclusion_fail` plus a variant with the two allocations
swapped; both must produce the same `TC_NOT_TE` failure.

---

## MP-14. Additivity of TC and TE counters
**Property.** Removing a course allocated to TC never reduces the satisfied TE count, and
vice versa — the two requirements draw from disjoint allocated sets (3 TC *in addition to*
2 TE).

**Rationale.** CHK p.1 — TCs are additional to TEs.

**Test sketch.** From a passing TC+TE transcript, drop one TC course; TE status must be
unchanged, only TC drops to 2/3.

**Likely break.** Shared pool allocation lets a course "float" between TC and TE counts.

---

## MP-15. Determinism / reproducibility
**Property.** `audit(T, C)` run repeatedly (same versions) yields byte-identical JSON
output (after normalising any timestamps).

**Rationale.** No runtime LLM, no randomness (PRM 89, 126).

**Test sketch.** Run any `audit ... --format json` twice; diff must be empty (excluding
volatile fields). This underpins `test_cli_snapshots.py`.

---

## MP-16. Overlap ≤ 8 ⇔ distinct ≥ 12 (for complete Specialisations)
**Property.** For a Specialisation allocated to exactly 20 units, `overlap_used ≤ 8` iff
`distinct ≥ 12`. The two reported numbers must always sum consistently
(`distinct = 20 − overlap` for a complete spec).

**Rationale.** SPC p.1. See ambiguity A-07 for partial specs (where the two are checked
independently).

**Test sketch.** For `mqm_ee2027_overlap_budget`: overlap 4 ⇒ distinct 16; assert the
report's two figures are mutually consistent.

---

## MP-17. Adding pure-UE courses never changes requirement/constraint outcomes
**Property.** Appending a course that is only ever allocated to residual UE (e.g. a free
elective) to a transcript leaves all requirement and constraint results unchanged (only the
UE/total unit tally grows).

**Rationale.** UE is residual capacity (PRM 346); it must not interfere with structured
requirements or overlap budgets.

**Test sketch.** Take `major_core_pass_basic`, append `GEX1234` (4u, UE-only); assert
failed-requirement and failed-constraint sets are unchanged.

---

## MP-18. Closed TC pool — no out-of-list satisfaction
**Property.** Adding a course outside the closed TC list (anything other than unused
EE2026/EE2028, EE3033, or the six extended cores) never increases the satisfied-TC count.
Only members of the closed set can move TC from k/3 to (k+1)/3.

**Rationale.** A-01 RESOLVED (TCL, FAQ Q3). The TC pool is a fixed enumerated set.

**Test sketch.** `tc_closed_list_reject_fail` — EE3801 as TC must not count.

**Likely break.** A regex like `EE3\d{3}C?` used as the TC predicate, accepting any EE3xxx.

---

## MP-19. SEP residency/programme monotonicity
**Property.** Converting an NUS attempt to a SEP attempt (same course/units) can only move the
NUS-residency ratio downward; once it crosses below 50% overall (or below 60% of programme),
the corresponding constraint flips to fail and never back to pass while more NUS courses are
removed.

**Rationale.** SEP p.2 — residency ≥50% overall, programme ≥60% at NUS.

**Test sketch.** `sep_residency_below_50_fail`; plus a paired fixture just above 50% that passes.

**Likely break.** Residency not computed at all (SEP treated like NUS), so mass SEP mapping
silently passes.

---

## MP-21. TC substitution is unit-neutral
**Property.** Moving a TC from UE into a vacated Common Curriculum pillar (Systems Thinking /
Creating Narratives / Sustainable Futures), or vice versa, must not change the total graduation
units (stays 160) nor the satisfied-TC count. The 3 inflight TCs reallocate CC pillar / UE
space; they never add 12 units on top of the degree.

**Rationale.** GRB p.4, p.12; FAQ Q4; CTK p.7 — the TCs are read *in lieu of* pillar courses or
using UE, not as an extra block.

**Test sketch.** `cc_tc_count_not_inflated`: assert total units == 160 whether the three TCs are
booked under ST/CN/SF pillars or under UE. Pair with `cc_cde2501_to_sf_with_gess_pass` (third TC
overflows to UE) — both must report the same 160 total.

**Likely break.** A separate 12-unit TC requirement added to CC 60 + UE 40 + Major 60, yielding
172 and over-counting; or TC double-use into a CC pillar mistakenly flagged as a TC<->TE
violation.

---

## MP-22. CDE2501 single-pillar exclusivity
**Property.** Across the Singapore Studies and Sustainable Futures pillars, CDE2501's 4 units are
counted **exactly once**. Exactly one of the two branches holds: (no GESS ⇒ CDE2501→SS, TC→SF)
or (GESS ⇒ GESS→SS, CDE2501→SF). Adding a GESS course flips CDE2501 from SS to SF but never
lets it occupy both.

**Rationale.** FAQ Q5/Q6; GRB p.10; CDE2501 is always compulsory but occupies one pillar.

**Test sketch.** `cc_cde2501_to_gess_no_gess_pass` vs `cc_cde2501_to_sf_with_gess_pass` (branch
flip) and `cc_double_count_cde2501_fail` (both pillars ⇒ fail).

**Likely break.** Treating CDE2501 as satisfying SS and SF simultaneously, fabricating 4 units.

---

## MP-20. Intake-parameterised TE eligibility
**Property.** For the AY2024 cohort config, CG3207/EE3105/EE3305/EE3306/EE3703/EE3801 are
TE-eligible; for an AY2025+ cohort config the same courses are UE-only. Swapping only the
cohort parameter must flip TE-eligibility for exactly these courses and nothing else.

**Rationale.** TE26 Note 3; GRB p.9 (AY2021–AY2024 TE table).

**Test sketch.** `cg3207_te_ay24_pass`, `ee3305_te_ay24_pass` (AY2024 pass); mirror cases under
an AY2025 config should fail. Confirms the rule is data-driven by intake, not hard-coded.

**Likely break.** A single global "UE-only" list that ignores the cohort, wrongly failing AY2024.

---

## Summary table

| id | invariant | primary source | guarded test case |
|----|-----------|----------------|-------------------|
| MP-1 | transcript order independence | PRM 514 | order_independence_check |
| MP-2 | config load idempotence | PRM 212 | config_merge_identical_ok |
| MP-3 | merge commutativity | PRM 208–216 | (new) |
| MP-4 | source_ref preservation | PRM 216, 603 | source_ref_preserved_on_failure |
| MP-5 | UE residual neutrality | PRM 362 | ue_residual_does_not_consume_overlap |
| MP-6 | manual dominance + constraint persistence | PRM 547 | manual_override_changes_greedy_choice |
| MP-7 | manual validity gate | PRM 547 | manual_alloc_* |
| MP-8 | alias idempotence / no double-credit / asym TE | SPC 6,8,11; TE26 Note 2 | alias_*, non_ee_course_not_te_fail |
| MP-9 | capstone lock monotonicity | SPC 1 | robotics_capstone_overlap_lock_fail |
| MP-10 | SEP per-spec cap monotonicity | SPC 1 | sep_specialisation_*_units_* |
| MP-11 | SEP cross-spec exclusivity | SPC 1 | sep_same_course_two_specialisations_fail |
| MP-12 | config conflict determinism | PRM 213 | config_merge_conflict_fail |
| MP-13 | TC/TE mutex symmetry | CHK 3 | tc_te_mutual_exclusion_fail |
| MP-14 | TC/TE additivity | CHK 1 | tc_only_3_courses_pass |
| MP-15 | determinism | PRM 89 | test_cli_snapshots |
| MP-16 | overlap⇔distinct consistency | SPC 1 | mqm_ee2027_overlap_budget |
| MP-17 | UE-only courses inert | PRM 346 | (new) |
| MP-18 | closed TC pool | A-01 (TCL/FAQ) | tc_closed_list_reject_fail |
| MP-19 | SEP residency monotonicity | SEP p.2 | sep_residency_below_50_fail |
| MP-20 | intake-parameterised TE eligibility | TE26 Note 3; GRB p.9 | cg3207_te_ay24_pass, ee3305_te_ay24_pass |
| MP-21 | TC substitution unit-neutral | GRB p.4,12; FAQ Q4; CTK p.7 | cc_tc_count_not_inflated |
| MP-22 | CDE2501 single-pillar exclusivity | FAQ Q5/Q6; GRB p.10 | cc_cde2501_*; cc_double_count_cde2501_fail |
