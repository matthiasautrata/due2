"""The constraint walk of `tools/check_corpus.py` (due2-profiles.md §5, #126).

`due2-constraint-cycle` pins the rejection of a two-step cycle. These tests pin the shortest
cycle, and the inputs the walk must admit or check without recursion: a named constraint
shared by two logical constraints, which is no cycle, nesting deeper than Python's recursion
limit, and the guard and witness mixing check over a duty's tree, which reads the walk's
order.
"""

from __future__ import annotations

import sys
from pathlib import Path

from check_corpus import check_file

HEAD = """\
@prefix odrl:  <http://www.w3.org/ns/odrl/2/> .
@prefix dprod: <https://ekgf.org/dprod/spec/develop/> .
@prefix due2:  <https://w3id.org/due2/profile#> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .
@prefix ex:    <https://example.org/> .

ex:policy a odrl:Set ;
    odrl:profile <https://ekgf.org/dprod/spec/develop/>, <https://w3id.org/due2/profile#> ;
    odrl:conflict odrl:prohibit ;
    odrl:permission ex:read .

ex:read a odrl:Permission ;
    odrl:action odrl:read ;
    odrl:target ex:Report ;
    {permission}
    odrl:duty ex:attest .

ex:attest a odrl:Duty ;
    odrl:action ex:attest ;
    {duty}
    dprod:deadline "2027-01-01T00:00:00Z"^^xsd:dateTime .

ex:attest a odrl:Action ; odrl:includedIn odrl:use .

ex:inEU a odrl:Constraint ;
    odrl:leftOperand ex:euDomiciled ; odrl:operator odrl:eq ; odrl:rightOperand true .

ex:inYear a odrl:Constraint ;
    odrl:leftOperand ex:performedAt ; odrl:operator odrl:gteq ;
    odrl:rightOperand "2026-01-01T00:00:00Z"^^xsd:dateTime .

ex:euDomiciled a odrl:LeftOperand ;
    dprod:operandSource dprod:stateSource ;
    dprod:operandProperty ex:euDomiciled ;
    rdfs:range xsd:boolean .

ex:performedAt a odrl:LeftOperand ;
    dprod:operandSource dprod:contextSource ;
    dprod:operandProperty due2:actionTime ;
    rdfs:range xsd:dateTime .
"""


def failures(path: Path, body: str, on_duty: bool = False) -> list[str]:
    """What the checker reports for `body`, with `ex:c0` the constraint of the permission, or
    of its duty when `on_duty`."""
    slot = "odrl:constraint ex:c0 ;"
    path.write_text(
        HEAD.format(permission="" if on_duty else slot, duty=slot if on_duty else "") + body
    )
    return [f for report, _, _ in check_file(path, [], True) for f in report.failures()]


def test_a_shared_member_is_no_cycle(tmp_path: Path) -> None:
    """Guards against a walk that takes a node it has finished for one on its path: `ex:inEU`
    is reached twice, through `ex:c0` and through `ex:c1`, and the policy is admitted."""
    body = """
ex:c0 a odrl:LogicalConstraint ; odrl:and ( ex:inEU ex:c1 ) .
ex:c1 a odrl:LogicalConstraint ; odrl:or ( ex:inEU ex:inEU2 ) .
ex:inEU2 a odrl:Constraint ;
    odrl:leftOperand ex:euDomiciled ; odrl:operator odrl:eq ; odrl:rightOperand false .
"""
    assert failures(tmp_path / "policy.ttl", body) == []


def test_a_self_member_is_a_cycle(tmp_path: Path) -> None:
    """The shortest cycle, `ex:c0 odrl:and ( ex:c0 )`, is rejected and the message names it
    once round. The corpus case's cycle has two steps, so only this test sees a walk that
    leaves `root` off its path: it would find the cycle one step late, as
    `ex:c0 -> ex:c0 -> ex:c0`."""
    body = "ex:c0 a odrl:LogicalConstraint ; odrl:and ( ex:c0 ) .\n"
    assert failures(tmp_path / "policy.ttl", body) == [
        "logical constraint cycle: ex:c0 -> ex:c0 (due2-profiles.md §5) [MalformedConstraint]"
    ]


def chain(depth: int) -> str:
    """`ex:c0` to `ex:c{depth}`, each an `odrl:and` of the next, the last of `ex:inEU`."""
    body = "".join(
        f"ex:c{i} a odrl:LogicalConstraint ; odrl:and ( ex:c{i + 1} ) .\n" for i in range(depth)
    )
    return body + f"ex:c{depth} a odrl:LogicalConstraint ; odrl:and ( ex:inEU ) .\n"


def test_deep_nesting_is_admitted(tmp_path: Path) -> None:
    """A chain deeper than the recursion limit, on the permission and on the duty, whose
    tree the mixing check reads too. The recursive walk this one replaced raised
    `RecursionError` on the first."""
    depth = sys.getrecursionlimit() + 100
    assert failures(tmp_path / "permission.ttl", chain(depth)) == []
    assert failures(tmp_path / "duty.ttl", chain(depth), on_duty=True) == []


def test_mixing_is_found_below_the_root(tmp_path: Path) -> None:
    """An `odrl:or` of a guard, `ex:inEU`, and a witness condition, `ex:inYear`, nested in
    the duty's `odrl:and` and sharing `ex:inEU` with it, is reported once. No corpus case is
    rejected for mixing, so without this test a mixing check that read its members' kinds
    before computing them, or never reported, would pass."""
    body = """
ex:c0 a odrl:LogicalConstraint ; odrl:and ( ex:inEU ex:c1 ) .
ex:c1 a odrl:LogicalConstraint ; odrl:or ( ex:inEU ex:inYear ) .
"""
    found = failures(tmp_path / "policy.ttl", body, on_duty=True)
    assert found == [
        "ex:c1: odrl:or mixes a guard and a witness condition [MixedDutyConstraint]"
    ], found
