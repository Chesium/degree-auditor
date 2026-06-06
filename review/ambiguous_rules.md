# Ambiguous Rules — require human confirmation

Each entry lists ≥2 plausible interpretations, the implementation consequence of each, and a **recommended conservative default** for the prototype. "Conservative" here means: do not silently let a student pass; prefer warnings / explicit human-review flags over silent assumptions (PRM 91, 809).

Source shorthand:
- **CHK** = `L_AY24JC_Checklist_Revised_3TC_4June2025.pdf`
- **SPC** = `ECE_Specialisations_AY2025_7July2025.pdf`
- **PRM** = `prompt.txt`
- **TCL** = `Electrical-Engineering-List-of-Additional-Technical-Courses-v3.pdf` (closed TC list)
- **FAQ** = `FAQ for In-Flight students_For AY24 Non Poly_17Jun2025.pdf`
- **GRB** = `EE2_Revised Grad Req Briefing_20June25.pdf`
- **CTK** = `EE2_Curriculum_Talk_2025_13Aug2025.pdf`
- **TE25/TE26** = `EE_TechElectives_AY2026_iii.pdf` (AY2026/27 master list; course attributes + intake carve-outs)
- **SEP** = `ECE_SEP_Outgoing_AY2627_30Jan26.pdf`

---

## Resolution status (updated after human review + new resources)

All 17 items were addressed in `ambiguous_human_review.md`. Status legend:
**RESOLVED** = decision final + evidence; **DEFAULT-ADOPTED** = recommended default accepted but
not explicitly marked "solved" (keep a light watch).

| id | status | decision |
|----|--------|----------|
| A-01 | RESOLVED | Interpretation 1 — **closed TC list** (not "any EE3xxxC"). Evidence: TCL, FAQ Q3. |
| A-02 | DEFAULT-ADOPTED | Evaluate both count and units; require both. |
| A-03 | RESOLVED | Single 2-TE requirement located in the Major Programme. |
| A-04 | DEFAULT-ADOPTED | Gate EE3033 TC-eligibility on term ≥ AY2025/26 S2; warn if term unknown. |
| A-05 | RESOLVED | Full 8u budget consumed; no further double-count. Evidence: Robotics page + GRB p.18. |
| A-06 | RESOLVED | Capstone-for-spec ⇒ zero SEP for that spec. Evidence: SPC p.1. |
| A-07 | RESOLVED | Enforce overlap ≤ 8 AND distinct ≥ 12 independently. |
| A-08 | RESOLVED | Require both (≥N courses AND ≥units) so the 20-unit total holds. |
| A-09 | RESOLVED | Interpretation 2 — **ignore "Emerging Technologies" (EE4032/EE4205) entirely**; not SET/MQM electives. Evidence: TE26 (EE4032=GEN, EE4205=CN, no spec tag). |
| A-10 | DEFAULT-ADOPTED | EE3331C canonical for IND4 core; ME3142 only with review (and non-EE ⇒ TE-ineligible). |
| A-11 | RESOLVED | Auto-evaluate both Robotics paths; report satisfied one. |
| A-12 | RESOLVED | UE residual is "free"; never the overlap-creating requirement. |
| A-13 | RESOLVED | **Enforce** the 60-unit level-1000 cap and internship-combination check; **ignore S/U** for now. |
| A-14 | RESOLVED | Cap SEP→Major-TE at 1; extra SEP TEs allowed only as UE; ≥1 NUS TE required. |
| A-15 | DEFAULT-ADOPTED | MQM follows 20/8/12; EE2027 overlap = 4u; tag host MSE. |
| A-16 | RESOLVED | CDE4301/CDE4301A cannot fulfil a Specialisation if also used for the IDP 2nd Major. Evidence: CDE iDP 2nd-major page. |

