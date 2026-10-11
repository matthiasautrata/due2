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

Scope: verdicts only. No config.violations = deny, no frontier or obligation
output, and atoms are flat conjunctions — a sanity check of §6.4's completion
claim, not a proof, and not a check of the rest of W3.
"""
import itertools
import random


def verdict(atoms, conflict, val, guards=None):
    guards = guards or {}

    def holds(lits):
        return all(val[v] == pol for v, pol in lits)
    perms = [a for a in atoms if a["eff"] == "Permit" and holds(a["lits"])]
    forbs = [a for a in atoms if a["eff"] == "Forbid" and holds(a["lits"])]
    if conflict == "prohibit" and forbs:
        perms = []
    elif conflict == "perm" and perms:
        forbs = []
    elif conflict == "invalid" and perms and forbs:
        perms, forbs = [], []
    if forbs:
        return "Deny"
    sets = [frozenset(d for d in a["duties"] if holds(guards.get(d, [])) and not val[d])
            for a in perms]   # decisions/0003: outstanding = owed and not fulfilled
    if any(not s for s in sets):
        return "Permit"
    return "Pending" if sets else "NotApplicable"


def brute(atoms, conflict, vars_, guards=None):
    vs = {verdict(atoms, conflict, dict(zip(vars_, bits)), guards)
          for bits in itertools.product([False, True], repeat=len(vars_))}
    return vs.pop() if len(vs) == 1 else "Indeterminate"


def directions(atoms, guards=None):
    """Per variable, the set of directions its occurrences move the verdict (True = up).
    A guard literal of a precondition duty moves it down when positive: more owed,
    lower verdict (decisions/0003)."""
    d = {}
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


def algorithm(atoms, conflict, vars_, guards=None):
    d = directions(atoms, guards)
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
            seen.add(verdict(atoms, conflict, val, guards))
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
    return 1 if mism or unsound or mism3 else 0


if __name__ == "__main__":
    raise SystemExit(main())
