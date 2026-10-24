/*
 * Question P of correctness-strategy.md §4.8: the listed frontier under unknowns.
 *
 * Under unknowns, the reply lists the frontier of the candidates that are ready or pending
 * whatever the unknowns are; an uncertain candidate enters only through the verdict
 * (due2-workflows.md v0.33 §6.3). decisions/0019 found a definite `Pending` whose listed frontier
 * omits a route that every completion offers, because no single permission gives it. P is a
 * question for the spec, not a claim, so the model characterises the omission:
 *
 *   ListedGiver      A route that one permission gives in every completion is listed, unless
 *                    some finding reads a variable both ways.
 *   Flagged          An omission comes with frontier_complete false: some completion's frontier
 *                    is not the listed one.
 *   NeedsMixed       An omission needs a mixed variable, one read both upward and downward
 *                    (§6.4, Computing it).
 *   TwoRoutes        Without a finding that reads a variable both ways, an omission needs two
 *                    permissions that read one mixed variable, in their own findings or their
 *                    preconditions' `owed`.
 *
 * The runs show one instance of each shape found: complementary permissions (decisions/0019),
 * a precondition that closes one route where another permission opens it, complementary
 * preconditions, and a finding that
 * reads a variable both ways.
 *
 * A route is an outstanding set. The listed frontier is formed from the ready and pending
 * candidates that no `T` atom removes in §6.2, as clingo-i reads §6.3. W3 is resolve.als, and the
 * worlds are every completion (everyCompletion).
 *
 * A bare § is a section of due2-workflows.md v0.33.
 *
 * Run: formal/alloy/run.sh formal/alloy/p_listed_frontier.als.
 * The scopes and times are in README.md.
 */
module p_listed_frontier

open resolve

fact { everyCompletion }

pred definitePending { all w: World | verdict[w] = Pending }

// §6.1: a candidate is ready or pending when its permission is `T` and no precondition's open
// value is `U`, nor is a violated precondition's `owed`. It survives §6.2 when no `T` prohibition
// of its policy removes it: a `U` atom removes nothing (§6.2). This is clingo-i's reading
// (explain.lp, listed). Its outstanding set is the same in every completion.
fun definiteCandidates: set Permission {
  { p: Permission |
      tApplies[p]
      and (no d: p.pre | openU[d] or (d in Lapsed and fulF[d] and uOwed[d]))
      and (no d: p.pre | d in Lapsed and fulF[d] and tOwed[d])
      and not (p.policy.conflict in Prohibit + Invalid
           and some f: Prohibition & policy.(p.policy) | tApplies[f]) }
}

// The listed frontier: the definite candidates whose outstanding set no other's strictly
// contains. Their outstanding set is the same in every world.
fun listed: set Permission {
  { p: definiteCandidates |
      no q: definiteCandidates | all w: World |
        outstanding[w, q] in outstanding[w, p] and outstanding[w, q] != outstanding[w, p] }
}

// Permission p gives, in world w, a route that every world's frontier offers.
pred offeredEverywhere[w: World, p: Permission] {
  p in frontier[w]
  all w2: World | some q: frontier[w2] | outstanding[w2, q] = outstanding[w, p]
}

pred isListed[w: World, p: Permission] {
  some l: listed | outstanding[w, l] = outstanding[w, p]
}

// The omission of decisions/0019: a route every completion offers that is not listed.
pred omission {
  definitePending
  some w: World, p: Permission | offeredEverywhere[w, p] and not isListed[w, p]
}

// No finding reads a variable both ways, as `x eq 5` and `x neq 5` in one `and` would. Such a
// finding is `U` before completion and `F` in every completion.
pred consistent {
  no r: Rule | some r.pos & r.neg
  no d: Duty | some d.opos & d.oneg or some d.ipos & d.ineg
}

pred givesEverywhere[p: Permission] { all w: World | offeredEverywhere[w, p] }

assert ListedGiver {
  definitePending and consistent implies all p: Permission |
    givesEverywhere[p] implies some w: World | isListed[w, p]
}

assert Flagged {
  omission implies some w: World |
    not (all p: frontier[w] | isListed[w, p])
    or some l: listed | no p: frontier[w] | outstanding[w, p] = outstanding[w, l]
}

// The directions of §6.4, as in m_monotonicity.als.
fun up: set Var {
  Permission.pos + Prohibition.neg + Duty.oneg
  + (Config.violations = DenyViolations => Obligation.ineg else none)
}

fun down: set Var {
  Permission.neg + Prohibition.pos + Duty.opos
  + (Config.violations = DenyViolations => Obligation.ipos else none)
}

assert NeedsMixed { omission implies some up & down }

// The variables a route's permission reads: its own, and its preconditions' `owed`.
fun routeReads[p: Permission]: set Var { readsApplies[p] + readsOwed[p.pre] }

assert TwoRoutes {
  omission and consistent implies
    some disj p, q: Permission | some routeReads[p] & routeReads[q] & up & down
}

// The decisions/0019 shape: two permissions on x and on ¬x with one outstanding set.
run Shape0019 { omission and one Var and #Permission = 3 } for 3 but 4 World

// A closing precondition: a lapsed precondition, owed on x, closes one route where the other permission,
// on x, opens the same route. No permission reads x both ways.
run ClosingPrecondition {
  omission and consistent
  no Permission.pos & Permission.neg
  some Permission.pre & Lapsed
  some Permission.(pos + neg) & Duty.(opos + oneg)
} for 3 but 4 World

// Complementary preconditions: two `T` permissions whose preconditions are owed on x and on ¬x.
run ComplementaryPreconditions {
  omission and consistent
  no Permission.pos + Permission.neg
} for 3 but 4 World

// A self-contradictory finding hides a route that one permission gives in every completion.
run SelfContradiction {
  definitePending
  some p: Permission | givesEverywhere[p] and no l: listed | all w: World |
    outstanding[w, l] = outstanding[w, p]
} for 3 but 4 World

check ListedGiver for 3 but 8 World
check Flagged for 3 but 8 World
check NeedsMixed for 3 but 8 World
check TwoRoutes for 3 but 8 World
