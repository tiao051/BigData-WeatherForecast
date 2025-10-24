# Use Python 3.11 for compatibility with pandas/numpy
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required by pandas & numpy
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy producer script
COPY producer.py .

# Create dataset directory (read-only volume in compose)
RUN mkdir -p /app/dataset

# Default command (overridden in compose)
CMD ["python", "producer.py", "--continuous", "--delay", "1"]
