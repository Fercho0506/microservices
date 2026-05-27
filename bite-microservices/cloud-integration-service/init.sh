#!/bin/bash
echo "Starting Cloud Integration Service..."
python manage.py migrate
gunicorn cloud_integration.wsgi:application --bind 0.0.0.0:8081 --workers 2 --timeout 60
