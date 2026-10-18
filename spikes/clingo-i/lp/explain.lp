%# explain.lp: the eliminations and the unknown parts, read from the findings
%
% The reply's `eliminated` and `unknown_parts` rows. The `eliminated` rows
% (due2-workflows.md §3.5, §6.2; decisions/0011 #4) are read from the findings before completion,
% not from a world, so they do not depend on the completion. A remover has finding `t`. A removed
% atom has finding `t` or `u`: a `u` atom removes nothing (due2-workflows.md §6.2), but it can be
% removed. Each row names one removed atom, one remover, and the strategy; an atom removed by two
% forbids has two rows (due2-workflows.md §3.5 **[D]**, #57). Variable letters:
% DESIGN.md § Vocabulary; in an `elim` row `X` is removed and `Y` removes it. The `unknown_part`
% rows name every `u` part of every atom whose finding is not `f`, with what it reads and why it is
% `u` (decisions/0016 #3 and its amendment).
%
% - **Consumes:** `atom/1`, `atom_effect/2`, `atom_policy/2`, `atom_rule/2`, `atom_party/3`,
%   `conflict/2` (structure.lp); `holds/2`, `atom_constraint/2` (applies.lp); `member/2`,
%   `left/2` (constraint.lp); `prop/2` (operand.lp); `leaf_status/2` (completion.lp).
% - **Provides:** `may_apply/1`, `surely_applies/1`, `same_policy/3`, `elim_within/3`, `void/1`,
%   `removed_within/1`, `elim/3`, `in_tree/2`, `unknown_part/3`.

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

%## Within the policy

% By the policy's conflict strategy (due2-workflows.md §6.2 #1), one row per remover.

%*! elim_within(X, Y, Strat)

Atom `Y` removes atom `X` within their policy, under its strategy `Strat`: under `prohibit` a `t`
forbid removes each permission, under `perm` a `t` permission removes each forbid, and under
`invalid` every atom of a void policy is removed by each other `t` atom of it.
*%
elim_within(X, Y, prohibit) :- may_apply(X), atom_effect(X, permit), surely_applies(Y),
    atom_effect(Y, forbid), same_policy(X, Y, prohibit).
elim_within(X, Y, perm) :- may_apply(X), atom_effect(X, forbid), surely_applies(Y),
    atom_effect(Y, permit), same_policy(X, Y, perm).

%*! void(P)

Policy `P` has strategy `invalid` and both a `t` permission and a `t` forbid, so it contributes
nothing. See due2-workflows.md §6.2 #1.
*%
void(P) :- conflict(P, invalid), surely_applies(X), atom_effect(X, permit), atom_policy(X, P),
    surely_applies(Y), atom_effect(Y, forbid), atom_policy(Y, P).
elim_within(X, Y, invalid) :- void(P), may_apply(X), atom_policy(X, P), surely_applies(Y),
    atom_policy(Y, P), X != Y.

%## Across policies

%*! removed_within(Y)

Atom `Y` is removed within its own policy, so it removes nothing across policies.
*%
removed_within(Y) :- elim_within(Y, _, _).

%*! elim(X, Y, Strat)

Atom `Y` removes atom `X` under strategy `Strat`: a strategy of their policy, or
`"prohibit-overrides"` across policies. Across policies, each `t` forbid its own policy did not
remove removes each permission of every other policy (due2-workflows.md §6.2 #2). structure.lp
admits one policy, so no vector reaches the cross-policy rule. It is there because
due2-workflows.md §3.5 records cross-policy rows (formalisation-review.md §3 #3), and
`test_combination_rows_on_facts` runs it on hand-written facts.
*%
elim(X, Y, Strat) :- elim_within(X, Y, Strat).
elim(X, Y, "prohibit-overrides") :- may_apply(X), atom_effect(X, permit), surely_applies(Y),
    atom_effect(Y, forbid), not removed_within(Y), atom_policy(X, P), atom_policy(Y, Q), P != Q.

#show elim/3.

%## Unknown parts

%*! in_tree(X, C)

Constraint node `C` is in a tree of atom `X`: one of its roots, or a member of a node in one.
*%
in_tree(X, C) :- atom_constraint(X, C).
in_tree(X, D) :- in_tree(X, C), member(C, D).

%*! unknown_part(X, Input, S)

Atom `X` has a `u` part that reads `Input` with status `S`. The relation is the
`unknown_part` of due2-workflows.md §3.5 and decisions/0016 #3. `Input` is `target` for the
request's target, `party(F)` for its party under function `F`, and `prop(Prop)` for a `u` leaf
whose left operand reads the property `Prop`. An absent target or party is `missing`, and a
leaf has its `leaf_status/2`. Every atom whose finding is `t` or `u` is reported, with every `u`
leaf of its trees, whether or not it decides its node: the reply names what was missing even
where it did not matter. An `f` atom is not reported. None of its `u` parts can change it, and
due2-workflows.md §5.5 lets an index skip it, so reporting it would make the reply depend on the
index (decisions/0016, amendment).
*%
% `holds(applies(X), V)` has exactly one `V` (kleene.lp), so `not ... f` is "`t` or `u`".
unknown_part(X, target, missing) :- atom(X), holds(part(X, target), u),
    not holds(applies(X), f).
unknown_part(X, party(F), missing) :- atom_party(X, F, _), holds(part(X, party(F)), u),
    not holds(applies(X), f).
unknown_part(X, prop(Prop), S) :- in_tree(X, C), leaf_status(C, S), left(C, Op), prop(Op, Prop),
    not holds(applies(X), f).

#show unknown_part/3.
