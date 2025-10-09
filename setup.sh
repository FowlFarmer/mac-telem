

# Gotta add fileperms: go to settings, search for file access, then do cmd+shift+g to set absolute path, then add /usr/bin/python3 
# edit theodore to whatever ur mac home name is and stick the plist in ~/Library/LaunchAgents/

# Make sure to set up the venv in this repo initally with requirements.txt

rm -rf ~/Library/Logs/telemetry.stderr.log
launchctl unload ~/Library/LaunchAgents/com.theodore.telemetry.plist 2>/dev/null || true
launchctl load   ~/Library/LaunchAgents/com.theodore.telemetry.plist
launchctl start  com.theodore.telemetry
tail -f ~/Library/Logs/telemetry.stderr.log