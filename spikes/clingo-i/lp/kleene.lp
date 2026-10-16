% kleene.lp: truth values and the integrity constraints (workflows §5.1).
% Kleene conjunction is #min over the ranks f < u < t.

rank(f, 0).
rank(u, 1).
rank(t, 2).
two_valued(f; t).

% Every item has exactly one value, and only a ranked one.
:- item(I), #count { V : holds(I, V) } != 1.
:- holds(_, V), not rank(V, _).

% Every completed item has exactly one value, f or t.
:- item(I), #count { V : cval(I, V) } != 1.
:- cval(_, V), not two_valued(V).

% Every completion has exactly one verdict.
:- #count { V : verdict(V) } != 1.
