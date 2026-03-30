FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Improve apt reliability (switch http->https where possible, add retries), then install deps
RUN set -eux; \
    if [ -f /etc/apt/sources.list ]; then sed -i -e 's|http://|https://|g' /etc/apt/sources.list; fi; \
    if [ -d /etc/apt/sources.list.d ]; then find /etc/apt/sources.list.d -type f -name '*.list' -exec sed -i -e 's|http://|https://|g' {} + ; fi; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then sed -i -e 's|http://|https://|g' /etc/apt/sources.list.d/debian.sources; fi; \
    echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80-retries; \
    apt-get update -o Acquire::Retries=5; \
    apt-get install -y --no-install-recommends gcc curl; \
    rm -rf /var/lib/apt/lists/*

# Copy requirements files (runtime excludes clerk-sdk-python which conflicts with pydantic v2)
COPY requirements.runtime.txt ./requirements.txt

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port (can be overridden by docker-compose)
EXPOSE 8000

# Default command: use PORT env (Render sets 10000) or 8000 for local
CMD ["sh", "-c", "uvicorn services.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

