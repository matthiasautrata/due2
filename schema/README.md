# The port schema

These files state, in JSON Schema 2020-12, what the evaluator port of `due2-platform.md` §2.1 takes and returns: the five collections of `due2-workflows.md` §3.1 to §3.5, encoded as `due2-workflows.md` §2 states. They also define the sixth collection, the lineage that W1 emits beside each corpus (`due2-workflows.md` §3.6), which the evaluator never reads. Read them if you write an evaluator, a normaliser, an adapter (REST or MCP, `due2-platform.md` §2.1), or a relation-level vector file (`conformance/README.md`).

| File | Defines |
|---|---|
| `collections.schema.json` | One definition per collection (`Corpus`, `Request`, `Sotw`, `Trace`, `Lineage`), one per value type of `due2-workflows.md` §2, and `Literal`, the object form a `Term` or `Instant` takes |
| `evaluator.schema.json` | The two calls: `PlanInput` and `PlanOutput` for `plan(corpus, request)`, `DecideInput` and `DecideOutput` for `decide(corpus, request, sotw)` |

**Generated, never edited.** `tools/gen_schema.py` reads the relation blocks of `due2-workflows.md` §3.1 to §3.6 and writes both files. To change the schema, edit the spec and run `uv run python tools/gen_schema.py`. `tests/test_schema.py` fails when a committed file differs from what the script generates, and when either file is not valid JSON Schema. The schema decides nothing the spec does not, except the lexical patterns that make its types checkable: an IRI, a language tag, an `xsd:dateTime` with a timezone.

**Identifiers.** Each file's `$id` is under `https://w3id.org/due2/schema/`, and `evaluator.schema.json` refers to `collections.schema.json` by that name. A validator should not fetch them: register both files locally, as `tools/harness/vectors.py` does.

## How a collection is described

- **Collection.** An object with one optional property per relation. Any other property is invalid. The singletons `request`, `sotw`, and `lineage` are required in their collections. `DecideOutput` is a `Trace` that must contain `verdict`.
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

The relation blocks do not list an `Enum` field's values, so `tools/gen_schema.py` lists them, and fails if a value appears nowhere in the spec. `diagnostic.code` takes the warning codes of `due2-diagnostics.md` §3. The `scope` of `atom_constraint` and `duty_constraint` takes `rule`, `action`, `relation`, or `party:` followed by the party function's full IRI, which the spec writes `party:<function>`.

The check on `Enum` values catches a misspelt or dropped value, not a value listed under the wrong field.

## What the schema leaves to other checks

- **Canonical bytes.** Tuple order, the JCS serialisation, and the collection id (`decisions/0007`) are not checked here. The caller canonicalises before it hashes.
- **Corpus invariants.** The structure that W1 guarantees and `due2-workflows.md` §3.1 states, such as every `Permit` and `Forbid` atom being a root, is checked by `check_invariants` in `tools/harness/vectors.py`.
- **`PlanOutput`.** Its form, `Reads`, is open (#106), so its definition is a description only.
- **Collection ids.** A `Digest` is checked for its form only. Whether it is the digest of the collection it names is the harness's check (`conformance/README.md`, Ids the vector file does not state).
- **Operand bindings.** No relation carries them yet, so no collection can describe a constraint that needs one (#108).
