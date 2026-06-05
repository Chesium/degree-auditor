# First Pass: Data Model, Config Loader, TC/TE Rules with uv

## Summary
Build a small runnable Python 3.11+ package named `degree_auditor` using the `uv` toolchain for project management, dependency locking, CLI execution, and tests. The first pass includes Pydantic models, YAML config loading/merging, TC/TE eligibility and constraint evaluation, seed AY24 JC EE config, a minimal Typer CLI, and 5 focused pytest tests.

This pass excludes specialisation rule execution, capstone locks, SEP rules beyond data-model fields, optimiser work, and full reporting polish.

## Key Changes
- Use `uv` as the project toolchain:
  - Create `pyproject.toml` compatible with `uv`.
  - Add runtime dependencies: `pydantic`, `pyyaml`, `typer`, and `rich`.
  - Add dev dependency group with `pytest`.
  - Generate and commit `uv.lock`.
  - Run commands via `uv run`, e.g. `uv run pytest` and `uv run degree-auditor ...`.
- Create package scaffold:
  - `degree_auditor/` with `models.py`, `config_loader.py`, `merge.py`, `eligibility.py`, `constraints.py`, `audit.py`, and `cli.py`.
  - `configs/nus_ee_ay24_jc/` seed YAML for programme, major, TC/TE pools, and constraints.
  - `examples/transcripts/` and `examples/manual_allocations/` for fixtures.
- Implement Pydantic models for `SourceRef`, `CourseAttempt`, `CourseAlias`, `CoursePool`, `Requirement`, `RequirementGroup`, `Specialisation`, `Constraint`, `Allocation`, `ConstraintResult`, and `AuditResult`.
- Implement config loading:
  - Accept one or more files/folders.
  - Recursively load `.yaml` / `.yml` files from folders.
  - Merge lists by `id`.
  - Accept identical duplicate ids.
  - Fail on conflicting duplicate ids unless incoming object has `override: true`.
  - Validate and preserve `source_ref` on rule-bearing config objects.
- Implement TC/TE behavior:
  - TC requires at least 3 allocated eligible courses.
  - TE requires at least 2 allocated eligible courses.
  - TC includes `EE2026`, `EE2028`, `EE3033`, `EE3131C`, `EE3408C`, `EE3331C`, `EE3431C`, `EE3731C`, `EE3104C`.
  - `EE2026` / `EE2028` TC eligibility depends on which one is not allocated to the major digital/microcontroller choice.
  - TE supports `EE4xxx`, `EE3xxxC`, and `EE3xxx`, excluding `EE3033` and `EE3031`.
  - TC and TE allocation for the same course fails mutual exclusion.
- Implement minimal CLI:
  - `uv run degree-auditor validate-config --config ...`
  - `uv run degree-auditor expand-eligibility --config ... --transcript ...`
  - `uv run degree-auditor audit --config ... --transcript ... [--allocation ...] [--format text|json]`

## Test Plan
Run tests with `uv run pytest`.

Implement 5 tests:
- `test_config_loads_seed_programme`: loads `configs/nus_ee_ay24_jc` and validates source refs.
- `test_merge_conflicting_duplicate_id_fails`: conflicting duplicate config object fails without `override: true`.
- `test_tc_te_mutual_exclusion_fail`: same course manually allocated to TC and TE fails.
- `test_ee2026_ee2028_choice_tc_success`: `EE2028` allocated to major and `EE2026` allocated to TC is valid.
- `test_te_exclusions_fail`: `EE3031` and `EE3033` manually allocated as TE both fail with source-aware constraint results.

## Assumptions
- `uv` is installed and available as `uv 0.10.5`.
- The implementation will use `uv sync` or equivalent `uv` commands to create/update the lockfile.
- Source refs for TC/TE seed config will cite `L_AY24JC_Checklist_Revised_3TC_4June2025.pdf`, with page values where visible from extracted text and `notes` when exact placement is uncertain.
- Greedy allocation can stay minimal; manual allocation remains authoritative when supplied.
- JSON output only needs to expose the Pydantic `AuditResult`; Rich text output can stay simple in this pass.
