import json
import re
import subprocess
from dotenv import load_dotenv
import psutil
from invoke import task
import boto3
import os
import psycopg2
import pystache
import shutil
import sys
import time
from datetime import datetime

# Constants
E2E_TEST_ROOT_DIR = "./e2e_test"
DOTENV_FILE = f"{E2E_TEST_ROOT_DIR}/config/.env"
RUNTIME_DIR = "./runtime"
LOGS_DIR = f"{RUNTIME_DIR}/logs"
COORDINATOR_REPO_URL = "https://github.com/MinaFoundation/uptime-service-validation.git"
COORDINATOR_RUNTIME_DIR = f"{RUNTIME_DIR}/uptime-service-validation"
SSL_CERTFILE = f"{COORDINATOR_RUNTIME_DIR}/uptime_service_validation/database/aws_keyspaces/cert/sf-class2-root.crt"
SUBMISSION_STORAGE = os.getenv("SUBMISSION_STORAGE")
REQUIRED_ENV_VARS = [
    "MINA_DAEMON_IMAGE",
    "UPTIME_SERVICE_IMAGE",
    "COORDINATOR_BRANCH",
    "STATELESS_VERIFIER_IMAGE",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_S3_BUCKET",
    "AWS_KEYSPACE",
    "AWS_REGION",
    "CONFIG_NETWORK_NAME",
    "NETWORK_NAME",
    "TEST_ENV",
    "SURVEY_INTERVAL_MINUTES",
    "MINI_BATCH_NUMBER",
    "UPTIME_DAYS_FOR_SCORE",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "AWS_DEFAULT_REGION",
    "CASSANDRA_HOST",
    "CASSANDRA_PORT",
    "SUBMISSION_STORAGE",
]


@task
def load_env(ctx):
    decode_dotenv(ctx)
    load_dotenv(DOTENV_FILE)


@task(pre=[load_env])
def test(ctx, action):
    if action == "setup":
        print("Setting up...")
        print("SUBMISSION_STORAGE: ", SUBMISSION_STORAGE)
        check_env_vars()
        clear_runtime(ctx)
        pull_images(ctx)
        clone_coordinator_repo(ctx)
        if SUBMISSION_STORAGE == "CASSANDRA":
            print("Preparing keyspace...")
            keyspace_drop_tables(ctx)
            keyspace_migrate(ctx, direction="up")
        network(ctx, "setup")
        network(ctx, "create")
        start_postgres(ctx)
        ctx.run(f"mkdir -p {LOGS_DIR}", echo=True)
        prepare_coordinator_postgres(ctx)
    elif action == "start":
        check_env_vars()
        network(ctx, "start")
        start_coordinator(ctx)
    elif action == "wait":
        if SUBMISSION_STORAGE == "CASSANDRA":
            keyspace_wait_for_availability(ctx)
        wait_for_verifications(ctx)
    elif action == "stop":
        network(ctx, "stop")
        stop_coordinator(ctx)
    elif action == "dump-logs":
        dump_logs(ctx)
    elif action == "assert":
        print("Asserting data...")
        assert_data(ctx)
        print()
        print("Asserting logs...")
        assert_logs(ctx)
    elif action == "teardown":
        network(ctx, "delete")
        stop_postgres(ctx)
        clear_s3_bucket(ctx)
        if SUBMISSION_STORAGE == "CASSANDRA":
            print("Dropping tables in keyspace...")
            keyspace_drop_tables(ctx)
        clear_runtime(ctx)


@task
def pull_images(ctx):
    mina_daemon_image = os.getenv("MINA_DAEMON_IMAGE")
    uptime_service_image = os.getenv("UPTIME_SERVICE_IMAGE")
    stateless_verifier_image = os.getenv("STATELESS_VERIFIER_IMAGE")

    ctx.run(f"docker pull {mina_daemon_image}", echo=True)
    ctx.run(f"docker pull {uptime_service_image}", echo=True)
    ctx.run(f"docker pull {stateless_verifier_image}", echo=True)
    ctx.run(f"docker pull postgres", echo=True)


def check_env_vars():
    missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing_vars:
        missing_vars_str = ", ".join(missing_vars)
        raise ValueError(
            f"Error: The following required environment variables are not set: {missing_vars_str}"
        )


