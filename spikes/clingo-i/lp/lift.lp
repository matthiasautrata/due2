%# lift.lp: triples to relations, and what the spike does not read
%
% Lifts the policy and module triples to relations that name no IRI, and detects every
% predicate, input field, and value the spike does not read, so that the vector is declined
% instead of answered wrongly (DESIGN.md § Declines). This is the only file that names an
% IRI: every later file reads the relations it provides. Variable letters: DESIGN.md
% § Vocabulary.
%
% - **Consumes:** the driver's facts (DESIGN.md § Input facts): the graphs (`triple/3`,
%   `module/3`, `pred_ns/2`, `selected_profile/1`), the request (`request_at/1`,
%   `request_param/2`, `request_param_set/1`), the SOTW (`sotw_effective_at/1`, `fact/2`,
%   `fact_value/2`, `evidence/4`, `evidence_param/3`, `signer/2`, `activation/2`,
%   `sotw_closure/3`), the config (`config_combination/1`, `config_violations/1`), and the
%   driver's own findings (`unread/1`, `unplaceable/2`); `policy/1` and `structure_node/1`
%   (structure.lp).
% - **Provides:** the vocabulary (`voc/2`, `conflict_value/2`, `policy_class/1`, `function/1`,
%   `match_key/1`, `vocab_ns/1`, `annotation/1`, `annotation_ns/1`); the lifted relations
%   (`type/2`, `subclass/2`, `has_rule/3`, `stated/3`, `stated_conflict_iri/2`,
%   `stated_conflict/2`, `profile_conflict/1`, `closure/3`); the declines
%   (`policy_predicate/1`, `family_predicate/1`, `consumed/2`, `annotated/1`, `unsupported/1`,
%   `unsupported_input/1`, `compared/1`, `unsupported_value/1`).

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

%*! conflict_value(Iri, C)

The `odrl:conflict` value `Iri` names the conflict strategy `C`: `prohibit`, `perm`, or
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

%*! annotation_ns(NS)

Every predicate in namespace `NS` (`dct:`, `prov:`) is an annotation.
*%
annotation_ns("http://purl.org/dc/terms/").
annotation_ns("http://www.w3.org/ns/prov#").

%## Lifted relations

%*! type(Node, Cls)

The policy graph states `Node rdf:type Cls`.
*%
type(Node, Cls) :- triple(Node, Pred, Cls), voc(type, Pred).

%*! subclass(Cls, Super)

A selected module states `Cls rdfs:subClassOf Super`. Only declared, direct edges: no closure
(odrl-compound-to-atomic-normalization.md §3).
*%
subclass(Cls, Super) :- module(Cls, Pred, Super), voc(subclass, Pred).

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

%*! stated_conflict(P, C)

Node `P` states the valid conflict strategy `C`.
*%
stated_conflict(P, C) :- stated_conflict_iri(P, Iri), conflict_value(Iri, C).

%*! profile_conflict(C)

A selected profile resource sets the default conflict strategy `C`. See due2-profiles.md §8.1.
*%
profile_conflict(C) :- selected_profile(Prof), module(Prof, Pred, Iri), voc(conflict, Pred),
    conflict_value(Iri, C).

%*! closure(Rel, A, B)

A declared `Rel` edge from `A` to the broader `B`, from the policy or a selected module. `Rel` is
always `includedIn`, the only hierarchy the spike reads; `odrl:partOf` is declined. The edges
are closed-world: an undeclared edge does not hold (due2-profiles.md §6).
*%
closure(includedIn, A, B) :- triple(A, Pred, B), voc(includedIn, Pred).
closure(includedIn, A, B) :- module(A, Pred, B), voc(includedIn, Pred).

%## What the spike does not read

%*! policy_predicate(Key)

`Key` names a predicate the spike reads on the policy node only.
*%
policy_predicate(profile; conflict; permission; prohibition).

%*! family_predicate(Key)

`Key` names a family predicate, read on the policy and its rules.
*%
family_predicate(action; target).

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
consumed(Node, Pred) :- triple(Node, Pred, _), voc(includedIn, Pred).

%*! annotated(Pred)

`Pred` is an annotation, by name or by namespace.
*%
annotated(Pred) :- annotation(Pred).
annotated(Pred) :- pred_ns(Pred, NS), annotation_ns(NS).

%*! unsupported(Feature)

The vector uses `Feature`, which the spike does not read, so solve 1 declines it, naming the
smallest `Feature`. Here `Feature` is a predicate IRI. structure.lp adds
`"profile-conflict-defaults"`.
*%
% Neither consumed nor annotated, and either in a vocabulary namespace or on the policy or a
% rule. On other nodes (assets, parties) a foreign predicate is data the spike never reads.
unsupported(Pred) :- triple(Node, Pred, _), not consumed(Node, Pred), not annotated(Pred),
    pred_ns(Pred, NS), vocab_ns(NS).
unsupported(Pred) :- triple(Node, Pred, _), not consumed(Node, Pred), not annotated(Pred),
    structure_node(Node).
% An action or target given as a node with rdf:value (IM 2.2 §2.5) is a refinement shape.
unsupported(Pred) :- triple(_, Pred, _), voc(value, Pred).

%## The input fields the spike does not read

%*! unsupported_input(Field)

The input field `Field` has content the spike does not read, so the vector is declined, naming
the smallest `Field`. An empty field gives no facts, so it declines nothing.
*%
unsupported_input("request.params") :- request_param(_, _).
unsupported_input("request.params") :- request_param_set(_).
unsupported_input("sotw.facts") :- fact(_, _).
unsupported_input("sotw.evidence") :- evidence(_, _, _, _).
unsupported_input("sotw.activation") :- activation(_, _).
unsupported_input("sotw.closure") :- sotw_closure(_, _, _).
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

%*! unsupported_value(Reason)

A compared RDF literal cannot be placed, for `Reason`, so the vector is declined. An
unplaceable literal the program never compares declines nothing (DESIGN.md § Values).
*%
unsupported_value(Reason) :- unplaceable(Lit, Reason), compared(Lit).
