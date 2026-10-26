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
%   `outstanding/3`, `forbidding/2`, `has_candidate/2`, `has_forbidding/2`,
%   `entry_eliminated/3`, `entry_kept/2`, `eliminated/2`, `deny/1`, `survives/2`,
%   `not_within/3`, `dominated/2`, `frontier/2`, `has_outstanding/2`,
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

% By the policy's conflict strategy (due2-workflows.md §6.2 #1). A `permit` or `forbid` atom
% takes part once in each policy that states it (`atom_policy/2`): its entry in that policy
% (due2-workflows.md §6.2, *Entries*). Each policy's fold reads its own entries, and removes an
% entry, not the atom.

%*! has_candidate(W, P)

Policy `P` has a candidate in world `W`: an atom that is a candidate and has an entry in `P`.
*%
has_candidate(W, P) :- candidate(W, X), atom_policy(X, P).

%*! has_forbidding(W, P)

Policy `P` has an applying prohibition in world `W`.
*%
has_forbidding(W, P) :- forbidding(W, X), atom_policy(X, P).

%*! entry_eliminated(W, X, P)

Atom `X` applies in world `W`, and policy `P`'s conflict strategy removes its entry in `P`: under
`prohibit` a forbid removes the candidates, under `perm` a candidate removes the forbids, and
under `invalid` a candidate and a forbid together void the policy, removing its applying permit
and forbid entries. A void policy's root obligations stay in force (decisions/0029).
*%
entry_eliminated(W, X, P) :- candidate(W, X), atom_policy(X, P), conflict(P, prohibit),
    has_forbidding(W, P).
entry_eliminated(W, X, P) :- forbidding(W, X), atom_policy(X, P), conflict(P, perm),
    has_candidate(W, P).
entry_eliminated(W, X, P) :- applying(W, X), not atom_effect(X, oblige), atom_policy(X, P),
    conflict(P, invalid), has_candidate(W, P), has_forbidding(W, P).

%*! entry_kept(W, X)

The applying permit or forbid atom `X` has an entry that its policy does not eliminate in
world `W`.
*%
entry_kept(W, X) :- applying(W, X), not atom_effect(X, oblige), atom_policy(X, P),
    not entry_eliminated(W, X, P).

%*! eliminated(W, X)

Atom `X` applies in world `W`, and every policy that states it removes its entry there. An atom
is not eliminated while any of its entries survives (due2-workflows.md §6.2, *Entries*), so a
permission that two policies state is removed only when both remove it. structure.lp admits
one policy, so no vector has a shared atom; `test_shared_permission_survives_in_its_other_policy`
runs this rule on hand-written facts.
*%
eliminated(W, X) :- entry_eliminated(W, X, _), not entry_kept(W, X).

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

%## The cautious basis

