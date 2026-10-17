"""The brute-force differential (DESIGN.md § Tests, correctness-strategy.md §4.1).

Over generated policies of permissions and prohibitions, with an absent target or an unnamed
assignee, a Python oracle enumerates every completion of the literals, flips each literal
alone, and derives the verdict, the basis, the eliminations, the `unknown` atoms, and the
range (due2-workflows.md §5.2, §6.1 to §6.4; decisions/0011). It reads the generated rules, not the
program's facts, and shares only the spec's literal key with it.

A rule may carry constraint trees over request parameters, some of them absent. The oracle
gives a tree its value by supervaluation: it tries `t` and `f` for each leaf whose parameter is
absent, each leaf on its own, and the tree is `u` when the tries disagree. That is strong Kleene
logic for a tree whose leaves are independent (due2-workflows.md §5.2), computed without the
program's ranks. A `u` constraint part of a `u` atom has a completion literal the spike does not
build yet (#48), so the oracle predicts the `"completion"` decline.

The mutation test runs the same differential against programs with one rule changed, and
asserts that it fails (#47). The measurement test asserts that the generator reaches each
shape the differential relies on.
"""

from __future__ import annotations

import itertools
import operator
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass

import pytest
from hypothesis import Phase, example, given, settings
from hypothesis import strategies as st

from clingo_i.interpret import CHAIN, Interpreter, load_programs
from clingo_i.json_types import Json, Obj
from tests.conftest import INIT, PREFIXES, vector

EX = "https://example.org/"
XSD_INTEGER = "http://www.w3.org/2001/XMLSchema#integer"
ACTIONS = ("use", "play")  # play ⊑ use in the test core (conftest.INIT)
PARTIES = ("alice", "bob")
OPERANDS = 3  # ex:o0 to ex:o2, each read from the request parameter of the same name
# Every leaf compares its operand with the right operand 1.
OPERATORS: dict[str, Callable[[int, int], bool]] = {
    "eq": operator.eq,
    "neq": operator.ne,
    "lt": operator.lt,
    "lteq": operator.le,
    "gt": operator.gt,
    "gteq": operator.ge,
}


@dataclass(frozen=True)
class Leaf:
    operand: int
    op: str


@dataclass(frozen=True)
class Node:
    conn: str  # and, or, xone, or not (dprod:not)
    members: tuple[Tree, ...]
    as_list: bool  # the members as one RDF list, or as repeated values


type Tree = Leaf | Node


@dataclass(frozen=True)
class Rule:
    name: str
    permit: bool
    action: str
    target: str
    assignee: str | None
    constraints: tuple[Tree, ...] = ()


@dataclass(frozen=True)
class Case:
    conflict: str
    rules: tuple[Rule, ...]
    action: str
    target: str | None  # None: absent
    assignee: str | None  # None: the request names no assignee
    params: tuple[int | None, ...] = (None,) * OPERANDS  # None: absent


def trees(depth: int) -> st.SearchStrategy[Tree]:
    """Constraint trees at most `depth` connectives deep. A leaf comes first, so it shrinks to one."""
    leaf = st.builds(Leaf, st.integers(0, OPERANDS - 1), st.sampled_from(tuple(OPERATORS)))
    if depth == 0:
        return leaf
    sub = trees(depth - 1)
    negation = st.builds(Node, st.just("not"), st.tuples(sub), st.just(False))
    nary = st.builds(
        Node,
        st.sampled_from(("and", "or", "xone")),
        st.lists(sub, min_size=2, max_size=3).map(tuple),
        st.booleans(),
    )
    return st.one_of(leaf, negation, nary)


TREES = trees(2)


