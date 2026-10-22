"""What the corpus cannot see (TESTS.md): integrity, declines, the explanation, and
a few verdicts that the other tests rely on."""

from __future__ import annotations

import pytest
from clingo import Control

from clingo_i.interpret import PROGRAM_FILES, VARIABLE_CAP, Interpreter, load_programs
from clingo_i.json_types import Json, Obj, as_obj
from tests.conftest import INIT, PREFIXES, PROF, vector

ODRL = "http://www.w3.org/ns/odrl/2/"
EX = "https://example.org/"


def verdict(reply: Obj) -> object:
    assert "output" in reply, reply
    out = reply["output"]
    assert isinstance(out, dict)
    assert out["frontier"] == [] and out["obligations"] == [] and out["exact"] is True
    return out["verdict"]


# --- verdicts the other tests stand on ---


@pytest.mark.parametrize(
    ("request_changes", "expected"),
    [
        ({}, "Permit"),  # play ⊑ use, target and assignee match
        ({"action": "odrl:use", "target": "ex:b"}, "Deny"),
        ({"action": "ex:other"}, "NotApplicable"),
        ({"target": None}, "Indeterminate"),  # absent target: the permission's part is u
        ({"parties": {}}, "Indeterminate"),  # absent assignee: the permission's party part is u
    ],
)
def test_verdicts(interpreter: Interpreter, request_changes: Obj, expected: str) -> None:
    v = vector(request={k: x for k, x in request_changes.items() if x is not None})
    request = v["request"]
    assert isinstance(request, dict)
    for k, x in request_changes.items():
        if x is None:
            del request[k]
    assert verdict(interpreter.reply(v)) == expected


def test_profile_subclass_and_conflict_default(interpreter: Interpreter) -> None:
    both = """
ex:p a {cls} ; {profile}
    odrl:permission ex:perm ; odrl:prohibition ex:forbid .
ex:perm a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a .
ex:forbid a odrl:Prohibition ; odrl:action odrl:use ; odrl:target ex:a .
"""
    # The profile types the policy (ex:Contract ⊑ odrl:Agreement) and defaults to prohibit.
    with_profile = PREFIXES + both.format(cls="ex:Contract", profile=f"odrl:profile <{PROF}> ;")
    assert verdict(interpreter.reply(vector(with_profile))) == "Deny"
    # No profile and no odrl:conflict: invalid, so the two applying rules void the policy.
    bare = PREFIXES + both.format(cls="odrl:Set", profile="")
    assert verdict(interpreter.reply(vector(bare))) == "NotApplicable"


def test_anonymous_rule(interpreter: Interpreter) -> None:
    policy = (
        PREFIXES
        + "ex:p a odrl:Set ; odrl:conflict odrl:prohibit ;"
        + " odrl:permission [ odrl:action odrl:use ; odrl:target ex:a ] .\n"
    )
    assert verdict(interpreter.reply(vector(policy))) == "Permit"


# --- integrity: a deleted rule is an error, never a verdict ---

DELETIONS = [
    ("kleene.lp", "rank(u, 1)."),
    ("applies.lp", "holds(part(X, action), f) :- atom(X), not action_matches(X)."),
    ("completion.lp", "completed(W, I, V) :- pre_in(W, I, 1), assigned(W, fin(I), V)."),
    (
        "resolve.lp",
        'verdict(W, "NotApplicable") :- world(W), not deny(W), not ready(W), not pending(W).',
    ),
]


@pytest.mark.parametrize(("file", "line"), DELETIONS)
def test_deleted_rule_fails_loudly(file: str, line: str) -> None:
    programs = load_programs()
    assert line in programs[file].splitlines(), f"{file} no longer has {line!r}"
    programs[file] = programs[file].replace(line, "")
    broken = Interpreter(INIT, programs)
    # Each vector exercises the deleted rule: an absent assignee gives a u part (kleene.lp),
    # which is opaque, so its atom's finding takes the value of the atom's own variable
    # (completion.lp); a foreign action gives an f part (applies.lp), and NotApplicable its rule
    # (resolve.lp).
    requests: dict[str, Obj] = {
        "kleene.lp": {"parties": {}},
        "applies.lp": {"action": "ex:other"},
        "completion.lp": {"parties": {}},
        "resolve.lp": {"action": "ex:other"},
    }
    reply = broken.reply(vector(request=requests[file]))
    assert "error" in reply, reply


def test_two_effects_fail_loudly() -> None:
    programs = load_programs()
    programs["explain.lp"] += "\natom_effect(X, forbid) :- atom(X).\n"
    assert "error" in Interpreter(INIT, programs).reply(vector())


def test_program_files_are_all_loaded() -> None:
    assert sorted(load_programs()) == sorted(PROGRAM_FILES)


# --- the explanation (due2-workflows.md §3.5, §3.7, §6.4; decisions/0011) ---


def explained(reply: Obj) -> Obj:
    """The output, with ex: names for refs, and without `unknown_parts`.

    `unknown_parts` has tests of its own (`test_unknown_parts`, `test_opaque_is_not_paired`), so
    the explanation tests here state only the verdict, its basis, eliminations, and range.
    """
    assert "output" in reply, reply
    out = reply["output"]
    assert isinstance(out, dict)
    hidden = ("frontier", "obligations", "exact", "unknown_parts")
    short = {k: v for k, v in out.items() if k not in hidden}
    return as_obj(_shorten(short), "output")


