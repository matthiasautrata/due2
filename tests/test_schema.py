"""The port schema (`schema/`) and the relation-level vector files it validates.

The schema is generated from due2-workflows.md §3 by `tools/gen_schema.py`; these tests
guard that the committed schema is that output, that it is valid JSON Schema, and that
the vector-file checks of `harness.vectors` reject what conformance/README.md says makes
a vector file invalid, and that the normaliser port's `Rejection` (due2-diagnostics.md §1,
*JSON form*) admits what the negative corpus cases expect and nothing without an error.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest
from gen_schema import SCHEMA, generate
from harness.json_types import Json, Obj
from harness.vectors import VECTORS, Schemas, check_collection, check_invariants, check_vector_file
from jsonschema import Draft202012Validator
from referencing import Registry
from referencing.jsonschema import DRAFT202012, Schema

CASES = Path(__file__).parents[1] / "conformance" / "cases"

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


@pytest.mark.parametrize(
    "name", ["collections.schema.json", "evaluator.schema.json", "normaliser.schema.json"]
)
def test_schema_is_valid_json_schema(name: str) -> None:
    """Guards a schema that is not 2020-12 JSON Schema: validators would reject it, or
    silently ignore a misspelt keyword's constraint."""
    Draft202012Validator.check_schema(json.loads((SCHEMA / name).read_text()))


def _errors(file: str, definition: str, doc: Obj) -> list[str]:
    """What `$defs/<definition>` of `schema/<file>` reports of `doc`, every file registered."""
    docs = [cast(Obj, json.loads(p.read_text())) for p in sorted(SCHEMA.glob("*.schema.json"))]
    registry = Registry[Schema]().with_resources(
        (cast(str, d["$id"]), DRAFT202012.create_resource(d)) for d in docs
    )
    base = next(cast(str, d["$id"]) for d in docs if cast(str, d["$id"]).endswith("/" + file))
    validator = Draft202012Validator({"$ref": f"{base}#/$defs/{definition}"}, registry=registry)
    # jsonschema's stubs leave iter_errors's overloads partly untyped.
    return [e.message for e in validator.iter_errors(doc)]  # pyright: ignore[reportUnknownMemberType]


def _rejection(codes: list[str], severity: str = "error") -> Obj:
    return {
        "diagnostics": [
            {"code": c, "severity": severity, "ref": ["https://example.org/p"], "message": ""}
            for c in codes
        ]
    }


def test_every_expected_rejection_is_a_valid_rejection() -> None:
    """Guards the code list against the registry: a code a negative corpus case expects, but
    the schema's `Diagnostic.code` lacks, would make W1's correct answer invalid at the port.
    Without it, a registry row the generator fails to parse goes unnoticed."""
    expected = [
        cast(Obj, json.loads(p.read_text())).get("expected_rejection")
        for p in sorted(CASES.glob("*/case.json"))
    ]
    codes = sorted({c for e in expected if e for c in cast(list[str], cast(Obj, e)["codes"])})
    assert codes
    assert _errors("normaliser.schema.json", "NormaliseOutput", _rejection(codes)) == []


def test_a_rejection_without_an_error_is_invalid() -> None:
    """Guards the `contains` clause: a run whose diagnostics are all warnings accepted the
    policy, so its output is a corpus, never a rejection (due2-workflows.md §4). Without it,
    a normaliser could return warnings alone and no corpus."""
    warnings_only = _rejection(["AnonymousEntity"], "warning")
    assert _errors("normaliser.schema.json", "NormaliseOutput", warnings_only) != []


def test_an_error_has_only_a_cause() -> None:
    """Guards the shape of `Error(cause)` (due2-platform.md §1.2): a caller branches on the
    error, so an error object must not pass for a trace or carry other fields."""
    assert _errors("collections.schema.json", "Error", {"cause": "contract violated"}) == []
    assert _errors("collections.schema.json", "Error", {"cause": "x", "verdict": "Deny"}) != []


@pytest.mark.parametrize("path", sorted(VECTORS.glob("*.json")), ids=lambda p: p.stem)
def test_every_vector_file_is_valid(path: Path, schemas: Schemas) -> None:
    """Guards a committed vector file that the harness would reject: without it, the file's
    scenarios would fail every evaluator for a fault of the file."""
    assert check_vector_file(path, schemas) == []