@task
def decode_dotenv(ctx):
    e2e_secret = os.getenv("E2E_SECRET")
    if not e2e_secret:
        print("Error: E2E_SECRET environment variable not set.")
        return

    if not os.path.exists(DOTENV_FILE):
        command = (
            f"gpg --pinentry-mode loopback --yes --passphrase {e2e_secret} "
            f"--output {DOTENV_FILE} --decrypt {DOTENV_FILE}.gpg"
        )
        ctx.run(command, echo=False, warn=True)


@task
def encode_dotenv(ctx):
    e2e_secret = os.getenv("E2E_SECRET")
    if not e2e_secret:
        print("Error: E2E_SECRET environment variable not set.")
        return

    command = (
        f"gpg --pinentry-mode loopback --passphrase {e2e_secret} "
        f"--symmetric --output {DOTENV_FILE}.gpg {DOTENV_FILE}"
    )
    ctx.run(command, echo=True, warn=True)


@task
def network(ctx, action):
    config_network_name = os.getenv("CONFIG_NETWORK_NAME")

    if not config_network_name:
        raise ValueError("CONFIG_NETWORK_NAME environment variable must be set.")

    if action == "setup":
        clear_s3_bucket(ctx)
        setup_topology(ctx)
        print("Uptime service setup completed.")
    elif action == "create":
        with ctx.cd(RUNTIME_DIR):
            ctx.run(
                f"minimina network create -t topology/topology.json -g topology/genesis_ledger.json -n {config_network_name}",
                echo=True,
            )
    elif action == "start":
        print("Starting network...")
        ctx.run(f"minimina network start -n {config_network_name}", echo=True)
    elif action == "stop":
        print("Stopping network...")
        ctx.run(f"minimina network stop -n {config_network_name}", echo=True)
    elif action == "delete":
        print("Deleting network...")
        ctx.run(f"minimina network delete -n {config_network_name}", echo=True)
    elif action == "status":
        ctx.run(f"minimina network status -n {config_network_name}", echo=True)
    else:
        raise ValueError(
            "Invalid action. Possible values are 'create', 'start', 'stop', 'delete', 'status'."
        )


@task(pre=[load_env])
def keyspace_drop_tables(ctx):
    sys.path.append(COORDINATOR_RUNTIME_DIR)
    os.environ["SSL_CERTFILE"] = os.path.abspath(SSL_CERTFILE)
    from uptime_service_validation.coordinator.aws_keyspaces_client import (
        AWSKeyspacesClient,
    )

    keyspace = os.getenv("AWS_KEYSPACE")
    cassandra = AWSKeyspacesClient()
    cassandra.connect()
    tables = cassandra.execute_query(
        f"SELECT table_name FROM system_schema.tables WHERE keyspace_name = '{keyspace}'"
    )
    for table in tables:
        print(f"Dropping table {keyspace}.{table[0]}")
        cassandra.execute_query(f"DROP TABLE {keyspace}.{table[0]}")
    cassandra.close()


@task
def keyspace_migrate(ctx, direction):
    if direction not in ["up", "down"]:
        raise ValueError("Invalid direction. Use 'up' or 'down'.")

    docker_command = (
        "docker run "
        "-e AWS_KEYSPACE "
        "-e AWS_REGION "
        "-e AWS_ACCESS_KEY_ID "
        "-e AWS_SECRET_ACCESS_KEY "
        "-e DELEGATION_WHITELIST_DISABLED=1 "
        "-e CONFIG_NETWORK_NAME "
        "--entrypoint db_migration "
        f"$UPTIME_SERVICE_IMAGE {direction}"
    )
    ctx.run(docker_command, echo=True)


@task
def clear_s3_bucket(ctx):
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    bucket_name = os.getenv("AWS_S3_BUCKET")
    prefix = os.getenv("CONFIG_NETWORK_NAME") + "/"

    if not all([aws_access_key_id, aws_secret_access_key, bucket_name, prefix]):
        raise ValueError("All required environment variables must be set.")

    session = boto3.Session(
        aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key
    )
    s3 = session.resource("s3")
    bucket = s3.Bucket(bucket_name)

    # List and delete objects within the specified prefix
    for obj in bucket.objects.filter(Prefix=prefix):
        obj.delete()

    print(f"All objects in '{prefix}' have been deleted from '{bucket_name}' bucket.")


