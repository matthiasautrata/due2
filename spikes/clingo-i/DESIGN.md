# clingo-i — design

clingo-i is the semantics program of `decisions/0009`. It is a generic clingo program over flattened ODRL, and it implements the `interpret` task of `spikes/README.md` § `interpret`. Python parses the vector and flattens it to facts, and every semantic step is a rule in `lp/`. This note is for a reader who wants to know how the program reaches a reply, what each file expects and produces, and what the spike declines and why. It is the Docs step of `ways-of-working.md` §14.1. Per-relation reference lives in the generated documentation (`docs/`, below), and progress lives in issue #9 and `journal.jsonl`, not here.

## Vocabulary

The spec defines most terms: atom, part, finding, candidate, completion, and verdict (`due2-workflows.md` §3.1, §5.2, §6.1, §6.4). These are the ones the program adds, or uses in a narrower sense:

- **Driver.** `flatten.py` and `values.py`: the Python that turns a vector into facts. It is syntactic, and decides nothing.
- **Item.** Anything that carries a truth value: a part, `part(X, action)`, `part(X, target)`, or `part(X, party(F))`, or an atom's finding, `applies(X)`.
- **Truth value.** `f`, `u`, or `t`, in that order. Elsewhere "value" is qualified: a rule's *stated value* (`stated/3`), a literal's *position* in a value space (§ Values).
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
| `A`, `B` | an action; `B` is the broader one in an `includedIn` edge |
| `T` | a target |
| `F` | a function predicate (a party role, such as `odrl:assignee`) |
| `Party` | a party |
| `E` | an effect, `permit` or `forbid` |
| `C` | a conflict strategy (`prohibit`, `perm`, `invalid`), or the cross-policy combination in an elimination row |
| `I` | an item |
| `V` | a truth value |
| `N` | a rank of a truth value |
| `L` | a completion variable |
| `W` | a world |

Longer names are spelled out where they occur: `Node`, `Pred`, `Fam` (a family: action, target, or a function), `Cls`, `Iri`, `Lit` (an RDF literal), and `Vp` (the truth value of a part inside an aggregate).

## Layout

```text
main.py                the protocol loop (spikes/README.md § Protocol)
clingo_i/flatten.py    the driver: Turtle and JSON to facts; no semantics
clingo_i/values.py     the driver's value table: value spaces, positions, and instant-plus-duration sums
clingo_i/interpret.py  the three solves, the declines, and the reply
clingo_i/json_types.py the JSON value type
lp/lift.lp             triples to relations that name no IRI; detects what the spike does not read
lp/structure.lp        the policy, its conflict strategy, interiorisation, and expansion into atoms
lp/kleene.lp           truth values, and the integrity constraints over every later file
lp/applies.lp          the parts of an atom, and its finding
lp/completion.lp       the completion variables, and one completion of them per answer set
lp/resolve.lp          candidates, conflict, verdict, and basis of one world
lp/explain.lp          the eliminations, read from the findings
lp/pivot.lp            solve 3 only: a completion, its flip, and the pivotal variables
docs/                  the generated reference: program.lp includes lp/ for clindocs; python.md for mkdocstrings
tests/                 the spike's own tests (§ Tests)
```

`lift.lp` is the only file that names an IRI. Every file after it reads relations named after the spec's.

**The generated reference.** `uv run --group docs mkdocs build --strict` builds `site/` (not committed): one page per `lp/` relation, with its doc block, a predicate table, and a dependency graph (clindocs), and one page for the Python modules (mkdocstrings). It is the place to look up one relation. `tests/test_docs.py` keeps it complete (§ Tests).

## Data flow

1. **Init.** The driver parses every module once and keeps its facts.
2. **Flatten** (`flatten.py`). The policy graph becomes `triple/3`. The core modules, and the modules of each profile the policy's `odrl:profile` selects, become `module/3`. The request, SOTW, and config become facts (§ Input facts). Then `values.py` places every RDF literal in those facts (§ Values).
3. **Solve 1:** facts, `lift.lp`, and `structure.lp`. The program is stratified, so it has exactly one model. It is read in this order, and the first hit decides:
   1. any `unsupported(Feature)`: the vector is declined, naming the smallest such feature in code-point order, so the same vector always gives the same reason;
   2. any `reject(Code, Node)`: an `error` reply, because `interpret` receives only admissible policies;
   3. any `unsupported_input(Field)`: declined, naming the smallest input field;
   4. any `unsupported_value(Reason)`: declined, naming the smallest reason (§ Values).
