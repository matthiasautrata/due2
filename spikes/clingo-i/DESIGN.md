# clingo-i — design

clingo-i is the semantics program of `decisions/0009`. It is a generic clingo program over flattened ODRL, and it implements the `interpret` task of `spikes/README.md` § `interpret`. Python parses the vector and flattens it to facts, and every semantic step is a rule in `lp/`. This note is for a reader who wants to know how the program reaches a reply, what each file expects and produces, and what the spike declines and why. It is the Docs step of `ways-of-working.md` §14.1. The tests, with the risk each guards, are in `TESTS.md`. Per-relation reference lives in the generated documentation (`docs/`, below), and progress lives in issue #9 and `journal.jsonl`, not here.

## Vocabulary

The spec defines most terms: atom, part, finding, candidate, outstanding set, open value, entry, alternative, frontier, completion, and verdict (`due2-workflows.md` §3.1, §5.2, §6.1, §6.2, §6.3, §6.4); duty, precondition, root obligation, bearer, guard, witness condition, evidence, instance, witness, and deadline (`due2-workflows.md` §3.1, §3.3, §5.2, §5.3); and left operand, binding, source, and operator (`due2-profiles.md` §2–§5). These are the ones the program adds, or uses in a narrower sense:

- **Driver.** `flatten.py` and `values.py`: the Python that turns a vector into facts. It is syntactic, and decides nothing.
- **Duty atom.** A duty node expanded like a rule, to one action term, one relation value, and one bearer: `a(Duty, A, T, Party)`, with the sentinel `none` for a missing relation or bearer (§ `structure.lp`). It is not an `atom/1`, because it is matched against evidence, not against the request.
- **Item.** Anything that carries a truth value: a part (`part(X, action)`, `part(X, target)`, `part(X, party(F))`, or `part(X, cons(C))`), an atom's finding (`applies(X)`), a constraint node (`c(C)`), a duty finding (`owed(Y)`, `in_force(Y)`, `fulfilled(Y)`), or a step of the witness test (`check(Y, E, K)`, `witness(Y, E)`, § `duty.lp`).
- **Truth value.** `f`, `u`, or `t`, in that order. Its **rank** is 0, 1, or 2. Elsewhere "value" is qualified: a rule's *stated value* (`stated/3`), a *read value* (what a left operand reads), a *right operand value*, and a literal's *position* in a value space (§ Values).
- **Constraint node.** A node of an authored constraint tree: a *root* (a rule's `odrl:constraint` value or an action term's `odrl:refinement` value), a *leaf* (it has an `odrl:leftOperand`), or a *connective* node (`odrl:and`, `odrl:or`, `odrl:xone`, `dprod:not`). Its *members* are the nodes the connective combines.
- **Action term.** The value of `odrl:action`: an action IRI, or a node whose `rdf:value` is the action and which carries the refinements (IM 2.2 §2.5).
- **Layer.** Where a binding is declared: the policy graph, a selected profile module, or a core module (`due2-profiles.md` §2).
- **Misfit.** A comparison whose two values do not fit the operator: an IRI against a literal, or literals of two value spaces. A misfit is `u`, never `f`.
- **Status.** Why a `u` part is `u` (`due2-profiles.md` §3, `decisions/0016`): `missing` (no value: an absent target, party, request parameter, or context value, a state fact `missing`, or `resolved` with no value for a single-valued operand), `invalid` (a value outside the range), `conflict` (several values for a single-valued operand), `unresolved` (a state fact `unresolved`, or no fact), or `misfit`. A *duty status* is the other sense, and is always qualified: `fulfilled`, `outstanding`, `violated`, or `unknown`, the status of a duty's instance (`due2-workflows.md` §5.3, § `duty.lp`).
- **Paired and opaque.** A `u` leaf whose status is `unresolved` is *paired*: its value exists and fits, so it shares a completion variable with every leaf that makes the same comparison, its complement included. Every other `u` part is *opaque*: a `u` target or party part, and a `u` leaf of any other status. An opaque part stays `u` in every completion (`decisions/0016` #1, #2).
- **Completion variable.** What a `u` finding reads (`due2-workflows.md` §6.4): `cons(D)` for a class of paired leaves with one key, `D` a leaf that names the class; `fin(I)` for a finding `I` with an opaque part, which completes the finding when the opaque part leaves it `u`; and `ful(Y)` for a `u` `fulfilled(Y)`. The spec calls the variable with a polarity a *literal*. "Literal" alone, in this note, means an RDF literal, `lit(Lex, Datatype)`.
- **Polarity.** How a paired leaf reads its variable: `pos`, or `neg` for a complement operator such as `neq`, which reads the variable of `eq` negated (§ `completion.lp`). `fin(I)` and `ful(Y)` are read `pos`. A constraint node has a polarity too, its *node polarity* in `live/4`: `neg` when the path from its root passes an odd number of negations, `dprod:not` or the negated members of an `xone` term, and `pos` otherwise (§ `explain.lp`).
- **Open node.** A constraint node that is `u` and lies on a path of `u` nodes from a `u` root of a `u` finding: an atom's constraint, or a duty's guard. Completion re-evaluates exactly the open nodes (§ `completion.lp`).
- **Closed.** A permission is closed in a world when it applies and one of its preconditions is owed and violated: the route can no longer be taken, so it is no candidate (`due2-workflows.md` §6.1, § `resolve.lp`).
- **Contender.** An atom that takes part in conflict in a world: a candidate, or a `forbid` that applies. A *sure* contender is one in every completion, and a *may* contender one in some (§ `explain.lp`).
- **Performer.** The one party whose act can witness a duty atom: the request subject when it is a member of a party-collection bearer, else the bearer, or the subject when the bearer is `none` (`decisions/0018`, § `duty.lp`).
- **Listed frontier.** The frontier the reply lists: read in world `k` from the findings, not from a completion, over the candidates whose state is `ready` or `pending` (§ `explain.lp`).
- **Unknown part.** A row of `unknown_part(X, Input, S)`: atom or duty atom `X` has a `u` part that reads `Input` with status `S` (§ `explain.lp`).
- **Live.** A `u` leaf is live in a finding when it lies in a disjunct of the finding's DNF that is not `f` (`due2-workflows.md` §3.5). Only a live leaf is named as an unknown part (§ `explain.lp`).
- **Scope.** What a constraint node refines: `rule`, under a rule's `odrl:constraint`, or `action`, under an action term's `odrl:refinement` (`due2-workflows.md` §3.1). It is part of the completion key.
- **Completion.** One assignment of `t` or `f` to every variable. With `n` variables there are `2^n`.
- **World.** An index that lets one answer set hold more than one completion. World `c` is the completion the answer set chose, and world `flip` (solve 3 only) is `c` with one variable negated. These two are the *completion worlds*. The node ranks also carry the *Kleene world* `k`: the ranks before completion, under strong Kleene logic, with the operands read from the request and the SOTW. A *witness world* `wit(E)`, one per piece of evidence `E`, reads a duty's witness conditions from `E` (§ `duty.lp`). `world/1` lists the completion worlds only.
- **Pivot.** The variable `flip` negates. A variable is *pivotal* when flipping it alone changes some completion's verdict (`decisions/0011` #1).
- **Remover.** In an elimination row, the atom that removes the other (`due2-workflows.md` §3.5).
- **Solve 1, 2, 3.** The three clingo runs of § Data flow. *Cautious* enumeration keeps the atoms true in every answer set, and *brave* the atoms true in some.
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
| `Op` | a left operand |
| `Lv`, `Rv` | a read value and a right operand value |
| `Lo`, `Hi` | the narrower and the broader end of a hierarchy edge |
| `K` | a kind: of term (`iri`, `lit`, `blank`), collection or node (`asset`, `party`), connective, cardinality (`one`, `set`), range, deadline (`absolute`, `relative`), or check of the witness test (`actor`, `deadline`, …) |
| `Src` | a source kind: `request`, `state`, `context`, or `witness` |
| `Prop` | an operand property |
| `Space`, `Dt`, `Tag` | a value space, a datatype, and a language tag |
| `Rg` | a range |
| `Rel` | an order relation: `lt`, `eq`, `gt`, or `u` |

Longer names are spelled out where they occur: `Term` (an RDF term, an action term among them), `List`, `Head`, `Cell`, `Item` (of an RDF list), `Layer`, `Path`, `Key`, `Value`, `Node`, `Owner` (the rule or duty a constraint root belongs to), `Pred`, `Iri`, `Lit` (an RDF literal), `Cls`, `Sup`, `Mid`, `Fam` (a family: action, target, or a function), `Asked` (the request's target or party), `Input` (what an unknown part reads), `Prof`, `Actor` (an evidence record's actor), `Issuer`, `Ref` (a request's `reference`), `Start` (the instant a duty's instance was first owed), `Np` (a rank inside an aggregate), and `Vp`, `Vc`, `Vk`, `Vw` (the truth value of a part, a node, a check, or a witness inside an aggregate).

## Layout

```text
main.py                the protocol loop (spikes/README.md § Protocol)
clingo_i/flatten.py    the driver: Turtle and JSON to facts; no semantics
clingo_i/values.py     the driver's value table: value spaces, positions, and instant-plus-duration sums
clingo_i/interpret.py  the three solves, the declines, and the reply
clingo_i/json_types.py the JSON value type
lp/lift.lp             triples to relations that name no IRI; the hierarchies; detects what the spike does not read
lp/structure.lp        the policy, its conflict strategy, interiorisation, action terms, and expansion into atoms and duty atoms
lp/kleene.lp           truth values and their ranks
lp/constraint.lp       the authored constraint trees, and their static checks
lp/operand.lp          each left operand's binding, and what it reads
lp/compare.lp          the operators, and the Kleene value of every constraint node
lp/applies.lp          the parts of an atom, and its finding
lp/duty.lp             a duty's guards and witness conditions, its findings, and its duty status
lp/completion.lp       the completion variables, and one completion of them per answer set
lp/resolve.lp          candidates, conflict, verdict, and basis of one world
lp/integrity.lp        the integrity constraints that make a gap an error
lp/explain.lp          the eliminations, read from the findings
lp/pivot.lp            solve 3 only: a completion, its flip, and the pivotal variables
docs/                  the generated reference: program.lp includes lp/ for clindocs; python.md for mkdocstrings
tests/                 the spike's own tests (`TESTS.md`)
```

`lift.lp` is the only file that names an IRI. Every file after it reads relations named after the spec's. The files load in the order above (`PROGRAM_FILES` in `interpret.py`), and each file's header names the files whose relations it reads.

**The generated reference.** `uv run --group docs mkdocs build --strict` builds `site/` (not committed): one page per `lp/` relation, with its doc block, a predicate table, and a dependency graph (clindocs), and one page for the Python modules (mkdocstrings). It is the place to look up one relation. `tests/test_docs.py` keeps it complete (`TESTS.md`).

## Data flow

1. **Init.** The driver parses every module once and keeps its facts.
2. **Flatten** (`flatten.py`). The policy graph becomes `triple/3`. The core modules, and the modules of each profile the policy's `odrl:profile` selects, become `module/4`, and `interpret.py` adds `layer/2` for each, naming it `core` or `module(Iri)`, the module of the profile `Iri`. The request, SOTW, and config become facts (§ Input facts). Then `values.py` places every RDF literal in those facts (§ Values).
3. **Solve 1:** facts, and `lift.lp` to `duty.lp` (the first eight files). The program has no choice rule and is stratified, so it has exactly one model. It is read in this order, and the first hit decides:
   1. any `unsupported(Feature)`: the vector is declined, naming the smallest such feature in code-point order, so the same vector always gives the same reason;
   2. any `reject(Code, Node)`: an `error` reply, because `interpret` receives only admissible policies;
   3. any `unsupported_input(Field)`: declined, naming the smallest input field;
   4. any `unsupported_value(Reason)`: declined, naming the smallest reason (§ Values).

   Solve 1 does not load `integrity.lp`. A decline or a rejection names what is wrong, and a failed integrity constraint would only say that something is.
4. **Solve 2:** every file but `pivot.lp`, in cautious mode, over the one world `c`. More than `VARIABLE_CAP`, 64, completion variables declines the vector as `variable-cap` (`correctness-strategy.md` §3 records why 64). `interpret.py` counts the `var/1` atoms of the first model, which `completion.lp` shows: the variables are the same in every model, but grounding leaves `var/1` atoms that no model makes true, so a count of the ground atoms would be too high (`test_variable_cap`). No model at all is an `error`: an integrity constraint failed, so the program is wrong. Otherwise, from the atoms true in every model:
   - the verdict is the one `verdict(c, Verdict)`, or `Indeterminate` if no verdict holds in every completion;
   - `basis(c, X, Role)` gives a definite verdict's basis;
   - `elim(X, P, Y, Strat)` gives `eliminated`. It reads no world, so it is the same in every model.
5. **Solve 3**, for an `Indeterminate` only: every file, in brave mode. Each model is a completion `c`, one `pivot(L)`, and the world `flip`, such that `c` and `flip` have different verdicts. The atoms true in some model give the `unknown(X)` atoms, and every `verdict(c, Verdict)` that occurs gives the range (§ `pivot.lp`).
6. **Reply** (§ Output).

## Worked example

This is the vector of `test_worked_example` (`tests/test_interpret.py`): the default test vector of `tests/conftest.py`, with the request's target removed. The facts below are copied from a run. § `compare.lp` has a second example, for constraints.

The policy, under `prohibit`:

```turtle
ex:p a odrl:Set ; odrl:conflict odrl:prohibit ;
    odrl:permission ex:perm ; odrl:prohibition ex:forbid .
ex:perm a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a ; odrl:assignee ex:alice .
ex:forbid a odrl:Prohibition ; odrl:action odrl:use ; odrl:target ex:b .
```

The core module declares `odrl:play odrl:includedIn odrl:use`. The request asks for action `odrl:play` by assignee `ex:alice`, and names no target.

**Solve 1.** Nothing is unsupported, and nothing is rejected. `structure.lp` finds the policy `ex:p`, its strategy `prohibit`, and two atoms:

- `a(ex:perm, odrl:use, ex:a, ex:alice)`, a `permit`;
- `a(ex:forbid, odrl:use, ex:b, none)`, a `forbid`. `none` is the sentinel for a rule with no assignee.

**Findings** (`applies.lp`), and the variables (`completion.lp`):

| Atom | action | target | party | finding | variable |
|---|---|---|---|---|---|
| perm | `t` (play ⊑ use) | `u` (no target) | `t` (alice) | `u` | `fin(applies(perm))` |
| forbid | `t` | `u` | — (no assignee) | `u` | `fin(applies(forbid))` |

The absent target is `missing`, so each atom's finding has an opaque part (`opaque_item/1`). It stays `u` in every completion, so each atom's parts have conjunction `u` (`pre_in(c, applies(X), 1)`), and each atom's own variable decides it. The run's atom ids are the full `a(R, A, T, Party)` terms, shortened here to the rule. Two variables give four completions. In each, `resolve.lp` applies the atoms whose variable is `t`, and `prohibit` removes the permission when the prohibition applies:

| `fin(applies(perm))` | `fin(applies(forbid))` | applies | verdict |
|---|---|---|---|
| `t` | `t` | perm, forbid | `Deny` (perm eliminated) |
| `t` | `f` | perm | `Permit` |
| `f` | `t` | forbid | `Deny` |
| `f` | `f` | — | `NotApplicable` |

**Solve 2.** No verdict holds in all four completions, so the verdict is `Indeterminate`, and no basis row holds in all four either. Neither atom has finding `t`, so neither removes anything: `eliminated` is empty.

**Solve 3** keeps a completion and a pivot only when the flip changes the verdict. Six such pairs exist:

- pivot `fin(applies(forbid))`, from each of the four completions. Each pair changes the verdict, for example (`t`, `t`) `Deny` to (`t`, `f`) `Permit`. The forbid reads it, so `unknown(forbid)` holds.
- pivot `fin(applies(perm))`, from (`t`, `f`) and (`f`, `f`), which swap `Permit` and `NotApplicable`. From (`t`, `t`) and (`f`, `t`) the flip leaves `Deny`, so those pairs are dropped. `unknown(perm)` holds.

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

### Input facts

The flatten is syntactic: one fact per triple or per input field, named after the relations of `due2-workflows.md` §3.2–§3.4. It drops nothing, and it adds only the value table (§ Values). The last column names the files that read the fact. A fact no file reads is flattened anyway, so that a later reader finds it and the round-trip tests cover it.

**Graphs.**

| Fact | From | Read by |
|---|---|---|
| `triple/3`: `triple(S, P, O)` | each policy triple | `lift.lp`, `structure.lp`, `constraint.lp` |
| `module/4`: `module(Path, S, P, O)` | each triple of a selected module, `Path` the module's path. Its blank nodes are scoped by `Path` | `lift.lp` |
| `layer/2`: `layer(Path, core \| module(Iri))` | each selected module file: `core` for a core file, `module(Iri)` for a file of the selected profile `Iri`, so a profile whose module is several files is one layer; a file in both is `core` (`interpret.py`) | `lift.lp` |
| `pred_ns/2`: `pred_ns(P, NS)` | each policy predicate. `NS` is `P` up to and including its last `#` or `/` | `lift.lp` |
| `selected_profile/1`: `selected_profile(Iri)` | each `odrl:profile` value that names a shipped profile | `lift.lp` |

**Request** (`due2-workflows.md` §3.2).

| Fact | From | Read by |
|---|---|---|
| `request_reference/1` | `reference`, as given | `duty.lp` |
| `request_action/1`: `request_action(A)` | `action` | `applies.lp` |
| `request_target/1`: `request_target(T)` | `target` | `applies.lp` |
| `request_absent/1`: `request_absent(target)` | the absence of `target` | `applies.lp` |
| `request_at/1`: `request_at(Lit)` | `at` | `lift.lp`, `operand.lp` (`actionTime`) |
| `request_party/2`: `request_party(F, Party)` | each element of `parties`; `F` is the function predicate IRI | `lift.lp`, `operand.lp` (`agent`), `applies.lp`, `duty.lp` (the request subject) |
| `request_param/2`: `request_param(Prop, Value)` | each value of `params`, keyed by property IRI | `lift.lp`, `operand.lp` |
| `request_param_set/1`: `request_param_set(Prop)` | a `params` element given as a list, so an empty set is not an absent parameter | `operand.lp` |

**SOTW** (`due2-workflows.md` §3.3).

| Fact | From | Read by |
|---|---|---|
| `sotw_effective_at/1` | `effective_at` | `lift.lp`, `operand.lp` (`clock`), `duty.lp` |
| `fact/2`: `fact(Prop, Status)` | each element of `facts`. `Status` is one of `resolved`, `missing`, `invalid`, `conflict`, `unresolved` | `operand.lp` |
| `fact_value/2`: `fact_value(Prop, Value)` | each value of a `facts` element | `lift.lp`, `operand.lp` |
| `evidence/4`: `evidence(E, OccurredAt, Actor, Action)` | each `evidence` record, `E` its `id` | `lift.lp`, `operand.lp` (`actionTime` in `wit(E)`), `duty.lp` |
| `evidence_object/2`, `evidence_issuer/2` | its optional `object` and `issuer` | `duty.lp` |
| `evidence_discharges/3`: `evidence_discharges(E, Duty, Ref)` | its optional `discharges` | `duty.lp` |
| `evidence_param/3`: `evidence_param(E, Prop, Value)` | each of its `params` | `lift.lp`, `operand.lp` (`witness`) |
| `activation/2`: `activation(Key, Lit)` | each element of `activation`: an instance key or rule IRI, and its instant. `duty.lp` reads a key that is a duty's IRI, as the case format names an activation (`conformance/README.md`, SOTW) | `lift.lp`, `duty.lp` |
| `sotw_closure/3`: `sotw_closure(Pred, Lo, Hi)` | each `closure` triple, `Pred` expanded | `lift.lp`: an edge of a hierarchy the spike reads (`closure_key/1`) joins `closure/3`; any other relation declines |

**Config** (`due2-workflows.md` §3.4).

| Fact | From | Read by |
|---|---|---|
| `config_combination/1` | `combination`, a string | `lift.lp` |
| `config_violations/1` | `violations`, `ignore` or `deny` | `resolve.lp` |
| `signer/2`: `signer(Duty, Issuer)` | each `signers` element | `duty.lp` |
| `unread/1`: `unread(Field)` | `preference`, `admit_source`, `admit_age`: the case format defines no shape for them (`conformance/README.md`), so their presence is recorded and declined | `lift.lp` (declined) |

**Values** (`values.py`, § Values): `value/3`, read by `operand.lp`, `compare.lp`, and `duty.lp`; `unplaceable/2`, read by `lift.lp` and `constraint.lp`; and `plus/3`, read by `duty.lp` for a relative deadline.

A field the case format does not define, a missing required field (`action`; an evidence record's `id`, `occurred_at`, `actor`, `action`), a duplicate evidence `id`, or an unknown status is an `error`: the vector is malformed, and nothing is guessed.

**Terms.**

- **IRIs** are clingo strings.
- **RDF literals** are `lit(Lex, Datatype)`, with the lexical form exactly as written. rdflib normalises lexical forms by default, and its normalisation is lossy: it truncates fractional seconds to six digits and drops a date's timezone. The driver therefore parses with normalisation off. A plain literal is `xsd:string`. A language-tagged one is `lit(Lex, rdf:langString, Tag)`.
- **Blank nodes** are `b(Scope, Label)`. The label is rdflib's canonical one (`rdflib.compare.to_canonical_graph`), so it does not depend on the labels the parser chose. `Scope` is `"policy"` or the module's path, so blank nodes from different graphs never meet.
- **Input names** are expanded with the vector's prefixes, the same way the harness expands them. A name is a string or `{"@id": …}`. `reference` is not a name, and stays as given.
- **Input values** (`params`, `fact_value`, an evidence record's `params`) are `{"@id": …}`, read as its IRI; `{"@value": …, "@type": …}`, read as `lit` with the type expanded; `{"@value": …}`, read as `xsd:string`; or `{"@value": …, "@language": …}`. A bare string is an `error`, because it is ambiguous between a name and a string.
- **Input instants** (`at`, `effective_at`, `occurred_at`, activation instants) are `lit(I, xsd:dateTime)`.

### Values

`values.py`, under `decisions/0009` #4. clingo's integers are 32-bit, and the program compares values but never computes with them. So the driver places each RDF literal `lit(Lex, Dt)` among the facts (policy, selected modules, and inputs) in a value space, and the program reads the value table, never the lexical form.

| Space | Datatypes | Value |
|---|---|---|
| `numeric` | `xsd:decimal`, `xsd:integer`, and the integer types derived from it | the exact number; `5` and `5.00` are equal |
| `instant` | `xsd:dateTime` and `xsd:dateTimeStamp` with a timezone | the point on the UTC timeline, exact to any fractional digit |
| `date` | `xsd:date` without a timezone | the day |
| `daytime` | `xsd:dayTimeDuration`, and `xsd:duration` with only day and time components | seconds, exact |
| `yearmonth` | `xsd:yearMonthDuration`, and `xsd:duration` with only year and month components | months |
| `boolean` | `xsd:boolean` | `false` before `true` |

These are the value spaces of `due2-profiles.md` §4. The first five are ordered within the space, and none is ordered across spaces. Booleans are placed, so they compare by value, but `lt` and its kin give them no order. Strings, tokens, IRIs, and other datatypes are compared only for equality, by their terms, so they get no position.

| Fact | Meaning |
|---|---|
| `value(Lit, Space, N)` | `Lit` lies in `Space`, at position `N` |
| `plus(Start, Lit, N)` | instant `Start` plus duration `Lit` lies at position `N` in the `instant` space |
| `unplaceable(Lit, Reason)` | `Lit` has a datatype the driver must place, but it cannot place it |

- **Positions.** In the `numeric` space, if every value is an integer within 32 bits, `N` is the value itself. Otherwise, and in every other space, `N` is the dense rank `0..k−1` of the space's distinct values in the vector. Equal values get equal ranks. A rank means nothing across vectors; within one, `N₁ < N₂` exactly when the values are so ordered.
- **Sums.** A relative deadline is the activation plus a duration (`due2-workflows.md` §5.3). `plus` is given for every `instant` literal and every `daytime` or `yearmonth` literal among the facts. The sum is XSD 1.1 Part 2 Appendix E: add the months in the instant's own timezone, clamp the day to the end of the month, then add the seconds. The sums join the `instant` ranking.
- **Unplaceable values.** Nothing is truncated, rounded, or guessed. `Reason` is one of:
  - `value: xsd:double` or `value: xsd:float`: due2 has no floats (`due2-profiles.md` §4);
  - `value: dateTime without timezone`: an instant must be on the UTC timeline;
  - `value: date with timezone`: such a date is an interval, and dates in different zones overlap;
  - `value: mixed xsd:duration`: year-month and day-time components together have no single order (`due2-profiles.md` §4);
  - `value: ill-typed <datatype>`: the lexical form is not in the datatype's lexical space, or is out of its range.

  An unplaceable literal matters only if the program compares it: `unsupported_value(Reason)` holds for `unplaceable(Lit, Reason)` with `compared(Lit)`. `compared` covers the input instants, the input values, the right operand values, and the deadlines. A float or a mixed duration as a right operand is a rejection instead (`FloatingPointOperand`, `MixedDuration`, `constraint.lp`), because solve 1 reads `reject` before `unsupported_value`.

  The two timezone reasons (`off_shape/1`) are a shape the kind does not admit, not a value the spike cannot place (`decisions/0024`). Only an input instant (`input_instant/1`) declines with them. As a right operand the literal is `reject("OperatorTypeMismatch", C)`, as a deadline `reject("InvalidTiming", Duty)`, and as a value a leaf reads it is a misfit, so the leaf is `u`.

### `lift.lp`

Lifts the triples to relations that name no IRI. It provides:

- **The vocabulary.** `voc/2` maps each short name to its IRI; the registries list the conflict strategies, policy classes, the 14 function predicates of `odrl-compound-to-atomic-normalization.md` §3, the match keys (`due2-workflows.md` §5.2; v1 has one, `odrl:assignee`), the 12 core operators of `due2-profiles.md` §4 (`operator/2`, six of them `set_based/1`), the connectives (`connective/1`), the binding attributes, sources, context built-ins, and cardinalities of `due2-profiles.md` §3, the XSD datatypes a range can name (`xsd_datatype/1`, `numeric_datatype/1`, `floating_datatype/1`, `derived_from/2`), and the two RDF Schema classes that admit values of several kinds (`any_literal/1`, `any_resource/1`).
- **The lifted policy.** `type/2`, `subclass/2` (declared, direct edges from the selected modules), `has_rule/3`, `stated/3` (the value a policy or rule node states for a family), `stated_conflict/2`, and `profile_conflict/1`.
- **Terms and lists.** `term/1` collects every term of the graphs and of the inputs the constraints read, and `kind/2` gives each its shape: `iri`, `lit`, or `blank`. `list_cell/2`, `list_item/2`, and `is_list/1` read RDF lists of the policy graph; `rdf:nil` is the empty list.
- **Bindings.** `decl(Layer, Op, Key, Value)` is one attribute of a binding stated in one layer: `policy` for the policy graph, `module(Iri)` for the files of a selected profile, or `core`. `layer_rank/2` orders the layers of `due2-profiles.md` §2 from the top: the policy 0, every profile module 1, the core 2. The profile modules share a rank because they have no order.
- **Kinds.** `dt_kind(Dt, K)` gives a datatype's kind (`due2-profiles.md` §3 *Kinds*): `numeric` for every XSD numeric type, the primitive for a derived XSD type, and the datatype itself otherwise. `term_kind(Term, K)` gives a term's kind, `iri` for an IRI. `admits_kind(Rg, K)` gives the kind a stated range admits: `literal` for `rdfs:Literal`, none for `rdfs:Resource`, and `iri` for a class.
- **The hierarchies.** `closure(Key, Lo, Hi)` holds each declared `includedIn`, `partOf`, `rdf:type`, `rdfs:subClassOf`, `skos:broader`, or `skos:inScheme` edge from the policy, a selected module, or the SOTW closure. A `skos:narrower` triple is the inverse `broader` edge, and `skos:topConceptOf` and the inverse `skos:hasTopConcept` are `inScheme` edges (`decisions/0015` #5, #8); `declared_in_scheme/2` holds the memberships of the policy and the modules alone. `concept_scheme(Op, S)` holds each `due2:conceptScheme` a layer states, a union rather than a binding attribute (`decisions/0015` #6). The edges are closed-world: an undeclared edge does not hold (`due2-profiles.md` §6). `coll_kind/2` types a collection (`odrl:AssetCollection` is `asset`, `odrl:PartyCollection` is `party`), and `node_kind/2` also types an `odrl:Asset` or `odrl:Party`. `le_k(Lo, Hi, K)` is the typed `partOf` of `due2-profiles.md` §6: the transitive closure through collections of kind `K` only. It is not reflexive; its readers add identity.
- **The declines and the rejections of the graph** (§ Declines). A `partOf` edge into an untyped node, or one typed both ways, declines as `odrl:partOf: untyped collection`, and an edge from a node of one kind into a collection of the other as `odrl:partOf: cross-kind edge`: a cross-kind path is invalid (`due2-profiles.md` §6), and the spike has no reading it trusts for either. `odrl:source` off a collection, or `odrl:refinement` on a collection, is `reject("UnsupportedConstruct", Node)` (`due2-diagnostics.md`). On a collection, `odrl:source` is inert: the spike reads membership only from the `partOf` edges. `rdf:value` is read only on an action term, and declines anywhere else. A policy with `dct:isReplacedBy` is void (IM 2.2 §2.8) and is `reject("ReplacedPolicy", P)`. A policy that names a profile with no module among those the driver loaded at init is not admissible either (`UnrecognisedProfile`, IM 2.2 §3.2); the driver reports it while building the input facts, before solve 1, since it has no module to load.

### `structure.lp`

Shaped like `due2-workflows.md` §3.1, under `odrl-compound-to-atomic-normalization.md` §3, §6.2, §6.3:

| Relation | `due2-workflows.md` §3.1 counterpart |
|---|---|
| `policy(P)`, `conflict(P, Strat)` | `policy(policy_id \| conflict, …)` |
| `atom(X)`, `atom_effect(X, Eff)`, `atom_rule(X, R)`, `atom_action(X, A)`, `atom_target(X, T)` | `atom(atom_id \| effect, action, relation, relation_value, source_rule)` |
| `atom_policy(X, P)` | `root(atom_id, policy_id)`: one tuple for each policy that states the atom (`decisions/0036`) |
| `atom_party(X, F, Party)` | `atom_party`, match keys only |
| `duty_atom(Y)`, `atom_effect(Y, oblige)`, `duty_action(Y, A)`, `duty_relation(Y, T)` | `atom`, for an `Oblige` atom |
| `duty_of(Y, Duty)`, `duty_scope(Y, InstScope)`, `duty_deadline(Y, Lit)` | `duty(atom_id \| source_duty, scope, deadline?, recurrence?)` |
| `bearer(Y, Party)` | `atom_party`, for the bearer role |
| `pre(X, Y)` | `edge`, a precondition |
| `obligation(Y)` | `root` |
| `reject(Code, Node)` | a W1 rejection (`due2-diagnostics.md`) |

- **Policy.** A policy is a node typed by a policy class, or by a class that a selected module declares `rdfs:subClassOf` one. Only declared, direct edges count (`odrl-compound-to-atomic-normalization.md` §3). No policy is `reject("NoPolicy", none)`, and more than one is `reject("MultiplePolicies", P)`.
- **Conflict strategy.** The policy's own `odrl:conflict` if it states one; otherwise the selected profile's default; otherwise `invalid` (`odrl-compound-to-atomic-normalization.md` §3). Two stated values, or a value outside the three, is `reject("InvalidConflict", P)`. Two selected profiles with different defaults is `unsupported`, because the normalisation does not say which wins.
- **Interiorisation** (`odrl-compound-to-atomic-normalization.md` §6.2). For each family a root rule states nothing for, the rule takes all of the policy's values. The families are the actions, the target, and each function predicate.
- **Action terms.** `action_term(Term)` is each stated action. `action_of(Term, A)` is its `rdf:value` if it states one, or the term itself if it is an IRI. A blank node with no `rdf:value`, or a term with two, is declined (`action: blank node without rdf:value`, `action: several rdf:value`).
- **Expansion** (`odrl-compound-to-atomic-normalization.md` §6.3). One atom for each action term × target × assignee. A rule left with no action or no target is `reject("MissingAction" | "MissingTarget", R)`.
- **Atom ids.** An atom id is `a(R, A, T, Party)`: its source rule, action term, target, and assignee, or the sentinel `none` for a rule with no assignee. The id holds the action term, not the action, so that applies.lp can find the term's refinements; `atom_action/2` gives the action. Digests stay host-side (`decisions/0007`); the spike needs only ids that are distinct and stable.
- **Carried functions.** Function predicates that are not match keys are carried, not matched (`due2-workflows.md` §5.2). Expanding over them would only copy atoms whose findings are identical, so clingo-i does not expand over them. A carried function that plays the bearer role still reaches a duty: `parent_bearer/2` reads it from the rule's values.
- **Duties.** A duty node is a precondition duty (`odrl:duty` of a permission, `pre_rule/2`), a root obligation (`odrl:obligation` of the policy), or both. A duty of a duty, a remedy, and a consequence are not evaluated for access (`due2-workflows.md` §5.5). Each duty node is expanded like a rule, into duty atoms `a(Duty, A, T, Party)`: one per action term, relation value, and bearer.
  - **Relation.** `T` is the duty's `odrl:target` or its `odrl:output` (`duty_rel/2`), or `none` when it states neither. Both together is `reject("TargetAndOutput", Duty)`.
  - **Values.** A root obligation is a root rule, so it takes the policy's values for each family it leaves unstated (`odrl-compound-to-atomic-normalization.md` §6.2). A stated `odrl:output` fills the relation family, so the policy's target is not taken. A precondition duty takes no policy-level value.
  - **Inheritance.** A precondition duty that states no function, and is not a root obligation, inherits its parties from each parent atom (`inherits/1`, `due2-profiles.md` §6). One that states any function inherits none (IM 2.2 §2.6.5).
  - **Bearer.** The bearer is the party of a function that plays the bearer role (`bearer_fn/1`): `odrl:assignee`, or `dprod:subjectOfDuty` under DPROD. For each role, a value the duty states beats one interiorised from the policy level (due2-workflows.md §4, stage 2), so a root obligation that states `dprod:subjectOfDuty` is not also borne by the policy-level `odrl:assignee` it receives (`states_bearer/1`, `bearer_value/3`). An inheriting duty takes the bearer of its parent atom (`inh_bearer/3`). With none, the bearer is `none`: the request subject.
  - **The id.** The bearer is in the id, and the other inherited parties are not. A duty shared by two parents with one bearer is therefore one atom, with one instance, and shared under two bearers it is two. The corpus's atom id also holds the other inherited parties (`duty.atom_id`, `due2-workflows.md` §3.1), but a witness reads only the bearer, so two atoms that differ only in another party would have the same findings, and the reply names both by one duty IRI. An instance key adds the request's performer and reference to the atom's id (`due2-workflows.md` §5.3). clingo-i evaluates one request at a time, so its instances are already those of that request, and it needs neither.
  - **Edges.** `pre(X, Y)` fans out over every atom of the duty (`odrl-compound-to-atomic-normalization.md` §6.3), so a permission atom's preconditions are read as a conjunction. An inheriting duty gives `X` only its atoms with `X`'s bearer. A permission that is its own precondition is `reject("RuleReferenceCycle", R)`.
  - **Timing and scope.** `dprod:deadline` on a duty, when DPROD is selected, gives `duty_deadline(Y, Lit)`, `absolute` for an `xsd:dateTime` and `relative` for an `xsd:duration` (`deadline_kind/2`). Two deadlines, or one of another type, is `reject("InvalidTiming", Duty)`; a deadline or a recurrence on the policy or a rule is `reject("TimingOutsideDuty", Node)`. `due2:instanceScope` gives `duty_scope(Y, InstScope)`, `member` by default.

### `kleene.lp`

The order `f < u < t`, as `rank(V, N)`, and `two_valued/1` (`f` and `t`, the values a completed item can take). Kleene conjunction is the truth value of least rank (`#min`), disjunction that of greatest rank (`#max`), and negation maps rank `N` to `2 − N`. The integrity constraints over these values are in `integrity.lp`.

### `constraint.lp`

Reads the constraint trees the policy authored (`due2-profiles.md` §4, §5), and checks them. A rule's `odrl:constraint` values are its roots (`top_constraint/2`), and an action term's `odrl:refinement` values are its refinement roots (`top_refinement/2`). A list value gives one root per item. Each root is one conjunct of every atom of the rule or the action term (§ `applies.lp`).

- **Nodes.** `cnode(C)` is a root or a member. A node with an `odrl:leftOperand` is a `leaf(C)`, with `left(C, Op)`, `op(C, O)` (its core operator), and `right(C, Term)` (its right operand values). A node with a connective predicate is `conn(C, K)`, with `member(C, D)`. Members, like the right operand values of a set-based operator, may be one RDF list or repeated values, and both are the same set (`decisions/0013`).
- **No rewriting.** The tree is evaluated as authored, and no NNF or DNF is ever built: under strong Kleene logic the tree has the value normalisation stage 2 would give its rewrite (§ `compare.lp`, Connectives).

**Rejections** (`due2-diagnostics.md`):

| Code | When |
|---|---|
| `MalformedConstraint` | a node that is neither a leaf nor a connective; a leaf without exactly one left operand, exactly one operator, and a right operand; several right operand values under a scalar operator; a list beside other values; the empty list under a set-based operator (`decisions/0013`, amendment); a connective over the empty list (`decisions/0017`) |
| `UnsupportedOperator` | an operator IRI outside the 12 core operators |
| `UnsupportedConnective` | `odrl:andSequence` |
| `FloatingPointOperand` | an `xsd:double` or `xsd:float` right operand |
| `MixedDuration` | an `xsd:duration` right operand with both year-month and day-time components |

`odrl:andSequence` is rejected, not read as `odrl:and`. Under frozen evaluation it would be the same as `odrl:and`, but `due2-diagnostics.md` rejects it, and the spike follows the spec.

**Declines.** A node the spec gives no reading, or only an unsettled one: a leaf that is also a connective; a node with two connectives; `dprod:not` without exactly one member; a cycle (`reach_c/2`, the transitive closure of `member/2`); a list, the empty list included, as the one value of a scalar operator.

### `operand.lp`

Binds each left operand a leaf uses (`used/1`), and reads its values (`due2-profiles.md` §2, §3).

**Binding** (`decisions/0014` #1–#3). A layer *declares* an operand when it states any of its binding attributes: source, property, range, cardinality, or allowed operators (`declares/2`). The binding is assembled from the layers in two parts:

- **Where it reads.** The source and the property each come from the highest layer that states them (`where_rank/3`). A policy may rebind a baseline operand, as `due2-rebound-pay-amount` rebinds `odrl:payAmount` to the request.
- **Its type.** The range, cardinality, and allowed operators come from the lowest declaring layer, the operand's *owner* (`owner_rank/2`). An attribute the owner omits has its default, and the default counts as stated: `owned(Op, cardinality, due2:one)` when the owner gives no cardinality. A higher layer that states a type attribute with other values than the owner's, defaults included, is `reject("RetypedOperand", C)` (`retyped/1`).

`bdecl(Op, Key, Value)` is the assembled binding. Two profile modules that state one attribute of an operand with different values are `reject("ConflictingProfileDeclaration", C)` (`module_differs/1`): the modules have no order, so neither wins, and such an operand gets no binding and no `UnboundLeftOperand`. Modules that agree are one declaration. `tools/check_corpus.py` resolves bindings by the same rules (`Bindings`).

The binding gives:

- `src(Op, Src)` and `prop(Op, Prop)`, exactly one each, or `reject("UnboundLeftOperand", C)`. A source outside the four, a property that is not an IRI, or a context property that is not a built-in is `reject("InvalidBinding", C)`. The `witness` source is read only in a duty's conditions, so a leaf on it in a tree of any other structure node is `reject("WitnessOutsideDuty", C)`. `node_tree/2` (`constraint.lp`) gives each node's trees: its constraint roots, and the refinement roots of the action terms it states. A tree shared by a duty and a rule is in both, and so is rejected.
- `card(Op, K)`: `set` if the binding states `due2:set`, otherwise `one`. Another cardinality IRI, or two, declines as `binding: cardinality`.
- `range_kind(Op, K)`: the kind the owner's range admits (`admits_kind/2`). `rdfs:Resource` admits every kind, so it has no `range_kind`. Two ranges, or one that is not an IRI, decline as `binding: range`.
- `prop_range_kind(Op, K)`: the kind of the `rdfs:range` that some layer states for the property `Op` reads. When no value has both kinds, the binding is `reject("OperandRangeMismatch", C)` (`decisions/0014` #5): every value the property gives would fail the range. Two kinds that differ have no value in common, except that `literal` shares its values with every kind but `iri`. An operand that reads itself, such as `odrl:payAmount`, is not compared with itself.
- `allowed(Op, Iri)`, the `due2:allowedOperator` values. An operator outside a stated list is `reject("OperatorTypeMismatch", C)`. Without a list every core operator is allowed. `due2-profiles.md` §3 narrows that default by the operators' signatures over the range, and the spike does not check the narrowing: a leaf whose operator does not fit its range evaluates as a misfit, `u`, where W1 would reject it. `interpret` receives only admissible policies, so only a negative vector can tell.

**Concept schemes** (`decisions/0015`). `scheme(Op, S)` gives the schemes of a used operand, and `has_scheme(Op)` makes its `eq`, `neq`, `isAnyOf`, and `isNoneOf` compare IRIs under `skos:broader` (§ `compare.lp`). Three checks of `decisions/0015` #8 reject the binding's constraints: an IRI right operand in none of the schemes by `declared_in_scheme/2` (`declared_concept/2`; normalisation does not see the SOTW, so its memberships do not count) and an operator outside `concept_operator/1` are `reject("OperatorTypeMismatch", C)`, and a scheme on a datatype range is `reject("InvalidBinding", C)`. A literal is not a concept, so a literal right operand is not checked.

`isA` over a set-valued operand is `reject("OperatorTypeMismatch", C)`, and so is an operator of one left value over one (`single_left/1`: `eq`, `neq`, the order operators, `isAnyOf`, `isNoneOf`; `decisions/0025`).

**Range conformance** (`conforms/2`, the defaults of `due2-profiles.md` §3). Without a range, or with `rdfs:Resource`, every value conforms. Otherwise a value conforms when its kind is the range's: an IRI to a class, an `xsd:dateTimeStamp` to `xsd:dateTime`. A `numeric` range also needs the literal placed in the numeric space, so `5` and `5.00` both conform to `xsd:decimal`, but an ill-typed number does not, nor an `xsd:double`, which has no exact equality (`due2-profiles.md` §4). `rdfs:Literal` takes any literal. A right operand value that does not conform is `reject("OperatorTypeMismatch", C)`.

**Reads.** An operand is read once in each world that evaluates a leaf on it (`read_in(W, Op)`): world `k`, and the witness world `wit(E)` of each piece of evidence `E` (`read_world/1`, § `duty.lp`). The completion worlds read nothing, because their leaves take a variable's value (§ `completion.lp`). `read_value(W, Op, Term)` is what the source gives in world `W`, and `read_resolved(W, Op)` says the source answered:

| Source | Answered when | Values |
|---|---|---|
| `request` | the request has the parameter, or gives it as a list, even an empty one | the parameter's values |
| `state` | the SOTW fact has status `resolved` | the fact's values |
| `witness`, in `wit(E)` only | the evidence `E` has the parameter | its values |
| `context`, `agent` | the request names an assignee | the assignee |
| `context`, `clock` | the SOTW has `effective_at` | that instant |
| `context`, `actionTime`, in `k` | the request has `at` | that instant |
| `context`, `actionTime`, in `wit(E)` | always | `E`'s `occurred_at` (`due2-workflows.md` §5.3) |

A fact with any other status (`missing`, `invalid`, `conflict`, `unresolved`), no fact at all, or an absent parameter or context value leaves the read unanswered, so `read_resolved/2` fails. A `witness` read in world `k` is never answered, but no world-`k` leaf makes one: world `k` skips the witness conditions (§ `duty.lp`), and a rule's leaf on the witness source is rejected (`WitnessOutsideDuty`, above). Then, in each world:

- `card_ok(W, Op)`: a `set` operand takes any number of values, none included; a `one` operand takes exactly one. Two or more for `one` is `MultipleValues`, and none is no value (`due2-profiles.md` §3).
- `nonconforming(W, Op)`: some read value is outside the range, `TypeMismatch` (`due2-profiles.md` §3), or is an IRI in none of the operand's schemes by any membership, the SOTW's included (`read_concept/2`, `decisions/0015` #4).
- `read_ok(W, Op)` when the read is resolved, its count fits, and every value conforms; `read_u(W, Op)` otherwise. A `u` read makes every leaf on it `u`, never `f` (`ways-of-working.md` §5.1). `integrity.lp` checks that every read is exactly one of the two.
- `read_status(W, Op, S)`, for a `u` read, the status of `decisions/0016`: a state fact's own status; `unresolved` for no fact; `missing` for an unanswered request, witness, or context read, or a resolved `one` read with no value; `conflict` for a resolved `one` read with several; `invalid` when a value is outside the range or its schemes. `integrity.lp` checks that each `u` read has exactly one.

### `compare.lp`

Gives every constraint node its rank in each world that evaluates it, `crank(W, C, N)`, and every node item its truth value, `holds(c(C), V)`, its rank in world `k`. `evaluates(W, C)` says which nodes world `W` evaluates: for `k`, every node but the witness-only ones of a duty (`witness_only/1`, § `duty.lp`); for a witness world `wit(E)`, the nodes of the witness conditions; and for a completion world, the open nodes (§ `completion.lp`). The leaf rules serve `k` and the witness worlds, which read operands, and the connective rules serve every world.

**Leaves.** A leaf on a `u` read has rank 1. On an `ok` read, `cpair(W, C, Lv, Rv)` pairs each value read in world `W` with each right operand value, and the pair is compared on its own. The comparisons below read only the two values, so they carry no world:

- **Equality**, `eqr(Lv, Rv, N)`. Two IRIs by identity. Two placed literals by position, if they lie in one space. Two unplaced literals by identity, if they have the same datatype (and, for `rdf:langString`, the same tag): that is "strings by code point" (`due2-profiles.md` §4). Every other pair is a misfit, rank 1: an IRI against a literal, a blank node, two spaces, a placed against an unplaced literal, two unplaced datatypes.
- **Order**, `cmpr(Lv, Rv, Rel)`: `lt`, `eq`, or `gt` within one ordered space, and `u` otherwise. `order_rank(O, Rel, N)` reads `lt`, `lteq`, `gt`, and `gteq` off the relation, and `u` gives rank 1.
- **Concepts**, `ceqr(C, Lv, Rv, N)`. On a leaf whose operand has a scheme, two IRIs are a concept pair (`concept_pair/3`), and `Lv = Rv` reads as `Lv ⊑ Rv`: `t` when `Lv` is `Rv`, or a chain of `skos:broader` edges (`above/2`, the transitive closure) leads from `Lv` to `Rv`; `f` otherwise (`decisions/0015` #3, #5). A read concept outside the schemes never gets here, since its read is `invalid`. Every other pair, a literal on either side included, has its `eqr/3` rank, so a string against a concept is a misfit.
- **Hierarchies.** `isPartOf` and `hasPart` ask `Lo ⊑ Hi` (`ler/3`): two IRIs by identity or the typed `partOf` closure `le_k/3`, and anything else a misfit. `isA` asks whether the read IRI is an instance of the class (`inst/2`): one `rdf:type` edge, then `rdfs:subClassOf` edges, all from `closure/3`.

**The operators** combine the pairs (`due2-profiles.md` §4). `eq`, `neq`, and the order operators compare the one read value with the one right value; `neq` is the negation of `eq`. `any_eq(W, C, Rv, N)` is the disjunction, over the values read in world `W`, of `= Rv`. Each `=` is `ceqr/4`, so on a concept-scheme operand `neq` and `isNoneOf` exclude every concept below a right value. `isAnyOf` is the greatest `any_eq` over the right values, and `isNoneOf` its negation. `isAllOf` is the least `any_eq` over the right values: every right value is read. `isPartOf` is the least, over the read values, of "part of some right value", and `hasPart` the least, over the right values, of "part of some read value"; with no read values `isPartOf` holds vacuously. `isA` is the least over the listed classes. The aggregates carry their identities (`#max { 0; … }`, `#min { 2; … }`), so an empty set has the value the operator's quantifier gives it.

**Connectives.** `and` is the least rank of its members, `or` the greatest, and `dprod:not` maps rank `N` to `2 − N`. Strong Kleene logic gives the tree the same value as its NNF and its DNF, because De Morgan's laws, double negation, and distributivity hold in it, so these rules realise the structural rules of normalisation stage 2 without rewriting. `xone` means its expansion, the disjunction of its terms, each term a member conjoined with the negation of every other member: ⋁ᵢ (aᵢ ∧ ⋀ⱼ≠ᵢ ¬aⱼ) (`due2-profiles.md` §5). The program counts instead: `xone_count(W, C, NT, NU)` says that `NT` members of `C` are `t` and `NU` are `u` in world `W`. The `xone` is `t` when NT = 1 and NU = 0; `f` when NT ≥ 2, or when NT = NU = 0; and `u` otherwise. That is the value of the expansion for any values of the members, case by case:

- **NT ≥ 2.** Every term conjoins the negation of some `t` member, which is `f`, so every term is `f`, and so is their disjunction.
- **NT = 1, NU = 0.** The `t` member's term conjoins `t` with the negations of `f` members, so it is `t`, and so is the disjunction.
- **NT = 1, NU ≥ 1.** The `t` member's term conjoins `t` with negations that are `t` or `u`, at least one `u`, so it is `u`. Every other term conjoins the `t` member negated, so it is `f`. The disjunction is `u`.
- **NT = NU = 0.** Every member is `f`, so every term is `f`.
- **NT = 0, NU ≥ 1.** A `u` member's term conjoins `u` with negations that are `t` or `u`, so it is `u`, and no term is `t`, since no member is. The disjunction is `u`.

The expansion has a term for each position in the list, while `member/2` holds a set of nodes. They agree because `constraint.lp` rejects a list that names one node twice (`decisions/0022` #1), so each node is one position. Two members with the same content are two nodes, and so two positions, whether they are compound or leaves; `constraint.lp` rejects two such leaves under an `xone` too (`decisions/0022` #2), but as an authoring error, not for this agreement. Counting reads `t xone u` as `u`, as the expansion does, not as `t`, which "exactly one is `t`" would give. A count that skipped the `u` members would give that `t`, and the mutant `xone-unknown-as-false` of `TESTS.md` is that shortcut.

**Units.** `odrl:unit` labels a right operand (`unit/2`, `constraint.lp`), and the completion key includes it (§ `completion.lp`). It converts nothing, and what a unit means for a comparison is open (#67), so a leaf compares the values alone: `5` with unit `ex:EUR` equals a read `5` (`test_unit_labels_without_converting`).

**Two datatypes of one kind.** Values of one kind compare by value, with or without a range (`decisions/0014` #6). Each value space of § Values holds one kind, so placed literals need no rule: `5` equals `5.0`. Two unplaced literals of one kind and different datatypes, such as an `xsd:token` and an `xsd:string`, decline as `value: derived string datatypes`: their values are their lexical forms after the whitespace facet, which the spike does not apply. Values of different kinds are a misfit, `u`.

**Worked example.** This is the vector of `test_constraint_worked_example`, copied from runs. The rule `ex:r` permits `odrl:use` on `ex:a`, and the request matches its action and target, so only the constraint part decides:

```turtle
ex:r odrl:constraint ex:c .
ex:c odrl:and ( ex:c1 ex:c2 ) .
ex:c1 odrl:leftOperand ex:purpose ; odrl:operator odrl:isAnyOf ;
    odrl:rightOperand ex:research, ex:teaching .
ex:c2 odrl:leftOperand ex:count ; odrl:operator odrl:lteq ; odrl:rightOperand 5 .
ex:purpose dprod:operandSource dprod:requestSource ; dprod:operandProperty ex:purpose .
ex:count dprod:operandSource dprod:requestSource ; dprod:operandProperty ex:count .
```

| Request `params` | Reads | Leaves | `crank(k, ex:c, N)` | Reply |
|---|---|---|---|---|
| purpose `ex:marketing` | `read_ok(ex:purpose)`, `read_u(ex:count)` | `eqr(ex:marketing, ex:research, 0)` and `eqr(ex:marketing, ex:teaching, 0)`, so `any_eq` is 0 for both and `crank(k, ex:c1, 0)`; `crank(k, ex:c2, 1)` | 0 | `NotApplicable` |
| purpose `ex:research` | as above | `eqr(ex:research, ex:research, 2)`, so `crank(k, ex:c1, 2)`; `crank(k, ex:c2, 1)` | 1 | `Indeterminate`, from `NotApplicable` to `Permit` |
| purpose `ex:research`, count `3` | both `ok` | `cpair(k, ex:c2, lit("3", xsd:integer), lit("5", xsd:integer))`, `crank(k, ex:c2, 2)` | 2 | `Permit` |
| purpose `ex:research`, count `7` | both `ok` | `crank(k, ex:c2, 0)` | 0 | `NotApplicable` |

The first row is the point of Kleene evaluation: `ex:count` is unknown, but `f ∧ u` is `f`, so the unknown does not matter, and the atom does not apply. In the second row `t ∧ u` is `u`, the constraint part is `u`, and so is the atom's finding. Completion decides it (§ `completion.lp`): `ex:c` and `ex:c2` are open, and `ex:c1` keeps its `t`. `ex:c2` reads one variable, so there are two completions. The permission applies when the variable is `t`, which gives `Permit`, and not when it is `f`, which gives `NotApplicable`. The reply names `ex:r` with role `unknown`.

### `applies.lp`

`due2-workflows.md` §5.2. Each atom gets its parts (`part_of(X, I)`) and a truth value for each (`holds(I, V)`):

- **action** is `t` when `request_action ⊑ atom_action` under the reflexive-transitive `includedIn` closure, and `f` otherwise. Only a request action that is the atom's action, or narrower, matches.
- **target** is `u` when `request_absent(target)` holds. Otherwise it is `t` when the requested asset is the target, or part of it under the typed `partOf` closure (`le_k(Asked, T, asset)`), and `f` otherwise (`target_matches/1`).
- **party** is checked for each `atom_party(X, F, Party)` with `F` a match key. It is `u` when the request names no party for `F`, `t` when a named party is `Party` or part of it (`le_k(Asked, Party, party)`), and `f` otherwise (`party_matches/2`). An atom with no assignee has no party part.
- **constraint**, `part(X, cons(C))`, for each root `C` of `atom_constraint(X, C)`: the rule's constraint roots and the action term's refinement roots. It takes the node's value, `holds(c(C), V)`.
- **applies** is the Kleene conjunction of the atom's parts, the least of their ranks (`#min`). Every atom has an action and a target part, so the set is never empty.

These are the values before completion. `completion.lp` gives each world's value of every `u` part and finding.

### `duty.lp`

`due2-workflows.md` §5.2. A duty's conditions are its constraint roots and the refinement roots of its action terms (`duty_root/2`); a root obligation that takes the policy's action takes its refinements too. They split into guards, which decide whether the duty is owed, and witness conditions, which decide whether a piece of evidence fulfils it:

- a leaf is a *witness leaf* when its left operand is bound to `due2:witnessSource`, or reads the context property `due2:actionTime`, the evidence's `occurred_at` (`witness_leaf/1`, `due2-workflows.md` §5.3);
- a conjunction splits into its members, recursively (`duty_part/2`), and each conjunct that is not a conjunction is a *split part* (`split_part/2`);
- `has_witness(C)` and `has_guard(C)` say that the tree under `C` has a witness leaf, or a leaf that is not one;
- a split part with no witness leaf is a guard (`guard(Y, C)`), and one whose leaves are all witness leaves is a witness condition (`witness_cond(Y, C)`);
- a split part with both, an `or`, `xone`, or `dprod:not` over a guard leaf and a witness leaf, is `reject("MixedDutyConstraint", C)` (`due2-diagnostics.md`). A guard is read once, in world `k`, before any evidence, and a witness condition once per piece of evidence, so a node that mixes them has no single place to be read.

For example, take a duty whose constraint is `ex:g eq ex:v and ex:w eq ex:v and ex:t eq ex:v`, with `ex:g` bound to the state, `ex:w` to `due2:witnessSource`, and `ex:t` to the context property `due2:actionTime`. The `and` splits into three parts: one guard, the `ex:g` leaf, and two witness conditions (`test_conjunction_splits_into_guard_and_witness`).

**The worlds of the witness conditions.** A witness condition has no value against the request: its leaves read the evidence, and world `k` has none. So world `k` skips the nodes that lie in a witness condition (`in_witness/1`), and the conjunctions of a duty's conditions with a witness condition below them, since the findings take the guards one by one. These are the witness-only nodes (`witness_only/1`). A node that also lies in a rule's tree (`rule_node/1`) is not one: world `k` evaluates it for the rule. That happens to a `due2:actionTime` leaf that a rule and a duty share, which reads the request's `at` in `k` and the evidence's `occurred_at` in `wit(E)` (§ `operand.lp`). Each piece of evidence `E` has its world `wit(E)`, which evaluates every node of every witness condition (`evaluates(wit(E), C)`), so `compare.lp` gives each one a rank `crank(wit(E), C, N)` from what `E` records. One algebra serves the request and the evidence: the same leaf and connective rules, in another world.

**Owed and in force** (`due2-workflows.md` §5.2), in world `k`:

- `owed(Y)`, for a precondition duty atom: the Kleene conjunction of its guards, `t` when it has none. `due2-workflows.md` §5.2 makes an unguarded duty owed whenever its parent applies. The finding does not read the parent: W3 reads it only for a parent candidate (`due2-workflows.md` §6.1).
- `in_force(Y)`, for a root obligation atom: the Kleene conjunction of `policy_match(Y, N)` and its guards. `policy_match` is the Kleene disjunction, `f` when there are none, over the `Permit` and `Forbid` atoms of the obligation's policy (`obligation_policy/2`) of `matched(X, N)`: the conjunction of the atom's action, target, and party parts (`match_part/2`), its constraint parts left out (`cons_part/1`). An obligation is in force when its policy matches the request, not when its own action does: in the worked example below, the request plays and the duty is to delete.
- `instance(Y)` when `owed(Y)` or `in_force(Y)` is `t` or `u`. Only an instance is tested against the evidence. A `u` instance is tested too, so that its `fulfilled` finding has a value whatever the guard turns out to be.

**The witness test** (`due2-workflows.md` §5.3). Each instance is paired with each piece of evidence (`witness_pair(Y, E)`), and each pair has seven checks, `check(Y, E, K)` for each `check_kind(K)`, each an item. `occurred_pos(E, N)` and `effective_pos(N)` place the evidence's `occurred_at` and the SOTW's `effective_at` in the `instant` space:

| Check `K` | `t` when | `f` when | `u` when |
|---|---|---|---|
| `effective` | `occurred_at` ≤ the SOTW's `effective_at` | `occurred_at` is later | the SOTW has no `effective_at`, which declines (below) |
| `deadline` | the duty has no deadline, or `occurred_at` ≤ the deadline (`deadline_at/2`) | `occurred_at` is later | never: an unplaceable deadline declines |
| `action` | the evidence's action is the duty's, or included in it (`ev_reaches/2`) | otherwise | never: the closure is closed-world |
| `object` | the duty has no relation value, or the evidence's object is it | otherwise, an evidence record with no object included | never |
| `actor` | the actor is the performer (`performer/2`): the request subject (`subject/1`) when it is a member of a party-collection bearer (`member_bearer/2`); else the bearer; or the subject when the bearer is `none` | the actor is someone else | the request names no subject, and the bearer is `none`, or a collection the actor is a member of (`open_actor/2`, for the collection) |
| `signer` | the config lists no signer for the duty (`signed/1`), or lists the evidence's issuer (`admitted/2`) | it lists signers, and not the issuer | never |
| `discharges` | the instance is not keyed on the request (`keyed/1`), or the evidence discharges the duty under the request's `reference` (`discharged/2`) | it is keyed, and the evidence does not | never |

The collection rows are `decisions/0018`: each member bears a duty whose bearer is a party collection, so the subject's own act witnesses it, and another member's does not. With no subject, a member's act is `u`, since that member may be the subject, and a non-member's is `f`.

The deadline is the absolute one, or the activation plus a relative one (`plus/3`). The activation (`activation_at/2`) is the SOTW's record for the duty's IRI (`activated/1`), the key the case format gives an activation, or `effective_at` when the SOTW has none (`due2-workflows.md` §5.3). An instance is keyed when its scope is `grant` and the request has a `reference`; without one, a `grant` duty falls back to `member`.

**Fulfilled and status.** `witness(Y, E)` is the Kleene conjunction of the seven checks and of the ranks of `Y`'s witness conditions in world `wit(E)`. `fulfilled(Y)` is the Kleene disjunction of the witnesses, `f` when there is no evidence. `passed(Y)` holds when the deadline is earlier than `effective_at`. It is fixed per evaluation, since both instants are inputs, so it is a fact about the vector, not a finding. The duty status `status(k, Y, S)` is the table of `due2-workflows.md` §5.3:

| `fulfilled(Y)` | `passed(Y)` | Duty status |
|---|---|---|
| `t` | either | `fulfilled` |
| `f` | no | `outstanding` |
| `f` | yes | `violated` |
| `u` | either | `unknown` |

A duty with no deadline never passes, so it is never `violated`. The table has no row for a deadline it cannot place against `effective_at`, so a duty whose deadline has no position, or a vector with a deadline and no `effective_at`, declines as `duty: deadline not comparable`.

A `u` duty finding, `owed`, `in_force`, or `fulfilled`, is completed like an atom's (§ `completion.lp`), and the reply names the inputs that made it `u` (§ `explain.lp`). One `u` has no such input: the `effective` check of evidence when the SOTW has no `effective_at`. `effective_at` is not a field an `unknown_part` row can name (`due2-workflows.md` §3.5), so the reply could not say what was unknown, and the vector declines as `duty: evidence without effective_at`.

**Worked example.** This is the vector of `test_late_witness_is_not_timely`, with the relations copied from a run. A permission to use `ex:a` travels with an obligation to delete it by 1 May:

```turtle
ex:p a odrl:Set ; odrl:profile dprod: ; odrl:target ex:a ;
    odrl:permission ex:perm ; odrl:obligation ex:o .
ex:perm a odrl:Permission ; odrl:action odrl:use .
ex:o a odrl:Duty ; odrl:action odrl:delete ;
    dprod:deadline "2026-05-01T00:00:00Z"^^xsd:dateTime .
```

The request asks `ex:alice` to play `ex:a` at 1 June, with `reference` `req-1`. The SOTW is effective at 1 June, and records one piece of evidence, `ex:e1`: `ex:alice` deleted `ex:a` on 15 May. With `O` the obligation's atom `a("ex:o", "odrl:delete", "ex:a", none)`:

1. `matched(a("ex:perm", "odrl:use", "ex:a", none), 2)`: `odrl:play` is included in `odrl:use`, and the target is `ex:a`. So `policy_match(O, 2)`, and with no guard `holds(in_force(O), t)` and `instance(O)`.
2. `witness_pair(O, "ex:e1")`. Six checks are `t`: `effective`, `action`, `object`, `actor` (the bearer is `none` and `ex:alice` is the subject), `signer`, and `discharges`. `deadline` is `f`, since 15 May is after 1 May. So `holds(witness(O, "ex:e1"), f)`, and `holds(fulfilled(O), f)`.
3. `deadline_at(O, 0)`, since 1 May is the earliest instant of the vector and positions are dense ranks from 0 (§ Values). `effective_at` is later, so `passed(O)`, and `status(k, O, violated)`.

Evidence that came too late is no witness: the duty was violated on 1 May, and deleting the asset afterwards does not undo that.

### `completion.lp`

`due2-workflows.md` §6.4, `decisions/0012`, `decisions/0016`. Completion decides four kinds of finding: an atom's `applies(X)`, and a duty atom's `owed(Y)`, `in_force(Y)`, and `fulfilled(Y)` (`duty_item/1`, § `duty.lp`). `u_item(I)` holds for a finding that is `u`. A `u` finding reads completion variables, and `reads(I, L)` collects them per finding. A `u` part of an `f` finding reads none, because the finding is `f` in every completion. A choice gives each variable `t` or `f` in world `c`, so solve 2's answer sets are exactly the completions. In each world a finding that is not `u` keeps its value. A `u` `applies`, `owed`, or `in_force` is re-derived from its parts in the world, by the same conjunction that gives the finding its world-`k` value in `duty.lp`, taken in the world (`pre_in/3`): an atom's parts (`part_in/3`); the guards of `owed` (`root_in/4`); and the policy match and the guards of `in_force`. The finding is that conjunction when it is `t` or `f`, and the value of `fin(I)` when it is `u`. A `u` `fulfilled(Y)` takes the value of `ful(Y)`. `completed_item/1` lists what must have a value in every world: every atom's finding and every duty finding.

**Duty findings.** Each is completed according to where its `u` comes from:

- **Guards.** A duty's `odrl:constraint` is a `top_constraint/2` of the duty node (`duty.lp`), so a guard is a tree in scope `rule` (`scope/2`, `constraint.lp`), completed node by node as an atom's constraint is. A guard leaf that makes a rule leaf's comparison reads the rule leaf's variable: where the rule's constraint holds, so does the guard (`test_guard_and_rule_leaf_share_a_variable`).
- **The policy match** of `in_force` is `u` only through a `u` target or party part of a rule (§ `duty.lp`), which is opaque, so a `u` match makes `in_force` opaque. The match is not re-derived in the world: it keeps rank 1, and `fin(in_force(Y))` decides the finding, a variable apart from each rule's own `fin`, as `decisions/0016` #2 asks of opaque parts (`test_missing_target_leaves_rule_and_obligation_unknown`).
- **Fulfilment.** A `u` `fulfilled(Y)` is not re-derived either, because nothing that makes it `u` is paired. A witness leaf (`witness_leaf/1`, `duty.lp`) reads the evidence in `wit(E)`, through a `witness` operand or a context built-in such as `due2:actionTime`, and only a `state` read has status `unresolved` (`read_status/3`, `operand.lp`). The actor check is `u` only on an absent subject, which is opaque. So `fulfilled(Y)` shares no variable with any other finding, and `ful(Y)` completes it soundly: the completions remain a superset of the realisable ones (below).

**Statuses.** Each `u` leaf has one status (`leaf_status/2`): its operand's read status in world `k` from `operand.lp` (`read_status/3`), or `misfit` when the read is `ok` and the leaf is still `u`, which only a misfit comparison makes it. A leaf whose status is not `unresolved` is opaque (`opaque_leaf/1`). An unresolved value exists and fits its operator, so of a leaf and its complement exactly one holds, and pairing them is sound. A missing, invalid, conflicting, or misfit value gives no such guarantee: for `"abc"`, neither `lt 5` nor `gteq 5` holds (`decisions/0016`, § Question).

**Opaque parts.** A `u` target part, a `u` party part, and an opaque leaf in an opened tree make an atom's finding opaque (`opaque_item/1`); a `u` policy match makes `in_force` opaque; and an opaque leaf in an opened guard makes `owed` or `in_force` opaque. The finding `I` gets the variable `fin(I)`. In each world an opaque target or party part keeps rank 1, and so do an opaque leaf and a `u` policy match. A connective above it is re-evaluated under strong Kleene logic, so the tree, and the finding's conjunction, can stay `u` in the world. Then `fin(I)` decides the finding. When the paired leaves settle the tree anyway, `fin(I)` is read but moves nothing: a `t` member of an `or` makes it `t`, and an `f` conjunct makes the atom `f`. An opaque part therefore shares a variable with no other part, its complement included, as `decisions/0016` #2 asks. Two atoms on one absent target are completed separately, and so are a leaf on a missing operand and its complement.

**Paired variables.** A `u` constraint part is completed node by node, but only on its open nodes (`opened/2`, `open/1`): those that are `u` and lie on a path of `u` nodes from the part's root. A node that is `t` or `f` keeps its value in every completion, because strong Kleene logic is monotone: replacing a `u` by `t` or `f` never turns a `t` into `f`, or an `f` into `t`. So:

- each open paired leaf reads one variable with a polarity (`leaf_lit(C, L, Pol)`);
- in each completion world, each open node gets a rank, `crank(W, C, N)`. A paired leaf takes its variable's value, 0 or 2, negated for `neg`. An opaque leaf keeps 1. An open connective is re-evaluated from its members by the connective rules of `compare.lp`, which the world applies to its open nodes (`evaluates(W, C)`). A member that is not open keeps its rank in world `k`;
- the constraint part takes its root's rank in the world.

**The key.** Two open paired leaves read one variable when they make the same comparison (`due2-workflows.md` §6.4). The key has six components:

| Component | Relation | Note |
|---|---|---|
| scope | `scope/2` (`constraint.lp`) | `rule` or `action` |
| binding | `src/2`, `prop/2` (`operand.lp`) | where the operand reads, not its IRI: two operands bound to one property read one value |
| positive operator | `op_literal(O, Base, Pol)` | a complement asserts its `Base`, `neg` |
| right operand values | `leaf_attr(C, right(Term))` | a set of terms |
| units | `leaf_attr(C, unit(Iri))` | a set |
| concept | `leaf_attr(C, concept)` | whether the operand has a concept scheme: with one, `eq` is ⊑, and without, identity |

The complements are `neq` of `eq`, `gteq` of `lt`, `gt` of `lteq`, and `isNoneOf` of `isAnyOf` (`complement/2`). `leaf_key/5` holds the first three components. Two leaves with one `leaf_key` differ when one has an attribute the other lacks (`attr_apart/2`), and `same_key/2` holds when neither does. The variable is `cons(D)`, with `D` the least leaf of the class in clingo's term order, so every leaf of the class names the same variable.

Right operands compare as terms, not values, so `5` and `5.0` are two variables. A node reached from both a rule's constraint and an action's refinement has two scopes, and so two keys for one value. It declines as `constraint: node in two scopes`.

**Example.** This is the first row of `test_completion_key`, copied from a run. Under `perm`, permission `ex:r1` has the leaf `c1`, `ex:x eq 5`, and permission `ex:r2` the leaf `c2`, `ex:x neq 5`. `ex:x` reads the state, which has no fact for it, so it is `unresolved`. Both leaves are `u` and paired, so both findings are `u`, and both leaves are open. They share a key: scope `rule`, the state property `ex:x`, base `eq`, right operand `{5}`, no unit. In the run, `c1` is the lesser label, so `leaf_lit(c1, cons(c1), pos)` and `leaf_lit(c2, cons(c1), neg)` hold: one variable, two completions.

| `cons(c1)` | `c1` | `c2` | applies | verdict |
|---|---|---|---|---|
| `t` | 2 | 0 | `ex:r1` | `Permit` |
| `f` | 0 | 2 | `ex:r2` | `Permit` |

The verdict is `Permit` in both, so the reply is a definite `Permit`, although both findings are `u`. Its basis is empty, because neither permission applies in both completions (§ `resolve.lp`). With one variable per leaf, some completion would make both leaves rank 0 and give `NotApplicable`, and the reply would be `Indeterminate`: the precision the key buys. With `ex:x` missing instead, the leaves are opaque, each atom is decided by its own `fin` variable, and the reply is that `Indeterminate`, `NotApplicable` to `Permit`. `test_opaque_is_not_paired` pins the same contrast on `lt` and `gteq`.

**Different values, different variables.** The completion is domain-unaware: it does not know which variables exclude or imply each other (domain-aware completion is `due2-workflows.md` §9 open decision 6). It misses three kinds of correlation:

- values: `ex:x eq 5` and `ex:x eq 6` are separate variables (`decisions/0012` #3), and the completion that makes both `t` is enumerated, though `ex:x` is single-valued and no state realises it;
- hierarchies: with `ex:a1 odrl:partOf ex:a`, a value `ex:a1` would make both `ex:x isPartOf ex:a1` and `ex:x isPartOf ex:a` `t`;
- comparisons on one value: `ex:x lt 3` implies `ex:x lt 5`, and `5` equals `5.0`, yet each is its own variable.

Opaque findings miss correlations too: their `fin(I)` and `ful(Y)` are independent of every other variable by construction. One absent subject, for example, would make a rule's party part and a duty's actor check `t` together, and the completions also hold the corners where they differ. In every case the variables stay independent, so the completions are a superset of the realisable ones, and:

- a definite verdict holds in every completion, so it holds in every realisable one, and it is sound;
- an `Indeterminate` may be reported where every realisable completion agrees, so precision, not soundness, is what is lost;
- a range covers every realisable verdict, and may be wider.

### `resolve.lp`

The four steps of `due2-workflows.md` §6.1–§6.4, in order. Every relation carries the world `W`, and within a world every completed value, the duty findings included, is `t` or `f`:

1. **Candidates** (`due2-workflows.md` §6.1). An instance is violated when it is not fulfilled and its deadline has passed (`violated/2`). A permission that applies is closed when one of its preconditions is owed and violated (`closed/2`), and every other permission that applies is a candidate (`candidate/2`). A candidate's outstanding set is its preconditions that are owed and not fulfilled (`outstanding/3`). Closure comes before conflict (`due2-workflows.md` §6), so a closed permission removes no prohibition, under either value of `config.violations`.
2. **Conflict** (`due2-workflows.md` §6.2), among the candidates and the prohibitions that apply. A `permit` or `forbid` atom takes part once in each policy that states it, as its entry there (`due2-workflows.md` §6.2, *Entries*). Within each policy, by its strategy (`due2-workflows.md` §6.2 #1), conflict removes entries (`entry_eliminated/3`):
   - `prohibit`: an applying `forbid` eliminates the policy's candidates;
   - `perm`: a candidate eliminates the policy's `forbid` atoms;
   - `invalid`: a candidate and an applying `forbid` together eliminate every `permit` and `forbid` atom of the policy that applies, and its root obligations stay in force (`decisions/0029`).

   An atom is eliminated (`eliminated/2`) when every policy that states it removes its entry, and remains a candidate or a prohibition while any entry is kept (`entry_kept/2`). So a permission that a void policy and a `perm` policy both state survives, by its entry in the second. `structure.lp` admits one policy, so no vector has a shared atom, and `test_shared_permission_survives_in_its_other_policy` runs the rule on hand-written facts.

   Across policies (`due2-workflows.md` §6.2 #2), something denies (`deny/1`) when a `forbid` survives, or when `config.violations` is `deny` and an obligation in force is violated (`due2-workflows.md` §6.4). Either eliminates every candidate (prohibit-overrides), so a candidate survives (`survives/2`) when conflict does not remove it and nothing denies. Under `ignore`, the default, whether stated or absent, `config_violations(deny)` does not hold, and obligations never change the verdict.
3. **The frontier** (`due2-workflows.md` §6.3). A surviving candidate is dominated when another's outstanding set is a strict subset of its own (`not_within/3`, `dominated/2`), and the frontier is the surviving candidates that are not dominated (`frontier/2`). The program compares candidates, not sets: two candidates with one set are both in the frontier, and `interpret.py` collapses them into one alternative (§ Output).
4. **Verdict**, by the table of `due2-workflows.md` §6.4, the first that holds: `Deny` if something denies; `Permit` if a frontier candidate has no outstanding duty (`ready/1`); `Pending` if the frontier is not empty (`pending/1`); otherwise `NotApplicable`. The empty set is a strict subset of every other, so under `Permit` the frontier holds only candidates with no outstanding duty.

**Basis of one world** (`basis/3`, `due2-workflows.md` §6.4): role `prohibition` for each surviving `forbid`; `permission` for each frontier candidate; under `Pending`, `duty` for each outstanding duty of a frontier candidate; and under `NotApplicable`, `closed` for each closed permission. A violated obligation that denies has no role here: `interpret.py` gives every obligation the reply lists, in force `t` or `u`, role `obligation`, under any verdict, from the rows of `explain.lp` (§ Output).

**The cautious basis.** Solve 2 reports a basis row only if it holds in every completion: an atom that carries a definite verdict whatever the unknowns are. An `Indeterminate` has no such row, and its basis comes from solve 3 instead. When no single atom carries a definite verdict in every completion, the basis is empty, and `unknown_parts` names what was unknown (`decisions/0016` #4). The brute-force oracle computes the same basis. Two shapes show where it differs from "the atoms with finding `t` that survive" (`test_completed_basis`):

- **An empty basis.** Prohibitions `ex:x eq 5` and `ex:x neq 5`, with `ex:x` unresolved, read one variable with opposite polarities. Each completion applies one of them, so the verdict is `Deny` in both, and no prohibition survives in both. The basis is empty.
- **A `u` atom in the basis.** A permission under `ex:x eq 5 or ex:x neq 5` has finding `u`, but its tree is `t` in every completion, so it carries the `Permit` in every completion and is in the basis.

A paired guard empties a basis too. In an example among `DUTY_EXAMPLES` (`test_brute_force.py`), `ex:r0` requires `ex:d0`, lapsed and unwitnessed, whose guard `ex:o2 eq 1` repeats the constraint of `ex:r1`, and `ex:o2` is unresolved. Where the shared variable is `t`, `ex:d0` is owed and violated, so `ex:r0` is closed and `ex:r1` permits; where it is `f`, `ex:r0` permits. The verdict is `Permit` in both, and the basis is empty. Both empty bases, this one and the first shape's, read a paired leaf, and the next argument shows that the empty basis of every definite `Deny` or `Permit` must.

**Without a paired leaf, the basis is not empty.** Suppose no `u` finding reads a `cons` variable, so no open leaf is paired; duty findings may be `u`, and the connectives are any. Then every variable is a `fin(I)` or a `ful(Y)`, read by one finding only, and that finding is its variable's value in every completion: an opaque part keeps rank 1, and with no paired leaf nothing an open node reads differs from world `k`, so every open node keeps rank 1, and the finding's conjunction stays `u`. Call a variable's value *lenient* when it makes its finding the one that permits more: `applies` `t` for a permission and `f` for a prohibition, `owed` and `in_force` `f`, `fulfilled` `t`; and *strict* when it is the other value. Let `L` be the completion with every variable lenient, and `S` the one with every variable strict. Every completion `C` lies between them, finding by finding: a permission applies in `C` if it does in `S`, and a prohibition applies in `C` only if it does in `S`; a precondition is owed in `C` only if it is in `S`, and fulfilled in `C` if it is in `S`. So a permission that applies in `S` is closed in `C`, or waits on a duty there, only if it is so in `S`. And a permission that is a candidate in `C` is one in `L`: it applies in `L`, since a permission that applies anywhere applies in `L`, and it is not closed in `L`, since a precondition owed and violated in `L` is owed and violated in every completion. These are facts about findings, not about verdicts, which are not monotone in them: under `invalid`, a permission that applies can void the policy. The two cases use only these facts.

- **A definite `Permit`.** `S` permits, so some candidate `X` survives in `S` and is ready. `X`'s finding is `t`, since strict makes a `u` permission `f`. In `C`, `X` applies, it is not closed and waits on no duty, since it does neither in `S`, and no prohibition of its policy applies to remove it under `prohibit` or `invalid`, since none applies in `S`. The verdict is definite, so `C` permits too, and nothing denies in `C`. So `X` survives in `C` with an empty outstanding set, which no other set is a strict subset of, and `X` is a ready candidate of `C`'s frontier. `X` is in role `permission` in every completion, so the basis holds it.
- **A definite `Deny`.** `L` denies. If a prohibition `X` survives in `L`, its finding is `t`, since lenient makes a `u` prohibition `f`, so it applies in every `C`; and a strategy that removes it in `C` needs a candidate of its policy in `C`, which would be one in `L`, where none removed `X`. If instead a violated obligation in force denies in `L`, its `in_force` is `t` and its `fulfilled` `f` there; lenient would make a `u` `in_force` `f` and a `u` `fulfilled` `t`, so these are its findings, the same in every `C`, and it denies in every `C`; `interpret.py` gives it role `obligation`.

So an empty basis under a definite `Deny` or `Permit` needs a `u` finding that reads a paired leaf, whose operand is `unresolved` and is listed as an unknown part: claim W of `correctness-strategy.md` §4.8. `tools/check_corpus.py` asks such a scenario to list it, and `check_waiver` checks the claim on every reply the differentials see (`TESTS.md`, claim W).

**`Pending` is the exception.** Dominance is not monotone: a candidate whose finding is `u` can dominate a `t` one in the completions where it applies, and not in the others. So the basis of a definite `Pending` can lack a permission, and can name a duty that the listed frontier does not (§ `explain.lp`). Both tests are in `tests/test_duty.py`:

- In `test_pending_basis_under_an_uncertain_route`, `ex:perm` (finding `t`) needs `ex:d` and `ex:d2`, and `ex:perm2` (finding `u`, on a missing request parameter) needs `ex:d`. Where `ex:perm2` applies, `{ex:d}` dominates; elsewhere `ex:perm` is the frontier. No permission is in both frontiers, so the basis is `ex:d` alone, outstanding in both. The listed frontier is `[[ex:d, ex:d2]]`, because `ex:perm2` is uncertain in world `k`.
- In `test_pending_basis_beyond_the_listed_frontier`, `ex:perm` (finding `t`) needs `ex:d`, and `ex:permA` on `ex:x eq 5` and `ex:permB` on `ex:x neq 5` both need `ex:d3`, with `ex:x` unresolved. One of the two applies in each completion, so each frontier offers `{ex:d}` and `{ex:d3}`, and the basis is `ex:perm`, `ex:d`, and `ex:d3`. Neither of the two is listed, so the listed frontier is `[[ex:d]]`.

The basis stays cautious: each `duty` row is outstanding in the frontier of every completion, and each `permission` row is in every frontier. Without unknowns, `tools/check_corpus.py` asks a `Pending` basis for a permission and for exactly the frontier's duties; when a scenario lists an unknown part, it checks only their kinds (`decisions/0019`).

### `integrity.lp`

The integrity constraints over every earlier file, in solves 2 and 3:

- every item has exactly one truth value, and only a ranked one;
- in every world that reads it (`read_in/2`), every left operand is exactly one of `read_ok` and `read_u`, and every compared pair has exactly one equality rank;
- every `u` read, and every `u` leaf, has exactly one status;
- every open leaf that is not opaque reads exactly one variable;
- in every completion world, every variable and every completed item has exactly one value, `f` or `t`;
- in every world, `k` included, every node the world evaluates has exactly one rank;
- every duty instance has exactly one duty status;
- every world has exactly one verdict.

They are why a rule deleted from the program fails loudly. Without its rule, some item has no value, some read no outcome or status, or some world no verdict, so the solve has no model and the reply is an `error`, never a verdict standing on the missing part (`TESTS.md`).

### `explain.lp`

`due2-workflows.md` §3.5, §6.2, `decisions/0011` #4. Elimination is read from the findings, not from a world, so `elim(X, P, Y, Strat)` carries no world and is the same in every completion. A row removes one entry: the atom `X` in policy `P` (`due2-workflows.md` §6.2, *Entries*). A precondition closes first (`due2-workflows.md` §6.1), then conflict removes. A remover in conflict takes part in it in every completion (`sure_contender/1`): a `forbid` with finding `t`, or a permission with finding `t` that no completion closes (`sure_candidate/1`, `maybe_closed/1`). A removed atom takes part in some completion (`may_contend/1`): its finding is `t` or `u`, and a permission is one no precondition surely closes (`may_candidate/1`, `surely_closed/1`). `u` atoms eliminate nothing (`due2-workflows.md` §6.2), but they can be removed.

- `violated_precondition`: each permission with finding `t` or `u` is removed by each of its preconditions that is owed `t` and violated (`closed_by/2`), which closes it in every completion where it applies. Closure is a fact about the atom, so every entry of it has a row;
- `prohibit`: each `t` `forbid` of the policy removes each permission that may be a candidate;
- `perm`: each sure candidate removes each of the policy's `forbid` atoms that may apply;
- `invalid`: a policy with a sure candidate and a `t` `forbid` is void (`void/1`). Each of its contenders is removed by each other sure contender of the policy;
- the combination (`prohibit-overrides`, the only one read): each entry of a `t` `forbid` that its policy `Q` did not remove (`removed_in/2`) removes each candidate entry in every policy other than `Q`. `structure.lp` admits one policy, so no vector reaches this rule. It is there because `due2-workflows.md` §3.5 records every elimination with its rule, cross-policy ones included, and `test_combination_rows_on_facts` runs it on hand-written facts.

**One row per remover.** An atom removed by two `forbid` atoms has two rows (`due2-workflows.md` §3.5, #57). Each row is a complete reason. In a conflict row, whenever `X` applies, `Y` applies too, because `Y` is `t`, and `Y` removes it. In a `violated_precondition` row, `Y` is the duty atom, owed `t` and violated, so it closes `X` wherever `X` applies. A reader can check each row against the policy alone. A single row naming the first remover would hide the others, and which one is "first" would depend on the order of the facts. A `u` remover gives no row, because it removes `X` only in some completions, and that is not a reason that holds whatever the unknowns are.

**The listed frontier** (`due2-workflows.md` §6.1, §6.3). The reply's `frontier` is read in world `k`, so it does not depend on the completion. A precondition whose instance is not violated has an open value (`open_k/2`): the Kleene conjunction of `owed` and the negation of `fulfilled`. Each permission that may be a candidate has one state (`candidate_state/2`), by the table of `due2-workflows.md` §6.1:

- `uncertain` when its finding is `u`, a precondition's open value is `u`, or a violated precondition's `owed` is `u` (`uncertain/1`);
- otherwise `pending` when some precondition's open value is `t`, so that it is in the outstanding set (`listed_out/2`), and `ready` when none is.

A ready or pending candidate that conflict does not remove is listed (`listed/1`). Conflict removes a candidate when it has a conflict row for every entry (`conflict_removes/2`, `conflict_keeps/1`, `conflicted/1`), so a permission that one policy removes and another keeps is listed. As with the combination, no vector reaches this, and `test_shared_permission_rows_name_the_entry` runs it on hand-written facts. The listed frontier is the listed candidates that no other listed candidate dominates (`listed_apart/2`, `listed_dominated/1`, `listed_front/1`), with their outstanding duties (`front_duty/2`). An uncertain candidate is not listed: it reaches the reply only through the verdict, which the completions decide. So under a definite `Pending` the listed frontier can differ from the frontier of a completion (§ `resolve.lp`, `decisions/0019`). This is the listed frontier that version 0.33 of `due2-workflows.md` gave. Version 0.34 lists the routes that suffice instead (`decisions/0026`), and clingo-i follows it with #103.

**Obligations** (`due2-workflows.md` §6.1). `obligation_row(Y, S)` names each root obligation in force `t` with its duty status, and each whose `in_force` is `u` as `unknown`. An obligation that is not in force is not reported.

**Unknown parts** (`due2-workflows.md` §3.5, `decisions/0016` #3 and its amendment). `unknown_part(X, Input, S)` holds for every `u` part of every finding that is `t` or `u` (`reported/1`): `target` and `party(F)` when the request field is absent, status `missing`, and `prop(Prop)` for each live `u` leaf of the finding's trees (`live/4`), with its `leaf_status/2`. A duty's findings report under the duty atom: `owed` and `in_force` their guards' live leaves; `in_force` also the `u` target and party parts of its policy's rules, whose match puts it in force; and `fulfilled`, for each witness pair that is not `f`, its witness conditions' live leaves, with their status in that evidence's world (`witness_status/3`), and a `u` actor check as the request's assignee, `missing`. The rows read the finding, not a world, so they do not depend on the completion.

An `f` atom is not reported. No `u` part can change it, because an `f` part makes the conjunction `f` in every completion, and `due2-workflows.md` §5.5 lets an index skip an atom that is certainly `f`, so its rows would depend on the index.

W1's atoms are the disjuncts of the DNF of each authored tree (`due2-workflows.md` §3.1, §4 stage 2), so a `u` leaf that lies only in `f` disjuncts is read only by `f` atoms, and is not reported either: in `or(and(lf, y), z)`, with `lf` a leaf that is `f`, `y` is not. A leaf that lies in a disjunct that is not `f` is live, and is reported though another member decides its node, in a `t` atom as in a `u` one: in `or(lt, y)`, with `lt` a leaf that is `t`, `y` is. The reply then names everything that was unknown in the disjuncts that can hold, whether or not it mattered, and a renderer may show less.

`live/4` finds the live leaves on the authored tree, without building the DNF, which can be exponentially larger. It walks down from each root of a reported finding, and for `fulfilled` from each witness condition in world `wit(E)`, for each witness pair that is not `f`. It carries the node polarity (not the literal polarity of § `completion.lp`), which `flip/2` reverses at `dprod:not`, and reads a node's rank under its polarity with `polar/4`, so that rank 0 under `neg` means the node is `t`:

- Under a node that is disjunctive at its polarity (`disj/2`: `or` at `pos`, `and` at `neg`), every member is live.
- Under one that is conjunctive (`conj/2`: `and` at `pos`, `or` at `neg`), a member is live unless a sibling is `f` at that polarity. Every disjunct the member lies in also holds one of each sibling's disjuncts. Under strong Kleene logic a node's value is the greatest of its disjuncts' values, so a sibling that is not `f` has a disjunct that is not `f`, and an `f` sibling's disjuncts are all `f`.
- A positive `xone` is the disjunction of its terms, each a member conjoined with the other members negated (`xone_pol/4`, `due2-profiles.md` §5). A member is live, at its polarity in a term, when no other conjunct of that term is `f`.
- A negated `xone` is the conjunction of the terms' negations, because a negation over an `xone` expands the `xone` first (`due2-profiles.md` §5). Each negated term is the disjunction of its members, flipped, and is `f` exactly when the term is `t`: when the `xone` is `t` and the term's member is its one `t` member (`xone_by/3`). So each member of a term is live, flipped, unless some other term is `t`.

Under a status the same for every rule, as an absent target is, every atom carries the row, so `interpret.py` projects them to the rule or duty node, and the reply has one row per rule, input, and status.

The same file holds the structure's constraints: every atom has exactly one `atom_effect` and one `atom_rule`, so a row names exactly one of each, as `due2-workflows.md` §3.1 requires, and at least one `atom_policy`. In the spec an atom's policies are its `root` tuples (`due2-workflows.md` §3.1, `decisions/0036`); the constraint checks only that there is one.

### `pivot.lp`

`decisions/0011` #1 to #3. Solve 3 only, after solve 2 has found an `Indeterminate`:

- `world(flip)`, and a choice of exactly one `pivot(L)` among the variables;
- `flip` copies `c`'s value of every variable, except the pivot, whose value it negates;
- an integrity constraint keeps only the models where `c` and `flip` have different verdicts;
- `unknown(X)` holds for an atom or duty atom `X` with a `u` finding that reads the pivot (`reads/2`, `finding_atom/2`).

Brave enumeration gives the union over the models. The `unknown` atoms are those with a pivotal variable (`decisions/0011` #1). The range is the least and the greatest `verdict(c, Verdict)` that occurs, in the chain `Deny < NotApplicable < Pending < Permit` (`decisions/0011` #3).

**Why the brave verdicts are exactly the completions' verdicts.** The flip constraint drops models, so it is not obvious that every verdict some completion takes survives in some model. It does:

1. The completions are the corners of an `n`-dimensional cube, and two corners are neighbours when they differ in one variable. The cube is connected: any corner reaches any other by flipping, one at a time, the variables in which they differ.
2. An `Indeterminate` means at least two verdicts occur. Let corner `c₁` have verdict `V`, and corner `c₂` some other verdict.
3. On the path from `c₁` to `c₂` the verdict starts at `V` and ends elsewhere, so some step goes from a corner `c` with verdict `V` to a neighbour without it.
4. That step is a model of solve 3: completion `c`, pivot the flipped variable. So `verdict(c, V)` is true in some model.

Conversely, `c` in every model is a completion. So the brave `verdict(c, _)` atoms are exactly the verdicts the completions take, and the range is exact. In § Worked example, `NotApplicable` occurs only at (`f`, `f`), and it survives through both of that corner's flips.

## Output

`interpret` replies with:

- `verdict` and `exact: true`. The reply enumerates every completion, which is the definition itself, so it is exact. A vector it cannot enumerate within the variable cap is declined instead;
- `frontier`: under `Pending`, the listed frontier of § `explain.lp`, and `[]` under any other verdict. Each alternative is a sorted list of duty IRIs, and the alternatives are sorted by size, then by their IRIs. Candidates whose outstanding duties have one set of IRIs are one alternative (`due2-workflows.md` §6.3), so `interpret.py` collapses them. A duty atom is named by its node (`due2-workflows.md` §3.7), so two sets that differ only in which atom of one node they hold collapse too, where `due2-workflows.md` §6.3, comparing by duty id, keeps them apart: the reply could not tell the two apart;
- `obligations`: each `obligation_row(Y, S)` as `{"duty", "status"}`;
- `verdict_basis`: the rows of solve 2 for a definite verdict, or role `unknown` for each `unknown(X)` of solve 3; and, under any verdict, role `obligation` for each obligation the reply lists;
- `eliminated`: each `elim(X, P, Y, Strat)` as `{"ref", "by", "rule"}`, with `Strat` the conflict strategy, the combination, or `violated_precondition`. The reply drops the policy `P`: `expected.eliminated` is the set of `(source, source of by_atom, rule)` triples (`due2-workflows.md` §3.7, *What the corpus asserts*), so the rows of two entries with one remover and rule are one;
- `unknown_parts`: each `unknown_part(X, Input, S)` as `{"ref", "input", "status"}`, under any verdict. `input` is `odrl:target`, the party function's IRI, or the property's IRI. The rows are sorted by their full IRIs;
- `verdict_range` `{"low", "high"}`, for an `Indeterminate` only.

Atoms are projected to their source rule, the `R` of `a(R, A, T, Party)`, and duty atoms to their duty node (`due2-workflows.md` §3.7). So the atoms of one rule share one `ref`. An elimination whose `ref` and `by` come from the same rule (under `invalid`, two atoms of one rule) is dropped, because at the authored level the rule would remove itself, and `invalid` says "other than itself".

The spike has no beyond-`max_mixed` fallback (`decisions/0009` #5), so `backend.toml` sets `exact_only` (`spikes/README.md`). The harness reports a scenario that states `exact: false` as `unsupported: max_mixed fallback` without asking the spike.

## Negation as failure

`not` never turns a missing truth value into `f`. Each use reads something that is complete by construction:

- the declared hierarchy edges (`not action_matches`, `not target_matches`, `not party_matches`, `not le_k`, `not inst`), which are closed-world (`due2-profiles.md` §6);
- input syntax and what `lift.lp`, `structure.lp`, `constraint.lp`, and `duty.lp` derive from it: whether a family is stated, a predicate consumed, a function named, a duty inheriting or with a bearer, a node a list, a leaf or a connective, a leaf a witness leaf, a tree with a witness or a guard leaf (`has_witness`, `has_guard`), a node in a rule's tree (`rule_node`) or in a witness condition, or a duty with a deadline or a relation value. `witness_only/1`, which `evaluates(k, C)` negates, reads only these, never a rank, so the ground program has no cycle through it;
- the value table and the term shapes (`not placed`, `not kind`, `not same_type`), which decide only that a pair is a misfit, and a misfit is `u`;
- the reads: `not read_resolved`, `not card_ok`, and `not conforms` make a read `u`, never `f`;
- in `completion.lp`, over relations fixed before the choice. `not complement`, `not leaf_attr`, and `not attr_apart` decide only which variable a leaf reads and with which polarity. `not open` picks the members of an open node that keep their rank, and these are `t` or `f`, because a `u` member of an open node is open itself. `open/1` reads the ranks of world `k`, and no rule for world `k` reads another world, so the ground program has no cycle through `not open`, although `crank/3` holds the ranks of every world;
- inside one world in `resolve.lp`, where every completed value, the duty findings included, is already `t` or `f`, and over `passed/1` and `config_violations/1`, which are facts about the vector;
- in `explain.lp`, over relations derived from the world-`k` findings and duty statuses: the `elim` rows (a `forbid` its own policy did not remove), the closure (`not surely_closed`, `not maybe_closed`), the listed frontier (`not uncertain`, `not conflicted`, `not listed_out`, `not listed_apart`, `not listed_dominated`), and the liveness walk (`not polar`, `not xone_by`), which reads node ranks and no relation it derives. A `u` finding gives no `elim` row, and the rows are only ever read as "no remover", never as a truth value. `not holds(owed(Y), f)` and `not holds(fulfilled(Y), t)` read a finding that has exactly one value (`kleene.lp`), so they mean "`t` or `u`" and "`f` or `u`";
- in `duty.lp`'s witness test, over input records, which are complete: an evidence record lists every field it has, and the config every signer. So `not evidence_object`, and an actor that is not the performer (`not performer`) and that the request does not leave open (`not open_actor`), make a check `f`. For the object this reads the equality `e.object = d.relation_value` of `due2-workflows.md` §5.3, with `object` optional: evidence that records no object does not record the duty's relation value. `not signed`, `not admitted`, `not keyed`, `not discharged`, and `not activated` read the config, the request, and the SOTW the same way, and `not ev_reaches` and `not has_member_bearer` read closed-world closures. Where an input that the test needs is absent, the check is `u`, not `f`: `not effective_pos` makes `effective` `u`, and `not subject` makes `actor` `u` (§ `duty.lp`). The activation is the one exception: it takes the spec's default, `effective_at`. `not passed` cannot hide an undecided deadline, because a deadline that has no position declines the vector.

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
| `binding: cardinality`, `binding: range` | `operand.lp` | a cardinality or range the spike cannot read, or two of them |
| `constraint: cycle`, `constraint: dprod:not with several members`, `constraint: leaf with a connective`, `constraint: list on a scalar operator`, `constraint: two connectives` | `constraint.lp` | no reading, or none the spec settles |
| `constraint: node in two scopes` | `constraint.lp` | one node would need two completion variables (§ `completion.lp`) |
| `duty: also a permission or prohibition` | `structure.lp` | a rule read as a duty, which the spec gives no reading |
| `duty: evidence without effective_at` | `duty.lp` | evidence, and no `effective_at`: the `effective` check is `u`, and reads no input an `unknown_part` row can name (`due2-workflows.md` §3.5, § `duty.lp`) |
| `duty: deadline not comparable` | `duty.lp` | a deadline with no position in the `instant` space, or a deadline and no `effective_at`: the status table of `due2-workflows.md` §5.3 has no row for a deadline it cannot place (§ `duty.lp`) |
| `duty: bearer from two functions` | `structure.lp` | two functions that play the bearer role disagree on a duty, both stated by it or both interiorised from the policy level: two bearers for one performance, which the spec does not settle |
| `duty: parent with two bearers` | `structure.lp` | a parent atom that passes two bearers to an inheriting duty |
| `duty: instance scope` | `structure.lp` | a `due2:instanceScope` other than `due2:member` or `due2:grant`, or two; no diagnostic covers it |
| `odrl:partOf: cross-kind edge`, `odrl:partOf: untyped collection` | `lift.lp` | a hierarchy the spike does not trust |
| `profile-conflict-defaults` | `structure.lp` | two profile defaults, and no rule for which wins |
| `recurrence` | `structure.lp` | a duty's `dprod:recurrence` needs occurrences, which the spike does not compute (`decisions/0009` #7) |

**In the input** (`lift.lp`). The driver flattens every field, and `unsupported_input(Field)` names each field the program does not read:

- a `sotw.closure` edge of a relation other than `includedIn`, `partOf`, `rdf:type`, `rdfs:subClassOf`, `skos:broader`, and `skos:inScheme`;
- `config.combination` other than `"prohibit-overrides"`;
- each `unread(Field)` (§ Input facts).

§ Input facts names the file that reads each other field. An empty field gives no facts, so it is not declined. When several fields hold, the smallest name wins: `config.*` before `request.*` before `sotw.*`.

**In the values.** `unsupported_value(Reason)`, read after the input declines: an unplaceable compared literal (§ Values), or `value: derived string datatypes` (§ `compare.lp`).

**Above the cap.** More than 64 completion variables is `variable-cap` (§ Data flow).

## Errors

These are an `error` reply, not a decline:

- an unknown `odrl:profile` (`UnrecognisedProfile`);
- a policy that is not admissible (`reject`). The codes are `NoPolicy`, `MultiplePolicies`, `InvalidConflict`, `MissingAction`, `MissingTarget`, `TargetAndOutput`, `RuleReferenceCycle`, `InvalidTiming`, and `TimingOutsideDuty` (`structure.lp`); `UnsupportedConstruct` and `ReplacedPolicy` (`lift.lp`); `MalformedConstraint`, `UnsupportedOperator`, `UnsupportedConnective`, `FloatingPointOperand`, and `MixedDuration` (`constraint.lp`); and `UnboundLeftOperand`, `InvalidBinding`, `ConflictingProfileDeclaration`, `RetypedOperand`, `OperandRangeMismatch`, `WitnessOutsideDuty`, and `OperatorTypeMismatch` (`operand.lp`); and `MixedDutyConstraint` (`duty.lp`). Each is defined in `due2-diagnostics.md`;
- a malformed vector (§ Input facts);
- an unsatisfiable program.

`interpret` receives only admissible policies from well-formed vectors, so each of these is a defect, in the vector or in the spike.
