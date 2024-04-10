"A mock for a real Mina network."
import csv

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class Node:
    """A Node is a simple bundle of a block producer's key and corresponding
    lilp2p peer id. It's capable of generating submission in the name od that
    node."""
    peer_id: str
    public_key: str

    def submission(self, block):
        """Create a new submission. Actually make it a method of an object
        containing a BP pub key and a peer_id."""
        now = datetime.now(timezone.utc)
        return {
            "submitter": self.public_key,
            "signature": "7mX1kSj74K1FVnNrRhDMabMshRA2iNadA5Q5ikqh95FAE3Hi4o6fQUQzgHmuacLk7ZZh9evh1FwAzMe1JwCycr5PZQ3RoXZf",
            "data": {
                "block": block,
                "created_at": now.strftime('%Y-%m-%dT%H:%M:%SZ'),
                "peer_id": self.peer_id,
                "snark_work": None
            }
        }

def load_nodes(filename, count):
    """Load at most [COUNT] nodes from a CSV file. Return a generator."""
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        if count is None:
            for row in reader:
                yield Node(row[0], row[1])
        else:
            returned_count = 0
            for row in reader:
                if returned_count < count:
                    yield Node(row[0], row[1])
                    returned_count += 1
                else:
                    return
            if returned_count < count:
                raise RuntimeError("Not enough BP keys in the file.")