def _shorten(x: Json) -> Json:
    if isinstance(x, dict):
        return {k: _shorten(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_shorten(v) for v in x]
    return x.replace(EX, "ex:") if isinstance(x, str) else x


def policy(conflict: str, *rules: str) -> str:
    """A policy ex:p with the given conflict and rules, each `kind name target [assignee]`."""
    lines: list[str] = []
    refs: list[str] = []
    for spec in rules:
        kind, name, target, *who = spec.split()
        cls, link = (
            ("Permission", "permission") if kind == "perm" else ("Prohibition", "prohibition")
        )
        party = f" ; odrl:assignee ex:{who[0]}" if who else ""
        lines.append(
            f"ex:{name} a odrl:{cls} ; odrl:action odrl:use ; odrl:target ex:{target}{party} ."
        )
        refs.append(f"odrl:{link} ex:{name}")
    head = f"ex:p a odrl:Set ; odrl:conflict odrl:{conflict} ; " + " ; ".join(refs) + " .\n"
    return PREFIXES + head + "\n".join(lines) + "\n"


def basis(*rows: str) -> list[Obj]:
    return [{"ref": r, "role": role} for r, role in (row.split() for row in rows)]


def elims(*rows: str) -> list[Obj]:
    return [{"ref": r, "by": b, "rule": rule} for r, b, rule in (row.split() for row in rows)]


@pytest.mark.parametrize(
    ("request_changes", "expected"),
    [
        ({}, {"verdict": "Permit", "verdict_basis": basis("ex:perm permission"), "eliminated": []}),
        (
            {"action": "odrl:use", "target": "ex:b"},
            {"verdict": "Deny", "verdict_basis": basis("ex:forbid prohibition"), "eliminated": []},
        ),
        (
            {"action": "ex:other"},
            {"verdict": "NotApplicable", "verdict_basis": [], "eliminated": []},
        ),
    ],
)
def test_definite_basis(interpreter: Interpreter, request_changes: Obj, expected: Obj) -> None:
    assert explained(interpreter.reply(vector(request=request_changes))) == expected


def test_worked_example(interpreter: Interpreter) -> None:
    # DESIGN.md § Worked example: with no target, each atom's target part is opaque, so each
    # atom has a variable of its own, and four completions give three verdicts.
    v = vector()
    request = as_obj(v["request"], "request")
    del request["target"]
    reply = interpreter.reply(v)
    assert explained(reply) == {
        "verdict": "Indeterminate",
        "verdict_basis": basis("ex:forbid unknown", "ex:perm unknown"),
        "eliminated": [],
        "verdict_range": {"low": "Deny", "high": "Permit"},
    }
    assert unknown_parts(reply) == [
        ("ex:forbid", "odrl:target", "missing"),
        ("ex:perm", "odrl:target", "missing"),
    ]


NO_PARTY: Obj = {"target": "ex:a", "parties": {}}


@pytest.mark.parametrize(
    ("pol", "expected"),
    [
        # A u candidate is removed by a t prohibition under prohibit (0011 #4).
        (
            policy("prohibit", "perm perm a alice", "forbid forbid a"),
            {
                "verdict": "Deny",
                "verdict_basis": basis("ex:forbid prohibition"),
                "eliminated": elims("ex:perm ex:forbid prohibit"),
            },
        ),
        # A u prohibition beside a t candidate removes nothing, and leaves the verdict open.
        (
            policy("prohibit", "perm perm a", "forbid forbid a alice"),
            {
                "verdict": "Indeterminate",
                "verdict_basis": basis("ex:forbid unknown"),
                "eliminated": [],
                "verdict_range": {"low": "Deny", "high": "Permit"},
            },
        ),
        # An irrelevant u atom is not named: ex:other moves no verdict, ex:perm being t.
        (
            policy("prohibit", "perm perm a", "perm other a alice", "forbid forbid a bob"),
            {
                "verdict": "Indeterminate",
                "verdict_basis": basis("ex:forbid unknown"),
                "eliminated": [],
                "verdict_range": {"low": "Deny", "high": "Permit"},
            },
        ),
        (
            policy("prohibit", "forbid forbid a alice"),
            {
                "verdict": "Indeterminate",
                "verdict_basis": basis("ex:forbid unknown"),
                "eliminated": [],
                "verdict_range": {"low": "Deny", "high": "NotApplicable"},
            },
        ),
        # A void policy removes its u atoms too, by each t atom; a u atom removes nothing.
        (
            policy("invalid", "perm perm a", "forbid forbid a", "perm other a alice"),
            {
                "verdict": "NotApplicable",
                "verdict_basis": [],
                "eliminated": elims(
                    "ex:forbid ex:perm invalid",
                    "ex:other ex:forbid invalid",
                    "ex:other ex:perm invalid",
                    "ex:perm ex:forbid invalid",
                ),
            },
        ),
    ],
)
def test_explanation(interpreter: Interpreter, pol: str, expected: Obj) -> None:
    assert explained(interpreter.reply(vector(pol, request=NO_PARTY))) == expected


@pytest.mark.parametrize(
    ("pol", "request_changes"),
    [
        # Both rules read the absent target ex:a.
        (policy("perm", "perm perm a", "forbid forbid a"), {"target": None}),
        # Both rules read the unnamed assignee ex:alice.
        (policy("perm", "perm perm a alice", "forbid forbid a alice"), NO_PARTY),
    ],
)
def test_absent_fields_are_not_shared(
    interpreter: Interpreter, pol: str, request_changes: Obj
) -> None:
    # An absent field is missing, so opaque, and its parts share no variable (decisions/0016
    # #2). One shared variable would give both or neither, so NotApplicable..Permit under perm;
    # independent variables admit the forbid alone, so the range reaches Deny.
    v = vector(pol, request={k: x for k, x in request_changes.items() if x is not None})
    request = v["request"]
    assert isinstance(request, dict)
    if request_changes.get("target", "") is None:
        del request["target"]
    out = explained(interpreter.reply(v))
    assert out["verdict_range"] == {"low": "Deny", "high": "Permit"}
    assert out["verdict_basis"] == basis("ex:forbid unknown", "ex:perm unknown")


def test_same_rule_eliminations_are_dropped(interpreter: Interpreter) -> None:
    # Two actions give ex:perm two atoms; under invalid each removes the other, which the
    # authored level drops ("other than itself").
    pol = policy("invalid", "perm perm a", "forbid forbid a").replace(
        "odrl:action odrl:use ; odrl:target ex:a .\nex:forbid",
        "odrl:action odrl:use, odrl:play ; odrl:target ex:a .\nex:forbid",
    )
    assert "odrl:play" in pol
    out = explained(interpreter.reply(vector(pol)))
    assert out["eliminated"] == elims("ex:forbid ex:perm invalid", "ex:perm ex:forbid invalid")


def test_combination_rows_on_facts() -> None:
    # One policy per vector for now (structure.lp), so the cross-policy row is tested on facts:
    # q's t forbid removes p's u candidate; r's forbid, removed in r under perm, removes nothing.
    facts = """
atom(x). atom_effect(x, permit). atom_policy(x, p). atom_rule(x, "x"). holds(applies(x), u).
atom(y). atom_effect(y, forbid). atom_policy(y, q). atom_rule(y, "y"). holds(applies(y), t).
atom(z). atom_effect(z, forbid). atom_policy(z, r). atom_rule(z, "z"). holds(applies(z), t).
atom(w). atom_effect(w, permit). atom_policy(w, r). atom_rule(w, "w"). holds(applies(w), t).
conflict(p, prohibit). conflict(q, prohibit). conflict(r, perm).
"""
    ctl = Control([])
    ctl.add("base", [], facts + load_programs()["explain.lp"])
    ctl.ground([("base", [])])
    rows: set[str] = set()
    ctl.solve(on_model=lambda m: rows.update(str(s) for s in m.symbols(shown=True)))
    assert rows == {
        'elim(x,y,"prohibit-overrides")',
        'elim(w,y,"prohibit-overrides")',
        "elim(z,w,perm)",
    }


# --- constraints (due2-profiles.md §3 to §6) ---

XSD = "http://www.w3.org/2001/XMLSchema#"
DPROD = "https://ekgf.org/dprod/spec/develop/"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
CONSTRAINT_PREFIXES = (
    PREFIXES
    + f"@prefix dprod: <{DPROD}> .\n@prefix xsd: <{XSD}> .\n"
    + "@prefix due2: <https://w3id.org/due2/profile#> .\n"
)


def bound(op: str, source: str = "requestSource", extra: str = "") -> str:
    """The policy-layer binding of `ex:<op>`, reading property `ex:<op>` of `source`."""
    return f"ex:{op} dprod:operandSource dprod:{source} ; dprod:operandProperty ex:{op}{extra} .\n"


def constrained(constraint: str, *bindings: str, rule: str = "Permission") -> str:
    """A policy whose one rule, `ex:r`, has the constraint `constraint` and the bindings."""
    link = "permission" if rule == "Permission" else "prohibition"
    return (
        CONSTRAINT_PREFIXES
        + f"ex:p a odrl:Set ; odrl:conflict odrl:prohibit ; odrl:{link} ex:r .\n"
        + f"ex:r a odrl:{rule} ; odrl:action odrl:use ; odrl:target ex:a ;"
        + f" odrl:constraint {constraint} .\n"
        + "".join(bindings)
    )


def iri(name: str) -> Obj:
    return {"@id": name}


def typed(lex: str, datatype: str) -> Obj:
    return {"@value": lex, "@type": XSD + datatype}


def outcome(reply: Obj) -> object:
    """The verdict, the decline, or `"error"`: one value to compare in a table."""
    if "unsupported" in reply:
        return reply["unsupported"]
    if "error" in reply:
        return "error"
    return verdict(reply)


# DESIGN.md § `compare.lp`, the worked example: `and` is the least of its members, so an f
# member decides it whatever the u one is, and a u that decides the finding is completed: the
# permission applies in one completion and not in the other, so Indeterminate.
WORKED_CONSTRAINT = """ex:c .
ex:c odrl:and ( ex:c1 ex:c2 ) .
ex:c1 odrl:leftOperand ex:purpose ; odrl:operator odrl:isAnyOf ;
    odrl:rightOperand ex:research, ex:teaching .
ex:c2 odrl:leftOperand ex:count ; odrl:operator odrl:lteq ; odrl:rightOperand 5"""


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"ex:purpose": iri("ex:marketing")}, "NotApplicable"),  # f and u is f
        ({"ex:purpose": iri("ex:research")}, "Indeterminate"),  # t and u is u: Permit or not
        ({"ex:purpose": iri("ex:research"), "ex:count": typed("3", "integer")}, "Permit"),
        ({"ex:purpose": iri("ex:research"), "ex:count": typed("7", "integer")}, "NotApplicable"),
    ],
)
def test_constraint_worked_example(interpreter: Interpreter, params: Obj, expected: str) -> None:
    pol = constrained(WORKED_CONSTRAINT, bound("purpose"), bound("count"))
    assert outcome(interpreter.reply(vector(pol, request={"params": params}))) == expected


def leaf(operator: str, right: str) -> str:
    return f"[ odrl:leftOperand ex:x ; odrl:operator odrl:{operator} ; odrl:rightOperand {right} ]"


