# due2 — Platform

**Status:** Draft v0.10. Every section is **[O]**: a map of the components around the evaluator, not a build order and not a decision. Where a section restates the specification, it cites it, and the specification's marker applies.
**Companions:** `due2-architecture.md` (what due2 is and why) · `due2-workflows.md` (the workflows and the data model this document builds on).

**Changes in v0.10** (2026-10-26, `decisions/0038`, #107): a case fixes its corpus, so `create_case` takes one, and an amended policy reaches an earlier request through a new case (§2.2, §2.6, §2.11, §3.3, §3.5). Evidence names its grant in two fields (§3.2). `put_corpus` renames the ids W1 minted for a published node's parts to the published ones (§2.3), and a policy version is a minted id (§2.3). Earlier changes are in `docs/archive/changes.md`.

Markers as in the companions: **[D]** decided · **[O]** open, alternatives listed · **[F]** blocked on an external unknown.

---

## 0. What this is

due2's specification fixes three pure functions, `normalise`, `plan`, and `decide`, and a *shell* around them that fetches facts, keeps cases, and stores traces (`due2-architecture.md` §2). This document breaks that shell into components. For each component it gives:

- its responsibility;
- the data it owns;
- a sketch of its interface;
- the section of the specification it inherits from.

It also gives the use cases the components serve (§3) and how they replace a running predecessor system (§4). The reader is anyone designing or reviewing a component, or deciding where a new capability belongs.

The specification governs. Where this document and `due2-workflows.md` disagree, the workflows document is right and this one has a defect. Nothing here reopens a **[D]** item. Where a component needs something the specification lacks, §5 names the gap and its issue.

**Vocabulary.** Terms the specification defines (request, SOTW, case, trace, frontier, plan) are listed in `due2-architecture.md` §0. This document adds:

| Term | Meaning |
|---|---|
| component | A unit with one responsibility and its own interface. It may run in its own process or share one (§1.2). |
| port | A component's interface, stated in the data model of `due2-workflows.md` §3, independent of transport (Cockburn's term, `references.md` §8). |
| adapter | A binding of a port to one transport: an in-process call, REST, or MCP (the Model Context Protocol, through which a language-model assistant calls tools). |
| orchestrator | The case workflow (§2.6): the one component that calls the others (§1.2). This document calls it the orchestrator, so that "workflow" keeps the sense of W1–W3. |
| evaluation | The record of one `decide` call: the `evaluation` tuple of `due2-workflows.md` §3.5, which names the four input collections, with the pins and the trace (§2.2). The act is a call to `decide`. |
| engine | One deployment of the evaluator, named by implementation and version. The predecessor's evaluator is another engine (§2.6, §4). |
| normal path, fast path | Whether a call to the evaluator carries its corpus in full or only the corpus's digest (§1.3). |
| connector | An adapter that fetches one kind of fact from an outside system, such as HR or a data catalog, for the SOTW services (§2.4). |
| inquiry | What a person asks in one sitting, such as "may I use these three datasets for this purpose". It holds one or more requests (§2.6). |
| draft request | A request whose parameters are still being gathered. It becomes a request when its case is created (§2.6). |
| predecessor | The decision system in service before due2, which due2 replaces gradually (§4). |
| route | One operation of the predecessor's interface, such as one REST endpoint, and the due2 call that replaces it (§4). |
| classification | A class of datasets in the catalog, such as `PII`. A dataset falls under a classification through hierarchy edges, and a policy may target the classification (§2.5). |

---

## 1. Principles **[O]**

### 1.1 The platform is the shell

`decide` is pure over its four inputs: corpus, request, SOTW, and config (`due2-workflows.md` §3.5). It never fetches, never waits, and never asks. Everything impure happens around it: finding the policies, fetching facts, asking people, recording answers. That keeps the evaluator replayable (`due2-workflows.md` §7), and it is why the evaluator is a component of its own (§2.1) that the case workflow calls with everything already gathered, rather than a service that fetches what it needs during evaluation.

### 1.2 Ports and adapters; deployment is configuration

Each component exposes a port (Cockburn, `references.md` §8). An in-process call, REST, and MCP are adapters over that one port. Whether two components share a process or talk over the network is a deployment setting, not a design change.

This works only if each port is designed for the remote case, with the in-process call as an optimisation of it:

