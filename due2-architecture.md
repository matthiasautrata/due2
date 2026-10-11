# due2 — Architecture

**Status:** Draft v0.6
**Companions:** `ways-of-working.md` (engineering discipline) · `due2-workflows.md` (the three workflows and the reference data model, language-independent) · `odrl-compound-to-atomic-normalization.md` (normalisation stage 1, normative). This document covers what due2 *is* and why; the workflows document fixes what each step consumes, produces, and preserves.

**Changes in v0.6:** duty timing landed in the corpus and is computed by W2, which restores W3 purity and the completion shortcut of `due2-workflows.md` §6.4 (§3.1, §5.3 there); DPROD's example policies are vendored under `profiles/vendor/dprod/examples/` and incorporated into the conformance corpus (§10). Readability: new §0 orientation (reading order, glossary, worked example); **SOTW** and **atom** glossed at first use (§1, §3); the representation story stated once — lifted tree in W1 stage 1, relations everywhere after (`due2-workflows.md` §4); external §-references named (RL2 legend in §8.2, DPROD legend in `due2-profiles.md` §8.2).

**Coherence updates, 2026-10-10** (after `decisions/0002`): §6.2's absent conflict term takes a selected profile's declared default first (normalisation spec §3); §4 item 1 states fill-only-unstated interiorisation (normalisation spec §6.2); §10's preservation property restated as the refinement of workflows §8 L9, its direct-interpreter slot resolved by the `decisions/0002` amendment — a Python direct interpreter over the lifted form; reading order gains `implementation-alternatives.md`.

**Changes in v0.5:** witness reads made explicit, so a request-source duty condition is a guard (§4 item 5); a duty that is both an obligation and a precondition (§4 items 4–5); §8.2 records what was harvested from RL2, and §8.3 DPROD Contracts; decision record `decisions/0001-rl2-as-donor.md`. v0.4 introduced profiles and operand bindings (`due2-profiles.md`), anonymous rules (§3.1), guard-only hoisting, obligations in force reported with the access answer (§6.3), and the conformance corpus (§10).

Markers as in the companion: **[D]** decided · **[O]** open, alternatives listed · **[F]** blocked on an external unknown.

---

## 0. Orientation

**The one-sentence story.** An author writes a policy in ODRL; due2 turns it once into a flat corpus of atoms, and then answers each request by evaluating every relevant atom against the request and a frozen snapshot of the world, and folding the results into one verdict with reasons.

**Reading order.** This document (what due2 is and why) → `due2-workflows.md` (the three workflows W1–W3 and the reference data model — the normative centre) → `due2-profiles.md` (how ODRL extensions are declared as data) → `odrl-compound-to-atomic-normalization.md` (W1 stage 1, implementation-ready) → `ways-of-working.md` (engineering discipline) → `implementation-alternatives.md` (the W1 implementation-alternatives review behind `decisions/0002`). `decisions/` holds the standing decision records; `conformance/` the case corpus that an implementation must satisfy; `profiles/` the shipped profile modules.

**Glossary.** Each term is defined in the section named; this is the map, not the definition.

| Term | One line | Where |
|---|---|---|
| policy | An authored ODRL document: permissions, prohibitions, obligations | workflows §3.1 |
| request | One access question: subject, action, target, time, parameters | workflows §3.2 |
| SOTW | The state of the world, frozen for one evaluation | workflows §3.3 |
| W1 / W2 / W3 | Normalise · evaluate every atom · fold findings into a verdict | workflows §1 |
| atom | A rule narrowed to one action, one target, one party per function, conjunctive constraints | §3 |
| corpus | The flat relations of atoms W1 emits and W2/W3 read | workflows §3.1 |
| root / edge | An atom a request matches directly / a parent→duty edge | workflows §3.1 |
| duty | An obligation; as a child of a permission, a precondition that gates it | workflows §5.3 |
| duty instance | One owed occurrence of a duty — per member, or per request (grant) | workflows §5.3 |
| guard / witness condition | A duty's constraint on *when* it is owed / on *what* fulfils it | workflows §5.2 |
| evidence | A record that a party performed an action — the only fulfilment source | workflows §3.3 |
| activation | When an instance was first owed; anchors relative deadlines | workflows §3.3 |
| finding | One atom's three-valued result: applies / in force / fulfilled | workflows §5.1 |
| `T` / `F` / `U` | Kleene truth: true, false, unknown — never collapse `U` to `F` | workflows §2 |
| verdict | Permit · Deny · Pending(frontier) · NotApplicable · Indeterminate | §6.1 |
| frontier | The `Pending` answer's routes, incomparable ones all listed | workflows §6.3 |
| in force | An obligation travels with its policy: in force when that policy matches | workflows §5.2 |
| profile | An ODRL extension, declared as data and compiled mechanically | profiles §1 |

