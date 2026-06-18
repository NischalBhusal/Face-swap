import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model


class FaceSwapper:
    """
    Loads InsightFace buffalo_l detector and inswapper_128 model once at startup.
    Exposes a single swap() method that takes two image paths and returns a BGR ndarray.
    """

    def __init__(self, model_path: str, det_size: tuple = (640, 640)):
        """
        Parameters
        ----------
        model_path : str
            Absolute or relative path to inswapper_128.onnx
        det_size : tuple
            Detection resolution fed to InsightFace (default 640×640).
        """
        # ------------------------------------------------------------------ #
        # 1. Face analysis / detector (buffalo_l)                             #
        # ------------------------------------------------------------------ #
        self.face_app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"],
        )
        self.face_app.prepare(ctx_id=0, det_size=det_size)

        # ------------------------------------------------------------------ #
        # 2. Inswapper model                                                  #
        # ------------------------------------------------------------------ #
        self.swapper = get_model(
            model_path,
            providers=["CPUExecutionProvider"],
        )

    # ---------------------------------------------------------------------- #
    # Public API                                                              #
    # ---------------------------------------------------------------------- #

    def swap(self, source_img_path: str, target_img_path: str) -> np.ndarray:
        """
        Swap the first detected face in source_img onto every face in target_img.

        Parameters
        ----------
        source_img_path : str
            Path to the image that supplies the face identity.
        target_img_path : str
            Path to the image whose faces will be replaced.

        Returns
        -------
        np.ndarray
            BGR image with faces swapped.

        Raises
        ------
        ValueError
            If no face is detected in either image.
        FileNotFoundError
            If either image path cannot be opened by OpenCV.
        """
        # -- Load images --------------------------------------------------- #
        source_img = cv2.imread(source_img_path)
        if source_img is None:
            raise FileNotFoundError(f"Cannot open source image: {source_img_path}")

        target_img = cv2.imread(target_img_path)
        if target_img is None:
            raise FileNotFoundError(f"Cannot open target image: {target_img_path}")

        # -- Detect faces -------------------------------------------------- #
        source_faces = self.face_app.get(source_img)
        if not source_faces:
            raise ValueError("No face detected in the source image. "
                             "Please upload a clear, front-facing photo.")

        target_faces = self.face_app.get(target_img)
        if not target_faces:
            raise ValueError("No face detected in the target image. "
                             "Please upload an image that contains at least one face.")

        # Sort by bounding-box area descending so index-0 is the largest face
        source_faces = sorted(
            source_faces,
            key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
            reverse=True,
        )
        source_face = source_faces[0]

        # -- Swap onto every target face ----------------------------------- #
        result = target_img.copy()
        for target_face in target_faces:
            result = self.swapper.get(result, target_face, source_face, paste_back=True)

        return result
