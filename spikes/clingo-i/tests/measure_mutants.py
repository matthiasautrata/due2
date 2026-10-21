"""Generator strength: the draw at which generation alone first exposes each mutant.

The mutation tests in test_brute_force.py run the explicit examples before generated draws, so
they show that the differentials can see each mutant, not that the generators find it. This
script runs each mutant against generated draws only (`first_kill`), once per seed from 0 to
SEEDS - 1, and prints the draw that first exposes it under each seed, or `-` when none of
LIMIT draws does. One seed's number is a single draw from a geometric distribution, so it
varies several-fold between seeds; the columns show by how much.
`test_generation_alone_exposes_mutant` asserts, for seed 0, that some draw exposes each
mutant outside its blind spots.

With `--shrink NAME`, it prints the shrunk failing case for a rule mutant instead: the case,
the vector, the mutant's reply, and the oracle's. That search is derandomized and shrinks, so
its failing draws are not those of the table.

Run from spikes/clingo-i:

    uv run python -m tests.measure_mutants [SEEDS [LIMIT]]
    uv run python -m tests.measure_mutants --shrink NAME
"""

from __future__ import annotations

import contextlib
import json
import sys

from hypothesis import given, settings

from tests.test_brute_force import (
    DUTY_MUTANTS,
    MUTANTS,
    STRENGTH_LIMIT,
    Case,
    cases,
    check,
    first_kill,
    mutated,
    oracle,
    render,
)


def table(seeds: int, limit: int) -> None:
    """Prints each mutant's first exposing draw under each seed, rule mutants first."""
    for name in [*sorted(MUTANTS), *sorted(DUTY_MUTANTS)]:
        ns = [first_kill(name, limit, at) for at in range(seeds)]
        print(f"{name:34}", *(f"{'-' if n is None else n:>5}" for n in ns), flush=True)


def shrink(name: str) -> None:
    """Prints the shrunk failing case of rule mutant `name`, its reply, and the oracle's.

    The cases are rule cases, so a duty mutant, whose differential draws duty cases, is refused.
    """
    if name not in MUTANTS:
        sys.exit(f"{name}: not a rule mutant (MUTANTS in tests/test_brute_force.py)")
    interp = mutated(name)
    failing: list[Case] = []

    # The last failure Hypothesis reports is the shrunk one. Derandomized, not seed 0: from
    # seed 0, shrinking `opaque-leaf-as-f` stops at four rules; derandomized, it reaches one.
    @settings(max_examples=STRENGTH_LIMIT, deadline=None, database=None, derandomize=True)
    @given(cases(dead=True))
    def run(case: Case) -> None:
        try:
            check(interp, case)
        except AssertionError:
            failing.append(case)
            raise

    with contextlib.suppress(AssertionError):
        run()
    if not failing:
        sys.exit(f"{name}: no failing case in {STRENGTH_LIMIT} draws")
    case = failing[-1]
    print(case)
    print(json.dumps(render(case), indent=1))
    print("--- mutant")
    print(json.dumps(interp.reply(render(case)), indent=1))
    print("--- oracle")
    print(json.dumps(oracle(case), indent=1))


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--shrink"]:
        if len(args) != 2:
            sys.exit("usage: python -m tests.measure_mutants --shrink NAME")
        shrink(args[1])
    else:
        table(int(args[0]) if args else 1, int(args[1]) if args[1:] else STRENGTH_LIMIT)
