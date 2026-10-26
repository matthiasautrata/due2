# 0022 — A repeated member of a logical constraint is malformed

**Status:** Decided, 2026-10-22 (the owner, asking whether the `xone` shapes that bounded testing reaches belong in policies at all)
**Context documents:** `due2-profiles.md` §5 · `due2-diagnostics.md` §3 · `due2-architecture.md` §10 · `conformance/odrl22-shape.ttl` · `spikes/clingo-i/DESIGN.md` § `compare.lp` · issue #100

## Question

`odrl:xone` holds when exactly one of its members holds. What does it mean when two of its members, the items of its list, are the same constraint? There are two ways to write that, and this record calls either a *repeated member*:

- the list names one node twice, as in `odrl:xone ( ex:c ex:c )`; members written as several values of `odrl:xone` instead of a list cannot do this, because an RDF graph holds each triple once;
- two nodes that are not logical constraints, called *leaves* here, state the same left operand, operator, unit, and right operand values.

Read as positions in a list, with W1's expansion ⋁ᵢ (aᵢ ∧ ⋀ⱼ≠ᵢ ¬aⱼ) (`due2-workflows.md` §4, stage 2), a repeated member changes the meaning of the whole `xone`:

| Members | Expansion | Value |
|---|---|---|
| `a, a` | (a ∧ ¬a) ∨ (a ∧ ¬a) | never `T`: `F` when `a` is decided, `U` when it is not |
| `a, a, b` | (a ∧ ¬a ∧ ¬b) ∨ (a ∧ ¬a ∧ ¬b) ∨ (b ∧ ¬a ∧ ¬a) | `b ∧ ¬a` whenever `a` is decided |

Read as a set of constraints, `xone(a, a)` is `a`, and `xone(a, a, b)` is `xone(a, b)`. The two readings differ whenever `a` holds. For `and` and `or` they agree, because both connectives are idempotent.

The two implementations disagreed in exactly this way. `tools/check_corpus.py` reads a list's members in order, with repeats, as W1 does. clingo-i, whose relation `member/2` holds a connective's members as a set, gave `odrl:xone ( ex:c ex:c )` the value of `ex:c`. A direct interpreter that differs from the pipeline on an admitted input breaks L9 (`due2-workflows.md` §8).

## What ODRL says

IM §2.5.2 gives a logical constraint "a list of the existing Constraint instances", and its validation requirements include "All of the operand values MUST be unique Constraint instances." So a list that names one node twice is invalid ODRL, for every connective, and `odrl22-shape.ttl` already fails it.

Two nodes that state the same leaf are two instances, so the requirement does not reach them. The `odrl:xone` entry of the vocabulary file (`ODRL22.ttl`) defines it as "satisfied when only one, and not more, of the Constraints is satisfied", which does not say whether "the Constraints" counts instances or what they state. So ODRL admits the second form and supports both readings of it.

## Decision

Normalisation rejects, with `MalformedConstraint` in stage 2:

1. a logical constraint of any connective whose list names one node twice, as IM §2.5.2 requires;
2. an `odrl:xone` with two leaf members that state the same left operand, operator, unit, and set of right operand values. Values compare as written terms (`due2-workflows.md` §2 `Term`), as the completion variables of `due2-workflows.md` §6.4 compare them, so `5` and `5.0` are different values.

Item 1 follows ODRL, as `decisions/0017` follows the shape for the empty list. Item 2 is due2's own, for reasons of the kind `decisions/0017` gives:

- ODRL gives the form no single reading, and the two candidates differ whenever the repeated member holds.
- No author who means "exactly one of these" lists a condition twice. The likely cause is an authoring error, such as a copy that was meant to be edited, or a generator that emitted one condition twice.
- The error is silent and changes the meaning of the policy: under the position reading, `xone(a, a, b)` quietly denies the case where `a` holds.

Rejecting both forms shows the author the error, and it leaves no input on which W1's position reading and clingo-i's set reading can disagree.

