# due2 — Architecture

**Status:** Draft v0.2
**Companions:** `ways-of-working.md` (engineering discipline) · `due2-workflows.md` (the three workflows and the reference data model, language-independent) · `odrl-compound-to-atomic-normalization.md` (normalisation stage 1, normative). This document covers what due2 *is* and why; the workflows document fixes what each step consumes, produces, and preserves.

**Changes in v0.2:** §2 tied to the three workflows; §3 schema moved to the workflows data model; §3.1 duty identity by binding, fulfilment by matching; §3.2 decided; §4 split into two stages; §6.1 `Pending(frontier)`; §6.2 all three conflict strategies admitted; §7 pins both normaliser stages; §10 stage-1 oracle; register updated; cross-references corrected. Terms unified across documents: **corpus** (was atom table), **SOTW**.

Markers as in the companion: **[D]** decided · **[O]** open, alternatives listed · **[F]** blocked on an external unknown.

---

## 1. Scope

due2 evaluates ODRL policies against requests and a state of the world, for governance-oriented access control and obligation management.

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

`normalise` emits the corpus and nothing else: flat relations of atoms, their parties and constraints, and parent→child edges. The schema is `due2-workflows.md` §3.1. Every atom carries required provenance — source policy and source rule — because every verdict must be explainable back to authored text. Full lineage is a separate collection, and the ledger pins the normaliser versions (§7).

Three consequences worth stating explicitly, because each was a live alternative:

- **`effect` is one required field, not two optionals.** "At most one of permission or prohibition" modelled as two optionals reintroduces the illegal states (both set, neither set) that normalisation exists to remove, and pushes a validity check into every consumer. Obligation-only rules are the third value, not the empty case.
- **Duties are not a separate type.** A duty is an atom whose role comes from the edge, not from its own shape. This removes the `Rule[Effect]` / `Rule[Unit]` split and, incidentally, gives the best possible wire format: flat relations, no recursion to marshal.
- **The trigger is derivable and therefore not stored.** Whether a child atom is a precondition duty, a remedy, or a consequence follows from the parent's effect. Storing it would be declaring something derivable. The cost is that an atom is not self-interpreting: its meaning depends on its referrer, and code that evaluates an atom without its incoming edge is wrong.

### 3.1 Sharing and identity **[D]**

Duties are shared in practice. "Complete annual training" attaches to many permits; "petition the council" attaches to many high-risk datasets. The two must behave differently: one training session should satisfy every permit that asks for it, while a petition about dataset X must not discharge the duty for dataset Y.

v0.1 gave every attachment its own atom. That conflicts with ODRL, where a duty shared by UID across permissions is fulfilled once, and with §8, where fulfilment is a matching event rather than a discharge keyed to an atom. Binding handles both cases correctly:

- **A duty instance is identified by its authored duty UID and its ground parameter binding** (§5). Attachments with the same binding share one instance; attachments with different bindings are distinct instances.
- **Fulfilment is matching.** A duty is fulfilled when an event matches its ground content (`due2-workflows.md` §5.3). Two instances with identical content are fulfilled by the same event — correctly, because they demand the same thing.
- **"About this dataset" is a binding, not an identity.** The petition duty binds its target to its parent's. X and Y bind differently, so their instances demand different events and cannot cross-discharge. An authored duty that names no target asks for one petition, and one petition satisfies it everywhere — which is what it says.

Normalisation stage 1 keeps authored sharing exactly (normalisation spec, invariant 4). Stage 2 instantiates per binding after parameter substitution (§4). Sharing survives in lineage, which is what lets the canonical duty be edited in one place.

Identity is **nominal**, from the author's URI. Content hashing would silently merge two duties that coincide today and diverge next quarter, and would destroy the explanation trace. The normaliser therefore requires every rule to be named, and confines content-derived identity to anonymous values — a refined action, a constraint — where content is the only identity there is (normalisation spec §3, §5.2).

**[O]** — a duty that must be performed once *per* attachment ("pay per use") is not expressible by matching. Deferred until a real duty needs it (`due2-workflows.md` §9).

### 3.2 Acyclicity **[D]**

