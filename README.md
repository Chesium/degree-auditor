# Degree Auditor

Prototype CLI degree auditor for NUS B.Eng. Electrical Engineering AY2024 JC/non-poly intake.

This is not official academic advice. It is a source-aware rule prototype built from the PDFs in `resources/`.

## Setup

```bash
uv sync
uv run pytest
```

## CLI

```bash
uv run degree-auditor validate-config --config configs/nus_ee_ay24_jc
uv run degree-auditor expand-eligibility --config configs/nus_ee_ay24_jc --transcript examples/transcripts/simple_completed.yaml
uv run degree-auditor audit --config configs/nus_ee_ay24_jc --transcript examples/transcripts/simple_completed.yaml
uv run degree-auditor audit --config configs/nus_ee_ay24_jc --transcript examples/transcripts/simple_completed.yaml --format json
```

This first pass implements the data model, config loading/merging, and EE TC/TE checks only.

