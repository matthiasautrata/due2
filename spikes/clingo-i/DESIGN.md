# clingo-i — design

clingo-i is the semantics program of `decisions/0009`. It is a generic clingo program over flattened ODRL, and it implements the `interpret` task of `spikes/README.md` § `interpret`. Python parses the vector and flattens it to facts, and every semantic step is a rule in `lp/`. This note is for a reader who wants to know how the program reaches a reply, what each file expects and produces, and what the spike declines and why. It is the Docs step of `ways-of-working.md` §14.1. Per-relation reference lives in the generated documentation (`docs/`, below), and progress lives in issue #9 and `journal.jsonl`, not here.

## Vocabulary

The spec defines most terms: atom, part, finding, candidate, completion, and verdict (`due2-workflows.md` §3.1, §5.2, §6.1, §6.4); duty, precondition, root obligation, bearer, guard, witness condition, evidence, instance, witness, and deadline (`due2-workflows.md` §3.1, §3.3, §5.2, §5.3); and left operand, binding, source, and operator (`due2-profiles.md` §2–§5). These are the ones the program adds, or uses in a narrower sense:

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
- **Completion variable.** What a `u` atom reads (`due2-workflows.md` §6.4): `cons(D)` for a class of paired leaves with one key, `D` a leaf that names the class, and `fin(X)` for an atom `X` with an opaque part, which completes the finding the opaque part leaves `u`. The spec calls the variable with a polarity a *literal*. "Literal" alone, in this note, means an RDF literal, `lit(Lex, Datatype)`.
- **Polarity.** How a paired leaf reads its variable: `pos`, or `neg` for a complement operator such as `neq`, which reads the variable of `eq` negated (§ `completion.lp`). `fin(X)` is read `pos`.
- **Open node.** A constraint node that is `u` and lies on a path of `u` nodes from a `u` root of an atom whose finding is `u`. Completion re-evaluates exactly the open nodes (§ `completion.lp`).
- **Unknown part.** A row of `unknown_part(X, Input, S)`: atom `X` has a `u` part that reads `Input` with status `S` (§ `explain.lp`).
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
| `X`, `Y` | an atom, or a duty atom. In an elimination row, `X` is removed and `Y` removes it; in `pre(X, Y)`, `Y` is a duty atom of the permission atom `X` |
| `P`, `Q` | a policy |
| `R` | a rule |
| `A`, `B` | an action, or an action term in an atom id; `B` is the broader one in an `includedIn` edge |
| `T` | a target, or a duty's relation value: its target or its `odrl:output` |
| `F` | a function predicate (a party role, such as `odrl:assignee`) |
| `Party` | a party, or `none` for a duty atom's missing bearer |
| `Duty` | a duty node: a precondition duty, a root obligation, or both |
| `E` | a piece of evidence: an evidence record's `id` |
| `Eff` | an effect, `permit` or `forbid` |
| `Strat` | a conflict strategy (`prohibit`, `perm`, `invalid`), or the cross-policy combination in an elimination row |
| `I` | an item |
| `V` | a truth value |
| `N`, `M`, `M2` | a rank of a truth value, or a position in a value space |
| `L` | a completion variable |
| `S` | a status, such as `missing` or `unresolved`, or a duty status, such as `outstanding` |
| `Pol` | a polarity, `pos` or `neg` |
| `Base` | the positive operator a leaf asserts: the operator itself, or the one its complement negates |
| `Scope` | a scope, `rule` or `action` |
| `InstScope` | an instance scope, `member` or `grant` |
| `Attr` | an attribute of a completion key: `right(Term)` or `unit(Iri)` |
| `W` | a world |
| `C`, `D`, `D2` | a constraint node; `D` is a member of `C` |
| `O` | a core operator, such as `eq` or `isPartOf` |
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
tests/                 the spike's own tests (§ Tests)
```

`lift.lp` is the only file that names an IRI. Every file after it reads relations named after the spec's. The files load in the order above (`PROGRAM_FILES` in `interpret.py`), and each file's header names the files whose relations it reads.

**The generated reference.** `uv run --group docs mkdocs build --strict` builds `site/` (not committed): one page per `lp/` relation, with its doc block, a predicate table, and a dependency graph (clindocs), and one page for the Python modules (mkdocstrings). It is the place to look up one relation. `tests/test_docs.py` keeps it complete (§ Tests).

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
   - `elim(X, Y, Strat)` gives `eliminated`. It reads no world, so it is the same in every model.
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
| perm | `t` (play ⊑ use) | `u` (no target) | `t` (alice) | `u` | `fin(perm)` |
| forbid | `t` | `u` | — (no assignee) | `u` | `fin(forbid)` |

The absent target is `missing`, so each atom's target part is opaque (`opaque_atom/1`). It stays `u` in every completion, so each atom's parts have conjunction `u` (`pre_in(c, X, 1)`), and each atom's own variable decides it. The run's atom ids are the full `a(R, A, T, Party)` terms, shortened here to the rule. Two variables give four completions. In each, `resolve.lp` applies the atoms whose variable is `t`, and `prohibit` removes the permission when the prohibition applies:

| `fin(perm)` | `fin(forbid)` | applies | verdict |
|---|---|---|---|
| `t` | `t` | perm, forbid | `Deny` (perm eliminated) |
| `t` | `f` | perm | `Permit` |
| `f` | `t` | forbid | `Deny` |
| `f` | `f` | — | `NotApplicable` |

**Solve 2.** No verdict holds in all four completions, so the verdict is `Indeterminate`, and no basis row holds in all four either. Neither atom has finding `t`, so neither removes anything: `eliminated` is empty.

**Solve 3** keeps a completion and a pivot only when the flip changes the verdict. Six such pairs exist:

- pivot `fin(forbid)`, from each of the four completions. Each pair changes the verdict, for example (`t`, `t`) `Deny` to (`t`, `f`) `Permit`. The forbid reads it, so `unknown(forbid)` holds.
- pivot `fin(perm)`, from (`t`, `f`) and (`f`, `f`), which swap `Permit` and `NotApplicable`. From (`t`, `t`) and (`f`, `t`) the flip leaves `Deny`, so those pairs are dropped. `unknown(perm)` holds.

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
| `request_party/2`: `request_party(F, Party)` | each entry of `parties`; `F` is the function predicate IRI | `lift.lp`, `operand.lp` (`agent`), `applies.lp`, `duty.lp` (the request subject) |
| `request_param/2`: `request_param(Prop, Value)` | each value of `params`, keyed by property IRI | `lift.lp`, `operand.lp` |
| `request_param_set/1`: `request_param_set(Prop)` | a `params` entry given as a list, so an empty set is not an absent parameter | `operand.lp` |

**SOTW** (`due2-workflows.md` §3.3).

| Fact | From | Read by |
|---|---|---|
| `sotw_effective_at/1` | `effective_at` | `lift.lp`, `operand.lp` (`clock`), `duty.lp` |
| `fact/2`: `fact(Prop, Status)` | each entry of `facts`. `Status` is one of `resolved`, `missing`, `invalid`, `conflict`, `unresolved` | `operand.lp` |
| `fact_value/2`: `fact_value(Prop, Value)` | each value of a `facts` entry | `lift.lp`, `operand.lp` |
| `evidence/4`: `evidence(E, OccurredAt, Actor, Action)` | each `evidence` record, `E` its `id` | `lift.lp`, `operand.lp` (`actionTime` in `wit(E)`), `duty.lp` |
| `evidence_object/2`, `evidence_issuer/2` | its optional `object` and `issuer` | `duty.lp` |
| `evidence_discharges/3`: `evidence_discharges(E, Duty, Ref)` | its optional `discharges` | `duty.lp` |
| `evidence_param/3`: `evidence_param(E, Prop, Value)` | each of its `params` | `lift.lp`, `operand.lp` (`witness`) |
| `activation/2`: `activation(Key, Lit)` | each entry of `activation`: an instance key or rule IRI, and its instant. `duty.lp` reads a key that is a duty's IRI, the key of a non-recurring instance (`conformance/README.md`, SOTW) | `lift.lp`, `duty.lp` |
| `sotw_closure/3`: `sotw_closure(Pred, Lo, Hi)` | each `closure` triple, `Pred` expanded | `lift.lp`: an edge of a hierarchy the spike reads (`closure_key/1`) joins `closure/3`; any other relation declines |

**Config** (`due2-workflows.md` §3.4).

| Fact | From | Read by |
|---|---|---|
| `config_combination/1`, `config_violations/1` | `combination` (a string) and `violations` (`ignore` or `deny`) | `lift.lp` |
| `signer/2`: `signer(Duty, Issuer)` | each `signers` entry | `duty.lp` |
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

These are the value spaces of `due2-profiles.md` §4. The first five are ordered within the space, and none is ordered across spaces. Booleans are placed, so they compare by value, but `lt` and its kin give them no order. Strings, tokens, IRIs, and other datatypes are compared only for equality, by their terms, so they get no entry.

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

### `lift.lp`

Lifts the triples to relations that name no IRI. It provides:

- **The vocabulary.** `voc/2` maps each short name to its IRI; the registries list the conflict strategies, policy classes, the 14 function predicates of `odrl-compound-to-atomic-normalization.md` §3, the match keys (`due2-workflows.md` §5.2; v1 has one, `odrl:assignee`), the 12 core operators of `due2-profiles.md` §4 (`operator/2`, six of them `set_based/1`), the connectives (`connective/1`), the binding attributes, sources, context built-ins, and cardinalities of `due2-profiles.md` §3, the XSD datatypes a range can name (`xsd_datatype/1`, `numeric_datatype/1`, `floating_datatype/1`, `derived_from/2`), and the two RDF Schema classes that admit values of several kinds (`any_literal/1`, `any_resource/1`).
- **The lifted policy.** `type/2`, `subclass/2` (declared, direct edges from the selected modules), `has_rule/3`, `stated/3` (the value a policy or rule node states for a family), `stated_conflict/2`, and `profile_conflict/1`.
- **Terms and lists.** `term/1` collects every term of the graphs and of the inputs the constraints read, and `kind/2` gives each its shape: `iri`, `lit`, or `blank`. `list_cell/2`, `list_item/2`, and `is_list/1` read RDF lists of the policy graph; `rdf:nil` is the empty list.
- **Bindings.** `decl(Layer, Op, Key, Value)` is one attribute of a binding stated in one layer: `policy` for the policy graph, `module(Iri)` for the files of a selected profile, or `core`. `layer_rank/2` orders the layers of `due2-profiles.md` §2 from the top: the policy 0, every profile module 1, the core 2. The profile modules share a rank because they have no order.
- **Kinds.** `dt_kind(Dt, K)` gives a datatype's kind (`due2-profiles.md` §3 *Kinds*): `numeric` for every XSD numeric type, the primitive for a derived XSD type, and the datatype itself otherwise. `term_kind(Term, K)` gives a term's kind, `iri` for an IRI. `admits_kind(Rg, K)` gives the kind a stated range admits: `literal` for `rdfs:Literal`, none for `rdfs:Resource`, and `iri` for a class.
- **The hierarchies.** `closure(Key, Lo, Hi)` holds each declared `includedIn`, `partOf`, `rdf:type`, `rdfs:subClassOf`, `skos:broader`, or `skos:inScheme` edge from the policy, a selected module, or the SOTW closure. A `skos:narrower` triple is the inverse `broader` edge, and `skos:topConceptOf` and the inverse `skos:hasTopConcept` are `inScheme` edges (`decisions/0015` #5, #8); `declared_in_scheme/2` holds the memberships of the policy and the modules alone. `concept_scheme(Op, S)` holds each `due2:conceptScheme` a layer states, a union rather than a binding attribute (`decisions/0015` #6). The edges are closed-world: an undeclared edge does not hold (`due2-profiles.md` §6). `coll_kind/2` types a collection (`odrl:AssetCollection` is `asset`, `odrl:PartyCollection` is `party`), and `node_kind/2` also types an `odrl:Asset` or `odrl:Party`. `le_k(Lo, Hi, K)` is the typed `partOf` of `due2-profiles.md` §6: the transitive closure through collections of kind `K` only. It is not reflexive; its readers add identity.
- **The declines and the rejections of the graph** (§ Declines). A `partOf` edge into an untyped node, or one typed both ways, declines as `odrl:partOf: untyped collection`, and an edge from a node of one kind into a collection of the other as `odrl:partOf: cross-kind edge`: a cross-kind path is invalid (`due2-profiles.md` §6), and the spike has no reading it trusts for either. `odrl:source` off a collection, or `odrl:refinement` on a collection, is `reject("UnsupportedConstruct", Node)` (`due2-diagnostics.md`). On a collection, `odrl:source` is inert: the spike reads membership only from the `partOf` edges. `rdf:value` is read only on an action term, and declines anywhere else.

### `structure.lp`

Shaped like `due2-workflows.md` §3.1, under `odrl-compound-to-atomic-normalization.md` §3, §6.2, §6.3:

| Relation | `due2-workflows.md` §3.1 counterpart |
|---|---|
| `policy(P)`, `conflict(P, Strat)` | `policy(policy_id \| conflict, …)` |
| `atom(X)`, `atom_effect(X, Eff)`, `atom_policy(X, P)`, `atom_rule(X, R)`, `atom_action(X, A)`, `atom_target(X, T)` | `atom(atom_id \| effect, action, relation, relation_value, policy_id, source_rule)` |
| `atom_party(X, F, Party)` | `atom_party`, match keys only |
| `duty_atom(Y)`, `atom_effect(Y, oblige)`, `duty_action(Y, A)`, `duty_relation(Y, T)` | `atom`, for an `Oblige` atom |
| `duty_of(Y, Duty)`, `duty_scope(Y, InstScope)`, `duty_deadline(Y, Lit)` | `duty(atom_id \| source_duty, scope, binding_key, deadline?, recurrence?)` |
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
  - **The id.** The bearer is in the id, and the other inherited parties are not. A duty shared by two parents with one bearer is therefore one atom, with one instance, and shared under two bearers it is two. `binding_key` (`due2-workflows.md` §3.1) also holds the other inherited parties, but a witness reads only the bearer, and a `grant` instance is keyed on the request (`due2-workflows.md` §5.3). So two atoms that differ only in another party would have the same findings, and the reply names both by one duty IRI.
  - **Edges.** `pre(X, Y)` fans out over every atom of the duty (`odrl-compound-to-atomic-normalization.md` §6.3), so a permission atom's preconditions are read as a conjunction. An inheriting duty gives `X` only its atoms with `X`'s bearer. A permission that is its own precondition is `reject("RuleReferenceCycle", R)`.
  - **Timing and scope.** `dprod:deadline` on a duty, when DPROD is selected, gives `duty_deadline(Y, Lit)`, `absolute` for an `xsd:dateTime` and `relative` for an `xsd:duration` (`deadline_kind/2`). Two deadlines, or one of another type, is `reject("InvalidTiming", Duty)`; a deadline or a recurrence on the policy or a rule is `reject("TimingOutsideDuty", Node)`. `due2:instanceScope` gives `duty_scope(Y, InstScope)`, `member` by default.

### `kleene.lp`

The order `f < u < t`, as `rank(V, N)`, and `two_valued/1` (`f` and `t`, the values a completed item can take). Kleene conjunction is the truth value of least rank (`#min`), disjunction that of greatest rank (`#max`), and negation maps rank `N` to `2 − N`. The integrity constraints over these values are in `integrity.lp`.

