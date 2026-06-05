from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readme_mentions_required_sections() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for text in [
        "not official academic advice",
        "uv sync",
        "CLI Usage",
        "Transcript YAML",
        "Manual Allocation YAML",
        "Config Merging",
        "Source References",
        "Limitations",
        "Future Work",
        "CP-SAT",
        "Streamlit",
        "NUSMods",
        "PDF-to-YAML",
        "Second major",
    ]:
        assert text in readme


def test_gitignore_contains_python_and_temp_outputs() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    for entry in [
        ".venv/",
        "__pycache__/",
        ".pytest_cache/",
        ".ruff_cache/",
        "tmp/",
        "temp/",
        "*.allocation.yaml",
    ]:
        assert entry in gitignore
