/*
 * W3 over one completion: candidates, conflict, frontier, and verdict (due2-workflows.md v0.34
 * §6.1–§6.4, with decisions/0045). A module, opened by the models of claims M, F, W, and P; it
 * has no commands.
 *
 * A world is a completion: every finding is `T` or `F`. A world states its findings as the
 * atoms and duties for which they are `T`. fromVars below derives them from an assignment to
 * the completion variables, for the models that need the variables.
 *
 * What the module leaves out, and why that does not weaken the models that open it:
 *
 * - Instances. A duty is one instance, with one `fulfilled` finding (§5.3). Recurrence adds
 *   instances, each a duty here.
 * - Timing. Whether an instance's deadline has passed is fixed by the evaluation, not a finding
 *   (§5.3), so it is a set of duties, `Lapsed`, the same in every world.
 * - Root obligations. A violated obligation is reported and never moves the verdict
 *   (decisions/0045), so no finding of an obligation reaches W3's verdict or its basis.
 * - Other cross-policy strategies. Across policies the rule is prohibit-overrides (§6.2 #2,
 *   decisions/0045), the only one claim M states.
 * - Grounds. The frontier is a set of candidates, not of alternatives; two candidates with one
 *   outstanding set are one alternative with two grounds (§6.3 #1).
 *
 * A bare § is a section of due2-workflows.md v0.34.
 */
module resolve

// Verdicts, in the order of §6.4: Deny < NotApplicable < Pending < Permit.

abstract sig Verdict { rank: one Int }
one sig Deny, NotApplicable, Pending, Permit extends Verdict {}

fact ranks {
  Deny.rank = 0
  NotApplicable.rank = 1
  Pending.rank = 2
  Permit.rank = 3
}

// Policies, atoms, and duties (§3.1)

abstract sig Strategy {}
one sig Prohibit, Perm, Invalid extends Strategy {}

sig Policy { conflict: one Strategy }

abstract sig Rule {
  policy: one Policy,
  // The literals of its `applies` finding: variables read true, and read false.
  pos, neg: set Var
}
sig Permission extends Rule { pre: set Duty }
sig Prohibition extends Rule {}

sig Duty {
  // The literals of its `owed` finding.
  opos, oneg: set Var
}
// Instances whose deadline has passed: effective_at > D (§5.3).
sig Lapsed in Duty {}

// A completion. `applies` holds the rules whose finding is `T`, `owed` the preconditions whose
// `owed` is `T`, and `fulfilled` the duties whose `fulfilled` is `T` (§5.1).
sig World {
  applies: set Rule,
  owed: set Duty,
  fulfilled: set Duty,
  // The completion variables that are `T`, for fromVars.
  val: set Var
}

// §5.3: within a completion, the violated instances are the unfulfilled duties whose deadline
// has passed.
fun violated[w: World]: set Duty { Lapsed - w.fulfilled }

// §6.1: a permission that applies is closed when a precondition is owed and violated, and is a
// candidate otherwise. A candidate's outstanding set is its open preconditions: owed and not
// fulfilled. A violated one closes the candidate instead.
fun closed[w: World]: set Permission {
  { p: Permission & w.applies | some p.pre & w.owed & violated[w] }
}

fun candidates[w: World]: set Permission { (Permission & w.applies) - closed[w] }

fun outstanding[w: World, p: Permission]: set Duty { p.pre & w.owed - w.fulfilled }

// §6.2 #1, within a policy. Under `prohibit` a prohibition that applies eliminates the policy's
// candidates. Under `perm` a candidate eliminates its prohibitions. Under `invalid` the two
// together void the policy.
fun survivingProhibitions[w: World]: set Prohibition {
  { f: Prohibition & w.applies |
      not (f.policy.conflict in Perm + Invalid and some candidates[w] & policy.(f.policy)) }
}

fun keptCandidates[w: World]: set Permission {
  { p: candidates[w] |
      not (p.policy.conflict in Prohibit + Invalid
           and some Prohibition & w.applies & policy.(p.policy)) }
}

