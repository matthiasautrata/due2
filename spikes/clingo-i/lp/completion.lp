%# completion.lp: the completion variables, and one completion of them
%
% Each `u` part of a `u` finding is completed or opaque (due2-workflows.md §6.4, decisions/0016).
% The findings completed are the ones resolve.lp reads: an atom's `applies`, and a precondition's
% `owed` and `fulfilled` (*Findings*). A `u` leaf whose operand reads an `unresolved` state
% property is completed: it reads a variable keyed by the comparison it makes, so a leaf and its
% complement read one variable with opposite polarities (decisions/0012), and a guard leaf and a
% rule leaf on one comparison read one variable. Every other `u` part is opaque: a `u` target or
% party part (an absent request field is `missing`), and a `u` leaf whose status is `missing`,
% `invalid`, `conflict`, or `misfit`. An opaque part stays `u` in every completion, and when it
% leaves the finding `u`, the finding's own variable `fin(I)` completes it. A `u` `fulfilled` is
% one variable of its own, `ful(Y, P)`, independent of every other as `fin(I)` is. A `u` part of an
% `f` finding reads none: the finding is `f` in every completion. One answer set gives every
% variable `t` or `f`, so the answer sets of solve 2 are the completions, `2^n` of them for `n`
% variables. Under each completion, the open nodes of every tree are re-evaluated under strong
% Kleene logic, and every `u` finding is re-derived. Every completed value is indexed by a world,
% so that pivot.lp can hold a second completion beside the first. Variable letters:
% DESIGN.md § Vocabulary.
%
% Every finding is an entry's (applies.lp, duty.lp), so every finding, open node, and opaque
% variable here carries the entry's policy `P`. A paired leaf's key carries `P` only when the leaf
% compares under a hierarchy (`hier_leaf/1`), so a leaf that two policies share reads one variable
% unless their hierarchies may order its value differently (due2-workflows.md §6.4,
% decisions/0050 #9).
%
% - **Consumes:** `operator/2` (lift.lp); `atom/1`, `atom_party/3` (structure.lp);
%   `scope/2`, `member/2`, `leaf/1`, `op/2`, `right/2`, `unit/2` (constraint.lp); `left/2`,
%   `src/2`, `prop/2` (bind.lp); `has_scheme/1`, `read_ok/3`, `read_status/4`,
%   `unchecked_unit/1` (operand.lp); `crank/4`, `evaluates/3` (compare.lp); `holds/2`, `part_of/3`,
%   `atom_constraint/2` (applies.lp); `rank/2` (kleene.lp); `pre/2` (structure.lp);
%   `guard/2`, `obligation_policy/2`, `instance/2` (duty.lp); `space/2` (structure.lp).
% - **Provides:** `duty_item/1`, `completed_item/1`, `u_item/1`, `item_space/2`, `item_root/2`,
%   `finding_atom/2`, `leaf_status/3`, `opaque_leaf/2`, `opened/2`, `open/2`, `opaque_item/1`,
%   `complement/2`, `op_literal/3`, `leaf_key/6`, `leaf_attr/3`, `hier_leaf/1`, `attr_apart/4`,
%   `same_key/4`, `leaf_lit/4`, `var/1`, `reads/2`, `world/1`, `assigned/3`, `part_in/3`,
%   `root_in/4`, `pre_in/3`, `completed/3`; extends `crank/4` and `evaluates/3` (compare.lp).

%## Findings

% A finding is completed only when resolve.lp reads it in a world: a rule's `applies`, and a
% precondition's `owed` and `fulfilled`, which can close a permission or leave it waiting on a duty.
% An obligation's findings move no verdict and no basis, since a violated root obligation is
% reported and never denies (decisions/0045, due2-workflows.md §6.1). explain.lp reports its row
% from the findings before completion, in world `k`. So an obligation's `in_force`, and the
% `fulfilled` of a duty that is an obligation and no precondition, are not completed and have no
% variable of their own: one would count toward the variable cap of interpret.py, double the
% completions, and change no answer (`test_obligation_findings_have_no_variable_of_their_own`). A
% duty entry that is both keeps its `fulfilled` variable as a precondition. A guard of `in_force` is
% still opened and keyed (`opened/2`), so a guard leaf that makes a completed leaf's comparison
% reads its variable (`reads/2`). An obligation is named `unknown` when that variable is pivotal,
% since its `u` part reads it (due2-workflows.md §6.4, decisions/0011 #1;
% `test_obligation_reads_a_shared_variable`).
%
% Each completed duty finding is completed according to where its `u` comes from:
%
% - **Guards.** A duty's `odrl:constraint` is a `top_constraint/2` of the duty node (duty.lp), so a
%   guard is a tree in scope `rule` (`scope/2`, constraint.lp), completed node by node as an atom's
%   constraint is. A guard leaf that makes a rule leaf's comparison reads the rule leaf's variable:
%   where the rule's constraint holds, so does the guard
%   (`test_guard_and_rule_leaf_share_a_variable`).
% - **Fulfilment.** A `u` `fulfilled(Y, P)` is not re-derived, because nothing that makes it `u`
%   is paired. A witness leaf (`witness_leaf/1`, duty.lp) reads the evidence in `wit(E)`, through a
%   `witness` operand or a context built-in such as `due2:actionTime`, and only a `state` read has
%   status `unresolved` (`read_status/4`, operand.lp). The actor check is `u` only on an absent
%   subject, which is opaque. So `fulfilled(Y, P)` shares no variable with any other finding, and
%   `ful(Y, P)` completes it soundly: the completions remain a superset of the realisable ones
%   (*Correlations the completion misses*).

%*! duty_item(I)

`I` is a duty finding of an entry: `owed(Y, P)`, `in_force(Y, P)`, or `fulfilled(Y, P)`.
duty.lp derives each, and explain.lp reports each.
*%
duty_item(owed(Y, P)) :- pre(X, Y), space(X, P).
duty_item(in_force(Y, P)) :- obligation_policy(Y, P).
duty_item(fulfilled(Y, P)) :- instance(Y, P).

%*! completed_item(I)

`I` has a completed value in every world: `applies(X, P)` for each entry of an atom, and
`owed(Y, P)` and `fulfilled(Y, P)` for each entry of a precondition. The check is in
integrity.lp.
*%
completed_item(applies(X, P)) :- atom(X), space(X, P).
completed_item(owed(Y, P)) :- duty_item(owed(Y, P)).
% A precondition whose `owed` is `f` has no instance (duty.lp), so no `fulfilled` to complete.
completed_item(fulfilled(Y, P)) :- duty_item(owed(Y, P)), duty_item(fulfilled(Y, P)).

%*! u_item(I)

Finding `I` is `u`: `applies(X, P)` of an entry, or a duty finding. Completion decides it when it
is a `completed_item/1`; an `in_force` only reads the variables it shares.
*%
u_item(applies(X, P)) :- holds(applies(X, P), u).
u_item(I) :- duty_item(I), holds(I, u).

%*! item_space(I, P)

Finding `I` is read in policy `P`'s data space: `P` is the policy of its entry.
*%
item_space(applies(X, P), P) :- completed_item(applies(X, P)).
item_space(owed(Y, P), P) :- duty_item(owed(Y, P)).
item_space(in_force(Y, P), P) :- duty_item(in_force(Y, P)).
item_space(fulfilled(Y, P), P) :- duty_item(fulfilled(Y, P)).

%*! item_root(I, C)

Constraint node `C` is a root of a tree that finding `I` conjoins: a constraint of the atom for
`applies(X, P)`, and a guard of the duty for `owed(Y, P)` and `in_force(Y, P)`. A `fulfilled`
finding has none: it is one variable of its own.
*%
item_root(applies(X, P), C) :- atom_constraint(X, C), space(X, P).
item_root(owed(Y, P), C) :- duty_item(owed(Y, P)), guard(Y, C).
item_root(in_force(Y, P), C) :- duty_item(in_force(Y, P)), guard(Y, C).

%*! finding_atom(I, X)

Finding `I` is a finding of an entry of the atom or duty atom `X`. pivot.lp names `X` as unknown,
since the reply names atoms by their source rule or duty, not entries.
*%
finding_atom(applies(X, P), X) :- completed_item(applies(X, P)).
finding_atom(owed(Y, P), Y) :- duty_item(owed(Y, P)).
finding_atom(in_force(Y, P), Y) :- duty_item(in_force(Y, P)).
finding_atom(fulfilled(Y, P), Y) :- duty_item(fulfilled(Y, P)).

%## Statuses

% Only an `unresolved` leaf is paired. An unresolved value exists and fits its operator, so of a
% leaf and its complement exactly one holds, and pairing them is sound. A missing, invalid,
% conflicting, or misfit value gives no such guarantee: for `"abc"`, neither `lt 5` nor `gteq 5`
% holds (decisions/0016, § Question).

%*! leaf_status(C, P, S)

Leaf `C` is `u` in world `k`, in policy `P`'s data space, with status `S`: its operand's read
status there, or `misfit` when the read is `ok` but a value does not fit the operator, or when
the leaf states a unit that its binding does not declare, whatever the read. The first misfit is
due2-workflows.md §5.4 step 3, the second step 1 (decisions/0049 #3). Every `u` leaf has exactly
one status in each of its data spaces (integrity.lp).
*%
leaf_status(C, P, S) :- evaluates(k, C, P), leaf(C), left(C, Op), read_status(k, Op, P, S),
    not unchecked_unit(C).
leaf_status(C, P, misfit) :- evaluates(k, C, P), unchecked_unit(C).
% A leaf whose read is ok has rank 1 only when some comparison is a misfit (compare.lp).
leaf_status(C, P, misfit) :- evaluates(k, C, P), leaf(C), left(C, Op), read_ok(k, Op, P),
    crank(k, C, P, 1).

%*! opaque_leaf(C, P)

Leaf `C` is `u` in policy `P`'s data space for a reason other than an `unresolved` value, so it
is never paired there.
*%
opaque_leaf(C, P) :- leaf_status(C, P, S), S != unresolved.

%## Open nodes

% A connective above an opaque part is re-evaluated under strong Kleene logic, so the tree, and the
% finding's conjunction, can stay `u` in the world. Then `fin(I)` decides the finding. When the
% paired leaves settle the tree anyway, `fin(I)` is read but moves nothing: a `t` member of an `or`
% makes it `t`, and an `f` conjunct makes the atom `f`. An opaque part therefore shares a variable
% with no other part, its complement included, as decisions/0016 #2 asks. Two atoms on one absent
% target are completed separately, and so are a leaf on a missing operand and its complement, and
% two entries of one atom.

%*! opened(I, C)

Constraint node `C` is `u` in the data space of the `u` finding `I`, and lies on a path of `u`
nodes from a root of `I` (`item_root/2`). Only these nodes can read a variable: a node that is
`t` or `f` keeps that value in every completion, because strong Kleene logic never turns `t` or
`f` into the other when a `u` is replaced by `t` or `f`.
*%
opened(I, C) :- u_item(I), item_root(I, C), item_space(I, P), holds(c(C, P), u).
opened(I, D) :- opened(I, C), member(C, D), item_space(I, P), holds(c(D, P), u).

%*! open(C, P)

Node `C` is opened for a completed finding read in policy `P`'s data space, so each completion
world evaluates it there (`evaluates/3`) and gives it a rank (`crank/4`). A node opened only for
an `in_force` is keyed but not evaluated: nothing reads its rank in a world.
*%
open(C, P) :- opened(I, C), completed_item(I), item_space(I, P).

%*! opaque_item(I)

The `u` finding `I` has an opaque part, so it can stay `u` in a world and has its own variable
`fin(I)`. For an entry of an atom the part is a `u` target or party part; for it or an `owed`, an
opaque leaf in an opened tree. An `in_force` has no `fin`: it is not completed.
*%
opaque_item(applies(X, P)) :- u_item(applies(X, P)), holds(part(X, P, target), u).
opaque_item(applies(X, P)) :- u_item(applies(X, P)), atom_party(X, F, _),
    holds(part(X, P, party(F)), u).
opaque_item(I) :- opened(I, C), completed_item(I), item_space(I, P), opaque_leaf(C, P).

%## Paired variables

% Two opened paired leaves read one variable when they make the same comparison (due2-workflows.md
% §6.4). The key has seven components:
%
% | Component | Relation | Note |
% |---|---|---|
% | scope | `scope/2` (constraint.lp) | `rule` or `action` |
% | binding | `src/2`, `prop/2` (bind.lp) | where the operand reads, not its IRI: two operands bound to one property read one value |
% | positive operator | `op_literal(O, Base, Pol)` | a complement asserts its `Base`, `neg` |
% | right operand values | `leaf_attr(C, P, right(Term))` | a set of terms |
% | units | `leaf_attr(C, P, unit(Iri))` | a set |
% | concept | `leaf_attr(C, P, concept)` | whether the operand has a concept scheme: with one, `eq` is ⊑, and without, identity |
% | policy | `leaf_attr(C, P, policy(P))` | for a leaf that compares under a hierarchy (`hier_leaf/1`), the policy whose data space reads it |
%
% A key belongs to a leaf read in one data space, `(C, P)`. `leaf_key/6` holds the first three
% components, and `leaf_attr/3` the sets. Only the last component names `P`, so one leaf read in
% two data spaces has one key there unless it compares under a hierarchy. A node reached from
% both a rule's constraint and an action's refinement has two scopes, and so two keys for one value.
% It declines as `constraint: node in two scopes`.

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

%*! leaf_key(C, P, Scope, Src, Prop, Base)

The `unresolved` leaf `C`, opened in policy `P`'s data space, has the scalar part of its
completion key: its scope, the source and property its left operand is bound to (not the operand
IRI, which two layers may bind to one property), and its positive operator.
*%
leaf_key(C, P, Scope, Src, Prop, Base) :- opened(I, C), item_space(I, P),
    leaf_status(C, P, unresolved), scope(C, Scope), left(C, Op), src(Op, Src), prop(Op, Prop),
    op(C, O), op_literal(O, Base, _).

%*! leaf_attr(C, P, Attr)

The `unresolved` leaf `C`, opened in policy `P`'s data space, has `Attr` in the set part of its
key: `right(Term)` for each right operand value, `unit(Iri)` for each unit, `concept` when its
left operand has a concept scheme, and `policy(P)` when it compares under a hierarchy. Two
operands bound to one property, one with a scheme and one without, read `eq` as ⊑ and as
identity, so their `eq` and `neq` are not complements (due2-workflows.md §6.4).
*%
leaf_attr(C, P, right(Term)) :- leaf_key(C, P, _, _, _, _), right(C, Term).
leaf_attr(C, P, unit(Iri)) :- leaf_key(C, P, _, _, _, _), unit(C, Iri).
leaf_attr(C, P, concept) :- leaf_key(C, P, _, _, _, _), left(C, Op), has_scheme(Op).
leaf_attr(C, P, policy(P)) :- leaf_key(C, P, _, _, _, _), hier_leaf(C).

%*! hier_leaf(C)

Leaf `C` compares under a hierarchy: its operator is `isA`, `isPartOf`, or `hasPart`, or its left
operand has a concept scheme. Its completion key includes the policy whose data space reads it,
because one value can be below a right operand in one policy's hierarchy and not in another's
(due2-workflows.md §6.4, decisions/0050 #9).
*%
hier_leaf(C) :- leaf(C), op(C, (isA; isPartOf; hasPart)).
hier_leaf(C) :- leaf(C), left(C, Op), has_scheme(Op).

%*! attr_apart(C, P, D, Q)

The keyed leaves `(C, P)` and `(D, Q)` have the same scalar key, and `(C, P)` has an attribute
`(D, Q)` lacks.
*%
attr_apart(C, P, D, Q) :- leaf_key(C, P, Scope, Src, Prop, Base),
    leaf_key(D, Q, Scope, Src, Prop, Base), leaf_attr(C, P, Attr), not leaf_attr(D, Q, Attr).

%*! same_key(C, P, D, Q)

The keyed leaves `(C, P)` and `(D, Q)` have the same completion key: the same scalar key, and the
same attribute set. The relation is reflexive, symmetric, and transitive.
*%
same_key(C, P, D, Q) :- leaf_key(C, P, Scope, Src, Prop, Base),
    leaf_key(D, Q, Scope, Src, Prop, Base), not attr_apart(C, P, D, Q), not attr_apart(D, Q, C, P).

%*! leaf_lit(C, P, L, Pol)

The `unresolved` leaf `C`, opened in policy `P`'s data space, reads the variable `L` with
polarity `Pol`. `L` is `cons((D, Q))`, with `(D, Q)` the least keyed leaf of `(C, P)`'s key
class, so keyed leaves with the same key read one variable. Right operand values are compared as
terms, so `5` and `5.0` give two variables. That loses precision, never soundness
(due2-workflows.md §6.4, "parts that are not the same expression").
*%
% `#min` over pairs orders them lexicographically, so the least pair is one keyed leaf of the
% class, not a mix of two.
leaf_lit(C, P, cons(M), Pol) :- leaf_key(C, P, _, _, _, _), op(C, O), op_literal(O, _, Pol),
    M = #min { (D, Q) : same_key(C, P, D, Q) }.

%## The completion

%*! var(L)

`L` is a completion variable: `cons((D, Q))` for a key class of paired leaves with an open
member, `fin(I)` for the opaque finding `I`, or `ful(Y, P)` for a completed `u`
`fulfilled(Y, P)`. interpret.py counts the `var/1` atoms of the first answer set, the same in
every answer set, and declines the vector above the variable cap (correctness-strategy.md §3).
*%
var(L) :- leaf_lit(C, P, L, _), open(C, P).
var(fin(I)) :- opaque_item(I).
var(ful(Y, P)) :- u_item(fulfilled(Y, P)), completed_item(fulfilled(Y, P)).
% Shown so that interpret.py can count them: in cautious and brave mode a model reports only
% shown atoms, and grounding leaves `var/1` atoms that no model makes true.
#show var/1.

%*! reads(I, L)

The `u` finding `I` reads the variable `L`: through a paired leaf of an opened tree, its own
`fin(I)`, or, for `fulfilled(Y, P)`, `ful(Y, P)`. pivot.lp names `I`'s atom when `L` is pivotal.
*%
reads(I, L) :- opened(I, C), item_space(I, P), leaf_lit(C, P, L, _), var(L).
reads(I, fin(I)) :- opaque_item(I).
reads(fulfilled(Y, P), ful(Y, P)) :- u_item(fulfilled(Y, P)), completed_item(fulfilled(Y, P)).

%*! world(W)

`W` is a completion world: an index for one completion held in the answer set. World `c`
(for "completion") is the completion the answer set chose; pivot.lp adds `flip`. The Kleene
world `k` of `crank/4` is not one: it holds no completion.
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
evaluates(W, C, P) :- world(W), open(C, P).
crank(W, D, P, N) :- world(W), open(C, P), member(C, D), not open(D, P), crank(k, D, P, N).
crank(W, C, P, 1) :- world(W), open(C, P), opaque_leaf(C, P).
crank(W, C, P, N) :- open(C, P), leaf_lit(C, P, L, pos), assigned(W, L, V), rank(V, N).
crank(W, C, P, 2 - N) :- open(C, P), leaf_lit(C, P, L, neg), assigned(W, L, V), rank(V, N).

%*! part_in(W, I, N)

In world `W`, the part `I` of a `u` entry of an atom has rank `N`. A constraint part whose root is
open takes its root's rank in the world. A `u` target or party part is opaque and keeps rank 1.
Every other part keeps its rank.
*%
part_in(W, part(X, P, cons(C)), N) :- opened(applies(X, P), C), atom_constraint(X, C),
    crank(W, C, P, N).
part_in(W, I, N) :- world(W), u_item(applies(X, P)), part_of(X, P, I), holds(I, V), V != u,
    rank(V, N).
part_in(W, part(X, P, target), 1) :- world(W), u_item(applies(X, P)),
    holds(part(X, P, target), u).
part_in(W, part(X, P, party(F)), 1) :- world(W), u_item(applies(X, P)), atom_party(X, F, _),
    holds(part(X, P, party(F)), u).

%*! root_in(W, I, C, N)

In world `W`, the guard `C` of the completed `u` duty finding `I` has rank `N`: its rank in the
world when it is open, and its rank in world `k` otherwise.
*%
root_in(W, I, C, N) :- opened(I, C), item_root(I, C), duty_item(I), item_space(I, P),
    crank(W, C, P, N).
root_in(W, I, C, N) :- world(W), u_item(I), duty_item(I), completed_item(I), item_root(I, C),
    item_space(I, P), holds(c(C, P), V), V != u, rank(V, N).

%*! pre_in(W, I, N)

In world `W`, the parts of the `u` finding `I` have Kleene conjunction of rank `N`. The parts
are an atom's parts, and the guards of `owed`, as applies.lp and duty.lp conjoin them in world
`k`. Rank 1 means that an opaque part leaves the finding `u`. A `u` `fulfilled` has no `pre_in`:
its variable `ful(Y, P)` decides it.
*%
pre_in(W, applies(X, P), N) :- world(W), u_item(applies(X, P)),
    N = #min { M, I : part_of(X, P, I), part_in(W, I, M) }.
% A `u` `owed` has a `u` guard, so the set is never empty.
pre_in(W, owed(Y, P), N) :- world(W), u_item(owed(Y, P)),
    N = #min { M, C : root_in(W, owed(Y, P), C, M) }.

%*! completed(W, I, V)

In world `W`, the finding `I` has value `V`, `t` or `f`. A finding that is not `u` keeps its
value. A `u` `applies` or `owed` takes the conjunction of its parts in the world, and when that
is `u`, the value of its variable `fin(I)`. A `u` `fulfilled(Y, P)` takes the value of
`ful(Y, P)`.
*%
completed(W, I, V) :- world(W), completed_item(I), holds(I, V), V != u.
completed(W, I, V) :- pre_in(W, I, N), N != 1, rank(V, N).
completed(W, I, V) :- pre_in(W, I, 1), assigned(W, fin(I), V).
completed(W, fulfilled(Y, P), V) :- u_item(fulfilled(Y, P)), assigned(W, ful(Y, P), V).

%## Worked example

% This is the first row of `test_completion_key`, copied from a run. Under `perm`, permission
% `ex:r1` has the leaf `c1`, `ex:x eq 5`, and permission `ex:r2` the leaf `c2`, `ex:x neq 5`. `ex:x`
% reads the state, which has no fact for it, so it is `unresolved`. Both leaves are `u` and paired,
% so both findings are `u`, and both leaves are open. They share a key: scope `rule`, the state
% property `ex:x`, base `eq`, right operand `{5}`, no unit, and no policy, since `eq` on an operand
% with no scheme reads no hierarchy. In the run, `c1` is the lesser label, so
% `leaf_lit(c1, P, cons((c1, P)), pos)` and `leaf_lit(c2, P, cons((c1, P)), neg)` hold, with `P`
% the one policy: one variable, two completions.
%
% | `cons((c1, P))` | `c1` | `c2` | applies | verdict |
% |---|---|---|---|---|
% | `t` | 2 | 0 | `ex:r1` | `Permit` |
% | `f` | 0 | 2 | `ex:r2` | `Permit` |
%
% The verdict is `Permit` in both, so the reply is a definite `Permit`, although both findings are
% `u`. Its basis is empty, because neither permission applies in both completions (resolve.lp, *The
% cautious basis*). With one variable per leaf, some completion would make both leaves rank 0 and
% give `NotApplicable`, and the reply would be `Indeterminate`: the precision the key buys. With
% `ex:x` missing instead, the leaves are opaque, each atom is decided by its own `fin` variable, and
% the reply is that `Indeterminate`, `NotApplicable` to `Permit`. `test_opaque_is_not_paired` pins
% the same contrast on `lt` and `gteq`.

%## Correlations the completion misses

% The completion is domain-unaware: it does not know which variables exclude or imply each other
% (domain-aware completion is due2-workflows.md §9 open decision 6). It misses three kinds of
% correlation:
%
% - values: `ex:x eq 5` and `ex:x eq 6` are separate variables (decisions/0012 #3), and the
%   completion that makes both `t` is enumerated, though `ex:x` is single-valued and no state
%   realises it;
% - hierarchies: with `ex:a1 odrl:partOf ex:a`, a value `ex:a1` would make both `ex:x isPartOf
%   ex:a1` and `ex:x isPartOf ex:a` `t`;
% - comparisons on one value: `ex:x lt 3` implies `ex:x lt 5`, and `5` equals `5.0`, yet each is its
%   own variable.
%
% Opaque findings miss correlations too: their `fin(I)` and `ful(Y, P)` are independent of every
% other variable by construction. One absent subject, for example, would make a rule's party part
% and a duty's actor check `t` together, and the completions also hold the corners where they
% differ. In every case the variables stay independent, so the completions are a superset of the
% realisable ones, and:
%
% - a definite verdict holds in every completion, so it holds in every realisable one, and it is
%   sound;
% - an `Indeterminate` may be reported where every realisable completion agrees, so precision, not
%   soundness, is what is lost;
% - a range covers every realisable verdict, and may be wider.
