%# duty.lp: a duty's guards and witness conditions, and its W2 findings
%
% Splits the constraints of each duty atom, and the refinements of its action term, into guards
% and witness conditions (due2-workflows.md §5.2). A guard decides whether the duty is owed; a
% witness condition decides whether a piece of evidence fulfils it. A leaf is a witness condition
% when its left operand reads `due2:witnessSource` or `due2:actionTime`; every other leaf is a
% guard. A conjunction splits into its members, and every other node is one guard or one witness
% condition, or rejected with `MixedDutyConstraint` when it mixes the two. Then it derives the
% findings of due2-workflows.md §5.1 in the Kleene world `k`: `owed` for a precondition duty,
% `in_force` for a root obligation, and `fulfilled` for every instance, with its duty status
% (due2-workflows.md §5.3). The guards are read in world `k`; the witness conditions are read once
% per piece of evidence `E`, in world `wit(E)`, by the rules of compare.lp. Absent evidence makes
% `fulfilled` `f`, never `u`. Variable letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `context_property/2`, `closure/3`, `triple/3`, `voc/2` (lift.lp); `rank/2`
%   (kleene.lp); `duty_atom/1`, `rule/1`, `policy/1`, `atom/1`, `atom_policy/2`, `pre/2`,
%   `obligation/1`, `bearer/2`, `duty_action/2`, `duty_relation/2`, `duty_deadline/2`,
%   `deadline_kind/2`, `duty_scope/2` (structure.lp); `top_constraint/2`, `top_refinement/2`,
%   `conn/2`, `member/2`, `leaf/1`, `left/2`, `node_tree/2` (constraint.lp); `src/2`, `prop/2`
%   (operand.lp); `crank/3` (compare.lp); `part_of/2`, `atom_constraint/2`, `holds/2`
%   (applies.lp); `evidence/4`, `evidence_object/2`, `evidence_issuer/2`,
%   `evidence_discharges/3`, `activation/2`, `signer/2`, `sotw_effective_at/1`,
%   `request_party/2`, `request_reference/1`, `value/3`, `plus/3` (driver).
% - **Provides:** `duty_root/2`, `duty_part/2`, `split_part/2`, `witness_leaf/1`,
%   `has_witness/1`, `has_guard/1`, `guard/2`, `witness_cond/2`, `in_witness/1`, `rule_node/1`,
%   `witness_only/1`, `cons_part/1`, `match_part/2`, `matched/2`, `obligation_policy/2`,
%   `policy_match/2`, `instance/1`, `witness_pair/2`, `check_kind/1`, `effective_pos/1`,
%   `occurred_pos/2`, `activated/1`, `activation_at/2`, `deadline_at/2`, `passed/1`,
%   `ev_reaches/2`, `subject/1`, `signed/1`, `admitted/2`, `keyed/1`, `discharged/2`,
%   `status/3`; extends `evaluates/2` (compare.lp), `item/1`, `holds/2` (applies.lp),
%   `reject/2` (structure.lp), and `unsupported/1` (lift.lp).

%## The split

%*! duty_root(Y, C)

`C` is a root of duty atom `Y`'s conditions: a constraint root of its duty, or a refinement root
of its action term. A refinement of a root obligation's policy-level action is the
obligation's, like the action. These are the roots `atom_constraint/2` gives a rule's atom.
*%
duty_root(a(Duty, Term, T, Party), C) :- duty_atom(a(Duty, Term, T, Party)),
    top_constraint(Duty, C).
duty_root(a(Duty, Term, T, Party), C) :- duty_atom(a(Duty, Term, T, Party)),
    top_refinement(Term, C).

%*! duty_part(Y, C)

Node `C` is a conjunct of duty atom `Y`'s conditions: a root, or a member of a conjunction that
is one.
*%
duty_part(Y, C) :- duty_root(Y, C).
duty_part(Y, D) :- duty_part(Y, C), conn(C, and), member(C, D).

%*! split_part(Y, C)

