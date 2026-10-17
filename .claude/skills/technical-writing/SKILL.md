---
name: technical-writing
description: Write and review due2's documentation and code comments for a cold reader, under ways-of-working.md §15. Use it whenever you write or revise any Markdown in this repo (spec, design note, decision record, README, corpus notes, an issue or PR body) or any code comment or docstring (Python, clingo/ASP), and whenever the user asks to review, clarify, explain, or improve docs or comments, even if they do not say "technical writing".
---

# Technical writing for due2

The rules are in `docs/correctness/ways-of-working.md` §15, and you must read it first. This skill is the procedure for applying them, the templates, and the review checklist.

The failure this skill exists to prevent is text written as a reminder by someone who holds the whole context: correct, terse, and impossible to follow cold. Every check below asks the same question: can a reader who has only the repository re-derive this?

## Procedure

1. **Name the reader and the kind.** Who opens this file, and what do they want? Is the passage reference, explanation, how-to, or a worked example (§15.2)? If it is status, it goes in README § Status, `CLAUDE.md` § Next, the issue, or the spike journal, not here.
2. **Inventory the vocabulary.** List every term and relation name the text uses. Each one is defined by the spec (cite the section), defined in this document's vocabulary, or self-explaining. A term with two senses gets a qualifier on one of them, every time (§15.3).
3. **Write the interface before the mechanism.** Say what goes in and what comes out, including sentinels and invariants, then how the mechanism works (§15.4).
4. **Walk one real input through.** Run the code on a small input and copy what it actually derives. Don't reconstruct it from memory. Add a test that pins the example's input and result (§15.5).
5. **Give each argument its steps.** For every "so", "therefore", "cannot", "exact", or "sound", write out the premises and the inference. For each test, state the risk it guards and what got through without it (§15.6).
6. **Anchor every reference.** Write `due2-workflows.md §6.4`, not `§6.4` (§15.7).
7. **Comment the code** with the templates below (§15.8).
8. **Build the generated reference** where there is one (clingo-i: `uv run --group docs mkdocs build --strict` in `spikes/clingo-i/`), and look at the pages you changed (§15.10).
9. **Run the checklist**, then README § Verify.

## Review checklist

When asked to review documentation, report findings against these items with file and line. Don't rewrite until the user asks.

- [ ] **Cold read.** Read the text as if you had only the repository, and mark every sentence whose claim you could not re-derive from it and its citations.
- [ ] **No status in reference.** No "increment N", "now", "for now", "this increment", "yet", or "lands with" in reference text, except a decline or open item that names its issue.
- [ ] **Vocabulary.** Every coined term is defined, every relation the code defines appears in the document, and no word has two unqualified senses.
- [ ] **Letters.** Each variable letter in a program has one kind, and the program states its letter table.
- [ ] **Interfaces.** Each file, module, and public function states what it consumes, what it provides, and why, including sentinels.
- [ ] **Example.** A mechanism has at least one worked example from a real run, pinned by a test.
- [ ] **Arguments.** Every soundness, exactness, or impossibility claim shows its steps, and every test states its counterfactual.
- [ ] **References.** No bare `§N` points into another document.
- [ ] **Comments.** Comments mark idioms, tricks, sentinels, and reasons, and none paraphrases its line.
- [ ] **Compression where it belongs.** Tables, code lists, and decline lists stay compact (§15.9). Don't pad them.
- [ ] **House style.** A paragraph is one line (rumdl, `MD013` off). Use sentence-case headings, the present tense, the active voice, and code font for names. Cite documents by bare file name.

You can measure some of this directly:

```bash
rg -n '§\s?[0-9]' FILE | rg -v '\.md §|decisions/[0-9]{4}'   # candidate bare § references
rg -n -i 'increment [0-9]|for now|this increment|lands with' FILE  # candidate status in reference
```

For clingo-i, `tests/test_docs.py` checks the doc blocks, their summary sentences, the header lists, the input facts in `DESIGN.md`, and the references (§15.10). The MkDocs build checks that every docstring and doc block renders.

## Templates

### ASP file header and predicate block

From `spikes/clingo-i/lp/applies.lp`:

```prolog
%# applies.lp: the parts of an atom, and its finding
%
% Splits each atom into parts, gives each part a truth value against the request, and derives
% the atom's finding, the Kleene conjunction of its parts (due2-workflows.md §5.2). A request
% field that is absent makes its part `u`, never `f`. Variable letters: DESIGN.md § Vocabulary.
%
% - **Consumes:** `atom/1`, `atom_action/2`, `atom_target/2`, `atom_party/3` (structure.lp);
%   `request_action/1`, `request_target/1`, `request_absent/1`, `request_party/2` (driver);
%   `closure/3` (lift.lp); `rank/2` (kleene.lp).
% - **Provides:** `part_of/2`, `item/1`, `reaches/2`, `action_matches/1`, `named/1`, `holds/2`.

%*! holds(I, V)

Item `I` has truth value `V`: `f`, `u`, or `t`. For `applies(X)` this is atom `X`'s finding.
It is the value before completion; completion.lp gives each world's value.
*%
```

- The header's first line is `%#`, which clindocs renders as the page title. `%##` lines are sections. `%%` lines are hidden from the reference.
- **Consumes** and **Provides** are Markdown bullets, and each relation is `` `name/arity` ``, so `tests/test_docs.py` can match them against the rules.
- A doc block goes next to the first rule that defines the predicate. A predicate defined in several files has one block, in the first file of `PROGRAM_FILES` that defines it. A later file that extends it lists it under both **Consumes** and **Provides**.
- The block's header is the predicate with named arguments. Name each argument after its kind from the letter table (`W` world, `V` truth value). Leave a blank line after the header.
- The first sentence is the summary clindocs' predicate table shows, cut at the first full stop. Keep dotted names (`kleene.lp`, `e.g.`) out of it.
- An implementation comment sits on the line above the rule it explains, and says what a fluent clingo reader would miss:

```prolog
% The Kleene conjunction of the parts. `#min` is used as a function: `Min` is the least rank
% among the atom's parts, and `V` is the value of that rank. Every atom has an action and a
% target part, so the set is never empty. If it were, `#min` would be `#sup`, no rank would
% match it, `applies(X)` would have no value, and the item constraint in kleene.lp would fail.
holds(applies(X), V) :- atom(X), rank(V, Min),
    Min = #min { N : part_of(X, I), holds(I, Vp), rank(Vp, N) }.
```

### Python module and function

From `spikes/clingo-i/clingo_i/`. The summary names what a function returns; a module docstring says what goes in and what comes out.

```python
"""The interpret task: three solves, the declines, and the reply.

`Interpreter.reply` takes one vector (`conformance/README.md`) and returns the reply of
`spikes/README.md` § `interpret`: an output, a decline, or an error. ...
"""


def _solve(self, facts: str, files: tuple[str, ...], mode: str) -> list[Symbol]:
    """Solves 2 and 3: the shown atoms true in every model (cautious) or in some (brave).

    clingo reports the consequences of the enumeration so far with each model, so the last
    model's atoms are the final answer.

    Raises:
        Declined: More than `VARIABLE_CAP` completion variables after grounding.
        RuntimeError: No model: an integrity constraint failed.
    """
```

### A design note (`spikes/<name>/DESIGN.md`)

Use this section order. Skip any section that would be empty.

1. **What this is**: one paragraph covering what the component does, who reads this note, where the generated reference is, and where status lives instead.
2. **Vocabulary**: coined terms, and the program's letter table.
3. **Layout**: one line per file.
4. **Data flow**: the stages, in order.
5. **Worked example**: one input followed through every stage, pinned by a test.
6. **Interfaces**: the input facts, then, for each file, what it consumes, what it provides (with meanings), and its semantics with their arguments.
7. **Output**, **Declines**, **Errors**: compact.
8. **Tests**: for each test, the risk it guards and its counterfactual.

## Sources

The rules come from Diátaxis (kinds of text), PEP 257 and the Google Python Style Guide (docstrings), Ousterhout's *A Philosophy of Software Design* (interface and implementation comments; comments describe what the code cannot), the Google developer documentation style guide (voice, tense, terminology), Knuth's literate programming (programs are written to be read), and potassco's clindocs (the ASP doc-block format). They are annotated in `docs/design/references.md` §5.
