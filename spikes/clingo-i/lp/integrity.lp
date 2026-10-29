%# integrity.lp: the constraints that make a gap an error
%
% The integrity constraints over every earlier file. The first three check the shape of each atom.
% The rest are why a deleted rule fails loudly (TESTS.md): without its rule, some item has no
% value, some read no outcome, or some world no verdict, so the solve has no model and the reply
% is an `error`, never a verdict.
% Solves 0 and 1 do not load this file: its declines and rejections name what is wrong, where a
% failed constraint would only say that something is. Variable letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `atom/1`, `atom_effect/2`, `atom_policy/2`, `atom_rule/2` (structure.lp);
%   `rank/2`, `two_valued/1` (kleene.lp); `read_in/3`, `read_ok/3`, `read_u/3`,
%   `read_status/4` (operand.lp); `pair/2`, `eqr/3`, `crank/4`, `evaluates/3` (compare.lp);
%   `item/1`, `holds/2` (applies.lp); `leaf/1` (constraint.lp); `instance/2`, `status/4`
%   (duty.lp); `leaf_status/3`, `opaque_leaf/2`, `open/2`, `leaf_lit/4`, `var/1`, `world/1`,
%   `assigned/3`, `completed/3`, `completed_item/1` (completion.lp); `verdict/2` (resolve.lp).
% - **Provides:** nothing: integrity constraints only.

% Each atom has one effect and one source rule (due2-workflows.md §3.1), so that each row of
% explain.lp names exactly one of each. It belongs to at least one policy, and has an entry in
% each. In the spec an atom's policies are its `root` tuples (due2-workflows.md §3.1,
% decisions/0036); the second constraint checks only that there is one.
:- atom(X), #count { Eff : atom_effect(X, Eff) } != 1.
:- atom(X), not atom_policy(X, _).
:- atom(X), #count { R : atom_rule(X, R) } != 1.

% Every item has exactly one value, and only a ranked one.
:- item(I), #count { V : holds(I, V) } != 1.
:- holds(_, V), not rank(V, _).

% In every world and data space that reads it, every read is ok or u, never both or neither;
% every compared pair has one equality rank.
:- read_in(W, Op, P), #count { ok : read_ok(W, Op, P); u : read_u(W, Op, P) } != 1.
:- pair(Lv, Rv), #count { N : eqr(Lv, Rv, N) } != 1.

% In each data space, every u read and every u leaf has exactly one status, so a cause of u that
% the statuses forget fails loudly, and every open leaf that is not opaque reads exactly one
% completion variable, so a leaf the variable key forgets fails loudly too.
:- read_u(W, Op, P), #count { S : read_status(W, Op, P, S) } != 1.
:- leaf(C), crank(k, C, P, 1), #count { S : leaf_status(C, P, S) } != 1.
:- open(C, P), leaf(C), not opaque_leaf(C, P), #count { L, Pol : leaf_lit(C, P, L, Pol) } != 1.

% In every completion world, every variable and completed item has exactly one value, `f` or
% `t`. In every world, `k` included, every node the world evaluates in a data space has exactly
% one rank there.
:- world(W), var(L), #count { V : assigned(W, L, V) } != 1.
:- evaluates(W, C, P), #count { N : crank(W, C, P, N) } != 1.
:- world(W), completed_item(I), #count { V : completed(W, I, V) } != 1.
:- completed(_, _, V), not two_valued(V).

% Every duty instance, one per entry, has exactly one status, so a row the status table forgets
% fails loudly.
:- instance(Y, P), #count { S : status(k, Y, P, S) } != 1.

% Every world has exactly one verdict.
:- world(W), #count { Verdict : verdict(W, Verdict) } != 1.
