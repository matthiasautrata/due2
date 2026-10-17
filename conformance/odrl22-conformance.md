# ODRL 2.2 Conformance — Protocol and Results

**Status:** Record of the 2026-10-10 conformance review
**Companions:** `odrl22-shape.ttl` (due2's SHACL encoding of the ODRL IM 2.2) · `tools/check_odrl22.py` (the harness) · `tools/check_corpus.py` (due2 admissibility) · `README.md` (corpus layout)

This document records how the claim *"due2 is a concrete, semantically sound interpretation of ODRL 2.2 — not a dialect"* is checked mechanically, what was found, and what remains open.

---

## 1. What "valid ODRL 2.2" can mean, mechanically

The ODRL 2.2 Recommendation ships **no normative SHACL file**. Its validators are defined by the Information Model's MUST requirements (IM §1.3 defines an "ODRL Validator" as checking cardinalities and the IM's validation requirements) and sketched as SHACL in the POE Working Group's validation notes (`w3.org/2016/poe/wiki/Validation`). The most complete published codification is the community shape `woutslabbinck/ODRL-shape`.

So the claim is checked in three layers, each with its own tool:

| Layer | Question | Tool |
|---|---|---|
| ODRL 2.2 structural validity | Is the corpus standard ODRL, as written? | `conformance/odrl22-shape.ttl` via `tools/check_odrl22.py` (pyshacl) |
| due2 admissibility | Is the corpus admissible W1 input (constructs due2 rejects are diagnosed, never approximated)? | `tools/check_corpus.py` |
| Semantic soundness | Does due2's evaluation mean what ODRL says? | `due2-workflows.md` §5–§6, the `Den` preservation obligation, and the corpus's hand-derived expected verdicts |

SHACL covers the first layer only. It certifies that due2's policies are standard ODRL, not a dialect; semantic soundness rests on the specs and the corpus, which is where it always rested.

## 2. Why due2 has its own shape

The community shape was run over the full corpus first (70 files: 66 case policies + 4 vendored DPROD example files, 16 policies). Result: **0/70 conform as published** — and every failure family was the shape disagreeing with the Rec it encodes, not the corpus:

| Shape behaviour | The Rec's actual text |
|---|---|
| `odrl:rightOperand maxCount 1`; list values fail the `sh:or` | IM §2.5.1: the rightOperand is "a literal, or IRI, or RightOperand; **or for set-based operators; list** of literals, or list of IRIs, or list of RightOperands". The list form is the IM's own encoding, used by the corpus with `isAnyOf`, `isNoneOf`, and `isPartOf`. |
| Logical-constraint operands must be Constraint-typed nodes; RDF lists fail | IM §2.5.2: the operand value "is a **list** of the existing Constraint instances". The POE WG's own sketch walks `rdf:rest`/`rdf:first`; the community shape validates only the repeated-object form its own example uses. |
| A Policy needs one of `permission`/`prohibition`/`duty` | IM §2.1: "at least one `permission`, `prohibition`, or **`obligation`**". `odrl:duty` is a Permission→Duty edge, not a Policy property. Obligation-only policies are valid ODRL; four corpus cases are. |
| `odrl:uid minCount 1` as an explicit triple | The IM maps uid to the JSON-LD `@id`: in RDF the node IRI **is** the uid. The check fails every RDF policy, including the W3C's own examples. |

With exactly the transformations the Rec itself defines — IM §2.7.1 compact-form replication ("Verify… Replicate… Remove"), uid-as-IRI — plus corrections for the four items above, the community shape passes 70/70. None of the corrections is due2-specific: two were needed by DPROD's own vendored examples.

Rather than carry a fork of someone else's shape, due2 ships its own: **`conformance/odrl22-shape.ttl`**, every constraint cited to its IM section. It validates the *authored* form natively — compact policies (§2.7.1), compound repetition (§2.7 note), list-valued set operands (§2.5.1), list-form logical constraints (§2.5.2), obligation-only policies (§2.1) — and recognises profile extensions at the points the IM declares: the `dprod:not` connective (§2.5.2: "Additional operand sub-properties MAY be defined by ODRL Profiles") and profile policy subclasses (§2.1).

The IM ties list-valued right operands to "set-based operators"; the Vocabulary enumerates them (§3.16.7–3.16.12: `isA`, `hasPart`, `isPartOf`, `isAllOf`, `isAnyOf`, `isNoneOf`) and repeats the rule (§3.14.7). The shape admits lists for exactly those six.

**Erratum (2026-10-11).** Until then this section called the set-based operators unenumerated and the shape admitted lists only for `isAnyOf`, `isNoneOf`, and `isAllOf`, `due2-profiles.md` §4's reading at the time. That was wrong: the Vocabulary enumerates them, and the shape rejected valid ODRL 2.2. Shape and §4 are fixed. What a list *means* for `isPartOf`, `hasPart`, and `isA` is a separate question that ODRL does not answer and the published semantics answer differently; due2 adopts Salas and Pareti et al.'s reading and warns (`ContestedOperatorReading`) wherever it applies (`decisions/0005`). `isPartOf` with a list is tested by `oval-list-right-operand`.

