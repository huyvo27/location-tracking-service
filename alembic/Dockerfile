# Use slim Python image
FROM python:3.12.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # netcat-openbsd \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_VERSION=1.8.2
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml poetry.lock ./
COPY . .

# Install only alembic dependencies
RUN poetry install --no-root --no-interaction --no-ansi --with alembic

# Default command
ENTRYPOINT ["poetry", "run", "alembic"]
