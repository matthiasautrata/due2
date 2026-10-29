%# lift.lp: triples to relations, and what the spike does not read
%
% Lifts the policy and module triples to relations that name no IRI, and detects every
% predicate, input field, and value the spike does not read, so that the vector is declined
% instead of answered wrongly (DESIGN.md § Declines). This is the only file that names an
% IRI: every later file reads the relations it provides. Variable letters: DESIGN.md
% § Vocabulary.
%
% - **Consumes:** the driver's facts (flatten.py): the graphs (`triple/3`,
%   `text_triple/4`, `module/4`, `layer/2`, `pred_ns/2`, `selected_profile/1`), the request
%   (`request_at/1`, `request_param/2`, `request_party/2`, `request_target/1`), the SOTW
%   (`sotw_effective_at/1`, `fact_answer/3`, `fact_answer_value/3`, `evidence/4`,
%   `evidence_param/3`, `evidence_issuer/2`, `activation/2`, `sotw_closure/3`), and the driver's
%   own finding `unplaceable/2`; `policy/1`, `rule/1`, `structure_node/1`, `action_term/1`,
%   `duty_node/1`, `pre_rule/2`, `node_deadline/2`, `atom_target/2`, `atom_party/3`, `bearer/2`,
%   `attester/2`, and `space/2` (structure.lp); `right/2`, `op/2`, and `node_space/2`
%   (constraint.lp); `cpair/5` (compare.lp).
% - **Provides:** the vocabulary (`voc/2`, `conflict_value/2`, `policy_class/1`, `function/1`,
%   `match_key/1`, `bearer_fn/1`, `attester_fn/1`, `vocab_ns/1`, `annotation/1`,
%   `annotation_ns/1`, `operator/2`,
%   `set_based/1`, `connective/1`, `binding_key/1`, `source_kind/2`, `context_property/2`,
%   `cardinality_value/2`, `xsd_datatype/1`, `numeric_datatype/1`, `any_literal/1`,
%   `any_resource/1`, `floating_datatype/1`, `derived_from/2`); the lifted relations (`type/2`,
%   `subclass/2`, `has_rule/3`, `stated/3`, `stated_conflict_iri/2`, `stated_conflict/2`,
%   `term/1`, `kind/2`, `list_cell/2`, `list_item/2`, `is_list/1`); the combined facts
%   (`valued/2`, `differs/1`, `fact/2`, `fact_value/2`); the kinds (`declared_datatype/1`,
%   `datatype/1`, `dt_kind/2`, `term_kind/2`); the hierarchies
%   (`closure_key/1`, `hierarchy_predicate/1`, `policy_text/2`, `policy_layer/2`, `edge/4`,
%   `closure/4`, `declared_in_scheme/2`, `coll_kind/3`, `node_kind/3`, `le_k/4`, `collection/1`,
%   `compares/3`, `part_up/3`, `part_down/3`, `walked/3`); the declines (`policy_predicate/1`,
%   `family_predicate/1`, `anywhere_predicate/1`, `timing_predicate/1`, `consumed/2`,
%   `annotated/1`, `unsupported/1`, `closure_relation/1`, `unsupported_input/1`, `compared/1`,
%   `input_instant/1`, `off_shape/1`, `unsupported_value/1`); extends `reject/2` (structure.lp).

%## Vocabulary

% `voc/2` maps each short name to its IRI. The registries list the conflict strategies, the policy
% classes, the 14 function predicates of odrl-compound-to-atomic-normalization.md §3, the match keys
% (due2-workflows.md §5.2; v1 has one, `odrl:assignee`), the 12 core operators of due2-profiles.md
% §4 (`operator/2`, six of them `set_based/1`), the connectives (`connective/1`), the binding
% attributes, sources, context built-ins, and cardinalities of due2-profiles.md §3, the XSD
% datatypes a range can name (`xsd_datatype/1`, `numeric_datatype/1`, `floating_datatype/1`,
% `derived_from/2`), and the two RDF Schema classes that admit values of several kinds
% (`any_literal/1`, `any_resource/1`).

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
voc(datatype,    "http://www.w3.org/2000/01/rdf-schema#Datatype").
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
voc(isReplacedBy, "http://purl.org/dc/terms/isReplacedBy").
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
voc(operandUnit, "https://w3id.org/due2/profile#unit").
voc(cardinality, "https://w3id.org/due2/profile#cardinality").
voc(allowedOperator, "https://w3id.org/due2/profile#allowedOperator").
voc(conceptScheme, "https://w3id.org/due2/profile#conceptScheme").
voc(broader,     "http://www.w3.org/2004/02/skos/core#broader").
voc(narrower,    "http://www.w3.org/2004/02/skos/core#narrower").
voc(inScheme,    "http://www.w3.org/2004/02/skos/core#inScheme").
voc(topConceptOf, "http://www.w3.org/2004/02/skos/core#topConceptOf").
voc(hasTopConcept, "http://www.w3.org/2004/02/skos/core#hasTopConcept").
voc(obligation,  "http://www.w3.org/ns/odrl/2/obligation").
voc(duty,        "http://www.w3.org/ns/odrl/2/duty").
voc(output,      "http://www.w3.org/ns/odrl/2/output").
voc(deadline,    "https://ekgf.org/dprod/spec/develop/deadline").
voc(recurrence,  "https://ekgf.org/dprod/spec/develop/recurrence").
voc(playsRole,   "https://w3id.org/due2/profile#playsRole").
voc(bearer,      "https://w3id.org/due2/profile#bearer").
voc(attester,    "https://w3id.org/due2/profile#attester").
voc(instanceScope, "https://w3id.org/due2/profile#instanceScope").
voc(member,      "https://w3id.org/due2/profile#member").
voc(grant,       "https://w3id.org/due2/profile#grant").
voc(xsd_dateTime, "http://www.w3.org/2001/XMLSchema#dateTime").
voc(xsd_duration, "http://www.w3.org/2001/XMLSchema#duration").

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

