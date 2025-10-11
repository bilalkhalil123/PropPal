"""
User sync API endpoint for direct user creation
"""
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr
from common.repositories.user_repository import UserRepository, get_user_repository
from models.users import User, UserResponse

router = APIRouter(prefix="/api/users", tags=["user-sync"])

class UserSyncRequest(BaseModel):
    """Request model for user sync"""
    clerk_id: str
    name: str
    email: EmailStr
    phone: Optional[str] = None
    role: str = "buyer"
    profile_image: Optional[str] = None

@router.post("/sync", response_model=UserResponse)
async def sync_user(
    request: Request,
    user_data: UserSyncRequest,
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Sync user from Clerk to our database
    Called by frontend after successful Clerk authentication
    """
    try:
        # Log incoming request
        print(f"\n🔄 [USER SYNC] Received sync request:")
        print(f"   📧 Email: {user_data.email}")
        print(f"   👤 Name: {user_data.name}")
        print(f"   🆔 Clerk ID: {user_data.clerk_id}")
        print(f"   📱 Phone: {user_data.phone}")
        print(f"   🎭 Role: {user_data.role}")
        print(f"   🖼️  Profile Image: {user_data.profile_image}")
        
        # Check if user already exists
        print(f"🔍 [USER SYNC] Checking if user exists...")
        existing_user = await user_repo.get_user_by_clerk_id(user_data.clerk_id)
        
        if existing_user:
            print(f"✅ [USER SYNC] User already exists, updating...")
            # Update existing user with latest data
            update_data = {
                "name": user_data.name,
                "email": user_data.email,
                "phone": user_data.phone,
                "role": user_data.role,
                "profile_image": user_data.profile_image,
            }
            
            updated_user = await user_repo.update_user(user_data.clerk_id, update_data)
            if updated_user:
                print(f"✅ [USER SYNC] User updated successfully!")
                print(f"   🆔 Database ID: {updated_user.id}")
                print(f"   📧 Email: {updated_user.email}")
                print(f"   👤 Name: {updated_user.name}")
                return UserResponse(
                    id=updated_user.id,
                    name=updated_user.name,
                    email=updated_user.email,
                    phone=updated_user.phone,
                    role=updated_user.role,
                    profile_image=updated_user.profile_image,
                    clerk_id=updated_user.clerk_id,
                    created_at=updated_user.created_at,
                    updated_at=updated_user.updated_at
                )
        else:
            print(f"🆕 [USER SYNC] User not found, creating new user...")
        
        # Create new user
        new_user_data = {
            "clerk_id": user_data.clerk_id,
            "name": user_data.name,
            "email": user_data.email,
            "phone": user_data.phone,
            "role": user_data.role,
            "profile_image": user_data.profile_image,
            "password_hash": None,  # Not needed with Clerk
        }
        
        created_user = await user_repo.create_user(new_user_data)
        print(f"✅ [USER SYNC] User created successfully!")
        print(f"   🆔 Database ID: {created_user.id}")
        print(f"   📧 Email: {created_user.email}")
        print(f"   👤 Name: {created_user.name}")
        
        return UserResponse(
            id=created_user.id,
            name=created_user.name,
            email=created_user.email,
            phone=created_user.phone,
            role=created_user.role,
            profile_image=created_user.profile_image,
            clerk_id=created_user.clerk_id,
            created_at=created_user.created_at,
            updated_at=created_user.updated_at
        )
        
    except Exception as e:
        print(f"❌ [USER SYNC] Error syncing user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error syncing user: {str(e)}")

@router.get("/sync-status/{clerk_id}")
async def get_sync_status(
    clerk_id: str,
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Check if user is synced in our database
    """
    try:
        print(f"\n🔍 [SYNC STATUS] Checking status for Clerk ID: {clerk_id}")
        user = await user_repo.get_user_by_clerk_id(clerk_id)
        if user:
            print(f"✅ [SYNC STATUS] User found in database!")
            print(f"   🆔 Database ID: {user.id}")
            print(f"   📧 Email: {user.email}")
            print(f"   👤 Name: {user.name}")
            return {
                "synced": True,
                "user_id": str(user.id),
                "last_updated": user.updated_at
            }
        else:
            print(f"❌ [SYNC STATUS] User not found in database")
            return {
                "synced": False,
                "message": "User not found in database"
            }
    except Exception as e:
        print(f"❌ [SYNC STATUS] Error checking sync status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error checking sync status: {str(e)}")