New rules/corrections surfaced by the resources (now folded into `rule_inventory.md`): closed TC
list; 3 TC = 12 units; SEP courses may map to TC for AY23/AY24 intakes; **non-EE courses
(MExxxx/CSxxxxDE/RBxxxx) cannot fulfil the EE TE rule** (UE only); for AY2024 intake CG3207,
EE3105, EE3305, EE3306, EE3703, EE3801 **are** valid TEs (the UE-only carve-out is AY2025
intake & after); SEP residency (≥50% overall) and programme (≥60%) minimums; several course
title updates. See `rule_inventory.md` §3, §4, §5, §9, §14.

---

## A-01. What counts as a "Technical Course" beyond the named list?

**Text.** CHK p.1 lists the TC pool as EE2026/EE2028 (unused), EE3033 (wef Sem2 AY25/26), and Extended Core {EE3131C, EE3408C, EE3331C, EE3431C, EE3731C, EE3104C}. But it also says "EE3xxxC courses can count towards fulfilling the TC requirement," and the TC/TE column block lists `EE3xxxC / EE3xxx / EE4xxx`.

- **Interpretation 1 (closed list):** TC pool is exactly the enumerated courses + the unused EE2026/EE2028 + EE3033. Consequence: a course like EE3801 (an EE3xxx) cannot be a TC; over-restrictive but safe.
- **Interpretation 2 (open EE3xxxC):** Any `EE3xxxC` course counts as TC (the "EE3xxxC courses can count" sentence). Consequence: courses such as EE3331C/EE3408C plus any future EE3xxxC are TC-eligible; broader.
- **Interpretation 3 (full TC column = TC pool):** The whole `EE3xxxC/EE3xxx/EE4xxx` block applies to TC too, making TC and TE pools nearly identical and distinguished only by allocation.

**Recommended default:** Interpretation 2 — TC pool = enumerated extended-core list ∪ {unused EE2026/EE2028} ∪ {EE3033 after date} ∪ {any EE3xxxC}. Mark EE3xxx/EE4xxx-as-TC as `needs_human_review`. Emit a warning when a TC is satisfied by a course outside the enumerated list.

> **RESOLVED → Interpretation 1 (closed list).** The dedicated `List of Additional Technical
> Courses` (TCL) enumerates exactly: (EE2026 or EE2028, when not used for Major), EE3033, and
> the six extended cores EE3131C, EE3408C, EE3331C, EE3431C, EE3731C, EE3104C. FAQ Q3 confirms
> "for the remaining 2 TCs, you may choose 2 from the list (EE3033, EE3131C, EE3408C, EE3331C,
> EE3431C, EE3731C, EE3104C)." There is **no** open "any EE3xxxC" rule — the only EE3xxxC
> courses that exist as extended cores are those six. The TC pool is a closed set; a course
> outside it must NOT satisfy TC. (3 TC = 12 units, FAQ.)

---

## A-02. Are TC and TE measured in courses or units?

**Text.** "Read 3 T.C", "Two EE Technical Electives … 8 units". TC count is stated as a count ("3"); TE is stated both as a count (2) and as units (8).

- **Interpretation 1 (count-based):** TC = ≥3 courses, TE = ≥2 courses regardless of unit size.
- **Interpretation 2 (unit-based):** TE = 8 units (so two 4-unit courses, but a single 8-unit course or three 2-unit courses could differ).

**Consequence.** Most EE courses are 4u, so count vs units rarely differ — but a SEP-mapped course or a non-4u course (e.g., a 2u or 5u mapping) would diverge. Count-based could pass a student short on units; unit-based could fail a student with the right number of courses.

**Recommended default:** Evaluate **both** and require both to pass (TC: ≥3 courses; TE: ≥2 courses AND ≥8 units). Warn if the two metrics disagree.

---

## A-03. Does the Major-internal "2 TE" requirement equal the "EE TE rule (2 TEs)"?

**Text.** CHK p.2 places "Two EE Technical Electives (8 units)" inside the 40-unit Major Programme. CHK p.1 refers to "the EE Technical Elective rule (of 2 T.Es)". PRM treats TE as both a Major requirement (PRM 302) and a standalone rule (PRM 327).

