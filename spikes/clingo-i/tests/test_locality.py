"""L11, locality (due2-workflows.md §8, decisions/0050): adding a policy changes no reply.

For every corpus vector, the generator below writes a policy `Q` that applies to nothing, since
its action is one no request names, and that states, in its own text, the hierarchy edges that
would widen the vector's policies if they could read them: the requested action `odrl:includedIn`
each action they name, and the requested target `odrl:partOf` each target they name. Those are
the two runs of decisions/0050. The vector's reply must be the same with `Q` beside its policies,
in either order, as without it. `Q`'s own rule is `f` in every world, so it adds no row to the
reply either. `Q` states no party membership; test_interpret.py's
`test_policy_reads_only_its_own_edges` and the case `due2-policy-locality` cover that.

The counterfactual: at `0928921` this test failed for 222 of the 485 vectors then in the corpus,
through three channels. The vector's rules read `Q`'s edges. `Q`'s own solve 0 met a SOTW edge
into a collection that only the vector's policies type, and declined it as untyped. Every text's
solve 0 ran without the request and the SOTW, so a duty's deadline declined as not comparable.

The shared-node variant (`test_a_shared_node_changes_no_entry`) puts beside the vector a policy
`Q` that also states one of the vector's rules, so that rule is one atom with an entry in each
policy (due2-workflows.md §3.1). `Q`'s entry may apply, so the verdict may change; what L11 fixes
is every W2 tuple that names an entry of the vector's policies. clingo-i's tuples are its world-`k`
findings: `holds/2` for every item, each keyed by its entry's policy, and `status/4` in `k`. The
vector's findings must be the same with `Q` first and last as without it, and the reply must stay
an output. `Q` keeps `leaky`'s edges, so its entry of the shared rule reads an `odrl:includedIn`
edge into the rule's action that the vector's entry must not read. The counterfactual: at
`d34d6d4`, which kept one finding per node, 30 of the 152 vectors this variant ran declined, 21
as read apart by their policies and 9 as needing a completion variable per policy. It covers 155;
the three scenarios of `due2-shared-nodes` that then declined alone were skipped.

Two more variants put a `Q` beside the vector that never links to the vector's nodes, so `Q`'s
W1, run on its text alone (due2-workflows.md §4), says nothing of them, and neither may the
corpus. The foreign-triples variant (`test_another_text_says_nothing_of_a_node`) writes, in
`Q`'s text, triples about every IRI that is a subject in the vector's texts: a label, a
`dct:isReplacedBy`, and each of the vector's triples about it again with another object. The risk is a corpus
solve that reads the union of the texts' triples, so that a stray `odrl:target` adds a target to
a rule, or a `dct:isReplacedBy` makes the vector `ReplacedPolicy`. The counterfactual: at
`05a7049`, where the corpus kept every text's triples, all 467 vectors it ran failed.

The foreign-profiles variant (`test_another_profile_describes_no_node`) runs under extra
profiles, registered for the test only (`hostile_init`), and `Q` selects them. One module gives
every predicate the vectors use the bearer and attester roles, makes every class they type a
subclass of `odrl:Set`, declares their right operands datatypes and concepts, and types their
targets and parties collections. A copy of each shipped profile the vector names includes the
same modules, and a profile is registered under each namespace of the vector's predicates that
the vector does not select. The risk is a corpus solve that reads a module without the policy
that selects it: the vocabulary that only `Q`'s profiles state would give the vector's duty a
bearer, and a module would belong to one profile only, so that the vector's policy lost it when
`Q` named the other. The vector alone, under these profiles, must give its reply too, since a
registered profile no policy names binds nothing. The counterfactual: at `05a7049`, where every
selected module's vocabulary was read by every policy and each module had one owning profile,
440 of the 467 vectors failed.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Iterator

import pytest
import rdflib
from clingo import Control, Model
from harness.corpus import Vector, init_message, interpret_vectors
from rdflib.term import Node

from clingo_i import flatten
from clingo_i.interpret import SOLVE_2, Interpreter, load_programs
from clingo_i.json_types import Obj, as_list, as_obj, as_str

ODRL = "http://www.w3.org/ns/odrl/2/"
VECTORS = interpret_vectors()
INTERPRETER = Interpreter(init_message())
Q = "urn:due2:l11:q"
# `Q`'s policy and its one rule, which applies to no request.
INERT = [
    f"@prefix odrl: <{ODRL}> .",
    f"<{Q}> a odrl:Set ; odrl:permission <urn:due2:l11:rq> .",
    "<urn:due2:l11:rq> a odrl:Permission ; odrl:action <urn:due2:l11:act> ; odrl:target"
    + " <urn:due2:l11:asset> .",
]


def parsed(vector: Vector) -> rdflib.Graph:
    """The union of the vector's policy texts."""
    graph = rdflib.Graph()
    for text in as_list(vector.input["policies"], "policies"):
        graph.parse(data=as_str(text, "policy"), format="turtle")
    return graph


