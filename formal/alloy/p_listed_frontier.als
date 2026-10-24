/*
 * Claim P of correctness-strategy.md §4.8: the listed frontier under unknowns (decisions/0026).
 *
 * A route is an outstanding set. It is open in a completion when some candidate that survives
 * §6.2 there has it, and it suffices when it is open in some completion and every completion has
 * an open route within it. For a definite `Pending` or `Permit`, the listed frontier is the
 * non-dominated routes that suffice (§6.3). Beyond max_frontier_vars, W3 lists the routes of the
 * candidates that are ready or pending whatever the unknowns are and that no completion removes
 * in §6.2 (§6.4). The model checks:
 *
 *   NoOmission        A route that every completion's frontier offers is listed: the omission
 *                     decisions/0019 found cannot happen.
 *   PermitListsEmpty  For a definite `Permit`, the listed frontier is the empty route.
 *   FallbackSound     Every candidate the fallback lists survives in every completion, so its
 *                     route suffices.
 *
 * That fulfilling a listed route's duties permits in every completion follows from claim M
 * (m_monotonicity.als) and is argued in decisions/0026. Three runs show routes that the
 * definition lists: a route no single permission gives in every completion (decisions/0019's
 * second run), a route open only in some completions, and a route that a smaller one dominates
 * in some completion (decisions/0019's first run). Two more show an empty listed frontier, and
 * why the fallback must exclude a candidate whose policy is under `invalid` with a `U`
 * prohibition.
 *
 * W3 is resolve.als, and the worlds are every completion (everyCompletion). A route is named by
 * a world and a candidate surviving there: outstanding[w, p].
 *
 * A bare § is a section of due2-workflows.md v0.34.
 *
 * Run: formal/alloy/run.sh formal/alloy/p_listed_frontier.als.
 * The scopes and times are in README.md.
 */
module p_listed_frontier

open resolve

fact { everyCompletion }

pred definitePending { all w: World | verdict[w] = Pending }

pred definitePermit { all w: World | verdict[w] = Permit }

pred suffices[w: World, p: Permission] {
  p in survivors[w]
  all w2: World | some q: survivors[w2] | outstanding[w2, q] in outstanding[w, p]
}

// A route that suffices, and that no route that suffices strictly dominates.
pred isListed[w: World, p: Permission] {
  suffices[w, p]
  no w2: World, q: Permission |
    suffices[w2, q]
    and outstanding[w2, q] in outstanding[w, p] and outstanding[w2, q] != outstanding[w, p]
}

// Permission p gives, in world w, a route that every world's frontier offers.
pred offeredEverywhere[w: World, p: Permission] {
  p in frontier[w]
  all w2: World | some q: frontier[w2] | outstanding[w2, q] = outstanding[w, p]
}

assert NoOmission {
  definitePending implies all w: World, p: Permission | offeredEverywhere[w, p] implies isListed[w, p]
}

assert PermitListsEmpty {
  definitePermit implies {
    some w: World, p: Permission | isListed[w, p]
    all w: World, p: Permission | isListed[w, p] implies no outstanding[w, p]
  }
}

// §6.1: a candidate is ready or pending whatever the unknowns are when its permission is `T`, no
// precondition's open value is `U`, and no precondition is lapsed, unfulfilled, and owed `T` or
// `U`. That also makes its outstanding set the same in every completion. The fallback keeps it unless a
// `T` prohibition removes it in §6.2, or its policy is under `invalid` with a `U` prohibition.
pred definite[p: Permission] {
  tApplies[p]
  no d: p.pre | openU[d] or (d in Lapsed and fulF[d] and d not in OwedRefuted)
}

pred removedByT[p: Permission] {
  p.policy.conflict in Prohibit + Invalid
  some f: Prohibition & policy.(p.policy) | tApplies[f]
}

pred removedByU[p: Permission] {
  p.policy.conflict = Invalid
  some f: Prohibition & policy.(p.policy) | uApplies[f]
}

fun fallback: set Permission { { p: Permission | definite[p] and not removedByT[p] and not removedByU[p] } }

assert FallbackSound {
  definitePending implies all p: fallback, w: World | p in survivors[w]
}

// decisions/0019's second run: a listed route that no single permission gives everywhere.
run NoSingleGiver {
  definitePending
  some w: World, p: Permission | isListed[w, p] and no q: Permission | all w2: World |
    q in survivors[w2] and outstanding[w2, q] = outstanding[w, p]
} for 3 but 4 World

// A listed route that some completion does not offer at all: a `fulfilled` finding is `U`.
run OpenInSome {
  definitePending
  some w: World, p: Permission | isListed[w, p] and some w2: World |
    no q: survivors[w2] | outstanding[w2, q] = outstanding[w, p]
} for 3 but 4 World

// decisions/0019's first run: a listed route that a smaller one dominates in some completion.
run DominatedInSome {
  definitePending
  some w: World, p: Permission | isListed[w, p] and some w2: World | p in survivors[w2] - frontier[w2]
} for 3 but 4 World

// What to do depends on an unknown: nothing suffices.
run EmptyListed {
  definitePending
  no w: World, p: Permission | isListed[w, p]
} for 3 but 4 World

// Without removedByU, the fallback would list a candidate that some completion removes.
run InvalidNeedsExclusion {
  definitePending
  some p: Permission, w: World | definite[p] and not removedByT[p] and p not in survivors[w]
} for 3 but 4 World

check NoOmission for 3 but 8 World
check PermitListsEmpty for 3 but 8 World
check FallbackSound for 3 but 8 World