- **Interpretation 1 (same 2 TEs):** There is exactly one 2-TE requirement, located in the Major Programme. The 3 TCs are separate and additional.
- **Interpretation 2 (distinct):** The Major Programme TE slots and the "EE TE rule" are different counters that happen to both equal 2.

**Consequence.** Interpretation 2 would (incorrectly) demand 4 TEs. Interpretation 1 is almost certainly intended.

**Recommended default:** Interpretation 1 — a single 2-TE requirement. The "3 TC in addition to 2 TE" wording (CHK p.1) confirms only TC is additive, not a second TE block.

---

## A-04. EE3033 effective-date semantics for `planned`/`in_progress` attempts

**Text.** "EE3033 … (wef sem2 AY25/26)" is TC-eligible only from Semester 2 AY2025/26.

- **Interpretation 1 (term on the attempt):** EE3033 counts as TC only if `term >= AY2025-2026 S2`. An attempt with an earlier term is rejected for TC.
- **Interpretation 2 (cohort-wide):** Since this is the AY24 intake, EE3033 is simply always TC-eligible (the date already passed for them).
- **Interpretation 3 (planned ignores date):** `planned` attempts with no firm term are assumed compliant.

**Consequence.** Interpretation 1 can fail a transcript where EE3033 was taken in AY2025-26 S1. Interpretation 2 ignores the explicit date and may over-credit.

**Recommended default:** Interpretation 1 with a warning when `term` is missing/unparseable (treat unknown-term EE3033 as TC-eligible **with** a `needs_human_review` warning rather than silent pass/fail).

---

## A-05. Capstone lock — scope of "no further technical elective may be double-counted"

**Text.** "if a student double counts Capstone project … to fulfil one Specialisation and Common Curriculum, then he/she cannot double count any technical elective for that Specialisation and another programme." (SPC p.1)

- **Interpretation 1 (full budget consumed):** The 8-unit capstone consumes the entire 8-unit overlap budget; therefore zero additional double-counts allowed. (Matches PRM 368.)
- **Interpretation 2 (literal: TEs only):** Only *technical electives* are blocked from further double-counting; a non-TE overlap (e.g., another core) might still be allowed within remaining budget — but the budget is already 8/8, so this is moot unless overlap math differs.
- **Interpretation 3 (per "another programme"):** The block applies only to double-counting with "another programme" (2nd major/minor), not to within-spec accounting.

**Consequence.** Interpretation 1 is strictest and matches the prompt. Interpretation 2/3 could allow an extra overlap that the registrar would reject.

**Recommended default:** Interpretation 1 — capstone double-count → overlap budget = 8/8 used, hard-block any further double-count for that Specialisation, regardless of role.

> **RESOLVED → Interpretation 1.** Confirmed by the ECE Robotics specialisation page (quoted in
> `ambiguous_human_review.md`): "if a student double counts Capstone project, e.g., EE4002D/R
> (8 units), to fulfil one Specialisation and Common Curriculum, then he/she cannot double count
> any technical elective for that Specialisation and another programme." Also GRB p.18.

---

## A-06. SPT capstone "compulsory" vs the overlap lock — is SPT ever passable with SEP or extra overlap?

**Text.** SPT standard path requires a satellite EE4002D/R (compulsory). The lock says using that capstone as a CC↔SPT double-count forbids further TE double-counting and forbids SEP mapping to SPT.

- **Interpretation 1 (capstone always double-counted):** Because the capstone is also CC's Integrated Project, SPT's capstone is *inevitably* a CC↔SPT double-count, so SPT *always* triggers the lock (0 SEP, no further overlap).
- **Interpretation 2 (capstone allocated to SPT only):** A student could allocate the capstone as SPT-primary and use a *different* course for CC's integrated project — but CC only has one capstone slot, so this is usually impossible.

**Consequence.** Interpretation 1 means any SPT audit must show "SEP mapped: 0/0 because capstone used" and a fully-consumed overlap budget. Interpretation 2 risks under-applying the lock.

