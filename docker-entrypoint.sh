#!/bin/sh
set -eu
mkdir -p /data/photos
python /app/generate_pwa.py
exec python /app/app.py