Node `C` is one of the parts duty atom `Y`'s conditions split into: a conjunct that is not
itself a conjunction. Each is a guard or a witness condition as a whole.
*%
split_part(Y, C) :- duty_part(Y, C), not conn(C, and).

%*! witness_leaf(C)

Leaf `C` reads the evidence: its left operand is bound to `due2:witnessSource`, or reads the
context property `due2:actionTime`. The second is the evidence's `occurred_at`, as
due2-workflows.md §5.3 says. Under a rule, the same leaf reads the request's `at`.
*%
witness_leaf(C) :- left(C, Op), src(Op, witness).
witness_leaf(C) :- left(C, Op), src(Op, context), prop(Op, Prop),
    context_property(Prop, actionTime).

%*! has_witness(C)

The tree under node `C`, `C` included, has a witness leaf.
*%
has_witness(C) :- witness_leaf(C).
has_witness(C) :- member(C, D), has_witness(D).

%*! has_guard(C)

The tree under node `C`, `C` included, has a leaf that is not a witness leaf.
*%
has_guard(C) :- leaf(C), not witness_leaf(C).
has_guard(C) :- member(C, D), has_guard(D).

% A part that mixes the two cannot be split: a guard is read before the evidence and a witness
% condition per piece of it, so `or`, `xone`, or `not` over both has no single place to be read.
reject("MixedDutyConstraint", C) :- split_part(_, C), has_witness(C), has_guard(C).

%*! guard(Y, C)

Node `C` is a guard of duty atom `Y`: a split part with no witness leaf. Its world-`k` value is
a conjunct of `owed(Y)` and `in_force(Y)`.
*%
guard(Y, C) :- split_part(Y, C), not has_witness(C).

%*! witness_cond(Y, C)

Node `C` is a witness condition of duty atom `Y`: a split part whose leaves all read the
evidence. It is read against each piece of evidence in turn.
*%
witness_cond(Y, C) :- split_part(Y, C), has_witness(C), not has_guard(C).

%## The worlds of the witness conditions

%*! in_witness(C)

Node `C` lies in a witness condition: it is one, or below one.
*%
in_witness(C) :- witness_cond(_, C).
in_witness(D) :- in_witness(C), member(C, D).

%*! rule_node(C)

Node `C` lies in a tree of a permission or prohibition, so world `k` reads it against the
request.
*%
rule_node(C) :- node_tree(R, C), rule(R).

%*! witness_only(C)

World `k` does not evaluate node `C`: it lies in a witness condition, or is a conjunction of a
duty's conditions with a witness condition below it, and it lies in no rule's tree.
*%
% Such a node has no world-`k` value: a witness leaf reads the evidence, and world `k` has none.
% A conjunction above a witness condition is not needed either, since `owed` and `in_force` take
% the guards one by one. A `due2:actionTime` leaf that a rule shares is evaluated in both worlds,
% against the request's `at` in `k` and the evidence's `occurred_at` in `wit(E)`.
witness_only(C) :- in_witness(C), not rule_node(C).
witness_only(C) :- duty_part(_, C), conn(C, and), has_witness(C), not rule_node(C).

% World `wit(E)` evaluates every node of a witness condition, so compare.lp gives each one a
% rank in that world, from the values operand.lp reads from `E`.
evaluates(wit(E), C) :- evidence(E, _, _, _), in_witness(C).

%## Owed and in force

% Each finding is an item, so integrity.lp's one-value constraint covers it.
item(owed(Y)) :- pre(_, Y).
item(in_force(Y)) :- obligation(Y).

% The Kleene conjunction of the guards. The 2 in the set is the conjunction's identity, so a
% duty with no guard is owed `t`: due2-workflows.md §5.2 makes it owed whenever its parent
% applies, and this finding does not read the parent, since W3 reads it for a parent only.
holds(owed(Y), V) :- pre(_, Y), rank(V, N),
    N = #min { 2; M, C : guard(Y, C), holds(c(C), Vc), rank(Vc, M) }.

