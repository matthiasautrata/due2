# due2 — Workflows and Reference Data Model

**Status:** Draft v0.44
**Companions:** `due2-architecture.md` (what due2 is and why) · `odrl-compound-to-atomic-normalization.md` (W1 stage 1, normative) · `due2-diagnostics.md` (every W1 diagnostic) · `ways-of-working.md` (how it is built).

**Changes in v0.44** (2026-10-25, `decisions/0032` amendment, #121): a duty atom's id identifies what it asks for, by stage 1's construction extended with what stage 2 adds (§3.1, §4), and replaces `binding_key`, which is dropped. A `member` instance is its duty atom; W2 mints an instance id from the atom's id with the request subject when the subject is the performer, the `reference` for a `grant` instance, and the occurrence (§5.3). `instance_key` is an `Id` (§3.3, §3.5). Earlier changes are in `docs/archive/changes.md`.

Markers as in the companions: **[D]** decided · **[O]** open, alternatives listed · **[F]** blocked on an external unknown.

This document fixes *what* each workflow consumes and produces and what it must preserve. It fixes no algorithm, storage engine, wire format, or language. Any implementation whose outputs satisfy §3–§8 on the conformance suite conforms.

---

## 1. Three workflows and a boundary **[D]**

```text
                     authored ODRL policies
                               │
   W1  Normalise               │      offline · per policy version · pure
                               ▼
                    Corpus  (atoms · edges · constraints)
                               │
   Request ──────────┐         │         ┌────────── SOTW (frozen)
                     ▼         ▼         ▼
   W2  Evaluate                map: one truth value per atom · pure
                               │
                               ▼
                    Findings  (truth · basis · reads)
                               │
   W3  Resolve                 fold: findings → verdict · pure
                               │
                               ▼
         Permit | Deny | Pending(frontier) | NotApplicable | Indeterminate
```

- **W1 — Normalise.** Turns authored policies into a flat corpus of atoms. Runs once per policy version. Every semantically interesting rewrite happens here (`due2-architecture.md` §2, §4).
- **W2 — Evaluate.** Given a request and a frozen SOTW, gives every relevant atom a three-valued truth value and the parts that determined it. A *map*: an atom's finding depends on that atom, the request, the SOTW, and the configuration — **never on another atom's finding**.
- **W3 — Resolve.** Folds the findings into one verdict: forms candidates, applies conflict strategies, collapses and orders duty alternatives, derives the verdict. Reads the corpus and the findings — **never the request or the SOTW**.

The two *never* clauses are the boundaries. They make W2 parallel and indexable, and W3 testable without a world.

**The boundary that is not a workflow.** Assembling and freezing the SOTW is impure — it fetches, retries, waits — and sits outside all three workflows. W2 reports which state properties it read (§5.4); those with no fact in the SOTW are the shell's cue to resolve them, record the answers in the case, and run W2–W3 again. That loop is orchestration, not semantics. By L3 (§8) it can change a verdict only by supplying missing information.

**One question here, two in the architecture.** `due2-architecture.md` §6.3 separates the access question (*may this request proceed?*) from the monitoring question (*what does this party owe now?*). Both consume W1's corpus and reuse W2's matching, constraint, and fulfilment machinery. They differ in the predicate W2 applies to root atoms and in the reduction W3 performs. This document specifies the access question. Monitoring is **[O]** (§9).

---

## 2. Conventions **[D]**

**Relations.** All data is held as collections of tuples. Each relation declares a key, written before `|`; set semantics apply to the key only. A relation written without `|` is keyed by all of its fields; one with an empty key holds exactly one tuple. Optional fields are written `field?`.

**Identity.** Occurrence identity lives in ids. Two tuples with equal content and different ids never merge — the property a naïve set-of-tuples model loses (`due2-architecture.md` §3.1).

**Collections.** Data comes in five collections — Corpus, Request, SOTW, Config, Trace. Each is identified by the digest of its canonical form, and tuples inside a collection do not repeat its id.

**Value types.**

| Type | Meaning |
|---|---|
| `Id` | IRI, compared by equality only. Generated ids are UUID IRIs (`odrl-compound-to-atomic-normalization.md` §5). |
| `Term` | An `Id`, or a literal `(lexical, datatype[, language])`. Exact numbers are lexical forms with a numeric datatype; there is no floating-point domain. |
| `Instant` | A literal of datatype `xsd:dateTime` with a timezone (`decisions/0024`). |
| `Truth` | `T`, `F`, `U` — Kleene strong three-valued logic. |
| `Enum` | A closed set of strings, listed in the field's row of §3 or in the section that row cites. |
| `Flag` | `true` or `false`. |
| `Count` | An integer within ±2^53. |
| `Digest` | `sha256:` followed by 64 lowercase hex digits: the SHA-256 of the bytes that the field's row names, written as a collection id is (below). The bytes behind `discharges` and `alt_id` are open (#107). |
| `String` | Text that is neither an IRI nor a literal, such as an RFC 5545 RRULE. |

**Canonical form.** Each collection has exactly one canonical serialisation, and its digest is the collection id. **[D]** (`decisions/0007`):

- **Encoding.** A collection is a JSON object keyed by relation name, serialised by RFC 8785 (JCS) to UTF-8. Each value is the relation's tuples, as a JSON array; a relation with no tuples is omitted, so a collection with no tuples is `{}`. A tuple is a JSON object keyed by field name; absent optional fields are omitted. Relation and field names are ASCII, so JCS orders them by code point.
- **Order.** Within a relation, tuples are sorted by key, field by field in declaration order, each field by Unicode code-point order of its serialised value. A relation with an empty key holds one tuple.
- **Values.** An `Id`, `Truth`, `Enum`, `Digest`, or `String` is a JSON string. A literal is the object `{"v": lexical, "t": datatype}` plus `"l": language` when present; an `Id` is never an object, so the two cannot collide. A number is never a JSON number — it is a literal with a numeric datatype. A `Count` is a JSON integer within ±2^53, and a `Flag` a JSON boolean. No floating point.
- **Digest.** The collection id is `sha256:` followed by the lowercase hex SHA-256 of the canonical bytes.

Canonical N-Quads remain the artifact of W1 stage 1, which carries a graph (`odrl-compound-to-atomic-normalization.md` §4); nothing downstream of stage 2 reads them.

---

## 3. Reference data model

Each relation is written as §2 declares it. A field is an `Id` unless a value type of §2 follows its name, as in `version: Digest`.

### 3.1 Corpus — output of W1

```text
policy            (policy_id | conflict: Enum, version: Digest)
policy_profile    (policy_id, profile)
atom              (atom_id | effect: Enum, action, relation?, relation_value?, policy_id, source_rule, priority?: Count)
atom_party        (atom_id, function | party)
constraint        (constraint_id | atom_id, clause?: Count, scope: Enum, left_operand, operator, datatype, unit?)
constraint_value  (constraint_id, value: Term)
edge              (parent_id, child_id)
root              (atom_id)
duty              (atom_id | source_duty, scope: Enum, deadline?: Term, recurrence?: String)
closure           (relation, narrower, broader)
diagnostic        (policy_id, code: Enum, ref)
```

| Field | Meaning |
|---|---|
| `policy.conflict` | `Enum {prohibit, perm, invalid}` — the source policy's ODRL conflict strategy. An absent term takes a selected profile's declared default first, then `invalid` (`odrl-compound-to-atomic-normalization.md` §3); W1 makes the result explicit. The policy's class (Set, Offer, Agreement, or a profile's subclass of one) is not kept: W1 stage 1 carries it (`odrl-compound-to-atomic-normalization.md` §4), and no workflow reads it (`decisions/0031`). |
| `policy.version` | The digest of the authored policy graph: `sha256:` followed by its `source_digest`, the SHA-256 of its canonical N-Quads (`odrl-compound-to-atomic-normalization.md` §5.2). Versions are told apart by content, never by a number that has to be ordered. |
| `policy_profile` | Each profile the policy names with `odrl:profile`, one tuple per IRI. A policy may name none, or several. |
| `atom.effect` | `Enum {Permit, Forbid, Oblige}` — one required field (`due2-architecture.md` §3). |
| `atom.action` | The atom's single action, unrefined. Refinements are constraints with scope `action`. |
| `atom.relation`, `relation_value` | At most one relation, `odrl:target` or `odrl:output`, and its value. |
| `atom.policy_id`, `source_rule` | Required provenance. `policy_id` drives the per-source conflict fold in W3; `source_rule` drives explanation. Full lineage is a separate collection (§3.6). |
| `atom.priority` | Used only by a priority-based cross-policy combination (§6.2). |
| `atom_party` | At most one party per function predicate per atom: `assignee`, `assigner`, `informedParty`, … |
| `constraint.scope` | `Enum {rule, action, relation, party:<function>}` — what the constraint refines. An action refinement is scope `action` on *this* atom. It never attaches to the action vocabulary term globally. |
| `constraint` | Conjunctive per atom, except within a duty (`constraint.clause`). W1 has made each disjunct of a `Permit` or `Forbid` atom's constraint an atom of its own (§4). |
| `constraint.clause` | Present on every constraint of an `Oblige` atom, absent on every other. A duty stays one atom, and its condition is kept in clauses: the constraints with one `clause` number form a conjunction, all of one kind, guard or witness condition, and a kind's value is the Kleene disjunction of its clauses (§5.2, §5.3). **[D]** (`decisions/0028`) |
| `constraint_value` | Right-operand values: one tuple for a scalar, several for a set operand, whether the policy writes it as an RDF list or as repeated values (`due2-profiles.md` §4). |
| `edge` | Parent atom → child duty atom. |
| `root` | The atoms that root an Atomic Policy in W1 stage 1: every `Permit` and `Forbid` atom, and every policy-level obligation. Stored, because it is not derivable: one named duty can be both an obligation of its policy and the precondition of a permission, so a root can also be the child of an edge. |
| `closure` | Direct hierarchy edges declared in the policy and its profile modules — `odrl:includedIn` between actions, typed `odrl:partOf` between assets or parties and their collections, `rdfs:subClassOf`, and `rdf:type` edges — those that type collections and those of individuals an `isA` constraint can compare. Between concepts there are two relations. `skos:broader` is the hierarchy, and a `skos:narrower` triple is recorded as the inverse `skos:broader` edge. `skos:inScheme` relates a concept to each scheme it is in, whether the input states that as `skos:inScheme`, `skos:topConceptOf`, or `skos:hasTopConcept` (`due2-profiles.md` §6). ODRL's own action hierarchy is one such module (`profiles/odrl-actions.ttl`). |
| `duty` | For every `Oblige` atom: the authored duty it instantiates, and its instance scope `Enum {member, grant}`. Scope defaults to `member`. W2 derives the duty instance from the atom (§5.3). |
| `duty.atom_id` | The duty atom's id identifies what it asks for. Stage 1 gives each rule it emits an id: the authored duty's own identity, or for a duty it expands, `atomic_rule_uid`, from the source duty's identity and the selected action, relation value, and parties (`odrl-compound-to-atomic-normalization.md` §5.1, §5.2). When stage 2 adds inherited party roles or parameter values (§4), the atom's id is `H(frame(namespace, "duty-atom", rule_uid, additions))`, in that document's notation (§5.2 there): `rule_uid` is stage 1's id, and `additions` is a run of fields, `frame(p, term(v))` for each party function or parameter `p` that stage 2 binds to the value `v`, sorted by unsigned byte order as `local_digest` sorts its pairs. Otherwise the atom keeps stage 1's id. Nothing else enters it, not the parent or the policy, so a named duty bound identically in two places is one atom. `rule_uid` is framed as stage 1 frames an identity, a UUID IRI as its raw bytes and any other IRI as UTF-8. **[D]** (`decisions/0032`, amendment of 2026-10-25) |
| `duty.deadline` | The authored duty's timing, projected by W1 stage 2 onto every atom it instantiates: an `xsd:dateTime` term with a timezone (absolute) or an `xsd:duration` term (relative to the instance's activation). W2 resolves it per instance (§5.3). |
| `duty.recurrence` | An RFC 5545 RRULE string; the duty is owed once per occurrence. W2 derives the instances (§5.3). |
| `diagnostic` | A warning W1 accepted the policy with: its code (`due2-diagnostics.md` §3) and the node it is about. Only warnings appear, because an error leaves no corpus (§4). W2 and W3 never read it; it is in the corpus so that the corpus digest, and with it the evaluation id, records the reading the policy was normalised under. |

