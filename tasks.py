from invoke import task
import boto3
import os
import pystache
import shutil

# Constants
RUNTIME_DIR = "./runtime"
COORDINATOR_REPO_URL = "https://github.com/MinaFoundation/uptime-service-validation.git"
COORDINATOR_RUNTIME_DIR = f"{RUNTIME_DIR}/uptime-service-validation"
SSL_CERTFILE = f"{COORDINATOR_RUNTIME_DIR}/uptime_service_validation/database/aws_keyspaces/cert/sf-class2-root.crt"


@task
def test(ctx, action):
    if action == "setup":
        network(ctx, "setup")
        network(ctx, "create")
        start_postgres(ctx)
        clone_coordinator_repo(ctx)
        prepare_coordinator_postgres(ctx)
    elif action == "start":
        network(ctx, "start")
        start_coordinator(ctx)
    elif action == "stop":
        network(ctx, "stop")
    elif action == "teardown":
        network(ctx, "delete")
        stop_postgres(ctx)
        clear_s3_bucket(ctx)
        migrate_keyspaces(ctx, direction="down")
        clear_runtime(ctx)


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
        ctx.run(f"minimina network start -n {config_network_name}", echo=True)
    elif action == "stop":
        ctx.run(f"minimina network stop -n {config_network_name}", echo=True)
    elif action == "delete":
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


@task
def start_coordinator(ctx):
    # Set environment variables
    os.environ["SSL_CERTFILE"] = os.path.abspath(SSL_CERTFILE)
    stateless_verifier_image = os.getenv("STATELESS_VERIFIER_IMAGE")
    worker_image, worker_tag = stateless_verifier_image.split(":")
    os.environ["WORKER_IMAGE"] = worker_image
    os.environ["WORKER_TAG"] = worker_tag

    with ctx.cd(COORDINATOR_RUNTIME_DIR):
        ctx.run("poetry install", echo=True)
        ctx.run("poetry run start", echo=True)
