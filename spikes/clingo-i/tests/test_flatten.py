"""The driver (TESTS.md): the flatten loses nothing, depends on no order or label,
parses what the checkers parse, and refuses a malformed input."""

from __future__ import annotations

import copy
import json
import random
import re
from functools import cache
from pathlib import Path

import pytest
import rdflib
from check_corpus import check_file
from clingo import Symbol, SymbolType
from harness.compare import expand as harness_expand
from harness.corpus import Vector, init_message, interpret_vectors
from hypothesis import given, settings
from hypothesis import strategies as st
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import RDF, XSD
from rdflib.term import Node

from clingo_i import flatten, values
from clingo_i.interpret import Interpreter
from clingo_i.json_types import Json, Obj, as_list, as_obj, as_str
from tests.conftest import BASE, SPIKE, vector

ROOT = SPIKE.parents[1]
TURTLE = sorted(
    {
        *ROOT.glob("conformance/cases/*/policy*.ttl"),
        *ROOT.glob("profiles/**/*.ttl"),
        *ROOT.glob("conformance/external/**/*.ttl"),
    }
)
VECTORS = interpret_vectors()


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


@cache
def exact_graph(path: Path) -> Graph | None:
    """The file as rdflib parses it with normalisation off; None when it does not parse."""
    saved, rdflib.NORMALIZE_LITERALS = rdflib.NORMALIZE_LITERALS, False
    try:
        g = Graph()
        g.parse(path, format="turtle")
        return g
    except Exception:  # noqa: BLE001 -- a parse failure of any kind
        return None
    finally:
        rdflib.NORMALIZE_LITERALS = saved


# --- the graph round trip ---


def decode_term(s: Symbol) -> Node:
    if s.type == SymbolType.String:
        return URIRef(s.string)
    args = [a.string for a in s.arguments]
    if s.name == "b":
        return BNode(args[1])
    if s.name == "lit" and len(args) == 3:
        assert args[1] == str(RDF.langString)
        return Literal(args[0], lang=args[2], normalize=False)
    assert s.name == "lit"
    return Literal(args[0], datatype=URIRef(args[1]), normalize=False)


def plain_is_string(g: Graph) -> Graph:
    """RDF 1.1: a plain literal is an xsd:string. rdflib keeps them apart."""
    out = Graph()
    for s, p, o in g:
        if isinstance(o, Literal) and o.datatype is None and o.language is None:
            o = Literal(str(o), datatype=XSD.string, normalize=False)
        out.add((s, p, o))
    return out


@pytest.mark.parametrize("path", TURTLE, ids=rel)
def test_graph_round_trip(path: Path) -> None:
    original = exact_graph(path)
    if original is None:
        pytest.skip("does not parse")
    facts = flatten.policy_facts(flatten.parse(path.read_text()))
    back = Graph()
    for f in facts:
        if f.match("triple", 3):
            s, p, o = (decode_term(a) for a in f.arguments)
            back.add((s, p, o))
    assert len(back) == len(original)
    assert isomorphic(back, plain_is_string(original))
    # Lexical forms survive: no literal is rewritten (isomorphism compares terms).
    lexes = {str(o) for o in original.objects() if isinstance(o, Literal)}
    assert {str(o) for o in back.objects() if isinstance(o, Literal)} == lexes


# --- the input round trip: the facts decoded back to the vector, names expanded ---


def canon(xs: list[Json]) -> list[Json]:
    """A list read as a set."""
    return sorted(xs, key=lambda x: json.dumps(x, sort_keys=True))


def norm_name(v: Json, pfx: dict[str, str]) -> str:
    if isinstance(v, dict):
        v = v["@id"]
    return harness_expand(as_str(v, "name"), pfx)


def norm_value(v: Json, pfx: dict[str, str]) -> Json:
    obj = as_obj(v, "value")
    if "@id" in obj:
        return {"@id": norm_name(obj, pfx)}
    out: Obj = {"@value": obj["@value"]}
    if "@language" in obj:
        out["@language"] = obj["@language"]
    elif "@type" in obj and harness_expand(as_str(obj["@type"], "@type"), pfx) != str(XSD.string):
        out["@type"] = harness_expand(as_str(obj["@type"], "@type"), pfx)
    return out


