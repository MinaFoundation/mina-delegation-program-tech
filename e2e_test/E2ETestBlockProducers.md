## E2E Test With Block Producers

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
 - `SUBMISSION_STORAGE` - set to `POSTGRES` or `CASSANDRA`, depending on which storage option you want to test.

1. **Test Setup (`invoke test setup`)**: This command prepares the testing environment. It involves setting up the Amazon Keyspaces database, ensuring the S3 bucket is empty, configuring the Postgres database, and initializing the Mina network along with the uptime service backend, coordinator, and stateless_verifier.

2. **Start Test (`invoke test start`)**: This command launches the test by starting the Mina network and the coordinator along with the stateless_verifier. This step simulates the operational environment of the Mina Delegation Program, allowing for real-time interaction and data processing.

3. **Wait for verified submissions (`invoke test wait`)**: This command will wait until the system receives submissions and they get validated. When the command stops that means system is in a state when further assertions can be made.

4. **Stop Test (`invoke test stop`)**: Use this command to halt the test. It effectively stops all operations initiated by the 'invoke test start' command. This is useful for temporarily halting the test process for analysis or debugging.

5. **Make assertions (`invoke test assert`)**: Use this command to cross-check data in Amazon S3 and Keyspaces and Postgres database. The assertions in this step verify data integrity after the test between all those data buckets. The task also checks logs for errors. 

6. **Test Teardown (`invoke test teardown`)**: This final command is used to clean up the testing environment post-testing. It clears the Amazon Keyspaces, S3 buckets, and the Postgres database, ensuring that the environment is reset for subsequent tests.
