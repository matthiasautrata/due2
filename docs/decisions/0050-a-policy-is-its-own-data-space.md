# 0050 — A policy is its own data space

**Status:** Decided, 2026-10-28 (the owner, on #152)
**Context documents:** `due2-workflows.md` §3.1, §3.3, §3.5, §4, §5.1–§5.3, §5.5, §6.1–§6.4, §8 · `due2-profiles.md` §6 · `odrl-compound-to-atomic-normalization.md` §1 · `decisions/0023` · `decisions/0036` · `decisions/0038` · `decisions/0047` · `decisions/0048` · issues #152, #149, #151, #144, #133

## Question

Policies evaluated together are one corpus, the union of their corpora relation by relation (`decisions/0036` #5). Before this record, W2 read one hierarchy over that union: the SOTW's `closure` with every policy's corpus `closure` (`due2-workflows.md` v0.59 §3.3, `decisions/0047`, `decisions/0048` #2). The agreement check left `closure` out, as vocabulary. So the hierarchy edges that one policy states, or that its profiles bring, reached every other policy's atoms.

Two runs on clingo-i at `0928921` show the effect. In both, `A`'s own permission is on `ex:a` and does not match the request. The `Permit` comes from `B`'s rule, read through `A`'s edges.

| `A` states | `B` states | Request | `B` alone | `A` and `B` |
|---|---|---|---|---|
| `ex:copy odrl:includedIn odrl:use` | permit `odrl:use` of `ex:b` | `ex:copy` of `ex:b` | `NotApplicable` | `Permit` |
| `ex:team a odrl:PartyCollection . ex:alice odrl:partOf ex:team` | `ex:team a odrl:PartyCollection`; permit `ex:team` `odrl:use` of `ex:b` | Alice, `odrl:use` of `ex:b` | `NotApplicable` | `Permit` |

The agreement check cannot close this gap. It makes the union safe for a node that both policies state, because both must say the same of it. An edge about a node that only one policy states is never compared. #149 fixed the same flaw for a profile's conflict default, bindings, units, and schemes, and #151 for a world edge that solve 0 read. Hierarchy edges were what remained.

The question is what an evaluation may read for one policy of a set, and how a set of policies is evaluated.

## Decision

1. **A policy is its own data space.** What W2 and W3 derive for policy `P` reads only:
   - `P`'s corpus, its text as W1 normalised it;
   - the modules of the profiles `P` names, and the core, which W1 has written into `P`'s corpus;
   - the world: the request and the SOTW.

   It never reads another policy's tuples. The world is the only context that policies share.
2. **Each kind of hierarchy data has one place.**
   - Vocabulary and ontology, such as action hierarchies, classes, and the typing of collections, come with the profiles a policy names, or with the policy itself (`decisions/0020`).
   - Membership, such as who is in a team or which asset is in which collection, is world data, recorded in the SOTW with a source and a status (`decisions/0048`).
   - An edge that a policy states is local to that policy.
3. **The corpus `closure` is keyed by its policy:** `closure (policy_id, relation, narrower, broader)`. W1 writes `P`'s own edges, and those of `P`'s profile modules and the core, under `P`. The union of corpora keeps them apart. The agreement check is unchanged. It still leaves `closure` out, because no two policies share a `closure` tuple, not because the tuples are vocabulary.
4. **Findings are per entry.** An *entry* is an atom in one of its policies: those its `root` tuples name and, for the child of an edge, its parents' policies (`due2-workflows.md` §3.1, `root`). `decisions/0036` #3 introduced entries for `Permit` and `Forbid` atoms in the conflict fold. Here every atom has them, and W2 evaluates each entry in its policy's data space: a hierarchy comparison for an entry in `P` reads `P`'s `closure` tuples and the SOTW's `closure`. `finding`, `basis`, `unknown_part`, `witness_basis`, `witness_part`, `instance`, `alternative`, and `verdict_basis` gain `policy_id` in their keys, and so does the SOTW's `activation`. A duty's entry in `P` is a precondition of its parents' entries in `P`.
5. **A set is evaluated by gathering entries and folding them.** W3 forms candidates from root `Permit` entries, and reads each candidate's outstanding set from its precondition duties' entries in the same policy. The conflict fold of `due2-workflows.md` §6.2 is unchanged: it already works on entries, and an atom remains a candidate, or a prohibition, while any of its entries survives.
6. **A root obligation is in force per entry.** Its entry in `P` is in force when `P` matches the request and its guards hold in `P`'s data space. This replaces `decisions/0036` #4, under which the obligation's match was the disjunction of its root policies' matches: each root policy's entry is reported on its own. One witness record can fulfil the duty under every policy. Whether it does is read per entry, because the witness test compares `e.actor` and `e.issuer` under the party hierarchy (`due2-workflows.md` §5.3).
7. **The atoms of one compound policy share its data space,** because they are one policy. W1's atomisation is faithful (L9), so this sharing gives what the compound policy's own reading gives.
8. **Law L11, locality.** For policies `P` and `Q` that agree (`due2-workflows.md` §4), every W2 tuple that names an entry of `P` is the same in the evaluation of `{P, Q}` as in that of `{P}`, given the same request and SOTW.
9. **The completion key of a hierarchy comparison includes the entry's policy.** A part that compares under a hierarchy, such as `eq` with a concept reading or `isPartOf`, shares a completion variable only with parts of entries in the same policy (`due2-workflows.md` §6.4). An opaque part is one variable per entry.
10. **An elimination names the removing entry.** `eliminated` gains `by_policy`, the policy of the entry `by_atom` that removed it, which differs from the removed entry's policy under `prohibit-overrides` (`due2-workflows.md` §3.5).

## Why this holds

- **Independent authors.** Policies evaluated together are often written by different parties: a provider's offer, a consumer's agreement, a regulator's prohibition. Each author can vouch only for what their own policy states. Under the union, a policy's meaning changed with edges that another author wrote, so no policy could be reviewed alone. `A`'s single `includedIn` edge widened `B`'s permission in the first run above. An edge can also narrow: one that makes a prohibition's target reach the request's asset turns a `Permit` into a `Deny`.
- **Agreement gives consistency, not locality.** The check makes a shared node mean the same thing in each policy, so the union acts as a copy of the node in each. Edges about nodes that only one policy names fall outside it, and so do edges above the request's own entities, which are named per request.
- **Sharing a rule still changes no verdict.** `decisions/0036` argued that a shared rule's entries are what copies of it in each policy would be. That argument assumed that the copies read one hierarchy. With findings per entry, each entry reads what a copy in its policy would read, so the argument holds without the assumption.
- **The completion argument carries over.** The proof of monotonicity in `due2-workflows.md` §6.4 already treats each entry as a case in its own policy's fold. A finding per entry makes that literal. A completion variable is keyed by its part's binding, scope, concept reading, unit, and right operands, not by its atom. So an unresolved fact that entries in two policies compare by identity or order is one variable, and the two reads stay correlated. A comparison that reads a hierarchy is keyed by its entry's policy as well, because one value can be below `c` in `P`'s hierarchy and not in `Q`'s. One variable for both would drop that completion and could give a definite verdict where `Indeterminate` is right, the error `decisions/0023` guards against. An opaque part is a variable of its own, one per entry.
- **One witness, read per policy.** A witness record names no policy, so it serves every policy that obliges the duty, as `decisions/0036` intended. Policies that agree on the hierarchy above the duty's parties give it the same answer. Membership lives in the SOTW, which every policy reads, so they usually do.
- **World answers stay world data.** Which world edges the shell fetches depends on the corpus (`due2-workflows.md` §3.3, *Plan, then evaluate*), so the SOTW of `{P, Q}` may hold an edge that only `P`'s plan asked for, and an entry of `Q` reads it. That is no reach into `P`: the edge is a fact about the world, recorded with its source, and it holds for `Q` as much as for `P`. L11 compares two evaluations over the same SOTW, so it holds, although the plan of `{P}` may fetch less than the plan of `{P, Q}`.

## Rejected

- **Extend the agreement check to the `closure` edges reachable from a shared node's constants.** Every policy that states a rule would have to restate the hierarchy edges that another policy holds above it. The check still could not cover edges above the request's entities, which no policy names in advance.
- **Forbid hierarchy edges in a policy's body**, so that all vocabulary comes from profiles. It removes vocabulary that a policy defines for itself, which `decisions/0020` admits. It also does not stop a profile's edges from reaching a policy that does not name the profile, which needs the per-policy `closure` anyway.
- **One finding per atom, read over the union of its policies' `closure`.** `Q`'s edges would still change `P`'s entry of a rule that both state.
- **One finding per atom, read over the intersection of its policies' `closure`.** Adding `Q` would remove `P`'s own edges from `P`'s reading of the shared rule, which breaks L11 the other way.
- **Per-policy findings for `Permit` and `Forbid` atoms only, with one finding per duty atom.** A duty's guards and its witness test read hierarchies too, through `isA`, `isPartOf`, and the party comparisons of `due2-workflows.md` §5.3, so the duty would have no data space to read them in.

## Consequences

- `due2-workflows.md` v0.60 keys `closure` by policy in §3.1, reads one hierarchy per policy in §3.3, adds `policy_id` to `activation` in §3.3 and to the trace relations in §3.5, keeps each policy's `closure` apart in §4, reads `in_force` and `instance` per entry in §5.1–§5.3 and §5.5, adds `by_policy` to `eliminated` in §3.5, forms candidates from entries in §6.1 and §6.3, adds the step to the proof in §6.4 and keys a hierarchy comparison's completion variable by policy there, and adds L11 in §8.
- `decisions/0036` #3 extends to every atom, #4 is replaced by item 6 above, and #5's union keeps each policy's `closure` apart. `decisions/0047` and `decisions/0048` #2 read one hierarchy per policy: the SOTW's `closure` with the policy's own. Each gains a note.
- `due2-profiles.md` v0.29 §6 says that a policy's edges and its profiles' edges travel with that policy only. `odrl-compound-to-atomic-normalization.md` 0.29 §1 defines `EvalSet` over several policies as the gathered entries of each.
- The port schema is regenerated as 3.0, because key fields are added.
- `conformance/README.md` states that a case's `sotw.activation` applies to every entry of the duty it names. #152 adds a corpus case of two policies that pins both runs above.
- #152 brings clingo-i to this record: it keys `closure` by its text and evaluates entries, and its tests pin the two runs and L11.
- `decisions/0038` #5 keys an instance and an activation by atom. Both gain `policy_id`, and 0038 gains a note.
- #144's plan reads each policy's `closure` to find the entities whose world edges to fetch. #133's agreement check does not change.

## Revisit when

- Two policies need a vocabulary that neither defines and no profile holds. The remedy is a profile that both name, not reading across policies.
