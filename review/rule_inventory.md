# Rule Inventory — NUS B.Eng. (EE) AY2024 JC / non-poly intake

Independent, implementation-blind review. **Updated** after human review (`ambiguous_human_review.md`)
and the additional resource PDFs. Sources used:

- **CHK** = `resources/L_AY24JC_Checklist_Revised_3TC_4June2025.pdf` (4 pages; "CHK p.N")
- **SPC** = `resources/ECE_Specialisations_AY2025_7July2025.pdf` (18 pages; "SPC p.N")
- **PRM** = `prompt.txt` ("PRM line N")
- **TCL** = `resources/Electrical-Engineering-List-of-Additional-Technical-Courses-v3.pdf` (closed TC list)
- **FAQ** = `resources/FAQ for In-Flight students_For AY24 Non Poly_17Jun2025.pdf`
- **GRB** = `resources/EE2_Revised Grad Req Briefing_20June25.pdf` ("GRB p.N")
- **CTK** = `resources/EE2_Curriculum_Talk_2025_13Aug2025.pdf` ("CTK p.N")
- **TE26** = `resources/EE_TechElectives_AY2026_iii.pdf` (master TE list; course attributes + intake carve-outs)
- **SEP** = `resources/ECE_SEP_Outgoing_AY2627_30Jan26.pdf`

Page numbers refer to the printed page markers in each PDF.
Every rule below is something the implementation must be able to represent, evaluate, or explicitly mark as out-of-scope/ambiguous.

> **Scope confirmation (CC units).** GRB describes a CC revision from 60→40 units with the
> Integrated Project moved into major space — that applies to the **fresh AY2025/26 intake**. For
> the **in-flight AY2024/25 cohort in scope here**, CTK p.7 confirms the structure stays
> **CC 60 / UE 40 / Major 60 = 160**, with the 3 TCs read inside CC pillar space (Systems
> Thinking / Creating Narratives / Sustainable Futures) or UE. The CHK checklist is authoritative
> for this cohort.

Legend for `kind`:
- `requirement` — a unit/course completion target that can be satisfied/unsatisfied.
- `constraint` — a cross-cutting validity check on an allocation (can fail even if requirements look satisfied).
- `policy` — a global modelling rule that shapes allocation/eligibility.
- `data` — a course-set / alias / pool definition.
- `scope` — explicitly in or out of scope for this prototype.

---

## 1. Degree-level / structural requirements

| id | kind | description | source |
|----|------|-------------|--------|
| `DEG_TOTAL_160` | requirement | Total degree requirement is 160 units for B.Eng.(EE). | CHK p.2 ("TOTAL 160 units"); PRM 28 |
| `CC_CDE_60` | requirement | Common Curriculum (CDE) totals 60 units. | CHK p.1 ("Common Curriculum CDE : 60 units"); PRM 29 |
| `CC_GE_24` | requirement | General Education sub-block = 24 units (six pillars below). | CHK p.1 |
| `CC_ISK_36` | requirement | Interdisciplinary Skills / Core Skills & Knowledge = 36 units (seven pillars + Integrated Project below). | CHK p.1 |

See **§1b (GE pillars)**, **§1c (Interdisciplinary Skills pillars)**, and **§1d (inflight TC
substitution)** for the per-pillar breakdown — the aggregates above are NOT sufficient on their
own; the auditor must check each pillar and the substitution logic.

---

## 1b. General Education — 6 pillars (24 units)

Each pillar is 4 units. `GESSxxxx`, `GECxxxx`, `GENxxxx` are **course families** — match by
prefix, not exact code.

