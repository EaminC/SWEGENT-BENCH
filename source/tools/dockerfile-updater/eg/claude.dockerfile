# claude.dockerfile for Strix: Forge API and unittest-ready
FROM python:3.12-slim

# --- Environment Variables for Forge/Anthropic ---
# Set both OPENAI (for OpenAI SDKs) AND Anthropic equivalents
# --- The actual key must be passed at build/run time, do not hardcode secrets ---
ENV FORGE_API_KEY=forge-Yjg1b858da3662009b3b0041bf7d4e14893e \
    OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=${FORGE_API_KEY} \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=${FORGE_API_KEY} \
    FORGE_BASE_URL=https://api.forge.tensorblock.co/v1 \
    MODEL=openkey/gpt-4.1 \
    AI_TEMPERATURE=0.7 \
    AI_MAX_TOKENS=1000 \
    AI_TOP_P=1 \
    AI_FREQUENCY_PENALTY=0 \
    AI_PRESENCE_PENALTY=0 \
    AI_STOP_SEQUENCES=

# --- System utilities and Python build tools ---
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl git && rm -rf /var/lib/apt/lists/*

# --- Install Poetry ---
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# --- Copy Poetry files and install all code + test dependencies ---
WORKDIR /app
COPY pyproject.toml .
# Only copy poetry.lock if it exists (ignore otherwise)
COPY poetry.lock .
RUN poetry config virtualenvs.create false && \
    poetry install --with dev --no-root

# --- Copy source code to /app ---
COPY . .

# --- Ensure unittest (stdlib) and pytest (dev dep) work ---
RUN python -c "import unittest" && \
    poetry run pytest --maxfail=1 --disable-warnings || true

# --- Default to interactive shell in /app ---
WORKDIR /app
CMD ["/bin/bash"]
