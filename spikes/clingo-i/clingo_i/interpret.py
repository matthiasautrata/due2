"""The interpret task: three solves, the declines, and the reply.

`Interpreter.reply` takes one vector (`conformance/README.md`) and returns the reply of
`spikes/README.md` § `interpret`: an output, a decline, or an error. The driver flattens the
vector to facts (`clingo_i.flatten`, `clingo_i.values`), and the program in `lp/` decides
everything else, in three solves (DESIGN.md § Data flow):

1. the declines and rejections, over `lift.lp` to `duty.lp`;
2. every completion of the unknown variables, cautious: the verdict, the basis, the
   eliminations, the listed frontier, the obligations, and the unknown parts;
3. for an `Indeterminate` only, every completion and one flipped variable, brave: the
   `unknown` atoms and the range.

A definite verdict is one that holds in every completion, so the reply is exact.
"""

from __future__ import annotations

import sys
from pathlib import Path

from clingo import Control, Function, MessageCode, Model, String, Symbol, SymbolType

from clingo_i import flatten, values
from clingo_i.json_types import Json, Obj, as_list, as_obj, as_str

LP = Path(__file__).resolve().parents[1] / "lp"
# The program, in load order. Each file's header names the files whose relations it reads.
PROGRAM_FILES = (
    "lift.lp",
    "structure.lp",
    "kleene.lp",
    "constraint.lp",
    "operand.lp",
    "compare.lp",
    "applies.lp",
    "duty.lp",
    "completion.lp",
    "resolve.lp",
    "integrity.lp",
    "explain.lp",
    "pivot.lp",
)
SOLVE_1 = PROGRAM_FILES[:8]  # lift.lp to duty.lp: no choice, so one model
SOLVE_2 = PROGRAM_FILES[:-1]  # all but pivot.lp
CHAIN = ("Deny", "NotApplicable", "Pending", "Permit")  # due2-workflows.md §6.4
VARIABLE_CAP = 64  # correctness-strategy.md §3, set by measurement (journal, #48)
ODRL_TARGET = "http://www.w3.org/ns/odrl/2/target"
# Read after the rejections, in order.
DECLINES = ("unsupported_input", "unsupported_value")


def load_programs() -> dict[str, str]:
    """The text of each program file, keyed by file name."""
    return {f: (LP / f).read_text() for f in PROGRAM_FILES}


class Declined(Exception):
    """A reply kind, not an error: the vector uses something the spike does not read.

    Attributes:
        feature: The decline reason the reply names, such as `odrl:duty` or
            `variable-cap` (DESIGN.md § Declines).
    """

    def __init__(self, feature: str) -> None:
        super().__init__(feature)
        self.feature = feature


def _log(code: MessageCode, message: str) -> None:
    """clingo's logger: every message but an undefined atom goes to stderr."""
    # An undefined atom is a relation with no facts in this vector (request_absent, say).
    if code != MessageCode.AtomUndefined:
        print(message, file=sys.stderr)


def _text(sym: Symbol) -> str:
    """A symbol as reply text: a string's contents unquoted, anything else as clingo prints it."""
    return sym.string if sym.type == SymbolType.String else str(sym)


def _input(sym: Symbol) -> str:
    """An `unknown_part` input as the IRI it reads: `odrl:target`, a party function, or a property."""
    return ODRL_TARGET if sym.match("target", 0) else _text(sym.arguments[0])


def _rule(atom: Symbol) -> str:
    """An atom id `a(R, A, T, Party)` as its source rule `R`, or its source duty for a duty atom.

    See due2-workflows.md §3.7.
    """
    return _text(atom.arguments[0])


def _frontier(shown: list[Symbol]) -> list[Json]:
    """The listed frontier: one sorted list of duty IRIs per alternative, sorted.

    Candidates whose outstanding duties have one set of IRIs are one alternative
    (due2-workflows.md §6.3), so the sets are collapsed here.
    """
    duties: dict[str, set[str]] = {
        str(s.arguments[0]): set() for s in shown if s.match("listed_front", 1)
    }
    for s in shown:
        if s.match("front_duty", 2):
            duties[str(s.arguments[0])].add(_rule(s.arguments[1]))
    routes = sorted({tuple(sorted(d)) for d in duties.values()}, key=lambda a: (len(a), a))
    return [list(a) for a in routes]


