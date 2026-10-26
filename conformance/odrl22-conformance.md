# ODRL 2.2 Conformance — Protocol and Results

**Status:** Reference: the protocol, what the checkers check, and the latest results. The earlier results, and the corrections that led to the current checks, are in `docs/archive/odrl22-conformance-log.md`.
**Companions:** `odrl22-shape.ttl` (due2's SHACL encoding of the ODRL IM 2.2) · `tools/check_odrl22.py` (the harness) · `tools/check_corpus.py` (due2 admissibility) · `README.md` (corpus layout)

This document records how the claim *"due2 is a concrete, semantically sound interpretation of ODRL 2.2 — not a dialect"* is checked mechanically, what the checks find, and what remains open.

---

## 1. What "valid ODRL 2.2" can mean, mechanically

The ODRL 2.2 Recommendation ships **no normative SHACL file**. Its validators are defined by the Information Model's MUST requirements (IM §1.3 defines an "ODRL Validator" as checking cardinalities and the IM's validation requirements) and sketched as SHACL in the POE Working Group's validation notes (`w3.org/2016/poe/wiki/Validation`). The most complete published codification is the community shape `woutslabbinck/ODRL-shape`.

So the claim is checked in three layers, each with its own tool:

| Layer | Question | Tool |
|---|---|---|
| ODRL 2.2 structural validity | Is the corpus standard ODRL, as written? | `conformance/odrl22-shape.ttl` via `tools/check_odrl22.py` (pyshacl) |
| due2 admissibility | Is the corpus admissible W1 input (constructs due2 rejects are diagnosed, never approximated)? | `tools/check_corpus.py` |
| Semantic soundness | Does due2's evaluation mean what ODRL says? | `due2-workflows.md` §5–§6, the `Den` preservation obligation, and the corpus's hand-derived expected verdicts |

