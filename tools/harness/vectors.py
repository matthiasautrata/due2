"""Relation-level vector files: their authoring form expanded, and every check they must pass.

A vector file (conformance/README.md, Relation-level vectors) carries one corpus and the
scenarios evaluated against it, written in an authoring form. `check_vector_file` takes
the path of one file and returns its problems, `[]` when it is valid. It expands each
collection (`expand`), then checks it against `schema/collections.schema.json`, checks
that no two tuples share a key, and checks the corpus invariants of due2-workflows.md
§3.1, which W1 establishes and the evaluator trusts. The expected trace is checked as
`decide`'s output (`schema/evaluator.schema.json`), so it must state `verdict`.

Sorting into canonical order and computing collection ids belong to the runner of the
`decide` task, which sends collections; this module only validates them.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import cast

from jsonschema import Draft202012Validator
from referencing import Registry
from referencing.jsonschema import DRAFT202012, Schema, SchemaRegistry

from harness.json_types import Json, Obj, as_list, as_obj, as_str, loads
from harness.xsd_time import datetime_ok

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "schema"
VECTORS = ROOT / "conformance" / "vectors"
ODRL_TARGET = "http://www.w3.org/ns/odrl/2/target"
XSD_DATETIME = "http://www.w3.org/2001/XMLSchema#dateTime"
# The fields that name a tuple of another corpus relation, and that relation's key field.
REFERENCES = {
    "policy_id": ("policy", "policy_id"),
    "atom_id": ("atom", "atom_id"),
    "parent_id": ("atom", "atom_id"),
    "child_id": ("atom", "atom_id"),
    "constraint_id": ("constraint", "constraint_id"),
}

FILE_FIELDS = {"file", "source", "notes", "tags", "prefixes", "corpus", "scenarios"}
SCENARIO_FIELDS = {"name", "tags", "request", "sotw", "config", "expected"}
NOT_PREFIXES = {"party", "sha256"}  # scope values and digests start with these
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def _bad_datetimes(value: Json) -> list[str]:
    """The lexical forms of every `xsd:dateTime` literal in `value` that names no instant
    (`harness.xsd_time`). The schema checks only the shape, so `2026-02-30T12:00:00Z` passes it,
    and its `Instant` pattern already rejects a form with no timezone."""
    if isinstance(value, list):
        return [b for v in value for b in _bad_datetimes(v)]
    if isinstance(value, dict):
        lex = value.get("v")
        if value.get("t") == XSD_DATETIME and isinstance(lex, str):
            return [] if datetime_ok(lex) else [lex]
        return [b for v in value.values() for b in _bad_datetimes(v)]
    return []


def _load(name: str) -> Obj:
    return as_obj(loads((SCHEMA / name).read_text()), name)


class Schemas:
    """The validators of each collection, and the key, optional, and `Digest` fields of each
    relation, read from `schema/`."""

    def __init__(self) -> None:
        collections, evaluator = _load("collections.schema.json"), _load("evaluator.schema.json")
        registry: SchemaRegistry = Registry[Schema]().with_resources(
            (as_str(s["$id"], "$id"), DRAFT202012.create_resource(s))
            for s in (collections, evaluator)
        )
        defs = as_obj(collections["$defs"], "$defs")
        self.relations: dict[str, dict[str, Obj]] = {}
        for c in ("Corpus", "Request", "Sotw", "Config", "Trace"):
            props = as_obj(as_obj(defs[c], c)["properties"], c)
            self.relations[c] = {r: as_obj(s, r) for r, s in props.items()}
        base = as_str(collections["$id"], "$id")
        self.validators = {
            c: Draft202012Validator({"$ref": f"{base}#/$defs/{c}"}, registry=registry)
            for c in self.relations
        }
        self.validators["Expected"] = Draft202012Validator(
            {"$ref": f"{as_str(evaluator['$id'], '$id')}#/$defs/DecideOutput"}, registry=registry
        )

    def key(self, collection: str, relation: str) -> list[str]:
        return [
            as_str(k, "x-key") for k in as_list(self.relations[collection][relation]["x-key"], "")
        ]

    def digests(self, collection: str, relation: str) -> set[str]:
        """The fields of a relation whose type is `Digest`."""
        items = as_obj(self.relations[collection][relation]["items"], relation)
        props = as_obj(items["properties"], relation)
        return {f for f, s in props.items() if as_obj(s, f).get("$ref") == "#/$defs/Digest"}

    def optional(self, collection: str, relation: str) -> set[str]:
        items = as_obj(self.relations[collection][relation]["items"], relation)
        required = {as_str(f, "") for f in as_list(items["required"], relation)}
        return set(as_obj(items["properties"], relation)) - required


def _expand_value(value: Json, prefixes: dict[str, str]) -> Json:
    """A prefixed name becomes its IRI. A literal's lexical form `v` and language `l` stay."""
    if isinstance(value, str):
        head, colon, rest = value.partition(":")
        return prefixes[head] + rest if colon and head in prefixes else value
    if isinstance(value, dict):
        return {k: v if k in ("v", "l") else _expand_value(v, prefixes) for k, v in value.items()}
    return value


