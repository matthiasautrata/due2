%# resolve.lp: candidates, conflict, verdict, and basis of one completion
%
% Resolves one world: which atoms apply in it, which conflict removes, and what the verdict is
% (due2-workflows.md §6.1, §6.2, §6.4). Every relation carries the world `W`, and within a world
% every completed value is `f` or `t`, so negation as failure reads a definite `f`: `not
% deny(W)` means "no surviving forbid in this completion", never "unknown". Variable letters:
% DESIGN.md § Vocabulary.
%
% - **Consumes:** `completed/3`, `world/1` (completion.lp); `atom_effect/2`, `atom_policy/2`,
%   `conflict/2` (structure.lp).
% - **Provides:** `applying/2`, `candidate/2`, `forbidding/2`, `has_candidate/2`,
%   `has_forbidding/2`, `eliminated/2`, `deny/1`, `ready/1`, `verdict/2`, `basis/3`.

%## Candidates

%*! applying(W, X)

Atom `X` applies in world `W`: its completed finding is `t`.
*%
applying(W, X) :- completed(W, applies(X), t).

%*! candidate(W, X)

Atom `X` is a permission that applies in world `W`. See due2-workflows.md §6.1.
*%
candidate(W, X) :- applying(W, X), atom_effect(X, permit).

%*! forbidding(W, X)

Atom `X` is a prohibition that applies in world `W`.
*%
forbidding(W, X) :- applying(W, X), atom_effect(X, forbid).

%## Conflict within the policy

% By the policy's conflict strategy (due2-workflows.md §6.2 #1).

%*! has_candidate(W, P)

Policy `P` has a candidate in world `W`.
*%
has_candidate(W, P) :- candidate(W, X), atom_policy(X, P).

%*! has_forbidding(W, P)

Policy `P` has an applying prohibition in world `W`.
*%
has_forbidding(W, P) :- forbidding(W, X), atom_policy(X, P).

%*! eliminated(W, X)

Atom `X` applies in world `W` but its policy's conflict strategy removes it: under `prohibit` a
forbid removes the candidates, under `perm` a candidate removes the forbids, and under
`invalid` a candidate and a forbid together void the policy, removing all its applying atoms.
*%
eliminated(W, X) :- candidate(W, X), atom_policy(X, P), conflict(P, prohibit), has_forbidding(W, P).
eliminated(W, X) :- forbidding(W, X), atom_policy(X, P), conflict(P, perm), has_candidate(W, P).
eliminated(W, X) :- applying(W, X), atom_policy(X, P), conflict(P, invalid),
    has_candidate(W, P), has_forbidding(W, P).

%## Across policies, and the verdict

%*! deny(W)

A prohibition survives in world `W`. Across policies the combination is prohibit-overrides
(due2-workflows.md §6.2 #2): a surviving forbid eliminates every candidate.
*%
deny(W) :- forbidding(W, X), not eliminated(W, X).

%*! ready(W)

A candidate survives in world `W` and nothing denies. Without duties, every surviving
candidate is ready (due2-workflows.md §6.1); `Pending` needs duties, which are declined (#49).
*%
ready(W) :- candidate(W, X), not eliminated(W, X), not deny(W).

%*! verdict(W, Verdict)

World `W` has verdict `Verdict`: `"Deny"`, `"Permit"`, or `"NotApplicable"`. Exactly one, by
the constraint in kleene.lp. interpret.py combines the verdicts of every completion into the
reply's verdict (due2-workflows.md §6.4).
*%
verdict(W, "Deny") :- deny(W).
verdict(W, "Permit") :- ready(W).
verdict(W, "NotApplicable") :- world(W), not deny(W), not ready(W).

%*! basis(W, X, Role)

Atom `X` determines world `W`'s verdict, in role `prohibition` or `permission`: the surviving
forbids for a Deny, the surviving candidates for a Permit. A NotApplicable world has no basis
(due2-workflows.md §6.4).
*%
basis(W, X, prohibition) :- forbidding(W, X), not eliminated(W, X).
basis(W, X, permission) :- candidate(W, X), not eliminated(W, X), not deny(W).

#show verdict/2.
#show basis/3.
