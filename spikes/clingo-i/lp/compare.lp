%# compare.lp: the operators, and the Kleene value of every constraint node
%
% Compares each value a leaf's operand reads with each of its right operand values, by value
% within a value space or, on an operand with a concept scheme, under `skos:broader`, and
% combines the comparisons by the operator's definition (due2-profiles.md §4). A comparison the
% operands do not fit, such as an IRI against a literal or values of two spaces, is `u` (rank
% 1), never `f`. Then the connectives combine their members' values: `and` is the least rank,
% `or` the greatest, `dprod:not` the involution, and `xone` counts its `t` and `u` members
% (*Connectives*). The leaf rules serve the worlds that read operands: the Kleene
% world `k`, before completion, and the witness worlds of duty.lp. The connective rules serve
% those and the completion worlds of completion.lp. Ranks are those of kleene.lp.
% Variable letters: DESIGN.md § Vocabulary.
%
% A node is evaluated once in each data space it is read in (`cspace/2`, constraint.lp): a node
% that two policies share reads each policy's hierarchies and schemes, which may differ
% (decisions/0050 #1). Every constraint node gets its rank in each world and data space that
% evaluates it, `crank(W, C, P, N)`, and every node item its truth value, `holds(c(C, P), V)`, its
% rank in world `k`.
%
% - **Consumes:** `kind/2`, `dt_kind/2`, `closure/4`, `le_k/4` (lift.lp); `value/3` (driver);
%   `rank/2` (kleene.lp); `cnode/1`, `conn/2`, `member/2`, `leaf/1`, `op/2`, `right/2`, `cspace/2`
%   (constraint.lp); `left/2` (bind.lp); `read_ok/3`, `read_u/3`, `read_value/3`, `has_scheme/1`,
%   `unchecked_unit/1` (operand.lp); `witness_only/1` (duty.lp).
% - **Provides:** `cpair/5`, `pair/2`, `placed/1`, `same_type/2`, `eqr/3`, `concept_pair/4`,
%   `above/3`, `ceqr/5`, `ordered/1`, `cmpr/3`, `order_rank/3`,
%   `part_space/3`, `ler/4`, `isa_space/3`, `inst/3`, `isar/4`,
%   `any_eq/5`, `any_le/5`, `crank/4`, `evaluates/3`, `xone_count/5`; extends `item/1`, `holds/2`
%   (applies.lp), and `unsupported_value/1` (lift.lp).

%## Pairs

% A leaf on a `u` read has rank 1. On an `ok` read, `cpair(W, C, P, Lv, Rv)` pairs each value read
% in world `W` with each right operand value, for the leaf read in policy `P`'s data space, and the
% pair is compared on its own. The comparisons of *Equality* and *Order* read only the two values,
% so they carry neither world nor policy. Those of *Concepts* and *Hierarchies* read a hierarchy,
% so they carry the policy whose data space holds it.
%
% A leaf whose unit its binding does not declare (`unchecked_unit/1`, operand.lp) has rank 1
% whatever is read, and gives no pairs: nothing says what unit the read value is in
% (decisions/0049 #3). A unit the binding declares is the unit of every read value, so a leaf
% that states it, or states none, compares the values alone (`test_units`).

%*! cpair(W, C, P, Lv, Rv)

In world `W`, leaf `C`, read in policy `P`'s data space, compares the read value `Lv` with the
right operand value `Rv`. A `u` read, or a unit the binding does not declare, gives no pairs: the
leaf is `u` whatever its values.
*%
% Gated on `evaluates/3`: an operand that a rule leaf and a witness leaf share (`due2:actionTime`)
% is read in both worlds, and only the witness leaf is evaluated in `wit(E)`.
cpair(W, C, P, Lv, Rv) :- evaluates(W, C, P), left(C, Op), read_ok(W, Op, P),
    read_value(W, Op, Lv), right(C, Rv), not unchecked_unit(C).

%*! pair(Lv, Rv)

Some leaf compares `Lv` with `Rv`. The comparisons below depend only on the two values.
*%
pair(Lv, Rv) :- cpair(_, _, _, Lv, Rv).

%*! placed(Term)

The literal `Term` has a position in a value space. values.py describes the spaces.
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
% value space holds one kind (values.py), and a position compares them by value, so `5` equals
% `5.0`.
unsupported_value("value: derived string datatypes") :- pair(Lv, Rv), not placed(Lv),
    not placed(Rv), Lv = lit(_, Dt), Rv = lit(_, Dt2), Dt != Dt2, dt_kind(Dt, K),
    dt_kind(Dt2, K).

%## Equality

% `eqr(Lv, Rv, N)` compares two IRIs by identity. It compares two placed literals by position, if
% they lie in one space. It compares two unplaced literals by identity, if they have the same
% datatype (and, for `rdf:langString`, the same tag): that is "strings by code point"
% (due2-profiles.md §4). Every other pair is a misfit, rank 1: an IRI against a literal, a blank
% node, two spaces, a placed against an unplaced literal, two unplaced datatypes.
%
% Values of one kind compare by value, with or without a range (decisions/0014 #6), and values of
% different kinds are a misfit, `u`.

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

% On a leaf whose operand has a scheme, two IRIs are a concept pair (`concept_pair/4`), and
% `ceqr(C, P, Lv, Rv, N)` reads `Lv = Rv` as `Lv ⊑ Rv` in policy `P`'s data space: `t` when `Lv`
% is `Rv`, or a chain of `skos:broader` edges (`above/3`, the transitive closure) leads from `Lv`
% to `Rv` there; `f` otherwise (decisions/0015 #3, #5). A read concept outside the schemes never
% gets here, since its read is `invalid`. Every other pair, a literal on either side included,
% has its `eqr/3` rank, so a string against a concept is a misfit.

%*! concept_pair(C, P, Lv, Rv)

Leaf `C`, read in policy `P`'s data space, compares the IRIs `Lv` and `Rv` as concepts: its left
operand has a concept scheme. Only IRIs are concepts, so a literal on either side is compared by
`eqr/3` (decisions/0015 #7).
*%
concept_pair(C, P, Lv, Rv) :- cpair(_, C, P, Lv, Rv), left(C, Op), has_scheme(Op),
    kind(Lv, iri), kind(Rv, iri).

%*! above(P, Lv, Hi)

In policy `P`'s data space, a chain of one or more `skos:broader` edges leads from the read
concept `Lv` to `Hi`: the transitive closure SKOS calls `skos:broaderTransitive` (decisions/0015
#5). Not reflexive: `ceqr/5` adds identity.
*%
above(P, Lv, Hi) :- concept_pair(_, P, Lv, _), closure(P, broader, Lv, Hi).
above(P, Lv, Hi) :- above(P, Lv, Mid), closure(P, broader, Mid, Hi).

%*! ceqr(C, P, Lv, Rv, N)

In leaf `C`, read in policy `P`'s data space, `Lv = Rv` has rank `N`. For a concept pair it is
`Lv ⊑ Rv`: `t` when `Lv` is `Rv` or below it in `P`'s data space, `f` otherwise, closed-world over
the declared edges (decisions/0015 #3, #4). A read concept in none of the operand's schemes never
gets here: its read is `invalid` (operand.lp). Every other pair has its `eqr/3` rank.
*%
ceqr(C, P, Lv, Rv, 2) :- concept_pair(C, P, Lv, Rv), Lv = Rv.
ceqr(C, P, Lv, Rv, 2) :- concept_pair(C, P, Lv, Rv), above(P, Lv, Rv).
ceqr(C, P, Lv, Rv, 0) :- concept_pair(C, P, Lv, Rv), Lv != Rv, not above(P, Lv, Rv).
ceqr(C, P, Lv, Rv, N) :- cpair(_, C, P, Lv, Rv), not concept_pair(C, P, Lv, Rv), eqr(Lv, Rv, N).

%## Order

% `cmpr(Lv, Rv, Rel)` is `lt`, `eq`, or `gt` within one ordered space, and `u` otherwise.
% `order_rank(O, Rel, N)` reads `lt`, `lteq`, `gt`, and `gteq` off the relation, and `u` gives rank
% 1.

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

% `isPartOf` and `hasPart` ask `Lo ⊑ Hi` (`ler/4`): two IRIs by identity or the typed `partOf`
% closure `le_k/4`, and anything else a misfit. `isA` asks whether the read IRI is an instance of
% the class (`inst/3`): one `rdf:type` edge, then `rdfs:subClassOf` edges, all from `closure/4`.
% Both read the hierarchy of the data space the leaf is read in (`part_space/3`, `isa_space/3`),
% so `ler/4` and `isar/4` are keyed by that policy as well as by the pair.

%*! part_space(Lo, Hi, P)

`isPartOf` or `hasPart` asks whether `Lo ⊑ Hi`, for a pair in either orientation, in a leaf read
in policy `P`'s data space.
*%
part_space(Lv, Rv, P) :- cpair(_, C, P, Lv, Rv), op(C, isPartOf).
part_space(Rv, Lv, P) :- cpair(_, C, P, Lv, Rv), op(C, hasPart).

%*! ler(P, Lo, Hi, N)

In policy `P`'s data space, `Lo ⊑ Hi` has rank `N`: two IRIs are ordered by identity and the
typed `partOf` closure, closed over the declared edges; any other pair is a misfit. The closure
is due2-profiles.md §6's.
*%
ler(P, Lo, Hi, 2) :- part_space(Lo, Hi, P), kind(Lo, iri), kind(Hi, iri), Lo = Hi.
ler(P, Lo, Hi, 2) :- part_space(Lo, Hi, P), kind(Lo, iri), kind(Hi, iri), le_k(P, Lo, Hi, _).
ler(P, Lo, Hi, 0) :- part_space(Lo, Hi, P), kind(Lo, iri), kind(Hi, iri), Lo != Hi,
    not le_k(P, Lo, Hi, _).
ler(P, Lo, Hi, 1) :- part_space(Lo, Hi, P), not kind(Lo, iri).
ler(P, Lo, Hi, 1) :- part_space(Lo, Hi, P), kind(Lo, iri), not kind(Hi, iri).

%*! isa_space(Lv, Cls, P)

`isA` asks whether the read value `Lv` is an instance of `Cls`, in a leaf read in policy `P`'s
data space.
*%
isa_space(Lv, Cls, P) :- cpair(_, C, P, Lv, Cls), op(C, isA).

%*! inst(P, Lv, Cls)

In policy `P`'s data space, `Lv` is an instance of `Cls`: an `rdf:type` edge, then
`rdfs:subClassOf` edges. That is the reading of `isA` in due2-profiles.md §6.
*%
inst(P, Lv, Cls) :- isa_space(Lv, _, P), closure(P, type, Lv, Cls).
inst(P, Lv, Sup) :- inst(P, Lv, Cls), closure(P, subclass, Cls, Sup).

%*! isar(P, Lv, Cls, N)

In policy `P`'s data space, `Lv` is an instance of `Cls` with rank `N`. Only an IRI is compared
with a class.
*%
isar(P, Lv, Cls, 2) :- isa_space(Lv, Cls, P), kind(Lv, iri), kind(Cls, iri), inst(P, Lv, Cls).
isar(P, Lv, Cls, 0) :- isa_space(Lv, Cls, P), kind(Lv, iri), kind(Cls, iri),
    not inst(P, Lv, Cls).
isar(P, Lv, Cls, 1) :- isa_space(Lv, Cls, P), not kind(Lv, iri).
isar(P, Lv, Cls, 1) :- isa_space(Lv, Cls, P), kind(Lv, iri), not kind(Cls, iri).

%## The operators

% The operators combine the pairs (due2-profiles.md §4). `eq`, `neq`, and the order operators
% compare the one read value with the one right value; `neq` is the negation of `eq`. `any_eq(W, C,
% P, Rv, N)` is the disjunction, over the values read in world `W`, of `= Rv`. Each `=` is `ceqr/5`,
% so on a concept-scheme operand `neq` and `isNoneOf` exclude every concept below a right value.
% `isAnyOf` is the greatest `any_eq` over the right values, and `isNoneOf` its negation. `isAllOf`
% is the least `any_eq` over the right values: every right value is read. `isPartOf` is the least,
% over the read values, of "part of some right value", and `hasPart` the least, over the right
% values, of "part of some read value"; with no read values `isPartOf` holds vacuously. `isA` is the
% least over the listed classes. The aggregates carry their identities (`#max { 0; … }`, `#min { 2;
% … }`), so an empty set has the value the operator's quantifier gives it.

%*! any_eq(W, C, P, Rv, N)

In world `W`, some value leaf `C` reads equals its right value `Rv`, with rank `N`, in policy
`P`'s data space: the Kleene disjunction over the read values, under `skos:broader` for concepts
(`ceqr/5`).
*%
any_eq(W, C, P, Rv, N) :- evaluates(W, C, P), right(C, Rv), left(C, Op), read_ok(W, Op, P),
    N = #max { 0; M, Lv : cpair(W, C, P, Lv, Rv), ceqr(C, P, Lv, Rv, M) }.

%*! any_le(W, C, P, Lo, N)

In world `W` and policy `P`'s data space, for `isPartOf`, the read value `Lo` is part of some
right value; for `hasPart`, the right value `Lo` is part of some read value. `N` is the rank of
that Kleene disjunction.
*%
any_le(W, C, P, Lv, N) :- op(C, isPartOf), evaluates(W, C, P), left(C, Op),
    read_value(W, Op, Lv), read_ok(W, Op, P),
    N = #max { 0; M, Rv : cpair(W, C, P, Lv, Rv), ler(P, Lv, Rv, M) }.
any_le(W, C, P, Rv, N) :- op(C, hasPart), evaluates(W, C, P), right(C, Rv), left(C, Op),
    read_ok(W, Op, P), N = #max { 0; M, Lv : cpair(W, C, P, Lv, Rv), ler(P, Rv, Lv, M) }.

%*! crank(W, C, P, N)

In world `W`, node `C`, read in policy `P`'s data space, has rank `N`. World `k` is the Kleene
world: the ranks before completion, under strong Kleene logic. A witness world `wit(E)` gives
the nodes of a duty's witness conditions their ranks against the evidence `E` (duty.lp).
completion.lp adds the ranks of the completion worlds `c` and `flip`. In a world that reads, a
leaf whose read is `u` has rank 1, and so does a leaf whose unit its binding does not declare.
Otherwise its operator decides (due2-profiles.md §4): `eq` and the order operators compare the
one read value with the one right value; `isAnyOf` is the greatest `eq` over the right values,
and `isNoneOf` its negation; `isAllOf` is the least, over right values, of `any_eq`; `isPartOf`
and `hasPart` are the least of `any_le`, and an empty read set holds vacuously; `isA` is the
least over the listed classes. Each `eq`, on a concept-scheme operand, is `⊑` (`ceqr/5`).
*%
crank(W, C, P, 1) :- evaluates(W, C, P), leaf(C), left(C, Op), read_u(W, Op, P).
crank(W, C, P, 1) :- evaluates(W, C, P), unchecked_unit(C).
% The aggregate rules below would give such a leaf, with no pairs, the aggregate's start value,
% a second rank, so they exclude it.
crank(W, C, P, N) :- op(C, eq), cpair(W, C, P, Lv, Rv), ceqr(C, P, Lv, Rv, N).
crank(W, C, P, 2 - N) :- op(C, neq), cpair(W, C, P, Lv, Rv), ceqr(C, P, Lv, Rv, N).
crank(W, C, P, N) :- op(C, O), cpair(W, C, P, Lv, Rv), cmpr(Lv, Rv, Rel), order_rank(O, Rel, N).
crank(W, C, P, N) :- op(C, isAnyOf), evaluates(W, C, P), left(C, Op), read_ok(W, Op, P),
    not unchecked_unit(C), N = #max { 0; M, Rv : any_eq(W, C, P, Rv, M) }.
crank(W, C, P, 2 - N) :- op(C, isNoneOf), evaluates(W, C, P), left(C, Op), read_ok(W, Op, P),
    not unchecked_unit(C), N = #max { 0; M, Rv : any_eq(W, C, P, Rv, M) }.
crank(W, C, P, N) :- op(C, isAllOf), evaluates(W, C, P), left(C, Op), read_ok(W, Op, P),
    not unchecked_unit(C), N = #min { 2; M, Rv : any_eq(W, C, P, Rv, M) }.
crank(W, C, P, N) :- op(C, O), O = (isPartOf; hasPart), evaluates(W, C, P), left(C, Op),
    read_ok(W, Op, P), not unchecked_unit(C), N = #min { 2; M, Lo : any_le(W, C, P, Lo, M) }.
crank(W, C, P, N) :- op(C, isA), evaluates(W, C, P), left(C, Op), read_ok(W, Op, P),
    not unchecked_unit(C),
    N = #min { 2; M, Lv, Cls : cpair(W, C, P, Lv, Cls), isar(P, Lv, Cls, M) }.

%## Connectives

%*! evaluates(W, C, P)

World `W` evaluates node `C`, in policy `P`'s data space, with the leaf and connective rules of
this file. World `k` evaluates every node but those of a duty's witness conditions, which the
witness worlds evaluate (duty.lp), once in each data space the node is read in. A completion
world evaluates only the open nodes (completion.lp): every other node keeps its world-`k` rank
there, so one set of connective rules serves every world.
*%
% A node of a duty's witness conditions has no world-`k` value: it reads the evidence, which
% world `k` does not have. duty.lp gives those nodes the worlds `wit(E)` instead.
evaluates(k, C, P) :- cnode(C), cspace(C, P), not witness_only(C).

% Kleene conjunction and disjunction as #min and #max with their identities (⋀∅ = t,
% ⋁∅ = f); `dprod:not` maps rank N to 2 - N. The identities only seed the aggregates: a
% connective with no member is rejected in constraint.lp (decisions/0017). Strong Kleene logic
% gives a tree the value of its NNF and DNF, because De Morgan's laws, double negation, and
% distributivity hold in it, so these rules realise the structural rules of normalisation stage 2
% without rewriting. A member is in every data space of its connective, since both lie in one
% tree (`cspace/2`, constraint.lp), so a connective reads its members' ranks in its own space.
crank(W, C, P, N) :- evaluates(W, C, P), conn(C, and),
    N = #min { 2; M, D : member(C, D), crank(W, D, P, M) }.
crank(W, C, P, N) :- evaluates(W, C, P), conn(C, or),
    N = #max { 0; M, D : member(C, D), crank(W, D, P, M) }.
crank(W, C, P, 2 - N) :- evaluates(W, C, P), conn(C, negation), member(C, D),
    crank(W, D, P, N).
% `xone` means its expansion, the disjunction of its terms, each term a member conjoined with the
% negation of every other member: ⋁ᵢ (aᵢ ∧ ⋀ⱼ≠ᵢ ¬aⱼ) (due2-profiles.md §5). The program counts
% instead: `xone_count(W, C, P, NT, NU)` says that `NT` members of `C` are `t` and `NU` are `u` in
% world `W` and policy `P`'s data space. The `xone` is `t` when NT = 1 and NU = 0; `f` when NT ≥ 2,
% or when NT = NU = 0; and `u` otherwise. That is the value of the expansion for any values of the
% members, case by case:
%
% - **NT ≥ 2.** Every term conjoins the negation of some `t` member, which is `f`, so every term
%   is `f`, and so is their disjunction.
% - **NT = 1, NU = 0.** The `t` member's term conjoins `t` with the negations of `f` members, so
%   it is `t`, and so is the disjunction.
% - **NT = 1, NU ≥ 1.** The `t` member's term conjoins `t` with negations that are `t` or `u`, at
%   least one `u`, so it is `u`. Every other term conjoins the `t` member negated, so it is `f`.
%   The disjunction is `u`.
% - **NT = NU = 0.** Every member is `f`, so every term is `f`.
% - **NT = 0, NU ≥ 1.** A `u` member's term conjoins `u` with negations that are `t` or `u`, so it
%   is `u`, and no term is `t`, since no member is. The disjunction is `u`.
%
% The expansion has a term for each position in the list, while `member/2` holds a set of nodes.
% They agree because constraint.lp rejects a list that names one node twice (decisions/0022 #1),
% so each node is one position. Two members with the same content are two nodes, and so two
% positions, whether they are compound or leaves; constraint.lp rejects two such leaves under an
% `xone` too (decisions/0022 #2), but as an authoring error, not for this agreement. Counting
% reads `t xone u` as `u`, as the expansion does, not as `t`, which "exactly one is `t`" would
% give. A count that skipped the `u` members would give that `t`, and the mutant
% `xone-unknown-as-false` of TESTS.md is that shortcut.

%*! xone_count(W, C, P, NT, NU)

In world `W` and policy `P`'s data space, `NT` members of the `xone` node `C` are `t` and `NU`
are `u`.
*%
xone_count(W, C, P, NT, NU) :- evaluates(W, C, P), conn(C, xone),
    NT = #count { D : member(C, D), crank(W, D, P, 2) },
    NU = #count { D : member(C, D), crank(W, D, P, 1) }.
crank(W, C, P, 2) :- xone_count(W, C, P, 1, 0).
crank(W, C, P, 0) :- xone_count(W, C, P, NT, _), NT >= 2.
crank(W, C, P, 0) :- xone_count(W, C, P, 0, 0).
crank(W, C, P, 1) :- xone_count(W, C, P, NT, NU), NT < 2, NU > 0.

%## Values

% Every node world `k` evaluates is an item `c(C, P)`, one per data space, so a node without a
% rank fails integrity.lp.
item(c(C, P)) :- evaluates(k, C, P).
holds(c(C, P), V) :- crank(k, C, P, N), rank(V, N).

%## Worked example

% This is the vector of `test_constraint_worked_example`, copied from runs. The rule `ex:r`
% permits `odrl:use` on `ex:a`, and the request matches its action and target, so only the
% constraint part decides:
%
% ```turtle
% ex:r odrl:constraint ex:c .
% ex:c odrl:and ( ex:c1 ex:c2 ) .
% ex:c1 odrl:leftOperand ex:purpose ; odrl:operator odrl:isAnyOf ;
%     odrl:rightOperand ex:research, ex:teaching .
% ex:c2 odrl:leftOperand ex:count ; odrl:operator odrl:lteq ; odrl:rightOperand 5 .
% ex:purpose dprod:operandSource dprod:requestSource ; dprod:operandProperty ex:purpose .
% ex:count dprod:operandSource dprod:requestSource ; dprod:operandProperty ex:count .
% ```
%
% | Request `params` | Reads | Leaves | `crank(k, ex:c, ex:p, N)` | Reply |
% |---|---|---|---|---|
% | purpose `ex:marketing` | `read_ok(k, ex:purpose, ex:p)`, `read_u(k, ex:count, ex:p)` | `eqr(ex:marketing, ex:research, 0)` and `eqr(ex:marketing, ex:teaching, 0)`, so `any_eq` is 0 for both and `crank(k, ex:c1, ex:p, 0)`; `crank(k, ex:c2, ex:p, 1)` | 0 | `NotApplicable` |
% | purpose `ex:research` | as above | `eqr(ex:research, ex:research, 2)`, so `crank(k, ex:c1, ex:p, 2)`; `crank(k, ex:c2, ex:p, 1)` | 1 | `Indeterminate`, from `NotApplicable` to `Permit` |
% | purpose `ex:research`, count `3` | both `ok` | `cpair(k, ex:c2, ex:p, lit("3", xsd:integer), lit("5", xsd:integer))`, `crank(k, ex:c2, ex:p, 2)` | 2 | `Permit` |
% | purpose `ex:research`, count `7` | both `ok` | `crank(k, ex:c2, ex:p, 0)` | 0 | `NotApplicable` |
%
% The first row is the point of Kleene evaluation: `ex:count` is unknown, but `f ∧ u` is `f`, so
% the unknown does not matter, and the atom does not apply. In the second row `t ∧ u` is `u`, the
% constraint part is `u`, and so is the atom's finding. Completion decides it (completion.lp):
% `ex:c` and `ex:c2` are open, and `ex:c1` keeps its `t`. `ex:c2` reads one variable, so there are
% two completions. The permission applies when the variable is `t`, which gives `Permit`, and not
% when it is `f`, which gives `NotApplicable`. The reply names `ex:r` with role `unknown`.
