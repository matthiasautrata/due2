%# operand.lp: what each left operand's binding admits, and what it reads
%
% Checks each leaf against its operand's binding, which bind.lp assembles (due2-profiles.md §3),
% and reads the operand's values in each world that evaluates it: in world `k` from the request,
% the SOTW, or the context, and in world `wit(E)` from the evidence `E` as well
% (due2-workflows.md §5.3). A read is `ok`, with its values, or `u`: its source could not answer,
% gave the wrong number of values, or gave a value outside the range. A `u` read makes its
% constraint `u`, never `f` (ways-of-working.md §5.1). A leaf the binding does not admit gets a
% `reject`. Variable letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `voc/2`, `context_property/2`, `kind/2`, `term_kind/2`,
%   `declared_in_scheme/2`, `closure/4`, `fact/2`, `fact_value/2` (lift.lp); `request_param/2`, `request_param_set/1`, `request_party/2`,
%   `sotw_effective_at/1`, `request_at/1`, `evidence/4`, `evidence_param/3`, `value/3`
%   (driver); `c_operator/2`, `op/2`, `right/2`, `unit/2`, `cspace/2` (constraint.lp); `left/2`, `owned/3`,
%   `src/2`, `prop/2`, `card/2`, `has_range/1`, `range_kind/2`, `allowed/2`,
%   `scheme/2` (bind.lp); `evaluates/2` (compare.lp).
% - **Provides:** `has_range_kind/1`, `has_allowed/1`, `single_left/1`, `has_scheme/1`,
%   `concept_operator/1`, `declared_concept/2`, `op_space/2`, `read_concept/3`, `read_concept/2`, `candidate_value/2`,
%   `conforms/2`, `read_world/1`, `read_in/2`, `read_value/3`, `read_resolved/2`,
%   `nonconforming/2`, `card_ok/2`, `read_ok/2`, `read_u/2`, `read_status/3`,
%   `unchecked_unit/1`; extends `reject/2` (structure.lp) and `unsupported/1` (lift.lp).

%## Operator checks

% `allowed(Op, Iri)` is a `due2:allowedOperator` value. An operator outside a stated list is
% `reject("OperatorTypeMismatch", C)`. Without a list every core operator is allowed.
% due2-profiles.md §3 narrows that default by the operators' signatures over the range, and the
% spike does not check the narrowing: a leaf whose operator does not fit its range evaluates as a
% misfit, `u`, where W1 would reject it. `interpret` receives only admissible policies, so only a
% negative vector can tell.
%
% `isA` over a set-valued operand is `reject("OperatorTypeMismatch", C)`, and so is an operator of
% one left value over one (`single_left/1`: `eq`, `neq`, the order operators, `isAnyOf`, `isNoneOf`;
% decisions/0025).

%*! has_allowed(Op)

`Op`'s binding lists its allowed operators. Without the list every core operator is allowed;
the default's narrowing by signature (due2-profiles.md §3) is not checked (*Operator
checks*).
*%
has_allowed(Op) :- allowed(Op, _).

%*! single_left(O)

Operator `O` compares one left value. That is its signature in due2-profiles.md §4.
*%
single_left(eq; neq; lt; lteq; gt; gteq; isAnyOf; isNoneOf).

% An operator the binding does not allow, a right operand outside the range, or isA or an
% operator of one left value over a set-valued operand (due2-diagnostics.md,
% OperatorTypeMismatch; decisions/0025).
reject("OperatorTypeMismatch", C) :- left(C, Op), has_allowed(Op), c_operator(C, Iri),
    not allowed(Op, Iri).
reject("OperatorTypeMismatch", C) :- left(C, Op), right(C, V), not conforms(V, Op).
reject("OperatorTypeMismatch", C) :- left(C, Op), card(Op, set), op(C, isA).
reject("OperatorTypeMismatch", C) :- left(C, Op), card(Op, set), op(C, O), single_left(O).

%## Units

