%# applies.lp: the parts of an atom, and its finding
%
% Splits each atom into parts, gives each part a truth value against the request, and derives
% the atom's finding, the Kleene conjunction of its parts (due2-workflows.md §5.2). A request
% field that is absent makes its part `u`, never `f`. Variable letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `atom/1`, `atom_action/2`, `atom_target/2`, `atom_party/3` (structure.lp);
%   `request_action/1`, `request_target/1`, `request_absent/1`, `request_party/2` (driver);
%   `closure/3` (lift.lp); `rank/2` (kleene.lp).
% - **Provides:** `part_of/2`, `item/1`, `reaches/2`, `action_matches/1`, `named/1`, `holds/2`.

%*! part_of(X, I)

Item `I` is a part of atom `X`: `part(X, action)`, `part(X, target)`, and `part(X, party(F))`
for each match key `F` the atom has a party for.
*%
part_of(X, part(X, action)) :- atom(X).
part_of(X, part(X, target)) :- atom(X).
part_of(X, part(X, party(F))) :- atom_party(X, F, _).

%*! item(I)

`I` must have exactly one truth value: each part, and `applies(X)` for each atom. The
constraint is in kleene.lp.
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

% Identity. An absent request target is u.
holds(part(X, target), u) :- atom(X), request_absent(target).
holds(part(X, target), t) :- atom_target(X, T), request_target(T).
holds(part(X, target), f) :- atom_target(X, T), request_target(Asked), Asked != T.

%## Party

% For each match key. A function the request names no party for is u.

%*! named(F)

The request names a party for function `F`.
*%
named(F) :- request_party(F, _).
holds(part(X, party(F)), u) :- atom_party(X, F, _), not named(F).
holds(part(X, party(F)), t) :- atom_party(X, F, Party), request_party(F, Party).
holds(part(X, party(F)), f) :- atom_party(X, F, Party), request_party(F, Asked), Asked != Party.

%## The finding

% The Kleene conjunction of the parts. `#min` is used as a function: `Min` is the least rank
% among the atom's parts, and `V` is the value of that rank. Every atom has an action and a
% target part, so the set is never empty. If it were, `#min` would be `#sup`, no rank would
% match it, `applies(X)` would have no value, and the item constraint in kleene.lp would fail.
holds(applies(X), V) :- atom(X), rank(V, Min),
    Min = #min { N : part_of(X, I), holds(I, Vp), rank(Vp, N) }.
