# syntax=docker/dockerfile:1
FROM python:3.12-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching)
COPY requirements.txt requirements_prod.txt ./
RUN pip install --no-cache-dir -r requirements_prod.txt

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput \
    --settings=arokah.settings_production 2>/dev/null || true

EXPOSE 8000

CMD ["gunicorn", "arokah.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--timeout", "120", \
     "--access-logfile", "-"]
