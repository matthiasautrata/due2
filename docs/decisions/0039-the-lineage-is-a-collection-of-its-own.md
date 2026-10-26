# 0039 — The lineage is a collection with relations of its own

**Status:** Decided, 2026-10-26 (the owner, on #136)
**Context documents:** `due2-workflows.md` §2, §3.1, §3.6, §3.7, §4, §8 · `odrl-compound-to-atomic-normalization.md` §5, §6.2, §7, §8.1 · `due2-platform.md` §2.3, §2.10 · `correctness-strategy.md` §4.3 · `decisions/0007` · `decisions/0010` · `decisions/0037` · `decisions/0038` · issue #136

## Question

W1 emits a corpus and a lineage (`due2-workflows.md` §4). In `due2-workflows.md` v0.48, §3.6 described the lineage in one paragraph of prose. It had no relations, so the schema generator could not read it, no test could check it, and three readers depended on records that no text fixed:

1. **Explanation** follows an atom of a trace to the authored rule, its selection, and its binding (`due2-workflows.md` §3.7, law L10).
2. **The `Den` oracle** checks stage 1 through the bijection between the atoms of the authored policy and those of `N(P0)`, which the lineage records (`odrl-compound-to-atomic-normalization.md` §8.1).
3. **The policy store** renames the ids that W1 minted for a published node's parts when a later policy states the node again (`decisions/0038` #3), so it must know which ids were minted.

The prose was also wrong in three places:

- it said the corpus references the lineage by digest, but the corpus of several policies is a union of per-policy corpora and holds no lineage id;
- `odrl-compound-to-atomic-normalization.md` §7 said an anonymous node's parent and predicate were already in `N(P0)` and were not repeated, but `N(P0)` is never serialised (`decisions/0037`), so that record was lost;
- it listed, as stage 2's part, the constraint disjunct of each root atom and the disjunct of each duty clause, which the corpus already holds in `atom_constraint` and `duty_constraint`.

Which relations does the lineage hold, and how is the lineage of a policy found?

## Decision

1. **The lineage is a collection, with relations in `due2-workflows.md` §3.6.** It is the sixth collection of `due2-workflows.md` §2, with a canonical form and a digest like the others (`decisions/0007`):

   ```text
   lineage       (| policy_id, version, stage1_profile, stage1_version: String, stage2_version: String)
   minted        (id)
   anonymous     (id | parent, predicate)
   identity      (node | id)
   rule_source   (rule_id | source_rule)
   selected      (rule_id, predicate | value)
   interiorised  (rule_id, predicate)
   atom_rule     (atom_id | rule_id)
   negation      (constraint_id | negates)
   ```

2. **One lineage per W1 run, never merged.** A run normalises one policy version under one normaliser version, and its lineage names both in its `lineage` tuple: the normaliser version is the stage-1 profile IRI and version and the stage-2 version, the triple that an evaluation pins (`due2-architecture.md` §7). The policy store keeps the lineage beside the corpus and finds it with `lineage(policy_id, version, normaliser_version)` (`due2-platform.md` §2.3). Explanation reads the lineage of each policy in an evaluation's corpus: the corpus's `policy` tuples give each policy and its version, and the evaluation pins the normaliser versions.
3. **Stage 1's records** (`odrl-compound-to-atomic-normalization.md` §7) are `rule_source` and `selected`, which together define the bijection of that document's invariant 3; `minted`; `anonymous`, the subject and predicate of the one triple that reaches each anonymous node; `identity`, each authored `odrl:uid` that differs from its node IRI (a blank node has no name of its own, so its uid needs no tuple); `interiorised`; and the profile IRI and version in `lineage`. A retained rule is its own source. The role by which a rule is reached is not recorded: `N(P0)` carries it in its root atoms and rule references, and the corpus in `root` and `edge`.
4. **Stage 2's records** are the ids it mints, in `minted`; `atom_rule`, the stage-1 rule each corpus atom was built from, for every atom; and `negation`, the constraint each negated constraint negates. The constraint disjuncts, the clauses, and a duty atom's binding stay in the corpus only.

## Why this holds

- **Each reader gets the records it needs.**
  - Explanation goes from a corpus atom through `atom_rule` to a stage-1 rule, then through `rule_source` and `selected` to the authored rule and the selection. A duty atom's binding is the party roles it inherited, and a duty that states any party function inherits none (`due2-workflows.md` §4), so the inherited roles are its `atom_party` tuples whose function its rule has no `selected` value for. A minted negation leads back to the authored constraint through `negation`, and a minted anonymous node to its anchor through `anonymous`.
  - The `Den` oracle needs, for each stage-1 rule, the authored rule `r` and the selection `σ` of its atom `(uid(r), σ)` (`odrl-compound-to-atomic-normalization.md` §8.1). That is `rule_source` joined with `selected`. The corpus atoms repeat the selected values, but reading them there would check stage 1 through stage 2's output, where a fault of one could hide a fault of the other.
  - The store renames exactly the ids in `minted`. An author may write a `urn:uuid:` IRI, so the form of an id does not tell a minted one from an authored one. The renaming applies to the lineage too, so a published lineage's `minted` names the published ids. A bound duty atom is found again by its duty and its binding (`decisions/0038` #3), which are `duty.source_duty` and the atom's `atom_party` tuples.
- **What the corpus holds is not repeated, except for the oracle.** The disjunct of a split atom is its `atom_constraint` set, the clauses of a duty are its `duty_constraint` tuples, a duty atom's binding follows from `atom_party` and `selected`, and a rule's role follows from `root`, `edge`, and the parent's effect (`due2-workflows.md` §3.1). Recording them again would give two sources that could disagree. `selected` is the one exception, for the reason above.
- **Per-run lineages fit minting.** A lineage is W1's output for one policy, as the corpus is. The union of corpora is a set union because shared named nodes agree (`decisions/0038`), but two lineages each have a `lineage` tuple, so a union of lineages would hold two tuples in a relation whose key is empty. Nothing needs the union: explanation reads one policy's lineage per atom.

## Rejected

- **Keep the lineage as prose until W1 is built.** The store's renaming (`decisions/0038`) and L10 already depend on its records, and the schema generator cannot check prose.
- **Reference the lineage by digest from the corpus.** A union of corpora would then hold several lineage ids, and the corpus digest would change whenever the lineage did, though no evaluation reads the lineage.
- **Record each rule's inbound roles.** A shared duty has several, and `root`, `edge`, and the parent's effect already give them.
- **Record a bound duty atom's inherited roles (`bound_party`).** They follow from `atom_party` and `selected`, since inheritance takes all of a parent's roles or none.
- **Tell minted ids by their `urn:uuid:` prefix.** An author may use such an IRI as a uid, and the store must never rename an authored id.

## Consequences

- `due2-workflows.md` v0.49: §3.6 has the relations and their table; §2 counts six collections; §3.1's `policy.version` names its reader and `duty.atom_id` where its binding is read; §3.7 and L10 read the lineage of each policy in the corpus; and §4's stage 2 row names its lineage records.
- `odrl-compound-to-atomic-normalization.md` 0.26: §7 names each record's relation and drops the inbound role.
- `due2-platform.md` v0.11: §2.3 adds `lineage`, and §2.10 says how explanation reaches it and that the store retains the lineage of each policy in a retained evaluation's corpus.
- `correctness-strategy.md` v0.20: §4.3 names the lineage relation that L10 reads, and §4.6 reads the lineage of each policy.
- `tools/gen_schema.py` reads §3.6, and the regenerated `schema/collections.schema.json` has a `Lineage` definition. No vector holds a lineage, since the evaluator never reads one, so the harness is unchanged.

## Revisit when

- A profile defines parameters, so that stage 2's parameter substitution (`due2-workflows.md` §4) binds parameter values into a duty atom. A duty atom's parameter values would then need a record, since nothing in the corpus tells them from values the rule states.
- An export to atomised ODRL is written (`decisions/0037` #6). It may need records that only the export reads.
