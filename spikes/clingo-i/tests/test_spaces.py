"""The bounded-exhaustive spaces in the brute-force differentials (#44, TESTS.md).

The differentials of test_brute_force.py check generated draws: many inputs, but each shape
reached only by chance. These tests check every input of each space in tests/spaces.py, smallest
first, so that every input up to a bound is covered and a failure shows on the smallest input
that has it. The oracle is the same brute force; the spaces supply inputs only.

Each space is checked at its PR bound in README § Verify, and at its slow bound under
`pytest -m slow`. The slow tests also assert that the slow spaces reach each shape the
differentials rely on, and that the spaces alone expose each mutant of MUTANTS and
DUTY_MUTANTS: no explicit example and no generated draw is needed to kill it.

The same inputs check claim M, monotonicity (correctness-strategy.md §4.8, #85), on the
oracle's semantics, with no clingo: the range that due2-workflows.md §6.4 *Computing it* finds
must be the range over every completion. Claim W, that a definite verdict holding by cases
lists an `unresolved` unknown part, is checked on every reply by `check` and `check_duties`;
the tests here show that the spaces reach that shape and that the check can fail.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable

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
    Literal,
    Node,
    Rule,
    applies,
    check,
    check_duties,
    check_waiver,
    duty_items,
    duty_oracle,
    duty_shapes,
    holds_by_cases,
    monotone_input,
    monotone_ranges,
    mutated,
    oracle,
    parts,
    render,
    render_duties,
    resolve,
    resolve_duties,
    shapes,
)

# The most inputs one test checks: a PR shard runs in about 10 s, a slow one in about 2 min.
SHARD = {"pr": 300, "slow": 3000}

# The space and tier whose inputs expose each mutant soonest, smallest input first. Three need
# the slow bounds; the PR bounds expose the rest.
EXPOSED_BY = {
    "and-or-swapped": ("xone", "pr"),
    "flip-constraint-deleted": ("conflicts", "slow"),
    "live-ignores-negation": ("pinned", "pr"),
    "live-negated-xone-ignores-terms": ("xone", "slow"),
    "live-xone-ignores-term": ("xone", "pr"),
    "missing-paired": ("trees", "pr"),
    "not-as-identity": ("xone", "pr"),
    "opaque-atoms-share-a-variable": ("leaves", "pr"),
    "opaque-leaf-as-f": ("leaves", "pr"),
    "polarity-ignored": ("xone", "pr"),
    "u-atoms-remove": ("leaves", "pr"),
    "u-leaf-of-f-atom-named": ("xone", "pr"),
    "unknown-parts-of-f-atoms": ("candidates", "pr"),
    "unknown-parts-of-u-atoms-only": ("pinned", "pr"),
    "variable-per-leaf": ("xone", "pr"),
    "xone-many-true-as-t": ("xone", "pr"),
    "xone-unknown-as-false": ("xone", "pr"),
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


# TESTS.md, the bounded-exhaustive spaces: the smallest input of xone at its slow
# bound that exposes live-negated-xone-ignores-terms, as clingo shows it and as a Case.
WITNESS_ATOMS = (
    "slot(1,r(prohibition,node(or,neg(node(xone,l(0,eq),node(and,l(0,neq),l(1,eq)))),l(0,eq))))"
    " operand(0,value) operand(1,unresolved) conflict(perm)"
)


def test_negated_xone_worked_example() -> None:
    t, f, u = Leaf(0, "eq"), Leaf(0, "neq"), Leaf(1, "eq")
    neg_xone = Node("not", (Node("xone", (t, Node("and", (f, u), False)), False),), False)
    tree = Node("or", (neg_xone, t), False)
    case = Case(
        "perm",
        (Rule("r0", False, "use", "a", None, (tree,)),),
        "use",
        "a",
        None,
        (1, None, None),
        (False, True, False),
    )
    found = answer_sets("xone.lp", SPACES["xone"].consts("slow"))
    shown = {" ".join(str(a) for a in m): m for m in found}
    assert to_input(shown[WITNESS_ATOMS], False) == case
    assert inputs("xone", "slow").index(case) == 8180
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


# --- claim M ---

type Monotone = tuple[dict[Literal, set[bool]], Callable[[dict[Literal, bool]], str]]


@pytest.mark.parametrize("tier", ["pr", pytest.param("slow", marks=pytest.mark.slow)])
@pytest.mark.parametrize("name", list(SPACES))
def test_space_is_monotone(name: str, tier: str) -> None:
    for x in inputs(name, tier):
        every, computed = monotone_ranges(*monotone_input(x))
        assert computed == every, x


def prohibitions_cancel(x: Case | Duties) -> Monotone:
    """A non-monotone verdict: two prohibitions that apply cancel, so a second one raises a
    `Deny` to `NotApplicable`."""
    assert isinstance(x, Case)
    ps = {r.name: parts(x, r) for r in x.rules}

    def verdict(w: dict[Literal, bool]) -> str:
        on = {n: applies(n, p, w) for n, p in ps.items()}
        forbids = sum(not r.permit and on[r.name] for r in x.rules)
        v = resolve(x, on)[0]
        return "NotApplicable" if v == "Deny" and forbids > 1 else v

    return monotone_input(x)[0], verdict


def deny_needs_a_rule(x: Case | Duties) -> Monotone:
    """DPROD's reading of a violated obligation (due2-workflows.md §6.4, exception 6 of
    due2-profiles.md §8.2): it denies only once a rule applies, so a new permission can turn
    `NotApplicable` into `Deny`."""
    assert isinstance(x, Duties)
    items, _ = duty_items(x)

    def verdict(w: dict[Literal, bool]) -> str:
        v = resolve_duties(x, w)[0]
        ruled = any(applies(r.name, items[r.name], w) for r in x.case.rules)
        return "NotApplicable" if v == "Deny" and not ruled else v

    return monotone_input(x)[0], verdict


def mixed_as_uniform(x: Case | Duties) -> Monotone:
    """The computation without its enumeration: each mixed variable completed as if it moved
    the verdict up."""
    dirs, verdict = monotone_input(x)
    return {lit: {True} if len(d) == 2 else d for lit, d in dirs.items()}, verdict


# Each change that the check must catch, and the space and tier whose inputs expose it.
MONOTONE_MUTANTS: dict[str, tuple[Callable[[Case | Duties], Monotone], str, str]] = {
    "prohibitions-cancel": (prohibitions_cancel, "leaves", "pr"),
    "deny-needs-a-rule": (deny_needs_a_rule, "obligation", "pr"),
    "mixed-as-uniform": (mixed_as_uniform, "obligation", "slow"),
}


@pytest.mark.parametrize(
    "name",
    [
        pytest.param(n, marks=[pytest.mark.slow] if tier == "slow" else [])
        for n, (_, _, tier) in MONOTONE_MUTANTS.items()
    ],
)
def test_monotone_check_kills_mutant(name: str) -> None:
    mutant, space, tier = MONOTONE_MUTANTS[name]
    for x in inputs(space, tier):
        every, computed = monotone_ranges(*mutant(x))
        if computed != every:
            return
    pytest.fail(f"no {tier} input of {space} exposes {name}")


# --- claim W ---


def test_pr_spaces_hold_by_cases(interpreter: Interpreter, duty_interpreter: Interpreter) -> None:
    """The PR spaces reach a definite verdict that holds by cases, among rules and duties
    alike, so `check_waiver` is not vacuous there. The oracle picks the inputs whose basis
    lacks a permission or a prohibition; the reply decides."""
    found: Counter[str] = Counter()
    for name in SPACES:
        for x in inputs(name, "pr"):
            duty = isinstance(x, Duties)
            out = duty_oracle(x) if duty else oracle(x)["output"]
            assert isinstance(out, dict) and isinstance(out["verdict_basis"], list)
            roles = {str(b["role"]) for b in out["verdict_basis"] if isinstance(b, dict)}
            if out["verdict"] not in ("Permit", "Deny") or roles & {"permission", "prohibition"}:
                continue
            got = duty_interpreter.reply(render_duties(x)) if duty else interpreter.reply(render(x))
            assert isinstance(got["output"], dict)
            found[name] += holds_by_cases(got["output"], x.violations if duty else "ignore")
    assert found == {"leaves": 2, "obligation": 2}


def test_waiver_worked_example(duty_interpreter: Interpreter) -> None:
    """TESTS.md, claim W: input 94 of `obligation` at the PR bound denies by cases.
    The prohibition applies when `o0 eq` holds; otherwise the obligation's guard `o0 neq` holds
    and the obligation is violated. No atom denies in every completion, so the basis names the
    obligation with status `unknown`, and `o0` is listed `unresolved`."""
    x = list(inputs("obligation", "pr"))[94]
    assert isinstance(x, Duties) and x.violations == "deny"
    got = duty_interpreter.reply(render_duties(x))["output"]
    assert isinstance(got, dict)
    ob, r0, o0 = (f"https://example.org/{n}" for n in ("ob", "r0", "o0"))
    assert got["verdict"] == "Deny"
    assert got["verdict_basis"] == [{"ref": ob, "role": "obligation"}]
    assert got["obligations"] == [{"duty": ob, "status": "unknown"}]
    assert got["unknown_parts"] == [
        {"ref": ob, "input": o0, "status": "unresolved"},
        {"ref": r0, "input": o0, "status": "unresolved"},
    ]
    assert holds_by_cases(got, x.violations)


def test_waiver_check_kills_missing_paired() -> None:
    """With `missing-paired`, two leaves on one missing operand share a variable, so a verdict
    holds by cases whose only unknown parts are `missing`: `check_waiver` must fail on some
    input of `leaves`, without the oracle."""
    interp = mutated("missing-paired")
    for x in inputs("leaves", "pr"):
        assert isinstance(x, Case)
        got = interp.reply(render(x))["output"]
        assert isinstance(got, dict)
        try:
            check_waiver(got)
        except AssertionError:
            return
    pytest.fail("no pr input of leaves exposes missing-paired to check_waiver")
