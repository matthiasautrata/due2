# ODRL 2.2 conformance — log of results and corrections

This file keeps the dated results and corrections that `conformance/odrl22-conformance.md` carried until 2026-10-26, moved here verbatim. The current protocol, the checks it led to, and the latest results are in that document, which holds where the two differ. Section numbers below are those of the document at the time.

## From §2: corrections to the shape

**Erratum (2026-10-11).** Until then this section called the set-based operators unenumerated and the shape admitted lists only for `isAnyOf`, `isNoneOf`, and `isAllOf`, `due2-profiles.md` §4's reading at the time. That was wrong: the Vocabulary enumerates them, and the shape rejected valid ODRL 2.2. Shape and `due2-profiles.md` §4 are fixed. What a list *means* for `isPartOf`, `hasPart`, and `isA` is a separate question that ODRL does not answer and the published semantics answer differently; due2 adopts Salas and Pareti et al.'s reading and warns (`ContestedOperatorReading`) wherever it applies (`decisions/0005`). `isPartOf` with a list is tested by `oval-list-right-operand`.

**Repeated values (2026-10-17).** Many authors write a set right operand as repeated values, `odrl:rightOperand ex:a, ex:b`, not as one list. IM §2.5.1 gives a Constraint "one rightOperand property value", but Vocabulary §5.1 makes the list a SHOULD ("the rdf:List predicate SHOULD be used"), and the ODRL JSON-LD context maps `rightOperand` without `@container: @list`, so a JSON array expands to repeated values. The shape accepts them on the six set-based operators, and rejects repeated values on any other operator and a list together with any other value (`decisions/0013`). Until then it accepted every repeated form silently, `eq ex:a, ex:b` included. `due2-repeated-right-operand` tests the accepted form and `due2-malformed-right-operand` the rejected ones.

