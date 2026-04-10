# Dockerfile for Code Review Assistant OpenEnv Environment
# Optimized for Hugging Face Spaces with vcpu=2, memory=8gb

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and task definitions
COPY src/ ./src/
COPY server/ ./server/
COPY tasks/ ./tasks/
COPY app.py .
COPY inference.py .
COPY openenv.yaml .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=7860

# Expose port for API
EXPOSE 7860

# Create directory for results
RUN mkdir -p /app/results

# Default command runs the Flask server with gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:7860", "--workers", "2", "--timeout", "120"]
