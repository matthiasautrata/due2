"""Randomised check of due2-workflows.md §6.4 (v0.6, completions over literals).

Claim: enumerating the mixed variables and completing the uniform ones at the
two extremes gives the same verdict (definite or Indeterminate) as brute force
over every assignment of every variable. Also counts how often v0.6 is definite
where the pre-v0.6 reading (every occurrence its own variable) was Indeterminate.

Model: one policy, conflict in {prohibit, perm, invalid}; Permit/Forbid atoms,
each a conjunction of literals (variable, polarity) over Boolean variables;
Permits carry precondition duties, each duty's fulfilment a variable, optionally
guarded by literals over the same variables (third phase). The verdict for a total
assignment follows §6.1-§6.4. Run: uv run python tools/check_completion.py

Recorded result (seed 20261011): 50000 cases, 0 mismatches, 1244 newly definite.
Second phase (seed 20261012, `rand_wide`): the beyond-max_mixed fallback is
sound — 1000 wider cases, 0 unsound, fallback in 111, Indeterminate in 84 of
those where the exact reading decides.

Third phase (seed 20261013, `rand_guarded`, decisions/0003): precondition duties
keep their guards, evaluated in W2 as `owed`; a duty is outstanding when owed and
not fulfilled, and a positive guard occurrence moves the verdict down. 50000
cases, 0 mismatches. (The second-phase demo of a hoisted guard was removed with
hoisting; under 0003 w3c-fs-c2's guard is uniform and two extremes suffice.)

Fourth phase (seed 20261014, `rand_deadlines`): each duty's deadline has passed
or not (fixed per case, §5.3); an owed, unfulfilled, past-deadline precondition
removes its candidate (§6.1). A root obligation never affects the verdict (§6.1,
decisions/0045), so the phase has none. Recorded: 50000 cases, 0 mismatches.

Fifth phase (seed 20261015, `rand_frontier`): partial knowledge, each variable
known T, known F, or U. For every definite Pending, the listed frontier (§6.3,
decisions/0026) is computed by brute force over every completion: the
non-dominated routes that suffice, where a route suffices when it is open in some
completion and every completion has an open route within it. frontier_complete
holds, by its §6.4 definition, iff every completion's frontier is the listed one.
Gated (decisions/0004, 0026): enumerating only the relevant unknowns, bounded by
max_frontier_vars, gives both exactly; and with the bound forced to 1, every route
the fallback lists suffices. Recorded: definite Pending in 942; listed frontier
empty in 1 (v0.33's, from ready and pending candidates only: 191; the routes open
in every completion: 181); frontier_complete false in 189; the rejected rule
"complete iff no candidate is uncertain" would say false in 143 more; bounded
enumeration 0 mismatches; with bound 1, fallback in 148, 0 unsound.

Scope: one policy; atoms are flat conjunctions; no obligations, recurrence, or
instances. A sanity check of §6.4's claims, not a proof, and not a check of the
rest of W3 (that is the differential against slow I on the relation-level
vectors, correctness-strategy.md §4.5).
"""

import itertools
import random
from collections.abc import Iterable
from typing import TypedDict, Unpack

type Var = str
type Lit = tuple[Var, bool]  # (variable, polarity)
type Guards = dict[Var, list[Lit]]  # duty -> guard literals (owed)
type Frontier = frozenset[frozenset[Var]]


class Atom(TypedDict):
    eff: str  # "Permit" or "Forbid"
    lits: list[Lit]
    duties: list[Var]


class Timing(TypedDict, total=False):
    past: dict[Var, bool]


