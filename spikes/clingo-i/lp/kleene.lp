% kleene.lp: truth values and the integrity constraints (workflows §5.1).
% Kleene conjunction is #min over the ranks f < u < t.

rank(f, 0).
rank(u, 1).
rank(t, 2).
two_valued(f; t).

% Every item has exactly one value, and only a ranked one.
:- item(I), #count { V : holds(I, V) } != 1.
:- holds(_, V), not rank(V, _).

% Every u part reads exactly one literal (completion.lp).
:- part_item(_, I), holds(I, u), #count { L : lit_of(I, L) } != 1.

% In every world, every literal and every item has exactly one value, f or t.
:- world(W), var(L), #count { V : lval(W, L, V) } != 1.
:- world(W), item(I), #count { V : cval(W, I, V) } != 1.
:- cval(_, _, V), not two_valued(V).

% Every world has exactly one verdict.
:- world(W), #count { V : verdict(W, V) } != 1.
