"""
FaceSwap API — FastAPI backend
==============================
Endpoints
---------
GET  /           → serves static/index.html
GET  /health     → JSON model status
POST /swap       → multipart face-swap, optional ?enhance=true
"""

import io
import os
import time
import uuid
import logging
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from utils.face_swapper import FaceSwapper
from utils.enhancer import enhance

# --------------------------------------------------------------------------- #
# Logging                                                                      #
# --------------------------------------------------------------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Constants                                                                    #
# --------------------------------------------------------------------------- #
MODEL_PATH = Path(__file__).parent / "models" / "inswapper_128.onnx"
MAX_FILE_BYTES = 10 * 1024 * 1024           # 10 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# --------------------------------------------------------------------------- #
# Global state — initialised once in the lifespan handler                     #
# --------------------------------------------------------------------------- #
face_swapper: FaceSwapper | None = None
model_loaded: bool = False


# --------------------------------------------------------------------------- #
# Lifespan (startup / shutdown)                                               #
# --------------------------------------------------------------------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    global face_swapper, model_loaded

    logger.info("Loading FaceSwapper — model path: %s", MODEL_PATH)
    if not MODEL_PATH.exists():
        logger.error(
            "inswapper_128.onnx NOT found at %s. "
            "Run:  mkdir models && wget <url> -O models/inswapper_128.onnx",
            MODEL_PATH,
        )
        model_loaded = False
    else:
        try:
            face_swapper = FaceSwapper(str(MODEL_PATH))
            model_loaded = True
            logger.info("FaceSwapper loaded successfully ✓")
        except Exception as exc:
            logger.exception("Failed to load FaceSwapper: %s", exc)
            model_loaded = False

    yield  # ←── application runs here

    logger.info("Shutting down.")


# --------------------------------------------------------------------------- #
# App                                                                          #
# --------------------------------------------------------------------------- #
app = FastAPI(
    title="FaceSwap API",
    description="Open-source face swap powered by InsightFace + GFPGAN",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for local dev / HF Spaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (CSS, JS, etc.)
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def _validate_upload(file: UploadFile, label: str) -> None:
    """Raise HTTPException 400 if content-type or size is invalid."""
    ct = (file.content_type or "").lower()
    ext = Path(file.filename or "").suffix.lower()

    if ct not in ALLOWED_CONTENT_TYPES and ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"{label}: unsupported file type '{ct}'. "
                   "Only JPG, PNG, and WebP are accepted.",
        )


async def _read_upload(file: UploadFile, label: str) -> bytes:
    """Read upload bytes, enforcing the 10 MB cap."""
    data = await file.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"{label}: file exceeds the 10 MB limit.",
        )
    return data


def _save_temp(data: bytes, suffix: str) -> str:
    """Write bytes to a uniquely named temp file and return its path."""
    tmp_path = os.path.join(
        tempfile.gettempdir(),
        f"faceswap_{uuid.uuid4().hex}{suffix}",
    )
    with open(tmp_path, "wb") as fh:
        fh.write(data)
    return tmp_path


def _cleanup(*paths: str) -> None:
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except OSError:
            pass


def _ndarray_to_jpeg_bytes(img: np.ndarray) -> bytes:
    """Encode a BGR ndarray to JPEG bytes."""
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise RuntimeError("cv2.imencode failed")
    return buf.tobytes()


# --------------------------------------------------------------------------- #
# Routes                                                                       #
# --------------------------------------------------------------------------- #
@app.get("/", include_in_schema=False)
async def index():
    html_path = static_dir / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(str(html_path), media_type="text/html")


@app.get("/health")
async def health():
    return JSONResponse(
        content={"status": "ok", "model_loaded": model_loaded},
        status_code=200,
    )


@app.post("/swap")
async def swap_faces(
    source_image: UploadFile = File(..., description="Image supplying the face identity"),
    target_image: UploadFile = File(..., description="Image whose faces will be replaced"),
    enhance_quality: bool = Query(False, alias="enhance"),
):
    """
    Perform a face swap.

    - **source_image**: Photo that provides the face to copy.
    - **target_image**: Photo that receives the swapped face(s).
    - **enhance** (query param, default false): run GFPGAN post-processing.
    """
    if not model_loaded or face_swapper is None:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Check server logs for details.",
        )

    # -- Validate ---------------------------------------------------------- #
    _validate_upload(source_image, "source_image")
    _validate_upload(target_image, "target_image")

    # -- Read data --------------------------------------------------------- #
    src_data = await _read_upload(source_image, "source_image")
    tgt_data = await _read_upload(target_image, "target_image")

    # Determine extension from filename / content-type
    def _ext(file: UploadFile) -> str:
        ext = Path(file.filename or "").suffix.lower()
        if ext in ALLOWED_EXTENSIONS:
            return ext
        ct = (file.content_type or "").lower()
        return {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(ct, ".jpg")

    src_path = tgt_path = None
    t0 = time.perf_counter()

    try:
        src_path = _save_temp(src_data, _ext(source_image))
        tgt_path = _save_temp(tgt_data, _ext(target_image))

        # -- Swap ---------------------------------------------------------- #
        try:
            result = face_swapper.swap(src_path, tgt_path)
        except ValueError as exc:
            # No face detected → 400
            raise HTTPException(status_code=400, detail=str(exc))
        except FileNotFoundError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            logger.exception("Swap error: %s", exc)
            raise HTTPException(status_code=500, detail=f"Swap failed: {exc}")

        # -- Enhance (optional) -------------------------------------------- #
        if enhance_quality:
            try:
                result = enhance(result)
            except Exception as exc:
                logger.warning("Enhancement failed, using raw result: %s", exc)

        elapsed = time.perf_counter() - t0
        logger.info("Swap completed in %.2fs (enhance=%s)", elapsed, enhance_quality)

        # -- Encode & return ----------------------------------------------- #
        jpeg_bytes = _ndarray_to_jpeg_bytes(result)
        return Response(
            content=jpeg_bytes,
            media_type="image/jpeg",
            headers={"X-Processing-Time": f"{elapsed:.3f}"},
        )

    finally:
        _cleanup(src_path, tgt_path)
