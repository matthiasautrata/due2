# 0032 — An instance records whether its deadline passed

**Status:** Decided, 2026-10-24 (the owner, on #113)
**Context documents:** `due2-workflows.md` §3.3, §3.5, §5.3, §6, §6.1, §6.4 · `odrl-compound-to-atomic-normalization.md` §6.3 · `schema/` · `docs/briefings/due2-review-2026-10-24.md` R02, R09 · issue #113

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
