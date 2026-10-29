# Reviews of 2026-10-29

Two outside reviews of revision `05a7049`, received on 2026-10-29. Part 1 is one review. Part 2 is a second, adversarial review of the same revision: is due2 more complicated than it needs to be? Part 3 is the second reviewer's reconciliation with the first, followed by its report again with §11, the addendum that reconciles the two. The responses are tracked in the milestone *Review 2026-10-29*.

Changes from the text as received: headings are nested under their part, and lose their trailing full stops; a table in Part 3 whose box-drawing characters arrived corrupted is rewritten as a Markdown table, and two corrupted characters (`≠`, `§`) are restored; blank lines and spacing follow rumdl. The words are unchanged.

## Part 1

### Overall judgment

**The unease is justified—but I would restart the delivery plan, not the repository.**

There is a sound core here: frozen inputs, explicit unknowns, evidence-derived fulfilment, policy-local evaluation, and replayable reasons. The complication comes from combining that core with several stronger promises before exercising the production path:

- decisions invariant across correlated completions;
- every sufficient duty route under uncertainty;
- precise pivotal causes;
- globally reconciled identities across independently published policies;
- a general profile system and an event-driven case platform.

Those are defensible choices. **They are not all consequences of ODRL.** A simpler evaluator is possible, but preserving every current promise will preserve much of the complexity.

The review also found **two reproducible clingo/Python boundary defects and one important normal-form contract gap**.

Reviewed revision: `05a7049`. No repository files or issues were changed.

### 1. Material findings

#### High — An unrelated policy’s profile can change who fulfils a duty

Profile-derived `function`, `bearer_fn`, and `attester_fn` declarations are global, although hierarchy evaluation and operand bindings are policy-local. See the `lift.lp:155-172` and the `interpret.py:341-349`.

An in-memory counterexample reproduced this:

- Policy P requires compensation. Its duty names the bank as `odrl:informedParty`, but no bearer; the requester is Alice.
- Evidence records compensation by the bank, not Alice.
- Policy Q is unrelated and does not match the request. Q alone selects a custom profile assigning the bearer role to `odrl:informedParty`.

| Evaluated policies | Actual verdict |
|---|---|
| P alone | `Pending` |
| P and unrelated Q | `Permit` |
| Q and P | `Permit` |

Q’s profile changes P’s duty interpretation. That violates locality, not merely an explanation preference.

**Direction:** resolve *all* profile-derived semantics within each policy’s environment—not only bindings and conflict defaults. This is a boundary repair, not a reason to replace ASP.

#### High — A module shared by two profiles disappears from one policy’s hierarchy

`_layers()` assigns each module path to one profile using `setdefault`. But inclusion in profiles is a many-to-many relationship, not single ownership. The `interpret.py:363-374` feeds the `lift.lp:654-669`.

A second in-memory counterexample used two custom profiles including the same module. That module supplied an action-hierarchy edge:

| Evaluation | Actual verdict |
|---|---|
| Q alone, selecting its profile | `Permit` |
| Q plus unrelated P, selecting the other profile | `NotApplicable` |

The edge remained available to the first profile but disappeared from Q’s data space.

**Direction:** represent module membership explicitly. A shared file must not acquire one exclusive profile owner.

Both defects escaped the existing locality tests because their principal adversarial variation is **hierarchy edges**, not changes in profile declarations or shared module membership. The `test_locality.py:50-76` makes that boundary visible.

#### High — The planned normal form cannot express every admitted negation

The flat corpus stores constraints and conjunctive attachments, with no polarity field or Boolean-expression relation. See the `due2-workflows.md:85-98`.

However, the language admits `dprod:not`, while lowering defines only four operator-complement pairs:

- `eq` / `neq`;
- `lt` / `gteq`;
- `lteq` / `gt`;
- `isAnyOf` / `isNoneOf`.

See the `due2-profiles.md:175`.

What represents **not an instance of C**—`not(x isA C)`—in the flat corpus? There is no specified negative `isA`, nor a sign on its attachment. The same issue affects `isPartOf`, `hasPart`, and `isAllOf`. It also arises through ordinary `xone` expansion, which introduces negated members.

The admission checks accepted a small `not(isA)` policy without diagnostics. clingo-i interpreted it correctly because it retains the expression tree. **The missing contract is the lowering into the future evaluator’s input**, not the authored interpreter’s answer.

The smallest repair may be **signed leaves**. Retaining a Boolean DAG is another option. Rejecting these forms is possible but would deliberately narrow the supported fragment.

This should be settled before implementing W1’s builder.

### 2. Where the avoidable complexity lies

#### A. “Flattening makes evaluation simple” is only partly true

Flattening structural action/target/party combinations has a clear justification. Mandatory constraint DNF is less obviously beneficial.

For example,

$$
(a_1 \lor b_1)\land\cdots\land(a_n\lor b_n)
$$

has $2^n$ DNF terms—even without `xone`.

Expansion removes Boolean structure from individual runtime atoms, but creates work elsewhere:

- more atoms and derived identities;
- lineage for the expansion;
- correlation between generated literals;
- reconstruction of authored-level explanations;
- preservation obligations between two representations.

The existing interpreter already evaluates Boolean trees without that expansion.

**Starting again, I would seriously compare structural atomisation plus a bounded Boolean DAG against mandatory DNF.** A DAG can still be represented as flat node-and-edge relations; it does not require runtime RDF.

The trade-off is real: W2 gains Boolean evaluation, and its trace contract changes. This is not an automatic improvement or a safe cosmetic refactor. The question is whether it reduces *total system complexity*, rather than just moving it.

#### B. Auditability and minimal causal explanation are different requirements

Replayable inputs and sufficient reasons are essential to this project. They do not automatically require:

- identifying exactly every pivotal literal;
- enumerating every sufficient route;
- proving that the reported frontier equals every completion’s frontier.

The `pivot.lp:1-37` is compact and elegant. Its cost comes from the promise it implements, not poor coding.

A simpler product could report broader relevant unknowns and certified sufficient routes, explicitly marking incompleteness. That would sacrifice precision, not necessarily safety.

**But that would be a semantic/product decision.** It must not be introduced silently as an implementation shortcut. If the current exactness promises are required, much of this machinery earns its place.

#### C. Semantic identity need not imply globally interned runtime objects

Shared duty identity matters. Arbitrarily cloning a duty per attachment would be wrong.

But the current design also requires publication-time agreement and reconciliation of freshly minted IDs across compiled corpora. See the `due2-platform.md:211-223`.

I would revisit the distinction between:

1. the authored identity of a duty;
2. its compiled occurrence or binding;
3. its evaluation entry in a policy;
4. the evidence that fulfils it.

Two stored evaluation records do not inherently require two performances. The evidence-matching rule decides that.

Since findings and activations are now policy-entry-specific anyway, **global physical deduplication buys less than the earlier design assumed**. A clean-slate design should consider immutable policy-local compiled units retaining authored identities, then fold their entries. Any required cross-policy agreement check can remain explicit.

This is an architectural alternative—not a claim that the current identity semantics can simply be deleted.

#### D. The assurance is strong inside some models and weaker at their boundaries

The response should not be “fewer tests.” The tests are valuable.

The problem is distribution of attention. Thousands of generated Boolean cases do not establish that:

- profile environments compose correctly;
- an input module can belong to several profiles;
- the normal form is closed under every admitted operation;
- the projected authored reply preserves the distinctions required by the full trace.

The new counterexamples are tiny. Their importance comes from crossing boundaries, not reaching greater Boolean depth.

**I would move the next assurance effort toward these seams before adding another verification layer.**

### 3. What I would change in the workflow and plan

The local discipline is mostly good: bounded reviews, explicit decisions, executable acceptance criteria, honest declines, and separate slow checks should stay.

The programme-level sequence is the concern. It currently puts relation vectors, the oracle’s second interface, and W2/W3 ahead of both W1 stages and the eventual full-path gate. See the `correctness-strategy.md:252-262`.

That is not a dependency deadlock—the vectors can be written now. But it delays discovering whether the complete architecture is smaller and clearer in practice than on paper.

**I would make the next deliverable one narrow production-shaped vertical slice:**

1. One fixed profile and a few representative policies.
2. Actual normalisation into the declared evaluator input.
3. Evaluation against a supplied frozen snapshot.
4. A complete trace with resolvable references.
5. Recording and byte-for-byte replay.
6. Differential comparison with clingo-i.

Unsupported features should be rejected or declined explicitly. Then widen the **same implementation**, one feature at a time—not build a disposable “lite” implementation beside it.

This follows the project’s own `ways-of-working.md:340-342`, but applies it across the programme rather than only within individual components.

I would also:

- keep recurrence and monitoring outside that first slice—they are already parked;
- settle language on deployment and maintainability grounds, without turning forecast agent traffic into an unmeasured performance conclusion;
- avoid reviving the cancelled backend bakeoff through continuing comparison administration;
- avoid another broad architecture expansion until this slice produces concrete evidence.

