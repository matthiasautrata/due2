% structure.lp: the policy, its conflict strategy, interiorisation, and expansion
% (normalisation §3, §6.2-§6.3), shaped like the workflows §3.1 relations.

% --- the policy (normalisation §3: declared, direct rdfs:subClassOf only) ---

policy_type(C) :- policy_class(C).
policy_type(C) :- subclass(C, D), policy_class(D).
policy(P) :- type(P, C), policy_type(C).

some_policy :- policy(_).
reject("NoPolicy", none) :- not some_policy.
reject("MultiplePolicies", P) :- policy(P), policy(Q), P != Q.

rule(R) :- policy(P), has_rule(P, R, _).
structure_node(N) :- policy(N).
structure_node(N) :- rule(N).

% --- the conflict strategy ---

states_conflict(P) :- stated_conflict_iri(P, _).
reject("InvalidConflict", P) :- stated_conflict_iri(P, V), policy(P), not conflict_value(V, _).
reject("InvalidConflict", P) :- stated_conflict(P, C), stated_conflict(P, D), policy(P), C != D.
unsupported("profile-conflict-defaults") :- profile_conflict(C), profile_conflict(D), C != D.

some_profile_conflict :- profile_conflict(_).
conflict(P, C) :- policy(P), stated_conflict(P, C).
conflict(P, C) :- policy(P), not states_conflict(P), profile_conflict(C).
conflict(P, invalid) :- policy(P), not states_conflict(P), not some_profile_conflict.

% --- interiorisation (§6.2): a root rule silent on a family takes the policy's values ---

family(action).
family(target).
family(F) :- function(F).

states(R, Fam) :- rule(R), stated(R, Fam, _).
rule_value(R, Fam, V) :- rule(R), stated(R, Fam, V).
rule_value(R, Fam, V) :- policy(P), has_rule(P, R, _), family(Fam), not states(R, Fam), stated(P, Fam, V).

has_value(R, Fam) :- rule_value(R, Fam, _).
reject("MissingAction", R) :- rule(R), not has_value(R, action).
reject("MissingTarget", R) :- rule(R), not has_value(R, target).

% --- expansion (§6.3): one atom per action x target x assignee ---
% Carried functions (not match keys) are not axes: they would only copy atoms.

has_match_value(R) :- rule_value(R, F, _), match_key(F).
assignee(R, Y) :- rule_value(R, F, Y), match_key(F).
assignee(R, none) :- rule(R), not has_match_value(R).

atom(a(R, A, T, Y)) :- rule(R), rule_value(R, action, A), rule_value(R, target, T), assignee(R, Y).
atom_rule(a(R, A, T, Y), R) :- atom(a(R, A, T, Y)).
atom_action(a(R, A, T, Y), A) :- atom(a(R, A, T, Y)).
atom_target(a(R, A, T, Y), T) :- atom(a(R, A, T, Y)).
atom_policy(X, P) :- atom_rule(X, R), policy(P), has_rule(P, R, _).
atom_effect(X, E) :- atom_rule(X, R), policy(P), has_rule(P, R, E).
atom_party(a(R, A, T, Y), F, Y) :- atom(a(R, A, T, Y)), rule_value(R, F, Y), match_key(F).
