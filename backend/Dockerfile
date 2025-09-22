# backend/Dockerfile
# NOTE: pick CUDA tag compatible with drivers on your VM; adjust if needed.
FROM nvidia/cuda:12.2-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# System packages commonly needed by audio/ASR libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    wget \
    build-essential \
    libsndfile1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python (ensure pip is present)
RUN apt-get update && apt-get install -y python3 python3-pip python3-venv && rm -rf /var/lib/apt/lists/*

# Copy requirements and install (this is heavy but runs in Cloud Build or on the VM)
COPY requirements.txt /app/requirements.txt
RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY . /app

# Expose the port your uvicorn runs on
EXPOSE 8000

# Default command to run FastAPI (uvicorn)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
