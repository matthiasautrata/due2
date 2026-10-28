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
%   `deadline_kind/2`, `duty_scope/2`, `attester/2`, `has_attester/1` (structure.lp);
%   `top_constraint/2`, `top_refinement/2`, `conn/2`, `member/2`, `leaf/1`, `node_tree/2`
%   (constraint.lp); `left/2`, `src/2`, `prop/2` (bind.lp); `crank/3` (compare.lp); `part_of/2`, `atom_constraint/2`, `holds/2`
%   (applies.lp); `evidence/4`, `evidence_object/2`, `evidence_issuer/2`,
%   `evidence_discharges/3`, `activation/2`, `sotw_effective_at/1`,
%   `request_party/2`, `request_reference/1`, `value/3`, `plus/3` (driver); `le_k/3` (lift.lp).
% - **Provides:** `duty_root/2`, `duty_part/2`, `split_part/2`, `witness_leaf/1`,
%   `has_witness/1`, `has_guard/1`, `guard/2`, `witness_cond/2`, `in_witness/1`, `rule_node/1`,
%   `witness_only/1`, `cons_part/1`, `match_part/2`, `matched/2`, `obligation_policy/2`,
%   `policy_match/2`, `instance/1`, `witness_pair/2`, `check_kind/1`, `effective_pos/1`,
%   `occurred_pos/2`, `activated/1`, `activation_at/2`, `deadline_at/2`, `passed/1`,
%   `ev_reaches/2`, `subject/1`, `member_bearer/2`, `has_member_bearer/1`, `performer/2`,
%   `open_actor/2`, `attested/2`, `keyed/1`, `discharged/2`,
%   `status/3`; extends `evaluates/2` (compare.lp), `item/1`, `holds/2` (applies.lp),
%   `reject/2` (structure.lp), and `unsupported/1` (lift.lp).

%## The split

% A duty's conditions are its constraint roots and the refinement roots of its action terms
% (`duty_root/2`); a root obligation that takes the policy's action takes its refinements too. They
% split into guards and witness conditions:
%
% - a leaf is a *witness leaf* when its left operand is bound to `due2:witnessSource`, or reads the
%   context property `due2:actionTime`, the evidence's `occurred_at` (`witness_leaf/1`,
%   due2-workflows.md §5.3);
% - a conjunction splits into its members, recursively (`duty_part/2`), and each conjunct that is
%   not a conjunction is a *split part* (`split_part/2`);
% - `has_witness(C)` and `has_guard(C)` say that the tree under `C` has a witness leaf, or a leaf
%   that is not one;
% - a split part with no witness leaf is a guard (`guard(Y, C)`), and one whose leaves are all
%   witness leaves is a witness condition (`witness_cond(Y, C)`);
% - a split part with both, an `or`, `xone`, or `dprod:not` over a guard leaf and a witness leaf, is
%   `reject("MixedDutyConstraint", C)` (due2-diagnostics.md). A guard is read once, in world `k`,
%   before any evidence, and a witness condition once per piece of evidence, so a node that mixes
%   them has no single place to be read.
%
% For example, take a duty whose constraint is `ex:g eq ex:v and ex:w eq ex:v and ex:t eq ex:v`,
% with `ex:g` bound to the state, `ex:w` to `due2:witnessSource`, and `ex:t` to the context property
% `due2:actionTime`. The `and` splits into three parts: one guard, the `ex:g` leaf, and two witness
% conditions (`test_conjunction_splits_into_guard_and_witness`).

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

% A witness condition has no value against the request: its leaves read the evidence, and world `k`
% has none. So world `k` skips the nodes that lie in a witness condition (`in_witness/1`), and the
% conjunctions of a duty's conditions with a witness condition below them, since the findings take
% the guards one by one. These are the witness-only nodes (`witness_only/1`). A node that also lies
% in a rule's tree (`rule_node/1`) is not one: world `k` evaluates it for the rule. That happens to
% a `due2:actionTime` leaf that a rule and a duty share, which reads the request's `at` in `k` and
% the evidence's `occurred_at` in `wit(E)` (operand.lp). Each piece of evidence `E` has its world
% `wit(E)`, which evaluates every node of every witness condition (`evaluates(wit(E), C)`), so
% compare.lp gives each one a rank `crank(wit(E), C, N)` from what `E` records. One algebra serves
% the request and the evidence: the same leaf and connective rules, in another world.

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

