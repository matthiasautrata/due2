% completion.lp: the literals of the unknown parts, and one completion of them (workflows §6.4).
% A u part reads a literal; parts with the same key are one variable (decisions/0011 #2).
% Constraint keys land with constraints (#47).

lit_of(part(X, target), target(T)) :- atom_target(X, T), holds(part(X, target), u).
lit_of(part(X, party(F)), party(F, P)) :- atom_party(X, F, P), holds(part(X, party(F)), u).
var(L) :- lit_of(_, L).

% World c is the completion; solve 3 adds its flip (pivot.lp).
world(c).
{ lval(c, L, t); lval(c, L, f) } = 1 :- var(L).

cval(W, I, V) :- world(W), lit_of(I, L), lval(W, L, V).
cval(W, I, V) :- world(W), part_item(_, I), holds(I, V), V != u.
cval(W, applies(X), V) :- world(W), atom(X), rank(V, N),
    N = #min { R : part_item(X, I), cval(W, I, Z), rank(Z, R) }.
