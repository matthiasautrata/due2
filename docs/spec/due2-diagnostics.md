# due2 — Diagnostic Registry

**Status:** Draft v0.18 (2026-10-26)
**Companions:** `due2-workflows.md` (§3.1 `diagnostic`, §3.5, §4) · `odrl-compound-to-atomic-normalization.md` · `due2-profiles.md` · `conformance/README.md` (negative cases)

**Changes in v0.18** (2026-10-26, `decisions/0036` amendment, #132): `IdentityConflict` across policies is found when a policy is published, not when corpora are combined (§1). Earlier changes are in `docs/archive/changes.md`.

Every diagnostic W1 can emit, in one table, and the one the policy store emits when it publishes a policy's corpus (`IdentityConflict` across policies). Each row is defined in the section it cites; this registry gives the defining section a code and does not restate the rule. A rejection that a spec states without a code gets its code here.

## 1. Shape **[D]**

A diagnostic is `(code, severity, ref, message)`:

- **code** — a name from §3. A new rejection or warning lands as a spec edit in the defining section plus a row here, in the same commit.
- **severity** — `error` rejects the policy: W1 returns its diagnostics and no corpus, no lineage, no partial output (`due2-workflows.md` §4). `warning` accepts it: the policy is normalised as written, and the warning is carried into the corpus (`due2-workflows.md` §3.1 `diagnostic`) and from there into the trace of every case that evaluates the policy (`due2-workflows.md` §3.5).
- **ref** — the node the diagnostic is about: the policy, rule, constraint, or asset/party node, by IRI or by its stage-1 skolem IRI. `RuleReferenceCycle` refs the cycle, every rule and edge in order (`odrl-compound-to-atomic-normalization.md` §6.3), and a `MalformedConstraint` for a cycle of logical constraints refs every constraint on it in order (`due2-profiles.md` §5).
- **message** — free text for the author. Not compared by tests.

**Stage.** W1 reports every error of the first stage that has one, and no later stage runs. Stage 1 is the input profile, identity, and atomic expansion (`odrl-compound-to-atomic-normalization.md`); stage 2 is constraints, operand bindings, and duty timing (`due2-profiles.md`; `due2-workflows.md` §4). *Publish* follows stage 2 and is not part of W1: the policy store compares a policy that both stages accept with the published policies when it is asked to publish its corpus (`put_corpus`, `due2-platform.md` §2.3), and its one error is `IdentityConflict` (`due2-workflows.md` §4, *Several policies are one corpus*). Evaluation never meets it. So the set of error codes for a rejected policy is deterministic, and a negative corpus case states it exactly (`conformance/README.md`).

**Not diagnostics.** The request-time part statuses `MissingValue`, `TypeMismatch`, and `MultipleValues` (`due2-profiles.md` §3) are statuses of an evaluated part, not of a policy. They make the part `U` and appear in the trace's `basis`. A missing binding, by contrast, is an authoring error (`UnboundLeftOperand`), never a runtime unknown.

## 2. Checker coverage

`tools/check_corpus.py` emits these codes for the rows it checks, and resolves every code it emits against §3, so the checker cannot invent a code. Rows marked *unchecked* are W1 obligations the checker does not see: graph-level structure that rdflib erases on parse (named graphs, blank-node sharing), identity computed by stage 1, and limits.

## 3. Registry

| Code | Sev. | Stage | Condition | Defined in |
|---|---|---|---|---|
| `NoPolicy` | error | 1 | No node is typed as a Policy class or a declared subclass. | `odrl-compound-to-atomic-normalization.md` §3 |
| `MultiplePolicies` | error | 1 | More than one Policy node in one input. | `odrl-compound-to-atomic-normalization.md` §3 |
| `NamedGraph` | error | 1 | The input uses named graphs. *Unchecked.* | `odrl-compound-to-atomic-normalization.md` §3 |
| `RequestAsPolicy` | error | 1 | An `odrl:Request` is supplied as a policy. | `due2-profiles.md` §8.1 |
| `ReplacedPolicy` | error | 1 | The Policy has `dct:isReplacedBy`: it is void, and its replacement is the policy to process. | ODRL IM §2.8; `odrl-compound-to-atomic-normalization.md` §3 (`decisions/0033`) |
| `MissingPolicyIdentity` | error | 1 | A blank-node Policy without an `odrl:uid`. | `odrl-compound-to-atomic-normalization.md` §3 |
| `MultipleUid` | error | 1 | A resource with more than one `odrl:uid`. | `odrl-compound-to-atomic-normalization.md` §5.1 |
| `IdentityConflict` | error | 1, publish | Distinct resources claim one effective identity. Within one policy, stage 1 finds it. Across policies, publishing finds it: the policy's corpus says something different of a node that a published policy's corpus holds, and the ref is the node (`due2-workflows.md` §4, *Several policies are one corpus*). *Unchecked.* | `odrl-compound-to-atomic-normalization.md` §5.1; `due2-workflows.md` §4 |
| `SharedAnonymousNode` | error | 1 | A blank node without a uid is the object of more than one triple. *Unchecked.* | `odrl-compound-to-atomic-normalization.md` §3 |
| `UnanchoredAnonymousNode` | error | 1 | A blank node reaches no IRI or uid-bearing anchor. *Unchecked.* | `odrl-compound-to-atomic-normalization.md` §3 |
| `UndeclaredProfile` | error | 1 | A DPROD or due2 core term used without declaring the profile by `odrl:profile`; or a term in a vocabulary position (an action, or a refined action's `rdf:value`, left operand, operator, function, relation, or conflict value) that is not an `odrl:` term of the ODRL vocabulary, a term of a selected profile's modules, or a term the policy types itself. A `cc:` term needs a profile. The second form is not raised when the policy declares a profile that has no due2 module, which is rejected with `UnrecognisedProfile` instead. | ODRL IM §2.1; `odrl-compound-to-atomic-normalization.md` §3; `conformance/odrl22-conformance.md` §3 (`decisions/0020`) |
| `UnrecognisedProfile` | error | 1 | The Policy declares, by `odrl:profile`, a profile that due2 has no module for. The ref names the Policy, the message the profile. | ODRL IM §3.2; `odrl-compound-to-atomic-normalization.md` §3; `due2-profiles.md` §2 (`decisions/0033`) |
| `InvalidActionHierarchy` | error | 1 | An action other than `odrl:use` and `odrl:transfer` that has no `odrl:includedIn` or more than one, has one that is not an `odrl:Action`, or whose `odrl:includedIn` path reaches neither `odrl:use` nor `odrl:transfer`; and a blank action node without `rdf:value`, which names no action. Which actions are checked, from which graphs, and the exemptions: `odrl-compound-to-atomic-normalization.md` §3. | ODRL IM §2.4; `odrl-compound-to-atomic-normalization.md` §3 (`decisions/0034`) |
| `UnsupportedProfileTerm` | error | 1 | A profile term needs an extension point not on the list. *Unchecked.* | `due2-profiles.md` §2 |
| `UnsupportedConstruct` | error | 1 | `odrl:inheritFrom`, `odrl:rightOperandReference`, `odrl:implies`, `odrl:hasPolicy`, `odrl:assignerOf`, `odrl:assigneeOf`, `odrl:source` outside a collection, a collection `odrl:refinement`, or an `odrl:constraint` on the Policy. The ref names the node, the message the term. | `odrl-compound-to-atomic-normalization.md` §3; `due2-profiles.md` §8.1 |
| `UnsupportedConnective` | error | 1 | `odrl:andSequence`. | `due2-profiles.md` §5 |
| `NoRule` | error | 1 | No `odrl:permission`, `odrl:prohibition`, or `odrl:obligation`. | `odrl-compound-to-atomic-normalization.md` §3 |
| `InvalidConflict` | error | 1 | More than one `odrl:conflict`, or a value other than `prohibit`, `perm`, `invalid`. | `odrl-compound-to-atomic-normalization.md` §3 |
| `MissingAction` | error | 1 | A rule with no action after interiorisation; a nested duty interiorises none. | `odrl-compound-to-atomic-normalization.md` §6.3 |
| `MissingTarget` | error | 1 | A Permission or Prohibition with no `odrl:target` after interiorisation. | `odrl-compound-to-atomic-normalization.md` §6.3 |
| `TargetAndOutput` | error | 1 | A rule with both `odrl:target` and `odrl:output`. | `odrl-compound-to-atomic-normalization.md` §6.3 |
| `LiteralEntity` | error | 1 | A literal as the value of `odrl:function`, `odrl:relation`, or any of their `rdfs:subPropertyOf` descendants, such as `odrl:target`, `odrl:assignee`, or `dprod:subjectOfDuty`: an Asset and a Party are resources. The ref names the node that has the property, the message the property and the literal. | ODRL IM §2.2, §2.3, §2.6; `odrl-compound-to-atomic-normalization.md` §3 (`decisions/0034`) |
| `MisplacedConstraint` | error | 1 | An `odrl:refinement` on anything other than an Action or a collection, or an `odrl:constraint` on anything other than a Policy or a Rule. A refinement on an Asset or a Party, and a constraint on the Policy itself, are `UnsupportedConstruct` instead. The ref names the node, the message the property. | `odrl-compound-to-atomic-normalization.md` §3 |
| `InvalidNesting` | error | 1 | A Rule edge outside its subject: `odrl:permission`, `odrl:prohibition`, or `odrl:obligation` not on the Policy, `odrl:duty` not on a Permission, `odrl:remedy` not on a Prohibition, `odrl:consequence` not on a Duty that `odrl:duty` or `odrl:obligation` references (so not on a Consequence or a Remedy); or a node in two Rule classes. | `odrl-compound-to-atomic-normalization.md` §3, §6.3 |
| `RuleReferenceCycle` | error | 1 | A cycle of `duty`, `consequence`, `remedy` edges. | `odrl-compound-to-atomic-normalization.md` §6.3 |
| `LimitExceeded` | error | 1 | Input triples, generated rules, or generated policies over the invocation's limit. *Unchecked.* | `odrl-compound-to-atomic-normalization.md` §3 |
| `AnonymousEntity` | warning | 1 | A blank-node target or assignee with no `odrl:uid` and no refinement: no request can name it, so its Rule is never `T`, and `U` on a request without a target or assignee. Also raised when the Rule names other targets. The ref names the node and its Rule. | `odrl-compound-to-atomic-normalization.md` §3 |
| `MalformedConstraint` | error | 2 | A constraint without exactly one `leftOperand` and one `operator`, or without a `rightOperand`; more than one `rightOperand` value on an operator that is not set-based; a set right operand that mixes a list with other values, gives two lists, or is the empty list; a logical constraint with more than one operand property, or with the empty list as an operand value, or whose list names one node twice; logical constraints whose members form a cycle; or an `odrl:xone` with two members, neither a logical constraint, that have the same left operand, operator, unit, and right operand values. | ODRL IM §2.5.1, §2.5.2; `due2-profiles.md` §4 (`decisions/0013` and its amendment), §5 (`decisions/0017`, `decisions/0022`) |
| `UnsupportedOperator` | error | 2 | An operator outside the core registry. | `due2-profiles.md` §4 |
| `UnboundLeftOperand` | error | 2 | A left operand with no single binding. | `due2-profiles.md` §3 |
| `InvalidBinding` | error | 2 | A binding whose source is not one of the closed sources, whose property is not an IRI, or whose context property is not built in; or a `due2:conceptScheme` on an operand whose range is a datatype. | `due2-profiles.md` §3, §4 |
| `ConflictingProfileDeclaration` | error | 2 | Two selected profile modules declare the same term differently. | `due2-profiles.md` §2 |
| `RetypedOperand` | error | 2 | A layer above the one that owns an operand's type states a range, cardinality, or allowed operators different from the owner's. An attribute the owner omits counts as its default. | `due2-profiles.md` §2 (`decisions/0014`) |
| `OperandRangeMismatch` | error | 2 | A binding whose range is of a different kind from the `rdfs:range` of the property it reads. | `due2-profiles.md` §3 (`decisions/0014`) |
| `OperatorTypeMismatch` | error | 2 | An operator not allowed for the operand; a right operand not of its range's kind; a `dateTime`, `date`, or `duration` right operand whose lexical form names no value of its datatype (XSD 1.1 Part 2 §3.3); a `dateTime` right operand without a timezone; a `date` right operand with a timezone; an operator of one left value (`eq`, `neq`, `lt`, `lteq`, `gt`, `gteq`, `isAnyOf`, `isNoneOf`, `isA`) over a set-valued operand. On an operand with a concept scheme: an operator other than `eq`, `neq`, `isAnyOf`, `isNoneOf`, or an IRI right operand in none of its schemes by the memberships the policy and its profile modules declare. | `due2-profiles.md` §3, §4 (`decisions/0015`, `decisions/0024`, `decisions/0025`) |
| `FloatingPointOperand` | error | 2 | An `xsd:float` or `xsd:double` right operand. | `due2-profiles.md` §4 |
| `MixedDuration` | error | 2 | A duration mixing year-month and day-time components. | `due2-profiles.md` §4 |
| `WitnessOutsideDuty` | error | 2 | A witness-source operand in a constraint that is not a duty's. | `due2-profiles.md` §3 |
| `MixedDutyConstraint` | error | 2 | `or`, `xone`, or `not` combining a guard and a witness condition. | `due2-workflows.md` §5.2 |
| `TimingOutsideDuty` | error | 2 | `dprod:deadline` or `dprod:recurrence` on a Policy, Permission, or Prohibition. | `due2-profiles.md` §7 |
| `InvalidTiming` | error | 2 | More than one deadline or recurrence; a deadline that is not an `xsd:dateTime` with a timezone or an `xsd:duration`, or whose lexical form names no value of its datatype; a recurrence that is not an RRULE. | `due2-profiles.md` §7 (`decisions/0024`) |
| `ContestedOperatorReading` | warning | 2 | `isPartOf`, `hasPart`, or `isA` with a list right operand, or `isPartOf`/`hasPart` over a set-valued operand: read after Salas–Pareti. | `due2-profiles.md` §4; `decisions/0005` |