| id | kind | description | source |
|----|------|-------------|--------|
| `CC_GE_GESS` | requirement | Singapore Studies pillar — any `GESSxxxx` course (4u). | CHK p.1 |
| `CC_GE_GEC` | requirement | Cultures & Connections pillar — any `GECxxxx` course (4u). | CHK p.1 |
| `CC_GE_GEN` | requirement | Communities & Engagement pillar — any `GENxxxx` course (4u). Advisory: complete by Year 3. Two GEN types (year-long service-learning vs one-sem project-based); some end at Special Term II and delay graduation. | CHK p.1; GRB p.20–21 |
| `CC_GE_ES2631` | requirement | Critique & Expression pillar — ES2631 (4u). | CHK p.1 |
| `CC_GE_CS1010E` | requirement | Digital Literacy pillar — CS1010E (4u). | CHK p.1 |
| `CC_GE_GEA1000` | requirement | Data Literacy pillar — GEA1000 (former GER1000) (4u). | CHK p.1 |

## 1c. Interdisciplinary Skills — 7 pillars + Integrated Project (36 units)

| id | kind | description | source |
|----|------|-------------|--------|
| `CC_ISK_DTK1234` | requirement | Design Thinking — DTK1234 (4u). | CHK p.1 |
| `CC_ISK_MAKER` | requirement | Maker Space — EG1311 / EG1311BE Design & Make (4u). | CHK p.1 |
| `CC_ISK_ST` | requirement | Systems Thinking — IE2141 (4u) **or a TC in lieu** (see `CC_TC_IN_LIEU_ST`). | CHK p.1; GRB p.4 |
| `CC_ISK_AI` | requirement | Artificial Intelligence — EE2211 Introduction to Machine Learning (4u). | CHK p.1 |
| `CC_ISK_SF` | requirement | Sustainable Futures — CDE2501 Liveable Cities (4u) **or a TC in lieu** (conditional, see `CC_TC_IN_LIEU_SF`). | CHK p.1; GRB p.10 |
| `CC_ISK_CN` | requirement | Creating Narratives — CDE2000 (4u) **or a TC in lieu** (see `CC_TC_IN_LIEU_CN`). | CHK p.1; GRB p.4 |
| `CC_ISK_PM` | requirement | Project Management — PF1101 (4u). | CHK p.1 |
| `CC_ISK_CAPSTONE` | requirement | Integrated Project — EE4002D/EE4002R (8u) or CDE4301 (12u, IDP). Same object as `CC_CAPSTONE` below; subject to the capstone overlap lock. | CHK p.1 |
| `CC_CAPSTONE` | requirement | Integrated Project: EE4002D Design Capstone (8u) **or** EE4002R Research Capstone (8u) **or** CDE4301 DCP Dissertation (12u, under 2nd Major IDP). | CHK p.1 |

## 1d. Inflight TC substitution into Common Curriculum (AY2024 cohort)

The 3 additional **Technical Courses** (not TEs) are absorbed by vacated CC pillars or by UE —
they do **not** add units beyond 160. These rules are the decision matrix from GRB p.12
(Options 1–4) / FAQ scenarios 1–16.

