# 0034 — The ODRL layer checks the action hierarchy, and `odrl:hasPolicy` is rejected

**Status:** Decided, 2026-10-24 (the owner, on #117); amended 2026-10-25 (the owner, on #122 and #123)
**Context documents:** `conformance/odrl22-conformance.md` · `conformance/odrl22-shape.ttl` · `odrl-compound-to-atomic-normalization.md` §3 · `due2-profiles.md` §5 · `due2-diagnostics.md` · `decisions/0020` · `decisions/0033` · `docs/briefings/due2-review-2026-10-24.md` R07 · `docs/briefings/due2-review-2026-10-25.md` F03, F04 · issues #117, #122, #123

## Question

due2 checks an input in two layers (`odrl22-conformance.md` §1). The ODRL 2.2 layer, `odrl22-shape.ttl` run by `tools/check_odrl22.py`, asks whether a policy is valid ODRL. The admission layer, `tools/check_corpus.py` and W1, asks whether due2 can evaluate it. The external review (R07) found five inputs that the layers got wrong:

| Input | ODRL IM | Before |
|---|---|---|
| An Agreement's assigner and assignee are the literals `"Alice"` and `"Bob"` | §2.3, §2.6: a party function's value is a Party | Both layers accepted it |
| One logical constraint has both `odrl:and` and `odrl:or` | §2.5.2: "exactly one" operand property | Both layers accepted it |
| An `odrl:eq` constraint has two `odrl:rightOperandReference` values | §2.5.1: one IRI, or a list for a set-based operator | The ODRL layer accepted it |
| A policy-defined action has no `odrl:includedIn` | §2.4: "An Action (except for use and transfer) MUST have one includedIn property value (of type Action)" | Both layers accepted it |
| An asset has `odrl:hasPolicy P`, and P's permission names no target | §2.2.3: the asset "MUST be inferred to be the target Asset of all the Rules of that Policy" | The ODRL layer rejected it |

The first four are invalid ODRL that the ODRL layer, or both layers, accepted. The last is valid ODRL that the ODRL layer called invalid.

The fourth reaches most of the corpus. 61 case policies define 91 actions of their own, as the RL2 and DPROD sources do, and give none of them an `odrl:includedIn`. Two more restate `odrl:display odrl:includedIn odrl:use`, although the ODRL vocabulary includes `odrl:display` in `odrl:play`, which gives `odrl:display` two values. And DPROD's own examples `baseline.ttl` and `odcs.ttl` define `ex:conformTo` with none.

## Decision

1. **Both layers check the action hierarchy.** An action other than `odrl:use` and `odrl:transfer` has exactly one `odrl:includedIn`, its value is an `odrl:Action`, and following `odrl:includedIn` from it reaches `odrl:use` or `odrl:transfer`. The edges are read from the policy, the core, the selected profile modules, and the ODRL vocabulary together, so an edge a policy states adds to the vocabulary's and never replaces it. W1 rejects a violation with the new stage-1 error `InvalidActionHierarchy`. Two kinds of action are exempt. The 21 actions that the ODRL vocabulary marks `owl:deprecated` have no `odrl:includedIn` there, so the rule cannot hold for them. A refined action is a blank node whose action is its `rdf:value` (IM §2.5.4), and that action is the one checked (amended 2026-10-25, below: any node with an `rdf:value`). A term that no vocabulary defines is not checked either: `UndeclaredProfile` rejects it already (`decisions/0020`).
2. **A literal is not an Asset or a Party.** The value of `odrl:target`, `odrl:output`, or a party function is a resource. W1 rejects a literal there with the new stage-1 error `LiteralEntity`.
3. **A logical constraint has one operand property.** W1 rejects two or more, counting `odrl:andSequence` and profile connectives such as `dprod:not`, with `MalformedConstraint`.
4. **The ODRL layer applies the right-operand-reference rule.** It rejects repeated `odrl:rightOperandReference` values on an operator that is not set-based, and a list together with another value, as it already did for `odrl:rightOperand` (`decisions/0013`). W1 needs no new check: it rejects every `odrl:rightOperandReference` with `UnsupportedConstruct` (`odrl-compound-to-atomic-normalization.md` §3).
5. **`odrl:hasPolicy` is valid ODRL that due2 rejects.** `tools/check_odrl22.py` applies the IM §2.2.3 inference before it validates, so the ODRL layer accepts the policy. W1 rejects a policy that an asset names with `odrl:hasPolicy`, with `UnsupportedConstruct`, also when its Rules name targets of their own.
6. **The corpus states the edge it lacked.** Each of the 91 actions that the 61 policies define is included in `odrl:use`, the broadest action, since no source says more. The two policies drop their restated `odrl:display` edge. DPROD's examples stay vendored unmodified: both checkers list them as expected to fail, with the reason, and the omission is reported upstream (EKGF/dprod#286).

## Why this holds

- **These are the IM's own MUSTs.** Both layers already reject other IM violations, such as a Permission with no target (IM §2.6.1). An odd rule is still a rule. Without IM §2.4, a policy author who prohibits `odrl:use` cannot tell whether that covers a custom action, because action matching reads the `odrl:includedIn` closure (`due2-workflows.md` §5.2).
- **The edge leaves every verdict as it was.** Matching asks whether the request's action is included in the rule's action. Including `ex:X` in `odrl:use` adds matches only for a rule on `odrl:use` itself, and only for requests for a custom action. Of the 61 policies, only `dprod-odcs-seller-contract` has a rule on `odrl:use`, and it gets requests for `odrl:read`, `odrl:modify`, `odrl:use`, and `odrl:distribute` only. Restated `odrl:display` edges changed nothing either: `odrl:display` reaches `odrl:use` through `odrl:play` without them.
- **A literal names no party.** A literal is not a resource, so it cannot be the Party that IM §2.3 requires. A rule whose assignee is `"Bob"` names no party a request could match, so its party part would never be T (`due2-workflows.md` §5.2). That is a silent error in the author's policy, not an unknown in the data.
- **W1 infers nothing beyond the declared edges.** `odrl-compound-to-atomic-normalization.md` §3 reads declared edges only. A target inferred from `odrl:hasPolicy` would be the one exception, and the exception points the wrong way: the asset is the subject and the policy the object, so the policy's own graph would no longer say what it governs. If W1 ignored the edge instead, it would drop a target the IM requires, which is an approximation that `due2-architecture.md` §1 rules out. Rejecting it costs the author one `odrl:target` triple.
- **Validity and admission stay separate** (`decisions/0033` item 4). The inverse form is valid ODRL, and the ODRL layer says so. Only W1 rejects it.

## Rejected

- **Leave IM §2.4 unchecked.** Both layers would keep accepting invalid ODRL, and the corpus would teach an implementer that a custom action needs no parent.
- **Include each corpus action in a closer parent.** The sources give none: the RL2 use cases and DPROD's examples define their actions with a label only. Inventing parents would change what the cases mean.
- **For R07's last row, infer the target in W1.** W1 would perform one inference, against the direction of the policy's own graph, as above.

## Consequences

- `due2-diagnostics.md` v0.11 adds `InvalidActionHierarchy` and `LiteralEntity`, adds `odrl:hasPolicy` to `UnsupportedConstruct`, and adds the second operand property to `MalformedConstraint`.
- `odrl-compound-to-atomic-normalization.md` 0.17 §3 states items 1, 2, and 5. Its profile version stays `1`, since no artifact has been produced under it.
- `due2-profiles.md` v0.18 §5 states item 3.
- `odrl22-shape.ttl` gains `ActionHierarchyShape`, `EntityValueShape`, the one-operand check on logical constraints, and the right-operand-reference check. `tools/check_odrl22.py` entails the `odrl:hasPolicy` target and lists the two DPROD examples as expected invalid. `tools/check_corpus.py` raises the new errors and lists the same two examples as expected to be rejected.
- Six negative cases pin the decision: `due2-literal-party`, `due2-and-or`, `due2-two-right-operand-references`, `due2-action-without-parent`, and `due2-action-two-parents` (all `odrl22_valid: false`), and `due2-has-policy` (valid ODRL).
- `odrl22-conformance.md` states which IM requirements the ODRL layer checks.

## Revisit when

- A source gives one of the corpus's custom actions a parent other than `odrl:use`.
- due2 admits inference beyond declared edges, for example a profile that states how its terms entail others.

## Amendment (2026-10-25, refined actions by structure; inverse parties)

### Question

The follow-up review found two gaps in this record (`docs/briefings/due2-review-2026-10-25.md` F03, F04).

**F03.** Item 1 says that a refined action is a blank node whose action is its `rdf:value`. IM §2.5.4 defines a refined action by its `rdf:value` and its refinements, not by its node kind, and the W3C CG's own formal-semantics examples C1 and C2 name the node `http://example.com/action/1`. A policy that names the node, or a tool that skolemises its blank nodes (RDF 1.1 Concepts §3.5), writes the same refined action with an IRI:

```turtle
ex:condition\/1 odrl:action ex:action\/1 .
ex:action\/1 rdf:value odrl:compensate ;
    odrl:refinement ex:refinement\/1 .
```

Both checkers read `rdf:value` only on a blank node. They took `ex:action/1` itself as the action: admission rejected it with `UndeclaredProfile`, and the ODRL layer with `UndeclaredProfile` and the class check. Typed `odrl:Action`, as in the review's input, it also failed the hierarchy check for want of an `odrl:includedIn`. The corpus hid the gap, because the translations `w3c-fs-c1` and `w3c-fs-c2` had replaced the CG's named node with a blank one and did not record the change. Stage 1 skolemises a refined-action node too (`odrl-compound-to-atomic-normalization.md` §5.1, case 3), so a policy it had skolemised, read again as input, would have failed the rule.

**F04.** IM §2.3.3 makes `odrl:assignerOf` and `odrl:assigneeOf` the party counterparts of `odrl:hasPolicy`. The ODRL vocabulary states the inference (`profiles/vendor/w3c/ODRL22.ttl`, the notes on both properties): the party "MUST be inferred to undertake the assignee functional role of all the Rules of that Policy", or the assigner role for `odrl:assignerOf`. Item 5 handled `odrl:hasPolicy` and not these two. The ODRL layer rejected an Agreement whose parties are stated only this way, for want of an assigner or an assignee (IM §2.1.3), although the IM supplies them. Admission accepted it, and W1 would have kept the edges as annotations (`odrl-compound-to-atomic-normalization.md` §3) and dropped the parties. A permission whose assignee is dropped matches every requester, because `due2-workflows.md` §5.2 builds a party part only for a party the atom names.

### Decision

1. **A refined action is recognised by its structure.** The action that a rule's `odrl:action` names is the node's `rdf:value` if it states one, and otherwise the node itself when it is an IRI. The node may be a blank node or an IRI, typed `odrl:Action` or not. Item 1's hierarchy check, and `decisions/0020`'s vocabulary check, apply to that action and never to the node of a refined action. A blank action node with no `rdf:value` names no action, so both layers reject it as an action without an `odrl:includedIn`: the ODRL layer by `ActionHierarchyShape`, and W1 with `InvalidActionHierarchy`.
2. **`odrl:assignerOf` and `odrl:assigneeOf` are treated as item 5 treats `odrl:hasPolicy`.** `tools/check_odrl22.py` applies the IM §2.3.3 inference before it validates: the party becomes the policy's assigner or assignee, which IM §2.7.1 shares with every Rule. W1 rejects a policy that a party names with either predicate, with `UnsupportedConstruct`.

### Why this holds

- **The IM defines a refined action by `rdf:value`.** IM §2.5.4 writes a refined action as an `rdf:value`, which names the action, and the refinements that narrow it. It says nothing of node kind, and the CG's examples name the node. The node is the narrowed use of `odrl:compensate`, not a new action term, so it has no place in the hierarchy, and giving it an `odrl:includedIn` would change what the policy says.
- **Skolemisation must not change validity.** Replacing a blank node with a skolem IRI leaves the graph's meaning unchanged (RDF 1.1 Concepts §3.5). A check that depends on node kind would accept a policy before skolemisation and reject it after, and stage 1 skolemises.
- **The structural rule is the one evaluators already need.** clingo-i reads an action term the same way: its `rdf:value` if it states one, otherwise the term itself if it is an IRI, and it declines a blank node without one (`spikes/clingo-i/lp/structure.lp`, `action_of/2`). An implementer writes one rule, with no special case for blank nodes.
- **Item 5's argument carries over to parties.** W1 infers nothing beyond the declared edges, and an inferred party would be the exception, read against the direction of the policy's graph. Ignoring the edge would drop a party the IM requires, and for an assignee it would widen the permission to every requester, which `due2-architecture.md` §1 rules out. Rejecting it costs the author one `odrl:assigner` or `odrl:assignee` triple.

### Rejected

- **Exempt every IRI action node with a refinement.** A refinement does not name the action, so a node with a refinement and no `rdf:value` would still name nothing.
- **Infer the parties in W1**, or keep the edges as annotations. The first is the inference item 5 rejected for targets. The second drops a party, as above.

### Consequences

- `conformance/odrl22-shape.ttl`: `ActionHierarchyShape` exempts a node with an `rdf:value` in place of every blank node. `tools/check_odrl22.py` reads `rdf:value` on any action node, types refined actions and blank action nodes `odrl:Action`, and entails the parties of `odrl:assignerOf` and `odrl:assigneeOf`. `tools/check_corpus.py` reads `rdf:value` on any action node, checks no refined-action node against the hierarchy, rejects a blank action node without `rdf:value`, and rejects both predicates.
- `odrl-compound-to-atomic-normalization.md` 0.19 §3 and `due2-diagnostics.md` v0.12 state the two items.
- `w3c-fs-c1` and `w3c-fs-c2` keep the CG's node names: the action, its refinement, and C2's constraint. Four new cases pin the change, and each fails under the checkers before it: `due2-refined-action-skolem`, a refined action named by a skolem IRI typed `odrl:Action`; `due2-action-without-value` (`odrl22_valid: false`); and `due2-assigner-of` and `due2-assignee-of` (valid ODRL, rejected by W1).

### Revisit when

- due2 admits inference beyond declared edges, as item 5's *Revisit when* says.
