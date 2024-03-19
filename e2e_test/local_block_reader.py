"This module is concerned with reading blocks from as local storage (file system)."

import base64
import os


class LocalBlockReader:
    "Read blocks from local file system."

    def __init__(self, block_dir):
        "Initialize."
        self.block_dir = block_dir
        self.blocks = None
        self.current_state_hash = None
        self.current_block_data = None

    def __iter__(self):
        block_list = os.path.join(self.block_dir, "block_list.txt")
        with open(block_list, "r", encoding="utf-8") as fp:
            self.blocks = (l.strip() for l in fp.readlines())
        return self

    def __next__(self):
        self.current_state_hash = next(self.blocks)
        self.current_block_data = None
        return self.current_state_hash

    def read_block(self):
        """Read the current block's data from disk and cache for
        future reuse."""
        if self.current_block_data is None:
            filename = f"{self.current_state_hash}.dat"
            path = os.path.join(self.block_dir, filename)
            with open(path, "rb") as fp:
                self.current_block_data = base64.b64encode(fp.read()).decode("utf-8")
        return self.current_block_data