| id | kind | description | source |
|----|------|-------------|--------|
| `CC_TC_IN_LIEU_ST` | policy | If IE2141 is **not** taken, a TC may satisfy the Systems Thinking pillar in lieu of IE2141. Mutually exclusive: IE2141 XOR (TC-in-ST). | FAQ Q1; GRB p.4, p.10 |
| `CC_TC_IN_LIEU_CN` | policy | If CDE2000 is **not** taken, a TC may satisfy the Creating Narratives pillar in lieu of CDE2000. Mutually exclusive: CDE2000 XOR (TC-in-CN). | FAQ Q1; GRB p.4 |
| `CC_TC_IN_LIEU_SF` | policy | A TC may satisfy the Sustainable Futures pillar **only when** CDE2501 is redirected to Singapore Studies (i.e. no GESS course taken). If a GESS course is taken, CDE2501 occupies SF and no TC may go there. | FAQ Q6; GRB p.10, p.12 |
| `CC_CDE2501_DUAL_ROLE` | constraint | **CDE2501 is always compulsory.** Exactly one of: (a) no GESS taken ⇒ CDE2501 → Singapore Studies (`CC_GE_GESS`) and a TC → Sustainable Futures; or (b) GESS taken ⇒ GESS → `CC_GE_GESS` and CDE2501 → Sustainable Futures (`CC_ISK_SF`), with the third TC going to UE. CDE2501 may occupy **only one** pillar (no double-count of CDE2501 across SS and SF). | FAQ Q5/Q6; GRB p.10; CHK p.1 |
| `CC_TC_OVERFLOW_TO_UE` | policy | TCs not absorbable by ST/CN/SF pillars must be read using UE space. The TC requirement reallocates CC pillar space or consumes UE; it never inflates the 160-unit total. | FAQ Q4; GRB p.4, p.12; CTK p.7 |
| `CC_RC_EXCLUSION` | scope | The standard substitution table does **not** apply to RC4 / UTCP / NUSC / RVRC / poly-graduate students (different college mappings; e.g. RC4 Junior Seminar precludes IE2141). Flag `needs_human_review` if such a `student_flag` is present. | FAQ table note + Q7; GRB p.17 |
| `UE_40` | requirement | Unrestricted Electives = 40 units; "build your own degree" / residual capacity. | CHK p.2 ("40 units"); PRM 30 |
| `MAJOR_60` | requirement | Major Requirements = 60 units total. | CHK p.2; PRM 31 |
| `MAJOR_ENGCORE_20` | requirement | Engineering Core = 20 units: MA1511 (2), MA1512 (2), MA1508E (4), EG2401A (2), EG3611A internship (10). | CHK p.2 |
| `MAJOR_INTERNSHIP_COMBO` | requirement | **(A-13 RESOLVED: enforce.)** The 10-unit internship may be satisfied by combinations: CFG2101 (4) + EG2605 UROP (4), EG3611A IA (10), EG3612 VIA (6), EG3611P (10, poly). | CHK p.2 |
| `MAJOR_PROG_40` | requirement | Major Programme = 40 units (8 fixed/choice core courses @4u = 32u + 2 TE @4u = 8u). | CHK p.2 |
| `LVL1000_MAX_60` | constraint | **(A-13 RESOLVED: enforce.)** No more than 60 units of level-1000 courses count toward the degree (excludes POY190x, CFG1010, ES1103, CFG1002, DYOC). Extra units excluded from graduation total but still count to GPA. | CHK p.3 |
| `SU_OPTION` | scope | **Out of scope for prototype (A-13).** S/U option / grade-free scheme not modelled. | CHK p.3; A-13 |

---

## 2. EE Major Programme core (fixed + choice)

| id | kind | description | source |
|----|------|-------------|--------|
| `MAJ_EE1111A` | requirement | EE1111A required (4u). | CHK p.2; PRM 294 |
| `MAJ_EE2111A` | requirement | EE2111A required (4u). | CHK p.2; PRM 295 |
| `MAJ_EE2012` | requirement | EE2012 required (4u). | CHK p.2; PRM 296 |
| `MAJ_EE2022` | requirement | EE2022 required (4u). | CHK p.2; PRM 297 |
| `MAJ_EE2023` | requirement | EE2023 required (4u). | CHK p.2; PRM 298 |
| `MAJ_EE2027` | requirement | EE2027 required (4u). Also an MQM core course (see overlap rules). | CHK p.2; PRM 299 |
| `MAJ_PC2020` | requirement | PC2020 required (4u). | CHK p.2; PRM 300 |
| `MAJ_DIGITAL_CHOICE` | requirement | Exactly one of EE2026 (Digital Design) or EE2028 (Microcontroller Programming) for the major (4u). Modelled as a choice group. | CHK p.2; PRM 301, 304 |
| `MAJ_TE_2` | requirement | Two EE Technical Electives (8u) inside the Major Programme. | CHK p.2 ("EE4____ / EE4____ … Two EE Technical Electives … 8 units"); PRM 302 |

---

## 3. Technical Course (TC) rule — AY24 JC/non-poly inflight change