@st.composite
def cases(draw: st.DrawFn) -> Case:
    rules = [
        Rule(
            f"r{i}",
            draw(st.booleans()),
            draw(st.sampled_from(ACTIONS)),
            draw(st.sampled_from(("a", "a", "b"))),
            draw(st.sampled_from((None, *PARTIES))),
            tuple(draw(st.lists(TREES, max_size=2)) if draw(st.booleans()) else ()),
        )
        for i in range(draw(st.integers(1, 4)))
    ]
    target = draw(st.sampled_from((None, "a", "b")))
    assignee = draw(st.sampled_from((None, *PARTIES)))
    if draw(st.booleans()):
        # Plant a t candidate beside the unknowns: then a u candidate moves no verdict, the
        # case that tells pivotal atoms from merely unknown ones (0011 #1). Unplanted, it is
        # about one Indeterminate in a hundred.
        rules.append(Rule(f"r{len(rules)}", True, "use", "a", None))
        target, assignee = "a", None
    return Case(
        draw(st.sampled_from(("prohibit", "perm", "invalid"))),
        tuple(rules),
        draw(st.sampled_from(ACTIONS)),
        target,
        assignee,
        tuple(draw(st.sampled_from((None, 0, 1, 2))) for _ in range(OPERANDS)),
    )


def turtle(tree: Tree) -> str:
    match tree:
        case Leaf(k, op):
            return f"[ odrl:leftOperand ex:o{k} ; odrl:operator odrl:{op} ; odrl:rightOperand 1 ]"
        case Node(conn, members, as_list):
            pred = "dprod:not" if conn == "not" else f"odrl:{conn}"
            items = [turtle(m) for m in members]
            return f"[ {pred} " + (f"( {' '.join(items)} )" if as_list else ", ".join(items)) + " ]"


def render(case: Case) -> Obj:
    refs = " ; ".join(
        f"odrl:{'permission' if r.permit else 'prohibition'} ex:{r.name}" for r in case.rules
    )
    lines = [
        "@prefix dprod: <https://ekgf.org/dprod/spec/develop/> .",
        f"ex:p a odrl:Set ; odrl:conflict odrl:{case.conflict} ; {refs} .",
    ]
    for r in case.rules:
        cls = "Permission" if r.permit else "Prohibition"
        party = f" ; odrl:assignee ex:{r.assignee}" if r.assignee else ""
        cons = (
            f" ; odrl:constraint {', '.join(map(turtle, r.constraints))}" if r.constraints else ""
        )
        lines.append(
            f"ex:{r.name} a odrl:{cls} ; odrl:action odrl:{r.action} ; odrl:target ex:{r.target}"
            f"{party}{cons} ."
        )
    # Each operand is bound in the policy to the request parameter of its own name.
    lines.extend(
        f"ex:o{k} dprod:operandSource dprod:requestSource ; dprod:operandProperty ex:o{k} ."
        for k in range(OPERANDS)
    )
    parties: Obj = {"odrl:assignee": f"ex:{case.assignee}"} if case.assignee else {}
    params: Obj = {
        f"ex:o{k}": {"@value": str(p), "@type": XSD_INTEGER}
        for k, p in enumerate(case.params)
        if p is not None
    }
    v = vector(
        PREFIXES + "\n".join(lines) + "\n",
        request={"action": f"odrl:{case.action}", "parties": parties, "params": params},
    )
    request = v["request"]
    assert isinstance(request, dict)
    if case.target is None:
        del request["target"]
    else:
        request["target"] = f"ex:{case.target}"
    return v


# --- the oracle ---

type Truth = bool | None  # None is u
type Literal = tuple[str, str]


def leaves(tree: Tree) -> Iterator[Leaf]:
    """The tree's leaf occurrences, depth first."""
    match tree:
        case Leaf():
            yield tree
        case Node(_, members, _):
            for m in members:
                yield from leaves(m)


def classical(tree: Tree, values: Iterator[bool]) -> bool:
    """Two-valued truth, taking each leaf occurrence's value from `values` in `leaves` order."""
    match tree:
        case Leaf():
            return next(values)
        case Node(conn, members, _):
            vs = [classical(m, values) for m in members]  # a list: every member reads its leaves
            if conn == "and":
                return all(vs)
            if conn == "or":
                return any(vs)
            if conn == "xone":
                return sum(vs) == 1
            return not vs[0]


