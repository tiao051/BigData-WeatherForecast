FROM openjdk:11-jre-slim

# Install Python 3.10 and required packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Set Python as default
RUN ln -s /usr/bin/python3 /usr/bin/python

# Set JAVA_HOME
ENV JAVA_HOME=/usr/local/openjdk-11
ENV PATH=$PATH:$JAVA_HOME/bin

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY webapp/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY webapp/ .

# Copy trained ML models from host machine to container
# These models can be loaded locally instead of from HDFS to avoid checksum errors
COPY machine_learning/models /app/models

# Expose Flask port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Run Flask app
CMD ["python", "app.py"]
