#!/bin/bash
set -e

# Ensure the instance/db directory exists.
mkdir -p /flask-app/instance/db

# If the database file does not exist in the mounted volume, run the parser script.
if [ ! -f /flask-app/instance/db/quiz.db ]; then
    echo "Database not found. Running parse_md_to_db.py to create it..."
    python parse_md_to_db.py
    # Move the created database to the persistent directory.
    mv quiz.db /flask-app/instance/db/quiz.db
fi

# Start the Flask application.
exec flask run --host=0.0.0.0