4. **Solve 2:** every file but `pivot.lp`, in cautious mode, over the one world `c`. More than 16 `var/1` atoms after grounding declines the vector as `variable-cap` (`correctness-strategy.md` §3). No model at all is an `error`: an integrity constraint failed, so the program is wrong. Otherwise, from the atoms true in every model:
   - the verdict is the one `verdict(c, Verdict)`, or `Indeterminate` if no verdict holds in every completion;
   - `basis(c, X, Role)` gives a definite verdict's basis;
   - `elim(X, Y, C)` gives `eliminated`. It reads no world, so it is the same in every model.
5. **Solve 3**, for an `Indeterminate` only: every file, in brave mode. Each model is a completion `c`, one `pivot(L)`, and the world `flip`, such that `c` and `flip` have different verdicts. The atoms true in some model give the `unknown(X)` atoms, and every `verdict(c, Verdict)` that occurs gives the range (§ `pivot.lp`).
6. **Reply** (§ Output).

## Worked example

This is the vector of `test_worked_example` (`tests/test_interpret.py`): the default test vector of `tests/conftest.py`, with the request's target removed. The facts below are copied from a run.

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

The flatten is syntactic: one fact per triple or per input field, named after the relations of `due2-workflows.md` §3.2–§3.4. It drops nothing, and it adds only the value table (§ Values). The last column names the file that reads the fact. A fact no file reads is flattened anyway, so that a later reader finds it and the round-trip tests cover it.

**Graphs.**

| Fact | From | Read by |
|---|---|---|
| `triple/3`: `triple(S, P, O)` | each policy triple | `lift.lp` |
| `module/3`: `module(S, P, O)` | each triple of a selected module | `lift.lp` |
| `pred_ns/2`: `pred_ns(P, NS)` | each policy predicate. `NS` is `P` up to and including its last `#` or `/` | `lift.lp` |
| `selected_profile/1`: `selected_profile(Iri)` | each `odrl:profile` value that names a shipped profile | `lift.lp` |

**Request** (`due2-workflows.md` §3.2).

| Fact | From | Read by |
|---|---|---|
| `request_reference/1` | `reference`, as given | — |
| `request_action/1`: `request_action(A)` | `action` | `applies.lp` |
| `request_target/1`: `request_target(T)` | `target` | `applies.lp` |
| `request_absent/1`: `request_absent(target)` | the absence of `target` | `applies.lp` |
| `request_at/1`: `request_at(I)` | `at` | `lift.lp` |
| `request_party/2`: `request_party(F, Party)` | each entry of `parties`; `F` is the function predicate IRI | `applies.lp` |
| `request_param/2`: `request_param(N, V)` | each value of `params`, keyed by property IRI | `lift.lp` (declined) |
| `request_param_set/1`: `request_param_set(N)` | a `params` entry given as a list, so an empty set is not an absent parameter | `lift.lp` (declined) |

**SOTW** (`due2-workflows.md` §3.3).

| Fact | From | Read by |
|---|---|---|
| `sotw_effective_at/1` | `effective_at` | `lift.lp` |
| `fact/2`: `fact(P, Status)`, `fact_value/2`: `fact_value(P, V)` | each entry of `facts`. `Status` is one of `resolved`, `missing`, `invalid`, `conflict`, `unresolved` | `lift.lp` (declined) |
| `evidence/4`: `evidence(E, OccurredAt, Actor, Action)` | each `evidence` record, `E` its `id` | `lift.lp` (declined) |
| `evidence_object/2`, `evidence_issuer/2` | its optional `object` and `issuer` | — |
| `evidence_discharges/3`: `evidence_discharges(E, Duty, Reference)` | its optional `discharges` | — |
| `evidence_param/3`: `evidence_param(E, N, V)` | each of its `params` | `lift.lp` (declined) |
| `activation/2`: `activation(K, I)` | each entry of `activation`: an instance key or rule IRI, and its instant | `lift.lp` (declined) |
| `sotw_closure/3`: `sotw_closure(Rel, Narrower, Broader)` | each `closure` triple, `Rel` expanded | `lift.lp` (declined) |

**Config** (`due2-workflows.md` §3.4).

