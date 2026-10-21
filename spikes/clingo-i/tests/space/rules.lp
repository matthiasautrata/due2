%# rules.lp: policies of constrained rules, under every operand status
%
% Each answer set is one input to the rule differential: one to `rules` rules, each a
% permission or a prohibition with at most one constraint tree; the status of each operand; and
% the conflict strategy. Every rule, and the request, is for `use` on target `a` with no
% assignee, so only the constraints decide which rules apply (`tests/spaces.py` maps the answer
% set to a `Case`).
%
% An operand's status says how the request and the state give it:
%
% - `value`: the request gives the value 1;
% - `resolved`: the state gives the value 1;
% - `missing`: the request gives nothing, so the operand is opaque;
% - `unresolved`: the state has no fact, so two leaves with one key read one variable.
%
% - **Constants:** `rules`, the most rules; `pinned`, 1 to pin operand 0 at `value` and operand 1
%   at `unresolved`, 0 to vary every status; and those of trees.lp.
% - **Shows:** `slot/2`, `operand/2`, `conflict/1`.

#include "trees.lp".
#const rules = 1.
#const pinned = 0.
#const operands = 2.
#const operators = 4.
#const size = 1.

cons(none).
cons(T) :- tree(T, _).
kind(permission; prohibition).
rterm(r(K, C)) :- kind(K), cons(C).

% The rules are a multiset: the slots are sorted, so renaming the rules gives no new input.
{ n(1..rules) } = 1.
{ slot(I, R) : rterm(R) } = 1 :- n(N), I = 1..N.
:- slot(I, R), slot(I + 1, R2), R > R2.

% The statuses are sorted by operand: renaming the operands gives no new input, since the trees
% range over every operand.
status(value; missing; resolved; unresolved).
{ operand(O, S) : status(S) } = 1 :- O = 0..operands - 1, pinned = 0.
:- operand(O, S), operand(O + 1, S2), S > S2, pinned = 0.
operand(0, value) :- pinned = 1.
operand(1, unresolved) :- pinned = 1.

% The strategy decides only between a permission and a prohibition, so with one kind of rule it
% is fixed.
strategy(prohibit; perm; invalid).
{ conflict(C) : strategy(C) } = 1.
both :- slot(_, r(permission, _)), slot(_, r(prohibition, _)).
:- not both, not conflict(perm).

#show slot/2.
#show operand/2.
#show conflict/1.
