# due2 conformance corpus

Cases are input/expected-output pairs in the reference data model of `due2-workflows.md`. They are written to be run by an evaluator; until one exists, `tools/check_corpus.py` checks everything that can be checked without one.

```bash
python3 tools/check_corpus.py conformance/cases          # every case
python3 tools/check_corpus.py conformance/cases/<case>   # one case
python3 tools/check_corpus.py profiles/vendor/dprod/examples/*.ttl   # the vendored DPROD examples, as policies
```

## Layout

```
conformance/cases/<case>/
    policy.ttl     one ODRL policy, plus the operand bindings it uses
    case.json      provenance, classification, and scenarios
```

Case names start with their origin: `rl2-` for the RL2 use cases (`github.com/matthiasautrata/RL2`, `conformance/usecases/`), `dprod-` for DPROD Contracts examples (`github.com/EKGF/dprod`, `develop`, `dprod-contracts/examples/`), `force-`, `oval-`, and `w3c-fs-` for other evaluators' suites (vendored under `external/`, see `external/README.md`), and `due2-` for cases authored here to cover what no origin exercises.

## Vendored DPROD examples

The upstream example policies themselves are vendored unmodified under `profiles/vendor/dprod/examples/` — four files, sixteen policies: eleven offers and contracts in `baseline.ttl`, two in `data-contract.ttl`, two in `data-use-policy.ttl`, one in `odcs.ttl` — so the DPROD-compatibility claims are reproducible locally: the command above checks all sixteen against due2's admitted input profile, the DPROD profile selected by their own `odrl:profile`.

The `dprod-*` cases cover every one of the sixteen vendored policies with scenarios and hand-derived verdicts, plus constructed cases (`dprod-divergences`, `dprod-not-negated-purpose`) that demonstrate the six documented divergences. Cases extract their policy from the vendored file, naming anonymous rules and dropping DPROD's input `dprod:dutyState` triples (due2 derives status from evidence and activation instead); the `source` field names the file and policy, and `notes` records every such change.

## `policy.ttl`

- Exactly one policy, typed `odrl:Set`, `odrl:Offer`, `odrl:Agreement`, or a profile subclass such as `dprod:DataContract`.
- ODRL 2.2 vocabulary for everything ODRL has. Profile terms only from the extension points of `due2-profiles.md` §2, and the policy names its profiles with `odrl:profile`.
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
| `request.params` | Values of `dprod:requestSource` properties, keyed by property IRI. Absent means `missing`. |
| `sotw.facts` | Values of `dprod:stateSource` properties: `status` is `resolved`, `missing`, `invalid`, `conflict`, or `unresolved`; `values` has one entry when resolved (any number, including none, for an operand declared `due2:cardinality due2:set`), two or more when in conflict, none otherwise. |
| `sotw.evidence` | `id`, `occurred_at`, `actor`, `action`, optional `object`, `issuer`, `discharges`, `params` (`due2-workflows.md` §3.3). `params` are read by `due2:witnessSource` operands in a duty's constraints (`due2-profiles.md` §3). `discharges` names a grant-scoped instance by the inputs of its key, `{"duty": IRI, "reference": <request reference>}`; the evaluator computes the digest (§5.3). |
| `sotw.activation` | Duty instance key or rule IRI → activation instant, an `xsd:dateTime`, for relative deadlines and recurrence anchors (`due2-workflows.md` §5.3, `due2-profiles.md` §7). |
| `sotw.closure` | `[relation, narrower, broader]` triples, for hierarchy edges not in the policy file. |
| `config` | `combination`; optional `preference`, `signers` (a list of `{"duty": IRI, "issuer": IRI}`, workflows §3.4), `violations` (`ignore` by default, `deny` for DPROD-aligned evaluation — exception 6 of `due2-profiles.md` §8.2 still diverges), `admit_source`, `admit_age`. |
| `expected.verdict` | `Permit`, `Deny`, `Pending`, `NotApplicable`, or `Indeterminate`, derived by hand from `due2-workflows.md` §5–§6 and `due2-profiles.md`. |
| `expected.frontier` | For `Pending`: a list of alternatives, each a list of outstanding duty IRIs. |
| `expected.exact` | Optional, and only meaningful when unknowns could affect the verdict: `false` asserts that it comes from the beyond-`max_mixed` fallback (`due2-workflows.md` §6.4), `true` that the completion was exact (`due2-max-mixed`). |
| `expected.obligations` | Obligations in force for the request (`due2-workflows.md` §5.2, §6.1): `{"duty": IRI, "status": "fulfilled" \| "outstanding" \| "violated" \| "unknown"}`, plus `"instance": <occurrence instant>` for an instance of a recurring duty. Statuses follow §5.3's table — W2 computes them from the witness finding and the deadline; include `unknown` ones too, and remember that a recurring obligation with no instance owed yet is not reported. |
| `expected.why` | The derivation in one or two sentences — which atoms applied, which were unknown, why the verdict follows. |
| `rl2_expected`, `dprod_expected`, `force_expected`, `oval_expected`, `w3c_expected` | The origin's own expected result, where it states one, in the origin's vocabulary (FORCE: rule kind and activation state; OVAL: accept decision under its semantics switches; W3C CG: activation and control state). A difference from `expected.verdict` is explained in `notes`. |