def beside(vector: Vector, q: str) -> Iterator[tuple[str, Obj]]:
    """The vector's input with `q` after its policies, then before them."""
    for q_first in (False, True):
        v = copy.deepcopy(vector.input)
        texts = as_list(v["policies"], "policies")
        v["policies"] = [q, *texts] if q_first else [*texts, q]
        yield ("q first" if q_first else "q last"), v


def leaky(vector: Vector) -> str:
    """`Q` for `vector`: an inert rule, and edges from the request's entities into its policies'."""
    request = as_obj(vector.input["request"], "request")
    graph = parsed(vector)
    lines = list(INERT)
    for field, pred, edge in (("action", "action", "includedIn"), ("target", "target", "partOf")):
        if field not in request:
            continue
        asked = flatten.expand(as_str(request[field], field), vector.prefixes, field)
        named = {str(o) for o in graph.objects(None, rdflib.URIRef(ODRL + pred))}
        lines += [f"<{asked}> odrl:{edge} <{o}> ." for o in sorted(named - {asked}) if "://" in o]
    return "\n".join(lines) + "\n"


@pytest.mark.parametrize("vec", VECTORS, ids=lambda v: v.id)
def test_another_policy_changes_no_reply(vec: Vector) -> None:
    alone = INTERPRETER.reply(vec.input)
    q = leaky(vec)
    for where, v in beside(vec, q):
        assert INTERPRETER.reply(v) == alone, (where, q)


RULE_LINKS = ("permission", "prohibition", "obligation")
# The ODRL properties of a policy that its rules do not inherit. Any other, such as an action, a
# target, or a party, fills in what a rule leaves unstated (odrl-compound-to-atomic-normalization.md
# §6.2), so a text that restates only the rule describes another rule.
OWN = {rdflib.URIRef(ODRL + p) for p in (*RULE_LINKS, "profile", "conflict", "uid")}
POLICY_CLASSES = {
    rdflib.URIRef(ODRL + c)
    for c in ("Policy", "Set", "Offer", "Agreement", "Privacy", "Request", "Ticket", "Assertion")
}


def described(graph: rdflib.Graph, rule: rdflib.URIRef) -> rdflib.Graph:
    """The triples that describe `rule`: those about it and, recursively, about each node they
    name, stopping at policies."""
    out = rdflib.Graph()
    seen: set[Node] = set()
    todo: list[Node] = [rule]
    while todo:
        node = todo.pop()
        if node in seen or set(graph.objects(node, rdflib.RDF.type)) & POLICY_CLASSES:
            continue
        seen.add(node)
        for s, p, o in graph.triples((node, None, None)):
            out.add((s, p, o))
            if not isinstance(o, rdflib.Literal):
                todo.append(o)
    return out


