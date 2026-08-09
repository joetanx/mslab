# syntax=docker/dockerfile:1

# Start from official Jupyter minimal notebook image
FROM quay.io/jupyter/minimal-notebook:latest

# Copy pyproject.toml configuration into the container
COPY --chown=1000:100 pyproject.toml .

# Install dependencies
RUN pip install --no-cache-dir . && rm pyproject.toml

# Start Jupyter with password hash from env
CMD ["/bin/bash", "-c", ": \"${JUPYTER_PASSWORD_HASH:?JUPYTER_PASSWORD_HASH is required}\"; exec start-notebook.py --notebook-dir=/home/jovyan/work --PasswordIdentityProvider.hashed_password=\"$JUPYTER_PASSWORD_HASH\""]
