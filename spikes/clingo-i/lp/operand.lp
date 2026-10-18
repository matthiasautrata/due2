%# operand.lp: each left operand's binding, and what it reads
%
% Binds each left operand a constraint uses, through the layers of due2-profiles.md §2
% (decisions/0014), and reads its values from the request, the SOTW, or the context
% (due2-profiles.md §3). A read is `ok`, with its values, or `u`: its source could not answer, gave
% the wrong number of values, or gave a value outside the range. A `u` read makes its constraint
% `u`, never `f` (ways-of-working.md §5.1). A binding that is not admissible gets a `reject`.
% Variable letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `decl/4`, `layer_rank/2`, `source_kind/2`, `context_property/2`,
%   `cardinality_value/2`, `kind/2`, `term_kind/2`, `admits_kind/2`, `voc/2`,
%   `concept_scheme/2`, `declared_in_scheme/2`, `closure/3` (lift.lp);
%   `request_param/2`, `request_param_set/1`, `fact/2`, `fact_value/2`,
%   `request_party/2`, `sotw_effective_at/1`, `request_at/1`, `value/3` (driver); `left/2`,
%   `c_operator/2`, `op/2`, `right/2`, `node_tree/2` (constraint.lp); `duty_node/1`
%   (structure.lp).
% - **Provides:** `used/1`, `declares/2`, `where_key/1`, `type_key/1`, `module_differs/1`,
%   `where_rank/3`, `owner_rank/2`, `bdecl/3`, `owned/3`, `retyped/1`, `src/2`, `prop/2`,
%   `card/2`, `has_range/1`, `range_kind/2`, `has_range_kind/1`, `prop_range_kind/2`,
%   `allowed/2`, `has_allowed/1`,
%   `single_left/1`, `scheme/2`, `has_scheme/1`, `concept_operator/1`, `declared_concept/2`,
%   `read_concept/2`, `candidate_value/2`, `conforms/2`, `read_value/2`, `read_resolved/1`,
%   `nonconforming/1`, `card_ok/1`, `read_ok/1`, `read_u/1`, `read_status/2`; extends
%   `reject/2` (structure.lp)
%   and `unsupported/1` (lift.lp).

%## Binding

%*! used(Op)

A constraint the program evaluates has left operand `Op`.
*%
used(Op) :- left(_, Op).

%*! declares(Layer, Op)

Layer `Layer` declares the used operand `Op`: it states one of its binding attributes
(`binding_key/1`).
*%
declares(Layer, Op) :- used(Op), decl(Layer, Op, _, _).

%*! where_key(Key)

`Key` says where `Op` reads: its source or its property. A higher layer may restate it.
*%
where_key(operandSource; operandProperty).

%*! type_key(Key)

