FROM python:3.11

# Use noninteractive frontend to avoid prompts during package installation and
# make apt-get more resilient to transient network/mirror issues by attempting
# a fallback install with --fix-missing if the first install fails.
ENV DEBIAN_FRONTEND=noninteractive
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl gnupg apt-transport-https || true; \
    apt-get update; \
    if ! apt-get install -y --no-install-recommends build-essential curl ca-certificates gcc libpq-dev; then \
        echo "Primary apt install failed, retrying with --fix-missing"; \
        apt-get update --fix-missing; \
        apt-get install -y --no-install-recommends --fix-missing build-essential curl ca-certificates gcc libpq-dev; \
    fi; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker cache.
COPY requirements.txt /app/requirements.txt

# Install python dependencies.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy application source
COPY . /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose API port
EXPOSE 8000

# Default command to run the FastAPI application using Uvicorn.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
