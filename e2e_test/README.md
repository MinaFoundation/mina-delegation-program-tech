Uptime service end-to-end test
==============================

Step 1. Block generation
------------------------

A blockchain is a hairy process, involving a lot of peer-to-peer
networking, distributing blocks and transactions, selecting
block producers and so forth. Any process involving a real
blockchain is inherently irreproducible. On top of that, Mina
nodes take a considerable time to start and synchronise. All this
would slow down the test.

In order to avoid these issues, we mock the network with a Python
script which will send submissions on behalf of some imaginary block
producers, containing blocks of some imaginary, dummy blockchain.
Because we don't want to depend on a node to generate these blocks,
we need to generate them beforehand. For this step we require
Mina repository. In particular we will use:

* `dump_blocks` app to generate dummy blocks
* `delegation_verify` app to extract state hashes from generated
  blocks

Both these apps are handled automatically by the provided `gen_blocks.sh`
script (they must be compiled manually, though). For the script to work
the following env variables should be set:

* `MINA_DIR` - the path to the mina repository
* `BLOCK_DIR` - the path to the directory where the generated blocks will be output
* `SUBMISSION` - the path to the dummy submission file

The script can be used as follows:

    $ BLOCK_DIR=/home/user/blocks ./gen_block.sh <number of blocks to generate>
    
Step 2. Upload
--------------

Pre-generated blocks should be uploaded to s3, where the mock will be able
to access them. An example package of 120 consecutive blocks can be found
here: https://s3.console.aws.amazon.com/s3/buckets/673156464838-mina-precomputed-blocks?region=us-west-2&bucketType=general&prefix=uptime-service-e2e-test/.

The folder should contain any number of `*.dat` files, each of which
should contain a binary block, and whose name should consist of the
block's state hash and `.dat` filename extension. Additionally, the
directory should also contain a special file `block_list.txt`, which
lists all the block state hashes in order, that is each block on the list
is the parent of the block on the next line. This file is used by the
mock to submit blocks in the right order, so that the uptime service
can reconstruct the dummy blockchain correctly and award uptime points
accordingly.

Step 3. Running the mock
------------------------

This step requires an uptime-service already running. It should be configured
such that to does not verify signatures on submissions. We want to test the
logic of the uptime service, not signature verification. The mock is run
as follows:

    $ python generate_submissions.py --block-s3-dir <folder name> <uptime service URL>
    
The mock contains a list of 15 hard-coded public keys, which serve as
block producers' addresses. It loads the list of blocks at the given
address and forms the chain of state hashes. It also rotates the list
of block producers so that it never ends. It sets the block pointer to
the first block on the list.

Then every minute it picks up the next node and sends a submission
with the block currently pointed to by the block pointer. Every 3 minutes
it also moves the block pointer to the next block. This way every block
producer appears to make a submission every 15 minutes and each block
gets submitted by 3 distinct block producers.

These parameters can be tweaked using command line parameters:

* `--block-time` followed by an integer defines the interval in seconds
  after which the system proceeds to the next block.
* `--submission-time` followed by an integer defines the interval
  in seconds after which the system proceeds with the next submission.
  
The mock can also be run without downloading blocks from s3. In this case
`--block-s3-dir` parameter should be replaces with `--block-dir` pointing
to a local directory containing blocks as described above.
