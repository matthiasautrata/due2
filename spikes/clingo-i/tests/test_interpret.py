"""What the corpus cannot see (TESTS.md): integrity, declines, the explanation, and
a few verdicts that the other tests rely on."""

from __future__ import annotations

import pytest
from clingo import Control, Model

from clingo_i.interpret import PROGRAM_FILES, SOLVE_2, VARIABLE_CAP, Interpreter, load_programs
from clingo_i.json_types import Json, Obj, as_obj
from tests.conftest import DPROD, DUE2, DUTY_INIT, INIT, POLICY, PREFIXES, PROF, vector

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
    (
        "applies.lp",
        "holds(part(X, P, action), f) :- atom(X), space(X, P), not action_matches(X, P).",
    ),
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


PARTIAL_DELETIONS = [
    (
        "guard",
        "constraint.lp",
        "node_space(Duty, P) :- duty_of(Y, Duty), space(Y, P).",
        "Permit",
        "guard_value",
    ),
    (
        "completion",
        "completion.lp",
        "completed(W, I, V) :- pre_in(W, I, 1), assigned(W, fin(I), V).",
        "Indeterminate",
        "completed",
    ),
]


@pytest.mark.parametrize(("gap", "file", "line", "intact", "check"), PARTIAL_DELETIONS)
def test_partial_gap_fails_loudly(gap: str, file: str, line: str, intact: str, check: str) -> None:
    # Each deletion leaves a gap that only some items or completions reach, and `check` is the
    # integrity.lp check that must name it.
    # `guard`: ex:d's guard `ex:g eq ex:v` reads ex:other, so ex:d is not owed and ex:r permits.
    # Without node_space for the duty, the guard has no data space and no value, and owed's #min
    # skips it, so ex:d is owed and the reply is Pending, unless a defect names the guard.
    # `completion`: ex:r has an absent assignee, an opaque part, and a constraint on unresolved
    # ex:x. Without the fin rule, the completions where the leaf is t have no `completed` value;
    # pruned by a constraint, they would leave only the completions where ex:r is f, and
    # NotApplicable, unless a defect in any model is an error.
    profile = (
        CONSTRAINT_PREFIXES
        + "ex:p a odrl:Set ; odrl:profile dprod: ; odrl:conflict odrl:prohibit ;"
    )
    if gap == "guard":
        policy = (
            profile
            + " odrl:permission ex:r .\n"
            + "ex:r a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a ; odrl:duty ex:d .\n"
            + "ex:d a odrl:Duty ; odrl:action odrl:compensate ; odrl:constraint "
            + "[ odrl:leftOperand ex:g ; odrl:operator odrl:eq ; odrl:rightOperand ex:v ] .\n"
            + bound("g", "stateSource")
        )
        fact: Obj = {"status": "resolved", "values": [{"@id": "ex:other"}]}
        v = vector(policy, sotw={"facts": {"ex:g": fact}})
    else:
        policy = (
            profile
            + " odrl:permission ex:r .\n"
            + "ex:r a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a ;"
            + f" odrl:assignee ex:alice ; odrl:constraint {leaf('eq', '5')} .\n"
            + bound("x", "stateSource")
        )
        v = vector(
            policy, request={"parties": {}}, sotw={"facts": {"ex:x": {"status": "unresolved"}}}
        )
    assert outcome(Interpreter(DUTY_INIT).reply(v)) == intact
    programs = load_programs()
    assert line in programs[file].splitlines(), f"{file} no longer has {line!r}"
    programs[file] = programs[file].replace(line, "")
    reply = Interpreter(DUTY_INIT, programs).reply(v)
    assert f"defect({check}(" in str(reply.get("error")), reply


def test_two_effects_fail_loudly() -> None:
    programs = load_programs()
    programs["integrity.lp"] += "\natom_effect(X, forbid) :- atom(X).\n"
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
    # The cross-policy rows, on explain.lp alone: q's t forbid y removes the candidate entries of
    # the other policies, p's u candidate x and r's t candidate w; r's forbid z, removed in r by w
    # under perm, removes nothing.
    facts = """
atom(x). atom_effect(x, permit). atom_policy(x, p). atom_rule(x, "x"). holds(applies(x, p), u).
atom(y). atom_effect(y, forbid). atom_policy(y, q). atom_rule(y, "y"). holds(applies(y, q), t).
atom(z). atom_effect(z, forbid). atom_policy(z, r). atom_rule(z, "z"). holds(applies(z, r), t).
atom(w). atom_effect(w, permit). atom_policy(w, r). atom_rule(w, "w"). holds(applies(w, r), t).
conflict(p, prohibit). conflict(q, prohibit). conflict(r, perm).
"""
    ctl = Control([])
    ctl.add("base", [], facts + load_programs()["explain.lp"])
    ctl.ground([("base", [])])
    rows: set[str] = set()
    ctl.solve(on_model=lambda m: rows.update(str(s) for s in m.symbols(shown=True)))
    assert rows == {
        'elim(x,p,y,"prohibit-overrides")',
        'elim(w,r,y,"prohibit-overrides")',
        "elim(z,r,w,perm)",
    }


# Entries (due2-workflows.md §6.2, decisions/0036): the permission `read` is stated by two
# policies. `a`, under invalid, also states the forbid `no`, and both apply, so `a` is void; `b`,
# under perm, has no forbid. `a`'s entries are removed and `b`'s entry of `read` survives.
SHARED = """
atom(read). atom_effect(read, permit). atom_rule(read, "read").
atom_policy(read, a). atom_policy(read, b).
atom(no). atom_effect(no, forbid). atom_rule(no, "no"). atom_policy(no, a).
conflict(a, invalid). conflict(b, perm).
"""


def test_shared_permission_survives_in_its_other_policy() -> None:
    # The risk is a fold that removes the atom when one policy removes its entry: that would
    # leave no candidate, and the verdict would be NotApplicable.
    facts = SHARED + (
        "world(c). completed(c, applies(read, a), t). completed(c, applies(read, b), t).\n"
        "completed(c, applies(no, a), t).\n"
    )
    ctl = Control(["--warn=none"])
    ctl.add("base", [], facts + load_programs()["resolve.lp"])
    ctl.ground([("base", [])])
    rows: set[str] = set()
    ctl.solve(on_model=lambda m: rows.update(str(s) for s in m.symbols(shown=True)))
    assert rows == {'verdict(c,"Permit")', "basis(c,read,permission)"}


