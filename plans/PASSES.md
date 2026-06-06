Pass 2: Major + Allocation Pipeline

Implement allocation.py.
Add full EE major evaluation: fixed core, EE2026/EE2028 choice, TE count included in major status.
Add plan-allocation --out ....
Add list-requirements.
Model residual UE as an allocation role, but without specialisation overlap logic yet.
Tests: major_core_pass_basic, greedy allocation output, manual allocation override, CLI smoke tests.


Pass 3: Course Matching + Full Config Shape

Strengthen course matching: exact codes, wildcard pools like EE4xxx, aliases, mapped SEP equivalents.
Add course_aliases.yaml, course_pools.yaml, common_curriculum.yaml.
Add one YAML file per specialisation with source refs, baskets, core/elective structures, and topic-tagged project options.
Add list-specialisations.
Tests: config merge across base folder + specialisation file, course matching, source refs for all specialisation config.


Pass 4: Specialisation Satisfaction + Overlap Budget

Evaluate selected specialisations.
Implement global specialisation policy: 20 units, max 8 overlap, min 12 distinct.
Treat specialisation + residual UE as non-overlap.
Implement AE, Industry 4.0, SET, MQM basic course/core/elective structures.
Implement Robotics coursework-only and capstone paths.
Tests: ae_core_overlap_with_tc_within_budget, ae_core_tc_te_conflict, robotics_coursework_only_pass, robotics_capstone_path_pass, mqm_ee2027_overlap_budget, ue_residual_does_not_consume_overlap.


Pass 5: Capstone Lock Rules

Implement Common Curriculum capstone allocation recognition.
Implement EE4002D/R capstone lock for SPT, Robotics, IoT, MQM.
If capstone is double-counted with Common Curriculum, consume full 8-unit overlap budget for that specialisation.
Forbid further TE double-counting for that same specialisation.
Implement SPT standard path and iDP replacement flag behavior.
Tests: robotics_capstone_overlap_lock_fail, spt_standard_pass, mqm_overlap_exceeds_budget_fail.


Pass 6: SEP Rules

Extend SEP data model if needed: original overseas code, mapped NUS equivalent, approval target, approval status.
Implement TE SEP rule: at least one qualifying TE done at NUS, at most one SEP-mapped EE3xxxC/EE4xxx for major TE.
Implement specialisation SEP rules: max 8 unique SEP units per specialisation, no same SEP course across two specialisations.
Enforce no SEP mapping when capstone is used for SPT, IoT, Robotics, MQM.
Tests: sep_te_one_nus_one_sep_pass, sep_te_all_sep_fail, sep_specialisation_max_8_units_pass, sep_specialisation_over_8_units_fail, sep_same_course_two_specialisations_fail, spt_capstone_sep_forbidden_fail.


Pass 7: Reporting + Structured Test Cases

Build reporting.py with richer terminal output.
Report major, TC, TE, selected specialisations, SEP status, overlap budget, capstone lock, missing units/courses, failed constraints, and source refs.
Add structured YAML test case format from the prompt.
Optionally add CLI snapshot tests once output stabilizes.
Tests: report content checks, JSON shape checks, structured fixture runner.


Pass 8: README + Prototype Polish

Expand README with scope, unofficial warning, install, CLI usage, transcript YAML, manual allocation YAML, config merge behavior, source refs, limitations, and future work.
Add .gitignore for .venv, __pycache__, .pytest_cache, temp allocation outputs.
Clean any generated cache artifacts from version control.
Final full-suite uv run pytest and CLI smoke pass.

Pass 9: Public Contract Alignment

Add contract output shape while preserving existing internal models.
Add pass, cohort, total_units, detailed requirements, constraints, failed_constraints, specialisations.
Add ID mapping from internal slot IDs to review IDs using edge_cases.yaml meta.slot_to_requirement.
Add audit exit code semantics: 0 pass, 2 audit fail, 1 invalid input/config.
Add --format yaml.
Tests: trivial JSON schema, failed audit exit 2, invalid input exit 1, known ID vocabulary.


Pass 10: Edge Case Harness

Add tests_blackbox/ or tests/test_review_edge_cases.py.
Load review/edge_cases.yaml, apply defaults, materialize temp transcript/allocation/config overlay.
Assert subset semantics from meta.assertion_semantics.
Initially mark unsupported categories with focused xfail only where implementation has not reached that pass.
This becomes the verification spine for all later passes.


Pass 11: Common Curriculum + UE + Total Units

Add CC requirements/pools/config for GE and ISK pillars.
Implement DEG_TOTAL_160, CC_CDE_60, UE_40, MAJOR_60.
Implement CDE2501 dual-role logic and TC-in-lieu ST/CN/SF.
Implement RC/college/poly human-review flags.
Tests from edge cases: CDE2501 branches, IE2141 XOR TC, RC4 substitution warning, TC count not inflated.


Pass 12: Internship + Level-1000

Add internship course pool and aliases.
Implement MAJOR_INTERNSHIP_10, combo units, UROP cap, UE overflow, poly APC, CEG-only exclusions.
Implement LVL1000_MAX_60.
Tests: all internship cases in edge_cases.yaml, level-1000 cap warning/fail behavior.


Pass 13: Course Catalog Corrections + Aliases

Update aliases and pools from rule_inventory.md.
Implement asymmetric alias handling: non-EE twins can satisfy specialisation/UE but not EE TE.
Add CG3207 AY2024 TE carve-out.
Add EE3033 term gate.
Add non-EE TE exclusion constraint.
Tests: ME3243/EE3305, ME3163/EE3306, ME3142, CG3207, EE3033 effective date.


Pass 14: Specialisation Completion Corrections

Update all seven specialisation configs to match inventory.
Implement IoT full satisfaction.
Correct Robotics basket, SPT basket/path, SET exclusions, MQM alternatives/project options, Industry 4.0 core/electives.
Implement CDE4301/CDE4301A vs IDP second-major conflict.
Tests: IoT, Robotics aliases, Emerging Tech exclusion, CDE4301 conflict, corrected baskets.


Pass 15: SEP Residency + SEP/TC Refinements

Implement SEP_RESIDENCY_50 and SEP_PROGRAMME_60.
Make SEP-to-TC an explicit, source-ref’d rule for AY23/AY24.
Ensure extra SEP TEs can go to UE but not Major TE.
Tests: SEP residency below 50, SEP programme 60, SEP mapped to TC.


Pass 16: Manual Allocation Validation

Add validation before audit:
unknown course
unknown requirement
allocation units exceed attempt units
ineligible target
duplicate single-instance double-use
Return exit 1 for invalid input via CLI.
Tests: manual_alloc_unknown_course_error, manual_alloc_units_exceed_attempt_error, manual_alloc_ineligible_requirement_fail.


Pass 17: Reporting + Determinism

Align text report sections with black-box snapshots.
Include missing courses/units, overlap, capstone lock, SEP mapped units, manual warnings.
Add deterministic ordering for transcript/config/allocation output.
Tests: snapshot/substrings, repeated JSON identical, plan-allocation round-trip.