def norm_values(v: Json, pfx: dict[str, str]) -> Json:
    if isinstance(v, list):
        return {"set": canon([norm_value(x, pfx) for x in v])}
    return norm_value(v, pfx)


def put(target: Obj, fields: Obj) -> None:
    """Each field that is not empty: an empty field gives no facts."""
    target.update({k: v for k, v in fields.items() if v})


def normalise(vector: Obj) -> Obj:
    """The vector as the facts must say it: names expanded, empty fields absent, sets sorted."""
    pfx = {k: as_str(v, k) for k, v in as_obj(vector["prefixes"], "prefixes").items()}
    req, sotw = (as_obj(vector[k], k) for k in ("request", "sotw"))
    r: Obj = {"action": norm_name(req["action"], pfx)}
    for k in ("reference", "at"):
        if k in req:
            r[k] = req[k]
    if req.get("target") is not None:
        r["target"] = norm_name(req["target"], pfx)
    parties: Obj = {
        harness_expand(k, pfx): canon(
            [norm_name(x, pfx) for x in (v if isinstance(v, list) else [v])]
        )
        for k, v in as_obj(req.get("parties") or {}, "parties").items()
    }
    params: Obj = {
        harness_expand(k, pfx): norm_values(v, pfx)
        for k, v in as_obj(req.get("params") or {}, "").items()
    }
    put(r, {"parties": parties, "params": params})
    s: Obj = {}
    if "effective_at" in sotw:
        s["effective_at"] = sotw["effective_at"]
    facts: Obj = {}
    for k, f in as_obj(sotw.get("facts") or {}, "facts").items():
        # One answer names no source, which the facts call `unnamed`; a list names each.
        answers = [as_obj(a, k) for a in ([f] if isinstance(f, dict) else as_list(f, k))]
        facts[harness_expand(k, pfx)] = {
            norm_name(a["source"], pfx) if "source" in a else "unnamed": {
                "status": a["status"],
                "values": canon([norm_value(x, pfx) for x in as_list(a.get("values") or [], k)]),
            }
            for a in answers
        }
    evidence: Obj = {}
    for raw in as_list(sotw.get("evidence") or [], "evidence"):
        e = as_obj(raw, "evidence")
        ev: Obj = {
            "occurred_at": e["occurred_at"],
            **{k: norm_name(e[k], pfx) for k in ("actor", "action", "object", "issuer") if k in e},
        }
        if "discharges" in e:
            d = as_obj(e["discharges"], "discharges")
            ev["discharges"] = [norm_name(d["duty"], pfx), d["reference"]]
        params_e = {
            harness_expand(k, pfx): norm_values(v, pfx)
            for k, v in as_obj(e.get("params") or {}, "").items()
        }
        if params_e:
            ev["params"] = params_e
        evidence[norm_name(e["id"], pfx)] = ev
    activation: Obj = {
        harness_expand(k, pfx): v for k, v in as_obj(sotw.get("activation") or {}, "").items()
    }
    closure = canon(
        [
            [norm_name(x, pfx) for x in as_list(t, "edge")]
            for t in as_list(sotw.get("closure") or [], "")
        ]
    )
    put(s, {"facts": facts, "evidence": evidence, "activation": activation, "closure": closure})
    return {"request": r, "sotw": s}


def text(s: Symbol) -> str:
    return s.string if s.type == SymbolType.String else str(s)


def decode_value(s: Symbol) -> Json:
    if s.type == SymbolType.String:
        return {"@id": s.string}
    args = [a.string for a in s.arguments]
    if len(args) == 3:
        return {"@value": args[0], "@language": args[2]}
    return (
        {"@value": args[0]} if args[1] == str(XSD.string) else {"@value": args[0], "@type": args[1]}
    )


def lex(s: Symbol) -> str:
    assert s.match("lit", 2) and s.arguments[1].string == str(XSD.dateTime)
    return s.arguments[0].string