def test_shared_permission_rows_name_the_entry() -> None:
    # Each removed entry has a row naming its policy, and `read` keeps its entry in `b`, which
    # stays on the listed frontier. The risk is reading one row as removing the atom: `read`
    # would not be listed in `b`, and the listed frontier would lose it.
    facts = SHARED + (
        "holds(applies(read, a), t). holds(applies(read, b), t). holds(applies(no, a), t).\n"
    )
    ctl = Control(["--warn=none"])
    ctl.add("base", [], facts + load_programs()["explain.lp"])
    ctl.ground([("base", [])])
    rows: set[str] = set()
    ctl.solve(on_model=lambda m: rows.update(str(s) for s in m.symbols(atoms=True)))
    assert {r for r in rows if r.startswith("elim(")} == {
        "elim(read,a,no,invalid)",
        "elim(no,a,read,invalid)",
    }
    assert "conflict_removes(read,a)" in rows
    assert "conflict_removes(read,b)" not in rows
    assert "listed(read,b)" in rows
    assert "listed(read,a)" not in rows


# --- constraints (due2-profiles.md §3 to §6) ---

XSD = "http://www.w3.org/2001/XMLSchema#"
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


# compare.lp, *Worked example*: `and` is the least of its members, so an f
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
        # A read dateTime without a timezone fits no operator: u (decisions/0024).
        (leaf("lt", '"2026-01-01T00:00:00Z"^^xsd:dateTime'), "",
         {"ex:x": typed("2025-01-01T00:00:00", "dateTime")}, "Indeterminate"),
        (leaf("neq", '"2026-01-01"^^xsd:date'), "", {"ex:x": typed("2025-01-01Z", "date")},
         "Indeterminate"),
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


def answer(source: str, status: str, *values: str) -> Obj:
    """One source's answer for a state fact (conformance/README.md, `sotw.facts`)."""
    return {"source": source, "status": status, "values": [iri(v) for v in values]}


# lift.lp, *Several sources*: the answers with values decide, and the others are ignored; with
# none, unresolved comes before invalid, and invalid before missing. A verdict row says the
# combination is resolved; a status row is the unknown part's status, the combined one. Without
# the guards that order the statuses, two answers without values give two `fact` statuses, and
# the reply has no output (the invalid and unresolved row fails).
@pytest.mark.parametrize(
    ("answers", "expected"),
    [
        ([answer("ex:s1", "resolved", "ex:v")], "Permit"),
        ([answer("ex:s1", "resolved", "ex:v"), answer("ex:s2", "resolved", "ex:v")], "Permit"),
        ([answer("ex:s1", "resolved", "ex:v"), answer("ex:s2", "resolved", "ex:w")], "conflict"),
        ([answer("ex:s1", "conflict", "ex:v", "ex:w"), answer("ex:s2", "resolved", "ex:v")],
         "conflict"),
        ([answer("ex:s1", "resolved", "ex:v"), answer("ex:s2", "unresolved")], "Permit"),
        ([answer("ex:s1", "resolved", "ex:w"), answer("ex:s2", "invalid")], "NotApplicable"),
        ([answer("ex:s1", "missing"), answer("ex:s2", "unresolved")], "unresolved"),
        ([answer("ex:s1", "invalid"), answer("ex:s2", "unresolved")], "unresolved"),
        ([answer("ex:s1", "missing"), answer("ex:s2", "invalid")], "invalid"),
        ([answer("ex:s1", "missing"), answer("ex:s2", "missing")], "missing"),
    ],
)  # fmt: skip
def test_several_sources(interpreter: Interpreter, answers: list[Json], expected: str) -> None:
    pol = constrained(leaf("eq", "ex:v"), bound("x", "stateSource"))
    reply = interpreter.reply(vector(pol, sotw={"facts": {"ex:x": answers}}))
    if expected in ("Permit", "NotApplicable"):
        assert outcome(reply) == expected
    else:
        assert unknown_parts(reply) == [("ex:r", "ex:x", expected)]


# A resolved answer for a set-valued operand with no members has values, the empty set
# (due2-workflows.md §3.3, *Several sources*). So it differs from an answer with a member, and
# agrees with another empty one. A combination that counts a resolved answer as having values
# only when it lists one fails both rows.
@pytest.mark.parametrize(
    ("answers", "expected"),
    [
        ([answer("ex:s1", "resolved"), answer("ex:s2", "resolved", "ex:v")], "conflict"),
        ([answer("ex:s1", "resolved"), answer("ex:s2", "resolved")], "NotApplicable"),
    ],
)
def test_several_sources_set(interpreter: Interpreter, answers: list[Json], expected: str) -> None:
    card = bound("x", "stateSource", " ; due2:cardinality due2:set")
    pol = constrained(leaf("isAllOf", "ex:v, ex:w"), card)
    reply = interpreter.reply(vector(pol, sotw={"facts": {"ex:x": answers}}))
    if expected == "NotApplicable":
        assert outcome(reply) == expected
    else:
        assert unknown_parts(reply) == [("ex:r", "ex:x", expected)]


# The texts of `policies` are one corpus, one policy each (due2-workflows.md §4, *Several
# policies are one corpus*). A second policy in its own text is admitted; the same policy added
# to the first text is `MultiplePolicies` (structure.lp). A rule that allowed one policy in all,
# rather than one per text, rejects the second policy in its own text too. Each text is
# normalised alone, so the second describes its own rule.
@pytest.mark.parametrize("own_text", [True, False])
def test_multiple_policies(interpreter: Interpreter, own_text: bool) -> None:
    first = constrained(leaf("eq", "ex:v"), bound("x"))
    second = (
        CONSTRAINT_PREFIXES
        + "ex:q a odrl:Set ; odrl:conflict odrl:prohibit ; odrl:permission ex:rq .\n"
        + "ex:rq odrl:action odrl:use ; odrl:target ex:b .\n"
    )
    v = vector(first)
    v["policies"] = [first, second] if own_text else [first + second]
    reply = interpreter.reply(v)
    if own_text:
        assert "error" not in reply, reply
    else:
        assert "error" in reply and "MultiplePolicies" in str(reply["error"]), reply


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


