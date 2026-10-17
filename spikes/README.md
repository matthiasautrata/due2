# Spikes

A spike is a candidate implementation, built to be compared. Spikes share one thing: the pinned vectors and their expected results, read from `conformance/` by one Python suite (`tests/`, harness in `tools/harness/`). Everything else is separate. Each spike is built from the same principles and requirements and judged by the same gate, and in the end their code and scores are compared (`decisions/0006` §5).

The first spike is `clingo-i`, the semantics program (issue #9, `decisions/0009`), implementing `interpret` over the corpus — the L9 oracle's role. The W2/W3 bakeoff spikes follow: #41 Clingo (possibly the same program's relation-level face, `decisions/0009` #8) and #40 Elixir first; #39 Python is deferred until the production evaluator is written.

## Rules

- **Tests first, written once.** The suite is Python and is shared. A spike adds no tests of its own to the shared suite, and it never changes a vector or an expected result to make itself pass. A vector it cannot meet without changing semantics is a finding: record it in the journal (`note`, with `--vector`) and in an issue. It is never a spec change (`decisions/0006` §4).
- **Same inputs.** A spike reads the spec (`docs/`) and the vectors. It does not read another spike's code until the comparison.
- **Text in, text out.** Every input and output is JSON or Turtle text. Nothing passes between the harness and a spike except the line protocol below.
- **Isolated.** A spike lives entirely under `spikes/<name>/`, with its own toolchain, lockfile, and checkers. Repo-level ruff and basedpyright skip `spikes/`, and the spike declares its own checkers instead.
- **Recorded.** `journal.jsonl` and `scorecard.json` are committed with the code they describe.

## Layout

```text
spikes/<name>/
    backend.toml     how to run and check the spike (below)
    journal.jsonl    effort, attempts, rewrites, bugs, checker and test runs; append-only
    scorecard.json   the last full test run; overwritten
    .stderr.log      the backend's stderr; not committed
    ...              the spike's own code, build files, lockfile
```

`backend.toml`:

```toml
command = ["uv", "run", "python", "main.py"]   # run with spikes/<name>/ as working directory
sources = ["src/**/*.py"]                      # globs: the code that counts as the spike's size

[[check]]                                      # one per compiler, type checker, or linter
name = "basedpyright"
command = ["uv", "run", "basedpyright"]
count = ' - (error|warning): '                 # regex; each matching output line is one diagnostic
```

Match the checker's own diagnostic form, not a bare `warning:`: the tool's own warnings (uv's `VIRTUAL_ENV` mismatch, for one) would count too.

Without `count`, a nonzero exit counts as one diagnostic.

## Protocol

The harness starts `command` once per test run and talks JSON lines over stdin and stdout, one request at a time. stderr goes to `.stderr.log`.

```text
-> {"init": {"modules": {path: text}, "core": [path], "profiles": {profile IRI: [path]}}}
<- {"ready": {"tasks": ["interpret"]}}
-> {"id": "<case>/<scenario>", "task": "interpret", "input": {...}}
<- {"id": "<case>/<scenario>", "output": {...}}   or   {"id": ..., "error": "..."}
                                                 or   {"id": ..., "unsupported": "<feature>"}
```

`init` carries every shipped profile module once: `core` is always loaded, and `profiles` lists the modules a policy's `odrl:profile` IRI selects (`tools/check_corpus.py` `CORE`, `MODULES`). `ready.tasks` declares what the spike implements. A task it does not declare is reported as unsupported, never as a pass. A spike that declares a task but cannot yet meet one vector declines it with `unsupported` and names the feature (`"recurrence"`, `"deadline"`): the vector is reported unsupported with that reason, never as a pass, and the same reply must come on every repeat. Declining is how a spike grows by increments (`ways-of-working.md` §14) and still runs green: every vector it does answer must pass. A spike declines only a feature it does not implement, and the scorecard's unsupported count shows the rest. A crash, a timeout (60 s per call, 120 s to `ready`), or a reply with the wrong `id` counts as an error, and the harness restarts the backend.

### `interpret`

One vector per positive scenario in `conformance/cases/` (negative cases wait for W1). Input:

```json
{"case": "...", "scenario": "...", "policy": "<policy.ttl text>", "prefixes": {"odrl": "..."},
 "request": {...}, "sotw": {...}, "config": {...}}
```

`request`, `sotw`, and `config` are exactly as in `case.json` (`conformance/README.md`). Output:

```json
{"verdict": "Pending",
 "frontier": [["<duty IRI>", "..."], ["..."]],
 "obligations": [{"duty": "<IRI>", "status": "outstanding", "instance": "<dateTime>"}],
 "exact": true,
 "verdict_basis": [{"ref": "<rule or duty IRI>", "role": "permission"}],
 "eliminated": [{"ref": "<IRI>", "by": "<IRI>", "rule": "prohibit"}],
 "verdict_range": {"low": "NotApplicable", "high": "Permit"},
 "unknown_parts": [{"ref": "<rule IRI>", "input": "<IRI>", "status": "missing"}]}
```

The verdict is one of the five. The frontier is a set of alternatives, each a set of duty IRIs. Obligations are a set; `status` is `fulfilled`, `outstanding`, `violated`, or `unknown`, and `instance` is present only for an instance of a recurring duty. `exact` is compared only for scenarios that state it. `verdict_basis` and `eliminated` are the explanation at the authored level (`conformance/README.md`, workflows §3.7), each a set, and both optional. `verdict_range` is an `Indeterminate`'s least and greatest completion verdict (`decisions/0011`), also optional. `unknown_parts` is every `U` part of every rule, under any verdict, as a set: the input it reads and that input's status (`decisions/0016`, `conformance/README.md`), also optional. Each is compared when the scenario states it and the output has it. A vector whose output matches but lacks a field the scenario states is reported unsupported (`not emitted: verdict_basis`), never as a pass. A spike that emits none of them yet still runs green, and grows into them by increment. Names may be full IRIs or use the vector's prefixes.

### `w2`, `w3`

Reserved for the bakeoff's relation-level vectors. Their format is issue #36, and it is written before any spike implements them.

## Running

```bash
uv run pytest --backend=<name>                         # every vector; failures shown per vector
uv run pytest --backend=<name> -k "<case>"             # some vectors; never writes a scorecard
uv run pytest --backend=<name> --scorecard --repeat=5  # the recorded run: median of 5 calls per vector
uv run pytest --backend=all --scorecard                # every spike
```

The plain `uv run pytest` of README § Verify runs only the harness's own tests. They show that a backend returning the expected results passes every vector, and that one returning nothing fails every vector.

## What is recorded

**Scorecard** (`pytest --scorecard`, full runs only):

- the revision (`+dirty` if uncommitted) and the machine;
- startup time, from spawn to `ready`, which includes loading the profile modules;
- per task: pass, fail, error, and unsupported counts, plus total, p50, p95, p99, and max latency;
- per vector: status, latency, and the first mismatch or error.

Latency is wall clock, from writing the request to reading the reply, measured by the harness the same way for every backend.

**Journal** (`uv run python tools/spike_journal.py`, plus one `run` entry per scorecard):

| Kind | Log it when | Fields |
|---|---|---|
| `session` | a stretch of work ends | `--minutes`, `--by` (a person or a model id) |
| `attempt` | a new approach replaces one that did not work (not each edit) | `--vector` if it targets one |
| `rewrite` | a component is thrown away and redone | |
| `bug` | a defect turns up after the code was believed right | `--vector` if a vector found it |
| `note` | a finding, a spec question, a vector the spike cannot meet | `--vector` |
| `check` | written by `spike_journal.py check <name>`: each checker's exit code and diagnostic count | |
| `run` | written by `pytest --scorecard`: the task summary | |

Run `check` at the end of every session, so the journal shows how the compiler and checker complaints evolve, not just where they end up.

```bash
uv run python tools/spike_journal.py log clingo-i session "completion over literals" --minutes 90 --by claude-opus-5-5
uv run python tools/spike_journal.py log clingo-i bug "guarded duty counted as unguarded" --vector "<case>/<scenario>"
uv run python tools/spike_journal.py check clingo-i
uv run python tools/spike_journal.py summary          # Markdown table, one row per spike
```

## Comparison

`summary` gives the measurable columns: source lines, effort, attempts, rewrites, bugs, test runs, diagnostics (all-time and current), pass rate, latency, and startup. The bakeoff's first scoring criteria (trace fidelity, how `U` and the verdicts are represented, reviewability; `decisions/0006` §5) are judged by reading the code. That comparison, with its table, lands as a decision record.
