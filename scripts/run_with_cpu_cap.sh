#!/usr/bin/env bash
# Run a process with CPU usage cap using background monitoring
# This is a macOS-compatible CPU throttling solution

set -euo pipefail

if [ $# -lt 2 ]; then
    echo "Usage: $0 <cpu_limit_percent> <command> [args...]"
    echo "Example: $0 50 python -m llama_cpp.server --model model.gguf"
    exit 1
fi

CPU_LIMIT=$1
shift
COMMAND="$@"

# Start the command in background
echo "Starting command with ${CPU_LIMIT}% CPU limit: $COMMAND"
$COMMAND &
TARGET_PID=$!
echo "Process PID: $TARGET_PID"

# Monitor and throttle in background
(
    while kill -0 $TARGET_PID 2>/dev/null; do
        # Get CPU usage
        CPU_PCT=$(ps -p $TARGET_PID -o %cpu= 2>/dev/null | awk '{print int($1)}' || echo "0")

        if [ "$CPU_PCT" -gt "$CPU_LIMIT" ]; then
            # Suspend process briefly to throttle
            kill -STOP $TARGET_PID 2>/dev/null || true
            sleep 0.1
            kill -CONT $TARGET_PID 2>/dev/null || true
            sleep 0.1
        else
            sleep 0.2
        fi
    done
) &
MONITOR_PID=$!

# Wait for main process
wait $TARGET_PID 2>/dev/null
EXIT_CODE=$?

# Clean up monitor
kill $MONITOR_PID 2>/dev/null || true

exit $EXIT_CODE
