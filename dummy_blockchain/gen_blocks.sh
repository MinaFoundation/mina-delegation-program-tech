#!/bin/env bash
# The following env variables need to be set for this script to work properly,
# as the defaults provided are unlikely to work:
#   DELEGATION_VERIFY - the path to the stateless verifier binary
#   DUMP_BLOCKS - the path to the dump blocks tool
#   BLOCK_DIR - the path to the directory where the generated blocks will be output
#   SUBMISSION - the path to the dummy submission file
# A dummy submission required to pass blocks through stateless verifier
# in order to obtain state hashes.
#
# If there is a source code for Mina on the machine and it has delegation_verify
# and dump_blocks apps compiled, it is possible to provide MINA_DIR variable
# pointing to the root of the source directory rather than specify binary paths
# directly.

# NOTE: all paths should be absolute, or else the stateless verifier gets
# confused and fails to load files.
if [[ -n "$MINA_DIR" ]]; then
  MINA_DIR="$(realpath "$MINA_DIR")" 
else
  MINA_DIR="$HOME/work/mina"
fi
if [[ -n "$DELEGATION_VERIFY" ]]; then
  DELEGATION_VERIFY="$(realpath "$DELEGATION_VERIFY")"
else
  DELEGATION_VERIFY="$MINA_DIR/_build/default/src/app/delegation_verify/delegation_verify.exe"
fi
if [[ -n "$DUMP_BLOCKS" ]]; then
  DUMP_BLOCKS="$(realpath "$DUMP_BLOCKS")"
else
  DUMP_BLOCKS="$MINA_DIR/_build/default/src/app/dump_blocks/dump_blocks.exe"
fi
if [[ -n "$BLOCK_DIR" ]]; then
  BLOCK_DIR="$(realpath "$BLOCK_DIR")"
else
  BLOCK_DIR="$(realpath blocks)"
fi
if [[ -n "$SUBMISSION" ]]; then
  SUBMISSION="$(realpath "$SUBMISSION")"
else
  SUBMISSION="$(realpath "$(dirname "$0")/dummy-submission.json")"
fi
if ! [[ -f "$SUBMISSION" ]]; then
  echo "Submission file not found!" > /dev/stderr
  exit 1
fi

if [[ -z "$1" ]]; then
  block_count=20
else
  block_count="$1"
fi
dummy_hash="dummy"

# If an argument is provided, it's assumed to be the state hash of
# the parent block. Otherwise, the parent state hash is generated at
# random.
function generate_block_after() {
  if [[ -z "$1" ]]; then
    args=()
  else
    args=("--parent" "$1")
  fi
  $DUMP_BLOCKS -o bin:"$BLOCK_DIR/$dummy_hash.dat" --full "${args[@]}"
}

function get_state_hash() {
  $DELEGATION_VERIFY fs --block-dir "$BLOCK_DIR" --no-check "$SUBMISSION" \
    | jq -r .state_hash
}

mkdir -p "$BLOCK_DIR"
cd $MINA_DIR
generate_block_after  # first block in the chain

current_block="$(get_state_hash)"
mv -v "$BLOCK_DIR/$dummy_hash.dat" "$BLOCK_DIR/$current_block.dat"
echo "$current_block" > "$BLOCK_DIR/block_list.txt"
block_count="$((block_count - 1))"

while [[ "$block_count" -gt 0 ]]; do
  generate_block_after "$current_block"
  current_block="$(get_state_hash)"
  echo "$current_block" >> "$BLOCK_DIR/block_list.txt"
  mv -v "$BLOCK_DIR/$dummy_hash.dat" "$BLOCK_DIR/$current_block.dat"
  block_count="$((block_count - 1))"
done

echo "*** Generated blocks: ***"
cat "$BLOCK_DIR/block_list.txt"
