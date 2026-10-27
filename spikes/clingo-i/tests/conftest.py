"""Inline modules and vectors for the spike's own tests (TESTS.md).

The modules are a small stand-in for the shipped profiles: an action hierarchy in the
core, and one profile with a policy subclass and a conflict default.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from clingo_i.interpret import Interpreter
from clingo_i.json_types import Obj

SPIKE = Path(__file__).resolve().parents[1]
PROF = "https://example.org/prof/"

PREFIXES = """\
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix dct:  <http://purl.org/dc/terms/> .
@prefix ex:   <https://example.org/> .
"""

CORE = PREFIXES + "odrl:play odrl:includedIn odrl:use .\n"
PROFILE = (
    PREFIXES
    + f"<{PROF}> odrl:conflict odrl:prohibit .\n"
    + "ex:Contract rdfs:subClassOf odrl:Agreement .\n"
)
INIT: Obj = {
    "modules": {"core.ttl": CORE, "prof.ttl": PROFILE},
    "core": ["core.ttl"],
    "profiles": {PROF: ["prof.ttl"]},
}

DPROD = "https://ekgf.org/dprod/spec/develop/"
DUE2 = "https://w3id.org/due2/profile#"
# INIT with the party roles of profiles/due2-core.ttl and profiles/dprod.ttl, for duties.
DUTY_INIT: Obj = {
    "modules": {
        "core.ttl": CORE
        + f"@prefix due2: <{DUE2}> .\nodrl:assignee due2:playsRole due2:bearer .\n"
        + "due2:attestingParty due2:playsRole due2:attester .\n",
        "prof.ttl": PROFILE,
        "dprod.ttl": f"@prefix due2: <{DUE2}> .\n@prefix dprod: <{DPROD}> .\n"
        + "dprod:subjectOfDuty due2:playsRole due2:bearer .\n",
    },
    "core": ["core.ttl"],
    "profiles": {PROF: ["prof.ttl"], DPROD: ["dprod.ttl"]},
}

# A permission on use of ex:a for ex:alice, and a prohibition on use of ex:b.
POLICY = (
    PREFIXES
    + """
ex:p a odrl:Set ;
    odrl:conflict odrl:prohibit ;
    odrl:permission ex:perm ;
    odrl:prohibition ex:forbid .
ex:perm a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a ; odrl:assignee ex:alice .
ex:forbid a odrl:Prohibition ; odrl:action odrl:use ; odrl:target ex:b .
"""
)

BASE: Obj = {
    "case": "test",
    "scenario": "test",
    "policies": [POLICY],
    "prefixes": {"odrl": "http://www.w3.org/ns/odrl/2/", "ex": "https://example.org/"},
    "request": {
        "reference": "req-1",
        "action": "odrl:play",
        "target": "ex:a",
        "at": "2026-06-01T00:00:00Z",
        "parties": {"odrl:assignee": "ex:alice"},
        "params": {},
    },
    "sotw": {
        "effective_at": "2026-06-01T00:00:00Z",
        "facts": {},
        "evidence": [],
        "activation": {},
        "closure": [],
    },
}


def vector(policy: str | None = None, /, **sections: Obj) -> Obj:
    """BASE with the policy replaced and each named section updated key by key."""
    v = copy.deepcopy(BASE)
    if policy is not None:
        v["policies"] = [policy]
    for name, changes in sections.items():
        section = v[name]
        assert isinstance(section, dict)
        section.update(changes)
    return v


@pytest.fixture(scope="session")
def interpreter() -> Interpreter:
    return Interpreter(INIT)


@pytest.fixture(scope="session")
def duty_interpreter() -> Interpreter:
    return Interpreter(DUTY_INIT)