Derived, not stored:

- **guard / witness condition** of a duty's constraint, from its bindings (§5.2).
- **role(d)** of a child follows from its parent's effect: `Permit` → precondition, `Forbid` → remedy, `Oblige` → consequence (`due2-architecture.md` §3).

Invariants, established by W1 and trusted downstream: `edge` is acyclic; every child is an `Oblige` atom; every `Permit` and `Forbid` atom is a root; in every corpus tuple, a `policy_id` names a `policy`, an `atom_id`, `parent_id`, or `child_id` names an `atom`, and a `constraint_id` names a `constraint`; an atom has `relation_value` exactly when it has `relation`; `Permit` and `Forbid` atoms carry `relation = odrl:target`.

### 3.2 Request

```text
request        (| reference?: String, action, target?, at: Instant)
request_party  (function | party)
request_param  (name | value: Term)
```

`reference` is the caller's identifier for the request; it also identifies grant-scoped duty instances (§5.3). `at` is the instant of the proposed action, an `xsd:dateTime` with a timezone — validity time, what ODRL's `dateTime` constrains. `target` may be absent — a request for an action on no named asset; every relation part is then `U` (§5.2), never `F`. The party with `function = assignee` is the subject — the party seeking to act. A request may name other parties, such as a recipient, under other function predicates. `request_param` carries the values of the normalised request that request-source operands read (`due2-profiles.md` §3), keyed by property IRI: purpose, record count, and so on. Nothing else is visible — no credentials, headers, or session state unless a profile exposes them here.

**`at` across a case's evaluations [D]** (`decisions/0030`). Each evaluation of a case names the request it ran with (§7.1). That request is the case's request, with `at` moved to the evaluation's `effective_at` when the case's `at` is earlier. A later `at`, as for an action proposed for a future date, is kept. Every other field is unchanged, so `reference`, and with it every grant-scoped instance (§5.3), carries over. The orchestrator (`due2-platform.md` §2.6) builds every access evaluation's request this way, so its `at` is never earlier than its `effective_at`: an action can no longer be taken at an instant that has passed. The evaluator does not compare the two: given an earlier `at`, it answers for that instant. So a payment made after a time window has closed cannot fulfil the window's permission at a later re-evaluation, while a payment made in time and recorded late still counts (`due2-reevaluation-moves-at`).

### 3.3 SOTW

```text
sotw              (| effective_at: Instant)
fact              (property | status: Enum)
fact_value        (property, value: Term)
attribution       (property, source | observed_at: Instant)
evidence          (evidence_id | occurred_at: Instant, actor, action, object?, issuer?, discharges?: Digest)
evidence_param    (evidence_id, name | value: Term)
activation        (instance_key: Id | at: Instant)
closure           (module, relation, narrower, broader)
```

| Relation | Meaning |
|---|---|
| `sotw.effective_at` | The instant at which the world is observed, an `xsd:dateTime` with a timezone — decision time. Evidence counts only if it occurred no later. |
| `fact` | One property of the normalised world-state node, which state-source operands read (`due2-profiles.md` §3), and its `status`: `Enum {resolved, missing, invalid, conflict, unresolved}`, never collapsed. *Missing*: the source says no value exists. *Unresolved*: the source could not be asked or did not answer. Whoever assembles the SOTW flattens onto this node everything the policies read — "the requester's department" becomes one property — so computing values is the assembler's job, never W2's. |
| `fact_value` | Exactly one value when `resolved` — for a set-valued operand, its members, of which there may be none — two or more when `conflict`, none otherwise. |
| `evidence` | A record that an action was performed: when, by whom, which action, on what, and who attests it (`issuer`). Approvals, payments, notifications. `discharges` optionally names the grant the evidence was submitted against, the digest of an authored duty and a request's `reference` (§5.3). Fulfilment is derived from evidence and never stored as a flag. Signatures and provenance are verified before the SOTW is frozen; W2 only compares `issuer` against configuration (§3.4). |
| `evidence_param` | Parameters of the performed action — an amount, a recipient — the counterpart of `request_param` for a proposed action. Read only by witness-source operands (`due2-profiles.md` §3). |
| `activation` | When a duty instance was first owed. Derived, not observed: the evaluation that first finds the instance owed records it in the case (`due2-profiles.md` §7). It anchors relative deadlines and recurrence occurrences (§5.3). |
| `closure` | Direct hierarchy edges from the world rather than from policies — current team membership, say — in a named, versioned module. W2 uses the transitive closure of these together with the corpus's `closure`: `a ⊑ b` holds when `a = b` or a chain of edges leads from `a` to `b`. Closure is closed-world over the declared edges: an edge that is not there does not hold, so the part is `F`, never `U`. Scheme membership is the exception: a request concept with no `skos:inScheme` edge to any of its operand's schemes is out of scheme, and its constraint is `U`, not `F` (`due2-profiles.md` §4). Only edges on paths up from the request's own entities — its parties, its target, the individuals `isA` compares, the concepts a concept-scheme operand compares — can decide a part, so only those, and those concepts' scheme memberships, are recorded (below). |

**The SOTW is the case's snapshot [D].** An evaluation reads only what its case has recorded: the part of the world the case cares about, as of `effective_at`. Every fact, piece of evidence, and activation is an event on the case, carrying the time it held in the world and the time it was recorded (§7). Its flattened properties describe one request's subject and target, so a SOTW is not reused for a request with a different subject or target.

**Plan, then evaluate [D].** W2 never asks for anything. Every value it can consult is named by an operand binding (`due2-profiles.md` §3) or by a hierarchy comparison in the corpus, so a pure sweep lists them before anything is fetched:

```text
plan : Corpus × Request → Reads
```

`Reads` holds each state property a state-source binding names, each request parameter a request-source binding names, and each world module the corpus's hierarchy comparisons use, with the request entities whose edges it needs. The shell fetches what the case lacks, records the answers, and calls W2 only once every planned item is in the case. A lookup that fails is recorded as `unresolved`, and one that finds no value as `missing`, so "never looked up" cannot reach W2. W2's `read` is always within the plan; a read outside it is a defect. Evidence is not planned: it reaches the case when it is submitted, and evidence the case does not hold is not yet performed (§5.3).

**Answers, not extensions [D].** The case records the answer to the question an evaluation asks — a property's value, the edges above an entity — never the dataset the source computed it from. Membership of a group with a billion members is one fact. A source that can only answer in bulk is queried by the shell, which records the answer and the version of the source it came from, as the ledger pins normaliser versions (`due2-architecture.md` §7); the bulk data is a cache, not part of the case. A positive hierarchy answer may carry its path as justification; a negative one has none shorter than the closure, and needs none. Several cases may read the same fact: each records it as it read it, and storage may share it.

**Read limit [O].** The plan's size is fixed by the corpus and the request — the bound properties, plus the edges above the request's entities — and is known before any fetch, as W1's limits are known before expansion (`due2-architecture.md` §4). A shell limit, `max_reads`, bounds it. What exceeding it yields is open: refuse the request before a case is created, or create the case and evaluate with the excess `unresolved`, so those parts are `U` (§9 #9, issue #34).

An evaluation's SOTW is frozen once W2 runs; a fact that changes later is a new event, which the next evaluation reads (§7.1). Two sources that disagree about the same fact at the same time are a `conflict`.

### 3.4 Config

```text
config        (| combination: Enum, violations: Enum, max_mixed: Count, max_frontier_vars: Count)
signer        (source_duty, issuer)
admit_source  (property, source)
admit_age     (property | max_age: Term)
```

