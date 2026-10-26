# 0043 — World hierarchy edges are events on the case

**Status:** Decided, 2026-10-26 (the owner, in the review of `due2-platform.md` on that date)
**Context documents:** `due2-workflows.md` §3.3, §7.1 · `due2-platform.md` §2.4, §2.5 · `decisions/0008` · `decisions/0040` · `decisions/0044` · issue #95

## Question

The SOTW holds `closure (module, relation, narrower, broader)`: hierarchy edges from the world, such as current team membership or a dataset's classification (`due2-workflows.md` §3.3). The plan lists each world module the corpus's hierarchy comparisons use, with the request entities whose edges it needs, and the shell records what it fetches in the case.

In `due2-workflows.md` v0.50 §7.1, an `event` has `kind ∈ {fact, evidence, activation}`. No kind holds a world edge, so a case could not record one, and an evaluation's SOTW, which is the case's events taken as of `effective_at`, could hold none. Every comparison against a world module would then read an empty hierarchy, and a re-evaluation could not reproduce one that had read edges. How are world edges recorded in a case?

## Decision

1. **A world edge reaches the case as an event of kind `closure`.** `kind ∈ {fact, evidence, activation, closure}`.
2. **One `closure` event is one answer: the edges on the paths up from one request entity in one module.** The answer names the module and the entity, and holds the `closure` tuples the source returned, possibly none. Its content id is the event's `ref`. One answer answers one planned read, so the plan's size stays what the corpus and the request fix (`due2-workflows.md` §3.3, *Read limit*).
3. **The SOTW's `closure` is the union of the latest answers.** For each module and entity, the SOTW takes the answer with the latest `valid_at` no later than `effective_at`, as it does for each property and source (`decisions/0040` #2). A later answer for an entity replaces its earlier one, so an edge the world removed above that entity is gone from the next evaluation.
4. **The module is named, not versioned, in the answer.** The version of the source that answered is the event's `source_version` (`decisions/0044`), as for a fact.

## Why this holds

- **Evaluation and re-evaluation read only the case.** The owner: "we need that, otherwise eval or re-eval will not work." An evaluation reads only what its case has recorded (`due2-workflows.md` §3.3), and replay rebuilds the SOTW from the events (`due2-workflows.md` §7). An edge the case does not hold cannot be read, and an edge read from outside the case cannot be replayed.
- **An answer per entity can say that an edge is gone.** Hierarchy is closed-world: an edge that is not recorded does not hold. If each event held one edge, removing an edge would need an event that retracts it. An answer that lists every edge above an entity replaces the last one, as a fact's later answer replaces its earlier one, and the ledger stays append-only.
- **Paths, not direct edges, keep the plan fixed.** If an answer held only the direct edges above its entity, the shell would learn each ancestor from one answer and then ask about it, so the reads would grow with what the sources return, and the plan could not be known before any fetch. An answer for a request entity is the question the plan names.
- **Answers that share an ancestor are kept current by their source.** Two request entities with a common ancestor each hold the ancestor's edges. If one answer is newer than the other, the union keeps an edge the newer one dropped until the older answer is replaced. That is the staleness `decisions/0040` #4 gives to the SOTW service, which supplies a new answer when a value it supplied changes in the world.

## Rejected

- **One event per edge.** An edge removed from the world would need a retraction event, and the SOTW would have to pair retractions with additions.
- **An answer of direct edges only.** The plan would grow with each fetch, as above.
- **The version in the module's name.** Each version of a source would be a different module, so a later answer from a new version would not replace the earlier one (item 3), and both would stay in the union.

## Consequences

- `due2-workflows.md` v0.51: §7.1 adds the kind and states items 2 and 3, and §3.3 says that each world-module answer is an event.
- `due2-platform.md` v0.13: `edges` returns one answer per entity, with the source's version (§2.4).
- What an answer records when its lookup fails is #95. This record gives a failed answer a place, the event, but not a status.

## Revisit when

- A source can answer only one edge at a time. The shell would then assemble each path answer from several lookups before recording it.
