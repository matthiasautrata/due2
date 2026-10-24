%# completion.lp: the completion variables, and one completion of them
%
% Each `u` part of a `u` finding is completed or opaque (due2-workflows.md §6.4, decisions/0016).
% The findings are an atom's `applies`, and a duty's `owed`, `in_force`, and `fulfilled`. A `u`
% leaf whose operand reads an `unresolved` state property is completed: it reads a variable keyed
% by the comparison it makes, so a leaf and its complement read one variable with opposite
% polarities (decisions/0012), and a guard leaf and a rule leaf on one comparison read one
% variable. Every other `u` part is opaque: a `u` target or party part (an absent request field
% is `missing`), and a `u` leaf whose status is `missing`, `invalid`, `conflict`, or `misfit`. An
% opaque part stays `u` in every completion, and when it leaves the finding `u`, the finding's
% own variable `fin(I)` completes it. A `u` `fulfilled` is one variable of its own, `ful(Y)`,
% independent of every other as `fin(I)` is. A `u` part of an `f` finding reads none: the
% finding is `f` in every completion. One answer set gives every variable `t` or `f`, so the
% answer sets of solve 2 are the completions, `2^n` of them for `n` variables. Under each
% completion, the open nodes of every tree are re-evaluated under strong Kleene logic, and every
% `u` finding is re-derived. Every completed value is indexed by a world, so that pivot.lp can
% hold a second completion beside the first. Variable letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `operator/2` (lift.lp); `atom/1`, `atom_party/3` (structure.lp);
%   `scope/2`, `member/2`, `leaf/1`, `left/2`, `op/2`, `right/2`, `unit/2` (constraint.lp);
%   `src/2`, `prop/2`, `has_scheme/1`, `read_ok/2`, `read_status/3` (operand.lp); `crank/3`,
%   `evaluates/2` (compare.lp); `holds/2`, `part_of/2`, `atom_constraint/2` (applies.lp);
%   `rank/2` (kleene.lp); `pre/2`, `obligation/1` (structure.lp); `guard/2`, `policy_match/2`,
%   `instance/1` (duty.lp).
% - **Provides:** `duty_item/1`, `u_item/1`, `item_root/2`, `finding_atom/2`, `leaf_status/2`,
%   `opaque_leaf/1`, `opened/2`, `open/1`, `opaque_item/1`, `complement/2`, `op_literal/3`,
%   `leaf_key/5`, `leaf_attr/2`, `attr_apart/2`, `same_key/2`, `leaf_lit/3`, `var/1`, `reads/2`,
%   `world/1`, `assigned/3`, `part_in/3`, `root_in/4`, `pre_in/3`, `completed/3`,
%   `completed_item/1`; extends `crank/3` and `evaluates/2` (compare.lp).

%## Findings

%*! duty_item(I)

`I` is a duty finding: `owed(Y)`, `in_force(Y)`, or `fulfilled(Y)`. duty.lp derives each.
*%
duty_item(owed(Y)) :- pre(_, Y).
duty_item(in_force(Y)) :- obligation(Y).
duty_item(fulfilled(Y)) :- instance(Y).

%*! u_item(I)

Finding `I` is `u`, so completion decides it: `applies(X)` of an atom, or a duty finding.
*%
u_item(applies(X)) :- holds(applies(X), u).
u_item(I) :- duty_item(I), holds(I, u).

%*! item_root(I, C)

Constraint node `C` is a root of a tree that finding `I` conjoins: a constraint of the atom for
`applies(X)`, and a guard of the duty for `owed(Y)` and `in_force(Y)`. A `fulfilled` finding has
none: it is one variable of its own.
*%
item_root(applies(X), C) :- atom_constraint(X, C).
item_root(owed(Y), C) :- pre(_, Y), guard(Y, C).
item_root(in_force(Y), C) :- obligation(Y), guard(Y, C).

%*! finding_atom(I, X)

