# 0020 — A vocabulary term is defined by ODRL, a declared profile, or the policy itself

**Status:** Decided, 2026-10-18 (the owner chose alternative B of #78, read for the `odrl:` namespace only)
**Context documents:** ODRL IM §2.1 · `due2-diagnostics.md` (`UndeclaredProfile`) · `odrl22-conformance.md` §3 · `conformance/README.md` § `policy.ttl` · `tools/check_odrl22.py` · `tools/check_corpus.py` · issue #78

## Question

ODRL IM §2.1: "An ODRL Policy MUST either: Only use terms defined in the ODRL Core Vocabulary, or Use an ODRL Profile that declares the supported vocabulary used by expressions in the Policy. In the latter case, the profile property MUST be used to indicate the IRIs of the ODRL Profile(s)." Both checkers implemented the rule as an allow-list of two namespaces, DPROD and due2 core: a term of either used without its `odrl:profile` declaration is `UndeclaredProfile`. A term from any other namespace passed with nothing to give it a meaning. An undeclared action then matches only itself, and the relations its vocabulary defines, `odrl:includedIn` edges for instance, are silently absent. The DALICC license library is the evidence: all 347 licenses use `dalicc:` actions, declare no profile, and passed both checkers (`docs/design/references.md`, DALICC).

A second gap sat in `tools/check_odrl22.py`. It typed every object of `odrl:action` as `odrl:Action`, so that a refined action, an untyped blank node (IM §2.5.4), meets the shape. The same typing made the shape's class check on actions pass for any IRI.

Which terms need no profile? The IM says only the Core Vocabulary. The W3C's own examples use Common Vocabulary terms (`odrl:purpose`, `odrl:dateTime`) with no profile, and 11 corpus cases (ten `rl2-*` and `due2-incomparable-frontier`, 21 terms) type their own `ex:` actions in the policy graph and declare no profile.

## Decision

This is alternative B of #78; the others are listed under Alternatives.

1. **A term is defined** when it is one of these:
   - a term in the `odrl:` namespace (`http://www.w3.org/ns/odrl/2/`) that `profiles/vendor/w3c/ODRL22.ttl` types, Core or Common;
   - a term a selected profile module types: the baseline modules `profiles/due2-core.ttl` and `profiles/odrl-actions.ttl` always, and the DPROD modules when the policy declares DPROD;
   - a term the policy's own graph types.
2. **The checked positions** are the objects of `odrl:action` (for a refined action, its `rdf:value`), `odrl:leftOperand`, `odrl:operator`, `odrl:function`, `odrl:relation`, and `odrl:conflict`. A term there that is not defined is `UndeclaredProfile`.
3. **`odrl:unit` is not checked.** A unit names the measure of a right operand's value, not a term of the policy language, and comes from any vocabulary: the IM's own examples and 13 corpus uses name `dbpedia:Euro` or `dbpedia:Dots_per_inch`. due2 gives a unit no relation to anything else, so nothing it would load is lost.
4. **The nine `cc:` terms in `ODRL22.ttl` are not defined** under item 1, because they are not in the `odrl:` namespace. The file types them `odrl:Action` with `odrl:includedIn odrl:use`. But each also carries the note "This term is defined by Creative Commons." Four of them name the same act as an ODRL action, and no triple in the file relates the two: `cc:Reproduction` and `odrl:reproduce`, `cc:Distribution` and `odrl:distribute`, `cc:DerivativeWorks` and `odrl:derive`, `cc:Attribution` and `odrl:attribute`. And they flatten Creative Commons' own permissions, requirements, and prohibitions into sub-actions of `use`. A policy that uses them declares a profile that gives them a meaning, as for any other foreign term. `profiles/odrl-actions.ttl` omits their `includedIn` edges for the same reason.
5. **A declared profile that due2 has no module for** defines whatever it declares, and due2 cannot tell what that is. So the check of item 2 does not run for such a policy. `tools/check_corpus.py` warns that the profile's terms are metadata. The policy has done what IM §2.1 asks; due2 cannot read the vocabulary it chose.
6. **The namespace rule stays.** A DPROD or due2 core term anywhere in a policy, in any position, still needs that profile's `odrl:profile` declaration. Normalisation selects a module by its declaration (`odrl-compound-to-atomic-normalization.md` §3), so an undeclared DPROD binding would be lost.
7. **The action class check is restored.** `tools/check_odrl22.py` types only blank-node objects of `odrl:action` as `odrl:Action`. An IRI action is then an `odrl:Action` only where a vocabulary or the policy types it so, and IM §2.5.4's class constraint can fail.

## Alternatives

- **A. Strict IM.** Only the Core Vocabulary needs no profile. This departs from the W3C's own examples and invalidates the 11 self-declaring cases. It would also require a profile for every Common Vocabulary term in the corpus, a count never taken.
- **C. As the decision, with a self-declared term in a namespace the policy's own profile declares.** It is closer to the IM's letter and changes the same 11 cases.
- **The `cc:` terms as defined, with their nine `includedIn` edges added to `profiles/odrl-actions.ttl`.** This follows `ODRL22.ttl` to the letter and keeps two unrelated names for one act.

## Consequences

The corpus and the vendored DPROD examples pass unchanged. Two negative cases pin the reading: `due2-undeclared-action` (an `ex:` action that nothing defines) and `due2-undeclared-cc-action` (`cc:Distribution`). Both are `odrl22_valid: false`. The first also fails the restored action class check. The DALICC licenses now fail both checkers with `UndeclaredProfile`. The strict reading of IM §2.1 also rejects the `cc:` case, since the `cc:` terms are not in the Core Vocabulary. The departure from IM §2.1's letter is recorded in `odrl22-conformance.md` §3: Common Vocabulary terms and self-typed terms are admitted without a profile.

## Amendment (2026-10-24, an unrecognised profile)

`decisions/0033` reverses item 5. A policy that declares a profile due2 has no module for is rejected at normalisation with `UnrecognisedProfile`, because ODRL IM §3.2 requires a processor that does not recognise a profile to stop, and because such a profile may declare what changes a verdict, such as a conflict default. `tools/check_corpus.py` raises the error where it warned. The vocabulary check of item 2 still does not run for such a policy, since the profile may define any term, so `tools/check_odrl22.py` can still find it valid ODRL 2.2. The rest of the decision stands.