### `constraint.lp`

Reads the constraint trees the policy authored (`due2-profiles.md` §4, §5), and checks them. A rule's `odrl:constraint` values are its roots (`top_constraint/2`), and an action term's `odrl:refinement` values are its refinement roots (`top_refinement/2`). A list value gives one root per item. Each root is one conjunct of every atom of the rule or the action term (§ `applies.lp`).

- **Nodes.** `cnode(C)` is a root or a member. A node with an `odrl:leftOperand` is a `leaf(C)`, with `left(C, Op)`, `op(C, O)` (its core operator), and `right(C, Term)` (its right operand values). A node with a connective predicate is `conn(C, K)`, with `member(C, D)`. Members, like the right operand values of a set-based operator, may be one RDF list or repeated values, and both are the same set (`decisions/0013`).
- **No rewriting.** The tree is evaluated as authored. Normalisation stage 2 would rewrite it to NNF and DNF; strong Kleene logic gives a tree the value of its NNF and its DNF, so `compare.lp` computes that value on the tree itself (§ `compare.lp`), and no DNF is ever built.

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

`isA` over a set-valued operand is `reject("OperatorTypeMismatch", C)`. A set-valued operand under an operator of one left value (`single_left/1`: `eq`, `neq`, the order operators, `isAnyOf`, `isNoneOf`) has no reading in the spec, and declines as `constraint: set-valued operand on a single-value operator`.

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