- **Coarse calls.** One call per step of a use case, not one per object.
- **Immutable collections, by value.** Arguments are canonical collections (§1.3), never live object graphs.
- **Safe retries.** A caller that times out does not know whether its write landed, and retries. A retry must not record an event twice. How the ledger recognises a repeated write is open; it must not add concurrency machinery to the event relation, which `decisions/0008` declined (#98).
- **Explicit errors.** A call that fails returns `Error(cause)`, as a crashed evaluation does (`due2-workflows.md` §7). A remote call can also fail in transport, and the caller handles that the same way.

**Each component works in its own space.** The orchestrator (§2.6) is the only component that calls other components. It fetches collections from the stores by id, passes them by value to the components that compute, and records what they return. Every other component answers from what the call carries and from the state it owns. The evaluator therefore receives all four of its inputs by value, so a replay with the same inputs is the same call as the original. The SOTW services and the catalog reach outside systems, which is their own space (§2.4, §2.5). The request GUI and the intelligent services call the orchestrator, and reach the other components only through it. A component's log serves operations and is never a record: the ledger is the record (§2.2).

**One schema, several adapters.** The port schema is generated from the relations of `due2-workflows.md` §3 and written in JSON Schema 2020-12 (`schema/README.md`). The REST description, in OpenAPI 3.1, and the MCP tool definitions are both generated from it, so the adapters cannot drift apart: OpenAPI 3.1's Schema Object is a superset of JSON Schema 2020-12, and MCP states a tool's inputs and outputs in JSON Schema (`references.md` §8). A collection carries no JSON-LD `@context`, and every `Id` is a full IRI, never a prefixed name such as `ex:a1` (`due2-workflows.md` §2). Its id is the digest of its bytes (`decisions/0007`), and a context or a prefix would let one value be written in two byte forms, so two collections with one meaning would have two ids. A JSON-LD context for consumers who want linked data can be added as a view, because it does not change the bytes that are hashed.

**One process by default.** The components are modules of one deployable. A component moves to its own process when its runtime character requires it:

- pure and stateless: the evaluator and W1;
- stateful: the ledger and the policy store;
- effectful: the connectors and the catalog;
- long-running: the orchestrator.

### 1.3 Ids and values

Every collection, whether corpus, request, SOTW, config, or trace, is canonical JSON, serialised by JCS (RFC 8785) as `due2-workflows.md` §2 states, and its id is its digest (`decisions/0007`). Stores hold collections under their ids, and records refer to them by id: an `evaluation` tuple names its corpus, request, SOTW, and config by id (`due2-workflows.md` §3.5). Between components, collections travel by value (§1.2). A cached collection can never be stale, because a changed collection has a different id. Versions and provenance largely follow from this (§2.10).

**The normal path and the fast path.** On the normal path, every call to the evaluator carries its corpus in full. The evaluator computes the corpus's digest itself and keeps the parsed and indexed corpus under it, so a repeated corpus is hashed again but not parsed or indexed again. This memo is derived state: the output is the same whether the corpus was held or not, and dropping the memo costs only time. The evaluator never takes the digest from the caller, because a wrong digest would file one corpus under another's id. On a fast path, the caller would send only the digest, and the evaluator would reply `not held` when it lacks the corpus. Every caller would then have to handle that reply, so the fast path is added only if the measurements of `ways-of-working.md` §10.4 (`decisions/0027` item 6) show that the transfer matters.

### 1.4 Who decides, and who may assert a fact

- **Only the evaluator decides.** No other component computes, approximates, or overrides a verdict. A rendering may select and order the reasons the trace holds, and never adds one (`due2-workflows.md` §3.7).
- **The configuration decides whose facts count.** Each state fact carries an `attribution`, its source and observation time. `admit_source` and `admit_age` say which sources count for which property (`due2-workflows.md` §3.4). A value from a source not admitted for its property is treated as `missing`.
- **The requester states the request.** Request-source operands, such as purpose or record count, read the request (`due2-profiles.md` §3). The requester supplies them, and the profile's binding is what makes them the requester's to state.
- **The intelligent services assert nothing.** They choose and phrase questions, map free text onto request fields and catalog entries, and narrate a rendered explanation. A state fact a person gives through them is recorded with that person as its `attribution` source, and counts only for properties whose `admit_source` lists that source. Otherwise it is treated as `missing` (`due2-workflows.md` §3.4), an opaque `U` part that completion does not split (`decisions/0016`), so an inadmissible answer can widen the verdict range instead of narrowing it. The orchestrator therefore asks a person only for properties whose `admit_source` admits them.

---

## 2. Components **[O]**

```text
                 ┌──────────────── request GUI ─────────────────┐
                 │  datasets · questions · verdict and reasons  │
                 └──────────────┬───────────────────▲───────────┘
                                │                   │
                     ┌──────────▼───────────────────┴───────┐
                     │  intelligent services                │  choose and phrase questions,
                     │  never decide, never assert a fact   │  map text to request fields
                     └──────────┬───────────────────────────┘
                                │
┌──────────────┐     ┌──────────▼─────────────────────────────┐     ┌──────────────────┐
│ catalog      │◄────┤  case workflow (orchestrator)          ├────►│ SOTW services    │
│ (external)   │     │  select · plan · ask · fetch ·         │     │ one connector    │
│ dataset →    │     │  record · decide · record · show       │     │ per bound        │
│ classes and  │     │  the only caller of the others         │     │ property         │
│ policies     │     └┬─────────┬────────────────┬───────────┬┘     └──────────────────┘
└──────────────┘      │         │                │           │
                      │         │                │           │
  ┌───────────────────▼┐ ┌──────▼───────┐ ┌──────▼───────┐ ┌─▼──────────────┐
  │ normalisation      │ │ policy store │ │ evaluator    │ │ ledger         │
  │ (W1): batch,       │ │ policies,    │ │ plan, decide │ │ case · event · │
  │ once per           │ │ corpora,     │ │ pure         │ │ evaluation     │
  │ policy version     │ │ profiles     │ │              │ │ append-only    │
  └────────────────────┘ └──────────────┘ └──────────────┘ └────────────────┘
```

Explanation (§2.9) is a component the orchestrator calls, as it calls the evaluator. Authoring (§2.11) is a set of use cases the orchestrator runs. Versions and provenance (§2.10) are obligations on every store. None of the three is drawn.

| § | Component | Inherits from |
|---|---|---|
| 2.1 | Evaluator | `plan` and `decide` (`due2-architecture.md` §2; `due2-workflows.md` §3.3, §5–§6) |
| 2.2 | Ledger | `due2-workflows.md` §7.1; `decisions/0008` |
| 2.3 | Policy store | `due2-workflows.md` §3.1 (corpus), §3.6 (lineage); `decisions/0007` |
| 2.4 | SOTW services | `due2-profiles.md` §3 (operand bindings); `due2-workflows.md` §3.3 (`fact`, `attribution`) |
| 2.5 | Catalog | `due2-workflows.md` §3.3 (world `closure` modules) |
| 2.6 | Case workflow | `due2-workflows.md` §1, §3.3 (the shell loop); `due2-architecture.md` §7 (re-evaluation) |
| 2.7 | Intelligent services | Nothing: the component is new |
| 2.8 | Normalisation | `due2-workflows.md` §4 (W1); `due2-diagnostics.md` |
| 2.9 | Explanation | `due2-workflows.md` §3.7; `decisions/0010` |
| 2.10 | Versions and provenance | `due2-architecture.md` §7 (normaliser pins); `due2-workflows.md` §3.6 (lineage) |
| 2.11 | Authoring | `due2-diagnostics.md` (W1's diagnostics) |

The interface sketches below use `name(arguments) -> result`. Types are those of `due2-workflows.md` §3. Every call can also return `Error(cause)` (§1.2), which the sketches leave out.

### 2.1 Evaluator

Answers one access question from its four inputs, and lists in advance what the answer can depend on. It owns no state: its memo of indexed corpora (§1.3) is derived and can be dropped.

```text
plan(corpus, request)                            -> Reads
decide(corpus, request, sotw, config)            -> Trace
```

`Reads` and the rule that `decide` runs only once every planned read is in the case are `due2-workflows.md` §3.3. The verdict is one relation of the trace, and the explanation is the part of the trace reachable from it (`due2-workflows.md` §3.7).

All four inputs arrive by value, and the evaluator fetches nothing (§1.2). §1.3 gives the normal and fast paths for the corpus. Inside the call, the evaluator may skip atoms through an index it builds from the corpus, within the limits of `due2-workflows.md` §5.5: only roots that are certainly `F`, never an atom whose match turns on a `U` part, never a precondition of a live permission. §2.3 gives the same rule for choosing the corpus. The request-free question, which duties a party owes now, is a second function over the same corpus (`due2-architecture.md` §6.3, #6).

### 2.2 Ledger

Holds cases: one per request and corpus, with every fact, piece of evidence, activation, and evaluation recorded as an event, append-only (`due2-workflows.md` §7.1).

```text
create_case(request, corpus_id)            -> case_id
append(case_id, event)                     -> seq
record_evaluation(case_id, evaluation)     -> seq            # built by the orchestrator (§2.6)
case(case_id)                              -> request, corpus, events, evaluations
sotw(case_id, effective_at)                -> sotw_id        # the case's events as of effective_at, frozen
get(collection_id)                         -> collection     # a request, SOTW, or evaluation it holds
cases(latest_verdict?)                     -> case_ids       # for re-evaluation (§3.3)
owed(party, at)                            -> duty instances # the monitoring question, open (#6)
```

The orchestrator calls `decide` and builds the `evaluation` (its ids, pins, and trace); the ledger only records it, and calls no other component (§1.2). Replay is therefore the orchestrator's (§2.6). The ledger never edits an event and never recomputes an earlier decision to answer an audit question: the earlier `evaluation` event is the answer.

### 2.3 Policy store

Holds authored policies, their corpora, configs, profile modules with their operand bindings, and the vocabularies and concept schemes policies refer to. Every item is immutable. A collection is named by its digest (`decisions/0007`), and a policy version by an id minted when it is stored (`decisions/0038`). A policy's current version is a pointer to one of them.

```text
put_policy(document)                       -> policy_id, version
put_corpus(policy_id, normaliser_version, corpus, lineage) -> corpus_id | IdentityConflict  # W1's output (§2.8)
corpus(policy_ids, normaliser_version)     -> corpus_id | absent          # the union of these policies' corpora
get(collection_id)                         -> collection
profiles()                                 -> profile modules
binding(property)                          -> operand binding             # due2-profiles.md §3
select(target, ancestors, action, parties) -> policy_ids                  # open (§5 #1)
```

The store never runs W1. Normalisation (§2.8) produces each corpus as a batch job when a policy version or a normaliser version is stored, and the orchestrator puts it here, which publishes it. On the request path, the orchestrator finds the policies that may apply with `select`, and their corpus with `corpus`: the union of their published corpora, relation by relation, which needs no normalisation and has no conflicts (`due2-workflows.md` §4). It is absent when a selected policy has no published corpus for the normaliser version, and what the request gets then is open (§5 #1). The store keeps each union it returns, so an evaluation can pin it. The evaluator then skips atoms within that corpus (§2.1). The orchestrator does not run W1 on the request path (`decisions/0027` item 3).

**Publishing checks agreement.** `put_corpus` publishes one policy's corpus; `put_policy` only stores its document. For each node that a published corpus of the same normaliser version holds, it compares the new corpus with the published one up to the renaming of minted ids. If they agree, it renames the ids W1 minted for the node's parts to the published ones, in the corpus and in its lineage, so the node and its parts are one individual across policies (`decisions/0038`). If they do not, it refuses the corpus with `IdentityConflict`, naming the node and the policy that holds it. The refused policy is not published, and the published ones are unaffected (`due2-workflows.md` §4, *Several policies are one corpus*). Only the current version of each other published policy is compared, never an earlier version of the same policy. A conflict within a set of policies is a conflict between two of them, so every set of published policies agrees, and every union `corpus` returns is well-formed. Building the checker is #133.

**Offers are selected like any other policy.** A store holds offers as well as agreements, and a verdict over an offer says what its terms permit, not that it has been accepted (`due2-workflows.md` §6.4, `decisions/0031`). Accepting an offer, such as by signing a contract, is a separate step outside the evaluator.

**A replaced policy is never selected.** A policy with `dct:isReplacedBy` is void, and its replacement is the policy to process (ODRL IM §2.8). `select` never returns a policy that names a replacement, and returns the replacement wherever it may apply. W1 rejects a replaced policy that reaches it (`ReplacedPolicy`, `decisions/0033`), because W1 never dereferences an IRI and so cannot fetch the replacement itself (`odrl-compound-to-atomic-normalization.md` §3).

**Selection must over-select.** `decide` reads only the policies in its corpus, so choosing that corpus is part of the decision's soundness. Suppose policy A permits reading dataset D and policy B prohibits it. Over both, the verdict is `Deny`; over A alone, it is `Permit`. Prohibition monotonicity (L5, `due2-workflows.md` §8) says only that adding B cannot raise the verdict, not that a corpus may leave B out.

Including a policy that cannot match the request is safe, because root atoms that are certainly `F` leave the trace unchanged (L8, `due2-workflows.md` §8). The converse needs care. A policy's obligations are in force when one of its `Permit` or `Forbid` atoms *matches* the request on action, relation, and parties, whatever its constraints (`due2-workflows.md` §5.2). So a policy whose permission matches but whose constraint is certainly `F` still puts its obligations in force, and under `violations = deny` a violated one acts as a prohibition (`due2-workflows.md` §6.4). Selection must therefore keep every policy with a `Permit` or `Forbid` atom whose match on action, target, and parties is not certainly `F`, and may skip a policy on those fields only, never on a constraint. This is the policy-level reading of the index rule of `due2-workflows.md` §5.5; #105 is to state the rule per root atom, with a property test. A catalog's attachment of a policy to a dataset helps find policies but is not the criterion: a policy whose target is a classification the dataset falls under applies whether or not anyone attached it.

### 2.4 SOTW services

Fetch the facts a plan names and return them in the form the SOTW records them: a status, values, and an attribution (`due2-workflows.md` §3.3). One connector serves each bound state property, or a family of them. The registry maps a property IRI to its connector.

```text
resolve(property, entities, at)            -> fact(status, values, attribution)
edges(module, entities)                    -> closure edges, with the module's version
register(property | module, connector)
```

Four rules from the specification bind every connector:

- **One hop.** "The requester's department" is one property, flattened by the connector. Computing values is the connector's job and never the evaluator's (`due2-profiles.md` §3).
- **Statuses are never collapsed.** `missing` means the source says no value exists. `unresolved` means the source could not be asked or did not answer. A connector that times out returns `unresolved`, never `missing`.
- **Answers, not extensions.** The case records the answer to the question asked, such as membership of one group, and the source version it came from. It never records the dataset the answer was computed from (`due2-workflows.md` §3.3).
- **The corpus decides what is needed.** A connector is needed for each property that the corpus's constraints read and that a profile binds to the state source. A profile binding that no policy reads needs none. A planned property with no connector is recorded as `unresolved` (§3.6).

### 2.5 Catalog

The data catalog is external. The catalog connector answers two questions about an identified dataset:

```text
describe(dataset)                          -> classification edges, attached policy ids
search(text)                               -> datasets
```

**Classifications are targets.** A classification edge such as "dataset D is in class PII" is a hierarchy edge from the world: a `closure` tuple in a world module (`due2-workflows.md` §3.3). A policy whose target is `PII` then matches a request for `D`, because `D ⊑ PII`. The catalog's edges feed two steps:

- policy selection (§2.3);
- matching, as SOTW closure edges recorded in the case.

**The catalog is the most dangerous connector.** Hierarchy is closed-world: an edge that is not recorded does not hold, and the part that needs it is `F`, not `U` (`due2-workflows.md` §3.3). The one exception is concept-scheme membership: a concept with no `skos:inScheme` edge to its operand's schemes makes its constraint `U` (`due2-workflows.md` §3.3, `due2-profiles.md` §4). A dataset's classification is a target hierarchy edge, not a scheme membership, so the exception does not cover it. A catalog that fails to report a classification therefore does not make a prohibition on that classification unknown. It makes the prohibition certainly not apply. `due2-workflows.md` §3.3 says that a lookup that fails is recorded as `unresolved`, but `closure` has no status field, so the SOTW has no way to record a hierarchy lookup that failed (§5 #2).

### 2.6 Case workflow

The orchestrator: it runs a use case from the first question to the presented answer, and is the only component that calls the others (§1.2). It fetches what each call needs, passes it by value, and records the result. It owns inquiries and draft requests. Cases belong to the ledger.

```text
open_inquiry(subject, action, datasets, at?)   -> inquiry_id, questions
answer(inquiry_id, answers)                    -> questions | outcomes
submit_evidence(case_id, evidence, key)        -> evaluation
reevaluate(case_id)                            -> evaluation
replay(case_id, seq, engine)                   -> match | mismatch
```

**Inquiries.** A request has at most one target (`due2-workflows.md` §3.2), and each request has one case (`decisions/0008`). A person asking about three datasets therefore makes three requests, and the inquiry groups them. How the requests share questions and answers is open (§5 #4). In the simplest form, each request is asked and decided on its own, and the inquiry only groups the answers.

**Draft requests.** A case's request is fixed when its case is created, except for its `at`, which each evaluation moves to its own time (`due2-workflows.md` §3.2, §7.1). Request parameters, such as purpose, therefore have to be gathered before the case is created, while the request is a draft. State facts are gathered after, as events on the case. §3.1 walks through the sequence.

**Re-evaluation.** When facts change, the orchestrator re-evaluates the affected cases. When a policy or normaliser version changes, it opens a new case over the new corpus for each affected request instead, because a case fixes its corpus (`due2-workflows.md` §7.1, `decisions/0038`). The new case starts without the earlier one's activations and evidence. Which cases count as affected is open. `due2-architecture.md` §7 starts with recomputing every pending case on any change. That alone never revokes a `Permit`, because a decided case is not pending, so revocation (§3.3) needs decided cases re-evaluated, or reopened over a new corpus, as well. Each evaluation asks at its own time: the orchestrator builds its request from the case's, with `at` moved to the evaluation's `effective_at` when the case's `at` is earlier, so it never sends an access evaluation an `at` earlier than its `effective_at`. The latest evaluation is the case's current answer, and the newest case of a request gives the request's (`due2-workflows.md` §3.2, §7.1; `decisions/0030`).

**Replay.** To check a recorded evaluation, the orchestrator fetches the four collections it names, from the policy store and the ledger, calls `decide` with them, and compares the digest of the new trace with the recorded one (`due2-workflows.md` §7). To the evaluator this is an ordinary call. The orchestrator chooses the `engine` that answers: a replay on the engine that made the evaluation checks the record, and a replay on the current engine checks for a regression. The first needs the ledger to record each evaluation's engine, which is open (§5 #5).

### 2.7 Intelligent services

An assistant, typically a language model, that serves the request GUI and drives the orchestrator through its MCP adapter.

- **It may:** find datasets from a description (catalog `search`, through the orchestrator); order questions by what decides the verdict (§3.1); phrase a question for its reader; map an answer onto a request field or a fact; narrate a rendered explanation (§2.9).
- **It may not:** call `decide` with facts it supplies; record a fact under any source other than the person who gave it; change a verdict or add a reason (§1.4).

Its useful work rests on what the trace already reports. For an `Indeterminate`, the trace names the atoms whose unknown parts decide the verdict (`verdict_basis` with role `unknown`, `decisions/0011`), the inputs those parts read (`unknown_part`), and the best and worst verdict still possible (`verdict_range`). For a `Pending`, the frontier lists the duties that would permit (`due2-workflows.md` §6.3). Asking about those first is the loop of §3.1, steps 8–10.

### 2.8 Normalisation

W1 behind a port: authored policies and their profiles in, a corpus or rejection diagnostics out (`due2-workflows.md` §4, `due2-diagnostics.md`). It runs once per policy version and normaliser version, never per request. It sits beside the policy store, off the request path: the orchestrator runs it as a batch job when a policy or normaliser version is published, and puts its corpus in the store (§2.3).

```text
normalise(policy, profiles)               -> corpus, lineage, warnings | rejections
```

### 2.9 Explanation

**Decision explanation** is read from the trace, never computed alongside it (`due2-workflows.md` §3.7). The service derives the explanation and renders it for a reader: a page, prose, or a summary for the intelligent services to narrate. A rendering that needs something the trace lacks reveals a trace defect, which is fixed in the trace, not in the renderer.

**Policy explanation** answers what a policy means before any request is made. It is read from the corpus and its lineage: the atoms one authored rule produced, their constraints, and the warnings W1 accepted the policy with.

```text
explanation(trace)                        -> derivation         # due2-workflows.md §3.7
render(derivation, audience)              -> text
explain_policy(corpus, lineage, warnings) -> atoms and constraints per authored rule
```

### 2.10 Versions and provenance

Mostly a consequence of §1.3, plus one obligation:

- **Content ids and immutable collections:** §1.3.
- **What each evaluation pins:** the corpus, SOTW, and config ids, and the normaliser versions in force (`due2-workflows.md` §7.1).
- **Which authored rule each atom came from:** the lineage (`due2-workflows.md` §3.6).
- **The obligation — retention:** replay needs every collection an evaluation names (`due2-workflows.md` §7). A store may therefore not delete a corpus, profile version, or lineage that any retained evaluation references.

### 2.11 Authoring

Supports writing and amending policies:

- **Lint:** W1's diagnostics.
- **Explain:** policy explanation (§2.9).
- **What-if:** before a version is published, call `decide` on recent cases and pending ones over the new corpus and list the verdicts that would change, revocations first. Nothing is recorded: each case keeps its corpus, and the new version reaches a request only through a new case (§2.6).

`decide` is pure and each case holds its SOTW, so a what-if run reads the ledger and writes nothing to it. The orchestrator runs it, as it runs a replay (§2.6). Whether what-if results are recorded at all is open (§5 #6).

```text
lint(document, profiles)                  -> diagnostics
what_if(corpus_id, case_ids)              -> verdict changes
```

---

## 3. Use cases **[O]**

### 3.1 Ask whether a dataset may be used

**The sequence.**

1. **Identify.** The person names datasets. The orchestrator finds them in the catalog (`search`) for the intelligent services.
2. **Describe.** For each dataset, the catalog returns its classification edges and attached policies (§2.5).
3. **Select.** The orchestrator asks the policy store for the corpus of every policy that may apply (§2.3), and fetches it.
4. **Draft.** The orchestrator drafts a request: the action, the dataset as target, the subject from authentication, and the time.
5. **Plan.** `plan` names everything the decision can read: request parameters, state properties, and hierarchy modules.
6. **Ask for parameters.** The planned request parameters are questions for the requester. When they are answered, the request is complete and the case is created. `plan` runs again on the complete request, since what it names can depend on the request.
7. **Fetch.** The connectors fetch every planned state property and hierarchy module. Each answer is recorded as an event, including failures as `unresolved`.
8. **Decide.** Every planned read is now in the case, so `decide` runs and the evaluation is recorded.
9. **Show.** The verdict and its explanation are shown:
   - a `Permit` names the policies that permit, so over an offer it reads "this offer permits you to proceed";
   - a `Pending` shows its frontier as the duties that would permit;
   - an `Indeterminate` shows what is missing and its `verdict_range`.
10. **Iterate.** For an `Indeterminate`, the orchestrator asks for the inputs that decide it: from a person, where `admit_source` admits them, or from a connector again, up to a retry limit the deployment sets. Each answer is a new event, and step 8 runs again.

**Why the loop is safe.** Information monotonicity (L4, `due2-workflows.md` §8) concerns one world whose unknowns get answered. A value that fits can only replace an `Indeterminate`. An answer that turns out not to fit, or that says no value exists, can turn a definite verdict into `Indeterminate`, but never into another definite one. So within one world, asking more never replaces one definite verdict by a different one; at worst it makes the answer less certain. A fact that changes in the world while the loop runs is a different matter: it is a new fact, and the verdict can move either way (§3.3).

**Why the loop ends.** It asks only about planned reads. The plan is fixed by the corpus and the complete request (`due2-workflows.md` §3.3), so it is finite. The orchestrator asks a person for each read at most once, and retries a connector at most up to the retry limit. Once every planned read has an answer, the retries are spent, or the person declines to give more, there is nothing left to ask.

**Worked example.** The case `conformance/cases/rl2-geo-restriction`, translated from RL2, has one policy (`policy.ttl`) and four scenarios (`case.json`). The case fixes the policy, the facts, and the verdicts; the steps around them, and `admit_source`, are this document's illustration.

- **Policy.** `ex:Customer` may `ex:access` `ex:Dataset` if `ex:jurisdiction` equals `"EU"`. The operand is bound to the state property `ex:requestJurisdiction`, so the value comes from a jurisdiction service, not from the requester.
- **Steps 4–8.** The plan names `ex:requestJurisdiction`, the only world value the policy reads. The service does not answer, the connector records the fact as `unresolved`, and `decide` runs. The case's expected output for scenario "jurisdiction unresolved" is, in excerpt (README § Verify runs every scenario of the case through clingo-i):

  ```json
  {"verdict": "Indeterminate",
   "verdict_basis": [{"ref": "ex:euAccess", "role": "unknown"}],
   "unknown_parts": [{"ref": "ex:euAccess", "input": "ex:requestJurisdiction", "status": "unresolved"}],
   "verdict_range": {"low": "NotApplicable", "high": "Permit"}}
  ```

- **Steps 9–10.** The screen says: undecided; at best permitted, at worst no rule applies; the one open question is the jurisdiction. If `admit_source` lists only the jurisdiction service, the orchestrator retries the connector and does not ask the customer, whose answer would not count (§1.4). A retry that returns `"EU"` gives `Permit` (scenario "EU jurisdiction"), `"US"` gives `NotApplicable` ("non-EU jurisdiction"), and `"EU"` and `"US"` from two determinations give `Indeterminate` with status `conflict` ("jurisdiction in conflict"). A conflict is not resolved by asking again: someone has to correct the disagreeing sources.

**Asking parameters in order of importance [O].** Step 6 asks every planned request parameter before the case is created. Asking first the ones that decide the verdict would need a call to `decide` over the draft request. An absent request parameter reads as `missing`, which is an opaque `U` part. An opaque part only adds completions, so its cost is an `Indeterminate`, never a wrong definite verdict (`decisions/0016` § Why it is sound). A call over the draft is therefore sound, but its `verdict_range` can be wider than the facts warrant (§5 #3).

### 3.2 Fulfil a duty

A `Pending` verdict records the duty instances it awaits (the trace's `instance` and `alt_duty`). The person performs one, such as obtaining an approval. The evidence is submitted naming the grant it answers, the authored duty and the request's `reference` (`discharges_duty` and `discharges_reference`, `due2-workflows.md` §5.3), recorded as an event, and the case is evaluated again (`due2-architecture.md` §7, the case flow). Nothing in the earlier evaluation changes.

### 3.3 The world changes

A role changes or a dataset is reclassified, and the orchestrator re-evaluates the affected cases. A policy is amended, and it opens a new case over the new corpus for each affected request (§2.6). The ledger records each new verdict as a new evaluation. Re-evaluation can turn a `Permit` into a `Deny`, a revocation, and the operation is the same in both directions (`due2-architecture.md` §7).

### 3.4 Audit a past decision

"What did we decide on 3 March, and why?" The ledger returns that evaluation, the orchestrator replays it on the engine that made it (§2.6), and the explanation service renders its trace. Today's policy is not consulted (`due2-architecture.md` §7, two clocks).

### 3.5 Amend a policy

The author edits the policy, lints it through W1, reads its explanation, and runs a what-if over recent cases and pending ones (§2.11). Publishing stores a new version, and new cases for the affected requests follow as in §3.3.

### 3.6 Add a source of facts

A new profile binds a new state property, or an existing property gains a source. Someone writes a connector, registers it for the property, and lists the source in `admit_source`. Until the connector exists, a plan that names the property records it as `unresolved`, and the parts that read it are `U`, never `F`.

### 3.7 What does a party owe now

Ledger management needs the duties a party owes across cases, independent of any request: the monitoring question of `due2-architecture.md` §6.3, open as #6.

---

## 4. Migration **[O]**

due2 replaces a predecessor that is in service, and its callers cannot all move at once, so the replacement is gradual: the *strangler fig* pattern (Fowler, `references.md` §8). New interfaces grow around the old system, take over one route at a time, and the old system is retired when no route uses it.

**Interface migration and engine migration are separate.** The predecessor's evaluator need not share due2's semantics: in particular, how it treats unknown data, and whether it reports what due2's trace reports. A due2 interface in front of the predecessor is therefore a facade over different semantics. That creates two risks:

- The facade lends the predecessor's answers the credibility of due2's contract.
- When the engine behind the facade is swapped, verdicts change behind an unchanged interface: a behaviour change presented as a refactoring.

The engine is chosen per route: a *branch by abstraction* (Fowler, `references.md` §8), where due2's interface is the abstraction and the predecessor and due2 are its two implementations. Each route moves through four phases, and its callers can see which phase it is in:

| Phase | What answers | What callers see |
|---|---|---|
| 1. Facade | The predecessor, behind due2's interface | due2's shape, with the answering engine named. A field the predecessor cannot fill is absent, never invented. |
| 2. Shadow | The predecessor. due2 evaluates the same input alongside, and both results are recorded | No change |
| 3. Cut-over | due2 | Verdicts may change. Each class of difference found in phase 2 is explained before cut-over. |
| 4. Retire | — | The predecessor's route is removed once nothing calls it. |

**The facade keeps the rules.** Unknown is never false at the facade either. It may present a predecessor's answer as the predecessor's. It may not present one as due2's verdict. How much the facade can fill depends on what the predecessor reports: a verdict, which inputs were missing, duty frontiers, a record of its decisions. Each such field is mapped explicitly, and a gap stays a gap.

**The shadow diff is a source of cases.** A shadow run plans, fetches, and decides as a real one does. `decide` is pure, so the only effects are the fetches, which load the sources, and the record of the result. Shadow results are recorded apart from the ledger's cases, so a shadow verdict is never mistaken for a decision (§5 #5). GitHub's Scientist is the model (`references.md` §8): callers keep getting the old answer, and every mismatch is recorded with its input. Each mismatch is one of three things:

- a defect in the predecessor, which becomes part of the explanation for the cut-over;
- a gap in due2's specification, which becomes an issue;
- a disagreement worth keeping, which becomes a conformance case under the corpus rules.

The predecessor is not an oracle, so a mismatch is something to triage, never a verdict on which side is right. If the predecessor records each decision's inputs, the first shadow run can replay recorded decisions offline, without touching a live route.

**Order.** Routes that carry no semantics move first: catalog lookup, then fact connectors, then the policy store. The evaluator's routes move last, through the shadow phase. Normalising the predecessor's policies through W1 early is a cheap measurement: each rejection names a construct due2 does not support, which blocks that policy's migration.

**Old decisions.** "What did we decide on 3 March" must keep working through the migration. The alternatives:

- *Keep the predecessor's record read-only until its retention expires; a ledger entry may refer to a predecessor record by id.* Nothing is converted, and replay is claimed only for evaluations due2 made. **Start here.**
- *Import the predecessor's decisions as ledger cases.* Each imported case would carry an evaluation that due2 cannot replay, which weakens what the ledger guarantees.

Either way, the ledger has to record which engine produced each evaluation, beside the normaliser pins (§5 #5).

**What this repository holds.** It specifies due2's interfaces, the phases, and the rules above. The predecessor's own interfaces, and the field-by-field mapping onto due2's, belong with the deployment that runs the predecessor.

---

## 5. Open questions

| # | Question | Where | Issue |
|---|---|---|---|
| 1 | Policy selection: what `select` may use, how it is shown to over-select, per policy and per root atom, and what a request gets when a selected policy has no published corpus | §2.3 | #94, #105 |
| 2 | A hierarchy lookup that fails cannot be recorded, because `closure` has no status, and hierarchy is closed-world, so a missing classification makes a part `F` | §2.5 | #95 |
| 3 | Asking request parameters in order of importance: a status for a parameter not yet asked, or an evaluation of the draft outside the ledger | §3.1 | #96 |
| 4 | Inquiries: how the requests of one inquiry share questions, answers, and presentation | §2.6 | #97 |
| 5 | The ledger: the engine that produced each evaluation, references to predecessor records, where shadow results go, and safe retries | §1.2, §4 | #98 |
| 6 | What-if results: recorded, and where | §2.11 | #99 |

Already open elsewhere: the monitoring question (#6), the read limit `max_reads` (#34), re-evaluation triggers (`due2-architecture.md` §7), remedies in the trace (#61).
