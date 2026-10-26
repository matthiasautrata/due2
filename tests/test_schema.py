"""The port schema (`schema/`) and the relation-level vector files it validates.

The schema is generated from due2-workflows.md §3 by `tools/gen_schema.py`; these tests
guard that the committed schema is that output, that it is valid JSON Schema, and that
the vector-file checks of `harness.vectors` reject what conformance/README.md says makes
a vector file invalid.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest
from gen_schema import SCHEMA, generate
from harness.json_types import Obj
from harness.vectors import VECTORS, Schemas, check_collection, check_vector_file, expand
from jsonschema import Draft202012Validator

FIXTURE = Path(__file__).parent / "fixtures" / "vectors" / "due2-one-permission.json"


@pytest.fixture(scope="module")
def schemas() -> Schemas:
    return Schemas()


def test_committed_schema_is_generated_from_the_spec() -> None:
    """Guards drift: a due2-workflows.md §3 edit to a relation, field, key, or type with no matching schema
    edit, or a hand edit of the schema. Without it, the schema and the spec could disagree
    and the vectors would be checked against the wrong one."""
    for name, content in generate().items():
        assert (SCHEMA / name).read_text() == content, (
            f"schema/{name} is stale: run uv run python tools/gen_schema.py"
        )


@pytest.mark.parametrize("name", ["collections.schema.json", "evaluator.schema.json"])
def test_schema_is_valid_json_schema(name: str) -> None:
    """Guards a schema that is not 2020-12 JSON Schema: validators would reject it, or
    silently ignore a misspelt keyword's constraint."""
    Draft202012Validator.check_schema(json.loads((SCHEMA / name).read_text()))


@pytest.mark.parametrize("path", sorted(VECTORS.glob("*.json")), ids=lambda p: p.stem)
def test_every_vector_file_is_valid(path: Path, schemas: Schemas) -> None:
    """Guards a committed vector file that the harness would reject: without it, the file's
    scenarios would fail every evaluator for a fault of the file."""
    assert check_vector_file(path, schemas) == []


def test_the_fixture_is_valid(schemas: Schemas) -> None:
    """The baseline of the mutations below: without it, a mutation could be rejected for a
    fault the fixture already had."""
    assert check_vector_file(FIXTURE, schemas) == []


def _corpus(doc: Obj) -> Obj:
    return cast(Obj, doc["corpus"])


def _scenario(doc: Obj) -> Obj:
    return cast(list[Obj], doc["scenarios"])[0]


def _atom(doc: Obj) -> Obj:
    return cast(list[Obj], _corpus(doc)["atom"])[0]


def _undefined_field(doc: Obj) -> None:
    _atom(doc)["weight"] = 1


def _key_clash(doc: Obj) -> None:
    _corpus(doc)["atom"] = [_atom(doc), {**_atom(doc), "action": "odrl:read"}]


def _not_a_root(doc: Obj) -> None:
    _corpus(doc)["root"] = []


def _add_constraint(doc: Obj) -> None:
    _corpus(doc)["constraint"] = [
        {
            "constraint_id": "ex:c1",
            "left_operand": "odrl:purpose",
            "operator": "odrl:eq",
            "datatype": "xsd:anyURI",
        }
    ]


def _clause_on_a_permit(doc: Obj) -> None:
    _add_constraint(doc)
    _corpus(doc)["duty_constraint"] = [
        {"atom_id": "ex:a1", "clause": 0, "constraint_id": "ex:c1", "scope": "rule"}
    ]


def _conjunct_on_a_duty(doc: Obj) -> None:
    _add_constraint(doc)
    duty = {**_atom(doc), "atom_id": "ex:a2", "effect": "Oblige"}
    cast(list[Obj], _corpus(doc)["atom"]).append(duty)
    _corpus(doc)["atom_constraint"] = [
        {"atom_id": "ex:a2", "constraint_id": "ex:c1", "scope": "rule"}
    ]


def _short_row(doc: Obj) -> None:
    table = cast(Obj, _corpus(doc)["atom_party"])
    table["rows"] = [["ex:a1", "odrl:assignee"]]


def _null_required(doc: Obj) -> None:
    table = cast(Obj, _corpus(doc)["atom_party"])
    table["rows"] = [["ex:a1", "odrl:assignee", None]]


def _two_verdicts(doc: Obj) -> None:
    trace = cast(Obj, cast(Obj, _scenario(doc)["expected"])["trace"])
    trace["verdict"] = [
        {"value": "Permit", "frontier_complete": True, "exact": True},
        {"value": "Deny", "frontier_complete": True, "exact": True},
    ]


def _no_verdict(doc: Obj) -> None:
    trace = cast(Obj, cast(Obj, _scenario(doc)["expected"])["trace"])
    del trace["verdict"]


def _instant_without_timezone(doc: Obj) -> None:
    sotw = cast(list[Obj], cast(Obj, _scenario(doc)["sotw"])["sotw"])
    sotw[0]["effective_at"] = {"v": "2026-06-01T00:00:00", "t": "xsd:dateTime"}


