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
import base64
from datetime import datetime, timedelta, timezone
import itertools
import json
import os
import requests
import sys
import time

from data import BLOCKS, BP_KEYS, LIBP2P_PEER_IDS, SNARK_WORK
from network import NODES


class Scheduler:
    """The scheduler mocks the behaviour of a real blockchain. It is
    given a list of block producers and a list of blocks. It then
    cycles over the block producers, returning them one by one, in
    intervals of the submission_time. It also keeps track of the
    current block, switching it every block_time, taking the next
    block from the provided list. When that list is exhausted,
    iteration stops."""

    def __init__(self, blocks, nodes, block_dir,
                 block_time=timedelta(minutes=3),
                 submission_time=timedelta(minutes=1)):
        self.block_dir = block_dir
        self.blocks = iter(blocks)
        self.nodes = itertools.cycle(nodes)
        self.current_block = next(self.blocks)
        self.block_time = block_time
        self.submission_time = submission_time
        self.next_block = None
        self.next_submission = None
        self.block_data = None

    def __iter__(self):
        now = datetime.now(timezone.utc)
        now.replace(second=0, microsecond=0)
        self.next_block = now + self.block_time
        self.next_submission = now + self.submission_time
        return self

    def __next__(self):
        now = datetime.now(timezone.utc)
        if now >= self.next_block:
            self.next_block += self.block_time
            # at some point this will raise StopIteration
            # which we allow to propagate to terminate the
            # scheduling
            self.current_block = next(self.blocks)
            self.block_data = None

        if now < self.next_submission:
            time.sleep((self.next_submission - now).total_seconds())

        self.next_submission += timedelta(seconds=60)
        return next(self.nodes)

    def read_block(self):
        if self.block_data is None:
            filename = f"{self.current_block}.dat"
            with open(os.path.join(self.block_dir, filename), "rb") as f:
                block = f.read()
                self.block_data = base64.b64encode(block).decode("ascii")
        return self.block_data


def parse_args():
    "Parse command line options."
    p = argparse.ArgumentParser()
    p.add_argument("--block-dir", required=True, help="Directory with block files.")
    p.add_argument("uptime_service_url")
    return p.parse_args()

def main(args):
    """Generate submissions for the uptime service."""
    scheduler = Scheduler(BLOCKS, NODES, args.block_dir)
    for node in scheduler:
        sub = node.submission(scheduler.read_block())
        now = datetime.now(timezone.utc)
        print(f"{now}: Submitting block {scheduler.current_block} for {node.public_key}...")
        r = requests.post(args.uptime_service_url, json=sub, timeout=15.0)
        json.dump(r.json(), sys.stdout, indent=2)
    print("Done.")


if __name__ == "__main__":
    main(parse_args())