def _digest_placeholders(t: Json, fields: set[str]) -> Json:
    """The tuple with each placeholder name in `fields` replaced by its digest (`expand`)."""
    if not isinstance(t, dict):
        return t  # reported by the schema
    return {
        f: "sha256:" + hashlib.sha256(v.encode()).hexdigest()
        if f in fields and isinstance(v, str) and not DIGEST.match(v)
        else v
        for f, v in t.items()
    }


def expand(
    raw: Json, collection: str, prefixes: dict[str, str], schemas: Schemas, where: str
) -> tuple[Obj, list[str]]:
    """One collection from the authoring form: tables to tuples, prefixes expanded, a
    repeated tuple counted once, and an empty relation omitted. Returns it and its problems.

    `collection` selects the relations, their optional fields, and, for `"Trace"`, the rule
    below. In the expected trace, a `Digest` field may hold a placeholder name instead of a digest,
    because the bytes behind the derived ids are open (#107). The name becomes the digest
    of its UTF-8 bytes, so it passes the schema, and two tuples that use one name keep one
    value. The comparison then matches names up to renaming (conformance/README.md)."""
    problems: list[str] = []
    out: Obj = {}
    for rel, value in as_obj(raw, where).items():
        tuples: list[Json] = []
        if isinstance(value, dict):  # the table form: {"fields": [...], "rows": [[...]]}
            fields = [as_str(f, rel) for f in as_list(value.get("fields"), f"{where}.{rel}")]
            optional = (
                schemas.optional(collection, rel)
                if rel in schemas.relations[collection]
                else set[str]()
            )
            for row in as_list(value.get("rows"), f"{where}.{rel}"):
                cells = as_list(row, f"{where}.{rel}")
                if len(cells) != len(fields):
                    problems.append(
                        f"{where}.{rel}: a row of {len(cells)} values for {len(fields)} fields"
                    )
                    continue
                if any(c is None and f not in optional for f, c in zip(fields, cells, strict=True)):
                    problems.append(f"{where}.{rel}: null in a field that is not optional")
                tuples.append({f: c for f, c in zip(fields, cells, strict=True) if c is not None})
        else:
            tuples = as_list(value, f"{where}.{rel}")
        if collection == "Trace" and rel in schemas.relations[collection]:
            tuples = [_digest_placeholders(t, schemas.digests(collection, rel)) for t in tuples]
        unique: list[Json] = []
        for t in (_expand_value(t, prefixes) for t in tuples):
            if t not in unique:
                unique.append(t)
        if unique:
            out[rel] = unique
    return out, problems


def check_collection(
    coll: Obj, collection: str, validator: str, schemas: Schemas, where: str
) -> list[str]:
    """Schema errors, two tuples with one key that differ elsewhere (set semantics,
    due2-workflows.md §2), and an `xsd:dateTime` whose shape the schema accepts but which names
    no instant.

    `validator` names the schema: a collection, or `"Expected"`, the trace as `decide`'s
    output, which must contain `verdict`. `collection` names the relations and keys."""
    problems = [
        f"{where}: {'/'.join(map(str, e.absolute_path)) or '(top)'}: {e.message}"
        # jsonschema's stubs leave iter_errors's overloads partly untyped.
        for e in schemas.validators[validator].iter_errors(coll)  # pyright: ignore[reportUnknownMemberType]
    ]
    for rel, tuples in coll.items():
        if rel not in schemas.relations[collection] or not isinstance(tuples, list):
            continue  # reported by the schema
        key = schemas.key(collection, rel)
        seen: dict[str, Json] = {}
        for t in tuples:
            if not isinstance(t, dict):
                continue
            k = repr([t.get(f) for f in key])
            if k in seen and seen[k] != t:
                problems.append(f"{where}.{rel}: two tuples with key {k}")
            seen[k] = t
    problems += [f"{where}: no such xsd:dateTime: {lex!r}" for lex in _bad_datetimes(coll)]
    return problems