@pytest.mark.parametrize(
    ("constraint", "binding", "params", "expected"),
    [
        # Equality: IRIs by identity; an IRI against a literal is a misfit, so u.
        (leaf("eq", "ex:v"), "", {"ex:x": iri("ex:v")}, "Permit"),
        (leaf("eq", "ex:v"), "", {"ex:x": iri("ex:w")}, "NotApplicable"),
        (leaf("eq", "ex:v"), "", {"ex:x": typed("v", "string")}, "Indeterminate"),
        (leaf("neq", "ex:v"), "", {"ex:x": iri("ex:w")}, "Permit"),
        # Strings by code point; a language tag is part of the type.
        (leaf("eq", '"v"'), "", {"ex:x": {"@value": "v"}}, "Permit"),
        (leaf("eq", '"v"@en'), "", {"ex:x": {"@value": "v", "@language": "de"}}, "Indeterminate"),
        # Order within a space: by value, so 5 and 5.00 are equal under a numeric range.
        (leaf("lt", "5"), "", {"ex:x": typed("3", "integer")}, "Permit"),
        (leaf("gteq", "5"), "", {"ex:x": typed("3", "integer")}, "NotApplicable"),
        (leaf("eq", "5"), " ; rdfs:range xsd:decimal", {"ex:x": typed("5.00", "decimal")}, "Permit"),
        # Two spaces have no order: u.
        (leaf("lt", "5"), "", {"ex:x": typed("2026-01-01T00:00:00Z", "dateTime")}, "Indeterminate"),
        # The set operators, over a set-valued operand.
        (leaf("isAnyOf", "ex:v, ex:w"), "", {"ex:x": iri("ex:w")}, "Permit"),
        (leaf("isNoneOf", "ex:v, ex:w"), "", {"ex:x": iri("ex:w")}, "NotApplicable"),
        (leaf("isAllOf", "ex:v, ex:w"), " ; due2:cardinality due2:set",
         {"ex:x": [iri("ex:w"), iri("ex:v"), iri("ex:z")]}, "Permit"),
        (leaf("isAllOf", "ex:v, ex:w"), " ; due2:cardinality due2:set",
         {"ex:x": [iri("ex:w")]}, "NotApplicable"),
    ],
)  # fmt: skip
def test_operators(
    interpreter: Interpreter, constraint: str, binding: str, params: Obj, expected: str
) -> None:
    pol = constrained(constraint, bound("x", extra=binding))
    assert outcome(interpreter.reply(vector(pol, request={"params": params}))) == expected


HIERARCHY = """ex:docs a odrl:AssetCollection . ex:a1 odrl:partOf ex:docs .
ex:Report rdfs:subClassOf ex:Document .
"""


@pytest.mark.parametrize(
    ("constraint", "params", "sotw", "expected"),
    [
        # isPartOf and hasPart read the typed partOf closure, identity included.
        (leaf("isPartOf", "ex:docs"), {"ex:x": iri("ex:a1")}, {}, "Permit"),
        (leaf("isPartOf", "ex:docs"), {"ex:x": iri("ex:docs")}, {}, "Permit"),
        (leaf("isPartOf", "ex:docs"), {"ex:x": iri("ex:a2")}, {}, "NotApplicable"),
        (leaf("hasPart", "ex:a1"), {"ex:x": iri("ex:docs")}, {}, "Permit"),
        # An empty set is part of anything: the least over no values is t.
        (leaf("isPartOf", "ex:docs"), {"ex:x": []}, {}, "Permit"),
        # isA: an rdf:type edge, here from the SOTW closure, then rdfs:subClassOf edges.
        (leaf("isA", "ex:Document"), {"ex:x": iri("ex:r1")},
         {"closure": [[RDF_TYPE, "ex:r1", "ex:Report"]]}, "Permit"),
        (leaf("isA", "ex:Document"), {"ex:x": iri("ex:r1")}, {}, "NotApplicable"),
    ],
)  # fmt: skip
def test_hierarchy_operators(
    interpreter: Interpreter, constraint: str, params: Obj, sotw: Obj, expected: str
) -> None:
    card = " ; due2:cardinality due2:set" if isinstance(params["ex:x"], list) else ""
    pol = constrained(constraint, bound("x", extra=card)) + HIERARCHY
    reply = interpreter.reply(vector(pol, request={"params": params}, sotw=sotw))
    assert outcome(reply) == expected


SKOS = "http://www.w3.org/2004/02/skos/core#"
# A scheme ex:s of four concepts, each membership in another of the three forms: ex:low is
# below ex:top by two edges, one of them a skos:narrower triple; ex:other has no path to ex:top.
SCHEME = f"""@prefix skos: <{SKOS}> .
ex:s skos:hasTopConcept ex:top .
ex:top skos:narrower ex:mid . ex:mid skos:inScheme ex:s .
ex:low skos:broader ex:mid ; skos:inScheme ex:s .
ex:other skos:topConceptOf ex:s .
"""


@pytest.mark.parametrize(
    ("constraint", "scheme", "params", "sotw", "expected"),
    [
        # eq is ⊑: identity, one inverted narrower edge, two edges; no path is f.
        (leaf("eq", "ex:top"), True, iri("ex:top"), {}, "Permit"),
        (leaf("eq", "ex:top"), True, iri("ex:mid"), {}, "Permit"),
        (leaf("eq", "ex:top"), True, iri("ex:low"), {}, "Permit"),
        (leaf("eq", "ex:mid"), True, iri("ex:top"), {}, "NotApplicable"),
        (leaf("eq", "ex:top"), True, iri("ex:other"), {}, "NotApplicable"),
        # Without a scheme the same edges are not read: eq is identity.
        (leaf("eq", "ex:top"), False, iri("ex:low"), {}, "NotApplicable"),
        # The complements: "not ex:top" excludes everything below it.
        (leaf("neq", "ex:top"), True, iri("ex:low"), {}, "NotApplicable"),
        (leaf("isNoneOf", "( ex:top )"), True, iri("ex:low"), {}, "NotApplicable"),
        (leaf("isAnyOf", "( ex:other ex:top )"), True, iri("ex:low"), {}, "Permit"),
        # A read concept in no scheme is invalid, and a string is a misfit: u, never f.
        (leaf("eq", "ex:top"), True, iri("ex:new"), {}, "Indeterminate"),
        (leaf("neq", "ex:top"), True, iri("ex:new"), {}, "Indeterminate"),
        (leaf("eq", "ex:top"), True, typed("top", "string"), {}, "Indeterminate"),
        # The SOTW supplies a read concept's edges and membership; an edge alone is not enough.
        (leaf("eq", "ex:top"), True, iri("ex:new"),
         {"closure": [[SKOS + "broader", "ex:new", "ex:low"], [SKOS + "inScheme", "ex:new", "ex:s"]]},
         "Permit"),
        (leaf("eq", "ex:top"), True, iri("ex:new"),
         {"closure": [[SKOS + "broader", "ex:new", "ex:low"]]}, "Indeterminate"),
        # A right operand counts the declared memberships only: normalisation has no SOTW.
        (leaf("eq", "ex:new"), True, iri("ex:new"),
         {"closure": [[SKOS + "inScheme", "ex:new", "ex:s"]]}, "error"),
    ],
)  # fmt: skip
def test_concept_operators(
    interpreter: Interpreter, constraint: str, scheme: bool, params: Obj, sotw: Obj, expected: str
) -> None:
    extra = " ; due2:conceptScheme ex:s" if scheme else ""
    pol = constrained(constraint, bound("x", extra=extra)) + SCHEME
    reply = interpreter.reply(vector(pol, request={"params": {"ex:x": params}}, sotw=sotw))
    assert outcome(reply) == expected


def test_concept_broader_cycle(interpreter: Interpreter) -> None:
    # SKOS does not forbid a cycle of skos:broader edges. The closure is a least fixpoint, so it
    # terminates, and each concept of the cycle is below the other.
    pol = constrained(leaf("eq", "ex:a"), bound("x", extra=" ; due2:conceptScheme ex:s")) + (
        f"@prefix skos: <{SKOS}> .\n"
        + "ex:a skos:broader ex:b ; skos:inScheme ex:s . ex:b skos:broader ex:a ; skos:inScheme ex:s .\n"
    )
    reply = interpreter.reply(vector(pol, request={"params": {"ex:x": iri("ex:b")}}))
    assert outcome(reply) == "Permit"


