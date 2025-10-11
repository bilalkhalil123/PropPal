"""
Clerk webhook handlers for user synchronization
"""
import json
import hmac
import hashlib
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from motor.motor_asyncio import AsyncIOMotorDatabase
from common.db import get_database
from common.config import get_settings
from common.repositories.user_repository import UserRepository, get_user_repository
from models.users import User, UserCreate
from datetime import datetime

router = APIRouter(prefix="/webhooks/clerk", tags=["clerk-webhooks"])

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Clerk webhook signature"""
    if not secret:
        return True  # Skip verification if no secret is set (development)
    
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"whsec_{expected_signature}", signature)

async def get_webhook_payload(request: Request, svix_signature: str = Header(None)):
    """Get and verify webhook payload"""
    settings = get_settings()
    
    # Get raw payload
    payload = await request.body()
    
    # Verify signature if secret is configured
    if settings.CLERK_WEBHOOK_SECRET and svix_signature:
        if not verify_webhook_signature(payload, svix_signature, settings.CLERK_WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    return json.loads(payload.decode('utf-8'))

@router.post("/user-created")
async def handle_user_created(
    request: Request,
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Handle Clerk user.created webhook
    Creates a user in our database when a new user signs up
    """
    try:
        # Get and verify webhook payload
        payload = await get_webhook_payload(request)
        
        # Extract user data from Clerk webhook
        clerk_user = payload.get("data", {})
        clerk_id = clerk_user.get("id")
        email_addresses = clerk_user.get("email_addresses", [])
        
        if not clerk_id or not email_addresses:
            raise HTTPException(status_code=400, detail="Missing required user data")
        
        # Get primary email
        primary_email = None
        for email_obj in email_addresses:
            if email_obj.get("id") == clerk_user.get("primary_email_address_id"):
                primary_email = email_obj.get("email_address")
                break
        
        if not primary_email:
            primary_email = email_addresses[0].get("email_address")
        
        # Extract user information
        first_name = clerk_user.get("first_name", "")
        last_name = clerk_user.get("last_name", "")
        name = f"{first_name} {last_name}".strip() or primary_email.split("@")[0]
        
        # Check if user already exists
        existing_user = await user_repo.get_user_by_clerk_id(clerk_id)
        if existing_user:
            return {
                "message": "User already exists", 
                "user_id": str(existing_user.id),
                "clerk_id": clerk_id
            }
        
        # Create new user data
        user_data = {
            "clerk_id": clerk_id,
            "name": name,
            "email": primary_email,
            "phone": None,  # Will be updated when user adds phone
            "role": "buyer",  # Default role - can be changed later
            "profile_image": clerk_user.get("profile_image_url"),
            "password_hash": None,  # Not needed with Clerk
        }
        
        # Create user in database
        created_user = await user_repo.create_user(user_data)
        
        return {
            "message": "User created successfully",
            "user_id": str(created_user.id),
            "clerk_id": clerk_id,
            "email": primary_email,
            "name": name
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing user creation: {str(e)}")

@router.post("/user-updated")
async def handle_user_updated(
    request: Request,
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Handle Clerk user.updated webhook
    Updates user data in our database when Clerk user is updated
    """
    try:
        payload = await get_webhook_payload(request)
        clerk_user = payload.get("data", {})
        clerk_id = clerk_user.get("id")
        
        if not clerk_id:
            raise HTTPException(status_code=400, detail="Missing clerk_id")
        
        # Find existing user
        existing_user = await user_repo.get_user_by_clerk_id(clerk_id)
        if not existing_user:
            # If user doesn't exist, create them (might happen if webhook order is wrong)
            return await handle_user_created(request, user_repo)
        
        # Extract updated information
        first_name = clerk_user.get("first_name", "")
        last_name = clerk_user.get("last_name", "")
        name = f"{first_name} {last_name}".strip()
        
        # Get primary email
        email_addresses = clerk_user.get("email_addresses", [])
        primary_email = None
        for email_obj in email_addresses:
            if email_obj.get("id") == clerk_user.get("primary_email_address_id"):
                primary_email = email_obj.get("email_address")
                break
        
        if not primary_email and email_addresses:
            primary_email = email_addresses[0].get("email_address")
        
        # Prepare update data
        update_data = {}
        if name:
            update_data["name"] = name
        if primary_email:
            update_data["email"] = primary_email
        if clerk_user.get("profile_image_url"):
            update_data["profile_image"] = clerk_user.get("profile_image_url")
        
        # Update user in database
        updated_user = await user_repo.update_user(clerk_id, update_data)
        
        if updated_user:
            return {
                "message": "User updated successfully",
                "user_id": str(updated_user.id),
                "clerk_id": clerk_id,
                "updated_fields": list(update_data.keys())
            }
        else:
            return {
                "message": "No changes made",
                "clerk_id": clerk_id
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing user update: {str(e)}")

@router.post("/user-deleted")
async def handle_user_deleted(
    request: Request,
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Handle Clerk user.deleted webhook
    Soft deletes user in our database when Clerk user is deleted
    """
    try:
        payload = await get_webhook_payload(request)
        clerk_user = payload.get("data", {})
        clerk_id = clerk_user.get("id")
        
        if not clerk_id:
            raise HTTPException(status_code=400, detail="Missing clerk_id")
        
        # Find existing user
        existing_user = await user_repo.get_user_by_clerk_id(clerk_id)
        if not existing_user:
            return {
                "message": "User not found", 
                "clerk_id": clerk_id
            }
        
        # Soft delete user
        success = await user_repo.soft_delete_user(clerk_id)
        
        if success:
            return {
                "message": "User deleted successfully",
                "user_id": str(existing_user.id),
                "clerk_id": clerk_id
            }
        else:
            return {
                "message": "Failed to delete user",
                "clerk_id": clerk_id
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing user deletion: {str(e)}")

@router.get("/health")
async def webhook_health():
    """Health check for Clerk webhooks"""
    return {"status": "ok", "service": "clerk-webhooks"}
