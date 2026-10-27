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
import logging
import re
import sys
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import rdflib
from harness.xsd_time import TIMEZONE, date_ok, datetime_ok, duration_kinds, instant_ok
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS, XSD
from rdflib.term import Node

# Literals keep the lexical form as written, for every graph this process parses: the flag is
# global. rdflib's default normalisation is lossy, and check_literal must see what it drops:
# "2026-12-31+01:00"^^xsd:date would reach it as "2026-12-31" and pass.
rdflib.NORMALIZE_LITERALS = False
# rdflib logs a traceback for each literal whose lexical form names no value, such as
# "2026-02-30T12:00:00Z"^^xsd:dateTime; names_value reports such a literal as a diagnostic.
logging.getLogger("rdflib.term").setLevel(logging.ERROR)

ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
DPROD = Namespace("https://ekgf.org/dprod/spec/develop/")
DUE2 = Namespace("https://w3id.org/due2/profile#")

ROOT = Path(__file__).resolve().parent.parent
PROFILES = ROOT / "profiles"
CORE = [PROFILES / "due2-core.ttl", PROFILES / "odrl-actions.ttl"]
W3C_VOCABULARY = PROFILES / "vendor" / "w3c" / "ODRL22.ttl"
MODULES = {
    str(DPROD): [*sorted((PROFILES / "vendor" / "dprod").glob("*.ttl")), PROFILES / "dprod.ttl"],
    str(DUE2): [],  # the baseline, always loaded: selecting it adds no module (decisions/0014)
}
ALIASES = {"dprod": str(DPROD), "due2": str(DUE2)}
# IM 2.1: a policy uses only Core terms, or declares the profiles whose terms
# it uses. Normalisation selects a profile's binding module by odrl:profile
# (normalisation spec 3), so an undeclared namespace is a W1 input error.
NAMESPACED_PROFILES = {str(DPROD): "DPROD Contracts", str(DUE2): "due2 core"}
# Where a policy names vocabulary; each term there must be defined by the odrl:
# namespace of the official vocabulary, a selected module, or the policy itself
# (decisions/0020). odrl:unit is not among them: a unit is a value's measure.
VOCABULARY_POSITIONS = (
    ODRL.action,
    ODRL.leftOperand,
    ODRL.operator,
    ODRL.function,
    ODRL.relation,
    ODRL.conflict,
)

POLICY_CLASSES = {ODRL.Policy, ODRL.Set, ODRL.Offer, ODRL.Agreement}
RULE_EDGES = {
    ODRL.permission: ODRL.Permission,
    ODRL.prohibition: ODRL.Prohibition,
    ODRL.obligation: ODRL.Duty,
}
NESTED_EDGES = (ODRL.duty, ODRL.consequence, ODRL.remedy)
RULE_CLASSES = (ODRL.Permission, ODRL.Prohibition, ODRL.Duty)
# Each Rule edge's subject and object class, from the edge's rdfs:domain and
# rdfs:range (Vocabulary 3.9.2, 3.10.2, 3.13.2-3.13.5); None is the Policy.
EDGE_PLACES: dict[Node, tuple[Node | None, Node]] = {
    ODRL.permission: (None, ODRL.Permission),
    ODRL.prohibition: (None, ODRL.Prohibition),
    ODRL.obligation: (None, ODRL.Duty),
    ODRL.duty: (ODRL.Permission, ODRL.Duty),
    ODRL.remedy: (ODRL.Prohibition, ODRL.Duty),
    ODRL.consequence: (ODRL.Duty, ODRL.Duty),
}
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
# The operators a concept-scheme operand admits (due2-profiles.md §4, decisions/0015 #8).
CONCEPT_OPERATORS = {ODRL.eq, ODRL.neq, ODRL.isAnyOf, ODRL.isNoneOf}
# The operators whose left is one value; a set-valued operand takes isAllOf, isPartOf,
# or hasPart (due2-profiles.md 4, decisions/0025).
ONE_VALUE = {
    ODRL.eq,
    ODRL.neq,
    ODRL.lt,
    ODRL.lteq,
    ODRL.gt,
    ODRL.gteq,
    ODRL.isAnyOf,
    ODRL.isNoneOf,
    ODRL.isA,
}
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
    XSD[t]
    for t in (
        *("decimal", "float", "double", "integer", "nonPositiveInteger", "negativeInteger"),
        *("long", "int", "short", "byte", "nonNegativeInteger", "positiveInteger"),
        *("unsignedLong", "unsignedInt", "unsignedShort", "unsignedByte"),
    )
}  # one kind (due2-profiles.md §3 Kinds)
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
        elif not names_value(v):
            r.diag(
                "InvalidTiming", f"{q(g, rule)}: dprod:deadline {str(v)!r} names no {xsd_name(v)}"
            )
        elif v.datatype == XSD.dateTime and not TIMEZONE.search(str(v)):
            r.diag(
                "InvalidTiming",
                f"{q(g, rule)}: dprod:deadline {v!r} has no timezone (decisions/0024)",
            )
        elif v.datatype == XSD.duration and len(duration_kinds(str(v)) or ()) > 1:
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


WHERE_ATTRS = (DPROD.operandSource, DPROD.operandProperty)
TYPE_ATTRS = (RDFS.range, DUE2.cardinality, DUE2.allowedOperator)
DEFAULTS: dict[Node, frozenset[Node]] = {DUE2.cardinality: frozenset({DUE2.one})}
# Derived XSD datatypes, by the primitive whose kind they have (XSD 1.1 Part 2 §3.3-3.4).
DERIVED: dict[Node, Node] = {
    **{
        XSD[t]: XSD.string
        for t in (
            *("normalizedString", "token", "language", "Name", "NCName", "NMTOKEN"),
            *("ID", "IDREF", "ENTITY"),
        )
    },
    XSD.dateTimeStamp: XSD.dateTime,
    XSD.dayTimeDuration: XSD.duration,
    XSD.yearMonthDuration: XSD.duration,
}
RDF_DATATYPES = {RDF.langString}
LITERAL = "literal"  # rdfs:Literal's kind: it admits a literal of any kind