Nesting cannot cycle; an edge relation can. `A requires B requires A` becomes representable the moment duties are shared, and will eventually be written by someone composing two policy libraries neither of whom saw the other.

Acyclicity is therefore a normaliser post-condition over the edge relation, not a visited-set in the evaluator. A cycle is a malformed policy to be rejected with a diagnostic, not a runtime condition to survive. The diagnostic lists every rule and edge on one cycle, in order (normalisation spec §6.3). The error message is the product.

---

## 4. What normalisation does **[D]**

Two stages, each with its own preservation property (`due2-workflows.md` §4). This list *is* the complexity of the system.

**Stage 1 — atomise** (`odrl-compound-to-atomic-normalization.md`):

1. **Interiorisation and cross-product expansion.** Policy-level actions, targets, and parties are copied into each root rule. Multi-valued action, relation, and party fields then expand into one atomic rule per combination. Conjunction versus disjunction is not declared per field; it follows from position. Expanding a root rule yields independent atoms, any one of which may match — disjunction. Expanding a nested duty fans out its parent's edges, so every resulting duty is owed — conjunction. Constraints and duties are never expansion axes: splitting a permission with three duties into three atoms would be a semantic error.
2. **Identity, skolemisation, lineage, acyclicity.**

**Stage 2 — build:**

3. **Constraint DNF, including `xone` elimination.** Each disjunct becomes an atom. This is the expansion with genuinely bad worst-case behaviour: `xone` over *n* constraints is exponential. **[O]** — bound it, and decide whether to expand eagerly or keep set-valued match keys where matching is membership anyway. See §9.
4. **Parameter substitution and per-binding instantiation.** See §5 and §3.1.
5. **Conditional-duty hoisting.** A duty carrying its own constraint forces the evaluator to answer "what does an inactive duty mean" — is the parent then unconditional, or void? Instead the case split is lifted into the parent's guard at normalisation. "Home lending may read; everyone else must petition first" becomes two atoms: permit with `dept == HomeLending` and no duty, permit with `dept != HomeLending` and the petition duty. Every duty in the corpus is then unconditional relative to its parent, and the evaluator's rule collapses to *parent active ⇒ duty owed*. Cost is one extra atom per conditional duty: additive, not multiplicative. **[O]** — a duty constraint referring to state that only exists after exercise cannot be hoisted, since it is not decidable at decision time. If no real duty does this, make hoistability a normaliser precondition and reject violations rather than supporting an unexercised case.
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
- **`NotApplicable`** is required regardless, because an obligation-only atom matching a request is applicable to duty and not to access. Having it removes any temptation to read "no permit matched" as Deny by accident rather than by policy.
- **`Indeterminate`** is per §5.1 of the companion document. An unresolvable operand is not false. A denial caused by a missing lookup and a denial caused by a rule must be distinguishable in the ledger afterwards. Precisely: the verdict is `Indeterminate` exactly when resolving the unknowns one way or another could change it (`due2-workflows.md` §6.4).

`Pending` is derivable rather than special: a permission applies, and its outstanding duties are known — no matching event within a complete evidence scope. Fulfilment is derived from events in the SOTW (§8), never stored.

### 6.2 Combination **[O]**

Prohibit-wins is a **default, not a law**. ODRL's `conflict` term takes `perm`, `prohibit`, or `invalid`, and it is a property of the source policy. Once atoms from several source policies are in one corpus they cannot be folded uniformly: the fold is per originating policy, then a combination across policies (`due2-workflows.md` §6.2). This is one of the reasons provenance is a required field rather than a nicety.

**[D]** — all three are admitted. `prohibit` and `perm` are pairwise precedence rules. `invalid` voids a source policy when one of its permissions and one of its prohibitions both apply; W3 can do that because every atom carries its source policy. An absent term means `invalid`, and the normaliser writes it explicitly.

**[O]** — what a void policy contributes. *Nothing* is the default: it is ODRL's reading (the policy does not govern), and it keeps the verdict monotone, so `Indeterminate` stays a two-completion computation (`due2-workflows.md` §6.4). *`Indeterminate` with a cause* is the fail-safe alternative; it adds a value outside that order and needs its own computation.

