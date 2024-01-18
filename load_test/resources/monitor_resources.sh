#!/bin/bash

if [ "$#" -ne 4 ]; then
    echo "Usage: $0 DURATION INTERVAL OUTPUT_FILE PID"
    exit 1
fi

DURATION=$1
INTERVAL=$2
OUTPUT_FILE=$3
PID=$4

echo "Monitoring CPU and Memory usage for process $PID for $DURATION seconds. Interval: $INTERVAL seconds."

# Write header to the output file
echo "Time %CPU MEM(MB)" > $OUTPUT_FILE

END_TIME=$((SECONDS+DURATION))

while [ $SECONDS -lt $END_TIME ]; do
    # Fetch %CPU and rss (memory usage in KB), then convert rss to MB
    ps -p $PID -o %cpu,rss --no-headers | awk -v OFS='\t' -v interval=$INTERVAL '{mem_in_mb=$2/1024; printf "%s %s %.2f\n", strftime("%Y-%m-%d %H:%M:%S"), $1, mem_in_mb}' >> $OUTPUT_FILE
    sleep $INTERVAL
done

echo "Monitoring completed."