def datatype_kind(dt: Node) -> str:
    """A datatype's kind (due2-profiles.md §3 Kinds, decisions/0014 #4)."""
    if dt in NUMERIC:
        return "numeric"
    return str(DERIVED.get(dt, dt))


def kinds_apart(k: str, k2: str) -> bool:
    """Whether no value has both kinds. `rdfs:Literal`'s kind meets every literal
    kind, but never the IRI kind."""
    if LITERAL in (k, k2):
        return "IRI" in (k, k2)
    return k != k2


def value_kind(v: Node) -> str | None:
    """A right operand's kind; None for a node that is neither an IRI nor a literal."""
    if isinstance(v, URIRef):
        return "IRI"
    if isinstance(v, Literal):
        return datatype_kind(v.datatype or (RDF.langString if v.language else XSD.string))
    return None


@dataclass
class Binding:
    """One left operand's binding, resolved through the layers. An empty `allowed`
    is the default: every core operator."""

    source: frozenset[Node]
    prop: frozenset[Node]
    range: frozenset[Node]
    card: Node
    allowed: frozenset[Node]


class Bindings:
    """Operand bindings resolved through the layers of due2-profiles.md §2
    (decisions/0014 #1-#3): the policy graph, the selected profile modules, and
    the baseline, from highest to lowest.

    The modules are one layer without order: each is kept as its own graph, so
    that two which state an attribute of one operand differently are a
    `ConflictingProfileDeclaration`, not a merge. The source and property come
    from the highest layer that states them. The range, cardinality, and allowed
    operators come from the lowest layer that declares the operand, its owner,
    and a higher layer that restates one with another value is a
    `RetypedOperand`. An omitted allowed-operator list defaults to every core
    operator; the checker does not narrow it by operator signatures, so any
    restatement of an omitted list counts as a retyping.

    `resolve` reports each operand's binding diagnostics to `r`, once per policy,
    whichever check asks first.
    """

    def __init__(self, policy: Graph, modules: list[Graph], core: Graph, r: Report) -> None:
        self.g, self.r = policy, r
        self.layers: list[list[Graph]] = [[policy], modules, [core]]
        self.all = [g for layer in self.layers for g in layer]
        self.cache: dict[Node, Binding | None] = {}
        self.conflicted: set[Node] = set()  # operands whose modules disagree; not unbound

    def stated(self, layer: list[Graph], op: Node, pred: Node) -> frozenset[Node]:
        return frozenset(o for g in layer for o in g.objects(op, pred))

    def resolve(self, op: Node) -> Binding | None:
        """The operand's binding, or None when it has no single source and property,
        or when its modules conflict (then `op` is in `conflicted`)."""
        if op not in self.cache:
            self.cache[op] = self._resolve(self.g, op, self.r)
        return self.cache[op]

    def _resolve(self, g: Graph, op: Node, r: Report) -> Binding | None:
        conflicted = False
        for pred in (*WHERE_ATTRS, *TYPE_ATTRS):
            seen = {v for m in self.layers[1] if (v := self.stated([m], op, pred))}
            if len(seen) > 1:
                conflicted = True
                r.diag(
                    "ConflictingProfileDeclaration",
                    f"{q(g, op)}: two selected profile modules state {q(g, pred)} differently "
                    f"(due2-profiles.md 2, decisions/0014 #3)",
                )
        if conflicted:
            self.conflicted.add(op)
            return None
        declaring = [
            lay
            for lay in self.layers
            if any(self.stated(lay, op, p) for p in (*WHERE_ATTRS, *TYPE_ATTRS))
        ]
        none: frozenset[Node] = frozenset()
        where = [
            next((v for lay in self.layers if (v := self.stated(lay, op, p))), none)
            for p in WHERE_ATTRS
        ]
        if not declaring or any(len(v) != 1 for v in where):
            return None
        owner = declaring[-1]
        typed: dict[Node, frozenset[Node]] = {}
        for pred in TYPE_ATTRS:
            typed[pred] = self.stated(owner, op, pred) or DEFAULTS.get(pred, none)
            for lay in self.layers[: self.layers.index(owner)]:
                v = self.stated(lay, op, pred)
                if v and v != typed[pred]:
                    r.diag(
                        "RetypedOperand",
                        f"{q(g, op)}: {q(g, pred)} restated above the layer that owns "
                        f"the operand's type (due2-profiles.md 2, decisions/0014 #2)",
                    )
        (card,) = typed[DUE2.cardinality] if len(typed[DUE2.cardinality]) == 1 else (DUE2.one,)
        b = Binding(where[0], where[1], typed[RDFS.range], card, typed[DUE2.allowedOperator])
        self._check_range(g, op, b, r)
        return b

    def schemes(self, op: Node) -> frozenset[Node]:
        """The operand's concept schemes: the union over every layer (decisions/0015 #6)."""
        return frozenset(s for lg in self.all for s in lg.objects(op, DUE2.conceptScheme))

    def in_scheme(self, v: Node, schemes: frozenset[Node]) -> bool:
        """Whether the policy or a module declares concept `v` a member of one of
        `schemes`: `skos:inScheme`, its sub-property `skos:topConceptOf`, or the
        inverse `skos:hasTopConcept` (SKOS Reference S7, S8; decisions/0015 #8).
        Membership is not inherited along `skos:broader` (SKOS Reference 4.6)."""
        return any(
            (v, p, s) in lg
            for lg in self.all
            for s in schemes
            for p in (SKOS.inScheme, SKOS.topConceptOf)
        ) or any((s, SKOS.hasTopConcept, v) in lg for lg in self.all for s in schemes)

    def range_kind(self, rng: Node) -> str | None:
        """A range's kind (decisions/0014 #4); None when it has none to check: a
        blank-node range, or `rdfs:Resource`, which admits every value."""
        if not isinstance(rng, URIRef) or rng == RDFS.Resource:
            return None
        if rng == RDFS.Literal:
            return LITERAL
        if str(rng).startswith(str(XSD)) or rng in RDF_DATATYPES:
            return datatype_kind(rng)
        if any((rng, RDF.type, RDFS.Datatype) in lg for lg in self.all):
            return str(rng)
        return "IRI"

    def _check_range(self, g: Graph, op: Node, b: Binding, r: Report) -> None:
        """`OperandRangeMismatch` (decisions/0014 #5). An operand that reads itself,
        such as `odrl:payAmount`, has its own range as the property's, and a
        restatement of it is already a `RetypedOperand`."""
        (prop,) = b.prop
        if prop == op:
            return
        mine = {k for v in b.range if (k := self.range_kind(v))}
        theirs = {
            k for lg in self.all for v in lg.objects(prop, RDFS.range) if (k := self.range_kind(v))
        }
        if any(kinds_apart(k, k2) for k in mine for k2 in theirs):
            r.diag(
                "OperandRangeMismatch",
                f"{q(g, op)}: its range is of kind {sorted(mine)}, but {q(g, prop)} "
                f"has range kind {sorted(theirs)} (due2-profiles.md 3, decisions/0014 #5)",
            )