@task
def setup_topology(ctx):
    source_dir = f"{E2E_TEST_ROOT_DIR}/topology"
    destination_dir = f"{RUNTIME_DIR}/topology"

    # Create the destination directory if it doesn't exist
    os.makedirs(destination_dir, exist_ok=True)

    # Copy the contents of the source directory to the destination directory
    if os.path.exists(source_dir) and os.path.isdir(source_dir):
        shutil.copytree(source_dir, destination_dir, dirs_exist_ok=True)
        print(f"Copied '{source_dir}' to '{destination_dir}'")
    else:
        print(f"Source directory '{source_dir}' does not exist.")
        return

    # Extract aws_account_id and bucket_name_suffix from AWS_S3_BUCKET
    aws_s3_bucket = os.getenv("AWS_S3_BUCKET")
    aws_account_id, bucket_name_suffix = aws_s3_bucket.split("-", 1)

    # Prepare data for template replacement
    context = {
        "mina_docker_image": os.getenv("MINA_DAEMON_IMAGE"),
        "uptime_service_image": os.getenv("UPTIME_SERVICE_IMAGE"),
        "config_network_name": os.getenv("CONFIG_NETWORK_NAME"),
        "aws_keyspace": os.getenv("AWS_KEYSPACE"),
        "aws_region": os.getenv("AWS_REGION"),
        "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "aws_account_id": aws_account_id,
        "bucket_name_suffix": bucket_name_suffix,
    }

    # Step 1: Update topology.json
    topology_json_path = os.path.join(destination_dir, "topology.json")
    with open(topology_json_path, "r") as file:
        template = file.read()
    rendered = pystache.render(template, context)
    with open(topology_json_path, "w") as file:
        file.write(rendered)

    # Step 2: Update app_config.json
    app_config_json_path = os.path.join(
        destination_dir, "uptime_service_config/app_config.json"
    )
    with open(app_config_json_path, "r") as file:
        template = file.read()
    rendered = pystache.render(template, context)
    if SUBMISSION_STORAGE == "CASSANDRA":
        # Remove the PostgreSQL configuration from the JSON file
        rendered = re.sub(r'"postgresql": {[^}]+},', "", rendered)
    elif SUBMISSION_STORAGE == "POSTGRES":
        # Remove the Cassandra configuration from the JSON file
        rendered = re.sub(r'"aws_keyspaces": {[^}]+},', "", rendered)
    with open(app_config_json_path, "w") as file:
        file.write(rendered)

    print("Updated JSON files in the runtime topology directory.")


@task
def clear_runtime(ctx):
    ctx.run(f"rm -rf {RUNTIME_DIR}", echo=True)
    print(f"Runtime directory '{RUNTIME_DIR}' cleared.")


@task(pre=[load_env])
def dump_logs(ctx):
    services = [
        "uptime-service-backend",
        "node-a",
        "node-b",
        "node-c",
        "snark-node",
        "default-seed",
    ]
    for service in services:
        log_file = os.path.abspath(os.path.join(LOGS_DIR, f"{service}.log"))
        ctx.run(
            f"minimina node logs -n {os.getenv('CONFIG_NETWORK_NAME')} -i {service} -r > {log_file}",
            echo=True,
        )
        print(f"Logs for {service} have been written to {log_file}")


@task
def start_postgres(ctx):
    # Get environment variables
    postgres_host = os.getenv("POSTGRES_HOST")
    postgres_port = os.getenv("POSTGRES_PORT")
    postgres_db = os.getenv("POSTGRES_DB")
    postgres_user = os.getenv("POSTGRES_USER")
    postgres_password = os.getenv("POSTGRES_PASSWORD")

    # Run the PostgreSQL Docker container
    ctx.run(
        f"docker run --name postgres-e2e "
        f"-e POSTGRES_DB={postgres_db} "
        f"-e POSTGRES_USER={postgres_user} "
        f"-e POSTGRES_PASSWORD={postgres_password} "
        f"-p {postgres_port}:5432 "
        "--network e2e-test_default "
        "-d postgres",
        echo=True,
    )
    # Wait for the container to start
    time.sleep(5)

    print(
        f"PostgreSQL container started on {postgres_host}:{postgres_port} "
        f"with database '{postgres_db}' and user '{postgres_user}'."
    )


@task
def stop_postgres(ctx):
    # Stop the PostgreSQL Docker container
    ctx.run("docker stop postgres-e2e", echo=True)
    # Remove the PostgreSQL Docker container
    ctx.run("docker rm postgres-e2e", echo=True)

    print("PostgreSQL container stopped and removed.")


