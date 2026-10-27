%# bind.lp: what each policy text's own layers decide
%
% Holds what the layers of one policy text decide for it (its policy graph, its own profiles'
% modules, and the core): the conflict default, and the binding of each left operand through the
% layers of due2-profiles.md §2 (decisions/0014). W1 normalises each policy alone
% (due2-workflows.md §4, *Several policies are one corpus*), so the driver loads this file only in
% a solve over one policy text, with that text's own profiles (`text_id/1`). The driver copies the
% relations the later files read (`INTERFACE` in interpret.py) into the solves over the corpus,
% which do not load this file. A left operand is `o(Iri, Text)`: the IRI `Iri`, as bound in text
% `Text`. Two texts may bind one IRI differently, and each leaf reads its own text's binding. A
% binding that is not admissible gets a `reject`. Variable letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `voc/2`, `binding_key/1`, `conflict_value/2`, `stated_conflict/2`,
%   `source_kind/2`, `context_property/2`, `cardinality_value/2`, `kind/2`, `xsd_datatype/1`,
%   `declared_datatype/1`, `dt_kind/2`, `any_literal/1`, `any_resource/1` (lift.lp);
%   `triple/3`, `module/4`, `layer/2`, `selected_profile/1`, `text_id/1` (driver); `policy/1`,
%   `states_conflict/1`, `duty_node/1` (structure.lp); `left_iri/2`, `node_tree/2`
%   (constraint.lp).
% - **Provides:** `left/2`, `profile_conflict/1`, `some_profile_conflict/0`, `conflict/2`,
%   `decl/4`, `layer_rank/2`, `concept_scheme/2`, `range_iri/1`, `admits_kind/2`, `used/1`,
%   `op_decl/4`, `declares/2`, `where_key/1`, `type_key/1`, `module_differs/1`, `where_rank/3`,
%   `owner_rank/2`, `bdecl/3`, `owned/3`, `retyped/1`, `src/2`, `prop/2`, `card/2`,
%   `has_range/1`, `range_kind/2`, `prop_range_kind/2`, `allowed/2`, `scheme/2`; extends
%   `reject/2` (structure.lp) and `unsupported/1` (lift.lp).

%## The text

%*! left(C, Op)

Leaf `C` has left operand `Op = o(Iri, Text)`: the IRI `Iri` it names, bound in the text `Text`
that states it.
*%
left(C, o(Iri, Text)) :- left_iri(C, Iri), text_id(Text).

%## The conflict strategy

% A policy's strategy is its own `odrl:conflict` if it states one; otherwise the default of a
% profile it selects; otherwise `invalid` (odrl-compound-to-atomic-normalization.md §3). A profile
% of another policy does not count: W1 normalises each policy alone (due2-workflows.md §4).
% structure.lp rejects a stated value that is not valid.

%*! profile_conflict(Strat)

A selected profile resource sets the default conflict strategy `Strat`. See due2-profiles.md §8.1.
*%
profile_conflict(Strat) :- selected_profile(Prof), module(_, Prof, Pred, Iri), voc(conflict, Pred),
    conflict_value(Iri, Strat).
% odrl-compound-to-atomic-normalization.md §3 does not say which of two profile defaults wins, so
% the vector is declined rather than guessed.
unsupported("profile-conflict-defaults") :- profile_conflict(Strat), profile_conflict(Strat2),
    Strat != Strat2.

%*! some_profile_conflict

Some selected profile sets a default conflict strategy.
*%
some_profile_conflict :- profile_conflict(_).

%*! conflict(P, Strat)

Policy `P` resolves its conflicts with strategy `Strat`: `prohibit`, `perm`, or `invalid`. That is
its own `odrl:conflict` if it states one, otherwise the selected profile's default, otherwise
`invalid` (odrl-compound-to-atomic-normalization.md §3).
*%
conflict(P, Strat) :- policy(P), stated_conflict(P, Strat).
conflict(P, Strat) :- policy(P), not states_conflict(P), profile_conflict(Strat).
conflict(P, invalid) :- policy(P), not states_conflict(P), not some_profile_conflict.

%## The layers

