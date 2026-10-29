%# structure.lp: the policy, its atoms, and its duty atoms
%
% Finds the one policy, checks its stated conflict strategy, finds the rules' values after
% interiorisation, and expands each rule into atoms: one per action, target, and assignee
% (odrl-compound-to-atomic-normalization.md §3, §6.2, §6.3). Each precondition duty and root
% obligation is expanded the same way into duty atoms, one per action, relation value, and
% bearer, with the edges that tie a permission atom to its preconditions. The atom relations are
% the columns of the atom table of due2-workflows.md §3.1. A policy that is not admissible gets a
% `reject`. Variable letters: DESIGN.md § Vocabulary.
%
% Each relation and its due2-workflows.md §3.1 counterpart:
%
% | Relation | due2-workflows.md §3.1 counterpart |
% |---|---|
% | `policy(P)`, and `conflict(P, Strat)` from bind.lp | `policy(policy_id \| conflict, …)` |
% | `atom(X)`, `atom_effect(X, Eff)`, `atom_rule(X, R)`, `atom_action(X, A)`, `atom_target(X, T)` | `atom(atom_id \| effect, action, relation, relation_value, source_rule)` |
% | `atom_policy(X, P)` | `root(atom_id, policy_id)`: one tuple for each policy that states the atom (`decisions/0036`) |
% | `atom_party(X, F, Party)` | `atom_party`, match keys only |
% | `duty_atom(Y)`, `atom_effect(Y, oblige)`, `duty_action(Y, A)`, `duty_relation(Y, T)` | `atom`, for an `Oblige` atom |
% | `duty_of(Y, Duty)`, `duty_scope(Y, InstScope)`, `duty_deadline(Y, Lit)` | `duty(atom_id \| source_duty, scope, deadline?, recurrence?)` |
% | `bearer(Y, Party)` | `atom_party`, for the bearer role |
% | `pre(X, Y)` | `edge`, a precondition |
% | `obligation(Y)` | `root` |
% | `reject(Code, Node)` | a W1 rejection (`due2-diagnostics.md`) |
%
% - **Consumes:** `type/2`, `subclass/2`, `policy_class/1`, `has_rule/3`, `stated/3`,
%   `stated_conflict_iri/2`, `stated_conflict/2`, `conflict_value/2`, `function/1`,
%   `match_key/1`, `bearer_fn/1`, `attester_fn/1`, `timing_predicate/1`,
%   `term_kind/2`, `voc/2`, `kind/2`, `off_shape/1` (lift.lp); `triple/3`, `unplaceable/2`,
%   `policy_texts/1` (driver).
% - **Provides:** `policy_type/1`, `policy/1`, `some_policy/0`, `reject/2`, `rule/1`,
%   `structure_node/1`, `states_conflict/1`, `family/1`,
%   `states_family/2`, `rule_value/3`, `has_value/2`, `has_match_value/1`,
%   `assignee/2`, `action_term/1`, `action_of/2`, `has_action_value/1`, `atom/1`,
%   `atom_rule/2`, `atom_action/2`, `atom_target/2`, `atom_policy/2`, `atom_effect/2`,
%   `atom_party/3`; the duties (`obliges/2`, `root_obligation/1`, `pre_rule/2`, `duty_node/1`,
%   `duty_stated/3`, `duty_states/2`, `duty_value/3`, `has_duty_value/2`, `duty_rel/2`,
%   `inherits/1`, `duty_states_party/1`, `states_bearer/1`, `bearer_value/3`, `own_bearer/2`,
%   `has_own_bearer/1`, `parent_bearer/2`, `has_parent_bearer/1`, `inh_bearer/3`, `duty_bearer/2`,
%   `attester/2`, `has_attester/1`, `duty_atom/1`, `duty_of/2`, `pre/2`, `obligation/1`,
%   `bearer/2`, `duty_action/2`, `duty_relation/2`); their timing and scope (`node_deadline/2`, `deadline_kind/2`,
%   `duty_deadline/2`, `duty_scope/2`, `scope_value/1`, `states_scope/1`); the data spaces (`space/2`, `spaced/1`); extends
%   `unsupported/1` (lift.lp).

%## The policy

