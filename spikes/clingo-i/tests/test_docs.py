"""The documentation checks (ways-of-working.md §15.10).

The generated reference (`docs/`, built by mkdocs with clindocs and mkdocstrings) is only as good
as the doc blocks it reads, so these tests hold the blocks to the program. Every relation the
program defines has exactly one `%*!` doc block, with the relation's arity and a summary
sentence that clindocs can cut at its first full stop. Each file's header lists what it
consumes and provides, and the lists match the rules. The documentation entry point includes
the files the interpreter loads, in the same order. No section reference is bare: each `§`
names its document.

The program is read with `clingo.ast`, the same parser the interpreter's solves use, so a rule
the parser reads differently from a regular expression cannot slip past.
"""

import re
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import cast

import pytest
from clingo import ast

from clingo_i.interpret import LP, PROGRAM_FILES

ROOT = Path(__file__).parent.parent
Signature = tuple[str, int]

# A `%*! name(A, B)` header, then the block's text up to `*%`.
DOC_BLOCK = re.compile(r"%\*!\s*(\w+)(?:\(([^)]*)\))?\s*\n(.*?)\*%", re.DOTALL)
# A backticked `name/arity` in a file header.
SIGNATURE = re.compile(r"`(\w+)/(\d+)`")


def _children(node: ast.AST, key: str) -> list[ast.AST]:
    """The nodes under `node.key`: one node, a sequence of them, or none.

    clingo's `AST` resolves attributes dynamically, so they have no static type. `items()` is
    typed, and the result is narrowed here, once.
    """
    value = dict(node.items())[key]
    if isinstance(value, ast.AST):
        return [value]
    if isinstance(value, ast.ASTSequence):
        return [c for c in cast("Iterable[object]", value) if isinstance(c, ast.AST)]
    return []


def _one(node: ast.AST, key: str) -> ast.AST:
    """The single node under `node.key`."""
    (child,) = _children(node, key)
    return child


def _signature(symbol: ast.AST) -> Signature | None:
    """The name and arity of an atom's symbol, or None for a term that names no predicate.

    A pooled atom, such as `two_valued(f; t)`, is one `Pool` of functions with the same name
    and arity, so its first function stands for all of them.
    """
    if symbol.ast_type == ast.ASTType.Pool:
        symbol = _children(symbol, "arguments")[0]
    fields = dict(symbol.items())
    if symbol.ast_type == ast.ASTType.Function:
        return (str(fields["name"]), len(_children(symbol, "arguments")))
    if symbol.ast_type == ast.ASTType.SymbolicTerm:
        return (str(fields["symbol"]), 0)
    return None


def _walk(node: ast.AST, in_head: bool, defined: set[Signature], used: set[Signature]) -> None:
    """Collect the predicates under `node`, as defined (`in_head`) or used.

    A conditional literal in a head, such as `{ pivot(L) : var(L) }`, defines its literal and
    uses its condition.
    """
    if node.ast_type == ast.ASTType.SymbolicAtom:
        sig = _signature(_one(node, "symbol"))
        if sig is not None:
            (defined if in_head else used).add(sig)
        return
    if node.ast_type == ast.ASTType.ConditionalLiteral and in_head:
        _walk(_one(node, "literal"), True, defined, used)
        for lit in _children(node, "condition"):
            _walk(lit, False, defined, used)
        return
    for key in node.child_keys:
        for child in _children(node, key):
            _walk(child, in_head, defined, used)


def predicates(text: str) -> tuple[set[Signature], set[Signature]]:
    """The predicates a program defines (in a rule head) and uses (anywhere else)."""
    defined: set[Signature] = set()
    used: set[Signature] = set()

    def rule(stm: ast.AST) -> None:
        if stm.ast_type == ast.ASTType.Rule:
            _walk(_one(stm, "head"), True, defined, used)
            for lit in _children(stm, "body"):
                _walk(lit, False, defined, used)

    ast.parse_string(text, rule)
    return defined, used


def header_list(text: str, label: str) -> set[Signature]:
    """The signatures after `**label:**` in a file's header comment, up to the next bullet."""
    header = text.split("\n\n%")[0] if text.startswith("%#") else ""
    match = re.search(rf"\*\*{label}:\*\*(.*?)(?=\n% - \*\*|\Z)", header, re.DOTALL)
    if match is None:
        return set()
    return {(name, int(arity)) for name, arity in SIGNATURE.findall(match.group(1))}


def arity(args: str | None) -> int:
    """The arity of a doc block header's argument list, `A, B` or none."""
    return 0 if not args else len([a for a in args.split(",") if a.strip()])


def _union(sets: Iterable[set[Signature]]) -> set[Signature]:
    """The union of `sets`, typed (`set().union()` is a set of unknowns)."""
    out: set[Signature] = set()
    for s in sets:
        out |= s
    return out


