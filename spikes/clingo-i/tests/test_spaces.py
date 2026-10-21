"""The bounded-exhaustive spaces in the brute-force differentials (#44, DESIGN.md § Tests).

The differentials of test_brute_force.py check generated draws: many inputs, but each shape
reached only by chance. These tests check every input of each space in tests/spaces.py, smallest
first, so that every input up to a bound is covered and a failure shows on the smallest input
that has it. The oracle is the same brute force; the spaces supply inputs only.

Each space is checked at its PR bound in README § Verify, and at its slow bound under
`pytest -m slow`. The slow tests also assert that the slow spaces reach each shape the
differentials rely on, and that the spaces alone expose each mutant of MUTANTS and
DUTY_MUTANTS: no explicit example and no generated draw is needed to kill it.
"""

from __future__ import annotations

from collections import Counter

import pytest

from clingo_i.interpret import Interpreter
from tests.spaces import SPACES, answer_sets, count, inputs, models, to_input
from tests.test_brute_force import (
    DUTY_MUTANTS,
    DUTY_WANTED,
    MUTANTS,
    WANTED,
    Case,
    Duties,
    Leaf,
    Node,
    Rule,
    check,
    check_duties,
    duty_shapes,
    mutated,
    oracle,
    render,
    shapes,
)

# The most inputs one test checks: a PR shard runs in about 10 s, a slow one in about 2 min.
SHARD = {"pr": 300, "slow": 3000}

# The space and tier whose inputs expose each mutant soonest, smallest input first. Five need
# the slow bounds; the PR bounds expose the rest.
EXPOSED_BY = {
    "and-or-swapped": ("negxone", "pr"),
    "flip-constraint-deleted": ("conflicts", "slow"),
    "live-ignores-negation": ("pinned", "pr"),
    "live-negated-xone-ignores-terms": ("negxone", "slow"),
    "live-xone-ignores-term": ("pinned", "slow"),
    "missing-paired": ("trees", "pr"),
    "not-as-identity": ("pinned", "pr"),
    "opaque-atoms-share-a-variable": ("leaves", "pr"),
    "opaque-leaf-as-f": ("leaves", "pr"),
    "polarity-ignored": ("negxone", "pr"),
    "u-atoms-remove": ("leaves", "pr"),
    "u-leaf-of-f-atom-named": ("pinned", "slow"),
    "unknown-parts-of-f-atoms": ("candidates", "pr"),
    "unknown-parts-of-u-atoms-only": ("pinned", "pr"),
    "variable-per-leaf": ("negxone", "pr"),
    "xone-without-negations": ("negxone", "pr"),
    "duties-never-unknown": ("routes", "pr"),
    "duty-roots-negated": ("guards", "pr"),
    "fulfilled-share-a-variable": ("routes", "pr"),
    "fulfilled-u-as-f": ("routes", "pr"),
    "in-force-guards-ignored": ("obligation", "pr"),
    "violated-u-owed-listed": ("guards", "slow"),
}


def shards(tier: str) -> list[tuple[str, int, int]]:
    """Each space at `tier` cut into shards of at most SHARD[tier] inputs: (space, k, of)."""
    out: list[tuple[str, int, int]] = []
    for name in SPACES:
        of = -(-count(name, tier) // SHARD[tier])
        out += [(name, k, of) for k in range(of)]
    return out


def check_one(rules: Interpreter, duties: Interpreter, x: Case | Duties) -> None:
    if isinstance(x, Duties):
        check_duties(duties, x)
    else:
        check(rules, x)


@pytest.mark.parametrize("tier", ["pr", pytest.param("slow", marks=pytest.mark.slow)])
@pytest.mark.parametrize("name", list(SPACES))
def test_space_has_its_count(name: str, tier: str) -> None:
    assert len(models(name, tier)) == count(name, tier)


@pytest.mark.parametrize(("name", "k", "of"), shards("pr"))
def test_pr_space_matches_brute_force(
    interpreter: Interpreter, duty_interpreter: Interpreter, name: str, k: int, of: int
) -> None:
    for x in inputs(name, "pr")[k::of]:
        check_one(interpreter, duty_interpreter, x)


@pytest.mark.slow
@pytest.mark.parametrize(("name", "k", "of"), shards("slow"))
def test_slow_space_matches_brute_force(
    interpreter: Interpreter, duty_interpreter: Interpreter, name: str, k: int, of: int
) -> None:
    for x in inputs(name, "slow")[k::of]:
        check_one(interpreter, duty_interpreter, x)


@pytest.mark.slow
def test_slow_spaces_reach_each_shape() -> None:
    seen: Counter[str] = Counter()
    for name in SPACES:
        for x in inputs(name, "slow"):
            seen.update(duty_shapes(x) if isinstance(x, Duties) else shapes(x))
    wanted = WANTED | DUTY_WANTED
    assert {s: seen[s] for s in wanted if seen[s] == 0} == {}, seen


def test_each_mutant_has_a_space() -> None:
    assert EXPOSED_BY.keys() == MUTANTS.keys() | DUTY_MUTANTS.keys()
    for name, (space, _) in EXPOSED_BY.items():
        assert SPACES[space].duties == (name in DUTY_MUTANTS), name


@pytest.mark.slow
@pytest.mark.parametrize("name", sorted(EXPOSED_BY))
def test_spaces_alone_expose_mutant(name: str) -> None:
    space, tier = EXPOSED_BY[name]
    interp = mutated(name)
    for x in inputs(space, tier):
        try:
            check_one(interp, interp, x)
        except AssertionError:
            return
    pytest.fail(f"no {tier} input of {space} exposes {name}")


# DESIGN.md § Tests, the bounded-exhaustive spaces: the smallest input of negxone at its slow
# bound that exposes live-negated-xone-ignores-terms, as clingo shows it and as a Case.
WITNESS_ATOMS = (
    "slot(1,r(prohibition,node(or,neg(node(xone,l(0,eq),node(and,l(0,neq),l(1,eq)))),l(0,eq))))"
    " operand(0,value) operand(1,unresolved) conflict(perm)"
)


def test_negated_xone_worked_example() -> None:
    t, f, u = Leaf(0, "eq"), Leaf(0, "neq"), Leaf(1, "eq")
    negxone = Node("not", (Node("xone", (t, Node("and", (f, u), False)), False),), False)
    tree = Node("or", (negxone, t), False)
    case = Case(
        "perm",
        (Rule("r0", False, "use", "a", None, (tree,)),),
        "use",
        "a",
        None,
        (1, None, None),
        (False, True, False),
    )
    found = answer_sets("negxone.lp", SPACES["negxone"].consts("slow"))
    shown = {" ".join(str(a) for a in m): m for m in found}
    assert to_input(shown[WITNESS_ATOMS], False) == case
    assert inputs("negxone", "slow").index(case) == 1052
    deny = {
        "verdict": "Deny",
        "verdict_basis": [{"ref": "https://example.org/r0", "role": "prohibition"}],
        "eliminated": [],
        "unknown_parts": [],
    }
    assert oracle(case) == {"output": deny}
    got = mutated("live-negated-xone-ignores-terms").reply(render(case))["output"]
    assert isinstance(got, dict)
    assert got["unknown_parts"] == [
        {"ref": "https://example.org/r0", "input": "https://example.org/o1", "status": "unresolved"}
    ]
