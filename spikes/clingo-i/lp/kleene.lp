%# kleene.lp: truth values, and the constraints that make a gap an error
%
% The three truth values and their order (due2-workflows.md §5.1), and the integrity constraints
% over every later file. The constraints are why a deleted rule fails loudly
% (DESIGN.md § Tests): without its rule, some item has no value, or some world no verdict, so the
% solve has no model and the reply is an `error`, never a verdict. Variable letters:
% DESIGN.md § Vocabulary.
%
% - **Consumes:** `item/1`, `holds/2`, `part_of/2` (applies.lp); `lit_of/2`, `var/1`,
%   `world/1`, `assigned/3`, `completed/3` (completion.lp); `verdict/2` (resolve.lp).
% - **Provides:** `rank/2`, `two_valued/1`.

%*! rank(V, N)

Truth value `V` has rank `N` in the order `f` < `u` < `t`. Kleene conjunction is the value of
the least rank (`#min`, applies.lp and completion.lp).
*%
rank(f, 0).
rank(u, 1).
rank(t, 2).

%*! two_valued(V)

`V` is `f` or `t`: a value a completed item can take.
*%
two_valued(f; t).

%## Integrity

% Every item has exactly one value, and only a ranked one.
:- item(I), #count { V : holds(I, V) } != 1.
:- holds(_, V), not rank(V, _).

% Every u part reads exactly one literal, so a part the literal key forgets fails loudly.
:- part_of(_, I), holds(I, u), #count { L : lit_of(I, L) } != 1.

% In every world, every variable and every item has exactly one value, f or t.
:- world(W), var(L), #count { V : assigned(W, L, V) } != 1.
:- world(W), item(I), #count { V : completed(W, I, V) } != 1.
:- completed(_, _, V), not two_valued(V).

% Every world has exactly one verdict.
:- world(W), #count { Verdict : verdict(W, Verdict) } != 1.