% A policy is a node typed by a policy class, or by a class that a selected module declares
% `rdfs:subClassOf` one. Only declared, direct edges count (odrl-compound-to-atomic-normalization.md
% §3). The vector carries one text per policy, and the policies of all texts are one corpus
% (due2-workflows.md §4, *Several policies are one corpus*). No policy is `reject("NoPolicy",
% none)`, and more policies than texts is `reject("MultiplePolicies", P)`.

%*! policy_type(Cls)

`Cls` types a policy: a policy class, or a class a selected module declares a direct
`rdfs:subClassOf` of one. See odrl-compound-to-atomic-normalization.md §3.
*%
policy_type(Cls) :- policy_class(Cls).
policy_type(Cls) :- subclass(Cls, Super), policy_class(Super).

%*! policy(P)

Node `P` is a policy: the policy graph types it with a policy type. An admissible vector has
exactly one per policy text.
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
`Node` is the sentinel `none` for `"NoPolicy"`, which has no node. The driver turns any
`reject` into an `error` reply, because `interpret` receives only admissible policies.
*%
reject("NoPolicy", none) :- not some_policy.
% W1 rejects a text with two policies (due2-workflows.md §4). Solve 0 sees one text, with
% `policy_texts(1)`, so there the rule is W1's check, as `NoPolicy` above is. Over the corpus
% (solve 1) it adds no new rejection: every policy is stated by some text, so more policies
% than texts means some text states two, and that text's solve 0 has rejected it already. The
% rule names every policy node.
reject("MultiplePolicies", P) :- policy(P), policy_texts(N), #count { Q : policy(Q) } > N.

%*! rule(R)

Node `R` is a rule of the policy: a permission or a prohibition.
*%
rule(R) :- policy(P), has_rule(P, R, _).

%*! obliges(P, Duty)

Policy `P` states `odrl:obligation Duty`.
*%
obliges(P, Duty) :- policy(P), triple(P, Pred, Duty), voc(obligation, Pred).

%*! root_obligation(Duty)

Node `Duty` is a root obligation: some policy states `odrl:obligation Duty`.
*%
root_obligation(Duty) :- obliges(_, Duty).

%*! pre_rule(R, Duty)

Node `Duty` is a precondition duty of the permission `R`: `R` states `odrl:duty Duty`. A duty of a
duty, a remedy, and a consequence are not evaluated for access (due2-workflows.md §5.5), so they
are not read.
*%
pre_rule(R, Duty) :- policy(P), has_rule(P, R, permit), triple(R, Pred, Duty), voc(duty, Pred).

%*! duty_node(Duty)

Node `Duty` is a duty: a root obligation, a precondition duty, or both.
*%
duty_node(Duty) :- root_obligation(Duty).
duty_node(Duty) :- pre_rule(_, Duty).
% A rule that is its own precondition is a cycle of odrl:duty edges
% (odrl-compound-to-atomic-normalization.md §6.3). A rule that is another rule's precondition
% is a Permission or Prohibition read as a Duty, which the spec gives no reading.
reject("RuleReferenceCycle", Duty) :- pre_rule(Duty, Duty).
unsupported("duty: also a permission or prohibition") :- duty_node(Duty), rule(Duty),
    not pre_rule(Duty, Duty).

%*! structure_node(Node)

`Node` is the policy, one of its rules, or one of its duties: where an unknown predicate declines,
whatever its namespace, because it may be a semantic extension. The rule is `unsupported/1` in
lift.lp.
*%
structure_node(Node) :- policy(Node).
structure_node(Node) :- rule(Node).
structure_node(Node) :- duty_node(Node).

%## The conflict strategy

% bind.lp gives each policy its strategy (`conflict/2`), from the profiles of its own text. Two
% stated values, or a value outside the three, is `reject("InvalidConflict", P)`.

%*! states_conflict(P)

Policy `P` states an `odrl:conflict`, valid or not.
*%
states_conflict(P) :- stated_conflict_iri(P, _).
% A policy that states an invalid value gets no conflict/2, and is rejected here.
reject("InvalidConflict", P) :- stated_conflict_iri(P, Iri), policy(P), not conflict_value(Iri, _).
reject("InvalidConflict", P) :- stated_conflict(P, Strat), stated_conflict(P, Strat2), policy(P),
    Strat != Strat2.

%## Interiorisation

% A root rule that states nothing for a family takes all of the policy's values for it
% (odrl-compound-to-atomic-normalization.md §6.2). The families are the actions, the target, and
% each function predicate.

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

