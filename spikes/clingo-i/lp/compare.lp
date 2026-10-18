%# compare.lp: the operators, and the Kleene value of every constraint node
%
% Compares each value a leaf's operand reads with each of its right operand values, by value
% within a value space or, on an operand with a concept scheme, under `skos:broader`, and
% combines the comparisons by the operator's definition (due2-profiles.md §4). A comparison the
% operands do not fit, such as an IRI against a literal or values of two spaces, is `u` (rank
% 1), never `f`. Then the connectives combine their members' values: `and` is the least rank,
% `or` the greatest, `dprod:not` the involution, and `xone` the value of its expansion
% (DESIGN.md § `compare.lp`). The connective rules serve every world: the Kleene world `k`,
% before completion, and the completion worlds of completion.lp. Ranks are those of kleene.lp.
% Variable letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `kind/2`, `dt_kind/2`, `closure/3`, `le_k/3` (lift.lp); `value/3` (driver);
%   `rank/2` (kleene.lp); `cnode/1`, `conn/2`, `member/2`, `leaf/1`, `left/2`, `op/2`,
%   `right/2` (constraint.lp); `read_ok/1`, `read_u/1`, `read_value/2`, `has_scheme/1`
%   (operand.lp).
% - **Provides:** `cpair/3`, `pair/2`, `placed/1`, `same_type/2`, `eqr/3`, `concept_pair/3`,
%   `above/2`, `ceqr/4`, `ordered/1`,
%   `cmpr/3`, `order_rank/3`, `part_pair/2`, `ler/3`, `isa_left/1`, `inst/2`, `isar/3`,
%   `any_eq/3`, `any_le/3`, `crank/3`, `evaluates/2`, `xone_term/4`; extends `item/1`, `holds/2`
%   (applies.lp) and `unsupported_value/1` (lift.lp).

%## Pairs

%*! cpair(C, Lv, Rv)

Leaf `C` compares the read value `Lv` with the right operand value `Rv`. A `u` read gives no
pairs: the leaf is `u` whatever its values.
*%
cpair(C, Lv, Rv) :- left(C, Op), read_ok(Op), read_value(Op, Lv), right(C, Rv).

%*! pair(Lv, Rv)

Some leaf compares `Lv` with `Rv`. The comparisons below depend only on the two values.
*%
pair(Lv, Rv) :- cpair(_, Lv, Rv).

%*! placed(Term)

The literal `Term` has a position in a value space. DESIGN.md § Values describes the spaces.
*%
placed(Term) :- value(Term, _, _).

%*! same_type(Lv, Rv)

The unplaced literals `Lv` and `Rv` have the same datatype, and for `rdf:langString` the same
language tag, so they are compared by identity. That is due2-profiles.md §4's "strings by code
point".
*%
same_type(Lv, Rv) :- pair(Lv, Rv), Lv = lit(_, Dt), Rv = lit(_, Dt).
same_type(Lv, Rv) :- pair(Lv, Rv), Lv = lit(_, Dt, Tag), Rv = lit(_, Dt, Tag).

% Two unplaced literals of one kind but different datatypes, such as an `xsd:token` and an
% `xsd:string`: decisions/0014 #6 compares them by value, and the spike does not apply the
% whitespace facets that map a derived string to its value. Placed literals need no rule: each
% value space holds one kind (DESIGN.md § Values), and a position compares them by value.
unsupported_value("value: derived string datatypes") :- pair(Lv, Rv), not placed(Lv),
    not placed(Rv), Lv = lit(_, Dt), Rv = lit(_, Dt2), Dt != Dt2, dt_kind(Dt, K),
    dt_kind(Dt2, K).

%## Equality

%*! eqr(Lv, Rv, N)

