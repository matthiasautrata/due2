#!/usr/bin/env python3
"""Randomised check of due2-workflows.md §6.4 (v0.6, completions over literals).

Claim: enumerating the mixed variables and completing the uniform ones at the
two extremes gives the same verdict (definite or Indeterminate) as brute force
over every assignment of every variable. Also counts how often v0.6 is definite
where the pre-v0.6 reading (every occurrence its own variable) was Indeterminate.

Model: one policy, conflict in {prohibit, perm, invalid}; Permit/Forbid atoms,
each a conjunction of literals (variable, polarity) over Boolean variables;
Permits carry precondition duties, each duty's fulfilment a variable, optionally
guarded by literals over the same variables (third phase). The verdict for a total
assignment follows §6.1-§6.4. Run: python3 tools/check_completion.py
Recorded result (seed 20261011): 50000 cases, 0 mismatches, 1244 newly definite.
Second phase (seed 20261012, `rand_wide`): the beyond-max_mixed fallback is
sound — 1000 wider cases, 0 unsound, fallback in 111, Indeterminate in 84 of
those where the exact reading decides.

Third phase (seed 20261013, `rand_guarded`, decisions/0003): precondition duties
keep their guards, evaluated in W2 as `owed`; a duty is outstanding when owed and
not fulfilled, and a positive guard occurrence moves the verdict down. 50000
cases, 0 mismatches. (The second-phase demo of a hoisted guard was removed with
hoisting; under 0003 w3c-fs-c2's guard is uniform and two extremes suffice.)

Fourth phase (seed 20261014, `rand_deny`): each duty's deadline has passed or
not (fixed per case, §5.3); an owed, unfulfilled, past-deadline precondition
removes its candidate (§6.1); root obligations, in force under literals over the
same variables, deny when violated under config.violations = deny (§6.4).
Recorded: 50000 cases, 0 mismatches, Deny under violations = deny in 3285.

Fifth phase (seed 20261015, `rand_frontier`): partial knowledge, each variable
known T, known F, or U. For every definite Pending, the frontier W3 lists from
ready and pending candidates (§6.1-§6.3) is compared with every completion's;
frontier_complete holds, by its §6.4 definition, iff all completions give the
listed frontier. The spec gives no computation for it; the checked rule is
"frontier_complete iff no candidate is uncertain", gated on soundness (never
true where some completion differs). Recorded: definite Pending in 942; listed
frontier empty in 191; a listed alternative off some completion's frontier in 4
(an uncertain candidate's smaller outstanding set dominates it); frontier_complete
false in 199; the rule wrong in 0, and false where the definition says true in
133 (sound, not exact; the exact computation is open, issue #29).

Scope: atoms are flat conjunctions; obligations carry no guards and no duties
of their own; no recurrence or instances. A sanity check of §6.4's claims, not
a proof, and not a check of the rest of W3 (that is the brute-force W3
differential, correctness-strategy.md §4.5).
"""
import itertools
import random


def evaluate(atoms, conflict, val, guards=None, past=None, obligations=None,
             violations="ignore"):
    """One completion (no U): (verdict, frontier), workflows §6.1-§6.4.
    past: duty -> its deadline has passed (fixed by the case, not a finding).
    obligations: root obligations, each {"lits": in_force literals, "duty": d}."""
    guards, past = guards or {}, past or {}

    def holds(lits):
        return all(val[v] == pol for v, pol in lits)

    def owed(d):
        return holds(guards.get(d, []))
    perms = [a for a in atoms if a["eff"] == "Permit" and holds(a["lits"])
             and not any(owed(d) and not val[d] and past.get(d) for d in a["duties"])]
    # §6.1: a violated precondition that is owed removes its candidate, under either
    # value of config.violations, before conflict resolution.
    forbs = [a for a in atoms if a["eff"] == "Forbid" and holds(a["lits"])]
    if conflict == "prohibit" and forbs:
        perms = []
    elif conflict == "perm" and perms:
        forbs = []
    elif conflict == "invalid" and perms and forbs:
        perms, forbs = [], []
    if forbs:
        return "Deny", frozenset()
    if violations == "deny" and any(holds(o["lits"]) and not val[o["duty"]] and past.get(o["duty"])
                                    for o in obligations or []):
        return "Deny", frozenset()   # §6.4: a violated obligation in force acts as a prohibition
    sets = {frozenset(d for d in a["duties"] if owed(d) and not val[d])
            for a in perms}   # decisions/0003: outstanding = owed and not fulfilled; §6.3 collapse
    frontier = frozenset(x for x in sets if not any(y < x for y in sets))
    if frozenset() in sets:
        return "Permit", frontier
    return ("Pending" if sets else "NotApplicable"), frontier


