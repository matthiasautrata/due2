%# negxone.lp: a coverage target, a negated xone with a compound term
%
% A negated `xone` passes liveness to the members of one term only when no other negated term
% is `f` (explain.lp, `live/4`). To test that check, a `u` leaf must lie in a compound term of
% a negated `xone` beside a term that is `t`, and the rule's atom must not be `f`, since an `f`
% atom reports no unknown parts; so the negated `xone` needs a sibling that keeps the tree from
% being `f`. The smallest such tree, `or(neg(xone(t, and(f, u))), t)`, has size 8, past the
% bounds of the `trees` and `pinned` spaces (tests/spaces.py).
%
% So this space fixes the form and enumerates only its holes. Each answer set is one rule
% whose constraint is `node(F, neg(node(xone, A, B)), C)`: `F` is `and`, `or`, or `xone`; `A`
% and `B` come from the catalog, and at least one of them is not a leaf; `C` comes from the
% catalog. The whole tree has at most `largest` nodes and leaves. Operand 0 is `value` and
% operand 1 is `unresolved`, so the leaves are `t`, `f`, and a paired `u` (rules.lp).
%
% - **Constants:** `largest`, the largest tree. Its holes are at most `largest - 5` in size, the
%   most that fits beside the rest of the shape.
% - **Shows:** `slot/2`, `operand/2`, `conflict/1`, as rules.lp does.

#const largest = 8.
#const operands = 2.
#const operators = 2.
#const size = largest - 5.
#include "trees.lp".

compound(T) :- tree(T, S), S > 1.
negxone(neg(node(xone, A, B)), 2 + SA + SB) :- tree(A, SA), tree(B, SB), A <= B,
    2 + SA + SB <= largest - 2, 1 { compound(A); compound(B) }.
shape(node(F, X, C)) :- conn(F), negxone(X, SX), tree(C, SC), 1 + SX + SC <= largest.

kind(permission; prohibition).
{ slot(1, r(K, T)) : kind(K), shape(T) } = 1.
operand(0, value).
operand(1, unresolved).
conflict(perm).

#show slot/2.
#show operand/2.
#show conflict/1.
