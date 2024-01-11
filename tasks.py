from invoke import task
import boto3
import os
import pystache
import shutil

@task
def setup_uptime_service(ctx):
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
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    bucket_name = os.getenv('AWS_S3_BUCKET')
    prefix = os.getenv('CONFIG_NETWORK_NAME') + '/'

    if not all([aws_access_key_id, aws_secret_access_key, bucket_name, prefix]):
        raise ValueError("All required environment variables must be set.")

    session = boto3.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )
    s3 = session.resource('s3')
    bucket = s3.Bucket(bucket_name)
    
    # List and delete objects within the specified prefix
    for obj in bucket.objects.filter(Prefix=prefix):
        obj.delete()

    print(f"All objects in '{prefix}' have been deleted from '{bucket_name}' bucket.")

@task
def setup_topology(ctx):
    source_dir = "./test/topology"
    destination_dir = "./runtime/topology"

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
    aws_s3_bucket = os.getenv('AWS_S3_BUCKET')
    aws_account_id, bucket_name_suffix = aws_s3_bucket.split('-', 1)

    # Prepare data for template replacement
    context = {
        'mina_docker_image': os.getenv('MINA_DAEMON_IMAGE'),
        'uptime_service_image': os.getenv('UPTIME_SERVICE_IMAGE'),
        'config_network_name': os.getenv('CONFIG_NETWORK_NAME'),
        'aws_keyspace': os.getenv('AWS_KEYSPACE'),
        'aws_region': os.getenv('AWS_REGION'),
        'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
        'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
        'aws_account_id': aws_account_id,
        'bucket_name_suffix': bucket_name_suffix
    }

    # Step 1: Update topology.json
    topology_json_path = os.path.join(destination_dir, "topology.json")
    with open(topology_json_path, 'r') as file:
        template = file.read()
    rendered = pystache.render(template, context)
    with open(topology_json_path, 'w') as file:
        file.write(rendered)

    # Step 2: Update app_config.json
    app_config_json_path = os.path.join(destination_dir, "uptime_service_config/app_config.json")
    with open(app_config_json_path, 'r') as file:
        template = file.read()
    rendered = pystache.render(template, context)
    with open(app_config_json_path, 'w') as file:
        file.write(rendered)

    print("Updated JSON files in the runtime topology directory.")

