#!/bin/env bash
# The following env variables need to be set for this script to work properly,
# as the defaults provided are unlikely to work:
#   MINA_DIR - the path to the mina source code
#   BLOCK_DIR - the path to the directory where the generated blocks will be output
#   SUBMISSION - the path to the dummy submission file
# A dummy submission required to pass blocks through stateless verifier
# in order to obtain state hashes.
# NOTE: all paths should be absolute, or else the stateless verifier gets
# confused and fails to load files.

if [[ -n "$MINA_DIR" ]]; then
  MINA_DIR="$(realpath "$MINA_DIR")" 
else
  MINA_DIR="$(dirname "$0")/../mina"
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
  $MINA_DIR/_build/default/src/app/dump_blocks/dump_blocks.exe \
    -o bin:"$BLOCK_DIR/$dummy_hash.dat" --full "${args[@]}"
}

function get_state_hash() {
  $MINA_DIR/_build/default/src/app/delegation_verify/delegation_verify.exe \
    fs --block-dir "$BLOCK_DIR" --no-check \
    "$SUBMISSION" \
    | jq -r .state_hash
}

mkdir -p "$BLOCK_DIR"
cd $MINA_DIR
generate_block_after  # first block in the chain

current_block="$(get_state_hash)"
echo "$current_block" > "$BLOCK_DIR/block_list.txt"

while [[ "$block_count" -gt 0 ]]; do
  generate_block_after "$current_block"
  current_block="$(get_state_hash)"
  echo "$current_block" >> "$BLOCK_DIR/block_list.txt"
  mv -v "$BLOCK_DIR/$dummy_hash.dat" "$BLOCK_DIR/$current_block.dat"
  block_count="$((block_count - 1))"
done

echo "*** Generated blocks: ***"
cat "$BLOCK_DIR/block_list.txt"
