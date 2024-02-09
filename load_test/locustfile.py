import json
import os
import random
from locust import HttpUser, TaskSet, task, between

# Get the test name from an environment variable
TEST_NAME = os.environ.get("TEST_NAME", "rc1")
print("-----------------------------------")
print(f"Test name: {TEST_NAME}")
print(f"Payload directory: ./payload/{TEST_NAME}")
print("To change the test name, set the TEST_NAME environment variable.")
print("-----------------------------------")

# Construct the payload directory path based on the test name
PAYLOAD_DIR = f"./payload/{TEST_NAME}"

TARGET_EP = "/v1/submit"


class UserBehavior(TaskSet):
    @task
    def submit_payload(self):
        files = os.listdir(PAYLOAD_DIR)
        files = [file for file in files if file.endswith(".json")]
        selected_file = random.choice(files)

        # Load the payload from the randomly selected file
        with open(f"{PAYLOAD_DIR}/{selected_file}", "r") as file:
            payload = json.load(file)

        headers = {"Content-Type": "application/json"}
        self.client.post(TARGET_EP, json=payload, headers=headers)


class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    wait_time = between(5, 15)
