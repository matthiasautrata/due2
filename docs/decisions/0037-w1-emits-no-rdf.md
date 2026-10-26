# 0037 — W1 emits no RDF: stage 1's atomised form is internal

**Status:** Decided, 2026-10-26 (the owner, on #134)
**Context documents:** `odrl-compound-to-atomic-normalization.md` §1, §4–§10 · `due2-workflows.md` §2, §3.1 (`root`), §3.6, §4 · `ways-of-working.md` §2.4 · `decisions/0007` · `decisions/0027` · `decisions/0036` · issue #134

## Question

In `odrl-compound-to-atomic-normalization.md` v0.23, stage 1's output `N(P0)` was a normative RDF graph of Atomic Policies, serialised as canonical N-Quads, with a PROV-O lineage graph beside it. Stage 2 builds the corpus from the lifted form, not from that graph (`due2-workflows.md` §4). W2 and W3 read only the corpus (`decisions/0027` #3). Explanation reads the lineage collection (`due2-workflows.md` §3.6). So nothing reads the graph or the sidecar.

Four things in the specification existed only for that graph:

- the `atomic-policy` and `activity` id domains;
- the rule that a policy keeps its id only if nothing in it expands;
- invariant 7, which normalises a part extracted from the graph again;
- the vocabulary of the PROV-O sidecar.

Is the atomised graph something due2 ships, or a step inside W1?

## Decision

1. **`N(P0)` is internal to W1.** It is stage 1's atomised lifted tree: `P0` with every rule atomic. Stage 2 reads it. It is never serialised, and it is not a conformance artifact.
2. **W1's outputs are the corpus, the lineage, and diagnostics,** each a collection under `decisions/0007`. Stage 1's lineage records are tuples of the lineage collection. The PROV-O sidecar is dropped.
3. **Invariant 3 stays as it is, over the internal form.** `Den(P0) ≅ Den(N(P0))` is checked in tests, through the bijection that stage 1's lineage records. It is not restated against the corpus: stage 2's DNF makes one atom several, so no bijection exists there (`due2-workflows.md` §4).
4. **An atom's root names the authored policy, and no node stands for an Atomic Policy.** Each atomic root rule occurrence is a root atom, which stage 2 records as `root (atom_id, policy_id)` (`decisions/0036`). The `atomic-policy` and `activity` id domains are dropped, and the authored policy keeps its id however its rules expand. The id domains `anon-node`, `atomic-rule`, `duty-atom`, and `duty-instance` stay, and so does `source_digest`. The canonical N-Quads term form stays too, because the hashes of `odrl-compound-to-atomic-normalization.md` §5.2 encode literals and the input graph with it.
5. **Invariant 7 becomes: a policy whose rules are all atomic normalises to itself.** Every rule keeps its id, and `N(P0)` has the same atoms, roots, and edges as `P0`. Since `N(P0)` is all-atomic, this still makes stage 1 idempotent. Checking the old form needed an RDF output to read back in.
6. **An export to atomised ODRL is written when someone asks for one.** It reads the corpus or stage 1's form. Until then, no code is written or maintained for it.

## Why this holds

- **No reader.** `decisions/0007` #2 and `decisions/0027` #3 already keep RDF out of everything after stage 2. This decision removes the last RDF writer. In the owner's words: "Don't write & maintain code nobody asks for."
- **The guarantee did not depend on the bytes.** Stage 1's correctness is invariant 3, a statement about denotations. The bijection it uses is in the lineage, wherever the lineage is kept. A serialised graph added nothing to the check.
- **The ids get simpler.** An Atomic Policy node needed an id of its own, plus a rule for when the authored one survives. `root` already says which policy an atom roots (`decisions/0036`), so the node had no job left.

## Rejected

- **Keep the graph as a conformance artifact.** That would mean a serialiser, a canonicaliser, a PROV-O sidecar, and a round-trip test, all for an output with no reader.
- **State `Den` against the corpus and drop stage 1's form from the specification.** Stage 2's DNF changes the number of atoms, so the comparison would be one-to-many. It would also merge stage 1's structural obligation with stage 2's semantic one, L9 (`due2-workflows.md` §4).

## Consequences

- `odrl-compound-to-atomic-normalization.md` v0.24:
  - §1 and §4 define `N(P0)` as internal.
  - §5.2 drops two domains and defines the canonical N-Quads that `source_digest` hashes.
  - §6.4 records root atoms.
  - §7 records the lineage as tuples.
  - §8 restates invariant 7.
  - §9 lists emitting RDF as a non-goal, §10 drops the suite items that read the graph, and §11 drops the PROV-O and RFC 6920 references.
- `due2-workflows.md` §2, §3.1 (`root`), and §4 drop the N-Quads artifact.
- `ways-of-working.md` §2.4 names one RDF boundary, the input.
- `correctness-strategy.md` §3 names the lifted tree as what the `Den` oracle shares with W1, and §4.2 lists the restated invariant 7.
- `due2-platform.md` §2.3 and §5 say "per root atom".
- The `why` of case `oval-prohibition-in-permission` takes root atoms from the Policy's own Rule edges.
- `due2-diagnostics.md` drops generated policies from `LimitExceeded`.
- `decisions/0007` item 2 is amended, because it said that stage 1 keeps N-Quads.

## Revisit when

A consumer needs atomised ODRL, such as the predecessor during migration (`due2-platform.md` §4) or an ODRL tool compared against due2. The answer then is an exporter, and stage 1 still writes no normative RDF.
