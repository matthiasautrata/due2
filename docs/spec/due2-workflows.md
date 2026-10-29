# due2 — Workflows and Reference Data Model

**Status:** Draft v0.62
**Companions:** `due2-architecture.md` (what due2 is and why) · `odrl-compound-to-atomic-normalization.md` (W1 stage 1, normative) · `due2-diagnostics.md` (every W1 diagnostic) · `ways-of-working.md` (how it is built).

**Changes in v0.62** (2026-10-29, #160): §3.5 lists an `eliminated` tuple only when its remover removes the entry in every completion in which the entry reaches the step that removes it, so a `prohibit-overrides` row needs its `Forbid` to survive its own policy in each completion where the removed candidate is one; §6.2 #2 points to it (`decisions/0052`). Earlier changes are in `docs/archive/changes.md`.

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
   W2  Evaluate                map: one truth value per entry · pure
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
- **W2 — Evaluate.** Given a request and a frozen SOTW, gives every relevant *entry*, an atom in one of its policies, a three-valued truth value and the parts that determined it. A *map*: an entry's finding depends on that atom, its policy's corpus, the request, and the SOTW — **never on another entry's finding, and never on another policy** (§3.3, `decisions/0050`).
- **W3 — Resolve.** Folds the findings into one verdict: forms candidates, applies conflict strategies, collapses and orders duty alternatives, derives the verdict. Reads the corpus and the findings — **never the request or the SOTW**.

The two *never* clauses are the boundaries. They make W2 parallel and indexable, and W3 testable without a world.

**The boundary that is not a workflow.** Assembling and freezing the SOTW is impure — it fetches, retries, waits — and sits outside all three workflows. W2 reports which state properties it read (§5.4); those with no fact in the SOTW are the shell's cue to resolve them, record the answers in the case, and run W2–W3 again. That loop is orchestration, not semantics. By L3 (§8) it can change a verdict only by supplying missing information.

**One question here, two in the architecture.** `due2-architecture.md` §6.3 separates the access question (*may this request proceed?*) from the monitoring question (*what does this party owe now?*). Both consume W1's corpus and reuse W2's matching, constraint, and fulfilment machinery. They differ in the predicate W2 applies to root atoms and in the reduction W3 performs. This document specifies the access question. Monitoring is **[O]** (§9).

---

## 2. Conventions **[D]**

**Relations.** All data is held as collections of tuples. Each relation declares a key, written before `|`; set semantics apply to the key only. A relation written without `|` is keyed by all of its fields; one with an empty key holds exactly one tuple. Optional fields are written `field?`, and a key field may be optional.

**Identity.** Occurrence identity lives in ids. Two tuples with equal content and different ids never merge — the property a naïve set-of-tuples model loses (`due2-architecture.md` §3.1).

**Collections.** Data comes in six collections — Corpus, Request, SOTW, Reads, Trace, and Lineage. Each is identified by the digest of its canonical form, and tuples inside a collection do not repeat its id.

**Value types.**

| Type | Meaning |
|---|---|
| `Id` | IRI, compared by equality only. An id that no author chose is minted: a UUID IRI with a random version 4 UUID (RFC 9562), minted once, when its thing is created (`odrl-compound-to-atomic-normalization.md` §5, `decisions/0038`). |
| `Term` | An `Id`, or a literal `(lexical, datatype[, language])`. Exact numbers are lexical forms with a numeric datatype; there is no floating-point domain. |
| `Instant` | A literal of datatype `xsd:dateTime` with a timezone (`decisions/0024`). |
| `Truth` | `T`, `F`, `U` — Kleene strong three-valued logic. |
| `Enum` | A closed set of strings, listed in the field's row of §3 or in the section that row cites. |
| `Flag` | `true` or `false`. |
| `Count` | An integer within ±2^53. |
| `Digest` | `sha256:` followed by 64 lowercase hex digits: the SHA-256 of the bytes that the field's row names, written as a collection id is (below). |
| `String` | Text that is neither an IRI nor a literal, such as an RFC 5545 RRULE. |

**Canonical form.** Each collection has exactly one canonical serialisation, and its digest is the collection id. **[D]** (`decisions/0007`):

- **Encoding.** A collection is a JSON object keyed by relation name, serialised by RFC 8785 (JCS) to UTF-8. Each value is the relation's tuples, as a JSON array; a relation with no tuples is omitted, so a collection with no tuples is `{}`. A tuple is a JSON object keyed by field name; absent optional fields are omitted. Relation and field names are ASCII, so JCS orders them by code point.
- **Order.** Within a relation, tuples are sorted by key, field by field in declaration order, each field by Unicode code-point order of its serialised value, with an absent optional field before any value. A relation with an empty key holds one tuple.
- **Values.** An `Id`, `Truth`, `Enum`, `Digest`, or `String` is a JSON string. A literal is the object `{"v": lexical, "t": datatype}` plus `"l": language` when present; an `Id` is never an object, so the two cannot collide. A number is never a JSON number — it is a literal with a numeric datatype. A `Count` is a JSON integer within ±2^53, and a `Flag` a JSON boolean. No floating point.
- **Digest.** The collection id is `sha256:` followed by the lowercase hex SHA-256 of the canonical bytes.

No collection is RDF, and W1 emits none: stage 1's output stays inside W1 (`odrl-compound-to-atomic-normalization.md` §4, `decisions/0037`).

---

## 3. Reference data model

Each relation is written as §2 declares it. A field is an `Id` unless a value type of §2 follows its name, as in `at: Instant`.

### 3.1 Corpus — output of W1

```text
policy            (policy_id | conflict: Enum, version)
policy_profile    (policy_id, profile)
atom              (atom_id | effect: Enum, action, relation?, relation_value?, source_rule, priority?: Count)
atom_party        (atom_id, function | party)
constraint        (constraint_id | left_operand, operator, datatype, unit?, source: Enum, property, range?, operand_unit?, cardinality: Enum)
constraint_value  (constraint_id, value: Term)
constraint_scheme (constraint_id, scheme)
atom_constraint   (atom_id, constraint_id, scope: Enum)
duty_constraint   (atom_id, clause: Count, constraint_id, scope: Enum)
edge              (parent_id, child_id)
root              (atom_id, policy_id)
duty              (atom_id | source_duty, scope: Enum, deadline?: Term, recurrence?: String)
closure           (policy_id, relation, narrower, broader)
diagnostic        (policy_id, code: Enum, ref, detail?)
```

| Field | Meaning |
|---|---|
| `policy.conflict` | `Enum {prohibit, perm, invalid}` — the source policy's ODRL conflict strategy. An absent term takes a selected profile's declared default first, then `invalid` (`odrl-compound-to-atomic-normalization.md` §3); W1 makes the result explicit. The policy's class (Set, Offer, Agreement, or a profile's subclass of one) is not kept: W1 stage 1 carries it (`odrl-compound-to-atomic-normalization.md` §4), and no workflow reads it (`decisions/0031`). |
| `policy.version` | The version of the authored policy: an id that the policy store mints when it stores the document (`put_policy`, `due2-platform.md` §2.3). Versions are told apart by id, never by a number that has to be ordered. W2 and W3 never read it. Explanation uses it to find the policy's lineage (§3.6). **[D]** (`decisions/0038`) |
| `policy_profile` | Each profile the policy names with `odrl:profile`, one tuple per IRI. A policy may name none, or several. |
| `atom.effect` | `Enum {Permit, Forbid, Oblige}` — one required field (`due2-architecture.md` §3). |
| `atom.action` | The atom's single action, unrefined. Refinements are constraints with scope `action`. |
| `atom.relation`, `relation_value` | At most one relation, `odrl:target` or `odrl:output`, and its value. |
| `atom.atom_id` | The id of the rule the atom comes from, or a minted one. Stage 1 gives each rule it emits an id (`odrl-compound-to-atomic-normalization.md` §5.1): its authored identity when the rule is named and not expanded, and an id minted for it otherwise, for an anonymous rule and for each atom of a rule it expands. An atom that is the only one stage 2 makes from its rule, and to which stage 2 binds nothing, keeps that id. Stage 2 mints one for every other atom: each disjunct atom of a `Permit` or `Forbid` atom's constraint (§4), and a duty atom as `duty.atom_id` says. What a minted id came from is in `source_rule` and the lineage (§3.6). A named rule's id never includes the policy that states it: the policies an atom belongs to are its `root` tuples, so a named permission or duty that several policies state is one atom, and the ids minted for its parts are minted once, when it is first published (§4, *Several policies are one corpus*). An anonymous root rule is part of its policy alone, so it is never shared. An anonymous node under a named parent is shared exactly when its parent is, as part of what the parent says. Otherwise sharing is stated by naming. **[D]** (`decisions/0036`, `decisions/0038`) |
| `atom.source_rule` | Required provenance: the authored rule the atom comes from, which drives explanation. Full lineage is a separate collection (§3.6). |
| `atom.priority` | Read by no rule: prohibit-overrides is the only cross-policy rule (§6.2). A priority-based cross-policy strategy would read it (§9). |
| `atom_party` | At most one party per function predicate per atom: `assignee`, `assigner`, `informedParty`, … |
| `constraint` | What a constraint asks, wherever it is attached: its left operand, its operator, the datatype its right operand is read as, and its unit. Its id is stage 1's id for the constraint node, by the rules of `atom.atom_id`; a constraint stage 2 creates, such as a negation that `xone` elimination adds (§4), gets a minted id. A named constraint that several rules use is one tuple, attached to each. **[D]** (`decisions/0036`) The tuple also carries the binding of its left operand, as W1 resolved it from the policy's profile layers (`due2-profiles.md` §2, §3), so that W2 needs nothing but the corpus to read the operand's value (`decisions/0047`). A constraint stage 2 creates has the binding of the constraint it is made from. The binding's allowed operators are not carried: W1 rejects a constraint whose operator its binding does not allow (`OperatorTypeMismatch`, `due2-diagnostics.md` §3), so every operator in a corpus is allowed. |
| `constraint.source`, `property` | Where W2 reads the left operand's value, `Enum {request, state, context, witness}` for the binding's `dprod:requestSource`, `dprod:stateSource`, `dprod:contextSource`, or `due2:witnessSource` (`due2-profiles.md` §3), and the property it reads there: a `request_param` and its `request_param_value`, a state `fact`, or a witness's `evidence_param` and its `evidence_param_value`, keyed by the property (§3.2, §3.3, §5.3). For `context`, `property` names the built-in: `dprod:agent`, `dprod:clock`, or `due2:actionTime` (`due2-profiles.md` §3). The binding belongs to the constraint rather than to the operand. A higher layer may rebind an operand for one policy (`due2-profiles.md` §2), so two policies may read one operand differently, while a named constraint that several policies use is one tuple. A constraint therefore has one binding, and a named constraint that two policies bind differently is described differently by their corpora, so publishing the second is rejected with `IdentityConflict` (§4). **[D]** (`decisions/0047`) |
| `constraint.range` | The binding's `rdfs:range`, the kind a left value must have: W2 makes a value of another kind `invalid` (`due2-profiles.md` §3, *Resolution*). Absent when no layer states a range, which admits a value of any kind. It is the left operand's type, and `datatype` is the right operand's. |
| `constraint.operand_unit` | The binding's `due2:unit`, the unit of every value read for the operand, absent when no layer that owns the type states one (`due2-profiles.md` §3, *Units*). It is the left operand's unit, and `unit` is the right operand's, the constraint's own `odrl:unit`. W1 rejects a constraint whose two units differ, so when both are present they are equal. A constraint with a `unit` and no `operand_unit` is a misfit for every value (§5.4). **[D]** (`decisions/0049`) |
| `constraint.cardinality` | `Enum {one, set}`: whether several values for the operand are a `conflict` or a set (`due2-profiles.md` §3). W1 writes the default, `one`, when no layer states it. |
| `constraint_scheme` | The concept schemes of the left operand, the union of every layer's `due2:conceptScheme` (`due2-profiles.md` §4), one tuple per scheme. An operand with no scheme has no tuple. |
| `atom_constraint` | The constraints of a `Permit` or `Forbid` atom, a conjunction: W1 has made each disjunct of the authored constraint an atom of its own (§4). `scope` is `Enum {rule, action, relation, party:<function>}`, what the constraint refines where it is attached. An action refinement is scope `action` on *this* atom. It never attaches to the action vocabulary term globally. |
| `duty_constraint` | The constraints of an `Oblige` atom, in clauses, with `scope` as in `atom_constraint`. A duty stays one atom, and its condition is kept in clauses: the constraints with one `clause` number form a conjunction, all of one kind, guard or witness condition, and a kind's value is the Kleene disjunction of its clauses (§5.2, §5.3). The clause numbers are W1's choice: only which constraints share a number matters. **[D]** (`decisions/0028`, `decisions/0036`) |
| `constraint_value` | Right-operand values: one tuple for a scalar, several for a set operand, whether the policy writes it as an RDF list or as repeated values (`due2-profiles.md` §4). |
| `edge` | Parent atom → child duty atom. |
| `root` | The root atoms of W1 stage 1 (`odrl-compound-to-atomic-normalization.md` §6.4), each with the policy it roots: every `Permit` and `Forbid` atom and every policy-level obligation, with one tuple for each policy that states it, however many policies are evaluated together (§4). `root.policy_id` drives the per-source conflict fold in W3 (§6.2) and decides which requests put an obligation in force (§5.2). An atom's *policies* are those its `root` tuples name and, for the child of an edge, its parents' policies. An *entry* is an atom in one of its policies, written `(atom, policy)`. A policy's *data space* is everything W2 reads for its entries: the policy's own corpus tuples, which hold its edges and those of the profile modules it names, and the world, which is the request and the SOTW (§3.3). W2 gives each entry its own findings, read in its policy's data space and never in another policy's (§5), and W3 folds entries (§6). A precondition, remedy, or consequence that no policy states as an obligation has no `root` tuple. Stored, because it is not derivable: one named duty can be both an obligation of its policy and the precondition of a permission, so a root can also be the child of an edge. **[D]** (`decisions/0036`, `decisions/0050`) |
| `closure` | The direct hierarchy edges of one policy's data space, keyed by that policy: those the policy declares and those of the profile modules it names — `odrl:includedIn` between actions, typed `odrl:partOf` between assets or parties and their collections, `rdfs:subClassOf`, and `rdf:type` edges — those that type collections and those of individuals an `isA` constraint can compare. Between concepts there are two relations. `skos:broader` is the hierarchy, and a `skos:narrower` triple is recorded as the inverse `skos:broader` edge. `skos:inScheme` relates a concept to each scheme it is in, whether the input states that as `skos:inScheme`, `skos:topConceptOf`, or `skos:hasTopConcept` (`due2-profiles.md` §6). ODRL's own action hierarchy is one such module (`profiles/odrl-actions.ttl`). W1 writes every edge under the policy it normalises, so two policies that state one edge have a tuple each, and the union of their corpora keeps them apart (§4). A hierarchy comparison for an entry in policy `P` reads `P`'s tuples and the SOTW's `closure`, never another policy's (§3.3). **[D]** (`decisions/0050`) |
| `duty` | For every `Oblige` atom: the authored duty it instantiates, and its instance scope `Enum {member, grant}`. Scope defaults to `member`. W2 derives the duty instance from the atom (§5.3). |
| `duty.atom_id` | A duty atom stands for one rule of stage 1 under one binding. It keeps stage 1's id (`atom.atom_id`) when stage 2 binds nothing into it: no inherited party role and no parameter value (§4). One that stage 2 binds gets a minted id, and its binding, the party roles it inherited, is read from its `atom_party` tuples and the lineage (§3.6, `atom_rule`). Stage 2 makes one atom for each rule and binding, whatever parent or policy states it. So a named duty bound identically in two places is one atom, found again by its duty and its binding when a later policy states it (§4, *Several policies are one corpus*), and one bound differently in two places, such as with the inherited assignees Alice and Bob, is two atoms. **[D]** (`decisions/0032`, amendment of 2026-10-25; `decisions/0038`) |
| `duty.deadline` | The authored duty's timing, projected by W1 stage 2 onto every atom it instantiates: an `xsd:dateTime` term with a timezone (absolute) or an `xsd:duration` term (relative to the instance's activation). W2 resolves it per instance (§5.3). |
| `duty.recurrence` | An RFC 5545 RRULE string; the duty is owed once per occurrence. W2 derives the instances (§5.3). |
| `diagnostic` | A warning W1 accepted the policy with: its code (`due2-diagnostics.md` §3), the node it is about, and, for a warning that names a second thing, that thing as `detail`: an `AnonymousEntity` node's Rule, or an `IgnoredPredicate`'s predicate. `ref` and `detail` are, in order, the items of the warning's `ref` list in its JSON form (`due2-diagnostics.md` §1). A node with two ignored predicates has two tuples. Only warnings appear, because an error leaves no corpus (§4). W2 and W3 never read it; it is in the corpus so that the corpus digest, and with it the evaluation id, records the reading the policy was normalised under. |

