#!/bin/bash
# nightly_test.sh - Run the self-test and send a desktop notification
# This script is designed to be run by cron at 11:00 PM nightly

# Navigate to the project directory
cd "$(dirname "$0")"

# Set up log directory for this run
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_DIR="logs/nightly_test_${TIMESTAMP}"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/nightly_test.log"

# Run the self-test
echo "Starting nightly self-test at $(date)" | tee -a "$LOG_FILE"
./run_self_test.sh 2>&1 | tee -a "$LOG_FILE"
TEST_EXIT_CODE=${PIPESTATUS[0]}

# Prepare notification message
if [ $TEST_EXIT_CODE -eq 0 ]; then
    NOTIFICATION_TITLE="Self-Test Passed"
    NOTIFICATION_TEXT="All tests passed successfully! Check logs for details."
    ALERT_ICON="✅"
else
    NOTIFICATION_TITLE="Self-Test Failed"
    NOTIFICATION_TEXT="$(grep -c "failed" "$LOG_FILE") tests failed. Check logs for details."
    ALERT_ICON="❌"
fi

# Send desktop notification using multiple methods for reliability
echo "Sending notification: $NOTIFICATION_TITLE - $NOTIFICATION_TEXT" | tee -a "$LOG_FILE"

# PRIMARY METHOD: Use AppleScript alert (confirmed working)
osascript -e "tell application \"System Events\" to display alert \"${ALERT_ICON} ${NOTIFICATION_TITLE}\" message \"${NOTIFICATION_TEXT}\""

# BACKUP METHODS (may not work in all contexts but included for redundancy)
# Try basic notification
osascript -e "display notification \"${NOTIFICATION_TEXT}\" with title \"${NOTIFICATION_TITLE}\" sound name \"Submarine\"" 2>/dev/null

# Use terminal-notifier if available
if command -v terminal-notifier &> /dev/null; then
    terminal-notifier -title "${NOTIFICATION_TITLE}" -message "${NOTIFICATION_TEXT}" -sound "Submarine"
fi

# Create a log file on Desktop with prominent name for visibility
DESKTOP_LOG="${HOME}/Desktop/SELFTEST_${TIMESTAMP}_${TEST_EXIT_CODE}.log"
echo "${ALERT_ICON} ${NOTIFICATION_TITLE} - ${NOTIFICATION_TEXT}" > "$DESKTOP_LOG"
echo "Test completed at $(date)" >> "$DESKTOP_LOG"
echo "Logs available at: ${LOG_DIR}" >> "$DESKTOP_LOG"

# Add summary to log
echo "Nightly test completed at $(date)" | tee -a "$LOG_FILE"
echo "Exit code: $TEST_EXIT_CODE" | tee -a "$LOG_FILE"
echo "Notification sent: $NOTIFICATION_TITLE - $NOTIFICATION_TEXT" | tee -a "$LOG_FILE"
echo "Desktop log created: $DESKTOP_LOG" | tee -a "$LOG_FILE"

exit $TEST_EXIT_CODE 