EUR = " ; due2:unit ex:EUR"


def unit(operator: str, right: str, iri: str) -> str:
    return leaf(operator, right)[:-1] + f"; odrl:unit {iri} ]"


# decisions/0049: a binding's due2:unit is the unit of every value read for the operand. A
# constraint in that unit, or in none, compares the values; a constraint in another unit is
# OperatorTypeMismatch; a constraint with a unit on a binding without one is u whatever is read,
# with status misfit. Without the unchecked rows the label-only reading (a definite Permit on 5,
# NotApplicable on 6) passes; without the USD row a differing unit is ignored; without the first
# two rows rejecting or blanking every unit passes.
@pytest.mark.parametrize(
    ("constraint", "binding", "value", "expected", "status"),
    [
        (unit("eq", "5", "ex:EUR"), EUR, "5", "Permit", None),
        (unit("eq", "5", "ex:EUR"), EUR, "6", "NotApplicable", None),
        (leaf("eq", "5"), EUR, "5", "Permit", None),
        (unit("eq", "5", "ex:EUR"), "", "5", "Indeterminate", "misfit"),
        (unit("eq", "5", "ex:EUR"), "", "6", "Indeterminate", "misfit"),
        (unit("eq", "5", "ex:USD"), EUR, "5", "error", None),
    ],
)  # fmt: skip
def test_units(
    interpreter: Interpreter,
    constraint: str,
    binding: str,
    value: str,
    expected: str,
    status: str | None,
) -> None:
    pol = constrained(constraint, bound("x", extra=binding))
    reply = interpreter.reply(vector(pol, request={"params": {"ex:x": typed(value, "integer")}}))
    assert outcome(reply) == expected
    if expected != "error":
        assert unknown_parts(reply) == ([] if status is None else [("ex:r", "ex:x", status)])


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


# W1 normalises each policy alone, with its own profiles' layers (due2-workflows.md §4, *Several
# policies are one corpus*), so a profile that policy Q names reaches neither the conflict default
# nor the bindings of policy P, which names none (#149). Each profile states one thing that would
# change P's reply if it leaked: a conflict default, a binding of ex:x, a unit for ex:x, or a
# concept scheme for ex:x.
LEAKS = {
    "conflict": f"<{PROF}conflict> odrl:conflict odrl:prohibit .\n",
    "binding": bound("x"),
    "unit": bound("x", extra=EUR),
    "scheme": "ex:x due2:conceptScheme ex:S .\n",
}
LEAK_MODULES: Obj = {"core.ttl": CONSTRAINT_PREFIXES}
for _name, _text in LEAKS.items():
    LEAK_MODULES[f"{_name}.ttl"] = CONSTRAINT_PREFIXES + _text
LEAK_INIT: Obj = {
    "modules": LEAK_MODULES,
    "core": ["core.ttl"],
    "profiles": {f"{PROF}{name}": [f"{name}.ttl"] for name in LEAKS},
}


def naming(profile: str, constraint: str = "") -> str:
    """Policy ex:q, which names `PROF<profile>` and states no conflict: one permission, ex:rq,
    on ex:b, with the constraint `constraint` if one is given."""
    on = f" ; odrl:constraint {constraint}" if constraint else ""
    return (
        CONSTRAINT_PREFIXES
        + f"ex:q a odrl:Set ; odrl:profile <{PROF}{profile}> ; odrl:permission ex:rq .\n"
        + f"ex:rq a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:b{on} .\n"
    )


# P alone gives the expected reply in each row, and Q's profile would change it:
#
# - P permits and prohibits use of ex:a and states no conflict, so it is `invalid` and void
#   (NotApplicable); Q's `prohibit` default would make it Deny.
# - P's ex:x has no binding of its own, so P is UnboundLeftOperand; Q's module would bind it.
# - P's leaf states a unit that P's binding does not declare, so it is u with status misfit;
#   Q's module would own ex:x's type and declare the unit.
# - P's ex:v is not a concept; Q's scheme would make the leaf an OperatorTypeMismatch.
CONFLICTED = (
    CONSTRAINT_PREFIXES
    + "ex:p a odrl:Set ; odrl:permission ex:r ; odrl:prohibition ex:f .\n"
    + "ex:r a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a .\n"
    + "ex:f a odrl:Prohibition ; odrl:action odrl:use ; odrl:target ex:a .\n"
)
LEAK_CASES = [
    ("conflict", CONFLICTED, iri("ex:v"), "NotApplicable"),
    ("binding", constrained(leaf("eq", "ex:v")), iri("ex:v"), "error"),
    ("unit", constrained(unit("eq", "5", "ex:EUR"), bound("x")), typed("5", "integer"),
     "Indeterminate"),
    ("scheme", constrained(leaf("eq", "ex:v"), bound("x")), iri("ex:v"), "Permit"),
]  # fmt: skip


@pytest.mark.parametrize("q_first", [False, True], ids=["p-first", "q-first"])
@pytest.mark.parametrize(
    ("profile", "p", "value", "expected"), LEAK_CASES, ids=[c[0] for c in LEAK_CASES]
)
def test_profile_stays_with_its_policy(
    profile: str, p: str, value: Obj, expected: str, q_first: bool
) -> None:
    interpreter = Interpreter(LEAK_INIT)
    v = vector(p, request={"action": "odrl:use", "params": {"ex:x": value}})
    alone = interpreter.reply(v)
    v["policies"] = [naming(profile), p] if q_first else [p, naming(profile)]
    joint = interpreter.reply(v)
    assert outcome(alone) == expected, alone
    assert outcome(joint) == expected, joint
    if expected == "error":
        assert "UnboundLeftOperand" in str(joint["error"]), joint
    if profile == "unit":
        assert unknown_parts(joint) == [("ex:r", "ex:x", "misfit")]


