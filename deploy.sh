#!/bin/bash
rm -rf nasdaq-watchdog
unzip nasdaq-watchdog.zip
cd nasdaq-watchdog
git init
git branch -M main
git remote add origin https://github.com/6ayoob/nasdaq-watchdog.git
git add .
git commit -m "Initial full version with bot token"
git push -f origin main
