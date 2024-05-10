"""This module generates submissions to the uptime service from an
imaginary blockchain. There are 15 block producers sending submissions
in 1-minute intervals from one another. This way every block on the
blockchain is submitted 3 times. These blocks are pre-generated and
SNARK work proofs in submissions are dummy, as they are not produced
on a real blockchain. The goal is to run the uptime service validation
against these blocks and submissions and see that:
  - every BP scores 100% of available points;
  - blocks form a smooth, uninterrupted chain and there are no forks."""

import argparse
from datetime import datetime, timedelta, timezone
import itertools
import json
import os.path
import sys
import time

import requests

from local_block_reader import LocalBlockReader
from s3_block_reader import S3BlockReader
import network


class Scheduler:
    """The scheduler mocks the behaviour of a real blockchain. It is
    given a list of block producers and a list of blocks. It then
    cycles over the block producers, returning them one by one, in
    intervals of the submission_time. It also keeps track of the
    current block, switching it every block_time, taking the next
    block from the provided list. When that list is exhausted,
    iteration stops."""

    def __init__(
        self,
        nodes,
        block_reader,
        block_time=timedelta(minutes=3),
        submission_time=timedelta(minutes=1),
    ):
        "Initialize the scheduler."
        self.block_reader = block_reader
        self.nodes = itertools.cycle(nodes)
        self.block_time = block_time
        self.submission_time = submission_time
        self.next_block = None
        self.next_submission = None

    def __iter__(self):
        "Initialize an iteration."
        now = datetime.now(timezone.utc)
        now.replace(second=0, microsecond=0)
        self.next_block = now + self.block_time
        self.next_submission = now + self.submission_time
        # initialize iteration on block reader and select the first block
        iter(self.block_reader)
        next(self.block_reader)
        return self

    def __next__(self):
        "Return the next scheduled submission."
        now = datetime.now(timezone.utc)
        if now >= self.next_block:
            self.next_block += self.block_time
            # at some point this will raise StopIteration
            # which we allow to propagate to terminate the
            # scheduling
            next(self.block_reader)

        if now < self.next_submission:
            time.sleep((self.next_submission - now).total_seconds())

        self.next_submission += self.submission_time
        return next(self.nodes)

    def read_block(self):
        "Use the block reader to extract more block data."
        return self.block_reader.read_block()

    @property
    def current_block(self):
        "Return the state hash of the current block."
        return self.block_reader.current_state_hash


def parse_args():
    "Parse command line options."
    default_bp_file = os.path.join(os.path.dirname(__file__), "bp_keys.csv")
    p = argparse.ArgumentParser()
    p.add_argument("--block-dir", help="Directory with block files.")
    p.add_argument("--block-s3-bucket", help="S3 bucket where blocks are stored.")
    p.add_argument("--block-s3-dir", help="S3 directory where blocks are stored.")
    p.add_argument("--block-time", default=180, type=int, help="Block time in seconds.")
    p.add_argument(
        "--submission-time",
        default=60,
        type=int,
        help="Interval between subsequent submissions.",
    )
    p.add_argument(
        "--block-producers-file",
        default=default_bp_file,
        help="A CSV file with block producers public keys.",
    )
    p.add_argument(
        "--block-producer-count",
        type=int,
        help="""Number of block producers to use
(cannot be bigger than available keys in the file).""",
    )
    p.add_argument("uptime_service_url")
    return p.parse_args()


def main(args):
    """Generate submissions for the uptime service."""
    if args.block_dir is not None:
        block_reader = LocalBlockReader(args.block_dir)
    elif args.block_s3_dir is not None and args.block_s3_bucket is not None:
        block_reader = S3BlockReader(args.block_s3_bucket, args.block_s3_dir)
    else:
        raise RuntimeError("No block storage provided!")

    nodes = tuple(
        network.load_nodes(args.block_producers_file, args.block_producer_count)
    )

    scheduler = Scheduler(
        nodes,
        block_reader,
        block_time=timedelta(seconds=args.block_time),
        submission_time=timedelta(seconds=args.submission_time),
    )
    for node in scheduler:
        sub = node.submission(scheduler.read_block())
        now = datetime.now(timezone.utc)
        print(
            f"{now}: Submitting block {scheduler.current_block} for {node.public_key}..."
        )
        try:
            r = requests.post(args.uptime_service_url, json=sub, timeout=5.0)
            json.dump(r.json(), sys.stdout, indent=2)
        except requests.exceptions.ConnectionError as e:
            json.dump({"error": str(e), "bp": sub["submitter"]}, sys.stdout, indent=2)
    print("Done.")


if __name__ == "__main__":
    main(parse_args())
