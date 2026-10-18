%# resolve.lp: candidates, conflict, frontier, verdict, and basis of one completion
%
% Resolves one world, in the four steps of due2-workflows.md §6.1–§6.4, in order: the
% candidates, with the permissions a violated precondition closes left out; conflict; the
% frontier of alternatives, by outstanding duties; and the verdict. Every relation carries the
% world `W`, and within a world every completed value is `f` or `t`, so negation as failure
% reads a definite `f`: `not deny(W)` means "nothing denies in this completion", never
% "unknown". Variable letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `completed/3`, `world/1` (completion.lp); `atom_effect/2`, `atom_policy/2`,
%   `conflict/2`, `pre/2`, `obligation/1` (structure.lp); `passed/1` (duty.lp);
%   `config_violations/1` (driver).
% - **Provides:** `applying/2`, `permitting/2`, `violated/2`, `closed/2`, `candidate/2`,
%   `outstanding/3`, `forbidding/2`, `has_candidate/2`, `has_forbidding/2`, `eliminated/2`,
%   `deny/1`, `survives/2`, `not_within/3`, `dominated/2`, `frontier/2`, `has_outstanding/2`,
%   `ready/1`, `pending/1`, `verdict/2`, `basis/3`.

%## Candidates

%*! applying(W, X)

Atom `X` applies in world `W`: its completed finding is `t`.
*%
applying(W, X) :- completed(W, applies(X), t).

%*! permitting(W, X)

Atom `X` is a permission that applies in world `W`.
*%
permitting(W, X) :- applying(W, X), atom_effect(X, permit).

%*! violated(W, Y)

In world `W`, the instance of duty atom `Y` is violated: it is not fulfilled, and its deadline
has passed. Violation is defined in due2-workflows.md §5.3. Only an instance has a `fulfilled`
value.
*%
violated(W, Y) :- completed(W, fulfilled(Y), f), passed(Y).

%*! closed(W, X)

In world `W`, the permission `X` applies, but a precondition of it is owed and violated, so the
route can no longer be taken and `X` is no candidate. This is the closure of due2-workflows.md
§6.1. It comes before conflict, so a closed permission removes no prohibition. A violated
precondition removes its candidate under either value of `config.violations`.
*%
closed(W, X) :- permitting(W, X), pre(X, Y), completed(W, owed(Y), t), violated(W, Y).

%*! candidate(W, X)

Atom `X` is a permission that applies in world `W` and is not closed. It is a candidate in the
sense of due2-workflows.md §6.1.
*%
candidate(W, X) :- permitting(W, X), not closed(W, X).

%*! outstanding(W, X, Y)

In world `W`, the duty atom `Y` is in the outstanding set of the candidate `X`: a precondition
of `X` that is owed and not fulfilled, so its open value is `t`. The set is that of
due2-workflows.md §6.1. A violated precondition that is owed closed `X` instead.
*%
outstanding(W, X, Y) :- candidate(W, X), pre(X, Y), completed(W, owed(Y), t),
    completed(W, fulfilled(Y), f).

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

%## Across policies

%*! deny(W)

Something denies in world `W`: a prohibition survives, or a violated obligation in force denies
under the configuration. These are the conditions of due2-workflows.md §6.4. The second needs
`config.violations` to be `deny`. Across policies the combination is prohibit-overrides
(due2-workflows.md §6.2 #2): a surviving forbid eliminates every candidate. Under `deny`, a
violated obligation acts as a surviving forbid. Under `ignore`, the default, whether stated or
absent, obligations never affect the verdict.
*%
deny(W) :- forbidding(W, X), not eliminated(W, X).
deny(W) :- config_violations(deny), obligation(Y), completed(W, in_force(Y), t), violated(W, Y).

%*! survives(W, X)

The candidate `X` survives conflict in world `W`, and nothing denies.
*%
survives(W, X) :- candidate(W, X), not eliminated(W, X), not deny(W).

%## The frontier

% Alternatives are sets of outstanding duties, compared by duty atom (due2-workflows.md §6.3).
% Two candidates with one set are one alternative, so the program never forms the sets: it
% compares the candidates, and the collapse happens where interpret.py projects them.

%*! not_within(W, X, X2)

In world `W`, the surviving candidate `X` has an outstanding duty that the surviving candidate
`X2` lacks, so `X`'s set is not a subset of `X2`'s.
*%
not_within(W, X, X2) :- outstanding(W, X, Y), survives(W, X2), not outstanding(W, X2, Y).

%*! dominated(W, X2)

In world `W`, a surviving candidate's outstanding set is a strict subset of `X2`'s: a subset
(`not not_within(W, X, X2)`) that is not equal (`not_within(W, X2, X)`).
*%
dominated(W, X2) :- survives(W, X), survives(W, X2), not not_within(W, X, X2),
    not_within(W, X2, X).

%*! frontier(W, X)

The surviving candidate `X` is in world `W`'s frontier: no other's outstanding set is a strict
subset of its own.
*%
frontier(W, X) :- survives(W, X), not dominated(W, X).

%*! has_outstanding(W, X)

The candidate `X` has an outstanding duty in world `W`.
*%
has_outstanding(W, X) :- outstanding(W, X, _).

%## The verdict

%*! ready(W)

World `W`'s frontier has a ready alternative: one with no outstanding duty. The empty set is a
strict subset of every other, so then it is the only alternative of the frontier.
*%
ready(W) :- frontier(W, X), not has_outstanding(W, X).

%*! pending(W)

World `W`'s frontier is not empty, and has no ready alternative.
*%
pending(W) :- frontier(W, _), not ready(W).

%*! verdict(W, Verdict)

World `W` has verdict `Verdict`: `"Deny"`, `"Permit"`, `"Pending"`, or `"NotApplicable"`, the
first whose condition holds, in that order. The order is that of due2-workflows.md §6.4.
Exactly one, by the constraint in integrity.lp. interpret.py combines the verdicts of every
completion into the reply's verdict.
*%
verdict(W, "Deny") :- deny(W).
verdict(W, "Permit") :- ready(W).
verdict(W, "Pending") :- pending(W).
verdict(W, "NotApplicable") :- world(W), not deny(W), not ready(W), not pending(W).

%*! basis(W, X, Role)

Atom `X` determines world `W`'s verdict in role `Role`. The roles follow due2-workflows.md §6.4:
`prohibition` for each surviving forbid, `permission` for each candidate of the frontier, under
`Permit` the ready ones; `duty` for each outstanding duty of the frontier under `Pending`; and
`closed` for each closed permission under `NotApplicable`. A violated obligation that denies has
no role here: role `obligation` names every obligation in force under any verdict, and
explain.lp reads it from the findings.
*%
basis(W, X, prohibition) :- forbidding(W, X), not eliminated(W, X).
basis(W, X, permission) :- frontier(W, X).
basis(W, Y, duty) :- pending(W), frontier(W, X), outstanding(W, X, Y).
basis(W, X, closed) :- verdict(W, "NotApplicable"), closed(W, X).

#show verdict/2.
#show basis/3.