def tree_value(case: Case, tree: Tree) -> Truth:
    """The tree's value by supervaluation over its leaf occurrences whose parameter is absent."""
    known: list[Truth] = []
    for leaf in leaves(tree):
        p = case.params[leaf.operand]
        known.append(None if p is None else OPERATORS[leaf.op](p, 1))
    gaps = [i for i, k in enumerate(known) if k is None]
    results: set[bool] = set()
    for fill in itertools.product((False, True), repeat=len(gaps)):
        values = list(known)
        for i, b in zip(gaps, fill, strict=True):
            values[i] = b
        results.add(classical(tree, iter(bool(v) for v in values)))
    return results.pop() if len(results) == 1 else None


def parts(case: Case, r: Rule) -> list[Truth | Literal]:
    """A rule's parts: a known truth, or the literal a u part reads (due2-workflows.md §6.4).

    A `u` constraint part is `None`: its literal is not built yet (#48).
    """
    out: list[Truth | Literal] = [case.action == r.action or r.action == "use"]
    out.append(("target", r.target) if case.target is None else case.target == r.target)
    if r.assignee is not None:
        out.append(("party", r.assignee) if case.assignee is None else case.assignee == r.assignee)
    out.extend(tree_value(case, t) for t in r.constraints)
    return out


def finding(ps: list[Truth | Literal]) -> Truth:
    """Kleene conjunction, with every literal u."""
    if any(p is False for p in ps):
        return False
    return None if any(p is None or isinstance(p, tuple) for p in ps) else True


def applies(ps: list[Truth | Literal], world: dict[Literal, bool]) -> bool:
    """Only called when no part is `None`, or some part is `False`."""
    return all(world[p] if isinstance(p, tuple) else p for p in ps)


def resolve(case: Case, on: dict[str, bool]) -> tuple[str, set[tuple[str, str]]]:
    """One completion's verdict and basis (due2-workflows.md §6.1 to §6.4)."""
    cands = {r.name for r in case.rules if r.permit and on[r.name]}
    forbids = {r.name for r in case.rules if not r.permit and on[r.name]}
    void = case.conflict == "invalid" and bool(cands) and bool(forbids)
    if void or (case.conflict == "prohibit" and forbids):
        cands = set[str]()
    if void or (case.conflict == "perm" and cands):
        forbids = set[str]()
    if forbids:
        return "Deny", {(f, "prohibition") for f in forbids}
    if cands:
        return "Permit", {(c, "permission") for c in cands}
    return "NotApplicable", set()


def declined(case: Case) -> bool:
    """Some `u` constraint part belongs to a `u` atom (applies.lp, `unsupported_part/1`)."""
    return any(
        finding(parts(case, r)) is None and any(tree_value(case, t) is None for t in r.constraints)
        for r in case.rules
    )


def oracle(case: Case) -> Obj:
    if declined(case):
        return {"unsupported": "completion"}
    ps = {r.name: parts(case, r) for r in case.rules}
    lits = sorted({p for v in ps.values() for p in v if isinstance(p, tuple)})

    def run(world: dict[Literal, bool]) -> tuple[str, set[tuple[str, str]]]:
        return resolve(case, {n: applies(p, world) for n, p in ps.items()})

    worlds = [
        dict(zip(lits, vals, strict=True))
        for vals in itertools.product((False, True), repeat=len(lits))
    ]
    results = [run(w) for w in worlds]
    verdicts = {v for v, _ in results}
    out: Obj = {}
    find = {n: finding(p) for n, p in ps.items()}
    if len(verdicts) == 1:
        out["verdict"] = verdicts.pop()
        common = results[0][1].intersection(*(b for _, b in results[1:]))
        out["verdict_basis"] = [{"ref": EX + n, "role": role} for n, role in sorted(common)]
    else:
        out["verdict"] = "Indeterminate"
        out["verdict_basis"] = [{"ref": EX + n, "role": "unknown"} for n in unknown(case)]
        out["verdict_range"] = {
            "low": min(verdicts, key=CHAIN.index),
            "high": max(verdicts, key=CHAIN.index),
        }
    out["eliminated"] = eliminations(case, find)
    return {"output": out}


