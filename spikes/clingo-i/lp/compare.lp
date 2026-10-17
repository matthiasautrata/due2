%# compare.lp: the operators, and the Kleene value of every constraint node
%
% Compares each value a leaf's operand reads with each of its right operand values, by value
% within a value space, and combines the comparisons by the operator's definition
% (due2-profiles.md §4). A comparison the operands do not fit, such as an IRI against a literal
% or values of two spaces, is `u` (rank 1), never `f`. Then the connectives combine their
% members' values: `and` is the least rank, `or` the greatest, `dprod:not` the involution, and
% `xone` the value of its expansion (DESIGN.md § `compare.lp`). Ranks are those of kleene.lp.
% Variable letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `kind/2`, `closure/3`, `le_k/3` (lift.lp); `value/3` (driver);
%   `rank/2` (kleene.lp); `cnode/1`, `conn/2`, `member/2`, `leaf/1`, `left/2`, `op/2`,
%   `right/2` (constraint.lp); `has_range/1`, `read_ok/1`, `read_u/1`, `read_value/2`
%   (operand.lp).
% - **Provides:** `cpair/3`, `pair/2`, `placed/1`, `same_type/2`, `eqr/3`, `ordered/1`,
%   `cmpr/3`, `order_rank/3`, `part_pair/2`, `ler/3`, `isa_left/1`, `inst/2`, `isar/3`,
%   `any_eq/3`, `any_le/3`, `crank/2`, `xone_term/3`; extends `item/1`, `holds/2`
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

% Two literals placed in one space with different datatypes, under an operand with no range:
% due2-profiles.md §3 does not say whether they compare by value or by identity (#65).
unsupported_value("value: datatypes differ without a range") :- cpair(C, Lv, Rv), left(C, Op),
    not has_range(Op), value(Lv, Space, _), value(Rv, Space, _), Lv = lit(_, Dt),
    Rv = lit(_, Dt2), Dt != Dt2.

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
the read values.
*%
any_eq(C, Rv, N) :- right(C, Rv), left(C, Op), read_ok(Op),
    N = #max { 0; M, Lv : cpair(C, Lv, Rv), eqr(Lv, Rv, M) }.

%*! any_le(C, Lo, N)

For `isPartOf`, the read value `Lo` is part of some right value; for `hasPart`, the right value
`Lo` is part of some read value. `N` is the rank of that Kleene disjunction.
*%
any_le(C, Lv, N) :- op(C, isPartOf), left(C, Op), read_value(Op, Lv), read_ok(Op),
    N = #max { 0; M, Rv : cpair(C, Lv, Rv), ler(Lv, Rv, M) }.
any_le(C, Rv, N) :- op(C, hasPart), right(C, Rv), left(C, Op), read_ok(Op),
    N = #max { 0; M, Lv : cpair(C, Lv, Rv), ler(Rv, Lv, M) }.

%*! crank(C, N)

Node `C` has rank `N`. A leaf whose read is `u` has rank 1. Otherwise its operator decides
(due2-profiles.md §4): `eq` and the order operators compare the one read value with the one
right value; `isAnyOf` is the greatest `eq` over the right values, and `isNoneOf` its negation;
`isAllOf` is the least, over right values, of `any_eq`; `isPartOf` and `hasPart` are the least
of `any_le`, and an empty read set holds vacuously; `isA` is the least over the listed classes.
*%
crank(C, 1) :- leaf(C), left(C, Op), read_u(Op).
crank(C, N) :- op(C, eq), cpair(C, Lv, Rv), eqr(Lv, Rv, N).
crank(C, 2 - N) :- op(C, neq), cpair(C, Lv, Rv), eqr(Lv, Rv, N).
crank(C, N) :- op(C, O), cpair(C, Lv, Rv), cmpr(Lv, Rv, Rel), order_rank(O, Rel, N).
crank(C, N) :- op(C, isAnyOf), left(C, Op), read_ok(Op),
    N = #max { 0; M, Rv : any_eq(C, Rv, M) }.
crank(C, 2 - N) :- op(C, isNoneOf), left(C, Op), read_ok(Op),
    N = #max { 0; M, Rv : any_eq(C, Rv, M) }.
crank(C, N) :- op(C, isAllOf), left(C, Op), read_ok(Op),
    N = #min { 2; M, Rv : any_eq(C, Rv, M) }.
crank(C, N) :- op(C, O), O = (isPartOf; hasPart), left(C, Op), read_ok(Op),
    N = #min { 2; M, Lo : any_le(C, Lo, M) }.
crank(C, N) :- op(C, isA), left(C, Op), read_ok(Op),
    N = #min { 2; M, Lv, Cls : cpair(C, Lv, Cls), isar(Lv, Cls, M) }.

%## Connectives

% Kleene conjunction and disjunction as #min and #max with their identities (⋀∅ = t,
% ⋁∅ = f); `dprod:not` maps rank N to 2 - N. Strong Kleene logic gives a tree the value of its
% NNF and DNF, so these rules realise the structural rules of normalisation stage 2 without
% rewriting.
crank(C, N) :- conn(C, and), N = #min { 2; M, D : member(C, D), crank(D, M) }.
crank(C, N) :- conn(C, or), N = #max { 0; M, D : member(C, D), crank(D, M) }.
crank(C, 2 - N) :- conn(C, negation), member(C, D), crank(D, N).
crank(C, N) :- conn(C, xone), N = #max { 0; M, D : xone_term(C, D, M) }.

%*! xone_term(C, D, N)

The disjunct of `xone` node `C` for its member `D` has rank `N`: `D`, and not each other
member. `xone` is the disjunction of these terms, ⋁ᵢ (aᵢ ∧ ⋀ⱼ≠ᵢ ¬aⱼ).
*%
xone_term(C, D, N) :- conn(C, xone), member(C, D), crank(D, _),
    N = #min { M, self : crank(D, M); 2 - M2, D2 : member(C, D2), D2 != D, crank(D2, M2) }.

%## Values

% Every constraint node `c(C)` is an item, so a node without a rank fails integrity.lp.
item(c(C)) :- cnode(C).
holds(c(C), V) :- crank(C, N), rank(V, N).