def _impossible_instant(doc: Obj) -> None:
    sotw = cast(list[Obj], cast(Obj, _scenario(doc)["sotw"])["sotw"])
    sotw[0]["effective_at"] = {"v": "2026-02-30T12:00:00Z", "t": "xsd:dateTime"}


def _padded_year(doc: Obj) -> None:
    sotw = cast(list[Obj], cast(Obj, _scenario(doc)["sotw"])["sotw"])
    sotw[0]["effective_at"] = {"v": "02026-01-01T00:00:00Z", "t": "xsd:dateTime"}


def _relation_without_value(doc: Obj) -> None:
    del _atom(doc)["relation_value"]


def _root_naming_no_atom(doc: Obj) -> None:
    _corpus(doc)["root"] = [
        {"atom_id": "ex:a1", "policy_id": "ex:p1"},
        {"atom_id": "ex:a9", "policy_id": "ex:p1"},
    ]


def _root_naming_no_policy(doc: Obj) -> None:
    _corpus(doc)["root"] = [{"atom_id": "ex:a1", "policy_id": "ex:p9"}]


def _edge_from_no_atom(doc: Obj) -> None:
    duty = {**_atom(doc), "atom_id": "ex:a2", "effect": "Oblige"}
    cast(list[Obj], _corpus(doc)["atom"]).append(duty)
    _corpus(doc)["edge"] = [{"parent_id": "ex:a9", "child_id": "ex:a2"}]


def _constraint_on_no_atom(doc: Obj) -> None:
    _add_constraint(doc)
    _corpus(doc)["atom_constraint"] = [
        {"atom_id": "ex:a9", "constraint_id": "ex:c1", "scope": "rule"}
    ]


def _config_without_bound(doc: Obj) -> None:
    config = cast(list[Obj], cast(Obj, _scenario(doc)["config"])["config"])
    del config[0]["max_mixed"]


def _party_as_prefix(doc: Obj) -> None:
    cast(Obj, doc["prefixes"])["party"] = "https://example.org/party/"


def test_a_placeholder_derived_id_becomes_a_digest(schemas: Schemas) -> None:
    """Guards the authoring rule for derived ids (#107): without it, an expected trace that
    names an alternative `alt1`, as conformance/README.md allows, would fail the schema."""
    raw: Obj = {
        "alternative": [{"alt_id": "alt1", "permission_id": "ex:a1"}],
        "alt_duty": [{"alt_id": "alt1", "duty_id": "ex:d1"}],
    }
    trace, problems = expand(raw, "Trace", {"ex": "https://example.org/"}, schemas, "t")
    assert problems == []
    assert check_collection(trace, "Trace", "Trace", schemas, "t") == []
    alt = cast(list[Obj], trace["alternative"])[0]["alt_id"]
    assert alt == cast(list[Obj], trace["alt_duty"])[0]["alt_id"]
    assert alt == "sha256:" + hashlib.sha256(b"alt1").hexdigest()


# Each mutation breaks one rule of conformance/README.md (Relation-level vectors) or of
# due2-workflows.md §2 and §3; the check that rejects it is named in the id.
MUTATIONS: dict[str, Callable[[Obj], None]] = {
    "schema: a field due2-workflows.md §3 does not define": _undefined_field,
    "set semantics: two tuples with one key": _key_clash,
    "invariant: a Permit atom that is not a root": _not_a_root,
    "invariant: a duty_constraint on a Permit atom (decisions/0028)": _clause_on_a_permit,
    "invariant: an atom_constraint on an Oblige atom (decisions/0036)": _conjunct_on_a_duty,
    "table form: a row shorter than its fields": _short_row,
    "table form: null in a required field": _null_required,
    "schema: an empty-key relation with two tuples": _two_verdicts,
    "decide output: no verdict": _no_verdict,
    "schema: an Instant with no timezone (decisions/0024)": _instant_without_timezone,
    "value: an Instant on 30 February": _impossible_instant,
    "value: an Instant whose year has a leading zero beyond four digits": _padded_year,
    "invariant: a relation with no relation_value": _relation_without_value,
    "invariant: a root that names no atom": _root_naming_no_atom,
    "invariant: a root that names no policy": _root_naming_no_policy,
    "invariant: an edge whose parent names no atom": _edge_from_no_atom,
    "invariant: a constraint on no atom": _constraint_on_no_atom,
    "schema: config without max_mixed": _config_without_bound,
    "prefixes: `party` as a prefix name": _party_as_prefix,
}


@pytest.mark.parametrize("mutate", MUTATIONS.values(), ids=MUTATIONS.keys())
def test_a_broken_vector_file_is_rejected(
    mutate: Callable[[Obj], None], schemas: Schemas, tmp_path: Path
) -> None:
    """Guards a check that passes everything: each mutation of the valid fixture must be
    reported, so a vector file with that fault cannot reach an evaluator as valid."""
    doc = cast(Obj, copy.deepcopy(json.loads(FIXTURE.read_text())))
    mutate(doc)
    path = tmp_path / FIXTURE.name
    path.write_text(json.dumps(doc))
    assert check_vector_file(path, schemas) != []
