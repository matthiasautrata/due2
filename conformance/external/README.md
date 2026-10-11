# External ODRL test suites

Other evaluators' test cases, vendored **unmodified** so that every translated corpus case is reproducible from source and every divergence can be checked against the original. Collected 2026-10-11.

| Directory | Upstream (commit) | License | Contents | Cases |
|---|---|---|---|---|
| `force/` | [SolidLabResearch/ODRL-Test-Suite](https://github.com/SolidLabResearch/ODRL-Test-Suite) `7958238` — FORCE, Ghent/imec | MIT (`force/LICENSE.md`) | `data/{index.ttl, policies, requests, sotw, test_cases}`; expected Compliance Reports. `data/results` (their evaluator's run reports) omitted. | 68 |
| `oval/` | [DIPS-Tools/ODRL-Engine](https://github.com/DIPS-Tools/ODRL-Engine) `f0839f6` — OVAL, Southampton | MIT (`oval/LICENSE`) | `access_control/` (policy, request JSON, expected decision with OVAL's semantics switches); `monitoring/{valid,invalid}/` (policy, CSV event log, expected compliance); `unit_tests.md` documents the switches. `force/` (their translation of FORCE) omitted. | 29 + 76 |
| `w3c-fs/` | [w3c/odrl](https://github.com/w3c/odrl) `1db8e6b` `formal-semantics/examples/` — W3C ODRL CG | W3C Software and Document License (`w3c-fs/LICENSE.md`) | JSON-LD policies, evaluation requests, states, compliance reports. | 9 |

Refresh by re-cloning at a newer commit and re-running the translation; never edit files here.

Searched and not vendored: ODRL-PAP (tests are ODRL→Rego translations, not verdicts), odrl-manager (expectations embedded in TypeScript), ODRE (policies without expected verdicts), Gaia-X odrl-toolbox testbed (one case), W3C POE 2018 test material (structural validation only; superseded by `odrl22-shape.ttl`).

## Translated into the corpus

| Corpus cases | From | Scenarios | How |
|---|---|---|---|
| `force-08` … `force-21` (14) | FORCE policies 8–21, test cases 026–068 | 43 | `tools/import_force.py` — mechanical, with an independent due2 derivation; disagreements flagged in `notes` (none beyond the documented divergences) |
| `oval-conflict-{perm,prohibit,invalid}`, `oval-duty-payment`, `oval-party-collection`, `oval-action-hierarchy` | OVAL access_control conflict1–3, duty1–3, partOf1–3, includedIn1–3 | 15 | By hand; each change in `notes` |
| `w3c-fs-a1`, `-b1`, `-c1`, `-c2` | W3C CG A1, B1, C1, C2 | 12 | By hand; each change in `notes` |

Each translated scenario keeps the origin's own result (`force_expected`, `oval_expected`, `w3c_expected`) next to due2's hand-derived `expected`, where the origin states one; scenarios added here are named `(added)` and have no origin result.

## Triage of what was not translated

| Group | Count | Why | Disposition |
|---|---|---|---|
| FORCE policies 1–7 (test cases 001–025) | 25 | Rules without `odrl:target` (and 1–2 without `odrl:action`). IM 2.6.1/2.6.2: a Permission and a Prohibition MUST have one target — these are not ODRL 2.2, and due2 rejects them at normalisation. They test FORCE's reading of an absent target as "any". | Not translatable. Reported upstream before — acknowledged, not fixed (2026-10-11); do not re-report. |
| OVAL `permission1–3`, `prohibition1–3` | 6 | Plain match / no-match; OVAL's default-semantics switch is irrelevant when a rule matches. Already covered by the corpus. | Skipped as redundant. |
| OVAL `default_sem1–6` | 6 | Requests with no Asset. due2's request has a mandatory `target` (workflows §3.2), so these cannot be posed. | **Blocked on a spec question** — see Findings #1. |
| OVAL `listRightOperand1–4` | 4 | `isPartOf` with a list right operand, read by OVAL as subset/membership. due2 admits lists only for set-based operators (`odrl22-conformance.md` §2, a due2 reading of IM 2.5.1). | Reading divergence, recorded. |
| OVAL `date1` | 1 | No target, untyped right operand `"2020-03-11T11:33:10"`, request without time. | Not ODRL 2.2 as written. |
| OVAL `monitoring/*` | 76 | Compliance of an event log, not an access request. due2's monitoring question is open (workflows §9 #4). `logic_or`, `logic_xone`, `logic_nested*` are useful once it is specified. | Deferred to #4. |
| W3C CG A2 | — | Policy without evaluation requests. | Nothing to translate. |

## Findings

**For due2's specs** (registered where noted):

1. **Requests without a target** (OVAL `default_sem*`). OVAL accepts them and lets a default semantics decide; due2 cannot express them. Options: (a) a malformed request, rejected before W2; (b) the target part is `U`, as an absent party already is (workflows §5.2: absent is not false), so permissions and prohibitions on the action become uncertain. (b) is the consistent reading; registered as workflows §9 #8.
2. **`invalid` voids a policy** (OVAL `conflict3`). OVAL reports such a policy as not evaluable — the alternative architecture §6.2 keeps open (Indeterminate with a cause) — where due2 currently contributes nothing (`NotApplicable`). First external evidence on that item; see `oval-conflict-invalid`.
3. **Refinement-free `odrl:source` on collections** (FORCE policies 16–18, 21). FORCE names collections by `odrl:source` and takes membership from `odrl:partOf` edges in the state of the world. due2 rejects `odrl:source`; translation drops it with no change in meaning. Evidence for `odrl22-conformance.md` §5 (whether to admit a refinement-free `source` as inert).
4. **Witness conditions as duty-action refinements** (OVAL duty1–3, CG C1–C2). Both write "pay at least/exactly x" as an `odrl:payAmount` refinement on `odrl:compensate`. With `odrl:payAmount` explicitly bound to `due2:witnessSource`, this is an ordinary witness condition — no new machinery. Evidence for `due2-profiles.md` §9 #6, which reduces to whether `due2-core` should ship that binding.
5. **Hoisting precision** (CG C2). A duty guarded by the request's weekday is exactly the case where independent completion widened the verdict to `Indeterminate`. Resolved by workflows v0.6 (completions over literals); `w3c-fs-c2` carries the scenario.

**For the ODRL formal semantics** (WG material):

6. **Unfulfilled preconditions: three evaluators, three readings.** FORCE activates the permission ("given that eventually the duty is fulfilled"); OVAL parameterises it (`semantics_for_duties`, default accept); the CG examples deny (C11, C22). due2 answers `Pending` with the duty as the route — which is what all three approximate as yes/no.
7. **Unknown is false everywhere else.** FORCE ("if no information is present … not satisfied"), OVAL, and the CG examples all close unknowns to false; none of the suites contains a case whose correct answer depends on an unknown. `due2-or-unknown` and `w3c-fs-b1` scenario 3 are such cases.
8. **Absent default semantics is a policy-level choice in the CG** (`Behaviour`: default/close/open) and an evaluator switch in OVAL. due2 returns `NotApplicable` and leaves the default to the enforcement point.
9. **Comparison across XSD types.** CG A1/A2 compare an `xsd:dateTime` action time with `"2018-01-01"^^xsd:date`, and use timezone-less instants, which XSD orders only partially. ODRL 2.2 does not say how; due2 rejects the mismatch at normalisation.
10. **Refinement vs constraint failure.** CG B12 keeps a rule `Active` when its refinement fails (controlState Deny), while A12 makes it `Inactive` when its constraint fails. due2 treats both as the atom not applying.

**Upstream defects found while translating** (status per bullet):

- FORCE: policies 1–7 omit required targets; test case 036 is wired to `temporal-future.ttl` (duplicate of 038) though titled for the current time; `all-2023.ttl`/`all-2024.ttl` carry a DutyReport for policy-19's duty instead of policy-21's. Reported upstream once before (acknowledged, not fixed — 2026-10-11); re-reporting is pointless until they act.
- OVAL: a summary of the findings below was sent to the authors on 2026-10-11, with the offer to file issues.
- OVAL: 74 of its 105 policy files are Offers without an assigner (IM 2.1.2); 85 of 105 fail ODRL 2.2 validation in all; untargeted rules; `odrl:unit` as a string literal (IM: IRI); untyped dateTime right operands.
- W3C CG: C1/C2 requests name `party/billie1` against assignee `party/billie` while the expected reports permit; B11/B12 request values written `{"@id": "1000"}` with `describesFeature` the unit IRI rather than the operand; C12 `paymentDate` untyped.

## Validator fixes the external data forced

- `tools/check_odrl22.py` ran with no inference, so an untyped rule (`odrl:permission [ … ]`, the IM's own example style) failed `sh:class odrl:Permission` **and** escaped `PermissionShape` — a missing target went unreported. It now adds the types the ODRL vocabulary entails (rdfs:range of the rule, action, target, and party properties; rdfs:domain of `odrl:leftOperand`; the connective of a Logical Constraint). The corpus still passes; external policies now fail for real reasons only.
- `tools/check_corpus.py` checked rejected constructs on policy, rule, and constraint nodes, never on asset or party nodes — where `odrl:source` and collection refinements actually occur (IM 2.5.5–2.5.6). It now checks them.