def check_invariants(corpus: Obj, where: str) -> list[str]:
    """The invariants of due2-workflows.md §3.1 that W1 establishes. A missing relation is
    empty, so a reference into it names nothing."""

    def rows(rel: str) -> list[Obj]:
        return [cast(Obj, t) for t in cast(list[Json], corpus.get(rel, []))]

    problems: list[str] = []
    effect = {cast(str, t["atom_id"]): t["effect"] for t in rows("atom")}
    # A root tuple for each policy that states the atom, so a shared one has several (decisions/0036).
    roots = {cast(str, t["atom_id"]) for t in rows("root")}
    for t in rows("atom"):
        a = cast(str, t["atom_id"])
        if t["effect"] in ("Permit", "Forbid"):
            if a not in roots:
                problems.append(f"{where}: {t['effect']} atom {a} is not a root")
            if t.get("relation") != ODRL_TARGET:
                problems.append(f"{where}: {t['effect']} atom {a} has no relation odrl:target")
        if ("relation" in t) != ("relation_value" in t):
            problems.append(f"{where}: atom {a} has one of relation and relation_value")
    keys = {rel: {str(t.get(field)) for t in rows(rel)} for rel, field in set(REFERENCES.values())}
    for rel in corpus:
        for t in rows(rel):
            for field, (target, _) in REFERENCES.items():
                if field in t and str(t[field]) not in keys[target]:
                    problems.append(f"{where}: {rel}.{field} {t[field]} names no {target}")
    # Only a duty's condition is kept in clauses (decisions/0028, decisions/0036). An atom
    # that names nothing is reported above, so only an atom of the wrong effect is here.
    for rel, oblige in (("atom_constraint", False), ("duty_constraint", True)):
        for t in rows(rel):
            a = cast(str, t["atom_id"])
            if a in effect and (effect[a] == "Oblige") != oblige:
                problems.append(f"{where}: {rel} {t['constraint_id']} on {effect[a]} atom {a}")
    children: dict[str, list[str]] = {}
    for t in rows("edge"):
        parent, child = cast(str, t["parent_id"]), cast(str, t["child_id"])
        children.setdefault(parent, []).append(child)
        if effect.get(child) != "Oblige":
            problems.append(f"{where}: edge child {child} is not an Oblige atom")
    # Depth-first search: a node met again while still on the path closes a cycle.
    state: dict[str, int] = {}  # 1 on the current path, 2 done

    def visit(node: str) -> bool:
        state[node] = 1
        for c in children.get(node, []):
            if state.get(c) == 1 or (c not in state and visit(c)):
                return True
        state[node] = 2
        return False

    if any(n not in state and visit(n) for n in list(children)):
        problems.append(f"{where}: edge has a cycle")
    return problems


def _check_tags(holder: Obj, where: str) -> list[str]:
    tags = holder.get("tags", [])
    ok = isinstance(tags, list) and all(isinstance(t, str) for t in tags)
    return [] if ok else [f"{where}: `tags` is not a list of strings"]


def check_vector_file(path: Path, schemas: Schemas) -> list[str]:
    """Every problem of one vector file; `[]` when it is valid."""
    doc = as_obj(loads(path.read_text()), path.name)
    name = path.stem
    problems = [f"{name}: unknown field {k}" for k in sorted(set(doc) - FILE_FIELDS)]
    if doc.get("file") != name:
        problems.append(f"{name}: `file` is {doc.get('file')!r}, not the file name")
    prefixes = {k: as_str(v, k) for k, v in as_obj(doc.get("prefixes", {}), "prefixes").items()}
    problems += [f"{name}: {p!r} may not be a prefix" for p in sorted(NOT_PREFIXES & set(prefixes))]
    problems += _check_tags(doc, name)

    corpus, more = expand(doc.get("corpus", {}), "Corpus", prefixes, schemas, f"{name}.corpus")
    problems += more + check_collection(corpus, "Corpus", "Corpus", schemas, f"{name}.corpus")
    problems += check_invariants(corpus, f"{name}.corpus")

    seen: set[str] = set()
    for raw in as_list(doc.get("scenarios"), f"{name}.scenarios"):
        s = as_obj(raw, name)
        sname = as_str(s.get("name"), f"{name}: scenario name")
        where = f"{name}/{sname}"
        if sname in seen:
            problems.append(f"{where}: duplicate scenario name")
        seen.add(sname)
        problems += [f"{where}: unknown field {k}" for k in sorted(set(s) - SCENARIO_FIELDS)]
        problems += _check_tags(s, where)
        for field, collection in (("request", "Request"), ("sotw", "Sotw"), ("config", "Config")):
            coll, more = expand(s.get(field, {}), collection, prefixes, schemas, f"{where}.{field}")
            problems += more + check_collection(
                coll, collection, collection, schemas, f"{where}.{field}"
            )
        expected = as_obj(s.get("expected"), f"{where}.expected")
        problems += [
            f"{where}.expected: unknown field {k}" for k in sorted(set(expected) - {"trace", "why"})
        ]
        if not isinstance(expected.get("why"), str):
            problems.append(f"{where}.expected: no `why`")
        trace, more = expand(
            expected.get("trace", {}), "Trace", prefixes, schemas, f"{where}.trace"
        )
        problems += more + check_collection(trace, "Trace", "Expected", schemas, f"{where}.trace")
    return problems
