

# Gotta add fileperms: go to settings, search for file access, then do cmd+shift+g to set absolute path, then add /usr/bin/python3 
# edit theodore to whatever ur mac home name is and stick the plist in ~/Library/LaunchAgents/

/usr/bin/python3 -m pip install --user pymongo psutil pyobjc python-dotenv
launchctl unload ~/Library/LaunchAgents/com.theodore.telemetry.plist 2>/dev/null || true
launchctl load   ~/Library/LaunchAgents/com.theodore.telemetry.plist
launchctl start  com.theodore.telemetry
tail -f ~/Library/Logs/telemetry.stderr.log