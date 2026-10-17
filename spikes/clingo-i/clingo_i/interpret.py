"""The interpret task (DESIGN.md § Data flow): two solves, the declines, and the reply."""

from __future__ import annotations

import sys
from pathlib import Path

from clingo import Control, Function, MessageCode, Model, String, Symbol, SymbolType

from clingo_i import flatten, values
from clingo_i.json_types import Obj, as_list, as_obj, as_str

LP = Path(__file__).resolve().parents[1] / "lp"
PROGRAM_FILES = (
    "lift.lp",
    "structure.lp",
    "kleene.lp",
    "applies.lp",
    "completion.lp",
    "resolve.lp",
)
SOLVE_1 = ("lift.lp", "structure.lp")
VARIABLE_CAP = 16  # correctness-strategy.md §3
DECLINES = ("unsupported_input", "unsupported_value")  # read after the rejections, in order


def load_programs() -> dict[str, str]:
    return {f: (LP / f).read_text() for f in PROGRAM_FILES}


class Declined(Exception):
    """A reply kind, not an error: the vector uses a feature this increment does not read."""

    def __init__(self, feature: str) -> None:
        super().__init__(feature)
        self.feature = feature


def _log(code: MessageCode, message: str) -> None:
    # An undefined atom is a relation with no facts in this vector (request_absent, say).
    if code != MessageCode.AtomUndefined:
        print(message, file=sys.stderr)


def _text(sym: Symbol) -> str:
    return sym.string if sym.type == SymbolType.String else str(sym)


class Interpreter:
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
        try:
            return {"output": self.interpret(vector)}
        except Declined as d:
            return {"unsupported": d.feature}
        except Exception as e:  # noqa: BLE001 -- every failure is an error reply, never a verdict
            return {"error": f"{type(e).__name__}: {e}"}

    def interpret(self, vector: Obj) -> Obj:
        prefixes = {k: as_str(v, k) for k, v in as_obj(vector["prefixes"], "prefixes").items()}
        graph = flatten.parse(as_str(vector["policy"], "policy"))

        facts = flatten.policy_facts(graph) + flatten.input_facts(vector, prefixes)
        paths = set(self._core)
        for iri in flatten.profiles(graph):
            if iri not in self._profiles:
                raise ValueError(f"unknown profile {iri}")
            paths.update(self._profiles[iri])
            facts.append(Function("selected_profile", [String(iri)]))
        for path in sorted(paths):
            facts.extend(self._modules[path])
        text = flatten.render(facts + values.value_facts(values.literals(facts)))

        self._structure(text)
        return {"verdict": self._verdict(text), "frontier": [], "obligations": [], "exact": True}

    def _program(self, files: tuple[str, ...]) -> str:
        return "\n".join(self._programs[f] for f in files)

    def _structure(self, facts: str) -> None:
        """Solve 1 (DESIGN.md § Data flow): the declines and rejections, first hit decides."""
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

    def _verdict(self, facts: str) -> str:
        """Solve 2: the verdict true in every completion, else Indeterminate."""
        ctl = Control(["0", "--enum-mode=cautious"], logger=_log)
        ctl.add("base", [], facts + "\n" + self._program(PROGRAM_FILES))
        ctl.ground([("base", [])])
        variables = sum(1 for _ in ctl.symbolic_atoms.by_signature("var", 1))
        if variables > VARIABLE_CAP:
            raise Declined("variable-cap")
        last: list[Symbol] = []

        def on_model(model: Model) -> None:
            last[:] = model.symbols(shown=True)

        if not ctl.solve(on_model=on_model).satisfiable:
            raise RuntimeError("no completion satisfies the integrity constraints")
        verdicts = [_text(s.arguments[0]) for s in last if s.match("verdict", 1)]
        return verdicts[0] if len(verdicts) == 1 else "Indeterminate"
