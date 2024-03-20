"""This module is concerned with downloading blocks to submit from S3."""

import base64
import boto3

from block_reader import BlockReader


class S3BlockReader(BlockReader):
    "Read blocks from local file system."

    def __init__(self, s3_bucket, prefix):
        "Initialize."
        super().__init__()
        self.bucket = s3_bucket
        self.prefix = prefix
        self.client = boto3.client("s3")

    def read_block_list(self):
        "Read the list of block state hashes to process."
        block_list_resp = self.client.get_object(
            Bucket=self.bucket,
            Key=f"{self.prefix}/block_list.txt"
        )
        return (bs.decode("utf8").strip() for bs in block_list_resp["Body"].readlines())

    def read_block(self):
        """Read the current block's data from disk and cache for
        future reuse."""
        if self.current_block_data is None:
            block_resp = self.client.get_object(
                Bucket=self.bucket,
                Key=f"{self.prefix}/{self.current_state_hash}.dat"
            )
            self.current_block_data = base64.b64encode(block_resp["Body"].read()).decode("utf-8")
        
        return self.current_block_data
