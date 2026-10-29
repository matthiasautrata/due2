%# explain.lp: the eliminations, the listed frontier, the obligations, and the unknown parts
%
% The reply's `eliminated`, `frontier`, `obligations`, and `unknown_parts`, all read from the
% findings before completion, in the Kleene world `k`, not from a completion world, so they do
% not depend on the completion.
%
% The `eliminated` rows (due2-workflows.md §3.5, §6.1, §6.2; decisions/0011 #4) name one removed
% entry, that is, an atom and one policy that states it (due2-workflows.md §6.2, *Entries*), one
% remover, and the rule; an entry removed by two forbids has two rows (due2-workflows.md §3.5
% **[D]**, #57). A permission is removed by its precondition when that duty is owed `t` and
% violated, which closes it in every completion where it applies. Conflict
% follows, among the candidates that are not closed. A remover is in conflict in every
% completion: a forbid with finding `t`, or a permission with finding `t` that no completion
% closes. A removed atom is in conflict in some completion: its finding is `t` or `u`, and a
% permission is not closed. A `u` atom removes nothing (due2-workflows.md §6.2), but it can be
% removed.
%
% The listed frontier is due2-workflows.md §6.3's, from the ready and pending candidates of world
% `k`: an uncertain candidate enters only through the verdict. The `obligations` rows name each
% obligation in force with its duty status, and each whose `in_force` is `u` as `unknown`
% (due2-workflows.md §6.1). The `unknown_part` rows name every `u` part of every finding that is
% not `f`, an atom's or a duty's, with what it reads and why it is `u` (decisions/0016 #3 and its
% amendment).
%
% Every relation here reads entries, an atom in one of its policies, with that entry's findings
% (due2-workflows.md §3.1, §6.2 *Entries*). The shown rows keep the entry where the reply needs it
% (`elim/4`, `listed_front/2`, `front_duty/3`), and interpret.py projects them to source rules.
% Variable letters: DESIGN.md § Vocabulary; in an `elim` row `X` is removed, `P` is the policy of
% its removed entry, and `Y` removes it. A polarity is `Pol`, `pos` or `neg`.
%
% - **Consumes:** `atom/1`, `atom_effect/2`, `atom_policy/2`, `atom_party/3`, `pre/2`,
%   `space/2` (structure.lp); `conflict/2`, `left/2`, `prop/2` (bind.lp); `holds/2` (applies.lp);
%   `conn/2`, `member/2`, `leaf/1` (constraint.lp); `read_ok/3`, `read_status/4`,
%   `unchecked_unit/1` (operand.lp); `crank/4`, `evaluates/3` (compare.lp); `rank/2` (kleene.lp);
%   `voc/2` (lift.lp); `witness_cond/2`, `obligation_policy/2`, `instance/2`, `passed/1`,
%   `status/4` (duty.lp); `duty_item/1`, `finding_atom/2`, `item_root/2`, `item_space/2`,
%   `leaf_status/3` (completion.lp).
% - **Provides:** `may_apply/2`, `surely_applies/2`, `closed_by/3`, `maybe_closed/2`,
%   `may_candidate/2`, `sure_candidate/2`, `may_contend/2`, `sure_contender/2`,
%   `elim_within/4`, `void/1`, `elim/4`, `open_k/3`, `uncertain/2`, `conflict_removes/2`,
%   `candidate_state/3`, `listed/2`, `listed_out/3`, `listed_apart/4`, `listed_dominated/2`,
%   `listed_front/2`, `front_duty/3`, `obligation_row/2`, `reported/1`, `polar/5`, `flip/2`,
%   `conj/2`, `disj/2`, `xone_pol/4`, `xone_by/4`, `live/5`, `witness_status/4`,
%   `unknown_part/3`.

%## Findings

%*! may_apply(X, P)

Atom `X`'s entry in policy `P` has finding `t` or `u`: some completion may make it apply, so it
can be removed.
*%
may_apply(X, P) :- holds(applies(X, P), t).
may_apply(X, P) :- holds(applies(X, P), u).

%*! surely_applies(X, P)

Atom `X`'s entry in policy `P` has finding `t`: it applies in every completion, so it can remove.
*%
surely_applies(X, P) :- holds(applies(X, P), t).

%## Closed by a precondition

%*! closed_by(X, P, Y)

The entry of permission `X` in policy `P`, with finding `t` or `u`, is removed by its
precondition `Y`, which is owed `t` and violated in `P`. In every completion where the entry
applies, `Y` closes it (due2-workflows.md §6.1).
*%
closed_by(X, P, Y) :- may_apply(X, P), atom_effect(X, permit), pre(X, Y),
    holds(owed(Y, P), t), status(k, Y, P, violated).

%*! maybe_closed(X, P)

Some completion may close the entry of permission `X` in policy `P`: a precondition of it whose
deadline has passed may be owed in `P` (`owed` is not `f`) and may be unfulfilled there
(`fulfilled` is not `t`).
*%
maybe_closed(X, P) :- atom_effect(X, permit), space(X, P), pre(X, Y), not holds(owed(Y, P), f),
    passed(Y), not holds(fulfilled(Y, P), t).

%*! may_candidate(X, P)

The entry of permission `X` in policy `P` is a candidate in some completion: its finding is `t`
or `u`, and no precondition surely closes it.
*%
may_candidate(X, P) :- may_apply(X, P), atom_effect(X, permit), not closed_by(X, P, _).

%*! sure_candidate(X, P)

The entry of permission `X` in policy `P` is a candidate in every completion: its finding is
`t`, and no completion closes it.
*%
sure_candidate(X, P) :- surely_applies(X, P), atom_effect(X, permit), not maybe_closed(X, P).

%*! may_contend(X, P)

Atom `X`'s entry in policy `P` takes part in conflict in some completion: a candidate there, or
a forbid that applies.
*%
may_contend(X, P) :- may_candidate(X, P).
may_contend(X, P) :- may_apply(X, P), atom_effect(X, forbid).

%*! sure_contender(X, P)

Atom `X`'s entry in policy `P` takes part in conflict in every completion, so it can remove.
*%
sure_contender(X, P) :- sure_candidate(X, P).
sure_contender(X, P) :- surely_applies(X, P), atom_effect(X, forbid).

%## Within the policy

% By the policy's conflict strategy (due2-workflows.md §6.2 #1), one row per remover. An atom
% removed by two forbids has two rows (due2-workflows.md §3.5, #57), and each row is a complete
% reason. In a conflict row, whenever `X` applies, `Y` applies too, because `Y` is `t`, and `Y`
% removes it. In a `violated_precondition` row, `Y` is the duty atom, owed `t` and violated, so it
% closes `X` wherever `X` applies. A reader can check each row against the policy alone. A single
% row naming the first remover would hide the others, and which one is "first" would depend on the
% order of the facts. A `u` remover gives no row, because it removes `X` only in some completions,
% and that is not a reason that holds whatever the unknowns are.

%*! elim_within(X, P, Y, Strat)

Atom `Y` removes the entry of atom `X` in policy `P`, under `P`'s strategy `Strat`: under
`prohibit` a `t` forbid removes each candidate, under `perm` a sure candidate removes each
forbid, and under `invalid` every contender of a void policy is removed by each other sure
contender of it.
*%
elim_within(X, P, Y, prohibit) :- may_candidate(X, P), sure_contender(Y, P),
    atom_effect(Y, forbid), conflict(P, prohibit).
elim_within(X, P, Y, perm) :- may_contend(X, P), atom_effect(X, forbid), sure_candidate(Y, P),
    conflict(P, perm).

%*! void(P)

Policy `P` has strategy `invalid`, a sure candidate, and a `t` forbid, so its contenders are
removed in every completion. Its root obligations stay in force (due2-workflows.md §6.2 #1,
decisions/0029).
*%
void(P) :- conflict(P, invalid), sure_candidate(_, P), surely_applies(Y, P),
    atom_effect(Y, forbid).
elim_within(X, P, Y, invalid) :- void(P), may_contend(X, P), sure_contender(Y, P), X != Y.

%## Across policies

%*! elim(X, P, Y, Strat)

Atom `Y` removes the entry of atom `X` in policy `P` under rule `Strat`: `violated_precondition`,
which removes `X`'s entry in `P` when its precondition is violated there, a strategy of `P`, or
`"prohibit-overrides"` across policies. Across policies, each entry of a `t` forbid that its
policy `Q` did not remove removes each candidate entry in every policy other than `Q`
(due2-workflows.md §6.2 #2). `test_combination_rows_on_facts` runs the cross-policy rule on
hand-written facts.
*%
elim(X, P, Y, violated_precondition) :- closed_by(X, P, Y).
elim(X, P, Y, Strat) :- elim_within(X, P, Y, Strat).
elim(X, P, Y, "prohibit-overrides") :- may_candidate(X, P), surely_applies(Y, Q),
    atom_effect(Y, forbid), not elim_within(Y, Q, _, _), P != Q.

#show elim/4.

%## The listed frontier

% The reply's `frontier` is read in world `k`, so it does not depend on the completion. An uncertain
% candidate is not listed: it reaches the reply only through the verdict, which the completions
% decide. So under a definite `Pending` the listed frontier can differ from the frontier of a
% completion (resolve.lp, *The cautious basis*; decisions/0019). This is the listed frontier that
% version 0.33 of due2-workflows.md gave. Version 0.34 lists the routes that suffice instead
% (decisions/0026), and clingo-i follows it with #103.

%*! open_k(Y, P, N)

The precondition `Y`, whose instance in policy `P` is not violated, has open value of rank `N`
there in world `k`: the Kleene conjunction of `owed` and the negation of `fulfilled`. The open
value is that of due2-workflows.md §6.1. A violated instance closes its candidate or makes it
uncertain instead, so it has no open value.
*%
% The Kleene conjunction is the lesser rank; `2 - Nf` is the rank of the negation of `fulfilled`.
% Only a precondition has an `owed` finding.
open_k(Y, P, No) :- instance(Y, P), not status(k, Y, P, violated), holds(owed(Y, P), Vo),
    holds(fulfilled(Y, P), Vf), rank(Vo, No), rank(Vf, Nf), No <= 2 - Nf.
open_k(Y, P, 2 - Nf) :- instance(Y, P), not status(k, Y, P, violated), holds(owed(Y, P), Vo),
    holds(fulfilled(Y, P), Vf), rank(Vo, No), rank(Vf, Nf), 2 - Nf < No.

%*! uncertain(X, P)

The candidate entry `(X, P)` is uncertain in world `k`: its finding is `u`, a precondition's open
value in `P` is `u`, or a violated precondition's `owed` in `P` is `u`. The states are those of
due2-workflows.md §6.1.
*%
uncertain(X, P) :- may_candidate(X, P), holds(applies(X, P), u).
uncertain(X, P) :- may_candidate(X, P), pre(X, Y), open_k(Y, P, 1).
uncertain(X, P) :- may_candidate(X, P), pre(X, Y), status(k, Y, P, violated),
    holds(owed(Y, P), u).

%*! listed_out(X, P, Y)

The candidate entry `(X, P)` is not uncertain, and its precondition `Y` has open value `t` in `P`
in world `k`: `Y` is in the entry's outstanding set.
*%
listed_out(X, P, Y) :- may_candidate(X, P), not uncertain(X, P), pre(X, Y), open_k(Y, P, 2).

%*! candidate_state(X, P, S)

In world `k`, the candidate entry `(X, P)` has state `S`: `ready`, `pending`, or `uncertain`. The
states are given by the table of due2-workflows.md §6.1. Every candidate entry has exactly one
(the constraint below).
*%
candidate_state(X, P, uncertain) :- uncertain(X, P).
candidate_state(X, P, pending) :- may_candidate(X, P), not uncertain(X, P), listed_out(X, P, _).
candidate_state(X, P, ready) :- may_candidate(X, P), not uncertain(X, P),
    #count { Y : listed_out(X, P, Y) } = 0.
:- may_candidate(X, P), #count { S : candidate_state(X, P, S) } != 1.

%*! conflict_removes(X, P)

Conflict removes the entry of atom `X` in policy `P` in every completion where it takes part: it
has an `elim` row other than `violated_precondition`.
*%
conflict_removes(X, P) :- elim(X, P, _, Strat), Strat != violated_precondition.

%*! listed(X, P)

The candidate entry `(X, P)` is ready or pending in world `k`, and conflict does not remove it,
so it forms an alternative of the listed frontier. The frontier is that of due2-workflows.md §6.3.
A permission whose entry in one policy is removed is still listed through its entry in another,
as an atom remains a candidate while any of its entries survives (due2-workflows.md §6.2,
*Entries*).
*%
listed(X, P) :- candidate_state(X, P, (ready; pending)), not conflict_removes(X, P).

%*! listed_apart(X, P, X2, P2)

The listed entry `(X, P)` has an outstanding duty that the listed entry `(X2, P2)` lacks.
*%
listed_apart(X, P, X2, P2) :- listed(X, P), listed_out(X, P, Y), listed(X2, P2),
    not listed_out(X2, P2, Y).

%*! listed_dominated(X2, P2)

A listed entry's outstanding set is a strict subset of that of the listed entry `(X2, P2)`.
*%
listed_dominated(X2, P2) :- listed(X, P), listed(X2, P2), not listed_apart(X, P, X2, P2),
    listed_apart(X2, P2, X, P).

%*! listed_front(X, P)

The listed entry `(X, P)` is in the listed frontier: no other's outstanding set is a strict
subset of its own. interpret.py reports it under a `Pending` verdict, collapsing entries with one
set of duty IRIs into one alternative.
*%
listed_front(X, P) :- listed(X, P), not listed_dominated(X, P).

%*! front_duty(X, P, Y)

The duty atom `Y` is outstanding for the entry `(X, P)` of the listed frontier.
*%
front_duty(X, P, Y) :- listed_front(X, P), listed_out(X, P, Y).

#show listed_front/2.
#show front_duty/3.

%## Obligations

%*! obligation_row(Y, S)

The obligation `Y` is reported with status `S`: its duty status when it is in force `t`, and
`unknown` when its `in_force` is `u`, whatever its status. One not in force is not reported
(due2-workflows.md §6.1). Each entry gives its row, so an obligation that two policies state has
one row per status its entries reach. interpret.py also names each in role `obligation`, under
any verdict.
*%
obligation_row(Y, S) :- obligation_policy(Y, P), holds(in_force(Y, P), t), status(k, Y, P, S).
obligation_row(Y, unknown) :- obligation_policy(Y, P), holds(in_force(Y, P), u).

#show obligation_row/2.

%## Unknown parts

% W1's atoms are the disjuncts of the DNF of each authored tree (due2-workflows.md §3.1, §4 stage
% 2), so a `u` leaf that lies only in `f` disjuncts is read only by `f` atoms, and is not reported:
% in `or(and(lf, y), z)`, with `lf` a leaf that is `f`, `y` is not. A leaf that lies in a disjunct
% that is not `f` is live, and is reported though another member decides its node, in a `t` atom as
% in a `u` one: in `or(lt, y)`, with `lt` a leaf that is `t`, `y` is. The reply then names
% everything that was unknown in the disjuncts that can hold, whether or not it mattered, and a
% renderer may show less. `live/5` finds the live leaves on the authored tree, without building the
% DNF, which can be exponentially larger.
%
% Under a status the same for every rule, as an absent target is, every atom carries the row, so
% interpret.py projects the rows to the rule or duty node, and the reply has one row per rule,
% input, and status.

%*! reported(I)

Finding `I` is `t` or `u`, so its `u` parts are reported. An `f` finding is not: none of its `u`
parts can change it, and due2-workflows.md §5.5 lets an index skip an `f` atom, so reporting it
would make the reply depend on the index (decisions/0016, amendment).
*%
% Every finding has exactly one value (kleene.lp), so `not ... f` is "`t` or `u`".
reported(applies(X, P)) :- atom(X), space(X, P), not holds(applies(X, P), f).
reported(I) :- duty_item(I), not holds(I, f).

%*! polar(W, C, P, Pol, N)

In world `W` and policy `P`'s data space, node `C` read with polarity `Pol` has rank `N`: its own
rank for `pos`, and its negation's for `neg`.
*%
polar(W, C, P, pos, N) :- crank(W, C, P, N).
polar(W, C, P, neg, 2 - N) :- crank(W, C, P, N).

%*! flip(Pol, Q)

Polarity `Q` is the opposite of `Pol`. A negation reads its member with the opposite polarity.
*%
flip(pos, neg).
flip(neg, pos).

%*! conj(K, Pol)

A node with connective `K`, read with polarity `Pol`, is a conjunction of its members, each read
with `Pol`: an `and` read positively, or an `or` read negatively (De Morgan).
*%
conj(and, pos).
conj(or, neg).

%*! disj(K, Pol)

A node with connective `K`, read with polarity `Pol`, is a disjunction of its members, each read
with `Pol`: an `or` read positively, or an `and` read negatively.
*%
disj(or, pos).
disj(and, neg).

%*! xone_pol(C, D, G, Q)

In the term of the `xone` node `C` for its member `D`, member `G` is read with polarity `Q`:
`pos` for `D` itself and `neg` for each other member. W1 expands an `xone` into one such
conjunction per member (due2-workflows.md §6.4 and §4, its stage 2).
*%
xone_pol(C, D, D, pos) :- conn(C, xone), member(C, D).
xone_pol(C, D, G, neg) :- conn(C, xone), member(C, D), member(C, G), G != D.

%*! xone_by(W, C, P, D)

In world `W` and policy `P`'s data space, the `xone` node `C` is `t` because of its member `D`:
`D` is the one member that is `t`. Then the term of `xone_pol/4` for `D` is `t`, and every other
term is `f`.
*%
xone_by(W, C, P, D) :- crank(W, C, P, 2), conn(C, xone), member(C, D), crank(W, D, P, 2).

%*! live(W, I, P, C, Pol)

Node `C`, read with polarity `Pol` in policy `P`'s data space, lies in a disjunct of finding `I`'s
DNF whose value, in world `W`, is not `f`. `P` is the policy of `I`'s entry. W1 makes that DNF, and
each disjunct is an atom (due2-workflows.md §3.1, §4 stage 2), so a `u` leaf is named exactly when
it is live (due2-workflows.md §3.5). The disjunct may be a contradiction, such as `a and not a`:
W1's rewrites are strong Kleene equivalences, which do not drop it.

The roots are the trees of a reported finding in world `k`, and the witness conditions of a
witness pair that is not `f`, in its world `wit(E)`. Each is a conjunct of its finding with every
other part, so it is live. Liveness passes from a node to its members as follows:

- A disjunction passes it to every member.
- A conjunction passes it to a member when no other member is `f` under its polarity
  (`polar/5` rank 0). Under strong Kleene logic a node's value is the greatest of its
  disjuncts' values, so each such sibling has a disjunct that is not `f`, and the member's
  disjuncts combine with those into disjuncts that are not `f` either. When a sibling is `f`,
  every disjunct through the conjunction is `f`.
- A negation passes it to its member, read with the opposite polarity.
- An `xone` read positively is the disjunction of its terms (`xone_pol/4`). A term passes
  liveness to a member when no other member of the term is `f` under its polarity there.
- An `xone` read negatively is the conjunction of its negated terms, because due2-profiles.md §5
  expands an `xone` before pushing a negation in. A negated term is the disjunction of its
  members, each read with the opposite polarity, and it is `f` exactly when its term is `t`:
  when the `xone` is `t` because of that term's member (`xone_by/4`). It passes liveness to its
  members when no other negated term is `f`.
*%
live(k, I, P, C, pos) :- reported(I), item_root(I, C), item_space(I, P).
live(wit(E), witness(Y, P, E), P, C, pos) :- witness_cond(Y, C), holds(witness(Y, P, E), V),
    V != f.
live(W, I, P, D, Pol) :- live(W, I, P, C, Pol), conn(C, K), disj(K, Pol), member(C, D).
live(W, I, P, D, Pol) :- live(W, I, P, C, Pol), conn(C, K), conj(K, Pol), member(C, D),
    not polar(W, D2, P, Pol, 0) : member(C, D2), D2 != D.
live(W, I, P, D, Q) :- live(W, I, P, C, Pol), conn(C, negation), member(C, D), flip(Pol, Q).
live(W, I, P, G, Q) :- live(W, I, P, C, pos), conn(C, xone), xone_pol(C, D, G, Q),
    not polar(W, H, P, R, 0) : xone_pol(C, D, H, R), H != G.
live(W, I, P, G, Q) :- live(W, I, P, C, neg), conn(C, xone), xone_pol(C, D, G, R), flip(R, Q),
    not xone_by(W, C, P, D2) : member(C, D2), D2 != D.

%*! witness_status(E, C, P, S)

The witness leaf `C` is `u` in world `wit(E)` and policy `P`'s data space with status `S`, as
`leaf_status/3` gives it for world `k`: its operand's read status there, or `misfit`.
*%
witness_status(E, C, P, S) :- evaluates(wit(E), C, P), leaf(C), left(C, Op),
    read_status(wit(E), Op, P, S), not unchecked_unit(C).
witness_status(E, C, P, misfit) :- evaluates(wit(E), C, P), unchecked_unit(C).
witness_status(E, C, P, misfit) :- evaluates(wit(E), C, P), leaf(C), left(C, Op),
    read_ok(wit(E), Op, P), crank(wit(E), C, P, 1).

%*! unknown_part(X, Input, S)

Atom or duty atom `X` has a `u` part, in a finding of one of its entries that is `t` or `u`, that
reads `Input` with status `S`. The relation is the `unknown_part` of due2-workflows.md §3.5 and
decisions/0016 #3. `Input` is `target` for the request's target, `party(F)` for its party under
function `F`, and `prop(Prop)` for a `u` leaf whose left operand reads the property `Prop`. An
absent target or party is `missing`, and a leaf has its status in the entry's data space. A `u` leaf
is named when it is live (`live/5`), whether or not it decides its node: the reply names what was
missing even where it did not matter, but not a leaf that only an `f` atom reads. The parts of a
duty's findings are its guards for `owed` and `in_force`; the match parts of its policy's rules for
`in_force`, under the obligation; and for `fulfilled`, the witness conditions and a `u` actor check,
which reads the request's assignee (duty.lp), of each witness pair that is not `f`.
*%
unknown_part(X, target, missing) :- reported(applies(X, P)), holds(part(X, P, target), u).
unknown_part(X, party(F), missing) :- reported(applies(X, P)), atom_party(X, F, _),
    holds(part(X, P, party(F)), u).
unknown_part(Y, target, missing) :- reported(in_force(Y, P)), atom_policy(X, P),
    holds(part(X, P, target), u).
unknown_part(Y, party(F), missing) :- reported(in_force(Y, P)), atom_policy(X, P),
    atom_party(X, F, _), holds(part(X, P, party(F)), u).
unknown_part(X, prop(Prop), S) :- live(k, I, P, C, _), finding_atom(I, X), leaf_status(C, P, S),
    left(C, Op), prop(Op, Prop).
unknown_part(Y, prop(Prop), S) :- live(wit(E), witness(Y, P, E), P, C, _),
    witness_status(E, C, P, S), left(C, Op), prop(Op, Prop).
unknown_part(Y, party(F), missing) :- holds(check(Y, P, E, actor), u),
    holds(witness(Y, P, E), V), V != f, voc(assignee, F).

#show unknown_part/3.
