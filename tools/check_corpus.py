"""Mechanical checks for due2 policies and conformance cases.

Checks what can be checked without an evaluator:
  * the policy is admissible input to due2 normalisation
    (odrl-compound-to-atomic-normalization.md §3, due2-profiles.md §2-§8);
  * every left operand has a binding and every operator is admitted
    (due2-profiles.md §3-§4);
  * case.json is well formed and consistent with the policy and its bindings
    (conformance/README.md).

Usage:
  check_corpus.py conformance/cases            # every case directory
  check_corpus.py path/to/policy.ttl [...]     # single policy files
  check_corpus.py --profile dprod file.ttl     # select a profile explicitly

Exit status is non-zero when any error is found. Warnings do not fail.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import RDF, RDFS, XSD
from rdflib.term import Node

ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
DPROD = Namespace("https://ekgf.org/dprod/spec/develop/")
DUE2 = Namespace("https://w3id.org/due2/profile#")

ROOT = Path(__file__).resolve().parent.parent
PROFILES = ROOT / "profiles"
CORE = [PROFILES / "due2-core.ttl", PROFILES / "odrl-actions.ttl"]
MODULES = {
    str(DPROD): [*sorted((PROFILES / "vendor" / "dprod").glob("*.ttl")), PROFILES / "dprod.ttl"],
    str(DUE2): [PROFILES / "due2-core.ttl"],
}
ALIASES = {"dprod": str(DPROD), "due2": str(DUE2)}
# IM 2.1: a policy uses only Core terms, or declares the profiles whose terms
# it uses. Normalisation selects a profile's binding module by odrl:profile
# (normalisation spec 3), so an undeclared namespace is a W1 input error.
NAMESPACED_PROFILES = {str(DPROD): "DPROD Contracts", str(DUE2): "due2 core"}

POLICY_CLASSES = {ODRL.Policy, ODRL.Set, ODRL.Offer, ODRL.Agreement}
RULE_EDGES = {
    ODRL.permission: ODRL.Permission,
    ODRL.prohibition: ODRL.Prohibition,
    ODRL.obligation: ODRL.Duty,
}
NESTED_EDGES = (ODRL.duty, ODRL.consequence, ODRL.remedy)
SOURCES = {DPROD.requestSource, DPROD.stateSource, DPROD.contextSource, DUE2.witnessSource}
CONTEXT_PROPS = {DPROD.agent, DPROD.clock, DUE2.actionTime}
OPERATORS = {
    ODRL[o]
    for o in (
        "eq",
        "neq",
        "lt",
        "lteq",
        "gt",
        "gteq",
        "isAnyOf",
        "isNoneOf",
        "isAllOf",
        "isPartOf",
        "hasPart",
        "isA",
    )
}
SET_BASED = {
    ODRL.isA,
    ODRL.hasPart,
    ODRL.isPartOf,
    ODRL.isAllOf,
    ODRL.isAnyOf,
    ODRL.isNoneOf,
}  # Vocab §3.16.7-3.16.12: a list, or repeated values, as the right operand (decisions/0013)
CONTESTED = {
    ODRL.isPartOf,
    ODRL.hasPart,
    ODRL.isA,
}  # list readings adopted, not given (decisions/0005)
CONNECTIVES = {ODRL["and"], ODRL["or"], ODRL.xone, DPROD["not"]}
REJECTED = {
    ODRL.inheritFrom: "inheritFrom",
    ODRL.andSequence: "andSequence",
    ODRL.rightOperandReference: "rightOperandReference",
    ODRL.implies: "implies",
    ODRL.source: "odrl:source outside a collection",
}
CONFLICT_VALUES = {ODRL.prohibit, ODRL.perm, ODRL.invalid}
NUMERIC = {
    XSD.integer,
    XSD.decimal,
    XSD.int,
    XSD.long,
    XSD.nonNegativeInteger,
    XSD.positiveInteger,
    XSD.short,
}
REJECTED_CODE = {ODRL.andSequence: "UnsupportedConnective"}  # others: UnsupportedConstruct
FLOATING = {XSD.float, XSD.double}
VERDICTS = {"Permit", "Deny", "Pending", "NotApplicable", "Indeterminate"}
CLASSIFICATIONS = {"odrl-core", "odrl-profile", "partial", "not-expressible"}
# left operand -> (source, property, cardinality), for the operands a policy reads.
type Used = dict[Node, tuple[Node, Node, Node]]


DIAGNOSTICS_DOC = ROOT / "docs" / "spec" / "due2-diagnostics.md"


def load_registry() -> dict[str, tuple[str, int]]:
    """code -> (severity, stage), from the registry table (due2-diagnostics.md 3)."""
    reg: dict[str, tuple[str, int]] = {}
    for line in DIAGNOSTICS_DOC.read_text().splitlines():
        m = re.match(r"^\| `(\w+)` \| (error|warning) \| (\d) \|", line)
        if m:
            reg[m.group(1)] = (m.group(2), int(m.group(3)))
    return reg


REGISTRY = load_registry()


@dataclass
class Report:
    """errors: case-format and harness failures. diagnostics: W1 errors the
    policy would be rejected with, as (code, message); a negative case expects
    them. Warnings, W1's and the checker's own, never fail."""

    name: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    diagnostics: list[tuple[str, str]] = field(default_factory=list)
    expected: list[str] = field(default_factory=list)  # a negative case's rejection, as expected

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def diag(self, code: str, msg: str) -> None:
        if code not in REGISTRY:
            raise KeyError(f"diagnostic {code} is not in {DIAGNOSTICS_DOC.name}")
        if REGISTRY[code][0] == "warning":
            self.warnings.append(f"{msg} [{code}]")
        else:
            self.diagnostics.append((code, msg))

    def rejection(self) -> list[str]:
        """The codes W1 reports: every error of the first stage that has one (workflows 4)."""
        if not self.diagnostics:
            return []
        first = min(REGISTRY[c][1] for c, _ in self.diagnostics)
        return sorted({c for c, _ in self.diagnostics if REGISTRY[c][1] == first})

    def failures(self) -> list[str]:
        return self.errors + [f"{m} [{c}]" for c, m in self.diagnostics]


def parse(paths: list[Path]) -> Graph:
    g = Graph()
    for p in paths:
        g.parse(p)
    return g


def q(g: Graph, node: Node) -> str:
    try:
        return node.n3(g.namespace_manager)
    except Exception:  # noqa: BLE001
        return str(node)


def subclass_closure(g: Graph) -> set[Node]:
    """Classes treated as ODRL policy classes: declared rdfs:subClassOf edges only."""
    classes: set[Node] = set(POLICY_CLASSES)
    changed = True
    while changed:
        changed = False
        for s, _, o in g.triples((None, RDFS.subClassOf, None)):
            if o in classes and s not in classes:
                classes.add(s)
                changed = True
    return classes


def members(g: Graph, node: Node) -> list[Node]:
    """Objects of a logical connective: an RDF list or repeated values."""
    if (node, RDF.first, None) in g or node == RDF.nil:
        return list(Collection(g, node))
    return [node]


DURATION_RE = re.compile(
    r"^-?P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)W)?(?:(\d+)D)?"
    r"(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$"
)
DATETIME_RE = re.compile(r"^-?\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$")


def single_kind_duration(lexical: str) -> bool:
    """A duration of one kind only: year-month, or day-time (due2-profiles.md §4)."""
    m = DURATION_RE.match(lexical)
    if not m:
        return False
    ym = bool(m.group(1) or m.group(2))
    dt = bool(m.group(3) or m.group(4) or m.group(5) or m.group(6) or m.group(7))
    return ym != dt  # exactly one kind present


def check_duty_timing(g: Graph, rule: Node, kind: Node, r: Report) -> None:
    """dprod:deadline and dprod:recurrence — duty timing (due2-profiles.md §7)."""
    dl = list(g.objects(rule, DPROD.deadline))
    rc = list(g.objects(rule, DPROD.recurrence))
    if kind != ODRL.Duty and (dl or rc):
        r.diag(
            "TimingOutsideDuty",
            f"{q(g, rule)}: dprod:deadline and dprod:recurrence are duty terms, "
            f"not terms of {q(g, kind)}",
        )
        return
    if len(dl) > 1:
        r.diag("InvalidTiming", f"{q(g, rule)}: more than one dprod:deadline")
    if len(rc) > 1:
        r.diag("InvalidTiming", f"{q(g, rule)}: more than one dprod:recurrence")
    for v in dl:
        if not isinstance(v, Literal) or v.datatype not in (XSD.dateTime, XSD.duration):
            r.diag(
                "InvalidTiming",
                f"{q(g, rule)}: dprod:deadline must be an xsd:dateTime (absolute) or "
                f"xsd:duration (relative to activation), got {v!r}",
            )
        elif v.datatype == XSD.duration and not single_kind_duration(str(v)):
            r.diag(
                "MixedDuration",
                f"{q(g, rule)}: duration deadline {v!r} mixes year-month and "
                f"day-time components (due2-profiles.md §4)",
            )
    for v in rc:
        if not isinstance(v, Literal) or "FREQ=" not in str(v):
            r.diag(
                "InvalidTiming",
                f"{q(g, rule)}: dprod:recurrence must be an RFC 5545 RRULE string "
                f"containing FREQ=, got {v!r}",
            )


class Bindings:
    """Operand bindings by precedence: policy graph > selected profiles > core."""

    def __init__(self, layers: list[Graph]) -> None:
        self.layers = layers

    def lookup(self, op: Node) -> tuple[list[Node], list[Node], Graph | None]:
        for g in self.layers:
            src = list(g.objects(op, DPROD.operandSource))
            prop = list(g.objects(op, DPROD.operandProperty))
            if src or prop:
                return src, prop, g
        return [], [], None

    def attr(self, op: Node, pred: Node) -> list[Node]:
        for g in self.layers:
            vals = list(g.objects(op, pred))
            if vals:
                return vals
        return []


def check_constraint(
    g: Graph, c: Node, b: Bindings, r: Report, used: Used, in_duty: bool = False
) -> None:
    for pred, label in REJECTED.items():
        if (c, pred, None) in g:
            r.diag(
                REJECTED_CODE.get(pred, "UnsupportedConstruct"),
                f"{q(g, c)}: {label} is not admitted",
            )
    conns = [p for p in CONNECTIVES if (c, p, None) in g]
    if conns:
        for p in conns:
            for o in g.objects(c, p):
                for m in members(g, o):
                    check_constraint(g, m, b, r, used, in_duty)
        return
    left = list(g.objects(c, ODRL.leftOperand))
    ops = list(g.objects(c, ODRL.operator))
    rights = list(g.objects(c, ODRL.rightOperand))
    if len(left) != 1 or len(ops) != 1:
        r.diag(
            "MalformedConstraint",
            f"{q(g, c)}: constraint needs exactly one leftOperand and one operator",
        )
        return
    op, operator = left[0], ops[0]
    if operator not in OPERATORS:
        r.diag(
            "UnsupportedOperator",
            f"{q(g, c)}: operator {q(g, operator)} is not in the core registry",
        )
    if not rights:
        r.diag("MalformedConstraint", f"{q(g, c)}: no rightOperand")
    lists = [ro for ro in rights if (ro, RDF.first, None) in g]
    if len(rights) > 1 and operator not in SET_BASED:
        r.diag(
            "MalformedConstraint",
            f"{q(g, c)}: {len(rights)} rightOperand values on {q(g, operator)}, "
            f"which is not set-based (due2-profiles.md 4, decisions/0013)",
        )
    elif lists and len(rights) > 1:
        r.diag(
            "MalformedConstraint",
            f"{q(g, c)}: a list rightOperand together with other values; write one list "
            f"or repeated values (due2-profiles.md 4, decisions/0013)",
        )
    if operator in CONTESTED and sum(len(members(g, ro)) for ro in rights) > 1:
        r.diag(
            "ContestedOperatorReading",
            f"{q(g, c)}: {q(g, operator)} with a list right operand "
            f"is read after Salas-Pareti (due2-profiles.md 4, decisions/0005)",
        )
    src, prop, _ = b.lookup(op)
    if len(src) != 1 or len(prop) != 1:
        r.diag("UnboundLeftOperand", f"{q(g, c)}: left operand {q(g, op)} has no single binding")
        return
    if src[0] not in SOURCES:
        r.diag(
            "InvalidBinding",
            f"{q(g, c)}: operand source {q(g, src[0])} is not one of the closed sources",
        )
    if src[0] == DUE2.witnessSource and not in_duty:
        r.diag("WitnessOutsideDuty", f"{q(g, c)}: witness-source operand {q(g, op)} outside a duty")
    if not isinstance(prop[0], URIRef):
        r.diag("InvalidBinding", f"{q(g, c)}: operandProperty of {q(g, op)} is not an IRI")
    if src[0] == DPROD.contextSource and prop[0] not in CONTEXT_PROPS:
        r.diag("InvalidBinding", f"{q(g, c)}: context property {q(g, prop[0])} is not a built-in")
    card = b.attr(op, DUE2.cardinality)
    used[op] = (src[0], prop[0], card[0] if card else DUE2.one)
    if card and card[0] == DUE2.set and operator in (ODRL.isPartOf, ODRL.hasPart):
        r.diag(
            "ContestedOperatorReading",
            f"{q(g, c)}: {q(g, operator)} over a set-valued operand "
            f"is read after Salas-Pareti (due2-profiles.md 4, decisions/0005)",
        )
    elif operator == ODRL.isA and card and card[0] == DUE2.set:
        r.diag("OperatorTypeMismatch", f"{q(g, c)}: isA takes one left value (due2-profiles.md 4)")
    allowed = b.attr(op, DUE2.allowedOperator)
    if allowed and operator not in allowed:
        r.diag(
            "OperatorTypeMismatch",
            f"{q(g, c)}: operator {q(g, operator)} not allowed for {q(g, op)}",
        )
    rng = b.attr(op, RDFS.range)
    for ro in rights:
        for v in members(g, ro):
            if isinstance(v, Literal):
                if v.datatype in FLOATING:
                    r.diag(
                        "FloatingPointOperand",
                        f"{q(g, c)}: floating-point right operand is not admitted",
                    )
                if rng and isinstance(rng[0], URIRef) and str(rng[0]).startswith(str(XSD)):
                    want, have = rng[0], v.datatype or XSD.string
                    if want != have and not (want in NUMERIC and have in NUMERIC):
                        r.diag(
                            "OperatorTypeMismatch",
                            f"{q(g, c)}: right operand {v!r} does not conform to range {q(g, want)}",
                        )


def witness_kinds(g: Graph, c: Node, b: Bindings) -> set[str]:
    """'witness' if the subtree reads a witness-dependent operand, 'guard' otherwise."""
    conns = [p for p in CONNECTIVES if (c, p, None) in g]
    if conns:
        kinds: set[str] = set()
        for p in conns:
            for o in g.objects(c, p):
                for m in members(g, o):
                    kinds |= witness_kinds(g, m, b)
        return kinds
    left = list(g.objects(c, ODRL.leftOperand))
    if len(left) != 1:
        return set()
    src, prop, _ = b.lookup(left[0])
    if src and (src[0] == DUE2.witnessSource or (prop and prop[0] == DUE2.actionTime)):
        return {"witness"}
    return {"guard"}


def check_mixed(g: Graph, c: Node, b: Bindings, r: Report) -> None:
    """Disjunction, xone, or negation mixing guards and witness conditions (workflows §5.2)."""
    for p in (ODRL["or"], ODRL.xone, DPROD["not"]):
        for o in g.objects(c, p):
            ms = members(g, o)
            kinds: set[str] = set()
            for m in ms:
                kinds |= witness_kinds(g, m, b)
            if len(kinds) == 2:
                r.diag(
                    "MixedDutyConstraint",
                    f"{q(g, c)}: {q(g, p)} mixes a guard and a witness condition",
                )
            for m in ms:
                check_mixed(g, m, b, r)
    for o in g.objects(c, ODRL["and"]):
        for m in members(g, o):
            check_mixed(g, m, b, r)


def check_rule(
    g: Graph,
    rule: Node,
    kind: Node,
    policy: Node,
    b: Bindings,
    r: Report,
    used: Used,
    seen: set[Node],
    path: list[Node],
    named: bool,
) -> None:
    if rule in path:
        r.diag(
            "RuleReferenceCycle",
            f"rule reference cycle: {' -> '.join(q(g, x) for x in [*path, rule])}",
        )
        return
    if rule in seen:
        return
    seen.add(rule)
    if isinstance(rule, BNode) and named:
        r.warn(f"anonymous {q(g, kind)} under {q(g, policy)}: corpus cases name every rule")
    for pred, label in REJECTED.items():
        if (rule, pred, None) in g:
            r.diag(
                REJECTED_CODE.get(pred, "UnsupportedConstruct"),
                f"{q(g, rule)}: {label} is not admitted",
            )
    check_duty_timing(g, rule, kind, r)
    actions = list(g.objects(rule, ODRL.action)) or list(g.objects(policy, ODRL.action))
    if not actions and not path:
        r.diag("MissingAction", f"{q(g, rule)}: no action, at rule or policy level")
    if not list(g.objects(rule, ODRL.action)) and path:
        r.diag("MissingAction", f"{q(g, rule)}: nested duty has no action")
    targets = list(g.objects(rule, ODRL.target))
    if not targets and not path:
        targets = list(g.objects(policy, ODRL.target))
    if kind in (ODRL.Permission, ODRL.Prohibition) and not targets:
        r.diag(
            "MissingTarget", f"{q(g, rule)}: {q(g, kind)} has no target, at rule or policy level"
        )
    if targets and (rule, ODRL.output, None) in g:
        r.diag("TargetAndOutput", f"{q(g, rule)}: both target and output")
    for c in list(g.objects(rule, ODRL.constraint)) + list(g.objects(rule, ODRL.refinement)):
        check_constraint(g, c, b, r, used, kind == ODRL.Duty)
        if kind == ODRL.Duty:
            check_mixed(g, c, b, r)
    for a in actions:
        for ref in g.objects(a, ODRL.refinement):
            check_constraint(g, ref, b, r, used, kind == ODRL.Duty)
    for pred in (ODRL.consequence, ODRL.remedy):
        if (rule, pred, None) in g:
            r.warn(f"{q(g, rule)}: {q(g, pred)} is carried by stage 1 but not evaluated for access")
    for pred in NESTED_EDGES:
        for d in g.objects(rule, pred):
            check_rule(g, d, ODRL.Duty, policy, b, r, used, seen, [*path, rule], named)


def ns_terms(g: Graph, ns: str) -> int:
    n = 0
    for _, p, o in g:
        if str(p).startswith(ns) or (isinstance(o, URIRef) and str(o).startswith(ns)):
            n += 1
    return n


ASSET_PARTY_EDGES = (
    ODRL.target,
    ODRL.output,
    ODRL.assignee,
    ODRL.assigner,
    ODRL.informedParty,
    ODRL.compensatedParty,
    ODRL.attributedParty,
    ODRL.consentingParty,
    ODRL.contractingParty,
    ODRL.trackingParty,
)


def asset_party_nodes(g: Graph) -> set[Node]:
    """Every node in an asset or party position, plus every declared collection."""
    nodes = {o for e in ASSET_PARTY_EDGES for o in g.objects(None, e)}
    nodes |= set(g.subjects(RDF.type, ODRL.AssetCollection))
    nodes |= set(g.subjects(RDF.type, ODRL.PartyCollection))
    return nodes


def check_policy(
    g: Graph, policy: Node, b: Bindings, profiles_graph: Graph, r: Report, named: bool
) -> Used:

    used: Used = {}
    declared = {str(p) for p in g.objects(policy, ODRL.profile)}
    for ns, label in NAMESPACED_PROFILES.items():
        if ns_terms(g, ns) and ns not in declared:
            r.diag(
                "UndeclaredProfile",
                f"{q(g, policy)}: uses {label} terms but declares no "
                f"odrl:profile <{ns}>; normalisation will not select its module",
            )
    if isinstance(policy, BNode) and not list(g.objects(policy, ODRL.uid)):
        r.diag("MissingPolicyIdentity", f"{q(g, policy)}: policy has no identity (IRI or odrl:uid)")
    for node in sorted(set(g.subjects(ODRL.uid, None)), key=str):
        if len(list(g.objects(node, ODRL.uid))) > 1:
            r.diag("MultipleUid", f"{q(g, node)}: more than one odrl:uid")
    for pred, label in REJECTED.items():
        if (policy, pred, None) in g:
            r.diag(
                REJECTED_CODE.get(pred, "UnsupportedConstruct"),
                f"{q(g, policy)}: {label} is not admitted",
            )
    for term in (DPROD.deadline, DPROD.recurrence):
        if (policy, term, None) in g:
            r.diag(
                "TimingOutsideDuty",
                f"{q(g, policy)}: {q(g, term)} on a Policy is not an extension point (duties only)",
            )
    # Asset and party nodes are where odrl:source and collection refinements
    # occur (IM 2.5.5-2.5.6). Rule and constraint nodes are checked in
    # check_rule and check_constraint, where odrl:source stays rejected.
    # A refinement-free odrl:source on a collection is admitted as an inert
    # annotation (profiles 8.1, 2026-10-11); refined collections are not.
    for node in sorted(asset_party_nodes(g), key=str):
        if (node, ODRL.refinement, None) in g:
            r.diag("UnsupportedConstruct", f"{q(g, node)}: collection refinement is not admitted")
    conflicts = list(g.objects(policy, ODRL.conflict))
    if len(conflicts) > 1:
        r.diag("InvalidConflict", f"{q(g, policy)}: more than one odrl:conflict")
    elif conflicts and conflicts[0] not in CONFLICT_VALUES:
        r.diag(
            "InvalidConflict",
            f"{q(g, policy)}: odrl:conflict {q(g, conflicts[0])} is not prohibit, perm, or invalid",
        )
    if (policy, RDF.type, ODRL.Request) in g:
        r.diag(
            "RequestAsPolicy", f"{q(g, policy)}: odrl:Request is an evaluation input, not a policy"
        )
    rules = [(rule, kind) for edge, kind in RULE_EDGES.items() for rule in g.objects(policy, edge)]
    if not rules:
        r.diag("NoRule", f"{q(g, policy)}: no permission, prohibition, or obligation")
    seen: set[Node] = set()
    for rule, kind in rules:
        check_rule(g, rule, kind, policy, b, r, used, seen, [], named)
    for c in g.objects(policy, ODRL.constraint):
        check_constraint(g, c, b, r, used)
    return used


def selected_profiles(g: Graph, policy: Node, explicit: list[str]) -> list[str]:
    sel = [ALIASES.get(p, p) for p in explicit]
    sel += [str(p) for p in g.objects(policy, ODRL.profile)]
    unknown = [p for p in sel if p not in MODULES]
    return [p for p in dict.fromkeys(sel) if p in MODULES] + unknown


def check_file(path: Path, explicit: list[str], named: bool) -> list[tuple[Report, Used, Graph]]:
    g = Graph()
    g.parse(path)
    pre = Graph()
    for p in CORE:
        pre.parse(p)
    for files in MODULES.values():
        for f in files:
            pre.parse(f)
    classes = subclass_closure(pre + g)
    policies = sorted({s for s, _, o in g.triples((None, RDF.type, None)) if o in classes}, key=str)
    out: list[tuple[Report, Used, Graph]] = []
    if not policies:
        r = Report(str(path))
        r.diag(
            "NoPolicy",
            "no policy node (odrl:Policy, Set, Offer, Agreement, or a declared subclass)",
        )
        return [(r, {}, g)]
    for policy in policies:
        r = Report(f"{path.name} :: {q(g, policy)}")
        sel = selected_profiles(g, policy, explicit)
        layers = [g]
        profile_graph = Graph()
        for p in sel:
            if p not in MODULES:
                r.warn(f"profile {p} has no due2 binding module; its terms are metadata")
                continue
            profile_graph += parse(MODULES[p])
        if len(profile_graph):
            layers.append(profile_graph)
        layers.append(parse(CORE))
        used = check_policy(g, policy, Bindings(layers), profile_graph, r, named)
        out.append((r, used, g))
    return out


def expand(curie: str, prefixes: dict[str, str]) -> str:
    if curie.startswith(("http://", "https://", "urn:")):
        return curie
    pfx, _, local = curie.partition(":")
    if pfx in prefixes:
        return prefixes[pfx] + local
    return curie


def check_rejection(case: dict[str, Any], reports: list[Report], r: Report) -> None:
    """A negative case (conformance/README.md): W1 must reject the policy with
    exactly the expected codes, those of the first failing stage."""
    exp = case["expected_rejection"]
    codes = exp.get("codes", [])
    if case.get("scenarios"):
        r.err("case.json: a negative case has no scenarios")
    if not codes:
        r.err("case.json: expected_rejection.codes is empty")
    for c in codes:
        if REGISTRY.get(c, ("", 0))[0] != "error":
            r.err(f"case.json: expected code {c} is not an error in due2-diagnostics.md")
    if not exp.get("why"):
        r.err("case.json: expected_rejection.why missing")
    got = sorted({c for x in reports for c in x.rejection()})
    if sorted(set(codes)) != got:
        r.err(f"expected rejection {sorted(set(codes))}, the policy gives {got or 'none'}")
        return
    for x in reports:
        x.expected = [f"{m} [{c}]" for c, m in x.diagnostics]
        x.diagnostics = []


def check_case(case_dir: Path) -> list[Report]:
    policy_path = case_dir / "policy.ttl"
    case_path = case_dir / "case.json"
    reports: list[Report] = []
    if not policy_path.exists():
        r = Report(case_dir.name)
        r.err("policy.ttl missing")
        return [r]
    results = check_file(policy_path, [], named=True)
    if len(results) != 1:
        r = Report(case_dir.name)
        r.diag(
            "MultiplePolicies", f"policy.ttl must contain exactly one policy, found {len(results)}"
        )
        reports.append(r)
    for r, _, _ in results:
        r.name = f"{case_dir.name}"
        reports.append(r)
    if not case_path.exists():
        reports[0].err("case.json missing")
        return reports
    r, used, g = results[0]
    try:
        case = json.loads(case_path.read_text())
    except json.JSONDecodeError as e:
        r.err(f"case.json: {e}")
        return reports
    negative = "expected_rejection" in case
    for key in ("case", "source", "classification") + (() if negative else ("scenarios",)):
        if key not in case:
            r.err(f"case.json: missing '{key}'")
    if not isinstance(case.get("odrl22_valid", True), bool):
        r.err("case.json: odrl22_valid must be true or false")
    if negative:
        check_rejection(case, reports, r)
        return reports
    if case.get("odrl22_valid", True) is False:
        r.err("case.json: a policy that is not valid ODRL 2.2 can only be a negative case")
    if case.get("classification") not in CLASSIFICATIONS:
        r.err(f"case.json: classification must be one of {sorted(CLASSIFICATIONS)}")
    if case.get("classification") in (
        "odrl-profile",
        "partial",
        "not-expressible",
    ) and not case.get("needs"):
        r.err("case.json: 'needs' must list the profile terms or missing constructs")
    prefixes = {"odrl": str(ODRL), "dprod": str(DPROD), "due2": str(DUE2), "xsd": str(XSD)}
    prefixes.update(case.get("prefixes", {}))
    request_props = {str(p) for s, p, _ in used.values() if s == DPROD.requestSource}
    state_props = {str(p) for s, p, _ in used.values() if s == DPROD.stateSource}
    witness_props = {str(p) for s, p, _ in used.values() if s == DUE2.witnessSource}
    set_props = {str(p) for _, p, c in used.values() if c == DUE2.set}

    rules = {str(x) for x in g.subjects(RDF.type, None)}
    scenarios = case.get("scenarios", [])
    if not scenarios:
        r.err("case.json: no scenarios")
    for i, sc in enumerate(scenarios):
        tag = f"scenario {i + 1} ({sc.get('name', '?')})"
        req = sc.get("request", {})
        for k in ("action", "at"):  # target may be absent (workflows 3.2)
            if k not in req:
                r.err(f"{tag}: request.{k} missing")
        for k in req.get("params", {}):
            if expand(k, prefixes) not in request_props:
                r.warn(f"{tag}: request param {k} is read by no bound operand")
        sotw = sc.get("sotw", {})
        if "effective_at" not in sotw:
            r.err(f"{tag}: sotw.effective_at missing")
        for k, fact in sotw.get("facts", {}).items():
            if expand(k, prefixes) not in state_props:
                r.warn(f"{tag}: SOTW fact {k} is read by no bound operand")
            st = fact.get("status", "resolved")
            n = len(fact.get("values", []))
            prop_iri = expand(k, prefixes)
            ok = {"resolved": n >= 1 or prop_iri in set_props, "conflict": n >= 2}.get(st, n == 0)
            if st not in ("resolved", "missing", "invalid", "conflict", "unresolved") or not ok:
                r.err(f"{tag}: fact {k} has status {st} with {n} values")
        for ev in sotw.get("evidence", []):
            for k in ("id", "occurred_at", "actor", "action"):
                if k not in ev:
                    r.err(f"{tag}: evidence missing {k}")
            for k in ev.get("params", {}):
                if expand(k, prefixes) not in witness_props:
                    r.warn(f"{tag}: evidence param {k} is read by no witness-source operand")
        has_deadline = (None, DPROD.deadline, None) in g
        for k, at in sotw.get("activation", {}).items():
            if not DATETIME_RE.match(str(at)):
                r.err(f"{tag}: activation of {k} is not an xsd:dateTime instant: {at!r}")
        exp = sc.get("expected", {})
        if exp.get("verdict") not in VERDICTS:
            r.err(f"{tag}: expected.verdict must be one of {sorted(VERDICTS)}")
        if not exp.get("why"):
            r.err(f"{tag}: expected.why missing")
        for alt in exp.get("frontier", []):
            for d in alt:
                if expand(d, prefixes) not in rules:
                    r.err(f"{tag}: frontier duty {d} is not a typed node in policy.ttl")
        for ob in exp.get("obligations", []):
            if expand(ob.get("duty", ""), prefixes) not in rules:
                r.err(f"{tag}: obligation {ob.get('duty')} is not a typed node in policy.ttl")
            if ob.get("status") not in ("fulfilled", "outstanding", "violated", "unknown"):
                r.err(
                    f"{tag}: obligation status {ob.get('status')!r} is not one of fulfilled, outstanding, violated, unknown"
                )
            if ob.get("status") == "violated" and not has_deadline:
                r.err(
                    f"{tag}: obligation {ob.get('duty')} is violated, but the policy has no "
                    f"dprod:deadline — without one, a duty is never violated"
                )
            if "instance" in ob and not DATETIME_RE.match(str(ob["instance"])):
                r.err(
                    f"{tag}: obligation instance {ob['instance']!r} is not an xsd:dateTime instant"
                )
        if exp.get("verdict") == "Pending" and not exp.get("frontier"):
            r.err(f"{tag}: Pending needs a frontier")
        check_explanation(tag, exp, sc.get("config", {}), g, prefixes, r)
        check_range(tag, exp, r)
    return reports


# workflows 3.5, 6.4: the roles a verdict's basis may hold, and the elimination rules.
BASIS_ROLES = {
    "Deny": {"prohibition", "obligation"},
    "Permit": {"permission", "obligation"},
    "Pending": {"permission", "duty", "obligation"},
    "Indeterminate": {"unknown", "obligation"},
    "NotApplicable": {"closed", "obligation"},
}
STRATEGIES = {"prohibit", "perm", "invalid"}
CHAIN = ("Deny", "NotApplicable", "Pending", "Permit")


def check_range(tag: str, exp: dict[str, Any], r: Report) -> None:
    """expected.verdict_range (conformance/README.md, workflows 3.5, decisions/0011): an
    Indeterminate's least and greatest completion verdict, low below high in the chain."""
    if "verdict_range" not in exp:
        return
    rng = entry(exp["verdict_range"], {"low", "high"})
    if rng is None:
        r.err(f"{tag}: verdict_range must be {{low, high}}: {exp['verdict_range']!r}")
    elif exp.get("verdict") != "Indeterminate":
        r.err(f"{tag}: verdict_range is recorded for an Indeterminate only (workflows 3.5)")
    elif rng["low"] not in CHAIN or rng["high"] not in CHAIN:
        r.err(f"{tag}: verdict_range ends must be one of {list(CHAIN)}")
    elif CHAIN.index(rng["low"]) >= CHAIN.index(rng["high"]):
        r.err(f"{tag}: verdict_range low {rng['low']} is not below high {rng['high']}")


