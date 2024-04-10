# Mina Delegation Program Tech

## Overview

This top-level repository serves as a central tech hub for the Mina Delegation Program, a comprehensive system designed to facilitate and manage the delegation program within the Mina blockchain network. The program comprises several key components, each with its specialized role in ensuring the efficiency and integrity of the delegation process. These components include:

1. **Uptime Service Backend** ([Repository](https://github.com/MinaFoundation/uptime-service-backend)): This service is responsible for collecting submissions from block producers within the Mina network. It acts as the primary data gathering endpoint, ensuring that submissions are timely and accurate for further processing. The data is gathered in Amazon Keyspaces and AWS S3.

2. **Uptime Service Validation (Coordinator)** ([Repository](https://github.com/MinaFoundation/uptime-service-validation)): Often referred to as the Coordinator, this component analyzes the submissions gathered by the Uptime Service Backend. Its primary function is to construct a delegation score based on the analyzed data.

3. **Stateless Verification Tool** ([Repository](https://github.com/MinaProtocol/mina/tree/develop/src/app/delegation_verify)): This tool is essential for maintaining the integrity of submissions. It performs stateless verification against each submission to ascertain its validity. This verification process is critical in ensuring that only legitimate and accurate data influences the delegation scores.

4. **Submission Updater** ([Repository](https://github.com/MinaFoundation/submission-updater)): This is a wrapper over the [Stateless verifier tool](https://github.com/MinaProtocol/mina/tree/develop/src/app/delegation_verify) that is responsible for communication with Cassandra database. It will select a range of submissions from Cassandra, feed `stateless_verifier_tool` with it, collect results and update submissions with gathered data. Typically `submission_updater` and `stateless_verifer_tool` are packaged into single docker image and work together as one component of the system.

5. **Leaderboard UI** ([Repository](https://github.com/MinaFoundation/delegation-program-leaderboard)): Website presenting block producer's availability scores. 

## Testing

As the overarching repository, this is also the home for end-to-end/system and load tests that validate the entire system's functionality. These tests are crucial for ensuring that each component of the Mina Delegation Program interacts seamlessly and performs as expected. A robust testing approach helps in identifying potential bottlenecks and ensures that the system can handle real-world use cases efficiently.

For recent test results go to [Test Reports](https://github.com/MinaFoundation/mina-delegation-program-tech/wiki/Test-Reports) page.

## E2E Tests

See [E2E Tests](https://github.com/MinaFoundation/mina-delegation-program-tech/tree/main/e2e_test).

## Load Tests

See [Load Tests](https://github.com/MinaFoundation/mina-delegation-program-tech/tree/main/load_test).

## Notes on Testing

- **Configuration**: Before running the tests, ensure that all configurations related to the network, databases, and services are correctly set up in accordance with the requirements of the Mina Delegation Program.
- **Monitoring**: While tests are running, it's advisable to monitor the outputs and logs for any anomalies or errors.
- **Re-running Tests**: To ensure reliability and consistency, you may need to run the tests multiple times, especially after making changes to any component of the system.

By following these steps, contributors and developers can effectively run end-to-end tests on the Mina Delegation Program, ensuring its robustness and reliability.