`Lv = Rv` has rank `N`. IRIs by identity; placed literals by position in one space; unplaced
literals of one type by identity. Every other pair is a misfit: rank 1.
*%
eqr(Lv, Rv, 2) :- pair(Lv, Rv), kind(Lv, iri), kind(Rv, iri), Lv = Rv.
eqr(Lv, Rv, 0) :- pair(Lv, Rv), kind(Lv, iri), kind(Rv, iri), Lv != Rv.
eqr(Lv, Rv, 1) :- pair(Lv, Rv), kind(Lv, iri), kind(Rv, lit).
eqr(Lv, Rv, 1) :- pair(Lv, Rv), kind(Lv, lit), kind(Rv, iri).
eqr(Lv, Rv, 1) :- pair(Lv, Rv), kind(Lv, blank).
eqr(Lv, Rv, 1) :- pair(Lv, Rv), kind(Rv, blank), not kind(Lv, blank).
eqr(Lv, Rv, 2) :- pair(Lv, Rv), value(Lv, Space, N), value(Rv, Space, N).
eqr(Lv, Rv, 0) :- pair(Lv, Rv), value(Lv, Space, N), value(Rv, Space, M), N != M.
eqr(Lv, Rv, 1) :- pair(Lv, Rv), value(Lv, Space, _), value(Rv, Space2, _), Space != Space2.
eqr(Lv, Rv, 1) :- pair(Lv, Rv), placed(Lv), kind(Rv, lit), not placed(Rv).
eqr(Lv, Rv, 1) :- pair(Lv, Rv), placed(Rv), kind(Lv, lit), not placed(Lv).
eqr(Lv, Rv, 2) :- pair(Lv, Rv), kind(Lv, lit), not placed(Lv), kind(Rv, lit), not placed(Rv),
    Lv = Rv.
eqr(Lv, Rv, 0) :- pair(Lv, Rv), kind(Lv, lit), not placed(Lv), kind(Rv, lit), not placed(Rv),
    same_type(Lv, Rv), Lv != Rv.
eqr(Lv, Rv, 1) :- pair(Lv, Rv), kind(Lv, lit), not placed(Lv), kind(Rv, lit), not placed(Rv),
    not same_type(Lv, Rv).

%## Concepts

%*! concept_pair(C, Lv, Rv)

