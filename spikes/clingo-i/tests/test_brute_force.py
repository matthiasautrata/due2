"""The brute-force differential (DESIGN.md § Tests, correctness-strategy.md §4.1).

Over generated policies of permissions and prohibitions, with an absent target or an unnamed
assignee, a Python oracle enumerates every completion of the literals, flips each literal
alone, and derives the verdict, the basis, the eliminations, the `unknown` atoms, and the
range (due2-workflows.md §5.2, §6.1 to §6.4; decisions/0011). It reads the generated rules, not the
program's facts, and shares only the spec's literal key with it.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from hypothesis import example, given, settings
from hypothesis import strategies as st

from clingo_i.interpret import CHAIN, Interpreter
from clingo_i.json_types import Json, Obj
from tests.conftest import PREFIXES, vector

EX = "https://example.org/"
ACTIONS = ("use", "play")  # play ⊑ use in the test core (conftest.INIT)
PARTIES = ("alice", "bob")


@dataclass(frozen=True)
class Rule:
    name: str
    permit: bool
    action: str
    target: str
    assignee: str | None


@dataclass(frozen=True)
class Case:
    conflict: str
    rules: tuple[Rule, ...]
    action: str
    target: str | None  # None: absent
    assignee: str | None  # None: the request names no assignee


@st.composite
def cases(draw: st.DrawFn) -> Case:
    rules = [
        Rule(
            f"r{i}",
            draw(st.booleans()),
            draw(st.sampled_from(ACTIONS)),
            draw(st.sampled_from(("a", "a", "b"))),
            draw(st.sampled_from((None, *PARTIES))),
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
    )


def render(case: Case) -> Obj:
    refs = " ; ".join(
        f"odrl:{'permission' if r.permit else 'prohibition'} ex:{r.name}" for r in case.rules
    )
    lines = [f"ex:p a odrl:Set ; odrl:conflict odrl:{case.conflict} ; {refs} ."]
    for r in case.rules:
        cls = "Permission" if r.permit else "Prohibition"
        party = f" ; odrl:assignee ex:{r.assignee}" if r.assignee else ""
        lines.append(
            f"ex:{r.name} a odrl:{cls} ; odrl:action odrl:{r.action} ; odrl:target ex:{r.target}{party} ."
        )
    parties: Obj = {"odrl:assignee": f"ex:{case.assignee}"} if case.assignee else {}
    v = vector(
        PREFIXES + "\n".join(lines) + "\n",
        request={"action": f"odrl:{case.action}", "parties": parties},
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


def parts(case: Case, r: Rule) -> list[Truth | Literal]:
    """A rule's parts: a known truth, or the literal a u part reads (due2-workflows.md §6.4)."""
    out: list[Truth | Literal] = [case.action == r.action or r.action == "use"]
    out.append(("target", r.target) if case.target is None else case.target == r.target)
    if r.assignee is not None:
        out.append(("party", r.assignee) if case.assignee is None else case.assignee == r.assignee)
    return out


def finding(ps: list[Truth | Literal]) -> Truth:
    """Kleene conjunction, with every literal u."""
    if any(p is False for p in ps):
        return False
    return None if any(isinstance(p, tuple) for p in ps) else True


def applies(ps: list[Truth | Literal], world: dict[Literal, bool]) -> bool:
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


def oracle(case: Case) -> Obj:
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
        pivotal = {
            lit for w in worlds for lit in lits if run(w)[0] != run({**w, lit: not w[lit]})[0]
        }
        unknown = sorted(
            n
            for n, p in ps.items()
            if find[n] is None and any(q in pivotal for q in p if isinstance(q, tuple))
        )
        out["verdict"] = "Indeterminate"
        out["verdict_basis"] = [{"ref": EX + n, "role": "unknown"} for n in unknown]
        out["verdict_range"] = {
            "low": min(verdicts, key=CHAIN.index),
            "high": max(verdicts, key=CHAIN.index),
        }
    out["eliminated"] = eliminations(case, find)
    return out


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


# A t candidate, a u candidate whose literal moves nothing, and a u forbid whose literal does:
# only the forbid is `unknown` (0011 #1). Random draws reach this shape in a few percent.
T, ALICE, BOB = (
    Rule("r0", True, "use", "a", None),
    Rule("r1", True, "use", "a", "alice"),
    Rule("r2", False, "use", "a", "bob"),
)


@settings(max_examples=400, deadline=None)
@given(cases())
@example(Case("prohibit", (T, ALICE, BOB), "use", "a", None))
@example(Case("invalid", (T, ALICE, BOB), "use", "a", None))
@example(
    Case(
        "perm",
        (Rule("r0", True, "use", "a", None), Rule("r1", False, "use", "a", None)),
        "use",
        None,
        None,
    )
)
def test_matches_brute_force(interpreter: Interpreter, case: Case) -> None:
    reply = interpreter.reply(render(case))
    assert "output" in reply, reply
    got = reply["output"]
    assert isinstance(got, dict)
    got = {k: v for k, v in got.items() if k not in ("frontier", "obligations", "exact")}
    assert got == oracle(case)
