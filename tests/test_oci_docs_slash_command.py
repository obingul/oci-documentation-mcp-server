from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = ROOT / ".agents" / "skills" / "oci-docs" / "SKILL.md"


def test_oci_docs_slash_command_skill_exists() -> None:
    """Ensure the repo-scoped Codex skill is checked in."""
    assert SKILL_PATH.exists()


def test_oci_docs_slash_command_matches_cli_surface() -> None:
    """Ensure the slash command documents the existing CLI surface."""
    content = SKILL_PATH.read_text()

    assert "name: oci-docs" in content
    assert "/oci-docs" in content
    assert "uv run oci-docs" in content

    for subcommand in ("answer", "search", "read"):
        assert f"`{subcommand}`" in content

    for flag in (
        "--search-phrase",
        "--max-sources",
        "--json",
        "--limit",
        "--max-length",
        "--start-index",
    ):
        assert flag in content
