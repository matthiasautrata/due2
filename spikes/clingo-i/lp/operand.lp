%# operand.lp: each left operand's binding, and what it reads
%
% Binds each left operand a constraint uses, through the layers of due2-profiles.md §2, and
% reads its values from the request, the SOTW, or the context (due2-profiles.md §3). A read is
% `ok`, with its values, or `u`: its source could not answer, gave the wrong number of values,
% or gave a value outside the range. A `u` read makes its constraint `u`, never `f`
% (ways-of-working.md §5.1). A binding that is not admissible gets a `reject`. Variable
% letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `decl/4`, `layer_rank/2`, `source_kind/2`, `context_property/2`,
%   `cardinality_value/2`, `xsd_datatype/1`, `numeric_datatype/1`, `any_literal/1`, `kind/2`,
%   `voc/2` (lift.lp); `request_param/2`, `request_param_set/1`, `fact/2`, `fact_value/2`,
%   `request_party/2`, `sotw_effective_at/1`, `request_at/1`, `value/3` (driver); `left/2`,
%   `c_operator/2`, `op/2`, `right/2` (constraint.lp).
% - **Provides:** `used/1`, `decl_rank/2`, `bound_rank/2`, `binding_layer/2`, `bdecl/3`,
%   `src/2`, `prop/2`, `card/2`, `has_range/1`, `range_kind/2`, `allowed/2`, `has_allowed/1`,
%   `single_left/1`, `candidate_value/2`, `conforms/2`, `read_value/2`, `read_resolved/1`,
%   `nonconforming/1`, `card_ok/1`, `read_ok/1`, `read_u/1`; extends `reject/2` (structure.lp)
%   and `unsupported/1` (lift.lp).

%## Binding

%*! used(Op)

A constraint the program evaluates has left operand `Op`.
*%
used(Op) :- left(_, Op).

%*! decl_rank(Op, N)

A layer of precedence `N` declares the used operand `Op`: it states a source or a property for
it. A layer that states only a range or a cardinality does not declare the operand.
*%
decl_rank(Op, N) :- used(Op), decl(Layer, Op, operandSource, _), layer_rank(Layer, N).
decl_rank(Op, N) :- used(Op), decl(Layer, Op, operandProperty, _), layer_rank(Layer, N).

%*! bound_rank(Op, N)

`N` is the highest precedence (the least rank) of a layer that declares `Op`.
*%
bound_rank(Op, N) :- decl_rank(Op, _), N = #min { M : decl_rank(Op, M) }.

%*! binding_layer(Op, Layer)

`Layer` gives `Op`'s binding: a declaring layer of the highest precedence. The whole
declaration comes from that one layer, never attribute by attribute from several (DESIGN.md
§ `operand.lp`).
*%
binding_layer(Op, Layer) :- bound_rank(Op, N), layer_rank(Layer, N),
    decl(Layer, Op, Key, _), Key = (operandSource; operandProperty).
% Two selected modules at one precedence: the order of odrl:profile values is not in the RDF,
% so which wins cannot be read (due2-profiles.md §2).
unsupported("binding: two profile modules") :- binding_layer(Op, Layer), binding_layer(Op, Layer2),
    Layer != Layer2.

%*! bdecl(Op, Key, Value)

`Op`'s binding has `Value` for attribute `Key`.
*%
bdecl(Op, Key, Value) :- binding_layer(Op, Layer), decl(Layer, Op, Key, Value).

% Exactly one source and one property (due2-profiles.md §3).
reject("UnboundLeftOperand", C) :- left(C, Op), #count { Src : bdecl(Op, operandSource, Src) } != 1.
reject("UnboundLeftOperand", C) :- left(C, Op),
    #count { Prop : bdecl(Op, operandProperty, Prop) } != 1.
% A closed source, an IRI property, and a built-in context property.
reject("InvalidBinding", C) :- left(C, Op), bdecl(Op, operandSource, Src), not source_kind(Src, _).
reject("InvalidBinding", C) :- left(C, Op), bdecl(Op, operandProperty, Prop), not kind(Prop, iri).
reject("InvalidBinding", C) :- left(C, Op), src(Op, context), prop(Op, Prop),
    not context_property(Prop, _).
% The witness is read inside a duty's constraints only, and duties are declined (#49).
reject("WitnessOutsideDuty", C) :- left(C, Op), src(Op, witness).

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

`Op`'s range is `numeric` (`xsd:decimal` or derived), another `datatype`, `literal`
(`rdfs:Literal`), or a `class`.
*%
range_kind(Op, numeric) :- bdecl(Op, range, Rg), numeric_datatype(Rg).
range_kind(Op, datatype) :- bdecl(Op, range, Rg), xsd_datatype(Rg), not numeric_datatype(Rg).
range_kind(Op, literal) :- bdecl(Op, range, Rg), any_literal(Rg).
range_kind(Op, class) :- bdecl(Op, range, Rg), kind(Rg, iri), not xsd_datatype(Rg),
    not any_literal(Rg).
unsupported("binding: range") :- bdecl(Op, range, Rg), bdecl(Op, range, Rg2), Rg != Rg2.
unsupported("binding: range") :- bdecl(Op, range, Rg), not kind(Rg, iri).

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

%## Range conformance

%*! candidate_value(Op, Term)

`Term` is compared against `Op`'s range: a value `Op` reads, or a right operand of a constraint
on `Op`.
*%
candidate_value(Op, Term) :- read_value(Op, Term).
candidate_value(Op, Term) :- left(C, Op), right(C, Term).

%*! conforms(Term, Op)

`Term` conforms to `Op`'s range: anything when there is no range; a literal placed in the
numeric space for a numeric range; a literal of exactly that datatype for another datatype; any
literal for `rdfs:Literal`; an IRI for a class. These are the defaults of due2-profiles.md §3.
*%
conforms(Term, Op) :- candidate_value(Op, Term), not has_range(Op).
conforms(Term, Op) :- candidate_value(Op, Term), range_kind(Op, numeric), value(Term, numeric, _).
conforms(Term, Op) :- candidate_value(Op, Term), range_kind(Op, datatype), bdecl(Op, range, Rg),
    Term = lit(_, Rg).
conforms(Term, Op) :- candidate_value(Op, Term), range_kind(Op, datatype), bdecl(Op, range, Rg),
    Term = lit(_, Rg, _).
conforms(Term, Op) :- candidate_value(Op, Term), range_kind(Op, literal), kind(Term, lit).
conforms(Term, Op) :- candidate_value(Op, Term), range_kind(Op, class), kind(Term, iri).

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

Some value `Op` reads is outside its range. That is `TypeMismatch` in due2-profiles.md §3.
*%
nonconforming(Op) :- read_value(Op, Term), not conforms(Term, Op).

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