%*! cons_part(I)

Item `I` is a constraint part of an atom, `part(X, cons(C))`.
*%
cons_part(part(X, cons(C))) :- atom_constraint(X, C).

%*! match_part(X, I)

Item `I` is a part of atom `X` that the request matches: its action, its target, or a party,
but not a constraint.
*%
match_part(X, I) :- part_of(X, I), not cons_part(I).

%*! matched(X, N)

The request matches atom `X`, constraints aside, with rank `N`: the Kleene conjunction of its
`match_part/2` parts.
*%
% Every atom has an action and a target part, so the set is never empty.
matched(X, N) :- atom(X), N = #min { M, I : match_part(X, I), holds(I, V), rank(V, M) }.

%*! obligation_policy(Y, P)

The root obligation atom `Y` travels with policy `P`: `P` states `odrl:obligation` for its duty.
*%
obligation_policy(a(Duty, Term, T, Party), P) :- obligation(a(Duty, Term, T, Party)),
    policy(P), triple(P, Pred, Duty), voc(obligation, Pred).

%*! policy_match(Y, N)

Some `Permit` or `Forbid` atom of root obligation `Y`'s policy matches the request with rank
`N`: the Kleene disjunction of `matched/2` over those atoms, `f` when there are none.
*%
policy_match(Y, N) :- obligation(Y),
    N = #max { 0; M, X : obligation_policy(Y, P), atom_policy(X, P), matched(X, M) }.

% An obligation is in force when its policy matches and its guards hold, not when its own action
% matches (due2-workflows.md §5.2).
holds(in_force(Y), V) :- obligation(Y), rank(V, N),
    N = #min { Np, match : policy_match(Y, Np);
               M, C : guard(Y, C), holds(c(C), Vc), rank(Vc, M) }.

%*! instance(Y)

Duty atom `Y` has an instance: it is owed `t` or `u`, or in force `t` or `u`. Only an instance
has a `fulfilled` finding (due2-workflows.md §5.3).
*%
instance(Y) :- holds(owed(Y), V), V != f.
instance(Y) :- holds(in_force(Y), V), V != f.

%## The witness test

%*! witness_pair(Y, E)

The evidence `E` is tested as a witness for the instance of duty atom `Y`.
*%
witness_pair(Y, E) :- instance(Y), evidence(E, _, _, _).

%*! check_kind(K)

`K` is a check of the witness test: `effective` (`occurred_at ≤ effective_at`), `deadline`
(`occurred_at` no later than the deadline), `action`, `object`, `actor`, `signer`, and
`discharges`. The test is due2-workflows.md §5.3's.
*%
check_kind(effective; deadline; action; object; actor; signer; discharges).

% Each check of each pair is an item, so a check that a rule forgets fails loudly.
item(check(Y, E, K)) :- witness_pair(Y, E), check_kind(K).

%*! effective_pos(N)

The SOTW's `effective_at` lies at position `N` in the `instant` space.
*%
effective_pos(N) :- sotw_effective_at(Lit), value(Lit, instant, N).

%*! occurred_pos(E, N)

The evidence `E` occurred at position `N` in the `instant` space.
*%
occurred_pos(E, N) :- evidence(E, Lit, _, _), value(Lit, instant, N).

% Evidence counts only if it occurred no later than effective_at. Without an effective_at, it
% cannot be told, so the check is u.
holds(check(Y, E, effective), t) :- witness_pair(Y, E), occurred_pos(E, N), effective_pos(M),
    N <= M.
holds(check(Y, E, effective), f) :- witness_pair(Y, E), occurred_pos(E, N), effective_pos(M),
    N > M.
holds(check(Y, E, effective), u) :- witness_pair(Y, E), not effective_pos(_).

%*! activated(Duty)

The SOTW records an activation for `Duty`: its key is the duty's IRI.
*%
activated(Duty) :- activation(Duty, _).

%*! activation_at(Y, Start)

