"""The interpret task: four solves, the declines, and the reply.

`Interpreter.reply` takes one vector (`conformance/README.md`) and returns the reply of
`spikes/README.md` § `interpret`: an output, a decline, or an error. The driver flattens the
vector to facts (`clingo_i.flatten`, `clingo_i.values`), and the program in `lp/` decides
everything else, in four solves (DESIGN.md § Data flow):

0. for each policy text alone, with its own profiles and the inputs, the bindings and
   conflict strategies (`bind.lp`), and that text's declines and rejections;
1. over the corpus of several texts, the declines and rejections, over `lift.lp` to
   `duty.lp` but `bind.lp`; for one text, solve 0's model stands in for it (`_corpus`);
2. every completion of the unknown variables, cautious: the verdict, the basis, the
   eliminations, the listed frontier, the obligations, and the unknown parts;
3. for an `Indeterminate` only, every completion and one flipped variable, brave: the
   `unknown` atoms and the range.

A definite verdict is one that holds in every completion, so the reply is exact.
"""

from __future__ import annotations

import hashlib
import sys
from collections.abc import Iterable
from pathlib import Path

from clingo import Control, Function, MessageCode, Model, Number, String, Symbol, SymbolType

from clingo_i import flatten, values
from clingo_i.json_types import Json, Obj, as_list, as_obj, as_str

