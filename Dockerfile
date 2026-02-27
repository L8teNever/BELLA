FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tar \
    gzip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for database
RUN mkdir -p /app/data

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Expose port
EXPOSE 5000

# Environment variables
ENV FLASK_APP=main.py
ENV PYTHONUNBUFFERED=1

# Use entrypoint script (auto-fixes Docker socket permissions)
ENTRYPOINT ["/app/entrypoint.sh"]
