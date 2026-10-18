"""Validate due2 policies against ODRL 2.2 itself.

Runs conformance/odrl22-shape.ttl (due2's SHACL encoding of the ODRL
Information Model 2.2, every constraint cited) over policy files, with the
official ODRL 2.2 vocabulary and due2's profile modules merged for class
hierarchy and term typing. Node types the vocabulary entails (rdfs:range of
odrl:permission etc., rdfs:domain of odrl:leftOperand, the connective of a
Logical Constraint) are added, since the IM leaves them implicit. Otherwise
policies are validated *as written* — no preprocessing: compact form (IM 2.7.1), list-valued right operands for
set-based operators (IM 2.5.1), and list-form logical constraints (IM 2.5.2)
are all checked natively.

Also checks IM 2.1's vocabulary rule — a policy uses only ODRL terms, or
declares the profiles whose terms it uses (odrl:profile) — which SHACL cannot
scope to a single policy file once graphs are merged, so it is done on the
policy file alone before merging. due2's reading of the rule is
docs/decisions/0020: a term in a vocabulary position is defined by the odrl:
namespace of the official vocabulary, a declared profile's modules, or the
policy itself.

This checks ODRL 2.2 validity only. due2 admissibility (the constructs due2
rejects with diagnostics) is tools/check_corpus.py. The protocol and its
recorded results are conformance/odrl22-conformance.md.

Usage:
  check_odrl22.py conformance/cases            # every case policy
  check_odrl22.py file.ttl [...]               # single policy files
  check_odrl22.py --all                        # corpus + vendored examples

A case whose case.json says "odrl22_valid": false (a negative case for a
policy that is not ODRL 2.2, conformance/README.md) is expected to fail; it
counts as failing only if it conforms.

Exit status is non-zero when any violation is found.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# pyshacl's own annotations leave parts of validate's return type unknown.
from pyshacl import validate  # pyright: ignore[reportUnknownVariableType]
from rdflib import BNode, Graph, Namespace, URIRef
from rdflib.namespace import RDF
from rdflib.term import Node

ROOT = Path(__file__).resolve().parent.parent
SHAPE = ROOT / "conformance" / "odrl22-shape.ttl"
PROFILES = ROOT / "profiles"
W3C_VOCABULARY = PROFILES / "vendor" / "w3c" / "ODRL22.ttl"
CORE_MODULES = [PROFILES / "due2-core.ttl", PROFILES / "odrl-actions.ttl"]
DPROD_MODULES = [*sorted((PROFILES / "vendor" / "dprod").glob("*.ttl")), PROFILES / "dprod.ttl"]
BASE = [W3C_VOCABULARY, *CORE_MODULES, *DPROD_MODULES]

ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
# IM 2.1: use only ODRL terms, or declare the profiles whose terms are used.
NAMESPACED_PROFILES = {
    "https://ekgf.org/dprod/spec/develop/": "DPROD Contracts",
    "https://w3id.org/due2/profile#": "due2 core",
}
# The modules a declared profile adds to the baseline, CORE_MODULES
# (check_corpus.py MODULES).
PROFILE_MODULES = {
    "https://ekgf.org/dprod/spec/develop/": DPROD_MODULES,
    "https://w3id.org/due2/profile#": [],
}
# Where a policy names vocabulary (decisions/0020 #2). odrl:unit is not among
# them: a unit is a value's measure, from any vocabulary (#3).
VOCABULARY_POSITIONS = (
    ODRL.action,
    ODRL.leftOperand,
    ODRL.operator,
    ODRL.function,
    ODRL.relation,
    ODRL.conflict,
)


def ns_terms(g: Graph, ns: str) -> int:
    """Terms (as predicates or objects) in the policy file alone."""
    n = 0
    for _, p, o in g:
        if str(p).startswith(ns) or (isinstance(o, URIRef) and str(o).startswith(ns)):
            n += 1
    return n


def typed(g: Graph) -> set[Node]:
    return {s for s in g.subjects(RDF.type, None) if isinstance(s, URIRef)}


@dataclass(frozen=True)
class Vocabulary:
    """The terms each source defines (decisions/0020 #1): the odrl: namespace of
    the official vocabulary and the baseline modules always, a profile's modules
    when the policy declares it."""

    baseline: frozenset[Node]
    profiles: dict[str, frozenset[Node]]

    @classmethod
    def load(cls) -> Vocabulary:
        w3c = Graph().parse(W3C_VOCABULARY)
        odrl = {t for t in typed(w3c) if str(t).startswith(str(ODRL))}
        core = Graph()
        for f in CORE_MODULES:
            core.parse(f)
        profiles: dict[str, frozenset[Node]] = {}
        for ns, files in PROFILE_MODULES.items():
            g = Graph()
            for f in files:
                g.parse(f)
            profiles[ns] = frozenset(typed(g))
        return cls(frozenset(odrl | typed(core)), profiles)


def vocabulary_terms(alone: Graph) -> set[Node]:
    """The IRIs in vocabulary positions. A refined action is a blank node whose
    rdf:value names the action (IM 2.5.4)."""
    terms: set[Node] = set()
    for p in VOCABULARY_POSITIONS:
        for o in alone.objects(None, p):
            if isinstance(o, BNode) and p == ODRL.action:
                o = alone.value(o, RDF.value)
            if isinstance(o, URIRef):
                terms.add(o)
    return terms


def check_profile_declarations(alone: Graph, vocabulary: Vocabulary) -> list[str]:
    declared = {str(p) for p in alone.objects(None, ODRL.profile)}
    problems: list[str] = []
    for ns, label in NAMESPACED_PROFILES.items():
        if ns_terms(alone, ns) and ns not in declared:
            problems.append(
                f"IM 2.1: policy uses {label} terms but declares no odrl:profile <{ns}>"
            )
    # A declared profile due2 has no module for may define any term (#5).
    if declared - PROFILE_MODULES.keys():
        return problems
    defined = set(vocabulary.baseline) | typed(alone)
    for ns in declared:
        defined |= vocabulary.profiles[ns]
    for t in sorted(vocabulary_terms(alone) - defined, key=str):
        problems.append(
            f"IM 2.1: <{t}> is defined by neither the ODRL vocabulary (odrl: namespace), "
            "a declared profile, nor the policy"
        )
    return problems


def violations_text(results_graph: Graph) -> list[str]:
    SH = Namespace("http://www.w3.org/ns/shacl#")

    def vals(r: Node, p: Node) -> list[str]:
        return [str(o) for o in results_graph.objects(r, p)]

    out: list[str] = []
    for r in sorted(results_graph.subjects(RDF.type, SH.ValidationResult), key=str):
        out.append(
            " | ".join(
                [
                    "Focus=" + (vals(r, SH.focusNode) or ["?"])[0],
                    "Path=" + (vals(r, SH.resultPath) or ["-"])[0],
                    (vals(r, SH.sourceConstraintComponent) or ["?"])[0].rsplit("#", 1)[-1],
                    "Msg=" + (vals(r, SH.resultMessage) or ["?"])[0],
                ]
            )
        )
    return out


# Types the ODRL 2.2 vocabulary itself entails for untyped nodes. The IM leaves
# rule and constraint typing implicit (its own Turtle examples write
# `odrl:permission [ ... ]`); RDFS range/domain axioms in ODRL22.ttl make the
# type explicit. Only these axioms are applied — no general RDFS closure — so
# the shape sees each node with the class the vocabulary assigns it, and an
# untyped Permission no longer escapes PermissionShape.
RANGE_TYPES = {
    ODRL.permission: ODRL.Permission,  # rdfs:range odrl:Permission
    ODRL.prohibition: ODRL.Prohibition,  # rdfs:range odrl:Prohibition
    ODRL.obligation: ODRL.Duty,  # rdfs:range odrl:Duty
    ODRL.duty: ODRL.Duty,
    ODRL.remedy: ODRL.Duty,
    ODRL.consequence: ODRL.Duty,
    ODRL.target: ODRL.Asset,
    ODRL.assignee: ODRL.Party,
    ODRL.assigner: ODRL.Party,
}
# Deliberately absent: rdfs:range odrl:LeftOperand of odrl:leftOperand. Applying
# it would make IM 2.5.1's "MUST be a LeftOperand" vacuous; whether an operand
# is declared is a vocabulary fact a profile must supply (IM 2.1), not a type
# the shape may assume. rdfs:range odrl:Action of odrl:action is applied only to
# blank nodes, for the same reason: a refined action is an untyped node
# (IM 2.5.4), and an IRI action is an Action only where a vocabulary or the
# policy types it so (decisions/0020 #7).
DOMAIN_TYPES = {ODRL.leftOperand: ODRL.Constraint}  # rdfs:domain odrl:Constraint
# IM 2.5.2: a Logical Constraint is identified by its operand property; the
# vocabulary declares no domain for them, so the connective is the evidence.
CONNECTIVES = [
    ODRL["and"],
    ODRL["or"],
    ODRL.xone,
    ODRL.andSequence,
    URIRef("https://ekgf.org/dprod/spec/develop/not"),
]


def entailed_types(alone: Graph) -> Graph:
    t = Graph()
    for p, c in RANGE_TYPES.items():
        for o in alone.objects(None, p):
            t.add((o, RDF.type, c))
    for o in alone.objects(None, ODRL.action):
        if isinstance(o, BNode):
            t.add((o, RDF.type, ODRL.Action))
    for p, c in DOMAIN_TYPES.items():
        for s in alone.subjects(p, None):
            t.add((s, RDF.type, c))
    for p in CONNECTIVES:
        for s in alone.subjects(p, None):
            t.add((s, RDF.type, ODRL.LogicalConstraint))
    return t


def check_file(
    path: Path, shapes: Graph, base: Graph, vocabulary: Vocabulary
) -> tuple[str, list[str]]:
    alone = Graph()
    alone.parse(path)
    problems = check_profile_declarations(alone, vocabulary)
    data = Graph()
    data += base
    data += alone
    data += entailed_types(alone)
    try:
        conforms, rg, _ = validate(  # pyright: ignore[reportUnknownVariableType]
            data_graph=data, shacl_graph=shapes, inference="none", advanced=True
        )
    except Exception as e:  # noqa: BLE001
        return str(path), [f"HARNESS ERROR (pyshacl raised): {e}"]
    if not isinstance(rg, Graph):
        return str(path), [f"HARNESS ERROR (pyshacl): {rg}"]
    if not conforms:
        problems += violations_text(rg)
    name = str(path.resolve().relative_to(ROOT))
    return name, problems


def expects_invalid(path: Path) -> bool:
    """A corpus case marked as not ODRL 2.2 (conformance/README.md, negative cases)."""
    case = path.parent / "case.json"
    if path.name != "policy.ttl" or not case.exists():
        return False
    try:
        return json.loads(case.read_text()).get("odrl22_valid", True) is False
    except json.JSONDecodeError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("paths", nargs="*", type=Path)
    ap.add_argument("--all", action="store_true", help="corpus cases plus vendored DPROD examples")
    ap.add_argument("--quiet", action="store_true", help="print only failing items")
    args = ap.parse_args()

    targets: list[Path] = []
    if args.all:
        targets += [
            p / "policy.ttl"
            for p in sorted((ROOT / "conformance" / "cases").iterdir())
            if (p / "policy.ttl").exists()
        ]
        targets += sorted((ROOT / "profiles" / "vendor" / "dprod" / "examples").glob("*.ttl"))
    for p in args.paths:
        if p.is_dir():
            if (p / "policy.ttl").exists():
                targets.append(p / "policy.ttl")
            else:
                targets += [
                    x / "policy.ttl" for x in sorted(p.iterdir()) if (x / "policy.ttl").exists()
                ]
        else:
            targets.append(p)
    if not targets:
        ap.error("no targets (give paths, a case directory, or --all)")

    shapes = Graph()
    shapes.parse(SHAPE)
    base = Graph()
    for f in BASE:
        base.parse(f)
    vocabulary = Vocabulary.load()

    bad = xfail = 0
    for t in targets:
        try:
            name, problems = check_file(t, shapes, base, vocabulary)
        except Exception as e:  # noqa: BLE001
            name, problems = str(t), [f"HARNESS ERROR: {e}"]
        if expects_invalid(t):
            if problems:
                xfail += 1
                if not args.quiet:
                    print(f"xfail {name}  (odrl22_valid: false; {len(problems)} violations)")
            else:
                bad += 1
                print(
                    f"FAIL  {name}\n      case.json says odrl22_valid: false, but the policy conforms"
                )
            continue
        if problems:
            bad += 1
            print(f"FAIL  {name}")
            for m in problems:
                print(f"      {m}")
        elif not args.quiet:
            print(f"ok    {name}")
    total = len(targets)
    print(f"\n{total} checked, {bad} failing" + (f", {xfail} invalid as expected" if xfail else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
