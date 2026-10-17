"""What the corpus cannot see (DESIGN.md § Tests): integrity, declines, the explanation, and
a few verdicts that the other tests rely on."""

from __future__ import annotations

import pytest
from clingo import Control

from clingo_i.interpret import PROGRAM_FILES, Interpreter, load_programs
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
    (
        "completion.lp",
        (
            "lit_of(part(X, party(F)), party(F, Party)) :- atom_party(X, F, Party), "
            "holds(part(X, party(F)), u)."
        ),
    ),
    ("resolve.lp", 'verdict(W, "NotApplicable") :- world(W), not deny(W), not ready(W).'),
]


@pytest.mark.parametrize(("file", "line"), DELETIONS)
def test_deleted_rule_fails_loudly(file: str, line: str) -> None:
    programs = load_programs()
    assert line in programs[file].splitlines(), f"{file} no longer has {line!r}"
    programs[file] = programs[file].replace(line, "")
    broken = Interpreter(INIT, programs)
    # Each vector exercises the deleted rule: an absent assignee gives a u part (kleene.lp)
    # that reads a party literal (completion.lp), a foreign action an f part (applies.lp),
    # and NotApplicable its rule (resolve.lp).
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
    """The output, with ex: names for refs and the shape of each explanation field checked."""
    assert "output" in reply, reply
    out = reply["output"]
    assert isinstance(out, dict)
    short = {k: v for k, v in out.items() if k not in ("frontier", "obligations", "exact")}
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
    # DESIGN.md § Worked example: with no target, each atom reads its own target variable, and
    # four completions give three verdicts.
    v = vector()
    request = as_obj(v["request"], "request")
    del request["target"]
    assert explained(interpreter.reply(v)) == {
        "verdict": "Indeterminate",
        "verdict_basis": basis("ex:forbid unknown", "ex:perm unknown"),
        "eliminated": [],
        "verdict_range": {"low": "Deny", "high": "Permit"},
    }


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
        # Both rules read the absent target ex:a: one literal.
        (policy("perm", "perm perm a", "forbid forbid a"), {"target": None}),
        # Both rules read the unnamed assignee ex:alice: one literal.
        (policy("perm", "perm perm a alice", "forbid forbid a alice"), NO_PARTY),
    ],
)
def test_atoms_share_a_literal(interpreter: Interpreter, pol: str, request_changes: Obj) -> None:
    # Independent parts would admit the forbid alone (Deny). One literal: both or neither,
    # and under perm both is Permit.
    v = vector(pol, request={k: x for k, x in request_changes.items() if x is not None})
    request = v["request"]
    assert isinstance(request, dict)
    if request_changes.get("target", "") is None:
        del request["target"]
    out = explained(interpreter.reply(v))
    assert out["verdict_range"] == {"low": "NotApplicable", "high": "Permit"}
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


# --- declines ---


def test_decline_names_smallest_unsupported_iri(interpreter: Interpreter) -> None:
    policy = (
        PREFIXES
        + """
ex:p a odrl:Set ; odrl:conflict odrl:prohibit ; odrl:permission ex:perm .
ex:perm a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a ;
    odrl:duty [ odrl:action odrl:compensate ] ;
    odrl:constraint [ odrl:leftOperand odrl:count ; odrl:operator odrl:lt ; odrl:rightOperand 5 ] .
"""
    )
    # odrl:constraint < odrl:duty < odrl:leftOperand in code-point order.
    first = interpreter.reply(vector(policy))
    assert first == {"unsupported": ODRL + "constraint"}
    assert interpreter.reply(vector(policy)) == first


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        ("ex:perm ex:weird ex:x .", {"unsupported": EX + "weird"}),  # unknown, on a rule
        ("ex:a odrl:partOf ex:coll .", {"unsupported": ODRL + "partOf"}),  # vocabulary, anywhere
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
        ({"sotw": {"facts": {"ex:x": {"status": "missing"}}}}, "sotw.facts"),
        ({"sotw": {"evidence": [EVIDENCE]}}, "sotw.evidence"),
        ({"sotw": {"activation": {"ex:d": "2026-01-01T00:00:00Z"}}}, "sotw.activation"),
        ({"sotw": {"closure": [["odrl:partOf", "ex:a", "ex:coll"]]}}, "sotw.closure"),
        ({"request": {"params": {"ex:purpose": {"@id": "ex:research"}}}}, "request.params"),
        ({"request": {"params": {"ex:purpose": []}}}, "request.params"),  # an empty set is a value
        ({"config": {"violations": "deny"}}, "config.violations"),
        ({"config": {"combination": "permit-overrides"}}, "config.combination"),
        ({"config": {"signers": [{"duty": "ex:d", "issuer": "ex:bank"}]}}, "config.signers"),
        ({"config": {"preference": "ex:p"}}, "config.preference"),
        # The smallest field wins, whatever the section order.
        (
            {
                "sotw": {"closure": [["odrl:partOf", "ex:a", "ex:c"]]},
                "config": {"violations": "deny"},
            },
            "config.violations",
        ),
        # A value the program compares, and cannot place (DESIGN.md § Values).
        ({"request": {"at": "2026-06-01T00:00:00"}}, "value: dateTime without timezone"),
        ({"sotw": {"effective_at": "2026-13-01T00:00:00Z"}}, "value: ill-typed xsd:dateTime"),
        # The input declines come first.
        (
            {"request": {"at": "2026-06-01T00:00:00", "params": {"ex:n": {"@value": "1"}}}},
            "request.params",
        ),
    ],
)
def test_input_declines(interpreter: Interpreter, changes: dict[str, Obj], reason: str) -> None:
    assert interpreter.reply(vector(**changes)) == {"unsupported": reason}


def test_empty_fields_are_not_declined(interpreter: Interpreter) -> None:
    v = vector(request={"params": {}}, sotw={"facts": {}, "evidence": [], "closure": []})
    assert verdict(interpreter.reply(v)) == "Permit"


def test_policy_declines_come_first(interpreter: Interpreter) -> None:
    policy = PREFIXES + POLICY_BODY + "ex:perm odrl:duty [ odrl:action odrl:compensate ] .\n"
    v = vector(policy, sotw={"evidence": [EVIDENCE]})
    assert interpreter.reply(v) == {"unsupported": ODRL + "duty"}


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
