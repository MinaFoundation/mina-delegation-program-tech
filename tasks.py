import subprocess
from dotenv import load_dotenv
import psutil
from invoke import task
import boto3
import os
import pystache
import shutil

# Constants
DOTENV_FILE = "./test/config/.env"
RUNTIME_DIR = "./runtime"
COORDINATOR_REPO_URL = "https://github.com/MinaFoundation/uptime-service-validation.git"
COORDINATOR_RUNTIME_DIR = f"{RUNTIME_DIR}/uptime-service-validation"
SSL_CERTFILE = f"{COORDINATOR_RUNTIME_DIR}/uptime_service_validation/database/aws_keyspaces/cert/sf-class2-root.crt"
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
]


@task
def load_env(ctx):
    decode_dotenv(ctx)
    load_dotenv(DOTENV_FILE)


@task(pre=[load_env])
def test(ctx, action):
    if action == "setup":
        check_env_vars()
        network(ctx, "setup")
        network(ctx, "create")
        start_postgres(ctx)
        clone_coordinator_repo(ctx)
        prepare_coordinator_postgres(ctx)
    elif action == "start":
        check_env_vars()
        network(ctx, "start")
        start_coordinator(ctx)
    elif action == "stop":
        network(ctx, "stop")
        stop_coordinator(ctx)
        dump_uptime_service_logs(ctx)
    elif action == "teardown":
        network(ctx, "delete")
        stop_postgres(ctx)
        clear_s3_bucket(ctx)
        migrate_keyspaces(ctx, direction="down")
        clear_runtime(ctx)


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
        setup_network(ctx)
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


@task
def setup_network(ctx):
    migrate_keyspaces(ctx, direction="down")
    migrate_keyspaces(ctx, direction="up")
    clear_s3_bucket(ctx)
    setup_topology(ctx)

    print("Uptime service setup completed.")


@task
def migrate_keyspaces(ctx, direction):
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
    source_dir = "./test/topology"
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
    with open(app_config_json_path, "w") as file:
        file.write(rendered)

    print("Updated JSON files in the runtime topology directory.")


@task
def clear_runtime(ctx):
    ctx.run(f"rm -rf {RUNTIME_DIR}", echo=True)
    print(f"Runtime directory '{RUNTIME_DIR}' cleared.")


@task(pre=[load_env])
def dump_uptime_service_logs(ctx):
    log_file = os.path.abspath(os.path.join(RUNTIME_DIR, "uptime-service.log"))
    ctx.run(
        f"minimina node logs -n {os.getenv('CONFIG_NETWORK_NAME')} -i uptime-service-backend -r > {log_file}",
        echo=True,
    )


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
        f"docker run --name postgres-container "
        f"-e POSTGRES_DB={postgres_db} "
        f"-e POSTGRES_USER={postgres_user} "
        f"-e POSTGRES_PASSWORD={postgres_password} "
        f"-p {postgres_port}:5432 "
        "-d postgres",
        echo=True,
    )

    print(
        f"PostgreSQL container started on {postgres_host}:{postgres_port} "
        f"with database '{postgres_db}' and user '{postgres_user}'."
    )


@task
def stop_postgres(ctx):
    # Stop the PostgreSQL Docker container
    ctx.run("docker stop postgres-container", echo=True)
    # Remove the PostgreSQL Docker container
    ctx.run("docker rm postgres-container", echo=True)

    print("PostgreSQL container stopped and removed.")


@task
def clone_coordinator_repo(ctx):
    coordinator_branch = os.getenv("COORDINATOR_BRANCH")
    if not coordinator_branch:
        raise ValueError("COORDINATOR_BRANCH environment variable must be set.")

    repo_url = "https://github.com/MinaFoundation/uptime-service-validation.git"
    destination_dir = "./runtime/uptime-service-validation"

    # Clone the specific branch of the repository into the runtime directory
    ctx.run(
        f"git clone --branch {coordinator_branch} {COORDINATOR_REPO_URL} {COORDINATOR_RUNTIME_DIR}",
        echo=True,
    )

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

    log_file = os.path.abspath(os.path.join(RUNTIME_DIR, "coordinator.log"))
    pid_file = os.path.abspath(os.path.join(RUNTIME_DIR, "coordinator.pid"))

    with ctx.cd(COORDINATOR_RUNTIME_DIR):
        ctx.run("poetry install", echo=True)

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