def leaf_key(g: Graph, c: Node) -> tuple[frozenset[Node], ...] | None:
    """What a leaf constraint states, with values as written; None for a logical constraint."""
    if any((c, p, None) in g for p in CONNECTIVES):
        return None
    rights = frozenset(m for ro in g.objects(c, ODRL.rightOperand) for m in members(g, ro))
    return (
        frozenset(g.objects(c, ODRL.leftOperand)),
        frozenset(g.objects(c, ODRL.operator)),
        frozenset(g.objects(c, ODRL.unit)),
        rights,
    )


def check_repeats(g: Graph, c: Node, p: Node, r: Report) -> None:
    """A list that names a node twice, or an odrl:xone that states one leaf twice (decisions/0022)."""
    ms = [m for o in g.objects(c, p) for m in members(g, o)]
    if len(set(ms)) < len(ms):
        r.diag(
            "MalformedConstraint",
            f"{q(g, c)}: {q(g, p)} names a member twice (due2-profiles.md 5, decisions/0022)",
        )
    keys = [k for m in set(ms) if (k := leaf_key(g, m)) is not None]
    if p == ODRL.xone and len(set(keys)) < len(keys):
        r.diag(
            "MalformedConstraint",
            f"{q(g, c)}: odrl:xone states one leaf twice (due2-profiles.md 5, decisions/0022)",
        )


def operands(g: Graph, c: Node) -> list[Node]:
    """The members of every connective on `c`, a member listed twice twice; none for a leaf
    constraint."""
    return [m for p in CONNECTIVES for o in g.objects(c, p) for m in members(g, o)]


def constraint_tree(g: Graph, root: Node, r: Report) -> list[Node]:
    """`root` and every node its connectives reach, each once, members before the logical
    constraint that lists them; empty, with `MalformedConstraint`, when the members form a
    cycle (due2-profiles.md §5). An empty tree gets no further checks, so a cycle is the one
    diagnostic its constraint gets.

    The walk keeps its own stack, so neither a cycle nor deep nesting meets Python's recursion
    limit. A node shared by two logical constraints is listed once and is no cycle: a cycle
    is a member that is still on the path from `root`.
    """
    order: list[Node] = []
    done: set[Node] = set()
    on_path = {root}
    stack = [(root, iter(operands(g, root)))]
    while stack:
        c, todo = stack[-1]
        m = next(todo, None)
        if m is None:
            stack.pop()
            on_path.discard(c)
            done.add(c)
            order.append(c)
        elif m in done:
            continue
        elif m in on_path:
            path = [n for n, _ in stack]
            cycle = [*path[path.index(m) :], m]
            r.diag(
                "MalformedConstraint",
                f"logical constraint cycle: {' -> '.join(q(g, n) for n in cycle)} "
                f"(due2-profiles.md 5)",
            )
            return []
        else:
            on_path.add(m)
            stack.append((m, iter(operands(g, m))))
    return order