A fact with any other status (`missing`, `invalid`, `conflict`, `unresolved`), no fact at all, or an absent parameter or context value leaves the read unanswered, so `read_resolved/2` fails. A `witness` read in world `k` is never answered, but no world-`k` leaf makes one: a witness leaf lies in a witness condition, which world `k` does not evaluate, and a rule's leaf on the witness source is rejected (§ `operand.lp`, `WitnessOutsideDuty`). Then, in each world:

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

**Connectives.** `and` is the least rank of its members, `or` the greatest, `dprod:not` maps rank `N` to `2 − N`, and `xone` is the disjunction of its terms `xone_term(W, C, D, N)`: member `D` and the negation of every other member, ⋁ᵢ (aᵢ ∧ ⋀ⱼ≠ᵢ ¬aⱼ). Strong Kleene logic gives the tree the same value as its NNF and its DNF, because De Morgan's laws, double negation, and distributivity hold in it, so these rules realise the structural rules of normalisation stage 2 without rewriting. `xone` uses its expansion, not "exactly one is `t`", so that `t xone u` is `u`, as the expansion gives, and not `t`.

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
- **applies** is the Kleene conjunction of the atom's parts. The rule uses `#min` as a function: `Min = #min { N : … }` binds the least rank. Every atom has an action and a target part, so the set is never empty. If it were, `#min` would be `#sup`, no rank would match, and the item constraint in `integrity.lp` would fail.

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
| `effective` | `occurred_at` ≤ the SOTW's `effective_at` | `occurred_at` is later | the SOTW has no `effective_at` |
| `deadline` | the duty has no deadline, or `occurred_at` ≤ the deadline (`deadline_at/2`) | `occurred_at` is later | never: an unplaceable deadline declines |
| `action` | the evidence's action is the duty's, or included in it (`ev_reaches/2`) | otherwise | never: the closure is closed-world |
| `object` | the duty has no relation value, or the evidence's object is it | otherwise, an evidence record with no object included | never |
| `actor` | the actor is the bearer; for bearer `none`, the actor is the request subject (`subject/1`) | the actor is someone else | the bearer is `none` and the request names no subject |
| `signer` | the config lists no signer for the duty (`signed/1`), or lists the evidence's issuer (`admitted/2`) | it lists signers, and not the issuer | never |
| `discharges` | the instance is not keyed on the request (`keyed/1`), or the evidence discharges the duty under the request's `reference` (`discharged/2`) | it is keyed, and the evidence does not | never |

The deadline is the absolute one, or the activation plus a relative one (`plus/3`). The activation (`activation_at/2`) is the SOTW's record for the duty's IRI (`activated/1`), the key the corpus gives a non-recurring instance, or `effective_at` when the SOTW has none (`due2-workflows.md` §5.3). An instance is keyed when its scope is `grant` and the request has a `reference`; without one, a `grant` duty falls back to `member`.

**Fulfilled and status.** `witness(Y, E)` is the Kleene conjunction of the seven checks and of the ranks of `Y`'s witness conditions in world `wit(E)`. `fulfilled(Y)` is the Kleene disjunction of the witnesses, `f` when there is no evidence. `passed(Y)` holds when the deadline is earlier than `effective_at`. It is fixed per evaluation, since both instants are inputs, so it is a fact about the vector, not a finding. The duty status `status(k, Y, S)` is the table of `due2-workflows.md` §5.3:

| `fulfilled(Y)` | `passed(Y)` | Duty status |
|---|---|---|
| `t` | either | `fulfilled` |
| `f` | no | `outstanding` |
| `f` | yes | `violated` |
| `u` | either | `unknown` |

A duty with no deadline never passes, so it is never `violated`. The table has no row for a deadline it cannot place against `effective_at`, so a duty whose deadline has no position, or a vector with a deadline and no `effective_at`, declines as `duty: deadline not comparable`.

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

`due2-workflows.md` §6.4, `decisions/0012`, `decisions/0016`. `u_atom(X)` holds for an atom whose finding is `u`. A `u` atom reads completion variables, and `reads(X, L)` collects them per atom. A `u` part of an `f` atom reads none, because the atom is `f` in every completion. A choice gives each variable `t` or `f` in world `c`, so solve 2's answer sets are exactly the completions. In each world an atom that is not `u` keeps its finding. For a `u` atom, its parts are re-derived in the world (`part_in/3`), their Kleene conjunction is taken (`pre_in/3`), and `applies` is that conjunction when it is `t` or `f`, and the value of `fin(X)` when it is `u`. `completed_item/1` lists what must have a value in every world: every finding.

**Statuses.** Each `u` leaf has one status (`leaf_status/2`): its operand's read status in world `k` from `operand.lp` (`read_status/3`), or `misfit` when the read is `ok` and the leaf is still `u`, which only a misfit comparison makes it. A leaf whose status is not `unresolved` is opaque (`opaque_leaf/1`). An unresolved value exists and fits its operator, so of a leaf and its complement exactly one holds, and pairing them is sound. A missing, invalid, conflicting, or misfit value gives no such guarantee: for `"abc"`, neither `lt 5` nor `gteq 5` holds (`decisions/0016`, § Question).

**Opaque parts.** A `u` target part, a `u` party part, and an opaque leaf in an opened tree make the atom opaque (`opaque_atom/1`), and the atom gets the variable `fin(X)`. In each world an opaque target or party part keeps rank 1, and so does an opaque leaf. A connective above it is re-evaluated under strong Kleene logic, so the tree, and the atom's conjunction, can stay `u` in the world. Then `fin(X)` decides the atom. When the paired leaves settle the tree anyway, `fin(X)` is read but moves nothing: a `t` member of an `or` makes it `t`, and an `f` conjunct makes the atom `f`. An opaque part therefore shares a variable with no other part, its complement included, as `decisions/0016` #2 asks. Two atoms on one absent target are completed separately, and so are a leaf on a missing operand and its complement.

**Paired variables.** A `u` constraint part is completed node by node, but only on its open nodes (`opened/2`, `open/1`): those that are `u` and lie on a path of `u` nodes from the part's root. A node that is `t` or `f` keeps its value in every completion, because strong Kleene logic is monotone: replacing a `u` by `t` or `f` never turns a `t` into `f`, or an `f` into `t`. So:

- each open paired leaf reads one variable with a polarity (`leaf_lit(C, L, Pol)`);
- in each completion world, each open node gets a rank, `crank(W, C, N)`. A paired leaf takes its variable's value, 0 or 2, negated for `neg`. An opaque leaf keeps 1. An open connective is re-evaluated from its members by the connective rules of `compare.lp`, which the world applies to its open nodes (`evaluates(W, C)`). A member that is not open keeps its rank in world `k`;
- the constraint part takes its root's rank in the world.

**The key.** Two open paired leaves read one variable when they make the same comparison (`due2-workflows.md` §6.4). The key has five components:

| Component | Relation | Note |
|---|---|---|
| scope | `scope/2` (`constraint.lp`) | `rule` or `action` |
| binding | `src/2`, `prop/2` (`operand.lp`) | where the operand reads, not its IRI: two operands bound to one property read one value |
| positive operator | `op_literal(O, Base, Pol)` | a complement asserts its `Base`, `neg` |
| right operand values | `leaf_attr(C, right(Term))` | a set of terms |
| units | `leaf_attr(C, unit(Iri))` | a set |

The complements are `neq` of `eq`, `gteq` of `lt`, `gt` of `lteq`, and `isNoneOf` of `isAnyOf` (`complement/2`). `leaf_key/5` holds the first three components. Two leaves with one `leaf_key` differ when one has an attribute the other lacks (`attr_apart/2`), and `same_key/2` holds when neither does. The variable is `cons(D)`, with `D` the least leaf of the class in clingo's term order, so every leaf of the class names the same variable.

Right operands compare as terms, not values, so `5` and `5.0` are two variables. A node reached from both a rule's constraint and an action's refinement has two scopes, and so two keys for one value. It declines as `constraint: node in two scopes`.

