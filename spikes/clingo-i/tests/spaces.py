"""The bounded-exhaustive spaces: every input up to a bound, as `Case`s and `Duties` (#44).

Each space is an ASP program in tests/space/ whose answer sets are the inputs of one
differential: a choice rule picks each part of the input, and integrity constraints keep one
input of each class that renaming or reordering maps onto itself (the programs' headers say
which). This module grounds a program with its bounds, maps each answer set to the `Case` or
`Duties` of test_brute_force.py, and orders the inputs smallest first, so that a failure is
reported on the smallest input that shows it. The expected answers come from the brute-force
oracle, never from the space programs: they choose what is checked, not what is right
(correctness-strategy.md §5, ASP-generated; decisions/0009 #6).

`count` computes each space's size independently, by counting the same classes in Python; a
symmetry constraint that removes too much, or too little, makes the two disagree.

Each space has two bounds: the PR bound, which README § Verify runs, and the slow bound, which
runs under `pytest -m slow` (DESIGN.md § Tests).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from math import comb
from pathlib import Path

from clingo import Control, Model, Symbol

from tests.test_brute_force import (
    DUTY_ACTIONS,
    OPEN,
    OPERANDS,
    Case,
    Duties,
    Duty,
    Leaf,
    Node,
    Rule,
    Tree,
    checked,
)

SPACE = Path(__file__).parent / "space"

# An operand status (rules.lp) as the request parameter and whether the state gives it.
STATUS: dict[str, tuple[int | None, bool]] = {
    "value": (1, False),
    "resolved": (1, True),
    "missing": (None, False),
    "unresolved": (None, True),
}


@dataclass(frozen=True)
class Space:
    program: str  # the file in tests/space/
    duties: bool  # inputs to the duty differential, not the rule differential
    pr: tuple[tuple[str, int], ...]  # the constants at the PR bound
    slow: tuple[tuple[str, int], ...]  # the constants at the slow bound

    def consts(self, tier: str) -> dict[str, int]:
        return dict(self.pr if tier == "pr" else self.slow)


SPACES = {
    # Two rules with leaf constraints, under every operand status.
    "leaves": Space(
        "rules.lp",
        False,
        (("rules", 2), ("size", 1), ("operators", 2), ("operands", 1)),
        (("rules", 2), ("size", 1)),
    ),
    # One rule with a tree of every shape, under every operand status.
    "trees": Space(
        "rules.lp",
        False,
        (("rules", 1), ("size", 3), ("operators", 2), ("operands", 1)),
        (("rules", 1), ("size", 4)),
    ),
    # One rule with a larger tree, its leaves t, f, and a paired u.
    "pinned": Space(
        "rules.lp",
        False,
        (("rules", 1), ("size", 4), ("pinned", 1), ("operators", 2)),
        (("rules", 1), ("size", 6), ("pinned", 1), ("operators", 2)),
    ),
    # Unconstrained rules and the request: candidates and conflict.
    "candidates": Space("candidates.lp", False, (("rules", 1),), (("rules", 2),)),
    # Three unconstrained rules over one action: conflict among more candidates.
    "conflicts": Space(
        "candidates.lp", False, (("rules", 1), ("actions", 1)), (("rules", 3), ("actions", 1))
    ),
    # The coverage target past the trees bounds: a negated xone with a compound term.
    "negxone": Space("negxone.lp", False, (("largest", 7),), (("largest", 8),)),
    # Permissions with routes of unguarded duties, and the subject alice or none.
    "routes": Space(
        "duties.lp",
        True,
        (("rules", 2), ("duties", 2), ("subjects", 2)),
        (("rules", 2), ("duties", 3), ("subjects", 2)),
    ),
    # A root obligation beside a rule, with a guard and one operand.
    "obligation": Space(
        "duties.lp",
        True,
        (
            ("rules", 1),
            ("duties", 0),
            ("operands", 1),
            ("guards", 1),
            ("obligations", 1),
            ("prohibitions", 1),
            ("subjects", 1),
            ("actors", 1),
        ),
        (
            ("rules", 1),
            ("duties", 0),
            ("operands", 1),
            ("guards", 1),
            ("obligations", 1),
            ("prohibitions", 1),
            ("subjects", 2),
        ),
    ),
    # Guarded duties whose guards read the rules' operand, with no evidence.
    "guards": Space(
        "duties.lp",
        True,
        (("rules", 1), ("duties", 2), ("operands", 1), ("guards", 1), ("actors", 1)),
        (("rules", 2), ("duties", 2), ("operands", 1), ("guards", 1), ("actors", 1)),
    ),
}


def answer_sets(program: str, consts: dict[str, int]) -> list[Sequence[Symbol]]:
    """The shown atoms of each answer set of `program` under `consts`."""
    args = ["0"] + [x for k, v in consts.items() for x in ("-c", f"{k}={v}")]
    ctl = Control(args)
    ctl.load(str(SPACE / program))
    ctl.ground([("base", [])])
    out: list[Sequence[Symbol]] = []

    def on_model(m: Model) -> None:
        out.append(m.symbols(shown=True))

    ctl.solve(on_model=on_model)
    return out


def tree(s: Symbol) -> Tree:
    """The tree of trees.lp's term `s`: `l(O, P)`, `neg(A)`, or `node(F, A, B[, C])`."""
    args = s.arguments
    if s.name == "l":
        return Leaf(args[0].number, args[1].name)
    if s.name == "neg":
        return Node("not", (tree(args[0]),), False)
    return Node(args[0].name, tuple(tree(a) for a in args[1:]), False)


