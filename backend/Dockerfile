# Backend Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose default port (Railway injects PORT)
EXPOSE 5001

# Run with gunicorn for production (use PORT env when provided)
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT:-5001} -w 2 --timeout 120 app:app"]
