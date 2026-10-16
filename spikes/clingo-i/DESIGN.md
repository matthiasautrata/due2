# clingo-i — design

clingo-i is the semantics program of `decisions/0009`: a generic clingo program over flattened ODRL that implements the `interpret` task of `spikes/README.md`. Python parses and flattens; every semantic step is a rule in `lp/`. This file is the Docs step of `ways-of-working.md` §14.1: structure, internal interfaces (the fact schema), and what the spike declines and why. It grows with each increment of #9 (#45–#50).

Increment 1 (#45) handles policies with permissions and prohibitions over action, target, and assignee, with no constraints or duties, under the default cross-policy combination. Everything else is declined, with the feature named.

## Layout

```text
main.py               the protocol loop (spikes/README.md § Protocol)
clingo_i/flatten.py   the driver: Turtle and JSON to facts; no semantics
clingo_i/interpret.py the two solves, the declines, and the reply
clingo_i/json_types.py the JSON value type
lp/lift.lp            triples to vocabulary-free relations; detects the unsupported
lp/structure.lp       policy class, conflict default, interiorisation, expansion   normalisation §3, §6.2–§6.3
lp/kleene.lp          truth values and the one-value integrity constraints          workflows §5.1
lp/applies.lp         the parts of an atom and its finding                          workflows §5.2
lp/completion.lp      one choice per unknown part                                   workflows §6.4
lp/resolve.lp         candidates, conflict, and the verdict of one completion       workflows §6.1–§6.4
tests/                the spike's own tests (§ Tests)
```

`lift.lp` is the only file that names an IRI. Every file after it reads relations whose names are the spec's.

## Data flow

1. **Init.** The driver parses every module once and keeps its facts.
2. **Flatten** (`flatten.py`). The policy graph becomes `triple/3`. The core modules and those the policy's `odrl:profile` selects become `module/3`. The request becomes `req_*` facts.
3. **Solve 1:** facts, `lift.lp`, and `structure.lp`. The program is stratified, so it has one model. If it holds any `unsupported(P)`, the vector is declined, naming the smallest such `P` in code-point order, so the same vector always gives the same reason. A `reject(Code, Node)` is an `error` reply, because `interpret` receives only admissible policies.
4. **Input declines.** These are checked in the driver, because they are fields of the input rather than triples (§ Declines).
5. **Solve 2:** all six files, in cautious enumeration mode. More than 16 `var/1` atoms declines the vector (strategy §3). No model at all is an `error`: an integrity constraint failed, and the program is wrong. Otherwise the verdict is the one `verdict/1` atom true in every model, or `Indeterminate` if there is none.

## Fact schema

### Driver facts

| Fact | From |
|---|---|
| `triple(S, P, O)` | each policy triple |
| `module(S, P, O)` | each triple of a selected module |
| `pred_ns(P, NS)` | each policy predicate. `NS` is `P` up to and including its last `#` or `/` |
| `selected_profile(I)` | each `odrl:profile` value that names a shipped profile |
| `req_action(A)`, `req_target(T)`, `req_party(F, X)` | the request; `F` is the function predicate IRI |
| `req_absent(target)` | the request names no target |

How terms are written:

- **IRIs** are clingo strings.
- **Literals** are `lit(Lex, Datatype)`. A plain literal is `xsd:string`. A language-tagged one is `rdf:langString`, without its tag: no reading looks at it yet.
- **Blank nodes** are `b(Scope, Label)`. The label is rdflib's canonical one (`rdflib.compare.to_canonical_graph`), so it does not depend on the labels the parser chose. `Scope` is `"policy"` or the module's path, so blank nodes from different graphs never meet.
- **Request names** are expanded with the vector's prefixes, the same way the harness expands them. A `{"@id": …}` value is read as its IRI.

The driver does not read `at`, `reference`, or `effective_at`. Nothing in this increment depends on them.

### Lifted relations (`lift.lp`)

| Relation | Meaning |
|---|---|
| `type(N, C)` | `rdf:type` in the policy graph |
| `subclass(C, D)` | `rdfs:subClassOf` in the selected modules |
| `policy_class(C)` | `odrl:Policy`, `odrl:Set`, `odrl:Offer`, or `odrl:Agreement` |
| `has_rule(P, R, Effect)` | `odrl:permission` (`permit`) or `odrl:prohibition` (`forbid`) |
| `stated(N, Family, V)` | the value `V` that a policy or rule node `N` states for a family: `action`, `target`, or a function predicate IRI |
| `function(F)`, `match_key(F)` | the 14 function predicates of normalisation §3; the match keys of workflows §5.2 (v1: `odrl:assignee`) |
| `stated_conflict(P, C)` | `odrl:conflict` on the policy, `C` one of `prohibit`, `perm`, `invalid` |
| `profile_conflict(C)` | `odrl:conflict` on a selected profile resource (`due2-profiles.md` §8.1) |
| `closure(Rel, Narrower, Broader)` | `odrl:includedIn` edges from the policy and the modules, `Rel = includedIn` |
| `unsupported(P)` | a predicate the spike does not read (§ Declines) |

### Structure (`structure.lp`), shaped like workflows §3.1

| Relation | §3.1 counterpart |
|---|---|
| `policy(P)`, `conflict(P, C)` | `policy(policy_id \| conflict, …)` |
| `atom(X)`, `atom_effect(X, E)`, `atom_policy(X, P)`, `atom_rule(X, R)`, `atom_action(X, A)`, `atom_target(X, T)` | `atom(atom_id \| effect, action, relation, relation_value, policy_id, source_rule)` |
| `atom_party(X, F, Party)` | `atom_party`, match keys only (below) |
| `closure(Rel, N, B)` | `closure` |
| `reject(Code, Node)` | a W1 rejection (`due2-diagnostics.md`) |

- **Atom ids.** An atom id is `a(R, A, T, Y)`: its source rule, action, target, and assignee, or `none` if it has no assignee. Digests stay host-side (`decisions/0007`). The spike needs only distinct, stable ids.
- **Carried functions.** Function predicates that are not match keys are carried, not matched (§5.2). Expanding over them would only copy atoms whose findings are identical, so clingo-i does not expand over them. They return when the trace needs a duty's bearer (#49).

### Findings (`kleene.lp`, `applies.lp`, `completion.lp`)

Every truth value is a `holds(I, V)` with `V` in `f`, `u`, `t`, over the items:

- `part(X, action)` and `part(X, target)`;
- `part(X, party(F))` for a match key `F`;
- `applies(X)`.

`item(I)` declares each item that must have a value. A completion gives every item `I` exactly one `cval(I, V)`, with `V` either `f` or `t`.

## Semantics, by file

### `structure.lp`

- **Policy.** A policy is a node typed by a policy class, or by a class that a selected module declares `rdfs:subClassOf` one. Only declared, direct edges count (normalisation §3). No policy is `reject("NoPolicy", none)`, and more than one is `reject("MultiplePolicies", P)`.
- **Conflict.** The conflict strategy is the policy's own `odrl:conflict` if it states one; otherwise the selected profile's default; otherwise `invalid` (normalisation §3). Two stated values, or a value outside the three, is `reject("InvalidConflict", P)`. Two selected profiles with different defaults is `unsupported`: normalisation §3 does not say which wins.
- **Interiorisation** (§6.2). For each family a root rule states nothing for, the rule takes all of the policy's values. The families are the actions, the target, and each function predicate.
- **Expansion** (§6.3). One atom for each action × target × assignee. A rule left with no action or no target is `reject("MissingAction" | "MissingTarget", R)`.

### `kleene.lp`

- The order `f < u < t`, as `rank(V, N)`. Kleene conjunction is `#min` over ranks.
- Integrity: every item has exactly one value, and so does every completed item. Every completion has exactly one verdict. A rule deleted from any file breaks one of these, so the solve fails loudly instead of answering.

### `applies.lp` (workflows §5.2)

- **action** is `t` when `req_action ⊑ atom_action` under the reflexive-transitive `includedIn` closure, and `f` otherwise. Only a narrower request matches.
- **target** is `u` when `req_absent(target)` holds. Otherwise it is `t` on identity and `f` otherwise. Target collections (`odrl:partOf`) are declined for now.
- **party** is checked for each `atom_party(X, F, P)` with `F` a match key. It is `u` when the request names no `F`, `t` when the named party is `P`, and `f` otherwise. A rule with no assignee has no party part.
- **applies** is the `#min` of the atom's parts.

### `completion.lp` (workflows §6.4)

- Each part with value `u` is a variable `var(I)`. A choice gives it `t` or `f`. Every other item completes to its own value, and `applies` is re-derived from the completed parts.
- **Literal key.** §6.4 says "each `U` part is a variable", with one exception: correlated constraint parts share one. That key lands with constraints. Until then, two relation or party parts on the same value are separate variables, exactly as the spec defines.

### `resolve.lp` (workflows §6.1–§6.4)

Within one completion, every value is `t` or `f`:

- A candidate is a `permit` atom that applies. There are no duties yet, so every candidate is ready.
- **Conflict within the policy** (§6.2.1):
  - `prohibit`: an applying `forbid` eliminates the policy's candidates.
  - `perm`: an applying candidate eliminates the policy's `forbid` atoms.
  - `invalid`: an applying candidate and an applying `forbid` together eliminate everything in the policy.
- **Across policies** (§6.2.2): a surviving applying `forbid` eliminates every candidate (prohibit-overrides).
- **Verdict**, per the §6.4 table:
  - `Deny` if a `forbid` survives;
  - otherwise `Permit` if a candidate survives;
  - otherwise `NotApplicable`.

  `Pending` needs duties (#49).

The output is `verdict`, `frontier: []`, `obligations: []`, and `exact: true`. Enumerating every completion is the definition itself, so it is exact.

## Negation as failure

`not` appears in three places:

- over the closure, which is closed-world over declared edges (`due2-profiles.md` §6);
- over input syntax and what `lift.lp` and `structure.lp` derive from it: whether a family is stated, whether a predicate is consumed, whether the request names a function;
- inside one completion in `resolve.lp`, where every value is already `t` or `f`.

It never turns a `u` into an `f`. A missing value has no `holds` fact, so the integrity constraint fails, instead of the value defaulting.

## Declines

A vector is declined, never guessed at, when it uses something this increment does not read.

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
- it sits on a structure node (the policy or one of its rules), whatever its namespace. An unknown predicate there may be a semantic extension (normalisation §3: "MUST NOT introduce additional … semantics").

Elsewhere, on asset, party, and action nodes, a predicate from another vocabulary is data the spike never reads, and it is ignored. Issue #53 adds a W1 warning for an unevaluated predicate on a structure node. The allowlist is the spike's version of that line.

**In the input** (`interpret.py`). Each of these is declined, named by its field:

- a non-empty `sotw.facts`, `sotw.evidence`, `sotw.activation`, `sotw.closure`, or `request.params`;
- any `config` other than `{"combination": "prohibit-overrides"}`.

Each later increment of #9 removes declines. The scorecard's unsupported count, and its reasons, show what is left.

**Errors.** These are an `error` reply, not a decline:

- an unknown `odrl:profile`;
- a policy that is not admissible (`reject`);
- an unsatisfiable program.

`interpret` receives only admissible policies, so each of these is a defect: in the vector or in the spike.

## Tests

The spike's own tests (`uv run pytest` in this directory) cover what the corpus cannot see. They use inline Turtle and a small inline module set, not the repo's profiles:

- **Integrity.** Deleting one rule from `kleene.lp`, `applies.lp`, or `resolve.lp` turns the reply into an error, not a verdict.
- **Declines.** A policy with both `odrl:constraint` and `odrl:duty` declines naming `odrl:constraint`, the smaller IRI, and gives the same reason on a repeat. An unknown predicate on a rule declines. An allowlisted annotation does not. An unknown predicate on an asset node outside the vocabulary namespaces is ignored. Each input-side decline names its field.
- **Protocol.** `main.py` answers `init` with `ready`, declaring `interpret`, and echoes the request `id`.

The corpus run is `uv run pytest --backend=clingo-i` from the repository root.