def evaluate(
    atoms: list[Atom],
    conflict: str,
    val: dict[Var, bool],
    guards: Guards | None = None,
    past: dict[Var, bool] | None = None,
) -> tuple[str, Frontier, Frontier]:
    """One completion (no U): (verdict, frontier, open routes), workflows §6.1-§6.4. The
    open routes are every surviving candidate's outstanding set, dominated or not.
    past: duty -> its deadline has passed (fixed by the case, not a finding)."""
    guards, past = guards or {}, past or {}

    def holds(lits: list[Lit]) -> bool:
        return all(val[v] == pol for v, pol in lits)

    def owed(d: Var) -> bool:
        return holds(guards.get(d, []))

    perms = [
        a
        for a in atoms
        if a["eff"] == "Permit"
        and holds(a["lits"])
        and not any(owed(d) and not val[d] and past.get(d) for d in a["duties"])
    ]
    # §6.1: a violated precondition that is owed removes its candidate, before conflict
    # resolution.
    forbs = [a for a in atoms if a["eff"] == "Forbid" and holds(a["lits"])]
    if conflict == "prohibit" and forbs:
        perms = []
    elif conflict == "perm" and perms:
        forbs = []
    elif conflict == "invalid" and perms and forbs:
        perms, forbs = [], []
    if forbs:
        return "Deny", frozenset(), frozenset()
    sets = {
        frozenset(d for d in a["duties"] if owed(d) and not val[d]) for a in perms
    }  # decisions/0003: outstanding = owed and not fulfilled; §6.3 collapse
    frontier = non_dominated(sets)
    if frozenset() in sets:
        return "Permit", frontier, frozenset(sets)
    return ("Pending" if sets else "NotApplicable"), frontier, frozenset(sets)


def non_dominated(sets: Iterable[frozenset[Var]]) -> Frontier:
    """§6.3: the routes whose outstanding set strictly contains no other's."""
    sets = set(sets)
    return frozenset(x for x in sets if not any(y < x for y in sets))


def sufficient(opens: Iterable[Frontier]) -> Frontier:
    """decisions/0026: the routes open in some completion such that every completion has
    an open route within them, given each completion's open routes."""
    opens = list(opens)
    routes = {r for o in opens for r in o}
    return frozenset(r for r in routes if all(any(s <= r for s in o) for o in opens))


def listed(opens: Iterable[Frontier]) -> Frontier:
    """decisions/0026: the listed frontier, the non-dominated routes that suffice."""
    return non_dominated(sufficient(opens))


def verdict(
    atoms: list[Atom],
    conflict: str,
    val: dict[Var, bool],
    guards: Guards | None = None,
    **kw: Unpack[Timing],
) -> str:
    return evaluate(atoms, conflict, val, guards, **kw)[0]


def brute(
    atoms: list[Atom],
    conflict: str,
    vars_: list[Var],
    guards: Guards | None = None,
    **kw: Unpack[Timing],
) -> str:
    vs = {
        verdict(atoms, conflict, dict(zip(vars_, bits, strict=True)), guards, **kw)
        for bits in itertools.product([False, True], repeat=len(vars_))
    }
    return vs.pop() if len(vs) == 1 else "Indeterminate"


def directions(atoms: list[Atom], guards: Guards | None = None) -> dict[Var, set[bool]]:
    """Per variable, the set of directions its occurrences move the verdict (True = up).
    A guard literal of a precondition duty moves it down when positive: more owed,
    lower verdict (decisions/0003)."""
    d: dict[Var, set[bool]] = {}
    for lits in (guards or {}).values():
        for v, pol in lits:
            d.setdefault(v, set()).add(not pol)
    for a in atoms:
        up = a["eff"] == "Permit"
        for v, pol in a["lits"]:
            d.setdefault(v, set()).add(up == pol)
        for v in a["duties"]:
            d.setdefault(v, set()).add(True)
    return d


def algorithm(
    atoms: list[Atom],
    conflict: str,
    vars_: list[Var],
    guards: Guards | None = None,
    **kw: Unpack[Timing],
) -> str:
    d = directions(atoms, guards)
    mixed = [v for v in vars_ if len(d.get(v, {True})) == 2]
    uniform = [v for v in vars_ if v not in mixed]
    seen: set[str] = set()
    for bits in itertools.product([False, True], repeat=len(mixed)):
        base = dict(zip(mixed, bits, strict=True))
        for extreme in (True, False):  # most permissive, most restrictive
            val = dict(base)
            for v in uniform:
                up = d.get(v, {True}) == {True}
                val[v] = up if extreme else not up
            seen.add(verdict(atoms, conflict, val, guards, **kw))
    return seen.pop() if len(seen) == 1 else "Indeterminate"