The known frontier mismatch [#103](https://github.com/matthiasautrata/due2/issues/103), mixed hierarchy planning gap [#144](https://github.com/matthiasautrata/due2/issues/144), and formal-key gap [#153](https://github.com/matthiasautrata/due2/issues/153) remain qualification limits. They are tracked limitations, not new discoveries from this review.

### 4. What I would keep

- Unknown distinct from false.
- Pure evaluation over frozen inputs.
- Evidence-derived fulfilment.
- Policy-local environments and per-policy conflict resolution.
- RDF confined to the authoring boundary.
- Hand-derived cases and independent differential checks.
- clingo-i as an oracle independent of the production evaluator.

In particular, **I would not replace clingo merely because the files look large**. The ASP comprises 4,887 physical lines, but parsing it counted 746 rules with bodies and 248 fact statements; much of the apparent size is documentation and vocabulary tables. The completion, resolution, and pivot techniques have understandable purposes.

The clearest simplification target is the **contract and representation surrounding that kernel**, not its syntax.

#### Verification performed

- Shared tests: **516 passed**, 2 skipped.
- clingo-i fast suite: **2,663 passed**.
- Corpus through clingo-i: **461 passed, 0 failed, 41 unsupported**.
- Corpus admission and abstract completion checks passed.
- The independent counterexamples above reproduced despite that green baseline.

The slow suite and Alloy models were not rerun for this review.

**Recommendation:** repair profile isolation, settle the normal form’s treatment of negation, and deliver one narrow end-to-end slice. Reconsider mandatory DNF and global compiled-object reconciliation with evidence from that slice. Do not throw away the corpus or start another evaluator from a blank page.

## Part 2

### due2 review: is it more complicated than it needs to be?

**Revision:** `05a7049` (2026-10-29 07:37 EDT), clean checkout. **Date:** 2026-10-29.
**Asked:** an adversarial review of design, workflow, plans, then code, especially the clingo program — and: if we started again from scratch, what would we do differently?
**Method:** six independent read-only reviews (semantics/spec; decision history; process and verification; the ASP program; the Python driver and tests; data model, schema, and corpus), each with a fixed charter, severity scale, and a required steelman per finding; then verification of every load-bearing claim by the coordinator. Experiments ran on copies under `/tmp`; the repository was not modified. Unpushed work on another machine is not covered.

Severity: **Blocker** — unsound, or wrong answers on admissible input. **Major** — accidental complexity or cost that keeps compounding. **Minor** — local.
"Verified" means re-run or re-read by the coordinator, not only reported by a reviewer.

---

#### 1. Conclusion

The unease is justified, and it is mostly not "ODRL is like that".

ODRL 2.2 is genuinely under-specified — no evaluation semantics, no source for operand values, unclear duty and conflict semantics — so a serious evaluator must decide a few dozen readings, and roughly a third of the 50 decision records are exactly that and look healthy. But most of the weight comes from five choices due2 made itself, each for a generality no real policy or consumer has yet demanded:

1. **Exact `Indeterminate`** over correlated literals (completion keys, mixed variables, `max_mixed`, pivots, routes that suffice, `frontier_complete`).
2. **One merged corpus with shared node identity** across policies — then, after it leaked, per-policy data spaces threaded back through every relation (`decisions/0036` → `0050`).
3. **A flat DNF atom form** with minted ids and a lineage collection, which W3 never needs to see.
4. **The full 16-relation trace as the byte-compared port**, ahead of any producer or consumer.
5. **The platform shell (ledger, sources, world edges, read limits) specified as relations** before any of it is built.

A process that turns every review finding into more contract — never into less — and that runs faster than one owner can weigh (14 decision records on 2026-10-26) did the rest.

Measured, not argued:

- Replacing exact completion with the spec's own sound fallback (every unknown independent; verdict and range by two folds) changes **5 of 467** evaluated verdicts, all `Permit → Indeterminate`, all in **3 due2-native cases built to exercise the layer**. **0 of 330** translated scenarios change. (§5.1)
- The cross-policy design is still leaking after this week's five fixes: one metadata triple about an offer, placed in the agreement's text, turns `NotApplicable` into `Permit` through the offer's rule (reproduced on `05a7049`, found independently by two reviewers). (§4.1)
- About 15% of all churn is executable code; 81% of commits touch bookkeeping; the evaluator has been "Next #1" since 2026-10-24 while the spec grew 30% and the schema went 1.0 → 3.0. (§5.8)

The good parts are real and worth keeping: Kleene logic with value statuses, the five verdicts with routes and dominance, the monotonicity argument that makes the verdict two folds, bindings as data, content-addressed pure evaluation, the hand-derived corpus with its `why`, and — in clingo-i — `resolve.lp`, `pivot.lp`, and the cautious/brave completion idea, which are exemplary ASP.

**Recommendation:** keep the boundary (`plan`/`decide`, RDF outside W2/W3) and the core semantics; cut the five generalities to a v1 envelope; fix the verified defects now; restructure clingo-i into two stages at the W1|W2 boundary; and start the evaluator against a frozen, small port. §7 gives the from-scratch alternatives ranked, §8 the decisions in the order to take them.

---

#### 2. Scope and limits

- Read: all of `docs/` (spec, design, decisions 0001–0050, correctness, briefings, archive), `spikes/clingo-i/` (14 `.lp` files, driver, tests), `tools/`, `tests/`, `schema/`, `conformance/` (format, sample cases, external triage), `formal/alloy/`, CI workflows, the 157 issues, git history, and the earlier reviews in `~/src/reviews/due2-2026-10-{24,25,27,28}/`.
- Ran: the full verify job and corpus locally (all green at `05a7049`; see the 2026-10-29 sync), the completion experiment over the whole corpus, and thirteen targeted clingo-i probes (`clingo-probes/`).
- Not covered: work not pushed from another machine; real organisational policies (none are in the repository); latency at production volume.

---

#### 3. What ODRL forces, and what due2 chose

| Concept | Forced by | Verdict |
|---|---|---|
| Kleene logic with value statuses (`missing`, `invalid`, `conflict`, `unresolved`, `misfit`) | Goal 1, "unknown is never false" | **Keep.** The differentiator. |
| Five verdicts, `verdict_range` | ODRL duties (Pending), goal 1 | **Keep.** The range is two folds. |
| Expanding action, target, party; compact-policy interiorisation | ODRL IM §2.7 | **Keep.** |
| Conflict strategies `perm`/`prohibit`/`invalid`; prohibit-overrides across policies | ODRL IM; one fixed cross-policy rule | **Keep.** |
| Duties as preconditions, fulfilled by evidence; guards vs witness conditions | ODRL IM §2.6, DPROD, RL2 | **Keep.** |
| Frontier: collapse by duty set, dominance by inclusion | due2's product (tell the requester what to do) | **Keep.** Elegant, cheap. |
| Bindings as data; profile layers; units; concept schemes | ODRL leaves operand sources undefined | **Keep**, mostly. Concept `eq` as ⊑ is a second meaning of `eq` (forced 0023). |
| Content-addressed inputs, pure `decide`, replay | Goal 3 | **Keep.** Cheap. |
| Literal completion keys, mixed/uniform, `max_mixed`, `exact` | Nothing; due2's precision goal | **Cut** (§5.1). |
| Pivotal literals | Nothing | **Cut** or offline tool. |
| Routes that suffice, `frontier_complete` by enumeration | Nothing | **Simplify** to pessimistic routes; complete iff no uncertain candidate (0004 option A). |
| Shared node identity, agreement precondition, publish renaming, entries | Nothing; only locality is needed | **Cut** to policy-local corpora (§5.2). |
| DNF of rule constraints, `xone` expansion, minted disjunct ids, lineage, L9 | W1's own rewrites | **Cut**: evaluate authored trees (§5.3). |
| 16-relation trace as byte-compared port; L10 per-witness rules | Goal 2 needs reasons, not this encoding | **Shrink** to an Answer; explanation beside it (§5.4). |
| `plan`/`Reads` (6 relations), world modules, `max_reads`, source combination, source versions | A closed-world hierarchy over limited fetches | **Defer**; make world hierarchy answers facts with a status (§4.4). |
| Ledger, cases, events, activations fed back from traces | Goal 3, platform | **Defer** to when the shell is built (one sentence now). |

Roughly 16 of the 50 decision records are ODRL readings and admission rules that look healthy (e.g. 0003, 0029, 0031, 0033, 0034, 0045); 34 descend wholly or partly from the five choices above (decision-history reviewer's count; spot-checked).

---

#### 4. Defects — fix regardless of any strategic choice

##### 4.1 Blocker — policy locality (L11) still leaks in clingo-i. **Verified.**

`lp/lift.lp:651`: `policy_text(P, Text) :- policy(P), text_triple(Text, P, _, _).` A text "states" policy `P` if it has *any* triple whose subject is `P`. Since `policy_text` feeds the per-policy hierarchy (`lift.lp:667`), any text that mentions `P` joins `P`'s data space.

Reproduction (`clingo-probes/e3b.py`): an offer `ex:offer` permits `odrl:use` of `ex:catalog`; an agreement (assignee `ex:bob`) states `ex:report1 odrl:partOf ex:catalog`. Alice asks for `ex:report1`:

| Agreement text | Reply |
|---|---|
| as above | `NotApplicable` (correct: the edge is the agreement's) |
| plus `ex:offer dprod:offerLifecycleStatus dprod:Accepted .` | **`Permit`**, basis `ex:read` — the offer's own rule |

The driver reviewer found the same root with `ex:p rdfs:comment "…"` (and a decline with `ex:p ex:relatedTo ex:q`). Sibling channels (ASP reviewer, reported): a stray `ex:p1 odrl:target ex:b` in another text adds a target to `p1`'s rule (e3c); `dct:isReplacedBy` in another text turns the whole vector into `ReplacedPolicy` (e10); a shared named rule described differently by two texts is silently merged where §4 requires `IdentityConflict` (e2, e8 — `_combine` compares only bindings and conflict strategies).

Why the tests miss it: the L11 generator (`tests/test_locality.py:50–68, 111–161`) never puts a triple about the vector's own policy into the second text; the brute-force differentials are single-policy.

Fix: minimal — a text states `P` only if it types `P` as a policy (or the driver supplies `text_policy` from each solve 0), and the generator annotates the vector's policy IRI. Structural — §5.6 (corpus solves never read `triple/3`).

##### 4.2 Major — integrity constraints do not catch partial gaps. **Verified.**

`integrity.lp:3–6` and `TESTS.md:11` promise that a deleted rule fails loudly. It does not when the gap affects only some items or some completions:

- Delete `node_space(Duty, P) :- duty_of(Y, Duty), space(Y, P).` (`constraint.lp`): a duty whose guard is false becomes owed — `Permit` becomes `Pending`, no error (`clingo-probes/e9.py`, re-run here). The `#min` over guard ranks (`duty.lp:204–205`) skips the guard with no rank.
- Delete the rule `DELETIONS` itself deletes (`completion.lp:389`) and use an input outside the test's own vector: `NotApplicable` where the intact program gives `Indeterminate` (driver reviewer, reported).

Fix: derive `defect/…` atoms instead of `:-` constraints and read them bravely; make guards and witness conditions part items so the one-value constraint covers them.

##### 4.3 Major — `eliminated` under unknowns states a reason that does not hold. **Verified.**

`clingo-probes/e1.py`: policy p1 (`perm`) has a `u` permission (`ex:x eq 5`, unresolved) and a `t` prohibition; policy p2 has a `t` permission. Reply: `Indeterminate`, `Deny..Permit`, and `eliminated: perm2 by forbid (prohibit-overrides)`. With `x = 5`, the prohibition is removed inside p1 and the verdict is `Permit` — `perm2` is not eliminated. `explain.lp:157–158` reads "not surely removed" as "survives", contradicting its own invariant (`explain.lp:12–15`: each row is a complete reason). The Python oracle copies the same approximation (`test_brute_force.py:605`), so nothing checks it independently. The spec (§3.5) does not define `eliminated` under unknowns: a spec gap first.

##### 4.4 Blocker for production — closed-world hierarchies over plan-limited fetches can fail open

`due2-workflows.md` §3.3 (l.174) reads world hierarchies closed-world: `a ⊑ b` is `U` only if an answer is `unresolved`, else `F`. `plan` (l.209–214) lists only the request's entities and the corpus's narrower values. Issue #144 (open) gives the counterexample: the policy states `ex:ds partOf ex:collA`, the catalog knows `ex:collA partOf ex:collB`, nobody asks about `ex:collA`, and `ex:ds ⊑ ex:collB` is `F` although it holds. If the rule on `ex:collB` is a prohibition, the request is permitted where it should be denied. The text is marked [D]; neither oracle can see it (the case format cannot hold world answers, `conformance/README.md` l.255).

Fix: a world-hierarchy question is a fact with a status; any entity on a chain with no answer makes the comparison `U` (#144's third option). `plan` becomes an optimisation, not a correctness obligation.

##### 4.5 Blocker for the port (cheap) — `request_param` cannot carry a set. **Verified.**

`request_param (name | value: Term)` (`due2-workflows.md:146`; schema `x-key: ["name"]`). The profiles admit set-valued request operands (`oval-list-right-operand/policy.ttl:35–40`, `due2:cardinality due2:set`), and at least 4 scenarios pass two values for one parameter (`oval-list-right-operand` ×2, `due2-list-part-and-class` ×2). They pass today only because clingo-i reads `case.json` directly. `evidence_param` has the same shape. Fix: key by `(name, value)` with a status, as `fact`/`fact_value` already are.

##### 4.6 Major — CI tiering is inverted; `main` has no green clingo-i run

`ways-of-working.md:210` decides a PR tier under 5 minutes and deterministic. The clingo-i job took 7.5 min (10-25), 11–16.5 min (10-27/28), and timed out at 20 min on `05a7049`; the same suite has varied 7.75–17.3 min with no code change. The differentials draw random seeds (`test_brute_force.py:84`). Docs-only commits (40%) still run SHACL and the clingo-i job. Measured locally (18 cores): 80 s wall, \~1,120 CPU-s; L11 ≈ 34%, spaces ≈ 31% (the `xone` space alone ≈ 22%), random differentials + enumeration ≈ 30%. The two L11 orders produce identical fact sets for all 502 vectors.

Fix (driver reviewer's plan, keeps every recorded catch — verified by them for the L11 channels): L11 one scenario per case, one order, skip the 3,953-line `force-20` policy; `xone` space limited to its first 1,200 inputs (every PR mutant it guards is exposed by input 1,128); differentials as explicit examples plus 1 × 100 fixed-seed draws; enumeration 1 × 50; full runs nightly; fail any PR test over 10 s; path filters for docs-only commits. Estimate: 4–5 min on a median runner.

##### 4.7 Minor — drift, verified instances

- `docs/design/due2-overview.md:149` says schema version `2.2`; it is `3.0` (`tools/gen_schema.py:32`).
- Issue #2 says "113" and "83" scenarios where `conformance/README.md` and the corpus say 122 and 92; it omits `due2-shared-nodes` from three lists.
- `spikes/clingo-i/scorecard.json` is at 444/485; `README.md:72` says 461/502.
- `§1` (l.42) and `§5.4` step 4 describe a fetch-after-W2 loop; `§3.3` (l.218) says "never looked up cannot reach W2".
- `correctness-strategy.md:115` claims L4/L5 tests on clingo-i that do not exist; `ways-of-working.md` [D] items (icontract, beartype, msgspec, Hypothesis profiles, mutmut, CrossHair, pip-audit) are used nowhere; the journal rule lapsed after 2026-10-18/21.

---

#### 5. Where the complexity comes from

##### 5.1 Exact completion — the largest generator, for 5 verdicts in 467. Major

**What it is.** §6.4's verdict is defined by invariance over completions of unknowns, made exact for correlated reads: two leaves that compare the same unresolved read are one variable (the *completion key*: scope, binding, concept reading, unit, right operands, and since 0050 the policy for hierarchy comparisons); complements share it with opposite polarity; opaque parts are their own variables; mixed variables are enumerated up to `max_mixed`; pivots name the unknown entries; the listed frontier is "routes that suffice" with `frontier_complete` by bounded enumeration.

**Cost.** §6.3–§6.4 is 3,423 of the spec's 19,548 words; records 0004, 0011, 0012, 0016, 0019, 0023, 0026, 0049 #3, 0050 #9; claims K, F, W, P each with an Alloy model; `tools/check_completion.py`; about 18 issues, 9 open. The key was patched four times (0012 → 0016 → 0023 → 0050 #9) and the newest component has no independent check (#153). Every new operand feature pays a "key tax", and an error in the key gives a *wrong definite verdict*. Constants change verdicts: in `due2-max-mixed`, k = 8 gives `Permit`, k = 9 `Indeterminate`.

**Measurement (verified).** Two variants of clingo-i on copies (`completion-experiment/`): V1 makes every unresolved leaf its own variable (one line of `completion.lp`); V2 makes every `U` part opaque, so each `U` finding is one independent variable — the spec's own fallback, which by claim M two folds compute exactly. Over the corpus (502 scenarios, 467 evaluated, 35 declined for recurrence), both variants change the same **5 verdicts and 1 range**:

| Scenario | Exact | Fallback |
|---|---|---|
| `due2-max-mixed` / nine flags unknown (k = 9) | Permit | Indeterminate (NotApplicable..Permit) — **what the corpus already expects** past the bound |
| `due2-max-mixed` / flag 1 true, eight unknown | Permit | Indeterminate (Pending..Permit) |
| `due2-unresolved-or-missing` / x unresolved | Permit | Indeterminate |
| `due2-unresolved-or-missing` / x has no fact | Permit | Indeterminate |
| `due2-xone-unknown` / EU-domiciled, US unknown, attestation on file | Permit | Indeterminate |
| `due2-xone-unknown` / … no attestation | range Pending..Permit | range NotApplicable..Permit |

No rl2, dprod, force, oval, or w3c scenario changes. Only 33 of 502 scenarios state an unresolved fact at all, 9 of them with a definite verdict (counted here). In the clingo-i journal of 2026-10-17, completion variables per vector were {0: 166, 1: 52, 2: 2, 3: 2}.

**Steelman.** `xone` and complementary rules ("home lending may read; everyone else must petition") are real idioms, and "Indeterminate exactly when the unknowns could change it" is the README's headline promise. *Rebuttal:* pairing covers only failed lookups (`unresolved`), so the result is approximate anyway (§6.4 *What stays approximate*, #25); the owner's own rule in 0016 — "If people want the policy to decide they might as well supply the data" — covers the loss; and the promise's "exactly" is relative to the spec's own syntactic key, which the oracle shares, so only Alloy found 0023's gap.

**From scratch.** Every `U` part is independent; verdict and range by two folds; unknown inputs reported with their statuses; routes = those of candidates ready or pending whatever the unknowns; `frontier_complete` iff no uncertain candidate. Only claim M remains; W3 reads only findings. If a real policy later needs correlated reads, add the key then, with that policy as the case.

##### 5.2 Cross-policy sharing — vestigial since 0050, still expensive. Major

The original choice (v0.1; Appendix "Why tuples": nested documents "fight the cross-policy fold") was one merged corpus in which a named rule two policies state is one atom (`decisions/0036`), with ids minted once and renamed at publish (`0038`) and an agreement precondition raising `IdentityConflict`. When one policy's edges turned another's `NotApplicable` into `Permit` (222 of 485 vectors failed L11 at `0928921`), `0050` made each policy its own data space — so every atom is now read per *entry* (atom, policy), with its own findings, instances, and activations.

- `0036:64` rejected per-policy copies because "a case would record two activations of one obligation" — exactly what `activation (atom_id, policy_id | at)` now does (verified). `0038:42` justified sharing because a shared duty is "instantiated once"; its own note now says "an instance in each".
- What sharing still buys: collapsing frontier routes "by duty id" — derivable from `(source_duty, binding)`, which clingo-i already uses.
- What it still costs: the agreement precondition and its unbuilt checker (#133, parked); `IdentityConflict` that depends on publish order; corpus ids that "depend on the store"; `policy_id` in 11 keys (schema 3.0); in clingo-i, a policy key in about 120 of 316 predicates and +2,060/−1,350 lines across #149–#157; and the leak of §4.1, which the keying is supposed to prevent.
- Coverage: the only multi-policy cases are 4 due2-native ones; §9 row 2 still waits for "a real multi-policy corpus".

**Steelman.** An offer, its agreement, and a regulator's prohibition evaluated together is a real shape, and one route for one duty two policies name is right. *Both survive policy-local corpora:* the fold already works per entry, and the collapse is derivable.

**From scratch.** Ids scoped per policy (deterministic from authored IRI and expansion selection — no minting, no renaming); each policy's W2 in its own data space by construction; prohibit-overrides across policies; routes merged by authored duty and binding; agreement as a publish-time lint. L11 then holds structurally.

##### 5.3 The flat DNF atom form — invisible to W3, and it carries the only exponential step. Major

W3 sees only whether some atom of a rule applies (`decisions/0016`, L9 point 3); duty DNF already gave way to clauses (`0028`); the `xone` expansion limit is still [O]; DNF needs minted disjunct ids and `negation` lineage and decides which unknown parts are named (§3.5), which clingo-i re-simulates over trees (`live/5`). L9 needs a second interpreter — and clingo-i already is one, over authored trees. The Appendix's reason for flat relations ("fight the cross-policy fold") lapsed when 0050 made the fold per policy.

**Steelman.** Flat conjunctions index and compile well (SQL, entitlements), and they feed policy diff (#15). *Rebuttal:* indexes key on rule-level fields, which survive; a compile step can come later, checked against the interpreter.

**From scratch.** W1 lifts, validates, binds, interiorises, and expands only action, target, and party; it emits the lifted tree (stage 1's form, today internal by `0037`). The evaluator reads constraint trees in Kleene logic. The lineage shrinks to a source map.

##### 5.4 The trace as the port. Major

The port has 56 relations and 183 fields (schema 3.0); the trace alone has 16 relations, byte-compared by L1 and replay. No engine emits any trace relation at relation level (#41 open; no vector file, #37 open); seven (`finding`, `basis`, `witness_basis`, `read`, `dominated`, `evaluation`, `diagnostic`) are produced or asserted nowhere, even as projections. Three of the four schema bumps in 37 hours changed fields no verdict depends on. Callers use the verdict, range, frontier, obligations, and unknown inputs.

**Steelman.** `decisions/0010`: an auditor must read the explanation without trusting or re-running an engine. *Rebuttal:* storing the same engine's explanation beside the Answer, with the engine version, meets that; a cross-engine byte contract is not needed for it.

**From scratch.** The normative port is an **Answer**: verdict, range, frontier, obligations, unknown inputs with statuses, determining rules (authored level, as the corpus already asserts). The explanation is emitted by the same engine, stored with its version, checked by L10 as a property test. Stay at schema 0.x until a consumer exists.

##### 5.5 The shell specified ahead of need. Major

Twelve records settle components that `due2-platform.md:3` itself calls "not a build order" (0008, 0030, 0038, 0039, 0040–0044, 0046–0048), ten of them on 2026-10-26; the ledger comes last in `correctness-strategy.md` §8. Several are the owner *removing* things (0045 no config, 0046 explicit calls) — but each removal cost a record and notes in others (0045 needed 7 notes and touched 168 files, 117 of them cases). From scratch: one sentence — `decide` is a pure function of pinned inputs — until the shell is built.

##### 5.6 The clingo program. Major, with an exemplary core

**Shape** (verified counts): 4,887 lines; **1,201 code**, 3,183 comment and doc-block, 503 blank. By role (ASP reviewer): IRI registries 254, RDF lift 68, W1 157, declines and rejections 186, key-only predicates 23, W2 290, completion 82, **W3 32**, explanation 83, integrity 26. `resolve.lp` (34 code lines) and `pivot.lp` (8) are exemplary; completion by one choice rule plus cautious and brave consequences is ASP used exactly right (41 variables, 2^41 completions: 2 cautious and 82 brave models, 0.16 s).

**The complexity is the stage boundary.** clingo-i does W1 inside the oracle (it is the L9 direct interpreter), and its corpus solves (1–3) re-derive every structural fact from the union of all texts' triples; locality is then restored by threading a policy key through \~120 of 316 predicates (292 of 957 rule heads), derived by hand in nine predicates (`space`, `node_space`, `cspace`, `node_tree`, `policy_text`, `policy_layer`, `edge`, `item_space`, `obligation_policy`) plus the text key on operands, `o(Iri, Text)`. Every defect of §4.1–§4.2 lives in that boundary. The four-solve choreography is a workaround, not semantics: on all 678 multi-text inputs built by the driver reviewer, solve 1 raised exactly the union of the per-text solve 0s; 99.1% of reply time is parse and ground.

**explain.lp** hand-writes a may/sure version of "in every completion" (`explain.lp:48–158`) instead of asking the solver, and is wrong once (§4.3). The listed frontier is still v0.33's (`explain.lp:164–169`, #103) and re-implements dominance.

**Patterns** (reported): `leaf_status` ≈ `witness_status`; `reaches` ≈ `ev_reaches`; `eqr` takes 14 rules and "fits" is defined four times; 19 projection rules pull keys out of finding terms; numeric datatypes listed in both `lift.lp` and `values.py`; `le_k` computes the full typed `partOf` closure per policy, unseeded (an 800-node chain with 4 policies: 3.3 s vs 0.55 s with 1); an undocumented decline (`structure.lp:459`, inherited attester).

**From scratch (ASP reviewer's first choice, driver reviewer's D1 — the two converged independently).** Two stages over an explicit normal form:

1. *Normalise*, one solve per text with `P` and `Text` fixed, no world: registries, lift, W1, declines and rejections. Emits `policy`, `root`, `atom`, `atom_party`, `edge`, `duty`, the constraint tree with the binding on each leaf, `atom_constraint`, and `closure(P, …)`.
2. Python: union of the relations, a generic agreement check (about 30 lines).
3. *Evaluate*, one grounding over the union: W2 keyed by entry, completion, W3, explanation from consequences, pivot. `resolve.lp` and `pivot.lp` carry over unchanged.

About 1,050 code lines, far less prose. It drops solve 1, `text_triple`, the derived keys, the text key, `_combine`, the may/sure layer, and the duplicates; fixes §4.1 by construction; and stage 3 *is* #41's relation-level face, so the Kotlin evaluator's oracle comes for free. If §5.1's simplification is taken, stage 3 shrinks further (no completion keys, no mixed enumeration).

##### 5.7 The driver and the tests. Major

The suite (7,187 lines, 2,663 fast-tier tests) is 1.5× the program. Inventory and verdicts (driver reviewer, spot-checked):

| Group | Caught real bugs? | Verdict |
|---|---|---|
| Corpus through the harness | Yes (`values.duration` on 86 vectors; missing evidence terms) | Keep |
| L11 locality (two generators) | Yes, as the gate for #152 and #157; missed #154 and §4.1 | Keep; sample in PR, full nightly; add policy-IRI annotations |
| Rule and duty differentials (Python oracles, \~300 and \~215 lines) | Yes, a few (#141's first cut; a bug in the oracle itself) | Keep examples + fixed seeds in PR |
| Bounded-exhaustive spaces (5,982 PR inputs) and mutants | No unplanted defect recorded | Trim `xone`; keep counts; mutants nightly |
| `test_interpret`, `test_duty` | Regression pins for #149–#157, all found by reviews | Keep |

Three Python models of §6.4 exist (`check_completion.py`, the oracle, `monotone_ranges`); `listed_frontier` is copied between them; `spaces.py` imports \~25 names from a test module. About 40 exact ASP substrings are pinned by mutants and deletions, \~27 of which #157 rewrote. Every leak bug since #149 was found by a review, not by a test.

##### 5.8 Process and verification. Major

- **Velocity beyond review.** 50 records (58.5k words, 1.7× the 34.6k-word spec), 14 on 2026-10-26; 0042 (14:05) superseded by 0045 (17:41) the same day; at least 12 decided items reversed or replaced within two days; 27 of 50 records not in force as written. 223 of 238 commits AI co-authored (verified), 0 pull requests. `CLAUDE.md` asks that "work by another model or agent" arrive as a pull request; whether that covers the main working session is ambiguous, but in effect no change has been reviewed before it landed.
- **Little executable work.** Word-level churn: 56% Markdown prose, 17% corpus, 20% code — and 73% of the ASP churn is comment lines, so about 15% is executable. 81% of commits touch a bookkeeping file; 40% change only Markdown.
- **Nine partial encodings of the semantics** (prose, corpus, clingo-i, brute-force oracle, `monotone_ranges`, `check_completion`, Alloy, `check_corpus`, SHACL, `import_force`'s matcher), six more planned before production. One change (`1726479`, no config) touched 168 files.
- **The common mode is the author.** One model family wrote the spec, the corpus, clingo-i, the oracles, and the Alloy models. 22 of the 27 issues labelled `bug` cite an outside, different-family review (verified by issue body); `references.md` records the lesson ("an independent reviewer with a different model family finds what the project's own oracles share a blind spot for"). Yet cross-model review is not in the process, and no external evaluator has ever been run against the corpus (OVAL is "read, never run").
- **Not converging.** Since the evaluator became Next #1 (`ef7410e`, 10-24): 82 commits, 25 records, schema 1.0 → 3.0, spec +30%, no relation-level vector. The newest finding pattern — a review control becomes a decision record, a schema major, a law, two cases, a 1,300-line clingo-i rewrite, a stale Alloy model, and a CI timeout within 13 hours (0050) — is the process working as designed.
- **Hand-kept duplicates drift** (§4.7): status in six places, history in five, coverage gaps in two (13 KB in the README, 17.9 KB in issue #2, 34 of 71 README commits edit it).

**Steelman.** Settling meaning in prose before code is cheaper than in code; the hand-derived corpus is the one oracle independent of all code, and 0050 changed none of its expectations; Alloy found real spec defects (K's scheme gap → 0023; P's fallback under `invalid`). All true — which is why §7 keeps the corpus and Alloy for M and drops the rest of the apparatus, not the other way round.

---

#### 6. What to keep

- Kleene logic with value statuses; "unknown is never false"; five verdicts; the range.
- The monotonicity proof and the two-folds computation — the best idea in the spec.
- Pending with routes, collapse, and dominance by inclusion.
- Bindings and profile layers as data; operand sources; units on the binding.
- The ODRL readings decided well: guards stay on the duty (0003), a void policy keeps its obligations and obligations never deny (0029, 0045), a verdict is the answer of the terms (0031), replaced policies and unknown profiles are rejected (0033), the action hierarchy is checked (0034), no config (0045).
- Pure `plan`/`decide` over content-addressed inputs; RDF outside W2/W3 (the 2026-10-27 review's point stands).
- The hand-derived corpus with `why`, including the 122-scenario authored-level explanation assertions.
- In clingo-i: `resolve.lp`, `pivot.lp`, `compare.lp`'s single algebra for every world, cautious/brave completion.
- Alloy for claim M (and K, if correlated completion is ever reinstated).

---

#### 7. If we started from scratch — alternatives, ranked by fit

##### A. Small core, policy-local, executable definition first (recommended)

```text
decide(policies, request, sotw) -> Answer            # pure; inputs by digest
  for each policy P, in P's own data space (P's corpus + P's profiles + the world):
    for each rule r of P (authored tree; expanded on action, target, party only):
      finding(r, P) := Kleene value of r's parts, each U part with (input, status)
    duties of P: owed, fulfilled from evidence, deadline status
  fold over (rule, P): P's conflict strategy; prohibit-overrides across policies;
    candidates; outstanding sets; collapse by (source_duty, binding); dominance
  lo := fold with every U at its most restrictive value
  hi := fold with every U at its most permissive value     # claim M: exact
  Answer := verdict (lo = hi, else Indeterminate [lo, hi]), frontier (pessimistic routes;
            complete iff no uncertain candidate), obligations, unknown inputs, determining rules
```

- **Envelope v1:** one or more policies, each evaluated locally; independent unknowns; absolute deadlines; recurrence and monitoring later; world hierarchy answers as facts with a status (open-world on unanswered chains); no ledger beyond "pin the inputs".
- **Process:** one spec of 10–15k words with inline rationale; decision records only for semantic forks forced by a failing case or a real policy; status and coverage generated from the corpus; a cross-model review per milestone with a fixed charter; a differential against an external evaluator on the two-valued, duty-free fragment with an allow-list of documented divergences; PR tier under 5 minutes, enforced.
- **Oracles:** the hand-derived corpus; one reference interpreter (the two-stage clingo program of §5.6, or a small Python one); Alloy for M.
- **Keeps** every goal and every element of §6. **Cuts** §5.1–§5.5. **Risks:** 5 synthetic verdicts become `Indeterminate`; `frontier_complete` is false more often; a later need for correlated reads reopens §5.1 — then with a real policy as its case.

##### B. Keep the architecture, prune what is vestigial (least disruptive)

Policy-local ids and corpora (cut sharing, renaming, agreement-as-precondition); the fallback as the semantics (or keep exactness but make bounds non-normative: any approximation must be sound and flagged); Answer port with the full trace internal; clingo-i to two stages; CI re-tiered; schema frozen at 3.x. **Keeps** the schema, the corpus, the Kotlin plan. **Risk:** DNF, lineage, and two evaluators to keep equal remain (§5.3).

##### C. Exact by solver (only if "exactly" is a hard product requirement)

Make supervaluation over typed value domains the definition, computed by clingo or SMT in production, which also closes #25. **Cuts** the syntactic key and its fallbacks. **Risks:** a solver on the hot path, JVM integration, latency at agent volume, scarce ASP skills.

##### D. Continue as is (not recommended)

"Done" is not observable: every review adds contract, every contract change fans out to nine encodings, and the evaluator recedes.

---

#### 8. Decisions for the owner, one at a time

In order of leverage; each is a fork with evidence above, and each would get one decision record.

1. **Exactness.** Keep exact correlated completion (status quo), or make every `U` part independent (the spec's fallback as the semantics). Evidence: §5.1 — 5 of 467 verdicts, all synthetic.
2. **Cross-policy identity.** Shared nodes with agreement and renaming (status quo), or policy-local corpora with collapse by authored duty. Evidence: §5.2.
3. **Normal form at the W1|W2 boundary.** DNF atoms (status quo), or the lifted tree. This shapes the Kotlin evaluator (#104) and clingo-i's restructuring. Evidence: §5.3, §5.6.
4. **The port.** The full trace byte-compared (status quo), or an Answer with the explanation beside it. Evidence: §5.4.
5. **World hierarchies.** Closed-world over planned fetches (status quo, unsound per #144), or answers as facts with a status. Evidence: §4.4.

Needs no decision (hygiene, small, independent of 1–5): fix `policy_text` and teach the L11 generator to annotate policy IRIs (§4.1); `defect/…` atoms instead of integrity constraints (§4.2); define `eliminated` under unknowns, then fix `explain.lp` (§4.3); widen the `request_param` key (§4.5); re-tier CI (§4.6); fix the drift of §4.7 and generate the counts.

---

#### 9. Where this review disagrees

- **With the 2026-10-27 outside review** ("retain the architecture … not a request for another architecture rewrite"). Agreed on the boundary: pure `plan`/`decide`, RDF outside W2/W3, relation-level qualification before interchangeability. Disagreed on what lies behind it: that review was defect-focused and scoped to the evaluator boundary; the costs here (§5) are not defects and were outside its charter.
- **Among this review's reviewers.** The process reviewer would retire the separate ASP oracle for a reference evaluator in the production language; the ASP reviewer would keep ASP for completion and restructure it. Both are right conditionally: if decision 1 keeps exactness, ASP is the right oracle (enumeration is what it is for); if decision 1 takes independent unknowns, the semantics is a deterministic fold, the oracle's case for ASP narrows to paradigm independence, and a small Python reference becomes competitive.
- **"No consumer."** The decision-history reviewer found no named consumer; `due2-platform.md` §4 plans migration from a predecessor (AIRDUE) and the next steps name an agent workload. The consumer is known but not wired: no producer or consumer exercises the port.
- **Severity of §4.4.** Rated Blocker for production; the project already tracks it (#144, open-decision). It is a known gap in decided text, not a discovery.

---

#### 10. Reproduction

All against `~/src/due2` at `05a7049`, using clingo-i's environment (`spikes/clingo-i/.venv`).

- `clingo-probes/` — `run.py` (the harness), `e1.py` (§4.3), `e3b.py` (§4.1), `e9.py` (§4.2), and the ASP reviewer's other probes (e2, e3, e3c, e4–e8, e10). Run as `cd clingo-probes && ~/src/due2/spikes/clingo-i/.venv/bin/python e3b.py`.
- `completion-experiment/` — `v1-each-leaf-own-variable.diff` and `v2-every-u-part-opaque.diff` against `spikes/clingo-i/lp/completion.lp`; `run.py VARIANT_ROOT OUT.jsonl` runs the whole corpus through a patched copy (`python -B -I`); `compare.py v1 v2` compares with `out-base.jsonl`. The outputs of the run used in §5.1 are included.

## Part 3

That review and mine largely agree, and its negation point checks out. It gives a concrete reason, beyond cost, not to keep DNF.

The negation gap, verified. Stage 2 pushes negation inward using complement operators (due2-profiles.md:175), but only eq, lt, lteq and isAnyOf have one. isA, isPartOf, hasPart and isAllOf have none, no diagnostic rejects their negation, and the corpus constraint relation has no polarity field. So dprod:not over an isPartOf, or an xone with such a member, can't be written into the corpus. clingo-i never meets this because it evaluates trees. Something has to be chosen either way:

- trees, where negation is just a node;
- a polarity field on the corpus's constraint links (atom_constraint, duty_constraint);
- a new rejection code.

Where we agree

- Fix the boundary, not the ASP. The kernel is good; the cost and every leak are in the contract and representation around it. Their count of 746 rules with bodies plus 248 facts matches my 1,201 code lines.
- Repair isolation first, and spend assurance effort on the seams between components before adding another verification layer.
- The overall order of work is the problem, not the local discipline.
- The same keep list: unknown ≠ false, pure evaluation, fulfilment from evidence, each policy in its own environment, RDF at the edge, the corpus, and clingo-i as an independent oracle.

One correction to my summary. Their vertical slice, widened in place, is the better practical form of my alternative A. "From scratch" should decide what the slice leaves out, not trigger a rewrite or a throwaway "lite" evaluator.

Where I'd still differ

1. When to decide on DNF. They defer it until the slice gives evidence; I'd decide before building it:
   - W1 stage 2 isn't written yet;
   - trees change no verdict (L9, and clingo-i already evaluates trees);
   - building the slice on DNF means first implementing the negation step that isn't closed.

   Cross-policy identity and exactness can wait for the slice. Its representative policies are exactly the evidence those decisions lack.
2. The trace in the slice. Keep byte-for-byte replay, which is cheap. But the slice should emit the Answer plus whatever trace relations it naturally produces, with "every reference resolves" (L10) as a property test. It shouldn't hand-derive all 16 relations first.

Merged sequence

| Step | What |
|---|---|
| 0. Needs no decision | Repair isolation, using both reviews' counterexamples as regression tests. The locality test generator must emit triples that name the other policy's IRIs and profile terms. Also fix integrity gaps by deriving defect atoms, define eliminated under unknowns, widen the request_param key, and re-tier CI. |
| 1. Decide | Normal form: authored trees, negation as a node, DNF only as an internal compile step. |
| 2. Build | The vertical slice: DPROD, a few representative policies (ideally the predecessor's real ones), real W1, the production-language evaluator, a frozen snapshot, Answer + trace with resolvable references, replay, a differential against clingo-i. Unsupported features are rejected or declined, and ids are local to each policy. |
| 3. Decide with the slice's evidence | Exactness, cross-policy identity, the Answer-vs-trace port split, and world hierarchies (#144). |

I added this comparison and the negation finding to the report as §11, and updated the memory note to the new order.

### due2 review: is it more complicated than it needs to be?

**Revision:** `05a7049` (2026-10-29 07:37 EDT), clean checkout. **Date:** 2026-10-29.
**Asked:** an adversarial review of design, workflow, plans, then code, especially the clingo program — and: if we started again from scratch, what would we do differently?
**Method:** six independent read-only reviews (semantics/spec; decision history; process and verification; the ASP program; the Python driver and tests; data model, schema, and corpus), each with a fixed charter, severity scale, and a required steelman per finding; then verification of every load-bearing claim by the coordinator. Experiments ran on copies under `/tmp`; the repository was not modified. Unpushed work on another machine is not covered.

Severity: **Blocker** — unsound, or wrong answers on admissible input. **Major** — accidental complexity or cost that keeps compounding. **Minor** — local.
"Verified" means re-run or re-read by the coordinator, not only reported by a reviewer.

---

#### 1. Conclusion

The unease is justified, and it is mostly not "ODRL is like that".

ODRL 2.2 is genuinely under-specified — no evaluation semantics, no source for operand values, unclear duty and conflict semantics — so a serious evaluator must decide a few dozen readings, and roughly a third of the 50 decision records are exactly that and look healthy. But most of the weight comes from five choices due2 made itself, each for a generality no real policy or consumer has yet demanded:

1. **Exact `Indeterminate`** over correlated literals (completion keys, mixed variables, `max_mixed`, pivots, routes that suffice, `frontier_complete`).
2. **One merged corpus with shared node identity** across policies — then, after it leaked, per-policy data spaces threaded back through every relation (`decisions/0036` → `0050`).
3. **A flat DNF atom form** with minted ids and a lineage collection, which W3 never needs to see.
4. **The full 16-relation trace as the byte-compared port**, ahead of any producer or consumer.
5. **The platform shell (ledger, sources, world edges, read limits) specified as relations** before any of it is built.

A process that turns every review finding into more contract — never into less — and that runs faster than one owner can weigh (14 decision records on 2026-10-26) did the rest.

Measured, not argued:

- Replacing exact completion with the spec's own sound fallback (every unknown independent; verdict and range by two folds) changes **5 of 467** evaluated verdicts, all `Permit → Indeterminate`, all in **3 due2-native cases built to exercise the layer**. **0 of 330** translated scenarios change. (§5.1)
- The cross-policy design is still leaking after this week's five fixes: one metadata triple about an offer, placed in the agreement's text, turns `NotApplicable` into `Permit` through the offer's rule (reproduced on `05a7049`, found independently by two reviewers). (§4.1)
- About 15% of all churn is executable code; 81% of commits touch bookkeeping; the evaluator has been "Next #1" since 2026-10-24 while the spec grew 30% and the schema went 1.0 → 3.0. (§5.8)

The good parts are real and worth keeping: Kleene logic with value statuses, the five verdicts with routes and dominance, the monotonicity argument that makes the verdict two folds, bindings as data, content-addressed pure evaluation, the hand-derived corpus with its `why`, and — in clingo-i — `resolve.lp`, `pivot.lp`, and the cautious/brave completion idea, which are exemplary ASP.

**Recommendation:** keep the boundary (`plan`/`decide`, RDF outside W2/W3) and the core semantics; cut the five generalities to a v1 envelope; fix the verified defects now; restructure clingo-i into two stages at the W1|W2 boundary; and start the evaluator against a frozen, small port. §7 gives the from-scratch alternatives ranked, §8 the decisions in the order to take them.

---

#### 2. Scope and limits

- Read: all of `docs/` (spec, design, decisions 0001–0050, correctness, briefings, archive), `spikes/clingo-i/` (14 `.lp` files, driver, tests), `tools/`, `tests/`, `schema/`, `conformance/` (format, sample cases, external triage), `formal/alloy/`, CI workflows, the 157 issues, git history, and the earlier reviews in `~/src/reviews/due2-2026-10-{24,25,27,28}/`.
- Ran: the full verify job and corpus locally (all green at `05a7049`; see the 2026-10-29 sync), the completion experiment over the whole corpus, and thirteen targeted clingo-i probes (`clingo-probes/`).
- Not covered: work not pushed from another machine; real organisational policies (none are in the repository); latency at production volume.

---

#### 3. What ODRL forces, and what due2 chose

| Concept | Forced by | Verdict |
|---|---|---|
| Kleene logic with value statuses (`missing`, `invalid`, `conflict`, `unresolved`, `misfit`) | Goal 1, "unknown is never false" | **Keep.** The differentiator. |
| Five verdicts, `verdict_range` | ODRL duties (Pending), goal 1 | **Keep.** The range is two folds. |
| Expanding action, target, party; compact-policy interiorisation | ODRL IM §2.7 | **Keep.** |
| Conflict strategies `perm`/`prohibit`/`invalid`; prohibit-overrides across policies | ODRL IM; one fixed cross-policy rule | **Keep.** |
| Duties as preconditions, fulfilled by evidence; guards vs witness conditions | ODRL IM §2.6, DPROD, RL2 | **Keep.** |
| Frontier: collapse by duty set, dominance by inclusion | due2's product (tell the requester what to do) | **Keep.** Elegant, cheap. |
| Bindings as data; profile layers; units; concept schemes | ODRL leaves operand sources undefined | **Keep**, mostly. Concept `eq` as ⊑ is a second meaning of `eq` (forced 0023). |
| Content-addressed inputs, pure `decide`, replay | Goal 3 | **Keep.** Cheap. |
| Literal completion keys, mixed/uniform, `max_mixed`, `exact` | Nothing; due2's precision goal | **Cut** (§5.1). |
| Pivotal literals | Nothing | **Cut** or offline tool. |
| Routes that suffice, `frontier_complete` by enumeration | Nothing | **Simplify** to pessimistic routes; complete iff no uncertain candidate (0004 option A). |
| Shared node identity, agreement precondition, publish renaming, entries | Nothing; only locality is needed | **Cut** to policy-local corpora (§5.2). |
| DNF of rule constraints, `xone` expansion, minted disjunct ids, lineage, L9 | W1's own rewrites | **Cut**: evaluate authored trees (§5.3). |
| 16-relation trace as byte-compared port; L10 per-witness rules | Goal 2 needs reasons, not this encoding | **Shrink** to an Answer; explanation beside it (§5.4). |
| `plan`/`Reads` (6 relations), world modules, `max_reads`, source combination, source versions | A closed-world hierarchy over limited fetches | **Defer**; make world hierarchy answers facts with a status (§4.4). |
| Ledger, cases, events, activations fed back from traces | Goal 3, platform | **Defer** to when the shell is built (one sentence now). |

Roughly 16 of the 50 decision records are ODRL readings and admission rules that look healthy (e.g. 0003, 0029, 0031, 0033, 0034, 0045); 34 descend wholly or partly from the five choices above (decision-history reviewer's count; spot-checked).

---

#### 4. Defects — fix regardless of any strategic choice

##### 4.1 Blocker — policy locality (L11) still leaks in clingo-i. **Verified.**

`lp/lift.lp:651`: `policy_text(P, Text) :- policy(P), text_triple(Text, P, _, _).` A text "states" policy `P` if it has *any* triple whose subject is `P`. Since `policy_text` feeds the per-policy hierarchy (`lift.lp:667`), any text that mentions `P` joins `P`'s data space.

Reproduction (`clingo-probes/e3b.py`): an offer `ex:offer` permits `odrl:use` of `ex:catalog`; an agreement (assignee `ex:bob`) states `ex:report1 odrl:partOf ex:catalog`. Alice asks for `ex:report1`:

| Agreement text | Reply |
|---|---|
| as above | `NotApplicable` (correct: the edge is the agreement's) |
| plus `ex:offer dprod:offerLifecycleStatus dprod:Accepted .` | **`Permit`**, basis `ex:read` — the offer's own rule |

The driver reviewer found the same root with `ex:p rdfs:comment "…"` (and a decline with `ex:p ex:relatedTo ex:q`). Sibling channels (ASP reviewer, reported): a stray `ex:p1 odrl:target ex:b` in another text adds a target to `p1`'s rule (e3c); `dct:isReplacedBy` in another text turns the whole vector into `ReplacedPolicy` (e10); a shared named rule described differently by two texts is silently merged where §4 requires `IdentityConflict` (e2, e8 — `_combine` compares only bindings and conflict strategies).

Why the tests miss it: the L11 generator (`tests/test_locality.py:50–68, 111–161`) never puts a triple about the vector's own policy into the second text; the brute-force differentials are single-policy.

Fix: minimal — a text states `P` only if it types `P` as a policy (or the driver supplies `text_policy` from each solve 0), and the generator annotates the vector's policy IRI. Structural — §5.6 (corpus solves never read `triple/3`).

##### 4.2 Major — integrity constraints do not catch partial gaps. **Verified.**

`integrity.lp:3–6` and `TESTS.md:11` promise that a deleted rule fails loudly. It does not when the gap affects only some items or some completions:

- Delete `node_space(Duty, P) :- duty_of(Y, Duty), space(Y, P).` (`constraint.lp`): a duty whose guard is false becomes owed — `Permit` becomes `Pending`, no error (`clingo-probes/e9.py`, re-run here). The `#min` over guard ranks (`duty.lp:204–205`) skips the guard with no rank.
- Delete the rule `DELETIONS` itself deletes (`completion.lp:389`) and use an input outside the test's own vector: `NotApplicable` where the intact program gives `Indeterminate` (driver reviewer, reported).

Fix: derive `defect/…` atoms instead of `:-` constraints and read them bravely; make guards and witness conditions part items so the one-value constraint covers them.

##### 4.3 Major — `eliminated` under unknowns states a reason that does not hold. **Verified.**

`clingo-probes/e1.py`: policy p1 (`perm`) has a `u` permission (`ex:x eq 5`, unresolved) and a `t` prohibition; policy p2 has a `t` permission. Reply: `Indeterminate`, `Deny..Permit`, and `eliminated: perm2 by forbid (prohibit-overrides)`. With `x = 5`, the prohibition is removed inside p1 and the verdict is `Permit` — `perm2` is not eliminated. `explain.lp:157–158` reads "not surely removed" as "survives", contradicting its own invariant (`explain.lp:12–15`: each row is a complete reason). The Python oracle copies the same approximation (`test_brute_force.py:605`), so nothing checks it independently. The spec (§3.5) does not define `eliminated` under unknowns: a spec gap first.

##### 4.4 Blocker for production — closed-world hierarchies over plan-limited fetches can fail open

`due2-workflows.md` §3.3 (l.174) reads world hierarchies closed-world: `a ⊑ b` is `U` only if an answer is `unresolved`, else `F`. `plan` (l.209–214) lists only the request's entities and the corpus's narrower values. Issue #144 (open) gives the counterexample: the policy states `ex:ds partOf ex:collA`, the catalog knows `ex:collA partOf ex:collB`, nobody asks about `ex:collA`, and `ex:ds ⊑ ex:collB` is `F` although it holds. If the rule on `ex:collB` is a prohibition, the request is permitted where it should be denied. The text is marked [D]; neither oracle can see it (the case format cannot hold world answers, `conformance/README.md` l.255).

Fix: a world-hierarchy question is a fact with a status; any entity on a chain with no answer makes the comparison `U` (#144's third option). `plan` becomes an optimisation, not a correctness obligation.

##### 4.5 Blocker for the port (cheap) — `request_param` cannot carry a set. **Verified.**

`request_param (name | value: Term)` (`due2-workflows.md:146`; schema `x-key: ["name"]`). The profiles admit set-valued request operands (`oval-list-right-operand/policy.ttl:35–40`, `due2:cardinality due2:set`), and at least 4 scenarios pass two values for one parameter (`oval-list-right-operand` ×2, `due2-list-part-and-class` ×2). They pass today only because clingo-i reads `case.json` directly. `evidence_param` has the same shape. Fix: key by `(name, value)` with a status, as `fact`/`fact_value` already are.

##### 4.6 Major — CI tiering is inverted; `main` has no green clingo-i run

`ways-of-working.md:210` decides a PR tier under 5 minutes and deterministic. The clingo-i job took 7.5 min (10-25), 11–16.5 min (10-27/28), and timed out at 20 min on `05a7049`; the same suite has varied 7.75–17.3 min with no code change. The differentials draw random seeds (`test_brute_force.py:84`). Docs-only commits (40%) still run SHACL and the clingo-i job. Measured locally (18 cores): 80 s wall, \~1,120 CPU-s; L11 ≈ 34%, spaces ≈ 31% (the `xone` space alone ≈ 22%), random differentials + enumeration ≈ 30%. The two L11 orders produce identical fact sets for all 502 vectors.

Fix (driver reviewer's plan, keeps every recorded catch — verified by them for the L11 channels): L11 one scenario per case, one order, skip the 3,953-line `force-20` policy; `xone` space limited to its first 1,200 inputs (every PR mutant it guards is exposed by input 1,128); differentials as explicit examples plus 1 × 100 fixed-seed draws; enumeration 1 × 50; full runs nightly; fail any PR test over 10 s; path filters for docs-only commits. Estimate: 4–5 min on a median runner.

##### 4.7 Minor — drift, verified instances

- `docs/design/due2-overview.md:149` says schema version `2.2`; it is `3.0` (`tools/gen_schema.py:32`).
- Issue #2 says "113" and "83" scenarios where `conformance/README.md` and the corpus say 122 and 92; it omits `due2-shared-nodes` from three lists.
- `spikes/clingo-i/scorecard.json` is at 444/485; `README.md:72` says 461/502.
- `§1` (l.42) and `§5.4` step 4 describe a fetch-after-W2 loop; `§3.3` (l.218) says "never looked up cannot reach W2".
- `correctness-strategy.md:115` claims L4/L5 tests on clingo-i that do not exist; `ways-of-working.md` [D] items (icontract, beartype, msgspec, Hypothesis profiles, mutmut, CrossHair, pip-audit) are used nowhere; the journal rule lapsed after 2026-10-18/21.

---

#### 5. Where the complexity comes from

##### 5.1 Exact completion — the largest generator, for 5 verdicts in 467. Major

**What it is.** §6.4's verdict is defined by invariance over completions of unknowns, made exact for correlated reads: two leaves that compare the same unresolved read are one variable (the *completion key*: scope, binding, concept reading, unit, right operands, and since 0050 the policy for hierarchy comparisons); complements share it with opposite polarity; opaque parts are their own variables; mixed variables are enumerated up to `max_mixed`; pivots name the unknown entries; the listed frontier is "routes that suffice" with `frontier_complete` by bounded enumeration.

**Cost.** §6.3–§6.4 is 3,423 of the spec's 19,548 words; records 0004, 0011, 0012, 0016, 0019, 0023, 0026, 0049 #3, 0050 #9; claims K, F, W, P each with an Alloy model; `tools/check_completion.py`; about 18 issues, 9 open. The key was patched four times (0012 → 0016 → 0023 → 0050 #9) and the newest component has no independent check (#153). Every new operand feature pays a "key tax", and an error in the key gives a *wrong definite verdict*. Constants change verdicts: in `due2-max-mixed`, k = 8 gives `Permit`, k = 9 `Indeterminate`.

**Measurement (verified).** Two variants of clingo-i on copies (`completion-experiment/`): V1 makes every unresolved leaf its own variable (one line of `completion.lp`); V2 makes every `U` part opaque, so each `U` finding is one independent variable — the spec's own fallback, which by claim M two folds compute exactly. Over the corpus (502 scenarios, 467 evaluated, 35 declined for recurrence), both variants change the same **5 verdicts and 1 range**:

| Scenario | Exact | Fallback |
|---|---|---|
| `due2-max-mixed` / nine flags unknown (k = 9) | Permit | Indeterminate (NotApplicable..Permit) — **what the corpus already expects** past the bound |
| `due2-max-mixed` / flag 1 true, eight unknown | Permit | Indeterminate (Pending..Permit) |
| `due2-unresolved-or-missing` / x unresolved | Permit | Indeterminate |
| `due2-unresolved-or-missing` / x has no fact | Permit | Indeterminate |
| `due2-xone-unknown` / EU-domiciled, US unknown, attestation on file | Permit | Indeterminate |
| `due2-xone-unknown` / … no attestation | range Pending..Permit | range NotApplicable..Permit |

No rl2, dprod, force, oval, or w3c scenario changes. Only 33 of 502 scenarios state an unresolved fact at all, 9 of them with a definite verdict (counted here). In the clingo-i journal of 2026-10-17, completion variables per vector were {0: 166, 1: 52, 2: 2, 3: 2}.

**Steelman.** `xone` and complementary rules ("home lending may read; everyone else must petition") are real idioms, and "Indeterminate exactly when the unknowns could change it" is the README's headline promise. *Rebuttal:* pairing covers only failed lookups (`unresolved`), so the result is approximate anyway (§6.4 *What stays approximate*, #25); the owner's own rule in 0016 — "If people want the policy to decide they might as well supply the data" — covers the loss; and the promise's "exactly" is relative to the spec's own syntactic key, which the oracle shares, so only Alloy found 0023's gap.

**From scratch.** Every `U` part is independent; verdict and range by two folds; unknown inputs reported with their statuses; routes = those of candidates ready or pending whatever the unknowns; `frontier_complete` iff no uncertain candidate. Only claim M remains; W3 reads only findings. If a real policy later needs correlated reads, add the key then, with that policy as the case.

##### 5.2 Cross-policy sharing — vestigial since 0050, still expensive. Major

The original choice (v0.1; Appendix "Why tuples": nested documents "fight the cross-policy fold") was one merged corpus in which a named rule two policies state is one atom (`decisions/0036`), with ids minted once and renamed at publish (`0038`) and an agreement precondition raising `IdentityConflict`. When one policy's edges turned another's `NotApplicable` into `Permit` (222 of 485 vectors failed L11 at `0928921`), `0050` made each policy its own data space — so every atom is now read per *entry* (atom, policy), with its own findings, instances, and activations.

- `0036:64` rejected per-policy copies because "a case would record two activations of one obligation" — exactly what `activation (atom_id, policy_id | at)` now does (verified). `0038:42` justified sharing because a shared duty is "instantiated once"; its own note now says "an instance in each".
- What sharing still buys: collapsing frontier routes "by duty id" — derivable from `(source_duty, binding)`, which clingo-i already uses.
- What it still costs: the agreement precondition and its unbuilt checker (#133, parked); `IdentityConflict` that depends on publish order; corpus ids that "depend on the store"; `policy_id` in 11 keys (schema 3.0); in clingo-i, a policy key in about 120 of 316 predicates and +2,060/−1,350 lines across #149–#157; and the leak of §4.1, which the keying is supposed to prevent.
- Coverage: the only multi-policy cases are 4 due2-native ones; §9 row 2 still waits for "a real multi-policy corpus".

**Steelman.** An offer, its agreement, and a regulator's prohibition evaluated together is a real shape, and one route for one duty two policies name is right. *Both survive policy-local corpora:* the fold already works per entry, and the collapse is derivable.

**From scratch.** Ids scoped per policy (deterministic from authored IRI and expansion selection — no minting, no renaming); each policy's W2 in its own data space by construction; prohibit-overrides across policies; routes merged by authored duty and binding; agreement as a publish-time lint. L11 then holds structurally.

##### 5.3 The flat DNF atom form — invisible to W3, and it carries the only exponential step. Major

W3 sees only whether some atom of a rule applies (`decisions/0016`, L9 point 3); duty DNF already gave way to clauses (`0028`); the `xone` expansion limit is still [O]; DNF needs minted disjunct ids and `negation` lineage and decides which unknown parts are named (§3.5), which clingo-i re-simulates over trees (`live/5`). L9 needs a second interpreter — and clingo-i already is one, over authored trees. The Appendix's reason for flat relations ("fight the cross-policy fold") lapsed when 0050 made the fold per policy.

**Steelman.** Flat conjunctions index and compile well (SQL, entitlements), and they feed policy diff (#15). *Rebuttal:* indexes key on rule-level fields, which survive; a compile step can come later, checked against the interpreter.

**From scratch.** W1 lifts, validates, binds, interiorises, and expands only action, target, and party; it emits the lifted tree (stage 1's form, today internal by `0037`). The evaluator reads constraint trees in Kleene logic. The lineage shrinks to a source map.

##### 5.4 The trace as the port. Major

The port has 56 relations and 183 fields (schema 3.0); the trace alone has 16 relations, byte-compared by L1 and replay. No engine emits any trace relation at relation level (#41 open; no vector file, #37 open); seven (`finding`, `basis`, `witness_basis`, `read`, `dominated`, `evaluation`, `diagnostic`) are produced or asserted nowhere, even as projections. Three of the four schema bumps in 37 hours changed fields no verdict depends on. Callers use the verdict, range, frontier, obligations, and unknown inputs.

**Steelman.** `decisions/0010`: an auditor must read the explanation without trusting or re-running an engine. *Rebuttal:* storing the same engine's explanation beside the Answer, with the engine version, meets that; a cross-engine byte contract is not needed for it.

**From scratch.** The normative port is an **Answer**: verdict, range, frontier, obligations, unknown inputs with statuses, determining rules (authored level, as the corpus already asserts). The explanation is emitted by the same engine, stored with its version, checked by L10 as a property test. Stay at schema 0.x until a consumer exists.

##### 5.5 The shell specified ahead of need. Major

Twelve records settle components that `due2-platform.md:3` itself calls "not a build order" (0008, 0030, 0038, 0039, 0040–0044, 0046–0048), ten of them on 2026-10-26; the ledger comes last in `correctness-strategy.md` §8. Several are the owner *removing* things (0045 no config, 0046 explicit calls) — but each removal cost a record and notes in others (0045 needed 7 notes and touched 168 files, 117 of them cases). From scratch: one sentence — `decide` is a pure function of pinned inputs — until the shell is built.

##### 5.6 The clingo program. Major, with an exemplary core

**Shape** (verified counts): 4,887 lines; **1,201 code**, 3,183 comment and doc-block, 503 blank. By role (ASP reviewer): IRI registries 254, RDF lift 68, W1 157, declines and rejections 186, key-only predicates 23, W2 290, completion 82, **W3 32**, explanation 83, integrity 26. `resolve.lp` (34 code lines) and `pivot.lp` (8) are exemplary; completion by one choice rule plus cautious and brave consequences is ASP used exactly right (41 variables, 2^41 completions: 2 cautious and 82 brave models, 0.16 s).

**The complexity is the stage boundary.** clingo-i does W1 inside the oracle (it is the L9 direct interpreter), and its corpus solves (1–3) re-derive every structural fact from the union of all texts' triples; locality is then restored by threading a policy key through \~120 of 316 predicates (292 of 957 rule heads), derived by hand in nine predicates (`space`, `node_space`, `cspace`, `node_tree`, `policy_text`, `policy_layer`, `edge`, `item_space`, `obligation_policy`) plus the text key on operands, `o(Iri, Text)`. Every defect of §4.1–§4.2 lives in that boundary. The four-solve choreography is a workaround, not semantics: on all 678 multi-text inputs built by the driver reviewer, solve 1 raised exactly the union of the per-text solve 0s; 99.1% of reply time is parse and ground.

**explain.lp** hand-writes a may/sure version of "in every completion" (`explain.lp:48–158`) instead of asking the solver, and is wrong once (§4.3). The listed frontier is still v0.33's (`explain.lp:164–169`, #103) and re-implements dominance.

**Patterns** (reported): `leaf_status` ≈ `witness_status`; `reaches` ≈ `ev_reaches`; `eqr` takes 14 rules and "fits" is defined four times; 19 projection rules pull keys out of finding terms; numeric datatypes listed in both `lift.lp` and `values.py`; `le_k` computes the full typed `partOf` closure per policy, unseeded (an 800-node chain with 4 policies: 3.3 s vs 0.55 s with 1); an undocumented decline (`structure.lp:459`, inherited attester).

**From scratch (ASP reviewer's first choice, driver reviewer's D1 — the two converged independently).** Two stages over an explicit normal form:

1. *Normalise*, one solve per text with `P` and `Text` fixed, no world: registries, lift, W1, declines and rejections. Emits `policy`, `root`, `atom`, `atom_party`, `edge`, `duty`, the constraint tree with the binding on each leaf, `atom_constraint`, and `closure(P, …)`.
2. Python: union of the relations, a generic agreement check (about 30 lines).
3. *Evaluate*, one grounding over the union: W2 keyed by entry, completion, W3, explanation from consequences, pivot. `resolve.lp` and `pivot.lp` carry over unchanged.

About 1,050 code lines, far less prose. It drops solve 1, `text_triple`, the derived keys, the text key, `_combine`, the may/sure layer, and the duplicates; fixes §4.1 by construction; and stage 3 *is* #41's relation-level face, so the Kotlin evaluator's oracle comes for free. If §5.1's simplification is taken, stage 3 shrinks further (no completion keys, no mixed enumeration).

##### 5.7 The driver and the tests. Major

The suite (7,187 lines, 2,663 fast-tier tests) is 1.5× the program. Inventory and verdicts (driver reviewer, spot-checked):

| Group | Caught real bugs? | Verdict |
|---|---|---|
| Corpus through the harness | Yes (`values.duration` on 86 vectors; missing evidence terms) | Keep |
| L11 locality (two generators) | Yes, as the gate for #152 and #157; missed #154 and §4.1 | Keep; sample in PR, full nightly; add policy-IRI annotations |
| Rule and duty differentials (Python oracles, \~300 and \~215 lines) | Yes, a few (#141's first cut; a bug in the oracle itself) | Keep examples + fixed seeds in PR |
| Bounded-exhaustive spaces (5,982 PR inputs) and mutants | No unplanted defect recorded | Trim `xone`; keep counts; mutants nightly |
| `test_interpret`, `test_duty` | Regression pins for #149–#157, all found by reviews | Keep |

Three Python models of §6.4 exist (`check_completion.py`, the oracle, `monotone_ranges`); `listed_frontier` is copied between them; `spaces.py` imports \~25 names from a test module. About 40 exact ASP substrings are pinned by mutants and deletions, \~27 of which #157 rewrote. Every leak bug since #149 was found by a review, not by a test.

##### 5.8 Process and verification. Major

- **Velocity beyond review.** 50 records (58.5k words, 1.7× the 34.6k-word spec), 14 on 2026-10-26; 0042 (14:05) superseded by 0045 (17:41) the same day; at least 12 decided items reversed or replaced within two days; 27 of 50 records not in force as written. 223 of 238 commits AI co-authored (verified), 0 pull requests. `CLAUDE.md` asks that "work by another model or agent" arrive as a pull request; whether that covers the main working session is ambiguous, but in effect no change has been reviewed before it landed.
- **Little executable work.** Word-level churn: 56% Markdown prose, 17% corpus, 20% code — and 73% of the ASP churn is comment lines, so about 15% is executable. 81% of commits touch a bookkeeping file; 40% change only Markdown.
- **Nine partial encodings of the semantics** (prose, corpus, clingo-i, brute-force oracle, `monotone_ranges`, `check_completion`, Alloy, `check_corpus`, SHACL, `import_force`'s matcher), six more planned before production. One change (`1726479`, no config) touched 168 files.
- **The common mode is the author.** One model family wrote the spec, the corpus, clingo-i, the oracles, and the Alloy models. 22 of the 27 issues labelled `bug` cite an outside, different-family review (verified by issue body); `references.md` records the lesson ("an independent reviewer with a different model family finds what the project's own oracles share a blind spot for"). Yet cross-model review is not in the process, and no external evaluator has ever been run against the corpus (OVAL is "read, never run").
- **Not converging.** Since the evaluator became Next #1 (`ef7410e`, 10-24): 82 commits, 25 records, schema 1.0 → 3.0, spec +30%, no relation-level vector. The newest finding pattern — a review control becomes a decision record, a schema major, a law, two cases, a 1,300-line clingo-i rewrite, a stale Alloy model, and a CI timeout within 13 hours (0050) — is the process working as designed.
- **Hand-kept duplicates drift** (§4.7): status in six places, history in five, coverage gaps in two (13 KB in the README, 17.9 KB in issue #2, 34 of 71 README commits edit it).

**Steelman.** Settling meaning in prose before code is cheaper than in code; the hand-derived corpus is the one oracle independent of all code, and 0050 changed none of its expectations; Alloy found real spec defects (K's scheme gap → 0023; P's fallback under `invalid`). All true — which is why §7 keeps the corpus and Alloy for M and drops the rest of the apparatus, not the other way round.

---

#### 6. What to keep

- Kleene logic with value statuses; "unknown is never false"; five verdicts; the range.
- The monotonicity proof and the two-folds computation — the best idea in the spec.
- Pending with routes, collapse, and dominance by inclusion.
- Bindings and profile layers as data; operand sources; units on the binding.
- The ODRL readings decided well: guards stay on the duty (0003), a void policy keeps its obligations and obligations never deny (0029, 0045), a verdict is the answer of the terms (0031), replaced policies and unknown profiles are rejected (0033), the action hierarchy is checked (0034), no config (0045).
- Pure `plan`/`decide` over content-addressed inputs; RDF outside W2/W3 (the 2026-10-27 review's point stands).
- The hand-derived corpus with `why`, including the 122-scenario authored-level explanation assertions.
- In clingo-i: `resolve.lp`, `pivot.lp`, `compare.lp`'s single algebra for every world, cautious/brave completion.
- Alloy for claim M (and K, if correlated completion is ever reinstated).

---

#### 7. If we started from scratch — alternatives, ranked by fit

##### A. Small core, policy-local, executable definition first (recommended)

```text
decide(policies, request, sotw) -> Answer            # pure; inputs by digest
  for each policy P, in P's own data space (P's corpus + P's profiles + the world):
    for each rule r of P (authored tree; expanded on action, target, party only):
      finding(r, P) := Kleene value of r's parts, each U part with (input, status)
    duties of P: owed, fulfilled from evidence, deadline status
  fold over (rule, P): P's conflict strategy; prohibit-overrides across policies;
    candidates; outstanding sets; collapse by (source_duty, binding); dominance
  lo := fold with every U at its most restrictive value
  hi := fold with every U at its most permissive value     # claim M: exact
  Answer := verdict (lo = hi, else Indeterminate [lo, hi]), frontier (pessimistic routes;
            complete iff no uncertain candidate), obligations, unknown inputs, determining rules
```

- **Envelope v1:** one or more policies, each evaluated locally; independent unknowns; absolute deadlines; recurrence and monitoring later; world hierarchy answers as facts with a status (open-world on unanswered chains); no ledger beyond "pin the inputs".
- **Process:** one spec of 10–15k words with inline rationale; decision records only for semantic forks forced by a failing case or a real policy; status and coverage generated from the corpus; a cross-model review per milestone with a fixed charter; a differential against an external evaluator on the two-valued, duty-free fragment with an allow-list of documented divergences; PR tier under 5 minutes, enforced.
- **Oracles:** the hand-derived corpus; one reference interpreter (the two-stage clingo program of §5.6, or a small Python one); Alloy for M.
- **Keeps** every goal and every element of §6. **Cuts** §5.1–§5.5. **Risks:** 5 synthetic verdicts become `Indeterminate`; `frontier_complete` is false more often; a later need for correlated reads reopens §5.1 — then with a real policy as its case.

##### B. Keep the architecture, prune what is vestigial (least disruptive)

Policy-local ids and corpora (cut sharing, renaming, agreement-as-precondition); the fallback as the semantics (or keep exactness but make bounds non-normative: any approximation must be sound and flagged); Answer port with the full trace internal; clingo-i to two stages; CI re-tiered; schema frozen at 3.x. **Keeps** the schema, the corpus, the Kotlin plan. **Risk:** DNF, lineage, and two evaluators to keep equal remain (§5.3).

##### C. Exact by solver (only if "exactly" is a hard product requirement)

Make supervaluation over typed value domains the definition, computed by clingo or SMT in production, which also closes #25. **Cuts** the syntactic key and its fallbacks. **Risks:** a solver on the hot path, JVM integration, latency at agent volume, scarce ASP skills.

##### D. Continue as is (not recommended)

"Done" is not observable: every review adds contract, every contract change fans out to nine encodings, and the evaluator recedes.

---

#### 8. Decisions for the owner, one at a time

In order of leverage; each is a fork with evidence above, and each would get one decision record.

1. **Exactness.** Keep exact correlated completion (status quo), or make every `U` part independent (the spec's fallback as the semantics). Evidence: §5.1 — 5 of 467 verdicts, all synthetic.
2. **Cross-policy identity.** Shared nodes with agreement and renaming (status quo), or policy-local corpora with collapse by authored duty. Evidence: §5.2.
3. **Normal form at the W1|W2 boundary.** DNF atoms (status quo), or the lifted tree. This shapes the Kotlin evaluator (#104) and clingo-i's restructuring. Evidence: §5.3, §5.6.
4. **The port.** The full trace byte-compared (status quo), or an Answer with the explanation beside it. Evidence: §5.4.
5. **World hierarchies.** Closed-world over planned fetches (status quo, unsound per #144), or answers as facts with a status. Evidence: §4.4.

Needs no decision (hygiene, small, independent of 1–5): fix `policy_text` and teach the L11 generator to annotate policy IRIs (§4.1); `defect/…` atoms instead of integrity constraints (§4.2); define `eliminated` under unknowns, then fix `explain.lp` (§4.3); widen the `request_param` key (§4.5); re-tier CI (§4.6); fix the drift of §4.7 and generate the counts.

---

#### 9. Where this review disagrees

- **With the 2026-10-27 outside review** ("retain the architecture … not a request for another architecture rewrite"). Agreed on the boundary: pure `plan`/`decide`, RDF outside W2/W3, relation-level qualification before interchangeability. Disagreed on what lies behind it: that review was defect-focused and scoped to the evaluator boundary; the costs here (§5) are not defects and were outside its charter.
- **Among this review's reviewers.** The process reviewer would retire the separate ASP oracle for a reference evaluator in the production language; the ASP reviewer would keep ASP for completion and restructure it. Both are right conditionally: if decision 1 keeps exactness, ASP is the right oracle (enumeration is what it is for); if decision 1 takes independent unknowns, the semantics is a deterministic fold, the oracle's case for ASP narrows to paradigm independence, and a small Python reference becomes competitive.
- **"No consumer."** The decision-history reviewer found no named consumer; `due2-platform.md` §4 plans migration from a predecessor (AIRDUE) and the next steps name an agent workload. The consumer is known but not wired: no producer or consumer exercises the port.
- **Severity of §4.4.** Rated Blocker for production; the project already tracks it (#144, open-decision). It is a known gap in decided text, not a discovery.

---

#### 10. Reproduction

All against `~/src/due2` at `05a7049`, using clingo-i's environment (`spikes/clingo-i/.venv`).

- `clingo-probes/` — `run.py` (the harness), `e1.py` (§4.3), `e3b.py` (§4.1), `e9.py` (§4.2), and the ASP reviewer's other probes (e2, e3, e3c, e4–e8, e10). Run as `cd clingo-probes && ~/src/due2/spikes/clingo-i/.venv/bin/python e3b.py`.
- `completion-experiment/` — `v1-each-leaf-own-variable.diff` and `v2-every-u-part-opaque.diff` against `spikes/clingo-i/lp/completion.lp`; `run.py VARIANT_ROOT OUT.jsonl` runs the whole corpus through a patched copy (`python -B -I`); `compare.py v1 v2` compares with `out-base.jsonl`. The outputs of the run used in §5.1 are included.

---

#### 11. Addendum (2026-10-29): the parallel review, reconciled

A parallel review of the same revision (shared with the coordinator after §1–§10 were written) recommends: repair profile isolation; settle the normal form's treatment of negation; deliver one narrow, production-shaped vertical slice; reconsider mandatory DNF and "global compiled-object reconciliation" with evidence from that slice; keep clingo-i as the independent oracle; do not throw away the corpus or start an evaluator from a blank page.

##### 11.1 New finding, verified: the DNF normal form is not closed under negation (Major)

`due2-profiles.md:175`: stage 2 pushes negation inward by De Morgan and by complement operators — `eq`↔`neq`, `lt`↔`gteq`, `lteq`↔`gt`, `isAnyOf`↔`isNoneOf` — and `not` over `xone` expands `xone` first. `isA`, `isPartOf`, `hasPart`, and `isAllOf` have no complement, no diagnostic rejects their negation, and `constraint` (`due2-workflows.md` §3.1) has no polarity field. So `dprod:not` over an `isPartOf`, or an `xone` with such a member (whose elimination negates members), has no representation in the corpus. clingo-i does not hit this because it evaluates trees. Fixes: trees as the normal form (negation is a node; nothing needs a complement), or a polarity on `atom_constraint`/`duty_constraint`, or a rejection code. One of the three has to be chosen in any case.

##### 11.2 Agreement

- The simplification target is the contract and representation around the ASP kernel, not its syntax (§5.6 here: `resolve.lp`, `pivot.lp`, completion are exemplary; the cost and every leak live at the stage boundary). The parallel review's count (746 rules with bodies, 248 facts) agrees with §5.6's 1,201 code lines.
- Repair isolation first; tiny boundary-crossing counterexamples matter more than deeper Boolean search; put assurance effort on the seams before adding a verification layer (§4.1, §4.2, §5.8).
- The programme sequence is the problem, not the local discipline: relation vectors, clingo-i's second face, and W2/W3 come before both W1 stages and the full-path gate (`correctness-strategy.md:252–262`). A vertical slice that is then widened, not a disposable "lite" evaluator beside it. This is a better operational form of §7 A than §7 itself gives: "from scratch" says what the slice leaves out, not that anything is rewritten.
- Keep: unknown ≠ false, pure evaluation over frozen inputs, evidence-derived fulfilment, policy-local environments and per-policy conflict, RDF at the authoring boundary, the hand-derived corpus, clingo-i as an independent oracle. Recurrence and monitoring outside the first slice; no revived bakeoff.

##### 11.3 Difference: when to decide

The parallel review defers DNF and cross-policy reconciliation until the slice gives evidence. This review would decide the normal form **before** the slice: W1 stage 2 is unwritten, trees change no verdict (L9; clingo-i already evaluates trees), and building the slice on DNF means first implementing the negation push-in that §11.1 shows is not closed — work that trees remove. Cross-policy identity and exactness can wait for the slice: its few representative policies (ideally the predecessor's real ones) are the evidence those decisions lack (§5.1 open question: does any real policy read an unresolvable fact both ways?).

A narrower difference: the parallel review puts "a complete trace with resolvable references" in the slice. Byte-for-byte replay is cheap and should be there; but the slice should emit the Answer plus the trace relations it naturally produces, with L10 as a property test, rather than first hand-deriving all 16 relations (§5.4).

##### 11.4 Merged sequence

0. **No decision needed:** isolation repair with both reviews' counterexamples as regression tests (the L11 generator must emit triples that name the other policy's IRIs and profile terms); `defect/…` atoms (§4.2); define `eliminated` under unknowns (§4.3); `request_param` key (§4.5); CI re-tier (§4.6).
1. **Decide:** the normal form — authored trees, negation as a node, DNF only as an internal compile step.
2. **Build:** the vertical slice — one profile (DPROD), a few representative policies, real W1 into the declared input, the evaluator in the production language, a frozen snapshot, Answer + trace with resolvable references, replay, differential against clingo-i; unsupported features rejected or declined explicitly; policy-local ids.
3. **Decide with the slice's evidence:** exactness (§5.1), cross-policy identity (§5.2), the port split (§5.4), world hierarchies (§4.4).