def check_constraint(
    g: Graph, c: Node, b: Bindings, r: Report, used: Used, in_duty: bool = False
) -> None:
    """The checks on one node of a constraint tree. It does not descend into the members:
    call it on every node `constraint_tree` returns."""
    for pred, label in REJECTED.items():
        if (c, pred, None) in g:
            r.diag(
                REJECTED_CODE.get(pred, "UnsupportedConstruct"),
                f"{q(g, c)}: {label} is not admitted",
            )
    conns = [p for p in CONNECTIVES if (c, p, None) in g]
    if len(conns) + ((c, ODRL.andSequence, None) in g) > 1:
        # IM 2.5.2: one operand property; two would leave the connective unstated.
        r.diag("MalformedConstraint", f"{q(g, c)}: more than one operand property")
    if conns:
        for p in conns:
            for o in g.objects(c, p):
                if o == RDF.nil:
                    r.diag(
                        "MalformedConstraint",
                        f"{q(g, c)}: {q(g, p)} over the empty list "
                        f"(due2-profiles.md 5, decisions/0017)",
                    )
            check_repeats(g, c, p, r)
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
    if operator in SET_BASED and RDF.nil in rights:
        r.diag(
            "MalformedConstraint",
            f"{q(g, c)}: the empty list as the right operand of {q(g, operator)} "
            f"(due2-profiles.md 4, decisions/0013 amendment)",
        )
    if operator in CONTESTED and sum(len(members(g, ro)) for ro in rights) > 1:
        r.diag(
            "ContestedOperatorReading",
            f"{q(g, c)}: {q(g, operator)} with a list right operand "
            f"is read after Salas-Pareti (due2-profiles.md 4, decisions/0005)",
        )
    bnd = b.resolve(op)
    if bnd is None:
        if op not in b.conflicted:
            r.diag(
                "UnboundLeftOperand", f"{q(g, c)}: left operand {q(g, op)} has no single binding"
            )
        return
    (src,), (prop,), card = bnd.source, bnd.prop, bnd.card
    if src not in SOURCES:
        r.diag(
            "InvalidBinding",
            f"{q(g, c)}: operand source {q(g, src)} is not one of the closed sources",
        )
    if src == DUE2.witnessSource and not in_duty:
        r.diag("WitnessOutsideDuty", f"{q(g, c)}: witness-source operand {q(g, op)} outside a duty")
    if not isinstance(prop, URIRef):
        r.diag("InvalidBinding", f"{q(g, c)}: operandProperty of {q(g, op)} is not an IRI")
    if src == DPROD.contextSource and prop not in CONTEXT_PROPS:
        r.diag("InvalidBinding", f"{q(g, c)}: context property {q(g, prop)} is not a built-in")
    used[op] = (src, prop, card)
    if card == DUE2.set and operator in (ODRL.isPartOf, ODRL.hasPart):
        r.diag(
            "ContestedOperatorReading",
            f"{q(g, c)}: {q(g, operator)} over a set-valued operand "
            f"is read after Salas-Pareti (due2-profiles.md 4, decisions/0005)",
        )
    elif operator in ONE_VALUE and card == DUE2.set:
        r.diag(
            "OperatorTypeMismatch",
            f"{q(g, c)}: {q(g, operator)} takes one left value, and {q(g, op)} is set-valued "
            f"(due2-profiles.md 4, decisions/0025)",
        )
    if bnd.allowed and operator not in bnd.allowed:
        r.diag(
            "OperatorTypeMismatch",
            f"{q(g, c)}: operator {q(g, operator)} not allowed for {q(g, op)}",
        )
    check_concepts(g, c, op, operator, rights, bnd, b, r)
    # The right operand's kind against the range's (due2-profiles.md 3 Kinds); a range
    # without a kind (a blank-node union, rdfs:Resource) admits any value, and
    # rdfs:Literal any literal.
    want = {k for v in bnd.range if (k := b.range_kind(v))}
    for ro in rights:
        for v in members(g, ro):
            if isinstance(v, Literal) and v.datatype in FLOATING:
                r.diag(
                    "FloatingPointOperand",
                    f"{q(g, c)}: floating-point right operand is not admitted",
                )
            check_literal(g, c, v, r)
            have = value_kind(v)
            if LITERAL in want and isinstance(v, Literal):
                continue
            if want and have and have not in want:
                r.diag(
                    "OperatorTypeMismatch",
                    f"{q(g, c)}: right operand {q(g, v)} is of kind {have}, "
                    f"not the range's {sorted(want)}",
                )


def xsd_name(lit: Literal) -> str:
    """The datatype of `lit` as `xsd:name`, for messages."""
    return str(lit.datatype).replace(str(XSD), "xsd:")


def names_value(lit: Literal) -> bool:
    """Whether a dateTime, date, or duration literal names a value of its datatype
    (`harness.xsd_time`). A literal of any other datatype is not checked, so True."""
    lex = str(lit)
    if lit.datatype == XSD.dateTime:
        return datetime_ok(lex)
    if lit.datatype == XSD.date:
        return date_ok(lex)
    if lit.datatype == XSD.duration:
        return duration_kinds(lex) is not None
    return True


def check_literal(g: Graph, c: Node, v: Node, r: Report) -> None:
    """Reports a temporal right operand `v` of constraint `c` that breaks a lexical rule of
    due2-profiles.md §4 (decisions/0024): it names a value of its datatype (`harness.xsd_time`),
    a dateTime has a timezone, a date has none, and a duration is single-kind. An IRI, or a
    literal of another datatype, is not checked here."""
    if not isinstance(v, Literal):
        return
    lex = str(v)
    if not names_value(v):
        r.diag("OperatorTypeMismatch", f"{q(g, c)}: right operand {lex!r} names no {xsd_name(v)}")
    elif v.datatype == XSD.dateTime and not TIMEZONE.search(lex):
        r.diag("OperatorTypeMismatch", f"{q(g, c)}: dateTime right operand {lex!r} has no timezone")
    elif v.datatype == XSD.date and TIMEZONE.search(lex):
        r.diag("OperatorTypeMismatch", f"{q(g, c)}: date right operand {lex!r} has a timezone")
    elif v.datatype == XSD.duration and len(duration_kinds(lex) or ()) > 1:
        r.diag(
            "MixedDuration",
            f"{q(g, c)}: duration right operand {lex!r} mixes year-month and day-time components",
        )


def check_concepts(
    g: Graph,
    c: Node,
    op: Node,
    operator: Node,
    rights: list[Node],
    bnd: Binding,
    b: Bindings,
    r: Report,
) -> None:
    """The three checks on a concept-scheme operand (due2-profiles.md 4, decisions/0015 #8).
    A range of kind IRI or `rdfs:Literal`, or with no kind, is not a datatype."""
    schemes = b.schemes(op)
    if not schemes:
        return
    if any(k not in (None, "IRI", LITERAL) for v in bnd.range for k in (b.range_kind(v),)):
        r.diag(
            "InvalidBinding",
            f"{q(g, c)}: {q(g, op)} names a concept scheme, but its range is a datatype "
            f"(due2-profiles.md 4, decisions/0015 #8)",
        )
    if operator not in CONCEPT_OPERATORS:
        r.diag(
            "OperatorTypeMismatch",
            f"{q(g, c)}: {q(g, operator)} on {q(g, op)}, which names a concept scheme; "
            f"only eq, neq, isAnyOf, and isNoneOf compare concepts (decisions/0015 #8)",
        )
    for ro in rights:
        for v in members(g, ro):
            if isinstance(v, URIRef) and not b.in_scheme(v, schemes):
                r.diag(
                    "OperatorTypeMismatch",
                    f"{q(g, c)}: right operand {q(g, v)} is in none of {q(g, op)}'s concept "
                    f"schemes (decisions/0015 #8)",
                )