`F` is a function predicate: a party role. These are the 14 of
odrl-compound-to-atomic-normalization.md §3, and each property a selected module gives a role with
`due2:playsRole`, as profiles/dprod.ttl gives `dprod:subjectOfDuty` (due2-profiles.md §6). Each is
a family a rule can inherit from its policy.
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
function(F) :- module(_, F, Pred, _), voc(playsRole, Pred).

%*! bearer_fn(F)

The function `F` plays the bearer role: a selected module states `F due2:playsRole due2:bearer`.
The baseline gives it to `odrl:assignee`, DPROD to `dprod:subjectOfDuty` (due2-profiles.md §6).
The bearer of a duty must perform it (due2-workflows.md §5.3).
*%
bearer_fn(F) :- function(F), module(_, F, Pred, Role), voc(playsRole, Pred), voc(bearer, Role).

%*! attester_fn(F)

The function `F` plays the attester role: a selected module states `F due2:playsRole
due2:attester`. The core profile gives it to `due2:attestingParty` (due2-profiles.md §6). Only
evidence whose issuer is at or below a duty's attester counts for the duty (due2-workflows.md
§5.3).
*%
attester_fn(F) :- function(F), module(_, F, Pred, Role), voc(playsRole, Pred), voc(attester, Role).

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
unit (`due2:unit`), its cardinality, or an allowed operator. The attributes are those of
due2-profiles.md §3.
*%
binding_key(operandSource; operandProperty; range; operandUnit; cardinality; allowedOperator).

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

`Iri` is `xsd:decimal` or a datatype derived from it. With `xsd:float` and `xsd:double`
(`floating_datatype/1`) they make the numeric kind (due2-profiles.md §3 Kinds).
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

%*! any_resource(Iri)

The range `Iri` accepts any RDF term, since it is `rdfs:Resource`. RDF Schema 1.1 §2.1 makes
it the class of everything.
*%
any_resource("http://www.w3.org/2000/01/rdf-schema#Resource").

%*! floating_datatype(Iri)

`Iri` is `xsd:float` or `xsd:double`. They are numeric, but a value of either declines
(values.py), and a right operand of either is rejected (due2-profiles.md §4).
*%
floating_datatype("http://www.w3.org/2001/XMLSchema#float").
floating_datatype("http://www.w3.org/2001/XMLSchema#double").

%*! derived_from(Dt, Prim)

The XSD datatype `Dt` is derived from the primitive `Prim` by restriction, so it has `Prim`'s
kind. The derivations are those of XSD 1.1 Part 2 §3.3-3.4. The numeric types are one kind of their own (`numeric_datatype/1`).
The list types `xsd:NMTOKENS`, `xsd:IDREFS`, and `xsd:ENTITIES` are not derived by restriction,
so they are kinds of their own.
*%
derived_from("http://www.w3.org/2001/XMLSchema#normalizedString", "http://www.w3.org/2001/XMLSchema#string").
derived_from("http://www.w3.org/2001/XMLSchema#token", "http://www.w3.org/2001/XMLSchema#string").
derived_from("http://www.w3.org/2001/XMLSchema#language", "http://www.w3.org/2001/XMLSchema#string").
derived_from("http://www.w3.org/2001/XMLSchema#NMTOKEN", "http://www.w3.org/2001/XMLSchema#string").
derived_from("http://www.w3.org/2001/XMLSchema#Name", "http://www.w3.org/2001/XMLSchema#string").
derived_from("http://www.w3.org/2001/XMLSchema#NCName", "http://www.w3.org/2001/XMLSchema#string").
derived_from("http://www.w3.org/2001/XMLSchema#ID", "http://www.w3.org/2001/XMLSchema#string").
derived_from("http://www.w3.org/2001/XMLSchema#IDREF", "http://www.w3.org/2001/XMLSchema#string").
derived_from("http://www.w3.org/2001/XMLSchema#ENTITY", "http://www.w3.org/2001/XMLSchema#string").
derived_from("http://www.w3.org/2001/XMLSchema#dateTimeStamp", "http://www.w3.org/2001/XMLSchema#dateTime").
derived_from("http://www.w3.org/2001/XMLSchema#dayTimeDuration", "http://www.w3.org/2001/XMLSchema#duration").
derived_from("http://www.w3.org/2001/XMLSchema#yearMonthDuration", "http://www.w3.org/2001/XMLSchema#duration").

