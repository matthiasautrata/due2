# 0033 — A replaced policy and an unrecognised profile are rejected

**Status:** Decided, 2026-10-24 (the owner, on #115)
**Context documents:** `odrl-compound-to-atomic-normalization.md` §3 · `due2-diagnostics.md` · `due2-profiles.md` §2 · `due2-platform.md` §2.3 · `decisions/0020` · `docs/briefings/due2-review-2026-10-24.md` R04, R06 · issue #115

## Question

The ODRL Information Model gives two processing rules that W1 did not follow. The external review found both.

**R04.** ODRL IM §2.8: "If a Policy has the `dc:isReplacedBy` property, then a processor MUST consider the first Policy void and MUST retrieve and process the identified Policy." (`dc:` is `http://purl.org/dc/terms/`.) due2 treated every Dublin Core term as an annotation, so the policy was evaluated as current. An example shows what is at stake. Licence v1 permits Dana to read a dataset. The owner publishes licence v2, which drops the permission, and marks v1 `dct:isReplacedBy` v2. Dana's request over v1 still got `Permit`.

**R06.** ODRL IM §3.2: "If the ODRL Processing system does not recognise the ODRL Profile identifier(s) then it MUST stop processing the policy." `decisions/0020` item 5 admitted a policy that declares a profile with no due2 module: `tools/check_corpus.py` warned that the profile's terms were metadata, and the vocabulary check did not run. But a profile can declare what changes a verdict. A policy with a permission and a prohibition on one request, and no `odrl:conflict`, gets the default `invalid` (ODRL IM §2.10) unless a selected profile declares another. If its unknown profile declares `prohibit`, the policy's answer is `Deny`, and due2's would be `NotApplicable`, since `invalid` voids the policy when both rules apply, and a void policy gives no access answer (`due2-workflows.md` §6.2, `decisions/0029`).

## Decision

1. **A replaced policy is rejected.** W1 rejects a Policy with `dct:isReplacedBy` with the new stage-1 error `ReplacedPolicy`. It does not fetch the replacement, since W1 never dereferences an IRI (`odrl-compound-to-atomic-normalization.md` §3). The policy store selects the replacement in its place (`due2-platform.md` §2.3).
2. **An unrecognised profile is rejected.** W1 rejects a Policy that declares, by `odrl:profile`, a profile that due2 has no module for, with the new stage-1 error `UnrecognisedProfile`. This reverses `decisions/0020` item 5, which gets an amendment.
3. **Both are errors, so processing stops.** As for every error, W1 returns its diagnostics and no corpus, and no later stage runs (`due2-diagnostics.md`).
4. **Validity and admission stay separate.** Both policies are valid ODRL 2.2, and `tools/check_odrl22.py` still says so. ODRL 2.2 validity is a property of the policy; admission is whether due2 can evaluate it. For a profile with no module, `tools/check_odrl22.py` still skips the vocabulary check, since the profile may define any term.

## Why this holds

- **Both rules are MUSTs on a processor, and due2 is one.** A replaced policy is void, so evaluating it answers for terms its owner has withdrawn. A profile due2 cannot read may declare a conflict default, a policy subclass, or an operand binding, and each of these can change a verdict. Reading such a profile's terms as metadata is the approximation that `due2-architecture.md` §1 rules out.
- **W1 stays a pure function of its input.** Following `dct:isReplacedBy` would make W1's output depend on what an IRI resolves to when it runs, which breaks replay. The policy store already decides which policies a request sees, so the replacement is resolved there, before W1.
- **Only `isReplacedBy` is normative among the metadata.** IM §2.8 lists creator, description, issued, modified, coverage, replaces, and isReplacedBy, and gives a processing rule for isReplacedBy alone. Every other `dct:` term stays an annotation, and so do `prov:` terms, which ODRL does not mention.
- **Nothing in the corpus changes.** Every case and every vendored DPROD example declares only DPROD or due2 core, and none uses `dct:isReplacedBy`. The warning of `decisions/0020` item 5 was never raised by any of them.

## Rejected

- **For R04, leave replacement to the policy store alone.** The store would never select a replaced policy, but one that reached W1 by another route would still be evaluated as current, with nothing to say that it is void.
- **For R04, let W1 follow the link.** W1 would fetch the replacement and normalise it in place of the input. It breaks W1's purity and replay, as above.
- **For R06, keep the warning.** A policy could get a verdict that its own profile contradicts, and nothing in the output would say so.

## Consequences

- `due2-diagnostics.md` v0.10 adds the rows `ReplacedPolicy` and `UnrecognisedProfile`, and `UndeclaredProfile` names the second as the code for a profile with no module.
- `odrl-compound-to-atomic-normalization.md` 0.16 §3 requires that every profile `P0` names has a module, and that `P0` is not replaced. Its profile version stays `1`, since no artifact has been produced under it.
- `due2-profiles.md` v0.17 §2 rejects a profile with no module. `due2-platform.md` v0.7 §2.3 says that `select` never returns a replaced policy.
- `tools/check_corpus.py` raises both errors. clingo-i rejects `dct:isReplacedBy` on the policy as `ReplacedPolicy`, and names `UnrecognisedProfile` in the error it already gave for a profile it does not ship.
- Two negative cases pin the decision: `due2-replaced-policy` and `due2-unrecognised-profile`. Both are `odrl22_valid: true`.

## Revisit when

- due2 admits a profile whose declarations it can read without a module, for example one that publishes them in a form `due2-profiles.md` §2 accepts.
