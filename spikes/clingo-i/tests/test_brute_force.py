"""The brute-force differential (DESIGN.md § Tests, correctness-strategy.md §4.1).

Over generated policies of permissions and prohibitions, with an absent target or an unnamed
assignee, a Python oracle enumerates every completion of the variables, flips each variable
alone, and derives the verdict, the basis, the eliminations, the `unknown` atoms, the range,
and the unknown parts (due2-workflows.md §5.2, §6.1 to §6.4; decisions/0011, decisions/0016).
It reads the generated rules, not the program's facts, and shares only the spec's completion
key with it.

A rule may carry constraint trees over operands, each read from a request parameter or from a
state property. A request parameter may be absent, so its read is `missing`; a state property
may have no fact, so its read is `unresolved` (due2-profiles.md §3). The oracle gives a tree
its value by supervaluation: it tries `t` and `f` for each leaf occurrence that is `u`, each on
its own, and the tree is `u` when the tries disagree. That is strong Kleene logic for a tree
whose leaf occurrences are independent (due2-workflows.md §5.2), computed without the
program's ranks.

Completion follows decisions/0016. Every leaf compares its operand with the right operand 1, so
two `unresolved` leaves with one operand and one operator, or with complementary operators,
read one variable (due2-workflows.md §6.4). A `missing` leaf, and an absent target or party, is
opaque: it stays `u` in every completion. Under a completion, a tree takes its supervaluation
with its paired leaves set, and an atom whose parts still leave it `u` takes the value of a
variable of its own.

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
from clingo import Control
from hypothesis import Phase, assume, example, given, settings
from hypothesis import strategies as st

from clingo_i.interpret import CHAIN, SOLVE_2, Interpreter, load_programs
from clingo_i.json_types import Json, Obj
from tests.conftest import INIT, PREFIXES, vector

EX = "https://example.org/"
XSD_INTEGER = "http://www.w3.org/2001/XMLSchema#integer"
ACTIONS = ("use", "play")  # play ⊑ use in the test core (conftest.INIT)
PARTIES = ("alice", "bob")
OPERANDS = 3  # ex:o0 to ex:o2, each read from the request parameter or state property ex:oK
ODRL = "http://www.w3.org/ns/odrl/2/"
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
    params: tuple[int | None, ...] = (None,) * OPERANDS  # None: no parameter, or no fact
    state: tuple[bool, ...] = (False,) * OPERANDS  # True: read from the state, not the request


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
        # None twice: an unknown operand is paired only when it also reads the state.
        tuple(draw(st.sampled_from((None, None, 0, 1, 2))) for _ in range(OPERANDS)),
        # Every operand from the state in half the cases: a variable two rules share needs two
        # paired leaves, and sharing is otherwise a few cases in a thousand.
        (True,) * OPERANDS
        if draw(st.booleans())
        else tuple(draw(st.booleans()) for _ in range(OPERANDS)),
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
    # Each operand is bound in the policy to the parameter or property of its own name.
    lines.extend(
        f"ex:o{k} dprod:operandSource dprod:{'stateSource' if state else 'requestSource'} ;"
        f" dprod:operandProperty ex:o{k} ."
        for k, state in enumerate(case.state)
    )
    parties: Obj = {"odrl:assignee": f"ex:{case.assignee}"} if case.assignee else {}
    values: Obj = {
        f"ex:o{k}": {"@value": str(p), "@type": XSD_INTEGER}
        for k, p in enumerate(case.params)
        if p is not None
    }
    params: Obj = {k: x for k, x in values.items() if not case.state[int(k[4:])]}
    facts: Obj = {
        k: {"status": "resolved", "values": [x]}
        for k, x in values.items()
        if case.state[int(k[4:])]
    }
    v = vector(
        PREFIXES + "\n".join(lines) + "\n",
        request={"action": f"odrl:{case.action}", "parties": parties, "params": params},
        sotw={"facts": facts},
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


# The positive operator and the polarity of each operator: a complement reads its base's
# variable negated (due2-workflows.md §6.4).
POLARITY: dict[str, tuple[str, bool]] = {
    "eq": ("eq", True),
    "neq": ("eq", False),
    "lt": ("lt", True),
    "gteq": ("lt", False),
    "lteq": ("lteq", True),
    "gt": ("lteq", False),
}


def leaf_literal(leaf: Leaf) -> Literal:
    """A paired leaf's variable: its operand and positive operator. Scope and right operand
    agree for every generated leaf."""
    return (f"o{leaf.operand}", POLARITY[leaf.op][0])


def paired(case: Case, leaf: Leaf) -> bool:
    """The leaf reads a state property with no fact: `unresolved`, so it is paired."""
    return case.params[leaf.operand] is None and case.state[leaf.operand]


def tree_value(case: Case, tree: Tree, world: dict[Literal, bool] | None = None) -> Truth:
    """The tree's value by supervaluation over its leaf occurrences that are `u`.

    With `world`, a paired leaf whose variable the world has takes that value first, so only
    the opaque leaves, and the paired leaves no atom reads, are tried.
    """
    known: list[Truth] = []
    for leaf in leaves(tree):
        p = case.params[leaf.operand]
        v = None if p is None else OPERATORS[leaf.op](p, 1)
        if v is None and world is not None and paired(case, leaf):
            lit = world.get(leaf_literal(leaf))
            v = None if lit is None else lit == POLARITY[leaf.op][1]
        known.append(v)
    gaps = [i for i, k in enumerate(known) if k is None]
    results: set[bool] = set()
    for fill in itertools.product((False, True), repeat=len(gaps)):
        values = list(known)
        for i, b in zip(gaps, fill, strict=True):
            values[i] = b
        results.add(classical(tree, iter(bool(v) for v in values)))
    return results.pop() if len(results) == 1 else None


@dataclass(frozen=True)
class Open:
    """A `u` constraint part of a rule."""

    case: Case
    tree: Tree

    def literals(self) -> Iterator[Literal]:
        """The variables of the paired open leaves."""
        return (leaf_literal(x) for x in open_leaves(self.case, self.tree) if paired(self.case, x))

    def opaque(self) -> bool:
        """Some open leaf is opaque, so the tree can stay `u` in a completion."""
        return any(not paired(self.case, x) for x in open_leaves(self.case, self.tree))

    def value(self, world: dict[Literal, bool]) -> Truth:
        return tree_value(self.case, self.tree, world)


def open_leaves(case: Case, tree: Tree) -> Iterator[Leaf]:
    """The leaves on a path of `u` nodes from the root: the leaves completion reads."""
    if tree_value(case, tree) is not None:
        return
    match tree:
        case Leaf():
            yield tree
        case Node(_, members, _):
            for m in members:
                yield from open_leaves(case, m)


type Part = Truth | Open


def parts(case: Case, r: Rule) -> list[Part]:
    """A rule's parts: a known truth, `None` for an absent target or party, or a `u` tree."""
    out: list[Part] = [case.action == r.action or r.action == "use"]
    out.append(None if case.target is None else case.target == r.target)
    if r.assignee is not None:
        out.append(None if case.assignee is None else case.assignee == r.assignee)
    out.extend(Open(case, t) if (v := tree_value(case, t)) is None else v for t in r.constraints)
    return out


