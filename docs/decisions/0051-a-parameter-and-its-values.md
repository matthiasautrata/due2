# 0051 — A request or evidence parameter and its values are two relations

**Status:** Decided, 2026-10-29 (#159)
**Context documents:** `due2-workflows.md` §3.2, §3.3 · `due2-profiles.md` §3 · `conformance/README.md` · `schema/` · `decisions/0025` · `decisions/0040` · issue #159

## Question

In `due2-workflows.md` v0.60 a request's parameters were `request_param (name | value: Term)`, and an evidence record's were `evidence_param (evidence_id, name | value: Term)`. The key leaves out `value`, so a parameter had at most one value. A binding may declare `due2:cardinality due2:set` for any source (`due2-profiles.md` §3), and a set-valued operand is compared with the set operators (`decisions/0025`). The vector format already gives such an operand a JSON list. Four scenarios pass two values for one request parameter: two in `oval-list-right-operand` and two in `due2-list-part-and-class`. They pass only because clingo-i reads `case.json` directly. The port schema, generated from the spec, would refuse them as two tuples with one key (#159).

How should the port carry a parameter with several values, or with none?

## Decision

1. **A parameter and its values are two relations**, as a state answer is `fact` and `fact_value` (`decisions/0040`), and a constraint is `constraint` and `constraint_value` (`due2-workflows.md` §3.1):

   ```text
   request_param         (name)
   request_param_value   (name, value: Term)
   evidence_param        (evidence_id, name)
   evidence_param_value  (evidence_id, name, value: Term)
   ```

2. **A parameter with no values is the empty set** for an operand whose cardinality is `set`, so `resolved`. For a `one` operand it is `missing`. A property with no parameter row is `missing` for either (`due2-profiles.md` §3, *Resolution*).
3. **A parameter has no status.** A request is what its caller states, and an evidence record is what its submitter states, so no source can fail to answer and nothing is `unresolved`. `missing` is a parameter that is not stated. `invalid` and `conflict` follow from the values and the binding, as the resolution table already says.

## Why this holds

- **Keying the value alone cannot state the empty set.** With `request_param (name, value: Term)`, a set-valued parameter with no members has no row, so it reads as absent, so `missing`, so `U`. A request to distribute no data packages, against `isPartOf` the packages a permission allows, would then never be `T`, though an empty left set is part of any set (`due2-profiles.md` §4) and the caller has said exactly what it proposes. The parameter row says the parameter was stated, as a `resolved` `fact` with no `fact_value` does for a state property (`due2-workflows.md` §3.3, *Several sources*).
- **The port keeps what the vector format can say.** A vector's `[]` is the empty set, and clingo-i reads it so for the request. With the parameter row, every vector maps to port tuples, and nothing a vector states is lost on the way to an evaluator.
- **A status would describe nothing.** `fact` carries a status because a source may answer `missing`, `invalid`, `conflict`, or `unresolved` for a property it was asked about. Nobody is asked for a request parameter: the caller states it or does not.

## Rejected

- **Key `request_param` by `(name, value)` and add nothing else.** It carries several values with the smallest change, but it cannot state the empty set, as above.
- **A status on the parameter, as on `fact`.** Its only use would be `unresolved`, and a request has no source that could fail to answer.

## Consequences

- `due2-workflows.md` v0.61 §3.2–§3.3 and `due2-profiles.md` v0.30 §3 state the relations, and `schema/` is generated from them.
- `conformance/README.md` maps a vector's `params` to the relations: one parameter row per property, one value row per value.
- clingo-i reads a list in an evidence record's `params` as it reads one in the request's, `[]` included (`evidence_param_set/2`).