Leaf `C` compares the IRIs `Lv` and `Rv` as concepts: its left operand has a concept scheme.
Only IRIs are concepts, so a literal on either side is compared by `eqr/3` (decisions/0015 #7).
*%
concept_pair(C, Lv, Rv) :- cpair(C, Lv, Rv), left(C, Op), has_scheme(Op), kind(Lv, iri),
    kind(Rv, iri).

%*! above(Lv, Hi)

A chain of one or more `skos:broader` edges leads from the read concept `Lv` to `Hi`: the
transitive closure SKOS calls `skos:broaderTransitive` (decisions/0015 #5). Not reflexive:
`ceqr/4` adds identity.
*%
above(Lv, Hi) :- concept_pair(_, Lv, _), closure(broader, Lv, Hi).
above(Lv, Hi) :- above(Lv, Mid), closure(broader, Mid, Hi).

%*! ceqr(C, Lv, Rv, N)

In leaf `C`, `Lv = Rv` has rank `N`. For a concept pair it is `Lv ⊑ Rv`: `t` when `Lv` is `Rv` or
below it, `f` otherwise, closed-world over the declared edges (decisions/0015 #3, #4). A read
concept in none of the operand's schemes never gets here: its read is `invalid` (operand.lp).
Every other pair has its `eqr/3` rank.
*%
ceqr(C, Lv, Rv, 2) :- concept_pair(C, Lv, Rv), Lv = Rv.
ceqr(C, Lv, Rv, 2) :- concept_pair(C, Lv, Rv), above(Lv, Rv).
ceqr(C, Lv, Rv, 0) :- concept_pair(C, Lv, Rv), Lv != Rv, not above(Lv, Rv).
ceqr(C, Lv, Rv, N) :- cpair(C, Lv, Rv), not concept_pair(C, Lv, Rv), eqr(Lv, Rv, N).

%## Order

%*! ordered(Space)

Value space `Space` is totally ordered: numbers, instants, dates, and the two kinds of duration.
Booleans are placed but not ordered.
*%
ordered(numeric; instant; date; daytime; yearmonth).

%*! cmpr(Lv, Rv, Rel)

`Lv` is `lt`, `eq`, or `gt` than `Rv` within one ordered space, or `u`: the two have no order.
*%
cmpr(Lv, Rv, lt) :- pair(Lv, Rv), value(Lv, Space, N), value(Rv, Space, M), ordered(Space), N < M.
cmpr(Lv, Rv, eq) :- pair(Lv, Rv), value(Lv, Space, N), value(Rv, Space, N), ordered(Space).
cmpr(Lv, Rv, gt) :- pair(Lv, Rv), value(Lv, Space, N), value(Rv, Space, M), ordered(Space), N > M.
cmpr(Lv, Rv, u) :- pair(Lv, Rv), not cmpr(Lv, Rv, lt), not cmpr(Lv, Rv, eq), not cmpr(Lv, Rv, gt).

%*! order_rank(O, Rel, N)

The order operator `O` has rank `N` on relation `Rel`.
*%
order_rank(lt, lt, 2).   order_rank(lt, eq, 0).   order_rank(lt, gt, 0).
order_rank(lteq, lt, 2). order_rank(lteq, eq, 2). order_rank(lteq, gt, 0).
order_rank(gt, lt, 0).   order_rank(gt, eq, 0).   order_rank(gt, gt, 2).
order_rank(gteq, lt, 0). order_rank(gteq, eq, 2). order_rank(gteq, gt, 2).
order_rank(O, u, 1) :- order_rank(O, lt, _).

%## Hierarchies

%*! part_pair(Lo, Hi)

`isPartOf` or `hasPart` asks whether `Lo ⊑ Hi`, for a pair in either orientation.
*%
part_pair(Lv, Rv) :- cpair(C, Lv, Rv), op(C, isPartOf).
part_pair(Rv, Lv) :- cpair(C, Lv, Rv), op(C, hasPart).

%*! ler(Lo, Hi, N)

`Lo ⊑ Hi` has rank `N`: two IRIs are ordered by identity and the typed `partOf` closure, closed
over the declared edges; any other pair is a misfit. The closure is due2-profiles.md §6's.
*%
ler(Lo, Hi, 2) :- part_pair(Lo, Hi), kind(Lo, iri), kind(Hi, iri), Lo = Hi.
ler(Lo, Hi, 2) :- part_pair(Lo, Hi), kind(Lo, iri), kind(Hi, iri), le_k(Lo, Hi, _).
ler(Lo, Hi, 0) :- part_pair(Lo, Hi), kind(Lo, iri), kind(Hi, iri), Lo != Hi, not le_k(Lo, Hi, _).
ler(Lo, Hi, 1) :- part_pair(Lo, Hi), not kind(Lo, iri).
ler(Lo, Hi, 1) :- part_pair(Lo, Hi), kind(Lo, iri), not kind(Hi, iri).

%*! isa_left(Lv)

`isA` asks about the classes of the read value `Lv`.
*%
isa_left(Lv) :- cpair(C, Lv, _), op(C, isA).

%*! inst(Lv, Cls)

`Lv` is an instance of `Cls`: an `rdf:type` edge, then `rdfs:subClassOf` edges. That is the
reading of `isA` in due2-profiles.md §6.
*%
inst(Lv, Cls) :- isa_left(Lv), closure(type, Lv, Cls).
inst(Lv, Sup) :- inst(Lv, Cls), closure(subclass, Cls, Sup).

%*! isar(Lv, Cls, N)

`Lv` is an instance of `Cls` with rank `N`. Only an IRI is compared with a class.
*%
isar(Lv, Cls, 2) :- cpair(C, Lv, Cls), op(C, isA), kind(Lv, iri), kind(Cls, iri), inst(Lv, Cls).
isar(Lv, Cls, 0) :- cpair(C, Lv, Cls), op(C, isA), kind(Lv, iri), kind(Cls, iri), not inst(Lv, Cls).
isar(Lv, Cls, 1) :- cpair(C, Lv, Cls), op(C, isA), not kind(Lv, iri).
isar(Lv, Cls, 1) :- cpair(C, Lv, Cls), op(C, isA), kind(Lv, iri), not kind(Cls, iri).

%## The operators

%*! any_eq(C, Rv, N)

Some value leaf `C` reads equals its right value `Rv`, with rank `N`: the Kleene disjunction over
the read values, under `skos:broader` for concepts (`ceqr/4`).
*%
any_eq(C, Rv, N) :- right(C, Rv), left(C, Op), read_ok(Op),
    N = #max { 0; M, Lv : ceqr(C, Lv, Rv, M) }.

%*! any_le(C, Lo, N)

For `isPartOf`, the read value `Lo` is part of some right value; for `hasPart`, the right value
`Lo` is part of some read value. `N` is the rank of that Kleene disjunction.
*%
any_le(C, Lv, N) :- op(C, isPartOf), left(C, Op), read_value(Op, Lv), read_ok(Op),
    N = #max { 0; M, Rv : cpair(C, Lv, Rv), ler(Lv, Rv, M) }.
any_le(C, Rv, N) :- op(C, hasPart), right(C, Rv), left(C, Op), read_ok(Op),
    N = #max { 0; M, Lv : cpair(C, Lv, Rv), ler(Rv, Lv, M) }.

%*! crank(W, C, N)

In world `W`, node `C` has rank `N`. World `k` is the Kleene world: the ranks before
completion, under strong Kleene logic, which this file derives for every node. completion.lp
adds the ranks of the completion worlds `c` and `flip`. In world `k` a leaf whose read is `u`
has rank 1. Otherwise its operator decides
(due2-profiles.md §4): `eq` and the order operators compare the one read value with the one
right value; `isAnyOf` is the greatest `eq` over the right values, and `isNoneOf` its negation;
`isAllOf` is the least, over right values, of `any_eq`; `isPartOf` and `hasPart` are the least
of `any_le`, and an empty read set holds vacuously; `isA` is the least over the listed classes.
Each `eq`, on a concept-scheme operand, is `⊑` (`ceqr/4`).
*%
crank(k, C, 1) :- leaf(C), left(C, Op), read_u(Op).
crank(k, C, N) :- op(C, eq), ceqr(C, _, _, N).
crank(k, C, 2 - N) :- op(C, neq), ceqr(C, _, _, N).
crank(k, C, N) :- op(C, O), cpair(C, Lv, Rv), cmpr(Lv, Rv, Rel), order_rank(O, Rel, N).
crank(k, C, N) :- op(C, isAnyOf), left(C, Op), read_ok(Op),
    N = #max { 0; M, Rv : any_eq(C, Rv, M) }.
crank(k, C, 2 - N) :- op(C, isNoneOf), left(C, Op), read_ok(Op),
    N = #max { 0; M, Rv : any_eq(C, Rv, M) }.
crank(k, C, N) :- op(C, isAllOf), left(C, Op), read_ok(Op),
    N = #min { 2; M, Rv : any_eq(C, Rv, M) }.
crank(k, C, N) :- op(C, O), O = (isPartOf; hasPart), left(C, Op), read_ok(Op),
    N = #min { 2; M, Lo : any_le(C, Lo, M) }.
crank(k, C, N) :- op(C, isA), left(C, Op), read_ok(Op),
    N = #min { 2; M, Lv, Cls : cpair(C, Lv, Cls), isar(Lv, Cls, M) }.

%## Connectives

%*! evaluates(W, C)

World `W` evaluates node `C` with the connective rules below. World `k` evaluates every node.
A completion world evaluates only the open nodes (completion.lp): every other node keeps its
world-`k` rank there, so one set of connective rules serves every world.
*%
evaluates(k, C) :- cnode(C).

% Kleene conjunction and disjunction as #min and #max with their identities (⋀∅ = t,
% ⋁∅ = f); `dprod:not` maps rank N to 2 - N. The identities only seed the aggregates: a
% connective with no member is rejected in constraint.lp (decisions/0017). Strong Kleene logic
% gives a tree the value of its NNF and DNF, so these rules realise the structural rules of
% normalisation stage 2 without rewriting.
crank(W, C, N) :- evaluates(W, C), conn(C, and),
    N = #min { 2; M, D : member(C, D), crank(W, D, M) }.
crank(W, C, N) :- evaluates(W, C), conn(C, or),
    N = #max { 0; M, D : member(C, D), crank(W, D, M) }.
crank(W, C, 2 - N) :- evaluates(W, C), conn(C, negation), member(C, D), crank(W, D, N).
crank(W, C, N) :- evaluates(W, C), conn(C, xone), N = #max { 0; M, D : xone_term(W, C, D, M) }.

%*! xone_term(W, C, D, N)

In world `W`, the disjunct of `xone` node `C` for its member `D` has rank `N`: `D`, and not
each other member. `xone` is the disjunction of these terms, ⋁ᵢ (aᵢ ∧ ⋀ⱼ≠ᵢ ¬aⱼ).
*%
xone_term(W, C, D, N) :- evaluates(W, C), conn(C, xone), member(C, D), crank(W, D, _),
    N = #min { M, self : crank(W, D, M); 2 - M2, D2 : member(C, D2), D2 != D,
        crank(W, D2, M2) }.

%## Values

% Every constraint node `c(C)` is an item, so a node without a rank fails integrity.lp.
item(c(C)) :- cnode(C).
holds(c(C), V) :- crank(k, C, N), rank(V, N).
