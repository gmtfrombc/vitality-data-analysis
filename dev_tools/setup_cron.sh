#!/bin/bash
# setup_cron.sh - Helper to set up the nightly cron job

# Get the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Create a temporary file with the current crontab plus our new job
crontab -l > /tmp/current_crontab 2>/dev/null || echo "# VP Data Analysis Cron Jobs" > /tmp/current_crontab
echo "" >> /tmp/current_crontab
echo "# Run self-test daily at 11:00 PM and show notification" >> /tmp/current_crontab
echo "0 23 * * * cd \"$PROJECT_DIR\" && ./nightly_test.sh" >> /tmp/current_crontab

# Check for duplicates (if this has been run before)
if [ "$(grep -c "nightly_test.sh" /tmp/current_crontab)" -gt 1 ]; then
    echo "WARNING: Duplicate entries detected. Please edit manually with 'crontab -e'"
    exit 1
fi

# Install the new crontab
crontab /tmp/current_crontab
rm /tmp/current_crontab

echo "✅ Cron job installed successfully!"
echo "The self-test will run automatically at 11:00 PM every night."
echo "You will receive a desktop notification with the results."
echo ""
echo "To view your cron jobs: crontab -l"
echo "To edit your cron jobs: crontab -e"

# Test that notifications work
echo "Testing desktop notification..."
osascript -e 'display notification "Notification system is working correctly!" with title "Test Notification" sound name "Submarine"' 