| id | kind | description | source |
|----|------|-------------|--------|
| `TC_MIN_3` | requirement | AY24 JC/non-poly intake must read **at least 3** Technical Courses (= **12 units**). 3 is the minimum; more is allowed. | CHK p.1; FAQ ("12 additional units of technical courses"); GRB p.6; PRM 32, 309 |
| `TC_ADDITIONAL_TO_TE` | policy | The 3 TCs are **in addition to** the 2-TE Tech Elective rule. Both must be satisfied. | CHK p.1; GRB p.8; PRM 34 |
| `TC_POOL` | data | **Closed** TC pool (exactly): EE2026 **or** EE2028 (whichever not used for Major), EE3033, and the six Extended Cores EE3131C, EE3408C, EE3331C, EE3431C, EE3731C, EE3104C. **No open "any EE3xxxC" rule** — these six are the only extended cores. A course outside this set must NOT satisfy TC. | TCL; FAQ Q3; GRB p.7; CHK p.1 — **corrects A-01** |
| `TC_EFFECTIVE_DATE_EE3033` | policy | EE3033 (Systems Integration & Design Lab) TC-eligible from **AY2025/26 Sem 2**; **AY2026/27 onward Sem 1 & 2**. Earlier terms must not allow it. Prereqs: EE2023, EE2026, EE2027. EE3033 is **not** an Extended Core and **not** a TE. | TCL; FAQ "Note"; TE26 Note 1; CHK p.1 |
| `TC_SEP_MAPPABLE` | policy | AY23/AY24 intake students **may map SEP courses to the TC requirement** (due to the inflight curriculum change). | SEP p.2 ("AY23 and AY24 intake students may take SEP courses to map to Technical Course (TC) requirements") — **new** |
| `TC_NOT_TE` | constraint | A Technical Course is **not** a Technical Elective. A course used for TC cannot concurrently fulfil TE. | CHK p.1, p.3; GRB p.8; FAQ Q2 note; PRM 33, 35 |

---

## 4. Technical Elective (TE) rule

| id | kind | description | source |
|----|------|-------------|--------|
| `TE_MIN_2` | requirement | At least 2 EE Technical Electives (8u). | CHK p.2; PRM 327 |
| `TE_POOL` | data | Eligible TE: any combination of EE4xxx, Extended Core EE3xxxC, and EE3xxx. Authoritative AY2021–AY2024 TE list is enumerated in GRB p.9 (per area CN/CISR/ICES/MwRF/MTD/PES/SAMI/GEN) + the six extended cores. | CHK p.2; GRB p.9; TE26; PRM 329–333 |
| `TE_EXCLUDE_NON_EE` | constraint | **Non-EE courses (MExxxx, CSxxxxDE, RBxxxx) cannot fulfil the EE TE rule — UE only.** They may still satisfy Specialisation electives. Affects ME3142/ME3243/ME3163/ME4245/RB4301, CS3237/CS3244/CS4222, CS20xxDE, etc. | TE26 Note 2 — **new** |
| `TE_AY24_CG3207_OK` | data | For **AY2024 intake & prior**, CG3207 **is** TE-eligible (the UE-only restriction on CG3207 applies only to AY2025 intake & after). | TE26 Note 3 ("AY2024 intake & prior: CG3207 can be used to fulfil EE Tech Elective rule") — **new/corrects** |
| `TE_AY24_EE3xxx_OK` | data | For **AY2024 intake**, EE3105, EE3305, EE3306, EE3703, EE3801 **are** valid TEs (they appear in the AY2021–AY2024 TE table). The "UE only" restriction on these is **AY2025 intake & after**. | GRB p.9 (titled "EE Technical Electives: AY2021-AY2024 intake"); TE26 Note 3 — **new** |
| `TE_EXCLUDE_EE3033` | constraint | EE3033 is explicitly **not** a TE (TC pool only; not an Extended Core). | CHK p.2; TE26 Note 1; PRM 336 |
| `TE_EXCLUDE_EE3031` | constraint | EE3031 can only fulfil UE for AY2021–AY2024 intake, **not** the TE rule. | CHK p.2 (Note *); PRM 337 |
| `TE_MUTEX_TC` | constraint | TE and TC are mutually exclusive (same course cannot satisfy both). Mirror of `TC_NOT_TE`. | CHK p.3; PRM 338 |