@pytest.mark.parametrize(
    ("fact", "expected"),
    [
        ({"status": "resolved", "values": [iri("ex:v")]}, "Permit"),
        ({"status": "resolved", "values": [iri("ex:w")]}, "NotApplicable"),
        # Every other status, and no fact at all, is u: never f.
        ({"status": "missing"}, "Indeterminate"),
        ({"status": "invalid"}, "Indeterminate"),
        ({"status": "conflict", "values": [iri("ex:v"), iri("ex:w")]}, "Indeterminate"),
        ({"status": "unresolved"}, "Indeterminate"),
        (None, "Indeterminate"),
        # Two values for a one-valued operand (MultipleValues), and none.
        ({"status": "resolved", "values": [iri("ex:v"), iri("ex:w")]}, "Indeterminate"),
        ({"status": "resolved", "values": []}, "Indeterminate"),
    ],
)
def test_state_read(interpreter: Interpreter, fact: Obj | None, expected: str) -> None:
    pol = constrained(leaf("eq", "ex:v"), bound("x", "stateSource"))
    facts: Obj = {} if fact is None else {"ex:x": fact}
    assert outcome(interpreter.reply(vector(pol, sotw={"facts": facts}))) == expected


@pytest.mark.parametrize(
    ("constraint", "binding", "params", "expected"),
    [
        # A value outside the range is TypeMismatch: the read is u.
        (leaf("eq", "5"), " ; rdfs:range xsd:integer", {"ex:x": {"@value": "5"}}, "Indeterminate"),
        (leaf("eq", "ex:v"), " ; rdfs:range ex:Thing", {"ex:x": typed("5", "integer")},
         "Indeterminate"),
        # The context: the request's assignee, and the SOTW's clock.
        (leaf("eq", "ex:alice"), "", {}, "Permit"),
        (leaf("lt", '"2027-01-01T00:00:00Z"^^xsd:dateTime'), "", {}, "Permit"),
    ],
)  # fmt: skip
def test_reads(
    interpreter: Interpreter, constraint: str, binding: str, params: Obj, expected: str
) -> None:
    if params:
        b = bound("x", extra=binding)
    else:
        prop = "agent" if "alice" in constraint else "clock"
        b = f"ex:x dprod:operandSource dprod:contextSource ; dprod:operandProperty dprod:{prop} .\n"
    pol = constrained(constraint, b)
    assert outcome(interpreter.reply(vector(pol, request={"params": params}))) == expected


def test_prohibition_constraint(interpreter: Interpreter) -> None:
    pol = constrained(leaf("eq", "ex:v"), bound("x"), rule="Prohibition")
    assert outcome(interpreter.reply(vector(pol, request={"params": {"ex:x": iri("ex:v")}}))) == (
        "Deny"
    )


def test_refinement(interpreter: Interpreter) -> None:
    # A refinement is one conjunct of every atom with that action term (IM 2.2 §2.5).
    pol = (
        CONSTRAINT_PREFIXES
        + "ex:p a odrl:Set ; odrl:conflict odrl:prohibit ; odrl:permission ex:r .\n"
        + "ex:r a odrl:Permission ; odrl:target ex:a ;"
        + f" odrl:action [ rdf:value odrl:use ; odrl:refinement {leaf('eq', 'ex:v')} ] .\n"
        + bound("x")
    ).replace("@prefix rdfs:", "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n"
              "@prefix rdfs:")  # fmt: skip
    for value, expected in (("ex:v", "Permit"), ("ex:w", "NotApplicable")):
        v = vector(pol, request={"action": "odrl:use", "params": {"ex:x": iri(value)}})
        assert outcome(interpreter.reply(v)) == expected


def test_unit_labels_without_converting(interpreter: Interpreter) -> None:
    # odrl:unit joins the completion key only; the comparison reads the values alone.
    c = "[ odrl:leftOperand ex:x ; odrl:operator odrl:eq ; odrl:rightOperand 5 ; odrl:unit ex:EUR ]"
    v = vector(constrained(c, bound("x")), request={"params": {"ex:x": typed("5", "integer")}})
    assert outcome(interpreter.reply(v)) == "Permit"


# Each layer declares ex:x's property: the policy reads ex:fromPolicy, each profile the property
# its module names, and the core ex:fromCore. The request gives only the property `param`.
def layered_init(props: tuple[str, ...]) -> Obj:
    def decl(prop: str) -> str:
        return (
            CONSTRAINT_PREFIXES
            + f"ex:x dprod:operandSource dprod:requestSource ; dprod:operandProperty ex:{prop} .\n"
        )

    modules: Obj = {"core.ttl": decl("fromCore")}
    profiles: Obj = {}
    for i, prop in enumerate(props):
        modules[f"prof{i}.ttl"] = decl(prop)
        profiles[f"{PROF}{i}"] = [f"prof{i}.ttl"]
    return {"modules": modules, "core": ["core.ttl"], "profiles": profiles}


# decisions/0014: the highest layer that states the property gives it, and two profile modules
# have no order, so a difference between them is ConflictingProfileDeclaration. Without the last
# two rows, a resolution that let one module win, or that compared files rather than profiles,
# would pass.
@pytest.mark.parametrize(
    ("in_policy", "props", "param", "expected"),
    [
        (False, (), "fromCore", "Permit"),
        (False, ("fromProfile",), "fromProfile", "Permit"),
        (False, ("fromProfile",), "fromCore", "Indeterminate"),  # the profile's property wins
        (True, ("fromProfile",), "fromPolicy", "Permit"),
        (False, ("fromProfile", "fromProfile"), "fromProfile", "Permit"),  # modules agree
        (False, ("fromProfile", "fromOther"), "fromProfile", "error"),
    ],
)
def test_binding_layers(in_policy: bool, props: tuple[str, ...], param: str, expected: str) -> None:
    profile = "".join(f"ex:p odrl:profile <{PROF}{i}> .\n" for i in range(len(props)))
    own = (
        "ex:x dprod:operandSource dprod:requestSource ; dprod:operandProperty ex:fromPolicy .\n"
        if in_policy
        else ""
    )
    pol = constrained(leaf("eq", "ex:v"), own) + profile
    v = vector(pol, request={"action": "odrl:use", "params": {f"ex:{param}": iri("ex:v")}})
    reply = Interpreter(layered_init(props)).reply(v)
    assert outcome(reply) == expected
    if expected == "error":
        assert "ConflictingProfileDeclaration" in str(reply["error"]), reply


def test_profile_module_spans_files() -> None:
    # A profile's module may be several files, as DPROD's is: they are one layer, so one file
    # giving the source and another the property is one binding, not two modules that differ.
    init: Obj = {
        "modules": {
            "core.ttl": CONSTRAINT_PREFIXES,
            "a.ttl": CONSTRAINT_PREFIXES + "ex:x dprod:operandSource dprod:requestSource .\n",
            "b.ttl": CONSTRAINT_PREFIXES + "ex:x dprod:operandProperty ex:y .\n",
        },
        "core": ["core.ttl"],
        "profiles": {PROF: ["a.ttl", "b.ttl"]},
    }
    pol = constrained(leaf("eq", "ex:v")) + f"ex:p odrl:profile <{PROF}> .\n"
    v = vector(pol, request={"action": "odrl:use", "params": {"ex:y": iri("ex:v")}})
    assert outcome(Interpreter(init).reply(v)) == "Permit"


# The core owns ex:x's type: a decimal range, and the default cardinality. A policy may restate
# where ex:x reads, or a type attribute with the owner's value, but no other type (decisions/0014
# #1-#2). The default counts as stated: without the `set` row, a check that compared stated
# values only would pass.
@pytest.mark.parametrize(
    ("restated", "expected"),
    [
        ("dprod:operandSource dprod:requestSource ; dprod:operandProperty ex:y", "Permit"),
        ("rdfs:range xsd:decimal", "Permit"),
        ("due2:cardinality due2:one", "Permit"),
        ("rdfs:range xsd:string", "error"),
        ("due2:cardinality due2:set", "error"),
    ],
)
def test_retyped_operand(restated: str, expected: str) -> None:
    core = CONSTRAINT_PREFIXES + (
        "ex:x dprod:operandSource dprod:requestSource ; dprod:operandProperty ex:y ;"
        + " rdfs:range xsd:decimal .\n"
    )
    init: Obj = {"modules": {"core.ttl": core}, "core": ["core.ttl"], "profiles": {}}
    pol = constrained(leaf("eq", "5"), f"ex:x {restated} .\n")
    v = vector(pol, request={"action": "odrl:use", "params": {"ex:y": typed("5", "integer")}})
    reply = Interpreter(init).reply(v)
    assert outcome(reply) == expected
    if expected == "error":
        assert "RetypedOperand" in str(reply["error"]), reply


