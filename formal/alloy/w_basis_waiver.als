/*
 * Claim W of correctness-strategy.md §4.8: the basis waiver.
 *
 * Under unknowns, verdict_basis names the atoms that play their role in every completion
 * (due2-workflows.md v0.34 §6.4; decisions/0016 #4). A verdict that holds by cases has none.
 * tools/check_corpus.py therefore waives the basis check for a definite `Permit` or `Deny`
 * whose scenario lists an `unresolved` unknown part. The claim that makes the waiver safe:
 *
 *   Waiver   A definite `Permit` or `Deny` with an empty basis has a `U` finding that reads a
 *            variable read by some other literal too.
 *
 * Only a completed part, one whose operand is `unresolved`, shares a variable (decisions/0016),
 * and such a part is listed as an unknown part (§5.4). So the claim gives the scenario a listed
 * `unresolved` part. The argument is in spikes/clingo-i/lp/resolve.lp,
 * *The cautious basis*.
 *
 * The basis roles are those of §6.4: under `Permit`, the ready alternative's permissions, here
 * every permission in the frontier; under `Deny`, the surviving prohibitions, and, under
 * `deny`, the obligations in force with a violated instance.
 *
 * W3 is resolve.als. The worlds are every completion (everyCompletion), so the scope on World
 * bounds the unknowns: 8 worlds hold every completion of three.
 *
 * A bare § is a section of due2-workflows.md v0.34.
 *
 * Run: formal/alloy/run.sh formal/alloy/w_basis_waiver.als.
 * The scopes and times are in README.md.
 */
module w_basis_waiver

open resolve

fact { everyCompletion }

pred definite[v: Verdict] { all w: World | verdict[w] = v }

fun permitBasis: set Permission { { p: Permission | all w: World | p in frontier[w] } }

fun denyBasis: set Rule + Duty {
  { f: Prohibition | all w: World | f in survivingProhibitions[w] }
  + { d: Obligation |
        Config.violations = DenyViolations and all w: World | d in w.inForce & violated[w] }
}

pred emptyBasis {
  definite[Permit] and no permitBasis
  or definite[Deny] and no denyBasis
}

// Two literals read x: two findings, or one finding both ways. Counted without arithmetic,
// which would overflow Alloy's small integers.
pred readTwice[x: Var] {
  let ap = pos.x + neg.x, ow = opos.x + oneg.x, inf = ipos.x + ineg.x {
    not lone ap or not lone ow or not lone inf
    or (some ap and some ow + inf) or (some ow and some inf)
    or some pos.x & neg.x or some opos.x & oneg.x or some ipos.x & ineg.x
  }
}

// A `U` finding reads x.
pred readByU[x: Var] {
  (some r: Rule | uApplies[r] and x in readsApplies[r])
  or (some d: Duty | uOwed[d] and x in readsOwed[d])
  or (some d: Duty | uInForce[d] and x in readsInForce[d])
}

assert Waiver {
  emptyBasis implies some x: Var | readTwice[x] and readByU[x]
}

// Not vacuous: an empty basis under `Permit`, and one under `Deny`.
run EmptyPermit { definite[Permit] and no permitBasis } for 3 but 4 World
run EmptyDeny { definite[Deny] and no denyBasis } for 3 but 4 World

check Waiver for 3 but 8 World
