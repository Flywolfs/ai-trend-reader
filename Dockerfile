FROM python:3.12-slim

# Install cron
RUN apt-get update && apt-get install -y --no-install-recommends cron && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency file first for better layer caching
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source code
COPY src/ src/
COPY config.example.yaml config.example.yaml

# Copy crontab
COPY crontab /etc/cron.d/trend-reader
RUN chmod 0644 /etc/cron.d/trend-reader && crontab /etc/cron.d/trend-reader

# Create data directory
RUN mkdir -p /app/data

# Install the package
RUN pip install --no-cache-dir -e .

# Default: run cron in foreground
# Use `docker run ... python -m ai_trend_reader` for one-shot execution
CMD ["cron", "-f"]
