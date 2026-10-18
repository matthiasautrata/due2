%# completion.lp: the completion variables, and one completion of them
%
% Each `u` part of a `u` atom is completed or opaque (due2-workflows.md §6.4, decisions/0016).
% A `u` leaf whose operand reads an `unresolved` state property is completed: it reads a
% variable keyed by the comparison it makes, so a leaf and its complement read one variable
% with opposite polarities (decisions/0012). Every other `u` part is opaque: a `u` target or
% party part (an absent request field is `missing`), and a `u` leaf whose status is `missing`,
% `invalid`, `conflict`, or `misfit`. An opaque part stays `u` in every completion, and when it
% leaves the atom's finding `u`, the atom's own variable `fin(X)` completes the finding. A `u`
% part of an `f` atom reads none: the atom is `f` in every completion. One answer set gives
% every variable `t` or `f`, so solve 2's answer sets are the completions, `2^n` of them for
% `n` variables. Under each completion, the open nodes of every tree are re-evaluated under
% strong Kleene logic, and every `u` finding is re-derived. Every completed value is indexed by
% a world, so that pivot.lp can hold a second completion beside the first. Variable letters:
% DESIGN.md § Vocabulary.
%
% - **Consumes:** `operator/2` (lift.lp); `atom/1`, `atom_party/3` (structure.lp);
%   `scope/2`, `member/2`, `leaf/1`, `left/2`, `op/2`, `right/2`, `unit/2` (constraint.lp);
%   `src/2`, `prop/2`, `read_ok/1`, `read_status/2` (operand.lp); `crank/3` (compare.lp);
%   `holds/2`, `part_of/2`, `atom_constraint/2` (applies.lp); `rank/2` (kleene.lp).
% - **Provides:** `u_atom/1`, `leaf_status/2`, `opaque_leaf/1`, `opened/2`, `open/1`,
%   `opaque_atom/1`, `complement/2`, `op_literal/3`, `leaf_key/5`, `leaf_attr/2`,
%   `attr_apart/2`, `same_key/2`, `leaf_lit/3`, `var/1`, `reads/2`, `world/1`, `assigned/3`,
%   `part_in/3`, `pre_in/3`, `completed/3`, `completed_item/1`; extends `crank/3` and
%   `evaluates/2` (compare.lp).

%*! u_atom(X)

Atom `X`'s finding is `u`, so completion decides it.
*%
u_atom(X) :- holds(applies(X), u).

%## Statuses

%*! leaf_status(C, S)

Leaf `C` is `u` with status `S`: its operand's read status, or `misfit` when the read is `ok` but a
value does not fit the operator. A misfit is due2-workflows.md §5.4 step 3. Every `u` leaf has
exactly one status (integrity.lp).
*%
leaf_status(C, S) :- leaf(C), left(C, Op), read_status(Op, S).
% A leaf whose read is ok has rank 1 only when some comparison is a misfit (compare.lp).
leaf_status(C, misfit) :- leaf(C), left(C, Op), read_ok(Op), crank(k, C, 1).

%*! opaque_leaf(C)

Leaf `C` is `u` for a reason other than an `unresolved` value, so it is never paired.
*%
opaque_leaf(C) :- leaf_status(C, S), S != unresolved.

%## Open nodes

%*! opened(X, C)

Constraint node `C` is `u`, and lies on a path of `u` nodes from a constraint root of the `u`
atom `X`. Only these nodes are re-evaluated: a node that is `t` or `f` keeps that value in every
completion, because strong Kleene logic never turns `t` or `f` into the other when a `u` is
replaced by `t` or `f`.
*%
opened(X, C) :- u_atom(X), atom_constraint(X, C), holds(c(C), u).
opened(X, D) :- opened(X, C), member(C, D), holds(c(D), u).

%*! open(C)

Node `C` is opened for some atom, so each completion world evaluates it (`evaluates/2`) and
gives it a rank (`crank/3`).
*%
open(C) :- opened(_, C).

%*! opaque_atom(X)

The `u` atom `X` has an opaque part: a `u` target or party part, or an opaque leaf in an
opened tree. Its finding can stay `u` in a world, so it has its own variable `fin(X)`.
*%
opaque_atom(X) :- u_atom(X), holds(part(X, target), u).
opaque_atom(X) :- u_atom(X), atom_party(X, F, _), holds(part(X, party(F)), u).
opaque_atom(X) :- opened(X, C), opaque_leaf(C).

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
right operand value, and `unit(Iri)` for each unit.
*%
leaf_attr(C, right(Term)) :- leaf_key(C, _, _, _, _), right(C, Term).
leaf_attr(C, unit(Iri)) :- leaf_key(C, _, _, _, _), unit(C, Iri).

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

`L` is a completion variable: `cons(D)` for a key class of paired leaves, or `fin(X)` for the
opaque atom `X`. interpret.py counts the `var/1` atoms of the first answer set, the same in
every answer set, and declines the vector above the variable cap (correctness-strategy.md §3).
*%
var(L) :- leaf_lit(_, L, _).
var(fin(X)) :- opaque_atom(X).
% Shown so that interpret.py can count them: in cautious and brave mode a model reports only
% shown atoms, and grounding leaves `var/1` atoms that no model makes true.
#show var/1.

%*! reads(X, L)

The `u` atom `X` reads the variable `L`: a paired leaf of an opened tree, or its own `fin(X)`.
pivot.lp names `X` when `L` is pivotal.
*%
reads(X, L) :- opened(X, C), leaf_lit(C, L, _).
reads(X, fin(X)) :- opaque_atom(X).

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
part_in(W, part(X, cons(C)), N) :- opened(X, C), atom_constraint(X, C), crank(W, C, N).
part_in(W, I, N) :- world(W), u_atom(X), part_of(X, I), holds(I, V), V != u, rank(V, N).
part_in(W, part(X, target), 1) :- world(W), u_atom(X), holds(part(X, target), u).
part_in(W, part(X, party(F)), 1) :- world(W), u_atom(X), atom_party(X, F, _),
    holds(part(X, party(F)), u).

%*! pre_in(W, X, N)

In world `W`, the parts of the `u` atom `X` have Kleene conjunction of rank `N`. Rank 1 means
that an opaque part leaves the finding `u`.
*%
pre_in(W, X, N) :- world(W), u_atom(X), N = #min { M, I : part_of(X, I), part_in(W, I, M) }.

%*! completed(W, I, V)

In world `W`, the item `I`, which is `applies(X)`, has value `V`, `t` or `f`. An atom that is not
`u` keeps its finding. A `u` atom takes the conjunction of its parts in the world, and when that is
`u`, the value of its variable `fin(X)`.
*%
completed(W, applies(X), V) :- world(W), holds(applies(X), V), V != u.
completed(W, applies(X), V) :- pre_in(W, X, N), N != 1, rank(V, N).
completed(W, applies(X), V) :- pre_in(W, X, 1), assigned(W, fin(X), V).

%*! completed_item(I)

`I` has a completed value in every world: `applies(X)` for each atom. The constraint is in
integrity.lp.
*%
completed_item(applies(X)) :- atom(X).
