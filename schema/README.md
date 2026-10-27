# The port schema

These files state, in JSON Schema 2020-12, what the evaluator port of `due2-platform.md` §2.1 takes and returns: the collections of `due2-workflows.md` §3.1 to §3.5, among them `Reads`, the output of `plan` (`due2-workflows.md` §3.3), encoded as `due2-workflows.md` §2 states. They also state what the normaliser port of `due2-platform.md` §2.8 returns: a corpus and the lineage beside it (`due2-workflows.md` §3.6), which the evaluator never reads, or a rejection. Every port can fail with an `Error` instead (`due2-platform.md` §1.2). The normaliser's input, an RDF policy document and its profiles, is not a collection, and the schema does not state it. Read them if you write an evaluator, a normaliser, an adapter (REST or MCP, `due2-platform.md` §2.1), or a relation-level vector file (`conformance/README.md`).

| File | Defines |
|---|---|
| `collections.schema.json` | One definition per collection (`Corpus`, `Request`, `Sotw`, `Reads`, `Trace`, `Lineage`), one per value type of `due2-workflows.md` §2, `Literal`, the object form a `Term` or `Instant` takes, and the two shapes a port returns besides collections: `Diagnostic` (`due2-diagnostics.md` §1, *JSON form*) and `Error`, `{"cause": text}` |
| `evaluator.schema.json` | The two calls: `PlanInput` and `PlanOutput` for `plan(corpus, request)`, `DecideInput` and `DecideOutput` for `decide(corpus, request, sotw)` |
| `normaliser.schema.json` | `NormaliseOutput`, the result of `normalise`: `{"corpus", "lineage"}`, whose warnings are the corpus's `diagnostic` tuples, or a `Rejection`, `{"diagnostics"}`, of which at least one is an `error` |

**Generated, never edited.** `tools/gen_schema.py` reads the relation blocks of `due2-workflows.md` §3.1 to §3.6 and `due2-diagnostics.md` and writes the three files. `due2-workflows.md` §3.3 has two blocks, the SOTW's and `Reads`'s, and the script tells them apart by their first relation. To change the schema, edit the spec and run `uv run python tools/gen_schema.py`. `tests/test_schema.py` fails when a committed file differs from what the script generates, and when any file is not valid JSON Schema. The schema decides nothing the spec does not, except the lexical patterns that make its types checkable: an IRI, a language tag, an `xsd:dateTime` with a timezone.

**Identifiers.** Each file's `$id` is under `https://w3id.org/due2/schema/1/`, and `evaluator.schema.json` and `normaliser.schema.json` refer to `collections.schema.json` by that name. A validator should not fetch them: register the files locally, as `tools/harness/vectors.py` does.

**Version.** Each file states the schema's version as `x-version`, `MAJOR.MINOR`, and its `$id` carries `MAJOR`, so two schemas that disagree on what is valid never share an `$id`. `VERSION` in `tools/gen_schema.py` sets it. A change bumps `MINOR` when every document valid under the previous version stays valid, such as a new optional field, a new keyed relation, or a new `Enum` value or diagnostic code, and `MAJOR` otherwise, such as a removed field, a new required one, a new singleton relation, or a narrower type. Every object here is closed, so a reader validating against an older `MINOR` rejects a document that uses an addition: upgrade the reader of a port before its writer. A collection does not state the version, because its bytes are its id; the adapter does, in its REST path or its MCP tool definitions (`due2-platform.md` §2.10). The tests compare the files with the generator's output, not with the previous version, so the bump is the author's call.

## How a collection is described

- **Collection.** An object with one optional property per relation. Any other property is invalid. The singletons `request`, `sotw`, and `lineage` are required in their collections. `PlanOutput` is a `Reads`, which may be empty. `DecideOutput` is a `Trace` that must contain `verdict`.
- **Relation.** An array of tuples with at least one item, because an empty relation is omitted, and with no item repeated. A relation with an empty key, such as `verdict`, holds exactly one tuple when it is present.
- **Tuple.** An object with one property per field. A field marked `?` in `due2-workflows.md` §3 is optional; every other field is required. Any other property is invalid.
- **`x-key`.** Each relation carries its key fields as the annotation `x-key`. JSON Schema cannot state that no two tuples share a key, so validators ignore `x-key`, and the harness checks it (`check_collection` in `tools/harness/vectors.py`).

| Value type (`due2-workflows.md` §2) | JSON Schema |
|---|---|
| `Id` | A string with `"format": "iri"` and a pattern for an IRI: a scheme, a colon, and no spaces. A prefixed name such as `ex:a1` matches too, so the schema cannot tell one from an IRI; a collection holds none, because the harness expands them first |
| `Term` | An `Id`, or a literal: `{"v": lexical, "t": datatype}` plus `"l": language` |
| `Instant` | A literal whose `t` is `xsd:dateTime` and whose `v` has a timezone (`decisions/0024`) |
| `Truth` | One of `T`, `F`, `U` |
| `Enum` | The field's values, from its row in `due2-workflows.md` §3 or the section it cites |
| `Flag` | A boolean |
| `Count` | An integer within ±2^53 |
| `Digest` | `sha256:` and 64 lowercase hex digits |
| `String` | A string |

The relation blocks do not list an `Enum` field's values, so `tools/gen_schema.py` lists them, and fails if a value appears nowhere in the spec. The corpus relation `diagnostic`'s `code` takes the warning codes of `due2-diagnostics.md` §3, because an error leaves no corpus; the port shape `Diagnostic`'s `code` takes every code of that registry. A constraint's `source` takes `request`, `state`, `context`, or `witness`, and its `cardinality` `one` or `set`. The `scope` of `atom_constraint` and `duty_constraint` takes `rule`, `action`, `relation`, or `party:` followed by the party function's full IRI, which the spec writes `party:<function>`.

The check on `Enum` values catches a misspelt or dropped value, not a value listed under the wrong field.

## What the schema leaves to other checks

- **Canonical bytes.** Tuple order, the JCS serialisation, and the collection id (`decisions/0007`) are not checked here. The caller canonicalises before it hashes.
- **Corpus invariants.** The structure that W1 guarantees and `due2-workflows.md` §3.1 states, such as every `Permit` and `Forbid` atom being a root, is checked by `check_invariants` in `tools/harness/vectors.py`.
- **Collection ids.** A `Digest` is checked for its form only. Whether it is the digest of the collection it names is the harness's check (`conformance/README.md`, Ids the vector file does not state).
