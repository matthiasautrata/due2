%# applies.lp: the parts of an atom, and its finding
%
% Splits each atom into parts, gives each part a truth value against the request, and derives
% the atom's finding, the Kleene conjunction of its parts (due2-workflows.md §5.2). A request
% field that is absent makes its part `u`, never `f`. Variable letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `atom/1`, `atom_action/2`, `atom_target/2`, `atom_party/3` (structure.lp);
%   `request_action/1`, `request_target/1`, `request_absent/1`, `request_party/2` (driver);
%   `closure/4`, `le_k/4` (lift.lp); `policy/1`, `space/2`
%   (structure.lp); `rank/2` (kleene.lp); `top_constraint/2`,
%   `top_refinement/2` (constraint.lp); `holds/2` of constraint nodes (compare.lp).
% - **Provides:** `part_of/2`, `item/1`, `reaches/3`, `action_matches/2`, `action_matches/1`,
%   `target_matches/2`, `target_matches/1`, `named/1`, `party_matches/3`, `party_matches/2`,
%   `atom_constraint/2`, `holds/2`; extends `unsupported/1` (lift.lp).

%*! part_of(X, I)

Item `I` is a part of atom `X`: `part(X, action)`, `part(X, target)`, and `part(X, party(F))`
for each match key `F` the atom has a party for, and `part(X, cons(C))` for each constraint
root `C` of the atom (`atom_constraint/2`).
*%
part_of(X, part(X, action)) :- atom(X).
part_of(X, part(X, target)) :- atom(X).
part_of(X, part(X, party(F))) :- atom_party(X, F, _).
part_of(X, part(X, cons(C))) :- atom_constraint(X, C).

%*! item(I)

`I` must have exactly one truth value: each part, `applies(X)` for each atom, and each
constraint node. compare.lp adds the nodes, and integrity.lp holds the constraint.
*%
item(I) :- part_of(_, I).
item(applies(X)) :- atom(X).

%*! holds(I, V)

Item `I` has truth value `V`: `f`, `u`, or `t`. For `applies(X)` this is atom `X`'s finding.
It is the value before completion; completion.lp gives each world's value.
*%

%## Action

% The action part is `t` when `request_action ⊑ atom_action` under the reflexive-transitive
% `includedIn` closure, and `f` otherwise: only a request action that is the atom's action, or
% narrower, matches.

%*! reaches(P, A, B)

In policy `P`'s data space, the request action `A` is included in `B`: the reflexive-transitive
closure of `odrl:includedIn` from `A`, over declared edges only.
*%
reaches(P, A, A) :- policy(P), request_action(A).
reaches(P, A, B) :- reaches(P, A, Mid), closure(P, includedIn, Mid, B).

%*! action_matches(X, P)

In policy `P`'s data space, the request action is atom `X`'s action, or narrower.
*%
action_matches(X, P) :- space(X, P), atom_action(X, B), request_action(A), reaches(P, A, B).

%*! action_matches(X)

The request action is atom `X`'s action, or narrower, in a data space of `X`.
*%
action_matches(X) :- action_matches(X, _).
holds(part(X, action), t) :- action_matches(X).
% `not` here reads the closure, which is closed-world over declared edges (due2-profiles.md §6),
% so f is the right value, not a u turned into f.
holds(part(X, action), f) :- atom(X), not action_matches(X).

%## Target

% The target part is `u` when `request_absent(target)` holds. Otherwise it is `t` when the
% requested asset is the target, or part of it under the typed `partOf` closure
% (`le_k(Asked, T, asset)`, due2-profiles.md §6), and `f` otherwise (`target_matches/1`).

%*! target_matches(X, P)

In policy `P`'s data space, the request target is atom `X`'s target, or part of it.
*%
target_matches(X, P) :- space(X, P), atom_target(X, T), request_target(T).
target_matches(X, P) :- space(X, P), atom_target(X, T), request_target(Asked),
    le_k(P, Asked, T, asset).

%*! target_matches(X)

The request target is atom `X`'s target, or part of it, in a data space of `X`.
*%
target_matches(X) :- target_matches(X, _).
holds(part(X, target), u) :- atom(X), request_absent(target).
holds(part(X, target), t) :- target_matches(X).
holds(part(X, target), f) :- atom(X), request_target(_), not target_matches(X).

%## Party

% A party part is checked for each `atom_party(X, F, Party)` with `F` a match key. It is `u` when
% the request names no party for `F`, `t` when a named party is `Party` or part of it
% (`le_k(Asked, Party, party)`), and `f` otherwise (`party_matches/2`). An atom with no assignee
% has no party part.

%*! named(F)

The request names a party for function `F`.
*%
named(F) :- request_party(F, _).

%*! party_matches(X, F, P)

In policy `P`'s data space, a party the request names for `F` is atom `X`'s party for `F`, or
part of it.
*%
party_matches(X, F, P) :- space(X, P), atom_party(X, F, Party), request_party(F, Party).
party_matches(X, F, P) :- space(X, P), atom_party(X, F, Party), request_party(F, Asked),
    le_k(P, Asked, Party, party).

%*! party_matches(X, F)

A party the request names for `F` is atom `X`'s party for `F`, or part of it, in a data space of
`X`.
*%
party_matches(X, F) :- party_matches(X, F, _).
holds(part(X, party(F)), u) :- atom_party(X, F, _), not named(F).
holds(part(X, party(F)), t) :- party_matches(X, F).
holds(part(X, party(F)), f) :- atom_party(X, F, _), named(F), not party_matches(X, F).

%## Constraints

% A constraint part, `part(X, cons(C))`, exists for each root `C` of `atom_constraint(X, C)`: the
% rule's constraint roots and the action term's refinement roots. It takes the node's value,
% `holds(c(C), V)`.

%*! atom_constraint(X, C)

`C` is a constraint root of atom `X`: a constraint of its rule, or a refinement of its action
term. Each is one conjunct of the finding.
*%
atom_constraint(a(R, Term, T, Party), C) :- atom(a(R, Term, T, Party)), top_constraint(R, C).
atom_constraint(a(R, Term, T, Party), C) :- atom(a(R, Term, T, Party)), top_refinement(Term, C).
holds(part(X, cons(C)), V) :- atom_constraint(X, C), holds(c(C), V).

%## The finding

% The Kleene conjunction of the parts. `#min` is used as a function: `Min` is the least rank
% among the atom's parts, and `V` is the value of that rank. Every atom has an action and a
% target part, so the set is never empty. If it were, `#min` would be `#sup`, no rank would
% match it, `applies(X)` would have no value, and the item constraint in integrity.lp would fail.
holds(applies(X), V) :- atom(X), rank(V, Min),
    Min = #min { N : part_of(X, I), holds(I, Vp), rank(Vp, N) }.


%## Shared atoms

% An atom in two policies is read in each one's data space (`space/2`). The program keeps one
% finding per atom, so where two of its spaces read a part apart, the vector declines (lift.lp,
% *Hierarchies*; `test_shared_rule_read_apart_declines`).
unsupported("shared node: read apart by its policies") :- space(X, P), space(X, Q),
    action_matches(X, P), not action_matches(X, Q).
unsupported("shared node: read apart by its policies") :- space(X, P), space(X, Q),
    target_matches(X, P), not target_matches(X, Q).
unsupported("shared node: read apart by its policies") :- space(X, P), space(X, Q),
    party_matches(X, F, P), not party_matches(X, F, Q).
