import os
import logging
import numpy as np
import cv2

logger = logging.getLogger(__name__)

# Path where the Dockerfile / setup script places the GFPGAN weights
_GFPGAN_WEIGHTS = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),   # project root
    "gfpgan", "weights", "GFPGANv1.4.pth",
)


def enhance(image_bgr: np.ndarray) -> np.ndarray:
    """
    Enhance a BGR image using GFPGANv1.4.

    Falls back to the original image if:
      - The GFPGAN weight file is missing.
      - Any exception is raised during enhancement.

    Parameters
    ----------
    image_bgr : np.ndarray
        Input image in BGR colour order (as returned by cv2.imread).

    Returns
    -------
    np.ndarray
        Enhanced BGR image, or the original if enhancement failed.
    """
    if not os.path.isfile(_GFPGAN_WEIGHTS):
        logger.warning(
            "GFPGANv1.4.pth not found at %s — skipping enhancement.",
            _GFPGAN_WEIGHTS,
        )
        return image_bgr

    try:
        from gfpgan import GFPGANer  # lazy import — heavy dependency

        restorer = GFPGANer(
            model_path=_GFPGAN_WEIGHTS,
            upscale=1,
            arch="clean",
            channel_multiplier=2,
            bg_upsampler=None,   # no background super-resolution (keeps it CPU-friendly)
        )

        # GFPGAN expects BGR uint8
        _, _, restored_img = restorer.enhance(
            image_bgr,
            has_aligned=False,
            only_center_face=False,
            paste_back=True,
            weight=0.5,
        )

        if restored_img is None:
            logger.warning("GFPGAN returned None — using original image.")
            return image_bgr

        return restored_img

    except Exception as exc:  # noqa: BLE001
        logger.error("Enhancement failed (%s) — returning original image.", exc)
        return image_bgr
