%# lift.lp: triples to relations, and what the spike does not read
%
% Lifts the policy and module triples to relations that name no IRI, and detects every
% predicate, input field, and value the spike does not read, so that the vector is declined
% instead of answered wrongly (DESIGN.md § Declines). This is the only file that names an
% IRI: every later file reads the relations it provides. Variable letters: DESIGN.md
% § Vocabulary.
%
% - **Consumes:** the driver's facts (DESIGN.md § Input facts): the graphs (`triple/3`,
%   `module/4`, `layer/2`, `pred_ns/2`, `selected_profile/1`), the request (`request_at/1`,
%   `request_param/2`, `request_party/2`), the SOTW (`sotw_effective_at/1`,
%   `fact_value/2`, `evidence/4`, `evidence_param/3`, `signer/2`, `activation/2`,
%   `sotw_closure/3`), the config (`config_combination/1`, `config_violations/1`), and the
%   driver's own findings (`unread/1`, `unplaceable/2`); `policy/1`, `rule/1`,
%   `structure_node/1`, and `action_term/1` (structure.lp); `right/2` (constraint.lp).
% - **Provides:** the vocabulary (`voc/2`, `conflict_value/2`, `policy_class/1`, `function/1`,
%   `match_key/1`, `vocab_ns/1`, `annotation/1`, `annotation_ns/1`, `operator/2`,
%   `set_based/1`, `connective/1`, `binding_key/1`, `source_kind/2`, `context_property/2`,
%   `cardinality_value/2`, `xsd_datatype/1`, `numeric_datatype/1`, `any_literal/1`); the lifted
%   relations (`type/2`, `subclass/2`, `has_rule/3`, `stated/3`, `stated_conflict_iri/2`,
%   `stated_conflict/2`, `profile_conflict/1`, `term/1`, `kind/2`, `list_cell/2`, `list_item/2`,
%   `is_list/1`, `decl/4`, `layer_rank/2`); the hierarchies (`closure_key/1`, `closure/3`,
%   `coll_kind/2`, `node_kind/2`, `le_k/3`); the declines (`policy_predicate/1`,
%   `family_predicate/1`, `anywhere_predicate/1`, `consumed/2`, `annotated/1`, `unsupported/1`,
%   `closure_relation/1`, `unsupported_input/1`, `compared/1`, `unsupported_value/1`); extends
%   `reject/2` (structure.lp).

%## Vocabulary

%*! voc(Key, Pred)

The IRI `Pred` of a term the program reads, under its short name `Key`. Rules match a triple's
predicate against `voc` instead of naming the IRI.

Args:
    - Key: the short name, such as `type` or `permission`.
    - Pred: the full IRI.