def kleene_and(vs: list[Truth]) -> Truth:
    if any(v is False for v in vs):
        return False
    return None if any(v is None for v in vs) else True


def finding(ps: list[Part]) -> Truth:
    """Kleene conjunction: an absent field or an open tree is u."""
    return kleene_and([None if isinstance(p, Open) else p for p in ps])


def fin(name: str) -> Literal:
    """The variable of rule `name`'s finding, for when an opaque part leaves it `u`."""
    return ("fin", name)


def reads(name: str, ps: list[Part]) -> set[Literal]:
    """The variables a `u` atom reads: its paired open leaves, and its own when it has an
    opaque part. An `f` atom reads none."""
    if finding(ps) is not None:
        return set()
    out: set[Literal] = set()
    for p in ps:
        if isinstance(p, Open):
            out.update(p.literals())
    if any(p is None or (isinstance(p, Open) and p.opaque()) for p in ps):
        out.add(fin(name))
    return out


def applies(name: str, ps: list[Part], world: dict[Literal, bool]) -> bool:
    if (f := finding(ps)) is not None:
        return f
    v = kleene_and([p.value(world) if isinstance(p, Open) else p for p in ps])
    return world[fin(name)] if v is None else v


def worlds(ps: dict[str, list[Part]]) -> tuple[list[Literal], list[dict[Literal, bool]]]:
    """The variables the u atoms read, and every completion of them."""
    lits = sorted(set[Literal]().union(*(reads(n, p) for n, p in ps.items())))
    return lits, [
        dict(zip(lits, vals, strict=True))
        for vals in itertools.product((False, True), repeat=len(lits))
    ]


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


