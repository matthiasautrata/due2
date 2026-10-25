# 0034 — The ODRL layer checks the action hierarchy, and `odrl:hasPolicy` is rejected

**Status:** Decided, 2026-10-24 (the owner, on #117)
**Context documents:** `conformance/odrl22-conformance.md` · `conformance/odrl22-shape.ttl` · `odrl-compound-to-atomic-normalization.md` §3 · `due2-profiles.md` §5 · `due2-diagnostics.md` · `decisions/0020` · `decisions/0033` · `docs/briefings/due2-review-2026-10-24.md` R07 · issue #117

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

1. **Both layers check the action hierarchy.** An action other than `odrl:use` and `odrl:transfer` has exactly one `odrl:includedIn`, its value is an `odrl:Action`, and following `odrl:includedIn` from it reaches `odrl:use` or `odrl:transfer`. The edges are read from the policy, the core, the selected profile modules, and the ODRL vocabulary together, so an edge a policy states adds to the vocabulary's and never replaces it. W1 rejects a violation with the new stage-1 error `InvalidActionHierarchy`. Two kinds of action are exempt. The 21 actions that the ODRL vocabulary marks `owl:deprecated` have no `odrl:includedIn` there, so the rule cannot hold for them. A refined action is a blank node whose action is its `rdf:value` (IM §2.5.4), and that action is the one checked. A term that no vocabulary defines is not checked either: `UndeclaredProfile` rejects it already (`decisions/0020`).
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
