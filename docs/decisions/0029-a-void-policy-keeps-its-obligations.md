# 0029 — A void policy keeps its root obligations

**Status:** Decided, 2026-10-24 (the owner, on #110)
**Context documents:** `due2-workflows.md` §3.7, §6.1, §6.2, §6.4, §8 L5 · `due2-architecture.md` §6.2 · `docs/briefings/due2-review-2026-10-24.md` R03 · issues #110, #92

## Question

Under `conflict = invalid`, a `T` permission and a `T` prohibition of one policy void it (`due2-workflows.md` §6.2). The spec said that all of the void policy's atoms are eliminated and that it contributes nothing. clingo-i (`spikes/clingo-i/lp/resolve.lp`) and the Alloy model (`formal/alloy/resolve.als`) eliminate only its permissions and prohibitions, so its root obligations stay in force, and under `config.violations = deny` a violated one still denies. The external review found the disagreement (R03). Which reading is meant?

An example shows what is at stake. Policy P, under `invalid` and `violations = deny`, has three rules: a permission to use a dataset; a prohibition on using it for marketing; and a root obligation on the steward to delete an expired copy by 1 June. On 2 June the copy has not been deleted, so the obligation is violated. A request to use the dataset for research matches only the permission, so there is no conflict, and the violated obligation denies it. A request to use it for marketing matches the permission and the prohibition, so P is void. If the void removed the obligation too, the marketing request would be `NotApplicable` while the research request is `Deny`. The request that P forbids would get the better answer, and with a second policy that permits the use it would get `Permit`.

## Decision

1. **A void policy loses its permissions and prohibitions, and keeps its root obligations.** Under `invalid`, a `T` candidate and a `T` `Forbid` of a policy eliminate every `Permit` and `Forbid` atom of it, with rule `invalid`. Its root obligations are not eliminated: each is in force or not by `due2-workflows.md` §5.2, and under `violations = deny` a violated one denies as it would in a policy that is not void.
2. **This departs from ODRL's reading.** ODRL 2.2 says that a policy whose `invalid` conflict arises is void, which plainly reads as the policy governing nothing. due2 reads "void" as the policy giving no access answer for the request. The departure is stated in `due2-architecture.md` §6.2, beside the other choices that `due2-workflows.md` §6.4 justifies by monotonicity (#92).
3. **A `Deny` from a violated obligation is explained by that obligation.** `verdict_basis` names it with role `obligation`, with its instance's status, `violated` (`due2-workflows.md` §5.3, §6.1, §6.4). When the policy is void, `eliminated` also names its permissions and prohibitions with rule `invalid`. A reply therefore carries both halves of "denied: the deletion obligation is violated; the policy's permission and prohibition voided each other".

## Why this holds

- **An obligation's violation does not depend on the request's action.** Whether the copy was deleted by 1 June is a fact about the world. The conflict that voids P is a fact about one request: the marketing request makes both the permission and the prohibition apply, and the research request does not. `due2-workflows.md` §6.2 already says that duties play no part in conflict. Keeping the obligations makes the void act only where the conflict is, on the access rules.
- **The verdict stays monotone, and the proof of `due2-workflows.md` §6.4 holds as written.** That proof tracks two sets, the candidates and the surviving `T` prohibitions, and under `deny` a violated obligation in force counts as a surviving prohibition. When a prohibition of P becomes `T` and voids P, P's candidates go, and its other prohibitions were all `F`, or P would have been void already. No obligation goes, so nothing that denied stops denying, and the verdict stays or falls. Under the other reading the void would remove a denying obligation. In the example, P without its prohibition gives `Deny` for the marketing request, and P with it gives `NotApplicable`: adding an applicable prohibition raised the verdict, against L5, and the two-completion computation of `due2-workflows.md` §6.4 would no longer bound every completion.
- **The executable semantics already agree.** clingo-i and the Alloy model implement this reading, and the corpus case `due2-void-keeps-obligation` passes under clingo-i unchanged. Their agreement does not settle the question, since both were written from the same reading. The argument above does.

## Rejected

- **Void removes everything.** It is ODRL's literal reading. It lets a request escape a violated obligation by asking for a forbidden use, breaks L5 under `deny`, and would need a new completion argument and changes to `tools/check_completion.py`, clingo-i, and the Alloy model.
- **`Indeterminate` with a cause.** A void policy would make the verdict `Indeterminate`, which is fail-safe. It is a value outside the chain of `due2-workflows.md` §6.4 and needs its own computation, so it stays parked (`due2-architecture.md` §6.2).
- **A void policy denies.** The void itself would be a `Deny`. Within one policy that makes `invalid` behave like `prohibit`, which ODRL keeps distinct.

## Consequences

- `due2-workflows.md` v0.37 states the rule in §6.2, adds the void's obligations to the prohibition case of §6.4's proof, and says in §6.4 that a `Deny` from a violated obligation is explained by role `obligation`. `due2-architecture.md` v0.12 §6.2 names the departure from ODRL.
- `conformance/README.md` says that `eliminated` under `invalid` lists the void policy's permissions and prohibitions, and `tools/check_corpus.py` rejects a case that lists an obligation there.
- `due2-void-keeps-obligation` pins the example in four scenarios: the research and the marketing request under `deny` (both `Deny`), the marketing request under `ignore`, and the marketing request with the copy deleted in time (both `NotApplicable`).
- clingo-i and the Alloy model give the same verdicts as before. clingo-i's `eliminated/2` no longer lists an obligation atom of a void policy, which its `deny/1` never read; the comments of both cite this record.

## Revisit when

- A real policy needs a void to remove its obligations, for example an obligation that exists only to accompany the access the conflict voids. Such a duty may belong on the permission as a precondition, where the void already removes it with its parent.

**Note (2026-10-26, `decisions/0045`):** `violations` is removed, and a violated obligation is reported and never denies. Item 1 stands: a void policy keeps its root obligations, and they are reported with their status. Item 3, and the example's `Deny` for the research request, no longer apply: that request is now permitted, with the violated obligation reported beside the verdict (`conformance/cases/due2-void-keeps-obligation`).