def bounded(
    atoms: list[Atom], conflict: str, vars_: list[Var], max_mixed: int = 8
) -> tuple[str, bool]:
    """v0.6 with the W3 limit of workflows §6.4: when more than max_mixed
    variables are mixed, their occurrences are completed independently — the
    pre-v0.6 reading, restricted to the mixed variables. Returns (verdict,
    exact); beyond the bound every freshened occurrence is uniform, so the
    enumeration inside algorithm() is empty and only the two extremes run."""
    d = directions(atoms)
    mixed = [v for v in vars_ if len(d.get(v, {True})) == 2]
    if len(mixed) <= max_mixed:
        return algorithm(atoms, conflict, vars_), True
    mset = set(mixed)
    fresh: list[Atom] = []
    k = 0
    for a in atoms:
        lits: list[Lit] = []
        for v, pol in a["lits"]:
            if v in mset:
                lits.append((f"m{k}", pol))
                k += 1
            else:
                lits.append((v, pol))
        fresh.append({**a, "lits": lits})
    uniform = [v for v in vars_ if v not in mset]
    return algorithm(fresh, conflict, [f"m{i}" for i in range(k)] + uniform), False


def independent(atoms: list[Atom], conflict: str, vars_: list[Var]) -> str:
    """Pre-v0.6: every literal occurrence its own variable."""
    fresh: list[Atom] = []
    k = 0
    for a in atoms:
        lits: list[Lit] = []
        for _, pol in a["lits"]:
            lits.append((f"o{k}", pol))
            k += 1
        fresh.append({**a, "lits": lits})
    return algorithm(
        fresh, conflict, [f"o{i}" for i in range(k)] + [v for v in vars_ if v.startswith("d")]
    )


def rand_case(rng: random.Random) -> tuple[list[Atom], str, list[Var]]:
    nv, nd = rng.randint(1, 4), rng.randint(0, 2)
    vs, ds = [f"x{i}" for i in range(nv)], [f"d{i}" for i in range(nd)]
    atoms: list[Atom] = []
    for _ in range(rng.randint(1, 5)):
        eff = rng.choice(["Permit", "Permit", "Forbid"])
        lits = [(v, rng.random() < 0.5) for v in rng.sample(vs, rng.randint(0, min(2, nv)))]
        duties = rng.sample(ds, rng.randint(0, nd)) if eff == "Permit" else []
        atoms.append({"eff": eff, "lits": lits, "duties": duties})
    return atoms, rng.choice(["prohibit", "perm", "invalid"]), vs + ds


def rand_guarded(rng: random.Random) -> tuple[list[Atom], str, list[Var], Guards]:
    """decisions/0003: precondition duties keep their guards (no hoisting). Each
    duty may carry guard literals over the same variables the rules read, so a
    guard can share a variable with a permission's or prohibition's constraint,
    in either polarity — the only way a guard becomes mixed."""
    nv, nd = rng.randint(1, 4), rng.randint(1, 3)
    vs, ds = [f"x{i}" for i in range(nv)], [f"d{i}" for i in range(nd)]
    guards = {
        d: [(v, rng.random() < 0.5) for v in rng.sample(vs, rng.randint(0, min(2, nv)))] for d in ds
    }
    atoms: list[Atom] = []
    for _ in range(rng.randint(1, 4)):
        eff = rng.choice(["Permit", "Permit", "Forbid"])
        lits = [(v, rng.random() < 0.5) for v in rng.sample(vs, rng.randint(0, min(2, nv)))]
        duties = rng.sample(ds, rng.randint(0, nd)) if eff == "Permit" else []
        atoms.append({"eff": eff, "lits": lits, "duties": duties})
    return atoms, rng.choice(["prohibit", "perm", "invalid"]), vs + ds, guards


