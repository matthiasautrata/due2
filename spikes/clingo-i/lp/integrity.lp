%# integrity.lp: the constraints that make a gap an error
%
% The integrity constraints over every earlier file. They are why a deleted rule fails loudly
% (DESIGN.md § Tests): without its rule, some item has no value, some read no outcome, or some
% world no verdict, so the solve has no model and the reply is an `error`, never a verdict.
% Solve 1 does not load this file: its declines and rejections name what is wrong, where a
% failed constraint would only say that something is. Variable letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `rank/2`, `two_valued/1` (kleene.lp); `read_in/2`, `read_ok/2`, `read_u/2`,
%   `read_status/3` (operand.lp); `pair/2`, `eqr/3`, `crank/3`, `evaluates/2` (compare.lp);
%   `item/1`, `holds/2` (applies.lp); `leaf/1` (constraint.lp); `instance/1`, `status/3`
%   (duty.lp);
%   `leaf_status/2`, `opaque_leaf/1`, `open/1`, `leaf_lit/3`, `var/1`, `world/1`, `assigned/3`,
%   `completed/3`, `completed_item/1` (completion.lp); `verdict/2` (resolve.lp).
% - **Provides:** nothing: integrity constraints only.

% Every item has exactly one value, and only a ranked one.
:- item(I), #count { V : holds(I, V) } != 1.
:- holds(_, V), not rank(V, _).

% In every world that reads it, every read is ok or u, never both or neither; every compared
% pair has one equality rank.
:- read_in(W, Op), #count { ok : read_ok(W, Op); u : read_u(W, Op) } != 1.
:- pair(Lv, Rv), #count { N : eqr(Lv, Rv, N) } != 1.

% Every u read and every u leaf has exactly one status, so a cause of u that the statuses
% forget fails loudly, and every open leaf that is not opaque reads exactly one completion
% variable, so a leaf the variable key forgets fails loudly too.
:- read_u(W, Op), #count { S : read_status(W, Op, S) } != 1.
:- leaf(C), crank(k, C, 1), #count { S : leaf_status(C, S) } != 1.
:- open(C), leaf(C), not opaque_leaf(C), #count { L, Pol : leaf_lit(C, L, Pol) } != 1.

% In every completion world, every variable and completed item has exactly one value, `f` or
% `t`. In every world, `k` included, every node the world evaluates has exactly one rank.
:- world(W), var(L), #count { V : assigned(W, L, V) } != 1.
:- evaluates(W, C), #count { N : crank(W, C, N) } != 1.
:- world(W), completed_item(I), #count { V : completed(W, I, V) } != 1.
:- completed(_, _, V), not two_valued(V).

% Every duty instance has exactly one status, so a row the status table forgets fails loudly.
:- instance(Y), #count { S : status(k, Y, S) } != 1.

% Every world has exactly one verdict.
:- world(W), #count { Verdict : verdict(W, Verdict) } != 1.
