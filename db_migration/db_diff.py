import argparse
from datetime import datetime, timedelta
import sys
import psycopg2
from psycopg2.sql import Literal


def batched(iterable, n):
    """Yield successive n-sized chunks from iterable."""
    items = []
    count = 0
    for item in iterable:
        if count < n:
            items.append(item)
            count += 1
        else:
            yield items
            items = [item]
            count = 1
    if items:
        yield items


class Insert:

    def __init__(self, connection, table, columns):
        self.connection = connection
        self.table = table
        self.columns = columns
        self.results = []

    def fetch_all(self):
        with self.connection.cursor() as cursor:
            q = "SELECT {} FROM {}".format(", ".join(self.columns), self.table)
            cursor.execute(q)
            self.results = cursor.fetchall()

    def fetch(
        self, condition, args, joins=(), clear_results=True, order_by="ASC", limit="ALL"
    ):
        if clear_results:
            self.results = []

        cols = ", ".join("{}.{}".format(self.table, col) for col in self.columns)
        j = " ".join(
            "JOIN {tbl} AS {as} ON {as}.{col} = {val}".format(**join) for join in joins
        )
        q = "SELECT DISTINCT {} FROM {} {} WHERE {} ORDER BY {}.{} {} LIMIT {}".format(
            cols, self.table, j, condition, self.table, self.columns[0], order_by, limit
        )

        with self.connection.cursor() as cursor:
            cursor.execute(q, args)
            self.results += cursor.fetchall()

    def print(self):
        for batch in batched(self.results, 1000):
            cols = ", ".join(self.columns)
            print("INSERT INTO {}".format(self.table))
            print("    ({})".format(cols))
            print("VALUES")
            print(
                "   ",
                ",\n    ".join(
                    "({})".format(
                        ", ".join(
                            Literal(item).as_string(self.connection) for item in row
                        )
                    )
                    for row in batch
                ),
            )
            print("ON CONFLICT(id)")
            print("DO UPDATE SET")
            print(
                "   ",
                ",\n    ".join(
                    "{col} = EXCLUDED.{col}".format(col=col) for col in self.columns
                ),
            )
            print(";")


def parse_args():
    p = argparse.ArgumentParser(description="Diff two uptime service databases.")
    p.add_argument("-H", "--host", help="Database hostname", default="localhost")
    p.add_argument("-p", "--port", help="Database port", default=5432, type=int)
    p.add_argument("-U", "--user", help="Database username", default="postgres")
    p.add_argument("-w", "--password", help="Database password", required=True)
    p.add_argument("-d", "--database", help="Database name", required=True)
    p.add_argument("last_update", help="Last update time", type=datetime.fromisoformat)
    p.add_argument(
        "-t",
        "--tables",
        help="Comma-separated list of tables to include (e.g., all, points, score_history, nodes, bot_logs, statehash, bot_logs_statehash)",
        default="all",
    )
    return p.parse_args()


def main(args):
    conn = psycopg2.connect(
        user=args.user,
        password=args.password,
        host=args.host,
        port=args.port,
        database=args.database,
    )

    tables = args.tables.split(",")

    print("BEGIN;\n")

    if "all" in tables or "bot_logs" in tables:
        bot_logs = Insert(
            conn,
            "bot_logs",
            (
                "id",
                "files_processed",
                "file_timestamps",
                "batch_start_epoch",
                "batch_end_epoch",
                "processing_time",
            ),
        )
        bot_logs.fetch(
            "bot_logs.batch_end_epoch >= trunc(extract(epoch from (%s)))",
            (args.last_update,),
        )
        bot_logs.print()
        print(
            "Bot logs fetched: {} rows".format(len(bot_logs.results)),
            file=sys.stderr,
        )

    if "all" in tables or "statehash" in tables:
        statehash = Insert(conn, "statehash", ("id", "value"))
        statehash.fetch(
            "bl.batch_end_epoch >= trunc(extract(epoch from (%s)))",
            # We need to fetch the last statehash before the range (which is needed for the parent_statehash_id column)
            # so let's fetch last_update - 60 minutes
            (args.last_update - timedelta(minutes=60),),
            joins=(
                {
                    "tbl": "bot_logs_statehash",
                    "as": "bls",
                    "col": "statehash_id",
                    "val": "statehash.id",
                },
                {"tbl": "bot_logs", "as": "bl", "col": "id", "val": "bls.bot_log_id"},
            ),
        )
        statehash.print()
        print(
            "Statehash fetched: {} rows".format(len(statehash.results)),
            file=sys.stderr,
        )

    if "all" in tables or "bot_logs_statehash" in tables:
        bot_logs_statehash = Insert(
            conn,
            "bot_logs_statehash",
            ("id", "bot_log_id", "statehash_id", "parent_statehash_id", "weight"),
        )
        bot_logs_statehash.fetch(
            "bl.batch_end_epoch >= trunc(extract(epoch from (%s)))",
            (args.last_update,),
            joins=(
                {
                    "tbl": "bot_logs",
                    "as": "bl",
                    "col": "id",
                    "val": "bot_logs_statehash.bot_log_id",
                },
            ),
        )
        bot_logs_statehash.print()
        print(
            "Bot_logs_statehash fetched: {} rows".format(
                len(bot_logs_statehash.results)
            ),
            file=sys.stderr,
        )

    if "all" in tables or "nodes" in tables:
        nodes = Insert(
            conn,
            "nodes",
            (
                "id",
                "block_producer_key",
                "score",
                "score_percent",
                "updated_at",
                "email_id",
                "application_status",
            ),
        )
        nodes.fetch_all()
        nodes.print()
        print(
            "Nodes fetched: {} rows".format(len(nodes.results)),
            file=sys.stderr,
        )

    if "all" in tables or "points" in tables:
        points = Insert(
            conn,
            "points",
            (
                "id",
                "file_name",
                "blockchain_epoch",
                "blockchain_height",
                "created_at",
                "amount",
                "node_id",
                "bot_log_id",
                "file_timestamps",
                "statehash_id",
            ),
        )
        points.fetch(
            "bl.batch_end_epoch >= trunc(extract(epoch from (%s)))",
            (args.last_update,),
            joins=(
                {
                    "tbl": "bot_logs",
                    "as": "bl",
                    "col": "id",
                    "val": "points.bot_log_id",
                },
            ),
        )
        points.print()
        print(
            "Points fetched: {} rows".format(len(points.results)),
            file=sys.stderr,
        )

    if "all" in tables or "score_history" in tables:
        score_history = Insert(
            conn, "score_history", ("node_id", "score_at", "score", "score_percent")
        )
        score_history.fetch(
            "score_at >= %s AND score_at IS NOT NULL", (args.last_update,)
        )
        score_history.print()
        print(
            "Score history fetched: {} rows".format(len(score_history.results)),
            file=sys.stderr,
        )

    print("COMMIT;")


if __name__ == "__main__":
    main(parse_args())
