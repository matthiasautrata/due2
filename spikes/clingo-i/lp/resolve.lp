% resolve.lp: candidates, conflict, verdict, and basis of one completion (workflows §6.1-§6.4).
% Every relation carries the world W; every value is f or t there, so negation as failure is sound.

applying(W, X) :- cval(W, applies(X), t).
candidate(W, X) :- applying(W, X), atom_effect(X, permit).
forbidding(W, X) :- applying(W, X), atom_effect(X, forbid).

% Conflict within the policy (§6.2.1).
has_candidate(W, P) :- candidate(W, X), atom_policy(X, P).
has_forbidding(W, P) :- forbidding(W, X), atom_policy(X, P).
eliminated(W, X) :- candidate(W, X), atom_policy(X, P), conflict(P, prohibit), has_forbidding(W, P).
eliminated(W, X) :- forbidding(W, X), atom_policy(X, P), conflict(P, perm), has_candidate(W, P).
eliminated(W, X) :- applying(W, X), atom_policy(X, P), conflict(P, invalid),
    has_candidate(W, P), has_forbidding(W, P).

% Across policies (§6.2.2), prohibit-overrides: a surviving forbid eliminates every candidate.
deny(W) :- forbidding(W, X), not eliminated(W, X).
% No duties yet, so every surviving candidate is ready.
ready(W) :- candidate(W, X), not eliminated(W, X), not deny(W).

verdict(W, "Deny") :- deny(W).
verdict(W, "Permit") :- ready(W).
verdict(W, "NotApplicable") :- world(W), not deny(W), not ready(W).

% The atoms that determine this completion's verdict (§6.4).
basis(W, X, prohibition) :- forbidding(W, X), not eliminated(W, X).
basis(W, X, permission) :- candidate(W, X), not eliminated(W, X), not deny(W).

#show verdict/2.
#show basis/3.
