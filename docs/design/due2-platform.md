# due2 — Platform

**Status:** Draft v0.1 (2026-10-21). Every section is **[O]**: a map of the components around the evaluator, not a build order and not a decision. Where a section restates the specification, it cites it, and the specification's marker applies.
**Companions:** `due2-architecture.md` (what due2 is and why) · `due2-workflows.md` (the workflows and the data model this document builds on).

Markers as in the companions: **[D]** decided · **[O]** open, alternatives listed · **[F]** blocked on an external unknown.

---

## 0. What this is

due2's specification fixes three pure functions, `normalise`, `plan`, and `decide`, and a *shell* around them that fetches facts, keeps cases, and stores traces (`due2-architecture.md` §2). This document breaks that shell into components. For each component it gives:

- its responsibility;
- the data it owns;
- a first sketch of its interface;
- the section of the specification it inherits from.

It also gives the use cases the components serve (§3) and how they replace a running predecessor system (§4). The reader is anyone designing or reviewing a component, or deciding where a new capability belongs.

The specification governs. Where this document and `due2-workflows.md` disagree, the workflows document is right and this one has a defect. Nothing here reopens a **[D]** item. Where a component needs something the specification lacks, §5 names the gap and its issue.

**Vocabulary.** Terms the specification defines (request, SOTW, case, trace, frontier, plan) are listed in `due2-architecture.md` §0. This document adds:

| Term | Meaning |
|---|---|
| component | A unit with one responsibility and its own interface. It may run in its own process or share one (§1.2). |
| port | A component's interface, stated in the data model of `due2-workflows.md` §3, independent of transport (Cockburn's term, `references.md` §8). |
| adapter | A binding of a port to one transport: an in-process call, REST, or MCP. |
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

This works only if each port is designed for the remote case. In-process is then an optimisation of it; the reverse does not hold. Concretely:

