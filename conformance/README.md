# due2 conformance corpus

Cases are input/expected-output pairs in the reference data model of `due2-workflows.md`. They are written to be run by an evaluator; until one exists, `tools/check_corpus.py` checks everything that can be checked without one.

```bash
python3 tools/check_corpus.py conformance/cases          # every case
python3 tools/check_corpus.py conformance/cases/<case>   # one case
```

## Layout

```
conformance/cases/<case>/
    policy.ttl     one ODRL policy, plus the operand bindings it uses
    case.json      provenance, classification, and scenarios
```

Case names start with their origin: `rl2-` for the RL2 use cases (`github.com/matthiasautrata/RL2`, `conformance/usecases/`), `dprod-` for DPROD Contracts examples (`github.com/EKGF/dprod`, `develop`, `dprod-contracts/examples/`).

## `policy.ttl`

- Exactly one policy, typed `odrl:Set`, `odrl:Offer`, `odrl:Agreement`, or a profile subclass such as `dprod:DataContract`.
- ODRL 2.2 vocabulary for everything ODRL has. Profile terms only from the extension points of `due2-profiles.md` §2, and the policy names its profiles with `odrl:profile`.
- Every rule is named (an IRI), so expected results can refer to it.
- Every left operand used is bound with `dprod:operandSource` and `dprod:operandProperty` (`due2-profiles.md` §3), either in the file or in a selected profile. Give `rdfs:range` wherever the type matters.
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
| `sotw.evidence` | `id`, `occurred_at`, `actor`, `action`, optional `object`, `issuer`, `discharges`, `params` (`due2-workflows.md` §3.3). `params` are read by `due2:witnessSource` operands in a duty's constraints (`due2-profiles.md` §3). |
| `sotw.activation` | Duty instance key or rule IRI → activation instant, for relative deadlines (`due2-profiles.md` §7). |
| `sotw.closure` | `[relation, narrower, broader]` triples, for hierarchy edges not in the policy file. |
| `config` | `combination`; optional `preference`, `signers`, `violations` (`ignore` by default, `deny` for DPROD-faithful evaluation), `admit_source`, `admit_age`. |
| `expected.verdict` | `Permit`, `Deny`, `Pending`, `NotApplicable`, or `Indeterminate`, derived by hand from `due2-workflows.md` §5–§6 and `due2-profiles.md`. |
| `expected.frontier` | For `Pending`: a list of alternatives, each a list of outstanding duty IRIs. |
| `expected.obligations` | Obligations in force for the request (`due2-workflows.md` §5.2, §6.1): `{"duty": IRI, "status": "fulfilled" \| "outstanding" \| "violated" \| "unknown"}`, plus `"instance": <occurrence instant>` for an instance of a recurring duty. Statuses follow the table in `due2-workflows.md` §6.1; include `unknown` ones too. |
| `expected.why` | The derivation in one or two sentences — which atoms applied, which were unknown, why the verdict follows. |
| `rl2_expected`, `dprod_expected` | The origin's own expected result, where it states one. A difference from `expected.verdict` is explained in `notes`. |

**Values.** A literal is `{"@value": ..., "@type": ...}`, an IRI `{"@id": ...}` — the JSON-LD forms. Prefixed names expand through `prefixes`.

**Classification.** Context built-ins (`dprod:clock`, `dprod:agent`, `due2:actionTime`), `due2:witnessSource`, and the binding properties themselves are operand-binding vocabulary, not profile terms: a case that uses only them is `odrl-core` and needs no `odrl:profile`. Profile terms are the extension points of `due2-profiles.md` §2 — `dprod:not`, `dprod:deadline`, `dprod:recurrence`, `dprod:subjectOfDuty`, policy subclasses.

**Standing divergences from RL2,** which a case need not re-explain:
- An unfulfilled precondition gives due2 `Pending` with the route, where RL2 gives `NotApplicable`.
- due2 closes `odrl:partOf` transitively; RL2 core matches only direct members.
- due2 evidence is existential: any witness fulfils a duty, so RL2's conflicting-evidence scenarios have no counterpart.
- Completion is over findings, so two permissions on complementary values of one unknown fact give `Indeterminate` (`due2-workflows.md` §6.4).

Expected results are hand-derived until an evaluator exists. The derivation in `why` is what a reviewer checks.
