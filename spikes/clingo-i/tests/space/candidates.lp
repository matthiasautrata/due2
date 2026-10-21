%# candidates.lp: which rules a request matches, and conflict
%
% Each answer set is one input to the rule differential: one to `rules` unconstrained rules and
% a request. A rule is a permission or a prohibition, for `use` or `play` (`play` is narrower,
% conftest.INIT), on target `a` or `b`, with no assignee or with alice or bob. The request is
% for `use` or `play`, on target `a` or with no target, and names alice or no assignee. An
% absent target or assignee leaves a rule's match `u`, so this space reaches the candidate set,
% conflict, and pivotal atoms.
%
% Leaving `b` and bob out of the request drops no input: renaming the targets, or the parties,
% maps a request for `b` or bob onto one for `a` or alice.
%
% - **Constants:** `rules`, the most rules; `actions`, 1 for `use` only, 2 for `use` and `play`.
% - **Shows:** `slot/2`, `request/3`, `conflict/1`.

#const rules = 1.
#const actions = 2.

kind(permission; prohibition).
action(use).
action(play) :- actions = 2.
target(a; b).
party(none; alice; bob).
rterm(r(K, A, T, P)) :- kind(K), action(A), target(T), party(P).

% The rules are a multiset (rules.lp).
{ n(1..rules) } = 1.
{ slot(I, R) : rterm(R) } = 1 :- n(N), I = 1..N.
:- slot(I, R), slot(I + 1, R2), R > R2.

{ request(A, T, P) : action(A), T = (a; none), P = (alice; none) } = 1.

% The strategy is fixed with one kind of rule (rules.lp).
strategy(prohibit; perm; invalid).
{ conflict(C) : strategy(C) } = 1.
both :- slot(_, r(permission, _, _, _)), slot(_, r(prohibition, _, _, _)).
:- not both, not conflict(perm).

#show slot/2.
#show request/3.
#show conflict/1.