# A binding's range must be of the kind of the range of the property it reads (decisions/0014
# #5): integer and decimal are one kind, `rdfs:Literal` admits any literal but no IRI, and a date
# is not a number. An operand that reads itself is not compared with itself.
@pytest.mark.parametrize(
    ("op_range", "prop_range", "expected"),
    [
        ("xsd:integer", "xsd:decimal", "Permit"),
        ("xsd:integer", "rdfs:Literal", "Permit"),
        ("xsd:integer", "xsd:date", "error"),
        ("ex:Thing", "xsd:date", "error"),
        ("ex:Thing", "rdfs:Literal", "error"),
    ],
)
def test_operand_range_mismatch(op_range: str, prop_range: str, expected: str) -> None:
    b = f"ex:x dprod:operandSource dprod:requestSource ; dprod:operandProperty ex:y ; rdfs:range {op_range} .\n"
    pol = constrained(leaf("eq", "5"), b, f"ex:y rdfs:range {prop_range} .\n")
    v = vector(pol, request={"action": "odrl:use", "params": {"ex:y": typed("5", "integer")}})
    reply = Interpreter(INIT).reply(v)
    if expected == "error":
        assert "error" in reply and "OperandRangeMismatch" in str(reply["error"]), reply
    else:
        assert outcome(reply) == expected


@pytest.mark.parametrize(
    ("extra", "request_changes", "expected"),
    [
        # The requested asset is part of the target collection.
        ("ex:a a odrl:AssetCollection . ex:a1 odrl:partOf ex:a .", {"target": "ex:a1"}, "Permit"),
        ("ex:a a odrl:AssetCollection .", {"target": "ex:a1"}, "NotApplicable"),
        ("ex:a1 odrl:partOf ex:a .", {"target": "ex:a1"}, "odrl:partOf: untyped collection"),
        (
            "ex:a a odrl:AssetCollection . ex:bob a odrl:Party ; odrl:partOf ex:a .",
            {},
            "odrl:partOf: cross-kind edge",
        ),
        # The named party is part of the assignee collection.
        (
            (
                "ex:r odrl:assignee ex:team . ex:team a odrl:PartyCollection ."
                " ex:alice odrl:partOf ex:team ."
            ),
            {"target": "ex:a"},
            "Permit",
        ),
    ],
)
def test_typed_part_of(
    interpreter: Interpreter, extra: str, request_changes: Obj, expected: str
) -> None:
    pol = (
        CONSTRAINT_PREFIXES
        + "ex:p a odrl:Set ; odrl:conflict odrl:prohibit ; odrl:permission ex:r .\n"
        + "ex:r a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a .\n"
        + extra
        + "\n"
    )
    assert outcome(interpreter.reply(vector(pol, request=request_changes))) == expected


@pytest.mark.parametrize(
    ("constraint", "binding", "code"),
    [
        ("[ odrl:operator odrl:eq ; odrl:rightOperand ex:v ]", None, "MalformedConstraint"),
        ("[ odrl:leftOperand ex:x ; odrl:operator odrl:eq ]", "", "MalformedConstraint"),
        (leaf("eq", "ex:v, ex:w"), "", "MalformedConstraint"),
        (leaf("isAnyOf", "( ex:v ), ex:w"), "", "MalformedConstraint"),
        ("[ odrl:leftOperand ex:x ; odrl:operator ex:near ; odrl:rightOperand 5 ]", "",
         "UnsupportedOperator"),
        (f"[ odrl:andSequence ( {leaf('eq', 'ex:v')} ) ]", "", "UnsupportedConnective"),
        (leaf("eq", '"1.5"^^xsd:double'), "", "FloatingPointOperand"),
        (leaf("lt", '"P1M1D"^^xsd:duration'), "", "MixedDuration"),
        (leaf("eq", "ex:v"), None, "UnboundLeftOperand"),
        (leaf("eq", "ex:v"), "ex:x dprod:operandSource ex:elsewhere ; dprod:operandProperty ex:x .\n",
         "InvalidBinding"),
        (leaf("eq", "ex:v"),
         "ex:x dprod:operandSource due2:witnessSource ; dprod:operandProperty ex:x .\n",
         "WitnessOutsideDuty"),
        (leaf("eq", "ex:v"), bound("x", extra=" ; due2:allowedOperator odrl:neq"),
         "OperatorTypeMismatch"),
        (leaf("eq", "5"), bound("x", extra=" ; rdfs:range ex:Thing"), "OperatorTypeMismatch"),
        # The empty list on a set-based operator (decisions/0013, amendment).
        (leaf("isAnyOf", "()"), "", "MalformedConstraint"),
        (leaf("isNoneOf", "()"), "", "MalformedConstraint"),
        # A concept-scheme operand (decisions/0015 #8): an IRI right operand in no scheme, an
        # operator that reads no hierarchy, and a datatype range.
        (leaf("eq", "ex:v"), bound("x", extra=" ; due2:conceptScheme ex:s"), "OperatorTypeMismatch"),
        (leaf("lt", "ex:top"), bound("x", extra=" ; due2:conceptScheme ex:s") + SCHEME,
         "OperatorTypeMismatch"),
        (leaf("eq", '"v"'), bound("x", extra=" ; due2:conceptScheme ex:s ; rdfs:range xsd:string"),
         "InvalidBinding"),
    ],
)  # fmt: skip
def test_constraint_rejections(
    interpreter: Interpreter, constraint: str, binding: str | None, code: str
) -> None:
    b = bound("x") if binding == "" else (binding or "")
    reply = interpreter.reply(vector(constrained(constraint, b)))
    assert "error" in reply and code in str(reply["error"]), reply


@pytest.mark.parametrize("rule", ["Permission", "Prohibition"])
@pytest.mark.parametrize(
    "constraint",
    [
        "[ odrl:and () ]",
        "[ odrl:or () ]",
        "[ odrl:xone () ]",
        "[ dprod:not () ]",
        f"[ odrl:and ( {leaf('eq', 'ex:v')} ), () ]",
    ],
)
def test_empty_connective_rejected(interpreter: Interpreter, constraint: str, rule: str) -> None:
    """A connective over the empty list is malformed (decisions/0017).

    Without the rejection, `and ()` took the identity `t` and the rule applied to every request
    (`Permit`, or `Deny` for a prohibition), `or ()` and `xone ()` took `f` and the rule never
    applied, and `not ()` was declined.
    """
    reply = interpreter.reply(vector(constrained(constraint, bound("x"), rule=rule)))
    assert "error" in reply and "MalformedConstraint" in str(reply["error"]), reply


@pytest.mark.parametrize(
    "constraint",
    [
        "ex:c . ex:c odrl:and ( ex:d ex:d ) . ex:d " + leaf("eq", "ex:v")[1:-1],
        "ex:c . ex:c odrl:xone ( ex:d ex:e ex:d ) . ex:d " + leaf("eq", "ex:v")[1:-1]
        + " . ex:e " + leaf("eq", "ex:w")[1:-1],
        f"[ odrl:xone ( {leaf('eq', 'ex:v')} {leaf('eq', 'ex:w')} {leaf('eq', 'ex:v')} ) ]",
        f"[ odrl:xone ( {leaf('isAnyOf', '( ex:v ex:w )')} {leaf('isAnyOf', '( ex:w ex:v )')} ) ]",
    ],
)  # fmt: skip
def test_repeated_member_rejected(interpreter: Interpreter, constraint: str) -> None:
    """A list that names a node twice, or an `xone` that states a leaf twice (decisions/0022).

    Both are malformed, and the right operand values compare as a set. Without the rejection, `member/2` held each repeat once, so `xone ( ex:d ex:e ex:d )` took
    the value of `xone ( ex:d ex:e )`, where W1's expansion reads three positions.
    """
    reply = interpreter.reply(vector(constrained(constraint, bound("x"))))
    assert "error" in reply and "MalformedConstraint" in str(reply["error"]), reply


@pytest.mark.parametrize(
    "constraint",
    [
        f"[ odrl:and ( {leaf('eq', 'ex:v')} {leaf('eq', 'ex:v')} ) ]",
        f"[ odrl:xone ( {leaf('eq', 'ex:v')} {leaf('neq', 'ex:v')} ) ]",
        f"[ odrl:xone ( {leaf('isAnyOf', '( ex:v ex:w )')} {leaf('isAnyOf', '( ex:v )')} ) ]",
    ],
)  # fmt: skip
def test_distinct_or_idempotent_members_admitted(interpreter: Interpreter, constraint: str) -> None:
    # Same-content leaves under `and` or `or` are admitted, and so are xone leaves that differ
    # only in operator or in one right operand value (decisions/0022).
    pol = constrained(constraint, bound("x"))
    reply = interpreter.reply(vector(pol, request={"params": {"ex:x": iri("ex:v")}}))
    assert "output" in reply, reply