% A binding's `due2:unit` is a type attribute (`operandUnit`, *Binding*). A leaf's `odrl:unit`
% (`unit/2`, constraint.lp) must be that IRI, or the leaf is `reject("OperatorTypeMismatch", C)`.
% A leaf that states a unit on an operand whose binding declares none is admitted, and is `u`
% whatever is read (compare.lp), with status `misfit` (completion.lp): nothing says what unit
% the read value is in (due2-profiles.md §3 Units, decisions/0049). W1 also warns with
% `UncheckedUnit`; the spike reports no warnings. bind.lp rejects two units, or one that is not an
% IRI.

%*! unchecked_unit(C)

Leaf `C` states a unit that its operand's binding does not declare: the binding declares no unit.
*%
unchecked_unit(C) :- unit(C, _), left(C, Op), not owned(Op, operandUnit, _).
reject("OperatorTypeMismatch", C) :- unit(C, Iri), left(C, Op), owned(Op, operandUnit, Iri2),
    Iri != Iri2.

%## Concept schemes

% Under decisions/0015, `scheme(Op, S)` gives the schemes of a used operand, and `has_scheme(Op)`
% makes its `eq`, `neq`, `isAnyOf`, and `isNoneOf` compare IRIs under `skos:broader` (compare.lp).
% Three checks of decisions/0015 #8 reject the binding's constraints:
%
% - an IRI right operand in none of the schemes by `declared_in_scheme/2` (`declared_concept/2`;
%   normalisation does not see the SOTW, so its memberships do not count) is
%   `reject("OperatorTypeMismatch", C)`;
% - so is an operator outside `concept_operator/1`;
% - a scheme on a datatype range is `reject("InvalidBinding", C)`.
%
% A literal is not a concept, so a literal right operand is not checked.

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

%*! op_space(Op, P)

Operand `Op` is read in policy `P`'s data space: it is the left operand of a leaf read there,
as `cspace/2` gives it.
*%
op_space(Op, P) :- left(C, Op), cspace(C, P).

%*! read_concept(P, Op, V)

The IRI `V` that `Op` reads, in some world, is in one of `Op`'s schemes in policy `P`'s data
space, by a membership the policy, one of its layers, or the SOTW states.
*%
read_concept(P, Op, V) :- read_value(_, Op, V), scheme(Op, S), op_space(Op, P),
    closure(P, inScheme, V, S).

%*! read_concept(Op, V)

The IRI `V` that `Op` reads is in one of `Op`'s schemes in a data space of `Op`.
*%
read_concept(Op, V) :- read_concept(_, Op, V).
unsupported("shared node: read apart by its policies") :- op_space(Op, P), op_space(Op, Q),
    read_concept(P, Op, V), not read_concept(Q, Op, V).

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

% `conforms/2` applies the defaults of due2-profiles.md §3. Without a range, or with
% `rdfs:Resource`, every value conforms. Otherwise a value conforms when its kind is the range's: an
% IRI to a class, an `xsd:dateTimeStamp` to `xsd:dateTime`. A `numeric` range also needs the literal
% placed in the numeric space, so `5` and `5.00` both conform to `xsd:decimal`, but an ill-typed
% number does not, nor an `xsd:double`, which has no exact equality (due2-profiles.md §4).
% `rdfs:Literal` takes any literal. A right operand value that does not conform is
% `reject("OperatorTypeMismatch", C)`.

%*! has_range_kind(Op)

`Op`'s range has a kind. `rdfs:Resource` has none, so it admits every term.
*%
has_range_kind(Op) :- range_kind(Op, _).

%*! candidate_value(Op, Term)

`Term` is compared against `Op`'s range: a value `Op` reads in some world, or a right operand
of a constraint on `Op`.
*%
candidate_value(Op, Term) :- read_value(_, Op, Term).
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

