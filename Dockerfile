# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution and installation
RUN pip install uv

# Copy the project files
COPY pyproject.toml uv.lock ./

# Install project dependencies using uv
RUN uv sync --frozen

# Copy the rest of the application code
COPY . .

# Collect static files
# RUN uv run manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run gunicorn
CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "core.wsgi:application"]