*%
voc(type,        "http://www.w3.org/1999/02/22-rdf-syntax-ns#type").
voc(value,       "http://www.w3.org/1999/02/22-rdf-syntax-ns#value").
voc(subclass,    "http://www.w3.org/2000/01/rdf-schema#subClassOf").
voc(uid,         "http://www.w3.org/ns/odrl/2/uid").
voc(profile,     "http://www.w3.org/ns/odrl/2/profile").
voc(conflict,    "http://www.w3.org/ns/odrl/2/conflict").
voc(permission,  "http://www.w3.org/ns/odrl/2/permission").
voc(prohibition, "http://www.w3.org/ns/odrl/2/prohibition").
voc(action,      "http://www.w3.org/ns/odrl/2/action").
voc(target,      "http://www.w3.org/ns/odrl/2/target").
voc(includedIn,  "http://www.w3.org/ns/odrl/2/includedIn").
voc(assignee,    "http://www.w3.org/ns/odrl/2/assignee").
voc(constraint,  "http://www.w3.org/ns/odrl/2/constraint").
voc(refinement,  "http://www.w3.org/ns/odrl/2/refinement").
voc(leftOperand, "http://www.w3.org/ns/odrl/2/leftOperand").
voc(operator,    "http://www.w3.org/ns/odrl/2/operator").
voc(rightOperand, "http://www.w3.org/ns/odrl/2/rightOperand").
voc(unit,        "http://www.w3.org/ns/odrl/2/unit").
voc(and,         "http://www.w3.org/ns/odrl/2/and").
voc(or,          "http://www.w3.org/ns/odrl/2/or").
voc(xone,        "http://www.w3.org/ns/odrl/2/xone").
voc(andSequence, "http://www.w3.org/ns/odrl/2/andSequence").
voc(negation,    "https://ekgf.org/dprod/spec/develop/not").
voc(partOf,      "http://www.w3.org/ns/odrl/2/partOf").
voc(source,      "http://www.w3.org/ns/odrl/2/source").
voc(assetCollection, "http://www.w3.org/ns/odrl/2/AssetCollection").
voc(partyCollection, "http://www.w3.org/ns/odrl/2/PartyCollection").
voc(asset,       "http://www.w3.org/ns/odrl/2/Asset").
voc(party,       "http://www.w3.org/ns/odrl/2/Party").
voc(first,       "http://www.w3.org/1999/02/22-rdf-syntax-ns#first").
voc(rest,        "http://www.w3.org/1999/02/22-rdf-syntax-ns#rest").
voc(nil,         "http://www.w3.org/1999/02/22-rdf-syntax-ns#nil").
voc(operandSource,   "https://ekgf.org/dprod/spec/develop/operandSource").
voc(operandProperty, "https://ekgf.org/dprod/spec/develop/operandProperty").
voc(range,       "http://www.w3.org/2000/01/rdf-schema#range").
voc(cardinality, "https://w3id.org/due2/profile#cardinality").
voc(allowedOperator, "https://w3id.org/due2/profile#allowedOperator").

%*! conflict_value(Iri, Strat)

The `odrl:conflict` value `Iri` names the conflict strategy `Strat`: `prohibit`, `perm`, or
`invalid`.
*%
conflict_value("http://www.w3.org/ns/odrl/2/prohibit", prohibit).
conflict_value("http://www.w3.org/ns/odrl/2/perm",     perm).
conflict_value("http://www.w3.org/ns/odrl/2/invalid",  invalid).

%*! policy_class(Cls)

`Cls` is one of the four ODRL policy classes. A subclass a selected module declares also types a
policy (`policy_type/1`, structure.lp).
*%
policy_class("http://www.w3.org/ns/odrl/2/Policy").
policy_class("http://www.w3.org/ns/odrl/2/Set").
policy_class("http://www.w3.org/ns/odrl/2/Offer").
policy_class("http://www.w3.org/ns/odrl/2/Agreement").

%*! function(F)

`F` is one of the 14 function predicates: the party roles. They are listed in
odrl-compound-to-atomic-normalization.md §3. Each is a family a rule can inherit from its policy.
*%
function("http://www.w3.org/ns/odrl/2/assignee").
function("http://www.w3.org/ns/odrl/2/assigner").
function("http://www.w3.org/ns/odrl/2/attributedParty").
function("http://www.w3.org/ns/odrl/2/attributingParty").
function("http://www.w3.org/ns/odrl/2/compensatedParty").
function("http://www.w3.org/ns/odrl/2/compensatingParty").
function("http://www.w3.org/ns/odrl/2/consentedParty").
function("http://www.w3.org/ns/odrl/2/consentingParty").
function("http://www.w3.org/ns/odrl/2/contractedParty").
function("http://www.w3.org/ns/odrl/2/contractingParty").
function("http://www.w3.org/ns/odrl/2/informedParty").
function("http://www.w3.org/ns/odrl/2/informingParty").
function("http://www.w3.org/ns/odrl/2/trackedParty").
function("http://www.w3.org/ns/odrl/2/trackingParty").

%*! match_key(F)

`F` is a function the request is matched on: in v1 only `odrl:assignee`. The other
functions are carried, not matched (due2-workflows.md §5.2).
*%
match_key("http://www.w3.org/ns/odrl/2/assignee").

%*! vocab_ns(NS)

`NS` is a namespace whose predicates mean something: `odrl:`, `due2:`, and each selected
profile. An unread predicate in one of them declines the vector.
*%
vocab_ns("http://www.w3.org/ns/odrl/2/").
vocab_ns("https://w3id.org/due2/profile#").
vocab_ns(Prof) :- selected_profile(Prof).

