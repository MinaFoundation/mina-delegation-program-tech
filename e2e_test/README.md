Uptime service end-to-end test
==============================

A blockchain is a hairy process, involving a lot of peer-to-peer
networking, distributing blocks and transactions, selecting block
producers, resolving forks and so forth. Any process involving a real
blockchain is inherently irreproducible. On top of that, Mina nodes
take a considerable time to start and synchronise. All this would slow
down the test.

In order to avoid these issues, we mock the network with a Python
script which will send submissions on behalf of some imaginary block
producers, containing blocks of some imaginary, dummy blockchain.
Because we don't want to depend on a node to generate these blocks,
we need to generate them beforehand.

Step 1. Block generation
------------------------

Use the script in `dummy_blockchain` directory to generate a dummy blockchain.

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

Use the `generate_submissions.py` script in `blockchain_mock` directory.
