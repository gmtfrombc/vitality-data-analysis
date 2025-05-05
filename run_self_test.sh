#!/bin/bash
# Daily self-test runner for the Data Analysis Assistant
# This script can be added to crontab to run daily tests
# Example crontab entry: 0 0 * * * /path/to/run_self_test.sh

# Navigate to the project root directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set up environment variables
# Uncomment and adjust these if using email notifications
# export SMTP_SERVER=smtp.example.com
# export SMTP_PORT=587
# export SMTP_USER=username
# export SMTP_PASSWORD=password
# export NOTIFICATION_SENDER=selftest@example.com

# Set offline mode - this avoids OpenAI API calls during testing
export OPENAI_API_KEY=""

# Create timestamp for this run
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")

# Create logs directory if it doesn't exist
mkdir -p logs

# Run the self-test
echo "Starting self-test run at ${TIMESTAMP} (OFFLINE MODE)"
python -m tests.golden.synthetic_self_test \
    --output-dir="logs/self_test_${TIMESTAMP}" \
    # Uncomment the following line to enable email notifications
    # --notify --recipients="your-email@example.com" \
    2>&1 | tee "logs/self_test_${TIMESTAMP}.log"

# Store the exit code
EXIT_CODE=$?

# Log the result
if [ $EXIT_CODE -eq 0 ]; then
    echo "Self-test completed successfully at $(date)"
else
    echo "Self-test failed with exit code ${EXIT_CODE} at $(date)"
fi

# Exit with the same code as the test
exit $EXIT_CODE 