- **Coarse calls.** One call per step of a use case, not one per object.
- **Ids and immutable collections.** Arguments are collection ids and canonical collections (§1.3), not live object graphs.
- **Safe retries.** A caller that times out does not know whether its write landed, and retries. A retry must not record an event twice. How the ledger recognises a repeated write is open; it must not add concurrency machinery to the event relation, which `decisions/0008` declined (#98).
- **Explicit errors.** A call that fails returns `Error(cause)`, as a crashed evaluation does (`due2-workflows.md` §7). A remote call can also fail in transport, and the caller handles that the same way.

A port designed in-process the other way, as fine-grained calls that assume shared memory, breaks the first time it crosses the network: chatty calls multiply latency, and a partial failure leaves half-written state.

**One schema, several adapters.** The port schema is derived once from the relations of `due2-workflows.md` §3. The REST description (OpenAPI) and the MCP tool definitions are both generated from it, so the adapters cannot drift apart.

**Start as one process.** The components are modules of one deployable at first. A component moves to its own process when its runtime character requires it:

- pure and stateless: the evaluator and W1;
- stateful: the ledger and the policy store;
- effectful: the connectors and the catalog;
- long-running: the case workflow.

### 1.3 Ids, not objects

Every collection, whether corpus, request, SOTW, config, or trace, is canonical JSON under JCS, and its id is its digest (`decisions/0007`). A component passes a stored collection by id. A draft request (§2.6) is not stored, so it travels by value. The receiver fetches the collection only if it doesn't hold it. A cached collection can never be stale, because a changed collection has a different id. Versions and provenance largely follow from this (§2.10).

### 1.4 Who decides, and who may assert a fact

- **Only the evaluator decides.** No other component computes, approximates, or overrides a verdict. A rendering may select and order the reasons the trace holds, and never adds one (`due2-workflows.md` §3.7).
- **The configuration decides whose facts count.** Each state fact carries an `attribution`, its source and observation time. `admit_source` and `admit_age` say which sources count for which property (`due2-workflows.md` §3.4). A value from a source not admitted for its property is treated as `missing`.
- **The requester states the request.** Request-source operands, such as purpose or record count, read the request (`due2-profiles.md` §3). The requester supplies them, and the profile's binding is what makes them the requester's to state.
- **The intelligent services assert nothing.** They choose and phrase questions, map free text onto request fields and catalog entries, and narrate a rendered explanation. A state fact a person gives through them is recorded with that person's identity as its `attribution` source. It counts only for properties whose `admit_source` lists that source. Otherwise it is treated as `missing` (`due2-workflows.md` §3.4), which is an opaque `U` part, so an inadmissible answer can widen the verdict range instead of narrowing it. The workflow therefore asks a person only for properties whose `admit_source` admits them.

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
┌──────────────┐     ┌──────────▼──────────────────────────┐     ┌──────────────────┐
│ catalog      │◄────┤  case workflow                      ├────►│ SOTW services    │
│ (external)   │     │  select · plan · ask · fetch ·       │     │ one connector    │
│ dataset →    │     │  record · decide · record · show     │     │ per bound        │
│ classes and  │     └──┬──────────────┬───────────────┬────┘     │ property         │
│ policies     │        │              │               │          └──────────────────┘
└──────────────┘        │              │               │
             ┌──────────▼───┐   ┌──────▼───────┐  ┌────▼──────────────────┐
             │ policy store │   │ evaluator    │  │ ledger                │
             │ policies,    │   │ plan, decide │  │ case · event ·        │
             │ corpora,     │   │ pure         │  │ evaluation            │
             │ profiles     │   └──────────────┘  │ append-only           │
             └──────▲───────┘                     └───────────────────────┘
                    │
     ┌──────────────┴──────────────────────────────────────────────┐
     │ authoring · normalisation (W1) · explanation · versions     │
     └─────────────────────────────────────────────────────────────┘
```

| § | Component | Inherits from | What is new |
|---|---|---|---|
| 2.1 | Evaluator | `plan` and `decide` (`due2-architecture.md` §2; `due2-workflows.md` §3.3, §5–§6) | The port only |
| 2.2 | Ledger | `due2-workflows.md` §7.1; `decisions/0008` | Queries; the monitoring question (#6) |
| 2.3 | Policy store | Corpus §3.1, lineage §3.6 (`due2-workflows.md`); `decisions/0007` | Storage, retrieval, selection |
| 2.4 | SOTW services | Operand bindings (`due2-profiles.md` §3); `fact` and `attribution` (`due2-workflows.md` §3.3) | The connector registry |
| 2.5 | Catalog | World `closure` modules (`due2-workflows.md` §3.3) | Classifications and attached policies |
| 2.6 | Case workflow | The shell loop (`due2-workflows.md` §1, §3.3); re-evaluation (`due2-architecture.md` §7) | Inquiries, draft requests, policy selection |
| 2.7 | Intelligent services | — | Everything |
| 2.8 | Normalisation | W1 (`due2-workflows.md` §4, `due2-diagnostics.md`) | The port only |
| 2.9 | Explanation | `due2-workflows.md` §3.7; `decisions/0010` | Rendering; policy explanation |
| 2.10 | Versions and provenance | Normaliser pins (`due2-architecture.md` §7), lineage (`due2-workflows.md` §3.6) | Retention |
| 2.11 | Authoring | W1 diagnostics | What-if replay |

The interface sketches below use `name(arguments) -> result`. Types are those of `due2-workflows.md` §3. Every call can also return `Error(cause)` (§1.2), which the sketches leave out.

### 2.1 Evaluator

Answers one access question from its four inputs, and lists in advance what the answer can depend on. It owns no state.

```text
plan(corpus_id, request)                         -> Reads
decide(corpus_id, request, sotw_id, config_id)   -> Trace
```

`Reads` and the rule that `decide` runs only once every planned read is in the case are `due2-workflows.md` §3.3. The verdict is one relation of the trace, and the explanation is the part of the trace reachable from it (`due2-workflows.md` §3.7). The request-free question, which duties a party owes now, is a second function over the same corpus (`due2-architecture.md` §6.3, #6).

### 2.2 Ledger

Holds cases: one per request, with every fact, piece of evidence, activation, and evaluation recorded as an event, append-only (`due2-workflows.md` §7.1).

```text
create_case(request)                       -> case_id
append(case_id, event)                     -> seq
record_evaluation(case_id, evaluation)     -> seq            # built by the case workflow (§2.6)
case(case_id)                              -> request, events, evaluations
sotw(case_id, effective_at)                -> sotw_id        # the case's events as of effective_at, frozen
replay(case_id, seq)                       -> match | mismatch
cases(latest_verdict?)                     -> case_ids       # for re-evaluation (§3.3)
owed(party, at)                            -> duty instances # the monitoring question, open (#6)
```

The case workflow calls `decide` and builds the `evaluation` (its ids, pins, and trace); the ledger only records it. `replay` is the one call through which the ledger uses the evaluator: it re-runs `decide` on the evaluation's pinned inputs and compares digests (`due2-workflows.md` §7). The ledger never edits an event and never recomputes an earlier decision to answer an audit question: the earlier `evaluation` event is the answer.

### 2.3 Policy store

Holds authored policies, their corpora, profile modules with their operand bindings, and the vocabularies and concept schemes policies refer to. Every item is immutable and named by its digest. A policy's current version is a pointer to one of them.

```text
put_policy(document)                       -> policy_id, version
corpus(policy_ids, normaliser)             -> corpus_id | diagnostics     # through W1 (§2.8)
get(collection_id)                         -> collection
profiles()                                 -> profile modules
binding(property)                          -> operand binding             # due2-profiles.md §3
select(target, ancestors, action, parties) -> policy_ids                  # open (§5 #1)
```

**Selection must over-select.** `decide` reads only the policies in its corpus, so choosing that corpus is part of the decision's soundness. A prohibition left out cannot eliminate a permission. For example, policy A permits reading dataset D and policy B prohibits it. Over both, the verdict is `Deny`; over A alone, it is `Permit`. Prohibition monotonicity (L5, `due2-workflows.md` §8) says only that adding B cannot raise the verdict. It does not protect a corpus that leaves B out.

Including a policy that cannot match the request is safe, for two reasons:

- Root atoms that are certainly `F` leave the trace unchanged (L8, `due2-workflows.md` §8).
- A policy's obligations are in force only if one of its `Permit` or `Forbid` atoms *matches* the request: action, relation, and parties, with constraints aside (`due2-workflows.md` §5.2).

The second reason cuts both ways. A policy whose permission matches the request but whose constraint is certainly `F` still puts its obligations in force, and under `violations = deny` a violated one acts as a prohibition (`due2-workflows.md` §6.4). So `select` must return every policy with a `Permit` or `Forbid` atom whose match on action, target, and parties is not certainly `F`. It may skip a policy only on those fields, never on a constraint. This is the rule for the corpus index (`due2-workflows.md` §5.5). A catalog's attachment of a policy to a dataset can help find policies, but it is not the criterion. A policy whose target is a classification the dataset falls under applies whether or not anyone attached it. This is the action-and-target index of `due2-architecture.md` §9, one level up.

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
- **The corpus decides what is needed.** A connector is needed for each property that the corpus's constraints read and that a profile binds to the state source. A profile binding that no policy reads needs none. Until a property's connector exists, a plan that names it records the property as `unresolved` (§3.6).

### 2.5 Catalog

The data catalog is external. The catalog connector answers two questions about an identified dataset:

```text
describe(dataset)                          -> classification edges, attached policy ids
search(text)                               -> datasets
```

**Classifications are targets.** A classification edge such as "dataset D is in class PII" is a hierarchy edge from the world: a `closure` tuple in a world module (`due2-workflows.md` §3.3). A policy whose target is `PII` then matches a request for `D`, because `D ⊑ PII`. The catalog's edges feed two steps:

- policy selection (§2.3);
- matching, as SOTW closure edges recorded in the case.

**The catalog is the most dangerous connector.** Hierarchy is closed-world: an edge that is not recorded does not hold, and the part that needs it is `F`, not `U` (`due2-workflows.md` §3.3). The one exception is concept-scheme membership: a concept with no `skos:inScheme` edge to its operand's schemes makes its constraint `U` (`due2-workflows.md` §3.3, `due2-profiles.md` §4). A dataset's classification is a target hierarchy edge, not a scheme membership, so the exception does not cover it. A catalog that fails to report a classification therefore does not make a prohibition on that classification unknown. It makes the prohibition certainly not apply. A fact lookup that fails is recorded as `unresolved`, but the specification gives no status to a hierarchy lookup that fails (§5 #2).

### 2.6 Case workflow

The orchestrator: it runs a use case from the first question to the presented answer, and is the only component that calls the others in sequence. It owns inquiries and draft requests. Cases belong to the ledger.

```text
open_inquiry(subject, action, datasets, at?)   -> inquiry_id, questions
answer(inquiry_id, answers)                    -> questions | outcomes
submit_evidence(case_id, evidence, key)        -> evaluation
reevaluate(case_id)                            -> evaluation
```

**Inquiries.** A request has at most one target (`due2-workflows.md` §3.2), and each request has one case (`decisions/0008`). A person asking about three datasets therefore makes three requests, and the inquiry groups them. How the requests share questions and answers is open (§5 #4). The starting point is the simplest form: an inquiry is one request and one case, and the workflow passes it straight through.

**Draft requests.** A case's request is fixed when its case is created (`due2-workflows.md` §7.1). Request parameters, such as purpose, therefore have to be gathered before the case is created, while the request is a draft. State facts are gathered after, as events on the case. §3.1 walks through the sequence.

**Re-evaluation.** When facts change, or a policy or normaliser version changes, the workflow re-evaluates the affected cases. Which cases count as affected is open. `due2-architecture.md` §7 starts with recomputing every pending case on any change. That alone never revokes a `Permit`, because a decided case is not pending, so revocation (§3.3) needs decided cases re-evaluated as well.

### 2.7 Intelligent services

An assistant, typically a language model, that serves the request GUI and drives the case workflow through its MCP adapter.

- **It may:** find datasets from a description (catalog `search`); order questions by what decides the verdict (§3.1); phrase a question for its reader; map an answer onto a request field or a fact; narrate a rendered explanation (§2.9).
- **It may not:** call `decide` with facts it supplies; record a fact under any source other than the person who gave it; change a verdict or add a reason (§1.4).

Its useful work rests on what the trace already reports. For an `Indeterminate`, the trace names:

- the atoms whose unknown parts decide the verdict (`verdict_basis` with role `unknown`, `decisions/0011`);
- the inputs those parts read (`unknown_part`);
- the best and worst verdict still possible (`verdict_range`).

For a `Pending`, the frontier lists the duties that would permit (`due2-workflows.md` §6.3). Asking first about whatever those name is the loop of §3.1, steps 8–10: evaluate, see what is missing, ask, evaluate again.

### 2.8 Normalisation

W1 behind a port: an authored policy and its profiles in, a corpus or rejection diagnostics out (`due2-workflows.md` §4, `due2-diagnostics.md`). It runs once per policy version and normaliser version, never per request.

```text
normalise(policy_id, profiles)            -> corpus_id, lineage_id, warnings | rejections
```

### 2.9 Explanation

**Decision explanation** is read from the trace, never computed alongside it (`due2-workflows.md` §3.7). The service derives the explanation and renders it for a reader: a page, prose, or a summary for the intelligent services to narrate. A rendering that needs something the trace lacks reveals a trace defect, which is fixed in the trace, not in the renderer.

**Policy explanation** answers what a policy means before any request is made. It is read from the corpus and its lineage: the atoms one authored rule produced, their constraints, and the warnings W1 accepted the policy with.

```text
explanation(case_id, seq)                 -> derivation         # due2-workflows.md §3.7
render(derivation, audience)              -> text
explain_policy(policy_id)                 -> atoms, constraints, lineage, warnings
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
- **What-if:** before a version is published, evaluate recent cases and pending ones against the new corpus and list the verdicts that would change, revocations first.

`decide` is pure and each case holds its SOTW, so a what-if run reads the ledger and writes nothing to it. Whether what-if results are recorded at all is open (§5 #6).

```text
lint(document, profiles)                  -> diagnostics
what_if(corpus_id, case_ids)              -> verdict changes
```

---

## 3. Use cases **[O]**

### 3.1 Ask whether a dataset may be used

**The sequence.**

1. **Identify.** The person names datasets. The intelligent services find them in the catalog (`search`).
2. **Describe.** For each dataset, the catalog returns its classification edges and attached policies (§2.5).
3. **Select.** The policy store returns every policy that may apply (§2.3) and its corpus.
4. **Draft.** The workflow drafts a request: the action, the dataset as target, the subject from authentication, and the time.
5. **Plan.** `plan` names everything the decision can read: request parameters, state properties, and hierarchy modules.
6. **Ask for parameters.** The planned request parameters are questions for the requester. When they are answered, the request is complete and the case is created. `plan` runs again on the complete request, since what it names can depend on the request.
7. **Fetch.** The connectors fetch every planned state property and hierarchy module. Each answer is recorded as an event, including failures as `unresolved`.
8. **Decide.** Every planned read is now in the case, so `decide` runs and the evaluation is recorded.
9. **Show.** The verdict and its explanation are shown:
   - a `Pending` shows its frontier as the duties that would permit;
   - an `Indeterminate` shows what is missing and its `verdict_range`.
10. **Iterate.** For an `Indeterminate`, the workflow asks for the inputs that decide it: from a person, where `admit_source` admits them, or from a connector again, up to a retry limit the deployment sets. Each answer is a new event, and step 8 runs again.

**Why the loop is safe.** Information monotonicity (L4, `due2-workflows.md` §8) concerns one world whose unknowns get answered. A value that fits can only replace an `Indeterminate`. An answer that turns out not to fit, or that says no value exists, can turn a definite verdict into `Indeterminate`, but never into another definite one. So within one world, asking more never replaces one definite verdict by a different one; at worst it makes the answer less certain. A fact that changes in the world while the loop runs is a different matter: it is a new fact, and the verdict can move either way (§3.3).

**Why the loop ends.** It asks only about planned reads. The plan is fixed by the corpus and the complete request (`due2-workflows.md` §3.3), so it is finite. Each read is asked of a person at most once and fetched from a connector at most up to the retry limit. Once every planned read has an answer, the retries are spent, or the person declines to give more, there is nothing left to ask.

**Worked example.** The case `conformance/cases/rl2-geo-restriction`, translated from RL2. Its policy is `policy.ttl` and its four scenarios are in `case.json`:

- **Policy.** `ex:Customer` may `ex:access` `ex:Dataset` if `ex:jurisdiction` equals `"EU"`. The operand `ex:jurisdiction` is bound to the state property `ex:requestJurisdiction`, so the value comes from a jurisdiction service, not from the requester.
- **Steps 4–5.** The customer asks to access the dataset. The only world value the policy reads is `ex:requestJurisdiction`, so the plan names it.
- **Steps 7–8.** The jurisdiction service does not answer. The connector records the fact as `unresolved`, and `decide` runs. Scenario "jurisdiction unresolved", run through clingo-i, gives:

  ```json
  {"verdict": "Indeterminate",
   "verdict_basis": [{"ref": "ex:euAccess", "role": "unknown"}],
   "unknown_parts": [{"ref": "ex:euAccess", "input": "ex:requestJurisdiction", "status": "unresolved"}],
   "verdict_range": {"low": "NotApplicable", "high": "Permit"}}
  ```

- **Step 9.** The screen says: undecided; at best permitted, at worst no rule applies; the one open question is the jurisdiction.
- **Step 10.** Suppose `admit_source` lists only the jurisdiction service for this property. The workflow then retries the connector and does not ask the customer, whose answer would not count (§1.4). Three outcomes are possible:

  | The service returns | Scenario | Verdict |
  |---|---|---|
  | `"EU"` | "EU jurisdiction" | `Permit` |
  | `"US"` | "non-EU jurisdiction" | `NotApplicable` |
  | `"EU"` and `"US"` from two determinations | "jurisdiction in conflict" | `Indeterminate`, with status `conflict` |

  A conflict is not resolved by asking again. Someone has to correct the disagreeing sources.

The case asserts each scenario's verdict, and the output above for the unresolved and conflict scenarios. The corpus run through clingo-i (README § Verify) checks them.

**Asking parameters in order of importance [O].** Step 6 asks every planned request parameter before the case is created. Asking first the ones that decide the verdict would need an evaluation of the draft request. An absent request parameter reads as `missing`, which is an opaque `U` part (`decisions/0016`). An evaluation over the draft is therefore sound, but its `verdict_range` can be wider than the facts warrant (§5 #3).

### 3.2 Fulfil a duty

A `Pending` verdict records the duty instances it awaits (the trace's `instance` and `alt_duty`). The person performs one, such as obtaining an approval. The evidence is submitted naming the instance it answers (`discharges`), recorded as an event, and the case is evaluated again (`due2-architecture.md` §7, the case flow). Nothing in the earlier evaluation changes.

### 3.3 The world changes

A role changes, a dataset is reclassified, or a policy is amended. The workflow re-evaluates the affected cases (§2.6), and the ledger records each new verdict as a new evaluation. Re-evaluation can turn a `Permit` into a `Deny`, a revocation, and the operation is the same in both directions (`due2-architecture.md` §7).

### 3.4 Audit a past decision

"What did we decide on 3 March, and why?" The ledger returns that evaluation, replay confirms its trace, and the explanation service renders it. Today's policy is not consulted (`due2-architecture.md` §7, two clocks).

### 3.5 Amend a policy

The author edits the policy, lints it through W1, reads its explanation, and runs a what-if over recent cases and pending ones (§2.11). Publishing stores a new version. Re-evaluation of affected cases follows as in §3.3.

### 3.6 Add a source of facts

A new profile binds a new state property, or an existing property gains a source. Someone writes a connector, registers it for the property, and lists the source in `admit_source`. Until the connector exists, a plan that names the property records it as `unresolved`, and the parts that read it are `U`, never `F`.

### 3.7 What does a party owe now

Ledger management needs the duties a party owes across cases, independent of any request: the monitoring question of `due2-architecture.md` §6.3, open as #6.

---

## 4. Migration **[O]**

due2 replaces a predecessor that is in service. A wholesale cut-over is not possible, so the replacement is gradual: the *strangler fig* pattern (Fowler, `references.md` §8). New interfaces grow around the old system, take over one route at a time, and the old system is retired when no route uses it.

**Interface migration and engine migration are separate.** The predecessor's evaluator need not share due2's semantics: in particular, how it treats unknown data, and whether it reports what due2's trace reports. A due2 interface in front of the predecessor is therefore a facade over different semantics. That creates two risks:

- The facade lends the predecessor's answers the credibility of due2's contract.
- When the engine behind the facade is later swapped, verdicts change behind an unchanged interface: a behaviour change presented as a refactoring.

Behind each route, the engine is chosen per route: a *branch by abstraction* (Fowler, `references.md` §8), where due2's interface is the abstraction and the predecessor and due2 are its two implementations. Each route moves through four phases, and its callers can see which phase it is in:

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

**Order.** Routes that carry no semantics move first:

1. catalog lookup;
2. fact connectors;
3. the policy store.

Evaluation moves last, through the shadow phase. Normalising the predecessor's policies through W1 early is a cheap measurement: each rejection names a construct due2 does not support, which is a per-policy blocker to migration.

**Old decisions.** "What did we decide on 3 March" must keep working through the migration. The alternatives:

- *Keep the predecessor's record read-only until its retention expires; a ledger entry may refer to a predecessor record by id.* Nothing is converted, and replay is claimed only for evaluations due2 made. **Start here.**
- *Import the predecessor's decisions as ledger cases.* Each imported case would carry an evaluation that due2 cannot replay, which weakens what the ledger guarantees.

Either way, the ledger has to record which engine produced each evaluation, beside the normaliser pins (§5 #5).

**What this repository holds.** It specifies due2's interfaces, the phases, and the rules above. The predecessor's own interfaces, and the field-by-field mapping onto due2's, belong with the deployment that runs the predecessor.

---

## 5. Open questions

| # | Question | Where | Issue |
|---|---|---|---|
| 1 | Policy selection: what may `select` use, and how is it shown to over-select? | §2.3 | #94 |
| 2 | A hierarchy lookup that fails has no status, and hierarchy is closed-world, so a missing classification makes a part `F` | §2.5 | #95 |
| 3 | Asking request parameters in order of importance: a status for a parameter not yet asked, or an evaluation of the draft outside the ledger | §3.1 | #96 |
| 4 | Inquiries: how the requests of one inquiry share questions, answers, and presentation | §2.6 | #97 |
| 5 | The ledger: the engine that produced each evaluation, references to predecessor records, where shadow results go, and safe retries | §1.2, §4 | #98 |
| 6 | What-if results: recorded, and where | §2.11 | #99 |

Already open elsewhere: the monitoring question (#6), the read limit `max_reads` (#34), re-evaluation triggers (`due2-architecture.md` §7), remedies in the trace (#61).
