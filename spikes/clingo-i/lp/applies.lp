% applies.lp: the parts of an atom and whether it applies (workflows §5.2).

part_item(X, part(X, action)) :- atom(X).
part_item(X, part(X, target)) :- atom(X).
part_item(X, part(X, party(F))) :- atom_party(X, F, _).
item(I) :- part_item(_, I).
item(applies(X)) :- atom(X).

% action: only a narrower request action matches, under reflexive-transitive includedIn.
reaches(A, A) :- req_action(A).
reaches(A, B) :- reaches(A, C), closure(includedIn, C, B).
action_matches(X) :- atom_action(X, B), req_action(A), reaches(A, B).
holds(part(X, action), t) :- action_matches(X).
holds(part(X, action), f) :- atom(X), not action_matches(X).

% target: identity; an absent request target is unknown.
holds(part(X, target), u) :- atom(X), req_absent(target).
holds(part(X, target), t) :- atom_target(X, T), req_target(T).
holds(part(X, target), f) :- atom_target(X, T), req_target(Q), Q != T.

% party, for each match key: an unnamed function is unknown.
named(F) :- req_party(F, _).
holds(part(X, party(F)), u) :- atom_party(X, F, _), not named(F).
holds(part(X, party(F)), t) :- atom_party(X, F, P), req_party(F, P).
holds(part(X, party(F)), f) :- atom_party(X, F, P), req_party(F, Q), Q != P.

% applies: the Kleene conjunction of the parts.
holds(applies(X), V) :- atom(X), rank(V, N), N = #min { R : part_item(X, I), holds(I, W), rank(W, R) }.
