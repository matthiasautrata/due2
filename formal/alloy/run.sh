#!/bin/sh
# Runs every command of the Alloy models given, or of all models here, and prints one line per
# command with its outcome and time. Alloy is fetched once into a cache and checked by digest.
#
#   formal/alloy/run.sh [model.als ...]
#
# Needs Java 17 or later and curl. The solutions go to $TMPDIR/due2-alloy/<model>/.
set -eu

version=6.2.0
digest=6b8c1cb5bc93bedfc7c61435c4e1ab6e688a242dc702a394628d9a9801edb78d
cache=${XDG_CACHE_HOME:-$HOME/.cache}/due2/alloy-$version
jar=$cache/org.alloytools.alloy.dist.jar
here=$(cd "$(dirname "$0")" && pwd)

if [ ! -f "$jar" ]; then
  mkdir -p "$cache"
  curl -fsSL -o "$jar.part" \
    "https://github.com/AlloyTools/org.alloytools.alloy/releases/download/v$version/org.alloytools.alloy.dist.jar"
  mv "$jar.part" "$jar"
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
  java --enable-native-access=ALL-UNNAMED -jar "$jar" exec -f -o "$out/$name" -t text "$model" 2>&1 |
    grep -E '^[0-9]+\. '
done