def size(t: Tree) -> int:
    return 1 if isinstance(t, Leaf) else 1 + sum(size(m) for m in t.members)


def maybe(s: Symbol) -> str | None:
    return None if s.name == "none" else s.name


def constraints(s: Symbol) -> tuple[Tree, ...]:
    return () if s.name == "none" else (tree(s),)


def rule(i: int, s: Symbol) -> Rule:
    """Slot `i`'s rule, `r(K, C)` (rules.lp, duties.lp) or `r(K, A, T, P)` (candidates.lp)."""
    args = s.arguments
    permit = args[0].name == "permission"
    if len(args) == 2:
        return Rule(f"r{i - 1}", permit, "use", "a", None, constraints(args[1]))
    return Rule(f"r{i - 1}", permit, args[1].name, args[2].name, maybe(args[3]))


def duty(s: Symbol) -> Duty:
    """The duty of `d(G, A, P)` (duties.lp)."""
    g, a, p = s.arguments
    return Duty(constraints(g), maybe(a), p.number == 1)


def to_input(atoms: Sequence[Symbol], duties: bool) -> Case | Duties:
    slots: dict[int, Symbol] = {}
    statuses: dict[int, tuple[int | None, bool]] = {}
    ds: dict[int, Duty] = {}
    edges: list[tuple[str, int]] = []
    request: tuple[str, str | None, str | None] = ("use", "a", None)
    conflict, obligation, violations = "perm", None, "ignore"
    for a in atoms:
        x = a.arguments
        match a.name:
            case "slot":
                slots[x[0].number] = x[1]
            case "operand":
                statuses[x[0].number] = STATUS[x[1].name]
            case "conflict":
                conflict = x[0].name
            case "request":
                request = (x[0].name, maybe(x[1]), maybe(x[2]))
            case "subject":
                request = (request[0], request[1], maybe(x[0]))
            case "dterm":
                ds[x[0].number] = duty(x[1])
            case "edge":
                edges.append((f"r{x[0].number - 1}", x[1].number))
            case "obligation":
                obligation = duty(x[0])
            case "violations":
                violations = "deny"
            case _:
                raise ValueError(a)
    missing = STATUS["missing"]
    case = Case(
        conflict,
        tuple(rule(i, s) for i, s in sorted(slots.items())),
        *request,
        tuple(statuses.get(k, missing)[0] for k in range(OPERANDS)),
        tuple(statuses.get(k, missing)[1] for k in range(OPERANDS)),
    )
    if not duties:
        return case
    return Duties(
        case,
        tuple(ds.get(k, OPEN) for k in range(len(DUTY_ACTIONS))),
        tuple(sorted(edges)),
        obligation,
        violations,
    )


def weight(x: Case | Duties) -> tuple[int, int]:
    """The order of the inputs: fewer rules first, then smaller trees, or, for duties, fewer edges."""
    if isinstance(x, Duties):
        return len(x.case.rules), len(x.edges)
    return len(x.rules), sum(size(t) for r in x.rules for t in r.constraints)