LP = Path(__file__).resolve().parents[1] / "lp"
# The program, in load order. Each file's header names the files whose relations it reads.
PROGRAM_FILES = (
    "lift.lp",
    "structure.lp",
    "kleene.lp",
    "constraint.lp",
    "bind.lp",
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
SOLVE_0 = PROGRAM_FILES[:9]  # lift.lp to duty.lp with bind.lp: no choice, so one model
# The solves over the corpus read bind.lp's relations as facts (`INTERFACE`).
CORPUS = tuple(f for f in PROGRAM_FILES if f != "bind.lp")
SOLVE_1 = CORPUS[:8]  # lift.lp to duty.lp: no choice, so one model
SOLVE_2 = CORPUS[:-1]  # all but pivot.lp
# What bind.lp decides for one text and the later files read, each keyed by an operand
# `o(Iri, Text)`. `conflict/2`, keyed by a policy, is copied apart (`_combine`).
INTERFACE = (
    ("left", 2), ("src", 2), ("prop", 2), ("card", 2), ("has_range", 1), ("range_kind", 2),
    ("allowed", 2), ("owned", 3), ("scheme", 2),
)  # fmt: skip
RAISED = (("reject", 2), ("unsupported", 1))
# What solve 0 tells the corpus of its text: the policy it states, which `_combine` copies,
# and the nodes it reaches, by which `_corpus` keeps the text's triples.
HANDOVER = (("policy_text", 2), ("reached", 1))
# Read after the rejections, in order.
DECLINES = ("unsupported_input", "unsupported_value")
# What the driver reads of solves 0 and 1.
STRUCTURE = (*INTERFACE, ("conflict", 2), *RAISED, *((d, 1) for d in DECLINES), *HANDOVER)
CHAIN = ("Deny", "NotApplicable", "Pending", "Permit")  # due2-workflows.md §6.4
VARIABLE_CAP = 64  # correctness-strategy.md §3, set by measurement (journal, #48)
ODRL_TARGET = "http://www.w3.org/ns/odrl/2/target"


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

    explain.lp lists candidate entries, an atom in one of its policies. Entries whose
    outstanding duties have one set of IRIs are one alternative (due2-workflows.md §6.3), so
    the sets are collapsed here.
    """
    duties: dict[tuple[str, str], set[str]] = {
        (str(s.arguments[0]), str(s.arguments[1])): set()
        for s in shown
        if s.match("listed_front", 2)
    }
    for s in shown:
        if s.match("front_duty", 3):
            entry = (str(s.arguments[0]), str(s.arguments[1]))
            duties[entry].add(_rule(s.arguments[2]))
    routes = sorted({tuple(sorted(d)) for d in duties.values()}, key=lambda a: (len(a), a))
    return [list(a) for a in routes]


def _combine(bound: dict[str, list[Symbol]]) -> list[Symbol]:
    """bind.lp's relations of each text (`bound`, solve 0's model by text id), as corpus facts.

    A leaf that several texts state keeps the operand of the first text in sorted text id, and
    each later text's must bind alike: the same `INTERFACE` relations with the operand left
    out. A policy that several texts state must get one strategy. Either difference is
    `reject("IdentityConflict", C)`, since the texts describe one node differently
    (due2-diagnostics.md). Every text's `RAISED` atoms are kept, so solve 1 raises them in its
    order; its other declines (`DECLINES`) solve 1 derives again, over the corpus. Every
    text's `policy_text/2` is kept too, so that a policy's text is the one whose solve 0
    derives it.
    """
    out: list[Symbol] = []
    keep: dict[Symbol, Symbol] = {}  # leaf to its operand
    seen: dict[Symbol, frozenset[tuple[str, str]]] = {}  # leaf or policy to its signature
    for atoms in bound.values():
        rows = [a for a in atoms if any(a.match(n, k) for n, k in INTERFACE)]
        out += [a for a in atoms if any(a.match(n, k) for n, k in RAISED)]
        out += [a for a in atoms if a.match("policy_text", 2)]
        named = [(a.arguments[0], a.arguments[1]) for a in rows if a.match("left", 2)]
        for leaf, op in named:
            sig = _signature(rows, op)
            if leaf not in keep:
                keep[leaf], seen[leaf] = op, sig
            elif seen[leaf] != sig:
                out.append(_identity_conflict(leaf))
        strategies: dict[Symbol, set[str]] = {}
        for a in atoms:
            if a.match("conflict", 2):
                strategies.setdefault(a.arguments[0], set()).add(str(a.arguments[1]))
        for policy, strats in strategies.items():
            sig = frozenset(("conflict", s) for s in strats)
            if seen.setdefault(policy, sig) != sig:
                out.append(_identity_conflict(policy))
            out += [Function("conflict", [policy, Function(s)]) for s in strats]
        kept = {op for leaf, op in named if keep[leaf] == op}
        out += [a for a in rows if a.arguments[0] in kept and not a.match("left", 2)]
    out += [Function("left", [leaf, op]) for leaf, op in keep.items()]
    return sorted(set(out))


def _signature(rows: Iterable[Symbol], op: Symbol) -> frozenset[tuple[str, str]]:
    """What `rows` say of the operand `op`, with `op` left out, so two texts' rows compare."""
    return frozenset(
        (a.name, ", ".join(map(str, a.arguments[1:])))
        for a in rows
        if a.arguments[0] == op and not a.match("left", 2)
    )


