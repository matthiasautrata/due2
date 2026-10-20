"""Every Markdown document we cite, and every decision record, exists.

Documents cite each other by bare file name (README § Layout), so moving a file,
for example into `docs/archive/`, must not leave a citation that names nothing. The
checks cover back-quoted `.md` names, Markdown link targets, and `decisions/NNNN`
numbers in our Markdown, Python and ASP sources. They do not check section numbers,
or citations of other kinds of file. Vendored suites and profiles are out of scope:
they are never edited, and a bare name never resolves to a file in them.
"""

from __future__ import annotations

import re
import subprocess
from collections import defaultdict

import pytest
from check_odrl22 import ROOT

VENDORED = ("conformance/external/", "profiles/vendor/")

# Documents in other repositories, cited by the name they have there.
EXTERNAL = {
    "formal-semantics.md": "DPROD Contracts, not vendored (due2-profiles.md §8)",
    "specification.md": "DPROD Contracts, not vendored",
    "RL2_Model.md": "RL2 (decisions/0001)",
    "RL2_Semantics.md": "RL2 (decisions/0001)",
    "RL2_Compilation.md": "RL2 (decisions/0001)",
}

# A back-quoted Markdown file name, alone or followed by a section (due2-workflows.md §6.4).
CITED = re.compile(r"`([^`\s]+\.md)(?:\s[^`]*)?`")
LINK = re.compile(r"\]\((?!https?://)([^)#\s]+\.md)(?:#[^)]*)?\)")
DECISION = re.compile(r"\bdecisions/(\d{4})\b")


def tracked() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],  # noqa: S607
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [p for p in out.splitlines() if (ROOT / p).exists()]


FILES = tracked()
OURS = [p for p in FILES if p.endswith((".md", ".py", ".lp")) and not p.startswith(VENDORED)]
BY_NAME: defaultdict[str, list[str]] = defaultdict(list)
for p in OURS:
    BY_NAME[p.rsplit("/", 1)[-1]].append(p)
RECORDS = {p.rsplit("/", 1)[-1][:4] for p in FILES if p.startswith("docs/decisions/0")}


def resolves(cited: str, source: str) -> bool:
    """A bare name names exactly one file; `README.md` is the top-level one. A path is
    read from the repository root, the citing file's directory, or `docs/`."""
    if "<" in cited:  # a pattern such as `spikes/<name>/DESIGN.md`
        return True
    if "/" not in cited:
        return cited == "README.md" or cited in EXTERNAL or len(BY_NAME[cited]) == 1
    if cited.rsplit("/", 1)[-1] in EXTERNAL:
        return True
    bases = (ROOT, (ROOT / source).parent, ROOT / "docs")
    return any((base / cited).is_file() for base in bases)


@pytest.mark.parametrize("source", OURS)
def test_every_cited_document_resolves(source: str) -> None:
    text = (ROOT / source).read_text()
    dangling = [
        f"{n}: {m.group(1)}"
        for n, line in enumerate(text.splitlines(), 1)
        for m in CITED.finditer(line)
        if not resolves(m.group(1), source)
    ]
    assert dangling == []


@pytest.mark.parametrize("source", [p for p in OURS if p.endswith(".md")])
def test_every_link_target_exists(source: str) -> None:
    text = (ROOT / source).read_text()
    parent = (ROOT / source).parent
    dangling = [m.group(1) for m in LINK.finditer(text) if not (parent / m.group(1)).is_file()]
    assert dangling == []


@pytest.mark.parametrize("source", OURS)
def test_every_cited_decision_exists(source: str) -> None:
    text = (ROOT / source).read_text()
    missing = sorted({m.group(1) for m in DECISION.finditer(text)} - RECORDS)
    assert missing == []
