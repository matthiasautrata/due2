%# integrity.lp: the constraints that make a gap an error
%
% The integrity constraints over every earlier file. They are why a deleted rule fails loudly
% (DESIGN.md § Tests): without its rule, some item has no value, some read no outcome, or some
% world no verdict, so the solve has no model and the reply is an `error`, never a verdict.
% Solve 1 does not load this file: its declines and rejections name what is wrong, where a
% failed constraint would only say that something is. Variable letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `rank/2`, `two_valued/1` (kleene.lp); `used/1`, `read_ok/1`, `read_u/1`
%   (operand.lp); `pair/2`, `eqr/3` (compare.lp); `item/1`, `holds/2` (applies.lp);
%   `atom_party/3` (structure.lp); `leaf/1` (constraint.lp); `u_atom/1`, `lit_of/2`, `open/1`,
%   `leaf_lit/3`, `var/1`, `world/1`, `assigned/3`, `crank_in/3`, `completed/3`,
%   `completed_item/1` (completion.lp); `verdict/2` (resolve.lp).
% - **Provides:** nothing: integrity constraints only.

% Every item has exactly one value, and only a ranked one.
:- item(I), #count { V : holds(I, V) } != 1.
:- holds(_, V), not rank(V, _).

% Every read is ok or u, never both or neither; every compared pair has one equality rank.
:- used(Op), #count { ok : read_ok(Op); u : read_u(Op) } != 1.
:- pair(Lv, Rv), #count { N : eqr(Lv, Rv, N) } != 1.

% Every u target or party part of a u atom, and every open leaf, reads exactly one completion
% variable, so a part or a leaf the variable key forgets fails loudly.
:- u_atom(X), holds(part(X, target), u), #count { L : lit_of(part(X, target), L) } != 1.
:- u_atom(X), atom_party(X, F, _), holds(part(X, party(F)), u),
    #count { L : lit_of(part(X, party(F)), L) } != 1.
:- open(C), leaf(C), #count { L, Pol : leaf_lit(C, L, Pol) } != 1.

% In every world, every variable, open node, and completed item has exactly one value, f or t.
:- world(W), var(L), #count { V : assigned(W, L, V) } != 1.
:- world(W), open(C), #count { N : crank_in(W, C, N) } != 1.
:- world(W), completed_item(I), #count { V : completed(W, I, V) } != 1.
:- completed(_, _, V), not two_valued(V).

% Every world has exactly one verdict.
:- world(W), #count { Verdict : verdict(W, Verdict) } != 1.