Finding `I` is a finding of the atom or duty atom `X`. pivot.lp names `X` as unknown.
*%
finding_atom(applies(X), X) :- atom(X).
finding_atom(owed(Y), Y) :- duty_item(owed(Y)).
finding_atom(in_force(Y), Y) :- duty_item(in_force(Y)).
finding_atom(fulfilled(Y), Y) :- duty_item(fulfilled(Y)).

%## Statuses

%*! leaf_status(C, S)

Leaf `C` is `u` in world `k` with status `S`: its operand's read status there, or `misfit` when
the read is `ok` but a value does not fit the operator. A misfit is due2-workflows.md §5.4 step
3. Every `u` leaf has exactly one status (integrity.lp).
*%
leaf_status(C, S) :- evaluates(k, C), leaf(C), left(C, Op), read_status(k, Op, S).
% A leaf whose read is ok has rank 1 only when some comparison is a misfit (compare.lp).
leaf_status(C, misfit) :- evaluates(k, C), leaf(C), left(C, Op), read_ok(k, Op),
    crank(k, C, 1).

%*! opaque_leaf(C)

Leaf `C` is `u` for a reason other than an `unresolved` value, so it is never paired.
*%
opaque_leaf(C) :- leaf_status(C, S), S != unresolved.

%## Open nodes

%*! opened(I, C)

Constraint node `C` is `u`, and lies on a path of `u` nodes from a root of the `u` finding `I`
(`item_root/2`). Only these nodes are re-evaluated: a node that is `t` or `f` keeps that value
in every completion, because strong Kleene logic never turns `t` or `f` into the other when a
`u` is replaced by `t` or `f`.
*%
opened(I, C) :- u_item(I), item_root(I, C), holds(c(C), u).
opened(I, D) :- opened(I, C), member(C, D), holds(c(D), u).

%*! open(C)

Node `C` is opened for some finding, so each completion world evaluates it (`evaluates/2`) and
gives it a rank (`crank/3`).
*%
open(C) :- opened(_, C).

%*! opaque_item(I)

The `u` finding `I` has an opaque part, so it can stay `u` in a world and has its own variable
`fin(I)`. For an atom the part is a `u` target or party part; for an obligation's `in_force`, a
`u` match of its policy, which only such parts make `u` (`policy_match/2` in duty.lp); and for
either, or for `owed`, an opaque leaf in an opened tree.
*%
opaque_item(applies(X)) :- u_item(applies(X)), holds(part(X, target), u).
opaque_item(applies(X)) :- u_item(applies(X)), atom_party(X, F, _), holds(part(X, party(F)), u).
opaque_item(in_force(Y)) :- u_item(in_force(Y)), policy_match(Y, 1).
opaque_item(I) :- opened(I, C), opaque_leaf(C).

%## Paired variables

%*! complement(Base, O)

`O` is the complement of the operator `Base`: `neq` of `eq`, `gteq` of `lt`, `gt` of `lteq`, and
`isNoneOf` of `isAnyOf`. The pairs are those of due2-workflows.md §6.4.
*%
complement(eq, neq). complement(lt, gteq). complement(lteq, gt). complement(isAnyOf, isNoneOf).

%*! op_literal(O, Base, Pol)

A leaf with operator `O` asserts the operator `Base` with polarity `Pol`, `pos` or `neg`: a
complement asserts its `Base` negatively, and every other operator asserts itself.
*%
op_literal(O, O, pos) :- operator(_, O), not complement(_, O).
op_literal(O, Base, neg) :- complement(Base, O).

%*! leaf_key(C, Scope, Src, Prop, Base)

The open `unresolved` leaf `C` has the scalar part of its completion key: its scope, the
source and property its left operand is bound to (not the operand IRI, which two layers may
bind to one property), and its positive operator.
*%
leaf_key(C, Scope, Src, Prop, Base) :- open(C), leaf_status(C, unresolved), scope(C, Scope),
    left(C, Op), src(Op, Src), prop(Op, Prop), op(C, O), op_literal(O, Base, _).

