Generate dummy blockchain
=========================

For this script we require 2 apps from Mina repository. In particular
we will use:

* `dump_blocks` app to generate dummy blocks
* `delegation_verify` app to extract state hashes from generated
  blocks

Both these apps are handled automatically by the provided `gen_blocks.sh`
script (they must be compiled manually, though). For the script to work
the following env variables should be set:

* `DELEGATION_VERIFY` - the path to the stateless verifier binary
* `DUMP_BLOCKS` - the path to the dump blocks tool.
* `BLOCK_DIR` - the path to the directory where the generated blocks will be output
* `SUBMISSION` - the path to the dummy submission file

The script can be used as follows:

    $ BLOCK_DIR=/home/user/blocks ./gen_block.sh <number of blocks to generate>

If source code for Mina is present in the file system, `DELEGATION_VERIFY`
and `DUMP_BLOCKS` paths can be replaced with `MINA_DIR` containing a path
to the root of the source code repository. Required apps still have to be
compiled by hand.
