"""The alagad-* skills are pure guidance over tools the agent already has.

A skill that tells the agent to run something is the class being removed from
the tenant fleet (the platform floor disables terminal / code_execution, so
such a skill can only fail or invent). This test pins, for each alagad-* skill:

  * the directory holds SKILL.md and nothing else (no scripts/, no helpers);
  * SKILL.md contains no fenced code block at all (so no shell block);
  * no line reads like a command line (python / curl / npx / pip / bash ...);
  * the frontmatter name matches the directory.

Run from the repo root with `pytest` (stdlib only, no fixtures).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"

# The three T1 skills authored 2026-09-19 (feat/alagad-t1-skills). Add every
# future alagad-* skill here; the ph-* pack predates the rule and is not
# covered (ph-business-hours-and-holidays carries one legacy bash block).
NO_SCRIPT_SKILLS = ("alagad-google", "alagad-sources", "alagad-receipts")

FENCE = re.compile(r"^\s*(```|~~~)")
COMMAND_LINE = re.compile(
    r"^\s*(\$ |python3? |curl |npx |npm |pip3? |bash |sh |wget |uv |hermes )"
)


@pytest.mark.parametrize("name", NO_SCRIPT_SKILLS)
def test_skill_dir_is_skill_md_only(name: str) -> None:
    entries = sorted(p.name for p in (SKILLS / name).iterdir())
    assert entries == ["SKILL.md"], f"{name}: unexpected files {entries}"


@pytest.mark.parametrize("name", NO_SCRIPT_SKILLS)
def test_skill_has_no_fenced_block(name: str) -> None:
    lines = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8").splitlines()
    fenced = [i + 1 for i, line in enumerate(lines) if FENCE.match(line)]
    assert not fenced, f"{name}: fenced block opener(s) at line(s) {fenced}"


@pytest.mark.parametrize("name", NO_SCRIPT_SKILLS)
def test_skill_has_no_command_lines(name: str) -> None:
    lines = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8").splitlines()
    hits = [(i + 1, line) for i, line in enumerate(lines) if COMMAND_LINE.match(line)]
    assert not hits, f"{name}: command-like line(s) {hits}"


@pytest.mark.parametrize("name", NO_SCRIPT_SKILLS)
def test_skill_frontmatter_name_matches_dir(name: str) -> None:
    text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{name}: missing frontmatter"
    head = text.split("---", 2)[1]
    assert re.search(rf"^name: {re.escape(name)}$", head, re.M), f"{name}: frontmatter name differs"
    assert re.search(r"^description: .{40,}$", head, re.M), f"{name}: description too short"


@pytest.mark.parametrize("name", NO_SCRIPT_SKILLS)
def test_skill_is_listed_in_install_manifest(name: str) -> None:
    install = (REPO / "install.sh").read_text(encoding="utf-8")
    assert f'"{name}"' in install, f"{name}: not in install.sh SKILLS array"