# The controls: a profile still reaches the policy that names it. Q's `prohibit` default resolves
# Q's own conflict, and Q's module binds Q's own ex:x leaf.
def test_profile_reaches_its_own_policy() -> None:
    interpreter = Interpreter(LEAK_INIT)
    q = naming("conflict").replace("ex:rq .", "ex:rq ; odrl:prohibition ex:fq .")
    q += "ex:fq a odrl:Prohibition ; odrl:action odrl:use ; odrl:target ex:b .\n"
    v = vector(q, request={"action": "odrl:use", "target": "ex:b"})
    assert outcome(interpreter.reply(v)) == "Deny"
    v = vector(request={"action": "odrl:use", "target": "ex:b", "params": {"ex:x": iri("ex:v")}})
    v["policies"] = [
        naming("binding", leaf("eq", "ex:v")),
        constrained(leaf("eq", "ex:w"), bound("x")),
    ]
    assert outcome(interpreter.reply(v)) == "Permit"


# A named node is one node of the corpus (due2-workflows.md §4). A leaf that two texts share is one
# leaf if their layers bind its operand alike; bound differently, it is IdentityConflict, the error
# the policy store gives at publish (due2-diagnostics.md).
@pytest.mark.parametrize(("q_property", "expected"), [("x", "Permit"), ("y", "error")])
def test_shared_leaf_binds_alike(q_property: str, expected: str) -> None:
    shared = "ex:c .\nex:c odrl:leftOperand ex:x ; odrl:operator odrl:eq ; odrl:rightOperand ex:v"
    p = constrained(shared, bound("x"))
    q = naming("conflict", shared) + bound("x").replace("ex:x .", f"ex:{q_property} .")
    v = vector(p, request={"action": "odrl:use", "params": {"ex:x": iri("ex:v")}})
    v["policies"] = [p, q]
    reply = Interpreter(LEAK_INIT).reply(v)
    assert outcome(reply) == expected, reply
    if expected == "error":
        assert "IdentityConflict at https://example.org/c" in str(reply["error"]), reply


# A world edge is declined only in a data space that reads it (decisions/0050 #1). The world puts
# ex:alice in ex:team, which only P types and compares the request's assignee with; Q never names
# ex:team. Every text's solve 0 sees the SOTW. When the decline fired on any edge reachable from
# a request entity, Q's solve 0 found the edge without the type and declined it as an untyped
# collection, and the corpus kept Q's decline (#151). With ex:team typed in no text, P's read
# still declines it.
@pytest.mark.parametrize("q_first", [False, True], ids=["p-first", "q-first"])
@pytest.mark.parametrize(
    ("typed_in_p", "expected"),
    [(True, "Permit"), (False, "odrl:partOf: untyped collection")],
    ids=["typed", "untyped"],
)
def test_world_edge_declines_only_where_read(
    interpreter: Interpreter, typed_in_p: bool, expected: str, q_first: bool
) -> None:
    p = (
        CONSTRAINT_PREFIXES
        + "ex:p a odrl:Set ; odrl:permission ex:r .\n"
        + "ex:r a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a ;"
        + " odrl:assignee ex:team .\n"
        + ("ex:team a odrl:PartyCollection .\n" if typed_in_p else "")
    )
    q = (
        CONSTRAINT_PREFIXES
        + "ex:q a odrl:Set ; odrl:permission ex:rq .\n"
        + "ex:rq a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:b .\n"
    )
    edge: Json = [ODRL + "partOf", EX + "alice", EX + "team"]
    v = vector(p, request={"action": "odrl:use"}, sotw={"closure": [edge]})
    v["policies"] = [q, p] if q_first else [p, q]
    assert outcome(interpreter.reply(v)) == expected


def two_texts(p_extra: str, q_rule: str, shared: bool = False) -> list[str]:
    """Policy ex:p, which permits use of ex:a and states `p_extra`, and policy ex:q, whose
    permission is `q_rule`'s body; with `shared`, ex:p states ex:q's rule too, named ex:rq."""
    rq = f"ex:rq a odrl:Permission ; {q_rule} .\n"
    p = (
        CONSTRAINT_PREFIXES
        + f"ex:p a odrl:Set ; odrl:permission ex:r{', ex:rq' if shared else ''} .\n"
        + "ex:r a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a .\n"
        + (rq if shared else "")
        + p_extra
    )
    q = CONSTRAINT_PREFIXES + "ex:q a odrl:Set ; odrl:permission ex:rq .\n" + rq
    return [p, q]


# The two runs of decisions/0050 (§ Question): policy ex:p states an edge from the request's
# entity, ex:copy or ex:alice, to what ex:q's rule names, and ex:p's own rule is on ex:a, so it
# does not match. ex:q alone is NotApplicable, and stays so beside ex:p in both orders. With one
# hierarchy over the corpus, both runs were Permit at 0928921. The `own` rows put the same edge
# in ex:q's text, where it widens ex:q's rule: a fix that dropped policy edges is caught.
TEAM = "ex:team a odrl:PartyCollection .\n"
EDGE_RUNS: dict[str, tuple[str, str, str, Obj]] = {
    "includedIn": ("ex:copy odrl:includedIn odrl:use .\n", ("odrl:action odrl:use ;"
                   " odrl:target ex:b"), "", {"action": "ex:copy", "target": "ex:b"}),
    "partOf": (TEAM + "ex:alice odrl:partOf ex:team .\n", ("odrl:assignee ex:team ;"
               " odrl:action odrl:use ; odrl:target ex:b"), TEAM, {"action": "odrl:use", "target": "ex:b"}),
}  # fmt: skip


@pytest.mark.parametrize("q_first", [False, True], ids=["p-first", "q-first"])
@pytest.mark.parametrize(("own", "expected"), [(False, "NotApplicable"), (True, "Permit")],
                         ids=["other", "own"])  # fmt: skip