%*! leaf_attr(C, Attr)

The open `unresolved` leaf `C` has `Attr` in the set part of its key: `right(Term)` for each
right operand value, `unit(Iri)` for each unit, and `concept` when its left operand has a
concept scheme. Two operands bound to one property, one with a scheme and one without, read
`eq` as ⊑ and as identity, so their `eq` and `neq` are not complements (due2-workflows.md §6.4).
*%
leaf_attr(C, right(Term)) :- leaf_key(C, _, _, _, _), right(C, Term).
leaf_attr(C, unit(Iri)) :- leaf_key(C, _, _, _, _), unit(C, Iri).
leaf_attr(C, concept) :- leaf_key(C, _, _, _, _), left(C, Op), has_scheme(Op).

%*! attr_apart(C, D)

The open `unresolved` leaves `C` and `D` have the same scalar key, and `C` has an attribute `D`
lacks.
*%
attr_apart(C, D) :- leaf_key(C, Scope, Src, Prop, Base), leaf_key(D, Scope, Src, Prop, Base),
    leaf_attr(C, Attr), not leaf_attr(D, Attr).

%*! same_key(C, D)

The open `unresolved` leaves `C` and `D` have the same completion key: the same scalar key, and
the same attribute set. The relation is reflexive, symmetric, and transitive.
*%
same_key(C, D) :- leaf_key(C, Scope, Src, Prop, Base), leaf_key(D, Scope, Src, Prop, Base),
    not attr_apart(C, D), not attr_apart(D, C).

%*! leaf_lit(C, L, Pol)

The open `unresolved` leaf `C` reads the variable `L` with polarity `Pol`. `L` is `cons(D)`,
with `D` the least leaf of `C`'s key class, so leaves with the same key read one variable.
Right operand values are compared as terms, so `5` and `5.0` give two variables. That loses
precision, never soundness (due2-workflows.md §6.4, "parts that are not the same expression").
*%
leaf_lit(C, cons(D), Pol) :- leaf_key(C, _, _, _, _), op(C, O), op_literal(O, _, Pol),
    D = #min { D2 : same_key(C, D2) }.

%## The completion

%*! var(L)

`L` is a completion variable: `cons(D)` for a key class of paired leaves, `fin(I)` for the
opaque finding `I`, or `ful(Y)` for a `u` `fulfilled(Y)`. interpret.py counts the `var/1`
atoms of the first answer set, the same in every answer set, and declines the vector above the
variable cap (correctness-strategy.md §3).
*%
var(L) :- leaf_lit(_, L, _).
var(fin(I)) :- opaque_item(I).
var(ful(Y)) :- u_item(fulfilled(Y)).
% Shown so that interpret.py can count them: in cautious and brave mode a model reports only
% shown atoms, and grounding leaves `var/1` atoms that no model makes true.
#show var/1.

%*! reads(I, L)

The `u` finding `I` reads the variable `L`: a paired leaf of an opened tree, its own `fin(I)`,
or, for `fulfilled(Y)`, `ful(Y)`. pivot.lp names `I`'s atom when `L` is pivotal.
*%
reads(I, L) :- opened(I, C), leaf_lit(C, L, _).
reads(I, fin(I)) :- opaque_item(I).
reads(fulfilled(Y), ful(Y)) :- u_item(fulfilled(Y)).

%*! world(W)

`W` is a completion world: an index for one completion held in the answer set. World `c`
(for "completion") is the completion the answer set chose; pivot.lp adds `flip`. The Kleene
world `k` of `crank/3` is not one: it holds no completion.
*%
world(c).

%*! assigned(W, L, V)

In world `W`, variable `L` has value `V`, `t` or `f`.
*%
% The choice: exactly one value for each variable in world c.
{ assigned(c, L, t); assigned(c, L, f) } = 1 :- var(L).

