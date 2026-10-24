#!/bin/sh
# Runs every command of the Alloy models given, or of all models here, and prints one line per
# command with its outcome and time. Alloy is the Maven artifact
# org.alloytools:org.alloytools.alloy.dist, checked by digest before use. The jar is taken from the
# local Maven repository when Maven has fetched it; otherwise it is downloaded once into a cache,
# from $DUE2_MAVEN_REPO (default Maven Central) with any credentials in ~/.netrc.
#
#   formal/alloy/run.sh [model.als ...]
#
# Needs Java 17 or later and curl. The solutions go to $TMPDIR/due2-alloy/<model>/. The SAT solver
# is $DUE2_ALLOY_SOLVER (default sat4j, pure Java); glucose and minisat are native and often faster.
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

if [ $# -eq 0 ]; then
  set -- "$here"/*.als
fi

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
done