@pytest.mark.parametrize("run", sorted(EDGE_RUNS))
def test_policy_reads_only_its_own_edges(
    interpreter: Interpreter, run: str, own: bool, expected: str, q_first: bool
) -> None:
    edge, q_rule, q_extra, request = EDGE_RUNS[run]
    p, q = two_texts("" if own else edge, q_rule)
    q += edge if own else q_extra
    v = vector(q, request=request)
    assert outcome(interpreter.reply(v)) == ("Permit" if own else "NotApplicable")
    v["policies"] = [q, p] if q_first else [p, q]
    assert outcome(interpreter.reply(v)) == expected


# A refinement on a policy-level action lies in the policy's own tree, and a policy is read in its
# own data space (`node_space/2`, constraint.lp), so the refinement is read in ex:p alone. ex:x is
# a state property with no fact, so the refinement is U and ex:p alone is Indeterminate. isA reads
# a hierarchy, so its completion variable is keyed by policy (decisions/0050 #9). Before #154 no
# node gave the policy's tree a space, so the refinement was read in every policy. The `rule`
# rows state the same refined action on ex:p's rule, whose tree always had ex:p's space.
REFINED_USE = (
    "[ rdf:value odrl:use ; odrl:refinement"
    " [ odrl:leftOperand ex:x ; odrl:operator odrl:isA ; odrl:rightOperand ex:c ] ]"
)


@pytest.mark.parametrize("q_first", [False, True], ids=["p-first", "q-first"])
@pytest.mark.parametrize("on_policy", [True, False], ids=["policy", "rule"])
def test_policy_refinement_stays_with_its_policy(
    interpreter: Interpreter, on_policy: bool, q_first: bool
) -> None:
    on_p, on_r = (
        (f" odrl:action {REFINED_USE} ;", "")
        if on_policy
        else ("", f" odrl:action {REFINED_USE} ;")
    )
    p = (
        CONSTRAINT_PREFIXES
        + "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n"
        + f"ex:p a odrl:Set ;{on_p} odrl:permission ex:r .\n"
        + f"ex:r a odrl:Permission ;{on_r} odrl:target ex:a .\n"
        + bound("x", "stateSource")
    )
    q = two_texts("", "odrl:action odrl:use ; odrl:target ex:b")[1]
    v = vector(p, request={"action": "odrl:use", "target": "ex:a"})
    assert outcome(interpreter.reply(v)) == "Indeterminate"
    v["policies"] = [q, p] if q_first else [p, q]
    assert outcome(interpreter.reply(v)) == "Indeterminate"


# A cross-policy row is listed only when it holds in every completion in which its entry is a
# candidate (due2-workflows.md §3.5, decisions/0052). ex:p states the prohibition ex:forbid and the
# permission ex:r, under `constraint` on the unresolved ex:x; ex:q states ex:rq, whose finding is
# t. Under `prohibit`, ex:forbid survives in every completion: it removes ex:r within ex:p and
# ex:rq across. Under `perm` with `ex:x eq 5`, where ex:x is 5, ex:r removes ex:forbid within ex:p
# and ex:rq permits; elsewhere ex:forbid denies. ex:rq is a candidate in both, and is removed in
# one, so no row. Under `perm` with `eq 5 or neq 5`, ex:r applies in every completion, the verdict
# is Permit, and ex:forbid removes nothing. A rule that read "ex:p does not surely remove
# ex:forbid", the Kleene world's approximation, listed ex:rq by ex:forbid in both `perm` rows.
@pytest.mark.parametrize(
    ("conflict", "constraint", "expected"),
    [
        ("prohibit", leaf("eq", "5"),
         {"verdict": "Deny", "verdict_basis": basis("ex:forbid prohibition"),
          "eliminated": elims("ex:r ex:forbid prohibit", "ex:rq ex:forbid prohibit-overrides")}),
        ("perm", leaf("eq", "5"),
         {"verdict": "Indeterminate", "verdict_basis": basis("ex:r unknown"), "eliminated": [],
          "verdict_range": {"low": "Deny", "high": "Permit"}}),
        ("perm", f"[ odrl:or ( {leaf('eq', '5')} {leaf('neq', '5')} ) ]",
         {"verdict": "Permit", "verdict_basis": basis("ex:r permission", "ex:rq permission"),
          "eliminated": []}),
    ],
    ids=["surviving", "uncertain", "removed-by-cases"],
)  # fmt: skip
def test_cross_policy_rows_hold_in_every_completion(
    interpreter: Interpreter, conflict: str, constraint: str, expected: Obj
) -> None:
    p = (
        CONSTRAINT_PREFIXES
        + f"ex:p a odrl:Set ; odrl:conflict odrl:{conflict} ;"
        + " odrl:permission ex:r ; odrl:prohibition ex:forbid .\n"
        + "ex:r a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a ;"
        + f" odrl:constraint {constraint} .\n"
        + "ex:forbid a odrl:Prohibition ; odrl:action odrl:use ; odrl:target ex:a .\n"
        + bound("x", "stateSource")
    )
    q = (
        CONSTRAINT_PREFIXES
        + "ex:q a odrl:Set ; odrl:permission ex:rq .\n"
        + "ex:rq a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a .\n"
    )
    v = vector(p, sotw={"facts": {"ex:x": {"status": "unresolved"}}})
    v["policies"] = [p, q]
    assert explained(interpreter.reply(v)) == expected


# A rule that two policies state is one atom with an entry in each, and each entry is read in its
# own policy's data space (decisions/0050 #4). In the `read-apart` row, ex:p's ex:copy edge makes
# ex:rq's action part t in ex:p and f in ex:q, so ex:rq's entry in ex:p permits. The risk is one
# reading per atom: ex:q's would make it NotApplicable. (A union of the spaces would permit too;
# test_locality.py's shared-node variant catches it through the findings.) In the `completion`
# row the request's target is absent, so each entry's target part is u and gets its own
# completion variable (decisions/0050 #9); the reply names ex:rq once.
@pytest.mark.parametrize(
    ("p_extra", "asked", "expected", "parts"),
    [
        ("ex:copy odrl:includedIn odrl:use .\n", {"action": "ex:copy", "target": "ex:b"},
         {"verdict": "Permit", "verdict_basis": basis("ex:rq permission"), "eliminated": []}, []),
        ("", {"action": "odrl:use", "target": None},
         {"verdict": "Indeterminate", "verdict_basis": basis("ex:r unknown", "ex:rq unknown"),
          "eliminated": [], "verdict_range": {"low": "NotApplicable", "high": "Permit"}},
         [("ex:r", "odrl:target", "missing"), ("ex:rq", "odrl:target", "missing")]),
    ],
    ids=["read-apart", "completion"],
)  # fmt: skip
def test_shared_rule_entries_read_apart(
    interpreter: Interpreter,
    p_extra: str,
    asked: Obj,
    expected: Obj,
    parts: list[tuple[str, str, str]],
) -> None:
    v = vector(request=asked)
    if asked.get("target") is None:
        del as_obj(v["request"], "request")["target"]
    texts: list[Json] = [*two_texts(p_extra, "odrl:action odrl:use ; odrl:target ex:b", True)]
    v["policies"] = texts
    reply = interpreter.reply(v)
    assert explained(reply) == expected
    assert unknown_parts(reply) == parts


