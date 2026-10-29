%# integrity.lp: the defects that make a gap an error
%
% The checks over every earlier file. Each check derives a `defect/1` atom instead of failing as
% an integrity constraint, because a constraint only removes the models it fails in: a gap in some
% completions would leave the others, and the cautious solve would read a verdict from them. The
% driver's defect search solves again for a model with a defect, and any one makes the reply an
% `error` that names it (`_solve` in clingo_i/interpret.py; DESIGN.md § Vocabulary). The first
% three checks are of the shape of each atom. The rest are why a deleted rule fails loudly
% (TESTS.md): without its rule, on an input that reaches it, some model leaves an item, a guard, a
% witness condition, a read, or a world without exactly one value. A deletion that changes a value
% without removing one is not caught. explain.lp adds one more check, `candidate_state(X, P)`.
% Solves 0 and 1 do not load this file: their declines and rejections name what is wrong, where a
% defect only names the relation that lost a value. Variable letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `atom/1`, `atom_effect/2`, `atom_policy/2`, `atom_rule/2`, `pre/2`, `space/2`
%   (structure.lp); `rank/2`, `two_valued/1` (kleene.lp); `read_in/3`, `read_ok/3`, `read_u/3`,
%   `read_status/4` (operand.lp); `pair/2`, `eqr/3`, `crank/4`, `evaluates/3` (compare.lp);
%   `item/1`, `holds/2` (applies.lp); `leaf/1` (constraint.lp); `guard/2`, `witness_cond/2`,
%   `obligation_policy/2`, `witness_pair/3`, `instance/2`, `status/4` (duty.lp);
%   `leaf_status/3`, `opaque_leaf/2`, `open/2`, `leaf_lit/4`, `var/1`, `world/1`, `assigned/3`,
%   `completed/3`, `completed_item/1` (completion.lp); `verdict/2` (resolve.lp); `defect_sought/0`
%   (driver).
% - **Provides:** `defect/1`, `guarded/2`, `some_defect/0`.

%*! defect(D)

Check `D` fails in this model: `D` names the check and the term it failed for, such as
`one_value(I)` for an item `I` with no value or two. The reply is an `error` if any model of
solve 2 or 3 has one.
*%
% Each atom has one effect and one source rule (due2-workflows.md §3.1), so that each row of
% explain.lp names exactly one of each. It belongs to at least one policy, and has an entry in
% each. In the spec an atom's policies are its `root` tuples (due2-workflows.md §3.1,
% decisions/0036); the second check asks only that there is one.
defect(one_effect(X)) :- atom(X), #count { Eff : atom_effect(X, Eff) } != 1.
defect(some_policy(X)) :- atom(X), not atom_policy(X, _).
defect(one_rule(X)) :- atom(X), #count { R : atom_rule(X, R) } != 1.

% Every item has exactly one value, and only a ranked one.
defect(one_value(I)) :- item(I), #count { V : holds(I, V) } != 1.
defect(ranked(V)) :- holds(_, V), not rank(V, _).

%*! guarded(Y, P)

Duty atom `Y` has a finding in policy `P` that conjoins its guards: `owed` for a precondition,
`in_force` for a root obligation. Both are defined in duty.lp.
*%
guarded(Y, P) :- pre(X, Y), space(X, P).
guarded(Y, P) :- obligation_policy(Y, P).

% Each member of the sets that duty.lp's `#min` conjoins has exactly one value: a `#min` skips a
% member with none, and would read the conjunction of the rest. `one_value` does not cover a guard:
% a node with no data space is not evaluated there, so `c(C, P)` is not an item (compare.lp). A
% guard is read in world `k`, and a witness condition in each witness pair's world `wit(E)`.
defect(guard_value(Y, C, P)) :- guarded(Y, P), guard(Y, C), #count { V : holds(c(C, P), V) } != 1.
defect(witness_rank(Y, C, P, E)) :- witness_pair(Y, P, E), witness_cond(Y, C),
    #count { N : crank(wit(E), C, P, N) } != 1.

% In every world and data space that reads it, every read is ok or u, never both or neither;
% every compared pair has one equality rank.
defect(one_read(W, Op, P)) :- read_in(W, Op, P),
    #count { ok : read_ok(W, Op, P); u : read_u(W, Op, P) } != 1.
defect(one_eqr(Lv, Rv)) :- pair(Lv, Rv), #count { N : eqr(Lv, Rv, N) } != 1.

% In each data space, every u read and every u leaf has exactly one status, so a cause of u that
% the statuses forget fails loudly, and every open leaf that is not opaque reads exactly one
% completion variable, so a leaf the variable key forgets fails loudly too.
defect(read_status(W, Op, P)) :- read_u(W, Op, P), #count { S : read_status(W, Op, P, S) } != 1.
defect(leaf_status(C, P)) :- leaf(C), crank(k, C, P, 1), #count { S : leaf_status(C, P, S) } != 1.
defect(leaf_lit(C, P)) :- open(C, P), leaf(C), not opaque_leaf(C, P),
    #count { L, Pol : leaf_lit(C, P, L, Pol) } != 1.

% In every completion world, every variable and completed item has exactly one value, `f` or
% `t`. In every world, `k` included, every node the world evaluates in a data space has exactly
% one rank there.
defect(assigned(W, L)) :- world(W), var(L), #count { V : assigned(W, L, V) } != 1.
defect(crank(W, C, P)) :- evaluates(W, C, P), #count { N : crank(W, C, P, N) } != 1.
defect(completed(W, I)) :- world(W), completed_item(I), #count { V : completed(W, I, V) } != 1.
defect(two_valued(V)) :- completed(_, _, V), not two_valued(V).

% Every duty instance, one per entry, has exactly one status, so a row the status table forgets
% fails loudly.
defect(status(Y, P)) :- instance(Y, P), #count { S : status(k, Y, P, S) } != 1.

% Every world has exactly one verdict.
defect(verdict(W)) :- world(W), #count { Verdict : verdict(W, Verdict) } != 1.

#show defect/1.

%*! some_defect

Some check fails in this model. The driver's defect search asks for a model with it.
*%
some_defect :- defect(_).

% `defect_sought` is false while the driver enumerates, so this constraint removes nothing; set
% true, it keeps only the models with a defect.
#external defect_sought.
:- defect_sought, not some_defect.
