% resolve.lp: candidates, conflict, and the verdict of one completion (workflows §6.1-§6.4).
% Every value is f or t here, so negation as failure is sound.

applying(X) :- cval(applies(X), t).
candidate(X) :- applying(X), atom_effect(X, permit).
forbidding(X) :- applying(X), atom_effect(X, forbid).

% Conflict within the policy (§6.2.1).
has_candidate(P) :- candidate(X), atom_policy(X, P).
has_forbidding(P) :- forbidding(X), atom_policy(X, P).
eliminated(X) :- candidate(X), atom_policy(X, P), conflict(P, prohibit), has_forbidding(P).
eliminated(X) :- forbidding(X), atom_policy(X, P), conflict(P, perm), has_candidate(P).
eliminated(X) :- applying(X), atom_policy(X, P), conflict(P, invalid), has_candidate(P), has_forbidding(P).

% Across policies (§6.2.2), prohibit-overrides: a surviving forbid eliminates every candidate.
deny :- forbidding(X), not eliminated(X).
% No duties yet, so every surviving candidate is ready.
ready :- candidate(X), not eliminated(X), not deny.

verdict("Deny") :- deny.
verdict("Permit") :- ready.
verdict("NotApplicable") :- not deny, not ready.

#show verdict/1.