def entry(x: object, keys: set[str]) -> dict[str, Any] | None:
    """x as an object with exactly these keys, or None."""
    return dict(x) if isinstance(x, dict) and set(x) == keys else None  # pyright: ignore[reportUnknownArgumentType]


def check_explanation(
    tag: str, exp: dict[str, Any], config: dict[str, Any], g: Graph, pfx: dict[str, str], r: Report
) -> None:
    """expected.verdict_basis and expected.eliminated (conformance/README.md, workflows 3.7):
    shape, that each IRI is a rule or duty of the right kind, and that roles fit the verdict."""
    perms = {str(x) for x in g.subjects(RDF.type, ODRL.Permission)}
    prohibs = {str(x) for x in g.subjects(RDF.type, ODRL.Prohibition)}
    preconds = {str(x) for x in g.objects(None, ODRL.duty)}
    obligs = {str(x) for x in g.objects(None, ODRL.obligation)}
    conflict = {str(x).removeprefix(str(ODRL)) for x in g.objects(None, ODRL.conflict)}
    verdict = exp.get("verdict")
    by_role: dict[str, set[str]] = {}
    if "verdict_basis" in exp:
        kinds = {
            "permission": perms,
            "closed": perms,
            "prohibition": prohibs,
            "duty": preconds,
            "obligation": obligs,
            "unknown": perms | prohibs | preconds | obligs,
        }
        for raw in exp["verdict_basis"]:
            b = entry(raw, {"ref", "role"})
            if b is None:
                r.err(f"{tag}: verdict_basis entry must be {{ref, role}}: {raw!r}")
                continue
            role, ref = b["role"], expand(b["ref"], pfx)
            if role not in kinds:
                r.err(f"{tag}: verdict_basis role {role!r} is not one of {sorted(kinds)}")
                continue
            if ref not in kinds[role]:
                r.err(f"{tag}: verdict_basis {b['ref']} is no {role} of policy.ttl")
            if verdict in BASIS_ROLES and role not in BASIS_ROLES[verdict]:
                r.err(f"{tag}: role {role} does not fit {verdict} (workflows 6.4)")
            by_role.setdefault(role, set()).add(ref)
        violated = {
            expand(o.get("duty", ""), pfx)
            for o in exp.get("obligations", [])
            if o.get("status") == "violated"
        }
        need = {
            "Permit": "permission" in by_role,
            "Pending": "permission" in by_role and "duty" in by_role,
            "Indeterminate": "unknown" in by_role,
            "Deny": "prohibition" in by_role
            or (
                config.get("violations") == "deny"
                and bool(by_role.get("obligation", set()) & violated)
            ),
        }
        if not need.get(str(verdict), True):
            r.err(f"{tag}: verdict_basis lacks the atoms that determine {verdict} (workflows 6.4)")
        frontier = {expand(d, pfx) for alt in exp.get("frontier", []) for d in alt}
        if verdict == "Pending" and by_role.get("duty", set()) != frontier:
            r.err(f"{tag}: the basis's duties must be the frontier's duties")
        in_force = {expand(o.get("duty", ""), pfx) for o in exp.get("obligations", [])}
        if by_role.get("obligation", set()) != in_force:
            r.err(f"{tag}: the basis's obligations must be expected.obligations' duties")
    if "eliminated" in exp:
        combination = config.get("combination", "prohibit-overrides")
        removers = {
            "prohibit": (perms, prohibs),
            "perm": (prohibs, perms),
            "invalid": (perms | prohibs | obligs, perms | prohibs),
            "violated_precondition": (perms, preconds),
            combination: (perms, prohibs),
        }
        closed_by: set[str] = set()
        for raw in exp["eliminated"]:
            e = entry(raw, {"ref", "by", "rule"})
            if e is None:
                r.err(f"{tag}: eliminated entry must be {{ref, by, rule}}: {raw!r}")
                continue
            rule, ref, by = e["rule"], expand(e["ref"], pfx), expand(e["by"], pfx)
            if rule not in removers:
                r.err(f"{tag}: elimination rule {rule!r} is not one of {sorted(removers)}")
                continue
            if rule in STRATEGIES and conflict and rule not in conflict:
                r.err(
                    f"{tag}: elimination rule {rule} is not the policy's conflict {sorted(conflict)}"
                )
            kinds_ref, kinds_by = removers[rule]
            if ref not in kinds_ref or by not in kinds_by or ref == by:
                r.err(f"{tag}: {e['by']} cannot eliminate {e['ref']} under {rule} (workflows 3.5)")
            if rule == "violated_precondition":
                closed_by.add(ref)
        if (
            "verdict_basis" in exp
            and verdict == "NotApplicable"
            and by_role.get("closed", set()) != closed_by
        ):
            r.err(f"{tag}: the closed candidates must be the violated_precondition eliminations")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--profile", action="append", default=[], help="select a profile (e.g. dprod)")
    ap.add_argument("--quiet", action="store_true", help="print only failing items")
    args = ap.parse_args()
    reports: list[Report] = []
    for p in args.paths:
        if p.is_dir() and (p / "policy.ttl").exists():
            reports += check_case(p)
        elif p.is_dir():
            for d in sorted(x for x in p.iterdir() if x.is_dir()):
                reports += check_case(d)
        else:
            reports += [r for r, _, _ in check_file(p, args.profile, named=False)]
    errors = 0
    for r in reports:
        fails = r.failures()
        errors += len(fails)
        if args.quiet and not fails:
            continue
        status = "FAIL" if fails else ("rej" if r.expected else ("warn" if r.warnings else "ok"))
        print(f"{status:4}  {r.name}")
        for m in fails:
            print(f"      error: {m}")
        for m in r.expected:
            print(f"      rejected, as expected: {m}")
        for m in r.warnings:
            print(f"      warn:  {m}")
    rejected = sum(1 for r in reports if r.expected and not r.failures())
    print(
        f"\n{len(reports)} checked, {sum(1 for r in reports if r.failures())} failing, "
        f"{errors} errors" + (f", {rejected} rejected as expected" if rejected else "")
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
