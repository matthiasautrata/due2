# 0032 — An instance records whether its deadline passed

**Status:** Decided, 2026-10-24 (the owner, on #113); amended 2026-10-25 (the owner, on #121)
**Context documents:** `due2-workflows.md` §3.3, §3.5, §5.3, §6, §6.1, §6.4 · `odrl-compound-to-atomic-normalization.md` §6.3 · `schema/` · `docs/briefings/due2-review-2026-10-24.md` R02, R09 · `docs/briefings/due2-review-2026-10-25.md` F02 · issues #113, #121

## Question

The `instance` relation carries each duty instance's status from W2 to W3 (`due2-workflows.md` §3.5). The external review found two faults in it.

**R02.** When a duty's `fulfilled` finding is `U`, its status is `unknown`, and the trace does not say whether the deadline has passed. W3 needs to know. In a completion where the finding is `F`, the instance is `violated` if the deadline has passed, which closes a precondition's route (`due2-workflows.md` §6.1) or denies under `violations = deny`, and `outstanding` if it has not. An example shows the difference. A permission to use a dataset has the precondition "pay at least 5.0 by 2 June". Dana's payment record is dated 1 June but states no amount, so the finding is `U`. Asked on 1 June, the verdict ranges from `Pending` (the payment does not count, and Dana can still pay) to `Permit`. Asked on 3 June, it ranges from `NotApplicable` (the payment does not count, and the route has closed) to `Permit`. W2's output is the same in both: one `instance` tuple with status `unknown`. The proof of `due2-workflows.md` §6.4 already reads "the `F` duties whose deadline has passed", a fact that no relation carried. clingo-i gives the right ranges only because its W3 reads its internal `passed/1`.

**R09.** For scope `grant`, the instance key was the digest of `source_duty` and `request.reference`. `source_duty` is the authored duty, and W1 expands a duty with two targets into two atoms with the same `source_duty` (`odrl-compound-to-atomic-normalization.md` §6.3). For "for each download, pay the licence fee and the data fee", both atoms had one key, and `instance` holds one atom per key, so the trace could not record both. The review also says that evidence for one fee would count for both (`due2-review-2026-10-24.md` R09). It would not, since the witness test requires `e.object` to be the duty's target (`due2-workflows.md` §5.3), but the key collision is a fault in the relation either way.

## Decision

1. **`instance` gains `passed: Flag`.** W2 sets it when the instance has an effective deadline `D` and `effective_at > D`, and clears it otherwise, including when there is no deadline. An occurrence of a recurring duty is an instance with its own `D` (`due2-workflows.md` §5.3, *Recurrence*), so it has its own `passed`. It is fixed per evaluation, as the deadline comparison already was (`due2-workflows.md` §5.3). The status table is unchanged. An `unknown` instance is `fulfilled` in a completion where its finding is `T`; where the finding is `F`, it is `violated` if `passed` is true and `outstanding` otherwise.
2. **W3's signature lists `instance`.** §6.1 already read the status, so the signature was incomplete.
3. **A grant-scoped instance key is the digest of `binding_key` and `request.reference`.** `binding_key` is the digest of the authored duty and its ground binding, which includes the target (`due2-workflows.md` §3.1). The key therefore differs where the binding differs, as for the two fees, and is shared where the binding is shared: a duty that is both an obligation and a precondition, or a duty two permissions share, has one instance for the request, so one payment serves both routes. The bytes of every derived key stay open (#107).
4. **`discharges` names the grant, not the instance.** Evidence submitted against a request names the digest of the authored duty and the request's `reference`, as the case format already spells it (`conformance/README.md`). The atoms of one authored duty share that grant, and the rest of the witness test picks among them: a payment of the licence fee has the licence fee as its `object`. A submitter therefore names what it knows, the duty it paid for and the request, and never needs the binding.

## Why this holds

- **The deadline fact is an input to W3 that only W2 can compute.** W3 does not read `effective_at` or the deadline, and §5.3 keeps it that way so that W3 stays a pure function of the trace and the completions of §6.4 stay well defined. Recording the comparison where it is made keeps that. Splitting the status into `unknown` and `unknown_late` would carry the same bit but change an enum that §6.1 and every consumer of the trace read; carrying `D` itself would make W3 compare instants.
- **The binding is what makes two atoms of one duty different.** Two atoms with the same `source_duty` differ only in their binding, so the binding, and nothing coarser, separates their instances. A `member` instance is already keyed on `binding_key` (`due2-workflows.md` §5.3), so the two scopes now differ only in whether the request's `reference` is added. Keying on `atom_id` would also separate the two fees, but `atom_id` is an artefact of W1's expansion, not part of what the duty asks for.
- **The executable semantics already agree.** clingo-i keys each duty atom on its binding, matches `discharges` against the authored duty and the reference, and reads `passed/1` in W3. The two cases named under Consequences pass under it unchanged, with the rest of the corpus it evaluates (`uv run pytest --backend=clingo-i`).

## Rejected

- **Split `unknown` into two statuses.** It carries the same information as `passed`, at the cost of an enum change in a relation every consumer reads.
- **Carry `D` in `instance` and let W3 compare it with `effective_at`.** W3 would read the clock, against `due2-workflows.md` §5.3.
- **Key a grant instance on `atom_id` and `request.reference`.** It fixes the collision, but ties instance identity to W1's atom ids rather than to the duty and its binding, on which `member` instances are keyed.
- **Reject a grant-scoped duty with several targets.** It removes the collision by removing something a policy can say today.

## Consequences

- `due2-workflows.md` v0.40: §3.5 adds `passed` to `instance`; §5.3 gives the grant key, says what `discharges` names, and says what an `unknown` instance can become; §6 lists `instance` in W3's signature; §6.4's proof reads `passed`; §3.3 says that `discharges` names a grant.
- `schema/collections.schema.json` is regenerated with `passed`.
- `due2-unknown-fulfilment-deadline` pins R02: the review's pair, the same payment asked on 1 June (`Indeterminate`, `Pending`..`Permit`) and on 3 June (`Indeterminate`, `NotApplicable`..`Permit`). `due2-grant-two-targets` pins R09: a payment of the licence fee leaves the data fee outstanding (`Pending`), and paying both gives `Permit`. Both are on #37's list for relation-level vectors, which can state `passed` and the two instances.

## Revisit when

- #107 settles the bytes of the derived keys and finds that a grant digest and an instance digest need a domain separator, or that evidence must name the instance after all, for example because two atoms of one duty differ only in something the witness test does not read.

## Amendment (2026-10-25, a duty instance is its atom, skolemised)

### Question

The follow-up review (F02) found that `binding_key`, "the digest of `source_duty` and its ground binding (parameter values, inherited party roles, target)" (`due2-workflows.md` v0.43 §3.1), does not identify an instance. Two cases show it.

- **A compound action.** One duty has two actions, `compensate` and `inform`, with one target and the same parties. W1 expands it into two atoms (`odrl-compound-to-atomic-normalization.md` §6.3), and evidence of compensation leaves information outstanding: clingo-i derives `Pending`. The action is not among the listed ingredients, so read literally, both atoms have one `binding_key`, and `instance`, keyed by it, cannot hold their two rows.
- **A performer from the request.** "Complete annual training", borne by the collection of all employees, is fulfilled for Alice by Alice's training and not by Bob's (`due2-workflows.md` §5.3, *Witness*; `decisions/0018`). `due2-workflows.md` v0.43 §5.3 said it "binds to the person", but W1 computes `binding_key` before any request exists, so it cannot contain the person.

Listing more ingredients would mend the first case. Both cases come from one design, though: a second key, beside the atom's id, that restates what the atom already is.

### Decision

1. **A duty atom's id identifies what it asks for.** Stage 1 already gives every rule it emits such an id: a duty it does not expand keeps its authored identity, and one it expands gets `atomic_rule_uid`, from the source duty's identity and the selected action, relation value, and parties (`odrl-compound-to-atomic-normalization.md` §5.1, §5.2). When stage 2 adds inherited party roles or parameter values, the atom's id is `H(frame(namespace, "duty-atom", rule_uid, additions))`, where `additions` is `frame(p, term(v))` for each function or parameter `p` it binds to `v`, in byte order. Nothing else enters the id: not the parent permission, not the policy. A named duty bound identically in two places is therefore one atom, and one bound differently is two. An anonymous duty's stage-1 id includes its parent (`odrl-compound-to-atomic-normalization.md` §5.2), so two anonymous copies are two atoms, as stage 1 already makes them.
2. **`duty.binding_key` is dropped.** The grant key of the original item 3 is replaced by item 3 of this amendment.
3. **The instance key is the atom's id, with what the request and the occurrence add.** W2 adds, each only when present: the request subject as performer, when the witness test reads it as the actor (the duty has no bearer, or its bearer is a PartyCollection the subject is not known to be outside of); `request.reference`, for scope `grant`; and the occurrence `t`, for a recurring duty. With nothing added, the key is the atom's id; otherwise it is `H(frame(namespace, "duty-instance", atom_id, additions))`, where each addition is framed after its name, `performer`, `reference`, or `occurrence`, in that order. `instance_key` is an `Id`.
4. **The original item 4 stands.** `discharges` still names the grant, the authored duty and the reference, not the instance, and the rest of the witness test picks among the atoms of one duty.

`due2-workflows.md` v0.44 §3.1 (`duty.atom_id`) and §5.3 (*Instance*) give the constructions.

### Why

- **One identity, not two.** The atom's id and `binding_key` both had to separate the atoms of one duty and both had to agree on when two placements are one duty. Keeping both made each new axis, action today, a function tomorrow, a place where they could disagree. Stage 1 already computes the id from the duty's content, the way an RDF graph skolemises a blank node, and the instance builds on it.
- **Each ingredient is added where it is known.** What the policy says is grounded by W1, in the atom's id. What the request says, the subject and the reference, and what the clock says, the occurrence, are grounded by W2, in the instance key. That answers the review's question of when each is grounded, and no W1 key has to anticipate a request.
- **The cases follow without a rule of their own.** The compound action gives two atoms by stage 1's selection, so two instances. Alice and Bob under one PartyCollection bearer differ in the performer, so two instances, and Alice's training serves every request of hers. A duty in two roles is one atom, and a request adds the same values in both roles, so one instance. A duty shared by two permissions with the same inherited roles is one atom, so one payment serves both routes, as the original item 3 intended.
- **An implementer codes one function.** The instance key is a pure function of the atom's id and three optional request-time values, framed as stage 1 frames its ids. There is no second canonicalisation of the binding to test against the first, and a vector can state every key outright.
- **The rejection of `atom_id` assumed what is not so.** The original record rejected keying on `atom_id` (under *Why this holds* and *Rejected*) as "an artefact of W1's expansion, not part of what the duty asks for". Stage 1 defines the id deterministically from the duty's content (`odrl-compound-to-atomic-normalization.md` §5.2), so it is what the duty asks for.

### Rejected

- **List the missing ingredients in `binding_key`.** It mends the compound action, but the performer still cannot enter a key W1 computes, and the two keys would still have to agree on every axis.
- **Ground the performer in W1, one atom per member of a collection.** W1 would need the membership of every collection, which belongs to the state of the world, and would multiply atoms by its size.
- **Put the parent permission in the atom's id.** A duty two permissions share, with the same binding, would then have two instances, and one payment would no longer serve both routes.

### Consequences

- `due2-workflows.md` v0.44: §2's `Digest` row no longer lists the instance keys as open; §3.1 drops `binding_key` and gives `duty.atom_id`; §3.3 and §3.5 make `instance_key` an `Id`; §4's stage-2 row names the id; §5.3 gives the instance key.
- `schema/collections.schema.json` is regenerated without `binding_key`.
- `odrl-compound-to-atomic-normalization.md` §5.2 notes that stage 2 and W2 mint ids under its namespace with the domains `duty-atom` and `duty-instance`.
- clingo-i's duty atom `a(Duty, A, T, Party)` already separates the two actions; its instance is per request, so the performer is implicit. Its id holds only the bearer, so where two parents give a shared duty different non-bearer roles, its relation-level face (#41) has one atom where the corpus has two (`spikes/clingo-i/DESIGN.md`).
- #107 keeps the bytes of `discharges` and `alt_id`. The relation-level vectors (#37) are to pin the compound action and Alice and Bob under a PartyCollection bearer.

### Revisit when

- #119 gives a recurring duty's occurrence a canonical `t` other than an `Instant` term.

## Note (2026-10-26, minted ids, `decisions/0038`)

`decisions/0038` replaces every key this record computes:

- **Amendment item 1.** A duty atom that stage 2 binds roles or parameter values into gets a minted id, not one computed under the `duty-atom` domain. A duty that two policies state with the same binding is found again by its duty and its binding when the second policy is published, so it stays one atom.
- **Amendment item 3.** A duty instance is keyed by its atom and, for a recurring duty, its occurrence: `instance (atom_id, occurrence?: Instant | status: Enum, passed: Flag)`. The performer and the reference are fixed within a case, which has one request, so the key does not hold them, and the `duty-instance` domain is dropped. `activation` is keyed by `atom_id`.
- **Original item 4.** `discharges` still names the grant, the authored duty and the request's `reference`. It is now two plain fields, `discharges_duty` and `discharges_reference`, with no digest.
- **Original Consequences.** #107 is closed: `discharges` and `alt_id` have no bytes to settle, since `alt_id` is a position (`due2-workflows.md` §6.3).

The cases this record pins, the compound action and Alice and Bob under one PartyCollection bearer, give the same instances as before: two atoms each.
