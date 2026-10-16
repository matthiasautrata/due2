# 0007 — Collections are JCS JSON arrays, identified by SHA-256

**Status:** Decided, 2026-10-16
**Context documents:** `due2-workflows.md` §2, §9 #1 · `ways-of-working.md` §2.4 · `decisions/0006` · `odrl-compound-to-atomic-normalization.md` §4 · issue #3

## Question

Each of the five collections has one canonical serialisation, and its digest is its id (workflows §2). The encoding was open: JCS JSON arrays or canonical N-Quads. The register blocked it on "builder design". The bakeoff (`decisions/0006`) needs it first, since its vectors are collections.

## Options

- **A — canonical N-Quads.** One format with stage 1's artifact.
- **B — JCS JSON arrays (chosen).**

## Decision

Option B. The wire form, order, value encoding, and digest are in workflows §2.

Why:

1. **Collections are tuples, not triples.** Relations have keys, optional fields, and enums (§2). N-Quads would need a reified encoding of each tuple, and an RDF canonicalisation on top. The tuple form is the model, not a view of it.
2. **RDF is a boundary format** (`ways-of-working.md` §2.4). Stage 2 projects the lifted form into relations, and nothing downstream reads RDF. Stage 1 keeps N-Quads because its artifact is a graph; that is a different object.
3. **Every bakeoff backend reads it without an RDF stack.** Python, Elixir, and a Clingo driver all parse JSON in their standard libraries or common ones. Vectors, golden traces, and digests are then the same bytes in every backend, which cross-backend trace equality (0006) requires.
4. **Determinism has one specification.** JCS fixes key order and string escapes; a number in a literal's lexical form is a string, so the float rules of JCS never apply.

## Consequences

- The relation-level vector format (#36) builds on this encoding.
- Replay compares ids computed by this rule; a change to it is a new decision, and old traces keep their ids.

## Revisit when

- A backend cannot produce JCS output byte-identically; fix that backend, not the rule.
- A collection grows tuples that are not flat (nested relations): the value rules need extending.
