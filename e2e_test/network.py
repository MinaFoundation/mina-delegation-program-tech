"A mock for a real Mina network."

from dataclasses import dataclass
from datetime import datetime, timezone

from data import BP_KEYS, LIBP2P_PEER_IDS


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

NODES = list(Node(peer_id, bp) for bp, peer_id in zip(BP_KEYS, LIBP2P_PEER_IDS))