% An operand is read once in each world that evaluates a leaf on it (`read_in(W, Op)`): world `k`,
% and the witness world `wit(E)` of each piece of evidence `E` (`read_world/1`, duty.lp). The
% completion worlds read nothing, because their leaves take a variable's value (completion.lp).
% `read_value(W, Op, Term)` is what the source gives in world `W`, and `read_resolved(W, Op)` says
% the source answered:
%
% | Source | Answered when | Values |
% |---|---|---|
% | `request` | the request has the parameter, or gives it as a list, even an empty one | the parameter's values |
% | `state` | the SOTW fact has status `resolved` | the fact's values |
% | `witness`, in `wit(E)` only | the evidence `E` has the parameter | its values |
% | `context`, `agent` | the request names an assignee | the assignee |
% | `context`, `clock` | the SOTW has `effective_at` | that instant |
% | `context`, `actionTime`, in `k` | the request has `at` | that instant |
% | `context`, `actionTime`, in `wit(E)` | always | `E`'s `occurred_at` (due2-workflows.md §5.3) |
%
% A fact with any other status (`missing`, `invalid`, `conflict`, `unresolved`), no fact at all, or
% an absent parameter or context value leaves the read unanswered, so `read_resolved/2` fails. A
% `witness` read in world `k` is never answered, but no world-`k` leaf makes one: world `k` skips
% the witness conditions (duty.lp), and a rule's leaf on the witness source is rejected
% (`WitnessOutsideDuty`, under *Binding*). Then, in each world:
%
% - `card_ok(W, Op)`: a `set` operand takes any number of values, none included; a `one` operand
%   takes exactly one. Two or more for `one` is `MultipleValues`, and none is no value
%   (due2-profiles.md §3).
% - `nonconforming(W, Op)`: some read value is outside the range, `TypeMismatch` (due2-profiles.md
%   §3), or is an IRI in none of the operand's schemes by any membership, the SOTW's included
%   (`read_concept/2`, decisions/0015 #4).
% - `read_ok(W, Op)` when the read is resolved, its count fits, and every value conforms; `read_u(W,
%   Op)` otherwise. A `u` read makes every leaf on it `u`, never `f` (ways-of-working.md §5.1).
%   integrity.lp checks that every read is exactly one of the two.
% - `read_status(W, Op, S)`, for a `u` read, the status of decisions/0016: a state fact's own
%   status; `unresolved` for no fact; `missing` for an unanswered request, witness, or context read,
%   or a resolved `one` read with no value; `conflict` for a resolved `one` read with several;
%   `invalid` when a value is outside the range or its schemes. integrity.lp checks that each `u`
%   read has exactly one.

%*! read_world(W)

World `W` reads operands: the Kleene world `k`, against the request, and the world `wit(E)` of
each piece of evidence `E`, against that evidence. The completion worlds read nothing; their
leaves are assigned (completion.lp).
*%
read_world(k).
read_world(wit(E)) :- evidence(E, _, _, _).

%*! read_in(W, Op)

World `W` evaluates a constraint on left operand `Op`, so `Op` is read in it.
*%
read_in(W, Op) :- read_world(W), evaluates(W, C), left(C, Op).

%*! read_value(W, Op, Term)

In world `W`, `Op` reads the value `Term`: a request parameter, a value of a `resolved` SOTW
fact, an evidence parameter in `wit(E)`, or the context built-in. The context built-ins are the
table of due2-profiles.md §3; `due2:actionTime` is the request's `at` in `k` and the evidence's
`occurred_at` in `wit(E)` (due2-workflows.md §5.3).
*%
read_value(W, Op, Term) :- read_in(W, Op), src(Op, request), prop(Op, Prop),
    request_param(Prop, Term).
read_value(W, Op, Term) :- read_in(W, Op), src(Op, state), prop(Op, Prop), fact(Prop, resolved),
    fact_value(Prop, Term).
read_value(wit(E), Op, Term) :- read_in(wit(E), Op), src(Op, witness), prop(Op, Prop),
    evidence_param(E, Prop, Term).
read_value(W, Op, Party) :- read_in(W, Op), src(Op, context), prop(Op, Prop),
    context_property(Prop, agent), request_party(F, Party), voc(assignee, F).
read_value(W, Op, Lit) :- read_in(W, Op), src(Op, context), prop(Op, Prop),
    context_property(Prop, clock), sotw_effective_at(Lit).
read_value(k, Op, Lit) :- read_in(k, Op), src(Op, context), prop(Op, Prop),
    context_property(Prop, actionTime), request_at(Lit).
read_value(wit(E), Op, Lit) :- read_in(wit(E), Op), src(Op, context), prop(Op, Prop),
    context_property(Prop, actionTime), evidence(E, Lit, _, _).

%*! read_resolved(W, Op)

In world `W`, `Op`'s source answered: the request has the parameter (a list parameter, even an
empty one), the SOTW fact is `resolved`, the evidence has the parameter, or the context has the
built-in. Every other status (`missing`, `invalid`, `conflict`, `unresolved`, or no fact at all)
leaves it unresolved.
*%
read_resolved(W, Op) :- read_in(W, Op), src(Op, request), prop(Op, Prop), request_param(Prop, _).
read_resolved(W, Op) :- read_in(W, Op), src(Op, request), prop(Op, Prop), request_param_set(Prop).
read_resolved(W, Op) :- read_in(W, Op), src(Op, state), prop(Op, Prop), fact(Prop, resolved).
read_resolved(wit(E), Op) :- read_in(wit(E), Op), src(Op, witness), prop(Op, Prop),
    evidence_param(E, Prop, _).
