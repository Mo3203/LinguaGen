#!/bin/bash
# Double-click this file to start the application.
cd "$(dirname "$0")" || exit 1
PORT=8000
while lsof -i :$PORT >/dev/null 2>&1; do PORT=$((PORT+1)); done
echo "Language Study is running."
echo
echo "  On this computer:  http://localhost:$PORT"
IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
[ -n "$IP" ] && echo "  On your phone:     http://$IP:$PORT"
echo
echo "Keep this window open while you study. Press Control and C to stop."
echo
( sleep 1; open "http://localhost:$PORT" ) &
python3 -m http.server $PORT