**Recommended default:** Interpretation 1 for the standard path; if a transcript somehow has two distinct capstone-eligible 8u projects, flag as `needs_human_review`.

---

## A-07. "Distinct 12 units" when a Specialisation requirement is itself satisfiable below 20 units of courses

**Text.** "at least 12 Units of the Specialisation must be distinct and not overlapping" while total is 20 and overlap ≤8.

- **Interpretation 1 (arithmetic):** distinct = 20 − overlap ≥ 12, i.e., overlap ≤ 8. The two numbers are the same constraint expressed two ways.
- **Interpretation 2 (independent floor):** The student must actually present ≥12 units of courses that are *uniquely* used for this Specialisation, separate from the overlap cap — relevant if a Specialisation is only partially completed.

**Consequence.** For a *complete* 20-unit Specialisation they coincide. For a *partial* Specialisation (e.g., 16 units done, 8 overlapping), Interpretation 2 fails it (only 8 distinct), Interpretation 1 may report "within budget."

**Recommended default:** Enforce both `overlap ≤ 8` AND `distinct ≥ 12` as independent checks on the *allocated* units, so partial specs are caught. Report each separately.

---

## A-08. IoT "≥2 electives OR 8 units equivalent" + 12-unit core — does total reach 20?

**Text.** IoT core = CS3237 + EE4211 + EE4409 (12u). Electives "≥2 or 8 units". 12 + 8 = 20. But "≥2 electives" of 4u = 8u; what if electives are non-4u?

- **Interpretation 1 (units dominate):** Need ≥8 elective units regardless of count → guarantees 20 total.
- **Interpretation 2 (count dominates):** Any 2 electives suffice even if <8 units, allowing a sub-20-unit Specialisation.

**Consequence.** Interpretation 2 could pass IoT at <20 units, contradicting `SPEC_TOTAL_20`.

**Recommended default:** Require BOTH (≥2 electives AND ≥8 elective units) so the 20-unit total is met; warn if a 4u-only assumption is violated. Same pattern applies to MQM ("≥3 courses or 12 units").

---

## A-09. "Emerging Technologies" EE4032 / EE4205 — which Specialisation?

**Text.** SPC p.10–11: after the SET synopsis and before the "Specialisation 7 / MQM" heading, two courses appear under "Emerging Technologies": EE4032 Blockchain Engineering, EE4205 Quantum Communication and Cryptography.

- **Interpretation 1 (SET electives):** They sit within the SET block, so they are additional SET electives.
- **Interpretation 2 (MQM / standalone):** They precede the MQM heading and may belong to neither, or be a general note.

**Consequence.** Wrongly attaching them to SET (or MQM) changes which courses satisfy that Specialisation's elective requirement.

**Recommended default:** Do **not** auto-attach them to any Specialisation. Model them in a separate `emerging_tech` pool flagged `needs_human_review`, and do not count them toward SET/MQM completion unless confirmed. Emit a warning if a transcript relies on them.

> **RESOLVED → Interpretation 2 (ignore entirely).** Human review: "Ignore the 'Emerging
> Technologies' at all." The AY2026/27 master list (TE26) corroborates this: EE4032 is tagged
> area **GEN** with no specialisation tag, and EE4205 is tagged **CN** with no specialisation
> tag — neither is a SET or MQM elective. Do not model an `emerging_tech` pool; these courses
> are ordinary EE4xxx TEs/UE and must not count toward any Specialisation's electives.

---

## A-10. ME3142 / "for ME students" alias for EE3331C in Industry 4.0

**Text.** IND4 core: "EE3331C Feedback Control Systems … or ME3142 Feedback Control Systems (for ME students)".

- **Interpretation 1 (EE students must use EE3331C):** ME3142 is only valid for ME-major students; an EE student cannot satisfy IND4 core with ME3142.
- **Interpretation 2 (full alias):** ME3142 ≡ EE3331C for everyone.

