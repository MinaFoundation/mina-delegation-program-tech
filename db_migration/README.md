# Migrate the uptime service database.

The delegation program that the Foundation ran before the hard fork will continue after the hard fork. Because computations of the uptime service are recursive in nature (output from the previous round influences how the next round will go), we need to migrate some data from the old service to the new one to serve as input for the first round. We’re not so much concerned with keeping historic record – such a record will be kept in the form of final database snapshot. Rather, we’re concerned with providing initial state of the service to kick it off properly. To this end we run a specialised migration script, whose task is to:

- Trim the database, leaving behind only data relevant for the past 3 months (after 1st December 2023).
- Migrate it to the format expected by the new uptime service.

Difference between the old database schema and the new one are not large. There’s a couple of tables that have been dropped as well as a few columns in existing tables. One column needs to be added in an existing table – the score_history table lacks a primary key. The migration script linked below takes care of all that.

[migrate.sql](./migrate.sql)

This script is intended to be run on a **copy** of the ontab database. Because it performs DELETE commands on some tables, it’s best to preserve a backup of the original database for safety, but also to preserve historic data, which might yet be needed in the future. This copy of the Ontab database will be provided as a database snapshot from AWS RDS service. It is important to have the snapshot encrypted with a key MF has access to so that we can restore the database from this snapshot on our end to run the script above.

NOTE: this will take several hours to execute (a lot of rows to drop and constraints to check). When the script is done, take a snapshot of the resulting database as a backup and you can hook the uptime service coordinator up to it,

## Taking a db diff

Under some circumstances (like e.g. an emergency hard fork) there might not be enough time to take a full Ontab database’s snapshot quickly (it takes several hours to produce) and then trim it (which takes another several hours). In that case a quicker approach can be used to synchronise the databases – the script linked below can be used to take a partial db dump (for increased speed) from the original database and move relevant records to the new database. The script can be run like this:

```bash
$ python db_diff.py -H $HOST -p $PORT -U $USERNAME -w $PASSWORD -d leaderboard_snark -t all $DATE > dump.sql
Bot logs fetched: 5932 rows
Statehash fetched: 57165 rows
Bot_logs_statehash fetched: 94737 rows
Nodes fetched: 1495 rows
Points fetched: 21950363 rows
Score history fetched: 8584008 rows
```

[db_diff.py](./db_diff.py)

Where:

- `$HOST` is the hostname of the original ontab database (delegation-uptime-ontab-4.c14zvdudnyw7.us-west-2.rds.amazonaws.com at the moment of writing this document)
- `$PORT` is port of the service (defaults to 5432)
- `$USERNAME` is the user that can read the database (we’ve graciously been given `ro_user` user to access the database).
- `$PASSWORD` is the USERNAME’s password for the database.
- `$DATE` is the day from which we want to take the diff (e.g. 2024-02-01). Only records added after that date will be dumped.

NOTE: the script requires psycopg2 package downloaded from pip.
You can dump data from all tables (`-t all`) or subset of supported tables (points, score_history, nodes, bot_logs, statehash, bot_logs_statehash), (e.g. `-t points,nodes`) 

This script will produce some SQL commands on the standard output and log some information to the standard error. Write it to a file and run the script against the target database in order to load the data. For instance, assuming the target database `delegation_program` is on localhost:

```bash
psql -h localhost -p 5432 -U postgres -d delegation_program -f dump.sql
```