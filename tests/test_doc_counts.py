"""The counts that documents copy from the corpus and the scorecard are the real ones.

`conformance/README.md` § Coverage gaps counts the scenarios that assert each explanation
field, and README § Status gives clingo-i's pass count. Both are copied by hand, so a case or
a recorded run that changes them would otherwise leave them stale. Each test finds the
sentence that states a count and compares it with the count read from the files. A sentence
reworded so that its pattern no longer matches fails the test, so the check cannot lapse
silently.
"""

from __future__ import annotations

import json
import re
from typing import cast

from check_odrl22 import ROOT

Obj = dict[str, object]


def scenarios() -> list[Obj]:
    """The `expected` object of every scenario in the corpus; a negative case has none."""
    out: list[Obj] = []
    for path in sorted((ROOT / "conformance/cases").glob("*/case.json")):
        case = cast(Obj, json.loads(path.read_text()))
        out.extend(cast(Obj, s["expected"]) for s in cast(list[Obj], case.get("scenarios") or []))
    return out


def stated(text: str, pattern: str) -> tuple[int, ...]:
    match = re.search(pattern, text)
    assert match, f"no sentence matches {pattern!r}"
    return tuple(int(g) for g in match.groups())


def test_coverage_counts_match_the_corpus() -> None:
    text = (ROOT / "conformance/README.md").read_text()
    expected = scenarios()
    explained = sum(1 for e in expected if "verdict_basis" in e or "eliminated" in e)
    unknown = sum(1 for e in expected if "unknown_parts" in e)
    indeterminate = [e for e in expected if e.get("verdict") == "Indeterminate"]
    ranged = sum(1 for e in indeterminate if "verdict_range" in e)
    assert stated(text, r"\(#57\), asserted by (\d+) scenarios") == (explained,)
    assert stated(text, r"\(#72\), asserted by the (\d+) scenarios") == (unknown,)
    assert stated(text, r"(\d+) of (\d+) scenarios assert `verdict_basis`") == (
        explained,
        len(expected),
    )
    assert stated(text, r"and (\d+) assert `unknown_parts`") == (unknown,)
    assert stated(text, r"(\d+) of the (\d+) `Indeterminate` scenarios") == (
        ranged,
        len(indeterminate),
    )


def test_status_counts_match_the_scorecard() -> None:
    text = (ROOT / "README.md").read_text()
    card = cast(Obj, json.loads((ROOT / "spikes/clingo-i/scorecard.json").read_text()))
    summary = cast(dict[str, int], cast(Obj, cast(Obj, card["tasks"])["interpret"])["summary"])
    assert stated(text, r"It passes (\d+) of the (\d+) scenarios") == (
        summary["pass"],
        summary["vectors"],
    )
    assert summary["vectors"] == len(scenarios())