def unknown(case: Case) -> list[str]:
    """The `u` rules that read a pivotal literal: one whose flip alone moves the verdict."""
    ps = {r.name: parts(case, r) for r in case.rules}
    lits = sorted({p for v in ps.values() for p in v if isinstance(p, tuple)})

    def verdict(world: dict[Literal, bool]) -> str:
        return resolve(case, {n: applies(p, world) for n, p in ps.items()})[0]

    worlds = [
        dict(zip(lits, vals, strict=True))
        for vals in itertools.product((False, True), repeat=len(lits))
    ]
    pivotal = {lit for w in worlds for lit in lits if verdict(w) != verdict({**w, lit: not w[lit]})}
    return sorted(
        n
        for n, p in ps.items()
        if finding(p) is None and any(q in pivotal for q in p if isinstance(q, tuple))
    )


def eliminations(case: Case, find: dict[str, Truth]) -> list[Json]:
    """Over the findings (due2-workflows.md §3.5, §6.2; decisions/0011 #4): t removes, t or u is removed."""
    rules = {r.name: r for r in case.rules}
    # explain.lp's may_apply and surely_applies: t or u can be removed, only t removes.
    removable = {n for n, f in find.items() if f is not False}
    removers = {n for n, f in find.items() if f is True}
    rows: set[tuple[str, str]] = set()
    if case.conflict == "prohibit":
        rows = {
            (x, y) for x in removable if rules[x].permit for y in removers if not rules[y].permit
        }
    elif case.conflict == "perm":
        rows = {
            (x, y) for x in removable if not rules[x].permit for y in removers if rules[y].permit
        }
    elif any(rules[y].permit for y in removers) and any(not rules[y].permit for y in removers):
        rows = {(x, y) for x in removable for y in removers if x != y}
    return [{"ref": EX + x, "by": EX + y, "rule": case.conflict} for x, y in sorted(rows)]


# --- the differential ---

# A t candidate, a u candidate whose literal moves nothing, and a u forbid whose literal does:
# only the forbid is `unknown` (0011 #1). Random draws reach this shape in a few percent.
T, ALICE, BOB = (
    Rule("r0", True, "use", "a", None),
    Rule("r1", True, "use", "a", "alice"),
    Rule("r2", False, "use", "a", "bob"),
)


def eq(k: int) -> Leaf:
    return Leaf(k, "eq")


def constrained(tree: Tree) -> Case:
    """One permission under `tree`, with ex:o0 = 1 and ex:o1 = 2."""
    return Case(
        "perm", (Rule("r0", True, "use", "a", None, (tree,)),), "use", "a", None, (1, 2, None)
    )


EXAMPLES = [
    Case("prohibit", (T, ALICE, BOB), "use", "a", None),
    Case("invalid", (T, ALICE, BOB), "use", "a", None),
    # Two atoms read one literal, target(a): their completions are correlated (0012 #1).
    Case(
        "perm",
        (Rule("r0", True, "use", "a", None), Rule("r1", False, "use", "a", None)),
        "use",
        None,
        None,
    ),
    # Each tree changes its value if its connective is misread: and as or, or as and, not as
    # the identity, xone as or.
    constrained(Node("and", (eq(0), eq(1)), False)),
    constrained(Node("or", (Leaf(0, "neq"), eq(0)), True)),
    constrained(Node("not", (eq(0),), False)),
    constrained(Node("xone", (eq(0), Leaf(1, "gt")), False)),
    # A u leaf under a connective that decides anyway: f and u is f, t or u is t.
    constrained(Node("and", (eq(1), eq(2)), True)),
    constrained(Node("or", (eq(0), eq(2)), False)),
    # A u constraint part of a u atom: the completion decline (#48).
    constrained(eq(2)),
]


def check(interp: Interpreter, case: Case) -> None:
    reply = interp.reply(render(case))
    got = reply.get("output")
    if isinstance(got, dict):
        reply = {
            "output": {
                k: v for k, v in got.items() if k not in ("frontier", "obligations", "exact")
            }
        }
    assert reply == oracle(case)


def differential(interp: Interpreter, config: settings) -> Callable[[], None]:
    """The differential against `interp`, on the examples and then on generated cases."""

    @config
    @given(cases())
    def run(case: Case) -> None:
        check(interp, case)

    for c in EXAMPLES:
        run = example(c)(run)
    return run


def test_matches_brute_force(interpreter: Interpreter) -> None:
    differential(interpreter, settings(max_examples=400, deadline=None))()


