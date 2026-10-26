"""The driver's flatten: Turtle and JSON to facts, and no semantics.

The flatten is syntactic: one fact per triple, and one fact or a few per input field, named
after the relations of due2-workflows.md §3.2 to §3.4. It drops nothing and decides nothing,
and it adds only the value table (`values.py`). A field the program does not read is still
flattened, so that a later reader finds it and the round-trip tests cover it; the program
declines a field it cannot answer for. These facts are the program's input: every relation a
file of `lp/` consumes and no file defines is listed below, with the files that read it.

**Graphs.**

- `triple/3`, `triple(S, P, O)`: each policy triple. Read by lift.lp, structure.lp, and
  constraint.lp.
- `module/4`, `module(Path, S, P, O)`: each triple of a selected module, `Path` the module's
  path. Its blank nodes are scoped by `Path`. Read by lift.lp.
- `layer/2`, `layer(Path, core | module(Iri))`: each selected module file, `core` for a core
  file and `module(Iri)` for a file of the selected profile `Iri`, so a profile whose module is
  several files is one layer; a file in both is `core` (`interpret.py`). Read by lift.lp.
- `pred_ns/2`, `pred_ns(P, NS)`: each policy predicate. `NS` is `P` up to and including its
  last `#` or `/`. Read by lift.lp.
- `selected_profile/1`, `selected_profile(Iri)`: each `odrl:profile` value that names a shipped
  profile. Read by lift.lp.

**Request** (due2-workflows.md §3.2).

- `request_reference/1`: `reference`, as given. Read by duty.lp.
- `request_action/1`, `request_action(A)`: `action`. Read by applies.lp.
- `request_target/1`, `request_target(T)`: `target`. Read by applies.lp.
- `request_absent/1`, `request_absent(target)`: the absence of `target`. Read by applies.lp.
- `request_at/1`, `request_at(Lit)`: `at`. Read by lift.lp, and by operand.lp for
  `actionTime`.
- `request_party/2`, `request_party(F, Party)`: each element of `parties`, `F` the function
  predicate IRI. Read by lift.lp, operand.lp (`agent`), applies.lp, and duty.lp (the request
  subject).
- `request_param/2`, `request_param(Prop, Value)`: each value of `params`, keyed by property
  IRI. Read by lift.lp and operand.lp.
- `request_param_set/1`, `request_param_set(Prop)`: a `params` element given as a list, so an
  empty set is not an absent parameter. Read by operand.lp.

**SOTW** (due2-workflows.md §3.3).

- `sotw_effective_at/1`: `effective_at`. Read by lift.lp, operand.lp (`clock`), and duty.lp.
- `fact/2`, `fact(Prop, Status)`: each element of `facts`. `Status` is one of `resolved`,
  `missing`, `invalid`, `conflict`, `unresolved`. Read by operand.lp.
- `fact_value/2`, `fact_value(Prop, Value)`: each value of a `facts` element. Read by lift.lp
  and operand.lp.
- `evidence/4`, `evidence(E, OccurredAt, Actor, Action)`: each `evidence` record, `E` its
  `id`. Read by lift.lp, operand.lp (`actionTime` in `wit(E)`), and duty.lp.
- `evidence_object/2`, `evidence_issuer/2`: its optional `object` and `issuer`. Read by
  duty.lp.
- `evidence_discharges/3`, `evidence_discharges(E, Duty, Ref)`: its optional `discharges`.
  Read by duty.lp.
- `evidence_param/3`, `evidence_param(E, Prop, Value)`: each of its `params`. Read by lift.lp
  and operand.lp (`witness`).
- `activation/2`, `activation(Key, Lit)`: each element of `activation`, a duty atom's id or a
  rule IRI, and its instant. duty.lp reads a key that is a duty's IRI, as the case format names an
  activation (`conformance/README.md`, SOTW). Read by lift.lp and duty.lp.
- `sotw_closure/3`, `sotw_closure(Pred, Lo, Hi)`: each `closure` triple, `Pred` expanded. Read
  by lift.lp: an edge of a hierarchy the spike reads (`closure_key/1`) joins `closure/3`, and
  any other relation declines.

**Config** (due2-workflows.md §3.4).

- `config_combination/1`: `combination`, a string. Read by lift.lp.
- `config_violations/1`: `violations`, `ignore` or `deny`. Read by resolve.lp.
- `signer/2`, `signer(Duty, Issuer)`: each `signers` element. Read by duty.lp.
- `unread/1`, `unread(Field)`: `preference`, `admit_source`. The case format
  defines no shape for them (`conformance/README.md`), so their presence is recorded, and
  lift.lp declines it.

**Values** (`values.py`): `value/3`, read by operand.lp, compare.lp, and duty.lp;
`unplaceable/2`, read by lift.lp and constraint.lp; and `plus/3`, read by duty.lp for a
relative deadline.

A field the case format does not define, a missing required field (`action`; an evidence
record's `id`, `occurred_at`, `actor`, `action`), a duplicate evidence `id`, or an unknown
status is a `ValueError`, which the reply reports as an `error`: the vector is malformed, and
nothing is guessed.

**Terms.**

- **IRIs** are clingo strings.
- **RDF literals** are `lit(Lex, Datatype)`, with the lexical form exactly as written. rdflib
  normalises lexical forms by default, and its normalisation is lossy: it truncates fractional
  seconds to six digits and drops a date's timezone. The driver therefore parses with
  normalisation off. A plain literal is `xsd:string`. A language-tagged one is
  `lit(Lex, rdf:langString, Tag)`.
- **Blank nodes** are `b(Scope, Label)`. The label is rdflib's canonical one
  (`rdflib.compare.to_canonical_graph`), so it does not depend on the labels the parser chose.
  `Scope` is `"policy"` or the module's path, so blank nodes from different graphs never meet.
- **Input names** are expanded with the vector's prefixes, the same way the harness expands
  them. A name is a string or `{"@id": …}`. `reference` is not a name, and stays as given.
- **Input values** (`params`, `fact_value`, an evidence record's `params`) are `{"@id": …}`,
  read as its IRI; `{"@value": …, "@type": …}`, read as `lit` with the type expanded;
  `{"@value": …}`, read as `xsd:string`; or `{"@value": …, "@language": …}`. A bare string is
  an error, because it is ambiguous between a name and a string.
- **Input instants** (`at`, `effective_at`, `occurred_at`, activation instants) are
  `lit(I, xsd:dateTime)`.
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
UNREAD_CONFIG = ("preference", "admit_source")


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


def policy_facts(graph: ReadOnlyGraphAggregate) -> list[Symbol]:
    """The policy graph: one `triple(S, P, O)` and one `pred_ns` per triple, blank nodes scoped
    `"policy"`."""
    out: list[Symbol] = []
    for s, p, o in graph:
        out.append(Function("triple", [term(s, "policy"), term(p, "policy"), term(o, "policy")]))
        out.append(Function("pred_ns", [term(p, "policy"), String(namespace(str(p)))]))
    return out


def module_facts(path: str, text: str) -> list[Symbol]:
    """The module at `path`: one `module(Path, S, P, O)` per triple, blank nodes scoped by the
    path. The path names the module's layer (module docstring, **Graphs**)."""
    return [
        Function("module", [String(path), term(s, path), term(p, path), term(o, path)])
        for s, p, o in parse(text)
    ]


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
