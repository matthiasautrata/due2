# 0030 — A re-evaluation asks at its own time

**Status:** Decided, 2026-10-24 (the owner, on #111)
**Context documents:** `due2-workflows.md` §3.2, §3.3, §5.3, §7, §7.1 · `due2-architecture.md` §7 · `due2-platform.md` §2.6 · `due2-profiles.md` §2, §3 · `decisions/0008` · `docs/briefings/due2-review-2026-10-24.md` R10 · issue #111

## Question

A request carries two instants. `request.at` is the instant of the proposed action, validity time, and it is what a constraint on `odrl:dateTime` reads under the `due2-core` binding (`due2-profiles.md` §3). `sotw.effective_at` is decision time, and it bounds which evidence counts as a witness (`due2-workflows.md` §5.3). The ledger fixed a case's request when the case was created (`due2-workflows.md` §7.1), so every re-evaluation of the case reused the first `at`, however late it ran. The external review found the consequence (R10): evidence performed after the proposed action time can fulfil a precondition of that action.

An example shows what is at stake. A permission to use a dataset holds before 1 April and has a payment duty. Dana asks on 1 March and has not paid, so the verdict is `Pending`. Dana pays on 15 April, and the case is re-evaluated on 20 April. With the first request, `at` is still 1 March, so the window is open, and the payment occurred before `effective_at`, so it is a witness: the verdict is `Permit`. But the window had closed before Dana paid, and the `Permit` arrives when the action can no longer be taken on 1 March. Which instant does a re-evaluation answer for?

## Decision

1. **Every evaluation records the request it runs with.** That request is the case's request with `at` moved to the evaluation's `effective_at` when the case's `at` is earlier. A later `at`, as for an action proposed for a future date, is kept. Every other field is unchanged. `reference` in particular is kept, so grant-scoped duty instances (`due2-workflows.md` §5.3) carry over from one evaluation to the next. The ledger's `evaluation` relation names this request (`due2-workflows.md` §7.1). For the first evaluation, made when the case is opened, the request is usually the case's own; for a re-evaluation, `at` usually moves.
2. **A case's current answer is its latest evaluation.** Earlier evaluations stay in the ledger with their own requests and are answered from, and replayed, as recorded (`decisions/0008`).
3. **The orchestrator builds the requests.** The orchestrator, the component of the shell that runs a case (`due2-platform.md` §2.6), builds every access evaluation's request by item 1, so no access evaluation has an `at` earlier than its `effective_at`.
4. **The evaluator does not change.** It does not compare `at` with `effective_at`, and it answers for whatever `at` it is given. A request whose `at` is earlier than its `effective_at` asks about an action at a past instant. The evaluator answers that question, and an access evaluation does not ask it.

In the example, the re-evaluation on 20 April runs with `at` 20 April. The window is closed, so the permission does not apply, and the verdict is `NotApplicable`. Had Dana paid on 20 March and the case been re-evaluated on 25 March, `at` would be 25 March, the window would be open, and the verdict would be `Permit`.

## Why this holds

- **It answers the question a re-evaluation is for.** A `Pending` case is asking whether the action may be taken. When the case is re-evaluated, the action can be taken only from that time on, so that is the instant the window has to cover. Moving `at` to `effective_at` asks exactly that, and it is how the review's third option reads: re-evaluation issues a new prospective request time.
- **Late-recorded earlier evidence and later-performed evidence stay apart.** The witness test reads `occurred_at`, never when the evidence was recorded (`due2-workflows.md` §5.3, §7.1). A payment made on 15 February but found out on 20 March still counts on 20 March, because 20 March is inside the window. A payment made on 15 April cannot open a window that closed on 1 April, because no re-evaluation after 15 April has an `at` inside it. The review asked for the two to be tested apart, and `due2-reevaluation-moves-at` does so.
- **Nothing new is needed.** The ledger already records every evaluation with a time, and the trace's `evaluation` tuple already names a request id (`due2-workflows.md` §3.5). The change says which request that is. W2 and W3 stay pure functions of their inputs, so replay is unaffected, and the corpus cases that set a past `at` keep their answers.
- **The DPROD profile already behaves this way.** It rebinds `odrl:dateTime` to `dprod:clock`, which is `effective_at` (`due2-profiles.md` §2), so its window is always tested at decision time. The hazard arose only under the `due2-core` binding, and the decision brings that binding into line for access evaluations.

## Rejected

- **Keep `at` fixed and bound precondition witnesses by it.** A witness of a permission's duty would also need `occurred_at ≤ at`, with `at` the case's. The witness test would then depend on the role of the duty: a duty that is both a precondition and an obligation would need two witness tests, bounded by `at` and by `effective_at`. It also breaks the ordinary flow: Dana asks on 1 March, pays on 5 March, and no re-evaluation of the case could ever return `Permit`, because the payment is after the case's `at`. Every payment would need a new case, so a grant-scoped payment would never count for the request it answers. Bounding by the moved `at` instead would add nothing, since the moved `at` is never earlier than `effective_at`.
- **Keep the behaviour and document it.** A late payment would then stretch every window, for as long as the case is open.
- **Let the evaluator test the window at the later of `at` and `effective_at`.** It gives the same verdicts as this decision. But the trace would name a request whose `at` the evaluator did not use, so a reader of the trace would need the rule to know which instant was answered for. The evaluator could also no longer be asked about an action at a past instant, the question that the revisit condition below may need.

## Consequences

- `due2-workflows.md` v0.38 states the rule in §3.2, and §7.1's `evaluation` relation gains the `request` its evaluation ran with. §7.1 also says that the latest evaluation is the case's current answer.
- `due2-platform.md` v0.4 §2.6 says that the orchestrator builds each evaluation's request. `due2-architecture.md` v0.13 §7 says, in its case flow, that a re-evaluation asks at its own time.
- `correctness-strategy.md` v0.14 §4.7 adds the rule to the case-history properties, for the stateful machine to check, and says that a moved `at` can change a verdict.
- Only what reads `at` is affected: a rule's `odrl:dateTime` constraints under `due2-core`. A duty's deadline is tested against `effective_at`, as before (`due2-workflows.md` §5.3). Re-evaluating a decided `Permit` whose window has since closed gives `NotApplicable`, which is the right answer to whether the action may be taken now.
- `due2-reevaluation-moves-at` pins the example in four scenarios: the first evaluation (`Pending`), the same evaluation with a payment made before it (`Permit`), the re-evaluation after the late payment (`NotApplicable`), and the review's stale request with `at` left on 1 March (`Permit`, the answer to the question about 1 March). clingo-i passes all four unchanged.

## Revisit when

- A use case needs a decision for an action at a past instant made at a later time, such as a retroactive approval. That would be a new kind of request, not a re-evaluation, and the orchestrator guard would need an exception for it.