@task
def clone_coordinator_repo(ctx):
    coordinator_branch = os.getenv("COORDINATOR_BRANCH")
    if not coordinator_branch:
        raise ValueError("COORDINATOR_BRANCH environment variable must be set.")

    # Clone the specific branch of the repository into the runtime directory
    ctx.run(
        f"git clone --branch {coordinator_branch} {COORDINATOR_REPO_URL} {COORDINATOR_RUNTIME_DIR}",
        echo=True,
    )

    with ctx.cd(COORDINATOR_RUNTIME_DIR):
        ctx.run("poetry install", echo=True)

    print(
        f"Repository cloned into {COORDINATOR_RUNTIME_DIR} on branch '{coordinator_branch}'."
    )


@task
def prepare_coordinator_postgres(ctx):
    with ctx.cd(COORDINATOR_RUNTIME_DIR):
        ctx.run("invoke create-database", echo=True)
        ctx.run("invoke init-database", echo=True)


@task(pre=[load_env])
def start_coordinator(ctx):
    # Set environment variables
    os.environ["SSL_CERTFILE"] = os.path.abspath(SSL_CERTFILE)
    stateless_verifier_image = os.getenv("STATELESS_VERIFIER_IMAGE")
    worker_image, worker_tag = stateless_verifier_image.split(":")
    os.environ["WORKER_IMAGE"] = worker_image
    os.environ["WORKER_TAG"] = worker_tag

    log_file = os.path.abspath(os.path.join(LOGS_DIR, "coordinator.log"))
    pid_file = os.path.abspath(os.path.join(RUNTIME_DIR, "coordinator.pid"))

    # Start the coordinator process
    print(f"Starting coordinator. Logs will be written to {log_file}")
    command = f"poetry run start > {log_file} 2>&1"
    proc = subprocess.Popen(command, shell=True, cwd=COORDINATOR_RUNTIME_DIR)

    # Write the PID to the pid_file
    with open(pid_file, "w") as f:
        f.write(str(proc.pid))


def kill_proc_tree(pid, including_parent=True):
    try:
        parent = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return  # Process already terminated

    children = parent.children(recursive=True)
    for child in children:
        child.kill()
    if including_parent:
        parent.kill()


@task
def stop_coordinator(ctx):
    print("Stopping coordinator...")
    pid_file = os.path.abspath(os.path.join(RUNTIME_DIR, "coordinator.pid"))

    try:
        with open(pid_file, "r") as file:
            pid = int(file.read().strip())

        kill_proc_tree(pid)

        os.remove(pid_file)
    except OSError as e:
        print(f"Error stopping coordinator: {e}")
    except FileNotFoundError:
        print("PID file not found. Is the coordinator running?")


def get_submissions():
    if SUBMISSION_STORAGE == "CASSANDRA":
        sys.path.append(COORDINATOR_RUNTIME_DIR)
        os.environ["SSL_CERTFILE"] = os.path.abspath(SSL_CERTFILE)
        from uptime_service_validation.coordinator.aws_keyspaces_client import (
            AWSKeyspacesClient,
        )

        keyspace = os.getenv("AWS_KEYSPACE")
        cassandra = AWSKeyspacesClient()
        cassandra.connect()
        submissions = cassandra.execute_query(
            f"SELECT JSON * FROM {keyspace}.submissions"
        )
        subs = [json.loads(row[0]) for row in submissions]
        cassandra.close()
        return subs
    elif SUBMISSION_STORAGE == "POSTGRES":
        host = os.getenv("POSTGRES_HOST")
        port = os.getenv("POSTGRES_PORT")
        dbname = os.getenv("POSTGRES_DB")
        user = os.getenv("POSTGRES_USER")
        password = os.getenv("POSTGRES_PASSWORD")

        conn_str = f"dbname='{dbname}' user='{user}' host='{host}' port='{port}' password='{password}'"

        conn = psycopg2.connect(conn_str)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, submitter, block_hash, validation_error, verified FROM submissions;"
        )
        subs = []
        for row in cursor.fetchall():
            try:
                row_dict = {
                    "id": row[0],
                    "submitter": row[1] if row[1] else None,
                    "block_hash": row[2] if row[2] else None,
                    "validation_error": row[3] if row[3] else None,
                    "verified": row[4] if row[4] else None,
                }
                subs.append(json.dumps(row_dict))
            except TypeError:
                print(f"Skipping row, expected JSON data but got: {row[0]}")
        return [json.loads(sub) for sub in subs]
    else:
        raise ValueError("Invalid submission storage type.")


