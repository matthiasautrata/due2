/*
 * Claim M of correctness-strategy.md §4.8: monotonicity.
 *
 * Under all three strategies and the default combination, "the verdict is monotone in every
 * finding", so the two extreme completions bound every completion's verdict (due2-workflows.md
 * v0.34 §6.4, Computing it). The model checks two claims:
 *
 *   Monotone       Of two completions, the one with every permission and `fulfilled` finding
 *                  at least as true, and every prohibition, `owed`, and, under `deny`,
 *                  `in_force` finding at most as true, has a verdict at least as high.
 *   UniformBound   Fix the mixed variables of a completion and set the uniform ones to one
 *                  extreme: the verdict moves only towards that extreme. This is the
 *                  computation of §6.4, which enumerates the mixed variables and completes the
 *                  uniform ones at both extremes.
 *
 * W3 is resolve.als. Monotone compares any two completions, so it states nothing about the
 * variables. UniformBound reads the findings from the variables (resolve.als, fromVars).
 *
 * A bare § is a section of due2-workflows.md v0.34.
 *
 * Run: formal/alloy/run.sh formal/alloy/m_monotonicity.als.
 * The scopes and times are in README.md.
 */
module m_monotonicity

open resolve

one sig Lo, Hi extends World {}

// Hi is at least as permissive as Lo, finding by finding.
pred morePermissive[lo, hi: World] {
  Permission & lo.applies in hi.applies
  Prohibition & hi.applies in lo.applies
  hi.owed in lo.owed
  hi.inForce in lo.inForce
  lo.fulfilled in hi.fulfilled
}

assert Monotone {
  morePermissive[Lo, Hi] implies verdict[Lo].rank <= verdict[Hi].rank
}

// Not vacuous: two completions in that order with different verdicts, under `invalid`.
run MonotoneStrict {
  morePermissive[Lo, Hi]
  verdict[Lo] = Deny
  verdict[Hi] = Permit
  Permission.policy.conflict = Invalid
} for 3

// The direction of each occurrence of a variable (§6.4, Computing it): upward when making it
// true can only raise the verdict, downward when it can only lower it. An `in_force` finding
// moves the verdict only under `deny`.
fun up: set Var {
  Permission.pos + Prohibition.neg + Duty.oneg
  + (Config.violations = DenyViolations => Obligation.ineg else none)
}

fun down: set Var {
  Permission.neg + Prohibition.pos + Duty.opos
  + (Config.violations = DenyViolations => Obligation.ipos else none)
}

fun mixed: set Var { up & down }

// e is completion c with every uniform variable set to its lower extreme, and every unknown
// `fulfilled` finding false.
pred lowerExtreme[c, e: World] {
  e.val = (c.val & mixed) + (c.val - up - down) + (down - up)
  e.fulfilled = c.fulfilled - Unknown
}

// And with every uniform variable at its upper extreme.
pred upperExtreme[c, e: World] {
  e.val = (c.val & mixed) + (c.val - up - down) + (up - down)
  e.fulfilled = c.fulfilled + Unknown
}

assert UniformBound {
  fromVars[Lo] and fromVars[Hi] implies {
    lowerExtreme[Hi, Lo] implies verdict[Lo].rank <= verdict[Hi].rank
    upperExtreme[Lo, Hi] implies verdict[Lo].rank <= verdict[Hi].rank
  }
}

// Not vacuous: a mixed variable, read both ways, and the two extremes of one assignment to it
// giving different verdicts.
run MixedVariable {
  fromVars[Lo] and fromVars[Hi]
  some mixed
  lowerExtreme[Hi, Lo]
  verdict[Lo] != verdict[Hi]
} for 3

check Monotone for 8
check UniformBound for 7