**Consequence.** For an EE-only auditor, Interpretation 1 means ME3142 should not satisfy IND4 core. Interpretation 2 risks crediting a course an EE student typically cannot take.

**Recommended default:** Treat EE3331C as the canonical IND4 core; accept ME3142 only with a `needs_human_review` warning ("ME-only alias"). Note this differs from EE3305/ME3243 and EE3306/ME3163, which are presented as plain equivalences (no "for ME students" caveat).

> **DEFAULT-ADOPTED + reinforced by TE26 Note 2.** The AY2026/27 master list states: "Non-EE
> courses (MExxxx, CSxxxxDE, RBxxxx) count towards UE requirements only. They cannot be used to
> fulfil EE Tech elective rules." Consequence: ME3142/ME3243/ME3163/ME4245/RB4301 and the CS
> specialisation courses may satisfy **Specialisation electives / UE**, but they can **never**
> satisfy the EE TE rule. When a student presents the ME-coded twin (e.g. ME3243) it resolves to
> the EE course for *Specialisation* eligibility only; it does not become TE-eligible. This is
> now captured as `TE_EXCLUDE_NON_EE` in `rule_inventory.md` §4.

---

## A-11. Robotics capstone "topic tag" provenance and Path selection

**Text.** Robotics Path 1 = 12u basket + final-year capstone (tag `robotics`); Path 2 = 20u basket. PRM says track grouping is advisory.

- **Interpretation 1 (auto-pick best path):** The auditor picks whichever path passes (prefer Path 1 if a robotics-tagged capstone exists, else Path 2).
- **Interpretation 2 (student declares path):** Path is chosen by the student/manual allocation; mismatched evidence fails.

**Consequence.** Auto-pick can mask a student's intent and silently switch paths; declared-path is stricter but needs an input field.

**Recommended default:** Auto-evaluate both paths, report the satisfied path; if neither passes, report the closest. When a `robotics`-tagged capstone is double-counted with CC, trigger `CAP_LOCK`. Warn if both paths are simultaneously claimed in manual allocation.

---

## A-12. Does a Specialisation course allocated to UE-residual ever count toward the Specialisation's 20 units?

**Text.** PRM 348/362: a course in Specialisation + residual UE only does NOT consume overlap budget.

- **Interpretation 1 (counts as distinct):** Such a course counts as distinct Specialisation units (UE is residual, not a "real" competing requirement). This is the natural reading and the basis of test `ue_residual_does_not_consume_overlap`.
- **Interpretation 2 (UE allocation excludes from spec):** If a course's primary role is `residual_ue`, it is "used by UE" and shouldn't also count to the Specialisation.

**Consequence.** Interpretation 2 would make almost every Specialisation impossible (since Specialisation courses naturally live in UE space, CHK p.2). Interpretation 1 is intended.

**Recommended default:** Interpretation 1 — UE is residual and "free"; a course can be Specialisation-distinct while sitting in UE without overlap consumption. UE is never the "other explicit requirement" that creates overlap.

---

## A-13. Level-1000 cap, internship combinations, and S/U — in scope for audit?

**Text.** CHK p.3 details the 60-unit level-1000 cap, internship combinations, and S/U options.

- **Interpretation 1 (model + check):** Implement `LVL1000_MAX_60` and internship-combo logic as real constraints.
- **Interpretation 2 (out of scope):** PRM's core-rules list (PRM 286–404) does not emphasise these; treat as informational only.

**Consequence.** Skipping them means a transcript exceeding the level-1000 cap would wrongly pass.

**Recommended default:** Model `LVL1000_MAX_60` as a warning-level constraint (not hard-fail for the prototype) and model the internship combos as an `MAJOR_INTERNSHIP_COMBO` requirement. Flag both as lower-priority / `needs_human_review`.