The instance of duty atom `Y` was first owed at the instant `Start`: the SOTW's activation for its
duty, or `effective_at` when there is none. That default is due2-workflows.md §5.3's.
*%
% The corpus keys a non-recurring instance by its duty's IRI (conformance/README.md, SOTW), so
% every atom of one duty shares its activation.
activation_at(a(Duty, Term, T, Party), Start) :- duty_atom(a(Duty, Term, T, Party)),
    activation(Duty, Start).
activation_at(a(Duty, Term, T, Party), Start) :- duty_atom(a(Duty, Term, T, Party)),
    not activated(Duty), sotw_effective_at(Start).

%*! deadline_at(Y, N)

The effective deadline of duty atom `Y` lies at position `N` in the `instant` space: an
absolute deadline's position, or activation plus a relative deadline (`plus/3`).
*%
deadline_at(Y, N) :- duty_deadline(Y, Lit), deadline_kind(Lit, absolute), value(Lit, instant, N).
deadline_at(Y, N) :- duty_deadline(Y, Lit), deadline_kind(Lit, relative), activation_at(Y, Start),
    plus(Start, Lit, N).

% A deadline that cannot be placed against effective_at leaves the status undecided, a case the
% status table of due2-workflows.md §5.3 has no row for.
unsupported("duty: deadline not comparable") :- duty_deadline(Y, _), not deadline_at(Y, _).
unsupported("duty: deadline not comparable") :- duty_deadline(_, _), not effective_pos(_).

% A witness after the deadline does not fulfil; a duty without a deadline has no such bound.
holds(check(Y, E, deadline), t) :- witness_pair(Y, E), not duty_deadline(Y, _).
holds(check(Y, E, deadline), t) :- witness_pair(Y, E), occurred_pos(E, N), deadline_at(Y, M),
    N <= M.
holds(check(Y, E, deadline), f) :- witness_pair(Y, E), occurred_pos(E, N), deadline_at(Y, M),
    N > M.

%*! ev_reaches(A, B)

The evidence action `A` is included in `B`: the reflexive-transitive closure of `odrl:includedIn`
from `A`, over declared edges only, as `reaches/2` is for the request action.
*%
ev_reaches(A, A) :- evidence(_, _, _, A).
ev_reaches(A, B) :- ev_reaches(A, Mid), closure(includedIn, Mid, B).

% The closure is closed-world over declared edges (due2-profiles.md §6), so f, not u.
holds(check(Y, E, action), t) :- witness_pair(Y, E), evidence(E, _, _, A), duty_action(Y, B),
    ev_reaches(A, B).
holds(check(Y, E, action), f) :- witness_pair(Y, E), evidence(E, _, _, A), duty_action(Y, B),
    not ev_reaches(A, B).

% Evidence with no object does not record the duty's relation value, so it is not a witness for
% a duty that has one.
holds(check(Y, E, object), t) :- witness_pair(Y, E), not duty_relation(Y, _).
holds(check(Y, E, object), t) :- witness_pair(Y, E), duty_relation(Y, T), evidence_object(E, T).
holds(check(Y, E, object), f) :- witness_pair(Y, E), duty_relation(Y, T),
    not evidence_object(E, T).

%*! subject(Party)

`Party` is the request subject: a party the request names for `odrl:assignee`. The subject is
due2-workflows.md §3.2's.
*%
subject(Party) :- request_party(F, Party), voc(assignee, F).

% The actor must be the bearer. A duty whose bearer is the request subject, in a request that
% names none, cannot be told: u, never f.
holds(check(Y, E, actor), t) :- witness_pair(Y, E), bearer(Y, Party), Party != none,
    evidence(E, _, Party, _).
holds(check(Y, E, actor), f) :- witness_pair(Y, E), bearer(Y, Party), Party != none,
    not evidence(E, _, Party, _).
holds(check(Y, E, actor), t) :- witness_pair(Y, E), bearer(Y, none), evidence(E, _, Party, _),
    subject(Party).
