## Load Tests

Load tests are an essential part of our testing strategy, designed to simulate real-world usage and ensure that the system can handle the expected traffic. These tests help us understand how the system behaves under heavy load conditions and identify any performance issues that need to be addressed.

### Tools and Scripts

For our load testing, we utilize [Locust](https://locust.io/), an easy-to-use, scriptable, and scalable performance testing tool. 

All necessary scripts for conducting load tests are located in the `./load_test` directory. This includes:

- **Test Scripts:** Python scripts (`*.py`) used by Locust to define user behavior and simulate traffic.
- **Resource Monitoring Scripts:** Bash scripts for monitoring system resources like CPU and memory usage during the tests (in case you run tests against local deployment).
- **Plotting Scripts:** Python scripts for visualizing the resource usage data and test results, aiding in the analysis (in case you run tests against local deployment).

### Running Load Tests

To run the load tests:

1. Navigate to the `./load_test` directory.
2. Activate the virtual environment with `poetry shell`.
3. Pick up a collection of payloads (see `./load_test/payload`). For instance to use payloads in `./load_test/payload/rc1` set `TEST_NAME=rc1` env var.
4. Pick up scenario.
 - basic - run `locust`.
 - random submitters - run `locust -f random_submitters.py`

5. Open your web browser and go to `http://localhost:8089` to access the Locust web interface.
6. Input the desired number of users, spawn rate, and host, then start the test by clicking the 'Start swarming' button.

Note that you can run test against local deployment of uptime-service-backend (typically host = `http://localhost:8080`) or deployment on one of the test environments (check with DevOps which hostname to use).

During the test, you can monitor the system's performance in real-time through the Locust web interface. For more detailed analysis, you can utilize the resource monitoring and plotting scripts to visualize system resource usage over time.

### Reports and Analysis

After each test, it's crucial to analyze the results to identify any performance bottlenecks or system behaviors that need to be addressed. The reports generated from the load tests can be found in the repository's [wiki](https://github.com/MinaFoundation/mina-delegation-program-tech/wiki). These reports provide a detailed analysis of the tests, including metrics like response times, the number of requests per second, and system resource usage.