def verdict(atoms, conflict, val, guards=None, **kw):
    return evaluate(atoms, conflict, val, guards, **kw)[0]


def brute(atoms, conflict, vars_, guards=None, **kw):
    vs = {verdict(atoms, conflict, dict(zip(vars_, bits)), guards, **kw)
          for bits in itertools.product([False, True], repeat=len(vars_))}
    return vs.pop() if len(vs) == 1 else "Indeterminate"


def directions(atoms, guards=None, obligations=None, violations="ignore"):
    """Per variable, the set of directions its occurrences move the verdict (True = up).
    A guard literal of a precondition duty moves it down when positive: more owed,
    lower verdict (decisions/0003). Under violations = deny an obligation's in_force
    literal moves it like a prohibition's, and its fulfilment upwards (§6.4 proof)."""
    d = {}
    for lits in (guards or {}).values():
        for v, pol in lits:
            d.setdefault(v, set()).add(not pol)
    if violations == "deny":
        for o in obligations or []:
            for v, pol in o["lits"]:
                d.setdefault(v, set()).add(not pol)
            d.setdefault(o["duty"], set()).add(True)
    for a in atoms:
        up = a["eff"] == "Permit"
        for v, pol in a["lits"]:
            d.setdefault(v, set()).add(up == pol)
        for v in a["duties"]:
            d.setdefault(v, set()).add(True)
    return d


def algorithm(atoms, conflict, vars_, guards=None, **kw):
    d = directions(atoms, guards, kw.get("obligations"), kw.get("violations", "ignore"))
    mixed = [v for v in vars_ if len(d.get(v, {True})) == 2]
    uniform = [v for v in vars_ if v not in mixed]
    seen = set()
    for bits in itertools.product([False, True], repeat=len(mixed)):
        base = dict(zip(mixed, bits))
        for extreme in (True, False):   # most permissive, most restrictive
            val = dict(base)
            for v in uniform:
                up = d.get(v, {True}) == {True}
                val[v] = up if extreme else not up
            seen.add(verdict(atoms, conflict, val, guards, **kw))
    return seen.pop() if len(seen) == 1 else "Indeterminate"


def bounded(atoms, conflict, vars_, max_mixed=8):
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
    fresh, k = [], 0
    for a in atoms:
        lits = []
        for v, pol in a["lits"]:
            if v in mset:
                lits.append((f"m{k}", pol))
                k += 1
            else:
                lits.append((v, pol))
        fresh.append({**a, "lits": lits})
    uniform = [v for v in vars_ if v not in mset]
    return algorithm(fresh, conflict, [f"m{i}" for i in range(k)] + uniform), False


def independent(atoms, conflict, vars_):
    """Pre-v0.6: every literal occurrence its own variable."""
    fresh, k = [], 0
    for a in atoms:
        lits = []
        for _, pol in a["lits"]:
            lits.append((f"o{k}", pol))
            k += 1
        fresh.append({**a, "lits": lits})
    return algorithm(fresh, conflict, [f"o{i}" for i in range(k)] + [v for v in vars_ if v.startswith("d")])