| Fact | From | Read by |
|---|---|---|
| `config_combination/1`, `config_violations/1` | `combination` (a string) and `violations` (`ignore` or `deny`) | `lift.lp` |
| `signer/2`: `signer(Duty, Issuer)` | each `signers` entry | `lift.lp` (declined) |
| `unread/1`: `unread(Field)` | `preference`, `admit_source`, `admit_age`: the case format defines no shape for them (`conformance/README.md`), so their presence is recorded and declined | `lift.lp` (declined) |

**Values** (`values.py`, § Values): `value/3`, `plus/3`, and `unplaceable/2`. Only `unplaceable/2` is read, by `lift.lp`.

A field the case format does not define, a missing required field (`action`; an evidence record's `id`, `occurred_at`, `actor`, `action`), a duplicate evidence `id`, or an unknown status is an `error`: the vector is malformed, and nothing is guessed.

**Terms.**

- **IRIs** are clingo strings.
- **RDF literals** are `lit(Lex, Datatype)`, with the lexical form exactly as written. rdflib normalises lexical forms by default, and its normalisation is lossy: it truncates fractional seconds to six digits and drops a date's timezone. The driver therefore parses with normalisation off. A plain literal is `xsd:string`. A language-tagged one is `lit(Lex, rdf:langString, Tag)`.
- **Blank nodes** are `b(Scope, Label)`. The label is rdflib's canonical one (`rdflib.compare.to_canonical_graph`), so it does not depend on the labels the parser chose. `Scope` is `"policy"` or the module's path, so blank nodes from different graphs never meet.
- **Input names** are expanded with the vector's prefixes, the same way the harness expands them. A name is a string or `{"@id": …}`. `reference` is not a name, and stays as given.
- **Input values** (`params`, `fact_value`, an evidence record's `params`) are `{"@id": …}`, read as its IRI; `{"@value": …, "@type": …}`, read as `lit` with the type expanded; `{"@value": …}`, read as `xsd:string`; or `{"@value": …, "@language": …}`. A bare string is an `error`, because it is ambiguous between a name and a string.
- **Input instants** (`at`, `effective_at`, `occurred_at`, activation instants) are `lit(I, xsd:dateTime)`.

### Values

`values.py`, under `decisions/0009` #4. clingo's integers are 32-bit, and the program compares values but never computes with them. So the driver places each RDF literal `lit(Lex, DT)` among the facts (policy, selected modules, and inputs) in a value space, and the program reads the value table, never the lexical form.

| Space | Datatypes | Value |
|---|---|---|
| `numeric` | `xsd:decimal`, `xsd:integer`, and the integer types derived from it | the exact number; `5` and `5.00` are equal |
| `instant` | `xsd:dateTime` and `xsd:dateTimeStamp` with a timezone | the point on the UTC timeline, exact to any fractional digit |
| `date` | `xsd:date` without a timezone | the day |
| `daytime` | `xsd:dayTimeDuration`, and `xsd:duration` with only day and time components | seconds, exact |
| `yearmonth` | `xsd:yearMonthDuration`, and `xsd:duration` with only year and month components | months |
| `boolean` | `xsd:boolean` | `false` before `true` |

These are the ordered spaces of `due2-profiles.md` §4: ordered within the space, and never across. Strings, tokens, IRIs, and other datatypes are compared only for equality, by their terms, so they get no entry.

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

  An unplaceable literal declines the vector only if the program compares it: `unsupported_value(Reason)` holds for `unplaceable(Lit, Reason)` with `compared(Lit)`. `compared` covers the input instants and input values, whose positions the spec fixes. The policy's own literals (right operands, deadlines) are read only by constraints and duties, which are declined first (#47, #49), so none of them is compared.

### `lift.lp`

Lifts the triples to relations that name no IRI: the vocabulary (`voc/2` maps each spec term to its IRI), `type/2`, `subclass/2`, `has_rule/3`, `stated/3` (the value a policy or rule node states for a family), `stated_conflict/2`, `profile_conflict/1`, and `closure/3` (declared `odrl:includedIn` edges). It also derives every decline (§ Declines). The function predicates are the 14 of `odrl-compound-to-atomic-normalization.md` §3, and the match keys are those of `due2-workflows.md` §5.2, of which v1 has one, `odrl:assignee`.

### `structure.lp`

Shaped like `due2-workflows.md` §3.1, under `odrl-compound-to-atomic-normalization.md` §3, §6.2, §6.3:

| Relation | `due2-workflows.md` §3.1 counterpart |
|---|---|
| `policy(P)`, `conflict(P, C)` | `policy(policy_id \| conflict, …)` |
| `atom(X)`, `atom_effect(X, E)`, `atom_policy(X, P)`, `atom_rule(X, R)`, `atom_action(X, A)`, `atom_target(X, T)` | `atom(atom_id \| effect, action, relation, relation_value, policy_id, source_rule)` |
| `atom_party(X, F, Party)` | `atom_party`, match keys only |
| `reject(Code, Node)` | a W1 rejection (`due2-diagnostics.md`) |

- **Policy.** A policy is a node typed by a policy class, or by a class that a selected module declares `rdfs:subClassOf` one. Only declared, direct edges count (`odrl-compound-to-atomic-normalization.md` §3). No policy is `reject("NoPolicy", none)`, and more than one is `reject("MultiplePolicies", P)`.
- **Conflict strategy.** The policy's own `odrl:conflict` if it states one; otherwise the selected profile's default; otherwise `invalid` (`odrl-compound-to-atomic-normalization.md` §3). Two stated values, or a value outside the three, is `reject("InvalidConflict", P)`. Two selected profiles with different defaults is `unsupported`, because the normalisation does not say which wins.
- **Interiorisation** (`odrl-compound-to-atomic-normalization.md` §6.2). For each family a root rule states nothing for, the rule takes all of the policy's values. The families are the actions, the target, and each function predicate.
- **Expansion** (`odrl-compound-to-atomic-normalization.md` §6.3). One atom for each action × target × assignee. A rule left with no action or no target is `reject("MissingAction" | "MissingTarget", R)`.
- **Atom ids.** An atom id is `a(R, A, T, Party)`: its source rule, action, target, and assignee, or the sentinel `none` for a rule with no assignee. Digests stay host-side (`decisions/0007`); the spike needs only ids that are distinct and stable.
- **Carried functions.** Function predicates that are not match keys are carried, not matched (`due2-workflows.md` §5.2). Expanding over them would only copy atoms whose findings are identical, so clingo-i does not expand over them. They are needed when a trace names a duty's bearer, and duties are declined (#49).

### `kleene.lp`

The order `f < u < t`, as `rank(V, N)`. Kleene conjunction is the truth value of least rank. The integrity constraints are here, over every later file: every item has exactly one truth value, every `u` part reads exactly one variable, every variable and every item has exactly one value in every world, and every world has exactly one verdict. A rule deleted from any file leaves some item or world without its value, so the solve has no model and the reply is an `error`, never a verdict (§ Tests).

### `applies.lp`

`due2-workflows.md` §5.2. Each atom gets its parts (`part_of(X, I)`) and a truth value for each (`holds(I, V)`):

- **action** is `t` when `request_action ⊑ atom_action` under the reflexive-transitive `includedIn` closure, and `f` otherwise. Only a request action that is the atom's action, or narrower, matches.
- **target** is `u` when `request_absent(target)` holds. Otherwise it is `t` on identity and `f` otherwise. Target collections (`odrl:partOf`) are declined.
- **party** is checked for each `atom_party(X, F, Party)` with `F` a match key. It is `u` when the request names no party for `F`, `t` when the named party is `Party`, and `f` otherwise. An atom with no assignee has no party part.
- **applies** is the Kleene conjunction of the atom's parts. The rule uses `#min` as a function: `Min = #min { N : … }` binds the least rank. Every atom has an action and a target part, so the set is never empty. If it were, `#min` would be `#sup`, no rank would match, and the integrity constraint would fail.

### `completion.lp`

`due2-workflows.md` §6.4, `decisions/0012`. A `u` target part reads the variable `target(T)`, and a `u` party part reads `party(F, Party)`. A choice gives each variable `t` or `f` in world `c`, so solve 2's answer sets are exactly the completions. In each world a `u` part takes its variable's value, every other part keeps its finding, and `applies` is re-derived from the completed parts.

**Same key, one variable.** Two parts that test the same request field against the same value are one variable (`decisions/0012` #1). The atoms that expansion copies from one rule share their target variable, and two rules for the same assignee share their party variable. Completing them separately would allow a completion in which the same question has two answers.

**Different values, different variables.** `target(ex:a)` and `target(ex:b)` are separate (`decisions/0012` #3), as in § Worked example. A request has one target, so no request realises both `t`, yet that completion is enumerated. The completion is domain-unaware: it does not know which variables exclude each other. Domain-aware completion is `due2-workflows.md` §9 open decision 6. The consequences follow from the completions being a superset of the realisable ones:

- a definite verdict holds in every completion, so it holds in every realisable one, and it is sound;
- an `Indeterminate` may be reported where every realisable completion agrees, so precision, not soundness, is what is lost;
- a range covers every realisable verdict, and may be wider.

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

**Why the cautious basis is the definite basis.** Solve 2 reports a basis row only if it holds in every completion. For a definite verdict, that is the set of atoms that determine it whatever the unknowns are. An `Indeterminate` has no such row, and its basis comes from solve 3 instead. The cautious basis of a definite verdict could be empty only if different atoms carried it in different completions. That cannot happen without constraints:

1. Every part reads its variable positively, so when every variable is `f`, only the atoms with finding `t` apply.
2. Take a `Deny`. In the all-`f` completion some `forbid` `Y` with finding `t` survives. `Y` applies in every completion. Within one policy, only a candidate removes it (`perm`, or `invalid` together with a forbid). But then no forbid of the policy survives under `perm`, and the policy is void under `invalid`, so the verdict is not `Deny`. So `Y` survives in every completion, and it is in the cautious basis.
3. Take a `Permit`. In the all-`f` completion some candidate `X` with finding `t` survives. Only a surviving `forbid` (under `prohibit`, or across policies) or a void policy (under `invalid`) removes `X`, and each of these also removes every other candidate, so the verdict would not be `Permit`. So `X` survives in every completion.

Constraints bring complementary polarities (`decisions/0012` #2), which break step 1. That argument is re-made when they are read (#47).

### `explain.lp`

`due2-workflows.md` §3.5, §6.2, `decisions/0011` #4. Elimination is read from the findings, not from a world, so `elim(X, Y, C)` carries no world and is the same in every completion. A remover `Y` has finding `t`. A removed atom `X` has finding `t` or `u`: `u` atoms eliminate nothing (`due2-workflows.md` §6.2), but they can be removed.

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
- `eliminated`: each `elim(X, Y, C)`, with `C` the conflict strategy or the combination;
- `verdict_range` `{"low", "high"}`, for an `Indeterminate` only.

Atoms are projected to their source rule, the `R` of `a(R, A, T, Party)` (`due2-workflows.md` §3.7). So the atoms of one rule are one entry. An elimination whose `ref` and `by` come from the same rule (under `invalid`, two atoms of one rule) is dropped, because at the authored level the rule would remove itself, and `invalid` says "other than itself".

## Negation as failure

`not` appears in four places, and in none of them does it turn a `u` into an `f`:

- over the closure, which is closed-world over declared edges (`due2-profiles.md` §6);
- over input syntax and what `lift.lp` and `structure.lp` derive from it: whether a family is stated, whether a predicate is consumed, whether the request names a function;
- inside one world in `resolve.lp`, where every value is already `t` or `f`;
- in `explain.lp`, over `elim` rows derived from findings (a `forbid` its own policy did not remove). A `u` finding gives no row, and the rows are only ever read as "no remover", never as a truth value.

A missing truth value has no `holds` fact. Then the integrity constraint fails, instead of the value defaulting to `f`.

## Declines

A vector is declined, never guessed at, when it uses something the spike does not read. The scorecard (`scorecard.json`) counts the declines and their reasons.

**In the policy** (`lift.lp`). A predicate `P` on node `S` is consumed when `lift.lp` reads it there:

| Predicate | Where |
|---|---|
| `rdf:type` | anywhere |
| `odrl:uid` | when it names `S` itself |
| `odrl:profile`, `odrl:conflict`, `odrl:permission`, `odrl:prohibition` | the policy |
| `odrl:action`, `odrl:target`, and the function predicates | anywhere: they are read on the policy and its rules, and elsewhere they hang under a declined link (`odrl:duty`, `odrl:refinement`) or off the policy, so declining on them would hide the feature |
| `odrl:includedIn` | anywhere |

A predicate is on the annotation allowlist when it is:

- `rdfs:label` or `rdfs:comment`;
- any `dct:` or `prov:` term;
- `skos:prefLabel`, `skos:altLabel`, `skos:hiddenLabel`, `skos:definition`, or `skos:note`;
- `dprod:offerLifecycleStatus` or `dprod:contractLifecycleStatus`, which are metadata (`due2-profiles.md` §8.1).

`unsupported(P)` holds for a predicate that is neither consumed nor allowlisted, when either:

- it is in a vocabulary namespace: `odrl:`, `due2:`, or a selected profile's IRI. Such a predicate means something, so ignoring it could change the verdict. Examples are `odrl:constraint`, `odrl:duty`, `odrl:partOf`, and `odrl:source`; or
- it sits on a structure node (the policy or one of its rules), whatever its namespace. An unknown predicate there may be a semantic extension (`odrl-compound-to-atomic-normalization.md` §3: "MUST NOT introduce additional … semantics").

Elsewhere, on asset, party, and action nodes, a predicate from another vocabulary is data the spike never reads, and it is ignored. Issue #53 adds a W1 warning for an unevaluated predicate on a structure node. The allowlist is the spike's version of that line.

**In the input** (`lift.lp`). The driver flattens every field, and `unsupported_input(Field)` names each field the program does not read:

- any fact of `request.params`, `sotw.facts`, `sotw.evidence`, `sotw.activation`, or `sotw.closure`;
- `config.combination` other than `"prohibit-overrides"`, any `config.violations`, any `config.signers`;
- each `unread(Field)` (§ Input facts).

An empty field gives no facts, so it is not declined. When several fields hold, the smallest name wins: `config.*` before `request.*` before `sotw.*`.

**In the values** (`lift.lp`). `unsupported_value(Reason)`, read after the input declines (§ Values).

**Above the cap.** More than 16 completion variables is `variable-cap` (§ Data flow).

## Errors

These are an `error` reply, not a decline:

- an unknown `odrl:profile`;
- a policy that is not admissible (`reject`);
- a malformed vector (§ Input facts);
- an unsatisfiable program.

`interpret` receives only admissible policies from well-formed vectors, so each of these is a defect, in the vector or in the spike.

## Tests

The spike's own tests (`uv run pytest` in this directory) cover what the corpus cannot see. L9 cannot see a driver bug, so the driver is tested on its own (`correctness-strategy.md` §4.1). Each item names the risk it guards.

**The program** (`test_interpret.py`), on inline Turtle and a small inline module set, not the repo's profiles:

- **Integrity.** A rule deleted from the program must not leave a verdict standing on the missing part. Deleting one rule from `kleene.lp`, `applies.lp`, `completion.lp`, or `resolve.lp` turns the reply into an error. So does an atom with two effects.
- **Explanation.** Each basis role and elimination rule on a small policy, so a wrong row cannot hide behind a right verdict. A `u` candidate removed by a `t` prohibition under `prohibit`. A `u` prohibition beside a `t` candidate under `prohibit`, which removes nothing. Two atoms of one rule share their target variable. An irrelevant `u` atom is not named `unknown`. Each range. The combination rule, on facts.
- **Worked example** (`test_worked_example`). The reply of § Worked example, so this note cannot drift from the program.
- **Brute force** (`test_brute_force.py`, Hypothesis, `correctness-strategy.md` §4.1). Over generated policies of permissions and prohibitions with absent targets and unnamed assignees, under each of the three conflict strategies, a Python oracle enumerates the completions, flips each variable alone, and derives the verdict, the basis, the eliminations, the `unknown` atoms, and the range. They must equal the reply. The oracle reads the generated rules, not the driver's facts, and shares only the spec's variable key (`due2-workflows.md` §6.4) with the program. Half the draws plant a `t` candidate beside the unknowns. Three explicit examples fix the shapes random draws rarely reach: a `u` atom whose variable changes no verdict (under `prohibit` and `invalid`), and two atoms reading one absent target. Without them, deleting the flip constraint in `pivot.lp`, or keying variables per part, survived most runs.
- **Declines.** A feature the spike does not read must decline, never be ignored. A policy with both `odrl:constraint` and `odrl:duty` declines naming `odrl:constraint`, the smaller IRI, and gives the same reason on a repeat. An unknown predicate on a rule declines. An allowlisted annotation does not. An unknown predicate on an asset node outside the vocabulary namespaces is ignored. Each input-side decline names its field, and an unplaceable input value declines naming its reason.
- **Protocol.** `main.py` answers `init` with `ready`, declaring `interpret`, and echoes the request `id`.

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
