# 0015 — An operand may compare concepts under a SKOS hierarchy

**Status:** Decided, 2026-10-17 (the owner decided #1–#4 on 2026-10-16 in issue #52; #5–#8 settle what that left open)
**Context documents:** `due2-profiles.md` §2, §3, §4, §6 · `due2-workflows.md` §3.1, §3.3, §5.4 · `due2-diagnostics.md` §3 · `decisions/0014` · issue #52

## Question

Purposes are often concepts in a SKOS concept scheme. The Data Privacy Vocabulary (DPV 2.1) publishes its purposes that way, abridged here:

```turtle
dpv:purposes-classes a skos:ConceptScheme .
dpv:Marketing       a skos:Concept ; skos:broader dpv:Purpose ;   skos:inScheme dpv:purposes-classes .
dpv:DirectMarketing a skos:Concept ; skos:broader dpv:Marketing ; skos:inScheme dpv:purposes-classes .
```

A permission for `odrl:purpose eq dpv:Marketing` should cover a request for `dpv:DirectMarketing`, and a prohibition on marketing should catch it. Up to `due2-profiles.md` v0.7 neither happens: `eq` compares IRIs by identity, and only `isPartOf`, `hasPart`, and `isA` read a hierarchy. How should due2 compare concepts, and where is that declared?

## What the sources say

**ODRL** compares a purpose with `eq` or `isAnyOf` and says nothing about hierarchies of right-operand values. Its own hierarchy property, `odrl:includedIn`, relates actions only (`profiles/vendor/w3c/ODRL22.ttl`).

**DPV 2.1** (`https://w3id.org/dpv/2.1/dpv/dpv.ttl`) types 118 resources `dpv:Purpose`. Every one states `skos:inScheme` and `skos:broader`, and none states `rdfs:subClassOf`. Each is also typed `rdfs:Class`, but with no subclass edges a class reading finds no hierarchy.

**SKOS** (W3C SKOS Reference, 2009) relates concepts by `skos:broader` and its inverse `skos:narrower` (S25). `skos:broader` is not transitive, but it is a sub-property of `skos:broaderTransitive`, which is (S22, S24; §8.6.6), so querying the transitive closure of `skos:broader` is SKOS's own reading. A concept belongs to a scheme by `skos:inScheme`, and `skos:topConceptOf` is a sub-property of it (S7). Membership is not inherited along the hierarchy: `A skos:narrower B` and `A skos:inScheme S` do not entail `B skos:inScheme S` (§4.6, Example 9). SKOS models concepts as individuals, and the links between them as facts about the scheme, "never as class or property axioms" (§1.3). Reading concepts as classes, so that `isA` could compare them, would contradict that, and issue #52 rejects it.

**OVAL** (DIPS-Tools/ODRL-Engine at `40b8ac6`, `ODRL_Evaluator.py` lines 153–186) expands a rule's action, assignee, and target into their transitive descendants and tests membership, and does not expand right-operand values. We suggested upstream that it should (issue #54). Salas, Pareti et al. (2025, §3.3) keep hierarchy reasoning out of the evaluator's core and materialise it.

## Decision

1. **Same shape as rule components.** Comparison stays by identity under unique names. A hierarchy is declared data, and a comparison tests membership in its transitive closure, as `due2-profiles.md` §6 already does for actions and for assets and parties. The authored policy stays as written, and the edges an evaluation uses are recorded (`due2-workflows.md` §3.3).
2. **Declared on the operand binding.** A binding states `due2:conceptScheme S` for each scheme its concepts come from. Its edges travel in the `closure` relation like `odrl:includedIn`: from the policy and its profile modules, or from the SOTW (`due2-workflows.md` §3.1, §3.3).
3. **Operators.** On an operand with a concept scheme, `eq` holds when the request value is ⊑ the right value, and `isAnyOf` when it is ⊑ some right value. `neq` and `isNoneOf` are their complements, so "not for marketing" excludes mail marketing. `due2-profiles.md` §5's complement pairs stay valid in Kleene logic: within a scheme each side is `T` exactly when the other is `F`, and a value outside every scheme gives `U` on both sides (#4).
4. **Unknown is never false.** A request value in a declared scheme with no path to the right value gives `F`, closed-world over the declared edges, as for actions. A request value in no declared scheme is `invalid`, so `U`. Without this, a prohibition on marketing would silently not apply to a purpose whose edges were not supplied.
5. **The hierarchy predicate is fixed to SKOS.** `c ⊑ d` holds when `c = d` or a chain of `skos:broader` edges leads from `c` to `d`. A `skos:narrower` triple is read as the inverse `skos:broader` edge. The predicate is not configurable, so no two layers can disagree about it. Cross-scheme mappings (`skos:exactMatch`, `skos:closeMatch`, `skos:broadMatch`) are not read.
6. **Schemes add up across layers.** An operand's schemes are the union of the `due2:conceptScheme` values of every layer: baseline, selected profile modules, and policy. A scheme is not a type attribute in the sense of `decisions/0014`, since a higher layer that adds one widens what the operand compares and changes no comparison already defined. This is how SKOS is used: a policy that adds its own purposes to DPV's adds a scheme beside DPV's, and does not replace it.
7. **Only IRIs are concepts.** The scheme rule of #4 applies to IRI values. A string is its own kind (`decisions/0014` #4), and compares by code point whether or not the operand has a scheme. So the baseline's `odrl:purpose`, with no range, stays one operand for both kinds of authoring: strings compare as strings, concepts under the hierarchy, and a string against a concept does not fit, so `U`.
8. **Checks at normalisation.** All three only reject. Each catches an authoring error that would otherwise give the same `U` on every request:
   - an IRI right operand that is in none of a concept-scheme operand's schemes, by the memberships the policy and its profile modules declare, is rejected with `OperatorTypeMismatch`. Normalisation does not see the SOTW, so its memberships do not count here. Membership is `skos:inScheme`, `skos:topConceptOf`, or the inverse `skos:hasTopConcept` (SKOS Reference S7, S8);
   - an operator other than `eq`, `neq`, `isAnyOf`, and `isNoneOf` on a concept-scheme operand is rejected with `OperatorTypeMismatch`;
   - a `due2:conceptScheme` on an operand whose range is a datatype is rejected with `InvalidBinding`.

## Rejected

- **Concepts as classes, read by `isA`** (#52). SKOS concepts are individuals, not classes (SKOS Reference §1.3), and DPV, which also types its purposes as classes, publishes their hierarchy only as `skos:broader`.
- **Inferring the hierarchy from a `skos:Concept` range, with no binding attribute.** A range is a type, and #52 put the hierarchy on the binding. A scheme also says which concepts are in scope, which a range cannot.
- **A configurable hierarchy predicate.** SKOS has one hierarchy, `skos:broader` with its inverse, and DPV uses it. A configurable predicate would add a conflict for layers to resolve and a choice for authors to get wrong.
- **One scheme per operand, with conflicts reported.** That would make a policy unable to add its own purposes to a profile's.
- **A new purpose operand for concepts.** `odrl:purpose` serves both, by #7, and `dprod-odcs-seller-contract` and the other string-valued purpose cases keep their meaning.
- **Expanding `isAllOf`, `isPartOf`, `hasPart`, `isA` and the orderings over concepts.** No case or policy needs them. They are rejected by #8 rather than given an unreviewed reading.

## Consequences

- `due2-profiles.md` §2 adds `due2:conceptScheme` to extension point 1 and `skos:broader` to point 7; §4 states #3–#8; §6 *Hierarchies* names the SKOS edges. `profiles/due2-core.ttl` declares `due2:conceptScheme`.
- `due2-workflows.md` §3.1 and §3.3 list `skos:broader` and `skos:inScheme` edges in `closure`, and say that the SOTW records the edges above a compared concept. §5.4 says that a misfit or an out-of-scheme concept gives `U`.
- `due2-diagnostics.md` §3 widens `OperatorTypeMismatch` and `InvalidBinding`.
- Corpus cases, with the checker and clingo-i changes that admit them (issue #69): a DPV-style purpose permission and prohibition, an in-scheme miss, and an out-of-scheme value giving `Indeterminate`.
- Issue #52 named this record `decisions/0010`, which is the trace record. It is this one.

## Revisit when

- A policy needs a concept comparison under `isAllOf` or a set-valued operand.
- A real deployment needs cross-scheme mappings, such as DPV purposes matched to a sector vocabulary.
