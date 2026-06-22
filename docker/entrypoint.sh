#!/usr/bin/env sh
set -eu

# Defaults (can be overridden via environment)
: "${DB_HOST:=db}"
: "${DB_PORT:=3306}"
: "${DB_NAME:=job_portal_db}"
: "${DB_USER:=root}"
: "${DB_PASSWORD:=StrongPass123}"

# Wait for MySQL
# Uses a lightweight check via python (avoids installing extra tools)
python - <<'PY'
import os, time
import socket
host=os.environ.get('DB_HOST','db')
port=int(os.environ.get('DB_PORT','3306'))
for _ in range(60):
    try:
        s=socket.create_connection((host,port),timeout=2)
        s.close()
        break
    except OSError:
        time.sleep(2)
else:
    raise SystemExit('Timed out waiting for MySQL')
PY

# Run migrations
python manage.py migrate --noinput

# Create superuser is optional; app includes a command, but we don't run it automatically
# unless credentials are provided.

# Collect static (safe even if unused)
python manage.py collectstatic --noinput 2>/dev/null || true

# Start server (Gunicorn if available)
if python -c "import gunicorn" 2>/dev/null; then
  exec gunicorn job_portal.wsgi:application --bind 0.0.0.0:8000 --workers 3
else
  exec python manage.py runserver 0.0.0.0:8000
fi

