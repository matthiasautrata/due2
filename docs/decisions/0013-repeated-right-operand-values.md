# 0013 — Repeated right-operand values are the same set as a list

**Status:** Decided, 2026-10-17
**Context documents:** `due2-profiles.md` §4 · `due2-diagnostics.md` §3 · `odrl22-conformance.md` §2 · `conformance/odrl22-shape.ttl` · `decisions/0005` · issue #64

## Question

A set-based operator (`isA`, `hasPart`, `isPartOf`, `isAllOf`, `isAnyOf`, `isNoneOf`; ODRL Vocabulary §3.16.7–3.16.12) takes a list right operand. ODRL IM §2.5.1 writes it as one value that is a list:

```turtle
odrl:operator odrl:isAnyOf ; odrl:rightOperand ( ex:a ex:b ex:c ) .
```

Many authors write repeated values instead, one triple per value. Authors of market-data-services ODRL are among them:

```turtle
odrl:operator odrl:isAnyOf ; odrl:rightOperand ex:a, ex:b, ex:c .
```

Should due2 admit the second form, and what does it mean?

## What ODRL says

The sources do not agree:

| Source | Says | Favours |
|---|---|---|
| ODRL IM §2.5.1 | a Constraint MUST have "one rightOperand property value of type … for set-based operators; list of literals, or list of IRIs, or list of RightOperands" | one value that is a list |
| ODRL Vocabulary §5.1 | "When a list of values is required, then the rdf:List predicate SHOULD be used." | the list, as a SHOULD, not a MUST |
| ODRL Vocabulary §3.14.7 and `profiles/vendor/w3c/ODRL22.ttl` | `odrl:rightOperand` is an `owl:DatatypeProperty` with range `RightOperand ∪ rdfs:Literal ∪ xsd:anyURI`, and it is not declared functional | neither: an `rdf:List` is outside the declared range, and nothing limits the number of values |
| The ODRL JSON-LD context, `http://www.w3.org/ns/odrl.jsonld` | `"rightOperand": "odrl:rightOperand"`, with no `"@container": "@list"` | repeated values: a JSON array expands to one triple per member |

The last row matters most in practice. The IM's examples are JSON-LD, and the Vocabulary tells producers to use this context (§5.2). Under it, `"rightOperand": ["a", "b", "c"]` is the repeated form. An author gets the IM's list only by writing `{"@list": ["a", "b", "c"]}`. The IM knows this: its note to §2.5.2 says that for `andSequence` "the @list keyword MUST be used to represent an ordered collection", because a plain array is not one. So the repeated form is what the standard's own JSON-LD serialisation produces from the obvious JSON. It is not an authoring mistake.

due2 already accepts both forms for the operands of a logical constraint (`odrl22-conformance.md` §2; `odrl22-shape.ttl`, LogicalConstraintShape). Until this record it also accepted both for right operands, silently: the spec stated no reading, and the checkers also passed `eq ex:a, ex:b`, which has none. One corpus case, `rl2-multi-certification`, uses the repeated form with `isAllOf`.

## Decision

1. **On a set-based operator, repeated values are the same right operand as a list of them.** The right operand is the set of its values, whichever form the author used. Both forms give the same `constraint_value` tuples (`due2-workflows.md` §3), so nothing after normalisation can tell them apart. Two premises make this exact, not approximate. None of the six operators depends on the order of the right operand (`due2-profiles.md` §4: each is membership, cover, or inclusion). None depends on repeats either, because a list's repeated member adds no element to the set, and RDF has no repeated triples to lose.
2. **No warning.** The two forms mean the same thing, so there is no reading to make visible. This differs from `decisions/0005`, where a list on `isPartOf`, `hasPart`, or `isA` has a contested meaning. `ContestedOperatorReading` still applies there, to more than one value in either form.
3. **Three forms have no reading, and are rejected with `MalformedConstraint`:**
   - more than one value on an operator that is not set-based, such as `eq ex:a, ex:b`. IM §2.5.1 gives such a constraint one value, and no operator in `due2-profiles.md` §4 compares against several;
   - a list together with any other value, such as `( ex:a ex:b ), ex:c`;
   - two or more lists. Their union, or a set of sets, would both be guesses.
4. **The ODRL 2.2 shape follows.** `odrl22-shape.ttl` accepts repeated values on the six set-based operators, since the Vocabulary's §5.1 is a SHOULD and the official JSON-LD context produces them. It rejects the three forms of #3, since the IM gives none of them a meaning.

## Rejected

- **Reject the repeated form, as IM §2.5.1's "one … value" reads in RDF.** That refuses what the official JSON-LD context makes of an ordinary array, and what authors in the field write, although its meaning is not in doubt.
- **Accept it with a warning.** A warning says that due2 made a choice the author should see. Here there is none, and the warning would sit in the trace of every such policy as noise.
- **Normalise the repeated form into a list in stage 1.** That would invent list cells and an order the author never wrote. `odrl-compound-to-atomic-normalization.md` keeps the authored structure, and `constraint_value` is a set already.

## Consequences

- `due2-profiles.md` §4 states #1 to #3, `due2-diagnostics.md` §3 widens `MalformedConstraint`, and `due2-workflows.md` §3 says that `constraint_value` does not depend on the form.
- `tools/check_corpus.py` and `odrl22-shape.ttl` implement #3 and #4.
- Corpus case `due2-repeated-right-operand` pins #1 and the equivalence of the two forms. The negative case `due2-malformed-right-operand` pins #3.
- clingo-i's flatten reads both forms when it learns constraints (#47).

## Revisit when

- The ODRL WG or CG changes the JSON-LD context to `@list`, or states that the repeated form is invalid.

## Amendment (2026-10-17, the empty list)

A fourth form has no reading: the empty list, `odrl:rightOperand ()`, as the right operand of a set-based operator. In RDF, `()` is the IRI `rdf:nil`. Normalisation rejects it with `MalformedConstraint`, as it does the three forms of item 3 of § Decision (#69).

ODRL gives the empty list no meaning. IM §2.5.1 asks a set-based operator for a "list of literals, or list of IRIs, or list of RightOperands". The Vocabulary describes a list of values (§3.14.7, §3.16.7–§3.16.12), and asks only that `rdf:List` SHOULD be used (§5.1). None of them, nor `ODRL22.ttl`, nor the Community Group's formal semantics draft, mentions an empty list or an empty set. Read as the empty set, each operator gives an answer that does not depend on the request at all:

| Operator | On the empty set |
|---|---|
| `isAnyOf` | `F`: no member to match |
| `isNoneOf` | `T`: no member to exclude |
| `isAllOf`, `hasPart`, `isA` | `T`, vacuously |
| `isPartOf` | `F`, unless the left value is itself empty |

A constraint like this decides nothing about the request, so it is more likely an authoring error, such as a generator that emptied a list, than an intent. It can also do harm without any sign: a prohibition on `isNoneOf ()` applies to every request. Rejecting it shows the author the error instead.

The other serialisations agree. In JSON-LD, `"rightOperand": []` gives no triple, so the constraint has no right operand and is already rejected. `{"@list": []}` gives `rdf:nil`, which this amendment rejects.

`odrl22-shape.ttl` keeps accepting the empty list, since it is an IRI and the IM does not require a list to have members. So the rejection is due2's own, as `WitnessOutsideDuty` is, and the negative case `due2-empty-right-operand` keeps `odrl22_valid` at its default. `due2-profiles.md` v0.11 §4, `due2-diagnostics.md` v0.4 §3, and `tools/check_corpus.py` follow.
