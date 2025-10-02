FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

# Set workdir
WORKDIR /workspace/aren-transcriber/backend

# System dependencies
RUN apt-get update && apt-get install -y ffmpeg git curl && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy source code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Run the backend server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