%*! annotation(Pred)

`Pred` is on the annotation allowlist: metadata that never changes a verdict, so it declines
nothing.
*%
annotation("http://www.w3.org/2000/01/rdf-schema#label").
annotation("http://www.w3.org/2000/01/rdf-schema#comment").
annotation("http://www.w3.org/2004/02/skos/core#prefLabel").
annotation("http://www.w3.org/2004/02/skos/core#altLabel").
annotation("http://www.w3.org/2004/02/skos/core#hiddenLabel").
annotation("http://www.w3.org/2004/02/skos/core#definition").
annotation("http://www.w3.org/2004/02/skos/core#note").
annotation("https://ekgf.org/dprod/spec/develop/offerLifecycleStatus").
annotation("https://ekgf.org/dprod/spec/develop/contractLifecycleStatus").
annotation("https://ekgf.org/dprod/spec/develop/effectiveDate").
annotation("https://ekgf.org/dprod/spec/develop/expirationDate").
annotation("https://ekgf.org/dprod/spec/develop/acceptsOffer").

%*! annotation_ns(NS)

Every predicate in namespace `NS` (`dct:`, `prov:`) is an annotation.
*%
annotation_ns("http://purl.org/dc/terms/").
annotation_ns("http://www.w3.org/ns/prov#").

%## Constraints

%*! operator(Iri, O)

The operator IRI `Iri` names the core operator `O`. The registry is due2-profiles.md §4; any
other operator IRI is rejected (`UnsupportedOperator`, constraint.lp).
*%
operator("http://www.w3.org/ns/odrl/2/eq",       eq).
operator("http://www.w3.org/ns/odrl/2/neq",      neq).
operator("http://www.w3.org/ns/odrl/2/lt",       lt).
operator("http://www.w3.org/ns/odrl/2/lteq",     lteq).
operator("http://www.w3.org/ns/odrl/2/gt",       gt).
operator("http://www.w3.org/ns/odrl/2/gteq",     gteq).
operator("http://www.w3.org/ns/odrl/2/isAnyOf",  isAnyOf).
operator("http://www.w3.org/ns/odrl/2/isNoneOf", isNoneOf).
operator("http://www.w3.org/ns/odrl/2/isAllOf",  isAllOf).
operator("http://www.w3.org/ns/odrl/2/isPartOf", isPartOf).
operator("http://www.w3.org/ns/odrl/2/hasPart",  hasPart).
operator("http://www.w3.org/ns/odrl/2/isA",      isA).

%*! set_based(O)

`O` is one of the six set-based operators, which take a set right operand: a list or repeated
values. The forms are those of due2-profiles.md §4 and decisions/0013.
*%
set_based(isAnyOf; isNoneOf; isAllOf; isPartOf; hasPart; isA).

%*! connective(K)

`K` names a logical connective: `and`, `or`, `xone`, `negation` (`dprod:not`), or
`andSequence`. These are the connectives of due2-profiles.md §5; `andSequence` is rejected
(constraint.lp).
*%
connective(and; or; xone; negation; andSequence).

%*! binding_key(Key)

`Key` names one attribute of a left operand's binding: its source, its property, its range, its
cardinality, or an allowed operator. The attributes are those of due2-profiles.md §3.
*%
binding_key(operandSource; operandProperty; range; cardinality; allowedOperator).

%*! source_kind(Iri, Src)

The operand source `Iri` is the closed source `Src`: `request`, `state`, `context`, or
`witness`. The sources are those of due2-profiles.md §3.
*%
source_kind("https://ekgf.org/dprod/spec/develop/requestSource", request).
source_kind("https://ekgf.org/dprod/spec/develop/stateSource",   state).
source_kind("https://ekgf.org/dprod/spec/develop/contextSource", context).
source_kind("https://w3id.org/due2/profile#witnessSource",       witness).

%*! context_property(Iri, Key)

