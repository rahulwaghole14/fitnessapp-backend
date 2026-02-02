import os
import uuid
from typing import Optional
from fastapi import UploadFile, HTTPException
from PIL import Image
import aiofiles
from pathlib import Path

# Allowed image extensions
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


class ImageService:
    def __init__(self, upload_dir: str = "app/media/profile_images"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def validate_image(self, file: UploadFile) -> None:
        """Validate image format and size"""
        # Check file extension
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file format. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # Check file size
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE // (1024 * 1024)}MB"
            )

    async def save_profile_image(self, file: UploadFile, user_id: int) -> str:
        """Save profile image and return the file path"""
        self.validate_image(file)

        # Generate filename using user_id
        file_extension = Path(file.filename).suffix.lower()
        filename = f"{user_id}{file_extension}"
        file_path = self.upload_dir / filename

        try:
            # Read and validate image content
            content = await file.read()

            # Validate it's actually an image
            try:
                Image.open(io.BytesIO(content))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid image file")

            # Reset file pointer
            await file.seek(0)

            # Save file (this will overwrite if it exists)
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)

            return f"app/media/profile_images/{filename}"

        except Exception as e:
            # Clean up if file was created but error occurred
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=500, detail=f"Failed to save image: {str(e)}")

    def delete_old_profile_image(self, old_image_path: Optional[str]) -> None:
        """Delete old profile image if it exists"""
        if old_image_path:
            old_file_path = Path(old_image_path)
            if old_file_path.exists():
                try:
                    old_file_path.unlink()
                except Exception:
                    # Log error but don't fail the operation
                    pass


# Import io for BytesIO
import io
