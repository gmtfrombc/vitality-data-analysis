#!/bin/bash

echo "Killing Panel/Tornado/Jupyter processes..."

# Kill any Python servers
pkill -f "python run.py"
pkill -f "panel serve"
pkill -f "bokeh serve"
pkill -f "tornado"
pkill -f "jupyter"

# Kill any zombie processes
zombie_pids=$(ps axo pid,stat | grep Z | awk '{print $1}')
if [ -n "$zombie_pids" ]; then
    echo "Found zombie processes, killing their parents..."
    for pid in $zombie_pids; do
        ppid=$(ps -o ppid= -p $pid)
        if [ -n "$ppid" ]; then
            echo "Killing parent process $ppid of zombie $pid"
            kill -9 $ppid
        fi
    done
fi

# Check for any remaining processes
remaining=$(ps aux | grep -E 'python|panel|bokeh|tornado|jupyter' | grep -v grep | grep -v "kill_panel.sh")
if [ -n "$remaining" ]; then
    echo "Some processes might still be running:"
    echo "$remaining"
    echo "You might need to manually kill them or restart your computer."
else
    echo "All processes successfully terminated."
fi

echo "Cleanup complete." 