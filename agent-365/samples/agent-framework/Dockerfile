# syntax=docker/dockerfile:1

# --- Stage 1: build ---
FROM python:slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Create a clean virtual environment
RUN python -m venv /opt/venv
# Update PATH so subsequent pip commands automatically use the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Install Python packages inside the virtual environment
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# --- Stage 2: runtime ---
FROM python:slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Permanently append the copied virtual environment to the runtime PATH
    PATH="/opt/venv/bin:$PATH" \
    HOST=0.0.0.0 \
    PORT=3978

# Create a non-root system user for security
RUN groupadd --system app && useradd --system --gid app --home /app app

WORKDIR /app

# 1. Copy the virtual environment from the builder stage
# 2. Automatically change ownership to the non-root user
COPY --from=builder --chown=app:app /opt/venv /opt/venv

# Copy application code (keep commented if mounting from volume)
# COPY --chown=app:app . .

# Switch away from root to the non-root application user
USER app

EXPOSE 3978

# Healthcheck using Python's built-in urllib to avoid installing curl/wget
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; from os import environ; urllib.request.urlopen('http://localhost:'+environ.get('PORT', '3978')+'/api/health', timeout=5)"

# Entrypoint binds 0.0.0.0:$PORT and serves /api/messages + /api/health.
CMD ["python", "start_with_generic_host.py"]