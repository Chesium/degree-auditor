# Rule Inventory — NUS B.Eng. (EE) AY2024 JC / non-poly intake

Independent, implementation-blind review. Sources used:

- **CHK** = `resources/L_AY24JC_Checklist_Revised_3TC_4June2025.pdf` (4 pages; cited as "CHK p.N")
- **SPC** = `resources/ECE_Specialisations_AY2025_7July2025.pdf` (18 pages; cited as "SPC p.N")
- **PRM** = `prompt.txt` (project requirements; cited as "PRM line N")

Page numbers refer to the printed page markers in each PDF (`-- N of 4 --`, `-- N of 18 --`).
Every rule below is something the implementation must be able to represent, evaluate, or explicitly mark as out-of-scope/ambiguous.

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
| `CC_GE_24` | requirement | General Education sub-block = 24 units (GESS, GEC, GEN, ES2631, CS1010E, GEA1000). | CHK p.1 |
| `CC_ISK_36` | requirement | Interdisciplinary Skills / Core Skills & Knowledge = 36 units (DTK1234, EG1311/EG1311BE, IE2141, EE2211, CDE2501, CDE2000, PF1101, capstone). | CHK p.1 |
| `CC_CAPSTONE` | requirement | Integrated Project: EE4002D Design Capstone (8u) **or** EE4002R Research Capstone (8u) **or** CDE4301 DCP Dissertation (12u, under 2nd Major IDP). | CHK p.1 |
| `UE_40` | requirement | Unrestricted Electives = 40 units; "build your own degree" / residual capacity. | CHK p.2 ("40 units"); PRM 30 |
| `MAJOR_60` | requirement | Major Requirements = 60 units total. | CHK p.2; PRM 31 |
| `MAJOR_ENGCORE_20` | requirement | Engineering Core = 20 units: MA1511 (2), MA1512 (2), MA1508E (4), EG2401A (2), EG3611A internship (10). | CHK p.2 |
| `MAJOR_INTERNSHIP_COMBO` | requirement | The 10-unit internship may be satisfied by combinations: CFG2101 (4) + EG2605 UROP (4), EG3611A IA (10), EG3612 VIA (6), EG3611P (10, poly). | CHK p.2 |
| `MAJOR_PROG_40` | requirement | Major Programme = 40 units (8 fixed/choice core courses @4u = 32u + 2 TE @4u = 8u). | CHK p.2 |
| `LVL1000_MAX_60` | constraint | No more than 60 units of level-1000 courses count toward the degree (excludes POY190x, CFG1010, ES1103, CFG1002, DYOC). Extra units excluded from graduation total but still count to GPA. | CHK p.3 |

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
| `TC_MIN_3` | requirement | AY24 JC/non-poly intake must read **at least 3** Technical Courses. 3 is the minimum; more is allowed. | CHK p.1 ("AY24 intake (JC/non-poly): Read 3 T.C", "3 T.C is the minimum"); PRM 32, 309 |
| `TC_ADDITIONAL_TO_TE` | policy | The 3 TCs are **in addition to** the 2-TE Tech Elective rule. Both must be satisfied. | CHK p.1; PRM 34 |
| `TC_POOL` | data | Eligible TC courses: EE2026 **or** EE2028 (whichever not used for Major), EE3033 (wef Sem2 AY25/26), and Extended Core EE3131C, EE3408C, EE3331C, EE3431C, EE3731C, EE3104C. EE3xxxC courses can count toward TC. | CHK p.1 (TC column); PRM 36, 313–322 |
| `TC_EFFECTIVE_DATE_EE3033` | policy | EE3033 is only TC-eligible from Semester 2 AY2025/26 onward; earlier terms must not allow it. | CHK p.1; PRM 36, 318 |
| `TC_NOT_TE` | constraint | A Technical Course is **not** a Technical Elective. A course used for TC cannot concurrently fulfil TE. | CHK p.1 ("Technical Course (T.C) is not Technical Elective (T.E)"); CHK p.3 ("Courses used to fulfil T.C rule, cannot be used to fulfil T.E rule, and v.v."); PRM 33, 35 |

---

## 4. Technical Elective (TE) rule

| id | kind | description | source |
|----|------|-------------|--------|
| `TE_MIN_2` | requirement | At least 2 EE Technical Electives (8u). | CHK p.2; PRM 327 |
| `TE_POOL` | data | Eligible TE: any combination of EE4xxx, Extended Core EE3xxxC, and EE3xxx. | CHK p.2 (TE column); PRM 329–333 |
| `TE_EXCLUDE_EE3033` | constraint | EE3033 is explicitly **not** a TE (it is TC/separate). | CHK p.2 ("EE3xxx (does not include EE3033)"); PRM 336 |
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
| `SET_ELECTIVES_MIN_2` | requirement | Choose ≥2 from: EE4501, EE4505, EE4438, EE4511. (Possibly also EE4032, EE4205 "Emerging Technologies" — see ambiguity A-09.) |

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
| `ALIAS_EE3305_ME3243` | EE3305 = ME3243 (Robotic System Design). | SPC p.8, p.12; PRM (aliases) |
| `ALIAS_EE3306_ME3163` | EE3306 = ME3163 (Intro to Cyber Physical Systems). | SPC p.6, p.12 |
| `ALIAS_EE3331C_ME3142` | EE3331C ≈ ME3142 (Feedback Control Systems; ME3142 "for ME students"). | SPC p.6 |
| `ALIAS_EE4002D_EE4002R` | EE4002D (Design) and EE4002R (Research) capstone variants, both 8u. | CHK p.1; SPC p.9 |
| `ALIAS_EE4436_MLE4207` | MLE4207 OR EE4436 (Fabrication Process Technology) — alternatives in MQM. | SPC p.11 |
| `ALIAS_EE4802_IE4213` | EE4802 = IE4213 (Learning from Data). | SPC p.12, p.14 |

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