**Example.** This is the first row of `test_completion_key`, copied from a run. Under `perm`, permission `ex:r1` has the leaf `c1`, `ex:x eq 5`, and permission `ex:r2` the leaf `c2`, `ex:x neq 5`. `ex:x` reads the state, which has no fact for it, so it is `unresolved`. Both leaves are `u` and paired, so both findings are `u`, and both leaves are open. They share a key: scope `rule`, the state property `ex:x`, base `eq`, right operand `{5}`, no unit. In the run, `c1` is the lesser label, so `leaf_lit(c1, cons(c1), pos)` and `leaf_lit(c2, cons(c1), neg)` hold: one variable, two completions.

| `cons(c1)` | `c1` | `c2` | applies | verdict |
|---|---|---|---|---|
| `t` | 2 | 0 | `ex:r1` | `Permit` |
| `f` | 0 | 2 | `ex:r2` | `Permit` |

The verdict is `Permit` in both, so the reply is a definite `Permit`, although both findings are `u`. Its basis is empty, because neither permission applies in both completions (§ `resolve.lp`). With one variable per leaf, some completion would make both leaves rank 0 and give `NotApplicable`, and the reply would be `Indeterminate`: the precision the key buys. With `ex:x` missing instead, the leaves are opaque, each atom is decided by its own `fin` variable, and the reply is that `Indeterminate`, `NotApplicable` to `Permit`. `test_opaque_is_not_paired` pins the same contrast on `lt` and `gteq`.