def s3_get_data():
    bucket_name = os.getenv("AWS_S3_BUCKET")
    network_name = os.getenv("CONFIG_NETWORK_NAME")
    s3 = boto3.client("s3")
    blocks = []
    submissions = []

    # Get the list of block file names and submission contents from the S3 bucket
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket_name, Prefix=f"{network_name}/")

    for page in pages:
        for obj in page["Contents"]:
            key = obj["Key"]
            if key.endswith(".dat"):
                blocks.append(key)
            elif key.endswith(".json"):
                # Retrieve and read the content of the JSON file
                json_obj = s3.get_object(Bucket=bucket_name, Key=key)
                json_content = json_obj["Body"].read().decode("utf-8")
                submission_content = json.loads(json_content)
                submissions.append(submission_content)  # Add the parsed JSON content

    return blocks, submissions


def postgres_get_data():
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    dbname = os.getenv("POSTGRES_DB")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")

    conn_str = f"dbname='{dbname}' user='{user}' host='{host}' port='{port}' password='{password}'"

    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()

    # Fetching postgres_submitters
    cursor.execute("SELECT block_producer_key FROM nodes;")
    postgres_submitters = [row[0] for row in cursor.fetchall()]

    # Fetching postgres_verified_subs
    cursor.execute("SELECT SUM(files_processed) FROM bot_logs;")
    postgres_verified_subs_num = cursor.fetchone()[0]

    # Close the cursor and the connection
    cursor.close()
    conn.close()

    return postgres_submitters, postgres_verified_subs_num


@task(pre=[load_env])
def keyspace_wait_for_availability(ctx):
    sys.path.append(COORDINATOR_RUNTIME_DIR)
    os.environ["SSL_CERTFILE"] = os.path.abspath(SSL_CERTFILE)
    from uptime_service_validation.coordinator.aws_keyspaces_client import (
        AWSKeyspacesClient,
    )

    keyspace = os.getenv("AWS_KEYSPACE")
    cassandra = AWSKeyspacesClient()
    cassandra.connect()
    # wait until table submissions is available
    while True:
        try:
            cassandra.execute_query(f"SELECT JSON * FROM {keyspace}.submissions")
            break
        except Exception as e:
            print(f"Waiting for keyspace to be available: {e}")
            time.sleep(5)
    print("Keyspace is available.")
    cassandra.close()


@task(pre=[load_env])
def wait_for_verifications(ctx):
    timeout = 60 * 60  # 60 minutes in seconds
    start_time = datetime.now()
    in_storage_subs = get_submissions()
    in_storage_verified_subs = [sub for sub in in_storage_subs if sub["verified"]]
    # subs for genesis_block have dummy proof so they return validation_error = (Pickles.verify dlog_check)
    # they will not be verified in postgres, so we will exclude them from the assertion
    in_storage_verified_subs_no_genesis_block = [
        sub
        for sub in in_storage_verified_subs
        if sub["validation_error"] != "(Pickles.verify dlog_check)"
    ]
    _, postgres_verified_subs_num = postgres_get_data()

    while not (
        len(in_storage_verified_subs) == len(in_storage_subs) > 0
        and postgres_verified_subs_num
        == len(in_storage_verified_subs_no_genesis_block)
        > 0
    ):
        current_time = datetime.now()
        elapsed_time = (current_time - start_time).total_seconds()

        # Check if timeout has been reached
        if elapsed_time > timeout:
            print(
                f"Timeout reached (in_storage / in_storage_verified / coordinator_verified): {len(in_storage_subs)} / {len(in_storage_verified_subs)} / {postgres_verified_subs_num}"
            )
            exit(1)

        time.sleep(15)

        print(
            f"Waiting for verifications (in_storage / in_storage_verified / coordinator_verified): {len(in_storage_subs)} / {len(in_storage_verified_subs)} / {postgres_verified_subs_num}"
        )

        in_storage_subs = get_submissions()
        in_storage_verified_subs = [sub for sub in in_storage_subs if sub["verified"]]
        in_storage_verified_subs_no_genesis_block = [
            sub
            for sub in in_storage_verified_subs
            if sub["validation_error"] != "(Pickles.verify dlog_check)"
        ]
        _, postgres_verified_subs_num = postgres_get_data()

    print(
        f"All submissions have been verified (in_storage / in_storage_verified / coordinator_verified): {len(in_storage_subs)} / {len(in_storage_verified_subs)} / {postgres_verified_subs_num}"
    )
    print(
        f"Genesis block submissions ({len(in_storage_verified_subs) - len(in_storage_verified_subs_no_genesis_block)}) are not included in the postgres_verified count."
    )