# --- mutation (#47) ---

MUTANTS: dict[str, tuple[str, list[tuple[str, str]]]] = {
    # Every literal pivotal: a u atom whose literal moves nothing is `unknown` too.
    "flip-constraint-deleted": (
        "pivot.lp",
        [(":- verdict(c, Verdict), verdict(flip, Verdict).", "")],
    ),
    # A literal per part, not per field and value: shared literals become independent.
    "literal-per-part": (
        "completion.lp",
        [
            ("lit_of(part(X, target), target(T))", "lit_of(part(X, target), target(X, T))"),
            (
                "lit_of(part(X, party(F)), party(F, Party))",
                "lit_of(part(X, party(F)), party(X, F, Party))",
            ),
        ],
    ),
    "u-atoms-remove": (
        "explain.lp",
        [
            (
                "surely_applies(X) :- holds(applies(X), t).",
                "surely_applies(X) :- holds(applies(X), t).\nsurely_applies(X) :- holds(applies(X), u).",
            )
        ],
    ),
    "and-or-swapped": (
        "compare.lp",
        [
            ("conn(C, and), N = #min { 2;", "conn(C, and), N = #max { 0;"),
            ("conn(C, or), N = #max { 0;", "conn(C, or), N = #min { 2;"),
        ],
    ),
    "not-as-identity": (
        "compare.lp",
        [("crank(C, 2 - N) :- conn(C, negation)", "crank(C, N) :- conn(C, negation)")],
    ),
    "xone-without-negations": (
        "compare.lp",
        [
            (
                "{ M, self : crank(D, M); 2 - M2, D2 : member(C, D2), D2 != D, crank(D2, M2) }",
                "{ M, self : crank(D, M) }",
            )
        ],
    ),
}


@pytest.mark.parametrize("name", sorted(MUTANTS))
def test_differential_kills_mutant(name: str) -> None:
    file, edits = MUTANTS[name]
    programs = load_programs()
    for old, new in edits:
        assert old in programs[file], f"{file} no longer has {old!r}"
        programs[file] = programs[file].replace(old, new)
    mutant = differential(
        Interpreter(INIT, programs),
        settings(
            max_examples=100, deadline=None, database=None, phases=(Phase.explicit, Phase.generate)
        ),
    )
    with pytest.raises((AssertionError, BaseExceptionGroup)):
        mutant()


# --- measurement (#47) ---


def shapes(case: Case) -> Iterator[str]:
    """The shapes the differential relies on that `case` has."""
    yield f"conflict {case.conflict}"
    expected = oracle(case)
    out = expected.get("output")
    if not isinstance(out, dict):
        yield "completion decline"
        return
    u_rules = [r.name for r in case.rules if finding(parts(case, r)) is None]
    if out["verdict"] == "Indeterminate" and len(unknown(case)) < len(u_rules):
        yield "Indeterminate with a non-pivotal u atom"
    reads = Counter(
        p
        for r in case.rules
        if finding(parts(case, r)) is None
        for p in set(parts(case, r))
        if isinstance(p, tuple)
    )
    if any(n > 1 for n in reads.values()):
        yield "two u atoms sharing a literal"
    tops = [t for r in case.rules for t in r.constraints if isinstance(t, Leaf)]
    if len(tops) > len(set(tops)):
        yield "constraint parts sharing a key"
    if any(
        tree_value(case, t) is not None and any(case.params[x.operand] is None for x in leaves(t))
        for r in case.rules
        for t in r.constraints
    ):
        yield "u leaf under a deciding connective"


def test_generator_reaches_each_shape() -> None:
    seen: Counter[str] = Counter()

    @settings(max_examples=400, deadline=None, database=None, derandomize=True)
    @given(cases())
    def tally(case: Case) -> None:
        seen.update(shapes(case))

    tally()
    wanted = {f"conflict {c}" for c in ("prohibit", "perm", "invalid")} | {
        "completion decline",
        "Indeterminate with a non-pivotal u atom",
        "two u atoms sharing a literal",
        "constraint parts sharing a key",
        "u leaf under a deciding connective",
    }
    assert {s: seen[s] for s in wanted if seen[s] == 0} == {}, seen