def approving(policy: str, rule: str, extra: str = "") -> str:
    """Policy `policy`, whose permission `rule` on use of ex:a carries duty ex:approval: the
    council is to compensate. Each policy states ex:approval alike, so it is one atom."""
    return (
        PREFIXES
        + f"ex:{policy} a odrl:Set ; odrl:permission ex:{rule} .\n"
        + f"ex:{rule} a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a ;"
        + " odrl:duty ex:approval .\n"
        + "ex:approval a odrl:Duty ; odrl:assignee ex:council ; odrl:action odrl:compensate .\n"
        + extra
    )


def fulfilled_values(interp: Interpreter, v: Obj) -> dict[str, str]:
    """Each policy's value of the one `fulfilled` item, in one model of solve 2's files."""
    programs = load_programs()
    ctl = Control(["--warn=none", "--models=1"])
    ctl.add("base", [], interp.facts(v) + "\n" + "\n".join(programs[f] for f in SOLVE_2))
    ctl.ground([("base", [])])
    out: dict[str, str] = {}

    def keep(model: Model) -> None:
        for s in model.symbols(atoms=True):
            if s.match("holds", 2) and s.arguments[0].match("fulfilled", 2):
                out[s.arguments[0].arguments[1].string] = str(s.arguments[1])

    assert ctl.solve(on_model=keep).satisfiable
    return out


# Duty ex:approval is one atom with an entry in each of ex:p and ex:q, and both entries are owed,
# as each policy's permission applies. Each entry's `fulfilled` is read in its own policy's data
# space (decisions/0050 #4). In the `both` row the council compensates, so the one event fulfils
# both entries and both permissions are ready. In the `local` row the event's action is
# ex:payOut, which ex:p alone places under odrl:compensate: ex:p's entry is fulfilled and ex:q's
# is not, so only ex:rp is in the basis. The risk is one finding per duty: it would make both
# entries alike in the `local` row, either both fulfilled or ex:rp pending.
@pytest.mark.parametrize("q_first", [False, True], ids=["p-first", "q-first"])
@pytest.mark.parametrize(
    ("action", "edge", "fulfilled", "permissions"),
    [("odrl:compensate", "", {"p": "t", "q": "t"}, ["ex:rp", "ex:rq"]),
     ("ex:payOut", "ex:payOut odrl:includedIn odrl:compensate .\n", {"p": "t", "q": "f"},
      ["ex:rp"])],
    ids=["both", "local"],
)  # fmt: skip
def test_shared_duty_entries_fulfilled_apart(
    duty_interpreter: Interpreter,
    action: str,
    edge: str,
    fulfilled: dict[str, str],
    permissions: list[str],
    q_first: bool,
) -> None:
    event: Obj = {"id": "ex:e1", "occurred_at": "2026-05-01T00:00:00Z", "actor": "ex:council",
                  "action": action}  # fmt: skip
    v = vector(request={"action": "odrl:use"}, sotw={"evidence": [event]})
    texts: list[Json] = [approving("p", "rp", edge), approving("q", "rq")]
    v["policies"] = texts[::-1] if q_first else texts
    rows = basis(*(f"{r} permission" for r in permissions))
    expected = {"verdict": "Permit", "verdict_basis": rows, "eliminated": []}
    assert explained(duty_interpreter.reply(v)) == expected
    values = fulfilled_values(duty_interpreter, v)
    assert values == {EX + p: value for p, value in fulfilled.items()}


# A profile's vocabulary is read only by the policies that name it (due2-profiles.md §2), a
# policy's text is only the text that types it, and a text says nothing of a node it never links
# to (due2-workflows.md §4). Each row is one counterexample (#158): the reply to `alone` must not
# change when `other` stands beside it, in either order. Before #158 each changed: the corpus
# solves read every module's party roles, kept one owning profile per module file, and kept every
# text's triples, and `policy_text/2` held for any text about a policy.
#
# - `bearer`: ex:d names ex:bank as informed party and no bearer, so its bearer is the request
#   subject ex:alice, and ex:bank's payment fulfils nothing: Pending. Q's profile makes
#   odrl:informedParty a bearer's function, which made ex:bank the bearer and the duty fulfilled.
# - `module`: profiles a and b include the same file, whose edge puts ex:copy under odrl:use.
#   P names b, so it permits copying ex:a; Q names a, and the file kept only a's layer.
# - `offer`: the offer permits use of ex:catalog. The agreement places ex:report1 in ex:catalog
#   and states the offer's lifecycle status, a triple about the offer that made the agreement's
#   text one of the offer's texts, and its edge part of the offer's data space.
# - `member`: ex:c1, a member of ex:c's `odrl:and` list, requires purpose research or teaching,
#   and the request's is marketing. Q's text gives ex:c1 the right operand marketing too, which
#   made it `t` and the rule permit while every text's triples were kept. It also guards
#   `reached/1`'s list rule: without it no text reaches ex:c1, the corpus drops the vector's own
#   triples about it, and a filter that keeps the triples of nodes no text reaches keeps Q's.
ROLES = (
    f"@prefix due2: <{DUE2}> .\n" + PREFIXES + "odrl:informedParty due2:playsRole due2:bearer .\n"
)
EDGE = PREFIXES + "ex:copy odrl:includedIn odrl:use .\n"
FOREIGN_INIT: Obj = {
    "modules": {**as_obj(DUTY_INIT["modules"], "modules"), "roles.ttl": ROLES, "edge.ttl": EDGE},
    "core": ["core.ttl"],
    "profiles": {
        **as_obj(DUTY_INIT["profiles"], "profiles"),
        f"{PROF}roles": ["roles.ttl"],
        f"{PROF}a": ["edge.ttl"],
        f"{PROF}b": ["edge.ttl"],
    },
}