// §6.4: only a surviving prohibition denies.
pred denies[w: World] { some survivingProhibitions[w] }

// §6.2 #2, prohibit-overrides across policies: a surviving prohibition eliminates every
// candidate.
fun survivors[w: World]: set Permission { denies[w] => none else keptCandidates[w] }

// §6.3: the frontier is the surviving candidates whose outstanding set no other's strictly
// contains.
fun frontier[w: World]: set Permission {
  { p: survivors[w] |
      no q: survivors[w] |
        outstanding[w, q] in outstanding[w, p] and outstanding[w, q] != outstanding[w, p] }
}

fun verdict[w: World]: one Verdict {
  denies[w] => Deny
  else (some p: frontier[w] | no outstanding[w, p]) => Permit
  else some frontier[w] => Pending
  else NotApplicable
}

// Completion variables (§6.4, "Completions range over literals")

// A completed literal's variable, or an opaque part's. K is checked in k_completion_key.als;
// here a variable is any input that a completion sets.
sig Var {}

// Each finding is a conjunction of literals, as a finding is the Kleene conjunction of its
// parts (§5.2): `applies` reads `pos` true and `neg` false, and so does `owed` (opos, oneg).
// A finding in a `Refuted` set has a part that is `F`, and a finding
// with no literal and none `F` is `T`. A duty's `fulfilled` is one variable of its own (§6.4):
// `T` for a duty in `Met`, `F` for one in neither, and free in each world for one in `Unknown`.
sig Refuted in Rule {}
sig OwedRefuted in Duty {}
sig Met in Duty {}
sig Unknown in Duty {}

fact findings {
  no Met & Unknown
  // Only a precondition has an `owed` finding.
  (opos + oneg).Var in Permission.pre
}

pred holds[w: World, ps, ns: set Var] { ps in w.val and no ns & w.val }

// The findings of world w are those its variables give.
pred fromVars[w: World] {
  w.applies = { r: Rule - Refuted | holds[w, r.pos, r.neg] }
  w.owed = { d: Duty - OwedRefuted | holds[w, d.opos, d.oneg] }
  w.fulfilled = Met + (w.fulfilled & Unknown)
}

// The variables a finding reads.
fun readsApplies[r: Rule]: set Var { r.pos + r.neg }
fun readsOwed[d: Duty]: set Var { d.opos + d.oneg }

// Before completion, every variable is `U`. A finding is then `F` when refuted, `T` when it
// reads no variable, and `U` otherwise (§5.1).
pred uApplies[r: Rule] { r not in Refuted and some readsApplies[r] }
pred tApplies[r: Rule] { r not in Refuted and no readsApplies[r] }
pred uOwed[d: Duty] { d not in OwedRefuted and some readsOwed[d] }
pred tOwed[d: Duty] { d not in OwedRefuted and no readsOwed[d] }

// Before completion (§5.1). `owed` is `F` when refuted, `T` with no literal, `U` otherwise;
// `fulfilled` is `T` in Met, `U` in Unknown, and `F` otherwise.
pred fulF[d: Duty] { d not in Met + Unknown }

// §6.1: open is owed ∧ ¬fulfilled, in Kleene logic. Its value is `U` when neither is `F`
// (owed, unfulfilled), not both are `T`, and not `fulfilled` `T`.
pred openU[d: Duty] {
  d not in OwedRefuted and d not in Met
  (uOwed[d] or d in Unknown)
}

// The worlds are every completion: closed under flipping one variable, or one unknown
// `fulfilled`. Within its scope on World, a model that asserts this sees every completion.
pred everyCompletion {
  some World
  all w: World | fromVars[w]
  // No two worlds are one completion, which spares the solver their permutations.
  all disj w, w2: World | w.val != w2.val or w.fulfilled != w2.fulfilled
  all w: World, x: Var | some w2: World |
    w2.val = w.val - x + (x - w.val) and w2.fulfilled = w.fulfilled
  all w: World, d: Unknown | some w2: World |
    w2.val = w.val and w2.fulfilled = w.fulfilled - d + (d - w.fulfilled)
}
