#!/bin/bash

coordinator_log="./runtime/logs/coordinator.log"
docker_container_name="uptime-service-backend-e2e-test"
multitail -l "tail -1000f $coordinator_log" -l "docker logs $docker_container_name -f"
