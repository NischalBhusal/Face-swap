# ⚡ FaceSwap — Free, Open-Source AI Face Swap

> Swap any face. Free. Instant. No sign-up.  
> Powered by **InsightFace** + **GFPGAN** — the same engines behind commercial tools.

[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Features

- 🔄 **One-click face swap** — upload source + target, get result in seconds
- 🧠 **Multi-face support** — swaps the source identity onto every detected face in the target image
- ✨ **GFPGAN enhancement** — optional quality boost via GFPGANv1.4
- 🖥️ **CPU-only** — no GPU required; runs on any machine
- 🔒 **Privacy-first** — images are processed in memory and deleted immediately
- 🚀 **Self-hostable** — Docker + Hugging Face Spaces ready

---

## Project Structure

```
faceswapfr/
├── main.py                  # FastAPI backend
├── requirements.txt         # Python dependencies
├── Dockerfile               # Docker / HF Spaces deployment
├── .gitattributes           # Git LFS for model files
├── .gitignore
├── models/
│   └── inswapper_128.onnx   # Downloaded at build time
├── static/
│   ├── index.html           # Single-page frontend
│   ├── style.css            # Dark theme CSS
│   └── app.js               # Frontend logic (drag-drop, fetch, toasts)
└── utils/
    ├── face_swapper.py      # InsightFace swap logic
    └── enhancer.py          # GFPGAN enhancement
```

---

## Local Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Download the inswapper model

```bash
mkdir -p models
wget https://huggingface.co/deepinsight/inswapper/resolve/main/inswapper_128.onnx \
     -O models/inswapper_128.onnx
```

### 3. (Optional) Download GFPGAN weights for enhancement

```bash
mkdir -p gfpgan/weights
wget https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/GFPGANv1.4.pth \
     -O gfpgan/weights/GFPGANv1.4.pth
```

### 4. Run the server

```bash
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000** in your browser.

---

## API Reference

### `GET /health`

Returns model load status.

```json
{ "status": "ok", "model_loaded": true }
```

### `POST /swap`

Perform a face swap.

| Parameter      | Type        | Description                                      |
|----------------|-------------|--------------------------------------------------|
| `source_image` | `file`      | Image supplying the face identity (JPG/PNG/WebP) |
| `target_image` | `file`      | Image whose faces will be replaced               |
| `enhance`      | `bool` (QS) | Run GFPGAN post-processing (default: `false`)    |

**Returns:** `image/jpeg` on success, or JSON `{ "detail": "..." }` on error.

**Error codes:**
- `400` — no face detected, bad file type, file too large
- `500` — internal model error
- `503` — model not loaded

---

## Hugging Face Spaces Deployment

1. Create a new Space → **SDK: Docker** → Visibility: Public
2. Clone your Space:
   ```bash
   git clone https://huggingface.co/spaces/YOUR_USERNAME/faceswap
   cd faceswap
   ```
3. Copy all project files into the cloned folder
4. Set up Git LFS:
   ```bash
   git lfs install
   ```
5. Push:
   ```bash
   git add .
   git commit -m "initial deploy"
   git push
   ```
6. Hugging Face will build the Docker image (~5 min first time)
7. Your Space is live at `https://huggingface.co/spaces/YOUR_USERNAME/faceswap`

> **Note:** The Dockerfile downloads both model weights (~900 MB total) at build time, so the first build takes a few minutes. Subsequent pushes use Docker layer caching and are much faster.

---

## Docker (self-hosted)

```bash
docker build -t faceswap .
docker run -p 7860:7860 faceswap
```

Open **http://localhost:7860**.

---

## Tech Stack

| Component   | Library                                                    |
|-------------|------------------------------------------------------------|
| Backend     | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn         |
| Face detect | [InsightFace](https://github.com/deepinsight/insightface) buffalo_l |
| Face swap   | InsightFace inswapper_128.onnx                             |
| Enhancement | [GFPGAN v1.4](https://github.com/TencentARC/GFPGAN)       |
| Runtime     | [ONNX Runtime](https://onnxruntime.ai/) (CPU)              |
| Frontend    | Vanilla HTML / CSS / JS — no frameworks                    |

---

## Limitations

- Requires a clear, reasonably front-facing face in the source image
- Sunglasses, extreme angles, heavy blur, or tiny faces may cause detection failure
- Processing time on CPU: ~5–15 s per image (varies with resolution and face count)
- GFPGAN adds ~10–20 s extra on CPU

---

## Ethics & Disclaimer

This tool is provided **for creative and educational purposes only**.

- ❌ Do not use to create non-consensual deepfakes
- ❌ Do not impersonate real individuals without their explicit permission
- ✅ Always obtain consent before swapping someone's face
- ✅ Clearly label AI-generated images when sharing

By using this software you agree to comply with all applicable laws and the terms of the underlying open-source licenses.

---

## License

MIT — see [LICENSE](LICENSE) for details.

Models are subject to their own licenses:
- InsightFace models: [InsightFace license](https://github.com/deepinsight/insightface/blob/master/LICENSE)
- GFPGAN: [MIT](https://github.com/TencentARC/GFPGAN/blob/master/LICENSE)