% These are the findings of due2-workflows.md §5.2, in world `k`:
%
% - `owed(Y)`, for a precondition duty atom: the Kleene conjunction of its guards, `t` when it has
%   none. due2-workflows.md §5.2 makes an unguarded duty owed whenever its parent applies. The
%   finding does not read the parent: W3 reads it only for a parent candidate (due2-workflows.md
%   §6.1).
% - `in_force(Y)`, for a root obligation atom: the Kleene conjunction of `policy_match(Y, N)` and
%   its guards. `policy_match` is the Kleene disjunction, `f` when there are none, over the `Permit`
%   and `Forbid` atoms of the obligation's policy (`obligation_policy/2`) of `matched(X, N)`: the
%   conjunction of the atom's action, target, and party parts (`match_part/2`), its constraint parts
%   left out (`cons_part/1`). An obligation is in force when its policy matches the request, not
%   when its own action does: in the worked example at the end of this file, the request plays and
%   the duty is to delete.
% - `instance(Y)` when `owed(Y)` or `in_force(Y)` is `t` or `u`. Only an instance is tested against
%   the evidence. A `u` instance is tested too, so that its `fulfilled` finding has a value whatever
%   the guard turns out to be.

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

% Under due2-workflows.md §5.3, each instance is paired with each piece of evidence
% (`witness_pair(Y, E)`), and each pair has seven checks, `check(Y, E, K)` for each `check_kind(K)`,
% each an item. `occurred_pos(E, N)` and `effective_pos(N)` place the evidence's `occurred_at` and
% the SOTW's `effective_at` in the `instant` space:
%
% | Check `K` | `t` when | `f` when | `u` when |
% |---|---|---|---|
% | `effective` | `occurred_at` ≤ the SOTW's `effective_at` | `occurred_at` is later | the SOTW has no `effective_at`, which declines (*Fulfilled and status*) |
% | `deadline` | the duty has no deadline, or `occurred_at` ≤ the deadline (`deadline_at/2`) | `occurred_at` is later | never: an unplaceable deadline declines |
% | `action` | the evidence's action is the duty's, or included in it (`ev_reaches/2`) | otherwise | never: the closure is closed-world |
% | `object` | the duty has no relation value, or the evidence's object is it | otherwise, an evidence record with no object included | never |
% | `actor` | the actor is the performer (`performer/2`): the request subject (`subject/1`) when it is a member of a party-collection bearer (`member_bearer/2`); else the bearer; or the subject when the bearer is `none` | the actor is someone else | the request names no subject, and the bearer is `none`, or a collection the actor is a member of (`open_actor/2`, for the collection) |
% | `attester` | the duty has no attester (`has_attester/1`, structure.lp), or the evidence's issuer is at or below one (`attested/2`) | the duty has an attester, and the evidence has no issuer or one that is not at or below it | never |
% | `discharges` | the instance is not the request's grant (`keyed/1`), or the evidence discharges the duty under the request's `reference` (`discharged/2`) | it is the request's grant, and the evidence does not | never |
%
% The collection rows are decisions/0018: each member bears a duty whose bearer is a party
% collection, so the subject's own act witnesses it, and another member's does not. With no subject,
% a member's act is `u`, since that member may be the subject, and a non-member's is `f`.
%
% The deadline is the absolute one, or the activation plus a relative one (`plus/3`). The activation
% (`activation_at/2`) is the SOTW's record for the duty's IRI (`activated/1`), the key the case
% format gives an activation, or `effective_at` when the SOTW has none (due2-workflows.md §5.3). An
% instance is the request's grant (`keyed/1`) when its scope is `grant` and the request has a
% `reference`; without one, a `grant` duty falls back to `member`.

%*! witness_pair(Y, E)

The evidence `E` is tested as a witness for the instance of duty atom `Y`.
*%
witness_pair(Y, E) :- instance(Y), evidence(E, _, _, _).

%*! check_kind(K)

