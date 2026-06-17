# mac-telem

One-shot telemetry job that updates a MongoDB document with your Mac's battery, location, and timestamp. A LaunchAgent runs `report.sh` every 5 minutes (and once at login).

!! Put the repo in a non-protected folder. Apple protects folders such as Desktop, Downloads, etc where the venv cannot be accessed by a launchagent.
- I suggest putting it in the ~ directory (home i.e. /Users/theodore ) or a custom subdir like ~/projects/

1. Create a python venv in this dir, then source activate, and install requirements.txt

2. Create a `.env` file with `MONGODB_URI` (and optional overrides like `MONGO_DB`, `MONGO_COLLECTION`)

3. Edit `com.theodore.telemetry.plist` and `setup.sh` paths if your home directory differs

4. Symlink your plist from this repo into the launchagents folder that macos uses:
    ln -sf /Users/theodore/mac-telem/com.theodore.telemetry.plist ~/Library/LaunchAgents/com.theodore.telemetry.plist

5. Run setup.sh

## Manual test

```bash
./report.sh
```

## How it works

- `report.sh` waits briefly for network, activates the venv, and runs `telemetry_daemon.py` once
- The Python script collects battery + location, upserts `_id: "current"` in MongoDB, then exits
- LaunchAgent uses `StartInterval` (300s) instead of a long-running process with `KeepAlive`
