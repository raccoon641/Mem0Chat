from __future__ import annotations

import hashlib
import os
from typing import Optional, Tuple

import requests

from ..config import get_settings


def compute_sha256(content_bytes: bytes) -> str:
    hasher = hashlib.sha256()
    hasher.update(content_bytes)
    return hasher.hexdigest()


def download_twilio_media(media_url: str) -> Tuple[Optional[bytes], Optional[str]]:
    settings = get_settings()
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        return None, None
    try:
        resp = requests.get(media_url, auth=(settings.twilio_account_sid, settings.twilio_auth_token), timeout=30)
        if resp.status_code == 200:
            content_type = resp.headers.get("Content-Type")
            return resp.content, content_type
        return None, None
    except Exception:
        return None, None


def persist_media(content_bytes: bytes, sha256_hex: str, content_type: Optional[str]) -> str:
    settings = get_settings()
    ext = ""
    if content_type:
        if "jpeg" in content_type:
            ext = ".jpg"
        elif "png" in content_type:
            ext = ".png"
        elif "ogg" in content_type:
            ext = ".ogg"
        elif "mp3" in content_type:
            ext = ".mp3"
        elif "mp4" in content_type or "mpeg4" in content_type:
            ext = ".mp4"
    filename = f"{sha256_hex}{ext}"
    media_dir = os.path.join(settings.storage_dir, "media")
    os.makedirs(media_dir, exist_ok=True)
    file_path = os.path.join(media_dir, filename)
    if not os.path.exists(file_path):
        with open(file_path, "wb") as f:
            f.write(content_bytes)
    return file_path


# --------- Image perceptual hash (aHash) utilities ---------

def _image_to_ahash_int(img) -> Optional[int]:
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        gray = img.convert("L").resize((8, 8))
        pixels = list(gray.getdata())
        avg = sum(pixels) / 64.0
        bits = 0
        for i, p in enumerate(pixels):
            if p >= avg:
                bits |= (1 << i)
        return bits
    except Exception:
        return None


def compute_image_ahash_from_bytes(content_bytes: bytes) -> Optional[int]:
    try:
        from PIL import Image
        import io
    except Exception:
        return None
    try:
        with Image.open(io.BytesIO(content_bytes)) as img:
            return _image_to_ahash_int(img)
    except Exception:
        return None


def compute_image_ahash_from_path(path: str) -> Optional[int]:
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        with Image.open(path) as img:
            return _image_to_ahash_int(img)
    except Exception:
        return None


def hamming_distance(a: int, b: int) -> int:
    return bin((a ^ b) & ((1 << 64) - 1)).count("1") 