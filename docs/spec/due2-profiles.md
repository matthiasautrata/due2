# due2 — Profiles and Operand Registry

**Status:** Draft v0.23
**Companions:** `due2-workflows.md` (what W1–W3 consume and produce) · `odrl-compound-to-atomic-normalization.md` (W1 stage 1) · `due2-architecture.md` (why).

**Changes in v0.23** (2026-10-26, `decisions/0040`, #137): §3 *Admissibility* keeps `admit_source`, which W2 applies when it combines the answers of several sources, and drops `admit_age`, because keeping values current is the SOTW service's job. Earlier changes are in `docs/archive/changes.md`.

Markers as in the companions: **[D]** decided · **[O]** open, alternatives listed · **[F]** blocked on an external unknown.

---

## 1. Purpose

ODRL is extended through profiles. due2 must evaluate a profile's terms **without code changes**: every term a profile introduces is declared as data, and normalisation compiles the declaration mechanically. This document fixes the declaration vocabulary, the closed set of extension points it can use, and where each lands in W1–W3.

Two sources are harvested rather than reinvented:

- **DPROD Contracts** (EKGF, `github.com/EKGF/dprod`, branch `develop`, `dprod-contracts/`, commit `50db943`) — an ODRL 2.2 profile for data contracts with deterministic evaluation. Its operand bindings are adopted verbatim, so a DPROD policy is a due2 policy without translation (§8). Everything due2 adopts from DPROD is provisional against that commit (§8). Its formal semantics, `dprod-contracts/docs/formal-semantics.md` at that commit, is cited below as `formal-semantics.md`; it is not vendored.
- **RL2** (`github.com/matthiasautrata/RL2`) — typed operands, fact resolution, admissibility and freshness, typed profile operators, duty windows. Its documents are cited by path, such as RL2's `spec/RL2_Model.md`.

ODRL's two W3C Recommendations are cited as the IM (the ODRL Information Model 2.2) and the Vocabulary (the ODRL Vocabulary & Expression 2.2).

---

## 2. Extension points **[D]**

A profile may extend ODRL at exactly these points. Anything else a profile defines is metadata: preserved, never evaluated. A profile term that would need a point not on this list is rejected at normalisation with `UnsupportedProfileTerm`.

| # | Extension point | Declared by | Used in |
|---|---|---|---|
| 1 | Left operand binding | `dprod:operandSource`, `dprod:operandProperty`, `rdfs:range`, `due2:cardinality`, `due2:allowedOperator`, `due2:conceptScheme` | W2 (`due2-workflows.md` §5.4) |
| 2 | Operator | closed core registry; profile operators by reduction | W2 (`due2-workflows.md` §5.4) |
| 3 | Logical connective | `odrl:and`, `odrl:or`, `odrl:xone`, `dprod:not` | W1 stage 2 |
| 4 | Policy class | `rdfs:subClassOf` an ODRL policy class | W1 stage 1 |
| 5 | Party role | `due2:playsRole` on a function property | W1 stage 2, W2 (`due2-workflows.md` §5.3) |
| 6 | Duty timing | `dprod:deadline`, `dprod:recurrence` | W1 stage 2 (corpus `duty`), W2 (`due2-workflows.md` §5.3) |
| 7 | Hierarchy | `odrl:includedIn` (actions), typed `odrl:partOf` (assets, parties), `skos:broader` (concepts, §4) | corpus and SOTW closure |
| 8 | Conflict default | `odrl:conflict` on the profile resource | W1 stage 1 |
| 9 | Duty instance scope | `due2:instanceScope` (default `due2:member`) | W1 stage 2, W2 (`due2-workflows.md` §5.3) |

**Where declarations come from.** A profile that uses this vocabulary declares itself, as DPROD does for operand bindings. For a profile that does not, due2 ships a *binding module*: a small Turtle file mapping that profile's terms onto the points above (`profiles/<name>.ttl`). A binding module adds declarations; it never changes a profile's own. A policy that declares a profile for which due2 ships no module, neither the profile's own declarations nor a binding module, is rejected at normalisation with `UnrecognisedProfile` (ODRL IM §3.2): due2 cannot tell what the profile declares, and a declaration it missed, such as a conflict default, could change the verdict.

**Layers [D].** Declarations come from three layers: the policy graph, the selected profile modules, and due2's baseline (`profiles/due2-core.ttl`), from highest to lowest. Declaring `odrl:profile <https://w3id.org/due2/profile#>` selects no extra module, because the baseline is always present underneath. The selected modules form one layer and have no order among themselves: two of them that declare the same term differently are rejected with `ConflictingProfileDeclaration`. A left operand's binding (§3) resolves through the layers in two parts (`decisions/0014`):

- **The type belongs to the lowest declaring layer.** A layer *declares* an operand when it states any of `dprod:operandSource`, `dprod:operandProperty`, `rdfs:range`, `due2:cardinality`, or `due2:allowedOperator` for it. The lowest such layer owns the operand's range, cardinality, and allowed operators, and an attribute it omits takes the §3 default. A higher layer may restate a type attribute only with the owner's value; any other value is rejected with `RetypedOperand`.
- **The source and property may be rebound.** They come from the highest layer that states them. A selected profile or a policy that rebinds a baseline operand is the intended override, not a conflict: DPROD binds `odrl:dateTime` to `dprod:clock`, and its range stays the baseline's `xsd:dateTime`.

Concept schemes (`due2:conceptScheme`, §4) are neither: an operand's schemes are the union of every layer's (`decisions/0015`).

The due2 vocabulary is `https://w3id.org/due2/profile#` (prefix `due2:`). It defines only what DPROD and ODRL do not: cardinality, allowed operators, concept schemes, roles, instance scope, the witness source, and one context property, `due2:actionTime`.

---

## 3. Left operands **[D]**

Every left operand used in a constraint has exactly one binding once the layers of §2 are resolved: one source and one property. This is DPROD's rule (`formal-semantics.md` §6.2), adopted unchanged.

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
| `dprod:stateSource` | a property of the normalised world-state node | SOTW `fact` keyed by the property IRI and the answering source |
| `dprod:contextSource` | a built-in | the table below |
| `due2:witnessSource` | inside a duty's constraints only: a parameter of the witness (`due2-workflows.md` §5.3) | `evidence_param` keyed by the property IRI |

| Context property | Value |
|---|---|
| `dprod:agent` | the request subject (`request_party` with `odrl:assignee`) |
| `dprod:clock` | `sotw.effective_at` — decision time |
| `due2:actionTime` | the instant of the action being evaluated: `request.at` for a rule matched against the request, the witness's `occurred_at` inside a duty's constraints (`due2-workflows.md` §5.3) |

**Witness reads are explicit.** A duty is checked against evidence of a performed action (`due2-workflows.md` §5.3). A constraint that reads that evidence says so in its binding: `due2:witnessSource` reads a parameter of the witness, and `due2:actionTime` its time. "Paid at least 100" binds `ex:amount` to the witness source. Every other source keeps its meaning inside a duty: a request-source operand reads the request, which is how DPROD reads a duty condition (`formal-semantics.md` §5.2). Letting the request source read the witness inside a duty would give one binding two meanings by position, and would misread DPROD's duty conditions as conditions on the evidence. The witness source is due2's, outside DPROD's closed set: a policy that must also validate against DPROD's shapes cannot use it, and then its duty constraints are all guards. A witness-source operand outside a duty is rejected at normalisation (`WitnessOutsideDuty`).

**One hop.** Resolution reads one property of one node. Anything nested — "the department of the requester", "the classification of the target" — is flattened onto the request or state node by whoever assembles them, before evaluation. That is DPROD's normalisation rule, and it is what keeps evaluation free of traversal, live lookups, and argument binding: computing a value is the assembler's job, never the evaluator's.

**Resolution.** For a request property `p`, or one source's answer for a state property `p`, and a declared range `τ`:

| Values present | Outcome | due2 status |
|---|---|---|
| none | `MissingValue` | `missing` |
| one, conforming to `τ` | the value | `resolved` |
| one, not conforming | `TypeMismatch` | `invalid` |
| several, cardinality `one` | `MultipleValues` | `conflict` |
| several, cardinality `set` | the set | `resolved` |
| source could not answer | — | `unresolved` |

`missing`, `invalid`, `conflict`, and `unresolved` make the constraint `U`. They never make it false (`ways-of-working.md` §5.1). Only an `unresolved` value is completed in `due2-workflows.md` §6.4, because only an `unresolved` value is known to exist. A constraint `U` for any other status, or for a value that does not fit its operator, is opaque there: never paired with its complement, so it cannot decide a verdict by cases (`decisions/0016`).

**Kinds [D]** (`decisions/0014`). A value's *kind* says what it can be compared with. Every XSD numeric datatype is one kind, numeric. Every other XSD primitive datatype is a kind of its own, and a derived datatype has its primitive's kind (XSD 1.1 Part 2 §2.4.2, §3.3–3.4), so `xsd:dateTimeStamp` is a `dateTime` and `xsd:dayTimeDuration` a `duration`. A datatype outside XSD, `rdf:langString` included, is a kind of its own. Every IRI has one kind, IRI, whatever its classes. A range has the kind of the values it admits: a datatype range its datatype's kind, a class range the IRI kind. Two classes admit more than one kind (RDF Schema 1.1 §2.1, §2.3): `rdfs:Literal` admits a literal of any kind, and `rdfs:Resource` a value of any kind. So for `OperandRangeMismatch` (*Checks at normalisation*, below), `rdfs:Resource` agrees with every range, and `rdfs:Literal` with every range but a class, whose values are IRIs. A right operand against `rdfs:Literal` need only be a literal.

**Defaults.** `rdfs:range` absent admits a value of any kind. Values are still compared by value within a kind (§4): `"1"^^xsd:integer` equals `"1.0"^^xsd:decimal`, and a left value whose kind differs from the right operand's, such as an IRI against a literal, does not fit the operator, so the constraint is `U` (`decisions/0014`, item 6). A range that is an XSD datatype requires a literal of its kind. A range that is a class requires an IRI; membership of the class is checked only by `isA`, against declared typing (§6), and otherwise the range documents intent. `due2:cardinality` absent means `one`. `due2:allowedOperator` absent means every core operator whose signature accepts the range (§4). A default fills what the layer that owns the operand's type omits (§2).

**Checks at normalisation.** A constraint whose left operand has no binding is rejected with `UnboundLeftOperand`. One whose operator is not allowed, or whose right operand is not of the range's kind, is rejected with `OperatorTypeMismatch`. A binding whose range has a kind other than that of the read property's `rdfs:range`, declared in any loaded layer, is rejected with `OperandRangeMismatch`. In practice this applies to the context properties: an operand that reads `dprod:clock` or `due2:actionTime` has no range or a `dateTime` one, and an operand that reads `dprod:agent` has no range or a class. A missing binding is an authoring error, never a runtime unknown.

These checks are coarse on purpose. They leave out class subsumption and disjointness, so any two class ranges agree; custom datatypes and their facets; coercion between kinds, so a `date` never meets a `dateTime`; unit conversion, which is the assembler's job (*One hop*, above); and the schemas of request and state producers, which due2 does not load. They only reject. Whatever they let through is still checked against the value at evaluation, where a misfit is a `TypeMismatch`, so `U`: a check left out costs a late `U`, never a wrong verdict.

**Layered bindings and DPROD's shapes.** DPROD's `LeftOperandShape` (`profiles/vendor/dprod/shapes/dprod-contracts-shapes.ttl`) requires exactly one source and one property on each left operand of the graph it validates, and has no notion of layers. A policy that rebinds an operand (§2) passes the shape when the policy graph is validated alone, and fails it when the layers are merged into one graph first. As with the witness source, a policy that must pass DPROD's shapes over the merged graph cannot rebind.

**Baseline bindings.** `profiles/due2-core.ttl` binds the ODRL Common Vocabulary operands that need no profile: `odrl:dateTime` to `due2:actionTime`, `odrl:purpose` and `odrl:recipient` to the request, and `odrl:payAmount` to the witness source (§9 #6). The last makes the idiom of the W3C CG examples and OVAL — "pay at least x" as an `odrl:payAmount` refinement of the duty's `odrl:compensate` — an ordinary witness condition with no per-policy binding. It is still an explicit binding, not a position-dependent reading: outside a duty `odrl:payAmount` is rejected (`WitnessOutsideDuty`), and a policy that means a requested amount rebinds its source to `dprod:requestSource` (§2), keeping the baseline's range `xsd:decimal`. Every other common-vocabulary operand needs a profile binding before use. A selected profile may rebind an operand's source and property, never its type (§2): under DPROD, `odrl:dateTime` reads `dprod:clock`, decision time, and is still an `xsd:dateTime`. Selecting a profile adopts all of its declarations, not just the terms a policy happens to use: a policy that wants `dprod:deadline` but action-time semantics for its time constraints rebinds `odrl:dateTime` to `due2:actionTime` in its own graph, the highest layer, or binds an operand of its own.

**Admissibility [D].** Configuration may restrict, per state property, the sources whose answers count (`admit_source`, `due2-workflows.md` §3.4), as RL2's `spec/RL2_Model.md` §4.4 does. W2 combines the admitted answers of a property into one status (`due2-workflows.md` §3.3, *Several sources*). A property whose answers all come from sources that are not admitted is `missing`, never a separate outcome. RL2 also drops a value whose validity interval has ended; due2 has no such filter, because keeping a value current is the SOTW service's job, and a changed value reaches the case as a new event (`decisions/0040`).

---

## 4. Operators **[D]**

A closed, typed core registry. An operand that does not fit an operator's signature is `invalid`, so the constraint is `U`.

| Operator | Left | Right | Holds when |
|---|---|---|---|
| `eq`, `neq` | one value | same kind (§3) | equal or not, by value within the kind: numbers by numeric value, strings by code point, IRIs by identity or under a concept scheme (below) |
| `lt`, `lteq`, `gt`, `gteq` | one number, `dateTime`, `date`, or single-component duration | same kind | order within the kind |
| `isAnyOf`, `isNoneOf` | one value | set | `eq` against some right value, or against none: the Kleene disjunction of the `eq`s, or its negation |
| `isAllOf` | set | set | left ⊇ right: the left covers every listed value, and may hold more |
| `isPartOf` | IRI, or set of IRIs | IRI, or list of IRIs | every left value ⊑ some right value, under the profile's declared `partOf` closure |
| `hasPart` | IRI, or set of IRIs | IRI, or list of IRIs | every right value ⊑ some left value, under the same closure |
| `isA` | one IRI | class, or list of classes | left is an instance of every listed class, under a declared `rdfs:subClassOf` module |

**One value or a set [D]** (`decisions/0025`, #102). An operator whose left is one value compares one value, as the Vocabulary defines it (`odrl:eq`: "a given value equals the right operand"). Over a set-valued operand (§3), normalisation rejects it with `OperatorTypeMismatch`. A set takes `isAllOf`, `isPartOf`, and `hasPart`: "contains `v`" is `hasPart v`.

**Set-based operators.** The Vocabulary calls six operators set-based — `isA`, `hasPart`, `isPartOf`, `isAllOf`, `isAnyOf`, `isNoneOf` (§3.16.7–3.16.12) — and allows a list right operand for exactly those (§3.14.7; IM §2.5.1). Neither the IM nor the Vocabulary says what `isPartOf`, `hasPart`, or `isA` *mean* with a list, and the published formal semantics disagree: Bonatti, Fornara and Harth (2025) give `isPartOf` and `isA` membership (∈) and `hasPart` ∋; Salas, Pareti et al. (2025) give `isPartOf` ⊂, `hasPart` ⊃, and `isA` as the subject's classes ⊇ the listed classes; the W3C workshop's open issues list it (Rodríguez-Doncel 2026, R-V2). **due2 adopts the Salas–Pareti reading** (`decisions/0005`), with three adjustments: inclusion is non-strict; set inclusion is generalised to the `partOf` closure, so `isPartOf` holds when every left value is part of some right value and `hasPart` when every right value is part of some left value, each the Kleene conjunction of a Kleene disjunction; and logic stays Kleene, so a missing or `invalid` value gives `U`, not false. A single IRI on either side is a singleton, and an empty left set makes `isPartOf` hold vacuously. Under an identity closure the readings are exactly Salas–Pareti's ⊆ and ⊇, and `isPartOf` reproduces OVAL's results (`oval-list-right-operand`).

**`isAllOf` covers, it need not equal [D].** The published semantics read `isAllOf` as set equality (Bonatti, Fornara and Harth: =; Salas and Pareti et al.: ≡) or as lying below every right value (Mustafa et al.). due2 keeps left ⊇ right (`decisions/0005`, issue #33). The Vocabulary's "a given value is all of the right operand" says the left has every listed value, not that it has nothing else, and a policy author who lists required purposes or certifications does not mean to exclude the rest. Where the left holds values beyond the list, due2 and OVAL give different answers; no warning is raised, because this is due2's reading of the definition, not a choice among equally supported ones.

Because the reading is adopted, not given by ODRL, normalisation accepts a list right operand or a set-valued left operand on these three operators with the warning `ContestedOperatorReading`, naming the operator and the reading applied. A warning does not reject: the corpus carries it (`due2-workflows.md` §3.1 `diagnostic`) into the trace of every case that evaluates the policy (§3.5 there). `due2-diagnostics.md` registers every code.

**A list or repeated values [D].** A set right operand may be written as one RDF list, `odrl:rightOperand ( ex:a ex:b )`, or as repeated values, `odrl:rightOperand ex:a, ex:b`. The repeated form is what the ODRL JSON-LD context makes of a JSON array, since it does not declare `rightOperand` an `@list`. On the six set-based operators both forms are one right operand, the set of the values, with no warning: no operator in the table above depends on order or repeats. Normalisation rejects four forms with `MalformedConstraint`: more than one value on an operator that is not set-based; a list together with any other value; two or more lists; and the empty list `()`, which ODRL gives no meaning and which would make the constraint's value independent of the request (`decisions/0013` and its amendment).

**Concept operands [D]** (`decisions/0015`, #52). A binding may name the SKOS concept schemes its IRI values come from, with one or more `due2:conceptScheme` values, and an operand's schemes are the union of every layer's (§2). On such an operand IRIs compare under the concept hierarchy (§6): `c ⊑ d` holds when `c = d` or a chain of `skos:broader` edges leads from `c` to `d`. `eq` holds when the request value is ⊑ the right value, and `isAnyOf` when it is ⊑ some right value, so a permission for purpose `dpv:Marketing` covers a request for `dpv:DirectMarketing`. `neq` and `isNoneOf` are their complements, so "not for marketing" excludes direct marketing too. For a request concept `c` and a right concept `d`, `eq` gives:

| `c` | `eq` |
|---|---|
| in one of the operand's schemes, and `c ⊑ d` | `T` |
| in one of the operand's schemes, with no path to `d` | `F`: closed-world over the declared edges, as for actions |
| in none of the operand's schemes | `U`: the value is `invalid`, so a prohibition never silently misses a concept whose edges were not supplied |

Only IRIs are concepts. A string compares by code point whether or not the operand has a scheme, and a string against a concept does not fit, so `U`. The baseline's `odrl:purpose`, which has no range, therefore serves both ways of writing a purpose: as a string, or as a concept once a layer names its scheme. Normalisation rejects, with `OperatorTypeMismatch`, an IRI right operand that is in none of the operand's schemes by the memberships the policy and its profile modules declare, and any operator other than `eq`, `neq`, `isAnyOf`, and `isNoneOf` on an operand with a scheme. Normalisation does not see the SOTW, so a membership that only the SOTW supplies does not save a right operand. A `due2:conceptScheme` on an operand whose range is a datatype is rejected with `InvalidBinding`.

Mixed-component durations (months with days) and floating-point values are rejected at normalisation, as RL2 does: they have no total order or no exact equality. Durations are ordered only within one kind — day-time durations (days, hours, minutes, seconds) with each other, year-month durations (years, months) with each other. `P1Y` against `P365D` is `invalid`, so `U`.

**Values.** A `dateTime`, `date`, or `duration` right operand whose lexical form names no value of its datatype, by the lexical rules of XSD 1.1 Part 2 §3.3.6, §3.3.7, and §3.3.9, is rejected at normalisation with `OperatorTypeMismatch`. Examples are `2026-02-30T12:00:00Z`, a day February lacks; `02026-01-01T00:00:00Z`, a year longer than four digits that starts with `0`; and `P1W`, ISO 8601's week form, which `xsd:duration` lacks. `tools/harness/xsd_time.py` implements the rules. Such a literal is the author's error, fixed by editing the policy. A value read at evaluation that does not fit is a data problem instead: its fact is `invalid` (`due2-workflows.md` §3.3), so `U`.

**Timezones [D]** (`decisions/0024`, #101). A `dateTime` has a timezone, and a `date` has none. XSD orders `dateTime` values, and `date` values, only partially when some have a timezone and some do not: a value with a timezone and one without are incomparable within 14 hours of each other, and their equality is undetermined (XSD 1.1 Part 2 §3.3.7, §3.3.9). Within one shape the order is total. Normalisation rejects a right operand of the other shape with `OperatorTypeMismatch`, and a deadline with `InvalidTiming` (§7). A read value of the other shape does not fit any operator, so `U`. The instants of a request and a SOTW have a timezone too (`due2-workflows.md` §3).

**Deliberate difference from DPROD.** DPROD's `apply` returns `false` for incomparable operands. due2 returns `U`, because an incomparable value is a data problem, not an unsatisfied condition (§8.2).

**Profile operators [O].** A profile may need an operator outside the registry, such as "within region". Without a mechanism to execute an arbitrary denotation safely, a profile operator is admitted only by reduction: either to core operators over a new operand, or to a state property the assembler computes ("`ex:withinRegion` is true"). A general mechanism — typed signature, total denotation, conformance vectors, after RL2's `spec/RL2_Compilation.md` §9.1 — is open (§9 #1).

---

## 5. Logical connectives **[D]**

`odrl:and`, `odrl:or`, `odrl:xone`, and `dprod:not`. ODRL has no negation; DPROD adds it with one operand. `odrl:andSequence` is rejected at normalisation (`UnsupportedConnective`): it carries ordering semantics and is not flattened into `and`.

A logical constraint has exactly one operand property (ODRL IM §2.5.2). One with two, `odrl:and` and `odrl:or` on the same node for example, is rejected (`MalformedConstraint`, `decisions/0034`): ODRL does not say whether the node means the conjunction of the two or their disjunction, and the two readings give different verdicts. `odrl:andSequence` counts as an operand property here, although it is rejected on its own too.

A connective's members may be one RDF list or repeated values, as a set right operand's may (§4). A connective over the empty list, `odrl:and ()` for example, is rejected (`MalformedConstraint`, `decisions/0017`): ODRL gives it no meaning, and the empty conjunction's `T` or the empty disjunction's `F` would decide the rule without looking at the request.

A connective whose list names one node twice is rejected too (`MalformedConstraint`, `decisions/0022`): ODRL IM §2.5.2 requires the operand values to be unique Constraint instances. An `odrl:xone` is also rejected when two of its members that are not logical constraints state the same left operand, operator, unit, and set of right operand values, compared as written terms (`due2-workflows.md` §2 `Term`). The two nodes are distinct instances, so ODRL admits this form, and the rejection is due2's own. Read as positions in the list, as W1's expansion reads it (`due2-workflows.md` §4, stage 2), `xone(a, a, b)` is `b ∧ ¬a` whenever `a` is decided; read as a set, it is `xone(a, b)`. ODRL does not say which reading it means, and an author who lists a condition twice most likely made a mistake. `and` and `or` are idempotent, so two leaves with the same content change nothing there and are admitted.

The members of logical constraints form no cycle: following members from a logical constraint never leads back to it. A cycle is rejected (`MalformedConstraint`), and the diagnostic's ref lists the constraints on it in order: `ex:c odrl:and ( ex:c )`, for example, or `ex:a` listing `ex:b` as a member while `ex:b` lists `ex:a`. ODRL IM §2.5.2 gives a logical constraint's operands as existing Constraint instances and does not say what one that contains itself means, and W1's expansion into DNF (`due2-workflows.md` §4, stage 2) would never end on it. A constraint that two logical constraints list as a member, or that two Rules name, is no cycle and is admitted. Such a constraint is named: stage 1 rejects a blank node referenced twice (`SharedAnonymousNode`) and any cycle of blank nodes (`UnanchoredAnonymousNode`, `odrl-compound-to-atomic-normalization.md` §3), so a cycle that reaches stage 2 runs through named constraints.

Stage 2 of W1 pushes negation inward before DNF: De Morgan for `and` and `or`, and complement operators for atoms — `eq`↔`neq`, `lt`↔`gteq`, `lteq`↔`gt`, `isAnyOf`↔`isNoneOf`. Both rewrites are valid in Kleene logic because an operand that is missing, ill-typed, or a concept outside the operand's schemes (§4) gives `U` on both sides. `not` over `xone` expands `xone` first.

---

## 6. Classes, roles, hierarchies **[D]**

**Policy classes.** A profile may declare `X rdfs:subClassOf odrl:Set | odrl:Offer | odrl:Agreement | odrl:Policy`. Normalisation treats an `X` as that ODRL class, using only declared edges and no further inference. DPROD's `DataOffer` and `DataContract` arrive this way.

**Party roles.** due2 needs two roles that ODRL leaves implicit:

| Role | Meaning | ODRL default | DPROD |
|---|---|---|---|
| `due2:bearer` | who must perform a duty | `odrl:assignee`, after role inheritance (`due2-workflows.md` §4) | `dprod:subjectOfDuty` |
| `due2:beneficiary` | who the duty is performed for | `odrl:assigner` | `dprod:objectOfDuty` |

A function property takes a role through `due2:playsRole` in a profile or binding module. A bearer still absent after inheritance is the request subject.

A duty with both roles is one atom with one set of parties. As a root obligation it receives the policy-level values (`odrl-compound-to-atomic-normalization.md` §6.2), and those count as its own: it then declares function properties and inherits nothing from the permissions that reference it. Parties stated on the duty itself are the clearest form.

**Hierarchies.** Actions follow the `odrl:includedIn` closure. Assets and parties follow the typed `odrl:partOf` closure: an asset path may pass only through `odrl:AssetCollection`, a party path only through `odrl:PartyCollection`, and a cross-kind path is invalid (`formal-semantics.md` §5.4). `isA` follows `rdf:type` and `rdfs:subClassOf`; the `rdf:type` edges of the individuals it compares travel in the closure like any other edge (`due2-workflows.md` §3.1). Concepts follow `skos:broader`, within the concept schemes their operand names (§4; `decisions/0015`). A `skos:narrower` triple is read as the inverse `skos:broader` edge. A concept is in a scheme when it states `skos:inScheme` or `skos:topConceptOf` for it, or the scheme states `skos:hasTopConcept` for the concept (SKOS Reference S7, S8). Membership is not inherited along the hierarchy, as in SKOS, and cross-scheme mappings such as `skos:exactMatch` are not read.

Edges declared in the policy and in its profile modules travel with the policy into the corpus `closure`. ODRL's own action hierarchy is shipped as one such module, `profiles/odrl-actions.ttl`, so `odrl:read ⊑ odrl:use` holds without each policy restating it. Edges about the world — who is in which team today — arrive in the SOTW `closure`; only the edges above the request's own entities are fetched and recorded (`due2-workflows.md` §3.3). W2 uses the transitive closure of both (`due2-workflows.md` §3.1, §3.3). The reading is closed-world over the declared edges: a membership that no edge establishes does not hold. A catch-all collection therefore needs its membership edges supplied, or nothing matches it.

---

## 7. Duties: timing and lifecycle **[D]**

DPROD's timing vocabulary is adopted.

- `dprod:deadline` — an `xsd:dateTime` with a timezone (absolute) or an `xsd:duration` (relative to activation).
- `dprod:recurrence` — an RFC 5545 RRULE generating instances of a duty.

Both are duty terms. On a Policy, a Permission, or a Prohibition, either is rejected with `TimingOutsideDuty`. A duty has at most one of each; a second deadline or recurrence, a deadline of another datatype or whose lexical form names no value of its datatype (§4), or a recurrence that is not an RRULE is rejected with `InvalidTiming` (`due2-diagnostics.md`).

A duty's timing lands in the corpus (`due2-workflows.md` §3.1, `duty`), projected by W1 stage 2 from the authored duty onto every atom it instantiates. W2 computes the effective deadline, the per-instance status, and the occurrences (`due2-workflows.md` §5.3), following DPROD's duty lifecycle (`formal-semantics.md` §5.2–§5.5). Timing applies to preconditions and to obligations in force alike. The vocabulary's readings:

- **A deadline is inclusive.** A witness at exactly `D` fulfils; violation needs `effective_at > D`, as in DPROD. RL2's window ends are exclusive, so an RL2 window ending at `E` maps to a deadline one tick before `E`, or to `E` with that one-instant difference accepted.
- **Activation is first owed.** A duty atom's instance is activated at the instant it was first owed in its case: the first trace in which it appears. The case history records it, and the shell supplies it in the SOTW as `activation (atom_id | at)` (`due2-workflows.md` §3.3). An instance with no entry is first owed now: its activation is `effective_at`. No hidden evaluator state. Duty atoms activate separately, so two obligations whose guards first held at different times have different activations. An instance of one occurrence of a recurring duty is activated at that occurrence, and needs no entry.
- **Recurrence anchors.** The occurrences of a recurring duty are anchored on the rule's `DTSTART`, or the duty's activation without one — which always exists, by the default above. An anchor the rule itself does not generate is not an occurrence (RFC 5545 leaves that case undefined). The first time a recurring duty is owed, its activation defaults to now, so its first instance is the rule's next occurrence; later evaluations read the recorded activation from the case history.
- **Violation is derived, not remembered** (`due2-workflows.md` §5.3). DPROD's `Violated` is terminal in its duty state Σ (`formal-semantics.md` §9.4); due2 recomputes per evaluation from evidence, so timely evidence found late fulfils. That disagreement is exception 2 (§8.2).
- **A violated precondition removes its candidate** (`due2-workflows.md` §6.1): W3 does not offer a route that can no longer be taken. Without a deadline, a duty is never violated.
- **Occurrences are bounded by `effective_at`.** DPROD's `expand` is unbounded as written, and its `performed` check has no lower bound, so one performance fulfils every later instance there (§8.2). due2 generates only instances already owed; reporting future ones is the not-yet-owed question (§9).

**Violations and access [D].** DPROD denies a request when a duty matched to it is violated (`formal-semantics.md` §7.2, step 6). due2 makes this configuration, not profile semantics: `config.violations ∈ {ignore, deny}`, default `ignore`. Under `ignore`, duties gate access only as preconditions, and obligations in force are reported. Under `deny`, an obligation in force that is violated denies the request (`due2-workflows.md` §6.4). Selecting the DPROD profile does not switch it on. A DPROD-aligned deployment sets `violations = deny`, and still differs where DPROD never collects the duty, such as `dprod-hr-data-access` scenario 6 (exception 6, §8.2).

**Not adopted.** RL2's Maintain duties (invariants that must hold over a window) and Promises. Neither has an ODRL encoding, and no policy in the corpus needs them (§9 #4).

---

## 8. DPROD Contracts compatibility **[D]**

**Provisional against upstream [F]** (#35). DPROD is vendored at commit `50db943` of `develop`, and a stack of upstream PRs (EKGF/dprod#275, PRs #264–#282) may still move the ontology — schedules, operand sources, duty-action refinements, offer applicability. Everything due2 adopts from DPROD — the binding vocabulary (§3), `dprod:not` (§5), roles and timing (§6–§7), the term table and the six exceptions below — is decided *as of that commit* and is deferred for adjustment when the stack lands: re-vendor, re-run both checkers, re-derive the `dprod-*` scenarios, and edit the affected rows. due2's own semantics — the Kleene discipline, the fail-safe reading — is not in scope for adjustment; only the adopted terms and the claims about DPROD's behaviour are.

### 8.1 Term by term

With `profiles/dprod.ttl` selected:

| DPROD term | due2 handling |
|---|---|
| `odrl:Permission`, `Prohibition`, `Duty`, `Set`, `Offer`, `Agreement` | native |
| `dprod:DataOffer`, `dprod:DataContract` | policy classes (§6) |
| `dprod:operandSource`, `dprod:operandProperty`, the three sources | operand bindings (§3) |
| `dprod:currentAgent` (read as `dprod:agent`), `odrl:dateTime` bound to `dprod:clock` | context built-ins (§3) |
| a duty's `odrl:constraint` | guards, read against the request (§3; `due2-workflows.md` §5.2) — DPROD's activation condition |
| `dprod:not` | connective (§5) |
| `dprod:subjectOfDuty`, `dprod:objectOfDuty` | `due2:bearer`, `due2:beneficiary` (§6) |
| `dprod:deadline`, `dprod:recurrence` | duty timing (§7): corpus fields and the W2 computation are `due2-workflows.md` §3.1, §5.3 |
| `odrl:conflict odrl:prohibit` on the profile | conflict default (§2, point 8) |
| typed `odrl:partOf`, `odrl:includedIn` | closure modules (§6) |
| `dprod:dutyState` | output, not input: due2 derives it (§7) |
| lifecycle statuses (`offerLifecycleStatus`, `contractLifecycleStatus`) | metadata; usable in constraints once flattened onto the request or state node |
| validity dates (`effectiveDate`, `expirationDate`), `acceptsOffer` | metadata, never evaluated — DPROD's policy grammar has no place for them either (`formal-semantics.md` §3.4). A validity window meant to gate a decision is written as a constraint on `dprod:clock` |
| Policy-level target and parties | shared defaults that a rule's own value overrides — DPROD's "inherited from policy if absent" (`odrl-compound-to-atomic-normalization.md` §6.2) |
| Anonymous rules | admitted, with a minted identity (`odrl-compound-to-atomic-normalization.md` §3, §5.2) |
| ODRL action hierarchy (`odrl:read` ⊑ `odrl:use`) | `profiles/odrl-actions.ttl`, which DPROD's examples assume |
| `Policy.condition` (`formal-semantics.md` §3.4) | no RDF encoding in DPROD, so nothing to map (§8.2) |
| `odrl:Request` as a policy | rejected — so does DPROD |
| `odrl:source` on a collection, without a refinement | admitted, inert: an annotation naming the collection; membership comes from closure edges as for any collection (§6). DPROD rejects it; FORCE's collection cases use it |
| collection `odrl:refinement` (with or without `odrl:source`) | rejected — so does DPROD. Open: issue #21. Whoever assembles the policy can supply a refined membership as closure edges instead (§6) |

`odrl-compound-to-atomic-normalization.md` makes DPROD's examples admissible: policies may be typed by a profile subclass (§6); an absent `odrl:conflict` takes the selected profile's declared default before falling back to `invalid`; anonymous rules are admitted; and policy-level values fill only what a rule leaves unstated. With `profiles/dprod.ttl` and `profiles/odrl-actions.ttl` selected, the policies of `data-contract.ttl` and `data-use-policy.ttl` pass `tools/check_corpus.py` unchanged. Those of `baseline.ttl` and `odcs.ttl` are rejected with `InvalidActionHierarchy` alone: they define the action `ex:conformTo` without the `odrl:includedIn` that ODRL IM §2.4 requires (`decisions/0034`, EKGF/dprod#286). Each of them is extracted as a `dprod-*` case, and the cases that use `ex:conformTo` state the edge.

### 8.2 Semantic relation

DPROD evaluates with two-valued logic and stops at the first resolution error: `Success(decision)` or `Failure(error)`. due2 evaluates with Kleene logic and returns `Indeterminate` only when the unknowns could change the outcome. Outside the six exceptions below:

> **due2 refines DPROD.** If DPROD returns `Success(d)`, due2 returns `d`. If DPROD returns `Failure`, due2 returns a decision or `Indeterminate`.

DPROD succeeds only when the outcome follows from resolved values along its evaluation path, and then every completion of the unread unknowns gives the same outcome — due2's condition for a definite verdict. due2 decides more often because Kleene masking is order-independent (`and(error, false)` is `false` in due2 and `Failure` in DPROD), and because an error in a rule that does not apply does not stop due2. The `dprod-*` cases in `conformance/` check this scenario by scenario.

**Exceptions, where due2 deliberately does not refine DPROD:**

1. **Incomparable operands.** DPROD's `apply` returns `false`; due2 returns `U`. Under a prohibition or `dprod:not`, DPROD's `false` turns malformed data into a `Permit` — DPROD fails open there, and due2 returns `Indeterminate`.
2. **DPROD-only state.** DPROD keeps duty state Σ between evaluations; due2 derives it from evidence and activation (§7). They agree when Σ was produced from the same evidence, in order.
3. **`Pending`.** due2 offers routes for preconditions. DPROD's semantics attaches no duties to permissions, so its examples never yield `Pending` in due2. A DPROD-profile policy that does use `odrl:duty` on a permission gets `Pending` in due2 where DPROD ignores the duty; no corpus case exercises this.
4. **Agreement parties.** DPROD lets either party of an Agreement match a rule that names no assignee (`formal-semantics.md` §7.3). due2 reads the policy-level assignee as that rule's assignee. A grantor's request is therefore permitted, or denied by a prohibition, in DPROD where due2 returns `NotApplicable`.
5. **Policy-level target.** DPROD treats the policy target as an applicability gate *and* lets a rule's own target override it (`formal-semantics.md` §7.3, §7.4). due2 reads it only as a default. A rule whose target differs from the policy's is unreachable in DPROD and applies in due2 (`dprod-multi-asset-offer`).
6. **Violated duties.** DPROD collects a duty only when the duty's own action matches the request, and denies for a violation only after a permission is active (`formal-semantics.md` §7.2, steps 1 and 6). due2 reports obligations *in force* — their policy matches the request — and, under `violations = deny`, treats a violated one as a prohibition, which keeps the verdict monotone (`due2-workflows.md` §6.4). Under `ignore`, due2 never denies for a violation, where DPROD does. The two agree whenever no duty is violated (`dprod-hr-data-access` scenario 7).

**Gaps found in DPROD, worth reporting upstream.** Determinism, order sensitivity, and incomparable operands are reported as EKGF/dprod#285. Bare section numbers below refer to `dprod-contracts/docs/formal-semantics.md`.

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

**Tracking.** As `due2-architecture.md` §11, stated once there. Each row keeps its number when it is resolved, because issues and other documents cite rows by number.

| # | Decision | Section | Blocked on | Issue |
|---|---|---|---|---|
| 1 | General mechanism for profile operators | §4 | First operator that cannot be reduced | #17 |
| 2 | Duty windows beyond `effective_at`: whether not-yet-owed instances are generated and reported, under what horizon; and the state of an obligation in force whose window has not opened, which is reported `outstanding` | §7 | A real duty with a future window | #18 |
| 3 | Bearer default for policy-level obligations without a bearer | §6 | Survey of real obligations | #19 |
| 4 | Maintain duties and Promises | §7 | A real policy that needs one | #20 |
| 7 | DPROD upstream stabilisation: re-vendoring past commit `50db943` | §8 | Upstream PRs landing (EKGF/dprod#275, PRs #264–#282) | #35 |

Rows 5 and 6 are closed. Row 5, a not-yet-owed state for an obligation in force whose window has not opened, is merged into row 2. Row 6, witness conditions via duty-action refinements, is resolved: `due2-core` binds `odrl:payAmount` to `due2:witnessSource` (§3), and request and evidence parameters stay separate collections. The evidence is OVAL `duty1-3` and the W3C CG examples C1 and C2, translated as `oval-duty-payment`, `w3c-fs-c1`, and `w3c-fs-c2`, with `due2-conditional-duties`.