% One atom per action term × target × assignee (odrl-compound-to-atomic-normalization.md §6.3).
% A rule left with no action or no target is `reject("MissingAction" | "MissingTarget", R)`.
%
% An atom id is `a(R, A, T, Party)`: its source rule, action term, target, and assignee, or the
% sentinel `none` for a rule with no assignee. The id holds the action term, not the action, so
% that applies.lp can find the term's refinements; `atom_action/2` gives the action. Digests stay
% host-side (decisions/0007); the spike needs only ids that are distinct and stable.
%
% Carried functions (every function but the match keys) are carried, not matched
% (due2-workflows.md §5.2), and they are not axes: expanding over them would only copy atoms
% whose findings are identical. A carried function that plays the bearer role still reaches a
% duty: `parent_bearer/2` reads it from the rule's values.

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

%## Action nodes

% An action may be given as a node: `odrl:action [ rdf:value odrl:use ; odrl:refinement … ]`
% (IM 2.2 §2.5). The node is the action term, which carries the refinements; its `rdf:value`
% is the action that is matched.
%
% `action_term(Term)` is each stated action. `action_of(Term, A)` is its `rdf:value` if it states
% one, or the term itself if it is an IRI. A blank node with no `rdf:value`, or a term with two,
% is declined (`action: blank node without rdf:value`, `action: several rdf:value`).

%*! action_term(Term)

`Term` is stated as an action of the policy or of a rule.
*%
action_term(Term) :- structure_node(Node), stated(Node, action, Term).

%*! has_action_value(Term)

The action term `Term` states an `rdf:value`.
*%
has_action_value(Term) :- action_term(Term), triple(Term, Pred, _), voc(value, Pred).

%*! action_of(Term, A)

The action term `Term` is for action `A`: its `rdf:value` if it states one, else the term
itself.
*%
action_of(Term, A) :- action_term(Term), triple(Term, Pred, A), voc(value, Pred).
action_of(Term, Term) :- action_term(Term), not has_action_value(Term), kind(Term, iri).
unsupported("action: several rdf:value") :- action_term(Term), action_of(Term, A),
    action_of(Term, A2), A != A2.
unsupported("action: blank node without rdf:value") :- action_term(Term),
    not has_action_value(Term), kind(Term, blank).

%*! atom(X)

`X = a(R, A, T, Party)` is an atom: rule `R` expanded to one action term `A`, one target `T`,
and one assignee `Party` (or `none`). The id is its content, so it is distinct and stable;
digests stay host-side (decisions/0007). The reply projects an atom to its rule `R`
(due2-workflows.md §3.7).
*%
atom(a(R, A, T, Party)) :- rule(R), rule_value(R, action, A), rule_value(R, target, T),
    assignee(R, Party).

%*! atom_rule(X, R)

Atom `X` comes from rule `R`.
*%
atom_rule(a(R, A, T, Party), R) :- atom(a(R, A, T, Party)).

%*! atom_action(X, A)

Atom `X` is for action `A`: the action of its action term.
*%
atom_action(a(R, Term, T, Party), A) :- atom(a(R, Term, T, Party)), action_of(Term, A).

%*! atom_target(X, T)

Atom `X` is for target `T`.
*%
atom_target(a(R, A, T, Party), T) :- atom(a(R, A, T, Party)).

%*! atom_policy(X, P)

Atom `X` belongs to policy `P`.
*%
atom_policy(X, P) :- atom_rule(X, R), policy(P), has_rule(P, R, _).

%*! atom_effect(X, Eff)

Atom `X` has effect `Eff`: `permit` or `forbid` for a rule atom, `oblige` for a duty atom.
*%
atom_effect(X, Eff) :- atom_rule(X, R), policy(P), has_rule(P, R, Eff).

%*! atom_party(X, F, Party)

Atom `X` is for party `Party` under match key `F`. An atom whose assignee is `none` has no
`atom_party`, because no `rule_value` is `none`, so it has no party part (applies.lp).
*%
atom_party(a(R, A, T, Party), F, Party) :- atom(a(R, A, T, Party)), rule_value(R, F, Party),
    match_key(F).

%## Duties