FILES = {name: (LP / name).read_text() for name in PROGRAM_FILES}
PARSED = {name: predicates(text) for name, text in FILES.items()}
DEFINED_ANYWHERE = _union(d for d, _ in PARSED.values())


def test_every_defined_predicate_has_one_doc_block() -> None:
    blocks: dict[Signature, list[str]] = defaultdict(list)
    for name, text in FILES.items():
        for m in DOC_BLOCK.finditer(text):
            blocks[(m.group(1), arity(m.group(2)))].append(name)
    assert {s: f for s, f in blocks.items() if len(f) > 1} == {}, "documented twice"
    assert sorted(DEFINED_ANYWHERE - blocks.keys()) == [], "defined but undocumented"
    assert sorted(blocks.keys() - DEFINED_ANYWHERE) == [], "documented but not defined"
    for sig, (name,) in blocks.items():
        assert sig in PARSED[name][0], f"{sig} is documented in {name}, which does not define it"


@pytest.mark.parametrize("name", PROGRAM_FILES)
def test_summary_sentence_is_whole(name: str) -> None:
    # clindocs' predicate table shows a block up to its first full stop, so a dot inside the
    # first sentence (`due2-profiles.md`, `e.g.`) cuts the summary short.
    for m in DOC_BLOCK.finditer(FILES[name]):
        body = m.group(3).strip()
        end = body.find(".")
        assert end > 0, f"{m.group(1)}: no summary sentence"
        after = body[end + 1 : end + 2]
        assert after in ("", " ", "\n"), f"{m.group(1)}: summary cut at {body[: end + 1]!r}"


@pytest.mark.parametrize("name", PROGRAM_FILES)
def test_header_lists_match_the_rules(name: str) -> None:
    defined, used = PARSED[name]
    provides = header_list(FILES[name], "Provides")
    consumes = header_list(FILES[name], "Consumes")
    # A file that extends a relation an earlier file defines (pivot.lp's assigned/3) and reads
    # it consumes it too.
    earlier = PROGRAM_FILES[: PROGRAM_FILES.index(name)]
    extended = defined & _union(PARSED[e][0] for e in earlier)
    read = used - (defined - extended)
    assert sorted(defined - provides) == [], "defined here but not in Provides"
    assert sorted(provides - defined) == [], "in Provides but not defined here"
    assert sorted(read - consumes) == [], "used here but not in Consumes"
    assert sorted(consumes - read) == [], "in Consumes but not used here"


def test_inputs_are_documented_in_design() -> None:
    used_anywhere = _union(u for _, u in PARSED.values())
    design = (ROOT / "DESIGN.md").read_text()
    inputs = sorted(used_anywhere - DEFINED_ANYWHERE)
    assert [f"{n}/{a}" for n, a in inputs if f"`{n}/{a}`" not in design] == []


def test_docs_entry_point_includes_the_program_in_order() -> None:
    text = (ROOT / "docs" / "program.lp").read_text()
    includes = re.findall(r'#include\s+"\.\./lp/([\w.]+)"\.', text)
    assert includes == list(PROGRAM_FILES)


# A section reference is anchored when a document name comes before it: `due2-workflows.md §6.4`,
# a chain such as `due2-workflows.md §3.5, §6.2` or a range with an en dash, or an
# external specification.
_SECTION = r"§(?:\s[A-Z][\w-]*(?:\s[\w-]+)*|[\w.]*\w)(?:\s\*\*\[D\]\*\*)?(?:\s#\d+)?"
_CHAIN = r"(?:(?:,\s*|\sand\s|\sto\s|[\u2013-])" + _SECTION + r")*"
ANCHORED = re.compile(
    r"(?:\S+\.md`?|IM 2\.2|XSD 1\.1 Part \d|RDF Schema 1\.1)[\s%#]+" + _SECTION + _CHAIN,
)
DOCUMENTED = [
    "DESIGN.md",
    "TESTS.md",
    "main.py",
    *(f"lp/{n}" for n in PROGRAM_FILES),
    *(str(p.relative_to(ROOT)) for p in sorted((ROOT / "clingo_i").glob("*.py"))),
    *(str(p.relative_to(ROOT)) for p in sorted((ROOT / "tests").glob("*.py"))),
    *(str(p.relative_to(ROOT)) for p in sorted((ROOT / "docs").glob("*.md"))),
]


@pytest.mark.parametrize("path", DOCUMENTED)
def test_no_bare_section_reference(path: str) -> None:
    text = (ROOT / path).read_text()
    masked = ANCHORED.sub(lambda m: "x" * len(m.group()), text)
    bare = [
        text.splitlines()[masked.count("\n", 0, m.start())].strip()
        for m in re.finditer(r"§\s?\d", masked)
    ]
    assert bare == []