def sharing(vector: Vector) -> str | None:
    """`Q` for `vector`, stating one of its rules as well as `leaky`'s rule and edges; None if no
    rule can be restated alike.

    A rule is restated alike only if its description has no blank node, since a blank node in
    `Q`'s text is another node, and its policy states nothing the rule inherits (`OWN`). Of
    those, a rule with a duty comes first, then one with a constraint, so that duty and
    constraint entries are shared too. `leaky`'s `odrl:partOf` edges into the shared rule's
    targets are dropped: they would make `Q`'s own entry decline (untyped collection), which is
    `Q`'s reply and no question of locality.
    """
    graph = parsed(vector)

    def order(row: tuple[rdflib.URIRef, rdflib.URIRef, str]) -> tuple[bool, bool, str]:
        def lacks(p: str) -> bool:
            return graph.value(row[0], rdflib.URIRef(ODRL + p)) is None

        return lacks("duty"), lacks("constraint"), str(row[0])

    stated = [
        (r, p, link)
        for link in RULE_LINKS
        for p, r in graph.subject_objects(rdflib.URIRef(ODRL + link))
        if isinstance(r, rdflib.URIRef) and isinstance(p, rdflib.URIRef)
    ]

    def alike(rule: rdflib.URIRef, pol: rdflib.URIRef) -> bool:
        blank = any(isinstance(n, rdflib.BNode) for t in described(graph, rule) for n in t)
        shared = {p for p in graph.predicates(pol, None) if str(p).startswith(ODRL)} - OWN
        return not blank and not shared

    chosen = next((row for row in sorted(stated, key=order) if alike(row[0], row[1])), None)
    if chosen is None:
        return None
    rule, pol, link = chosen
    triples = described(graph, rule)
    targets = {str(o) for o in triples.objects(None, rdflib.URIRef(ODRL + "target"))}
    edges = [
        line
        for line in leaky(vector).splitlines()
        if not (" odrl:partOf " in line and line.split()[-2].strip("<>") in targets)
    ]
    profiles = graph.objects(pol, rdflib.URIRef(ODRL + "profile"))
    return (
        "\n".join([*edges, f"<{Q}> odrl:{link} <{rule}> ."])
        + "".join(f"\n<{Q}> odrl:profile <{p}> ." for p in profiles)
        + "\n"
        + triples.serialize(format="nt")
    )


PROGRAMS = load_programs()


def findings(vector: Obj) -> set[str]:
    """The world-`k` findings of every entry outside `Q`: each `holds/2`, and `status/4` in `k`.

    World `k` is fixed before completion, so one model of solve 2's files has them all.
    """
    ctl = Control(["--warn=none", "--models=1"])
    ctl.add("base", [], INTERPRETER.facts(vector) + "\n" + "\n".join(PROGRAMS[f] for f in SOLVE_2))
    ctl.ground([("base", [])])
    out: set[str] = set()

    def keep(model: Model) -> None:
        for s in model.symbols(atoms=True):
            if s.match("holds", 2) or (s.match("status", 4) and s.arguments[0].match("k", 0)):
                out.add(str(s))

    assert ctl.solve(on_model=keep).satisfiable
    return {s for s in out if f'"{Q}"' not in s}


SHARING = [(v, q) for v in VECTORS if (q := sharing(v)) is not None]


@pytest.mark.parametrize(("vec", "q"), SHARING, ids=[v.id for v, _ in SHARING])
def test_a_shared_node_changes_no_entry(vec: Vector, q: str) -> None:
    if "output" not in INTERPRETER.reply(vec.input):
        pytest.skip("the vector alone has no output")
    alone = findings(vec.input)
    for where, v in beside(vec, q):
        assert "output" in INTERPRETER.reply(v), (where, q)
        assert findings(v) == alone, (where, q)


RDFS = "http://www.w3.org/2000/01/rdf-schema#"
DCT = "http://purl.org/dc/terms/"
SKOS = "http://www.w3.org/2004/02/skos/core#"
XSD = "http://www.w3.org/2001/XMLSchema#"
DUE2 = "https://w3id.org/due2/profile#"
PROFILE = rdflib.URIRef(ODRL + "profile")
INIT = init_message()
SHIPPED = as_obj(INIT["profiles"], "profiles")
# A statement of `Q`'s text: subject IRI, predicate IRI, and object in Turtle.
Row = tuple[str, str, str]


