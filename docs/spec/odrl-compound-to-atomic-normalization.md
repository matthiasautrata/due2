# ODRL Compound-to-Atomic Normalization

Status: Implementation-ready contract  
Version: 0.22  
Profile: `https://w3id.org/due2/odrl-normalization/v1`, version `1`  
Companion: `due2-workflows.md` — this specification is stage 1 of W1  

Changes in 0.22 (2026-10-26, `decisions/0036`, #130): §5.2 says that an anonymous node is identified by its place, so two anonymous nodes in different places are distinct, and that sharing is stated by naming. §5.1's rule that distinct resources do not claim one identity extends to the policies normalised together. Earlier changes are in `docs/archive/changes.md`.

The profile version stays `1` until an artifact has been produced under it. From then on, any change to admitted input or generated identity bumps it.

## 1. Goal

This specification defines one deterministic transformation:

```text
one valid compound ODRL Policy P0
    -> one default RDF graph N(P0) containing valid Atomic Policies
    + one separate PROV-O lineage graph
```

The normalized graph is intended to be passed as one artifact to an evaluator. The normalizer performs structural expansion, identity normalization, and lineage recording. It does not reason about, evaluate, compare, or enforce policies.

For the supported profile:

```text
Den(P0) ≅ Den(N(P0))
```

where `Den` is the denotation of §8.1 and `≅` is the bijection the lineage graph records. Every due2 evaluation depends on a Policy only through its denotation (`due2-workflows.md` §4), so this implies `Eval(P0, C) = EvalSet(N(P0), C)` for every evaluator context `C`.

`EvalSet` consumes the complete `N(P0)` artifact. It is not defined over an arbitrary union of independently normalized artifacts.

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are interpreted as in BCP 14 when written in capitals.

## 2. Normative basis

The structural authority is the ODRL 2.2 Information Model:

- [§2.1](https://www.w3.org/TR/odrl-model/#policy): a Policy has one UID and at least one Permission, Prohibition, or Obligation.
- [§2.6](https://www.w3.org/TR/odrl-model/#rule): atomic Rule cardinalities.
- [§2.6.1–2.6.2](https://www.w3.org/TR/odrl-model/#permission): Permissions and Prohibitions require a target.
- [§2.6.5](https://www.w3.org/TR/odrl-model/#duty-perm): a Duty shared by UID across Permissions is fulfilled once.
- [§2.7](https://www.w3.org/TR/odrl-model/#composition): compound Rules expand into atomic Rules.
- [§2.7.1](https://www.w3.org/TR/odrl-model/#composition-compact): compact Policy properties are replicated into Rules before atomicization.
- [§2.10](https://www.w3.org/TR/odrl-model/#conflict): `odrl:prohibit` gives Prohibitions precedence over Permissions, `odrl:perm` the reverse; absence of `odrl:conflict` defaults to `odrl:invalid`.

The W3C POE normalization notes and research in §11 are informative. They do not add inference or evaluation to this transformation.

## 3. Fixed input profile

One invocation accepts one finite RDF default graph. The entire graph is the source and identity domain; there is no configurable closure calculation. It MUST contain exactly one Policy `P0` and the complete component graph required to normalize it. Named graphs and unrelated Policies are rejected.

The invocation also receives the *selected profile modules*: the finite graphs of the profiles `P0` names with `odrl:profile`, together with due2's binding modules for them (`due2-profiles.md` §2). They are read for two things only: declared policy subclasses and a declared conflict default. They are not part of the source graph and do not enter `source_digest`. Every profile `P0` names MUST have a module. A profile without one is rejected with `UnrecognisedProfile`: due2 cannot tell what it declares, such as a conflict default that would change a verdict, and ODRL IM §3.2 requires a processor that does not recognise a profile to stop processing the policy.

A Policy node is a distinct RDF node with an explicit `rdf:type` of `odrl:Policy`, `odrl:Set`, `odrl:Offer`, or `odrl:Agreement`, or of a class that a selected profile module declares `rdfs:subClassOf` one of these — `dprod:DataContract`, for instance. Only declared edges count; no other class inference is performed. Exactly one such node MUST exist; a node with more than one of these types still counts once.

`P0` MUST:

- be valid in the supported ODRL 2.2 compact/compound fragment;
- have an identity: be an IRI node, or carry exactly one `odrl:uid` (the ODRL JSON-LD context maps `uid` to `@id`, so in RDF the IRI is usually the uid);
- have at least one `odrl:permission`, `odrl:prohibition`, or `odrl:obligation`;
- have at most one `odrl:conflict`, whose value is `odrl:prohibit`, `odrl:perm`, or `odrl:invalid`;
- not be replaced: a Policy with `dct:isReplacedBy` (`http://purl.org/dc/terms/isReplacedBy`) is void, and a processor MUST process the replacement instead (ODRL IM §2.8). This profile never dereferences an IRI, so it does not fetch the replacement: `P0` is rejected with `ReplacedPolicy`, and the policy store supplies the replacement (`due2-platform.md` §2.3). Other metadata on `P0` are annotations; and
- be fully materialized, and use none of the constructs outside the fragment: `odrl:inheritFrom`; `odrl:rightOperandReference`, whose right operand is fetched by dereferencing an IRI, an input that is neither the policy nor the request; `odrl:implies`, which action matching does not read (it reads `odrl:includedIn`, `due2-workflows.md` §5.2); `odrl:source` anywhere but on a collection (`due2-profiles.md` §8.1); `odrl:hasPolicy`, whose subject is the Asset and not the Policy (ODRL IM §2.2.3 infers the Asset as the target of every Rule of the Policy, and this profile performs no inference beyond declared edges, so an author states the Asset as `odrl:target` instead); `odrl:assignerOf` and `odrl:assigneeOf`, the same inverse form for a Party (ODRL IM §2.3.3 infers the Party as the assigner or assignee of every Rule of the Policy, so an author states it as `odrl:assigner` or `odrl:assignee` instead; ignoring the edge would drop the Party, and a Rule without its assignee matches every requester, since `due2-workflows.md` §5.2 builds a party part only for a party the atom names); and an `odrl:constraint` on `P0` itself, which the vocabulary admits (Vocabulary §3.14.2: its domain is Policy or Rule) but the IM gives no meaning: IM §2.1 lists no constraint among a Policy's properties, and IM §2.7.1 shares only actions, relations, and functions with the Rules, so §6.2 interiorises no constraint. Each is rejected with `UnsupportedConstruct`, never approximated (`due2-architecture.md` §1).

Every constraint and every Rule MUST sit where the ODRL vocabulary places it. The vocabulary fixes the subject of each property by its `rdfs:domain`, and this profile reads each property only there. A value anywhere else would be dropped or read as something it is not, so it is rejected instead:

- An `odrl:refinement` narrows an Action, an Asset Collection, or a Party Collection (IM §2.5; Vocabulary §3.14.3), and an `odrl:constraint` conditions a Rule (IM §2.5, §2.6; Vocabulary §3.14.2). A refinement on anything other than an Action or a collection, such as a Policy or a Rule, and a constraint on anything other than a Policy or a Rule, such as an Action, an Asset, a Party, or a collection, are rejected with `MisplacedConstraint`, which names the node and the property. The domain is tested, not a list of the places each may not sit, so a Party that only a profile's own role reaches, such as DPROD's `dprod:subjectOfDuty`, is covered. A refinement on an Asset or a Party is read as a collection refinement, which is rejected with `UnsupportedConstruct` (`due2-profiles.md` §8.1), and so is a constraint on the Policy itself (above). Neither is read in the other's place: a Rule's refinement read as its constraint would be an approximation.
- `odrl:permission`, `odrl:prohibition`, and `odrl:obligation` have a Policy as their subject (Vocabulary §3.9.2, §3.10.2, §3.13.2); `odrl:duty` a Permission (Vocabulary §3.13.3); `odrl:remedy` a Prohibition (Vocabulary §3.13.5); and `odrl:consequence` a Duty that `odrl:duty` or `odrl:obligation` references (Vocabulary §3.13.4; IM §2.6.3). Permission, Prohibition, and Duty are pairwise disjoint (IM §2.6; Vocabulary §3.9.1, §3.10.1, §3.13.1). A Rule edge from any other subject, and a node that its incoming Rule edges and its explicit types place in two Rule classes, are rejected with `InvalidNesting`. A Prohibition nested in a Permission, for instance, is none of `P0`'s Rules, and §6.4 builds Atomic Policies only from `P0`'s Rule edges. Admitting it would drop it, and the Permission would permit what the Prohibition forbids.

`P0` MUST also meet two requirements of the ODRL Information Model that the vocabulary's domains do not state:

- **Assets and Parties are resources.** The value of `odrl:function` is a Party and the value of `odrl:relation` an Asset (IM §2.2, §2.3, §2.6; their `rdfs:range` in `profiles/vendor/w3c/ODRL22.ttl`), and every `rdfs:subPropertyOf` descendant of either inherits that range. So the value of any of these properties is an IRI or a blank node, and a literal there is rejected with `LiteralEntity`. The descendants are read from the ODRL vocabulary, due2's core, the selected profile modules, and the source graph together. They include `odrl:target`, `odrl:output`, the function predicates listed below, and a profile's own party roles, such as DPROD's `dprod:subjectOfDuty`. A Rule whose assignee is the literal `"Bob"` names no party that a request could match, so its party part would never be `T` (`due2-workflows.md` §5.2), and its author would not be told why. A duty whose `dprod:subjectOfDuty` is the literal `"Alice"` would have a bearer that no evidence could name, since an evidence `actor` is an `Id`, an IRI (`due2-workflows.md` §2; `schema/collections.schema.json`), so no evidence could ever fulfil it.
- **Every action reaches `odrl:use` or `odrl:transfer`.** An action other than these two has exactly one `odrl:includedIn`, whose value is an `odrl:Action`, and following `odrl:includedIn` from it reaches `odrl:use` or `odrl:transfer` (IM §2.4). The edges are read from the source graph, the selected profile modules, due2's core, and the ODRL vocabulary together, so an edge the policy states adds to the vocabulary's and never replaces it: restating `odrl:display odrl:includedIn odrl:use` gives `odrl:display` a second value beside the vocabulary's `odrl:play`. An action node that states an `rdf:value` is a refined action, a blank node or an IRI alike, typed `odrl:Action` or not: its action is its `rdf:value` (IM §2.5.4), and the node itself is not an action of the hierarchy, so a skolem IRI that replaces it (§5.1) needs no `odrl:includedIn`. A blank action node without an `rdf:value` names no action and violates the requirement. The requirement covers every action a Rule names, the `rdf:value` of every refined action, every action the source graph defines other than a refined-action node, and the ancestors of each. It skips the actions the ODRL vocabulary marks `owl:deprecated`, which have no `odrl:includedIn` there, and terms that no vocabulary defines, which `UndeclaredProfile` rejects already. A violation is rejected with `InvalidActionHierarchy`. Action matching reads the `odrl:includedIn` closure (`due2-workflows.md` §5.2): without this requirement, a custom action could sit outside it, and a Prohibition of `odrl:use` would not cover it.

An absent term takes the conflict default a selected profile declares with `odrl:conflict` on its profile resource — DPROD declares `odrl:prohibit` — and otherwise means `odrl:invalid` (ODRL IM §2.10). Either way it is made explicit on every output Atomic Policy. All three values survive decomposition. `prohibit` and `perm` are pairwise precedence rules. `invalid` voids the source Policy when one of its Permissions and one of its Prohibitions both apply, and the source Policy remains identifiable: one `N(P0)` artifact derives from exactly one source Policy, and every downstream atom carries its source Policy (`due2-workflows.md` §3.1).

Anonymous structure must have a local shape:

- every blank node without an authored `odrl:uid` MUST be the object of exactly one triple, and following those triples upward MUST reach an IRI node or a node with an authored `odrl:uid` — its *anchor*. A blank node referenced twice is rejected with `SharedAnonymousNode`. One that reaches no anchor, including any cycle of blank nodes, is rejected with `UnanchoredAnonymousNode`.

Anything shared must be named. Anonymous structure is thus a forest of trees hanging from named nodes, which is what makes its identity local (§5.2).

An anonymous Asset or Party is admitted with a warning. A blank node without an authored `odrl:uid` and without an `odrl:refinement` that is an `odrl:target` or an `odrl:assignee` (the one party function a request matches, `due2-workflows.md` §5.2) gets a generated identity (§5.1, case 3). No request names that identity, and no `odrl:partOf` edge reaches it (`due2-profiles.md` §6). So the Rule's target or party part is `F` when the request names a target or an assignee, and `U` when it names none (absent is not false, `due2-workflows.md` §5.2). The Rule never applies definitely, and on a request without a target or assignee it can make the verdict `Indeterminate`. W1 warns with `AnonymousEntity`, naming the node and its Rule, also when the Rule names other targets. A refined collection is rejected instead (`UnsupportedConstruct`, #21). An author who means a collection names it and supplies its members as `odrl:partOf` edges.

Rules may be anonymous, as ODRL allows (a Rule's `uid` is optional, IM §2.6). An anonymous Rule's identity is local and content-derived like any anonymous node (§5.2): editing the Rule changes its identity and that of its atoms. A Rule whose identity must survive edits — in particular a duty that evidence names (grant scope, `due2-workflows.md` §5.3) — should be named.

The input graph MUST be self-contained for Rule references. A Rule in the graph MUST NOT depend on an undisclosed parent Policy or an external Rule that would also need transformation. IRIs are never dereferenced.

The baseline recognizes these ODRL Common Vocabulary axes:

- relation predicates: `odrl:target`, `odrl:output`;
- function predicates: `odrl:assignee`, `odrl:assigner`, `odrl:attributedParty`, `odrl:attributingParty`, `odrl:compensatedParty`, `odrl:compensatingParty`, `odrl:consentedParty`, `odrl:consentingParty`, `odrl:contractedParty`, `odrl:contractingParty`, `odrl:informedParty`, `odrl:informingParty`, `odrl:trackedParty`, and `odrl:trackingParty`.

Other predicates are preserved as annotations but MUST NOT introduce additional relation, function, inheritance, or expansion semantics. Such semantics require a future versioned profile. A Rule edge, `odrl:constraint`, or `odrl:refinement` outside the place this section gives it is not an annotation: it is rejected as above.

The invocation MUST include limits for input triples, generated Rules, and generated Policies. Exceeding a limit fails the complete invocation without partial authoritative output.

`source_digest` in §5.2 covers the entire supplied graph and identifies the input in lineage. It enters no output node identity: an edit to one part of the input changes only the identities that depend on that part (§8, invariant 10). The caller MUST still pass the intended stable Policy graph, not an ambient RDF store projection.

## 4. Output contract

The primary output is one plain default RDF graph containing a non-empty set:

```text
N(P0) = { NP_i | 0 <= i < |N(P0)| }
```

Each `NP_i` MUST:

- be a valid ODRL Policy;
- have exactly one root Permission, Prohibition, or Obligation;
- contain only atomic reachable Rules, including Duties;
- retain `P0`'s Policy class, profile, conflict term — made explicit (§3) — and non-shortcut metadata; and
- have the identity required by §5.

Shared resources are represented once and referenced by all applicable Atomic Policies. The primary graph contains no PROV-O, run metadata, membership triples, or transformer vocabulary.

The graph's file or API value is its artifact boundary. Named graphs are not used. Independently produced artifacts MUST NOT be concatenated for evaluation.

The normative serialization is canonical N-Quads: each triple in the canonical term form of RDF Dataset Canonicalization 1.0, lines sorted by Unicode code point. The output contains no blank nodes, so no blank-node labelling is involved. Presentation serializations MAY also be emitted but are not conformance artifacts.

## 5. Identity normalization

### 5.1 Effective identity and skolemization

For each Policy, Rule, Asset, Party, Constraint, or LogicalConstraint, its effective semantic identity is:

1. its authored `odrl:uid`, if present;
2. otherwise its RDF node IRI, if it is an IRI; or
3. otherwise a generated UUID from §5.2.

By §3, a Policy always takes case 1 or 2. Case 3 applies to anonymous Rules, Assets, Parties, Constraints, LogicalConstraints, refined-action nodes, and RDF list cells.

An existing valid authored UID is preserved. Distinct resources MUST NOT claim the same effective identity, within one policy or across the policies normalised together (`due2-workflows.md` §4, *Several policies are one corpus*). A resource with more than one UID is invalid.

Output is skolem-only:

- an identifiable blank node is replaced by its effective identity IRI;
- any other blank node, including an RDF list cell, is replaced by its generated UUID IRI; and
- no blank node remains in the primary output.

For an IRI node whose authored UID differs from its node IRI, the node IRI and inbound RDF edges remain unchanged; consumers use the authored UID as its semantic identity.

When one compound Rule expands into several Rules, its authored UID cannot belong to every atom. Each atom receives a generated UID. The source UID is retained as one-to-many lineage, not as an output Rule UID. Unexpanded resources retain their authored identity.

### 5.2 Deterministic UUIDs

`frame(fields...)` concatenates each field after an unsigned 64-bit big-endian byte length. Strings use UTF-8; UUIDs and digests use raw bytes. `H(x)` takes the first 128 bits of SHA-256, then sets the RFC 9562 UUID version to 8 and variant to `10`.

```text
namespace = H(frame(
  "https://w3id.org/due2/odrl-normalization/v1", "1"
))
```

**Anonymous nodes.** By §3, anonymous structure is a forest of trees hanging from named anchors. A tree has a canonical form computed bottom-up, with no blank-node labelling:

```text
term(o) = frame("iri", o)                                    if o is an IRI
        = frame("literal", canonical N-Quads term of o)      if o is a literal
        = frame("anon", local_digest(o))                     if o is an anonymous node

local_digest(n) = SHA-256(frame(sorted [ frame(p, term(o)) : (n, p, o) in the graph ]))
```

Sorting is by unsigned byte order of the framed pairs. Because the structure is a tree, the definition is well-founded, linear in the tree's size, and independent of how the input labelled its blank nodes.

```text
anon_node_uid = H(frame(
  namespace, "anon-node", parent_effective_uid, predicate_iri,
  local_digest(node), duplicate_index
))
```

`parent_effective_uid` is the effective identity of the node's single parent, assigned top-down from the anchor. `duplicate_index` numbers, from 0, the siblings that share parent, predicate, and local digest. Such siblings are indistinguishable, so any assignment of indices yields the same output graph; their descendants differ through their parents.

An anonymous node's identity therefore depends only on its own content, its parent, and the predicate that reaches it. Editing triples anywhere else — an annotation, a different Rule — leaves it unchanged. That is deliberate: an anonymous node has no name, so its place (its parent and the predicate that reaches it) and its content are all that identify it, and two anonymous nodes under different parents are distinct however alike they are. Sharing is stated by naming: a Rule, duty, or constraint that several parents or policies share, or whose identity must survive an edit to its content, should be named (§3, `due2-workflows.md` §3.1, `atom.atom_id`).

**Generated Rules, Policies, and the Activity.**

```text
atomic_rule_uid = H(frame(
  namespace, "atomic-rule", source_rule_effective_uid,
  canonical_selection_tuple
))

atomic_policy_uid = H(frame(
  namespace, "atomic-policy", source_policy_uid,
  root_role_iri, root_atomic_rule_uid
))

activity_uid = H(frame(
  namespace, "activity", source_digest
))
```

`root_role_iri` deliberately distinguishes Permission, Prohibition, and Obligation occurrences. The canonical selection tuple is the framed sequence of selected `(predicate IRI, canonical N-Quads term)` pairs in the order defined by §6.3; after skolemization every selected term is an IRI or a literal.

`source_digest` is the raw SHA-256 of the canonical N-Quads (§4) of the input graph after skolemization, and `source_ni` the corresponding RFC 6920 `ni:///sha-256;...` URI. Skolemization is deterministic and label-independent, so isomorphic inputs share a source digest. Only the Activity and the lineage depend on it.

These UUIDs are stable names with 122 retained digest bits. They are not signatures or authorization credentials.

Stage 2 and W2 build on these ids under the same `namespace`, with two further domains: `duty-atom`, a duty atom's id when stage 2 adds inherited roles or parameter values (`due2-workflows.md` §3.1), and `duty-instance`, a duty instance's key (`due2-workflows.md` §5.3).

## 6. Transformation

### 6.1 Phases

The implementation MUST run these phases in order:

1. parse, bound, and validate the fixed input profile, including the unsupported constructs, anonymous-node shape, and the conflict term (§3);
2. assign effective identities and skolemize every anonymous node (§5.2);
3. compute the source digest of the skolemized graph;
4. interiorize compact Policy properties;
5. validate post-interiorization Rule requirements, including Rule-reference acyclicity (§6.3);
6. compute exact generated-Rule and generated-Policy counts and fail any limit before materialization;
7. expand compound Rules with graph memoization;
8. create one Atomic Policy per atomic root Rule occurrence;
9. validate the output and emit canonical N-Quads; and
10. emit the separate lineage graph.

### 6.2 Compact Policy interiorization

Policy-level values fill in what a root Rule leaves unstated, and are then removed from the Policy level. They are grouped in families: the actions; the relations (`odrl:target`, `odrl:output`); and each function predicate separately. A root Rule that states any value of a family keeps its own values for that family. A root Rule that states none receives all the Policy-level values of that family, which may form a compound axis (§6.3).

ODRL IM §2.7.1 says shared properties are "replicated" into Rules but does not say what happens when a Rule already has the property. Filling only unstated families reads the Policy level as a default, which is what authors mean when they override it on one Rule — and what DPROD Contracts specifies ("inherited from policy if absent"; `due2-profiles.md` §8.1).

For this profile, the IM's “each Rule in the Policy” (§2.7.1) means each root Rule directly linked from `P0`. Nested Duties retain their own properties and do not inherit Policy-level shortcuts.

The transformer MUST record in lineage which values came from Policy-level interiorization; stage 2 needs it to resolve party roles (`due2-workflows.md` §4). Because relations form one family, a Rule that states `odrl:output` never receives a Policy-level `odrl:target`, so interiorization cannot create a Rule with both.

### 6.3 Atomic expansion

After interiorization:

- every Rule MUST have at least one Action;
- a Permission or Prohibition MUST have at least one `odrl:target` and no other relation predicate;
- a Duty MAY have no relation, one or more `odrl:target` values, or one or more `odrl:output` values, but not both predicates;
- a Consequence Duty MUST NOT have another Consequence, and a Remedy Duty MUST NOT have a Consequence (IM §2.6.3, §2.6.7; `InvalidNesting`, §3);
- the Rule-reference graph — `odrl:duty`, `odrl:consequence`, and `odrl:remedy` edges between Rules — MUST be acyclic. A cycle is rejected with `RuleReferenceCycle`, and the diagnostic MUST list every Rule and edge on one cycle, in order; and
- every atomic result has exactly one Action, at most one relation value in total, and at most one Party for each function predicate.

The ordered expansion axes are:

1. `odrl:action`;
2. the single relation predicate, if present; and
3. function predicates in ascending IRI Unicode code-point order.

Values are ordered by the Unicode code-point order of their canonical N-Quads term strings. The lexicographically ordered Cartesian product produces the atomic Rules.

Each atom generated from a compound Rule copies the source Rule class and all non-axis outgoing properties except the source `odrl:uid`. Its RDF node IRI and sole `odrl:uid` MUST both be its generated `atomic_rule_uid`; generated atoms MUST NOT share the source Rule node. Multiple Constraints, Duties, Consequences, and Remedies are retained together; they are not expansion axes.

Transform each source Rule once. Every non-root inbound reference to an expanded Rule is fanned out to its atoms. This includes `odrl:duty`, `odrl:consequence`, `odrl:remedy`, and annotation references. Root Policy edges are instead consumed when §6.4 creates Atomic Policies. Fan-out intentionally copies an inbound annotation reference to every derived atom.

An already atomic Rule retains its node and effective identity.

### 6.4 Atomic Policies

Create one `NP_i` for every atomic root Rule occurrence. It has one root edge with the same role as in `P0`, copies the permitted Policy metadata, and references the shared normalized component graph.

Retain `P0` and its authored UID only when no Rule anywhere in the input graph was expanded and the result is one Atomic Policy. Otherwise every generated Atomic Policy uses `atomic_policy_uid` as both its RDF node and sole `odrl:uid`; the source Policy UID remains in lineage. Thus expanding only a nested Duty still produces a new Policy identity even when the output cardinality is one.

## 7. Required lineage

The separate lineage graph MUST record:

- each generated Atomic Policy `prov:wasDerivedFrom` `P0`;
- each generated atomic Rule `prov:wasDerivedFrom` its source Rule;
- the selected tuple and inbound role for each generated atom;
- every IRI minted for an anonymous node, marked as generated;
- every authored, effective, and generated UID mapping;
- `activity_uid` as the generating `prov:Activity`;
- the profile IRI and version; and
- `prov:used` from the Activity to the source graph entity identified by `source_ni`.

The sidecar MUST use only PROV-O, RDF, and these profile terms under `https://w3id.org/due2/odrl-normalization/v1#`: `sourceNode`, `effectiveUid`, `generatedUid`, `selectionTuple`, `inboundRole`, `normalizationProfile`, and `profileVersion`. The Activity records the pinned profile IRI with `normalizationProfile` and the literal version `"1"` with `profileVersion`. The subject of a mapping is the normalized node. An anonymous node's parent and predicate are already in the primary graph and are not repeated.

Retained resources are recorded as retained mappings, not as self-derivations. Volatile timestamps and host information belong in an optional operational log, not the deterministic lineage graph. The lineage graph is a separate default graph, contains no blank nodes, and is serialized as canonical N-Quads (§4).

The `wasDerivedFrom` and `selectionTuple` records are not only audit data. They define the bijection under which invariant 3 is checked (§8.1); a lineage graph that does not define one is non-conforming.

## 8. Invariants

A conforming implementation establishes:

1. **Validity:** every output Policy and reachable Rule is valid under this profile, and the Rule-reference graph is acyclic.
2. **Completeness:** every Cartesian selection appears exactly once and no other atom is generated.
3. **Structural preservation:** `Den(P0) ≅ Den(N(P0))` under the bijection the lineage graph records (§8.1). Because every due2 evaluation depends on a Policy only through `Den`, this gives `Eval(P0, C) = EvalSet(N(P0), C)` for the supported fragment.
4. **Sharing:** a shared source Duty remains one shared atomic Duty or shared set of atomic Duties; fulfillment-once identity is not cloned per parent.
5. **Identity:** unexpanded resources retain authored identities; expanded resources receive deterministic identities with complete one-to-many lineage.
6. **Determinism:** isomorphic input graphs yield identical primary and lineage bytes.
7. **Idempotence:** normalizing the test extraction of an already normalized `NP_i` returns the same singleton canonical bytes.
8. **Boundedness:** limits fail before partial authoritative output.
9. **Purity:** output depends only on the supplied graph, the selected profile modules, the fixed profile, and limits; there is no I/O or ambient entailment.
10. **Locality:** an output IRI depends only on its source identity; for an anonymous node, on its own content, parent, and predicate; and for a generated Rule or Policy, on the selection that produced it. Editing triples elsewhere in the input changes no output IRI.

For invariant 7 only, `Extract(N(P0), NP_i)` is the smallest default graph obtained by starting at `NP_i`, including every triple whose subject has been reached, and recursively reaching each object IRI that is also a subject in `N(P0)`, except any Policy node other than `NP_i`. This includes the complete reachable shared component graph. Extraction is a conformance-test operation, not permission to concatenate, split, or independently deploy normalized artifacts.

### 8.1 Denotation

Invariant 3 is stated over a denotation small enough to define here, so that it can be implemented independently of §6 as a test oracle.

Let `P` be a valid input graph after skolemization (§5.2) and compact interiorization (§6.2). For a Rule `r`, let `Sel(r)` be its ordered Cartesian product of selections from §6.3 — one selection if `r` is already atomic. `Den(P)` consists of `P`'s class, profile, and conflict term, together with three sets:

- **atoms** `A`: one atom `(uid(r), σ)` for every Rule `r` reachable from `P` and every `σ ∈ Sel(r)`, carrying `r`'s class, the values `σ` selects, and `r`'s other properties except `odrl:uid` and Rule references, which `E` carries;
- **roots** `R`: `(role, (uid(r), σ))` for every root edge of `P` and every `σ ∈ Sel(r)`;
- **edges** `E`: `((uid(p), σp), role, (uid(d), σd))` for every Rule reference `p → d` with that role, and every `σp ∈ Sel(p)` and `σd ∈ Sel(d)`.

In `N(P0)` every Rule is atomic, so `Den(N(P0))` reads directly off the graph. Invariant 3 holds when the lineage records map the atoms of `Den(P0)` one-to-one onto those of `Den(N(P0))`, preserving class, selected values, non-axis properties, roots, and edges.

The definition has no memoization, no fan-out bookkeeping, and no Atomic Policy construction — the parts of §6 most likely to be wrong — which is what makes it an independent oracle. It is a pure function over a finite structure, the kind of target `ways-of-working.md` §9 names for machine-checked verification. `correctness-strategy.md` §4.8 states it again in the formal model (issue #8).

## 9. Evaluator boundary and non-goals

`N(P0)` is consumed by stage 2 of W1 (`due2-workflows.md` §4), which builds the evaluation corpus; it is not evaluated directly. The retained conflict term governs active Permissions and Prohibitions derived from the same source Policy — precedence under `prohibit` and `perm`, voiding under `invalid` — which is why every Atomic Policy carries it. Shared Duties remain shared here. Instantiating them per parameter binding is stage 2's job.

Ordering Duty alternatives belongs to W3 (`due2-workflows.md` §6.3). The normalizer does not construct, rank, or select Duty sets.

This specification does not:

- apply or preserve Policy inheritance;
- dereference IRIs, retrieve Policies, or follow external assignments;
- perform RDFS/OWL inference or ODRL action/constraint inference;
- simplify Constraints or LogicalConstraints;
- resolve conflicts, evaluate fulfillment, or enforce Policies;
- merge separately normalized artifacts;
- support blank nodes in output or named-graph packaging;
- define custom profile relation/function axes; or
- compile to an evaluator-specific representation.

## 10. Minimum conformance suite

The first implementation MUST include golden positive and negative vectors for:

- an already normalized atomic Policy returning byte-identical output;
- `2 targets x 2 actions` producing four Atomic Policies;
- compact Action and target interiorization;
- a Permission with no target failing after interiorization;
- a Duty with `odrl:output` alone succeeding;
- a Rule with both `odrl:target` and `odrl:output` failing;
- compact Policy `odrl:target` not reaching a root Duty that states `odrl:output`, and a Rule-level `odrl:assignee` overriding the Policy-level one;
- a Policy typed only by a declared profile subclass, and an absent conflict term taking a selected profile's default;
- multiple values of each recognized function predicate;
- an IRI-identified compound Rule producing distinct atom node IRIs equal to their distinct `atomic_rule_uid` values;
- a shared named Duty referenced by two Permissions, remaining one Duty;
- a compound shared Duty with an authored UID expanding once, remaining shared, and receiving one-to-many lineage;
- an atomic root Rule with a compound nested Duty producing one newly identified Atomic Policy rather than retaining `P0`'s UID;
- two structurally equal named Duties remaining distinct, and two structurally equal anonymous siblings — identical refined actions on one Rule — receiving distinct IRIs;
- obligations, Duties, Consequences, and Remedies retaining their edge roles;
- each misplacement of §3 rejected with its diagnostic: a refinement on a Policy and on a Rule, a constraint on an Action, on a collection, and on a Party that only a profile's own role names (`MisplacedConstraint`), a constraint on `P0` (`UnsupportedConstruct`), a Prohibition nested in a Permission, a Remedy on a Duty, a Consequence on a Permission, and a Consequence on a Consequence or a Remedy (`InvalidNesting`);
- authored UID conflicts;
- deterministic UUID, skolem, source digest, and lineage values across isomorphic serializations;
- rejection of a literal target and a literal party (`LiteralEntity`), of an action with no `odrl:includedIn` and of one with two (`InvalidActionHierarchy`), of a blank action node without `rdf:value` (`InvalidActionHierarchy`), and of `odrl:hasPolicy`, `odrl:assignerOf`, and `odrl:assigneeOf` (`UnsupportedConstruct`); acceptance of a refined action whose node is a blank node, an authored IRI, and a skolem IRI typed `odrl:Action`;
- acceptance of all three conflict values, and of an absent term emitted as explicit `odrl:invalid`; rejection of `odrl:inheritFrom`, named graphs, and multiple Policies;
- acceptance of an anonymous Rule with a local identity; rejection of a multiply referenced anonymous node and an unanchored anonymous node, each with its diagnostic;
- a Rule-reference cycle rejected, with every Rule and edge of the cycle in the diagnostic;
- an edit to an annotation, and an edit to one Rule, each leaving every unrelated output IRI unchanged;
- exact-limit success and over-limit failure;
- absence of provenance and transformer metadata from the primary graph; and
- a `Den` oracle (§8.1), implemented independently of §6, agreeing with every positive vector through the lineage bijection.

Property tests SHOULD permute triple order, JSON-LD order, and source blank-node labels, and SHOULD check invariant 3 against the `Den` oracle on generated Policies. A second implementation MAY serve as a differential oracle, but it must implement this same contract.

Implementation technology is replaceable:

| Approach | Acceptance condition |
|---|---|
| Direct deterministic transformer | Recommended baseline; pure bounded core and simplest replay and testing. |
| Generated code | Generator inputs and output are versioned and reproduce the same conformance bytes. |
| RDF/SPARQL or rule engine | Evaluation order, graph scope, limits, identity generation, and serialization are deterministic. |
| LLM or chat skill | May propose examples or tests, but is not an authoritative transformer unless every output is deterministically checked and canonicalized. |

A first implementation is complete when it passes this suite, emits structured diagnostics with the codes of `due2-diagnostics.md`, and exposes the deterministic transformation as a library or command-line operation. Evaluation, comparison, storage, networking, and user interfaces are separate projects.

## 11. References

- W3C, [ODRL Information Model 2.2](https://www.w3.org/TR/odrl-model/), especially §§2.1, 2.6–2.7.1, and 2.10.
- W3C, [ODRL Vocabulary & Expression 2.2](https://www.w3.org/TR/odrl-vocab/). Fixed relation and function predicate lists.
- W3C POE Working Group, [Validation and normalization notes](https://www.w3.org/2016/poe/wiki/Validation). Informative compact and compound transformation sketches.
- W3C, [RDF Dataset Canonicalization 1.0](https://www.w3.org/TR/rdf-canon/).
- W3C, [RDF 1.1 Concepts and Abstract Syntax](https://www.w3.org/TR/rdf11-concepts/), §3.5 on skolemization.
- W3C, [PROV-O](https://www.w3.org/TR/prov-o/).
- IETF, [RFC 6920: Naming Things with Hashes](https://www.rfc-editor.org/rfc/rfc6920).
- IETF, [RFC 9562: UUIDs](https://www.rfc-editor.org/rfc/rfc9562).
- Steyskal and Polleres, [Towards Formal Semantics for ODRL Policies](https://aic.ai.wu.ac.at/~polleres/publications/stey-poll-2015RuleML.pdf), RuleML 2015.
- De Vos, Kirrane, Padget, and Satoh, [ODRL Policy Modelling and Compliance Checking](https://doi.org/10.1007/978-3-030-31095-0_3), RuleML+RR 2019.
- Salas et al., [Evaluation and Comparison Semantics for ODRL](https://arxiv.org/abs/2509.05139), 2025.
- Salas, Pareti, and Konstantinidis, [ODRL Policy Comparison Through Normalisation](https://arxiv.org/abs/2603.12926), 2026.
- Salas et al., [A Formally Grounded ODRL Evaluator: Implementation and Comparison](https://arxiv.org/abs/2607.15987), 2026.