holds(check(Y, E, actor), f) :- witness_pair(Y, E), bearer(Y, none), subject(_),
    evidence(E, _, Actor, _), not subject(Actor).
holds(check(Y, E, actor), u) :- witness_pair(Y, E), bearer(Y, none), not subject(_).

%*! signed(Duty)

The config lists `signer` entries for `Duty`, so only evidence from a listed issuer counts for
it. The signers are due2-workflows.md §3.4's.
*%
signed(Duty) :- signer(Duty, _).

%*! admitted(Duty, E)

The evidence `E` has an issuer that a `signer` entry lists for `Duty`.
*%
admitted(Duty, E) :- signer(Duty, Issuer), evidence_issuer(E, Issuer).

holds(check(a(Duty, Term, T, Party), E, signer), t) :- witness_pair(a(Duty, Term, T, Party), E),
    not signed(Duty).
holds(check(a(Duty, Term, T, Party), E, signer), t) :- witness_pair(a(Duty, Term, T, Party), E),
    admitted(Duty, E).
holds(check(a(Duty, Term, T, Party), E, signer), f) :- witness_pair(a(Duty, Term, T, Party), E),
    signed(Duty), not admitted(Duty, E).

%*! keyed(Y)

The instance of duty atom `Y` is keyed on the request: its scope is `grant` and the request has
a `reference`. Without a reference, a `grant` duty falls back to `member` (due2-workflows.md
§5.3).
*%
keyed(Y) :- duty_scope(Y, grant), request_reference(_).

%*! discharged(Y, E)

The evidence `E` was submitted against the request's instance of duty atom `Y`: its
`discharges` names `Y`'s duty and the request's `reference`.
*%
discharged(a(Duty, Term, T, Party), E) :- witness_pair(a(Duty, Term, T, Party), E),
    request_reference(Ref), evidence_discharges(E, Duty, Ref).

holds(check(Y, E, discharges), t) :- witness_pair(Y, E), not keyed(Y).
holds(check(Y, E, discharges), t) :- witness_pair(Y, E), keyed(Y), discharged(Y, E).
holds(check(Y, E, discharges), f) :- witness_pair(Y, E), keyed(Y), not discharged(Y, E).

%## Fulfilled and status

% Each pair is an item: the witness test conjoined with the witness conditions in world wit(E).
% The seven checks are always in the set, so the #min always has a value.
item(witness(Y, E)) :- witness_pair(Y, E).
holds(witness(Y, E), V) :- witness_pair(Y, E), rank(V, N),
    N = #min { M, check, K : holds(check(Y, E, K), Vk), rank(Vk, M);
               M, cond, C : witness_cond(Y, C), crank(wit(E), C, M) }.

% The Kleene disjunction over the evidence: `t` if some witness satisfies the duty, `f` if every
% one fails, which includes having none (due2-workflows.md §5.3). The 0 is the disjunction's
% identity, which gives the empty set its `f`.
item(fulfilled(Y)) :- instance(Y).
holds(fulfilled(Y), V) :- instance(Y), rank(V, N),
    N = #max { 0; M, E : holds(witness(Y, E), Vw), rank(Vw, M) }.

%*! passed(Y)

The deadline of duty atom `Y` has passed: `effective_at` is later than it. This is fixed per
evaluation, so it is not a finding (due2-workflows.md §5.3).
*%
passed(Y) :- deadline_at(Y, M), effective_pos(N), N > M.

%*! status(W, Y, S)

In world `W`, the instance of duty atom `Y` has duty status `S`: `fulfilled`, `outstanding`,
`violated`, or `unknown`. It is the status table of due2-workflows.md §5.3, from the
`fulfilled` finding and `passed/1`. Without a deadline a duty is never violated.
*%
status(k, Y, fulfilled) :- holds(fulfilled(Y), t).
status(k, Y, outstanding) :- holds(fulfilled(Y), f), not passed(Y).
status(k, Y, violated) :- holds(fulfilled(Y), f), passed(Y).
status(k, Y, unknown) :- holds(fulfilled(Y), u).
