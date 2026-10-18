# due2 — Diagnostic Registry

**Status:** Draft v0.5 (2026-10-17)
**Companions:** `due2-workflows.md` (§3.1 `diagnostic`, §3.5, §4) · `odrl-compound-to-atomic-normalization.md` · `due2-profiles.md` · `conformance/README.md` (negative cases)

**Changes in v0.5** (2026-10-17, `decisions/0017`, #74): `MalformedConstraint` covers a logical constraint over the empty list. **v0.4** (2026-10-17, `decisions/0013` amendment, #69): `MalformedConstraint` covers an empty list as a set right operand. **v0.3** (2026-10-17, `decisions/0014`, `decisions/0015`): new rows `ConflictingProfileDeclaration` (named in profiles §2 since v0.4 but never registered), `RetypedOperand`, and `OperandRangeMismatch`; `InvalidBinding` and `OperatorTypeMismatch` cover concept schemes. **v0.2** (2026-10-17, `decisions/0013`, #64): `MalformedConstraint` covers more than one right-operand value on an operator that is not set-based, and a set right operand that mixes a list with other values or gives two lists.

Every diagnostic W1 can emit, in one table. Each row is defined in the section it cites; this registry gives the defining section a code and does not restate the rule. A rejection that a spec states without a code gets its code here.

## 1. Shape **[D]**

A diagnostic is `(code, severity, ref, message)`:

- **code** — a name from §3. A new rejection or warning lands as a spec edit in the defining section plus a row here, in the same commit.
- **severity** — `error` rejects the policy: W1 returns its diagnostics and no corpus, no lineage, no partial output (workflows §4). `warning` accepts it: the policy is normalised as written, and the warning is carried into the corpus (workflows §3.1 `diagnostic`) and from there into the trace of every case that evaluates the policy (workflows §3.5).
- **ref** — the node the diagnostic is about: the policy, rule, constraint, or asset/party node, by IRI or by its stage-1 skolem IRI. `RuleReferenceCycle` refs the cycle, every rule and edge in order (normalisation spec §6.3).
- **message** — free text for the author. Not compared by tests.

**Stage.** W1 reports every error of the first stage that has one, and no later stage runs. Stage 1 is the input profile, identity, and atomic expansion (normalisation spec); stage 2 is constraints, operand bindings, and duty timing (profiles; workflows §4). So the set of error codes for a rejected policy is deterministic, and a negative corpus case states it exactly (`conformance/README.md`).

**Not diagnostics.** The request-time part statuses `MissingValue`, `TypeMismatch`, and `MultipleValues` (profiles §3) are statuses of an evaluated part, not of a policy. They make the part `U` and appear in the trace's `basis`. A missing binding, by contrast, is an authoring error (`UnboundLeftOperand`), never a runtime unknown.

## 2. Checker coverage

`tools/check_corpus.py` emits these codes for the rows it checks, and resolves every code it emits against §3, so the checker cannot invent a code. Rows marked *unchecked* are W1 obligations the checker does not see: graph-level structure that rdflib erases on parse (named graphs, blank-node sharing), identity computed by stage 1, and limits.

## 3. Registry

| Code | Sev. | Stage | Condition | Defined in |
|---|---|---|---|---|
| `NoPolicy` | error | 1 | No node is typed as a Policy class or a declared subclass. | normalisation §3 |
| `MultiplePolicies` | error | 1 | More than one Policy node in one input. | normalisation §3 |
| `NamedGraph` | error | 1 | The input uses named graphs. *Unchecked.* | normalisation §3 |
| `RequestAsPolicy` | error | 1 | An `odrl:Request` is supplied as a policy. | profiles §8.1 |
| `MissingPolicyIdentity` | error | 1 | A blank-node Policy without an `odrl:uid`. | normalisation §3 |
| `MultipleUid` | error | 1 | A resource with more than one `odrl:uid`. | normalisation §5.1 |
| `IdentityConflict` | error | 1 | Distinct resources claim one effective identity. *Unchecked.* | normalisation §5.1 |
| `SharedAnonymousNode` | error | 1 | A blank node without a uid is the object of more than one triple. *Unchecked.* | normalisation §3 |
| `UnanchoredAnonymousNode` | error | 1 | A blank node reaches no IRI or uid-bearing anchor. *Unchecked.* | normalisation §3 |
| `UndeclaredProfile` | error | 1 | A DPROD or due2 core term used without declaring the profile by `odrl:profile`; or a term in a vocabulary position (an action, or a refined action's `rdf:value`, left operand, operator, function, relation, or conflict value) that is not an `odrl:` term of the ODRL vocabulary, a term of a selected profile's modules, or a term the policy types itself. A `cc:` term needs a profile. The second form is not raised when the policy declares a profile that has no due2 module. | ODRL IM §2.1; `odrl-compound-to-atomic-normalization.md` §3; `odrl22-conformance.md` §3 (`decisions/0020`) |
| `UnsupportedProfileTerm` | error | 1 | A profile term needs an extension point not on the list. *Unchecked.* | profiles §2 |
| `UnsupportedConstruct` | error | 1 | `odrl:inheritFrom`, `odrl:rightOperandReference`, `odrl:implies`, `odrl:source` outside a collection, or a collection `odrl:refinement`. The ref names the node, the message the term. | normalisation §3; profiles §8.1 |
| `UnsupportedConnective` | error | 1 | `odrl:andSequence`. | profiles §5 |
| `NoRule` | error | 1 | No `odrl:permission`, `odrl:prohibition`, or `odrl:obligation`. | normalisation §3 |
| `InvalidConflict` | error | 1 | More than one `odrl:conflict`, or a value other than `prohibit`, `perm`, `invalid`. | normalisation §3 |
| `MissingAction` | error | 1 | A rule with no action after interiorisation; a nested duty interiorises none. | normalisation §6.3 |
| `MissingTarget` | error | 1 | A Permission or Prohibition with no `odrl:target` after interiorisation. | normalisation §6.3 |
| `TargetAndOutput` | error | 1 | A rule with both `odrl:target` and `odrl:output`. | normalisation §6.3 |
| `InvalidNesting` | error | 1 | A Consequence with a Consequence, or a Remedy with a Consequence. *Unchecked.* | normalisation §6.3 |
| `RuleReferenceCycle` | error | 1 | A cycle of `duty`, `consequence`, `remedy` edges. | normalisation §6.3 |
| `LimitExceeded` | error | 1 | Input triples, generated rules, or generated policies over the invocation's limit. *Unchecked.* | normalisation §3 |
| `MalformedConstraint` | error | 2 | A constraint without exactly one `leftOperand` and one `operator`, or without a `rightOperand`; more than one `rightOperand` value on an operator that is not set-based; a set right operand that mixes a list with other values, gives two lists, or is the empty list; or a logical constraint with the empty list as an operand value. | ODRL IM §2.5.1, §2.5.2; profiles §4 (`decisions/0013` and its amendment), §5 (`decisions/0017`) |
| `UnsupportedOperator` | error | 2 | An operator outside the core registry. | profiles §4 |
| `UnboundLeftOperand` | error | 2 | A left operand with no single binding. | profiles §3 |
| `InvalidBinding` | error | 2 | A binding whose source is not one of the closed sources, whose property is not an IRI, or whose context property is not built in; or a `due2:conceptScheme` on an operand whose range is a datatype. | profiles §3, §4 |
| `ConflictingProfileDeclaration` | error | 2 | Two selected profile modules declare the same term differently. | profiles §2 |
| `RetypedOperand` | error | 2 | A layer above the one that owns an operand's type states a range, cardinality, or allowed operators different from the owner's. An attribute the owner omits counts as its default. | profiles §2 (`decisions/0014`) |
| `OperandRangeMismatch` | error | 2 | A binding whose range is of a different kind from the `rdfs:range` of the property it reads. | profiles §3 (`decisions/0014`) |
| `OperatorTypeMismatch` | error | 2 | An operator not allowed for the operand, a right operand not of its range's kind, or `isA` over a set-valued operand. On an operand with a concept scheme: an operator other than `eq`, `neq`, `isAnyOf`, `isNoneOf`, or an IRI right operand in none of its schemes by the memberships the policy and its profile modules declare. | profiles §3, §4 (`decisions/0015`) |
| `FloatingPointOperand` | error | 2 | An `xsd:float` or `xsd:double` right operand. | profiles §4 |
| `MixedDuration` | error | 2 | A duration mixing year-month and day-time components. | profiles §4 |
| `WitnessOutsideDuty` | error | 2 | A witness-source operand in a constraint that is not a duty's. | profiles §3 |
| `MixedDutyConstraint` | error | 2 | `or`, `xone`, or `not` combining a guard and a witness condition. | workflows §5.2 |
| `TimingOutsideDuty` | error | 2 | `dprod:deadline` or `dprod:recurrence` on a Policy, Permission, or Prohibition. | profiles §7 |
| `InvalidTiming` | error | 2 | More than one deadline or recurrence; a deadline that is not an `xsd:dateTime` or `xsd:duration`; a recurrence that is not an RRULE. | profiles §7 |
| `ContestedOperatorReading` | warning | 2 | `isPartOf`, `hasPart`, or `isA` with a list right operand, or `isPartOf`/`hasPart` over a set-valued operand: read after Salas–Pareti. | profiles §4; `decisions/0005` |