Parameters that are not policy content. `combination` is the cross-policy strategy, `Enum {prohibit-overrides}`; other strategies are open (§6.2). `max_mixed` and `max_frontier_vars` bound W3's exact computations (§6.4); the caller sets each, 8 unless it has reason to choose otherwise. They are config, not constants of the evaluator, because they change the trace: L1 (§8) requires the same trace bytes from the same evaluation, and an evaluation is its four input collection ids (§3.5), `config_id` among them. A declared preference among frontier alternatives (§6.3) would be a config field too; its form is open (#5). `signer` is the admissibility record for evidence. When a duty has `signer` entries, only evidence whose `issuer` is listed counts for it, and evidence without an issuer counts for nothing. A duty with no entries accepts any issuer (RL2's `spec/RL2_Model.md` §4.4). `violations` is `ignore` (the default) or `deny` (§6.4). `admit_source` and `admit_age` are the admissibility record for facts: a value whose `attribution` source is not listed for its property, or that was observed longer than `max_age`, an `xsd:duration`, before `effective_at`, is treated as absent — `missing` (`due2-profiles.md` §3).

### 3.5 Trace — output of W2 and W3

```text
evaluation     (| corpus_id: Digest, request_id: Digest, sotw_id: Digest, config_id: Digest)
finding        (atom_id, predicate: Enum | truth: Truth)
basis          (atom_id, predicate: Enum, kind: Enum, ref | truth: Truth)
unknown_part   (atom_id, predicate: Enum, kind: Enum, ref | input, status: Enum)
witness_basis  (atom_id, witness, ref | truth: Truth)
witness_part   (atom_id, witness, ref | input, status: Enum)
read           (property)
instance       (instance_key: Id | atom_id, occurrence?: Instant, status: Enum, passed: Flag)
eliminated     (atom_id, by_atom, rule: Enum)
alternative    (alt_id: Digest, permission_id)
alt_duty       (alt_id: Digest, duty_id)
dominated      (alt_id: Digest, by_alt: Digest)
verdict        (| value: Enum, frontier_complete: Flag, exact: Flag)
verdict_basis  (atom_id, role: Enum)
verdict_range  (| low: Enum, high: Enum)
diagnostic     (policy_id, code: Enum, ref)
```

| Relation | Written by | Meaning |
|---|---|---|
| `evaluation` | shell | The four input collection ids. The evaluation id is the digest of this tuple — derived, not stored. The case is not an input: the ledger links each evaluation to its case (§7), so the trace depends on content alone. |
| `finding` | W2 | One truth value per evaluated atom and predicate — `applies`, `in_force`, `owed`, or `fulfilled` (§5.1). |
| `basis` | W2 | The parts that *determine* the finding, keyed by the finding's atom and predicate. The parts of a duty's witness conditions are in `witness_basis` instead. `kind ∈ {action, relation, party, constraint, evidence, fact}`; `ref` is the constraint, evidence, state property, or function; `truth` is that part's value. An `F` finding names the part that failed. |
| `unknown_part` | W2 | Every `U` part of every finding W2 produces whose value is `T` or `U`, determining or not, except the parts of a duty's witness conditions, which are in `witness_part`: its atom, the finding's predicate, the part's `kind` and `ref` as in `basis`, the `input` it reads (`odrl:target`, a party function, or an operand's property), and that input's `status`: `missing`, `invalid`, `conflict`, `unresolved`, or `misfit`, a `resolved` value that does not fit the operator (§5.4). An `unresolved` part is completed, and every other part is opaque (§6.4). An `F` finding's `U` parts are not named: none of them can change it, and an index may skip a certainly-`F` atom (§5.5), so naming them would make the relation depend on the index. Root atoms, and a duty's clauses, are the disjuncts of the constraint DNF, unsimplified, with negation pushed to the leaves and `xone` expanded (§3.1, §4 stage 2, §6.4), so a `U` leaf of the authored tree is named exactly when some root atom or duty clause that reads it is `T` or `U`, even if the node above it is decided: in `or(a, u)` with `a` true, `u` is named; in `and(a, u)` with `a` false, it is not. **[D]** (`decisions/0016` and its amendment, `decisions/0028`) |
| `witness_basis` | W2 | The parts of a duty's witness conditions that determine its `fulfilled` finding, for each witness (§5.3): `witness` is the witness's `evidence_id`, and `ref` is the constraint. Every part of a witness clause is a constraint that reads the witness (§5.2). The basis rule of §5.2 applies per witness: for `T`, every part of each clause the witness satisfies, so a witness that satisfies none has no rows; for `F`, the failing parts of every clause, for every witness; for `U`, the `U` parts of each clause that is not `F` for that witness. **[D]** (`decisions/0035`) |
| `witness_part` | W2 | The `U` parts of a duty's witness clauses, when the duty's `fulfilled` finding is `T` or `U`: its atom, the witness, the constraint `ref`, and the `input` and `status` as in `unknown_part`. A part is named under a witness exactly when a clause that reads it is `T` or `U` for that witness, the liveness rule of `unknown_part` applied per witness. One constraint read against two witnesses is two rows, each with the status of what it read. **[D]** (`decisions/0035`) |
| `read` | W2 | Every state property consulted, determining or not. What the ledger pins (`due2-architecture.md` §7); also the dependency index re-evaluation may use. |
| `instance` | W2 | One tuple per evaluated duty instance (§5.3): its atom, the occurrence instant `t` for an instance of a recurring duty (absent otherwise), its status `Enum {fulfilled, outstanding, violated, unknown}`, and `passed`, whether its deadline has passed: the instance has an effective deadline `D` and `effective_at > D` (§5.3). The instance key is the key under which a case records what is owed and when it was first owed (`activation`). |
| `eliminated` | W3 | A candidate or prohibition removed — by conflict resolution, or by a violated precondition duty instance (§6.1, rule `violated_precondition`) — the atom that removed it, and the rule applied: the policy's `conflict` value within a policy, the `combination` across policies (§6.2), or `violated_precondition`. **[D]** (#57) `by_atom` is one tuple per remover: under `prohibit` and a prohibit-overrides combination, each `T` `Forbid` that eliminates the candidate; under `perm`, each `T` candidate that eliminates the `Forbid`; under `invalid`, each `T` candidate and `T` `Forbid` of the void policy other than the atom itself; under `violated_precondition`, the violated duty. |
| `alternative`, `alt_duty` | W3 | Candidates collapsed by outstanding duty set: one `alt_id` per distinct set — its digest — with every permission that gives it and every duty in it. Under unknowns, the sets are the routes that suffice (§6.3), and the permissions those that give each in some completion. |
| `dominated` | W3 | An alternative whose outstanding set strictly contains another's, one tuple per alternative it contains. |
| `verdict` | W3 | The verdict; whether the reported alternatives are known to be all of them; and whether the computation was exact, or fell back beyond `max_mixed` (independent completion) or `max_frontier_vars` (`frontier_complete` false) (§6.4). `exact` is relative to completion over literals (§6.4): it does not mean that the operands' values were reasoned over. |
| `verdict_basis` | W3 | The atoms that determined the verdict, by role: `prohibition`, `permission`, `duty`, `unknown`, `obligation` — and `closed`, naming the candidates a violated precondition removed, so a `NotApplicable` that closed a route can be told apart from one where nothing matched. |
| `verdict_range` | W3 | For an `Indeterminate` only: the least and the greatest completion verdict in the order `Deny < NotApplicable < Pending < Permit` (§6.4). Sound, and possibly wider, when `verdict.exact` is false. **[D]** (`decisions/0011`) |
| `diagnostic` | shell | The corpus `diagnostic` tuples of every policy with an atom in `finding`, copied unchanged, so that a verdict that rests on a contested reading says so (`due2-diagnostics.md` §1). |

### 3.6 Lineage

Which authored rule, which expansion selection, and which parameter binding produced each atom is a separate collection, produced by W1 and referenced by digest from the corpus. W2 and W3 never read it. Explanation and audit do (§3.7). Stage 1's part is normative (`odrl-compound-to-atomic-normalization.md` §7). Stage 2 adds, for each root atom, the constraint disjunct it came from, for each duty clause the disjunct it holds, and for each atom the parameter binding (§4).

### 3.7 Explanation **[D]** (`decisions/0010`)

A verdict alone does not explain a decision; the trace does. Every evaluation that returns a verdict emits its trace (§7), and the explanation is read from it, never computed alongside it.

**The derivation.** An evaluation's explanation is the part of its trace reachable from `verdict`, through references the relations already carry:

| From | To | Through |
|---|---|---|
| `verdict` | the determining atoms, by role | `verdict_basis`; for `Pending`, also `alternative`, `alt_duty`, `dominated`; for `Indeterminate`, also `verdict_range` |
| `verdict` | every input that was missing, invalid, in conflict, unresolved, or a misfit, in a finding that is not `F`, whether or not it mattered | `unknown_part`; for a witness condition, `witness_part` |
| an atom | its findings | `finding` |
| a finding | the parts that determined it (§5.2) | `basis`; for a duty, also `witness_basis` and `instance` |
| a `fact` part | the value and status read | `read`, and the SOTW's `fact`, `fact_value`, `attribution` |
| an `evidence` part, or the `witness` of a `witness_basis` or `witness_part` row | the record | the SOTW's `evidence`, `evidence_param` |
| a `constraint` part | the constraint as normalised | the corpus's `constraint`, `constraint_value` |
| a removed atom | the atom that removed it, and the rule | `eliminated` |
| an atom | the authored rule, expansion selection, and binding | `source_rule`, lineage (§3.6) |
| a policy in the derivation | the contested readings it was accepted under | `diagnostic` |

Reading it needs the trace, the evaluation's four input collections, and the lineage, and nothing else. It never re-runs W2 or W3 and never reads the world. Law L10 (§8) makes this checkable: every reference resolves, and every finding follows from its basis. The derivation is typed relations under the canonical encoding (`decisions/0007`), so it is parseable by any reader that reads the trace.

**Groups are keys.** What belongs together is a key the trace, the corpus, or the lineage already holds. The reader never infers it.

