Blockchain mock
===============

This script requires an uptime-service already running. It should be
configured such that it does not verify signatures on submissions. We
want to test the logic of the uptime service, not signature
verification. The mock is run as follows:

    $ python generate_submissions.py --block-s3-bucket <bucket> \
        --block-s3-dir <folder name> <uptime service URL>

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

The mock can also be run without downloading blocks from s3. In this
case `--block-s3-bucket` and `--block-s3-dir` parameters should be
replaces with `--block-dir` pointing to a local directory containing
blocks as described above.

The values of `--block-time` and `--submission-time` do not have any
formal constraints assigned to them, but they are expressed as an
integral number of seconds. Setting the `--submission-time` to 0
will cause the script to send submissions as fast as possible and
actual submission times will depend on machine's and network
connection's throughput, so it's not recommended.

`--block-time` is only checked before the next submission is going to
be made. For this reason setting it to a value smaller or equal to
`--submission-time` will have the effect that for every submission a
new block is picked. Every block will be submitted at least once
nonetheless, even if `--block-time` is much smaller than
`--submission-time`, so there is not really any point in choosing a
value smaller than `--submission-time`.

Note that choosing too low value of `--block-time` relative to
`--submission-time` may result in uptime service refusing to score any
points, because it expects to see the same blocks submitted by
multiple peers.
