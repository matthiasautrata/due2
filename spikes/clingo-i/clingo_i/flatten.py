"""The driver's flatten (DESIGN.md § Fact schema): Turtle and JSON to facts, and no semantics."""

from __future__ import annotations

from clingo import Function, String, Symbol
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.compare import to_canonical_graph
from rdflib.graph import ReadOnlyGraphAggregate
from rdflib.namespace import RDF, XSD
from rdflib.term import Node

from clingo_i.json_types import Json, Obj

ODRL_PROFILE = URIRef("http://www.w3.org/ns/odrl/2/profile")


def parse(text: str) -> ReadOnlyGraphAggregate:
    """The graph with rdflib's canonical blank node labels, independent of the parser's."""
    graph = Graph()
    graph.parse(data=text, format="turtle")
    return to_canonical_graph(graph)


def term(node: Node, scope: str) -> Symbol:
    if isinstance(node, URIRef):
        return String(str(node))
    if isinstance(node, BNode):
        return Function("b", [String(scope), String(str(node))])
    if isinstance(node, Literal):
        if node.language is not None:
            datatype = str(RDF.langString)
        else:
            datatype = str(node.datatype or XSD.string)
        return Function("lit", [String(str(node)), String(datatype)])
    raise TypeError(f"unexpected RDF term {node!r}")


def namespace(predicate: str) -> str:
    """The predicate up to and including its last '#' or '/'."""
    return predicate[: max(predicate.rfind("#"), predicate.rfind("/")) + 1]


def fact(name: str, *args: Symbol) -> str:
    return f"{Function(name, list(args))}."


def graph_facts(graph: ReadOnlyGraphAggregate, name: str, scope: str) -> list[str]:
    out: list[str] = []
    for s, p, o in graph:
        out.append(fact(name, term(s, scope), term(p, scope), term(o, scope)))
        if name == "triple":
            out.append(fact("pred_ns", term(p, scope), String(namespace(str(p)))))
    return out


def policy_facts(graph: ReadOnlyGraphAggregate) -> list[str]:
    return graph_facts(graph, "triple", "policy")


def module_facts(path: str, text: str) -> list[str]:
    return graph_facts(parse(text), "module", path)


def profiles(graph: ReadOnlyGraphAggregate) -> list[str]:
    """Every odrl:profile value; lift.lp declines one that is not on the policy."""
    return sorted({str(o) for o in graph.objects(None, ODRL_PROFILE)})


def expand(name: str, prefixes: dict[str, str]) -> str:
    """As the harness expands a name (tools/harness/compare.py)."""
    if name.startswith(("http://", "https://", "urn:")):
        return name
    pfx, sep, local = name.partition(":")
    return prefixes[pfx] + local if sep and pfx in prefixes else name


def name(value: Json, prefixes: dict[str, str], what: str) -> Symbol:
    if isinstance(value, dict) and isinstance(value.get("@id"), str):
        value = value["@id"]
    if not isinstance(value, str):
        raise TypeError(f"{what}: expected a name, got {value!r}")
    return String(expand(value, prefixes))


def request_facts(request: Obj, prefixes: dict[str, str]) -> list[str]:
    out = [fact("req_action", name(request["action"], prefixes, "request.action"))]
    target = request.get("target")
    if target is None:
        out.append(fact("req_absent", Function("target")))
    else:
        out.append(fact("req_target", name(target, prefixes, "request.target")))
    parties = request.get("parties") or {}
    if not isinstance(parties, dict):
        raise TypeError("request.parties: expected an object")
    for key, value in parties.items():
        function = String(expand(key, prefixes))
        for v in value if isinstance(value, list) else [value]:
            out.append(fact("req_party", function, name(v, prefixes, f"request.parties.{key}")))
    return out
