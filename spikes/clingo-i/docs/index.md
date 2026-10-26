# clingo-i

The spike `clingo-i` implements due2's `interpret` as a generic clingo program over flattened
ODRL (`decisions/0009`): a Python driver flattens the vector's policy to facts, and the program
derives the verdict and its explanation.

- [The semantics program](program.md): every relation of `lp/`, with its arguments, where it is
  defined and used, and the source.
- [The driver](python.md): the Python modules that flatten the input, run the solves, and build
  the reply, with the input facts (`flatten.py`) and the value table (`values.py`).

The design, its vocabulary, and a worked example are in `DESIGN.md`, beside this directory. Build
this site with `uv run --group docs mkdocs build --strict` in `spikes/clingo-i`; the output goes
to `site/`, which is not committed.