@pytest.mark.parametrize(
    ("constraint", "binding", "reason"),
    [
        ("[ odrl:leftOperand ex:x ; odrl:operator odrl:eq ; odrl:rightOperand ex:v ;"
         + f" odrl:and ( {leaf('eq', 'ex:v')} ) ]", "", "constraint: leaf with a connective"),
        (f"[ odrl:and ( {leaf('eq', 'ex:v')} ) ; odrl:or ( {leaf('eq', 'ex:w')} ) ]", "",
         "constraint: two connectives"),
        (f"[ dprod:not ( {leaf('eq', 'ex:v')} {leaf('eq', 'ex:w')} ) ]", "",
         "constraint: dprod:not with several members"),
        ("ex:c . ex:c odrl:or ( ex:c ex:d ) . ex:d " + leaf("eq", "ex:v")[1:-1], "",
         "constraint: cycle"),
        (leaf("eq", "()"), "", "constraint: list on a scalar operator"),
        (leaf("eq", "( ex:v )"), "", "constraint: list on a scalar operator"),
        (leaf("eq", "ex:v"), " ; due2:cardinality due2:set",
         "constraint: set-valued operand on a single-value operator"),
        (leaf("eq", "ex:v"), " ; due2:cardinality due2:many", "binding: cardinality"),
        (leaf("eq", "ex:v"), " ; rdfs:range xsd:integer, xsd:string", "binding: range"),
    ],
)  # fmt: skip
def test_constraint_declines(
    interpreter: Interpreter, constraint: str, binding: str, reason: str
) -> None:
    v = vector(constrained(constraint, bound("x", extra=binding)))
    assert interpreter.reply(v) == {"unsupported": reason}


CONSTRAINT_DELETIONS = [
    ("compare.lp", "crank(W, C, N) :- op(C, eq), cpair(W, C, Lv, Rv), ceqr(C, Lv, Rv, N)."),
    ("operand.lp", "read_u(W, Op) :- read_in(W, Op), not read_resolved(W, Op)."),
]


@pytest.mark.parametrize(("file", "line"), CONSTRAINT_DELETIONS)
def test_deleted_constraint_rule_fails_loudly(file: str, line: str) -> None:
    # A leaf without a rank, or a read neither ok nor u, fails integrity.lp in solve 2. The
    # `or` has a t member that the deleted rule does not touch (ex:y neq for compare.lp, ex:x eq
    # for operand.lp, ex:y unread), so the intact program gives a definite verdict, and only the
    # deleted rule can turn the reply into an error.
    programs = load_programs()
    assert line in programs[file].splitlines(), f"{file} no longer has {line!r}"
    programs[file] = programs[file].replace(line, "")
    c = f"[ odrl:or ( {leaf('eq', 'ex:v')} {leaf('neq', 'ex:w').replace('ex:x', 'ex:y')} ) ]"
    params: Obj = {"ex:x": iri("ex:v")}
    if file == "compare.lp":
        params["ex:y"] = iri("ex:v")
    v = vector(constrained(c, bound("x"), bound("y")), request={"params": params})
    assert "output" in Interpreter(INIT).reply(v)
    assert "error" in Interpreter(INIT, programs).reply(v)


def test_datatypes_differ_without_a_range(interpreter: Interpreter) -> None:
    # With no range, values of one kind compare by value (decisions/0014 #6), so 5 = 5.0. A value
    # of another kind is a misfit: a string "5" is not a number, so u, and the two completions disagree.
    v = vector(
        constrained(leaf("eq", "5"), bound("x")),
        request={"params": {"ex:x": typed("5.0", "decimal")}},
    )
    assert outcome(interpreter.reply(v)) == "Permit"
    v = vector(
        constrained(leaf("eq", "5"), bound("x")),
        request={"params": {"ex:x": typed("5", "string")}},
    )
    assert outcome(interpreter.reply(v)) == "Indeterminate"


# --- the completion key (due2-workflows.md §6.4; completion.lp) ---

RDF_PREFIX = "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n"


def two_rules(c1: str, c2: str, kind: str = "Permission", refine: bool = False) -> str:
    """Rules ex:r1 under `c1` and ex:r2 under `c2`, both of `kind`, reading ex:x and ex:y.

    Both operands read the state, and a vector with no fact for them leaves them
    `unresolved`, so their leaves are paired (completion.lp).

    With `refine`, `c2` refines ex:r2's action instead of constraining the rule.
    """
    link = kind.lower()
    r2 = f"ex:r2 a odrl:{kind} ; odrl:target ex:a ;" + (
        f" odrl:action [ rdf:value odrl:use ; odrl:refinement {c2} ] .\n"
        if refine
        else f" odrl:action odrl:use ; odrl:constraint {c2} .\n"
    )
    return (
        CONSTRAINT_PREFIXES
        + RDF_PREFIX
        + f"ex:p a odrl:Set ; odrl:conflict odrl:perm ; odrl:{link} ex:r1, ex:r2 .\n"
        + f"ex:r1 a odrl:{kind} ; odrl:action odrl:use ; odrl:target ex:a ;"
        + f" odrl:constraint {c1} .\n"
        + r2
        + bound("x", "stateSource")
        + bound("y", "stateSource")
    )


def unit(operator: str, right: str, iri: str) -> str:
    return leaf(operator, right)[:-1] + f"; odrl:unit {iri} ]"


# With no fact for ex:x, every leaf is u and unresolved. Two leaves are one variable when every
# part of the key matches; a complement reads it negatively, so r1 or r2 applies in every
# completion: Permit.
# Any other difference makes two variables, and the completion where both are f gives
# NotApplicable. Without the rows that differ, a key that merged too much would pass; without
# the rows that agree, one variable per leaf would.
@pytest.mark.parametrize(
    ("c1", "c2", "refine", "expected"),
    [
        (leaf("eq", "5"), leaf("neq", "5"), False, "Permit"),
        (leaf("lt", "5"), leaf("gteq", "5"), False, "Permit"),
        (leaf("lteq", "5"), leaf("gt", "5"), False, "Permit"),
        # A set right operand is a set: its order and repetition do not matter.
        (leaf("isAnyOf", "ex:v, ex:w"), leaf("isNoneOf", "( ex:w ex:v )"), False, "Permit"),
        (unit("eq", "5", "ex:EUR"), unit("neq", "5", "ex:EUR"), False, "Permit"),
        # ex:y reads another property, so another value.
        (leaf("eq", "5"), leaf("neq", "5").replace("ex:x", "ex:y"), False, "Indeterminate"),
        (leaf("eq", "5"), leaf("neq", "6"), False, "Indeterminate"),
        (leaf("eq", "5"), leaf("lt", "5"), False, "Indeterminate"),
        (leaf("eq", "5"), unit("neq", "5", "ex:EUR"), False, "Indeterminate"),
        (unit("eq", "5", "ex:EUR"), unit("neq", "5", "ex:USD"), False, "Indeterminate"),
        # Right operands compare as terms, so 5 and 5.0 are two variables (completion.lp).
        (leaf("eq", "5"), leaf("neq", "5.0"), False, "Indeterminate"),
        (leaf("isAnyOf", "ex:v, ex:w"), leaf("isNoneOf", "ex:v"), False, "Indeterminate"),
        # A rule's constraint and an action's refinement are different scopes.
        (leaf("eq", "5"), leaf("neq", "5"), True, "Indeterminate"),
    ],
)
def test_completion_key(
    interpreter: Interpreter, c1: str, c2: str, refine: bool, expected: str
) -> None:
    pol = two_rules(c1, c2, refine=refine)
    assert outcome(interpreter.reply(vector(pol))) == expected


def test_binding_not_operand_iri(interpreter: Interpreter) -> None:
    # ex:y bound to ex:x's property reads the same value, so the leaves share a variable.
    pol = two_rules(leaf("eq", "5"), leaf("neq", "5").replace("ex:x", "ex:y")).replace(
        "ex:y dprod:operandSource dprod:stateSource ; dprod:operandProperty ex:y",
        "ex:y dprod:operandSource dprod:stateSource ; dprod:operandProperty ex:x",
    )
    assert outcome(interpreter.reply(vector(pol))) == "Permit"