def rule_policy(policy: str, target: str, extra: str = "", profile: str = "") -> str:
    """Policy ex:`policy`, naming `PROF<profile>` if given, which permits use of `target`;
    the permission ex:r`policy` ends with `extra`."""
    named = f" ; odrl:profile <{PROF}{profile}>" if profile else ""
    return (
        PREFIXES
        + f"ex:{policy} a odrl:Set{named} ; odrl:permission ex:r{policy} .\n"
        + f"ex:r{policy} a odrl:Permission ; odrl:action odrl:use ; odrl:target {target}{extra} .\n"
    )


PAYMENT: Obj = {"id": "ex:e1", "occurred_at": "2026-05-01T00:00:00Z", "actor": "ex:bank",
                "action": "odrl:compensate"}  # fmt: skip
OFFER = (
    PREFIXES
    + "ex:offer a odrl:Offer ; odrl:assigner ex:shop ; odrl:permission ex:ro .\n"
    + "ex:ro a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:catalog .\n"
    + "ex:catalog a odrl:AssetCollection .\n"
)
AGREEMENT = (
    PREFIXES
    + f"@prefix dprod: <{DPROD}> .\n"
    + "ex:agr a odrl:Agreement ; odrl:assigner ex:shop ; odrl:assignee ex:bob ;"
    + " odrl:permission ex:ra .\n"
    + "ex:ra a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:catalog .\n"
    + "ex:catalog a odrl:AssetCollection .\n"
    + "ex:report1 odrl:partOf ex:catalog .\n"
    + "ex:offer dprod:offerLifecycleStatus dprod:Accepted .\n"
)
FOREIGN_CASES: dict[str, tuple[str, str, dict[str, Obj], str]] = {
    "bearer": (
        rule_policy("p", "ex:a", " ; odrl:duty ex:d")
        + "ex:d a odrl:Duty ; odrl:action odrl:compensate ; odrl:informedParty ex:bank .\n",
        rule_policy("q", "ex:b", profile="roles"),
        {"request": {"action": "odrl:use"}, "sotw": {"evidence": [PAYMENT]}},
        "Pending",
    ),
    "module": (
        rule_policy("p", "ex:a", profile="b"),
        rule_policy("q", "ex:z", profile="a"),
        {"request": {"action": "ex:copy"}},
        "Permit",
    ),
    "offer": (OFFER, AGREEMENT, {"request": {"target": "ex:report1"}}, "NotApplicable"),
    "member": (
        constrained(WORKED_CONSTRAINT, bound("purpose"), bound("count")),
        rule_policy("q", "ex:b") + "ex:c1 odrl:rightOperand ex:marketing .\n",
        {
            "request": {
                "params": {"ex:purpose": iri("ex:marketing"), "ex:count": typed("3", "integer")}
            }
        },
        "NotApplicable",
    ),
}


@pytest.mark.parametrize("other_first", [False, True], ids=["other-last", "other-first"])
@pytest.mark.parametrize("case", sorted(FOREIGN_CASES))
def test_another_text_changes_no_structure(case: str, other_first: bool) -> None:
    alone, other, sections, expected = FOREIGN_CASES[case]
    interpreter = Interpreter(FOREIGN_INIT)
    v = vector(alone, **sections)
    reply = interpreter.reply(v)
    assert as_obj(reply.get("output"), "output")["verdict"] == expected, reply
    v["policies"] = [other, alone] if other_first else [alone, other]
    assert interpreter.reply(v) == reply


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
            {"target": "ex:bob"},
            "odrl:partOf: cross-kind edge",
        ),
        # The decline is demand-driven: the request names ex:a itself, so no read walks the
        # cross-kind edge out of ex:bob, and the rule answers (lift.lp, *Hierarchies*).
        (
            "ex:a a odrl:AssetCollection . ex:bob a odrl:Party ; odrl:partOf ex:a .",
            {},
            "Permit",
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
        # A single-valued type attribute stated twice, or of the wrong kind (#145).
        (leaf("eq", "ex:v"), bound("x", extra=" ; due2:cardinality due2:many"), "InvalidBinding"),
        (leaf("eq", "ex:v"), bound("x", extra=" ; due2:cardinality due2:one, due2:set"),
         "InvalidBinding"),
        (leaf("eq", "ex:v"), bound("x", extra=" ; rdfs:range xsd:integer, xsd:string"),
         "InvalidBinding"),
        (leaf("eq", "ex:v"), bound("x", extra=' ; rdfs:range "xsd:string"'), "InvalidBinding"),
        (leaf("eq", "ex:v"), bound("x", extra=" ; due2:unit ex:EUR, ex:USD"), "InvalidBinding"),
        (leaf("eq", "ex:v"), bound("x", extra=' ; due2:unit "EUR"'), "InvalidBinding"),
        # A dateTime without a timezone, or a date with one (decisions/0024).
        (leaf("lt", '"2026-01-01T00:00:00"^^xsd:dateTime'), "", "OperatorTypeMismatch"),
        (leaf("eq", '"2026-01-01Z"^^xsd:date'), "", "OperatorTypeMismatch"),
        # An operator of one left value over a set-valued operand (decisions/0025).
        (leaf("eq", "ex:v"), bound("x", extra=" ; due2:cardinality due2:set"),
         "OperatorTypeMismatch"),
        (leaf("isAnyOf", "ex:v, ex:w"), bound("x", extra=" ; due2:cardinality due2:set"),
         "OperatorTypeMismatch"),
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
    ("triple", "code"),
    [
        ("ex:p dct:isReplacedBy ex:p2 .", "ReplacedPolicy"),
        ("ex:p odrl:profile ex:unshipped .", "UnrecognisedProfile"),
    ],
)
def test_policy_rejections(interpreter: Interpreter, triple: str, code: str) -> None:
    """A replaced policy (IM 2.2 §2.8) and an unrecognised profile (IM 2.2 §3.2) are rejected.

    Without the first rule, `dct:isReplacedBy` would be an annotation, and the void policy would
    give its own `Permit`. Without the code in the second error, a caller could not tell an
    unrecognised profile from a malformed vector.
    """
    reply = interpreter.reply(vector(POLICY + triple + "\n"))
    assert "error" in reply and code in str(reply["error"]), reply


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
        (leaf("eq", "ex:v"), " ; rdfs:range [ <http://www.w3.org/2002/07/owl#unionOf> ( xsd:integer xsd:string ) ]",
         "binding: range"),
    ],
)  # fmt: skip
def test_constraint_declines(
    interpreter: Interpreter, constraint: str, binding: str, reason: str
) -> None:
    v = vector(constrained(constraint, bound("x", extra=binding)))
    assert interpreter.reply(v) == {"unsupported": reason}


