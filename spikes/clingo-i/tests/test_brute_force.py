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

The unknown parts are read from an explicit DNF of each rule's trees, unsimplified, whose
disjuncts are W1's atoms (due2-profiles.md §5): a `u` leaf is named only when it lies in a
disjunct that is not `f`. The program finds the same leaves by walking the tree (`live/4`), so
the generator plants, in a quarter of the cases, a branch that is `f` whatever its subtree.

The duty differential extends the generated policies with duties (due2-workflows.md §5.3, §6;
decisions/0018, decisions/0019). Each permission may require some of three duties, and the
policy may carry a root obligation, with `violations` set to `ignore` or `deny`. A duty may
have a guard tree, a passed deadline, and one evidence row whose actor is alice or bob. With
no request subject, the actor check of a duty borne by the subject is `u`. A guard tree is
completed as a rule's tree is, so a guard leaf with a rule leaf's key reads its variable; an
`owed` or `in_force` still `u`, and a `fulfilled` that is `u`, takes a variable of its own.
The oracle then derives closure, the candidates, the frontier
(listed only when every completion agrees, due2-workflows.md §6.3), the verdict, its range, the
basis, and the duties named `unknown`. Half the generated cases make every finding known, so
that a definite Pending, a frontier of two alternatives, and a Deny by the obligation occur
often enough to be tested.