---

## 5. SEP (Student Exchange Programme) rules

| id | kind | description | source |
|----|------|-------------|--------|
| `SEP_TE_ONE_NUS` | constraint | At least one TE (EE3xxxC **or** EE4xxx) must be completed at NUS. | SPC p.1 (rule 2); PRM 341, 397 |
| `SEP_TE_MAX_ONE_MAPPED` | constraint | At most **one** SEP-mapped EE3xxxC/EE4xxx may be used to fulfil the Major TE requirement. (Unlimited SEP TEs may still map to UE.) | SPC p.1 (rule 2); PRM 342, 398 |
| `SEP_SPEC_MAX_8` | constraint | At most 8 units of **unique** SEP courses may be mapped per Specialisation. | SPC p.1 (rule 3); PRM 401 |
| `SEP_SPEC_NO_REUSE` | constraint | A SEP course approved for one Specialisation must not be mapped again to another Specialisation or Minor. | SPC p.1 (rule 3); PRM 402 |
| `SEP_CAPSTONE_FORBIDS_SEP` | constraint | If the capstone is used to fulfil SPT, IoT, Rbt, or MQM, then **no** SEP courses may be mapped to that respective Specialisation. | SPC p.1 (rule 3); PRM 379, 404 |
| `SEP_RESIDENCY_50` | constraint | NUS residency: **≥50%** of overall courses must be read at NUS. | SEP p.2 — **new** |
| `SEP_PROGRAMME_60` | constraint | Programme requirement: **≥60%** of course requirements must be read at NUS. | SEP p.2 — **new** |
| `SEP_MAY_MAP_TC` | policy | AY23/AY24 intake students may map SEP courses to the **TC** requirement (mirror of `TC_SEP_MAPPABLE`). | SEP p.2 — **new** |
| `SEP_CORE_ADVISORY_16` | policy | Advisory (not hard): do not map away more than 16 units of level-2xxx EE core courses on SEP. | SEP p.2 — **new, advisory** |

---

## 6. Specialisation global policy

| id | kind | description | source |
|----|------|-------------|--------|
| `SPEC_TOTAL_20` | requirement | Each Specialisation = 20 units. | SPC p.1; PRM 356 |
| `SPEC_MAX_OVERLAP_8` | constraint | Up to 8 units (40%) of a Specialisation may be double-counted with another requirement. | SPC p.1; PRM 357 |
| `SPEC_MIN_DISTINCT_12` | constraint | At least 12 units of each Specialisation must be distinct/non-overlapping. | SPC p.1; PRM 358 |
| `SPEC_OVERLAP_DEF` | policy | An allocation "overlaps" only if the same course units are also allocated to another **explicit non-UE** requirement (TC, TE, CC, another Spec). | PRM 360 |
| `SPEC_ADVISORY` | policy | Specialisations are advisory; students may take a subset / compose own TEs. Track groupings (e.g. Robotics Track 1/2/3) are advisory only, not hard requirements. | SPC p.2 ("serve as an advisory"), SPC p.8 (Robotics tracks); PRM 460 |

---

## 7. Capstone double-counting lock

| id | kind | description | source |
|----|------|-------------|--------|
| `CAP_LOCK` | constraint | If EE4002D/EE4002R (8u) is double-counted between Common Curriculum and a Specialisation, the entire 8-unit overlap budget for that Specialisation is consumed, and **no further** technical elective may be double-counted for that Specialisation. | SPC p.1 (rule 1 cont.); PRM 366–368 |
| `CAP_LOCK_APPLIES` | policy | Applies to SPT (compulsory satellite capstone), and to Robotics / IoT / MQM **if** their related capstone is used for that Specialisation. | SPC p.1; PRM 370–375 |
| `CAP_LOCK_SEP` | constraint | When capstone is used for SPT/IoT/Rbt/MQM, no SEP courses may map to that Specialisation (= `SEP_CAPSTONE_FORBIDS_SEP`). | SPC p.1; PRM 377–379 |
| `CDE4301_NO_SPEC_IF_IDP` | constraint | CDE4301/CDE4301A **cannot** fulfil a Specialisation in any Engineering major if it is also used for the IDP Second Major. The 8-unit capstone *lock* itself remains restricted to EE4002D/EE4002R. | CDE iDP 2nd-Major page (A-16) — **new** |