`K` is a check of the witness test: `effective` (`occurred_at ≤ effective_at`), `deadline`
(`occurred_at` no later than the deadline), `action`, `object`, `actor`, `attester`, and
`discharges`. The test is due2-workflows.md §5.3's.
*%
check_kind(effective; deadline; action; object; actor; attester; discharges).

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
% The u check reads no input that due2-workflows.md §3.5 lets `unknown_part` name, so the reply
% could not say what is missing: solve 1 declines the vector instead.
unsupported("duty: evidence without effective_at") :- witness_pair(_, _), not effective_pos(_).

%*! activated(Duty)

The SOTW records an activation for `Duty`: its key is the duty's IRI.
*%
activated(Duty) :- activation(Duty, _).

%*! activation_at(Y, Start)

The instance of duty atom `Y` was first owed at the instant `Start`: the SOTW's activation for its
duty, or `effective_at` when there is none. That default is due2-workflows.md §5.3's.
*%
% The case format names an activation by its duty's IRI (conformance/README.md, SOTW), so every
% atom of one duty shares its activation. That IRI is the duty atom's id, which keys `activation`
% (due2-workflows.md §3.3), when W1 does not expand the duty.
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

%*! member_bearer(Y, Party)

The request subject `Party` is a member of duty atom `Y`'s bearer, a party collection, so it
bears `Y` for this request: each member of a collection bears its duty (decisions/0018).
*%
member_bearer(Y, Party) :- bearer(Y, Coll), subject(Party), le_k(Party, Coll, party).

%*! has_member_bearer(Y)

The request subject bears duty atom `Y` as a member of its bearer.
*%
has_member_bearer(Y) :- member_bearer(Y, _).

%*! performer(Y, Party)

`Party` is the one actor whose act can witness duty atom `Y`: the request subject when it is a
member of `Y`'s bearer, else the bearer, or the subject when the bearer is `none`. A duty with
no performer has a bearer that the request leaves open (`open_actor/2`).
*%
performer(Y, Party) :- member_bearer(Y, Party).
performer(Y, Party) :- bearer(Y, Party), Party != none, not has_member_bearer(Y).
performer(Y, Party) :- bearer(Y, none), subject(Party).

%*! open_actor(Y, Actor)

An act by `Actor` may witness duty atom `Y`, and the request cannot tell: it names no subject,
and `Actor` is a member of `Y`'s bearer, so `Actor` may be the subject (decisions/0018).
*%
open_actor(Y, Actor) :- bearer(Y, Coll), not subject(_), evidence(_, _, Actor, _),
    le_k(Actor, Coll, party).

% The actor must be the performer. An actor the request cannot tell apart from the subject is u,
% never f: a member of a collection bearer, or anyone when the bearer is `none` and the request
% names no subject, which leaves the duty with no performer.
holds(check(Y, E, actor), t) :- witness_pair(Y, E), evidence(E, _, Actor, _),
    performer(Y, Actor).
holds(check(Y, E, actor), f) :- witness_pair(Y, E), evidence(E, _, Actor, _), performer(Y, _),
    not performer(Y, Actor), not open_actor(Y, Actor).
holds(check(Y, E, actor), u) :- witness_pair(Y, E), evidence(E, _, Actor, _),
    open_actor(Y, Actor).
holds(check(Y, E, actor), u) :- witness_pair(Y, E), bearer(Y, none), not subject(_).

%*! attested(Duty, E)

The evidence `E` has an issuer at or below an attester of `Duty`: the attester itself, or a
party below it under the party closure (`le_k/3`), such as a member of an attester that is a
party collection. The attester is due2-workflows.md §5.3's.
*%
attested(Duty, E) :- attester(Duty, Issuer), evidence_issuer(E, Issuer).
attested(Duty, E) :- attester(Duty, A), evidence_issuer(E, Issuer), le_k(Issuer, A, party).

% A duty with no attester counts evidence from any issuer, or none. One with an attester counts
% only attested evidence, so evidence with no issuer is `f`, never `u`: the SOTW states every
% issuer it has.
holds(check(a(Duty, Term, T, Party), E, attester), t) :- witness_pair(a(Duty, Term, T, Party), E),
    not has_attester(Duty).
