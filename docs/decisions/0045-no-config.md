# 0045 — An evaluation has no config

**Status:** Decided, 2026-10-26 (the owner, in the review of `due2-platform.md` on that date)
**Context documents:** `due2-workflows.md` §3.3, §3.4, §3.5, §5.3, §6, §7.1, §8 · `due2-profiles.md` §6, §7, §8.2 · `decisions/0004` · `decisions/0029` · `decisions/0040` · `decisions/0042` · issues #4, #5

## Question

`due2-workflows.md` v0.51 §3.4 gives each evaluation a config, an input beside the request, the corpus, and the SOTW:

```text
config        (| combination: Enum, violations: Enum, max_mixed: Count, max_frontier_vars: Count)
signer        (source_duty, issuer)
admit_source  (property, source)
```

Each field changes the trace, so the config is one of the evaluation's four input ids, and a case fixes it (`decisions/0042`). That needs a config store, an id on every case and evaluation, and a way to choose a config when a case opens. The owner asked who would change a config, and how often: "we're building a lot of machinery that in practice — i fear — nobody will ever touch." Does any field need to be a per-evaluation choice?

## Decision

1. **There is no config.** `decide` takes the request, the corpus, and the SOTW. The trace's `evaluation` tuple has three input ids, and a case holds no config id: `case (case_id | request, corpus, pins)`.
2. **`combination` is removed.** Across policies the rule is fixed: prohibit-overrides, under which any surviving `T` `Forbid` eliminates every candidate. Within a policy, its own `odrl:conflict` decides, as before. Other cross-policy strategies stay open (#4); `atom.priority` stays as the field one of them would read.
3. **`violations` is removed, and a violated obligation never denies.** A root obligation in force is reported with its status, `violated` included, and does not gate access. A permission's duty stays a precondition of that permission alone (§6.1): a violated one removes its own candidate, with rule `violated_precondition`, and another permission of the request can still permit.
4. **`signer` is replaced by an attester.** `due2:attestingParty` is a party function of the duty whose function plays the role `due2:attester` (`due2-profiles.md` §6). When a duty has an attester, evidence counts for it only if its `issuer` is the attester or below it in the party closure; evidence with no issuer does not count. A duty with no attester accepts any issuer. The attester is a party role, so it is inherited as other roles are (`due2-workflows.md` §4).
5. **`max_mixed` and `max_frontier_vars` are constants of the spec,** each 8. They still change the trace, and they are part of what an evaluator version means.
6. **`admit_source` moves to the connector registry.** The orchestrator records a fact answer only from a source registered for the property, and a person's answer only when it asked that person (`due2-platform.md`). Every recorded answer is admitted, and W2 combines them by `decisions/0040` #3.
7. **A preference among frontier alternatives (#5) would be authored in the policy,** not chosen per evaluation.

## Why this holds

- **Nobody would set the config.** Each field was a choice with one value in use. Every one of the corpus's 457 scenarios at the time ran under `prohibit-overrides`; 12 ran under `violations = deny`, all to show DPROD's reading; one case listed signers. A field nobody changes is a constant, and a constant needs no store, no id, and no case term.
- **ODRL already has the per-policy choice.** `odrl:conflict` is how an author picks a strategy, within the policy that needs it. A cross-policy strategy has no author, and #4 waits for a real corpus of several policies.
- **ODRL does not let an unfulfilled obligation gate a permission.** ODRL IM §2.6.1 makes a permission's duty "a pre-condition between the Permission and the Duty", and a permission "can be exercised" only when its duties are fulfilled. IM §2.6.4 says a policy-level obligation "is fulfilled if all constraints are satisfied and if its action … has been exercised", and lets a policy state a consequence of not fulfilling it; it says nothing that ties it to the policy's permissions. So in due2 two permissions, one with a violated duty and one without, give `Permit` through the second, and a violated obligation of the policy is reported beside the verdict. The owner: "If a permit activates … then the permit holds."
- **Violated and outstanding stay apart.** The owner asked that a violated duty not be read as a pending one. They are told apart where the reader looks: a violated precondition closes its candidate rather than joining the frontier (§6.1, role `closed`), and `instance.status` and the `verdict_basis` role `obligation` name `violated` and `outstanding` as different statuses.
- **Who attests a duty is policy content.** The signer list said whose evidence counts for a duty. That is a fact about the duty, which the policy's author knows, so it belongs in the policy, as ODRL's other functions (`informedParty`, `trackingParty`) are. A party function also gets the party closure: an issuer below the attester, such as a bank under a payment network, counts.
- **The bounds are budgets, not choices.** `max_mixed` and `max_frontier_vars` decide when W3 falls back to a sound approximation (`decisions/0004`, `decisions/0027`). Nobody has a reason to choose one value per case, and a constant keeps L1 (`due2-workflows.md` §8): the trace is still a function of the inputs and the spec version.
- **Admission is about the conversation, not the evaluation.** Which sources may answer a property is known when the orchestrator asks, so it records only answers it may count. A volunteered answer is not recorded as a fact of the case, and the SOTW then holds only admitted answers.

## Rejected

- **Keep `violations` with default `ignore`.** The `deny` mode had one user: the DPROD-faithful scenarios. It also complicated the monotonicity proof and law L7, and made an obligation act as a prohibition, which ODRL does not say. DPROD's behaviour could return as profile semantics, stated by the profile.
- **Treat a violated obligation as pending.** `Pending` offers routes that the requester can still take; a violated obligation has no such route. The owner: "There is a difference between a violated duty and a pending duty. That needs to be preserved."
- **Keep `signer` as a separate record outside the policy.** It would stay an input of every evaluation, and it would name issuers without the party closure.
- **Fix only the defaults and keep the fields.** The machinery would stay: the store, the ids, and the case term.

## Consequences

- `due2-workflows.md` v0.52:
  - §3.3 *Several sources*: every recorded answer is admitted.
  - §3.4 becomes *Constants*.
  - §3.5: `evaluation` has three input ids.
  - §3.7: the explanation reads no `admit_source`.
  - §5.3: the witness rule reads the attester.
  - §6: W3 takes no config; §6.2 fixes prohibit-overrides across policies; §6.4 drops the `deny` clause of the `Deny` row, of the monotonicity proof, and of the uniform-variable rule.
  - §7.1: `case` has no config.
  - §8: L7 drops its `deny` clause.
  - §9 row 2 is about other strategies.
- `due2-profiles.md`: §6 adds the attester role; §7 states that a violated obligation never denies; §8.2 exception 6 covers every scenario where DPROD would deny for a violation.
- `profiles/due2-core.ttl` adds `due2:attester` and `due2:attestingParty`.
- `conformance/`: scenarios have no `config`. The 12 `violations = deny` scenarios change: five that are now identical to a sibling scenario are removed, and seven take the verdict the obligation no longer gates, each with its notes. `due2-grant-signers` names the bank as the duty's attester. A new case, `due2-violated-precondition-beside-permission`, shows a violated precondition closing its own permission while a second permission for the same read still permits.
- `decisions/0004`, `decisions/0008`, `decisions/0029`, `decisions/0038`, `decisions/0040`, and `decisions/0042` carry notes.
- `due2-platform.md` follows in its next version: `decide` takes three inputs, and the connector registry admits sources.

## Revisit when

- Two deployments need different values for one of these fields for the same policies. The field then returns, as a profile term if the policies' profile decides it, or as config otherwise.