def oracle(case: Case) -> Obj:
    ps = {r.name: parts(case, r) for r in case.rules}

    def run(world: dict[Literal, bool]) -> tuple[str, set[tuple[str, str]]]:
        return resolve(case, {n: applies(n, p, world) for n, p in ps.items()})

    results = [run(w) for w in worlds(ps)[1]]
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
    out["unknown_parts"] = unknown_parts(case)
    return {"output": out}


def unknown(case: Case) -> list[str]:
    """The `u` rules that read a pivotal variable: one whose flip alone moves the verdict."""
    ps = {r.name: parts(case, r) for r in case.rules}

    def verdict(world: dict[Literal, bool]) -> str:
        return resolve(case, {n: applies(n, p, world) for n, p in ps.items()})[0]

    lits, ws = worlds(ps)
    pivotal = {lit for w in ws for lit in lits if verdict(w) != verdict({**w, lit: not w[lit]})}
    return sorted(n for n, p in ps.items() if reads(n, p) & pivotal)


def unknown_parts(case: Case) -> list[Json]:
    """Every `u` part of every rule whose finding is not `f` (decisions/0016 #3, amendment).

    An absent target or party is `missing`, and so is a leaf whose parameter is absent; a leaf
    whose property has no fact is `unresolved`. A `u` leaf of a `t` rule, under a node another
    member decides, is a row too. The rows are sorted by full IRI, as the reply's are.
    """
    rows: set[tuple[str, str, str]] = set()
    for r in case.rules:
        if finding(parts(case, r)) is False:
            continue
        if case.target is None:
            rows.add((EX + r.name, ODRL + "target", "missing"))
        if r.assignee is not None and case.assignee is None:
            rows.add((EX + r.name, ODRL + "assignee", "missing"))
        for leaf in (x for t in r.constraints for x in leaves(t)):
            if case.params[leaf.operand] is None:
                status = "unresolved" if case.state[leaf.operand] else "missing"
                rows.add((EX + r.name, f"{EX}o{leaf.operand}", status))
    return [{"ref": ref, "input": i, "status": st} for ref, i, st in sorted(rows)]


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

# A t candidate, a u candidate whose variable moves nothing, and a u forbid whose variable does:
# only the forbid is `unknown` (0011 #1). Random draws reach this shape in a few percent.
T, ALICE, BOB = (
    Rule("r0", True, "use", "a", None),
    Rule("r1", True, "use", "a", "alice"),
    Rule("r2", False, "use", "a", "bob"),
)


def eq(k: int) -> Leaf:
    return Leaf(k, "eq")


# Operands for `constrained`: ex:o2 from the state, so `unresolved`, or from the request, so
# `missing`.
PAIRED = (False, False, True)
OPAQUE = (False, False, False)


def constrained(tree: Tree, state: tuple[bool, ...] = PAIRED) -> Case:
    """One permission under `tree`, with ex:o0 = 1, ex:o1 = 2, and ex:o2 unknown."""
    return Case(
        "perm",
        (Rule("r0", True, "use", "a", None, (tree,)),),
        "use",
        "a",
        None,
        (1, 2, None),
        state,
    )


def lt_or_gteq(state: tuple[bool, ...]) -> Case:
    """decisions/0016's example: two permissions, ex:o2 lt 1 and ex:o2 gteq 1."""
    return Case(
        "perm",
        (
            Rule("r0", True, "use", "a", None, (Leaf(2, "lt"),)),
            Rule("r1", True, "use", "a", None, (Leaf(2, "gteq"),)),
        ),
        "use",
        "a",
        None,
        (None,) * OPERANDS,
        state,
    )


