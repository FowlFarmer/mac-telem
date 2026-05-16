#!/bin/bash

# Wait until network dns settles
sleep 15

cd /Users/theodore/mac-telem
source venv/bin/activate

exec python3 telemetry_daemon.py