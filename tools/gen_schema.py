"""Generates the port schema, `schema/*.schema.json`, from due2-workflows.md §2 and §3.

The relations, their fields, keys, and value types are parsed from the relation blocks of
due2-workflows.md §3.1 to §3.3, §3.5, and §3.6, so the schema cannot add or drop a field the
spec does not.
What the blocks do not carry is stated here and checked against the spec text: each
`Enum` field's values (the field's row in due2-workflows.md §3, or the section it cites), and the
codes a diagnostic may carry (the registry of due2-diagnostics.md §3). The shapes no relation
block states, a diagnostic (due2-diagnostics.md §1, *JSON form*) and an error
(due2-platform.md §1.2), are written here. The schema files and their version rule are described in
`schema/README.md`. `tests/test_schema.py` fails when the committed files
differ from what this script generates.

Run: uv run python tools/gen_schema.py
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from harness.json_types import Json, Obj

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / "docs" / "spec" / "due2-workflows.md"
DIAGNOSTICS = ROOT / "docs" / "spec" / "due2-diagnostics.md"
SCHEMA = ROOT / "schema"
# MAJOR.MINOR, by the rule of due2-platform.md §2.10: MINOR when every document valid under the
# previous version stays valid, MAJOR otherwise. MAJOR is part of every $id.
VERSION = "2.2"
BASE = f"https://w3id.org/due2/schema/{VERSION.split('.')[0]}/"

# Collection → the due2-workflows.md §3.N whose relation block declares it, and the first
# relation of that block. §3.3 declares two collections, the SOTW and `Reads`; §3.4 states
# constants, not a collection.
SECTIONS = {
    "Corpus": ("3.1", "policy"),
    "Request": ("3.2", "request"),
    "Sotw": ("3.3", "sotw"),
    "Reads": ("3.3", "read_param"),
    "Trace": ("3.5", "evaluation"),
    "Lineage": ("3.6", "lineage"),
}

XSD_DATETIME = "http://www.w3.org/2001/XMLSchema#dateTime"
IRI = r"[A-Za-z][A-Za-z0-9+.\-]*:[^\s<>\"{}|\\^`]+"
VERDICTS = ["Permit", "Deny", "Pending", "NotApplicable", "Indeterminate"]
PREDICATES = ["applies", "in_force", "owed", "fulfilled"]
KINDS = ["action", "relation", "party", "constraint", "evidence", "fact"]
CONFLICT = ["prohibit", "perm", "invalid"]
CROSS_POLICY = ["prohibit-overrides"]  # due2-workflows.md §6.2

# (collection, relation, field) → the field's values, from its row in due2-workflows.md §3. "<warnings>"
# stands for the warning codes of due2-diagnostics.md §3.
ENUMS: dict[tuple[str, str, str], list[str]] = {
    ("Corpus", "policy", "conflict"): CONFLICT,
    ("Corpus", "atom", "effect"): ["Permit", "Forbid", "Oblige"],
    ("Corpus", "constraint", "source"): ["request", "state", "context", "witness"],
    ("Corpus", "constraint", "cardinality"): ["one", "set"],
    ("Corpus", "atom_constraint", "scope"): ["rule", "action", "relation", "party:<function>"],
    ("Corpus", "duty_constraint", "scope"): ["rule", "action", "relation", "party:<function>"],
    ("Corpus", "duty", "scope"): ["member", "grant"],
    ("Corpus", "diagnostic", "code"): ["<warnings>"],
    ("Sotw", "fact", "status"): ["resolved", "missing", "invalid", "conflict", "unresolved"],
    ("Sotw", "closure_answer", "status"): ["resolved", "unresolved"],
    ("Reads", "read_evidence_edges", "field"): ["issuer", "actor"],
    ("Trace", "finding", "predicate"): PREDICATES,
    ("Trace", "basis", "predicate"): PREDICATES,
    ("Trace", "basis", "kind"): KINDS,
    ("Trace", "unknown_part", "predicate"): PREDICATES,
    ("Trace", "unknown_part", "kind"): KINDS,
    ("Trace", "unknown_part", "status"): ["missing", "invalid", "conflict", "unresolved", "misfit"],
    ("Trace", "witness_part", "status"): ["missing", "invalid", "conflict", "unresolved", "misfit"],
    ("Trace", "instance", "status"): ["fulfilled", "outstanding", "violated", "unknown"],
    ("Trace", "eliminated", "rule"): [*CONFLICT, *CROSS_POLICY, "violated_precondition"],
    ("Trace", "verdict", "value"): VERDICTS,
    ("Trace", "verdict_basis", "role"): [
        "prohibition",
        "permission",
        "duty",
        "unknown",
        "obligation",
        "closed",
    ],
    ("Trace", "verdict_range", "low"): VERDICTS[:4],
    ("Trace", "verdict_range", "high"): VERDICTS[:4],
    ("Trace", "diagnostic", "code"): ["<warnings>"],
}

# The value types of due2-workflows.md §2, as JSON Schema.
VALUE_TYPES: dict[str, Obj] = {
    "Id": {
        "description": "An IRI, in full, compared by equality only.",
        "type": "string",
        "format": "iri",
        "pattern": f"^{IRI}$",
    },
    "Literal": {
        "description": "A literal: its lexical form, its datatype, and its language if any.",
        "type": "object",
        "properties": {
            "v": {"type": "string"},
            "t": {"$ref": "#/$defs/Id"},
            "l": {"type": "string", "pattern": "^[A-Za-z]{1,8}(-[A-Za-z0-9]{1,8})*$"},
        },
        "required": ["v", "t"],
        "additionalProperties": False,
    },
    "Term": {
        "description": "An Id or a literal; a string is an Id, an object a literal.",
        "anyOf": [{"$ref": "#/$defs/Id"}, {"$ref": "#/$defs/Literal"}],
    },
    "Instant": {
        "description": "An xsd:dateTime literal with a timezone (decisions/0024).",
        "type": "object",
        "properties": {
            "v": {
                "type": "string",
                "pattern": (
                    r"^-?[0-9]{4,}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
                    r"(\.[0-9]+)?(Z|[+\-][0-9]{2}:[0-9]{2})$"
                ),
            },
            "t": {"const": XSD_DATETIME},
        },
        "required": ["v", "t"],
        "additionalProperties": False,
    },
    "Truth": {"description": "Kleene truth value.", "enum": ["T", "F", "U"]},
    "Flag": {"type": "boolean"},
    "Count": {
        "description": "An integer within ±2^53.",
        "type": "integer",
        "minimum": -(2**53),
        "maximum": 2**53,
    },
    "Digest": {
        "description": "sha256: and 64 lowercase hex digits.",
        "type": "string",
        "pattern": "^sha256:[0-9a-f]{64}$",
    },
    "String": {"description": "Text that is neither an IRI nor a literal.", "type": "string"},
}


@dataclass(frozen=True)
class Field:
    name: str
    type: str
    optional: bool


@dataclass(frozen=True)
class Relation:
    name: str
    key: tuple[str, ...]  # empty: the relation holds one tuple
    fields: tuple[Field, ...]  # in declaration order


LINE = re.compile(r"^(\w+)\s+\(([^)]*)\)$")
FIELD = re.compile(r"^(\w+)(\?)?(?::\s*(\w+))?$")


def parse_relation(line: str) -> Relation:
    """One line of a due2-workflows.md §3 block, such as `fact (property | status: Enum)`."""
    m = LINE.match(line.strip())
    if m is None:
        raise ValueError(f"not a relation: {line!r}")
    name, body = m.groups()
    # No `|`: keyed by every field (due2-workflows.md §2).
    key_part, _, value_part = body.partition("|") if "|" in body else (body, "", "")
    key: list[Field] = []
    values: list[Field] = []
    for part, into in ((key_part, key), (value_part, values)):
        for raw in filter(None, (s.strip() for s in part.split(","))):
            f = FIELD.match(raw)
            if f is None:
                raise ValueError(f"{name}: not a field: {raw!r}")
            into.append(Field(f[1], f[3] or "Id", f[2] is not None))
    return Relation(name, tuple(f.name for f in key), (*key, *values))


def spec_relations(text: str) -> dict[str, list[Relation]]:
    """The relations of each collection in `SECTIONS`, from the block of its section that
    starts with its first relation."""
    out: dict[str, list[Relation]] = {}
    for collection, (number, first) in SECTIONS.items():
        section = re.search(
            rf"^### {re.escape(number)} .*?(?=^### )", text, re.MULTILINE | re.DOTALL
        )
        block = section and re.search(
            rf"^```text\n({re.escape(first)}\s.*?)^```", section[0], re.MULTILINE | re.DOTALL
        )
        if not block:
            raise ValueError(f"due2-workflows.md §{number}: no relation block for {collection}")
        out[collection] = [parse_relation(line) for line in block[1].splitlines() if line]
    return out


def diagnostic_codes(text: str) -> dict[str, str]:
    """Every code of due2-diagnostics.md §3 → its severity, `error` or `warning`."""
    return dict(sorted(re.findall(r"^\| `(\w+)` \| (error|warning) \|", text, re.MULTILINE)))


def field_schema(collection: str, rel: str, f: Field, warnings: list[str]) -> Json:
    if f.type != "Enum":
        if f.type not in VALUE_TYPES or f.type == "Literal":
            raise ValueError(f"{collection}.{rel}.{f.name}: unknown type {f.type}")
        return {"$ref": f"#/$defs/{f.type}"}
    values = ENUMS.get((collection, rel, f.name))
    if values is None:
        raise ValueError(f"{collection}.{rel}.{f.name}: an Enum with no values in ENUMS")
    if values == ["<warnings>"]:
        return {"enum": list(warnings)}
    if "party:<function>" in values:
        # A party constraint's scope names its function, an IRI: `party:<IRI>`.
        fixed = "|".join(re.escape(v) for v in values if v != "party:<function>")
        return {"type": "string", "pattern": f"^({fixed}|party:{IRI})$"}
    return {"enum": list(values)}


def relation_schema(collection: str, r: Relation, warnings: list[str]) -> Obj:
    props: Obj = {f.name: field_schema(collection, r.name, f, warnings) for f in r.fields}
    tuple_schema: Obj = {
        "type": "object",
        "properties": props,
        "required": [f.name for f in r.fields if not f.optional],
        "additionalProperties": False,
    }
    # Canonical form: an empty relation is omitted, tuples do not repeat (due2-workflows.md §2).
    schema: Obj = {"type": "array", "minItems": 1, "uniqueItems": True}
    if not r.key:
        schema["maxItems"] = 1
    schema["x-key"] = list(r.key)
    schema["items"] = tuple_schema
    return schema


def port_shapes(codes: dict[str, str]) -> Obj:
    """The two shapes a port returns besides collections: a diagnostic and an error."""
    return {
        "Diagnostic": {
            "description": "A W1 or publish diagnostic (due2-diagnostics.md §1).",
            "type": "object",
            "properties": {
                "code": {"enum": list(codes)},
                "severity": {"enum": ["error", "warning"]},
                # The nodes it is about, in the order due2-diagnostics.md §1 gives.
                "ref": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/Id"}},
                "message": {"$ref": "#/$defs/String"},
            },
            "required": ["code", "severity", "ref", "message"],
            "additionalProperties": False,
        },
        "Error": {
            "description": "A failed call, Error(cause) (due2-platform.md §1.2): not a verdict.",
            "type": "object",
            "properties": {"cause": {"$ref": "#/$defs/String"}},
            "required": ["cause"],
            "additionalProperties": False,
        },
    }


def collections_schema(
    relations: dict[str, list[Relation]], warnings: list[str], codes: dict[str, str]
) -> Obj:
    defs: Obj = {**VALUE_TYPES, **port_shapes(codes)}
    for collection, rels in relations.items():
        coll: Obj = {
            "type": "object",
            "properties": {r.name: relation_schema(collection, r, warnings) for r in rels},
            "additionalProperties": False,
        }
        # A singleton outside the trace states the request, SOTW, or W1 run itself; the
        # trace's are absent when not produced (verdict_range outside Indeterminate).
        singletons: list[Json] = [r.name for r in rels if not r.key]
        if collection != "Trace" and singletons:
            coll["required"] = singletons
        defs[collection] = coll
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": BASE + "collections.schema.json",
        "x-version": VERSION,
        "title": "due2 collections",
        "description": (
            "The six collections of due2-workflows.md §2-§3 in canonical form, and the "
            "Diagnostic and Error a port returns. "
            "Generated by tools/gen_schema.py; see schema/README.md."
        ),
        "$defs": defs,
    }


def evaluator_schema() -> Obj:
    def ref(name: str) -> Obj:
        return {"$ref": f"collections.schema.json#/$defs/{name}"}

    def call(*names: str) -> Obj:
        return {
            "type": "object",
            "properties": {n.lower(): ref(n) for n in names},
            "required": [n.lower() for n in names],
            "additionalProperties": False,
        }

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": BASE + "evaluator.schema.json",
        "x-version": VERSION,
        "title": "due2 evaluator port",
        "description": (
            "The two calls of due2-platform.md §2.1, inputs and outputs by value. "
            "Generated by tools/gen_schema.py; see schema/README.md."
        ),
        "$defs": {
            "PlanInput": call("Corpus", "Request"),
            "PlanOutput": ref("Reads"),
            "DecideInput": call("Corpus", "Request", "Sotw"),
            "DecideOutput": {**ref("Trace"), "required": ["evaluation", "verdict"]},
        },
    }


def normaliser_schema() -> Obj:
    def ref(name: str) -> Obj:
        return {"$ref": f"collections.schema.json#/$defs/{name}"}

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": BASE + "normaliser.schema.json",
        "x-version": VERSION,
        "title": "due2 normaliser port",
        "description": (
            "The output of normalise (due2-platform.md §2.8, due2-workflows.md §4): a corpus "
            "and its lineage, or a rejection. Generated by tools/gen_schema.py; see "
            "schema/README.md."
        ),
        "$defs": {
            "Rejection": {
                "description": "The run's diagnostics, at least one an error (due2-diagnostics.md §1).",
                "type": "object",
                "properties": {
                    "diagnostics": {
                        "type": "array",
                        "items": ref("Diagnostic"),
                        "contains": {"properties": {"severity": {"const": "error"}}},
                    }
                },
                "required": ["diagnostics"],
                "additionalProperties": False,
            },
            "NormaliseOutput": {
                "oneOf": [
                    {
                        # Warnings travel in the corpus's `diagnostic` relation.
                        "type": "object",
                        "properties": {"corpus": ref("Corpus"), "lineage": ref("Lineage")},
                        "required": ["corpus", "lineage"],
                        "additionalProperties": False,
                    },
                    {"$ref": "#/$defs/Rejection"},
                ]
            },
        },
    }


def check_enums_in_spec(text: str) -> None:
    """Raises if an Enum value stated here appears nowhere in due2-workflows.md, in code font
    or in a `{...}` list. It catches a misspelt or dropped value, not a value listed under
    the wrong field: the spec text is not tied to fields."""
    for where, values in ENUMS.items():
        for v in values:
            special = v in ("<warnings>", "party:<function>")
            if (
                not special
                and f"`{v}`" not in text
                and not re.search(rf"[{{ ,]{re.escape(v)}[,}} ]", text)
            ):
                raise ValueError(f"{'.'.join(where)}: {v!r} is not in due2-workflows.md")


def render(schema: Obj) -> str:
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def generate() -> dict[str, str]:
    """File name → content of every schema file."""
    text = WORKFLOWS.read_text()
    check_enums_in_spec(text)
    codes = diagnostic_codes(DIAGNOSTICS.read_text())
    warnings = [c for c, severity in codes.items() if severity == "warning"]
    return {
        "collections.schema.json": render(
            collections_schema(spec_relations(text), warnings, codes)
        ),
        "evaluator.schema.json": render(evaluator_schema()),
        "normaliser.schema.json": render(normaliser_schema()),
    }


def main() -> int:
    SCHEMA.mkdir(exist_ok=True)
    for name, content in generate().items():
        (SCHEMA / name).write_text(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
