%# duties.lp: permissions with duties, and a root obligation
%
% Each answer set is one input to the duty differential (`Duties` in test_brute_force.py): one to
% `rules` rules, each with at most one leaf constraint; up to `duties` duties, each with at most
% one leaf guard, an evidence row by one actor or none, and a deadline that has passed or none;
% the edges by which permissions require duties; with `obligations` 1, a root obligation; the
% subject of the request; the operand statuses (rules.lp); and the conflict strategy. Every rule is for `use` on target `a` with no assignee.
%
% Duty `d(G, A, P)` has guard `G` (a leaf or `none`), evidence by actor `A` (`none` for no
% evidence row), and `P` 1 when its deadline has passed. The duties are sorted, so each multiset
% of duties is one input: the duty actions are interchangeable. Every duty is required by at
% least one permission, since a duty nothing requires decides nothing.
%
% - **Constants:** `rules`, the most rules; `duties`, the most duties, at most 3 (DUTY_ACTIONS);
%   `operands`, the operands the leaves read; `guards`, 1 to let duties be guarded;
%   `prohibitions`, 1 to allow prohibitions; `obligations`, 1 for a root obligation; `subjects`,
%   2 for the subject alice or none, 1 for alice only; `actors`, 1 to 3 for the evidence actors
%   none, alice, and bob.
% - **Shows:** `slot/2`, `operand/2`, `conflict/1`, `subject/1`, `dterm/2`, `edge/2`,
%   `obligation/1`.

#const rules = 1.
#const duties = 1.
#const operands = 0.
#const operators = 2.
#const size = 1.
#const guards = 0.
#const prohibitions = 0.
#const obligations = 0.
#const subjects = 1.
#const actors = 3.
#include "trees.lp".

cons(none).
cons(T) :- tree(T, _).
guard(none).
guard(T) :- tree(T, _), guards = 1.
kind(permission).
kind(prohibition) :- prohibitions = 1.
rterm(r(K, C)) :- kind(K), cons(C).

% The rules are a multiset (rules.lp).
{ n(1..rules) } = 1.
{ slot(I, R) : rterm(R) } = 1 :- n(N), I = 1..N.
:- slot(I, R), slot(I + 1, R2), R > R2.

% The statuses are sorted by operand (rules.lp).
status(value; missing; resolved; unresolved).
{ operand(O, S) : status(S) } = 1 :- O = 0..operands - 1.
:- operand(O, S), operand(O + 1, S2), S > S2.

% The strategy is fixed with one kind of rule (rules.lp).
strategy(prohibit; perm; invalid).
{ conflict(C) : strategy(C) } = 1.
both :- slot(_, r(permission, _)), slot(_, r(prohibition, _)).
:- not both, not conflict(perm).

party(alice).
party(none) :- subjects = 2.
{ subject(P) : party(P) } = 1.

actor(none).
actor(alice) :- actors >= 2.
actor(bob) :- actors = 3.
dterm(d(G, A, P)) :- guard(G), actor(A), P = 0..1.

{ k(0..duties) } = 1.
duty(D) :- k(N), D = 0..N - 1.
{ dterm(D, X) : dterm(X) } = 1 :- duty(D).
:- dterm(D, X), dterm(D + 1, Y), X > Y.
{ edge(I, D) } :- slot(I, r(permission, _)), duty(D).
:- duty(D), not edge(_, D).

{ obligation(X) : dterm(X) } = 1 :- obligations = 1.

#show slot/2.
#show operand/2.
#show conflict/1.
#show subject/1.
#show dterm/2.
#show edge/2.
#show obligation/1.
