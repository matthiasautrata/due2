%# xone.lp: two coverage targets, the liveness checks of an xone
%
% An `xone` passes liveness to its members term by term (explain.lp, `live/4`), and each of
% its two checks needs a tree larger than the `trees` and `pinned` spaces reach
% (tests/spaces.py):
%
% - A positive `xone` passes liveness through a term only when no other member of the term is
%   `f` there. To test that check, a `u` leaf must lie in an `xone` each of whose terms has
%   such a member, which needs two members that are `t`. The only `t` leaf of this space is
%   `l(0,eq)`, and two leaves with the same content under an `xone` are malformed
%   (decisions/0022), so one of the two is compound. The smallest such `xone` is
%   `xone(t, or(t, u))`.
% - A negated `xone` passes liveness to the members of one term only when no other negated term
%   is `f`. To test that check, a `u` leaf must lie in a compound term of a negated `xone`
%   beside a term that is `t`, as in `neg(xone(t, and(f, u)))`.
%
% Either way, the rule's atom must not be `f`, since an `f` atom reports no unknown parts; so
% the `xone` needs a sibling that keeps the tree from being `f`. The smallest trees,
% `or(xone(t, or(t, u)), t)` with size 7 and `or(neg(xone(t, and(f, u))), t)` with size 8, are
% past the bounds of the `trees` and `pinned` spaces.
%
% So this space fixes the two forms and enumerates only their holes. Each answer set is one rule
% whose constraint is `node(F, X, C)`, where `X` is `node(xone, A, B)` or
% `neg(node(xone, A, B))`: `F` is `and`, `or`, or `xone`; `A` and `B` are two different trees
% from the catalog, at least one of them not a leaf; `C` comes from the catalog. The whole tree
% has at most `largest` nodes and leaves. Operand 0 is `value` and operand 1 is `unresolved`,
% so the leaves are `t`, `f`, and a paired `u` (rules.lp).
%
% - **Constants:** `largest`, the largest tree. Its holes are at most `largest - 4` in size, the
%   most that fits beside the rest of the positive form; the bound on the whole tree keeps the
%   holes of the negated form one smaller.
% - **Shows:** `slot/2`, `operand/2`, `conflict/1`, as rules.lp does.

#const largest = 8.
#const operands = 2.
#const operators = 2.
#const size = largest - 4.
#include "trees.lp".

compound(T) :- tree(T, S), S > 1.
pair(A, B, SA + SB) :- tree(A, SA), tree(B, SB), A < B, 1 { compound(A); compound(B) }.
hole(node(xone, A, B), 1 + S) :- pair(A, B, S), 1 + S <= largest - 2.
hole(neg(node(xone, A, B)), 2 + S) :- pair(A, B, S), 2 + S <= largest - 2.
shape(node(F, X, C)) :- conn(F), hole(X, SX), tree(C, SC), 1 + SX + SC <= largest.

kind(permission; prohibition).
{ slot(1, r(K, T)) : kind(K), shape(T) } = 1.
operand(0, value).
operand(1, unresolved).
conflict(perm).

#show slot/2.
#show operand/2.
#show conflict/1.