def rand_deadlines(rng: random.Random) -> tuple[list[Atom], str, list[Var], Guards, Timing]:
    """Fourth phase: deadlines. Each duty's deadline has passed or not (fixed per case);
    an owed, unfulfilled, past-deadline precondition removes its candidate."""
    nv, nd = rng.randint(1, 4), rng.randint(1, 3)
    vs, ds = [f"x{i}" for i in range(nv)], [f"d{i}" for i in range(nd)]
    unguarded = set(rng.sample(ds, rng.randint(0, nd)))
    guards = {
        d: [(v, rng.random() < 0.5) for v in rng.sample(vs, rng.randint(0, min(2, nv)))]
        for d in ds
        if d not in unguarded
    }
    past = {d: rng.random() < 0.5 for d in ds}
    atoms: list[Atom] = []
    for _ in range(rng.randint(1, 4)):
        eff = rng.choice(["Permit", "Permit", "Forbid"])
        lits = [(v, rng.random() < 0.5) for v in rng.sample(vs, rng.randint(0, min(2, nv)))]
        duties = rng.sample(ds, rng.randint(0, nd)) if eff == "Permit" else []
        atoms.append({"eff": eff, "lits": lits, "duties": duties})
    # These draws once built root obligations and chose `violations`, which decisions/0045
    # removed. They are kept, unused, so that each seed still yields the cases it recorded:
    # decisions/0004 cites the fifth phase's numbers for seed 20261015.
    for _ in sorted(unguarded):
        if rng.random() < 0.7:
            for _ in rng.sample(vs, rng.randint(0, min(2, nv))):
                rng.random()
    rng.choice(["ignore", "deny"])
    kw: Timing = {"past": past}
    return atoms, rng.choice(["prohibit", "perm", "invalid"]), vs + ds, guards, kw


def kleene_and(xs: Iterable[bool | None]) -> bool | None:
    xs = list(xs)
    return False if False in xs else (None if None in xs else True)


def fallback_frontier(
    atoms: list[Atom],
    conflict: str,
    known: dict[Var, bool],
    guards: Guards,
    past: dict[Var, bool],
    v033: bool = False,
) -> tuple[Frontier, bool, set[Var]]:
    """The frontier W3 lists beyond max_frontier_vars, from three-valued findings
    (§6.4, decisions/0026): the routes of the ready and pending candidates that no
    completion removes in §6.2; uncertain candidates (permission U, an unknown open
    duty, or a violated precondition whose owed is U) are left out, and so are the
    candidates of a policy under invalid with a U prohibition. v033=True keeps them,
    which is v0.33's listed frontier, for the fifth phase's comparison.
    known: variable -> True/False, absent = U. Returns (frontier, any_uncertain,
    relevant):
    relevant holds the unknown variables of uncertain candidates' parts (permission,
    owed, fulfilled) and of prohibitions whose finding is U — the only unknowns a
    completion can use to change the frontier while Pending stands (decisions/0004)."""

    def lit(v: Var, pol: bool) -> bool | None:
        return None if v not in known else known[v] == pol

    def val(lits: list[Lit]) -> bool | None:
        return kleene_and(lit(v, p) for v, p in lits)

    sure: list[frozenset[Var]] = []
    uncertain, forbs_t, forbs_u = False, False, False
    relevant: set[Var] = set()

    def unknowns(lits: list[Lit]) -> set[Var]:
        return {v for v, _ in lits if v not in known}

    for a in atoms:
        f = val(a["lits"])
        if a["eff"] == "Forbid":
            forbs_t = forbs_t or f is True
            if f is None:
                forbs_u = True
                relevant |= unknowns(a["lits"])
            continue
        if f is False:
            continue
        opens: set[Var] = set()
        removed, unsure = False, f is None
        for d in a["duties"]:
            ow, fu = val(guards.get(d, [])), known.get(d)
            op = kleene_and([ow, None if fu is None else not fu])
            if fu is False and past.get(d):  # violated instance
                if ow is True:
                    removed = True
                elif ow is None:
                    unsure = True
            elif op is True:
                opens.add(d)
            elif op is None:
                unsure = True
        if removed:
            continue
        if unsure:
            uncertain = True
            relevant |= unknowns(a["lits"])
            for d in a["duties"]:
                relevant |= unknowns(guards.get(d, [])) | ({d} - known.keys())
        else:
            sure.append(frozenset(opens))
    if (forbs_t and conflict == "prohibit") or (forbs_u and conflict == "invalid" and not v033):
        sure = []  # under invalid, a completion where the U prohibition is T voids the policy
    return non_dominated(sure), uncertain, relevant


