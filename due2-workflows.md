# due2 — Workflows and Reference Data Model

**Status:** Draft v0.1
**Companions:** `due2-architecture.md` (what due2 is and why) · `odrl-compound-to-atomic-normalization.md` (W1 stage 1, normative) · `ways-of-working.md` (how it is built).

Markers as in the companions: **[D]** decided · **[O]** open, alternatives listed · **[F]** blocked on an external unknown.

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
- **W2 — Evaluate.** Given a request and a frozen SOTW, gives every relevant atom a three-valued truth value and the parts that determined it. A *map*: an atom's finding depends on that atom, the request, and the SOTW — **never on another atom's finding**.
- **W3 — Resolve.** Folds the findings into one verdict: forms candidates, applies conflict strategies, collapses and orders duty alternatives, derives the verdict. Reads the corpus and the findings — **never the request or the SOTW**.

The two *never* clauses are the boundaries. They make W2 parallel and indexable, and W3 testable without a world.

**The boundary that is not a workflow.** Assembling and freezing the SOTW is impure — it fetches, retries, waits — and sits outside all three workflows. W2 reports which requirements it read (§5.4); those with no resolution in the SOTW are the shell's cue to resolve them, freeze a new revision, and run W2–W3 again. That loop is orchestration, not semantics. By L3 (§8) it can change a verdict only by supplying missing information.

**One question here, two in the architecture.** Architecture §6.3 separates the access question (*may this request proceed?*) from the monitoring question (*what does this party owe now?*). Both consume W1's corpus and reuse W2's matching, constraint, and fulfilment machinery. They differ in the predicate W2 applies to root atoms and in the reduction W3 performs. This document specifies the access question. Monitoring is **[O]** (§9).

---

## 2. Conventions **[D]**