**Anonymous targets (2026-10-18).** The shape required an IRI target on every Permission, Prohibition, and Duty. IM §2.6.1 asks for a target "of type Asset", and IM §2.2 says an Asset SHOULD have a uid, so an anonymous target is valid ODRL 2.2. The shape now admits a blank node there. due2 admits it with the `AnonymousEntity` warning, because no request can name it (`odrl-compound-to-atomic-normalization.md` §3, #79). `due2-anonymous-target` tests it.

## 3. Results (2026-10-10)

```text
python3 tools/check_odrl22.py --all
70 checked, 0 failing        # 66 corpus policies + 4 vendored DPROD files
```

Zero structural ODRL 2.2 violations across the whole corpus and DPROD's own examples. `check_corpus.py` stays green (66 checked, 0 failing; the 16 vendored DPROD policies separately: 0 failing).

The review found and fixed one real blemish, plus one hygiene gap:

1. **37 corpus policies used DPROD- or due2-vocabulary terms without declaring `odrl:profile`** (IM §2.1: use only Core terms, or declare the profiles whose terms you use — and "the profile property MUST be used to indicate the IRIs"). All 37 now declare `<https://ekgf.org/dprod/spec/develop/>` and/or `<https://w3id.org/due2/profile#>`. This is not cosmetic: normalisation selects a profile's binding module by `odrl:profile` (`odrl-compound-to-atomic-normalization.md` §3), so an undeclared namespace would silently lose its bindings.
2. **`check_corpus.py` now rejects undeclared namespaces** as a W1 input error, and `check_odrl22.py` checks the same rule against the IM, so the corpus cannot regress. Note the distinction recorded in `conformance/README.md`: *classification* (which due2 extension points a case needs) is separate from *declaration* (which vocabulary namespaces appear in the policy). A case can classify `odrl-core` and still need the DPROD profile declaration, because operand bindings are DPROD-vocabulary terms.
3. **Both checkers checked IM §2.1 only for the DPROD and due2 namespaces (2026-10-18, #78).** A term from any other namespace passed with no profile, as the 347 DALICC licenses did with their `dalicc:` actions (`docs/design/references.md`, DALICC). Both now check every term in a vocabulary position: an action, left operand, operator, function, relation, or conflict value must be an `odrl:` term of the ODRL vocabulary, a term of a declared profile's modules, or a term the policy types itself (`decisions/0020`). This departs from the IM's letter in two ways. Common Vocabulary terms such as `odrl:purpose` need no profile, as in the W3C's own examples. And a term the policy types itself needs none, as in the `rl2-*` cases. It is stricter than `profiles/vendor/w3c/ODRL22.ttl` in one: the file's nine `cc:` actions need a profile (`decisions/0020` #4). `check_odrl22.py` also typed every IRI action as an `odrl:Action`, so IM §2.5.4's class check on actions could not fail; it now types only refined actions, which are blank nodes. `due2-undeclared-action` and `due2-undeclared-cc-action` are the negative cases. After the change, `check_odrl22.py --all` checks 129 files: 0 failing, 11 invalid as expected.
4. **Neither checker checked where a constraint or a Rule sits (2026-10-20, #93).** OVAL's validation files exposed it (§5a). The shape tested each property only at the place the IM gives it, and `check_corpus.py` read each only there, so an `odrl:refinement` on a Rule or a Policy, an `odrl:constraint` on an action node, and a Rule nested under an edge outside its domain, such as a Prohibition under a Permission, passed both, and normalisation would have dropped them. The ODRL vocabulary gives each of these properties a domain: `odrl:refinement` an Action, an AssetCollection, or a PartyCollection (Vocabulary §3.14.3); `odrl:constraint` a Policy or a Rule (Vocabulary §3.14.2); `permission`, `prohibition`, and `obligation` the Policy, `duty` a Permission, `remedy` a Prohibition, and `consequence` a Duty (Vocabulary §3.9.2, §3.10.2, §3.13.2–§3.13.5). IM §2.6.3 and §2.6.7 also keep a consequence off a Consequence and off a Remedy. The shape now states each domain as a `sh:maxCount 0` on every other subject, and `check_corpus.py` rejects a misplacement as `MisplacedConstraint` or `InvalidNesting` (`odrl-compound-to-atomic-normalization.md` §3). It also rejects an `odrl:constraint` on the Policy, which the vocabulary allows but the IM gives no meaning, as `UnsupportedConstruct`; the shape admits that one. Eight negative cases pin the checks: `oval-refinement-on-duty`, `oval-refinement-on-policy`, `oval-constraint-on-action`, `oval-constraint-on-collection`, `oval-prohibition-in-permission`, `oval-remedy-on-duty`, `oval-consequence-on-permission`, and `due2-policy-constraint`. After the change, `check_odrl22.py --all` checks 139 files: 0 failing, 18 invalid as expected.
5. **Neither checker checked three IM requirements, the shape missed a fourth, and the shape rejected one valid form (2026-10-24, #117).** The external review found them (`docs/briefings/due2-review-2026-10-24.md` R07), and `decisions/0034` settles them. Both checkers now require the value of a target, an output, or a party function to be a resource, never a literal (IM §2.2, §2.3, §2.6; `LiteralEntity`); a logical constraint to have exactly one operand property (IM §2.5.2; `MalformedConstraint`); and every action other than `odrl:use` and `odrl:transfer` to have exactly one `odrl:includedIn`, of type Action, on a path that reaches one of the two (IM §2.4; `InvalidActionHierarchy`). The shape also applies `decisions/0013`'s rule on repeated and list values to `odrl:rightOperandReference` (IM §2.5.1), which W1 rejects outright. And `check_odrl22.py` now applies IM §2.2.3's inference before it validates: an asset's `odrl:hasPolicy` makes the asset the target of every Rule of the policy, so the inverse form is valid ODRL 2.2. W1 rejects it with `UnsupportedConstruct`. IM §2.4 reached most of the corpus. 61 case policies defined 91 actions without an `odrl:includedIn`, as their RL2 and DPROD sources do, and each action now states `odrl:includedIn odrl:use`, the broadest action, since no source gives a closer one. Two more restated `odrl:display odrl:includedIn odrl:use`, which gave `odrl:display` a second value beside the vocabulary's `odrl:play`, and now drop it. DPROD's examples `baseline.ttl` and `odcs.ttl` define `ex:conformTo` without one: they stay vendored unmodified, both checkers list them as expected to fail, and the omission is reported upstream (EKGF/dprod#286). Six negative cases pin the checks: `due2-literal-party`, `due2-and-or`, `due2-two-right-operand-references`, `due2-action-without-parent`, `due2-action-two-parents`, and `due2-has-policy`. After the change, `check_odrl22.py --all` checks 159 files: 0 failing, 26 invalid as expected. No external suite's count changed from the runs of 2026-10-20 (§5a).
6. **Both checkers recognised a refined action by its node kind, and neither applied IM §2.3.3 (2026-10-25, #122, #123).** The follow-up review found both (`docs/briefings/due2-review-2026-10-25.md` F03, F04), and the amendment of `decisions/0034` settles them. A refined action is an action node with an `rdf:value` (IM §2.5.4), and the IM does not say the node is blank, but both checkers treated a named one as an action of the hierarchy, so a policy translated from JSON-LD with its node names kept, such as `w3c-fs-c1`, failed IM §2.4 and §2.1. Both now read a refined action's `rdf:value`, whatever its node kind, and `ActionHierarchyShape` admits any node with an `rdf:value` in place of any blank node: a blank action without one names no action, so it now fails both checkers. `w3c-fs-c1` and `w3c-fs-c2` keep their source's node names again. `check_odrl22.py` also applies IM §2.3.3's inference before it validates, as it applies §2.2.3's: a party's `odrl:assignerOf` or `odrl:assigneeOf` makes it the assigner or assignee of the policy's Rules, so the inverse form is valid ODRL 2.2, and W1 rejects it with `UnsupportedConstruct`. Four cases pin the change: `due2-refined-action-skolem`, a refined action named by a skolem IRI and typed `odrl:Action`, and the negative cases `due2-action-without-value`, `due2-assigner-of`, and `due2-assignee-of`. After the change, `check_odrl22.py --all` checks 163 files: 0 failing, 27 invalid as expected.
7. **Both checkers listed the properties whose value must be a resource, and missed a profile's own (2026-10-25, #124).** The follow-up review found it (`docs/briefings/due2-review-2026-10-25.md` F06). Each checker listed the target, the output, and the fourteen party functions of the ODRL vocabulary, so `dprod:subjectOfDuty "Alice"` passed both, and a duty's bearer was a name that no evidence actor, an `Id` and so an IRI (`due2-workflows.md` §2; `schema/collections.schema.json`), could match. In the ODRL vocabulary `odrl:function` has range `odrl:Party` and `odrl:relation` range `odrl:Asset`, and every party function and every relation is an `rdfs:subPropertyOf` descendant of one of them, as are DPROD's `dprod:subjectOfDuty` and `dprod:objectOfDuty`. Both checkers now read those descendants from the vocabularies, so a property a profile declares as such a sub-property is covered without a list to keep (`decisions/0034` item 2; `LiteralEntity`). `dprod:agent` has range `odrl:Party` but is a sub-property of neither, and stays outside the check: it is a property of DPROD's `EvaluationContext`, which describes a request, not a policy. The negative case `due2-literal-bearer` pins the change. After the change, `check_odrl22.py --all` checks 164 files: 0 failing, 28 invalid as expected.
8. **Both checkers placed a constraint by a list of the nodes it may not sit on, and missed a profile's own party (2026-10-25, #129).** Found while fixing item 7. The shape listed the action, the target, the output, and 8 of the 14 party functions, and `check_corpus.py` listed the ODRL ones, so a constraint on the Party that only `dprod:subjectOfDuty` names passed both, and normalisation would have dropped it. The ODRL vocabulary gives `odrl:constraint` the domain Policy or Rule (Vocabulary §3.14.2). RDFS reads that as entailing a type, and the vocabulary declares Party and Rule disjoint nowhere, so no reasoner would object; but the IM defines Party and Rule as separate classes (IM §2.3, §2.6). Both checkers now test the domain itself: a node with a constraint must be the Policy or a Rule. `check_corpus.py` tests `odrl:refinement`'s domain the same way, Action or collection; the shape keeps its rule that a Policy or a Rule holds no refinement, because a domain test there would need the Asset or Party type of every value of a function or relation sub-property, and the range types `check_odrl22.py` adds cover only the ODRL ones. The negative case `due2-constrained-bearer` pins the change. After the change, `check_odrl22.py --all` checks 165 files: 0 failing, 29 invalid as expected.

## From §5: the first half of #21

The first half of #21 was decided on 2026-10-11. Before then due2 rejected `odrl:source` outright, and `check_corpus.py` did not check asset and party nodes for it.

## 5a. Results against other evaluators' suites (2026-10-11)

The external suites vendored under `conformance/external/` exposed a defect in the harness. It validated with no inference, and the shape tests rule and constraint values by `sh:class`. An untyped rule node — `odrl:permission [ … ]`, the style of the IM's own Turtle examples — therefore failed `sh:class odrl:Permission`, and it was never targeted by `PermissionShape`, so its required target went unchecked. The corpus passed only because every corpus node is typed explicitly. `check_odrl22.py` now adds the types the ODRL 2.2 vocabulary entails: rdfs:range of `permission`, `prohibition`, `obligation`, `duty`, `remedy`, `consequence`, `action`, `target`, `assignee`, and `assigner`; rdfs:domain of `leftOperand`; and Logical Constraint for a node with a connective. rdfs:range of `leftOperand` is deliberately not applied, because it would make IM 2.5.1's "MUST be a LeftOperand" vacuous.

```text
python3 tools/check_odrl22.py --all                 111 checked, 0 failing, 7 invalid as expected   (107 cases: 66 + 34 translated, 7 of them FORCE 1–7 as negative cases + 7 due2-native; 4 DPROD files)
FORCE policies                                      21 checked, 7 failing   (policies 1-7: no target, 1-2 no action)
OVAL policies                                      105 checked, 85 failing  (Offer without assigner, missing targets, unit as string, ...)
```

The seven "invalid as expected" are FORCE policies 1–7, carried verbatim as negative cases (`odrl22_valid: false`, `conformance/README.md`). The harness fails if one of them conforms. The external failures are upstream IM violations, itemised in `conformance/external/README.md`. Six OVAL policies use a list right operand with `isPartOf`; the shape flagged them until the erratum of §2, which this record earlier described as a reading the IM leaves open. It was a due2 shape defect. The fix does not change the count: all six also lack an assigner (IM 2.1.2) and a target (IM 2.6.1), so they still fail.

Re-run 2026-10-16, after the OVAL refresh to `40b8ac6` (#51):

```text
python3 tools/check_odrl22.py --all                 112 checked, 0 failing, 7 invalid as expected   (108 cases: the new negative case oval-untyped-datetime is valid ODRL 2.2)
OVAL policies                                      110 checked, 52 failing  (undeclared left operands 47, unit as string 5)
```

Upstream fixed the assigners and targets. The four `listRightOperand` files now fail only on the undeclared left operand `ex:page`.

Re-run 2026-10-20, after the OVAL refresh to `532db7c`:

```text
OVAL policies                                      119 checked, 52 failing  (the same 52; the nine new logic_with_nulls files are valid)
```

Re-run 2026-10-20, after the OVAL refresh to `ee72ffc`:

```text
OVAL policies                                      122 checked, 51 failing  (undeclared left operands 47, unit as string 4)
OVAL validation/valid_ODRL                          36 checked,  9 failing  (unit as string 6, undefined terms 3, one assigner per policy 2)
OVAL validation/invalid_ODRL                        25 checked, 11 failing  (14 accepted: nested Rules 12, misplaced refinement 2; #93)
```

Re-run 2026-10-20, after the placement checks of #93 (§3 item 4):

```text
OVAL validation/valid_ODRL                          36 checked,  9 failing  (unchanged)
OVAL validation/invalid_ODRL                        25 checked, 25 failing
```

Re-run 2026-10-24, after the checks of #117 (§3 item 5):

```text
OVAL validation/valid_ODRL                          36 checked,  9 failing  (as on 2026-10-20)
OVAL validation/invalid_ODRL                        25 checked, 25 failing  (as on 2026-10-20)
FORCE policies                                      21 checked,  7 failing  (as on 2026-10-11)
```

The validation counts overlap: a file can fail for more than one reason. `conformance/external/README.md` § Triage of what was not translated gives the readings.