EXAMPLES = [
    Case("prohibit", (T, ALICE, BOB), "use", "a", None),
    Case("invalid", (T, ALICE, BOB), "use", "a", None),
    # Two atoms on one absent target: the target is missing, so opaque, and each atom has a
    # variable of its own (decisions/0016 #2). Shared, the range would stop at NotApplicable.
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
    # A u leaf, and two leaves that read one variable, positively and negatively: the tree is u
    # (Kleene), but t in every completion. Opaque, the two leaves are independent and the tree
    # stays u, so the atom's own variable decides it (decisions/0016 § L9).
    constrained(eq(2)),
    constrained(Node("or", (eq(2), Leaf(2, "neq")), False)),
    constrained(eq(2), OPAQUE),
    constrained(Node("or", (eq(2), Leaf(2, "neq")), False), OPAQUE),
    # Two rules that read one variable with opposite polarity: one or the other applies. With
    # the operand missing, neither need apply (decisions/0016's example).
    lt_or_gteq(PAIRED),
    lt_or_gteq(OPAQUE),
    # An opaque leaf and a paired one in one tree: where the paired leaf is f, the tree is u
    # in the world, and the atom's own variable decides it.
    Case(
        "perm",
        (
            Rule("r0", True, "use", "a", None, (Node("or", (eq(1), eq(2)), False),)),
            Rule("r1", True, "use", "a", None, (Leaf(2, "neq"),)),
        ),
        "use",
        "a",
        None,
        (None,) * OPERANDS,
        PAIRED,
    ),
    # An f atom (a foreign action) with an absent target and a missing leaf: its u parts are
    # not reported, because an index may skip it (decisions/0016, amendment).
    Case(
        "prohibit",
        (Rule("r0", True, "play", "a", None, (eq(0),)), Rule("r1", False, "use", "b", None)),
        "use",
        None,
        None,
    ),
    # A u leaf under a t node, beside an open leaf with the same variable: only the open leaf
    # is read.
    Case(
        "prohibit",
        (
            Rule("r0", True, "use", "a", None, (Node("or", (eq(0), eq(2)), False), eq(2))),
            Rule("r1", False, "use", "a", "bob"),
        ),
        "use",
        "a",
        None,
        (1, None, None),
        PAIRED,
    ),
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


# --- the enumeration against fixed solves (#48) ---

CHOICE = "{ assigned(c, L, t); assigned(c, L, f) } = 1 :- var(L)."


def shown_sets(program: str, mode: str = "auto") -> list[frozenset[str]]:
    """The shown atoms of every model of `program`."""
    ctl = Control(["0", f"--enum-mode={mode}"], logger=lambda _code, _msg: None)
    ctl.add("base", [], program)
    ctl.ground([("base", [])])
    models: list[frozenset[str]] = []
    ctl.solve(on_model=lambda m: models.append(frozenset(map(str, m.symbols(shown=True)))))
    return models


def test_enumeration_matches_fixed_solves(interpreter: Interpreter) -> None:
    """One answer set per completion, and the cautious reply is the fold of fixed solves.

    Without it, the differential could pass while the choice rule admits a model that is not a
    completion, or misses one, if the oracle made the same mistake; and the reply could read
    clingo's cautious enumeration wrongly. The brute force solves the evaluation layer once per
    assignment, with every variable a fact and no choice rule.
    """
    programs = load_programs()
    assert CHOICE in programs["completion.lp"]
    program = "\n".join(programs[f] for f in SOLVE_2)
    fixed = program.replace(CHOICE, "")

    @settings(max_examples=150, deadline=None)
    @given(cases())
    def run(case: Case) -> None:
        v = render(case)
        reply = interpreter.reply(v)
        assert "output" in reply, reply
        text = interpreter.facts(v)
        ctl = Control([], logger=lambda _code, _msg: None)
        ctl.add("base", [], text + "\n" + program)
        ctl.ground([("base", [])])
        variables: list[str] = []
        ctl.solve(
            on_model=lambda m: variables.extend(
                str(a.arguments[0]) for a in m.symbols(atoms=True) if a.match("var", 1)
            )
        )
        assume(len(variables) <= 6)
        enumerated = shown_sets(text + "\n" + program)
        assert len(enumerated) == 2 ** len(variables)
        solves: list[frozenset[str]] = []
        for values in itertools.product(("t", "f"), repeat=len(variables)):
            facts = "".join(
                f"assigned(c, {lit}, {val})." for lit, val in zip(variables, values, strict=True)
            )
            models = shown_sets(text + "\n" + facts + "\n" + fixed)
            assert len(models) == 1, models
            solves.extend(models)
        assert sorted(map(sorted, enumerated)) == sorted(map(sorted, solves))
        common = solves[0].intersection(*solves[1:])
        verdicts = {a for s in solves for a in s if a.startswith("verdict(")}
        out = reply["output"]
        assert isinstance(out, dict)
        assert (out["verdict"] == "Indeterminate") == (len(verdicts) > 1)
        assert shown_sets(text + "\n" + program, "cautious")[-1] == common

    run()


# --- mutation (#47) ---

MUTANTS: dict[str, tuple[str, list[tuple[str, str]]]] = {
    # Every variable pivotal: a u atom whose variable moves nothing is `unknown` too.
    "flip-constraint-deleted": (
        "pivot.lp",
        [(":- verdict(c, Verdict), verdict(flip, Verdict).", "")],
    ),
    # A missing leaf paired as if unresolved: the pairing decisions/0016 removed.
    "missing-paired": (
        "completion.lp",
        [
            (
                "opaque_leaf(C) :- leaf_status(C, S), S != unresolved.",
                "opaque_leaf(C) :- leaf_status(C, S), S != unresolved, S != missing.",
            ),
            ("open(C), leaf_status(C, unresolved), scope", "open(C), not opaque_leaf(C), scope"),
        ],
    ),
    # One variable for every opaque atom: their completions become correlated.
    "opaque-atoms-share-a-variable": (
        "completion.lp",
        [
            ("var(fin(X)) :- opaque_atom(X).", "var(fin(0)) :- opaque_atom(X)."),
            ("reads(X, fin(X)) :- opaque_atom(X).", "reads(X, fin(0)) :- opaque_atom(X)."),
            ("assigned(W, fin(X), V).", "assigned(W, fin(0), V)."),
        ],
    ),
    # An opaque leaf read as f in each world: unknown as false.
    "opaque-leaf-as-f": (
        "completion.lp",
        [
            (
                "crank_in(W, C, 1) :- world(W), open(C), opaque_leaf(C).",
                "crank_in(W, C, 0) :- world(W), open(C), opaque_leaf(C).",
            )
        ],
    ),
    # The absent target of an f atom reported: the reply would depend on the index.
    "unknown-parts-of-f-atoms": (
        "explain.lp",
        [
            (
                "holds(part(X, target), u),\n    not holds(applies(X), f).",
                "holds(part(X, target), u).",
            )
        ],
    ),
    # The u leaves of a t atom dropped: only u atoms report their leaves.
    "unknown-parts-of-u-atoms-only": (
        "explain.lp",
        [
            (
                "prop(Op, Prop),\n    not holds(applies(X), f).",
                "prop(Op, Prop), holds(applies(X), u).",
            )
        ],
    ),
    # One variable per leaf: leaves with the same key become independent.
    "variable-per-leaf": (
        "completion.lp",
        [("leaf_lit(C, cons(D), Pol) :-", "leaf_lit(C, cons(C), Pol) :- D = C,")],
    ),
    # A complement read as its base: `neq` as `eq`.
    "polarity-ignored": (
        "completion.lp",
        [
            (
                "crank_in(W, C, 2 - N) :- leaf_lit(C, L, neg)",
                "crank_in(W, C, N) :- leaf_lit(C, L, neg)",
            )
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
    assert isinstance(out, dict)
    u_rules = [r.name for r in case.rules if finding(parts(case, r)) is None]
    if out["verdict"] == "Indeterminate" and len(unknown(case)) < len(u_rules):
        yield "Indeterminate with a non-pivotal u atom"
    shared = Counter(lit for r in case.rules for lit in reads(r.name, parts(case, r)))
    if any(n > 1 for n in shared.values()):
        yield "two u atoms sharing a variable"
    if any(lit[0] == "fin" for lit in shared):
        yield "an atom with a variable of its own"
    if any(
        isinstance(p, Open) and p.opaque() and any(True for _ in p.literals())
        for r in case.rules
        for p in parts(case, r)
    ):
        yield "an open tree with an opaque and a paired leaf"
    if case.target is None and any(finding(parts(case, r)) is False for r in case.rules):
        yield "an f atom on an absent target"
    polarities: dict[Literal, set[bool]] = {}
    for r in case.rules:
        if finding(parts(case, r)) is not None:
            continue
        for t in r.constraints:
            for leaf in open_leaves(case, t):
                if paired(case, leaf):
                    polarities.setdefault(leaf_literal(leaf), set()).add(POLARITY[leaf.op][1])
    if any(len(p) == 2 for p in polarities.values()):
        yield "open leaves reading one variable with both polarities"
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
        "open leaves reading one variable with both polarities",
        "Indeterminate with a non-pivotal u atom",
        "two u atoms sharing a variable",
        "an atom with a variable of its own",
        "an open tree with an opaque and a paired leaf",
        "an f atom on an absent target",
        "constraint parts sharing a key",
        "u leaf under a deciding connective",
    }
    assert {s: seen[s] for s in wanted if seen[s] == 0} == {}, seen
