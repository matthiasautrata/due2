# due2 — Profiles and Operand Registry

**Status:** Draft v0.5
**Companions:** `due2-workflows.md` (what W1–W3 consume and produce) · `odrl-compound-to-atomic-normalization.md` (W1 stage 1) · `due2-architecture.md` (why).

**Changes in v0.5:** set-based operators follow the Vocabulary (§3.16.7–3.16.12, §3.14.7): `isPartOf`, `hasPart`, and `isA` take a list right operand, read after Salas and Pareti et al. (2025), and a policy that uses one gets the warning `ContestedOperatorReading` (§4; `decisions/0005`).

**Changes in v0.4:** duty timing landed — `deadline` and `recurrence` are corpus fields and W2 computes the effective deadline, the per-instance status, and the occurrences (`due2-workflows.md` §3.1, §5.3); §7 now fixes the vocabulary's readings and points there for the computation, replacing its own status table; violation is derived, not remembered, against DPROD's terminal `Violated` (§7); the DPROD example policies are vendored under `profiles/vendor/dprod/examples/` and incorporated into the corpus (§8.1). v0.3: a witness source replaces the request source's double reading inside duties (§3); duration kinds (§4); `rdf:type` for `isA` and parties of a duty with both roles (§6); activation defaults to first owed, recurring instances bounded below, anchor rule restated (§7); DPROD exception 6 and the duty-condition correction (§8.2); not-yet-open windows registered (§9).

Markers as in the companions: **[D]** decided · **[O]** open, alternatives listed · **[F]** blocked on an external unknown.

---

## 1. Purpose

ODRL is extended through profiles. due2 must evaluate a profile's terms **without code changes**: every term a profile introduces is declared as data, and normalisation compiles the declaration mechanically. This document fixes the declaration vocabulary, the closed set of extension points it can use, and where each lands in W1–W3.

Two sources are harvested rather than reinvented:

- **DPROD Contracts** (EKGF, `github.com/EKGF/dprod`, branch `develop`, `dprod-contracts/`, commit `50db943`) — an ODRL 2.2 profile for data contracts with deterministic evaluation. Its operand bindings are adopted verbatim, so a DPROD policy is a due2 policy without translation (§8).
- **RL2** (`github.com/matthiasautrata/RL2`) — typed operands, fact resolution, admissibility and freshness, typed profile operators, duty windows.

---

## 2. Extension points **[D]**

A profile may extend ODRL at exactly these points. Anything else a profile defines is metadata: preserved, never evaluated. A profile term that would need a point not on this list is rejected at normalisation with `UnsupportedProfileTerm`.

| # | Extension point | Declared by | Used in |
|---|---|---|---|
| 1 | Left operand binding | `dprod:operandSource`, `dprod:operandProperty`, `rdfs:range`, `due2:cardinality`, `due2:allowedOperator` | W2 §5.4 |
| 2 | Operator | closed core registry; profile operators by reduction | W2 §5.4 |
| 3 | Logical connective | `odrl:and`, `odrl:or`, `odrl:xone`, `dprod:not` | W1 stage 2 |
| 4 | Policy class | `rdfs:subClassOf` an ODRL policy class | W1 stage 1 |
| 5 | Party role | `due2:playsRole` on a function property | W1 stage 2, W2 §5.3 |
| 6 | Duty timing | `dprod:deadline`, `dprod:recurrence` | W1 stage 2 (corpus `duty`), W2 `due2-workflows.md` §5.3 |
| 7 | Hierarchy | `odrl:includedIn` (actions), typed `odrl:partOf` (assets, parties) | SOTW closure |
| 8 | Conflict default | `odrl:conflict` on the profile resource | W1 stage 1 |
| 9 | Duty instance scope | `due2:instanceScope` (default `due2:member`) | W1 stage 2, W2 §5.3 |

**Where declarations come from.** A profile that uses this vocabulary declares itself, as DPROD does for operand bindings. For a profile that does not, due2 ships a *binding module*: a small Turtle file mapping that profile's terms onto the points above (`profiles/<name>.ttl`). A binding module adds declarations; it never changes a profile's own.

