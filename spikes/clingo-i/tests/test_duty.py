"""Duty atoms and the guard/witness split, on solve 1's model (DESIGN.md § Tests).

`odrl:duty` and `odrl:obligation` still decline the vector (DESIGN.md § Declines), so these
tests ground solve 1's files directly and read the relations of structure.lp and duty.lp.
"""

from __future__ import annotations

import copy

import pytest
from clingo import Control

from clingo_i.interpret import SOLVE_1, Interpreter, load_programs
from tests.conftest import INIT, PREFIXES, vector

DPROD = "https://ekgf.org/dprod/spec/develop/"
DUE2 = "https://w3id.org/due2/profile#"
HEAD = (
    PREFIXES
    + f"@prefix dprod: <{DPROD}> .\n@prefix due2: <{DUE2}> .\n"
    + "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"
    + "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n"
)
SHORT = {"https://example.org/": "ex:", "http://www.w3.org/ns/odrl/2/": "odrl:"}
SHOWN = (
    "duty_atom", "pre", "bearer", "obligation", "duty_deadline", "deadline_kind", "duty_scope",
    "guard", "witness_cond", "reject", "unsupported",
)  # fmt: skip


@pytest.fixture(scope="module")
def duty_interpreter() -> Interpreter:
    """INIT with the bearer roles of profiles/due2-core.ttl and profiles/dprod.ttl."""
    init = copy.deepcopy(INIT)
    modules = init["modules"]
    assert isinstance(modules, dict)
    modules["core.ttl"] = str(modules["core.ttl"]) + (
        f"@prefix due2: <{DUE2}> .\nodrl:assignee due2:playsRole due2:bearer .\n"
    )
    modules["dprod.ttl"] = (
        f"@prefix due2: <{DUE2}> .\n@prefix dprod: <{DPROD}> .\n"
        + "dprod:subjectOfDuty due2:playsRole due2:bearer .\n"
    )
    profiles = init["profiles"]
    assert isinstance(profiles, dict)
    profiles[DPROD] = ["dprod.ttl"]
    return Interpreter(init)


def rows(interp: Interpreter, body: str, profile: bool = False) -> set[str]:
    """Solve 1's model of the policy `ex:p` with `body`, as the `SHOWN` rows, IRIs shortened."""
    head = f"ex:p a odrl:Set{' ; odrl:profile dprod:' if profile else ''} ;\n"
    facts = interp.facts(vector(HEAD + head + body))
    programs = load_programs()
    ctl = Control(["--warn=none"])
    ctl.add("base", [], facts + "\n" + "\n".join(programs[f] for f in SOLVE_1))
    ctl.ground([("base", [])])
    out: set[str] = set()
    ctl.solve(on_model=lambda m: out.update(str(s) for s in m.symbols(atoms=True)))
    for long, short in SHORT.items():
        out = {s.replace(f'"{long}', f'"{short}') for s in out}
    return {s for s in out if s.split("(")[0] in SHOWN}


def pick(found: set[str], name: str) -> set[str]:
    return {s for s in found if s.startswith(name + "(")}


def declines(found: set[str]) -> set[str]:
    """The `unsupported` rows other than the duty properties, which still decline every vector."""
    return pick(found, "unsupported") - {
        'unsupported("odrl:duty")', 'unsupported("odrl:obligation")',
    }  # fmt: skip


PERM = 'a("ex:perm","odrl:use","ex:a",'
DUTY_D = 'a("ex:d","odrl:compensate",none,'


def test_precondition_inherits_each_parent_atoms_bearer(duty_interpreter: Interpreter) -> None:
    # A duty that states no function takes the bearer of each parent atom: two assignees give
    # two duty atoms, and each permission atom's edge goes to its own bearer's atom only.
    found = rows(
        duty_interpreter,
        """    odrl:permission ex:perm .
ex:perm a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a ;
    odrl:assignee ex:alice, ex:bob ; odrl:duty ex:d .
ex:d a odrl:Duty ; odrl:action odrl:compensate .
""",
    )
    alice, bob = DUTY_D + '"ex:alice")', DUTY_D + '"ex:bob")'
    assert pick(found, "duty_atom") == {f"duty_atom({alice})", f"duty_atom({bob})"}
    assert pick(found, "pre") == {
        f'pre({PERM}"ex:alice"),{alice})',
        f'pre({PERM}"ex:bob"),{bob})',
    }
    assert pick(found, "bearer") == {f'bearer({alice},"ex:alice")', f'bearer({bob},"ex:bob")'}
    assert pick(found, "obligation") == set()
    assert pick(found, "duty_scope") == {f"duty_scope({alice},member)", f"duty_scope({bob},member)"}
    assert pick(found, "reject") == set()