def frontier_complete(
    atoms: list[Atom],
    conflict: str,
    known: dict[Var, bool],
    guards: Guards,
    kw: Timing,
    bound: int = 8,
) -> tuple[Frontier, bool, bool]:
    """§6.4, decisions/0004 and 0026: for a definite Pending, enumerate every assignment
    to the relevant unknowns, the others fixed F (no two-extremes shortcut: a frontier
    is a set, not a point on the verdict chain). The listed frontier is the
    non-dominated routes that suffice over the assignments, and frontier_complete holds iff
    each assignment's frontier is the listed one. Beyond `bound`, the fallback frontier,
    not complete and inexact. Returns (listed frontier, frontier_complete, exact)."""
    fallback, _, relevant = fallback_frontier(atoms, conflict, known, guards, kw.get("past", {}))
    if len(relevant) > bound:
        return fallback, False, False
    rel = sorted(relevant)
    rest = {v: False for v in all_vars(atoms, guards) if v not in known and v not in relevant}
    runs = [
        evaluate(
            atoms, conflict, {**known, **rest, **dict(zip(rel, bits, strict=True))}, guards, **kw
        )
        for bits in itertools.product([False, True], repeat=len(rel))
    ]
    front = listed(o for _, _, o in runs)
    return front, all(f == front for _, f, _ in runs), True


def all_vars(atoms: list[Atom], guards: Guards) -> set[Var]:
    vs = {v for a in atoms for v, _ in a["lits"]} | {d for a in atoms for d in a["duties"]}
    return vs | {v for lits in guards.values() for v, _ in lits}


def rand_frontier(
    rng: random.Random,
) -> tuple[list[Atom], str, list[Var], Guards, Timing, dict[Var, bool]]:
    """Fifth phase: partial knowledge. Each variable is known T, known F, or unknown,
    so definite candidates exist beside uncertain ones and the listed frontier can be
    compared with every completion's."""
    atoms, conflict, vars_, guards, kw = rand_deadlines(rng)
    known = {v: rng.random() < 0.5 for v in vars_ if rng.random() < 0.5}
    return atoms, conflict, vars_, guards, kw, known


def rand_wide(rng: random.Random) -> tuple[list[Atom], str, list[Var]]:
    """Instances sized to exceed max_mixed: each variable gets an up and a
    down occurrence with high probability, so most are mixed."""
    nv = rng.randint(9, 10)
    vs = [f"x{i}" for i in range(nv)]
    atoms: list[Atom] = []
    for v in vs:
        if rng.random() < 0.85:
            if rng.random() < 0.5:
                atoms.append({"eff": "Permit", "lits": [(v, True)], "duties": []})
            else:
                atoms.append({"eff": "Forbid", "lits": [(v, False)], "duties": []})
        if rng.random() < 0.85:
            if rng.random() < 0.5:
                atoms.append({"eff": "Permit", "lits": [(v, False)], "duties": []})
            else:
                atoms.append({"eff": "Forbid", "lits": [(v, True)], "duties": []})
    ds = [f"d{i}" for i in range(rng.randint(0, 1))]
    for a in atoms:  # occasional duties, so Pending is reachable
        if ds and a["eff"] == "Permit" and rng.random() < 0.5:
            a["duties"] = list(ds)
    rng.shuffle(atoms)
    return atoms, rng.choice(["prohibit", "perm", "invalid"]), vs + ds


