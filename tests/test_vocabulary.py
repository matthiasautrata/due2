"""IM 2.1's vocabulary rule and IM 2.5.4's action class in `tools/check_odrl22.py`.

The negative cases `due2-undeclared-action` and `due2-undeclared-cc-action` only show that
the checker finds some violation (`xfail`). These tests pin which ones, as
`docs/decisions/0020` reads the rule.
"""

from __future__ import annotations

import pytest
from check_odrl22 import BASE, ROOT, SHAPE, Vocabulary, check_file
from rdflib import Graph

CASES = ROOT / "conformance" / "cases"
type Checker = tuple[Graph, Graph, Vocabulary]


@pytest.fixture(scope="module")
def checker() -> Checker:
    shapes = Graph().parse(SHAPE)
    base = Graph()
    for f in BASE:
        base.parse(f)
    return shapes, base, Vocabulary.load()


def problems(case: str, checker: Checker) -> list[str]:
    return check_file(CASES / case / "policy.ttl", *checker)[1]


def is_action_class(p: str) -> bool:
    return "Path=http://www.w3.org/ns/odrl/2/action" in p and "ClassConstraintComponent" in p


def test_an_undefined_action_fails_the_rule_and_the_class(checker: Checker) -> None:
    """Guards both gaps of #78. Before decisions/0020, an action from no vocabulary passed:
    the profile rule knew only the DPROD and due2 namespaces, and every IRI object of
    `odrl:action` was typed `odrl:Action`, so the class constraint could not fail."""
    found = problems("due2-undeclared-action", checker)
    assert any("IM 2.1: <http://example.com/promote>" in p for p in found), found
    assert any(is_action_class(p) for p in found), found


def test_a_cc_action_needs_a_profile(checker: Checker) -> None:
    """Guards decisions/0020 #4. `ODRL22.ttl` types `cc:Distribution`, so reading the whole
    file as defined would admit it without its `includedIn` edges. Its class is an Action,
    so the class constraint holds."""
    found = problems("due2-undeclared-cc-action", checker)
    expected = (
        "IM 2.1: <http://creativecommons.org/ns#Distribution> is defined by neither the ODRL "
        "vocabulary (odrl: namespace), a declared profile, nor the policy"
    )
    assert found == [expected]


@pytest.mark.parametrize("case", ["due2-conditional-duties", "rl2-display-vs-nondisplay"])
def test_refined_and_self_typed_actions_are_admitted(case: str, checker: Checker) -> None:
    """Guards the other side of the line. A refined action is an untyped blank node
    (IM 2.5.4), and an `rl2-*` policy types its own `ex:` actions. Typing no action, or
    requiring a profile for self-typed terms, would fail these."""
    assert problems(case, checker) == []


def test_the_baseline_has_no_cc_terms(checker: Checker) -> None:
    """The `odrl:` namespace filter is what keeps the nine `cc:` actions out; without it they
    are in the baseline, through `ODRL22.ttl`."""
    assert not [t for t in checker[2].baseline if str(t).startswith("http://creativecommons.org/")]
