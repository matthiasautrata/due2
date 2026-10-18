# 0018 — Each member bears a duty whose bearer is a party collection

**Status:** Decided, 2026-10-18 (the owner chose the member reading)
**Context documents:** `due2-workflows.md` §5.3 (Witness) · `due2-profiles.md` §6, §8.1 · issue #49

## Question

A witness for a duty `d` is evidence whose `actor` is `d`'s bearer (`due2-workflows.md` §5.3). The bearer is the party in the bearer role, `odrl:assignee` unless a profile says otherwise, and a precondition that states no party inherits its parent permission's (`due2-workflows.md` §4). When that party is an `odrl:PartyCollection`, which acts witness the duty?

The case is `force-21` (`conformance/cases/force-21/`). Its permission lets `ex:partyCollection` read `ex:x` if the duty `odrl:compensate` is met, and the duty inherits the collection as its bearer. The request names `ex:alice`, a member, as the assignee, and the one evidence record says that `ex:alice` compensated. Read literally, "`e.actor` is `d`'s bearer" asks for an act by `ex:partyCollection` itself, so the duty has no witness and the verdict is `Pending`. The case expects `Permit`, as FORCE does.

## What ODRL says

ODRL IM §2.3 (`references.md` §1) defines a `PartyCollection` as "a Party that is a single entity representing a set of member entities", and says that "all the members of the set will undertake the same functional role in the Rule". IM §2.3.2 adds that `odrl:partOf` lets "a Rule that relates to a PartyCollection … understand which individual Parties the Rule may apply to". IM §2.6.3 says that "the Party obligated to perform the duty MUST satisfy the Duty". Read together: each member is an assignee in its own right, and a member who exercises the permission is the party obligated to perform its duty.

## Decision

A duty whose bearer is a party collection is borne by each member. When the request subject is a member (`subject ⊑ bearer` under the party closure), the witness's `actor` must be the subject. When the request names no subject, an act by a member is `U`, because that member may be the subject. Otherwise the actor must be the bearer itself, as before.

In `force-21`, `ex:alice` is the subject and a member, so her act is a witness and the verdict is `Permit`.

## Rejected

- **Any member's act.** `actor ⊑ bearer` under the party closure. Then `ex:bob` paying would discharge `ex:alice`'s duty, and the scope `member` instance, which "binds to the person" (`due2-workflows.md` §5.3), would be fulfilled by someone else.
- **Strict equality.** Only an act recorded with the collection as its actor counts. It contradicts IM §2.3, and no evidence source records a collection as an actor.

## Consequences

`due2-workflows.md` v0.28 §5.3 states the rule. clingo-i's actor check reads it (`spikes/clingo-i/lp/duty.lp`), and `force-21` keeps its expected `Permit`.

## Revisit when

- A profile gives a collection a duty that the collection performs as one party, such as a board resolution. That needs a bearer role of its own, not this default.
