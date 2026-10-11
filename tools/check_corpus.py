#!/usr/bin/env python3
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

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import RDF, RDFS, XSD

ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
DPROD = Namespace("https://ekgf.org/dprod/spec/develop/")
DUE2 = Namespace("https://w3id.org/due2/profile#")

ROOT = Path(__file__).resolve().parent.parent
PROFILES = ROOT / "profiles"
CORE = [PROFILES / "due2-core.ttl", PROFILES / "odrl-actions.ttl"]
MODULES = {
    str(DPROD): sorted((PROFILES / "vendor" / "dprod").glob("*.ttl")) + [PROFILES / "dprod.ttl"],
    str(DUE2): [PROFILES / "due2-core.ttl"],
}
ALIASES = {"dprod": str(DPROD), "due2": str(DUE2)}
# IM 2.1: a policy uses only Core terms, or declares the profiles whose terms
# it uses. Normalisation selects a profile's binding module by odrl:profile
# (normalisation spec 3), so an undeclared namespace is a W1 input error.
NAMESPACED_PROFILES = {str(DPROD): "DPROD Contracts", str(DUE2): "due2 core"}

POLICY_CLASSES = {ODRL.Policy, ODRL.Set, ODRL.Offer, ODRL.Agreement}
RULE_EDGES = {ODRL.permission: ODRL.Permission, ODRL.prohibition: ODRL.Prohibition,
              ODRL.obligation: ODRL.Duty}
NESTED_EDGES = (ODRL.duty, ODRL.consequence, ODRL.remedy)
SOURCES = {DPROD.requestSource, DPROD.stateSource, DPROD.contextSource, DUE2.witnessSource}
CONTEXT_PROPS = {DPROD.agent, DPROD.clock, DUE2.actionTime}
OPERATORS = {ODRL[o] for o in ("eq", "neq", "lt", "lteq", "gt", "gteq", "isAnyOf",
                               "isNoneOf", "isAllOf", "isPartOf", "hasPart", "isA")}
CONNECTIVES = {ODRL["and"], ODRL["or"], ODRL.xone, DPROD["not"]}
REJECTED = {ODRL.inheritFrom: "inheritFrom", ODRL.andSequence: "andSequence",
            ODRL.rightOperandReference: "rightOperandReference", ODRL.implies: "implies",
            ODRL.source: "collection source"}
CONFLICT_VALUES = {ODRL.prohibit, ODRL.perm, ODRL.invalid}
NUMERIC = {XSD.integer, XSD.decimal, XSD.int, XSD.long, XSD.nonNegativeInteger,
           XSD.positiveInteger, XSD.short}
FLOATING = {XSD.float, XSD.double}
VERDICTS = {"Permit", "Deny", "Pending", "NotApplicable", "Indeterminate"}
CLASSIFICATIONS = {"odrl-core", "odrl-profile", "partial", "not-expressible"}


@dataclass
class Report:
    name: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def parse(paths: list[Path]) -> Graph:
    g = Graph()
    for p in paths:
        g.parse(p)
    return g


def q(g: Graph, node) -> str:
    try:
        return node.n3(g.namespace_manager)
    except Exception:  # noqa: BLE001
        return str(node)


def subclass_closure(g: Graph) -> set:
    """Classes treated as ODRL policy classes: declared rdfs:subClassOf edges only."""
    classes = set(POLICY_CLASSES)
    changed = True
    while changed:
        changed = False
        for s, _, o in g.triples((None, RDFS.subClassOf, None)):
            if o in classes and s not in classes:
                classes.add(s)
                changed = True
    return classes


def members(g: Graph, node) -> list:
    """Objects of a logical connective: an RDF list or repeated values."""
    if (node, RDF.first, None) in g or node == RDF.nil:
        return list(Collection(g, node))
    return [node]


DURATION_RE = re.compile(
    r"^-?P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)W)?(?:(\d+)D)?"
    r"(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$"
)
DATETIME_RE = re.compile(
    r"^-?\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$"
)


def single_kind_duration(lexical: str) -> bool:
    """A duration of one kind only: year-month, or day-time (due2-profiles.md §4)."""
    m = DURATION_RE.match(lexical)
    if not m:
        return False
    ym = bool(m.group(1) or m.group(2))
    dt = bool(m.group(3) or m.group(4) or m.group(5) or m.group(6) or m.group(7))
    return ym != dt  # exactly one kind present


