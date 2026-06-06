# Degree Auditor

Prototype CLI degree auditor for NUS B.Eng. Electrical Engineering AY2024 JC/non-poly intake.

This project is not official academic advice. It is an unofficial, source-aware rule prototype for experimenting with curriculum modelling, audit reporting, and allocation validation.

## Scope

The prototype currently models:

- EE fixed major core and the EE2026/EE2028 digital/microcontroller choice.
- Technical Course (TC) and Technical Elective (TE) eligibility and mutual exclusion.
- Course aliases, wildcard pools, SEP mapped equivalents, and source-aware YAML config merging.
- Selected EE specialisation satisfaction, overlap budget, capstone lock, and SEP mapping rules.
- Greedy allocation, interactive allocation, manual allocation override, JSON audit output, and Rich terminal reports.

It does not replace faculty, department, or registrar checks.

## Install

Use Python 3.11+ and `uv`.

```bash
uv sync
uv run pytest
```

## CLI Usage

Validate config:

```bash
uv run degree-auditor validate-config --config configs/nus_ee_ay24_jc
```

Inspect eligibility:

```bash
uv run degree-auditor expand-eligibility \
  --config configs/nus_ee_ay24_jc \
  --transcript examples/transcripts/simple_completed.yaml
```

Create an editable allocation plan:

```bash
uv run degree-auditor plan-allocation \
  --config configs/nus_ee_ay24_jc \
  --transcript examples/transcripts/simple_completed.yaml \
  --out tmp/allocation.yaml
```

Create an interactive allocation plan with eligibility comments:

```bash
uv run degree-auditor interactive-allocate \
  --config configs/nus_ee_ay24_jc \
  --transcript examples/transcripts/simple_completed.yaml \
  --out tmp/allocation.yaml
```

Create an interactive allocation plan and immediately audit it:

```bash
uv run degree-auditor interactive-allocate \
  --config configs/nus_ee_ay24_jc \
  --transcript examples/transcripts/simple_completed.yaml \
  --out tmp/allocation.yaml \
  --audit
```

Audit with generated allocation:

```bash
uv run degree-auditor audit \
  --config configs/nus_ee_ay24_jc \
  --transcript examples/transcripts/simple_completed.yaml
```

Audit with manual allocation and JSON output:

```bash
uv run degree-auditor audit \
  --config configs/nus_ee_ay24_jc \
  --transcript examples/transcripts/simple_completed.yaml \
  --allocation tmp/allocation.yaml \
  --format json
```

List configured requirements and specialisations:

```bash
uv run degree-auditor list-requirements --config configs/nus_ee_ay24_jc
uv run degree-auditor list-specialisations --config configs/nus_ee_ay24_jc
```

## Transcript YAML

Transcript files use a top-level `courses` list. SEP courses keep the original overseas code in `course_code` and the mapped NUS equivalent in `mapped_to`.

```yaml
student_flags:
  - IDP
courses:
  - course_code: EE3331C
    title: Feedback Control Systems
    units: 4
    term: AY2025-2026 S1
    grade: A-
    status: completed
    source: NUS
    topic_tags: []
    approved_for: []
  - course_code: SEP4308
    units: 4
    source: SEP
    mapped_to: EE4308
    approval_status: approved
    approved_for:
      - EE24JC_TE
```

## Manual Allocation YAML

Manual allocation files use top-level `allocations`. When supplied to `audit --allocation`, the manual allocation fully replaces greedy allocation.

The `interactive-allocate` command can generate this file by prompting through each transcript course. It writes comments before each course allocation block showing the eligibility expansion used during selection.

```yaml
allocations:
  - course_code: EE2028
    requirement_id: EE24JC_MAJOR_DIGITAL_CHOICE
    units: 4
    allocation_role: primary
  - course_code: EE3331C
    requirement_id: EE24JC_TC
    units: 4
    allocation_role: primary
  # EE4308 eligibility: EE24JC_TE, RBT_ELECTIVES_20_UNITS, UE_RESIDUAL, IGNORED
  - course_code: EE4308
    requirement_id: EE24JC_TE
    units: 4
    allocation_role: primary
```

Allocation roles are `primary`, `double_count`, `residual_ue`, and `ignored`.

## Config Merging

The loader accepts one or more YAML files or folders. Folders are scanned recursively for `.yaml` and `.yml` files.

Rule-bearing lists such as requirements, pools, constraints, aliases, and specialisations are merged by `id`. Identical duplicate ids are accepted. Conflicting duplicate ids fail unless the incoming object has `override: true`.

## Source References

Rules and curriculum objects carry `source_ref` metadata with document, page, section, quote, and notes fields where available. Audit results preserve source refs on constraint results, and text reports surface source documents for failed or important rules.

Some page-level references are still marked with notes where PDF extraction was ambiguous.

## Test Cases

Prompt-style structured audit cases live in `examples/test_cases/`. Each case includes:

```yaml
id: string
description: human-readable description
transcript:
  courses: []
manual_allocation:
  allocations: []
expected:
  pass: true
  satisfied_requirements: []
  failed_requirements: []
  failed_constraints: []
  warnings: []
```

The regular pytest suite validates these cases alongside focused unit tests.

## Limitations

- Greedy allocation is intentionally simple and not globally optimal.
- Specialisation support is partial and focused on the modelled EE AY24 JC paths.
- IoT is structurally loadable and participates in SEP checks, but full IoT satisfaction is deferred.
- Capstone topic matching depends on transcript `topic_tags`.
- SEP and source-reference handling model the prompt requirements, not an official approval workflow.
- No second major or minor audit is implemented.

## Future Work

- CP-SAT or ILP allocation optimiser.
- Streamlit UI.
- NUSMods API import.
- PDF-to-YAML extraction pipeline.
- More cohorts and programmes.
- Second major and minor support.
- Stable CLI snapshot tests once report wording settles.
