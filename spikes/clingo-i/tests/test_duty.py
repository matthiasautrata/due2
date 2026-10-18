"""Duty atoms, the guard/witness split, and the duty findings (DESIGN.md § Tests).

`odrl:duty` and `odrl:obligation` decline the vector (DESIGN.md § Declines), so these tests
ground the program files directly: solve 1's for the atoms and the split, which `rows` reads,
and solve 2's, integrity constraints included, for the findings and statuses, which
`findings` reads.
"""

from __future__ import annotations

import copy

import pytest
from clingo import Control

from clingo_i.interpret import SOLVE_1, SOLVE_2, Interpreter, load_programs
from clingo_i.json_types import Obj
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
    # instance's activation (due2-workflows.md §5.3). Without deadline_kind, both would reject
    # as InvalidTiming.
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


def findings(interp: Interpreter, body: str, profile: bool = False, **sections: Obj) -> set[str]:
    """One model of solve 2's files, integrity.lp included, of `ex:p` with `body`, IRIs shortened.

    Grounding solve 2's files and not solve 1's makes the integrity constraints apply: a model
    exists only if every item has one value and every instance one status. World `k` is fixed
    before completion, so every model has the same findings.
    """
    head = f"ex:p a odrl:Set{' ; odrl:profile dprod:' if profile else ''} ;\n"
    facts = interp.facts(vector(HEAD + head + body, **sections))
    programs = load_programs()
    ctl = Control(["--warn=none", "--models=1"])
    ctl.add("base", [], facts + "\n" + "\n".join(programs[f] for f in SOLVE_2))
    ctl.ground([("base", [])])
    out: set[str] = set()
    result = ctl.solve(on_model=lambda m: out.update(str(s) for s in m.symbols(atoms=True)))
    assert result.satisfiable, "an integrity constraint failed"
    for long, short in SHORT.items():
        out = {s.replace(f'"{long}', f'"{short}') for s in out}
    return out


def value_of(found: set[str], item: str) -> str | None:
    """The truth value of `item` in `found`, or None if it is not an item."""
    values = {s[len(f"holds({item},") : -1] for s in found if s.startswith(f"holds({item},")}
    assert len(values) <= 1
    return values.pop() if values else None


D = DUTY_D + "none)"  # ex:d under ex:perm, which names no assignee: the bearer is the subject
PRE = permission(" ; odrl:duty ex:d") + "ex:d a odrl:Duty ; odrl:action odrl:compensate .\n"
PAID: Obj = {"id": "ex:e1", "occurred_at": "2026-05-01T00:00:00Z", "actor": "ex:alice",
             "action": "odrl:compensate"}  # fmt: skip


def test_unguarded_duty_without_evidence_is_outstanding(duty_interpreter: Interpreter) -> None:
    # No guard makes owed t (due2-workflows.md §5.1), so the duty is an instance; no evidence
    # makes fulfilled f, and no deadline means none has passed. Without the empty-set 2 in
    # owed's #min, an unguarded duty would have no owed value and no instance.
    found = findings(duty_interpreter, PRE)
    assert value_of(found, f"owed({D})") == "t"
    assert value_of(found, f"fulfilled({D})") == "f"
    assert pick(found, "status") == {f"status(k,{D},outstanding)"}


@pytest.mark.parametrize(
    ("fact", "owed"),
    [({"status": "resolved", "values": [{"@id": "ex:v"}]}, "t"), ({"status": "missing"}, "u"),
     ({"status": "resolved", "values": [{"@id": "ex:other"}]}, "f")],
)  # fmt: skip
def test_guard_decides_owed(duty_interpreter: Interpreter, fact: Obj, owed: str) -> None:
    # A guard is read in world k: a missing fact makes owed u, and a u-owed duty is still an
    # instance, so it is not dropped as if it were not owed (unknown is never false). Only an
    # f guard removes the instance, and with it the fulfilled item.
    found = findings(
        duty_interpreter, duty_with(leaf("g"), GUARD), profile=True, sotw={"facts": {"ex:g": fact}}
    )
    assert value_of(found, f"owed({D})") == owed
    assert (value_of(found, f"fulfilled({D})") is None) == (owed == "f")


def test_matching_evidence_fulfils(duty_interpreter: Interpreter) -> None:
    # Every check is t, so the witness and the duty are: without the witness pair, evidence
    # would never be read and every duty would stay outstanding.
    found = findings(duty_interpreter, PRE, sotw={"evidence": [PAID]})
    assert value_of(found, f'witness({D},"ex:e1")') == "t"
    assert pick(found, "status") == {f"status(k,{D},fulfilled)"}


