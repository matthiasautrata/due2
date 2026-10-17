"""The driver's flatten (DESIGN.md § Fact schema): Turtle and JSON to facts, and no semantics."""

from __future__ import annotations

from collections.abc import Generator, Iterable
from contextlib import contextmanager

import rdflib
from clingo import Function, String, Symbol
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.compare import to_canonical_graph
from rdflib.graph import ReadOnlyGraphAggregate
from rdflib.namespace import RDF, XSD
from rdflib.term import Node

from clingo_i.json_types import Json, Obj, as_list, as_obj, as_str

ODRL_PROFILE = URIRef("http://www.w3.org/ns/odrl/2/profile")
STATUSES = ("resolved", "missing", "invalid", "conflict", "unresolved")
VIOLATIONS = ("ignore", "deny")
UNREAD_CONFIG = ("preference", "admit_source", "admit_age")  # no case-format shape yet


@contextmanager
def _exact_literals() -> Generator[None]:
    """rdflib's literal normalisation is lossy (fractional seconds, a date's timezone)."""
    saved = rdflib.NORMALIZE_LITERALS
    rdflib.NORMALIZE_LITERALS = False
    try:
        yield
    finally:
        rdflib.NORMALIZE_LITERALS = saved


def parse(text: str) -> ReadOnlyGraphAggregate:
    """The graph, lexical forms as written, with rdflib's canonical blank node labels."""
    with _exact_literals():
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
            return Function(
                "lit", [String(str(node)), String(str(RDF.langString)), String(node.language)]
            )
        return Function("lit", [String(str(node)), String(str(node.datatype or XSD.string))])
    raise TypeError(f"unexpected RDF term {node!r}")


def namespace(predicate: str) -> str:
    """The predicate up to and including its last '#' or '/'."""
    return predicate[: max(predicate.rfind("#"), predicate.rfind("/")) + 1]


def render(facts: Iterable[Symbol]) -> str:
    return "\n".join(f"{f}." for f in facts)


def graph_facts(graph: ReadOnlyGraphAggregate, name: str, scope: str) -> list[Symbol]:
    out: list[Symbol] = []
    for s, p, o in graph:
        out.append(Function(name, [term(s, scope), term(p, scope), term(o, scope)]))
        if name == "triple":
            out.append(Function("pred_ns", [term(p, scope), String(namespace(str(p)))]))
    return out


def policy_facts(graph: ReadOnlyGraphAggregate) -> list[Symbol]:
    return graph_facts(graph, "triple", "policy")


def module_facts(path: str, text: str) -> list[Symbol]:
    return graph_facts(parse(text), "module", path)


def profiles(graph: ReadOnlyGraphAggregate) -> list[str]:
    """Every odrl:profile value; lift.lp declines one that is not on the policy."""
    return sorted({str(o) for o in graph.objects(None, ODRL_PROFILE)})


# --- the input (workflows §3.2 to §3.4, conformance/README.md) ---


def expand(name: str, prefixes: dict[str, str]) -> str:
    """As the harness expands a name (tools/harness/compare.py)."""
    if name.startswith(("http://", "https://", "urn:")):
        return name
    pfx, sep, local = name.partition(":")
    return prefixes[pfx] + local if sep and pfx in prefixes else name


def fields(value: Json, what: str, required: tuple[str, ...], optional: tuple[str, ...]) -> Obj:
    """The object, with no field outside the case format and none of the required missing."""
    obj = as_obj(value, what)
    unknown = sorted(set(obj) - set(required) - set(optional))
    if unknown:
        raise ValueError(f"{what}: unknown field {unknown[0]!r}")
    missing = [k for k in required if k not in obj]
    if missing:
        raise ValueError(f"{what}: missing field {missing[0]!r}")
    return obj


def name(value: Json, prefixes: dict[str, str], what: str) -> Symbol:
    """A name: a string, or {"@id": …}."""
    if isinstance(value, dict):
        value = fields(value, what, ("@id",), ())["@id"]
    return String(expand(as_str(value, what), prefixes))


def value(v: Json, prefixes: dict[str, str], what: str) -> Symbol:
    """An input value: {"@id"}, or {"@value"} with an optional "@type" or "@language"."""
    obj = as_obj(v, what)  # a bare string is ambiguous between a name and a string
    if "@id" in obj:
        return name(obj, prefixes, what)
    fields(obj, what, ("@value",), ("@type", "@language"))
    lex = as_str(obj["@value"], f"{what}.@value")
    if "@language" in obj:
        if "@type" in obj:
            raise ValueError(f"{what}: both @type and @language")
        lang = as_str(obj["@language"], f"{what}.@language")
        return Function("lit", [String(lex), String(str(RDF.langString)), String(lang)])
    datatype = (
        expand(as_str(obj["@type"], f"{what}.@type"), prefixes)
        if "@type" in obj
        else str(XSD.string)
    )
    return Function("lit", [String(lex), String(datatype)])


def instant(v: Json, what: str) -> Symbol:
    return Function("lit", [String(as_str(v, what)), String(str(XSD.dateTime))])


def _values(v: Json) -> list[Json]:
    return v if isinstance(v, list) else [v]


