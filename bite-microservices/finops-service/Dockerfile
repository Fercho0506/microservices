FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=finops.settings
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

ENTRYPOINT ["sh", "init.sh"]