def rand_case(rng):
    nv, nd = rng.randint(1, 4), rng.randint(0, 2)
    vs, ds = [f"x{i}" for i in range(nv)], [f"d{i}" for i in range(nd)]
    atoms = []
    for _ in range(rng.randint(1, 5)):
        eff = rng.choice(["Permit", "Permit", "Forbid"])
        lits = [(v, rng.random() < 0.5) for v in rng.sample(vs, rng.randint(0, min(2, nv)))]
        duties = rng.sample(ds, rng.randint(0, nd)) if eff == "Permit" else []
        atoms.append({"eff": eff, "lits": lits, "duties": duties})
    return atoms, rng.choice(["prohibit", "perm", "invalid"]), vs + ds


def rand_guarded(rng):
    """decisions/0003: precondition duties keep their guards (no hoisting). Each
    duty may carry guard literals over the same variables the rules read, so a
    guard can share a variable with a permission's or prohibition's constraint,
    in either polarity — the only way a guard becomes mixed."""
    nv, nd = rng.randint(1, 4), rng.randint(1, 3)
    vs, ds = [f"x{i}" for i in range(nv)], [f"d{i}" for i in range(nd)]
    guards = {d: [(v, rng.random() < 0.5) for v in rng.sample(vs, rng.randint(0, min(2, nv)))]
              for d in ds}
    atoms = []
    for _ in range(rng.randint(1, 4)):
        eff = rng.choice(["Permit", "Permit", "Forbid"])
        lits = [(v, rng.random() < 0.5) for v in rng.sample(vs, rng.randint(0, min(2, nv)))]
        duties = rng.sample(ds, rng.randint(0, nd)) if eff == "Permit" else []
        atoms.append({"eff": eff, "lits": lits, "duties": duties})
    return atoms, rng.choice(["prohibit", "perm", "invalid"]), vs + ds, guards


def rand_deny(rng):
    """Fourth phase: deadlines and config.violations. Each duty's deadline has passed
    or not (fixed per case); an owed, unfulfilled, past-deadline precondition removes
    its candidate; root obligations, in force under literals over the same variables,
    deny when violated under violations = deny. Obligation duties carry no guards
    (§6.4's proof counts owed only for preconditions)."""
    nv, nd = rng.randint(1, 4), rng.randint(1, 3)
    vs, ds = [f"x{i}" for i in range(nv)], [f"d{i}" for i in range(nd)]
    unguarded = set(rng.sample(ds, rng.randint(0, nd)))
    guards = {d: [(v, rng.random() < 0.5) for v in rng.sample(vs, rng.randint(0, min(2, nv)))]
              for d in ds if d not in unguarded}
    past = {d: rng.random() < 0.5 for d in ds}
    atoms = []
    for _ in range(rng.randint(1, 4)):
        eff = rng.choice(["Permit", "Permit", "Forbid"])
        lits = [(v, rng.random() < 0.5) for v in rng.sample(vs, rng.randint(0, min(2, nv)))]
        duties = rng.sample(ds, rng.randint(0, nd)) if eff == "Permit" else []
        atoms.append({"eff": eff, "lits": lits, "duties": duties})
    obligations = [{"lits": [(v, rng.random() < 0.5) for v in rng.sample(vs, rng.randint(0, min(2, nv)))],
                    "duty": d}   # an obligation may also be a precondition of a permission
                   for d in sorted(unguarded) if rng.random() < 0.7]
    kw = {"past": past, "obligations": obligations, "violations": rng.choice(["ignore", "deny"])}
    return atoms, rng.choice(["prohibit", "perm", "invalid"]), vs + ds, guards, kw


def kleene_and(xs):
    xs = list(xs)
    return False if False in xs else (None if None in xs else True)


def listed_frontier(atoms, conflict, known, guards, past):
    """The frontier W3 lists from three-valued findings (§6.1-§6.3): alternatives from
    surviving ready and pending candidates only; uncertain candidates (permission U,
    an unknown open duty, or a violated precondition whose owed is U) are left out.
    known: variable -> True/False, absent = U. Returns (frontier, any_uncertain)."""
    def lit(v, pol):
        return None if v not in known else known[v] == pol

    def val(lits):
        return kleene_and(lit(v, p) for v, p in lits)
    sure, uncertain, forbs_t = [], False, False
    for a in atoms:
        f = val(a["lits"])
        if a["eff"] == "Forbid":
            forbs_t = forbs_t or f is True
            continue
        if f is False:
            continue
        opens, removed, unsure = set(), False, f is None
        for d in a["duties"]:
            ow, fu = val(guards.get(d, [])), known.get(d)
            op = kleene_and([ow, None if fu is None else not fu])
            if fu is False and past.get(d):          # violated instance
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
        else:
            sure.append(frozenset(opens))
    if forbs_t and conflict == "prohibit":
        sure = []
    sets = set(sure)
    return frozenset(x for x in sets if not any(y < x for y in sets)), uncertain


