import os
import uuid
from typing import Optional
from fastapi import UploadFile, HTTPException
from PIL import Image
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# Allowed image extensions
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

class ImageService:
    def __init__(self):
        self.base_folder = os.getenv("CLOUDINARY_BASE_FOLDER", "fitness-app")
        self.upload_folder = f"{self.base_folder}/users/profile_images"

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
        self.validate_image(file)

        # Generate unique public ID for Cloudinary (add timestamp to avoid overwriting)
        import time
        file_extension = Path(file.filename).suffix.lower()
        timestamp = int(time.time())
        public_id = f"user_{user_id}_profile_{timestamp}"

        try:
            # Read file content
            content = await file.read()

            # Validate it's actually an image
            try:
                Image.open(io.BytesIO(content))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid image file")

            # Reset file pointer
            await file.seek(0)

            # Upload to Cloudinary (no overwrite to create new image)
            upload_result = cloudinary.uploader.upload(
                file.file,
                public_id=public_id,
                folder=self.upload_folder,
                resource_type="image",
                format=file_extension.replace(".", ""),
                overwrite=False
            )

            # Return the secure URL
            return upload_result["secure_url"]

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload image to Cloudinary: {str(e)}")

    def delete_old_profile_image(self, old_image_url: Optional[str]) -> None:
        if old_image_url and "cloudinary" in old_image_url:
            try:
                # Extract public_id from Cloudinary URL
                # URL format: https://res.cloudinary.com/cloud_name/image/upload/v1234567890/folder/public_id.ext
                parts = old_image_url.split('/')
                if len(parts) >= 8:
                    # Find the index of 'upload' in the URL
                    upload_index = parts.index('upload')
                    # Extract folder and public_id (skip version number)
                    folder_and_public_id = '/'.join(parts[upload_index+2:])
                    # Remove file extension
                    public_id = folder_and_public_id.rsplit('.', 1)[0]
                    
                    # Delete from Cloudinary
                    cloudinary.uploader.destroy(public_id, resource_type="image")
            except Exception:
                # Log error but don't fail the operation
                pass


class AdminImageService:
    """Separate service for admin profile images"""
    def __init__(self):
        self.base_folder = os.getenv("CLOUDINARY_BASE_FOLDER", "fitness-app")
        self.upload_folder = f"{self.base_folder}/admins/profile_images"

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

    async def save_profile_image(self, file: UploadFile, admin_id: int) -> str:
        self.validate_image(file)

        # Generate unique public ID for Cloudinary (add timestamp to avoid overwriting)
        import time
        file_extension = Path(file.filename).suffix.lower()
        timestamp = int(time.time())
        public_id = f"admin_{admin_id}_profile_{timestamp}"

        try:
            # Read file content
            content = await file.read()

            # Validate it's actually an image
            try:
                Image.open(io.BytesIO(content))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid image file")

            # Reset file pointer
            await file.seek(0)

            # Upload to Cloudinary (no overwrite to create new image)
            upload_result = cloudinary.uploader.upload(
                file.file,
                public_id=public_id,
                folder=self.upload_folder,
                resource_type="image",
                format=file_extension.replace(".", ""),
                overwrite=False
            )

            # Return the secure URL
            return upload_result["secure_url"]

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload admin image to Cloudinary: {str(e)}")

    def delete_old_profile_image(self, old_image_url: Optional[str]) -> None:
        if old_image_url and "cloudinary" in old_image_url:
            try:
                # Extract public_id from Cloudinary URL
                # URL format: https://res.cloudinary.com/cloud_name/image/upload/v1234567890/folder/public_id.ext
                parts = old_image_url.split('/')
                if len(parts) >= 8:
                    # Find the index of 'upload' in the URL
                    upload_index = parts.index('upload')
                    # Extract folder and public_id (skip version number)
                    folder_and_public_id = '/'.join(parts[upload_index+2:])
                    # Remove file extension
                    public_id = folder_and_public_id.rsplit('.', 1)[0]
                    
                    # Delete from Cloudinary
                    cloudinary.uploader.destroy(public_id, resource_type="image")
            except Exception:
                # Log error but don't fail the operation
                pass

# Import io for BytesIO
import io