---

## 8. UE treatment

| id | kind | description | source |
|----|------|-------------|--------|
| `UE_RESIDUAL` | policy | UE is residual graduation capacity, not a normal double-counting requirement. | PRM 346 |
| `UE_NO_OVERLAP_CONSUME` | policy | A Specialisation course allocated to the Specialisation **and residual UE only** does NOT consume the Specialisation's overlap budget. Overlap is consumed only when also allocated to another explicit requirement. | PRM 348, 362; PRM 757–759 |

---

## 9. Specialisation baskets (data + requirement structure)

### 9.1 Advanced Electronics (AE) — SPC p.5
| id | kind | description |
|----|------|-------------|
| `AE_CORE` | requirement | Core (compulsory): EE3408C, EE3431C. |
| `AE_ELECTIVES_MIN_3` | requirement | Choose ≥3 from: EE4218, EE4407, EE4415, EE5507, CG3207, EE4409, EE4435, EE4436, EE4437, EE4438. |

### 9.2 Industry 4.0 (Indust4) — SPC p.6
| id | kind | description |
|----|------|-------------|
| `IND4_CORE` | requirement | Core: (EE3331C or ME3142) **and** (EE3306/ME3163). |
| `IND4_ELECTIVES_MIN_3` | requirement | Choose ≥3 from: EE4302, EE4311, EE4312, EE4315, EE4307, EE4211, EE4212, EE4314, RB4301, ME3242, ME4262, ME5422, ME4248, ME5405, CN4227R, CN4221R. |

### 9.3 Internet of Things (IoT) — SPC p.7
| id | kind | description |
|----|------|-------------|
| `IOT_CORE` | requirement | Core: CS3237, EE4211, EE4409. |
| `IOT_ELECTIVES_MIN_2_OR_8U` | requirement | Choose ≥2 electives **or** 8 units equivalent from: CS3244, CS4222, EE4204, EE4216, EE4218, plus IoT-related EE4002D/EE4002R / CP4106 / CG4002 as topic-tagged project options. |

### 9.4 Robotics (Rbt) — SPC p.8
| id | kind | description |
|----|------|-------------|
| `RBT_PATH1_CAPSTONE` | requirement | Path 1: 12 units from Robotics basket + a final-year capstone tagged `robotics`. |
| `RBT_PATH2_COURSEWORK` | requirement | Path 2: 20 units from Robotics basket (no capstone). |
| `RBT_BASKET` | data | BN4203, BN4601, EE3305/ME3243, EE4311, EE4312, EE4314, RB4301, EE4308, EE4309, EE4705, ME4242, ME4245, ME5406, MLE4228. |

### 9.5 Space Technology (SPT) — SPC p.9
| id | kind | description |
|----|------|-------------|
| `SPT_CORE` | requirement | Standard path core: EE3105 + EE4002D/EE4002R tagged `satellite` (8u, compulsory). |
| `SPT_ELECTIVES_MIN_2` | requirement | Choose ≥2 from: EE3104C, EE3131C, EE3331C, EE4101, EE4115, EE4218, EE4314, EE4503. |
| `SPT_IDP_PATH` | requirement | iDP path: EE4002D may be replaced by another 8 units of recommended SPT TEs (EE3105 + 4 basket courses). Only active when `student_flags: [IDP]`. EG4301 may be topic-related but its units must NOT count toward SPT (triple-count avoidance). |

### 9.6 Sustainable Electric Transportation (SET) — SPC p.10
| id | kind | description |
|----|------|-------------|
| `SET_CORE` | requirement | Core: EE4502, EE4503, EE4513. |
| `SET_ELECTIVES_MIN_2` | requirement | Choose ≥2 from: EE4501, EE4505, EE4438, EE4511. **(A-09 RESOLVED: EE4032/EE4205 "Emerging Technologies" are NOT SET electives — ignore that block entirely; EE4032 is GEN-area, EE4205 is CN-area per TE26.)** |

