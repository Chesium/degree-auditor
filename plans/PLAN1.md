# First Pass: Data Model, Config Loader, TC/TE Rules

## Summary
Build a small runnable Python 3.11+ package named `degree_auditor` with Pydantic models, YAML config loading/merging, TC/TE eligibility and constraint evaluation, a minimal CLI, seed AY24 JC EE config, and 5 focused pytest tests.

This pass will deliberately exclude specialisation rule execution, capstone locks, SEP rules beyond data-model fields, optimiser work, and full reporting polish.

## Key Changes
- Create project scaffold:
  - `pyproject.toml` with `pydantic`, `pyyaml`, `typer`, `rich`, and `pytest`.
  - `degree_auditor/` package with `models.py`, `config_loader.py`, `merge.py`, `eligibility.py`, `constraints.py`, `audit.py`, and `cli.py`.
  - `configs/nus_ee_ay24_jc/` seed YAML for programme, major, TC/TE pools, and constraints.
  - `examples/transcripts/` and `examples/manual_allocations/` for test fixtures.
- Implement Pydantic models for:
  - `SourceRef`, `CourseAttempt`, `CourseAlias`, `CoursePool`, `Requirement`, `RequirementGroup`, `Specialisation`, `Constraint`, `Allocation`, `ConstraintResult`, `AuditResult`.
- Implement config loading:
  - Accept one or more files/folders.
  - Recursively load `.yaml` / `.yml` files from folders.
  - Merge lists by `id` for requirements, pools, constraints, aliases, and specialisations.
  - Accept identical duplicate ids.
  - Fail on conflicting duplicate ids unless incoming object has `override: true`.
  - Preserve and validate `source_ref` on every rule-bearing object.
- Implement TC/TE behavior:
  - TC requires at least 3 allocated eligible courses.
  - TE requires at least 2 allocated eligible courses.
  - TC pool includes `EE2026`, `EE2028`, `EE3033`, `EE3131C`, `EE3408C`, `EE3331C`, `EE3431C`, `EE3731C`, `EE3104C`.
  - `EE2026` / `EE2028` TC eligibility is conditional: only the one not allocated to the major digital/microcontroller choice can count as TC.
  - TE eligibility supports `EE4xxx`, `EE3xxxC`, and `EE3xxx`.
  - TE excludes `EE3033` and `EE3031`.
  - A course allocated to TC and TE fails mutual exclusion.
- Implement minimal CLI:
  - `degree-auditor validate-config --config ...`
  - `degree-auditor expand-eligibility --config ... --transcript ...`
  - `degree-auditor audit --config ... --transcript ... [--allocation ...] [--format text|json]`

## Test Plan
Implement 5 tests runnable with `pytest`:

- `test_config_loads_seed_programme`: loads `configs/nus_ee_ay24_jc` and validates source refs.
- `test_merge_conflicting_duplicate_id_fails`: conflicting duplicate config object fails without `override: true`.
- `test_tc_te_mutual_exclusion_fail`: same course manually allocated to TC and TE fails.
- `test_ee2026_ee2028_choice_tc_success`: `EE2028` allocated to major and `EE2026` allocated to TC is valid.
- `test_te_exclusions_fail`: `EE3031` and `EE3033` manually allocated as TE both fail with source-aware constraint results.

## Assumptions
- Source refs for TC/TE seed config will cite `L_AY24JC_Checklist_Revised_3TC_4June2025.pdf`, using page values where visible from extracted text and `notes` when exact page placement is uncertain.
- The first pass may include structural `Specialisation` fields but will not evaluate specialisation, SEP, overlap, or capstone constraints yet.
- Greedy allocation can be minimal: enough to allocate obvious major choice, TC, and TE deterministically for tests; manual allocation remains the authority when supplied.
- JSON output only needs to expose the Pydantic `AuditResult`; rich terminal formatting can stay simple in this pass.