read_resolved(W, Op) :- read_in(W, Op), src(Op, context), read_value(W, Op, _).

%*! nonconforming(W, Op)

In world `W`, some value `Op` reads is outside its range, or is an IRI in none of its concept
schemes. The first is `TypeMismatch` in due2-profiles.md §3, the second decisions/0015 #4:
either way the read is `invalid`, so `u`, never `f`.
*%
nonconforming(W, Op) :- read_value(W, Op, Term), not conforms(Term, Op).
nonconforming(W, Op) :- read_value(W, Op, V), kind(V, iri), has_scheme(Op),
    not read_concept(Op, V).

%*! card_ok(W, Op)

In world `W`, `Op` read as many values as its cardinality allows: exactly one for `one`, any
number, none included, for `set`. More than one for `one` is `MultipleValues`.
*%
card_ok(W, Op) :- read_resolved(W, Op), card(Op, set).
card_ok(W, Op) :- read_resolved(W, Op), card(Op, one),
    #count { Term : read_value(W, Op, Term) } = 1.

%*! read_ok(W, Op)

In world `W`, `Op`'s read gives a value set the operators compare.
*%
read_ok(W, Op) :- read_resolved(W, Op), card_ok(W, Op), not nonconforming(W, Op).

%*! read_u(W, Op)

In world `W`, `Op`'s read is unknown, so every constraint on it is `u` there. That is the
resolution rule of due2-profiles.md §3.
*%
read_u(W, Op) :- read_in(W, Op), not read_resolved(W, Op).
read_u(W, Op) :- read_resolved(W, Op), not card_ok(W, Op).
read_u(W, Op) :- nonconforming(W, Op).

%*! read_status(W, Op, S)

In world `W`, `Op`'s read is `u` with status `S`: `missing`, `invalid`, `conflict`, or
`unresolved`. The statuses are those of due2-profiles.md §3. A request, witness, or context
source that has no value is `missing`. A state property keeps the status of its fact, and is
`unresolved` when it has none. A resolved read with no value on cardinality `one` is `missing`,
and with several `conflict`. A read of the right number of values with one outside the range is
`invalid`. Only `unresolved` is completed by pairing (completion.lp, decisions/0016).
*%
read_status(W, Op, missing) :- read_in(W, Op), src(Op, Src), Src != state,
    not read_resolved(W, Op).
read_status(W, Op, S) :- read_in(W, Op), src(Op, state), prop(Op, Prop), fact(Prop, S),
    S != resolved.
read_status(W, Op, unresolved) :- read_in(W, Op), src(Op, state), prop(Op, Prop),
    not fact(Prop, _).
read_status(W, Op, missing) :- read_resolved(W, Op), card(Op, one),
    #count { Term : read_value(W, Op, Term) } = 0.
read_status(W, Op, conflict) :- read_resolved(W, Op), card(Op, one),
    #count { Term : read_value(W, Op, Term) } > 1.
read_status(W, Op, invalid) :- card_ok(W, Op), nonconforming(W, Op).