% `decl(Layer, Iri, Key, Value)` is one attribute of a binding stated in one layer: `policy` for
% the policy graph, `module(Prof)` for the files of a selected profile, or `core`. `layer_rank/2`
% orders the layers of due2-profiles.md §2 from the top: the policy 0, every profile module 1, the
% core 2. The profile modules share a rank because they have no order. `admits_kind(Rg, K)` gives
% the kind a stated range admits (due2-profiles.md §3 *Kinds*): `literal` for `rdfs:Literal`, none
% for `rdfs:Resource`, and `iri` for a class.

%*! decl(Layer, Iri, Key, Value)

Layer `Layer` states `Value` for attribute `Key` of `Iri`, a left operand or a property
(`binding_key/1`). `Layer` is `policy` for the policy graph, `module(Prof)` for the files of
selected profile `Prof`'s module, or `core` for the baseline (`layer/2`).
*%
decl(policy, Iri, Key, Value) :- triple(Iri, Pred, Value), voc(Key, Pred), binding_key(Key).
decl(Layer, Iri, Key, Value) :- module(Path, Iri, Pred, Value), voc(Key, Pred), binding_key(Key),
    layer(Path, Layer).

%*! layer_rank(Layer, N)

Layer `Layer` has rank `N`, highest first: the policy graph 0, every selected profile module 1,
and the baseline 2. The layers of due2-profiles.md §2; the modules share one rank, because they
have no order.
*%
layer_rank(policy, 0).
layer_rank(Layer, 1) :- layer(_, Layer), Layer = module(_).
layer_rank(core, 2).

%*! concept_scheme(Iri, Scheme)

