#!/usr/bin/env python3
"""Validate due2 policies against ODRL 2.2 itself.

Runs conformance/odrl22-shape.ttl (due2's SHACL encoding of the ODRL
Information Model 2.2, every constraint cited) over policy files, with the
official ODRL 2.2 vocabulary and due2's profile modules merged for class
hierarchy and term typing. Policies are validated *as written* — no
preprocessing: compact form (IM 2.7.1), list-valued right operands for
set-based operators (IM 2.5.1), and list-form logical constraints (IM 2.5.2)
are all checked natively.

Also checks IM 2.1's vocabulary rule — a policy uses only ODRL Core terms,
or declares the profiles whose terms it uses (odrl:profile) — which SHACL
cannot scope to a single policy file once graphs are merged, so it is done
on the policy file alone before merging.

This checks ODRL 2.2 validity only. due2 admissibility (the constructs due2
rejects with diagnostics) is tools/check_corpus.py. The protocol and its
recorded results are conformance/odrl22-conformance.md.

Usage:
  check_odrl22.py conformance/cases            # every case policy
  check_odrl22.py file.ttl [...]               # single policy files
  check_odrl22.py --all                        # corpus + vendored examples

Exit status is non-zero when any violation is found.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF
from pyshacl import validate

ROOT = Path(__file__).resolve().parent.parent
SHAPE = ROOT / "conformance" / "odrl22-shape.ttl"
BASE = [
    ROOT / "profiles" / "vendor" / "w3c" / "ODRL22.ttl",
    ROOT / "profiles" / "due2-core.ttl",
    ROOT / "profiles" / "odrl-actions.ttl",
    ROOT / "profiles" / "dprod.ttl",
    *sorted((ROOT / "profiles" / "vendor" / "dprod").glob("*.ttl")),
]

ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
# IM 2.1: use only Core terms, or declare the profiles whose terms are used.
NAMESPACED_PROFILES = {
    "https://ekgf.org/dprod/spec/develop/": "DPROD Contracts",
    "https://w3id.org/due2/profile#": "due2 core",
}


def ns_terms(g: Graph, ns: str) -> int:
    """Terms (as predicates or objects) in the policy file alone."""
    n = 0
    for _, p, o in g:
        if str(p).startswith(ns):
            n += 1
        elif isinstance(o, URIRef) and str(o).startswith(ns):
            n += 1
    return n


def check_profile_declarations(alone: Graph) -> list[str]:
    declared = {str(p) for p in alone.objects(None, ODRL.profile)}
    problems = []
    for ns, label in NAMESPACED_PROFILES.items():
        if ns_terms(alone, ns) and ns not in declared:
            problems.append(
                f"IM 2.1: policy uses {label} terms but declares no "
                f"odrl:profile <{ns}>")
    return problems


def violations_text(results_graph: Graph) -> list[str]:
    SH = Namespace("http://www.w3.org/ns/shacl#")
    out = []
    for r in sorted(results_graph.subjects(RDF.type, SH.ValidationResult), key=str):
        def vals(p):
            return [str(o) for o in results_graph.objects(r, p)]
        out.append(" | ".join([
            "Focus=" + (vals(SH.focusNode) or ["?"])[0],
            "Path=" + (vals(SH.resultPath) or ["-"])[0],
            (vals(SH.sourceConstraintComponent) or ["?"])[0].rsplit("#", 1)[-1],
            "Msg=" + (vals(SH.resultMessage) or ["?"])[0],
        ]))
    return out


def check_file(path: Path, shapes: Graph, base: Graph) -> tuple[str, list[str]]:
    alone = Graph()
    alone.parse(path)
    problems = check_profile_declarations(alone)
    data = Graph()
    data += base
    data += alone
    try:
        conforms, rg, _ = validate(data_graph=data, shacl_graph=shapes,
                                   inference="none", advanced=True)
    except Exception as e:  # noqa: BLE001
        return str(path), [f"HARNESS ERROR (pyshacl raised): {e}"]
    if not isinstance(rg, Graph):
        return str(path), [f"HARNESS ERROR (pyshacl): {rg}"]
    if not conforms:
        problems += violations_text(rg)
    name = str(path.resolve().relative_to(ROOT))
    return name, problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", type=Path)
    ap.add_argument("--all", action="store_true",
                    help="corpus cases plus vendored DPROD examples")
    ap.add_argument("--quiet", action="store_true", help="print only failing items")
    args = ap.parse_args()

    targets: list[Path] = []
    if args.all:
        targets += [p / "policy.ttl" for p in sorted((ROOT / "conformance" / "cases").iterdir())
                    if (p / "policy.ttl").exists()]
        targets += sorted((ROOT / "profiles" / "vendor" / "dprod" / "examples").glob("*.ttl"))
    for p in args.paths:
        if p.is_dir():
            if (p / "policy.ttl").exists():
                targets.append(p / "policy.ttl")
            else:
                targets += [x / "policy.ttl" for x in sorted(p.iterdir())
                            if (x / "policy.ttl").exists()]
        else:
            targets.append(p)
    if not targets:
        ap.error("no targets (give paths, a case directory, or --all)")

    shapes = Graph()
    shapes.parse(SHAPE)
    base = Graph()
    for f in BASE:
        base.parse(f)

    bad = 0
    for t in targets:
        try:
            name, problems = check_file(t, shapes, base)
        except Exception as e:  # noqa: BLE001
            name, problems = str(t), [f"HARNESS ERROR: {e}"]
        if problems:
            bad += 1
            print(f"FAIL  {name}")
            for m in problems:
                print(f"      {m}")
        elif not args.quiet:
            print(f"ok    {name}")
    total = len(targets)
    print(f"\n{total} checked, {bad} failing")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
