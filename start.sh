#!/usr/bin/env bash
set -e
PORT="${PORT:-10000}"
exec gunicorn -w 2 -b "0.0.0.0:${PORT}" "wsgi:application"
