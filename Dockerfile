# Multi-stage build for efficient image size
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 scraper && \
    chown -R scraper:scraper /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/scraper/.local

# Copy application code
COPY --chown=scraper:scraper . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs && \
    chown -R scraper:scraper /app/data /app/logs

# Set environment variables
ENV PATH=/home/scraper/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER scraper

# Default command
CMD ["python", "main.py"]
