# aren-transcriber 🎙️

An Arabic-English transcriber web app that demonstrates **AI-powered audio transcription and speaker diarization** with:

- **FastAPI** backend (transcription + diarization pipeline)
- **React** frontend (UI to upload and process audio files)
- **PyTorch + GPU acceleration** (via NVIDIA Docker images)
- **Hugging Face integration** (pyannote pipeline for diarization)
![Demo](/src/assets/demo.mp4)
<video src="https://raw.githubusercontent.com/Ahmedkdk24/aren-transcriber/main/src/assets/demo.mp4" controls width="640"></video>

---

## 🚀 Deployment with GPU (Google Cloud + Docker)

This guide shows how to run **aren-transcriber** on a GCP VM with GPU support.  
It reflects the actual troubleshooting and solutions used to make GPU, Docker, and PyTorch work together.

---

## 📋 Prerequisites (on GCP VM)

- VM with NVIDIA GPU (e.g. T4, L4)
- NVIDIA driver installed on the VM
- [Docker](https://docs.docker.com/engine/install/) installed
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed
- Docker Compose v2 installed (`docker compose version`)
- Hugging Face account + token (for gated `pyannote` models)

Check GPU is visible on host:

```bash
nvidia-smi
````

---

## 🛠️ Environment Setup

1. **Clone repo:**

```bash
git clone https://github.com/yourusername/aren-transcriber.git
cd aren-transcriber
```

2. **Set up Hugging Face token:**

Create a `.env` file in the project root:

```ini
HF_TOKEN=your_huggingface_token_here
```

---

## 📦 Docker Setup

### Option A — Standalone Docker (backend only)

```bash
# build image
docker build -t aren-transcriber:latest .

# run container
docker run -d --gpus all --ipc=host --ulimit memlock=-1 --ulimit stack=67108864 \
  -p 8000:8000 -v $(pwd):/workspace/aren-transcriber \
  --env-file .env \
  --name aren-transcriber aren-transcriber:latest
```

Backend available at: [http://VM_EXTERNAL_IP:8000](http://VM_EXTERNAL_IP:8000)

Run frontend separately on host:

```bash
cd frontend
npm install
npm run dev -- --host
```

Frontend: [http://VM_EXTERNAL_IP:5173](http://VM_EXTERNAL_IP:5173)

---

### Option B — Docker Compose (backend + frontend)

`docker-compose.yml` (already in repo):

```yaml
version: "3.9"
services:
  backend:
    build: .
    container_name: aren-backend
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    ports:
      - "8000:8000"
    volumes:
      - ./:/workspace/aren-transcriber
    env_file:
      - .env
    runtime: nvidia

  frontend:
    image: node:20-bullseye
    container_name: aren-frontend
    working_dir: /app
    volumes:
      - ./frontend:/app
    ports:
      - "5173:5173"
    command: ["npm", "run", "dev", "--", "--host"]
```

Run both:

```bash
docker compose up --build
```

Backend: [http://VM_EXTERNAL_IP:8000](http://VM_EXTERNAL_IP:8000)
Frontend: [http://VM_EXTERNAL_IP:5173](http://VM_EXTERNAL_IP:5173)

---

## 🎧 ffmpeg (for pydub)

If you see warnings about `ffprobe` or `avprobe`, install ffmpeg inside backend container:

```bash
docker exec -it aren-backend bash
apt-get update && apt-get install -y ffmpeg
```

Add to `Dockerfile` to make permanent.

---

## 🔑 Hugging Face Authentication

In `backend/__init__.py`, the Hugging Face token is loaded from env vars:

```python
from huggingface_hub import login
import os

login(token=os.getenv("HF_TOKEN"))
```

⚠️ If you request a **gated model** (`pyannote/speaker-diarization-community-1`), you must be approved by Hugging Face.
Otherwise, use a fallback (e.g. `pyannote/speaker-diarization-3.1`).

---

## 🐛 Common Issues

* **`nvidia-smi: command not found` inside container**
  Run `nvidia-smi` on host. Containers may not include that binary, but GPU passthrough still works.

* **`undefined symbol: cudnn...` errors**
  Means host driver / cuDNN mismatch. Fix by ensuring host NVIDIA driver is new enough for container CUDA.

* **`torchvision::nms does not exist`**
  Happens when torch / torchvision versions mismatch. Stick with preinstalled versions in NVIDIA PyTorch images.

* **`numpy.core.multiarray failed to import`**
  Caused by reinstalling numpy against mismatched torch. Again: avoid reinstalling torch stack inside container.

---

## ✅ Verification

Check GPU is accessible inside backend container:

```bash
docker exec -it aren-backend python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

Expected:

```
True NVIDIA L4
```
---

## 🌍 For Reviewers

This project demonstrates:

* GPU-accelerated transcription/diarization
* Practical handling of CUDA / cuDNN / PyTorch container setup
* Integration of Hugging Face gated models
* Fullstack deployment with Docker Compose

If reproducing, please use the **Dockerfile + Compose setup** instead of manual installs.
That ensures a consistent environment.