% A duty node is a precondition duty (`odrl:duty` of a permission, `pre_rule/2`), a root
% obligation (`odrl:obligation` of the policy), or both. A duty of a duty, a remedy, and a
% consequence are not evaluated for access (due2-workflows.md §5.5).
%
% A duty is expanded like a rule, into duty atoms `a(Duty, A, T, Party)`: one per action term,
% relation value, and bearer (odrl-compound-to-atomic-normalization.md §6.3). The relation `T` is
% the duty's `odrl:target` or its `odrl:output` (`duty_rel/2`), or `none` when it states neither.
% Both together is `reject("TargetAndOutput", Duty)`.
%
% A root obligation is a root rule, so it fills
% each family it leaves unstated from the policy (odrl-compound-to-atomic-normalization.md
% §6.2); a precondition duty takes no policy-level value. Its parties come from its parent
% permission instead, after expansion (due2-workflows.md §4, stage 2): a duty that states no
% function takes all of them from the parent atom, and one that states any takes none (IM 2.2
% §2.6.5). A duty that is both a root obligation and a precondition is one atom with the
% policy-level values, which count as its own, so it inherits nothing (due2-profiles.md §6). A
% stated `odrl:output` fills the relation family, so a root obligation that states one does not
% take the policy's target. An inheriting duty is `inherits/1`.
%
% The bearer is the party of a function that plays the bearer role (`bearer_fn/1`):
% `odrl:assignee`, or `dprod:subjectOfDuty` under DPROD. For each role, a value the duty states
% beats one interiorised from the policy level (due2-workflows.md §4, stage 2), so a root
% obligation that states `dprod:subjectOfDuty` is not also borne by the policy-level
% `odrl:assignee` it receives (`states_bearer/1`, `bearer_value/3`). An inheriting duty takes the
% bearer of its parent atom (`inh_bearer/3`). With none, the bearer is `none`: the request
% subject.
%
% The attester is the party of a function that plays the attester role (`attester_fn/1`):
% `due2:attestingParty`. It is one of the duty's own values (`attester/2`), and the spike declines
% an attester the duty would inherit.
%
% The bearer is in the id, and the other inherited parties are not. A duty shared by two parents
% with one bearer is therefore one atom, with one instance, and shared under two bearers it is
% two. The corpus's atom id also holds the other inherited parties (`duty.atom_id`,
% due2-workflows.md §3.1), but a witness reads only the bearer, so two atoms that differ only in
% another party would have the same findings, and the reply names both by one duty IRI. An
% instance is keyed by its atom and occurrence (due2-workflows.md §5.3). A case has one request,
% so its performer and reference are fixed, and clingo-i, which evaluates one request at a time,
% needs neither.
%
% `pre(X, Y)` fans out over every atom of the duty (odrl-compound-to-atomic-normalization.md
% §6.3), so a permission atom's preconditions are read as a conjunction. An inheriting duty gives
% `X` only its atoms with `X`'s bearer. A permission that is its own precondition is
% `reject("RuleReferenceCycle", R)`.

%*! duty_stated(Duty, Fam, Term)

`Duty` itself states `Term` for `Fam`, which is `action`, `relation`, or a function IRI. The
relation family holds an `odrl:target` or an `odrl:output`, as in
odrl-compound-to-atomic-normalization.md §6.2.
*%
duty_stated(Duty, action, A) :- duty_node(Duty), stated(Duty, action, A).
duty_stated(Duty, relation, T) :- duty_node(Duty), stated(Duty, (target; output), T).
duty_stated(Duty, F, Party) :- duty_node(Duty), function(F), stated(Duty, F, Party).
reject("TargetAndOutput", Duty) :- duty_node(Duty), stated(Duty, target, _),
    stated(Duty, output, _).

%*! duty_states(Duty, Fam)

`Duty` itself states at least one value for `Fam`.
*%
duty_states(Duty, Fam) :- duty_stated(Duty, Fam, _).

%*! duty_value(Duty, Fam, Term)

`Term` is one of `Duty`'s own values for `Fam`: what it states, or, for a root obligation that
states nothing for the family, each value the policy states. An inherited party is not one: it
belongs to the parent atom (`inh_bearer/3`).
*%
duty_value(Duty, Fam, Term) :- duty_stated(Duty, Fam, Term).
duty_value(Duty, action, A) :- obliges(P, Duty), not duty_states(Duty, action),
    stated(P, action, A).
duty_value(Duty, relation, T) :- obliges(P, Duty), not duty_states(Duty, relation),
    stated(P, target, T).
