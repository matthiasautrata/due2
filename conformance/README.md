# due2 conformance corpus

Cases are input/expected-output pairs in the reference data model of `due2-workflows.md`. They are written to be run by an evaluator; `tools/check_corpus.py` checks everything that can be checked without one.

```bash
uv run python tools/check_corpus.py conformance/cases          # every case
uv run python tools/check_corpus.py conformance/cases/<case>   # one case
uv run python tools/check_corpus.py profiles/vendor/dprod/examples/*.ttl   # the vendored DPROD examples, as policies
```

## Layout

```text
conformance/cases/<case>/
    policy.ttl     one ODRL policy, plus the operand bindings it uses
    case.json      provenance, classification, and scenarios — or, for a negative case, the expected rejection
```

Case names start with their origin: `rl2-` for the RL2 use cases (`github.com/matthiasautrata/RL2`, `conformance/usecases/`), `dprod-` for DPROD Contracts examples (`github.com/EKGF/dprod`, `develop`, `dprod-contracts/examples/`), `force-`, `oval-`, and `w3c-fs-` for other evaluators' suites (vendored under `external/`, see `external/README.md`), and `due2-` for cases authored here to cover what no origin exercises.

## Running a backend

Each positive scenario is a vector of the `interpret` task: its policy, request, SOTW, and config in, its `expected` out. `uv run pytest --backend=<spike>` runs every vector against a spike under `spikes/`; the protocol, output shape, and comparison rules are in `spikes/README.md`. Negative cases are not `interpret` vectors; they wait for W1, the normaliser.

## Vendored DPROD examples

The upstream example policies themselves are vendored unmodified under `profiles/vendor/dprod/examples/` — four files, sixteen policies: eleven offers and contracts in `baseline.ttl`, two in `data-contract.ttl`, two in `data-use-policy.ttl`, one in `odcs.ttl` — so the DPROD-compatibility claims are reproducible locally: the command above checks all sixteen against due2's admitted input profile, the DPROD profile selected by their own `odrl:profile`.

The `dprod-*` cases cover every one of the sixteen vendored policies with scenarios and hand-derived verdicts, plus constructed cases (`dprod-divergences`, `dprod-not-negated-purpose`) that demonstrate the six documented divergences. Cases extract their policy from the vendored file, naming anonymous rules and dropping DPROD's input `dprod:dutyState` triples (due2 derives status from evidence and activation instead); the `source` field names the file and policy, and `notes` records every such change.

## `policy.ttl`

- Exactly one policy, typed `odrl:Set`, `odrl:Offer`, `odrl:Agreement`, or a profile subclass such as `dprod:DataContract`.
- ODRL 2.2 vocabulary for everything ODRL has. Profile terms only from the extension points of `due2-profiles.md` §2, and the policy names its profiles with `odrl:profile`. Every action, left operand, operator, function, relation, and conflict value is an `odrl:` term, a term of a declared profile, or a term the policy types itself, such as `ex:display a odrl:Action` (`decisions/0020`). A `cc:` action needs a profile.
- Every rule is named (an IRI), so expected results can refer to it.
- Every left operand used is bound with `dprod:operandSource` and `dprod:operandProperty` (`due2-profiles.md` §3), either in the file or in a selected profile. Give `rdfs:range` wherever the type matters.
- Duty timing on duty rules only: `dprod:deadline` — an `xsd:dateTime`, or a single-kind `xsd:duration` relative to activation — and `dprod:recurrence`, an RRULE string containing `FREQ=` (`due2-profiles.md` §7).
- An explicit `odrl:conflict` unless the case is about the default.
- Self-contained: actions, parties, assets, and hierarchy edges the case needs are in the file — except what the shipped profile modules in `profiles/` already supply, such as ODRL's action hierarchy (`odrl:read ⊑ odrl:use`).
- Domain actions, assets, parties, and operands (`ex:retrieve`, `ex:requestedRecords`) are domain vocabulary. They do not count as profile terms for classification.

## `case.json`

