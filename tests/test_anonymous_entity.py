"""The `AnonymousEntity` warning of `tools/check_corpus.py` (normalisation §3, #79).

A corpus case carries no expected warnings, so `due2-anonymous-target` alone would pass with
the warning gone. These tests pin where it is raised and where it is not.
"""

from __future__ import annotations

from pathlib import Path

from check_corpus import ROOT, check_file

POLICY = """\
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix ex:   <http://example.com/> .

ex:policy a odrl:Set ;
    odrl:conflict odrl:prohibit ;
    odrl:permission ex:read .

ex:read a odrl:Permission ;
    odrl:action odrl:read ;
    odrl:target ex:dataset, [ a odrl:Asset ] ;
    odrl:assignee [ a odrl:Party ] .
"""


def warnings(path: Path) -> list[str]:
    return [w for report, _, _ in check_file(path, [], True) for w in report.warnings]


def test_the_case_warns_once() -> None:
    """Guards the gate of #79: the corpus case's one anonymous target is warned."""
    found = warnings(ROOT / "conformance" / "cases" / "due2-anonymous-target" / "policy.ttl")
    assert sum(w.endswith("[AnonymousEntity]") for w in found) == 1, found


def test_named_targets_and_assignees(tmp_path: Path) -> None:
    """Guards the owner's two choices: the warning fires although the rule also names
    `ex:dataset`, and an anonymous assignee, the one party a request matches, is warned too."""
    path = tmp_path / "policy.ttl"
    path.write_text(POLICY)
    found = [w for w in warnings(path) if w.endswith("[AnonymousEntity]")]
    assert len(found) == 2, found
    assert any("anonymous target" in w for w in found), found
    assert any("anonymous assignee" in w for w in found), found