### 9.7 Microelectronics & Quantum Materials (MQM) — SPC p.11 (Main Host MSE, Co-Host ECE)
| id | kind | description |
|----|------|-------------|
| `MQM_CORE` | requirement | Core: EE2027, MLE2105. |
| `MQM_ELECTIVES_MIN_3_OR_12U` | requirement | Choose ≥3 courses (12 units) from: EE3431C, EE4409, EE4435, EE4437, EE4438, MLE3105, MLE4201, (MLE4207 or EE4436), MLE4219, MLE4220, MLE4222, and a related-area project (MLE4101B / EE4002D / EE4002R / approved 2-sem research). |
| `MQM_EE2027_OVERLAP` | constraint | EE2027 is already EE Major core; if also allocated to MQM it consumes 4 units of MQM's overlap budget. | PRM 503, 721–724 |

---

## 10. Course aliases / equivalences (data)

| id | description | source |
|----|-------------|--------|
| `ALIAS_EE3305_ME3243` | EE3305 cross-listed with ME3243 (Robotic System Design). **ME3243 is non-EE → UE/Spec only, not TE** (`TE_EXCLUDE_NON_EE`). | SPC p.8, p.12; TE26 p.2 |
| `ALIAS_EE3306_ME3163` | EE3306 cross-listed with ME3163 (Intro to Cyber Physical Systems). **ME3163 is non-EE → UE/Spec only, not TE.** | SPC p.6, p.12; TE26 p.2 |
| `ALIAS_EE3331C_ME3142` | EE3331C ≈ ME3142 (Feedback Control Systems; ME3142 "for ME students", non-EE → not TE). | SPC p.6; TE26 (anti-req) |
| `ALIAS_EE4002D_EE4002R` | EE4002D (Design) and EE4002R (Research) capstone variants, both 8u. | CHK p.1; SPC p.9 |
| `ALIAS_EE4436_MLE4207` | MLE4207 OR EE4436 (Fabrication Process Technology) — alternatives in MQM. | SPC p.11; TE26 (anti-req EE4436/MLE4207) |
| `ALIAS_EE4802_IE4213` | EE4802 = IE4213 (Learning from Data); anti-req of EE4211. | SPC p.12, p.14; TE26 p.4 |
| `ALIAS_GEA1000_GER1000` | GEA1000 = former GER1000 (Data Literacy pillar). | CHK p.1 |

**Alias note:** resolving a non-EE twin (e.g. ME3243→EE3305) grants **Specialisation/UE**
eligibility only; it never makes the course TE-eligible (`TE_EXCLUDE_NON_EE`).

---

## 10b. Course-title / attribute corrections (data)

The Specialisations PDF and `prompt.txt` use a few outdated titles. Authoritative titles per
TE26 (master list, 6 Apr 2026):

| course | corrected title / attribute | source |
|--------|------------------------------|--------|
| EE3731C | "Signal **Analytics**" (not "Signal Analysis") | TE26 p.1; GRB p.7 |
| EE3033 | "Systems Integration and Design **Lab**"; prereq EE2023+EE2026+EE2027 | TCL; TE26 Note 1 |
| EE4409 | "**Microelectronic Applications for Modern Life**" (was "Modern Microelectronic Devices & Sensors") | TE26 p.2 |
| EE4315 | "**Industrial Control Systems with AI**" (former EE4303 "Intelligent Industrial Control Systems") | TE26 p.2 |
| EE4305 | "**Fuzzy/Neural Systems for intelligent robotics**"; anti-req of EE4311/EE4312 | TE26 p.2 |
| EE4205 | "**Quantum Computing and Communication**" (former "Quantum Communication and Cryptography") | TE26 p.1 |
| EE4438 | "Solar Cells and **Modules**" (SPC AE list says "Solar Cells and Courses" — typo) | TE26 p.3 |
| EE4112 | "Radio Frequency for Cellular and Satellite Systems" (MWRF) | TE26 p.2 |