```json
{
  "case": "rl2-volume-limit",
  "source": "RL2 conformance/usecases/volume-limit.md",
  "classification": "odrl-core",
  "needs": [],
  "notes": "How the RL2 original maps, and anything lost or changed.",
  "prefixes": { "ex": "https://example.org/" },
  "scenarios": [
    {
      "name": "within ceiling and quota",
      "request": {
        "reference": "req-1",
        "action": "ex:retrieve",
        "target": "ex:DataService",
        "at": "2026-06-01T00:00:00Z",
        "parties": { "odrl:assignee": "ex:Subscriber" },
        "params": { "ex:requestedRecords": { "@value": "12000", "@type": "xsd:integer" } }
      },
      "sotw": {
        "effective_at": "2026-06-01T00:00:00Z",
        "facts": {
          "ex:requestedWithinRemaining": { "status": "resolved", "values": [ { "@value": "true", "@type": "xsd:boolean" } ] }
        },
        "evidence": [],
        "activation": {},
        "closure": []
      },
      "config": { "combination": "prohibit-overrides" },
      "expected": {
        "verdict": "Permit",
        "frontier": [],
        "obligations": [],
        "why": "Both constraints hold; the permission applies and has no duties."
      },
      "rl2_expected": "Permit"
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `classification` | `odrl-core` — ODRL 2.2 plus operand bindings. `odrl-profile` — needs a profile term from `due2-profiles.md` §2. `partial` — some scenarios or aspects cannot be expressed. `not-expressible` — needs semantics outside due2's extension points; the closest ODRL is still written. |
| `needs` | For anything but `odrl-core`: the profile terms used, or the constructs missing. |
| `request.params` | Values of `dprod:requestSource` properties, keyed by property IRI. Absent means `missing`. An operand with `due2:cardinality due2:set` takes a JSON list of values (`oval-list-right-operand`). |
| `sotw.facts` | Values of `dprod:stateSource` properties: `status` is `resolved`, `missing`, `invalid`, `conflict`, or `unresolved`; `values` has one entry when resolved (any number, including none, for an operand declared `due2:cardinality due2:set`), two or more when in conflict, none otherwise. |
| `sotw.evidence` | `id`, `occurred_at`, `actor`, `action`, optional `object`, `issuer`, `discharges`, `params` (`due2-workflows.md` §3.3). `params` are read by `due2:witnessSource` operands in a duty's constraints (`due2-profiles.md` §3). `discharges` names a grant-scoped instance by the inputs of its key, `{"duty": IRI, "reference": <request reference>}`; the evaluator computes the digest (`due2-workflows.md` §5.3). |
| `sotw.activation` | Duty instance key or rule IRI → activation instant, an `xsd:dateTime`, for relative deadlines and recurrence anchors (`due2-workflows.md` §5.3, `due2-profiles.md` §7). |
| `sotw.closure` | `[relation, narrower, broader]` triples, for hierarchy edges not in the policy file. |
| `config` | `combination`; optional `preference`, `signers` (a list of `{"duty": IRI, "issuer": IRI}`, `due2-workflows.md` §3.4), `violations` (`ignore` by default, `deny` for DPROD-aligned evaluation — exception 6 of `due2-profiles.md` §8.2 still diverges), `admit_source`, `admit_age`. |
| `expected.verdict` | `Permit`, `Deny`, `Pending`, `NotApplicable`, or `Indeterminate`, derived by hand from `due2-workflows.md` §5–§6 and `due2-profiles.md`. |
| `expected.frontier` | For `Pending`: a list of alternatives, each a list of outstanding duty IRIs. |
| `expected.exact` | Optional, and only meaningful when unknowns could affect the verdict: `false` asserts that it comes from the beyond-`max_mixed` fallback (`due2-workflows.md` §6.4), `true` that the completion was exact (`due2-max-mixed`). |
| `expected.obligations` | Obligations in force for the request (`due2-workflows.md` §5.2, §6.1): `{"duty": IRI, "status": "fulfilled" \| "outstanding" \| "violated" \| "unknown"}`, plus `"instance": <occurrence instant>` for an instance of a recurring duty. Statuses follow the table of `due2-workflows.md` §5.3 — W2 computes them from the witness finding and the deadline; include `unknown` ones too, and remember that a recurring obligation with no instance owed yet is not reported. |
| `expected.verdict_basis` | Optional: the atoms that determined the verdict, by role, at the authored level (`due2-workflows.md` §3.7, §6.4) — a set of `{"ref": IRI, "role": R}`. `ref` is the rule IRI, or the duty IRI for roles `duty` and `obligation`; the disjuncts of one rule are one entry. Roles: `prohibition` (the surviving `T` prohibitions of a `Deny`), `permission` (a `Permit`'s ready permissions, a `Pending`'s frontier permissions), `duty` (a `Pending`'s outstanding duties — exactly the frontier's when no unknown part is listed), `unknown` (an `Indeterminate`'s `U` atoms with a pivotal literal, `decisions/0011`), `closed` (a `NotApplicable`'s candidates removed by a violated precondition), and `obligation` (every obligation in force under any verdict — exactly `expected.obligations`' duties). Under unknowns each role names the atoms that play it in every completion, so a verdict that holds by cases, such as a `Deny` from two prohibitions on `x eq 5` and `x neq 5` with `x` unresolved, can have no `prohibition` (`due2-workflows.md` §6.4, `decisions/0016`). A `Pending` that lists an unknown part of any status may lack `permission` or `duty`, and its duties may differ from the frontier's, because its frontier varies by dominance (`decisions/0019`). Absent means not asserted; `[]` asserts that nothing determined it. |
| `expected.eliminated` | Optional: the atoms removed, the atom that removed each, and the rule — a set of `{"ref": IRI, "by": IRI, "rule": X}` (`due2-workflows.md` §3.5, §6.1–§6.2). `X` is the policy's `conflict` (`prohibit`: a permission by a `T` prohibition; `perm`: a prohibition by a `T` permission; `invalid`: every rule of the void policy, by each `T` permission and prohibition other than itself), `violated_precondition` (a permission by its violated duty; with `verdict_basis`, the `closed` entries of a `NotApplicable` are exactly these), or the cross-policy `combination`. Absent means not asserted. |
| `expected.verdict_range` | Optional, for an `Indeterminate` only: the least and the greatest completion verdict, `{"low": V, "high": V}`, in the order `Deny < NotApplicable < Pending < Permit` (`due2-workflows.md` §3.5, §6.4, `decisions/0011`). `low` is below `high`, and neither is `Indeterminate`. Absent means not asserted. |
| `expected.unknown_parts` | Optional: every `U` part of every rule's atoms whose finding is `T` or `U`, and of every duty's findings that are `T` or `U` (a guard, a witness condition, or `odrl:assignee`, the bearer's party function, when the request names no subject), whether or not it determined anything, under any verdict (`due2-workflows.md` §3.5, §3.7, `decisions/0016` and its amendment) — a set of `{"ref": IRI, "input": IRI, "status": S}`. `ref` is the rule or duty IRI, and the parts of one rule or duty that read one input with one status are one entry. `input` is what the part reads: `odrl:target`, a party function such as `odrl:assignee`, or the operand's property. `status` is `missing` (no value: an absent target, party, or parameter, a state fact `missing`, or `resolved` with no value for a single-valued operand), `invalid`, `conflict`, `unresolved` (a state fact `unresolved`, or none), or `misfit` (a resolved value that does not fit the operator, `due2-workflows.md` §5.4). Absent means not asserted; `[]` asserts that every part was known. |
| `expected.why` | The derivation in one or two sentences — which atoms applied, which were unknown, why the verdict follows. |
| `rl2_expected`, `dprod_expected`, `force_expected`, `oval_expected`, `w3c_expected` | The origin's own expected result, where it states one, in the origin's vocabulary (FORCE: rule kind and activation state; OVAL: accept decision under its semantics switches; W3C CG: activation and control state). A difference from `expected.verdict` is explained in `notes`. |

**Negative cases.** A case whose policy W1 must reject carries `expected_rejection` instead of `scenarios`:

```json
"expected_rejection": {
  "codes": ["MissingTarget"],
  "why": "The permission has no odrl:target, at rule or policy level; `odrl-compound-to-atomic-normalization.md` §6.3 rejects it in stage 1."
}
```

- `codes` is the exact set of error codes W1 returns, from `docs/spec/due2-diagnostics.md` §3. W1 reports every error of the first failing stage and runs no later stage (`due2-diagnostics.md` §1), so the set is deterministic. `tools/check_corpus.py` compares it with what it emits.
- `why` names the defining section, as a scenario's `why` does.
- `odrl22_valid: false` marks a policy that is not valid ODRL 2.2, for example FORCE policies 1–7, which have no target. `tools/check_odrl22.py` then expects the shape to fail it (`xfail`) and fails if it conforms. Omitted, it means `true`: the rejection is due2's own (`due2-witness-outside-duty`). Only a negative case may set it to `false`.
- The origin's results are kept as they are on a translated scenario. `force-01` … `force-07` keep FORCE's test cases as a `force_expected` list of `{test_case, title, request, sotw, result}`; `oval-untyped-datetime` keeps OVAL's as an `oval_expected` list of `{test_case, title, request, result}`. A case translated from one of OVAL's validation files names the file as `test_case` and OVAL's expected rejection as `result`, with `title` and `request` null, because a validation file has neither.

**Values.** A literal is `{"@value": ..., "@type": ...}`, an IRI `{"@id": ...}` — the JSON-LD forms. Prefixed names expand through `prefixes`.

**Classification.** Context built-ins (`dprod:clock`, `dprod:agent`, `due2:actionTime`), `due2:witnessSource`, and the binding properties themselves are operand-binding vocabulary, not profile terms: a case that uses only them still classifies as `odrl-core`. Profile terms are the extension points of `due2-profiles.md` §2 — `dprod:not`, `dprod:deadline`, `dprod:recurrence`, `dprod:subjectOfDuty`, policy subclasses.

**Profile declaration is separate from classification.** IM §2.1 requires a policy that uses non-Core vocabulary to declare the profiles whose terms it uses — and the binding properties (`dprod:operandSource`, `dprod:operandProperty`) are DPROD-vocabulary terms appearing in the policy. So a case can classify `odrl-core` and still carry `odrl:profile <https://ekgf.org/dprod/spec/develop/>` (and `<https://w3id.org/due2/profile#>` when it uses `due2:` terms). `tools/check_corpus.py` rejects an undeclared namespace as a W1 input error — normalisation selects a profile's binding module by `odrl:profile` — and `tools/check_odrl22.py` checks the same rule against the IM directly. Both also reject a term from any other namespace that neither a declared profile nor the policy defines (`UndeclaredProfile`, `decisions/0020`).

