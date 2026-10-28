# 0047 — The corpus carries operand bindings, and `Reads` is four relations

**Status:** Decided, 2026-10-26 (the owner, in the review of the evaluator's inputs on that date); notes 2026-10-26 (`decisions/0048`), 2026-10-28 (`decisions/0050`)
**Context documents:** `due2-workflows.md` §3.1, §3.3, §4, §5.4 · `due2-profiles.md` §2, §3, §4, §6 · `due2-platform.md` §2.1, §2.4, §2.5 · `decisions/0027` · `decisions/0036` · `decisions/0043` · issues #106, #108

## Question

W2 evaluates a constraint by its left operand's binding: its source, its property, its range, its cardinality, and its concept schemes (`due2-profiles.md` §3, §4). `plan : Corpus × Request → Reads` reads the same bindings to list what an evaluation may read (`due2-workflows.md` §3.3). In `due2-workflows.md` v0.52, two things were missing:

- **No corpus relation carried a binding** (#108). The bindings live in the profile modules, which W1 reads. The corpus is the only thing that crosses from W1 to W2 and W3 (`decisions/0027` #3), and `decide` takes the corpus, the request, and the SOTW alone. So W2 could not evaluate a constraint, and no relation-level vector could state one.
- **`Reads` had no relations** (#106). `due2-workflows.md` §3.3 said what it holds, not how. The evaluator port's schema needs relations for it, as for every collection. The corpus also names no world module, while the SOTW's `closure` has a `module` field, so it was open how `plan` names the module a hierarchy comparison uses.

## Decision

1. **A constraint's tuple carries its operand's binding.** `constraint (constraint_id | left_operand, operator, datatype, unit?, source: Enum, property, range?, cardinality: Enum)`, with `source ∈ {request, state, context, witness}` and `cardinality ∈ {one, set}`, and `constraint_scheme (constraint_id, scheme)` for each concept scheme. W1 writes the binding as it resolved it from the policy's layers, defaults included. For a context operand, `property` names the built-in: `dprod:agent`, `dprod:clock`, or `due2:actionTime`. `decisions/0049` #4 adds `operand_unit?`, the binding's unit.
2. **Allowed operators are not carried.** W1 rejects an operator that the binding does not allow (`OperatorTypeMismatch`), so every operator in a corpus is allowed, and W2 has nothing to check.
3. **`Reads` is four relations:** `read_param (property)`, `read_state (property)`, `read_edges (module, entity)`, and `read_fact_edges (module, property)`. The last lists a state property whose values a hierarchy comparison reads: the edges above each value of its facts are fetched after the facts.
4. **World modules are named by the kind of hierarchy they hold,** from a closed set of kinds: `due2:partyHierarchy`, `due2:assetHierarchy` (catalog classifications included), `due2:classHierarchy`, and one module per concept scheme, named by the scheme's IRI. The corpus names no module. Action hierarchies come from the corpus alone.
5. **A value whose kind the constraint does not say is listed in both modules.** The narrower value of an `isPartOf` or `hasPart` comparison may be a party or an asset, so `plan` lists it in `due2:partyHierarchy` and `due2:assetHierarchy`.

## Why this holds

- **One binding per constraint is the only key that fits both rules.** A higher layer may rebind an operand for one policy (`due2-profiles.md` §2), so a key of the operand alone would be wrong. A named constraint that several policies use is one tuple (`decisions/0036`), so a key of `(policy_id, left_operand)` would give one constraint two bindings, and W2 could not tell which applies to an atom shared by both policies. Keyed by the constraint, a binding is part of what the constraint says. Two policies that bind one named constraint differently say different things of one node, which publication refuses with `IdentityConflict` (`due2-workflows.md` §4).
- **The corpus digest then records the reading.** A binding changes what a constraint evaluates to. Carried in the corpus, it is part of the corpus id, and so of every evaluation id, as warnings are (`due2-workflows.md` §3.1, `diagnostic`). A binding read from a profile module at evaluation would not be.
- **A module named by kind needs no field in the corpus.** The kind of a comparison fixes the module `plan` lists, except for an `isPartOf` or `hasPart` value, which item 5 lists in two: a party part reads party membership, a target part asset membership, `isA` class typing, and a concept operand its scheme. W2 reads the union of every module's edges, so the module is a label for fetching, and the module follows from the corpus as it is, and a SOTW service registers for a module by the same name (`due2-platform.md` §2.4).
- **Listing a value in both modules is sound.** A module that does not hold an entity answers with no edges, and hierarchy is closed-world over the edges recorded (`due2-workflows.md` §3.3, `closure`), so the extra answer adds nothing. Listing the value in one module would need a type the constraint does not state.
- **Fact values cannot be entities of `read_edges`.** A state value is not known until its facts are recorded, so `plan` cannot name it. `read_fact_edges` names the property instead, and the shell finds the entities once it holds the facts.

## Rejected

- **Bindings keyed by `(policy_id, left_operand)`,** with relations `binding`, `binding_operator`, and `binding_scheme`. A constraint shared by two policies would have two bindings, as above.
- **Carrying allowed operators.** W2 would check what W1 has already rejected.
- **A module field on `atom` and `constraint`.** W1 would have to choose a module for each comparison, from information the profile modules do not state, and the closed set of kinds already decides it.
- **`read_edges` with an optional entity and an optional property,** one of them present. The relation would have two meanings, and the schema could not state that exactly one field is present.

## Consequences

- `due2-workflows.md` v0.53: §3.1 adds the binding fields and `constraint_scheme`; §4's agreement compares `constraint_scheme`; §3.3 gives `Reads` its relations and names the world modules; §5.4 step 1 reads the binding from the corpus.
- `schema/` has a `Reads` collection, and `PlanOutput` is a `Reads`.
- A named constraint that two policies' profile layers bind differently, which published before, now fails to publish with `IdentityConflict`. The `IdentityConflict` row of `due2-diagnostics.md` covers it unchanged: the binding is part of what the constraint's tuple says.
- `decisions/0043` #2 speaks of one request entity. An answer is for one entity, which may also be a value in the corpus or a fact's value. The plan's size is no longer fixed by the corpus and the request alone: `read_fact_edges` asks for edges above each value of a fact, and a set-valued fact may have many. A read limit counts them (#34).
- Not planned: edges above the issuer or actor of evidence, which a duty's attester and bearer compare, and above a witness's parameter values. Evidence is not planned (`due2-workflows.md` §3.3), so a comparison that needs them reads only the edges the case holds (#142).
- An answer names its module and entity but not its source, so two sources registered for one module overwrite each other (#143).

## Revisit when

- A comparison needs a hierarchy that none of the four kinds holds.
- A value's kind must be known to choose between the party and the asset module, as when one IRI names a party in one hierarchy and an asset in another.

**Note (2026-10-26, `decisions/0048`):** `Reads` gains `read_evidence_edges` and `read_witness_edges`, so it is six relations, and the edges above evidence values are planned and fetched when evidence is recorded. An answer names its source and carries a status, which resolves the two last consequences. A plan over `max_reads` is refused, and `max_reads` counts each relation tuple once, not each fact value as the fourth consequence supposed.

**Note (2026-10-28, `decisions/0050`):** W2 no longer reads one hierarchy over the whole corpus. An entry in policy `P` reads the union of every world module's `closure` tuples with `P`'s own corpus `closure`. The modules stay labels for fetching, and a comparison still does not choose one.
