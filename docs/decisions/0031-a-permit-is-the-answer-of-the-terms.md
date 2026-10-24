# 0031 — A verdict is the answer of the terms supplied

**Status:** Decided, 2026-10-24 (the owner, on #112)
**Context documents:** `due2-workflows.md` §3.1, §3.7, §5.2, §6.4 · `due2-platform.md` §2.3, §3.1 · `due2-profiles.md` §6, §8.1 · `odrl-compound-to-atomic-normalization.md` §3, §4 · `due2-architecture.md` §8.2 · `docs/briefings/due2-review-2026-10-24.md` §6 · issue #112

## Question

In ODRL, an Offer proposes rules and an Agreement grants them (W3C, *ODRL Information Model 2.2* §2.1.2). due2 evaluates a Set, an Offer, and an Agreement alike. W1's first stage keeps the policy's class in its output (`odrl-compound-to-atomic-normalization.md` §4), but the corpus's `policy` relation drops it (`due2-workflows.md` §3.1), so W2 and W3 never see it. The external review asked what `Permit` then means: that the supplied terms allow the action, or that the requester holds a grant to take it. A caller building authorisation on due2 needs to know.

An example shows what is at stake. A data-product owner publishes a DPROD `DataOffer`: anyone may read the customer dataset for research. Dana asks to read it for research. The policy store holds the offer, so the orchestrator selects it, and the evaluator returns `Permit`. Dana has not accepted the offer, and no agreement exists.

## Decision

1. **A verdict is the answer of the policies supplied, as written.** `Permit` says that the policies in the corpus permit the request's action in the SOTW. It does not say that anyone has accepted them. Over the offer in the example, `Permit` reads "this offer permits you to proceed". This cuts both ways: an offer's prohibitions and, under `violations = deny`, its violated obligations deny as any policy's do, and a `Pending` over an offer lists the duties its terms require.
2. **No workflow reads the policy class.** W1 uses it to find the policy nodes, a profile's class counting as the ODRL class it declares (`odrl-compound-to-atomic-normalization.md` §3, `due2-profiles.md` §6), and stage 1 carries it through. The corpus does not keep it, and W2 and W3 evaluate every class alike.
3. **Offers are selected like any other policy.** The orchestrator selects every policy that may apply to a request, offers and agreements alike (`due2-platform.md` §2.3).
4. **Accepting an offer is a separate step.** Writing an offer's terms into an agreement, such as signing a contract, happens outside the evaluator. due2 did not take over RL2's materialisation of an Offer into an Agreement (`due2-architecture.md` §8.2), and DPROD's `acceptsOffer` is metadata that no workflow reads (`due2-profiles.md` §8.1). Whether a deployment requires an agreement before access is taken is its choice, not part of the verdict.

## Why this holds

- **The question a requester asks is about the terms.** In the example, Dana wants to know whether the dataset may be read on the terms on offer, before any contract exists. `Permit` answers it, and a `Pending` says what the terms still require.
- **The terms already say who they are for.** An offer whose permission names an assignee matches a request only when the request's subject is that party, or a member of it (`due2-workflows.md` §5.2). An offer made to someone else does not apply to Dana, so "this offer permits you" is said only to a party the offer covers.
- **Acceptance and withdrawal are facts about the world, not rules.** Whether Dana has signed, and whether the owner has withdrawn the offer, are recorded outside the policy. DPROD's lifecycle statuses are metadata, usable in constraints once flattened onto the request or a state node, and its validity dates are never evaluated (`due2-profiles.md` §8.1). A deployment keeps a withdrawn offer out of the corpus by selection, or flattens its status onto the request and writes a constraint on it.
- **The trace names what permitted.** `verdict_basis` names the permissions that make a `Permit`, and each atom names its policy (`due2-workflows.md` §3.1, §3.7). A presentation can therefore say which policy permits, and read that policy's class from the authored policy in the policy store.
- **Nothing changes in the evaluator.** The corpus already evaluates offers this way: eleven cases evaluate a DPROD `DataOffer`, and `dprod-market-data-feed` returns `Permit` under an active offer that no agreement accompanies. `dprod-customer-api-v1` returns `Permit` under an offer whose status is `dprod:Fulfilled`, since the status is not read.

## Rejected

- **Carry the class, and give an offer's permissions no effect without acceptance.** The evaluator would need a field for acceptance in the request or the SOTW. Without it, an offer's permissions would be no candidates, so a request that only an offer covers would be `NotApplicable` (`due2-workflows.md` §6.4). That hides the answer to the requester's real question, whether the terms allow the action.
- **Make acceptance a precondition.** W1 would add an "accept the offer" duty to each permission of an offer, so the answer would be `Pending` with that route. That invents a duty nobody authored. It also merges the offer with the agreement that accepting it creates, which is a separate policy and which due2 does not materialise (`due2-architecture.md` §8.2).

## Consequences

- `due2-workflows.md` v0.39 states the meaning in §6.4 and says in §3.1 that `policy` keeps no class. `odrl-compound-to-atomic-normalization.md` §4 is unchanged.
- `due2-platform.md` v0.5 §2.3 says that offers are selected like any policy, and §3.1 shows a `Permit` over an offer as "this offer permits you to proceed".
- The corpus needs no new case: the offer cases already pin the reading.

## Revisit when

- A deployment needs the trace itself to distinguish a grant from an offer, for example to say "this offer would permit you" and "your agreement permits you" without consulting the policy store. The class could then be kept in `policy` for the explanation, still unread by W2 and W3.