def foreign(vector: Vector) -> list[Row]:
    """`Q`'s statements about the vector's nodes, none of which `Q` links to.

    For every IRI that is the subject of a triple in the vector's texts: a label, a `dct:isReplacedBy`, and each
    triple about it again with another object. A copied `odrl:profile` names a shipped
    profile the vector does not, so that `Q` stays admissible; a blank object is not copied,
    since a blank node in `Q`'s text is another node.
    """
    graph = parsed(vector)
    unnamed = sorted(set(SHIPPED) - {str(o) for o in graph.objects(None, PROFILE)})
    rows: set[Row] = set()
    for s in {str(s) for s in graph.subjects() if isinstance(s, rdflib.URIRef)}:
        rows |= {(s, RDFS + "label", '"l11"'), (s, DCT + "isReplacedBy", "<urn:due2:l11:new>")}
        for p, o in graph.predicate_objects(rdflib.URIRef(s)):
            if p == PROFILE:
                rows |= {(s, str(p), f"<{i}>") for i in unnamed[:1]}
            elif isinstance(o, rdflib.Literal):
                rows.add((s, str(p), '"l11"'))
            elif isinstance(o, rdflib.URIRef):
                rows.add((s, str(p), "<urn:due2:l11:other>"))
    return sorted(rows)


def admissible(vector: Vector, rows: list[Row]) -> str:
    """`Q`'s text: the inert rule and `rows`, less those that make `Q` alone decline or fail.

    `Q`'s own decline or rejection is `Q`'s reply, no question of locality. Where `Q` alone
    declines a predicate, its rows go; where it is rejected at a node, the rows about the
    node go (an error names each node as `Code at Node`, `Interpreter._structure`). `odrl:source` on a node only the vector types a collection is the usual one.
    """
    while True:
        q = "\n".join([*INERT, *(f"<{s}> <{p}> {o} ." for s, p, o in rows)]) + "\n"
        v = copy.deepcopy(vector.input)
        v["policies"] = [q]
        reply = INTERPRETER.reply(v)
        if "output" in reply:
            return q
        if "unsupported" in reply:
            kept = [r for r in rows if r[1] != reply["unsupported"]]
        else:
            nodes = set(re.findall(r" at (\S+)", as_str(reply.get("error"), "error")))
            kept = [r for r in rows if r[0] not in nodes]
        assert len(kept) < len(rows), reply
        rows = kept


@pytest.mark.parametrize("vec", VECTORS, ids=lambda v: v.id)
def test_another_text_says_nothing_of_a_node(vec: Vector) -> None:
    alone = INTERPRETER.reply(vec.input)
    if "output" not in alone:
        pytest.skip("the vector alone has no output")
    q = admissible(vec, foreign(vec))
    for where, v in beside(vec, q):
        assert INTERPRETER.reply(v) == alone, (where, q)


HOST = "http://a.example/l11/"
# The predicates and classes `Q`'s own text uses, and the policy classes: a role or a superclass
# on them would change `Q`, not the vector, or make every policy of the vector a `Set`.
Q_PREDICATES = {str(rdflib.RDF.type), *(ODRL + p for p in ("permission", "action", "target"))}
Q_CLASSES = {str(c) for c in POLICY_CLASSES} | {ODRL + "Permission"}
# ODRL's party functions, the 14 of odrl-compound-to-atomic-normalization.md §3.
FUNCTIONS = {ODRL + f for f in ("assignee", "assigner")} | {
    f"{ODRL}{verb}{side}Party"
    for verb in ("attribut", "compensat", "consent", "contract", "inform", "track")
    for side in ("ed", "ing")
}


