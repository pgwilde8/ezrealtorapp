"""
DigitalOcean Spaces service for file uploads
"""

import os
import boto3
from botocore.exceptions import ClientError
from PIL import Image
import io
from typing import Tuple, Optional
import uuid
from datetime import datetime

class SpacesService:
    def __init__(self):
        """Initialize Spaces client using environment variables"""
        self.access_key = os.getenv("DO_SPACES_KEY")
        self.secret_key = os.getenv("DO_SPACES_SECRETKEY")
        self.bucket_name = os.getenv("SPACES_BUCKET", "ezrealtorapp-spaces")
        self.region = os.getenv("SPACES_REGION", "sfo3")
        self.endpoint = os.getenv("SPACES_ENDPOINT", "https://sfo3.digitaloceanspaces.com")
        self.cdn_endpoint = os.getenv("SPACES_CDN_ENDPOINT", f"https://{self.bucket_name}.{self.region}.cdn.digitaloceanspaces.com")
        
        # Initialize boto3 client
        self.client = boto3.client(
            's3',
            region_name=self.region,
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key
        )
    
    def upload_image(
        self, 
        file_data: bytes, 
        folder: str, 
        filename: str,
        content_type: str = "image/jpeg",
        max_size: Tuple[int, int] = (1200, 900),
        quality: int = 85
    ) -> Tuple[str, str, dict]:
        """
        Upload an image to Spaces with optimization
        
        Args:
            file_data: Image file bytes
            folder: Folder path (e.g., "agents/test6" or "properties/test6")
            filename: Filename (e.g., "profile.jpg" or "prop-abc123-001.jpg")
            content_type: MIME type
            max_size: Maximum dimensions (width, height)
            quality: JPEG quality (1-100)
        
        Returns:
            Tuple of (full_url, thumbnail_url, metadata)
        """
        try:
            # Open image with Pillow
            image = Image.open(io.BytesIO(file_data))
            
            # Get original dimensions
            original_width, original_height = image.size
            metadata = {
                "width": original_width,
                "height": original_height,
                "format": image.format
            }
            
            # Convert RGBA to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if len(image.split()) == 4 else None)
                image = background
            
            # Resize if needed (maintain aspect ratio)
            if original_width > max_size[0] or original_height > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save optimized image to buffer
            optimized_buffer = io.BytesIO()
            image.save(optimized_buffer, format='JPEG', quality=quality, optimize=True)
            optimized_buffer.seek(0)
            optimized_data = optimized_buffer.getvalue()
            
            # Upload full-size image
            full_path = f"{folder}/{filename}"
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=full_path,
                Body=optimized_data,
                ContentType=content_type,
                ACL='public-read',
                CacheControl='max-age=31536000'  # 1 year cache
            )
            
            # Generate thumbnail (400x300)
            thumbnail_image = image.copy()
            thumbnail_image.thumbnail((400, 300), Image.Resampling.LANCZOS)
            
            thumbnail_buffer = io.BytesIO()
            thumbnail_image.save(thumbnail_buffer, format='JPEG', quality=80, optimize=True)
            thumbnail_buffer.seek(0)
            thumbnail_data = thumbnail_buffer.getvalue()
            
            # Upload thumbnail
            thumbnail_filename = filename.rsplit('.', 1)[0] + '_thumb.jpg'
            thumbnail_path = f"thumbnails/{folder}/{thumbnail_filename}"
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=thumbnail_path,
                Body=thumbnail_data,
                ContentType=content_type,
                ACL='public-read',
                CacheControl='max-age=31536000'
            )
            
            # Generate URLs (use direct endpoint for now, not CDN)
            direct_endpoint = f"https://{self.bucket_name}.{self.region}.digitaloceanspaces.com"
            full_url = f"{direct_endpoint}/{full_path}"
            thumbnail_url = f"{direct_endpoint}/{thumbnail_path}"
            
            # Update metadata with file sizes
            metadata["file_size"] = len(optimized_data)
            metadata["thumbnail_size"] = len(thumbnail_data)
            metadata["final_width"] = image.width
            metadata["final_height"] = image.height
            
            return full_url, thumbnail_url, metadata
            
        except Exception as e:
            raise Exception(f"Failed to upload image: {str(e)}")
    
    def delete_image(self, url: str) -> bool:
        """
        Delete an image from Spaces
        
        Args:
            url: Full URL of the image
        
        Returns:
            True if successful
        """
        try:
            # Extract path from URL
            if self.cdn_endpoint in url:
                path = url.replace(f"{self.cdn_endpoint}/", "")
            elif self.endpoint in url:
                path = url.replace(f"{self.endpoint}/{self.bucket_name}/", "")
            else:
                return False
            
            # Delete the file
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=path
            )
            
            # Try to delete thumbnail if it exists
            if not path.startswith("thumbnails/"):
                thumbnail_path = f"thumbnails/{path.rsplit('.', 1)[0]}_thumb.jpg"
                try:
                    self.client.delete_object(
                        Bucket=self.bucket_name,
                        Key=thumbnail_path
                    )
                except:
                    pass  # Thumbnail might not exist
            
            return True
            
        except ClientError as e:
            print(f"Error deleting image: {e}")
            return False
    
    def generate_unique_filename(self, original_filename: str, prefix: str = "") -> str:
        """
        Generate a unique filename
        
        Args:
            original_filename: Original filename
            prefix: Optional prefix (e.g., "prop-abc123")
        
        Returns:
            Unique filename
        """
        ext = original_filename.rsplit('.', 1)[-1].lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        
        if prefix:
            return f"{prefix}_{timestamp}_{unique_id}.{ext}"
        return f"{timestamp}_{unique_id}.{ext}"


# Create singleton instance
spaces_service = SpacesService()