### 6.3 Two kinds of question **[D]**

Only one of the three duty triggers is answerable at request time. Preconditions gate a permit, so `decide` resolves them. Remedies and consequences fire on events that have already happened or failed to happen — that is obligation monitoring against accumulated state, not an access decision.

So the interface is two functions over the same corpus:

- `decide` returns a verdict plus duties that *would become owed*.
- A separate query returns duties *currently owed* for a party.

In workflow terms, both share W1 and W2's matching, constraint, and fulfilment machinery, and differ in the predicate applied to root atoms and in the W3 reduction. If that split is not in the signature now, it gets bolted on later as a special case.

---

## 7. Ledger **[D]**

Every decision is recorded. Because `decide` is pure over `(request, corpus, SOTW)`, the ledger is a replayable collection of cases and every production decision becomes a regression case — the conformance suite fills itself.

**Re-evaluate, never patch.** The temptation is to find `Pending` entries whose petition has been approved and flip them. A `Pending` record is not a promise; it is a decision made under facts that have since changed, and the only sound way to learn the new answer is to ask again.

**An entry pins its inputs:** request, policy version, **both normaliser versions** — the stage-1 profile IRI and version, and the stage-2 builder version (the corpus is derived, so a normaliser change can move a verdict with no policy edit) — and the SOTW facts consulted with their values (the trace's `read` relation). A timestamp alone suffices only if the SOTW is itself append-only and queryable as-of; otherwise record the values.

**The direction is not only upward.** Re-evaluation can turn Permit into Deny — a role changed, a dataset was reclassified, a policy was amended. A mechanism built as "upgrade pending to permit" has no path for that, and revocation matters more to a control function than issuance. The operation is verdict-agnostic and the ledger records transitions both ways.

**Two clocks, and two events.** "What is the verdict now" and "what did we decide on 3 March, and why" are different queries; decision time and validity time are both first-class or the audit answer gets reconstructed from today's policy and is wrong. Separately, decision and exercise are distinct events: revoking a permit does not unmake access already taken under it.

**Re-evaluation trigger [O]:**

- *Recompute all pending on any change.* Trivially correct, no bookkeeping. Pending sets in governance are small and approvals are rare, so this is almost certainly sufficient. **Start here.**
- *Dependency index.* Index pending entries by the requirements in their `read` relation, which W2 already produces as a byproduct. Justified only when the first option measurably hurts.

---

## 8. Relation to the Southampton work **[D]**

Salas, Pareti, Yumuşak, Gheisari, Ibáñez and Konstantinidis, *Evaluation and Comparison Semantics for ODRL* (arXiv:2509.05139). We should track it; we cannot adopt it wholesale.

**What it confirms.** Duties there are relations over rules — pairs and triples — rather than nested structures, which is independently the shape of §3. It also requires that a duty rule be exercisable by the obligated party, a well-formedness check worth adopting. And duty preconditions are temporal over the event log: the permission is violated if it matched and no matching duty event exists at an earlier timestamp. That settles the question §7 raises — approval is a **fact** in the event set, not a discharge operation — which is what makes re-evaluation purely derivable, and what §3.1 builds on.

**Where it diverges, and why it matters to us.**

| | Their semantics | due2 |
|---|---|---|
| Modality | Monitoring: is this state of the world violating? Access control reduces to it only if the post-action state can be predicted | Access control at request time, where that prediction is exactly what is unavailable |
| Nulls | An unspecified feature makes any condition false, following SPARQL filter semantics | `Indeterminate` is a distinct verdict (§6.1) |
| Absence of a duty event | Violation | Outstanding only within a complete evidence scope; otherwise unknown (`due2-workflows.md` §5.3) |
| Verdict | Per-policy boolean, valid or violated | Per-request, five-valued |
| Conflict | Prohibited-by-default, structurally; prohibitions carve out subsets of permissions | `conflict` strategy read from the policy (§6.2) |

**One restriction to check our policies against:** they require each boolean combination of constraints to use features of a single ODRL component. Constraints on the requester's department satisfy this. A constraint *relating* two components — requester's department equals the dataset's owning department — does not.

**The part worth taking.** Because matching is a boolean query, policy comparison becomes query containment and equivalence: deciding whether one policy is equivalent to, more restrictive than, or more permissive than another. That gives a **policy diff** — "is this amendment strictly more restrictive than the version it replaces" — which is hard to build any other way and directly useful for change control. **[O]** — worth a spike; it is a capability, not a dependency.

---

## 9. Execution **[O]**

See companion §10 for the general rule. Specific to due2:

**Today:** interpret atoms in memory, in Python. No dependency on another engine's semantics, trivial per-decision explanation, portable. Adequate for governance-scale volumes. The workflows document keeps the semantics independent of that choice.

**First optimisation, if needed:** index the corpus by action and target. Most of the available speedup is in not evaluating irrelevant atoms, and the candidate set drops from thousands to a handful. It is sound because a root atom that certainly does not apply is neutral in W3 (`due2-workflows.md` §5.5, L8). Same language, same conformance suite, available now. Exhaust this before adopting a second semantics.

**Only then**, and only against measurement: Rego/OPA, Rust via PyO3, or SQL compilation, with the trade-offs in companion §10.3. Note that for entitlement-scale work the interesting property of Rego is *partial evaluation* — a residual condition pushed into a query, so one call returns what a party may see — not raw throughput. If Rego earns its place, that is why.

**What none of these fix.** Entitlements and realtime do not fail on Python being slow. They fail on cardinality (millions of resource-party pairs stop fitting the expand-everything model — a normalisation-strategy problem), on SOTW freshness (a p99 dominated by resolving whether someone is still in home lending), and on explanation cost (building a full reason per decision is affordable in governance and may not be at volume). A faster evaluator addresses none of the three.

### 9.1 Measurement before argument **[O]**

Record before the debate: p99 with the resolver excluded, atoms evaluated per request, candidate event-set size, and whether every decision must carry an explanation. If kernel time is not a clear majority of the budget at realistic volume, a compiled hot path buys nothing.

---

## 10. Conformance suite **[D]**

One suite, backend-parameterised from day one even while exactly one backend exists. It is the cheapest thing to build now and the most expensive to retrofit.

Contents:

- Hypothesis-generated policies and requests, with a decision table.
- The laws of `due2-workflows.md` §8, as properties.
- The semantic-preservation property: `decide(normalise(p), r, w) == interpret_directly(p, r, w)`. Stage 1 now carries its own oracle: the denotation of normalisation spec §8.1, a page of definition, checked through the lineage bijection. **[O]** — a direct interpreter for stage 2 and the evaluator remains a specification artefact to maintain. Real cost, and the only check that the rest of normalisation has not quietly changed meaning.
- Explicit `Indeterminate` cases with unresolvable operands, asserted per backend. This is the property most likely to be silently lost in a port.
- Every ledger entry, replayed.
- Differential mode across backends, once there is more than one.

---

## 11. Open decisions register

Workflow-level decisions — canonical encoding, cross-policy combination, preference among alternatives, the monitoring question, per-attachment discharge, request match keys — are registered in `due2-workflows.md` §9.

| # | Decision | Section | Blocked on |
|---|---|---|---|
| 1 | Eager DNF expansion vs set-valued match keys | §4 item 3 | Blowup measurement on real policies |
| 2 | Atom-count threshold values and diagnostic | §4 | First pathological policy |
| 3 | Whether any duty constraint is genuinely non-hoistable | §4 item 5 | Survey of real duties |
| 4 | What a void (`invalid`) policy contributes: nothing (default) or `Indeterminate` with a cause | §6.2 | Real policy requiring it |
| 5 | Re-evaluation trigger: recompute-all vs dependency index | §7 | Measurement once pending volume is known |
| 6 | Direct interpreter for stage 2 and the evaluator (stage 1 has its denotational oracle) | §10 | Cost estimate |
| 7 | Policy-diff via query containment | §8 | Spike |
| 8 | Execution target beyond indexed Python | §9 | Measurement per §9.1 |