**Different values, different variables.** `ex:x eq 5` and `ex:x eq 6` are separate variables (`decisions/0012` #3). `ex:x` is single-valued, so no state realises both `t`, yet that completion is enumerated. The completion is domain-unaware: it does not know which variables exclude each other. Domain-aware completion is `due2-workflows.md` §9 open decision 6. The consequences follow from the completions being a superset of the realisable ones:

- a definite verdict holds in every completion, so it holds in every realisable one, and it is sound;
- an `Indeterminate` may be reported where every realisable completion agrees, so precision, not soundness, is what is lost;
- a range covers every realisable verdict, and may be wider.

Two kinds of correlation are not seen by the key:

- hierarchies: with `ex:a1 odrl:partOf ex:a`, a value `ex:a1` would make both `ex:x isPartOf ex:a1` and `ex:x isPartOf ex:a` `t`;
- comparisons on one value: `ex:x lt 5` and `ex:x lt 3`, or `5` and `5.0`, are separate variables, though `ex:x lt 3` implies `ex:x lt 5`, and `5` equals `5.0`.

In both cases the variables stay independent, so the completions remain a superset of the realisable ones, and the three consequences above still hold. An opaque part's `fin` variable is independent of every other by construction, so it too only adds completions.

### `resolve.lp`

`due2-workflows.md` §6.1, §6.2, §6.4. Every relation carries the world `W`, and within a world every value is `t` or `f`:

- A candidate is a `permit` atom that applies. Duties are declined (#49), so every surviving candidate is ready, and `Pending` does not occur.
- **Conflict within the policy** (`due2-workflows.md` §6.2 #1):
  - `prohibit`: an applying `forbid` eliminates the policy's candidates;
  - `perm`: an applying candidate eliminates the policy's `forbid` atoms;
  - `invalid`: an applying candidate and an applying `forbid` together eliminate everything in the policy.
- **Across policies** (`due2-workflows.md` §6.2 #2): a surviving `forbid` eliminates every candidate (prohibit-overrides).
- **Verdict**, per the table of `due2-workflows.md` §6.4: `Deny` if a `forbid` survives; otherwise `Permit` if a candidate survives; otherwise `NotApplicable`.
- **Basis of one world**: `basis(W, X, prohibition)` for each surviving `forbid` of a `Deny`, and `basis(W, X, permission)` for each surviving candidate of a `Permit`.

**The cautious basis.** Solve 2 reports a basis row only if it holds in every completion: an atom that carries a definite verdict whatever the unknowns are. An `Indeterminate` has no such row, and its basis comes from solve 3 instead. When no single atom carries a definite verdict in every completion, the basis is empty, and `unknown_parts` names what was unknown (`decisions/0016` #4). The brute-force oracle computes the same basis. Two shapes show where it differs from "the atoms with finding `t` that survive" (`test_completed_basis`):

- **An empty basis.** Prohibitions `ex:x eq 5` and `ex:x neq 5`, with `ex:x` unresolved, read one variable with opposite polarities. Each completion applies one of them, so the verdict is `Deny` in both, and no prohibition survives in both. The basis is empty.
- **A `u` atom in the basis.** A permission under `ex:x eq 5 or ex:x neq 5` has finding `u`, but its tree is `t` in every completion, so it carries the `Permit` in every completion and is in the basis.

**When the basis is not empty.** The cautious basis of a definite verdict is not empty when the completion that makes every variable `f`, the all-`f` completion, applies only the atoms whose finding is `t`. That holds when every open paired leaf is `pos` and every open connective is an `and` or an `or`, and so whenever no leaf is paired, whatever the connectives. The argument has three steps:

1. Under the premise, the all-`f` completion gives every open node rank 0 or 1. A paired leaf is 0 by its variable, and an opaque leaf is 1. An open `and` has an open member, which is at most 1. An open `or` has no `t` member, since it would be `t`, so its members are `f` or open, and all are at most 1. With no paired leaf, every open node keeps rank 1 whatever its connective, since nothing it reads has changed. So the conjunction of a `u` atom's parts is at most 1, and the atom is `f`: by that conjunction, or by `fin(X)`, which is `f`. The atoms that apply are exactly those with finding `t`, and these apply in every completion.
2. Take a `Deny`. In the all-`f` completion some `forbid` `Y` with finding `t` survives. Within one policy, only a candidate removes `Y` (`perm`, or `invalid` together with a forbid). But then no forbid of the policy survives under `perm`, and the policy is void under `invalid`, so the verdict would not be `Deny`. So `Y` survives in every completion, and it is in the cautious basis.
3. Take a `Permit`. In the all-`f` completion some candidate `X` with finding `t` survives. Only a surviving `forbid` (under `prohibit`, or across policies) or a void policy (under `invalid`) removes `X`, and each of these also removes every other candidate, so the verdict would not be `Permit`. So `X` survives in every completion.

A paired `neg` leaf, or a `dprod:not` or an `xone` over a paired leaf, breaks step 1: the all-`f` completion can make an atom apply whose finding is `u`, as `ex:x neq 5` does in the first shape above, and as `t xone u` does. So an empty basis under a definite verdict needs an `unresolved` unknown part, which `tools/check_corpus.py` asks a scenario to list.

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

They are why a rule deleted from the program fails loudly. Without its rule, some item has no value, some read no outcome or status, or some world no verdict, so the solve has no model and the reply is an `error`, never a verdict standing on the missing part (§ Tests).

### `explain.lp`

`due2-workflows.md` §3.5, §6.2, `decisions/0011` #4. Elimination is read from the findings, not from a world, so `elim(X, Y, Strat)` carries no world and is the same in every completion. A remover `Y` has finding `t`. A removed atom `X` has finding `t` or `u`: `u` atoms eliminate nothing (`due2-workflows.md` §6.2), but they can be removed.

- `prohibit`: each `t` `forbid` of the policy removes each of its candidates;
- `perm`: each `t` candidate removes each of the policy's `forbid` atoms;
- `invalid`: a policy with a `t` candidate and a `t` `forbid` is void. Each of its `t` or `u` atoms is removed by each other `t` atom of the policy;
- the combination (`prohibit-overrides`, the only one read): each `t` `forbid` that its own policy did not remove removes each candidate of every other policy. `structure.lp` admits one policy, so no vector reaches this rule. It is there because `due2-workflows.md` §3.5 records cross-policy eliminations as rows (`formalisation-review.md` §3 #3), and `test_combination_rows_on_facts` runs it on hand-written facts.

**One row per remover.** An atom removed by two `forbid` atoms has two rows (`due2-workflows.md` §3.5, #57). Each row is a complete reason: whenever `X` applies, `Y` applies too, because `Y` is `t`, and `Y` removes it. A reader can check each row against the policy alone. A single row naming the first remover would hide the others, and which one is "first" would depend on the order of the facts. A `u` remover gives no row, because it removes `X` only in some completions, and that is not a reason that holds whatever the unknowns are.

**Unknown parts** (`decisions/0016` #3 and its amendment). `unknown_part(X, Input, S)` holds for every `u` part of every atom whose finding is `t` or `u`: `target` and `party(F)` when the request field is absent, status `missing`, and `prop(Prop)` for each `u` leaf anywhere in the atom's trees (`in_tree/2`), with its `leaf_status/2`. The rows read the finding, not a world, so they do not depend on the completion. An `f` atom is not reported, for two reasons. First, none of its `u` parts can change it: its finding is the Kleene conjunction of its parts, and an `f` part makes it `f` in every completion. Second, `due2-workflows.md` §5.5 lets an index skip an atom that is certainly `f`, so its rows would depend on the index. A `u` leaf under a node that another member decides is still reported, in a `t` atom as in a `u` one. The reply then names everything that was unknown in the rules that can apply, whether or not it mattered, and a renderer may show less. Under a status the same for every rule, as an absent target is, every atom carries the row, so `interpret.py` projects them to the rule, and the reply has one row per rule, input, and status.

The same file holds the structure's one-value constraints: every atom has exactly one `atom_effect`, `atom_policy`, and `atom_rule`, so a row names exactly one of each (`formalisation-review.md` §3 #2).

### `pivot.lp`

`decisions/0011` #1 to #3. Solve 3 only, after solve 2 has found an `Indeterminate`:

- `world(flip)`, and a choice of exactly one `pivot(L)` among the variables;
- `flip` copies `c`'s value of every variable, except the pivot, whose value it negates;
- an integrity constraint keeps only the models where `c` and `flip` have different verdicts;
- `unknown(X)` holds for an atom whose finding is `u` and which reads the pivot in one of its `u` parts (`reads/2`).

Brave enumeration gives the union over the models. The `unknown` atoms are those with a pivotal variable (`decisions/0011` #1). The range is the least and the greatest `verdict(c, Verdict)` that occurs, in the chain `Deny < NotApplicable < Pending < Permit` (`decisions/0011` #3).

**Why the brave verdicts are exactly the completions' verdicts.** The flip constraint drops models, so it is not obvious that every verdict some completion takes survives in some model. It does:

1. The completions are the corners of an `n`-dimensional cube, and two corners are neighbours when they differ in one variable. The cube is connected: any corner reaches any other by flipping, one at a time, the variables in which they differ.
2. An `Indeterminate` means at least two verdicts occur. Let corner `c₁` have verdict `V`, and corner `c₂` some other verdict.
3. On the path from `c₁` to `c₂` the verdict starts at `V` and ends elsewhere, so some step goes from a corner `c` with verdict `V` to a neighbour without it.
4. That step is a model of solve 3: completion `c`, pivot the flipped variable. So `verdict(c, V)` is true in some model.

Conversely, `c` in every model is a completion. So the brave `verdict(c, _)` atoms are exactly the verdicts the completions take, and the range is exact. In § Worked example, `NotApplicable` occurs only at (`f`, `f`), and it survives through both of that corner's flips.

## Output

`interpret` replies with:

- `verdict`, `frontier: []`, `obligations: []`, and `exact: true`. The reply enumerates every completion, which is the definition itself, so it is exact. A vector it cannot enumerate within the variable cap is declined instead;
- `verdict_basis`: the rows of solve 2 for a definite verdict, or role `unknown` for each `unknown(X)` of solve 3;
- `eliminated`: each `elim(X, Y, Strat)`, with `Strat` the conflict strategy or the combination;
- `unknown_parts`: each `unknown_part(X, Input, S)` as `{"ref", "input", "status"}`, under any verdict. `input` is `odrl:target`, the party function's IRI, or the property's IRI. The rows are sorted by their full IRIs;
- `verdict_range` `{"low", "high"}`, for an `Indeterminate` only.

Atoms are projected to their source rule, the `R` of `a(R, A, T, Party)` (`due2-workflows.md` §3.7). So the atoms of one rule are one entry. An elimination whose `ref` and `by` come from the same rule (under `invalid`, two atoms of one rule) is dropped, because at the authored level the rule would remove itself, and `invalid` says "other than itself".

## Negation as failure

`not` never turns a missing truth value into `f`. Each use reads something that is complete by construction:

- the declared hierarchy edges (`not action_matches`, `not target_matches`, `not party_matches`, `not le_k`, `not inst`), which are closed-world (`due2-profiles.md` §6);
- input syntax and what `lift.lp`, `structure.lp`, `constraint.lp`, and `duty.lp` derive from it: whether a family is stated, a predicate consumed, a function named, a duty inheriting or with a bearer, a node a list, a leaf or a connective, a leaf a witness leaf, a tree with a witness or a guard leaf (`has_witness`, `has_guard`), a node in a rule's tree (`rule_node`) or in a witness condition, or a duty with a deadline or a relation value. `witness_only/1`, which `evaluates(k, C)` negates, reads only these, never a rank, so the ground program has no cycle through it;
- the value table and the term shapes (`not placed`, `not kind`, `not same_type`), which decide only that a pair is a misfit, and a misfit is `u`;
- the reads: `not read_resolved`, `not card_ok`, and `not conforms` make a read `u`, never `f`;
- in `completion.lp`, over relations fixed before the choice. `not complement`, `not leaf_attr`, and `not attr_apart` decide only which variable a leaf reads and with which polarity. `not open` picks the members of an open node that keep their rank, and these are `t` or `f`, because a `u` member of an open node is open itself. `open/1` reads the ranks of world `k`, and no rule for world `k` reads another world, so the ground program has no cycle through `not open`, although `crank/3` holds the ranks of every world;
- inside one world in `resolve.lp`, where every value is already `t` or `f`;
- in `explain.lp`, over `elim` rows derived from findings (a `forbid` its own policy did not remove). A `u` finding gives no row, and the rows are only ever read as "no remover", never as a truth value;
- in `duty.lp`'s witness test, over input records, which are complete: an evidence record lists every field it has, and the config every signer. So `not evidence_object` and an actor that is not the bearer make a check `f`. For the object this is the spike's reading of the equality `e.object = d.relation_value` of `due2-workflows.md` §5.3, where `object` is optional: evidence that records no object does not record the duty's relation value, so the equality does not hold. `not signed`, `not admitted`, `not keyed`, `not discharged`, and `not activated` read the config, the request, and the SOTW the same way. `not ev_reaches` reads the declared `includedIn` edges, which are closed-world. Where an input that the test needs is absent, the check is `u`, not `f`: `not effective_pos` makes `effective` `u`, and `not subject` makes `actor` `u` for a duty whose bearer is the subject. The activation is the one exception, and it takes the default the spec gives it, `effective_at`. `not passed` cannot hide an undecided deadline, because a deadline that has no position declines the vector.

A missing truth value has no `holds` fact. Then an integrity constraint fails, instead of the value defaulting to `f`.

## Declines

A vector is declined, never guessed at, when it uses something the spike does not read. The scorecard (`scorecard.json`) counts the declines and their reasons.

**In the policy** (`lift.lp`). A predicate `P` on node `S` is consumed when the program reads it there:

| Predicate | Where |
|---|---|
| `rdf:type` | anywhere |
| `odrl:uid` | when it names `S` itself |
| `odrl:profile`, `odrl:conflict`, `odrl:permission`, `odrl:prohibition` | the policy |
| `odrl:action`, `odrl:target`, and the function predicates | anywhere: they are read on the policy, its rules, and its duties, and elsewhere they hang under a declined link (`odrl:duty`) or off the policy, so declining on them would hide the feature |
| `odrl:includedIn`, `odrl:partOf`, `odrl:source`, `odrl:leftOperand`, `odrl:operator`, `odrl:rightOperand`, `odrl:unit`, the connectives, the binding attributes, `due2:conceptScheme`, `skos:broader`, `skos:narrower`, `skos:inScheme`, `skos:topConceptOf`, and `skos:hasTopConcept` | anywhere |
| `odrl:constraint` | a rule or a duty |
| `odrl:output`, `due2:instanceScope` | a duty |
| `dprod:deadline`, `dprod:recurrence` | the policy, a rule, or a duty, with DPROD selected; on the policy or a rule they are rejected |
| `odrl:refinement` | an action term, or a collection (where it is rejected) |
| `rdf:value` | an action term |

A predicate is on the annotation allowlist when it is:

- `rdfs:label` or `rdfs:comment`;
- any `dct:` or `prov:` term;
- `skos:prefLabel`, `skos:altLabel`, `skos:hiddenLabel`, `skos:definition`, or `skos:note`;
- `dprod:offerLifecycleStatus`, `dprod:contractLifecycleStatus`, `dprod:effectiveDate`, `dprod:expirationDate`, or `dprod:acceptsOffer`, which are metadata (`due2-profiles.md` §8.1).

`unsupported(P)` holds for a predicate that is neither consumed nor allowlisted, when either:

- it is in a vocabulary namespace: `odrl:`, `due2:`, or a selected profile's IRI. Such a predicate means something, so ignoring it could change the verdict. Examples are `odrl:duty`, `odrl:remedy`, and `odrl:constraint` on a node that is not a rule; or
- it sits on a structure node (the policy, one of its rules, or one of its duties), whatever its namespace. An unknown predicate there may be a semantic extension (`odrl-compound-to-atomic-normalization.md` §3: "MUST NOT introduce additional … semantics").

Elsewhere, on asset, party, and action nodes, a predicate from another vocabulary is data the spike never reads, and it is ignored. Issue #53 adds a W1 warning for an unevaluated predicate on a structure node. The allowlist is the spike's version of that line.

**The other policy declines**, each a fixed reason:

| Reason | File | Why |
|---|---|---|
| `action: blank node without rdf:value`, `action: several rdf:value` | `structure.lp` | the action term names no single action |
| `binding: cardinality`, `binding: range` | `operand.lp` | a cardinality or range the spike cannot read, or two of them |
| `constraint: cycle`, `constraint: dprod:not with several members`, `constraint: leaf with a connective`, `constraint: list on a scalar operator`, `constraint: two connectives` | `constraint.lp` | no reading, or none the spec settles |
| `constraint: node in two scopes` | `constraint.lp` | one node would need two completion variables (§ `completion.lp`) |
| `constraint: set-valued operand on a single-value operator` | `operand.lp` | no reading in `due2-profiles.md` §4 |
| `duty: also a permission or prohibition` | `structure.lp` | a rule read as a duty, which the spec gives no reading |
| `duty: deadline not comparable` | `duty.lp` | a deadline with no position in the `instant` space, or a deadline and no `effective_at`: the status table of `due2-workflows.md` §5.3 has no row for a deadline it cannot place (§ `duty.lp`) |
| `duty: bearer from two functions` | `structure.lp` | two functions that play the bearer role disagree on a duty, both stated by it or both interiorised from the policy level: two bearers for one performance, which the spec does not settle |
| `duty: parent with two bearers` | `structure.lp` | a parent atom that passes two bearers to an inheriting duty |
| `duty: instance scope` | `structure.lp` | a `due2:instanceScope` other than `due2:member` or `due2:grant`, or two; no diagnostic covers it |
| `odrl:partOf: cross-kind edge`, `odrl:partOf: untyped collection` | `lift.lp` | a hierarchy the spike does not trust |
| `profile-conflict-defaults` | `structure.lp` | two profile defaults, and no rule for which wins |
| `recurrence` | `structure.lp` | a duty's `dprod:recurrence` needs occurrences, which the spike does not compute (`decisions/0009` #7) |

`odrl:duty` and `odrl:obligation` are not consumed (#49), so a reply declines a policy with a duty on one of them, and the `duty:` and `recurrence` reasons show in the program's relations, which the tests read (§ Tests).

**In the input** (`lift.lp`). The driver flattens every field, and `unsupported_input(Field)` names each field the program does not read:

- a `sotw.closure` edge of a relation other than `includedIn`, `partOf`, `rdf:type`, `rdfs:subClassOf`, `skos:broader`, and `skos:inScheme`;
- `config.combination` other than `"prohibit-overrides"`, and any `config.violations`;
- each `unread(Field)` (§ Input facts).

`request.params`, `sotw.facts`, and the context values are read by `operand.lp`; `sotw.evidence` by `operand.lp` and `duty.lp`; and `sotw.activation` and `config.signers` by `duty.lp`. An empty field gives no facts, so it is not declined. When several fields hold, the smallest name wins: `config.*` before `request.*` before `sotw.*`.

**In the values.** `unsupported_value(Reason)`, read after the input declines: an unplaceable compared literal (§ Values), or `value: derived string datatypes` (§ `compare.lp`).

**Above the cap.** More than 64 completion variables is `variable-cap` (§ Data flow).

## Errors

These are an `error` reply, not a decline:

- an unknown `odrl:profile`;
- a policy that is not admissible (`reject`). The codes are `NoPolicy`, `MultiplePolicies`, `InvalidConflict`, `MissingAction`, `MissingTarget`, `TargetAndOutput`, `RuleReferenceCycle`, `InvalidTiming`, and `TimingOutsideDuty` (`structure.lp`); `UnsupportedConstruct` (`lift.lp`); `MalformedConstraint`, `UnsupportedOperator`, `UnsupportedConnective`, `FloatingPointOperand`, and `MixedDuration` (`constraint.lp`); and `UnboundLeftOperand`, `InvalidBinding`, `ConflictingProfileDeclaration`, `RetypedOperand`, `OperandRangeMismatch`, `WitnessOutsideDuty`, and `OperatorTypeMismatch` (`operand.lp`); and `MixedDutyConstraint` (`duty.lp`). Each is defined in `due2-diagnostics.md`;
- a malformed vector (§ Input facts);
- an unsatisfiable program.

`interpret` receives only admissible policies from well-formed vectors, so each of these is a defect, in the vector or in the spike.

## Tests

The spike's own tests (`uv run pytest` in this directory) cover what the corpus cannot see. L9 cannot see a driver bug, so the driver is tested on its own (`correctness-strategy.md` §4.1). Each item names the risk it guards, and what got through without it.

**The program** (`test_interpret.py`), on inline Turtle and a small inline module set, not the repo's profiles:

- **Integrity.** A rule deleted from the program must not leave a verdict standing on the missing part. Deleting one rule from `kleene.lp`, `applies.lp`, `completion.lp`, or `resolve.lp` (`DELETIONS`), or the `eq` rule of `compare.lp` or the unresolved-read rule of `operand.lp` (`CONSTRAINT_DELETIONS`), turns the reply into an error, where the intact program answers. So does an atom with two effects. Each deletion's vector is one the intact program answers with a definite verdict: the constraint vector puts a `t` member, which the deletion does not touch, under an `or`.
- **Explanation.** Each basis role and elimination rule on a small policy, so a wrong row cannot hide behind a right verdict. A `u` candidate removed by a `t` prohibition under `prohibit`. A `u` prohibition beside a `t` candidate under `prohibit`, which removes nothing. Two rules on one absent target, and two on one absent assignee, are completed separately (`test_absent_fields_are_not_shared`): one shared variable would give `NotApplicable` to `Permit` under `perm`, and separate ones give `Deny` to `Permit`. An irrelevant `u` atom is not named `unknown`. Each range. The combination rule, on facts.
- **Worked examples** (`test_worked_example`, `test_constraint_worked_example`). The replies of § Worked example, its unknown parts included, and of the example in § `compare.lp`, so this note cannot drift from the program.
- **Operators** (`test_operators`, `test_hierarchy_operators`). Each operator on a value that makes it `t` and one that makes it `f`, so a rule that answers one way regardless is caught; and each misfit on a value that would be `f` under a two-valued reading: an IRI against a string, two language tags, an instant against a number. `isA` reads an `rdf:type` edge from the SOTW closure, so a closure the driver dropped would show. An empty read set is vacuously part of anything.
- **Concepts** (`test_concept_operators`, `test_concept_broader_cycle`). One scheme whose memberships use all three forms and whose edges include a `skos:narrower` triple. `eq` holds on identity, one inverted edge, and two edges, and not upward or with no path; without the scheme the same edges are not read. `neq` and `isNoneOf` exclude a concept below the right value. A read concept in no scheme and a string are `u` under `eq` and `neq` alike. The SOTW supplies a read concept's edge and membership, and an edge alone leaves it `invalid`; a right operand in a scheme by the SOTW only is rejected. A cycle of `broader` edges terminates. Deleting the narrower inversion, the transitive step, the `hasTopConcept` membership, the read membership, or the out-of-scheme rule fails at least three rows each. The three rejections are rows of `test_constraint_rejections`.
- **Reads** (`test_state_read`, `test_reads`). Every SOTW status but `resolved`, and no fact at all, is `u`, never `f`; so are two values and no value for a `one` operand, and a read value outside the range. The context reads the assignee and the clock.
- **Bindings** (`test_binding_layers`, `test_profile_module_spans_files`, `test_retyped_operand`, `test_operand_range_mismatch`). The highest layer that states the property gives it: with a profile binding, a request giving only the core property is `u`, not a match. Two profile modules that agree bind, and two that differ are rejected, so a rule that let one module win is caught. A profile split over two files is one module, so a rule that compared files is caught. A policy may restate where a baseline operand reads, or its type with the owner's values, and any other type is rejected; the `due2:set` row fails if the default does not count as stated. A range of another kind than the read property's is rejected, and `rdfs:Literal` matches any literal range but not a class range.
- **Hierarchies** (`test_typed_part_of`). A requested asset in a target collection matches, and one that is not a member does not; a named party in an assignee collection matches; an untyped collection and a cross-kind edge decline.
- **Rules, refinements, and units** (`test_prohibition_constraint`, `test_refinement`, `test_unit_labels_without_converting`). A constraint on a prohibition decides a `Deny`; a refinement is a conjunct of the atom; a unit does not change a comparison.
- **The completion key** (`test_completion_key`, `test_binding_not_operand_iri`). Two rules under `perm`, each with one `u` leaf on an unresolved operand. When the two leaves share every component of the key, and one is the other's complement, one of the rules applies in every completion, and the verdict is `Permit`. Each other row changes one component: the property, the right operand, the operator, a unit, the unit's value, `5` against `5.0`, the right operand set, or the scope. Each of these gives two variables, and `Indeterminate`. Without the rows that share a key, one variable per leaf would pass. Without the rows that differ, a key that merged too much would pass. Two operand IRIs bound to one property share a variable, so a key on the operand IRI is caught.
- **Opaque parts** (`test_opaque_is_not_paired`). `decisions/0016`'s example: permissions `x lt 5` and `x gteq 5`. With `x = 3`, `Permit` and no unknown part. With `x` absent, `"abc"`, or `ex:v`, the leaves are opaque, and the reply is `Indeterminate`, `NotApplicable` to `Permit`, naming the status. With `x` unresolved, one variable gives a definite `Permit`. Before `decisions/0016` the three opaque rows were a definite `Permit`, so a program that paired every `u` leaf is caught.
- **Unknown parts** (`test_unknown_parts`, `test_invalid_read_is_reported`). One leaf on a state property, under every status the SOTW can give: `missing`, `invalid`, `conflict`, `unresolved`, no fact, `resolved` with no value, with two values, and with a misfit value. An absent target and an absent assignee are `missing`. An atom whose action does not match, so `f`, reports nothing, though its leaf is unresolved and its assignee absent. A read value outside the declared range is `invalid`. A status mapped to the wrong name, or a part reported for an `f` atom, fails a row.
- **A decided leaf** (`test_decided_leaf_is_reported`). A permission `x eq ex:v or y eq ex:w`, with `x` resolved to `ex:v` and `y` unresolved, is `Permit`, and its reply names `y` as `unresolved`. A program that reported only `u` atoms would name nothing.
- **The completed basis** (`test_completed_basis`). The two shapes of § `resolve.lp`, a `Permit` whose basis names a `u` permission and a `Deny` with an empty basis, and the `Permit` with an empty basis of the example in § `completion.lp`. They pin the basis `decisions/0016` #4 settled.
- **The cap** (`test_variable_cap`). An `or` of `n` leaves on one unresolved operand, each with its own right operand, each leaf written twice: `n` variables. `n = 64` answers and `n = 65` declines as `variable-cap`. The repeated leaves leave ground `var/1` atoms that no model makes true, so a count of the ground atoms would decline both.
- **Rejections and declines** (`test_constraint_rejections`, `test_constraint_declines`, `test_datatypes_differ_without_a_range`, `test_derived_strings_decline`, `test_node_in_two_scopes`). Each code and reason of § Declines and § Errors that a constraint or a binding produces, on a minimal policy, so a check that is deleted or never fires is caught.
- **Declines.** A feature the spike does not read must decline, never be ignored, and one it reads must not decline: `sotw.evidence`, `sotw.activation`, and `config.signers` give a `Permit` on a policy without duties (`test_duty_inputs_are_read`). A policy with both `odrl:duty` and `odrl:remedy` declines naming `odrl:duty`, the smaller IRI, and gives the same reason on a repeat. An unknown predicate on a rule declines. An allowlisted annotation does not. An unknown predicate on an asset node outside the vocabulary namespaces is ignored. Each input-side decline names its field, and an unplaceable input value declines naming its reason.
- **Duties** (`test_duty.py`), on solve 1's program. A reply declines a policy with `odrl:duty` or `odrl:obligation` (#49), so these tests read the duty relations from the program, not a reply:
  - **Inheritance.** The duty of a permission with two assignees is two duty atoms, each the precondition of the parent atom with its bearer. Shared by two permissions with one assignee, it is one atom, and a parent with no assignee passes `none`. A program that dropped the bearer from the id, or gave each parent atom every duty atom, fails a row. A duty that names its own party keeps it under every parent atom. A root obligation takes the policy's target and parties, and a precondition duty takes neither.
  - **Bearers.** A root obligation with `dprod:subjectOfDuty` and a different policy-level `odrl:assignee` has the stated party as its only bearer; without `states_bearer/1` it would decline as `duty: bearer from two functions`, as the three DPROD contract cases did. A duty that states both functions with different parties declines, and with the same party it does not.
  - **The split.** An `and` of a state leaf, a witness leaf, and an `actionTime` leaf gives one guard and two witness conditions. A witness refinement of a duty's action is a witness condition. An `or`, an `xone`, or a `dprod:not` over a guard leaf and a witness leaf is `MixedDutyConstraint`, and an `or` of witness leaves alone is not. Without the conjunction rule, the first row's `and` is one part with both kinds of leaf, and is rejected.
  - **Relations and timing.** A stated `odrl:output` is the relation, and the policy's target is not taken. Each deadline kind, each instance scope with `member` the default, and an unknown scope declines.
  - **Rejections.** `InvalidTiming` (two deadlines, and a deadline of another type), `TimingOutsideDuty`, `TargetAndOutput`, `MissingAction`, `RuleReferenceCycle`, and `WitnessOutsideDuty` for a witness refinement of a permission's action: without the action branch of `node_tree/2`, the last one passes.
  - **Recurrence.** A `dprod:recurrence` declines the vector as `recurrence`.
- **Duty findings** (`test_duty.py`), on one model of solve 2's program, integrity constraints included, so a finding or check that a rule forgets has no value and fails the solve:
  - **Owed** (`test_unguarded_duty_without_evidence_is_outstanding`, `test_guard_decides_owed`). A duty with no guard is owed and, with no evidence, `outstanding`: without the identity 2 in `owed`'s `#min`, it would have no `owed` value. A guard on a missing fact makes `owed` `u`, and the duty still has an instance; only an `f` guard removes it.
  - **The witness test** (`test_matching_evidence_fulfils`, `test_each_failing_check_fails_the_witness`, `test_admitted_issuer_and_discharged_reference_pass`, `test_no_named_subject_leaves_the_actor_unknown`). Matching evidence fulfils the duty. Then each of six checks fails on its own, the actor, the action, `effective`, the signer, the discharge, and the object, and each makes the witness `f`: a check that answered `t` regardless would leave the duty `fulfilled`. An admitted issuer and a discharge under the request's reference pass. A request that names no subject makes the actor check `u` and the duty status `unknown`, where a two-valued reading would say `outstanding`.
  - **The witness worlds** (`test_witness_condition_is_read_from_the_evidence`, `test_witness_only_nodes_are_not_world_k_items`, `test_action_time_is_the_evidence_time`). A witness leaf reads the evidence's params in `wit(E)`: matching, it is `t`; different, `f`; absent, `u`, and the duty status `unknown`. Read in world `k`, it would be `u` for every piece of evidence. In an `and` of a guard and a witness leaf, only the guard is a world-`k` item, and only the witness leaf is evaluated in `wit(E)`; without `witness_only/1`, world `k` would give the witness leaf a value, `u`, although it has no evidence to read. `due2:actionTime` `lteq` 10 May is `t` for evidence of 1 May and `f` for 20 May; read from the request's 1 June, both would be `f`.
  - **Deadlines** (`test_deadline_decides_outstanding_or_violated`, `test_late_witness_is_not_timely`). An absolute deadline before `effective_at` makes an unfulfilled obligation `violated`, and one after it `outstanding`. A relative one counts from the activation, and from `effective_at` without one, so `P1D` is `violated` from an activation in May and `outstanding` without one. Evidence after the deadline is no witness: without the deadline check, it would fulfil the duty. This is the worked example of § `duty.lp`.
  - **In force** (`test_obligation_without_a_matching_rule_is_not_in_force`). A root obligation in a policy with no permission or prohibition is not in force, so it has no instance, although the request asks for the obligation's own action on its target. A program that matched the obligation itself would find it in force.
- **Protocol.** `main.py` answers `init` with `ready`, declaring `interpret`, and echoes the request `id`.

**The brute-force differential** (`test_brute_force.py`, Hypothesis, `correctness-strategy.md` §4.1):

- **What it compares.** Over generated policies of permissions and prohibitions under each of the three conflict strategies, with absent targets and unnamed assignees, a Python oracle enumerates the completions, flips each variable alone, and derives the verdict, the basis, the eliminations, the `unknown` atoms, the range, and the unknown parts. They must equal the reply. A rule may carry constraint trees: depth two over operands `ex:o0` to `ex:o2`, each read from the request or from the state, with `eq`, `neq`, and the order operators against `1`, under `and`, `or`, `xone`, and `dprod:not`, with members as a list or as repeated values. An operand may have no value: an absent request parameter is `missing`, and a state property with no fact is `unresolved`. The oracle values a tree by supervaluation: it tries `t` and `f` for each `u` leaf occurrence, each on its own, and the tree is `u` when the tries disagree. That is strong Kleene logic for independent leaves, computed without the program's ranks. Under a completion, the oracle sets each unresolved leaf from its variable, negated for a complement operator, and takes the supervaluation again, so a missing leaf stays `u`. An atom whose parts are still `u` takes the value of its own variable, as `fin(X)` does; an absent target or party is such a part. An unresolved leaf's variable is its operand and positive operator, so `neq` reads `eq`'s variable negated, `gteq` reads `lt`'s, and `gt` reads `lteq`'s; every generated leaf is in rule scope against `1` with no unit, so these are the only key components that vary. The basis is the rows that hold in every completion (§ `resolve.lp`), and the unknown parts are every absent field and every leaf without a value, of every rule whose finding is not `f`. The oracle reads the generated rules, not the driver's facts, and shares only the spec's variable key (`due2-workflows.md` §6.4) and the statuses of `decisions/0016` with the program.
- **Examples.** Eighteen explicit cases fix the shapes random draws rarely reach: a `u` atom whose variable changes no verdict (under `prohibit` and `invalid`); two atoms on one absent target, each with a variable of its own; one tree per connective that changes value if the connective is misread (`and` as `or`, `or` as `and`, `dprod:not` as the identity, `xone` as `or`); a `u` leaf under an `and` and an `or` that decide anyway; a lone `u` leaf; an `or` of a leaf and its complement, which is `u` under Kleene logic but `t` in every completion when unresolved, and stays `u` when missing; two rules whose leaves are complements (`lt` and `gteq`), so one of them applies in every completion when unresolved, and neither need when missing; a tree with a missing and an unresolved leaf, where the world leaves it `u` and the atom's own variable decides; an `f` atom with an absent target and a missing leaf, whose unknown parts are not reported; and a `u` leaf under a `t` node, beside an open leaf with the same variable, where only the open leaf is read.
- **Mutants** (`test_differential_kills_mutant`). The differential must fail against each of twelve programs with one rule changed: the flip constraint of `pivot.lp` deleted; a missing leaf paired as if unresolved; one `fin` variable shared by every opaque atom; an opaque leaf read as `f`; unknown parts reported only for `u` atoms; unknown parts reported for `f` atoms; one constraint variable per leaf instead of per key; a complement read as its base; `u` atoms as removers; `and` and `or` swapped; `dprod:not` as the identity; `xone` without its negations. Each runs with 100 generated draws after the examples. In one derandomized measurement, generation alone first killed them after 106, 143, 6, 15, 857, 10, 36, 175, 6, 14, 58, and 121 draws. So without the examples, the flip, missing-paired, `u`-atoms-only, polarity, and `xone` mutants survive 100 draws.
- **Enumeration** (`test_enumeration_matches_fixed_solves`). The differential trusts that solve 2's answer sets are exactly the completions, and an oracle with the same mistake would hide a choice rule that admits a model that is not a completion, or misses one. Over 150 generated cases with at most six variables, the test solves solve 2's program once per assignment, with each variable's value a fact and the choice rule deleted. Each fixed solve has one model. The enumeration has `2^n` models, and their shown atoms are those of the fixed solves. The reply is `Indeterminate` exactly when the fixed solves reach more than one verdict. clingo's cautious consequences are the intersection of the fixed solves, so a misreading of the cautious enumeration is caught too. The test found that grounding leaves `var/1` atoms that no model makes true, which is why `interpret.py` counts the variables in the first model.
- **Shapes** (`test_generator_reaches_each_shape`). Over 400 derandomized draws, the generator must reach every conflict strategy, an `Indeterminate` with a non-pivotal `u` atom, two `u` atoms sharing a variable, an atom with a variable of its own, an open tree with an opaque and a paired leaf, an `f` atom on an absent target, open leaves reading one variable with both polarities, two constraint roots that are the same leaf (which the key must merge), and a `u` leaf under a deciding connective. A generator change that stops producing one of them would leave the differential passing on nothing; the test fails on a zero count instead.

**The driver** (`test_flatten.py`), over the repo's own files:

- **Graph round trip.** The flatten must drop nothing. For every policy and module file, `triple/3` decoded back to RDF is isomorphic to the parsed graph, lexical forms included. A plain literal and its `xsd:string` twin are one term (RDF 1.1).
- **Input round trip.** For every corpus vector, the request, SOTW, and config facts decode back to the input, with names expanded and lists read as sets.
- **Invariance** (Hypothesis). The facts must not depend on serialisation order. Shuffling the triples and relabelling the blank nodes of a policy, written as N-Triples, gives the same fact set. So does shuffling the keys and lists of a vector's input, and the reply is the same.
- **Acceptance.** Over the corpus policies, the vendored DPROD examples, the shipped modules, and the external suites:
  - the driver parses exactly the files that `tools/check_corpus.py` and `tools/check_odrl22.py` parse (both call rdflib's default parse). All three use rdflib, so this is register #3's common mode, and it is checked rather than assumed;
  - every file that parses, the driver flattens and places without error. That is a superset of what either checker accepts, so the SHACL run is not needed here;
  - no file `check_corpus.py` admits holds an unplaceable literal, so the driver can place every value due2 admits.
- **Errors.** An unknown field, a missing required field, a duplicate evidence id, and a bare-string value are each an error.

**The values** (`test_values.py`):

- **Order** (Hypothesis). A position must order exactly as its value. Over generated decimals in any lexical form, and instants in any timezone with any number of fractional digits, positions are ordered exactly as the values are. Day-time durations take their value from `timedelta`. The oracles are Python's `Decimal`, `datetime`, and `timedelta`, which share no code with `values.py`.
- **Pass-through.** 32-bit integers keep their value as their position. One wider integer or one decimal turns the space into ranks.
- **Sums.** The XSD 1.1 Part 2 Appendix E example (`2000-01-12T12:13:14Z` + `P1Y3M5DT7H10M3.3S` = `2001-04-17T19:23:17.3Z`), end-of-month clamping, a timezone near a month's end, and, by Hypothesis, day-time sums against `datetime + timedelta`.
- **Placement.** Each unplaceable reason, and lexical forms at the edges of their spaces: `24:00:00`, year zero and negative years, leap days, and the ranges of the derived integer types.

**The documentation** (`test_docs.py`, `ways-of-working.md` §15.10). The generated reference is only as complete as its doc blocks:

- every relation the program defines has exactly one `%*!` doc block, in the file that defines it;
- each block's first sentence is whole, because clindocs' predicate table cuts a block at its first full stop;
- each file header's **Consumes** and **Provides** lists match its rules, read with `clingo.ast`;
- every input fact the program reads is named in § Input facts;
- `docs/program.lp` includes the program files in the interpreter's order;
- no section reference in the spike is bare.

The corpus run is `uv run pytest --backend=clingo-i` from the repository root.