@pytest.mark.parametrize(
    ("c1", "c2", "kind", "expected"),
    [
        # A permission whose tree is u holds in every completion: the u atom is in the basis.
        (
            f"[ odrl:or ( {leaf('eq', '5')} {leaf('neq', '5')} ) ]",
            leaf("eq", "6"),
            "Permission",
            {
                "verdict": "Permit",
                "verdict_basis": basis("ex:r1 permission"),
                "eliminated": [],
            },
        ),
        # One rule applies in each completion, a different one in each: no rule applies in
        # every completion, so the basis is empty. The permissions are DESIGN.md's example in
        # § completion.lp.
        (
            leaf("eq", "5"),
            leaf("neq", "5"),
            "Permission",
            {"verdict": "Permit", "verdict_basis": [], "eliminated": []},
        ),
        (
            leaf("eq", "5"),
            leaf("neq", "5"),
            "Prohibition",
            {"verdict": "Deny", "verdict_basis": [], "eliminated": []},
        ),
    ],
)
def test_completed_basis(
    interpreter: Interpreter, c1: str, c2: str, kind: str, expected: Obj
) -> None:
    pol = two_rules(c1, c2, kind)
    assert explained(interpreter.reply(vector(pol))) == expected


def test_node_in_two_scopes(interpreter: Interpreter) -> None:
    # One node as a rule's constraint and as an action's refinement (constraint.lp).
    pol = two_rules("ex:c", "ex:c", refine=True) + f"ex:c {leaf('eq', '5')[1:-1]} .\n"
    assert interpreter.reply(vector(pol)) == {"unsupported": "constraint: node in two scopes"}


@pytest.mark.parametrize(
    ("n", "expected"), [(VARIABLE_CAP, "Indeterminate"), (VARIABLE_CAP + 1, "variable-cap")]
)
def test_variable_cap(interpreter: Interpreter, n: int, expected: str) -> None:
    # An or of n leaves with n right operands, each leaf twice, on an unresolved operand: n
    # variables. The repeats leave ground `var/1` atoms no model makes true, so a cap on the
    # ground atoms would decline both.
    leaves = " ".join(leaf("eq", str(i)) for i in range(n) for _ in range(2))
    pol = constrained(f"[ odrl:or ( {leaves} ) ]", bound("x", "stateSource"))
    assert outcome(interpreter.reply(vector(pol))) == expected


def unknown_parts(reply: Obj) -> list[tuple[str, str, str]]:
    """The reply's `unknown_parts` as `(ref, input, status)` rows with short names, sorted.

    The reply sorts its rows by their full IRIs, which this checks before shortening them.
    """
    out = as_obj(reply["output"], "output")
    rows = out["unknown_parts"]
    assert isinstance(rows, list)
    triples: list[tuple[str, str, str]] = []
    for row in rows:
        r = as_obj(row, "unknown part")
        ref, i, status = r["ref"], r["input"], r["status"]
        assert isinstance(ref, str) and isinstance(i, str) and isinstance(status, str)
        triples.append((ref, i, status))
    assert triples == sorted(triples)
    short = {"ex:": EX, "odrl:": ODRL}
    for name, ns in short.items():
        triples = [(r.replace(ns, name), i.replace(ns, name), st) for r, i, st in triples]
    return sorted(triples)


def lt_or_gteq(source: str) -> str:
    """decisions/0016's example: permissions ex:r1 `x lt 5` and ex:r2 `x gteq 5`, x on `source`."""
    pol = two_rules(leaf("lt", "5"), leaf("gteq", "5"))
    return pol.replace(
        "ex:x dprod:operandSource dprod:stateSource", f"ex:x dprod:operandSource dprod:{source}"
    )


# decisions/0016's example. Only an unresolved value is paired: then exactly one of lt and gteq
# holds, so Permit. A missing value or a misfit (a string, an IRI) fits neither, so each rule's
# leaf is opaque, each atom completes on its own, and the completion where neither applies gives
# NotApplicable. Before decisions/0016 the last three rows were a definite Permit with nothing
# reported. Every u part is named, under a definite verdict too.
@pytest.mark.parametrize(
    ("source", "value", "expected", "status"),
    [
        ("requestSource", typed("3", "integer"), "Permit", None),
        ("requestSource", None, "Indeterminate", "missing"),
        ("requestSource", {"@value": "abc"}, "Indeterminate", "misfit"),
        ("requestSource", iri("ex:v"), "Indeterminate", "misfit"),
        ("stateSource", None, "Permit", "unresolved"),
    ],
)  # fmt: skip
def test_opaque_is_not_paired(
    interpreter: Interpreter, source: str, value: Obj | None, expected: str, status: str | None
) -> None:
    params: Obj = {} if value is None else {"ex:x": value}
    reply = interpreter.reply(vector(lt_or_gteq(source), request={"params": params}))
    assert outcome(reply) == expected
    if expected == "Indeterminate":
        out = explained(reply)
        assert out["verdict_range"] == {"low": "NotApplicable", "high": "Permit"}
    rows = [] if status is None else [("ex:r1", "ex:x", status), ("ex:r2", "ex:x", status)]
    assert unknown_parts(reply) == rows


# Each status of due2-profiles.md §3 is reported as the operand's read gives it, and an absent
# target or party names the field it reads. The last row is an atom that is f (a foreign
# action): its u parts are not reported, because an index may skip it (decisions/0016,
# amendment). Without these rows a status could be reported as another, or an f atom's parts
# reported.
@pytest.mark.parametrize(
    ("changes", "fact", "expected"),
    [
        ({}, {"status": "missing"}, [("ex:r", "ex:x", "missing")]),
        ({}, {"status": "invalid"}, [("ex:r", "ex:x", "invalid")]),
        ({}, {"status": "conflict", "values": [iri("ex:v"), iri("ex:w")]},
         [("ex:r", "ex:x", "conflict")]),
        ({}, {"status": "unresolved"}, [("ex:r", "ex:x", "unresolved")]),
        ({}, None, [("ex:r", "ex:x", "unresolved")]),
        ({}, {"status": "resolved", "values": []}, [("ex:r", "ex:x", "missing")]),
        ({}, {"status": "resolved", "values": [iri("ex:v"), iri("ex:w")]},
         [("ex:r", "ex:x", "conflict")]),
        ({}, {"status": "resolved", "values": [typed("5", "integer")]},
         [("ex:r", "ex:x", "misfit")]),
        ({}, {"status": "resolved", "values": [iri("ex:v")]}, []),
        ({"target": None}, {"status": "resolved", "values": [iri("ex:v")]},
         [("ex:r", "odrl:target", "missing")]),
        ({"parties": {}}, {"status": "resolved", "values": [iri("ex:v")]},
         [("ex:r", "odrl:assignee", "missing")]),
        ({"action": "ex:other", "parties": {}}, None, []),
    ],
)  # fmt: skip
def test_unknown_parts(
    interpreter: Interpreter, changes: Obj, fact: Obj | None, expected: list[tuple[str, str, str]]
) -> None:
    pol = constrained(leaf("eq", "ex:v"), bound("x", "stateSource")).replace(
        "odrl:target ex:a ;", "odrl:target ex:a ; odrl:assignee ex:alice ;"
    )
    facts: Obj = {} if fact is None else {"ex:x": fact}
    v = vector(pol, request={k: x for k, x in changes.items() if x is not None},
               sotw={"facts": facts})  # fmt: skip
    request = as_obj(v["request"], "request")
    for k, x in changes.items():
        if x is None:
            del request[k]
    assert unknown_parts(interpreter.reply(v)) == expected


def test_decided_leaf_is_reported(interpreter: Interpreter) -> None:
    # A t atom whose or has a t member and a u leaf: the u leaf decides nothing, and is
    # reported (due2-workflows.md §3.5). Reporting only u atoms would drop it.
    y = "[ odrl:leftOperand ex:y ; odrl:operator odrl:eq ; odrl:rightOperand ex:w ]"
    pol = constrained(
        f"[ odrl:or ( {leaf('eq', 'ex:v')} {y} ) ]", bound("x"), bound("y", "stateSource")
    )
    reply = interpreter.reply(vector(pol, request={"params": {"ex:x": iri("ex:v")}}))
    assert outcome(reply) == "Permit"
    assert unknown_parts(reply) == [("ex:r", "ex:y", "unresolved")]