% Solve 2 reports a basis row only if it holds in every completion: an atom that carries a definite
% verdict whatever the unknowns are. An `Indeterminate` has no such row, and its basis comes from
% solve 3 instead. When no single atom carries a definite verdict in every completion, the basis is
% empty, and `unknown_parts` names what was unknown (decisions/0016 #4). The brute-force oracle
% computes the same basis. Two shapes show where it differs from "the atoms with finding `t` that
% survive" (`test_completed_basis`):
%
% - **An empty basis.** Prohibitions `ex:x eq 5` and `ex:x neq 5`, with `ex:x` unresolved, read one
%   variable with opposite polarities. Each completion applies one of them, so the verdict is `Deny`
%   in both, and no prohibition survives in both. The basis is empty.
% - **A `u` atom in the basis.** A permission under `ex:x eq 5 or ex:x neq 5` has finding `u`, but
%   its tree is `t` in every completion, so it carries the `Permit` in every completion and is in
%   the basis.
%
% A paired guard empties a basis too. In an example among `DUTY_EXAMPLES`
% (`tests/test_brute_force.py`), `ex:r0` requires `ex:d0`, lapsed and unwitnessed, whose guard
% `ex:o2 eq 1` repeats the constraint of `ex:r1`, and `ex:o2` is unresolved. Where the shared
% variable is `t`, `ex:d0` is owed and violated, so `ex:r0` is closed and `ex:r1` permits; where it
% is `f`, `ex:r0` permits. The verdict is `Permit` in both, and the basis is empty. Both empty
% bases, this one and the first shape's, read a paired leaf, and the next argument shows that the
% empty basis of every definite `Deny` or `Permit` must.
%
% **Without a paired leaf, the basis is not empty.** Suppose no `u` finding reads a `cons` variable,
% so no open leaf is paired; duty findings may be `u`, and the connectives are any. Then every
% variable is a `fin(I)` or a `ful(Y)`, read by one finding only, and that finding is its variable's
% value in every completion: an opaque part keeps rank 1, and with no paired leaf nothing an open
% node reads differs from world `k`, so every open node keeps rank 1, and the finding's conjunction
% stays `u`. Call a variable's value *lenient* when it makes its finding the one that permits more:
% `applies` `t` for a permission and `f` for a prohibition, `owed` and `in_force` `f`, `fulfilled`
% `t`; and *strict* when it is the other value. Let `L` be the completion with every variable
% lenient, and `S` the one with every variable strict. Every completion `C` lies between them,
% finding by finding: a permission applies in `C` if it does in `S`, and a prohibition applies in
% `C` only if it does in `S`; a precondition is owed in `C` only if it is in `S`, and fulfilled in
% `C` if it is in `S`. So a permission that applies in `S` is closed in `C`, or waits on a duty
% there, only if it is so in `S`. And a permission that is a candidate in `C` is one in `L`: it
% applies in `L`, since a permission that applies anywhere applies in `L`, and it is not closed in
% `L`, since a precondition owed and violated in `L` is owed and violated in every completion. These
% are facts about findings, not about verdicts, which are not monotone in them: under `invalid`, a
% permission that applies can void the policy. The two cases use only these facts.
%
% - **A definite `Permit`.** `S` permits, so some candidate `X` survives in `S` and is ready. `X`'s
%   finding is `t`, since strict makes a `u` permission `f`. In `C`, `X` applies, it is not closed
%   and waits on no duty, since it does neither in `S`, and no prohibition of its policy applies to
%   remove it under `prohibit` or `invalid`, since none applies in `S`. The verdict is definite, so
%   `C` permits too, and nothing denies in `C`. So `X` survives in `C` with an empty outstanding
%   set, which no other set is a strict subset of, and `X` is a ready candidate of `C`'s frontier.
%   `X` is in role `permission` in every completion, so the basis holds it.
% - **A definite `Deny`.** `L` denies. If a prohibition `X` survives in `L`, its finding is `t`,
%   since lenient makes a `u` prohibition `f`, so it applies in every `C`; and a strategy that
%   removes it in `C` needs a candidate of its policy in `C`, which would be one in `L`, where none
%   removed `X`. If instead a violated obligation in force denies in `L`, its `in_force` is `t` and
%   its `fulfilled` `f` there; lenient would make a `u` `in_force` `f` and a `u` `fulfilled` `t`, so
%   these are its findings, the same in every `C`, and it denies in every `C`; `interpret.py` gives
%   it role `obligation`.
%
% So an empty basis under a definite `Deny` or `Permit` needs a `u` finding that reads a paired
% leaf, whose operand is `unresolved` and is listed as an unknown part: claim W of
% correctness-strategy.md §4.8. `tools/check_corpus.py` asks such a scenario to list it, and
% `check_waiver` checks the claim on every reply the differentials see (TESTS.md, claim W).
%
% **`Pending` is the exception.** Dominance is not monotone: a candidate whose finding is `u` can
% dominate a `t` one in the completions where it applies, and not in the others. So the basis of a
% definite `Pending` can lack a permission, and can name a duty that the listed frontier does not
% (explain.lp, *The listed frontier*). Both tests are in `tests/test_duty.py`:
%
% - In `test_pending_basis_under_an_uncertain_route`, `ex:perm` (finding `t`) needs `ex:d` and
%   `ex:d2`, and `ex:perm2` (finding `u`, on a missing request parameter) needs `ex:d`. Where
%   `ex:perm2` applies, `{ex:d}` dominates; elsewhere `ex:perm` is the frontier. No permission is in
%   both frontiers, so the basis is `ex:d` alone, outstanding in both. The listed frontier is
%   `[[ex:d, ex:d2]]`, because `ex:perm2` is uncertain in world `k`.
% - In `test_pending_basis_beyond_the_listed_frontier`, `ex:perm` (finding `t`) needs `ex:d`, and
%   `ex:permA` on `ex:x eq 5` and `ex:permB` on `ex:x neq 5` both need `ex:d3`, with `ex:x`
%   unresolved. One of the two applies in each completion, so each frontier offers `{ex:d}` and
%   `{ex:d3}`, and the basis is `ex:perm`, `ex:d`, and `ex:d3`. Neither of the two is listed, so the
%   listed frontier is `[[ex:d]]`.
%
% The basis stays cautious: each `duty` row is outstanding in the frontier of every completion, and
% each `permission` row is in every frontier. Without unknowns, `tools/check_corpus.py` asks a
% `Pending` basis for a permission and for exactly the frontier's duties; when a scenario lists an
% unknown part, it checks only their kinds (decisions/0019).
