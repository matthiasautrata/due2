% lift.lp: triples to vocabulary-free relations (DESIGN.md § Fact schema), and the
% predicates this increment does not read (DESIGN.md § Declines). The only file that
% names an IRI; every later file reads the relations defined here.

% --- vocabulary ---

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

conflict_value("http://www.w3.org/ns/odrl/2/prohibit", prohibit).
conflict_value("http://www.w3.org/ns/odrl/2/perm",     perm).
conflict_value("http://www.w3.org/ns/odrl/2/invalid",  invalid).

policy_class("http://www.w3.org/ns/odrl/2/Policy").
policy_class("http://www.w3.org/ns/odrl/2/Set").
policy_class("http://www.w3.org/ns/odrl/2/Offer").
policy_class("http://www.w3.org/ns/odrl/2/Agreement").

% The function predicates of normalisation §3, and the match keys of workflows §5.2.
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
match_key("http://www.w3.org/ns/odrl/2/assignee").

% Namespaces whose predicates mean something: odrl, due2, and each selected profile.
vocab_ns("http://www.w3.org/ns/odrl/2/").
vocab_ns("https://w3id.org/due2/profile#").
vocab_ns(I) :- selected_profile(I).

% The annotation allowlist.
annotation("http://www.w3.org/2000/01/rdf-schema#label").
annotation("http://www.w3.org/2000/01/rdf-schema#comment").
annotation("http://www.w3.org/2004/02/skos/core#prefLabel").
annotation("http://www.w3.org/2004/02/skos/core#altLabel").
annotation("http://www.w3.org/2004/02/skos/core#hiddenLabel").
annotation("http://www.w3.org/2004/02/skos/core#definition").
annotation("http://www.w3.org/2004/02/skos/core#note").
annotation("https://ekgf.org/dprod/spec/develop/offerLifecycleStatus").
annotation("https://ekgf.org/dprod/spec/develop/contractLifecycleStatus").
annotation_ns("http://purl.org/dc/terms/").
annotation_ns("http://www.w3.org/ns/prov#").

% --- lifted relations ---

type(N, C) :- triple(N, T, C), voc(type, T).
subclass(C, D) :- module(C, S, D), voc(subclass, S).

has_rule(P, R, permit) :- triple(P, X, R), voc(permission, X).
has_rule(P, R, forbid) :- triple(P, X, R), voc(prohibition, X).

stated(N, action, A) :- triple(N, X, A), voc(action, X).
stated(N, target, T) :- triple(N, X, T), voc(target, X).
stated(N, F, V) :- triple(N, F, V), function(F).

stated_conflict_iri(P, V) :- triple(P, X, V), voc(conflict, X).
stated_conflict(P, C) :- stated_conflict_iri(P, V), conflict_value(V, C).
profile_conflict(C) :- selected_profile(I), module(I, X, V), voc(conflict, X), conflict_value(V, C).

closure(includedIn, N, B) :- triple(N, X, B), voc(includedIn, X).
closure(includedIn, N, B) :- module(N, X, B), voc(includedIn, X).

% --- what this increment does not read ---

policy_predicate(profile; conflict; permission; prohibition).
family_predicate(action; target).

consumed(S, P) :- triple(S, P, _), voc(type, P).
consumed(S, P) :- triple(S, P, S), voc(uid, P).
consumed(S, P) :- triple(S, P, _), policy(S), voc(K, P), policy_predicate(K).
% Read on the policy and its rules; anywhere else they hang under a declined link
% (odrl:duty, odrl:refinement) or off the policy, so naming them would hide the feature.
consumed(S, P) :- triple(S, P, _), voc(K, P), family_predicate(K).
consumed(S, P) :- triple(S, P, _), function(P).
consumed(S, P) :- triple(S, P, _), voc(includedIn, P).

annotated(P) :- annotation(P).
annotated(P) :- pred_ns(P, NS), annotation_ns(NS).

unsupported(P) :- triple(S, P, _), not consumed(S, P), not annotated(P), pred_ns(P, NS), vocab_ns(NS).
unsupported(P) :- triple(S, P, _), not consumed(S, P), not annotated(P), structure_node(S).
% An action or target given as a node with rdf:value (IM 2.2 §2.5) is a refinement shape.
unsupported(P) :- triple(_, P, _), voc(value, P).