**A request through the pipeline** (from `conformance/cases/dprod-customer-api-v2`, scenario 3; the full derivation is the case's `why`):

1. *Authored.* An offer grants `read` on the customer-data asset — and carries a delivery obligation: *deliver the data every day by 07:30* (`dprod:recurrence` daily 07:00, `dprod:deadline` 30 minutes).
2. *W1.* The offer normalises into two atoms: the permission, and the delivery obligation as a root duty atom carrying its timing. Nothing else in the policy survives into the corpus as behaviour.
3. *The request.* Analytics asks to `read` customer data on 2026-06-03 at 07:10. The SOTW freezes: the delivery owed on 06-01 was performed at 07:10 that morning — admissible evidence — and the deployment answers under `violations = deny`.
4. *W2.* The permission atom *applies* (action, target, party all match). The delivery atom is *in force* (its policy matches the request) and resolves to three instances — 06-01, 06-02, 06-03: the first fulfilled by the evidence, the second **violated** (no witness, deadline 07:30 on 06-02 passed), the third outstanding (its window is still open).
5. *W3.* The candidate is ready, no prohibition applies — but under `violations = deny` a violated instance of an obligation in force acts as a surviving prohibition.
6. ***Deny***, with `verdict_basis` naming the violated 06-02 instance — and with the 06-03 instance still outstanding, so the answer explains both what went wrong and what is still owed.

---

## 1. Scope

due2 evaluates ODRL policies against requests and a state of the world — the **SOTW** of the pipeline below — for governance-oriented access control and obligation management.

**In scope:** access decisions with reasons; duties, including duties that gate a permission; a durable record of every decision that supports re-evaluation and audit.

**Out of scope for now, but shaping the design:** entitlement-scale precomputation and realtime evaluation. Neither is a requirement today. §9 records what is preserved so that neither becomes a rewrite.

**Not a goal:** implementing all of ODRL. Coverage grows against real policies. Constructs we do not support are rejected at normalisation with a diagnostic, never accepted and approximated.

---

## 2. Pipeline **[D]**

Three functions, two of them pure.

```
normalise : Policy                     -> Corpus     (offline, per policy version)   W1
decide    : Request x Corpus x SOTW    -> Verdict    (hot, per request)              W3 ∘ W2
re_decide : LedgerEntry x Corpus x SOTW -> Verdict   (on change)
```

`re_decide` is `decide` applied to a recorded request. It is named separately because it is a distinct operational trigger, not a distinct semantics.

`decide` is itself two workflows with a hard boundary between them. W2 evaluates: it gives each relevant atom a three-valued finding from the request and a frozen SOTW, and never looks at another atom's finding. W3 resolves: it folds the findings into one verdict and never looks at the request or the SOTW. `due2-workflows.md` specifies all three workflows, their data, and their laws. This document gives the reasons.

**The stages have opposite characteristics** and must not be reasoned about together:

- `normalise` runs rarely, may be slow, emits an artefact that is *checked* rather than trusted, and is where every semantically interesting rewrite happens. It is the risky half.
- `decide` runs per request, is a filter and a fold over flat records, and is the half where latency lives and correctness risk is lowest.

This asymmetry drives §10 (where verification effort goes) and §9 (why performance arguments are narrower than they look).

---

## 3. Normal form **[D]**

`normalise` emits the corpus and nothing else: flat relations of atoms, their parties and constraints, and parent→child edges. An **atom** is a rule narrowed to one action, at most one relation value, at most one party per function, and conjunctive constraints — the unit a request is matched against; ODRL's atomic Rule (IM §2.6). The schema is `due2-workflows.md` §3.1. Every atom carries required provenance — source policy and source rule — because every verdict must be explainable back to authored text. Full lineage is a separate collection, and the ledger pins the normaliser versions (§7).

Three consequences worth stating explicitly, because each was a live alternative:

- **`effect` is one required field, not two optionals.** "At most one of permission or prohibition" modelled as two optionals reintroduces the illegal states (both set, neither set) that normalisation exists to remove, and pushes a validity check into every consumer. Obligation-only rules are the third value, not the empty case.
- **Duties are not a separate type.** A duty is an atom whose role comes from the edge, not from its own shape. This removes the `Rule[Effect]` / `Rule[Unit]` split and, incidentally, gives the best possible wire format: flat relations, no recursion to marshal.
- **The trigger is derivable and therefore not stored.** Whether a child atom is a precondition duty, a remedy, or a consequence follows from the parent's effect. Storing it would be declaring something derivable. The cost is that an atom is not self-interpreting: its meaning depends on its referrer, and code that evaluates an atom without its incoming edge is wrong.

### 3.1 Sharing and identity **[D]**

Duties are shared in practice. "Complete annual training" attaches to many permits; "petition the council" attaches to many high-risk datasets. The two must behave differently: one training session should satisfy every permit that asks for it, while a petition about dataset X must not discharge the duty for dataset Y.

v0.1 gave every attachment its own atom. That conflicts with ODRL, where a duty shared by UID across permissions is fulfilled once, and with §8, where fulfilment is derived from evidence rather than discharged against a stored atom. Duty instances handle both cases, following RL2 (§8.2):

- **A duty instance is the authored duty plus its scope.** Scope `member`: the authored duty UID and its ground binding (§5). Attachments that bind the duty identically share one instance, and one fulfilment serves all of them. Scope `grant`: the authored duty UID and the request — one instance per request, for "pay per use".
- **Fulfilment is derived from evidence.** A duty is fulfilled by a record that its obligated party performed its action on its object, admitted by the duty's signer configuration (`due2-workflows.md` §5.3). A grant-scoped instance accepts only evidence submitted against it.
- **"About this dataset" is a binding, not an identity.** The petition duty binds its target to its parent's. X and Y bind differently, so their instances need evidence about different objects and cannot cross-discharge. An authored duty that names no target asks for one petition, and one petition satisfies it everywhere — which is what it says.

Normalisation stage 1 keeps authored sharing exactly (normalisation spec, invariant 4). Stage 2 instantiates per binding after parameter substitution (§4). Sharing survives in lineage, which is what lets the canonical duty be edited in one place.

Identity is **nominal**, from the author's URI. Content hashing would silently merge two duties that coincide today and diverge next quarter, and would destroy the explanation trace. Rules may still be anonymous, as ODRL allows; their identity is then derived from their content, which is the only identity an unnamed thing has (normalisation spec §3, §5.2). A rule whose identity must survive edits — above all a duty that evidence names — should be named.

### 3.2 Acyclicity **[D]**

Nesting cannot cycle; an edge relation can. `A requires B requires A` becomes representable the moment duties are shared, and will eventually be written by someone composing two policy libraries neither of whom saw the other.

Acyclicity is therefore a normaliser post-condition over the edge relation, not a visited-set in the evaluator. A cycle is a malformed policy to be rejected with a diagnostic, not a runtime condition to survive. The diagnostic lists every rule and edge on one cycle, in order (normalisation spec §6.3). The error message is the product.

---

## 4. What normalisation does **[D]**

Two stages, each with its own preservation property (`due2-workflows.md` §4). This list *is* the complexity of the system.

**Stage 1 — atomise** (`odrl-compound-to-atomic-normalization.md`):

1. **Interiorisation and cross-product expansion.** Policy-level actions, targets, and parties fill what a root rule leaves unstated, per family — a rule that states any value of a family keeps its own (normalisation spec §6.2). Multi-valued action, relation, and party fields then expand into one atomic rule per combination. Conjunction versus disjunction is not declared per field; it follows from position. Expanding a root rule yields independent atoms, any one of which may match — disjunction. Expanding a nested duty fans out its parent's edges, so every resulting duty is owed — conjunction. Constraints and duties are never expansion axes: splitting a permission with three duties into three atoms would be a semantic error.
2. **Identity, skolemisation, lineage, acyclicity.**

**Stage 2 — build:**

3. **Constraint DNF, including `xone` elimination.** Each disjunct becomes an atom. This is the expansion with genuinely bad worst-case behaviour: `xone` over *n* constraints is exponential. **[D]** (2026-10-10, `decisions/0002`) — expansion stays eager: the exact-count limit check below fails a pathological policy before materialising anything, and the corpus has yet to contain one. Set-valued match keys reopen only on the first real policy that needs them.
4. **Parameter substitution, role inheritance, and per-binding instantiation.** A duty that declares no function properties takes all of them from its parent permission (ODRL IM §2.6.5); one that declares any inherits none. The inherited roles are part of the binding, which settles a tension inside ODRL: a shared duty is "fulfilled once", yet takes its roles from each referrer — referrers with different roles yield different instances. A duty that is also a root obligation receives the policy-level values as its own, so it inherits nothing (`due2-profiles.md` §6). See §5 and §3.1.
5. **Conditional-duty hoisting.** This applies to a duty's *guards* — constraints that read no witness operand (`due2:witnessSource` or `due2:actionTime`). Constraints on the performance itself, such as "paid at least 100" or "attested after 1 January", stay on the duty as witness conditions (`due2-workflows.md` §5.2). A duty that is also a root obligation keeps its guards for that role; hoisting copies them into each parent. A duty carrying its own guard forces the evaluator to answer "what does an inactive duty mean" — is the parent then unconditional, or void? Instead the case split is lifted into the parent's guard at normalisation. "Home lending may read; everyone else must petition first" becomes two atoms: permit with `dept == HomeLending` and no duty, permit with `dept != HomeLending` and the petition duty. Every duty in the corpus is then unconditional relative to its parent, and the evaluator's rule collapses to *parent active ⇒ duty owed*. Cost is one extra atom per conditional duty: additive, not multiplicative. **[O]** — a duty constraint referring to state that only exists after exercise cannot be hoisted, since it is not decidable at decision time. If no real duty does this, make hoistability a normaliser precondition and reject violations rather than supporting an unexercised case.
6. **Projection and provenance.** Project into the corpus relations, joining stage-1 lineage so that every atom carries its source policy and rule.

**Blowup budget:** `|atoms| ≈ |actions| × |targets| × |parties| × |DNF disjuncts| + |conditional duties| + |duty attachments|`. Only the first term is multiplicative. Stage 1 computes exact counts and fails a limit before materialising anything. **[O]** — the threshold values, and their diagnostic.

---

## 5. Parameters and operands **[D]**

Free variables in a shared duty template look alike and are two different things. Separating them is load-bearing.

**The derivability test comes first.** For each free variable, ask whether it is determined by action, target, party and the state of the world. "The dataset's risk tier", "the requester's department", "the applicable review board" look like parameters and are functions of things already in hand. Those are not parameters. They are operands the constraint vocabulary should name and the resolver should answer. A thin operand vocabulary reappears as a long parameter list; the fix is the vocabulary, not a binding mechanism.

What survives splits by resolution time, and the two must not share a mechanism:

| | Parameter | Context operand |
|---|---|---|
| Bound | On the edge, at normalisation | From request and SOTW, at decision |
| Ground by | End of normalisation | Never — resolved each time |
| If missing | Malformed policy, rejected statically | `Indeterminate` verdict, at runtime |

Conflating them loses the ability to prove statically that a policy is fully specified, because a well-formedness failure would become a runtime outcome.

Since parameters are ground at normalisation, they are substituted there, and the substitution fixes each duty instance's binding (§3.1). The evaluator therefore carries no environment: no substitution, no scoping rules, no capture.

**The binding language is deliberately not a language.** A binding maps a parameter to a ground term, or to a parameter in the parent's scope. Not to an expression. Once bindings can compute, normalisation stops being a syntactic rewrite and acquires its own evaluation order — and the semantic-preservation property (§10) becomes much harder to state.

---

## 6. Deciding

### 6.1 Verdicts **[D]**

```
Permit | Deny | Pending(frontier) | NotApplicable | Indeterminate
```

- **`Pending`** is the escape hatch made visible. When a permission is gated on a duty that has not been fulfilled, the answer is neither Permit nor Deny; it is deny-with-a-discharge-path. Flattening it into Deny is a real product failure: the requester never learns the route exists. In governance this case is common, not exotic. Several permissions may each offer a route; `Pending` carries the **frontier** — every route whose outstanding duties are not a strict superset of another route's (`due2-workflows.md` §6.3). Routes are not ranked unless a preference is declared.
- **`NotApplicable`** is required regardless, because an obligation-only atom matching a request is applicable to duty and not to access. Having it removes any temptation to read "no permit matched" as Deny by accident rather than by policy. A `NotApplicable` where a violated precondition closed a matched route is distinguishable from one where nothing matched: the trace records the closure (`due2-workflows.md` §6.1).
- **`Indeterminate`** is the absent/unknown/false discipline of `ways-of-working.md` §5.1 made a verdict. An unresolvable operand is not false. A denial caused by a missing lookup and a denial caused by a rule must be distinguishable in the ledger afterwards. Precisely: the verdict is `Indeterminate` exactly when resolving the unknowns one way or another could change it (`due2-workflows.md` §6.4).

`Pending` is derivable rather than special: a permission applies, and some of its duties have no admissible evidence of performance yet. Absence of evidence means *not yet fulfilled*, not unknown; evidence arrives through the case (§7), and fulfilment is derived from it, never stored.

### 6.2 Combination **[O]**

Prohibit-wins is a **default, not a law**. ODRL's `conflict` term takes `perm`, `prohibit`, or `invalid`, and it is a property of the source policy. Once atoms from several source policies are in one corpus they cannot be folded uniformly: the fold is per originating policy, then a combination across policies (`due2-workflows.md` §6.2). This is one of the reasons provenance is a required field rather than a nicety.

**[D]** — all three are admitted. `prohibit` and `perm` are pairwise precedence rules. `invalid` voids a source policy when one of its permissions and one of its prohibitions both apply; W3 can do that because every atom carries its source policy. An absent term takes a selected profile's declared default first, then `invalid` (normalisation spec §3); the normaliser writes the result explicitly.

**[O]** — what a void policy contributes. *Nothing* is the default: it is ODRL's reading (the policy does not govern), and it keeps the verdict monotone, so `Indeterminate` stays a two-completion computation (`due2-workflows.md` §6.4). *`Indeterminate` with a cause* is the fail-safe alternative; it adds a value outside that order and needs its own computation.

### 6.3 Two kinds of question **[D]**

Only one of the three duty triggers is answerable at request time. Preconditions gate a permit, so `decide` resolves them. Remedies and consequences fire on events that have already happened or failed to happen — that is obligation monitoring against accumulated state, not an access decision.

So the interface is two functions over the same corpus:

- `decide` returns a verdict plus duties that *would become owed*.
- A separate query returns duties *currently owed* for a party.

In workflow terms, both share W1 and W2's matching, constraint, and fulfilment machinery, and differ in the predicate applied to root atoms and in the W3 reduction. The access answer already reports the obligations *in force* for the request — those of the policy it is made under — with their status (`due2-workflows.md` §5.2, §6.1). What remains open is the request-free query: everything a party owes now. If that split is not in the signature now, it gets bolted on later as a special case.

---

## 7. Ledger **[D]**

Every decision is recorded. Because `decide` is pure over `(request, corpus, SOTW)`, the ledger is a replayable collection of cases and every production decision becomes a regression case — the conformance suite fills itself.

**Re-evaluate, never patch.** The temptation is to find `Pending` entries whose petition has been approved and flip them. A `Pending` record is not a promise; it is a decision made under facts that have since changed, and the only sound way to learn the new answer is to ask again.

**An entry pins its inputs:** request, policy version, **both normaliser versions** — the stage-1 profile IRI and version, and the stage-2 builder version (the corpus is derived, so a normaliser change can move a verdict with no policy edit) — and the SOTW facts consulted with their values (the trace's `read` relation). A timestamp alone suffices only if the SOTW is itself append-only and queryable as-of; otherwise record the values.

**The direction is not only upward.** Re-evaluation can turn Permit into Deny — a role changed, a dataset was reclassified, a policy was amended. A mechanism built as "upgrade pending to permit" has no path for that, and revocation matters more to a control function than issuance. The operation is verdict-agnostic and the ledger records transitions both ways.

**Two clocks, and two events.** "What is the verdict now" and "what did we decide on 3 March, and why" are different queries; decision time and validity time are both first-class or the audit answer gets reconstructed from today's policy and is wrong. Separately, decision and exercise are distinct events: revoking a permit does not unmake access already taken under it. In the data model, decision time is `sotw.effective_at` and validity time is `request.at` (`due2-workflows.md` §3).

**The case flow.** A request whose verdict is `Pending` records the duty instances it awaits — the trace's `instance` and `alt_duty` relations. Evidence submitted later names the instance it answers. The next evaluation, over a new SOTW, finds it and may return `Permit`; nothing in the earlier trace changes.

**Re-evaluation trigger [O]:**

- *Recompute all pending on any change.* Trivially correct, no bookkeeping. Pending sets in governance are small and approvals are rare, so this is almost certainly sufficient. **Start here.**
- *Dependency index.* Index pending entries by the state properties in their `read` relation, which W2 already produces as a byproduct. Justified only when the first option measurably hurts.

---

## 8. Relation to prior work **[D]**

### 8.1 The Southampton work

Salas, Pareti, Yumuşak, Gheisari, Ibáñez and Konstantinidis, *Evaluation and Comparison Semantics for ODRL* (arXiv:2509.05139). We should track it; we cannot adopt it wholesale.

**What it confirms.** Duties there are relations over rules — pairs and triples — rather than nested structures, which is independently the shape of §3. It also requires that a duty rule be exercisable by the obligated party, a well-formedness check worth adopting. And duty preconditions are temporal over the event log: the permission is violated if it matched and no matching duty event exists at an earlier timestamp. That settles the question §7 raises — approval is a **fact** in the event set, not a discharge operation — which is what makes re-evaluation purely derivable, and what §3.1 builds on.

**Where it diverges, and why it matters to us.**

| | Their semantics | due2 |
|---|---|---|
| Modality | Monitoring: is this state of the world violating? Access control reduces to it only if the post-action state can be predicted | Access control at request time, where that prediction is exactly what is unavailable |
| Nulls | An unspecified feature makes any condition false, following SPARQL filter semantics | `Indeterminate` is a distinct verdict (§6.1) |
| Absence of a duty event | Violation | Not yet fulfilled: the duty is outstanding and the verdict `Pending` (`due2-workflows.md` §5.3) |
| Verdict | Per-policy boolean, valid or violated | Per-request, five-valued |
| Conflict | Prohibited-by-default, structurally; prohibitions carve out subsets of permissions | `conflict` strategy read from the policy (§6.2) |

**One restriction to check our policies against:** they require each boolean combination of constraints to use features of a single ODRL component. Constraints on the requester's department satisfy this. A constraint *relating* two components — requester's department equals the dataset's owning department — does not.

**The part worth taking.** Because matching is a boolean query, policy comparison becomes query containment and equivalence: deciding whether one policy is equivalent to, more restrictive than, or more permissive than another. That gives a **policy diff** — "is this amendment strictly more restrictive than the version it replaces" — which is hard to build any other way and directly useful for change control. **[O]** — worth a spike; it is a capability, not a dependency.

### 8.2 RL2

RL2 (`~/src/RL2`, `github.com/matthiasautrata/RL2`) is due2's predecessor: an attempt to extend ODRL into a language of its own, with formal semantics. It is not a superset of ODRL — it has its own vocabulary and a partial translator — and it has never been executed. due2 harvests it rather than adopting it (`decisions/0001-rl2-as-donor.md`).

Harvested — section numbers cite RL2's specs (`Model` = `spec/RL2_Model.md`, `Semantics` = `spec/RL2_Semantics.md`, `Compilation` = `spec/RL2_Compilation.md`):

- **Evidence and fulfilment** — Model §4.3–§4.5, §7.3: evidence as records of performed actions; absence means not yet fulfilled; trust verified before evaluation, with a closed signer admissibility record.
- **Duty instances** — Semantics §Duty Template Binding: per-member and per-grant occurrence identity, with evidence naming the grant it discharges.
- **Typed operands** — Model §4.2–§4.4: value types, the missing / invalid / conflict discipline, admissibility and freshness, merged with DPROD's one-hop bindings (`due2-profiles.md` §3).
- **Guards and witness conditions** — RL2's `condition` and `postCondition` (`due2-workflows.md` §5.2).
- **The use cases** — all 49, rewritten in ODRL as `conformance/cases/rl2-*` (§10).

Left behind: the vocabulary, Maintain duties, Promises, Offer → Agreement materialisation, and duty status as an operand. The corpus records each case that needs one of them.

Sources for open items:

- stage 2 — RL2_Compilation: canonical projection, closed-world rule, diagnostic registry, determinism;
- conflict resolution and exception patterns — Semantics §Conflict Resolution;
- profile operators — Compilation §9.1 (`due2-profiles.md` §4);
- replayable policy selection and the re-evaluation loop — ExternalData §6–§7.

### 8.3 DPROD Contracts

DPROD Contracts (EKGF, `github.com/EKGF/dprod`, branch `develop`, `dprod-contracts/`) is an ODRL 2.2 profile for data contracts with deterministic evaluation — much of RL2's intent, expressed the way ODRL intends. due2 handles it as a profile, with no translation: its operand bindings are due2's (`due2-profiles.md` §3), and its other terms land on due2's extension points (§8.1 there). Where DPROD returns a decision, due2 returns the same one, outside six documented exceptions; where DPROD fails, due2 still decides when the unknowns cannot change the outcome (§8.2 there). Testing DPROD's examples also found gaps in DPROD itself, listed there for upstream.

---

## 9. Execution **[O]**

See companion §10 for the general rule. Specific to due2:

**Today:** interpret atoms in memory, in Python. No dependency on another engine's semantics, trivial per-decision explanation, portable. Adequate for governance-scale volumes. The workflows document keeps the semantics independent of that choice.

**First optimisation, if needed:** index the corpus by action and target. Most of the available speedup is in not evaluating irrelevant atoms, and the candidate set drops from thousands to a handful. It is sound because a root atom that certainly does not apply is neutral in W3 (`due2-workflows.md` §5.5, L8). Same language, same conformance suite, available now. Exhaust this before adopting a second semantics.

**Only then**, and only against measurement: Rego/OPA, Rust via PyO3, or SQL compilation, with the trade-offs in `ways-of-working.md` §10.3. Note that for entitlement-scale work the interesting property of Rego is *partial evaluation* — a residual condition pushed into a query, so one call returns what a party may see — not raw throughput. If Rego earns its place, that is why.

**What none of these fix.** Entitlements and realtime do not fail on Python being slow. They fail on cardinality (millions of resource-party pairs stop fitting the expand-everything model — a normalisation-strategy problem), on SOTW freshness (a p99 dominated by resolving whether someone is still in home lending), and on explanation cost (building a full reason per decision is affordable in governance and may not be at volume). A faster evaluator addresses none of the three.

### 9.1 Measurement before argument **[O]**

Record before the debate: p99 with the resolver excluded, atoms evaluated per request, evidence-set size, and whether every decision must carry an explanation. If kernel time is not a clear majority of the budget at realistic volume, a compiled hot path buys nothing.

---

## 10. Conformance suite **[D]**

One suite, backend-parameterised from day one even while exactly one backend exists. It is the cheapest thing to build now and the most expensive to retrofit.

Contents:

- Hypothesis-generated policies and requests, with a decision table.
- The laws of `due2-workflows.md` §8, as properties.
- The case corpus in `conformance/`: the RL2 use cases rewritten in ODRL, and DPROD Contracts examples — now vendored unmodified under `profiles/vendor/dprod/examples/` and covered as cases — each with scenarios and hand-derived expected verdicts, checked mechanically by `tools/check_corpus.py` until an evaluator runs them.
- The semantic-preservation property: `decide(normalise(p), r, w)` equals `interpret_directly(p, r, w)` whenever the completion is exact (workflows §6.4, §8 L9, v0.6, 2026-10-11): completions range over literals, so the guards hoisting splits and their negations share one variable. Beyond the `max_mixed` bound it weakens to refinement — a definite pipeline verdict equals the direct one, and the pipeline may return `Indeterminate` where the direct one decides (the 2026-10-10 reading). Stage 1 now carries its own oracle: the denotation of normalisation spec §8.1, a page of definition, checked through the lineage bijection. **Resolved 2026-10-10** (`decisions/0002` and its amendment): a Python direct interpreter over the lifted (authored) form is the maintained L9 oracle; the Dafny extraction covers the `Den` oracle and stage-1 expansion first, extending to stage 2's rewriting second. Real cost, and still the only check that the rest of normalisation has not quietly changed meaning.
- Explicit `Indeterminate` cases with unresolvable operands, asserted per backend. This is the property most likely to be silently lost in a port.
- Every ledger entry, replayed.
- Differential mode across backends, once there is more than one.

---

## 11. Open decisions register

Workflow-level decisions — canonical encoding, cross-policy combination, preference among alternatives, the monitoring question, request match keys — are registered in `due2-workflows.md` §9. Duty timing is decided (`due2-workflows.md` §5.3, `due2-profiles.md` §7).

**Tracking.** Open items are recorded as GitHub issues (labels: `open-decision`, `corpus`, `verification`, `work-item`, `parked`); the execution-target cluster (#8) covers ways-of-working §13 #10/#11/#13. This register remains the specification record: a resolution lands here, and the issue closes.

| # | Decision | Section | Blocked on |
|---|---|---|---|
| 1 | Eager DNF expansion vs set-valued match keys | §4 item 3 | Resolved by default (`decisions/0002`): eager, limit-enforced; set-valued keys reopen on the first pathological policy |
| 2 | Atom-count threshold values and diagnostic | §4 | First pathological policy |
| 3 | Whether any duty constraint is genuinely non-hoistable | §4 item 5 | Survey of real duties |
| 4 | What a void (`invalid`) policy contributes: nothing (default) or `Indeterminate` with a cause | §6.2 | Real policy requiring it |
| 5 | Re-evaluation trigger: recompute-all vs dependency index | §7 | Measurement once pending volume is known |
| 6 | Direct interpreter for stage 2 and the evaluator (stage 1 has its denotational oracle) | §10 | Resolved by `decisions/0002`: Dafny-extracted `Den` oracle (stage 1) plus a Python reference evaluator (stage 2, W2, W3) until a verified backend passes the corpus |
| 7 | Policy-diff via query containment | §8.1 | Spike |
| 8 | Execution target beyond indexed Python | §9 | Measurement per §9.1 |
