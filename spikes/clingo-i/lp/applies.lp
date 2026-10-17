%# applies.lp: the parts of an atom, and its finding
%
% Splits each atom into parts, gives each part a truth value against the request, and derives
% the atom's finding, the Kleene conjunction of its parts (due2-workflows.md §5.2). A request
% field that is absent makes its part `u`, never `f`. Variable letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `atom/1`, `atom_action/2`, `atom_target/2`, `atom_party/3` (structure.lp);
%   `request_action/1`, `request_target/1`, `request_absent/1`, `request_party/2` (driver);
%   `closure/3`, `le_k/3` (lift.lp); `rank/2` (kleene.lp); `top_constraint/2`,
%   `top_refinement/2` (constraint.lp); `holds/2` of constraint nodes (compare.lp).
% - **Provides:** `part_of/2`, `item/1`, `reaches/2`, `action_matches/1`, `target_matches/1`,
%   `named/1`, `party_matches/2`, `atom_constraint/2`, `holds/2`.

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

% Only a request action that is the atom's action or narrower matches.

%*! reaches(A, B)

The request action `A` is included in `B`: the reflexive-transitive closure of `odrl:includedIn`
from `A`, over declared edges only.
*%
reaches(A, A) :- request_action(A).
reaches(A, B) :- reaches(A, Mid), closure(includedIn, Mid, B).

%*! action_matches(X)

The request action is atom `X`'s action, or narrower.
*%
action_matches(X) :- atom_action(X, B), request_action(A), reaches(A, B).
holds(part(X, action), t) :- action_matches(X).
% `not` here reads the closure, which is closed-world over declared edges (due2-profiles.md §6),
% so f is the right value, not a u turned into f.
holds(part(X, action), f) :- atom(X), not action_matches(X).

%## Target

% The requested asset is the target, or part of it under the typed partOf closure
% (due2-profiles.md §6). An absent request target is u.

%*! target_matches(X)

The request target is atom `X`'s target, or part of it.
*%
target_matches(X) :- atom_target(X, T), request_target(T).
target_matches(X) :- atom_target(X, T), request_target(Asked), le_k(Asked, T, asset).
holds(part(X, target), u) :- atom(X), request_absent(target).
holds(part(X, target), t) :- target_matches(X).
holds(part(X, target), f) :- atom(X), request_target(_), not target_matches(X).

%## Party

% For each match key: a named party that is the atom's party, or part of it. A function the
% request names no party for is u.

%*! named(F)

The request names a party for function `F`.
*%
named(F) :- request_party(F, _).

%*! party_matches(X, F)

A party the request names for `F` is atom `X`'s party for `F`, or part of it.
*%
party_matches(X, F) :- atom_party(X, F, Party), request_party(F, Party).
party_matches(X, F) :- atom_party(X, F, Party), request_party(F, Asked),
    le_k(Asked, Party, party).
holds(part(X, party(F)), u) :- atom_party(X, F, _), not named(F).
holds(part(X, party(F)), t) :- party_matches(X, F).
holds(part(X, party(F)), f) :- atom_party(X, F, _), named(F), not party_matches(X, F).

%## Constraints

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