@pytest.mark.parametrize(
    ("change", "kind", "extra", "config"),
    [({"actor": "ex:bob"}, "actor", "", {}),
     ({"action": "odrl:delete"}, "action", "", {}),
     ({"occurred_at": "2026-07-01T00:00:00Z"}, "effective", "", {}),
     ({}, "signer", "", {"signers": [{"duty": "ex:d", "issuer": "ex:bank"}]}),
     ({}, "discharges", " ; due2:instanceScope due2:grant", {}),
     ({}, "object", " ; odrl:output ex:receipt", {})],
)  # fmt: skip
def test_each_failing_check_fails_the_witness(
    duty_interpreter: Interpreter, change: Obj, kind: str, extra: str, config: Obj
) -> None:
    # Each check of the witness test (due2-workflows.md §5.3) on its own: one f check makes the
    # witness f, and the duty, with no other witness, stays outstanding. Without the check's
    # rule its item would have no value and the integrity constraint would fail.
    body = PRE.replace("odrl:compensate .", f"odrl:compensate{extra} .")
    duty = D.replace("none,none", '"ex:receipt",none') if kind == "object" else D
    found = findings(
        duty_interpreter, body, profile=True, sotw={"evidence": [PAID | change]}, config=config
    )
    assert value_of(found, f'check({duty},"ex:e1",{kind})') == "f"
    assert value_of(found, f'witness({duty},"ex:e1")') == "f"
    assert pick(found, "status") == {f"status(k,{duty},outstanding)"}


def test_admitted_issuer_and_discharged_reference_pass(duty_interpreter: Interpreter) -> None:
    # The counterparts of the signer and discharges failures: the issuer the config admits and a
    # discharge naming the request's reference make both checks t.
    evidence: Obj = {
        **PAID,
        "issuer": "ex:bank",
        "discharges": {"duty": "ex:d", "reference": "req-1"},
    }
    found = findings(
        duty_interpreter,
        PRE.replace("odrl:compensate .", "odrl:compensate ; due2:instanceScope due2:grant ."),
        profile=True,
        sotw={"evidence": [evidence]},
        config={"signers": [{"duty": "ex:d", "issuer": "ex:bank"}]},
    )
    assert value_of(found, f'check({D},"ex:e1",signer)') == "t"
    assert value_of(found, f'check({D},"ex:e1",discharges)') == "t"
    assert pick(found, "status") == {f"status(k,{D},fulfilled)"}


@pytest.mark.parametrize(
    ("params", "witness", "status"),
    [({"ex:w": {"@id": "ex:v"}}, "t", "fulfilled"), ({"ex:w": {"@id": "ex:other"}}, "f",
      "outstanding"), ({}, "u", "unknown")],
)  # fmt: skip
def test_witness_condition_is_read_from_the_evidence(
    duty_interpreter: Interpreter, params: Obj, witness: str, status: str
) -> None:
    # A witness leaf is read in world wit(E), from E's params: absent, it is u, so the duty's
    # status is unknown, not outstanding. Read in world k, it would be u for every evidence.
    evidence: Obj = {**PAID, "params": params}
    found = findings(
        duty_interpreter,
        duty_with(leaf("w"), WITNESS),
        profile=True,
        sotw={"evidence": [evidence]},
    )
    assert value_of(found, f'witness({D},"ex:e1")') == witness
    assert pick(found, "status") == {f"status(k,{D},{status})"}


def test_witness_only_nodes_are_not_world_k_items(duty_interpreter: Interpreter) -> None:
    # The and splits: the guard leaf is a world-k item, the witness leaf is evaluated only in
    # wit(E), and the and itself in no world, since its parts are read apart. Without
    # witness_only, world k would give the witness leaf a value, u, with no evidence to read.
    found = findings(
        duty_interpreter,
        duty_with(f"[ odrl:and ( {leaf('g')} {leaf('w')} ) ]", WITNESS, GUARD),
        profile=True,
        sotw={"evidence": [PAID]},
    )
    guards = {s[s.rindex(",b(") + 1 : -1] for s in pick(found, "guard")}  # guard(Y, C)
    assert {
        s[len("item(c(") : -2] for s in pick(found, "item") if s.startswith("item(c(")
    } == guards
    witness = {s[s.rindex(",b(") + 1 : -1] for s in pick(found, "witness_cond")}
    assert {s for s in pick(found, "evaluates") if s.startswith("evaluates(wit(")} == {
        f'evaluates(wit("ex:e1"),{c})' for c in witness
    }