@cache
def models(name: str, tier: str) -> tuple[Case | Duties, ...]:
    """Every answer set of space `name` at `tier`, as inputs, smallest first."""
    space = SPACES[name]
    found = [to_input(a, space.duties) for a in answer_sets(space.program, space.consts(tier))]
    return tuple(sorted(found, key=lambda x: (weight(x), repr(x))))


def inputs(name: str, tier: str) -> tuple[Case | Duties, ...]:
    """The inputs the differential checks: duty inputs only when `checked` admits them."""
    return tuple(x for x in models(name, tier) if not isinstance(x, Duties) or checked(x))


# --- independent counts ---


def mult(n: int, k: int) -> int:
    """The multisets of `k` items from `n` kinds."""
    return comb(n + k - 1, k) if n else int(k == 0)


def catalog(operands: int, operators: int, most: int) -> list[int]:
    """The trees of trees.lp by size: `c[s]` trees of size `s`, for `s` from 0 to `most`."""
    c = [0] * (most + 1)

    def members(k: int, w: int) -> int:
        # Multisets of `k` trees of total size `w`: choose how many of each size, then which.
        ways = {(0, 0): 1}
        for s in range(1, w + 1):
            nxt: dict[tuple[int, int], int] = {}
            for (n, total), v in ways.items():
                for m in range(k - n + 1):
                    if total + m * s <= w:
                        key = (n + m, total + m * s)
                        nxt[key] = nxt.get(key, 0) + v * mult(c[s], m)
            ways = nxt
        return ways.get((k, w), 0)

    for s in range(1, most + 1):
        c[s] = (operands * operators if s == 1 else c[s - 1]) + 3 * (
            members(2, s - 1) + members(3, s - 1)
        )
    return c


def rule_sets(most: int, half: int, both: int = 3) -> int:
    """Multisets of 1 to `most` rules from `half` permissions and `half` prohibitions.

    A set with both kinds takes each of the `both` conflict strategies; any other takes one.
    """
    total = 0
    for n in range(1, most + 1):
        one_kind = 2 * mult(half, n)
        total += both * (mult(2 * half, n) - one_kind) + one_kind
    return total


def duty_count(k: dict[str, int]) -> int:
    trees = 2 * k["operands"]
    perms, prohibs = 1 + trees, (1 + trees) * k["prohibitions"]
    kinds = (1 + trees * k["guards"]) * k["actors"] * 2
    total = 0
    for p in range(k["rules"] + 1):
        for q in range(k["rules"] + 1 - p):
            if p + q == 0:
                continue
            routes = sum(mult(kinds, n) * (2**p - 1) ** n for n in range(k["duties"] + 1))
            total += mult(perms, p) * mult(prohibs, q) * (3 if p and q else 1) * routes
    obligation = kinds * 2 if k["obligations"] else 1
    return total * mult(4, k["operands"]) * k["subjects"] * obligation


def count(name: str, tier: str) -> int:
    """The size of space `name` at `tier`, counted without the space program."""
    space = SPACES[name]
    k = space.consts(tier)
    match space.program:
        case "rules.lp":
            k = {"pinned": 0, "operands": 2, "operators": 4} | k
            trees = sum(catalog(k["operands"], k["operators"], k["size"]))
            statuses = 1 if k["pinned"] else mult(4, k["operands"])
            return rule_sets(k["rules"], 1 + trees) * statuses
        case "candidates.lp":
            k = {"actions": 2} | k
            return rule_sets(k["rules"], k["actions"] * 2 * 3) * k["actions"] * 2 * 2
        case "negxone.lp":
            largest = k["largest"]
            c = catalog(2, 2, largest - 5)
            pairs = [0] * (largest + 1)
            for sa in range(1, len(c)):
                for sb in range(sa, len(c)):
                    w = sa + sb
                    if w <= largest - 4:
                        pairs[w] += c[sa] * c[sb] if sa < sb else mult(c[sa], 2)
            pairs[2] -= mult(c[1], 2)  # two leaves: neither term is compound
            shapes = sum(
                pairs[w] * sum(c[1 : largest - 1 - (w + 2) + 1]) for w in range(2, largest - 3)
            )
            return 2 * 3 * shapes
        case _:
            return duty_count(
                {"duties": 1, "operands": 0, "guards": 0, "prohibitions": 0, "obligations": 0}
                | {"subjects": 1, "actors": 3}
                | k
            )
