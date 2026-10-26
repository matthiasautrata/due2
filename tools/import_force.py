"""Translate the vendored FORCE test suite into due2 conformance cases.

Reads conformance/external/force/ (unmodified upstream, see its NOTICE) and
writes conformance/cases/force-<policy>/ — one case per FORCE policy, one
scenario per FORCE test case. Run once; the generated cases are then corpus
artefacts reviewed and maintained by hand like any other. Re-running
overwrites them.

Translation (recorded per case in `notes`):
  * FORCE's request (an odrl:Request with one permission) -> request;
    temp:currentTime -> request.at and sotw.effective_at (FORCE has one clock;
    odrl:dateTime is bound to the action time in due2-core).
  * odrl:partOf triples in the SOTW -> sotw.closure.
  * A DutyReport with performanceState Performed -> one evidence record by the
    duty's bearer. FORCE's asserted deontic states are not inputs in due2,
    which derives duty status from evidence (due2-profiles.md 8.2, exc. 2).
  * odrl:source on collections is kept: due2 admits a refinement-free source
    as an inert annotation (due2-profiles.md 8.1); membership is the SOTW's
    partOf edges. An explicit odrl:conflict is added.
  * FORCE's own result is kept as `force_expected` (rule kind:activation).

The due2 verdict is derived independently by the small matcher below, which
covers exactly what these policies use: one permission, optional duties,
odrl:dateTime constraints under and/or, includedIn/partOf closure. Where the
two disagree beyond the documented divergences, the scenario is marked for
review in `notes` rather than silently aligned.

Policies 1-7 (--negative): their rules omit odrl:target (and 1-2
odrl:action); IM 2.6.1/2.6.2 require one target, so they are not ODRL 2.2 and
due2 rejects them at normalisation. They become negative cases
(conformance/README.md): the policy copied unchanged, the expected rejection
codes (due2-diagnostics.md), and FORCE's own results kept per test case.

Usage:
  import_force.py              # policies 8-21 -> positive cases
  import_force.py --negative   # policies 1-7  -> negative cases
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from rdflib import Graph, Namespace
from rdflib.namespace import DCTERMS, RDF, XSD

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "conformance" / "external" / "force"
OUT = ROOT / "conformance" / "cases"
ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
EX = Namespace("http://example.org/")
TEMP = Namespace("http://example.com/request/")
REP = Namespace("https://w3id.org/force/compliance-report#")
UPSTREAM = "SolidLabResearch/ODRL-Test-Suite@7958238"

INCLUDE = range(8, 22)
# odrl:read ⊑ odrl:use is the only includedIn edge these cases need; due2
# ships it in profiles/odrl-actions.ttl.
INCLUDED_IN = {(ODRL.read, ODRL.use)}

# Found while translating; worth reporting upstream (conformance/external/README.md).
UPSTREAM_DEFECTS = {
    11: [
        (
            "Upstream defect: testcase-036 is titled for the current-time state (temporal.ttl) "
            "but index.ttl wires it to temporal-future.ttl, making it a duplicate of 038; the "
            "scenario follows the wiring, and the lt-at-equal-instant case is untested."
        )
    ],
    21: [
        (
            "Upstream defect: the DutyReport in all-2023.ttl and all-2024.ttl names policy-19's "
            "duty, not this policy's. Read as a world fact — ex:alice compensated — it is one "
            "evidence record, and due2's evidence is existential (conformance/README.md), so it "
            "witnesses this duty too: 065 permits in both evaluators, for different reasons."
        )
    ],
}

PREFIXES = {"odrl": str(ODRL), "ex": str(EX), "xsd": str(XSD)}


def curie(t) -> str:
    s = str(t)
    for p, ns in PREFIXES.items():
        if s.startswith(ns) and re.fullmatch(r"[A-Za-z0-9_\-]+", s[len(ns) :]):
            return f"{p}:{s[len(ns) :]}"
    return s


def lit(dt: str) -> dict:
    return {"@value": dt, "@type": "xsd:dateTime"}


def utc(lexical: str) -> datetime:
    return datetime.fromisoformat(lexical)


def name_of(path: str) -> str:
    return os.path.basename(str(path))


# ---------------------------------------------------------------- matcher


def leq(a, b, edges) -> bool:
    """a ⊑ b under the reflexive-transitive closure of `edges`."""
    seen, todo = set(), [a]
    while todo:
        x = todo.pop()
        if x == b:
            return True
        if x in seen:
            continue
        seen.add(x)
        todo += [y for (n, y) in edges if n == x]
    return False


def holds(g: Graph, c, at: datetime) -> bool:
    for conn, f in ((ODRL["and"], all), (ODRL["or"], any)):
        ms = list(g.objects(c, conn))
        if ms:
            return f(holds(g, m, at) for m in ms)
    if g.value(c, ODRL.leftOperand) != ODRL.dateTime:
        raise ValueError(f"{c}: FORCE constraints here read odrl:dateTime only")

    op = g.value(c, ODRL.operator)
    rv = utc(str(g.value(c, ODRL.rightOperand)))
    return {
        ODRL.eq: at == rv,
        ODRL.neq: at != rv,
        ODRL.lt: at < rv,
        ODRL.lteq: at <= rv,
        ODRL.gt: at > rv,
        ODRL.gteq: at >= rv,
    }[op]


def derive(pol: Graph, rule, req: dict, at: datetime, partof: set, witnessed: set):
    """Return (verdict, frontier, failing-part text, duty ids)."""
    fails = []
    if not leq(req["action"], pol.value(rule, ODRL.action), INCLUDED_IN):
        fails.append(f"action {curie(req['action'])} ⋢ {curie(pol.value(rule, ODRL.action))}")
    if not leq(req["target"], pol.value(rule, ODRL.target), partof):
        fails.append(f"target {curie(req['target'])} ⋢ {curie(pol.value(rule, ODRL.target))}")
    a = pol.value(rule, ODRL.assignee)
    if a is not None and not leq(req["assignee"], a, partof):
        fails.append(f"assignee {curie(req['assignee'])} ⋢ {curie(a)}")
    for c in pol.objects(rule, ODRL.constraint):
        if not holds(pol, c, at):
            fails.append(f"the odrl:dateTime constraint is F at {at.isoformat()}")
    if fails:
        return "NotApplicable", [], "; ".join(fails), []
    duties = sorted(pol.objects(rule, ODRL.duty), key=str)
    outstanding = [
        d for d in duties if (pol.value(d, ODRL.action), req["assignee"]) not in witnessed
    ]
    if outstanding:
        return "Pending", [[curie(d) for d in outstanding]], "", outstanding
    return "Permit", [], "", duties


# ---------------------------------------------------------------- reading


def load(rel: str) -> Graph:
    return Graph().parse(SRC / rel)


def duty_bearers() -> dict:
    """Duty IRI -> bearer, from every FORCE policy (FORCE reports name duties
    across policies, see notes)."""
    out = {}
    for f in (SRC / "policies").glob("*.ttl"):
        g = Graph().parse(f)
        for perm, duty in g.subject_objects(ODRL.duty):
            out[duty] = (
                g.value(duty, ODRL.assignee) or g.value(perm, ODRL.assignee),
                g.value(duty, ODRL.action),
            )
    return out


def main() -> None:
    idx = Graph().parse(SRC / "index.ttl")
    bearers = duty_bearers()
    by_policy: dict[str, list] = {}
    for tc in idx.subjects(EX.policySource, None):
        by_policy.setdefault(name_of(idx.value(tc, EX.policySource)), []).append(tc)

    for n in INCLUDE:
        pfile = f"policy-{n}.ttl"
        pol = load(f"policies/{pfile}")
        policy = next(pol.subjects(RDF.type, ODRL.Set))
        rule = pol.value(policy, ODRL.permission)
        desc = str(pol.value(policy, DCTERMS.description))
        has_source = (None, ODRL.source, None) in pol
        pol.add((policy, ODRL.conflict, ODRL.prohibit))

        scenarios, review = [], []
        tcs = sorted(by_policy[pfile], key=lambda t: name_of(idx.value(t, EX.expectedReportSource)))
        for tc in tcs:
            tcfile = name_of(idx.value(tc, EX.expectedReportSource))
            rq = load(f"requests/{name_of(idx.value(tc, EX.requestSource))}")
            rperm = next(rq.objects(None, ODRL.permission))
            req = {k: rq.value(rperm, ODRL[k]) for k in ("assignee", "action", "target")}
            sw_name = name_of(idx.value(tc, EX.sotwSource))
            sw = load(f"sotw/{sw_name}")
            now = str(sw.value(TEMP.currentTime, DCTERMS.issued))
            at = utc(now)
            partof = {(s, o) for s, o in sw.subject_objects(ODRL.partOf)}
            evidence, witnessed = [], set()
            for i, rr in enumerate(
                sorted(sw.subjects(REP.performanceState, REP.Performed), key=str)
            ):
                actor, action = bearers[sw.value(rr, REP.rule)]
                evidence.append(
                    {
                        "id": f"ev-{i + 1}",
                        "occurred_at": now,
                        "actor": curie(actor),
                        "action": curie(action),
                    }
                )
                witnessed.add((action, actor))
            exp = load(f"test_cases/{tcfile}")
            rr = next(exp.subjects(REP.activationState, None))
            force = (
                exp.value(rr, RDF.type).split("#")[1].replace("Report", "")
                + ":"
                + exp.value(rr, REP.activationState).split("#")[1]
            )

            verdict, frontier, fail, duties = derive(pol, rule, req, at, partof, witnessed)
            if verdict == "NotApplicable":
                why = f"{curie(rule)} does not apply: {fail}. It is the only rule."
            elif verdict == "Pending":
                why = (
                    f"{curie(rule)} applies, but its precondition duty "
                    f"{', '.join(frontier[0])} has no witness in the evidence, so it is "
                    f"outstanding (workflows §5.3): the frontier is that one route."
                )
            else:
                why = f"{curie(rule)} applies: action, target and assignee match"
                why += (
                    " and every constraint holds at request.at"
                    if list(pol.objects(rule, ODRL.constraint))
                    else ""
                )
                why += (
                    f"; its duty is witnessed by {', '.join(e['id'] for e in evidence)}"
                    if duties
                    else "; it has no duties"
                ) + "."
            agrees = (force == "Permission:Active") == (verdict in ("Permit", "Pending"))
            asserted_violation = (None, REP.deonticState, REP.Violated) in sw
            if not agrees and not asserted_violation:
                review.append(f"{tcfile}: due2 {verdict}, FORCE {force}")
            scenarios.append(
                {
                    "name": f"{tcfile.removesuffix('.ttl')} ({sw_name.removesuffix('.ttl')})",
                    "request": {
                        "reference": f"force-{tcfile[9:12]}",
                        "action": curie(req["action"]),
                        "target": curie(req["target"]),
                        "at": now,
                        "parties": {"odrl:assignee": curie(req["assignee"])},
                        "params": {},
                    },
                    "sotw": {
                        "effective_at": now,
                        "facts": {},
                        "evidence": evidence,
                        "activation": {},
                        "closure": [["odrl:partOf", curie(s), curie(o)] for s, o in sorted(partof)],
                    },
                    "expected": {
                        "verdict": verdict,
                        "frontier": frontier,
                        "obligations": [],
                        "why": why,
                    },
                    "force_expected": force,
                }
            )

        notes = [
            (
                f"Translated by tools/import_force.py from {UPSTREAM} data/policies/{pfile} "
                f'and its {len(tcs)} test cases; FORCE: "{desc}"'
            ),
            (
                "temp:currentTime becomes request.at and sotw.effective_at; odrl:partOf edges in "
                "FORCE's state of the world become sotw.closure; an explicit odrl:conflict "
                "odrl:prohibit is added (single rule, so it cannot fire)."
            ),
        ]
        if has_source:
            notes.append(
                "odrl:source on the collection is kept as written: due2 admits a "
                "refinement-free source as an inert annotation (due2-profiles.md §8.1), "
                "and membership comes from FORCE's partOf edges, carried in sotw.closure."
            )
        if list(pol.subject_objects(ODRL.duty)):
            notes.append(
                "FORCE's duty states are asserted inputs (DutyReports); due2 derives them "
                "from evidence. A report with performanceState Performed becomes one "
                "evidence record by the duty's bearer; NonSet and Violated reports carry no "
                "evidence. FORCE activates the permission while the duty is unperformed "
                '("given that eventually the duty is fulfilled"); due2 returns Pending '
                "with the duty as the route — the standing divergence on preconditions. "
                "FORCE's Violated state has no deadline behind it, so due2 cannot reproduce "
                "it and returns Pending."
            )
        notes += UPSTREAM_DEFECTS.get(n, [])
        if review:
            notes.append(
                "REVIEW — disagreement beyond the documented divergences: " + "; ".join(review)
            )

        case = f"force-{n:02d}"
        d = OUT / case
        d.mkdir(parents=True, exist_ok=True)
        ttl = pol.serialize(format="turtle")
        (d / "policy.ttl").write_text(
            f"# Source: {UPSTREAM} data/policies/{pfile} (MIT, imec), via tools/import_force.py.\n"
            f"# Changes: odrl:conflict added.\n\n" + ttl
        )
        (d / "case.json").write_text(
            json.dumps(
                {
                    "case": case,
                    "source": f"FORCE test suite ({UPSTREAM}) data/policies/{pfile}",
                    "classification": "odrl-core",
                    "needs": [],
                    "notes": " ".join(notes),
                    "prefixes": {"ex": str(EX)},
                    "scenarios": scenarios,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )
        print(f"{case}: {len(scenarios)} scenarios" + (f", REVIEW {len(review)}" if review else ""))


NEGATIVE = range(1, 8)


def negative() -> None:
    idx = Graph().parse(SRC / "index.ttl")
    by_policy: dict[str, list] = {}
    for tc in idx.subjects(EX.policySource, None):
        by_policy.setdefault(name_of(idx.value(tc, EX.policySource)), []).append(tc)
    for n in NEGATIVE:
        pfile = f"policy-{n}.ttl"
        pol = load(f"policies/{pfile}")
        policy = next(pol.subjects(RDF.type, ODRL.Set))
        desc = str(pol.value(policy, DCTERMS.description))
        rules = [r for e in (ODRL.permission, ODRL.prohibition) for r in pol.objects(policy, e)]
        codes = {"MissingTarget"}
        if not any(pol.value(r, ODRL.action) for r in rules) and not pol.value(policy, ODRL.action):
            codes.add("MissingAction")
        lacks = "neither an action nor a target" if "MissingAction" in codes else "no target"
        kind = "Permission" if (policy, ODRL.permission, None) in pol else "Prohibition"

        origin = []
        tcs = sorted(by_policy[pfile], key=lambda t: name_of(idx.value(t, EX.expectedReportSource)))
        for tc in tcs:
            tcfile = name_of(idx.value(tc, EX.expectedReportSource))
            exp = load(f"test_cases/{tcfile}")
            rq = load(f"requests/{name_of(idx.value(tc, EX.requestSource))}")
            rperm = next(rq.objects(None, ODRL.permission))
            rr = next(exp.subjects(REP.activationState, None))
            origin.append(
                {
                    "test_case": tcfile.removesuffix(".ttl"),
                    "title": str(next(exp.objects(None, DCTERMS.title), "")),
                    "request": {
                        k: curie(rq.value(rperm, ODRL[k]))
                        for k in ("assignee", "action", "target")
                        if rq.value(rperm, ODRL[k]) is not None
                    },
                    "sotw": name_of(idx.value(tc, EX.sotwSource)),
                    "result": (
                        exp.value(rr, RDF.type).split("#")[1].replace("Report", "")
                        + ":"
                        + exp.value(rr, REP.activationState).split("#")[1]
                    ),
                }
            )

        case = f"force-{n:02d}"
        d = OUT / case
        d.mkdir(parents=True, exist_ok=True)
        (d / "policy.ttl").write_text(
            f"# Source: {UPSTREAM} data/policies/{pfile} (MIT, imec), via tools/import_force.py --negative.\n"
            f"# Changes: none. Not ODRL 2.2 (IM 2.6.1/2.6.2); a negative case.\n\n"
            + (SRC / "policies" / pfile).read_text()
        )
        (d / "case.json").write_text(
            json.dumps(
                {
                    "case": case,
                    "source": f"FORCE test suite ({UPSTREAM}) data/policies/{pfile}",
                    "classification": "odrl-core",
                    "needs": [],
                    "odrl22_valid": False,
                    "notes": (
                        f"Translated by tools/import_force.py --negative from {UPSTREAM} data/policies/{pfile} "
                        f'and its {len(tcs)} test cases; FORCE: "{desc}" FORCE reads an absent '
                        f'{"action and target" if "MissingAction" in codes else "target"} as "any". ODRL 2.2 '
                        "does not: a Permission and a Prohibition MUST have one action and one target "
                        "(IM 2.6.1, 2.6.2), so the policy is not ODRL 2.2 and fails "
                        "odrl22-shape.ttl. due2 rejects it rather than guess the reading "
                        '(architecture §1); "everyone, everything" is the enforcement point\'s default, '
                        "or an explicit asset collection. The test cases are kept, with FORCE's results, "
                        "in force_expected; due2 evaluates none of them. Upstream defect, reported before "
                        "(conformance/external/README.md)."
                    ),
                    "prefixes": {"ex": str(EX)},
                    "expected_rejection": {
                        "codes": sorted(codes),
                        "why": (
                            f"The {kind} {curie(rules[0])} has {lacks}, at rule or policy level. "
                            "Normalisation §6.3 requires "
                            + ("an action and a target" if "MissingAction" in codes else "a target")
                            + " after interiorisation, so W1 rejects the policy in stage 1."
                        ),
                    },
                    "force_expected": origin,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )
        print(f"{case}: rejected with {sorted(codes)}; {len(origin)} FORCE test cases kept")


if __name__ == "__main__":
    negative() if "--negative" in sys.argv[1:] else main()