def test_no_named_subject_leaves_the_actor_unknown(duty_interpreter: Interpreter) -> None:
    # The bearer is the request subject, and the request names none: the actor check is u, not
    # f, so the duty is unknown rather than outstanding.
    found = findings(duty_interpreter, PRE, sotw={"evidence": [PAID]}, request={"parties": {}})
    assert value_of(found, f'check({D},"ex:e1",actor)') == "u"
    assert pick(found, "status") == {f"status(k,{D},unknown)"}


def root_obligation(deadline: str) -> str:
    """A root obligation on ex:a, with a permission the request matches, so it is in force."""
    return (
        "    odrl:target ex:a ; odrl:permission ex:perm ; odrl:obligation ex:o .\n"
        + "ex:perm a odrl:Permission ; odrl:action odrl:use .\n"
        + f"ex:o a odrl:Duty ; odrl:action odrl:delete ; dprod:deadline {deadline} .\n"
    )


@pytest.mark.parametrize(
    ("deadline", "activation", "status"),
    [('"2026-05-01T00:00:00Z"^^xsd:dateTime', {}, "violated"),
     ('"2027-01-01T00:00:00Z"^^xsd:dateTime', {}, "outstanding"),
     ('"P1D"^^xsd:duration', {"ex:o": "2026-05-01T00:00:00Z"}, "violated"),
     ('"P1D"^^xsd:duration', {}, "outstanding")],
)  # fmt: skip
def test_deadline_decides_outstanding_or_violated(
    duty_interpreter: Interpreter, deadline: str, activation: Obj, status: str
) -> None:
    # An unfulfilled duty is violated once its deadline has passed at effective_at. A relative
    # deadline counts from the activation, or from effective_at when the duty is not activated
    # (due2-workflows.md §5.3), so P1D with no activation has not passed.
    found = findings(
        duty_interpreter, root_obligation(deadline), profile=True, sotw={"activation": activation}
    )
    assert value_of(found, f"in_force({O})") == "t"
    assert pick(found, "status") == {f"status(k,{O},{status})"}


CHECKS = ("effective", "deadline", "action", "object", "actor", "signer", "discharges")


def test_late_witness_is_not_timely(duty_interpreter: Interpreter) -> None:
    # Evidence after the deadline matches every other check but is not timely, so the duty is
    # violated: without the deadline check, late performance would fulfil it.
    late: Obj = {"id": "ex:e1", "occurred_at": "2026-05-15T00:00:00Z", "actor": "ex:alice",
            "action": "odrl:delete", "object": "ex:a"}  # fmt: skip
    found = findings(
        duty_interpreter,
        root_obligation('"2026-05-01T00:00:00Z"^^xsd:dateTime'),
        profile=True,
        sotw={"evidence": [late]},
    )
    # The steps of DESIGN.md § duty.lp's worked example, each one pinned.
    assert pick(found, "policy_match") == {f"policy_match({O},2)"}
    assert value_of(found, f"in_force({O})") == "t"
    checks = {k: value_of(found, f'check({O},"ex:e1",{k})') for k in CHECKS}
    assert checks == {k: "f" if k == "deadline" else "t" for k in CHECKS}
    assert value_of(found, f'witness({O},"ex:e1")') == "f"
    assert value_of(found, f"fulfilled({O})") == "f"
    assert {f"deadline_at({O},0)", f"passed({O})"} <= found
    assert pick(found, "status") == {f"status(k,{O},violated)"}


def test_obligation_without_a_matching_rule_is_not_in_force(duty_interpreter: Interpreter) -> None:
    # A root obligation is in force only while some permission or prohibition of its policy
    # matches the request (due2-workflows.md §5.2); here the policy has none, so in_force is f
    # and there is no instance. The request asks for the obligation's own action on its target,
    # so a program that matched the obligation itself would find it in force.
    found = findings(duty_interpreter, obligation(""), request={"action": "odrl:delete"})
    assert value_of(found, f"in_force({O})") == "f"
    assert pick(found, "status") == set()


@pytest.mark.parametrize(("occurred", "witness"), [("2026-05-01", "t"), ("2026-05-20", "f")])
def test_action_time_is_the_evidence_time(
    duty_interpreter: Interpreter, occurred: str, witness: str
) -> None:
    # In world wit(E), due2:actionTime is E's occurred_at, not the request's time: read from
    # the request (2026-06-01), both cases would be f.
    by = (
        "[ odrl:leftOperand ex:t ; odrl:operator odrl:lteq ;"
        + ' odrl:rightOperand "2026-05-10T00:00:00Z"^^xsd:dateTime ]'
    )
    found = findings(
        duty_interpreter,
        duty_with(by, ACTION_TIME),
        profile=True,
        sotw={"evidence": [PAID | {"occurred_at": f"{occurred}T00:00:00Z"}]},
    )
    assert value_of(found, f'witness({D},"ex:e1")') == witness