class Interpreter:
    """One harness session: the modules, parsed once, and the program.

    Args:
        init: The harness's `init` message body (`spikes/README.md` § Protocol): `modules`
            maps each module path to its Turtle, `core` lists the paths every vector loads, and
            `profiles` maps each profile IRI to the paths it adds.
        programs: The program text by file name, in place of `lp/`. The integrity tests pass a
            program with one rule deleted.
    """

    def __init__(self, init: Obj, programs: dict[str, str] | None = None) -> None:
        modules = as_obj(init["modules"], "init.modules")
        self._modules = {p: flatten.module_facts(p, as_str(t, p)) for p, t in modules.items()}
        self._core = [as_str(p, "init.core") for p in as_list(init["core"], "init.core")]
        self._profiles = {
            iri: [as_str(p, iri) for p in as_list(paths, iri)]
            for iri, paths in as_obj(init["profiles"], "init.profiles").items()
        }
        self._programs = programs if programs is not None else load_programs()

    def reply(self, vector: Obj) -> Obj:
        """The reply to one vector: `{"output": …}`, `{"unsupported": …}`, or `{"error": …}`.

        Any exception is an error reply, so a defect never becomes a verdict.
        """
        try:
            return {"output": self.interpret(vector)}
        except Declined as d:
            return {"unsupported": d.feature}
        except Exception as e:  # noqa: BLE001 -- every failure is an error reply, never a verdict
            return {"error": f"{type(e).__name__}: {e}"}

    def interpret(self, vector: Obj) -> Obj:
        """The output for one vector (DESIGN.md § Output).

        Args:
            vector: A corpus vector: `prefixes`, `policy` (Turtle), `request`, `sotw`, and
                `config`.

        Returns:
            `verdict`, `frontier`, `obligations`, `exact`, `verdict_basis`, `eliminated`,
            `unknown_parts`, and, for an `Indeterminate`, `verdict_range`. Refs are source rule
            IRIs.

        Raises:
            Declined: The vector uses something the spike does not read.
            ValueError: The vector is malformed, names an unknown profile, or the policy is
                not admissible.
            RuntimeError: The program has no model, so it is wrong.
        """
        text = self.facts(vector)
        self._structure(text)
        shown = self._solve(text, SOLVE_2, "cautious")
        verdicts = [_text(s.arguments[1]) for s in shown if s.match("verdict", 2)]
        verdict = verdicts[0] if len(verdicts) == 1 else "Indeterminate"
        basis = {
            (_rule(s.arguments[1]), _text(s.arguments[2])) for s in shown if s.match("basis", 3)
        }
        rows = {
            (_rule(s.arguments[0]), _text(s.arguments[1]))
            for s in shown
            if s.match("obligation_row", 2)
        }
        out: Obj = {
            "verdict": verdict,
            "frontier": _frontier(shown) if verdict == "Pending" else [],
            "obligations": [{"duty": d, "status": status} for d, status in sorted(rows)],
            "exact": True,
        }
        reached: set[str] = set()
        if verdict == "Indeterminate":
            pivots = self._solve(text, PROGRAM_FILES, "brave")
            basis = {(_rule(s.arguments[0]), "unknown") for s in pivots if s.match("unknown", 1)}
            reached = {
                _text(s.arguments[1])
                for s in pivots
                if s.match("verdict", 2) and _text(s.arguments[0]) == "c"
            }
        # Every listed obligation, in force t or u, has role `obligation`, under any verdict
        # (DESIGN.md § Output).
        basis |= {(d, "obligation") for d, _ in rows}
        out["verdict_basis"] = [{"ref": r, "role": role} for r, role in sorted(basis)]
        out["eliminated"] = [
            {"ref": ref, "by": by, "rule": rule}
            for ref, by, rule in sorted(
                {
                    (_rule(s.arguments[0]), _rule(s.arguments[1]), _text(s.arguments[2]))
                    for s in shown
                    if s.match("elim", 3)
                }
            )
            if ref != by  # the authored level: "other than itself" (DESIGN.md § Output)
        ]
        out["unknown_parts"] = [
            {"ref": ref, "input": i, "status": status}
            for ref, i, status in sorted(
                {
                    (_rule(s.arguments[0]), _input(s.arguments[1]), _text(s.arguments[2]))
                    for s in shown
                    if s.match("unknown_part", 3)
                }
            )
        ]
        if reached:
            out["verdict_range"] = {
                "low": min(reached, key=CHAIN.index),
                "high": max(reached, key=CHAIN.index),
            }
        return out

    def facts(self, vector: Obj) -> str:
        """The vector as the program's input facts (DESIGN.md § Input facts), one per line.

        Raises:
            ValueError: The vector is malformed or names an unknown profile.
        """
        prefixes = {k: as_str(v, k) for k, v in as_obj(vector["prefixes"], "prefixes").items()}
        graph = flatten.parse(as_str(vector["policy"], "policy"))

        facts = flatten.policy_facts(graph) + flatten.input_facts(vector, prefixes)
        # A path's layer: `core`, or `module(Iri)` for the profile whose module it is part of
        # (decisions/0014 #3). A file in both the core and a profile is core.
        layers: dict[str, Symbol] = {path: Function("core") for path in self._core}
        for iri in flatten.profiles(graph):
            if iri not in self._profiles:
                raise ValueError(f"unknown profile {iri}")
            for path in self._profiles[iri]:
                layers.setdefault(path, Function("module", [String(iri)]))
            facts.append(Function("selected_profile", [String(iri)]))
        for path in sorted(layers):
            facts.extend(self._modules[path])
            facts.append(Function("layer", [String(path), layers[path]]))
        return flatten.render(facts + values.value_facts(values.literals(facts)))

    def _program(self, files: tuple[str, ...]) -> str:
        """The text of `files`, joined in the given order."""
        return "\n".join(self._programs[f] for f in files)

    def _structure(self, facts: str) -> None:
        """Solve 1: raise on the first decline or rejection, in the order of DESIGN.md § Data flow.

        The program is stratified, so it has one model. Within each kind the smallest name wins,
        so the same vector always gives the same reason.
        """
        ctl = Control([], logger=_log)
        ctl.add("base", [], facts + "\n" + self._program(SOLVE_1))
        ctl.ground([("base", [])])
        atoms: list[Symbol] = []

        def on_model(model: Model) -> None:
            atoms.extend(model.symbols(atoms=True))

        if not ctl.solve(on_model=on_model).satisfiable:
            raise RuntimeError("structure program has no model")
        unsupported = sorted(_text(a.arguments[0]) for a in atoms if a.match("unsupported", 1))
        if unsupported:
            raise Declined(unsupported[0])
        rejects = sorted(
            f"{_text(a.arguments[0])} at {_text(a.arguments[1])}"
            for a in atoms
            if a.match("reject", 2)
        )
        if rejects:
            raise ValueError("not admissible: " + "; ".join(rejects))
        for name in DECLINES:
            found = sorted(_text(a.arguments[0]) for a in atoms if a.match(name, 1))
            if found:
                raise Declined(found[0])

    def _solve(self, facts: str, files: tuple[str, ...], mode: str) -> list[Symbol]:
        """Solves 2 and 3: the shown atoms true in every model (cautious) or in some (brave).

        clingo reports the consequences of the enumeration so far with each model, so the last
        model's atoms are the final answer. The variables are counted in the first model:
        `var/1` is the same in every model, but grounding keeps `var/1` atoms that no model
        makes true, so counting the ground atoms would overcount (completion.lp).

        Raises:
            Declined: More than `VARIABLE_CAP` completion variables.
            RuntimeError: No model: an integrity constraint failed.
        """
        ctl = Control(["0", f"--enum-mode={mode}"], logger=_log)
        ctl.add("base", [], facts + "\n" + self._program(files))
        ctl.ground([("base", [])])
        last: list[Symbol] = []
        over = False

        def on_model(model: Model) -> bool:
            nonlocal over
            if not last and not over:
                variables = sum(1 for a in model.symbols(shown=True) if a.match("var", 1))
                over = variables > VARIABLE_CAP
            last[:] = model.symbols(shown=True)
            return not over  # False stops the enumeration

        if not ctl.solve(on_model=on_model).satisfiable:
            raise RuntimeError(f"no model satisfies the integrity constraints ({mode})")
        if over:
            raise Declined("variable-cap")
        return last