def test_shared_duty_under_one_bearer_is_one_atom(duty_interpreter: Interpreter) -> None:
    # Two permissions with the same assignee share ex:d: one atom, so one instance, with an
    # edge from each. A parent with no bearer passes `none`, the request subject.
    found = rows(
        duty_interpreter,
        """    odrl:permission ex:perm, ex:perm2, ex:perm3 .
ex:perm a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a ; odrl:assignee ex:alice ;
    odrl:duty ex:d .
ex:perm2 a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:b ; odrl:assignee ex:alice ;
    odrl:duty ex:d .
ex:perm3 a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:c ; odrl:duty ex:d .
ex:d a odrl:Duty ; odrl:action odrl:compensate .
""",
    )
    alice, nobody = DUTY_D + '"ex:alice")', DUTY_D + "none)"
    assert pick(found, "duty_atom") == {f"duty_atom({alice})", f"duty_atom({nobody})"}
    assert pick(found, "pre") == {
        f'pre({PERM}"ex:alice"),{alice})',
        f'pre(a("ex:perm2","odrl:use","ex:b","ex:alice"),{alice})',
        f'pre(a("ex:perm3","odrl:use","ex:c",none),{nobody})',
    }
    assert f"bearer({nobody},none)" in found


def test_duty_with_its_own_party_inherits_nothing(duty_interpreter: Interpreter) -> None:
    # A duty that states an assignee keeps it under every parent atom, and odrl:output is its
    # relation.
    found = rows(
        duty_interpreter,
        """    odrl:permission ex:perm .
ex:perm a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a ;
    odrl:assignee ex:alice, ex:bob ; odrl:duty ex:d .
ex:d a odrl:Duty ; odrl:action odrl:compensate ; odrl:output ex:receipt ; odrl:assignee ex:carol .
""",
    )
    carol = 'a("ex:d","odrl:compensate","ex:receipt","ex:carol")'
    assert pick(found, "duty_atom") == {f"duty_atom({carol})"}
    assert pick(found, "pre") == {
        f'pre({PERM}"ex:alice"),{carol})',
        f'pre({PERM}"ex:bob"),{carol})',
    }


def test_root_obligation_takes_policy_level_values(duty_interpreter: Interpreter) -> None:
    # A root obligation fills each family it leaves unstated from the policy, like a rule; a
    # precondition duty takes none of them, so ex:d has no relation.
    found = rows(
        duty_interpreter,
        """    odrl:target ex:a ; odrl:assignee ex:alice ;
    odrl:permission ex:perm ; odrl:obligation ex:o .
ex:perm a odrl:Permission ; odrl:action odrl:use ; odrl:duty ex:d .
ex:d a odrl:Duty ; odrl:action odrl:compensate .
ex:o a odrl:Duty ; odrl:action odrl:delete .
""",
    )
    o = 'a("ex:o","odrl:delete","ex:a","ex:alice")'
    alice = DUTY_D + '"ex:alice")'
    assert pick(found, "duty_atom") == {f"duty_atom({o})", f"duty_atom({alice})"}
    assert pick(found, "obligation") == {f"obligation({o})"}
    assert pick(found, "pre") == {f'pre({PERM}"ex:alice"),{alice})'}


def test_stated_bearer_beats_interiorised(duty_interpreter: Interpreter) -> None:
    # The obligation states dprod:subjectOfDuty and receives the policy-level odrl:assignee; the
    # stated value is the only bearer (due2-workflows.md §4). Without states_bearer/1 the two
    # functions would disagree and the vector would decline.
    found = rows(
        duty_interpreter,
        """    odrl:target ex:a ; odrl:assignee ex:alice ; odrl:obligation ex:o .
ex:o a odrl:Duty ; odrl:action odrl:delete ; dprod:subjectOfDuty ex:bob .
""",
        profile=True,
    )
    assert declines(found) == set()
    assert pick(found, "bearer") == {'bearer(a("ex:o","odrl:delete","ex:a","ex:bob"),"ex:bob")'}