The context property `Iri` is the built-in `Key`: `agent`, `clock`, or `actionTime`. The
built-ins are those of due2-profiles.md §3.
*%
context_property("https://ekgf.org/dprod/spec/develop/agent", agent).
context_property("https://ekgf.org/dprod/spec/develop/clock", clock).
context_property("https://w3id.org/due2/profile#actionTime",  actionTime).

%*! cardinality_value(Iri, K)

The cardinality `Iri` is `one` or `set`. See due2-profiles.md §3.
*%
cardinality_value("https://w3id.org/due2/profile#one", one).
cardinality_value("https://w3id.org/due2/profile#set", set).

%*! xsd_datatype(Iri)

`Iri` is a datatype, not a class, as a range: a built-in datatype of XSD or `rdf:langString`.
A range that is not a datatype is a class (due2-profiles.md §3). The built-ins are those of
XSD 1.1.
*%
xsd_datatype("http://www.w3.org/1999/02/22-rdf-syntax-ns#langString").
xsd_datatype("http://www.w3.org/2001/XMLSchema#string").
xsd_datatype("http://www.w3.org/2001/XMLSchema#boolean").
xsd_datatype("http://www.w3.org/2001/XMLSchema#decimal").
xsd_datatype("http://www.w3.org/2001/XMLSchema#float").
xsd_datatype("http://www.w3.org/2001/XMLSchema#double").
xsd_datatype("http://www.w3.org/2001/XMLSchema#duration").
xsd_datatype("http://www.w3.org/2001/XMLSchema#dateTime").
xsd_datatype("http://www.w3.org/2001/XMLSchema#time").
xsd_datatype("http://www.w3.org/2001/XMLSchema#date").
xsd_datatype("http://www.w3.org/2001/XMLSchema#gYearMonth").
xsd_datatype("http://www.w3.org/2001/XMLSchema#gYear").
xsd_datatype("http://www.w3.org/2001/XMLSchema#gMonthDay").
xsd_datatype("http://www.w3.org/2001/XMLSchema#gDay").
xsd_datatype("http://www.w3.org/2001/XMLSchema#gMonth").
xsd_datatype("http://www.w3.org/2001/XMLSchema#hexBinary").
xsd_datatype("http://www.w3.org/2001/XMLSchema#base64Binary").
xsd_datatype("http://www.w3.org/2001/XMLSchema#anyURI").
xsd_datatype("http://www.w3.org/2001/XMLSchema#QName").
xsd_datatype("http://www.w3.org/2001/XMLSchema#NOTATION").
xsd_datatype("http://www.w3.org/2001/XMLSchema#normalizedString").
xsd_datatype("http://www.w3.org/2001/XMLSchema#token").
xsd_datatype("http://www.w3.org/2001/XMLSchema#language").
xsd_datatype("http://www.w3.org/2001/XMLSchema#NMTOKEN").
xsd_datatype("http://www.w3.org/2001/XMLSchema#NMTOKENS").
xsd_datatype("http://www.w3.org/2001/XMLSchema#Name").
xsd_datatype("http://www.w3.org/2001/XMLSchema#NCName").
xsd_datatype("http://www.w3.org/2001/XMLSchema#ID").
xsd_datatype("http://www.w3.org/2001/XMLSchema#IDREF").
xsd_datatype("http://www.w3.org/2001/XMLSchema#IDREFS").
xsd_datatype("http://www.w3.org/2001/XMLSchema#ENTITY").
xsd_datatype("http://www.w3.org/2001/XMLSchema#ENTITIES").
xsd_datatype("http://www.w3.org/2001/XMLSchema#integer").
xsd_datatype("http://www.w3.org/2001/XMLSchema#nonPositiveInteger").
xsd_datatype("http://www.w3.org/2001/XMLSchema#negativeInteger").
xsd_datatype("http://www.w3.org/2001/XMLSchema#long").
xsd_datatype("http://www.w3.org/2001/XMLSchema#int").
xsd_datatype("http://www.w3.org/2001/XMLSchema#short").
xsd_datatype("http://www.w3.org/2001/XMLSchema#byte").
xsd_datatype("http://www.w3.org/2001/XMLSchema#nonNegativeInteger").
xsd_datatype("http://www.w3.org/2001/XMLSchema#unsignedLong").
xsd_datatype("http://www.w3.org/2001/XMLSchema#unsignedInt").
xsd_datatype("http://www.w3.org/2001/XMLSchema#unsignedShort").
xsd_datatype("http://www.w3.org/2001/XMLSchema#unsignedByte").
xsd_datatype("http://www.w3.org/2001/XMLSchema#positiveInteger").
xsd_datatype("http://www.w3.org/2001/XMLSchema#yearMonthDuration").
xsd_datatype("http://www.w3.org/2001/XMLSchema#dayTimeDuration").
xsd_datatype("http://www.w3.org/2001/XMLSchema#dateTimeStamp").
xsd_datatype("http://www.w3.org/2001/XMLSchema#anyAtomicType").
xsd_datatype("http://www.w3.org/2001/XMLSchema#anySimpleType").

