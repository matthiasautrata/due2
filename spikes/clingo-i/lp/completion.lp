%# completion.lp: the completion variables, and one completion of them
%
% Each `u` part of a `u` atom reads completion variables. A target or a party part reads one
% variable, keyed by the field it tests. A constraint part reads the variables of the `u`
% leaves of its tree, each keyed by the comparison it makes (due2-workflows.md §6.4). A `u`
% part of an `f` atom reads none: the atom is `f` in every completion. One answer set gives
% every variable `t` or `f`, so solve 2's answer sets are exactly the completions, `2^n` of
% them for `n` variables (decisions/0012). Under each completion, the open nodes of every tree
% are re-evaluated two-valued, and every `u` part and finding is re-derived. Every completed
% value is indexed by a world, so that pivot.lp can hold a second completion beside the first.
% Variable letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `operator/2` (lift.lp); `atom/1`, `atom_target/2`, `atom_party/3`
%   (structure.lp); `scope/2`, `conn/2`, `member/2`, `leaf/1`, `left/2`, `op/2`, `right/2`,
%   `unit/2` (constraint.lp); `src/2`, `prop/2` (operand.lp); `crank/2` (compare.lp);
%   `holds/2`, `part_of/2`, `atom_constraint/2` (applies.lp); `rank/2` (kleene.lp).
% - **Provides:** `u_atom/1`, `lit_of/2`, `opened/2`, `open/1`, `complement/2`, `op_literal/3`,
%   `leaf_key/5`, `leaf_attr/2`, `attr_apart/2`, `same_key/2`, `leaf_lit/3`, `var/1`,
%   `reads/2`, `world/1`, `assigned/3`, `crank_in/3`, `completed/3`, `completed_item/1`.

%*! u_atom(X)

Atom `X`'s finding is `u`, so completion decides it.
*%
u_atom(X) :- holds(applies(X), u).

%## Target and party variables

%*! lit_of(I, L)

