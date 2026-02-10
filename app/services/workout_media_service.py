import os
import uuid
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException
from PIL import Image
import aiofiles
from pathlib import Path
import io

# Allowed file extensions
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_VIDEO_SIZE = 50 * 1024 * 1024  # 50 MB

class WorkoutMediaService:
    def __init__(self):
        self.image_upload_dir = Path("app/media/workout_images")
        self.video_upload_dir = Path("app/media/workout_videos")
        self.image_upload_dir.mkdir(parents=True, exist_ok=True)
        self.video_upload_dir.mkdir(parents=True, exist_ok=True)

    def validate_image(self, file: UploadFile) -> None:
        """Validate image format and size"""
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
            
        # Check file extension
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image format. Allowed formats: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
            )

        # Check file size
        if file.size and file.size > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Image size exceeds maximum limit of {MAX_IMAGE_SIZE // (1024 * 1024)}MB"
            )

    def validate_video(self, file: UploadFile) -> None:
        """Validate video format and size"""
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
            
        # Check file extension
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ALLOWED_VIDEO_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid video format. Allowed formats: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
            )

        # Check file size
        if file.size and file.size > MAX_VIDEO_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Video size exceeds maximum limit of {MAX_VIDEO_SIZE // (1024 * 1024)}MB"
            )

    async def save_workout_image(self, file: UploadFile, workout_id: int, workout_title: str) -> str:
        """Save workout image and return the file path"""
        self.validate_image(file)

        # Generate filename using workout_id and workout_title
        file_extension = Path(file.filename).suffix.lower()
        # Sanitize workout title for filename
        sanitized_title = "".join(c for c in workout_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        sanitized_title = sanitized_title.replace(' ', '_')
        filename = f"{workout_id}_{sanitized_title}{file_extension}"
        file_path = self.image_upload_dir / filename

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

            return f"app/media/workout_images/{filename}"

        except Exception as e:
            # Clean up if file was created but error occurred
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=500, detail=f"Failed to save image: {str(e)}")

    async def save_workout_video(self, file: UploadFile, workout_id: int, workout_title: str) -> str:
        """Save workout video and return the file path"""
        self.validate_video(file)

        # Generate filename using workout_id and workout_title
        file_extension = Path(file.filename).suffix.lower()
        # Sanitize workout title for filename
        sanitized_title = "".join(c for c in workout_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        sanitized_title = sanitized_title.replace(' ', '_')
        filename = f"{workout_id}_{sanitized_title}{file_extension}"
        file_path = self.video_upload_dir / filename

        try:
            # Read video content
            content = await file.read()

            # Reset file pointer
            await file.seek(0)

            # Save file (this will overwrite if it exists)
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)

            return f"app/media/workout_videos/{filename}"

        except Exception as e:
            # Clean up if file was created but error occurred
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=500, detail=f"Failed to save video: {str(e)}")

    async def save_workout_media(self, image_file: Optional[UploadFile] = None, 
                                video_file: Optional[UploadFile] = None,
                                workout_id: int = None, 
                                workout_title: str = None) -> Tuple[Optional[str], Optional[str]]:
        """Save workout media files and return their paths"""
        image_path = None
        video_path = None

        if image_file and workout_id and workout_title:
            image_path = await self.save_workout_image(image_file, workout_id, workout_title)

        if video_file and workout_id and workout_title:
            video_path = await self.save_workout_video(video_file, workout_id, workout_title)

        return image_path, video_path

    def delete_old_workout_media(self, old_image_path: Optional[str], old_video_path: Optional[str]) -> None:
        """Delete old workout media files if they exist"""
        if old_image_path:
            old_file_path = Path(old_image_path)
            if old_file_path.exists():
                try:
                    old_file_path.unlink()
                except Exception:
                    # Log error but don't fail the operation
                    pass

        if old_video_path:
            old_file_path = Path(old_video_path)
            if old_file_path.exists():
                try:
                    old_file_path.unlink()
                except Exception:
                    # Log error but don't fail the operation
                    pass
