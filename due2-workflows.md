# due2 — Workflows and Reference Data Model

**Status:** Draft v0.5
**Companions:** `due2-architecture.md` (what due2 is and why) · `odrl-compound-to-atomic-normalization.md` (W1 stage 1, normative) · `ways-of-working.md` (how it is built).

**Changes in v0.5:** duty timing landed — `deadline` and `recurrence` are corpus fields (§3.1), W2 computes the effective deadline and a per-instance status (§5.3, following DPROD `formal-semantics.md` §5.2–5.5), the trace's `instance` carries occurrence and status (§3.5), W3 reads the status and never re-derives it, a violated precondition removes its candidate (§6.1), and the §6.4 proof covers timing. RDF confined to the boundary (appendix; ways-of-working §2.4).

**Changes in v0.4:** after the full corpus sweep (`conformance/`): witness conditions read a dedicated witness source, so a request-source duty condition is a guard, as in DPROD (§5.2, §5.3); a duty with both roles keeps its guards for its root role and has one `fulfilled` finding (§5.2, §5.3); witnesses are performed by the duty's bearer (§5.3); obligation status tabulated (§6.1); why a violation acts as a prohibition rather than DPROD's later check (§6.4); `rdf:type` edges for `isA` in the closure (§3.1); §5.5 aligned with §5.2.

Markers as in the companions: **[D]** decided · **[O]** open, alternatives listed · **[F]** blocked on an external unknown.

**Coherence updates, 2026-10-10** (after `decisions/0002`): L9 restated as a refinement — conditional-duty hoisting splits one unknown into correlated findings completed independently, so the equality as previously written cannot hold under unknowns; L6 scoped to §6.2's conflict eliminations, because `eliminated` now also records `violated_precondition` removals (§3.5, §6.1), which give a closed route visibility in `verdict_basis` (role `closed`); the absent conflict term takes a selected profile's declared default first (normalisation spec §3); §5.3's no-guard sentence scoped to the parent relation.

This document fixes *what* each workflow consumes and produces and what it must preserve. It fixes no algorithm, storage engine, wire format, or language. Any implementation whose outputs satisfy §3–§8 on the conformance suite conforms.

---

## 1. Three workflows and a boundary **[D]**

