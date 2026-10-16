% completion.lp: one completion of the unknown parts (workflows §6.4).
% Each U part is its own variable; correlated constraint parts land with constraints.

var(I) :- part_item(_, I), holds(I, u).
{ cval(I, t); cval(I, f) } = 1 :- var(I).
cval(I, V) :- part_item(_, I), holds(I, V), V != u.
cval(applies(X), V) :- atom(X), rank(V, N), N = #min { R : part_item(X, I), cval(I, W), rank(W, R) }.
