# 0007 — Collections are JCS JSON arrays, identified by SHA-256

**Status:** Decided, 2026-10-16; amended 2026-10-24
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

## Amendment (2026-10-24, several relations in one collection)

The decision said that a collection is a JSON array of tuples, but every collection holds several relations: the corpus has ten, and even the request has three (`due2-workflows.md` §3.1–§3.5). An array of tuples does not say which relation a tuple belongs to, so the encoding did not fix the bytes of any collection. The owner settled it while the evaluator's port schema was designed (#36).

**Decision.** A collection is a JSON object keyed by relation name. Each value is that relation's tuples, as a JSON array sorted as before. A relation with no tuples is omitted, so that an empty relation has one form. JCS orders the relation names. A collection with no tuples at all is `{}`. `due2-workflows.md` §2 states the rule. Where the title and Option B say "arrays", read this amendment.

**Why.**

- **The schema states it directly.** Each relation is one property of the collection, with its own tuple schema, so JSON Schema validates a collection without a discriminator.
- **The alternative needs a reserved field.** Tagging each tuple with its relation name keeps one array, but the tag must be a name no relation uses as a field, and the corpus's `closure` already has a field called `relation`.