def leaf_kinds(g: Graph, c: Node, b: Bindings) -> set[str]:
    """'witness' if leaf `c` reads a witness-dependent operand, 'guard' otherwise; empty when
    it has no single left operand."""
    left = list(g.objects(c, ODRL.leftOperand))
    if len(left) != 1:
        return set()
    bnd = b.resolve(left[0])
    if bnd and (DUE2.witnessSource in bnd.source or DUE2.actionTime in bnd.prop):
        return {"witness"}
    return {"guard"}


def check_mixed(g: Graph, tree: list[Node], b: Bindings, r: Report) -> None:
    """Disjunction, xone, or negation mixing guards and witness conditions
    (due2-workflows.md §5.2).

    `tree` comes from `constraint_tree`, members first, so a logical constraint's kinds are
    the union of its members' kinds, already computed.
    """
    kinds: dict[Node, set[str]] = {}
    for c in tree:
        # `set[str]()` types the union, and is its value over no members (`odrl:and ()`).
        if any((c, p, None) in g for p in CONNECTIVES):
            kinds[c] = set[str]().union(*(kinds[m] for m in operands(g, c)))
        else:
            kinds[c] = leaf_kinds(g, c, b)
        for p in (ODRL["or"], ODRL.xone, DPROD["not"]):
            for o in g.objects(c, p):
                if len(set[str]().union(*(kinds[m] for m in members(g, o)))) == 2:
                    r.diag(
                        "MixedDutyConstraint",
                        f"{q(g, c)}: {q(g, p)} mixes a guard and a witness condition",
                    )


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
    for c in g.objects(rule, ODRL.constraint):
        tree = constraint_tree(g, c, r)
        for n in tree:
            check_constraint(g, n, b, r, used, kind == ODRL.Duty)
        if kind == ODRL.Duty:
            check_mixed(g, tree, b, r)
    for a in actions:
        for ref in g.objects(a, ODRL.refinement):
            for n in constraint_tree(g, ref, r):
                check_constraint(g, n, b, r, used, kind == ODRL.Duty)
    for pred in (ODRL.consequence, ODRL.remedy):
        if (rule, pred, None) in g:
            r.warn(f"{q(g, rule)}: {q(g, pred)} is carried by stage 1 but not evaluated for access")
    for pred in NESTED_EDGES:
        for d in g.objects(rule, pred):
            check_rule(g, d, ODRL.Duty, policy, b, r, used, seen, [*path, rule], named)


def typed(g: Graph) -> set[Node]:
    return {s for s in g.subjects(RDF.type, None) if isinstance(s, URIRef)}


@cache
def odrl_terms() -> frozenset[Node]:
    """The odrl: terms the official vocabulary types, Core and Common. Its cc:
    terms are not among them (decisions/0020 #4)."""
    return frozenset(t for t in typed(parse([W3C_VOCABULARY])) if str(t).startswith(str(ODRL)))


def vocabulary_terms(g: Graph, positions: tuple[URIRef, ...] = VOCABULARY_POSITIONS) -> set[Node]:
    """The IRIs in `positions`; a refined action, blank or named, names its action
    by rdf:value (IM 2.5.4)."""
    terms: set[Node] = set()
    for p in positions:
        for o in g.objects(None, p):
            if p == ODRL.action and (o, RDF.value, None) in g:
                o = g.value(o, RDF.value)
            if isinstance(o, URIRef):
                terms.add(o)
    return terms


def ns_terms(g: Graph, ns: str) -> int:
    n = 0
    for _, p, o in g:
        if str(p).startswith(ns) or (isinstance(o, URIRef) and str(o).startswith(ns)):
            n += 1
    return n


def entity_properties(vocabulary: Graph) -> frozenset[Node]:
    """The properties whose value must be a resource, never a literal.

    `vocabulary` is the merged graph: the policy, due2's core, the selected profile
    modules, and the ODRL vocabulary. The result is odrl:function (range odrl:Party),
    odrl:relation (range odrl:Asset), and every rdfs:subPropertyOf descendant of
    either, which inherits the range: odrl:assignee, odrl:informedParty,
    odrl:target, and a profile's own party roles, such as dprod:subjectOfDuty.
    """
    found: set[Node] = {ODRL.function, ODRL.relation}
    frontier = set(found)
    while frontier:
        frontier = {s for o in frontier for s in vocabulary.subjects(RDFS.subPropertyOf, o)}
        frontier -= found
        found |= frontier
    return frozenset(found)


def asset_party_nodes(g: Graph, entities: frozenset[Node]) -> set[Node]:
    """Every node that is the value of one of `entities` (`entity_properties`), plus
    every declared collection."""
    nodes = {o for e in entities for o in g.objects(None, e)}
    nodes |= set(g.subjects(RDF.type, ODRL.AssetCollection))
    nodes |= set(g.subjects(RDF.type, ODRL.PartyCollection))
    return nodes


ROOT_ACTIONS = {ODRL.use, ODRL.transfer}


@cache
def deprecated_actions() -> frozenset[Node]:
    """The actions the official vocabulary deprecates. They have no odrl:includedIn,
    so IM 2.4 cannot hold for them, and check_actions exempts them."""
    v = parse([W3C_VOCABULARY])
    return frozenset(
        s
        for s, o in v.subject_objects(OWL.deprecated)
        if o == Literal(True) and (s, RDF.type, ODRL.Action) in v
    )