**Relations.** All data is held as collections of tuples. Each relation declares a key, written before `|`; set semantics apply to the key only. A relation with an empty key holds exactly one tuple. Optional fields are written `field?`.

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
```

| Field | Meaning |
|---|---|
| `policy.conflict` | `Enum {prohibit, perm, invalid}` — the source policy's ODRL conflict strategy. W1 makes an absent term explicit as `invalid`. |
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

Derived, not stored:

- **root(a)** ⇔ no `edge(_, a)`. Roots are what a request is matched against. A root `Oblige` atom is a policy-level obligation.
- **role(d)** of a child follows from its parent's effect: `Permit` → precondition, `Forbid` → remedy, `Oblige` → consequence (architecture §3).

Invariants, established by W1 and trusted downstream: `edge` is acyclic; every child is an `Oblige` atom; every `atom.policy_id` names a `policy`; `Permit` and `Forbid` atoms carry `relation = odrl:target`.

### 3.2 Request

```
request        (| reference?, action, target, at)
request_party  (function | party)
request_param  (name | value)
```

`reference` is the caller's identifier for the request. The party with `function = assignee` is the subject — the party seeking to act. A request may name other parties, such as a recipient, under other function predicates. `request_param` carries the values the operand registry exposes to constraints: purpose, record count, and so on. Nothing else is visible — no credentials, headers, or session state unless a profile exposes them here.

### 3.3 SOTW

```
sotw              (| effective_at, revision)
requirement       (requirement_id | operand)
requirement_arg   (requirement_id, name | value)
resolution        (requirement_id | status)
resolution_value  (requirement_id, value)
attribution       (requirement_id, source | observed_at)
event             (event_id | action, target?, at)
event_party       (event_id, function | party)
evidence_scope    (scope_id | action?, target?, party?, complete_through)
closure           (module, relation, narrower, broader)
```

| Relation | Meaning |
|---|---|
| `requirement` | One operand applied to its arguments — "department of alice". `requirement_id` is the digest of operand and arguments, so W2 computes it without consulting the SOTW. |
| `resolution.status` | `Enum {resolved, missing, invalid, conflict, unresolved}`, never collapsed. *Missing*: the source says no value exists. *Unresolved*: the source could not be asked or did not answer. |
| `resolution_value` | Exactly one value when `resolved`, two or more when `conflict`, none otherwise. |
| `event` | Something that happened: an observed action, its parties, its time. Approvals, payments, notifications. Fulfilment is derived from events (§5.3) and never stored as a flag. |
| `evidence_scope` | A source's claim that its record of events is complete through `complete_through` for the given action, target, and party. An absent field means any. Without such a claim, absence of an event proves nothing. |
| `closure` | Transitive closure of a named, versioned hierarchy: `odrl:includedIn`, `skos:broader`, class or membership relations. `a ⊑ b` holds when `a = b` or `closure(m, rel, a, b)`. |

The SOTW is immutable. A later revision may add resolutions. It may not change a terminal one: a re-resolution that disagrees is a `conflict`.

### 3.4 Config

```
config  (| combination, preference?)
```

The W3 parameters that are not policy content: the cross-policy `combination` (§6.2) and an optional declared `preference` among frontier alternatives (§6.3).

### 3.5 Trace — output of W2 and W3

```
case           (| corpus_id, request_id, sotw_id, config_id)
finding        (atom_id | truth)
basis          (atom_id, kind, ref | truth)
read           (requirement_id)
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
| `finding` | W2 | One truth value per evaluated atom. The predicate depends on the atom's role (§5.1). |
| `basis` | W2 | The parts that *determine* the finding. `kind ∈ {action, relation, party, constraint, event, requirement}`; `ref` is the constraint, event, requirement, or function; `truth` is that part's value. An `F` finding names the part that failed. |
| `read` | W2 | Every requirement consulted, determining or not. What the ledger pins (architecture §7); also the dependency index re-evaluation may use. |
| `eliminated` | W3 | A candidate or prohibition removed by conflict resolution, the atom that removed it, and the rule applied. |
| `alternative`, `alt_duty` | W3 | Candidates collapsed by outstanding duty set: one `alt_id` per distinct set — its digest — with every permission that gives it and every duty in it. |
| `dominated` | W3 | An alternative whose outstanding set strictly contains another's. |
| `verdict` | W3 | The verdict, and whether the reported alternatives are known to be all of them. |
| `verdict_basis` | W3 | The atoms that determined the verdict, by role: `prohibition`, `permission`, `duty`, `unknown`, `obligation`. |

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
| **2. Build** | Constraint DNF, including `xone`; parameter substitution and per-binding duty instantiation; conditional-duty hoisting; projection into §3.1; provenance from stage-1 lineage. | architecture §4–§5 |

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
W2 : Corpus × Request × SOTW → finding × basis × read
```

### 5.1 One predicate per role

Every finding is the truth value of one predicate, chosen by role:

| Atom | Predicate | `T` | `F` | `U` |
|---|---|---|---|---|
| root `Permit`, `Forbid`, `Oblige` | **applies** (§5.2) | every part `T` | some part `F` | no part `F`, some part `U` |
| precondition duty | **fulfilled** (§5.3) | a matching event exists | no matching event, within a complete evidence scope | otherwise |

Duty status reuses the same three values: `T` fulfilled, `F` outstanding, `U` unknown. There is no second status vocabulary.

### 5.2 Applies

An atom applies when all of its parts hold, combined by Kleene conjunction (`F ∧ U = F`):

- **action:** `request.action ⊑ atom.action` under the `odrl:includedIn` closure. A request for a narrower action matches an atom on a broader one, never the reverse.
- **relation:** `request.target ⊑ atom.relation_value` under the profile's target closure — collection membership, `isPartOf`.
- **party:** for each `atom_party(a, f, p)` where the profile declares `f` a match key, `request_party(f) ⊑ p` under the party closure. If the request does not name `f`, the part is `U` — absent is not false. Function predicates that are not match keys are carried, not matched. In v1 only `assignee` is a match key.
- **constraint:** each of the atom's constraints, at its scope (§5.4).

The basis records the determining parts: all of them for `T`, the failing ones for `F`, the unknown ones for `U`.

### 5.3 Fulfilled

A precondition duty `d` is fulfilled when some event `e` with `e.at ≤ sotw.effective_at` matches it:

- `e.action ⊑ d.action`;
- `e.target = d.relation_value`, if `d` has one;
- the obligated party performed it: `event_party(e, assignee)` is `d`'s assignee, or the request subject if `d` names none;
- each of `d`'s constraints holds for `e`.

The finding is `T` if a matching event exists; `F` if none matches and an `evidence_scope` covering `d`'s action, target, and party is complete through `effective_at`; `U` otherwise. Without completeness claims, absence of evidence is not evidence of absence and `Pending` is unreachable: every unfulfilled duty would be `U`.

Fulfilment is matching, not bookkeeping. Two duties with identical ground content are fulfilled by the same event — ODRL's shared duty, fulfilled once. Keeping attachments apart is therefore a matter of binding a duty's target to its parent's, not of identity (architecture §3.1).

### 5.4 Constraints

For a constraint with left operand `o`:

1. The operand registry (profile metadata) gives `o`'s provider — request field, request parameter, or SOTW requirement — its value type, cardinality, and allowed operators.
2. For a SOTW provider, W2 computes the `requirement_id`, records it in `read`, and looks up its `resolution`.
3. Status `resolved` → apply the operator to the value(s) and `constraint_value`(s), giving `T` or `F`. Any other status, or no resolution at all → `U`, with basis kind `requirement`.
4. The shell finds requirements still to resolve as `read` requirements with no `resolution` in the SOTW. Derived, not recorded twice.

Operators form a closed, typed registry. Strings compare by Unicode code point. No operator consults the clock, the locale, or randomness; time enters only as `sotw.effective_at` and event times.

### 5.5 Which atoms

W2 produces a finding for:

- every root atom whose finding could be other than `F`; and
- every precondition duty of a root `Permit` whose finding is not `F`.

An index may skip root atoms that are certainly `F` — wrong action, wrong target — because an `F` root is neutral in W3. It may not skip an atom whose match turns on a `U` part. It never skips a precondition of a live permission: an `F` duty is outstanding, which is not neutral. Remedies and consequences are not evaluated for access; they belong to the monitoring question.

---

## 6. W3 — Resolve **[D]**

```
W3 : Corpus × finding × Config → eliminated × alternative × alt_duty × dominated × verdict × verdict_basis
```

Four steps in fixed order. The order is normative: conflict resolution runs before any duty is looked at, so duties can choose among surviving permissions but never decide which survive.

### 6.1 Candidates

Every root `Permit` with finding `T` or `U` is a candidate. Its **outstanding set** is its precondition duties with finding `F`; its **unknown set**, those with `U`. Each candidate is in exactly one state:

| State | Condition |
|---|---|
| **ready** | permission `T`; no outstanding, no unknown duty |
| **pending** | permission `T`; some outstanding, no unknown duty |
| **uncertain** | permission `U`, or some unknown duty |

Root `Oblige` atoms that apply do not affect the verdict. They are reported in `verdict_basis` with role `obligation`.

### 6.2 Conflict

1. **Within a source policy**, by its `conflict`. Under `prohibit`, a `T` `Forbid` eliminates that policy's candidates. Under `perm`, a `T` candidate eliminates that policy's `Forbid` atoms. Under `invalid`, a `T` candidate and a `T` `Forbid` together void the policy: all of its atoms are eliminated, with rule `invalid`. **[O]** — whether a void policy contributes nothing, as here, or `Indeterminate` with a cause (architecture §6.2).
2. **Across source policies**, by `config.combination` **[O]**. Default: prohibit-overrides — any surviving `T` `Forbid` eliminates every candidate. Alternatives: permit-overrides; priority-ordered first-applicable on `atom.priority`.

`U` atoms eliminate nothing; they make the verdict uncertain (§6.4). Every elimination is recorded with its rule. Duties play no part.

### 6.3 Collapse and order

Alternatives are formed from surviving ready and pending candidates. Uncertain candidates enter only through §6.4.

1. **Collapse.** Candidates with the same outstanding set — compared by duty id — form one alternative. Two permissions that cost the same are one choice with two grounds, not two choices.
2. **Order by inclusion.** Alternative `A` dominates `B` when `outstanding(A) ⊊ outstanding(B)`. This needs nothing but duty identity: no weights, no costs, no configuration. A ready candidate has the empty set and so dominates every pending one. Authorisation state is not a separate rule — it falls out of the order.
3. **Frontier.** The non-dominated alternatives. If there are several, they are incomparable — neither demands a subset of the other's duties — and W3 reports all of them.

**Sorting [O].** Inclusion is a partial order, and the frontier is its honest output. A total order needs a declared preference — fewest duties, declared weights, a ranking of duty kinds — in `config.preference`. Without one, alternatives are listed in a deterministic order (outstanding-set size, then `alt_id`) that expresses **no** preference. Storage order, upload time, and evaluation order never break a tie.

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

**Computing it.** Order the completion verdicts `Deny < NotApplicable < Pending < Permit`. Under all three strategies and the default combination, the verdict is monotone in every finding: making a permission or a duty more true never lowers it, and making a prohibition more true never raises it. So the most restrictive completion (permissions and duties `F`, prohibitions `T`) gives the minimum and the most permissive (the reverse) gives the maximum. If the two agree, every completion agrees. The definition therefore costs two evaluations, not exponentially many.

Monotonicity and the shortcut were checked exhaustively over 20,000 random instances with up to three policies of mixed strategy, shared duties, and every completion. Reading `invalid` as `Indeterminate` instead would add a value outside the order, so that alternative needs its own argument.

`frontier_complete` is false when some uncertain candidate could, in some completion, add or change a frontier alternative without changing the verdict: `Pending` stands, but the listed alternatives may not be all of them.

`verdict_basis` names the determining atoms: the surviving prohibition for `Deny`; the ready alternative's permissions for `Permit`; the frontier's permissions and outstanding duties for `Pending`; the `U` atoms whose completion changes the outcome for `Indeterminate`.

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
| **L6** | **Duty neutrality.** Adding, removing, or fulfilling duties never changes `eliminated`. |
| **L7** | **Readiness.** If some candidate is ready after §6.2 and no surviving `Forbid` is `T` or `U`, the verdict is `Permit`. |
| **L8** | **Skip soundness.** Evaluating more root atoms that are certainly `F` leaves the trace unchanged. |
| **L9** | **Preservation.** For a direct interpreter `I` over authored policies, `W3(W2(W1(p), r, s), c) = I(p, r, s, c)` — wherever that interpreter is maintained (architecture §10). |

---

## 9. Open decisions

Scope decisions — which ODRL constructs are admitted, including `invalid` — are registered in the architecture (§11).

| # | Decision | Section | Blocked on |
|---|---|---|---|
| 1 | Concrete canonical encoding of collections | §2 | Builder design |
| 2 | Cross-policy combination default | §6.2 | A real multi-policy corpus |
| 3 | Declared preference among frontier alternatives | §6.3 | First incomparable frontier in practice |
| 4 | Monitoring question: root predicate and reduction | §1 | Obligation-monitoring requirements |
| 5 | Per-attachment discharge ("pay once per use"), which matching cannot express | §5.3 | A real duty that needs it |
| 6 | Request match keys beyond `assignee` | §5.2 | Survey of real policies |

---

## Appendix — Why tuples

Three representations were credible.

| | W2 (map) | W3 (join, group, fold) | Occurrence identity | Note |
|---|---|---|---|---|
| **Typed relations** | an atom is a row | native | explicit keys | Chosen. The model is the interface; any language or store can hold it. |
| RDF graph | an atom is a subgraph | SPARQL | skolem IRIs | Already the stage-1 form. A finding with truth and basis is n-ary and needs reification, and SPARQL filter semantics turn evaluation errors into false — the collapse ways-of-working §5.1 forbids. |
| Nested documents | natural | joins in application code | natural | Fits one policy; fights the cross-policy fold and the grouping into alternatives. |

The builder projects stage-1 RDF into relations. Nothing downstream of W1 sees RDF.
