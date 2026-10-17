%# structure.lp: the policy, its conflict strategy, and its atoms
%
% Finds the one policy, its conflict strategy, and the rules' values after interiorisation, and
% expands each rule into atoms: one per action, target, and assignee
% (odrl-compound-to-atomic-normalization.md §3, §6.2, §6.3). The atom relations are the columns
% of the atom table of due2-workflows.md §3.1. A policy that is not admissible gets a `reject`.
% Variable letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `type/2`, `subclass/2`, `policy_class/1`, `has_rule/3`, `stated/3`,
%   `stated_conflict_iri/2`, `stated_conflict/2`, `conflict_value/2`, `profile_conflict/1`,
%   `function/1`, `match_key/1` (lift.lp).
% - **Provides:** `policy_type/1`, `policy/1`, `some_policy/0`, `reject/2`, `rule/1`,
%   `structure_node/1`, `states_conflict/1`, `some_profile_conflict/0`, `conflict/2`,
%   `family/1`, `states_family/2`, `rule_value/3`, `has_value/2`, `has_match_value/1`,
%   `assignee/2`, `atom/1`, `atom_rule/2`, `atom_action/2`, `atom_target/2`, `atom_policy/2`,
%   `atom_effect/2`, `atom_party/3`; extends `unsupported/1` (lift.lp).

%## The policy

%*! policy_type(Cls)

`Cls` types a policy: a policy class, or a class a selected module declares a direct
`rdfs:subClassOf` of one. See odrl-compound-to-atomic-normalization.md §3.
*%
policy_type(Cls) :- policy_class(Cls).
policy_type(Cls) :- subclass(Cls, Super), policy_class(Super).

%*! policy(P)

Node `P` is a policy: the policy graph types it with a policy type. An admissible vector has
exactly one.
*%
policy(P) :- type(P, Cls), policy_type(Cls).

%*! some_policy

The policy graph has a policy. A flag with no arguments, so that `not some_policy` says "no
policy at all".
*%
some_policy :- policy(_).

%*! reject(Code, Node)

The policy is not admissible: a W1 rejection `Code`, found at `Node`. The codes are in
due2-diagnostics.md.
`Node` is the sentinel `none` for `"NoPolicy"`, which has no node. Solve 1 turns any `reject`
into an `error` reply, because `interpret` receives only admissible policies.
*%
reject("NoPolicy", none) :- not some_policy.
reject("MultiplePolicies", P) :- policy(P), policy(Q), P != Q.

%*! rule(R)

Node `R` is a rule of the policy: a permission or a prohibition.
*%
rule(R) :- policy(P), has_rule(P, R, _).

%*! structure_node(Node)

`Node` is the policy or one of its rules: where an unknown predicate declines, whatever its
namespace, because it may be a semantic extension. The rule is `unsupported/1` in lift.lp.
*%
structure_node(Node) :- policy(Node).
structure_node(Node) :- rule(Node).

%## The conflict strategy

%*! states_conflict(P)

Policy `P` states an `odrl:conflict`, valid or not.
*%
states_conflict(P) :- stated_conflict_iri(P, _).
% A policy that states an invalid value gets no conflict/2 below, and is rejected here.
reject("InvalidConflict", P) :- stated_conflict_iri(P, Iri), policy(P), not conflict_value(Iri, _).
reject("InvalidConflict", P) :- stated_conflict(P, C), stated_conflict(P, C2), policy(P), C != C2.
% odrl-compound-to-atomic-normalization.md §3 does not say which of two profile defaults wins, so
% the vector is declined rather than guessed.
unsupported("profile-conflict-defaults") :- profile_conflict(C), profile_conflict(C2), C != C2.

%*! some_profile_conflict

Some selected profile sets a default conflict strategy.
*%
some_profile_conflict :- profile_conflict(_).

%*! conflict(P, C)