CONSTRAINT_DELETIONS = [
    (
        "compare.lp",
        "crank(W, C, P, N) :- op(C, eq), cpair(W, C, P, Lv, Rv), ceqr(C, P, Lv, Rv, N).",
    ),
    ("operand.lp", "read_u(W, Op, P) :- read_in(W, Op, P), not read_resolved(W, Op)."),
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


def two_rules(
    c1: str, c2: str, kind: str = "Permission", refine: bool = False, x_extra: str = ""
) -> str:
    """Rules ex:r1 under `c1` and ex:r2 under `c2`, both of `kind`, reading ex:x and ex:y.

    Both operands read the state, and a vector with no fact for them leaves them
    `unresolved`, so their leaves are paired (completion.lp).

    With `refine`, `c2` refines ex:r2's action instead of constraining the rule. `x_extra` is
    appended to ex:x's binding.
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
        + bound("x", "stateSource", x_extra)
        + bound("y", "stateSource")
    )


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
        # ex:y reads another property, so another value.
        (leaf("eq", "5"), leaf("neq", "5").replace("ex:x", "ex:y"), False, "Indeterminate"),
        (leaf("eq", "5"), leaf("neq", "6"), False, "Indeterminate"),
        (leaf("eq", "5"), leaf("lt", "5"), False, "Indeterminate"),
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


# The constraint's own unit is part of the key, and W1 does not fill it from the binding
# (decisions/0049 #4), so a leaf without a unit and one with the binding's unit are two
# variables. An unchecked unit is opaque, so it is never paired. Without the last row a misfit
# leaf would be paired with its complement, a Permit no arriving value can produce.
@pytest.mark.parametrize(
    ("c1", "c2", "binding", "expected"),
    [
        (unit("eq", "5", "ex:EUR"), unit("neq", "5", "ex:EUR"), EUR, "Permit"),
        (leaf("eq", "5"), unit("neq", "5", "ex:EUR"), EUR, "Indeterminate"),
        (unit("eq", "5", "ex:EUR"), unit("neq", "5", "ex:EUR"), "", "Indeterminate"),
    ],
)
def test_completion_key_units(
    interpreter: Interpreter, c1: str, c2: str, binding: str, expected: str
) -> None:
    pol = two_rules(c1, c2, x_extra=binding)
    assert outcome(interpreter.reply(vector(pol))) == expected


def test_binding_not_operand_iri(interpreter: Interpreter) -> None:
    # ex:y bound to ex:x's property reads the same value, so the leaves share a variable.
    pol = two_rules(leaf("eq", "5"), leaf("neq", "5").replace("ex:x", "ex:y")).replace(
        "ex:y dprod:operandSource dprod:stateSource ; dprod:operandProperty ex:y",
        "ex:y dprod:operandSource dprod:stateSource ; dprod:operandProperty ex:x",
    )
    assert outcome(interpreter.reply(vector(pol))) == "Permit"


def test_concept_scheme_in_key(interpreter: Interpreter) -> None:
    # ex:y is bound to ex:x's property, with a scheme: its eq is ⊑ and ex:x's is identity. At
    # ex:x = ex:low both leaves are f, so they are not complements and stay two variables
    # (due2-workflows.md §6.4). Sharing one would give Permit, which ex:low refutes.
    pol = (
        two_rules(leaf("eq", "ex:top"), leaf("neq", "ex:top").replace("ex:x", "ex:y")).replace(
            "ex:y dprod:operandSource dprod:stateSource ; dprod:operandProperty ex:y",
            "ex:y dprod:operandSource dprod:stateSource ; dprod:operandProperty ex:x ;"
            " due2:conceptScheme ex:s",
        )
        + SCHEME
    )
    assert outcome(interpreter.reply(vector(pol))) == "Indeterminate"
    low: Obj = {"facts": {"ex:x": {"status": "resolved", "values": [iri("ex:low")]}}}
    assert outcome(interpreter.reply(vector(pol, sotw=low))) == "NotApplicable"


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
        # every completion, so the basis is empty. The permissions are the worked example
        # of completion.lp.
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
        # A value the program compares, and cannot place (values.py).
        ({"request": {"at": "2026-06-01T00:00:00"}}, "value: dateTime without timezone"),
        ({"sotw": {"effective_at": "2026-13-01T00:00:00Z"}}, "value: ill-typed xsd:dateTime"),
        # The input declines come first.
        (
            {
                "request": {"at": "2026-06-01T00:00:00"},
                "sotw": {"closure": [["ex:knows", "ex:a", "ex:b"]]},
            },
            "sotw.closure",
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
        {"sotw": {"evidence": [EVIDENCE | {"issuer": "ex:bank"}]}},
    ],
)
def test_duty_inputs_are_read(interpreter: Interpreter, changes: dict[str, Obj]) -> None:
    # The fields duty.lp reads are not declined, and without a duty they change nothing. Had lift.lp kept their declines, each would reply `unsupported`.
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