def check_duty_timing(g: Graph, rule, kind, r: Report) -> None:
    """dprod:deadline and dprod:recurrence — duty timing (due2-profiles.md §7)."""
    dl = list(g.objects(rule, DPROD.deadline))
    rc = list(g.objects(rule, DPROD.recurrence))
    if kind != ODRL.Duty and (dl or rc):
        r.err(f"{q(g, rule)}: dprod:deadline and dprod:recurrence are duty terms, "
              f"not terms of {q(g, kind)}")
        return
    if len(dl) > 1:
        r.err(f"{q(g, rule)}: more than one dprod:deadline")
    if len(rc) > 1:
        r.err(f"{q(g, rule)}: more than one dprod:recurrence")
    for v in dl:
        if not isinstance(v, Literal) or v.datatype not in (XSD.dateTime, XSD.duration):
            r.err(f"{q(g, rule)}: dprod:deadline must be an xsd:dateTime (absolute) or "
                  f"xsd:duration (relative to activation), got {v!r}")
        elif v.datatype == XSD.duration and not single_kind_duration(str(v)):
            r.err(f"{q(g, rule)}: duration deadline {v!r} mixes year-month and "
                  f"day-time components (due2-profiles.md §4)")
    for v in rc:
        if not isinstance(v, Literal) or "FREQ=" not in str(v):
            r.err(f"{q(g, rule)}: dprod:recurrence must be an RFC 5545 RRULE string "
                  f"containing FREQ=, got {v!r}")


class Bindings:
    """Operand bindings by precedence: policy graph > selected profiles > core."""

    def __init__(self, layers: list[Graph]):
        self.layers = layers

    def lookup(self, op) -> tuple[list, list, Graph | None]:
        for g in self.layers:
            src = list(g.objects(op, DPROD.operandSource))
            prop = list(g.objects(op, DPROD.operandProperty))
            if src or prop:
                return src, prop, g
        return [], [], None

    def attr(self, op, pred) -> list:
        for g in self.layers:
            vals = list(g.objects(op, pred))
            if vals:
                return vals
        return []


def check_constraint(g: Graph, c, b: Bindings, r: Report, used: dict, in_duty: bool = False) -> None:
    for pred, label in REJECTED.items():
        if (c, pred, None) in g:
            r.err(f"{q(g, c)}: {label} is not admitted")
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
        r.err(f"{q(g, c)}: constraint needs exactly one leftOperand and one operator")
        return
    op, operator = left[0], ops[0]
    if operator not in OPERATORS:
        r.err(f"{q(g, c)}: operator {q(g, operator)} is not in the core registry")
    if not rights:
        r.err(f"{q(g, c)}: no rightOperand")
    src, prop, _ = b.lookup(op)
    if len(src) != 1 or len(prop) != 1:
        r.err(f"{q(g, c)}: left operand {q(g, op)} has no single binding (UnboundLeftOperand)")
        return
    if src[0] not in SOURCES:
        r.err(f"{q(g, c)}: operand source {q(g, src[0])} is not one of the closed sources")
    if src[0] == DUE2.witnessSource and not in_duty:
        r.err(f"{q(g, c)}: witness-source operand {q(g, op)} outside a duty (WitnessOutsideDuty)")
    if not isinstance(prop[0], URIRef):
        r.err(f"{q(g, c)}: operandProperty of {q(g, op)} is not an IRI")
    if src[0] == DPROD.contextSource and prop[0] not in CONTEXT_PROPS:
        r.err(f"{q(g, c)}: context property {q(g, prop[0])} is not a built-in")
    card = b.attr(op, DUE2.cardinality)
    used[op] = (src[0], prop[0], card[0] if card else DUE2.one)
    allowed = b.attr(op, DUE2.allowedOperator)
    if allowed and operator not in allowed:
        r.err(f"{q(g, c)}: operator {q(g, operator)} not allowed for {q(g, op)} (OperatorTypeMismatch)")
    rng = b.attr(op, RDFS.range)
    for ro in rights:
        for v in members(g, ro):
            if isinstance(v, Literal):
                if v.datatype in FLOATING:
                    r.err(f"{q(g, c)}: floating-point right operand is not admitted")
                if rng and isinstance(rng[0], URIRef) and str(rng[0]).startswith(str(XSD)):
                    want, have = rng[0], v.datatype or XSD.string
                    if want != have and not (want in NUMERIC and have in NUMERIC):
                        r.err(f"{q(g, c)}: right operand {v!r} does not conform to range {q(g, want)}")


def witness_kinds(g: Graph, c, b: Bindings) -> set:
    """'witness' if the subtree reads a witness-dependent operand, 'guard' otherwise."""
    conns = [p for p in CONNECTIVES if (c, p, None) in g]
    if conns:
        kinds: set = set()
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


def check_mixed(g: Graph, c, b: Bindings, r: Report) -> None:
    """Disjunction, xone, or negation mixing guards and witness conditions (workflows §5.2)."""
    for p in (ODRL["or"], ODRL.xone, DPROD["not"]):
        for o in g.objects(c, p):
            ms = members(g, o)
            kinds: set = set()
            for m in ms:
                kinds |= witness_kinds(g, m, b)
            if len(kinds) == 2:
                r.err(f"{q(g, c)}: {q(g, p)} mixes a guard and a witness condition (MixedDutyConstraint)")
            for m in ms:
                check_mixed(g, m, b, r)
    for o in g.objects(c, ODRL["and"]):
        for m in members(g, o):
            check_mixed(g, m, b, r)