`Key` is a type attribute: the range, the cardinality, or the allowed operators. Only the
lowest declaring layer states it (decisions/0014 #1).
*%
type_key(range; cardinality; allowedOperator).

%*! module_differs(Op)

Two selected profile modules state one attribute of `Op` with different values. The modules
have no order, so neither wins: that is `ConflictingProfileDeclaration` (decisions/0014 #3).
*%
module_differs(Op) :- used(Op), decl(module(P), Op, Key, V), decl(module(P2), Op, Key, _),
    P != P2, not decl(module(P2), Op, Key, V).
reject("ConflictingProfileDeclaration", C) :- left(C, Op), module_differs(Op).

%*! where_rank(Op, Key, N)

`N` is the least rank of a layer that states `Op`'s source or property `Key`: the highest layer
that states it gives it (decisions/0014 #2).
*%
where_rank(Op, Key, N) :- used(Op), where_key(Key), decl(_, Op, Key, _), not module_differs(Op),
    N = #min { M : decl(L, Op, Key, _), layer_rank(L, M) }.

%*! owner_rank(Op, N)

`N` is the rank of the lowest layer that declares `Op`, the layer that owns its type
(decisions/0014 #1).
*%
owner_rank(Op, N) :- declares(_, Op), not module_differs(Op),
    N = #max { M : declares(L, Op), layer_rank(L, M) }.

%*! bdecl(Op, Key, Value)

`Op`'s binding has `Value` for attribute `Key`: its source and property from the highest layer
that states each, its type attributes from the owner. An attribute the owner omits has none here,
and its default is read where it is used (`card/2`, `has_allowed/1`, `conforms/2`).
*%
bdecl(Op, Key, Value) :- where_rank(Op, Key, N), decl(L, Op, Key, Value), layer_rank(L, N).
bdecl(Op, Key, Value) :- owner_rank(Op, N), type_key(Key), decl(L, Op, Key, Value),
    layer_rank(L, N).

%*! owned(Op, Key, Value)

`Op`'s type attribute `Key` has `Value`, as the owner states it, or as the default fills it in:
`due2:one` for a cardinality the owner omits. An omitted range or operator list has no value,
which is the default (due2-profiles.md §3 Defaults).
*%
owned(Op, Key, Value) :- bdecl(Op, Key, Value), type_key(Key).
owned(Op, cardinality, Iri) :- owner_rank(Op, _), not bdecl(Op, cardinality, _),
    cardinality_value(Iri, one).

%*! retyped(Op)

A layer above the owner states a type attribute of `Op` with other values than the owner's, a
default included: that is `RetypedOperand` (decisions/0014 #2). An omitted operator list is
every core operator, and the spike does not compute that list, so any operator list a higher
layer states over an omitted one counts.
*%
retyped(Op) :- owner_rank(Op, N), decl(L, Op, Key, V), type_key(Key), layer_rank(L, M), M < N,
    not owned(Op, Key, V).
retyped(Op) :- owner_rank(Op, N), owned(Op, Key, V), decl(L, Op, Key, _), layer_rank(L, M),
    M < N, not decl(L, Op, Key, V).
reject("RetypedOperand", C) :- left(C, Op), retyped(Op).

% Exactly one source and one property (due2-profiles.md §3).
% A conflicted operand is rejected for the conflict alone.
reject("UnboundLeftOperand", C) :- left(C, Op), not module_differs(Op),
    #count { Src : bdecl(Op, operandSource, Src) } != 1.
reject("UnboundLeftOperand", C) :- left(C, Op), not module_differs(Op),
    #count { Prop : bdecl(Op, operandProperty, Prop) } != 1.
% A closed source, an IRI property, and a built-in context property.
reject("InvalidBinding", C) :- left(C, Op), bdecl(Op, operandSource, Src), not source_kind(Src, _).
reject("InvalidBinding", C) :- left(C, Op), bdecl(Op, operandProperty, Prop), not kind(Prop, iri).
reject("InvalidBinding", C) :- left(C, Op), src(Op, context), prop(Op, Prop),
    not context_property(Prop, _).
% The witness is read inside a duty's constraints and the refinements of its actions only
% (due2-workflows.md §5.2): a tree shared with a policy or a rule is rejected.
reject("WitnessOutsideDuty", C) :- left(C, Op), src(Op, witness), node_tree(Node, C),
    not duty_node(Node).

%*! src(Op, Src)

`Op` reads source `Src`: `request`, `state`, `context`, or `witness`.
*%
src(Op, Src) :- bdecl(Op, operandSource, Iri), source_kind(Iri, Src).

%*! prop(Op, Prop)

`Op` reads property `Prop` of its source.
*%
prop(Op, Prop) :- bdecl(Op, operandProperty, Prop).

%*! card(Op, K)

`Op` has cardinality `K`: `one`, unless its binding states `due2:set`. That is the default of
due2-profiles.md §3.
*%
card(Op, set) :- bdecl(Op, cardinality, Iri), cardinality_value(Iri, set).
card(Op, one) :- used(Op), not card(Op, set).
unsupported("binding: cardinality") :- bdecl(Op, cardinality, Iri), not cardinality_value(Iri, _).
unsupported("binding: cardinality") :- bdecl(Op, cardinality, Iri), bdecl(Op, cardinality, Iri2),
    Iri != Iri2.

%*! has_range(Op)

`Op`'s binding states a range.
*%
has_range(Op) :- bdecl(Op, range, _).

%*! range_kind(Op, K)

`Op`'s range admits values of kind `K` (`admits_kind/2`).
*%
range_kind(Op, K) :- bdecl(Op, range, Rg), admits_kind(Rg, K).
unsupported("binding: range") :- bdecl(Op, range, Rg), bdecl(Op, range, Rg2), Rg != Rg2.
unsupported("binding: range") :- bdecl(Op, range, Rg), not kind(Rg, iri).

%*! has_range_kind(Op)

`Op`'s range has a kind. `rdfs:Resource` has none, so it admits every term.
*%
has_range_kind(Op) :- range_kind(Op, _).

%*! prop_range_kind(Op, K)

The property `Op` reads has a range, stated in some layer, that admits kind `K`. An operand that
reads itself, such as `odrl:payAmount`, has its own range as its property's, so it is left out.
*%
prop_range_kind(Op, K) :- prop(Op, Prop), Prop != Op, decl(_, Prop, range, Rg),
    admits_kind(Rg, K).

% The binding's range and the property's are of different kinds (decisions/0014 #5). `literal`
% admits a literal of every kind, so it meets every kind but `iri`: a literal is never an IRI.
reject("OperandRangeMismatch", C) :- left(C, Op), range_kind(Op, K), prop_range_kind(Op, K2),
    K != K2, K != literal, K2 != literal.
reject("OperandRangeMismatch", C) :- left(C, Op), range_kind(Op, literal), prop_range_kind(Op, iri).
reject("OperandRangeMismatch", C) :- left(C, Op), range_kind(Op, iri), prop_range_kind(Op, literal).

%## Operator checks

%*! allowed(Op, Iri)

`Op`'s binding allows the operator `Iri`.
*%
allowed(Op, Iri) :- bdecl(Op, allowedOperator, Iri).

%*! has_allowed(Op)

`Op`'s binding lists its allowed operators. Without the list every core operator is allowed;
the default's narrowing by signature (due2-profiles.md §3) is not checked (DESIGN.md
§ `operand.lp`).
*%
has_allowed(Op) :- allowed(Op, _).

%*! single_left(O)

Operator `O` compares one left value. That is its signature in due2-profiles.md §4.
*%
single_left(eq; neq; lt; lteq; gt; gteq; isAnyOf; isNoneOf).

% An operator the binding does not allow, a right operand outside the range, or isA over a
% set-valued operand (due2-diagnostics.md, OperatorTypeMismatch).
reject("OperatorTypeMismatch", C) :- left(C, Op), has_allowed(Op), c_operator(C, Iri),
    not allowed(Op, Iri).
reject("OperatorTypeMismatch", C) :- left(C, Op), right(C, V), not conforms(V, Op).
reject("OperatorTypeMismatch", C) :- left(C, Op), card(Op, set), op(C, isA).
% A set-valued operand under an operator of one left value: the spec gives no reading.
unsupported("constraint: set-valued operand on a single-value operator") :- left(C, Op),
    card(Op, set), op(C, O), single_left(O).

%## Concept schemes

%*! scheme(Op, S)

`Op` compares concepts of the SKOS concept scheme `S`: some layer states `Op due2:conceptScheme S`.
The schemes are the union over the layers (decisions/0015 #6).
*%
scheme(Op, S) :- used(Op), concept_scheme(Op, S).

%*! has_scheme(Op)

`Op` has a concept scheme, so it compares IRIs under `skos:broader`. The comparison is
`ceqr/4` in compare.lp.
*%
has_scheme(Op) :- scheme(Op, _).

%*! concept_operator(O)

`O` is an operator that reads a concept hierarchy: `eq` and `isAnyOf`, and their complements
`neq` and `isNoneOf` (decisions/0015 #3).
*%
concept_operator(eq; neq; isAnyOf; isNoneOf).

%*! declared_concept(Op, V)

The IRI right operand `V` of a constraint on `Op` is in one of `Op`'s schemes, by a membership
the policy or a selected module declares.
*%
declared_concept(Op, V) :- left(C, Op), right(C, V), scheme(Op, S), declared_in_scheme(V, S).

%*! read_concept(Op, V)

The IRI `V` that `Op` reads is in one of `Op`'s schemes, by a membership the policy, a selected
module, or the SOTW states.
*%
read_concept(Op, V) :- read_value(Op, V), scheme(Op, S), closure(inScheme, V, S).

% The three checks of decisions/0015 #8. Normalisation does not see the SOTW, so a right
% operand counts only the memberships the policy and its modules declare. A literal is not a
% concept, so it is not checked: a string against a concept is a misfit (decisions/0015 #7).
reject("OperatorTypeMismatch", C) :- left(C, Op), has_scheme(Op), right(C, V), kind(V, iri),
    not declared_concept(Op, V).
reject("OperatorTypeMismatch", C) :- left(C, Op), has_scheme(Op), op(C, O),
    not concept_operator(O).
% A datatype range admits no IRI, so no concept. `rdfs:Literal` and `rdfs:Resource` are classes,
% not datatypes: the first has kind `literal`, the second none.
reject("InvalidBinding", C) :- left(C, Op), has_scheme(Op), range_kind(Op, K), K != iri,
    K != literal.

%## Range conformance

%*! candidate_value(Op, Term)

`Term` is compared against `Op`'s range: a value `Op` reads, or a right operand of a constraint
on `Op`.
*%
candidate_value(Op, Term) :- read_value(Op, Term).
candidate_value(Op, Term) :- left(C, Op), right(C, Term).

%*! conforms(Term, Op)

`Term` conforms to `Op`'s range: anything when there is no range or a range without a kind; a
term of the range's kind; any literal for `rdfs:Literal`. These are the defaults of
due2-profiles.md §3, so `5` and `5.00` both conform to `xsd:decimal`, and a `xsd:dateTimeStamp`
to `xsd:dateTime`.
*%
conforms(Term, Op) :- candidate_value(Op, Term), not has_range(Op).
conforms(Term, Op) :- candidate_value(Op, Term), has_range(Op), not has_range_kind(Op).
conforms(Term, Op) :- candidate_value(Op, Term), range_kind(Op, K), term_kind(Term, K),
    K != numeric.
% A numeric value must be placed in the numeric space. An ill-typed one is invalid, and so is an
% `xsd:float` or `xsd:double`, which has no exact equality (due2-profiles.md §4), so neither
% conforms, and the read is `u`.
conforms(Term, Op) :- candidate_value(Op, Term), range_kind(Op, numeric),
    value(Term, numeric, _).
conforms(Term, Op) :- candidate_value(Op, Term), range_kind(Op, literal), kind(Term, lit).

%## Reads

%*! read_value(Op, Term)

`Op` reads the value `Term`: a request parameter, a value of a `resolved` SOTW fact, or the
context built-in. The context built-ins are the table of due2-profiles.md §3.
*%
read_value(Op, Term) :- src(Op, request), prop(Op, Prop), request_param(Prop, Term).
read_value(Op, Term) :- src(Op, state), prop(Op, Prop), fact(Prop, resolved),
    fact_value(Prop, Term).
read_value(Op, Party) :- src(Op, context), prop(Op, Prop), context_property(Prop, agent),
    request_party(F, Party), voc(assignee, F).
read_value(Op, Lit) :- src(Op, context), prop(Op, Prop), context_property(Prop, clock),
    sotw_effective_at(Lit).
read_value(Op, Lit) :- src(Op, context), prop(Op, Prop), context_property(Prop, actionTime),
    request_at(Lit).

%*! read_resolved(Op)

`Op`'s source answered: the request has the parameter (a list parameter, even an empty one),
the SOTW fact is `resolved`, or the context has the built-in. Every other status (`missing`,
`invalid`, `conflict`, `unresolved`, or no fact at all) leaves it unresolved.
*%
read_resolved(Op) :- src(Op, request), prop(Op, Prop), request_param(Prop, _).
read_resolved(Op) :- src(Op, request), prop(Op, Prop), request_param_set(Prop).
read_resolved(Op) :- src(Op, state), prop(Op, Prop), fact(Prop, resolved).
read_resolved(Op) :- src(Op, context), read_value(Op, _).

%*! nonconforming(Op)

Some value `Op` reads is outside its range, or is an IRI in none of its concept schemes. The
first is `TypeMismatch` in due2-profiles.md §3, the second decisions/0015 #4: either way the read
is `invalid`, so `u`, never `f`.
*%
nonconforming(Op) :- read_value(Op, Term), not conforms(Term, Op).
nonconforming(Op) :- read_value(Op, V), kind(V, iri), has_scheme(Op), not read_concept(Op, V).

%*! card_ok(Op)

`Op` read as many values as its cardinality allows: exactly one for `one`, any number, none
included, for `set`. More than one for `one` is `MultipleValues`.
*%
card_ok(Op) :- read_resolved(Op), card(Op, set).
card_ok(Op) :- read_resolved(Op), card(Op, one), #count { Term : read_value(Op, Term) } = 1.

%*! read_ok(Op)

`Op`'s read gives a value set the operators compare.
*%
read_ok(Op) :- read_resolved(Op), card_ok(Op), not nonconforming(Op).

%*! read_u(Op)

`Op`'s read is unknown, so every constraint on it is `u`. That is the resolution rule of
due2-profiles.md §3.
*%
read_u(Op) :- used(Op), not read_resolved(Op).
read_u(Op) :- read_resolved(Op), not card_ok(Op).
read_u(Op) :- nonconforming(Op).

%*! read_status(Op, S)

`Op`'s read is `u` with status `S`: `missing`, `invalid`, `conflict`, or `unresolved`. The
statuses are those of due2-profiles.md §3. A request, witness, or context source that has no
value is `missing`. A state property keeps the status of its fact, and is `unresolved` when it
has none. A resolved read with no value on cardinality `one` is `missing`, and with several
`conflict`. A read of the right number of values with one outside the range is `invalid`. Only
`unresolved` is completed by pairing (completion.lp, decisions/0016).
*%
read_status(Op, missing) :- used(Op), src(Op, Src), Src != state, not read_resolved(Op).
read_status(Op, S) :- used(Op), src(Op, state), prop(Op, Prop), fact(Prop, S), S != resolved.
read_status(Op, unresolved) :- used(Op), src(Op, state), prop(Op, Prop), not fact(Prop, _).
read_status(Op, missing) :- read_resolved(Op), card(Op, one),
    #count { Term : read_value(Op, Term) } = 0.
read_status(Op, conflict) :- read_resolved(Op), card(Op, one),
    #count { Term : read_value(Op, Term) } > 1.
read_status(Op, invalid) :- card_ok(Op), nonconforming(Op).