Item 2 is an authoring aid, and soundness does not depend on how completely it detects repeats. Two compound members with the same content in different nodes are not detected. Both W1's expansion and clingo-i's counting (below) read them as two positions, so they still agree. Two leaves whose values are the same but are written differently (`5` and `5.0`) are not detected either. They are then two completion variables (`due2-workflows.md` §6.4), not one, which can only widen a verdict to `Indeterminate` (`decisions/0012`).

## Rejected

- **Admit only leaves as `xone` members.** IM §2.5.2 and the vocabulary file ask every connective's members to be Constraint instances, so the letter of ODRL excludes nesting for `and`, `or`, and `xone` alike. due2 admits nested connectives, as DPROD and OVAL write them, and `conformance/odrl22-shape.ttl` accepts them. Excluding them for `xone` alone would simplify clingo-i's liveness rules (`spikes/clingo-i/DESIGN.md` § `explain.lp`), but OVAL's suite nests `and` and `or` inside `xone` in nine of its policies (under `conformance/external/oval/`: `logic_with_nulls7`, `8`, and `8b` in `access_control/`; `logic_nested` and `logic_nested2`–`6` in the two monitoring directories). A compound alternative inside an exclusive choice is also an ordinary thing to write: `xone(adminLevel ≥ 3, or(resolution ≤ 256, media = paper))`. So this would reject a shape that an external evaluator accepts and tests, only to make an oracle smaller.
- **Reject only a repeated node in `xone`.** ODRL's requirement covers every connective, and admitting it in `and` and `or` would leave due2 accepting a policy that the ODRL 2.2 check fails, for no gain: the idempotent reading needs no repeat.
- **Reject two leaves with the same content in `and` and `or` too.** Both readings agree there, so nothing is ambiguous, and ODRL admits the form.
- **Read the set.** It agrees with `and` and `or`, but it makes `xone ( ex:c ex:c )` mean `ex:c`. That reading needs every implementation to deduplicate members first. A procedural evaluator that loops over the list, the natural implementation, gets the position reading instead.
- **Read the positions.** It is what W1's expansion and a loop over the list do. It is unambiguous, but it makes an authoring error mean something, and the meaning it gives is rarely what the author wanted.
- **Warn.** A warning still lets the policy through with one of two readings. Neither reading is right often enough to choose it for the author.

## Consequences

`due2-profiles.md` v0.14 §5 and `due2-diagnostics.md` v0.8 §3 state the rejections. `tools/check_corpus.py` and clingo-i (`spikes/clingo-i/lp/constraint.lp`) reject both forms. The negative case `due2-repeated-member-node` covers item 1 and sets `odrl22_valid: false`, because the shape fails it too; `due2-xone-repeated-leaf` covers item 2 and is valid ODRL 2.2.

clingo-i gives an `xone` its value by counting its members: with `T` members `t` and `U` members `u`, the `xone` is `t` when `T = 1` and `U = 0`; `f` when `T ≥ 2`, or when `T = U = 0`; and `u` otherwise. That is the Kleene value of the expansion for any values of the members, which `spikes/clingo-i/DESIGN.md` § `compare.lp` shows case by case. So L9 compares two different computations of `xone`: W1's expansion and clingo-i's count, where clingo-i once computed the expansion too. A procedural evaluator is likely to count as well, and the shortcut it is most likely to take, reading an unknown member as false, is a mutant that the clingo-i tests kill.

## Revisit when

- The ODRL WG or CG gives two `xone` members with the same content a meaning.
- A real policy turns up that repeats an `xone` member on purpose.

**Note (2026-10-26):** the clingo-i sections this record cites moved beside the code (#135). `spikes/clingo-i/DESIGN.md` § `compare.lp` is now `spikes/clingo-i/lp/compare.lp`, *Connectives*, which holds the `xone` case analysis; § `explain.lp`'s liveness rules are now the `live/4` doc block of `spikes/clingo-i/lp/explain.lp`.