def check_actions(g: Graph, hierarchy: Graph, defined: frozenset[Node], r: Report) -> None:
    """IM 2.4: an action other than use and transfer has exactly one odrl:includedIn,
    of type Action, and following odrl:includedIn from it reaches use or transfer.

    Checks the actions the policy uses or defines, and their ancestors, in
    `hierarchy`: the policy with the core, the selected modules, and the official
    vocabulary, so that an edge restated in the policy adds to the vocabulary's
    rather than replacing it. A term outside `defined` is UndeclaredProfile
    instead, and an action the vocabulary deprecates is exempt. A refined action
    is checked through its rdf:value, never as a node of the hierarchy itself."""
    todo = vocabulary_terms(g, (ODRL.action,))
    todo |= {
        s
        for s in g.subjects(RDF.type, ODRL.Action)
        if isinstance(s, URIRef) and (s, RDF.value, None) not in g
    }
    for a in sorted(g.objects(None, ODRL.action), key=str):
        if isinstance(a, BNode) and (a, RDF.value, None) not in g:
            r.diag(
                "InvalidActionHierarchy",
                f"{q(g, a)}: a blank action without rdf:value names no action, so it has "
                "no odrl:includedIn",
            )
    seen: set[Node] = set()
    while todo:
        a = todo.pop()
        if a in seen or a not in defined or a in ROOT_ACTIONS or a in deprecated_actions():
            continue
        seen.add(a)
        parents = sorted(hierarchy.objects(a, ODRL.includedIn), key=str)
        todo |= set(parents)
        if len(parents) != 1:
            r.diag(
                "InvalidActionHierarchy",
                f"{q(g, a)}: {len(parents)} odrl:includedIn values; IM 2.4 requires one",
            )
        for parent in parents:
            if (parent, RDF.type, ODRL.Action) not in hierarchy:
                r.diag(
                    "InvalidActionHierarchy",
                    f"{q(g, a)}: odrl:includedIn {q(g, parent)}, which is not an odrl:Action",
                )
        if parents and not reachable(hierarchy, a, set(), ODRL.includedIn) & ROOT_ACTIONS:
            r.diag(
                "InvalidActionHierarchy",
                f"{q(g, a)}: its odrl:includedIn path reaches neither odrl:use nor odrl:transfer",
            )


def reachable(g: Graph, root: Node, stop: set[Node], edge: URIRef | None = None) -> set[Node]:
    """Every node that a path of triples reaches from `root`, `root` included,
    entering no node of `stop` except `root`. With `edge`, only triples with that
    predicate."""
    seen, todo = {root}, [root]
    while todo:
        for o in g.objects(todo.pop(), edge):
            if not isinstance(o, Literal) and o not in seen:
                seen.add(o)
                if o not in stop:
                    todo.append(o)
    return seen


def check_placement(
    g: Graph, policy: Node, policies: set[Node], entities: frozenset[Node], r: Report
) -> None:
    """Constraints and Rules where the ODRL vocabulary places them (normalisation
    3). The rest of this checker reads each property only in its place, so a
    misplaced one would otherwise be dropped silently. Scoped to the policy's
    component graph, which stops at another policy (a DPROD Agreement names its
    Offer), so that a file with several policies reports each once."""
    scope = reachable(g, policy, policies)
    classes: dict[Node, set[Node]] = {}
    for edge, (_, cls) in EDGE_PLACES.items():
        for s, o in g.subject_objects(edge):
            if s in scope:
                classes.setdefault(o, set()).add(cls)
    for cls in RULE_CLASSES:
        for s in g.subjects(RDF.type, cls):
            if s in scope:
                classes.setdefault(s, set()).add(cls)
    # The Rule classes are pairwise disjoint (IM 2.6; Vocabulary 3.9.1, 3.10.1,
    # 3.13.1): a duty edge on a Prohibition makes it a Permission as well.
    for node, cs in sorted(classes.items(), key=lambda x: str(x[0])):
        if len(cs) > 1:
            both = " and ".join(sorted(q(g, c) for c in cs))
            r.diag("InvalidNesting", f"{q(g, node)}: both {both}, which are disjoint")
    # A Consequence or a Remedy carries no Consequence (IM 2.6.3, 2.6.7).
    closed = {o for e in (ODRL.consequence, ODRL.remedy) for o in g.objects(None, e)}
    for edge, (domain, _) in EDGE_PLACES.items():
        for s in sorted({s for s in g.subjects(edge, None) if s in scope}, key=str):
            if domain is None:
                ok, place = s in policies, "a Policy"
            else:
                ok, place = classes.get(s) == {domain}, f"a {q(g, domain)}"
                if edge == ODRL.consequence and s in closed:
                    ok, place = False, "a Duty that odrl:duty or odrl:obligation references"
            if not ok:
                r.diag("InvalidNesting", f"{q(g, s)}: {q(g, edge)} belongs on {place} only")
    # The vocabulary's domains: a refinement narrows an Action or a collection, and
    # a constraint conditions a Policy or a Rule (IM 2.5; Vocabulary 3.14.2-3.14.3).
    # Each is tested as a domain, not against a list of the nodes it may not sit on,
    # so a node a profile's own property reaches is covered. `narrowed` holds every
    # Asset and Party, so a refinement on one passes here and check_policy rejects it
    # as a collection refinement (UnsupportedConstruct); the Policy's own constraint
    # passes here and is UnsupportedConstruct there too.
    actions = {a for s, a in g.subject_objects(ODRL.action) if s in scope}
    narrowed = actions | asset_party_nodes(g, entities)
    for node in sorted({s for s in g.subjects(ODRL.refinement, None) if s in scope}, key=str):
        if node not in narrowed:
            r.diag(
                "MisplacedConstraint",
                f"{q(g, node)}: odrl:refinement on neither an Action nor a collection",
            )
    for node in sorted({s for s in g.subjects(ODRL.constraint, None) if s in scope}, key=str):
        if node not in policies and node not in classes:
            r.diag(
                "MisplacedConstraint",
                f"{q(g, node)}: odrl:constraint on neither a Policy nor a Rule",
            )


