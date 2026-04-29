import os
import uuid
import time
from typing import Optional
from fastapi import UploadFile, HTTPException
from PIL import Image
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from pathlib import Path
import io

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
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB for meal images

class MealImageService:
    """Service for handling meal image uploads"""
    
    def __init__(self):
        self.base_folder = os.getenv("CLOUDINARY_BASE_FOLDER", "fitness-app")
        self.upload_folder = f"{self.base_folder}/meals"

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

    async def save_meal_image(self, file: UploadFile, meal_id: Optional[int] = None) -> str:
        """Upload meal image to cloud storage and return URL"""
        self.validate_image(file)

        # Generate unique public ID for Cloudinary
        file_extension = Path(file.filename).suffix.lower()
        timestamp = int(time.time())
        
        if meal_id:
            public_id = f"meal_{meal_id}_{timestamp}"
        else:
            public_id = f"meal_{uuid.uuid4().hex[:8]}_{timestamp}"

        try:
            # Read file content
            content = await file.read()

            # Validate it's actually an image and process it
            img_bytes = io.BytesIO()
            try:
                img = Image.open(io.BytesIO(content))
                # Convert to RGB if needed
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Resize if too large
                max_size = (1200, 800)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Save compressed image to bytes
                img.save(img_bytes, format='JPEG', quality=85, optimize=True)
                img_bytes.seek(0)
                
            except Exception as img_error:
                raise HTTPException(status_code=400, detail="Invalid image file")

            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                img_bytes,
                public_id=public_id,
                folder=self.upload_folder,
                resource_type="image",
                format="jpg",
                overwrite=True
            )

            # Return the secure URL
            return upload_result["secure_url"]

        except cloudinary.exceptions.Error as cloud_error:
            raise HTTPException(status_code=500, detail=f"Cloudinary upload failed: {str(cloud_error)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload meal image: {str(e)}")

    def delete_old_meal_image(self, old_image_url: Optional[str]) -> None:
        """Delete old meal image from cloud storage"""
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