duty_value(Duty, F, Party) :- obliges(P, Duty), function(F), not duty_states(Duty, F),
    stated(P, F, Party).

%*! has_duty_value(Duty, Fam)

`Duty` has a value of its own for `Fam`. A duty needs an action; it may have no relation.
*%
has_duty_value(Duty, Fam) :- duty_value(Duty, Fam, _).
reject("MissingAction", Duty) :- duty_node(Duty), not has_duty_value(Duty, action).

%*! duty_rel(Duty, T)

`T` is a relation value of `Duty`, or the sentinel `none` when it has none, so that a duty
without a relation still expands to atoms.
*%
duty_rel(Duty, T) :- duty_value(Duty, relation, T).
duty_rel(Duty, none) :- duty_node(Duty), not has_duty_value(Duty, relation).

%*! inherits(Duty)

The precondition duty `Duty` states no function and is not a root obligation, so it takes its
parties from each parent atom.
*%
inherits(Duty) :- pre_rule(_, Duty), not root_obligation(Duty), not duty_states_party(Duty).

%*! duty_states_party(Duty)

`Duty` has a function value of its own.
*%
duty_states_party(Duty) :- duty_value(Duty, F, _), function(F).

%*! states_bearer(Duty)

`Duty` itself states a value for a function that plays the bearer role (`bearer_fn/1`).
*%
states_bearer(Duty) :- duty_stated(Duty, F, _), bearer_fn(F).

%*! bearer_value(Duty, F, Party)

`Party` is a value of `Duty`'s function `F`, which plays the bearer role, and decides its
bearer: a value the duty states, or, if it states none for the role, one interiorised from the
policy level.
*%
% odrl-compound-to-atomic-normalization.md §6.2 fills each function separately, so a root
% obligation that states dprod:subjectOfDuty still receives the policy-level odrl:assignee. For
% each role, a value the rule states beats an interiorised one (due2-workflows.md §4, stage 2),
% so the interiorised assignee is not a bearer.
bearer_value(Duty, F, Party) :- duty_stated(Duty, F, Party), bearer_fn(F).
bearer_value(Duty, F, Party) :- duty_value(Duty, F, Party), bearer_fn(F), not states_bearer(Duty).
% Two bearer functions that disagree, both stated or both from the policy level, name two
% bearers for one performance, a case the spec does not settle.
unsupported("duty: bearer from two functions") :- bearer_value(Duty, F, Party),
    bearer_value(Duty, F2, _), F != F2, not bearer_value(Duty, F2, Party).

%*! own_bearer(Duty, Party)

`Party` is a bearer of `Duty` from its own function values (`bearer_value/3`).
*%
own_bearer(Duty, Party) :- bearer_value(Duty, _, Party).

%*! has_own_bearer(Duty)

`Duty` has a bearer of its own.
*%
has_own_bearer(Duty) :- own_bearer(Duty, _).

%*! parent_bearer(X, Party)

`Party` is a bearer the permission atom `X` passes to a duty that inherits from it: its party for a
match key that plays the bearer role, or its rule's value for a carried function that does.
*%
parent_bearer(X, Party) :- atom_party(X, F, Party), bearer_fn(F).
parent_bearer(X, Party) :- atom(X), atom_rule(X, R), rule_value(R, F, Party), bearer_fn(F),
    not match_key(F).
unsupported("duty: parent with two bearers") :- parent_bearer(X, Party), parent_bearer(X, Party2),
    Party != Party2, atom_rule(X, R), pre_rule(R, Duty), inherits(Duty).

%*! has_parent_bearer(X)

The permission atom `X` passes a bearer.
*%
has_parent_bearer(X) :- parent_bearer(X, _).

%*! inh_bearer(X, Duty, Party)

`Duty`, which inherits, has bearer `Party` under its parent atom `X`: the bearer `X` passes, or
the sentinel `none` when it passes none.
*%
inh_bearer(X, Duty, Party) :- pre_rule(R, Duty), inherits(Duty), atom_rule(X, R),
    parent_bearer(X, Party).
inh_bearer(X, Duty, none) :- pre_rule(R, Duty), inherits(Duty), atom_rule(X, R),
    not has_parent_bearer(X).

%*! duty_bearer(Duty, Party)