def check_policy(
    g: Graph,
    policy: Node,
    policies: set[Node],
    b: Bindings,
    r: Report,
    named: bool,
    defined: frozenset[Node] | None,
    entities: frozenset[Node],
) -> Used:
    """`policies` are the graph's policy nodes. `defined` is the vocabulary the
    policy may use (decisions/0020), or None when a selected profile has no
    module: the policy is then rejected (UnrecognisedProfile), and the profile
    may define any term, so the vocabulary is not checked (decisions/0033).
    `entities` are the properties whose value is an Asset or a Party
    (`entity_properties`)."""
    used: Used = {}
    declared = {str(p) for p in g.objects(policy, ODRL.profile)}
    for ns, label in NAMESPACED_PROFILES.items():
        if ns_terms(g, ns) and ns not in declared:
            r.diag(
                "UndeclaredProfile",
                f"{q(g, policy)}: uses {label} terms but declares no "
                f"odrl:profile <{ns}>; normalisation will not select its module",
            )
    if defined is not None:
        for t in sorted(vocabulary_terms(g) - defined, key=str):
            r.diag(
                "UndeclaredProfile",
                f"{q(g, t)}: defined by neither the ODRL vocabulary (odrl: namespace), "
                "a selected profile, nor the policy",
            )
    if (policy, DCTERMS.isReplacedBy, None) in g:
        # IM 2.8: the policy is void; the policy store selects its replacement.
        r.diag("ReplacedPolicy", f"{q(g, policy)}: dct:isReplacedBy; evaluate the replacement")
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
    if (policy, ODRL.constraint, None) in g:
        # Valid ODRL (Vocabulary 3.14.2), but the IM gives it no meaning: IM 2.1
        # lists none, and IM 2.7.1 shares none with the Rules (normalisation 3).
        r.diag(
            "UnsupportedConstruct", f"{q(g, policy)}: odrl:constraint on a Policy is not admitted"
        )
    check_placement(g, policy, policies, entities, r)
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
    for node in sorted(asset_party_nodes(g, entities), key=str):
        if (node, ODRL.refinement, None) in g:
            r.diag("UnsupportedConstruct", f"{q(g, node)}: collection refinement is not admitted")
    # IM 2.2, 2.3, 2.6: an Asset or a Party is a resource, and a literal is not one.
    for edge in sorted(entities, key=str):
        for owner, node in sorted(g.subject_objects(edge), key=str):
            if isinstance(node, Literal):
                r.diag(
                    "LiteralEntity",
                    f"{q(g, owner)}: {q(g, edge)} is the literal {node.n3()}, not an IRI",
                )
    # IM 2.2.3 infers a target for every Rule from odrl:hasPolicy, and IM 2.3.3 an
    # assigner or assignee from odrl:assignerOf or odrl:assigneeOf. Normalisation
    # infers nothing beyond the declared edges, so it would drop them.
    for edge, function in (
        (ODRL.hasPolicy, "the asset as odrl:target"),
        (ODRL.assignerOf, "the party as odrl:assigner"),
        (ODRL.assigneeOf, "the party as odrl:assignee"),
    ):
        for node in sorted(g.subjects(edge, policy), key=str):
            r.diag(
                "UnsupportedConstruct",
                f"{q(g, node)}: {q(g, edge)} is not admitted; state {function} "
                "on the Policy or its Rules",
            )
    # The target and the assignee are what a request matches (workflows 5.2); an
    # anonymous one has a generated identity nothing can name (normalisation 3).
    for edge, field_ in ((ODRL.target, "target"), (ODRL.assignee, "assignee")):
        for owner, node in sorted(g.subject_objects(edge), key=str):
            if not isinstance(node, BNode) or (node, ODRL.uid, None) in g:
                continue
            if (node, ODRL.refinement, None) in g:
                continue
            r.diag(
                "AnonymousEntity",
                f"{q(g, owner)}: anonymous {field_} {q(g, node)} has no identity a request can "
                f"name; the rule is never T, and a request with no {field_} makes it U, so the "
                "verdict can be Indeterminate",
            )
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
        modules: list[Graph] = []
        for p in sel:
            if p not in MODULES:
                # IM 3.2: a processor that does not recognise a profile stops.
                r.diag("UnrecognisedProfile", f"{q(g, policy)}: profile <{p}> has no due2 module")
            elif MODULES[p]:
                modules.append(parse(MODULES[p]))
        core = parse(CORE)
        vocabulary = g + core + parse([W3C_VOCABULARY])
        for m in modules:
            vocabulary += m
        defined = None
        if all(p in MODULES for p in sel):
            defined = frozenset(
                odrl_terms().union(typed(core), typed(g), *(typed(m) for m in modules))
            )
        used = check_policy(
            g,
            policy,
            set(policies),
            Bindings(g, modules, core, r),
            r,
            named,
            defined,
            entity_properties(vocabulary),
        )
        if defined is not None:
            check_actions(g, vocabulary, defined, r)
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


# Vendored upstream policies that W1 rejects, with the codes it rejects them with.
# They are kept unmodified (conformance/README.md), so the rejection is expected.
VENDORED_REJECTED = {
    "profiles/vendor/dprod/examples/baseline.ttl": (
        ["InvalidActionHierarchy"],
        "ex:conformTo has no odrl:includedIn",
    ),
    "profiles/vendor/dprod/examples/odcs.ttl": (
        ["InvalidActionHierarchy"],
        "ex:conformTo has no odrl:includedIn",
    ),
}


def check_vendored(path: Path, reports: list[Report]) -> None:
    """A policy file in VENDORED_REJECTED: each of its policies must be rejected
    with exactly the listed codes."""
    try:
        rel = path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return
    if rel not in VENDORED_REJECTED:
        return
    codes, reason = VENDORED_REJECTED[rel]
    for x in reports:
        got = sorted(set(x.rejection()))
        if got != sorted(codes):
            x.err(f"vendored, expected rejection {sorted(codes)} ({reason}), gives {got or 'none'}")
            continue
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
        if "config" in sc:
            r.err(f"{tag}: an evaluation has no config (decisions/0045)")
        req = sc.get("request", {})
        for k in ("action", "at"):  # target may be absent (workflows 3.2)
            if k not in req:
                r.err(f"{tag}: request.{k} missing")
        if "at" in req and not instant_ok(str(req["at"])):
            r.err(f"{tag}: request.at is not an xsd:dateTime instant: {req['at']!r}")
        for k in req.get("params", {}):
            if expand(k, prefixes) not in request_props:
                r.warn(f"{tag}: request param {k} is read by no bound operand")
        sotw = sc.get("sotw", {})
        if "effective_at" not in sotw:
            r.err(f"{tag}: sotw.effective_at missing")
        elif not instant_ok(str(sotw["effective_at"])):
            r.err(
                f"{tag}: sotw.effective_at is not an xsd:dateTime instant: {sotw['effective_at']!r}"
            )
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
            if "occurred_at" in ev and not instant_ok(str(ev["occurred_at"])):
                r.err(
                    f"{tag}: evidence occurred_at is not an xsd:dateTime instant: {ev['occurred_at']!r}"
                )
            for k in ev.get("params", {}):
                if expand(k, prefixes) not in witness_props:
                    r.warn(f"{tag}: evidence param {k} is read by no witness-source operand")
        has_deadline = (None, DPROD.deadline, None) in g
        for k, at in sotw.get("activation", {}).items():
            if not instant_ok(str(at)):
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
            if "instance" in ob and not instant_ok(str(ob["instance"])):
                r.err(
                    f"{tag}: obligation instance {ob['instance']!r} is not an xsd:dateTime instant"
                )
        if exp.get("verdict") == "Pending" and not exp.get("frontier"):
            r.err(f"{tag}: Pending needs a frontier")
        check_explanation(tag, exp, g, prefixes, r)
        check_range(tag, exp, r)
        check_frontier_complete(tag, exp, r)
        check_unknown_parts(tag, exp, g, prefixes, {str(p) for _, p, _ in used.values()}, r)
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