**Standing divergences from RL2,** which a case need not re-explain:

- An unfulfilled precondition gives due2 `Pending` with the route, where RL2 gives `NotApplicable`.
- due2 closes `odrl:partOf` transitively; RL2 core matches only direct members.
- due2 evidence is existential: any witness fulfils a duty, so RL2's conflicting-evidence scenarios have no counterpart.
- Completion is over findings, so two permissions on complementary values of one unknown fact give `Indeterminate` (`due2-workflows.md` §6.4).

**Standing divergences from DPROD,** which a `dprod-*` case need not re-explain: the six exceptions of `due2-profiles.md` §8.2 — Kleene masking and errors in rules that do not apply, incomparable operands, duty state derived from evidence, Agreement parties, policy-level targets, and violated duties — together with DPROD's duty-collection rule (`formal-semantics.md` §7.2 step 1: a duty is collected only when its own action matches the request), which is why no DPROD duty is ever collected for a read.

Expected results are hand-derived. The derivation in `why` is what a reviewer checks.

## Coverage gaps

Specified and marked decided, but with no exercising case. Each gap is an authoring task, not a spec change; the list is re-derived by grepping the corpus. **Tracked as GitHub issues** (label `corpus`); this section remains the specification record.

Re-derived 2026-10-20, after the placement cases of #93; earlier re-derivations are listed in `docs/archive/changes.md` § `conformance/README.md` § Coverage gaps.