Each differential runs as `COPIES` parametrized copies, each with its own random seed, so
that pytest-xdist runs them on separate workers (#82); a run makes `COPIES` times each draw
count.

The mutation tests run the same differentials against programs with one rule changed, and
assert that they fail (#47, #49). The duty examples alone kill each duty mutant. The
measurement tests assert that the generators reach each shape the differentials rely on.
Generated draws do not expose every mutant on their own (tests/measure_mutants.py); the
bounded-exhaustive spaces of test_spaces.py do, with the same oracle (#44).
"""

from __future__ import annotations

import contextlib
import itertools
import operator
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace

import pytest
from clingo import Control
from hypothesis import Phase, assume, example, given, seed, settings
from hypothesis import strategies as st

from clingo_i.interpret import CHAIN, SOLVE_2, Interpreter, load_programs
from clingo_i.json_types import Json, Obj
from tests.conftest import DUTY_INIT, INIT, PREFIXES, vector

EX = "https://example.org/"
XSD_INTEGER = "http://www.w3.org/2001/XMLSchema#integer"
ACTIONS = ("use", "play")  # play ⊑ use in the test core (conftest.INIT)
PARTIES = ("alice", "bob")
OPERANDS = 3  # ex:o0 to ex:o2, each read from the request parameter or state property ex:oK
COPIES = 4  # parametrized copies of each differential, with a random seed each
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
def cases(draw: st.DrawFn, dead: bool = False) -> Case:
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
    case = Case(
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
    # With `dead`, a quarter of the cases get a branch that only f atoms read: drawn freely, a
    # u leaf in such a branch is rare. The duty generator draws without it.
    return dead_branch(draw, case) if dead and draw(st.integers(0, 3)) == 0 else case


def dead_branch(draw: st.DrawFn, case: Case) -> Case:
    """`case` with one rule's first constraint `keep` replaced by `or(dead, keep)`.

    `dead` is `f` whatever its subtree `sub` is: `and(lf, sub)`, `not(or(lt, sub))`, or
    `xone(lt, lt, sub)`, where `lf` and `lt` are leaves, on an operand with a value, that are
    `f` and `t`. Each DNF disjunct that holds a leaf of `sub` is then `f`, so a `u` leaf of
    `sub` that `keep` does not also read is not an unknown part (due2-workflows.md §3.5).
    """
    known = [k for k, p in enumerate(case.params) if p is not None]
    if not known:
        return case
    k = draw(st.sampled_from(known))
    value = case.params[k]
    assert value is not None
    false, true = (
        Leaf(k, draw(st.sampled_from([op for op, f in OPERATORS.items() if f(value, 1) is b])))
        for b in (False, True)
    )
    sub = draw(TREES)
    dead = draw(
        st.sampled_from(
            (
                Node("and", (false, sub), False),
                Node("not", (Node("or", (true, sub), True),), False),
                Node("xone", (true, true, sub), True),
            )
        )
    )
    i = draw(st.integers(0, len(case.rules) - 1))
    rule = case.rules[i]
    rest = rule.constraints or (draw(TREES),)
    tree = Node("or", (dead, rest[0]), draw(st.booleans()))
    rules = (*case.rules[:i], replace(rule, constraints=(tree, *rest[1:])), *case.rules[i + 1 :])
    return replace(case, rules=rules)


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


type Disjunct = frozenset[tuple[Leaf, bool]]


def dnf(tree: Tree, positive: bool = True) -> set[Disjunct]:
    """The tree's disjunctive normal form, as W1 makes it (due2-workflows.md §4 stage 2).

    Each disjunct is a set of leaves, each read positively or negated. Negation is pushed in by
    De Morgan, and an `xone` is the disjunction, over its members, of that member conjoined
    with the negation of every other; a negated `xone` is expanded first (due2-profiles.md §5).
    The product is distributed in full: a disjunct that holds a leaf and its negation is kept,
    because strong Kleene logic does not make it `f`.
    """

    def product(*parts: set[Disjunct]) -> set[Disjunct]:
        return {frozenset().union(*ds) for ds in itertools.product(*parts)}

    match tree:
        case Leaf():
            return {frozenset({(tree, positive)})}
        case Node("not", (m,), _):
            return dnf(m, not positive)
        case Node("xone", members, _):
            terms = [
                [dnf(m, (m_i == d_i) == positive) for m_i, m in enumerate(members)]
                for d_i in range(len(members))
            ]
            if positive:
                return set[Disjunct]().union(*(product(*t) for t in terms))
            return product(*(set[Disjunct]().union(*t) for t in terms))
        case Node(conn, members, _):
            each = [dnf(m, positive) for m in members]
            if (conn == "and") == positive:
                return product(*each)
            return set[Disjunct]().union(*each)


def disjunct_value(case: Case, d: Disjunct) -> Truth:
    """The Kleene conjunction of the disjunct's leaves, each read with its polarity."""
    values: list[Truth] = []
    for leaf, positive in d:
        p = case.params[leaf.operand]
        values.append(None if p is None else OPERATORS[leaf.op](p, 1) == positive)
    if False in values:
        return False
    return None if None in values else True


def unknown_parts(case: Case) -> list[Json]:
    """Every `u` part of every rule whose finding is not `f` (decisions/0016 #3, amendment).

    An absent target or party is `missing`, and so is a leaf whose parameter is absent; a leaf
    whose property has no fact is `unresolved`. A rule's atoms are the disjuncts of its trees'
    DNF (`dnf`), so a `u` leaf is a row when it lies in a disjunct that is not `f`
    (due2-workflows.md §3.5). A rule's target, party, and trees are conjoined, and none is `f`
    when the rule is not, so each tree has a disjunct that is not `f`, and that disjunct
    combines with one from each other tree into an atom that is not `f`. A `u` leaf of a `t`
    rule, under a node another member decides, is a row too, as long as its disjunct is not
    `f`. The rows are sorted by full IRI, as the reply's are.
    """
    rows: set[tuple[str, str, str]] = set()
    for r in case.rules:
        if finding(parts(case, r)) is False:
            continue
        if case.target is None:
            rows.add((EX + r.name, ODRL + "target", "missing"))
        if r.assignee is not None and case.assignee is None:
            rows.add((EX + r.name, ODRL + "assignee", "missing"))
        live = (d for t in r.constraints for d in dnf(t) if disjunct_value(case, d) is not False)
        for leaf, _ in (x for d in live for x in d):
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
    # A u leaf that only f atoms read, in each shape: under an f and, under a negated or with
    # a t member, under an xone with two t members, and under the negation of an xone that is t
    # (a t member beside an f and). The t leaf beside it decides the rule, and the u leaf is not
    # named (#81).
    *(
        Case(
            "prohibit",
            (Rule("r0", True, "use", "a", None, (Node("or", (dead, eq(0)), False),)),),
            "use",
            "a",
            None,
            (1, 2, None),
            PAIRED,
        )
        for dead in (
            Node("and", (eq(1), eq(2)), False),
            Node("not", (Node("or", (eq(0), eq(2)), False),), False),
            Node("xone", (eq(0), eq(0), eq(2)), True),
            Node("not", (Node("xone", (eq(0), Node("and", (eq(1), eq(2)), False)), True),), False),
        )
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
    @given(cases(dead=True))
    def run(case: Case) -> None:
        check(interp, case)

    for c in EXAMPLES:
        run = example(c)(run)
    return run


@pytest.mark.parametrize("copy", range(COPIES))
def test_matches_brute_force(interpreter: Interpreter, copy: int) -> None:
    del copy
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


@pytest.mark.parametrize("copy", range(COPIES))
def test_enumeration_matches_fixed_solves(interpreter: Interpreter, copy: int) -> None:
    """One answer set per completion, and the cautious reply is the fold of fixed solves.

    Without it, the differential could pass while the choice rule admits a model that is not a
    completion, or misses one, if the oracle made the same mistake; and the reply could read
    clingo's cautious enumeration wrongly. The brute force solves the evaluation layer once per
    assignment, with every variable a fact and no choice rule.
    """
    del copy
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
    # One variable for every opaque finding: their completions become correlated.
    "opaque-atoms-share-a-variable": (
        "completion.lp",
        [
            ("var(fin(I)) :- opaque_item(I).", "var(fin(0)) :- opaque_item(I)."),
            ("reads(I, fin(I)) :- opaque_item(I).", "reads(I, fin(0)) :- opaque_item(I)."),
            ("assigned(W, fin(I), V).", "assigned(W, fin(0), V)."),
        ],
    ),
    # An opaque leaf read as f in each world: unknown as false.
    "opaque-leaf-as-f": (
        "completion.lp",
        [
            (
                "crank(W, C, 1) :- world(W), open(C), opaque_leaf(C).",
                "crank(W, C, 0) :- world(W), open(C), opaque_leaf(C).",
            )
        ],
    ),
    # The u parts of an f atom reported: the reply would depend on the index.
    "unknown-parts-of-f-atoms": (
        "explain.lp",
        [
            (
                "reported(applies(X)) :- atom(X), not holds(applies(X), f).",
                "reported(applies(X)) :- atom(X).",
            )
        ],
    ),
    # The u parts of a t atom dropped: only u atoms report their parts.
    "unknown-parts-of-u-atoms-only": (
        "explain.lp",
        [
            (
                "reported(applies(X)) :- atom(X), not holds(applies(X), f).",
                "reported(applies(X)) :- holds(applies(X), u).",
            )
        ],
    ),
    # Every u leaf of a reported finding named, as before #81: a leaf that only f atoms read is
    # named too.
    "u-leaf-of-f-atom-named": (
        "explain.lp",
        [
            (
                "conj(K, P), member(C, D),\n    not polar(W, D2, P, 0) : member(C, D2), D2 != D.",
                "conj(K, P), member(C, D).",
            )
        ],
    ),
    # A negation passes liveness on without flipping the polarity.
    "live-ignores-negation": (
        "explain.lp",
        [
            (
                "conn(C, negation), member(C, D), flip(P, Q).",
                "conn(C, negation), member(C, D), Q = P.",
            )
        ],
    ),
    # An xone term passes liveness on whatever its other members are.
    "live-xone-ignores-term": (
        "explain.lp",
        [
            (
                "xone_pol(C, D, G, Q),\n    not polar(W, H, R, 0) : xone_pol(C, D, H, R), H != G.",
                "xone_pol(C, D, G, Q).",
            )
        ],
    ),
    # A negated xone passes liveness on whatever its other negated terms are.
    "live-negated-xone-ignores-terms": (
        "explain.lp",
        [
            (
                "flip(R, Q),\n    not xone_term(W, C, D2, 2) : member(C, D2), D2 != D.",
                "flip(R, Q).",
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
                "crank(W, C, 2 - N) :- leaf_lit(C, L, neg)",
                "crank(W, C, N) :- leaf_lit(C, L, neg)",
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
            ("conn(C, and),\n    N = #min { 2;", "conn(C, and),\n    N = #max { 0;"),
            ("conn(C, or),\n    N = #max { 0;", "conn(C, or),\n    N = #min { 2;"),
        ],
    ),
    "not-as-identity": (
        "compare.lp",
        [
            (
                "crank(W, C, 2 - N) :- evaluates(W, C), conn(C, negation)",
                "crank(W, C, N) :- evaluates(W, C), conn(C, negation)",
            )
        ],
    ),
    "xone-without-negations": (
        "compare.lp",
        [
            (
                "{ M, self : crank(W, D, M); 2 - M2, D2 : member(C, D2), D2 != D,\n        crank(W, D2, M2) }",
                "{ M, self : crank(W, D, M) }",
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
    for r in case.rules:
        if finding(parts(case, r)) is False:
            continue
        for t in r.constraints:
            forms = dnf(t)
            live = {x for d in forms if disjunct_value(case, d) is not False for x, _ in d}
            if any(case.params[x.operand] is None and x not in live for d in forms for x, _ in d):
                yield "u leaf that only f atoms read"


# The shapes of `shapes` that the generator, and the slow spaces (test_spaces.py), reach.
WANTED = {f"conflict {c}" for c in ("prohibit", "perm", "invalid")} | {
    "open leaves reading one variable with both polarities",
    "Indeterminate with a non-pivotal u atom",
    "two u atoms sharing a variable",
    "an atom with a variable of its own",
    "an open tree with an opaque and a paired leaf",
    "an f atom on an absent target",
    "constraint parts sharing a key",
    "u leaf under a deciding connective",
    "u leaf that only f atoms read",
}


def test_generator_reaches_each_shape() -> None:
    seen: Counter[str] = Counter()

    @settings(max_examples=400, deadline=None, database=None, derandomize=True)
    @given(cases(dead=True))
    def tally(case: Case) -> None:
        seen.update(shapes(case))

    tally()
    assert {s: seen[s] for s in WANTED if seen[s] == 0} == {}, seen


# --- duties (#49) ---

# The actions of ex:d0 to ex:d2: distinct, so an evidence row witnesses one duty only. The root
# obligation ex:ob deletes.
DUTY_ACTIONS = ("compensate", "inform", "attribute")
EARLY = "2026-05-01T00:00:00Z"  # every evidence row's time: before the deadline and effective_at
DEADLINE = "2026-05-15T00:00:00Z"  # before effective_at (conftest.BASE), so it has passed


@dataclass(frozen=True)
class Duty:
    guards: tuple[Tree, ...] = ()
    actor: str | None = None  # the actor of the duty's one evidence row; None: no row
    past: bool = False  # the duty has a deadline, DEADLINE


@dataclass(frozen=True)
class Duties:
    """A `Case` whose permissions carry preconditions, and an optional root obligation."""

    case: Case
    duties: tuple[Duty, ...]  # ex:d0, ex:d1, ...
    edges: tuple[tuple[str, int], ...]  # (permission, duty index): the permission requires it
    obligation: Duty | None = None  # ex:ob, on the policy
    violations: str = "ignore"


@st.composite
def duty_cases(draw: st.DrawFn) -> Duties:
    case = draw(cases())
    tops = [t for r in case.rules for t in r.constraints if isinstance(t, Leaf)]
    # A guard that copies a rule's leaf shares its key, so the two read one variable when the
    # operand is unresolved; drawn freely, that is a few cases in a thousand.
    guards = st.lists(st.sampled_from(tops) | TREES if tops else TREES, max_size=1).map(tuple)
    actors, past = st.sampled_from((None, "alice", "bob")), st.booleans()
    least = 0
    if draw(st.booleans()):
        # Every finding known in half the cases, and each permission with an open duty more
        # often: with unknowns, nearly every case is Indeterminate, and a definite Pending with
        # two alternatives, or a Deny by the obligation, is a few cases in a thousand.
        rules = tuple(replace(r, constraints=()) for r in case.rules)
        subject = case.assignee or draw(st.sampled_from(PARTIES))
        case = replace(case, rules=rules, target=case.target or "a", assignee=subject)
        guards, actors = st.just(()), st.sampled_from((None, None, "alice", "bob"))
        past, least = st.sampled_from((False, False, True)), 1
    duty = st.builds(Duty, guards, actors, past)
    duties = tuple(draw(duty) for _ in DUTY_ACTIONS)
    wanted = {
        (r, k)
        for r in case.rules
        if r.permit
        for k in draw(
            st.lists(st.integers(0, len(DUTY_ACTIONS) - 1), min_size=least, max_size=2, unique=True)
        )
    }
    # The holders of one duty share its bearer, the first holder's, so a duty IRI names one
    # duty atom, and the reply's IRIs say which atoms the program compared.
    first = {k: r.assignee for r, k in sorted(wanted, key=lambda e: e[0].name)}
    edges = {(r.name, k) for r, k in wanted if r.assignee == first[k]}
    return Duties(
        case,
        duties,
        tuple(sorted(edges)),
        draw(st.none() | duty),
        draw(st.sampled_from(("ignore", "deny"))),
    )


def render_duties(dc: Duties) -> Obj:
    v = render(dc.case)
    policy = str(v["policy"])
    head = "ex:p a odrl:Set ;"
    assert policy.count(head) == 1
    lines = [policy.replace(head, head + " odrl:profile dprod: ;")]
    evidence: list[Json] = []

    def duty(name: str, action: str, d: Duty, target: str | None = None) -> None:
        rel = f" ; odrl:target {target}" if target else ""
        deadline = f' ; dprod:deadline "{DEADLINE}"^^xsd:dateTime' if d.past else ""
        cons = f" ; odrl:constraint {', '.join(map(turtle, d.guards))}" if d.guards else ""
        lines.append(f"ex:{name} a odrl:Duty ; odrl:action odrl:{action}{rel}{deadline}{cons} .")
        if d.actor is not None:
            row: Obj = {"id": f"ex:e{name}", "occurred_at": EARLY, "actor": f"ex:{d.actor}"}
            row["action"] = f"odrl:{action}"
            if target:
                row["object"] = target
            evidence.append(row)

    lines.extend(f"ex:{n} odrl:duty ex:d{k} ." for n, k in dc.edges)
    for k in sorted({k for _, k in dc.edges}):
        duty(f"d{k}", DUTY_ACTIONS[k], dc.duties[k])
    if dc.obligation is not None:
        lines.append("ex:p odrl:obligation ex:ob .")
        duty("ob", "delete", dc.obligation, "ex:a")
    v["policy"] = "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n" + "\n".join(lines) + "\n"
    sotw, config = v["sotw"], v["config"]
    assert isinstance(sotw, dict) and isinstance(config, dict)
    sotw["evidence"] = evidence
    config["violations"] = dc.violations
    return v


# A precondition atom's key: `dK@bearer`, the bearer the parent permission's assignee, or `None`
# for the request subject. The root obligation's is `ob`.


def pres(dc: Duties) -> dict[str, list[str]]:
    """Each permission's precondition atom keys."""
    rules = {r.name: r for r in dc.case.rules}
    out: dict[str, list[str]] = {r.name: [] for r in dc.case.rules}
    for n, k in dc.edges:
        out[n].append(f"d{k}@{rules[n].assignee}")
    return out


def duty_of(dc: Duties, key: str) -> Duty:
    if key == "ob":
        assert dc.obligation is not None
        return dc.obligation
    return dc.duties[int(key[1])]


def iri(key: str) -> str:
    """The IRI of a rule name, a duty atom key, or an item name (`owed KEY`, `in_force ob`)."""
    return EX + key.split(" ")[-1].split("@")[0]


def matched(case: Case, r: Rule) -> Truth:
    """The request matches rule `r`, constraints aside: its action, target, and party parts."""
    return finding(parts(case, r)[: 3 if r.assignee else 2])


def fulfilment(case: Case, key: str, d: Duty) -> Truth:
    """The duty's `fulfilled` in world k: its one row, if any, is timely and of its action, so
    the actor check decides. The bearer is the parent's assignee or the request subject, and
    `u` when the request names no subject (due2-workflows.md §5.3)."""
    if d.actor is None:
        return False
    bearer = key.split("@")[1] if "@" in key else "None"
    who = case.assignee if bearer == "None" else bearer
    return None if who is None else d.actor == who


def duty_items(dc: Duties) -> tuple[dict[str, list[Part]], dict[str, Truth]]:
    """The items completion reads, by name: each rule's parts, each precondition atom's guards
    (`owed KEY`), and the obligation's policy match and guards (`in_force ob`); and each
    instance's `fulfilled` in world k, by key. Only an owed or in-force `t` or `u` has an
    instance."""
    case = dc.case
    items: dict[str, list[Part]] = {r.name: parts(case, r) for r in case.rules}
    fulfilled: dict[str, Truth] = {}

    def guards(d: Duty) -> list[Part]:
        return [Open(case, t) if (v := tree_value(case, t)) is None else v for t in d.guards]

    for key in sorted({k for ks in pres(dc).values() for k in ks}):
        d = duty_of(dc, key)
        items[f"owed {key}"] = guards(d)
        if finding(items[f"owed {key}"]) is not False:
            fulfilled[key] = fulfilment(case, key, d)
    if dc.obligation is not None:
        ms = [matched(case, r) for r in case.rules]
        match: Truth = True if True in ms else (None if None in ms else False)
        items["in_force ob"] = [match, *guards(dc.obligation)]
        if finding(items["in_force ob"]) is not False:
            fulfilled["ob"] = fulfilment(case, "ob", dc.obligation)
    return items, fulfilled


def ful(key: str) -> Literal:
    """The variable of a `u` `fulfilled`: a disjunction over witnesses, one variable of its own
    (due2-workflows.md §6.4)."""
    return ("ful", key)


def duty_reads(dc: Duties) -> dict[str, set[Literal]]:
    """The variables each item reads, `fulfilled KEY` included."""
    items, fulfilled = duty_items(dc)
    out = {n: reads(n, ps) for n, ps in items.items()}
    out.update({f"fulfilled {k}": {ful(k)} for k, v in fulfilled.items() if v is None})
    return out


type Basis = set[tuple[str, str]]


def resolve_duties(dc: Duties, world: dict[Literal, bool]) -> tuple[str, Basis]:
    """One completion's verdict and basis, by atom key (due2-workflows.md §6.1 to §6.4)."""
    items, fulfilled = duty_items(dc)
    on = {n: applies(n, ps, world) for n, ps in items.items()}
    done = {k: world[ful(k)] if v is None else v for k, v in fulfilled.items()}
    rules = dc.case.rules
    pre = pres(dc)

    def violated(key: str) -> bool:
        return done.get(key) is False and duty_of(dc, key).past

    def owed(key: str) -> bool:
        return on[f"owed {key}"]

    permitting = {r.name for r in rules if r.permit and on[r.name]}
    closed = {x for x in permitting if any(owed(k) and violated(k) for k in pre[x])}
    cands = permitting - closed
    outstanding = {x: frozenset(k for k in pre[x] if owed(k) and done[k] is False) for x in cands}
    forbids = {r.name for r in rules if not r.permit and on[r.name]}
    conflict = dc.case.conflict
    void = conflict == "invalid" and bool(cands) and bool(forbids)
    if void or (conflict == "prohibit" and forbids):
        cands = set[str]()
    if void or (conflict == "perm" and cands):
        forbids = set[str]()
    obliged = dc.obligation is not None and on["in_force ob"] and violated("ob")
    if forbids or (dc.violations == "deny" and obliged):
        return "Deny", {(f, "prohibition") for f in forbids}
    front = {x for x in cands if not any(outstanding[y] < outstanding[x] for y in cands)}
    if any(not outstanding[x] for x in front):
        return "Permit", {(x, "permission") for x in front}
    if front:
        duties = {(k, "duty") for x in front for k in outstanding[x]}
        return "Pending", {(x, "permission") for x in front} | duties
    return "NotApplicable", {(x, "closed") for x in closed}


def listed_frontier(dc: Duties) -> list[Json]:
    """The frontier the reply lists: from the candidates that are ready or pending in world k
    (due2-workflows.md §6.3), as `tools/check_completion.py`'s `listed_frontier` forms it. A
    candidate is uncertain when its finding is `u`, a precondition's open value is `u`, or a
    violated precondition's `owed` is `u`. Conflict removes no candidate here: the frontier is
    listed under a definite `Pending`, and a `t` forbid that removed candidates under `prohibit`
    or `invalid` would make some completion `Deny` or `NotApplicable`."""
    items, fulfilled = duty_items(dc)
    k_find = {n: finding(ps) for n, ps in items.items()}
    sure: set[frozenset[str]] = set()
    for x, keys in pres(dc).items():
        if not next(r for r in dc.case.rules if r.name == x).permit or k_find[x] is False:
            continue
        unsure, removed, opens = k_find[x] is None, False, set[str]()
        for k in keys:
            ow = k_find[f"owed {k}"]
            if ow is False:
                continue
            fu = fulfilled[k]
            if fu is False and duty_of(dc, k).past:
                removed |= ow is True
                unsure |= ow is None
                continue
            op = kleene_and([ow, None if fu is None else not fu])
            if op is True:
                opens.add(k)
            unsure |= op is None
        if not removed and not unsure:
            sure.add(frozenset(opens))
    front = {x for x in sure if not any(y < x for y in sure)}
    routes = {tuple(sorted(iri(k) for k in x)) for x in front}
    return [list(a) for a in sorted(routes, key=lambda a: (len(a), a))]


def duty_unknown(dc: Duties) -> set[str]:
    """The IRIs of the `u` items that read a pivotal variable."""
    by = duty_reads(dc)
    lits = sorted(set[Literal]().union(*by.values()))
    pivotal: set[Literal] = set()
    for vals in itertools.product((False, True), repeat=len(lits)):
        w = dict(zip(lits, vals, strict=True))
        v = resolve_duties(dc, w)[0]
        pivotal |= {lit for lit in lits if resolve_duties(dc, {**w, lit: not w[lit]})[0] != v}
    return {iri(n) for n, ls in by.items() if ls & pivotal}


def duty_oracle(dc: Duties) -> Obj:
    """The verdict, `verdict_range`, basis, and listed frontier of brute force over `dc`."""
    lits = sorted(set[Literal]().union(*duty_reads(dc).values()))
    results = [
        resolve_duties(dc, dict(zip(lits, vals, strict=True)))
        for vals in itertools.product((False, True), repeat=len(lits))
    ]
    verdicts = {v for v, _ in results}
    items, _ = duty_items(dc)
    obligation = (
        {(EX + "ob", "obligation")}
        if "in_force ob" in items and finding(items["in_force ob"]) is not False
        else set[tuple[str, str]]()
    )
    out: Obj = {"frontier": []}
    if len(verdicts) == 1:
        out["verdict"] = verdict = verdicts.pop()
        common = results[0][1].intersection(*(b for _, b in results[1:]))
        basis = {(iri(k), role) for k, role in common}
        if verdict == "Pending":
            out["frontier"] = listed_frontier(dc)
    else:
        out["verdict"] = "Indeterminate"
        basis = {(n, "unknown") for n in duty_unknown(dc)}
        out["verdict_range"] = {
            "low": min(verdicts, key=CHAIN.index),
            "high": max(verdicts, key=CHAIN.index),
        }
    out["verdict_basis"] = [{"ref": r, "role": role} for r, role in sorted(basis | obligation)]
    return out


def check_duties(interp: Interpreter, dc: Duties) -> None:
    reply = interp.reply(render_duties(dc))
    got = reply.get("output")
    assert isinstance(got, dict), reply
    keys = ("verdict", "frontier", "verdict_range", "verdict_basis")
    assert {k: got[k] for k in keys if k in got} == duty_oracle(dc)


def checked(dc: Duties) -> bool:
    """`dc` is small enough to enumerate: at most `DUTY_VARIABLES` variables."""
    return len(set[Literal]().union(*duty_reads(dc).values())) <= DUTY_VARIABLES


DUTY_VARIABLES = 10
PLAIN = Rule("r0", True, "use", "a", None)
OPEN = Duty()  # unguarded, no evidence, no deadline: owed t and outstanding
LAPSED = Duty(past=True)  # owed t, no evidence, deadline passed: violated


def duties(
    case: Case,
    edges: tuple[tuple[str, int], ...],
    *ds: Duty,
    obligation: Duty | None = None,
    violations: str = "ignore",
) -> Duties:
    return Duties(
        case, (*ds, *(OPEN,) * (len(DUTY_ACTIONS) - len(ds))), edges, obligation, violations
    )


DUTY_EXAMPLES = [
    # A violated precondition whose `owed` is u: where it is owed it closes r0, elsewhere r0 waits
    # on ex:d1, and r1 waits on ex:d2 in both. Pending is definite, but r0 is uncertain, so only
    # ex:d2 is listed (due2-workflows.md §6.3). Read as pending, r0 would add [ex:d1].
    duties(
        Case(
            "perm",
            (PLAIN, Rule("r1", True, "use", "a", None)),
            "use",
            "a",
            "alice",
            (None,) * OPERANDS,
            PAIRED,
        ),
        (("r0", 0), ("r0", 1), ("r1", 2)),
        Duty((eq(2),), past=True),
    ),
    # Two alternatives, ex:d0 and ex:d1 with ex:d2, neither a subset of the other, so both are
    # listed; r0 and r2 wait on one atom, ex:d0, and collapse into one alternative.
    duties(
        Case(
            "perm",
            (PLAIN, Rule("r1", True, "use", "a", None), Rule("r2", True, "use", "a", None)),
            "use",
            "a",
            "alice",
        ),
        (("r0", 0), ("r1", 1), ("r1", 2), ("r2", 0)),
    ),
    # A guard and a rule constraint on one unresolved operand read one variable: where the
    # forbid applies the guard is f, so r1 is never closed and Permit is out of range. Read
    # apart, the range would reach Permit.
    duties(
        Case(
            "prohibit",
            (Rule("r0", False, "use", "a", None, (eq(2),)), Rule("r1", True, "use", "a", None)),
            "use",
            "a",
            "alice",
            (None,) * OPERANDS,
            PAIRED,
        ),
        (("r1", 0),),
        Duty((Leaf(2, "neq"),), past=True),
    ),
    # An absent target leaves r0 and the policy match u, each with a variable of its own: the
    # violated root obligation denies only where it is in force (due2-workflows.md §6.4).
    duties(
        Case("perm", (PLAIN,), "use", None, None),
        (),
        obligation=LAPSED,
        violations="deny",
    ),
    # A request with no subject: the actor check is u, so `fulfilled` is u, with its own
    # variable, and the lapsed precondition closes r0 only where it is unfulfilled.
    duties(Case("perm", (PLAIN,), "use", "a", None), (("r0", 0),), Duty((), "alice", True)),
    # Two lapsed duties with u `fulfilled`, each its own variable. ex:d0 decides r0, so it is
    # pivotal; ex:d1 hangs off r1, whose action never matches, so no flip of it moves the
    # verdict, and only ex:d0 is named `unknown`. Read as one variable, ex:d1 would share
    # ex:d0's pivot and be named too.
    duties(
        Case("perm", (PLAIN, Rule("r1", True, "read", "a", None)), "use", "a", None),
        (("r0", 0), ("r1", 1)),
        Duty((), "alice", True),
        Duty((), "alice", True),
    ),
    # A guarded obligation: in force where its guard is, so the lapse denies only there. Read
    # from the policy match alone, it would deny in every completion.
    duties(
        Case("perm", (PLAIN,), "use", "a", None, (None,) * OPERANDS, PAIRED),
        (),
        obligation=Duty((eq(2),), past=True),
        violations="deny",
    ),
    # A definite Permit with an empty basis (DESIGN.md § `resolve.lp`): ex:d0's guard repeats
    # r1's constraint on an unresolved operand. Where it holds, ex:d0 is owed and violated, so r0
    # is closed and r1 permits; where it does not, r1 does not apply and r0 permits.
    duties(
        Case(
            "perm",
            (PLAIN, Rule("r1", True, "use", "a", None, (eq(2),))),
            "use",
            "a",
            "alice",
            (None,) * OPERANDS,
            PAIRED,
        ),
        (("r0", 0),),
        Duty((eq(2),), past=True),
    ),
    # One duty under two permissions with one bearer is one atom: fulfilled by alice, it leaves
    # both ready; bob's act would fulfil nothing.
    duties(
        Case(
            "perm",
            (Rule("r0", True, "use", "a", "alice"), Rule("r1", True, "use", "a", "alice")),
            "use",
            "a",
            "alice",
        ),
        (("r0", 0), ("r1", 0), ("r1", 1)),
        Duty((), "alice", True),
    ),
]


def duty_differential(interp: Interpreter, config: settings) -> Callable[[], None]:
    """The duty differential against `interp`, on the examples and then on generated cases."""

    @config
    @given(duty_cases())
    def run(dc: Duties) -> None:
        assume(checked(dc))
        check_duties(interp, dc)

    for dc in DUTY_EXAMPLES:
        run = example(dc)(run)
    return run


@pytest.mark.parametrize("copy", range(COPIES))
def test_duties_match_brute_force(duty_interpreter: Interpreter, copy: int) -> None:
    del copy
    duty_differential(duty_interpreter, settings(max_examples=300, deadline=None))()


DUTY_MUTANTS: dict[str, tuple[str, list[tuple[str, str]]]] = {
    # A guard read negated in the completion worlds.
    "duty-roots-negated": (
        "completion.lp",
        [
            (
                "duty_item(I), crank(W, C, N).",
                "duty_item(I), crank(W, C, M), N = 2 - M.",
            )
        ],
    ),
    # One variable for every u `fulfilled`: their completions become correlated.
    "fulfilled-share-a-variable": (
        "completion.lp",
        [
            ("var(ful(Y)) :- u_item(fulfilled(Y)).", "var(ful(0)) :- u_item(fulfilled(Y))."),
            ("reads(fulfilled(Y), ful(Y))", "reads(fulfilled(Y), ful(0))"),
            ("assigned(W, ful(Y), V).", "assigned(W, ful(0), V)."),
        ],
    ),
    # A u `in_force` completed from its policy match alone, its guards dropped.
    "in-force-guards-ignored": (
        "completion.lp",
        [("policy_match(Y, Np); M, C : root_in(W, in_force(Y), C, M) }", "policy_match(Y, Np) }")],
    ),
    # A u `fulfilled` read as f in each world: unknown as false.
    "fulfilled-u-as-f": (
        "completion.lp",
        [
            (
                "completed(W, fulfilled(Y), V) :- u_item(fulfilled(Y)), assigned(W, ful(Y), V).",
                "completed(W, fulfilled(Y), f) :- u_item(fulfilled(Y)), world(W).",
            )
        ],
    ),
    # Only rule atoms named `unknown`: a pivotal duty finding goes unreported.
    "duties-never-unknown": (
        "pivot.lp",
        [
            (
                "unknown(X) :- reads(I, L), pivot(L), finding_atom(I, X).",
                "unknown(X) :- reads(applies(X), L), pivot(L).",
            )
        ],
    ),
    # A candidate with a violated precondition of u `owed` listed as if it waited on the rest.
    "violated-u-owed-listed": (
        "explain.lp",
        [
            (
                (
                    "uncertain(X) :- may_candidate(X), pre(X, Y), status(k, Y, violated), "
                    "holds(owed(Y), u).\n"
                ),
                "",
            )
        ],
    ),
}


@pytest.mark.parametrize("name", sorted(DUTY_MUTANTS))
def test_duty_differential_kills_mutant(name: str) -> None:
    file, edits = DUTY_MUTANTS[name]
    programs = load_programs()
    for old, new in edits:
        assert programs[file].count(old) == 1, f"{file} no longer has {old!r} once"
        programs[file] = programs[file].replace(old, new)
    mutant = duty_differential(
        Interpreter(DUTY_INIT, programs),
        settings(
            max_examples=100, deadline=None, database=None, phases=(Phase.explicit, Phase.generate)
        ),
    )
    with pytest.raises((AssertionError, BaseExceptionGroup)):
        mutant()


def duty_shapes(dc: Duties) -> Iterator[str]:
    """The shapes the duty differential relies on that `dc` has."""
    items, fulfilled = duty_items(dc)
    k_find = {n: finding(ps) for n, ps in items.items()}
    if any(n.startswith("owed ") and v is None for n, v in k_find.items()):
        yield "a u owed"
    if None in fulfilled.values():
        yield "a u fulfilled"
    if k_find.get("in_force ob", False) is None:
        yield "a u in_force"
    by = duty_reads(dc)
    rule_lits = set[Literal]().union(*(by[r.name] for r in dc.case.rules))
    if any(ls & rule_lits for n, ls in by.items() if " " in n):
        yield "a duty finding sharing a variable with a rule"
    out = duty_oracle(dc)
    verdict = out["verdict"]
    frontier, basis = out["frontier"], out["verdict_basis"]
    assert isinstance(frontier, list) and isinstance(basis, list)
    roles = {(b["ref"], b["role"]) for b in basis if isinstance(b, dict)}
    rules = {EX + r.name for r in dc.case.rules}
    if verdict == "Pending":
        yield "Pending"
    if len(frontier) > 1:
        yield "two listed alternatives"
    if any(role == "closed" for _, role in roles):
        yield "a closed route"
    if verdict == "Deny" and not any(role == "prohibition" for _, role in roles):
        yield "Deny by an obligation"
    if any(role == "unknown" and ref not in rules for ref, role in roles):
        yield "Indeterminate naming a duty"


# The shapes of `duty_shapes` that the generator, and the slow spaces, reach.
DUTY_WANTED = {
    "a u owed",
    "a u fulfilled",
    "a u in_force",
    "a duty finding sharing a variable with a rule",
    "Pending",
    "two listed alternatives",
    "a closed route",
    "Deny by an obligation",
    "Indeterminate naming a duty",
}


def test_duty_generator_reaches_each_shape() -> None:
    seen: Counter[str] = Counter()

    @settings(max_examples=1000, deadline=None, database=None, derandomize=True)
    @given(duty_cases())
    def tally(dc: Duties) -> None:
        assume(checked(dc))
        seen.update(duty_shapes(dc))

    tally()
    assert {s: seen[s] for s in DUTY_WANTED if seen[s] == 0} == {}, seen


# --- generator strength (#44) ---

# Draws each mutant gets from generation alone in tests/measure_mutants.py.
STRENGTH_LIMIT = 2000


def mutated(name: str) -> Interpreter:
    """The interpreter with mutant `name`, from MUTANTS or DUTY_MUTANTS, applied."""
    duty = name in DUTY_MUTANTS
    file, edits = (DUTY_MUTANTS if duty else MUTANTS)[name]
    programs = load_programs()
    for old, new in edits:
        assert old in programs[file], f"{file} no longer has {old!r}"
        programs[file] = programs[file].replace(old, new)
    return Interpreter(DUTY_INIT if duty else INIT, programs)


def first_kill(name: str, limit: int, at: int = 0) -> int | None:
    """The generated draw that first exposes mutant `name`, or None if none of `limit` does.

    Generation alone: no explicit examples and no shrinking, so the number measures the
    generator, not the examples tuned to the mutants. The draws come from seed `at`, so the
    number is the same on every run until the generator or the program changes. A duty draw
    counts only when `checked` admits it, as in the duty differential. Hypothesis replays the
    failing draw before it raises, so the first failure is recorded as it happens.
    """
    interp = mutated(name)
    draws = 0
    first: int | None = None
    config = settings(
        max_examples=limit,
        deadline=None,
        database=None,
        phases=(Phase.generate,),
    )

    def seen(check_one: Callable[[], None]) -> None:
        nonlocal draws, first
        draws += 1
        try:
            check_one()
        except AssertionError:
            if first is None:
                first = draws
            raise

    @seed(at)
    @config
    @given(cases(dead=True))
    def rule_run(case: Case) -> None:
        seen(lambda: check(interp, case))

    @seed(at)
    @config
    @given(duty_cases())
    def duty_run(dc: Duties) -> None:
        assume(checked(dc))
        seen(lambda: check_duties(interp, dc))

    with contextlib.suppress(AssertionError, BaseExceptionGroup):
        (duty_run if name in DUTY_MUTANTS else rule_run)()
    return first


def test_opaque_leaf_as_f_fails_open() -> None:
    """The worked example of `opaque-leaf-as-f`: an unknown read as false lets a request through.

    The request states neither the target nor ex:o0, so the prohibition has two opaque `u`
    parts and the verdict is Indeterminate between Deny and NotApplicable. The mutant reads
    the opaque leaf as `f`, so the prohibition cannot apply and it answers NotApplicable while
    still listing both unknowns. tests/measure_mutants.py --shrink opaque-leaf-as-f prints
    the shrunk case Hypothesis finds; this is that case, pinned.
    """
    case = Case(
        conflict="prohibit",
        rules=(Rule("r0", False, "use", "a", None, (Leaf(0, "eq"),)),),
        action="use",
        target=None,
        assignee=None,
    )
    unknown_parts = [
        {"ref": EX + "r0", "input": ODRL + "target", "status": "missing"},
        {"ref": EX + "r0", "input": EX + "o0", "status": "missing"},
    ]
    right = oracle(case)["output"]
    assert isinstance(right, dict)
    assert right["verdict"] == "Indeterminate"
    assert right["verdict_range"] == {"low": "Deny", "high": "NotApplicable"}
    assert right["unknown_parts"] == unknown_parts
    wrong = mutated("opaque-leaf-as-f").reply(render(case))["output"]
    assert isinstance(wrong, dict)
    assert (wrong["verdict"], wrong["verdict_basis"]) == ("NotApplicable", [])
    assert wrong["unknown_parts"] == unknown_parts
