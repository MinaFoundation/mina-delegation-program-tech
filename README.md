# Mina Delegation Program Tech

## Overview

This top-level repository serves as a central tech hub for the Mina Delegation Program, a comprehensive system designed to facilitate and manage the delegation program within the Mina blockchain network. The program comprises several key components, each with its specialized role in ensuring the efficiency and integrity of the delegation process. These components include:

1. **Uptime Service Backend** ([Repository](https://github.com/MinaFoundation/uptime-service-backend)): This service is responsible for collecting submissions from block producers within the Mina network. It acts as the primary data gathering endpoint, ensuring that submissions are timely and accurate for further processing. The data is gathered in Amazon Keyspaces and AWS S3.

2. **Uptime Service Validation (Coordinator)** ([Repository](https://github.com/MinaFoundation/uptime-service-validation)): Often referred to as the Coordinator, this component analyzes the submissions gathered by the Uptime Service Backend. Its primary function is to construct a delegation score based on the analyzed data.

3. **Stateless Verification Tool** ([Pull Request](https://github.com/MinaProtocol/mina/pull/14593)): This tool is essential for maintaining the integrity of submissions. Run by the Coordinator, it performs stateless verification against each submission to ascertain its validity. This verification process is critical in ensuring that only legitimate and accurate data influences the delegation scores.

## End-to-End (E2E) Testing

As the overarching repository, this is also the home for end-to-end tests that validate the entire system's functionality. These tests are crucial for ensuring that each component of the Mina Delegation Program interacts seamlessly and performs as expected.

## Running E2E Tests from GH Workflow

## Running E2E Tests Locally

The end-to-end (E2E) testing framework for the Mina Delegation Program is designed to comprehensively evaluate the integration and functionality of the entire system. We utilize Python's Invoke library to manage and run these tests. Below are the steps and commands to execute the E2E tests.

### Prerequisites

Before running the E2E tests, ensure you have the following:

1. **Poetry**: Run `poetry shell` in the repository's root to set up the Python environment and install all necessary dependencies.
2. **Docker**: Required for testing the `uptime-service-backend`, `stateless_verifier`. The test also sets up `postgres` docker image
which is required for `uptime-service-validation` (coordinator).

### Test Execution Process

1. **Test Setup (`invoke test setup`)**: This command prepares the testing environment. It involves setting up the Amazon Keyspaces database, ensuring the S3 bucket is empty, configuring the Postgres database, and initializing the Mina network along with the uptime service backend, coordinator, and stateless_verifier.

2. **Start Test (`invoke test start`)**: This command launches the test by starting the Mina network and the coordinator along with the stateless_verifier. This step simulates the operational environment of the Mina Delegation Program, allowing for real-time interaction and data processing.

3. **Stop Test (`invoke test stop`)**: Use this command to halt the test. It effectively stops all operations initiated by the 'invoke test start' command. This is useful for temporarily halting the test process for analysis or debugging.

4. **Test Teardown (`invoke test teardown`)**: This final command is used to clean up the testing environment post-testing. It clears the Amazon Keyspaces, S3 buckets, and the Postgres database, ensuring that the environment is reset for subsequent tests.

### Notes on Testing

- **Configuration**: Before running the tests, ensure that all configurations related to the network, databases, and services are correctly set up in accordance with the requirements of the Mina Delegation Program.
- **Monitoring**: While tests are running, it's advisable to monitor the outputs and logs for any anomalies or errors.
- **Re-running Tests**: To ensure reliability and consistency, you may need to run the tests multiple times, especially after making changes to any component of the system.

By following these steps, contributors and developers can effectively run end-to-end tests on the Mina Delegation Program, ensuring its robustness and reliability.