```
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

- **W1 — Normalise.** Turns authored policies into a flat corpus of atoms. Runs once per policy version. Every semantically interesting rewrite happens here (architecture §2, §4).
- **W2 — Evaluate.** Given a request and a frozen SOTW, gives every relevant atom a three-valued truth value and the parts that determined it. A *map*: an atom's finding depends on that atom, the request, the SOTW, and the configuration — **never on another atom's finding**.
- **W3 — Resolve.** Folds the findings into one verdict: forms candidates, applies conflict strategies, collapses and orders duty alternatives, derives the verdict. Reads the corpus and the findings — **never the request or the SOTW**.

The two *never* clauses are the boundaries. They make W2 parallel and indexable, and W3 testable without a world.

**The boundary that is not a workflow.** Assembling and freezing the SOTW is impure — it fetches, retries, waits — and sits outside all three workflows. W2 reports which state properties it read (§5.4); those with no fact in the SOTW are the shell's cue to resolve them, freeze a new revision, and run W2–W3 again. That loop is orchestration, not semantics. By L3 (§8) it can change a verdict only by supplying missing information.

**One question here, two in the architecture.** Architecture §6.3 separates the access question (*may this request proceed?*) from the monitoring question (*what does this party owe now?*). Both consume W1's corpus and reuse W2's matching, constraint, and fulfilment machinery. They differ in the predicate W2 applies to root atoms and in the reduction W3 performs. This document specifies the access question. Monitoring is **[O]** (§9).

---

## 2. Conventions **[D]**

**Relations.** All data is held as collections of tuples. Each relation declares a key, written before `|`; set semantics apply to the key only. A relation written without `|` is keyed by all of its fields; one with an empty key holds exactly one tuple. Optional fields are written `field?`.

**Identity.** Occurrence identity lives in ids. Two tuples with equal content and different ids never merge — the property a naïve set-of-tuples model loses (architecture §3.1).

**Collections.** Data comes in five collections — Corpus, Request, SOTW, Config, Trace. Each is identified by the digest of its canonical form, and tuples inside a collection do not repeat its id.

**Value types.**

| Type | Meaning |
|---|---|
| `Id` | IRI, compared by equality only. Generated ids are UUID IRIs (normalisation spec §5). |
| `Term` | An `Id`, or a literal `(lexical, datatype[, language])`. Exact numbers are lexical forms with a numeric datatype; there is no floating-point domain. Instants are `xsd:dateTime` in UTC. |
| `Truth` | `T`, `F`, `U` — Kleene strong three-valued logic. |
| `Enum` | A closed set, listed with the field. |

**Canonical form.** Each collection has exactly one canonical serialisation, and its digest is the collection id. Decided: tuples sorted by key in Unicode code-point order of their serialised fields; absent optional fields omitted; no floating point. **[O]** the concrete encoding — JCS JSON arrays or canonical N-Quads. Stage 1 of W1 already emits canonical N-Quads; the corpus encoding is decided with the builder.

---

## 3. Reference data model

### 3.1 Corpus — output of W1

```
policy            (policy_id | conflict, profile, version)
atom              (atom_id | effect, action, relation?, relation_value?, policy_id, source_rule, priority?)
atom_party        (atom_id, function | party)
constraint        (constraint_id | atom_id, scope, left_operand, operator, datatype, unit?)
constraint_value  (constraint_id, value)
edge              (parent_id, child_id)
root              (atom_id)
duty              (atom_id | source_duty, scope, binding_key, deadline?, recurrence?)
closure           (relation, narrower, broader)
```

| Field | Meaning |
|---|---|
| `policy.conflict` | `Enum {prohibit, perm, invalid}` — the source policy's ODRL conflict strategy. An absent term takes a selected profile's declared default first, then `invalid` (normalisation spec §3); W1 makes the result explicit. |
| `atom.effect` | `Enum {Permit, Forbid, Oblige}` — one required field (architecture §3). |
| `atom.action` | The atom's single action, unrefined. Refinements are constraints with scope `action`. |
| `atom.relation`, `relation_value` | At most one relation, `odrl:target` or `odrl:output`, and its value. |
| `atom.policy_id`, `source_rule` | Required provenance. `policy_id` drives the per-source conflict fold in W3; `source_rule` drives explanation. Full lineage is a separate collection (§3.6). |
| `atom.priority` | Used only by a priority-based cross-policy combination (§6.2). |
| `atom_party` | At most one party per function predicate per atom: `assignee`, `assigner`, `informedParty`, … |
| `constraint.scope` | `Enum {rule, action, relation, party:<function>}` — what the constraint refines. An action refinement is scope `action` on *this* atom. It never attaches to the action vocabulary term globally. |
| `constraint` | Conjunctive per atom. W1 has eliminated disjunction. |
| `constraint_value` | Right-operand values: one tuple for a scalar, several for a set operand. |
| `edge` | Parent atom → child duty atom. |
| `root` | The atoms that root an Atomic Policy in W1 stage 1: every `Permit` and `Forbid` atom, and every policy-level obligation. Stored, because it is not derivable: one named duty can be both an obligation of its policy and the precondition of a permission, so a root can also be the child of an edge. |
| `closure` | Direct hierarchy edges declared in the policy and its profile modules — `odrl:includedIn` between actions, typed `odrl:partOf` between assets or parties and their collections, `rdfs:subClassOf`, and `rdf:type` edges — those that type collections and those of individuals an `isA` constraint can compare. ODRL's own action hierarchy is one such module (`profiles/odrl-actions.ttl`). |
| `duty` | For every `Oblige` atom: the authored duty it instantiates, its instance scope `Enum {member, grant}`, and `binding_key` — the digest of `source_duty` and its ground binding (parameter values, inherited party roles, target). W2 derives the duty instance from these (§5.3). Scope defaults to `member`. |
| `duty.deadline` | The authored duty's timing, projected by W1 stage 2 onto every atom it instantiates: an `xsd:dateTime` term (absolute) or an `xsd:duration` term (relative to the instance's activation). W2 resolves it per instance (§5.3). |
| `duty.recurrence` | An RFC 5545 RRULE string; the duty is owed once per occurrence. W2 derives the instances (§5.3). |

Derived, not stored:

- **guard / witness condition** of a duty's constraint, from its bindings (§5.2).
- **role(d)** of a child follows from its parent's effect: `Permit` → precondition, `Forbid` → remedy, `Oblige` → consequence (architecture §3).

Invariants, established by W1 and trusted downstream: `edge` is acyclic; every child is an `Oblige` atom; every `Permit` and `Forbid` atom is a root; every `atom.policy_id` names a `policy`; `Permit` and `Forbid` atoms carry `relation = odrl:target`.

### 3.2 Request

```
request        (| reference?, action, target, at)
request_party  (function | party)
request_param  (name | value)
```

`reference` is the caller's identifier for the request; it also identifies grant-scoped duty instances (§5.3). `at` is the instant of the proposed action — validity time, what ODRL's `dateTime` constrains. The party with `function = assignee` is the subject — the party seeking to act. A request may name other parties, such as a recipient, under other function predicates. `request_param` carries the values of the normalised request that request-source operands read (`due2-profiles.md` §3), keyed by property IRI: purpose, record count, and so on. Nothing else is visible — no credentials, headers, or session state unless a profile exposes them here.

### 3.3 SOTW

```
sotw              (| effective_at, revision)
fact              (property | status)
fact_value        (property, value)
attribution       (property, source | observed_at)
evidence          (evidence_id | occurred_at, actor, action, object?, issuer?, discharges?)
evidence_param    (evidence_id, name | value)
activation        (instance_key | at)
closure           (module, relation, narrower, broader)
```

| Relation | Meaning |
|---|---|
| `sotw.effective_at` | The instant at which the world is observed — decision time. Evidence counts only if it occurred no later. |
| `fact` | One property of the normalised world-state node, which state-source operands read (`due2-profiles.md` §3), and its `status`: `Enum {resolved, missing, invalid, conflict, unresolved}`, never collapsed. *Missing*: the source says no value exists. *Unresolved*: the source could not be asked or did not answer. Whoever assembles the SOTW flattens onto this node everything the policies read — "the requester's department" becomes one property — so computing values is the assembler's job, never W2's. |
| `fact_value` | Exactly one value when `resolved` — for a set-valued operand, its members, of which there may be none — two or more when `conflict`, none otherwise. |
| `evidence` | A record that an action was performed: when, by whom, which action, on what, and who attests it (`issuer`). Approvals, payments, notifications. `discharges` optionally names the duty instance the evidence was submitted against (§5.3). Fulfilment is derived from evidence and never stored as a flag. Signatures and provenance are verified before the SOTW is frozen; W2 only compares `issuer` against configuration (§3.4). |
| `evidence_param` | Parameters of the performed action — an amount, a recipient — the counterpart of `request_param` for a proposed action. Read only by witness-source operands (`due2-profiles.md` §3). |
| `activation` | When a duty instance was first owed, taken from the case history. It anchors relative deadlines and recurrence occurrences (§5.3). |
| `closure` | Direct hierarchy edges from the world rather than from policies — current team membership, say — in a named, versioned module. W2 uses the transitive closure of these together with the corpus's `closure`: `a ⊑ b` holds when `a = b` or a chain of edges leads from `a` to `b`. Closure is closed-world over the declared edges: an edge that is not there does not hold, so the part is `F`, never `U`. |

The SOTW is assembled for one request: flattened properties describe that request's subject and target, and a SOTW is not reused for a request with a different subject or target.

The SOTW is immutable. A later revision may add resolutions. It may not change a terminal one: a re-resolution that disagrees is a `conflict`.

### 3.4 Config

```
config        (| combination, preference?, violations)
signer        (source_duty, issuer)
admit_source  (property, source)
admit_age     (property | max_age)
```

Parameters that are not policy content: the cross-policy `combination` (§6.2), an optional declared `preference` among frontier alternatives (§6.3), and `signer`, the admissibility record for evidence. When a duty has `signer` entries, only evidence whose `issuer` is listed counts for it, and evidence without an issuer counts for nothing. A duty with no entries accepts any issuer (RL2 Model §4.4). `violations` is `ignore` (the default) or `deny` (§6.4). `admit_source` and `admit_age` are the admissibility record for facts: a value whose `attribution` source is not listed for its property, or that was observed longer than `max_age` before `effective_at`, is treated as absent — `missing` (`due2-profiles.md` §3).

### 3.5 Trace — output of W2 and W3

```
case           (| corpus_id, request_id, sotw_id, config_id)
finding        (atom_id, predicate | truth)
basis          (atom_id, kind, ref | truth)
read           (property)
instance       (instance_key | atom_id, occurrence?, status)
eliminated     (atom_id | by_atom, rule)
alternative    (alt_id, permission_id)
alt_duty       (alt_id, duty_id)
dominated      (alt_id | by_alt)
verdict        (| value, frontier_complete)
verdict_basis  (atom_id | role)
```

| Relation | Written by | Meaning |
|---|---|---|
| `case` | shell | The four input collection ids. The case id is the digest of this tuple — derived, not stored. |
| `finding` | W2 | One truth value per evaluated atom and predicate — `applies`, `in_force`, or `fulfilled` (§5.1). |
| `basis` | W2 | The parts that *determine* the finding. `kind ∈ {action, relation, party, constraint, evidence, fact}`; `ref` is the constraint, evidence, state property, or function; `truth` is that part's value. An `F` finding names the part that failed. |
| `read` | W2 | Every state property consulted, determining or not. What the ledger pins (architecture §7); also the dependency index re-evaluation may use. |
| `instance` | W2 | One tuple per evaluated duty instance (§5.3): its atom, the occurrence instant `t` for an instance of a recurring duty (absent otherwise), and its status `Enum {fulfilled, outstanding, violated, unknown}`. The instance key is the key under which a case records what is owed and evidence is submitted. |
| `eliminated` | W3 | A candidate or prohibition removed — by conflict resolution, or by a violated precondition duty instance (§6.1, rule `violated_precondition`) — the atom that removed it, and the rule applied. |
| `alternative`, `alt_duty` | W3 | Candidates collapsed by outstanding duty set: one `alt_id` per distinct set — its digest — with every permission that gives it and every duty in it. |
| `dominated` | W3 | An alternative whose outstanding set strictly contains another's. |
| `verdict` | W3 | The verdict, and whether the reported alternatives are known to be all of them. |
| `verdict_basis` | W3 | The atoms that determined the verdict, by role: `prohibition`, `permission`, `duty`, `unknown`, `obligation` — and `closed`, naming the candidates a violated precondition removed, so a `NotApplicable` that closed a route can be told apart from one where nothing matched. |

### 3.6 Lineage

Which authored rule, which expansion selection, and which parameter binding produced each atom is a separate collection, produced by W1 and referenced by digest from the corpus. W2 and W3 never read it. Explanation and audit do.

---

## 4. W1 — Normalise **[D]**

```
W1 : authored policies → Corpus × Lineage
```

Two stages, both pure, each with its own preservation obligation:

| Stage | Does | Specified in |
|---|---|---|
| **1. Atomise** | Compact interiorisation; expansion of multi-valued action, relation, and party axes; identity and skolemisation; lineage. Structure-preserving: shared duties stay shared. | `odrl-compound-to-atomic-normalization.md` |
| **2. Build** | Constraint DNF, including `xone`; parameter substitution and per-binding duty instantiation; party-role inheritance — a duty that declares no function properties takes all of them from its parent permission (ODRL IM §2.6.5), one that declares any takes none, and for each role a value the rule states beats one interiorised from the policy level (normalisation spec §6.2); conditional-duty hoisting; projection into §3.1; provenance from stage-1 lineage. | architecture §4–§5 |

**Two forms carry a policy through W1.** Stage 1 parses the authored graph into a **lifted tree** — a forest of trees hanging from named rules (normalisation spec §3) — and transforms that; RDF is a boundary format, read at the parse and written at the emit (ways-of-working §2.4). Its artifact is canonical N-Quads. Stage 2 projects the lifted form into the **relations** of §3.1 — collections of tuples whose fields are the terms of §2 — and the relations are all W2 and W3 ever see.

**Position decides conjunction.** Expanding a root rule yields independent root atoms — any one may match a request, which is disjunction. Expanding a nested duty fans out the parent's edges — every resulting duty is owed, which is conjunction. Neither stage declares which fields are disjunctive; it follows from where the value sits.

Obligations on the output:

- **Stage 1 preserves structure.** It preserves the denotation `Den` — the set of ground atomic rules with identity-bearing duty edges — up to a bijection its lineage records (normalisation spec §8.1).
- **Stage 2 preserves meaning.** DNF and hoisting change how many atoms there are, so no bijection exists. Its obligation is L9, checked against a direct interpreter (architecture §10).
- **Sufficiency.** Stage 2 depends on its input only through `Den` — never on node IRIs, triple order, or annotations — and W2 and W3 depend on a policy only through its corpus. So every evaluation depends on an authored policy only through its denotation, which is what lets stage 1's structural guarantee carry through to verdicts.
- **Determinism and bounds.** Isomorphic inputs give identical canonical outputs. A limit breach fails the whole run before any output.
- **Well-formedness.** The §3.1 invariants hold.

---

## 5. W2 — Evaluate **[D]**

```
W2 : Corpus × Request × SOTW × Config → finding × basis × read × instance
```

### 5.1 One predicate per role

Every finding is the truth value of one predicate, chosen by role:

| Atom | Predicate | `T` | `F` | `U` |
|---|---|---|---|---|
| `Permit`, `Forbid` | **applies** (§5.2) | every part `T` | some part `F` | no part `F`, some part `U` |
| root `Oblige` | **in_force** (§5.2) | its policy matches the request and its guards hold | its policy does not match, or a guard fails | otherwise |
| precondition duty; root obligation in force | **fulfilled** (§5.3) | some witness satisfies the duty | every witness fails, or there is none | otherwise |

Duty status reuses the same three values: `T` fulfilled, `F` outstanding, `U` unknown. There is no second status vocabulary. Timing adds a fourth reported state — `violated` — derived in §5.3, not a truth value: it does not enter Kleene combination.

### 5.2 Applies

An atom applies when all of its parts hold, combined by Kleene conjunction (`F ∧ U = F`):

- **action:** `request.action ⊑ atom.action` under the `odrl:includedIn` closure. A request for a narrower action matches an atom on a broader one, never the reverse.
- **relation:** `request.target ⊑ atom.relation_value` under the profile's target closure — collection membership, `isPartOf`.
- **party:** for each `atom_party(a, f, p)` where the profile declares `f` a match key, `request_party(f) ⊑ p` under the party closure. If the request does not name `f`, the part is `U` — absent is not false. Function predicates that are not match keys are carried, not matched. In v1 only `assignee` is a match key.
- **constraint:** each of the atom's constraints, at its scope (§5.4).

The basis records the determining parts: all of them for `T`, the failing ones for `F`, the unknown ones for `U`.

**Guards and witness conditions.** A duty's constraint is a *witness condition* if it reads a witness operand — one bound to `due2:witnessSource`, or `due2:actionTime` — and a *guard* otherwise. Nothing else is declared: the split follows from the bindings (`due2-profiles.md` §3). A guard reads the request, the SOTW, and the context exactly as a permission's constraint does, so a request-source operand in a duty is a guard — DPROD's reading of a duty condition (`formal-semantics.md` §5.2, D-ACTIVATE). A conjunction may mix the two and splits into its parts. A disjunction or negation that mixes them has no reading as either and is rejected at normalisation (`MixedDutyConstraint`). Guards decide *when* a duty is owed; witness conditions decide *what* fulfils it (§5.3). This is RL2's split between `condition` and `postCondition`, and DPROD's between a duty's condition and its performance. A precondition's guards are hoisted into its parent permission by W1 (architecture §4 item 5). A duty that is also a root obligation keeps its guards for that role: hoisting copies them into each parent, and the obligation's `in_force` still reads them.

**In force.** A root obligation of policy `P` is in force for a request when some `Permit` or `Forbid` atom of `P` *matches* the request — action, relation, and parties as above, constraints aside — and the obligation's guards hold, combined by Kleene logic. An obligation is not matched by its own action: it travels with the policy under which the request is made. A log-every-access obligation is therefore in force for a read, which an action match would never achieve.

### 5.3 Fulfilled

Fulfilment follows RL2 (`spec/RL2_Model.md` §4.3, §7.3). It is derived from evidence of performed actions, and the absence of evidence means *not yet fulfilled* — never unknown. The case history is where evidence arrives: a duty with none is outstanding, and the requester is told so through `Pending`.

**Instance.** Each precondition duty `d` resolves to one duty instance, recorded in `instance`:

- scope `member` — the instance key is `binding_key`: the authored duty with its ground binding. Requests that bind the duty identically share the instance, so one fulfilment serves all of them. "Complete annual training" binds to the person; "petition the council about X" binds to the person and X.
- scope `grant` — the instance key is the digest of `source_duty` and `request.reference`: one instance per request, fulfilled only by evidence submitted against it ("pay per use"). A request without a `reference` falls back to `member`.

**Witness.** Evidence `e` is a witness for `d` when:

- `e.occurred_at ≤ sotw.effective_at`;
- `e.action ⊑ d.action`;
- `e.object = d.relation_value`, if `d` has one;
- `e.actor` is `d`'s bearer — the party in the bearer role (`due2-profiles.md` §6: `odrl:assignee` unless a profile says otherwise), after role inheritance (§4) — or the request subject if `d` still names none;
- `signer` admits `e.issuer` for `d`'s `source_duty` (§3.4);
- for scope `grant`, `e.discharges` is `d`'s instance key. For scope `member`, `discharges` is not consulted.

A duty with both roles — an obligation of its policy and a precondition of a permission — is one atom. For a given request it has one instance key in both roles (for scope `grant`, keyed on `request.reference` in both), so it has one `fulfilled` finding, which both roles read.

**Truth.** `d`'s witness conditions are evaluated once per witness: witness-source operands read its `evidence_param`, and `due2:actionTime` is its `occurred_at` (`due2-profiles.md` §3). Every other operand reads the request, the SOTW, or the context as usual. The finding is the Kleene disjunction, over all witnesses, of the conjunction of `d`'s witness conditions: `T` if some witness satisfies them all; `F` if every witness fails one, which includes having no witness; `U` otherwise.

**Deadline and status.** A duty atom may carry timing (§3.1): a `deadline` — an absolute `xsd:dateTime`, or an `xsd:duration` relative to the instance's activation — and a `recurrence`. For an instance with activation `A` (the SOTW's `activation` relation, defaulting to `effective_at`: an instance first owed now):

- the **effective deadline** is `D = deadline` when absolute, `A + duration` when relative, and absent when the duty has none (DPROD `formal-semantics.md` §5.3). Durations are single-kind — day-time or year-month — as §4 of `due2-profiles.md` requires;
- a witness must be timely: it counts only with `occurred_at ≤ min(effective_at, D)`. Performance after `D` does not fulfil — DPROD's D-FULFILL (§5.2 there) — and a late witness does not reopen a deadline;
- the instance's **status**, which W2 writes to the trace (§3.5):

| witness finding | deadline | status |
|---|---|---|
| `T` | any, or none | `fulfilled` |
| `F` | none, or `effective_at ≤ D` | `outstanding` |
| `F` | `effective_at > D` | `violated` |
| `U` | — | `unknown` |

Without a deadline a duty is never violated. Status is derived, never remembered: an evaluation computes it from its evidence, `effective_at`, and `D`, so timely evidence — a witness with `occurred_at ≤ D` — found in a later SOTW makes the instance fulfilled in that evaluation. DPROD instead keeps `Violated` terminal in its duty state Σ (`formal-semantics.md` §9.4); that disagreement is exception 2 (`due2-profiles.md` §8.2). W3 reads the status from the trace and never re-derives it: the deadline comparison is thereby fixed per case — it is a fact of the SOTW, not a finding — which is what keeps W3 pure and the completions of §6.4 well-defined.

**Recurrence.** A duty with `recurrence` is owed once per occurrence of its RRULE. W2 generates the occurrences `t ≤ effective_at` — the anchor is the rule's `DTSTART`, or the duty's activation without one (`due2-profiles.md` §7) — and derives one instance per occurrence: the instance key extends with `t`, the trace's `occurrence` is `t`, the instance's activation is `t`, and a relative deadline is `t + duration`. A witness for an occurrence must also satisfy `occurred_at ≥ t`: one delivery does not fulfil every later instance. DPROD's `performed` check has no lower bound, so one performance fulfils every later instance there — a gap found in DPROD (`due2-profiles.md` §8.2). Occurrences beyond `effective_at` — instances not yet owed — are not generated; reporting them is the open window question (§9, `due2-profiles.md` §9).

Relative to its parent, a duty has no applicability guard of its own here. W1 hoists conditional duties into their parent's constraints (architecture §4), so every duty in the corpus is owed whenever its parent applies. (A duty that is also a root obligation keeps its guards for that role, §5.2.)

Fulfilment is derivation, not bookkeeping. Evidence is appended to the case and the case is evaluated again; no status is ever flipped in place.

### 5.4 Constraints

For a constraint with left operand `o`:

1. `o`'s binding (`due2-profiles.md` §3) gives its source — request, state, or context — its property, value type, cardinality, and allowed operators. Inside a duty's constraints the witness stands in for the request (§5.3).
2. For a state-source operand, W2 records the property in `read` and looks up its `fact`. A request-source operand reads `request_param`; a context operand reads its built-in.
3. Status `resolved` → apply the operator to the value(s) and `constraint_value`(s), giving `T` or `F`. Any other status, or no fact at all → `U`, with basis kind `fact`.
4. The shell finds properties still to resolve as `read` properties with no `fact` in the SOTW. Derived, not recorded twice.

Operators form a closed, typed registry. Strings compare by Unicode code point. No operator consults the clock, the locale, or randomness. Time enters only as `request.at`, `sotw.effective_at`, and evidence times: a constraint on when the action happens (ODRL `dateTime`) reads `request.at` for a permission or prohibition and the witness's `occurred_at` for a duty.

### 5.5 Which atoms

W2 produces a finding for:

- every `Permit` and `Forbid` atom whose finding could be other than `F`;
- every precondition duty of a `Permit` whose finding is not `F`; and
- every root obligation of a policy some of whose `Permit` or `Forbid` atoms match the request (§5.2), with its `fulfilled` finding when `in_force` is `T` or `U`; and
- one `instance` tuple (§3.5) for every duty instance derived above — for a recurring duty, one per occurrence (§5.3).

An index may skip root atoms that are certainly `F` — wrong action, wrong target — because an `F` root is neutral in W3. It may not skip an atom whose match turns on a `U` part. It never skips a precondition of a live permission: an `F` duty is outstanding, which is not neutral. Remedies and consequences are not evaluated for access; they belong to the monitoring question.

---

## 6. W3 — Resolve **[D]**

```
W3 : Corpus × finding × Config → eliminated × alternative × alt_duty × dominated × verdict × verdict_basis
```

Four steps in fixed order. The order is normative: conflict resolution runs before any duty is looked at, so duties can choose among surviving permissions but never decide which survive.

### 6.1 Candidates

A root `Permit` with finding `T` or `U` is a candidate — unless one of its precondition duty instances is `violated` (§5.3). A violated precondition removes its parent's candidacy outright: the route can no longer be taken, and `Pending` must not offer it. The removal is recorded in `eliminated` with rule `violated_precondition`, and `verdict_basis` carries it with role `closed` (§3.5), so the answer distinguishes *a route that closed* from *nothing that matched*. A surviving candidate's **outstanding set** is its precondition duties with finding `F` — a violated one removed the candidate instead of joining the set; its **unknown set**, those with `U`. Each candidate is in exactly one state:

| State | Condition |
|---|---|
| **ready** | permission `T`; no outstanding, no unknown duty |
| **pending** | permission `T`; some outstanding, no unknown duty |
| **uncertain** | permission `U`, or some unknown duty |

Root obligations in force are reported in `verdict_basis` with role `obligation`, with their bearer and, for each of their instances, the status W2 computed (§5.3) — `fulfilled`, `outstanding`, `violated`, or `unknown` — which is what §6.4's `deny` reads. An obligation whose `in_force` is `U` is reported `unknown`, whatever its instance status; one not in force is not reported. Neither status nor bearer is stored beyond the trace. Under `config.violations = ignore`, obligations never affect the verdict; a violated *precondition* still removes its candidate (`due2-profiles.md` §7).

### 6.2 Conflict

1. **Within a source policy**, by its `conflict`. Under `prohibit`, a `T` `Forbid` eliminates that policy's candidates. Under `perm`, a `T` candidate eliminates that policy's `Forbid` atoms. Under `invalid`, a `T` candidate and a `T` `Forbid` together void the policy: all of its atoms are eliminated, with rule `invalid`. **[O]** — whether a void policy contributes nothing, as here, or `Indeterminate` with a cause (architecture §6.2).
2. **Across source policies**, by `config.combination` **[O]**. Default: prohibit-overrides — any surviving `T` `Forbid` eliminates every candidate. Alternatives: permit-overrides; priority-ordered first-applicable on `atom.priority`.

`U` atoms eliminate nothing; they make the verdict uncertain (§6.4). Every elimination is recorded with its rule. Duties play no part.

### 6.3 Collapse and order

Alternatives are formed from surviving ready and pending candidates. Uncertain candidates enter only through §6.4.

1. **Collapse.** Candidates with the same outstanding set — compared by duty id — form one alternative. Two permissions that cost the same are one choice with two grounds, not two choices.
2. **Order by inclusion.** Alternative `A` dominates `B` when `outstanding(A) ⊊ outstanding(B)`. This needs nothing but duty identity: no weights, no costs, no configuration. A ready candidate has the empty set and so dominates every pending one. Authorisation state is not a separate rule — it falls out of the order.
3. **Frontier.** The non-dominated alternatives. If there are several, they are incomparable — neither demands a subset of the other's duties — and W3 reports all of them. Each outstanding duty is reported with its bearer, so a route that waits on someone other than the requester — a second approver — says so.

**Sorting [O].** Inclusion is a partial order, and the frontier is its honest output. A total order needs a declared preference — fewest duties, declared weights, a ranking of duty kinds — in `config.preference`. Without one, alternatives are listed in a deterministic order (outstanding-set size, then `alt_id`) that expresses **no** preference. Storage order, upload time, and evaluation order never break a tie.

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

Under `deny`, a violated obligation in force acts as a surviving prohibition. DPROD instead checks violations only once a permission is active (`formal-semantics.md` §7.2, steps 5–6). Withholding only `Permit` and `Pending` would let a new permission turn `NotApplicable` into `Deny`, which breaks monotonicity and with it the two-completion computation below. due2 keeps monotonicity; the difference is DPROD exception 6 (`due2-profiles.md` §8.2).

**Computing it.** Order the completion verdicts `Deny < NotApplicable < Pending < Permit`. Under all three strategies and the default combination, the verdict is monotone in every finding: making a permission or a duty more true never lowers it, and making a prohibition more true never raises it.

*Proof*, by cases on one finding changing from `F` to `T`. The verdict rises with the candidate set and falls with the set of surviving `T` prohibitions, so it suffices to track those two sets.

- **A duty.** §6.2 never looks at duties, so candidates and eliminations are unchanged; one outstanding set shrinks, a pending candidate may become ready, and a candidate removed by a violated precondition re-enters. The verdict stays or rises.
- **A permission `p` of policy `P`.** Under `prohibit`, `p` is eliminated if `P` has a `T` prohibition and is otherwise a new candidate. Under `perm`, `p` is a new candidate and eliminates `P`'s prohibitions. Under `invalid`, if `P` has a `T` prohibition: either `P` already had a `T` candidate and was void already, so nothing changes, or its prohibition survived before and the verdict was `Deny`, the minimum. Candidates are only added and prohibitions only removed. The verdict stays or rises.
- **A prohibition `f` of policy `P`.** Under `prohibit`, `f` survives. Under `perm`, `f` is eliminated if `P` has a `T` candidate and survives otherwise. Under `invalid`, if `P` has a `T` candidate, `P` is voided: its candidates go, and so do its prohibitions — which were all `F`, or `P` would already have been void. Candidates are only removed and prohibitions only added. The verdict stays or falls.
- **Under `violations = deny`, an obligation's `in_force` finding, or a duty's `fulfilled` finding.** A violated instance of an obligation in force acts as a surviving prohibition. The status is computed by W2 from the `fulfilled` finding and the deadline, which the case fixes (§5.3); it is not itself a finding, so it does not vary between completions — within a completion, the violated instances are exactly the `F` duties whose deadline has passed. Making `in_force` more true can only add a violated obligation, and making `fulfilled` more true can only remove one — a violated precondition also restores its candidate. So `in_force` is completed like a prohibition, and `fulfilled` like any duty. ∎

The verdict is therefore a monotone map from completions — ordered with prohibitions reversed — into a chain. Every completion's verdict lies between that of the most restrictive completion (permissions and duties `F`, prohibitions `T`) and that of the most permissive one (the reverse). If the two agree, every completion agrees, so the definition costs two evaluations, not exponentially many. A randomised check — 20,000 instances, every completion of each enumerated — found no counterexample. Reading `invalid` as `Indeterminate` instead would add a value outside the chain, so that alternative needs its own argument.

**Completions range over findings, not facts.** Two findings that read the same fact are completed independently, including combinations no value of the fact could produce: `x ≤ 5` and `x > 5` both `F`, say. The definition therefore errs only towards `Indeterminate` — and normalisation can widen the error: conditional-duty hoisting splits one unknown fact into two findings completed independently, so the normalised verdict can be `Indeterminate` where the authored policy decides (L9 records this as refinement; #6's exact completion over the shared fact restores equality). A definite verdict is still invariant over every real value of every unknown fact, but some `Indeterminate` verdicts would be definite under an exact reading — two permissions on `x = true` and `x = false` with `x` unknown permit for every value of `x`. Completing over fact values instead would be exact, but it needs each operand's value domain and is not bounded in general. RL2 makes the same approximation (Semantics §Conflict Resolution). **[O]** — an exact refinement for the common case of a shared Boolean or enumerated fact (§9).

`frontier_complete` is false when some uncertain candidate could, in some completion, add or change a frontier alternative without changing the verdict: `Pending` stands, but the listed alternatives may not be all of them.

`verdict_basis` names the determining atoms: the surviving prohibition for `Deny`; the ready alternative's permissions for `Permit`; the frontier's permissions and outstanding duties for `Pending`; the `U` atoms whose completion changes the outcome for `Indeterminate`; and, for a `NotApplicable` where candidates were removed by violated preconditions, those candidates with role `closed` (§3.5).

---

## 7. Replay **[D]**

A case is its four input collection ids. W2 and W3 are pure, so the trace is a function of the case: replay re-runs them and compares digests, and calls no resolver. The ledger (architecture §7) stores the case, the reads with their values, and the verdict. Re-evaluation is a new case with a new SOTW — never an edit to an old trace.

---

## 8. Laws

Acceptance criteria for any implementation, checked by property tests over generated inputs (ways-of-working §7).

| | Law |
|---|---|
| **L1** | **Determinism.** Same case, same trace bytes, whatever the tuple order, machine, or locale. |
| **L2** | **Boundaries.** An atom's W2 finding is unchanged by adding, removing, or changing other atoms. W3's output is unchanged by any change to request or SOTW that leaves the findings unchanged. |
| **L3** | **Prefetch neutrality.** Adding resolutions W2 does not read leaves the trace unchanged. Adding ones it reads can only turn `U` into `T` or `F`. |
| **L4** | **Information monotonicity.** Resolving an unknown never turns `Permit` into `Deny` or back; it can only replace `Indeterminate`. |
| **L5** | **Prohibition monotonicity.** Adding an applicable prohibition never raises the verdict. |
| **L6** | **Duty neutrality.** Conflict resolution (§6.2) never looks at duties: its eliminations are unchanged by adding, removing, or fulfilling them. (The `violated_precondition` eliminations of §6.1 are duty-driven by design and outside this law.) |
| **L7** | **Readiness.** If some candidate is ready after §6.2 and no surviving `Forbid` is `T` or `U`, the verdict is `Permit`. |
| **L8** | **Skip soundness.** Evaluating more root atoms that are certainly `F` leaves the trace unchanged. |
| **L9** | **Preservation (refinement).** For a direct interpreter `I` over authored policies (architecture §10): when every finding is definite, `W3(W2(W1(p), r, s), c) = I(p, r, s, c)`. With unknowns, a definite pipeline verdict still equals `I`'s — the real fact values induce one completion, and if all completions agree, so does that one — but the pipeline may return `Indeterminate` where `I` decides: conditional-duty hoisting splits one unknown fact into correlated findings that §6.4 completes independently. Equality under unknowns is restored only by the exact completion over the shared fact (§9 #6). |

---

## 9. Open decisions

Scope decisions — which ODRL constructs are admitted, including `invalid` — are registered in the architecture (§11).

| # | Decision | Section | Blocked on |
|---|---|---|---|
| 1 | Concrete canonical encoding of collections | §2 | Builder design |
| 2 | Cross-policy combination default | §6.2 | A real multi-policy corpus |
| 3 | Declared preference among frontier alternatives | §6.3 | First incomparable frontier in practice |
| 4 | Monitoring question — duties currently owed by a party, independent of any request. Obligations in force for a request are covered by §5.2 and §6.1 | §1 | Obligation-monitoring requirements |
| 5 | Request match keys beyond `assignee` | §5.2 | Survey of real policies |
| 6 | Exact completion over a shared Boolean or enumerated fact | §6.4 | A real policy where the over-approximation matters |
| 7 | Cases with several policies, needed to test cross-policy combination and errors in policies that do not apply | §6.2 | Case-format extension |

Deadline windows and the `violated` status, open as #5 until v0.4, are decided in §5.3: timing is in the corpus, W2 computes the effective deadline and the per-instance status, and a violated precondition removes its candidate. What stays open is the *not-yet-owed* state of an instance whose occurrence or window is in the future (`due2-profiles.md` §9).

---

## Appendix — Why tuples

Three representations were credible.

| | W2 (map) | W3 (join, group, fold) | Occurrence identity | Note |
|---|---|---|---|---|
| **Typed relations** | an atom is a row | native | explicit keys | Chosen. The model is the interface; any language or store can hold it. |
| RDF graph | an atom is a subgraph | SPARQL | skolem IRIs | Already the stage-1 form. A finding with truth and basis is n-ary and needs reification, and SPARQL filter semantics turn evaluation errors into false — the collapse ways-of-working §5.1 forbids. |
| Nested documents | natural | joins in application code | natural | Fits one policy; fights the cross-policy fold and the grouping into alternatives. |

The builder projects the lifted stage-1 form into relations. RDF is a boundary format, not a working representation (ways-of-working §2.4): stage 1 parses the authored graph into a tree, transforms the tree, and emits canonical N-Quads as its artifact; stage 2 consumes the lifted form, and nothing downstream of the parse sees RDF.
