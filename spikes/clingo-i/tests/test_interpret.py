"""What the corpus cannot see (DESIGN.md § Tests): integrity, declines, and a few verdicts
that the declines and integrity tests rely on."""

from __future__ import annotations

import pytest

from clingo_i.interpret import PROGRAM_FILES, Interpreter, load_programs
from clingo_i.json_types import Obj
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
    ("resolve.lp", 'verdict("NotApplicable") :- not deny, not ready.'),
]


@pytest.mark.parametrize(("file", "line"), DELETIONS)
def test_deleted_rule_fails_loudly(file: str, line: str) -> None:
    programs = load_programs()
    assert line in programs[file].splitlines(), f"{file} no longer has {line!r}"
    programs[file] = programs[file].replace(line, "")
    broken = Interpreter(INIT, programs)
    # Each vector exercises the deleted rule: an absent target gives a u part (kleene.lp),
    # a foreign action an f part (applies.lp), and NotApplicable its rule (resolve.lp).
    requests: dict[str, Obj] = {
        "kleene.lp": {"parties": {}},
        "applies.lp": {"action": "ex:other"},
        "resolve.lp": {"action": "ex:other"},
    }
    reply = broken.reply(vector(request=requests[file]))
    assert "error" in reply, reply


def test_program_files_are_all_loaded() -> None:
    assert sorted(load_programs()) == sorted(PROGRAM_FILES)


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


@pytest.mark.parametrize(
    ("section", "changes", "field"),
    [
        ("sotw", {"facts": {"ex:x": "1"}}, "sotw.facts"),
        ("sotw", {"evidence": [{"duty": "ex:d"}]}, "sotw.evidence"),
        ("sotw", {"activation": {"ex:d": "2026-01-01T00:00:00Z"}}, "sotw.activation"),
        ("sotw", {"closure": [["odrl:partOf", "ex:a", "ex:coll"]]}, "sotw.closure"),
        ("request", {"params": {"ex:purpose": "ex:research"}}, "request.params"),
        ("config", {"violations": "deny"}, "config.violations"),
        ("config", {"combination": "permit-overrides"}, "config.combination"),
    ],
)
def test_input_declines(interpreter: Interpreter, section: str, changes: Obj, field: str) -> None:
    assert interpreter.reply(vector(**{section: changes})) == {"unsupported": field}


# --- errors ---


def test_unknown_profile_is_an_error(interpreter: Interpreter) -> None:
    policy = PREFIXES + POLICY_BODY + "ex:p odrl:profile <https://example.org/unknown/> .\n"
    assert "error" in interpreter.reply(vector(policy))


def test_no_policy_is_an_error(interpreter: Interpreter) -> None:
    policy = PREFIXES + "ex:perm a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a .\n"
    assert "error" in interpreter.reply(vector(policy))