%## The lifted policy

% The lifted policy is `type/2`, `subclass/2` (declared, direct edges from the selected modules),
% `has_rule/3`, `stated/3` (the value a policy or rule node states for a family), and
% `stated_conflict/2`.
%
% Terms and lists: `term/1` collects every term of the graphs and of the inputs the constraints
% read, and `kind/2` gives each its shape: `iri`, `lit`, or `blank`. `list_cell/2`, `list_item/2`,
% and `is_list/1` read RDF lists of the policy graph; `rdf:nil` is the empty list.

%*! type(Node, Cls)

The policy graph states `Node rdf:type Cls`.
*%
type(Node, Cls) :- triple(Node, Pred, Cls), voc(type, Pred).

%*! subclass(Cls, Super)

A selected module states `Cls rdfs:subClassOf Super`. Only declared, direct edges: no closure
(odrl-compound-to-atomic-normalization.md §3).
*%
subclass(Cls, Super) :- module(_, Cls, Pred, Super), voc(subclass, Pred).

%*! has_rule(P, R, Eff)

Node `P` links rule `R` with effect `Eff`: `permit` for `odrl:permission`, `forbid` for
`odrl:prohibition`. `P` is any node; structure.lp keeps the policy's.
*%
has_rule(P, R, permit) :- triple(P, Pred, R), voc(permission, Pred).
has_rule(P, R, forbid) :- triple(P, Pred, R), voc(prohibition, Pred).

%*! stated(Node, Fam, Term)

`Node` states `Term` for `Fam`: `action`, `target`, `output`, or a function IRI (then `Term` is a
party). Any node; structure.lp reads only those of the policy, its rules, and its duties, and
`output` only on a duty.
*%
stated(Node, action, A) :- triple(Node, Pred, A), voc(action, Pred).
stated(Node, target, T) :- triple(Node, Pred, T), voc(target, Pred).
stated(Node, output, T) :- triple(Node, Pred, T), voc(output, Pred).
stated(Node, F, Party) :- triple(Node, F, Party), function(F).

%*! stated_conflict_iri(P, Iri)

Node `P` states `odrl:conflict Iri`, whether or not `Iri` is a valid strategy.
*%
stated_conflict_iri(P, Iri) :- triple(P, Pred, Iri), voc(conflict, Pred).

%*! stated_conflict(P, Strat)

Node `P` states the valid conflict strategy `Strat`.
*%
stated_conflict(P, Strat) :- stated_conflict_iri(P, Iri), conflict_value(Iri, Strat).

%*! kind(Term, K)

The RDF term `Term` is an `iri`, a `lit` (an RDF literal), or a `blank` node, by the shape the
driver gives it. The shapes are in flatten.py. Defined for every term of the
graphs and the inputs the constraints read.
*%
kind(Term, lit) :- term(Term), Term = lit(_, _).
kind(Term, lit) :- term(Term), Term = lit(_, _, _).
kind(Term, blank) :- term(Term), Term = b(_, _).
kind(Term, iri) :- term(Term), not kind(Term, lit), not kind(Term, blank).

%*! term(Term)

`Term` occurs in the policy graph, a selected module, a request value, a fact value, or an
evidence value: the domain of `kind/2`.
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
term(Term) :- evidence(_, Term, _, _).
term(Term) :- evidence_param(_, _, Term).

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

%## Kinds

% `dt_kind(Dt, K)` gives a datatype's kind (due2-profiles.md §3 *Kinds*): `numeric` for every XSD
% numeric type, the primitive for a derived XSD type, and the datatype itself otherwise.
% `term_kind(Term, K)` gives a term's kind, `iri` for an IRI. bind.lp gives the kind a stated
% range admits (`admits_kind/2`).

%*! declared_datatype(Dt)

