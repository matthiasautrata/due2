# 0014 — An operand's type belongs to the layer that declares it

**Status:** Decided, 2026-10-17
**Context documents:** `due2-profiles.md` §2, §3, §4 · `due2-diagnostics.md` §3 · `profiles/due2-core.ttl` · `profiles/vendor/dprod/shapes/dprod-contracts-shapes.ttl` · issues #65, #67

## Question

A left operand's binding (`due2-profiles.md` §3) says where its value comes from and what the value must be:

```turtle
odrl:payAmount
    dprod:operandSource due2:witnessSource ;   # where: the source
    dprod:operandProperty odrl:payAmount ;     # where: the property read
    rdfs:range xsd:decimal ;                   # what: the type attributes
    due2:cardinality due2:one ;
    due2:allowedOperator odrl:gteq, odrl:lteq .
```

Bindings resolve through three layers: the policy graph, the selected profile modules, and due2's baseline `profiles/due2-core.ttl` (`due2-profiles.md` §2). A higher layer may rebind a lower one's operand. Up to v0.7 that section said nothing about which attributes a rebinding may change, and it ordered the profile modules by "`odrl:profile` declaration order". Three questions follow:

1. When several layers state attributes of one operand, which apply?
2. Should a binding's range be checked against the range of the property it reads?
3. With no range, how are values compared (#65)?

## What the sources say

**ODRL** declares left operands as individuals of `odrl:LeftOperand` and gives them no type: no range, no cardinality, no operator restriction (`profiles/vendor/w3c/ODRL22.ttl`, `odrl:LeftOperand`, and the operand individuals that follow it). Typing is left to profiles.

**DPROD** has one binding per operand and no layers. `LeftOperandShape` (`dprod-contracts-shapes.ttl`, commit `50db943`) requires exactly one `dprod:operandSource` and exactly one `dprod:operandProperty` on every left operand, and exempts the two operands DPROD binds itself, `dprod:currentAgent` and `odrl:dateTime`. A binding's `rdfs:range` types the value read: a value outside it is a `TypeMismatch` (`formal-semantics.md` §6.2). DPROD does not check the right operand against the range, and gives `false` for incomparable values (`due2-profiles.md` §8.2, exception 1). It declares ranges on its context properties: `dprod:clock` is an `xsd:dateTime` and `dprod:agent` an `odrl:Party` (`dprod-contracts.ttl`).

**due2's two implementations disagreed.** `tools/check_corpus.py` (`Bindings.attr`) takes each attribute from the highest layer that states it, so a policy could change a baseline operand's range by stating its own. clingo-i (`spikes/clingo-i/DESIGN.md` § Binding) takes the whole declaration from the highest layer that states a source or property, so a range stated in a lower layer was lost. It declines two profile modules that both bind an operand, because the order of `odrl:profile` values is not in the RDF: repeated values are a set (`decisions/0013`).

## Decision

1. **The type belongs to the lowest declaring layer.** A layer *declares* an operand when it states any of its binding attributes: `dprod:operandSource`, `dprod:operandProperty`, `rdfs:range`, `due2:cardinality`, or `due2:allowedOperator`. The lowest layer that declares the operand *owns* its type attributes: range, cardinality, and allowed operators. An attribute the owner omits takes the default of `due2-profiles.md` §3, and that default is as fixed as a stated value. `decisions/0049` #1 adds `due2:unit` to both lists: it declares the operand, and it is a type attribute.
2. **Higher layers may rebind the source and the property, never the type.** The source and the property come from the highest layer that states them, so DPROD's binding of `odrl:dateTime` to `dprod:clock` still replaces the baseline's `due2:actionTime`. A higher layer may restate a type attribute only with the owner's value. Any other value is rejected with `RetypedOperand`. A higher layer that omits a type attribute does not restate it.
3. **The profile modules form one layer, without order.** Two selected modules that state an attribute of the same operand with different values are rejected with `ConflictingProfileDeclaration`. The phrase "in `odrl:profile` declaration order" is deleted from `due2-profiles.md` §2.
4. **Values have kinds.** All XSD numeric datatypes are one kind. Every other XSD primitive datatype is a kind, and a derived datatype has its primitive's kind (XSD 1.1 Part 2 §2.4.2, §3.3–3.4), so `xsd:dateTimeStamp` is a `dateTime` and `xsd:dayTimeDuration` a `duration`. Any datatype outside XSD, `rdf:langString` included, is a kind of its own. All IRIs are one kind, whatever class they belong to. A range has the kind of its values; a class range has the IRI kind; an absent range has no kind and admits every value.
5. **A binding's range must agree with the read property's.** When the read property has an `rdfs:range` in a loaded layer, and both ranges have a kind, the two kinds must be the same. If they differ, the policy is rejected with `OperandRangeMismatch`. In practice the check applies to the context properties: `dprod:clock` and `due2:actionTime` are `xsd:dateTime`, and `dprod:agent` is an IRI.
6. **With no range, values compare by value within a kind (#65, alternative 1).** `"1"^^xsd:integer` equals `"1.0"^^xsd:decimal`. A left value whose kind differs from the right operand's, such as an IRI against a literal, does not fit the operator. It is `invalid`, so the constraint is `U` (`due2-profiles.md` §4). "Compared by identity" in v0.7's §3 *Defaults* meant only that no datatype is required, and is reworded.

**What the checks leave out**, deliberately: class subsumption and disjointness (two class ranges always agree); custom datatypes and their facets; coercion between kinds, so `date` never meets `dateTime`; unit conversion, which is the assembler's job (`due2-profiles.md` §3, *One hop*); and the schemas of request and state producers, which due2 does not load. These checks only reject. Everything they let through is still checked against the value at evaluation, where a misfit is `TypeMismatch`, so `U`. A coarse static check therefore costs at most a late `U`, never a wrong verdict.

## Rejected

- **Per-attribute fall-through, as `check_corpus.py` implemented it.** A policy could make the baseline's `xsd:decimal` `odrl:payAmount` an `xsd:string` and compare it by code point. The operand would mean different things in different policies under one name.
- **The whole declaration from one layer, as clingo-i implemented it.** A profile that rebinds `odrl:dateTime` to `dprod:clock` would have to restate the range, and a profile that forgets it would silently drop the type.
- **Ordering the profile modules.** RDF does not keep the order of `odrl:profile` values (`decisions/0013`), so any order would be one the author never wrote.
- **Rejecting a rebinding of the source.** DPROD itself rebinds `odrl:dateTime`, and that rebinding is the intended way to choose decision time over action time (`due2-profiles.md` §3, *Baseline bindings*).
- **Class-level range checks.** They need class inference, which due2 performs nowhere else (`due2-profiles.md` §6), for a check whose omission costs only a late `U`.

## Consequences

- `due2-profiles.md` §2 states #1–#3; §3 states #4–#6 and the omissions, and says what a layered binding does to DPROD validation; `profiles/due2-core.ttl` rewords its `odrl:payAmount` comment.
- `due2-diagnostics.md` §3 adds `RetypedOperand`, `OperandRangeMismatch`, and `ConflictingProfileDeclaration`, which v0.7 named without registering.
- `tools/check_corpus.py` and clingo-i read bindings as #1–#3 (issue #68). clingo-i's `binding: two profile modules` decline becomes a rejection when the modules differ, and an answer when they agree. Its `value: datatypes differ without a range` decline becomes an answer under #6.
- DPROD's shapes see one graph and no layers. A policy that rebinds an operand passes them when they validate the policy graph alone, and fails `LeftOperandShape` when the layers are merged into one graph. This is the same caveat as for `due2:witnessSource` (`due2-profiles.md` §3).
- #65 closes with this record. #67 (units) builds on #1: the unit belongs to the declaring layer.

## Revisit when

- A real profile needs to narrow an inherited operand's type, such as a range of `xsd:integer` under the baseline's `xsd:decimal`. Narrowing could then be allowed as a restatement that is a subtype.
