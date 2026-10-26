# due2 — Platform

**Status:** Draft v0.14. Every section is **[O]**: a map of the components around the evaluator, not a build order. A paragraph marked **[D]** states a decision record. Where a section restates the specification, it cites it, and the specification's marker applies.
**Companions:** `due2-architecture.md` (what due2 is and why) · `due2-workflows.md` (the workflows and the data model this document builds on).

**Changes in v0.14** (2026-10-26, `decisions/0045`, `decisions/0046`): `decide` takes three inputs, and the connector registry, keyed by property and source, decides whose answers a case records (§1.4, §2.4). §1.3 tells apart the two relations named `evaluation`, and §2.3 drops the configured rule for violated obligations. Publication is a workflow of its own (§2.11). A case changes only by explicit calls, among them `record_facts`, `refresh`, `reevaluate`, and `reopen` (§2.6). Earlier changes are in `docs/archive/changes.md`.

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
| orchestrator | The case workflow (§2.6), one of the two components that call others (§1.2). This document calls it the orchestrator, so that the bare word "workflow" keeps the sense of W1–W3. The publication workflow, the other such component, is always named in full. |
| publication workflow | The other component that calls others: it lints, normalises, and publishes policies, and runs what-if checks (§2.11). |
| evaluation | The record of one `decide` call: the SOTW it read and the trace `decide` returned (`due2-workflows.md` §7.1). Its corpus and pins are its case's (§2.2). The act is a call to `decide`. §1.3 tells apart the two relations named `evaluation`. |
| engine | One deployment of the evaluator, named by implementation and version. The predecessor's evaluator is another engine (§2.6, §4). |
| normal path, fast path | Whether a call to the evaluator carries its corpus in full or only the corpus's digest (§1.3). |
| connector registry | The list, for each state property and world module, of the sources that answer it, each with the connector that asks it (§2.4). A source is whoever gives a state fact: a system or a person (`due2-workflows.md` §3.3). |
| connector | An adapter that fetches one kind of fact from an outside system, such as HR or a data catalog, for the SOTW services (§2.4). |
| registered source | A source that the connector registry lists for a state property or a world module. A case records answers only from registered sources (§1.4, §2.4). |
| inquiry | What a person asks in one sitting, such as "may I use these three datasets for this purpose". It holds one or more requests (§2.6). |
| draft request | A request whose parameters are still being gathered. It becomes a request when its case is created (§2.6). |
| predecessor | The decision system in service before due2, which due2 replaces gradually (§4). |
| route | One operation of the predecessor's interface, such as one REST endpoint, and the due2 call that replaces it (§4). |
| classification | A class of datasets in the catalog, such as `PII`. A dataset falls under a classification through hierarchy edges, and a policy may target the classification (§2.5). |

---

## 1. Principles **[O]**

### 1.1 The platform is the shell

`decide` is pure over its three inputs: corpus, request, and SOTW (`due2-workflows.md` §3.5). It never fetches, never waits, and never asks. Everything impure happens around it: finding the policies, fetching facts, asking people, recording answers. That keeps the evaluator replayable (`due2-workflows.md` §7), and it is why the evaluator is a component of its own (§2.1) that the case workflow calls with everything already gathered, rather than a service that fetches what it needs during evaluation.

### 1.2 Ports and adapters; deployment is configuration

Each component exposes a port (Cockburn, `references.md` §8). An in-process call, REST, and MCP are adapters over that one port. Whether two components share a process or talk over the network is a deployment setting, not a design change.

This works only if each port is designed for the remote case, with the in-process call as an optimisation of it:

- **Coarse calls.** One call per step of a use case, not one per object.
- **Immutable collections, by value.** Arguments are canonical collections (§1.3), never live object graphs.
- **Safe retries.** A caller that times out does not know whether its write landed, and retries. A retry must not record an event twice. How the ledger recognises a repeated write is open; it must not add concurrency machinery to the event relation, which `decisions/0008` declined (#98).
- **Explicit errors.** A call that fails returns `Error(cause)`, as a crashed evaluation does (`due2-workflows.md` §7). A remote call can also fail in transport, and the caller handles that the same way.

**Each component works in its own space.** Two components call others: the orchestrator (§2.6), which runs cases, and the publication workflow (§2.11), which publishes policies (`decisions/0046`). Each of the two fetches collections from the stores by id, passes them by value to the components that compute, and records what they return. Every other component answers from what the call carries and from the state it owns. The evaluator therefore receives all three of its inputs by value, so a replay with the same inputs is the same call as the original. The SOTW services and the catalog reach outside systems, which is their own space (§2.4, §2.5). The request GUI and the intelligent services call the orchestrator, and reach the other components only through it; an author's tools call the publication workflow. A component's log serves operations and is never a record: the ledger is the record (§2.2).

**One schema, several adapters.** The port schema is generated from the relations of `due2-workflows.md` §3 and written in JSON Schema 2020-12 (`schema/README.md`). The REST description, in OpenAPI 3.1, and the MCP tool definitions are both generated from it, so the adapters cannot drift apart: OpenAPI 3.1's Schema Object is a superset of JSON Schema 2020-12, and MCP states a tool's inputs and outputs in JSON Schema (`references.md` §8). A collection carries no JSON-LD `@context`, and every `Id` is a full IRI, never a prefixed name such as `ex:a1` (`due2-workflows.md` §2). Its id is the digest of its bytes (`decisions/0007`), and a context or a prefix would let one value be written in two byte forms, so two collections with one meaning would have two ids. A JSON-LD context for consumers who want linked data can be added as a view, because it does not change the bytes that are hashed.

**One process by default.** The components are modules of one deployable. A component moves to its own process when its runtime character requires it:

- pure and stateless: the evaluator and W1;
- stateful: the ledger and the policy store;
- effectful: the connectors and the catalog;
- long-running: the orchestrator;
- on demand, off the request path: the publication workflow.

### 1.3 Ids and values

Every collection, whether corpus, request, SOTW, or trace, is canonical JSON, serialised by JCS (RFC 8785) as `due2-workflows.md` §2 states, and its id is its digest (`decisions/0007`). Stores hold collections under their ids, and records refer to them by id. Between components, collections travel by value (§1.2). A cached collection can never be stale, because a changed collection has a different id. Versions and provenance largely follow from this (§2.10).

**Two relations are named `evaluation`.** The *trace's `evaluation` tuple* names the three input collections of one `decide` call, corpus, request, and SOTW, by id, and the evaluation id is its digest (`due2-workflows.md` §3.5). The *ledger's `evaluation` record* is an event of a case: its sequence number, the id of the SOTW it read, and the trace or the error `decide` returned (`due2-workflows.md` §7.1). The record holds the trace, and with it the tuple; the tuple names no case.

**The normal path and the fast path.** On the normal path, every call to the evaluator carries its corpus in full. The evaluator computes the corpus's digest itself and keeps the parsed and indexed corpus under it, so a repeated corpus is hashed again but not parsed or indexed again. This memo is derived state: the output is the same whether the corpus was held or not, and dropping the memo costs only time. The evaluator never takes the digest from the caller, because a wrong digest would file one corpus under another's id. On a fast path, the caller would send only the digest, and the evaluator would reply `not held` when it lacks the corpus. Every caller would then have to handle that reply, so the fast path is added only if the measurements of `ways-of-working.md` §10.4 (`decisions/0027` item 6) show that the transfer matters.

### 1.4 Who decides, and who may assert a fact

- **Only the evaluator decides.** No other component computes, approximates, or overrides a verdict. A rendering may select and order the reasons the trace holds, and never adds one (`due2-workflows.md` §3.7).
- **The connector registry decides whose facts count [D]** (`decisions/0045`). Each state fact is one source's answer, recorded with its source (`due2-workflows.md` §3.3). The orchestrator records an answer only from a source registered for its property (§2.4), and a person's answer only when it asked that person, so every answer a case holds counts, and the evaluator combines the answers of each property (`due2-workflows.md` §3.3, *Several sources*).
- **The requester states the request.** Request-source operands, such as purpose or record count, read the request (`due2-profiles.md` §3). The requester supplies them, and the profile's binding is what makes them the requester's to state.
- **The intelligent services assert nothing.** They choose and phrase questions, map free text onto request fields and catalog entries, and narrate a rendered explanation. The orchestrator asks a person for a state property only when the registry lists that person, or the person's role in the request, as a source for it, and records the answer with that person as its source. A fact a person volunteers unasked is not recorded (`decisions/0045`).

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
│ dataset →    │     │  record · decide · record · show       │     │ per registered   │
│ classes and  │     │  runs cases                            │     │ property, source │
│ policies     │     └──────────┬────────────────┬───────────┬┘     └──────────────────┘
└──────────────┘                │                │           │
                                │                │           │
  ┌────────────────────┐ ┌──────▼───────┐ ┌──────▼───────┐ ┌─▼──────────────┐
  │ publication        ├►│ policy store │ │ evaluator    │ │ ledger         │
  │ workflow: lint,    │ │ policies,    │ │ plan, decide │ │ case · event · │
  │ normalise, what-if,│ │ corpora,     │ │ pure         │ │ evaluation     │
  │ publish            │ │ profiles     │ │              │ │ append-only    │
  └─────────┬──────────┘ └──────────────┘ └──────────────┘ └────────────────┘
            │
  ┌─────────▼──────────┐
  │ normalisation (W1) │
  │ batch, once per    │
  │ policy version     │
  └────────────────────┘
```

Explanation (§2.9) is a component the orchestrator calls, as it calls the evaluator, and is not drawn. Versions and provenance (§2.10) are obligations on every store. The publication workflow also calls the evaluator and reads the ledger for its what-if checks (§2.11); those lines are not drawn either.

| § | Component | Inherits from |
|---|---|---|
| 2.1 | Evaluator | `plan` and `decide` (`due2-architecture.md` §2; `due2-workflows.md` §3.3, §5–§6) |
| 2.2 | Ledger | `due2-workflows.md` §7.1; `decisions/0008` |
| 2.3 | Policy store | `due2-workflows.md` §3.1 (corpus), §3.6 (lineage); `decisions/0007` |
| 2.4 | SOTW services | `due2-profiles.md` §3 (operand bindings); `due2-workflows.md` §3.3 (`fact`, `fact_value`) |
| 2.5 | Catalog | `due2-workflows.md` §3.3 (world `closure` modules) |
| 2.6 | Case workflow | `due2-workflows.md` §1, §3.3 (the shell loop); `due2-architecture.md` §7 (re-evaluation) |
| 2.7 | Intelligent services | Nothing: the component is new |
| 2.8 | Normalisation | `due2-workflows.md` §4 (W1); `due2-diagnostics.md` |
| 2.9 | Explanation | `due2-workflows.md` §3.7; `decisions/0010` |
| 2.10 | Versions and provenance | `due2-architecture.md` §7 (normaliser pins); `due2-workflows.md` §3.6 (lineage) |
| 2.11 | Publication workflow | `due2-workflows.md` §4 (W1, publishing); `due2-diagnostics.md` (W1's diagnostics) |

The interface sketches below use `name(arguments) -> result`. Types are those of `due2-workflows.md` §3. Every call can also return `Error(cause)` (§1.2), which the sketches leave out.

### 2.1 Evaluator

Answers one access question from its three inputs, and lists in advance what the answer can depend on. It owns no state: its memo of indexed corpora (§1.3) is derived and can be dropped.

```text
plan(corpus, request)                            -> Reads
decide(corpus, request, sotw)                    -> Trace
```

`Reads` and the rule that `decide` runs only once every planned read is in the case are `due2-workflows.md` §3.3. The verdict is one relation of the trace, and the explanation is the part of the trace reachable from it (`due2-workflows.md` §3.7).

All three inputs arrive by value, and the evaluator fetches nothing (§1.2). §1.3 gives the normal and fast paths for the corpus. Inside the call, the evaluator may skip atoms through an index it builds from the corpus, within the limits of `due2-workflows.md` §5.5: only roots that are certainly `F`, never an atom whose match turns on a `U` part, never a precondition of a live permission. §2.3 gives the same rule for choosing the corpus. The request-free question, which duties a party owes now, is a second function over the same corpus (`due2-architecture.md` §6.3, #6).

### 2.2 Ledger

Holds cases: one per request and the terms it is decided under (corpus and normaliser pins), with every fact, piece of evidence, activation, and evaluation recorded as an event, append-only (`due2-workflows.md` §7.1).

```text
create_case(request, corpus_id, pins)     -> case_id
append(case_id, event)                     -> seq
record_evaluation(case_id, evaluation)     -> seq            # the SOTW id and the trace `decide` returned (§2.6)
case(case_id)                              -> request, corpus, pins, events, evaluations
sotw(case_id, effective_at)                -> sotw_id        # the case's events as of effective_at, frozen
get(collection_id)                         -> collection     # a request, SOTW, or trace it holds
cases(latest_verdict?)                     -> case_ids       # for re-evaluation (§3.3)
owed(party, at)                            -> duty instances # the monitoring question, open (#6)
```

The orchestrator calls `decide`, which returns the whole trace, and records the evaluation: the SOTW id and the trace as returned, of which it builds no part (`decisions/0041`). The ledger only records it, and calls no other component (§1.2). Replay is therefore the orchestrator's (§2.6). The ledger never edits an event and never recomputes an earlier decision to answer an audit question: the earlier `evaluation` event is the answer.

### 2.3 Policy store

Holds authored policies, their corpora, profile modules with their operand bindings, and the vocabularies and concept schemes policies refer to. Every item is immutable. A collection is named by its digest (`decisions/0007`), and a policy version by an id minted when it is stored (`decisions/0038`). A policy's current version is a pointer to one of them.

```text
put_policy(document)                       -> policy_id, version
put_corpus(policy_id, normaliser_version, corpus, lineage) -> corpus_id | IdentityConflict  # W1's output (§2.8)
corpus(policy_ids, normaliser_version)     -> corpus_id | absent          # the union of these policies' corpora
lineage(policy_id, version, normaliser_version) -> lineage_id | absent  # due2-workflows.md §3.6
get(collection_id)                         -> collection
profiles()                                 -> profile modules
binding(property)                          -> operand binding             # due2-profiles.md §3
select(target, ancestors, action, parties) -> policy_ids                  # open (§5 #1)
```

The store never runs W1. Normalisation (§2.8) produces each corpus as a batch job when a policy version or a normaliser version is stored, and the publication workflow puts it here, which publishes it (§2.11). On the request path, the orchestrator finds the policies that may apply with `select`, and their corpus with `corpus`: the union of their published corpora, relation by relation, which needs no normalisation and has no conflicts (`due2-workflows.md` §4). It is absent when a selected policy has no published corpus for the normaliser version, and what the request gets then is open (§5 #1). The store keeps each union it returns, so an evaluation can pin it. The evaluator then skips atoms within that corpus (§2.1). The orchestrator does not run W1 on the request path (`decisions/0027` item 3).

**Publishing checks agreement.** `put_corpus` publishes one policy's corpus; `put_policy` only stores its document. For each node that a published corpus of the same normaliser version holds, it compares the new corpus with the published one up to the renaming of minted ids. If they agree, it renames the ids W1 minted for the node's parts to the published ones, in the corpus and in its lineage, so the node and its parts are one individual across policies (`decisions/0038`). If they do not, it refuses the corpus with `IdentityConflict`, naming the node and the policy that holds it. The refused policy is not published, and the published ones are unaffected (`due2-workflows.md` §4, *Several policies are one corpus*). Only the current version of each other published policy is compared, never an earlier version of the same policy. A conflict within a set of policies is a conflict between two of them, so every set of published policies agrees, and every union `corpus` returns is well-formed. Building the checker is #133.

**Offers are selected like any other policy.** A store holds offers as well as agreements, and a verdict over an offer says what its terms permit, not that it has been accepted (`due2-workflows.md` §6.4, `decisions/0031`). Accepting an offer, such as by signing a contract, is a separate step outside the evaluator.

**A replaced policy is never selected.** A policy with `dct:isReplacedBy` is void, and its replacement is the policy to process (ODRL IM §2.8). `select` never returns a policy that names a replacement, and returns the replacement wherever it may apply. W1 rejects a replaced policy that reaches it (`ReplacedPolicy`, `decisions/0033`), because W1 never dereferences an IRI and so cannot fetch the replacement itself (`odrl-compound-to-atomic-normalization.md` §3).

**Selection must over-select.** `decide` reads only the policies in its corpus, so choosing that corpus is part of the decision's soundness. Suppose policy A permits reading dataset D and policy B prohibits it. Over both, the verdict is `Deny`; over A alone, it is `Permit`. Prohibition monotonicity (L5, `due2-workflows.md` §8) says only that adding B cannot raise the verdict, not that a corpus may leave B out.

Including a policy that cannot match the request is safe, because root atoms that are certainly `F` leave the trace unchanged (L8, `due2-workflows.md` §8). The converse needs care. A policy's obligations are in force when one of its `Permit` or `Forbid` atoms *matches* the request on action, relation, and parties, whatever its constraints (`due2-workflows.md` §5.2). So a policy whose permission matches but whose constraint is certainly `F` still puts its obligations in force, and the trace reports each of them with its status, a violated one included (`due2-workflows.md` §6.1). A corpus that left the policy out would give the same verdict and a trace that omits them. Selection must therefore keep every policy with a `Permit` or `Forbid` atom whose match on action, target, and parties is not certainly `F`, and may skip a policy on those fields only, never on a constraint. This is the policy-level reading of the index rule of `due2-workflows.md` §5.5; #105 is to state the rule per root atom, with a property test. A catalog's attachment of a policy to a dataset helps find policies but is not the criterion: a policy whose target is a classification the dataset falls under applies whether or not anyone attached it.

### 2.4 SOTW services

Fetch the facts a plan names and return them in the form the SOTW records them: one answer per source, with its status and values (`due2-workflows.md` §3.3). One connector asks one source, for one state property or world module, or for a family of them.

```text
resolve(property, entities, at)            -> fact(source, status, values), with the source's version
edges(module, entities)                    -> per entity, the closure edges on the paths up from it, with the source's version
register(property | module, source, connector)
sources(property | module)                 -> registered sources, each with its connector
```

**The registry admits sources [D]** (`decisions/0045`). The connector registry is keyed by property and source: it lists, for each state property and world module, the sources registered for it, each with the connector that asks it. For a planned property, the orchestrator asks every registered source, and records a source that cannot be asked as `unresolved` (`due2-workflows.md` §3.3, *Several sources*). It records an answer only from a registered source, so every answer a case holds is admitted, and the evaluator reads no list of admitted sources. A person can be a registered source too, such as the requester for a property only the requester knows; the orchestrator then asks the person through the request GUI (§1.4).

Five rules from the specification bind every connector:

- **One hop.** "The requester's department" is one property, flattened by the connector. Computing values is the connector's job and never the evaluator's (`due2-profiles.md` §3).
- **Statuses are never collapsed.** `missing` means the source says no value exists. `unresolved` means the source could not be asked or did not answer. A connector that times out returns `unresolved`, never `missing`.
- **Answers, not extensions.** The case records the answer to the question asked, such as membership of one group, and, on its event, the version of the source it came from (`decisions/0044`). For a world module, one answer holds the edges on the paths up from one request entity, and a later answer for the entity replaces it (`decisions/0043`). The case never records the dataset the answer was computed from (`due2-workflows.md` §3.3).
- **The corpus decides what is needed.** A connector is needed for each property that the corpus's constraints read and that a profile binds to the state source. A profile binding that no policy reads needs none. A planned property with no registered source has no `fact`, and the evaluator reads it as `unresolved` (`due2-workflows.md` §5.4; §3.6).
- **The service keeps values current.** When a value it supplied changes in the world, the new one reaches the case as a new event, through an explicit call to the orchestrator: `record_facts`, which records answers the caller brings, or `refresh`, which asks the registered sources again (§2.6, `decisions/0046`). No one checks an answer's age, and a re-evaluation asks no source again (`decisions/0040`).

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

The orchestrator: it runs a case from the first question to the presented answer. It is one of the two components that call others; the other, the publication workflow, publishes policies (§1.2, §2.11). It fetches what each call needs, passes it by value, and records the result. It owns inquiries and draft requests. Cases belong to the ledger.

```text
open_inquiry(subject, action, datasets, at?)   -> inquiry_id, questions
answer(inquiry_id, answers)                    -> questions | outcomes
submit_evidence(case_id, evidence, key)        -> evaluation
record_facts(case_id, answers, key)            -> seq
refresh(case_id, key)                          -> seq
reevaluate(case_id, key)                       -> evaluation
reopen(case_id, key)                           -> case_id, evaluation
show(case_id, seq?)                            -> verdict, rendered explanation
replay(case_id, seq, engine)                   -> match | mismatch
```

`key` is the caller's idempotency key, on every call that records an event or opens a case: a retry of a call with the same key records nothing a second time (`decisions/0046`). How the ledger keeps keys is open (§5 #5). `submit_evidence` records the evidence and evaluates the case, because the person who submits it waits for the answer. `record_facts` and `refresh` only record, and return the sequence number of the last event they recorded, so a caller can record several changes before one `reevaluate`. `record_facts` refuses with `Error` an answer whose source is not registered for its property (§2.4). `show` renders the case's latest evaluation, or the one at `seq`, through the explanation service (§2.9).

**Inquiries.** A request has at most one target (`due2-workflows.md` §3.2), and each request has one case (`decisions/0008`). A person asking about three datasets therefore makes three requests, and the inquiry groups them. How the requests share questions and answers is open (§5 #4). In the simplest form, each request is asked and decided on its own, and the inquiry only groups the answers.

**Draft requests.** A case's request is fixed when its case is created, except for its `at`, which each evaluation moves to its own time (`due2-workflows.md` §3.2, §7.1). Request parameters, such as purpose, therefore have to be gathered before the case is created, while the request is a draft. State facts are gathered after, as events on the case. §3.1 walks through the sequence.

**A case changes only by explicit calls [D]** (`decisions/0046`). There is no subscription and no change feed. A changed value reaches a case when someone calls `record_facts` with it, as the answer of a registered source (§2.4): the SOTW service that holds it, say, or an operator, or calls `refresh`, which asks every source that a connector answers again for the case's planned state properties and world modules (§2.4). `refresh` prompts no person: a person's earlier answer stays in the case, and a changed one arrives through `record_facts`. Neither call checks an answer's age. `reevaluate` then calls `decide` over what the case holds, and asks no source (`decisions/0040`). A policy or normaliser change reaches an earlier request only through `reopen`, which runs §3.1 for the case's request without asking its parameters again: it describes the target and selects the corpus afresh (steps 2 and 3), so a policy attached since is included, takes the normaliser pins current at the call, plans, creates the new case (`create_case`, §2.2), fetches, and decides (steps 5 to 8), because a case fixes its terms (`due2-workflows.md` §7.1, `decisions/0038`). The new case starts without the earlier one's activations and evidence.

**Which cases, and when, is the caller's choice.** The platform computes no set of affected cases. The ledger lists cases by their latest verdict (`cases`, §2.2), so re-evaluating every pending case, which `due2-architecture.md` §7 starts with, is a loop of calls. That loop never revokes a `Permit`, because a decided case is not pending, so a revocation (§3.3) needs a decided case re-evaluated, or reopened after a policy change, as well. Which cases to reopen after a policy change is the judgement of whoever publishes it, informed by the what-if check (§2.11).

**Each evaluation asks at its own time.** The orchestrator builds its request from the case's, with `at` moved to the evaluation's `effective_at` when the case's `at` is earlier, so it never sends an access evaluation an `at` earlier than its `effective_at`. The latest evaluation is the case's current answer, and the newest case of a request gives the request's (`due2-workflows.md` §3.2, §7.1; `decisions/0030`).

**Replay.** To check a recorded evaluation, the orchestrator fetches the case's corpus and the evaluation's SOTW from the policy store and the ledger, builds the evaluation's request from the case's as above, calls `decide` with the three, and compares the digest of the new trace with the recorded one (`due2-workflows.md` §7). To the evaluator this is an ordinary call. The orchestrator chooses the `engine` that answers: a replay on the engine that made the evaluation checks the record, and a replay on the current engine checks for a regression. The first needs the ledger to record each evaluation's engine, which is open (§5 #5).

### 2.7 Intelligent services

An assistant, typically a language model, that serves the request GUI and drives the orchestrator through its MCP adapter.

- **It may:** find datasets from a description (catalog `search`, through the orchestrator); order questions by what decides the verdict (§3.1); phrase a question for its reader; map an answer onto a request field or a fact; narrate a rendered explanation (§2.9).
- **It may not:** call `decide` with facts it supplies; record a fact under any source other than the person who gave it; change a verdict or add a reason (§1.4).

Its useful work rests on what the trace already reports. For an `Indeterminate`, the trace names the atoms whose unknown parts decide the verdict (`verdict_basis` with role `unknown`, `decisions/0011`), the inputs those parts read (`unknown_part`), and the best and worst verdict still possible (`verdict_range`). For a `Pending`, the frontier lists the duties that would permit (`due2-workflows.md` §6.3). Asking about those first is the loop of §3.1, steps 8–10.

### 2.8 Normalisation

W1 behind a port: authored policies and their profiles in, a corpus or rejection diagnostics out (`due2-workflows.md` §4, `due2-diagnostics.md`). It runs once per policy version and normaliser version, never per request. It sits beside the policy store, off the request path: the publication workflow runs it as a batch job when a policy or normaliser version is published, and puts its corpus in the store (§2.3, §2.11).

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
- **What each evaluation pins:** its SOTW id; its corpus id and the normaliser versions in force are its case's (`due2-workflows.md` §7.1, `decisions/0042`).
- **Which authored rule each atom came from:** the lineage (`due2-workflows.md` §3.6). An evaluation's corpus names each policy and its version in `policy`, and its case pins the normaliser versions, so `lineage` finds the lineage of each policy it holds.
- **The obligation — retention:** replay needs every collection the trace's `evaluation` tuple names, the corpus, the request, and the SOTW (§1.3, `due2-workflows.md` §7). A store may therefore not delete a corpus or profile version that any retained evaluation references, nor the lineage of a policy in such a corpus.

### 2.11 Publication workflow

**Takes a policy from its author to the policy store [D]** (`decisions/0046`). It runs when an author publishes a policy version or a normaliser version is released, never on the request path. It calls normalisation, the policy store, and, for what-if checks, the evaluator and the ledger, and records nothing in the ledger.

```text
lint(document, profiles)                  -> diagnostics
what_if(document, case_ids)               -> verdict changes
publish(document)                         -> policy_id, version | rejections | IdentityConflict
```

- **Lint:** W1's diagnostics for a document, without storing it (`due2-diagnostics.md`).
- **Explain:** policy explanation (§2.9).
- **What-if:** before a version is published, call `decide` on the named cases, typically recent and pending ones, each over the corpus that `select` and `corpus` (§2.3) would give its request once the new version is published, and list the verdicts that would change, revocations first. `decide` is pure and each case holds its SOTW, so a what-if run reads the ledger and writes nothing to it. Whether what-if results are recorded at all is open (§5 #6).
- **Publish:** store the document (`put_policy`), normalise it (§2.8), and put its corpus (`put_corpus`), which checks agreement with the published policies (§2.3). A rejection or an `IdentityConflict` puts no corpus, so the stored document stays unpublished. A new normaliser version is published the same way, policy by policy.

Publishing changes no case: each case keeps its corpus (`due2-workflows.md` §7.1). The new version reaches an earlier request only when someone reopens its case (§2.6), and which cases to reopen is the judgement of whoever publishes it, informed by the what-if result.

---

## 3. Use cases **[O]**

### 3.1 Ask whether a dataset may be used

**The sequence.**

1. **Identify.** The person names datasets. The orchestrator finds them in the catalog (`search`) for the intelligent services.
2. **Describe.** For each dataset, the catalog returns its classification edges and attached policies (§2.5).
3. **Select.** The orchestrator asks the policy store for the corpus of every policy that may apply (§2.3), and fetches it.
4. **Draft.** The orchestrator drafts a request: the action, the dataset as target, the subject from authentication, and the time.
5. **Plan.** `plan` names everything the decision can read: request parameters, state properties, and hierarchy modules.
6. **Ask for parameters.** The planned request parameters are questions for the requester. When they are answered, the request is complete, and the case is created with the request, the corpus, and the normaliser pins (§2.2). `plan` runs again on the complete request, since what it names can depend on the request.
7. **Fetch.** The connectors of every registered source fetch each planned state property and hierarchy module (§2.4). Each answer is recorded as an event, one per source, including failures as `unresolved`.
8. **Decide.** Every planned read is now in the case, so `decide` runs and the evaluation is recorded.
9. **Show.** The verdict and its explanation are shown:
   - a `Permit` names the policies that permit, so over an offer it reads "this offer permits you to proceed";
   - a `Pending` shows its frontier as the duties that would permit;
   - an `Indeterminate` shows what is missing and its `verdict_range`.
10. **Iterate.** For an `Indeterminate`, the orchestrator asks for the inputs that decide it: from a person, where the registry lists that person as a source (§2.4), or from a connector again, up to a retry limit the deployment sets. Each answer is a new event, and step 8 runs again.

**Why the loop is safe.** Information monotonicity (L4, `due2-workflows.md` §8) concerns one world whose unknowns get answered. A value that fits can only replace an `Indeterminate`. An answer that turns out not to fit, or that says no value exists, can turn a definite verdict into `Indeterminate`, but never into another definite one. So within one world, asking more never replaces one definite verdict by a different one; at worst it makes the answer less certain. A fact that changes in the world while the loop runs is a different matter: it is a new fact, and the verdict can move either way (§3.3).

**Why the loop ends.** It asks only about planned reads. The plan is fixed by the corpus and the complete request (`due2-workflows.md` §3.3), so it is finite. The orchestrator asks a person for each read at most once, and retries a connector at most up to the retry limit. Once every planned read has an answer, the retries are spent, or the person declines to give more, there is nothing left to ask.

**Worked example.** The case `conformance/cases/rl2-geo-restriction`, translated from RL2, has one policy (`policy.ttl`) and four scenarios (`case.json`). The case fixes the policy, the facts, and the verdicts; the steps around them, and the registered sources, are this document's illustration.

- **Policy.** `ex:Customer` may `ex:access` `ex:Dataset` if `ex:jurisdiction` equals `"EU"`. The operand is bound to the state property `ex:requestJurisdiction`, so the value comes from a jurisdiction service, not from the requester.
- **Steps 4–8.** The plan names `ex:requestJurisdiction`, the only world value the policy reads. The service does not answer, the connector records the fact as `unresolved`, and `decide` runs. The case's expected output for scenario "jurisdiction unresolved" is, in excerpt (README § Verify runs every scenario of the case through clingo-i):

  ```json
  {"verdict": "Indeterminate",
   "verdict_basis": [{"ref": "ex:euAccess", "role": "unknown"}],
   "unknown_parts": [{"ref": "ex:euAccess", "input": "ex:requestJurisdiction", "status": "unresolved"}],
   "verdict_range": {"low": "NotApplicable", "high": "Permit"}}
  ```

- **Steps 9–10.** The screen says: undecided; at best permitted, at worst no rule applies; the one open question is the jurisdiction. If the registry lists only the jurisdiction service as a source of `ex:requestJurisdiction`, the orchestrator retries the connector and does not ask the customer, whose answer it would not record (§1.4). A retry that returns `"EU"` gives `Permit` (scenario "EU jurisdiction"), `"US"` gives `NotApplicable` ("non-EU jurisdiction"), and `"EU"` and `"US"` from two determinations give `Indeterminate` with status `conflict` ("jurisdiction in conflict"). A conflict is not resolved by asking again: someone has to correct the disagreeing sources.

**Asking parameters in order of importance [O].** Step 6 asks every planned request parameter before the case is created. Asking first the ones that decide the verdict would need a call to `decide` over the draft request. An absent request parameter reads as `missing`, which is an opaque `U` part. An opaque part only adds completions, so its cost is an `Indeterminate`, never a wrong definite verdict (`decisions/0016` § Why it is sound). A call over the draft is therefore sound, but its `verdict_range` can be wider than the facts warrant (§5 #3).

### 3.2 Fulfil a duty

A `Pending` verdict records the duty instances it awaits (the trace's `instance` and `alt_duty`). The person performs one, such as obtaining an approval. The evidence is submitted naming the grant it answers, the authored duty and the request's `reference` (`discharges_duty` and `discharges_reference`, `due2-workflows.md` §5.3), recorded as an event, and the case is evaluated again (`due2-architecture.md` §7, the case flow). Nothing in the earlier evaluation changes.

### 3.3 The world changes

A role changes or a dataset is reclassified. The change reaches each case that needs it through `record_facts` or `refresh`, and `reevaluate` then decides the case again. A policy is amended and published, and whoever published it reopens the cases it should reach, each as a new case over the new corpus (§2.6, §2.11). The ledger records each new verdict as a new evaluation. Re-evaluation can turn a `Permit` into a `Deny`, a revocation, and the operation is the same in both directions (`due2-architecture.md` §7).

### 3.4 Audit a past decision

"What did we decide on 3 March, and why?" The ledger returns that evaluation, the orchestrator replays it on the engine that made it, and `show` renders its trace (§2.6). Today's policy is not consulted (`due2-architecture.md` §7, two clocks).

### 3.5 Amend a policy

The author edits the policy, lints it through W1, reads its explanation, and runs a what-if over recent cases and pending ones. The publication workflow then publishes the new version (§2.11), and the cases the author chooses are reopened as in §3.3.

### 3.6 Add a source of facts

A new profile binds a new state property, or an existing property gains a source. Someone writes a connector and registers the source and its connector for the property (§2.4). Until a source is registered, a planned property has no `fact`, the evaluator reads it as `unresolved`, and the parts that read it are `U`, never `F`. Cases already open learn the new source's answers when someone calls `refresh` on them (§2.6).

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
