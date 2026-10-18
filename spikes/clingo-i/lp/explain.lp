%# explain.lp: the eliminations, the listed frontier, the obligations, and the unknown parts
%
% The reply's `eliminated`, `frontier`, `obligations`, and `unknown_parts`, all read from the
% findings before completion, in the Kleene world `k`, not from a completion world, so they do
% not depend on the completion.
%
% The `eliminated` rows (due2-workflows.md §3.5, §6.1, §6.2; decisions/0011 #4) name one removed
% atom, one remover, and the rule; an atom removed by two forbids has two rows
% (due2-workflows.md §3.5 **[D]**, #57). A permission is removed by its precondition when that
% duty is owed `t` and violated, which closes it in every completion where it applies. Conflict
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
% Variable letters: DESIGN.md § Vocabulary; in an `elim` row `X` is removed and `Y` removes it.
%
% - **Consumes:** `atom/1`, `atom_effect/2`, `atom_policy/2`, `atom_rule/2`, `atom_party/3`,
%   `conflict/2`, `pre/2`, `obligation/1` (structure.lp); `holds/2` (applies.lp); `member/2`,
%   `leaf/1`, `left/2` (constraint.lp); `prop/2`, `read_ok/2`, `read_status/3` (operand.lp);
%   `crank/3`, `evaluates/2` (compare.lp); `rank/2` (kleene.lp); `voc/2` (lift.lp);
%   `witness_cond/2`, `obligation_policy/2`, `instance/1`, `passed/1`, `status/3` (duty.lp);
%   `duty_item/1`, `finding_atom/2`, `item_root/2`, `leaf_status/2` (completion.lp).
% - **Provides:** `may_apply/1`, `surely_applies/1`, `same_policy/3`, `closed_by/2`,
%   `surely_closed/1`, `maybe_closed/1`, `may_candidate/1`, `sure_candidate/1`, `may_contend/1`,
%   `sure_contender/1`, `elim_within/3`, `void/1`, `removed_within/1`, `elim/3`, `open_k/2`,
%   `uncertain/1`, `conflicted/1`, `candidate_state/2`, `listed/1`, `listed_out/2`,
%   `listed_apart/2`, `listed_dominated/1`, `listed_front/1`, `front_duty/2`,
%   `obligation_row/2`, `reported/1`, `in_tree/2`, `witness_status/2`, `unknown_part/3`.

%## Integrity

% Each atom has one effect, one policy, and one source rule, so that a row names exactly one
% of each (formalisation-review.md §3 #2).
:- atom(X), #count { Eff : atom_effect(X, Eff) } != 1.
:- atom(X), #count { P : atom_policy(X, P) } != 1.
:- atom(X), #count { R : atom_rule(X, R) } != 1.

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

%*! same_policy(X, Y, Strat)

Atoms `X` and `Y` belong to the same policy, whose conflict strategy is `Strat`.
*%
same_policy(X, Y, Strat) :- atom_policy(X, P), atom_policy(Y, P), conflict(P, Strat).

%## Closed by a precondition

%*! closed_by(X, Y)

The permission `X`, with finding `t` or `u`, is removed by its precondition `Y`, which is owed
`t` and violated. In every completion where `X` applies, `Y` closes it (due2-workflows.md §6.1).
*%
closed_by(X, Y) :- may_apply(X), atom_effect(X, permit), pre(X, Y), holds(owed(Y), t),
    status(k, Y, violated).

%*! surely_closed(X)

Some precondition closes the permission `X` in every completion where it applies.
*%
surely_closed(X) :- closed_by(X, _).

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
may_candidate(X) :- may_apply(X), atom_effect(X, permit), not surely_closed(X).

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

% By the policy's conflict strategy (due2-workflows.md §6.2 #1), one row per remover.

%*! elim_within(X, Y, Strat)

Atom `Y` removes atom `X` within their policy, under its strategy `Strat`: under `prohibit` a `t`
forbid removes each candidate, under `perm` a sure candidate removes each forbid, and under
`invalid` every contender of a void policy is removed by each other sure contender of it.
*%
elim_within(X, Y, prohibit) :- may_candidate(X), sure_contender(Y), atom_effect(Y, forbid),
    same_policy(X, Y, prohibit).
elim_within(X, Y, perm) :- may_contend(X), atom_effect(X, forbid), sure_candidate(Y),
    same_policy(X, Y, perm).

%*! void(P)

Policy `P` has strategy `invalid`, a sure candidate, and a `t` forbid, so it contributes nothing
in any completion. See due2-workflows.md §6.2 #1.
*%
void(P) :- conflict(P, invalid), sure_candidate(X), atom_policy(X, P), surely_applies(Y),
    atom_effect(Y, forbid), atom_policy(Y, P).
elim_within(X, Y, invalid) :- void(P), may_contend(X), atom_policy(X, P), sure_contender(Y),
    atom_policy(Y, P), X != Y.

%## Across policies

%*! removed_within(Y)

Atom `Y` is removed within its own policy, so it removes nothing across policies.
*%
removed_within(Y) :- elim_within(Y, _, _).

%*! elim(X, Y, Strat)

Atom `Y` removes atom `X` under rule `Strat`: `violated_precondition`, a strategy of their
policy, or `"prohibit-overrides"` across policies. Across policies, each `t` forbid its own policy
did not remove removes each candidate of every other policy (due2-workflows.md §6.2 #2).
structure.lp admits one policy, so no vector reaches the cross-policy rule. It is there because
due2-workflows.md §3.5 records cross-policy rows (formalisation-review.md §3 #3), and
`test_combination_rows_on_facts` runs it on hand-written facts.
*%
elim(X, Y, violated_precondition) :- closed_by(X, Y).
elim(X, Y, Strat) :- elim_within(X, Y, Strat).
elim(X, Y, "prohibit-overrides") :- may_candidate(X), surely_applies(Y), atom_effect(Y, forbid),
    not removed_within(Y), atom_policy(X, P), atom_policy(Y, Q), P != Q.

#show elim/3.

%## The listed frontier

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

%*! conflicted(X)

Conflict removes atom `X` in every completion where it takes part: it has an `elim` row other
than `violated_precondition`.
*%
conflicted(X) :- elim(X, _, Strat), Strat != violated_precondition.

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

%*! reported(I)

Finding `I` is `t` or `u`, so its `u` parts are reported. An `f` finding is not: none of its `u`
parts can change it, and due2-workflows.md §5.5 lets an index skip an `f` atom, so reporting it
would make the reply depend on the index (decisions/0016, amendment).
*%
% Every finding has exactly one value (kleene.lp), so `not ... f` is "`t` or `u`".
reported(applies(X)) :- atom(X), not holds(applies(X), f).
reported(I) :- duty_item(I), not holds(I, f).

%*! in_tree(I, C)

Constraint node `C` is in a tree of finding `I`: one of its roots, or a member of a node in one.
The roots of `fulfilled(Y)` are the witness conditions of `Y`.
*%
in_tree(I, C) :- item_root(I, C).
in_tree(fulfilled(Y), C) :- duty_item(fulfilled(Y)), witness_cond(Y, C).
in_tree(I, D) :- in_tree(I, C), member(C, D).

%*! witness_status(C, S)

The witness leaf `C` is `u` in some world `wit(E)` with status `S`, as `leaf_status/2` gives it
for world `k`: its operand's read status there, or `misfit`.
*%
witness_status(C, S) :- evaluates(wit(E), C), leaf(C), left(C, Op), read_status(wit(E), Op, S).
witness_status(C, misfit) :- evaluates(wit(E), C), leaf(C), left(C, Op), read_ok(wit(E), Op),
    crank(wit(E), C, 1).

%*! unknown_part(X, Input, S)

Atom or duty atom `X` has a `u` part, in a finding that is `t` or `u`, that reads `Input` with
status `S`. The relation is the `unknown_part` of due2-workflows.md §3.5 and decisions/0016 #3.
`Input` is `target` for the request's target, `party(F)` for its party under function `F`, and
`prop(Prop)` for a `u` leaf whose left operand reads the property `Prop`. An absent target or
party is `missing`, and a leaf has its status. Every `u` leaf of a reported finding's trees is
named, whether or not it decides its node: the reply names what was missing even where it did
not matter. The parts of a duty's findings are its guards for `owed` and `in_force`; the match
parts of its policy's rules for `in_force`, under the obligation; and for `fulfilled`, its
witness conditions in each evidence's world and a `u` actor check, which reads the request's
assignee (duty.lp).
*%
unknown_part(X, target, missing) :- reported(applies(X)), holds(part(X, target), u).
unknown_part(X, party(F), missing) :- reported(applies(X)), atom_party(X, F, _),
    holds(part(X, party(F)), u).
unknown_part(Y, target, missing) :- reported(in_force(Y)), obligation_policy(Y, P),
    atom_policy(X, P), holds(part(X, target), u).
unknown_part(Y, party(F), missing) :- reported(in_force(Y)), obligation_policy(Y, P),
    atom_policy(X, P), atom_party(X, F, _), holds(part(X, party(F)), u).
unknown_part(X, prop(Prop), S) :- reported(I), finding_atom(I, X), in_tree(I, C),
    leaf_status(C, S), left(C, Op), prop(Op, Prop).
unknown_part(Y, prop(Prop), S) :- reported(fulfilled(Y)), in_tree(fulfilled(Y), C),
    witness_status(C, S), left(C, Op), prop(Op, Prop).
unknown_part(Y, party(F), missing) :- reported(fulfilled(Y)), holds(check(Y, _, actor), u),
    voc(assignee, F).

#show unknown_part/3.