`Dt` is typed `rdfs:Datatype` in the policy graph or a selected module: a datatype outside XSD.
*%
declared_datatype(Dt) :- triple(Dt, Pred, Cls), voc(type, Pred), voc(datatype, Cls).
declared_datatype(Dt) :- module(_, Dt, Pred, Cls), voc(type, Pred), voc(datatype, Cls).

%*! datatype(Dt)

`Dt` is a datatype: an XSD built-in or `rdf:langString`, a declared datatype, or the datatype of
a literal among the terms. It is the domain of `dt_kind/2`.
*%
datatype(Dt) :- xsd_datatype(Dt).
datatype(Dt) :- declared_datatype(Dt).
datatype(Dt) :- term(lit(_, Dt)).
datatype(Dt) :- term(lit(_, Dt, _)).

%*! dt_kind(Dt, K)

The datatype `Dt` has kind `K`, which says what its values can be compared with. Kinds are
defined in due2-profiles.md §3. The kind is `numeric` for every XSD numeric type, the primitive for a
derived XSD type, and `Dt` itself otherwise, `rdf:langString` and every datatype outside XSD
included.
*%
dt_kind(Dt, numeric) :- datatype(Dt), numeric_datatype(Dt).
dt_kind(Dt, numeric) :- datatype(Dt), floating_datatype(Dt).
dt_kind(Dt, Prim) :- datatype(Dt), derived_from(Dt, Prim).
dt_kind(Dt, Dt) :- datatype(Dt), not numeric_datatype(Dt), not floating_datatype(Dt),
    not derived_from(Dt, _).

%*! term_kind(Term, K)

The term `Term` has kind `K`: `iri` for an IRI, its datatype's kind for a literal. A blank node
has no kind.
*%
term_kind(Term, iri) :- kind(Term, iri).
term_kind(Term, K) :- term(Term), Term = lit(_, Dt), dt_kind(Dt, K).
term_kind(Term, K) :- term(Term), Term = lit(_, Dt, _), dt_kind(Dt, K).

%## Several sources

% A state property may have several answers, one per source (due2-workflows.md §3.3, *Several
% sources*; decisions/0040). The program reads one status and one set of values per property, so
% this section combines the answers: those with values decide, and a disagreement among them is a
% `conflict`. The SOTW names no source in a case whose fact is one answer; the driver then names
% it `unnamed`, and the combination of one answer is that answer.

%*! valued(Prop, Source)

`Source`'s answer for `Prop` has values: its status is `resolved`, possibly with no value, or
`conflict`.
*%
valued(Prop, Source) :- fact_answer(Prop, Source, resolved).
valued(Prop, Source) :- fact_answer(Prop, Source, conflict).

%*! differs(Prop)

Two answers for `Prop` that have values differ: one holds a value the other lacks. Values are
compared as sets of written terms, so a `resolved` answer with no value differs from one with a
value.
*%
differs(Prop) :- valued(Prop, Source), valued(Prop, Other),
    fact_answer_value(Prop, Source, Value), not fact_answer_value(Prop, Other, Value).

%*! fact(Prop, S)