**Repeated values (2026-10-17).** Many authors write a set right operand as repeated values, `odrl:rightOperand ex:a, ex:b`, not as one list. IM §2.5.1 gives a Constraint "one rightOperand property value", but Vocabulary §5.1 makes the list a SHOULD ("the rdf:List predicate SHOULD be used"), and the ODRL JSON-LD context maps `rightOperand` without `@container: @list`, so a JSON array expands to repeated values. The shape accepts them on the six set-based operators, and rejects repeated values on any other operator and a list together with any other value (`decisions/0013`). Until then it accepted every repeated form silently, `eq ex:a, ex:b` included. `due2-repeated-right-operand` tests the accepted form and `due2-malformed-right-operand` the rejected ones.

## 3. Results (2026-10-10)

```text
python3 tools/check_odrl22.py --all
70 checked, 0 failing        # 66 corpus policies + 4 vendored DPROD files
```

Zero structural ODRL 2.2 violations across the whole corpus and DPROD's own examples. `check_corpus.py` stays green (66 checked, 0 failing; the 16 vendored DPROD policies separately: 0 failing).

The review found and fixed one real blemish, plus one hygiene gap:

1. **37 corpus policies used DPROD- or due2-vocabulary terms without declaring `odrl:profile`** (IM §2.1: use only Core terms, or declare the profiles whose terms you use — and "the profile property MUST be used to indicate the IRIs"). All 37 now declare `<https://ekgf.org/dprod/spec/develop/>` and/or `<https://w3id.org/due2/profile#>`. This is not cosmetic: normalisation selects a profile's binding module by `odrl:profile` (normalisation spec §3), so an undeclared namespace would silently lose its bindings.
2. **`check_corpus.py` now rejects undeclared namespaces** as a W1 input error, and `check_odrl22.py` checks the same rule against the IM, so the corpus cannot regress. Note the distinction recorded in `conformance/README.md`: *classification* (which due2 extension points a case needs) is separate from *declaration* (which vocabulary namespaces appear in the policy). A case can classify `odrl-core` and still need the DPROD profile declaration, because operand bindings are DPROD-vocabulary terms.

## 4. What this does not establish

- **Semantic fidelity is not SHACL-checkable.** The shape proves the corpus is grammatical ODRL 2.2; the meaning of due2's evaluation is established by `due2-workflows.md` §5–§6, the preservation obligation, and the corpus's hand-derived verdicts.
- **due2 deliberately rejects some valid ODRL** (`andSequence`, `rightOperandReference`, `inheritFrom`, `implies`, collection `odrl:refinement`, floating-point operands; a refinement-free `odrl:source` on a collection is admitted as inert since 2026-10-11, §5) — rejected at normalisation with diagnostics, never accepted and approximated (architecture §1). The shape validates ODRL as written and so admits them; `check_corpus.py` draws the due2 line. Subsetting is what the ODRL profile mechanism is for; a profile that declares its supported subset is not a dialect.
- **The collection-refinement rules are encoded but unexercised.** The shape implements IM §2.5.5/§2.5.6 (a refined `AssetCollection`/`PartyCollection` MUST be referenced via `odrl:source`); no corpus policy uses collection refinements, so the constraint is untested against live data.

## 5. `odrl:source` admitted; collection refinements deferred

IM §2.5.5–2.5.6 make `odrl:source` load-bearing: a refined collection is *referenced through* its source (a query defining the membership), and `uid` "MUST NOT be used to identify" the collection. due2 currently rejects `odrl:source` and collection `odrl:refinement` outright (`due2-profiles.md` §8.1: "rejected — so does DPROD"), reading collections closed-world over declared membership edges (§6).

Whether due2 should admit collection refinements — party collections especially, where "the requester's department" wants a refinement-shaped encoding — is **registered for discussion**; it touches W2's matching (the refinement would have to be evaluated per member) and the SOTW's closure story. Until decided, the shape keeps the IM's rule on the books and the corpus stays away from the construct.

**Decided 2026-10-11 (issue #21, first half).** FORCE's collection policies (16–18, 21) use `odrl:source` *without* a refinement: it names the collection, and membership comes from `odrl:partOf` edges in the state of the world. Under due2's closure reading that form is inert, so due2 admits it as an annotation (`due2-profiles.md` §8.1). `force-16` … `force-21` now carry it as written, with unchanged verdicts. Collection *refinements* stay rejected and open (#21). The trigger is MDS external contracts that need refined membership; the interim answer is for the mapper to materialise the refined member set as closure edges. That covers everything except request-relative refinements ("the requester's department"), the residual that would force the spec work. `check_corpus.py` now enforces the line on asset and party nodes, which it did not check before 2026-10-11.

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

## 6. Reproducing

```bash
uv run python tools/check_odrl22.py --all                 # ODRL 2.2 validity, due2's shape
uv run python tools/check_corpus.py conformance/cases    # due2 admissibility
uv run python tools/check_corpus.py profiles/vendor/dprod/examples/*.ttl
```

Dependencies managed via `uv` (`pyproject.toml`, Python 3.14+): `rdflib`, `pyshacl`. The official ODRL 2.2 vocabulary is vendored at `profiles/vendor/w3c/ODRL22.ttl`; refresh only by re-downloading from the header's URL.