holds(check(a(Duty, Term, T, Party), E, attester), t) :- witness_pair(a(Duty, Term, T, Party), E),
    attested(Duty, E).
holds(check(a(Duty, Term, T, Party), E, attester), f) :- witness_pair(a(Duty, Term, T, Party), E),
    has_attester(Duty), not attested(Duty, E).

%*! keyed(Y)

The instance of duty atom `Y` is the request's grant: its scope is `grant` and the request has
a `reference`, which evidence must name to discharge it. Without a reference, a `grant` duty falls back to scope `member`, as
due2-workflows.md §5.3 says.
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

% `witness(Y, E)` is the Kleene conjunction of the seven checks and of the ranks of `Y`'s witness
% conditions in world `wit(E)`. `fulfilled(Y)` is the Kleene disjunction of the witnesses, `f` when
% there is no evidence. `passed(Y)` holds when the deadline is earlier than `effective_at`. It is
% fixed per evaluation, since both instants are inputs, so it is a fact about the vector, not a
% finding. The duty status `status(k, Y, S)` is the table of due2-workflows.md §5.3:
%
% | `fulfilled(Y)` | `passed(Y)` | Duty status |
% |---|---|---|
% | `t` | either | `fulfilled` |
% | `f` | no | `outstanding` |
% | `f` | yes | `violated` |
% | `u` | either | `unknown` |
%
% A duty with no deadline never passes, so it is never `violated`. The table has no row for a
% deadline it cannot place against `effective_at`, so a duty whose deadline has no position, or a
% vector with a deadline and no `effective_at`, declines as `duty: deadline not comparable`.
%
% A precondition's `u` `owed` or `fulfilled` is completed like an atom's; an obligation's findings
% move no verdict, so they are not (completion.lp, *Findings*). For every `u` duty finding, the
% reply names the inputs that made it `u` (explain.lp). One `u` has no such input: the `effective`
% check of evidence when the SOTW has no `effective_at`. `effective_at` is not a field an
% `unknown_part` row can name (due2-workflows.md §3.5), so the reply could not say what was unknown,
% and the vector declines as `duty: evidence without effective_at`.

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

%## Worked example

% This is the vector of `test_late_witness_is_not_timely`, with the relations copied from a run.
% A permission to use `ex:a` travels with an obligation to delete it by 1 May:
%
% ```turtle
% ex:p a odrl:Set ; odrl:profile dprod: ; odrl:target ex:a ;
%     odrl:permission ex:perm ; odrl:obligation ex:o .
% ex:perm a odrl:Permission ; odrl:action odrl:use .
% ex:o a odrl:Duty ; odrl:action odrl:delete ;
%     dprod:deadline "2026-05-01T00:00:00Z"^^xsd:dateTime .
% ```
%
% The request asks `ex:alice` to play `ex:a` at 1 June, with `reference` `req-1`. The SOTW is
% effective at 1 June, and records one piece of evidence, `ex:e1`: `ex:alice` deleted `ex:a` on
% 15 May. With `O` the obligation's atom `a("ex:o", "odrl:delete", "ex:a", none)`:
%
% 1. `matched(a("ex:perm", "odrl:use", "ex:a", none), 2)`: `odrl:play` is included in
%    `odrl:use`, and the target is `ex:a`. So `policy_match(O, 2)`, and with no guard
%    `holds(in_force(O), t)` and `instance(O)`.
% 2. `witness_pair(O, "ex:e1")`. Six checks are `t`: `effective`, `action`, `object`, `actor`
%    (the bearer is `none` and `ex:alice` is the subject), `attester`, and `discharges`. `deadline`
%    is `f`, since 15 May is after 1 May. So `holds(witness(O, "ex:e1"), f)`, and
%    `holds(fulfilled(O), f)`.
% 3. `deadline_at(O, 0)`, since 1 May is the earliest instant of the vector and positions are
%    dense ranks from 0 (values.py). `effective_at` is later, so `passed(O)`, and
%    `status(k, O, violated)`.
%
% Evidence that came too late is no witness: the duty was violated on 1 May, and deleting the
% asset afterwards does not undo that.