Derived, not stored:

- **guard / witness condition** of a duty's constraint, from its bindings (§5.2).
- **role(d)** of a child follows from its parent's effect: `Permit` → precondition, `Forbid` → remedy, `Oblige` → consequence (`due2-architecture.md` §3).

Invariants, established by W1 and trusted downstream: `edge` is acyclic; every child is an `Oblige` atom; every `Permit` and `Forbid` atom has a `root` tuple; an `atom_constraint` names a `Permit` or `Forbid` atom, and a `duty_constraint` an `Oblige` atom; in every corpus tuple, a `policy_id` names a `policy`, an `atom_id`, `parent_id`, or `child_id` names an `atom`, and a `constraint_id` names a `constraint`; an atom has `relation_value` exactly when it has `relation`; `Permit` and `Forbid` atoms carry `relation = odrl:target`.

### 3.2 Request

```text
request              (| reference?: String, action, target?, at: Instant)
request_party        (function | party)
request_param        (name)
request_param_value  (name, value: Term)
```

`reference` is the caller's identifier for the request; it also identifies grant-scoped duty instances (§5.3). `at` is the instant of the proposed action, an `xsd:dateTime` with a timezone — validity time, what ODRL's `dateTime` constrains. `target` may be absent — a request for an action on no named asset; every relation part is then `U` (§5.2), never `F`. The party with `function = assignee` is the subject — the party seeking to act. A request may name other parties, such as a recipient, under other function predicates. `request_param` names each property of the normalised request that request-source operands read (`due2-profiles.md` §3), by its IRI: purpose, record count, and so on. Its values are in `request_param_value`. A parameter with no values is the empty set when the operand that reads it is set-valued, and `missing` otherwise; a property with no `request_param` is `missing` too. A parameter has no status, since the request is what its caller states: `invalid` and `conflict` follow from its values and the operand's binding (`due2-profiles.md` §3, *Resolution*; `decisions/0051`). Nothing else is visible — no credentials, headers, or session state unless a profile exposes them here.

**`at` across a case's evaluations [D]** (`decisions/0030`). Each evaluation of a case names the request it ran with (§7.1). That request is the case's request, with `at` moved to the evaluation's `effective_at` when the case's `at` is earlier. A later `at`, as for an action proposed for a future date, is kept. Every other field is unchanged, so `reference`, and with it every grant-scoped instance (§5.3), carries over. The orchestrator (`due2-platform.md` §2.6) builds every access evaluation's request this way, so its `at` is never earlier than its `effective_at`: an action can no longer be taken at an instant that has passed. The evaluator does not compare the two: given an earlier `at`, it answers for that instant. So a payment made after a time window has closed cannot fulfil the window's permission at a later re-evaluation, while a payment made in time and recorded late still counts (`due2-reevaluation-moves-at`).

### 3.3 SOTW

```text
sotw                 (| effective_at: Instant)
fact                 (property, source | status: Enum)
fact_value           (property, source, value: Term)
evidence             (evidence_id | occurred_at: Instant, actor, action, object?, issuer?, discharges_duty?, discharges_reference?: String)
evidence_param       (evidence_id, name)
evidence_param_value (evidence_id, name, value: Term)
activation           (atom_id, policy_id | at: Instant)
closure              (module, relation, narrower, broader)
closure_answer       (module, entity, source | status: Enum)
```

| Relation | Meaning |
|---|---|
| `sotw.effective_at` | The instant at which the world is observed, an `xsd:dateTime` with a timezone — decision time. Evidence counts only if it occurred no later. |
| `fact` | One source's answer for one property of the normalised world-state node, which state-source operands read (`due2-profiles.md` §3), and its `status`: `Enum {resolved, missing, invalid, conflict, unresolved}`, never collapsed. *Missing*: the source says no value exists. *Unresolved*: the source could not be asked or did not answer. `source` names who answered: a service, or a person the orchestrator asked (`due2-platform.md` §1.4). W2 reads the combination of a property's admitted answers (*Several sources*, below). Whoever assembles the SOTW flattens onto this node everything the policies read — "the requester's department" becomes one property — so computing values is the assembler's job, never W2's. |
| `fact_value` | The source's values: exactly one when `resolved` — for a set-valued operand, its members, of which there may be none — two or more when `conflict`, none otherwise. |
| `evidence` | A record that an action was performed: when, by whom, which action, on what, and who attests it (`issuer`). Approvals, payments, notifications. `discharges_duty` and `discharges_reference`, both or neither, name the grant the evidence was submitted against: an authored duty and a request's `reference` (§5.3). Fulfilment is derived from evidence and never stored as a flag. Signatures and provenance are verified before the SOTW is frozen; W2 only compares `issuer` against the duty's attester (§5.3). |
| `evidence_param` | Parameters of the performed action — an amount, a recipient — the counterpart of `request_param` for a proposed action. Read only by witness-source operands (`due2-profiles.md` §3). |
| `evidence_param_value` | A parameter's values, as `request_param_value` holds a request parameter's (§3.2). |
| `activation` | When the instance of a duty entry was first owed (§3.1, `root`). Derived, not observed: the evaluation that first finds the instance owed records it in the case (`due2-profiles.md` §7). It is keyed by the entry's policy because each policy reads the duty's guards in its own data space, so two policies that oblige one duty may first owe it at different times (`decisions/0050`). It anchors relative deadlines and recurrence occurrences (§5.3). An instance of one occurrence of a recurring duty is activated at that occurrence, which needs no record. |
| `closure` | Direct hierarchy edges from the world rather than from policies — current team membership, say — in a named module: the union of the edges of every answer in `closure_answer`. For an entry in policy `P`, W2 uses the transitive closure of these together with `P`'s corpus `closure`: `a ⊑ b` holds when `a = b` or a chain of edges leads from `a` to `b`. Closure is closed-world over the declared edges once every answer is in: for `a ≠ b` with no such chain, `a ⊑ b` is `U` when some answer is `unresolved` for `a` or for an entity that a chain of edges reaches from `a`, and `F` otherwise (`decisions/0048`). Those answers count because the edges they would have held are the only ones that could extend a chain from `a` towards `b`; an answer for `b` or for anything not above `a` cannot. An answer counts in any module, including one that holds no edges of the comparison's kind, such as the asset module for a party: that is sound, since its edges could only add chains, and it can cost an `Indeterminate` where a definite verdict was right. A module with no registered source has no answers, and the policy's own edges are then all there is. Scheme membership is the exception: a request concept with no `skos:inScheme` edge to any of its operand's schemes is out of scheme, and its constraint is `U`, not `F` (`due2-profiles.md` §4). Only edges on paths up from the entities a part compares — the request's parties and target, the values a hierarchy operator compares, the concepts a concept-scheme operand compares — can decide a part, so only those, and those concepts' scheme memberships, are recorded (*Plan, then evaluate*, below). |
| `closure_answer` | One source's answer for the edges on the paths up from one entity in one module, and its `status`: `Enum {resolved, unresolved}`. *Resolved*: the source answered with the edges it holds, possibly none, which is how a module that does not hold the entity answers. *Unresolved*: the source could not be asked or did not answer, and the answer holds no edges. Each answer is an event on the case, and a later answer from the source for the module and entity replaces its earlier one (§7.1, `decisions/0043`, `decisions/0048`). A hierarchy part that is `U` because of an `unresolved` answer is opaque (§6.4). |

**The SOTW is the case's snapshot [D].** An evaluation reads only what its case has recorded: the part of the world the case cares about, as of `effective_at`. Every fact, world-edge answer, piece of evidence, and activation is an event on the case, carrying the time it held in the world and the time it was recorded (§7). Its flattened properties describe one request's subject and target, so a SOTW is not reused for a request with a different subject or target.

**Plan, then evaluate [D].** W2 never asks for anything. Every value it can consult is named by an operand binding (`due2-profiles.md` §3) or by a hierarchy comparison in the corpus, so a pure sweep lists them before anything is fetched:

```text
plan : Corpus × Request → Reads
```

`Reads` is the collection of what an evaluation may read beyond the corpus and the request **[D]** (`decisions/0047`, `decisions/0048`):

```text
read_param           (property)
read_state           (property)
read_edges           (module, entity)
read_fact_edges      (module, property)
read_evidence_edges  (module, field: Enum)
read_witness_edges   (module, property)
```

