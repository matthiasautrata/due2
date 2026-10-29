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
"""

from __future__ import annotations

import copy

import pytest
import rdflib
from harness.corpus import Vector, init_message, interpret_vectors

from clingo_i import flatten
from clingo_i.interpret import Interpreter
from clingo_i.json_types import as_list, as_obj, as_str

ODRL = "http://www.w3.org/ns/odrl/2/"
VECTORS = interpret_vectors()
INTERPRETER = Interpreter(init_message())


def leaky(vector: Vector) -> str:
    """`Q` for `vector`: an inert rule, and edges from the request's entities into its policies'."""
    request = as_obj(vector.input["request"], "request")
    graph = rdflib.Graph()
    for text in as_list(vector.input["policies"], "policies"):
        graph.parse(data=as_str(text, "policy"), format="turtle")
    lines = [
        f"@prefix odrl: <{ODRL}> .",
        "<urn:due2:l11:q> a odrl:Set ; odrl:permission <urn:due2:l11:rq> .",
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
