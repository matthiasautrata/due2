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
"""

from __future__ import annotations

import copy

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


def leaky(vector: Vector) -> str:
    """`Q` for `vector`: an inert rule, and edges from the request's entities into its policies'."""
    request = as_obj(vector.input["request"], "request")
    graph = rdflib.Graph()
    for text in as_list(vector.input["policies"], "policies"):
        graph.parse(data=as_str(text, "policy"), format="turtle")
    lines = [
        f"@prefix odrl: <{ODRL}> .",
        f"<{Q}> a odrl:Set ; odrl:permission <urn:due2:l11:rq> .",
        "<urn:due2:l11:rq> a odrl:Permission ; odrl:action <urn:due2:l11:act> ; odrl:target"
        + " <urn:due2:l11:asset> .",
    ]
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
    for q_first in (False, True):
        v = copy.deepcopy(vec.input)
        texts = as_list(v["policies"], "policies")
        v["policies"] = [q, *texts] if q_first else [*texts, q]
        assert INTERPRETER.reply(v) == alone, ("q first" if q_first else "q last", q)


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
    graph = rdflib.Graph()
    for text in as_list(vector.input["policies"], "policies"):
        graph.parse(data=as_str(text, "policy"), format="turtle")

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
    for q_first in (False, True):
        v = copy.deepcopy(vec.input)
        texts = as_list(v["policies"], "policies")
        v["policies"] = [q, *texts] if q_first else [*texts, q]
        where = ("q first" if q_first else "q last", q)
        assert "output" in INTERPRETER.reply(v), where
        assert findings(v) == alone, where
