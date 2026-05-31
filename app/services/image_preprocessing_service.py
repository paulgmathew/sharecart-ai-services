from __future__ import annotations

import asyncio

import cv2
import numpy as np

from app.config.settings import Settings


class ImagePreprocessingService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def preprocess(self, image_bytes: bytes) -> bytes:
        return await asyncio.to_thread(self._preprocess_sync, image_bytes)

    def _preprocess_sync(self, image_bytes: bytes) -> bytes:
        image_np = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Unable to decode image")

        image = self._resize_large_image(image)
        image = self._deskew(image)
        image = self._enhance_contrast(image)
        image = self._normalize_brightness(image)
        image = self._crop_likely_receipt_region(image)

        success, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        if not success:
            raise ValueError("Unable to encode preprocessed image")
        return encoded.tobytes()

    def _resize_large_image(self, image: np.ndarray) -> np.ndarray:
        height, width = image.shape[:2]
        max_dim = max(height, width)
        if max_dim <= self._settings.max_image_dimension:
            return image

        scale = self._settings.max_image_dimension / float(max_dim)
        new_w = int(width * scale)
        new_h = int(height * scale)
        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))

        if coords.size == 0:
            return image

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_channel = clahe.apply(l_channel)
        merged = cv2.merge((l_channel, a_channel, b_channel))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    def _normalize_brightness(self, image: np.ndarray) -> np.ndarray:
        return cv2.normalize(image, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)

    def _crop_likely_receipt_region(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return image

        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        h, w = image.shape[:2]
        image_area = h * w

        for contour in contours[:5]:
            x, y, cw, ch = cv2.boundingRect(contour)
            area = cw * ch
            if area > image_area * 0.2:
                margin = 10
                x1 = max(0, x - margin)
                y1 = max(0, y - margin)
                x2 = min(w, x + cw + margin)
                y2 = min(h, y + ch + margin)
                return image[y1:y2, x1:x2]

        return image