def unlist(params: dict[str, list[Json]], sets: set[str]) -> Obj:
    """Each parameter's values as normalise() writes them: a set, possibly empty, when it was
    given as a list, and otherwise its one value."""
    assert all(len(v) == 1 for k, v in params.items() if k not in sets)
    return {
        k: {"set": canon(params.get(k, []))} if k in sets else params[k][0]
        for k in params.keys() | sets
    }


def decode(facts: list[Symbol]) -> Obj:
    """The facts read back as normalise() writes the vector."""
    r: Obj = {}
    s: Obj = {}
    sets: set[str] = set()
    parties: dict[str, list[Json]] = {}
    params: dict[str, list[Json]] = {}
    ev_sets: set[tuple[str, str]] = set()
    ev_params: dict[str, dict[str, list[Json]]] = {}
    facts_o: dict[str, dict[str, Obj]] = {}
    evidence: dict[str, Obj] = {}

    def answer(prop: str, source: str) -> Obj:
        return facts_o.setdefault(prop, {}).setdefault(source, {"values": []})

    closure: list[Json] = []
    activation: Obj = {}
    for f in facts:
        a = f.arguments
        match f.name:
            case "request_action":
                r["action"] = a[0].string
            case "request_reference":
                r["reference"] = a[0].string
            case "request_target":
                r["target"] = a[0].string
            case "request_absent":
                assert str(a[0]) == "target"
            case "request_at":
                r["at"] = lex(a[0])
            case "request_party":
                parties.setdefault(a[0].string, []).append(a[1].string)
            case "request_param_set":
                sets.add(a[0].string)
            case "request_param":
                params.setdefault(a[0].string, []).append(decode_value(a[1]))
            case "sotw_effective_at":
                s["effective_at"] = lex(a[0])
            case "fact_answer":
                answer(a[0].string, text(a[1]))["status"] = text(a[2])
            case "fact_answer_value":
                vs = answer(a[0].string, text(a[1]))["values"]
                assert isinstance(vs, list)
                vs.append(decode_value(a[2]))
            case "evidence":
                evidence.setdefault(a[0].string, {}).update(
                    occurred_at=lex(a[1]), actor=a[2].string, action=a[3].string
                )
            case "evidence_object" | "evidence_issuer":
                evidence.setdefault(a[0].string, {})[f.name.removeprefix("evidence_")] = a[1].string
            case "evidence_discharges":
                evidence.setdefault(a[0].string, {})["discharges"] = [a[1].string, a[2].string]
            case "evidence_param_set":
                ev_sets.add((a[0].string, a[1].string))
            case "evidence_param":
                vs = ev_params.setdefault(a[0].string, {}).setdefault(a[1].string, [])
                vs.append(decode_value(a[2]))
            case "activation":
                activation[a[0].string] = lex(a[1])
            case "sotw_closure":
                closure.append([x.string for x in a])
            case _:
                raise AssertionError(f"unknown fact {f}")
    if parties:
        r["parties"] = {k: canon(v) for k, v in parties.items()}
    if params or sets:
        r["params"] = unlist(params, sets)
    for e, prop in ev_sets:
        ev_params.setdefault(e, {}).setdefault(prop, [])
    for e, ps in ev_params.items():
        evidence[e]["params"] = unlist(ps, {prop for x, prop in ev_sets if x == e})
    for answers in facts_o.values():
        for fo in answers.values():
            fo["values"] = canon(as_list(fo["values"], "values"))
    facts_j: Obj = {k: dict(v.items()) for k, v in facts_o.items()}
    evidence_j: Obj = dict(evidence.items())
    put(
        s,
        {
            "facts": facts_j,
            "evidence": evidence_j,
            "activation": activation,
            "closure": canon(closure),
        },
    )
    return {"request": r, "sotw": s}


def prefixes(v: Obj) -> dict[str, str]:
    return {k: as_str(x, k) for k, x in as_obj(v["prefixes"], "prefixes").items()}


@pytest.mark.parametrize("vec", VECTORS, ids=lambda v: v.id)
def test_input_round_trip(vec: Vector) -> None:
    facts = flatten.input_facts(vec.input, prefixes(vec.input))
    assert decode(facts) == normalise(vec.input)