def hostile_init() -> Obj:
    """The shipped profiles, and the test's own, which speak of every vector's vocabulary.

    `l11-vocab.ttl`, under `HOST + "vocab"`, gives every predicate the vectors use (but `Q`'s and `odrl:profile`)
    the bearer and attester roles; makes every class they type (but `Q_CLASSES`) a subclass
    of `odrl:Set`; declares every IRI right operand and every non-XSD literal datatype a
    datatype, and every IRI right operand a concept of every scheme they name; and types
    every target an asset collection and every party a party collection. Each
    shipped profile has a copy under `HOST + "copy/<i>"`, with the same modules, and each
    namespace of the vectors' predicates that is no shipped profile is registered with an
    empty module.
    """
    graphs = [parsed(v) for v in VECTORS]
    triples = [t for g in graphs for t in g]
    iri = rdflib.URIRef

    def objects(pred: str) -> set[str]:
        return {str(o) for _, p, o in triples if str(p) == pred and isinstance(o, iri)}

    predicates = {str(p) for _, p, _ in triples}
    classes = {str(o) for _, p, o in triples if p == rdflib.RDF.type and isinstance(o, iri)}
    rights = objects(ODRL + "rightOperand")
    datatypes = {
        str(o.datatype)
        for _, _, o in triples
        if isinstance(o, rdflib.Literal) and o.datatype and not str(o.datatype).startswith(XSD)
    }
    parties = {str(o) for _, p, o in triples if str(p) in FUNCTIONS and isinstance(o, iri)}
    vocab = [
        *(
            f"<{p}> <{DUE2}playsRole> <{DUE2}{r}> ."
            for p in sorted(predicates - Q_PREDICATES - {str(PROFILE)})
            for r in ("bearer", "attester")
        ),
        *(f"<{c}> <{RDFS}subClassOf> <{ODRL}Set> ." for c in sorted(classes - Q_CLASSES)),
        *(f"<{d}> a <{RDFS}Datatype> ." for d in sorted(rights | datatypes)),
        *(
            f"<{r}> <{SKOS}inScheme> <{s}> ."
            for r in sorted(rights)
            for s in sorted(objects(DUE2 + "conceptScheme"))
        ),
        *(f"<{a}> a <{ODRL}AssetCollection> ." for a in sorted(objects(ODRL + "target"))),
        *(f"<{a}> a <{ODRL}PartyCollection> ." for a in sorted(parties)),
    ]
    namespaces = {flatten.namespace(p) for p in predicates} - {ODRL, DUE2, *SHIPPED}
    modules = {**as_obj(INIT["modules"], "modules")}
    modules |= {"l11-vocab.ttl": "\n".join(vocab) + "\n", "l11-empty.ttl": ""}
    profiles: Obj = {**SHIPPED, HOST + "vocab": ["l11-vocab.ttl"]}
    profiles |= {copied(i): SHIPPED[i] for i in SHIPPED}
    profiles |= {ns: ["l11-empty.ttl"] for ns in namespaces}
    return {**INIT, "modules": modules, "profiles": profiles}


def copied(profile: str) -> str:
    """The test's copy of a shipped profile."""
    return f"{HOST}copy/{sorted(SHIPPED).index(profile)}"


HOSTILE_INIT = hostile_init()
HOSTILE = Interpreter(HOSTILE_INIT)


def hostile(vector: Vector) -> str:
    """`Q` for `vector`: the inert rule, under the vocabulary profile, the copy of every profile
    the vector names, and each registered namespace of the vector's predicates it does not name."""
    graph = parsed(vector)
    named = {str(o) for o in graph.objects(None, PROFILE)}
    used = {flatten.namespace(str(p)) for p in graph.predicates()}
    registered = as_obj(HOSTILE_INIT["profiles"], "profiles")
    names = [
        HOST + "vocab",
        *(copied(i) for i in sorted(named & set(SHIPPED))),
        *sorted(n for n in used - named - set(SHIPPED) if n in registered),
    ]
    return "\n".join([*INERT, *(f"<{Q}> odrl:profile <{n}> ." for n in names)]) + "\n"


@pytest.mark.parametrize("vec", VECTORS, ids=lambda v: v.id)
def test_another_profile_describes_no_node(vec: Vector) -> None:
    alone = INTERPRETER.reply(vec.input)
    if "output" not in alone:
        pytest.skip("the vector alone has no output")
    assert HOSTILE.reply(vec.input) == alone, "a profile no policy names changed the reply"
    q = hostile(vec)
    v = copy.deepcopy(vec.input)
    v["policies"] = [q]
    assert "output" in HOSTILE.reply(v), ("q alone", q)
    for where, v in beside(vec, q):
        assert HOSTILE.reply(v) == alone, (where, q)