def main() -> int:
    rng = random.Random(20261011)
    n, mism, tighter = 50000, 0, 0
    for _ in range(n):
        atoms, conflict, vars_ = rand_case(rng)
        b, a = brute(atoms, conflict, vars_), algorithm(atoms, conflict, vars_)
        if a != b:
            mism += 1
            if mism <= 3:
                print("MISMATCH", conflict, atoms, b, a)
        if b != "Indeterminate" and independent(atoms, conflict, vars_) == "Indeterminate":
            tighter += 1
    print(f"{n} cases, {mism} mismatches; definite under v0.6, Indeterminate before: {tighter}")
    # Beyond the bound (workflows §6.4): the fallback is sound — its verdict is
    # brute force's own or Indeterminate; when exact, it must equal brute force.
    rng2 = random.Random(20261012)
    n2, unsound, fallbacks, lost = 1000, 0, 0, 0
    for _ in range(n2):
        atoms, conflict, vars_ = rand_wide(rng2)
        b = brute(atoms, conflict, vars_)
        v, ex = bounded(atoms, conflict, vars_)
        if v != "Indeterminate" and v != b:
            unsound += 1
            print("UNSOUND", conflict, atoms, b, v)
        if not ex:
            fallbacks += 1
            if v == "Indeterminate" and b != "Indeterminate":
                lost += 1
    print(
        f"{n2} wide cases, {unsound} unsound; fallback in {fallbacks}, "
        f"Indeterminate there where the exact reading decides: {lost}"
    )
    # decisions/0003: guarded preconditions, guards evaluated in W2 (owed), not hoisted.
    rng3 = random.Random(20261013)
    n3, mism3, guard_mixed = 50000, 0, 0
    for _ in range(n3):
        atoms, conflict, vars_, guards = rand_guarded(rng3)
        b, a = brute(atoms, conflict, vars_, guards), algorithm(atoms, conflict, vars_, guards)
        if a != b:
            mism3 += 1
            if mism3 <= 3:
                print("MISMATCH (guarded)", conflict, atoms, guards, b, a)
        d = directions(atoms, guards)
        if any(len(d.get(v, set())) == 2 for g in guards.values() for v, _ in g):
            guard_mixed += 1
    print(f"{n3} guarded-duty cases, {mism3} mismatches; a guard variable mixed in {guard_mixed}")
    # Deadlines and violated preconditions (§6.1, §6.4 proof).
    rng4 = random.Random(20261014)
    n4, mism4 = 50000, 0
    for _ in range(n4):
        atoms, conflict, vars_, guards, kw = rand_deadlines(rng4)
        b, a = (
            brute(atoms, conflict, vars_, guards, **kw),
            algorithm(atoms, conflict, vars_, guards, **kw),
        )
        if a != b:
            mism4 += 1
            if mism4 <= 3:
                print("MISMATCH (deadlines)", conflict, atoms, guards, kw, b, a)
    print(f"{n4} deadline cases, {mism4} mismatches")
    # The listed frontier and frontier_complete (§6.3, §6.4, decisions/0004 and 0026), for
    # definite Pending verdicts, against their definitions by brute force over every
    # unknown. Gates: the bounded enumeration over the relevant unknowns equals both; with a
    # bound of 1, so that the fallback runs, every route listed suffices.
    rng5 = random.Random(20261015)
    n5 = 50000
    pending = empty = open_empty = old_empty = gained = old_unsound = incomplete = rule_loose = 0
    mism5 = unsound5 = fell = 0
    for _ in range(n5):
        atoms, conflict, vars_, guards, kw, known = rand_frontier(rng5)
        unknown = [v for v in vars_ if v not in known]
        runs = [
            evaluate(
                atoms, conflict, {**known, **dict(zip(unknown, bits, strict=True))}, guards, **kw
            )
            for bits in itertools.product([False, True], repeat=len(unknown))
        ]
        if {v for v, _, _ in runs} != {"Pending"}:
            continue
        pending += 1
        enough = sufficient(o for _, _, o in runs)
        front = listed(o for _, _, o in runs)  # the definition, by brute force
        complete = all(f == front for _, f, _ in runs)
        old, uncertain, _ = fallback_frontier(
            atoms, conflict, known, guards, kw.get("past", {}), v033=True
        )
        empty += not front
        open_empty += not any(all(r in o for _, _, o in runs) for r in runs[0][2])
        old_empty += not old
        gained += front != old
        old_unsound += not old <= enough
        incomplete += not complete
        rule_loose += uncertain and complete  # what 'complete iff no uncertain candidate' loses
        got, fc, exact = frontier_complete(atoms, conflict, known, guards, kw)
        if not exact or got != front or fc != complete:
            mism5 += 1
            if mism5 <= 3:
                print("MISMATCH (frontier)", conflict, atoms, guards, kw, known, front, got)
        got1, fc1, exact1 = frontier_complete(atoms, conflict, known, guards, kw, bound=1)
        fell += not exact1
        unsound5 += not got1 <= enough or (exact1 and (got1, fc1) != (front, complete))
    print(
        f"{n5} partial-knowledge cases, definite Pending in {pending}: listed frontier empty in "
        f"{empty} (v0.33: {old_empty}; routes open in every completion: {open_empty}); differs from v0.33's in {gained}; v0.33 listed a route "
        f"that does not suffice in {old_unsound}; frontier_complete false in "
        f"{incomplete}, true where an uncertain candidate exists in {rule_loose}; bounded "
        f"enumeration {mism5} mismatches; with bound 1, fallback in {fell}, {unsound5} unsound"
    )
    return 1 if mism or unsound or mism3 or mism4 or mism5 or unsound5 else 0


if __name__ == "__main__":
    raise SystemExit(main())
