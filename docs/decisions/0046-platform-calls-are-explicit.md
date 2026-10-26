# 0046 — Publication is its own workflow, and a case changes only by explicit calls

**Status:** Decided, 2026-10-26 (the owner, in the review of `due2-platform.md` on that date)
**Context documents:** `due2-platform.md` §1.2, §2.4, §2.6, §2.11, §3 · `due2-architecture.md` §7 · `due2-workflows.md` §7.1 · `decisions/0038` · `decisions/0040` · `decisions/0045` · issues #14, #98, #140

## Question

`due2-platform.md` v0.13 left three things to the orchestrator, the one component that calls the others:

- **Publishing.** The orchestrator ran W1 as a batch job when a policy or normaliser version was stored, put the corpus in the policy store, and ran what-if checks over cases (`due2-platform.md` §2.3, §2.8, §2.11).
- **Changed values.** `decisions/0040` made keeping a value current the SOTW service's job: when a value changes in the world, the service supplies the new one, and it reaches each case that read it as a new event. How the service reports a change, and which cases receive it, was open (#140): a subscription, a change feed, or polling.
- **New cases after a policy change.** A case fixes its corpus (`decisions/0038`), so an amended policy reaches an earlier request only through a new case. Which cases the orchestrator reopens, and when, was open.

Each of these is machinery: an event bus, a dependency index from properties to cases, or a rule that decides which cases a publication affects. Is any of it needed before the platform runs?

## Decision

1. **Publication is a workflow of its own.** The publication workflow lints a policy, normalises it (W1), runs what-if checks, and publishes the corpus to the policy store. The orchestrator runs cases and never publishes. The two workflows are the only components that call others.
2. **A case changes only by explicit calls to the orchestrator.** There is no subscription and no change feed. Each call names its case. Besides `submit_evidence`, which records evidence and evaluates the case, four calls carry a changed value or a policy change to a case:
   - `record_facts(case_id, answers, key)` records answers that a caller brings, such as a SOTW service that knows a value changed, or an operator.
   - `refresh(case_id, key)` asks every source that a connector answers again for the case's planned state properties and world modules, and records each answer. It prompts no person.
   - `reevaluate(case_id, key)` calls `decide` over what the case holds, and asks no source.
   - `reopen(case_id, key)` opens a new case for the case's request, with its corpus selected again and the normaliser pins current at the call, and fetches its reads.

   `show(case_id, seq?)` renders an evaluation and changes nothing.
3. **Who calls, and for which cases, is the caller's choice.** The ledger lists cases by their latest verdict, so a caller can sweep every pending case. The platform computes no set of affected cases.
4. **`key` is the caller's idempotency key** on every call that records an event or opens a case: a retry with the same key records nothing a second time. How the ledger stores keys stays open (#98).

## Why this holds

- **Publishing and deciding run at different times and fail differently.** Publication runs when an author or a normaliser release asks for it, and can refuse a policy (`IdentityConflict`, W1's rejections). A case runs when a requester asks. Keeping them apart keeps the request path free of W1, as `decisions/0027` item 3 and its reasons require, and lets an author run what-if checks without touching a case.
- **Nobody has measured a need for the machinery.** Pending sets in governance are small and approvals are rare (`due2-architecture.md` §7). An explicit call per case does the job a subscription would, and a sweep over pending cases is a loop of such calls. The owner: "too much machinery for now. Leave it to explicit calls. no pub/sub for now".
- **`refresh` answers a source that cannot report changes,** the case that `decisions/0040` named as its reason to revisit. Someone who knows a source cannot push calls `refresh` on the cases that need it. `refresh` asks again; it does not check an answer's age, so `decisions/0040` #4 stands: neither the orchestrator nor the evaluator decides that an answer is too old.
- **Reopening is a judgement about a policy change.** A what-if run shows which verdicts a new version would change. Whether those cases should be reopened, and when, belongs to the people who published the change, so it is a call they make, not a rule the platform applies.

## Rejected

- **A subscription or change feed from each SOTW service.** It needs a bus, a registry of subscribers, and a rule for which cases a change reaches, before anyone has shown that the explicit calls are too slow.
- **A dependency index from properties to cases** (`due2-architecture.md` §7, the second trigger). Justified only when re-evaluating every pending case measurably hurts (#14).
- **Reopening every affected case on publication.** It needs the platform to decide which cases a policy affects, which is the over-selection problem of `due2-platform.md` §2.3 (#94), and it would act on a judgement that whoever published the policy has not made.

## Consequences

- `due2-platform.md` v0.14: §1.2 names the two workflows; §2.4 keys the registry by property and source; §2.6 adds `record_facts`, `refresh`, `reopen`, and `show`, and gives `reevaluate` a key; §2.11 becomes the publication workflow; §3.3, §3.5, and §3.6 follow; §5 drops the question of how a changed value is reported.
- `due2-architecture.md` §7: the first re-evaluation trigger is explicit calls.
- `decisions/0040` carries a note.

## Revisit when

- Explicit calls measurably fail to keep cases current: a sweep over pending cases takes too long, or callers miss changes they should have recorded.
