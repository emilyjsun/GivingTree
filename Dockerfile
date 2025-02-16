FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    git \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create directories for persistent storage
RUN mkdir -p /app/chroma_db /app/vector_db

# Set environment variable for tokenizers
ENV TOKENIZERS_PARALLELISM=false

CMD ["python", "run_matcher.py"] 