Some layer states `Iri due2:conceptScheme Scheme`: the policy graph, a selected module, or the
baseline. An operand's schemes are the union over its layers, not a type attribute
(decisions/0015 #6), so this is not a `decl/4` attribute: a layer that states only a scheme
does not own the operand's type.
*%
concept_scheme(Iri, Scheme) :- triple(Iri, Pred, Scheme), voc(conceptScheme, Pred).
concept_scheme(Iri, Scheme) :- module(_, Iri, Pred, Scheme), voc(conceptScheme, Pred).

%*! range_iri(Rg)

Some layer states the IRI `Rg` as a range.
*%
range_iri(Rg) :- decl(_, _, range, Rg), kind(Rg, iri).

%*! admits_kind(Rg, K)

The range `Rg` admits values of kind `K`: a datatype range its datatype's kind, and a class range
`iri`. Both are the kinds of due2-profiles.md §3. `rdfs:Literal` gets `literal`, which admits a
literal of any kind; `rdfs:Resource` admits every term, so it has no kind. Defined for the IRI
ranges that a layer states (`decl/4`), of an operand or of the property an operand reads.
*%
admits_kind(Rg, K) :- range_iri(Rg), xsd_datatype(Rg), dt_kind(Rg, K).
admits_kind(Rg, K) :- range_iri(Rg), declared_datatype(Rg), dt_kind(Rg, K).
admits_kind(Rg, literal) :- range_iri(Rg), any_literal(Rg).
admits_kind(Rg, iri) :- range_iri(Rg), not xsd_datatype(Rg), not declared_datatype(Rg),
    not any_literal(Rg), not any_resource(Rg).

%## Binding

% A left operand is bound when a leaf uses it (`used/1`), under decisions/0014 #1–#3. A layer
% *declares* an operand when it states any of its binding attributes: source, property, range,
% unit, cardinality, or allowed operators (`declares/2`). The binding is assembled from the layers
% in two parts:
%
% - **Where it reads.** The source and the property each come from the highest layer that states
%   them (`where_rank/3`). A policy may rebind a baseline operand, as `due2-rebound-pay-amount`
%   rebinds `odrl:payAmount` to the request.
% - **Its type.** The range, unit, cardinality, and allowed operators come from the lowest declaring
%   layer, the operand's *owner* (`owner_rank/2`). An attribute the owner omits has its default, and
%   the default counts as stated: `owned(Op, cardinality, due2:one)` when the owner gives no
%   cardinality. A higher layer that states a type attribute with other values than the owner's,
%   defaults included, is `reject("RetypedOperand", C)` (`retyped/1`).
%
% `bdecl(Op, Key, Value)` is the assembled binding. Two profile modules that state one attribute of
% an operand with different values are `reject("ConflictingProfileDeclaration", C)`
% (`module_differs/1`): the modules have no order, so neither wins, and such an operand gets no
% binding and no `UnboundLeftOperand`. Modules that agree are one declaration.
% `tools/check_corpus.py` resolves bindings by the same rules (`Bindings`).
%
% The binding gives:
%
% - `src(Op, Src)` and `prop(Op, Prop)`, exactly one each, or `reject("UnboundLeftOperand", C)`. A
%   source outside the four, a property that is not an IRI, or a context property that is not a
%   built-in is `reject("InvalidBinding", C)`. The `witness` source is read only in a duty's
%   conditions, so a leaf on it in a tree of any other structure node is
%   `reject("WitnessOutsideDuty", C)`. `node_tree/2` (constraint.lp) gives each node's trees: its
%   constraint roots, and the refinement roots of the action terms it states. A tree shared by a
%   duty and a rule is in both, and so is rejected.
% - `card(Op, K)`: `set` if the binding states `due2:set`, otherwise `one`. Another cardinality,
%   or two, is `reject("InvalidBinding", C)`.
% - `range_kind(Op, K)`: the kind the owner's range admits (`admits_kind/2`). `rdfs:Resource` admits
%   every kind, so it has no `range_kind`. Two ranges, or a literal one, are
%   `reject("InvalidBinding", C)`. A blank-node range, such as an OWL class expression, declines as
%   `binding: range`: due2 admits it, and the spike does not read it.
% - `prop_range_kind(Op, K)`: the kind of the `rdfs:range` that some layer states for the property
%   `Op` reads. When no value has both kinds, the binding is `reject("OperandRangeMismatch", C)`
%   (decisions/0014 #5): every value the property gives would fail the range. Two kinds that differ
%   have no value in common, except that `literal` shares its values with every kind but `iri`. An
%   operand that reads itself, such as `odrl:payAmount`, is not compared with itself.

%*! used(Op)

A constraint the program evaluates has left operand `Op`.
*%
used(Op) :- left(_, Op).

%*! op_decl(Layer, Op, Key, Value)

Layer `Layer` states `Value` for attribute `Key` of the used operand `Op`, by its IRI.
*%
op_decl(Layer, Op, Key, Value) :- used(Op), Op = o(Iri, _), decl(Layer, Iri, Key, Value).

%*! declares(Layer, Op)

Layer `Layer` declares the used operand `Op`: it states one of its binding attributes
(`binding_key/1`).
*%
declares(Layer, Op) :- op_decl(Layer, Op, _, _).

%*! where_key(Key)

`Key` says where `Op` reads: its source or its property. A higher layer may restate it.
*%
where_key(operandSource; operandProperty).

%*! type_key(Key)

`Key` is a type attribute: the range, the unit, the cardinality, or the allowed operators. Only
the lowest declaring layer states it (decisions/0014 #1, decisions/0049 #1).
*%
type_key(range; operandUnit; cardinality; allowedOperator).

%*! module_differs(Op)

Two selected profile modules state one attribute of `Op` with different values. The modules
have no order, so neither wins: that is `ConflictingProfileDeclaration` (decisions/0014 #3).
*%
module_differs(Op) :- op_decl(module(Prof), Op, Key, Value), op_decl(module(Prof2), Op, Key, _),
    Prof != Prof2, not op_decl(module(Prof2), Op, Key, Value).
reject("ConflictingProfileDeclaration", C) :- left(C, Op), module_differs(Op).

%*! where_rank(Op, Key, N)

`N` is the least rank of a layer that states `Op`'s source or property `Key`: the highest layer
that states it gives it (decisions/0014 #2).
*%
where_rank(Op, Key, N) :- where_key(Key), op_decl(_, Op, Key, _), not module_differs(Op),
    N = #min { M : op_decl(Layer, Op, Key, _), layer_rank(Layer, M) }.

%*! owner_rank(Op, N)

`N` is the rank of the lowest layer that declares `Op`, the layer that owns its type
(decisions/0014 #1).
*%
owner_rank(Op, N) :- declares(_, Op), not module_differs(Op),
    N = #max { M : declares(Layer, Op), layer_rank(Layer, M) }.

%*! bdecl(Op, Key, Value)

`Op`'s binding has `Value` for attribute `Key`: its source and property from the highest layer
that states each, its type attributes from the owner. An attribute the owner omits has none here,
and its default is read where it is used (`card/2`, `has_allowed/1`, `conforms/2`).
*%
bdecl(Op, Key, Value) :- where_rank(Op, Key, N), op_decl(Layer, Op, Key, Value),
    layer_rank(Layer, N).
bdecl(Op, Key, Value) :- owner_rank(Op, N), type_key(Key), op_decl(Layer, Op, Key, Value),
    layer_rank(Layer, N).

%*! owned(Op, Key, Value)

`Op`'s type attribute `Key` has `Value`, as the owner states it, or as the default fills it in:
`due2:one` for a cardinality the owner omits. An omitted range, unit, or operator list has no value,
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
retyped(Op) :- owner_rank(Op, N), op_decl(Layer, Op, Key, Value), type_key(Key),
    layer_rank(Layer, M), M < N, not owned(Op, Key, Value).
retyped(Op) :- owner_rank(Op, N), owned(Op, Key, Value), op_decl(Layer, Op, Key, _),
    layer_rank(Layer, M), M < N, not op_decl(Layer, Op, Key, Value).
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
% One cardinality, `due2:one` or `due2:set` (due2-profiles.md §3, Checks at normalisation).
reject("InvalidBinding", C) :- left(C, Op), bdecl(Op, cardinality, Iri),
    not cardinality_value(Iri, _).
reject("InvalidBinding", C) :- left(C, Op), bdecl(Op, cardinality, Iri),
    bdecl(Op, cardinality, Iri2), Iri != Iri2.

%*! has_range(Op)

`Op`'s binding states a range.
*%
has_range(Op) :- bdecl(Op, range, _).

%*! range_kind(Op, K)

`Op`'s range admits values of kind `K` (`admits_kind/2`).
*%
range_kind(Op, K) :- bdecl(Op, range, Rg), admits_kind(Rg, K).
% One range, not a literal (due2-profiles.md §3, Checks at normalisation).
reject("InvalidBinding", C) :- left(C, Op), bdecl(Op, range, Rg), bdecl(Op, range, Rg2), Rg != Rg2.
reject("InvalidBinding", C) :- left(C, Op), bdecl(Op, range, Rg), kind(Rg, lit).
unsupported("binding: range") :- bdecl(Op, range, Rg), kind(Rg, blank).

%*! prop_range_kind(Op, K)

The property `Op` reads has a range, stated in some layer, that admits kind `K`. An operand that
reads itself, such as `odrl:payAmount`, has its own range as its property's, so it is left out.
*%
prop_range_kind(Op, K) :- prop(Op, Prop), Op = o(Iri, _), Prop != Iri, decl(_, Prop, range, Rg),
    admits_kind(Rg, K).

% The binding's range and the property's are of different kinds (decisions/0014 #5). `literal`
% admits a literal of every kind, so it meets every kind but `iri`: a literal is never an IRI.
reject("OperandRangeMismatch", C) :- left(C, Op), range_kind(Op, K), prop_range_kind(Op, K2),
    K != K2, K != literal, K2 != literal.
reject("OperandRangeMismatch", C) :- left(C, Op), range_kind(Op, literal), prop_range_kind(Op, iri).
reject("OperandRangeMismatch", C) :- left(C, Op), range_kind(Op, iri), prop_range_kind(Op, literal).

%## Operator lists, units, and schemes

% The type attributes that operand.lp checks a leaf against: the allowed operators, the unit,
% and the concept schemes. Two units, or one that is not an IRI, are `reject("InvalidBinding", C)`
% (due2-profiles.md §3, Checks at normalisation).

%*! allowed(Op, Iri)

`Op`'s binding allows the operator `Iri`.
*%
allowed(Op, Iri) :- bdecl(Op, allowedOperator, Iri).
reject("InvalidBinding", C) :- left(C, Op), bdecl(Op, operandUnit, Unit),
    bdecl(Op, operandUnit, Unit2), Unit != Unit2.
reject("InvalidBinding", C) :- left(C, Op), bdecl(Op, operandUnit, Unit), not kind(Unit, iri).

%*! scheme(Op, Scheme)

`Op` compares concepts of the SKOS concept scheme `S`: some layer states `Iri due2:conceptScheme
Scheme` for its IRI. The schemes are the union over the layers (decisions/0015 #6).
*%
scheme(Op, Scheme) :- used(Op), Op = o(Iri, _), concept_scheme(Iri, Scheme).