def check_frontier_complete(tag: str, exp: dict[str, Any], r: Report) -> None:
    """expected.frontier_complete (conformance/README.md, workflows 6.4, decisions/0004): whether
    every completion's frontier is the listed one, recorded for a Pending only."""
    if "frontier_complete" not in exp:
        return
    if not isinstance(exp["frontier_complete"], bool):
        r.err(f"{tag}: frontier_complete must be true or false")
    elif exp.get("verdict") != "Pending":
        r.err(f"{tag}: frontier_complete is recorded for a Pending only (workflows 6.4)")


PART_STATUSES = {"missing", "invalid", "conflict", "unresolved", "misfit"}


def check_unknown_parts(
    tag: str, exp: dict[str, Any], g: Graph, pfx: dict[str, str], props: set[str], r: Report
) -> None:
    """expected.unknown_parts (conformance/README.md, workflows 3.5, decisions/0016): shape,
    that each ref is a rule or duty of policy.ttl, and that a target or party input is missing.

    An input that is not the property of an operand the policy reads, `props`, is the target
    or a party function. A request field is never unresolved (due2-profiles.md 3), and the
    case format carries an absent target or party as absent, so its status can only be
    `missing`. An operand's property, `odrl:purpose` among them, can have any status.
    """
    if "unknown_parts" not in exp:
        return
    rules = {str(x) for c in (ODRL.Permission, ODRL.Prohibition) for x in g.subjects(RDF.type, c)}
    duties = {str(x) for p in (ODRL.duty, ODRL.obligation) for x in g.objects(None, p)}
    for raw in exp["unknown_parts"]:
        u = entry(raw, {"ref", "input", "status"})
        if u is None:
            r.err(f"{tag}: unknown_parts entry must be {{ref, input, status}}: {raw!r}")
            continue
        if u["status"] not in PART_STATUSES:
            r.err(
                f"{tag}: unknown part status {u['status']!r} is not one of {sorted(PART_STATUSES)}"
            )
        if expand(u["ref"], pfx) not in rules | duties:
            r.err(f"{tag}: unknown part {u['ref']} is no rule or duty of policy.ttl")
        if expand(u["input"], pfx) not in props and u["status"] != "missing":
            r.err(f"{tag}: the request field {u['input']} can only be missing (profiles 3)")


def entry(x: object, keys: set[str]) -> dict[str, Any] | None:
    """x as an object with exactly these keys, or None."""
    return dict(x) if isinstance(x, dict) and set(x) == keys else None  # pyright: ignore[reportUnknownArgumentType]


def check_explanation(
    tag: str, exp: dict[str, Any], g: Graph, pfx: dict[str, str], r: Report
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
        need = {
            "Permit": "permission" in by_role,
            "Pending": "permission" in by_role and "duty" in by_role,
            "Indeterminate": "unknown" in by_role,
            "Deny": "prohibition" in by_role,
        }
        # A definite verdict that holds by cases has no atom in every completion, so its basis
        # can lack the role (workflows 6.4, decisions/0016 #4). Holding by cases needs two
        # atoms that read one variable, and only unresolved parts are shared, so the waiver
        # asks the scenario to list one.
        parts = (entry(u, {"ref", "input", "status"}) for u in exp.get("unknown_parts", []))
        by_cases = any(u is not None and u["status"] == "unresolved" for u in parts)
        # A Pending's frontier varies by dominance, so one variable of any status can leave
        # either role empty, and the listed frontier can miss duties of every completion's
        # (decisions/0019). Under unknowns only the kinds are checked.
        loose = verdict == "Pending" and bool(exp.get("unknown_parts"))
        waived = loose or (verdict != "Indeterminate" and by_cases)
        if not need.get(str(verdict), True) and not waived:
            r.err(
                f"{tag}: verdict_basis lacks the atoms that determine {verdict} (workflows 6.4);"
                " a verdict that holds by cases states its unresolved unknown_parts"
            )
        frontier = {expand(d, pfx) for alt in exp.get("frontier", []) for d in alt}
        if verdict == "Pending" and not loose and by_role.get("duty", set()) != frontier:
            r.err(f"{tag}: the basis's duties must be the frontier's duties")
        in_force = {expand(o.get("duty", ""), pfx) for o in exp.get("obligations", [])}
        if by_role.get("obligation", set()) != in_force:
            r.err(f"{tag}: the basis's obligations must be expected.obligations' duties")
    if "eliminated" in exp:
        removers = {
            "prohibit": (perms, prohibs),
            "perm": (prohibs, perms),
            "invalid": (perms | prohibs, perms | prohibs),
            "violated_precondition": (perms, preconds),
            "prohibit-overrides": (perms, prohibs),
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
            file_reports = [r for r, _, _ in check_file(p, args.profile, named=False)]
            check_vendored(p, file_reports)
            reports += file_reports
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