The `u` target or party part `I` of a `u` atom reads the variable `L`: `target(T)` for a target
part, the atom's target, and `party(F, Party)` for a party part, its function and party. Parts
with the same variable test the same request field against the same value (decisions/0012
#1). Different values of one field, `target(a)` and `target(b)`, are different variables
(decisions/0012 #3). Each of these parts reads its variable positively.
*%
lit_of(part(X, target), target(T)) :- u_atom(X), atom_target(X, T), holds(part(X, target), u).
lit_of(part(X, party(F)), party(F, Party)) :- u_atom(X), atom_party(X, F, Party),
    holds(part(X, party(F)), u).

%## Constraint variables

%*! opened(X, C)

Constraint node `C` is `u`, and lies on a path of `u` nodes from a constraint root of the `u`
atom `X`. Only these nodes are completed: a node that is `t` or `f` keeps that value in every
completion, because strong Kleene logic never turns `t` or `f` into the other when a `u` is
replaced by `t` or `f`.
*%
opened(X, C) :- u_atom(X), atom_constraint(X, C), holds(c(C), u).
opened(X, D) :- opened(X, C), member(C, D), holds(c(D), u).

%*! open(C)

Node `C` is opened for some atom, so each world gives it a two-valued rank (`crank_in/3`).
*%
open(C) :- opened(_, C).

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

The open leaf `C` has the scalar part of its completion key: its scope, the source and
property its left operand is bound to (not the operand IRI, which two layers may bind to one
property), and its positive operator.
*%
leaf_key(C, Scope, Src, Prop, Base) :- open(C), leaf(C), scope(C, Scope), left(C, Op),
    src(Op, Src), prop(Op, Prop), op(C, O), op_literal(O, Base, _).

%*! leaf_attr(C, Attr)

The open leaf `C` has `Attr` in the set part of its key: `right(Term)` for each right operand
value, and `unit(Iri)` for each unit.
*%
leaf_attr(C, right(Term)) :- open(C), right(C, Term).
leaf_attr(C, unit(Iri)) :- open(C), unit(C, Iri).

%*! attr_apart(C, D)

The open leaves `C` and `D` have the same scalar key, and `C` has an attribute `D` lacks.
*%
attr_apart(C, D) :- leaf_key(C, Scope, Src, Prop, Base), leaf_key(D, Scope, Src, Prop, Base),
    leaf_attr(C, Attr), not leaf_attr(D, Attr).

%*! same_key(C, D)

The open leaves `C` and `D` have the same completion key: the same scalar key, and the same
attribute set. The relation is reflexive, symmetric, and transitive.
*%
same_key(C, D) :- leaf_key(C, Scope, Src, Prop, Base), leaf_key(D, Scope, Src, Prop, Base),
    not attr_apart(C, D), not attr_apart(D, C).

%*! leaf_lit(C, L, Pol)

The open leaf `C` reads the variable `L` with polarity `Pol`. `L` is `cons(D)`, with `D` the
least leaf of `C`'s key class, so leaves with the same key read one variable. Right operand
values are compared as terms, so `5` and `5.0` give two variables. That loses precision, never
soundness (due2-workflows.md §6.4, "parts that are not the same expression").
*%
leaf_lit(C, cons(D), Pol) :- leaf_key(C, _, _, _, _), op(C, O), op_literal(O, _, Pol),
    D = #min { D2 : same_key(C, D2) }.

%## The completion

%*! var(L)

`L` is a completion variable. interpret.py counts the `var/1` atoms of the first answer set, the
same in every answer set, and declines the vector above the variable cap
(correctness-strategy.md §3).
*%
var(L) :- lit_of(_, L).
var(L) :- leaf_lit(_, L, _).
% Shown so that interpret.py can count them: in cautious and brave mode a model reports only
% shown atoms, and grounding leaves `var/1` atoms that no model makes true.
#show var/1.

%*! reads(X, L)

The `u` atom `X` reads the variable `L` in one of its `u` parts. pivot.lp names `X` when `L` is
pivotal.
*%
reads(X, L) :- u_atom(X), part_of(X, I), lit_of(I, L).
reads(X, L) :- opened(X, C), leaf_lit(C, L, _).

%*! world(W)

`W` is a world: an index for one completion held in the answer set. World `c` (for
"completion") is the completion the answer set chose; pivot.lp adds `flip`.
*%
world(c).

%*! assigned(W, L, V)

In world `W`, variable `L` has value `V`, `t` or `f`.
*%
% The choice: exactly one value for each variable in world c.
{ assigned(c, L, t); assigned(c, L, f) } = 1 :- var(L).

%*! crank_in(W, C, N)

In world `W`, the open node `C`, or a member of an open node, has rank `N`, 0 or 2. A member
that is not open keeps its rank. An open leaf takes its variable's value, negated for
polarity `neg`. An open connective is re-evaluated from its members: within a world every
rank is 0 or 2, so these are the two-valued connectives.
*%
crank_in(W, D, N) :- world(W), open(C), member(C, D), not open(D), crank(D, N).
crank_in(W, C, N) :- leaf_lit(C, L, pos), assigned(W, L, V), rank(V, N).
crank_in(W, C, 2 - N) :- leaf_lit(C, L, neg), assigned(W, L, V), rank(V, N).
% The connective rules of compare.lp, over one world's ranks. `xone` is "exactly one member is
% t", which its expansion equals when no member is u.
crank_in(W, C, N) :- world(W), open(C), conn(C, and),
    N = #min { 2; M, D : member(C, D), crank_in(W, D, M) }.
crank_in(W, C, N) :- world(W), open(C), conn(C, or),
    N = #max { 0; M, D : member(C, D), crank_in(W, D, M) }.
crank_in(W, C, 2 - N) :- open(C), conn(C, negation), member(C, D), crank_in(W, D, N).
crank_in(W, C, 2) :- world(W), open(C), conn(C, xone),
    #count { D : member(C, D), crank_in(W, D, 2) } = 1.
crank_in(W, C, 0) :- world(W), open(C), conn(C, xone),
    #count { D : member(C, D), crank_in(W, D, 2) } != 1.

%*! completed(W, I, V)

In world `W`, item `I` has value `V`, `t` or `f`. An atom that is not `u` keeps its finding.
For a `u` atom, a `u` target or party part takes its variable's value, a `u` constraint part
its root's rank in the world, every other part keeps its finding, and `applies(X)` is the
Kleene conjunction of the completed parts.
*%
completed(W, applies(X), V) :- world(W), holds(applies(X), V), V != u.
completed(W, I, V) :- world(W), lit_of(I, L), assigned(W, L, V).
completed(W, part(X, cons(C)), V) :- opened(X, C), atom_constraint(X, C), crank_in(W, C, N),
    rank(V, N).
completed(W, I, V) :- world(W), u_atom(X), part_of(X, I), holds(I, V), V != u.
% The #min-as-function idiom of applies.lp, over the completed parts.
completed(W, applies(X), V) :- world(W), u_atom(X), rank(V, Min),
    Min = #min { N : part_of(X, I), completed(W, I, Vp), rank(Vp, N) }.

%*! completed_item(I)

`I` has a completed value in every world: each atom's finding, and each part of a `u` atom.
The constraint is in integrity.lp.
*%
completed_item(applies(X)) :- atom(X).
completed_item(I) :- u_atom(X), part_of(X, I).
