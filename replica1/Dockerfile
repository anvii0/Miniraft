FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The application code will be bind-mounted to /app/src,
# so we don't necessarily need to COPY it here,
# but we can copy a default version in case it runs without bind mount.
COPY src/ /app/src/

# Watchdog will be used to auto-reload
CMD ["watchmedo", "auto-restart", "--directory=./src", "--pattern=*.py", "--recursive", "--"]
