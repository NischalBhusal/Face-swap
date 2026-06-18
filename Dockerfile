# ── Base image ─────────────────────────────────────────────────────────────
FROM python:3.10-slim

# ── System dependencies needed by OpenCV / InsightFace ─────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
      libgl1-mesa-glx \
      libglib2.0-0 \
      libsm6 \
      libxrender1 \
      libxext6 \
      wget \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ───────────────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies (layer-cached separately from app code) ─────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application source ──────────────────────────────────────────────────────
COPY main.py .
COPY utils/ ./utils/
COPY static/ ./static/

# ── Model directories ───────────────────────────────────────────────────────
RUN mkdir -p models gfpgan/weights

# ── Download inswapper_128.onnx (~550 MB) ──────────────────────────────────
RUN wget -q --show-progress \
      https://huggingface.co/deepinsight/inswapper/resolve/main/inswapper_128.onnx \
      -O /app/models/inswapper_128.onnx

# ── Download GFPGANv1.4 weights (~333 MB) ──────────────────────────────────
RUN wget -q --show-progress \
      https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/GFPGANv1.4.pth \
      -O /app/gfpgan/weights/GFPGANv1.4.pth

# ── Expose port (Hugging Face Spaces expects 7860) ──────────────────────────
EXPOSE 7860

# ── Healthcheck ─────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD wget -q -O- http://localhost:7860/health | grep -q '"status":"ok"' || exit 1

# ── Run ─────────────────────────────────────────────────────────────────────
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
