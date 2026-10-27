"""The oracle CLI (tools/oracle.py) asks clingo-i the question the harness asks.

The CLI reads a scenario two ways: from a case directory, as the harness does, or from policy
files and a scenario object, as a caller outside the corpus does. These tests build the
`interpret` input both ways and need no backend.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from harness.corpus import CASES
from harness.json_types import as_list, as_obj, loads
from oracle import case_inputs, file_inputs

CASE = CASES / "dprod-audit-logs"


def test_a_scenario_file_gives_the_case_input(tmp_path: Path) -> None:
    """Risk: the file route builds a different input, so the oracle answers another question.

    Without it, a file route that dropped `STANDARD_PREFIXES` or read the policies differently
    would give an error or another verdict for a scenario the corpus pins.
    """
    case = as_obj(loads((CASE / "case.json").read_text()), "case")
    for (name, expected), raw in zip(
        case_inputs(CASE, []), as_list(case["scenarios"], "scenarios"), strict=True
    ):
        s = as_obj(raw, name)
        f = tmp_path / "scenario.json"
        f.write_text(
            json.dumps(
                {**{k: s[k] for k in ("name", "request", "sotw")}, "prefixes": case["prefixes"]}
            )
        )
        [(got_name, got)] = file_inputs([CASE / "policy.ttl"], [str(f)])
        assert got_name == name
        assert {**got, "case": expected["case"]} == expected


def test_a_scenario_without_a_sotw_is_rejected(tmp_path: Path) -> None:
    """Risk: a malformed scenario reaches the oracle, whose error reads as the policy's fault.

    Without it, a missing `sotw` would reach clingo-i, and its error reply would be counted as
    a difference with the other evaluator rather than as a fault in the translation.
    """
    f = tmp_path / "scenario.json"
    f.write_text(json.dumps({"request": {}}))
    with pytest.raises(ValueError, match="no 'sotw'"):
        list(file_inputs([CASE / "policy.ttl"], [str(f)]))