%*! numeric_datatype(Iri)

`Iri` is `xsd:decimal` or a datatype derived from it. A numeric range accepts a literal of any of
them that is placed in the numeric space (due2-profiles.md §3, DESIGN.md § Values). `xsd:float`
and `xsd:double` are rejected, so they are not listed.
*%
numeric_datatype("http://www.w3.org/2001/XMLSchema#decimal").
numeric_datatype("http://www.w3.org/2001/XMLSchema#integer").
numeric_datatype("http://www.w3.org/2001/XMLSchema#nonPositiveInteger").
numeric_datatype("http://www.w3.org/2001/XMLSchema#negativeInteger").
numeric_datatype("http://www.w3.org/2001/XMLSchema#long").
numeric_datatype("http://www.w3.org/2001/XMLSchema#int").
numeric_datatype("http://www.w3.org/2001/XMLSchema#short").
numeric_datatype("http://www.w3.org/2001/XMLSchema#byte").
numeric_datatype("http://www.w3.org/2001/XMLSchema#nonNegativeInteger").
numeric_datatype("http://www.w3.org/2001/XMLSchema#unsignedLong").
numeric_datatype("http://www.w3.org/2001/XMLSchema#unsignedInt").
numeric_datatype("http://www.w3.org/2001/XMLSchema#unsignedShort").
numeric_datatype("http://www.w3.org/2001/XMLSchema#unsignedByte").
numeric_datatype("http://www.w3.org/2001/XMLSchema#positiveInteger").

%*! any_literal(Iri)

The range `Iri` accepts any RDF literal: `rdfs:Literal`.
*%
any_literal("http://www.w3.org/2000/01/rdf-schema#Literal").

%*! type(Node, Cls)

The policy graph states `Node rdf:type Cls`.
*%
type(Node, Cls) :- triple(Node, Pred, Cls), voc(type, Pred).

%*! subclass(Cls, Super)

A selected module states `Cls rdfs:subClassOf Super`. Only declared, direct edges: no closure
(odrl-compound-to-atomic-normalization.md §3).
*%
subclass(Cls, Super) :- module(_, Cls, Pred, Super), voc(subclass, Pred).

%*! has_rule(P, R, E)

Node `P` links rule `R` with effect `E`: `permit` for `odrl:permission`, `forbid` for
`odrl:prohibition`. `P` is any node; structure.lp keeps the policy's.
*%
has_rule(P, R, permit) :- triple(P, Pred, R), voc(permission, Pred).
has_rule(P, R, forbid) :- triple(P, Pred, R), voc(prohibition, Pred).

%*! stated(Node, Fam, Term)

`Node` states `Term` for family `Fam`: `action`, `target`, or a function IRI (then `Term` is a
party). Any node; structure.lp reads only the policy's and its rules'.
*%
stated(Node, action, A) :- triple(Node, Pred, A), voc(action, Pred).
stated(Node, target, T) :- triple(Node, Pred, T), voc(target, Pred).
stated(Node, F, Party) :- triple(Node, F, Party), function(F).

%*! stated_conflict_iri(P, Iri)

Node `P` states `odrl:conflict Iri`, whether or not `Iri` is a valid strategy.
*%
stated_conflict_iri(P, Iri) :- triple(P, Pred, Iri), voc(conflict, Pred).