SHACL covers the first layer only. A policy that passes the shape meets the IM requirements the shape encodes, each cited to its IM section (§2). This does not show that the policy meets every IM requirement (§5), or that each of its literals names a value of its datatype, which the checkers test instead (#125). Semantic soundness rests on the specs and the corpus, which is where it always rested.

## 2. Why due2 has its own shape

The community shape was run over the full corpus first (70 files: 66 case policies + 4 vendored DPROD example files, 16 policies). Result: **0/70 conform as published** — and every failure family was the shape disagreeing with the Rec it encodes, not the corpus:

| Shape behaviour | The Rec's actual text |
|---|---|
| `odrl:rightOperand maxCount 1`; list values fail the `sh:or` | IM §2.5.1: the rightOperand is "a literal, or IRI, or RightOperand; **or for set-based operators; list** of literals, or list of IRIs, or list of RightOperands". The list form is the IM's own encoding, used by the corpus with `isAnyOf`, `isNoneOf`, and `isPartOf`. |
| Logical-constraint operands must be Constraint-typed nodes; RDF lists fail | IM §2.5.2: the operand value "is a **list** of the existing Constraint instances". The POE WG's own sketch walks `rdf:rest`/`rdf:first`; the community shape validates only the repeated-object form its own example uses. |
| A Policy needs one of `permission`/`prohibition`/`duty` | IM §2.1: "at least one `permission`, `prohibition`, or **`obligation`**". `odrl:duty` is a Permission→Duty edge, not a Policy property. Obligation-only policies are valid ODRL; four corpus cases are. |
| `odrl:uid minCount 1` as an explicit triple | The IM maps uid to the JSON-LD `@id`: in RDF the node IRI **is** the uid. The check fails every RDF policy, including the W3C's own examples. |

With exactly the transformations the Rec itself defines — IM §2.7.1 compact-form replication ("Verify… Replicate… Remove"), uid-as-IRI — plus corrections for the four items above, the community shape passes 70/70. None of the corrections is due2-specific: two were needed by DPROD's own vendored examples.

Rather than carry a fork of someone else's shape, due2 ships its own: **`conformance/odrl22-shape.ttl`**, every constraint cited to its IM section. It validates the *authored* form natively — compact policies (IM §2.7.1), compound repetition (IM §2.7 note), list-valued set operands (IM §2.5.1), list-form logical constraints (IM §2.5.2), obligation-only policies (IM §2.1) — and recognises profile extensions at the points the IM declares: the `dprod:not` connective (IM §2.5.2: "Additional operand sub-properties MAY be defined by ODRL Profiles") and profile policy subclasses (IM §2.1).

**Set-based operators.** The IM ties list-valued right operands to "set-based operators"; the Vocabulary enumerates them (Vocabulary §3.16.7–3.16.12: `isA`, `hasPart`, `isPartOf`, `isAllOf`, `isAnyOf`, `isNoneOf`) and repeats the rule (Vocabulary §3.14.7). The shape admits lists for exactly those six. What a list *means* for `isPartOf`, `hasPart`, and `isA` is a separate question that ODRL does not answer and the published semantics answer differently; due2 adopts Salas and Pareti et al.'s reading and warns (`ContestedOperatorReading`) wherever it applies (`decisions/0005`). `isPartOf` with a list is tested by `oval-list-right-operand`. **Erratum (2026-10-11):** until then the shape admitted lists only for `isAnyOf`, `isNoneOf`, and `isAllOf`, and so rejected valid ODRL 2.2; the account is in `docs/archive/odrl22-conformance-log.md`.

**Repeated values.** Many authors write a set right operand as repeated values, `odrl:rightOperand ex:a, ex:b`, not as one list. IM §2.5.1 gives a Constraint "one rightOperand property value", but Vocabulary §5.1 makes the list a SHOULD ("the rdf:List predicate SHOULD be used"), and the ODRL JSON-LD context maps `rightOperand` without `@container: @list`, so a JSON array expands to repeated values. The shape accepts them on the six set-based operators, and rejects repeated values on any other operator and a list together with any other value (`decisions/0013`). `due2-repeated-right-operand` tests the accepted form and `due2-malformed-right-operand` the rejected ones.

**Anonymous targets.** IM §2.6.1 asks for a target "of type Asset", and IM §2.2 says an Asset SHOULD have a uid, so an anonymous target is valid ODRL 2.2, and the shape admits a blank node there. due2 admits it with the `AnonymousEntity` warning, because no request can name it (`odrl-compound-to-atomic-normalization.md` §3, #79). `due2-anonymous-target` tests it.

## 3. What the checkers check

Beyond the shape's structure, both checkers apply the rules below. Each names the IM or Vocabulary section it encodes, the decision that settles it, and the cases that pin it. `check_odrl22.py` checks ODRL 2.2 validity, and `check_corpus.py` checks W1 admissibility, which also rejects the valid constructs of §5.

1. **Every term is defined (IM §2.1, `decisions/0020`).** A term in a vocabulary position — an action, left operand, operator, function, relation, or conflict value — is an `odrl:` term of the ODRL vocabulary, a term of a declared profile's modules, or a term the policy types itself. This departs from the IM's letter in two ways: Common Vocabulary terms such as `odrl:purpose` need no profile, as in the W3C's own examples, and a term the policy types itself needs none, as in the `rl2-*` cases. It is stricter than `profiles/vendor/w3c/ODRL22.ttl` in one: the file's nine `cc:` actions need a profile (`decisions/0020` #4). The declaration is not cosmetic: normalisation selects a profile's binding module by `odrl:profile` (`odrl-compound-to-atomic-normalization.md` §3), so an undeclared namespace would silently lose its bindings. *Declaration* (which vocabulary namespaces appear in the policy) is separate from *classification* (which due2 extension points a case needs, `conformance/README.md`): a case can classify `odrl-core` and still need the DPROD profile declaration, because operand bindings are DPROD-vocabulary terms. Negative cases: `due2-undeclared-action`, `due2-undeclared-cc-action`.
2. **Assets and Parties are resources (IM §2.2, §2.3, §2.6; `decisions/0034` item 2).** The value of a target, an output, or any `rdfs:subPropertyOf` descendant of `odrl:function` or `odrl:relation` is a resource, never a literal (`LiteralEntity`). The checkers read those descendants from the vocabularies, so a profile's own, such as `dprod:subjectOfDuty`, is covered without a list to keep. `dprod:agent` has range `odrl:Party` but is a sub-property of neither, and stays outside the check: it is a property of DPROD's `EvaluationContext`, which describes a request, not a policy. Negative cases: `due2-literal-party`, `due2-literal-bearer`.
3. **A logical constraint has exactly one operand property (IM §2.5.2; `MalformedConstraint`).** Negative case: `due2-and-or`.
4. **Constraints and Rules sit where the vocabulary places them (Vocabulary §3.9.2, §3.10.2, §3.13.2–§3.13.5, §3.14.2, §3.14.3; IM §2.6.3, §2.6.7).** A node with an `odrl:constraint` is the Policy or a Rule. `odrl:refinement` sits on an Action or a collection. `permission`, `prohibition`, and `obligation` have the Policy as subject, `duty` a Permission, `remedy` a Prohibition, and `consequence` a Duty; a Duty reached by `remedy` or `consequence` carries no `consequence`. The IM defines Party and Rule as separate classes (IM §2.3, §2.6), so a constraint on a Party is misplaced, including one that only a profile's function such as `dprod:subjectOfDuty` names. `check_corpus.py` rejects a misplacement as `MisplacedConstraint` or `InvalidNesting` (`odrl-compound-to-atomic-normalization.md` §3), and an `odrl:constraint` on the Policy, which the vocabulary allows but the IM gives no meaning, as `UnsupportedConstruct`; the shape admits that one. For `odrl:refinement` the shape tests that a Policy or a Rule holds none, not the domain itself, because a domain test would need the Asset or Party type of every value of a function or relation sub-property, and the range types `check_odrl22.py` adds cover only the ODRL ones. Negative cases: `oval-refinement-on-duty`, `oval-refinement-on-policy`, `oval-constraint-on-action`, `oval-constraint-on-collection`, `oval-prohibition-in-permission`, `oval-remedy-on-duty`, `oval-consequence-on-permission`, `due2-policy-constraint`, `due2-constrained-bearer`.
5. **Every action reaches `odrl:use` or `odrl:transfer` (IM §2.4; `decisions/0034`).** Every other action has exactly one `odrl:includedIn`, of type Action, on a path that reaches one of the two (`InvalidActionHierarchy`). A corpus action whose source gives no parent states `odrl:includedIn odrl:use`, the broadest action. DPROD's examples `baseline.ttl` and `odcs.ttl` define `ex:conformTo` without one: they stay vendored unmodified, both checkers list them as expected to fail, and the omission is reported upstream (EKGF/dprod#286). Negative cases: `due2-action-without-parent`, `due2-action-two-parents`.
6. **A refined action is its `rdf:value`, whatever its node kind (IM §2.5.4; `decisions/0034`, amendment).** The IM does not say the node is blank, so a policy translated from JSON-LD with its node names kept, such as `w3c-fs-c1` and `w3c-fs-c2`, is checked through its `rdf:value`. A blank action without one names no action, and fails. Cases: `due2-refined-action-skolem`, a refined action named by a skolem IRI and typed `odrl:Action`, and the negative case `due2-action-without-value`.
7. **`odrl:rightOperandReference` follows `decisions/0013` (IM §2.5.1).** The shape applies the rule on repeated and list values to it; W1 rejects it outright. Negative case: `due2-two-right-operand-references`.
8. **Inverse forms are inferred before validation.** `check_odrl22.py` applies IM §2.2.3 (an asset's `odrl:hasPolicy` makes it the target of every Rule of the policy) and IM §2.3.3 (a party's `odrl:assignerOf` or `odrl:assigneeOf` makes it the assigner or assignee of the policy's Rules), so these forms are valid ODRL 2.2. W1 rejects them with `UnsupportedConstruct`. Negative cases: `due2-has-policy`, `due2-assigner-of`, `due2-assignee-of`.
9. **Entailed types are added before validation.** The shape tests rule and constraint values by `sh:class`, so an untyped rule node — `odrl:permission [ … ]`, the style of the IM's own Turtle examples — would fail `sh:class odrl:Permission` and escape `PermissionShape`, leaving its required target unchecked. `check_odrl22.py` therefore adds the types the ODRL 2.2 vocabulary entails: rdfs:range of `permission`, `prohibition`, `obligation`, `duty`, `remedy`, `consequence`, `action`, `target`, `assignee`, and `assigner`; rdfs:domain of `leftOperand`; and Logical Constraint for a node with a connective. rdfs:range of `leftOperand` is deliberately not applied, because it would make IM §2.5.1's "MUST be a LeftOperand" vacuous.

## 4. Results

At `57f18bc`, the corpus and the vendored DPROD examples:

```text
uv run python tools/check_odrl22.py --all
169 checked, 0 failing, 29 invalid as expected
```

The 29 "invalid as expected" are the 27 negative cases whose `case.json` says `"odrl22_valid": false` (`conformance/README.md`), FORCE policies 1–7 among them, and DPROD's `baseline.ttl` and `odcs.ttl` (item 5); the harness fails if one of them conforms.

The suites of other evaluators, vendored under `conformance/external/`:

| Suite | Checked | Failing | Why |
|---|---|---|---|
| FORCE policies | 21 | 7 | Policies 1–7 have no target, and 1–2 no action |
| OVAL policies (`access_control`, `monitoring_*`) | 122 | 51 | Undeclared left operands 47, unit as string 4 |
| OVAL `validation/valid_ODRL` | 36 | 9 | Unit as string 6, undefined terms 3, IM §2.1.2–2.1.3 read as one assigner per policy 2 |
| OVAL `validation/invalid_ODRL` | 25 | 25 | All rejected, as their suite expects |

The failures are upstream IM violations. A file can fail for more than one reason, so the reasons can sum to more than the count. `conformance/external/README.md` § Triage of what was not translated gives the readings.

## 5. What this does not establish

- **Semantic fidelity is not SHACL-checkable.** The shape establishes that the corpus meets the IM requirements it cites; the meaning of due2's evaluation is established by `due2-workflows.md` §5–§6, the preservation obligation, and the corpus's hand-derived verdicts.
- **The shape checks only the IM requirements it cites.** Each constraint that encodes an IM requirement names its section, and `rg 'IM §?[0-9]' conformance/odrl22-shape.ttl` lists them. A requirement that no constraint cites is unchecked. Every gap found so far was such a requirement (`docs/archive/odrl22-conformance-log.md`), so a policy that passes the shape is valid ODRL 2.2 only as far as these sections reach.
- **due2 deliberately rejects some valid ODRL** (`andSequence`, `rightOperandReference`, `inheritFrom`, `implies`, `hasPolicy`, `assignerOf`, `assigneeOf`, collection `odrl:refinement`, floating-point operands; a refinement-free `odrl:source` on a collection is admitted as inert, §6) — rejected at normalisation with diagnostics, never accepted and approximated (`due2-architecture.md` §1). The shape validates ODRL as written and so admits them; `check_corpus.py` draws the due2 line. Subsetting is what the ODRL profile mechanism is for; a profile that declares its supported subset is not a dialect.
- **The collection-refinement rules are encoded but unexercised.** The shape implements IM §2.5.5/§2.5.6 (a refined `AssetCollection`/`PartyCollection` MUST be referenced via `odrl:source`); no corpus policy uses collection refinements, so the constraint is untested against live data.

## 6. `odrl:source` admitted; collection refinements rejected

IM §2.5.5–2.5.6 make `odrl:source` load-bearing: a refined collection is *referenced through* its source (a query defining the membership), and `uid` "MUST NOT be used to identify" the collection. due2 reads collections closed-world, over the membership edges the SOTW declares (`due2-profiles.md` §6).

A collection's `odrl:source` without a refinement is admitted as an annotation (`due2-profiles.md` §8.1). It names the collection; membership still comes from `odrl:partOf` edges, so under the closed-world reading the source is inert. FORCE's collection policies (16–18, 21) use this form, and `force-16` … `force-21` carry it as written, with the verdicts they had without it. `check_corpus.py` enforces the line on asset and party nodes.

A collection `odrl:refinement` is rejected, with or without a source, as DPROD rejects it. Whether to admit it is open (#21). It touches W2's matching, because the refinement would be evaluated per member, and the SOTW's closure. Whoever assembles the policy can instead supply the refined member set as closure edges. That covers every refinement except a request-relative one, such as "the requester's department", which is the case that would need the spec work. The shape keeps the IM's rule, and no corpus policy uses a collection refinement (§5).

## 7. Reproducing

```bash
uv run python tools/check_odrl22.py --all                 # ODRL 2.2 validity, due2's shape
uv run python tools/check_corpus.py conformance/cases    # due2 admissibility
uv run python tools/check_corpus.py profiles/vendor/dprod/examples/*.ttl
```

The external suites are checked by passing their policy files: for OVAL, the `.ttl` files of `access_control/` and `monitoring_*`, and the `.ttl` and `.jsonld` files of each `validation/` directory; for FORCE, `policies/*.ttl`.

Dependencies managed via `uv` (`pyproject.toml`, Python 3.14+): `rdflib`, `pyshacl`. The official ODRL 2.2 vocabulary is vendored at `profiles/vendor/w3c/ODRL22.ttl`; refresh only by re-downloading from the header's URL.