`Party` is a bearer of `Duty`: its own, one passed by a parent atom, or the sentinel `none`. A
bearer `none` is the request subject (due2-profiles.md §6).
*%
duty_bearer(Duty, Party) :- own_bearer(Duty, Party).
duty_bearer(Duty, none) :- duty_node(Duty), not inherits(Duty), not has_own_bearer(Duty).
duty_bearer(Duty, Party) :- inh_bearer(_, Duty, Party).

%*! attester(Duty, Party)

`Party` is an attester of `Duty`: a value of its own for a function that plays the attester role
(`attester_fn/1`), such as `due2:attestingParty`. Only evidence whose issuer is at or below an
attester counts for the duty (due2-workflows.md §5.3). The attester is not in the duty atom's id:
it filters the evidence and names no performer.
*%
attester(Duty, Party) :- duty_value(Duty, F, Party), attester_fn(F).
% due2-profiles.md §6 has an inheriting duty take its parent's attester as it takes any other
% party. A duty with two parents could then take two attesters for one atom, so the spike
% declines an attester it would have to inherit rather than pick a reading.
unsupported("duty: inherited attester") :- inherits(Duty), pre_rule(R, Duty), rule_value(R, F, _),
    attester_fn(F).

%*! has_attester(Duty)

`Duty` names an attester, so evidence with no issuer, or an issuer not at or below an attester,
does not count for it.
*%
has_attester(Duty) :- attester(Duty, _).

%*! duty_atom(Y)

`Y = a(Duty, A, T, Party)` is a duty atom: `Duty` expanded to one action term `A`, one relation
value `T` (or `none`), and one bearer `Party` (or `none`). A duty atom is not an `atom/1`: it is
matched against evidence, not against the request (due2-workflows.md §5.3). The bearer is in the
id, so a duty shared by two parents with one bearer is one atom, with one instance, and shared
under two bearers it is two. Other inherited parties are not in the id, though the corpus's atom
id holds them (`duty.atom_id` of due2-workflows.md §3.1). A witness reads only the bearer of a
duty, so two atoms that differ only in such a party would have the same findings and the same
authored duty IRI.
*%
duty_atom(a(Duty, A, T, Party)) :- duty_value(Duty, action, A), duty_rel(Duty, T),
    duty_bearer(Duty, Party).

%*! duty_of(Y, Duty)

Duty atom `Y` comes from `Duty`. That is its `source_duty` in due2-workflows.md §3.1.
*%
duty_of(a(Duty, A, T, Party), Duty) :- duty_atom(a(Duty, A, T, Party)).

%*! pre(X, Y)

The duty atom `Y` is a precondition of the permission atom `X`. Edges fan out over every atom of
the duty (odrl-compound-to-atomic-normalization.md §6.3), so `X`'s preconditions are read as a
conjunction. A duty that inherits gives `X` only the atoms with `X`'s bearer.
*%
pre(X, Y) :- pre_rule(R, Duty), not inherits(Duty), atom_rule(X, R), duty_of(Y, Duty).
pre(X, a(Duty, A, T, Party)) :- inh_bearer(X, Duty, Party), duty_atom(a(Duty, A, T, Party)).

%*! obligation(Y)

The duty atom `Y` is a root obligation of the policy.
*%
obligation(Y) :- duty_of(Y, Duty), root_obligation(Duty).
atom_effect(Y, oblige) :- duty_atom(Y).

%*! space(X, P)

Atom or duty atom `X` is read in policy `P`'s data space (decisions/0050 #4): a `Permit` or
`Forbid` atom in each policy that states its rule, a root obligation in each policy that obliges
its duty, and a precondition in each space of its permission. A duty atom that reaches none of
these is read in every policy, so that it is still read where a single policy gives it one.
*%
space(X, P) :- atom_policy(X, P).
space(Y, P) :- obligation(Y), duty_of(Y, Duty), obliges(P, Duty).
space(Y, P) :- pre(X, Y), space(X, P).
space(Y, P) :- duty_atom(Y), not spaced(Y), policy(P).

%*! spaced(X)

Atom or duty atom `X` has a data space from one of its policies.
*%
spaced(X) :- atom_policy(X, _).
spaced(Y) :- obligation(Y), duty_of(Y, Duty), obliges(_, Duty).
spaced(Y) :- pre(X, Y), atom(X).

%*! bearer(Y, Party)

The duty atom `Y` must be performed by `Party`, or by the request subject when `Party` is `none`.
*%
bearer(a(Duty, A, T, Party), Party) :- duty_atom(a(Duty, A, T, Party)).

