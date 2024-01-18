import json
import os
import random
from locust import HttpUser, TaskSet, task, between

TARGET_EP = "http://localhost:8080/v1/submit"


class UserBehavior(TaskSet):
    @task
    def submit_payload(self):
        files = os.listdir("./payload")
        files = [file for file in files if file.endswith(".json")]
        selected_file = random.choice(files)

        # Load the payload from the randomly selected file
        with open(f"./payload/{selected_file}", "r") as file:
            payload = json.load(file)

        headers = {"Content-Type": "application/json"}
        self.client.post(TARGET_EP, json=payload, headers=headers)


class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    wait_time = between(5, 15)