The combined status of the answers for the state property `Prop`. If some answer has values, it
is `resolved` when every such answer is `resolved` with the same values, and `conflict`
otherwise. If none has, it is the first of `unresolved`, `invalid`, and `missing` that some
answer has. A property with no answer has no `fact`, and operand.lp reads it as `unresolved`.
*%
fact(Prop, conflict) :- fact_answer(Prop, _, conflict).
fact(Prop, conflict) :- differs(Prop).
% `resolved` restates the two `conflict` rules' bodies rather than reading `not fact(Prop,
% conflict)`, so `fact/2` does not depend negatively on itself and the program stays stratified.
fact(Prop, resolved) :- valued(Prop, _), not fact_answer(Prop, _, conflict), not differs(Prop).
fact(Prop, unresolved) :- fact_answer(Prop, _, unresolved), not valued(Prop, _).
fact(Prop, invalid) :- fact_answer(Prop, _, invalid), not valued(Prop, _),
    not fact_answer(Prop, _, unresolved).
fact(Prop, missing) :- fact_answer(Prop, _, missing), not valued(Prop, _),
    not fact_answer(Prop, _, unresolved), not fact_answer(Prop, _, invalid).

%*! fact_value(Prop, Value)

`Value` is one of the combined values of `Prop`: a value of an answer that has values. Answers
without values are ignored.
*%
fact_value(Prop, Value) :- valued(Prop, Source), fact_answer_value(Prop, Source, Value).

%## Hierarchies

% A policy is its own data space (decisions/0050 #1): what the program derives for policy `P`
% reads only `P`'s own text, the core and the modules of the profiles `P` names, and the SOTW.
% So every hierarchy is keyed by its policy. `closure(P, Key, Lo, Hi)` holds each declared
% `includedIn`, `partOf`, `rdf:type`, `rdfs:subClassOf`, `skos:broader`, or `skos:inScheme` edge
% that `P`'s data space states (`edge/4`), and every edge of the SOTW closure, which every policy
% reads. A `skos:narrower` triple is the inverse `broader` edge, and `skos:topConceptOf` and the
% inverse `skos:hasTopConcept` are `inScheme` edges (decisions/0015 #5, #8). The edges are
% closed-world: an undeclared edge does not hold (due2-profiles.md §6). Edges that another
% policy's text states, or a profile that `P` does not name, never reach `P`, even when that
% policy and `P` are evaluated together (`test_policy_reads_only_its_own_edges`).
%
% `declared_in_scheme/2` holds the memberships that some text or module declares, for the checks
% of normalisation (operand.lp), which run on one text at a time. bind.lp reads each
% `due2:conceptScheme` a layer states (`concept_scheme/2`).
%
% `coll_kind(P, Node, K)` types a collection in `P`'s data space (`odrl:AssetCollection` is
% `asset`, `odrl:PartyCollection` is `party`), and `node_kind/3` also types an `odrl:Asset` or
% `odrl:Party`. `le_k(P, Lo, Hi, K)` is the typed `partOf` of due2-profiles.md §6 in `P`'s data
% space: the transitive closure through collections of kind `K` only. It is not reflexive; its
% readers add identity.
%
% The readers of the hierarchies are keyed by policy too, and each node is read in the data spaces
% of its policies: an atom in `space/2` (structure.lp), a constraint node in `cspace/2`
% (constraint.lp). A node that is in two policies is read in each, and each reading gives that
% entry's finding (due2-workflows.md §3.3, §6.2 *Entries*).

%*! closure_key(Key)

`Key` names a hierarchy the spike reads: `includedIn` (actions), `partOf` (assets and parties),
`type`, and `subclass` (`isA`), `broader` and `inScheme` (concepts). See due2-profiles.md §6 and
decisions/0015.
*%
closure_key(includedIn; partOf; type; subclass; broader; inScheme).

%*! hierarchy_predicate(Pred)

`Pred` is the IRI of a predicate that states a hierarchy edge: one of `closure_key/1`, or
`skos:narrower`, `skos:topConceptOf`, or `skos:hasTopConcept`.
*%
hierarchy_predicate(Pred) :- voc(Key, Pred), closure_key(Key).
hierarchy_predicate(Pred) :- voc((narrower; topConceptOf; hasTopConcept), Pred).

%*! policy_text(P, Text)

Policy `P` is stated by the policy text `Text`: the text has a triple about `P`. A policy that two
agreeing texts state is stated by both (due2-workflows.md §4).
*%
policy_text(P, Text) :- policy(P), text_triple(Text, P, _, _).

%*! policy_layer(P, Path)

The module at `Path` is in policy `P`'s data space: a core module, or a module of a profile that
`P` names with `odrl:profile`. A profile named by another policy is not in it.
*%
policy_layer(P, Path) :- policy(P), layer(Path, core).
policy_layer(P, Path) :- policy(P), layer(Path, module(Iri)), triple(P, Pred, Iri),
    voc(profile, Pred).

%*! edge(P, S, Pred, O)

Policy `P`'s data space states the hierarchy triple `S Pred O`: a text that states `P`, or a
module in `P`'s layers, has it.
*%
edge(P, S, Pred, O) :- policy_text(P, Text), text_triple(Text, S, Pred, O),
    hierarchy_predicate(Pred).
edge(P, S, Pred, O) :- policy_layer(P, Path), module(Path, S, Pred, O), hierarchy_predicate(Pred).

%*! closure(P, Key, Lo, Hi)

In policy `P`'s data space, a declared `Key` edge leads from `Lo` to the broader `Hi`: an edge of
`P`'s text or layers, or of the SOTW closure. The edges are closed-world: an undeclared edge
does not hold (due2-profiles.md §6).
*%
closure(P, Key, Lo, Hi) :- edge(P, Lo, Pred, Hi), voc(Key, Pred), closure_key(Key).
closure(P, Key, Lo, Hi) :- policy(P), sotw_closure(Pred, Lo, Hi), voc(Key, Pred),
    closure_key(Key).
% A `skos:narrower` triple is the inverse `skos:broader` edge (decisions/0015 #5). The SOTW
% states its edges in one orientation, so it gives `skos:broader` only.
closure(P, broader, Lo, Hi) :- edge(P, Hi, Pred, Lo), voc(narrower, Pred).
closure(P, inScheme, C, S) :- edge(P, C, Pred, S), voc(topConceptOf, Pred).
closure(P, inScheme, C, S) :- edge(P, S, Pred, C), voc(hasTopConcept, Pred).

%*! declared_in_scheme(C, S)

A policy text or a selected module states that concept `C` is in scheme `S`: by
`skos:inScheme`, by its sub-property `skos:topConceptOf`, or by the inverse
`skos:hasTopConcept` (SKOS Reference S7, S8). Membership is not inherited along `skos:broader`.
Normalisation checks right operands against these memberships alone, since it does not see the
SOTW (decisions/0015 #8). It runs in solve 0, on one text and its own layers, so these are that
text's memberships. `closure(P, inScheme, C, S)` adds the SOTW's.
*%
declared_in_scheme(C, S) :- triple(C, Pred, S), voc((inScheme; topConceptOf), Pred).
declared_in_scheme(C, S) :- module(_, C, Pred, S), voc((inScheme; topConceptOf), Pred).
declared_in_scheme(C, S) :- triple(S, Pred, C), voc(hasTopConcept, Pred).
declared_in_scheme(C, S) :- module(_, S, Pred, C), voc(hasTopConcept, Pred).

%*! coll_kind(P, Node, K)

In policy `P`'s data space, `Node` is a collection of kind `K`: an `odrl:AssetCollection` is
`asset`, an `odrl:PartyCollection` is `party`.
*%
coll_kind(P, Node, asset) :- closure(P, type, Node, Cls), voc(assetCollection, Cls).
coll_kind(P, Node, party) :- closure(P, type, Node, Cls), voc(partyCollection, Cls).

%*! node_kind(P, Node, K)

In policy `P`'s data space, `Node` is of kind `K`: a collection of that kind, or typed
`odrl:Asset` or `odrl:Party`.
*%
node_kind(P, Node, K) :- coll_kind(P, Node, K).
node_kind(P, Node, asset) :- closure(P, type, Node, Cls), voc(asset, Cls).
node_kind(P, Node, party) :- closure(P, type, Node, Cls), voc(party, Cls).

%*! le_k(P, Lo, Hi, K)

In policy `P`'s data space, `Lo` is part of the collection `Hi` of kind `K`: the transitive
`odrl:partOf` closure, through collections of kind `K` only. That is the typed `partOf` of
due2-profiles.md §6. Not reflexive: the matchers add identity.
*%
le_k(P, Lo, Hi, K) :- closure(P, partOf, Lo, Hi), coll_kind(P, Hi, K).
le_k(P, Lo, Hi, K) :- le_k(P, Lo, Mid, K), closure(P, partOf, Mid, Hi), coll_kind(P, Hi, K).

%*! collection(Node)

Some text, selected module, or SOTW edge types `Node` as an asset or party collection. The
`odrl:source` and refinement rejections and `consumed/2` read it, since a text is checked
whatever policy it states.
*%
collection(Node) :- triple(Node, Pred, Cls), voc(type, Pred),
    voc((assetCollection; partyCollection), Cls).
collection(Node) :- module(_, Node, Pred, Cls), voc(type, Pred),
    voc((assetCollection; partyCollection), Cls).
collection(Node) :- sotw_closure(Pred, Node, Cls), voc(type, Pred),
    voc((assetCollection; partyCollection), Cls).

%*! compares(P, Lo, Hi)

Policy `P` asks whether `Lo` is part of `Hi`: a request entity against the target or party of
one of `P`'s atoms, the two values of one of `P`'s `isPartOf` or `hasPart` leaves, or an actor or
issuer that the witness test of one of `P`'s duties compares with a bearer or an attester.
*%
compares(P, Asked, T) :- request_target(Asked), atom_target(X, T), space(X, P).
compares(P, Asked, Party) :- request_party(F, Asked), atom_party(X, F, Party), space(X, P).
compares(P, Lv, Rv) :- cpair(_, C, P, Lv, Rv), op(C, isPartOf).
compares(P, Rv, Lv) :- cpair(_, C, P, Lv, Rv), op(C, hasPart).
compares(P, Party, Coll) :- request_party(F, Party), voc(assignee, F), bearer(Y, Coll),
    Coll != none, space(Y, P).
compares(P, Actor, Coll) :- evidence(_, _, Actor, _), bearer(Y, Coll), Coll != none,
    space(Y, P).
compares(P, Issuer, A) :- evidence_issuer(_, Issuer), attester(Duty, A), node_space(Duty, P).

%*! part_up(P, Lo, N)

In policy `P`'s data space, `N` is `Lo` or above it along `partOf` edges of any kind, for a `Lo`
that `P` compares.
*%
part_up(P, Lo, Lo) :- compares(P, Lo, _).
part_up(P, Lo, N2) :- part_up(P, Lo, N), closure(P, partOf, N, N2).

%*! part_down(P, Hi, N)

In policy `P`'s data space, `N` is `Hi` or below it along `partOf` edges of any kind, for a `Hi`
that `P` compares.
*%
part_down(P, Hi, Hi) :- compares(P, _, Hi).
part_down(P, Hi, N) :- part_down(P, Hi, N2), closure(P, partOf, N, N2).

%*! walked(P, Lo, Hi)

The `partOf` edge from `Lo` to `Hi` lies on a path, of any kinds, between two nodes that policy
`P` compares, so `P`'s reading of that comparison may cross it.
*%
walked(P, A, B) :- compares(P, Lo, Hi), part_up(P, Lo, A), closure(P, partOf, A, B),
    part_down(P, Hi, B).

% A path may pass only through collections of one kind, and a cross-kind path is invalid
% (due2-profiles.md §6). An edge into an untyped node, or across kinds, has no reading the spike
% trusts, so it is declined, but only where some policy's comparison may cross it (`walked/3`).
% Every typed path is a path of any kinds, so an edge on no path of any kinds between two compared
% nodes is on no typed one either, under any typing: whatever it means, it changes no answer
% (`test_typed_part_of`, `test_policy_reads_only_its_own_edges`).
unsupported("odrl:partOf: untyped collection") :- walked(P, _, Hi), not coll_kind(P, Hi, _).
unsupported("odrl:partOf: untyped collection") :- walked(P, _, Hi), coll_kind(P, Hi, asset),
    coll_kind(P, Hi, party).
unsupported("odrl:partOf: cross-kind edge") :- walked(P, Lo, Hi), node_kind(P, Lo, K),
    coll_kind(P, Hi, K2), K != K2.
% odrl:source on a collection names where its members come from; the spike reads membership
% only from the partOf edges, so it is inert there. Elsewhere it is not admissible, and neither
% is a collection's refinement (due2-diagnostics.md, UnsupportedConstruct).
reject("UnsupportedConstruct", Node) :- triple(Node, Pred, _), voc(source, Pred),
    not collection(Node).
reject("UnsupportedConstruct", Node) :- triple(Node, Pred, _), voc(refinement, Pred),
    collection(Node).
% A policy with `dct:isReplacedBy` is void, and its replacement is the policy to evaluate
% (IM 2.2 §2.8). Every other `dct:` term on it stays an annotation.
reject("ReplacedPolicy", P) :- policy(P), triple(P, Pred, _), voc(isReplacedBy, Pred).

%## What the spike does not read

% The declines and the rejections of the graph (DESIGN.md § Declines):
%
% - A `partOf` edge into an untyped node, or one typed both ways, declines as `odrl:partOf: untyped
%   collection`, and an edge from a node of one kind into a collection of the other as `odrl:partOf:
%   cross-kind edge`. A cross-kind path is invalid (due2-profiles.md §6), and the spike has no
%   reading it trusts for either. Only an edge that some data space walks declines (`walked/3`,
%   *Hierarchies*): an edge that no comparison of a policy crosses changes no reply.
% - `odrl:source` off a collection, or `odrl:refinement` on a collection, is
%   `reject("UnsupportedConstruct", Node)` (due2-diagnostics.md). On a collection, `odrl:source` is
%   inert: the spike reads membership only from the `partOf` edges.
% - `rdf:value` is read only on an action term, and declines anywhere else.
% - A policy with `dct:isReplacedBy` is void (IM 2.2 §2.8) and is `reject("ReplacedPolicy", P)`.
% - A policy that names a profile with no module among those the driver loaded at init is not
%   admissible either (`UnrecognisedProfile`, IM 2.2 §3.2). The driver reports it while building the
%   input facts, before solve 1, since it has no module to load.

%*! policy_predicate(Key)

`Key` names a predicate the spike reads on the policy node only.
*%
policy_predicate(profile; conflict; permission; prohibition; obligation).

%*! family_predicate(Key)

`Key` names a family predicate, read on the policy and its rules.
*%
family_predicate(action; target).

%*! anywhere_predicate(Key)

`Key` names a predicate the spike reads on any node: the hierarchy edges, the constraint
predicates, the connectives (`andSequence` so that it is rejected, not declined), the
binding attributes, the concept schemes, and the SKOS hierarchy and membership.
*%
% odrl:unit labels the right operand and joins the completion key (due2-workflows.md §6.4). It
% converts nothing, so a comparison reads the values alone.
anywhere_predicate(includedIn; partOf; source; leftOperand; operator; rightOperand; unit).
anywhere_predicate(Key) :- connective(Key).
anywhere_predicate(Key) :- binding_key(Key).
anywhere_predicate(conceptScheme; broader; narrower; inScheme; topConceptOf; hasTopConcept).

%*! timing_predicate(Pred)

`Pred` is `dprod:deadline` or `dprod:recurrence`, and DPROD is a selected profile. The timing
vocabulary is DPROD's (due2-profiles.md §7): without the profile it is a predicate the spike does
not read.
*%
timing_predicate(Pred) :- voc((deadline; recurrence), Pred), pred_ns(Pred, NS),
    selected_profile(NS).

%*! consumed(Node, Pred)

The spike reads predicate `Pred` on `Node`, so it declines nothing there. The table of what it
reads is in DESIGN.md § Declines.
*%
consumed(Node, Pred) :- triple(Node, Pred, _), voc(type, Pred).
consumed(Node, Pred) :- triple(Node, Pred, Node), voc(uid, Pred).
consumed(Node, Pred) :- triple(Node, Pred, _), policy(Node), voc(Key, Pred), policy_predicate(Key).
% The families are consumed on every node, not only on the policy and its rules. Anywhere else
% they hang under a link that is itself declined (odrl:duty on a duty, odrl:refinement) or off
% the policy, so declining on them would name the family instead of the feature.
consumed(Node, Pred) :- triple(Node, Pred, _), voc(Key, Pred), family_predicate(Key).
consumed(Node, Pred) :- triple(Node, Pred, _), function(Pred).
consumed(Node, Pred) :- triple(Node, Pred, _), voc(Key, Pred), anywhere_predicate(Key).
consumed(Node, Pred) :- triple(Node, Pred, _), voc(constraint, Pred), rule(Node).
consumed(Node, Pred) :- triple(Node, Pred, _), voc(constraint, Pred), duty_node(Node).
consumed(Node, Pred) :- pre_rule(Node, Duty), triple(Node, Pred, Duty), voc(duty, Pred).
consumed(Node, Pred) :- triple(Node, Pred, _), voc((output; instanceScope), Pred), duty_node(Node).
% Timing is read on the policy and its rules too, where it is rejected (structure.lp).
consumed(Node, Pred) :- triple(Node, Pred, _), timing_predicate(Pred), structure_node(Node).
consumed(Node, Pred) :- triple(Node, Pred, _), voc(refinement, Pred), action_term(Node).
consumed(Node, Pred) :- triple(Node, Pred, _), voc(refinement, Pred), collection(Node).
consumed(Node, Pred) :- triple(Node, Pred, _), voc(value, Pred), action_term(Node).

%*! annotated(Pred)

`Pred` is an annotation, by name or by namespace.
*%
annotated(Pred) :- annotation(Pred).
annotated(Pred) :- pred_ns(Pred, NS), annotation_ns(NS).

%*! unsupported(Feature)

The vector uses `Feature`, which the spike does not read, so solve 1 declines it, naming the
smallest `Feature`. Here `Feature` is a predicate IRI, or a reason for a hierarchy the
spike does not trust (`"odrl:partOf: …"`). structure.lp, constraint.lp, and bind.lp add
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
unsupported_input("sotw.closure") :- sotw_closure(Pred, _, _), not closure_relation(Pred).

%## The values the program compares

%*! compared(Lit)

The program compares the RDF literal `Lit`, so it needs `Lit`'s position. These are the input
instants and input values, whose positions the spec fixes (values.py).
*%
compared(Lit) :- request_at(Lit).
compared(Lit) :- sotw_effective_at(Lit).
compared(Lit) :- activation(_, Lit).
compared(Lit) :- evidence(_, Lit, _, _).
compared(Lit) :- request_param(_, Lit).
compared(Lit) :- fact_value(_, Lit).
compared(Lit) :- evidence_param(_, _, Lit).
compared(Lit) :- right(_, Lit).
compared(Lit) :- node_deadline(_, Lit).

%*! input_instant(Lit)

`Lit` is an instant of the input: the request's `at`, the SOTW's `effective_at`, an activation,
or an evidence time.
*%
input_instant(Lit) :- request_at(Lit).
input_instant(Lit) :- sotw_effective_at(Lit).
input_instant(Lit) :- activation(_, Lit).
input_instant(Lit) :- evidence(_, Lit, _, _).

%*! off_shape(Reason)

A literal unplaceable for `Reason` has a shape its kind does not admit: a `dateTime` without a
timezone, or a `date` with one (decisions/0024). It declines only as an input instant. As a right
operand or a deadline it is a rejection (constraint.lp, structure.lp), and as a value a leaf
reads, a misfit, so `u` (compare.lp).
*%
off_shape("value: dateTime without timezone"; "value: date with timezone").

%*! unsupported_value(Reason)

A compared RDF literal cannot be placed, for `Reason`, so the vector is declined. An
unplaceable literal the program never compares declines nothing (values.py).
*%
unsupported_value(Reason) :- unplaceable(Lit, Reason), compared(Lit), not off_shape(Reason).
unsupported_value(Reason) :- unplaceable(Lit, Reason), input_instant(Lit), off_shape(Reason).