% A completion world's ranks. It evaluates the open nodes, and the connective rules of
% compare.lp re-evaluate each open connective from its members, so a world can leave a node
% `u`. A member that is not open keeps its world-`k` rank. An opaque leaf keeps rank 1. A paired
% leaf takes its variable's value, negated for polarity `neg`.
evaluates(W, C) :- world(W), open(C).
crank(W, D, N) :- world(W), open(C), member(C, D), not open(D), crank(k, D, N).
crank(W, C, 1) :- world(W), open(C), opaque_leaf(C).
crank(W, C, N) :- leaf_lit(C, L, pos), assigned(W, L, V), rank(V, N).
crank(W, C, 2 - N) :- leaf_lit(C, L, neg), assigned(W, L, V), rank(V, N).

%*! part_in(W, I, N)

In world `W`, the part `I` of a `u` atom has rank `N`. A constraint part whose root is open
takes its root's rank in the world. A `u` target or party part is opaque and keeps rank 1.
Every other part keeps its rank.
*%
part_in(W, part(X, cons(C)), N) :- opened(applies(X), C), atom_constraint(X, C),
    crank(W, C, N).
part_in(W, I, N) :- world(W), u_item(applies(X)), part_of(X, I), holds(I, V), V != u,
    rank(V, N).
part_in(W, part(X, target), 1) :- world(W), u_item(applies(X)), holds(part(X, target), u).
part_in(W, part(X, party(F)), 1) :- world(W), u_item(applies(X)), atom_party(X, F, _),
    holds(part(X, party(F)), u).

%*! root_in(W, I, C, N)

In world `W`, the guard `C` of the `u` duty finding `I` has rank `N`: its rank in the world when
it is open, and its rank in world `k` otherwise.
*%
root_in(W, I, C, N) :- opened(I, C), item_root(I, C), duty_item(I), crank(W, C, N).
root_in(W, I, C, N) :- world(W), u_item(I), duty_item(I), item_root(I, C), holds(c(C), V),
    V != u, rank(V, N).

%*! pre_in(W, I, N)

In world `W`, the parts of the `u` finding `I` have Kleene conjunction of rank `N`. The parts
are an atom's parts, the guards of `owed`, and the policy match and guards of `in_force`, as
duty.lp conjoins them in world `k`. Rank 1 means that an opaque part leaves the finding `u`. A `u`
`fulfilled` has no `pre_in`: its variable `ful(Y)` decides it.
*%
pre_in(W, applies(X), N) :- world(W), u_item(applies(X)),
    N = #min { M, I : part_of(X, I), part_in(W, I, M) }.
% A `u` `owed` has a `u` guard, so the set is never empty.
pre_in(W, owed(Y), N) :- world(W), u_item(owed(Y)),
    N = #min { M, C : root_in(W, owed(Y), C, M) }.
% The tag `match` keeps the policy match's rank apart from a guard's equal rank in the set.
pre_in(W, in_force(Y), N) :- world(W), u_item(in_force(Y)),
    N = #min { Np, match : policy_match(Y, Np); M, C : root_in(W, in_force(Y), C, M) }.

%*! completed(W, I, V)

In world `W`, the finding `I` has value `V`, `t` or `f`. A finding that is not `u` keeps its
value. A `u` `applies`, `owed`, or `in_force` takes the conjunction of its parts in the world,
and when that is `u`, the value of its variable `fin(I)`. A `u` `fulfilled(Y)` takes the value
of `ful(Y)`.
*%
completed(W, I, V) :- world(W), completed_item(I), holds(I, V), V != u.
completed(W, I, V) :- pre_in(W, I, N), N != 1, rank(V, N).
completed(W, I, V) :- pre_in(W, I, 1), assigned(W, fin(I), V).
completed(W, fulfilled(Y), V) :- u_item(fulfilled(Y)), assigned(W, ful(Y), V).

%*! completed_item(I)

`I` has a completed value in every world: `applies(X)` for each atom, and each duty finding. The
constraint is in integrity.lp.
*%
completed_item(applies(X)) :- atom(X).
completed_item(I) :- duty_item(I).
