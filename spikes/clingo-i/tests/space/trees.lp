%# trees.lp: the catalog of constraint trees up to a size
%
% A tree is a leaf or a node. The leaf `l(O, P)` compares operand `O` under operator `P` with the
% right operand 1, as every leaf of the brute-force differential does. The node `neg(A)` is
% `dprod:not`, and `node(F, A, B)` or `node(F, A, B, C)` is `F`, one of `and`, `or`, and `xone`,
% over two or three members. A tree's size counts its leaves and nodes.
%
% A node's members are sorted, so each multiset of members is one tree. That drops no input:
% the members are rendered as repeated RDF objects, which have no order. The members of an
% `xone` are a set: two equal leaves in an `xone` are malformed (decisions/0022), and two equal
% compound members, which are admitted, are left out to keep the catalog small.
%
% - **Constants,** set by the program that includes this one: `operands`, the operands the leaves
%   read; `operators`, 2 for `eq` and `neq` only, 4 for `lt` and `gteq` as well; `size`, the
%   largest tree.
% - **Provides:** `tree/2`, a tree and its size.

op(eq; neq).
op(lt; gteq) :- operators = 4.
tree(l(O, P), 1) :- O = 0..operands - 1, op(P).
tree(neg(A), S + 1) :- tree(A, S), S < size.

% The sizes are fixed before the lookups, so grounding joins only trees that fit. The members of
% `and` and `or` are sorted with `<=`, those of `xone` with `<`.
conn(and; or; xone).
tree(node(F, A, B), S) :- conn(F), F != xone, S = 3..size, SA = 1..S - 2,
    tree(A, SA), tree(B, S - 1 - SA), A <= B.
tree(node(F, A, B, C), S) :- conn(F), F != xone, S = 4..size, SA = 1..S - 3, SB = 1..S - 2 - SA,
    tree(A, SA), tree(B, SB), A <= B, tree(C, S - 1 - SA - SB), B <= C.
tree(node(xone, A, B), S) :- S = 3..size, SA = 1..S - 2,
    tree(A, SA), tree(B, S - 1 - SA), A < B.
tree(node(xone, A, B, C), S) :- S = 4..size, SA = 1..S - 3, SB = 1..S - 2 - SA,
    tree(A, SA), tree(B, SB), A < B, tree(C, S - 1 - SA - SB), B < C.
