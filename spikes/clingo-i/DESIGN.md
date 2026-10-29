# clingo-i — design

clingo-i is the semantics program of `decisions/0009`. It is a generic clingo program over flattened ODRL, and it implements the `interpret` task of `spikes/README.md` § `interpret`. Python parses the vector and flattens it to facts, and every semantic step is a rule in `lp/`. This note is for a reader who wants to know how the program reaches a reply, what each file expects and produces, and what the spike declines and why. It is the Docs step of `ways-of-working.md` §14.1. The tests, with the risk each guards, are in `TESTS.md`. Per-relation reference lives in the generated documentation (`docs/`, below), and progress lives in issue #9 and `journal.jsonl`, not here.

## Vocabulary

The spec defines most terms: atom, part, finding, candidate, outstanding set, open value, entry, alternative, frontier, completion, and verdict (`due2-workflows.md` §3.1, §5.2, §6.1, §6.2, §6.3, §6.4); duty, precondition, root obligation, bearer, guard, witness condition, evidence, instance, witness, and deadline (`due2-workflows.md` §3.1, §3.3, §5.2, §5.3); and left operand, binding, source, and operator (`due2-profiles.md` §2–§5). These are the ones the program adds, or uses in a narrower sense:

- **Driver.** `flatten.py` and `values.py`: the Python that turns a vector into facts. It is syntactic, and decides nothing.
- **Duty atom.** A duty node expanded like a rule, to one action term, one relation value, and one bearer: `a(Duty, A, T, Party)`, with the sentinel `none` for a missing relation or bearer (`structure.lp`). It is not an `atom/1`, because it is matched against evidence, not against the request.
- **Item.** Anything that carries a truth value: a part (`part(X, P, action)`, `part(X, P, target)`, `part(X, P, party(F))`, or `part(X, P, cons(C))`), an atom's finding (`applies(X, P)`), a constraint node (`c(C, P)`), a duty finding (`owed(Y, P)`, `in_force(Y, P)`, `fulfilled(Y, P)`), or a step of the witness test (`check(Y, P, E, K)`, `witness(Y, P, E)`, `duty.lp`). `P` is the policy of the item's entry, and the item is read in `P`'s data space (*Data space*, below), so a node that two policies share has an item in each.
- **Truth value.** `f`, `u`, or `t`, in that order. Its **rank** is 0, 1, or 2. Elsewhere "value" is qualified: a rule's *stated value* (`stated/3`), a *read value* (what a left operand reads), a *right operand value*, and a literal's *position* in a value space (`values.py`).
- **Constraint node.** A node of an authored constraint tree: a *root* (a rule's `odrl:constraint` value or an action term's `odrl:refinement` value), a *leaf* (it has an `odrl:leftOperand`), or a *connective* node (`odrl:and`, `odrl:or`, `odrl:xone`, `dprod:not`). Its *members* are the nodes the connective combines.
- **Action term.** The value of `odrl:action`: an action IRI, or a node whose `rdf:value` is the action and which carries the refinements (IM 2.2 §2.5).
- **Layer.** Where a binding is declared: the policy graph, a selected profile module, or a core module (`due2-profiles.md` §2).
- **Misfit.** A comparison whose two values do not fit the operator: an IRI against a literal, or literals of two value spaces. A leaf that states a unit its binding does not declare is a misfit whatever is read (`decisions/0049`). A misfit is `u`, never `f`.
- **Status.** Why a `u` part is `u` (`due2-profiles.md` §3, `decisions/0016`): `missing` (no value: an absent target, party, request parameter, or context value, a state fact `missing`, or `resolved` with no value for a single-valued operand), `invalid` (a value outside the range), `conflict` (several values for a single-valued operand), `unresolved` (a state fact `unresolved`, or no fact), or `misfit`. A *duty status* is the other sense, and is always qualified: `fulfilled`, `outstanding`, `violated`, or `unknown`, the status of a duty's instance (`due2-workflows.md` §5.3, `duty.lp`).
- **Paired and opaque.** A `u` leaf whose status is `unresolved` is *paired*: its value exists and fits, so it shares a completion variable with every leaf that makes the same comparison, its complement included. Every other `u` part is *opaque*: a `u` target or party part, and a `u` leaf of any other status. An opaque part stays `u` in every completion (`decisions/0016` #1, #2).
- **Completion variable.** What a `u` finding reads (`due2-workflows.md` §6.4): `cons(D)` for a class of paired leaves with one key, `D` a leaf that names the class; `fin(I)` for a finding `I` with an opaque part, which completes the finding when the opaque part leaves it `u`; and `ful(Y, P)` for a `u` `fulfilled(Y, P)`. Only the findings `resolve.lp` reads are completed and have variables of their own: an atom's `applies`, and a precondition's `owed` and `fulfilled`. An obligation's findings move no verdict, so they have none of their own, and read only the `cons` variables they share with those findings (`completion.lp`, *Findings*). The spec calls the variable with a polarity a *literal*. "Literal" alone, in this note, means an RDF literal, `lit(Lex, Datatype)`.
- **Polarity.** How a paired leaf reads its variable: `pos`, or `neg` for a complement operator such as `neq`, which reads the variable of `eq` negated (`completion.lp`). `fin(I)` and `ful(Y, P)` are read `pos`. A constraint node has a polarity too, its *node polarity* in `live/4`: `neg` when the path from its root passes an odd number of negations, `dprod:not` or the negated members of an `xone` term, and `pos` otherwise (`explain.lp`).
- **Open node.** A constraint node that is `u` and lies on a path of `u` nodes from a `u` root of a `u` finding: an atom's constraint, or a duty's guard. Completion re-evaluates exactly the open nodes (`completion.lp`).
- **Closed.** A permission is closed in a world when it applies and one of its preconditions is owed and violated: the route can no longer be taken, so it is no candidate (`due2-workflows.md` §6.1, `resolve.lp`).
- **Contender.** An atom that takes part in conflict in a world: a candidate, or a `forbid` that applies. A *sure* contender is one in every completion, and a *may* contender one in some (`explain.lp`).
- **Performer.** The one party whose act can witness a duty atom: the request subject when it is a member of a party-collection bearer, else the bearer, or the subject when the bearer is `none` (`decisions/0018`, `duty.lp`).
- **Listed frontier.** The frontier the reply lists: read in world `k` from the findings, not from a completion, over the candidates whose state is `ready` or `pending` (`explain.lp`).
- **Unknown part.** A row of `unknown_part(X, Input, S)`: atom or duty atom `X` has a `u` part that reads `Input` with status `S` (`explain.lp`).
- **Live.** A `u` leaf is live in a finding when it lies in a disjunct of the finding's DNF that is not `f` (`due2-workflows.md` §3.5). Only a live leaf is named as an unknown part (`explain.lp`).
- **Scope.** What a constraint node refines: `rule`, under a rule's `odrl:constraint`, or `action`, under an action term's `odrl:refinement` (`due2-workflows.md` §3.1). It is part of the completion key.
- **Completion.** One assignment of `t` or `f` to every variable. With `n` variables there are `2^n`.
- **World.** An index that lets one answer set hold more than one completion. World `c` is the completion the answer set chose, and world `flip` (solve 3 only) is `c` with one variable negated. These two are the *completion worlds*. The node ranks also carry the *Kleene world* `k`: the ranks before completion, under strong Kleene logic, with the operands read from the request and the SOTW. A *witness world* `wit(E)`, one per piece of evidence `E`, reads a duty's witness conditions from `E` (`duty.lp`). `world/1` lists the completion worlds only.
- **Pivot.** The variable `flip` negates. A variable is *pivotal* when flipping it alone changes some completion's verdict (`decisions/0011` #1).
- **Remover.** In an elimination row, the atom that removes the other (`due2-workflows.md` §3.5).
- **Text id.** The name of one policy text of a vector: the first 12 hexadecimal digits of the SHA-256 hash of the text (`interpret.py`). It scopes the text's blank nodes and its left operands, `o(Iri, Text)`. Identical texts have one text id, so they are one text.
- **Data space.** What the program may read for one policy (`decisions/0050` #1): its text's triples (`text_triple/4`), the core and its own profiles' modules (`policy_layer/2`), and the request and the SOTW. `closure/4` is keyed by policy, an atom's data spaces are `space/2` (`structure.lp`) and a constraint node's `cspace/2` (`constraint.lp`), and each hierarchy comparison reads `closure/4` in its node's data spaces. Each finding is an entry's (*Item*, above), so a node that two policies share is read once in each data space, and each of its entries keeps its own finding (`decisions/0050` #4). A paired leaf's completion key carries the policy only when the leaf compares under a hierarchy, the case where two data spaces may order its value differently (`decisions/0050` #9, `completion.lp`). No policy reads another's triples, so adding a policy changes no finding of the others' entries, clingo-i's form of L11 (`due2-workflows.md` §8). Scenarios 1–3 of `conformance/cases/due2-policy-locality/` are the worked example: one edge widens the permission of the policy that states it and no other.
- **Described, reached.** A policy text *describes* a node when the modules of its layers may say what the node's predicates mean (`described/2`, `lift.lp`): in solve 0, every node its triples mention; over the corpus, the nodes it reaches and the subjects of the triples kept for it (§ Data flow). It *reaches* a node when the node is one of its policies, or the object of a triple the spike reads on a node it reaches, or an item of a list it reaches (`reached/1`). A text that never links to a node neither reaches nor describes it, as its W1, run on that text alone, would not.
- **Solve 0, 1, 2, 3.** The clingo runs of § Data flow: solve 0 once for each policy text, then solves 1 to 3 over the corpus. *Cautious* enumeration keeps the atoms true in every answer set, and *brave* the atoms true in some.
- **Decline.** A reply of kind `unsupported`, naming the feature the spike does not read (§ Declines). A *rejection* is a W1 diagnostic (`due2-diagnostics.md`): the policy is not admissible, and the reply is an `error`.

**Variable letters.** Every file uses one kind per letter:

| Letter | Kind |
|---|---|
| `X`, `Y` | an atom, or a duty atom. In an elimination row, `X` is removed, in its entry in policy `P`, and `Y` removes it; in `pre(X, Y)`, `Y` is a duty atom of the permission atom `X` |
| `P`, `Q` | a policy; in the cross-policy elimination rule, `Q` is the remover's policy and `P` the removed entry's |
| `R` | a rule |
| `A`, `B` | an action, or an action term in an atom id; `B` is the broader one in an `includedIn` edge |
| `T` | a target, or a duty's relation value: its target or its `odrl:output` |
| `F` | a function predicate (a party role, such as `odrl:assignee`) |
| `Party` | a party, or `none` for a duty atom's missing bearer |
| `Duty` | a duty node: a precondition duty, a root obligation, or both |
| `E` | a piece of evidence: an evidence record's `id` |
| `Eff` | an effect, `permit` or `forbid` |
| `Strat` | a conflict strategy (`prohibit`, `perm`, `invalid`), or the cross-policy combination in an elimination row, or `violated_precondition` in a closure row |
| `I` | an item; in `completion.lp` and `pivot.lp`, a finding, the item an atom or duty atom is completed by |
| `V` | a truth value |
| `N`, `M`, `M2` | a rank of a truth value, or a position in a value space |
| `L` | a completion variable |
| `S` | a status, such as `missing` or `unresolved`, or a duty status, such as `outstanding` |
| `Pol` | a polarity, `pos` or `neg` |
| `Base` | the positive operator a leaf asserts: the operator itself, or the one its complement negates |
| `Scope` | a scope, `rule` or `action` |
| `InstScope` | an instance scope, `member` or `grant` |
| `Attr` | an attribute of a completion key: `right(Term)`, `unit(Iri)`, or `concept` |
| `W` | a world |
| `C`, `D`, `D2` | a constraint node; `D` is a member of `C` |
| `O` | a core operator, such as `eq` or `isPartOf` |
| `NT`, `NU` | the number of an `xone`'s members that are `t`, and that are `u` |
| `Op` | a left operand, `o(Iri, Text)`: its IRI, and the text id of the policy text that binds it |
| `Lv`, `Rv` | a read value and a right operand value |
| `Lo`, `Hi` | the narrower and the broader end of a hierarchy edge |
| `K` | a kind: of term (`iri`, `lit`, `blank`), collection or node (`asset`, `party`), connective, cardinality (`one`, `set`), range, deadline (`absolute`, `relative`), or check of the witness test (`actor`, `deadline`, …) |
| `Src` | a source kind: `request`, `state`, `context`, or `witness` |
| `Prop` | an operand property |
| `Space`, `Dt`, `Tag` | a value space, a datatype, and a language tag |
| `Rg` | a range |
| `Rel` | an order relation: `lt`, `eq`, `gt`, or `u` |

Longer names are spelled out where they occur: `Term` (an RDF term, an action term among them), `List`, `Head`, `Cell`, `Item` (of an RDF list), `Layer`, `Path`, `Text` (a text id), `Key`, `Value`, `Node`, `Owner` (the rule or duty a constraint root belongs to), `Pred`, `Iri`, `Lit` (an RDF literal), `Cls`, `Sup`, `Mid`, `Fam` (a family: action, target, or a function), `Asked` (the request's target or party), `Input` (what an unknown part reads), `Prof`, `Actor` (an evidence record's actor), `Issuer`, `Ref` (a request's `reference`), `Source` (a source of a fact's answer, or `unnamed` for a fact given as one answer), `Other` (a second source, compared with `Source`), `Start` (the instant a duty's instance was first owed), `Np` (a rank inside an aggregate), and `Vp`, `Vc`, `Vk`, `Vw` (the truth value of a part, a node, a check, or a witness inside an aggregate).

## Layout

```text
main.py                the protocol loop (spikes/README.md § Protocol)
clingo_i/flatten.py    the driver: Turtle and JSON to facts; no semantics
clingo_i/values.py     the driver's value table: value spaces, positions, and instant-plus-duration sums
clingo_i/interpret.py  the four solves, the declines, and the reply
clingo_i/json_types.py the JSON value type
lp/lift.lp             triples to relations that name no IRI; several sources' answers to one fact; the hierarchies; detects what the spike does not read
lp/structure.lp        the policy, interiorisation, action terms, and expansion into atoms and duty atoms
lp/kleene.lp           truth values and their ranks
lp/constraint.lp       the authored constraint trees, and their static checks
lp/bind.lp             solve 0 only: what each policy text's own layers decide, its conflict strategy and its operands' bindings
lp/operand.lp          what each left operand's binding admits, and what it reads
lp/compare.lp          the operators, and the Kleene value of every constraint node
lp/applies.lp          the parts of an atom, and its finding
lp/duty.lp             a duty's guards and witness conditions, its findings, and its duty status
lp/completion.lp       the completion variables, and one completion of them per answer set
lp/resolve.lp          candidates, conflict, verdict, and basis of one world
lp/integrity.lp        the shape of each atom, and the integrity constraints that make a gap an error
lp/explain.lp          the eliminations, read from the findings
lp/pivot.lp            solve 3 only: a completion, its flip, and the pivotal variables
docs/                  the generated reference: program.lp includes lp/ for clindocs; python.md for mkdocstrings
tests/                 the spike's own tests (`TESTS.md`)
```

`lift.lp` is the only file that names an IRI. Every file after it reads relations named after the spec's. The files load in the order above (`PROGRAM_FILES` in `interpret.py`), `bind.lp` in solve 0 only, and each file's header names the files whose relations it reads.

**The generated reference.** `uv run --group docs mkdocs build --strict` builds `site/` (not committed): one page per `lp/` relation, with its doc block, a predicate table, and a dependency graph (clindocs), and one page for the Python modules (mkdocstrings). It is the place to look up one relation. `tests/test_docs.py` keeps it complete (`TESTS.md`).

## Data flow

1. **Init.** The driver parses every module once and keeps its facts.
2. **Flatten** (`flatten.py`). Each of the vector's policy texts is parsed alone and becomes `triple/3`, and `text_triple/4` with its text id, its blank nodes scoped by that id, a hash of the text. The corpus is the union of the texts' triples (`due2-workflows.md` §4, *Several policies are one corpus*). The core modules, and the modules of each profile a text's `odrl:profile` selects, become `module/4`, and `interpret.py` adds `layer/2` for each, naming it `core` or `module(Iri)` for each profile `Iri` that includes it, so a file that two profiles include has a layer for each. `text_layer/2` and `text_profile/2` name each text's own layers and profiles: the core, and those its `odrl:profile` selects. The request and the SOTW become facts (`flatten.py`). Then `values.py` places every RDF literal in those facts (`values.py`).
3. **Solve 0**, once for each policy text: that text's facts and its own profiles' layers, and `lift.lp` to `bind.lp` (`SOLVE_0`). W1 normalises each policy alone (`due2-workflows.md` §4), so a profile binds only the policy that names it: its conflict default, its operands' bindings, units, and schemes. Solve 0 gets the request and the SOTW too, because the declines and rejections a text raises are those it raises alone, in its own data space, and some read the world: a duty's deadline needs `effective_at` to be comparable. `bind.lp` keys each left operand by its text, `o(Iri, Text)`. The vocabulary that a module gives a node (its functions' party roles, its class's superclasses, a concept's schemes, a collection type, a timing predicate) is read only through the layers of a text that describes the node (`described/2`, `lift.lp`); in solve 0 those are the nodes of the text's triples. Solve 0 also derives `reached/1`: the text's policies, and every node they reach through a predicate the spike consumes (`consumed/2`) or through a list (`list_item/2`). The driver copies each model's binding relations (`INTERFACE`), `conflict/2`, `policy_text/2`, and its `reject` and `unsupported` atoms (`RAISED`) into the corpus facts; solve 1 derives the other declines again, over the corpus. A leaf that two texts state with different binding relations, or a policy that two texts give different conflict strategies, is an `IdentityConflict` rejection, the error the policy store raises when it publishes a corpus (`due2-diagnostics.md`). These are the only differences the spike checks: two texts that say different things of any other shared node are not rejected.
4. **Solve 1:** the corpus facts, and `lift.lp` to `duty.lp` without `bind.lp` (`SOLVE_1`). The corpus keeps what each text says apart, as W1 does (`_corpus`). A text's `triple/3` is kept only if its subject is a blank node, which is the text's own, or a node that text's solve 0 reached; `text_triple/4` keeps every triple, so each text's edges reach its own policy's `closure/4`. The driver states `described/2` for each text: the nodes its solve 0 reached, and the subjects of its kept triples. So a text that never links to a node says nothing of it, and a profile's modules speak only of the nodes that the texts selecting it describe (`test_locality.py`). For a single text it is not run: that text is the corpus, and solve 0's model is read instead. Solve 1 would load the same files but `bind.lp`, over the same triples, inputs, and layers, and read as facts the relations that solve 0's `bind.lp` derived from them, so it would derive the same atoms (`_corpus`). The program has no choice rule and is stratified, so it has exactly one model. It is read in this order, and the first hit decides:
   1. any `unsupported(Feature)`: the vector is declined, naming the smallest such feature in code-point order, so the same vector always gives the same reason;
   2. any `reject(Code, Node)`: an `error` reply, because `interpret` receives only admissible policies;
   3. any `unsupported_input(Field)`: declined, naming the smallest input field;
   4. any `unsupported_value(Reason)`: declined, naming the smallest reason (`values.py`).

   Solves 0 and 1 do not load `integrity.lp`. A decline or a rejection names what is wrong, and a failed integrity constraint would only say that something is.
5. **Solve 2:** every file but `bind.lp` and `pivot.lp`, in cautious mode, over the one world `c`. More than `VARIABLE_CAP`, 64, completion variables declines the vector as `variable-cap` (`correctness-strategy.md` §3 records why 64). `interpret.py` counts the `var/1` atoms of the first model, which `completion.lp` shows: the variables are the same in every model, but grounding leaves `var/1` atoms that no model makes true, so a count of the ground atoms would be too high (`test_variable_cap`). No model at all is an `error`: an integrity constraint failed, so the program is wrong. Otherwise, from the atoms true in every model:
   - the verdict is the one `verdict(c, Verdict)`, or `Indeterminate` if no verdict holds in every completion;
   - `basis(c, X, Role)` gives a definite verdict's basis;
   - `elim(X, P, Y, Strat)` gives `eliminated`. It reads no world, so it is the same in every model.
6. **Solve 3**, for an `Indeterminate` only: every file but `bind.lp`, in brave mode. Each model is a completion `c`, one `pivot(L)`, and the world `flip`, such that `c` and `flip` have different verdicts. The atoms true in some model give the `unknown(X)` atoms, and every `verdict(c, Verdict)` that occurs gives the range (`pivot.lp`, *The range is exact*).
7. **Reply** (§ Output).

## Worked example

This is the vector of `test_worked_example` (`tests/test_interpret.py`): the default test vector of `tests/conftest.py`, with the request's target removed. The facts below are copied from a run. `compare.lp`, *Worked example*, has a second example, for constraints.

The policy, under `prohibit`:

```turtle
ex:p a odrl:Set ; odrl:conflict odrl:prohibit ;
    odrl:permission ex:perm ; odrl:prohibition ex:forbid .
ex:perm a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a ; odrl:assignee ex:alice .
ex:forbid a odrl:Prohibition ; odrl:action odrl:use ; odrl:target ex:b .
```

The core module declares `odrl:play odrl:includedIn odrl:use`. The request asks for action `odrl:play` by assignee `ex:alice`, and names no target.

**Solve 0.** There is one policy text, so solve 1 is not run. Nothing is unsupported, and nothing is rejected. `structure.lp` finds the policy `ex:p`, `bind.lp` its strategy `prohibit`, and `structure.lp` two atoms:

- `a(ex:perm, odrl:use, ex:a, ex:alice)`, a `permit`;
- `a(ex:forbid, odrl:use, ex:b, none)`, a `forbid`. `none` is the sentinel for a rule with no assignee.

**Findings** (`applies.lp`), and the variables (`completion.lp`):

| Atom | action | target | party | finding | variable |
|---|---|---|---|---|---|
| perm | `t` (play ⊑ use) | `u` (no target) | `t` (alice) | `u` | `fin(applies(perm, p))` |
| forbid | `t` | `u` | — (no assignee) | `u` | `fin(applies(forbid, p))` |

The absent target is `missing`, so each atom's finding has an opaque part (`opaque_item/1`). It stays `u` in every completion, so each atom's parts have conjunction `u` (`pre_in(c, applies(X, p), 1)`), and each atom's own variable decides it. The run's atom ids are the full `a(R, A, T, Party)` terms, shortened here to the rule, and each finding names its entry's policy, `ex:p`, shortened to `p`. Two variables give four completions. In each, `resolve.lp` applies the atoms whose variable is `t`, and `prohibit` removes the permission when the prohibition applies:

| `fin(applies(perm, p))` | `fin(applies(forbid, p))` | applies | verdict |
|---|---|---|---|
| `t` | `t` | perm, forbid | `Deny` (perm eliminated) |
| `t` | `f` | perm | `Permit` |
| `f` | `t` | forbid | `Deny` |
| `f` | `f` | — | `NotApplicable` |

**Solve 2.** No verdict holds in all four completions, so the verdict is `Indeterminate`, and no basis row holds in all four either. Neither atom has finding `t`, so neither removes anything: `eliminated` is empty.

**Solve 3** keeps a completion and a pivot only when the flip changes the verdict. Six such pairs exist:

- pivot `fin(applies(forbid, p))`, from each of the four completions. Each pair changes the verdict, for example (`t`, `t`) `Deny` to (`t`, `f`) `Permit`. The forbid reads it, so `unknown(forbid)` holds.
- pivot `fin(applies(perm, p))`, from (`t`, `f`) and (`f`, `f`), which swap `Permit` and `NotApplicable`. From (`t`, `t`) and (`f`, `t`) the flip leaves `Deny`, so those pairs are dropped. `unknown(perm)` holds.

The verdicts `c` takes are `Deny`, `Permit`, and `NotApplicable`, so the range is `Deny` to `Permit`.

**Unknown parts** (`explain.lp`): `unknown_part(perm, target, missing)` and `unknown_part(forbid, target, missing)`.

**Reply** (refs shortened to `ex:` and `odrl:`):

```json
{"verdict": "Indeterminate", "frontier": [], "obligations": [], "exact": true,
 "verdict_basis": [{"ref": "ex:forbid", "role": "unknown"}, {"ref": "ex:perm", "role": "unknown"}],
 "eliminated": [],
 "unknown_parts": [{"ref": "ex:forbid", "input": "odrl:target", "status": "missing"},
                   {"ref": "ex:perm", "input": "odrl:target", "status": "missing"}],
 "verdict_range": {"low": "Deny", "high": "Permit"}}
```

The first completion applies both atoms, a target that is both `ex:a` and `ex:b`, and no request realises it. It is enumerated anyway, because a missing target has no value to be one of the two: the reply says only what holds whatever the target is, and that the target is missing (`decisions/0016`, the rejected alternative of sharing). With one variable for both atoms, the completions would be both or neither, and the range would stop at `NotApplicable`.

## Interfaces

What each file consumes and provides, the meaning of every relation and its arguments, and the arguments for the semantics live next to the code: the header, section prose, and doc blocks of each `lp/` file, and the module docstrings of `clingo_i/flatten.py` (the input facts) and `clingo_i/values.py` (the value table). The generated reference renders them (§ Layout, *The generated reference*). This note cites them by file and section, as `completion.lp`, *Paired variables*, and does not restate them.

## Output

`interpret` replies with:

- `verdict` and `exact: true`. The reply enumerates every completion, which is the definition itself, so it is exact. A vector it cannot enumerate within the variable cap is declined instead;
- `frontier`: under `Pending`, the listed frontier of `explain.lp`, *The listed frontier*, and `[]` under any other verdict. Each alternative is a sorted list of duty IRIs, and the alternatives are sorted by size, then by their IRIs. Candidates whose outstanding duties have one set of IRIs are one alternative (`due2-workflows.md` §6.3), so `interpret.py` collapses them. A duty atom is named by its node (`due2-workflows.md` §3.7), so two sets that differ only in which atom of one node they hold collapse too, where `due2-workflows.md` §6.3, comparing by duty id, keeps them apart: the reply could not tell the two apart;
- `obligations`: each `obligation_row(Y, S)` as `{"duty", "status"}`;
- `verdict_basis`: the rows of solve 2 for a definite verdict, or role `unknown` for each `unknown(X)` of solve 3; and, under any verdict, role `obligation` for each obligation the reply lists;
- `eliminated`: each `elim(X, P, Y, Strat)` as `{"ref", "by", "rule"}`, with `Strat` the conflict strategy, the combination, or `violated_precondition`. The reply drops the policy `P` and the remover's policy (`by_policy` in `due2-workflows.md` §3.5): `expected.eliminated` is the set of `(source, source of by_atom, rule)` triples (`due2-workflows.md` §3.7, *What the corpus asserts*), so the rows of two entries with one remover and rule are one;
- `unknown_parts`: each `unknown_part(X, Input, S)` as `{"ref", "input", "status"}`, under any verdict. `input` is `odrl:target`, the party function's IRI, or the property's IRI. The rows are sorted by their full IRIs;
- `verdict_range` `{"low", "high"}`, for an `Indeterminate` only.

Atoms are projected to their source rule, the `R` of `a(R, A, T, Party)`, and duty atoms to their duty node (`due2-workflows.md` §3.7). So the atoms of one rule share one `ref`. An elimination whose `ref` and `by` come from the same rule (under `invalid`, two atoms of one rule) is dropped, because at the authored level the rule would remove itself, and `invalid` says "other than itself".

The spike has no fallback beyond `max_mixed` or `max_frontier_vars` (`decisions/0009` #5), so `backend.toml` sets `exact_only` (`spikes/README.md`). The harness reports a scenario that states `exact: false` as `unsupported: inexact fallback` without asking the spike.

## Negation as failure

`not` never turns a missing truth value into `f`. Each use reads something that is complete by construction:

- the declared hierarchy edges (`not action_matches`, `not target_matches`, `not party_matches`, `not le_k`, `not inst`), which are closed-world (`due2-profiles.md` §6). They are complete in the case format, which records no `unresolved` world-edge answer (`conformance/README.md` § Coverage gaps), so no comparison here is `U` for a failed lookup;
- input syntax and what `lift.lp`, `structure.lp`, `constraint.lp`, and `duty.lp` derive from it: whether a family is stated, a predicate consumed, a function named, a duty inheriting or with a bearer, a node a list, a leaf or a connective, a leaf a witness leaf, a tree with a witness or a guard leaf (`has_witness`, `has_guard`), a node in a rule's tree (`rule_node`) or in a witness condition, or a duty with a deadline or a relation value. `witness_only/1`, which `evaluates(k, C)` negates, reads only these, never a rank, so the ground program has no cycle through it;
- the value table and the term shapes (`not placed`, `not kind`, `not same_type`), which decide only that a pair is a misfit, and a misfit is `u`;
- the reads: `not read_resolved`, `not card_ok`, and `not conforms` make a read `u`, never `f`;
- in `completion.lp`, over relations fixed before the choice. `not complement`, `not leaf_attr`, and `not attr_apart` decide only which variable a leaf reads and with which polarity. `not open` picks the members of an open node that keep their rank, and these are `t` or `f`, because a `u` member of an open node is open itself. `open/1` reads the ranks of world `k`, and no rule for world `k` reads another world, so the ground program has no cycle through `not open`, although `crank/3` holds the ranks of every world;
- inside one world in `resolve.lp`, where every completed value, the duty findings included, is already `t` or `f`, and over `passed/1`, a fact about the vector;
- in `explain.lp`, over relations derived from the world-`k` findings and duty statuses: the `elim` rows (a `forbid` its own policy did not remove), the closure (`not closed_by`, `not maybe_closed`), the listed frontier (`not uncertain`, `not conflicted`, `not listed_out`, `not listed_apart`, `not listed_dominated`), and the liveness walk (`not polar`, `not xone_by`), which reads node ranks and no relation it derives. A `u` finding gives no `elim` row, and the rows are only ever read as "no remover", never as a truth value. `not holds(owed(Y), f)` and `not holds(fulfilled(Y), t)` read a finding that has exactly one value (`kleene.lp`), so they mean "`t` or `u`" and "`f` or `u`";
- in `duty.lp`'s witness test, over input records, which are complete: an evidence record lists every field it has, its issuer included. So `not evidence_object`, and an actor that is not the performer (`not performer`) and that the request does not leave open (`not open_actor`), make a check `f`. For the object this reads the equality `e.object = d.relation_value` of `due2-workflows.md` §5.3, with `object` optional: evidence that records no object does not record the duty's relation value. `not attested`, `not keyed`, `not discharged`, and `not activation` read the policy, the request, and the SOTW the same way, and `not ev_reaches` and `not member_bearer` read closed-world closures. Where an input that the test needs is absent, the check is `u`, not `f`: `not effective_pos` makes `effective` `u`, and `not subject` makes `actor` `u` (`duty.lp`). The activation is the one exception: it takes the spec's default, `effective_at`. `not passed` cannot hide an undecided deadline, because a deadline that has no position declines the vector.

A missing truth value has no `holds` fact. Then an integrity constraint fails, instead of the value defaulting to `f`.

## Declines

A vector is declined, never guessed at, when it uses something the spike does not read. The scorecard (`scorecard.json`) counts the declines and their reasons.

**In the policy** (`lift.lp`). A predicate `P` on node `S` is consumed when the program reads it there:

| Predicate | Where |
|---|---|
| `rdf:type` | anywhere |
| `odrl:uid` | when it names `S` itself |
| `odrl:profile`, `odrl:conflict`, `odrl:permission`, `odrl:prohibition`, `odrl:obligation` | the policy |
| `odrl:action`, `odrl:target`, and the function predicates | anywhere: they are read on the policy, its rules, and its duties, and elsewhere they hang under a declined link (`odrl:remedy`, `odrl:consequence`) or off the policy, so declining on them would hide the feature |
| `odrl:includedIn`, `odrl:partOf`, `odrl:source`, `odrl:leftOperand`, `odrl:operator`, `odrl:rightOperand`, `odrl:unit`, the connectives, the binding attributes, `due2:conceptScheme`, `skos:broader`, `skos:narrower`, `skos:inScheme`, `skos:topConceptOf`, and `skos:hasTopConcept` | anywhere |
| `odrl:constraint` | a rule or a duty |
| `odrl:duty` | a permission, as its precondition duty |
| `odrl:output`, `due2:instanceScope` | a duty |
| `dprod:deadline`, `dprod:recurrence` | the policy, a rule, or a duty, with DPROD selected; on the policy or a rule they are rejected |
| `odrl:refinement` | an action term, or a collection (where it is rejected) |
| `rdf:value` | an action term |

A predicate is on the annotation allowlist when it is:

- `rdfs:label` or `rdfs:comment`;
- any `dct:` or `prov:` term, except `dct:isReplacedBy` on the policy, which is `reject("ReplacedPolicy", P)` (IM 2.2 §2.8);
- `skos:prefLabel`, `skos:altLabel`, `skos:hiddenLabel`, `skos:definition`, or `skos:note`;
- `dprod:offerLifecycleStatus`, `dprod:contractLifecycleStatus`, `dprod:effectiveDate`, `dprod:expirationDate`, or `dprod:acceptsOffer`, which are metadata (`due2-profiles.md` §8.1).

`unsupported(P)` holds for a predicate that is neither consumed nor allowlisted, when either:

- it is in a vocabulary namespace: `odrl:`, `due2:`, or a selected profile's IRI. Such a predicate means something, so ignoring it could change the verdict. Examples are `odrl:remedy`, `odrl:inheritFrom`, and `odrl:constraint` on a node that is not a rule or a duty; or
- it sits on a structure node (the policy, one of its rules, or one of its duties), whatever its namespace. An unknown predicate there may be a semantic extension (`odrl-compound-to-atomic-normalization.md` §3: "MUST NOT introduce additional … semantics").

Elsewhere, on asset, party, and action nodes, a predicate from another vocabulary is data the spike never reads, and it is ignored. Issue #53 adds a W1 warning for an unevaluated predicate on a structure node. The allowlist is the spike's version of that line.

**The other policy declines**, each a fixed reason:

| Reason | File | Why |
|---|---|---|
| `action: blank node without rdf:value`, `action: several rdf:value` | `structure.lp` | the action term names no single action |
| `binding: range` | `bind.lp` | a blank-node range, such as an OWL class expression, which due2 admits and the spike does not read |
| `constraint: cycle`, `constraint: dprod:not with several members`, `constraint: leaf with a connective`, `constraint: list on a scalar operator`, `constraint: two connectives` | `constraint.lp` | no reading, or none the spec settles |
| `constraint: node in two scopes` | `constraint.lp` | one node would need two completion variables (`completion.lp`) |
| `duty: also a permission or prohibition` | `structure.lp` | a rule read as a duty, which the spec gives no reading |
| `duty: evidence without effective_at` | `duty.lp` | evidence, and no `effective_at`: the `effective` check is `u`, and reads no input an `unknown_part` row can name (`due2-workflows.md` §3.5, `duty.lp`) |
| `duty: deadline not comparable` | `duty.lp` | a deadline with no position in the `instant` space, or a deadline and no `effective_at`: the status table of `due2-workflows.md` §5.3 has no row for a deadline it cannot place (`duty.lp`) |
| `duty: bearer from two functions` | `structure.lp` | two functions that play the bearer role disagree on a duty, both stated by it or both interiorised from the policy level: two bearers for one performance, which the spec does not settle |
| `duty: parent with two bearers` | `structure.lp` | a parent atom that passes two bearers to an inheriting duty |
| `duty: instance scope` | `structure.lp` | a `due2:instanceScope` other than `due2:member` or `due2:grant`, or two; no diagnostic covers it |
| `odrl:partOf: cross-kind edge`, `odrl:partOf: untyped collection` | `lift.lp` | a hierarchy the spike does not trust, on a path that a comparison of some policy walks (`walked/3`); an edge that no comparison crosses changes no reply, so it does not decline |
| `profile-conflict-defaults` | `bind.lp` | two profile defaults in one text, and no rule for which wins |
| `recurrence` | `structure.lp` | a duty's `dprod:recurrence` needs occurrences, which the spike does not compute (`decisions/0009` #7) |

**In the input** (`lift.lp`). The driver flattens every field, and `unsupported_input(Field)` names each field the program does not read:

- a `sotw.closure` edge of a relation other than `includedIn`, `partOf`, `rdf:type`, `rdfs:subClassOf`, `skos:broader`, and `skos:inScheme`;
- each `unread(Field)` (`flatten.py`).

The `flatten.py` docstring names the file that reads each other field. An empty field gives no facts, so it is not declined. When several fields hold, the smallest name wins: `request.*` before `sotw.*`.

**In the values.** `unsupported_value(Reason)`, read after the input declines: an unplaceable compared literal (`values.py`), or `value: derived string datatypes` (`compare.lp`).

**Above the cap.** More than 64 completion variables is `variable-cap` (§ Data flow).

## Errors

These are an `error` reply, not a decline:

- an unknown `odrl:profile` (`UnrecognisedProfile`);
- a policy that is not admissible (`reject`). The codes are `NoPolicy`, `MultiplePolicies`, `InvalidConflict`, `MissingAction`, `MissingTarget`, `TargetAndOutput`, `RuleReferenceCycle`, `InvalidTiming`, and `TimingOutsideDuty` (`structure.lp`); `UnsupportedConstruct` and `ReplacedPolicy` (`lift.lp`); `MalformedConstraint`, `UnsupportedOperator`, `UnsupportedConnective`, `FloatingPointOperand`, and `MixedDuration` (`constraint.lp`); `UnboundLeftOperand`, `InvalidBinding`, `ConflictingProfileDeclaration`, `RetypedOperand`, `OperandRangeMismatch`, and `WitnessOutsideDuty` (`bind.lp`); `OperatorTypeMismatch`, and `InvalidBinding` for a right operand outside the operand's scheme (`operand.lp`); `MixedDutyConstraint` (`duty.lp`); and `IdentityConflict` (`interpret.py`, after solve 0). Each is defined in `due2-diagnostics.md`;
- a malformed vector (`flatten.py`), among them a name in `request` or `sotw` whose prefix is undeclared, or that has none: it would equal no policy term and make a part `F` (#146);
- an unsatisfiable program.

`interpret` receives only admissible policies from well-formed vectors, so each of these is a defect, in the vector or in the spike.
