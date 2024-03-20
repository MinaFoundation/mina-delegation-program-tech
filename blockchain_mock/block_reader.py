"""This module defines a generic block reader, which cannot read blocks,
just contains the general policy of iterating over them."""


class BlockReader:
    """General logic of returning blocks in sequence, regardless of
    how they're stored or read."""

    def __init__(self):
        "Initialize."
        self.blocks = None
        self.current_state_hash = None
        self.current_block_data = None

    def __iter__(self):
        self.blocks = self.read_block_list()
        return self

    def __next__(self):
        self.current_state_hash = next(self.blocks)
        self.current_block_data = None
        return self.current_state_hash

    def read_block_list(self):
        """Read the list of block state hashes to process.
        This is a dummy implementation, returning an empty
        iterator. To be overridden in subclasses."""
        return iter(())