def check_rule(g: Graph, rule, kind, policy, b: Bindings, r: Report, used: dict,
               seen: set, path: list, named: bool) -> None:
    if rule in path:
        r.err(f"rule reference cycle: {' -> '.join(q(g, x) for x in path + [rule])}")
        return
    if rule in seen:
        return
    seen.add(rule)
    if isinstance(rule, BNode) and named:
        r.warn(f"anonymous {q(g, kind)} under {q(g, policy)}: corpus cases name every rule")
    for pred, label in REJECTED.items():
        if (rule, pred, None) in g:
            r.err(f"{q(g, rule)}: {label} is not admitted")
    check_duty_timing(g, rule, kind, r)
    actions = list(g.objects(rule, ODRL.action)) or list(g.objects(policy, ODRL.action))
    if not actions and not path:
        r.err(f"{q(g, rule)}: no action, at rule or policy level")
    if not list(g.objects(rule, ODRL.action)) and path:
        r.err(f"{q(g, rule)}: nested duty has no action")
    targets = list(g.objects(rule, ODRL.target))
    if not targets and not path:
        targets = list(g.objects(policy, ODRL.target))
    if kind in (ODRL.Permission, ODRL.Prohibition) and not targets:
        r.err(f"{q(g, rule)}: {q(g, kind)} has no target, at rule or policy level")
    if targets and (rule, ODRL.output, None) in g:
        r.err(f"{q(g, rule)}: both target and output")
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
            check_rule(g, d, ODRL.Duty, policy, b, r, used, seen, path + [rule], named)


def ns_terms(g: Graph, ns: str) -> int:
    n = 0
    for _, p, o in g:
        if str(p).startswith(ns):
            n += 1
        elif isinstance(o, URIRef) and str(o).startswith(ns):
            n += 1
    return n


ASSET_PARTY_EDGES = (ODRL.target, ODRL.output, ODRL.assignee, ODRL.assigner,
                     ODRL.informedParty, ODRL.compensatedParty, ODRL.attributedParty,
                     ODRL.consentingParty, ODRL.contractingParty, ODRL.trackingParty)


def asset_party_nodes(g: Graph) -> set:
    """Every node in an asset or party position, plus every declared collection."""
    nodes = {o for e in ASSET_PARTY_EDGES for o in g.objects(None, e)}
    nodes |= set(g.subjects(RDF.type, ODRL.AssetCollection))
    nodes |= set(g.subjects(RDF.type, ODRL.PartyCollection))
    return nodes


def check_policy(g: Graph, policy, b: Bindings, profiles_graph: Graph, r: Report,
                 named: bool) -> dict:
    used: dict = {}
    declared = {str(p) for p in g.objects(policy, ODRL.profile)}
    for ns, label in NAMESPACED_PROFILES.items():
        if ns_terms(g, ns) and ns not in declared:
            r.err(f"{q(g, policy)}: uses {label} terms but declares no "
                  f"odrl:profile <{ns}>; normalisation will not select its module")
    if isinstance(policy, BNode) and len(list(g.objects(policy, ODRL.uid))) != 1:
        r.err(f"{q(g, policy)}: policy has no identity (IRI or exactly one odrl:uid)")
    for pred, label in REJECTED.items():
        if (policy, pred, None) in g:
            r.err(f"{q(g, policy)}: {label} is not admitted")
    for term in (DPROD.deadline, DPROD.recurrence):
        if (policy, term, None) in g:
            r.err(f"{q(g, policy)}: {q(g, term)} on a Policy is not an extension point (duties only)")
    # Asset and party nodes are where odrl:source and collection refinements
    # occur (IM 2.5.5-2.5.6); due2-profiles.md 8.1 rejects both. Rule and
    # constraint nodes are checked in check_rule and check_constraint.
    for node in sorted(asset_party_nodes(g), key=str):
        if (node, ODRL.source, None) in g:
            r.err(f"{q(g, node)}: collection source (odrl:source) is not admitted")
        if (node, ODRL.refinement, None) in g:
            r.err(f"{q(g, node)}: collection refinement is not admitted")
    conflicts = list(g.objects(policy, ODRL.conflict))
    if len(conflicts) > 1:
        r.err(f"{q(g, policy)}: more than one odrl:conflict")
    elif conflicts and conflicts[0] not in CONFLICT_VALUES:
        r.err(f"{q(g, policy)}: odrl:conflict {q(g, conflicts[0])} is not prohibit, perm, or invalid")
    if (policy, RDF.type, ODRL.Request) in g:
        r.err(f"{q(g, policy)}: odrl:Request is an evaluation input, not a policy")
    rules = [(rule, kind) for edge, kind in RULE_EDGES.items() for rule in g.objects(policy, edge)]
    if not rules:
        r.err(f"{q(g, policy)}: no permission, prohibition, or obligation")
    seen: set = set()
    for rule, kind in rules:
        check_rule(g, rule, kind, policy, b, r, used, seen, [], named)
    for c in g.objects(policy, ODRL.constraint):
        check_constraint(g, c, b, r, used)
    return used


