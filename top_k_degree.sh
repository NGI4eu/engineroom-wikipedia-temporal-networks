#!/usr/bin/env bash
# shellcheck disable=SC2128
SOURCED=false && [ "$0" = "$BASH_SOURCE" ] || SOURCED=true

input_file=''
mode=''
output_dir=''
k=10
debug=false

read -rd '' docstring <<EOF
Usage:
  top_k_degree.sh [options] [-k <top_k>] ( --mode in | --mode out ) \
<input_file> <output_dir>
  top_k_degree.sh ( -h | --help )
  top_k_degree.sh ( --version )

  Arguments:
  --mode ( in | out )   Calculate indegree ('in') or outdegree ('out').
  <input_file>                    File to process.

  Options:
  -d, --debug           Enable debug mode.
  -k <top_k>            Print top-k results [default: 10].
  -h, --help            Show this help message and exits.
  --version             Print version and copyright information.
----
top_k_degree.sh 0.1.0
copyright (c) 2018 Cristian Consonni
MIT License
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.
EOF

eval "$(echo "$docstring" | docopts -V - -h - : "$@" )"

# bash strict mode
if ! $SOURCED; then
  set -euo pipefail
  IFS=$'\n\t'
fi

tmpdir=$(mktemp -d -t tmp.XXXXXXXXXX)
function finish {
  rm -rf "$tmpdir"
}
trap finish EXIT

#################### Utils
if $debug; then
  echodebug() { 
    echo -en "[$(date '+%F_%k:%M:%S')][debug]\\t"
    echo "$@" 1>&2;
  }
else
  echodebug() { true; }
fi
####################

echodebug "input_file: $input_file"
echodebug "output_dir: $output_dir"
echodebug "top_k: $k"
echodebug "mode: $mode"

head -n1 "$input_file" > "$tmpdir/header"

input_name="$(basename "$input_file")"

if [[ "$mode" == 'in' ]]; then
  output_name=$(echo "$input_name" | sed -re 's/(.*)\.csv/\1.in.csv/')

  tail -n+2 "$input_file" | awk '{print $2}' \
                          | sort \
                          | uniq -c \
                          | sort -k 1 -nr \
                          | head -n "$k" > "$output_dir/$output_name"

else
  output_name=$(echo "$input_name" | sed -re 's/(.*)\.csv/\1.out.csv/')

  tail -n+2 "$input_file" | awk '{print $1}' \
                          | sort \
                          | uniq -c \
                          | sort -k 1 -nr \
                          | head -n "$k" > "$output_dir/$output_name"
fi
