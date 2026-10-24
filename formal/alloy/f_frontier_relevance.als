/*
 * Claim F of correctness-strategy.md §4.8: frontier relevance.
 *
 * For a definite `Pending`, the relevant unknowns are the variables of the `U` parts of
 * uncertain candidates (permission, `owed`, `fulfilled`) and of prohibitions whose finding is
 * `U`, and "no other unknown can move the frontier while the verdict stands" (due2-workflows.md
 * v0.33 §6.4, frontier_complete; decisions/0004). W3 therefore enumerates only the relevant
 * unknowns to decide frontier_complete. The model checks a stronger claim, which needs no
 * quantifier over every completion:
 *
 *   Relevant   Two completions that both give `Pending` and agree on every relevant unknown
 *              have one frontier, with one outstanding set per candidate in it.
 *
 * A definite `Pending` gives `Pending` in every completion, so the claim covers it.
 *
 * W3 is resolve.als, and the findings come from the variables (fromVars). Before completion,
 * every variable is `U`.
 *
 * A bare § is a section of due2-workflows.md v0.33.
 *
 * Run: formal/alloy/run.sh formal/alloy/f_frontier_relevance.als.
 * The scopes and times are in README.md.
 */
module f_frontier_relevance

open resolve

one sig C1, C2 extends World {}

fact { fromVars[C1] and fromVars[C2] }

// A permission is a candidate before completion when it applies `T` or `U` and no
// precondition is owed `T` and violated: unfulfilled `F`, with its deadline passed (§6.1).
pred candidate[p: Permission] {
  p not in Refuted
  no d: p.pre | tOwed[d] and fulF[d] and d in Lapsed
}

// §6.1: uncertain when the permission is `U`, or some duty's open value is `U`.
fun uncertain: set Permission {
  { p: Permission | candidate[p] and (uApplies[p] or some d: p.pre | openU[d]) }
}

// The relevant unknowns: the variables of the `U` parts of uncertain candidates, and of `U`
// prohibitions, and the unknown `fulfilled` findings of uncertain candidates' preconditions.
fun relevantVars: set Var {
  readsApplies[uncertain] + readsOwed[uncertain.pre]
  + { x: Var | some f: Prohibition | uApplies[f] and x in readsApplies[f] }
}

fun relevantFulfilled: set Duty { uncertain.pre & Unknown }

pred agreeOnRelevant[a, b: World] {
  a.val & relevantVars = b.val & relevantVars
  a.fulfilled & relevantFulfilled = b.fulfilled & relevantFulfilled
}

assert Relevant {
  (verdict[C1] = Pending and verdict[C2] = Pending and agreeOnRelevant[C1, C2]) implies {
    frontier[C1] = frontier[C2]
    all p: frontier[C1] | outstanding[C1, p] = outstanding[C2, p]
  }
}

// Not vacuous: two `Pending` completions whose frontiers differ, on a relevant unknown.
run RelevantMoves {
  verdict[C1] = Pending and verdict[C2] = Pending
  frontier[C1] != frontier[C2]
} for 3

// Not vacuous: two `Pending` completions that differ on an unknown that is not relevant.
run IrrelevantDiffers {
  verdict[C1] = Pending and verdict[C2] = Pending
  agreeOnRelevant[C1, C2]
  C1.val != C2.val
} for 3

check Relevant for 6