| Relation | Meaning |
|---|---|
| `read_param` | A request parameter that a constraint with `source` `request` reads (§3.1). The request carries it or not, so nothing is fetched. It names what a requester should supply: a parameter the request lacks is `missing`, and its constraint is `U` (§5.4). |
| `read_state` | A state property that a constraint with `source` `state` reads. The shell asks every source registered for it (*Several sources*, below). |
| `read_edges` | A world module and an entity whose edges, on the paths up from it in that module, can decide a part. The entity is known before anything is fetched: a party or the target of the request, a request parameter's value, the subject that `dprod:agent` names, or a value in the corpus, such as a `hasPart` constraint's right operand. |
| `read_fact_edges` | A world module and a state property whose values a hierarchy comparison reads: the edges above each value of the property's recorded facts. The values are known only once the facts are, so the shell fetches these edges after the facts. It is a relation of its own so that each relation has one meaning and no field that is present exactly when another is absent. |
| `read_evidence_edges` | A world module and an evidence field, `Enum {issuer, actor}`, whose value a duty compares under the party closure: `issuer` when some duty atom has an attester, `actor` when some duty atom has a bearer (§5.3). The values are known only once evidence is submitted, so the shell fetches these edges when it records evidence, before it evaluates. The module is always `due2:partyHierarchy`; it is a field, as in the other relations, because sources register by module (`due2-platform.md` §2.4). |
| `read_witness_edges` | A world module and a witness-source property whose values a hierarchy comparison reads: the edges above each value of the property in each piece of evidence, fetched when the evidence is recorded. |

**World modules [D]** (`decisions/0047`). A world module is named by the kind of hierarchy it holds, from a closed set, so the corpus names no module: the kind of comparison names it. Action hierarchies come from the corpus alone.

| Module | Holds | Entities whose edges `plan` lists |
|---|---|---|
| `due2:partyHierarchy` | `odrl:partOf` edges between parties and party collections, and the `rdf:type` edges of the collections on their paths | each request party whose function is a match key that some `atom_party` tuple names (§5.2; `assignee` in v1); the request subject, when a duty atom has a bearer (§5.3); each value on the narrower side of an `isPartOf` or `hasPart` constraint; an evidence `issuer` or `actor` (`read_evidence_edges`) |
| `due2:assetHierarchy` | `odrl:partOf` edges between assets and asset collections, catalog classifications included (`due2-platform.md` §2.5), and the `rdf:type` edges of the collections on their paths | the request's `target`; each value on the narrower side of an `isPartOf` or `hasPart` constraint |
| `due2:classHierarchy` | `rdf:type` and `rdfs:subClassOf` edges | each left value of an `isA` constraint |
| a concept scheme's IRI | the `skos:broader` and `skos:inScheme` edges of the scheme's concepts | each left value of a constraint whose `constraint_scheme` names the scheme |

Only the narrower side of a `⊑` needs the edges above it. `isPartOf` asks whether each left value is ⊑ some right value, and `hasPart` whether each right value is ⊑ some left value (`due2-profiles.md` §4), so the narrower side is an `isPartOf` constraint's left values and a `hasPart` constraint's right values, which are corpus constants. Such a value may be a party or an asset, and the constraint does not say which, so `plan` lists it in both modules. That is sound because a module that does not hold the entity answers with no edges, and an edge that is not there does not hold (`closure`, above). A left value from a state property is listed in `read_fact_edges` with the property, and one from a witness-source property in `read_witness_edges`, in each module that the table's row for its comparison names; every other value is an entity of `read_edges`.

The module is a label for fetching, not for reading. W2 reads one hierarchy per policy: for an entry in policy `P`, the union of every module's `closure` tuples in the SOTW with `P`'s tuples in the corpus `closure`. That union is the hierarchy of `P`'s data space (§3.1, `root`). No entry reads another policy's tuples, so an edge that one policy states never reaches another policy's rules (`decisions/0050`). A comparison does not choose a module; the entities it compares and the `rdf:type` edges on their paths decide which edges it follows.

The shell fetches what the case lacks, records the answers, and calls W2 only once every planned item is in the case. A lookup that fails is recorded as `unresolved`, and one that finds no value for a state property as `missing`, so "never looked up" cannot reach W2. W2's `read` is within the plan, and a read outside it is a defect. Evidence itself is not planned: it reaches the case when it is submitted, and evidence the case does not hold is not yet performed (§5.3). The edges above its values are planned, by `read_evidence_edges` and `read_witness_edges`, and fetched when it is recorded (`decisions/0048`).

**Answers, not extensions [D].** The case records the answer to the question an evaluation asks — a property's value, the edges above an entity — never the dataset the source computed it from. Membership of a group with a billion members is one fact. A source that can only answer in bulk is queried by the shell, which records the answer and, on its event, the version of the source it came from (§7.1, `decisions/0044`), as the ledger pins normaliser versions (`due2-architecture.md` §7); the bulk data is a cache, not part of the case. A positive hierarchy answer may carry its path as justification; a negative one has none shorter than the closure, and needs none. Several cases may read the same fact: each records it as it read it, and storage may share it.

**Read limit [D]** (`decisions/0048`). The plan is fixed by the corpus and the request, and is known before any fetch, as W1's limits are known before expansion (`due2-architecture.md` §4). A shell limit, `max_reads`, which the deployment sets, bounds the number of its tuples, and the shell refuses a request whose plan exceeds it, before a case is created. A `read_fact_edges`, `read_evidence_edges`, or `read_witness_edges` tuple counts once. The answers it fans out to are not bounded: the edges above each value of a fact, or of each piece of evidence, are known only once those are recorded, when the case already exists.

An evaluation's SOTW is frozen once W2 runs; a fact that changes later is a new event, which the next evaluation reads (§7.1). Keeping a value current is the SOTW service's job: when the value changes in the world, the service supplies the new one, and a re-evaluation asks no source again (`decisions/0040`).

**Several sources [D]** (`decisions/0040`, `decisions/0045`). Each source's answer is kept as it came, and W2 combines the answers of each property into one status and one set of values. Every answer a case records is admitted: the orchestrator records a fact answer only from a source registered for the property, and a person's answer only when it asked that person (`due2-platform.md` §2.4). W2 therefore reads no list of admitted sources.

- *Answers with values.* These are the answers whose status is `resolved` or `conflict`. If there are any, the combined status is `resolved` when all of them are `resolved` with the same values, compared as sets of written terms (§2), and `conflict` otherwise; the combined values are theirs, and answers without values are ignored. A `resolved` answer for a set-valued operand with no members counts as one with values.
- *No answer with values.* The combined status is `unresolved` if any answer is `unresolved`, otherwise `invalid` if any is `invalid`, otherwise `missing`.
- *No answer at all.* A property with no `fact` is `unresolved` (§5.4).

The shell asks every registered source for a planned property, and records a source that cannot be asked as `unresolved`, so a registered source does not drop out of the combined status unseen.

The part's truth value, and the `status` of `unknown_part` and `witness_part` (§3.5), are those of the combined status. Answers without values cannot outweigh one with values, because they give the part nothing to compare; two different values cannot both be right, so they are a `conflict`.

### 3.4 Constants **[D]** (`decisions/0045`)

An evaluation has no parameters beyond its three inputs, the corpus, the request, and the SOTW. What a configuration would choose is fixed by this document or authored in the policy:

| Constant | Value | What it bounds or fixes |
|---|---|---|
| `max_mixed` | 8 | The mixed variables W3 completes jointly; beyond it they are completed independently (§6.4). |
| `max_frontier_vars` | 8 | The relevant unknowns over which W3 enumerates every assignment to find the frontier; beyond it the frontier is not known to be complete (§6.4). |

Both change the trace, so they are part of what this document's version means: L1 (§8) requires the same trace bytes from the same inputs under the same version. The cross-policy rule is prohibit-overrides (§6.2), and a policy's own strategy is its `odrl:conflict`. Whose evidence counts for a duty is the duty's attester (§5.3). A preference among frontier alternatives would be authored in the policy (§6.3, #5).

### 3.5 Trace — output of W2 and W3

```text
evaluation     (| corpus_id: Digest, request_id: Digest, sotw_id: Digest)
finding        (atom_id, policy_id, predicate: Enum | truth: Truth)
basis          (atom_id, policy_id, predicate: Enum, kind: Enum, ref | truth: Truth)
unknown_part   (atom_id, policy_id, predicate: Enum, kind: Enum, ref, input | status: Enum)
witness_basis  (atom_id, policy_id, witness, ref | truth: Truth)
witness_part   (atom_id, policy_id, witness, ref | input, status: Enum)
read           (property)
instance       (atom_id, policy_id, occurrence?: Instant | status: Enum, passed: Flag)
eliminated     (atom_id, policy_id, by_atom, by_policy, rule: Enum)
alternative    (alt_id: Count, permission_id, policy_id)
alt_duty       (alt_id: Count, duty_id)
dominated      (alt_id: Count, by_alt: Count)
verdict        (| value: Enum, frontier_complete: Flag, exact: Flag)
verdict_basis  (atom_id, policy_id, role: Enum)
verdict_range  (| low: Enum, high: Enum)
diagnostic     (policy_id, code: Enum, ref, detail?)
```

