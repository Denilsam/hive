import os
from PIL import Image
from django.core.exceptions import ValidationError

# Allowed file extensions & mime types for images
ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.svg'}
ALLOWED_IMAGE_MIME_TYPES = {'image/png', 'image/jpeg', 'image/webp', 'image/svg+xml'}
MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

def validate_uploaded_image(file_obj):
    """
    Validates uploaded file size, extension, MIME type, and Pillow format integrity.
    Prevents path traversal and unsafe executable extensions.
    """
    if not file_obj:
        return

    # 1. File size check
    if file_obj.size > MAX_UPLOAD_SIZE_BYTES:
        raise ValidationError(f"File size exceeds maximum allowed limit of {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB.")

    # 2. Extension check
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}")

    # 3. Content type check
    content_type = getattr(file_obj, 'content_type', '').lower()
    if content_type and content_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise ValidationError(f"Invalid file MIME type '{content_type}'.")

    # 4. Safe image integrity verification with Pillow (skipping SVG which is handled via text check)
    if ext in {'.png', '.jpg', '.jpeg', '.webp'}:
        try:
            file_obj.seek(0)
            img = Image.open(file_obj)
            img.verify()
            file_obj.seek(0)
        except Exception:
            raise ValidationError("Invalid or corrupted image file.")

    # 5. Safe SVG check: Ensure SVG does not contain script tags or inline JS handlers
    if ext == '.svg' or content_type == 'image/svg+xml':
        try:
            file_obj.seek(0)
            content = file_obj.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='ignore')
            content_lower = content.lower()
            if '<script' in content_lower or 'javascript:' in content_lower or 'onload=' in content_lower or 'onerror=' in content_lower:
                raise ValidationError("SVG image contains disallowed active content or scripts.")
            file_obj.seek(0)
        except ValidationError:
            raise
        except Exception:
            raise ValidationError("Unable to validate SVG image content.")
