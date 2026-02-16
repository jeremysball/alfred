#!/bin/bash
# Wrapper to run pi from local node_modules
cd /home/node/.openclaw/workspace/openclaw-pi
./node_modules/.bin/pi "$@"
