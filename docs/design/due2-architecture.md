# due2 — Architecture

**Status:** Draft v0.19
**Companions:** `ways-of-working.md` (engineering discipline) · `due2-workflows.md` (the three workflows and the reference data model, language-independent) · `odrl-compound-to-atomic-normalization.md` (normalisation stage 1, normative). This document covers what due2 *is* and why; the workflows document fixes what each step consumes, produces, and preserves.

**Changes in v0.19** (2026-10-26, `decisions/0047`): §2: the edges above a state property's values are planned by property and fetched once its facts are recorded. Earlier changes are in `docs/archive/changes.md`.

Markers as in the companion: **[D]** decided · **[O]** open, alternatives listed · **[F]** blocked on an external unknown.

---

## 0. Orientation

**The one-sentence story.** An author writes a policy in ODRL; due2 turns it once into a flat corpus of atoms, and then answers each request by evaluating every relevant atom against the request and a frozen snapshot of the world, and folding the results into one verdict with reasons.

**Reading order.** `due2-overview.md` (the big picture, and clingo-i as an oracle) → this document (what due2 is and why) → `due2-workflows.md` (the three workflows W1–W3 and the reference data model — the normative centre) → `due2-profiles.md` (how ODRL extensions are declared as data) → `odrl-compound-to-atomic-normalization.md` (W1 stage 1, implementation-ready) → `due2-diagnostics.md` (every code W1 can reject or warn with) → `due2-platform.md` (the components around the evaluator, and its port) → `ways-of-working.md` (engineering discipline) → `correctness-strategy.md` (which check guards which risk, and what must exist before each component is coded) → `references.md` (the annotated bibliography: what was read, why, and what it taught). The documents live under `docs/`: `spec/` (workflows, profiles, normalisation, diagnostics), `design/` (this document, the platform, and the references), `correctness/` (ways of working, correctness strategy), `decisions/` (the decision records, indexed with their standing in `docs/decisions/README.md`), and `archive/` (documents no longer current, kept as history). At the root, `conformance/` holds the case corpus that an implementation must satisfy, `schema/` the evaluator's port in JSON Schema, `profiles/` the shipped profile modules, `spikes/` the candidate implementations (among them clingo-i, the semantics program that serves as oracle), `formal/` the Alloy models of the correctness claims, and `tools/` the checkers.

**Glossary.** Each term is defined in the section named; this is the map, not the definition.