def test_two_stated_bearer_functions_decline(duty_interpreter: Interpreter) -> None:
    # A duty that states both bearer functions names two bearers for one performance.
    found = rows(
        duty_interpreter,
        """    odrl:target ex:a ; odrl:obligation ex:o .
ex:o a odrl:Duty ; odrl:action odrl:delete ; odrl:assignee ex:alice ;
    dprod:subjectOfDuty ex:bob .
""",
        profile=True,
    )
    assert 'unsupported("duty: bearer from two functions")' in found
    agreeing = rows(
        duty_interpreter,
        """    odrl:target ex:a ; odrl:obligation ex:o .
ex:o a odrl:Duty ; odrl:action odrl:delete ; odrl:assignee ex:alice ;
    dprod:subjectOfDuty ex:alice .
""",
        profile=True,
    )
    assert declines(agreeing) == set()
    assert pick(agreeing, "bearer") == {
        'bearer(a("ex:o","odrl:delete","ex:a","ex:alice"),"ex:alice")'
    }


WITNESS = "ex:w dprod:operandSource due2:witnessSource ; dprod:operandProperty ex:w .\n"
GUARD = "ex:g dprod:operandSource dprod:stateSource ; dprod:operandProperty ex:g .\n"
ACTION_TIME = (
    "ex:t dprod:operandSource dprod:contextSource ; dprod:operandProperty due2:actionTime .\n"
)


def duty_with(constraint: str, *bindings: str) -> str:
    return (
        """    odrl:permission ex:perm .
ex:perm a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a ; odrl:duty ex:d .
"""
        + f"ex:d a odrl:Duty ; odrl:action odrl:compensate ; odrl:constraint {constraint} .\n"
        + "".join(bindings)
    )


def leaf(op: str) -> str:
    return f"[ odrl:leftOperand ex:{op} ; odrl:operator odrl:eq ; odrl:rightOperand ex:v ]"


def test_conjunction_splits_into_guard_and_witness(duty_interpreter: Interpreter) -> None:
    # The and splits; the witness leaf and the due2:actionTime leaf are witness conditions, the
    # state leaf a guard. The witness operand is admissible inside a duty.
    found = rows(
        duty_interpreter,
        duty_with(
            f"[ odrl:and ( {leaf('g')} {leaf('w')} {leaf('t')} ) ]", WITNESS, GUARD, ACTION_TIME
        ),
        profile=True,
    )
    assert pick(found, "reject") == set()
    assert len(pick(found, "guard")) == 1
    assert len(pick(found, "witness_cond")) == 2


def test_witness_refinement_of_a_duty_action(duty_interpreter: Interpreter) -> None:
    # A refinement of a duty's action is one of its conditions (due2-workflows.md §5.2): without
    # duty_root's refinement rule, this witness leaf would be neither guard nor witness
    # condition, and node_tree would let WitnessOutsideDuty fire on it.
    found = rows(
        duty_interpreter,
        f"""    odrl:permission ex:perm .
ex:perm a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a ; odrl:duty ex:d .
ex:d a odrl:Duty ; odrl:action [ rdf:value odrl:compensate ; odrl:refinement {leaf("w")} ] .
{WITNESS}""",
        profile=True,
    )
    assert pick(found, "reject") == set()
    assert len(pick(found, "witness_cond")) == 1
    assert pick(found, "guard") == set()


@pytest.mark.parametrize("conn", ["odrl:or", "odrl:xone"])
def test_mixed_part_is_rejected(duty_interpreter: Interpreter, conn: str) -> None:
    # A disjunction over a guard and a witness condition has no single place to be read. Over
    # two witness leaves it is one witness condition, so the reject reads the mixture, not the
    # connective.
    found = rows(
        duty_interpreter,
        duty_with(f"[ {conn} ( {leaf('g')} {leaf('w')} ) ]", WITNESS, GUARD),
        profile=True,
    )
    assert len({s for s in pick(found, "reject") if "MixedDutyConstraint" in s}) == 1
    pure = rows(
        duty_interpreter,
        duty_with(f"[ {conn} ( {leaf('w')} {leaf('t')} ) ]", WITNESS, ACTION_TIME),
        profile=True,
    )
    assert pick(pure, "reject") == set()
    assert len(pick(pure, "witness_cond")) == 1


def test_negated_mixture_is_rejected(duty_interpreter: Interpreter) -> None:
    # Only a top-level conjunction splits: a conjunction under `not` is one part, and has_guard
    # and has_witness close over every level of it.
    found = rows(
        duty_interpreter,
        duty_with(f"[ dprod:not [ odrl:and ( {leaf('g')} {leaf('w')} ) ] ]", WITNESS, GUARD),
        profile=True,
    )
    assert len({s for s in pick(found, "reject") if "MixedDutyConstraint" in s}) == 1


def obligation(extra: str) -> str:
    return (
        "    odrl:target ex:a ; odrl:obligation ex:o .\n"
        + f"ex:o a odrl:Duty ; odrl:action odrl:delete{extra} .\n"
    )


