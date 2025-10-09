# mac-telem
Simple daemon that allows your mac to update a mongodb database with your battery, location and timestamp

!! Put the repo in a non-protected folder. Apple protects folders such as Desktop, Downloads, etc where the venv cannot be accessed by a launchagent.
- I suggest putting it in the ~ directory (home i.e. /Users/theodore ) or a custom subdir like ~/projects/

1. Create a python venv in this dir, then source activate, and install requirements.txt

2. Edit the plist and setup.sh to reflect your directories and move it into Library/Launchagents folder on mac

3. Run setup.sh