- *The atoms of one authored rule* share `source_rule` and the lineage's selection tuple.
- *A permission and the duties that gate it* are linked by `edge`, `alternative`, and `alt_duty`.
- *The instances of one duty* are its `instance` tuples.
- *The policies evaluated together* are told apart by `atom.policy_id`. Each elimination names its rule: the policy's own strategy, or the cross-policy combination (§6.2).
- *The evaluations of one case* are ordered by its `seq` (§7.1). What changed between two of them is a per-relation set difference of their canonical traces, read with the events recorded between them.

**Rendering is later.** Prose, a page, or a screen is a presentation step over the derivation. It may select and order, and it never adds a reason. A rendering that needs what the derivation lacks reveals a trace defect, fixed by a trace relation under L1 and L10, never by the renderer.

**What the corpus asserts.** A case names atoms by their authored IRI: the projection through `source_rule`, or `source_duty` for a duty, as `frontier` and `obligations` already do (`conformance/README.md`). `expected.verdict_basis` is the set of `(source, role)` pairs of the trace's `verdict_basis`, and `expected.eliminated` the set of `(source, source of by_atom, rule)` triples of its `eliminated`, so the disjuncts of one rule (§4) are one entry. Full traces, with atom ids, are pinned by L1 and replay, not by authored cases.

