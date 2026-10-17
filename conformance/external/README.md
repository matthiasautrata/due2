# External ODRL test suites

Other evaluators' test cases, vendored **unmodified** so that every translated corpus case is reproducible from source and every divergence can be checked against the original. Collected 2026-10-11; OVAL refreshed 2026-10-16.

| Directory | Upstream (commit) | License | Contents | Cases |
|---|---|---|---|---|
| `force/` | [SolidLabResearch/ODRL-Test-Suite](https://github.com/SolidLabResearch/ODRL-Test-Suite) `7958238` — FORCE, Ghent/imec | MIT (`force/LICENSE.md`) | `data/{index.ttl, policies, requests, sotw, test_cases}`; expected Compliance Reports. `data/results` (their evaluator's run reports) omitted. | 68 |
| `oval/` | [DIPS-Tools/ODRL-Engine](https://github.com/DIPS-Tools/ODRL-Engine) `40b8ac6` — OVAL, Southampton | MIT (`oval/LICENSE`) | `access_control/` (policy, request JSON, expected decision with OVAL's semantics switches); `monitoring_compliant/`, `monitoring_non_compliant/` (policy, CSV event log, expected compliance; upstream's names since `81524b2`); `unit_tests.md` documents the switches. `force/` (their translation of FORCE) omitted. | 29 + 81 |
| `w3c-fs/` | [w3c/odrl](https://github.com/w3c/odrl) `1db8e6b` `formal-semantics/examples/` — W3C ODRL CG | W3C Software and Document License (`w3c-fs/LICENSE.md`) | JSON-LD policies, evaluation requests, states, compliance reports. | 9 |

Refresh by re-cloning at a newer commit and re-running the translation; never edit files here.

Searched and not vendored: ODRL-PAP (tests are ODRL→Rego translations, not verdicts), odrl-manager (expectations embedded in TypeScript), ODRE (policies without expected verdicts), Gaia-X odrl-toolbox testbed (one case), W3C POE 2018 test material (structural validation only; superseded by `odrl22-shape.ttl`).

## Translated into the corpus

| Corpus cases | From | Scenarios | How |
|---|---|---|---|
| `force-01` … `force-07` (7) | FORCE policies 1–7, test cases 001–025 | — | `tools/import_force.py --negative`. Negative cases: the policy is verbatim, the rejection is `MissingTarget` (1–2 also `MissingAction`), and all 25 test cases are kept as `force_expected` |
| `force-08` … `force-21` (14) | FORCE policies 8–21, test cases 026–068 | 43 | `tools/import_force.py` — mechanical, with an independent due2 derivation; disagreements flagged in `notes` (none beyond the documented divergences) |
| `oval-conflict-{perm,prohibit,invalid}`, `oval-duty-payment`, `oval-party-collection`, `oval-action-hierarchy` | OVAL access_control conflict1–3, duty1–3, partOf1–3, includedIn1–3 | 15 | By hand; each change in `notes` |
| `w3c-fs-a1`, `-b1`, `-c1`, `-c2` | W3C CG A1, B1, C1, C2 | 12 | By hand; each change in `notes` |
| `oval-no-target-permission`, `oval-no-target-prohibition` | OVAL default_sem1–6, permission1–3, prohibition1–3 | 4 | By hand, after workflows §9 #8 was decided (issue #26) |
| `oval-list-right-operand` | OVAL listRightOperand1–4 | 4 | By hand; `due2-profiles.md` §4's list reading of `isPartOf` |
| `oval-untyped-datetime` | OVAL date1 | — | Negative case: the constraint as authored, rejected `OperatorTypeMismatch` (an untyped right operand for `odrl:dateTime`); OVAL's result kept as `oval_expected` |

Each translated scenario keeps the origin's own result (`force_expected`, `oval_expected`, `w3c_expected`) next to due2's hand-derived `expected`, where the origin states one; scenarios added here are named `(added)` and have no origin result.

## Triage of what was not translated

| Group | Count | Why | Disposition |
|---|---|---|---|
| FORCE policies 1–7 (test cases 001–025) | 25 | Rules without `odrl:target` (and 1–2 without `odrl:action`). IM 2.6.1/2.6.2: a Permission and a Prohibition MUST have one target — these are not ODRL 2.2, and due2 rejects them at normalisation. They test FORCE's reading of an absent target as "any". | Translated as negative cases `force-01` … `force-07`: the expected answer is the rejection, and FORCE's results are kept. Reported upstream before — acknowledged, not fixed (2026-10-11); do not re-report. |
| OVAL `listRightOperand1–4` | 4 | `isPartOf` with a list right operand. Recorded until 2026-10-11 as a reading divergence; it was a due2 shape defect, now fixed (`odrl22-conformance.md` §2 erratum). At `f0839f6` the originals lacked an assigner (IM 2.1.2) and a target (IM 2.6.1); since `40b8ac6` they are targeted Sets. | Translated as `oval-list-right-operand`. |
| OVAL `date1` | 1 | Untargeted until `531edf1`; untyped right operand `"2020-03-11T11:33:10"`, request without time (OVAL substitutes the current time). | Translated as the negative case `oval-untyped-datetime` (2026-10-16). |
| OVAL `monitoring_compliant/*`, `monitoring_non_compliant/*` | 81 | Compliance of an event log, not an access request. due2's monitoring question is open (workflows §9 #4). `logic_or`, `logic_xone`, `logic_nested*` are useful once it is specified. | Deferred to #4. |
| W3C CG A2 | — | Policy without evaluation requests. | Nothing to translate. |

## Findings

**For due2's specs** (registered where noted):

1. **Requests without a target** (OVAL `default_sem*`). OVAL accepts them and lets an evaluator switch decide (prohibit, permit, or unspecified by default). due2 decided (2026-10-11, workflows §3.2, §5.2, issue #26) that the target is optional and an absent one makes every relation part `U`, as an absent party already did: the verdict is `Indeterminate` when the target could decide it, and the default belongs to the enforcement point. Translated as `oval-no-target-permission`, `oval-no-target-prohibition`.
2. **`invalid` voids a policy** (OVAL `conflict3`). OVAL reports such a policy as not evaluable. due2 decided (2026-10-11, architecture §6.2) to keep *contributes nothing* (`NotApplicable`): validity is W1's and the checkers' concern, a self-voiding policy is an evaluation outcome visible in the trace, and OVAL's reading conflates the two. See `oval-conflict-invalid`.
3. **Refinement-free `odrl:source` on collections** (FORCE policies 16–18, 21). FORCE names collections by `odrl:source` and takes membership from `odrl:partOf` edges in the state of the world. Under due2's closure reading this is inert, so it is now admitted as an annotation (2026-10-11, `due2-profiles.md` §8.1) and the translations keep it. Collection refinements stay rejected (issue #21).
4. **Witness conditions as duty-action refinements** (OVAL duty1–3, CG C1–C2). Both write "pay at least/exactly x" as an `odrl:payAmount` refinement on `odrl:compensate`. Since 2026-10-11 `due2-core` binds `odrl:payAmount` to `due2:witnessSource` (`due2-profiles.md` §9 #6), so these policies need no binding of their own and are used as written.
5. **Conditional duties** (CG C2). A duty guarded by the request's weekday exposed two things. Under hoisting, independent completion widened the verdict to `Indeterminate`; workflows v0.6 fixed that with completions over literals. Hoisting itself was then withdrawn, because it is ×2^c for c guarded duties on one permission (`decisions/0003`). The CG's reading — duty Inactive, permission Active (C21) — is now due2's structure as well: guards stay on the duty.

**For the ODRL formal semantics** (WG material):

6. **Unfulfilled preconditions: three evaluators, three readings.** FORCE activates the permission ("given that eventually the duty is fulfilled"); OVAL parameterises it (`semantics_for_duties`, default accept); the CG examples deny (C11, C22). due2 answers `Pending` with the duty as the route — which is what all three approximate as yes/no.
7. **Unknown is false everywhere else.** FORCE ("if no information is present … not satisfied"), OVAL, and the CG examples all close unknowns to false. OVAL comes closest: it also reports *conditional matches*, rules that would match for some values of the request's unspecified features, with a warning — but its decision ignores them, and inside a logical constraint the null re-evaluation is unreachable code, so an unspecified feature there is plain false (`ODRL_Evaluator.py` `eval_constraint`, at `40b8ac6`); none of the suites contains a case whose correct answer depends on an unknown. `due2-or-unknown` and `w3c-fs-b1` scenario 3 are such cases.
8. **Absent default semantics is a policy-level choice in the CG** (`Behaviour`: default/close/open) and an evaluator switch in OVAL. due2 returns `NotApplicable` and leaves the default to the enforcement point.
9. **Comparison across XSD types.** CG A1/A2 compare an `xsd:dateTime` action time with `"2018-01-01"^^xsd:date`, and use timezone-less instants, which XSD orders only partially. ODRL 2.2 does not say how; due2 rejects the mismatch at normalisation.
10. **Refinement vs constraint failure.** CG B12 keeps a rule `Active` when its refinement fails (controlState Deny), while A12 makes it `Inactive` when its constraint fails. due2 treats both as the atom not applying.

**Upstream defects found while translating** (status per bullet):

- FORCE: policies 1–7 omit required targets; test case 036 is wired to `temporal-future.ttl` (duplicate of 038) though titled for the current time; `all-2023.ttl`/`all-2024.ttl` carry a DutyReport for policy-19's duty instead of policy-21's. Reported upstream once before (acknowledged, not fixed — 2026-10-11); re-reporting is pointless until they act.
- OVAL: a summary of the findings below was sent to the authors on 2026-10-11, with the offer to file issues. They acted on it within two days (`c2773ed` … `19692cc`, 2026-10-11 to 10-13): the test policies are Sets, every rule has a target, and their SHACL now requires targets and restricts `odrl:conflict` values and sub-rule types.
- OVAL: hierarchy reasoning (since 2026-08-27; unchanged at `40b8ac6`) covers only a rule's action, assignee and target. Constraint values get none: `isPartOf` and `hasPart` are plain subset tests, `isA` is unsupported, and a narrower SKOS purpose does not match `purpose eq` its broader one, so a prohibition fails open. Reported 2026-10-16 as [DIPS-Tools/ODRL-Engine#8](https://github.com/DIPS-Tools/ODRL-Engine/issues/8); due2's reading is issue #52.
- OVAL: null matching inside a logical constraint is unreachable (finding 7). Reported 2026-10-16 as [DIPS-Tools/ODRL-Engine#9](https://github.com/DIPS-Tools/ODRL-Engine/issues/9).
- OVAL: at `f0839f6`, 74 of its 105 policy files were Offers without an assigner (IM 2.1.2), rules were untargeted, and 85 of 105 failed ODRL 2.2 validation; both are fixed. At `40b8ac6`, 52 of 110 still fail: 47 use left operands that neither the ODRL vocabulary nor a declared profile defines (`ex:page`, `ex:age`, `ex:publicationDate`, and `odrl:adminLevel`, which is not an ODRL term; IM 2.1), and 5 write `odrl:unit` as a string literal (IM 2.5.1: an IRI). 17 write dateTime right operands untyped.
- W3C CG: C1/C2 requests name `party/billie1` against assignee `party/billie` while the expected reports permit; B11/B12 request values written `{"@id": "1000"}` with `describesFeature` the unit IRI rather than the operand; C12 `paymentDate` untyped.

## Validator fixes the external data forced

- `tools/check_odrl22.py` ran with no inference, so an untyped rule (`odrl:permission [ … ]`, the IM's own example style) failed `sh:class odrl:Permission` **and** escaped `PermissionShape` — a missing target went unreported. It now adds the types the ODRL vocabulary entails (rdfs:range of the rule, action, target, and party properties; rdfs:domain of `odrl:leftOperand`; the connective of a Logical Constraint). The corpus still passes; external policies now fail for real reasons only.
- `tools/check_corpus.py` checked rejected constructs on policy, rule, and constraint nodes, never on asset or party nodes — where `odrl:source` and collection refinements actually occur (IM 2.5.5–2.5.6). It now checks them.