**Layer precedence [D].** Bindings resolve through ordered layers: the policy graph first, then the selected profile modules in `odrl:profile` declaration order, then due2's baseline (`profiles/due2-core.ttl`) as the lowest layer. A selected profile rebinding a baseline operand is the intended override, not a conflict; `ConflictingProfileDeclaration` applies only among *selected* modules that declare the same term differently. Declaring `odrl:profile <https://w3id.org/due2/profile#>` selects no extra module — the baseline is always present underneath.

The due2 vocabulary is `https://w3id.org/due2/profile#` (prefix `due2:`). It defines only what DPROD and ODRL do not: cardinality, allowed operators, roles, instance scope, and two context properties.

---

## 3. Left operands **[D]**

Every left operand used in a constraint has exactly one binding: one source and one property. This is DPROD's rule (`formal-semantics.md` §6.2), adopted unchanged.

```turtle
ex:purpose a odrl:LeftOperand ;
    dprod:operandSource dprod:requestSource ;
    dprod:operandProperty odrl:purpose ;
    rdfs:range xsd:string ;
    due2:cardinality due2:one ;
    due2:allowedOperator odrl:eq, odrl:neq, odrl:isAnyOf, odrl:isNoneOf .
```

**Sources are closed:**

| Source | Reads | due2 data (`due2-workflows.md` §3) |
|---|---|---|
| `dprod:requestSource` | a property of the normalised request | `request_param` keyed by the property IRI |
| `dprod:stateSource` | a property of the normalised world-state node | SOTW `fact` keyed by the property IRI |
| `dprod:contextSource` | a built-in | the table below |
| `due2:witnessSource` | inside a duty's constraints only: a parameter of the witness (`due2-workflows.md` §5.3) | `evidence_param` keyed by the property IRI |

| Context property | Value |
|---|---|
| `dprod:agent` | the request subject (`request_party` with `odrl:assignee`) |
| `dprod:clock` | `sotw.effective_at` — decision time |
| `due2:actionTime` | the instant of the action being evaluated: `request.at` for a rule matched against the request, the witness's `occurred_at` inside a duty's constraints (`due2-workflows.md` §5.3) |

**Witness reads are explicit.** A duty is checked against evidence of a performed action (`due2-workflows.md` §5.3). A constraint that reads that evidence says so in its binding: `due2:witnessSource` reads a parameter of the witness, and `due2:actionTime` its time. "Paid at least 100" binds `ex:amount` to the witness source. Every other source keeps its meaning inside a duty: a request-source operand reads the request, which is how DPROD reads a duty condition (`formal-semantics.md` §5.2). An earlier draft let the request source read the witness inside a duty; that gave one binding two meanings by position, and it misread DPROD's duty conditions as conditions on the evidence. The witness source is due2's, outside DPROD's closed set: a policy that must also validate against DPROD's shapes cannot use it, and then its duty constraints are all guards. A witness-source operand outside a duty is rejected at normalisation (`WitnessOutsideDuty`).

**One hop.** Resolution reads one property of one node. Anything nested — "the department of the requester", "the classification of the target" — is flattened onto the request or state node by whoever assembles them, before evaluation. That is DPROD's normalisation rule, and it is what keeps evaluation free of traversal, live lookups, and argument binding: computing a value is the assembler's job, never the evaluator's.

**Resolution.** For a request or state property `p` and a declared range `τ`:

| Values present | Outcome | due2 status |
|---|---|---|
| none | `MissingValue` | `missing` |
| one, conforming to `τ` | the value | `resolved` |
| one, not conforming | `TypeMismatch` | `invalid` |
| several, cardinality `one` | `MultipleValues` | `conflict` |
| several, cardinality `set` | the set | `resolved` |
| source could not answer | — | `unresolved` |

`missing`, `invalid`, `conflict`, and `unresolved` make the constraint `U`. They never make it false (ways-of-working §5.1).

**Defaults.** `rdfs:range` absent means any literal or IRI, compared by identity. A range that is an XSD datatype requires a literal of that datatype (any numeric type for a numeric range). A range that is a class requires an IRI; membership of the class is checked only by `isA`, against declared typing (§6), and otherwise the range documents intent. `due2:cardinality` absent means `one`. `due2:allowedOperator` absent means every core operator whose signature accepts the range (§4).