**[O] A witness for `Indeterminate`.** The `unknown` atoms and their `U` basis say which facts decide, not how. Whether the trace also records a pair of completions with different verdicts is open (issue #58). Each pivotal literal (§6.4) gives such a pair, differing in that literal alone (`decisions/0011`).

**[O] Remedies.** What would change the verdict: for `Indeterminate`, the values of the unknowns that force each verdict in `verdict_range`; for `Deny` and `NotApplicable`, the least change to the request, facts, or evidence that would permit. These are the abductive and contrastive explanations of formal XAI (`references.md` §2). The `Pending` frontier is already one. Whether the trace records them is open (issue #61).

---

## 4. W1 — Normalise **[D]**

```text
W1 : authored policies → (Corpus × Lineage) | Diagnostics
```

A policy W1 cannot normalise is rejected with diagnostics, never accepted and approximated (`due2-architecture.md` §1). Every code is in `due2-diagnostics.md`.

Two stages, both pure, each with its own preservation obligation:

| Stage | Does | Specified in |
|---|---|---|
| **1. Atomise** | Compact interiorisation; expansion of multi-valued action, relation, and party axes; identity and skolemisation; lineage. Structure-preserving: shared duties stay shared. | `odrl-compound-to-atomic-normalization.md` |
| **2. Build** | Constraint DNF, including `xone`; parameter substitution and per-binding duty instantiation, each binding a duty atom with its own id (§3.1, `duty.atom_id`); party-role inheritance — a duty that declares no function properties takes all of them from its parent permission (ODRL IM §2.6.5), one that declares any takes none, and for each role a value the rule states beats one interiorised from the policy level (`odrl-compound-to-atomic-normalization.md` §6.2); projection into §3.1 — a duty's guards stay on its atom (`decisions/0003`); provenance from stage-1 lineage. | `due2-architecture.md` §4–§5 |

**Two forms carry a policy through W1.** Stage 1 parses the authored graph into a **lifted tree** — a forest of trees hanging from named rules (`odrl-compound-to-atomic-normalization.md` §3) — and transforms that; RDF is a boundary format, read at the parse and written at the emit (`ways-of-working.md` §2.4). Its artifact is canonical N-Quads. Stage 2 projects the lifted form into the **relations** of §3.1 — collections of tuples whose fields are the terms of §2 — and the relations are all W2 and W3 ever see.

**Position decides conjunction.** Expanding a root rule yields independent root atoms — any one may match a request, which is disjunction. Expanding a nested duty fans out the parent's edges — every resulting duty is owed, which is conjunction. Neither stage declares which fields are disjunctive; it follows from where the value sits. A constraint's DNF is not an expansion of this kind. A disjunct of a `Permit` or `Forbid` atom's constraint becomes an atom of its own, an alternative. A duty's constraint is never split: it would make alternative conditions into duties all owed. Its disjuncts become clauses of its one atom (§3.1, `decisions/0028`).

Obligations on the output:

- **Stage 1 preserves structure.** It preserves the denotation `Den` — the set of ground atomic rules with identity-bearing duty edges — up to a bijection its lineage records (`odrl-compound-to-atomic-normalization.md` §8.1).
- **Stage 2 preserves meaning.** DNF changes how many atoms there are, so no bijection exists. Its obligation is L9, checked against a direct interpreter (`due2-architecture.md` §10).
- **Sufficiency.** Stage 2 depends on its input only through `Den` — never on node IRIs, triple order, or annotations — and W2 and W3 depend on a policy only through its corpus. So every evaluation depends on an authored policy only through its denotation, which is what lets stage 1's structural guarantee carry through to verdicts.
- **Determinism and bounds.** Isomorphic inputs give identical canonical outputs. A limit breach fails the whole run before any output.
- **Well-formedness.** The §3.1 invariants hold.
- **Rejection.** An `error` diagnostic rejects the policy with no corpus and no lineage. W1 reports every error of the first stage that has one, and runs no later stage, so a rejected policy's set of codes is deterministic and a negative corpus case can state it (`due2-diagnostics.md` §1). Warnings never reject; they are carried in `diagnostic` (§3.1).

---

## 5. W2 — Evaluate **[D]**

```text
W2 : Corpus × Request × SOTW × Config → finding × basis × unknown_part × witness_basis × witness_part × read × instance
```

### 5.1 One predicate per role

Every finding is the truth value of one predicate, chosen by role:

| Atom | Predicate | `T` | `F` | `U` |
|---|---|---|---|---|
| `Permit`, `Forbid` | **applies** (§5.2) | every part `T` | some part `F` | no part `F`, some part `U` |
| root `Oblige` | **in_force** (§5.2) | its policy matches the request and some guard clause holds (or it has none) | its policy does not match, or every guard clause fails | otherwise |
| precondition duty | **owed** (§5.2) | some guard clause holds (or it has none) | every guard clause fails | otherwise |
| precondition duty owed `T` or `U`; root obligation in force | **fulfilled** (§5.3) | some witness satisfies the duty (per witness: `witness_basis`) | every witness fails, or there is none | otherwise |

Duty status reuses the same three values: `T` fulfilled, `F` outstanding, `U` unknown. There is no second status vocabulary. Timing adds a fourth reported state — `violated` — derived in §5.3, not a truth value: it does not enter Kleene combination.

### 5.2 Applies

An atom applies when all of its parts hold, combined by Kleene conjunction (`F ∧ U = F`):

- **action:** `request.action ⊑ atom.action` under the `odrl:includedIn` closure. A request for a narrower action matches an atom on a broader one, never the reverse.
- **relation:** `request.target ⊑ atom.relation_value` under the profile's target closure — collection membership, `isPartOf`. If the request names no target, the part is `U`: absent is not false, as for parties (§9 #8). An index may therefore not skip atoms on target for such a request (§5.5).
- **party:** for each `atom_party(a, f, p)` where the profile declares `f` a match key, `request_party(f) ⊑ p` under the party closure. If the request does not name `f`, the part is `U` — absent is not false. Function predicates that are not match keys are carried, not matched. In v1 only `assignee` is a match key.
- **constraint:** each of the atom's constraints, at its scope (§5.4).

The basis records the determining parts: all of them for `T`, the failing ones for `F`, the unknown ones for `U`; a duty's findings read its clauses (§5.2).

**Guards and witness conditions.** A duty's constraint is a *witness condition* if it reads a witness operand — one bound to `due2:witnessSource`, or `due2:actionTime` — and a *guard* otherwise. Nothing else is declared: the split follows from the bindings (`due2-profiles.md` §3). A guard reads the request, the SOTW, and the context exactly as a permission's constraint does, so a request-source operand in a duty is a guard — DPROD's reading of a duty condition (`formal-semantics.md` §5.2, D-ACTIVATE). A conjunction may mix the two and splits into its parts. A disjunction or negation that mixes them has no reading as either and is rejected at normalisation (`MixedDutyConstraint`). One that does not mix them is kept: W1 puts the guards' conjunction and the witness conditions' conjunction in DNF separately, and each disjunct is a *clause* of the duty's one atom (`constraint.clause`, §3.1). A clause holds when all of its parts hold, by Kleene conjunction, and the guards hold when some guard clause holds, by Kleene disjunction (`decisions/0028`). For a duty, the basis records every part of each clause that holds for `T`, the failing parts of every clause for `F`, and the `U` parts of each clause that is not `F` for `U`. A witness clause is evaluated once per witness (§5.3), so its parts are recorded per witness, in `witness_basis`, by the same rule. Guards decide *when* a duty is owed; witness conditions decide *what* fulfils it (§5.3). This is RL2's split between `condition` and `postCondition`, and DPROD's between a duty's condition and its performance. Guards stay on the duty (`decisions/0003`).

**Owed.** A precondition duty is owed when its guards hold, by the clause rule above; with no guards it is owed whenever its parent applies. An inactive duty is not owed — the parent permission stands without it (DPROD D-ACTIVATE; W3C CG example C21). A duty that is also a root obligation reads the same guards in that role, through `in_force`; both findings come from one evaluation of the guards, and canonical literals (§6.4) keep them correlated.

**In force.** A root obligation of policy `P` is in force for a request when some `Permit` or `Forbid` atom of `P` *matches* the request — action, relation, and parties as above, constraints aside — and the obligation's guards hold, by the clause rule of §5.2. An obligation is not matched by its own action: it travels with the policy under which the request is made. A log-every-access obligation is therefore in force for a read, which an action match would never achieve.

### 5.3 Fulfilled

Fulfilment follows RL2 (`spec/RL2_Model.md` §4.3, §7.3). It is derived from evidence of performed actions, and the absence of evidence means *not yet fulfilled* — never unknown. The case history is where evidence arrives: a duty with none is outstanding, and the requester is told so through `Pending`.

**Instance.** Each precondition duty `d` resolves to one duty instance, recorded in `instance`:

- scope `member` — one instance per duty atom and performer (and occurrence, under *Recurrence* below), shared by every request with that performer, so one fulfilment serves all of them. "Petition the council about X" binds to X, and its atoms for X and Y are two instances.
- scope `grant` — one instance per request, fulfilled only by evidence submitted against it ("pay per use"). A request without a `reference` falls back to `member`.

The instance key is the duty atom's id, with what the request and the occurrence add **[D]** (`decisions/0032`, amendment of 2026-10-25):

- the **performer**, the request subject, when the witness test below reads it as the actor: the duty has no bearer, or its bearer is an `odrl:PartyCollection` and the subject is not known to be outside it (`subject ⊑ bearer` is `T` or `U`). When membership is `U`, the instance is the subject's if the subject is a member, and the witness test is `U` for any other member's act. "Complete annual training", borne by all employees, is then one instance for Alice and another for Bob, and Alice's training serves every request of hers. A request that names no subject adds none;
- `request.reference`, for scope `grant`;
- the occurrence `t`, for a recurring duty (*Recurrence* below).

With nothing added, the key is the atom's id. Otherwise it is `H(frame(namespace, "duty-instance", atom_id, additions))` in the notation of `odrl-compound-to-atomic-normalization.md` §5.2, where `additions` is a run of fields, in this order and each only when added: `frame("performer", term(subject))`, `frame("reference", reference)` with the reference as UTF-8, and `frame("occurrence", term(t))`. Each value carries its name, so no placeholder marks an absent one, and `atom_id` is framed as stage 1 frames an identity, a UUID IRI as its raw bytes and any other IRI as UTF-8. The case history records each key from the trace's `instance` tuple, so a shell that supplies an `activation` copies the key and never computes it (`due2-profiles.md` §7). The atoms an authored duty expands into, one per action or target say, therefore have one instance each, and a duty in two roles, or one that two permissions share with the same inherited roles and parameter values, has one instance for the request.

**Witness.** Evidence `e` is a witness for `d` when:

- `e.occurred_at ≤ sotw.effective_at`;
- `e.action ⊑ d.action`;
- `e.object = d.relation_value`, if `d` has one;
- `e.actor` is `d`'s bearer — the party in the bearer role (`due2-profiles.md` §6: `odrl:assignee` unless a profile says otherwise), after role inheritance (§4) — or the request subject if `d` still names none. A bearer that is an `odrl:PartyCollection` is borne by each of its members, which "undertake the same functional role in the Rule" (ODRL IM §2.3), so when the request subject is a member (`subject ⊑ bearer` under the party closure), `e.actor` must be the subject: another member's act does not discharge it. When the request names no subject, an act by a member is `U`, since that member may be the subject (`decisions/0018`);
- `signer` admits `e.issuer` for `d`'s `source_duty` (§3.4);
- for scope `grant`, `e.discharges` is the digest of `d`'s `source_duty` and `request.reference`: the evidence was submitted against this request's grant of the duty. The atoms of one authored duty share that grant, and the rest of the test picks among them: a payment of one fee has that fee as its `object`. For scope `member`, `discharges` is not consulted.

A duty with both roles — an obligation of its policy and a precondition of a permission — is one atom. For a given request it has one instance key in both roles, since the request adds the same values in both, so it has one `fulfilled` finding, which both roles read.

**Truth.** `d`'s witness conditions are evaluated once per witness: witness-source operands read its `evidence_param`, and `due2:actionTime` is its `occurred_at` (`due2-profiles.md` §3). Every other operand reads the request, the SOTW, or the context as usual; in a duty, those are the guards (§5.2). A witness satisfies the witness conditions when it satisfies some witness clause (§5.2), and any witness satisfies a duty with none. The finding is the Kleene disjunction of that value over all witnesses: `T` if some witness satisfies some clause; `F` if every witness fails every clause, which includes having no witness; `U` otherwise. Each witness's evaluation is recorded under its `evidence_id`: the parts of the witness clauses in `witness_basis`, and their `U` parts in `witness_part` (§3.5). A duty requiring a payment of 5, with one witness that states no amount and another that states an IRI for it, has two `witness_part` rows for the one constraint, with statuses `missing` and `invalid` (`decisions/0035`).

**Deadline and status.** A duty atom may carry timing (§3.1): a `deadline` — an absolute `xsd:dateTime` with a timezone, or an `xsd:duration` relative to the instance's activation — and a `recurrence`. For an instance with activation `A` (the SOTW's `activation` relation, defaulting to `effective_at`: an instance first owed now):

- the **effective deadline** is `D = deadline` when absolute, `A + duration` when relative, and absent when the duty has none (DPROD `formal-semantics.md` §5.3). Durations are single-kind — day-time or year-month — as §4 of `due2-profiles.md` requires;
- a witness must be timely: it counts only with `occurred_at ≤ min(effective_at, D)`. Performance after `D` does not fulfil — DPROD's D-FULFILL (§5.2 there) — and a late witness does not reopen a deadline;
- the instance's **status**, which W2 writes to the trace (§3.5):

| witness finding | deadline | status |
|---|---|---|
| `T` | any, or none | `fulfilled` |
| `F` | none, or `effective_at ≤ D` | `outstanding` |
| `F` | `effective_at > D` | `violated` |
| `U` | — | `unknown` |

Without a deadline a duty is never violated. Status is derived, never remembered: an evaluation computes it from its evidence, `effective_at`, and `D`, so timely evidence — a witness with `occurred_at ≤ D` — found in a later SOTW makes the instance fulfilled in that evaluation. DPROD instead keeps `Violated` terminal in its duty state Σ (`formal-semantics.md` §9.4); that disagreement is exception 2 (`due2-profiles.md` §8.2). W3 reads the status, and `passed`, from the trace and never re-derives them: the deadline comparison is thereby fixed per evaluation — it is a fact of the SOTW, not a finding — which is what keeps W3 pure and the completions of §6.4 well-defined.

**What an unknown instance can become [D]** (`decisions/0032`). An `unknown` instance is `fulfilled` in a completion where its finding is `T`. Where the finding is `F`, it is `violated` if `passed` is true and `outstanding` otherwise, as the table gives. W2 records `passed` on every instance for this reason: the status `unknown` does not say whether the deadline has passed, and a violated precondition closes its route (§6.1), so the two cases can give different verdicts. Without a deadline, `passed` is false.

**Recurrence.** A duty with `recurrence` is owed once per occurrence of its RRULE. W2 generates the occurrences `t ≤ effective_at` — the anchor is the rule's `DTSTART`, or the duty's activation without one (`due2-profiles.md` §7) — and derives one instance per occurrence: the instance key extends with `t`, the trace's `occurrence` is `t`, the instance's activation is `t`, and a relative deadline is `t + duration`. A witness for an occurrence must also satisfy `occurred_at ≥ t`: one delivery does not fulfil every later instance. DPROD's `performed` check has no lower bound, so one performance fulfils every later instance there — a gap found in DPROD (`due2-profiles.md` §8.2). Occurrences beyond `effective_at` — instances not yet owed — are not generated; reporting them is the open window question (§9, `due2-profiles.md` §9).

An instance exists only for a duty that is owed: a precondition whose `owed` finding is `F` has no instance and no `fulfilled` finding, as an occurrence not yet due has none. One whose `owed` is `U` has both, and W3 combines them (§6.1).

Fulfilment is derivation, not bookkeeping. Evidence is appended to the case and the case is evaluated again; no status is ever flipped in place.

### 5.4 Constraints

For a constraint with left operand `o`:

1. `o`'s binding (`due2-profiles.md` §3) gives its source — request, state, witness, or context — its property, value type, cardinality, allowed operators, and any concept schemes.
2. For a state-source operand, W2 records the property in `read` and looks up its `fact`. A request-source operand reads `request_param`, a witness-source operand the witness's `evidence_param` (§5.3), and a context operand its built-in.
3. Status `resolved` → apply the operator to the value(s) and `constraint_value`(s), giving `T` or `F`, or `U` when a value does not fit the operator: a kind other than the right operand's, a `dateTime` without a timezone or a `date` with one (`decisions/0024`), or a concept in none of the operand's schemes (`due2-profiles.md` §4). A state property with any other status, or with no fact at all → `U`, with basis kind `fact` and the property as `ref`: what resolves it is the property's fact. Every other `U` from a value has basis kind `constraint` and the constraint as `ref`: a value of any source that does not fit, or a request or witness value that is `missing`, `invalid`, or in `conflict` (`due2-profiles.md` §3). What resolves it is a value that fits, not a state fact. Every `U` part is also recorded in `unknown_part` (§3.5), or in `witness_part` under its witness for a part of a witness clause (§5.3), with the status of what it read: the state property's status (`unresolved` when it has no fact), the request or witness value's status, or `misfit` for a `resolved` value that does not fit. An absent target or party (§5.2) is `missing`.
4. The shell finds properties still to resolve as `read` properties with no `fact` in the SOTW. Derived, not recorded twice.

Operators form a closed, typed registry. Strings compare by Unicode code point. No operator consults the clock, the locale, or randomness. Time enters only as `request.at`, `sotw.effective_at`, and evidence times, each an `xsd:dateTime` with a timezone (`decisions/0024`): a constraint on when the action happens (ODRL `dateTime`) reads `request.at` for a permission or prohibition and the witness's `occurred_at` for a duty.

### 5.5 Which atoms

W2 produces a finding for:

- every `Permit` and `Forbid` atom whose finding could be other than `F`;
- every precondition duty of a `Permit` whose finding is not `F` — its `owed` finding, and its `fulfilled` finding when `owed` is `T` or `U`; and
- every root obligation of a policy some of whose `Permit` or `Forbid` atoms match the request (§5.2), with its `fulfilled` finding when `in_force` is `T` or `U`; and
- one `instance` tuple (§3.5) for every duty instance derived above — for a recurring duty, one per occurrence (§5.3).

An index may skip root atoms that are certainly `F` — wrong action, wrong target — because an `F` root is neutral in W3. It may not skip an atom whose match turns on a `U` part. It never skips a precondition of a live permission: an owed, unfulfilled duty is outstanding, which is not neutral. Remedies and consequences are not evaluated for access; they belong to the monitoring question.

---

## 6. W3 — Resolve **[D]**

```text
W3 : Corpus × finding × basis × unknown_part × instance × Config → eliminated × alternative × alt_duty × dominated × verdict × verdict_basis
```

Four steps in fixed order. The order is normative: conflict resolution runs before duties choose among routes, so duties can choose among surviving permissions but never decide which survive. The one duty finding read before conflict is a violated precondition that is owed: it closes its route outright (§6.1), so the closed permission takes no part in conflict.

### 6.1 Candidates

A precondition duty is **open** for its parent when `owed ∧ ¬fulfilled` (§5.1), in Kleene logic: `T` when it is owed and unfulfilled, `F` when it is not owed or is fulfilled, `U` otherwise. A duty that is not owed is not open, whatever its evidence.

A root `Permit` with finding `T` or `U` is a candidate — unless one of its precondition duty instances is `violated` (§5.3) and that duty's `owed` is `T`. A violated precondition removes its parent's candidacy outright: the route can no longer be taken, and `Pending` must not offer it. The removal is recorded in `eliminated` with rule `violated_precondition`, and `verdict_basis` carries it with role `closed` (§3.5), so the answer distinguishes *a route that closed* from *nothing that matched*. A violated precondition whose `owed` is `U` makes the candidate uncertain instead. A surviving candidate's **outstanding set** is its precondition duties whose open value is `T` — a violated one removed the candidate instead of joining the set; its **unknown set**, those whose open value is `U`. Each candidate is in exactly one state:

| State | Condition |
|---|---|
| **ready** | permission `T`; no outstanding, no unknown duty |
| **pending** | permission `T`; some outstanding, no unknown duty |
| **uncertain** | permission `U`, or some unknown duty |

Root obligations in force are reported in `verdict_basis` with role `obligation`, with their bearer and, for each of their instances, the status W2 computed (§5.3) — `fulfilled`, `outstanding`, `violated`, or `unknown` — which is what §6.4's `deny` reads. An obligation whose `in_force` is `U` is reported `unknown`, whatever its instance status; one not in force is not reported. Neither status nor bearer is stored beyond the trace. Under `config.violations = ignore`, obligations never affect the verdict; a violated *precondition* still removes its candidate (`due2-profiles.md` §7).

### 6.2 Conflict

1. **Within a source policy**, by its `conflict`. Under `prohibit`, a `T` `Forbid` eliminates that policy's candidates. Under `perm`, a `T` candidate eliminates that policy's `Forbid` atoms. Under `invalid`, a `T` candidate and a `T` `Forbid` together void the policy: all of its `Permit` and `Forbid` atoms are eliminated, with rule `invalid`. **[D]** (`decisions/0029`) A void policy gives no access answer, and its root obligations stay in force (§5.2): a violated one still denies under `violations = deny` (§6.4), because whether an obligation was met does not depend on the request that voided the policy. `Indeterminate` with a cause stays parked (`due2-architecture.md` §6.2).
2. **Across source policies**, by `config.combination` **[O]**. Default: prohibit-overrides — any surviving `T` `Forbid` eliminates every candidate. Alternatives: permit-overrides; priority-ordered first-applicable on `atom.priority`.

`U` atoms eliminate nothing; they make the verdict uncertain (§6.4). Every elimination is recorded with its rule. Duties play no part.

### 6.3 Collapse and order

Within one completion, alternatives are formed from the ready and pending candidates that survive §6.2. Under unknowns, the reply lists the frontier that the paragraph *The listed frontier* below defines.

1. **Collapse.** Candidates with the same outstanding set — compared by duty id — form one alternative. Two permissions that cost the same are one choice with two grounds, not two choices.
2. **Order by inclusion.** Alternative `A` dominates `B` when `outstanding(A) ⊊ outstanding(B)`. This needs nothing but duty identity: no weights, no costs, no configuration. A ready candidate has the empty set and so dominates every pending one. Authorisation state is not a separate rule — it falls out of the order.
3. **Frontier.** The non-dominated alternatives. If there are several, they are incomparable — neither demands a subset of the other's duties — and W3 reports all of them. Each outstanding duty is reported with its bearer, so a route that waits on someone other than the requester — a second approver — says so.

**Sorting [O].** Inclusion is a partial order, and the frontier is its honest output. A total order needs a declared preference — fewest duties, declared weights, a ranking of duty kinds — in config, a field whose form is open (#5). Without one, alternatives are listed in a deterministic order (outstanding-set size, then `alt_id`) that expresses **no** preference. Storage order, upload time, and evaluation order never break a tie.

**The listed frontier [D]** (`decisions/0026`). A *route* is an outstanding set. Under unknowns, each completion (§6.4) has its own candidates and frontier. A route is **open** in a completion when some candidate that survives §6.2 there has it, whether or not a smaller route dominates it there. A route **suffices** when it is open in some completion and every completion has an open route within it: the same set or a subset. For a definite `Pending` or `Permit` (§6.4), the listed frontier is the routes that suffice and that no route that suffices dominates. Each is an alternative whose grounds are the permissions that give it in some completion. For a definite `Permit`, every completion has the empty route open, so the listed frontier is the empty route.

A listed route is one the requester can act on. In each completion, some candidate's outstanding set lies within it, and fulfilling the route's duties empties that set. A fulfilled duty is not violated, so §6.1 closes no candidate on its account, and §6.2 never reads duties, so the candidate still survives and is ready. Under the default combination, making `fulfilled` findings true never lowers a verdict (§6.4), and the completion's verdict was not `Deny`, so it becomes `Permit`. A route that does not suffice is not listed: fulfilling its duties may permit only in some completions. Three examples, each with `x` unresolved:

- Permissions on `x eq 5` and on `x neq 5` both need `d`. The route `{d}` is open in every completion, though no one permission gives it in each, and it is listed with both as grounds.
- One permission needs `d` and `d2`, and `d2`'s `fulfilled` finding is `U`. Its route is `{d, d2}` in some completions and `{d}` in the others. `{d, d2}` suffices, `{d}` does not, and `{d, d2}` is listed.
- One permission needs `d0`, owed when `x` is false, and `d1`, owed when it is true. Its route is `{d0}` where `x` is false and `{d1}` where it is true, and neither is within the other. No route suffices, and the listed frontier is empty: what to do depends on `x`, which `unknown_part` names (§3.5).

### 6.4 Verdict

The verdict is defined by invariance:

> Replace every `U` finding by `T` or `F`. If every such completion gives the same verdict, that is the verdict. Otherwise it is `Indeterminate`.

For a completion, which has no `U`:

| Verdict | Condition, checked in order |
|---|---|
| `Deny` | a `Forbid` survives §6.2 and applies; or `config.violations = deny` and some instance of an obligation in force has status `violated` (§5.3) |
| `Permit` | the frontier contains a ready alternative |
| `Pending(frontier)` | the frontier is non-empty |
| `NotApplicable` | otherwise |

**What a verdict says [D]** (`decisions/0031`). A verdict is the answer of the policies in the corpus, as written, for the request in the SOTW, whatever their class. Over an offer, `Permit` says that the offer's terms permit the action: "this offer permits you to proceed". It does not say that anyone has accepted the offer. Accepting it, and recording the agreement that results, happen outside the workflows. The reading cuts both ways: an offer's prohibitions and, under `violations = deny`, its violated obligations deny as any policy's do. The offer permits only a requester it covers, since an assignee is matched like any party (§5.2). A withdrawn or expired offer still permits unless selection leaves it out or a constraint on its status, flattened onto the request, excludes it (`due2-profiles.md` §8.1). `verdict_basis` names the permitting atoms and so their policies (§3.7).

Under `deny`, a violated obligation in force acts as a surviving prohibition. DPROD instead checks violations only once a permission is active (`formal-semantics.md` §7.2, steps 5–6). Withholding only `Permit` and `Pending` would let a new permission turn `NotApplicable` into `Deny`, which breaks monotonicity and with it the two-completion computation below. due2 keeps monotonicity; the difference is DPROD exception 6 (`due2-profiles.md` §8.2).

**Computing it.** Order the completion verdicts `Deny < NotApplicable < Pending < Permit`. Under all three strategies and the default combination, the verdict is monotone in every finding: making a permission or a duty's `fulfilled` more true never lowers it, and making a prohibition or a precondition's `owed` more true never raises it.

*Proof*, by cases on one finding changing from `F` to `T`. The verdict rises with the candidate set and falls with the set of surviving `T` prohibitions, so it suffices to track those two sets.

- **A duty's `fulfilled` finding.** One outstanding set shrinks, and a pending candidate may become ready. A candidate that a violated precondition removed may also re-enter (§6.1). It then passes through §6.2 exactly as the new candidate of the permission case below does, so eliminations may change (L6, §8), but candidates are only added and prohibitions only removed. The verdict stays or rises.
- **A precondition's `owed` finding.** An owed duty may become open: one outstanding set grows, and a ready candidate may become pending. Or, if its instance is violated, its candidate is removed before §6.2 (§6.1), which is the permission case below run from `T` to `F`: candidates are only removed and prohibitions only added. The verdict stays or falls, so `owed` is completed like a prohibition (`decisions/0003`).
- **A permission `p` of policy `P`.** Under `prohibit`, `p` is eliminated if `P` has a `T` prohibition and is otherwise a new candidate. Under `perm`, `p` is a new candidate and eliminates `P`'s prohibitions. Under `invalid`, if `P` has a `T` prohibition: either `P` already had a `T` candidate and was void already, so nothing changes, or its prohibition survived before and the verdict was `Deny`, the minimum. Candidates are only added and prohibitions only removed. The verdict stays or rises.
- **A prohibition `f` of policy `P`.** Under `prohibit`, `f` survives. Under `perm`, `f` is eliminated if `P` has a `T` candidate and survives otherwise. Under `invalid`, if `P` has a `T` candidate, `P` is voided: its candidates go, and so do its prohibitions — which were all `F`, or `P` would already have been void. Its obligations stay (§6.2), so a violated one still denies under `deny`. Candidates are only removed and prohibitions only added. The verdict stays or falls.
- **Under `violations = deny`, an obligation's `in_force` finding, or a duty's `fulfilled` finding.** A violated instance of an obligation in force acts as a surviving prohibition. The status is computed by W2 from the `fulfilled` finding and the deadline, which the evaluation fixes (§5.3); it is not itself a finding, so it does not vary between completions — within a completion, the violated instances are exactly the `F` duties whose instance has `passed` (§3.5, §5.3; for a precondition, those also owed). Making `in_force` more true can only add a violated obligation, and making `fulfilled` more true can only remove one — a violated precondition also restores its candidate. So `in_force` is completed like a prohibition, and `fulfilled` like any duty. ∎

The verdict is therefore a monotone map from completions — ordered with prohibitions reversed — into a chain. Every completion's verdict lies between that of the most restrictive completion (permissions and `fulfilled` findings `F`; prohibitions, `owed`, and under `deny` `in_force` `T`) and that of the most permissive one (the reverse). If the two agree, every completion agrees, so the definition costs two evaluations, not exponentially many. `tools/check_completion.py` checks the two-extremes computation against brute force over every completion (below). Reading `invalid` as `Indeterminate` instead would add a value outside the chain, so that alternative — parked, `due2-architecture.md` §6.2 — would need its own argument.

**Completions range over literals [D].** A finding is `U` because some of its parts are (§5.2). A `U` part whose value exists but is not known, one that reads a state property that is `unresolved` or has no fact, is **completed**. Every other `U` part is **opaque** (`decisions/0016`): its value is `missing` (an absent target or party included), `invalid`, in `conflict`, or a misfit (§5.4). Nothing says that its input has one value that fits, so an operator and its complement need not have opposite truth values there, and the pairing below does not hold for it. An opaque part is a variable of its own, shared with no other part. In an authored constraint tree it stays `U` under strong Kleene logic, and the finding it leaves `U` is completed instead. W1's rewrites are strong Kleene equivalences, so a tree and its DNF atoms, or a duty's clauses, are `U` together (L9). Each completed `U` part is a *variable*, with one exception that makes the definition exact for parts the policy correlates: two constraint parts with the same scope, operand binding (source and property, `due2-profiles.md` §3 — not the left-operand IRI, which two policies may bind differently), concept reading, unit, and right operand(s) are one variable — the same polarity when their operators are equal, opposite polarities when they are complements (`eq`/`neq`, `lt`/`gteq`, `lteq`/`gt`, `isAnyOf`/`isNoneOf`). The key is derived from the corpus's `constraint` and `constraint_value` tuples, so nothing is stored. Right operands are compared as written terms (§2 `Term`), each a lexical form with its datatype, so the datatype is part of the key through them. The concept reading says whether the left operand has a concept scheme (`due2-profiles.md` §4): with one, `eq` is ⊑ under `skos:broader`, and without one, identity. Two operands bound to one property, one with a scheme and one without, therefore make different comparisons. With `x` a concept below `c`, `eq c` without a scheme and `neq c` with one are both `F`, so they are not complements, and pairing them would give a wrong definite verdict (`decisions/0023`). Two terms with one value, such as `5` and `5.0`, are then two variables: like the parts below whose relation is not worked out, that can cost a definite verdict, never produce a wrong one. Relation and party parts are keyed the same way: two that test the same request field against the same value with the same relation (the target, or one function's party) are one variable, so the atoms that W1's expansion copies from one rule, or that two rules give the same party, share it (`decisions/0011` #2, `decisions/0012`). A request field has no `unresolved` status, so an absent target or party is opaque, and shares nothing (`decisions/0016`). Parts that are not the same expression or its complement stay separate variables, even over one field (target `ex:a` and target `ex:b`; `eq 0` and `lteq 2`), as *What stays approximate* below says. A duty's `fulfilled` finding, a disjunction over witnesses, is one variable of its own. A completion assigns `T` or `F` to every variable, and each `U` finding is re-derived from its parts by Kleene conjunction (§5.2) under that assignment.

This matters wherever one fact is read in both directions. `xone` expands into disjuncts that carry the others' negations. Authors write complements across rules ("home lending may read; everyone else must petition first" as two permissions, `dept = HL` and `dept ≠ HL`). A guard literal may also appear in a rule's constraint. With the fact unknown, completing those parts independently admits combinations no value produces — both `dept = HL` and `dept ≠ HL` `F` — and the verdict widens to `Indeterminate` where the authored policy decides. In `due2-xone-unknown`, single-domicile clients are permitted by an `xone` and dual-domicile clients by a separate rule with an attestation duty; with one domicile known, the other unknown, and the attestation on file, every value of the unknown fact permits. Sharing one variable excludes the impossible combinations, and the verdict is `Permit`.

*Computing it.* A variable is **uniform** when each of its occurrences moves the verdict the same way — upward for a positive occurrence in a permission's `applies` or a duty's `fulfilled`, or a negative one in a prohibition's `applies`, a precondition's `owed`, or an obligation's `in_force` under `deny`; downward for the reverse — and **mixed** otherwise. By the monotonicity argument above, applied per occurrence, uniform variables are bounded by the two extreme completions. Mixed variables are enumerated: for each of the `2^k` assignments to the `k` mixed variables, complete the uniform ones at both extremes. The verdict is definite when all `2^(k+1)` completion verdicts agree. `k` counts only unknown literals that occur with both directions in the evaluation at hand — zero unless a fact is read both ways, as above; a duty's guards alone never raise it. Beyond `max_mixed` (a `config` field, §3.4) the mixed variables are completed independently, each occurrence its own variable: sound, erring only towards `Indeterminate`, and recorded as `verdict.exact = false`. Either way, a definite verdict is invariant over every real value of every unresolved fact, and over both truth values of every opaque part. `tools/check_completion.py` checks this computation against brute force over every assignment, under the three conflict strategies, with the fallback forced, with guards that share variables with rule constraints (`decisions/0003`), and with deadlines, violated preconditions, and `violations = deny`. It has found no mismatch, and 2.5% of its instances are definite where completing every occurrence independently says `Indeterminate`.

*What stays approximate.* Parts that read one fact but are neither identical nor complementary remain independent: `x ≤ 5` and `x > 7` both `T` is still a completion, though no value of `x` produces it, and two permissions on `x = "a"` and `x = "b"` over an enumerated `x` are still `Indeterminate` when `x` is unknown. The cost is an `Indeterminate`, or a wider `verdict_range`, never a wrong definite verdict. Exactness there needs each operand's value domain and is not bounded in general. RL2 makes the same approximation for all shared facts (RL2's `spec/RL2_Semantics.md` § Conflict Resolution). **[O]** — domain-aware completion for enumerated facts (§9 #6). `verdict.exact` is relative to this definition. It says that no fallback was taken beyond `max_mixed` or `max_frontier_vars`, not that the operands' value domains were reasoned over: an exact `Indeterminate` may still be decidable by reasoning over the values (#25).

`frontier_complete` is true iff every completion's frontier is the listed frontier (§6.3). It is false when some uncertain candidate could, in some completion, add or change a frontier alternative without changing the verdict: `Pending` stands, but a completion's frontier may hold routes that are not listed, or lack some that are. "Change" includes removal: an uncertain candidate whose outstanding set is smaller can dominate a listed alternative.

*Computing it* **[D]** (`decisions/0004`, `decisions/0026`). For a definite `Pending`, the *relevant unknowns* are the variables of the `U` parts of uncertain candidates (permission, `owed`, `fulfilled`) and of prohibitions whose finding is `U`. Ready and pending candidates have none, and two `Pending` completions that agree on the relevant unknowns have the same surviving candidates, each with the same outstanding set. So they have the same open routes and the same frontier. With `r` relevant unknowns, at most `max_frontier_vars` (a `config` field, §3.4), W3 enumerates all `2^r` assignments, with every other unknown at one fixed value. The routes that suffice, and so the listed frontier, are read from those assignments' open routes, and `frontier_complete` is true iff each assignment's frontier is the listed frontier. The two-extremes shortcut does not apply, because a frontier is a set, not a point on the verdict chain. Beyond the bound, W3 lists the routes of the candidates that are ready or pending whatever the unknowns are, and that no completion removes in §6.2, the non-dominated ones. Under `invalid`, a `U` prohibition in a candidate's policy voids the policy in the completions where the prohibition is `T`, so such a candidate is left out. Under `prohibit` and the default combination, such a prohibition gives `Deny` where it is `T`, so a definite `Pending` has none. Each route listed then suffices, since its candidate survives with it in every completion, though some route that suffices may be missing. `frontier_complete` is false and `verdict.exact` is false. The cheaper rule "complete iff no candidate is uncertain" is sound but less exact; `decisions/0004` compares the two, and `tools/check_completion.py` checks the enumeration against the definitions, and that every route the fallback lists suffices.

`verdict_basis` names the determining atoms: for `Deny`, the surviving prohibition, or, under `deny`, the violated obligation in force, which role `obligation` names with its status (§6.1); the ready alternative's permissions for `Permit`; the frontier's permissions and outstanding duties for `Pending`. Under unknowns these are the atoms that play the role in every completion **[D]** (`decisions/0016`, #71): the certain answer, the notion that makes the verdict definite. A `U` atom that plays it in every completion is named. A verdict that holds by cases has no such atom, and its basis is empty. Two prohibitions on `x eq 5` and `x neq 5`, with `x` unresolved, give `Deny` in both completions, each from a different prohibition, so the basis is empty, and `unknown_part` names `x`. `verdict_basis` also names the `U` atoms whose completion changes the outcome for `Indeterminate`, and, for a `NotApplicable` where candidates were removed by violated preconditions, those candidates with role `closed` (§3.5).

**Which `U` atoms [D]** (`decisions/0011`). A variable is **pivotal** when flipping it alone changes some completion's verdict. The `unknown` atoms are those whose finding is `U` and that have a pivotal variable among their `U` parts. A `U` atom that differs between two disagreeing completions, but could not have moved the verdict, is not named. The pivotal variables are the relevant variables of the verdict as a function of the completions, and the Halpern–Pearl causes of it under some contingency (`references.md` §2). They are read per literal, not per atom, because atoms share literals. With them, `verdict_range` gives the least and the greatest completion verdict: the two extremes, or the extremes of the mixed enumeration. *Computing it* **[O]**: by enumeration within a bound, as for `frontier_complete`. Past the bound, every `U` atom is named, and `verdict.exact` is false. The bound is set with W3 (#38, #42).

---

## 7. Replay **[D]**

An evaluation is one run of W2 and W3 over a case (§7.1), identified by its four input collection ids. W2 and W3 are pure, so the trace is a function of the evaluation: replay re-runs them and compares digests, and calls no resolver. The ledger (`due2-architecture.md` §7) records every case: each evaluation, the reads with their values, and the verdict. Re-evaluation is a new evaluation of the same case, over a new SOTW — never an edit to an old trace.

**Crashes [D].** A failure that should never happen, such as a violated contract, a broken invariant, or an I/O fault in the shell, is not a verdict. The shell answers `Error(cause)`. The verdict set stays the five values of §1, and `Indeterminate` keeps its one meaning: the data could not decide. What the caller does with an error is the caller's default, as it is for `Indeterminate`. A crashed evaluation produces no trace. The ledger stores the evaluation and the cause. W2 and W3 are pure, so replaying that evaluation reproduces the crash: the evaluation is the bug report. W1 is the same: a crash in normalisation is an error, not diagnostics, and builds no corpus (`ways-of-working.md` §2.2).

### 7.1 The ledger **[D]** (`decisions/0008`)

The ledger holds cases. Each request opens exactly one case, and everything after it — facts, evidence, activations, evaluations — is an event on that case, in the order recorded. The SOTW is the case's truth about the world as it evolves: there is no separate revision, only the events so far.

```text
case        (case_id | request)
event       (case_id, seq | kind, valid_at?, ref)
evaluation  (case_id, seq | request, corpus, sotw, config, pins, trace?, verdict?, error?)
```

| Relation | Meaning |
|---|---|
| `case` | One per request: `request` is the request that opened the case. `case_id` is assigned by the shell. |
| `event` | `seq` counts from 1, in the order the shell recorded events, and numbers `evaluation` tuples too. `kind ∈ {fact, evidence, activation}`; `ref` is the content id of the §3.3 tuple recorded. `valid_at` is when it held in the world; a fact learned late simply carries an earlier `valid_at`. Policy amendments and normaliser upgrades are not events: the next evaluation names the new corpus id. |
| `evaluation` | The evaluation recorded at `seq`, once; `event` does not repeat it. It holds the request, corpus, SOTW, and config ids (§3.5 names all four). The request is the case's, with an earlier `at` moved to `effective_at` (§3.2). It also holds the normaliser versions in force (`pins`), and the outcome: `trace` and `verdict`, or `error` with its cause. |

**The SOTW of an evaluation** is the case's events before it, taken as of `sotw.effective_at`: for each fact, the value with the latest `valid_at` no later than `effective_at`. It is frozen as a collection, and its digest is the evaluation's `sotw` id.

**The current answer** for a case is its latest evaluation.

**What did we decide, and when.** Earlier decisions are not recomputed: the answer is the earlier `evaluation` event, which pins its inputs, and replay reproduces its trace (§7).

**Append-only.** Events are added, never changed. The shell serialises writes per case.

---

## 8. Laws

Acceptance criteria for any implementation, checked by property tests over generated inputs (`ways-of-working.md` §7).

| | Law |
|---|---|
| **L1** | **Determinism.** Same evaluation, same trace bytes, whatever the tuple order, machine, or locale. |
| **L2** | **Boundaries.** An atom's W2 finding reads no other atom's finding. It is unchanged by adding, removing, or changing other atoms, with one exception: a root obligation's `in_force` reads whether some root `Permit` or `Forbid` of its own policy matches the request (§5.2, *In force*), so it can change with those atoms' action, relation, and party parts. W3's output is unchanged by any change to the request or SOTW that leaves W3's inputs from W2 unchanged: `finding`, `basis`, `unknown_part`, and `instance` (§6). A change that leaves the findings alone can still change the others, for example a later `effective_at` that sets an instance's `passed` (`decisions/0032`). |
| **L3** | **Prefetch neutrality.** Adding facts that W2 does not read leaves the trace unchanged, except for the `evaluation` tuple, whose `sotw_id` names the larger SOTW (§3.5). Adding a `resolved` value for a state property that W2 reads and that had none (`unresolved`, §5.4) can only turn `U` into `T` or `F`, or leave it `U` as a misfit (L4). A second value for a property that has one is not covered: under cardinality one it is a `conflict`, which makes the part `U` (`due2-profiles.md` §3). |
| **L4** | **Information monotonicity.** Resolving an unknown never turns `Permit` into `Deny` or back. A value that arrives and fits, for an unresolved or an opaque part, can only replace `Indeterminate`. One that arrives as a misfit, or the answer that none exists, makes a completed part opaque (§6.4), and can turn a definite verdict into `Indeterminate`, never into another definite one (`decisions/0016`). |
| **L5** | **Prohibition monotonicity.** Adding an applicable prohibition never raises the verdict. |
| **L6** | **Duty neutrality.** Conflict resolution (§6.2) reads no duty finding: its eliminations depend only on the candidates that enter it and the prohibitions. Adding, removing, or fulfilling duties changes them only by changing which candidates §6.1 removes with rule `violated_precondition`; when those removals are unchanged, so are the eliminations of §6.2. Under `perm`, for example, timely evidence for a precondition whose deadline has passed restores its permission, which then eliminates its policy's `T` `Forbid`. |
| **L7** | **Readiness.** If some candidate is ready after §6.2, no surviving `Forbid` is `T` or `U`, and, under `violations = deny`, no obligation whose `in_force` is `T` or `U` has an instance that is `violated`, or `unknown` with `passed` set (§5.3), the verdict is `Permit`. |
| **L8** | **Skip soundness.** Evaluating more root atoms that are certainly `F` leaves the trace unchanged. |
| **L9** | **Preservation.** For a direct interpreter `I` over authored policies (`due2-architecture.md` §10), which completes the authored policy's unknown literals by the same rule (§6.4): `W3(W2(W1(p), r, s), c) = I(p, r, s, c)` whenever `verdict.exact` holds. The parts W1 rewrites — DNF disjuncts, including `xone`'s negated operands and `dprod:not` pushed inward — are identical or complementary to authored ones, so they denote the same variables, and the two sides enumerate the same completions. Opaque parts (§6.4) are variables of their own on the pipeline side and stay `U` in `I`'s tree. W1's rewrites are strong Kleene equivalences, so the tree is `U` exactly when its atoms' disjunction is, and both sides offer W3 the same choices (`decisions/0016`). A duty's condition is rewritten into clauses within its one atom, and the clauses of a kind are disjoined back into one finding (`decisions/0003`, `decisions/0028`). With `exact = false` the law weakens to refinement: a definite pipeline verdict equals `I`'s, and the pipeline may return `Indeterminate` where `I` decides. |
| **L10** | **Explicability** (§3.7, `decisions/0010`). Every atom, part, fact, and evidence id the trace names resolves in the trace, the evaluation's inputs, or the lineage. Every finding's truth is its predicate's connective over its `basis` truths (§5.1–§5.3). For a `fulfilled` finding the connective is per witness: a clause is the Kleene conjunction of its `witness_basis` truths under that witness, the witness satisfies the conditions by the disjunction of its clauses, and the finding is the disjunction of that value over the records named by its `evidence` parts, each conjoined with the record's `evidence` truth (§5.2, §5.3). Every atom in `verdict_basis` or `eliminated` has its findings and an authored source. |

---

## 9. Open decisions

Scope decisions — which ODRL constructs are admitted, including `invalid` — are registered in `due2-architecture.md` §11. Each row is tracked by the issue it names, and keeps its number when it is resolved, because issues and decision records cite rows by number.

| # | Decision | Section | Blocked on | Issue |
|---|---|---|---|---|
| 2 | Cross-policy combination default | §6.2 | A real multi-policy corpus | #4 |
| 3 | Declared preference among frontier alternatives | §6.3 | First incomparable frontier in practice | #5 |
| 4 | Monitoring question — the duties a party owes at a given time, independent of any request. Obligations in force for a request are covered by §5.2 and §6.1 | §1 | Obligation-monitoring requirements | #6 |
| 5 | Request match keys beyond `assignee` | §5.2 | Survey of real policies | #7 |
| 6 | Domain-aware completion over parts that read one fact or request field but are neither identical nor complementary (enumerated values, overlapping ranges, distinct values of a single-valued field such as the target). Identical parts that make the same read, and complementary constraint parts, already share a variable (§6.4, `decisions/0012`) | §6.4 | A real policy where the remaining over-approximation matters | #25 |
| 7 | Cases with several policies, needed to test cross-policy combination and errors in policies that do not apply | §6.2 | Case-format extension | #1 |
| 9 | Outcome of exceeding the read limit `max_reads`: refuse before a case is created, or evaluate with the excess `unresolved` | §3.3 | A real policy and request that approach it | #34 |

Rows 1 and 8 are resolved: row 1, the canonical encoding of collections (§2, `decisions/0007`), and row 8, a request without a target, whose relation part is `U` (§5.2; cases `oval-no-target-permission` and `oval-no-target-prohibition`).

Deadlines and the `violated` status are decided (§5.3). The *not-yet-owed* state of an instance whose occurrence or window is in the future is open (`due2-profiles.md` §9, #18).

---

## Appendix — Why tuples

Three representations were credible.

| | W2 (map) | W3 (join, group, fold) | Occurrence identity | Note |
|---|---|---|---|---|
| **Typed relations** | an atom is a row | native | explicit keys | Chosen. The model is the interface; any language or store can hold it. |
| RDF graph | an atom is a subgraph | SPARQL | skolem IRIs | Already the stage-1 form. A finding with truth and basis is n-ary and needs reification, and SPARQL filter semantics turn evaluation errors into false — the collapse `ways-of-working.md` §5.1 forbids. |
| Nested documents | natural | joins in application code | natural | Fits one policy; fights the cross-policy fold and the grouping into alternatives. |

Stage 2 projects the lifted stage-1 form into relations; nothing downstream of the parse sees RDF (§4).
