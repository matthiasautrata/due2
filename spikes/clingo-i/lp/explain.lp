% explain.lp: eliminations over the findings (workflows §3.5, §6.2; decisions/0011 #4).
% A remover has finding t; a removed atom has t or u: U atoms eliminate nothing, but can be removed.
% No world: the rows do not depend on the completion.

% Each atom has one effect, one policy, and one source rule (formalisation review §3 #2).
:- atom(X), #count { E : atom_effect(X, E) } != 1.
:- atom(X), #count { P : atom_policy(X, P) } != 1.
:- atom(X), #count { R : atom_rule(X, R) } != 1.

live(X) :- holds(applies(X), t).
live(X) :- holds(applies(X), u).
sure(X) :- holds(applies(X), t).
same_policy(X, Y, C) :- atom_policy(X, P), atom_policy(Y, P), conflict(P, C).

% Within the policy (§6.2.1), one row per remover (§3.5).
inner(X, Y, prohibit) :- live(X), atom_effect(X, permit), sure(Y), atom_effect(Y, forbid),
    same_policy(X, Y, prohibit).
inner(X, Y, perm) :- live(X), atom_effect(X, forbid), sure(Y), atom_effect(Y, permit),
    same_policy(X, Y, perm).
void(P) :- conflict(P, invalid), sure(X), atom_effect(X, permit), atom_policy(X, P),
    sure(Y), atom_effect(Y, forbid), atom_policy(Y, P).
inner(X, Y, invalid) :- void(P), live(X), atom_policy(X, P), sure(Y), atom_policy(Y, P), X != Y.

% Across policies (§6.2.2), prohibit-overrides: each t forbid its own policy did not remove
% removes each candidate of every other policy. One policy only, for now (structure.lp).
removed(Y) :- inner(Y, _, _).
elim(X, Y, R) :- inner(X, Y, R).
elim(X, Y, "prohibit-overrides") :- live(X), atom_effect(X, permit), sure(Y),
    atom_effect(Y, forbid), not removed(Y), atom_policy(X, P), atom_policy(Y, Q), P != Q.

#show elim/3.