**Checks at normalisation.** A constraint whose left operand has no binding is rejected with `UnboundLeftOperand`. One whose operator is not allowed, or whose right operand does not conform to the range, is rejected with `OperatorTypeMismatch`. A missing binding is an authoring error, never a runtime unknown.

**Baseline bindings.** `profiles/due2-core.ttl` binds the ODRL Common Vocabulary operands that need no profile: `odrl:dateTime` to `due2:actionTime`, `odrl:purpose` and `odrl:recipient` to the request, and `odrl:payAmount` to the witness source (resolved 2026-10-11, §9 #6). The last makes the idiom of the W3C CG examples and OVAL — "pay at least x" as an `odrl:payAmount` refinement of the duty's `odrl:compensate` — an ordinary witness condition with no per-policy binding. It is still an explicit binding, not a position-dependent reading: outside a duty `odrl:payAmount` is rejected (`WitnessOutsideDuty`), and a policy that means a requested amount binds its own operand, which overrides the baseline (§2 layers). Every other common-vocabulary operand needs a profile binding before use. A selected profile may rebind an operand; DPROD binds `odrl:dateTime` to `dprod:clock`, and under DPROD that binding wins — a selected profile overriding the baseline (§2 layer precedence), not a conflict. Selecting a profile adopts all of its declarations, not just the terms a policy happens to use: a policy that wants `dprod:deadline` but action-time semantics for its time constraints binds its own operand to `due2:actionTime` rather than using `odrl:dateTime`.

**Admissibility and freshness [D].** Configuration may restrict, per state property, the admitted sources and their age (`admit_source`, `admit_age`, `due2-workflows.md` §3.4), as RL2 Model §4.4 does. A value failing the filter is treated as absent: `missing`, never a separate outcome.

---

## 4. Operators **[D]**

A closed, typed core registry. An operand that does not fit an operator's signature is `invalid`, so the constraint is `U`.

| Operator | Left | Right | Holds when |
|---|---|---|---|
| `eq`, `neq` | any | same type | equal or not, by value within the datatype; IRIs by identity; strings by code point |
| `lt`, `lteq`, `gt`, `gteq` | number, `dateTime`, `date`, single-component duration | same type | order within the datatype |
| `isAnyOf`, `isNoneOf` | one value | set | membership or its absence |
| `isAllOf` | set | set | left ⊇ right: the left covers every listed value, and may hold more |
| `isPartOf` | IRI, or set of IRIs | IRI, or list of IRIs | every left value ⊑ some right value, under the profile's declared `partOf` closure |
| `hasPart` | IRI, or set of IRIs | IRI, or list of IRIs | every right value ⊑ some left value, under the same closure |
| `isA` | IRI | class, or list of classes | left is an instance of every listed class, under a declared `rdfs:subClassOf` module |

**Set-based operators.** The Vocabulary calls six operators set-based — `isA`, `hasPart`, `isPartOf`, `isAllOf`, `isAnyOf`, `isNoneOf` (§3.16.7–3.16.12) — and allows a list right operand for exactly those (§3.14.7; IM §2.5.1). Neither the IM nor the Vocabulary says what `isPartOf`, `hasPart`, or `isA` *mean* with a list, and the published formal semantics disagree: Bonatti, Fornara and Harth (2025) give `isPartOf` and `isA` membership (∈) and `hasPart` ∋; Salas, Pareti et al. (2025) give `isPartOf` ⊂, `hasPart` ⊃, and `isA` as the subject's classes ⊇ the listed classes; the W3C workshop's open issues list it (Rodríguez-Doncel 2026, R-V2). **due2 adopts the Salas–Pareti reading** (`decisions/0005`), with three adjustments: inclusion is non-strict; set inclusion is generalised to the `partOf` closure, so `isPartOf` holds when every left value is part of some right value and `hasPart` when every right value is part of some left value, each the Kleene conjunction of a Kleene disjunction; and logic stays Kleene, so a missing or `invalid` value gives `U`, not false. A single IRI on either side is a singleton, and an empty left set makes `isPartOf` hold vacuously. Under an identity closure the readings are exactly Salas–Pareti's ⊆ and ⊇, and `isPartOf` reproduces OVAL's results (`oval-list-right-operand`).

**`isAllOf` covers, it need not equal [D].** The published semantics read `isAllOf` as set equality (Bonatti, Fornara and Harth: =; Salas and Pareti et al.: ≡) or as lying below every right value (Mustafa et al.). due2 keeps left ⊇ right (`decisions/0005`, issue #33). The Vocabulary's "a given value is all of the right operand" says the left has every listed value, not that it has nothing else, and a policy author who lists required purposes or certifications does not mean to exclude the rest. Where the left holds values beyond the list, due2 and OVAL give different answers; no warning is raised, because this is due2's reading of the definition, not a choice among equally supported ones.

Because the reading is adopted, not given by ODRL, normalisation accepts a list right operand or a set-valued left operand on these three operators with the warning `ContestedOperatorReading`, naming the operator and the reading applied. A warning is a diagnostic that does not reject; the corpus carries it (`due2-workflows.md` §3.1 `diagnostic`) into the trace of every case that evaluates the policy (§3.5 there). Every diagnostic code, error or warning, is registered in `due2-diagnostics.md`. Before 2026-10-11 this section admitted lists only for `isAnyOf`, `isNoneOf`, and `isAllOf`, and the shape rejected the others: that was a due2 defect, since lists are valid ODRL for all six.

Mixed-component durations (months with days) and floating-point values are rejected at normalisation, as RL2 does: they have no total order or no exact equality. Durations are ordered only within one kind — day-time durations (days, hours, minutes, seconds) with each other, year-month durations (years, months) with each other. `P1Y` against `P365D` is `invalid`, so `U`.

**Deliberate difference from DPROD.** DPROD's `apply` returns `false` for incomparable operands. due2 returns `U`, because an incomparable value is a data problem, not an unsatisfied condition (§8.2).

**Profile operators [O].** A profile may need an operator outside the registry, such as "within region". Until there is a mechanism to execute an arbitrary denotation safely, a profile operator is admitted only by reduction: either to core operators over a new operand, or to a state property the assembler computes ("`ex:withinRegion` is true"). A general mechanism — typed signature, total denotation, conformance vectors, after RL2 Compilation §9.1 — is open.

---

## 5. Logical connectives **[D]**

`odrl:and`, `odrl:or`, `odrl:xone`, and `dprod:not`. ODRL has no negation; DPROD adds it with one operand. `odrl:andSequence` is rejected at normalisation (`UnsupportedConnective`): it carries ordering semantics and is not flattened into `and`.

Stage 2 of W1 pushes negation inward before DNF: De Morgan for `and` and `or`, and complement operators for atoms — `eq`↔`neq`, `lt`↔`gteq`, `lteq`↔`gt`, `isAnyOf`↔`isNoneOf`. Both rewrites are valid in Kleene logic because an operand that is missing or ill-typed gives `U` on both sides. `not` over `xone` expands `xone` first.

---

## 6. Classes, roles, hierarchies **[D]**

**Policy classes.** A profile may declare `X rdfs:subClassOf odrl:Set | odrl:Offer | odrl:Agreement | odrl:Policy`. Normalisation treats an `X` as that ODRL class, using only declared edges and no further inference. DPROD's `DataOffer` and `DataContract` arrive this way.

**Party roles.** due2 needs two roles that ODRL leaves implicit:

| Role | Meaning | ODRL default | DPROD |
|---|---|---|---|
| `due2:bearer` | who must perform a duty | `odrl:assignee`, after role inheritance (`due2-workflows.md` §4) | `dprod:subjectOfDuty` |
| `due2:beneficiary` | who the duty is performed for | `odrl:assigner` | `dprod:objectOfDuty` |

A function property takes a role through `due2:playsRole` in a profile or binding module. A bearer still absent after inheritance is the request subject.

A duty with both roles is one atom with one set of parties. As a root obligation it receives the policy-level values (normalisation spec §6.2), and those count as its own: it then declares function properties and inherits nothing from the permissions that reference it. Parties stated on the duty itself are the clearest form.

**Hierarchies.** Actions follow the `odrl:includedIn` closure. Assets and parties follow the typed `odrl:partOf` closure: an asset path may pass only through `odrl:AssetCollection`, a party path only through `odrl:PartyCollection`, and a cross-kind path is invalid (`formal-semantics.md` §5.4). `isA` follows `rdf:type` and `rdfs:subClassOf`; the `rdf:type` edges of the individuals it compares travel in the closure like any other edge (`due2-workflows.md` §3.1).

Edges declared in the policy and in its profile modules travel with the policy into the corpus `closure`. ODRL's own action hierarchy is shipped as one such module, `profiles/odrl-actions.ttl`, so `odrl:read ⊑ odrl:use` holds without each policy restating it. Edges about the world — who is in which team today — arrive in the SOTW `closure`; only the edges above the request's own entities are fetched and recorded (`due2-workflows.md` §3.3). W2 uses the transitive closure of both (`due2-workflows.md` §3.1, §3.3). The reading is closed-world over the declared edges: a membership that no edge establishes does not hold. A catch-all collection therefore needs its membership edges supplied, or nothing matches it.

---

## 7. Duties: timing and lifecycle **[D]**

DPROD's timing vocabulary is adopted. It closes what was `due2-workflows.md` open decision #5.

- `dprod:deadline` — an `xsd:dateTime` (absolute) or an `xsd:duration` (relative to activation).
- `dprod:recurrence` — an RFC 5545 RRULE generating instances of a duty.

Both land in the corpus (`due2-workflows.md` §3.1, `duty`), projected by W1 stage 2 from the authored duty onto every atom it instantiates. W2 computes the effective deadline, the per-instance status, and the occurrences (`due2-workflows.md` §5.3), following DPROD's duty lifecycle (`formal-semantics.md` §5.2–§5.5). Timing applies to preconditions and to obligations in force alike. The vocabulary's readings:

- **A deadline is inclusive.** A witness at exactly `D` fulfils; violation needs `effective_at > D`, as in DPROD. RL2's window ends are exclusive, so an RL2 window ending at `E` maps to a deadline one tick before `E`, or to `E` with that one-instant difference accepted.
- **Activation is first owed.** A duty instance is activated at the instant it was first owed — the first trace in which it appears. The case history records it, and the shell supplies it in the SOTW as `activation (instance_key | at)`. An instance with no entry is first owed now: its activation is `effective_at`. No hidden evaluator state. Instances activate separately, so two obligations whose guards first held at different times have different activations.
- **Recurrence anchors.** The occurrences of a recurring duty are anchored on the rule's `DTSTART`, or the duty's activation without one — which always exists, by the default above. An anchor the rule itself does not generate is not an occurrence (RFC 5545 leaves that case undefined). The first time a recurring duty is owed, its activation defaults to now, so its first instance is the rule's next occurrence; later evaluations read the recorded activation from the case history.
- **Violation is derived, not remembered** (`due2-workflows.md` §5.3). DPROD's `Violated` is terminal in its duty state Σ (`formal-semantics.md` §9.4); due2 recomputes per evaluation from evidence, so timely evidence found late fulfils. That disagreement is exception 2 (§8.2).
- **A violated precondition removes its candidate** (`due2-workflows.md` §6.1): W3 does not offer a route that can no longer be taken. Without a deadline, a duty is never violated.
- **Occurrences are bounded by `effective_at`.** DPROD's `expand` is unbounded as written, and its `performed` check has no lower bound, so one performance fulfils every later instance there (§8.2). due2 generates only instances already owed; reporting future ones is the not-yet-owed question (§9).

**Violations and access [D].** DPROD denies a request when a duty matched to it is violated (`formal-semantics.md` §7.2, step 6). due2 makes this configuration, not profile semantics: `config.violations ∈ {ignore, deny}`, default `ignore`. Under `ignore`, duties gate access only as preconditions, and obligations in force are reported. Under `deny`, an obligation in force that is violated denies the request (`due2-workflows.md` §6.4). Selecting the DPROD profile does not switch it on; a DPROD-aligned deployment sets `violations = deny` — aligned, not identical: exception 6 (§8.2) still diverges in the six scenarios where DPROD never collects the duty. due2's "in force" — the obligation's policy matches the request — replaces DPROD's "the duty's own action matches the request", which rarely holds (§8.2).

**Not adopted.** RL2's Maintain duties (invariants that must hold over a window) and Promises. Neither has an ODRL encoding, and no real policy needs them yet.

---

## 8. DPROD Contracts compatibility **[D]**

### 8.1 Term by term

With `profiles/dprod.ttl` selected:

| DPROD term | due2 handling |
|---|---|
| `odrl:Permission`, `Prohibition`, `Duty`, `Set`, `Offer`, `Agreement` | native |
| `dprod:DataOffer`, `dprod:DataContract` | policy classes (§6) |
| `dprod:operandSource`, `dprod:operandProperty`, the three sources | operand bindings (§3) |
| `dprod:currentAgent`, `odrl:dateTime` bound to `dprod:clock` | context built-ins (§3) |
| a duty's `odrl:constraint` | guards, read against the request (§3; `due2-workflows.md` §5.2) — DPROD's activation condition |
| `dprod:not` | connective (§5) |
| `dprod:subjectOfDuty`, `dprod:objectOfDuty` | `due2:bearer`, `due2:beneficiary` (§6) |
| `dprod:deadline`, `dprod:recurrence` | duty timing (§7): corpus fields and the W2 computation are `due2-workflows.md` §3.1, §5.3 |
| `odrl:conflict odrl:prohibit` on the profile | conflict default (§2, point 8) |
| typed `odrl:partOf`, `odrl:includedIn` | closure modules (§6) |
| `dprod:dutyState` | output, not input: due2 derives it (§7) |
| lifecycle statuses (`offerLifecycleStatus`, `contractLifecycleStatus`) | metadata; usable in constraints once flattened onto the request or state node |
| Policy-level target and parties | shared defaults that a rule's own value overrides — DPROD's "inherited from policy if absent" (normalisation spec §6.2) |
| Anonymous rules | admitted, with content-derived identity (normalisation spec §3) |
| ODRL action hierarchy (`odrl:read` ⊑ `odrl:use`) | `profiles/odrl-actions.ttl`, which DPROD's examples assume |
| `Policy.condition` (`formal-semantics.md` §3.4) | no RDF encoding in DPROD, so nothing to map (§8.2) |
| `odrl:Request` as a policy | rejected — so does DPROD |
| `odrl:source` on a collection, without a refinement | admitted, inert: an annotation naming the collection; membership comes from closure edges as for any collection (§6). DPROD rejects it; FORCE's collection cases use it (2026-10-11) |
| collection `odrl:refinement` (with or without `odrl:source`) | rejected — so does DPROD. Open: issue #21; for MDS, the mapper materialises refined membership as closure edges |

Normalisation spec 0.12 makes DPROD's examples admissible: policies may be typed by a profile subclass (§6); an absent `odrl:conflict` takes the selected profile's declared default before falling back to `invalid`; anonymous rules are admitted; and policy-level values fill only what a rule leaves unstated. With `profiles/dprod.ttl` and `profiles/odrl-actions.ttl` selected, every DPROD example passes `tools/check_corpus.py` unchanged.

### 8.2 Semantic relation

DPROD evaluates with two-valued logic and stops at the first resolution error: `Success(decision)` or `Failure(error)`. due2 evaluates with Kleene logic and returns `Indeterminate` only when the unknowns could change the outcome. Outside the six exceptions below:

> **due2 refines DPROD.** If DPROD returns `Success(d)`, due2 returns `d`. If DPROD returns `Failure`, due2 returns a decision or `Indeterminate`.

DPROD succeeds only when the outcome follows from resolved values along its evaluation path, and then every completion of the unread unknowns gives the same outcome — due2's condition for a definite verdict. due2 decides more often because Kleene masking is order-independent (`and(error, false)` is `false` in due2 and `Failure` in DPROD), and because an error in a rule that does not apply does not stop due2. The `dprod-*` cases in `conformance/` check this scenario by scenario.

**Exceptions, where due2 deliberately does not refine DPROD:**

1. **Incomparable operands.** DPROD's `apply` returns `false`; due2 returns `U`. Under a prohibition or `dprod:not`, DPROD's `false` turns malformed data into a `Permit` — DPROD fails open there, and due2 returns `Indeterminate`.
2. **DPROD-only state.** DPROD keeps duty state Σ between evaluations; due2 derives it from evidence and activation (§7). They agree when Σ was produced from the same evidence, in order.
3. **`Pending`.** due2 offers routes for preconditions. DPROD's semantics attaches no duties to permissions, so its examples never yield `Pending` in due2. A DPROD-profile policy that does use `odrl:duty` on a permission gets `Pending` in due2 where DPROD ignores the duty; no case exercises this yet.
4. **Agreement parties.** DPROD lets either party of an Agreement match a rule that names no assignee (`formal-semantics.md` §7.3). due2 reads the policy-level assignee as that rule's assignee. A grantor's request is therefore permitted, or denied by a prohibition, in DPROD where due2 returns `NotApplicable`.
5. **Policy-level target.** DPROD treats the policy target as an applicability gate *and* lets a rule's own target override it (`formal-semantics.md` §7.3, §7.4). due2 reads it only as a default. A rule whose target differs from the policy's is unreachable in DPROD and applies in due2 (`dprod-multi-asset-offer`).
6. **Violated duties.** DPROD collects a duty only when the duty's own action matches the request, and denies for a violation only after a permission is active (`formal-semantics.md` §7.2, steps 1 and 6). due2 reports obligations *in force* — their policy matches the request — and, under `violations = deny`, treats a violated one as a prohibition, which keeps the verdict monotone (`due2-workflows.md` §6.4). Under `ignore`, due2 never denies for a violation, where DPROD does. The two agree whenever no duty is violated (`dprod-hr-data-access` scenario 7).

**Gaps found in DPROD, worth reporting upstream** — bare section numbers below are `dprod-contracts/docs/formal-semantics.md`:

- Matching direction. §7.4 writes `norm.action matches Env.action` and `norm.asset matches Env.asset`, the reverse of §7.3 and of the authoring guide. Read literally, a prohibition on `odrl:use` never matches a `read`.
- Determinism. Step 4 asks whether some prohibition is active, over an unordered set, and fails on the first error. When one prohibition holds and another errors, the outcome depends on order, contradicting the determinism theorem (§9.2).
- Order sensitivity. Left-to-right short-circuit makes `and` and `or` non-commutative under errors (§6.1).
- Incomparable operands. `apply` returning `false` contradicts the fail-fast principle (§6.2), and under negation it fails open.
- Reachability. A rule-level target that differs from the policy target can never be reached (§7.3), and neither can the example's provider duties in `data-contract.ttl`.
- Duty collection. A duty is collected only when its own action matches the requested action (§7.2, step 1), so obligations rarely reach the result. A duty with no subject falls into neither the grantor nor the grantee set (step 2).
- Bearer default. The ontology says an omitted `subjectOfDuty` means the data product owner, which is not a declared operand; `specification.md` §3.2 says consumer duties in an Offer omit it.
- Recurrence. `expand` is unbounded, and the examples' RRULEs have no `DTSTART`, so which occurrences exist is undetermined (§5.5). `performed` has no lower bound, so one performance fulfils every later instance (§5.4).
- Unmapped abstract syntax. `Policy.condition` (§3.4) has no RDF encoding; `effectiveDate` and `expirationDate` are never evaluated; §7.3 does not say how a policy with several targets matches.

## 9. Open decisions

**Tracking.** Open items are recorded as GitHub issues (labels: `open-decision`, `corpus`, `verification`, `work-item`, `parked`). This register remains the specification record: a resolution lands here, and the issue closes.

| # | Decision | Section | Blocked on |
|---|---|---|---|
| 1 | General mechanism for profile operators | §4 | First operator that cannot be reduced |
| 2 | Whether instances beyond `effective_at` — not yet owed — are ever generated and reported, and under what horizon | §7 | First recurring duty where the future window matters |
| 3 | Bearer default for policy-level obligations without a bearer | §6 | Survey of real obligations |
| 4 | Maintain duties and Promises | §7 | A real policy that needs one |
| 5 | A not-yet-owed state for an obligation in force whose window has not opened (RL2's `Pending` before the window starts); today it is reported `outstanding` | §7 | A real duty with a future window |
| 6 | Witness conditions via duty-action refinements | §3 | **Resolved 2026-10-11:** `due2-core` binds `odrl:payAmount` to `due2:witnessSource`. `due2:witnessSource` stays; request and evidence parameters stay separate collections. Evidence: OVAL `duty1-3`, W3C CG C1/C2 (`oval-duty-payment`, `w3c-fs-c1`, `w3c-fs-c2`, `due2-conditional-duties`) |
