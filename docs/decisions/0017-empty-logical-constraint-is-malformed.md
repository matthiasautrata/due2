# 0017 — A logical constraint over the empty list is malformed

**Status:** Decided, 2026-10-17 (the owner asked for the reasoning of the `decisions/0013` amendment)
**Context documents:** `due2-profiles.md` §5 · `due2-diagnostics.md` §3 · `decisions/0013` (amendment) · issue #74

## Question

A logical constraint names its members with one operand property: `odrl:and`, `odrl:or`, `odrl:xone`, or `dprod:not` (`due2-profiles.md` §5). The value may be one RDF list or repeated values. What does a connective over the empty list mean, `odrl:and ()` for example? In RDF, `()` is the IRI `rdf:nil`, so the connective has a value and no member.

Read with the usual identities for an empty conjunction and disjunction, the four connectives give answers that do not depend on the request:

| Connective | On the empty list | Effect on its rule |
|---|---|---|
| `odrl:and ()` | `T`, vacuously | a permission permits, and a prohibition denies, every request it otherwise matches |
| `odrl:or ()` | `F`: no member holds | the rule never applies |
| `odrl:xone ()` | `F`: no member is the one that holds | the rule never applies |
| `dprod:not ()` | none: negation takes one operand | — |

clingo-i at `440744d` gave exactly the first three readings, because its aggregates over the members return their empty-set identities, and declined the fourth. `tools/check_corpus.py` accepted all four.

## What ODRL says

IM §2.5.2 says the operand's value "is a list of the existing Constraint instances", and `odrl22-shape.ttl` reads that as a list with at least one member: its `LogicalConstraintShape` asks the list for an `rdf:first`. So a policy with an empty connective already fails the ODRL 2.2 check. Nothing in the IM, the Vocabulary, `ODRL22.ttl`, or the Community Group's formal semantics draft gives an empty connective a meaning.

## Decision

Normalisation rejects a logical constraint any of whose operand values is the empty list, with `MalformedConstraint` in stage 2. It is the fifth form of that code, beside the four for leaves (`decisions/0013` and its amendment).

The reasons are those of the `decisions/0013` amendment for the empty set as a right operand:

1. ODRL gives the form no meaning.
2. Every reading decides the rule without looking at the request, so the form is more likely an authoring error, such as a generator that emptied a list, than an intent.
3. The error is silent and can be harmful: a prohibition on `odrl:and ()` denies everything it matches, and a permission on `odrl:or ()` never permits anything.

Rejecting it shows the author the error instead.

The other serialisations agree. In JSON-LD, an empty array gives either no triple or `rdf:nil`, depending on whether the context declares the term a list. With no triple the node is neither a leaf nor a connective, which `MalformedConstraint` already rejects; `rdf:nil` is what this record rejects.

## Rejected

- **Read the identities.** It is what an implementation does by accident, and the table shows why it is unsafe.
- **Decline.** A decline says the spec does not settle a reading. Here no reading exists, and a decline would hide an authoring error behind a capability gap.

## Consequences

`due2-profiles.md` v0.12 §5 and `due2-diagnostics.md` v0.5 §3 state the rejection. `tools/check_corpus.py` and clingo-i reject it, and the negative case `due2-empty-logical-constraint` covers all four connectives. Unlike `due2-empty-right-operand`, the case sets `odrl22_valid: false`, because the shape fails it too. A `dprod:not` with more than one member keeps its decline: it has readings (a conjunction under the negation, or an error), and the spec does not choose between them.

## Revisit when

- The ODRL WG or CG gives an empty logical constraint a meaning.
