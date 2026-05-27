#!/bin/bash
echo "Starting FinOps Service..."
python manage.py makemigrations expenses
python manage.py migrate
gunicorn finops.wsgi:application --bind 0.0.0.0:8080 --workers 4 --threads 2 --timeout 30