| Relation | Computed by | Meaning |
|---|---|---|
| `evaluation` | W2 | The three input collection ids, each the digest of its collection's canonical bytes (`decisions/0007`), computed from the inputs `decide` receives (`decisions/0041`). The evaluation id is the digest of this tuple — derived, not stored. The case is not an input: the ledger links each evaluation to its case (§7), so the trace depends on content alone. |
| `finding` | W2 | One truth value per evaluated entry and predicate — `applies`, `in_force`, `owed`, or `fulfilled` (§5.1). An entry is an atom in one of its policies (§3.1, `root`), and its finding is read in that policy's data space (§3.3), so an atom that two policies state has a finding in each, and the two may differ. **[D]** (`decisions/0050`) |
| `basis` | W2 | The parts that *determine* the finding, keyed by the finding's entry and predicate. The parts of a duty's witness conditions are in `witness_basis` instead. `kind ∈ {action, relation, party, constraint, evidence, fact}`; `ref` is the constraint, evidence, state property, or function; `truth` is that part's value. An `F` finding names the part that failed. |
| `unknown_part` | W2 | Every `U` part of every finding W2 produces whose value is `T` or `U`, determining or not, except the parts of a duty's witness conditions, which are in `witness_part`: its entry, the finding's predicate, the part's `kind` and `ref` as in `basis`, the `input` it reads (`odrl:target`, a party function, or an operand's property; for an `evidence` part, the duty's party function that its comparison reads, §5.3), and that input's `status`: `missing`, `invalid`, `conflict`, `unresolved`, or `misfit`: a `resolved` value that does not fit the operator, or any value read by a constraint whose unit its binding does not declare, which no value fits (§5.4, `decisions/0049`). A part has one row for each input that makes it `U`, so `input` is part of the key: an `evidence` part whose comparisons with the bearer and with the attester are both `U` has two rows (§5.3). A part that reads an `unresolved` state property is completed, and every other part is opaque (§6.4), including a hierarchy part that is `U` because an answer for its narrower side is `unresolved` (§3.3, `closure`). An `F` finding's `U` parts are not named: none of them can change it, and an index may skip a certainly-`F` entry (§5.5), so naming them would make the relation depend on the index. Root atoms, and a duty's clauses, are the disjuncts of the constraint DNF, unsimplified, with negation pushed to the leaves and `xone` expanded (§3.1, §4 stage 2, §6.4), so a `U` leaf of the authored tree is named exactly when some root atom or duty clause that reads it is `T` or `U`, even if the node above it is decided: in `or(a, u)` with `a` true, `u` is named; in `and(a, u)` with `a` false, it is not. **[D]** (`decisions/0016` and its amendment, `decisions/0028`) |
| `witness_basis` | W2 | The parts of a duty's witness conditions that determine its `fulfilled` finding, for each witness (§5.3): `witness` is the witness's `evidence_id`, and `ref` is the constraint. Every part of a witness clause is a constraint that reads the witness (§5.2). The basis rule of §5.2 applies per witness: for `T`, every part of each clause the witness satisfies, so a witness that satisfies none has no rows; for `F`, the failing parts of every clause, for every witness; for `U`, the `U` parts of each clause that is not `F` for that witness. **[D]** (`decisions/0035`) |
| `witness_part` | W2 | The `U` parts of a duty's witness clauses, when the duty's `fulfilled` finding is `T` or `U`: its entry, the witness, the constraint `ref`, and the `input` and `status` as in `unknown_part`. A part is named under a witness exactly when a clause that reads it is `T` or `U` for that witness, the liveness rule of `unknown_part` applied per witness. One constraint read against two witnesses is two rows, each with the status of what it read. **[D]** (`decisions/0035`) |
| `read` | W2 | Every state property consulted, determining or not. What the ledger pins (`due2-architecture.md` §7); also the dependency index re-evaluation may use. |
| `instance` | W2 | One tuple per evaluated duty instance (§5.3): its entry, the occurrence instant `t` for an instance of a recurring duty (absent otherwise), its status `Enum {fulfilled, outstanding, violated, unknown}`, and `passed`, whether its deadline has passed: the instance has an effective deadline `D` and `effective_at > D` (§5.3). The entry and the occurrence are the instance's key within a case (§5.3), and `activation` records when an entry's instance was first owed (§3.3). |
| `eliminated` | W3 | An entry of a candidate or prohibition removed (§6.2, *Entries*) — by conflict resolution, or by a violated precondition duty instance (§6.1, rule `violated_precondition`, one tuple for each entry) — the policy of the entry, the entry that removed it (`by_atom` in `by_policy`), and the rule applied: the policy's `conflict` value within a policy, `prohibit-overrides` across policies (§6.2), or `violated_precondition`. **[D]** (#57) `by_atom` is one tuple per remover: under `prohibit` and `prohibit-overrides`, each `T` `Forbid` that eliminates the candidate; under `perm`, each `T` candidate that eliminates the `Forbid`; under `invalid`, each `T` candidate and `T` `Forbid` of the void policy other than the atom itself; under `violated_precondition`, the violated duty. `by_policy` is the entry's own policy, except under `prohibit-overrides`, where it is the policy of the `Forbid` entry that removes it. **[D]** (`decisions/0052`) Under unknowns, a tuple is listed only when its remover removes the entry in every completion (§6.4) in which the entry reaches the step that removes it: under `violated_precondition`, where the entry applies; under a conflict rule, where it is a candidate or, for a `Forbid`, applies. A `U` entry can be removed (`decisions/0011` #4), but the removal may not depend on an unknown. Within a policy, a tuple holds when its remover takes part in every completion: a `T` `Forbid`, or a `T` candidate that no completion closes (§6.1). Under `prohibit-overrides`, the `T` `Forbid` entry must also survive its own policy's fold in each completion in which the removed entry is a candidate. A `Forbid` is not listed as a remover of that candidate when its own policy removes it in one such completion, such as by a `U` candidate under `perm`. |
| `alternative`, `alt_duty` | W3 | Candidates collapsed by outstanding duty set: one `alt_id` per distinct set — its position, from 0, in the order of §6.3 — with every permission entry that gives it and every duty in it. Under unknowns, the sets are the routes that suffice (§6.3), and the permission entries those that give each in some completion. |
| `dominated` | W3 | An alternative whose outstanding set strictly contains another's, one tuple per alternative it contains. |
| `verdict` | W3 | The verdict; whether the reported alternatives are known to be all of them; and whether the computation was exact, or fell back beyond `max_mixed` (independent completion) or `max_frontier_vars` (`frontier_complete` false) (§6.4). `exact` is relative to completion over literals (§6.4): it does not mean that the operands' values were reasoned over. |
| `verdict_basis` | W3 | The entries that determined the verdict, by role: `prohibition`, `permission`, `duty`, `unknown`, `obligation` — and `closed`, naming the candidates a violated precondition removed, so a `NotApplicable` that closed a route can be told apart from one where nothing matched. |
| `verdict_range` | W3 | For an `Indeterminate` only: the least and the greatest completion verdict in the order `Deny < NotApplicable < Pending < Permit` (§6.4). Sound, and possibly wider, when `verdict.exact` is false. **[D]** (`decisions/0011`) |
| `diagnostic` | W2 | The corpus `diagnostic` tuples of every policy with an entry in `finding` (§3.1, `root`), copied unchanged, so that a verdict that rests on a contested reading says so (`due2-diagnostics.md` §1). |

### 3.6 Lineage — output of W1 **[D]** (`decisions/0039`)

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

The lineage says where each id of a corpus comes from: which authored node, and which selection of an expanded rule. It holds only what the corpus does not. W1 emits one lineage with each corpus, so there is one for each policy version and normaliser version (§4). The policy store keeps it beside the corpus and finds it by the policy, the version, and the normaliser version (`due2-platform.md` §2.3). The corpus of several policies is the union of their corpora (§4), but their lineages are not merged: each policy's lineage stays its own.

W2 and W3 never read the lineage. Three readers do:

- explanation, which follows an atom of a trace to the authored rule (§3.7);
- the `Den` oracle, which checks stage 1 through the bijection that `rule_source` and `selected` record (`odrl-compound-to-atomic-normalization.md` §7, §8.1); and
- the policy store, which renames the ids in `minted` when it publishes a corpus (§4, *Several policies are one corpus*).

A *stage-1 rule* is an atomic rule that stage 1 emits (`odrl-compound-to-atomic-normalization.md` §4), and `rule_id` is its id (§3.1, `atom.atom_id`). Stage 2 builds the corpus atoms from the stage-1 rules.

| Relation | Meaning |
|---|---|
| `lineage` | The run: the policy and the version W1 normalised (§3.1, `policy.version`), the stage-1 profile IRI and version (the `Profile` line of `odrl-compound-to-atomic-normalization.md`), and the version of stage 2. The last three together are the *normaliser version*: what the policy store's calls take as `normaliser_version` (`due2-platform.md` §2.3), and what a case pins for its evaluations (§7.1, `due2-architecture.md` §7). |
| `minted` | Every id that the run minted, in stage 1 or stage 2 (§2, `Id`). These are the ids that the policy store may rename when it publishes the corpus (§4), and the renaming applies here too, so a published lineage names the published ids. |
| `anonymous` | For each node that no author named and that stage 1 minted an id for (`odrl-compound-to-atomic-normalization.md` §5.1, case 3): the subject and predicate of the one triple whose object it is (`odrl-compound-to-atomic-normalization.md` §3). Following `parent` upward reaches the node's anchor, the named node it is a part of. |
| `identity` | Each IRI node whose authored `odrl:uid` differs from its node IRI: the node IRI, and the uid, which is the node's id everywhere else (`odrl-compound-to-atomic-normalization.md` §5.1). A node without a tuple has its node IRI or its minted id as its id. A blank node with an authored `odrl:uid` has the uid as its id and no tuple, since a blank node has no name of its own to map. |
| `rule_source` | For every stage-1 rule, the authored rule it comes from: the rule itself when stage 1 kept it, and the rule it expanded otherwise (`odrl-compound-to-atomic-normalization.md` §6.3). |
| `selected` | For every stage-1 rule, its value on each expansion axis: `odrl:action` and its action, the relation predicate and its value, and each party function and its party (`odrl-compound-to-atomic-normalization.md` §6.3). With `rule_source`, it is the atom `(uid(r), σ)` of the denotation, the authored rule `r` and the selection `σ` (`odrl-compound-to-atomic-normalization.md` §8.1). The corpus atoms repeat these values, but the `Den` oracle checks stage 1 through this record alone, so that a fault of stage 2 cannot hide one of stage 1. |
| `interiorised` | The predicates whose values a root stage-1 rule took from the policy level, because the rule stated no value of that family (`odrl-compound-to-atomic-normalization.md` §6.2). Stage 2 reads it to resolve party roles (§4). |
| `atom_rule` | For every corpus atom, the stage-1 rule it was built from, including an atom that keeps the rule's id. The atom's `source_rule` (§3.1) is that rule's `rule_source.source_rule`. The constraint disjunct of a `Permit` or `Forbid` atom and the clauses of a duty atom are in the corpus (`atom_constraint`, `duty_constraint`), not here. So is a duty atom's binding: a duty that states any party function inherits none (§4), so the roles it inherited are its `atom_party` tuples whose function its rule has no `selected` value for. |
| `negation` | Each constraint that stage 2 made by negating another, when it eliminates `xone` or pushes `dprod:not` inward (§4), and the constraint it negates. |

### 3.7 Explanation **[D]** (`decisions/0010`)

A verdict alone does not explain a decision; the trace does. Every evaluation that returns a verdict emits its trace (§7), and the explanation is read from it, never computed alongside it.

**The derivation.** An evaluation's explanation is the part of its trace reachable from `verdict`, through references the relations already carry:

| From | To | Through |
|---|---|---|
| `verdict` | the determining entries, by role | `verdict_basis`; for `Pending`, also `alternative`, `alt_duty`, `dominated`; for `Indeterminate`, also `verdict_range` |
| `verdict` | every input that was missing, invalid, in conflict, unresolved, or a misfit, in a finding that is not `F`, whether or not it mattered | `unknown_part`; for a witness condition, `witness_part` |
| an entry | its findings | `finding` |
| a finding | the parts that determined it (§5.2) | `basis`; for a duty, also `witness_basis` and `instance` |
| a `fact` part | the value and status read, and which sources answered | `read`, and the SOTW's `fact` and `fact_value` |
| an `evidence` part, or the `witness` of a `witness_basis` or `witness_part` row | the record | the SOTW's `evidence`, `evidence_param`, `evidence_param_value` |
| a `constraint` part | the constraint as normalised | the corpus's `constraint`, `constraint_value` |
| a removed entry | the atom that removed it, and the rule | `eliminated` |
| an atom | the authored rule, expansion selection, and binding | `source_rule`; the lineage's `atom_rule` and `selected`, and the atom's `atom_party` (§3.6) |
| a policy in the derivation | the contested readings it was accepted under | `diagnostic` |

Reading it needs the trace, the evaluation's three input collections, and the lineage of each policy in its corpus (§3.6), and nothing else. It never re-runs W2 or W3 and never reads the world. Law L10 (§8) makes this checkable: every reference resolves, and every finding follows from its basis. The derivation is typed relations under the canonical encoding (`decisions/0007`), so it is parseable by any reader that reads the trace.

**Groups are keys.** What belongs together is a key the trace, the corpus, or the lineage already holds. The reader never infers it.

- *The atoms of one authored rule* share `source_rule`. Atoms with one `atom_rule.rule_id` were built from one selection of that rule (§3.6).
- *A permission and the duties that gate it* are linked by `edge`, `alternative`, and `alt_duty`.
- *The instances of one duty* are its `instance` tuples.
- *The policies evaluated together* are told apart by `root.policy_id`, and every W2 tuple about an atom names the policy of its entry (§3.5). Each elimination names its rule: the policy's own strategy, or `prohibit-overrides` across policies (§6.2).
- *The evaluations of one case* are ordered by its `seq` (§7.1). What changed between two of them is a per-relation set difference of their canonical traces, read with the events recorded between them.

**Rendering is later.** Prose, a page, or a screen is a presentation step over the derivation. It may select and order, and it never adds a reason. A rendering that needs what the derivation lacks reveals a trace defect, fixed by a trace relation under L1 and L10, never by the renderer.

**What the corpus asserts.** A case names atoms by their authored IRI: the projection through `source_rule`, or `source_duty` for a duty, as `frontier` and `obligations` already do (`conformance/README.md`). `expected.verdict_basis` is the set of `(source, role)` pairs of the trace's `verdict_basis`, and `expected.eliminated` the set of `(source, source of by_atom, rule)` triples of its `eliminated`, so the disjuncts of one rule (§4) give one triple. Full traces, with atom ids, are pinned by L1 and replay, not by authored cases.

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
| **1. Atomise** | Compact interiorisation; expansion of multi-valued action, relation, and party axes; identity, with an id minted for each node no author named; lineage. Structure-preserving: shared duties stay shared. | `odrl-compound-to-atomic-normalization.md` |
| **2. Build** | Constraint DNF, including `xone`; parameter substitution and per-binding duty instantiation, each binding a duty atom with its own id (§3.1, `duty.atom_id`); party-role inheritance — a duty that declares no function properties takes all of them from its parent permission (ODRL IM §2.6.5), one that declares any takes none, and for each role a value the rule states beats one interiorised from the policy level (`odrl-compound-to-atomic-normalization.md` §6.2); projection into §3.1 — a duty's guards stay on its atom (`decisions/0003`); the lineage of §3.6, with stage 1's part and stage 2's `minted`, `atom_rule`, and `negation`. | `due2-architecture.md` §4–§5 |

**Two forms carry a policy through W1.** Stage 1 parses the authored graph into a **lifted tree** — a forest of trees hanging from named rules (`odrl-compound-to-atomic-normalization.md` §3) — and transforms that; RDF is a boundary format, read at the parse and never written (`ways-of-working.md` §2.4). Stage 1's output stays inside W1 (`decisions/0037`). Stage 2 projects the lifted form into the **relations** of §3.1 — collections of tuples whose fields are the terms of §2 — and the relations are all W2 and W3 ever see.

**Position decides conjunction.** Expanding a root rule yields independent root atoms — any one may match a request, which is disjunction. Expanding a nested duty fans out the parent's edges — every resulting duty is owed, which is conjunction. Neither stage declares which fields are disjunctive; it follows from where the value sits. A constraint's DNF is not an expansion of this kind. A disjunct of a `Permit` or `Forbid` atom's constraint becomes an atom of its own, an alternative. A duty's constraint is never split: it would make alternative conditions into duties all owed. Its disjuncts become clauses of its one atom (§3.1, `decisions/0028`).

**Several policies are one corpus [D]** (`decisions/0036`, `decisions/0050`). Stage 1 normalises one policy per input (`MultiplePolicies`, `due2-diagnostics.md` §3), so W1 runs both stages on each authored policy, and the corpus of the policies evaluated together is the union of their corpora, relation by relation. No named node's id includes the policy that states it (§3.1, `atom.atom_id`). Each run of W1 mints fresh ids, so when the policy store publishes a corpus, it renames the ids that the corpus minted for a published named node and its parts to the published ones, in the corpus and in its lineage: the node's anonymous parts, the atoms of its expansion and its constraint's disjuncts, and a duty atom of the same duty and binding (§3.1, `duty.atom_id`). A named node's parts are therefore minted once, when it is first published, and a named permission, prohibition, duty, or constraint that two policies state is one tuple in the union. An atom that both state as a root has a `root` tuple for each. Each policy's `closure` tuples stay under its own `policy_id` (§3.1), and W2 evaluates an atom once for each of its policies, in that policy's data space (§3.3, §5.5). So the union holds the policies side by side, and none reads another's tuples. The union never fails, because its inputs must agree. *Agreement* is a precondition: two corpora that both hold a node say the same of it, up to the renaming of minted ids, its tuple in `policy`, `atom`, `constraint`, or `duty`, and the set of tuples that name it in the first field of `policy_profile`, `atom_party`, `constraint_value`, `constraint_scheme`, `atom_constraint`, `duty_constraint`, or `edge`. `root` is not compared, because which policies state a node is what differs between them, and neither are `closure` and `diagnostic`, whose tuples are keyed by their policy, so no two policies share one. Once a published policy's corpus holds a node, that is the node's description, and a policy whose corpus says something different of it is in error. The policy store rejects it when it is published, with `IdentityConflict`, whose ref is the node, and the published policies are unaffected. The renaming exists exactly when the two agree, so finding it is the agreement check (`decisions/0038`). Nothing at evaluation repairs a description or chooses between two. A policy is *published* when the store accepts its corpus (`put_corpus`, `due2-platform.md` §2.3); storing its document does not publish it. It is compared with the current version of every other published policy, normalised by the same normaliser version, and never with an earlier version of itself. For example, offer `A` and agreement `B` both oblige `duty:deliver` with the `deadline` `P1D`, and both are published. Policy `C` states `duty:deliver` with the `deadline` `P2D`. Both stages accept `C`, but its `duty` tuple shares the key `duty:deliver` with `A`'s and differs in `deadline`, so `C` is rejected when it is published, and `A` and `B` are evaluated as before. `C` is rejected too if it states a named permission `rule:read` of `A` without the constraint that `A` attaches to it, because the two corpora give `rule:read` different sets of `atom_constraint` tuples.

Obligations on the output:

- **Stage 1 preserves structure.** It preserves the denotation `Den` — the set of ground atomic rules with identity-bearing duty edges — up to a bijection its lineage records (`odrl-compound-to-atomic-normalization.md` §8.1).
- **Stage 2 preserves meaning.** DNF changes how many atoms there are, so no bijection exists. Its obligation is L9, checked against a direct interpreter (`due2-architecture.md` §10).
- **Sufficiency.** Stage 2 depends on its input only through `Den` — never on node IRIs, triple order, or annotations — and W2 and W3 depend on a policy only through its corpus. So every evaluation depends on an authored policy only through its denotation, which is what lets stage 1's structural guarantee carry through to verdicts.
- **Determinism and bounds.** W1 is deterministic up to renaming of minted ids: two runs over one input, or over isomorphic inputs, give corpora and lineages that one bijection between their minted ids makes equal (`decisions/0038`). A limit breach fails the whole run before any output.
- **Well-formedness.** The §3.1 invariants hold.
- **Rejection.** An `error` diagnostic rejects the policy, with no corpus and no lineage. W1 reports every error of the first stage that has one, and runs no later stage, so a rejected policy's set of codes is deterministic and a negative corpus case can state it (`due2-diagnostics.md` §1). A policy that both stages accept is still rejected by the policy store when it is published, if it disagrees with a published policy (`IdentityConflict`, *Several policies are one corpus*, above). Warnings never reject; they are carried in `diagnostic` (§3.1).

---

## 5. W2 — Evaluate **[D]**

```text
W2 : Corpus × Request × SOTW → finding × basis × unknown_part × witness_basis × witness_part × read × instance
```

### 5.1 One predicate per role

Every finding is the truth value of one predicate for one entry, an atom in one of its policies (§3.1, `root`), chosen by the atom's role in that policy. W2 reads an entry in policy `P` in `P`'s data space (§3.3): its hierarchy comparisons follow `P`'s `closure` with the SOTW's, and a duty's entry in `P` is a precondition of its parents' entries in `P`. The atoms that W1 makes from one authored policy are all in that policy's data space, so they share it, as the parts of the authored policy do; L9 makes that sharing give the authored policy's own reading. **[D]** (`decisions/0050`)

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

**Owed.** A precondition duty is owed when its guards hold, by the clause rule above; with no guards it is owed whenever its parent applies. An inactive duty is not owed — the parent permission stands without it (DPROD D-ACTIVATE; W3C CG example C21). A duty entry that is also a root obligation of its policy reads the same guards in that role, through `in_force`; both findings come from one evaluation of the guards, and canonical literals (§6.4) keep them correlated.

**In force.** A root obligation has an entry in each of its *root policies*, the policies its `root` tuples name (§3.1). Its entry in `P` is in force for a request when `P` matches the request and the obligation's guards hold in `P`'s data space, by the clause rule of §5.2. A policy `P` *matches* when some `Permit` or `Forbid` atom of `P` matches the request in `P`'s data space — action, relation, and parties as above, constraints aside. A duty that two policies state as an obligation, such as a delivery that an offer and the agreement made from it both oblige, is one atom with an entry in each. Each entry is in force when its own policy matches and has its own instance (§5.3). One witness record can fulfil both, and whether it does is read per entry (`decisions/0036`, `decisions/0050`). An obligation is not matched by its own action: it travels with the policy under which the request is made. A log-every-access obligation is therefore in force for a read, which an action match would never achieve.

### 5.3 Fulfilled

Fulfilment follows RL2 (`spec/RL2_Model.md` §4.3, §7.3). It is derived from evidence of performed actions, and the absence of evidence means *not yet fulfilled* — never unknown. The case history is where evidence arrives: a duty with none is outstanding, and the requester is told so through `Pending`.

**Instance.** Each duty entry `d` that W2 evaluates (§5.5) resolves to one duty instance, recorded in `instance`:

- scope `member` — one instance per duty entry (and occurrence, under *Recurrence* below), fulfilled by the performer's act whatever request it was submitted against, so one fulfilment serves every request of that performer. "Petition the council about X" binds to X, and its atoms for X and Y are two instances.
- scope `grant` — one instance per request, fulfilled only by evidence submitted against it ("pay per use"). A request without a `reference` falls back to `member`.

**The instance key [D]** (`decisions/0032`, amendment of 2026-10-25; `decisions/0038`). An instance is keyed by its duty entry, the atom's id and the policy, and, for a recurring duty, its occurrence `t` (*Recurrence* below; `instance`, §3.5). A case has one request (§7.1), so the request subject and `reference` are the same in every evaluation of a case (`decisions/0030`), and the key needs neither. They decide which evidence counts, through the witness test below:

- the **performer**, the request subject, when the witness test reads it as the actor: the duty has no bearer, or its bearer is an `odrl:PartyCollection` and the subject is not known to be outside it (`subject ⊑ bearer` is `T` or `U`). When membership is `U`, the instance is the subject's if the subject is a member, and the witness test is `U` for any other member's act. "Complete annual training", borne by all employees, is then Alice's instance in Alice's case and Bob's in Bob's, and Bob's training does not fulfil Alice's;
- `request.reference`, for scope `grant`: only evidence submitted against this request's grant counts.

The case records an entry's activation from the first trace whose `instance` names it (`due2-profiles.md` §7). The atoms an authored duty expands into, one per action or target say, have one instance each, and a duty in two roles, or one that two permissions share with the same inherited roles and parameter values, is one atom (§3.1, `duty.atom_id`), so it has one instance in each of its policies.

**Witness.** Evidence `e` is a witness for `d` when:

- `e.occurred_at ≤ sotw.effective_at`;
- `e.action ⊑ d.action`;
- `e.object = d.relation_value`, if `d` has one;
- `e.actor` is `d`'s bearer — the party in the bearer role (`due2-profiles.md` §6: `odrl:assignee` unless a profile says otherwise), after role inheritance (§4) — or the request subject if `d` still names none. A bearer that is an `odrl:PartyCollection` is borne by each of its members, which "undertake the same functional role in the Rule" (ODRL IM §2.3), so when the request subject is a member (`subject ⊑ bearer` under the party closure), `e.actor` must be the subject: another member's act does not discharge it. When the request names no subject, an act by a member is `U`, since that member may be the subject (`decisions/0018`);
- if `d` has an attester — the party in the role `due2:attester` (`due2-profiles.md` §6), after role inheritance (§4) — `e.issuer` is the attester or below it under the party closure (`e.issuer ⊑ attester`), and evidence with no `issuer` is no witness. A duty with no attester accepts any issuer, as RL2 accepts any for a duty with no signers (RL2's `spec/RL2_Model.md` §4.4). Who attests a duty is policy content, so it is a party function of the duty and not an input of the evaluation (`decisions/0045`);
- for scope `grant`, `e.discharges_duty` is `d`'s `source_duty` and `e.discharges_reference` is `request.reference`: the evidence was submitted against this request's grant of the duty. The atoms of one authored duty share that grant, and the rest of the test picks among them: a payment of one fee has that fee as its `object`. For scope `member`, neither field is consulted.

A comparison above under the party closure — `subject ⊑ bearer`, `e.actor ⊑ bearer`, or `e.issuer ⊑ attester` — is `U` when an answer for its narrower side, or above it, is `unresolved` (§3.3, `closure`; `decisions/0048`). The record's `evidence` part is then `U` unless another condition is `F`, and `unknown_part` names it with kind `evidence`, the record as `ref`, the compared party function as `input` (the bearer's function, or `due2:attester`), and status `unresolved`. When both comparisons are `U`, the part has two rows, one per party function (§3.5). It is opaque (§6.4). Each comparison is read in the entry's data space, its policy's `closure` with the SOTW's (§3.3). So one record can be a witness for the duty's entry in `P` and not for its entry in `Q`, when only `P`'s own edges place `e.actor` under the bearer (`decisions/0050`).

A duty with both roles in one policy — an obligation of the policy and a precondition of one of its permissions — is one entry. It has one instance there, so it has one `fulfilled` finding in that policy, which both roles read. When the obligation is of one policy and the permission of another, the duty has an entry in each, and each entry reads its own policy's data space.

**Truth.** `d`'s witness conditions are evaluated once per witness: witness-source operands read its `evidence_param_value`, and `due2:actionTime` is its `occurred_at` (`due2-profiles.md` §3). Every other operand reads the request, the SOTW, or the context as usual; in a duty, those are the guards (§5.2). A witness satisfies the witness conditions when it satisfies some witness clause (§5.2), and any witness satisfies a duty with none. The finding is the Kleene disjunction of that value over all witnesses: `T` if some witness satisfies some clause; `F` if every witness fails every clause, which includes having no witness; `U` otherwise. Each witness's evaluation is recorded under its `evidence_id`: the parts of the witness clauses in `witness_basis`, and their `U` parts in `witness_part` (§3.5). A duty requiring a payment of 5, with one witness that states no amount and another that states an IRI for it, has two `witness_part` rows for the one constraint, with statuses `missing` and `invalid` (`decisions/0035`).

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

**Recurrence.** A duty with `recurrence` is owed once per occurrence of its RRULE. W2 generates the occurrences `t ≤ effective_at` — the anchor is the rule's `DTSTART`, or the duty's activation without one (`due2-profiles.md` §7) — and derives one instance per occurrence: the instance is keyed by the entry and `t`, the trace's `occurrence` is `t`, the instance's activation is `t`, and a relative deadline is `t + duration`. A witness for an occurrence must also satisfy `occurred_at ≥ t`: one delivery does not fulfil every later instance. DPROD's `performed` check has no lower bound, so one performance fulfils every later instance there — a gap found in DPROD (`due2-profiles.md` §8.2). Occurrences beyond `effective_at` — instances not yet owed — are not generated; reporting them is the open window question (§9, `due2-profiles.md` §9).

An instance exists only for a duty that is owed: a precondition whose `owed` finding is `F` has no instance and no `fulfilled` finding, as an occurrence not yet due has none. One whose `owed` is `U` has both, and W3 combines them (§6.1).

Fulfilment is derivation, not bookkeeping. Evidence is appended to the case and the case is evaluated again; no status is ever flipped in place.

### 5.4 Constraints

For a constraint with left operand `o`:

1. `o`'s binding (`due2-profiles.md` §3), which the corpus carries on the constraint (§3.1), gives its source — request, state, witness, or context — its property, range, unit, cardinality, and any concept schemes (`constraint_scheme`). W1 has already checked the operator against the binding's allowed operators, and the constraint's unit against the binding's. A constraint that has a `unit` and no `operand_unit` is `U` with status `misfit`, whatever is read, and steps 2 and 3 do not decide it: nothing says what unit a read value is in (`due2-profiles.md` §3, *Units*; `decisions/0049`). W2 still records a state-source property in `read`.
2. For a state-source operand, W2 records the property in `read` and combines its admitted `fact` answers (§3.3, *Several sources*). A request-source operand reads `request_param_value`, a witness-source operand the witness's `evidence_param_value` (§5.3), and a context operand its built-in.
3. Status `resolved` → apply the operator to the value(s) and `constraint_value`(s), giving `T` or `F`, or `U` when a value does not fit the operator: a kind other than the right operand's, a `dateTime` without a timezone or a `date` with one (`decisions/0024`), or a concept in none of the operand's schemes (`due2-profiles.md` §4), or `U` when a hierarchy comparison is `U` because a world-edge answer is `unresolved` (§3.3, `closure`). A state property with any other combined status, or with no fact at all → `U`, with basis kind `fact` and the property as `ref`: what resolves it is the property's fact. Every other `U` from a value has basis kind `constraint` and the constraint as `ref`: a value of any source that does not fit, a request or witness value that is `missing`, `invalid`, or in `conflict` (`due2-profiles.md` §3), or a hierarchy comparison made `U` by an `unresolved` world-edge answer. What resolves it is a value that fits, not a state fact. Every `U` part is also recorded in `unknown_part` (§3.5), or in `witness_part` under its witness for a part of a witness clause (§5.3), with the status of what it read: the state property's combined status (`unresolved` when it has no fact), the request or witness value's status, or `misfit` for a `resolved` value that does not fit, and `unresolved` for a hierarchy comparison made `U` by a world-edge answer. An absent target or party (§5.2) is `missing`.
4. The shell finds properties still to resolve as `read` properties with no `fact` from an admitted source in the SOTW. Derived, not recorded twice.

Operators form a closed, typed registry. Strings compare by Unicode code point. No operator consults the clock, the locale, or randomness. Time enters only as `request.at`, `sotw.effective_at`, and evidence times, each an `xsd:dateTime` with a timezone (`decisions/0024`): a constraint on when the action happens (ODRL `dateTime`) reads `request.at` for a permission or prohibition and the witness's `occurred_at` for a duty.

### 5.5 Which atoms

W2 produces a finding for each of these entries, read in its policy's data space (§3.3):

- every `Permit` and `Forbid` entry whose finding could be other than `F`;
- every precondition duty entry of a `Permit` entry in the same policy whose finding is not `F` — its `owed` finding, and its `fulfilled` finding when `owed` is `T` or `U`; and
- every root obligation entry of a policy some of whose `Permit` or `Forbid` atoms match the request (§5.2), with its `fulfilled` finding when `in_force` is `T` or `U`; and
- one `instance` tuple (§3.5) for every duty instance derived above — for a recurring duty, one per occurrence (§5.3).

An index may skip root entries that are certainly `F` — wrong action, wrong target — because an `F` root is neutral in W3. It may not skip an entry whose match turns on a `U` part. It never skips a precondition of a live permission: an owed, unfulfilled duty is outstanding, which is not neutral. Remedies and consequences are not evaluated for access; they belong to the monitoring question.

---

## 6. W3 — Resolve **[D]**

```text
W3 : Corpus × finding × basis × unknown_part × instance → eliminated × alternative × alt_duty × dominated × verdict × verdict_basis
```

Four steps in fixed order. The order is normative: conflict resolution runs before duties choose among routes, so duties can choose among surviving permissions but never decide which survive. The one duty finding read before conflict is a violated precondition that is owed: it closes its route outright (§6.1), so the closed permission takes no part in conflict.

### 6.1 Candidates

W3 reads entries (§3.1, `root`): a candidate is a `Permit` entry, and its precondition duties are read as their entries in the candidate's policy (§5.1). A precondition duty is **open** for its parent when `owed ∧ ¬fulfilled` (§5.1), in Kleene logic: `T` when it is owed and unfulfilled, `F` when it is not owed or is fulfilled, `U` otherwise. A duty that is not owed is not open, whatever its evidence.

A root `Permit` entry with finding `T` or `U` is a candidate — unless one of its precondition duty instances is `violated` (§5.3) and that duty's `owed` is `T`. A violated precondition removes its parent's candidacy outright: the route can no longer be taken, and `Pending` must not offer it. The removal is recorded in `eliminated` with rule `violated_precondition`, and `verdict_basis` carries it with role `closed` (§3.5), so the answer distinguishes *a route that closed* from *nothing that matched*. A violated precondition whose `owed` is `U` makes the candidate uncertain instead. A surviving candidate's **outstanding set** is its precondition duties whose open value is `T` — a violated one removed the candidate instead of joining the set; its **unknown set**, those whose open value is `U`. Each candidate is in exactly one state:

| State | Condition |
|---|---|
| **ready** | permission `T`; no outstanding, no unknown duty |
| **pending** | permission `T`; some outstanding, no unknown duty |
| **uncertain** | permission `U`, or some unknown duty |

Root obligation entries in force are reported in `verdict_basis` with role `obligation`, with their bearer and, for each of their instances, the status W2 computed (§5.3) — `fulfilled`, `outstanding`, `violated`, or `unknown`. An obligation whose `in_force` is `U` is reported `unknown`, whatever its instance status; one not in force is not reported. Neither status nor bearer is stored beyond the trace. Obligations never affect the verdict, a violated one included: ODRL makes a duty a precondition of its permission (ODRL IM §2.6.1), and ties a policy's obligation to none of its permissions (ODRL IM §2.6.4). A violated *precondition* removes its own candidate only, and another permission of the request can still permit (`due2-profiles.md` §7, `decisions/0045`).

### 6.2 Conflict

**Entries [D]** (`decisions/0036`, `decisions/0050`). A `Permit` or `Forbid` atom takes part once for each policy its `root` tuples name (§3.1): its *entry* in that policy, with that entry's finding (§5.1). Below, a policy's candidates and `Forbid` atoms are their entries in it, and an elimination removes an entry. An atom remains a candidate, or a prohibition, while any of its entries survives. A permission that two policies state is therefore removed only when both remove it, which gives the verdict that one copy of it in each policy would: each entry is read in its policy's data space, as that policy's copy would be (§3.3).

1. **Within a source policy**, by its `conflict`. Under `prohibit`, a `T` `Forbid` eliminates that policy's candidates. Under `perm`, a `T` candidate eliminates that policy's `Forbid` atoms. Under `invalid`, a `T` candidate and a `T` `Forbid` together void the policy: all of its `Permit` and `Forbid` atoms are eliminated, with rule `invalid`. **[D]** (`decisions/0029`) A void policy gives no access answer, and its root obligations stay in force (§5.2) and are reported (§6.1), because whether an obligation was met does not depend on the request that voided the policy. `Indeterminate` with a cause stays parked (`due2-architecture.md` §6.2).
2. **Across source policies**, by prohibit-overrides **[D]** (`decisions/0045`): any surviving `T` `Forbid` eliminates every candidate. Under unknowns, which `Forbid` survives can depend on the completion, and §3.5 `eliminated` lists only the removals that hold in every completion (`decisions/0052`). Other strategies, such as permit-overrides or priority-ordered first-applicable on `atom.priority`, are open (§9, #4).

`U` entries eliminate nothing; they make the verdict uncertain (§6.4). Every elimination is recorded with its rule. Duties play no part.

### 6.3 Collapse and order

Within one completion, alternatives are formed from the ready and pending candidates that survive §6.2. Under unknowns, the reply lists the frontier that the paragraph *The listed frontier* below defines.

1. **Collapse.** Candidates with the same outstanding set — compared by duty id — form one alternative, whatever their policies. Two permissions that cost the same are one choice with two grounds, not two choices.
2. **Order by inclusion.** Alternative `A` dominates `B` when `outstanding(A) ⊊ outstanding(B)`. This needs nothing but duty identity: no weights, no costs, no configuration. A ready candidate has the empty set and so dominates every pending one. Authorisation state is not a separate rule — it falls out of the order.
3. **Frontier.** The non-dominated alternatives. If there are several, they are incomparable — neither demands a subset of the other's duties — and W3 reports all of them. Each outstanding duty is reported with its bearer, so a route that waits on someone other than the requester — a second approver — says so.

**Sorting [O].** Inclusion is a partial order, and the frontier is its honest output. A total order needs a declared preference — fewest duties, declared weights, a ranking of duty kinds — authored in the policy, in a form that is open (#5, `decisions/0045`). Without one, alternatives are listed in a deterministic order that expresses **no** preference: by outstanding-set size, then by the set's duty ids, sorted and compared as lists by code point. `alt_id` is an alternative's position in that order, from 0 (`decisions/0038`). Storage order, upload time, and evaluation order never break a tie.

**The listed frontier [D]** (`decisions/0026`). A *route* is an outstanding set. Under unknowns, each completion (§6.4) has its own candidates and frontier. A route is **open** in a completion when some candidate that survives §6.2 there has it, whether or not a smaller route dominates it there. A route **suffices** when it is open in some completion and every completion has an open route within it: the same set or a subset. For a definite `Pending` or `Permit` (§6.4), the listed frontier is the routes that suffice and that no route that suffices dominates. Each is an alternative whose grounds are the permission entries that give it in some completion. For a definite `Permit`, every completion has the empty route open, so the listed frontier is the empty route.

A listed route is one the requester can act on. In each completion, some candidate's outstanding set lies within it, and fulfilling the route's duties empties that set. A fulfilled duty is not violated, so §6.1 closes no candidate on its account, and §6.2 never reads duties, so the candidate still survives and is ready. Making `fulfilled` findings true never lowers a verdict (§6.4), and the completion's verdict was not `Deny`, so it becomes `Permit`. A route that does not suffice is not listed: fulfilling its duties may permit only in some completions. Three examples, each with `x` unresolved:

- Permissions on `x eq 5` and on `x neq 5` both need `d`. The route `{d}` is open in every completion, though no one permission gives it in each, and it is listed with both as grounds.
- One permission needs `d` and `d2`, and `d2`'s `fulfilled` finding is `U`. Its route is `{d, d2}` in some completions and `{d}` in the others. `{d, d2}` suffices, `{d}` does not, and `{d, d2}` is listed.
- One permission needs `d0`, owed when `x` is false, and `d1`, owed when it is true. Its route is `{d0}` where `x` is false and `{d1}` where it is true, and neither is within the other. No route suffices, and the listed frontier is empty: what to do depends on `x`, which `unknown_part` names (§3.5).

### 6.4 Verdict

The verdict is defined by invariance:

> Replace every `U` finding by `T` or `F`. If every such completion gives the same verdict, that is the verdict. Otherwise it is `Indeterminate`.

For a completion, which has no `U`:

| Verdict | Condition, checked in order |
|---|---|
| `Deny` | a `Forbid` survives §6.2 and applies |
| `Permit` | the frontier contains a ready alternative |
| `Pending(frontier)` | the frontier is non-empty |
| `NotApplicable` | otherwise |

**What a verdict says [D]** (`decisions/0031`). A verdict is the answer of the policies in the corpus, as written, for the request in the SOTW, whatever their class. Over an offer, `Permit` says that the offer's terms permit the action: "this offer permits you to proceed". It does not say that anyone has accepted the offer. Accepting it, and recording the agreement that results, happen outside the workflows. The reading cuts both ways: an offer's prohibitions deny as any policy's do. The offer permits only a requester it covers, since an assignee is matched like any party (§5.2). A withdrawn or expired offer still permits unless selection leaves it out or a constraint on its status, flattened onto the request, excludes it (`due2-profiles.md` §8.1). `verdict_basis` names the permitting atoms and so their policies (§3.7).

DPROD withholds access while a policy's obligation is violated, once a permission is active (`formal-semantics.md` §7.2, steps 5–6). due2 does not: obligations never affect the verdict (§6.1), and the difference is DPROD exception 6 (`due2-profiles.md` §8.2).

**Computing it.** Order the completion verdicts `Deny < NotApplicable < Pending < Permit`. Under all three strategies and prohibit-overrides, the verdict is monotone in every finding: making a permission or a duty's `fulfilled` more true never lowers it, and making a prohibition or a precondition's `owed` more true never raises it.

*Proof*, by cases on one finding changing from `F` to `T`. The verdict rises with the candidate set and falls with the set of surviving `T` prohibitions, so it suffices to track those two sets. A finding is one entry's, in one policy (§5.1), and each policy's fold reads only its own entries (§6.2, *Entries*). An atom is in either set while some entry is in it, so each case below moves the two sets the same way in whichever policy its entry is, and the cases compose when several entries change.

- **A duty's `fulfilled` finding.** One outstanding set shrinks, and a pending candidate may become ready. A candidate that a violated precondition removed may also re-enter (§6.1). It then passes through §6.2 exactly as the new candidate of the permission case below does, so eliminations may change (L6, §8), but candidates are only added and prohibitions only removed. The verdict stays or rises.
- **A precondition's `owed` finding.** An owed duty may become open: one outstanding set grows, and a ready candidate may become pending. Or, if its instance is violated, its candidate is removed before §6.2 (§6.1), which is the permission case below run from `T` to `F`: candidates are only removed and prohibitions only added. The verdict stays or falls, so `owed` is completed like a prohibition (`decisions/0003`).
- **A permission `p` of policy `P`.** Under `prohibit`, `p` is eliminated if `P` has a `T` prohibition and is otherwise a new candidate. Under `perm`, `p` is a new candidate and eliminates `P`'s prohibitions. Under `invalid`, if `P` has a `T` prohibition: either `P` already had a `T` candidate and was void already, so nothing changes, or its prohibition survived before and the verdict was `Deny`, the minimum. Candidates are only added and prohibitions only removed. The verdict stays or rises.
- **A prohibition `f` of policy `P`.** Under `prohibit`, `f` survives. Under `perm`, `f` is eliminated if `P` has a `T` candidate and survives otherwise. Under `invalid`, if `P` has a `T` candidate, `P` is voided: its candidates go, and so do its prohibitions — which were all `F`, or `P` would already have been void. Its obligations stay in force (§6.2), and they never affect the verdict (§6.1). Candidates are only removed and prohibitions only added. The verdict stays or falls. ∎

The verdict is therefore a monotone map from completions — ordered with prohibitions reversed — into a chain. Every completion's verdict lies between that of the most restrictive completion (permissions and `fulfilled` findings `F`; prohibitions and `owed` `T`) and that of the most permissive one (the reverse). If the two agree, every completion agrees, so the definition costs two evaluations, not exponentially many. `tools/check_completion.py` checks the two-extremes computation against brute force over every completion (below). Reading `invalid` as `Indeterminate` instead would add a value outside the chain, so that alternative — parked, `due2-architecture.md` §6.2 — would need its own argument.

**A void policy, against ODRL [D]** (#92). ODRL 2.2 reads a policy whose `invalid` conflict arises as void, governing nothing. due2 reads it as giving no access answer for the request, and the reading has two halves (`decisions/0029`). The void policy abstains rather than giving `Indeterminate`: `Indeterminate` lies outside the chain, and the proof above needs every completion's verdict in it. This gives up a verdict that says the policy contradicts itself on this request; the trace still shows the contradiction, as `eliminated` with rule `invalid`. The void policy keeps its root obligations in force, for a reason the proof does not need, since obligations never affect the verdict (§6.1): whether an obligation was met is a fact about the world, while the conflict is a fact about one request, and voiding the obligations would let a request hide a violated one by asking for a use the policy forbids (`due2-architecture.md` §6.2). That a violated obligation never denies is not a departure: it is ODRL's reading, and DPROD's denial is a recorded difference (`due2-profiles.md` §7, §8.2 exception 6).

**Completions range over literals [D].** A finding is `U` because some of its parts are (§5.2). A `U` part whose value exists but is not known, one that reads a state property that is `unresolved` or has no fact, is **completed**. Every other `U` part is **opaque** (`decisions/0016`): its value is `missing` (an absent target or party included), `invalid`, in `conflict`, or a misfit (§5.4), which includes every value read by a constraint that states a unit its binding does not declare (`decisions/0049`), or it is a hierarchy comparison made `U` by an `unresolved` world-edge answer (§3.3, `closure`; `decisions/0048`). Nothing says that its input has one value that fits, so an operator and its complement need not have opposite truth values there, and the pairing below does not hold for it. An opaque part is a variable of its own, one for each entry that reads it, shared with no other part. In an authored constraint tree it stays `U` under strong Kleene logic, and the finding it leaves `U` is completed instead. W1's rewrites are strong Kleene equivalences, so a tree and its DNF atoms, or a duty's clauses, are `U` together (L9). Each completed `U` part is a *variable*, with one exception that makes the definition exact for parts the policy correlates: two constraint parts with the same scope, operand binding (source and property, `due2-profiles.md` §3 — not the left-operand IRI, which two policies may bind differently), concept reading, unit (the constraint's own `unit`, not its `operand_unit`), and right operand(s) are one variable — the same polarity when their operators are equal, opposite polarities when they are complements (`eq`/`neq`, `lt`/`gteq`, `lteq`/`gt`, `isAnyOf`/`isNoneOf`). The key is derived from the corpus's `constraint` and `constraint_value` tuples, so nothing is stored. Right operands are compared as written terms (§2 `Term`), each a lexical form with its datatype, so the datatype is part of the key through them. The concept reading says whether the left operand has a concept scheme (`due2-profiles.md` §4): with one, `eq` is ⊑ under `skos:broader`, and without one, identity. Two operands bound to one property, one with a scheme and one without, therefore make different comparisons. With `x` a concept below `c`, `eq c` without a scheme and `neq c` with one are both `F`, so they are not complements, and pairing them would give a wrong definite verdict (`decisions/0023`). For the same reason, a part whose comparison reads a hierarchy (`due2-profiles.md` §4), such as `eq` with a concept reading, `isA`, or `isPartOf`, also has its entry's policy in the key. Two policies' `closure` tuples may order one value differently (§3.1, `closure`), so an unknown value can be ⊑ `c` for an entry in `P` and not for one in `Q`, and one variable for both would drop that completion (`decisions/0050`). Two terms with one value, such as `5` and `5.0`, are then two variables, and so are a constraint that states no unit and one that states its binding's unit, though both are read in that unit (`decisions/0049` #4): like the parts below whose relation is not worked out, that can cost a definite verdict, never produce a wrong one. Relation and party parts are keyed the same way: two that test the same request field against the same value with the same relation (the target, or one function's party) are one variable, so the atoms that W1's expansion copies from one rule, or that two rules give the same party, share it (`decisions/0011` #2, `decisions/0012`). A request field has no `unresolved` status, so an absent target or party is opaque, and shares nothing (`decisions/0016`). Parts that are not the same expression or its complement stay separate variables, even over one field (target `ex:a` and target `ex:b`; `eq 0` and `lteq 2`), as *What stays approximate* below says. A duty's `fulfilled` finding, a disjunction over witnesses, is one variable of its own. A completion assigns `T` or `F` to every variable, and each `U` finding is re-derived from its parts by Kleene conjunction (§5.2) under that assignment.

This matters wherever one fact is read in both directions. `xone` expands into disjuncts that carry the others' negations. Authors write complements across rules ("home lending may read; everyone else must petition first" as two permissions, `dept = HL` and `dept ≠ HL`). A guard literal may also appear in a rule's constraint. With the fact unknown, completing those parts independently admits combinations no value produces — both `dept = HL` and `dept ≠ HL` `F` — and the verdict widens to `Indeterminate` where the authored policy decides. In `due2-xone-unknown`, single-domicile clients are permitted by an `xone` and dual-domicile clients by a separate rule with an attestation duty; with one domicile known, the other unknown, and the attestation on file, every value of the unknown fact permits. Sharing one variable excludes the impossible combinations, and the verdict is `Permit`.

*Computing it.* A variable is **uniform** when each of its occurrences moves the verdict the same way — upward for a positive occurrence in a permission's `applies` or a duty's `fulfilled`, or a negative one in a prohibition's `applies`, or a precondition's `owed`; downward for the reverse — and **mixed** otherwise. By the monotonicity argument above, applied per occurrence, uniform variables are bounded by the two extreme completions. Mixed variables are enumerated: for each of the `2^k` assignments to the `k` mixed variables, complete the uniform ones at both extremes. The verdict is definite when all `2^(k+1)` completion verdicts agree. `k` counts only unknown literals that occur with both directions in the evaluation at hand — zero unless a fact is read both ways, as above; a duty's guards alone never raise it. Beyond `max_mixed` (a constant, §3.4) the mixed variables are completed independently, each occurrence its own variable: sound, erring only towards `Indeterminate`, and recorded as `verdict.exact = false`. Either way, a definite verdict is invariant over every real value of every unresolved fact, and over both truth values of every opaque part. `tools/check_completion.py` checks this computation against brute force over every assignment, under the three conflict strategies, with the fallback forced, with guards that share variables with rule constraints (`decisions/0003`), and with deadlines and violated preconditions. It has found no mismatch, and 2.5% of its instances are definite where completing every occurrence independently says `Indeterminate`.

*What stays approximate.* Parts that read one fact but are neither identical nor complementary remain independent: `x ≤ 5` and `x > 7` both `T` is still a completion, though no value of `x` produces it, and two permissions on `x = "a"` and `x = "b"` over an enumerated `x` are still `Indeterminate` when `x` is unknown. The cost is an `Indeterminate`, or a wider `verdict_range`, never a wrong definite verdict. Exactness there needs each operand's value domain and is not bounded in general. RL2 makes the same approximation for all shared facts (RL2's `spec/RL2_Semantics.md` § Conflict Resolution). **[O]** — domain-aware completion for enumerated facts (§9 #6). `verdict.exact` is relative to this definition. It says that no fallback was taken beyond `max_mixed` or `max_frontier_vars`, not that the operands' value domains were reasoned over: an exact `Indeterminate` may still be decidable by reasoning over the values (#25).

`frontier_complete` is true iff every completion's frontier is the listed frontier (§6.3). It is false when some uncertain candidate could, in some completion, add or change a frontier alternative without changing the verdict: `Pending` stands, but a completion's frontier may hold routes that are not listed, or lack some that are. "Change" includes removal: an uncertain candidate whose outstanding set is smaller can dominate a listed alternative.

*Computing it* **[D]** (`decisions/0004`, `decisions/0026`). For a definite `Pending`, the *relevant unknowns* are the variables of the `U` parts of uncertain candidates (permission, `owed`, `fulfilled`) and of prohibitions whose finding is `U`. Ready and pending candidates have none, and two `Pending` completions that agree on the relevant unknowns have the same surviving candidates, each with the same outstanding set. So they have the same open routes and the same frontier. With `r` relevant unknowns, at most `max_frontier_vars` (a constant, §3.4), W3 enumerates all `2^r` assignments, with every other unknown at one fixed value. The routes that suffice, and so the listed frontier, are read from those assignments' open routes, and `frontier_complete` is true iff each assignment's frontier is the listed frontier. The two-extremes shortcut does not apply, because a frontier is a set, not a point on the verdict chain. Beyond the bound, W3 lists the routes of the candidates that are ready or pending whatever the unknowns are, and that no completion removes in §6.2, the non-dominated ones. Under `invalid`, a `U` prohibition in a candidate's policy voids the policy in the completions where the prohibition is `T`, so such a candidate is left out. Under `prohibit`, and across policies by prohibit-overrides, such a prohibition gives `Deny` where it is `T`, so a definite `Pending` has none. Each route listed then suffices, since its candidate survives with it in every completion, though some route that suffices may be missing. `frontier_complete` is false and `verdict.exact` is false. The cheaper rule "complete iff no candidate is uncertain" is sound but less exact; `decisions/0004` compares the two, and `tools/check_completion.py` checks the enumeration against the definitions, and that every route the fallback lists suffices.

`verdict_basis` names the determining entries: for `Deny`, the surviving prohibition; the ready alternative's permissions for `Permit`; the frontier's permissions and outstanding duties for `Pending`. Under unknowns these are the entries that play the role in every completion **[D]** (`decisions/0016`, #71): the certain answer, the notion that makes the verdict definite. A `U` entry that plays it in every completion is named. A verdict that holds by cases has no such entry, and its basis is empty. Two prohibitions on `x eq 5` and `x neq 5`, with `x` unresolved, give `Deny` in both completions, each from a different prohibition, so the basis is empty, and `unknown_part` names `x`. `verdict_basis` also names the `U` entries whose completion changes the outcome for `Indeterminate`, and, for a `NotApplicable` where candidates were removed by violated preconditions, those candidates with role `closed` (§3.5).

**Which `U` atoms [D]** (`decisions/0011`). A variable is **pivotal** when flipping it alone changes some completion's verdict. The `unknown` entries are those whose finding is `U` and that have a pivotal variable among their `U` parts. A `U` entry that differs between two disagreeing completions, but could not have moved the verdict, is not named. The pivotal variables are the relevant variables of the verdict as a function of the completions, and the Halpern–Pearl causes of it under some contingency (`references.md` §2). They are read per literal, not per entry, because entries share literals. With them, `verdict_range` gives the least and the greatest completion verdict: the two extremes, or the extremes of the mixed enumeration. *Computing it* **[O]**: by enumeration within a bound, as for `frontier_complete`. Past the bound, every `U` entry is named, and `verdict.exact` is false. The bound is set with W3 (#38, #42).

---

## 7. Replay **[D]**

An evaluation is one run of W2 and W3 over a case (§7.1), identified by its three input collection ids. W2 and W3 are pure, so the trace is a function of the evaluation: replay re-runs them and compares digests, and calls no resolver. The ledger (`due2-architecture.md` §7) records every case: each evaluation, the reads with their values, and the verdict. Re-evaluation is a new evaluation of the same case, over a new SOTW — never an edit to an old trace.

**Crashes [D].** A failure that should never happen, such as a violated contract, a broken invariant, or an I/O fault in the shell, is not a verdict. The shell answers `Error(cause)`. The verdict set stays the five values of §1, and `Indeterminate` keeps its one meaning: the data could not decide. What the caller does with an error is the caller's default, as it is for `Indeterminate`. A crashed evaluation produces no trace. The ledger stores the evaluation and the cause. W2 and W3 are pure, so replaying that evaluation reproduces the crash: the evaluation is the bug report. W1 is the same: a crash in normalisation is an error, not diagnostics, and builds no corpus (`ways-of-working.md` §2.2).

### 7.1 The ledger **[D]** (`decisions/0008`)

The ledger holds cases. A request opens a case under the terms chosen for it — the corpus and the normaliser pins — and everything after it — facts, world edges, evidence, activations, evaluations — is an event on that case, in the order recorded. The SOTW is the case's truth about the world as it evolves: there is no separate revision, only the events so far.

```text
case        (case_id | request, corpus: Digest, pins)
event       (case_id, seq | kind, valid_at?, source_version?, ref)
evaluation  (case_id, seq | sotw: Digest, trace?, verdict?, error?)
```

| Relation | Meaning |
|---|---|
| `case` | The terms the case was opened under: `request` is the request that opened it, `corpus` the id of the corpus chosen then, and `pins` the normaliser versions that built the corpus. `case_id` is assigned by the shell. |
| `event` | `seq` counts from 1, in the order the shell recorded events, and numbers `evaluation` tuples too. `kind ∈ {fact, evidence, activation, closure}`; `ref` is the content id of what was recorded: for a fact, one source's answer, a §3.3 `fact` with its `fact_value` tuples; for a `closure` event, one source's world-module answer: its `closure_answer` tuple, naming the module, the entity asked about, the source, and the status, and the `closure` tuples on the paths up from that entity, possibly none (`decisions/0043`, `decisions/0048`); for evidence and an activation, the §3.3 tuple. `valid_at` is when it held in the world; a fact learned late simply carries an earlier `valid_at`. `source_version` is the version of the source that answered a fact or `closure` event, when the source reports one; W2 never reads it (`decisions/0044`). Policy amendments and normaliser upgrades are not events, and they change no case (below). |
| `evaluation` | The evaluation recorded at `seq`, once; `event` does not repeat it. It holds the SOTW id and the outcome: `trace` and `verdict`, or `error` with its cause. Its corpus and pins are the case's, and its request is the case's with an earlier `at` moved to `effective_at` (§3.2), so §3.5's three input ids are all derived from the case and the SOTW (`decisions/0042`). |

**The SOTW of an evaluation** is the case's events before it, taken as of `sotw.effective_at`: for each property and source, the answer with the latest `valid_at` no later than `effective_at`, and for each world module, entity, and source, likewise; of two answers with the same `valid_at`, the later `seq` counts. Its `closure_answer` holds those world-module answers, and its `closure` is the union of their tuples (`decisions/0043`, `decisions/0048`). A re-evaluation asks no source again: it reads the answers already recorded, and a value that changed in the world reaches the case as a new event from the SOTW service (`decisions/0040`). It is frozen as a collection, and its digest is the evaluation's `sotw` id.

**The current answer** for a case is its latest evaluation.

**A case fixes its terms [D]** (`decisions/0038`, `decisions/0042`). Every evaluation of a case uses the case's request, corpus, and pins, so no case is evaluated against terms it was not opened under; within a case, only the world changes. To apply an amended policy, or a new normaliser version to an earlier request, as for a revocation, the orchestrator opens a new case for the request under the new terms. Its activations start afresh, and evidence recorded on the earlier case counts only if it is recorded again.

**What did we decide, and when.** Earlier decisions are not recomputed: the answer is the earlier `evaluation` event, which with its case pins its inputs, and replay reproduces its trace (§7).

**Append-only.** Events are added, never changed. The shell serialises writes per case.

---

## 8. Laws

Acceptance criteria for any implementation, checked by property tests over generated inputs (`ways-of-working.md` §7).

| | Law |
|---|---|
| **L1** | **Determinism.** Same evaluation, same trace bytes, whatever the tuple order, machine, or locale. |
| **L2** | **Boundaries.** An entry's W2 finding reads no other entry's finding. It is unchanged by adding, removing, or changing other atoms, with one exception: a root obligation's `in_force` in policy `P` reads whether some root `Permit` or `Forbid` of `P` matches the request (§5.2, *In force*), so it can change with those atoms' action, relation, and party parts. W3's output is unchanged by any change to the request or SOTW that leaves W3's inputs from W2 unchanged: `finding`, `basis`, `unknown_part`, and `instance` (§6). A change that leaves the findings alone can still change the others, for example a later `effective_at` that sets an instance's `passed` (`decisions/0032`). |
| **L3** | **Prefetch neutrality.** Adding facts that W2 does not read leaves the trace unchanged, except for the `evaluation` tuple, whose `sotw_id` names the larger SOTW (§3.5). Adding a `resolved` value for a state property that W2 reads and that had none (`unresolved`, §5.4) can only turn `U` into `T` or `F`, or leave it `U` as a misfit (L4). A second value for a property that has one is not covered: under cardinality one it is a `conflict`, and so is an admitted source's answer that differs from another's (§3.3, *Several sources*); either makes the part `U` (`due2-profiles.md` §3). |
| **L4** | **Information monotonicity.** Resolving an unknown never turns `Permit` into `Deny` or back. A value that arrives and fits, for an unresolved or an opaque part, can only replace `Indeterminate`. One that arrives as a misfit, or the answer that none exists, makes a completed part opaque (§6.4), and can turn a definite verdict into `Indeterminate`, never into another definite one (`decisions/0016`). |
| **L5** | **Prohibition monotonicity.** Adding an applicable prohibition never raises the verdict. |
| **L6** | **Duty neutrality.** Conflict resolution (§6.2) reads no duty finding: its eliminations depend only on the candidates that enter it and the prohibitions. Adding, removing, or fulfilling duties changes them only by changing which candidates §6.1 removes with rule `violated_precondition`; when those removals are unchanged, so are the eliminations of §6.2. Under `perm`, for example, timely evidence for a precondition whose deadline has passed restores its permission, which then eliminates its policy's `T` `Forbid`. |
| **L7** | **Readiness.** If some candidate is ready after §6.2, and no surviving `Forbid` is `T` or `U`, the verdict is `Permit`. |
| **L8** | **Skip soundness.** Evaluating more root entries that are certainly `F` leaves the trace unchanged. |
| **L9** | **Preservation.** For a direct interpreter `I` over authored policies (`due2-architecture.md` §10), which completes the authored policy's unknown literals by the same rule (§6.4): `W3(W2(W1(p), r, s)) = I(p, r, s)` whenever `verdict.exact` holds. The parts W1 rewrites — DNF disjuncts, including `xone`'s negated operands and `dprod:not` pushed inward — are identical or complementary to authored ones, so they denote the same variables, and the two sides enumerate the same completions. Opaque parts (§6.4) are variables of their own on the pipeline side and stay `U` in `I`'s tree. W1's rewrites are strong Kleene equivalences, so the tree is `U` exactly when its atoms' disjunction is, and both sides offer W3 the same choices (`decisions/0016`). A duty's condition is rewritten into clauses within its one atom, and the clauses of a kind are disjoined back into one finding (`decisions/0003`, `decisions/0028`). With `exact = false` the law weakens to refinement: a definite pipeline verdict equals `I`'s, and the pipeline may return `Indeterminate` where `I` decides. |
| **L10** | **Explicability** (§3.7, `decisions/0010`). Every entry, atom, part, fact, and evidence id the trace names resolves in the trace, the evaluation's inputs, or the lineages of its policies (§3.6). Every finding's truth is its predicate's connective over its `basis` truths (§5.1–§5.3). For a `fulfilled` finding the connective is per witness: a clause is the Kleene conjunction of its `witness_basis` truths under that witness, the witness satisfies the conditions by the disjunction of its clauses, and the finding is the disjunction of that value over the records named by its `evidence` parts, each conjoined with the record's `evidence` truth (§5.2, §5.3). Every entry in `verdict_basis` or `eliminated` has its findings, and its atom an authored source. |
| **L11** | **Locality** (`decisions/0050`). For policies `P` and `Q` that agree (§4), every W2 tuple that names an entry of `P` is the same in the evaluation of `{P, Q}` as in that of `{P}`, given the same request and SOTW. Adding a policy therefore changes the verdict only through its own entries in W3's fold (§6.2), never by changing what another policy's rules read. |

---

## 9. Open decisions

Scope decisions — which ODRL constructs are admitted, including `invalid` — are registered in `due2-architecture.md` §11. Each row is tracked by the issue it names, and keeps its number when it is resolved, because issues and decision records cite rows by number.

| # | Decision | Section | Blocked on | Issue |
|---|---|---|---|---|
| 2 | Cross-policy strategies other than prohibit-overrides | §6.2 | A real multi-policy corpus | #4 |
| 3 | Declared preference among frontier alternatives | §6.3 | First incomparable frontier in practice | #5 |
| 4 | Monitoring question — the duties a party owes at a given time, independent of any request. Obligations in force for a request are covered by §5.2 and §6.1 | §1 | Obligation-monitoring requirements | #6 |
| 5 | Request match keys beyond `assignee` | §5.2 | Survey of real policies | #7 |
| 6 | Domain-aware completion over parts that read one fact or request field but are neither identical nor complementary (enumerated values, overlapping ranges, distinct values of a single-valued field such as the target). Identical parts that make the same read, and complementary constraint parts, already share a variable (§6.4, `decisions/0012`) | §6.4 | A real policy where the remaining over-approximation matters | #25 |

Rows 1, 7, 8, and 9 are resolved: row 1, the canonical encoding of collections (§2, `decisions/0007`); row 7, cases with several policies, whose files a case adds beside `policy.ttl` and evaluates as one corpus (§4, *Several policies are one corpus*; `conformance/README.md`; case `due2-prohibit-overrides`), while an error in a policy that does not apply is W1's rejection of that policy alone, so it is a negative case of its own (§4); row 8, a request without a target, whose relation part is `U` (§5.2; cases `oval-no-target-permission` and `oval-no-target-prohibition`); and row 9, the read limit, which refuses a request whose plan exceeds it (§3.3, `decisions/0048`).

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