XT, XT2, XF = leaf("eq", "ex:v"), leaf("neq", "ex:w"), leaf("eq", "ex:w")  # ex:x = ex:v: t, t, f
Y, Z = (leaf("eq", "ex:v").replace("ex:x", f"ex:{op}") for op in ("y", "z"))


# A u leaf is named iff it lies in a disjunct of the rule's DNF that is not f
# (due2-workflows.md §3.5): through not, and, or, and both polarities of xone
# (due2-profiles.md §5). Each row joins
# z, always live, by or, so the rule stays u. In the first five, ex:y lies only in f disjuncts;
# in the last two, it lies in a u one. Named by tree membership, the first five would name
# ex:y too; read without the flip of polarity at not, the second and fifth would.
@pytest.mark.parametrize(
    ("dead", "named"),
    [(f"[ odrl:and ( {XF} {Y} ) ]", ["z"]),
     (f"[ dprod:not ( [ odrl:or ( {XT} {Y} ) ] ) ]", ["z"]),
     (f"[ dprod:not ( [ dprod:not ( [ odrl:and ( {XF} {Y} ) ] ) ] ) ]", ["z"]),
     (f"[ odrl:xone ( {XT} {XT2} {Y} ) ]", ["z"]),
     (f"[ dprod:not ( [ odrl:xone ( {XT} [ odrl:and ( {XF} {Y} ) ] ) ] ) ]", ["z"]),
     (f"[ odrl:and ( {XT} {Y} ) ]", ["y", "z"]),
     (f"[ dprod:not ( [ odrl:xone ( {XT} {Y} ) ] ) ]", ["y", "z"])],
)  # fmt: skip
def test_leaf_in_f_disjuncts_only_is_not_reported(
    interpreter: Interpreter, dead: str, named: list[str]
) -> None:
    pol = constrained(
        f"[ odrl:or ( {dead} {Z} ) ]", bound("x"), bound("y", "stateSource"),
        bound("z", "stateSource"),
    )  # fmt: skip
    reply = interpreter.reply(vector(pol, request={"params": {"ex:x": iri("ex:v")}}))
    assert unknown_parts(reply) == [("ex:r", f"ex:{op}", "unresolved") for op in named]


def test_invalid_read_is_reported(interpreter: Interpreter) -> None:
    # A request value outside the operand's range is non-conforming (due2-profiles.md §3).
    pol = constrained(leaf("eq", "5"), bound("x", extra=" ; rdfs:range xsd:integer"))
    reply = interpreter.reply(vector(pol, request={"params": {"ex:x": {"@value": "5"}}}))
    assert unknown_parts(reply) == [("ex:r", "ex:x", "invalid")]


def test_derived_strings_decline(interpreter: Interpreter) -> None:
    # xsd:token and xsd:string are one kind, compared by value after the whitespace facet, which
    # the spike does not apply (compare.lp).
    v = vector(
        constrained(leaf("eq", '"a"'), bound("x")),
        request={"params": {"ex:x": typed("a", "token")}},
    )
    assert interpreter.reply(v) == {"unsupported": "value: derived string datatypes"}


# --- declines ---


def test_decline_names_smallest_unsupported_iri(interpreter: Interpreter) -> None:
    policy = (
        PREFIXES
        + """
ex:p a odrl:Set ; odrl:conflict odrl:prohibit ; odrl:permission ex:perm ;
    odrl:inheritFrom ex:q .
ex:perm a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a ;
    odrl:remedy [ odrl:action odrl:compensate ] .
"""
    )
    # odrl:inheritFrom < odrl:remedy in code-point order.
    first = interpreter.reply(vector(policy))
    assert first == {"unsupported": ODRL + "inheritFrom"}
    assert interpreter.reply(vector(policy)) == first


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        ("ex:perm ex:weird ex:x .", {"unsupported": EX + "weird"}),  # unknown, on a rule
        ("ex:a odrl:hasPolicy ex:p .", {"unsupported": ODRL + "hasPolicy"}),  # vocabulary, anywhere
        ('ex:p rdfs:label "p" ; dct:title "t" .', None),  # annotations on the policy
        ('ex:a ex:colour "red" .', None),  # data on an asset node: never read
    ],
)
def test_decline_rule(interpreter: Interpreter, extra: str, expected: Obj | None) -> None:
    reply = interpreter.reply(vector(PREFIXES + POLICY_BODY + extra + "\n"))
    if expected is None:
        assert verdict(reply) == "Permit"
    else:
        assert reply == expected


POLICY_BODY = """
ex:p a odrl:Set ; odrl:conflict odrl:prohibit ; odrl:permission ex:perm .
ex:perm a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a .
"""


EVIDENCE: Obj = {
    "id": "ex:e1",
    "occurred_at": "2026-05-01T00:00:00Z",
    "actor": "ex:alice",
    "action": "odrl:compensate",
}


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"sotw": {"closure": [["ex:knows", "ex:a", "ex:b"]]}}, "sotw.closure"),  # not a hierarchy
        ({"config": {"combination": "permit-overrides"}}, "config.combination"),
        ({"config": {"preference": "ex:p"}}, "config.preference"),
        # The smallest field wins, whatever the section order.
        (
            {
                "sotw": {"closure": [["ex:knows", "ex:a", "ex:b"]]},
                "config": {"combination": "permit-overrides"},
            },
            "config.combination",
        ),
        # A value the program compares, and cannot place (DESIGN.md § Values).
        ({"request": {"at": "2026-06-01T00:00:00"}}, "value: dateTime without timezone"),
        ({"sotw": {"effective_at": "2026-13-01T00:00:00Z"}}, "value: ill-typed xsd:dateTime"),
        # The input declines come first.
        (
            {
                "request": {"at": "2026-06-01T00:00:00"},
                "config": {"combination": "permit-overrides"},
            },
            "config.combination",
        ),
    ],
)
def test_input_declines(interpreter: Interpreter, changes: dict[str, Obj], reason: str) -> None:
    assert interpreter.reply(vector(**changes)) == {"unsupported": reason}


def test_empty_fields_are_not_declined(interpreter: Interpreter) -> None:
    v = vector(request={"params": {}}, sotw={"facts": {}, "evidence": [], "closure": []})
    assert verdict(interpreter.reply(v)) == "Permit"


@pytest.mark.parametrize(
    "changes",
    [
        {"sotw": {"evidence": [EVIDENCE]}},
        {"sotw": {"activation": {"ex:d": "2026-01-01T00:00:00Z"}}},
        {"config": {"signers": [{"duty": "ex:d", "issuer": "ex:bank"}]}},
        {"config": {"violations": "deny"}},
    ],
)
def test_duty_inputs_are_read(interpreter: Interpreter, changes: dict[str, Obj]) -> None:
    # The fields duty.lp and resolve.lp read are not declined, and without a duty they change
    # nothing. Had lift.lp kept their declines, each would reply `unsupported`.
    assert verdict(interpreter.reply(vector(**changes))) == "Permit"


def test_policy_declines_come_first(interpreter: Interpreter) -> None:
    policy = PREFIXES + POLICY_BODY + "ex:forbid odrl:remedy [ odrl:action odrl:compensate ] .\n"
    v = vector(policy, sotw={"closure": [["ex:knows", "ex:a", "ex:b"]]})
    assert interpreter.reply(v) == {"unsupported": ODRL + "remedy"}


def test_uncompared_unplaceable_literal(interpreter: Interpreter) -> None:
    # An annotation is never compared, so a value it cannot place does not decline.
    tzless = '"2026-01-01T00:00:00"^^<http://www.w3.org/2001/XMLSchema#dateTime>'
    policy = PREFIXES + POLICY_BODY + f"ex:p dct:issued {tzless} .\n"
    assert verdict(interpreter.reply(vector(policy))) == "Permit"


# --- errors ---


def test_unknown_profile_is_an_error(interpreter: Interpreter) -> None:
    policy = PREFIXES + POLICY_BODY + "ex:p odrl:profile <https://example.org/unknown/> .\n"
    assert "error" in interpreter.reply(vector(policy))


def test_malformed_input_is_an_error(interpreter: Interpreter) -> None:
    reply = interpreter.reply(vector(request={"params": {"ex:purpose": "ex:research"}}))
    assert reply == {"error": "TypeError: request.params.ex:purpose: expected an object, got str"}


def test_no_policy_is_an_error(interpreter: Interpreter) -> None:
    policy = PREFIXES + "ex:perm a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a .\n"
    assert "error" in interpreter.reply(vector(policy))
