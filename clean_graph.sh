#!/usr/bin/env bash
# shellcheck disable=SC2128
SOURCED=false && [ "$0" = "$BASH_SOURCE" ] || SOURCED=true

if ! $SOURCED; then
  set -euo pipefail
  IFS=$'\n\t'
fi

tmpdir=$(mktemp -d -t tmp.XXXXXXXXXX)
function finish {
  rm -rf "$tmpdir"
}
trap finish EXIT


input_file="$1"
input_name="$(basename "$input_file")"

output_dir="$2"

head -n1 "$input_file" > "$tmpdir/header"
tail -n+2 "$input_file" | sort \
                        | uniq \
                        | awk '$1 != $2 {print $0}' \
                           > "$tmpdir/data"

cat "$tmpdir/header" "$tmpdir/data" > "$output_dir/clean_$input_name"