---

## 11. Allocation strategy (policy)

| id | kind | description | source |
|----|------|-------------|--------|
| `ALLOC_ELIGIBILITY_NEQ_ALLOCATION` | policy | Course eligibility ≠ course allocation. A course eligible for many requirements is allocated to specific ones; the auditor validates the allocation. | PRM 109–112 |
| `ALLOC_GREEDY_PRIORITY` | policy | Deterministic greedy priority: (1) fixed Major core, (2) EE2026/EE2028 choice, (3) CC capstone, (4) TC, (5) TE, (6) selected Specialisations, (7) residual UE. | PRM 514–524 |
| `ALLOC_MANUAL_OVERRIDE` | policy | Manual allocation overrides greedy, but constraints are still evaluated. Invalid manual allocations must produce clear errors or failed constraint results. | PRM 527, 547 |
| `ALLOC_ROLES` | data | Allocation roles: `primary`, `double_count`, `residual_ue`, `ignored`. | PRM 279–284 |

---

## 12. Config / source-reference policy

| id | kind | description | source |
|----|------|-------------|--------|
| `CFG_SOURCE_REF` | policy | Every loaded config object must retain a `source_ref` (document, page, section, quote, notes). | PRM 216, 218–229 |
| `CFG_MERGE_BY_ID` | policy | Requirements, pools, constraints, specialisations merged by `id`. Identical → accept; conflict → fail fast unless `override: true`. | PRM 208–214 |
| `CFG_MERGE_UNION_LISTS` | policy | Pool `includes`/`excludes` unioned unless a conflict is detected. | PRM 215–216 |
| `CFG_DESCRIPTION_HUMAN` | policy | `description` must be human-readable, derived from PDF text. | PRM 231 |

---

## 13. Explicit scope boundaries

| id | kind | description | source |
|----|------|-------------|--------|
| `SCOPE_NO_2ND_MAJOR` | scope | Second-major audit out of scope (data structures may exist but not tested). | PRM 12, 87, 403 |
| `SCOPE_NO_MINOR` | scope | Minor audit out of scope; only cross-Specialisation SEP conflict is tested. | PRM 87, 403 |
| `SCOPE_NO_OPTIMISER` | scope | No CP-SAT / ILP optimiser; greedy + manual only. | PRM 86 |
| `SCOPE_NO_WEB` | scope | No web app, no live scraping, no runtime LLM. | PRM 85, 88, 89 |
| `SCOPE_CDE4301_IDP` | scope | CDE4301 dissertation path is under 2nd Major IDP; model but treat as IDP-gated. | CHK p.1; PRM 474–478 |

---

## Cross-cutting "hot" courses (eligible for many requirements — high allocation-conflict risk)

These are the courses most likely to expose allocation bugs (eligibility ≠ allocation):

| course | eligible for |
|--------|--------------|
| EE3331C | TC (extended core), TE (EE3xxxC), IND4 core, SPT elective |
| EE3408C | TC (extended core), TE, AE core |
| EE3431C | TC (extended core), TE, AE core, MQM elective |
| EE3104C | TC (extended core), TE, SPT elective |
| EE3131C | TC (extended core), TE, SPT elective |
| EE3731C | TC (extended core), TE |
| EE4409 | TE, AE elective, IoT core, MQM elective |
| EE4438 | TE, AE elective, SET elective, MQM elective |
| EE4218 | TE, AE elective, IoT elective, SPT elective |
| EE4211 | TE, IND4 elective, IoT core |
| EE4314 | TE, IND4 elective, Robotics basket, SPT elective |
| EE4311/EE4312 | TE, IND4 elective, Robotics basket |
| EE2027 | Major core, MQM core (4u overlap) |
| EE4002D/R | CC capstone, IoT/SPT/Rbt/MQM project (capstone lock) |
| EE2026/EE2028 | Major digital choice; the unused one → TC |