%*! stated_conflict(P, Strat)

Node `P` states the valid conflict strategy `Strat`.
*%
stated_conflict(P, Strat) :- stated_conflict_iri(P, Iri), conflict_value(Iri, Strat).

%*! profile_conflict(Strat)

A selected profile resource sets the default conflict strategy `Strat`. See due2-profiles.md §8.1.
*%
profile_conflict(Strat) :- selected_profile(Prof), module(_, Prof, Pred, Iri), voc(conflict, Pred),
    conflict_value(Iri, Strat).

%*! kind(Term, K)

The RDF term `Term` is an `iri`, a `lit` (an RDF literal), or a `blank` node, by the shape the
driver gives it. The shapes are in DESIGN.md § Input facts. Defined for every term of the
graphs and the inputs the constraints read.
*%
kind(Term, lit) :- term(Term), Term = lit(_, _).
kind(Term, lit) :- term(Term), Term = lit(_, _, _).
kind(Term, blank) :- term(Term), Term = b(_, _).
kind(Term, iri) :- term(Term), not kind(Term, lit), not kind(Term, blank).

%*! term(Term)

`Term` occurs in the policy graph, a selected module, a request value, or a fact value: the
domain of `kind/2`.
*%
term(Term) :- triple(Term, _, _).
term(Term) :- triple(_, _, Term).
term(Term) :- module(_, Term, _, _).
term(Term) :- module(_, _, _, Term).
term(Term) :- request_param(_, Term).
term(Term) :- request_party(_, Term).
term(Term) :- fact_value(_, Term).
term(Term) :- sotw_effective_at(Term).
term(Term) :- request_at(Term).

%*! list_cell(Head, Cell)

`Cell` is a cell of the RDF list that starts at `Head`, in the policy graph. A list's items
are its cells' `rdf:first` values.
*%
list_cell(Head, Head) :- triple(Head, Pred, _), voc(first, Pred).
list_cell(Head, Cell) :- list_cell(Head, Prev), triple(Prev, Pred, Cell), voc(rest, Pred),
    triple(Cell, First, _), voc(first, First).

%*! list_item(Head, Item)

`Item` is an item of the RDF list `Head`.
*%
list_item(Head, Item) :- list_cell(Head, Cell), triple(Cell, Pred, Item), voc(first, Pred).

%*! is_list(Node)

`Node` is an RDF list: a list cell, or `rdf:nil`, the empty list.
*%
is_list(Node) :- list_cell(Node, Node).
is_list(Node) :- voc(nil, Node).

%*! decl(Layer, Op, Key, Value)

Layer `Layer` declares `Value` for attribute `Key` of left operand `Op`'s binding
(`binding_key/1`). `Layer` is `policy` for the policy graph, or a module path (`layer/2`).
*%
decl(policy, Op, Key, Value) :- triple(Op, Pred, Value), voc(Key, Pred), binding_key(Key).
decl(Path, Op, Key, Value) :- module(Path, Op, Pred, Value), voc(Key, Pred), binding_key(Key).

%*! layer_rank(Layer, N)

Layer `Layer` has precedence `N`, lowest first: the policy graph 0, the selected profile
modules 1, and the core modules 2. That is the layer precedence of due2-profiles.md §2.
*%
layer_rank(policy, 0).
layer_rank(Path, 1) :- layer(Path, profile).
layer_rank(Path, 2) :- layer(Path, core).

%## Hierarchies

%*! closure_key(Key)

`Key` names a hierarchy the spike reads: `includedIn` (actions), `partOf` (assets and parties),
`type`, and `subclass` (`isA`). See due2-profiles.md §6.
*%
closure_key(includedIn; partOf; type; subclass).

%*! closure(Key, Lo, Hi)

A declared `Key` edge from `Lo` to the broader `Hi`, from the policy, a selected module, or the
SOTW closure. The edges are closed-world: an undeclared edge does not hold (due2-profiles.md
§6).
*%
closure(Key, Lo, Hi) :- triple(Lo, Pred, Hi), voc(Key, Pred), closure_key(Key).
closure(Key, Lo, Hi) :- module(_, Lo, Pred, Hi), voc(Key, Pred), closure_key(Key).
closure(Key, Lo, Hi) :- sotw_closure(Pred, Lo, Hi), voc(Key, Pred), closure_key(Key).