def selected_profiles(g: Graph, policy, explicit: list[str]) -> list[str]:
    sel = [ALIASES.get(p, p) for p in explicit]
    sel += [str(p) for p in g.objects(policy, ODRL.profile)]
    unknown = [p for p in sel if p not in MODULES]
    return [p for p in dict.fromkeys(sel) if p in MODULES] + unknown


def check_file(path: Path, explicit: list[str], named: bool) -> list[tuple[Report, dict, Graph]]:
    g = Graph()
    g.parse(path)
    pre = Graph()
    for p in CORE:
        pre.parse(p)
    for files in MODULES.values():
        for f in files:
            pre.parse(f)
    classes = subclass_closure(pre + g)
    policies = sorted({s for s, _, o in g.triples((None, RDF.type, None)) if o in classes},
                      key=str)
    out = []
    if not policies:
        r = Report(str(path))
        r.err("no policy node (odrl:Policy, Set, Offer, Agreement, or a declared subclass)")
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


def expand(curie: str, prefixes: dict) -> str:
    if curie.startswith(("http://", "https://", "urn:")):
        return curie
    pfx, _, local = curie.partition(":")
    if pfx in prefixes:
        return prefixes[pfx] + local
    return curie


def check_case(case_dir: Path) -> list[Report]:
    policy_path = case_dir / "policy.ttl"
    case_path = case_dir / "case.json"
    reports = []
    if not policy_path.exists():
        r = Report(case_dir.name)
        r.err("policy.ttl missing")
        return [r]
    results = check_file(policy_path, [], named=True)
    if len(results) != 1:
        r = Report(case_dir.name)
        r.err(f"policy.ttl must contain exactly one policy, found {len(results)}")
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
    for key in ("case", "source", "classification", "scenarios"):
        if key not in case:
            r.err(f"case.json: missing '{key}'")
    if case.get("classification") not in CLASSIFICATIONS:
        r.err(f"case.json: classification must be one of {sorted(CLASSIFICATIONS)}")
    if case.get("classification") in ("odrl-profile", "partial", "not-expressible") \
            and not case.get("needs"):
        r.err("case.json: 'needs' must list the profile terms or missing constructs")
    prefixes = {"odrl": str(ODRL), "dprod": str(DPROD), "due2": str(DUE2), "xsd": str(XSD)}
    prefixes.update(case.get("prefixes", {}))
    request_props = {str(p) for s, p, _ in used.values() if s == DPROD.requestSource}
    state_props = {str(p) for s, p, _ in used.values() if s == DPROD.stateSource}
    witness_props = {str(p) for s, p, _ in used.values() if s == DUE2.witnessSource}
    set_props = {str(p) for s, p, c in used.values() if c == DUE2.set}
    rules = {str(x) for x in g.subjects(RDF.type, None)}
    scenarios = case.get("scenarios", [])
    if not scenarios:
        r.err("case.json: no scenarios")
    for i, sc in enumerate(scenarios):
        tag = f"scenario {i + 1} ({sc.get('name', '?')})"
        req = sc.get("request", {})
        for k in ("action", "target", "at"):
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
                r.err(f"{tag}: obligation status {ob.get('status')!r} is not one of fulfilled, outstanding, violated, unknown")
            if ob.get("status") == "violated" and not has_deadline:
                r.err(f"{tag}: obligation {ob.get('duty')} is violated, but the policy has no "
                      f"dprod:deadline — without one, a duty is never violated")
            if "instance" in ob and not DATETIME_RE.match(str(ob["instance"])):
                r.err(f"{tag}: obligation instance {ob['instance']!r} is not an xsd:dateTime instant")
        if exp.get("verdict") == "Pending" and not exp.get("frontier"):
            r.err(f"{tag}: Pending needs a frontier")
    return reports


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
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
        errors += len(r.errors)
        if args.quiet and not r.errors:
            continue
        status = "FAIL" if r.errors else ("warn" if r.warnings else "ok")
        print(f"{status:4}  {r.name}")
        for m in r.errors:
            print(f"      error: {m}")
        for m in r.warnings:
            print(f"      warn:  {m}")
    print(f"\n{len(reports)} checked, {sum(1 for r in reports if r.errors)} failing, {errors} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
