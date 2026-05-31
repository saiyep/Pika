import os
import uuid
from datetime import datetime

from app.settings import settings

_EXT_BY_MIME = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
}


def _ext_from(filename: str | None, content_type: str | None) -> str:
    if content_type and content_type.lower() in _EXT_BY_MIME:
        return _EXT_BY_MIME[content_type.lower()]
    if filename and "." in filename:
        return "." + filename.rsplit(".", 1)[1].lower()
    return ".jpg"


def save_image(content: bytes, filename: str | None, content_type: str | None) -> str:
    """Save raw image under uploads/medical/{YYYY}/{MM}/ and return a RELATIVE path.

    Relative to UPLOAD_DIR. Absolute path is rejoined at read time via abs_path().
    """
    now = datetime.now()
    sub = os.path.join(now.strftime("%Y"), now.strftime("%m"))
    abs_dir = os.path.join(settings.upload_dir, sub)
    os.makedirs(abs_dir, exist_ok=True)

    ext = _ext_from(filename, content_type)
    name = f"{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"

    abs_path = os.path.join(abs_dir, name)
    with open(abs_path, "wb") as f:
        f.write(content)

    return os.path.join(sub, name).replace("\\", "/")


def abs_path(relative_path: str) -> str:
    return os.path.join(settings.upload_dir, relative_path)
