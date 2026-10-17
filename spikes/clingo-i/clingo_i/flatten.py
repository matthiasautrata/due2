"""The driver's flatten: Turtle and JSON to facts, and no semantics.

Each triple becomes one fact, and each input field one fact or a few, named after the relations
of due2-workflows.md §3.2 to §3.4. The flatten drops nothing and decides nothing: a field the
program does not read is still flattened, and the program declines it (DESIGN.md § Input facts).
A field the case format does not define is a `ValueError`, because the vector is malformed.

The terms: an IRI is a clingo string, a blank node `b(Scope, Label)`, and an RDF literal
`lit(Lex, Datatype)` or `lit(Lex, rdf:langString, Tag)`, with the lexical form as written.
"""

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
# Config fields the case format names but gives no shape (conformance/README.md): their
# presence is recorded as `unread`, and the program declines it.
UNREAD_CONFIG = ("preference", "admit_source", "admit_age")


@contextmanager
def _exact_literals() -> Generator[None]:
    """Parse with rdflib's literal normalisation off, and restore it afterwards.

    The normalisation is lossy: it truncates fractional seconds to six digits and drops a
    date's timezone, and the value table needs the lexical form as written.
    """
    saved = rdflib.NORMALIZE_LITERALS
    rdflib.NORMALIZE_LITERALS = False
    try:
        yield
    finally:
        rdflib.NORMALIZE_LITERALS = saved


def parse(text: str) -> ReadOnlyGraphAggregate:
    """The Turtle `text` as a graph, lexical forms as written, with canonical blank node labels.

    The labels come from `rdflib.compare.to_canonical_graph`, so they do not depend on the
    labels the parser chose, and the facts do not depend on serialisation order.
    """
    with _exact_literals():
        graph = Graph()
        graph.parse(data=text, format="turtle")
        return to_canonical_graph(graph)


def term(node: Node, scope: str) -> Symbol:
    """An RDF term as a clingo term; `scope` keeps blank nodes of different graphs apart.

    Raises:
        TypeError: `node` is not an IRI, a blank node, or a literal.
    """
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
    """The predicate IRI up to and including its last `#` or `/`, read by `pred_ns/2`."""
    return predicate[: max(predicate.rfind("#"), predicate.rfind("/")) + 1]


def render(facts: Iterable[Symbol]) -> str:
    """The facts as program text, one per line."""
    return "\n".join(f"{f}." for f in facts)


def graph_facts(graph: ReadOnlyGraphAggregate, name: str, scope: str) -> list[Symbol]:
    """One `name(S, P, O)` fact per triple; for the policy (`triple`), each `pred_ns` too."""
    out: list[Symbol] = []
    for s, p, o in graph:
        out.append(Function(name, [term(s, scope), term(p, scope), term(o, scope)]))
        if name == "triple":
            out.append(Function("pred_ns", [term(p, scope), String(namespace(str(p)))]))
    return out


def policy_facts(graph: ReadOnlyGraphAggregate) -> list[Symbol]:
    """The policy graph as `triple/3` and `pred_ns/2`, blank nodes scoped `"policy"`."""
    return graph_facts(graph, "triple", "policy")


def module_facts(path: str, text: str) -> list[Symbol]:
    """The module at `path` as `module/3`, blank nodes scoped by the path."""
    return graph_facts(parse(text), "module", path)


def profiles(graph: ReadOnlyGraphAggregate) -> list[str]:
    """Every `odrl:profile` value in the graph, sorted; lift.lp declines one not on the policy."""
    return sorted({str(o) for o in graph.objects(None, ODRL_PROFILE)})


# --- the input (due2-workflows.md §3.2 to §3.4, conformance/README.md) ---


def expand(name: str, prefixes: dict[str, str]) -> str:
    """A compact name `pfx:local` expanded with `prefixes`, as the harness expands it.

    An absolute IRI, or a name whose prefix is not declared, is returned as given. The rule is
    the one of tools/harness/compare.py, so the driver and the harness read a name alike.
    """
    if name.startswith(("http://", "https://", "urn:")):
        return name
    pfx, sep, local = name.partition(":")
    return prefixes[pfx] + local if sep and pfx in prefixes else name


def fields(value: Json, what: str, required: tuple[str, ...], optional: tuple[str, ...]) -> Obj:
    """`value` as an object, checked against the case format's fields.

    Args:
        value: The JSON value to check.
        what: Its path in the vector, for the error message.
        required: The fields that must be present.
        optional: The fields that may be present.

    Raises:
        TypeError: `value` is not an object.
        ValueError: A field is outside `required` and `optional`, or a required one is missing.
    """
    obj = as_obj(value, what)
    unknown = sorted(set(obj) - set(required) - set(optional))
    if unknown:
        raise ValueError(f"{what}: unknown field {unknown[0]!r}")
    missing = [k for k in required if k not in obj]
    if missing:
        raise ValueError(f"{what}: missing field {missing[0]!r}")
    return obj


def name(value: Json, prefixes: dict[str, str], what: str) -> Symbol:
    """A name, a string or `{"@id": …}`, expanded to an IRI string."""
    if isinstance(value, dict):
        value = fields(value, what, ("@id",), ())["@id"]
    return String(expand(as_str(value, what), prefixes))


def value(v: Json, prefixes: dict[str, str], what: str) -> Symbol:
    """An input value as a term: `{"@id": …}` an IRI, `{"@value": …}` a `lit`.

    `"@type"` gives the datatype, expanded, and `"@language"` a language tag; with neither,
    the datatype is `xsd:string`.

    Raises:
        TypeError: `v` is a bare string, which is ambiguous between a name and a string.
        ValueError: An unknown field, or both `"@type"` and `"@language"`.
    """
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
    """An input instant (a string) as `lit(I, xsd:dateTime)`."""
    return Function("lit", [String(as_str(v, what)), String(str(XSD.dateTime))])


def _values(v: Json) -> list[Json]:
    """A field that holds one value or a list of them, as a list."""
    return v if isinstance(v, list) else [v]


def request_facts(request: Obj, prefixes: dict[str, str]) -> list[Symbol]:
    """The request's facts (due2-workflows.md §3.2).

    An absent target is the fact `request_absent(target)`, not the lack of a fact, so a
    rule can read it without negation. A `params` entry given as a list adds
    `request_param_set`, so that an empty set is not an absent parameter.
    """
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
    """The SOTW's facts (due2-workflows.md §3.3).

    Raises:
        ValueError: An unknown fact status, a duplicate evidence id, or a closure entry that is
            not `[relation, narrower, broader]`.
    """
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
    """The config's facts (due2-workflows.md §3.4); each `UNREAD_CONFIG` field is `unread`."""
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
    """The facts of the vector's request, SOTW, and config, names expanded with `prefixes`."""
    return (
        request_facts(as_obj(vector["request"], "request"), prefixes)
        + sotw_facts(as_obj(vector["sotw"], "sotw"), prefixes)
        + config_facts(as_obj(vector["config"], "config"), prefixes)
    )
