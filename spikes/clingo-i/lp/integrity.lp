%# integrity.lp: the constraints that make a gap an error
%
% The integrity constraints over every earlier file. They are why a deleted rule fails loudly
% (DESIGN.md § Tests): without its rule, some item has no value, some read no outcome, or some
% world no verdict, so the solve has no model and the reply is an `error`, never a verdict.
% Solve 1 does not load this file: its declines and rejections name what is wrong, where a
% failed constraint would only say that something is. Variable letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `rank/2`, `two_valued/1` (kleene.lp); `used/1`, `read_ok/1`, `read_u/1`
%   (operand.lp); `pair/2`, `eqr/3` (compare.lp); `item/1`, `holds/2`, `part_of/2`
%   (applies.lp); `u_atom/1`, `lit_of/2`, `var/1`, `world/1`, `assigned/3`, `completed/3`,
%   `completed_item/1` (completion.lp); `verdict/2` (resolve.lp).
% - **Provides:** nothing: integrity constraints only.

% Every item has exactly one value, and only a ranked one.
:- item(I), #count { V : holds(I, V) } != 1.
:- holds(_, V), not rank(V, _).

% Every read is ok or u, never both or neither; every compared pair has one equality rank.
:- used(Op), #count { ok : read_ok(Op); u : read_u(Op) } != 1.
:- pair(Lv, Rv), #count { N : eqr(Lv, Rv, N) } != 1.

% Every u part of a u atom reads exactly one completion variable, so a part the variable key
% forgets fails loudly.
:- u_atom(X), part_of(X, I), holds(I, u), #count { L : lit_of(I, L) } != 1.

% In every world, every variable and every completed item has exactly one value, f or t.
:- world(W), var(L), #count { V : assigned(W, L, V) } != 1.
:- world(W), completed_item(I), #count { V : completed(W, I, V) } != 1.
:- completed(_, _, V), not two_valued(V).

% Every world has exactly one verdict.
:- world(W), #count { Verdict : verdict(W, Verdict) } != 1.
