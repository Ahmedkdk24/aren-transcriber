# Use NVIDIA CUDA base image with PyTorch (for GPU)
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# Set working directory
WORKDIR /app

# Prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Python + system deps
RUN apt-get update && apt-get install -y \
    python3 python3-pip ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (if you have requirements.txt)
COPY backend/requirements.txt .

# Install Python deps
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Expose the app port (FastAPI/Flask typically run on 8080 inside GCP)
EXPOSE 8080

# Run your backend
CMD ["python3", "app.py"]