def rand_frontier(rng):
    """Fifth phase: partial knowledge. Each variable is known T, known F, or unknown,
    so definite candidates exist beside uncertain ones and the listed frontier can be
    compared with every completion's."""
    atoms, conflict, vars_, guards, kw = rand_deny(rng)
    kw["violations"] = "ignore"
    known = {v: rng.random() < 0.5 for v in vars_ if rng.random() < 0.5}
    return atoms, conflict, vars_, guards, kw, known


def rand_wide(rng):
    """Instances sized to exceed max_mixed: each variable gets an up and a
    down occurrence with high probability, so most are mixed."""
    nv = rng.randint(9, 10)
    vs = [f"x{i}" for i in range(nv)]
    atoms = []
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
    for a in atoms:                       # occasional duties, so Pending is reachable
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
    print(f"{n2} wide cases, {unsound} unsound; fallback in {fallbacks}, "
          f"Indeterminate there where the exact reading decides: {lost}")
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
    # Deadlines, violated preconditions, and config.violations = deny (§6.1, §6.4 proof).
    rng4 = random.Random(20261014)
    n4, mism4, denied = 50000, 0, 0
    for _ in range(n4):
        atoms, conflict, vars_, guards, kw = rand_deny(rng4)
        b, a = brute(atoms, conflict, vars_, guards, **kw), algorithm(atoms, conflict, vars_, guards, **kw)
        if a != b:
            mism4 += 1
            if mism4 <= 3:
                print("MISMATCH (deny)", conflict, atoms, guards, kw, b, a)
        denied += b == "Deny" and kw["violations"] == "deny"
    print(f"{n4} deadline/violations cases, {mism4} mismatches; Deny under violations = deny in {denied}")
    # The listed frontier against every completion's, for definite Pending verdicts (§6.3,
    # frontier_complete in §6.4). Observations, not gates: the spec defines frontier_complete
    # by quantifying over completions and gives no computation, so these measure where the
    # listed frontier and the completions part ways.
    rng5 = random.Random(20261015)
    n5, pending, empty, wrong, incomplete, rule_unsound, rule_loose = 50000, 0, 0, 0, 0, 0, 0
    for _ in range(n5):
        atoms, conflict, vars_, guards, kw, known = rand_frontier(rng5)
        unknown = [v for v in vars_ if v not in known]
        fronts, verdicts = set(), set()
        for bits in itertools.product([False, True], repeat=len(unknown)):
            v, f = evaluate(atoms, conflict, {**known, **dict(zip(unknown, bits))}, guards, **kw)
            verdicts.add(v)
            fronts.add(f)
        if verdicts != {"Pending"}:
            continue
        pending += 1
        listed, uncertain = listed_frontier(atoms, conflict, known, guards, kw["past"])
        complete = fronts == {listed}             # the definition, by brute force
        empty += not listed
        wrong += any(not listed <= f for f in fronts) and bool(listed)
        incomplete += not complete
        rule_unsound += (not uncertain) and not complete   # proposed: complete iff no uncertain candidate
        rule_loose += uncertain and complete
    print(f"{n5} partial-knowledge cases, definite Pending in {pending}: listed frontier empty in {empty}; "
          f"a listed alternative off some completion's frontier in {wrong}; frontier_complete false in "
          f"{incomplete}; 'no uncertain candidate' claims complete wrongly in {rule_unsound}, "
          f"says incomplete where complete in {rule_loose}")
    return 1 if mism or unsound or mism3 or mism4 or rule_unsound else 0


if __name__ == "__main__":
    raise SystemExit(main())
