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