Closed gaps, with the cases that close them:

- **`due2:witnessSource` and `evidence_param`** — `oval-duty-payment`, `w3c-fs-c1`, `w3c-fs-c2` (as duty-action refinements, `due2-profiles.md` §9 #6).
- **Grant scope and `discharges`**, **`signers`** — `due2-grant-signers`.
- **`odrl:or`** — `force-20` (260 disjuncts, all known) and `due2-or-unknown` (Kleene, with unknowns).
- **`max_mixed` fallback (`due2-workflows.md` §6.4, beyond the bound)** — `due2-max-mixed` (nine facts each read both ways by an authored permission pair, `expected.exact = false`; scenario 2 sits at the bound, where only exact enumeration decides).
- **`perm` and `invalid` conflict strategies** — `oval-conflict-perm`, `oval-conflict-invalid`.
- **Incomparable frontier** — `due2-incomparable-frontier` (collapse, dominance, second approver); `config.preference` itself waits on its format (`due2-workflows.md` §9 #3).
- **Requests without a target** — `oval-no-target-permission`, `oval-no-target-prohibition` (`due2-workflows.md` §3.2, §5.2).
- **Canonical literals deciding a verdict** — `due2-xone-unknown` (an `xone` operand read both ways; `due2-workflows.md` §6.4).
- **Unknown duty guards; many conditional duties on one permission** — `due2-conditional-duties` (nine guarded duties, linear and exact, `decisions/0003`) and `w3c-fs-c2` scenarios 4–5.
- **`isPartOf` with a list right operand** — `oval-list-right-operand` (`decisions/0005`).
- **`verdict_basis` and `eliminated`** — `expected.verdict_basis` and `expected.eliminated` in the case format (#57), asserted by 61 scenarios: `due2-concept-complement`, `due2-concept-purpose`, `due2-concept-purpose-prohibition`, `due2-nested-unknowns`, `due2-or-unknown`, `due2-rebound-pay-amount`, `due2-repeated-right-operand`, `due2-shared-reads`, `due2-unresolved-or-missing`, `oval-conflict-invalid`, `oval-conflict-perm`, `oval-conflict-prohibit`, `rl2-pay-to-play`, `rl2-attestation-gating`. Every verdict and role is asserted, and the eliminations `prohibit`, `perm`, `invalid`, and `violated_precondition`. `expected.verdict_range` (#59) is asserted by the two `Indeterminate` scenarios of each of `due2-or-unknown`, `due2-repeated-right-operand`, `due2-shared-reads`, and `due2-concept-purpose-prohibition`, the four of each of `due2-unresolved-or-missing` and `due2-nested-unknowns`, the three of `due2-concept-purpose`, and the one of each of `due2-rebound-pay-amount` and `due2-concept-complement`.
- **Atoms that read one absent request field** — `due2-shared-reads` (one target, one assignee, under `invalid`): each atom is completed alone, so `Indeterminate` (`due2-workflows.md` §6.4, `decisions/0016`).
- **Unresolved against missing, misfit, and conflicting values** — `due2-unresolved-or-missing` (`decisions/0016`'s example: a pair of complementary permissions is a definite `Permit` with an empty basis only when the value is unresolved).
- **`unknown_parts`** — `expected.unknown_parts` in the case format (#72), asserted by the 31 scenarios of `due2-shared-reads`, `due2-unresolved-or-missing`, `due2-nested-unknowns`, the three concept-scheme cases, and `dprod-audit-logs`, whose obligation is `unknown` on a missing retention period. Every status is asserted, `invalid` by a concept in no declared scheme, and the inputs `odrl:target`, `odrl:assignee`, a state property, and `odrl:purpose`.
- **Unknown parts in nested trees** — `due2-nested-unknowns` (an `xone` with a decided member, an `or` of an `and`, an `and` of an `or`, and an `or` over a negated `or`): a `U` leaf that lies only in `F` atoms is not named, and one that decides nothing is (`due2-workflows.md` §3.5, `decisions/0016`, amendment).
- **A set right operand written as repeated values** — `due2-repeated-right-operand` (the list and the repeated form side by side, with the same three verdicts; `due2-profiles.md` §4, `decisions/0013`).
- **A higher layer rebinding an operand's source** — `due2-rebound-pay-amount` (the policy reads `odrl:payAmount` from the request and keeps the baseline's range; `due2-profiles.md` §2, `decisions/0014`).
- **Concept-scheme operands** — `due2-concept-purpose` (`eq` under `skos:broader`, with the SOTW supplying a concept's edges), `due2-concept-purpose-prohibition` (a prohibition, with `skos:narrower`, `skos:topConceptOf`, and `skos:hasTopConcept`), and `due2-concept-complement` (`neq` and `isNoneOf`); an in-scheme miss is `f`, and a concept in no scheme or a string is `u` (`due2-profiles.md` §4, `decisions/0015`).
- **Negative cases** — `expected_rejection` in the case format; `force-01` … `force-07` (`MissingAction`, `MissingTarget`), `due2-witness-outside-duty` (`WitnessOutsideDuty`), `oval-untyped-datetime` (`OperatorTypeMismatch`), `due2-malformed-right-operand` (`MalformedConstraint`), `due2-retyped-operand` (`RetypedOperand`), `due2-operand-range-mismatch` (`OperandRangeMismatch`), `due2-concept-out-of-scheme-right` and `due2-concept-operator` (`OperatorTypeMismatch`), `due2-concept-datatype-range` (`InvalidBinding`), `due2-empty-right-operand` and `due2-empty-logical-constraint` (`MalformedConstraint`), `due2-undeclared-action` and `due2-undeclared-cc-action` (`UndeclaredProfile`), `oval-refinement-on-duty`, `oval-refinement-on-policy`, `oval-constraint-on-action`, and `oval-constraint-on-collection` (`MisplacedConstraint`), `due2-policy-constraint` (`UnsupportedConstruct`), and `oval-prohibition-in-permission`, `oval-remedy-on-duty`, and `oval-consequence-on-permission` (`InvalidNesting`).
- **An anonymous target** — `due2-anonymous-target` (a blank-node collection described only by `dct:type`: `NotApplicable` when the request names a target, `Indeterminate` when it names none; the `AnonymousEntity` warning, #79).

Open gaps:

- **Rejection codes without a negative case.** Covered: `MissingAction`, `MissingTarget`, `WitnessOutsideDuty`, `OperatorTypeMismatch` (a right operand outside its range, a right operand outside its operand's concept schemes, and an operator other than `eq`, `neq`, `isAnyOf`, and `isNoneOf` on a concept-scheme operand; the operator-not-allowed and `isA`-over-a-set forms lack one), `MalformedConstraint` (several values on `eq`, a list mixed with a value, the empty list as a right operand, and a connective over the empty list; the missing-operand and two-lists forms lack one), `RetypedOperand` (a restated range; the cardinality and allowed-operator forms lack one), `OperandRangeMismatch`, `InvalidBinding` (a concept scheme on a datatype range; the source, property, and context-property forms lack one), `UndeclaredProfile` (an action no vocabulary defines; an undeclared DPROD or due2 namespace lacks one), `MisplacedConstraint` (a refinement on a Duty and on a Policy, a constraint on an action node and on an AssetCollection; a constraint on an Asset or a Party lacks one), `UnsupportedConstruct` (a constraint on the Policy; `odrl:inheritFrom`, `odrl:rightOperandReference`, `odrl:implies`, a misplaced `odrl:source`, and a collection refinement lack one), `InvalidNesting` (a Prohibition under a Permission, a remedy on a Duty, a consequence on a Permission; a consequence on a Consequence or a Remedy, and a node in two Rule classes, lack one). `ConflictingProfileDeclaration` cannot have one while DPROD is the only profile that ships a binding module, because it needs two modules that declare one term differently; the clingo-i unit tests cover it with test modules. Every other error of `due2-diagnostics.md` §3 needs one. `odrl-compound-to-atomic-normalization.md` §10's minimum suite names the stage-1 vectors. The *unchecked* rows need W1 itself, because the checker cannot see them.
- **`admit_source` / `admit_age`** — a case-format gap: `sotw.facts` carries no attribution (`source`, `observed_at`), so the filter cannot be shown at work; three cases note this in `notes`. Fixing it needs a fact-attribution extension to the case format.
- **`config.preference`** — the incomparable frontier has a case (`due2-incomparable-frontier`), but the preference format is open (`due2-workflows.md` §9 #3, #5).
- **Several policies per case** — `due2-workflows.md` §9 #7 (#1); blocked on a case-format extension. With it come the cross-policy combinations: every case's `combination` is `prohibit-overrides`.
- **`frontier_complete`** — no case asserts it, neither an incomplete frontier under a definite `Pending` nor the beyond-`max_frontier_vars` fallback (`due2-workflows.md` §6.4, `decisions/0004`); needs `expected.frontier_complete` in the case format (#30).
- **The explanation in the rest of the corpus** — 61 of 438 scenarios assert `verdict_basis` and `eliminated`, and 31 assert `unknown_parts` (`due2-workflows.md` §3.7). The W3 done-gate names `verdict_basis` (`correctness-strategy.md` §4.5), so the rest are backfilled as cases are touched. An elimination by the cross-policy `combination` waits for several policies per case. 21 of the 88 `Indeterminate` scenarios assert `verdict_range`. The `Indeterminate` witness is open (#58).
- **`hasPart` and `isA` with a list**, and a non-trivial `partOf` closure under a list — `due2-profiles.md` §4, `decisions/0005` (#32).
- **Remedies and consequences** — carried by stage 1, not evaluated for access; no case until the monitoring question (`due2-workflows.md` §9 #4, #6) is specified. OVAL's monitoring cases are the external material.