def _identity_conflict(node: Symbol) -> Symbol:
    """`reject("IdentityConflict", Node)`."""
    return Function("reject", [String("IdentityConflict"), node])


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
            vector: A corpus vector: `prefixes`, `policies` (Turtle texts), `request`, and `sotw`.

        Returns:
            `verdict`, `frontier`, `obligations`, `exact`, `verdict_basis`, `eliminated`,
            `unknown_parts`, and, for an `Indeterminate`, `verdict_range`. Refs are source rule
            IRIs.

        Raises:
            Declined: The vector uses something the spike does not read.
            ValueError: The vector is malformed, or the policy is not admissible, which includes
                naming a profile with no module (`UnrecognisedProfile`).
            RuntimeError: The program has no model, so it is wrong.
        """
        text, atoms = self._corpus(vector)
        self._structure(atoms)
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
            pivots = self._solve(text, CORPUS, "brave")
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
                    # An `elim` row names the removed entry's policy. The reply drops it: the
                    # corpus compares (source, by source, rule) triples (DESIGN.md § Output).
                    (_rule(s.arguments[0]), _rule(s.arguments[2]), _text(s.arguments[3]))
                    for s in shown
                    if s.match("elim", 4)
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
        """The vector as the input facts of the solves over the corpus, one per line.

        Raises:
            ValueError: The vector is malformed, or names a profile with no module, which is
                not admissible (`UnrecognisedProfile`).
        """
        return self._corpus(vector)[0]

    def _corpus(self, vector: Obj) -> tuple[str, list[Symbol]]:
        """The facts of the solves over the corpus, and the model whose declines and
        rejections the driver raises (`_structure`).

        Each policy text is solved alone, in its own layers and with the inputs (solve 0): W1
        normalises each policy by itself (due2-workflows.md §4, *Several policies are one
        corpus*), so one policy's profile does not reach another's operands or conflict
        strategy. The inputs are there because a policy is its own data space with the world
        (decisions/0050 #1): its declines and rejections are those it raises alone, and some,
        such as a duty's deadline that is not comparable, read the SOTW. Without the inputs,
        every text's solve 0 declined such a duty when there were several texts
        (`test_another_text_leaves_the_deadline_comparable`). The corpus facts are the union of the
        texts' facts, with every profile's layers, the inputs, and bind.lp's relations
        (`INTERFACE`) and rejections copied in. A named leaf or policy that two texts state
        must get the same binding, or strategy, from each: otherwise it is an
        `IdentityConflict` (due2-diagnostics.md).

        What one text says must not change another's policy, as it cannot in W1, so the
        corpus keeps each text's facts apart in two ways. A text's `triple/3` about an IRI is
        kept only if the text reaches the IRI in its solve 0 (`reached/1`): a text that never
        links to a node says nothing of it. A triple with a blank subject is always kept,
        since blank nodes are scoped by their text. `text_triple/4` is kept whole, since each
        policy reads only its own text's (`edge/4`). And each text's layers are its own
        (`text_layer/2`, `text_profile/2`), read only on the nodes the text describes
        (`described/2`): the union of those it reaches and the subjects of its kept triples.
        So a text's profiles and triples bear only on its own policies' nodes (the L11
        variants of `test_locality.py`, and `test_another_text_changes_no_structure` in
        `test_interpret.py`).

        With one text, that text is the corpus, so solve 1 is not run, and solve 0's model is
        returned. Solve 1 would load the same files but `bind.lp`,
        over the same triples, inputs, and layers, with bind.lp's relations given as facts
        that solve 0 derived from those same inputs, so its model would hold the same atoms of
        `STRUCTURE`. Identical texts share a hash, so they count as one text here.

        Raises:
            ValueError: The vector is malformed, or names a profile with no module, which is
                not admissible (`UnrecognisedProfile`).
        """
        prefixes = {k: as_str(v, k) for k, v in as_obj(vector["prefixes"], "prefixes").items()}
        texts = [as_str(t, "policies") for t in as_list(vector["policies"], "policies")]
        # A text is named by its hash, which scopes its blank nodes and its operands.
        named = {hashlib.sha256(t.encode()).hexdigest()[:12]: t for t in texts}
        inputs = flatten.input_facts(vector, prefixes)
        graphs = {tid: flatten.parse(named[tid]) for tid in sorted(named)}
        triples = {tid: flatten.policy_facts(g, tid) for tid, g in graphs.items()}
        profiles = {tid: flatten.profiles(g) for tid, g in graphs.items()}
        bound: dict[str, list[Symbol]] = {}
        for tid in graphs:
            facts = [Function("policy_texts", [Number(1)]), Function("text_id", [String(tid)])]
            facts += triples[tid] + inputs + self._layers(profiles[tid])
            facts += self._text_layers(tid, profiles[tid])
            bound[tid] = self._model(self._render(facts), SOLVE_0)
        reached = {
            tid: {a.arguments[0] for a in atoms if a.match("reached", 1)}
            for tid, atoms in bound.items()
        }
        facts = [Function("policy_texts", [Number(len(named))])]
        for tid in graphs:
            facts += self._text_layers(tid, profiles[tid])
            described = set(reached[tid])
            for f in triples[tid]:
                if f.match("triple", 3):
                    s = f.arguments[0]
                    if s.match("b", 2) or s in reached[tid]:
                        facts.append(f)
                        described.add(s)
                else:
                    facts.append(f)
            facts += [Function("described", [String(tid), n]) for n in sorted(described)]
        facts += inputs + self._layers(sorted({i for p in profiles.values() for i in p}))
        facts += _combine(bound)
        rendered = self._render(facts)
        if len(bound) == 1:
            return rendered, next(iter(bound.values()))
        return rendered, self._model(rendered, SOLVE_1)

    def _layers(self, profiles: list[str]) -> list[Symbol]:
        """The modules of the core and of the selected `profiles`, each file with its layer.

        Raises:
            ValueError: A profile has no module, which is not admissible (`UnrecognisedProfile`).
        """
        # A path's layers: `core`, or `module(Iri)` for each profile whose module it is part
        # of (decisions/0014 #3). A file in both the core and a profile is core.
        layers: dict[str, set[Symbol]] = {path: {Function("core")} for path in self._core}
        facts: list[Symbol] = []
        for iri in profiles:
            if iri not in self._profiles:
                # IM 2.2 §3.2: a processor that does not recognise a profile stops.
                raise ValueError(f"not admissible: UnrecognisedProfile at {iri}")
            for path in self._profiles[iri]:
                if path not in self._core:
                    layers.setdefault(path, set()).add(Function("module", [String(iri)]))
            facts.append(Function("selected_profile", [String(iri)]))
        for path in sorted(layers):
            facts.extend(self._modules[path])
            facts += [Function("layer", [String(path), lay]) for lay in sorted(layers[path])]
        return facts

    def _text_layers(self, tid: str, profiles: list[str]) -> list[Symbol]:
        """The layers of text `tid`, which selects `profiles`: `text_layer/2` for each core
        file and each file of its profiles, and `text_profile/2` for each profile.

        Call it after `_layers` on the same profiles, which rejects one with no module.
        """
        paths = set(self._core).union(*(self._profiles[iri] for iri in profiles))
        facts = [Function("text_layer", [String(tid), String(p)]) for p in sorted(paths)]
        return facts + [Function("text_profile", [String(tid), String(i)]) for i in profiles]

    def _render(self, facts: list[Symbol]) -> str:
        """`facts` and their value table as program text (flatten.py, values.py)."""
        return flatten.render(facts + values.value_facts(values.literals(facts)))

    def _program(self, files: tuple[str, ...]) -> str:
        """The text of `files`, joined in the given order."""
        return "\n".join(self._programs[f] for f in files)

    def _model(self, facts: str, files: tuple[str, ...]) -> list[Symbol]:
        """The `STRUCTURE` atoms of the one model of `facts` under `files` (solves 0 and 1).

        These files make no choice and are stratified, so the program has at most one model.

        Raises:
            RuntimeError: No model: a constraint of `files` failed.
        """
        shows = "\n".join(f"#show {n}/{k}." for n, k in STRUCTURE)
        ctl = Control([], logger=_log)
        ctl.add("base", [], "\n".join((facts, self._program(files), shows)))
        ctl.ground([("base", [])])
        atoms: list[Symbol] = []

        def on_model(model: Model) -> None:
            atoms.extend(model.symbols(shown=True))

        if not ctl.solve(on_model=on_model).satisfiable:
            raise RuntimeError("structure program has no model")
        return atoms

    def _structure(self, atoms: list[Symbol]) -> None:
        """Raise on the first decline or rejection of `atoms`, solve 1's model (or solve 0's,
        for one text), in the order of DESIGN.md § Data flow.

        Within each kind the smallest name wins, so the same vector always gives the same
        reason.
        """
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