def request_facts(request: Obj, prefixes: dict[str, str]) -> list[Symbol]:
    fields(request, "request", ("action",), ("reference", "target", "at", "parties", "params"))
    out = [Function("request_action", [name(request["action"], prefixes, "request.action")])]
    if "reference" in request:
        out.append(
            Function(
                "request_reference", [String(as_str(request["reference"], "request.reference"))]
            )
        )
    target = request.get("target")
    if target is None:
        out.append(Function("request_absent", [Function("target")]))
    else:
        out.append(Function("request_target", [name(target, prefixes, "request.target")]))
    if "at" in request:
        out.append(Function("request_at", [instant(request["at"], "request.at")]))
    for key, v in as_obj(request.get("parties") or {}, "request.parties").items():
        function = String(expand(key, prefixes))
        for x in _values(v):
            out.append(
                Function("request_party", [function, name(x, prefixes, f"request.parties.{key}")])
            )
    for key, v in as_obj(request.get("params") or {}, "request.params").items():
        param = String(expand(key, prefixes))
        if isinstance(v, list):
            out.append(Function("request_param_set", [param]))
        for x in _values(v):
            out.append(
                Function("request_param", [param, value(x, prefixes, f"request.params.{key}")])
            )
    return out


def sotw_facts(sotw: Obj, prefixes: dict[str, str]) -> list[Symbol]:
    fields(sotw, "sotw", (), ("effective_at", "facts", "evidence", "activation", "closure"))
    out: list[Symbol] = []
    if "effective_at" in sotw:
        out.append(
            Function("sotw_effective_at", [instant(sotw["effective_at"], "sotw.effective_at")])
        )
    for key, f in as_obj(sotw.get("facts") or {}, "sotw.facts").items():
        what = f"sotw.facts.{key}"
        obj = fields(f, what, ("status",), ("values",))
        status = as_str(obj["status"], f"{what}.status")
        if status not in STATUSES:
            raise ValueError(f"{what}: unknown status {status!r}")
        prop = String(expand(key, prefixes))
        out.append(Function("fact", [prop, Function(status)]))
        for x in as_list(obj.get("values") or [], f"{what}.values"):
            out.append(Function("fact_value", [prop, value(x, prefixes, f"{what}.values")]))
    seen: set[Symbol] = set()
    for i, raw in enumerate(as_list(sotw.get("evidence") or [], "sotw.evidence")):
        what = f"sotw.evidence[{i}]"
        ev = fields(
            raw,
            what,
            ("id", "occurred_at", "actor", "action"),
            ("object", "issuer", "discharges", "params"),
        )
        e = name(ev["id"], prefixes, f"{what}.id")
        if e in seen:
            raise ValueError(f"{what}: duplicate evidence id {e}")
        seen.add(e)
        out.append(
            Function(
                "evidence",
                [
                    e,
                    instant(ev["occurred_at"], f"{what}.occurred_at"),
                    name(ev["actor"], prefixes, f"{what}.actor"),
                    name(ev["action"], prefixes, f"{what}.action"),
                ],
            )
        )
        for k in ("object", "issuer"):
            if k in ev:
                out.append(Function(f"evidence_{k}", [e, name(ev[k], prefixes, f"{what}.{k}")]))
        if "discharges" in ev:
            d = fields(ev["discharges"], f"{what}.discharges", ("duty", "reference"), ())
            out.append(
                Function(
                    "evidence_discharges",
                    [
                        e,
                        name(d["duty"], prefixes, f"{what}.discharges.duty"),
                        String(as_str(d["reference"], f"{what}.discharges.reference")),
                    ],
                )
            )
        for key, x in as_obj(ev.get("params") or {}, f"{what}.params").items():
            param = String(expand(key, prefixes))
            out.append(
                Function("evidence_param", [e, param, value(x, prefixes, f"{what}.params.{key}")])
            )
    for key, at in as_obj(sotw.get("activation") or {}, "sotw.activation").items():
        out.append(
            Function(
                "activation", [String(expand(key, prefixes)), instant(at, f"sotw.activation.{key}")]
            )
        )
    for i, raw in enumerate(as_list(sotw.get("closure") or [], "sotw.closure")):
        edge = as_list(raw, f"sotw.closure[{i}]")
        if len(edge) != 3:
            raise ValueError(f"sotw.closure[{i}]: expected [relation, narrower, broader]")
        out.append(
            Function("sotw_closure", [name(x, prefixes, f"sotw.closure[{i}]") for x in edge])
        )
    return out


def config_facts(config: Obj, prefixes: dict[str, str]) -> list[Symbol]:
    fields(config, "config", ("combination",), ("violations", "signers", *UNREAD_CONFIG))
    out = [
        Function(
            "config_combination", [String(as_str(config["combination"], "config.combination"))]
        )
    ]
    if "violations" in config:
        violations = as_str(config["violations"], "config.violations")
        if violations not in VIOLATIONS:
            raise ValueError(f"config.violations: unknown value {violations!r}")
        out.append(Function("config_violations", [Function(violations)]))
    for i, raw in enumerate(as_list(config.get("signers") or [], "config.signers")):
        what = f"config.signers[{i}]"
        s = fields(raw, what, ("duty", "issuer"), ())
        out.append(
            Function(
                "signer",
                [
                    name(s["duty"], prefixes, f"{what}.duty"),
                    name(s["issuer"], prefixes, f"{what}.issuer"),
                ],
            )
        )
    out.extend(Function("unread", [String(f"config.{k}")]) for k in UNREAD_CONFIG if k in config)
    return out


def input_facts(vector: Obj, prefixes: dict[str, str]) -> list[Symbol]:
    return (
        request_facts(as_obj(vector["request"], "request"), prefixes)
        + sotw_facts(as_obj(vector["sotw"], "sotw"), prefixes)
        + config_facts(as_obj(vector["config"], "config"), prefixes)
    )