%*! duty_action(Y, A)

The duty atom `Y` is for action `A`: the action of its action term.
*%
duty_action(a(Duty, Term, T, Party), A) :- duty_atom(a(Duty, Term, T, Party)), action_of(Term, A).

%*! duty_relation(Y, T)

The duty atom `Y` is for relation value `T`, the object a witness must name. A duty atom without
a relation has none.
*%
duty_relation(a(Duty, A, T, Party), T) :- duty_atom(a(Duty, A, T, Party)), T != none.

%## Duty timing and scope

% `dprod:deadline` on a duty, when DPROD is selected, gives `duty_deadline(Y, Lit)`, `absolute` for
% an `xsd:dateTime` and `relative` for an `xsd:duration` (`deadline_kind/2`). Two deadlines, or one
% of another type, is `reject("InvalidTiming", Duty)`; a deadline or a recurrence on the policy or a
% rule is `reject("TimingOutsideDuty", Node)`. `due2:instanceScope` gives `duty_scope(Y,
% InstScope)`, `member` by default.

%*! node_deadline(Duty, Lit)

`Duty` states `dprod:deadline Lit`. At most one, an `xsd:dateTime` with a timezone or an
`xsd:duration` (due2-diagnostics.md, InvalidTiming).
*%
node_deadline(Duty, Lit) :- duty_node(Duty), triple(Duty, Pred, Lit), voc(deadline, Pred),
    timing_predicate(Pred).
reject("InvalidTiming", Duty) :- duty_node(Duty), #count { Lit : node_deadline(Duty, Lit) } > 1.
reject("InvalidTiming", Duty) :- node_deadline(Duty, Lit), not deadline_kind(Lit, _).
reject("InvalidTiming", Duty) :- node_deadline(Duty, Lit), unplaceable(Lit, R), off_shape(R).
% Timing belongs to duties (due2-profiles.md §7).
reject("TimingOutsideDuty", Node) :- triple(Node, Pred, _), timing_predicate(Pred), policy(Node).
reject("TimingOutsideDuty", Node) :- triple(Node, Pred, _), timing_predicate(Pred), rule(Node).
% Recurrence needs occurrences, which the spike does not compute (decisions/0009 #7). The whole
% vector declines, since a duty's instances would otherwise be read without them.
unsupported("recurrence") :- duty_node(Duty), triple(Duty, Pred, _), voc(recurrence, Pred),
    timing_predicate(Pred).

%*! deadline_kind(Lit, K)

The deadline `Lit` is `absolute`, an `xsd:dateTime`, or `relative`, an `xsd:duration`. A
relative deadline counts from the instance's activation (due2-workflows.md §5.3).
*%
deadline_kind(Lit, absolute) :- node_deadline(_, Lit), term_kind(Lit, K), voc(xsd_dateTime, K).
deadline_kind(Lit, relative) :- node_deadline(_, Lit), term_kind(Lit, K), voc(xsd_duration, K).

%*! duty_deadline(Y, Lit)

The duty atom `Y` has the deadline `Lit`, its duty's.
*%
duty_deadline(Y, Lit) :- duty_of(Y, Duty), node_deadline(Duty, Lit).

%*! duty_scope(Y, InstScope)

The duty atom `Y` has instance scope `InstScope`: `member`, the default, or `grant`. The scopes
are those of due2-workflows.md §5.3.
*%
duty_scope(Y, InstScope) :- duty_of(Y, Duty), triple(Duty, Pred, Iri), voc(instanceScope, Pred),
    voc(InstScope, Iri), scope_value(InstScope).
duty_scope(Y, member) :- duty_of(Y, Duty), not states_scope(Duty).
% No diagnostic covers a value outside due2:member and due2:grant, or two values, so the
% vector is declined rather than rejected under a guessed code.
unsupported("duty: instance scope") :- states_scope(Duty),
    #count { InstScope : duty_scope(Y, InstScope), duty_of(Y, Duty) } != 1.

%*! scope_value(InstScope)

`InstScope` names an instance scope: `member` or `grant`.
*%
scope_value(member; grant).

%*! states_scope(Duty)

`Duty` states a `due2:instanceScope`.
*%
states_scope(Duty) :- duty_node(Duty), triple(Duty, Pred, _), voc(instanceScope, Pred).