%*! coll_kind(Node, K)

`Node` is a collection of kind `K`: an `odrl:AssetCollection` is `asset`, an
`odrl:PartyCollection` is `party`.
*%
coll_kind(Node, asset) :- closure(type, Node, Cls), voc(assetCollection, Cls).
coll_kind(Node, party) :- closure(type, Node, Cls), voc(partyCollection, Cls).

%*! node_kind(Node, K)

`Node` is of kind `K`: a collection of that kind, or typed `odrl:Asset` or `odrl:Party`.
*%
node_kind(Node, K) :- coll_kind(Node, K).
node_kind(Node, asset) :- closure(type, Node, Cls), voc(asset, Cls).
node_kind(Node, party) :- closure(type, Node, Cls), voc(party, Cls).

%*! le_k(Lo, Hi, K)

`Lo` is part of the collection `Hi` of kind `K`: the transitive `odrl:partOf` closure, through
collections of kind `K` only. That is the typed `partOf` of due2-profiles.md §6. Not reflexive: the
matchers add identity.
*%
le_k(Lo, Hi, K) :- closure(partOf, Lo, Hi), coll_kind(Hi, K).
le_k(Lo, Hi, K) :- le_k(Lo, Mid, K), closure(partOf, Mid, Hi), coll_kind(Hi, K).

% A path may pass only through collections of one kind, and a cross-kind path is invalid
% (due2-profiles.md §6). An edge into an untyped node, or across kinds, has no reading the spike
% trusts, so it is declined.
unsupported("odrl:partOf: untyped collection") :- closure(partOf, _, Hi), not coll_kind(Hi, _).
unsupported("odrl:partOf: untyped collection") :- closure(partOf, _, Hi), coll_kind(Hi, asset),
    coll_kind(Hi, party).
unsupported("odrl:partOf: cross-kind edge") :- closure(partOf, Lo, Hi), node_kind(Lo, K),
    coll_kind(Hi, K2), K != K2.
% odrl:source on a collection names where its members come from; the spike reads membership
% only from the partOf edges, so it is inert there. Elsewhere it is not admissible, and neither
% is a collection's refinement (due2-diagnostics.md, UnsupportedConstruct).
reject("UnsupportedConstruct", Node) :- triple(Node, Pred, _), voc(source, Pred),
    not coll_kind(Node, _).
reject("UnsupportedConstruct", Node) :- triple(Node, Pred, _), voc(refinement, Pred),
    coll_kind(Node, _).

%## What the spike does not read

%*! policy_predicate(Key)

`Key` names a predicate the spike reads on the policy node only.
*%
policy_predicate(profile; conflict; permission; prohibition).

%*! family_predicate(Key)

`Key` names a family predicate, read on the policy and its rules.
*%
family_predicate(action; target).

%*! anywhere_predicate(Key)

`Key` names a predicate the spike reads on any node: the hierarchy edge, the constraint
predicates, the connectives (`andSequence` so that it is rejected, not declined), and the
binding attributes.
*%
% odrl:unit labels the right operand and joins the completion key (due2-workflows.md §6.4). It
% converts nothing, so a comparison reads the values alone.
anywhere_predicate(includedIn; partOf; source; leftOperand; operator; rightOperand; unit).
anywhere_predicate(Key) :- connective(Key).
anywhere_predicate(Key) :- binding_key(Key).

%*! consumed(Node, Pred)

