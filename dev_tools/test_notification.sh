#!/bin/bash
# Simple script to test if macOS notifications are working

echo "Testing macOS notification system..."

# Try different notification methods
echo "Method 1: Using osascript with display notification"
osascript -e 'display notification "This is a test notification" with title "Test 1" sound name "Submarine"'
sleep 2

echo "Method 2: Using terminal-notifier if available"
if command -v terminal-notifier &> /dev/null; then
    terminal-notifier -title "Test 2" -message "This is a terminal-notifier test" -sound "Submarine"
else
    echo "terminal-notifier not installed. You can install it with: brew install terminal-notifier"
fi
sleep 2

echo "Method 3: Using AppleScript alert"
osascript -e 'tell application "System Events" to display alert "Test Alert" message "This is a test alert"'

echo "Notification tests complete!"
echo ""
echo "If you didn't see any notifications, please check:"
echo "1. System Preferences → Notifications → Terminal (or iTerm) should be allowed"
echo "2. Make sure you're not in Do Not Disturb mode"
echo "3. If using a terminal in VS Code/Cursor, try running from Terminal.app instead" 