LISTED: Obj = {
    "ex:two": [{"@id": "ex:v"}, {"@id": "ex:w"}],
    "ex:none": [],
    "ex:one": [{"@id": "ex:v"}],
    "ex:bare": {"@id": "ex:v"},
}
EVIDENCE: Obj = {
    "id": "e1",
    "occurred_at": "2026-05-01T00:00:00Z",
    "actor": "ex:alice",
    "action": "odrl:compensate",
    "params": LISTED,
}


def test_list_params_round_trip() -> None:
    # The corpus has no empty list and no list in an evidence record's params, so the round trip
    # above never reads them. Without `request_param_set`, `[]` would read as an absent
    # parameter, and `["ex:v"]` as the bare value. Without `evidence_param_set`, a list in an
    # evidence record's params is refused as malformed input.
    v = vector(request={"params": LISTED}, sotw={"evidence": [EVIDENCE]})
    assert decode(flatten.input_facts(v, prefixes(v))) == normalise(v)


# --- invariance: no order and no blank node label reaches the facts ---


def relabel(nt: str, rnd: random.Random) -> str:
    labels = sorted(set(re.findall(r"_:(\w+)", nt)))
    fresh = [f"x{n}" for n in rnd.sample(range(10 * len(labels) + 1), len(labels))]
    mapping = dict(zip(labels, fresh, strict=True))
    lines = [
        re.sub(r"_:(\w+)", lambda m: "_:" + mapping[m[1]], line) for line in nt.splitlines() if line
    ]
    rnd.shuffle(lines)
    return "\n".join(lines) + "\n"


POLICIES = [p for p in TURTLE if "conformance/cases/" in rel(p)]


@settings(max_examples=60, deadline=None)
@given(st.sampled_from(POLICIES), st.randoms(use_true_random=False))
def test_graph_invariance(path: Path, rnd: random.Random) -> None:
    text_ = path.read_text()
    g = exact_graph(path)
    assert g is not None
    saved, rdflib.NORMALIZE_LITERALS = rdflib.NORMALIZE_LITERALS, False
    try:
        nt = g.serialize(format="nt")
    finally:
        rdflib.NORMALIZE_LITERALS = saved
    a = set(flatten.policy_facts(flatten.parse(text_)))
    b = set(flatten.policy_facts(flatten.parse(relabel(nt, rnd))))
    assert a == b


def shuffled(x: Json, rnd: random.Random) -> Json:
    """Every object's keys and every list shuffled, except a closure edge's three names."""
    if isinstance(x, dict):
        items = list(x.items())
        rnd.shuffle(items)
        return {k: edges(v, rnd) if k == "closure" else shuffled(v, rnd) for k, v in items}
    if isinstance(x, list):
        ys = [shuffled(v, rnd) for v in x]
        rnd.shuffle(ys)
        return ys
    return x


def edges(x: Json, rnd: random.Random) -> Json:
    ys: list[Json] = [list(as_list(e, "edge")) for e in as_list(x, "closure")]
    rnd.shuffle(ys)
    return ys


@cache
def corpus_interpreter() -> Interpreter:
    return Interpreter(init_message())


@settings(max_examples=60, deadline=None)
@given(st.sampled_from(VECTORS), st.randoms(use_true_random=False))
def test_input_invariance(vec: Vector, rnd: random.Random) -> None:
    v = vec.input
    w = as_obj(shuffled(copy.deepcopy(v), rnd), "vector")
    assert set(flatten.input_facts(v, prefixes(v))) == set(flatten.input_facts(w, prefixes(w)))
    assert corpus_interpreter().reply(w) == corpus_interpreter().reply(v)


# --- acceptance: what the checkers parse and admit, the driver flattens and places ---


def default_parse(path: Path) -> bool:
    """As both checkers parse a file (tools/check_corpus.py, tools/check_odrl22.py)."""
    try:
        Graph().parse(path)
    except Exception:  # noqa: BLE001
        return False
    return True