The spike reads predicate `Pred` on `Node`, so it declines nothing there. The table of what it
reads is in DESIGN.md § Declines.
*%
consumed(Node, Pred) :- triple(Node, Pred, _), voc(type, Pred).
consumed(Node, Pred) :- triple(Node, Pred, Node), voc(uid, Pred).
consumed(Node, Pred) :- triple(Node, Pred, _), policy(Node), voc(Key, Pred), policy_predicate(Key).
% The families are consumed on every node, not only on the policy and its rules. Anywhere else
% they hang under a link that is itself declined (odrl:duty, odrl:refinement) or off the policy,
% so declining on them would name the family instead of the feature.
consumed(Node, Pred) :- triple(Node, Pred, _), voc(Key, Pred), family_predicate(Key).
consumed(Node, Pred) :- triple(Node, Pred, _), function(Pred).
consumed(Node, Pred) :- triple(Node, Pred, _), voc(Key, Pred), anywhere_predicate(Key).
consumed(Node, Pred) :- triple(Node, Pred, _), voc(constraint, Pred), rule(Node).
consumed(Node, Pred) :- triple(Node, Pred, _), voc(refinement, Pred), action_term(Node).
consumed(Node, Pred) :- triple(Node, Pred, _), voc(refinement, Pred), coll_kind(Node, _).
consumed(Node, Pred) :- triple(Node, Pred, _), voc(value, Pred), action_term(Node).

%*! annotated(Pred)

`Pred` is an annotation, by name or by namespace.
*%
annotated(Pred) :- annotation(Pred).
annotated(Pred) :- pred_ns(Pred, NS), annotation_ns(NS).

%*! unsupported(Feature)

The vector uses `Feature`, which the spike does not read, so solve 1 declines it, naming the
smallest `Feature`. Here `Feature` is a predicate IRI, or a reason for a hierarchy the
spike does not trust (`"odrl:partOf: …"`). structure.lp, constraint.lp, and operand.lp add
reasons of their own, listed in DESIGN.md § Declines.
*%
% Neither consumed nor annotated, and either in a vocabulary namespace or on the policy or a
% rule. On other nodes (assets, parties) a foreign predicate is data the spike never reads.
unsupported(Pred) :- triple(Node, Pred, _), not consumed(Node, Pred), not annotated(Pred),
    pred_ns(Pred, NS), vocab_ns(NS).
unsupported(Pred) :- triple(Node, Pred, _), not consumed(Node, Pred), not annotated(Pred),
    structure_node(Node).
% rdf:value is read only on an action node (IM 2.2 §2.5): anywhere else it declines.
unsupported(Pred) :- triple(Node, Pred, _), voc(value, Pred), not action_term(Node).

%## The input fields the spike does not read

%*! closure_relation(Pred)

`Pred` is a hierarchy relation the spike reads (`closure_key/1`). A SOTW closure edge of any
other relation declines the vector.
*%
closure_relation(Pred) :- voc(Key, Pred), closure_key(Key).

%*! unsupported_input(Field)

The input field `Field` has content the spike does not read, so the vector is declined, naming
the smallest `Field`. An empty field gives no facts, so it declines nothing.
*%
unsupported_input("sotw.evidence") :- evidence(_, _, _, _).
unsupported_input("sotw.activation") :- activation(_, _).
unsupported_input("sotw.closure") :- sotw_closure(Pred, _, _), not closure_relation(Pred).
unsupported_input("config.combination") :- config_combination(Comb), Comb != "prohibit-overrides".
unsupported_input("config.violations") :- config_violations(_).
unsupported_input("config.signers") :- signer(_, _).
unsupported_input(Field) :- unread(Field).

%## The values the program compares

%*! compared(Lit)

The program compares the RDF literal `Lit`, so it needs `Lit`'s position. These are the input
instants and input values, whose positions the spec fixes (DESIGN.md § Values).
*%
compared(Lit) :- request_at(Lit).
compared(Lit) :- sotw_effective_at(Lit).
compared(Lit) :- activation(_, Lit).
compared(Lit) :- evidence(_, Lit, _, _).
compared(Lit) :- request_param(_, Lit).
compared(Lit) :- fact_value(_, Lit).
compared(Lit) :- evidence_param(_, _, Lit).
compared(Lit) :- right(_, Lit).

%*! unsupported_value(Reason)

A compared RDF literal cannot be placed, for `Reason`, so the vector is declined. An
unplaceable literal the program never compares declines nothing (DESIGN.md § Values).
*%
unsupported_value(Reason) :- unplaceable(Lit, Reason), compared(Lit).
