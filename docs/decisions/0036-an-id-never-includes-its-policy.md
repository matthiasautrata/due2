# 0036 — An id never includes its policy, and an atom roots each policy that states it

**Status:** Decided, 2026-10-26 (the owner, on #130)
**Context documents:** `due2-workflows.md` §3.1, §3.5, §4, §5.1, §5.2, §6.2, §8 (L2) · `odrl-compound-to-atomic-normalization.md` §5.1, §5.2 · `due2-diagnostics.md` §3 · `decisions/0028` · `decisions/0032` · `spikes/clingo-i/lp/duty.lp` · issues #130, #107, #131

## Question

In `due2-workflows.md` v0.44 an atom carried one `policy_id`, and a constraint carried the one atom it was attached to:

```text
atom        (atom_id | effect: Enum, action, relation?, relation_value?, policy_id, source_rule, priority?: Count)
root        (atom_id)
constraint  (constraint_id | atom_id, clause?: Count, scope: Enum, left_operand, operator, datatype, unit?)
```

An id comes from stage 1: a named node keeps its authored identity, and an anonymous one is identified by its place, the parent and the predicate that reach it, and by its content (`odrl-compound-to-atomic-normalization.md` §5.1, §5.2). A duty atom's id adds only what stage 2 adds: "not the parent permission, not the policy" (`decisions/0032`). W1 normalises one policy per input (`MultiplePolicies`), and no spec said how the corpora of policies evaluated together are combined.

So a named rule that two policies state has one `atom_id` and two values of `policy_id`, and nothing said which one the corpus keeps. For example, offer `A` and agreement `B`, made from it, both state `duty:deliver-2026-001` as `odrl:obligation`, so under the key `atom_id` the two `atom` tuples clash. A named constraint that two rules use, in one policy or in two, has the same fault: one `constraint_id` with two values of `atom_id`.

The policy is read in two places: the per-policy conflict fold (`due2-workflows.md` §6.2), and whether a root obligation is in force, which asks whether some permission or prohibition of its policy matches the request (`due2-workflows.md` §5.2).

## Decision

1. **No named node's id includes the policy, or any other envelope, that states it.**

   | Node | Its id |
   |---|---|
   | Named rule, duty, or constraint | Its authored identity |
   | Rule that stage 1 expands along a multi-valued axis | `atomic_rule_uid`, its source's id and the selection |
   | Duty to which stage 2 adds roles or parameter values | `duty-atom` (`decisions/0032`) |
   | Disjunct atom; constraint stage 2 derives, such as an `xone` negation | Derived from its source; the construction is open (#107) |
   | Anonymous node | Its place and content; for an anonymous root rule, the place is its policy |

2. **Membership and attachment are key fields of their own relations:**

   ```text
   atom             (atom_id | effect: Enum, action, relation?, relation_value?, source_rule, priority?: Count)
   root             (atom_id, policy_id)
   constraint       (constraint_id | left_operand, operator, datatype, unit?)
   atom_constraint  (atom_id, constraint_id, scope: Enum)
   duty_constraint  (atom_id, clause: Count, constraint_id, scope: Enum)
   ```

   A `root` tuple says that the atom roots an Atomic Policy of that policy. Every `Permit` and `Forbid` atom, and every policy-level obligation, has one for each policy that states it. A duty that is only a precondition, remedy, or consequence has none. `atom_constraint` attaches a constraint to a `Permit` or `Forbid` atom, and `duty_constraint` to an `Oblige` atom, in the clauses of `decisions/0028`, which this record amends.
3. **A shared permission or prohibition takes part once in each of its policies.** Its part in one policy is its *entry* there. The conflict fold of `due2-workflows.md` §6.2 eliminates entries, and an atom remains a candidate, or a prohibition, while any of its entries survives. The trace relation `eliminated` gains `policy_id`, one tuple for each entry removed. A case's `expected.eliminated` projection is unchanged.
4. **A root obligation is in force when one of its root policies matches** the request: its match is the Kleene disjunction of its root policies' matches, and its guards must hold as before (`due2-workflows.md` §5.2). clingo-i reads it so: `lp/duty.lp` relates a duty to every policy that states it as an obligation (`obligation_policy/2`) and takes the greatest match over them.
5. **The corpus of policies evaluated together is the union of their corpora,** relation by relation, formed after both stages have accepted every policy. Two corpora that both hold a node must say the same of it: its keyed tuple (`policy`, `atom`, `constraint`, `duty`), and the tuples that name it in the first field of `policy_profile`, `atom_party`, `constraint_value`, `atom_constraint`, `duty_constraint`, and `edge`. `root` differs by design and is not compared. If two corpora say different things of one node, W1 rejects the union with `IdentityConflict`, whose ref is the node. For example, if `A` gives `duty:deliver-2026-001` the deadline `P1D` and `B` gives it `P2D`, the two `duty` tuples share the key and differ in `deadline`. If `A` attaches a constraint to `rule:read` and `B` does not, their `atom_constraint` tuples for `rule:read` differ. `priority` is a field of `atom`, so two policies that give one rule different priorities conflict too.

## Why this holds

- **An id names the thing, not where it is stated.** The author who names a rule says what it is. An offer and the agreement made from it that both grant `rule:read` grant one read, so the corpus holds one atom. An id that included the policy would split it into two, and change whenever another policy restated the rule.
- **One duty, one fulfilment.** A duty is fulfilled by a witness, a record of its action performed (`due2-workflows.md` §5.3), and nothing in a witness names a policy. The delivery that `A` and `B` both oblige is one delivery. With one atom it has one instance key (`due2-workflows.md` §5.3), so one witness fulfils it under both policies, and a case records it as owed once.
- **Entries give the verdict of copies.** Each policy's `conflict` strategy applies to that policy's entries, so the fold still reads one strategy for each thing it eliminates. By item 5 the policies that share an atom say the same of it, so its entries are what equal copies in each policy would be, and it is eliminated exactly when those copies would be: sharing a rule changes no verdict. For example, `A` under `invalid` permits `rule:read` and has a `Forbid` of the same action, both apply, and `B` under `perm` permits `rule:read`. `A` is void, so both of its entries are eliminated. `B`'s entry of `rule:read` survives, and the verdict is `Permit`, as it would be with a copy of the rule in each policy.
- **A duty is owed under either policy.** A request made under `A` or under `B` puts the delivery in force, because each policy obliges it. The disjunction is monotone in each policy's match, so the completion argument of `due2-workflows.md` §6.4 holds for it. That argument gains one step for an atom with several entries: a change to its finding is a change to each entry, each in its own policy's fold, and each moves the candidates and the prohibitions the same way.
- **The key is the fact.** A `root` tuple states one fact: this atom roots that policy. An `atom_constraint` tuple states another: this constraint is attached to that atom. The canonical encoding's values are scalars (`due2-workflows.md` §2), so a list of policies on `atom`, or of atoms on `constraint`, has no place in it.
- **Sharing is stated by naming.** Two licences, each with its own permission carrying an anonymous duty "pay 100 EUR", give the duties different parents, so they are two duties, and paying once fulfils one of them. Their authors did not say that the two are one, and naming the duty in both is how they would say it. An anonymous node under a named parent that two policies share is shared with it, as part of what the parent says, and item 5 requires the policies to agree on it.
- **Unions fail closed.** A shared node that two corpora describe differently means two policies disagree about one resource. Choosing one of them would hide the disagreement, so it is rejected, as stage 1 already rejects two resources that claim one identity (`odrl-compound-to-atomic-normalization.md` §5.1).

## Rejected

- **Put the policy into a permission's or prohibition's id**, by a new `policy-rule` domain beside those of `odrl-compound-to-atomic-normalization.md` §5.2. Each policy would then have its own atom, so the fold needs no entries, but a rule that two policies state becomes two atoms, and its id depends on the envelope that carries it.
- **Identify an anonymous node by its content alone.** The two "pay 100 EUR" duties above would merge, and one payment would fulfil both, which neither author said.
- **Eliminate a shared atom when any one of its entries is eliminated.** In the example above, `A`'s voiding would remove `B`'s permission too, leaving no candidate, and the verdict would be `NotApplicable` where copies in each policy give `Permit`.
- **Keep `policy_id` on `atom`, and give each policy its own copy of a shared duty.** The duty's id would include the policy. Two copies of one delivery would each need a witness, and a case would record two activations of one obligation.
- **Pick one policy, the first or the least.** Any rule for picking one is arbitrary, and the obligation of the other policy is lost.
- **Compare only the keyed tuples in the union.** A named rule that `A` states with a constraint and `B` states without one would take the constraint into `B` silently, because `atom_constraint` has no field outside its key to differ in.
- **Keep one attachment relation, with a clause number on every row and a fixed value for a `Permit` or `Forbid` atom.** `tools/gen_schema.py` rejects an optional key field, and the fixed value would be a number that means nothing.

## Consequences

- `due2-workflows.md` v0.45 states the ids and relations in §3.1, `eliminated` in §3.5, the union in §4, the in-force rule in §5.1 and §5.2, entries in §6.2, the proof's step in §6.4, and L2. `due2-architecture.md` v0.14 restates the in-force rule.
- `odrl-compound-to-atomic-normalization.md` 0.22 extends §5.1's rule against two resources with one identity to the policies normalised together, and §5.2 says that an anonymous node is identified by its place. `due2-diagnostics.md` v0.17 extends `IdentityConflict` to the union, a step after stage 2.
- `decisions/0028` is amended: its clause number is a field of `duty_constraint`.
- `schema/collections.schema.json` is regenerated. `tools/harness/vectors.py` checks that every `Permit` and `Forbid` atom has a `root` tuple, that an `atom_constraint` names a `Permit` or `Forbid` atom, and that a `duty_constraint` names an `Oblige` atom.
- The construction of a disjunct atom's id, and of a constraint's id that stage 2 derives, is tracked with the other derived ids (#107).
- clingo-i keeps one policy per atom: `lp/explain.lp` requires exactly one `atom_policy/2`, and `lp/resolve.lp` eliminates atoms, not entries. #131 brings it to this record.
- No corpus case changes. Every case holds one policy, and cases of several policies are a gap of the case format (#1).

## Revisit when

- A policy is evaluated together with one it supersedes. `ReplacedPolicy` rejects the replaced policy (`decisions/0033`), so the union never holds both. If replaced policies are ever admitted, a duty restated by the replacement with a different deadline would be an `IdentityConflict`, and versioning would need its own rule.
