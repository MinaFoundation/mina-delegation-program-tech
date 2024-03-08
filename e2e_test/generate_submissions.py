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
import itertools
import requests

from data import BLOCKS, BP_KEYS, LIBP2P_PEER_IDS, SNARK_WORK
from network import NODES


def parse_args():
    "Parse command line options."
    p = argparse.ArgumentParser()
    p.add_argument("uptime_service_url")
    p.parse_args()

def main(args):
    """Generate submissions for the uptime service."""
    nodes = itertools.cycle(NODES)
    for statehash in BLOCKS:
        for _ in range(3):
            node = next(nodes)
            sub = node.submission(statehash)
            print("Sending submission:", sub)
            requests.post(args.uptime_service_url, json=sub, timeout=15.0)


if __name__ == "__main__":
    main(parse_args())