**Values.** A literal is `{"@value": ..., "@type": ...}`, an IRI `{"@id": ...}` — the JSON-LD forms. Prefixed names expand through `prefixes`.

**Classification.** Context built-ins (`dprod:clock`, `dprod:agent`, `due2:actionTime`), `due2:witnessSource`, and the binding properties themselves are operand-binding vocabulary, not profile terms: a case that uses only them still classifies as `odrl-core`. Profile terms are the extension points of `due2-profiles.md` §2 — `dprod:not`, `dprod:deadline`, `dprod:recurrence`, `dprod:subjectOfDuty`, policy subclasses.

**Profile declaration is separate from classification.** IM §2.1 requires a policy that uses non-Core vocabulary to declare the profiles whose terms it uses — and the binding properties (`dprod:operandSource`, `dprod:operandProperty`) are DPROD-vocabulary terms appearing in the policy. So a case can classify `odrl-core` and still carry `odrl:profile <https://ekgf.org/dprod/spec/develop/>` (and `<https://w3id.org/due2/profile#>` when it uses `due2:` terms). `tools/check_corpus.py` rejects an undeclared namespace as a W1 input error — normalisation selects a profile's binding module by `odrl:profile` — and `tools/check_odrl22.py` checks the same rule against the IM directly.

**Standing divergences from RL2,** which a case need not re-explain:
- An unfulfilled precondition gives due2 `Pending` with the route, where RL2 gives `NotApplicable`.
- due2 closes `odrl:partOf` transitively; RL2 core matches only direct members.
- due2 evidence is existential: any witness fulfils a duty, so RL2's conflicting-evidence scenarios have no counterpart.
- Completion is over findings, so two permissions on complementary values of one unknown fact give `Indeterminate` (`due2-workflows.md` §6.4).

**Standing divergences from DPROD,** which a `dprod-*` case need not re-explain: the six exceptions of `due2-profiles.md` §8.2 — Kleene masking and errors in rules that do not apply, incomparable operands, duty state derived from evidence, Agreement parties, policy-level targets, and violated duties — together with DPROD's duty-collection rule (`formal-semantics.md` §7.2 step 1: a duty is collected only when its own action matches the request), which is why no DPROD duty is ever collected for a read.

Expected results are hand-derived until an evaluator exists. The derivation in `why` is what a reviewer checks.

## Coverage gaps

Specified and marked decided, but with no exercising case. Each gap is an authoring task, not a spec change; the list is re-derived by grepping the corpus. **Tracked as GitHub issues** (label `corpus`); this section remains the specification record.

Re-derived 2026-10-11, after the external suites and the `due2-` cases. Closed since 2026-10-10:

- ~~`due2:witnessSource` and `evidence_param`~~ — `oval-duty-payment`, `w3c-fs-c1`, `w3c-fs-c2` (as duty-action refinements, `due2-profiles.md` §9 #6).
- ~~Grant scope and `discharges`~~, ~~`signers`~~ — `due2-grant-signers`.
- ~~`odrl:or`~~ — `force-20` (260 disjuncts, all known) and `due2-or-unknown` (Kleene, with unknowns).
- ~~`max_mixed` fallback (§6.4 beyond the bound)~~ — `due2-max-mixed` (nine facts each read both ways by an authored permission pair, `expected.exact = false`; scenario 2 sits at the bound, where only exact enumeration decides).
- ~~`perm` and `invalid` conflict strategies~~ — `oval-conflict-perm`, `oval-conflict-invalid`.
- ~~Incomparable frontier~~ — `due2-incomparable-frontier` (collapse, dominance, second approver); `config.preference` itself waits on its format (workflows §9 #3).
- ~~Requests without a target~~ — `oval-no-target-permission`, `oval-no-target-prohibition` (workflows §3.2, §5.2, decided 2026-10-11).
- ~~Canonical literals deciding a verdict~~ — `due2-xone-unknown` (an `xone` operand read both ways; workflows v0.6, §6.4).
- ~~Unknown duty guards; many conditional duties on one permission~~ — `due2-conditional-duties` (nine guarded duties, linear and exact, `decisions/0003`) and `w3c-fs-c2` scenarios 4–5.

Still open:

- **`WitnessOutsideDuty`** and the other normalisation rejections — the case format has no negative cases (expected rejection instead of a verdict). The external suites supply candidates (`external/README.md`, FORCE policies 1–7).
- **`admit_source` / `admit_age`** — a case-format gap: `sotw.facts` carries no attribution (`source`, `observed_at`), so the filter cannot be shown at work; three cases note this in `notes`. Fixing it needs a fact-attribution extension to the case format.
- **`config.preference`** — the incomparable frontier exists now, but the preference format is open (§9 #3).
- **Several policies per case** — workflows §9 #7; blocked on a case-format extension. With it, the cross-policy combinations (`combination` is still always `prohibit-overrides`).
- **Remedies and consequences** — carried by stage 1, not evaluated for access; no case until the monitoring question (§9 #4) is specified. OVAL's monitoring cases are the external material.
