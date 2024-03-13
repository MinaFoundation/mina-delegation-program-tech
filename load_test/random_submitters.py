import json
import os
import random
from locust import HttpUser, TaskSet, task, between

# Get the test name from an environment variable
TEST_NAME = os.environ.get("TEST_NAME", "rc1")

# Construct the payload directory path based on the test name
PAYLOAD_DIR = f"./payload/{TEST_NAME}"

# Load submitters
with open("submitters.json", "r") as file:
    SUBMITTERS = json.load(file)["submitters"]

TARGET_EP = "/v1/submit"

print("-----------------------------------")
print(f"Test name: {TEST_NAME}")
print(f"Payload directory: ./payload/{TEST_NAME}")
print(f"Number of submitters: {len(SUBMITTERS)}")
print("To change the test name, set the TEST_NAME environment variable.")
print("-----------------------------------")


class UserBehavior(TaskSet):
    @task
    def submit_payload(self):
        # Select a random payload file
        files = os.listdir(PAYLOAD_DIR)
        files = [file for file in files if file.endswith(".json")]
        selected_file = random.choice(files)

        # Load the payload
        with open(f"{PAYLOAD_DIR}/{selected_file}", "r") as file:
            payload = json.load(file)

        # Randomly select a submitter and assign to the payload
        random_submitter = random.choice(SUBMITTERS)
        payload["submitter"] = random_submitter

        headers = {"Content-Type": "application/json"}
        self.client.post(TARGET_EP, json=payload, headers=headers)


class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    wait_time = between(1, 5)
