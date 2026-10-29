%# applies.lp: the parts of an atom, and its finding
%
% Splits each atom into parts, gives each part a truth value against the request, and derives
% the atom's finding, the Kleene conjunction of its parts (due2-workflows.md §5.2). A request
% field that is absent makes its part `u`, never `f`. Variable letters: DESIGN.md § Vocabulary.
%
% An atom has one entry for each policy that states its rule (due2-workflows.md §3.1), and each
% entry is read in its own policy's data space (decisions/0050 #1). So every part, and the
% finding, is keyed by the atom and the policy: `part(X, P, action)` and `applies(X, P)`. An
% atom two policies share has two findings, which differ where the two data spaces read it apart.
%
% - **Consumes:** `atom/1`, `atom_action/2`, `atom_target/2`, `atom_party/3` (structure.lp);
%   `request_action/1`, `request_target/1`, `request_absent/1`, `request_party/2` (driver);
%   `closure/4`, `le_k/4` (lift.lp); `policy/1`, `space/2`
%   (structure.lp); `rank/2` (kleene.lp); `top_constraint/2`,
%   `top_refinement/2` (constraint.lp); `holds/2` of constraint nodes (compare.lp).
% - **Provides:** `part_of/3`, `item/1`, `reaches/3`, `action_matches/2`, `target_matches/2`,
%   `named/1`, `party_matches/3`, `atom_constraint/2`, `holds/2`.

%*! part_of(X, P, I)

Item `I` is a part of atom `X`'s entry in policy `P`: `part(X, P, action)`, `part(X, P, target)`,
and `part(X, P, party(F))` for each match key `F` the atom has a party for, and
`part(X, P, cons(C))` for each constraint root `C` of the atom (`atom_constraint/2`).
*%
part_of(X, P, part(X, P, action)) :- space(X, P), atom(X).
part_of(X, P, part(X, P, target)) :- space(X, P), atom(X).
part_of(X, P, part(X, P, party(F))) :- space(X, P), atom_party(X, F, _).
part_of(X, P, part(X, P, cons(C))) :- space(X, P), atom_constraint(X, C).

%*! item(I)

`I` must have exactly one truth value: each part, `applies(X, P)` for each entry, and each
constraint node in each of its data spaces. compare.lp adds the nodes, and integrity.lp checks
it.
*%
item(I) :- part_of(_, _, I).
item(applies(X, P)) :- atom(X), space(X, P).

%*! holds(I, V)

Item `I` has truth value `V`: `f`, `u`, or `t`. For `applies(X, P)` this is the finding of atom
`X`'s entry in policy `P`. It is the value before completion; completion.lp gives each world's
value.
*%

%## Action

% The action part is `t` when `request_action ⊑ atom_action` under the reflexive-transitive
% `includedIn` closure of the entry's data space, and `f` otherwise: only a request action that is
% the atom's action, or narrower, matches.

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
holds(part(X, P, action), t) :- action_matches(X, P).
% `not` here reads the closure, which is closed-world over declared edges (due2-profiles.md §6),
% so f is the right value, not a u turned into f.
holds(part(X, P, action), f) :- atom(X), space(X, P), not action_matches(X, P).

%## Target

% The target part is `u` when `request_absent(target)` holds. Otherwise it is `t` when the
% requested asset is the target, or part of it under the typed `partOf` closure of the entry's
% data space (`le_k(P, Asked, T, asset)`, due2-profiles.md §6), and `f` otherwise
% (`target_matches/2`).

%*! target_matches(X, P)

In policy `P`'s data space, the request target is atom `X`'s target, or part of it.
*%
target_matches(X, P) :- space(X, P), atom_target(X, T), request_target(T).
target_matches(X, P) :- space(X, P), atom_target(X, T), request_target(Asked),
    le_k(P, Asked, T, asset).
holds(part(X, P, target), u) :- atom(X), space(X, P), request_absent(target).
holds(part(X, P, target), t) :- target_matches(X, P).
holds(part(X, P, target), f) :- atom(X), space(X, P), request_target(_),
    not target_matches(X, P).

%## Party

% A party part is checked for each `atom_party(X, F, Party)` with `F` a match key. It is `u` when
% the request names no party for `F`, `t` when a named party is `Party` or part of it in the
% entry's data space (`le_k(P, Asked, Party, party)`), and `f` otherwise (`party_matches/3`). An
% atom with no assignee has no party part.

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
holds(part(X, P, party(F)), u) :- atom_party(X, F, _), space(X, P), not named(F).
holds(part(X, P, party(F)), t) :- party_matches(X, F, P).
holds(part(X, P, party(F)), f) :- atom_party(X, F, _), space(X, P), named(F),
    not party_matches(X, F, P).

%## Constraints

% A constraint part, `part(X, P, cons(C))`, exists for each root `C` of `atom_constraint(X, C)`:
% the rule's constraint roots and the action term's refinement roots. It takes the node's value in
% the entry's data space, `holds(c(C, P), V)`.

%*! atom_constraint(X, C)

`C` is a constraint root of atom `X`: a constraint of its rule, or a refinement of its action
term. Each is one conjunct of the finding.
*%
atom_constraint(a(R, Term, T, Party), C) :- atom(a(R, Term, T, Party)), top_constraint(R, C).
atom_constraint(a(R, Term, T, Party), C) :- atom(a(R, Term, T, Party)), top_refinement(Term, C).
holds(part(X, P, cons(C)), V) :- atom_constraint(X, C), space(X, P), holds(c(C, P), V).

%## The finding

% The Kleene conjunction of the parts. `#min` is used as a function: `Min` is the least rank
% among the entry's parts, and `V` is the value of that rank. Every entry has an action and a
% target part, so the set is never empty. If it were, `#min` would be `#sup`, no rank would
% match it, `applies(X, P)` would have no value, and integrity.lp's one-value check would
% derive a defect.
holds(applies(X, P), V) :- atom(X), space(X, P), rank(V, Min),
    Min = #min { N : part_of(X, P, I), holds(I, Vp), rank(Vp, N) }.
