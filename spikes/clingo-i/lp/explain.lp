%# explain.lp: the eliminations, the listed frontier, the obligations, and the unknown parts
%
% The reply's `eliminated`, `frontier`, `obligations`, and `unknown_parts`, all read from the
% findings before completion, in the Kleene world `k`, not from a completion world, so they do
% not depend on the completion.
%
% The `eliminated` rows (due2-workflows.md §3.5, §6.1, §6.2; decisions/0011 #4) name one removed
% entry, that is, an atom and one policy that states it (due2-workflows.md §6.2, *Entries*), one
% remover, and the rule; an entry removed by two forbids has two rows (due2-workflows.md §3.5
% **[D]**, #57). A permission is removed by its precondition when that duty is owed `t` and
% violated, which closes it in every completion where it applies. Conflict
% follows, among the candidates that are not closed. A remover is in conflict in every
% completion: a forbid with finding `t`, or a permission with finding `t` that no completion
% closes. A removed atom is in conflict in some completion: its finding is `t` or `u`, and a
% permission is not closed. A `u` atom removes nothing (due2-workflows.md §6.2), but it can be
% removed.
%
% The listed frontier is due2-workflows.md §6.3's, from the ready and pending candidates of world
% `k`: an uncertain candidate enters only through the verdict. The `obligations` rows name each
% obligation in force with its duty status, and each whose `in_force` is `u` as `unknown`
% (due2-workflows.md §6.1). The `unknown_part` rows name every `u` part of every finding that is
% not `f`, an atom's or a duty's, with what it reads and why it is `u` (decisions/0016 #3 and its
% amendment).
% Variable letters: DESIGN.md § Vocabulary; in an `elim` row `X` is removed, `P` is the policy of
% its removed entry, and `Y` removes it.
%
% - **Consumes:** `atom/1`, `atom_effect/2`, `atom_policy/2`, `atom_party/3`,
%   `pre/2`, `obligation/1` (structure.lp); `conflict/2`, `left/2`, `prop/2` (bind.lp);
%   `holds/2` (applies.lp); `conn/2`, `member/2`, `leaf/1` (constraint.lp); `read_ok/2`,
%   `read_status/3`, `unchecked_unit/1` (operand.lp); `crank/3`, `evaluates/2` (compare.lp); `rank/2` (kleene.lp);
%   `voc/2` (lift.lp);
%   `witness_cond/2`, `obligation_policy/2`, `instance/1`, `passed/1`, `status/3` (duty.lp);
%   `duty_item/1`, `finding_atom/2`, `item_root/2`, `leaf_status/2` (completion.lp).
% - **Provides:** `may_apply/1`, `surely_applies/1`, `same_policy/4`, `closed_by/2`,
%   `maybe_closed/1`, `may_candidate/1`, `sure_candidate/1`, `may_contend/1`,
%   `sure_contender/1`, `elim_within/4`, `void/1`, `elim/4`, `open_k/2`,
%   `uncertain/1`, `conflict_removes/2`, `conflict_keeps/1`, `conflicted/1`,
%   `candidate_state/2`, `listed/1`, `listed_out/2`,
%   `listed_apart/2`, `listed_dominated/1`, `listed_front/1`, `front_duty/2`,
%   `obligation_row/2`, `reported/1`, `polar/4`, `flip/2`, `conj/2`, `disj/2`,
%   `xone_pol/4`, `xone_by/3`, `live/4`, `witness_status/3`, `unknown_part/3`.

%## Findings

%*! may_apply(X)

Atom `X` has finding `t` or `u`: some completion may make it apply, so it can be removed.
*%
may_apply(X) :- holds(applies(X), t).
may_apply(X) :- holds(applies(X), u).

%*! surely_applies(X)

Atom `X` has finding `t`: it applies in every completion, so it can remove.
*%
surely_applies(X) :- holds(applies(X), t).

%*! same_policy(X, Y, P, Strat)

Atoms `X` and `Y` both belong to policy `P`, whose conflict strategy is `Strat`.
*%
same_policy(X, Y, P, Strat) :- atom_policy(X, P), atom_policy(Y, P), conflict(P, Strat).

%## Closed by a precondition

%*! closed_by(X, Y)

The permission `X`, with finding `t` or `u`, is removed by its precondition `Y`, which is owed
`t` and violated. In every completion where `X` applies, `Y` closes it (due2-workflows.md §6.1).
*%
closed_by(X, Y) :- may_apply(X), atom_effect(X, permit), pre(X, Y), holds(owed(Y), t),
    status(k, Y, violated).

%*! maybe_closed(X)

Some completion may close the permission `X`: a precondition of it whose deadline has passed
may be owed (`owed` is not `f`) and may be unfulfilled (`fulfilled` is not `t`).
*%
maybe_closed(X) :- atom_effect(X, permit), pre(X, Y), not holds(owed(Y), f), passed(Y),
    not holds(fulfilled(Y), t).

%*! may_candidate(X)

The permission `X` is a candidate in some completion: its finding is `t` or `u`, and no
precondition surely closes it.
*%
may_candidate(X) :- may_apply(X), atom_effect(X, permit), not closed_by(X, _).

%*! sure_candidate(X)

The permission `X` is a candidate in every completion: its finding is `t`, and no completion
closes it.
*%
sure_candidate(X) :- surely_applies(X), atom_effect(X, permit), not maybe_closed(X).

%*! may_contend(X)

Atom `X` takes part in conflict in some completion: a candidate there, or a forbid that applies.
*%
may_contend(X) :- may_candidate(X).
may_contend(X) :- may_apply(X), atom_effect(X, forbid).

%*! sure_contender(X)

Atom `X` takes part in conflict in every completion, so it can remove.
*%
sure_contender(X) :- sure_candidate(X).
sure_contender(X) :- surely_applies(X), atom_effect(X, forbid).

%## Within the policy

% By the policy's conflict strategy (due2-workflows.md §6.2 #1), one row per remover. An atom
% removed by two forbids has two rows (due2-workflows.md §3.5, #57), and each row is a complete
% reason. In a conflict row, whenever `X` applies, `Y` applies too, because `Y` is `t`, and `Y`
% removes it. In a `violated_precondition` row, `Y` is the duty atom, owed `t` and violated, so it
% closes `X` wherever `X` applies. A reader can check each row against the policy alone. A single
% row naming the first remover would hide the others, and which one is "first" would depend on the
% order of the facts. A `u` remover gives no row, because it removes `X` only in some completions,
% and that is not a reason that holds whatever the unknowns are.

%*! elim_within(X, P, Y, Strat)

Atom `Y` removes the entry of atom `X` in policy `P`, under `P`'s strategy `Strat`: under
`prohibit` a `t` forbid removes each candidate, under `perm` a sure candidate removes each
forbid, and under `invalid` every contender of a void policy is removed by each other sure
contender of it.
*%
elim_within(X, P, Y, prohibit) :- may_candidate(X), sure_contender(Y), atom_effect(Y, forbid),
    same_policy(X, Y, P, prohibit).
elim_within(X, P, Y, perm) :- may_contend(X), atom_effect(X, forbid), sure_candidate(Y),
    same_policy(X, Y, P, perm).

%*! void(P)

Policy `P` has strategy `invalid`, a sure candidate, and a `t` forbid, so its contenders are
removed in every completion. Its root obligations stay in force (due2-workflows.md §6.2 #1,
decisions/0029).
*%
void(P) :- conflict(P, invalid), sure_candidate(X), atom_policy(X, P), surely_applies(Y),
    atom_effect(Y, forbid), atom_policy(Y, P).
elim_within(X, P, Y, invalid) :- void(P), may_contend(X), atom_policy(X, P), sure_contender(Y),
    atom_policy(Y, P), X != Y.

%## Across policies

%*! elim(X, P, Y, Strat)

Atom `Y` removes the entry of atom `X` in policy `P` under rule `Strat`: `violated_precondition`,
which removes every entry of `X`, a strategy of `P`, or `"prohibit-overrides"` across policies.
Across policies, each entry of a `t` forbid that its policy `Q` did not remove removes each
candidate entry in every policy other than `Q` (due2-workflows.md §6.2 #2). structure.lp admits
one policy, so no vector reaches the cross-policy rule. It is there because due2-workflows.md
§3.5 records every removal with its rule, cross-policy ones included, and
`test_combination_rows_on_facts` runs it on hand-written facts.
*%
elim(X, P, Y, violated_precondition) :- closed_by(X, Y), atom_policy(X, P).
elim(X, P, Y, Strat) :- elim_within(X, P, Y, Strat).
elim(X, P, Y, "prohibit-overrides") :- may_candidate(X), surely_applies(Y), atom_effect(Y, forbid),
    atom_policy(Y, Q), not elim_within(Y, Q, _, _), atom_policy(X, P), P != Q.

#show elim/4.

%## The listed frontier

% The reply's `frontier` is read in world `k`, so it does not depend on the completion. An uncertain
% candidate is not listed: it reaches the reply only through the verdict, which the completions
% decide. So under a definite `Pending` the listed frontier can differ from the frontier of a
% completion (resolve.lp, *The cautious basis*; decisions/0019). This is the listed frontier that
% version 0.33 of due2-workflows.md gave. Version 0.34 lists the routes that suffice instead
% (decisions/0026), and clingo-i follows it with #103.

%*! open_k(Y, N)

The precondition `Y`, whose instance is not violated, has open value of rank `N` in world `k`:
the Kleene conjunction of `owed` and the negation of `fulfilled`. The open value is that of
due2-workflows.md §6.1. A violated instance closes its candidate or makes it uncertain instead,
so it has no open value.
*%
% The Kleene conjunction is the lesser rank; `2 - Nf` is the rank of the negation of `fulfilled`.
open_k(Y, No) :- pre(_, Y), instance(Y), not status(k, Y, violated), holds(owed(Y), Vo),
    holds(fulfilled(Y), Vf), rank(Vo, No), rank(Vf, Nf), No <= 2 - Nf.
open_k(Y, 2 - Nf) :- pre(_, Y), instance(Y), not status(k, Y, violated), holds(owed(Y), Vo),
    holds(fulfilled(Y), Vf), rank(Vo, No), rank(Vf, Nf), 2 - Nf < No.

%*! uncertain(X)

The candidate `X` is uncertain in world `k`: its finding is `u`, a precondition's open value is
`u`, or a violated precondition's `owed` is `u`. The states are those of due2-workflows.md §6.1.
*%
uncertain(X) :- may_candidate(X), holds(applies(X), u).
uncertain(X) :- may_candidate(X), pre(X, Y), open_k(Y, 1).
uncertain(X) :- may_candidate(X), pre(X, Y), status(k, Y, violated), holds(owed(Y), u).

%*! listed_out(X, Y)

The candidate `X` is not uncertain, and its precondition `Y` has open value `t` in world `k`: `Y`
is in `X`'s outstanding set.
*%
listed_out(X, Y) :- may_candidate(X), not uncertain(X), pre(X, Y), open_k(Y, 2).

%*! candidate_state(X, S)

In world `k`, the candidate `X` has state `S`: `ready`, `pending`, or `uncertain`. The states
are given by the table of due2-workflows.md §6.1. Every candidate has exactly one (the constraint
below).
*%
candidate_state(X, uncertain) :- uncertain(X).
candidate_state(X, pending) :- may_candidate(X), not uncertain(X), listed_out(X, _).
candidate_state(X, ready) :- may_candidate(X), not uncertain(X),
    #count { Y : listed_out(X, Y) } = 0.
:- may_candidate(X), #count { S : candidate_state(X, S) } != 1.

%*! conflict_removes(X, P)

Conflict removes the entry of atom `X` in policy `P` in every completion where it takes part: it
has an `elim` row other than `violated_precondition`.
*%
conflict_removes(X, P) :- elim(X, P, _, Strat), Strat != violated_precondition.

%*! conflict_keeps(X)

Atom `X` has an entry that conflict does not remove.
*%
conflict_keeps(X) :- atom_policy(X, P), not conflict_removes(X, P).

%*! conflicted(X)

Conflict removes every entry of atom `X` in every completion where it takes part. Entries are
those of due2-workflows.md §6.2.
*%
conflicted(X) :- conflict_removes(X, _), not conflict_keeps(X).

%*! listed(X)

The candidate `X` is ready or pending in world `k`, and conflict does not remove it, so it forms
an alternative of the listed frontier. The frontier is that of due2-workflows.md §6.3.
*%
listed(X) :- candidate_state(X, (ready; pending)), not conflicted(X).

%*! listed_apart(X, X2)

The listed candidate `X` has an outstanding duty that the listed candidate `X2` lacks.
*%
listed_apart(X, X2) :- listed(X), listed_out(X, Y), listed(X2), not listed_out(X2, Y).

%*! listed_dominated(X2)

A listed candidate's outstanding set is a strict subset of the listed candidate `X2`'s.
*%
listed_dominated(X2) :- listed(X), listed(X2), not listed_apart(X, X2), listed_apart(X2, X).

%*! listed_front(X)

The listed candidate `X` is in the listed frontier: no other's outstanding set is a strict subset
of its own. interpret.py reports it under a `Pending` verdict, collapsing candidates with one set
of duty IRIs into one alternative.
*%
listed_front(X) :- listed(X), not listed_dominated(X).

%*! front_duty(X, Y)

The duty atom `Y` is outstanding for the candidate `X` of the listed frontier.
*%
front_duty(X, Y) :- listed_front(X), listed_out(X, Y).

#show listed_front/1.
#show front_duty/2.

%## Obligations

%*! obligation_row(Y, S)

The obligation `Y` is reported with status `S`: its duty status when it is in force `t`, and
`unknown` when its `in_force` is `u`, whatever its status. One not in force is not reported
(due2-workflows.md §6.1). interpret.py also names each in role `obligation`, under any verdict.
*%
obligation_row(Y, S) :- obligation(Y), holds(in_force(Y), t), status(k, Y, S).
obligation_row(Y, unknown) :- obligation(Y), holds(in_force(Y), u).

#show obligation_row/2.

%## Unknown parts

% W1's atoms are the disjuncts of the DNF of each authored tree (due2-workflows.md §3.1, §4 stage
% 2), so a `u` leaf that lies only in `f` disjuncts is read only by `f` atoms, and is not reported:
% in `or(and(lf, y), z)`, with `lf` a leaf that is `f`, `y` is not. A leaf that lies in a disjunct
% that is not `f` is live, and is reported though another member decides its node, in a `t` atom as
% in a `u` one: in `or(lt, y)`, with `lt` a leaf that is `t`, `y` is. The reply then names
% everything that was unknown in the disjuncts that can hold, whether or not it mattered, and a
% renderer may show less. `live/4` finds the live leaves on the authored tree, without building the
% DNF, which can be exponentially larger.
%
% Under a status the same for every rule, as an absent target is, every atom carries the row, so
% interpret.py projects the rows to the rule or duty node, and the reply has one row per rule,
% input, and status.

%*! reported(I)

Finding `I` is `t` or `u`, so its `u` parts are reported. An `f` finding is not: none of its `u`
parts can change it, and due2-workflows.md §5.5 lets an index skip an `f` atom, so reporting it
would make the reply depend on the index (decisions/0016, amendment).
*%
% Every finding has exactly one value (kleene.lp), so `not ... f` is "`t` or `u`".
reported(applies(X)) :- atom(X), not holds(applies(X), f).
reported(I) :- duty_item(I), not holds(I, f).

%*! polar(W, C, P, N)

In world `W`, node `C` read with polarity `P` has rank `N`: its own rank for `pos`, and its
negation's for `neg`.
*%
polar(W, C, pos, N) :- crank(W, C, N).
polar(W, C, neg, 2 - N) :- crank(W, C, N).

%*! flip(P, Q)

Polarity `Q` is the opposite of `P`. A negation reads its member with the opposite polarity.
*%
flip(pos, neg).
flip(neg, pos).

%*! conj(K, P)

A node with connective `K`, read with polarity `P`, is a conjunction of its members, each read
with `P`: an `and` read positively, or an `or` read negatively (De Morgan).
*%
conj(and, pos).
conj(or, neg).

%*! disj(K, P)

A node with connective `K`, read with polarity `P`, is a disjunction of its members, each read
with `P`: an `or` read positively, or an `and` read negatively.
*%
disj(or, pos).
disj(and, neg).

%*! xone_pol(C, D, G, Q)

In the term of the `xone` node `C` for its member `D`, member `G` is read with polarity `Q`:
`pos` for `D` itself and `neg` for each other member. W1 expands an `xone` into one such
conjunction per member (due2-workflows.md §6.4 and §4, its stage 2).
*%
xone_pol(C, D, D, pos) :- conn(C, xone), member(C, D).
xone_pol(C, D, G, neg) :- conn(C, xone), member(C, D), member(C, G), G != D.

%*! xone_by(W, C, D)

In world `W`, the `xone` node `C` is `t` because of its member `D`: `D` is the one member that
is `t`. Then the term of `xone_pol/4` for `D` is `t`, and every other term is `f`.
*%
xone_by(W, C, D) :- crank(W, C, 2), conn(C, xone), member(C, D), crank(W, D, 2).

%*! live(W, I, C, P)

Node `C`, read with polarity `P`, lies in a disjunct of finding `I`'s DNF whose value, in world
`W`, is not `f`. W1 makes that DNF, and each disjunct is an atom (due2-workflows.md §3.1, §4
stage 2), so a `u` leaf is named exactly when it is live (due2-workflows.md §3.5). The
disjunct may be a contradiction, such as `a and not a`: W1's rewrites are strong Kleene
equivalences, which do not drop it.

The roots are the trees of a reported finding in world `k`, and the witness conditions of a
witness pair that is not `f`, in its world `wit(E)`. Each is a conjunct of its finding with every
other part, so it is live. Liveness passes from a node to its members as follows:

- A disjunction passes it to every member.
- A conjunction passes it to a member when no other member is `f` under its polarity
  (`polar/4` rank 0). Under strong Kleene logic a node's value is the greatest of its
  disjuncts' values, so each such sibling has a disjunct that is not `f`, and the member's
  disjuncts combine with those into disjuncts that are not `f` either. When a sibling is `f`,
  every disjunct through the conjunction is `f`.
- A negation passes it to its member, read with the opposite polarity.
- An `xone` read positively is the disjunction of its terms (`xone_pol/4`). A term passes
  liveness to a member when no other member of the term is `f` under its polarity there.
- An `xone` read negatively is the conjunction of its negated terms, because due2-profiles.md §5
  expands an `xone` before pushing a negation in. A negated term is the disjunction of its
  members, each read with the opposite polarity, and it is `f` exactly when its term is `t`:
  when the `xone` is `t` because of that term's member (`xone_by/3`). It passes liveness to its
  members when no other negated term is `f`.
*%
live(k, I, C, pos) :- reported(I), item_root(I, C).
live(wit(E), witness(Y, E), C, pos) :- witness_cond(Y, C), holds(witness(Y, E), V), V != f.
live(W, I, D, P) :- live(W, I, C, P), conn(C, K), disj(K, P), member(C, D).
live(W, I, D, P) :- live(W, I, C, P), conn(C, K), conj(K, P), member(C, D),
    not polar(W, D2, P, 0) : member(C, D2), D2 != D.
live(W, I, D, Q) :- live(W, I, C, P), conn(C, negation), member(C, D), flip(P, Q).
live(W, I, G, Q) :- live(W, I, C, pos), conn(C, xone), xone_pol(C, D, G, Q),
    not polar(W, H, R, 0) : xone_pol(C, D, H, R), H != G.
live(W, I, G, Q) :- live(W, I, C, neg), conn(C, xone), xone_pol(C, D, G, R), flip(R, Q),
    not xone_by(W, C, D2) : member(C, D2), D2 != D.

%*! witness_status(E, C, S)

The witness leaf `C` is `u` in world `wit(E)` with status `S`, as `leaf_status/2` gives it for
world `k`: its operand's read status there, or `misfit`.
*%
witness_status(E, C, S) :- evaluates(wit(E), C), leaf(C), left(C, Op),
    read_status(wit(E), Op, S), not unchecked_unit(C).
witness_status(E, C, misfit) :- evaluates(wit(E), C), unchecked_unit(C).
witness_status(E, C, misfit) :- evaluates(wit(E), C), leaf(C), left(C, Op), read_ok(wit(E), Op),
    crank(wit(E), C, 1).

%*! unknown_part(X, Input, S)

Atom or duty atom `X` has a `u` part, in a finding that is `t` or `u`, that reads `Input` with
status `S`. The relation is the `unknown_part` of due2-workflows.md §3.5 and decisions/0016 #3.
`Input` is `target` for the request's target, `party(F)` for its party under function `F`, and
`prop(Prop)` for a `u` leaf whose left operand reads the property `Prop`. An absent target or
party is `missing`, and a leaf has its status. A `u` leaf is named when it is live
(`live/4`), whether or not it decides its node: the reply names what was missing even where it
did not matter, but not a leaf that only an `f` atom reads. The parts of a duty's findings are
its guards for `owed` and `in_force`; the match parts of its policy's rules for `in_force`,
under the obligation; and for `fulfilled`, the witness conditions and a `u` actor check, which
reads the request's assignee (duty.lp), of each witness pair that is not `f`.
*%
unknown_part(X, target, missing) :- reported(applies(X)), holds(part(X, target), u).
unknown_part(X, party(F), missing) :- reported(applies(X)), atom_party(X, F, _),
    holds(part(X, party(F)), u).
unknown_part(Y, target, missing) :- reported(in_force(Y)), obligation_policy(Y, P),
    atom_policy(X, P), holds(part(X, target), u).
unknown_part(Y, party(F), missing) :- reported(in_force(Y)), obligation_policy(Y, P),
    atom_policy(X, P), atom_party(X, F, _), holds(part(X, party(F)), u).
unknown_part(X, prop(Prop), S) :- live(k, I, C, _), finding_atom(I, X), leaf_status(C, S),
    left(C, Op), prop(Op, Prop).
unknown_part(Y, prop(Prop), S) :- live(wit(E), witness(Y, E), C, _), witness_status(E, C, S),
    left(C, Op), prop(Op, Prop).
unknown_part(Y, party(F), missing) :- holds(check(Y, E, actor), u), holds(witness(Y, E), V),
    V != f, voc(assignee, F).

#show unknown_part/3.