@task(pre=[load_env])
def assert_data(ctx):
    # Get data from Storage (Keyspaces or PostgreSQL)
    in_storage_subs = get_submissions()
    in_storage_verified_subs = [sub for sub in in_storage_subs if sub["verified"]]
    in_storage_verified_subs_no_genesis_block = [
        sub
        for sub in in_storage_verified_subs
        if sub["validation_error"] != "(Pickles.verify dlog_check)"
    ]
    in_storage_submitter_keys = set([sub["submitter"] for sub in in_storage_subs])
    in_storage_block_hashes = set([sub["block_hash"] for sub in in_storage_subs])

    # Get data from S3
    s3_blocks, s3_submissions = s3_get_data()
    s3_block_hashes = set(
        [filename.split("/")[-1].split(".")[0] for filename in s3_blocks]
    )
    s3_submitter_keys = set([sub["submitter"] for sub in s3_submissions])

    # Get data from Coordinator (PostgreSQL)
    postgres_submitters, postgres_verified_subs_num = postgres_get_data()

    # Print data
    print("SUBMISSIONS DATA")
    print(f"Total In Storage submissions: {len(in_storage_subs)}")
    print(f"Total S3 submissions: {len(s3_submissions)}")
    print(f"Total In Storage verified submissions: {len(in_storage_verified_subs)}")
    print(
        f"Total In Storage valid verified submissions (exluding genesis_block): {len(in_storage_verified_subs_no_genesis_block)}"
    )
    print(f"Total Postgres verified submissions: {postgres_verified_subs_num}")
    print()
    print("SUBMITTERS DATA")
    print(f"Total In Storage unique submitters: {len(in_storage_submitter_keys)}")
    print(f"Total S3 submitters: {len(s3_submitter_keys)}")
    print(f"Total Postgres submitters: {len(postgres_submitters)}")
    print()
    print("BLOCKS DATA")
    print(f"Total In Storage blocks (hashes): {len(in_storage_block_hashes)}")
    print(f"Total S3 blocks: {len(s3_blocks)}")

    # Assertions
    # Check verified submissions in Storage equals verified submissions in Postgres
    assert (
        len(in_storage_verified_subs_no_genesis_block) == postgres_verified_subs_num
    ), (
        f"Mismatch in number of valid verified submissions between Storage ({len(in_storage_verified_subs)}) "
        f"and Coordinator ({postgres_verified_subs_num})"
    )
    # Check if the number of unique block hashes in Storage equals the number of block files in S3
    assert len(in_storage_block_hashes) == len(
        s3_block_hashes
    ), f"Mismatch in number of unique block hashes between Storage ({len(in_storage_block_hashes)}) and S3 ({len(s3_block_hashes)})"

    # Check block hashes in Storage and S3 are the same
    assert (
        in_storage_block_hashes == s3_block_hashes
    ), f"Block hashes do not match in Storage ({in_storage_block_hashes}) and S3 ({s3_block_hashes})"

    # Check if the number of submissions in Storage equals the number of submissions in S3
    assert len(in_storage_subs) == len(
        s3_submissions
    ), f"Mismatch in number of submissions between Storage ({len(in_storage_subs)}) and S3 ({len(s3_submissions)})"

    postgres_submitter_keys = set(postgres_submitters)

    # Check if all sets contain the same elements
    assert (
        in_storage_submitter_keys == s3_submitter_keys == postgres_submitter_keys
    ), f"Submitter keys do not match across Storage ({in_storage_submitter_keys}), S3 ({s3_submitter_keys}), and Coordinator ({postgres_submitter_keys})"


@task
def assert_logs(ctx):
    error_pattern = re.compile(r"ERROR|Error|FATAL|Fatal")
    error_found = False

    for log_file in os.listdir(LOGS_DIR):
        if log_file == "coordinator.log" or log_file == "uptime-service-backend.log":
            with open(os.path.join(LOGS_DIR, log_file), "r") as file:
                for line in file:
                    if error_pattern.search(line):
                        print(
                            f"Error or fatal entry found in {log_file}: {line.strip()}"
                        )
                        error_found = True

    if error_found:
        print("Errors or fatal entries were found in log files.")
        sys.exit(1)
    else:
        print("No error or fatal entries found in logs.")
        sys.exit(0)
