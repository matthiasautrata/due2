% pivot.lp: solve 3 only. A completion c, one literal flipped, and the world flip (decisions/0011).
% Brave enumeration: the union over models is the pivotal literals and their unknown atoms.

world(flip).
{ pivot(L) : var(L) } = 1.
lval(flip, L, V) :- lval(c, L, V), not pivot(L).
lval(flip, L, t) :- pivot(L), lval(c, L, f).
lval(flip, L, f) :- pivot(L), lval(c, L, t).

% Only a flip that changes the verdict.
:- verdict(c, V), verdict(flip, V).

unknown(X) :- holds(applies(X), u), part_item(X, I), lit_of(I, L), pivot(L).

#show unknown/1.
