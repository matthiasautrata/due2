# clingo-i — design

clingo-i is the semantics program of `decisions/0009`. It is a generic clingo program over flattened ODRL, and it implements the `interpret` task of `spikes/README.md` § `interpret`. Python parses the vector and flattens it to facts, and every semantic step is a rule in `lp/`. This note is for a reader who wants to know how the program reaches a reply, what each file expects and produces, and what the spike declines and why. It is the Docs step of `ways-of-working.md` §14.1. Per-relation reference lives in the generated documentation (`docs/`, below), and progress lives in issue #9 and `journal.jsonl`, not here.

## Vocabulary

The spec defines most terms: atom, part, finding, candidate, completion, and verdict (`due2-workflows.md` §3.1, §5.2, §6.1, §6.4), and left operand, binding, source, and operator (`due2-profiles.md` §2–§5). These are the ones the program adds, or uses in a narrower sense:

- **Driver.** `flatten.py` and `values.py`: the Python that turns a vector into facts. It is syntactic, and decides nothing.
- **Item.** Anything that carries a truth value: a part (`part(X, action)`, `part(X, target)`, `part(X, party(F))`, or `part(X, cons(C))`), an atom's finding (`applies(X)`), or a constraint node (`c(C)`).
- **Truth value.** `f`, `u`, or `t`, in that order. Its **rank** is 0, 1, or 2. Elsewhere "value" is qualified: a rule's *stated value* (`stated/3`), a *read value* (what a left operand reads), a *right operand value*, and a literal's *position* in a value space (§ Values).
- **Constraint node.** A node of an authored constraint tree: a *root* (a rule's `odrl:constraint` value or an action term's `odrl:refinement` value), a *leaf* (it has an `odrl:leftOperand`), or a *connective* node (`odrl:and`, `odrl:or`, `odrl:xone`, `dprod:not`). Its *members* are the nodes the connective combines.
- **Action term.** The value of `odrl:action`: an action IRI, or a node whose `rdf:value` is the action and which carries the refinements (IM 2.2 §2.5).
- **Layer.** Where a binding is declared: the policy graph, a selected profile module, or a core module (`due2-profiles.md` §2).
- **Misfit.** A comparison whose two values do not fit the operator: an IRI against a literal, or literals of two value spaces. A misfit is `u`, never `f`.
- **Completion variable.** What a `u` part reads, keyed by what the part tests: `target(T)` or `party(F, Party)` (`decisions/0012` #1). Two parts with the same key are one variable. The spec calls the variable with a polarity a *literal* (`due2-workflows.md` §6.4). Every part here reads its variable positively, so `lit_of(I, L)` names the variable `L` itself. "Literal" alone, in this note, means an RDF literal, `lit(Lex, Datatype)`.
- **Completion.** One assignment of `t` or `f` to every variable. With `n` variables there are `2^n`.
- **World.** An index that lets one answer set hold more than one completion. World `c` is the completion the answer set chose, and world `flip` (solve 3 only) is `c` with one variable negated.
- **Pivot.** The variable `flip` negates. A variable is *pivotal* when flipping it alone changes some completion's verdict (`decisions/0011` #1).
- **Remover.** In an elimination row, the atom that removes the other (`due2-workflows.md` §3.5).
- **Solve 1, 2, 3.** The three clingo runs of § Data flow. *Cautious* enumeration keeps the atoms true in every answer set, and *brave* the atoms true in some.
- **Decline.** A reply of kind `unsupported`, naming the feature the spike does not read (§ Declines). A *rejection* is a W1 diagnostic (`due2-diagnostics.md`): the policy is not admissible, and the reply is an `error`.

**Variable letters.** Every file uses one kind per letter:

| Letter | Kind |
|---|---|
| `X`, `Y` | an atom. In an elimination row, `X` is removed and `Y` removes it |
| `P`, `Q` | a policy |
| `R` | a rule |
| `A`, `B` | an action, or an action term in an atom id; `B` is the broader one in an `includedIn` edge |
| `T` | a target |
| `F` | a function predicate (a party role, such as `odrl:assignee`) |
| `Party` | a party |
| `E` | an effect, `permit` or `forbid` |
| `Strat` | a conflict strategy (`prohibit`, `perm`, `invalid`), or the cross-policy combination in an elimination row |
| `I` | an item |
| `V` | a truth value |
| `N`, `M`, `M2` | a rank of a truth value, or a position in a value space |
| `L` | a completion variable |
| `W` | a world |
| `C`, `D`, `D2` | a constraint node; `D` is a member of `C` |
| `O` | a core operator, such as `eq` or `isPartOf` |
| `Op` | a left operand |
| `Lv`, `Rv` | a read value and a right operand value |
| `Lo`, `Hi` | the narrower and the broader end of a hierarchy edge |
| `K` | a kind: of term (`iri`, `lit`, `blank`), collection or node (`asset`, `party`), connective, cardinality (`one`, `set`), or range |
| `Src` | a source kind: `request`, `state`, `context`, or `witness` |
| `Prop` | an operand property |
| `Space`, `Dt`, `Tag` | a value space, a datatype, and a language tag |
| `Rg` | a range |
| `Rel` | an order relation: `lt`, `eq`, `gt`, or `u` |

Longer names are spelled out where they occur: `Term` (an RDF term, an action term among them), `List`, `Head`, `Cell`, `Item` (of an RDF list), `Layer`, `Path`, `Key`, `Value`, `Node`, `Pred`, `Iri`, `Lit` (an RDF literal), `Cls`, `Sup`, `Mid`, `Fam` (a family: action, target, or a function), `Asked` (the request's target or party), `Prof`, and `Vp` (the truth value of a part inside an aggregate).

## Layout

```text
main.py                the protocol loop (spikes/README.md § Protocol)
clingo_i/flatten.py    the driver: Turtle and JSON to facts; no semantics
clingo_i/values.py     the driver's value table: value spaces, positions, and instant-plus-duration sums
clingo_i/interpret.py  the three solves, the declines, and the reply
clingo_i/json_types.py the JSON value type
lp/lift.lp             triples to relations that name no IRI; the hierarchies; detects what the spike does not read
lp/structure.lp        the policy, its conflict strategy, interiorisation, action terms, and expansion into atoms
lp/kleene.lp           truth values and their ranks
lp/constraint.lp       the authored constraint trees, and their static checks
lp/operand.lp          each left operand's binding, and what it reads
lp/compare.lp          the operators, and the Kleene value of every constraint node
lp/applies.lp          the parts of an atom, and its finding
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
2. **Flatten** (`flatten.py`). The policy graph becomes `triple/3`. The core modules, and the modules of each profile the policy's `odrl:profile` selects, become `module/4`, and `interpret.py` adds `layer/2` for each, naming it `core` or `profile`. The request, SOTW, and config become facts (§ Input facts). Then `values.py` places every RDF literal in those facts (§ Values).
3. **Solve 1:** facts, and `lift.lp` to `applies.lp` (the first seven files). The program has no choice rule and is stratified, so it has exactly one model. It is read in this order, and the first hit decides:
   1. any `unsupported(Feature)`: the vector is declined, naming the smallest such feature in code-point order, so the same vector always gives the same reason;
   2. any `reject(Code, Node)`: an `error` reply, because `interpret` receives only admissible policies;
   3. any `unsupported_input(Field)`: declined, naming the smallest input field;
   4. any `unsupported_value(Reason)`: declined, naming the smallest reason (§ Values);
   5. any `unsupported_part(Kind)`: declined, naming the kind (§ `applies.lp`).

   Solve 1 does not load `integrity.lp`. A decline or a rejection names what is wrong, and a failed integrity constraint would only say that something is.
4. **Solve 2:** every file but `pivot.lp`, in cautious mode, over the one world `c`. More than 16 `var/1` atoms after grounding declines the vector as `variable-cap` (`correctness-strategy.md` §3). No model at all is an `error`: an integrity constraint failed, so the program is wrong. Otherwise, from the atoms true in every model:
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
| perm | `t` (play ⊑ use) | `u` (no target) | `t` (alice) | `u` | `target(ex:a)` |
| forbid | `t` | `u` | — (no assignee) | `u` | `target(ex:b)` |

The targets differ, so the two `u` parts are two variables, and there are four completions. In each, `resolve.lp` applies the atoms whose variable is `t`, and `prohibit` removes the permission when the prohibition applies:

| `target(ex:a)` | `target(ex:b)` | applies | verdict |
|---|---|---|---|
| `t` | `t` | perm, forbid | `Deny` (perm eliminated) |
| `t` | `f` | perm | `Permit` |
| `f` | `t` | forbid | `Deny` |
| `f` | `f` | — | `NotApplicable` |

**Solve 2.** No verdict holds in all four completions, so the verdict is `Indeterminate`, and no basis row holds in all four either. Neither atom has finding `t`, so neither removes anything: `eliminated` is empty.

**Solve 3** keeps a completion and a pivot only when the flip changes the verdict. Six such pairs exist:

- pivot `target(ex:b)`, from each of the four completions. Each pair changes the verdict, for example (`t`, `t`) `Deny` to (`t`, `f`) `Permit`. Its `u` part is the forbid's, so `unknown(forbid)` holds.
- pivot `target(ex:a)`, from (`t`, `f`) and (`f`, `f`), which swap `Permit` and `NotApplicable`. From (`t`, `t`) and (`f`, `t`) the flip leaves `Deny`, so those pairs are dropped. `unknown(perm)` holds.

The verdicts `c` takes are `Deny`, `Permit`, and `NotApplicable`, so the range is `Deny` to `Permit`.

**Reply** (refs shortened to `ex:`):

```json
{"verdict": "Indeterminate", "frontier": [], "obligations": [], "exact": true,
 "verdict_basis": [{"ref": "ex:forbid", "role": "unknown"}, {"ref": "ex:perm", "role": "unknown"}],
 "eliminated": [],
 "verdict_range": {"low": "Deny", "high": "Permit"}}
```

The first completion, both targets `t`, is one no request can realise: a request has one target, and `ex:a` and `ex:b` are different. § `completion.lp` explains why it is enumerated anyway.

## Interfaces

### Input facts

The flatten is syntactic: one fact per triple or per input field, named after the relations of `due2-workflows.md` §3.2–§3.4. It drops nothing, and it adds only the value table (§ Values). The last column names the files that read the fact. A fact no file reads is flattened anyway, so that a later reader finds it and the round-trip tests cover it.

**Graphs.**

| Fact | From | Read by |
|---|---|---|
| `triple/3`: `triple(S, P, O)` | each policy triple | `lift.lp`, `structure.lp`, `constraint.lp` |
| `module/4`: `module(Path, S, P, O)` | each triple of a selected module, `Path` the module's path. Its blank nodes are scoped by `Path` | `lift.lp` |
| `layer/2`: `layer(Path, core \| profile)` | each selected module: `core` for a core module, `profile` for a module of a selected profile (`interpret.py`) | `lift.lp` |
| `pred_ns/2`: `pred_ns(P, NS)` | each policy predicate. `NS` is `P` up to and including its last `#` or `/` | `lift.lp` |
| `selected_profile/1`: `selected_profile(Iri)` | each `odrl:profile` value that names a shipped profile | `lift.lp` |

**Request** (`due2-workflows.md` §3.2).

| Fact | From | Read by |
|---|---|---|
| `request_reference/1` | `reference`, as given | — |
| `request_action/1`: `request_action(A)` | `action` | `applies.lp` |
| `request_target/1`: `request_target(T)` | `target` | `applies.lp` |
| `request_absent/1`: `request_absent(target)` | the absence of `target` | `applies.lp` |
| `request_at/1`: `request_at(I)` | `at` | `lift.lp`, `operand.lp` (`actionTime`) |
| `request_party/2`: `request_party(F, Party)` | each entry of `parties`; `F` is the function predicate IRI | `lift.lp`, `operand.lp` (`agent`), `applies.lp` |
| `request_param/2`: `request_param(Prop, Value)` | each value of `params`, keyed by property IRI | `lift.lp`, `operand.lp` |
| `request_param_set/1`: `request_param_set(Prop)` | a `params` entry given as a list, so an empty set is not an absent parameter | `operand.lp` |

**SOTW** (`due2-workflows.md` §3.3).

| Fact | From | Read by |
|---|---|---|
| `sotw_effective_at/1` | `effective_at` | `lift.lp`, `operand.lp` (`clock`) |
| `fact/2`: `fact(Prop, Status)` | each entry of `facts`. `Status` is one of `resolved`, `missing`, `invalid`, `conflict`, `unresolved` | `operand.lp` |
| `fact_value/2`: `fact_value(Prop, Value)` | each value of a `facts` entry | `lift.lp`, `operand.lp` |
| `evidence/4`: `evidence(E, OccurredAt, Actor, Action)` | each `evidence` record, `E` its `id` | `lift.lp` (declined) |
| `evidence_object/2`, `evidence_issuer/2` | its optional `object` and `issuer` | — |
| `evidence_discharges/3`: `evidence_discharges(E, Duty, Reference)` | its optional `discharges` | — |
| `evidence_param/3`: `evidence_param(E, Prop, Value)` | each of its `params` | `lift.lp` (declined) |
| `activation/2`: `activation(Key, I)` | each entry of `activation`: an instance key or rule IRI, and its instant | `lift.lp` (declined) |
| `sotw_closure/3`: `sotw_closure(Pred, Lo, Hi)` | each `closure` triple, `Pred` expanded | `lift.lp`: an edge of a hierarchy the spike reads (`closure_key/1`) joins `closure/3`; any other relation declines |

**Config** (`due2-workflows.md` §3.4).

| Fact | From | Read by |
|---|---|---|
| `config_combination/1`, `config_violations/1` | `combination` (a string) and `violations` (`ignore` or `deny`) | `lift.lp` |
| `signer/2`: `signer(Duty, Issuer)` | each `signers` entry | `lift.lp` (declined) |
| `unread/1`: `unread(Field)` | `preference`, `admit_source`, `admit_age`: the case format defines no shape for them (`conformance/README.md`), so their presence is recorded and declined | `lift.lp` (declined) |

**Values** (`values.py`, § Values): `value/3`, read by `operand.lp` and `compare.lp`; `unplaceable/2`, read by `lift.lp` and `constraint.lp`; and `plus/3`, which no file reads (relative deadlines belong to duties, #49).

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
| `plus(I, D, N)` | instant `I` plus duration `D` lies at position `N` in the `instant` space |
| `unplaceable(Lit, Reason)` | `Lit` has a datatype the driver must place, but it cannot place it |

- **Positions.** In the `numeric` space, if every value is an integer within 32 bits, `N` is the value itself. Otherwise, and in every other space, `N` is the dense rank `0..k−1` of the space's distinct values in the vector. Equal values get equal ranks. A rank means nothing across vectors; within one, `N₁ < N₂` exactly when the values are so ordered.
- **Sums.** A relative deadline is `A + duration` (`due2-workflows.md` §5.3). `plus` is given for every `instant` literal and every `daytime` or `yearmonth` literal among the facts. The sum is XSD 1.1 Part 2 Appendix E: add the months in the instant's own timezone, clamp the day to the end of the month, then add the seconds. The sums join the `instant` ranking.
- **Unplaceable values.** Nothing is truncated, rounded, or guessed. `Reason` is one of:
  - `value: xsd:double` or `value: xsd:float`: due2 has no floats (`due2-profiles.md` §4);
  - `value: dateTime without timezone`: an instant must be on the UTC timeline;
  - `value: date with timezone`: such a date is an interval, and dates in different zones overlap;
  - `value: mixed xsd:duration`: year-month and day-time components together have no single order (`due2-profiles.md` §4);
  - `value: ill-typed <datatype>`: the lexical form is not in the datatype's lexical space, or is out of its range.

  An unplaceable literal matters only if the program compares it: `unsupported_value(Reason)` holds for `unplaceable(Lit, Reason)` with `compared(Lit)`. `compared` covers the input instants, the input values, and the right operand values. A float or a mixed duration as a right operand is a rejection instead (`FloatingPointOperand`, `MixedDuration`, `constraint.lp`), because solve 1 reads `reject` before `unsupported_value`. The policy's other literals, such as deadlines, belong to duties, which are declined first (#49).

### `lift.lp`

Lifts the triples to relations that name no IRI. It provides:

- **The vocabulary.** `voc/2` maps each short name to its IRI; the registries list the conflict strategies, policy classes, the 14 function predicates of `odrl-compound-to-atomic-normalization.md` §3, the match keys (`due2-workflows.md` §5.2; v1 has one, `odrl:assignee`), the 12 core operators of `due2-profiles.md` §4 (`operator/2`, six of them `set_based/1`), the connectives (`connective/1`), the binding attributes, sources, context built-ins, and cardinalities of `due2-profiles.md` §3, and the XSD datatypes a range can name (`xsd_datatype/1`, `numeric_datatype/1`, `any_literal/1`).
- **The lifted policy.** `type/2`, `subclass/2` (declared, direct edges from the selected modules), `has_rule/3`, `stated/3` (the value a policy or rule node states for a family), `stated_conflict/2`, and `profile_conflict/1`.
- **Terms and lists.** `term/1` collects every term of the graphs and of the inputs the constraints read, and `kind/2` gives each its shape: `iri`, `lit`, or `blank`. `list_cell/2`, `list_item/2`, and `is_list/1` read RDF lists of the policy graph; `rdf:nil` is the empty list.
- **Bindings.** `decl(Layer, Op, Key, Value)` is one attribute of a binding declared in one layer: `policy` for the policy graph, or a module path. `layer_rank/2` gives the layer precedence of `due2-profiles.md` §2: the policy 0, the profile modules 1, the core modules 2.
- **The hierarchies.** `closure(Key, Lo, Hi)` holds each declared `includedIn`, `partOf`, `rdf:type`, or `rdfs:subClassOf` edge from the policy, a selected module, or the SOTW closure. The edges are closed-world: an undeclared edge does not hold (`due2-profiles.md` §6). `coll_kind/2` types a collection (`odrl:AssetCollection` is `asset`, `odrl:PartyCollection` is `party`), and `node_kind/2` also types an `odrl:Asset` or `odrl:Party`. `le_k(Lo, Hi, K)` is the typed `partOf` of `due2-profiles.md` §6: the transitive closure through collections of kind `K` only. It is not reflexive; its readers add identity.
- **The declines and the rejections of the graph** (§ Declines). A `partOf` edge into an untyped node, or one typed both ways, declines as `odrl:partOf: untyped collection`, and an edge from a node of one kind into a collection of the other as `odrl:partOf: cross-kind edge`: a cross-kind path is invalid (`due2-profiles.md` §6), and the spike has no reading it trusts for either. `odrl:source` off a collection, or `odrl:refinement` on a collection, is `reject("UnsupportedConstruct", Node)` (`due2-diagnostics.md`). On a collection, `odrl:source` is inert: the spike reads membership only from the `partOf` edges. `rdf:value` is read only on an action term, and declines anywhere else.

### `structure.lp`

Shaped like `due2-workflows.md` §3.1, under `odrl-compound-to-atomic-normalization.md` §3, §6.2, §6.3:

| Relation | `due2-workflows.md` §3.1 counterpart |
|---|---|
| `policy(P)`, `conflict(P, Strat)` | `policy(policy_id \| conflict, …)` |
| `atom(X)`, `atom_effect(X, E)`, `atom_policy(X, P)`, `atom_rule(X, R)`, `atom_action(X, A)`, `atom_target(X, T)` | `atom(atom_id \| effect, action, relation, relation_value, policy_id, source_rule)` |
| `atom_party(X, F, Party)` | `atom_party`, match keys only |
| `reject(Code, Node)` | a W1 rejection (`due2-diagnostics.md`) |

- **Policy.** A policy is a node typed by a policy class, or by a class that a selected module declares `rdfs:subClassOf` one. Only declared, direct edges count (`odrl-compound-to-atomic-normalization.md` §3). No policy is `reject("NoPolicy", none)`, and more than one is `reject("MultiplePolicies", P)`.
- **Conflict strategy.** The policy's own `odrl:conflict` if it states one; otherwise the selected profile's default; otherwise `invalid` (`odrl-compound-to-atomic-normalization.md` §3). Two stated values, or a value outside the three, is `reject("InvalidConflict", P)`. Two selected profiles with different defaults is `unsupported`, because the normalisation does not say which wins.
- **Interiorisation** (`odrl-compound-to-atomic-normalization.md` §6.2). For each family a root rule states nothing for, the rule takes all of the policy's values. The families are the actions, the target, and each function predicate.
- **Action terms.** `action_term(Term)` is each stated action. `action_of(Term, A)` is its `rdf:value` if it states one, or the term itself if it is an IRI. A blank node with no `rdf:value`, or a term with two, is declined (`action: blank node without rdf:value`, `action: several rdf:value`).
- **Expansion** (`odrl-compound-to-atomic-normalization.md` §6.3). One atom for each action term × target × assignee. A rule left with no action or no target is `reject("MissingAction" | "MissingTarget", R)`.
- **Atom ids.** An atom id is `a(R, A, T, Party)`: its source rule, action term, target, and assignee, or the sentinel `none` for a rule with no assignee. The id holds the action term, not the action, so that applies.lp can find the term's refinements; `atom_action/2` gives the action. Digests stay host-side (`decisions/0007`); the spike needs only ids that are distinct and stable.
- **Carried functions.** Function predicates that are not match keys are carried, not matched (`due2-workflows.md` §5.2). Expanding over them would only copy atoms whose findings are identical, so clingo-i does not expand over them. They are needed when a trace names a duty's bearer, and duties are declined (#49).

### `kleene.lp`

The order `f < u < t`, as `rank(V, N)`, and `two_valued/1` (`f` and `t`, the values a completed item can take). Kleene conjunction is the truth value of least rank (`#min`), disjunction that of greatest rank (`#max`), and negation maps rank `N` to `2 − N`. The integrity constraints over these values are in `integrity.lp`.

### `constraint.lp`

Reads the constraint trees the policy authored (`due2-profiles.md` §4, §5), and checks them. A rule's `odrl:constraint` values are its roots (`top_constraint/2`), and an action term's `odrl:refinement` values are its refinement roots (`top_refinement/2`). A list value gives one root per item. Each root is one conjunct of every atom of the rule or the action term (§ `applies.lp`).

- **Nodes.** `cnode(C)` is a root or a member. A node with an `odrl:leftOperand` is a `leaf(C)`, with `left(C, Op)`, `op(C, O)` (its core operator), and `right(C, Term)` (its right operand values). A node with a connective predicate is `conn(C, K)`, with `member(C, D)`. Members, like the right operand values of a set-based operator, may be one RDF list or repeated values, and both are the same set (`decisions/0013`).
- **No rewriting.** The tree is evaluated as authored. Normalisation stage 2 would rewrite it to NNF and DNF; strong Kleene logic gives a tree the value of its NNF and its DNF, so `compare.lp` computes that value on the tree itself (§ `compare.lp`), and no DNF is ever built.

**Rejections** (`due2-diagnostics.md`):

| Code | When |
|---|---|
| `MalformedConstraint` | a node that is neither a leaf nor a connective; a leaf without exactly one left operand, exactly one operator, and a right operand; several right operand values under a scalar operator; a list beside other values |
| `UnsupportedOperator` | an operator IRI outside the 12 core operators |
| `UnsupportedConnective` | `odrl:andSequence` |
| `FloatingPointOperand` | an `xsd:double` or `xsd:float` right operand |
| `MixedDuration` | an `xsd:duration` right operand with both year-month and day-time components |

`odrl:andSequence` is rejected, not read as `odrl:and`. Under frozen evaluation it would be the same as `odrl:and`, but `due2-diagnostics.md` rejects it, and the spike follows the spec.

**Declines.** A node the spec gives no reading, or only an unsettled one: a leaf that is also a connective; a node with two connectives; `dprod:not` without exactly one member; a cycle (`reach_c/2`, the transitive closure of `member/2`); an empty list as a right operand; a list as the one value of a scalar operator.

### `operand.lp`

Binds each left operand a leaf uses (`used/1`), and reads its values (`due2-profiles.md` §2, §3).

**Binding.** A layer *declares* an operand when it states its `dprod:operandSource` or its `dprod:operandProperty`. The binding is the whole declaration of the declaring layer with the least rank (`binding_layer/2`), never assembled attribute by attribute from several layers: `bdecl(Op, Key, Value)` reads every attribute from that one layer. A layer that states only a range or a cardinality does not declare the operand, and its attributes are not read. Two layers at the same rank, which can only be two selected profile modules, decline as `binding: two profile modules`: the order of `odrl:profile` values is not in the RDF, so which wins cannot be read (`due2-profiles.md` §2).

`tools/check_corpus.py` resolves bindings differently: it falls through the layers attribute by attribute. The two agree on every corpus vector, because no corpus layer declares part of a binding that another layer completes. A vector whose policy restates only the property of a core binding would separate them.

The binding gives:

- `src(Op, Src)` and `prop(Op, Prop)`, exactly one each, or `reject("UnboundLeftOperand", C)`. A source outside the four, a property that is not an IRI, or a context property that is not a built-in is `reject("InvalidBinding", C)`. The `witness` source is read only in a duty's constraints, so a rule constraint on it is `reject("WitnessOutsideDuty", C)`.
- `card(Op, K)`: `set` if the binding states `due2:set`, otherwise `one`. Another cardinality IRI, or two, declines as `binding: cardinality`.
- `range_kind(Op, K)`: `numeric` (`xsd:decimal` or a type derived from it), `datatype` (another XSD datatype or `rdf:langString`), `literal` (`rdfs:Literal`), or `class` (any other IRI). Two ranges, or one that is not an IRI, decline as `binding: range`.
- `allowed(Op, Iri)`, the `due2:allowedOperator` values. An operator outside a stated list is `reject("OperatorTypeMismatch", C)`. Without a list every core operator is allowed. `due2-profiles.md` §3 narrows that default by the operators' signatures over the range, and the spike does not check the narrowing: a leaf whose operator does not fit its range evaluates as a misfit, `u`, where W1 would reject it. `interpret` receives only admissible policies, so only a negative vector can tell.

`isA` over a set-valued operand is `reject("OperatorTypeMismatch", C)`. A set-valued operand under an operator of one left value (`single_left/1`: `eq`, `neq`, the order operators, `isAnyOf`, `isNoneOf`) has no reading in the spec, and declines as `constraint: set-valued operand on a single-value operator`.

**Range conformance** (`conforms/2`, the defaults of `due2-profiles.md` §3). Without a range, every value conforms. A `numeric` range takes a literal placed in the numeric space, so `5` and `5.00` both conform to `xsd:decimal`. A `datatype` range takes a literal of exactly that datatype. A `literal` range takes any literal, and a `class` range any IRI. A right operand value that does not conform is `reject("OperatorTypeMismatch", C)`.

**Reads.** `read_value(Op, Term)` is what the source gives, and `read_resolved(Op)` says the source answered:

| Source | Answered when | Values |
|---|---|---|
| `request` | the request has the parameter, or gives it as a list, even an empty one | the parameter's values |
| `state` | the SOTW fact has status `resolved` | the fact's values |
| `context`, `agent` | the request names an assignee | the assignee |
| `context`, `clock` | the SOTW has `effective_at` | that instant |
| `context`, `actionTime` | the request has `at` | that instant |

A fact with any other status (`missing`, `invalid`, `conflict`, `unresolved`), no fact at all, or an absent parameter or context value leaves the read unresolved. Then:

- `card_ok(Op)`: a `set` operand takes any number of values, none included; a `one` operand takes exactly one. Two or more for `one` is `MultipleValues`, and none is no value (`due2-profiles.md` §3).
- `nonconforming(Op)`: some read value is outside the range, `TypeMismatch` (`due2-profiles.md` §3).
- `read_ok(Op)` when the read is resolved, its count fits, and every value conforms; `read_u(Op)` otherwise. A `u` read makes every leaf on it `u`, never `f` (`ways-of-working.md` §5.1). `integrity.lp` checks that every used operand is exactly one of the two.

### `compare.lp`

Gives every constraint node its rank, `crank(C, N)`, and every node item its truth value, `holds(c(C), V)`.

**Leaves.** A leaf on a `u` read has rank 1. On an `ok` read, `cpair(C, Lv, Rv)` pairs each read value with each right operand value, and the pair is compared on its own:

- **Equality**, `eqr(Lv, Rv, N)`. Two IRIs by identity. Two placed literals by position, if they lie in one space. Two unplaced literals by identity, if they have the same datatype (and, for `rdf:langString`, the same tag): that is "strings by code point" (`due2-profiles.md` §4). Every other pair is a misfit, rank 1: an IRI against a literal, a blank node, two spaces, a placed against an unplaced literal, two unplaced datatypes.
- **Order**, `cmpr(Lv, Rv, Rel)`: `lt`, `eq`, or `gt` within one ordered space, and `u` otherwise. `order_rank(O, Rel, N)` reads `lt`, `lteq`, `gt`, and `gteq` off the relation, and `u` gives rank 1.
- **Hierarchies.** `isPartOf` and `hasPart` ask `Lo ⊑ Hi` (`ler/3`): two IRIs by identity or the typed `partOf` closure `le_k/3`, and anything else a misfit. `isA` asks whether the read IRI is an instance of the class (`inst/2`): one `rdf:type` edge, then `rdfs:subClassOf` edges, all from `closure/3`.

**The operators** combine the pairs (`due2-profiles.md` §4). `eq`, `neq`, and the order operators compare the one read value with the one right value; `neq` is the negation of `eq`. `any_eq(C, Rv, N)` is the disjunction, over the read values, of `= Rv`. `isAnyOf` is the greatest `any_eq` over the right values, and `isNoneOf` its negation. `isAllOf` is the least `any_eq` over the right values: every right value is read. `isPartOf` is the least, over the read values, of "part of some right value", and `hasPart` the least, over the right values, of "part of some read value"; with no read values `isPartOf` holds vacuously. `isA` is the least over the listed classes. The aggregates carry their identities (`#max { 0; … }`, `#min { 2; … }`), so an empty set has the value the operator's quantifier gives it.

**Connectives.** `and` is the least rank of its members, `or` the greatest, `dprod:not` maps rank `N` to `2 − N`, and `xone` is the disjunction of its terms `xone_term(C, D, N)`: member `D` and the negation of every other member, ⋁ᵢ (aᵢ ∧ ⋀ⱼ≠ᵢ ¬aⱼ). Strong Kleene logic gives the tree the same value as its NNF and its DNF, because De Morgan's laws, double negation, and distributivity hold in it, so these rules realise the structural rules of normalisation stage 2 without rewriting. `xone` uses its expansion, not "exactly one is `t`", so that `t xone u` is `u`, as the expansion gives, and not `t`.

**Units.** `odrl:unit` labels a right operand, and the completion key will include it (#48). It converts nothing, so a leaf compares the values alone: `5` with unit `ex:EUR` equals a read `5` (`test_unit_labels_without_converting`).

**Two datatypes, no range.** When a pair's literals lie in one space with different datatypes and the operand has no range, `due2-profiles.md` §3 does not say whether they compare by value or by identity, so the vector declines as `value: datatypes differ without a range` (#65).

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

| Request `params` | Reads | Leaves | `crank(ex:c, N)` | Reply |
|---|---|---|---|---|
| purpose `ex:marketing` | `read_ok(ex:purpose)`, `read_u(ex:count)` | `eqr(ex:marketing, ex:research, 0)` and `eqr(ex:marketing, ex:teaching, 0)`, so `any_eq` is 0 for both and `crank(ex:c1, 0)`; `crank(ex:c2, 1)` | 0 | `NotApplicable` |
| purpose `ex:research` | as above | `eqr(ex:research, ex:research, 2)`, so `crank(ex:c1, 2)`; `crank(ex:c2, 1)` | 1 | declined, `completion` |
| purpose `ex:research`, count `3` | both `ok` | `cpair(ex:c2, lit("3", xsd:integer), lit("5", xsd:integer))`, `crank(ex:c2, 2)` | 2 | `Permit` |
| purpose `ex:research`, count `7` | both `ok` | `crank(ex:c2, 0)` | 0 | `NotApplicable` |

The first row is the point of Kleene evaluation: `ex:count` is unknown, but `f ∧ u` is `f`, so the unknown does not matter, and the atom does not apply. In the second row `t ∧ u` is `u`, the constraint part is `u` and so is the atom's finding, and a `u` constraint part of a `u` atom is declined (§ `applies.lp`).

### `applies.lp`

`due2-workflows.md` §5.2. Each atom gets its parts (`part_of(X, I)`) and a truth value for each (`holds(I, V)`):

- **action** is `t` when `request_action ⊑ atom_action` under the reflexive-transitive `includedIn` closure, and `f` otherwise. Only a request action that is the atom's action, or narrower, matches.
- **target** is `u` when `request_absent(target)` holds. Otherwise it is `t` when the requested asset is the target, or part of it under the typed `partOf` closure (`le_k(Asked, T, asset)`), and `f` otherwise (`target_matches/1`).
- **party** is checked for each `atom_party(X, F, Party)` with `F` a match key. It is `u` when the request names no party for `F`, `t` when a named party is `Party` or part of it (`le_k(Asked, Party, party)`), and `f` otherwise (`party_matches/2`). An atom with no assignee has no party part.
- **constraint**, `part(X, cons(C))`, for each root `C` of `atom_constraint(X, C)`: the rule's constraint roots and the action term's refinement roots. It takes the node's value, `holds(c(C), V)`.
- **applies** is the Kleene conjunction of the atom's parts. The rule uses `#min` as a function: `Min = #min { N : … }` binds the least rank. Every atom has an action and a target part, so the set is never empty. If it were, `#min` would be `#sup`, no rank would match, and the item constraint in `integrity.lp` would fail.

**The completion decline.** A `u` constraint part of an atom whose finding is `u` gives `unsupported_part("completion")`, and solve 1 declines the vector before any enumeration. Such a part needs a completion variable keyed by the constraint's left operand, operator, right operand, and unit (`due2-workflows.md` §6.4), with a polarity, and that is #48. A `u` constraint part of an atom whose finding is `f` declines nothing: some other part is `f`, so the atom is `f` in every completion whatever the constraint is.

### `completion.lp`

`due2-workflows.md` §6.4, `decisions/0012`. `u_atom(X)` holds for an atom whose finding is `u`. Each `u` part of a `u` atom reads one variable: a target part reads `target(T)`, and a party part reads `party(F, Party)`. A `u` part of an `f` atom reads none, because the atom is `f` in every completion. After the completion decline, every `u` part of a `u` atom is a target or a party part. A choice gives each variable `t` or `f` in world `c`, so solve 2's answer sets are exactly the completions. In each world an atom that is not `u` keeps its finding; for a `u` atom, a `u` part takes its variable's value, every other part keeps its finding, and `applies` is re-derived from the completed parts. `completed_item/1` lists what must have a value in every world: every finding, and every part of a `u` atom.

**Same key, one variable.** Two parts that test the same request field against the same value are one variable (`decisions/0012` #1). The atoms that expansion copies from one rule share their target variable, and two rules for the same assignee share their party variable. Completing them separately would allow a completion in which the same question has two answers.

**Different values, different variables.** `target(ex:a)` and `target(ex:b)` are separate (`decisions/0012` #3), as in § Worked example. A request has one target, so no request realises both `t`, yet that completion is enumerated. The completion is domain-unaware: it does not know which variables exclude each other. Domain-aware completion is `due2-workflows.md` §9 open decision 6. The consequences follow from the completions being a superset of the realisable ones:

- a definite verdict holds in every completion, so it holds in every realisable one, and it is sound;
- an `Indeterminate` may be reported where every realisable completion agrees, so precision, not soundness, is what is lost;
- a range covers every realisable verdict, and may be wider.

Typed `partOf` adds a correlation the key does not see: with `ex:a1 odrl:partOf ex:a`, a requested `ex:a1` would make both `target(ex:a1)` and `target(ex:a)` `t`. The variables stay independent, so the completions remain a superset, and the three consequences above still hold.

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

**Why the cautious basis is the definite basis.** Solve 2 reports a basis row only if it holds in every completion. For a definite verdict, that is the set of atoms that determine it whatever the unknowns are. An `Indeterminate` has no such row, and its basis comes from solve 3 instead. The cautious basis of a definite verdict could be empty only if different atoms carried it in different completions. That cannot happen:

1. Every variable is read by a target or a party part of a `u` atom, positively: a `u` constraint part of a `u` atom is declined (§ `applies.lp`), and a constraint part that is `t` or `f` keeps its finding in every world. So when every variable is `f`, only the atoms with finding `t` apply.
2. Take a `Deny`. In the all-`f` completion some `forbid` `Y` with finding `t` survives. `Y` applies in every completion. Within one policy, only a candidate removes it (`perm`, or `invalid` together with a forbid). But then no forbid of the policy survives under `perm`, and the policy is void under `invalid`, so the verdict is not `Deny`. So `Y` survives in every completion, and it is in the cautious basis.
3. Take a `Permit`. In the all-`f` completion some candidate `X` with finding `t` survives. Only a surviving `forbid` (under `prohibit`, or across policies) or a void policy (under `invalid`) removes `X`, and each of these also removes every other candidate, so the verdict would not be `Permit`. So `X` survives in every completion.

Step 1 is what #48 must re-make. A constraint completion literal can be negative (`decisions/0012` #2), and then the all-`f` completion makes an atom apply whose finding is `u`.

### `integrity.lp`

The integrity constraints over every earlier file, in solves 2 and 3:

- every item has exactly one truth value, and only a ranked one;
- every used left operand is exactly one of `read_ok` and `read_u`, and every compared pair has exactly one equality rank;
- every `u` part of a `u` atom reads exactly one variable;
- in every world, every variable and every completed item has exactly one value, `f` or `t`;
- every world has exactly one verdict.

They are why a rule deleted from the program fails loudly. Without its rule, some item has no value, some read no outcome, or some world no verdict, so the solve has no model and the reply is an `error`, never a verdict standing on the missing part (§ Tests).

### `explain.lp`

`due2-workflows.md` §3.5, §6.2, `decisions/0011` #4. Elimination is read from the findings, not from a world, so `elim(X, Y, Strat)` carries no world and is the same in every completion. A remover `Y` has finding `t`. A removed atom `X` has finding `t` or `u`: `u` atoms eliminate nothing (`due2-workflows.md` §6.2), but they can be removed.

- `prohibit`: each `t` `forbid` of the policy removes each of its candidates;
- `perm`: each `t` candidate removes each of the policy's `forbid` atoms;
- `invalid`: a policy with a `t` candidate and a `t` `forbid` is void. Each of its `t` or `u` atoms is removed by each other `t` atom of the policy;
- the combination (`prohibit-overrides`, the only one read): each `t` `forbid` that its own policy did not remove removes each candidate of every other policy. `structure.lp` admits one policy, so no vector reaches this rule. It is there because `due2-workflows.md` §3.5 records cross-policy eliminations as rows (`formalisation-review.md` §3 #3), and `test_combination_rows_on_facts` runs it on hand-written facts.

**One row per remover.** An atom removed by two `forbid` atoms has two rows (`due2-workflows.md` §3.5, #57). Each row is a complete reason: whenever `X` applies, `Y` applies too, because `Y` is `t`, and `Y` removes it. A reader can check each row against the policy alone. A single row naming the first remover would hide the others, and which one is "first" would depend on the order of the facts. A `u` remover gives no row, because it removes `X` only in some completions, and that is not a reason that holds whatever the unknowns are.

The same file holds the structure's one-value constraints: every atom has exactly one `atom_effect`, `atom_policy`, and `atom_rule`, so a row names exactly one of each (`formalisation-review.md` §3 #2).

### `pivot.lp`

`decisions/0011` #1 to #3. Solve 3 only, after solve 2 has found an `Indeterminate`:

- `world(flip)`, and a choice of exactly one `pivot(L)` among the variables;
- `flip` copies `c`'s value of every variable, except the pivot, whose value it negates;
- an integrity constraint keeps only the models where `c` and `flip` have different verdicts;
- `unknown(X)` holds for an atom whose finding is `u` and which has a `u` part that reads the pivot.

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
- `verdict_range` `{"low", "high"}`, for an `Indeterminate` only.

Atoms are projected to their source rule, the `R` of `a(R, A, T, Party)` (`due2-workflows.md` §3.7). So the atoms of one rule are one entry. An elimination whose `ref` and `by` come from the same rule (under `invalid`, two atoms of one rule) is dropped, because at the authored level the rule would remove itself, and `invalid` says "other than itself".

## Negation as failure

`not` never turns a missing truth value into `f`. Each use reads something that is complete by construction:

- the declared hierarchy edges (`not action_matches`, `not target_matches`, `not party_matches`, `not le_k`, `not inst`), which are closed-world (`due2-profiles.md` §6);
- input syntax and what `lift.lp`, `structure.lp`, and `constraint.lp` derive from it: whether a family is stated, a predicate consumed, a function named, a node a list, a leaf or a connective;
- the value table and the term shapes (`not placed`, `not kind`, `not same_type`), which decide only that a pair is a misfit, and a misfit is `u`;
- the reads: `not read_resolved`, `not card_ok`, and `not conforms` make a read `u`, never `f`;
- inside one world in `resolve.lp`, where every value is already `t` or `f`;
- in `explain.lp`, over `elim` rows derived from findings (a `forbid` its own policy did not remove). A `u` finding gives no row, and the rows are only ever read as "no remover", never as a truth value.

A missing truth value has no `holds` fact. Then an integrity constraint fails, instead of the value defaulting to `f`.

## Declines

A vector is declined, never guessed at, when it uses something the spike does not read. The scorecard (`scorecard.json`) counts the declines and their reasons.

**In the policy** (`lift.lp`). A predicate `P` on node `S` is consumed when the program reads it there:

| Predicate | Where |
|---|---|
| `rdf:type` | anywhere |
| `odrl:uid` | when it names `S` itself |
| `odrl:profile`, `odrl:conflict`, `odrl:permission`, `odrl:prohibition` | the policy |
| `odrl:action`, `odrl:target`, and the function predicates | anywhere: they are read on the policy and its rules, and elsewhere they hang under a declined link (`odrl:duty`) or off the policy, so declining on them would hide the feature |
| `odrl:includedIn`, `odrl:partOf`, `odrl:source`, `odrl:leftOperand`, `odrl:operator`, `odrl:rightOperand`, `odrl:unit`, the connectives, and the binding attributes | anywhere |
| `odrl:constraint` | a rule |
| `odrl:refinement` | an action term, or a collection (where it is rejected) |
| `rdf:value` | an action term |

A predicate is on the annotation allowlist when it is:

- `rdfs:label` or `rdfs:comment`;
- any `dct:` or `prov:` term;
- `skos:prefLabel`, `skos:altLabel`, `skos:hiddenLabel`, `skos:definition`, or `skos:note`;
- `dprod:offerLifecycleStatus` or `dprod:contractLifecycleStatus`, which are metadata (`due2-profiles.md` §8.1).

`unsupported(P)` holds for a predicate that is neither consumed nor allowlisted, when either:

- it is in a vocabulary namespace: `odrl:`, `due2:`, or a selected profile's IRI. Such a predicate means something, so ignoring it could change the verdict. Examples are `odrl:duty`, `odrl:remedy`, and `odrl:constraint` on a node that is not a rule; or
- it sits on a structure node (the policy or one of its rules), whatever its namespace. An unknown predicate there may be a semantic extension (`odrl-compound-to-atomic-normalization.md` §3: "MUST NOT introduce additional … semantics").

Elsewhere, on asset, party, and action nodes, a predicate from another vocabulary is data the spike never reads, and it is ignored. Issue #53 adds a W1 warning for an unevaluated predicate on a structure node. The allowlist is the spike's version of that line. DPROD's `dprod:effectiveDate`, `dprod:expirationDate`, and `dprod:acceptsOffer` are not on it, because `due2-profiles.md` §8.1 does not list them, so a policy that states them declines (#66).

**The other policy declines**, each a fixed reason:

| Reason | File | Why |
|---|---|---|
| `action: blank node without rdf:value`, `action: several rdf:value` | `structure.lp` | the action term names no single action |
| `binding: cardinality`, `binding: range` | `operand.lp` | a cardinality or range the spike cannot read, or two of them |
| `binding: two profile modules` | `operand.lp` | two layers at one precedence |
| `constraint: cycle`, `constraint: dprod:not without one member`, `constraint: empty list`, `constraint: leaf with a connective`, `constraint: list on a scalar operator`, `constraint: two connectives` | `constraint.lp` | no reading, or none the spec settles |
| `constraint: set-valued operand on a single-value operator` | `operand.lp` | no reading in `due2-profiles.md` §4 |
| `odrl:partOf: cross-kind edge`, `odrl:partOf: untyped collection` | `lift.lp` | a hierarchy the spike does not trust |
| `profile-conflict-defaults` | `structure.lp` | two profile defaults, and no rule for which wins |

**In the input** (`lift.lp`). The driver flattens every field, and `unsupported_input(Field)` names each field the program does not read:

- any record of `sotw.evidence` or `sotw.activation`, and a `sotw.closure` edge of a relation other than `includedIn`, `partOf`, `rdf:type`, and `rdfs:subClassOf`;
- `config.combination` other than `"prohibit-overrides"`, any `config.violations`, any `config.signers`;
- each `unread(Field)` (§ Input facts).

`request.params`, `sotw.facts`, and the context values are read by `operand.lp`. An empty field gives no facts, so it is not declined. When several fields hold, the smallest name wins: `config.*` before `request.*` before `sotw.*`.

**In the values.** `unsupported_value(Reason)`, read after the input declines: an unplaceable compared literal (§ Values), or `value: datatypes differ without a range` (§ `compare.lp`, #65).

**In the parts.** `unsupported_part("completion")`, read last: a `u` constraint part of a `u` atom (§ `applies.lp`, #48).

**Above the cap.** More than 16 completion variables is `variable-cap` (§ Data flow).

## Errors

These are an `error` reply, not a decline:

- an unknown `odrl:profile`;
- a policy that is not admissible (`reject`). The codes are `NoPolicy`, `MultiplePolicies`, `InvalidConflict`, `MissingAction`, and `MissingTarget` (`structure.lp`); `UnsupportedConstruct` (`lift.lp`); `MalformedConstraint`, `UnsupportedOperator`, `UnsupportedConnective`, `FloatingPointOperand`, and `MixedDuration` (`constraint.lp`); and `UnboundLeftOperand`, `InvalidBinding`, `WitnessOutsideDuty`, and `OperatorTypeMismatch` (`operand.lp`). Each is defined in `due2-diagnostics.md`;
- a malformed vector (§ Input facts);
- an unsatisfiable program.

`interpret` receives only admissible policies from well-formed vectors, so each of these is a defect, in the vector or in the spike.

## Tests

The spike's own tests (`uv run pytest` in this directory) cover what the corpus cannot see. L9 cannot see a driver bug, so the driver is tested on its own (`correctness-strategy.md` §4.1). Each item names the risk it guards, and what got through without it.

**The program** (`test_interpret.py`), on inline Turtle and a small inline module set, not the repo's profiles:

- **Integrity.** A rule deleted from the program must not leave a verdict standing on the missing part. Deleting one rule from `kleene.lp`, `applies.lp`, `completion.lp`, or `resolve.lp` (`DELETIONS`), or the `eq` rule of `compare.lp` or the unresolved-read rule of `operand.lp` (`CONSTRAINT_DELETIONS`), turns the reply into an error, where the intact program answers. So does an atom with two effects. Each deletion's vector is chosen so that solve 1 declines nothing first: the constraint vector puts a `t` member, which the deletion does not touch, under an `or`.
- **Explanation.** Each basis role and elimination rule on a small policy, so a wrong row cannot hide behind a right verdict. A `u` candidate removed by a `t` prohibition under `prohibit`. A `u` prohibition beside a `t` candidate under `prohibit`, which removes nothing. Two atoms of one rule share their target variable. An irrelevant `u` atom is not named `unknown`. Each range. The combination rule, on facts.
- **Worked examples** (`test_worked_example`, `test_constraint_worked_example`). The replies of § Worked example and of the example in § `compare.lp`, so this note cannot drift from the program.
- **Operators** (`test_operators`, `test_hierarchy_operators`). Each operator on a value that makes it `t` and one that makes it `f`, so a rule that answers one way regardless is caught; and each misfit on a value that would be `f` under a two-valued reading: an IRI against a string, two language tags, an instant against a number. `isA` reads an `rdf:type` edge from the SOTW closure, so a closure the driver dropped would show. An empty read set is vacuously part of anything.
- **Reads** (`test_state_read`, `test_reads`). Every SOTW status but `resolved`, and no fact at all, is `u`, never `f`; so are two values and no value for a `one` operand, and a read value outside the range. The context reads the assignee and the clock.
- **Bindings** (`test_binding_layers`). Each layer wins over the ones after it, and the winning layer's declaration is read whole: with a profile binding, a request giving only the core property is `u`, not a match. Two profile modules decline.
- **Hierarchies** (`test_typed_part_of`). A requested asset in a target collection matches, and one that is not a member does not; a named party in an assignee collection matches; an untyped collection and a cross-kind edge decline.
- **Rules, refinements, and units** (`test_prohibition_constraint`, `test_refinement`, `test_unit_labels_without_converting`). A constraint on a prohibition decides a `Deny`; a refinement is a conjunct of the atom; a unit does not change a comparison.
- **Rejections and declines** (`test_constraint_rejections`, `test_constraint_declines`, `test_datatypes_differ_without_a_range`). Each code and reason of § Declines and § Errors that a constraint or a binding produces, on a minimal policy, so a check that is deleted or never fires is caught.
- **Declines.** A feature the spike does not read must decline, never be ignored. A policy with both `odrl:duty` and `odrl:remedy` declines naming `odrl:duty`, the smaller IRI, and gives the same reason on a repeat. An unknown predicate on a rule declines. An allowlisted annotation does not. An unknown predicate on an asset node outside the vocabulary namespaces is ignored. Each input-side decline names its field, and an unplaceable input value declines naming its reason.
- **Protocol.** `main.py` answers `init` with `ready`, declaring `interpret`, and echoes the request `id`.

**The brute-force differential** (`test_brute_force.py`, Hypothesis, `correctness-strategy.md` §4.1):

- **What it compares.** Over generated policies of permissions and prohibitions under each of the three conflict strategies, with absent targets and unnamed assignees, a Python oracle enumerates the completions, flips each variable alone, and derives the verdict, the basis, the eliminations, the `unknown` atoms, and the range. They must equal the reply. A rule may carry constraint trees: depth two over request parameters `ex:o0` to `ex:o2` (`ex:o2` sometimes absent), with `eq`, `neq`, and the order operators against `1`, under `and`, `or`, `xone`, and `dprod:not`, with members as a list or as repeated values. The oracle values a tree by supervaluation: it tries `t` and `f` for each leaf on an absent parameter, each leaf on its own, and the tree is `u` when the tries disagree. That is strong Kleene logic for independent leaves, computed without the program's ranks. A `u` constraint part of a `u` atom makes the oracle predict the `completion` decline. The oracle reads the generated rules, not the driver's facts, and shares only the spec's variable key (`due2-workflows.md` §6.4) with the program.
- **Examples.** Ten explicit cases fix the shapes random draws rarely reach: a `u` atom whose variable changes no verdict (under `prohibit` and `invalid`); two atoms reading one absent target; one tree per connective that changes value if the connective is misread (`and` as `or`, `or` as `and`, `dprod:not` as the identity, `xone` as `or`); a `u` leaf under an `and` and an `or` that decide anyway; and the completion decline.
- **Mutants** (`test_differential_kills_mutant`). The differential must fail against each of six programs with one rule changed: the flip constraint of `pivot.lp` deleted; one variable per part instead of per key; `u` atoms as removers; `and` and `or` swapped; `dprod:not` as the identity; `xone` without its negations. Each runs with 100 generated draws after the examples. In one measurement, generation alone first killed them after 323, 29, 15, 44, 44, and 158 draws, so the flip-constraint mutant survives without the examples, and the others survive the first draws.
- **Shapes** (`test_generator_reaches_each_shape`). Over 400 derandomized draws, the generator must reach every conflict strategy, the completion decline, an `Indeterminate` with a non-pivotal `u` atom, two `u` atoms sharing a variable, two constraint roots with the same leaf (the case #48's key must merge), and a `u` leaf under a deciding connective. A generator change that stops producing one of them would leave the differential passing on nothing; the test fails on a zero count instead.

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