@pytest.mark.parametrize("path", TURTLE, ids=rel)
def test_acceptance(path: Path) -> None:
    text_ = path.read_text()
    parses = default_parse(path)
    if not parses:
        with pytest.raises(Exception):  # noqa: B017 -- any parse failure
            flatten.parse(text_)
        return
    # Every file that parses, a superset of what either checker admits, flattens and places.
    facts = flatten.policy_facts(flatten.parse(text_))
    table = values.value_facts(values.literals(facts))
    unplaceable = [f for f in table if f.match("unplaceable", 2)]
    if unplaceable:
        try:
            admitted = all(not r.failures() for r, _, _ in check_file(path, [], named=False))
        except Exception:  # noqa: BLE001
            admitted = False
        assert not admitted, unplaceable


# --- errors: a malformed input is refused, and nothing is guessed ---


def sections(**changes: Obj) -> Obj:
    v = copy.deepcopy(BASE)
    for name, change in changes.items():
        section = as_obj(v[name], name)
        for k, x in change.items():
            if x is None:
                section.pop(k, None)
            else:
                section[k] = x
    return v


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"request": {"colour": "red"}}, "request: unknown field 'colour'"),
        ({"request": {"action": None}}, "request: missing field 'action'"),
        ({"sotw": {"weather": {}}}, "sotw: unknown field 'weather'"),
        ({"sotw": {"facts": {"ex:x": {"status": "known"}}}}, "unknown status 'known'"),
        ({"sotw": {"facts": {"ex:x": {"values": []}}}}, "missing field 'status'"),
        (
            {"sotw": {"facts": {"ex:x": [{"source": "ex:s", "status": "missing"}] * 2}}},
            "a second answer from source",
        ),
        ({"sotw": {"facts": {"ex:x": [{"status": "missing"}]}}}, "missing field 'source'"),
        ({"request": {"params": {"ex:purpose": "ex:research"}}}, "expected an object, got str"),
        (
            {
                "request": {
                    "params": {"ex:n": {"@value": "1", "@type": "xsd:int", "@language": "en"}}
                }
            },
            "both @type and @language",
        ),
        ({"request": {"params": {"ex:n": {"@value": 1}}}}, "expected a string, got int"),
        (
            {
                "sotw": {
                    "evidence": [
                        {"id": "ex:e", "occurred_at": "2026-01-01T00:00:00Z", "actor": "ex:a"}
                    ]
                }
            },
            "missing field 'action'",
        ),
        (
            {
                "sotw": {
                    "evidence": [
                        {
                            "id": "ex:e",
                            "occurred_at": "2026-01-01T00:00:00Z",
                            "actor": "ex:a",
                            "action": "odrl:use",
                        }
                    ]
                    * 2
                }
            },
            "duplicate evidence id",
        ),
        (
            {"sotw": {"closure": [["odrl:partOf", "ex:a"]]}},
            "expected [relation, narrower, broader]",
        ),
        # #146: a name with an undeclared prefix, or none, equals no policy term, so it would
        # have made a part F where the caller meant a term. Without the check, each passes.
        ({"request": {"target": "asset:x"}}, "request.target: undeclared prefix 'asset'"),
        ({"request": {"action": "read"}}, "request.action: 'read' is neither an IRI"),
        ({"request": {"parties": {"zz:assignee": "ex:a"}}}, "request.parties: undeclared prefix"),
        ({"request": {"parties": {"odrl:assignee": "agent:a"}}}, "undeclared prefix 'agent'"),
        ({"request": {"params": {"zz:n": {"@value": "1"}}}}, "request.params: undeclared prefix"),
        (
            {"request": {"params": {"ex:n": {"@value": "1", "@type": "zz:int"}}}},
            "request.params.ex:n.@type: undeclared prefix 'zz'",
        ),
        (
            {"sotw": {"facts": {"zz:x": {"status": "missing"}}}},
            "sotw.facts: undeclared prefix 'zz'",
        ),
        (
            {"sotw": {"activation": {"zz:d": "2026-01-01T00:00:00Z"}}},
            "sotw.activation: undeclared prefix 'zz'",
        ),
    ],
)
def test_malformed_input(changes: dict[str, Obj], message: str) -> None:
    v = sections(**changes)
    with pytest.raises((ValueError, TypeError), match=re.escape(message)):
        flatten.input_facts(v, prefixes(v))
