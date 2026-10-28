#!/bin/sh
set -eu

python /app/docker/wait_for_db.py
exec alembic upgrade head
