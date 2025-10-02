# aren-transcriber — README (GPU / Docker / PyTorch setup notes)

> This README documents **the GPU + Docker + PyTorch troubleshooting & setup flow** we followed while getting `aren-transcriber` running.
> It collects the exact, practical steps, commands and diagnostics that will help a reviewer reproduce (or understand) what happened and why some steps are necessary.
> Use it as a guide or copy-paste into your `README.md`. Adjust versions and tokens for your environment.

---

## Table of contents

1. [Quick summary](#quick-summary)
2. [High-level recommendation](#high-level-recommendation)
3. [Prerequisites (host)](#prerequisites-host)
4. [Host GPU / driver checks (very important)](#host-gpu--driver-checks-very-important)
5. [cuDNN / local repo install (if using host packages)](#cudnn--local-repo-install-if-using-host-packages)
6. [Why Docker was used (and the recommended approach)](#why-docker-was-used-and-the-recommended-approach)
7. [Install NVIDIA Container Toolkit (host)](#install-nvidia-container-toolkit-host)
8. [Quick Docker test (verify GPU from inside container)](#quick-docker-test-verify-gpu-from-inside-container)
9. [Working inside the NVIDIA PyTorch container — practical steps](#working-inside-the-nvidia-pytorch-container---practical-steps)
10. [Install app dependencies (without breaking container PyTorch)](#install-app-dependencies-without-breaking-container-pytorch)
11. [ffmpeg (pydub) — why needed and how to install in container or image](#ffmpeg-pydub---why-needed-and-how-to-install-in-container-or-image)
12. [Hugging Face + pyannote (auth & gated models)](#hugging-face--pyannote-auth--gated-models)
13. [Common errors & how to fix them (diagnostics)](#common-errors--how-to-fix-them-diagnostics)
14. [Make installs permanent: Dockerfile + build steps (recommended)](#make-installs-permanent-dockerfile--build-steps-recommended)
15. [Run backend & frontend — example commands & port mapping](#run-backend--frontend---example-commands--port-mapping)
16. [Docker housekeeping & disk issues (GCP tips)](#docker-housekeeping--disk-issues-gcp-tips)
17. [Alternatives if you want to avoid this stack](#alternatives-if-you-want-to-avoid-this-stack)
18. [FAQ / Notes for the reviewer](#faq--notes-for-the-reviewer)

---

## Quick summary

* GPU stacks break when versions mismatch: **host NVIDIA driver ↔ container CUDA runtime ↔ cuDNN ↔ PyTorch wheel ↔ torchvision/torchaudio ↔ numpy**.
* The **safest** approach is: pick an official GPU image (NVIDIA NGC / PyTorch), **do not overwrite** the core ML stack (torch/torchvision/torchaudio) inside the container, and add only your app deps on top. Commit a custom image once.
* If anything goes wrong: check host `nvidia-smi`, `df -h`, `docker ps -a`, `ldconfig -p | grep cudnn`, `python --version`.

---

## High-level recommendation

For a portfolio project where you just want a reproducible demo:

1. Build a single custom Docker image (based on NVIDIA's official PyTorch) that has:

   * ffmpeg installed
   * your Python dependencies (BUT **do not** re-install torch/torchvision/torchaudio unless you know exact matching builds)
   * any other system packages
2. Push that image or include `Dockerfile` in repo so reviewers can `docker build` once and run containers reproducibly.

---

## Prerequisites (host)

* Linux VM with an NVIDIA GPU (or cloud instance with GPU)
* `docker` installed and working on the host
* `nvidia-container-toolkit` installed (so containers can access GPUs)
* Enough disk space to pull NVIDIA images (~several GBs)

---

## Host GPU & driver checks (very important)

On the **host** (not inside a container) run:

```bash
# Show GPU / driver info
nvidia-smi

# Check disk usage
df -h /

# Show mounted block devices
lsblk

# Show installed CUDA compiler (if any)
nvcc --version  # may be missing if only driver installed
```

**Rule of thumb:** The host driver must be new enough to support the CUDA version used by the container. If driver is too old, upgrade the driver on the host.

---

## cuDNN / local repo install (if using host packages)

If you installed a local `.deb` repo (e.g. `cudnn-local-repo-debian12-...`), do the following to add the key and repo:

```bash
# Example: copy the packaged keyring (adjust path & filename from package)
sudo cp /var/cudnn-local-repo-debian12-9.13.0/cudnn-local-*-keyring.gpg /usr/share/keyrings/

# Add APT source (use exact key filename)
echo "deb [signed-by=/usr/share/keyrings/cudnn-local-4CB7544D-keyring.gpg] file:///var/cudnn-local-repo-debian12-9.13.0 /" | \
  sudo tee /etc/apt/sources.list.d/cudnn-local.list

sudo apt update
sudo apt install -y libcudnn9 libcudnn9-dev
```

Verify cuDNN:

```bash
ldconfig -p | grep cudnn
# Example expected line:
# libcudnn_cnn.so.9 => /lib/x86_64-linux-gnu/libcudnn_cnn.so.9
```

---

## Why Docker was used (and the recommended approach)

* Docker isolates OS-level dependencies and should make the environment reproducible.
* BUT: container images that include CUDA/driver-sensitive binaries must be used correctly — host driver compatibility matters.
* **Do not** mix-and-match by installing random system libs in the host and expecting the container to handle it unless you bake them into the image.

---

## Install NVIDIA Container Toolkit (host)

If `docker run --gpus all ...` fails with driver/toolkit errors, install the toolkit on the host:

```bash
# Add NVIDIA repo key & source (host)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure docker runtime and restart it
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Test GPU access from host into a container:

```bash
docker run --rm --gpus all nvidia/cuda:12.6.2-devel-ubuntu22.04 nvidia-smi
```

If the image returns GPU table, GPU passthrough works.

---

## Quick Docker test (verify GPU from inside container)

Run the NVIDIA PyTorch container and test PyTorch:

```bash
docker run --rm --gpus all nvcr.io/nvidia/pytorch:24.09-py3 \
  python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

Output should include `True` and the GPU model (e.g. `NVIDIA L4`).

**Note:** If the container logs "Failed to detect NVIDIA driver version" it is usually harmless as long as `torch.cuda.is_available()` returns `True`.

---

## Working inside the NVIDIA PyTorch container — practical steps

1. **Run the container and mount your repo** (so changes to code are reflected on host):

```bash
# Recommended: run detached so it stays up after you exit
docker run -d --gpus all --ipc=host --ulimit memlock=-1 --ulimit stack=67108864 \
  -v ~/aren-transcriber:/workspace/aren-transcriber \
  -w /workspace/aren-transcriber \
  -p 8000:8000 \
  --name aren-transcriber \
  nvcr.io/nvidia/pytorch:24.09-py3 tail -f /dev/null
```

2. **Open a shell inside the container:**

```bash
docker exec -it aren-transcriber bash
# now you're at: root@<id>:/workspace/aren-transcriber#
```

3. **Inside container**: install application-only Python deps (see next section):

```bash
pip install --upgrade pip
pip install -r requirements-app-only.txt    # DO NOT include torch/torchvision/torchaudio here
```

4. **Start backend** inside container (or from container startup cmd):

```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

---

## Install app dependencies (without breaking container PyTorch)

**Important:** NVIDIA PyTorch containers come with PyTorch / torchvision / torchaudio preinstalled and compiled to match the image’s CUDA/cuDNN. **Do not blindly reinstall** `torch`, `torchvision`, or `torchaudio` via pip unless you know exact matching wheels. Reinstalling them often causes `numpy.core.multiarray`, `_ZNK5torch8autograd...`, or `undefined symbol` errors.

**Recommended**:

* Create a `requirements-app-only.txt` with just your app dependencies (FastAPI, uvicorn, pyannote, pydub, huggingface-hub, etc.) *excluding* torch & friends:

```
fastapi
uvicorn
pydub
huggingface-hub
pyannote.audio
# other app deps
```

* Install it inside the container with:

```bash
pip install --no-cache-dir -r requirements-app-only.txt
```

* If a dependency absolutely requires a specific torch build, prefer building a custom image with that exact torch wheel baked in (see Dockerfile below).

---

## ffmpeg (pydub) — why needed and how to install

`pydub` uses `ffprobe`/`ffmpeg`. If you see:

```
RuntimeWarning: Couldn't find ffprobe or avprobe
```

install ffmpeg inside the container:

```bash
# inside container as root
apt-get update && apt-get install -y ffmpeg
```

**Make it permanent** by adding `apt-get install -y ffmpeg` to your Dockerfile (see below) and building an image so installs persist across container restarts.

---

## Hugging Face + pyannote (auth & gated models)

* **Authentication**: do not rely on interactive `login()` in a headless docker run. Use an environment variable:

```bash
# host: pass token into the container
docker run -e HF_TOKEN=hf_xxx ... nvcr.io/nvidia/pytorch:24.09-py3
```

* **In Python (no prompt)**:

```python
from huggingface_hub import login
import os
login(token=os.getenv("HF_TOKEN"))

from pyannote.audio import Pipeline
pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")  # public fallback
```

* **Gated repos / access requests**: if a model is gated (e.g. `pyannote/speaker-diarization-community-1`), you must request access on Hugging Face and be approved. If not approved, the token will not grant access. Implement a fallback in code (public model) so the service continues to work:

```python
try:
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-community-1")
except Exception:
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
```

---

## Common errors & how to fix them (diagnostics)

Below are the errors encountered during the setup and recommended fixes.

### 1. `nvcc: command not found`

* Means CUDA toolkit is not installed on host (only driver installed). Usually fine for Docker containers because they include CUDA runtime — `nvcc` is only needed for compiling CUDA code on host.

### 2. `Unable to load any of {libcudnn_cnn.so...} Invalid handle. Cannot load symbol cudnnCreateConvolutionDescriptor`

* Usually caused by missing or mismatched cuDNN. Fix:

  * Ensure `ldconfig -p | grep cudnn` shows `libcudnn_cnn.so.9`.
  * If missing inside host (not container), install cuDNN or copy keyring & install from cuDNN local repo (see earlier section).
  * If inside container, install `libcudnn*` via apt **or** prefer using the container’s pre-bundled cuDNN.

### 3. `pip install torch ... ERROR: No matching distribution found for torch`

* Most common cause: Python version incompatible with available wheels (e.g. Python 3.12 but torch wheels only for <=3.11).
* Check `python --version`. Use supported Python or use conda to get supported python version.

### 4. `RuntimeError: operator torchvision::nms does not exist` or `ImportError: numpy.core.multiarray failed to import` or `undefined symbol` in torchaudio

* These are ABI mismatches between torch / torchvision / numpy / torchaudio.
* **Safe approach**: use torch/torchvision/torchaudio versions that ship with the container. Avoid reinstalling them. If you must change, pin and install all three together to the matching builds.

### 5. `docker: failed to register layer: ... no space left on device`

* Clean docker artifacts:

```bash
docker system prune -af --volumes
sudo apt-get clean
```

* Check disk usage: `df -h` and `sudo du -h / --max-depth=1 | sort -hr | head -20`
* If disks were resized in GCP, you might need `growpart` and `resize2fs`:

```bash
sudo apt-get install -y cloud-guest-utils
sudo growpart /dev/nvme0n1 1
sudo resize2fs /dev/nvme0n1p1
```

---

## Make installs permanent: Dockerfile + build steps (recommended)

Create `Dockerfile` in repo (example):

```dockerfile
# Dockerfile — build on top of NVIDIA's PyTorch image
FROM nvcr.io/nvidia/pytorch:24.09-py3

WORKDIR /workspace/aren-transcriber

# system packages
RUN apt-get update && \
    apt-get install -y ffmpeg git curl && \
    rm -rf /var/lib/apt/lists/*

# copy only app requirements (do NOT include torch/torchvision/torchaudio)
COPY requirements-app-only.txt requirements-app-only.txt

# install Python deps for the app (but not torch)
RUN pip install --no-cache-dir -r requirements-app-only.txt

# copy code
COPY . /workspace/aren-transcriber

# default command to run (change as needed)
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
# build image once
docker build -t aren-transcriber:latest .

# run container (detached)
docker run -d --gpus all --ipc=host --ulimit memlock=-1 --ulimit stack=67108864 \
  -p 8000:8000 -v $(pwd):/workspace/aren-transcriber --name aren-transcriber aren-transcriber:latest
```

To get a shell into the running container:

```bash
docker exec -it aren-transcriber bash
```

If you previously installed packages manually inside a container and want to save that state:

```bash
# with container id <cid>
docker commit <cid> yourrepo/aren-transcriber:custom
# then push or use the new image
```

---

## Run backend & frontend — example commands & port mapping

### Option A — Backend in container, frontend on host

1. Run backend image:

```bash
docker run -d --gpus all -p 8000:8000 -v $(pwd):/workspace/aren-transcriber \
  --name aren-transcriber aren-transcriber:latest
```

2. On the **host** (VM), in your frontend folder:

```bash
npm install
npm run dev -- --host   # default Vite port 5173
```

* Visit `http://VM_EXTERNAL_IP:5173` for frontend. Frontend will call backend at `http://VM_EXTERNAL_IP:8000`.

### Option B — Both services as containers (docker-compose)

`docker-compose.yml` (simple sketch — GPU in compose requires Docker Engine 20+ and compose v2+):

```yaml
version: "3.9"
services:
  backend:
    image: aren-transcriber:latest
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
    runtime: nvidia
  frontend:
    image: node:20-bullseye
    working_dir: /app
    volumes:
      - ./frontend:/app
    ports:
      - "5173:5173"
    command: ["npm", "run", "dev", "--", "--host"]
```

Note: Compose GPU configuration varies by Docker version; running frontend on the host is often easier.

---

## Docker housekeeping & disk issues (GCP tips)

* Check disk usage: `df -h`
* Free Docker space:

```bash
docker system df
docker system prune -af --volumes
```

* Clean apt cache:

```bash
sudo apt-get clean
sudo rm -rf /var/lib/apt/lists/*
```

* If you resized a GCP boot disk and `resize2fs` says “nothing to do”, grow the partition:

```bash
sudo apt-get install -y cloud-guest-utils   # for growpart
sudo growpart /dev/nvme0n1 1
sudo resize2fs /dev/nvme0n1p1
```

---

## Alternatives if you want to avoid this stack

* **CPU-only**: run the app without GPU just to demonstrate the pipeline.
* **Google Colab / Vertex AI / Paperspace**: preconfigured GPU environments.
* **Conda**: easier dependency management locally (no pip wheel ABI issues).
* **Managed ML infra**: AWS Sagemaker, GCP Vertex AI that handle container environment for you.

---

## FAQ / Notes for the reviewer

* **Why do I pin versions?** PyTorch + CUDA require tightly matched versions. Pinning avoids runtime symbol errors.
* **Why not install torch via pip in container?** The container already includes a correctly built torch. Installing different torch builds breaks binary compatibility.
* **Hugging Face tokens** — use env var `HF_TOKEN` and `huggingface_hub.login(token=os.getenv("HF_TOKEN"))`.
* **If you see `nvidia-smi: command not found` inside a container** — run `nvidia-smi` on the **host**. Containers often don’t have that binary.
* **If you get stuck**: try `docker ps -a` to find stopped containers, `docker start -ai <id>` to reattach, and `docker exec -it <id> bash` to enter while running in background.

---

## Minimal files to include in the repo (suggestion)

* `Dockerfile` (as above)
* `requirements-app-only.txt` (no torch)
* `run.sh` (example script to build and run)
* `README.md` (this file)
* `docker-compose.yml` (optional)

---

## Closing notes

This README is intentionally pragmatic — it documents the exact causes of the common failure modes and gives deterministic steps to avoid them:

* **Use NVIDIA base images** for GPU work, but **don’t overwrite the ML runtime** inside them unless you know the exact wheel tags.
* **Bake** any system-level dependencies (ffmpeg, etc.) into a `Dockerfile` and build an image (one-time), then run containers from that image. That’s the “do it once and forget it” approach Docker is meant for.