def test_the_fixture_is_valid(schemas: Schemas) -> None:
    """The baseline of the mutations below: without it, a mutation could be rejected for a
    fault the fixture already had."""
    assert check_vector_file(FIXTURE, schemas) == []


DIGEST = "sha256:" + "0" * 64
VERDICT: Obj = {"value": "Permit", "frontier_complete": True, "exact": True}


def test_a_decision_names_its_inputs() -> None:
    """Guards `DecideOutput` against a trace that does not say what it was decided from:
    `evaluation` holds the three input ids (decisions/0041, item 2), and a replay compares
    them. Without `evaluation` in `required`, an evaluator could omit it and still be valid."""
    evaluation: list[Json] = [{"corpus_id": DIGEST, "request_id": DIGEST, "sotw_id": DIGEST}]
    assert _errors("evaluator.schema.json", "DecideOutput", {"verdict": [VERDICT]}) != []
    doc: Obj = {"evaluation": evaluation, "verdict": [VERDICT]}
    assert _errors("evaluator.schema.json", "DecideOutput", doc) == []


def test_a_key_is_compared_by_value(schemas: Schemas) -> None:
    """Guards set semantics (due2-workflows.md §2) when a key holds an object: JSON member
    order is not significant, so two `instance` tuples whose `occurrence` differs only in
    member order share a key. Without it, a key built with `repr` tells them apart, and two
    statuses for one instance pass."""
    at = "2026-06-01T00:00:00Z"
    trace: Obj = {
        "verdict": [VERDICT],
        "instance": [
            {"atom_id": "ex:d", "occurrence": {"v": at, "t": "xsd:dateTime"},
             "status": "fulfilled", "passed": True},
            {"atom_id": "ex:d", "occurrence": {"t": "xsd:dateTime", "v": at},
             "status": "violated", "passed": True},
        ],
    }  # fmt: skip
    problems = check_collection(trace, "Trace", "Expected", schemas, "t")
    assert any("two tuples with key" in p for p in problems), problems


def _chain(n: int) -> Obj:
    """A corpus of one Permit root and `n` Oblige atoms, each the child of the one before."""
    target = "http://www.w3.org/ns/odrl/2/target"
    atoms: list[Json] = [
        {"atom_id": f"ex:a{i}", "policy_id": "ex:p", "effect": "Oblige" if i else "Permit",
         "action": "odrl:use", "relation": target, "relation_value": "ex:t"}
        for i in range(n + 1)
    ]  # fmt: skip
    edges: list[Json] = [{"parent_id": f"ex:a{i}", "child_id": f"ex:a{i + 1}"} for i in range(n)]
    return {
        "policy": [{"policy_id": "ex:p", "conflict": "perm", "version": "ex:pv1"}],
        "atom": atoms,
        "edge": edges,
        "root": [{"atom_id": "ex:a0", "policy_id": "ex:p"}],
    }


def test_a_deep_chain_is_checked() -> None:
    """Guards the cycle check against depth: a chain longer than Python's recursion limit,
    1000, is checked, and one back edge is a cycle. Without it, a recursive search raises
    `RecursionError` on a valid corpus."""
    corpus = _chain(1100)
    assert check_invariants(corpus, "c") == []
    cast(list[Obj], corpus["edge"]).append({"parent_id": "ex:a1100", "child_id": "ex:a1"})
    assert "c: edge has a cycle" in check_invariants(corpus, "c")


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
            "source": "request",
            "property": "odrl:purpose",
            "cardinality": "one",
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


def _scheme_of_no_constraint(doc: Obj) -> None:
    _corpus(doc)["constraint_scheme"] = [{"constraint_id": "ex:c9", "scheme": "ex:purposes"}]


def _sotw_without_effective_at(doc: Obj) -> None:
    sotw = cast(list[Obj], cast(Obj, _scenario(doc)["sotw"])["sotw"])
    del sotw[0]["effective_at"]


def _party_as_prefix(doc: Obj) -> None:
    cast(Obj, doc["prefixes"])["party"] = "https://example.org/party/"


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
    "invariant: a constraint_scheme that names no constraint (decisions/0047)": _scheme_of_no_constraint,
    "schema: a SOTW without effective_at": _sotw_without_effective_at,
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
