# Mina Delegation Program Tech

## Overview

This top-level repository serves as a central tech hub for the Mina Delegation Program, a comprehensive system designed to facilitate and manage the delegation program within the Mina blockchain network. The program comprises several key components, each with its specialized role in ensuring the efficiency and integrity of the delegation process. These components include:

1. **Uptime Service Backend** ([Repository](https://github.com/MinaFoundation/uptime-service-backend)): This service is responsible for collecting submissions from block producers within the Mina network. It acts as the primary data gathering endpoint, ensuring that submissions are timely and accurate for further processing. The data is gathered in Amazon Keyspaces and AWS S3.

2. **Uptime Service Validation (Coordinator)** ([Repository](https://github.com/MinaFoundation/uptime-service-validation)): Often referred to as the Coordinator, this component analyzes the submissions gathered by the Uptime Service Backend. Its primary function is to construct a delegation score based on the analyzed data.

3. **Stateless Verification Tool** ([Pull Request](https://github.com/MinaProtocol/mina/pull/14593)): This tool is essential for maintaining the integrity of submissions. Run by the Coordinator, it performs stateless verification against each submission to ascertain its validity. This verification process is critical in ensuring that only legitimate and accurate data influences the delegation scores.

## Testing

As the overarching repository, this is also the home for end-to-end/system and load tests that validate the entire system's functionality. These tests are crucial for ensuring that each component of the Mina Delegation Program interacts seamlessly and performs as expected. A robust testing approach helps in identifying potential bottlenecks and ensures that the system can handle real-world use cases efficiently.

For recent test results go to [Test Reports](https://github.com/MinaFoundation/mina-delegation-program-tech/wiki/Test-Reports) page.

## E2E Tests

The end-to-end (E2E) testing framework for the Mina Delegation Program is designed to comprehensively evaluate the integration and functionality of the entire system. We utilize Python's Invoke library to manage and run these tests.

The diagram below illustrates the end-to-end test of the whole system:

![e2e_test](https://github.com/MinaFoundation/mina-delegation-program-tech/assets/42900201/aed5fc69-ba0a-4380-bfae-0c68c5a4616c)

### Running E2E Tests from GH Workflow

Navigate to [E2E Test Mina Delegation Program](https://github.com/MinaFoundation/mina-delegation-program-tech/actions/workflows/e2e.yml) and run the workflow filling all the reqiored parameters.

### Running E2E Tests Locally

Below are the steps and commands to execute the E2E tests locally.

#### Prerequisites

Before running the E2E tests, ensure you have the following:

1. **Poetry**: Run `poetry shell` in the repository's root to set up the Python environment and install all necessary dependencies.
2. **Docker**: Required for testing the `uptime-service-backend`, `stateless_verifier`. The test also sets up `postgres` docker image
which is required for `uptime-service-validation` (coordinator).
3. **Login to ECR**: Make sure to be logged into ECR to be able to get required docker images for `uptime-service-backend` and `stateless_verifier`.

#### Test Execution Process

Before starting make sure to have following env variables set:
 - `E2E_SECRET` - secret required for decoding `./test/config/.env` file hodling env variables required to set connection to Amazon Keyspaces, S3 and Postgres database.
 - `MINA_DAEMON_IMAGE` - mina daemon image to start private mina network (using `minimina`).
 - `UPTIME_SERVICE_IMAGE` - uptime service image to test against.
 - `COORDINATOR_BRANCH` - uptime service validation (coordinator) branch/tag to test against.
 - `STATELESS_VERIFIER_IMAGE` - stateless verifier image to test against.

1. **Test Setup (`invoke test setup`)**: This command prepares the testing environment. It involves setting up the Amazon Keyspaces database, ensuring the S3 bucket is empty, configuring the Postgres database, and initializing the Mina network along with the uptime service backend, coordinator, and stateless_verifier.

2. **Start Test (`invoke test start`)**: This command launches the test by starting the Mina network and the coordinator along with the stateless_verifier. This step simulates the operational environment of the Mina Delegation Program, allowing for real-time interaction and data processing.

3. **Wait for verified submissions (`invoke test wait`)**: This command will wait until the system receives submissions and they get validated. When the command stops that means system is in a state when further assertions can be made.

4. **Stop Test (`invoke test stop`)**: Use this command to halt the test. It effectively stops all operations initiated by the 'invoke test start' command. This is useful for temporarily halting the test process for analysis or debugging.

5. **Make assertions (`invoke test assert`)**: Use this command to cross-check data in Amazon S3 and Keyspaces and Postgres database. The assertions in this step verify data integrity after the test between all those data buckets. The task also checks logs for errors. 

6. **Test Teardown (`invoke test teardown`)**: This final command is used to clean up the testing environment post-testing. It clears the Amazon Keyspaces, S3 buckets, and the Postgres database, ensuring that the environment is reset for subsequent tests.

## Load Tests

Load tests are an essential part of our testing strategy, designed to simulate real-world usage and ensure that the system can handle the expected traffic. These tests help us understand how the system behaves under heavy load conditions and identify any performance issues that need to be addressed.

### Tools and Scripts

For our load testing, we utilize [Locust](https://locust.io/), an easy-to-use, scriptable, and scalable performance testing tool. 

All necessary scripts for conducting load tests are located in the `./load_test` directory. This includes:

- **Test Scripts:** Python scripts (`*.py`) used by Locust to define user behavior and simulate traffic.
- **Resource Monitoring Scripts:** Bash scripts for monitoring system resources like CPU and memory usage during the tests.
- **Plotting Scripts:** Python scripts for visualizing the resource usage data and test results, aiding in the analysis.

### Running Load Tests

To run the load tests:

1. Navigate to the `./load_test` directory.
2. Activate the virtual environment with `poetry shell`.
3. Start the Locust server by running the `locust` command.
4. Open your web browser and go to `http://localhost:8089` to access the Locust web interface.
5. Input the desired number of users, spawn rate, and host, then start the test by clicking the 'Start swarming' button.

During the test, you can monitor the system's performance in real-time through the Locust web interface. For more detailed analysis, you can utilize the resource monitoring and plotting scripts to visualize system resource usage over time.

### Reports and Analysis

After each test, it's crucial to analyze the results to identify any performance bottlenecks or system behaviors that need to be addressed. The reports generated from the load tests can be found in the repository's [wiki](https://github.com/MinaFoundation/mina-delegation-program-tech/wiki). These reports provide a detailed analysis of the tests, including metrics like response times, the number of requests per second, and system resource usage.

## Notes on Testing

- **Configuration**: Before running the tests, ensure that all configurations related to the network, databases, and services are correctly set up in accordance with the requirements of the Mina Delegation Program.
- **Monitoring**: While tests are running, it's advisable to monitor the outputs and logs for any anomalies or errors.
- **Re-running Tests**: To ensure reliability and consistency, you may need to run the tests multiple times, especially after making changes to any component of the system.

By following these steps, contributors and developers can effectively run end-to-end tests on the Mina Delegation Program, ensuring its robustness and reliability.
