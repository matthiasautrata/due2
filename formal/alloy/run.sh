#!/bin/sh
# Runs every command of the Alloy models given, or of every model here that has commands, and
# prints one line per command with its outcome and time. Each command states the outcome it
# expects: `expect 1`, an instance or a counterexample exists; `expect 0`, none does. The script
# exits 1 when a command states none or its outcome differs. Alloy is the Maven artifact
# org.alloytools:org.alloytools.alloy.dist, checked by digest before use. The jar is taken from the
# local Maven repository when Maven has fetched it; otherwise it is downloaded once into a cache,
# from $DUE2_MAVEN_REPO (default Maven Central) with any credentials in ~/.netrc.
#
#   formal/alloy/run.sh [model.als ...]
#
# Needs Java 17 or later, curl, and python3. The solutions go to $TMPDIR/due2-alloy/<model>/. The
# SAT solver is $DUE2_ALLOY_SOLVER (default sat4j, pure Java); glucose and minisat are native and
# often faster.
set -eu

version=6.2.0
digest=6037cbeee0e8423c1c468447ed10f5fcf2f2743a2ffc39cb1c81f2905c0fdb9d
path=org/alloytools/org.alloytools.alloy.dist/$version/org.alloytools.alloy.dist-$version.jar
repo=${DUE2_MAVEN_REPO:-https://repo1.maven.org/maven2}
here=$(cd "$(dirname "$0")" && pwd)

jar=$HOME/.m2/repository/$path
if [ ! -f "$jar" ]; then
  jar=${XDG_CACHE_HOME:-$HOME/.cache}/due2/$(basename "$path")
  if [ ! -f "$jar" ]; then
    mkdir -p "$(dirname "$jar")"
    curl -fsSL --netrc-optional -o "$jar.part" "$repo/$path"
    mv "$jar.part" "$jar"
  fi
fi
actual=$(shasum -a 256 "$jar" | cut -d' ' -f1)
if [ "$actual" != "$digest" ]; then
  echo "run.sh: $jar has digest $actual, expected $digest" >&2
  exit 1
fi

# A model with no commands, such as resolve.als, is a module that the others open and compile.
if [ $# -eq 0 ]; then
  for model in "$here"/*.als; do
    if grep -Eq '^(run|check) ' "$model"; then set -- "$@" "$model"; fi
  done
fi

# receipt.json gives the solutions each command found, and its `expects`: -1 when the command
# states none, and no key at all for `expect 0`.
compare='
import json, sys
status = 0
for name, command in json.load(open(sys.argv[1]))["commands"].items():
    want, found = command.get("expects", 0), 1 if command.get("solution") else 0
    if want != found:
        print(f"run.sh: {name} expects {want}, found {found}", file=sys.stderr)
        status = 1
sys.exit(status)
'
failed=0

out=${TMPDIR:-/tmp}/due2-alloy
for model in "$@"; do
  name=$(basename "$model" .als)
  echo "$name"
  log=$(java --enable-native-access=ALL-UNNAMED -jar "$jar" exec -f -s "${DUE2_ALLOY_SOLVER:-sat4j}" -o "$out/$name" -t text "$model" 2>&1) || true
  # A model that does not compile prints no command line: show Alloy's error instead.
  if ! printf '%s\n' "$log" | grep -E '^[0-9]+\. '; then
    printf '%s\n' "$log" | head -5 >&2
    exit 1
  fi
  python3 -I -c "$compare" "$out/$name/receipt.json" || failed=1
done
exit "$failed"
