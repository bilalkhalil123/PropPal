"""
Backblaze B2 storage service for image uploads using S3-compatible API.
"""

import os
import io
import sys
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional
from dotenv import load_dotenv
import boto3
from botocore.config import Config

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.config import get_settings

load_dotenv()

# Cache for S3 client
_s3_client_cache = None


def _get_b2_config():
    """Get B2 configuration from settings."""
    settings = get_settings()
    return (
        settings.B2_ENDPOINT,
        settings.B2_ACCESS_KEY,
        settings.B2_SECRET_KEY,
        settings.B2_BUCKET,
        settings.B2_PUBLIC_URL_TEMPLATE
    )


def _get_s3_client():
    """Get or create S3 client for Backblaze B2."""
    global _s3_client_cache
    
    if _s3_client_cache:
        return _s3_client_cache
    
    B2_ENDPOINT, B2_ACCESS_KEY, B2_SECRET_KEY, _, _ = _get_b2_config()
    
    if not B2_ENDPOINT or not B2_ACCESS_KEY or not B2_SECRET_KEY:
        raise ValueError("B2_ENDPOINT, B2_ACCESS_KEY, and B2_SECRET_KEY must be set in environment variables")
    
    session = boto3.session.Session()
    _s3_client_cache = session.client(
        's3',
        aws_access_key_id=B2_ACCESS_KEY,
        aws_secret_access_key=B2_SECRET_KEY,
        endpoint_url=B2_ENDPOINT,
        config=Config(signature_version='s3v4'),
        region_name=None
    )
    
    return _s3_client_cache


def _get_public_url_template():
    """Get public URL template, constructing default if not provided."""
    B2_ENDPOINT, _, _, B2_BUCKET, B2_PUBLIC_URL_TEMPLATE = _get_b2_config()
    
    if B2_PUBLIC_URL_TEMPLATE:
        return B2_PUBLIC_URL_TEMPLATE
    
    # Construct default template from endpoint and bucket
    if B2_ENDPOINT and B2_BUCKET:
        hostname = urlparse(B2_ENDPOINT).hostname
        return f"https://{B2_BUCKET}.{hostname}/{{key}}"
    
    raise ValueError("B2_PUBLIC_URL_TEMPLATE or B2_ENDPOINT and B2_BUCKET must be set")


def upload_file(file_content: bytes, file_name: str, content_type: str = "image/jpeg") -> str:
    """
    Upload a file to Backblaze B2 using S3-compatible API and return the public URL.
    
    Args:
        file_content: File content as bytes
        file_name: Name for the file in B2 (will be used as the key)
        content_type: MIME type of the file
        
    Returns:
        Public URL of the uploaded file
    """
    _, _, _, B2_BUCKET, _ = _get_b2_config()
    
    if not B2_BUCKET:
        raise ValueError("B2_BUCKET must be set in environment variables")
    
    # Get S3 client
    s3_client = _get_s3_client()
    
    # Get public URL template
    public_url_template = _get_public_url_template()
    
    # Use file_name as the key (you can modify this to add a prefix like "proppal/")
    key = file_name
    
    # Upload file
    file_obj = io.BytesIO(file_content)
    extra_args = {'ContentType': content_type}
    
    try:
        s3_client.upload_fileobj(file_obj, B2_BUCKET, key, ExtraArgs=extra_args)
    except Exception as e:
        # Retry without extra_args if it fails
        file_obj.seek(0)
        s3_client.upload_fileobj(file_obj, B2_BUCKET, key)
    
    # Construct public URL
    public_url = public_url_template.format(key=key)
    
    return public_url