> **RESOLVED → enforce both, ignore S/U.** Human review: "enforce the 60-unit level-1000 cap and
> internship combination check. ignore S/U for now." Promote `LVL1000_MAX_60` and
> `MAJOR_INTERNSHIP_COMBO` to enforced constraints (no longer `needs_human_review`). The S/U
> option is explicitly out of scope for the prototype.

---

## A-14. "Up to one SEP-mapped TE for Major" vs unlimited SEP TEs to UE

**Text.** SPC p.1: "Students can map back one EE3xxxC/EE4xxx from SEP to fulfil the Major programme's TE requirement. You can do as many TEs as you want while on SEP, which can be used to fulfil UE."

- **Interpretation 1:** Exactly one SEP TE may satisfy the *Major TE* counter; additional SEP TEs are valid but only as UE (do not count to the 2-TE rule).
- **Interpretation 2:** Up to one SEP TE total may be *used at all*; extra SEP TEs are invalid.

**Consequence.** Interpretation 2 wrongly rejects legitimate UE-bound SEP courses.

**Recommended default:** Interpretation 1 — cap SEP→Major-TE at 1; allow extra SEP TEs as UE; ensure ≥1 NUS TE remains.

---

## A-15. MQM is co-hosted (Main Host MSE) — does ECE-side double-count budget still apply?

**Text.** SPC p.11 marks MQM "Main Host: MSE, Co-Host: ECE". The 8-unit overlap rule is stated for EE Specialisations generally.

- **Interpretation 1:** MQM follows the same 20/8/12 rule; EE2027 overlap consumes 4u (PRM 503).
- **Interpretation 2:** MSE-hosted Specialisation may have different double-count rules not captured in this PDF.

**Consequence.** Interpretation 2 introduces unknown host-specific rules outside the provided sources.

**Recommended default:** Interpretation 1 (per PRM 503), but tag MQM with a `host: MSE` note and `needs_human_review` for any MSE-specific deviation.

---

## A-16. Capstone units: 8u (EE4002D/R) vs 12u (CDE4301) and overlap budget interaction

**Text.** CC capstone may be EE4002D/R (8u) or CDE4301 (12u, IDP 2nd major).

- **Interpretation 1:** Only the 8u EE4002D/R variants participate in the Specialisation capstone lock; CDE4301 is IDP-only and out of scope.
- **Interpretation 2:** A 12u capstone double-counted would exceed the 8u overlap budget outright (12 > 8) and should fail.

**Consequence.** Ambiguity about whether CDE4301 can ever double-count to a Specialisation.

**Recommended default:** Restrict the capstone lock to EE4002D/EE4002R (8u). Treat CDE4301 as IDP-gated and never auto-double-count it to a Specialisation; flag if attempted.

> **RESOLVED.** Per the CDE iDP 2nd-Major page (quoted in `ambiguous_human_review.md`):
> "CDE4301/CDE4301A cannot be used to fulfil a specialisation in any Engineering major if it
> [is] also used to fulfil the Second Major in Innovation & Design." Model a hard constraint
> `CDE4301_NO_SPEC_IF_IDP`: if CDE4301/CDE4301A is allocated to the IDP 2nd Major, it cannot
> also be allocated to any Specialisation. The capstone *lock* remains restricted to EE4002D/R.

---

## A-17. "Final-year capstone" for Robotics — must it be EE4002D/R specifically?

**Text.** Robotics Path 1 says "a final-year Capstone" (no code). IoT lists EE4002D/R OR CP4106 OR CG4002. MQM lists MLE4101B / EE4002D/R / approved 2-sem project.

- **Interpretation 1:** Robotics capstone must be EE4002D/R tagged `robotics`.
- **Interpretation 2:** Any final-year capstone-type project (incl. CP4106/CG4002/CDE4301) tagged `robotics` qualifies.

**Consequence.** Interpretation 2 is broader and affects which capstones trigger the lock.

**Recommended default:** Accept EE4002D/R tagged `robotics` by default; accept other capstone codes only with `needs_human_review`. The capstone lock (CC double-count) applies only when the qualifying capstone is an EE4002D/R that also satisfies CC.