| Term | One line | Where |
|---|---|---|
| policy | An authored ODRL document: permissions, prohibitions, obligations | `due2-workflows.md` §3.1 |
| request | One access question: subject, action, target, time, parameters | `due2-workflows.md` §3.2 |
| SOTW | The state of the world, frozen for one evaluation | `due2-workflows.md` §3.3 |
| W1 / W2 / W3 | Normalise · evaluate every atom · fold findings into a verdict | `due2-workflows.md` §1 |
| atom | A rule narrowed to one action, one target, one party per function, conjunctive constraints (a duty's, in clauses) | §3 |
| corpus | The flat relations of atoms W1 emits and W2/W3 read | `due2-workflows.md` §3.1 |
| root / edge | An atom a request matches directly / a parent→duty edge | `due2-workflows.md` §3.1 |
| duty | An obligation; as a child of a permission, a precondition that gates it | `due2-workflows.md` §5.3 |
| duty instance | One owed occurrence of a duty — per member, or per request (grant) | `due2-workflows.md` §5.3 |
| guard / witness condition | A duty's constraint on *when* it is owed / on *what* fulfils it | `due2-workflows.md` §5.2 |
| evidence | A record that a party performed an action — the only fulfilment source | `due2-workflows.md` §3.3 |
| activation | When an instance was first owed; anchors relative deadlines | `due2-workflows.md` §3.3 |
| finding | One atom's three-valued result: applies / in force / fulfilled | `due2-workflows.md` §5.1 |
| `T` / `F` / `U` | Kleene truth: true, false, unknown — never collapse `U` to `F` | `due2-workflows.md` §2 |
| verdict | Permit · Deny · Pending(frontier) · NotApplicable · Indeterminate | §6.1 |
| frontier | The `Pending` answer's routes, incomparable ones all listed | `due2-workflows.md` §6.3 |
| trace / explanation | What W2 and W3 emit for an evaluation; the explanation is the part reachable from the verdict (`verdict_basis`, `eliminated`) | `due2-workflows.md` §3.5, §3.7 |
| opaque part | A `U` part whose value is missing, invalid, in conflict, or does not fit its operator: a completion variable of its own, never shared or paired with a complement | `due2-workflows.md` §6.4, `decisions/0016` |
| pivotal literal | A literal whose flip alone changes some completion's verdict; an `Indeterminate` names the `U` atoms that hold one, and its `verdict_range` | `due2-workflows.md` §6.4, `decisions/0011` |
| in force | An obligation travels with its policies: in force when one of the policies that state it matches | `due2-workflows.md` §5.2 |
| profile | An ODRL extension, declared as data and compiled mechanically | `due2-profiles.md` §1 |

**A request through the pipeline** (from `conformance/cases/dprod-customer-api-v2`, scenario 2; the expected answer is the case's hand-derived one, and its `why` gives the derivation):

1. *Authored.* An offer on the customer-data asset, taken from DPROD Contracts' examples, has six rules: permissions to `read` and to `derive`, a prohibition on `distribute`, and three obligations. One obligation is *deliver the data every day by 07:30*: `dprod:recurrence` daily at 07:00, with a `dprod:deadline` of 30 minutes. The other two are schema conformance and usage reporting within 30 days.
2. *W1.* Each rule already has one action and at most one target, so the offer normalises into six atoms, once the offer's target and assigner fill the rules that state none (`odrl-compound-to-atomic-normalization.md` §6.2). The three obligations are root duty atoms, and the delivery and reporting atoms carry their timing.
3. *The request.* Analytics asks to `read` customer data on 2026-06-03 at 07:10. The SOTW holds one evidence record, the delivery performed at 07:10 on 06-01, and the delivery's activation at 07:00 on 06-01.
4. *W2.* The read permission *applies*: its action and target match, and it names no assignee. The derive permission and the prohibition do not apply, since their actions differ from `read`. All three obligations are *in force*, because their policy matches the request. The delivery resolves to three instances. The 06-01 instance is fulfilled by the evidence. The 06-02 instance is **violated**: no evidence answers it, and its deadline, 07:30 on 06-02, has passed. The 06-03 instance is outstanding, since its deadline is still ahead. The schema and reporting obligations are outstanding.
5. *W3.* The read permission has no precondition duties, so nothing gates it, and no prohibition applies, so the read permission is a ready candidate. The obligations are independent of the permission: a violated obligation is reported and does not move the verdict (`due2-workflows.md` §6.1, `decisions/0045`).
6. ***Permit***. The obligations the answer reports list the fulfilled 06-01 instance, the violated 06-02 instance, and the outstanding 06-03 one, so the answer says what went wrong and what is still owed beside the permission. DPROD also permits this request, but for another reason: it never collects a duty whose action differs from the request's (`due2-profiles.md` §8.2, exception 6).

---

## 1. Scope

due2 evaluates ODRL policies against requests and a state of the world — the **SOTW** of the pipeline below — for governance-oriented access control and obligation management.

**In scope:** access decisions with reasons; duties, including duties that gate a permission; a durable record of every decision that supports re-evaluation and audit.

**Out of scope, but shaping the design:** entitlement-scale precomputation and realtime evaluation. Neither is a requirement. §9 records what is preserved so that neither becomes a rewrite.

**Not a goal:** implementing all of ODRL. Coverage grows against real policies. Constructs we do not support are rejected at normalisation with a diagnostic, never accepted and approximated.

---

## 2. Pipeline **[D]**

Three pure functions. The shell around them fetches facts, records them in the case, and stores traces.

```text
normalise : Policy                          -> Corpus   (offline, per policy version)   W1
plan      : Corpus x Request                -> Reads    (per request, before decide)
decide    : Corpus x Request x SOTW         -> Trace    (hot, per evaluation)           W3 ∘ W2
```

`plan` is the sweep the operand bindings exist for (`due2-profiles.md` §3): every value an evaluation can consult is named by a binding, so the reads are planned from the corpus and the request before anything is fetched. Only the edges above a state property's values wait for its facts (`due2-workflows.md` §3.3). The shell fetches what the case lacks, records it, and calls `decide` only when every planned read is in the case (`due2-workflows.md` §3.3). `decide` returns the trace, and the verdict is one relation in it. Re-evaluation is `decide` over the case's current SOTW: a distinct operational trigger (§7), not a distinct function.

`decide` is itself two workflows with a hard boundary between them. W2 evaluates: it gives each relevant atom a three-valued finding from the request and a frozen SOTW, and never looks at another atom's finding. W3 resolves: it folds the findings into one verdict and never looks at the request or the SOTW. `due2-workflows.md` specifies all three workflows, their data, and their laws. This document gives the reasons.

**The stages have opposite characteristics** and must not be reasoned about together:

- `normalise` runs rarely, may be slow, emits an artefact that is *checked* rather than trusted, and is where every semantically interesting rewrite happens. It is the risky half.
- `decide` runs per request, is a filter and a fold over flat records, and is the half where latency lives and correctness risk is lowest.

This asymmetry drives §10 (where verification effort goes) and §9 (why performance arguments are narrower than they look).

---

## 3. Normal form **[D]**

`normalise` emits the corpus and nothing else: flat relations of atoms, their parties and constraints, and parent→child edges. An **atom** is a rule narrowed to one action, at most one relation value, at most one party per function, and conjunctive constraints, which on a duty are grouped into clauses (item 3 of §4) — the unit a request is matched against; ODRL's atomic Rule (ODRL 2.2 Information Model, IM, §2.6). The schema is `due2-workflows.md` §3.1. Every atom carries required provenance — source policy and source rule — because every verdict must be explainable back to authored text. Full lineage is a separate collection, and the ledger pins the normaliser versions (§7).

Three consequences worth stating explicitly, because each was a live alternative:

- **`effect` is one required field, not two optionals.** "At most one of permission or prohibition" modelled as two optionals reintroduces the illegal states (both set, neither set) that normalisation exists to remove, and pushes a validity check into every consumer. Obligation-only rules are the third value, not the empty case.
- **Duties are not a separate type.** A duty is an atom whose role comes from the edge, not from its own shape. This removes the `Rule[Effect]` / `Rule[Unit]` split and, incidentally, gives the best possible wire format: flat relations, no recursion to marshal.
- **The trigger is derivable and therefore not stored.** Whether a child atom is a precondition duty, a remedy, or a consequence follows from the parent's effect. Storing it would be declaring something derivable. The cost is that an atom is not self-interpreting: its meaning depends on its referrer, and code that evaluates an atom without its incoming edge is wrong.

### 3.1 Sharing and identity **[D]**

Duties are shared in practice. "Complete annual training" attaches to many permits; "petition the council" attaches to many high-risk datasets. The two must behave differently: one training session should satisfy every permit that asks for it, while a petition about dataset X must not discharge the duty for dataset Y.

Giving every attachment its own atom would conflict with ODRL, where a duty shared by UID across permissions is fulfilled once, and with §8, where fulfilment is derived from evidence rather than discharged against a stored atom. Duty instances handle both cases, following RL2 (§8.2):

- **A duty instance is the authored duty plus its scope.** Scope `member`: the duty atom, whose id holds the authored duty UID and its ground binding (§5), plus the performer when the request supplies it (`due2-workflows.md` §5.3). Attachments that bind the duty identically share one instance, and one fulfilment serves all of them. Scope `grant`: the duty atom and the request's reference — one instance per request, for "pay per use".
- **Fulfilment is derived from evidence.** A duty is fulfilled by a record that its obligated party performed its action on its object, made by the duty's attester or by an issuer below it in the party closure, when the duty names one with `due2:attestingParty` (`due2-workflows.md` §5.3). A grant-scoped instance accepts only evidence submitted against it.
- **"About this dataset" is a binding, not an identity.** The petition duty binds its target to its parent's. X and Y bind differently, so their instances need evidence about different objects and cannot cross-discharge. An authored duty that names no target asks for one petition, and one petition satisfies it everywhere — which is what it says.

Normalisation stage 1 keeps authored sharing exactly (`odrl-compound-to-atomic-normalization.md`, invariant 4). Stage 2 instantiates per binding after parameter substitution (§4). Sharing survives in lineage, which is what lets the canonical duty be edited in one place.

Identity is **nominal**, from the author's URI. Content hashing would silently merge two duties that coincide today and diverge next quarter, and would destroy the explanation trace. Rules may still be anonymous, as ODRL allows; W1 then mints their identity, once, when their policy is first published, so nothing outside due2 can name them beforehand (`odrl-compound-to-atomic-normalization.md` §3, §5.2; `decisions/0038`). A rule that something outside its policy names, above all a duty that evidence names, should be named.

### 3.2 Acyclicity **[D]**

Nesting cannot cycle; an edge relation can. `A requires B requires A` becomes representable the moment duties are shared, and will eventually be written by someone composing two policy libraries neither of whom saw the other.

Acyclicity is therefore a normaliser post-condition over the edge relation, not a visited-set in the evaluator. A cycle is a malformed policy to be rejected with a diagnostic, not a runtime condition to survive. The diagnostic lists every rule and edge on one cycle, in order (`odrl-compound-to-atomic-normalization.md` §6.3). The error message is the product.

---

## 4. What normalisation does **[D]**

Two stages, each with its own preservation property (`due2-workflows.md` §4). This list *is* the complexity of the system.

**Stage 1 — atomise** (`odrl-compound-to-atomic-normalization.md`):

1. **Interiorisation and cross-product expansion.** Policy-level actions, targets, and parties fill what a root rule leaves unstated, per family — a rule that states any value of a family keeps its own (`odrl-compound-to-atomic-normalization.md` §6.2). Multi-valued action, relation, and party fields then expand into one atomic rule per combination. Conjunction versus disjunction is not declared per field; it follows from position. Expanding a root rule yields independent atoms, any one of which may match — disjunction. Expanding a nested duty fans out its parent's edges, so every resulting duty is owed — conjunction. Constraints and duties are never expansion axes: splitting a permission with three duties into three atoms would be a semantic error.
2. **Identity, skolemisation, lineage, acyclicity.**

**Stage 2 — build:**

3. **Constraint DNF, including `xone` elimination.** Each disjunct of a root rule's constraint becomes an atom, an alternative. A duty's constraint is not split, since its atoms are all owed: its disjuncts become clauses of its one atom (`decisions/0028`). This is the expansion with genuinely bad worst-case behaviour: `xone` over *n* constraints is exponential. **[D]** (`decisions/0002`) Expansion stays eager: the exact-count limit check below fails a pathological policy before materialising anything, and no corpus case comes near the limit. Set-valued match keys reopen only on the first real policy that needs them.
4. **Parameter substitution, role inheritance, and per-binding instantiation.** A duty that declares no function properties takes all of them from its parent permission (ODRL IM §2.6.5); one that declares any inherits none. The inherited roles are part of the binding, which settles a tension inside ODRL: a shared duty is "fulfilled once", yet takes its roles from each referrer — referrers with different roles yield different instances. A duty that is also a root obligation receives the policy-level values as its own, so it inherits nothing (`due2-profiles.md` §6). See §5 and §3.1.
5. **Conditional duties stay conditional [D]** (`decisions/0003`). A duty's constraints split, by their bindings, into *guards* — when the duty is owed — and *witness conditions* — what fulfils it, such as "paid at least 100" or "attested after 1 January" (`due2-workflows.md` §5.2). Both stay on the duty atom, as clauses when either is a disjunction (item 3). W2 evaluates a precondition's guards as `owed`, and a root obligation's as part of `in_force`, so a duty with both roles needs no special case. An inactive duty is simply not owed — DPROD's D-ACTIVATE reading and the W3C CG's (C21). The rejected alternative, hoisting guards into the parent permission, multiplies its atoms by 2^*c* for *c* guarded duties (`decisions/0003`). The question of guards over post-exercise state dissolves with it: such a condition is a witness condition, not a guard.
6. **Projection and provenance.** Project into the corpus relations, joining stage-1 lineage so that every atom carries its source policy and rule.

**Blowup budget:** `|atoms| ≈ |actions| × |targets| × |parties| × |DNF disjuncts| + |duty attachments|`. Only the first term is multiplicative, and within it only DNF (`xone` above all) is exponential. Duties add atoms linearly, since their guards stay on the duty (item 5) and their DNF disjuncts are clauses, not atoms (item 3). A duty's clauses grow as its DNF does, so the exact count includes them. Stage 1 computes exact counts and fails a limit before materialising anything. **[O]** — the threshold values, and their diagnostic.

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

```text
Permit | Deny | Pending(frontier) | NotApplicable | Indeterminate
```

- **`Pending`** is the escape hatch made visible. When a permission is gated on a duty that has not been fulfilled, the answer is neither Permit nor Deny; it is deny-with-a-discharge-path. Flattening it into Deny is a real product failure: the requester never learns the route exists. In governance this case is common, not exotic. Several permissions may each offer a route; `Pending` carries the **frontier** — every route whose outstanding duties are not a strict superset of another route's (`due2-workflows.md` §6.3). Routes are not ranked unless a preference is declared.
- **`NotApplicable`** is required regardless, because an obligation-only atom matching a request is applicable to duty and not to access. Having it removes any temptation to read "no permit matched" as Deny by accident rather than by policy. A `NotApplicable` where a violated precondition closed a matched route is distinguishable from one where nothing matched: the trace records the closure (`due2-workflows.md` §6.1).
- **`Indeterminate`** is the absent/unknown/false discipline of `ways-of-working.md` §5.1 made a verdict. An unresolvable operand is not false. A denial caused by a missing lookup and a denial caused by a rule must be distinguishable in the ledger afterwards. Precisely: the verdict is `Indeterminate` exactly when resolving the unknowns one way or another could change it (`due2-workflows.md` §6.4).

`Pending` is derivable rather than special: a permission applies, and some of its duties have no admissible evidence of performance yet. Absence of evidence means *not yet fulfilled*, not unknown; evidence arrives through the case (§7), and fulfilment is derived from it, never stored.

### 6.2 Combination **[D]**

Prohibit-wins is a **default, not a law**. ODRL's `conflict` term takes `perm`, `prohibit`, or `invalid`, and it is a property of the source policy. Once atoms from several source policies are in one corpus they cannot be folded uniformly: the fold is per originating policy, then prohibit-overrides across policies, fixed for every evaluation (`due2-workflows.md` §6.2, `decisions/0045`). Other cross-policy strategies are open (`due2-workflows.md` §9 #2). This is one of the reasons provenance is a required field rather than a nicety.

**[D]** — all three are admitted. `prohibit` and `perm` are pairwise precedence rules. `invalid` voids a source policy when one of its permissions and one of its prohibitions both apply; W3 can do that because every atom carries its source policy. An absent term takes a selected profile's declared default first, then `invalid` (`odrl-compound-to-atomic-normalization.md` §3); the normaliser writes the result explicitly.

**[D]** A void policy gives *no access answer*: its permissions and prohibitions are eliminated. Its root obligations stay in force and are still reported, a violated one included (`decisions/0029`). ODRL reads a void policy as governing nothing, so this is a departure. Whether an obligation was met does not depend on the request whose conflict voids the policy, and dropping it would let a request hide a violated obligation by asking for a use the policy forbids. Validity and evaluation are separate concerns: a malformed policy is rejected at W1 or by the checkers, while a well-formed policy that voids itself for one request is an evaluation outcome, visible in the trace (`eliminated`, rule `invalid`). OVAL reports such a policy as not evaluable (`oval-conflict-invalid`), which conflates the two. *`Indeterminate` with a cause* — the fail-safe alternative, a value outside the chain needing its own computation — stays parked; revisit if a real policy needs a void policy to block rather than abstain.

### 6.3 Two kinds of question **[D]**

Only one of the three duty triggers is answerable at request time. Preconditions gate a permit, so `decide` resolves them. Remedies and consequences fire on events that have already happened or failed to happen — that is obligation monitoring against accumulated state, not an access decision.

So the interface is two functions over the same corpus:

- `decide` returns a verdict plus duties that *would become owed*.
- A separate query returns duties *currently owed* for a party.

In workflow terms, both share W1 and W2's matching, constraint, and fulfilment machinery, and differ in the predicate applied to root atoms and in the W3 reduction. The access answer already reports the obligations *in force* for the request — those of the policy it is made under — with their status (`due2-workflows.md` §5.2, §6.1). What remains open is the request-free query: everything a party owes now (#6). A split left out of the signature gets bolted on later as a special case.

---

## 7. Ledger **[D]**

Every decision is recorded. Because `decide` is pure over `(corpus, request, SOTW)`, the ledger records every case and its evolution, each evaluation replayable, and every production decision can become a conformance case — the conformance suite fills itself. A case is created when a request is made; an evaluation is one run over it (`due2-workflows.md` §7).

**Re-evaluate, never patch.** The temptation is to find `Pending` cases whose petition has been approved and flip them. A `Pending` record is not a promise; it is a decision made under facts that have since changed, and the only sound way to learn the new answer is to ask again.

**A case and its evaluations pin their inputs:** request, policy version, **both normaliser versions** — the stage-1 profile IRI and version, and the stage-2 builder version (the corpus is derived, so a normaliser change gives a new corpus, and a new case over it can get another verdict with no policy edit) — and the SOTW, which is the case's own record of the world: the facts consulted, with their values (the trace's `read` relation; `due2-workflows.md` §3.3). Values, not timestamps into a source, so the entry stands even when the source keeps no history.

**The direction is not only upward.** Re-evaluation can turn Permit into Deny — a role changed, a dataset was reclassified, a policy was amended. An amendment reaches an earlier request through a new case over the new corpus, since a case fixes its corpus (`due2-workflows.md` §7.1). A mechanism built as "upgrade pending to permit" has no path for that, and revocation matters more to a control function than issuance. The operation is verdict-agnostic and the ledger records transitions both ways.

**Two clocks, and two events.** "What is the verdict now" and "what did we decide on 3 March, and why" are different queries; decision time and validity time are both first-class or the audit answer gets reconstructed from today's policy and is wrong. Separately, decision and exercise are distinct events: revoking a permit does not unmake access already taken under it. In the data model, decision time is `sotw.effective_at` and validity time is `request.at` (`due2-workflows.md` §3).

**The case flow.** A request whose verdict is `Pending` records the duty instances it awaits — the trace's `instance` and `alt_duty` relations. Evidence submitted later is recorded in the case's SOTW, and evidence for a grant-scoped duty names the duty and the request's `reference` (`due2-workflows.md` §3.3, §5.3). The next evaluation, over a new SOTW, finds it and may return `Permit`; nothing in the earlier trace changes. That evaluation asks at its own time: its request is the case's with `at` moved to its `effective_at`, so a payment made after a time window has closed cannot reopen it (`due2-workflows.md` §3.2, `decisions/0030`).

**Re-evaluation trigger [O]:**

- *Explicit calls.* Whoever records a changed fact on a case asks for its re-evaluation (submitting evidence evaluates the case by itself), and re-evaluating every pending case is a loop of such calls; there is no subscription (`due2-platform.md` §2.6, `decisions/0046`). A policy or normaliser change reaches a request only when its case is reopened, as a new case (above). Trivially correct, no bookkeeping. Pending sets in governance are small and approvals are rare, so this is almost certainly sufficient. **Start here.**
- *Dependency index.* Index pending cases by the state properties in their `read` relation, which W2 already produces as a byproduct. Justified only when the first option measurably hurts.

---

## 8. Relation to prior work **[D]**

### 8.1 The Southampton work

Salas, Pareti, Yumuşak, Gheisari, Ibáñez and Konstantinidis, *Evaluation and Comparison Semantics for ODRL* (arXiv:2509.05139). due2 takes from it the shape of duties and the reading of approval as a fact (below), and diverges from it on unknowns, duties without evidence, and verdicts.

The comparison below covers that paper, *A Formally Grounded ODRL Evaluator* (arXiv:2607.15987), *ODRL Policy Comparison Through Normalisation* (arXiv:2603.12926), and OVAL, their evaluator, at commit `40b8ac6` (#55). Items marked **[O]** are candidates for due2, not adopted.

- **Monitoring and access control, formally (2607.15987).** Def 1 defines offline monitoring of a state of the world ω and Def 3 defines online (streaming) monitoring. Def 5 defines access control: a request is accepted iff ω ∪ {e_R} is valid, where e_R is the requested event. Thm 4.1 shows the two coincide under two conditions: the stream arrives one event at a time, and the policy uses only permissions, prohibitions and duties. This sharpens the Modality row below. In their semantics, the "post-action state" is ω ∪ {e_R}, and that is a set union, not a prediction. The difference from due2 lies elsewhere: in ω ∪ {e_R} an unknown feature is false, and a duty with no event is violated, whereas due2 returns `U` and `Pending`. **[O]** Their Defs 1 and 3 are a candidate definition for due2's monitoring question (#6), with `U` in place of false. They do not settle #6, which is blocked on requirements.
- **Comparison by normalisation (2603.12926).** Constraints are put in DNF. Operators are regularised to `==`, `<` and `>`, and numeric and temporal ranges are split into disjoint intervals. Containment then becomes set membership over the intervals, and prohibitions are subtracted from permissions. The set operators are excluded. Their normal form is a constraint normal form. due2's stage 1 is structural: it produces atomic rules and preserves `Den` (`odrl-compound-to-atomic-normalization.md` §8.1). The two compose rather than compete. **[O]** A policy-diff spike (#15) would run their comparison over due2's atomic rules. It would then have to say what to do with `isA`, `isPartOf`, `hasPart` and the list operators, which due2 admits (`decisions/0005`) and their comparison excludes.
- **OVAL's access-control mode** (`ODRL_Evaluator.py`, `evaluate_ODRL_access_request_on_dataframe`, at `40b8ac6`). It has a mode for single prospective requests, and the Nulls, Absence of a duty event, Verdict, Conflict and Default rows below say what it does.

**Reasoning.** Their semantics keeps hierarchy reasoning out of the core, under unique names, and materialises it instead (2509.05139 §3.3). 2607.15987 repeats that "the chosen semantics does not include reasoning". OVAL nevertheless has `reasoning=True` by default, over the ODRL vocabulary. Its code expands only a rule's action (`includedIn`), assignee and target (`partOf`) into their transitive descendants; constraint values get no hierarchy. due2 has the same shape: comparison by identity, and declared hierarchy edges in a closed-world closure (`due2-profiles.md` §6). due2 extends it to `isPartOf`, `hasPart` and `isA` (`due2-profiles.md` §4), and to SKOS concept schemes on constraint operands (`decisions/0015`). The missing hierarchy on constraint values was reported to OVAL as DIPS-Tools/ODRL-Engine#8 (`conformance/external/README.md`).

**What it confirms.** Duties there are relations over rules — pairs and triples — rather than nested structures, which is independently the shape of §3. It also requires that a duty rule be exercisable by the obligated party, a well-formedness check worth adopting. And duty preconditions are temporal over the event log: the permission is violated if it matched and no matching duty event exists at an earlier timestamp. That settles the question §7 raises — approval is a **fact** in the event set, not a discharge operation — which is what makes re-evaluation purely derivable, and what §3.1 builds on.

**Where it diverges, and why it matters to us.**

| | Their semantics | due2 |
|---|---|---|
| Modality | Monitoring: is this state of the world violating? Access control is validity of ω ∪ {e_R}, and it coincides with streaming monitoring for permissions, prohibitions and duties (2607.15987 Def 5, Thm 4.1) | Access control at request time, over a world in which features may be unknown; monitoring is open (#6) |
| Nulls | An unspecified feature makes any condition false, following SPARQL filter semantics. OVAL also lists *conditional matches*, rules that would match for some value of an unspecified feature, with a warning. Its decision uses full matches only. At `40b8ac6` the null re-evaluation did not reach inside a logical constraint; since `596f10c` it does (DIPS-Tools/ODRL-Engine#9) | `Indeterminate` is a distinct verdict (§6.1) |
| Absence of a duty event | Violation. OVAL's access-control mode makes it a switch, `semantics_for_duties`: 1 (the default) accepts on the promise that the duty will be fulfilled; −1 rejects without evidence of fulfilment | Not yet fulfilled: the duty is outstanding and the verdict `Pending` (`due2-workflows.md` §5.3) |
| Verdict | Per-policy boolean, valid or violated. OVAL's access-control mode returns accept, reject, or `None`, plus an English explanation list and the matched rules with their null-only conditions and unfulfilled duties | Per-request, five-valued, with a trace whose explanation is machine-readable (`decisions/0010`) |
| Conflict | Prohibited-by-default, structurally; prohibitions carve out subsets of permissions. OVAL's access-control mode reads the policy's `conflict` value: 1, permissions override; −1, prohibitions override; 0, the policy is invalid and no decision is made. An absent value is read as 0 | `conflict` strategy read from the policy (§6.2) |
| Default | Prohibited-by-default in the semantics. In OVAL it is an evaluator switch, `semantics_by_default`: −1 rejects, the default; 1 accepts; 0 returns `None` | `NotApplicable`; the default is the enforcement point's (`conformance/external/README.md`, finding 8) |

**One restriction to check our policies against:** they require each boolean combination of constraints to use features of a single ODRL component. Constraints on the requester's department satisfy this. A constraint *relating* two components — requester's department equals the dataset's owning department — does not.

**The part worth taking.** Because matching is a boolean query, policy comparison becomes query containment and equivalence: deciding whether one policy is equivalent to, more restrictive than, or more permissive than another. That gives a **policy diff** — "is this amendment strictly more restrictive than the version it replaces" — which is hard to build any other way and directly useful for change control. **[O]** — worth a spike; it is a capability, not a dependency.

### 8.2 RL2

RL2 (`github.com/matthiasautrata/RL2`) is due2's predecessor: an attempt to extend ODRL into a language of its own, with formal semantics. It is not a superset of ODRL — it has its own vocabulary and a partial translator — and it has never been executed. due2 harvests it rather than adopting it (`decisions/0001-rl2-as-donor.md`).

Harvested — section numbers cite RL2's specs (`Model` = `spec/RL2_Model.md`, `Semantics` = `spec/RL2_Semantics.md`, `Compilation` = `spec/RL2_Compilation.md`):

- **Evidence and fulfilment** — Model §4.3–§4.5, §7.3: evidence as records of performed actions; absence means not yet fulfilled; trust verified before evaluation, with a closed signer admissibility record.
- **Duty instances** — Semantics §Duty Template Binding: per-member and per-grant occurrence identity, with evidence naming the grant it discharges.
- **Typed operands** — Model §4.2–§4.4: value types, the missing / invalid / conflict discipline, and admissibility by source, merged with DPROD's one-hop bindings (`due2-profiles.md` §3). RL2's freshness filter is not harvested: keeping values current is the SOTW service's job (`decisions/0040`).
- **Guards and witness conditions** — RL2's `condition` and `postCondition` (`due2-workflows.md` §5.2).
- **The use cases** — all 49, rewritten in ODRL as `conformance/cases/rl2-*` (§10).

Left behind: the vocabulary, Maintain duties, Promises, Offer → Agreement materialisation, and duty status as an operand. The corpus records each case that needs one of them.

Sources for open items:

- stage 2 — RL2_Compilation: canonical projection, closed-world rule, determinism; its diagnostic registry became `due2-diagnostics.md`;
- conflict resolution and exception patterns — Semantics §Conflict Resolution;
- profile operators — Compilation §9.1 (`due2-profiles.md` §4);
- replayable policy selection and the re-evaluation loop — ExternalData §6–§7.

### 8.3 DPROD Contracts

DPROD Contracts (EKGF, `github.com/EKGF/dprod`, branch `develop`, `dprod-contracts/`) is an ODRL 2.2 profile for data contracts with deterministic evaluation — much of RL2's intent, expressed the way ODRL intends. due2 handles it as a profile, with no translation: its operand bindings are due2's (`due2-profiles.md` §3), and its other terms land on due2's extension points (`due2-profiles.md` §8.1). Where DPROD returns a decision, due2 returns the same one, outside six documented exceptions; where DPROD fails, due2 still decides when the unknowns cannot change the outcome (`due2-profiles.md` §8.2). Testing DPROD's examples also found gaps in DPROD itself, listed there for upstream. Everything adopted from DPROD is provisional against the vendored commit, pending a stack of upstream PRs (`due2-profiles.md` §8, issue #35).

---

## 9. Execution **[O]**

`ways-of-working.md` §10 gives the general rule. Specific to due2:

**The shape [D]:** an evaluator interprets atoms in memory. W1 is a Python batch job, run once per policy version (`decisions/0002` #1). The language of W2 and W3, and of the service that hosts them, is open, with Kotlin leading (`decisions/0027`, #104). The corpus, JCS JSON named by its digest (`decisions/0007`), is the only thing that crosses from W1 to W2 and W3, and nothing after W1 reads RDF. Agents as well as people will call the evaluator, so it must handle more requests, and more at once, than governance alone would bring. An in-memory interpreter keeps the per-decision explanation cheap. `due2-workflows.md` keeps the semantics independent of the implementation language.

**First optimisation, if needed:** index the corpus by action and target. Most of the available speedup is in not evaluating irrelevant atoms, and the candidate set drops from thousands to a handful. It is sound because a root atom that certainly does not apply is neutral in W3 (`due2-workflows.md` §5.5, L8). It needs no new language and runs under the same conformance suite. Exhaust this before adopting a second semantics.

**Only then**, and only against measurement: Rego/OPA, Rust in process, or SQL compilation, with the trade-offs in `ways-of-working.md` §10.3. Note that for entitlement-scale work the interesting property of Rego is *partial evaluation* — a residual condition pushed into a query, so one call returns what a party may see — not raw throughput. If Rego earns its place, that is why.

**What none of these fix.** Entitlements and realtime do not fail on a slow evaluator. They fail on cardinality (millions of resource-party pairs stop fitting the expand-everything model — a normalisation-strategy problem), on SOTW freshness (a p99 dominated by resolving whether someone is still in home lending), and on explanation cost (building a full reason per decision is affordable in governance and may not be at volume). A faster evaluator addresses none of the three.

### 9.1 Measurement before argument **[O]**

Record before the debate: p99 with the resolver excluded, atoms evaluated per request, evidence-set size, and whether every decision must carry an explanation. If kernel time is not a clear majority of the budget at realistic volume, a compiled hot path buys nothing.

---

## 10. Conformance suite **[D]**

One suite, parameterised by backend from the start (`ways-of-working.md` §10.2). It is the cheapest thing to build first and the most expensive to retrofit.

Contents:

- Generated policies and requests: bounded-exhaustive enumeration over a tiny vocabulary, and Hypothesis over larger inputs, from one description of the input space (`correctness-strategy.md` §1.1, §5).
- The laws of `due2-workflows.md` §8, as properties.
- The case corpus in `conformance/`: the RL2 use cases rewritten in ODRL, the DPROD Contracts examples, cases translated from other evaluators' suites (FORCE, OVAL, and the W3C formal-semantics cases), and cases authored for due2 to cover what no origin exercises (`conformance/README.md`). Each case has scenarios and hand-derived expected verdicts, and `tools/check_corpus.py` checks them mechanically.
- The semantic-preservation property, L9 (`due2-workflows.md` §8): `decide(normalise(p), r, w)` equals `interpret_directly(p, r, w)` whenever the completion is exact; beyond the `max_mixed` bound, the pipeline's verdict only refines the direct one. The direct interpreter over the authored policy is the clingo semantics program, clingo-i (`decisions/0009`). Stage 1 has its own oracle as well, the denotation `Den` of `odrl-compound-to-atomic-normalization.md` §8.1, checked through the lineage bijection, and it moves into the formal model (`decisions/0021`, `correctness-strategy.md` §4.8). Maintaining a second interpreter is costly, and L9 is the only check that the rest of normalisation has not quietly changed meaning.
- Explicit `Indeterminate` cases with unresolvable operands, asserted per backend. This is the property most likely to be silently lost in a port.
- Every recorded evaluation, replayed.
- Differential mode across backends, once there is more than one.

---

## 11. Open decisions register

Workflow-level decisions — canonical encoding, cross-policy strategies other than prohibit-overrides, preference among alternatives, the monitoring question, request match keys — are registered in `due2-workflows.md` §9. Duty timing is decided (`due2-workflows.md` §5.3, `due2-profiles.md` §7).

**Tracking.** Open items are recorded as GitHub issues (labels `open-decision`, `corpus`, `verification`, `work-item`, `parked`); each issue names its source-of-truth section. This convention is stated here once and covers every open-decision register — this one, `due2-workflows.md` §9, `due2-profiles.md` §9, `ways-of-working.md` §13, `correctness-strategy.md` §9: a register remains the specification record, a resolution lands in it, and the issue closes. Sub-issues, milestones, and the development cycle are `ways-of-working.md` §14. The execution-target issue (#16) also covers `ways-of-working.md` §13 #10, #11, and #13.

Rows keep their numbers, because issues cite them. Rows 1, 3, 4, and 6 are resolved, and their resolutions are in §4 item 3, §4 item 5, §6.2, and §9–§10.

| # | Decision | Section | Issue | Blocked on |
|---|---|---|---|---|
| 2 | Atom-count threshold values and diagnostic | §4 | #11 | The first pathological policy. Only DNF is exponential (`decisions/0003`), and its exact-count limit is decided (§4 item 3) |
| 5 | Re-evaluation trigger: explicit calls (`decisions/0046`) vs dependency index | §7 | #14 | Measurement once pending volume is known |
| 7 | Policy diff via query containment | §8.1 | #15 | A spike |
| 8 | Execution target beyond indexed in-memory evaluation | §9 | #16 | Measurement per §9.1 |