Policy `P` resolves its conflicts with strategy `C`: `prohibit`, `perm`, or `invalid`. That is
its own `odrl:conflict` if it states one, otherwise the selected profile's default, otherwise
`invalid` (odrl-compound-to-atomic-normalization.md §3).
*%
conflict(P, C) :- policy(P), stated_conflict(P, C).
conflict(P, C) :- policy(P), not states_conflict(P), profile_conflict(C).
conflict(P, invalid) :- policy(P), not states_conflict(P), not some_profile_conflict.

%## Interiorisation

% A root rule that states nothing for a family takes all of the policy's values for it
% (odrl-compound-to-atomic-normalization.md §6.2).

%*! family(Fam)

`Fam` is a family of values a rule states or inherits: `action`, `target`, or a function IRI.
*%
family(action).
family(target).
family(F) :- function(F).

%*! states_family(R, Fam)

Rule `R` itself states at least one value for family `Fam`.
*%
states_family(R, Fam) :- rule(R), stated(R, Fam, _).

%*! rule_value(R, Fam, Term)

`Term` is one of rule `R`'s values for family `Fam`: what the rule states, or, if it states
nothing for the family, each value the policy states.
*%
rule_value(R, Fam, Term) :- rule(R), stated(R, Fam, Term).
rule_value(R, Fam, Term) :- policy(P), has_rule(P, R, _), family(Fam), not states_family(R, Fam),
    stated(P, Fam, Term).

%*! has_value(R, Fam)

Rule `R` has a value for family `Fam` after interiorisation. A rule needs an action and a target.
*%
has_value(R, Fam) :- rule_value(R, Fam, _).
reject("MissingAction", R) :- rule(R), not has_value(R, action).
reject("MissingTarget", R) :- rule(R), not has_value(R, target).

%## Expansion

% One atom per action × target × assignee (odrl-compound-to-atomic-normalization.md §6.3).
% Carried functions (every function but the match keys) are not axes: expanding over them would
% only copy atoms whose findings are identical.

%*! has_match_value(R)

Rule `R` has a value for some match key.
*%
has_match_value(R) :- rule_value(R, F, _), match_key(F).

%*! assignee(R, Party)

`Party` is an assignee of rule `R`, or the sentinel `none` when it has none, so that a rule
without an assignee still expands to atoms.
*%
assignee(R, Party) :- rule_value(R, F, Party), match_key(F).
assignee(R, none) :- rule(R), not has_match_value(R).

%*! atom(X)

`X = a(R, A, T, Party)` is an atom: rule `R` expanded to one action `A`, one target `T`, and one
assignee `Party` (or `none`). The id is its content, so it is distinct and stable; digests stay
host-side (decisions/0007). The reply projects an atom to its rule `R` (due2-workflows.md §3.7).
*%
atom(a(R, A, T, Party)) :- rule(R), rule_value(R, action, A), rule_value(R, target, T),
    assignee(R, Party).

%*! atom_rule(X, R)

Atom `X` comes from rule `R`.
*%
atom_rule(a(R, A, T, Party), R) :- atom(a(R, A, T, Party)).

%*! atom_action(X, A)

Atom `X` is for action `A`.
*%
atom_action(a(R, A, T, Party), A) :- atom(a(R, A, T, Party)).

%*! atom_target(X, T)

Atom `X` is for target `T`.
*%
atom_target(a(R, A, T, Party), T) :- atom(a(R, A, T, Party)).

%*! atom_policy(X, P)

Atom `X` belongs to policy `P`.
*%
atom_policy(X, P) :- atom_rule(X, R), policy(P), has_rule(P, R, _).

%*! atom_effect(X, E)

Atom `X` has effect `E`: `permit` or `forbid`.
*%
atom_effect(X, E) :- atom_rule(X, R), policy(P), has_rule(P, R, E).

%*! atom_party(X, F, Party)

Atom `X` is for party `Party` under match key `F`. An atom whose assignee is `none` has no
`atom_party`, because no `rule_value` is `none`, so it has no party part (applies.lp).
*%
atom_party(a(R, A, T, Party), F, Party) :- atom(a(R, A, T, Party)), rule_value(R, F, Party),
    match_key(F).