def permission(extra: str) -> str:
    return (
        "    odrl:permission ex:perm .\n"
        + f"ex:perm a odrl:Permission ; odrl:action odrl:use ; odrl:target ex:a{extra} .\n"
    )


O = 'a("ex:o","odrl:delete","ex:a",none)'
# A witness leaf refining a permission's action: node_tree reaches it through the action term.
WITNESS_IN_RULE = (
    permission("").replace("odrl:action odrl:use", "odrl:action ex:act")
    + f"ex:act rdf:value odrl:use ; odrl:refinement {leaf('w')} .\n"
    + WITNESS
)


def test_stated_output_keeps_the_policy_target_out(duty_interpreter: Interpreter) -> None:
    # odrl:output is the relation family, so a root obligation that states it takes no policy
    # target: one relation, no TargetAndOutput.
    found = rows(duty_interpreter, obligation(" ; odrl:output ex:b"))
    assert pick(found, "duty_atom") == {'duty_atom(a("ex:o","odrl:delete","ex:b",none))'}
    assert pick(found, "reject") == set()


@pytest.mark.parametrize(
    ("deadline", "kind"),
    [('"2027-01-01T00:00:00Z"^^xsd:dateTime', "absolute"), ('"P1D"^^xsd:duration', "relative")],
)
def test_deadline_kinds(duty_interpreter: Interpreter, deadline: str, kind: str) -> None:
    # A deadline's kind is its datatype: a dateTime is absolute, a duration counts from the
    # instance's activation (due2-workflows.md §5.3). Without deadline_kind, both would reject as InvalidTiming.
    found = rows(duty_interpreter, obligation(f" ; dprod:deadline {deadline}"), profile=True)
    assert pick(found, "reject") == set()
    assert len(pick(found, "duty_deadline")) == 1
    assert {s.rsplit(",", 1)[1] for s in pick(found, "deadline_kind")} == {f"{kind})"}


@pytest.mark.parametrize(
    ("body", "code"),
    [
        (obligation(' ; dprod:deadline "tomorrow"'), "InvalidTiming"),
        (obligation(' ; dprod:deadline "P1D"^^xsd:duration, "P2D"^^xsd:duration'), "InvalidTiming"),
        (permission(' ; dprod:deadline "P1D"^^xsd:duration'), "TimingOutsideDuty"),
        (obligation(" ; odrl:target ex:a ; odrl:output ex:b"), "TargetAndOutput"),
        ("    odrl:obligation ex:o .\nex:o a odrl:Duty ; odrl:target ex:a .\n", "MissingAction"),
        (permission(" ; odrl:duty ex:perm"), "RuleReferenceCycle"),
        (WITNESS_IN_RULE, "WitnessOutsideDuty"),
    ],
)  # fmt: skip
def test_duty_rejections(duty_interpreter: Interpreter, body: str, code: str) -> None:
    # Each code of due2-diagnostics.md that structure.lp or operand.lp emits for a duty, on the
    # smallest policy that has it: without the rule, the policy would be admissible.
    found = rows(duty_interpreter, body, profile=True)
    assert any(f'reject("{code}"' in s for s in found), found


def test_recurrence_declines(duty_interpreter: Interpreter) -> None:
    # Recurrence declines the whole vector: its occurrences are not evaluated (DESIGN.md §
    # Declines), and a verdict that ignored them would claim more than the spike reads.
    found = rows(duty_interpreter, obligation(' ; dprod:recurrence "FREQ=DAILY"'), profile=True)
    assert 'unsupported("recurrence")' in found


@pytest.mark.parametrize(
    ("scope", "expected"),
    [("", "member"), (" ; due2:instanceScope due2:grant", "grant"),
     (" ; due2:instanceScope due2:member", "member")],
)  # fmt: skip
def test_instance_scope(duty_interpreter: Interpreter, scope: str, expected: str) -> None:
    # Member is the default (due2-workflows.md §5.3); an explicit value is read as stated.
    found = rows(duty_interpreter, obligation(scope), profile=True)
    assert pick(found, "duty_scope") == {f"duty_scope({O},{expected})"}
    assert declines(found) == set()


def test_unknown_instance_scope_declines(duty_interpreter: Interpreter) -> None:
    # A value outside the two would otherwise give the duty no scope, and no instance key.
    found = rows(duty_interpreter, obligation(" ; due2:instanceScope ex:sometimes"), profile=True)
    assert 'unsupported("duty: instance scope")' in found
